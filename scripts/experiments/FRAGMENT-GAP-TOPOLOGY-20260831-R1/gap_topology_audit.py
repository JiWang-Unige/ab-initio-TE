#!/usr/bin/env python3
"""Audit false-negative gap topology without changing any predictions.

The input contract is deliberately narrow: truth and prediction intervals are
zero-based, half-open TSV/BED rows (``seqid, start, end``), and calibration is
a complete binary state track with a header (``seqid, start, end, state``).
Prediction rows are unioned into observed positive runs.  Internal zero runs
and terminal omissions are recorded separately; no gap is filled or otherwise
rescued.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


BINS = ("<80", "80-499", "500-999", ">=1000")
TRUTH_FIELDS = [
    "truth_id", "seqid", "truth_start", "truth_end", "truth_length",
    "truth_length_bin", "positive_runs_overlapping", "covered_bp",
    "uncovered_bp", "left_uncovered_bp", "right_uncovered_bp",
    "internal_gap_count", "internal_gap_bp", "missed", "split",
    "terminal_gap_count", "terminal_gap_bp",
    "iid_expected_positive_runs", "iid_expected_internal_gaps",
    "iid_expected_any_positive", "iid_expected_split",
    "markov_expected_positive_runs", "markov_expected_internal_gaps",
    "markov_expected_any_positive", "markov_expected_split",
]
GAP_FIELDS = [
    "event_type", "truth_id", "seqid", "truth_start", "truth_end", "truth_length",
    "truth_length_bin", "gap_start", "gap_end", "gap_length",
    "relative_start", "relative_end", "relative_mid",
    "before_positive_run_start", "before_positive_run_end",
    "before_positive_run_length", "after_positive_run_start",
    "after_positive_run_end", "after_positive_run_length",
    "distance_to_left_truth_boundary", "distance_to_right_truth_boundary",
    "touches_window_edge", "window_edge_side", "window_ids",
    "nearest_window_seam_signed_distance", "nearest_window_seam_abs_distance",
]
SUMMARY_FIELDS = [
    "truth_length_bin", "truth_intervals", "truth_bp", "covered_bp",
    "bp_recall", "truth_with_positive", "truth_with_positive_rate",
    "missed_truth_intervals", "missed_rate", "split_truth_intervals",
    "split_rate", "observed_fragments", "mean_fragments_per_truth",
    "median_fragments_per_truth", "internal_gap_truth_intervals",
    "internal_gap_truth_rate", "observed_internal_gaps", "internal_gap_bp",
    "internal_gap_bp_per_truth_bp", "mean_internal_gap_length",
    "median_internal_gap_length", "iid_expected_fragments",
    "iid_expected_internal_gaps", "markov_expected_fragments",
    "markov_expected_internal_gaps", "iid_expected_any_positive_rate",
    "iid_expected_split_rate", "markov_expected_any_positive_rate",
    "markov_expected_split_rate",
    "terminal_gap_records", "left_terminal_gap_records", "right_terminal_gap_records",
    "terminal_gap_bp", "left_terminal_gap_bp", "right_terminal_gap_bp",
]


@dataclass(frozen=True)
class Interval:
    seqid: str
    start: int
    end: int
    ident: str


def _open_text(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def _table(path: Path) -> tuple[list[str], list[dict[str, str]], bool]:
    with _open_text(path) as handle:
        lines = [line.rstrip("\r\n") for line in handle if line.strip() and not line.startswith("#")]
    if not lines:
        raise ValueError(f"empty interval input: {path}")
    first = lines[0].split("\t")
    lowered = {field.strip().lower() for field in first}
    has_header = bool({"start", "end"}.issubset(lowered) or {"start0", "end0"}.issubset(lowered))
    if has_header:
        fields = [field.strip() for field in first]
        if len(set(fields)) != len(fields):
            raise ValueError(f"duplicate columns in header: {path}")
        rows = []
        for line_number, line in enumerate(lines[1:], start=2):
            values = line.split("\t")
            if len(values) != len(fields):
                raise ValueError(f"wrong column count at {path}:{line_number}")
            rows.append(dict(zip(fields, values)))
        return fields, rows, True
    rows = []
    for line_number, line in enumerate(lines, start=1):
        values = line.split("\t")
        if len(values) < 3:
            raise ValueError(f"BED-like row has fewer than 3 columns at {path}:{line_number}")
        rows.append({"seqid": values[0], "start": values[1], "end": values[2], "name": values[3] if len(values) > 3 else ""})
    return ["seqid", "start", "end", "name"], rows, False


def _column(fields: Iterable[str], names: tuple[str, ...], required: bool = True) -> str | None:
    by_lower = {field.lower(): field for field in fields}
    for name in names:
        if name in by_lower:
            return by_lower[name]
    if required:
        raise ValueError(f"input needs one of columns {names}")
    return None


def _integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer for {label}: {value!r}") from error


def _intervals(path: Path, *, truth: bool = False, windows: bool = False) -> list[Interval]:
    fields, rows, _ = _table(path)
    seq_col = _column(fields, ("seqid", "chrom", "chromosome", "contig"))
    start_col = _column(fields, ("start", "start0"))
    end_col = _column(fields, ("end", "end0"))
    id_col = _column(fields, ("truth_id", "id", "feature_id"), required=False)
    name_col = _column(fields, ("name",), required=False)
    explicit_ids = [row[id_col] for row in rows] if id_col else []
    if id_col and (not all(explicit_ids) or len(set(explicit_ids)) != len(explicit_ids)):
        raise ValueError(f"explicit IDs must be non-empty and unique: {path}")
    names = [row[name_col] for row in rows] if name_col else []
    use_names = bool(names and all(names) and len(set(names)) == len(names))
    result = []
    for index, row in enumerate(rows, start=1):
        seqid = row[seq_col]
        start = _integer(row[start_col], f"{path}:{index}.start")
        end = _integer(row[end_col], f"{path}:{index}.end")
        if not seqid or start < 0 or end <= start:
            raise ValueError(f"invalid zero-based half-open interval at {path}:{index}")
        if id_col:
            ident = row[id_col]
        elif use_names:
            ident = row[name_col]  # type: ignore[index]
        elif truth:
            ident = f"truth_{index:06d}"
        elif windows:
            ident = f"window_{index:06d}"
        else:
            ident = f"interval_{index:06d}"
        result.append(Interval(seqid, start, end, ident))
    if truth:
        ordered = sorted(result, key=lambda x: (x.seqid, x.start, x.end))
        previous: dict[str, Interval] = {}
        for interval in ordered:
            prior = previous.get(interval.seqid)
            if prior and interval.start < prior.end:
                raise ValueError(f"truth intervals overlap: {prior.ident} and {interval.ident}")
            previous[interval.seqid] = interval
    return result


def _calibration(path: Path) -> dict[str, object]:
    fields, rows, has_header = _table(path)
    if not has_header:
        raise ValueError("calibration input must have a header with seqid, start, end, state")
    seq_col = _column(fields, ("seqid", "chrom", "chromosome", "contig"))
    start_col = _column(fields, ("start", "start0"))
    end_col = _column(fields, ("end", "end0"))
    state_col = _column(fields, ("state", "label"))
    by_seq: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        start = _integer(row[start_col], f"{path}:{index}.start")
        end = _integer(row[end_col], f"{path}:{index}.end")
        state = _integer(row[state_col], f"{path}:{index}.state")
        if start < 0 or end <= start or state not in (0, 1):
            raise ValueError(f"invalid calibration row at {path}:{index}")
        by_seq[row[seq_col]].append((start, end, state))
    if not by_seq:
        raise ValueError(f"empty calibration input: {path}")
    counts = Counter({"00": 0, "01": 0, "10": 0, "11": 0})
    state_bp = Counter({0: 0, 1: 0})
    first_states: list[int] = []
    for seqid, parts in by_seq.items():
        parts.sort()
        if parts[0][0] != 0:
            raise ValueError(f"calibration sequence does not start at zero: {seqid}")
        first_states.append(parts[0][2])
        previous_state = None
        previous_end = 0
        for start, end, state in parts:
            if start != previous_end:
                raise ValueError(f"calibration intervals must form a complete track: {seqid}")
            length = end - start
            state_bp[state] += length
            if length > 1:
                counts[f"{state}{state}"] += length - 1
            if previous_state is not None:
                counts[f"{previous_state}{state}"] += 1
            previous_state = state
            previous_end = end
    total_bp = state_bp[0] + state_bp[1]
    p1 = state_bp[1] / total_bp
    n0 = counts["00"] + counts["01"]
    n1 = counts["10"] + counts["11"]
    if not n0 or not n1:
        raise ValueError("calibration must contain transitions out of both states")
    p01 = counts["01"] / n0
    p10 = counts["10"] / n1
    return {
        "path": str(path),
        "sequences": len(by_seq),
        "total_bp": total_bp,
        "state_bp": {"0": state_bp[0], "1": state_bp[1]},
        "transition_counts": dict(counts),
        "positive_probability": p1,
        "initial_positive_probability": sum(first_states) / len(first_states),
        "p_positive_given_negative": p01,
        "p_negative_given_positive": p10,
    }


def _bin(length: int) -> str:
    if length < 80:
        return "<80"
    if length < 500:
        return "80-499"
    if length < 1000:
        return "500-999"
    return ">=1000"


def _iid(length: int, p1: float) -> dict[str, float]:
    if length <= 0:
        return {
            "expected_positive_runs": 0.0,
            "expected_internal_gaps": 0.0,
            "expected_any_positive": 0.0,
            "expected_split": 0.0,
        }
    q = 1.0 - p1
    positive_runs = p1 + (length - 1) * q * p1
    any_positive = 1.0 - q**length
    internal_gaps = 0.0
    if length >= 3:
        n = length - 2
        geometric = q * (1.0 - q**n) / (1.0 - q) if q != 1.0 else float(n)
        internal_gaps = p1 * q * (n - geometric)
    split = _split_probability(length, p1, p1, q)
    return {
        "expected_positive_runs": positive_runs,
        "expected_internal_gaps": internal_gaps,
        "expected_any_positive": any_positive,
        "expected_split": split,
    }


def _markov(length: int, pi1: float, p01: float, p10: float) -> dict[str, float]:
    if length <= 0:
        return {
            "expected_positive_runs": 0.0,
            "expected_internal_gaps": 0.0,
            "expected_any_positive": 0.0,
            "expected_split": 0.0,
        }
    prob1 = pi1
    positive_runs = prob1
    covered_bp = prob1
    for _ in range(1, length):
        next_prob1 = prob1 * (1.0 - p10) + (1.0 - prob1) * p01
        positive_runs += (1.0 - prob1) * p01
        covered_bp += next_prob1
        prob1 = next_prob1
    internal_gaps = 0.0
    prob1_before = pi1
    for position in range(1, max(1, length - 1)):
        remaining = length - position - 1
        if remaining <= 0:
            break
        internal_gaps += prob1_before * p10 * (1.0 - (1.0 - p01) ** remaining)
        prob1_before = prob1_before * (1.0 - p10) + (1.0 - prob1_before) * p01
    return {
        "expected_positive_runs": positive_runs,
        "expected_internal_gaps": internal_gaps,
        "expected_any_positive": 1.0 - (1.0 - pi1) * (1.0 - p01) ** (length - 1),
        "expected_split": _split_probability(length, pi1, p01, p10),
    }


def _split_probability(length: int, pi1: float, p01: float, p10: float) -> float:
    """Return exact P(at least two positive runs) by a stable four-state DP."""
    if length <= 0:
        return 0.0
    # A/B/C/D are zero positive-runs/last zero, one run/last one, one
    # run/last zero, and at least two runs.  D is absorbing.
    a, b, c, d = 1.0 - pi1, pi1, 0.0, 0.0
    for _ in range(1, length):
        a, b, c, d = (
            a * (1.0 - p01),
            a * p01 + b * (1.0 - p10),
            b * p10 + c * (1.0 - p01),
            d + c * p01,
        )
    return d


def _merge(intervals: list[Interval]) -> dict[str, list[Interval]]:
    grouped: dict[str, list[Interval]] = defaultdict(list)
    for interval in intervals:
        grouped[interval.seqid].append(interval)
    merged: dict[str, list[Interval]] = defaultdict(list)
    for seqid in sorted(grouped):
        ordered = sorted(grouped[seqid], key=lambda x: (x.start, x.end))
        for interval in ordered:
            if not merged[seqid] or interval.start > merged[seqid][-1].end:
                merged[seqid].append(interval)
            else:
                prior = merged[seqid][-1]
                merged[seqid][-1] = Interval(seqid, prior.start, max(prior.end, interval.end), prior.ident)
    return merged


WindowIndexEntry = tuple[list[Interval], list[Interval], list[int], list[int], list[int]]


def _window_index(windows: dict[str, list[Interval]]) -> dict[str, WindowIndexEntry]:
    index: dict[str, WindowIndexEntry] = {}
    for seqid, values in windows.items():
        start_windows = sorted(values, key=lambda x: (x.start, x.end, x.ident))
        end_windows = sorted(values, key=lambda x: (x.end, x.start, x.ident))
        index[seqid] = (
            start_windows,
            end_windows,
            [window.start for window in start_windows],
            [window.end for window in end_windows],
            sorted({coordinate for value in values for coordinate in (value.start, value.end)}),
        )
    return index


def _edge_info(
    gap: tuple[int, int],
    windows: dict[str, list[Interval]] | dict[str, WindowIndexEntry] | None,
    seqid: str,
) -> tuple[str, str, str, str, str]:
    if windows is None:
        return "NA", "", "", "NA", "NA"
    sides: set[str] = set()
    start, end = gap
    entry = windows.get(seqid)
    if entry is None:
        return "0", "", "", "NA", "NA"
    if isinstance(entry, list):
        start_windows, end_windows, start_coordinates, end_coordinates, seams = _window_index(windows)[seqid]
    else:
        start_windows, end_windows, start_coordinates, end_coordinates, seams = entry
    left_start = bisect.bisect_left(start_coordinates, start)
    left_end = bisect.bisect_left(start_coordinates, end)
    right_start = bisect.bisect_right(end_coordinates, start)
    right_end = bisect.bisect_right(end_coordinates, end)
    touched = {
        window.ident for window in start_windows[left_start:left_end]
    }
    touched.update(window.ident for window in end_windows[right_start:right_end])
    if left_start < left_end:
        sides.add("left")
    if right_start < right_end:
        sides.add("right")
    if not seams:
        signed, absolute = "NA", "NA"
    else:
        # Distance is to the gap interval, not its midpoint: a seam inside a
        # gap is distance zero; a seam before/after it is signed negative/
        # positive, respectively.  Ties are resolved by coordinate.
        candidates = []
        seam_index = bisect.bisect_left(seams, start)
        nearby_seams = seams[seam_index:seam_index + 1]
        if seam_index:
            nearby_seams.append(seams[seam_index - 1])
        for seam in nearby_seams:
            if seam < start:
                distance = seam - start
            elif seam > end:
                distance = seam - end
            else:
                distance = 0
            candidates.append((abs(distance), distance, seam))
        _, distance, _ = min(candidates)
        signed, absolute = str(distance), str(abs(distance))
    return ("1" if sides else "0", ",".join(sorted(sides)), ",".join(sorted(touched)), signed, absolute)


def _gap_row(
    event_type: str,
    item: Interval,
    gap_start: int,
    gap_end: int,
    before: tuple[int, int] | None,
    after: tuple[int, int] | None,
    windows: dict[str, WindowIndexEntry] | None,
) -> dict[str, object]:
    edge, side, ids, seam_signed, seam_abs = _edge_info(
        (gap_start, gap_end), windows, item.seqid,
    )
    length = item.end - item.start
    return {
        "event_type": event_type, "truth_id": item.ident, "seqid": item.seqid,
        "truth_start": item.start, "truth_end": item.end, "truth_length": length,
        "truth_length_bin": _bin(length), "gap_start": gap_start, "gap_end": gap_end,
        "gap_length": gap_end - gap_start,
        "relative_start": (gap_start - item.start) / length,
        "relative_end": (gap_end - item.start) / length,
        "relative_mid": ((gap_start + gap_end) / 2 - item.start) / length,
        "before_positive_run_start": before[0] if before else "",
        "before_positive_run_end": before[1] if before else "",
        "before_positive_run_length": before[1] - before[0] if before else "",
        "after_positive_run_start": after[0] if after else "",
        "after_positive_run_end": after[1] if after else "",
        "after_positive_run_length": after[1] - after[0] if after else "",
        "distance_to_left_truth_boundary": gap_start - item.start,
        "distance_to_right_truth_boundary": item.end - gap_end,
        "touches_window_edge": edge, "window_edge_side": side, "window_ids": ids,
        "nearest_window_seam_signed_distance": seam_signed,
        "nearest_window_seam_abs_distance": seam_abs,
    }


def _analyze(
    truth: list[Interval],
    prediction_runs: dict[str, list[Interval]],
    calibration: dict[str, object],
    windows: dict[str, list[Interval]] | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    starts = {seqid: [interval.start for interval in runs] for seqid, runs in prediction_runs.items()}
    truth_rows: list[dict[str, object]] = []
    gap_rows: list[dict[str, object]] = []
    p1 = float(calibration["positive_probability"])
    pi1 = float(calibration["initial_positive_probability"])
    p01 = float(calibration["p_positive_given_negative"])
    p10 = float(calibration["p_negative_given_positive"])
    window_index = _window_index(windows) if windows is not None else None
    for item in truth:
        length = item.end - item.start
        overlapping: list[tuple[int, int]] = []
        runs = prediction_runs.get(item.seqid, [])
        index = max(0, bisect.bisect_left(starts.get(item.seqid, []), item.start) - 1)
        while index < len(runs) and runs[index].start < item.end:
            run = runs[index]
            clipped_start = max(item.start, run.start)
            clipped_end = min(item.end, run.end)
            if clipped_start < clipped_end:
                overlapping.append((clipped_start, clipped_end))
            index += 1
        covered_bp = sum(end - start for start, end in overlapping)
        internal_gaps: list[tuple[int, int, tuple[int, int], tuple[int, int]]] = []
        for before, after in zip(overlapping, overlapping[1:]):
            if before[1] < after[0]:
                internal_gaps.append((before[1], after[0], before, after))
        iid = _iid(length, p1)
        markov = _markov(length, pi1, p01, p10)
        row: dict[str, object] = {
            "truth_id": item.ident, "seqid": item.seqid, "truth_start": item.start,
            "truth_end": item.end, "truth_length": length, "truth_length_bin": _bin(length),
            "positive_runs_overlapping": len(overlapping), "covered_bp": covered_bp,
            "uncovered_bp": length - covered_bp,
            "left_uncovered_bp": (overlapping[0][0] - item.start) if overlapping else length,
            "right_uncovered_bp": (item.end - overlapping[-1][1]) if overlapping else 0,
            "internal_gap_count": len(internal_gaps),
            "internal_gap_bp": sum(end - start for start, end, _, _ in internal_gaps),
            "missed": int(not overlapping), "split": int(len(overlapping) > 1),
            "terminal_gap_count": (
                int(overlapping[0][0] > item.start) + int(overlapping[-1][1] < item.end)
                if overlapping else 0
            ),
            "terminal_gap_bp": (
                (overlapping[0][0] - item.start) + (item.end - overlapping[-1][1])
                if overlapping else 0
            ),
            "iid_expected_positive_runs": iid["expected_positive_runs"],
            "iid_expected_internal_gaps": iid["expected_internal_gaps"],
            "iid_expected_any_positive": iid["expected_any_positive"],
            "iid_expected_split": iid["expected_split"],
            "markov_expected_positive_runs": markov["expected_positive_runs"],
            "markov_expected_internal_gaps": markov["expected_internal_gaps"],
            "markov_expected_any_positive": markov["expected_any_positive"],
            "markov_expected_split": markov["expected_split"],
        }
        truth_rows.append(row)
        for gap_start, gap_end, before, after in internal_gaps:
            gap_rows.append(_gap_row("internal", item, gap_start, gap_end, before, after, window_index))
        if overlapping:
            first = overlapping[0]
            last = overlapping[-1]
            if item.start < first[0]:
                gap_rows.append(_gap_row("left_terminal", item, item.start, first[0], None, first, window_index))
            if last[1] < item.end:
                gap_rows.append(_gap_row("right_terminal", item, last[1], item.end, last, None, window_index))
    bin_rows: list[dict[str, object]] = []
    for length_bin in BINS:
        rows = [row for row in truth_rows if row["truth_length_bin"] == length_bin]
        if not rows:
            continue
        count = len(rows)
        truth_bp = sum(int(row["truth_length"]) for row in rows)
        covered_bp = sum(int(row["covered_bp"]) for row in rows)
        fragments = [int(row["positive_runs_overlapping"]) for row in rows]
        internal_gap_rows = [
            gap for gap in gap_rows
            if gap["event_type"] == "internal" and gap["truth_length_bin"] == length_bin
        ]
        terminal_gap_rows = [
            gap for gap in gap_rows
            if gap["event_type"] != "internal" and gap["truth_length_bin"] == length_bin
        ]
        gap_lengths = [int(gap["gap_length"]) for gap in internal_gap_rows]
        internal_truth = sum(int(row["internal_gap_count"]) > 0 for row in rows)
        expected_iid_fragments = sum(float(row["iid_expected_positive_runs"]) for row in rows)
        expected_iid_gaps = sum(float(row["iid_expected_internal_gaps"]) for row in rows)
        expected_iid_any = sum(float(row["iid_expected_any_positive"]) for row in rows)
        expected_iid_split = sum(float(row["iid_expected_split"]) for row in rows)
        expected_markov_fragments = sum(float(row["markov_expected_positive_runs"]) for row in rows)
        expected_markov_gaps = sum(float(row["markov_expected_internal_gaps"]) for row in rows)
        expected_markov_any = sum(float(row["markov_expected_any_positive"]) for row in rows)
        expected_markov_split = sum(float(row["markov_expected_split"]) for row in rows)
        bin_rows.append({
            "truth_length_bin": length_bin, "truth_intervals": count, "truth_bp": truth_bp,
            "covered_bp": covered_bp, "bp_recall": covered_bp / truth_bp,
            "truth_with_positive": sum(not int(row["missed"]) for row in rows),
            "truth_with_positive_rate": sum(not int(row["missed"]) for row in rows) / count,
            "missed_truth_intervals": sum(int(row["missed"]) for row in rows),
            "missed_rate": sum(int(row["missed"]) for row in rows) / count,
            "split_truth_intervals": sum(int(row["split"]) for row in rows),
            "split_rate": sum(int(row["split"]) for row in rows) / count,
            "observed_fragments": sum(fragments), "mean_fragments_per_truth": statistics.mean(fragments),
            "median_fragments_per_truth": statistics.median(fragments),
            "internal_gap_truth_intervals": internal_truth,
            "internal_gap_truth_rate": internal_truth / count,
            "observed_internal_gaps": sum(int(row["internal_gap_count"]) for row in rows),
            "internal_gap_bp": sum(int(row["internal_gap_bp"]) for row in rows),
            "internal_gap_bp_per_truth_bp": sum(int(row["internal_gap_bp"]) for row in rows) / truth_bp,
            "mean_internal_gap_length": statistics.mean(gap_lengths) if gap_lengths else 0.0,
            "median_internal_gap_length": statistics.median(gap_lengths) if gap_lengths else 0.0,
            "iid_expected_fragments": expected_iid_fragments,
            "iid_expected_internal_gaps": expected_iid_gaps,
            "markov_expected_fragments": expected_markov_fragments,
            "markov_expected_internal_gaps": expected_markov_gaps,
            "iid_expected_any_positive_rate": expected_iid_any / count,
            "iid_expected_split_rate": expected_iid_split / count,
            "markov_expected_any_positive_rate": expected_markov_any / count,
            "markov_expected_split_rate": expected_markov_split / count,
            "terminal_gap_records": len(terminal_gap_rows),
            "left_terminal_gap_records": sum(gap["event_type"] == "left_terminal" for gap in terminal_gap_rows),
            "right_terminal_gap_records": sum(gap["event_type"] == "right_terminal" for gap in terminal_gap_rows),
            "terminal_gap_bp": sum(int(gap["gap_length"]) for gap in terminal_gap_rows),
            "left_terminal_gap_bp": sum(int(gap["gap_length"]) for gap in terminal_gap_rows if gap["event_type"] == "left_terminal"),
            "right_terminal_gap_bp": sum(int(gap["gap_length"]) for gap in terminal_gap_rows if gap["event_type"] == "right_terminal"),
        })
    global_summary = {
        "truth_intervals": len(truth_rows), "truth_bp": sum(int(row["truth_length"]) for row in truth_rows),
        "observed_prediction_runs_total": sum(len(runs) for runs in prediction_runs.values()),
        "observed_prediction_runs_overlapping_truth": sum(int(row["positive_runs_overlapping"]) for row in truth_rows),
        "internal_gap_records": sum(gap["event_type"] == "internal" for gap in gap_rows),
        "terminal_gap_records": sum(gap["event_type"] != "internal" for gap in gap_rows),
        "terminal_gap_bp": sum(int(gap["gap_length"]) for gap in gap_rows if gap["event_type"] != "internal"),
        "windows_supplied": windows is not None,
        "truth_with_internal_gap": sum(int(row["internal_gap_count"]) > 0 for row in truth_rows),
    }
    return truth_rows, gap_rows, {"bins": bin_rows, "global": global_summary}


def _jsonable(value: object) -> object:
    if isinstance(value, Counter):
        return dict(value)
    return value


def _write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format(row.get(field, "")) for field in fields})


def _format(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _exclude_truth(
    truth: list[Interval], exclude_path: Path | None,
) -> tuple[list[Interval], list[Interval]]:
    if exclude_path is None:
        return truth, []
    exclusions = _intervals(exclude_path)
    by_seq: dict[str, list[Interval]] = defaultdict(list)
    for exclusion in exclusions:
        by_seq[exclusion.seqid].append(exclusion)
    kept: list[Interval] = []
    excluded_truth: list[Interval] = []
    for item in truth:
        if any(
            exclusion.start < item.end and item.start < exclusion.end
            for exclusion in by_seq.get(item.seqid, [])
        ):
            excluded_truth.append(item)
        else:
            kept.append(item)
    return kept, excluded_truth


def audit(
    truth_path: Path,
    prediction_path: Path,
    calibration_path: Path,
    windows_path: Path | None,
    output_dir: Path,
    exclude_path: Path | None = None,
) -> None:
    truth_all = _intervals(truth_path, truth=True)
    truth, excluded_truth = _exclude_truth(truth_all, exclude_path)
    prediction = _intervals(prediction_path)
    calibration = _calibration(calibration_path)
    windows_list = _intervals(windows_path, windows=True) if windows_path else None
    windows = defaultdict(list)
    if windows_list is not None:
        for window in windows_list:
            windows[window.seqid].append(window)
    prediction_runs = _merge(prediction)
    truth_rows, gap_rows, summaries = _analyze(truth, prediction_runs, calibration, windows if windows_list is not None else None)
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_tsv(output_dir / "truth_summary.tsv", TRUTH_FIELDS, truth_rows)
    _write_tsv(output_dir / "gap_records.tsv", GAP_FIELDS, gap_rows)
    _write_tsv(output_dir / "summary.tsv", SUMMARY_FIELDS, summaries["bins"])
    null_models = {
        "calibration": calibration,
        "iid_bernoulli": {
            "positive_probability": calibration["positive_probability"],
            "parameter_source": "explicit calibration/validation state track",
            "expectation_scope": "each truth interval is an independent length-L sequence; no flanking state is assumed",
            "expected_by_length_bin": summaries["bins"],
        },
        "markov_two_state": {
            "initial_positive_probability": calibration["initial_positive_probability"],
            "p_positive_given_negative": calibration["p_positive_given_negative"],
            "p_negative_given_positive": calibration["p_negative_given_positive"],
            "parameter_source": "explicit calibration/validation state track",
            "expectation_scope": "each truth interval starts from the calibration initial-state distribution; no test truth is used for parameters",
            "expected_by_length_bin": summaries["bins"],
        },
    }
    (output_dir / "null_models.json").write_text(json.dumps(null_models, indent=2, sort_keys=True, default=_jsonable) + "\n", encoding="utf-8")
    run_summary = {
        "schema": "fragment_gap_topology_audit_v1",
        "coordinate_contract": "zero-based half-open",
        "truth_input": str(truth_path), "prediction_input": str(prediction_path),
        "calibration_input": str(calibration_path), "windows_input": str(windows_path) if windows_path else None,
        "exclude_input": str(exclude_path) if exclude_path else None,
        "prediction_union": "overlapping_or_touching_prediction_intervals_form_one_positive_run",
        "gap_definition": "internal rows are maximal uncovered intervals bounded by two observed positive runs; terminal rows are uncovered truth prefixes/suffixes with one observed anchor",
        "fully_missed_truth_policy": "no gap row is emitted when a truth interval has no observed positive run; missed remains in truth_summary",
        "exclusion_policy": "any overlap with an exclusion interval removes the entire truth interval; excluded intervals are outside all reported denominators",
        "rescue_applied": False,
        "global": {
            **summaries["global"],
            "truth_intervals_before_exclusion": len(truth_all),
            "excluded_truth_intervals": len(excluded_truth),
            "excluded_truth_bp": sum(item.end - item.start for item in excluded_truth),
        },
    }
    (output_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, required=True, help="zero-based half-open truth intervals")
    parser.add_argument("--prediction", type=Path, required=True, help="zero-based half-open prediction intervals")
    parser.add_argument("--calibration", type=Path, required=True, help="complete binary validation/calibration state track")
    parser.add_argument("--windows", type=Path, help="optional zero-based evaluator/window intervals")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exclude-intervals", type=Path, help="truth intervals overlapping these rows are excluded wholesale")
    args = parser.parse_args()
    audit(args.truth, args.prediction, args.calibration, args.windows, args.output_dir, args.exclude_intervals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
