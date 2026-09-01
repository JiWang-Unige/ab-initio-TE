#!/usr/bin/env python3
"""Evaluate the frozen G2 gap-fill mask on a labeled Human chr19 test."""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np


_PROBE_SPEC = importlib.util.spec_from_file_location(
    "phase0_mask_fragment_feature_probe", Path(__file__).with_name("phase0_feature_probe.py"),
)
if _PROBE_SPEC is None or _PROBE_SPEC.loader is None:
    raise RuntimeError("cannot load the frozen Phase-0 feature probe")
_PROBE = importlib.util.module_from_spec(_PROBE_SPEC)
_PROBE_SPEC.loader.exec_module(_PROBE)

FEATURE_GROUPS = _PROBE.FEATURE_GROUPS
feature_values = _PROBE.feature_values
G2 = FEATURE_GROUPS["G2_FULL_LIBRARY_FREE"]

CHROMOSOME = "chr19"
BLOCK_SIZE = 1_000_000
BOOTSTRAP_REPLICATES = 1_000
BOOTSTRAP_SEED = 20260901
BRIDGE = "COMPARATOR_BRIDGE_SUPPORTED"
SEPARATION = "COMPARATOR_SEPARATION_SUPPORTED"
AMBIGUOUS = "COMPARATOR_RELATION_AMBIGUOUS"


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def read_intervals(
    path: Path, chromosome_length: int, require_chr19: bool = False,
) -> list[tuple[int, int]]:
    """Read zero-based half-open intervals, selecting chr19 from genome tracks."""
    with _open_text(path) as handle:
        lines = [line.rstrip("\r\n") for line in handle if line.strip() and not line.startswith("#")]
    if not lines:
        return []
    first = lines[0].split("\t")
    lowered = {field.lower(): index for index, field in enumerate(first)}
    if {"seqid", "start", "end"} <= set(lowered):
        seq_index, start_index, end_index = lowered["seqid"], lowered["start"], lowered["end"]
        rows = lines[1:]
    elif {"chrom", "start", "end"} <= set(lowered):
        seq_index, start_index, end_index = lowered["chrom"], lowered["start"], lowered["end"]
        rows = lines[1:]
    else:
        seq_index, start_index, end_index = 0, 1, 2
        rows = lines
    intervals: list[tuple[int, int]] = []
    for line in rows:
        fields = line.split("\t")
        seqid = fields[seq_index]
        if seqid != CHROMOSOME:
            if require_chr19:
                raise ValueError(f"interval asset contains non-chr19 sequence: {seqid}")
            continue
        start, end = int(fields[start_index]), int(fields[end_index])
        if start < 0 or end <= start or end > chromosome_length:
            raise ValueError(f"invalid chr19 interval: {start}-{end}")
        intervals.append((start, end))
    return merge_intervals(intervals)


def subtract_intervals(
    intervals: Iterable[tuple[int, int]], cutters: Iterable[tuple[int, int]],
) -> list[tuple[int, int]]:
    cuts = merge_intervals(cutters)
    result: list[tuple[int, int]] = []
    for start, end in merge_intervals(intervals):
        cursor = start
        for cut_start, cut_end in cuts:
            if cut_end <= cursor:
                continue
            if cut_start >= end:
                break
            if cut_start > cursor:
                result.append((cursor, min(cut_start, end)))
            cursor = max(cursor, cut_end)
            if cursor >= end:
                break
        if cursor < end:
            result.append((cursor, end))
    return result


def intersect_intervals(
    intervals: Iterable[tuple[int, int]], cutters: Iterable[tuple[int, int]],
) -> list[tuple[int, int]]:
    left = merge_intervals(intervals)
    right = merge_intervals(cutters)
    result: list[tuple[int, int]] = []
    right_index = 0
    for start, end in left:
        while right_index < len(right) and right[right_index][1] <= start:
            right_index += 1
        index = right_index
        while index < len(right) and right[index][0] < end:
            overlap_start = max(start, right[index][0])
            overlap_end = min(end, right[index][1])
            if overlap_start < overlap_end:
                result.append((overlap_start, overlap_end))
            index += 1
    return merge_intervals(result)


def interval_bp(intervals: Iterable[tuple[int, int]]) -> int:
    return sum(end - start for start, end in intervals)


def _overlap_bp(left: Iterable[tuple[int, int]], right: Iterable[tuple[int, int]]) -> int:
    return interval_bp(intersect_intervals(left, right))


def _finite_array(value: object, field: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"locked parameter {field} must be finite and one-dimensional")
    return array


def load_feature_lock(path: Path) -> tuple[dict[str, object], float]:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(lock, dict):
        raise ValueError("feature lock must be a JSON object")
    if lock.get("status") != "PASS_TO_TEST":
        raise ValueError("mask gate requires feature lock status=PASS_TO_TEST")
    if lock.get("selection_locked") is not True:
        raise ValueError("mask gate requires selection_locked=true")
    if lock.get("test_labels_read") is not False:
        raise ValueError("mask gate requires test_labels_read=false in the pre-test lock")
    if lock.get("test_label_release_allowed") is not True:
        raise ValueError("mask gate requires test_label_release_allowed=true")
    if lock.get("selected_deployment_group") != "G2_FULL_LIBRARY_FREE":
        raise ValueError("mask gate requires the frozen G2 deployment group")
    baselines = lock.get("baselines")
    if not isinstance(baselines, dict):
        raise ValueError("feature lock baselines are missing")
    simple = baselines.get("simple_gap_length_cutoff")
    if not isinstance(simple, dict):
        raise ValueError("feature lock simple baseline is missing")
    simple_status = simple.get("status")
    maximum = simple.get("maximum_gap_length")
    if simple_status == "PASS":
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
            raise ValueError("feature lock simple baseline threshold is invalid")
    elif maximum is not None:
        raise ValueError("non-PASS simple baseline must not carry a threshold")
    groups = lock.get("groups")
    if not isinstance(groups, dict) or set(groups) != set(FEATURE_GROUPS):
        raise ValueError("feature lock must contain exactly G0, G1 and G2")
    for name, fields in FEATURE_GROUPS.items():
        group = groups[name]
        if not isinstance(group, dict) or group.get("features") != fields:
            raise ValueError(f"frozen feature list differs for {name}")
        arrays = [
            _finite_array(group.get(field), f"{name}.{field}")
            for field in ("coefficient", "imputation_median", "standardization_mean", "standardization_scale")
        ]
        if any(len(array) != len(fields) for array in arrays):
            raise ValueError(f"locked parameter lengths disagree for {name}")
        intercept = group.get("intercept")
        if not isinstance(intercept, (int, float)) or not math.isfinite(float(intercept)):
            raise ValueError(f"locked intercept is invalid for {name}")
        validation = group.get("validation")
        if not isinstance(validation, dict):
            raise ValueError(f"locked validation block is missing for {name}")
        operating = validation.get("operating_threshold")
        if not isinstance(operating, dict):
            raise ValueError(f"locked operating threshold is missing for {name}")
        op_status, op_threshold = operating.get("status"), operating.get("threshold")
        if op_status == "PASS":
            if not isinstance(op_threshold, (int, float)) or not math.isfinite(float(op_threshold)):
                raise ValueError(f"PASS operating threshold is invalid for {name}")
        elif op_threshold is not None:
            raise ValueError(f"non-PASS operating threshold must be null for {name}")
    g2 = groups["G2_FULL_LIBRARY_FREE"]
    assert isinstance(g2, dict)
    validation = g2.get("validation")
    if not isinstance(validation, dict):
        raise ValueError("G2 validation block is missing")
    operating = validation.get("operating_threshold")
    if not isinstance(operating, dict) or operating.get("status") != "PASS":
        raise ValueError("G2 requires a PASS frozen operating threshold")
    threshold = operating.get("threshold")
    if not isinstance(threshold, (int, float)) or not math.isfinite(float(threshold)):
        raise ValueError("G2 operating threshold is invalid")
    return lock, float(threshold)


def load_candidate_rows(path: Path) -> tuple[list[dict[str, str]], int]:
    required = {
        "candidate_id", "seqid", "gap_start", "gap_end", "gap_length", "eligible_main",
        "clean_target", "comparator_relation", "gap_comparator_positive_bp",
        "gap_comparator_negative_bp", "gap_comparator_unknown_bp",
        *G2,
    }
    rows: list[dict[str, str]] = []
    excluded_unknown = 0
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("chr19 labeled candidates lack required frozen feature/label fields")
        for row in reader:
            if row["seqid"] != CHROMOSOME:
                raise ValueError("chr19 mask gate received a non-chr19 candidate")
            if row["eligible_main"] != "1":
                continue
            candidate_id = row["candidate_id"]
            if candidate_id in seen:
                raise ValueError("duplicate eligible chr19 candidate_id")
            seen.add(candidate_id)
            unknown = int(row["gap_comparator_unknown_bp"])
            if unknown < 0:
                raise ValueError("candidate unknown comparator bp cannot be negative")
            if unknown:
                excluded_unknown += 1
                continue
            start, end, length = int(row["gap_start"]), int(row["gap_end"]), int(row["gap_length"])
            if start < 0 or end <= start or end - start != length:
                raise ValueError(f"invalid candidate gap interval: {candidate_id}")
            if any(int(row[field]) < 0 for field in ("gap_comparator_positive_bp", "gap_comparator_negative_bp")):
                raise ValueError(f"negative candidate comparator bp: {candidate_id}")
            rows.append(row)
    return rows, excluded_unknown


def load_candidate_evaluation(path: Path, expected_count: int, threshold: float) -> dict[str, object]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("candidate evaluation must be a JSON object")
    if result.get("test_chromosome") != CHROMOSOME:
        raise ValueError("candidate evaluation is not the chr19 test")
    if result.get("test_labels_read") is not True:
        raise ValueError("candidate evaluation must record released test labels")
    if result.get("candidate_count") != expected_count:
        raise ValueError("candidate evaluation count differs from eligible primary candidates")
    groups = result.get("group_metrics")
    if not isinstance(groups, dict) or "G2_FULL_LIBRARY_FREE" not in groups:
        raise ValueError("candidate evaluation lacks G2 metrics")
    g2 = groups["G2_FULL_LIBRARY_FREE"]
    if not isinstance(g2, dict):
        raise ValueError("candidate evaluation G2 metrics are invalid")
    metrics = g2.get("candidate_metrics")
    if not isinstance(metrics, dict) or metrics.get("threshold_kind") != "score":
        raise ValueError("candidate evaluation must use the frozen G2 score threshold")
    evaluated_threshold = metrics.get("threshold")
    if not isinstance(evaluated_threshold, (int, float)) or not math.isclose(
        float(evaluated_threshold), threshold, rel_tol=0.0, abs_tol=1e-12,
    ):
        raise ValueError("candidate evaluation G2 threshold differs from feature lock")
    selected = metrics.get("selected_candidates")
    if not isinstance(selected, int) or isinstance(selected, bool) or selected < 0:
        raise ValueError("candidate evaluation G2 selected count is missing or invalid")
    return result


def _sigmoid(values: np.ndarray) -> np.ndarray:
    result = np.empty_like(values, dtype=np.float64)
    positive = values >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exponential = np.exp(values[~positive])
    result[~positive] = exponential / (1.0 + exponential)
    return result


def locked_group_scores(lock: dict[str, object], rows: list[dict[str, str]], group_name: str) -> np.ndarray:
    if not rows:
        return np.asarray([], dtype=np.float64)
    raw = np.asarray([[feature_values(row)[field] for field in G2] for row in rows], dtype=np.float64)
    group = lock["groups"][group_name]
    assert isinstance(group, dict)
    fields = FEATURE_GROUPS[group_name]
    indices = [G2.index(field) for field in fields]
    median = _finite_array(group["imputation_median"], f"{group_name}.imputation_median")
    mean = _finite_array(group["standardization_mean"], f"{group_name}.standardization_mean")
    scale = _finite_array(group["standardization_scale"], f"{group_name}.standardization_scale")
    coefficient = _finite_array(group["coefficient"], f"{group_name}.coefficient")
    filled = np.where(np.isfinite(raw[:, indices]), raw[:, indices], median)
    return _sigmoid(float(group["intercept"]) + ((filled - mean) / scale).dot(coefficient))


def g2_scores(lock: dict[str, object], rows: list[dict[str, str]]) -> np.ndarray:
    return locked_group_scores(lock, rows, "G2_FULL_LIBRARY_FREE")


def simple_scores(rows: list[dict[str, str]]) -> np.ndarray:
    return -np.asarray([int(row["gap_length"]) for row in rows], dtype=np.float64)


def frozen_threshold(lock: dict[str, object], group_name: str) -> tuple[str, float | None, float | int | None]:
    if group_name == "SIMPLE_LENGTH":
        baselines = lock["baselines"]
        assert isinstance(baselines, dict)
        cutoff = baselines["simple_gap_length_cutoff"]
        assert isinstance(cutoff, dict)
        maximum = cutoff.get("maximum_gap_length")
        return str(cutoff["status"]), None if maximum is None else -float(maximum), maximum
    groups = lock["groups"]
    assert isinstance(groups, dict)
    group = groups[group_name]
    assert isinstance(group, dict)
    operating = group["validation"]["operating_threshold"]
    assert isinstance(operating, dict)
    value = operating.get("threshold")
    return str(operating["status"]), None if value is None else float(value), value


def best_operating_baseline(lock: dict[str, object]) -> str | None:
    names = ("SIMPLE_LENGTH", "G0_LENGTH", "G1_GEOMETRY_LOGITS")
    valid: list[tuple[float, str]] = []
    for name in names:
        status, _threshold, _display = frozen_threshold(lock, name)
        if name == "SIMPLE_LENGTH":
            baselines = lock["baselines"]
            assert isinstance(baselines, dict)
            value = baselines["simple_gap_length_cutoff"].get("validation_average_precision")
        else:
            groups = lock["groups"]
            assert isinstance(groups, dict)
            value = groups[name]["validation"].get("average_precision")
        if status == "PASS" and isinstance(value, (int, float)) and math.isfinite(float(value)):
            valid.append((float(value), name))
    return max(valid)[1] if valid else None


def scores_for_group(lock: dict[str, object], rows: list[dict[str, str]], group_name: str) -> np.ndarray:
    if group_name == "SIMPLE_LENGTH":
        return simple_scores(rows)
    return locked_group_scores(lock, rows, group_name)


def validate_baseline_evaluation(
    candidate_evaluation: dict[str, object], lock: dict[str, object], expected_count: int,
) -> tuple[str | None, str | None, float | None, float | int | None]:
    comparison = candidate_evaluation.get("comparison")
    if not isinstance(comparison, dict):
        raise ValueError("candidate evaluation baseline comparison is missing")
    ranking = comparison.get("best_ranking_baseline")
    operating = comparison.get("best_operating_baseline")
    allowed = {"SIMPLE_LENGTH", "G0_LENGTH", "G1_GEOMETRY_LOGITS"}
    if ranking not in allowed:
        raise ValueError("candidate evaluation best_ranking_baseline is invalid")
    if operating is not None and operating not in allowed:
        raise ValueError("candidate evaluation best_operating_baseline is invalid")
    expected_operating = best_operating_baseline(lock)
    if operating != expected_operating:
        raise ValueError("candidate evaluation best_operating_baseline differs from feature lock")
    groups = candidate_evaluation["group_metrics"]
    assert isinstance(groups, dict)
    if operating is None:
        return ranking, operating, None, None
    status, threshold, display = frozen_threshold(lock, operating)
    metrics = groups[operating]["candidate_metrics"]
    if not isinstance(metrics, dict) or metrics.get("threshold_kind") != (
        "maximum_gap_length" if operating == "SIMPLE_LENGTH" else "score"
    ):
        raise ValueError("candidate evaluation operating baseline threshold kind is invalid")
    evaluated = metrics.get("threshold")
    if status != "PASS":
        raise ValueError("candidate evaluation selected a non-PASS operating baseline")
    if not isinstance(threshold, float) or not isinstance(evaluated, (int, float)) or not math.isclose(
        float(evaluated), float(display), rel_tol=0.0, abs_tol=1e-12,
    ):
        raise ValueError("candidate evaluation operating baseline threshold differs from feature lock")
    selected = metrics.get("selected_candidates")
    if not isinstance(selected, int) or isinstance(selected, bool) or selected < 0 or selected > expected_count:
        raise ValueError("candidate evaluation operating baseline selected count is invalid")
    return ranking, operating, threshold, display


def read_p3_mask(path: Path, chromosome_length: int) -> list[tuple[int, int]]:
    intervals = read_intervals(path, chromosome_length, require_chr19=True)
    if not intervals:
        raise ValueError("raw P3 canonical mask is empty")
    return intervals


def _candidate_intervals(rows: list[dict[str, str]]) -> list[tuple[int, int]]:
    return [(int(row["gap_start"]), int(row["gap_end"])) for row in rows]


def validate_candidate_gaps(rows: list[dict[str, str]], p3_mask: list[tuple[int, int]]) -> None:
    gaps = _candidate_intervals(rows)
    if gaps != merge_intervals(gaps):
        raise ValueError("candidate gaps overlap or touch and cannot be independent additions")
    if _overlap_bp(gaps, p3_mask):
        raise ValueError("candidate gap overlaps the raw P3 mask")


def whole_mask_metrics(
    mask: list[tuple[int, int]], positive: list[tuple[int, int]], unknown: list[tuple[int, int]],
    chromosome_length: int,
) -> dict[str, object]:
    callable_regions = subtract_intervals([(0, chromosome_length)], unknown)
    positive_callable = intersect_intervals(positive, callable_regions)
    prediction = intersect_intervals(mask, callable_regions)
    callable_bp = interval_bp(callable_regions)
    positive_bp = interval_bp(positive_callable)
    predicted_bp = interval_bp(prediction)
    true_positive = _overlap_bp(prediction, positive_callable)
    false_positive = predicted_bp - true_positive
    false_negative = positive_bp - true_positive
    true_negative = callable_bp - true_positive - false_positive - false_negative
    precision = None if true_positive + false_positive == 0 else true_positive / (true_positive + false_positive)
    recall = None if positive_bp == 0 else true_positive / positive_bp
    f1 = None if precision is None or recall is None or precision + recall == 0 else 2 * precision * recall / (precision + recall)
    denominator = math.sqrt(
        (true_positive + false_positive) * (true_positive + false_negative)
        * (true_negative + false_positive) * (true_negative + false_negative),
    )
    mcc = None if denominator == 0 else (true_positive * true_negative - false_positive * false_negative) / denominator
    return {
        "callable_bp": callable_bp,
        "positive_bp": positive_bp,
        "predicted_bp": predicted_bp,
        "true_positive_bp": true_positive,
        "false_positive_bp": false_positive,
        "false_negative_bp": false_negative,
        "true_negative_bp": true_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mcc": mcc,
    }


def _mask_intersections(mask: list[tuple[int, int]], truth: tuple[int, int]) -> list[tuple[int, int]]:
    start, end = truth
    return [(max(left, start), min(right, end)) for left, right in mask if left < end and right > start]


def _fragment_metrics(mask: list[tuple[int, int]], truth_runs: list[tuple[int, int]]) -> tuple[dict[str, object], list[tuple[int, int]]]:
    fragment_count = 0
    missed = 0
    split = 0
    left_omission = 0
    right_omission = 0
    terminal_omission = 0
    terminal_omitted_bp = 0
    internal_gaps: list[tuple[int, int]] = []
    for start, end in truth_runs:
        covered = _mask_intersections(mask, (start, end))
        fragment_count += len(covered)
        if not covered:
            missed += 1
            terminal_omitted_bp += end - start
            left_omission += 1
            right_omission += 1
            terminal_omission += 1
            continue
        if len(covered) >= 2:
            split += 1
            for previous, current in zip(covered, covered[1:]):
                if previous[1] < current[0]:
                    internal_gaps.append((previous[1], current[0]))
        left_missing = covered[0][0] > start
        right_missing = covered[-1][1] < end
        if left_missing:
            left_omission += 1
            terminal_omitted_bp += covered[0][0] - start
        if right_missing:
            right_omission += 1
            terminal_omitted_bp += end - covered[-1][1]
        if left_missing or right_missing:
            terminal_omission += 1
    truth_count = len(truth_runs)
    truth_bp = interval_bp(truth_runs)
    return {
        "truth_runs": truth_count,
        "truth_bp": truth_bp,
        "fragments": fragment_count,
        "fragments_per_truth": None if truth_count == 0 else fragment_count / truth_count,
        "missed_truth_runs": missed,
        "missed_rate": None if truth_count == 0 else missed / truth_count,
        "split_truth_runs": split,
        "split_rate": None if truth_count == 0 else split / truth_count,
        "left_terminal_omission_truth_runs": left_omission,
        "right_terminal_omission_truth_runs": right_omission,
        "terminal_omission_truth_runs": terminal_omission,
        "terminal_omission_truth_truth": None if truth_count == 0 else terminal_omission / truth_count,
        "terminal_omitted_bp": terminal_omitted_bp,
        "terminal_omitted_bp_truth_bp": None if truth_bp == 0 else terminal_omitted_bp / truth_bp,
        "internal_gap_count": len(internal_gaps),
        "internal_gap_bp": interval_bp(internal_gaps),
    }, internal_gaps


def internal_gap_recovery(
    raw_mask: list[tuple[int, int]], refined_mask: list[tuple[int, int]], truth_runs: list[tuple[int, int]],
) -> dict[str, object]:
    _raw_metrics, raw_gaps = _fragment_metrics(raw_mask, truth_runs)
    raw_internal_bp = interval_bp(raw_gaps)
    added = subtract_intervals(refined_mask, raw_mask)
    added_internal_bp = _overlap_bp(added, raw_gaps)
    raw_long = [(start, end) for start, end in raw_gaps if end - start > 5]
    added_long_bp = _overlap_bp(added, raw_long)
    return {
        "raw_internal_gap_count": len(raw_gaps),
        "raw_internal_gap_bp": raw_internal_bp,
        "added_internal_gap_positive_bp": added_internal_bp,
        "internal_gap_positive_bp_recall": None if raw_internal_bp == 0 else added_internal_bp / raw_internal_bp,
        "raw_internal_gap_gt5_bp": interval_bp(raw_long),
        "added_internal_gap_gt5_positive_bp": added_long_bp,
        "internal_gap_gt5_positive_bp_recall": None if not raw_long else added_long_bp / interval_bp(raw_long),
    }


def _candidate_bp_by_track(
    rows: list[dict[str, str]], positive: list[tuple[int, int]], unknown: list[tuple[int, int]],
) -> list[tuple[int, int, int]]:
    result: list[tuple[int, int, int]] = []
    for row in rows:
        start, end = int(row["gap_start"]), int(row["gap_end"])
        row_unknown = _overlap_bp([(start, end)], unknown)
        row_positive = _overlap_bp([(start, end)], positive)
        row_negative = end - start - row_unknown - row_positive
        if row_negative < 0:
            raise ValueError(f"candidate comparator tracks exceed gap length: {row['candidate_id']}")
        if row_unknown != int(row["gap_comparator_unknown_bp"]):
            raise ValueError(f"candidate unknown bp disagrees with comparator track: {row['candidate_id']}")
        if row_positive != int(row["gap_comparator_positive_bp"]):
            raise ValueError(f"candidate positive bp disagrees with comparator track: {row['candidate_id']}")
        if row_negative != int(row["gap_comparator_negative_bp"]):
            raise ValueError(f"candidate negative bp disagrees with comparator track: {row['candidate_id']}")
        result.append((row_positive, row_negative, end - start))
    return result


def added_bp_precision_bootstrap(
    rows: list[dict[str, str]], selected: np.ndarray, positive: list[tuple[int, int]], unknown: list[tuple[int, int]],
) -> dict[str, object]:
    by_track = _candidate_bp_by_track(rows, positive, unknown)
    block_values: dict[int, tuple[int, int, int]] = {}
    for index, row in enumerate(rows):
        block = int(row["gap_start"]) // BLOCK_SIZE
        current = block_values.get(block, (0, 0, 0))
        if selected[index]:
            positive_bp, negative_bp, added_bp = by_track[index]
            block_values[block] = (current[0] + positive_bp, current[1] + negative_bp, current[2] + added_bp)
        else:
            block_values.setdefault(block, current)
    selected_positive = sum(value[0] for value in block_values.values())
    selected_negative = sum(value[1] for value in block_values.values())
    observed = None if selected_positive + selected_negative == 0 else selected_positive / (selected_positive + selected_negative)
    if not block_values:
        return {
            "status": "NOT_EVALUABLE_EMPTY_SELECTION",
            "observed_precision": observed,
            "lower_95": None,
            "upper_95": None,
            "unit": "1Mb block",
            "replicates": BOOTSTRAP_REPLICATES,
            "valid_replicates": 0,
            "seed": BOOTSTRAP_SEED,
            "empty_selected_replicates_omitted": BOOTSTRAP_REPLICATES,
            "statistic": "pooled selected positive bp / pooled selected (positive + negative) bp",
        }
    rng = random.Random(BOOTSTRAP_SEED)
    blocks = sorted(block_values)
    values: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = [block_values[rng.choice(blocks)] for _ in blocks]
        total_positive = sum(item[0] for item in sampled)
        total_negative = sum(item[1] for item in sampled)
        if total_positive + total_negative:
            values.append(total_positive / (total_positive + total_negative))
    ordered = np.sort(np.asarray(values, dtype=np.float64)) if values else np.asarray([], dtype=np.float64)
    return {
        "status": "PASS" if observed is not None else "NOT_EVALUABLE_EMPTY_SELECTION",
        "observed_precision": observed,
        "lower_95": None if not values else float(ordered[int(0.025 * len(ordered))]),
        "upper_95": None if not values else float(ordered[min(len(ordered) - 1, int(0.975 * len(ordered)))]),
        "unit": "1Mb block",
        "replicates": BOOTSTRAP_REPLICATES,
        "valid_replicates": len(values),
        "seed": BOOTSTRAP_SEED,
        "empty_selected_replicates_omitted": BOOTSTRAP_REPLICATES - len(values),
        "statistic": "pooled selected positive bp / pooled selected (positive + negative) bp",
    }


def block_summaries(
    rows: list[dict[str, str]], selected: np.ndarray, raw_mask: list[tuple[int, int]], refined_mask: list[tuple[int, int]],
    positive: list[tuple[int, int]], unknown: list[tuple[int, int]], chromosome_length: int,
) -> list[dict[str, object]]:
    indices: dict[int, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        indices[int(row["gap_start"]) // BLOCK_SIZE].append(index)
    callable_regions = subtract_intervals([(0, chromosome_length)], unknown)
    summaries: list[dict[str, object]] = []
    for block, block_indices in sorted(indices.items()):
        start, end = block * BLOCK_SIZE, min((block + 1) * BLOCK_SIZE, chromosome_length)
        block_positive = intersect_intervals(positive, [(start, end)])
        block_unknown = intersect_intervals(unknown, [(start, end)])
        block_callable = intersect_intervals(callable_regions, [(start, end)])
        raw_block = intersect_intervals(raw_mask, [(start, end)])
        refined_block = intersect_intervals(refined_mask, [(start, end)])
        selected_indices = [index for index in block_indices if selected[index]]
        selected_intervals = [_candidate_intervals(rows)[index] for index in selected_indices]
        summaries.append({
            "block_start": start,
            "block_end": end,
            "candidate_count": len(block_indices),
            "selected_candidate_count": len(selected_indices),
            "candidate_positive_bp": sum(int(rows[index]["gap_comparator_positive_bp"]) for index in block_indices),
            "candidate_negative_bp": sum(int(rows[index]["gap_comparator_negative_bp"]) for index in block_indices),
            "selected_gap_bp": interval_bp(selected_intervals),
            "selected_positive_bp": sum(int(rows[index]["gap_comparator_positive_bp"]) for index in selected_indices),
            "selected_negative_bp": sum(int(rows[index]["gap_comparator_negative_bp"]) for index in selected_indices),
            "callable_bp": interval_bp(block_callable),
            "positive_bp": interval_bp(block_positive),
            "unknown_bp": interval_bp(block_unknown),
            "raw_mask_bp": interval_bp(raw_block),
            "refined_mask_bp": interval_bp(refined_block),
        })
    return summaries


def write_refined_mask(path: Path, intervals: list[tuple[int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["seqid", "start", "end", "source", "name", "score", "strand", "attributes"])
        for start, end in intervals:
            writer.writerow([CHROMOSOME, start, end, "phase0_g2_gap_bridge", ".", ".", ".", "."])


def write_selected_sidecar(
    path: Path, rows: list[dict[str, str]], scores: np.ndarray, threshold: float, selected: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "candidate_id", "seqid", "gap_start", "gap_end", "g2_score", "threshold", "selected",
        "gap_comparator_positive_bp", "gap_comparator_negative_bp", "gap_comparator_unknown_bp",
        "positive_bp", "negative_bp", "unknown_bp",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for index, row in enumerate(rows):
            positive = row["gap_comparator_positive_bp"]
            negative = row["gap_comparator_negative_bp"]
            unknown = row["gap_comparator_unknown_bp"]
            writer.writerow({
                "candidate_id": row["candidate_id"], "seqid": row["seqid"],
                "gap_start": row["gap_start"], "gap_end": row["gap_end"],
                "g2_score": f"{float(scores[index]):.17g}", "threshold": f"{threshold:.17g}",
                "selected": str(int(selected[index])),
                "gap_comparator_positive_bp": positive,
                "gap_comparator_negative_bp": negative,
                "gap_comparator_unknown_bp": unknown,
                "positive_bp": positive, "negative_bp": negative, "unknown_bp": unknown,
            })


def evaluate_mask_fragment_gate(
    feature_lock_path: Path, candidate_evaluation_path: Path, labeled_path: Path, p3_canonical_path: Path,
    comparator_positive_path: Path, comparator_unknown_path: Path, chromosome_length: int,
    output_path: Path, refined_canonical_path: Path, selected_sidecar_path: Path,
) -> dict[str, object]:
    lock, threshold = load_feature_lock(feature_lock_path)
    rows, excluded_unknown = load_candidate_rows(labeled_path)
    candidate_evaluation = load_candidate_evaluation(candidate_evaluation_path, len(rows), threshold)
    ranking_baseline, operating_baseline, baseline_threshold, baseline_display = validate_baseline_evaluation(
        candidate_evaluation, lock, len(rows),
    )
    raw_mask = read_p3_mask(p3_canonical_path, chromosome_length)
    validate_candidate_gaps(rows, raw_mask)
    if any(int(row["gap_end"]) > chromosome_length for row in rows):
        raise ValueError("candidate gap extends beyond the declared chromosome length")
    positive = read_intervals(comparator_positive_path, chromosome_length)
    raw_unknown = read_intervals(comparator_unknown_path, chromosome_length)
    effective_unknown = subtract_intervals(raw_unknown, positive)
    _candidate_bp_by_track(rows, positive, effective_unknown)
    scores = g2_scores(lock, rows)
    selected = scores >= threshold
    evaluated_selected = candidate_evaluation["group_metrics"]["G2_FULL_LIBRARY_FREE"]["candidate_metrics"].get("selected_candidates")
    if evaluated_selected is not None and evaluated_selected != int(selected.sum()):
        raise ValueError("candidate evaluation selected count differs from frozen G2 scoring")
    selected_gaps = [_candidate_intervals(rows)[index] for index in np.flatnonzero(selected)]
    refined_mask = merge_intervals([*raw_mask, *selected_gaps])
    truth_runs = subtract_intervals(positive, effective_unknown)
    raw_fragment, _ = _fragment_metrics(raw_mask, truth_runs)
    refined_fragment, _ = _fragment_metrics(refined_mask, truth_runs)
    internal = internal_gap_recovery(raw_mask, refined_mask, truth_runs)
    added_intervals = subtract_intervals(refined_mask, raw_mask)
    added_positive = _overlap_bp(added_intervals, positive)
    added_unknown = _overlap_bp(added_intervals, effective_unknown)
    added_negative = interval_bp(added_intervals) - added_positive - added_unknown
    baseline_result: dict[str, object]
    if operating_baseline is None:
        baseline_result = {
            "status": "NO_BASELINE_OPERATING_POINT",
            "route_status": "G2_ONLY_SAFE_OPERATING_POINT",
            "best_ranking_baseline": ranking_baseline,
            "best_operating_baseline": None,
            "reason": "SIMPLE_LENGTH, G0 and G1 have no frozen PASS precision-floor threshold",
        }
    else:
        baseline_scores = scores_for_group(lock, rows, operating_baseline)
        assert baseline_threshold is not None
        baseline_selected = baseline_scores >= baseline_threshold
        baseline_gaps = [_candidate_intervals(rows)[index] for index in np.flatnonzero(baseline_selected)]
        baseline_mask = merge_intervals([*raw_mask, *baseline_gaps])
        baseline_added = subtract_intervals(baseline_mask, raw_mask)
        baseline_truth = interval_bp(truth_runs)
        baseline_result = {
            "status": "EVALUATED",
            "route_status": "G2_PLUS_FROZEN_OPERATING_BASELINE",
            "best_ranking_baseline": ranking_baseline,
            "best_operating_baseline": operating_baseline,
            "threshold": baseline_display,
            "threshold_kind": "maximum_gap_length" if operating_baseline == "SIMPLE_LENGTH" else "score",
            "selected_candidates": int(baseline_selected.sum()),
            "added_bp": {
                "added_bp": interval_bp(baseline_added),
                "added_positive_bp": _overlap_bp(baseline_added, positive),
                "added_negative_bp": interval_bp(baseline_added) - _overlap_bp(baseline_added, positive) - _overlap_bp(baseline_added, effective_unknown),
                "added_unknown_bp": _overlap_bp(baseline_added, effective_unknown),
                "precision_bootstrap": added_bp_precision_bootstrap(rows, baseline_selected, positive, effective_unknown),
            },
            "whole_mask": {
                "raw": whole_mask_metrics(raw_mask, positive, effective_unknown, chromosome_length),
                "refined": whole_mask_metrics(baseline_mask, positive, effective_unknown, chromosome_length),
            },
            "fragmentation": {
                "raw": raw_fragment,
                "refined": _fragment_metrics(baseline_mask, truth_runs)[0],
            },
            "internal_gap_recovery": internal_gap_recovery(raw_mask, baseline_mask, truth_runs),
            "added_positive_recall": None if baseline_truth == 0 else _overlap_bp(baseline_added, positive) / baseline_truth,
        }
    gate_metrics = {
        "added_bp": {
            "selected_candidates": int(selected.sum()),
            "added_bp": interval_bp(added_intervals),
            "added_positive_bp": added_positive,
            "added_negative_bp": added_negative,
            "added_unknown_bp": added_unknown,
            "precision": None if added_positive + added_negative == 0 else added_positive / (added_positive + added_negative),
            "recall": None if interval_bp(truth_runs) == 0 else added_positive / interval_bp(truth_runs),
            "precision_bootstrap": added_bp_precision_bootstrap(rows, selected, positive, effective_unknown),
        },
        "whole_mask": {
            "raw": whole_mask_metrics(raw_mask, positive, effective_unknown, chromosome_length),
            "refined": whole_mask_metrics(refined_mask, positive, effective_unknown, chromosome_length),
        },
        "fragmentation": {"raw": raw_fragment, "refined": refined_fragment},
        "internal_gap_recovery": internal,
        "baseline": baseline_result,
    }
    blocks = block_summaries(rows, selected, raw_mask, refined_mask, positive, effective_unknown, chromosome_length)
    write_refined_mask(refined_canonical_path, refined_mask)
    write_selected_sidecar(selected_sidecar_path, rows, scores, threshold, selected)
    result: dict[str, object] = {
        "schema": "gap_bridge_phase0_mask_fragment_gate_v1",
        "status": "PARTIAL_GATE_NO_GENE_SAFETY",
        "feature_lock": str(feature_lock_path),
        "candidate_evaluation": str(candidate_evaluation_path),
        "labeled_test": str(labeled_path),
        "p3_canonical": str(p3_canonical_path),
        "refined_canonical": str(refined_canonical_path),
        "selected_sidecar": str(selected_sidecar_path),
        "test_chromosome": CHROMOSOME,
        "chromosome_length": chromosome_length,
        "test_labels_read": True,
        "frozen_g2_threshold": threshold,
        "comparator_positive_bp": interval_bp(positive),
        "comparator_unknown_source": str(comparator_unknown_path),
        "comparator_unknown_source_bp": interval_bp(raw_unknown),
        "comparator_unknown_effective_bp": interval_bp(effective_unknown),
        "candidate_count": len(rows),
        "excluded_unknown_candidates": excluded_unknown,
        "selected_gap_count": int(selected.sum()),
        "all_original_p3_positive_bases_retained": not subtract_intervals(raw_mask, refined_mask),
        "operating_route": (
            "G2_ONLY_SAFE_OPERATING_POINT" if operating_baseline is None
            else "G2_PLUS_FROZEN_OPERATING_BASELINE"
        ),
        "selected_gap_ids": [rows[index]["candidate_id"] for index in np.flatnonzero(selected)],
        "metrics": gate_metrics,
        "block_size_bp": BLOCK_SIZE,
        "block_summaries": blocks,
        "prospective_gate": {
            "status": "NOT_EVALUATED",
            "unavailable_metrics": [
                "gene_overlap_added_negative_bp", "gene_overlap_added_bp_precision",
                "canonical_splice_core_negative_bp", "callable_cds_negative_fill_rate",
                "affected_genes", "affected_exons",
            ],
            "candidate_and_mask_metrics_are_not_a_full_gate": True,
        },
        "selection_and_thresholds": "G2 parameters and threshold were read directly from feature_lock.json; no refit or chr19 threshold matching was performed",
        "candidate_evaluation_status": candidate_evaluation.get("status"),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-lock", required=True, type=Path)
    parser.add_argument("--candidate-evaluation", required=True, type=Path)
    parser.add_argument("--labeled", required=True, type=Path)
    parser.add_argument("--p3-canonical", required=True, type=Path)
    parser.add_argument("--comparator-positive", required=True, type=Path)
    parser.add_argument("--comparator-unknown", required=True, type=Path)
    parser.add_argument("--chromosome-length", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--refined-canonical", required=True, type=Path)
    parser.add_argument("--selected-sidecar", required=True, type=Path)
    args = parser.parse_args(argv)
    evaluate_mask_fragment_gate(
        args.feature_lock, args.candidate_evaluation, args.labeled, args.p3_canonical,
        args.comparator_positive, args.comparator_unknown, args.chromosome_length,
        args.output, args.refined_canonical, args.selected_sidecar,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
