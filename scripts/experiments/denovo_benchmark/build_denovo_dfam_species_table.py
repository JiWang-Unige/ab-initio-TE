#!/usr/bin/env python3
"""Build species table for B-animal eval de novo+Dfam augmentation."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROWS = [
    ("pig", "Sus scrofa"),
    ("cattle", "Bos taurus"),
    ("horse", "Equus caballus"),
    ("western_honey_bee", "Apis mellifera"),
    ("red_flour_beetle", "Coleoptera"),
    ("opossum", "Monodelphis domestica"),
    ("lizard", "Anolis carolinensis"),
    ("x_laevis", "Xenopus laevis"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            delimiter="\t",
            fieldnames=["species_code", "repeatmasker_species"],
        )
        writer.writeheader()
        for species_code, repeatmasker_species in ROWS:
            writer.writerow(
                {
                    "species_code": species_code,
                    "repeatmasker_species": repeatmasker_species,
                }
            )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
