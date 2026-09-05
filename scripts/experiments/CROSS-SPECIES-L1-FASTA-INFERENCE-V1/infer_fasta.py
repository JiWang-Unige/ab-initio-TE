#!/usr/bin/env python3
"""Sequence-only material prediction with an existing frozen L1 shared CAL artifact.

No labels, fitting, smoothing, or insertion reconstruction. A missing summary.json
means the output is incomplete; failed runs can leave partial streamed tracks.
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np

HELPER_PATH = Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903" / "calibrate_evaluate_x0.py"
SPEC = importlib.util.spec_from_file_location("l1_fasta_helpers", HELPER_PATH)
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)
WINDOW_BP = core.WINDOW_BP
DNA_SYMBOLS = frozenset("ACGTRYSWKMBDHVN")


def read_fasta(path: Path):
    """Yield uppercase contigs, retaining IUPAC ambiguity and reading one at a time."""
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    seen = set()
    name = None
    parts = []
    with opener(path, "rt") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    if not parts:
                        raise ValueError(f"empty FASTA contig: {name}")
                    yield name, "".join(parts)
                header = line[1:].split()
                if not header:
                    raise ValueError(f"empty FASTA header at line {line_number}")
                name = header[0]
                if name in seen:
                    raise ValueError(f"duplicate FASTA contig: {name}")
                seen.add(name)
                parts = []
            else:
                if name is None:
                    raise ValueError(f"sequence before FASTA header at line {line_number}")
                sequence = line.upper()
                invalid = set(sequence) - DNA_SYMBOLS
                if invalid:
                    raise ValueError(f"unsupported DNA symbols at line {line_number}: {sorted(invalid)}")
                parts.append(sequence)
    if name is None:
        raise ValueError("empty FASTA input")
    if not parts:
        raise ValueError(f"empty FASTA contig: {name}")
    yield name, "".join(parts)


def load_calibration(args) -> dict:
    calibration = json.loads(args.calibration_json.read_text())
    expected_paths = {
        "model_dir": str(args.model_dir.resolve()),
        "tokenizer_dir": str((args.tokenizer_dir or args.model_dir).resolve()),
        "model_code_dir": str(args.model_code_dir.resolve()) if args.model_code_dir else None,
    }
    for key, expected in expected_paths.items():
        if calibration.get(key) != expected:
            raise ValueError(f"calibration artifact belongs to a different {key}")
    if (calibration.get("calibration_scope") != "six-species-shared"
            or calibration.get("fit_split") != "CAL"
            or sorted(calibration.get("species", [])) != sorted(core.CAL_SPECIES)):
        raise ValueError("requires the existing six-species-shared CAL calibration")
    protocol = calibration.get("calibration_protocol", calibration.get("protocol"))
    if protocol != "CROSS-SPECIES-L1-X0-PLATT-V1":
        raise ValueError("unsupported calibration protocol")
    for key in ("platt_slope", "platt_intercept", "threshold"):
        if not np.isfinite(float(calibration[key])):
            raise ValueError(f"non-finite calibration {key}")
    if float(calibration["threshold_selection"]["threshold"]) != float(calibration["threshold"]):
        raise ValueError("calibration threshold differs from its frozen selection")
    return calibration


class TrackWriter:
    """Stream exact-value runs, carrying a single pending interval across chunks."""

    def __init__(self, handle, chrom, probability=False):
        self.handle, self.chrom, self.probability = handle, chrom, probability
        self.pending = None
        self.intervals = 0

    def flush(self):
        if self.pending is not None:
            start, end, value = self.pending
            if self.probability or value:
                suffix = f"\t{float(value):.17g}" if self.probability else ""
                self.handle.write(f"{self.chrom}\t{start}\t{end}{suffix}\n")
                self.intervals += 1
            self.pending = None

    def append(self, offset, values):
        boundaries = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1, len(values)]
        for left, right in zip(boundaries[:-1], boundaries[1:]):
            start, end, value = offset + int(left), offset + int(right), values[left]
            if self.pending is not None and self.pending[1] == start and self.pending[2] == value:
                self.pending = (self.pending[0], end, value)
            else:
                self.flush()
                self.pending = (start, end, value)


def run(args) -> dict:
    if args.batch_size < 1:
        raise ValueError("batch-size must be positive")
    calibration = load_calibration(args)
    records = read_fasta(args.fasta)
    first = next(records)  # Reject an empty/invalid first contig before loading weights.
    record_stream = itertools.chain((first,), records)
    del first
    output_paths = {
        "probability_bedgraph_gz": args.output_dir / "material_probability.bedGraph.gz",
        "material_bed": args.output_dir / "material_runs.bed",
        "ambiguity_qc_bed": args.output_dir / "ambiguity_qc.bed",
        "summary_json": args.output_dir / "summary.json",
    }
    for path in output_paths.values():
        if path.exists():
            raise FileExistsError(f"output already exists; use a new output directory: {path}")
    model, tokenizer, device = core.load_final_model(
        args.model_dir, args.tokenizer_dir, args.cpu, args.model_code_dir
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    contigs = []
    slope, intercept, threshold = (float(calibration[key]) for key in
                                   ("platt_slope", "platt_intercept", "threshold"))
    with gzip.open(output_paths["probability_bedgraph_gz"], "xt") as probabilities, \
            output_paths["material_bed"].open("x") as material, \
            output_paths["ambiguity_qc_bed"].open("x") as ambiguity:
        for name, sequence in record_stream:
            tracks = (TrackWriter(probabilities, name, True),
                      TrackWriter(material, name), TrackWriter(ambiguity, name))
            positive_bp = ambiguous_bp = windows = 0
            for batch_start in range(0, len(sequence), WINDOW_BP * args.batch_size):
                starts = list(range(batch_start, min(len(sequence), batch_start + WINDOW_BP * args.batch_size), WINDOW_BP))
                sequences = [sequence[start:start + WINDOW_BP] for start in starts]
                margins = core.infer_half_margins(model, tokenizer, device, sequences, args.batch_size)
                if len(margins) != len(sequences):
                    raise ValueError("inference returned the wrong number of windows")
                for start, window, margin in zip(starts, sequences, margins):
                    margin = np.asarray(margin)
                    if margin.shape != (len(window),) or not np.isfinite(margin).all():
                        raise ValueError(f"invalid projected margins for {name}:{start}")
                    # Keep the evaluator's float32 margin -> Platt arithmetic unchanged.
                    probability = core.sigmoid(slope * margin + intercept)
                    predicted = probability >= threshold
                    symbols = np.frombuffer(window.encode("ascii"), dtype="S1")
                    ambiguous = ~np.isin(symbols, [b"A", b"C", b"G", b"T"])
                    for track, values in zip(tracks, (probability, predicted, ambiguous)):
                        track.append(start, values)
                    positive_bp += int(predicted.sum())
                    ambiguous_bp += int(ambiguous.sum())
                    windows += 1
            for track in tracks:
                track.flush()
            contigs.append({"name": name, "length_bp": len(sequence), "windows": windows,
                            "threshold_positive_bp": positive_bp, "ambiguous_bp": ambiguous_bp,
                            "material_runs": tracks[1].intervals, "ambiguity_runs": tracks[2].intervals})
    summary = {
        "protocol": "CROSS-SPECIES-L1-FASTA-INFERENCE-V1", "status": "COMPLETED",
        "input_fasta": str(args.fasta.resolve()), "model_dir": calibration["model_dir"],
        "tokenizer_dir": calibration["tokenizer_dir"], "model_code_dir": calibration["model_code_dir"],
        "calibration_json": str(args.calibration_json.resolve()), "seed": calibration["seed"],
        "calibration_scope": calibration["calibration_scope"], "fit_split": "CAL",
        "platt_slope": slope, "platt_intercept": intercept, "threshold": threshold,
        "threshold_rule": "probability >= frozen CAL threshold",
        "window_bp": WINDOW_BP, "window_alignment": "nonoverlapping, contig origin 0",
        "tail_policy": "actual sequence length; existing NTv2 tokenizer padding only",
        "coordinates": "0-based half-open", "device": str(device), "batch_size": args.batch_size,
        "ambiguity_policy": "uppercase IUPAC; existing <unk> tokenization; no prediction censoring",
        "interpretation": "TE material connected runs, not insertion IDs; no scientific evaluation",
        "scientific_metrics_computed": False, "labels_used": False,
        "contigs": contigs, "total_bp": sum(item["length_bp"] for item in contigs),
        "outputs": {key: str(path.resolve()) for key, path in output_paths.items()},
    }
    with output_paths["summary_json"].open("x") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return summary


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fasta", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path)
    parser.add_argument("--model-code-dir", type=Path)
    parser.add_argument("--calibration-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--cpu", action="store_true")
    return parser


if __name__ == "__main__":
    print(json.dumps(run(build_parser().parse_args()), indent=2, sort_keys=True))
