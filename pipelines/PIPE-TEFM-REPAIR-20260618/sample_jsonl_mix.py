#!/usr/bin/env python3
"""Deterministically sample and merge JSONL.GZ window pools."""
from __future__ import annotations

import argparse
import gzip
import json
import random
from pathlib import Path


def read_jsonl_gz(path: str) -> list[dict]:
    rows = []
    with gzip.open(path, "rt") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources-json", required=True,
                    help="JSON list of {path, quota, species_code}.")
    ap.add_argument("--out-jsonl", required=True)
    ap.add_argument("--out-meta", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    sources = json.loads(args.sources_json)
    out_rows = []
    meta = {"seed": args.seed, "sources": [], "n": 0}
    for src in sources:
        rows = read_jsonl_gz(src["path"])
        rng.shuffle(rows)
        quota = int(src["quota"])
        take = rows[:quota]
        for row in take:
            if src.get("species_code"):
                row["species_code"] = src["species_code"]
        out_rows.extend(take)
        meta["sources"].append({
            "path": src["path"],
            "species_code": src.get("species_code", ""),
            "available": len(rows),
            "quota": quota,
            "taken": len(take),
        })
    rng.shuffle(out_rows)
    write_jsonl_gz(Path(args.out_jsonl), out_rows)
    meta["n"] = len(out_rows)
    Path(args.out_meta).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_meta).write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
