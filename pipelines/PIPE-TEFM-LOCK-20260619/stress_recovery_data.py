#!/usr/bin/env python3
"""Build per-species held-out recovery datasets from eval-only manifests."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
sys.path.insert(0, str(SUPP))

from prepare_ucsc_windows import choose_eval_chroms, eligible_rows, write_split  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--species", nargs="+", required=True)
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--step", type=int, default=4096)
    ap.add_argument("--max-n-frac", type=float, default=0.2)
    ap.add_argument("--max-train-windows", type=int, default=2400)
    ap.add_argument("--max-val-windows", type=int, default=600)
    ap.add_argument("--max-test-windows", type=int, default=1200)
    args = ap.parse_args()

    rows = {r["species_code"]: r for r in eligible_rows(args.manifest, "eval_only", args.species)}
    missing = sorted(set(args.species) - set(rows))
    if missing:
        raise SystemExit(f"missing eval_only manifest rows: {missing}")
    out_root = Path(args.out_dir)
    manifest = []
    for species in args.species:
        row = rows[species]
        chroms = choose_eval_chroms(row, args.window, 3)
        split_spec = [
            ("train", chroms[0], args.max_train_windows),
            ("val", chroms[1] if len(chroms) > 1 else chroms[0], args.max_val_windows),
            ("test", chroms[2] if len(chroms) > 2 else chroms[-1], args.max_test_windows),
        ]
        species_dir = out_root / species
        meta = {"species": species, "window": args.window, "step": args.step, "splits": {}}
        for split, chrom, max_windows in split_spec:
            stats = write_split(
                species_dir / split / "data.jsonl.gz",
                row["genome"],
                row["comparator_strict"],
                [chrom],
                args.window,
                args.step,
                args.max_n_frac,
                max_windows,
            )
            meta["splits"][split] = stats
        species_dir.mkdir(parents=True, exist_ok=True)
        (species_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        manifest.append(meta)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "recovery_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"species": args.species, "out_dir": str(out_root)}, indent=2))


if __name__ == "__main__":
    main()
