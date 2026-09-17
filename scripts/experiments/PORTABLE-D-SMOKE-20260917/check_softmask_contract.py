#!/usr/bin/env python3
"""Check the canonical-base-only softmask contract on an existing output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_fasta(path: Path, uppercase: bool = True):
    name = None
    parts = []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            if name is not None:
                yield name, "".join(parts)
            name = line[1:].split()[0]
            parts = []
        elif line:
            sequence = line.strip()
            parts.append(sequence.upper() if uppercase else sequence)
    if name is not None:
        yield name, "".join(parts)


def read_mask(path: Path, lengths: dict[str, int]):
    masks = {name: [False] * length for name, length in lengths.items()}
    for line in path.read_text().splitlines():
        name, left, right = line.split("\t")
        for index in range(int(left), int(right)):
            masks[name][index] = True
    return masks


def run(args: argparse.Namespace) -> dict:
    records = list(read_fasta(args.fasta))
    lengths = {name: len(sequence) for name, sequence in records}
    masks = read_mask(args.material_bed, lengths)
    observed = dict(read_fasta(args.softmasked_fasta, uppercase=False))
    mismatches = []
    for name, sequence in records:
        expected = "".join(
            base.lower() if flag and base in "ACGT" else base
            for base, flag in zip(sequence, masks[name])
        )
        if observed.get(name) != expected:
            mismatches.append(name)
    result = {
        "status": "PASS" if not mismatches else "FAIL",
        "protocol": "PORTABLE-D-SOFTMASK-CONTRACT-20260917",
        "canonical_positive_bases_lowercase_only": True,
        "iupac_and_n_preserved_uppercase": True,
        "contigs": len(records),
        "mismatched_contigs": mismatches,
        "source_material_bed": str(args.material_bed.resolve()),
        "source_softmasked_fasta": str(args.softmasked_fasta.resolve()),
    }
    if args.output_json:
        args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fasta", type=Path, required=True)
    parser.add_argument("--material-bed", type=Path, required=True)
    parser.add_argument("--softmasked-fasta", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    return parser


if __name__ == "__main__":
    print(json.dumps(run(build_parser().parse_args()), indent=2, sort_keys=True))
