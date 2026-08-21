#!/usr/bin/env python3
"""Audit RepeatMasker chunk and species-level outputs against a manifest."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)


REQUIRED_SUFFIXES = {
    "out": [".fa.out.gz", ".fa.out"],
    "gff": [".fa.out.gff.gz", ".fa.out.gff"],
    "tbl": [".fa.tbl.gz", ".fa.tbl"],
    "masked": [".fa.masked.gz", ".fa.masked"],
}


def first_existing(chunk_dir: Path, suffixes: list[str]) -> Path | None:
    for suffix in suffixes:
        matches = sorted(chunk_dir.glob(f"*{suffix}"))
        if matches:
            return matches[0]
    return None


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-manifest", required=True)
    parser.add_argument("--species-manifest")
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--details-out", required=True)
    args = parser.parse_args()

    chunks: list[dict[str, str]]
    with Path(args.chunk_manifest).open(newline="") as handle:
        chunks = list(csv.DictReader(handle, delimiter="\t"))

    species_rows: dict[str, dict[str, str]] = {}
    if args.species_manifest:
        with Path(args.species_manifest).open(newline="") as handle:
            species_rows = {row["species_code"]: row for row in csv.DictReader(handle, delimiter="\t")}

    details: list[dict[str, object]] = []
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for chunk in chunks:
        chunk_dir = Path(chunk["output_dir"])
        found = {name: first_existing(chunk_dir, suffixes) for name, suffixes in REQUIRED_SUFFIXES.items()}
        missing = [name for name, path in found.items() if path is None]
        row = {
            "species_code": chunk["species_code"],
            "chunk_index": chunk["chunk_index"],
            "chunk_id": chunk["chunk_id"],
            "records": chunk.get("records", ""),
            "chunk_bases": chunk.get("chunk_bases", ""),
            "complete_marker": int((chunk_dir / "COMPLETE").exists()),
            "out_present": int(found["out"] is not None),
            "gff_present": int(found["gff"] is not None),
            "tbl_present": int(found["tbl"] is not None),
            "masked_present": int(found["masked"] is not None),
            "final_outputs_complete": int(not missing),
            "missing_final_outputs": ",".join(missing),
            "output_dir": str(chunk_dir),
        }
        details.append(row)
        grouped[chunk["species_code"]].append(row)

    summary: list[dict[str, object]] = []
    for species, rows in sorted(grouped.items()):
        manifest_row = species_rows.get(species, {})
        species_out = Path(manifest_row.get("species_output_dir", rows[0]["output_dir"]).rsplit("/chunks/", 1)[0])
        expected = len(rows)
        final_ok = sum(int(row["final_outputs_complete"]) for row in rows)
        complete_markers = sum(int(row["complete_marker"]) for row in rows)
        missing_ids = [
            str(row["chunk_id"])
            for row in rows
            if not int(row["final_outputs_complete"])
        ]
        merged_out = species_out / f"{species}.repeatmasker.out.gz"
        merged_gff = species_out / f"{species}.repeatmasker.out.gff.gz"
        merged_tbl = species_out / f"{species}.repeatmasker.tbl.gz"
        merged_masked = species_out / f"{species}.repeatmasker.masked.fa.gz"
        chunks_ok = final_ok == expected
        merged_ok = all(path.exists() and path.stat().st_size > 0 for path in [merged_out, merged_gff, merged_tbl, merged_masked])
        if not chunks_ok:
            status = "MISSING_CHUNK_FINAL_OUTPUTS"
        elif not merged_ok:
            status = "CHUNKS_OK_NOT_MERGED"
        else:
            status = "OK"
        summary.append({
            "species_code": species,
            "expected_chunks": expected,
            "complete_markers": complete_markers,
            "final_complete_chunks": final_ok,
            "missing_final_chunks": expected - final_ok,
            "missing_chunk_ids": ",".join(missing_ids[:50]),
            "species_complete_marker": int((species_out / "COMPLETE").exists()),
            "merged_out_present": int(merged_out.exists() and merged_out.stat().st_size > 0),
            "merged_gff_present": int(merged_gff.exists() and merged_gff.stat().st_size > 0),
            "merged_tbl_present": int(merged_tbl.exists() and merged_tbl.stat().st_size > 0),
            "merged_masked_present": int(merged_masked.exists() and merged_masked.stat().st_size > 0),
            "status": status,
            "species_output_dir": str(species_out),
        })

    write_tsv(Path(args.details_out), details, [
        "species_code", "chunk_index", "chunk_id", "records", "chunk_bases", "complete_marker",
        "out_present", "gff_present", "tbl_present", "masked_present", "final_outputs_complete",
        "missing_final_outputs", "output_dir",
    ])
    write_tsv(Path(args.summary_out), summary, [
        "species_code", "expected_chunks", "complete_markers", "final_complete_chunks",
        "missing_final_chunks", "missing_chunk_ids", "species_complete_marker",
        "merged_out_present", "merged_gff_present", "merged_tbl_present", "merged_masked_present",
        "status", "species_output_dir",
    ])


if __name__ == "__main__":
    main()
