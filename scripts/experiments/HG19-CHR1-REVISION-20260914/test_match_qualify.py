#!/usr/bin/env python3
"""Focused tests for chain, sequence, and source-only matching contracts."""
from __future__ import annotations

import tempfile
from pathlib import Path

from match_qualify import (
    ChainIndex,
    IntervalUnion,
    find_paths,
    parse_chains,
    select_controls,
    sequence_metrics,
    source_sequence_covariates,
)


def test_chain_blocks_and_internal_indel_stratum() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "synthetic.chain"
        path.write_text(
            "chain 100 chr2 100 + 0 20 chr2 100 + 50 71 1\n"
            "10 2 3\n"
            "8\n\n"
            "chain 100 chr2 100 + 30 40 chr2 100 + 80 90 2\n"
            "10\n\n"
            "chain 100 chr3 100 + 0 10 chr3 100 - 20 30 3\n"
            "10\n\n",
            encoding="utf-8",
        )
        chains = parse_chains(path)
    index = ChainIndex(chains)
    indel = find_paths(index, "chr2", "chr2", 0, 20, 50, 71)
    assert len(indel) == 1
    assert indel[0].full_source_coverage is False
    assert indel[0].source_gap_bp == 2
    assert indel[0].target_gap_bp == 3
    assert indel[0].strict_internal_bijection is False
    single = find_paths(index, "chr2", "chr2", 32, 38, 82, 88)
    assert single[0].block_count == 1
    assert single[0].strict_internal_bijection is True
    minus = find_paths(index, "chr3", "chr3", 0, 10, 70, 80)
    assert minus[0].q_strand == "-"
    assert minus[0].strict_internal_bijection is True


def test_sequence_negative_orientation_and_old_boundary_relations() -> None:
    metrics = sequence_metrics("AAGC", "GCTT", 0, 4, 0, 4, "-")
    assert metrics["mismatch_bp"] == 0
    assert metrics["source_non_acgt_count"] == 0
    union = IntervalUnion([(10, 20)])
    assert union.distance_and_relation(12, 15) == (0, "OVERLAP")
    assert union.distance_and_relation(20, 25) == (0, "ADJACENT")
    assert union.distance_and_relation(30, 35) == (10, "ISOLATED")
    covariates = source_sequence_covariates("AACGNN", 0, 6)
    assert covariates["source_gc_count"] == 2
    assert covariates["source_non_acgt_count"] == 2


def _qualified(row_id: int, mapping_id: str, state: str, gc: float, distance: int) -> dict:
    return {
        "row_id": row_id,
        "mapping_id": mapping_id,
        "state": state,
        "source_chrom": "chr2",
        "source_start0": row_id * 100,
        "source_end": row_id * 100 + 100,
        "source_length": 100,
        "old_te_relation": "ISOLATED",
        "source_non_acgt_count": 0,
        "old_te_distance_bin": "51_200",
        "old_te_distance_bp": distance,
        "source_gc_fraction": gc,
        "chain_stratum": "SINGLE_BLOCK",
        "sequence_status": "SEQUENCE_EXACT",
    }


def test_matching_uses_source_covariates_and_retains_unmatched() -> None:
    rows = [
        _qualified(1, "fp1", "FP", 0.50, 100),
        _qualified(2, "fp2", "FP", 0.90, 100),
        _qualified(3, "tn1", "TN", 0.51, 101),
    ]
    matches, summary = select_controls(rows)
    assert matches[0]["match_status"] == "MATCHED_TN"
    assert matches[0]["control_mapping_id"] == "tn1"
    assert matches[1]["match_status"] == "UNMATCHED_FP"
    assert summary["matched_pairs_n"] == 1
    assert summary["unmatched_fp_n"] == 1


if __name__ == "__main__":
    test_chain_blocks_and_internal_indel_stratum()
    test_sequence_negative_orientation_and_old_boundary_relations()
    test_matching_uses_source_covariates_and_retains_unmatched()
    print("match_qualify contract tests: PASS")
