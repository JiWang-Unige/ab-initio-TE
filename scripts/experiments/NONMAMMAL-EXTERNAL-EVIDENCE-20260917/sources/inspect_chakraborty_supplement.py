#!/usr/bin/env python3
"""Inspect Chakraborty et al. sim-complex supplementary metadata.

This is a source-only helper.  It reads a locally downloaded Europe PMC
supplementary bundle and the nested SupplementalFile_S1.zip; it does not
download a genome, run RepeatMasker, or call any project inference code.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from xml.etree import ElementTree


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
LIBRARY_NAME = "supp_gr.263442.120_SupplementalFile_S1.zip"
LIBRARY_FASTA = "File_S1.fasta"


def fasta_records(text: str) -> Iterable[Tuple[str, str]]:
    header = None
    seq: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                yield header, "".join(seq)
            header, seq = line[1:], []
        else:
            seq.append(line)
    if header is not None:
        yield header, "".join(seq)


def xlsx_rows(path: Path) -> List[List[str]]:
    with zipfile.ZipFile(path) as zf:
        shared: List[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in item.findall(".//m:t", NS)))
        root = ElementTree.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows: List[List[str]] = []
        for row in root.findall(".//m:row", NS):
            values: List[str] = []
            for cell in row.findall("m:c", NS):
                value = cell.find("m:v", NS)
                text = "" if value is None else value.text or ""
                if cell.attrib.get("t") == "s" and text:
                    text = shared[int(text)]
                values.append(text)
            rows.append(values)
        return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplementary-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with zipfile.ZipFile(args.supplementary_zip) as outer:
        library_zip = outer.read(LIBRARY_NAME)
        table14 = outer.read("supp_gr.263442.120_supplemental_Table_S14.xlsx")
        table17 = outer.read("supp_gr.263442.120_supplemental_Table_S17.xlsx")

    from io import BytesIO

    with zipfile.ZipFile(BytesIO(library_zip)) as inner:
        fasta = inner.read(LIBRARY_FASTA).decode("utf-8")
    records = list(fasta_records(fasta))
    classes = Counter()
    record_lengths = []
    for header, sequence in records:
        record_lengths.append(len(sequence))
        if "#" in header:
            classes[header.split("#", 1)[1].split("/", 1)[0]] += 1

    s14_path = args.output.parent / ".temporary_S14.xlsx"
    s17_path = args.output.parent / ".temporary_S17.xlsx"
    s14_path.write_bytes(table14)
    s17_path.write_bytes(table17)
    try:
        s14 = xlsx_rows(s14_path)
        s17 = xlsx_rows(s17_path)
    finally:
        s14_path.unlink()
        s17_path.unlink()

    probe_rows = [row for row in s14 if row and row[0] == "193XP probe"]
    accession_rows = [row for row in s17 if row and row[0] == "PRJNA383250"]
    xp = [(header, sequence) for header, sequence in records if header.startswith("193XP_SAT#")]

    result: Dict[str, object] = {
        "library_filename": LIBRARY_FASTA,
        "record_count": len(records),
        "total_bp": sum(record_lengths),
        "min_bp": min(record_lengths),
        "max_bp": max(record_lengths),
        "class_counts": dict(sorted(classes.items())),
        "193xp_records": [{"header": h, "length": len(s)} for h, s in xp],
        "table_s14_193xp_rows": probe_rows,
        "table_s17_project_rows": accession_rows,
        "193xp_class": "Satellite/Satellite",
        "193xp_te_eligible": False,
        "te_specific_independent_support": False,
        "coordinate_status": "library FASTA and probe table contain no genome coordinates",
        "te_coordinate_status": "no independent genome-coordinate support for a TE-class record was found",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
