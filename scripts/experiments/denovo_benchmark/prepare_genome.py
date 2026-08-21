#!/usr/bin/env python3
"""Materialize an uncompressed FASTA for de novo TE benchmark tools."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
from pathlib import Path


def open_input(path: Path):
    with path.open("rb") as raw:
        magic = raw.read(2)
    if magic == b"\x1f\x8b" or path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def fasta_stats(path: Path) -> dict[str, int]:
    seqs = 0
    bp = 0
    with path.open("rt") as handle:
        for line in handle:
            if line.startswith(">"):
                seqs += 1
            else:
                bp += len(line.strip())
    return {"seqs": seqs, "bp": bp}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--stats", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    stats_path = Path(args.stats).resolve()
    done_path = output.with_suffix(output.suffix + ".done")

    if done_path.exists() and output.exists() and output.stat().st_size > 0 and not args.force:
        stats = fasta_stats(output)
        stats.update({"species": args.species, "source": str(source), "output": str(output), "skipped": True})
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
        return 0

    if not source.exists():
        raise SystemExit(f"source FASTA does not exist: {source}")

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    with open_input(source) as src, tmp.open("wt") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    tmp.replace(output)

    stats = fasta_stats(output)
    if stats["seqs"] == 0 or stats["bp"] == 0:
        raise SystemExit(f"invalid FASTA after materialization: {output}")

    stats.update({"species": args.species, "source": str(source), "output": str(output), "skipped": False})
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    done_path.write_text("OK\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
