#!/usr/bin/env python3
"""Compare the training hg19 RepeatMasker table with UCSC's 2009 .out file.

The audit deliberately keeps the source coordinate conventions separate while
parsing, then compares normalized records only on the six chromosomes used by
the revision task.  RepeatMasker IDs and scores are not part of a comparison
key.  The raw official download is supplied by the Slurm wrapper and is never
written to the repository.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
from pathlib import Path


ALLOWED_CHROMOSOMES = ("chr1", "chr2", "chr3", "chr4", "chr11", "chr13")
ALLOWED = set(ALLOWED_CHROMOSOMES)
TE_CLASSES = {"SINE", "LINE", "LTR", "DNA", "RC", "RETROPOSON"}
OFFICIAL_URL = "https://hgdownload.soe.ucsc.edu/goldenPath/hg19/bigZips/hg19.fa.out.gz"
OFFICIAL_INDEX_URL = "https://hgdownload.soe.ucsc.edu/goldenPath/hg19/bigZips/"

# chrom, start0, end0, strand, repeat name, repeat class, repeat family
Record = tuple[str, int, int, str, str, str, str]
Coord = tuple[str, int, int, str]
Material = tuple[str, int, int]


def normalize_strand(value: str) -> str:
    if value == "C":
        return "-"
    if value in {"+", "-"}:
        return value
    raise ValueError(f"unsupported RepeatMasker strand: {value!r}")


def split_class_family(value: str) -> tuple[str, str]:
    value = value.strip().upper()
    if "/" in value:
        repeat_class, family = value.split("/", 1)
    else:
        repeat_class, family = value, ""
    return repeat_class, family


def label_bucket(repeat_class: str) -> str:
    if repeat_class in TE_CLASSES:
        return "P"
    if "?" in repeat_class or repeat_class == "UNKNOWN":
        return "I"
    return "N"


class Parsed:
    """Counters and coordinate material for one source."""

    def __init__(self) -> None:
        self.records: collections.Counter[Record] = collections.Counter()
        self.coords: collections.Counter[Coord] = collections.Counter()
        self.material: collections.Counter[Material] = collections.Counter()
        self.by_chrom: dict[str, collections.Counter[Record]] = {
            chrom: collections.Counter() for chrom in ALLOWED_CHROMOSOMES
        }
        self.coords_by_chrom: dict[str, collections.Counter[Coord]] = {
            chrom: collections.Counter() for chrom in ALLOWED_CHROMOSOMES
        }
        self.material_by_chrom: dict[str, collections.Counter[Material]] = {
            chrom: collections.Counter() for chrom in ALLOWED_CHROMOSOMES
        }
        self.buckets: dict[str, collections.Counter[Record]] = {
            bucket: collections.Counter() for bucket in ("P", "I", "N")
        }
        self.bucket_by_chrom: dict[str, dict[str, collections.Counter[Record]]] = {
            chrom: {bucket: collections.Counter() for bucket in ("P", "I", "N")}
            for chrom in ALLOWED_CHROMOSOMES
        }
        self.bucket_intervals: dict[str, dict[str, list[tuple[int, int]]]] = {
            chrom: {bucket: [] for bucket in ("P", "I", "N")}
            for chrom in ALLOWED_CHROMOSOMES
        }
        self.te_intervals: dict[str, list[tuple[int, int]]] = {
            chrom: [] for chrom in ALLOWED_CHROMOSOMES
        }
        self.rows = 0
        self.te_rows = 0

    def add(self, record: Record) -> None:
        chrom, start, end, strand, _, repeat_class, _ = record
        bucket = label_bucket(repeat_class)
        coord = (chrom, start, end, strand)
        material = (chrom, start, end)
        self.records[record] += 1
        self.coords[coord] += 1
        self.material[material] += 1
        self.by_chrom[chrom][record] += 1
        self.coords_by_chrom[chrom][coord] += 1
        self.material_by_chrom[chrom][material] += 1
        self.buckets[bucket][record] += 1
        self.bucket_by_chrom[chrom][bucket][record] += 1
        self.bucket_intervals[chrom][bucket].append((start, end))
        self.rows += 1
        if bucket == "P":
            self.te_intervals[chrom].append((start, end))
            self.te_rows += 1


def make_record(
    chrom: str,
    start0: int,
    end0: int,
    strand: str,
    repeat_name: str,
    repeat_class: str,
    repeat_family: str,
) -> Record:
    if chrom not in ALLOWED:
        raise ValueError(f"unexpected chromosome {chrom}")
    if not 0 <= start0 < end0:
        raise ValueError(f"invalid interval {chrom}:{start0}-{end0}")
    return (
        chrom,
        int(start0),
        int(end0),
        normalize_strand(strand),
        repeat_name.strip().upper(),
        repeat_class.strip().upper(),
        repeat_family.strip().upper(),
    )


def parse_rmsk(path: Path) -> Parsed:
    """Parse UCSC rmsk.txt coordinates, already 0-based half-open."""
    parsed = Parsed()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.rstrip("\r\n").split("\t")
            # Do not inspect annotation fields on chromosomes outside the
            # permitted panel.  The training table is expected to be 17-column.
            if len(fields) < 6 or fields[5] not in ALLOWED:
                continue
            if len(fields) != 17:
                raise ValueError(f"{path}:{line_no}: expected 17 columns")
            chrom = fields[5]
            start0, end0 = int(fields[6]), int(fields[7])
            record = make_record(
                chrom,
                start0,
                end0,
                fields[9],
                fields[10],
                *split_class_family(fields[11]),
            )
            # Keep the source family as its own field.  In rmsk.txt the class
            # and family are separate columns; split_class_family above only
            # handles a slash if a source contains one in the class field.
            if fields[12].strip():
                record = (*record[:5], record[5], fields[12].strip().upper())
            parsed.add(record)
    return parsed


def parse_out(path: Path) -> Parsed:
    """Parse RepeatMasker .out rows and convert 1-based closed intervals."""
    parsed = Parsed()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.split()
            if len(fields) < 15:
                continue
            # Filter by the permitted chromosome before parsing coordinates or
            # annotation fields.  This keeps the audit's source scope explicit
            # and avoids inspecting rows outside the six-chromosome panel.
            chrom = fields[4]
            if chrom not in ALLOWED:
                continue
            try:
                # The first three values are score/div/del/ins; score is only
                # parsed to distinguish data rows from the textual header and
                # is intentionally omitted from the comparison key.
                float(fields[0])
                start1, end1 = int(fields[5]), int(fields[6])
            except ValueError:
                continue
            if not 1 <= start1 <= end1:
                raise ValueError(f"{path}:{line_no}: invalid 1-based interval")
            repeat_class, family = split_class_family(fields[10])
            record = make_record(
                chrom,
                start1 - 1,
                end1,
                fields[8],
                fields[9],
                repeat_class,
                family,
            )
            parsed.add(record)
    return parsed


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def subtract_intervals(
    source: list[tuple[int, int]], blockers: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    blocked = merge_intervals(blockers)
    for start, end in merge_intervals(source):
        cursor = start
        for block_start, block_end in blocked:
            if block_end <= cursor:
                continue
            if block_start >= end:
                break
            if block_start > cursor:
                result.append((cursor, min(block_start, end)))
            cursor = max(cursor, block_end)
            if cursor >= end:
                break
        if cursor < end:
            result.append((cursor, end))
    return result


def intersection_length(
    left: list[tuple[int, int]], right: list[tuple[int, int]]
) -> int:
    left, right = merge_intervals(left), merge_intervals(right)
    i = j = total = 0
    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0])
        end = min(left[i][1], right[j][1])
        if start < end:
            total += end - start
        if left[i][1] <= right[j][1]:
            i += 1
        else:
            j += 1
    return total


def counter_stats(left: collections.Counter, right: collections.Counter) -> dict:
    matched = sum(min(count, right.get(key, 0)) for key, count in left.items())
    left_only = sum(max(count - right.get(key, 0), 0) for key, count in left.items())
    right_only = sum(max(count - left.get(key, 0), 0) for key, count in right.items())
    return {
        "official_2009_rows": int(sum(left.values())),
        "training_rmsk_rows": int(sum(right.values())),
        "matched_rows": int(matched),
        "official_2009_only_rows": int(left_only),
        "training_rmsk_only_rows": int(right_only),
        "official_2009_unique_keys": int(len(left)),
        "training_rmsk_unique_keys": int(len(right)),
    }


def effective_label_intervals(parsed: Parsed) -> dict[str, dict[str, list[tuple[int, int]]]]:
    """Return annotation-derived P and ignore material after ignore override."""
    result = {}
    for chrom in ALLOWED_CHROMOSOMES:
        positive = parsed.bucket_intervals[chrom]["P"]
        ignored = parsed.bucket_intervals[chrom]["I"]
        result[chrom] = {
            "P": subtract_intervals(positive, ignored),
            "I": merge_intervals(ignored),
        }
    return result


def coverage_summary(left: Parsed, right: Parsed) -> dict:
    left_labels = effective_label_intervals(left)
    right_labels = effective_label_intervals(right)
    by_chrom = {}
    exact = True
    for chrom in ALLOWED_CHROMOSOMES:
        left_te = merge_intervals(left.te_intervals[chrom])
        right_te = merge_intervals(right.te_intervals[chrom])
        left_p = left_labels[chrom]["P"]
        right_p = right_labels[chrom]["P"]
        left_i = left_labels[chrom]["I"]
        right_i = right_labels[chrom]["I"]
        te_intersection = intersection_length(left_te, right_te)
        p_intersection = intersection_length(left_p, right_p)
        i_intersection = intersection_length(left_i, right_i)
        row = {
            "te": {
                "official_2009_bp": int(sum(end - start for start, end in left_te)),
                "training_rmsk_bp": int(sum(end - start for start, end in right_te)),
                "intersection_bp": int(te_intersection),
                "official_2009_only_bp": int(sum(end - start for start, end in left_te) - te_intersection),
                "training_rmsk_only_bp": int(sum(end - start for start, end in right_te) - te_intersection),
            },
            "effective_labels": {},
        }
        for bucket, left_intervals, right_intervals, overlap in (
            ("P", left_p, right_p, p_intersection),
            ("I", left_i, right_i, i_intersection),
        ):
            left_bp = sum(end - start for start, end in left_intervals)
            right_bp = sum(end - start for start, end in right_intervals)
            row["effective_labels"][bucket] = {
                "official_2009_bp": int(left_bp),
                "training_rmsk_bp": int(right_bp),
                "intersection_bp": int(overlap),
                "official_2009_only_bp": int(left_bp - overlap),
                "training_rmsk_only_bp": int(right_bp - overlap),
                "exact_intervals": left_intervals == right_intervals,
            }
            exact &= left_intervals == right_intervals
        exact &= left_te == right_te
        by_chrom[chrom] = row
    return {
        "by_chromosome": by_chrom,
        "effective_label_intervals_equal": bool(exact),
    }


def write_differences(path: Path, official: Parsed, training: Parsed) -> None:
    """Keep every unmatched normalized key, aggregated only by multiplicity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(
            [
                "scope",
                "source",
                "chrom",
                "start0",
                "end0",
                "strand",
                "repeat_name",
                "repClass",
                "repFamily",
                "multiplicity",
            ]
        )
        for scope, left, right in (
            ("all", official.records, training.records),
            ("TE", official.buckets["P"], training.buckets["P"]),
            ("ignore", official.buckets["I"], training.buckets["I"]),
        ):
            for source, counter in (
                ("official_2009_only", left - right),
                ("training_rmsk_only", right - left),
            ):
                for key, count in sorted(counter.items()):
                    writer.writerow([scope, source, *key, int(count)])


def build_report(official: Parsed, training: Parsed, config_path: Path, rmsk_path: Path, out: Path) -> dict:
    all_stats = counter_stats(official.records, training.records)
    te_stats = counter_stats(official.buckets["P"], training.buckets["P"])
    ignore_stats = counter_stats(official.buckets["I"], training.buckets["I"])
    coords_stats = counter_stats(official.coords, training.coords)
    # The overall TE coordinate comparison is intentionally explicit rather
    # than relying on record names or RepeatMasker IDs.
    te_coord_left = collections.Counter()
    te_coord_right = collections.Counter()
    for (chrom, start, end, strand, *_), count in official.buckets["P"].items():
        te_coord_left[(chrom, start, end, strand)] += count
    for (chrom, start, end, strand, *_), count in training.buckets["P"].items():
        te_coord_right[(chrom, start, end, strand)] += count
    te_coords_stats = counter_stats(te_coord_left, te_coord_right)
    by_chrom = {}
    for chrom in ALLOWED_CHROMOSOMES:
        by_chrom[chrom] = {
            "all_records": counter_stats(official.by_chrom[chrom], training.by_chrom[chrom]),
            "all_coordinates_with_strand": counter_stats(
                official.coords_by_chrom[chrom], training.coords_by_chrom[chrom]
            ),
            "TE_records": counter_stats(
                official.bucket_by_chrom[chrom]["P"], training.bucket_by_chrom[chrom]["P"]
            ),
            "ignore_records": counter_stats(
                official.bucket_by_chrom[chrom]["I"], training.bucket_by_chrom[chrom]["I"]
            ),
            "label_material": {},
        }
    coverage = coverage_summary(official, training)
    for chrom in ALLOWED_CHROMOSOMES:
        by_chrom[chrom]["label_material"] = coverage["by_chromosome"][chrom]
    exact_all = official.records == training.records
    exact_te = official.buckets["P"] == training.buckets["P"]
    exact_ignore = official.buckets["I"] == training.buckets["I"]
    if exact_all and coverage["effective_label_intervals_equal"]:
        verdict = "2009_PROVENANCE_CLOSED_EXACT_NORMALIZED_RECORDS"
    elif coverage["effective_label_intervals_equal"]:
        verdict = "2009_LABEL_MATERIAL_MATCH_RECORD_PROVENANCE_NOT_EXACT"
    else:
        verdict = "CANNOT_CLAIM_2009_INHERITANCE"
    return {
        "status": "AUDIT_COMPLETED",
        "verdict": verdict,
        "allowed_chromosomes": list(ALLOWED_CHROMOSOMES),
        "official_2009": {
            "url": OFFICIAL_URL,
            "index_url": OFFICIAL_INDEX_URL,
            "repeatmasker": "open-3-2-7 (2009-01-29), -s",
            "library": "RepBase RELEASE 20090120",
            "coordinate_convention": "1-based closed; normalized to 0-based half-open",
            "rows": official.rows,
            "TE_rows": official.te_rows,
        },
        "training_rmsk": {
            "path": str(rmsk_path),
            "coordinate_convention": "0-based half-open",
            "rows": training.rows,
            "TE_rows": training.te_rows,
        },
        "config": str(config_path),
        "normalization": {
            "strand": "C converted to -; + retained",
            "case_folding": "repeat_name, repClass and repFamily converted to uppercase",
            "comparison_key": "chrom,start0,end0,strand,repeat_name,repClass,repFamily",
            "excluded_from_key": ["RepeatMasker ID", "score", "div", "del", "ins", "alignment offsets"],
            "label_buckets": {"P": "TE class", "I": "UNKNOWN or ? class", "N": "other class"},
        },
        "overall": {
            "all_normalized_records": all_stats,
            "all_normalized_coordinates_with_strand": coords_stats,
            "TE_normalized_records": te_stats,
            "TE_normalized_coordinates_with_strand": te_coords_stats,
            "ignore_normalized_records": ignore_stats,
            "exact_all_records": bool(exact_all),
            "exact_TE_records": bool(exact_te),
            "exact_ignore_records": bool(exact_ignore),
        },
        "by_chromosome": by_chrom,
        "coverage": coverage,
        "differences_file": str(out / "normalized_differences.tsv.gz"),
    }


def write_markdown(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    overall = report["overall"]
    lines = [
        "# HG19 2009 RepeatMasker provenance audit",
        "",
        f"**Verdict:** `{report['verdict']}`",
        "",
        "This audit compares the official UCSC hg19 initial-release `.out` file "
        "with the raw training `rmsk.txt.gz` on chr1/2/3/4/11/13 only. "
        "Official 1-based closed coordinates were converted to 0-based half-open; "
        "`C` strand was converted to `-`; repeat names, classes and families were "
        "case-folded to uppercase. IDs and scores were excluded from keys.",
        "",
        f"Official source: [{OFFICIAL_URL}]({OFFICIAL_URL}) "
        f"(RepeatMasker open-3-2-7, `-s`, RepBase RELEASE 20090120).",
        "",
        "| Scope | Official rows | Training rows | Matched | Official only | Training only |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label, key in (
        ("all normalized records", "all_normalized_records"),
        ("TE normalized records", "TE_normalized_records"),
        ("ignore normalized records", "ignore_normalized_records"),
        ("TE coordinates + strand", "TE_normalized_coordinates_with_strand"),
    ):
        row = overall[key]
        lines.append(
            f"| {label} | {row['official_2009_rows']} | {row['training_rmsk_rows']} | "
            f"{row['matched_rows']} | {row['official_2009_only_rows']} | "
            f"{row['training_rmsk_only_rows']} |"
        )
    lines += [
        "",
        "| Chromosome | Official TE bp | Training TE bp | TE intersection bp | Effective P/I intervals equal |",
        "|---|---:|---:|---:|---|",
    ]
    for chrom in report["allowed_chromosomes"]:
        row = report["coverage"]["by_chromosome"][chrom]
        lines.append(
            f"| {chrom} | {row['te']['official_2009_bp']} | {row['te']['training_rmsk_bp']} | "
            f"{row['te']['intersection_bp']} | "
            f"{all(v['exact_intervals'] for v in row['effective_labels'].values())} |"
        )
    lines += [
        "",
        f"All unmatched normalized keys are retained in `{report['differences_file']}` "
        "with multiplicities; the raw official download is kept beside the report "
        "on Baobab and is not part of the repository.",
        "",
        "The verdict closes exact 2009 provenance only when normalized records and "
        "effective positive/ignore label material agree. A material-only match is "
        "reported separately and should not be described as exact library/engine "
        "inheritance.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict:
    root = args.root.resolve()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    rmsk = args.rmsk if args.rmsk.is_absolute() else root / args.rmsk
    official = args.official_out.resolve()
    if not rmsk.is_file() or not official.is_file():
        raise FileNotFoundError(f"missing source: rmsk={rmsk}, official={official}")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    parsed_official = parse_out(official)
    parsed_training = parse_rmsk(rmsk)
    report = build_report(parsed_official, parsed_training, args.config.resolve(), rmsk, out)
    report["official_2009"]["downloaded_file"] = str(official)
    report_path = out / "provenance_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_differences(out / "normalized_differences.tsv.gz", parsed_official, parsed_training)
    write_markdown(report, out / "provenance_report.md")
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--rmsk", type=Path, required=True)
    parser.add_argument("--official-out", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
