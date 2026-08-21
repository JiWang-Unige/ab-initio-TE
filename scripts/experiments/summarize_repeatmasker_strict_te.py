#!/usr/bin/env python3
"""Summarize strict TE calls from merged RepeatMasker .out files."""

from __future__ import annotations

import argparse
import csv
import gzip
from collections import Counter
from pathlib import Path

STRICT_TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "RETROPOSON"}


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", errors="replace")
    return path.open(errors="replace")


def parse_out(path: Path) -> tuple[int, int, Counter[str]]:
    intervals = 0
    bp_sum = 0
    classes: Counter[str] = Counter()
    with open_text(path) as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith(("SW", "score", "There were no")):
                continue
            parts = stripped.split()
            if len(parts) < 11:
                continue
            class_family = parts[10]
            top = class_family.split("/", 1)[0].upper()
            if top not in STRICT_TE_CLASSES:
                continue
            try:
                start = int(parts[5])
                end = int(parts[6])
            except ValueError:
                continue
            intervals += 1
            bp_sum += max(0, end - start + 1)
            classes[top] += 1
    return intervals, bp_sum, classes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species-manifest", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--fail-zero", action="store_true")
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    with Path(args.species_manifest).open(newline="") as handle:
        species_rows = list(csv.DictReader(handle, delimiter="\t"))
    for row in species_rows:
        code = row["species_code"]
        out_path = Path(row["species_output_dir"]) / f"{code}.repeatmasker.out.gz"
        if not out_path.exists():
            rows.append({
                "species_code": code,
                "repeatmasker_out": str(out_path),
                "strict_intervals": "0",
                "strict_bp_sum": "0",
                "strict_classes": "",
                "status": "MISSING_OUT",
            })
            continue
        intervals, bp_sum, classes = parse_out(out_path)
        status = "OK"
        if args.fail_zero and bp_sum <= 0:
            status = "ZERO_STRICT_TE"
        rows.append({
            "species_code": code,
            "repeatmasker_out": str(out_path),
            "strict_intervals": str(intervals),
            "strict_bp_sum": str(bp_sum),
            "strict_classes": ";".join(f"{k}:{v}" for k, v in sorted(classes.items())),
            "status": status,
        })

    fields = ["species_code", "repeatmasker_out", "strict_intervals", "strict_bp_sum", "strict_classes", "status"]
    out = Path(args.summary_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    bad = [row for row in rows if row["status"] != "OK"]
    if bad:
        preview = ", ".join(f"{row['species_code']}:{row['status']}" for row in bad[:20])
        raise SystemExit(f"strict TE summary failed: {preview}")


if __name__ == "__main__":
    main()
