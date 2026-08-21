#!/usr/bin/env python3
"""Build de novo+Dfam vs UCSC comparison manifest for B-animal eval species."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


TOOLS = ("repeatmodeler", "edta", "repeatscout", "earlgrey")
ROLES = {"mammal_holdout", "invertebrate_holdout", "optional_stress"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-manifest", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    ready_manifest = Path(args.ready_manifest)
    run_root = Path(args.run_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with ready_manifest.open() as handle, out.open("w", newline="") as out_handle:
        reader = csv.DictReader(handle, delimiter="\t")
        writer = csv.DictWriter(
            out_handle,
            delimiter="\t",
            fieldnames=["species_code", "tool", "annotation_gff3", "comparator_strict"],
        )
        writer.writeheader()
        for row in reader:
            if row["design"] != "B_animal_production" or row["role"] not in ROLES:
                continue
            comp = row["comparator_strict"]
            if not comp or comp == "NA":
                continue
            species = row["species_code"]
            for tool in TOOLS:
                writer.writerow(
                    {
                        "species_code": species,
                        "tool": f"{tool}_plus_dfam",
                        "annotation_gff3": str(run_root / "dfam_augmented" / species / tool / "annotation.gff3"),
                        "comparator_strict": comp,
                    }
                )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
