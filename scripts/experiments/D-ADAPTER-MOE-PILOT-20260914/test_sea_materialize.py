#!/usr/bin/env python3
"""Focused label-policy smoke for the sea-urchin materializer."""

from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sea_materialize_under_test", HERE / "sea_materialize.py")
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(start: int, end: int, class_family: str) -> dict[str, object]:
    return {"start": start, "end": end, "attributes": f"class_family={class_family}"}


def main() -> None:
    region = {
        "id": "sea_urchin__r01__scaffold__100_1048676",
        "start_bp": 100,
        "end_bp": 100 + len("AAAANAAAAACGTACGTACGT"),
    }
    sequence = "AAAANAAAAACGTACGTACGT"
    labels, stats = module.build_labels(
        region,
        sequence,
        [
            row(100, 105, "LINE/L1"),
            row(103, 108, "PLE"),
            row(108, 110, "Simple_repeat"),
        ],
    )
    # PLE masks its overlap and the N at position 4 is masked even inside a TE.
    assert labels[0:3] == "111"
    assert labels[3:8] == "?????"
    assert labels[8:10] == "00"
    assert stats["non_acgt_masked_bp"] == 1
    assert stats["positive_bp"] + stats["reference_negative_bp"] + stats["masked_bp"] == len(sequence)
    assert stats["masked_bp"] == 5
    assert module.row_bucket("PLE") == "unknown_or_ambiguous"
    assert module.row_bucket("LINE/L1") == "known_te"
    assert module.row_bucket("Simple_repeat") == "reference_negative"
    print("{\"status\":\"PASS\",\"policy\":\"unknown-and-non-ACGT-mask\"}")


if __name__ == "__main__":
    main()
