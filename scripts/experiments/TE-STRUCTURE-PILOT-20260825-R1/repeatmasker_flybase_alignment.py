#!/usr/bin/env python3
"""Run the narrow FlyBase T1 RepeatMasker-alignment evaluation.

The existing LEMMI adapter owns coordinate normalization and interval metrics.
This entry point only fixes the D2 comparison contract and exposes the
positive-truth metrics that are valid for FlyBase T1.  It deliberately does
not report precision/F1 fields because unlabelled FlyBase sequence is not an
exhaustive negative set.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any


ADAPTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "LEMMI-TE-BENCH-20260824-R1"
    / "adapter.py"
)


def _load_adapter():
    spec = importlib.util.spec_from_file_location("lemmi_te_adapter", ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load LEMMI adapter: {ADAPTER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_lengths(path: Path) -> dict[str, int]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value:
        raise ValueError("contig lengths must be a non-empty JSON object")
    lengths: dict[str, int] = {}
    for seqid, length in value.items():
        if not isinstance(seqid, str) or not isinstance(length, int) or length < 1:
            raise ValueError(f"invalid declared contig length: {seqid!r}")
        lengths[seqid] = length
    return lengths


def _safe_metrics(raw: dict[str, Any], boundary_tol_bp: int) -> dict[str, Any]:
    """Select only metrics supported by positive-only T1 truth."""
    if raw.get("truth_tier") != "T1":
        raise ValueError("D2 requires T1 truth metrics")
    if boundary_tol_bp not in {5, 25}:
        raise ValueError(f"unsupported D2 boundary tolerance: {boundary_tol_bp}")
    return {
        "bp_recall": raw["bp_recall"],
        "segment_recall_iou_0_8": raw["segment_recall"],
        f"boundary_recall_{boundary_tol_bp}bp": raw["boundary_recall"],
        "mean_fragments_per_truth": raw["mean_fragments_per_true"],
        "split_true_rate": raw["split_true_rate"],
        "missed_true_rate": raw["missed_true_rate"],
    }


def run(
    flybase_truth: Path,
    repeatmasker_prediction: Path,
    contig_lengths: Path,
    *,
    truth_format: str = "auto",
    prediction_format: str = "auto",
    output: Path | None = None,
) -> dict[str, Any]:
    """Evaluate RepeatMasker against the same-assembly FlyBase T1 truth."""
    lengths = _read_lengths(contig_lengths)
    adapter = _load_adapter()

    with tempfile.TemporaryDirectory(prefix="d2-flybase-rm-") as tmp:
        root = Path(tmp)
        truth_canonical = root / "flybase.truth.canonical.tsv"
        prediction_canonical = root / "repeatmasker.prediction.canonical.tsv"
        adapter.convert(flybase_truth, truth_canonical, truth_format)
        adapter.convert(repeatmasker_prediction, prediction_canonical, prediction_format)

        raw_by_tolerance: dict[int, dict[str, Any]] = {}
        for tolerance in (5, 25):
            raw_by_tolerance[tolerance] = adapter.evaluate(
                truth_canonical,
                prediction_canonical,
                lengths,
                iou_threshold=0.8,
                boundary_tol_bp=tolerance,
                truth_tier="T1",
                overlap_policy="flat_union",
            )

        # Boundary tolerance must not change the bp, segment, or fragmentation
        # denominators.  If it does, the comparison contract is not aligned.
        stable_keys = (
            "bp_recall",
            "segment_recall",
            "true_segments",
            "pred_segments",
            "mean_fragments_per_true",
            "split_true_rate",
            "missed_true_rate",
        )
        for key in stable_keys:
            if raw_by_tolerance[5][key] != raw_by_tolerance[25][key]:
                raise ValueError(f"boundary tolerance changed non-boundary metric: {key}")

        result: dict[str, Any] = {
            "status": "PASS",
            "profile": "TE-STRUCTURE-PILOT-20260825-R1-D2",
            "truth_tier": "T1",
            "claim_scope": "T1_positive_only_recall_boundary_fragmentation",
            "coordinate_convention": "zero_based_half_open",
            "overlap_policy": "flat_union",
            "same_declared_contig_lengths": str(contig_lengths),
            "flybase_truth": str(flybase_truth),
            "repeatmasker_prediction": str(repeatmasker_prediction),
            "metrics": {
                **_safe_metrics(raw_by_tolerance[5], 5),
                **_safe_metrics(raw_by_tolerance[25], 25),
            },
        }

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flybase-truth", type=Path, required=True)
    parser.add_argument("--repeatmasker-prediction", type=Path, required=True)
    parser.add_argument("--contig-lengths", type=Path, required=True)
    parser.add_argument("--truth-format", default="auto", choices=["auto", "bed", "gff", "gff3", "repeatmasker_out"])
    parser.add_argument("--prediction-format", default="auto", choices=["auto", "bed", "gff", "gff3", "repeatmasker_out"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(
        args.flybase_truth,
        args.repeatmasker_prediction,
        args.contig_lengths,
        truth_format=args.truth_format,
        prediction_format=args.prediction_format,
        output=args.output,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
