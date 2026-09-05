#!/usr/bin/env python3
"""One real-model synthetic inference pass; check streamed interface products."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

import infer_fasta as interface


def read_bed(path):
    result = {}
    for line in path.read_text().splitlines():
        chrom, start, end = line.split("\t")
        result.setdefault(chrom, []).append((int(start), int(end)))
    return result


def run(args):
    root = args.output_dir
    root.mkdir(parents=True, exist_ok=False)
    # Synthetic only: two full windows, a nine-base tail, a five-base contig.
    records = {"synthetic_long": "ACGT" * 2050 + "N", "synthetic_short": "aNRyt"}
    fasta = root / "synthetic.fa"
    fasta.write_text("".join(f">{name}\n{sequence}\n" for name, sequence in records.items()))
    captured = []
    original = interface.core.infer_half_margins

    def capture(*values, **kwargs):
        margins = original(*values, **kwargs)
        captured.extend(margin.copy() for margin in margins)
        return margins

    options = argparse.Namespace(
        fasta=fasta, model_dir=args.model_dir, tokenizer_dir=args.model_dir,
        model_code_dir=args.model_code_dir, calibration_json=args.calibration_json,
        output_dir=root / "prediction", batch_size=2, cpu=True,
    )
    # Capture this same pass, never repeat model inference for comparison.
    with patch.object(interface.core, "infer_half_margins", side_effect=capture):
        summary = interface.run(options)
    expected = {}
    offset = 0
    for chrom, sequence in records.items():
        count = (len(sequence) + interface.WINDOW_BP - 1) // interface.WINDOW_BP
        expected[chrom] = np.concatenate([
            interface.core.sigmoid(summary["platt_slope"] * margin + summary["platt_intercept"])
            for margin in captured[offset:offset + count]
        ])
        assert len(expected[chrom]) == len(sequence)
        offset += count
    assert offset == len(captured) == 4
    cursor = dict.fromkeys(records, 0)
    with gzip.open(root / "prediction/material_probability.bedGraph.gz", "rt") as handle:
        for line in handle:
            chrom, left, right, value = line.split("\t")
            left, right, value = int(left), int(right), float(value)
            assert chrom in records and left == cursor[chrom] and left < right <= len(records[chrom])
            assert np.all(expected[chrom][left:right] == value)
            cursor[chrom] = right
    assert cursor == {name: len(sequence) for name, sequence in records.items()}
    material = read_bed(root / "prediction/material_runs.bed")
    ambiguity = read_bed(root / "prediction/ambiguity_qc.bed")
    for name, sequence in records.items():
        assert material.get(name, []) == interface.core.runs_from_bool(expected[name] >= summary["threshold"])
        qc = np.array([base not in "ACGT" for base in sequence.upper()])
        assert ambiguity.get(name, []) == interface.core.runs_from_bool(qc)
    result = {
        "protocol": "CROSS-SPECIES-L1-FASTA-INFERENCE-V1", "status": "PASS",
        "scope": "synthetic sequence-only engineering; no accuracy or generalization endpoint",
        "real_model_forward_passes": "one pass over four windows; no second inference",
        "window_lengths_bp": [len(row) for row in captured], "input_bp": 8206,
        "probabilities_exactly_match_captured_legacy_helper": True,
        "complete_half_open_coordinates": True, "material_runs_match_frozen_threshold": True,
        "ambiguity_qc_matches_input_only": True, "labels_read": False,
        "conf_or_sealed_data_read": False, "gpu_requested": False,
        "inference_summary": str((root / "prediction/summary.json").resolve()),
    }
    (root / "smoke_report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-code-dir", type=Path, required=True)
    parser.add_argument("--calibration-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    print(json.dumps(run(parser.parse_args()), indent=2, sort_keys=True))
