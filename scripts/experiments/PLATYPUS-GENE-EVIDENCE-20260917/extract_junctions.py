#!/usr/bin/env python3
"""Extract uniquely mapped splice junction evidence from a SAM stream.

HISAT2 does not create STAR's ``SJ.out.tab``.  This parser consumes SAM records
from ``samtools view`` and emits a six-column custom summary consumed by
``summarize_evidence.py``.  Only primary alignments carrying ``NH:i:1`` are
counted; secondary/supplementary/unmapped records are ignored.  Adjacent mate
records are combined by exact QNAME (with only trailing ``/1`` or ``/2``
removed), so counts are template-level rather than alignment-record-level.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict


CIGAR = re.compile(r"(\d+)([MIDNSHP=X])")
MATE_SUFFIX = re.compile(r"(?:/1|/2)$")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sam", default="-", help="SAM input, or - for stdin")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-overhang", type=int, default=8)
    return ap.parse_args()


def nh_value(fields: list[str]) -> int | None:
    for field in fields[11:]:
        if field.startswith("NH:i:"):
            try:
                return int(field[5:])
            except ValueError:
                return None
    return None


def junctions_from_cigar(pos: int, cigar: str):
    ops = [(int(n), op) for n, op in CIGAR.findall(cigar)]
    if not ops or "N" not in cigar:
        return
    ref_pos = pos
    for i, (length, op) in enumerate(ops):
        if op == "N":
            left = ops[i - 1][0] if i > 0 and ops[i - 1][1] in "M=X" else 0
            right = ops[i + 1][0] if i + 1 < len(ops) and ops[i + 1][1] in "M=X" else 0
            yield ref_pos, ref_pos + length - 1, min(left, right)
            ref_pos += length
        elif op in "MDN=X":
            ref_pos += length


def template_name(qname: str) -> str:
    """Normalize common paired-read suffixes before template de-duplication."""

    return MATE_SUFFIX.sub("", qname)


def main() -> None:
    args = parse_args()
    handle = sys.stdin if args.sam == "-" else open(args.sam, encoding="utf-8")
    # Per junction: all NH=1 templates, strict-overhang NH=1 templates, and
    # maximum observed overhang.  Keeping both counts prevents a mixture of
    # short-anchor and long-anchor templates from passing the strict threshold.
    counts: dict[tuple[str, int, int], list[int]] = defaultdict(lambda: [0, 0, 0])
    eligible_records = 0
    eligible_templates = 0
    junction_records = 0
    current_template: str | None = None
    current_junctions: dict[tuple[str, int, int], int] = {}

    def flush_template() -> None:
        nonlocal junction_records, eligible_templates, current_template, current_junctions
        if current_template is None:
            return
        eligible_templates += 1
        for key, overhang in current_junctions.items():
            counts[key][0] += 1
            if overhang >= args.min_overhang:
                counts[key][1] += 1
            counts[key][2] = max(counts[key][2], overhang)
            junction_records += 1
        current_template = None
        current_junctions = {}

    try:
        for line in handle:
            if not line.strip() or line.startswith("@"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 11:
                continue
            flag = int(fields[1])
            if flag & (4 | 256 | 2048):
                continue
            if nh_value(fields) != 1:
                continue
            qname = template_name(fields[0])
            # HISAT2 emits mates adjacent in the SAM stream.  Flush only at a
            # template boundary so the same junction traversed by both mates
            # contributes once per NH=1 template, not twice per alignment.
            if current_template is not None and qname != current_template:
                flush_template()
            if current_template is None:
                current_template = qname
            eligible_records += 1
            for start, end, overhang in junctions_from_cigar(int(fields[3]), fields[5]) or ():
                key = (fields[2], start, end)
                current_junctions[key] = max(current_junctions.get(key, 0), overhang)
        flush_template()
    finally:
        if handle is not sys.stdin:
            handle.close()

    with open(args.out, "w", encoding="utf-8") as out:
        for (seqname, start, end), (all_templates, strict_templates, overhang) in sorted(counts.items()):
            # This is a deliberately custom six-column format, not STAR's
            # SJ.out.tab: contig, intron start/end, all NH=1 templates,
            # strict-overhang NH=1 templates, and max observed overhang.
            out.write(
                f"{seqname}\t{start}\t{end}\t{all_templates}\t{strict_templates}\t{overhang}\n"
            )
    print(json.dumps(
        {
            "primary_nh1_alignment_records": eligible_records,
            "primary_nh1_templates": eligible_templates,
            "junction_template_records": junction_records,
            "distinct_junctions": len(counts),
            "template_deduplication": "adjacent SAM records; only trailing /1,/2 suffixes normalized",
        }, indent=2
    ))


if __name__ == "__main__":
    main()
