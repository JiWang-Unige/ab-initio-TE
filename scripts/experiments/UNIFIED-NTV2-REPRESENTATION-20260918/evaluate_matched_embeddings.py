#!/usr/bin/env python3
"""Evaluate one cached matched NTv2 representation.

All fits are train-only and all endpoints preserve their declared support:
known-five (BG + four main TE classes), full-eight, and conditional TE-four.
The binary row is a known-support TE-versus-BG diagnostic.  K-means is
annotation-filtered for the conditional endpoints; it is an unsupervised
partition fit, but its score still uses the supplied labels and is therefore
not label-free biological discovery.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

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
SPLITS = ("train", "val", "test")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--feature-root", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise SystemExit("PyYAML is required to read the protocol") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_split(root: Path, split: str) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    x = np.load(root / f"{split}_features.npy", mmap_mode="r")
    y = np.load(root / f"{split}_labels.npy")
    records = [
        json.loads(line)
        for line in (root / f"{split}_records.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(x) != len(y) or len(y) != len(records):
        raise ValueError(f"{split}: feature/label/record counts disagree")
    if not np.isfinite(np.asarray(x[: min(len(x), 32)])).all():
        raise ValueError(f"{split}: non-finite feature values")
    return np.asarray(x), np.asarray(y, dtype=np.int64), records


def endpoint_masks(y: np.ndarray) -> dict[str, tuple[np.ndarray, list[int]]]:
    known = np.isin(y, KNOWN_IDS)
    te = np.isin(y, TE_IDS)
    return {
        "known_five": (known, [0, 1, 2, 3, 4]),
        "full_eight": (np.ones(len(y), dtype=bool), list(range(8))),
        "conditional_te_four": (te, [1, 2, 3, 4]),
    }


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, labels: list[int]) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)) if len(y_true) else None,
        "balanced_accuracy": float(
            recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ) if len(y_true) else None,
        "macro_precision": float(
            precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ) if len(y_true) else None,
        "macro_recall": float(
            recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ) if len(y_true) else None,
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ) if len(y_true) else None,
        "per_class": {
            LABEL_NAMES[label]: {
                "support": int((y_true == label).sum()),
                "precision": float(
                    precision_score(y_true, y_pred, labels=[label], average="macro", zero_division=0)
                ),
                "recall": float(
                    recall_score(y_true, y_pred, labels=[label], average="macro", zero_division=0)
                ),
                "f1": float(
                    f1_score(y_true, y_pred, labels=[label], average="macro", zero_division=0)
                ),
            }
            for label in labels
        },
    }


def species_array(records: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray(
        [row.get("species_code", row.get("species", "unknown")) for row in records], dtype=object
    )


def by_species(y_true: np.ndarray, y_pred: np.ndarray, records: list[dict[str, Any]], labels: list[int]) -> dict[str, Any]:
    species = species_array(records)
    return {
        str(name): classification_metrics(y_true[species == name], y_pred[species == name], labels)
        for name in sorted(set(species.tolist()))
    }


def run_knn(
    x_train: np.ndarray,
    y_train: np.ndarray,
    train_records: list[dict[str, Any]],
    x_test: np.ndarray,
    y_test: np.ndarray,
    test_records: list[dict[str, Any]],
) -> dict[str, Any]:
    from sklearn.neighbors import KNeighborsClassifier

    out: dict[str, Any] = {}
    train_eps = endpoint_masks(y_train)
    test_eps = endpoint_masks(y_test)
    for name, (train_mask, labels) in train_eps.items():
        test_mask, _ = test_eps[name]
        if not train_mask.any() or not test_mask.any():
            out[name] = {"n": 0, "accuracy": None, "macro_f1": None}
            continue
        clf = KNeighborsClassifier(
            n_neighbors=min(5, int(train_mask.sum())), weights="distance", metric="cosine"
        )
        clf.fit(x_train[train_mask], y_train[train_mask])
        pred = clf.predict(x_test[test_mask])
        result = classification_metrics(y_test[test_mask], pred, labels)
        result["fit_scope"] = "train_only"
        result["by_species"] = by_species(y_test[test_mask], pred, [test_records[i] for i in np.flatnonzero(test_mask)], labels)
        out[name] = result

    # This binary diagnostic intentionally excludes all three non-main4 states
    # from both fit and test support instead of silently calling them BG.
    known_train = np.isin(y_train, KNOWN_IDS)
    known_test = np.isin(y_test, KNOWN_IDS)
    binary_train = (y_train[known_train] != 0).astype(np.int64)
    binary_test = (y_test[known_test] != 0).astype(np.int64)
    clf = KNeighborsClassifier(
        n_neighbors=min(5, int(known_train.sum())), weights="distance", metric="cosine"
    )
    clf.fit(x_train[known_train], binary_train)
    binary_pred = clf.predict(x_test[known_test])
    result = classification_metrics(binary_test, binary_pred, [0, 1])
    result.update(
        {
            "fit_scope": "known_five_train_only",
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
    out["binary_te_vs_bg_known"] = result
    return out


def fit_standardizer(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.asarray(x, dtype=np.float64).mean(axis=0)
    scale = np.asarray(x, dtype=np.float64).std(axis=0)
    scale[scale == 0] = 1.0
    return mean, scale


def run_kmeans(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, y_test: np.ndarray, seed: int) -> dict[str, Any]:
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    out: dict[str, Any] = {}
    train_eps = endpoint_masks(y_train)
    test_eps = endpoint_masks(y_test)
    for name, (train_mask, labels) in train_eps.items():
        test_mask, _ = test_eps[name]
        if not train_mask.any() or not test_mask.any():
            out[name] = {}
            continue
        mean, scale = fit_standardizer(x_train[train_mask])
        z_train = (x_train[train_mask] - mean) / scale
        z_test = (x_test[test_mask] - mean) / scale
        out[name] = {
            "fit_scope": "train_only_annotation_filtered_support",
            "annotation_filtered_support": name != "full_eight",
            "label_free_fit_but_label_scored": True,
        }
        for k in (2, 4, 5, 8):
            if k > len(z_train):
                continue
            km = KMeans(n_clusters=k, n_init=10, random_state=seed)
            km.fit(z_train)
            clusters = km.predict(z_test)
            out[name][f"k{k}"] = {
                "n": int(len(y_test[test_mask])),
                "ari": float(adjusted_rand_score(y_test[test_mask], clusters)),
                "nmi": float(normalized_mutual_info_score(y_test[test_mask], clusters)),
                "labels": labels,
            }

    mean, scale = fit_standardizer(x_train)
    full_k2 = KMeans(n_clusters=2, n_init=10, random_state=seed)
    full_k2.fit((x_train - mean) / scale)
    known_test = np.isin(y_test, KNOWN_IDS)
    binary_test = (y_test[known_test] != 0).astype(np.int64)
    clusters = full_k2.predict((x_test[known_test] - mean) / scale)
    out["binary_te_vs_bg_known_from_full_k2"] = {
        "n": int(known_test.sum()),
        "full_test_n": int(len(y_test)),
        "excluded_unknown_test_counts": {
            LABEL_NAMES[i]: int((y_test == i).sum()) for i in range(5, len(LABEL_NAMES))
        },
        "ari": float(adjusted_rand_score(binary_test, clusters)),
        "nmi": float(normalized_mutual_info_score(binary_test, clusters)),
        "fit_scope": "full_eight_train",
        "k": 2,
        "label_free_fit_but_label_scored": True,
    }
    return out


def run_logistic(
    x_train: np.ndarray,
    y_train: np.ndarray,
    train_records: list[dict[str, Any]],
    x_test: np.ndarray,
    y_test: np.ndarray,
    test_records: list[dict[str, Any]],
) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression

    out: dict[str, Any] = {}
    train_eps = endpoint_masks(y_train)
    test_eps = endpoint_masks(y_test)
    for name, (train_mask, labels) in train_eps.items():
        test_mask, _ = test_eps[name]
        if not train_mask.any() or not test_mask.any():
            out[name] = {"n": 0, "accuracy": None, "macro_f1": None}
            continue
        mean, scale = fit_standardizer(x_train[train_mask])
        z_train = (x_train[train_mask] - mean) / scale
        z_test = (x_test[test_mask] - mean) / scale
        clf = LogisticRegression(
            max_iter=1000,
            solver="lbfgs",
            multi_class="auto",
            random_state=42,
        )
        clf.fit(z_train, y_train[train_mask])
        pred = clf.predict(z_test)
        result = classification_metrics(y_test[test_mask], pred, labels)
        result["fit_scope"] = "train_only_standardized"
        result["by_species"] = by_species(y_test[test_mask], pred, [test_records[i] for i in np.flatnonzero(test_mask)], labels)
        out[name] = result

    known_train = np.isin(y_train, KNOWN_IDS)
    known_test = np.isin(y_test, KNOWN_IDS)
    mean, scale = fit_standardizer(x_train[known_train])
    clf = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=42)
    clf.fit(
        (x_train[known_train] - mean) / scale,
        (y_train[known_train] != 0).astype(np.int64),
    )
    pred = clf.predict((x_test[known_test] - mean) / scale)
    result = classification_metrics((y_test[known_test] != 0).astype(np.int64), pred, [0, 1])
    result.update(
        {
            "fit_scope": "known_five_train_only_standardized",
            "full_test_n": int(len(y_test)),
            "known_test_n": int(known_test.sum()),
            "excluded_unknown_test_counts": {
                LABEL_NAMES[i]: int((y_test == i).sum()) for i in range(5, len(LABEL_NAMES))
            },
            "by_species": by_species(
                (y_test[known_test] != 0).astype(np.int64),
                pred,
                [test_records[i] for i in np.flatnonzero(known_test)],
                [0, 1],
            ),
        }
    )
    out["binary_te_vs_bg_known"] = result
    return out


def sequence_confounders(records: list[dict[str, Any]], y: np.ndarray) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for record, label in zip(records, y.tolist()):
        seq = str(record.get("sequence", "")).upper()
        length = len(seq)
        gc = (seq.count("G") + seq.count("C")) / length if length else 0.0
        n_fraction = seq.count("N") / length if length else 0.0
        rows.append(
            {
                "species_code": record.get("species_code", record.get("species", "unknown")),
                "label": int(label),
                "gc_fraction": gc,
                "N_fraction": n_fraction,
                "sequence_length_bp": length,
                # SIB labels are window-level states, not per-base masks.  The
                # declared TE fraction is consequently a binary window
                # indicator rather than an invented base-level fraction.
                "TE_fraction": float(int(label) != 0),
            }
        )
    out: dict[str, Any] = {"definition": "TE_fraction is window-level label != BG; sequence_length is raw bp"}
    arr = {key: np.asarray([row[key] for row in rows], dtype=float) for key in ("gc_fraction", "N_fraction", "sequence_length_bp", "TE_fraction")}
    out["pooled"] = {
        key: {"mean": float(value.mean()), "std": float(value.std()), "min": float(value.min()), "max": float(value.max())}
        for key, value in arr.items()
    }
    by_label: dict[str, Any] = {}
    for label, name in enumerate(LABEL_NAMES):
        mask = y == label
        if not mask.any():
            by_label[name] = {"n": 0}
            continue
        by_label[name] = {
            "n": int(mask.sum()),
            **{
                key: {
                    "mean": float(value[mask].mean()),
                    "std": float(value[mask].std()),
                }
                for key, value in arr.items()
            },
        }
    out["by_label"] = by_label
    out["by_species"] = {}
    species = np.asarray([row["species_code"] for row in rows], dtype=object)
    for species_name in sorted(set(species.tolist())):
        mask = species == species_name
        out["by_species"][species_name] = {
            "n": int(mask.sum()),
            "label_counts": {LABEL_NAMES[i]: int(((y == i) & mask).sum()) for i in range(8)},
            **{
                key: {"mean": float(value[mask].mean()), "std": float(value[mask].std())}
                for key, value in arr.items()
            },
        }
    return out


def main() -> None:
    args = parse_args()
    cfg = load_yaml(args.config)
    feature_meta = json.loads((args.feature_root / "metadata.json").read_text(encoding="utf-8"))
    expected_pooling = "attention_mask_mean_excluding_structural_special_tokens_and_padding"
    if feature_meta.get("pooling") != expected_pooling:
        raise ValueError(f"feature cache pooling mismatch: {feature_meta.get('pooling')!r}")
    loaded = {split: load_split(args.feature_root, split) for split in SPLITS}
    train_x, train_y, train_records = loaded["train"]
    val_x, val_y, val_records = loaded["val"]
    test_x, test_y, test_records = loaded["test"]
    if len(train_x) != 1843 or len(val_x) != 809 or len(test_x) != 1580:
        raise ValueError("SIB split count mismatch")
    if train_x.shape[1] != test_x.shape[1] or train_x.shape[1] != val_x.shape[1]:
        raise ValueError("embedding dimensions disagree")
    # Extraction writes record keys for the same row order.  The direct
    # identity check below detects accidental feature/label misalignment.
    for split, rows in (("train", train_records), ("val", val_records), ("test", test_records)):
        if any(int(row["label"]) != int(loaded[split][1][i]) for i, row in enumerate(rows)):
            raise ValueError(f"{split}: cached record labels are misaligned")

    results: dict[str, Any] = {
        "protocol": cfg.get("experiment_id"),
        "feature_root": str(args.feature_root),
        "seed": args.seed,
        "feature_dim": int(train_x.shape[1]),
        "counts": {
            "train": int(len(train_y)),
            "val": int(len(val_y)),
            "test": int(len(test_y)),
            "test_labels": {LABEL_NAMES[i]: int((test_y == i).sum()) for i in range(8)},
        },
        "pooling_contract": feature_meta.get("pooling"),
        "supervised_knn5": run_knn(train_x, train_y, train_records, test_x, test_y, test_records),
        "supervised_linear_probe": run_logistic(train_x, train_y, train_records, test_x, test_y, test_records),
        "unsupervised_kmeans": run_kmeans(train_x, train_y, test_x, test_y, args.seed),
        "confounders": {
            "train": sequence_confounders(train_records, train_y),
            "val": sequence_confounders(val_records, val_y),
            "test": sequence_confounders(test_records, test_y),
        },
        "umap_is_primary_endpoint": False,
        "test_records_species": sorted({str(row.get("species_code", "unknown")) for row in test_records}),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "metrics.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
