#!/usr/bin/env python3
"""Compare finalized de novo TE annotations against UCSC strict-TE BEDs."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import json
from pathlib import Path
from typing import Iterable


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def merge_intervals(intervals: Iterable[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    merged: list[tuple[str, int, int]] = []
    for chrom, start, end in sorted(intervals):
        if end <= start:
            continue
        if not merged or merged[-1][0] != chrom or start > merged[-1][2]:
            merged.append((chrom, start, end))
        elif end > merged[-1][2]:
            merged[-1] = (merged[-1][0], merged[-1][1], end)
    return merged


def interval_bp(intervals: Iterable[tuple[str, int, int]]) -> int:
    return sum(end - start for _, start, end in intervals)


def intersect_bp(a: list[tuple[str, int, int]], b: list[tuple[str, int, int]]) -> int:
    by_chrom_a: dict[str, list[tuple[int, int]]] = {}
    by_chrom_b: dict[str, list[tuple[int, int]]] = {}
    for chrom, start, end in a:
        by_chrom_a.setdefault(chrom, []).append((start, end))
    for chrom, start, end in b:
        by_chrom_b.setdefault(chrom, []).append((start, end))

    total = 0
    for chrom in sorted(set(by_chrom_a) & set(by_chrom_b)):
        ia = ib = 0
        va = by_chrom_a[chrom]
        vb = by_chrom_b[chrom]
        while ia < len(va) and ib < len(vb):
            a_start, a_end = va[ia]
            b_start, b_end = vb[ib]
            total += max(0, min(a_end, b_end) - max(a_start, b_start))
            if a_end <= b_end:
                ia += 1
            else:
                ib += 1
    return total


def read_fasta_headers(path: Path) -> list[str]:
    headers: list[str] = []
    with open_text(path) as handle:
        for line in handle:
            if line.startswith(">"):
                headers.append(line[1:].strip().split()[0])
    return headers


def build_order_mapping(renamed_fasta: Path, original_fasta: Path) -> dict[str, str]:
    renamed = read_fasta_headers(renamed_fasta)
    original = read_fasta_headers(original_fasta)
    if not renamed or len(renamed) != len(original):
        return {}
    return dict(zip(renamed, original))


def infer_seqid_mapping(annotation_path: Path, tool: str) -> tuple[dict[str, str], str]:
    outdir = annotation_path.parent
    status = load_json(outdir / "status.json")

    if tool == "edta":
        mapping_path = outdir / "edta_output" / "id_mapping.json"
        mapping = load_json(mapping_path)
        if mapping:
            return mapping, str(mapping_path)
        return {}, ""

    if tool == "earlgrey" and status.get("annotation_source_kind") == "repeatmasker_out":
        source_path = Path(status.get("annotation_source_path", ""))
        input_dir = outdir / "work" / "input"
        prep_fasta = None
        if source_path.name.endswith(".prep.out"):
            prep_fasta = input_dir / source_path.name.removesuffix(".out")
        if prep_fasta is None or not prep_fasta.exists():
            prep_candidates = sorted(input_dir.glob("*.fa.prep"))
            prep_fasta = prep_candidates[0] if prep_candidates else None
        genome_path = Path(status.get("genome", "")) if status.get("genome") else None
        if prep_fasta and genome_path and prep_fasta.exists() and genome_path.exists():
            mapping = build_order_mapping(prep_fasta, genome_path)
            if mapping:
                return mapping, f"order:{prep_fasta}->{genome_path}"
        return {}, ""

    return {}, ""


def read_gff(path: Path, seqid_mapping: dict[str, str] | None = None) -> tuple[list[tuple[str, int, int]], dict[str, int]]:
    intervals: list[tuple[str, int, int]] = []
    raw_count = raw_bp = 0
    remapped_records = 0
    mapping = seqid_mapping or {}
    with open_text(path) as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            seqid = mapping.get(parts[0], parts[0])
            if seqid != parts[0]:
                remapped_records += 1
            start = int(parts[3]) - 1
            end = int(parts[4])
            intervals.append((seqid, start, end))
            raw_count += 1
            raw_bp += max(0, end - start)
    return intervals, {
        "raw_interval_count": raw_count,
        "raw_bp_sum": raw_bp,
        "remapped_records": remapped_records,
    }


def read_bed(path: Path) -> tuple[list[tuple[str, int, int]], dict[str, int]]:
    intervals: list[tuple[str, int, int]] = []
    raw_count = raw_bp = 0
    with open_text(path) as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            start = int(parts[1])
            end = int(parts[2])
            intervals.append((parts[0], start, end))
            raw_count += 1
            raw_bp += max(0, end - start)
    return intervals, {
        "raw_interval_count": raw_count,
        "raw_bp_sum": raw_bp,
    }


def write_bed(path: Path, intervals: Iterable[tuple[str, int, int]]) -> None:
    with path.open("wt") as handle:
        for chrom, start, end in intervals:
            handle.write(f"{chrom}\t{start}\t{end}\n")


def compare_one(
    species: str,
    tool: str,
    denovo_path_s: str,
    ucsc_path_s: str,
    outdir_s: str,
) -> dict[str, str | int]:
    outdir = Path(outdir_s)
    bed_dir = outdir / "merged_beds"
    bed_dir.mkdir(parents=True, exist_ok=True)
    denovo_path = Path(denovo_path_s)
    ucsc_path = Path(ucsc_path_s)

    seqid_mapping, remap_source = infer_seqid_mapping(denovo_path, tool)
    denovo_raw, denovo_stats = read_gff(denovo_path, seqid_mapping=seqid_mapping)
    ucsc_raw, ucsc_stats = read_bed(ucsc_path)
    denovo_merged = merge_intervals(denovo_raw)
    ucsc_merged = merge_intervals(ucsc_raw)

    denovo_bp = interval_bp(denovo_merged)
    ucsc_bp = interval_bp(ucsc_merged)
    shared = intersect_bp(denovo_merged, ucsc_merged)
    union = denovo_bp + ucsc_bp - shared
    denovo_only = denovo_bp - shared
    ucsc_only = ucsc_bp - shared
    jaccard = shared / union if union else 0.0
    denovo_covered = shared / denovo_bp if denovo_bp else 0.0
    ucsc_covered = shared / ucsc_bp if ucsc_bp else 0.0

    stem = f"{species}.{tool}"
    write_bed(bed_dir / f"{stem}.denovo_merged.bed", denovo_merged)
    write_bed(bed_dir / f"{stem}.ucsc_merged.bed", ucsc_merged)

    return {
        "species_code": species,
        "tool": tool,
        "denovo_raw_intervals": denovo_stats["raw_interval_count"],
        "denovo_raw_bp_sum": denovo_stats["raw_bp_sum"],
        "denovo_merged_intervals": len(denovo_merged),
        "denovo_merged_bp": denovo_bp,
        "ucsc_raw_strict_intervals": ucsc_stats["raw_interval_count"],
        "ucsc_raw_strict_bp_sum": ucsc_stats["raw_bp_sum"],
        "ucsc_merged_intervals": len(ucsc_merged),
        "ucsc_merged_bp": ucsc_bp,
        "shared_bp": shared,
        "denovo_only_bp": denovo_only,
        "ucsc_only_bp": ucsc_only,
        "jaccard": f"{jaccard:.6f}",
        "denovo_bp_covered_by_ucsc": f"{denovo_covered:.6f}",
        "ucsc_bp_covered_by_denovo": f"{ucsc_covered:.6f}",
        "denovo_minus_ucsc_bp": denovo_bp - ucsc_bp,
        "remap_applied": "1" if seqid_mapping else "0",
        "remap_source": remap_source,
        "remapped_records": denovo_stats["remapped_records"],
        "denovo_source": str(denovo_path),
        "ucsc_source": str(ucsc_path),
    }


def read_manifest(path: Path) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"species_code", "tool", "annotation_gff3", "comparator_strict"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"manifest missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            species = row["species_code"]
            tool = row["tool"]
            denovo = row["annotation_gff3"]
            comparator = row["comparator_strict"]
            if species and tool and denovo and comparator and comparator != "NA":
                rows.append((species, tool, denovo, comparator))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    pairs = read_manifest(Path(args.manifest))

    if args.jobs > 1 and len(pairs) > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = [
                pool.submit(compare_one, species, tool, denovo, ucsc, str(outdir))
                for species, tool, denovo, ucsc in pairs
            ]
            summary_rows = [future.result() for future in concurrent.futures.as_completed(futures)]
    else:
        summary_rows = [
            compare_one(species, tool, denovo, ucsc, str(outdir))
            for species, tool, denovo, ucsc in pairs
        ]
    summary_rows = sorted(summary_rows, key=lambda row: (str(row["species_code"]), str(row["tool"])))

    header = list(summary_rows[0])
    with (outdir / "summary.tsv").open("wt") as handle:
        handle.write("\t".join(header) + "\n")
        for row in summary_rows:
            handle.write("\t".join(str(row[col]) for col in header) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
