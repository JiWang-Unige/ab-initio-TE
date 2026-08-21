#!/usr/bin/env python3
"""Prebuild RepeatMasker Dfam species libraries in a run-scoped overlay."""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

csv.field_size_limit(sys.maxsize)

INDEX_SUFFIXES = {
    ".ndb",
    ".nhr",
    ".nin",
    ".njs",
    ".not",
    ".nsq",
    ".ntf",
    ".nto",
}
EXCLUDE_NAMES = {"refineableHash.dat", "rmblastdb.log", "speciesMeta.pm"}


def species_dir_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name.strip().lower()).strip("_")


def count_fasta_records(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open(errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                count += 1
    return count


def library_component_candidates(species_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in sorted(species_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name in EXCLUDE_NAMES:
            continue
        if path.suffix in INDEX_SUFFIXES:
            continue
        candidates.append(path)
    return candidates


def resolve_species_inputs(overlay: Path, rm_species: str) -> tuple[str, list[Path]]:
    safe = species_dir_name(rm_species)
    search_dirs = [
        overlay / "CONS-Dfam_3.9" / safe,
        overlay / "CONS-Dfam_3.9" / f"{safe}.working",
    ]
    for species_dir in search_dirs:
        if not species_dir.exists():
            continue
        specieslib = species_dir / "specieslib"
        if specieslib.exists():
            return "single_specieslib", [specieslib]
        candidates = library_component_candidates(species_dir)
        if candidates:
            return "split_component_libs", candidates
    return "missing", []


def run_one(row: dict[str, str], args: argparse.Namespace) -> dict[str, str]:
    code = row["species_code"]
    rm_species = row["repeatmasker_species"]
    safe = species_dir_name(rm_species)
    out_dir = Path(args.probe_root) / code
    out_dir.mkdir(parents=True, exist_ok=True)
    probe = out_dir / f"{code}.probe.fa"
    probe.write_text(f">{code}_probe\n" + ("ACGT" * 2500) + "\n")
    log = out_dir / "repeatmasker_probe.log"
    env = os.environ.copy()
    env["LIBDIR"] = str(Path(args.overlay).resolve())
    cmd = [
        args.repeatmasker,
        "-pa",
        "1",
        "-xsmall",
        "-gff",
        "-dir",
        str(out_dir),
        "-species",
        rm_species,
        str(probe),
    ]
    with log.open("w") as handle:
        proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, env=env)
    mode, inputs = resolve_species_inputs(Path(args.overlay), rm_species)
    specieslib = Path(args.overlay) / "CONS-Dfam_3.9" / safe / "specieslib"
    seq_count = sum(count_fasta_records(path) for path in inputs)
    size = sum(path.stat().st_size for path in inputs if path.exists())
    status = "OK"
    if proc.returncode != 0:
        status = "REPEATMASKER_FAILED"
    elif size < args.min_bytes or seq_count < args.min_records:
        status = "SPECIESLIB_TOO_SMALL"
    return {
        "species_code": code,
        "repeatmasker_species": rm_species,
        "specieslib_dir": safe,
        "specieslib": str(specieslib),
        "specieslib_mode": mode,
        "specieslib_input_count": str(len(inputs)),
        "specieslib_bytes": str(size),
        "specieslib_records": str(seq_count),
        "status": status,
        "probe_log": str(log),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species-table", required=True)
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--probe-root", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--repeatmasker", default="/home/users/j/jwang/.conda/envs/te_benchmark/bin/RepeatMasker")
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--min-bytes", type=int, default=20_000)
    parser.add_argument("--min-records", type=int, default=50)
    args = parser.parse_args()

    with Path(args.species_table).open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise SystemExit("empty species table")

    results: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = [pool.submit(run_one, row, args) for row in rows]
        for future in as_completed(futures):
            result = future.result()
            print(f"{result['species_code']}\t{result['status']}\t{result['specieslib_records']}")
            results.append(result)

    fields = [
        "species_code",
        "repeatmasker_species",
        "specieslib_dir",
        "specieslib",
        "specieslib_mode",
        "specieslib_input_count",
        "specieslib_bytes",
        "specieslib_records",
        "status",
        "probe_log",
    ]
    out = Path(args.summary_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda row: row["species_code"]))

    bad = [row for row in results if row["status"] == "REPEATMASKER_FAILED"]
    if bad:
        preview = ", ".join(f"{row['species_code']}:{row['status']}" for row in bad[:20])
        raise SystemExit(f"specieslib prebuild failed: {preview}")


if __name__ == "__main__":
    main()
