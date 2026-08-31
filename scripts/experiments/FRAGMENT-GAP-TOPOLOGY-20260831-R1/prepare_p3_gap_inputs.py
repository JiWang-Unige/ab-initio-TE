#!/usr/bin/env python3
"""Prepare frozen P3 tracks and windows for the gap-topology audit.

The ``chr11-validation`` mode runs the frozen C5 P3 model on the first 800
validation windows and exports thresholded canonical intervals plus one
independent calibration sequence for every truth-positive run.  The
``project-canonical`` mode makes the same track from already frozen canonical
truth and prediction intervals; its calibration is explicitly an in-sample
diagnostic and cannot select a rule.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WINDOW = 8192
VALIDATION_WINDOWS = 800
VALIDATION_CHROM = "chr11"
THRESHOLD = 0.5
WEIGHT_MODE = "triangular"
WINDOW_FIELDS = ["window_id", "seqid", "start", "end", "length"]
CALIBRATION_FIELDS = ["seqid", "start", "end", "state"]
RUN_FIELDS = ["seqid", "source_seqid", "source_start", "source_end", "length", "truth_run_index"]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _c5_module():
    return _load_module(
        ROOT / "scripts/experiments/C5-HYBRID-PILOT-20260830/c5_hybrid_pilot.py",
        "gap_inputs_c5_hybrid_pilot",
    )


def _gap_module():
    return _load_module(HERE / "gap_topology_audit.py", "gap_inputs_topology_audit")


def _records(path: Path, limit: int | None = None) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if limit is not None and index >= limit:
                break
            yield json.loads(line)


def _validate_window_rows(
    records: Iterable[dict[str, Any]], *, expected_chrom: str | None = None,
    require_full_window: bool = False,
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for index, row in enumerate(records):
        seqid = str(row["chr"])
        start, end = int(row["start"]), int(row["end"])
        sequence = str(row["sequence"])
        if expected_chrom is not None and seqid != expected_chrom:
            raise ValueError(f"window {index} is {seqid}, expected {expected_chrom}")
        length = end - start
        if start < 0 or length <= 0 or length > WINDOW or len(sequence) != length:
            raise ValueError(f"window {index} is not a valid <= {WINDOW}-bp interval")
        if require_full_window and length != WINDOW:
            raise ValueError(f"window {index} is not an exact {WINDOW}-bp interval")
        validated.append({"seqid": seqid, "start": start, "end": end, "length": length})
    if not validated:
        raise ValueError("no windows in JSONL input")
    return validated


def _write_windows(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WINDOW_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for index, row in enumerate(records, start=1):
            writer.writerow({
                "window_id": f"window_{index:06d}", "seqid": row["seqid"],
                "start": row["start"], "end": row["end"], "length": row["length"],
            })


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    return _c5_module().runs(mask)


def _rle_rows(seqid: str, states: np.ndarray) -> list[dict[str, Any]]:
    if states.ndim != 1 or states.size == 0 or not np.isin(states, [0, 1]).all():
        raise ValueError("RLE state track must be a non-empty binary vector")
    rows: list[dict[str, Any]] = []
    start = 0
    state = int(states[0])
    for end in range(1, states.size):
        next_state = int(states[end])
        if next_state != state:
            rows.append({"seqid": seqid, "start": start, "end": end, "state": state})
            start, state = end, next_state
    rows.append({"seqid": seqid, "start": start, "end": int(states.size), "state": state})
    return rows


def _write_calibration(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALIBRATION_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_canonical(path: Path, intervals: Iterable[tuple[str, int, int]], source: str) -> None:
    fields = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for seqid, start, end in intervals:
            writer.writerow({
                "seqid": seqid, "start": start, "end": end, "name": source,
                "score": ".", "strand": ".", "source": source, "attributes": ".",
            })


def _write_run_manifest(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _truth_intervals(
    truth_path: Path, exclude_path: Path | None, union_truth: bool,
) -> tuple[list[Any], list[Any]]:
    gap = _gap_module()
    truth_all = gap._load_truth(truth_path, union_truth)
    if exclude_path is None:
        return truth_all, []
    exclusions = gap._intervals(exclude_path)
    kept, excluded = [], []
    for item in truth_all:
        overlaps = any(
            exclusion.seqid == item.seqid
            and exclusion.start < item.end
            and item.start < exclusion.end
            for exclusion in exclusions
        )
        (excluded if overlaps else kept).append(item)
    return kept, excluded


def _track_from_prediction_intervals(
    truth_path: Path, prediction_path: Path, exclude_path: Path | None,
    union_truth: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[Any]]:
    truth, excluded = _truth_intervals(truth_path, exclude_path, union_truth)
    gap = _gap_module()
    prediction_runs = gap._merge(gap._intervals(prediction_path))
    starts = {
        seqid: [interval.start for interval in intervals]
        for seqid, intervals in prediction_runs.items()
    }
    calibration: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    for truth_index, item in enumerate(truth, start=1):
        states = np.zeros(item.end - item.start, dtype=np.int8)
        intervals = prediction_runs.get(item.seqid, [])
        index = max(0, bisect.bisect_left(starts.get(item.seqid, []), item.start) - 1)
        while index < len(intervals) and intervals[index].start < item.end:
            interval = intervals[index]
            start = max(item.start, interval.start)
            end = min(item.end, interval.end)
            if start < end:
                states[start - item.start:end - item.start] = 1
            index += 1
        seqid = f"truth_run_{truth_index:06d}"
        calibration.extend(_rle_rows(seqid, states))
        manifest.append({
            "seqid": seqid, "source_seqid": item.seqid,
            "source_start": item.start, "source_end": item.end,
            "length": item.end - item.start, "truth_run_index": truth_index,
        })
        truth_rows.append({"seqid": item.seqid, "start": item.start, "end": item.end})
    return calibration, manifest, truth_rows, excluded


def project_canonical(
    truth_path: Path, prediction_path: Path, output_dir: Path,
    exclude_path: Path | None = None, union_truth: bool = False,
) -> dict[str, Any]:
    calibration, manifest, truth_rows, excluded = _track_from_prediction_intervals(
        truth_path, prediction_path, exclude_path, union_truth,
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    calibration_path = output_dir / "in_sample.calibration.tsv"
    _write_calibration(calibration_path, calibration)
    _write_run_manifest(output_dir / "in_sample.truth_runs.tsv", manifest)
    result = {
        "schema": "p3_gap_in_sample_projection_v1",
        "status": "PASS",
        "diagnostic_scope": "in-sample diagnostic only",
        "rule_selection_allowed": False,
        "calibration_role": "exploratory null parameters from the same frozen truth/prediction inputs",
        "truth_input": str(truth_path), "prediction_input": str(prediction_path),
        "exclude_input": str(exclude_path) if exclude_path else None,
        "truth_union_applied": union_truth,
        "calibration": str(calibration_path), "truth_runs": len(truth_rows),
        "excluded_truth_runs": len(excluded),
        "excluded_truth_bp": sum(item.end - item.start for item in excluded),
        "coordinate_contract": "zero-based half-open; every truth run has an independent 0..L sequence",
    }
    (output_dir / "in_sample.manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return result


def chr11_validation(
    data_jsonl: Path, model_dir: Path, output_dir: Path,
) -> dict[str, Any]:
    c5 = _c5_module()
    records = _validate_window_rows(
        _records(data_jsonl, VALIDATION_WINDOWS),
        expected_chrom=VALIDATION_CHROM,
        require_full_window=True,
    )
    if len(records) != VALIDATION_WINDOWS:
        raise ValueError(f"validation input must contain exactly {VALIDATION_WINDOWS} windows")
    probabilities, truths = c5.assemble_track(
        data_jsonl, model_dir, VALIDATION_WINDOWS, WEIGHT_MODE,
    )
    if set(probabilities) != {VALIDATION_CHROM}:
        raise ValueError(f"validation input must contain only {VALIDATION_CHROM}")
    probability = probabilities[VALIDATION_CHROM]
    truth = truths[VALIDATION_CHROM]
    known = truth >= 0
    prediction_mask = (probability >= THRESHOLD) & known
    truth_mask = truth == 1
    truth_runs = _runs(truth_mask)
    prediction_runs = _runs(prediction_mask)
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_windows(output_dir / "validation.windows.tsv", records)
    _write_canonical(
        output_dir / "validation.truth.canonical.tsv",
        ((VALIDATION_CHROM, start, end) for start, end in truth_runs),
        "P3_GAP_VALIDATION_TRUTH",
    )
    _write_canonical(
        output_dir / "validation.prediction.canonical.tsv",
        ((VALIDATION_CHROM, start, end) for start, end in prediction_runs),
        "P3_GAP_VALIDATION_PREDICTION",
    )
    calibration: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for truth_index, (start, end) in enumerate(truth_runs, start=1):
        seqid = f"truth_run_{truth_index:06d}"
        calibration.extend(_rle_rows(seqid, prediction_mask[start:end].astype(np.int8)))
        manifest.append({
            "seqid": seqid, "source_seqid": VALIDATION_CHROM,
            "source_start": start, "source_end": end, "length": end - start,
            "truth_run_index": truth_index,
        })
    _write_calibration(output_dir / "validation.calibration.tsv", calibration)
    _write_run_manifest(output_dir / "validation.truth_runs.tsv", manifest)
    result = {
        "schema": "p3_gap_chr11_validation_inputs_v1", "status": "PASS",
        "diagnostic_scope": "out-of-sample validation track for gap-topology audit",
        "rule_selection_allowed": False,
        "data_jsonl": str(data_jsonl), "model_dir": str(model_dir),
        "chrom": VALIDATION_CHROM, "windows": VALIDATION_WINDOWS,
        "threshold": THRESHOLD, "weight_mode": WEIGHT_MODE,
        "truth_runs": len(truth_runs), "prediction_runs": len(prediction_runs),
        "coordinates": "zero-based half-open; each truth run calibration sequence is independent 0..L",
        "outputs": {
            "windows": str(output_dir / "validation.windows.tsv"),
            "truth": str(output_dir / "validation.truth.canonical.tsv"),
            "prediction": str(output_dir / "validation.prediction.canonical.tsv"),
            "calibration": str(output_dir / "validation.calibration.tsv"),
        },
    }
    (output_dir / "validation.manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return result


def windows_only(data_jsonl: Path, output_path: Path, max_windows: int | None) -> dict[str, Any]:
    records = _validate_window_rows(_records(data_jsonl, max_windows))
    _write_windows(output_path, records)
    return {"schema": "p3_gap_windows_v1", "status": "PASS", "windows": len(records), "input": str(data_jsonl)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validation = sub.add_parser("chr11-validation")
    validation.add_argument("--data-jsonl", type=Path, required=True)
    validation.add_argument("--model-dir", type=Path, required=True)
    validation.add_argument("--output-dir", type=Path, required=True)
    project = sub.add_parser("project-canonical")
    project.add_argument("--truth", type=Path, required=True)
    project.add_argument("--prediction", type=Path, required=True)
    project.add_argument("--output-dir", type=Path, required=True)
    project.add_argument("--exclude-intervals", type=Path)
    project.add_argument("--union-truth", action="store_true")
    windows = sub.add_parser("windows")
    windows.add_argument("--data-jsonl", type=Path, required=True)
    windows.add_argument("--output", type=Path, required=True)
    windows.add_argument("--max-windows", type=int)
    args = parser.parse_args()
    if args.command == "chr11-validation":
        result = chr11_validation(args.data_jsonl, args.model_dir, args.output_dir)
    elif args.command == "project-canonical":
        result = project_canonical(
            args.truth, args.prediction, args.output_dir,
            args.exclude_intervals, args.union_truth,
        )
    else:
        result = windows_only(args.data_jsonl, args.output, args.max_windows)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
