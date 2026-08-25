#!/usr/bin/env python3
"""Stratify strict TE interval metrics by frozen truth-run length.

Inputs are canonical interval TSVs produced by the LEMMI TE adapter.  Truth
and prediction intervals are first flattened to non-overlapping runs, then
predictions are greedily matched one-to-one to truth runs at the requested
IoU threshold.  Only after that global matching are truth runs assigned to
the four length bins.

For a length bin, ``pred_segments`` contains predictions that overlap a truth
run in that bin (including below-IoU false positives).  Predictions with no
truth overlap are counted in ``unassigned_prediction_segments`` and in the
overall T0 denominator, but cannot be assigned to a truth-length bin.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]
BIN_LABELS = ("<80", "80-499", "500-999", ">=1000")


def read_canonical(path: Path) -> list[tuple[str, int, int]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != FIELDS:
            raise ValueError(f"canonical fields must be {FIELDS}")
        rows = []
        for row in reader:
            start = int(row["start"])
            end = int(row["end"])
            if not row["seqid"] or start < 0 or end <= start:
                raise ValueError("invalid canonical interval")
            rows.append((row["seqid"], start, end))
    return rows


def read_lengths(path: Path) -> dict[str, int]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or any(not isinstance(v, int) or v < 1 for v in value.values()):
        raise ValueError("lengths must be a JSON object of positive integer lengths")
    return {str(key): value for key, value in value.items()}


def union_runs(rows: list[tuple[str, int, int]], lengths: dict[str, int]) -> list[tuple[str, int, int]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for seqid, start, end in rows:
        if seqid not in lengths:
            raise ValueError(f"interval seqid {seqid!r} missing from lengths")
        if end > lengths[seqid]:
            raise ValueError(f"interval exceeds contig length: {seqid}:{start}-{end}")
        grouped.setdefault(seqid, []).append((start, end))

    runs: list[tuple[str, int, int]] = []
    for seqid in sorted(grouped):
        current_start, current_end = sorted(grouped[seqid])[0]
        for start, end in sorted(grouped[seqid])[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                runs.append((seqid, current_start, current_end))
                current_start, current_end = start, end
        runs.append((seqid, current_start, current_end))
    return runs


def overlap_iou(left: tuple[str, int, int], right: tuple[str, int, int]) -> tuple[int, float]:
    if left[0] != right[0]:
        return 0, 0.0
    overlap = max(0, min(left[2], right[2]) - max(left[1], right[1]))
    if not overlap:
        return 0, 0.0
    union = max(left[2], right[2]) - min(left[1], right[1])
    return overlap, overlap / union


def global_match(
    truth_runs: list[tuple[str, int, int]],
    pred_runs: list[tuple[str, int, int]],
    iou_threshold: float,
) -> tuple[dict[int, int], dict[int, int | None]]:
    """Return one-to-one ``truth_index -> pred_index`` and pred assignments.

    A prediction not reaching the IoU threshold is still assigned to its
    highest-overlap truth for per-bin false-positive accounting.  Predictions
    with no overlap are assigned ``None``.
    """
    truth_by_seq: dict[str, list[int]] = {}
    for index, (seqid, _start, _end) in enumerate(truth_runs):
        truth_by_seq.setdefault(seqid, []).append(index)
    matched_truth: dict[int, int] = {}
    pred_assignment: dict[int, int | None] = {}
    used_truth: set[int] = set()

    for pred_index, pred in enumerate(pred_runs):
        best_any: tuple[float, int] | None = None
        best_free: tuple[float, int] | None = None
        for truth_index in truth_by_seq.get(pred[0], []):
            _overlap, iou = overlap_iou(pred, truth_runs[truth_index])
            if iou <= 0:
                continue
            candidate = (iou, truth_index)
            if best_any is None or candidate[0] > best_any[0]:
                best_any = candidate
            if truth_index not in used_truth and (best_free is None or candidate[0] > best_free[0]):
                best_free = candidate

        pred_assignment[pred_index] = best_any[1] if best_any is not None else None
        if best_free is not None and best_free[0] >= iou_threshold:
            truth_index = best_free[1]
            used_truth.add(truth_index)
            matched_truth[truth_index] = pred_index
            pred_assignment[pred_index] = truth_index
    return matched_truth, pred_assignment


def length_bin(length: int) -> str:
    if length < 80:
        return "<80"
    if length < 500:
        return "80-499"
    if length < 1000:
        return "500-999"
    return ">=1000"


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _summary(
    truth_indices: list[int],
    pred_indices: list[int],
    matched_truth: dict[int, int],
    truth_runs: list[tuple[str, int, int]],
    pred_runs: list[tuple[str, int, int]],
    fragment_counts: dict[int, int],
    truth_tier: str,
    boundary_tolerances: tuple[int, ...],
) -> dict[str, object]:
    truth_count = len(truth_indices)
    pred_count = len(pred_indices)
    true_positive = sum(index in matched_truth for index in truth_indices)
    false_negative = truth_count - true_positive
    false_positive = pred_count - true_positive
    recall = true_positive / truth_count if truth_count else 0.0
    precision = true_positive / pred_count if pred_count else 0.0
    row: dict[str, object] = {
        "truth_segments": truth_count,
        "pred_segments": pred_count,
        "segment_tp": true_positive,
        "segment_fn": false_negative,
        "segment_recall": recall,
        "mean_fragments_per_true": sum(fragment_counts[index] for index in truth_indices) / truth_count
        if truth_count
        else 0.0,
        "split_true_rate": sum(fragment_counts[index] > 1 for index in truth_indices) / truth_count
        if truth_count
        else 0.0,
        "missed_true_rate": sum(fragment_counts[index] == 0 for index in truth_indices) / truth_count
        if truth_count
        else 0.0,
    }
    for tolerance in boundary_tolerances:
        hits = 0
        for truth_index in truth_indices:
            pred_index = matched_truth.get(truth_index)
            if pred_index is None:
                continue
            truth = truth_runs[truth_index]
            pred = pred_runs[pred_index]
            if abs(pred[1] - truth[1]) <= tolerance and abs(pred[2] - truth[2]) <= tolerance:
                hits += 1
        boundary_recall = hits / truth_count if truth_count else 0.0
        boundary_precision = hits / pred_count if pred_count else 0.0
        row[f"boundary_hits_{tolerance}bp"] = hits
        row[f"boundary_recall_{tolerance}bp"] = boundary_recall
        if truth_tier == "T1":
            row[f"boundary_precision_{tolerance}bp"] = None
            row[f"boundary_f1_{tolerance}bp"] = None
        else:
            row[f"boundary_precision_{tolerance}bp"] = boundary_precision
            row[f"boundary_f1_{tolerance}bp"] = _f1(boundary_precision, boundary_recall)
    if truth_tier == "T1":
        row["segment_fp"] = None
        row["segment_precision"] = None
        row["segment_f1"] = None
    else:
        row["segment_fp"] = false_positive
        row["segment_precision"] = precision
        row["segment_f1"] = _f1(precision, recall)
    return row


def evaluate(
    truth_rows: list[tuple[str, int, int]],
    pred_rows: list[tuple[str, int, int]],
    lengths: dict[str, int],
    *,
    truth_tier: str = "T0",
    iou_threshold: float = 0.8,
    boundary_tolerances: tuple[int, ...] = (5, 25),
) -> dict[str, object]:
    if truth_tier not in {"T0", "T1"}:
        raise ValueError("truth_tier must be T0 or T1")
    truth_runs = union_runs(truth_rows, lengths)
    pred_runs = union_runs(pred_rows, lengths)
    matched_truth, pred_assignment = global_match(truth_runs, pred_runs, iou_threshold)
    fragment_counts = {
        truth_index: sum(overlap_iou(truth, pred)[0] > 0 for pred in pred_runs)
        for truth_index, truth in enumerate(truth_runs)
    }
    truth_bins = {label: [] for label in BIN_LABELS}
    for index, (_seqid, start, end) in enumerate(truth_runs):
        truth_bins[length_bin(end - start)].append(index)
    pred_bins = {label: [] for label in BIN_LABELS}
    unassigned_predictions = 0
    for pred_index, truth_index in pred_assignment.items():
        if truth_index is None:
            unassigned_predictions += 1
        else:
            pred_bins[length_bin(truth_runs[truth_index][2] - truth_runs[truth_index][1])].append(pred_index)

    result: dict[str, object] = {
        "truth_tier": truth_tier,
        "iou_threshold": iou_threshold,
        "boundary_tolerances_bp": list(boundary_tolerances),
        "truth_runs": len(truth_runs),
        "prediction_runs": len(pred_runs),
        "unassigned_prediction_segments": unassigned_predictions,
        "prediction_bin_denominator": "truth-associated predictions; unassigned predictions are overall-only",
    }
    result["overall"] = _summary(
        list(range(len(truth_runs))),
        list(range(len(pred_runs))),
        matched_truth,
        truth_runs,
        pred_runs,
        fragment_counts,
        truth_tier,
        boundary_tolerances,
    )
    result["bins"] = {
        label: _summary(
            truth_bins[label],
            pred_bins[label],
            matched_truth,
            truth_runs,
            pred_runs,
            fragment_counts,
            truth_tier,
            boundary_tolerances,
        )
        for label in BIN_LABELS
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, required=True, help="canonical truth TSV")
    parser.add_argument("--prediction", type=Path, required=True, help="canonical prediction TSV")
    parser.add_argument("--lengths", type=Path, required=True, help="JSON object of contig lengths")
    parser.add_argument("--truth-tier", choices=["T0", "T1"], default="T0")
    parser.add_argument("--iou-threshold", type=float, default=0.8)
    parser.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5, 25])
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(
        read_canonical(args.truth),
        read_canonical(args.prediction),
        read_lengths(args.lengths),
        truth_tier=args.truth_tier,
        iou_threshold=args.iou_threshold,
        boundary_tolerances=tuple(args.boundary_tolerances),
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
