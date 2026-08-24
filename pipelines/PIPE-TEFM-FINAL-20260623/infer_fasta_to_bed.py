#!/usr/bin/env python3
"""Inference-only CE bridge: frozen FASTA -> canonicalizable prediction BED."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Iterator

WINDOW = 8192
STRIDE = 8192
THRESHOLD = 0.5


def iter_fasta(path: Path) -> Iterator[tuple[str, str]]:
    """Yield one normalized FASTA record at a time, including gzip input."""
    opener = gzip.open if str(path).endswith(".gz") else open
    name: str | None = None
    chunks: list[str] = []
    with opener(path, "rt", encoding="ascii", errors="strict") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks).upper()
                name = line[1:].split()[0]
                if not name:
                    raise ValueError(f"empty FASTA name at line {line_no}")
                chunks = []
            elif name is None:
                raise ValueError(f"FASTA sequence precedes header at line {line_no}")
            else:
                chunks.append(line)
        if name is not None:
            yield name, "".join(chunks).upper()


def load_lengths(path: Path) -> dict[str, int]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value:
        raise ValueError("contig lengths must be a non-empty JSON object")
    lengths: dict[str, int] = {}
    for name, length in value.items():
        if not isinstance(name, str) or not isinstance(length, int) or length < 1:
            raise ValueError(f"invalid contig length for {name!r}")
        lengths[name] = length
    return lengths


def window_specs(length: int, window: int = WINDOW, stride: int = STRIDE) -> list[tuple[int, int]]:
    """Return real-coordinate windows; the final window may be shorter."""
    if length < 1 or window != WINDOW or stride != STRIDE:
        raise ValueError("this frozen bridge requires positive length and 8192/8192 geometry")
    return [(start, min(start + window, length)) for start in range(0, length, stride)]


def expected_window_count(lengths: dict[str, int]) -> int:
    """Count all full or tail-padded windows under the frozen geometry."""
    return sum((length + WINDOW - 1) // WINDOW for length in lengths.values())


def coverage_audit(length: int, specs: list[tuple[int, int]]) -> dict:
    if not specs or specs[0][0] != 0:
        raise ValueError("window coverage does not start at zero")
    missing = 0
    overlap = 0
    previous_end = 0
    for start, end in specs:
        if end <= start or start != previous_end:
            if start > previous_end:
                missing += start - previous_end
            elif start < previous_end:
                overlap += previous_end - start
            raise ValueError(f"non-contiguous window coverage at {start}:{end}")
        previous_end = end
    if previous_end != length:
        missing += length - previous_end
        raise ValueError(f"window coverage ends at {previous_end}, expected {length}")
    return {"windows": len(specs), "covered_bp": length, "missing_bp": missing,
            "overlap_bp": overlap, "no_missing_bp": missing == 0, "no_overlap": overlap == 0}


def threshold_runs(probabilities, threshold: float = THRESHOLD) -> list[tuple[int, int]]:
    """Convert a boolean-like per-base vector into half-open runs."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(probabilities):
        positive = bool(value >= threshold)
        if positive and start is None:
            start = index
        elif not positive and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(probabilities)))
    return runs


def _load_model(model_dir: Path):
    supp = Path(__file__).resolve().parents[1] / "PIPE-TEFM-SUPP-20260617"
    sys.path.insert(0, str(supp))
    from te_token_task import load_trained_model  # type: ignore
    return load_trained_model(str(model_dir))


def _infer_window(model, tokenizer, sequence: str, real_length: int, device, torch):
    if len(sequence) != WINDOW:
        raise ValueError(f"model input length is {len(sequence)}, expected {WINDOW}")
    encoded = tokenizer(sequence, add_special_tokens=False, truncation=True,
                        max_length=WINDOW, padding="max_length", return_tensors="pt")
    input_ids = encoded.get("input_ids")
    attention_mask = encoded.get("attention_mask")
    if input_ids is None or attention_mask is None or input_ids.shape[-1] != WINDOW:
        raise ValueError("tokenizer did not preserve frozen single-nt geometry")
    encoded["attention_mask"] = attention_mask.clone()
    if real_length < WINDOW:
        encoded["attention_mask"][:, real_length:] = 0
    model_inputs = {key: value.to(device) for key, value in encoded.items()
                    if key in {"input_ids", "attention_mask"}}
    with torch.no_grad():
        logits = model(**model_inputs).logits[0]
    if logits.shape[0] < WINDOW or logits.shape[-1] < 2:
        raise ValueError(f"model logits have unexpected shape {tuple(logits.shape)}")
    return torch.softmax(logits, dim=-1)[:real_length, 1].detach().cpu().numpy()


def run(args) -> dict:
    if args.window != WINDOW or args.stride != STRIDE or abs(args.threshold - THRESHOLD) > 1e-12:
        raise ValueError("frozen bridge requires --window 8192 --stride 8192 --threshold 0.5")
    lengths = load_lengths(args.lengths)
    model, tokenizer, meta = _load_model(args.model_dir)
    if str(meta.get("token_label_mode")) != "single_nt_nospecial":
        raise ValueError(f"model token_label_mode is not single_nt_nospecial: {meta.get('token_label_mode')}")
    import torch
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    device = torch.device("cuda" if args.device == "cuda" or
                          (args.device == "auto" and torch.cuda.is_available()) else "cpu")
    model.to(device)
    model.eval()
    args.output_bed.parent.mkdir(parents=True, exist_ok=True)
    expected_windows = expected_window_count(lengths)
    observed_windows = observed_bp = 0
    seen: set[str] = set()
    audits: dict[str, dict] = {}
    with args.output_bed.open("w", encoding="utf-8") as bed:
        bed.write("# LEMMI-TE FM inference-only prediction; truth labels were not read\n")
        for name, sequence in iter_fasta(args.assembly):
            if name in seen:
                raise ValueError(f"duplicate FASTA contig: {name}")
            seen.add(name)
            if name not in lengths:
                raise ValueError(f"FASTA contig missing from frozen lengths: {name}")
            if len(sequence) != lengths[name]:
                raise ValueError(f"length mismatch for {name}: FASTA={len(sequence)} JSON={lengths[name]}")
            specs = window_specs(len(sequence), args.window, args.stride)
            audits[name] = coverage_audit(len(sequence), specs)
            contig_prob: list[float] = []
            for start, end in specs:
                real_length = end - start
                piece = sequence[start:end]
                padded = piece + ("N" * (args.window - real_length))
                values = _infer_window(model, tokenizer, padded, real_length, device, torch)
                contig_prob.extend(values.tolist())
                observed_windows += 1
            if len(contig_prob) != len(sequence):
                raise ValueError(f"prediction coverage mismatch for {name}")
            for start, end in threshold_runs(contig_prob, args.threshold):
                bed.write(f"{name}\t{start}\t{end}\t{args.model_name}\t0\t.\n")
            observed_bp += len(sequence)
    missing = sorted(set(lengths) - seen)
    if missing:
        raise ValueError(f"frozen lengths contain FASTA-missing contigs: {missing[:5]}")
    if observed_windows != expected_windows or observed_bp != sum(lengths.values()):
        raise ValueError("global prediction coverage audit failed")
    manifest = {"status": "PASS", "model_name": args.model_name, "model_dir": str(args.model_dir),
                "assembly": str(args.assembly), "lengths": str(args.lengths), "window": args.window,
                "stride": args.stride, "threshold": args.threshold, "device": str(device),
                "contigs": len(seen), "total_bp": observed_bp, "windows": observed_windows,
                "expected_windows": expected_windows, "missing_bp": 0, "overlap_bp": 0,
                "coverage_complete": True, "contig_audits": audits}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--lengths", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output-bed", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument("--stride", type=int, default=STRIDE)
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
