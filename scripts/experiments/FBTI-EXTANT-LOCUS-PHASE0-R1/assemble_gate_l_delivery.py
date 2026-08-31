#!/usr/bin/env python3
"""Assemble one independent, actor-specific Gate-L delivery directory.

The coordinator packet manifest and the other actor's assignment are used only
as input.  The delivery contains one opaque assignment, its six response TSVs,
the packet data needed to annotate those IDs, the handbook, and the evidence
registry.  Packet files are copied explicitly so the result is independent of
the coordinator bundle and cannot accidentally include model atoms or other
coordinator-only assets.
"""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


ACTORS = {"A1", "A2"}
PACKET_FILES = (
    "packet.tsv",
    "sequence.fa",
    "context_features.tsv",
    "raw_flybase_features.gff3",
)
RESPONSE_FILES = (
    "package_reviews.tsv",
    "loci.tsv",
    "material_segments.tsv",
    "boundaries.tsv",
    "interruptions.tsv",
    "relations.tsv",
)
ASSIGNMENT_FIELDS = {
    "actor_id",
    "assignment_order",
    "packet_id",
    "packet_relpath",
    "response_dir",
}


def _read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        if fields is None:
            raise ValueError(f"missing TSV header: {path}")
        if len(fields) != len(set(fields)):
            raise ValueError(f"duplicate TSV columns: {path}")
        rows = list(reader)
    if any(value is None for row in rows for value in row.values()):
        raise ValueError(f"malformed TSV row: {path}")
    return fields, rows


def _packet_ids_from_bundle(packet_bundle: Path) -> list[str]:
    fields, rows = _read_tsv(packet_bundle / "packet_manifest.tsv")
    if "packet_id" not in fields:
        raise ValueError("packet manifest missing packet_id")
    packet_ids = [row["packet_id"] for row in rows]
    if not packet_ids or any(not packet_id for packet_id in packet_ids):
        raise ValueError("packet manifest has no usable packet IDs")
    if len(packet_ids) != len(set(packet_ids)):
        raise ValueError("packet manifest contains duplicate packet_id")
    if any(Path(packet_id).name != packet_id for packet_id in packet_ids):
        raise ValueError("packet_id is not a simple directory name")

    packet_root = packet_bundle / "packets"
    if not packet_root.is_dir():
        raise ValueError(f"missing packet directory: {packet_root}")
    packet_dirs = {
        path.name for path in packet_root.iterdir() if path.is_dir()
    }
    if packet_dirs != set(packet_ids):
        raise ValueError("packet_id set differs between manifest and packet directories")
    for packet_id in packet_ids:
        packet_dir = packet_root / packet_id
        for filename in PACKET_FILES:
            if not (packet_dir / filename).is_file():
                raise ValueError(f"missing packet file: {packet_id}/{filename}")
        packet_fields, packet_rows = _read_tsv(packet_dir / "packet.tsv")
        if "packet_id" not in packet_fields or len(packet_rows) != 1:
            raise ValueError(f"invalid packet.tsv: {packet_id}")
        if packet_rows[0]["packet_id"] != packet_id:
            raise ValueError(f"packet.tsv packet_id disagrees with manifest: {packet_id}")
    return packet_ids


def _assignment_ids(kit_dir: Path, actor: str, packet_ids: set[str]) -> tuple[Path, list[dict[str, str]]]:
    actor_dir = kit_dir / f"annotator_{actor}"
    assignment_path = actor_dir / "assignment.tsv"
    fields, rows = _read_tsv(assignment_path)
    missing = sorted(ASSIGNMENT_FIELDS - set(fields))
    if missing:
        raise ValueError(f"assignment missing fields: {missing}")
    if not rows:
        raise ValueError("assignment has no packet IDs")
    seen: set[str] = set()
    orders: list[int] = []
    expected_response_dir = f"annotator_{actor}/responses"
    for row in rows:
        packet_id = row["packet_id"]
        if packet_id in seen:
            raise ValueError(f"duplicate assignment packet_id: {packet_id}")
        if packet_id not in packet_ids:
            raise ValueError(f"assignment packet_id not in packet bundle: {packet_id}")
        if row["actor_id"] != actor:
            raise ValueError(f"assignment actor_id disagrees with --actor: {packet_id}")
        if row["packet_relpath"] != f"packets/{packet_id}":
            raise ValueError(f"unexpected packet_relpath: {packet_id}")
        if row["response_dir"] != expected_response_dir:
            raise ValueError(f"unexpected response_dir: {packet_id}")
        try:
            orders.append(int(row["assignment_order"]))
        except ValueError as error:
            raise ValueError(f"invalid assignment_order: {packet_id}") from error
        seen.add(packet_id)
    if seen != packet_ids:
        raise ValueError("packet_id set differs between packet bundle and assignment")
    if sorted(orders) != list(range(1, len(rows) + 1)):
        raise ValueError("assignment_order must be a complete 1-based order")
    return assignment_path, rows


def _response_paths_and_validate(
    kit_dir: Path,
    actor: str,
    packet_ids: set[str],
) -> list[Path]:
    response_dir = kit_dir / f"annotator_{actor}" / "responses"
    paths: list[Path] = []
    for filename in RESPONSE_FILES:
        path = response_dir / filename
        fields, rows = _read_tsv(path)
        id_field = "packet_id" if "packet_id" in fields else "package_id"
        if id_field not in fields:
            raise ValueError(f"response missing opaque packet ID: {path}")
        if "actor_id" not in fields:
            raise ValueError(f"response missing actor_id: {path}")
        for row in rows:
            packet_id = row[id_field]
            if packet_id not in packet_ids:
                raise ValueError(f"response packet_id not in packet bundle: {packet_id}")
            if "actor_id" in fields and row["actor_id"] != actor:
                raise ValueError(f"response actor_id disagrees with --actor: {path}")
        paths.append(path)
    return paths


def assemble_gate_l_delivery(
    packet_bundle: Path,
    kit_dir: Path,
    handbook: Path,
    evidence_registry: Path,
    actor: str,
    output_dir: Path,
) -> None:
    """Build one self-contained delivery for ``actor``."""

    if actor not in ACTORS:
        raise ValueError(f"unsupported actor: {actor}")
    packet_ids = set(_packet_ids_from_bundle(packet_bundle))
    assignment_path, assignment_rows = _assignment_ids(kit_dir, actor, packet_ids)
    response_paths = _response_paths_and_validate(kit_dir, actor, packet_ids)
    if not handbook.is_file():
        raise ValueError(f"missing handbook: {handbook}")
    if not evidence_registry.is_file():
        raise ValueError(f"missing evidence registry: {evidence_registry}")

    output_dir.mkdir(parents=True, exist_ok=False)
    assignment_fields, _ = _read_tsv(assignment_path)
    with (output_dir / "assignment.tsv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=assignment_fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in assignment_rows:
            writer.writerow({**row, "response_dir": "responses"})
    response_output = output_dir / "responses"
    response_output.mkdir()
    for response_path in response_paths:
        shutil.copy2(response_path, response_output / response_path.name)

    packet_output = output_dir / "packets"
    packet_output.mkdir()
    for packet_id in sorted(packet_ids):
        source_dir = packet_bundle / "packets" / packet_id
        destination_dir = packet_output / packet_id
        destination_dir.mkdir()
        for filename in PACKET_FILES:
            shutil.copy2(source_dir / filename, destination_dir / filename)

    shutil.copy2(handbook, output_dir / "annotator_handbook.md")
    shutil.copy2(evidence_registry, output_dir / "evidence_registry.tsv")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-bundle", type=Path, required=True)
    parser.add_argument("--kit-dir", type=Path, required=True)
    parser.add_argument("--handbook", type=Path, required=True)
    parser.add_argument("--evidence-registry", type=Path, required=True)
    parser.add_argument("--actor", choices=sorted(ACTORS), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    assemble_gate_l_delivery(
        args.packet_bundle,
        args.kit_dir,
        args.handbook,
        args.evidence_registry,
        args.actor,
        args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
