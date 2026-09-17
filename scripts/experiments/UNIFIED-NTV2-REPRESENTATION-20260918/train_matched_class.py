#!/usr/bin/env python3
"""Train a matched NTv2 eight-state class head on the frozen D coordinates.

The binary six-species D checkpoint is kept intact.  This focused trainer
initializes its NTv2 encoder, replaces only the native token-classification
linear head with an eight-state head, and optionally unfreezes the last two
encoder blocks.  A species-balanced tile sampler mirrors the D training loop:
one 8,192-bp tile (two 4,096-bp records) per species per optimizer step.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import math
import random
import time
from pathlib import Path
from typing import Any

import numpy as np


LABEL_NAMES = [
    "BG",
    "SINE",
    "LINE",
    "LTR",
    "DNA",
    "KNOWN_OTHER_TE",
    "AMBIGUOUS_TE",
    "UNCLASSIFIED",
]
ID2LABEL = {i: name for i, name in enumerate(LABEL_NAMES)}
LABEL2ID = {name: i for i, name in ID2LABEL.items()}
SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
CLASS_WEIGHTS = [1.0, 3.0, 3.0, 3.0, 3.0, 3.0, 2.0, 2.0]
KMER_BP = 6
WINDOW_BP = 4096


def sequence_tokens(sequence: str, width: int = KMER_BP) -> list[str]:
    full_length = len(sequence) // width * width
    tokens = [sequence[start : start + width] for start in range(0, full_length, width)]
    tokens.extend(sequence[full_length:])
    return [token if set(token) <= {"A", "C", "G", "T"} else "<unk>" for token in tokens]


def token_span_lengths(sequence: str, width: int = KMER_BP) -> list[int]:
    """Base counts represented by the same native tokens used for training."""
    full_length = len(sequence) // width * width
    return [width] * (full_length // width) + [1] * (len(sequence) - full_length)


def majority_labels(label_text: str, width: int = KMER_BP) -> list[int]:
    """Map base ontology labels to native NTv2 token labels.

    A 6-bp token crossing a class boundary uses the most frequent base label;
    exact ties use the lowest numeric label.  This deterministic projection is
    fixed before training and is also used for validation/test scoring.
    """
    if len(label_text) != WINDOW_BP or any(char not in "01234567" for char in label_text):
        raise ValueError("class labels must be a 4096-character string of digits 0..7")
    result: list[int] = []
    full_length = len(label_text) // width * width
    for start in range(0, full_length, width):
        counts = np.bincount(np.frombuffer(label_text[start : start + width].encode("ascii"), dtype=np.uint8) - ord("0"), minlength=8)
        result.append(int(np.flatnonzero(counts == counts.max())[0]))
    result.extend(int(char) for char in label_text[full_length:])
    return result


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            sequence = str(row.get("sequence", "")).upper()
            labels = str(row.get("labels", ""))
            if len(sequence) != WINDOW_BP or len(labels) != WINDOW_BP:
                raise ValueError(f"{path}:{line_no}: expected 4096-bp sequence and labels")
            if any(char not in "01234567" for char in labels):
                raise ValueError(f"{path}:{line_no}: invalid class label digit")
            if row.get("species_code") not in SPECIES:
                raise ValueError(f"{path}:{line_no}: unexpected species {row.get('species_code')!r}")
            if "tile_id" not in row or "half" not in row:
                raise ValueError(f"{path}:{line_no}: matched class record lacks tile_id/half")
            records.append(row)
    return records


def paired_tiles(path: Path) -> dict[str, dict[str, tuple[dict[str, Any], dict[str, Any]]]]:
    by_species: dict[str, dict[str, dict[int, dict[str, Any]]]] = {
        species: {} for species in SPECIES
    }
    for row in load_records(path):
        species = str(row["species_code"])
        tile_id = str(row["tile_id"])
        half = int(row["half"])
        if half not in (0, 1):
            raise ValueError(f"{path}: invalid tile half {half}")
        tile = by_species[species].setdefault(tile_id, {})
        if half in tile:
            raise ValueError(f"{path}: duplicate {species}/{tile_id}/half{half}")
        tile[half] = row
    result: dict[str, dict[str, tuple[dict[str, Any], dict[str, Any]]]] = {}
    for species in SPECIES:
        result[species] = {}
        for tile_id, halves in by_species[species].items():
            if set(halves) != {0, 1}:
                raise ValueError(f"{path}: unpaired tile {species}/{tile_id}")
            result[species][tile_id] = (halves[0], halves[1])
    return result


def load_native_d_to_class(init_checkpoint: Path, base_model: Path):
    import torch
    from transformers import AutoConfig, AutoTokenizer
    from transformers.dynamic_module_utils import get_class_from_dynamic_module

    config = AutoConfig.from_pretrained(
        str(init_checkpoint), trust_remote_code=True, local_files_only=True
    )
    config.num_labels = len(LABEL_NAMES)
    config.id2label = ID2LABEL
    config.label2id = LABEL2ID
    model_class = get_class_from_dynamic_module(
        config.auto_map["AutoModelForTokenClassification"],
        str(base_model),
        local_files_only=True,
    )
    model = model_class._from_config(config)
    state = torch.load(init_checkpoint / "pytorch_model.bin", map_location="cpu")
    head_keys = {"classifier.weight", "classifier.bias"}
    filtered = {key: value for key, value in state.items() if key not in head_keys}
    missing, unexpected = model.load_state_dict(filtered, strict=False)
    if set(missing) != head_keys or unexpected:
        raise RuntimeError(
            f"D->class state transfer mismatch: missing={missing}, unexpected={unexpected}"
        )
    tokenizer = AutoTokenizer.from_pretrained(
        str(base_model), trust_remote_code=True, local_files_only=True
    )
    return model, tokenizer


def configure_trainable(model, scope: str) -> dict[str, Any]:
    if scope not in {"head", "last2", "all"}:
        raise ValueError(f"unsupported train scope {scope!r}")
    for parameter in model.parameters():
        parameter.requires_grad = False
    trainable_names: list[str] = []
    if scope == "all":
        for name, parameter in model.named_parameters():
            parameter.requires_grad = True
            trainable_names.append(name)
    else:
        for name, parameter in model.named_parameters():
            if name.startswith("classifier."):
                parameter.requires_grad = True
                trainable_names.append(name)
        if scope == "last2":
            layers = getattr(getattr(model, "esm", None), "encoder", None)
            layers = getattr(layers, "layer", None)
            if layers is None or len(layers) < 2:
                raise RuntimeError("native NTv2 model does not expose encoder.layer")
            for layer in layers[-2:]:
                for name, parameter in layer.named_parameters():
                    parameter.requires_grad = True
                    trainable_names.append(f"esm.encoder.layer[-2:]::{name}")
    count = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    return {
        "scope": scope,
        "trainable_parameter_count": int(count),
        "trainable_parameter_tensors": len(trainable_names),
        "classifier_is_trainable": bool(model.classifier.weight.requires_grad),
        "encoder_frozen_except_last_two": scope == "last2",
    }


def build_optimizer(model, learning_rate: float, weight_decay: float):
    """Use the D optimizer's decay convention for a matched class arm."""
    import torch
    from transformers.pytorch_utils import ALL_LAYERNORM_LAYERS
    from transformers.trainer_pt_utils import get_parameter_names
    decay_names = set(get_parameter_names(model, ALL_LAYERNORM_LAYERS))
    decay_names = {name for name in decay_names if "bias" not in name}
    parameters = dict(model.named_parameters())
    groups = [
        {
            "params": [
                parameter
                for name, parameter in parameters.items()
                if parameter.requires_grad and name in decay_names
            ],
            "weight_decay": weight_decay,
        },
        {
            "params": [
                parameter
                for name, parameter in parameters.items()
                if parameter.requires_grad and name not in decay_names
            ],
            "weight_decay": 0.0,
        },
    ]
    return torch.optim.AdamW(groups, lr=learning_rate)


def encode_batch(tokenizer, records: list[dict[str, Any]], device):
    import torch

    sequences = [sequence_tokens(str(row["sequence"])) for row in records]
    labels = [majority_labels(str(row["labels"])) for row in records]
    token_count = len(sequences[0])
    if any(len(tokens) != token_count for tokens in sequences):
        raise ValueError("variable token count in fixed-length records")
    max_length = ((token_count + 2 + 7) // 8) * 8
    encoded = tokenizer(
        sequences,
        is_split_into_words=True,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_special_tokens_mask=True,
        return_tensors="pt",
    )
    special = encoded.pop("special_tokens_mask")
    token_labels = torch.full_like(encoded["input_ids"], fill_value=-100, dtype=torch.long)
    for i, row_labels in enumerate(labels):
        positions = [
            j for j, (attended, is_special) in enumerate(
                zip(encoded["attention_mask"][i].tolist(), special[i].tolist())
            ) if attended and not is_special
        ]
        if len(positions) != len(row_labels):
            raise ValueError(f"native token count {len(positions)} != class labels {len(row_labels)}")
        token_labels[i, positions] = torch.tensor(row_labels, dtype=torch.long)
    return (
        {key: value.to(device) for key, value in encoded.items()},
        token_labels.to(device),
    )


def batch_metrics(confusion: np.ndarray) -> dict[str, Any]:
    f1s: list[float] = []
    recalls: list[float] = []
    precisions: list[float] = []
    per_class: dict[str, dict[str, float | int]] = {}
    for label, name in ID2LABEL.items():
        tp = int(confusion[label, label])
        fp = int(confusion[:, label].sum() - tp)
        fn = int(confusion[label, :].sum() - tp)
        support = int(confusion[label, :].sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[name] = {
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        if support:
            f1s.append(f1)
            recalls.append(recall)
            precisions.append(precision)
    return {
        "macro_f1": float(np.mean(f1s)) if f1s else 0.0,
        "macro_precision": float(np.mean(precisions)) if precisions else 0.0,
        "macro_recall": float(np.mean(recalls)) if recalls else 0.0,
        "accuracy": float(np.trace(confusion) / confusion.sum()) if confusion.sum() else 0.0,
        "support_total": int(confusion.sum()),
        "confusion_rows_true_cols_pred": confusion.tolist(),
        "per_class": per_class,
    }


def evaluate(model, tokenizer, split_tiles, device, batch_records: int = 2) -> dict[str, Any]:
    import torch

    model.eval()
    confusion = np.zeros((len(LABEL_NAMES), len(LABEL_NAMES)), dtype=np.int64)
    bp_confusion = np.zeros_like(confusion)
    species_confusions = {
        species: np.zeros_like(confusion) for species in SPECIES
    }
    species_bp_confusions = {
        species: np.zeros_like(confusion) for species in SPECIES
    }
    started = time.time()
    with torch.inference_mode():
        for species in SPECIES:
            rows = [row for tile in split_tiles[species].values() for row in tile]
            for start in range(0, len(rows), batch_records):
                batch = rows[start : start + batch_records]
                encoded, labels = encode_batch(tokenizer, batch, device)
                logits = model(**encoded).logits
                pred = logits.argmax(dim=-1)
                for row_index, row in enumerate(batch):
                    mask = labels[row_index].ne(-100)
                    truth = labels[row_index][mask].detach().cpu().numpy()
                    guess = pred[row_index][mask].detach().cpu().numpy()
                    if len(guess) != len(token_span_lengths(str(row["sequence"]))):
                        raise RuntimeError(
                            f"token prediction/base span count mismatch for {species}:{row.get('chrom')}:{row.get('start')}"
                        )
                    spans = token_span_lengths(str(row["sequence"]))
                    base_truth = np.frombuffer(
                        str(row["labels"]).encode("ascii"), dtype=np.uint8
                    ) - ord("0")
                    if len(base_truth) != sum(spans):
                        raise RuntimeError("base label length does not match token span lengths")
                    for true_label, pred_label in zip(truth.tolist(), guess.tolist()):
                        confusion[int(true_label), int(pred_label)] += 1
                        species_confusions[species][int(true_label), int(pred_label)] += 1
                    expanded_guess = np.repeat(guess.astype(np.int64), np.asarray(spans, dtype=np.int64))
                    if len(expanded_guess) != len(base_truth):
                        raise RuntimeError("expanded token predictions do not cover 4096 bp")
                    np.add.at(bp_confusion, (base_truth.astype(np.int64), expanded_guess), 1)
                    np.add.at(
                        species_bp_confusions[species],
                        (base_truth.astype(np.int64), expanded_guess),
                        1,
                    )
    result = batch_metrics(confusion)
    result["elapsed_seconds"] = time.time() - started
    result["bp"] = batch_metrics(bp_confusion)
    result["by_species"] = {}
    result["bp"]["by_species"] = {}
    # Pooled and per-species token/base confusion were accumulated in the same
    # forward pass; no second validation/test inference is needed.
    for species in SPECIES:
        species_result = batch_metrics(species_confusions[species])
        species_result["species"] = species
        result["by_species"][species] = species_result
        species_bp_result = batch_metrics(species_bp_confusions[species])
        species_bp_result["species"] = species
        result["bp"]["by_species"][species] = species_bp_result
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init-checkpoint", type=Path, required=True)
    ap.add_argument("--base-model", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--train-scope", choices=("head", "last2", "all"), default="last2")
    ap.add_argument("--max-steps", type=int, default=900)
    ap.add_argument("--eval-steps", type=int, default=150)
    ap.add_argument("--warmup-steps", type=int, default=90)
    ap.add_argument("--learning-rate", type=float, default=2e-5)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--bf16", action="store_true")
    args = ap.parse_args()

    import torch

    if args.max_steps < 1 or args.eval_steps < 1 or args.warmup_steps < 0:
        raise SystemExit("max-steps/eval-steps must be positive and warmup-steps non-negative")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing to reuse non-empty output: {args.output_dir}")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    if not torch.cuda.is_available():
        raise SystemExit("matched class training requires CUDA; use smoke for loader-only checks")

    train_tiles = paired_tiles(args.data_dir / "train" / "data.jsonl.gz")
    val_tiles = paired_tiles(args.data_dir / "val" / "data.jsonl.gz")
    test_tiles = paired_tiles(args.data_dir / "test" / "data.jsonl.gz")
    counts = {
        "train": {species: len(train_tiles[species]) for species in SPECIES},
        "val": {species: len(val_tiles[species]) for species in SPECIES},
        "test": {species: len(test_tiles[species]) for species in SPECIES},
    }
    expected = {
        "train": {**{species: 1500 for species in SPECIES if species != "c_elegans"}, "c_elegans": 3000},
        "val": {species: 500 for species in SPECIES},
        "test": {species: 500 for species in SPECIES},
    }
    if counts != expected:
        raise RuntimeError(f"matched class tile counts {counts} != {expected}")

    model, tokenizer = load_native_d_to_class(args.init_checkpoint, args.base_model)
    trainable = configure_trainable(model, args.train_scope)
    device = torch.device("cuda")
    model.to(device)
    model.config.use_cache = False
    model.train()
    train_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = build_optimizer(model, args.learning_rate, args.weight_decay)
    from transformers import get_linear_schedule_with_warmup

    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=min(args.warmup_steps, max(0, args.max_steps - 1)),
        num_training_steps=args.max_steps,
    )
    class_weights = torch.tensor(CLASS_WEIGHTS, dtype=torch.float32, device=device)
    rng = {species: random.Random(args.seed + i) for i, species in enumerate(SPECIES)}
    tile_orders = {species: list(train_tiles[species]) for species in SPECIES}
    for species in SPECIES:
        rng[species].shuffle(tile_orders[species])
    tile_positions = {species: 0 for species in SPECIES}

    def next_tile(species: str) -> tuple[dict[str, Any], dict[str, Any]]:
        position = tile_positions[species]
        if position >= len(tile_orders[species]):
            rng[species].shuffle(tile_orders[species])
            position = 0
            tile_positions[species] = 0
        tile_id = tile_orders[species][position]
        tile_positions[species] += 1
        return train_tiles[species][tile_id]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    best_metric = -math.inf
    best_step = 0
    validation_history: list[dict[str, Any]] = []
    started = time.time()
    with (args.output_dir / "train_log.jsonl").open("w", encoding="utf-8", buffering=1) as log:
        for step in range(1, args.max_steps + 1):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            raw_losses: dict[str, float] = {}
            for species in SPECIES:
                records = list(next_tile(species))
                encoded, labels = encode_batch(tokenizer, records, device)
                autocast_enabled = bool(args.bf16)
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=autocast_enabled):
                    logits = model(**encoded).logits
                    loss = torch.nn.functional.cross_entropy(
                        logits.reshape(-1, len(LABEL_NAMES)),
                        labels.reshape(-1),
                        weight=class_weights,
                        ignore_index=-100,
                    )
                # Match the six-species D loop: each species contributes one
                # sixth of the optimizer gradient at every step while its raw
                # loss remains logged in native units.
                (loss / len(SPECIES)).backward()
                raw_losses[species] = float(loss.detach().cpu())
            torch.nn.utils.clip_grad_norm_(train_parameters, args.grad_clip)
            optimizer.step()
            scheduler.step()
            log.write(json.dumps({"step": step, "loss": raw_losses, "learning_rate": optimizer.param_groups[0]["lr"]}) + "\n")

            if step % args.eval_steps == 0 or step == args.max_steps:
                validation = evaluate(model, tokenizer, val_tiles, device)
                validation["step"] = step
                validation_history.append(validation)
                metric = float(validation["macro_f1"])
                if metric > best_metric:
                    best_metric = metric
                    best_step = step
                    best_dir = args.output_dir / "best_model"
                    model.save_pretrained(best_dir, safe_serialization=False)
                    tokenizer.save_pretrained(best_dir)
                print(json.dumps({"step": step, "validation_macro_f1": metric, "best_step": best_step}, sort_keys=True), flush=True)

    # Reload the selected state before the final test so the test is evaluated
    # exactly once with the predeclared validation-selected checkpoint.
    selected = args.output_dir / "best_model"
    model, tokenizer = load_native_d_to_class(args.init_checkpoint, args.base_model)
    state = torch.load(selected / "pytorch_model.bin", map_location="cpu")
    missing, unexpected = model.load_state_dict(state, strict=True)
    if missing or unexpected:
        raise RuntimeError(f"saved class checkpoint reload mismatch: {missing}, {unexpected}")
    model.to(device)
    testing = evaluate(model, tokenizer, test_tiles, device)
    metadata = {
        "protocol": "UNIFIED-NTV2-REPRESENTATION-20260918",
        "seed": args.seed,
        "init_checkpoint": str(args.init_checkpoint),
        "base_model": str(args.base_model),
        "data_dir": str(args.data_dir),
        "output_dir": str(args.output_dir),
        "train_scope": args.train_scope,
        "max_steps": args.max_steps,
        "eval_steps": args.eval_steps,
        "warmup_steps": args.warmup_steps,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "class_weights": CLASS_WEIGHTS,
        "label_map": {str(key): value for key, value in ID2LABEL.items()},
        "base_token_projection": "6-bp majority label; ties -> lowest numeric label; same rule for all splits",
        "tile_sampling": "one tile per species per step; c_elegans TRAIN includes D upstream override",
        "split_tile_counts": counts,
        "trainable": trainable,
        "best_validation_macro_f1": best_metric,
        "best_step": best_step,
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "training_meta.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "validation_history.json").write_text(json.dumps(validation_history, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "test_results.json").write_text(json.dumps(testing, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS_MATCHED_CLASS_TRAIN", "best_step": best_step, "validation_macro_f1": best_metric, "test_macro_f1": testing["macro_f1"]}, indent=2))


if __name__ == "__main__":
    main()
