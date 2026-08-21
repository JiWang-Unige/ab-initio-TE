#!/usr/bin/env python3
"""Convert common TE interval outputs to a canonical zero-based half-open TSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List

FIELDS = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]


def _record(seqid: str, start: int, end: int, name: str, score: str, strand: str,
            source: str, attributes: str) -> Dict[str, object]:
    if start < 0 or end <= start:
        raise ValueError(f"invalid half-open interval: {seqid}:{start}-{end}")
    if strand not in {"+", "-", ".", "?"}:
        raise ValueError(f"invalid strand: {strand}")
    return {"seqid": seqid, "start": start, "end": end, "name": name or ".",
            "score": score or ".", "strand": strand, "source": source or ".",
            "attributes": attributes or "."}


def parse_gff(path: Path) -> Iterable[Dict[str, object]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) != 9:
                raise ValueError(f"GFF row does not have 9 columns: {line[:100]!r}")
            seqid, source, feature, start1, end1, score, strand, phase, attrs = cols
            name = feature
            for item in attrs.split(";"):
                if item.startswith(("Name=", "ID=")):
                    name = item.split("=", 1)[1]
                    break
            yield _record(seqid, int(start1) - 1, int(end1), name, score, strand,
                          source, f"feature={feature};phase={phase};{attrs}")


def parse_bed(path: Path) -> Iterable[Dict[str, object]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 3:
                raise ValueError(f"BED row has fewer than 3 columns: {line[:100]!r}")
            yield _record(cols[0], int(cols[1]), int(cols[2]),
                          cols[3] if len(cols) > 3 else ".",
                          cols[4] if len(cols) > 4 else ".",
                          cols[5] if len(cols) > 5 else ".", "BED", ".")


def parse_repeatmasker_out(path: Path) -> Iterable[Dict[str, object]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            cols = line.split()
            if len(cols) < 11 or not cols[0].isdigit():
                continue
            strand = "-" if cols[8] == "C" else "+"
            yield _record(cols[4], int(cols[5]) - 1, int(cols[6]), cols[9], cols[0],
                          strand, "RepeatMasker", f"class_family={cols[10]}")


def convert(path: Path, output: Path, fmt: str = "auto") -> int:
    if fmt == "auto":
        low = path.name.lower()
        if low.endswith((".gff", ".gff3")):
            fmt = "gff"
        elif low.endswith((".bed", ".bed6")):
            fmt = "bed"
        elif low.endswith(".out"):
            fmt = "repeatmasker_out"
        else:
            raise ValueError(f"cannot infer adapter format for {path}")
    parsers = {"gff": parse_gff, "bed": parse_bed, "repeatmasker_out": parse_repeatmasker_out}
    rows: List[Dict[str, object]] = list(parsers[fmt](path))
    rows.sort(key=lambda row: (str(row["seqid"]), int(row["start"]), int(row["end"]), str(row["name"])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def synthetic_self_test(root: Path) -> Dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    gff = root / "fixture.gff3"
    gff.write_text("##gff-version 3\nchrA\ttest\tLTR\t1\t10\t.\t+\t.\tID=x;Name=elt1\n", encoding="utf-8")
    bed = root / "fixture.bed"
    bed.write_text("chrA\t10\t20\telt2\t0\t-\n", encoding="utf-8")
    gff_out = root / "fixture_gff.canonical.tsv"
    bed_out = root / "fixture_bed.canonical.tsv"
    if convert(gff, gff_out, "gff") != 1 or convert(bed, bed_out, "bed") != 1:
        raise AssertionError("adapter fixture row count mismatch")
    gff_row = list(csv.DictReader(gff_out.open(encoding="utf-8"), delimiter="\t"))[0]
    bed_row = list(csv.DictReader(bed_out.open(encoding="utf-8"), delimiter="\t"))[0]
    assert (gff_row["start"], gff_row["end"]) == ("0", "10")
    assert (bed_row["start"], bed_row["end"]) == ("10", "20")
    return {"pass": True, "coordinate_convention": "zero_based_half_open", "fixtures": 2}
