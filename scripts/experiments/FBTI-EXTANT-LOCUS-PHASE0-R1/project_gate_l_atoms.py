#!/usr/bin/env python3
"""Project adjudicated material onto the frozen canonical P3 atoms."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


MATERIAL_FIELDS = {
    "package_id",
    "segment_id",
    "locus_id",
    "seqid",
    "start",
    "end",
    "locus_assignment_status",
}
ATOM_FIELDS = {
    "package_id",
    "atom_id",
    "seqid",
    "start0",
    "end0",
    "package_censored",
}
OUTPUT_FIELDS = [
    "package_id",
    "atom_id",
    "seqid",
    "start",
    "end",
    "assignment",
    "assigned_locus_id",
    "assigned_segment_ids",
    "projection_eligibility",
]


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        if fields is None:
            raise ValueError(f"missing TSV header: {path}")
        if len(set(fields)) != len(fields):
            raise ValueError(f"duplicate TSV columns: {path}")
        return fields, list(reader)


def _require_fields(path: Path, fields: list[str], required: set[str]) -> None:
    missing = sorted(required - set(fields))
    if missing:
        raise ValueError(f"{path} missing fields: {missing}")


def _integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer for {label}: {value!r}") from error


def _overlap(start: int, end: int, other_start: int, other_end: int) -> int:
    return max(0, min(end, other_end) - max(start, other_start))


def _union_length(intervals: list[tuple[int, int]]) -> int:
    if not intervals:
        return 0
    total = 0
    current_start, current_end = sorted(intervals)[0]
    for start, end in sorted(intervals)[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    return total + current_end - current_start


def _material_rows_by_package(
    rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    by_package: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        status = row["locus_assignment_status"]
        if status not in {"assigned", "unresolved"}:
            raise ValueError(
                f"invalid locus_assignment_status: {row['package_id']}/{status}"
            )
        if status == "assigned" and not row["locus_id"]:
            raise ValueError(
                f"assigned material has no locus_id: {row['package_id']}/{row['segment_id']}"
            )
        if status == "unresolved" and row["locus_id"]:
            raise ValueError(
                f"unresolved material names a locus: {row['package_id']}/{row['segment_id']}"
            )
        start = _integer(row["start"], f"{row['package_id']}/{row['segment_id']}.start")
        end = _integer(row["end"], f"{row['package_id']}/{row['segment_id']}.end")
        if end <= start:
            raise ValueError(f"non-positive material interval: {row['package_id']}/{row['segment_id']}")
        parsed = dict(row)
        parsed["_start"] = str(start)
        parsed["_end"] = str(end)
        by_package[row["package_id"]].append(parsed)
    return by_package


def _project_eligible_atom(
    atom: dict[str, str], materials: list[dict[str, str]]
) -> dict[str, str]:
    atom_start = _integer(atom["start0"], f"{atom['atom_id']}.start0")
    atom_end = _integer(atom["end0"], f"{atom['atom_id']}.end0")
    if atom_end <= atom_start:
        raise ValueError(f"non-positive atom interval: {atom['atom_id']}")

    assigned_rows = [
        row
        for row in materials
        if row["locus_assignment_status"] == "assigned"
        and row["seqid"] == atom["seqid"]
        and _overlap(
            atom_start,
            atom_end,
            int(row["_start"]),
            int(row["_end"]),
        )
        > 0
    ]
    unresolved_rows = [
        row
        for row in materials
        if row["locus_assignment_status"] == "unresolved"
        and row["seqid"] == atom["seqid"]
        and _overlap(
            atom_start,
            atom_end,
            int(row["_start"]),
            int(row["_end"]),
        )
        > 0
    ]
    segment_ids = ",".join(sorted(row["segment_id"] for row in assigned_rows))

    atom_length = atom_end - atom_start
    assigned_intervals = [
        (
            max(atom_start, int(row["_start"])),
            min(atom_end, int(row["_end"])),
        )
        for row in assigned_rows
    ]
    unresolved_intervals = [
        (
            max(atom_start, int(row["_start"])),
            min(atom_end, int(row["_end"])),
        )
        for row in unresolved_rows
    ]
    assigned_support = _union_length(assigned_intervals)
    unresolved_support = _union_length(unresolved_intervals)
    total_support = assigned_support + unresolved_support

    assignment = "unresolved"
    assigned_locus_id = ""
    if total_support * 2 < atom_length:
        assignment = "unassigned"
    elif assigned_rows:
        intervals_by_locus: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for row in assigned_rows:
            start = max(atom_start, int(row["_start"]))
            end = min(atom_end, int(row["_end"]))
            intervals_by_locus[row["locus_id"]].append((start, end))

        coverage_by_locus = {
            locus_id: _union_length(intervals)
            for locus_id, intervals in intervals_by_locus.items()
        }
        ranked = sorted(
            coverage_by_locus.items(),
            key=lambda item: (-item[1], item[0]),
        )
        top_locus, top_coverage = ranked[0]
        second_coverage = ranked[1][1] if len(ranked) > 1 else 0
        if (
            top_coverage * 10 >= total_support * 9
            and second_coverage * 10 <= total_support
        ):
            assignment = "unique"
            assigned_locus_id = top_locus
        elif sum(coverage >= atom_length * 0.2 for coverage in coverage_by_locus.values()) >= 2:
            assignment = "mixed"

    return {
        "package_id": atom["package_id"],
        "atom_id": atom["atom_id"],
        "seqid": atom["seqid"],
        "start": atom["start0"],
        "end": atom["end0"],
        "assignment": assignment,
        "assigned_locus_id": assigned_locus_id,
        "assigned_segment_ids": segment_ids,
        "projection_eligibility": "eligible",
    }


def project_atoms(
    material_rows: list[dict[str, str]], atom_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    materials_by_package = _material_rows_by_package(material_rows)
    projected: list[dict[str, str]] = []
    for atom in atom_rows:
        censored = atom["package_censored"]
        if censored not in {"0", "1"}:
            raise ValueError(f"invalid package_censored: {atom['atom_id']}/{censored}")
        if censored == "1":
            projected.append(
                {
                    "package_id": atom["package_id"],
                    "atom_id": atom["atom_id"],
                    "seqid": atom["seqid"],
                    "start": atom["start0"],
                    "end": atom["end0"],
                    "assignment": "",
                    "assigned_locus_id": "",
                    "assigned_segment_ids": "",
                    "projection_eligibility": "package_censored",
                }
            )
        else:
            projected.append(
                _project_eligible_atom(atom, materials_by_package.get(atom["package_id"], []))
            )
    return projected


def write_projection(
    material_segments_path: Path, package_atoms_path: Path, output_path: Path
) -> None:
    material_fields, material_rows = read_tsv(material_segments_path)
    atom_fields, atom_rows = read_tsv(package_atoms_path)
    _require_fields(material_segments_path, material_fields, MATERIAL_FIELDS)
    _require_fields(package_atoms_path, atom_fields, ATOM_FIELDS)
    projected = project_atoms(material_rows, atom_rows)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=OUTPUT_FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(projected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-segments", type=Path, required=True)
    parser.add_argument("--package-atoms", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_projection(args.material_segments, args.package_atoms, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
