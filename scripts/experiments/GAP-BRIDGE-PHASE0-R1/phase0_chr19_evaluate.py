#!/usr/bin/env python3
"""Apply the locked Phase-0 probe to the one-use, explicitly labeled chr19 test."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import random
from pathlib import Path

import numpy as np


_PROBE_SPEC = importlib.util.spec_from_file_location(
    "phase0_chr19_feature_probe", Path(__file__).with_name("phase0_feature_probe.py"),
)
if _PROBE_SPEC is None or _PROBE_SPEC.loader is None:
    raise RuntimeError("cannot load the frozen Phase-0 feature probe")
_PROBE = importlib.util.module_from_spec(_PROBE_SPEC)
_PROBE_SPEC.loader.exec_module(_PROBE)
FEATURE_GROUPS = _PROBE.FEATURE_GROUPS
feature_values = _PROBE.feature_values


GROUP_NAMES = tuple(FEATURE_GROUPS)
BRIDGE = "COMPARATOR_BRIDGE_SUPPORTED"
SEPARATION = "COMPARATOR_SEPARATION_SUPPORTED"
AMBIGUOUS = "COMPARATOR_RELATION_AMBIGUOUS"
BLOCK_SIZE = 1_000_000
BOOTSTRAP_REPLICATES = 1_000
BOOTSTRAP_SEED = 20260901
REQUIRED_LOCK_FIELDS = (
    "status", "selection_locked", "test_labels_read", "test_label_release_allowed",
    "groups", "selected_deployment_group", "baselines",
)
UNAVAILABLE_METRICS = [
    "whole_mask_bp_precision", "whole_mask_bp_recall", "whole_mask_bp_f1", "whole_mask_mcc",
    "split_rate", "fragments_per_truth", "internal_gap_count", "internal_gap_mass",
    "missed_rate", "terminal_omission_rate",
    "gene_overlap_added_negative_bp", "gene_overlap_added_bp_precision",
    "canonical_splice_core_negative_bp", "callable_cds_negative_fill_rate",
    "affected_genes", "affected_exons",
]


def _finite_array(values: object, field: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"locked parameter {field} must be a finite one-dimensional array")
    return array


def load_lock(path: Path) -> dict[str, object]:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(lock, dict):
        raise ValueError("feature lock must be a JSON object")
    missing = [field for field in REQUIRED_LOCK_FIELDS if field not in lock]
    if missing:
        raise ValueError(f"feature lock missing required fields: {missing}")
    if lock["status"] != "PASS_TO_TEST":
        raise ValueError("chr19 evaluation requires feature lock status=PASS_TO_TEST")
    if lock["selection_locked"] is not True:
        raise ValueError("chr19 evaluation requires selection_locked=true")
    if lock["test_labels_read"] is not False:
        raise ValueError("chr19 evaluation requires test_labels_read=false in the pre-test lock")
    if lock["test_label_release_allowed"] is not True:
        raise ValueError("chr19 evaluation requires test_label_release_allowed=true")
    if lock["selected_deployment_group"] != "G2_FULL_LIBRARY_FREE":
        raise ValueError("the frozen deployment group must remain G2_FULL_LIBRARY_FREE")
    groups = lock["groups"]
    if not isinstance(groups, dict) or set(groups) != set(GROUP_NAMES):
        raise ValueError("feature lock must contain exactly the frozen G0, G1 and G2 groups")
    for group_name in GROUP_NAMES:
        group = groups[group_name]
        if not isinstance(group, dict):
            raise ValueError(f"locked group is not an object: {group_name}")
        if group.get("features") != FEATURE_GROUPS[group_name]:
            raise ValueError(f"locked feature list differs from the frozen {group_name} list")
        for field in ("coefficient", "imputation_median", "standardization_mean", "standardization_scale"):
            _finite_array(group.get(field), f"{group_name}.{field}")
        if not isinstance(group.get("intercept"), (int, float)) or not math.isfinite(float(group["intercept"])):
            raise ValueError(f"locked parameter {group_name}.intercept must be finite")
        validation = group.get("validation")
        if not isinstance(validation, dict) or not isinstance(validation.get("average_precision"), (int, float)):
            raise ValueError(f"locked validation AP is missing for {group_name}")
        operating = validation.get("operating_threshold")
        if not isinstance(operating, dict):
            raise ValueError(f"locked operating threshold is missing for {group_name}")
        threshold = operating.get("threshold")
        threshold_status = operating.get("status")
        if group_name == "G2_FULL_LIBRARY_FREE":
            if threshold_status != "PASS" or not isinstance(threshold, (int, float)):
                raise ValueError("G2 requires a PASS validation operating threshold")
            if not math.isfinite(float(threshold)):
                raise ValueError("G2 operating threshold is non-finite")
        elif threshold_status == "PASS":
            if not isinstance(threshold, (int, float)) or not math.isfinite(float(threshold)):
                raise ValueError(f"PASS operating threshold is invalid for {group_name}")
        elif threshold is not None:
            raise ValueError(f"non-PASS operating threshold must be null for {group_name}")
    baselines = lock["baselines"]
    if not isinstance(baselines, dict):
        raise ValueError("feature lock baselines must be an object")
    simple = baselines.get("simple_gap_length_cutoff")
    if not isinstance(simple, dict):
        raise ValueError("frozen simple gap-length baseline is missing")
    simple_status = simple.get("status")
    maximum_gap_length = simple.get("maximum_gap_length")
    if simple_status == "PASS":
        if not isinstance(maximum_gap_length, int) or isinstance(maximum_gap_length, bool) or maximum_gap_length < 1:
            raise ValueError("frozen simple gap-length cutoff is invalid")
    elif maximum_gap_length is not None:
        raise ValueError("non-PASS simple cutoff must have null maximum_gap_length")
    a0 = baselines.get("A0_consensus_alignment")
    if not isinstance(a0, dict) or "status" not in a0:
        raise ValueError("A0 pretest status is missing from the feature lock")
    return lock


def load_chr19_rows(path: Path) -> tuple[list[dict[str, str]], int, set[str]]:
    required = {
        "candidate_id", "seqid", "gap_start", "gap_length", "eligible_main", "clean_target",
        "comparator_relation", "gap_comparator_positive_bp", "gap_comparator_negative_bp",
        "gap_comparator_unknown_bp",
    }
    rows: list[dict[str, str]] = []
    excluded_unknown = 0
    eligible_ids: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("chr19 labeled TSV lacks the explicit comparator-projection fields")
        for row in reader:
            if row["seqid"] != "chr19":
                raise ValueError("chr19 evaluator received a non-chr19 row")
            if row["eligible_main"] != "1":
                continue
            if row["candidate_id"] in eligible_ids:
                raise ValueError("duplicate eligible chr19 candidate_id")
            eligible_ids.add(row["candidate_id"])
            unknown_bp = int(row["gap_comparator_unknown_bp"])
            if unknown_bp < 0:
                raise ValueError("unknown comparator bp cannot be negative")
            if unknown_bp != 0:
                excluded_unknown += 1
                continue
            relation = row["comparator_relation"]
            target = row["clean_target"]
            if relation not in {BRIDGE, SEPARATION, AMBIGUOUS}:
                raise ValueError(f"unknown comparator relation: {relation}")
            if relation == BRIDGE and target != "1":
                raise ValueError("bridge row does not have clean_target=1")
            if relation == SEPARATION and target != "0":
                raise ValueError("separation row does not have clean_target=0")
            if relation == AMBIGUOUS and target != "":
                raise ValueError("ambiguous row has a clean target")
            for field in ("gap_start", "gap_length", "gap_comparator_positive_bp", "gap_comparator_negative_bp"):
                if int(row[field]) < 0:
                    raise ValueError(f"negative candidate value: {field}")
            rows.append(row)
    return rows, excluded_unknown, eligible_ids


def load_purge_membership(path: Path, candidate_ids: set[str]) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["candidate_id", "purged"]:
            raise ValueError("purge membership must have exactly candidate_id and purged columns")
        membership: dict[str, int] = {}
        for row in reader:
            candidate_id = row["candidate_id"]
            if candidate_id in membership:
                raise ValueError(f"duplicate purge membership candidate_id: {candidate_id}")
            if row["purged"] not in {"0", "1"}:
                raise ValueError(f"purged must be 0 or 1: {candidate_id}")
            membership[candidate_id] = int(row["purged"])
    if set(membership) != candidate_ids:
        raise ValueError("purge membership must cover exactly all primary chr19 candidate IDs")
    return membership


def _matrix(rows: list[dict[str, str]]) -> np.ndarray:
    return np.asarray(
        [[feature_values(row)[field] for field in FEATURE_GROUPS["G2_FULL_LIBRARY_FREE"]] for row in rows],
        dtype=np.float64,
    )


def _sigmoid(values: np.ndarray) -> np.ndarray:
    result = np.empty_like(values, dtype=np.float64)
    positive = values >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    result[~positive] = exp_values / (1.0 + exp_values)
    return result


def locked_scores(lock: dict[str, object], rows: list[dict[str, str]]) -> dict[str, np.ndarray]:
    raw = _matrix(rows)
    scores: dict[str, np.ndarray] = {}
    groups = lock["groups"]
    assert isinstance(groups, dict)
    for group_name in GROUP_NAMES:
        group = groups[group_name]
        assert isinstance(group, dict)
        fields = FEATURE_GROUPS[group_name]
        indices = [FEATURE_GROUPS["G2_FULL_LIBRARY_FREE"].index(field) for field in fields]
        values = raw[:, indices]
        median = _finite_array(group["imputation_median"], f"{group_name}.imputation_median")
        mean = _finite_array(group["standardization_mean"], f"{group_name}.standardization_mean")
        scale = _finite_array(group["standardization_scale"], f"{group_name}.standardization_scale")
        coefficient = _finite_array(group["coefficient"], f"{group_name}.coefficient")
        if not (len(fields) == len(median) == len(mean) == len(scale) == len(coefficient)):
            raise ValueError(f"locked parameter lengths disagree for {group_name}")
        filled = np.where(np.isfinite(values), values, median)
        scores[group_name] = _sigmoid(
            float(group["intercept"]) + ((filled - mean) / scale).dot(coefficient),
        )
    return scores


def average_precision(target: np.ndarray, scores: np.ndarray) -> float | None:
    if target.size == 0 or int(target.sum()) == 0:
        return None
    order = np.argsort(-scores, kind="mergesort")
    ordered_scores = scores[order]
    ordered_target = target[order].astype(np.int64)
    ends = np.flatnonzero(np.r_[ordered_scores[1:] != ordered_scores[:-1], True])
    cumulative_positive = np.cumsum(ordered_target)
    cumulative_count = np.arange(1, target.size + 1)
    group_positive = np.diff(np.r_[0, cumulative_positive[ends]])
    precision = cumulative_positive[ends] / cumulative_count[ends]
    return float(np.sum(precision * group_positive) / int(target.sum()))


def expected_calibration_error(target: np.ndarray, scores: np.ndarray, bins: int = 10) -> float | None:
    if target.size == 0:
        return None
    result = 0.0
    for index in range(bins):
        left, right = index / bins, (index + 1) / bins
        selected = (scores >= left) & (scores < right if index < bins - 1 else scores <= right)
        if selected.any():
            result += float(selected.mean()) * abs(float(target[selected].mean()) - float(scores[selected].mean()))
    return float(result)


def _ratio(numerator: int | float, denominator: int | float) -> float | None:
    return None if denominator == 0 else float(numerator / denominator)


def candidate_metrics(
    target: np.ndarray,
    scores: np.ndarray,
    threshold: float | None = None,
    display_threshold: float | int | None = None,
    threshold_kind: str = "score",
    calibrated: bool = True,
) -> dict[str, object]:
    positive = int(target.sum())
    ap = average_precision(target, scores)
    result: dict[str, object] = {
        "clean_candidates": int(target.size),
        "positive_candidates": positive,
        "negative_candidates": int(target.size - positive),
        "prevalence": _ratio(positive, target.size),
        "average_precision": ap,
        "normalized_average_precision": None if ap is None or target.size == 0 or positive == 0 else ap / (positive / target.size),
        "brier": float(np.mean((scores - target) ** 2)) if calibrated and target.size else None,
        "ece_10bin": expected_calibration_error(target, scores) if calibrated else None,
        "calibration_status": "EVALUATED" if calibrated else "NOT_APPLICABLE_UNCALIBRATED_RANKING_SCORE",
    }
    if threshold is not None:
        selected = scores >= threshold
        tp = int(np.sum(selected & (target == 1)))
        fp = int(np.sum(selected & (target == 0)))
        fn = positive - tp
        precision = _ratio(tp, tp + fp)
        recall = _ratio(tp, positive)
        f1 = None if precision is None or recall is None or precision + recall == 0 else 2 * precision * recall / (precision + recall)
        result.update({
            "threshold": threshold if display_threshold is None else display_threshold,
            "threshold_kind": threshold_kind,
            "selected_candidates": int(selected.sum()),
            "true_positive_candidates": tp,
            "false_positive_candidates": fp,
            "false_negative_candidates": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        })
    return result


def added_bp_metrics(
    rows: list[dict[str, str]], scores: np.ndarray, threshold: float,
    display_threshold: float | int | None = None, threshold_kind: str = "score",
) -> dict[str, object]:
    positive = np.asarray([int(row["gap_comparator_positive_bp"]) for row in rows], dtype=np.int64)
    negative = np.asarray([int(row["gap_comparator_negative_bp"]) for row in rows], dtype=np.int64)
    unknown = np.asarray([int(row["gap_comparator_unknown_bp"]) for row in rows], dtype=np.int64)
    selected = scores >= threshold
    added_positive = int(positive[selected].sum())
    added_negative = int(negative[selected].sum())
    total_positive = int(positive.sum())
    total_negative = int(negative.sum())
    return {
        "threshold": threshold if display_threshold is None else display_threshold,
        "threshold_kind": threshold_kind,
        "eligible_candidates": len(rows),
        "selected_candidates": int(selected.sum()),
        "selected_unknown_bp": int(unknown[selected].sum()),
        "added_positive_bp": added_positive,
        "added_negative_bp": added_negative,
        "total_positive_bp": total_positive,
        "total_negative_bp": total_negative,
        "total_unknown_bp": int(unknown.sum()),
        "added_bp_precision": _ratio(added_positive, added_positive + added_negative),
        "added_bp_recall": _ratio(added_positive, total_positive),
    }


def _clean_targets(rows: list[dict[str, str]]) -> np.ndarray:
    return np.asarray([int(row["clean_target"]) if row["clean_target"] in {"0", "1"} else -1 for row in rows], dtype=np.int8)


def simple_baseline(lock: dict[str, object], rows: list[dict[str, str]]) -> tuple[np.ndarray, float | None, float | int | None, str]:
    baselines = lock["baselines"]
    assert isinstance(baselines, dict)
    cutoff = baselines["simple_gap_length_cutoff"]
    assert isinstance(cutoff, dict)
    status = str(cutoff["status"])
    scores = -np.asarray([int(row["gap_length"]) for row in rows], dtype=np.float64)
    if status != "PASS":
        return scores, None, None, status
    maximum = cutoff["maximum_gap_length"]
    assert isinstance(maximum, int) and not isinstance(maximum, bool)
    return scores, -float(maximum), maximum, status


def threshold_spec(
    lock: dict[str, object], group_name: str,
) -> tuple[str, float | None, float | int | None, str]:
    if group_name == "SIMPLE_LENGTH":
        baselines = lock["baselines"]
        assert isinstance(baselines, dict)
        cutoff = baselines["simple_gap_length_cutoff"]
        assert isinstance(cutoff, dict)
        status = str(cutoff["status"])
        maximum = cutoff.get("maximum_gap_length")
        return status, None if maximum is None else -float(maximum), maximum, "maximum_gap_length"
    groups = lock["groups"]
    assert isinstance(groups, dict)
    group = groups[group_name]
    assert isinstance(group, dict)
    operating = group["validation"]["operating_threshold"]
    assert isinstance(operating, dict)
    status = str(operating["status"])
    threshold = operating.get("threshold")
    return status, None if threshold is None else float(threshold), threshold, "score"


def _block_indices(rows: list[dict[str, str]]) -> dict[int, np.ndarray]:
    blocks: dict[int, list[int]] = {}
    for index, row in enumerate(rows):
        block = int(row["gap_start"]) // BLOCK_SIZE
        blocks.setdefault(block, []).append(index)
    return {block: np.asarray(indices, dtype=np.int64) for block, indices in sorted(blocks.items())}


def block_summaries(
    rows: list[dict[str, str]], targets: np.ndarray, scores: dict[str, np.ndarray], lock: dict[str, object],
) -> list[dict[str, object]]:
    groups = lock["groups"]
    assert isinstance(groups, dict)
    summaries: list[dict[str, object]] = []
    for block, indices in _block_indices(rows).items():
        block_rows = [rows[index] for index in indices]
        clean = targets[indices] >= 0
        block_result: dict[str, object] = {
            "block_start": block * BLOCK_SIZE,
            "block_end": (block + 1) * BLOCK_SIZE,
            "candidates": len(indices),
            "clean_candidates": int(clean.sum()),
            "bridge_candidates": int(np.sum(targets[indices] == 1)),
            "separation_candidates": int(np.sum(targets[indices] == 0)),
            "ambiguous_candidates": int(np.sum(targets[indices] < 0)),
            "bridge_gt5_candidates": sum(int(targets[index] == 1 and int(rows[index]["gap_length"]) > 5) for index in indices),
            "positive_bp": sum(int(row["gap_comparator_positive_bp"]) for row in block_rows),
            "negative_bp": sum(int(row["gap_comparator_negative_bp"]) for row in block_rows),
            "unknown_bp": sum(int(row["gap_comparator_unknown_bp"]) for row in block_rows),
            "groups": {},
        }
        group_result = block_result["groups"]
        assert isinstance(group_result, dict)
        for group_name in ("SIMPLE_LENGTH", *GROUP_NAMES):
            status, threshold, display_threshold, threshold_kind = threshold_spec(lock, group_name)
            metric = candidate_metrics(
                targets[indices][clean], scores[group_name][indices][clean], threshold,
                display_threshold, threshold_kind, group_name != "SIMPLE_LENGTH",
            )
            group_result[group_name] = {
                "threshold_status": status,
                "candidate_metrics": metric,
                "added_bp_metrics": None if threshold is None else added_bp_metrics(
                    block_rows, scores[group_name][indices], threshold,
                    display_threshold, threshold_kind,
                ),
            }
        summaries.append(block_result)
    return summaries


def bootstrap_ap_difference(
    blocks: dict[int, np.ndarray], targets: np.ndarray, g2: np.ndarray, baseline: np.ndarray,
) -> dict[str, object]:
    if len(blocks) == 0 or not any(np.any(targets[index] >= 0) for index in blocks.values()):
        return {
            "status": "NOT_EVALUABLE", "unit": "1Mb block", "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED, "statistic": "pooled AP(G2)-pooled AP(best frozen baseline)",
            "observed": None, "mean": None, "lower_95": None, "upper_95": None,
        }
    clean_blocks = {
        block: index[(targets[index] >= 0)] for block, index in blocks.items()
        if np.any(targets[index] >= 0)
    }
    all_clean = np.flatnonzero(targets >= 0)
    observed_g2 = average_precision(targets[all_clean], g2[all_clean])
    observed_base = average_precision(targets[all_clean], baseline[all_clean])
    observed = None if observed_g2 is None or observed_base is None else observed_g2 - observed_base
    rng = random.Random(BOOTSTRAP_SEED)
    block_names = sorted(clean_blocks)
    replicates: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = [clean_blocks[rng.choice(block_names)] for _ in block_names]
        sample_indices = np.concatenate(sampled)
        g2_ap = average_precision(targets[sample_indices], g2[sample_indices])
        base_ap = average_precision(targets[sample_indices], baseline[sample_indices])
        if g2_ap is not None and base_ap is not None:
            replicates.append(g2_ap - base_ap)
    if not replicates:
        return {
            "status": "NOT_EVALUABLE", "unit": "1Mb block", "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED, "statistic": "pooled AP(G2)-pooled AP(best frozen baseline)",
            "observed": observed, "mean": None, "lower_95": None, "upper_95": None,
        }
    values = np.sort(np.asarray(replicates, dtype=np.float64))
    return {
        "status": "PASS",
        "unit": "1Mb block",
        "estimand": "pooled sufficient candidates after block resampling",
        "replicates": BOOTSTRAP_REPLICATES,
        "valid_replicates": int(values.size),
        "seed": BOOTSTRAP_SEED,
        "statistic": "pooled AP(G2)-pooled AP(best frozen baseline)",
        "observed": observed,
        "mean": float(values.mean()),
        "lower_95": float(values[int(0.025 * values.size)]),
        "upper_95": float(values[min(values.size - 1, int(0.975 * values.size))]),
    }


def evaluate_chr19(
    lock_path: Path, labeled_path: Path, purge_membership_path: Path, output_path: Path,
) -> dict[str, object]:
    lock = load_lock(lock_path)
    rows, excluded_unknown, eligible_ids = load_chr19_rows(labeled_path)
    membership = load_purge_membership(purge_membership_path, eligible_ids)
    targets = _clean_targets(rows)
    scores = locked_scores(lock, rows)
    simple_scores, _simple_threshold, _simple_display, _simple_status = simple_baseline(lock, rows)
    scores = {"SIMPLE_LENGTH": simple_scores, **scores}
    groups = lock["groups"]
    assert isinstance(groups, dict)
    group_metrics: dict[str, object] = {}
    simple_lock = lock["baselines"]["simple_gap_length_cutoff"]
    assert isinstance(simple_lock, dict)
    validation_aps = {"SIMPLE_LENGTH": float(simple_lock["validation_average_precision"])}
    validation_aps.update({
        group_name: float(groups[group_name]["validation"]["average_precision"])
        for group_name in GROUP_NAMES
    })
    for group_name in ("SIMPLE_LENGTH", *GROUP_NAMES):
        status, threshold, display_threshold, threshold_kind = threshold_spec(lock, group_name)
        clean = targets >= 0
        metric = candidate_metrics(
            targets[clean], scores[group_name][clean], threshold, display_threshold, threshold_kind,
            group_name != "SIMPLE_LENGTH",
        )
        group_metrics[group_name] = {
            "validation_average_precision": validation_aps[group_name],
            "threshold_status": status,
            "candidate_metrics": metric,
            "added_bp_metrics": None if threshold is None else added_bp_metrics(
                rows, scores[group_name], threshold, display_threshold, threshold_kind,
            ),
        }
    best_baseline = max(
        ("SIMPLE_LENGTH", "G0_LENGTH", "G1_GEOMETRY_LOGITS"),
        key=lambda name: (validation_aps[name], name),
    )
    clean = targets >= 0
    g2_ap = group_metrics["G2_FULL_LIBRARY_FREE"]["candidate_metrics"]["average_precision"]
    baseline_ap = group_metrics[best_baseline]["candidate_metrics"]["average_precision"]
    comparison = {
        "best_baseline": best_baseline,
        "selection_basis": "locked chr13 validation average_precision among SIMPLE_LENGTH, G0 and G1",
        "g2_minus_best_baseline_average_precision": None if g2_ap is None or baseline_ap is None else g2_ap - baseline_ap,
        "g2_minus_best_baseline_normalized_average_precision": (
            group_metrics["G2_FULL_LIBRARY_FREE"]["candidate_metrics"]["normalized_average_precision"]
            - group_metrics[best_baseline]["candidate_metrics"]["normalized_average_precision"]
            if group_metrics["G2_FULL_LIBRARY_FREE"]["candidate_metrics"]["normalized_average_precision"] is not None
            and group_metrics[best_baseline]["candidate_metrics"]["normalized_average_precision"] is not None else None
        ),
        "g2_minus_best_baseline_brier": (
            group_metrics["G2_FULL_LIBRARY_FREE"]["candidate_metrics"]["brier"]
            - group_metrics[best_baseline]["candidate_metrics"]["brier"]
            if group_metrics["G2_FULL_LIBRARY_FREE"]["candidate_metrics"]["brier"] is not None
            and group_metrics[best_baseline]["candidate_metrics"]["brier"] is not None else None
        ),
        "g2_minus_best_baseline_ece_10bin": (
            group_metrics["G2_FULL_LIBRARY_FREE"]["candidate_metrics"]["ece_10bin"]
            - group_metrics[best_baseline]["candidate_metrics"]["ece_10bin"]
            if group_metrics["G2_FULL_LIBRARY_FREE"]["candidate_metrics"]["ece_10bin"] is not None
            and group_metrics[best_baseline]["candidate_metrics"]["ece_10bin"] is not None else None
        ),
    }
    blocks = _block_indices(rows)
    block_rows = block_summaries(rows, targets, scores, lock)
    both_class_blocks = sum(
        int(np.any(targets[index] == 1) and np.any(targets[index] == 0)) for index in blocks.values()
    )
    bridge_longer_than_5bp = sum(
        int(targets[index] == 1 and int(rows[index]["gap_length"]) > 5)
        for index in range(len(rows))
    )
    denominator = {
        "eligible_main_candidates": len(rows) + excluded_unknown,
        "excluded_unknown_candidates": excluded_unknown,
        "primary_candidates": len(rows),
        "eligible_clean_bridge_candidates": int(np.sum(targets == 1)),
        "eligible_clean_separation_candidates": int(np.sum(targets == 0)),
        "eligible_bridge_longer_than_5bp": bridge_longer_than_5bp,
        "independent_1mb_blocks_with_both_clean_classes": both_class_blocks,
        "required": {
            "clean_bridge_candidates": 1000,
            "clean_separation_candidates": 1000,
            "bridge_longer_than_5bp": 200,
            "blocks_with_both_clean_classes": 20,
        },
        "status": "PASS" if (
            int(np.sum(targets == 1)) >= 1000 and int(np.sum(targets == 0)) >= 1000
            and bridge_longer_than_5bp >= 200
            and both_class_blocks >= 20
        ) else "TEST_DENOMINATOR_INSUFFICIENT",
    }
    purged = np.asarray([membership[row["candidate_id"]] == 1 for row in rows], dtype=bool)
    challenge = ~purged
    challenge_clean = challenge & clean
    challenge_metrics: dict[str, object] = {}
    for group_name in ("SIMPLE_LENGTH", *GROUP_NAMES):
        challenge_metrics[group_name] = {
            "clean_candidates": int(challenge_clean.sum()),
            "challenge_candidates": int(challenge.sum()),
            "average_precision": average_precision(targets[challenge_clean], scores[group_name][challenge_clean]),
            "normalized_average_precision": (
                None if not challenge_clean.any() or int(targets[challenge_clean].sum()) == 0
                else average_precision(targets[challenge_clean], scores[group_name][challenge_clean])
                / (int(targets[challenge_clean].sum()) / int(challenge_clean.sum()))
            ),
        }
    challenge_g2_ap = challenge_metrics["G2_FULL_LIBRARY_FREE"]["average_precision"]
    challenge_baseline_ap = challenge_metrics[best_baseline]["average_precision"]
    a0 = lock["baselines"]["A0_consensus_alignment"]
    assert isinstance(a0, dict)
    a0_result = dict(a0)
    a0_result.update({
        "metrics_available": False,
        "superiority_claim_allowed": False,
    })
    challenge_status = "EVALUATED" if challenge_g2_ap is not None and challenge_baseline_ap is not None else "NOT_EVALUABLE"
    result: dict[str, object] = {
        "schema": "gap_bridge_phase0_chr19_evaluation_v1",
        "status": "PARTIAL_EVALUATION_UNAVAILABLE_ASSETS",
        "feature_lock": str(lock_path),
        "labeled_test": str(labeled_path),
        "purge_membership": str(purge_membership_path),
        "test_labels_read": True,
        "test_chromosome": "chr19",
        "candidate_count": len(rows),
        "excluded_unknown_candidates": excluded_unknown,
        "group_metrics": group_metrics,
        "comparison": comparison,
        "prospective_denominator": denominator,
        "block_size_bp": BLOCK_SIZE,
        "block_summaries": block_rows,
        "bootstrap_ap_difference": bootstrap_ap_difference(blocks, targets, scores["G2_FULL_LIBRARY_FREE"], scores[best_baseline]),
        "purged_challenge": {
            "status": challenge_status,
            "membership_column": "purged",
            "purged_candidates": int(purged.sum()),
            "unpurged_challenge_candidates": int(challenge.sum()),
            "unpurged_challenge_clean_candidates": int(challenge_clean.sum()),
            "ranking_metrics_only": challenge_metrics,
            "g2_minus_best_baseline_average_precision": None if challenge_g2_ap is None or challenge_baseline_ap is None else challenge_g2_ap - challenge_baseline_ap,
        },
        "a0_consensus_alignment": a0_result,
        "prospective_gate": {
            "status": "NOT_EVALUATED",
            "reason": "whole-mask, fragmentation and gene-safety assets were not supplied to this candidate evaluator",
            "unavailable_metrics": UNAVAILABLE_METRICS,
            "candidate_metrics_are_not_a_full_gate": True,
        },
        "selection_and_thresholds": "all SIMPLE_LENGTH/G0/G1/G2 parameters, C values and validation-frozen thresholds were read from feature_lock.json; no refit or new selection was performed",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-lock", type=Path, required=True)
    parser.add_argument("--labeled", type=Path, required=True)
    parser.add_argument("--purge-membership", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_chr19(args.feature_lock, args.labeled, args.purge_membership, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
