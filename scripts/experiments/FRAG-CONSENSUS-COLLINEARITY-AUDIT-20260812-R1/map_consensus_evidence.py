#!/usr/bin/env python3
"""Map public leaf sequences to frozen consensus coordinates using fixed seed chains."""

from __future__ import annotations

import argparse
import collections
import multiprocessing
import statistics
from pathlib import Path

from common import iter_fasta, read_json, reverse_complement, write_tsv


EVIDENCE_FIELDS = [
    "leaf_id", "mapping_status", "consensus_id", "consensus_strand", "consensus_start0",
    "consensus_end0", "consensus_length", "seed_coverage", "inlier_seed_count", "second_seed_coverage",
]
_WORKER_INDEX: dict[str, list[tuple[str, int]]] | None = None
_WORKER_CONSENSUS: dict[str, str] | None = None
_WORKER_PARAMS: dict | None = None


def covered_fraction(positions: list[int], kmer_size: int, query_length: int) -> float:
    if not positions or query_length <= 0:
        return 0.0
    merged = 0
    left, right = positions[0], positions[0] + kmer_size
    for position in positions[1:]:
        next_right = position + kmer_size
        if position <= right:
            right = max(right, next_right)
        else:
            merged += right - left
            left, right = position, next_right
    merged += right - left
    return min(1.0, merged / query_length)


def build_index(consensus: dict[str, str], kmer_size: int, posting_cap: int) -> dict[str, list[tuple[str, int]]]:
    index: dict[str, list[tuple[str, int]]] = collections.defaultdict(list)
    overflow: set[str] = set()
    for consensus_id in sorted(consensus):
        sequence = consensus[consensus_id]
        for position in range(0, max(0, len(sequence) - kmer_size + 1)):
            kmer = sequence[position : position + kmer_size]
            if "N" in kmer or kmer in overflow:
                continue
            values = index[kmer]
            values.append((consensus_id, position))
            if len(values) > posting_cap:
                overflow.add(kmer)
                del index[kmer]
    return dict(index)


def orientation_candidates(query: str, orientation: str, index: dict[str, list[tuple[str, int]]], consensus: dict[str, str], params: dict) -> list[dict[str, object]]:
    kmer_size = int(params["kmer_size"])
    stride = int(params["query_stride"])
    band = int(params["diagonal_band_bp"])
    hits: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    for qpos in range(0, max(0, len(query) - kmer_size + 1), stride):
        kmer = query[qpos : qpos + kmer_size]
        for consensus_id, cpos in index.get(kmer, []):
            hits[consensus_id].append((qpos, cpos))
    candidates = []
    for consensus_id, pairs in hits.items():
        if len(pairs) < int(params["minimum_inlier_seed_count"]):
            continue
        diagonals = [cpos - qpos for qpos, cpos in pairs]
        center = statistics.median(diagonals)
        inliers = [(qpos, cpos) for qpos, cpos in pairs if abs((cpos - qpos) - center) <= band]
        unique_qpos = sorted({qpos for qpos, _ in inliers})
        coverage = covered_fraction(unique_qpos, kmer_size, len(query))
        if len(unique_qpos) < int(params["minimum_inlier_seed_count"]):
            continue
        candidates.append({
            "consensus_id": consensus_id,
            "consensus_strand": orientation,
            "consensus_start0": min(cpos for _, cpos in inliers),
            "consensus_end0": max(cpos for _, cpos in inliers) + kmer_size,
            "consensus_length": len(consensus[consensus_id]),
            "seed_coverage": coverage,
            "inlier_seed_count": len(unique_qpos),
        })
    return candidates


def map_leaf(leaf_id: str, sequence: str, index: dict[str, list[tuple[str, int]]], consensus: dict[str, str], params: dict) -> dict[str, object]:
    candidates = orientation_candidates(sequence, "+", index, consensus, params)
    candidates.extend(orientation_candidates(reverse_complement(sequence), "-", index, consensus, params))
    candidates.sort(key=lambda row: (-float(row["seed_coverage"]), -int(row["inlier_seed_count"]), str(row["consensus_id"]), str(row["consensus_strand"])))
    if not candidates:
        return {"leaf_id": leaf_id, "mapping_status": "NO_EVIDENCE", "seed_coverage": 0.0, "inlier_seed_count": 0, "second_seed_coverage": 0.0}
    top = candidates[0]
    second_coverage = float(candidates[1]["seed_coverage"]) if len(candidates) > 1 else 0.0
    top["leaf_id"] = leaf_id
    top["second_seed_coverage"] = second_coverage
    if float(top["seed_coverage"]) < float(params["minimum_query_seed_coverage"]):
        top["mapping_status"] = "INSUFFICIENT_EVIDENCE"
    elif float(top["seed_coverage"]) - second_coverage < float(params["minimum_top_to_second_coverage_margin"]):
        top["mapping_status"] = "AMBIGUOUS_EVIDENCE"
    else:
        top["mapping_status"] = "MAPPED"
    return top


def _map_worker(record: tuple[str, str]) -> dict[str, object]:
    if _WORKER_INDEX is None or _WORKER_CONSENSUS is None or _WORKER_PARAMS is None:
        raise RuntimeError("mapping worker was not initialized")
    return map_leaf(record[0], record[1], _WORKER_INDEX, _WORKER_CONSENSUS, _WORKER_PARAMS)


def map_all(leaves_fasta: Path, consensus_fasta: Path, out_path: Path, params: dict) -> None:
    consensus = dict(iter_fasta(consensus_fasta))
    if not consensus:
        raise ValueError("empty consensus library")
    index = build_index(consensus, int(params["kmer_size"]), int(params["maximum_consensus_postings_per_kmer"]))
    records = list(iter_fasta(leaves_fasta))
    workers = min(int(params.get("workers", 1)), max(1, len(records)))
    if workers == 1:
        rows = [map_leaf(leaf_id, sequence, index, consensus, params) for leaf_id, sequence in records]
    else:
        global _WORKER_INDEX, _WORKER_CONSENSUS, _WORKER_PARAMS
        _WORKER_INDEX, _WORKER_CONSENSUS, _WORKER_PARAMS = index, consensus, params
        with multiprocessing.get_context("fork").Pool(processes=workers) as pool:
            rows = pool.map(_map_worker, records)
    write_tsv(out_path, rows, EVIDENCE_FIELDS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--leaves-fasta", required=True, type=Path)
    parser.add_argument("--consensus-fasta", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    config = read_json(args.config)
    map_all(args.leaves_fasta, args.consensus_fasta, args.out, config["sequence_evidence"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
