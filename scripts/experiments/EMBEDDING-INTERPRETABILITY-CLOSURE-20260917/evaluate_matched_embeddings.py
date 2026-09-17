#!/usr/bin/env python3
"""Evaluate matched embeddings without test-driven tuning.

This evaluator consumes one checkpoint's cached train/val/test feature arrays
and the fixed SIB record metadata. It reports raw K-means geometry and simple
train-fitted readouts for three explicitly separated endpoints:

* known BG/SINE/LINE/LTR/DNA;
* full eight-state comparator labels.

It is intentionally an evaluator, not a feature extractor or trainer. The
caller must create one feature-root per checkpoint with identical sequences,
split files, pooling, and record ordering.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

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


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="YAML protocol file")
    ap.add_argument("--feature-root", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise SystemExit("PyYAML is required to read the protocol") from exc
    return yaml.safe_load(path.read_text())


def load_split(root: Path, split: str) -> Tuple[np.ndarray, np.ndarray, list[dict]]:
    x = np.load(root / f"{split}_features.npy", mmap_mode="r")
    y = np.load(root / f"{split}_labels.npy")
    records = [json.loads(line) for line in (root / f"{split}_records.jsonl").read_text().splitlines() if line]
    if len(x) != len(y) or len(y) != len(records):
        raise ValueError(f"{split}: feature/label/record counts disagree")
    if not np.isfinite(np.asarray(x[: min(len(x), 32)])).all():
        raise ValueError(f"{split}: non-finite feature values")
    return np.asarray(x), np.asarray(y, dtype=np.int64), records


def standardize_fit(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mean = np.asarray(x, dtype=np.float64).mean(axis=0)
    scale = np.asarray(x, dtype=np.float64).std(axis=0)
    scale[scale == 0] = 1.0
    return mean, scale


def subset_ids(y: np.ndarray, ids: Iterable[int]) -> np.ndarray:
    return np.isin(y, np.asarray(list(ids), dtype=np.int64))


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, labels: list[int]) -> dict:
    from sklearn.metrics import accuracy_score, f1_score

    # sklearn's balanced_accuracy_score has no ``labels`` argument. Restrict
    # the macro recall explicitly so predictions outside the endpoint (for
    # example an uncertain state predicted for a known-five test record) are
    # counted as errors without changing the endpoint denominator.
    from sklearn.metrics import recall_score

    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)) if len(y_true) else None,
        "balanced_accuracy": float(
            recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ) if len(y_true) else None,
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ) if len(y_true) else None,
    }


def endpoint_masks(y: np.ndarray) -> Dict[str, Tuple[np.ndarray, list[int]]]:
    """Return explicit endpoints without relabelling BG or unknown states.

    ``conditional_te_four`` is a TE-only diagnostic: both its fitting and
    evaluation masks contain SINE/LINE/LTR/DNA only.  This keeps it separate
    from detection and prevents BG from being silently folded into TE.
    """

    known = subset_ids(y, KNOWN_IDS)
    te = subset_ids(y, TE_IDS)
    return {
        "known_five": (known, [0, 1, 2, 3, 4]),
        "full_eight": (np.ones(len(y), dtype=bool), list(range(8))),
        "conditional_te_four": (te, [1, 2, 3, 4]),
    }


def run_knn(
    x_train: np.ndarray,
    y_train: np.ndarray,
    train_records: list[dict],
    x_test: np.ndarray,
    y_test: np.ndarray,
    test_records: list[dict],
) -> dict:
    from sklearn.neighbors import KNeighborsClassifier

    out = {}
    for name, (train_mask, labels) in endpoint_masks(y_train).items():
        test_mask, _ = endpoint_masks(y_test)[name]
        if not train_mask.any() or not test_mask.any():
            out[name] = {"n": 0, "accuracy": None, "balanced_accuracy": None, "macro_f1": None}
            continue
        n_neighbors = min(5, int(train_mask.sum()))
        clf = KNeighborsClassifier(n_neighbors=n_neighbors, weights="distance", metric="cosine")
        clf.fit(x_train[train_mask], y_train[train_mask])
        pred = clf.predict(x_test[test_mask])
        endpoint_metrics = classification_metrics(y_test[test_mask], pred, labels)
        species = np.asarray(
            [r.get("species_code", r.get("species", "unknown")) for r in test_records],
            dtype=object,
        )[test_mask]
        endpoint_metrics["by_species"] = {
            str(species_name): classification_metrics(
                y_test[test_mask][species == species_name],
                pred[species == species_name],
                labels,
            )
            for species_name in sorted(set(species.tolist()))
        }
        out[name] = endpoint_metrics
    # A separate binary diagnostic answers TE-versus-BG without relabelling
    # KNOWN_OTHER_TE, AMBIGUOUS_TE, or UNCLASSIFIED as BG. Those non-main4
    # states are retained in the full-eight row and are reported as excluded
    # support here.
    known_train = subset_ids(y_train, KNOWN_IDS)
    known_test = subset_ids(y_test, KNOWN_IDS)
    binary_train = (y_train[known_train] != 0).astype(np.int64)
    binary_test = (y_test[known_test] != 0).astype(np.int64)
    clf = KNeighborsClassifier(
        n_neighbors=min(5, int(known_train.sum())), weights="distance", metric="cosine"
    )
    clf.fit(x_train[known_train], binary_train)
    binary_pred = clf.predict(x_test[known_test])
    species = np.asarray(
        [r.get("species_code", r.get("species", "unknown")) for r in test_records],
        dtype=object,
    )[known_test]
    binary_metrics = classification_metrics(binary_test, binary_pred, [0, 1])
    binary_metrics["full_test_n"] = int(len(y_test))
    binary_metrics["known_test_n"] = int(known_test.sum())
    binary_metrics["excluded_unknown_test_counts"] = {
        LABEL_NAMES[i]: int((y_test == i).sum()) for i in range(5, len(LABEL_NAMES))
    }
    binary_metrics["by_species"] = {
        str(species_name): classification_metrics(
            binary_test[species == species_name],
            binary_pred[species == species_name],
            [0, 1],
        )
        for species_name in sorted(set(species.tolist()))
    }
    out["binary_te_vs_bg_known"] = binary_metrics
    return out


def run_kmeans(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, y_test: np.ndarray, seed: int) -> dict:
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    out = {}
    # K is predeclared and every fit is TRAIN-only.  Endpoint-specific fitting
    # avoids letting BG dominate the conditional TE-only geometry.
    for name, (train_mask, labels) in endpoint_masks(y_train).items():
        test_mask, _ = endpoint_masks(y_test)[name]
        if not train_mask.any() or not test_mask.any():
            out[name] = {}
            continue
        mean, scale = standardize_fit(x_train[train_mask])
        z_train = (x_train[train_mask] - mean) / scale
        z_test = (x_test[test_mask] - mean) / scale
        y_eval = y_test[test_mask]
        out[name] = {}
        for k in (2, 4, 5, 8):
            if k > len(z_train):
                continue
            km = KMeans(n_clusters=k, n_init=10, random_state=seed)
            km.fit(z_train)
            clusters = km.predict(z_test)
            out[name][f"k{k}"] = {
                "n": int(len(y_eval)),
                "ari": float(adjusted_rand_score(y_eval, clusters)),
                "nmi": float(normalized_mutual_info_score(y_eval, clusters)),
                "labels": labels,
            }
    # Score the predeclared K=2 clustering fit on the full eight-state TRAIN
    # support against binary truth only on the known five-state TEST support.
    # Non-main4 states are retained in the full-eight row and never converted
    # into BG for this diagnostic.
    mean, scale = standardize_fit(x_train)
    full_k2 = KMeans(n_clusters=2, n_init=10, random_state=seed)
    full_k2.fit((x_train - mean) / scale)
    known_test = subset_ids(y_test, KNOWN_IDS)
    binary_test = (y_test[known_test] != 0).astype(np.int64)
    binary_clusters = full_k2.predict((x_test[known_test] - mean) / scale)
    out["binary_te_vs_bg_known_from_full_k2"] = {
        "n": int(known_test.sum()),
        "full_test_n": int(len(y_test)),
        "excluded_unknown_test_counts": {
            LABEL_NAMES[i]: int((y_test == i).sum()) for i in range(5, len(LABEL_NAMES))
        },
        "ari": float(adjusted_rand_score(binary_test, binary_clusters)),
        "nmi": float(normalized_mutual_info_score(binary_test, binary_clusters)),
        "fit_scope": "full_eight_train",
        "k": 2,
    }
    return out


def main() -> None:
    args = parse_args()
    cfg = load_yaml(Path(args.config))
    train_x, train_y, train_records = load_split(args.feature_root, "train")
    test_x, test_y, test_records = load_split(args.feature_root, "test")
    if train_x.shape[1] != test_x.shape[1]:
        raise ValueError("train/test embedding dimensions disagree")

    metadata_path = args.feature_root / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)
    feature_meta = json.loads(metadata_path.read_text())
    expected_pooling = "attention_mask_mean_excluding_padding_and_special_tokens"
    if feature_meta.get("pooling") != expected_pooling:
        raise ValueError(
            "feature cache pooling is not the frozen special-token-free contract: "
            f"{feature_meta.get('pooling')!r}"
        )
    results = {
        "protocol": cfg.get("experiment_id"),
        "feature_root": str(args.feature_root),
        "seed": args.seed,
        "feature_dim": int(train_x.shape[1]),
        "counts": {
            "train": int(len(train_y)),
            "test": int(len(test_y)),
            "test_labels": {LABEL_NAMES[i]: int((test_y == i).sum()) for i in range(8)},
        },
        "pooling_contract": feature_meta.get("pooling"),
        "supervised_knn5": run_knn(train_x, train_y, train_records, test_x, test_y, test_records),
        "unsupervised_kmeans": run_kmeans(train_x, train_y, test_x, test_y, args.seed),
        "umap_is_primary_endpoint": False,
        "test_records_species": sorted(
            {r.get("species_code", r.get("species", "unknown")) for r in test_records}
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "metrics.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
