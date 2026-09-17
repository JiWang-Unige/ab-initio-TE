"""Command line entry point for portable D FASTA inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from .bundle import Bundle
from .fasta import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate TE-material probability BEDGraph, material BED and softmasked FASTA."
    )
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--fasta", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument(
        "--cpu-threads",
        type=int,
        default=0,
        help="torch CPU threads; zero keeps the environment default",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    bundle = Bundle.load(args.bundle_root)
    summary = run(
        bundle,
        args.fasta,
        args.output_dir,
        device=args.device,
        batch_size=args.batch_size,
        cpu_threads=args.cpu_threads,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0
