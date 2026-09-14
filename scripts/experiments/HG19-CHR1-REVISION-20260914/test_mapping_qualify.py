#!/usr/bin/env python3
"""Small mapping-contract regressions; no external binary or annotations."""
from __future__ import annotations

from mapping_qualify import LiftedInterval, SourceInterval, classify_interval


ALLOWED_SOURCE = {"chr2", "chr3", "chr4"}
ALLOWED_TARGET = {"chr2", "chr3", "chr4"}


def source(start: int = 10, end: int = 20) -> SourceInterval:
    return SourceInterval(1, "r000000001", "chr2", start, end, "FP", "0", ".", "tile1")


def lifted(mapping_id: str, chrom: str, start: int, end: int) -> LiftedInterval:
    return LiftedInterval(mapping_id, chrom, start, end, "FP", "0", ".", "tile1")


def test_synthetic_forward_reverse_chain_roundtrip() -> None:
    # Synthetic chain blocks: hg19 chr2 [0,100) -> CHM13 chr2 [1000,1100),
    # and the reciprocal block back to hg19.  The classifier checks the
    # resulting coordinate roundtrip, without implementing a second liftover.
    row = source()
    forward = lifted(row.mapping_id, "chr2", 1010, 1020)
    reverse = lifted(row.mapping_id, "chr2", 10, 20)
    result = classify_interval(row, [forward], [reverse], ALLOWED_SOURCE, ALLOWED_TARGET)
    assert result["mapping_status"] == "UNIQUE_RECIPROCAL_SAME_LENGTH"
    assert result["qualified_unique_reciprocal_same_length"] is True


def test_length_change_is_retained_but_never_qualified() -> None:
    row = source()
    forward = lifted(row.mapping_id, "chr2", 1010, 1019)
    reverse = lifted(row.mapping_id, "chr2", 10, 19)
    result = classify_interval(row, [forward], [reverse], ALLOWED_SOURCE, ALLOWED_TARGET)
    assert result["mapping_status"] == "LENGTH_CHANGED_NONRECIPROCAL"
    assert result["length_changed"] is True
    assert result["qualified_unique_reciprocal_same_length"] is False


def test_ambiguous_and_unmapped_destinations_are_not_collapsed() -> None:
    row = source()
    f1 = lifted(row.mapping_id, "chr2", 1010, 1020)
    f2 = lifted(row.mapping_id, "chr2", 2010, 2020)
    result = classify_interval(row, [f1, f2], [], ALLOWED_SOURCE, ALLOWED_TARGET)
    assert result["mapping_status"] == "AMBIGUOUS_FORWARD"
    assert result["forward_count"] == 2
    assert result["qualified_unique_reciprocal_same_length"] is False

    result = classify_interval(row, [], [], ALLOWED_SOURCE, ALLOWED_TARGET)
    assert result["mapping_status"] == "UNMAPPED_FORWARD"
    assert result["forward_count"] == 0


def test_target_scope_is_separate_from_reciprocity() -> None:
    row = source()
    forward = lifted(row.mapping_id, "chrX", 1010, 1020)
    reverse = lifted(row.mapping_id, "chr2", 10, 20)
    result = classify_interval(row, [forward], [reverse], ALLOWED_SOURCE, ALLOWED_TARGET)
    assert result["mapping_status"] == "TARGET_OUT_OF_SCOPE_RECIPROCAL_SAME_LENGTH"
    assert result["target_scope"] == "OUT_OF_SCOPE"
    assert result["qualified_unique_reciprocal_same_length"] is False


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_"):
            function()
    print("mapping_qualify synthetic regression: PASS")
