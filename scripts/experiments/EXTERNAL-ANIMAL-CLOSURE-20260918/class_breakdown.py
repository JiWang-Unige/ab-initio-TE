#!/usr/bin/env python3
"""Break down completed fixed-D calls by strict source broad class.

This is a post-hoc diagnostic over existing ``material_runs.bed`` files.  It
does not change the model threshold or re-calibrate.  Each broad class is
unioned independently from the original RepeatMasker ``.class`` field, so
overlap between classes is retained and reported rather than silently added
to the strict-known union.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


KNOWN = ("DNA", "LINE", "SINE", "LTR", "RC", "Retroposon")
KNOWN_SET = set(KNOWN)
UNCERTAIN = {"Unknown", "ARTEFACT"}


def open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open()


def fasta(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    name, parts = None, []
    with opener(path, "rt") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(parts).upper()
                name, parts = line[1:].split()[0], []
            else:
                if name is None:
                    raise ValueError("sequence before FASTA header")
                parts.append(line)
    if name is not None:
        yield name, "".join(parts).upper()


def bed(path: Path):
    with open_text(path) as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            fields = line.split()
            if len(fields) < 3:
                raise ValueError(f"invalid BED row {path}:{number}")
            left, right = int(fields[1]), int(fields[2])
            if left < 0 or right <= left:
                raise ValueError(f"invalid BED coordinates {path}:{number}")
            yield fields[0], left, right


def source_intervals(path: Path, regions):
    """Return raw intervals grouped by panel and broad source class.

    ``fields[10]`` is the original RepeatMasker ``.class`` value (for
    example ``LINE/CR1``).  We use only its broad prefix for the requested
    six-class table, while retaining the exact values as provenance.
    """
    by_panel = defaultdict(lambda: defaultdict(list))
    uncertain_by_panel = defaultdict(list)
    exact_class_by_panel = defaultdict(lambda: defaultdict(set))
    source_class_rows = defaultdict(int)
    rows_seen = 0
    for number, line in enumerate(open_text(path), 1):
        fields = line.split()
        if len(fields) < 11 or not fields[0].isdigit():
            continue
        rows_seen += 1
        seqid = fields[4]
        broad = fields[10].split("/", 1)[0]
        source_class_rows[broad] += 1
        if seqid not in regions:
            continue
        row = regions[seqid]
        start, end = int(fields[5]) - 1, int(fields[6])
        left, right = max(start, row["start"]), min(end, row["end"])
        if right <= left:
            continue
        interval = (left - row["start"], right - row["start"], fields[10])
        panel_id = row["panel_id"]
        if broad in KNOWN_SET:
            by_panel[panel_id][broad].append(interval)
            exact_class_by_panel[panel_id][broad].add(fields[10])
        elif broad in UNCERTAIN or "?" in broad:
            uncertain_by_panel[panel_id].append(interval)
    return by_panel, uncertain_by_panel, exact_class_by_panel, {
        "rows_seen": rows_seen,
        "broad_class_rows": dict(source_class_rows),
    }


def merge_mask(width, intervals):
    mask = np.zeros(width, dtype=bool)
    for left, right, _ in intervals:
        if not (0 <= left < right <= width):
            raise ValueError(f"panel interval out of bounds: {left}-{right}/{width}")
        mask[left:right] = True
    return mask


def class_metrics(mask, callable_mask, predicted, uncertain_mask, intervals, exact_classes):
    class_callable = mask & callable_mask
    reference_bp = int(class_callable.sum())
    recovered_bp = int((class_callable & predicted).sum())
    return {
        "original_class_values": sorted(exact_classes),
        "source_rows": len(intervals),
        "interval_union_bp": int(mask.sum()),
        "reference_bp_callable": reference_bp,
        "recovered_bp": recovered_bp,
        "missed_bp": int((class_callable & ~predicted).sum()),
        "recall": recovered_bp / reference_bp if reference_bp else None,
        "non_callable_bp_excluded": int((mask & ~callable_mask).sum()),
        "uncertain_overlap_bp": int((mask & uncertain_mask).sum()),
    }


def run(args):
    panel = json.loads((args.panel / "panel.json").read_text())
    regions = {row["source_seqid"]: row for row in panel["regions"]}
    panel_sequences = dict(fasta(args.panel / "panel.fa"))
    expected_ids = {row["panel_id"] for row in panel["regions"]}
    if set(panel_sequences) != expected_ids:
        raise ValueError("panel FASTA IDs differ from panel manifest")
    inference = json.loads((args.inference / "summary.json").read_text())
    if inference.get("status") != "COMPLETED" or inference.get("total_bp") != panel["total_bp"]:
        raise ValueError("inference is incomplete or has a different denominator")

    by_panel, uncertain_by_panel, exact_by_panel, source_info = source_intervals(
        Path(args.reference), regions
    )
    predictions = defaultdict(list)
    for seqid, left, right in bed(args.inference / "material_runs.bed"):
        predictions[seqid].append((left, right))

    all_callable, all_predicted = [], []
    all_class_masks = {broad: [] for broad in KNOWN}
    all_uncertain = []
    per_region = []
    for row in panel["regions"]:
        panel_id = row["panel_id"]
        sequence = panel_sequences[panel_id]
        if len(sequence) != panel["selection"]["length_bp"]:
            raise ValueError(f"unexpected sequence length for {panel_id}")
        symbols = np.frombuffer(sequence.encode("ascii"), dtype="S1")
        callable_mask = np.isin(symbols, [b"A", b"C", b"G", b"T"])
        uncertain_mask = merge_mask(
            len(sequence), uncertain_by_panel.get(panel_id, [])
        )
        predicted = np.zeros(len(sequence), dtype=bool)
        for left, right in predictions.get(panel_id, []):
            if not (0 <= left < right <= len(sequence)):
                raise ValueError(f"prediction outside fixed panel: {panel_id}:{left}-{right}")
            predicted[left:right] = True

        class_rows = {}
        for broad in KNOWN:
            intervals = by_panel.get(panel_id, {}).get(broad, [])
            mask = merge_mask(len(sequence), intervals)
            class_rows[broad] = class_metrics(
                mask,
                callable_mask,
                predicted,
                uncertain_mask,
                intervals,
                exact_by_panel.get(panel_id, {}).get(broad, set()),
            )
            all_class_masks[broad].append(mask)
        known_union = np.logical_or.reduce(
            [all_class_masks[broad][-1] for broad in KNOWN]
        )
        per_region.append(
            {
                "panel_id": panel_id,
                "source_seqid": row["source_seqid"],
                "callable_bp": int(callable_mask.sum()),
                "n_or_noncallable_bp": int((~callable_mask).sum()),
                "uncertain_bp": int(uncertain_mask.sum()),
                "strict_known_union_bp": int(known_union.sum()),
                "class_union_sum_bp": sum(v["interval_union_bp"] for v in class_rows.values()),
                "classes_overlap_excess_bp": int(
                    sum(v["interval_union_bp"] for v in class_rows.values())
                    - known_union.sum()
                ),
                "classes": class_rows,
            }
        )
        all_callable.append(callable_mask)
        all_predicted.append(predicted)
        all_uncertain.append(uncertain_mask)

    callable_mask = np.concatenate(all_callable)
    predicted = np.concatenate(all_predicted)
    uncertain_mask = np.concatenate(all_uncertain)
    class_results = {}
    all_masks = []
    for broad in KNOWN:
        mask = np.concatenate(all_class_masks[broad])
        class_results[broad] = class_metrics(
            mask,
            callable_mask,
            predicted,
            uncertain_mask,
            [],
            sorted({v for row in per_region for v in row["classes"][broad]["original_class_values"]}),
        )
        class_results[broad]["source_rows"] = sum(
            row["classes"][broad]["source_rows"] for row in per_region
        )
        all_masks.append(mask)
    strict_known_union = np.logical_or.reduce(all_masks)
    class_union_sum_bp = sum(v["interval_union_bp"] for v in class_results.values())
    result = {
        "status": "COMPLETED_CLASS_BREAKDOWN_EXISTING_PREDICTIONS",
        "species": panel["species"],
        "assembly": panel["source"]["assembly"],
        "panel_total_bp": panel["total_bp"],
        "callable_bp": int(callable_mask.sum()),
        "n_or_noncallable_bp_excluded": int((~callable_mask).sum()),
        "uncertain_bp": int(uncertain_mask.sum()),
        "strict_known_union_bp": int(strict_known_union.sum()),
        "class_union_sum_bp": class_union_sum_bp,
        "classes_overlap_excess_bp": class_union_sum_bp - int(strict_known_union.sum()),
        "class_union_note": "Each broad class is independently unioned from the original .class field. Class rows can overlap across classes; class bp must not be summed as a strict-known total.",
        "classes": class_results,
        "per_region": per_region,
        "inference": str(args.inference),
        "reference": str(args.reference),
        "source_info": source_info,
        "threshold_policy": "Existing material_runs.bed is scored unchanged; no threshold change or recalibration was performed.",
        "claim_boundary": "Class-specific recovery is against the documented same-assembly strict-known source layer on the fixed 104.86-Mb panel; it is not biological truth or completeness.",
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--inference", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
