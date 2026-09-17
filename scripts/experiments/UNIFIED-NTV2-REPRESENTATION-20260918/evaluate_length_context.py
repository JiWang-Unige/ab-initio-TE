#!/usr/bin/env python3
"""Score the bounded 512/2048/4096 context diagnostic.

The selected source rows are frozen before this script runs.  Every context
length uses the same target labels and the same train/DEV support; validation
rows are reported for composition/support context but never used for model
selection.  The composition baseline is a train-fitted standardized logistic
readout over target/context GC and N fractions plus context length.
"""
from __future__ import annotations

import argparse
import json
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
KNOWN_IDS = np.asarray([0, 1, 2, 3, 4], dtype=np.int64)
TE_IDS = np.asarray([1, 2, 3, 4], dtype=np.int64)
CONTEXTS = (512, 2048, 4096)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()


def metrics(y_true: np.ndarray, y_pred: np.ndarray, labels: list[int]) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)) if len(y_true) else None,
        "macro_precision": float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)) if len(y_true) else None,
        "macro_recall": float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)) if len(y_true) else None,
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)) if len(y_true) else None,
        "per_class": {
            LABEL_NAMES[label]: {
                "support": int((y_true == label).sum()),
                "precision": float(precision_score(y_true, y_pred, labels=[label], average="macro", zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, labels=[label], average="macro", zero_division=0)),
                "f1": float(f1_score(y_true, y_pred, labels=[label], average="macro", zero_division=0)),
            }
            for label in labels
        },
    }


def endpoint_masks(y: np.ndarray) -> dict[str, tuple[np.ndarray, list[int]]]:
    return {
        "known_five": (np.isin(y, KNOWN_IDS), [0, 1, 2, 3, 4]),
        "full_eight": (np.ones(len(y), dtype=bool), list(range(8))),
        "conditional_te_four": (np.isin(y, TE_IDS), [1, 2, 3, 4]),
    }


def species_array(records: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([str(row["species_code"]) for row in records], dtype=object)


def by_species(y: np.ndarray, pred: np.ndarray, records: list[dict[str, Any]], labels: list[int]) -> dict[str, Any]:
    species = species_array(records)
    return {
        name: metrics(y[species == name], pred[species == name], labels)
        for name in sorted(set(species.tolist()))
    }


def standardize_fit(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0] = 1.0
    return mean, scale


def supervised_readouts(
    x_train: np.ndarray,
    y_train: np.ndarray,
    train_records: list[dict[str, Any]],
    x_test: np.ndarray,
    y_test: np.ndarray,
    test_records: list[dict[str, Any]],
) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier

    out: dict[str, Any] = {}
    train_eps = endpoint_masks(y_train)
    test_eps = endpoint_masks(y_test)
    for readout_name, model_factory in (
        ("knn5_cosine", lambda: KNeighborsClassifier(n_neighbors=5, weights="distance", metric="cosine")),
        ("linear_logistic", lambda: LogisticRegression(max_iter=1000, solver="lbfgs", random_state=42)),
    ):
        endpoints: dict[str, Any] = {}
        for endpoint, (train_mask, labels) in train_eps.items():
            test_mask, _ = test_eps[endpoint]
            if not train_mask.any() or not test_mask.any():
                endpoints[endpoint] = {"n": 0, "macro_f1": None}
                continue
            if readout_name == "linear_logistic":
                mean, scale = standardize_fit(x_train[train_mask])
                fit_x = (x_train[train_mask] - mean) / scale
                pred_x = (x_test[test_mask] - mean) / scale
            else:
                fit_x = x_train[train_mask]
                pred_x = x_test[test_mask]
            classifier = model_factory()
            classifier.set_params(n_neighbors=min(5, int(train_mask.sum()))) if readout_name == "knn5_cosine" else None
            classifier.fit(fit_x, y_train[train_mask])
            pred = classifier.predict(pred_x)
            result = metrics(y_test[test_mask], pred, labels)
            result["fit_scope"] = "TRAIN_only"
            result["by_species"] = by_species(
                y_test[test_mask], pred, [test_records[i] for i in np.flatnonzero(test_mask)], labels
            )
            endpoints[endpoint] = result

        known_train = np.isin(y_train, KNOWN_IDS)
        known_test = np.isin(y_test, KNOWN_IDS)
        binary_train = (y_train[known_train] != 0).astype(np.int64)
        binary_test = (y_test[known_test] != 0).astype(np.int64)
        if readout_name == "linear_logistic":
            mean, scale = standardize_fit(x_train[known_train])
            fit_x = (x_train[known_train] - mean) / scale
            pred_x = (x_test[known_test] - mean) / scale
        else:
            fit_x = x_train[known_train]
            pred_x = x_test[known_test]
        classifier = model_factory()
        classifier.set_params(n_neighbors=min(5, int(known_train.sum()))) if readout_name == "knn5_cosine" else None
        classifier.fit(fit_x, binary_train)
        binary_pred = classifier.predict(pred_x)
        binary_result = metrics(binary_test, binary_pred, [0, 1])
        binary_result.update(
            {
                "fit_scope": "known_five_TRAIN_only",
                "full_test_n": int(len(y_test)),
                "known_test_n": int(known_test.sum()),
                "excluded_unknown_test_counts": {
                    LABEL_NAMES[i]: int((y_test == i).sum()) for i in range(5, len(LABEL_NAMES))
                },
                "by_species": by_species(
                    binary_test,
                    binary_pred,
                    [test_records[i] for i in np.flatnonzero(known_test)],
                    [0, 1],
                ),
            }
        )
        endpoints["binary_te_vs_bg_known"] = binary_result
        out[readout_name] = endpoints
    return out


def load_composition(path: Path) -> np.ndarray:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    keys = ("target_gc_fraction", "target_N_fraction", "context_gc_fraction", "context_N_fraction", "context_length_bp")
    return np.asarray([[float(row[key]) for key in keys] for row in rows], dtype=np.float32)


def composition_baseline(
    c_train: np.ndarray,
    y_train: np.ndarray,
    c_test: np.ndarray,
    y_test: np.ndarray,
) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression

    known_train = np.isin(y_train, KNOWN_IDS)
    known_test = np.isin(y_test, KNOWN_IDS)
    mean, scale = standardize_fit(c_train[known_train])
    classifier = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=42)
    classifier.fit((c_train[known_train] - mean) / scale, (y_train[known_train] != 0).astype(np.int64))
    pred = classifier.predict((c_test[known_test] - mean) / scale)
    result = metrics((y_test[known_test] != 0).astype(np.int64), pred, [0, 1])
    result.update(
        {
            "features": ["target_gc_fraction", "target_N_fraction", "context_gc_fraction", "context_N_fraction", "context_length_bp"],
            "fit_scope": "known_five_TRAIN_only_standardized",
            "full_test_n": int(len(y_test)),
            "known_test_n": int(known_test.sum()),
            "excluded_unknown_test_counts": {LABEL_NAMES[i]: int((y_test == i).sum()) for i in range(5, len(LABEL_NAMES))},
        }
    )
    return result


def main() -> None:
    args = parse_args()
    manifest = json.loads((args.input_root / "input_manifest.json").read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (args.input_root / "records.jsonl").read_text(encoding="utf-8").splitlines() if line]
    labels = np.asarray([int(row["target_label"]) for row in records], dtype=np.int64)
    split = np.asarray([row["split"] for row in records], dtype=object)
    train_mask = split == "train"
    test_mask = split == "test"
    val_mask = split == "val"
    if int(train_mask.sum()) != 384 or int(val_mask.sum()) != 192 or int(test_mask.sum()) != 192:
        raise ValueError("length diagnostic split counts do not match 384/192/192")
    support = {
        name: {
            "n": int(mask.sum()),
            "label_counts": {LABEL_NAMES[i]: int((labels[mask] == i).sum()) for i in range(8)},
            "species_counts": {
                species: int(sum(mask[j] and records[j]["species_code"] == species for j in range(len(records))))
                for species in sorted({row["species_code"] for row in records})
            },
        }
        for name, mask in (("train", train_mask), ("val", val_mask), ("test", test_mask))
    }
    results: dict[str, Any] = {
        "protocol": manifest.get("protocol"),
        "input_root": str(args.input_root),
        "seed": args.seed,
        "target_definition": manifest.get("target_span_definition"),
        "target_pooling": manifest.get("target_pooling"),
        "offset_mapping": manifest.get("offset_mapping"),
        "support": support,
        "models": {},
        "no_validation_tuning": True,
    }
    for model_id in ("pretrained", "binary_D", "class_D_last2"):
        model_root = args.input_root / model_id
        model_results: dict[str, Any] = {}
        for context_length in CONTEXTS:
            x = np.load(model_root / f"context_{context_length}_features.npy")
            if len(x) != len(records):
                raise ValueError(f"{model_id}/{context_length}: feature rows disagree with manifest")
            composition = load_composition(model_root / f"context_{context_length}_composition.jsonl")
            model_results[str(context_length)] = {
                "n": int(len(x)),
                "supervised": supervised_readouts(
                    x[train_mask], labels[train_mask], [records[i] for i in np.flatnonzero(train_mask)],
                    x[test_mask], labels[test_mask], [records[i] for i in np.flatnonzero(test_mask)],
                ),
                "composition_baseline": composition_baseline(
                    composition[train_mask], labels[train_mask], composition[test_mask], labels[test_mask]
                ),
            }
        results["models"][model_id] = model_results
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "metrics.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
