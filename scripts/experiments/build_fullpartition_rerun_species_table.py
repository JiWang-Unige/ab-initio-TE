#!/usr/bin/env python3
"""Build the species table for the full-Dfam-partition RepeatMasker rerun."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)


def project_relative(root: Path, path_text: str) -> str:
    path = Path(path_text)
    if str(path).startswith("/home/users/j/jwang/ab-initio-TE/"):
        path = root / str(path).removeprefix("/home/users/j/jwang/ab-initio-TE/")
    if path.is_absolute():
        try:
            return str(path.resolve().relative_to(root))
        except ValueError:
            return str(path)
    return str(path)


def load_metadata(manifests: list[Path]) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    for manifest in manifests:
        with manifest.open(newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                code = row["species_code"]
                metadata.setdefault(
                    code,
                    {
                        "scientific_name": row["scientific_name"],
                        "repeatmasker_species": row["repeatmasker_species"],
                        "taxid": row["taxid"],
                        "priority": row["priority"],
                    },
                )
    return metadata


def infer_priority(kingdom: str, role: str) -> str:
    if kingdom == "plant":
        return f"fullpartition_plant_{role}"
    return f"fullpartition_animal_{role}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--prior-species-manifest", action="append", default=[])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    split_manifest = root / args.split_manifest
    prior_manifests = [root / path for path in args.prior_species_manifest]
    metadata = load_metadata(prior_manifests)

    by_code: dict[str, dict[str, str]] = {}
    with split_manifest.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            code = row["species_code"]
            genome = row["genome"]
            entry = by_code.setdefault(
                code,
                {
                    "species_code": code,
                    "kingdom": row["kingdom"],
                    "roles": set(),
                    "fasta": genome,
                },
            )
            entry["roles"].add(row["role"])
            if entry["fasta"] != genome:
                raise SystemExit(f"{code}: multiple genome paths in split manifest")

    missing = sorted(code for code in by_code if code not in metadata)
    if missing:
        raise SystemExit(f"Missing species metadata for: {', '.join(missing)}")

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "species_code",
        "scientific_name",
        "repeatmasker_species",
        "fasta",
        "taxid",
        "priority",
        "existing_complete",
    ]
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for code in sorted(by_code):
            entry = by_code[code]
            meta = metadata[code]
            roles = ",".join(sorted(entry["roles"]))
            priority = infer_priority(entry["kingdom"], roles)
            writer.writerow(
                {
                    "species_code": code,
                    "scientific_name": meta["scientific_name"],
                    "repeatmasker_species": meta["repeatmasker_species"],
                    "fasta": project_relative(root, entry["fasta"]),
                    "taxid": meta["taxid"],
                    "priority": priority,
                    "existing_complete": "",
                }
            )


if __name__ == "__main__":
    main()
