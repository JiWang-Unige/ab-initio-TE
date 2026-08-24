#!/usr/bin/env python3
"""Exact, label-preserving enrichment of the archived Module 5 JSONL.

The source BED is the same canonical ``rmsk_te.bed.gz`` family used by the
historical extractor.  The join key is intentionally strict:
``(species, chrom, start, end, class, family)``.  This utility only restores
source annotation metadata (repeat name, strand, raw BED fields and hashes).
It never creates or infers copy, superfamily, or homology-component identity.
Missing or ambiguous source matches are typed errors; no partial output is
published.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


JOIN_FIELDS = ("species", "chrom", "start", "end", "class", "family")
NOT_GENERATED_FIELDS = ("copy_id", "superfamily_id", "homology_component_id")


class EnrichmentError(RuntimeError):
    """Input/source identity cannot be resolved without inference."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")


def load_fragments(path: Path) -> list[dict]:
    rows = []
    with open_text(path) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EnrichmentError(f"MALFORMED_FRAGMENT_JSON:{line_number}:{exc}") from exc
            if not isinstance(row, dict):
                raise EnrichmentError(f"FRAGMENT_NOT_OBJECT:{line_number}")
            rows.append(row)
    if not rows:
        raise EnrichmentError("EMPTY_FRAGMENT_INPUT")
    return rows


def join_key(row: dict) -> tuple[str, str, int, int, str, str]:
    missing = [field for field in JOIN_FIELDS if field not in row or row[field] in (None, "")]
    if missing:
        raise EnrichmentError(f"FRAGMENT_MISSING_JOIN_FIELDS:{','.join(missing)}")
    try:
        start, end = int(row["start"]), int(row["end"])
    except (TypeError, ValueError) as exc:
        raise EnrichmentError(f"FRAGMENT_NON_INTEGER_COORDINATE:{row.get('species')}:{row.get('chrom')}:{row.get('start')}:{row.get('end')}") from exc
    if start < 0 or end <= start:
        raise EnrichmentError(f"FRAGMENT_INVALID_INTERVAL:{row.get('species')}:{row.get('chrom')}:{start}:{end}")
    return (str(row["species"]), str(row["chrom"]), start, end, str(row["class"]), str(row["family"]))


def bed_key(species: str, fields: list[str]) -> tuple[str, str, int, int, str, str]:
    if len(fields) < 8:
        raise EnrichmentError(f"BED_SCHEMA_TOO_SHORT:{species}:{len(fields)}")
    try:
        start, end = int(fields[1]), int(fields[2])
    except ValueError as exc:
        raise EnrichmentError(f"BED_NON_INTEGER_COORDINATE:{species}:{fields[:3]}") from exc
    return (species, fields[0], start, end, fields[6], fields[7])


def exact_enrich(rows: list[dict], bed_root: Path) -> tuple[list[dict], dict]:
    targets_by_species: dict[str, dict[tuple, list[int]]] = defaultdict(lambda: defaultdict(list))
    for index, row in enumerate(rows):
        key = join_key(row)
        targets_by_species[key[0]][key].append(index)

    matches: dict[int, list[dict]] = defaultdict(list)
    source_audit = []
    for species, target_keys in sorted(targets_by_species.items()):
        bed_path = bed_root / species / "rmsk_te.bed.gz"
        if not bed_path.is_file():
            raise EnrichmentError(f"MISSING_CANONICAL_BED:{species}:{bed_path}")
        digest = sha256_file(bed_path)
        scanned = 0
        matching_source_rows = 0
        with gzip.open(bed_path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip() or line.startswith("#"):
                    continue
                fields = line.rstrip("\n").split("\t")
                key = bed_key(species, fields)
                scanned += 1
                if key not in target_keys:
                    continue
                matching_source_rows += 1
                raw = line.rstrip("\n")
                source = {
                    "source_bed_path": str(bed_path),
                    "source_bed_sha256": digest,
                    "source_bed_line_number": line_number,
                    "source_bed_row_sha256": sha256_bytes(raw.encode("utf-8")),
                    # Preserve the exact source line as an audit-friendly raw
                    # field; parsed columns remain available below.
                    "raw": raw,
                    "source_bed_fields": fields,
                    "source_join_key": list(key),
                    "repeat_name": fields[3],
                    "strand": fields[5],
                    "source_class": fields[6],
                    "source_family": fields[7],
                }
                for row_index in target_keys[key]:
                    matches[row_index].append(source)
        source_audit.append({
            "species": species,
            "path": str(bed_path),
            "sha256": digest,
            "scanned_bed_rows": scanned,
            "matched_source_rows": matching_source_rows,
            "target_key_count": len(target_keys),
        })

    missing = [index for index in range(len(rows)) if not matches.get(index)]
    ambiguous = [index for index in range(len(rows)) if len(matches[index]) != 1 and index not in missing]
    if missing:
        raise EnrichmentError(f"BED_JOIN_MISSING:{len(missing)}:row_indices={missing[:10]}")
    if ambiguous:
        raise EnrichmentError(f"BED_JOIN_AMBIGUOUS:{len(ambiguous)}:row_indices={ambiguous[:10]}")

    enriched = []
    for index, row in enumerate(rows):
        output = dict(row)
        output.update(matches[index][0])
        output["enrichment_status"] = "exact_canonical_bed_join"
        output["identity_fields_generated"] = []
        enriched.append(output)
    manifest = {
        "schema_version": "TEFM-MODULE5-BED-ENRICHMENT-1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_records": len(rows),
        "output_records": len(enriched),
        "join_fields": list(JOIN_FIELDS),
        "source_audit": source_audit,
        "generated_identity_fields": [],
        "not_generated_identity_fields": list(NOT_GENERATED_FIELDS),
        "copy_id_policy": "not_created; coordinates and family names are not copy identity",
        "superfamily_policy": "not_created; raw class/family are preserved only",
        "homology_component_policy": "not_created; no sequence graph or fallback",
    }
    return enriched, manifest


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, path)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run(args: argparse.Namespace) -> int:
    fragments = Path(args.fragments).resolve()
    bed_root = Path(args.bed_root).resolve()
    output = Path(args.output).resolve()
    if not fragments.is_file():
        raise EnrichmentError(f"MISSING_FRAGMENT_INPUT:{fragments}")
    rows = load_fragments(fragments)
    enriched, manifest = exact_enrich(rows, bed_root)
    manifest["input_path"] = str(fragments)
    manifest["input_sha256"] = sha256_file(fragments)
    manifest["bed_root"] = str(bed_root)
    write_jsonl(output, enriched)
    write_json(output.with_suffix(output.suffix + ".manifest.json"), manifest)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fragments", required=True, help="Module5 JSONL or JSONL.GZ")
    parser.add_argument("--bed-root", required=True, help="Root containing <species>/rmsk_te.bed.gz")
    parser.add_argument("--output", required=True, help="Enriched JSONL output")
    return parser


if __name__ == "__main__":
    try:
        raise SystemExit(run(build_parser().parse_args()))
    except EnrichmentError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
