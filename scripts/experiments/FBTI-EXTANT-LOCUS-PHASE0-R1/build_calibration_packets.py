#!/usr/bin/env python3
"""Build P3-blind evidence packets for the frozen calibration packages.

The coordinator manifest retains the frozen package mapping.  Each packet
contains only its exact assembly sequence, package coordinates, derived
context fields, and the matching raw FlyBase GFF3 records.  Canonical P3 atoms
are intentionally not read or written here.
"""

from __future__ import annotations

import argparse
import csv
import gzip
from collections import Counter, defaultdict
from pathlib import Path


PACKAGE_FIELDS = {
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
CONTEXT_FIELDS = {"package_id", "feature_id", "seqid", "start0", "end0", "strand"}
PACKET_MANIFEST_FIELDS = [
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
]
PACKET_FIELDS = [
    "packet_id",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
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


def _integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer for {label}: {value!r}") from error


def _feature_ids(value: str, package_id: str) -> list[str]:
    feature_ids = [feature_id.strip() for feature_id in value.split(",")]
    if not feature_ids or any(not feature_id for feature_id in feature_ids):
        raise ValueError(f"empty focal feature ID in package: {package_id}")
    if len(set(feature_ids)) != len(feature_ids):
        raise ValueError(f"duplicate focal feature ID in package: {package_id}")
    return feature_ids


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
        assembly_id = row["assembly_id"]
        if not role or not seqid or not assembly_id:
            raise ValueError(f"incomplete package identity: {package_id}")
        if unit_type not in {"S0", "S1"}:
            raise ValueError(f"unexpected unit_type for package {package_id}: {unit_type}")
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
                "source": row,
                "package_id": package_id,
                "role": role,
                "role_rank": _integer(row["role_rank"], f"{package_id}.role_rank"),
                "unit_type": unit_type,
                "hard_cell": row["hard_cell"],
                "assembly_id": assembly_id,
                "seqid": seqid,
                "core_start0": core_start,
                "core_end0": core_end,
                "package_start0": package_start,
                "package_end0": package_end,
                "feature_ids": _feature_ids(row["feature_ids"], package_id),
            }
        )
    return packages


def read_context(path: Path) -> tuple[list[str], dict[str, list[dict[str, object]]]]:
    fields, rows = read_tsv(path)
    if not CONTEXT_FIELDS.issubset(fields):
        raise ValueError(f"context fields must include {sorted(CONTEXT_FIELDS)}")
    if "packet_id" in fields:
        raise ValueError("context features contain reserved packet_id column")
    by_package: dict[str, list[dict[str, object]]] = defaultdict(list)
    for line_number, row in enumerate(rows, start=2):
        package_id = row["package_id"]
        feature_id = row["feature_id"]
        if not package_id or not feature_id or not row["seqid"]:
            raise ValueError(f"incomplete context row at line {line_number}")
        start = _integer(row["start0"], f"{feature_id}.start0")
        end = _integer(row["end0"], f"{feature_id}.end0")
        if start < 0 or end <= start:
            raise ValueError(f"invalid context interval: {feature_id}")
        if "start1" in fields or "end1" in fields:
            if "start1" not in fields or "end1" not in fields:
                raise ValueError("context features must include both start1 and end1")
            start1 = _integer(row["start1"], f"{feature_id}.start1")
            end1 = _integer(row["end1"], f"{feature_id}.end1")
            if start1 != start + 1 or end1 != end:
                raise ValueError(f"context 1-based coordinates disagree: {feature_id}")
        by_package[package_id].append(
            {"source": row, "feature_id": feature_id, "seqid": row["seqid"], "start": start, "end": end}
        )
    return fields, by_package


def select_calibration(packages: list[dict[str, object]]) -> list[dict[str, object]]:
    calibration = [package for package in packages if package["role"] == "calibration"]
    if len(calibration) != 12:
        raise ValueError(f"expected 12 calibration packages, got {len(calibration)}")
    if Counter(str(package["unit_type"]) for package in calibration) != Counter({"S0": 6, "S1": 6}):
        raise ValueError("calibration packages must contain 6 S0 and 6 S1 packages")
    ranks = sorted(int(package["role_rank"]) for package in calibration)
    if ranks != list(range(1, 13)):
        raise ValueError("calibration role_rank must be exactly 1..12")
    s0_cells = {str(package["hard_cell"]) for package in calibration if package["unit_type"] == "S0"}
    if s0_cells != {"S0-L1", "S0-L2", "S0-L3", "S0-L4"}:
        raise ValueError("calibration S0 packages must cover all four hard cells")
    s1_counts = Counter(str(package["hard_cell"]) for package in calibration if package["unit_type"] == "S1")
    if s1_counts != Counter({"S1-C1": 2, "S1-C2": 2, "S1-C3": 2}):
        raise ValueError("calibration S1 packages must contain two packages per hard cell")
    return sorted(calibration, key=lambda package: int(package["role_rank"]))


def _overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start < right_end and right_start < left_end


def validate_context(
    calibration_packages: list[dict[str, object]],
    all_packages: list[dict[str, object]],
    context_by_package: dict[str, list[dict[str, object]]],
) -> dict[str, list[dict[str, object]]]:
    all_package_ids = {str(package["package_id"]) for package in all_packages}
    package_by_id = {str(package["package_id"]): package for package in all_packages}
    for package_id in context_by_package:
        if package_id not in all_package_ids:
            raise ValueError(f"context references unknown package: {package_id}")

    context_owner: dict[str, str] = {}
    for package_id, rows in context_by_package.items():
        package = package_by_id.get(package_id)
        if package is None:
            continue
        package_seqid = str(package["seqid"])
        package_start = int(package["package_start0"])
        package_end = int(package["package_end0"])
        seen_features: set[str] = set()
        for record in rows:
            feature_id = str(record["feature_id"])
            if feature_id in seen_features:
                raise ValueError(f"duplicate context feature in package: {package_id}/{feature_id}")
            seen_features.add(feature_id)
            if str(record["seqid"]) != package_seqid:
                raise ValueError(f"context feature crosses package contig: {package_id}/{feature_id}")
            if not _overlap(int(record["start"]), int(record["end"]), package_start, package_end):
                raise ValueError(f"context feature does not overlap package: {package_id}/{feature_id}")
            previous_package = context_owner.get(feature_id)
            if previous_package is not None and previous_package != package_id:
                raise ValueError(f"truth context feature enters multiple packages: {feature_id}")
            context_owner[feature_id] = package_id

    selected_context: dict[str, list[dict[str, object]]] = {}
    for package in calibration_packages:
        package_id = str(package["package_id"])
        rows = context_by_package.get(package_id, [])
        if not rows:
            raise ValueError(f"missing context rows for calibration package: {package_id}")
        focal_ids = {str(feature_id) for feature_id in package["feature_ids"]}
        observed_ids = {str(record["feature_id"]) for record in rows}
        if not focal_ids.issubset(observed_ids):
            missing = sorted(focal_ids - observed_ids)[0]
            raise ValueError(f"focal feature missing from context: {package_id}/{missing}")
        if package["unit_type"] == "S1" and len(focal_ids) < 2:
            raise ValueError(f"S1 package has fewer than two focal features: {package_id}")
        selected_context[package_id] = rows
    return selected_context


def validate_package_intervals(packages: list[dict[str, object]]) -> None:
    ordered = sorted(
        packages,
        key=lambda package: (
            str(package["seqid"]),
            int(package["package_start0"]),
            int(package["package_end0"]),
            str(package["package_id"]),
        ),
    )
    previous_by_seqid: dict[str, tuple[int, str]] = {}
    for package in ordered:
        package_id = str(package["package_id"])
        seqid = str(package["seqid"])
        start = int(package["package_start0"])
        end = int(package["package_end0"])
        previous = previous_by_seqid.get(seqid)
        if previous is not None and start < previous[0]:
            raise ValueError(f"selected packages overlap: {previous[1]} and {package_id}")
        if previous is None or end > previous[0]:
            previous_by_seqid[seqid] = (end, package_id)


def _gff_feature_id(attributes: str) -> str | None:
    ids = []
    for item in attributes.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key == "ID":
            ids.append(value)
    if len(ids) > 1:
        raise ValueError("FlyBase GFF3 feature has multiple ID attributes")
    return ids[0] if ids else None


def read_flybase_gff(
    path: Path,
    context_by_feature: dict[str, dict[str, object]],
    feature_to_package: dict[str, str],
) -> dict[str, list[str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    raw_by_package: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) != 9:
                raise ValueError(f"invalid GFF3 field count at line {line_number}")
            if fields[1] != "FlyBase" or fields[2] != "transposable_element":
                continue
            feature_id = _gff_feature_id(fields[8])
            if feature_id is None or not feature_id.startswith("FBti"):
                continue
            if feature_id not in context_by_feature:
                continue
            if feature_id in seen:
                raise ValueError(f"duplicate FlyBase GFF3 feature: {feature_id}")
            start1 = _integer(fields[3], f"GFF3 line {line_number}.start")
            end1 = _integer(fields[4], f"GFF3 line {line_number}.end")
            if start1 < 1 or end1 < start1:
                raise ValueError(f"invalid GFF3 interval at line {line_number}")
            context = context_by_feature[feature_id]
            context_source = context["source"]
            if (
                fields[0] != str(context["seqid"])
                or fields[6] != str(context_source["strand"])
                or start1 - 1 != int(context["start"])
                or end1 != int(context["end"])
            ):
                raise ValueError(f"FlyBase GFF3 coordinates/strand disagree: {feature_id}")
            if "start1" in context_source:
                if start1 != int(context_source["start1"]) or end1 != int(context_source["end1"]):
                    raise ValueError(f"FlyBase GFF3 1-based coordinates disagree: {feature_id}")
            seen.add(feature_id)
            raw_by_package[feature_to_package[feature_id]].append(line)

    missing = sorted(set(context_by_feature) - seen)
    if missing:
        raise ValueError(f"missing FlyBase GFF3 feature: {missing[0]}")
    return raw_by_package


def read_fasta(path: Path) -> dict[str, str]:
    opener = gzip.open if path.suffix == ".gz" else open
    sequences: dict[str, str] = {}
    name: str | None = None
    chunks: list[str] = []
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    sequences[name] = "".join(chunks)
                name = line[1:].split()[0]
                if not name or name in sequences:
                    raise ValueError(f"invalid or duplicate FASTA contig: {name}")
                chunks = []
            else:
                if name is None:
                    raise ValueError("FASTA sequence before first header")
                chunks.append(line)
    if name is None:
        raise ValueError(f"empty FASTA: {path}")
    sequences[name] = "".join(chunks)
    return sequences


def _manifest_row(package: dict[str, object], packet_id: str) -> dict[str, str]:
    return {
        "packet_id": packet_id,
        "package_id": str(package["package_id"]),
        "role": str(package["role"]),
        "role_rank": str(package["role_rank"]),
        "unit_type": str(package["unit_type"]),
        "hard_cell": str(package["hard_cell"]),
        "assembly_id": str(package["assembly_id"]),
        "seqid": str(package["seqid"]),
        "core_start0": str(package["core_start0"]),
        "core_end0": str(package["core_end0"]),
        "package_start0": str(package["package_start0"]),
        "package_end0": str(package["package_end0"]),
        "feature_ids": ",".join(str(feature_id) for feature_id in package["feature_ids"]),
    }


def _packet_row(package: dict[str, object], packet_id: str) -> dict[str, str]:
    return {
        "packet_id": packet_id,
        "assembly_id": str(package["assembly_id"]),
        "seqid": str(package["seqid"]),
        "core_start0": str(package["core_start0"]),
        "core_end0": str(package["core_end0"]),
        "package_start0": str(package["package_start0"]),
        "package_end0": str(package["package_end0"]),
    }


def _write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_sequence(path: Path, packet_id: str, package: dict[str, object], sequence: str) -> None:
    header = (
        f">{packet_id} {package['assembly_id']}:{package['seqid']}:"
        f"{package['package_start0']}-{package['package_end0']}\n"
    )
    lines = [sequence[index : index + 60] for index in range(0, len(sequence), 60)]
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def _write_raw_gff(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_calibration_packets(
    packages_path: Path,
    context_path: Path,
    assembly_path: Path,
    flybase_gff_path: Path,
    output_dir: Path,
) -> None:
    packages = read_packages(packages_path)
    validate_package_intervals(packages)
    calibration = select_calibration(packages)
    context_fields, context_by_package = read_context(context_path)
    selected_context = validate_context(calibration, packages, context_by_package)
    context_by_feature = {
        str(record["feature_id"]): record
        for rows in selected_context.values()
        for record in rows
    }
    feature_to_package = {
        feature_id: package_id
        for package_id, rows in selected_context.items()
        for feature_id in (str(record["feature_id"]) for record in rows)
    }
    raw_by_package = read_flybase_gff(
        flybase_gff_path, context_by_feature, feature_to_package
    )
    sequences = read_fasta(assembly_path)
    if len(set(str(package["assembly_id"]) for package in calibration)) != 1:
        raise ValueError("calibration packages use multiple assembly IDs")

    prepared: list[tuple[str, dict[str, object], list[dict[str, object]], str, list[str]]] = []
    for package in calibration:
        packet_id = f"CALIB-{int(package['role_rank']):02d}"
        seqid = str(package["seqid"])
        if seqid not in sequences:
            raise ValueError(f"package contig missing from assembly: {package['package_id']}/{seqid}")
        start = int(package["package_start0"])
        end = int(package["package_end0"])
        sequence = sequences[seqid][start:end]
        if len(sequence) != end - start:
            raise ValueError(f"package interval outside assembly: {package['package_id']}")
        package_id = str(package["package_id"])
        prepared.append(
            (
                packet_id,
                package,
                selected_context[package_id],
                sequence,
                raw_by_package[package_id],
            )
        )

    output_dir.mkdir(parents=True, exist_ok=False)
    packet_root = output_dir / "packets"
    packet_root.mkdir()
    _write_tsv(
        output_dir / "packet_manifest.tsv",
        PACKET_MANIFEST_FIELDS,
        [_manifest_row(package, packet_id) for packet_id, package, _, _, _ in prepared],
    )

    packet_context_fields = [
        "packet_id",
        *[
            field
            for field in context_fields
            if field not in {"package_id", "header_md5"}
        ],
    ]
    for packet_id, package, context_rows, sequence, raw_lines in prepared:
        packet_dir = packet_root / packet_id
        packet_dir.mkdir()
        _write_tsv(packet_dir / "packet.tsv", PACKET_FIELDS, [_packet_row(package, packet_id)])
        _write_tsv(
            packet_dir / "context_features.tsv",
            packet_context_fields,
            [
                {
                    "packet_id": packet_id,
                    **{
                        field: str(record["source"][field])
                        for field in context_fields
                        if field not in {"package_id", "header_md5"}
                    },
                }
                for record in context_rows
            ],
        )
        _write_sequence(packet_dir / "sequence.fa", packet_id, package, sequence)
        _write_raw_gff(packet_dir / "raw_flybase_features.gff3", raw_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", "--selected-packages", dest="packages", type=Path, required=True)
    parser.add_argument("--context-features", type=Path, required=True)
    parser.add_argument("--assembly-fasta", type=Path, required=True)
    parser.add_argument("--flybase-gff", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_calibration_packets(
        args.packages,
        args.context_features,
        args.assembly_fasta,
        args.flybase_gff,
        args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
