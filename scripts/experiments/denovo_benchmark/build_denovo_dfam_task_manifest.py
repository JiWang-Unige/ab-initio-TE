#!/usr/bin/env python3
"""Build de novo+Dfam RepeatMasker task manifest from finalized benchmark outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


TOOLS = ("repeatmodeler", "edta", "repeatscout", "earlgrey")


def load_species_map(path: Path) -> dict[str, str]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return {row["species_code"]: row["repeatmasker_species"] for row in reader}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species-manifest", required=True)
    parser.add_argument("--species-table", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    species_manifest = Path(args.species_manifest)
    species_map = load_species_map(Path(args.species_table))
    run_root = Path(args.run_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "task_id",
        "species_code",
        "repeatmasker_species",
        "genome",
        "denovo_tool",
        "denovo_library",
        "output_dir",
    ]
    task_id = 0
    with species_manifest.open(newline="") as handle, out.open("w", newline="") as out_handle:
        reader = csv.DictReader(handle, delimiter="\t")
        writer = csv.DictWriter(out_handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            species = row["species_code"]
            genome = row["normalized_genome"]
            repeatmasker_species = species_map[species]
            for tool in TOOLS:
                task_id += 1
                writer.writerow(
                    {
                        "task_id": task_id,
                        "species_code": species,
                        "repeatmasker_species": repeatmasker_species,
                        "genome": genome,
                        "denovo_tool": tool,
                        "denovo_library": str(run_root / "raw_outputs" / species / tool / "library.fasta"),
                        "output_dir": str(run_root / "dfam_augmented" / species / tool),
                    }
                )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
