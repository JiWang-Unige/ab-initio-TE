#!/usr/bin/env python3
"""Build a public leaf bundle and a physically separate evaluator-truth bundle."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

from common import iter_fasta, read_json, stable_token, write_fasta, write_tsv, atomic_write_json


PUBLIC_FIELDS = ["leaf_id", "seqid", "start0", "end0", "length_bp", "sequence_sha256"]
TRUTH_FIELDS = [
    "leaf_id", "seqid", "rm_id", "truth_group_id", "truth_parent_start0", "truth_parent_end0",
    "class_root", "repeat_name", "truth_strand", "overlap_marker", "row_count_bin",
]


def row_count_bin(count: int, bins: list[list[object]]) -> str:
    for lower, upper, label in bins:
        if int(lower) <= count <= int(upper):
            return str(label)
    raise ValueError(f"row count {count} is outside frozen bins")


def load_groups(annotation_path: Path, sampling: dict) -> dict[tuple[str, str], list[dict[str, str]]]:
    allowed = set(sampling["eligible_primary_contigs"])
    groups: dict[tuple[str, str], list[dict[str, str]]] = collections.defaultdict(list)
    import csv
    with annotation_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["seqid"] in allowed:
                groups[(row["seqid"], row["rm_id"])].append(row)
    minimum = int(sampling["minimum_rows_per_truth_group"])
    maximum = int(sampling["maximum_rows_per_truth_group"])
    return {key: rows for key, rows in groups.items() if minimum <= len(rows) <= maximum}


def select_groups(groups: dict[tuple[str, str], list[dict[str, str]]], sampling: dict) -> list[tuple[tuple[str, str], list[dict[str, str]], str]]:
    seed = int(sampling["seed"])
    strata: dict[tuple[str, str], list[tuple[tuple[str, str], list[dict[str, str]], str]]] = collections.defaultdict(list)
    for key, rows in groups.items():
        roots = {row["class_root"] for row in rows}
        if len(roots) != 1:
            raise ValueError(f"truth group has conflicting class_root: {key}")
        count_bin = row_count_bin(len(rows), sampling["row_count_bins"])
        strata[(next(iter(roots)), count_bin)].append((key, rows, count_bin))
    cap = int(sampling["maximum_groups_per_stratum"])
    selected = []
    for stratum in sorted(strata):
        ranked = sorted(strata[stratum], key=lambda item: stable_token(seed, item[0][0], item[0][1], length=64))
        selected.extend(ranked[:cap])
    global_cap = int(sampling["maximum_groups_total"])
    return sorted(selected, key=lambda item: stable_token(seed, item[0][0], item[0][1], length=64))[:global_cap]


def build_bundle(annotation_path: Path, assembly_path: Path, out_dir: Path, sampling: dict) -> dict:
    selected = select_groups(load_groups(annotation_path, sampling), sampling)
    needed_contigs = {key[0] for key, _, _ in selected}
    assembly = {name: seq for name, seq in iter_fasta(assembly_path) if name in needed_contigs}
    if set(assembly) != needed_contigs:
        raise ValueError(f"assembly missing contigs: {sorted(needed_contigs - set(assembly))}")

    public_rows: list[dict[str, object]] = []
    truth_rows: list[dict[str, object]] = []
    fasta_records: list[tuple[str, str]] = []
    seed = int(sampling["seed"])
    for (seqid, rm_id), rows, count_bin in selected:
        parent_start = min(int(row["start0"]) for row in rows)
        parent_end = max(int(row["end0"]) for row in rows)
        truth_group_id = "truth_" + stable_token("rice", seqid, rm_id)
        for row in sorted(rows, key=lambda value: (int(value["start0"]), int(value["end0"]), int(value["source_line"]))):
            start0, end0 = int(row["start0"]), int(row["end0"])
            if not (0 <= start0 < end0 <= len(assembly[seqid])):
                raise ValueError(f"invalid coordinates in source line {row['source_line']}")
            sequence = assembly[seqid][start0:end0].upper()
            leaf_id = "leaf_" + stable_token(seed, seqid, row["source_line"])
            public_rows.append({
                "leaf_id": leaf_id, "seqid": seqid, "start0": start0, "end0": end0,
                "length_bp": end0 - start0, "sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
            })
            fasta_records.append((leaf_id, sequence))
            truth_rows.append({
                "leaf_id": leaf_id, "seqid": seqid, "rm_id": row["rm_id"],
                "truth_group_id": truth_group_id, "truth_parent_start0": parent_start,
                "truth_parent_end0": parent_end, "class_root": row["class_root"],
                "repeat_name": row["repeat_name"], "truth_strand": row["strand"],
                "overlap_marker": row["overlap_marker"], "row_count_bin": count_bin,
            })

    public_rows.sort(key=lambda row: (str(row["seqid"]), int(row["start0"]), str(row["leaf_id"])))
    truth_rows.sort(key=lambda row: str(row["leaf_id"]))
    fasta_by_id = dict(fasta_records)
    write_tsv(out_dir / "public" / "leaves.tsv", public_rows, PUBLIC_FIELDS)
    write_fasta(out_dir / "public" / "leaves.fa", ((str(row["leaf_id"]), fasta_by_id[str(row["leaf_id"])]) for row in public_rows))
    write_tsv(out_dir / "evaluator_only" / "truth.tsv", truth_rows, TRUTH_FIELDS)
    strata = collections.Counter((str(row["class_root"]), str(row["row_count_bin"])) for row in truth_rows)
    report = {
        "schema_version": "FRAG-COLLINEARITY-SAMPLE-1.0.0",
        "truth_tier": "T1",
        "unlabelled_space_is_negative": False,
        "selected_truth_group_count": len(selected),
        "public_leaf_count": len(public_rows),
        "stratum_leaf_counts": {"|".join(key): value for key, value in sorted(strata.items())},
        "assembler_forbidden_fields": ["rm_id", "truth_group_id", "truth_parent_start0", "truth_parent_end0", "class_root", "repeat_name", "truth_strand", "overlap_marker"],
    }
    atomic_write_json(out_dir / "sample_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--annotation", required=True, type=Path)
    parser.add_argument("--assembly", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    config = read_json(args.config)
    build_bundle(args.annotation, args.assembly, args.out_dir, config["sampling"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
