#!/usr/bin/env python3
"""Focused contract tests for the descriptive overlap stage."""
from __future__ import annotations

from annotation_overlap import UnionIndex, annotation_category, merge_intervals


def test_annotation_category_contract() -> None:
    assert annotation_category("LINE/L1") == "TE"
    assert annotation_category("Retroposon") == "TE"
    assert annotation_category("Unknown") == "UNKNOWN"
    assert annotation_category("DNA/?") == "UNKNOWN"
    assert annotation_category("Simple_repeat") == "NONTE"
    assert annotation_category("Low_complexity") == "NONTE"
    assert annotation_category("Satellite") == "NONTE"
    assert annotation_category("rRNA") == "NONTE"
    assert annotation_category("PLE") == "UNRECOGNIZED"


def test_union_overlap_does_not_double_count() -> None:
    intervals = merge_intervals([(0, 10), (5, 15), (30, 35)])
    assert intervals == [(0, 15), (30, 35)]
    index = UnionIndex(intervals)
    assert index.overlap_bp(8, 32) == 9
    assert index.overlap_bp(15, 30) == 0


if __name__ == "__main__":
    test_annotation_category_contract()
    test_union_overlap_does_not_double_count()
    print("annotation_overlap contract tests: PASS")
