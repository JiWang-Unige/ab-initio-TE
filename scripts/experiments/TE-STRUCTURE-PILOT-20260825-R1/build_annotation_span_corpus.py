#!/usr/bin/env python3
"""Build annotation-conditioned span-MLM masks from binary 8192-bp windows.

The input labels are reference-annotation runs, not biological copy boundaries.
The output therefore supports a comparator-conditioned engineering pilot only.
Interior candidates stay at least +/-64 bp from a known transition.  Boundary
candidates are the narrower +/-24-bp position bands whose 32-bp spans cross
the transition with at least 8 bp on each side.  Flanks are clean background
positions 64-256 bp outside a usable boundary.  Separated positive runs are
scanned independently and are never connected.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Iterable, Iterator


WINDOW = 8192
BOUNDARY_HALF_WIDTH = 64
BOUNDARY_CANDIDATE_HALF_WIDTH = 24
BOUNDARY_MIN_EACH_SIDE = 8
SPAN_LENGTH = 32
DEFAULT_FLANK_BP = 256
FLANK_MIN_DISTANCE = 64
FLANK_MAX_DISTANCE = 256
CLEAN_OUTSIDE_BP = 128


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def _open_output(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "wt", encoding="utf-8")
    return path.open("wt", encoding="utf-8")


def _known(labels: list[int], sequence: str, value: int, index: int) -> bool:
    return labels[index] == value and sequence[index].upper() != "N"


def _positive_runs(labels: list[int], sequence: str) -> Iterator[tuple[int, int]]:
    index = 0
    while index < WINDOW:
        if not _known(labels, sequence, 1, index):
            index += 1
            continue
        start = index
        index += 1
        while index < WINDOW and _known(labels, sequence, 1, index):
            index += 1
        yield start, index


def _mask(window: int, positions: Iterable[int]) -> list[bool]:
    result = [False] * window
    for index in positions:
        result[index] = True
    return result


def _transition_records(labels: list[int], sequence: str) -> list[tuple[int, int, int, int]]:
    """Return known run boundaries as ``(edge, run_index, outer_left, outer_right)``."""
    runs = list(_positive_runs(labels, sequence))
    transitions: list[tuple[int, int, int, int]] = []
    for run_index, (start, end) in enumerate(runs):
        if start > 0 and _known(labels, sequence, 0, start - 1):
            transitions.append((start, run_index, start - CLEAN_OUTSIDE_BP, start))
        if end < WINDOW and _known(labels, sequence, 0, end):
            transitions.append((end, run_index, end, end + CLEAN_OUTSIDE_BP))
    return transitions


def _clean_external_boundary(
    labels: list[int],
    sequence: str,
    transition: tuple[int, int, int, int],
    runs: list[tuple[int, int]],
) -> bool:
    edge, run_index, outer_left, outer_right = transition
    if outer_left < 0 or outer_right > WINDOW:
        return False
    if not all(_known(labels, sequence, 0, index) for index in range(outer_left, outer_right)):
        return False
    for other_index, (start, end) in enumerate(runs):
        if other_index != run_index and start < outer_right and outer_left < end:
            return False
    return True


def _boundary_intervals(labels: list[int], sequence: str) -> list[tuple[int, int]]:
    """Return usable 32-bp boundary candidate position bands."""
    runs = list(_positive_runs(labels, sequence))
    intervals: list[tuple[int, int]] = []
    for transition in _transition_records(labels, sequence):
        edge, _run_index, _outer_left, _outer_right = transition
        if not _clean_external_boundary(labels, sequence, transition, runs):
            continue
        left = edge - BOUNDARY_CANDIDATE_HALF_WIDTH
        right = edge + BOUNDARY_CANDIDATE_HALF_WIDTH
        if left < 0 or right > WINDOW:
            continue
        if not all(
            _known(labels, sequence, 0, index) or _known(labels, sequence, 1, index)
            for index in range(left, right)
        ):
            continue
        for start in range(left, right - SPAN_LENGTH + 1):
            end = start + SPAN_LENGTH
            if not (start < edge < end):
                raise ValueError("boundary candidate band contains a span that does not cross its transition")
            if edge - start < BOUNDARY_MIN_EACH_SIDE or end - edge < BOUNDARY_MIN_EACH_SIDE:
                raise ValueError("boundary candidate span violates the minimum bases on each side")
        intervals.append((left, right))

    # A single binary candidate mask cannot represent overlapping or touching
    # bands without creating starts that need not cross one transition. Drop
    # every colliding band; short/adjacent runs remain available only where
    # their unambiguous interior is at least 64 bp from a transition.
    keep = [True] * len(intervals)
    for left_index, (left, right) in enumerate(intervals):
        for right_index in range(left_index + 1, len(intervals)):
            other_left, other_right = intervals[right_index]
            if left <= other_right and other_left <= right:
                keep[left_index] = False
                keep[right_index] = False
    return [interval for index, interval in enumerate(intervals) if keep[index]]


def build_record(record: dict, *, flank_bp: int = DEFAULT_FLANK_BP) -> dict:
    sequence = record["sequence"]
    labels = record["labels"]
    if not isinstance(sequence, str) or len(sequence) != WINDOW:
        raise ValueError(f"sequence length is not {WINDOW}")
    if not isinstance(labels, list) or len(labels) != WINDOW:
        raise ValueError(f"labels length is not {WINDOW}")
    if any(value not in (-100, 0, 1) for value in labels):
        raise ValueError("labels must contain only -100, 0 and 1")
    if not FLANK_MIN_DISTANCE <= flank_bp <= FLANK_MAX_DISTANCE:
        raise ValueError(f"flank_bp must be in [{FLANK_MIN_DISTANCE}, {FLANK_MAX_DISTANCE}]")

    runs = list(_positive_runs(labels, sequence))
    transitions = _transition_records(labels, sequence)
    boundary_intervals = _boundary_intervals(labels, sequence)
    boundary_positions = {index for left, right in boundary_intervals for index in range(left, right)}
    exclusion_intervals = []
    for edge, _run_index, _outer_left, _outer_right in transitions:
        left = max(0, edge - BOUNDARY_HALF_WIDTH)
        right = min(WINDOW, edge + BOUNDARY_HALF_WIDTH)
        exclusion_intervals.append((left, right))
    exclusion_positions = {index for left, right in exclusion_intervals for index in range(left, right)}
    interior_positions = {
        index
        for start, end in runs
        for index in range(start, end)
        if index not in exclusion_positions
    }

    flank_positions: set[int] = set()
    valid_transition_keys = set()
    for edge, run_index, outer_left, outer_right in transitions:
        candidate_interval = (
            edge - BOUNDARY_CANDIDATE_HALF_WIDTH,
            edge + BOUNDARY_CANDIDATE_HALF_WIDTH,
        )
        if (
            _clean_external_boundary(
                labels, sequence, (edge, run_index, outer_left, outer_right), runs
            )
            and candidate_interval in boundary_intervals
        ):
            valid_transition_keys.add((edge, run_index))
    for edge, run_index, outer_left, outer_right in transitions:
        if (edge, run_index) not in valid_transition_keys:
            continue
        if outer_left < edge:
            lower = max(0, edge - flank_bp)
            index = edge - FLANK_MIN_DISTANCE
            while (
                index >= lower
                and _known(labels, sequence, 0, index)
            ):
                flank_positions.add(index)
                index -= 1
        else:
            upper = min(WINDOW, edge + flank_bp + 1)
            index = edge + FLANK_MIN_DISTANCE
            while (
                index < upper
                and _known(labels, sequence, 0, index)
            ):
                flank_positions.add(index)
                index += 1

    output = dict(record)
    output["candidate_masks"] = {
        "interior": _mask(WINDOW, sorted(interior_positions)),
        "boundary": _mask(WINDOW, sorted(boundary_positions)),
        "flank": _mask(WINDOW, sorted(flank_positions)),
    }
    output["unknown_mask"] = [value < 0 for value in labels]
    output["boundary_intervals"] = [[left, right] for left, right in boundary_intervals]
    output["boundary_exclusion_intervals"] = [[left, right] for left, right in exclusion_intervals]
    return output


def build(args) -> dict[str, object]:
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    records = 0
    totals = {name: 0 for name in ("interior", "boundary", "flank")}
    boundary_count = 0
    exclusion_count = 0
    with _open_text(args.input_jsonl) as source, _open_output(args.output_jsonl) as destination:
        for index, line in enumerate(source):
            if args.max_records is not None and index >= args.max_records:
                break
            if not line.strip():
                continue
            record = build_record(json.loads(line), flank_bp=args.flank_bp)
            for name, values in record["candidate_masks"].items():
                totals[name] += sum(values)
            boundary_count += len(record["boundary_intervals"])
            exclusion_count += len(record["boundary_exclusion_intervals"])
            destination.write(json.dumps(record, separators=(",", ":")) + "\n")
            records += 1

    metadata = {
        "schema": "annotation_conditioned_span_corpus_v1",
        "source_jsonl": str(args.input_jsonl),
        "output_jsonl": str(args.output_jsonl),
        "window": WINDOW,
        "span_length_bp": SPAN_LENGTH,
        "boundary_exclusion_half_width_bp": BOUNDARY_HALF_WIDTH,
        "boundary_exclusion_band_bp": BOUNDARY_HALF_WIDTH,
        "boundary_candidate_half_width_bp": BOUNDARY_CANDIDATE_HALF_WIDTH,
        "boundary_min_each_side_bp": BOUNDARY_MIN_EACH_SIDE,
        "clean_outside_bp": CLEAN_OUTSIDE_BP,
        "flank_bp": args.flank_bp,
        "flank_range_bp": [FLANK_MIN_DISTANCE, args.flank_bp],
        "candidate_strata": ["interior", "boundary", "flank"],
        "annotation_level": "reference_annotation_run",
        "boundary_semantics": "reference_run_boundary",
        "biological_copy_claim": False,
        "claim_scope": "reference annotation run only; not biological full-copy",
        "records": records,
        "boundary_intervals": boundary_count,
        "boundary_exclusion_intervals": exclusion_count,
        "candidate_bp": totals,
    }
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--flank-bp", type=int, default=DEFAULT_FLANK_BP)
    parser.add_argument("--max-records", type=int)
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
