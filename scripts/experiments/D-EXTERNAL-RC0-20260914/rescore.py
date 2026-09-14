#!/usr/bin/env python3
"""Re-score completed RC0 predictions under the frozen Label-A TE contract.

This command deliberately never loads the model or calls inference.  It reads
the saved base-pair probability arrays from a completed RC0 output, rebuilds
the truth buckets from the raw RepeatMasker output, and emits a corrected
score report in a new directory.  The original prediction output remains an
immutable execution record; its old summary is not silently replaced.
"""
from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path
from typing import Any

import numpy as np

import rc0  # resolved from this experiment directory when run as a script


def _read_fasta(path: Path) -> dict[str, str]:
    return {name: sequence for name, sequence in rc0.inference.read_fasta(path)}


def _write_single_region_canonical(
    path: Path,
    rows: list[tuple[str, int, int]],
    region_id: str,
) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("seqid\tstart\tend\tname\tscore\tstrand\tsource\tattributes\n")
        for seqid, start, end in rows:
            if seqid == region_id:
                handle.write(f"{seqid}\t{start}\t{end}\t.\t.\t.\t.\t.\n")


def _score_arm(
    arm: str,
    values: dict[str, np.ndarray],
    regions: list[dict[str, Any]],
    sequences: dict[str, str],
    truth_canonical: Path,
    truth_callable: Path,
    truth_masks: dict[str, np.ndarray],
    panel_lengths: dict[str, int],
    output_dir: Path,
    threshold: float,
) -> dict[str, Any]:
    material_bed = output_dir / f"{arm}.material.bed"
    canonical = output_dir / f"{arm}.canonical.tsv"
    rc0._write_material_bed(material_bed, regions, values, threshold)
    rc0.adapter.convert(material_bed, canonical, "bed")
    callable_canonical = rc0._clip_canonical_to_callable(
        canonical, regions, sequences, output_dir, arm
    )
    callable_lengths = {
        str(region["id"]): sum(base in "ACGT" for base in sequences[str(region["id"])])
        for region in regions
    }
    callable_panel_bp = int(sum(callable_lengths.values()))
    full_t1 = rc0.adapter.evaluate(truth_canonical, canonical, panel_lengths, truth_tier="T1")
    full_t0 = rc0.adapter.evaluate(truth_canonical, canonical, panel_lengths, truth_tier="T0")
    callable_t1 = rc0.adapter.evaluate(
        truth_callable, callable_canonical, panel_lengths, truth_tier="T1"
    )
    callable_t0 = rc0.adapter.evaluate(
        truth_callable, callable_canonical, panel_lengths, truth_tier="T0"
    )
    callable_t1 = rc0._correct_callable_metrics(callable_t1, callable_panel_bp, "T1")
    callable_t0 = rc0._correct_callable_metrics(callable_t0, callable_panel_bp, "T0")
    truth_rows = rc0.adapter.read_canonical(truth_callable)
    pred_rows = rc0.adapter.read_canonical(callable_canonical)
    per_region: dict[str, Any] = {}
    for region in regions:
        rid = str(region["id"])
        one_truth = output_dir / f".{arm}.{rid}.truth.tsv"
        one_pred = output_dir / f".{arm}.{rid}.pred.tsv"
        _write_single_region_canonical(one_truth, truth_rows, rid)
        _write_single_region_canonical(one_pred, pred_rows, rid)
        lengths = {rid: int(region["length_bp"])}
        one_t1 = rc0.adapter.evaluate(one_truth, one_pred, lengths, truth_tier="T1")
        one_t0 = rc0.adapter.evaluate(one_truth, one_pred, lengths, truth_tier="T0")
        one_callable_bp = int(callable_lengths[rid])
        one_t1 = rc0._correct_callable_metrics(one_t1, one_callable_bp, "T1")
        one_t0 = rc0._correct_callable_metrics(one_t0, one_callable_bp, "T0")
        per_region[rid] = {
            "length_bp": int(region["length_bp"]),
            "callable_bp": int(one_callable_bp),
            "truth_positive_bp": int(np.count_nonzero(truth_masks[rid])),
            "strata": rc0._strata(
                sequences[rid], truth_masks[rid], values[rid], threshold
            ),
            "t1": one_t1,
            "repeatmasker_comparator_t0": one_t0,
        }
        one_truth.unlink()
        one_pred.unlink()
    return {
        "material_bed": str(material_bed.resolve()),
        "canonical": str(canonical.resolve()),
        "callable_canonical": str(callable_canonical.resolve()),
        "primary_callable_t1_positive_recovery": callable_t1,
        "callable_repeatmasker_comparator_agreement_t0": callable_t0,
        "full_region_t1_positive_recovery": full_t1,
        "full_region_repeatmasker_comparator_agreement_t0": full_t0,
        "per_region": per_region,
        "callable_bp": callable_panel_bp,
        "predicted_positive_bp": int(
            sum(np.count_nonzero(values[rid] >= threshold) for rid in values)
        ),
        "material_run_count": int(
            sum(len(rc0._material_runs(values[rid] >= threshold)) for rid in values)
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--candidate", required=True, choices=["platypus", "sea_urchin", "c_briggsae"]
    )
    parser.add_argument("--existing-output", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-root", type=Path)
    parser.add_argument(
        "--label-out",
        type=Path,
        help="optional alternate RepeatMasker .out; defaults to the candidate Label-A output",
    )
    parser.add_argument(
        "--label-source",
        default=None,
        help="short provenance label for an alternate comparator annotation",
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    config = rc0._read_json(args.config.resolve())
    candidate = rc0._candidate(config, args.candidate)
    rc0._check_panel(config, candidate)
    source_dir = args.existing_output.resolve()
    source_summary_path = source_dir / "summary.json"
    source_probabilities = source_dir / "probabilities.npz"
    source_regions_path = source_dir / "panel_regions.json"
    source_fasta = source_dir / "panel_regions.fa"
    for path in (source_summary_path, source_probabilities, source_regions_path, source_fasta):
        if not path.is_file():
            raise FileNotFoundError(f"completed RC0 prediction input missing: {path}")
    source_summary = rc0._read_json(source_summary_path)
    if source_summary.get("status") != "COMPLETED":
        raise ValueError("source RC0 summary is not COMPLETED")
    if source_summary.get("candidate") != args.candidate:
        raise ValueError("source RC0 candidate does not match --candidate")
    regions = json.loads(source_regions_path.read_text(encoding="utf-8"))
    if not isinstance(regions, list) or len(regions) != 4:
        raise ValueError("source panel_regions.json must contain four regions")
    # The source summary is also the fixed coordinate record produced at
    # inference time; reject a mismatch rather than rescoring different bases.
    if regions != source_summary.get("regions"):
        raise ValueError("source panel region record differs between summary and panel_regions.json")
    remote_root = Path(args.remote_root or config["remote_root"])
    if args.label_out is None:
        label_out = rc0._resolve_path(remote_root, str(candidate["label_out"]))
        label_source = args.label_source or "candidate_Label-A"
    else:
        label_out = args.label_out.expanduser().resolve()
        label_source = args.label_source or "alternate_RepeatMasker_comparator"
    calibration_path = rc0._resolve_path(
        remote_root, str(config["model"]["calibration_relpath"])
    )
    assert label_out is not None and calibration_path is not None
    if not label_out.is_file() or not calibration_path.is_file():
        raise FileNotFoundError("label or frozen calibration input missing")
    calibration = rc0._read_json(calibration_path)
    threshold = float(calibration["threshold"])
    source_threshold = float(source_summary["model"]["threshold"])
    if abs(threshold - source_threshold) > 1e-12:
        raise ValueError("source prediction threshold differs from frozen CAL threshold")
    sequences = _read_fasta(source_fasta)
    expected_ids = {str(row["id"]) for row in regions}
    if set(sequences) != expected_ids:
        raise ValueError("source panel FASTA IDs differ from source region record")
    callable_lengths = {
        str(region["id"]): sum(base in "ACGT" for base in sequences[str(region["id"])])
        for region in regions
    }
    callable_panel_bp = int(sum(callable_lengths.values()))
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"rescore output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    truth_bed, truth_canonical, truth_audit = rc0._make_truth(label_out, regions, output_dir)
    truth_masks = rc0._truth_masks(truth_canonical, regions)
    panel_lengths = {str(row["id"]): int(row["length_bp"]) for row in regions}
    truth_callable = rc0._clip_canonical_to_callable(
        truth_canonical, regions, sequences, output_dir, "truth_repeatmasker_panel"
    )
    with np.load(source_probabilities, allow_pickle=False) as archive:
        arms: dict[str, dict[str, np.ndarray]] = {}
        for arm in ("F", "RC", "mean", "phase_mean"):
            values: dict[str, np.ndarray] = {}
            for region in regions:
                rid = str(region["id"])
                key = f"{arm}__{rid}"
                if key not in archive:
                    raise ValueError(f"source probabilities missing {key}")
                array = np.asarray(archive[key], dtype=np.float64)
                if array.shape != (int(region["length_bp"]),) or not np.isfinite(array).all():
                    raise ValueError(f"invalid source probability array {key}")
                values[rid] = array
            arms[arm] = values
    arm_results = {
        arm: _score_arm(
            arm,
            values,
            regions,
            sequences,
            truth_canonical,
            truth_callable,
            truth_masks,
            panel_lengths,
            output_dir,
            threshold,
        )
        for arm, values in arms.items()
    }
    summary = {
        "protocol": "D-EXTERNAL-RC0-20260914-LABEL-CONTRACT-RESCORE",
        "status": "COMPLETED",
        "scientific_scope": "label-contract rescore of saved fixed-D predictions; no inference",
        "candidate": candidate["id"],
        "species": candidate["species"],
        "assembly": candidate["assembly"],
        "source_prediction_output": str(source_dir),
        "source_summary": str(source_summary_path),
        "source_probability_arrays": str(source_probabilities),
        "label_out": str(label_out.resolve()),
        "label_source": label_source,
        "threshold": threshold,
        "truth": {
            "primary_tier": "T1",
            "source": label_source,
            "raw_repeatmasker_rows_seen": int(truth_audit["raw_repeatmasker_rows_seen"]),
            "panel_rows_retained": int(truth_audit["panel_buckets"]["known_te"]["rows"]),
            "panel_rows_retained_all_buckets": int(truth_audit["panel_rows_retained_all_buckets"]),
            "primary_known_te_overlap_bp": int(
                truth_audit["panel_buckets"]["known_te"]["overlap_bp"]
            ),
            "primary_known_te_union_bp": int(
                truth_audit["panel_buckets"]["known_te"]["union_bp"]
            ),
            "primary_endpoint_status": (
                "ELIGIBLE_KNOWN_TE_IN_PANEL"
                if int(truth_audit["panel_buckets"]["known_te"]["rows"]) > 0
                else "NOT_EVALUABLE_NO_KNOWN_TE_IN_PANEL"
            ),
            "class_audit": str((output_dir / "truth_repeatmasker_panel_class_audit.json").resolve()),
            "class_policy": truth_audit["policy"],
            "bucket_canonical_paths": truth_audit["canonical_paths"],
            "canonical": str(truth_canonical.resolve()),
            "callable_canonical": str(truth_callable.resolve()),
            "callable_panel_bp": int(sum(callable_lengths.values())),
            "callable_non_acgt_panel_bp": int(sum(panel_lengths.values()) - callable_panel_bp),
            "primary_callable_policy": "intersect truth and prediction with A/C/G/T before primary T1 endpoints",
            "t0_name": "repeatmasker_comparator_agreement_t0",
            "t0_is_independent_accuracy": False,
            "unlabelled_sequence_is_negative": False,
        },
        "arms": arm_results,
        "status_denominator": "one completed source candidate x four saved arms; no inference rerun",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output_dir / "STATUS.json").write_text(
        json.dumps({"status": "COMPLETED", "summary": str((output_dir / "summary.json").resolve())}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "STATUS.json").write_text(
            json.dumps(
                {"status": "FAILED", "error": str(exc), "traceback": traceback.format_exc()},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
    print(json.dumps({"status": result["status"], "candidate": result["candidate"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
