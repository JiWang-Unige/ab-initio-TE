#!/usr/bin/env python3
"""Convert UCSC RepeatMasker annotations to TE-only BED files."""

from __future__ import annotations

import argparse
import csv
import gzip
from collections import Counter
from pathlib import Path


STRICT_TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "RETROPOSON"}
UNKNOWN_CLASSES = {"UNKNOWN", "UNSPECIFIED"}


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def normalize_class(rep_class: str) -> str:
    token = (rep_class or "").split("/", 1)[0].strip()
    return token.rstrip("?").upper()


def keep_class(rep_class: str, mode: str) -> bool:
    normalized = normalize_class(rep_class)
    if normalized in STRICT_TE_CLASSES:
        return True
    if mode == "plus_unknown" and normalized in UNKNOWN_CLASSES:
        return True
    return False


def bed_score(score: str) -> str:
    try:
        value = int(float(score))
    except ValueError:
        return "0"
    return str(max(0, min(1000, value)))


def parse_ucsc_rmsk_table(path: Path):
    with open_text(path) as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 17:
                continue
            yield {
                "chrom": fields[5],
                "start": fields[6],
                "end": fields[7],
                "strand": fields[9],
                "name": fields[10],
                "class": fields[11],
                "family": fields[12],
                "score": fields[1],
            }


def parse_repeatmasker_out(path: Path):
    with open_text(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith(("SW", "score", "There were no", "higher")):
                continue
            fields = line.split()
            if len(fields) < 14:
                continue
            try:
                int(fields[0])
                start = int(fields[5]) - 1
                end = int(fields[6])
            except ValueError:
                continue
            repeat_type = fields[10]
            if "/" in repeat_type:
                rep_class, rep_family = repeat_type.split("/", 1)
            else:
                rep_class, rep_family = repeat_type, repeat_type
            yield {
                "chrom": fields[4],
                "start": str(start),
                "end": str(end),
                "strand": fields[8],
                "name": fields[9],
                "class": rep_class,
                "family": rep_family,
                "score": fields[0],
            }


def source_rows(path: Path, source_format: str):
    if source_format == "ucsc_table":
        yield from parse_ucsc_rmsk_table(path)
    elif source_format == "repeatmasker_out":
        yield from parse_repeatmasker_out(path)
    else:
        raise SystemExit(f"Unsupported source format: {source_format}")


def write_outputs(source: Path, source_format: str, out_prefix: Path) -> None:
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    for mode in ["strict", "plus_unknown"]:
        out_bed = out_prefix.with_name(f"{out_prefix.name}_{mode}.bed.gz")
        total = 0
        kept = 0
        class_counts: Counter[str] = Counter()
        kept_counts: Counter[str] = Counter()
        with gzip.open(out_bed, "wt") as out:
            for row in source_rows(source, source_format):
                total += 1
                class_key = row["class"] or ""
                class_counts[class_key] += 1
                if not keep_class(class_key, mode):
                    continue
                kept += 1
                kept_counts[class_key] += 1
                combined = f"{row['class']}/{row['family']}" if row["family"] else row["class"]
                out.write(
                    "\t".join(
                        [
                            row["chrom"],
                            row["start"],
                            row["end"],
                            row["name"],
                            bed_score(row["score"]),
                            row["strand"],
                            row["class"],
                            row["family"],
                            combined,
                        ]
                    )
                    + "\n"
                )
        summary_rows.append(
            {
                "mode": mode,
                "source": str(source),
                "source_format": source_format,
                "total_records": total,
                "kept_records": kept,
                "output": str(out_bed),
                "kept_classes": ";".join(f"{k}:{v}" for k, v in sorted(kept_counts.items())),
                "all_classes": ";".join(f"{k}:{v}" for k, v in sorted(class_counts.items())),
            }
        )

    summary_path = out_prefix.with_name(f"{out_prefix.name}_summary.tsv")
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            delimiter="\t",
            fieldnames=[
                "mode",
                "source",
                "source_format",
                "total_records",
                "kept_records",
                "output",
                "kept_classes",
                "all_classes",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-format", choices=["ucsc_table", "repeatmasker_out"], required=True)
    parser.add_argument("--out-prefix", required=True)
    args = parser.parse_args()

    write_outputs(Path(args.source), args.source_format, Path(args.out_prefix))


if __name__ == "__main__":
    main()
