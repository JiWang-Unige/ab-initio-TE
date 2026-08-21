#!/usr/bin/env python3
"""Build main4+Unknown token-classification windows across animal species."""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import sys
from pathlib import Path

SEG = Path("pipelines/PIPE-TEFM-SEG-SF-20260618").resolve()
SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
sys.path.insert(0, str(SEG))
sys.path.insert(0, str(SUPP))

from prepare_superfamily_windows import ID2LABEL, iter_windows, opener, read_manifest  # noqa: E402
from prepare_ucsc_windows import choose_eval_chroms  # noqa: E402

SF5 = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}


def map_sf5(rep_class: str, rep_family: str = "", rep_name: str = "") -> int:
    """Strict main4 mapping; ambiguous/non-main RepeatMasker classes become Unknown."""
    c = (rep_class or "").upper().strip()
    f = (rep_family or "").upper()
    n = (rep_name or "").upper()
    text = f"{c} {f} {n}"
    if not c or "?" in c or "UNKNOWN" in text or c in {"RC", "RETROPOSON"}:
        return 5
    if "SINE" in c:
        return 1
    if "LINE" in c:
        return 2
    if "LTR" in c:
        return 3
    if c == "DNA" or c.startswith("DNA/"):
        return 4
    return 5


def load_sf5_intervals(bed: str):
    vals = collections.defaultdict(list)
    with opener(bed) as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip().split("\t")
            if len(parts) < 3:
                continue
            try:
                chrom, start, end = parts[0], int(parts[1]), int(parts[2])
            except ValueError:
                continue
            name = parts[3] if len(parts) > 3 else ""
            rep_class = parts[6] if len(parts) > 6 else ""
            rep_family = parts[7] if len(parts) > 7 else ""
            cls = map_sf5(rep_class, rep_family, name)
            vals[chrom].append((start, end, cls))
    packed = {}
    for chrom, items in vals.items():
        items.sort()
        packed[chrom] = (items, [x[1] for x in items])
    return packed


def eligible(manifest: str, split: str, species: list[str]) -> list[dict]:
    want = set(species)
    rows = []
    for row in read_manifest(manifest):
        if row.get("split") != split:
            continue
        if want and row.get("species_code") not in want:
            continue
        if not row.get("genome") or not Path(row["genome"]).exists():
            continue
        if not row.get("comparator_strict") or not Path(row["comparator_strict"]).exists():
            continue
        rows.append(row)
    return rows


def write_records(path: Path, rows: list[dict], split_name: str, window: int, step: int,
                  max_n_frac: float, max_per_species: int) -> dict:
    counts = collections.Counter()
    per_species = {}
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as out:
        for row in rows:
            chroms = choose_eval_chroms(row, window, 3)
            chrom = chroms[0] if split_name == "train" else chroms[1] if split_name == "val" and len(chroms) > 1 else chroms[-1]
            intervals = load_sf5_intervals(row["comparator_strict"])
            n = 0
            for rec in iter_windows(row["genome"], intervals, {chrom}, window, step, max_n_frac, max_per_species):
                rec["species_code"] = row["species_code"]
                out.write(json.dumps(rec) + "\n")
                counts.update(rec["labels"])
                n += 1
            per_species[row["species_code"]] = {"chrom": chrom, "windows": n}
    return {
        "class_bp": {SF5.get(k, ID2LABEL.get(k, str(k))): int(v) for k, v in sorted(counts.items())},
        "per_species": per_species,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--species", nargs="+", required=True)
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--step", type=int, default=4096)
    ap.add_argument("--max-n-frac", type=float, default=0.2)
    ap.add_argument("--max-train-per-species", type=int, default=900)
    ap.add_argument("--max-val-per-species", type=int, default=240)
    ap.add_argument("--max-test-per-species", type=int, default=360)
    args = ap.parse_args()

    rows = eligible(args.manifest, "fine_tune", args.species)
    if not rows:
        raise SystemExit("no eligible fine_tune rows")
    out = Path(args.out_dir)
    meta = {"window": args.window, "step": args.step, "species": [r["species_code"] for r in rows], "splits": {}}
    meta["splits"]["train"] = write_records(out / "train/data.jsonl.gz", rows, "train", args.window, args.step, args.max_n_frac, args.max_train_per_species)
    meta["splits"]["val"] = write_records(out / "val/data.jsonl.gz", rows, "val", args.window, args.step, args.max_n_frac, args.max_val_per_species)
    meta["splits"]["test"] = write_records(out / "test/data.jsonl.gz", rows, "test", args.window, args.step, args.max_n_frac, args.max_test_per_species)
    out.mkdir(parents=True, exist_ok=True)
    (out / "label_map.json").write_text(json.dumps({str(k): v for k, v in SF5.items()}, indent=2) + "\n")
    (out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
