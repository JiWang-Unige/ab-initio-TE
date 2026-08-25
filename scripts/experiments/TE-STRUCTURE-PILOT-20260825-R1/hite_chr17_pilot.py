#!/usr/bin/env python3
"""Emit the HiTE human chr17 prefix engineering contract.

This module does not execute HiTE, crop files, or create runtime wrappers.  It
records the exact commands and shared truth/mask/length contract for a later
Slurm cell.  Human H0 labels are RepeatMasker-derived comparator labels, so
the resulting metrics are comparator-agreement metrics rather than independent
biological accuracy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CHROM = "chr17"
WINDOW_BP = 8192
PREFIX_WINDOWS = 1200
PREFIX_BP = WINDOW_BP * PREFIX_WINDOWS


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


def _prefix_contract(contig_lengths: Path) -> dict[str, Any]:
    lengths = _read_lengths(contig_lengths)
    if CHROM not in lengths:
        raise ValueError(f"declared contig lengths do not contain {CHROM}")
    if lengths[CHROM] < PREFIX_BP:
        raise ValueError(f"{CHROM} is shorter than the fixed 1200-window prefix")
    return {"source": str(contig_lengths), "required": {CHROM: PREFIX_BP}}


def build_contract(
    assembly: Path,
    truth: Path,
    unknown_mask: Path,
    contig_lengths: Path,
    hite_sif: Path,
    output_root: Path,
    *,
    model_prediction: Path | None = None,
) -> dict[str, Any]:
    """Build a contract without executing any command or writing assets."""
    length_contract = _prefix_contract(contig_lengths)
    output_root = Path(output_root)
    prefix_fasta = output_root / f"{CHROM}.prefix-{PREFIX_BP}.fa"
    prefix_truth = output_root / f"{CHROM}.prefix-{PREFIX_BP}.truth.bed"
    prefix_unknown = output_root / f"{CHROM}.prefix-{PREFIX_BP}.unknown.bed"
    prefix_lengths = output_root / f"{CHROM}.prefix-{PREFIX_BP}.lengths.json"
    hite_dir = output_root / "hite"
    hite_gff = hite_dir / "HiTE.gff"
    hite_canonical = output_root / "hite.canonical.tsv"
    adapter = Path(__file__).resolve().parents[1] / "LEMMI-TE-BENCH-20260824-R1" / "adapter.py"

    prefix = {
        "seqid": CHROM,
        "start": 0,
        "end": PREFIX_BP,
        "end_is_exclusive": True,
        "window_bp": WINDOW_BP,
        "windows": PREFIX_WINDOWS,
    }
    methods: dict[str, str] = {"hite": str(hite_canonical)}
    if model_prediction is not None:
        methods["model"] = str(model_prediction)

    return {
        "status": "CONTRACT_ONLY",
        "profile": "TE-STRUCTURE-PILOT-20260825-R1-HITE-CHR17",
        "execution": "commands_not_run",
        "claim_scope": "RepeatMasker-comparator agreement only",
        "truth_is_independent_biological_gold": False,
        "coordinate_convention": "zero_based_half_open",
        "prefix": prefix,
        "inputs": {
            "assembly": str(assembly),
            "truth": str(truth),
            "unknown_mask": str(unknown_mask),
            "contig_lengths": str(contig_lengths),
            "hite_sif": str(hite_sif),
        },
        "assembly_length_contract": length_contract,
        "commands": [
            {
                "id": "crop_assembly",
                "shell": (
                    f"samtools faidx {assembly} {CHROM}:1-{PREFIX_BP} "
                    f"| sed '1c\\>{CHROM}' > {prefix_fasta}"
                ),
                "stdout": str(prefix_fasta),
                "coordinate_contract": (
                    "samtools 1-based inclusive syntax maps to 0-based [0,end); "
                    "the region header is rewritten to chr17 so HiTE and truth share seqid"
                ),
            },
            {
                "id": "crop_truth",
                "operation": "crop_bed_zero_based_half_open",
                "input": str(truth),
                "output": str(prefix_truth),
                "interval": [CHROM, 0, PREFIX_BP],
            },
            {
                "id": "crop_unknown_mask",
                "operation": "crop_bed_zero_based_half_open",
                "input": str(unknown_mask),
                "output": str(prefix_unknown),
                "interval": [CHROM, 0, PREFIX_BP],
            },
            {
                "id": "project_contig_lengths",
                "operation": "project_declared_length",
                "input": str(contig_lengths),
                "output": str(prefix_lengths),
                "required": {CHROM: PREFIX_BP},
            },
            {
                "id": "run_hite",
                "argv": [
                    "apptainer", "exec", "--cleanenv", str(hite_sif),
                    "python", "/HiTE/main.py",
                    "--genome", str(prefix_fasta),
                    "--thread", "$SLURM_CPUS_PER_TASK",
                    "--plant", "0", "--annotate", "1",
                    "--out_dir", str(hite_dir),
                ],
                "expected_output": str(hite_gff),
            },
            {
                "id": "convert_hite_gff",
                "argv": [
                    "python3", str(adapter), "convert",
                    "--input", str(hite_gff),
                    "--output", str(hite_canonical),
                    "--format", "gff3",
                ],
            },
        ],
        "evaluation_contract": {
            "methods": methods,
            "truth": str(prefix_truth),
            "unknown_mask": str(prefix_unknown),
            "contig_lengths": str(prefix_lengths),
            "same_truth_and_mask_for_all_methods": True,
            "mask_policy": "exclude unknown bases before bp and interval metrics; never count them as negatives",
            "truth_semantics": "RepeatMasker-derived human comparator runs",
            "overlap_policy": "flat_union",
            "segment_iou": 0.8,
            "boundary_tolerances_bp": [5, 25],
            "short_prediction_bp": 80,
            "metrics": [
                "bp_precision_agreement",
                "bp_recall_agreement",
                "bp_f1_agreement",
                "segment_f1_agreement_iou_0_8",
                "boundary_f1_agreement_5bp",
                "boundary_f1_agreement_25bp",
                "short_prediction_rate",
                "mean_fragments_per_comparator_run",
                "split_comparator_run_rate",
                "missed_comparator_run_rate",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--unknown-mask", type=Path, required=True)
    parser.add_argument("--contig-lengths", type=Path, required=True)
    parser.add_argument("--hite-sif", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model-prediction", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_contract(
        args.assembly,
        args.truth,
        args.unknown_mask,
        args.contig_lengths,
        args.hite_sif,
        args.output_root,
        model_prediction=args.model_prediction,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
