#!/usr/bin/env python3
"""Materialize frozen 8192/8192 FASTA windows for P3-X inference.

The P3-R1 evaluator consumes comparator JSONL rows and suppresses predictions
where ``labels`` are negative.  This input is therefore deliberately labelled
all-zero: it is an inference-only adapter, not truth and never a training
input.  The resulting dummy truth/metrics files must not be used for claims.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Iterator


WINDOW = 8192
STRIDE = 8192


def _open_text(path: Path):
    opener = gzip.open if str(path).endswith(".gz") else open
    return opener(path, "rt", encoding="ascii", errors="strict")


def iter_fasta(path: Path) -> Iterator[tuple[str, str]]:
    """Yield one upper-case FASTA record at a time, including gzip input."""
    name: str | None = None
    chunks: list[str] = []
    with _open_text(path) as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    sequence = "".join(chunks).upper()
                    if not sequence:
                        raise ValueError(f"empty FASTA sequence for {name!r}")
                    yield name, sequence
                name = line[1:].split()[0]
                if not name:
                    raise ValueError(f"empty FASTA name at line {line_no}")
                chunks = []
            elif name is None:
                raise ValueError(f"FASTA sequence precedes header at line {line_no}")
            else:
                chunks.append(line)
        if name is not None:
            sequence = "".join(chunks).upper()
            if not sequence:
                raise ValueError(f"empty FASTA sequence for {name!r}")
            yield name, sequence


def iter_inference_rows(path: Path) -> Iterator[dict[str, object]]:
    """Yield contiguous frozen windows with all-zero inference-only labels."""
    seen: set[str] = set()
    for seqid, sequence in iter_fasta(path):
        if seqid in seen:
            raise ValueError(f"duplicate FASTA contig: {seqid}")
        seen.add(seqid)
        for start in range(0, len(sequence), STRIDE):
            end = min(start + WINDOW, len(sequence))
            piece = sequence[start:end]
            yield {
                "chr": seqid,
                "start": start,
                "end": end,
                "sequence": piece,
                "labels": [0] * len(piece),
            }


def write_inference_jsonl(assembly: Path, output_jsonl: Path, manifest: Path) -> dict[str, object]:
    """Write rows and a coverage manifest without reading any truth asset."""
    if output_jsonl.exists():
        raise FileExistsError(f"refusing to overwrite inference input: {output_jsonl}")
    if manifest.exists():
        raise FileExistsError(f"refusing to overwrite inference manifest: {manifest}")

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    contigs = 0
    total_bp = 0
    windows = 0
    tail_windows = 0
    with gzip.open(output_jsonl, "wt", encoding="utf-8", newline="\n") as handle:
        for row in iter_inference_rows(assembly):
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
            contigs += 1 if row["start"] == 0 else 0
            total_bp += int(row["end"]) - int(row["start"])
            windows += 1
            if int(row["end"]) - int(row["start"]) < WINDOW:
                tail_windows += 1

    result: dict[str, object] = {
        "schema": "p3_x_inference_jsonl_v1",
        "status": "PASS",
        "assembly": str(assembly),
        "output_jsonl": str(output_jsonl),
        "window": WINDOW,
        "stride": STRIDE,
        "contigs": contigs,
        "total_bp": total_bp,
        "windows": windows,
        "tail_windows": tail_windows,
        "coverage_complete": True,
        "label_mode": "all_zero_dummy_for_p3_r1_evaluator_only",
        "truth_read": False,
        "claim_scope": "inference input only; do not use dummy truth or metrics",
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument("--stride", type=int, default=STRIDE)
    args = parser.parse_args()
    if args.window != WINDOW or args.stride != STRIDE:
        raise ValueError("P3-X frozen input requires --window 8192 --stride 8192")
    result = write_inference_jsonl(args.assembly, args.output_jsonl, args.manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
