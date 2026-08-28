#!/usr/bin/env python3
"""Materialize the matched Human chr17 D1 truth and model intervals.

The existing matched Human checkpoints were evaluated on the first 1,200
records of the held-out test JSONL.  This entry point uses that exact record
prefix for both the reference labels and inference, then writes canonical
zero-based half-open intervals for ``length_stratified_eval.py``.  Unknown
label positions are not emitted as predictions, so the D1 denominator is the
same known-base prefix used by the source records.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import importlib.util
from pathlib import Path
from typing import Any, Iterator


WINDOW = 8192
PREFIX_WINDOWS = 1200
CHROM = "chr17"
PREFIX_BP = WINDOW * PREFIX_WINDOWS
UNKNOWN_LABEL = -100
FIELDS = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]


def _open_jsonl(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def iter_windows(path: Path, max_windows: int = PREFIX_WINDOWS) -> Iterator[dict[str, Any]]:
    """Yield the fixed Human test prefix and reject coordinate drift."""
    if max_windows != PREFIX_WINDOWS:
        raise ValueError(f"D1 is frozen to exactly {PREFIX_WINDOWS} windows")
    count = 0
    with _open_jsonl(path) as handle:
        for index, line in enumerate(handle):
            if index >= max_windows:
                break
            count += 1
            record = json.loads(line)
            validate_record(index, record)
            yield record
    if count != max_windows:
        raise ValueError(f"expected exactly {max_windows} Human test records")


def validate_record(index: int, record: dict[str, Any]) -> None:
    if record.get("chr") != CHROM:
        raise ValueError(f"record {index} is not {CHROM}")
    expected_start = index * WINDOW
    if int(record["start"]) != expected_start or int(record["end"]) != expected_start + WINDOW:
        raise ValueError(f"record {index} is not the contiguous 8192-bp prefix")
    sequence = record["sequence"]
    labels = record["labels"]
    if not isinstance(sequence, str) or len(sequence) != WINDOW:
        raise ValueError(f"record {index} sequence length is not {WINDOW}")
    if not isinstance(labels, list) or len(labels) != WINDOW or any(value not in {UNKNOWN_LABEL, 0, 1} for value in labels):
        raise ValueError(f"record {index} labels are not a {WINDOW}-base {{{UNKNOWN_LABEL}, 0, 1}} vector")


def runs(values: Any, positive: int = 1) -> list[tuple[int, int]]:
    """Return contiguous half-open runs equal to ``positive``."""
    output: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(values):
        if value == positive and start is None:
            start = index
        elif value != positive and start is not None:
            output.append((start, index))
            start = None
    if start is not None:
        output.append((start, len(values)))
    return output


def canonical_rows(intervals: list[tuple[int, int]], name: str) -> list[dict[str, str | int]]:
    return [
        {
            "seqid": CHROM,
            "start": start,
            "end": end,
            "name": name,
            "score": "0",
            "strand": ".",
            "source": "TE-STRUCTURE-D1",
            "attributes": ".",
        }
        for start, end in intervals
    ]


def write_canonical(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _load_strict_module():
    path = Path(__file__).resolve().parents[3] / "pipelines" / "PIPE-TEFM-FINAL-20260623" / "strict_segment_eval.py"
    spec = importlib.util.spec_from_file_location("tefm_strict_segment_eval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load strict evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_truth(args: argparse.Namespace) -> dict[str, Any]:
    labels = [value for record in iter_windows(args.data_jsonl) for value in record["labels"]]
    if len(labels) != PREFIX_BP:
        raise ValueError(f"assembled labels have {len(labels)} bases, expected {PREFIX_BP}")
    truth = canonical_rows(runs(labels, 1), "human_reference_te")
    unknown = canonical_rows(runs(labels, UNKNOWN_LABEL), "human_unknown")
    write_canonical(args.out_truth, truth)
    write_canonical(args.out_unknown, unknown)
    args.out_lengths.parent.mkdir(parents=True, exist_ok=True)
    args.out_lengths.write_text(json.dumps({CHROM: PREFIX_BP}, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": "PASS",
        "profile": "TE-STRUCTURE-PILOT-20260825-R1-D1-HUMAN-TRUTH",
        "windows": PREFIX_WINDOWS,
        "window_bp": WINDOW,
        "prefix": {"seqid": CHROM, "start": 0, "end": PREFIX_BP},
        "truth": str(args.out_truth),
        "unknown": str(args.out_unknown),
        "known_bp": PREFIX_BP - sum(end - start for start, end in runs(labels, UNKNOWN_LABEL)),
        "unknown_bp": sum(end - start for start, end in runs(labels, UNKNOWN_LABEL)),
        "lengths": str(args.out_lengths),
        "claim_scope": "Human held-out comparator labels from the materialized test JSONL",
    }
    if args.out_manifest is not None:
        args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.out_manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def predict(args: argparse.Namespace) -> dict[str, Any]:
    strict = _load_strict_module()
    import numpy as np
    import torch

    records = list(iter_windows(args.data_jsonl))
    labels = np.asarray([value for record in records for value in record["labels"]], dtype=np.int8)
    if labels.size != PREFIX_BP:
        raise ValueError(f"assembled labels have {labels.size} bases, expected {PREFIX_BP}")
    model, tokenizer, meta = strict.load_trained_model(str(args.model_dir))
    label_mode = str(meta.get("token_label_mode", ""))
    if label_mode != "single_nt_nospecial":
        raise ValueError(f"matched D1 requires single_nt_nospecial, got {label_mode}")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    model.to(device)
    model.eval()
    probability = np.zeros(PREFIX_BP, dtype=np.float32)
    covered = np.zeros(PREFIX_BP, dtype=np.float32)
    weights = strict.center_weights(WINDOW, args.weight_mode)
    for index, record in enumerate(records):
        start = index * WINDOW
        end = start + WINDOW
        values = strict.infer_probs_for_label_mode(
            model, tokenizer, record["sequence"], WINDOW, device, label_mode
        )
        if values.shape != (WINDOW,):
            raise ValueError(f"model returned {values.shape} probabilities for record {index}")
        probability[start:end] += values * weights
        covered[start:end] += weights
    if not np.all(covered > 0):
        raise ValueError("D1 prediction coverage has uncovered bases")
    probability /= covered
    predicted = probability >= args.threshold
    predicted[labels < 0] = False
    rows = canonical_rows(
        runs(predicted.astype(np.int8).tolist(), 1),
        args.model_name,
    )
    write_canonical(args.out_prediction, rows)
    result = {
        "status": "PASS",
        "profile": "TE-STRUCTURE-PILOT-20260825-R1-D1-HUMAN-PREDICTION",
        "model_name": args.model_name,
        "model_dir": str(args.model_dir),
        "data_jsonl": str(args.data_jsonl),
        "windows": PREFIX_WINDOWS,
        "window_bp": WINDOW,
        "prefix": {"seqid": CHROM, "start": 0, "end": PREFIX_BP},
        "device": str(device),
        "weight_mode": args.weight_mode,
        "threshold": args.threshold,
        "ignored_bp": int((labels < 0).sum()),
        "prediction_intervals": len(rows),
        "prediction": str(args.out_prediction),
        "claim_scope": "Human held-out comparator agreement; unknown label positions excluded",
    }
    if args.out_manifest is not None:
        args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.out_manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    truth = sub.add_parser("truth")
    truth.add_argument("--data-jsonl", type=Path, required=True)
    truth.add_argument("--out-truth", type=Path, required=True)
    truth.add_argument("--out-unknown", type=Path, required=True)
    truth.add_argument("--out-lengths", type=Path, required=True)
    truth.add_argument("--out-manifest", type=Path)
    pred = sub.add_parser("predict")
    pred.add_argument("--data-jsonl", type=Path, required=True)
    pred.add_argument("--model-dir", type=Path, required=True)
    pred.add_argument("--model-name", required=True)
    pred.add_argument("--out-prediction", type=Path, required=True)
    pred.add_argument("--out-manifest", type=Path)
    pred.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    pred.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    pred.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    result = write_truth(args) if args.command == "truth" else predict(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
