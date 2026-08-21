#!/usr/bin/env python3
"""Build the RepeatMasker+Dfam anchor species manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


ANCHORS = [
    {
        "species_code": "human",
        "scientific_name": "Homo sapiens",
        "repeatmasker_species": "Homo sapiens",
        "fasta": ".backup/data/genome_data/current_eukaryotes/animals/human/hs1.fa.gz",
        "legacy_backup": ".backup/data/genome_data/current_eukaryotes/animals/human/hs1.repeatMasker.out.gz",
        "priority": "core_anchor",
    },
    {
        "species_code": "mouse",
        "scientific_name": "Mus musculus",
        "repeatmasker_species": "Mus musculus",
        "fasta": ".backup/data/genome_data/current_eukaryotes/animals/mouse/mm39.fa",
        "legacy_backup": "",
        "priority": "core_anchor",
    },
    {
        "species_code": "chicken",
        "scientific_name": "Gallus gallus",
        "repeatmasker_species": "Gallus gallus",
        "fasta": ".backup/data/genome_data/current_eukaryotes/animals/chicken/galGal6.fa",
        "legacy_backup": "",
        "priority": "core_anchor",
    },
    {
        "species_code": "zebrafish",
        "scientific_name": "Danio rerio",
        "repeatmasker_species": "Danio rerio",
        "fasta": ".backup/data/genome_data/current_eukaryotes/animals/zebrafish/danRer11.fa",
        "legacy_backup": "",
        "priority": "core_anchor",
    },
    {
        "species_code": "fruit_fly",
        "scientific_name": "Drosophila melanogaster",
        "repeatmasker_species": "Drosophila melanogaster",
        "fasta": ".backup/data/genome_data/current_eukaryotes/animals/fruit_fly/dm6.fa",
        "legacy_backup": "",
        "priority": "core_anchor",
    },
    {
        "species_code": "c_elegans",
        "scientific_name": "Caenorhabditis elegans",
        "repeatmasker_species": "Caenorhabditis elegans",
        "fasta": ".backup/data/genome_data/current_eukaryotes/animals/c_elegans/ce11.fa",
        "legacy_backup": "",
        "priority": "core_anchor",
    },
]


FIELDNAMES = [
    "array_index",
    "species_code",
    "scientific_name",
    "repeatmasker_species",
    "fasta_path",
    "fasta_bytes",
    "fasta_md5",
    "legacy_backup_out",
    "output_dir",
    "action",
    "reason",
    "priority",
]


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    run_root = root / "software_outputs" / "repeatmasker_dfam" / args.run_id
    rows: list[dict[str, str]] = []

    for i, anchor in enumerate(ANCHORS, start=1):
        fasta = root / anchor["fasta"]
        out_dir = run_root / anchor["species_code"]
        complete = out_dir / "COMPLETE"
        legacy = root / anchor["legacy_backup"] if anchor["legacy_backup"] else None
        if complete.exists():
            action = "skip_existing_run"
            reason = f"existing COMPLETE in {out_dir}"
        else:
            action = "submit"
            reason = "no Dfam 3.9 self-run COMPLETE found"

        if legacy and legacy.exists() and action == "submit":
            reason += "; legacy backup exists but is not this Dfam 3.9 run"

        if not fasta.exists():
            action = "blocked_missing_fasta"
            reason = f"missing FASTA: {fasta}"
            fasta_bytes = ""
            fasta_hash = ""
        else:
            fasta_bytes = str(fasta.stat().st_size)
            fasta_hash = file_md5(fasta)

        rows.append(
            {
                "array_index": str(i),
                "species_code": anchor["species_code"],
                "scientific_name": anchor["scientific_name"],
                "repeatmasker_species": anchor["repeatmasker_species"],
                "fasta_path": str(fasta),
                "fasta_bytes": fasta_bytes,
                "fasta_md5": fasta_hash,
                "legacy_backup_out": str(legacy) if legacy and legacy.exists() else "",
                "output_dir": str(out_dir),
                "action": action,
                "reason": reason,
                "priority": anchor["priority"],
            }
        )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
