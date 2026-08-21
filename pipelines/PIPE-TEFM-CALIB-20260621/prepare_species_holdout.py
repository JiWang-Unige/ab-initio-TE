#!/usr/bin/env python3
"""Build species-specific train/val/test windows from one manifest row.

This is intentionally used only for stress calibration screens such as
honeybee/beetle, where the species is eval_only in the main panel but we need
to test whether direct chromosome-heldout fine-tuning can recover annotation.
"""
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
    ap.add_argument("--species", required=True)
    ap.add_argument("--split", default="eval_only")
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--step", type=int, default=4096)
    ap.add_argument("--max-n-frac", type=float, default=0.2)
    ap.add_argument("--train-windows", type=int, default=3600)
    ap.add_argument("--val-windows", type=int, default=900)
    ap.add_argument("--test-windows", type=int, default=1200)
    args = ap.parse_args()

    rows = eligible_rows(args.manifest, args.split, [args.species])
    if not rows:
        raise SystemExit(f"Missing {args.split} row for {args.species} with comparator_strict")
    row = rows[0]
    chroms = choose_eval_chroms(row, args.window, 3)
    if len(chroms) < 2:
        raise SystemExit(f"Need at least 2 labelled chromosomes for {args.species}")
    train_chrom = chroms[0]
    val_chrom = chroms[1]
    test_chrom = chroms[2] if len(chroms) > 2 else chroms[1]
    out = Path(args.out_dir)
    meta = {
        "mode": "species_holdout",
        "species": args.species,
        "source_split": args.split,
        "window": args.window,
        "step": args.step,
        "splits": {},
    }
    meta["splits"]["train"] = write_split(
        out / "train/data.jsonl.gz", row["genome"], row["comparator_strict"],
        [train_chrom], args.window, args.step, args.max_n_frac, args.train_windows,
        row.get("comparator_plus_unknown"),
    )
    meta["splits"]["val"] = write_split(
        out / "val/data.jsonl.gz", row["genome"], row["comparator_strict"],
        [val_chrom], args.window, args.step, args.max_n_frac, args.val_windows,
        row.get("comparator_plus_unknown"),
    )
    meta["splits"]["test"] = write_split(
        out / "test/data.jsonl.gz", row["genome"], row["comparator_strict"],
        [test_chrom], args.window, args.step, args.max_n_frac, args.test_windows,
        row.get("comparator_plus_unknown"),
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
