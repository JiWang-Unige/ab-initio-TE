#!/usr/bin/env python3
"""Global consensus-collinearity partition with immutable, exactly-once leaves."""

from __future__ import annotations

import argparse
import collections
import random
from pathlib import Path

from common import read_json, read_tsv, stable_token, write_tsv


PARENT_FIELDS = ["parent_id", "seqid", "start0", "end0", "consensus_id", "consensus_strand", "child_leaf_ids", "child_count", "partition_kind"]
ASSIGNMENT_FIELDS = ["leaf_id", "parent_id", "mapping_status", "immutable", "partition_kind"]


def evidence_for_public_leaves(public_rows: list[dict[str, str]], evidence_rows: list[dict[str, str]], shuffle_seed: int | None) -> dict[str, dict[str, str]]:
    public_ids = [row["leaf_id"] for row in public_rows]
    evidence = {row["leaf_id"]: dict(row) for row in evidence_rows}
    if set(evidence) != set(public_ids):
        raise ValueError("public/evidence leaf IDs differ")
    if shuffle_seed is None:
        return evidence
    payloads = []
    for leaf_id in sorted(public_ids):
        payload = {key: value for key, value in evidence[leaf_id].items() if key != "leaf_id"}
        payloads.append(payload)
    random.Random(shuffle_seed).shuffle(payloads)
    return {leaf_id: {"leaf_id": leaf_id, **payload} for leaf_id, payload in zip(sorted(public_ids), payloads)}


def compatible(left: dict[str, str], right: dict[str, str], maximum_overlap_fraction: float) -> bool:
    if left["seqid"] != right["seqid"] or left["consensus_id"] != right["consensus_id"] or left["consensus_strand"] != right["consensus_strand"]:
        return False
    if int(left["start0"]) >= int(right["start0"]):
        return False
    left_start, left_end = int(left["consensus_start0"]), int(left["consensus_end0"])
    right_start, right_end = int(right["consensus_start0"]), int(right["consensus_end0"])
    allowance = int(maximum_overlap_fraction * min(left_end - left_start, right_end - right_start))
    if left["consensus_strand"] == "+":
        return right_start + allowance >= left_end
    return right_end - allowance <= left_start


def maximum_matching(nodes: list[dict[str, str]], maximum_overlap_fraction: float) -> dict[int, int]:
    """Deterministic Kuhn matching yields a minimum path cover on the DAG."""
    adjacency = {
        i: [j for j in range(i + 1, len(nodes)) if compatible(nodes[i], nodes[j], maximum_overlap_fraction)]
        for i in range(len(nodes))
    }
    matched_right: dict[int, int] = {}

    def augment(left: int, seen: set[int]) -> bool:
        for right in adjacency[left]:
            if right in seen:
                continue
            seen.add(right)
            if right not in matched_right or augment(matched_right[right], seen):
                matched_right[right] = left
                return True
        return False

    for left in range(len(nodes)):
        augment(left, set())
    return {left: right for right, left in matched_right.items()}


def partition(public_rows: list[dict[str, str]], evidence_rows: list[dict[str, str]], params: dict, partition_kind: str, shuffle_seed: int | None = None) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    evidence = evidence_for_public_leaves(public_rows, evidence_rows, shuffle_seed)
    combined = []
    for public in public_rows:
        row = {**public, **evidence[public["leaf_id"]]}
        combined.append(row)
    mapped = [row for row in combined if row["mapping_status"] == "MAPPED"]
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = collections.defaultdict(list)
    for row in mapped:
        groups[(row["seqid"], row["consensus_id"], row["consensus_strand"])].append(row)

    paths: list[list[dict[str, str]]] = []
    assigned: set[str] = set()
    for key in sorted(groups):
        nodes = sorted(groups[key], key=lambda row: (int(row["start0"]), int(row["end0"]), row["leaf_id"]))
        successors = maximum_matching(nodes, float(params["maximum_consensus_overlap_fraction"]))
        predecessors = {right: left for left, right in successors.items()}
        for start in [index for index in range(len(nodes)) if index not in predecessors]:
            path = []
            current = start
            while True:
                path.append(nodes[current])
                if current not in successors:
                    break
                current = successors[current]
            paths.append(path)
            assigned.update(row["leaf_id"] for row in path)
    for row in combined:
        if row["leaf_id"] not in assigned:
            paths.append([row])

    parents: list[dict[str, object]] = []
    assignments: list[dict[str, object]] = []
    for path in paths:
        child_ids = sorted(row["leaf_id"] for row in path)
        parent_id = "parent_" + stable_token(partition_kind, *child_ids)
        mapped_path = [row for row in path if row["mapping_status"] == "MAPPED"]
        parents.append({
            "parent_id": parent_id,
            "seqid": path[0]["seqid"],
            "start0": min(int(row["start0"]) for row in path),
            "end0": max(int(row["end0"]) for row in path),
            "consensus_id": mapped_path[0]["consensus_id"] if mapped_path else "",
            "consensus_strand": mapped_path[0]["consensus_strand"] if mapped_path else "",
            "child_leaf_ids": ",".join(child_ids),
            "child_count": len(child_ids),
            "partition_kind": partition_kind,
        })
        for row in path:
            assignments.append({
                "leaf_id": row["leaf_id"], "parent_id": parent_id,
                "mapping_status": row["mapping_status"], "immutable": "true", "partition_kind": partition_kind,
            })
    if len(assignments) != len(public_rows) or len({row["leaf_id"] for row in assignments}) != len(public_rows):
        raise AssertionError("leaf retention/exactly-once invariant failed")
    parents.sort(key=lambda row: (str(row["seqid"]), int(row["start0"]), str(row["parent_id"])))
    assignments.sort(key=lambda row: str(row["leaf_id"]))
    return parents, assignments


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--public-leaves", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--parents-out", required=True, type=Path)
    parser.add_argument("--assignments-out", required=True, type=Path)
    parser.add_argument("--partition-kind", required=True, choices=["CONSENSUS_COLLINEARITY", "EVIDENCE_SHUFFLE_NULL"])
    parser.add_argument("--shuffle-seed", type=int)
    args = parser.parse_args()
    config = read_json(args.config)
    parents, assignments = partition(read_tsv(args.public_leaves), read_tsv(args.evidence), config["global_partition"], args.partition_kind, args.shuffle_seed)
    write_tsv(args.parents_out, parents, PARENT_FIELDS)
    write_tsv(args.assignments_out, assignments, ASSIGNMENT_FIELDS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
