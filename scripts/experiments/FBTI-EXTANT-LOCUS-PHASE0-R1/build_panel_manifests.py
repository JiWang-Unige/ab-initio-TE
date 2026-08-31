#!/usr/bin/env python3
"""Build the selected-panel sidecars used by annotation and Gate O.

The sidecars retain the source FlyBase and canonical P3 fields and add only
the package join key plus the atom boundary relationship.  Coordinates are
zero-based, half-open throughout.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


PACKAGE_FIELDS = {
    "package_id",
    "role",
    "unit_type",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
    "feature_ids",
}
TRUTH_REQUIRED_FIELDS = {"feature_id", "seqid", "start0", "end0"}
ATOM_REQUIRED_FIELDS = {"seqid", "start", "end"}
ATOM_SIDEcar_FIELDS = {"package_id", "atom_id", "overlap_role", "package_censored"}


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        if fields is None:
            raise ValueError(f"missing TSV header: {path}")
        if len(set(fields)) != len(fields):
            raise ValueError(f"duplicate TSV columns: {path}")
        return fields, list(reader)


def _integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer for {label}: {value!r}") from error


def _feature_ids(value: str, package_id: str) -> list[str]:
    ids = [feature_id.strip() for feature_id in value.split(",")]
    if not ids or any(not feature_id for feature_id in ids):
        raise ValueError(f"empty focal feature ID in package: {package_id}")
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate focal feature ID in package: {package_id}")
    return ids


def read_packages(path: Path) -> list[dict[str, object]]:
    fields, rows = read_tsv(path)
    if not PACKAGE_FIELDS.issubset(fields):
        raise ValueError(f"packages fields must include {sorted(PACKAGE_FIELDS)}")
    packages: list[dict[str, object]] = []
    seen: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        package_id = row["package_id"]
        if not package_id:
            raise ValueError(f"empty package_id at line {line_number}")
        if package_id in seen:
            raise ValueError(f"duplicate package_id: {package_id}")
        seen.add(package_id)
        role = row["role"]
        unit_type = row["unit_type"]
        seqid = row["seqid"]
        if not role:
            raise ValueError(f"empty package role: {package_id}")
        if unit_type not in {"S0", "S1"}:
            raise ValueError(f"unexpected unit_type for package {package_id}: {unit_type}")
        if not seqid:
            raise ValueError(f"empty package seqid: {package_id}")
        core_start = _integer(row["core_start0"], f"{package_id}.core_start0")
        core_end = _integer(row["core_end0"], f"{package_id}.core_end0")
        package_start = _integer(row["package_start0"], f"{package_id}.package_start0")
        package_end = _integer(row["package_end0"], f"{package_id}.package_end0")
        if package_start < 0 or package_end <= package_start:
            raise ValueError(f"invalid package interval: {package_id}")
        if core_start < package_start or core_end > package_end or core_end <= core_start:
            raise ValueError(f"core interval is not contained in package: {package_id}")
        packages.append(
            {
                "package_id": package_id,
                "role": role,
                "unit_type": unit_type,
                "seqid": seqid,
                "core_start": core_start,
                "core_end": core_end,
                "package_start": package_start,
                "package_end": package_end,
                "feature_ids": _feature_ids(row["feature_ids"], package_id),
            }
        )
    return packages


def read_truth(path: Path) -> tuple[list[str], list[dict[str, object]]]:
    fields, rows = read_tsv(path)
    if not TRUTH_REQUIRED_FIELDS.issubset(fields):
        raise ValueError(f"truth fields must include {sorted(TRUTH_REQUIRED_FIELDS)}")
    if "package_id" in fields:
        raise ValueError("truth metadata cannot contain reserved package_id column")
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        feature_id = row["feature_id"]
        if not feature_id:
            raise ValueError(f"empty truth feature_id at line {line_number}")
        if feature_id in seen:
            raise ValueError(f"duplicate truth feature_id: {feature_id}")
        seen.add(feature_id)
        seqid = row["seqid"]
        start = _integer(row["start0"], f"{feature_id}.start0")
        end = _integer(row["end0"], f"{feature_id}.end0")
        if not seqid or start < 0 or end <= start:
            raise ValueError(f"invalid truth interval: {feature_id}")
        records.append(
            {
                "feature_id": feature_id,
                "seqid": seqid,
                "start": start,
                "end": end,
                "source": row,
            }
        )
    return fields, records


def read_atoms(path: Path) -> tuple[list[str], list[dict[str, object]]]:
    fields, rows = read_tsv(path)
    if not ATOM_REQUIRED_FIELDS.issubset(fields):
        raise ValueError(f"canonical P3 fields must include {sorted(ATOM_REQUIRED_FIELDS)}")
    if ATOM_SIDEcar_FIELDS.intersection(fields):
        raise ValueError("canonical P3 TSV contains reserved sidecar column")
    atoms: list[dict[str, object]] = []
    seen: set[tuple[str, int, int]] = set()
    for line_number, row in enumerate(rows, start=2):
        seqid = row["seqid"]
        start = _integer(row["start"], f"P3 line {line_number}.start")
        end = _integer(row["end"], f"P3 line {line_number}.end")
        key = (seqid, start, end)
        if key in seen:
            raise ValueError(f"duplicate canonical P3 coordinates: {seqid}:{start}:{end}")
        seen.add(key)
        if not seqid or start < 0 or end <= start:
            raise ValueError(f"invalid canonical P3 interval at line {line_number}")
        atoms.append({"seqid": seqid, "start": start, "end": end, "source": row})
    return fields, atoms


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def truth_components(records: list[dict[str, object]]) -> dict[str, frozenset[str]]:
    by_seqid: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        by_seqid[str(record["seqid"])].append(index)
    union_find = UnionFind(len(records))
    for indices in by_seqid.values():
        ordered = sorted(
            indices,
            key=lambda index: (
                int(records[index]["start"]),
                int(records[index]["end"]),
                str(records[index]["feature_id"]),
            ),
        )
        active: list[int] = []
        for index in ordered:
            start = int(records[index]["start"])
            active = [prior for prior in active if int(records[prior]["end"]) > start]
            for prior in active:
                union_find.union(index, prior)
            active.append(index)
    groups: dict[int, set[str]] = defaultdict(set)
    for index, record in enumerate(records):
        groups[union_find.find(index)].add(str(record["feature_id"]))
    result: dict[str, frozenset[str]] = {}
    for group in groups.values():
        component = frozenset(group)
        for feature_id in component:
            result[feature_id] = component
    return result


def validate_packages(
    packages: list[dict[str, object]],
    truth_by_id: dict[str, dict[str, object]],
    components: dict[str, frozenset[str]],
) -> None:
    ordered = sorted(
        packages,
        key=lambda package: (
            str(package["seqid"]),
            int(package["package_start"]),
            int(package["package_end"]),
            str(package["package_id"]),
        ),
    )
    last_by_seqid: dict[str, tuple[int, str]] = {}
    for package in ordered:
        package_id = str(package["package_id"])
        seqid = str(package["seqid"])
        start = int(package["package_start"])
        end = int(package["package_end"])
        previous = last_by_seqid.get(seqid)
        if previous is not None and start < previous[0]:
            raise ValueError(
                f"selected packages overlap: {previous[1]} and {package_id}"
            )
        if previous is None or end > previous[0]:
            last_by_seqid[seqid] = (end, package_id)

        feature_ids = set(str(feature_id) for feature_id in package["feature_ids"])
        missing = sorted(feature_ids - truth_by_id.keys())
        if missing:
            raise ValueError(f"package {package_id} references unknown truth feature: {missing[0]}")
        focal = [truth_by_id[feature_id] for feature_id in feature_ids]
        if any(str(record["seqid"]) != seqid for record in focal):
            raise ValueError(f"package focal features cross seqids: {package_id}")
        core_start = min(int(record["start"]) for record in focal)
        core_end = max(int(record["end"]) for record in focal)
        if (int(package["core_start"]), int(package["core_end"])) != (core_start, core_end):
            raise ValueError(f"package core coordinates do not match focal features: {package_id}")

        unit_type = str(package["unit_type"])
        component = components[str(next(iter(feature_ids)))]
        if unit_type == "S0":
            if len(feature_ids) != 1 or len(component) != 1:
                raise ValueError(f"S0 package is not a singleton component: {package_id}")
        elif feature_ids != set(component):
            raise ValueError(f"S1 package does not contain its complete truth component: {package_id}")


def _overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start < right_end and right_start < left_end


def _atom_role(atom_start: int, atom_end: int, package_start: int, package_end: int) -> str:
    left = atom_start < package_start
    right = atom_end > package_end
    if left and right:
        return "both_censored"
    if left:
        return "left_censored"
    if right:
        return "right_censored"
    return "contained"


def build_sidecars(
    packages_path: Path, truth_path: Path, p3_path: Path
) -> tuple[list[str], list[dict[str, str]], list[str], list[dict[str, str]]]:
    packages = read_packages(packages_path)
    truth_fields, truth_records = read_truth(truth_path)
    atom_fields, atoms = read_atoms(p3_path)
    truth_by_id = {str(record["feature_id"]): record for record in truth_records}
    components = truth_components(truth_records)
    validate_packages(packages, truth_by_id, components)

    context_rows: list[dict[str, str]] = []
    context_owner: dict[str, str] = {}
    truth_sorted = sorted(
        truth_records,
        key=lambda record: (
            str(record["seqid"]),
            int(record["start"]),
            int(record["end"]),
            str(record["feature_id"]),
        ),
    )
    for package in packages:
        package_id = str(package["package_id"])
        package_start = int(package["package_start"])
        package_end = int(package["package_end"])
        hits = [
            record
            for record in truth_sorted
            if str(record["seqid"]) == str(package["seqid"])
            and _overlap(int(record["start"]), int(record["end"]), package_start, package_end)
        ]
        hit_ids = {str(record["feature_id"]) for record in hits}
        focal_ids = set(str(feature_id) for feature_id in package["feature_ids"])
        if not focal_ids.issubset(hit_ids):
            raise ValueError(f"focal truth feature is absent from package context: {package_id}")
        for feature_id in hit_ids:
            previous_owner = context_owner.get(feature_id)
            if previous_owner is not None and previous_owner != package_id:
                raise ValueError(
                    f"truth context feature enters multiple packages: {feature_id}"
                )
            context_owner[feature_id] = package_id
        context_rows.extend(
            {"package_id": package_id, **dict(record["source"])} for record in hits
        )

    atom_rows: list[dict[str, str]] = []
    atoms_sorted = sorted(
        atoms,
        key=lambda atom: (str(atom["seqid"]), int(atom["start"]), int(atom["end"])),
    )
    for package in packages:
        package_id = str(package["package_id"])
        package_start = int(package["package_start"])
        package_end = int(package["package_end"])
        for atom in atoms_sorted:
            if str(atom["seqid"]) != str(package["seqid"]):
                continue
            atom_start = int(atom["start"])
            atom_end = int(atom["end"])
            if not _overlap(atom_start, atom_end, package_start, package_end):
                continue
            key = (str(atom["seqid"]), atom_start, atom_end)
            role = _atom_role(atom_start, atom_end, package_start, package_end)
            atom_rows.append(
                {
                    "package_id": package_id,
                    "atom_id": f"P3:{key[0]}:{key[1]}:{key[2]}",
                    "seqid": key[0],
                    "start0": str(key[1]),
                    "end0": str(key[2]),
                    "overlap_role": role,
                    "package_censored": "0" if role == "contained" else "1",
                    **{
                        field: dict(atom["source"])[field]
                        for field in atom_fields
                        if field not in {"seqid", "start", "end"}
                    },
                }
            )

    context_fields = ["package_id", *truth_fields]
    atom_output_fields = [
        "package_id",
        "atom_id",
        "seqid",
        "start0",
        "end0",
        "overlap_role",
        "package_censored",
        *[field for field in atom_fields if field not in {"seqid", "start", "end"}],
    ]
    return context_fields, context_rows, atom_output_fields, atom_rows


def write_sidecars(
    output_dir: Path,
    context_fields: list[str],
    context_rows: list[dict[str, str]],
    atom_fields: list[str],
    atom_rows: list[dict[str, str]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    for filename, fields, rows in (
        ("context_features.tsv", context_fields, context_rows),
        ("package_atoms.tsv", atom_fields, atom_rows),
    ):
        with (output_dir / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def build_panel_manifests(
    packages_path: Path, truth_path: Path, p3_path: Path, output_dir: Path
) -> None:
    context_fields, context_rows, atom_fields, atom_rows = build_sidecars(
        packages_path, truth_path, p3_path
    )
    write_sidecars(output_dir, context_fields, context_rows, atom_fields, atom_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", "--selected-packages", dest="packages", type=Path, required=True)
    parser.add_argument("--truth-metadata", type=Path, required=True)
    parser.add_argument("--p3-atoms", "--canonical-p3", dest="p3_atoms", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_panel_manifests(args.packages, args.truth_metadata, args.p3_atoms, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
