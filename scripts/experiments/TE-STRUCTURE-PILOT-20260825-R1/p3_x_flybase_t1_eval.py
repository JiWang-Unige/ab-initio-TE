#!/usr/bin/env python3
"""Evaluate P3-X predictions against the frozen FlyBase positive-only T1 truth.

This wrapper reuses the project's interval matching implementation but removes
precision/F1/FP/TN fields from the persisted result.  FlyBase's unlabelled
space is not an exhaustive negative set, so those metrics are not computed or
claimed for this run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from length_stratified_eval import (  # noqa: E402
    evaluate,
    read_canonical,
    read_lengths,
)


def _allowed_key(key: str) -> bool:
    lower = key.lower()
    if "precision" in lower or "f1" in lower:
        return False
    if lower.endswith("_fp") or lower.endswith("_tn"):
        return False
    return True


def _t1_only(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _t1_only(item)
            for key, item in value.items()
            if _allowed_key(str(key))
        }
    if isinstance(value, list):
        return [_t1_only(item) for item in value]
    return value


def evaluate_flybase_t1(
    truth: Path,
    prediction: Path,
    lengths: Path,
    *,
    iou_threshold: float = 0.8,
    boundary_tolerances: tuple[int, ...] = (5, 25),
) -> dict[str, object]:
    result = evaluate(
        read_canonical(truth),
        read_canonical(prediction),
        read_lengths(lengths),
        truth_tier="T1",
        iou_threshold=iou_threshold,
        boundary_tolerances=boundary_tolerances,
    )
    filtered = _t1_only(result)
    assert isinstance(filtered, dict)
    filtered.pop("unassigned_prediction_segments", None)
    filtered.pop("prediction_bin_denominator", None)
    filtered["claim_scope"] = "FlyBase T1 positive-only: recall, boundary recall, fragmentation"
    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--lengths", type=Path, required=True)
    parser.add_argument("--iou-threshold", type=float, default=0.8)
    parser.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5, 25])
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_flybase_t1(
        args.truth,
        args.prediction,
        args.lengths,
        iou_threshold=args.iou_threshold,
        boundary_tolerances=tuple(args.boundary_tolerances),
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
