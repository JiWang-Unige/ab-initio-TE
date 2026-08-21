#!/usr/bin/env python3
"""Finalize self Label-A vs UCSC comparison report tables."""

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
            row["self_minus_ucsc_bp"] = str(
                int(row["self_merged_bp"]) - int(row["ucsc_merged_bp"])
            )
            rows.append(row)

    ranked = sorted(rows, key=lambda row: float(row["jaccard"]), reverse=True)
    fields = [
        "species_code",
        "concordance_class",
        "jaccard",
        "self_bp_covered_by_ucsc",
        "ucsc_bp_covered_by_self",
        "self_merged_bp",
        "ucsc_merged_bp",
        "shared_bp",
        "self_only_bp",
        "ucsc_only_bp",
        "self_minus_ucsc_bp",
    ]
    with (outdir / "qc_flags.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row[field] for field in fields} for row in rows)

    with (outdir / "summary_ranked_by_jaccard.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(ranked)

    missing_path = outdir / "missing_comparator.tsv"
    missing: list[str] = []
    if missing_path.exists():
        with missing_path.open(newline="") as handle:
            missing = [row["species_code"] for row in csv.DictReader(handle, delimiter="\t")]

    counts = Counter(row["concordance_class"] for row in rows)
    readme = f"""# {outdir.name}

Current ready-by-design self-run RepeatMasker+Dfam Label-A vs UCSC/local strict-TE comparator audit.

Inputs:
- Manifest: `{manifest}`
- Pair manifest: deduplicated by `species_code` from current ready-by-design entries.
- Self Label-A source: current `02_ready_by_design` entries resolving to the latest ready self Label-A targets.
- Comparator source: `/home/users/j/jwang/ab-initio-TE/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/**` strict TE BEDs.

Outputs:
- `summary.tsv`: species-level bp overlap metrics.
- `summary_ranked_by_jaccard.tsv`: rows sorted by Jaccard descending.
- `qc_flags.tsv`: concordance classes high>=0.80, moderate>=0.50, low>=0.10, severe<0.10.
- `missing_comparator.tsv`: ready entries without usable strict UCSC/local comparator.
- `merged_beds/`: merged strict-TE intervals for each paired species/source.

Result counts: {len(rows)} paired entries; high={counts.get("high", 0)}, moderate={counts.get("moderate", 0)}, low={counts.get("low", 0)}, severe={counts.get("severe", 0)}; missing comparators={len(missing)}.

Missing comparator species: {", ".join(missing) if missing else "none"}.
"""
    (outdir / "README.md").write_text(readme)
    print(readme)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
