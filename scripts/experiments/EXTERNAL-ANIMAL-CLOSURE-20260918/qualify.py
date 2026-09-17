#!/usr/bin/env python3
"""Qualify fixed, label-rich external animal panels before model inference."""
from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


KNOWN = {"DNA", "LINE", "SINE", "LTR", "RC", "Retroposon"}


def open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open()


def read_sizes(path: Path) -> Dict[str, int]:
    result = {}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 2 or not fields[1].isdigit():
            raise ValueError(f"invalid chrom.sizes row {path}:{number}")
        if fields[0] in result:
            raise ValueError(f"duplicate source contig {fields[0]}")
        result[fields[0]] = int(fields[1])
    if not result:
        raise ValueError(f"empty sizes file: {path}")
    return result


def select_regions(sizes: Dict[str, int], width: int, count: int):
    eligible = [(name, length) for name, length in sizes.items() if length >= width]
    selected = sorted(eligible, key=lambda item: (-item[1], item[0]))[:count]
    if len(selected) != count:
        raise ValueError(f"only {len(selected)} source contigs meet the {width}-bp minimum")
    return [
        {"panel_id": f"core{index:02d}", "source_seqid": name,
         "assembly_length_bp": length, "start": (length - width) // 2,
         "end": (length - width) // 2 + width}
        for index, (name, length) in enumerate(selected)
    ]


def merge_length(intervals: Iterable[Tuple[int, int]]) -> int:
    ordered = sorted((int(left), int(right)) for left, right in intervals if right > left)
    total = 0
    current = None
    for left, right in ordered:
        if current is None:
            current = [left, right]
        elif left <= current[1]:
            current[1] = max(current[1], right)
        else:
            total += current[1] - current[0]
            current = [left, right]
    if current is not None:
        total += current[1] - current[0]
    return total


def parse_repeat(path: Path, regions):
    selected = {row["source_seqid"]: row for row in regions}
    by_region = defaultdict(list)
    by_class = Counter()
    all_rows = 0
    known_rows = 0
    unknown_rows = 0
    full_known_intervals = []
    with open_text(path) as handle:
        for number, line in enumerate(handle, 1):
            fields = line.split()
            if len(fields) < 11 or not fields[0].isdigit():
                continue
            all_rows += 1
            seqid = fields[4]
            try:
                start = int(fields[5]) - 1
                end = int(fields[6])
            except ValueError as exc:
                raise ValueError(f"invalid RepeatMasker coordinate {path}:{number}") from exc
            if end <= start:
                continue
            class_family = fields[10]
            # Keep RepeatMasker uncertainty markers out of the strict positive
            # layer; `DNA?` and `LTR?` are source uncertainty, not known TE.
            broad = class_family.split("/", 1)[0]
            by_class[class_family] += 1
            if broad in KNOWN:
                known_rows += 1
                full_known_intervals.append((seqid, start, end))
            if broad == "Unknown" or "?" in class_family:
                unknown_rows += 1
            if seqid not in selected:
                continue
            row = selected[seqid]
            left, right = max(start, row["start"]), min(end, row["end"])
            if right > left and broad in KNOWN:
                by_region[row["panel_id"]].append((left - row["start"], right - row["start"]))
    source_lengths = {name: length for name, length in ((x[0], x[1]) for x in full_known_intervals)}
    del source_lengths
    return {
        "rows_seen": all_rows,
        "known_te_rows": known_rows,
        "unknown_or_uncertain_rows": unknown_rows,
        "class_counts": dict(by_class),
        "known_te_full_assembly_bp_estimate": None,
        "known_te_panel_bp_by_region": {key: merge_length(value) for key, value in by_region.items()},
        "known_te_intervals_by_region": {key: len(value) for key, value in by_region.items()},
    }


def qualify(args):
    config = json.loads(args.config.read_text())
    spec = config["species"][args.species]
    panel_cfg = config["selection"]
    sizes = read_sizes(Path(spec["sizes"]))
    regions = select_regions(sizes, int(panel_cfg["length_bp"]), int(panel_cfg["contigs"]))
    source = parse_repeat(Path(spec["historical_rm_out"]), regions)
    # A second pass over the parsed class counts is unnecessary for full source
    # bp only if we retain per-contig intervals.  The gate uses the documented
    # preliminary total and the selected panel union; full bp is checked below
    # directly from a compact interval union map.
    full_by_seq = defaultdict(list)
    with open_text(Path(spec["historical_rm_out"])) as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < 11 or not fields[0].isdigit():
                continue
            broad = fields[10].split("/", 1)[0]
            if broad not in KNOWN:
                continue
            start, end = int(fields[5]) - 1, int(fields[6])
            if end > start:
                full_by_seq[fields[4]].append((start, end))
    full_known_bp = sum(merge_length(value) for value in full_by_seq.values())
    panel_known_bp = sum(source["known_te_panel_bp_by_region"].values())
    panel_bp = int(panel_cfg["contigs"]) * int(panel_cfg["length_bp"])
    rows_with_both = sum(
        0 < source["known_te_panel_bp_by_region"].get(row["panel_id"], 0) < int(panel_cfg["length_bp"])
        for row in regions
    )
    broad_count = sum(
        count > 0 for broad, count in Counter(
            key.split("/", 1)[0] for key in source["class_counts"]
        ).items() if broad in KNOWN
    )
    gate = config["quality_gate"]
    reasons = []
    if full_known_bp < int(gate["minimum_full_assembly_known_te_bp"]):
        reasons.append("full_assembly_known_te_bp_below_minimum")
    if panel_known_bp < int(gate["minimum_selected_panel_known_te_bp"]):
        reasons.append("selected_panel_known_te_bp_below_minimum")
    fraction = panel_known_bp / panel_bp
    if fraction < float(gate["minimum_selected_panel_positive_fraction"]):
        reasons.append("selected_panel_positive_fraction_below_minimum")
    if fraction > float(gate["maximum_selected_panel_positive_fraction"]):
        reasons.append("selected_panel_positive_fraction_above_maximum")
    if rows_with_both < int(gate["minimum_selected_regions_with_positive_and_background"]):
        reasons.append("too_few_mixed_positive_background_regions")
    if broad_count < int(gate["minimum_broad_class_count"]):
        reasons.append("too_few_broad_te_classes")
    result = {
        "status": "QUALIFIED" if not reasons else "REJECTED_BEFORE_INFERENCE",
        "species": args.species,
        "scientific_name": spec["scientific_name"],
        "assembly": spec["assembly"],
        "source": spec,
        "selection": {"config": panel_cfg, "regions": regions, "labels_used_in_selection": False,
                       "scores_used_in_selection": False},
        "source_summary": source,
        "quality_metrics": {
            "full_assembly_known_te_bp_union": full_known_bp,
            "selected_panel_known_te_bp_union": panel_known_bp,
            "selected_panel_bp": panel_bp,
            "selected_panel_positive_fraction": fraction,
            "mixed_positive_background_regions": rows_with_both,
            "broad_class_count": broad_count,
        },
        "gate": {"thresholds": gate, "failed_reasons": reasons},
        "claim_boundary": "Source coverage qualification of a same-assembly RepeatMasker layer; not independent biological truth and not a model score.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--species", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
