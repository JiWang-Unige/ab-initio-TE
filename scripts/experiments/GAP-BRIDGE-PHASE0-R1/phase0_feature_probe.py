#!/usr/bin/env python3
"""Fit and lock the pre-test feature-only Human gap-bridge probes."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


G0 = ["log1p_gap_length"]
G1 = G0 + [
    "log1p_left_run_length", "log1p_right_run_length", "log1p_span_length",
    "touches_window_seam", "log1p_nearest_window_seam_abs_distance",
    "pte_gap_mean", "pte_gap_min", "pte_gap_max",
    "pte_left_run_mean", "pte_right_run_mean", "pte_left_edge", "pte_right_edge",
    "state_background_gap_mean", "state_interior_gap_mean",
    "state_left_boundary_gap_max", "state_right_boundary_gap_max",
    "state_right_boundary_left_edge", "state_left_boundary_right_edge",
]
G2 = G1 + [
    "gap_gc_fraction", "gap_entropy", "log1p_gap_max_homopolymer",
    "left_flank_gc_fraction", "right_flank_gc_fraction",
    "flank_3mer_jaccard", "log1p_microhomology_bp",
]
FEATURE_GROUPS = {
    "G0_LENGTH": G0,
    "G1_GEOMETRY_LOGITS": G1,
    "G2_FULL_LIBRARY_FREE": G2,
}
REGULARIZATION_GRID = [0.01, 0.1, 1.0, 10.0]
TARGET_VALIDATION_ADDED_BP_PRECISION = 0.98


def number(row: dict[str, str], field: str) -> float:
    value = row.get(field, "")
    return float(value) if value not in {"", "NA"} else math.nan


def log1p_number(row: dict[str, str], field: str) -> float:
    value = number(row, field)
    return math.log1p(value) if math.isfinite(value) else math.nan


def feature_values(row: dict[str, str]) -> dict[str, float]:
    values = {
        "log1p_gap_length": log1p_number(row, "gap_length"),
        "log1p_left_run_length": log1p_number(row, "left_run_length"),
        "log1p_right_run_length": log1p_number(row, "right_run_length"),
        "log1p_span_length": log1p_number(row, "span_length"),
        "touches_window_seam": number(row, "touches_window_seam"),
        "log1p_nearest_window_seam_abs_distance": log1p_number(
            row, "nearest_window_seam_abs_distance",
        ),
        "log1p_gap_max_homopolymer": log1p_number(row, "gap_max_homopolymer"),
        "log1p_microhomology_bp": log1p_number(row, "microhomology_bp"),
    }
    for field in G2:
        if field not in values:
            values[field] = number(row, field)
    return values


def load_table(paths: list[Path]) -> dict[str, np.ndarray]:
    features: list[list[float]] = []
    targets: list[int] = []
    positive_bp: list[int] = []
    negative_bp: list[int] = []
    unknown_bp: list[int] = []
    gap_length: list[int] = []
    block: list[int] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                if row["eligible_main"] != "1":
                    continue
                values = feature_values(row)
                features.append([values[field] for field in G2])
                target = row.get("clean_target", "")
                targets.append(int(target) if target in {"0", "1"} else -1)
                positive_bp.append(int(row["gap_comparator_positive_bp"]))
                negative_bp.append(int(row["gap_comparator_negative_bp"]))
                unknown_bp.append(int(row["gap_comparator_unknown_bp"]))
                gap_length.append(int(row["gap_length"]))
                block.append(int(row["gap_start"]) // 1_000_000)
    return {
        "features": np.asarray(features, dtype=np.float64),
        "target": np.asarray(targets, dtype=np.int8),
        "positive_bp": np.asarray(positive_bp, dtype=np.int64),
        "negative_bp": np.asarray(negative_bp, dtype=np.int64),
        "unknown_bp": np.asarray(unknown_bp, dtype=np.int64),
        "gap_length": np.asarray(gap_length, dtype=np.int32),
        "block": np.asarray(block, dtype=np.int32),
    }


def choose_added_bp_threshold(
    scores: np.ndarray,
    positive_bp: np.ndarray,
    negative_bp: np.ndarray,
    target_precision: float,
) -> dict[str, float | int | str | None]:
    order = np.argsort(-scores, kind="mergesort")
    ordered_scores = scores[order]
    cumulative_positive = np.cumsum(positive_bp[order])
    cumulative_negative = np.cumsum(negative_bp[order])
    group_ends = np.flatnonzero(np.r_[ordered_scores[1:] != ordered_scores[:-1], True])
    chosen = None
    for index in group_ends:
        denominator = cumulative_positive[index] + cumulative_negative[index]
        precision = cumulative_positive[index] / denominator if denominator else math.nan
        if denominator and precision >= target_precision:
            chosen = index
    if chosen is None:
        return {
            "status": "NO_NONEMPTY_THRESHOLD",
            "threshold": 1.0,
            "selected_candidates": 0,
            "added_positive_bp": 0,
            "added_negative_bp": 0,
            "added_bp_precision": None,
        }
    denominator = cumulative_positive[chosen] + cumulative_negative[chosen]
    return {
        "status": "PASS",
        "threshold": float(ordered_scores[chosen]),
        "selected_candidates": int(chosen + 1),
        "added_positive_bp": int(cumulative_positive[chosen]),
        "added_negative_bp": int(cumulative_negative[chosen]),
        "added_bp_precision": float(cumulative_positive[chosen] / denominator),
    }


def expected_calibration_error(target: np.ndarray, scores: np.ndarray, bins: int = 10) -> float:
    total = target.size
    result = 0.0
    for index in range(bins):
        left, right = index / bins, (index + 1) / bins
        selected = (scores >= left) & (scores < right if index < bins - 1 else scores <= right)
        if selected.any():
            result += selected.mean() * abs(target[selected].mean() - scores[selected].mean())
    return float(result) if total else math.nan


def impute_and_scale(
    train: np.ndarray, other: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    median = np.nanmedian(train, axis=0)
    median[~np.isfinite(median)] = 0.0
    train_filled = np.where(np.isfinite(train), train, median)
    other_filled = np.where(np.isfinite(other), other, median)
    mean = train_filled.mean(axis=0)
    scale = train_filled.std(axis=0)
    scale[scale == 0] = 1.0
    return (train_filled - mean) / scale, (other_filled - mean) / scale, median, mean, scale


def fit_and_lock(
    train_paths: list[Path], validation_path: Path, output: Path,
) -> dict[str, object]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss

    train = load_table(train_paths)
    validation = load_table([validation_path])
    train_clean = train["target"] >= 0
    validation_clean = validation["target"] >= 0
    if set(train["target"][train_clean].tolist()) != {0, 1}:
        raise ValueError("training clean denominator must contain both relations")
    if set(validation["target"][validation_clean].tolist()) != {0, 1}:
        raise ValueError("validation clean denominator must contain both relations")

    groups: dict[str, object] = {}
    for group_name, feature_names in FEATURE_GROUPS.items():
        indices = [G2.index(field) for field in feature_names]
        train_x = train["features"][train_clean][:, indices]
        validation_x = validation["features"][:, indices]
        scaled_train, scaled_validation, median, mean, scale = impute_and_scale(
            train_x, validation_x,
        )
        train_y = train["target"][train_clean]
        validation_y = validation["target"][validation_clean]
        best = None
        for regularization_c in REGULARIZATION_GRID:
            model = LogisticRegression(
                C=regularization_c, penalty="l2", solver="lbfgs", max_iter=1000,
            )
            model.fit(scaled_train, train_y)
            scores = model.predict_proba(scaled_validation)[:, 1]
            ap = float(average_precision_score(validation_y, scores[validation_clean]))
            candidate = (ap, -regularization_c, model, scores)
            if best is None or candidate[:2] > best[:2]:
                best = candidate
        assert best is not None
        ap, negative_c, model, scores = best
        clean_scores = scores[validation_clean]
        threshold = choose_added_bp_threshold(
            scores, validation["positive_bp"], validation["negative_bp"],
            TARGET_VALIDATION_ADDED_BP_PRECISION,
        )
        groups[group_name] = {
            "features": feature_names,
            "regularization_c": -negative_c,
            "imputation_median": median.tolist(),
            "standardization_mean": mean.tolist(),
            "standardization_scale": scale.tolist(),
            "coefficient": model.coef_[0].tolist(),
            "intercept": float(model.intercept_[0]),
            "validation": {
                "clean_candidates": int(validation_clean.sum()),
                "bridge_prevalence": float(validation_y.mean()),
                "average_precision": ap,
                "ap_over_prevalence": float(ap / validation_y.mean()),
                "brier": float(brier_score_loss(validation_y, clean_scores)),
                "ece_10bin": expected_calibration_error(validation_y, clean_scores),
                "operating_threshold": threshold,
            },
        }

    result: dict[str, object] = {
        "schema": "gap_bridge_phase0_feature_lock_v1",
        "status": "PASS",
        "selection_locked": True,
        "test_labels_read": False,
        "train_paths": [str(path) for path in train_paths],
        "validation_path": str(validation_path),
        "regularization_grid": REGULARIZATION_GRID,
        "threshold_rule": "most permissive validation threshold with added-bp precision >= 0.98",
        "selected_deployment_group": "G2_FULL_LIBRARY_FREE",
        "train_clean_candidates": int(train_clean.sum()),
        "validation_eligible_candidates": int(validation["target"].size),
        "groups": groups,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fit = sub.add_parser("fit-lock")
    fit.add_argument("--train", type=Path, action="append", required=True)
    fit.add_argument("--validation", type=Path, required=True)
    fit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = fit_and_lock(args.train, args.validation, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
