#!/usr/bin/env python3
"""Prepare blind human-annotation templates for one frozen packet role.

The packet bundle is already P3-blind and contains the only packet material
distributed to annotators.  This script creates two independent assignment
orders over the same twelve opaque packet IDs, the Pass-1 response TSVs from
the frozen annotation contract, and a separate adjudicator input/template
directory.  It does not copy packet contents, expose the coordinator mapping,
or create Pass-2 atom-projection files.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


PACKET_MANIFEST_FIELDS = {
    "packet_id",
    "package_id",
    "role",
    "role_rank",
    "unit_type",
    "hard_cell",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
    "feature_ids",
}
PACKET_FIELDS = {
    "packet_id",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
}
PACKET_FILES = (
    "packet.tsv",
    "sequence.fa",
    "context_features.tsv",
    "raw_flybase_features.gff3",
)

ASSIGNMENT_FIELDS = [
    "actor_id",
    "assignment_order",
    "packet_id",
    "packet_relpath",
    "response_dir",
]
ADJUDICATION_INPUT_FIELDS = [
    "packet_id",
    "packet_relpath",
    "a1_response_dir",
    "a2_response_dir",
    "adjudication_response_dir",
]

PACKAGE_REVIEW_FIELDS = [
    "package_id",
    "actor_id",
    "package_status",
    "topology_resolution",
    "topology_reason",
]
PASS1_RESPONSE_FIELDS = {
    "loci.tsv": [
        "package_id",
        "actor_id",
        "locus_id",
        "locus_status",
        "locus_envelope_start",
        "locus_envelope_end",
    ],
    "material_segments.tsv": [
        "package_id",
        "actor_id",
        "segment_id",
        "locus_id",
        "seqid",
        "start",
        "end",
        "evidence_codes",
        "locus_assignment_status",
    ],
    "boundaries.tsv": [
        "package_id",
        "actor_id",
        "locus_id",
        "side",
        "identifiability",
        "lower_pos",
        "upper_pos",
        "evidence_codes",
    ],
    "interruptions.tsv": [
        "package_id",
        "actor_id",
        "interruption_id",
        "locus_id",
        "child_locus_id",
        "seqid",
        "start",
        "end",
        "interruption_type",
        "evidence_codes",
    ],
    "relations.tsv": [
        "package_id",
        "actor_id",
        "relation_id",
        "relation_type",
        "subject_locus_id",
        "object_locus_id",
        "evidence_codes",
    ],
}


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        if fields is None:
            raise ValueError(f"missing TSV header: {path}")
        if len(set(fields)) != len(fields):
            raise ValueError(f"duplicate TSV columns: {path}")
        return fields, list(reader)


def read_frozen_packet_manifest(bundle_dir: Path) -> list[dict[str, str]]:
    manifest_path = bundle_dir / "packet_manifest.tsv"
    fields, rows = read_tsv(manifest_path)
    missing = sorted(PACKET_MANIFEST_FIELDS - set(fields))
    if missing:
        raise ValueError(f"packet manifest missing fields: {missing}")
    roles = {row["role"] for row in rows}
    if len(roles) != 1:
        raise ValueError("packet manifest must contain one role")
    role = next(iter(roles))
    expected_count, prefix, width = {
        "calibration": (12, "CALIB", 2),
        "main": (120, "MAIN", 3),
        "reserve": (40, "RESERVE", 3),
    }.get(role, (0, "", 0))
    if not expected_count or len(rows) != expected_count:
        raise ValueError(f"expected frozen {role} packet count {expected_count}, got {len(rows)}")

    expected_ids = [f"{prefix}-{index:0{width}d}" for index in range(1, expected_count + 1)]
    packet_ids = [row["packet_id"] for row in rows]
    if len(set(packet_ids)) != len(packet_ids):
        raise ValueError("packet manifest contains duplicate packet_id")
    if set(packet_ids) != set(expected_ids):
        raise ValueError(f"packet manifest must contain the complete {role} opaque-ID range")

    for row in rows:
        packet_id = row["packet_id"]
        if row["role"] != role:
            raise ValueError(f"mixed packet roles in bundle: {packet_id}")
        packet_dir = bundle_dir / "packets" / packet_id
        if not packet_dir.is_dir():
            raise ValueError(f"missing packet directory: {packet_id}")
        for filename in PACKET_FILES:
            if not (packet_dir / filename).is_file():
                raise ValueError(f"missing packet file: {packet_id}/{filename}")
        packet_fields, packet_rows = read_tsv(packet_dir / "packet.tsv")
        if set(packet_fields) != PACKET_FIELDS or len(packet_rows) != 1:
            raise ValueError(f"invalid packet.tsv schema: {packet_id}")
        if packet_rows[0]["packet_id"] != packet_id:
            raise ValueError(f"packet.tsv ID disagrees with manifest: {packet_id}")

    return sorted(rows, key=lambda row: row["packet_id"])


def _write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _packet_ids_for_actor(packet_ids: list[str], seed: int) -> list[str]:
    order = list(packet_ids)
    random.Random(seed).shuffle(order)
    return order


def _write_response_templates(response_dir: Path, actor_id: str, packet_ids: list[str]) -> None:
    response_dir.mkdir()
    _write_tsv(
        response_dir / "package_reviews.tsv",
        PACKAGE_REVIEW_FIELDS,
        [
            {
                "package_id": packet_id,
                "actor_id": actor_id,
                "package_status": "",
                "topology_resolution": "",
                "topology_reason": "",
            }
            for packet_id in packet_ids
        ],
    )
    for filename, fields in PASS1_RESPONSE_FIELDS.items():
        _write_tsv(response_dir / filename, fields, [])


def _write_annotator_kit(
    output_dir: Path,
    actor_id: str,
    packet_ids: list[str],
) -> None:
    actor_dir = output_dir / f"annotator_{actor_id}"
    actor_dir.mkdir()
    _write_tsv(
        actor_dir / "assignment.tsv",
        ASSIGNMENT_FIELDS,
        [
            {
                "actor_id": actor_id,
                "assignment_order": str(order),
                "packet_id": packet_id,
                "packet_relpath": f"packets/{packet_id}",
                "response_dir": f"annotator_{actor_id}/responses",
            }
            for order, packet_id in enumerate(packet_ids, start=1)
        ],
    )
    _write_response_templates(actor_dir / "responses", actor_id, packet_ids)


def prepare_gate_l_annotation_kits(
    packet_bundle: Path,
    output_dir: Path,
    assignment_seed: int = 20260831,
) -> None:
    packets = read_frozen_packet_manifest(packet_bundle)
    packet_ids = [row["packet_id"] for row in packets]
    a1_ids = _packet_ids_for_actor(packet_ids, assignment_seed)
    a2_ids = _packet_ids_for_actor(packet_ids, assignment_seed + 1)

    output_dir.mkdir(parents=True, exist_ok=False)
    _write_annotator_kit(output_dir, "A1", a1_ids)
    _write_annotator_kit(output_dir, "A2", a2_ids)

    adjudicator_dir = output_dir / "adjudicator"
    adjudicator_dir.mkdir()
    _write_tsv(
        adjudicator_dir / "adjudication_input.tsv",
        ADJUDICATION_INPUT_FIELDS,
        [
            {
                "packet_id": packet_id,
                "packet_relpath": f"packets/{packet_id}",
                "a1_response_dir": "annotator_A1/responses",
                "a2_response_dir": "annotator_A2/responses",
                "adjudication_response_dir": "adjudicator/responses",
            }
            for packet_id in packet_ids
        ],
    )
    _write_response_templates(adjudicator_dir / "responses", "ADJ", packet_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--assignment-seed", type=int, default=20260831)
    args = parser.parse_args()
    prepare_gate_l_annotation_kits(
        args.packet_bundle,
        args.output_dir,
        args.assignment_seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
