#!/usr/bin/env python3
"""Train-only linear and sequence-composition diagnostics for legacy features.

This reuses already completed GENERanno and NTv2 feature caches.  It does not
rerun extraction or tune a threshold.  The binary denominator is the same
known-five SIB support used for the earlier 5-NN `.522` diagnostic.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np


LABEL_NAMES = ["BG", "SINE", "LINE", "LTR", "DNA", "KNOWN_OTHER_TE", "AMBIGUOUS_TE", "UNCLASSIFIED"]
KNOWN_IDS = np.asarray([0, 1, 2, 3, 4], dtype=np.int64)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--model", action="append", required=True, help="MODEL_ID=FEATURE_ROOT")
    ap.add_argument("--out-json", type=Path, required=True)
    return ap.parse_args()


def metric(y: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

    labels = [0, 1]
    matrix = confusion_matrix(y, pred, labels=labels)
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_precision": float(precision_score(y, pred, labels=labels, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y, pred, labels=labels, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y, pred, labels=labels, average="macro", zero_division=0)),
        "confusion_rows_true_cols_pred": matrix.tolist(),
        "per_class": {
            name: {
                "support": int((y == label).sum()),
                "precision": float(precision_score(y, pred, labels=[label], average="macro", zero_division=0)),
                "recall": float(recall_score(y, pred, labels=[label], average="macro", zero_division=0)),
                "f1": float(f1_score(y, pred, labels=[label], average="macro", zero_division=0)),
            }
            for label, name in ((0, "BG"), (1, "TE"))
        },
    }


def load_raw_records(data_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in ("train", "val", "test"):
        with gzip.open(data_dir / split / "data.jsonl.gz", "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("species_code"),
        row.get("chr", row.get("chrom")),
        int(row["start"]),
        int(row["end"]),
        row.get("source_record", row.get("source_chunk", "")),
    )


def composition(rows: list[dict[str, Any]]) -> np.ndarray:
    values = []
    for row in rows:
        sequence = str(row["sequence"]).upper()
        length = len(sequence)
        values.append(
            [
                (sequence.count("G") + sequence.count("C")) / length,
                sequence.count("N") / length,
                float(length),
            ]
        )
    return np.asarray(values, dtype=np.float32)


def standardized_logistic(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression

    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale == 0] = 1.0
    model = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=42)
    model.fit((x_train - mean) / scale, y_train)
    return model.predict((x_test - mean) / scale)


def main() -> None:
    args = parse_args()
    model_specs = []
    for raw in args.model:
        model_id, root = raw.split("=", 1)
        model_specs.append((model_id, Path(root)))
    raw_rows = load_raw_records(args.data_dir)
    raw_keys = [key(row) for row in raw_rows]
    result: dict[str, Any] = {
        "protocol": "UNIFIED-NTV2-REPRESENTATION-20260918",
        "diagnostic": "legacy_known_five_binary_linear_and_composition",
        "denominator": {
            "split": "fixed SIB test known-five support",
            "test_full_n": 1580,
            "test_known_n": 1281,
            "BG": 360,
            "TE": 921,
            "excluded": {name: None for name in LABEL_NAMES[5:]},
        },
        "models": {},
        "composition_features": ["GC_fraction", "N_fraction", "sequence_length_bp"],
        "no_threshold_or_hyperparameter_tuning": True,
    }
    for model_id, feature_root in model_specs:
        train_x = np.load(feature_root / "train_features.npy")
        test_x = np.load(feature_root / "test_features.npy")
        train_y_full = np.load(feature_root / "train_labels.npy").astype(np.int64)
        test_y_full = np.load(feature_root / "test_labels.npy").astype(np.int64)
        train_records = [json.loads(line) for line in (feature_root / "train_records.jsonl").read_text().splitlines() if line]
        test_records = [json.loads(line) for line in (feature_root / "test_records.jsonl").read_text().splitlines() if line]
        if [key(row) for row in train_records] != raw_keys[: len(train_records)]:
            raise ValueError(f"{model_id}: train feature record order does not match SIB raw order")
        if [key(row) for row in test_records] != raw_keys[-len(test_records) :]:
            raise ValueError(f"{model_id}: test feature record order does not match SIB raw order")
        train_mask = np.isin(train_y_full, KNOWN_IDS)
        test_mask = np.isin(test_y_full, KNOWN_IDS)
        y_train = (train_y_full[train_mask] != 0).astype(np.int64)
        y_test = (test_y_full[test_mask] != 0).astype(np.int64)
        pred_linear = standardized_logistic(train_x[train_mask], y_train, test_x[test_mask])
        test_records_known = [test_records[index] for index in np.flatnonzero(test_mask)]
        # Feature record caches intentionally omit sequence strings.  Reuse
        # the already validated raw SIB rows in the same split order for the
        # GC/N/length baseline.
        raw_train_rows = raw_rows[: len(train_records)]
        raw_test_rows = raw_rows[-len(test_records) :]
        composition_train = composition(raw_train_rows)[train_mask]
        composition_test = composition(raw_test_rows)[test_mask]
        pred_composition = standardized_logistic(composition_train, y_train, composition_test)
        result["models"][model_id] = {
            "feature_dim": int(train_x.shape[1]),
            "linear_probe": {
                **metric(y_test, pred_linear),
                "fit_scope": "known_five_TRAIN_only_standardized",
            },
            "composition_baseline": {
                **metric(y_test, pred_composition),
                "fit_scope": "known_five_TRAIN_only_standardized",
                "features": ["GC_fraction", "N_fraction", "sequence_length_bp"],
            },
        }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
