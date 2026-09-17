#!/usr/bin/env python3
"""Replay the validated long-benchmark score from compact block counts.

This is the standalone CPU part of the long-panel benchmark.  It reproduces
the arithmetic in ``benchmarks/te_omnibenchmark/long_panel.py`` without
importing the research repository, running a caller, or reading raw sequence
data.  The input is an explicit JSON bundle containing the validated block
counts and the recorded native status metadata.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROTOCOL = "TE-LONG-BENCH-20260915"
EXPECTED_CELLS = 14


def metrics(counts: Tuple[int, int, int, int], synthetic: bool) -> Dict[str, Any]:
    """Match the frozen long_panel.py metric calculation exactly."""
    tp, fp, fn, tn = counts
    result: Dict[str, Any] = {
        "reference_positive_bp": tp + fn,
        "predicted_bp": tp + fp,
        "overlap_bp": tp,
        "reference_positive_recall": tp / (tp + fn) if tp + fn else None,
        "prediction_outside_reference_bp": fp,
        "precision": None,
        "f1": None,
    }
    if synthetic:
        result.update(
            tp=tp,
            fp=fp,
            fn=fn,
            tn=tn,
            recall=result["reference_positive_recall"],
            precision=tp / (tp + fp) if tp + fp else None,
            f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        )
    return result


def score(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Recompute all planned cells from validated sufficient statistics."""
    if bundle.get("protocol") != PROTOCOL:
        raise ValueError(f"expected protocol {PROTOCOL!r}")
    attempts = bundle.get("attempts")
    datasets = bundle.get("datasets")
    if not isinstance(attempts, dict) or not isinstance(datasets, dict):
        raise ValueError("bundle must contain attempts and datasets objects")
    attempt_datasets = attempts.get("datasets")
    if not isinstance(attempt_datasets, dict):
        raise ValueError("bundle attempts.datasets is missing")

    cells: List[Dict[str, Any]] = []
    for dataset, paths in attempt_datasets.items():
        if dataset not in datasets:
            raise ValueError(f"attempts reference unknown dataset: {dataset}")
        observed = datasets[dataset]
        for method, source_attempt in paths.items():
            statuses = observed.get("statuses", {})
            if method not in statuses:
                raise ValueError(f"missing status for {dataset}/{method}")
            status = statuses[method]
            values = None
            if status.get("status") == "COMPLETED":
                blocks = observed.get("blocks", {})
                try:
                    counts = tuple(
                        sum(block[method][index] for block in blocks.values())
                        for index in range(4)
                    )
                except (KeyError, TypeError) as exc:
                    raise ValueError(f"missing block count for {dataset}/{method}") from exc
                if sum(counts) != observed["callable_evaluation_bp"]:
                    raise ValueError(f"block counts do not recover callable denominator: {dataset}/{method}")
                values = metrics(counts, dataset == "sim100")
                source = observed.get("metrics", {}).get(method)
                if source is None:
                    raise ValueError(f"missing recorded metrics for {dataset}/{method}")
                for key, value in values.items():
                    old = source.get(key)
                    if (value is None) != (old is None) or (
                        value is not None
                        and not math.isclose(value, old, rel_tol=1e-12, abs_tol=1e-12)
                    ):
                        raise ValueError(f"recorded metric differs: {dataset}/{method}/{key}")
            cells.append(
                {
                    "cell_id": f"{dataset}|{method}",
                    "dataset": dataset,
                    "method": method,
                    "status": status["status"],
                    "metrics": values,
                    # These fields are historical provenance.  They are not
                    # required to run this replay and must not be edited to
                    # make the standalone package work elsewhere.
                    "source_attempt": source_attempt,
                    "native_wall_seconds": status.get("wall_seconds"),
                    "native_steps": status.get("steps"),
                    "native_hardware": {
                        key: status.get(key)
                        for key in ("hostname", "cpu_model", "accelerator", "cpus", "cpus_allocated")
                    },
                    "failure_reason": status.get("failure_reason"),
                }
            )

    result = {
        "protocol": PROTOCOL,
        "cells": cells,
        "expected_cells": EXPECTED_CELLS,
        "replay_scope": "Recompute metrics from Slurm-validated block counts, not native callers",
        "real_absolute_precision_f1": None,
        "L3_insertion_identity": None,
        "source_comparisons": {
            name: value.get("comparisons") for name, value in datasets.items()
        },
        "source_engineering_attempts": attempts.get("failed_engineering_attempts"),
        "provenance_note": (
            "source_attempt, native_steps, native_wall_seconds and native_hardware are historical "
            "native-run provenance; this command performs no native annotation and does not require "
            "those historical paths to exist"
        ),
    }
    result["status_counts"] = dict(Counter(cell["status"] for cell in cells))
    result["scored_cells"] = sum(cell["metrics"] is not None for cell in cells)
    if len(cells) != EXPECTED_CELLS:
        raise ValueError(f"expected {EXPECTED_CELLS} planned cells, observed {len(cells)}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="validated score bundle JSON")
    parser.add_argument("--output", type=Path, required=True, help="replay result JSON path")
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text())
    result = score(bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({
        "status": "PASS",
        "output": str(args.output),
        "planned_cells": len(result["cells"]),
        "status_counts": result["status_counts"],
        "scored_cells": result["scored_cells"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
