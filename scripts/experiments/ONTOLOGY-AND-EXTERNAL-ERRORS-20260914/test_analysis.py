#!/usr/bin/env python3
"""Small deterministic contract checks for the ontology/error audit."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ontology_external", HERE / "audit_ontology_external.py")
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main() -> None:
    assert module.truth_bucket("LINE/L1") == "known_te"
    assert module.truth_bucket("RC/Helitron") == "known_te"
    assert module.truth_bucket("Retroposon/SVA") == "known_te"
    assert module.truth_bucket("PLE/Penelope") == "unknown_or_ambiguous"
    assert module.truth_bucket("Simple_repeat") == "hard_non_te"
    assert module.truth_bucket("DNA?") == "unknown_or_ambiguous"
    assert module.dimension_length(79) == "<80"
    assert module.dimension_length(80) == "80-499"
    assert module.dimension_length(500) == "500-999"
    assert module.dimension_length(1000) == ">=1000"
    assert module.dimension_divergence(None) == "NA"
    assert module.dimension_divergence(4.99) == "<5"
    assert module.dimension_divergence(5.0) == "5-15"
    assert module.dimension_divergence(15.0) == "15-30"
    assert module.dimension_divergence(30.0) == ">=30"

    regions = [{
        "id": "r1",
        "source_seqid": "chr1",
        "source_length_bp": 1000,
        "start_bp": 100,
        "end_bp": 120,
        "length_bp": 20,
    }]
    by_source, by_id = module._region_lookup(regions)
    row = {"seqid": "chr1", "start": 101, "end": 105}
    region, left, right, mode = module.map_panel_interval(row, by_source, by_id)
    assert region is regions[0] and (left, right, mode) == (1, 5, "source_assembly")
    row = {"seqid": "r1", "start": 102, "end": 106}
    region, left, right, mode = module.map_panel_interval(row, by_source, by_id)
    assert region is regions[0] and (left, right, mode) == (2, 6, "panel_id_absolute")
    row = {"seqid": "r1", "start": 2, "end": 6}
    region, left, right, mode = module.map_panel_interval(row, by_source, by_id)
    assert region is regions[0] and (left, right, mode) == (2, 6, "panel_id_local")
    row = {"seqid": "missing", "start": 0, "end": 4}
    region, left, right, mode = module.map_panel_interval(row, by_source, by_id)
    assert region is None and (left, right, mode) == (0, 0, None)

    callable_prefix = module._prefix(np.array([True, True, False, True], dtype=bool))
    predicted_prefix = module._prefix(np.array([False, True, False, True], dtype=bool))
    stat = {}
    module.update_stat(stat, {"F": (callable_prefix, predicted_prefix)}, 0, 4)
    result = module.finalize_row_stat(stat)
    assert result["rows"] == 1
    assert result["by_arm"]["F"]["callable_bp"] == 3
    assert result["by_arm"]["F"]["predicted_positive_callable_bp"] == 2
    assert result["by_arm"]["F"]["missed_callable_bp"] == 1
    assert result["by_arm"]["F"]["any_recovery_rate"] == 1.0

    print("analysis contract tests: PASS")


if __name__ == "__main__":
    main()
