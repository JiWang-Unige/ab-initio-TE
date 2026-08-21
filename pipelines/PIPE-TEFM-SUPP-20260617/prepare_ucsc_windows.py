#!/usr/bin/env python3
"""Build UCSC strict-TE binary JSONL windows from ready-by-design manifests."""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import json
import random
from pathlib import Path

TEFINAL_SPLIT = {
    "train": ["chr1", "chr3", "chr5", "chr7", "chr9"],
    "val": ["chr11", "chr13", "chr15"],
    "test": ["chr17", "chr19", "chr20", "chr21", "chr22"],
}


def opener(path: str):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path, "rt")


def read_manifest(path: str) -> list[dict]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_intervals(bed: str) -> dict[str, tuple[list[tuple[int, int]], list[int]]]:
    intervals: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    with opener(bed) as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip().split("\t")
            if len(parts) < 3:
                continue
            try:
                intervals[parts[0]].append((int(parts[1]), int(parts[2])))
            except ValueError:
                continue
    packed = {}
    for chrom, vals in intervals.items():
        vals = sorted(vals)
        packed[chrom] = (vals, [end for _, end in vals])
    return packed


def bed_chroms(bed: str) -> set[str]:
    return set(load_intervals(bed))


def fasta_lengths(fasta: str) -> dict[str, int]:
    lengths: dict[str, int] = {}
    cur = None
    n = 0
    with opener(fasta) as handle:
        for raw in handle:
            line = raw.rstrip()
            if line.startswith(">"):
                if cur is not None:
                    lengths[cur] = n
                cur = line[1:].split()[0]
                n = 0
            elif cur is not None:
                n += len(line.strip())
        if cur is not None:
            lengths[cur] = n
    return lengths


def paint(labels: list[int], chrom: str, start: int, end: int, intervals, value: int) -> None:
    item = intervals.get(chrom)
    if not item:
        return
    vals, ends = item
    idx = max(0, bisect.bisect_left(ends, start) - 1)
    for te_start, te_end in vals[idx:]:
        if te_start >= end:
            break
        left = max(te_start, start) - start
        right = min(te_end, end) - start
        if right > left:
            labels[left:right] = [value] * (right - left)


def iter_windows(fasta: str, intervals, chroms: set[str], window: int, step: int,
                 max_n_frac: float, max_windows: int | None = None,
                 unknown_intervals=None):
    emitted = 0
    cur = None
    buf = ""
    buf_start = 0

    def emit_available(chrom: str):
        nonlocal emitted
        nonlocal buf, buf_start
        while len(buf) >= window:
            if max_windows is not None and emitted >= max_windows:
                return
            piece = buf[:window]
            start = buf_start
            if piece.count("N") / max(1, window) > max_n_frac:
                buf = buf[step:]
                buf_start += step
                continue
            labels = [0] * window
            if unknown_intervals is not None:
                paint(labels, chrom, start, start + window, unknown_intervals, -100)
            paint(labels, chrom, start, start + window, intervals, 1)
            emitted += 1
            yield {
                "sequence": piece,
                "labels": labels,
                "chr": chrom,
                "start": start,
                "end": start + window,
            }
            buf = buf[step:]
            buf_start += step

    with opener(fasta) as handle:
        for raw in handle:
            line = raw.rstrip()
            if line.startswith(">"):
                cur = line[1:].split()[0]
                buf = ""
                buf_start = 0
                if max_windows is not None and emitted >= max_windows:
                    break
            elif cur in chroms:
                buf += line.upper()
                yield from emit_available(cur)
                if max_windows is not None and emitted >= max_windows:
                    break


def write_split(out_path: Path, fasta: str, bed: str, chroms: list[str], window: int,
                step: int, max_n_frac: float, max_windows: int | None,
                unknown_bed: str | None = None) -> dict:
    intervals = load_intervals(bed)
    unknown_intervals = load_intervals(unknown_bed) if unknown_bed and Path(unknown_bed).exists() else None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = pos = neg = ign = 0
    with gzip.open(out_path, "wt") as out:
        for rec in iter_windows(fasta, intervals, set(chroms), window, step, max_n_frac, max_windows, unknown_intervals):
            out.write(json.dumps(rec) + "\n")
            n += 1
            pos += sum(1 for x in rec["labels"] if x == 1)
            neg += sum(1 for x in rec["labels"] if x == 0)
            ign += sum(1 for x in rec["labels"] if x == -100)
    return {"windows": n, "bp_pos": pos, "bp_neg": neg, "bp_ignore": ign, "chroms": chroms}


def choose_eval_chrom(row: dict, min_len: int, preferred: str | None = None) -> str:
    return choose_eval_chroms(row, min_len, 1, preferred)[0]


def choose_eval_chroms(row: dict, min_len: int, n: int, preferred: str | None = None) -> list[str]:
    lengths = fasta_lengths(row["genome"])
    valid = bed_chroms(row["comparator_strict"]) & set(lengths)
    if preferred and preferred in valid:
        return [preferred]
    excluded = ("chrM", "chrMT", "MT", "Mt", "M", "chrUn")
    candidates = [c for c in valid if not any(c.startswith(x) for x in excluded) and lengths[c] >= min_len]
    if not candidates:
        candidates = [c for c in valid if lengths[c] >= min_len]
    if not candidates:
        raise SystemExit(f"No eval chromosome with UCSC labels for {row['species_code']}")
    ordered = sorted(candidates, key=lambda c: lengths[c], reverse=True)
    return ordered[:max(1, min(n, len(ordered)))]


def eligible_rows(manifest: str, split: str, species: list[str] | None) -> list[dict]:
    rows = []
    want = set(species or [])
    for row in read_manifest(manifest):
        if row.get("split") != split:
            continue
        if want and row.get("species_code") not in want:
            continue
        if not row.get("comparator_strict") or not Path(row["comparator_strict"]).exists():
            continue
        if not row.get("genome") or not Path(row["genome"]).exists():
            continue
        rows.append(row)
    return rows


def build_human(args) -> None:
    rows = eligible_rows(args.manifest, "fine_tune", [args.species])
    if not rows:
        raise SystemExit(f"Missing fine_tune row for {args.species}")
    row = rows[0]
    meta = {"mode": "human_tefinal", "species": args.species, "window": args.window, "splits": {}}
    for split, chroms in TEFINAL_SPLIT.items():
        meta["splits"][split] = write_split(
            Path(args.out_dir) / split / "data.jsonl.gz",
            row["genome"], row["comparator_strict"], chroms,
            args.window, args.step, args.max_n_frac, args.max_windows_per_split,
            row.get("comparator_plus_unknown"),
        )
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    (Path(args.out_dir) / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")


def build_eval(args) -> None:
    rows = eligible_rows(args.manifest, args.split, args.species)
    out_root = Path(args.out_dir)
    summary = []
    for row in rows:
        chrom = choose_eval_chrom(row, args.window, args.chrom)
        species_dir = out_root / row["species_code"]
        stats = write_split(
            species_dir / "test" / "data.jsonl.gz",
            row["genome"], row["comparator_strict"], [chrom],
            args.window, args.step, args.max_n_frac, args.max_windows_per_species,
            row.get("comparator_plus_unknown"),
        )
        item = {"species_code": row["species_code"], "split": args.split, "chrom": chrom, **stats}
        summary.append(item)
        (species_dir / "metadata.json").write_text(json.dumps(item, indent=2) + "\n")
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "eval_manifest.json").write_text(json.dumps(summary, indent=2) + "\n")


def build_mixed(args) -> None:
    proportions = json.loads(args.proportions_json)
    rows = {r["species_code"]: r for r in eligible_rows(args.manifest, "fine_tune", list(proportions))}
    missing = sorted(set(proportions) - set(rows))
    if missing:
        raise SystemExit(f"Missing fine_tune rows with comparator_strict: {missing}")
    random.seed(args.seed)
    out = Path(args.out_dir)
    meta = {"mode": "mixed", "window": args.window, "proportions": proportions, "splits": {}}
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
                unknown_intervals = (
                    load_intervals(row["comparator_plus_unknown"])
                    if row.get("comparator_plus_unknown") and Path(row["comparator_plus_unknown"]).exists()
                    else None
                )
                for rec in iter_windows(row["genome"], intervals, {chrom}, args.window, args.step, args.max_n_frac, quota, unknown_intervals):
                    rec["species_code"] = species
                    tmp.append(rec)
                for rec in tmp:
                    handle.write(json.dumps(rec) + "\n")
                split_meta[species] = {"chrom": chrom, "windows": len(tmp), "quota": quota}
        meta["splits"][split_name] = split_meta
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--manifest", required=True)
    common.add_argument("--out-dir", required=True)
    common.add_argument("--window", type=int, required=True)
    common.add_argument("--step", type=int)
    common.add_argument("--max-n-frac", type=float, default=0.2)
    common.add_argument("--max-windows-per-split", type=int)
    common.add_argument("--max-windows-per-species", type=int)
    p = sub.add_parser("human", parents=[common])
    p.add_argument("--species", default="human")
    p = sub.add_parser("eval", parents=[common])
    p.add_argument("--split", choices=["fine_tune", "eval_only"], required=True)
    p.add_argument("--chrom")
    p.add_argument("--species", nargs="*")
    p = sub.add_parser("mixed", parents=[common])
    p.add_argument("--proportions-json", required=True)
    p.add_argument("--total-windows", type=int, required=True)
    p.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.step is None:
        args.step = args.window
    if args.cmd == "human":
        build_human(args)
    elif args.cmd == "eval":
        build_eval(args)
    elif args.cmd == "mixed":
        build_mixed(args)


if __name__ == "__main__":
    main()
