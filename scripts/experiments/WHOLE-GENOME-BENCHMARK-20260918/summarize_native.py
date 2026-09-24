#!/usr/bin/env python3
"""Summarize native GFF/library outputs without dropping Unknown classes."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Dict, Iterable, List, Tuple

from common import fasta_records, file_metadata, write_json


UNKNOWN = {"", "?", "-", "unknown", "unclassified", "na", "none", "."}


def parse_attributes(value: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for field in value.split(";"):
        if "=" in field:
            key, raw = field.split("=", 1)
        elif " " in field:
            key, raw = field.split(None, 1)
        else:
            continue
        result[key.strip().lower()] = raw.strip().strip('"')
    return result


def split_class(raw: str) -> Tuple[str, str]:
    """Return a broad class and family while preserving the raw source string."""
    value = raw.strip()
    if value.lower() in UNKNOWN:
        return "Unknown", "Unknown"
    value = value.replace(" ", "_")
    pieces = [piece for piece in re.split(r"[/|:]", value) if piece]
    broad = pieces[0]
    upper = broad.upper()
    aliases = {"LTR_RETROTRANSPOSON": "LTR", "LINE": "LINE", "SINE": "SINE",
               "DNA": "DNA", "RC": "RC", "RETROPOSON": "Retroposon"}
    broad = aliases.get(upper, broad)
    family = pieces[1] if len(pieces) > 1 else (pieces[0] if broad != "Unknown" else "Unknown")
    return broad, family


def class_from_attributes(attributes: Dict[str, str]) -> Tuple[str, str, str]:
    candidates = []
    for key in ("classification", "class_family", "repeat_class", "class", "family", "repclass", "name", "target"):
        if key in attributes and attributes[key]:
            candidates.append(attributes[key])
    raw = candidates[0] if candidates else "Unknown"
    broad, family = split_class(raw)
    return broad, family, raw


def merge_intervals(intervals: Iterable[Tuple[int, int]]) -> List[Tuple[int, int]]:
    merged: List[List[int]] = []
    for left, right in sorted(intervals):
        if right <= left:
            continue
        if not merged or left > merged[-1][1]:
            merged.append([left, right])
        else:
            merged[-1][1] = max(merged[-1][1], right)
    return [(left, right) for left, right in merged]


def summarize_gff(path: Path) -> Dict[str, object]:
    rows = 0
    unknown_rows = 0
    class_rows: Counter = Counter()
    family_rows: Counter = Counter()
    intervals: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    # Keep the chromosome key below the class key.  Merging intervals from
    # different contigs in one coordinate space undercounts any class whose
    # copies share the same local coordinates on multiple contigs.
    class_intervals: Dict[str, Dict[str, List[Tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError("missing or empty native annotation: %s" % path)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\n").split("\t")
            if len(fields) < 5:
                continue
            try:
                start = int(fields[3]) - 1
                end = int(fields[4])
            except ValueError:
                continue
            if end <= start:
                continue
            attributes = parse_attributes(fields[8] if len(fields) >= 9 else "")
            broad, family, raw_class = class_from_attributes(attributes)
            rows += 1
            unknown_rows += int(broad == "Unknown")
            class_rows[broad] += 1
            family_rows[family] += 1
            intervals[fields[0]].append((start, end))
            class_intervals[broad][fields[0]].append((start, end))
    merged = {chrom: merge_intervals(values) for chrom, values in intervals.items()}
    class_merged = {
        label: {chrom: merge_intervals(values) for chrom, values in by_chrom.items()}
        for label, by_chrom in class_intervals.items()
    }
    return {
        "path": str(path), "metadata": file_metadata(path), "rows": rows,
        "unknown_rows": unknown_rows, "classified_rows": rows - unknown_rows,
        "class_rows": dict(sorted(class_rows.items())), "family_rows": dict(sorted(family_rows.items())),
        "union_bp": sum(right - left for values in merged.values() for left, right in values),
        "class_union_bp": {
            label: sum(right - left for values in class_merged[label].values() for left, right in values)
            for label in sorted(class_merged)
        },
        "contigs": len(merged),
    }


def summarize_repeatmasker_out(path: Path) -> Dict[str, object]:
    """Summarize RepeatMasker output using its native class/family columns.

    RepeatMasker GFF3 records expose the target name as ``Target=Motif:...``;
    that target is not the repeat class.  The tabular ``.out`` format has the
    native repeat name (column 10) and class/family (column 11), so RM2
    summaries must use this file.  Class intervals are indexed by both class
    and contig before merging to avoid cross-contig coordinate collisions.
    """
    rows = 0
    unknown_rows = 0
    class_rows: Counter = Counter()
    family_rows: Counter = Counter()
    class_family_rows: Counter = Counter()
    intervals: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    class_intervals: Dict[str, Dict[str, List[Tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError("missing or empty native RepeatMasker output: %s" % path)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            fields = raw.split()
            # Header/separator lines do not have the 15 columns of a data row.
            if len(fields) < 11:
                continue
            try:
                start = int(fields[5]) - 1
                end = int(fields[6])
            except (ValueError, IndexError):
                continue
            if end <= start:
                continue
            chrom = fields[4]
            repeat_name = fields[9]
            class_family = fields[10]
            broad, _unused_family = split_class(class_family)
            rows += 1
            unknown_rows += int(broad == "Unknown")
            class_rows[broad] += 1
            family_rows[repeat_name] += 1
            class_family_rows[class_family] += 1
            intervals[chrom].append((start, end))
            class_intervals[broad][chrom].append((start, end))
    merged = {chrom: merge_intervals(values) for chrom, values in intervals.items()}
    class_merged = {
        label: {chrom: merge_intervals(values) for chrom, values in by_chrom.items()}
        for label, by_chrom in class_intervals.items()
    }
    return {
        "path": str(path), "metadata": file_metadata(path), "source_format": "RepeatMasker .out",
        "rows": rows, "unknown_rows": unknown_rows, "classified_rows": rows - unknown_rows,
        "class_rows": dict(sorted(class_rows.items())),
        "family_rows": dict(sorted(family_rows.items())),
        "class_family_rows": dict(sorted(class_family_rows.items())),
        "union_bp": sum(right - left for values in merged.values() for left, right in values),
        "class_union_bp": {
            label: sum(right - left for values in class_merged[label].values() for left, right in values)
            for label in sorted(class_merged)
        },
        "contigs": len(merged),
        "field_contract": {
            "contig": 5, "start_1_based": 6, "end_1_based_inclusive": 7,
            "repeat_name": 10, "class_family": 11,
        },
    }


def summarize_library(path: Path) -> Dict[str, object]:
    records = 0
    unknown_records = 0
    classes: Counter = Counter()
    families: Counter = Counter()
    for name, _sequence in fasta_records(path):
        records += 1
        broad, family = split_class(name)
        if broad == "Unknown":
            unknown_records += 1
        classes[broad] += 1
        families[family] += 1
    if records == 0:
        raise ValueError("empty native library: %s" % path)
    return {"path": str(path), "metadata": file_metadata(path), "records": records,
            "unknown_records": unknown_records, "classified_records": records - unknown_records,
            "class_records": dict(sorted(classes.items())), "family_records": dict(sorted(families.items()))}


def summarize(args: argparse.Namespace) -> Dict[str, object]:
    out = args.output_dir.resolve()
    status_path = out / "status.json"
    if not status_path.exists():
        raise FileNotFoundError("native status missing: %s" % status_path)
    status = json.loads(status_path.read_text())
    if status.get("status") != "COMPLETED":
        raise ValueError("native output is not terminal-success: %s" % status.get("status"))
    annotation = out / "annotation.gff3"
    library = out / "library.fasta"
    if args.method == "RM2":
        annotation_summary = summarize_repeatmasker_out(out / "annotation.out")
    else:
        annotation_summary = summarize_gff(annotation)
    summary = {
        "protocol": "WHOLE-GENOME-BENCHMARK-20260918",
        "status": "COMPLETED",
        "species": args.species,
        "method": args.method,
        "annotation": annotation_summary,
        "library": summarize_library(library),
        "unknown_policy": "Missing, empty, '?', '-', unclassified and unknown class fields remain Unknown; no row is filtered",
        "classification_scope": "Native output attributes and native library headers; class counts are descriptive and may overlap in bp",
    }
    write_json(out / "annotation_summary.json", summary)
    print(json.dumps({"status": "COMPLETED", "species": args.species, "method": args.method,
                      "annotation_union_bp": summary["annotation"]["union_bp"],
                      "unknown_rows": summary["annotation"]["unknown_rows"]}, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", required=True, choices=("chicken", "zebrafish"))
    parser.add_argument("--method", required=True, choices=("EDTA", "RM2"))
    parser.add_argument("--output-dir", type=Path, required=True)
    summarize(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
