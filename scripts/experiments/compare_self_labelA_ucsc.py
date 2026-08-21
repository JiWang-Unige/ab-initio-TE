#!/usr/bin/env python3
"""Compare self-run RepeatMasker Label-A with UCSC/local RepeatMasker TE BEDs."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
from pathlib import Path
from typing import Iterable


STRICT_TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "Retroposon"}


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def is_strict_te(class_family: str) -> bool:
    top = class_family.split("/", 1)[0]
    return top in STRICT_TE_CLASSES


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


def read_self_repeatmasker(path: Path) -> tuple[list[tuple[str, int, int]], dict[str, int]]:
    intervals: list[tuple[str, int, int]] = []
    raw_count = raw_bp = skipped_non_te = 0
    class_bp: dict[str, int] = {}
    with open_text(path) as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) < 11 or not parts[0].isdigit():
                continue
            class_family = parts[10]
            start = int(parts[5]) - 1
            end = int(parts[6])
            bp = max(0, end - start)
            class_bp[class_family] = class_bp.get(class_family, 0) + bp
            if not is_strict_te(class_family):
                skipped_non_te += 1
                continue
            intervals.append((parts[4], start, end))
            raw_count += 1
            raw_bp += bp
    return intervals, {
        "raw_strict_interval_count": raw_count,
        "raw_strict_bp_sum": raw_bp,
        "skipped_non_te_records": skipped_non_te,
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
        "raw_strict_interval_count": raw_count,
        "raw_strict_bp_sum": raw_bp,
    }


def write_bed(path: Path, intervals: Iterable[tuple[str, int, int]]) -> None:
    with path.open("wt") as handle:
        for chrom, start, end in intervals:
            handle.write(f"{chrom}\t{start}\t{end}\n")


def compare_one(species: str, self_path_s: str, ucsc_path_s: str, outdir_s: str) -> dict[str, str | int]:
    outdir = Path(outdir_s)
    bed_dir = outdir / "merged_beds"
    bed_dir.mkdir(parents=True, exist_ok=True)
    self_path = Path(self_path_s)
    ucsc_path = Path(ucsc_path_s)

    self_raw, self_stats = read_self_repeatmasker(self_path)
    ucsc_raw, ucsc_stats = read_bed(ucsc_path)
    self_merged = merge_intervals(self_raw)
    ucsc_merged = merge_intervals(ucsc_raw)

    self_bp = interval_bp(self_merged)
    ucsc_bp = interval_bp(ucsc_merged)
    shared = intersect_bp(self_merged, ucsc_merged)
    union = self_bp + ucsc_bp - shared
    self_only = self_bp - shared
    ucsc_only = ucsc_bp - shared
    jaccard = shared / union if union else 0.0
    self_covered = shared / self_bp if self_bp else 0.0
    ucsc_covered = shared / ucsc_bp if ucsc_bp else 0.0

    write_bed(bed_dir / f"{species}.self_labelA.strict_merged.bed", self_merged)
    write_bed(bed_dir / f"{species}.ucsc.strict_merged.bed", ucsc_merged)

    return {
        "species_code": species,
        "self_raw_strict_intervals": self_stats["raw_strict_interval_count"],
        "self_raw_strict_bp_sum": self_stats["raw_strict_bp_sum"],
        "self_skipped_non_te_records": self_stats["skipped_non_te_records"],
        "self_merged_intervals": len(self_merged),
        "self_merged_bp": self_bp,
        "ucsc_raw_strict_intervals": ucsc_stats["raw_strict_interval_count"],
        "ucsc_raw_strict_bp_sum": ucsc_stats["raw_strict_bp_sum"],
        "ucsc_merged_intervals": len(ucsc_merged),
        "ucsc_merged_bp": ucsc_bp,
        "shared_bp": shared,
        "self_only_bp": self_only,
        "ucsc_only_bp": ucsc_only,
        "jaccard": f"{jaccard:.6f}",
        "self_bp_covered_by_ucsc": f"{self_covered:.6f}",
        "ucsc_bp_covered_by_self": f"{ucsc_covered:.6f}",
        "self_source": str(self_path),
        "ucsc_source": str(ucsc_path),
    }


def read_manifest(path: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"species_code", "self_out", "comparator_strict"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"manifest missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            species = row["species_code"]
            self_out = row["self_out"]
            comparator = row["comparator_strict"]
            if species and self_out and comparator and comparator != "NA":
                rows.append((species, self_out, comparator))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", action="append",
                        help="species_code,self_repeatmasker_out,ucsc_te_strict_bed")
    parser.add_argument("--manifest", help="TSV with species_code, self_out, comparator_strict")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    if not args.pair and not args.manifest:
        parser.error("provide --pair or --manifest")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    pairs: list[tuple[str, str, str]] = []
    for pair in args.pair or []:
        species, self_path_s, ucsc_path_s = pair.split(",", 2)
        pairs.append((species, self_path_s, ucsc_path_s))
    if args.manifest:
        pairs.extend(read_manifest(Path(args.manifest)))

    if args.jobs > 1 and len(pairs) > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = [
                pool.submit(compare_one, species, self_path, ucsc_path, str(outdir))
                for species, self_path, ucsc_path in pairs
            ]
            summary_rows = [future.result() for future in concurrent.futures.as_completed(futures)]
    else:
        summary_rows = [
            compare_one(species, self_path, ucsc_path, str(outdir))
            for species, self_path, ucsc_path in pairs
        ]
    summary_rows = sorted(summary_rows, key=lambda row: str(row["species_code"]))

    header = list(summary_rows[0])
    with (outdir / "summary.tsv").open("wt") as handle:
        handle.write("\t".join(header) + "\n")
        for row in summary_rows:
            handle.write("\t".join(str(row[col]) for col in header) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
