#!/usr/bin/env python3
"""Build chunked RepeatMasker+Dfam manifests for species.md panels."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class Species:
    code: str
    scientific_name: str
    repeatmasker_species: str
    fasta: str
    taxid: str
    priority: str
    existing_complete: str = ""


ANIMALS = [
    Species("human", "Homo sapiens", "Homo sapiens", ".backup/data/genome_data/current_eukaryotes/animals/human/hs1.fa", "9606", "human_anchor"),
    Species("mouse", "Mus musculus", "Mus musculus", ".backup/data/genome_data/current_eukaryotes/animals/mouse/mm39.fa", "10090", "core_train", "software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/mouse/COMPLETE"),
    Species("rat", "Rattus norvegicus", "Rattus norvegicus", ".backup/data/genome_data/current_eukaryotes/animals/rat/rn7.fa.gz", "10116", "core_train"),
    Species("dog", "Canis lupus familiaris", "Canis lupus familiaris", ".backup/data/genome_data/current_eukaryotes/animals/dog/canFam6.fa.gz", "9615", "core_train"),
    Species("chicken", "Gallus gallus", "Gallus gallus", ".backup/data/genome_data/current_eukaryotes/animals/chicken/galGal6.fa", "9031", "core_train", "software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/chicken/COMPLETE"),
    Species("zebrafish", "Danio rerio", "Danio rerio", ".backup/data/genome_data/current_eukaryotes/animals/zebrafish/danRer11.fa", "7955", "core_train", "software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/zebrafish/COMPLETE"),
    Species("fruit_fly", "Drosophila melanogaster", "Drosophila melanogaster", ".backup/data/genome_data/current_eukaryotes/animals/fruit_fly/dm6.fa", "7227", "core_train", "software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/fruit_fly/COMPLETE"),
    Species("c_elegans", "Caenorhabditis elegans", "Caenorhabditis elegans", ".backup/data/genome_data/current_eukaryotes/animals/c_elegans/ce11.fa", "6239", "core_train", "software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/c_elegans/COMPLETE"),
    Species("pig", "Sus scrofa", "Sus scrofa", ".backup/data/genome_data/current_eukaryotes/animals/pig/susScr11.fa.gz", "9823", "core_holdout"),
    Species("cattle", "Bos taurus", "Bos taurus", ".backup/data/genome_data/current_eukaryotes/animals/cattle/bosTau9.fa", "9913", "core_holdout"),
    Species("horse", "Equus caballus", "Equus caballus", ".backup/data/genome_data/current_eukaryotes/animals/horse/equCab3.fa.gz", "9796", "core_holdout"),
    Species("western_clawed_frog", "Xenopus tropicalis", "Xenopus tropicalis", ".backup/data/genome_data/current_eukaryotes/animals/western_clawed_frog/xenTro10.fa", "8364", "core_holdout"),
    Species("western_honey_bee", "Apis mellifera", "Apis mellifera", ".backup/data/genome_data/current_eukaryotes/animals/western_honey_bee/apiMel2.fa.gz", "7460", "core_holdout"),
    Species("red_flour_beetle", "Tribolium castaneum", "Tribolium castaneum", ".backup/data/genome_data/current_eukaryotes/animals/red_flour_beetle/triCas2.fa.gz", "7070", "core_holdout"),
]

PLANTS = [
    Species("thale_cress", "Arabidopsis thaliana", "Arabidopsis thaliana", ".backup/data/genome_data/current_eukaryotes/plants/thale_cress/Arabidopsis_thaliana.TAIR10.dna.toplevel.fa", "3702", "plant_sentinel"),
    Species("rice", "Oryza sativa", "Oryza sativa", ".backup/data/genome_data/current_eukaryotes/plants/rice/Oryza_sativa.IRGSP-1.0.dna.toplevel.fa", "4530", "plant_sentinel"),
    Species("maize", "Zea mays", "Zea mays", ".backup/data/genome_data/current_eukaryotes/plants/maize/Zea_mays.Zm-B73-REFERENCE-NAM-5.0.dna.toplevel.fa", "4577", "plant_sentinel"),
    Species("tomato", "Solanum lycopersicum", "Solanum lycopersicum", ".backup/data/genome_data/current_eukaryotes/plants/tomato/Solanum_lycopersicum.SL3.0.dna.toplevel.fa.gz", "4081", "plant_sentinel"),
    Species("green_foxtail", "Setaria viridis", "Setaria viridis", ".backup/data/genome_data/current_eukaryotes/plants/green_foxtail/Setaria_viridis.Setaria_viridis_v2.0.dna.toplevel.fa.gz", "4556", "plant_sentinel"),
    Species("grape", "Vitis vinifera", "Vitis vinifera", ".backup/data/genome_data/current_eukaryotes/plants/grape/Vitis_vinifera.ASM3070453v1.dna.toplevel.fa.gz", "29760", "plant_sentinel"),
]


CHUNK_FIELDS = [
    "chunk_index",
    "species_code",
    "scientific_name",
    "repeatmasker_species",
    "taxid",
    "priority",
    "source_fasta",
    "source_fasta_bytes",
    "source_fasta_md5",
    "chunk_id",
    "chunk_fasta",
    "chunk_bases",
    "record_count",
    "records",
    "output_dir",
    "species_output_dir",
]

SPECIES_FIELDS = [
    "species_code",
    "scientific_name",
    "repeatmasker_species",
    "taxid",
    "priority",
    "source_fasta",
    "source_fasta_bytes",
    "source_fasta_md5",
    "species_output_dir",
    "action",
    "reason",
    "chunk_count",
    "chunk_bases",
    "existing_complete",
]


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def md5(path: Path) -> str:
    h = hashlib.md5()
    opener = path.open
    with opener("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize_record_name(header: str) -> str:
    token = header.strip().split()[0]
    token = re.sub(r"[^A-Za-z0-9_.:-]+", "_", token)
    return token[:120] or "record"


def read_fasta_records(path: Path) -> Iterator[tuple[str, str]]:
    name: str | None = None
    seq_parts: list[str] = []
    with open_text(path) as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(seq_parts)
                name = line[1:]
                seq_parts = []
            else:
                seq_parts.append(line.strip())
    if name is not None:
        yield name, "".join(seq_parts)


def write_chunk(path: Path, records: list[tuple[str, str]]) -> tuple[int, int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    bases = 0
    names: list[str] = []
    with path.open("w") as out:
        for header, seq in records:
            names.append(sanitize_record_name(header))
            bases += len(seq)
            out.write(f">{header}\n")
            for i in range(0, len(seq), 80):
                out.write(seq[i : i + 80] + "\n")
    return bases, len(records), ",".join(names)


def build_chunks(
    species: Species,
    source: Path,
    run_root: Path,
    target_bases: int,
) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    pending: list[tuple[str, str]] = []
    pending_bases = 0
    next_id = 1
    src_bytes = str(source.stat().st_size)
    src_md5 = md5(source)
    species_out = run_root / species.code
    chunk_root = run_root / "chunks" / species.code

    def flush(records: list[tuple[str, str]], label: str) -> None:
        nonlocal next_id
        if not records:
            return
        chunk_id = f"{species.code}_chunk_{next_id:05d}_{label}"
        chunk_path = chunk_root / f"{chunk_id}.fa"
        bases, record_count, record_names = write_chunk(chunk_path, records)
        chunks.append(
            {
                "species_code": species.code,
                "scientific_name": species.scientific_name,
                "repeatmasker_species": species.repeatmasker_species,
                "taxid": species.taxid,
                "priority": species.priority,
                "source_fasta": str(source),
                "source_fasta_bytes": src_bytes,
                "source_fasta_md5": src_md5,
                "chunk_id": chunk_id,
                "chunk_fasta": str(chunk_path),
                "chunk_bases": str(bases),
                "record_count": str(record_count),
                "records": record_names,
                "output_dir": str(species_out / "chunks" / chunk_id),
                "species_output_dir": str(species_out),
            }
        )
        next_id += 1

    for header, seq in read_fasta_records(source):
        seq_bases = len(seq)
        if seq_bases >= target_bases:
            flush(pending, "bundle")
            pending = []
            pending_bases = 0
            flush([(header, seq)], sanitize_record_name(header))
            continue
        if pending and pending_bases + seq_bases > target_bases:
            flush(pending, "bundle")
            pending = []
            pending_bases = 0
        pending.append((header, seq))
        pending_bases += seq_bases
    flush(pending, "bundle")
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--target-bases", type=int, default=50_000_000)
    parser.add_argument("--chunk-manifest", required=True)
    parser.add_argument("--species-manifest", required=True)
    parser.add_argument("--panels", default="animals", help="Comma-separated panels: animals,plants,all")
    parser.add_argument("--species-codes", help="Comma-separated species_code allowlist after panel expansion.")
    parser.add_argument("--force-rerun-existing", action="store_true", help="Ignore existing_complete markers and submit all listed species.")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    run_root = root / "software_outputs" / "repeatmasker_dfam" / args.run_id
    run_root.mkdir(parents=True, exist_ok=True)

    requested = {panel.strip() for panel in args.panels.split(",") if panel.strip()}
    if "all" in requested:
        requested = {"animals", "plants"}
    unknown = requested - {"animals", "plants"}
    if unknown:
        raise SystemExit(f"Unknown panel(s): {','.join(sorted(unknown))}")
    panel_species: list[Species] = []
    if "animals" in requested:
        panel_species.extend(ANIMALS)
    if "plants" in requested:
        panel_species.extend(PLANTS)
    if args.species_codes:
        keep = {code.strip() for code in args.species_codes.split(",") if code.strip()}
        known = {species.code for species in panel_species}
        missing = keep - known
        if missing:
            raise SystemExit(f"species_codes not present in selected panels: {','.join(sorted(missing))}")
        panel_species = [species for species in panel_species if species.code in keep]

    chunk_rows: list[dict[str, str]] = []
    species_rows: list[dict[str, str]] = []
    for species in panel_species:
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
            reason = "chunked no-align RepeatMasker+Dfam run required"
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

    chunk_manifest = Path(args.chunk_manifest)
    species_manifest = Path(args.species_manifest)
    chunk_manifest.parent.mkdir(parents=True, exist_ok=True)
    species_manifest.parent.mkdir(parents=True, exist_ok=True)
    with chunk_manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHUNK_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(chunk_rows)
    with species_manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SPECIES_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(species_rows)


if __name__ == "__main__":
    main()
