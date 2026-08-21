#!/usr/bin/env python3
"""Build chunked RepeatMasker+Dfam manifests from a small TSV species table."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from repeatmasker_dfam_species_chunks import (  # noqa: E402
    CHUNK_FIELDS,
    SPECIES_FIELDS,
    Species,
    build_chunks,
    md5,
)


REQUIRED_FIELDS = [
    "species_code",
    "scientific_name",
    "repeatmasker_species",
    "fasta",
    "taxid",
    "priority",
]


def read_species_table(path: Path) -> list[Species]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    missing = [field for field in REQUIRED_FIELDS if field not in (rows[0].keys() if rows else [])]
    if missing:
        raise SystemExit(f"{path}: missing required columns: {','.join(missing)}")
    species: list[Species] = []
    for row in rows:
        if not row.get("species_code") or row["species_code"].startswith("#"):
            continue
        species.append(
            Species(
                row["species_code"],
                row["scientific_name"],
                row["repeatmasker_species"],
                row["fasta"],
                row["taxid"],
                row["priority"],
                row.get("existing_complete", ""),
            )
        )
    return species


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--run-root",
        help=(
            "Output root for chunk FASTA files and per-species outputs. "
            "Default: software_outputs/repeatmasker_dfam/<run-id>."
        ),
    )
    parser.add_argument("--species-table", required=True)
    parser.add_argument("--target-bases", type=int, default=50_000_000)
    parser.add_argument("--chunk-manifest", required=True)
    parser.add_argument("--species-manifest", required=True)
    parser.add_argument("--force-rerun-existing", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    run_root = Path(args.run_root) if args.run_root else root / "software_outputs" / "repeatmasker_dfam" / args.run_id
    if not run_root.is_absolute():
        run_root = root / run_root
    run_root.mkdir(parents=True, exist_ok=True)
    species_list = read_species_table(root / args.species_table)

    chunk_rows: list[dict[str, str]] = []
    species_rows: list[dict[str, str]] = []
    for species in species_list:
        source = root / species.fasta
        species_out = run_root / species.code
        existing_complete = root / species.existing_complete if species.existing_complete else None
        if existing_complete and existing_complete.exists() and not args.force_rerun_existing:
            action = "skip_existing_complete"
            reason = f"existing complete run: {existing_complete}"
            src_bytes = str(source.stat().st_size) if source.exists() else ""
            src_hash = md5(source) if source.exists() else ""
            chunks: list[dict[str, str]] = []
        elif not source.exists():
            action = "blocked_missing_fasta"
            reason = f"missing FASTA: {source}"
            src_bytes = ""
            src_hash = ""
            chunks = []
        else:
            action = "submit_chunked"
            reason = "custom chunked no-align RepeatMasker+Dfam run required"
            chunks = build_chunks(species, source, run_root, args.target_bases)
            src_bytes = str(source.stat().st_size)
            src_hash = md5(source)
            chunk_rows.extend(chunks)
        species_rows.append(
            {
                "species_code": species.code,
                "scientific_name": species.scientific_name,
                "repeatmasker_species": species.repeatmasker_species,
                "taxid": species.taxid,
                "priority": species.priority,
                "source_fasta": str(source),
                "source_fasta_bytes": src_bytes,
                "source_fasta_md5": src_hash,
                "species_output_dir": str(species_out),
                "action": action,
                "reason": reason,
                "chunk_count": str(len(chunks)),
                "chunk_bases": str(sum(int(row["chunk_bases"]) for row in chunks)),
                "existing_complete": str(existing_complete) if existing_complete and existing_complete.exists() else "",
            }
        )

    for i, row in enumerate(chunk_rows, start=1):
        row["chunk_index"] = str(i)

    for out_path, fields, rows in [
        (Path(args.chunk_manifest), CHUNK_FIELDS, chunk_rows),
        (Path(args.species_manifest), SPECIES_FIELDS, species_rows),
    ]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
