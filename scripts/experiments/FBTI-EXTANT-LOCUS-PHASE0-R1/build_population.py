#!/usr/bin/env python3
"""Build the label-blind FlyBase package population for Phase-0 Gate L.

This preflight materializes S0 coordinate-isolated FBti units and S1 complete
connected components of the FBti interval-overlap graph.  It does not sample
the annotation panel and does not assign biological locus truth.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path


FLANK_BP = 10_000
TRUTH_FIELDS = {
    "feature_id",
    "seqid",
    "start0",
    "end0",
    "strand",
    "flybase_name",
    "release",
    "species",
}
OVERLAP_FIELDS = {
    "seqid",
    "left_id",
    "left_start0",
    "left_end0",
    "right_id",
    "right_start0",
    "right_end0",
    "relationship",
}
ATOM_FIELDS = {"seqid", "start", "end"}


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


def read_truth(path: Path) -> dict[str, dict[str, object]]:
    fields, rows = read_tsv(path)
    if not TRUTH_FIELDS.issubset(fields):
        raise ValueError(f"truth fields must include {sorted(TRUTH_FIELDS)}")
    records: dict[str, dict[str, object]] = {}
    for row in rows:
        feature_id = row["feature_id"]
        if feature_id in records:
            raise ValueError(f"duplicate truth feature_id: {feature_id}")
        start = int(row["start0"])
        end = int(row["end0"])
        if start < 0 or end <= start:
            raise ValueError(f"invalid truth interval: {feature_id}")
        if row["release"] != "r6.68" or row["species"] != "Dmel":
            raise ValueError(f"unexpected release/species: {feature_id}")
        records[feature_id] = {
            "feature_id": feature_id,
            "seqid": row["seqid"],
            "start": start,
            "end": end,
            "strand": row["strand"],
            "flybase_name": row["flybase_name"],
        }
    return records


def relation(left: dict[str, object], right: dict[str, object]) -> str:
    if left["start"] == right["start"] and left["end"] == right["end"]:
        return "equal_coordinates"
    if (
        left["start"] <= right["start"] and left["end"] >= right["end"]
    ) or (
        right["start"] <= left["start"] and right["end"] >= left["end"]
    ):
        return "strict_containment"
    return "partial_overlap"


def actual_overlap_pairs(
    records: dict[str, dict[str, object]],
) -> set[tuple[str, str, str]]:
    by_seqid: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records.values():
        by_seqid[str(record["seqid"])].append(record)
    pairs: set[tuple[str, str, str]] = set()
    for seq_records in by_seqid.values():
        active: list[dict[str, object]] = []
        for current in sorted(
            seq_records,
            key=lambda row: (int(row["start"]), int(row["end"]), str(row["feature_id"])),
        ):
            active = [row for row in active if int(row["end"]) > int(current["start"])]
            for prior in active:
                left, right = sorted((str(prior["feature_id"]), str(current["feature_id"])))
                pairs.add((left, right, relation(prior, current)))
            active.append(current)
    return pairs


def read_overlap_pairs(
    path: Path, records: dict[str, dict[str, object]]
) -> set[tuple[str, str, str]]:
    fields, rows = read_tsv(path)
    if not OVERLAP_FIELDS.issubset(fields):
        raise ValueError(f"overlap fields must include {sorted(OVERLAP_FIELDS)}")
    pairs: set[tuple[str, str, str]] = set()
    for row in rows:
        left_id = row["left_id"]
        right_id = row["right_id"]
        if left_id not in records or right_id not in records:
            raise ValueError(f"overlap pair references unknown ID: {left_id}/{right_id}")
        left = records[left_id]
        right = records[right_id]
        expected_coordinates = (
            str(left["seqid"]),
            int(left["start"]),
            int(left["end"]),
            int(right["start"]),
            int(right["end"]),
        )
        observed_coordinates = (
            row["seqid"],
            int(row["left_start0"]),
            int(row["left_end0"]),
            int(row["right_start0"]),
            int(row["right_end0"]),
        )
        if observed_coordinates != expected_coordinates:
            raise ValueError(f"overlap coordinate mismatch: {left_id}/{right_id}")
        left_key, right_key = sorted((left_id, right_id))
        pairs.add((left_key, right_key, row["relationship"]))
    actual = actual_overlap_pairs(records)
    if pairs != actual:
        raise ValueError(
            f"overlap graph mismatch: provided={len(pairs)} actual={len(actual)}"
        )
    return pairs


class UnionFind:
    def __init__(self, keys: list[str]) -> None:
        self.parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def connected_components(
    records: dict[str, dict[str, object]], pairs: set[tuple[str, str, str]]
) -> list[list[str]]:
    union_find = UnionFind(list(records))
    for left, right, _ in pairs:
        union_find.union(left, right)
    groups: dict[str, list[str]] = defaultdict(list)
    for feature_id in records:
        groups[union_find.find(feature_id)].append(feature_id)
    return [sorted(group) for group in groups.values()]


def read_lengths(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("contig lengths must be a JSON object")
    return {str(key): int(value) for key, value in payload.items()}


def read_fasta_lengths(path: Path) -> dict[str, int]:
    opener = gzip.open if path.suffix == ".gz" else path.open
    lengths: dict[str, int] = {}
    name: str | None = None
    length = 0
    with opener(path, "rt", encoding="utf-8") if path.suffix == ".gz" else opener(
        "r", encoding="utf-8"
    ) as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    lengths[name] = length
                name = line[1:].split()[0]
                if not name or name in lengths:
                    raise ValueError("invalid or duplicate FASTA contig name")
                length = 0
            else:
                if name is None:
                    raise ValueError("FASTA sequence before first header")
                length += len(line.strip())
    if name is not None:
        lengths[name] = length
    return lengths


def read_atom_index(
    path: Path, lengths: dict[str, int]
) -> dict[str, tuple[list[int], list[int]]]:
    fields, rows = read_tsv(path)
    if not ATOM_FIELDS.issubset(fields):
        raise ValueError(f"atom fields must include {sorted(ATOM_FIELDS)}")
    starts: dict[str, list[int]] = defaultdict(list)
    ends: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        seqid = row["seqid"]
        start = int(row["start"])
        end = int(row["end"])
        if seqid not in lengths or start < 0 or end <= start or end > lengths[seqid]:
            raise ValueError("invalid P3 atom interval")
        starts[seqid].append(start)
        ends[seqid].append(end)
    return {
        seqid: (sorted(seq_starts), sorted(ends[seqid]))
        for seqid, seq_starts in starts.items()
    }


def count_overlaps(
    index: dict[str, tuple[list[int], list[int]]], seqid: str, start: int, end: int
) -> int:
    starts, ends = index.get(seqid, ([], []))
    return bisect_left(starts, end) - bisect_right(ends, start)


def maximum_depth(records: list[dict[str, object]]) -> int:
    events: list[tuple[int, int]] = []
    for record in records:
        events.append((int(record["start"]), 1))
        events.append((int(record["end"]), -1))
    depth = 0
    maximum = 0
    for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
        depth += delta
        maximum = max(maximum, depth)
    return maximum


def nearest_gap_by_id(
    records: dict[str, dict[str, object]], singleton_ids: set[str]
) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    by_seqid: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records.values():
        by_seqid[str(record["seqid"])].append(record)
    for seq_records in by_seqid.values():
        ordered = sorted(seq_records, key=lambda row: (int(row["start"]), int(row["end"])))
        prefix_max_end: list[int] = []
        maximum_end = -1
        for record in ordered:
            prefix_max_end.append(maximum_end)
            maximum_end = max(maximum_end, int(record["end"]))
        for index, record in enumerate(ordered):
            feature_id = str(record["feature_id"])
            if feature_id not in singleton_ids:
                continue
            gaps: list[int] = []
            if index:
                gaps.append(max(0, int(record["start"]) - prefix_max_end[index]))
            if index + 1 < len(ordered):
                gaps.append(max(0, int(ordered[index + 1]["start"]) - int(record["end"])))
            result[feature_id] = min(gaps) if gaps else None
    return result


def maximum_nonoverlap(units: list[dict[str, object]], unit_type: str | None = None) -> int:
    selected = 0
    for seqid in sorted({str(unit["seqid"]) for unit in units}):
        last_end = -1
        candidates = [
            unit
            for unit in units
            if unit["seqid"] == seqid and (unit_type is None or unit["unit_type"] == unit_type)
        ]
        for unit in sorted(candidates, key=lambda row: (int(row["package_end0"]), int(row["package_start0"]))):
            if int(unit["package_start0"]) >= last_end:
                selected += 1
                last_end = int(unit["package_end0"])
    return selected


def build_population(
    truth_path: Path,
    overlap_path: Path,
    atom_path: Path,
    lengths_path: Path,
    assembly_path: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    records = read_truth(truth_path)
    pairs = read_overlap_pairs(overlap_path, records)
    lengths = read_lengths(lengths_path)
    if len(lengths) != 1870 or sum(lengths.values()) != 143_726_002:
        raise ValueError("contig lengths are not the frozen exact r6.68 assembly")
    if lengths != read_fasta_lengths(assembly_path):
        raise ValueError("contig length mapping does not match the exact r6.68 FASTA")
    for record in records.values():
        seqid = str(record["seqid"])
        if seqid not in lengths or int(record["end"]) > lengths[seqid]:
            raise ValueError(f"truth interval outside assembly: {record['feature_id']}")
    atom_index = read_atom_index(atom_path, lengths)

    components = connected_components(records, pairs)
    singleton_ids = {component[0] for component in components if len(component) == 1}
    nearest_gaps = nearest_gap_by_id(records, singleton_ids)
    name_frequency = Counter(str(record["flybase_name"]) for record in records.values())

    raw_units: list[dict[str, object]] = []
    for component in components:
        component_records = [records[feature_id] for feature_id in component]
        seqids = {str(record["seqid"]) for record in component_records}
        if len(seqids) != 1:
            raise ValueError("overlap component crosses contigs")
        seqid = next(iter(seqids))
        core_start = min(int(record["start"]) for record in component_records)
        core_end = max(int(record["end"]) for record in component_records)
        package_start = max(0, core_start - FLANK_BP)
        package_end = min(lengths[seqid], core_end + FLANK_BP)
        raw_units.append(
            {
                "unit_type": "S0" if len(component) == 1 else "S1",
                "seqid": seqid,
                "core_start0": core_start,
                "core_end0": core_end,
                "package_start0": package_start,
                "package_end0": package_end,
                "feature_ids": ",".join(component),
                "feature_count": len(component),
                "core_length": core_end - core_start,
                "max_overlap_depth": maximum_depth(component_records),
                "p3_atoms_core": count_overlaps(atom_index, seqid, core_start, core_end),
                "p3_atoms_package": count_overlaps(atom_index, seqid, package_start, package_end),
                "nearest_fbti_gap": nearest_gaps.get(component[0]) if len(component) == 1 else None,
                "exact_name_frequency_min": min(
                    name_frequency[str(record["flybase_name"])] for record in component_records
                ),
                "exact_name_frequency_max": max(
                    name_frequency[str(record["flybase_name"])] for record in component_records
                ),
            }
        )

    units = sorted(
        raw_units,
        key=lambda row: (str(row["seqid"]), int(row["core_start0"]), int(row["core_end0"])),
    )
    counters = {"S0": 0, "S1": 0}
    for unit in units:
        unit_type = str(unit["unit_type"])
        counters[unit_type] += 1
        unit["unit_id"] = f"{unit_type}-{counters[unit_type]:05d}"

    summary: dict[str, object] = {
        "schema": "fbti_extant_locus_population_v1",
        "status": "PREFLIGHT_PASS",
        "claim_scope": "label-blind package population only; not Gate L/O/E evidence",
        "coordinate_contract": "0-based half-open",
        "flank_bp": FLANK_BP,
        "truth_records": len(records),
        "provided_overlap_pairs": len(pairs),
        "S0_units": counters["S0"],
        "S1_units": counters["S1"],
        "overlap_participating_records": sum(
            int(unit["feature_count"]) for unit in units if unit["unit_type"] == "S1"
        ),
        "p3_atoms": sum(len(starts) for starts, _ in atom_index.values()),
        "exact_name_frequency_degenerate": len(name_frequency) == len(records),
        "maximum_nonoverlap_packages_all": maximum_nonoverlap(units),
        "maximum_nonoverlap_packages_S0": maximum_nonoverlap(units, "S0"),
        "maximum_nonoverlap_packages_S1": maximum_nonoverlap(units, "S1"),
        "inputs": {
            "truth_metadata": str(truth_path),
            "overlap_pairs": str(overlap_path),
            "p3_atoms": str(atom_path),
            "contig_lengths": str(lengths_path),
            "assembly_fasta": str(assembly_path),
        },
    }
    return units, summary


def write_outputs(units: list[dict[str, object]], summary: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    columns = [
        "unit_id",
        "unit_type",
        "seqid",
        "core_start0",
        "core_end0",
        "package_start0",
        "package_end0",
        "feature_ids",
        "feature_count",
        "core_length",
        "max_overlap_depth",
        "p3_atoms_core",
        "p3_atoms_package",
        "nearest_fbti_gap",
        "exact_name_frequency_min",
        "exact_name_frequency_max",
    ]
    with (output_dir / "population.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in columns} for row in units)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth-metadata", type=Path, required=True)
    parser.add_argument("--overlap-pairs", type=Path, required=True)
    parser.add_argument("--p3-atoms", type=Path, required=True)
    parser.add_argument("--contig-lengths", type=Path, required=True)
    parser.add_argument("--assembly-fasta", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    units, summary = build_population(
        args.truth_metadata,
        args.overlap_pairs,
        args.p3_atoms,
        args.contig_lengths,
        args.assembly_fasta,
    )
    write_outputs(units, summary, args.output_dir)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
