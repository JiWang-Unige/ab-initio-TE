#!/usr/bin/env python3
"""Build mixed supervised binary windows from explicit species/split rows."""
from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
from pathlib import Path

SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
sys.path.insert(0, str(SUPP))

from prepare_ucsc_windows import choose_eval_chroms, eligible_rows, iter_windows, load_intervals  # noqa: E402


def parse_species_split(values: list[str]) -> dict[str, str]:
    out = {}
    for item in values:
        if ":" in item:
            species, split = item.split(":", 1)
        else:
            species, split = item, "fine_tune"
        out[species] = split
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--species-split", nargs="+", required=True,
                    help="Entries like fruit_fly:fine_tune western_honey_bee:eval_only")
    ap.add_argument("--proportions-json", required=True)
    ap.add_argument("--total-windows", type=int, required=True)
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--step", type=int, default=4096)
    ap.add_argument("--max-n-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    species_split = parse_species_split(args.species_split)
    proportions = json.loads(args.proportions_json)
    if set(proportions) != set(species_split):
        raise SystemExit("proportions species must match --species-split species")
    rows = {}
    for species, split in species_split.items():
        vals = eligible_rows(args.manifest, split, [species])
        if not vals:
            raise SystemExit(f"Missing {split} row with comparator_strict for {species}")
        rows[species] = vals[0]
    rng = random.Random(args.seed)
    out = Path(args.out_dir)
    meta = {
        "mode": "mixed_any",
        "window": args.window,
        "step": args.step,
        "species_split": species_split,
        "proportions": proportions,
        "splits": {},
    }
    for split_name, frac in [("train", 0.9), ("val", 0.1)]:
        split_path = out / split_name / "data.jsonl.gz"
        split_path.parent.mkdir(parents=True, exist_ok=True)
        split_meta = {}
        with gzip.open(split_path, "wt") as handle:
            for species, prop in proportions.items():
                row = rows[species]
                chroms = choose_eval_chroms(row, args.window, 2)
                chrom = chroms[0] if split_name == "train" or len(chroms) == 1 else chroms[1]
                quota = max(1, int(args.total_windows * frac * float(prop)))
                tmp = []
                intervals = load_intervals(row["comparator_strict"])
                for rec in iter_windows(row["genome"], intervals, {chrom}, args.window, args.step, args.max_n_frac, quota):
                    rec["species_code"] = species
                    tmp.append(rec)
                rng.shuffle(tmp)
                for rec in tmp:
                    handle.write(json.dumps(rec) + "\n")
                split_meta[species] = {"split": species_split[species], "chrom": chrom, "windows": len(tmp), "quota": quota}
        meta["splits"][split_name] = split_meta
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
