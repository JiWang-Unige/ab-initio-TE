#!/usr/bin/env python3
"""Clean direct-SF5 training, GPU smoke, and masked order-clade-held-out eval."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD", "1")
os.environ.setdefault("WANDB_DISABLED", "true")

import numpy as np

ID2LABEL = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}
MAIN4 = {1, 2, 3, 4}
UNKNOWN = 5
NUM_LABELS = 6
STATE2ID = {"P": 0, "U": 1, "hardN": 2, "RN": 3}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def expand_state_ids(rle: list[list[int]], expected: int) -> list[int]:
    states = [int(sid) for sid, length in rle for _ in range(int(length))]
    if len(states) != expected:
        raise ValueError(f"state_rle length {len(states)} != {expected}")
    return states


def encode_record(rec: dict, tokenizer, window: int, torch_module) -> dict:
    sequence = rec["sequence"][:window]
    labels = [int(x) for x in rec["labels"][:window]]
    if len(sequence) != window or len(labels) != window:
        raise ValueError("record does not match frozen window length")
    max_length = window + 2
    encoded = tokenizer(sequence, truncation=True, max_length=max_length, padding="max_length")
    token_labels = ([-100] + labels + [-100])[:max_length]
    token_labels.extend([-100] * (max_length - len(token_labels)))
    if len(encoded["input_ids"]) != max_length or len(token_labels) != max_length:
        raise ValueError("tokenizer/padding alignment failure")
    return {"input_ids": torch_module.tensor(encoded["input_ids"], dtype=torch_module.long),
            "attention_mask": torch_module.tensor(encoded.get("attention_mask", [1] * max_length), dtype=torch_module.long),
            "labels": torch_module.tensor(token_labels, dtype=torch_module.long)}


def safe_prf(y_true: np.ndarray, y_pred: np.ndarray, label: int) -> tuple[float, float, float, int]:
    tp = int(((y_true == label) & (y_pred == label)).sum())
    fp = int(((y_true != label) & (y_pred == label)).sum())
    fn = int(((y_true == label) & (y_pred != label)).sum())
    support = int((y_true == label).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1, support


def path_distance(a: int, b: int) -> int:
    def path(label: int) -> tuple[str, ...]:
        if label == 0:
            return ("ROOT", "BG")
        if label == UNKNOWN:
            return ("ROOT", "TE")
        return ("ROOT", "TE", ID2LABEL[int(label)])
    pa, pb = path(int(a)), path(int(b))
    common = 0
    for x, y in zip(pa, pb):
        if x != y:
            break
        common += 1
    return len(pa) + len(pb) - 2 * common


def score_arrays(y_true: np.ndarray, y_pred: np.ndarray, confidence: np.ndarray | None = None,
                 states: np.ndarray | None = None, threshold: float = 0.90) -> dict[str, float | int]:
    out: dict[str, float | int] = {}
    main_f1 = []
    for label, name in ID2LABEL.items():
        precision, recall, f1, support = safe_prf(y_true, y_pred, label)
        prefix = name.lower()
        out.update({f"{prefix}_precision": precision, f"{prefix}_recall": recall, f"{prefix}_f1": f1, f"{prefix}_support": support})
        if label in MAIN4 and support:
            main_f1.append(f1)
    true_te, pred_te = (y_true != 0).astype(np.int8), (y_pred != 0).astype(np.int8)
    out["te_detect_f1"] = safe_prf(true_te, pred_te, 1)[2]
    main_mask, unknown_mask = np.isin(y_true, list(MAIN4)), y_true == UNKNOWN
    out["main4_conditional_macro_f1"] = float(np.mean(main_f1)) if main_f1 else 0.0
    out["main4_false_unknown_rate"] = float((y_pred[main_mask] == UNKNOWN).mean()) if main_mask.any() else 0.0
    out["unknown_recall"] = float((y_pred[unknown_mask] == UNKNOWN).mean()) if unknown_mask.any() else 0.0
    wrong = y_true != y_pred
    distance = np.fromiter((path_distance(a, b) for a, b in zip(y_true[wrong], y_pred[wrong])), dtype=np.float64)
    out["hierarchical_path_distance"] = float(distance.mean()) if distance.size else 0.0
    if confidence is not None:
        over = wrong & np.isin(y_pred, list(MAIN4)) & (confidence >= threshold)
        out["overconfident_leaf_error"] = float(over.sum() / max(1, int((y_true != 0).sum())))
    else:
        out["overconfident_leaf_error"] = 0.0
    out.update({"evaluated_tokens": int(y_true.size), "main4_support": int(main_mask.sum()), "unknown_support": int(unknown_mask.sum())})
    if states is not None:
        for name in ("RN", "hardN"):
            mask = states == STATE2ID[name]
            out[f"{name}_support"] = int(mask.sum())
            out[f"{name}_te_fpr"] = float((y_pred[mask] != 0).mean()) if mask.any() else 0.0
        u_mask = states == STATE2ID["U"]
        out["U_ignored_support"] = int(u_mask.sum())
        out["U_predicted_te_candidate_rate"] = float((y_pred[u_mask] != 0).mean()) if u_mask.any() else 0.0
    return out


def score_logits(logits: np.ndarray, labels: np.ndarray, state_ids: np.ndarray, records: list[dict], temperature: float,
                 threshold: float, partition: str) -> dict:
    scaled = logits.astype(np.float64) / temperature
    scaled -= scaled.max(axis=-1, keepdims=True)
    probs = np.exp(scaled)
    probs /= probs.sum(axis=-1, keepdims=True)
    pred, confidence = probs.argmax(axis=-1), probs.max(axis=-1)
    score_mask = labels != -100
    result = score_arrays(labels[score_mask], pred[score_mask], confidence[score_mask], state_ids[score_mask], threshold)
    token_mask = state_ids >= 0
    for name in ("RN", "hardN"):
        guard = token_mask & (state_ids == STATE2ID[name])
        result[f"{name}_support"] = int(guard.sum())
        result[f"{name}_te_fpr"] = float((pred[guard] != 0).mean()) if guard.any() else 0.0
    u_guard = token_mask & (state_ids == STATE2ID["U"])
    result["U_ignored_support"] = int(u_guard.sum())
    result["U_predicted_te_candidate_rate"] = float((pred[u_guard] != 0).mean()) if u_guard.any() else 0.0
    by_species: dict[str, list[int]] = defaultdict(list)
    for index, rec in enumerate(records):
        by_species[rec["species_code"]].append(index)
    species_metrics, species_minima = {}, []
    for species, indices in sorted(by_species.items()):
        idx = np.asarray(indices)
        mask = score_mask[idx]
        metric = score_arrays(labels[idx][mask], pred[idx][mask], confidence[idx][mask], state_ids[idx][mask], threshold)
        local_states, local_pred = state_ids[idx], pred[idx]
        for name in ("RN", "hardN"):
            guard = local_states == STATE2ID[name]
            metric[f"{name}_support"] = int(guard.sum())
            metric[f"{name}_te_fpr"] = float((local_pred[guard] != 0).mean()) if guard.any() else 0.0
        guard = local_states == STATE2ID["U"]
        metric["U_ignored_support"] = int(guard.sum())
        metric["U_predicted_te_candidate_rate"] = float((local_pred[guard] != 0).mean()) if guard.any() else 0.0
        metric.update({"windows": len(indices), "species_taxid": records[indices[0]]["species_taxid"]})
        species_metrics[species] = metric
        species_minima.append(float(metric["main4_conditional_macro_f1"]))
    by_clade: dict[str, list[int]] = defaultdict(list)
    for index, rec in enumerate(records):
        by_clade[str(rec["clade_id"])].append(index)
    clade_metrics, clade_minima = {}, []
    for clade_id, indices in sorted(by_clade.items()):
        idx = np.asarray(indices); mask = score_mask[idx]
        metric = score_arrays(labels[idx][mask], pred[idx][mask], confidence[idx][mask], state_ids[idx][mask], threshold)
        metric.update({"windows": len(indices), "clade_id": clade_id, "clade_name": records[indices[0]]["clade_name"],
                       "species_codes": sorted({records[i]["species_code"] for i in indices})})
        clade_metrics[clade_id] = metric
        clade_minima.append(float(metric["main4_conditional_macro_f1"]))
    result.update({"per_species_secondary": species_metrics,
                   "minimum_primary_species_main4_macro_f1_secondary": min(species_minima) if species_minima else 0.0,
                   "per_clade": clade_metrics, "minimum_clade_main4_macro_f1": min(clade_minima) if clade_minima else 0.0,
                   "partition": partition, "temperature": temperature, "clade_generalization_claim": True})
    return result


def fit_temperature(logits: np.ndarray, labels: np.ndarray, grid: list[float]) -> tuple[float, dict[str, float]]:
    mask = labels != -100
    y, z = labels[mask].astype(np.int64), logits[mask].astype(np.float64)
    losses = {}
    for temperature in grid:
        scaled = z / float(temperature)
        maximum = scaled.max(axis=1)
        lse = maximum + np.log(np.exp(scaled - maximum[:, None]).sum(axis=1))
        losses[str(temperature)] = float(np.mean(lse - scaled[np.arange(len(y)), y]))
    selected = min(grid, key=lambda x: (losses[str(x)], x))
    return float(selected), losses


def runtime_imports():
    import torch
    from torch.utils.data import Dataset
    from transformers import AutoModelForTokenClassification, AutoTokenizer, Trainer, TrainingArguments, default_data_collator, set_seed
    return torch, Dataset, AutoModelForTokenClassification, AutoTokenizer, Trainer, TrainingArguments, default_data_collator, set_seed


def make_dataset_class(torch, Dataset):
    class DatasetImpl(Dataset):
        def __init__(self, path: Path, tokenizer, window: int, limit: int | None = None):
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                self.records = [json.loads(line) for index, line in enumerate(handle) if limit is None or index < limit]
            self.tokenizer, self.window = tokenizer, window
        def __len__(self):
            return len(self.records)
        def __getitem__(self, index: int):
            return encode_record(self.records[index], self.tokenizer, self.window, torch)
        def aligned_state_ids(self) -> np.ndarray:
            values = []
            for rec in self.records:
                states = expand_state_ids(rec["state_rle"], self.window)
                values.append(np.asarray([-1] + states + [-1], dtype=np.int8))
            return np.stack(values) if values else np.zeros((0, self.window + 2), dtype=np.int8)
    return DatasetImpl


def load_model(path: Path, AutoModel, AutoTokenizer):
    tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True, local_files_only=True)
    model = AutoModel.from_pretrained(path, num_labels=NUM_LABELS, id2label=ID2LABEL, label2id={v: k for k, v in ID2LABEL.items()},
                                      trust_remote_code=True, local_files_only=True, ignore_mismatched_sizes=True)
    return model, tokenizer


def make_trainer(torch, Trainer, weights: list[float]):
    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            loss_fn = torch.nn.CrossEntropyLoss(weight=torch.tensor(weights, device=outputs.logits.device), ignore_index=-100)
            loss = loss_fn(outputs.logits.reshape(-1, NUM_LABELS), labels.reshape(-1))
            return (loss, outputs) if return_outputs else loss
    return WeightedTrainer


def predict(trainer, dataset) -> tuple[np.ndarray, np.ndarray]:
    output = trainer.predict(dataset)
    logits = output.predictions[0] if isinstance(output.predictions, tuple) else output.predictions
    return np.asarray(logits), np.asarray(output.label_ids)


def train_command(args) -> None:
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    torch, Dataset, AutoModel, AutoTokenizer, Trainer, TrainingArguments, collator, set_seed = runtime_imports()
    DatasetImpl = make_dataset_class(torch, Dataset)
    set_seed(int(cfg["seed"]))
    model, tokenizer = load_model(root / cfg["base_checkpoint"], AutoModel, AutoTokenizer)
    train_ds = DatasetImpl(args.data_dir / "train/data.jsonl.gz", tokenizer, int(cfg["window"]))
    val_ds = DatasetImpl(args.data_dir / "val/data.jsonl.gz", tokenizer, int(cfg["window"]))
    if not len(train_ds) or not len(val_ds):
        raise ValueError("frozen clean train/validation dataset is empty")
    t = cfg["training"]
    training_args = TrainingArguments(output_dir=str(args.output_dir / "checkpoints"), overwrite_output_dir=True,
        per_device_train_batch_size=int(t["batch_size"]), per_device_eval_batch_size=int(t["batch_size"]),
        gradient_accumulation_steps=int(t["gradient_accumulation_steps"]), learning_rate=float(t["learning_rate"]), warmup_ratio=0.1,
        weight_decay=0.01, max_steps=int(t["max_steps"]), eval_strategy="steps", save_strategy="steps",
        eval_steps=int(t["eval_steps"]), save_steps=int(t["eval_steps"]), save_total_limit=2, load_best_model_at_end=True,
        metric_for_best_model=t["model_selection_metric"], greater_is_better=True, logging_steps=50, bf16=bool(t["bf16"]),
        gradient_checkpointing=bool(t["gradient_checkpointing"]), seed=int(cfg["seed"]), report_to="none", remove_unused_columns=False,
        save_safetensors=False)
    def metrics(eval_pred):
        logits, labels = eval_pred
        mask = labels != -100
        return score_arrays(labels[mask], np.argmax(logits, axis=-1)[mask])
    WeightedTrainer = make_trainer(torch, Trainer, list(t["class_weights"]))
    trainer = WeightedTrainer(model=model, args=training_args, train_dataset=train_ds, eval_dataset=val_ds,
                              compute_metrics=metrics, data_collator=collator)
    trainer.train()
    best = args.output_dir / "best_model"
    trainer.save_model(str(best))
    tokenizer.save_pretrained(str(best))
    val_logits, val_labels = predict(trainer, val_ds)
    temperature, losses = fit_temperature(val_logits, val_labels, list(t["temperature_grid"]))
    atomic_json(args.output_dir / "calibration.json", {"selection_split": "validation_only", "selected_temperature": temperature,
                                                       "validation_nll_by_temperature": losses, "validation_windows": len(val_ds),
                                                       "test_calibration_count": 0})
    atomic_json(args.output_dir / "training_meta.json", {"initialization": cfg["base_checkpoint"], "historical_head_used_for_initialization": False,
        "initialization_asset_contract_sha256": cfg["asset_contract_sha256"],
        "n_train_windows": len(train_ds), "n_val_windows": len(val_ds), "seed": cfg["seed"], "model_selection_split": "validation_only",
        "model_selection_metric": t["model_selection_metric"], "data_pass_manifest_sha256": args.data_pass_sha256,
        "config_sha256": sha256_file(args.config)})


def smoke_command(args) -> None:
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    torch, Dataset, AutoModel, AutoTokenizer, _Trainer, _TrainingArguments, _collator, _seed = runtime_imports()
    if not torch.cuda.is_available():
        raise ValueError("GPU smoke requires CUDA")
    DatasetImpl = make_dataset_class(torch, Dataset)
    model, tokenizer = load_model(root / cfg["base_checkpoint"], AutoModel, AutoTokenizer)
    if cfg["training"]["gradient_checkpointing"]:
        model.gradient_checkpointing_enable()
    model.cuda().train()
    ds = DatasetImpl(args.data_dir / "train/data.jsonl.gz", tokenizer, int(cfg["window"]), int(cfg["gpu_smoke"]["windows"]))
    if not len(ds):
        raise ValueError("GPU smoke dataset empty")
    torch.cuda.reset_peak_memory_stats()
    batch = {k: v.unsqueeze(0).cuda() for k, v in ds[0].items()}
    labels = batch.pop("labels")
    output = model(**batch)
    loss = torch.nn.functional.cross_entropy(output.logits.reshape(-1, NUM_LABELS), labels.reshape(-1), ignore_index=-100)
    loss.backward()
    peak = torch.cuda.max_memory_allocated() / (1024 ** 3)
    maximum = float(cfg["gpu_smoke"]["max_peak_vram_gib"])
    result = {"pass": math.isfinite(float(loss)) and peak <= maximum, "loss": float(loss.detach().cpu()), "peak_vram_gib": peak,
              "max_peak_vram_gib": maximum, "full_window_backward": True, "window": cfg["window"], "windows": len(ds)}
    result.update({"torch_version": torch.__version__, "cuda_runtime": torch.version.cuda,
                   "cuda_device": torch.cuda.get_device_name(torch.cuda.current_device())})
    atomic_json(args.output, result)
    if not result["pass"]:
        raise SystemExit(f"GPU smoke failed: {result}")


def eval_command(args) -> None:
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    torch, Dataset, AutoModel, AutoTokenizer, Trainer, TrainingArguments, collator, _seed = runtime_imports()
    DatasetImpl = make_dataset_class(torch, Dataset)
    model_path = args.clean_model_dir / "best_model" if args.model == "clean" else root / cfg["historical_head"]
    model, tokenizer = load_model(model_path, AutoModel, AutoTokenizer)
    ds = DatasetImpl(args.data_dir / args.partition / "data.jsonl.gz", tokenizer, int(cfg["window"]))
    if not len(ds):
        raise ValueError(f"evaluation partition empty: {args.partition}")
    eval_args = TrainingArguments(output_dir=str(args.output.parent / f"_tmp_{args.model}_{args.partition}"),
                                  per_device_eval_batch_size=int(cfg["training"]["batch_size"]), report_to="none", remove_unused_columns=False)
    WeightedTrainer = make_trainer(torch, Trainer, list(cfg["training"]["class_weights"]))
    logits, labels = predict(WeightedTrainer(model=model, args=eval_args, data_collator=collator), ds)
    if args.model == "clean":
        calibration = json.loads((args.clean_model_dir / "calibration.json").read_text(encoding="utf-8"))
        temperature = float(calibration["selected_temperature"])
    else:
        temperature = 1.0
    result = score_logits(logits, labels, ds.aligned_state_ids(), ds.records, temperature,
                          float(cfg["training"]["overconfidence_threshold"]), args.partition)
    result.update({"model": args.model, "model_path": str(model_path), "n_windows": len(ds), "test_calibration_count": 0,
                   "historical_head_role": "CONTINUITY_COMPARATOR_ONLY" if args.model == "historical" else "NOT_APPLICABLE"})
    if not all(math.isfinite(float(x)) for x in result.values() if isinstance(x, (int, float))):
        raise ValueError("non-finite evaluation metric")
    atomic_json(args.output, result)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("train"); p.add_argument("--config", required=True, type=Path); p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path); p.add_argument("--data-pass-sha256", required=True)
    p = sub.add_parser("smoke"); p.add_argument("--config", required=True, type=Path); p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p = sub.add_parser("eval"); p.add_argument("--config", required=True, type=Path); p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--clean-model-dir", required=True, type=Path); p.add_argument("--model", choices=("clean", "historical"), required=True)
    p.add_argument("--partition", choices=("test_primary", "audit_optional_stress"), required=True); p.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "train": train_command(args)
    elif args.command == "smoke": smoke_command(args)
    else: eval_command(args)


if __name__ == "__main__":
    main()
