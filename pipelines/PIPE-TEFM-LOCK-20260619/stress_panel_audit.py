#!/usr/bin/env python3
"""Join model transfer scores with label-source concordance for primary/stress panels."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


PRIMARY = {"human", "cattle", "horse", "pig", "opossum", "mouse", "zebrafish", "chicken", "western_clawed_frog", "fruit_fly", "c_elegans"}
STRESS = {"lizard", "x_laevis", "western_honey_bee", "red_flour_beetle"}


def read_tsv(path: str) -> list[dict]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mixed-eval", required=True)
    ap.add_argument("--concordance", required=True)
    ap.add_argument("--out-tsv", required=True)
    args = ap.parse_args()

    conc = {r["species_code"]: r for r in read_tsv(args.concordance)}
    rows = []
    for r in read_tsv(args.mixed_eval):
        if r.get("model") != "invert_boost_animal_4096":
            continue
        species = r.get("species", "")
        if species in PRIMARY:
            panel = "primary_pre_registered"
        elif species in STRESS:
            panel = "stress_diagnostic"
        else:
            panel = "other"
        c = conc.get(species, {})
        out = {
            "panel": panel,
            "species": species,
            "stage": r.get("stage", ""),
            "te_f1": r.get("te_f1", ""),
            "te_precision": r.get("te_precision", ""),
            "te_recall": r.get("te_recall", ""),
            "te_auprc": r.get("te_auprc", ""),
            "label_jaccard": c.get("jaccard", ""),
            "self_merged_bp": c.get("self_merged_bp", ""),
            "ucsc_merged_bp": c.get("ucsc_merged_bp", ""),
            "self_bp_covered_by_ucsc": c.get("self_bp_covered_by_ucsc", ""),
            "ucsc_bp_covered_by_self": c.get("ucsc_bp_covered_by_self", ""),
        }
        rows.append(out)
    write_tsv(Path(args.out_tsv), rows)


if __name__ == "__main__":
    main()
