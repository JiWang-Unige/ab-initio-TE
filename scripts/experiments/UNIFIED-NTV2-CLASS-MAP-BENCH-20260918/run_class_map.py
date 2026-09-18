#!/usr/bin/env python3
"""Run the validation-selected NTv2 eight-state class head on fixed targets.

The loader and six-base token projection are imported from the matched
representation experiment.  This runner only performs native argmax inference
and writes per-base ontology runs; it never reads comparator labels.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
REP = ROOT / "scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
sys.path.insert(0, str(REP))
from train_matched_class import LABEL_NAMES, sequence_tokens  # noqa: E402
from extract_matched_ntv2 import native_token_classifier  # noqa: E402


WINDOW_BP = 4096
NONCALLABLE = "NONCALLABLE"
ALLOWED = set("ACGTRYSWKMBDHVN")


def fasta_records(path: Path):
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    name = None
    chunks: list[str] = []
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks)
                fields = line[1:].split()
                if not fields:
                    raise ValueError(f"empty FASTA header at {path}:{line_no}")
                name = fields[0]
                chunks = []
            else:
                if name is None:
                    raise ValueError(f"sequence before FASTA header at {path}:{line_no}")
                sequence = line.upper()
                invalid = set(sequence) - ALLOWED
                if invalid:
                    raise ValueError(f"unsupported sequence symbols at {path}:{line_no}: {sorted(invalid)}")
                chunks.append(sequence)
    if name is not None:
        yield name, "".join(chunks)


class RunWriter:
    def __init__(self, handle, chrom: str):
        self.handle = handle
        self.chrom = chrom
        self.pending: tuple[int, int, str] | None = None
        self.intervals = 0

    def flush(self) -> None:
        if self.pending is not None:
            start, end, label = self.pending
            self.handle.write(f"{self.chrom}\t{start}\t{end}\t{label}\n")
            self.intervals += 1
            self.pending = None

    def append(self, offset: int, labels: np.ndarray) -> None:
        if labels.ndim != 1:
            raise ValueError("run labels must be one-dimensional")
        boundaries = np.r_[0, np.flatnonzero(labels[1:] != labels[:-1]) + 1, len(labels)]
        for left, right in zip(boundaries[:-1], boundaries[1:]):
            start, end = offset + int(left), offset + int(right)
            label = str(labels[left])
            if self.pending is not None and self.pending[1] == start and self.pending[2] == label:
                self.pending = (self.pending[0], end, label)
            else:
                self.flush()
                self.pending = (start, end, label)


def encode_and_predict(model: Any, tokenizer: Any, sequences: list[str], device: Any) -> list[np.ndarray]:
    import torch

    token_rows = [sequence_tokens(sequence) for sequence in sequences]
    max_tokens = max(len(row) for row in token_rows)
    max_length = ((max_tokens + 2 + 7) // 8) * 8
    encoded = tokenizer(
        token_rows,
        is_split_into_words=True,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_special_tokens_mask=True,
        return_tensors="pt",
    )
    special = encoded.pop("special_tokens_mask")
    encoded = {key: value.to(device) for key, value in encoded.items() if key in {"input_ids", "attention_mask"}}
    with torch.inference_mode():
        logits = model(**encoded).logits
    predictions: list[np.ndarray] = []
    for row_index, (sequence, tokens) in enumerate(zip(sequences, token_rows)):
        positions = [
            index
            for index, (attended, is_special) in enumerate(
                zip(encoded["attention_mask"][row_index].tolist(), special[row_index].tolist())
            )
            if attended and not is_special
        ]
        if len(positions) != len(tokens):
            raise RuntimeError(
                f"native token count {len(positions)} != six-base projection count {len(tokens)}"
            )
        token_labels = logits[row_index, positions].argmax(dim=-1).detach().cpu().numpy()
        labels: list[str] = []
        for token, label_id in zip(tokens, token_labels.tolist()):
            if int(label_id) not in range(len(LABEL_NAMES)):
                raise RuntimeError(f"invalid class argmax {label_id}")
            labels.extend([LABEL_NAMES[int(label_id)]] * len(token))
        if len(labels) != len(sequence):
            raise RuntimeError(f"projected label length {len(labels)} != sequence length {len(sequence)}")
        values = np.asarray(labels, dtype=object)
        values[np.asarray([base not in "ACGT" for base in sequence], dtype=bool)] = NONCALLABLE
        predictions.append(values)
    return predictions


def run(args: argparse.Namespace) -> dict[str, Any]:
    import torch

    if args.batch_size < 1:
        raise ValueError("batch-size must be positive")
    if not args.class_model.is_dir():
        raise FileNotFoundError(f"class checkpoint directory missing: {args.class_model}")
    if not ((args.class_model / "pytorch_model.bin").is_file() or (args.class_model / "model.safetensors").is_file()):
        raise FileNotFoundError(f"class checkpoint has no model weights: {args.class_model}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(f"refusing to reuse non-empty output: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = list(fasta_records(args.fasta))
    if not records:
        raise ValueError(f"empty target FASTA: {args.fasta}")
    target_names = set(args.targets.split(",")) if args.targets else {name for name, _ in records}
    records = [(name, sequence) for name, sequence in records if name in target_names]
    if set(name for name, _ in records) != target_names:
        raise ValueError(f"target FASTA names differ from requested targets: {target_names}")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")

    started = time.time()
    model, tokenizer = native_token_classifier(args.class_model, args.base_model)
    model.to(device)
    model.eval()
    output_runs = args.output_dir / "predicted_classes.bed.gz"
    summary_path = args.output_dir / "summary.json"
    summaries = []
    label_counts = {name: 0 for name in LABEL_NAMES}
    label_counts[NONCALLABLE] = 0
    with gzip.open(output_runs, "wt", encoding="utf-8") as handle:
        for chrom, sequence in records:
            chrom_started = time.time()
            writer = RunWriter(handle, chrom)
            chrom_counts = {name: 0 for name in LABEL_NAMES}
            chrom_counts[NONCALLABLE] = 0
            windows = 0
            for batch_start in range(0, len(sequence), WINDOW_BP * args.batch_size):
                starts = list(range(batch_start, min(len(sequence), batch_start + WINDOW_BP * args.batch_size), WINDOW_BP))
                windows += len(starts)
                windows_labels = encode_and_predict(
                    model,
                    tokenizer,
                    [sequence[start : start + WINDOW_BP] for start in starts],
                    device,
                )
                for start, labels in zip(starts, windows_labels):
                    writer.append(start, labels)
                    values, counts = np.unique(labels, return_counts=True)
                    for value, count in zip(values.tolist(), counts.tolist()):
                        chrom_counts[str(value)] += int(count)
                        label_counts[str(value)] += int(count)
            writer.flush()
            summaries.append({
                "chromosome": chrom,
                "length_bp": len(sequence),
                "acgt_bp": int(sum(base in "ACGT" for base in sequence)),
                "non_acgt_bp": int(sum(base not in "ACGT" for base in sequence)),
                "windows": windows,
                "run_count": writer.intervals,
                "label_counts": chrom_counts,
                "wall_seconds": time.time() - chrom_started,
            })
    result = {
        "protocol": "UNIFIED-NTV2-CLASS-MAP-BENCH-20260918",
        "status": "COMPLETED",
        "species": args.species,
        "assembly": args.assembly,
        "model": {
            "class_model": str(args.class_model.resolve()),
            "base_model": str(args.base_model.resolve()),
            "model_loader": "UNIFIED-NTV2-REPRESENTATION-20260918/extract_matched_ntv2.py:native_token_classifier",
            "token_projection": "UNIFIED-NTV2-REPRESENTATION-20260918/train_matched_class.py:sequence_tokens, six-base tokens plus tail",
            "window_bp": WINDOW_BP,
            "window_alignment": "nonoverlapping, contig origin 0",
            "prediction": "native 8-class argmax projected to base spans; non-ACGT output as NONCALLABLE",
        },
        "input_fasta": str(args.fasta.resolve()),
        "target_chromosomes": [row["chromosome"] for row in summaries],
        "device": str(device),
        "batch_size": args.batch_size,
        "label_map": {str(index): name for index, name in enumerate(LABEL_NAMES)},
        "noncallable_label": NONCALLABLE,
        "labels_used": False,
        "timing": {"wall_seconds": time.time() - started, "bp_per_second": sum(row["length_bp"] for row in summaries) / max(time.time() - started, 1e-12)},
        "label_counts": label_counts,
        "contigs": summaries,
        "outputs": {"predicted_classes_bed_gz": str(output_runs.resolve()), "summary_json": str(summary_path.resolve())},
    }
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fasta", type=Path, required=True)
    parser.add_argument("--class-model", type=Path, required=True)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--species", required=True, choices=("chicken", "zebrafish"))
    parser.add_argument("--assembly", required=True)
    parser.add_argument("--targets", default="chr10,chr20")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", default="cuda")
    print(json.dumps(run(parser.parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
