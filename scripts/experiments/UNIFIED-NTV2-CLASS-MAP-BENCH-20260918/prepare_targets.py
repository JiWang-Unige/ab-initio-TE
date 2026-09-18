#!/usr/bin/env python3
"""Extract the fixed chr10/chr20 targets without reading labels or scores."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "configs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918.json"
ALLOWED = set("ACGTRYSWKMBDHVN")


def read_target_records(path: Path, targets: set[str]):
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    name = None
    chunks: list[str] = []
    seen: set[str] = set()
    emitted: dict[str, str] = {}
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None and name in targets:
                    emitted[name] = "".join(chunks)
                fields = line[1:].split()
                if not fields:
                    raise ValueError(f"empty FASTA header at {path}:{line_no}")
                name = fields[0]
                if name in seen:
                    raise ValueError(f"duplicate FASTA contig {name}")
                seen.add(name)
                chunks = []
            else:
                if name is None:
                    raise ValueError(f"sequence before FASTA header at {path}:{line_no}")
                seq = line.upper()
                invalid = set(seq) - ALLOWED
                if invalid:
                    raise ValueError(f"unsupported FASTA symbols at {path}:{line_no}: {sorted(invalid)}")
                if name in targets:
                    chunks.append(seq)
        if name is not None and name in targets:
            emitted[name] = "".join(chunks)
    missing = sorted(targets - set(emitted))
    if missing:
        raise FileNotFoundError(f"target chromosomes missing from {path}: {missing}")
    if any(not emitted[name] for name in targets):
        raise ValueError("target chromosome has no sequence")
    return emitted


def run(args: argparse.Namespace) -> dict:
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    if args.species not in config["species"]:
        raise ValueError(f"unsupported species {args.species}")
    species_cfg = config["species"][args.species]
    source = (ROOT / species_cfg["source_fasta"]).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    targets = list(species_cfg["target_chromosomes"])
    records = read_target_records(source, set(targets))
    out_dir = (ROOT / "outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/prepared").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    fasta_path = out_dir / f"{args.species}.fa"
    manifest_path = out_dir / f"{args.species}.manifest.json"
    if fasta_path.exists() or manifest_path.exists():
        raise FileExistsError(f"refusing to replace prepared target: {fasta_path}")
    with fasta_path.open("w", encoding="ascii") as handle:
        for name in targets:
            sequence = records[name]
            handle.write(f">{name}\n")
            for start in range(0, len(sequence), 80):
                handle.write(sequence[start : start + 80] + "\n")
    result = {
        "protocol": "UNIFIED-NTV2-CLASS-MAP-BENCH-20260918",
        "status": "COMPLETED",
        "species": args.species,
        "assembly": species_cfg["assembly"],
        "source_fasta": str(source),
        "target_chromosomes": targets,
        "selection": "fixed chr10/chr20 from D exposure audit; no label, score, or native output used",
        "coordinate_convention": "0-based half-open for downstream maps",
        "records": {name: {"length_bp": len(records[name]), "acgt_bp": sum(base in "ACGT" for base in records[name]), "non_acgt_bp": sum(base not in "ACGT" for base in records[name])} for name in targets},
        "total_bp": sum(len(records[name]) for name in targets),
        "fasta": str(fasta_path),
        "manifest": str(manifest_path),
    }
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--species", choices=("chicken", "zebrafish"), required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
