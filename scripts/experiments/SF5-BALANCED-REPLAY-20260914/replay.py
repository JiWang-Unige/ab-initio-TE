#!/usr/bin/env python3
"""Balanced replay of the already scored SF5 test-prefix records.

The replay deliberately selects only the first fixed quota for four species
from the first 1,200 records used by the historical SF5 score.  It loads the
two existing checkpoints through the locked ``superfamily5_task.load_model``
helper, performs inference only, and writes per-position predictions plus
confusion-derived compact metrics.  It never calls the legacy training path.
"""
from __future__ import annotations

import argparse
import collections
import gc
import gzip
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple


LABEL_NAMES = {
    0: "BG",
    1: "SINE",
    2: "LINE",
    3: "LTR",
    4: "DNA",
    5: "Unknown",
}
MAIN4 = (1, 2, 3, 4)
TARGET_SPECIES = ("mouse", "zebrafish", "chicken", "western_clawed_frog")
LEGACY_EXCLUDED_SPECIES = ("fruit_fly", "c_elegans")
EXPECTED_MODEL_NAMES = (
    "SF5_base_pretrained_seed42",
    "SF5_binary_h0_seed42",
)


def validate_config(config: Mapping[str, object]) -> dict:
    """Validate the complete replay-entry contract before any model load.

    Keeping all configuration reads here makes a malformed run fail at the
    entry point rather than after selection or after one model has loaded.
    The returned values are the fields consumed by ``run``.
    """
    protocol = config["protocol"]
    status = config["status"]
    seed = int(config["seed"])
    window = int(config["window"])
    selection = config["selection"]
    if not isinstance(selection, Mapping):
        raise TypeError("selection must be an object")
    data_relpath = selection["data_relpath"]
    prefix_limit = int(selection["legacy_scored_prefix_limit"])
    species_order = tuple(selection["species_order"])
    per_species = int(selection["per_species_quota"])
    selected_windows = int(selection["selected_windows"])
    old_scored_population = selection["old_scored_population"]
    excluded_from_new_scoring = tuple(selection["excluded_from_new_scoring"])

    model_paths = config["model_paths"]
    if not isinstance(model_paths, Mapping):
        raise TypeError("model_paths must be an object")
    model_paths = dict(model_paths)

    outputs = config["outputs"]
    if not isinstance(outputs, Mapping):
        raise TypeError("outputs must be an object")
    remote_relroot = outputs["remote_relroot"]
    raw_predictions_policy = outputs["raw_predictions_policy"]

    resources = config["resources"]
    if not isinstance(resources, Mapping):
        raise TypeError("resources must be an object")
    partition = resources["partition"]
    gpu = resources["gpu"]
    cpus_per_task = int(resources["cpus_per_task"])
    memory = resources["memory"]
    time_limit = resources["time"]

    metric_contract = config["metric_contract"]
    if not isinstance(metric_contract, Mapping):
        raise TypeError("metric_contract must be an object")
    labels = metric_contract["labels"]
    confusion_orientation = metric_contract["confusion_orientation"]
    main4_macro_f1 = metric_contract["main4_macro_f1"]
    binary_material = metric_contract["binary_material"]
    raw_position_count = int(metric_contract["raw_position_count"])

    execution_policy = config["execution_policy"]
    if not isinstance(execution_policy, Mapping):
        raise TypeError("execution_policy must be an object")
    inference_only = bool(execution_policy["inference_only"])
    legacy_loader = execution_policy["legacy_loader"]
    training_path_called = bool(execution_policy["training_path_called"])
    tokenization = execution_policy["tokenization"]
    new_validation = bool(execution_policy["new_validation"])
    independent_validation = bool(execution_policy["independent_validation"])

    if protocol != "SF5_BALANCED_REPLAY_20260914":
        raise ValueError(f"unexpected protocol: {protocol}")
    if status != "FIXED_BEFORE_INFERENCE":
        raise ValueError(f"unexpected status: {status}")
    if seed != 42 or window != 4096:
        raise ValueError("seed/window contract drift")
    if species_order != TARGET_SPECIES or per_species != 120:
        raise ValueError("balanced replay species/quota contract drift")
    if prefix_limit != 1200 or selected_windows != 480:
        raise ValueError("balanced replay prefix/size contract drift")
    if old_scored_population != {
        "mouse": 360,
        "zebrafish": 360,
        "chicken": 360,
        "western_clawed_frog": 120,
        "fruit_fly": 0,
        "c_elegans": 0,
    }:
        raise ValueError("historical scored-population contract drift")
    required_excluded = {"fruit_fly", "c_elegans", "human", "sealed_species"}
    if not required_excluded.issubset(set(excluded_from_new_scoring)):
        raise ValueError("excluded-species contract drift")
    if set(model_paths) != set(EXPECTED_MODEL_NAMES):
        raise ValueError(f"model_paths names drift: {sorted(model_paths)}")
    if any(
        not isinstance(path, str) or not path.endswith("/best_model")
        for path in model_paths.values()
    ):
        raise ValueError("model_paths must point to best_model directories")
    if not isinstance(data_relpath, str) or not data_relpath.endswith("data.jsonl.gz"):
        raise ValueError("selection.data_relpath must point to the fixed test JSONL")
    if (
        not isinstance(remote_relroot, str)
        or remote_relroot != "outputs/SF5-BALANCED-REPLAY-20260914"
    ):
        raise ValueError("output root contract drift")
    if not isinstance(raw_predictions_policy, str) or "Baobab" not in raw_predictions_policy:
        raise ValueError("raw prediction retention contract drift")
    if partition not in ("shared-gpu", "private-teodoro-gpu"):
        raise ValueError(f"unsupported approved GPU partition: {partition}")
    if (
        gpu != "nvidia_geforce_rtx_3090:1"
        or cpus_per_task != 4
        or memory != "64G"
        or time_limit != "02:00:00"
    ):
        raise ValueError("resource contract drift")
    expected_labels = {
        "0": "BG",
        "1": "SINE",
        "2": "LINE",
        "3": "LTR",
        "4": "DNA",
        "5": "Unknown",
    }
    if labels != expected_labels:
        raise ValueError("six-label metric contract drift")
    if confusion_orientation != "true rows, predicted columns":
        raise ValueError("confusion orientation drift")
    if "all six-label" not in main4_macro_f1 or "BG and Unknown" not in main4_macro_f1:
        raise ValueError("main4 metric definition drift")
    if binary_material != "BG versus all five non-BG labels, including Unknown":
        raise ValueError("binary material definition drift")
    if raw_position_count != selected_windows * window:
        raise ValueError("raw position count drift")
    if (
        not inference_only
        or legacy_loader
        != "pipelines/PIPE-TEFM-LOCK-20260619/superfamily5_task.py:load_model"
    ):
        raise ValueError("inference/loader contract drift")
    if training_path_called or new_validation or independent_validation:
        raise ValueError("replay must not train or open a new validation set")
    if (
        not isinstance(tokenization, str)
        or "1 nt per token" not in tokenization
        or "BOS/EOS" not in tokenization
    ):
        raise ValueError("tokenization contract drift")
    return {
        "data_relpath": data_relpath,
        "species_order": species_order,
        "per_species": per_species,
        "prefix_limit": prefix_limit,
        "window": window,
        "seed": seed,
        "model_paths": model_paths,
        "protocol": protocol,
    }


def select_species_quota(
    jsonl_gz: Path,
    species_order: Sequence[str],
    per_species: int,
    prefix_limit: int,
) -> Tuple[List[dict], dict]:
    """Select the first fixed quota per species within a fixed old prefix.

    The source file is read only through ``prefix_limit`` records.  The
    resulting list is returned in the original test-file order, while each
    item retains its zero-based source record index and within-species rank.
    """
    if per_species <= 0 or prefix_limit <= 0:
        raise ValueError("per_species and prefix_limit must be positive")
    quotas = {species: int(per_species) for species in species_order}
    counts = collections.Counter()
    selected: List[dict] = []
    with gzip.open(jsonl_gz, "rt", encoding="utf-8") as handle:
        for record_index, line in enumerate(handle):
            if record_index >= prefix_limit:
                break
            record = json.loads(line)
            species = record.get("species_code")
            if species not in quotas or counts[species] >= quotas[species]:
                continue
            sequence = record.get("sequence")
            labels = record.get("labels")
            if not isinstance(sequence, str) or not isinstance(labels, list):
                raise ValueError(f"record {record_index}: missing sequence/labels")
            selected.append(
                {
                    "record_index": int(record_index),
                    "species_rank": int(counts[species]),
                    "species_code": species,
                    "record": record,
                }
            )
            counts[species] += 1
            if all(counts[species] == quota for species, quota in quotas.items()):
                break

    missing = {
        species: quotas[species] - counts[species]
        for species in species_order
        if counts[species] != quotas[species]
    }
    if missing:
        raise ValueError(f"prefix cannot satisfy species quotas: {missing}")
    selected.sort(key=lambda item: item["record_index"])
    metadata = {
        "source_prefix_limit": int(prefix_limit),
        "species_order": list(species_order),
        "quota_per_species": int(per_species),
        "selected_total": len(selected),
        "species_counts": {species: int(counts[species]) for species in species_order},
        "selected_record_indices": [item["record_index"] for item in selected],
        "selected_record_index_min": min(item["record_index"] for item in selected),
        "selected_record_index_max": max(item["record_index"] for item in selected),
        "all_selected_within_prefix": all(
            item["record_index"] < prefix_limit for item in selected
        ),
        "excluded_species": list(LEGACY_EXCLUDED_SPECIES),
        "selection_rule": "first quota records per target species in original order within old scored prefix",
    }
    return selected, metadata


def selection_rows(selected: Sequence[dict]) -> List[dict]:
    rows = []
    for selection_index, item in enumerate(selected):
        record = item["record"]
        sequence = record["sequence"]
        labels = record["labels"]
        rows.append(
            {
                "selection_index": int(selection_index),
                "record_id": f"test_line_{item['record_index']:06d}",
                "record_index": int(item["record_index"]),
                "species_rank": int(item["species_rank"]),
                "species_code": item["species_code"],
                "chr": record.get("chr", ""),
                "start": record.get("start", ""),
                "end": record.get("end", ""),
                "sequence_length": len(sequence),
                "label_length": len(labels),
            }
        )
    return rows


def write_selection(output: Path, selected: Sequence[dict], metadata: Mapping[str, object]) -> None:
    rows = selection_rows(selected)
    payload = {
        "status": "SELECTION_FROZEN_BEFORE_MODEL_LOAD",
        "protocol": "SF5_BALANCED_REPLAY_20260914",
        **metadata,
        "records": rows,
    }
    (output / "selection.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = list(rows[0])
    with (output / "selection.tsv").open("w", encoding="utf-8", newline="") as handle:
        handle.write("\t".join(fields) + "\n")
        for row in rows:
            handle.write("\t".join(str(row[field]) for field in fields) + "\n")
    (output / "STATUS").write_text("SELECTION_FROZEN_BEFORE_MODEL_LOAD\n", encoding="utf-8")


def tokenize_records(tokenizer, selected: Sequence[dict], window: int) -> Tuple[List[dict], dict]:
    """Validate the locked 1 nt to 1 token plus BOS/EOS contract."""
    encodings: List[dict] = []
    raw_token_counts = []
    input_token_counts = []
    label_counts = []
    bos_positions = set()
    eos_positions = set()
    for item in selected:
        record = item["record"]
        sequence = record["sequence"][:window]
        labels = [int(value) for value in record["labels"][:window]]
        if len(sequence) != window or len(labels) != window:
            raise ValueError(
                f"record {item['record_index']}: expected {window} bp and labels, "
                f"got {len(sequence)} and {len(labels)}"
            )
        raw_tokens = tokenizer.tokenize(sequence)
        if len(raw_tokens) != window:
            raise ValueError(
                f"record {item['record_index']}: tokenizer emitted {len(raw_tokens)} "
                f"tokens for {window} nt"
            )
        raw_ids = tokenizer.convert_tokens_to_ids(raw_tokens)
        built = tokenizer.build_inputs_with_special_tokens(raw_ids)
        if len(built) != window + 2:
            raise ValueError(
                f"record {item['record_index']}: special-token sequence has {len(built)} "
                f"tokens, expected {window + 2}"
            )
        enc = tokenizer(
            sequence,
            truncation=True,
            max_length=window + 2,
            padding="max_length",
            return_tensors="pt",
        )
        input_ids = enc["input_ids"]
        attention_mask = enc.get("attention_mask")
        if input_ids.ndim != 2 or tuple(input_ids.shape) != (1, window + 2):
            raise ValueError(
                f"record {item['record_index']}: input shape {tuple(input_ids.shape)} "
                f"does not equal (1, {window + 2})"
            )
        if attention_mask is None or int(attention_mask.sum().item()) != window + 2:
            raise ValueError(f"record {item['record_index']}: unexpected attention mask")
        bos_id = tokenizer.bos_token_id
        eos_id = tokenizer.eos_token_id
        if bos_id is None or eos_id is None:
            raise ValueError("tokenizer has no BOS/EOS IDs")
        ids = input_ids[0].tolist()
        if ids[0] != bos_id or ids[-1] != eos_id:
            raise ValueError(f"record {item['record_index']}: BOS/EOS are not at 0/{window + 1}")
        if built[0] != bos_id or built[-1] != eos_id:
            raise ValueError(f"record {item['record_index']}: built BOS/EOS mismatch")
        if any(label < 0 or label >= len(LABEL_NAMES) for label in labels):
            raise ValueError(f"record {item['record_index']}: label outside six-class contract")
        encodings.append({"input_ids": input_ids, "attention_mask": attention_mask})
        raw_token_counts.append(len(raw_tokens))
        input_token_counts.append(int(input_ids.shape[1]))
        label_counts.append(len(labels))
        bos_positions.add(0)
        eos_positions.add(window + 1)
    return encodings, {
        "tokenizer_class": tokenizer.__class__.__name__,
        "records_checked": len(selected),
        "raw_bp_per_record": int(window),
        "raw_tokens_min": min(raw_token_counts),
        "raw_tokens_max": max(raw_token_counts),
        "input_tokens_min": min(input_token_counts),
        "input_tokens_max": max(input_token_counts),
        "labeled_tokens_per_record": int(window),
        "bos_positions": sorted(bos_positions),
        "eos_positions": sorted(eos_positions),
        "special_tokens_per_record": 2,
        "one_nt_to_one_token": True,
        "contract_pass": True,
    }


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    import numpy as np

    matrix = np.zeros((len(LABEL_NAMES), len(LABEL_NAMES)), dtype=np.int64)
    np.add.at(matrix, (y_true.reshape(-1), y_pred.reshape(-1)), 1)
    return matrix


def _prf(tp: int, fp: int, fn: int, support: int) -> dict:
    precision = tp / float(tp + fp) if tp + fp else 0.0
    recall = tp / float(tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": int(support),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
    }


def metrics_for_arrays(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    import numpy as np

    matrix = confusion_matrix(y_true, y_pred)
    per_class = {}
    f1_values = []
    for label, name in LABEL_NAMES.items():
        tp = int(matrix[label, label])
        fp = int(matrix[:, label].sum() - tp)
        fn = int(matrix[label, :].sum() - tp)
        item = _prf(tp, fp, fn, int(matrix[label, :].sum()))
        item["predicted_n"] = int(matrix[:, label].sum())
        per_class[name] = item
        f1_values.append(item["f1"])

    material_true = y_true.reshape(-1) != 0
    material_pred = y_pred.reshape(-1) != 0
    tn = int((~material_true & ~material_pred).sum())
    fp = int((~material_true & material_pred).sum())
    fn = int((material_true & ~material_pred).sum())
    tp = int((material_true & material_pred).sum())
    binary = _prf(tp, fp, fn, int(material_true.sum()))
    binary.update({"tn": tn, "negative_support": int((~material_true).sum())})
    return {
        "n_positions": int(y_true.size),
        "confusion_true_rows_pred_columns": matrix.tolist(),
        "class_metrics": per_class,
        "main4_f1_all_positions": {
            LABEL_NAMES[label]: per_class[LABEL_NAMES[label]]["f1"] for label in MAIN4
        },
        "main4_macro_f1_all_positions": float(
            np.mean([per_class[LABEL_NAMES[label]]["f1"] for label in MAIN4])
        ),
        "macro_f1_all6": float(np.mean(f1_values)),
        "binary_material": binary,
        "unknown_recall": per_class["Unknown"]["recall"],
    }


def summarize_predictions(selected: Sequence[dict], labels: np.ndarray, predictions: np.ndarray) -> dict:
    import numpy as np

    species = np.asarray([item["species_code"] for item in selected])
    per_species = {}
    for species_code in TARGET_SPECIES:
        record_mask = species == species_code
        if not record_mask.any():
            raise ValueError(f"missing selected species {species_code}")
        per_species[species_code] = metrics_for_arrays(
            labels[record_mask], predictions[record_mask]
        )
        per_species[species_code]["n_records"] = int(record_mask.sum())
    return {
        "global": metrics_for_arrays(labels, predictions),
        "per_species": per_species,
    }


def _load_legacy_helpers(project_root: Path):
    pipeline_dir = project_root / "pipelines" / "PIPE-TEFM-LOCK-20260619"
    if str(pipeline_dir) not in sys.path:
        sys.path.insert(0, str(pipeline_dir))
    os.environ.setdefault("TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD", "1")
    os.environ.setdefault("WANDB_DISABLED", "true")
    from superfamily5_task import ID2LABEL as legacy_id2label  # type: ignore
    from superfamily5_task import load_model as legacy_load_model  # type: ignore

    if dict(legacy_id2label) != LABEL_NAMES:
        raise ValueError(f"legacy label map drift: {legacy_id2label}")
    return legacy_load_model


def run_one_model(
    project_root: Path,
    model_name: str,
    checkpoint: Path,
    selected: Sequence[dict],
    window: int,
    output: Path,
    device,
) -> dict:
    import numpy as np

    legacy_load_model = _load_legacy_helpers(project_root)
    model, tokenizer = legacy_load_model(str(checkpoint))
    model.to(device)
    model.eval()
    encodings, tokenization = tokenize_records(tokenizer, selected, window)
    labels = np.asarray(
        [[int(value) for value in item["record"]["labels"][:window]] for item in selected],
        dtype=np.uint8,
    )
    predictions = np.empty_like(labels)
    for index, encoding in enumerate(encodings):
        batch = {
            "input_ids": encoding["input_ids"].to(device),
            "attention_mask": encoding["attention_mask"].to(device),
        }
        with __import__("torch").inference_mode():
            result = model(**batch)
        logits = result.logits if hasattr(result, "logits") else result[0]
        if logits.ndim != 3 or logits.shape[1] != window + 2 or logits.shape[2] != len(LABEL_NAMES):
            raise ValueError(
                f"{model_name}: unexpected logits shape {tuple(logits.shape)}, "
                f"expected (1, {window + 2}, {len(LABEL_NAMES)})"
            )
        predictions[index] = (
            logits[0, 1 : window + 1, :].float().detach().cpu().numpy().argmax(axis=-1).astype(np.uint8)
        )

    raw_dir = output / "raw_predictions"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{model_name}.npz"
    np.savez_compressed(
        raw_path,
        record_indices=np.asarray([item["record_index"] for item in selected], dtype=np.int64),
        species_indices=np.asarray([item["species_rank"] for item in selected], dtype=np.int64),
        labels=labels,
        predictions=predictions,
    )
    result = summarize_predictions(selected, labels, predictions)
    result.update(
        {
            "model_name": model_name,
            "checkpoint": str(checkpoint),
            "raw_predictions_path": str(raw_path),
            "raw_predictions_retained_on_baobab": True,
            "training_called": False,
            "tokenization": tokenization,
        }
    )
    del model, tokenizer, encodings
    gc.collect()
    if getattr(device, "type", "") == "cuda":
        __import__("torch").cuda.empty_cache()
    return result


def run(args: argparse.Namespace) -> dict:
    config = json.loads(args.config.read_text(encoding="utf-8"))
    validated = validate_config(config)
    project_root = args.project_root.resolve()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite output directory: {output}")
    output.mkdir(parents=True, exist_ok=False)

    species_order = validated["species_order"]
    per_species = validated["per_species"]
    prefix_limit = validated["prefix_limit"]
    window = validated["window"]
    data_path = project_root / validated["data_relpath"]
    selected, selection = select_species_quota(
        data_path, species_order, per_species, prefix_limit
    )
    write_selection(output, selected, selection)

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("balanced SF5 replay requires a CUDA device")
    device = torch.device("cuda")
    torch.manual_seed(validated["seed"])
    model_results = {}
    for model_name, relative_checkpoint in validated["model_paths"].items():
        checkpoint = project_root / relative_checkpoint
        if not checkpoint.is_dir():
            raise FileNotFoundError(f"missing checkpoint: {checkpoint}")
        model_results[model_name] = run_one_model(
            project_root, model_name, checkpoint, selected, window, output, device
        )

    result = {
        "status": "SF5_BALANCED_REPLAY_COMPLETED",
        "protocol": validated["protocol"],
        "seed": validated["seed"],
        "inference_only": True,
        "training_called": False,
        "window": window,
        "data_path": str(data_path),
        "selection": selection,
        "models": model_results,
        "excluded_from_new_scoring": ["fruit_fly", "c_elegans", "human", "sealed_species"],
        "interpretation": {
            "old_prefix_was_not_recomputed": True,
            "balanced_replay_is_not_independent_validation": True,
            "main4_metric_definition": "Each SINE/LINE/LTR/DNA F1 is computed over all six-label valid positions; these four F1 values are averaged. BG and Unknown still contribute FP/FN to each class F1.",
            "binary_material_definition": "BG versus all five non-BG labels, including Unknown, over all selected positions.",
            "coordinates_are_trace_metadata_only": True,
        },
    }
    (output / "metrics.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "completion.json").write_text(
        json.dumps(
            {
                "status": result["status"],
                "job_id": args.job_id,
                "selected_total": selection["selected_total"],
                "model_names": list(model_results),
                "inference_only": True,
                "training_called": False,
                "metrics": str(output / "metrics.json"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "STATUS").write_text(result["status"] + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--job-id", default="unknown")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
