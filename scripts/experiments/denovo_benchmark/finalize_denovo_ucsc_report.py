#!/usr/bin/env python3
"""Finalize de novo vs UCSC overlap report tables."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def concordance_class(jaccard: float) -> str:
    if jaccard >= 0.80:
        return "high"
    if jaccard >= 0.50:
        return "moderate"
    if jaccard >= 0.10:
        return "low"
    return "severe"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    manifest = Path(args.manifest)
    rows: list[dict[str, str]] = []
    with (outdir / "summary.tsv").open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            row["concordance_class"] = concordance_class(float(row["jaccard"]))
            rows.append(row)

    ranked = sorted(rows, key=lambda row: (row["tool"], -float(row["jaccard"]), row["species_code"]))
    fields = [
        "species_code",
        "tool",
        "concordance_class",
        "jaccard",
        "denovo_bp_covered_by_ucsc",
        "ucsc_bp_covered_by_denovo",
        "denovo_merged_bp",
        "ucsc_merged_bp",
        "shared_bp",
        "denovo_only_bp",
        "ucsc_only_bp",
        "denovo_minus_ucsc_bp",
    ]
    with (outdir / "qc_flags.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row[field] for field in fields} for row in rows)

    with (outdir / "summary_ranked.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=ranked[0].keys())
        writer.writeheader()
        writer.writerows(ranked)

    tool_counts = Counter(row["tool"] for row in rows)
    class_counts = Counter(f"{row['tool']}::{row['concordance_class']}" for row in rows)
    counts_lines = ["key\tcount"]
    for key in sorted(tool_counts):
        counts_lines.append(f"tool::{key}\t{tool_counts[key]}")
    for key in sorted(class_counts):
        counts_lines.append(f"{key}\t{class_counts[key]}")
    (outdir / "tool_counts.tsv").write_text("\n".join(counts_lines) + "\n")

    readme = f"""# {outdir.name}

De novo benchmark standardized annotation vs UCSC strict-TE comparator audit.

Inputs:
- Manifest: `{manifest}`
- Summary source: `{outdir / 'summary.tsv'}`

Outputs:
- `summary.tsv`: species/tool bp overlap metrics.
- `qc_flags.tsv`: concordance classes high>=0.80, moderate>=0.50, low>=0.10, severe<0.10.
- `summary_ranked.tsv`: rows ranked within each tool by Jaccard.
- `tool_counts.tsv`: row counts by tool and tool-specific concordance class.
- `merged_beds/`: merged de novo and UCSC interval BEDs for each species/tool pair.

Result counts: {len(rows)} rows across {len(tool_counts)} tools.
"""
    (outdir / "README.md").write_text(readme)
    print(readme)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
