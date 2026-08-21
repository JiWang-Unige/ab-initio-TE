#!/usr/bin/env python3
"""Build GENERanno single-nt superfamily JSONL windows from UCSC TE BEDs."""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import json
from pathlib import Path

TEFINAL_SPLIT = {
    "train": ["chr1", "chr3", "chr5", "chr7", "chr9"],
    "val": ["chr11", "chr13", "chr15"],
    "test": ["chr17", "chr19", "chr20", "chr21", "chr22"],
}

ID2LABEL = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Other"}


def opener(path: str):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path, "rt")


def read_manifest(path: str) -> list[dict]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def map_class(rep_class: str, rep_family: str = "", rep_name: str = "") -> int:
    c = (rep_class or "").upper()
    f = (rep_family or "").upper()
    n = (rep_name or "").upper()
    text = f"{c} {f} {n}"
    if "SINE" in c:
        return 1
    if "LINE" in c:
        return 2
    if "LTR" in c or "GYPSY" in text or "COPIA" in text or "ERV" in text or "RETROPOSON" in c:
        return 3
    if (
        "DNA" in c or c == "RC" or "HELITRON" in text or "TIR" in text or "HAT" in text
        or "MULE" in text or "MARINER" in text or "CACTA" in text or "MITE" in text
        or "TCMAR" in text or "PIF" in text or "HARBINGER" in text
    ):
        return 4
    return 5


def load_class_intervals(bed: str):
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
            cls = map_class(rep_class, rep_family, name)
            vals[chrom].append((start, end, cls))
    packed = {}
    for chrom, rows in vals.items():
        rows.sort()
        packed[chrom] = (rows, [x[1] for x in rows])
    return packed


def paint(labels: list[int], chrom: str, start: int, end: int, intervals) -> None:
    item = intervals.get(chrom)
    if not item:
        return
    vals, ends = item
    idx = max(0, bisect.bisect_left(ends, start) - 1)
    for te_start, te_end, cls in vals[idx:]:
        if te_start >= end:
            break
        left = max(te_start, start) - start
        right = min(te_end, end) - start
        if right > left:
            labels[left:right] = [cls] * (right - left)


def iter_windows(fasta: str, intervals, chroms: set[str], window: int, step: int,
                 max_n_frac: float, max_windows: int | None = None):
    emitted = 0
    cur = None
    buf = ""
    buf_start = 0

    def emit(chrom: str):
        nonlocal emitted, buf, buf_start
        while len(buf) >= window:
            if max_windows is not None and emitted >= max_windows:
                return
            seq = buf[:window]
            start = buf_start
            if seq.count("N") / max(1, window) <= max_n_frac:
                labels = [0] * window
                paint(labels, chrom, start, start + window, intervals)
                emitted += 1
                yield {"sequence": seq, "labels": labels, "chr": chrom, "start": start, "end": start + window}
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
                yield from emit(cur)
                if max_windows is not None and emitted >= max_windows:
                    break


def write_split(path: Path, fasta: str, bed: str, chroms: list[str], window: int,
                step: int, max_n_frac: float, max_windows: int | None) -> dict:
    intervals = load_class_intervals(bed)
    counts = collections.Counter()
    n = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as out:
        for rec in iter_windows(fasta, intervals, set(chroms), window, step, max_n_frac, max_windows):
            out.write(json.dumps(rec) + "\n")
            n += 1
            counts.update(rec["labels"])
    return {"windows": n, "class_bp": {ID2LABEL[k]: int(v) for k, v in sorted(counts.items())}, "chroms": chroms}


def command_human(args) -> None:
    rows = [r for r in read_manifest(args.manifest) if r.get("species_code") == args.species and r.get("split") == "fine_tune"]
    if not rows:
        raise SystemExit(f"missing fine_tune row for {args.species}")
    row = rows[0]
    out = Path(args.out_dir)
    meta = {"mode": "human_superfamily", "species": args.species, "window": args.window, "step": args.step, "splits": {}}
    for split, chroms in TEFINAL_SPLIT.items():
        meta["splits"][split] = write_split(
            out / split / "data.jsonl.gz", row["genome"], row["comparator_strict"],
            chroms, args.window, args.step, args.max_n_frac, args.max_windows_per_split,
        )
    out.mkdir(parents=True, exist_ok=True)
    (out / "label_map.json").write_text(json.dumps({str(k): v for k, v in ID2LABEL.items()}, indent=2) + "\n")
    (out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("human")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--species", default="human")
    p.add_argument("--window", type=int, required=True)
    p.add_argument("--step", type=int)
    p.add_argument("--max-n-frac", type=float, default=0.2)
    p.add_argument("--max-windows-per-split", type=int, default=3000)
    args = ap.parse_args()
    if args.step is None:
        args.step = args.window
    if args.cmd == "human":
        command_human(args)


if __name__ == "__main__":
    main()
