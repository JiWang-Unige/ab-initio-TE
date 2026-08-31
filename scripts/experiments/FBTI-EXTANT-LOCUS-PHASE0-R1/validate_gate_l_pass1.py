#!/usr/bin/env python3
"""Validate and normalize one frozen Gate-L Pass-1 response bundle.

The response tables use opaque packet IDs while an annotator is blind.  The
coordinator packet manifest supplies the only packet-to-package mapping.  This
script validates the frozen Pass-1 ontology and writes normalized tables only
after every table has passed validation.  P3 atom projection and Gate-L
metrics are deliberately outside this command.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


MANIFEST_REQUIRED_FIELDS = {
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
EVIDENCE_REGISTRY_FIELDS = {
    "evidence_code",
    "evidence_class",
    "source_version",
    "independent_of_fbti_endpoint",
    "used_by_gate_e",
}

TABLE_FIELDS = {
    "package_reviews.tsv": [
        "package_id",
        "actor_id",
        "package_status",
        "topology_resolution",
        "topology_reason",
    ],
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

PACKAGE_STATUSES = {
    "resolved",
    "partially_resolved",
    "unresolved",
    "abstained",
}
LOCUS_STATUSES = {"resolved", "partially_resolved", "unresolved"}
LOCUS_ASSIGNMENT_STATUSES = {"assigned", "unresolved"}
BOUNDARY_SIDES = {"left", "right"}
BOUNDARY_IDENTIFIABILITY = {"point", "interval", "unidentifiable"}
INTERRUPTION_TYPES = {
    "nested_locus_occupied",
    "unknown_sequence",
    "assembly_gap",
    "non_TE_supported",
    "unresolved",
}
RELATION_TYPES = {"nested_in", "distinct_locus", "overlap_unresolved"}
ADJUDICATION_RESOLUTIONS = {
    "accept_a1",
    "accept_a2",
    "same_topology_minor_edit",
    "new_topology",
}


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        if fields is None:
            raise ValueError(f"missing TSV header: {path}")
        if len(set(fields)) != len(fields):
            raise ValueError(f"duplicate TSV columns: {path}")
        rows = list(reader)
    for line_number, row in enumerate(rows, start=2):
        if any(value is None for value in row.values()):
            raise ValueError(f"malformed TSV row at {path}:{line_number}")
    return fields, rows


def _integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer for {label}: {value!r}") from error


def read_packet_manifest(path: Path) -> dict[str, dict[str, object]]:
    fields, rows = read_tsv(path)
    missing = sorted(MANIFEST_REQUIRED_FIELDS - set(fields))
    if missing:
        raise ValueError(f"packet manifest missing fields: {missing}")
    if not rows:
        raise ValueError("packet manifest is empty")

    packets: dict[str, dict[str, object]] = {}
    packages: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        packet_id = row["packet_id"]
        package_id = row["package_id"]
        if not packet_id or not package_id:
            raise ValueError(f"empty packet/package ID at {path}:{line_number}")
        if packet_id in packets:
            raise ValueError(f"duplicate packet_id in manifest: {packet_id}")
        if package_id in packages:
            raise ValueError(f"duplicate package_id in manifest: {package_id}")
        if row["role"] not in {"calibration", "main", "reserve"}:
            raise ValueError(f"unexpected packet role: {packet_id}/{row['role']}")
        if not row["assembly_id"] or not row["seqid"]:
            raise ValueError(f"empty assembly or seqid in manifest: {packet_id}")
        package_start = _integer(row["package_start0"], f"{packet_id}.package_start0")
        package_end = _integer(row["package_end0"], f"{packet_id}.package_end0")
        core_start = _integer(row["core_start0"], f"{packet_id}.core_start0")
        core_end = _integer(row["core_end0"], f"{packet_id}.core_end0")
        if package_start < 0 or package_end <= package_start:
            raise ValueError(f"invalid package interval: {packet_id}")
        if core_start < package_start or core_end > package_end or core_end <= core_start:
            raise ValueError(f"core interval is not contained in package: {packet_id}")
        packets[packet_id] = {
            "package_id": package_id,
            "seqid": row["seqid"],
            "package_start": package_start,
            "package_end": package_end,
        }
        packages.add(package_id)
    return packets


def read_evidence_registry(path: Path) -> set[str]:
    fields, rows = read_tsv(path)
    missing = sorted(EVIDENCE_REGISTRY_FIELDS - set(fields))
    if missing:
        raise ValueError(f"evidence registry missing fields: {missing}")
    codes: set[str] = set()
    for row in rows:
        code = row["evidence_code"]
        if not code or code in codes:
            raise ValueError(f"duplicate or empty evidence_code: {code!r}")
        for field in ("independent_of_fbti_endpoint", "used_by_gate_e"):
            if row[field] not in {"0", "1"}:
                raise ValueError(f"invalid {field} for evidence code {code}")
        codes.add(code)
    return codes


def _check_fields(filename: str, fields: list[str]) -> None:
    expected = TABLE_FIELDS[filename]
    if set(fields) != set(expected):
        raise ValueError(f"{filename} schema must be {expected}, got {fields}")


def _check_actor(rows: list[dict[str, str]], actor: str, filename: str) -> None:
    for row in rows:
        if row["actor_id"] != actor:
            raise ValueError(
                f"{filename} actor_id disagrees with --actor {actor}: {row['actor_id']!r}"
            )


def _check_evidence_codes(
    raw: dict[str, list[dict[str, str]]], allowed_codes: set[str]
) -> None:
    for filename in (
        "material_segments.tsv",
        "boundaries.tsv",
        "interruptions.tsv",
        "relations.tsv",
    ):
        for row in raw[filename]:
            value = row["evidence_codes"]
            codes = [] if not value else value.split(",")
            if codes != sorted(set(codes)):
                raise ValueError(f"{filename} evidence_codes must be unique and sorted")
            unknown = sorted(set(codes) - allowed_codes)
            if unknown:
                raise ValueError(f"{filename} uses unknown evidence_code: {unknown[0]}")


def _map_package_id(row: dict[str, str], packets: dict[str, dict[str, object]], filename: str) -> dict[str, str]:
    packet_id = row["package_id"]
    if packet_id not in packets:
        raise ValueError(f"{filename} references unknown packet_id: {packet_id}")
    normalized = dict(row)
    normalized["package_id"] = str(packets[packet_id]["package_id"])
    return normalized


def _inside(start: int, end: int, package: dict[str, object]) -> bool:
    return (
        int(package["package_start"]) <= start
        and start < end
        and end <= int(package["package_end"])
    )


def _boundary_inside(position: int, package: dict[str, object]) -> bool:
    return int(package["package_start"]) <= position <= int(package["package_end"])


def _check_package_reviews(
    rows: list[dict[str, str]],
    packets: dict[str, dict[str, object]],
    actor: str,
) -> None:
    packet_ids = set(packets)
    seen: set[str] = set()
    for row in rows:
        packet_id = row["package_id"]
        if packet_id not in packet_ids:
            raise ValueError(f"package_reviews.tsv references unknown packet_id: {packet_id}")
        if packet_id in seen:
            raise ValueError(f"duplicate package review: {packet_id}")
        seen.add(packet_id)
        if row["package_status"] not in PACKAGE_STATUSES:
            raise ValueError(f"invalid package_status: {packet_id}/{row['package_status']}")
        if actor in {"A1", "A2"}:
            if row["topology_resolution"]:
                raise ValueError("A1/A2 topology_resolution must be empty")
        elif row["topology_resolution"] not in ADJUDICATION_RESOLUTIONS:
            raise ValueError(
                f"invalid ADJ topology_resolution: {packet_id}/{row['topology_resolution']}"
            )
        if row["topology_resolution"] == "new_topology" and not row["topology_reason"]:
            raise ValueError(f"ADJ new_topology requires topology_reason: {packet_id}")
    if seen != packet_ids:
        missing = sorted(packet_ids - seen)
        extra = sorted(seen - packet_ids)
        raise ValueError(f"package review denominator mismatch; missing={missing}, extra={extra}")


def _validate_package_tables(
    packets: dict[str, dict[str, object]],
    reviews: list[dict[str, str]],
    loci: list[dict[str, str]],
    materials: list[dict[str, str]],
    boundaries: list[dict[str, str]],
    interruptions: list[dict[str, str]],
    relations: list[dict[str, str]],
) -> None:
    rows_by_packet: dict[str, dict[str, list[dict[str, str]]]] = {
        packet_id: {
            "loci": [],
            "materials": [],
            "boundaries": [],
            "interruptions": [],
            "relations": [],
        }
        for packet_id in packets
    }
    review_by_packet = {row["package_id"]: row for row in reviews}
    for filename, key, rows in (
        ("loci.tsv", "loci", loci),
        ("material_segments.tsv", "materials", materials),
        ("boundaries.tsv", "boundaries", boundaries),
        ("interruptions.tsv", "interruptions", interruptions),
        ("relations.tsv", "relations", relations),
    ):
        for row in rows:
            if row["package_id"] not in rows_by_packet:
                raise ValueError(f"{filename} references unknown normalized package: {row['package_id']}")
            rows_by_packet[row["package_id"]][key].append(row)

    for packet_id, tables in rows_by_packet.items():
        package = packets[packet_id]
        review = review_by_packet[packet_id]
        locus_rows = tables["loci"]
        material_rows = tables["materials"]
        boundary_rows = tables["boundaries"]
        interruption_rows = tables["interruptions"]
        relation_rows = tables["relations"]
        locus_ids: set[str] = set()
        locus_status: dict[str, str] = {}
        for row in locus_rows:
            locus_id = row["locus_id"]
            if not locus_id or locus_id in locus_ids:
                raise ValueError(f"duplicate or empty locus_id: {packet_id}/{locus_id}")
            if row["locus_status"] not in LOCUS_STATUSES:
                raise ValueError(f"invalid locus_status: {packet_id}/{row['locus_status']}")
            start = _integer(row["locus_envelope_start"], f"{packet_id}/{locus_id}.locus_envelope_start")
            end = _integer(row["locus_envelope_end"], f"{packet_id}/{locus_id}.locus_envelope_end")
            if not _inside(start, end, package):
                raise ValueError(f"locus envelope outside package: {packet_id}/{locus_id}")
            locus_ids.add(locus_id)
            locus_status[locus_id] = row["locus_status"]

        segment_ids: set[str] = set()
        assigned_segments: list[tuple[str, str, int, int]] = []
        assigned_material_intervals: list[tuple[str, int, int]] = []
        unresolved_material_intervals: list[tuple[str, int, int]] = []
        assigned_loci: set[str] = set()
        assigned_by_locus: dict[str, list[tuple[int, int]]] = {
            locus_id: [] for locus_id in locus_ids
        }
        for row in material_rows:
            segment_id = row["segment_id"]
            if not segment_id or segment_id in segment_ids:
                raise ValueError(f"duplicate or empty segment_id: {packet_id}/{segment_id}")
            if row["locus_assignment_status"] not in LOCUS_ASSIGNMENT_STATUSES:
                raise ValueError(
                    f"invalid locus_assignment_status: {packet_id}/{row['locus_assignment_status']}"
                )
            locus_id = row["locus_id"]
            if row["locus_assignment_status"] == "assigned":
                if locus_id not in locus_ids:
                    raise ValueError(f"material segment references unknown locus: {packet_id}/{locus_id}")
                assigned_loci.add(locus_id)
            elif locus_id:
                raise ValueError(f"unresolved material segment must not name a locus: {packet_id}/{segment_id}")
            if row["seqid"] != package["seqid"]:
                raise ValueError(f"material segment crosses package contig: {packet_id}/{segment_id}")
            start = _integer(row["start"], f"{packet_id}/{segment_id}.start")
            end = _integer(row["end"], f"{packet_id}/{segment_id}.end")
            if not _inside(start, end, package):
                raise ValueError(f"material segment outside package: {packet_id}/{segment_id}")
            if row["locus_assignment_status"] == "assigned":
                assigned_segments.append((row["seqid"], locus_id, start, end))
                assigned_by_locus[locus_id].append((start, end))
                assigned_material_intervals.append((segment_id, start, end))
            else:
                unresolved_material_intervals.append((segment_id, start, end))
            segment_ids.add(segment_id)

        for assigned_id, assigned_start, assigned_end in assigned_material_intervals:
            for unresolved_id, unresolved_start, unresolved_end in unresolved_material_intervals:
                if max(assigned_start, unresolved_start) < min(assigned_end, unresolved_end):
                    raise ValueError(
                        f"assigned and unresolved material overlap: "
                        f"{packet_id}/{assigned_id}/{unresolved_id}"
                    )

        for row in locus_rows:
            locus_id = row["locus_id"]
            segments = assigned_by_locus[locus_id]
            if not segments:
                raise ValueError(f"declared locus has no assigned material: {packet_id}/{locus_id}")
            envelope_start = int(row["locus_envelope_start"])
            envelope_end = int(row["locus_envelope_end"])
            if min(start for start, _ in segments) < envelope_start or max(
                end for _, end in segments
            ) > envelope_end:
                raise ValueError(
                    f"locus envelope does not contain assigned material: {packet_id}/{locus_id}"
                )

        ordered_segments = sorted(assigned_segments, key=lambda item: (item[0], item[2], item[3], item[1]))
        for previous, current in zip(ordered_segments, ordered_segments[1:]):
            if previous[0] != current[0] or current[2] > previous[3]:
                continue
            if previous[1] == current[1]:
                raise ValueError(f"material segments overlap or touch within locus: {packet_id}/{current[1]}")
            if current[2] < previous[3]:
                raise ValueError(f"assigned material segments overlap across loci: {packet_id}")

        boundary_keys: set[tuple[str, str]] = set()
        for row in boundary_rows:
            locus_id = row["locus_id"]
            side = row["side"]
            if locus_id not in locus_ids:
                raise ValueError(f"boundary references unknown locus: {packet_id}/{locus_id}")
            if side not in BOUNDARY_SIDES:
                raise ValueError(f"invalid boundary side: {packet_id}/{side}")
            key = (locus_id, side)
            if key in boundary_keys:
                raise ValueError(f"duplicate boundary side: {packet_id}/{locus_id}/{side}")
            if row["identifiability"] not in BOUNDARY_IDENTIFIABILITY:
                raise ValueError(
                    f"invalid boundary identifiability: {packet_id}/{row['identifiability']}"
                )
            lower = row["lower_pos"]
            upper = row["upper_pos"]
            if row["identifiability"] == "unidentifiable":
                if lower or upper:
                    raise ValueError(f"unidentifiable boundary must have empty positions: {packet_id}/{locus_id}/{side}")
            else:
                if not lower or not upper:
                    raise ValueError(f"identified boundary requires both positions: {packet_id}/{locus_id}/{side}")
                lower_pos = _integer(lower, f"{packet_id}/{locus_id}/{side}.lower_pos")
                upper_pos = _integer(upper, f"{packet_id}/{locus_id}/{side}.upper_pos")
                if not _boundary_inside(lower_pos, package) or not _boundary_inside(upper_pos, package):
                    raise ValueError(f"boundary position outside package: {packet_id}/{locus_id}/{side}")
                if lower_pos > upper_pos:
                    raise ValueError(f"boundary interval is reversed: {packet_id}/{locus_id}/{side}")
                if row["identifiability"] == "point" and lower_pos != upper_pos:
                    raise ValueError(f"point boundary requires one position: {packet_id}/{locus_id}/{side}")
                if row["identifiability"] == "interval" and lower_pos == upper_pos:
                    raise ValueError(f"interval boundary requires a range: {packet_id}/{locus_id}/{side}")
            boundary_keys.add(key)
        expected_boundary_keys = {(locus_id, side) for locus_id in locus_ids for side in BOUNDARY_SIDES}
        if boundary_keys != expected_boundary_keys:
            raise ValueError(f"each locus requires exactly one left and right boundary: {packet_id}")

        interruption_ids: set[str] = set()
        for row in interruption_rows:
            interruption_id = row["interruption_id"]
            if not interruption_id or interruption_id in interruption_ids:
                raise ValueError(f"duplicate or empty interruption_id: {packet_id}/{interruption_id}")
            locus_id = row["locus_id"]
            if locus_id not in locus_ids:
                raise ValueError(f"interruption references unknown locus: {packet_id}/{locus_id}")
            if row["interruption_type"] not in INTERRUPTION_TYPES:
                raise ValueError(f"invalid interruption_type: {packet_id}/{row['interruption_type']}")
            child_locus_id = row["child_locus_id"]
            if row["interruption_type"] == "nested_locus_occupied":
                if not child_locus_id or child_locus_id not in locus_ids:
                    raise ValueError(f"nested interruption requires a child locus: {packet_id}/{interruption_id}")
            elif child_locus_id:
                raise ValueError(f"non-nested interruption must not name child_locus_id: {packet_id}/{interruption_id}")
            if row["seqid"] != package["seqid"]:
                raise ValueError(f"interruption crosses package contig: {packet_id}/{interruption_id}")
            start = _integer(row["start"], f"{packet_id}/{interruption_id}.start")
            end = _integer(row["end"], f"{packet_id}/{interruption_id}.end")
            if not _inside(start, end, package):
                raise ValueError(f"interruption outside package: {packet_id}/{interruption_id}")
            interruption_ids.add(interruption_id)

        relation_ids: set[str] = set()
        relation_pairs: dict[tuple[str, str], list[dict[str, str]]] = {}
        for row in relation_rows:
            relation_id = row["relation_id"]
            if not relation_id or relation_id in relation_ids:
                raise ValueError(f"duplicate or empty relation_id: {packet_id}/{relation_id}")
            relation_type = row["relation_type"]
            if relation_type not in RELATION_TYPES:
                raise ValueError(f"invalid relation_type: {packet_id}/{relation_type}")
            subject = row["subject_locus_id"]
            object_ = row["object_locus_id"]
            if subject not in locus_ids or object_ not in locus_ids:
                raise ValueError(f"relation references unknown locus: {packet_id}/{relation_id}")
            if subject == object_:
                raise ValueError(f"relation self-edge: {packet_id}/{relation_id}")
            if relation_type != "nested_in" and subject >= object_:
                raise ValueError(f"symmetric relation endpoints must be lexicographic: {packet_id}/{relation_id}")
            pair = tuple(sorted((subject, object_)))
            relation_pairs.setdefault(pair, []).append(row)
            relation_ids.add(relation_id)

        expected_pairs = {
            (left, right)
            for index, left in enumerate(sorted(locus_ids))
            for right in sorted(locus_ids)[index + 1 :]
        }
        if set(relation_pairs) != expected_pairs or any(
            len(rows) != 1 for rows in relation_pairs.values()
        ):
            raise ValueError(f"each pair of declared loci requires exactly one relation: {packet_id}")

        nested_edges = {
            (row["subject_locus_id"], row["object_locus_id"])
            for row in relation_rows
            if row["relation_type"] == "nested_in"
        }
        parent_by_child: dict[str, str] = {}
        for child, parent in nested_edges:
            if child in parent_by_child:
                raise ValueError(f"nested locus has multiple immediate parents: {packet_id}/{child}")
            parent_by_child[child] = parent
        for child in parent_by_child:
            seen = {child}
            current = child
            while current in parent_by_child:
                current = parent_by_child[current]
                if current in seen:
                    raise ValueError(f"nested_in cycle: {packet_id}/{child}")
                seen.add(current)
        for row in interruption_rows:
            if row["interruption_type"] == "nested_locus_occupied":
                edge = (row["child_locus_id"], row["locus_id"])
                if edge not in nested_edges:
                    raise ValueError(f"nested interruption lacks matching nested_in edge: {packet_id}/{row['interruption_id']}")

        package_status = review["package_status"]
        stable_loci = {
            locus_id
            for locus_id, status in locus_status.items()
            if status in {"resolved", "partially_resolved"}
        }
        if package_status == "abstained":
            if any(tables.values()):
                raise ValueError(f"abstained package must not contain annotation rows: {packet_id}")
        elif package_status == "resolved":
            if not locus_ids or stable_loci != locus_ids or len(assigned_loci) != len(locus_ids):
                raise ValueError(f"resolved package has incomplete locus/material annotation: {packet_id}")
            if any(row["locus_assignment_status"] != "assigned" for row in material_rows):
                raise ValueError(f"resolved package has unresolved material: {packet_id}")
            if any(row["relation_type"] == "overlap_unresolved" for row in relation_rows):
                raise ValueError(f"resolved package has unresolved topology: {packet_id}")
        elif package_status == "partially_resolved":
            if not stable_loci or not assigned_loci:
                raise ValueError(f"partially_resolved package lacks stable locus and assigned material: {packet_id}")
        elif package_status == "unresolved":
            if stable_loci or not material_rows:
                raise ValueError(f"unresolved package has stable locus or no supported material: {packet_id}")

        if not locus_ids and any((boundary_rows, interruption_rows, relation_rows)):
            raise ValueError(f"annotation rows reference no declared loci: {packet_id}")


def _write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_and_normalize(
    packet_manifest: Path,
    evidence_registry: Path,
    input_dir: Path,
    actor: str,
    output_dir: Path,
) -> None:
    if actor not in {"A1", "A2", "ADJ"}:
        raise ValueError(f"unsupported actor: {actor}")
    packets = read_packet_manifest(packet_manifest)
    evidence_codes = read_evidence_registry(evidence_registry)
    raw: dict[str, list[dict[str, str]]] = {}
    for filename, expected_fields in TABLE_FIELDS.items():
        fields, rows = read_tsv(input_dir / filename)
        _check_fields(filename, fields)
        _check_actor(rows, actor, filename)
        raw[filename] = rows

    _check_evidence_codes(raw, evidence_codes)

    normalized = {
        filename: [_map_package_id(row, packets, filename) for row in rows]
        for filename, rows in raw.items()
    }
    normalized_packets = {
        str(package["package_id"]): package for package in packets.values()
    }
    _check_package_reviews(normalized["package_reviews.tsv"], normalized_packets, actor)
    _validate_package_tables(
        normalized_packets,
        normalized["package_reviews.tsv"],
        normalized["loci.tsv"],
        normalized["material_segments.tsv"],
        normalized["boundaries.tsv"],
        normalized["interruptions.tsv"],
        normalized["relations.tsv"],
    )

    output_dir.mkdir(parents=True, exist_ok=False)
    for filename, fields in TABLE_FIELDS.items():
        _write_tsv(output_dir / filename, fields, normalized[filename])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-manifest", type=Path, required=True)
    parser.add_argument("--evidence-registry", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--actor", choices=("A1", "A2", "ADJ"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_and_normalize(
        args.packet_manifest,
        args.evidence_registry,
        args.input_dir,
        args.actor,
        args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
