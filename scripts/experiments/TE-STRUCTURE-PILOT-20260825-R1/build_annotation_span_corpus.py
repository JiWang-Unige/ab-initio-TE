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
MASK_FRACTION_NUMERATOR = 15
MASK_FRACTION_DENOMINATOR = 100
STRATUM_WEIGHTS = {"interior": 0.45, "boundary": 0.30, "flank": 0.25}


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def _open_output(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "wt", encoding="utf-8")
    return path.open("wt", encoding="utf-8")


def _merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def read_annotation_bed(path: Path) -> dict[str, list[tuple[int, int]]]:
    """Read and union zero-based half-open annotation intervals by sequence."""
    intervals: dict[str, list[tuple[int, int]]] = {}
    with _open_text(path) as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) < 3:
                raise ValueError(f"annotation BED row {line_no} has fewer than 3 columns")
            seqid = columns[0]
            try:
                start, end = int(columns[1]), int(columns[2])
            except ValueError as exc:
                raise ValueError(f"annotation BED row {line_no} has non-integer coordinates") from exc
            if not seqid or start < 0 or end <= start:
                raise ValueError(f"annotation BED row {line_no} has invalid interval")
            intervals.setdefault(seqid, []).append((start, end))
    return {seqid: _merge_intervals(rows) for seqid, rows in intervals.items()}


def _annotation_mask(record: dict, annotation_intervals: dict[str, list[tuple[int, int]]]) -> list[bool]:
    sequence = record["sequence"]
    seqid = record.get("chr")
    if not isinstance(seqid, str) or not seqid:
        raise ValueError("annotation-bed conditioning requires record chr")
    try:
        window_start, window_end = int(record["start"]), int(record["end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("annotation-bed conditioning requires integer record start/end") from exc
    if window_start < 0 or window_end - window_start != len(sequence):
        raise ValueError("annotation-bed conditioning requires record coordinates to span its sequence")
    mask = [False] * len(sequence)
    for start, end in annotation_intervals.get(seqid, []):
        if end <= window_start:
            continue
        if start >= window_end:
            break
        left = max(start, window_start) - window_start
        right = min(end, window_end) - window_start
        for index in range(left, right):
            mask[index] = True
    return mask


def apply_annotation_bed(
    record: dict,
    annotation_intervals: dict[str, list[tuple[int, int]]],
) -> dict:
    """Build temporary candidate labels from the high-confidence union.

    Existing class-strict positives outside the sidecar become ignore (-100),
    so low-confidence TE cannot become a clean flank.  Existing -100 values
    remain -100; sidecar-covered known bases become positive candidates.  The
    caller uses these labels only to construct candidate masks; the original
    labels remain the output labels so the callable MLM denominator is frozen.
    """
    labels = record["labels"]
    high_confidence = _annotation_mask(record, annotation_intervals)
    conditioned = [
        -100 if label < 0 else 1 if high_confidence[index] else -100 if label == 1 else 0
        for index, label in enumerate(labels)
    ]
    output = dict(record)
    output["labels"] = conditioned
    return output


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


def _runs(mask: list[bool]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(mask + [False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            runs.append((start, index))
            start = None
    return runs


def _packable_span_counts(candidate_masks: dict[str, list[bool]]) -> dict[str, int]:
    """Return the maximum number of fixed-length spans in each disjoint stratum."""
    return {
        name: sum((end - start) // SPAN_LENGTH for start, end in _runs(candidate_masks[name]))
        for name in STRATUM_WEIGHTS
    }


def _callable_bp(record: dict) -> int:
    return sum(
        label >= 0 and base.upper() != "N"
        for label, base in zip(record["labels"], record["sequence"])
    )


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


def build_record(
    record: dict,
    *,
    flank_bp: int = DEFAULT_FLANK_BP,
    annotation_intervals: dict[str, list[tuple[int, int]]] | None = None,
) -> dict:
    original_record = record
    if annotation_intervals is not None:
        record = apply_annotation_bed(record, annotation_intervals)
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

    flank_positions.difference_update(boundary_positions)

    candidate_masks = {
        "interior": _mask(WINDOW, sorted(interior_positions)),
        "boundary": _mask(WINDOW, sorted(boundary_positions)),
        "flank": _mask(WINDOW, sorted(flank_positions)),
    }
    if annotation_intervals is not None:
        original_callable = [
            label >= 0 and base.upper() != "N"
            for label, base in zip(original_record["labels"], sequence)
        ]
        candidate_masks = {
            name: [candidate and callable_base for candidate, callable_base in zip(mask, original_callable)]
            for name, mask in candidate_masks.items()
        }
    output = dict(record)
    output["candidate_masks"] = candidate_masks
    output["unknown_mask"] = [value < 0 for value in labels]
    if annotation_intervals is not None:
        output["labels"] = list(original_record["labels"])
        output["unknown_mask"] = [value < 0 for value in original_record["labels"]]
    output["boundary_intervals"] = [[left, right] for left, right in boundary_intervals]
    output["boundary_exclusion_intervals"] = [[left, right] for left, right in exclusion_intervals]
    return output


def build(args) -> dict[str, object]:
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    retain_limit = getattr(args, "retain_packable_windows", None)
    annotation_bed = getattr(args, "annotation_bed", None)
    annotation_intervals = read_annotation_bed(annotation_bed) if annotation_bed is not None else None
    annotation_union_intervals = (
        sum(len(intervals) for intervals in annotation_intervals.values())
        if annotation_intervals is not None
        else 0
    )
    annotation_high_confidence_bp = 0
    annotation_demoted_positive_bp = 0
    annotation_preserved_unknown_bp = 0
    if retain_limit is not None and retain_limit < 0:
        raise ValueError("retain_packable_windows must be non-negative")
    records = 0
    scanned_records = 0
    filtered_records = 0
    packable_span_totals = {name: 0 for name in STRATUM_WEIGHTS}
    totals = {name: 0 for name in ("interior", "boundary", "flank")}
    boundary_count = 0
    exclusion_count = 0
    with _open_text(args.input_jsonl) as source, _open_output(args.output_jsonl) as destination:
        for index, line in enumerate(source):
            if args.max_records is not None and index >= args.max_records:
                break
            if retain_limit is not None and records >= retain_limit:
                break
            if not line.strip():
                continue
            scanned_records += 1
            input_record = json.loads(line)
            if annotation_intervals is not None:
                original_labels = input_record["labels"]
                high_confidence = _annotation_mask(input_record, annotation_intervals)
                record = build_record(
                    input_record,
                    flank_bp=args.flank_bp,
                    annotation_intervals=annotation_intervals,
                )
                annotation_high_confidence_bp += sum(
                    old >= 0 and selected
                    for old, selected in zip(original_labels, high_confidence)
                )
                annotation_demoted_positive_bp += sum(
                    old == 1 and not selected
                    for old, selected in zip(original_labels, high_confidence)
                )
                annotation_preserved_unknown_bp += sum(
                    old < 0 for old in original_labels
                )
            else:
                record = build_record(input_record, flank_bp=args.flank_bp)
            if retain_limit is not None:
                callable_bp = _callable_bp(record)
                target_bp = round(
                    callable_bp * MASK_FRACTION_NUMERATOR / MASK_FRACTION_DENOMINATOR
                )
                required_spans = target_bp // SPAN_LENGTH
                if target_bp > 0 and required_spans == 0:
                    required_spans = 1
                packable_by_stratum = _packable_span_counts(record["candidate_masks"])
                if (
                    sum(packable_by_stratum.values()) < required_spans
                    or packable_by_stratum["boundary"] < 1
                ):
                    filtered_records += 1
                    continue
                for name in STRATUM_WEIGHTS:
                    packable_span_totals[name] += packable_by_stratum[name]
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
        "scanned_records": scanned_records,
        "retained_records": records,
        "filtered_records": filtered_records,
        "retention_limit": retain_limit,
        "retained_packable_span_totals": packable_span_totals,
        "filter_rule": (
            "retain only windows where the disjoint candidate masks can satisfy the total "
            "floor(round(0.15 * callable_bp) / 32) span budget and provide at least one "
            "clean boundary span"
            if retain_limit is not None
            else "none; emit every input record"
        ),
        "boundary_intervals": boundary_count,
        "boundary_exclusion_intervals": exclusion_count,
        "candidate_bp": totals,
        "annotation_bed": str(annotation_bed) if annotation_bed is not None else None,
        "annotation_union_intervals": annotation_union_intervals,
        "annotation_conditioning": (
            "high_confidence_repeatmasker_union_over_original_reference_runs"
            if annotation_intervals is not None
            else "none"
        ),
        "annotation_conditioning_semantics": (
            "sidecar-covered known bases condition candidate masks; original labels and "
            "unknown_mask remain unchanged; original positives outside the sidecar are "
            "excluded from candidates; existing -100 is preserved; sidecar intervals are "
            "unioned before boundary derivation; callable denominator remains the original "
            "known-base count; not biological full-copy truth"
            if annotation_intervals is not None
            else "original labels and sequence are unchanged"
        ),
        "annotation_high_confidence_positive_bp": annotation_high_confidence_bp,
        "annotation_demoted_positive_bp": annotation_demoted_positive_bp,
        "annotation_preserved_unknown_bp": annotation_preserved_unknown_bp,
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
    parser.add_argument("--retain-packable-windows", type=int)
    parser.add_argument("--annotation-bed", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
