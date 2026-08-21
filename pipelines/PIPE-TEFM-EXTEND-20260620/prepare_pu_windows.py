#!/usr/bin/env python3
"""Prepare positive-window PU JSONL datasets for low-confidence TE labels.

Labels are bp-level:
  1  = annotated TE positive
 -1  = unlabeled/unknown, ignored by positive loss and optionally penalized as U

This intentionally avoids treating unannotated plant/stress sequence as a
reliable negative during training. Evaluation datasets should still be built by
the standard binary window preparer so F1 is computed against a fixed reference.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import json
import random
import sys
from pathlib import Path

SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
sys.path.insert(0, str(SUPP))
from prepare_ucsc_windows import choose_eval_chroms, opener, read_manifest  # noqa: E402


def load_intervals(bed: str) -> dict[str, tuple[list[tuple[int, int]], list[int]]]:
    vals: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    with opener(bed) as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip().split("\t")
            if len(parts) < 3:
                continue
            try:
                vals[parts[0]].append((int(parts[1]), int(parts[2])))
            except ValueError:
                continue
    packed = {}
    for chrom, items in vals.items():
        items = sorted(items)
        packed[chrom] = (items, [end for _, end in items])
    return packed


def read_fasta_chrom(path: str, chrom: str) -> str:
    parts = []
    found = False
    with opener(path) as handle:
        for raw in handle:
            line = raw.rstrip()
            if line.startswith(">"):
                if found:
                    break
                found = line[1:].split()[0] == chrom
            elif found:
                parts.append(line.upper())
    if not parts:
        raise RuntimeError(f"chromosome {chrom} not found in {path}")
    return "".join(parts)


def paint_positive(labels: list[int], chrom: str, start: int, end: int, intervals) -> int:
    item = intervals.get(chrom)
    if not item:
        return 0
    vals, ends = item
    idx = max(0, bisect.bisect_left(ends, start) - 1)
    painted = 0
    for te_start, te_end in vals[idx:]:
        if te_start >= end:
            break
        left = max(te_start, start) - start
        right = min(te_end, end) - start
        if right > left:
            for i in range(left, right):
                if labels[i] != 1:
                    painted += 1
                labels[i] = 1
    return painted


def eligible_rows(manifest: str, split: str, species: list[str] | None) -> list[dict]:
    want = set(species or [])
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


def candidate_starts(te_start: int, te_end: int, chrom_len: int, window: int, rng: random.Random) -> list[int]:
    length = te_end - te_start
    starts = []
    if length <= window:
        starts.append((te_start + te_end) // 2 - window // 2)
        starts.append(te_start - window // 4)
        starts.append(te_end - (3 * window) // 4)
    else:
        # Dynamic long-TE sampling: cover internal regions and both boundaries,
        # avoiding a fixed center-only view.
        qs = [0.12, 0.30, 0.50, 0.70, 0.88]
        for q in qs:
            center = int(te_start + q * length)
            starts.append(center - window // 2)
        starts.extend([te_start - window // 4, te_end - (3 * window) // 4])
        for _ in range(2):
            starts.append(rng.randint(te_start, max(te_start, te_end - window)))
    return [max(0, min(s, max(0, chrom_len - window))) for s in starts]


def iter_positive_windows(row: dict, chrom: str, window: int, max_n_frac: float,
                          max_windows: int, seed: int):
    rng = random.Random(seed)
    seq = read_fasta_chrom(row["genome"], chrom)
    intervals = load_intervals(row["comparator_strict"])
    chrom_intervals = intervals.get(chrom, ([], []))[0]
    starts = []
    for te_start, te_end in chrom_intervals:
        if te_end <= te_start:
            continue
        starts.extend(candidate_starts(te_start, te_end, len(seq), window, rng))
    starts = list(dict.fromkeys(starts))
    rng.shuffle(starts)
    emitted = 0
    for start in starts:
        if emitted >= max_windows:
            break
        piece = seq[start:start + window]
        if len(piece) != window or piece.count("N") / max(1, len(piece)) > max_n_frac:
            continue
        labels = [-1] * window
        pos_bp = paint_positive(labels, chrom, start, start + window, intervals)
        if pos_bp <= 0:
            continue
        emitted += 1
        yield {
            "sequence": piece,
            "labels": labels,
            "chr": chrom,
            "start": start,
            "end": start + window,
            "species_code": row["species_code"],
            "pos_bp": pos_bp,
        }


def write_mixed(path: Path, rows: list[dict], proportions: dict[str, float], split_name: str,
                window: int, max_n_frac: float, total_windows: int, seed: int) -> dict:
    by_species = {row["species_code"]: row for row in rows}
    stats = {}
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as out:
        for species, prop in proportions.items():
            row = by_species.get(species)
            if row is None:
                continue
            chroms = choose_eval_chroms(row, window, 3)
            chrom = chroms[0] if split_name == "train" else chroms[min(1, len(chroms) - 1)]
            quota = max(1, int(total_windows * float(prop)))
            n = pos = unknown = 0
            for rec in iter_positive_windows(row, chrom, window, max_n_frac, quota, seed + len(stats) * 17):
                out.write(json.dumps(rec) + "\n")
                n += 1
                pos += rec["pos_bp"]
                unknown += window - rec["pos_bp"]
            stats[species] = {"chrom": chrom, "quota": quota, "windows": n, "positive_bp": pos, "unknown_bp": unknown}
    return stats


def normalize_props(rows: list[dict], requested: dict[str, float] | None) -> dict[str, float]:
    species = [r["species_code"] for r in rows]
    if requested:
        vals = {s: float(requested[s]) for s in species if s in requested}
    else:
        vals = {s: 1.0 for s in species}
    total = sum(vals.values())
    if total <= 0:
        raise SystemExit("no positive species weights")
    return {s: v / total for s, v in vals.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--species", nargs="*")
    ap.add_argument("--proportions-json")
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--max-n-frac", type=float, default=0.2)
    ap.add_argument("--train-windows", type=int, default=5400)
    ap.add_argument("--val-windows", type=int, default=900)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = eligible_rows(args.manifest, "fine_tune", args.species)
    if not rows:
        raise SystemExit("no eligible fine_tune rows with comparator_strict")
    requested = json.loads(args.proportions_json) if args.proportions_json else None
    props = normalize_props(rows, requested)
    out = Path(args.out_dir)
    meta = {
        "mode": "positive_only_pu",
        "window": args.window,
        "proportions": props,
        "splits": {},
        "note": "Training labels use 1 for TE positives and -1 for unlabeled bases; no background windows are sampled.",
    }
    meta["splits"]["train"] = write_mixed(out / "train/data.jsonl.gz", rows, props, "train", args.window, args.max_n_frac, args.train_windows, args.seed)
    meta["splits"]["val"] = write_mixed(out / "val/data.jsonl.gz", rows, props, "val", args.window, args.max_n_frac, args.val_windows, args.seed + 1000)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
