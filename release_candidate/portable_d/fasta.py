"""FASTA parsing and streaming sequence-only outputs."""

from __future__ import annotations

import gzip
import itertools
import json
from pathlib import Path

import numpy as np

from .bundle import Bundle, WINDOW_BP
from .model import infer_half_margins, load_model_and_tokenizer, sigmoid


DNA_SYMBOLS = frozenset("ACGTRYSWKMBDHVN")


def read_fasta(path: Path):
    """Yield unique uppercase contigs while retaining supported IUPAC symbols."""
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    seen: set[str] = set()
    name = None
    parts: list[str] = []
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
                    raise ValueError(
                        f"unsupported DNA symbols at line {line_number}: {sorted(invalid)}"
                    )
                parts.append(sequence)
    if name is None:
        raise ValueError("empty FASTA input")
    if not parts:
        raise ValueError(f"empty FASTA contig: {name}")
    yield name, "".join(parts)


class TrackWriter:
    """Stream exact-value BED/bedGraph runs across window boundaries."""

    def __init__(self, handle, chrom: str, probability: bool = False):
        self.handle = handle
        self.chrom = chrom
        self.probability = probability
        self.pending = None
        self.intervals = 0

    def flush(self) -> None:
        if self.pending is None:
            return
        start, end, value = self.pending
        if self.probability or value:
            suffix = f"\t{float(value):.17g}" if self.probability else ""
            self.handle.write(f"{self.chrom}\t{start}\t{end}{suffix}\n")
            self.intervals += 1
        self.pending = None

    def append(self, offset: int, values: np.ndarray) -> None:
        boundaries = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1, len(values)]
        for left, right in zip(boundaries[:-1], boundaries[1:]):
            start, end, value = offset + int(left), offset + int(right), values[left]
            if self.pending is not None and self.pending[1] == start and self.pending[2] == value:
                self.pending = (self.pending[0], end, value)
            else:
                self.flush()
                self.pending = (start, end, value)


def _output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "probability_bedgraph": output_dir / "material_probability.bedGraph",
        "material_bed": output_dir / "material_runs.bed",
        "ambiguity_qc_bed": output_dir / "ambiguity_qc.bed",
        "softmasked_fasta": output_dir / "softmasked.fa",
        "summary_json": output_dir / "summary.json",
    }


def run(
    bundle: Bundle,
    fasta_path: Path,
    output_dir: Path,
    device: str = "auto",
    batch_size: int = 12,
    cpu_threads: int = 0,
) -> dict:
    """Run sequence-only D inference and write probability/material/softmask tracks."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    output_paths = _output_paths(output_dir)
    for path in output_paths.values():
        if path.exists():
            raise FileExistsError(f"output already exists; use a new directory: {path}")
    records = read_fasta(fasta_path)
    first = next(records)
    record_stream = itertools.chain((first,), records)
    del first
    model, tokenizer, actual_device = load_model_and_tokenizer(
        bundle, device_request=device, cpu_threads=cpu_threads
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    slope = float(bundle.calibration["platt_slope"])
    intercept = float(bundle.calibration["platt_intercept"])
    threshold = float(bundle.calibration["threshold"])
    contigs = []
    with output_paths["probability_bedgraph"].open("x") as probabilities, \
            output_paths["material_bed"].open("x") as material, \
            output_paths["ambiguity_qc_bed"].open("x") as ambiguity, \
            output_paths["softmasked_fasta"].open("x") as softmasked:
        for name, sequence in record_stream:
            tracks = (
                TrackWriter(probabilities, name, True),
                TrackWriter(material, name),
                TrackWriter(ambiguity, name),
            )
            softmasked.write(f">{name}\n")
            positive_bp = ambiguous_bp = windows = 0
            for batch_start in range(0, len(sequence), WINDOW_BP * batch_size):
                starts = list(
                    range(
                        batch_start,
                        min(len(sequence), batch_start + WINDOW_BP * batch_size),
                        WINDOW_BP,
                    )
                )
                windows_seq = [sequence[start : start + WINDOW_BP] for start in starts]
                margins = infer_half_margins(
                    model, tokenizer, actual_device, windows_seq, batch_size
                )
                if len(margins) != len(windows_seq):
                    raise ValueError("inference returned the wrong number of windows")
                for start, window, margin in zip(starts, windows_seq, margins):
                    margin = np.asarray(margin)
                    if margin.shape != (len(window),) or not np.isfinite(margin).all():
                        raise ValueError(f"invalid projected margins for {name}:{start}")
                    probability = sigmoid(slope * margin + intercept)
                    predicted = probability >= threshold
                    symbols = np.frombuffer(window.encode("ascii"), dtype="S1")
                    ambiguous_values = ~np.isin(symbols, [b"A", b"C", b"G", b"T"])
                    for track, values in zip(
                        tracks, (probability, predicted, ambiguous_values)
                    ):
                        track.append(start, values)
                    # Keep the inference uncensored in probability/BED/QC
                    # outputs. For the downstream softmask, only canonical
                    # bases are lowercased; predicted IUPAC/N stays uppercase.
                    softmasked.write(
                        "".join(
                            base.lower() if masked and base in "ACGT" else base.upper()
                            for base, masked in zip(window, predicted)
                        )
                        + "\n"
                    )
                    positive_bp += int(predicted.sum())
                    ambiguous_bp += int(ambiguous_values.sum())
                    windows += 1
            for track in tracks:
                track.flush()
            contigs.append(
                {
                    "name": name,
                    "length_bp": len(sequence),
                    "windows": windows,
                    "threshold_positive_bp": positive_bp,
                    "ambiguous_bp": ambiguous_bp,
                    "material_runs": tracks[1].intervals,
                    "ambiguity_runs": tracks[2].intervals,
                }
            )
    summary = {
        "protocol": "portable-d-te/v1",
        "upstream_inference_protocol": "CROSS-SPECIES-L1-FASTA-INFERENCE-V1",
        "status": "COMPLETED",
        "model_id": bundle.manifest["model_id"],
        "bundle_root": str(bundle.root.resolve()),
        "input_fasta": str(Path(fasta_path).resolve()),
        "calibration_json": str(bundle.calibration_path.resolve()),
        "calibration_protocol": bundle.calibration.get("calibration_protocol"),
        "calibration_scope": bundle.calibration["calibration_scope"],
        "fit_split": "CAL",
        "seed": bundle.calibration.get("seed"),
        "platt_slope": slope,
        "platt_intercept": intercept,
        "threshold": threshold,
        "threshold_rule": "probability >= frozen CAL threshold",
        "window_bp": WINDOW_BP,
        "window_alignment": "nonoverlapping, contig origin 0",
        "tail_policy": "actual sequence length; NTv2 tokenizer padding only",
        "coordinates": "0-based half-open",
        "device": str(actual_device),
        "batch_size": batch_size,
        "ambiguity_policy": "uppercase IUPAC; <unk> tokenization; no prediction censoring",
        "softmask_policy": "lowercase threshold-positive ACGT only; keep IUPAC/N uppercase",
        "interpretation": "TE-material connected runs, not insertion IDs; no scientific evaluation",
        "scientific_metrics_computed": False,
        "labels_used": False,
        "contigs": contigs,
        "total_bp": sum(item["length_bp"] for item in contigs),
        "outputs": {key: str(path.resolve()) for key, path in output_paths.items()},
    }
    with output_paths["summary_json"].open("x") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return summary
