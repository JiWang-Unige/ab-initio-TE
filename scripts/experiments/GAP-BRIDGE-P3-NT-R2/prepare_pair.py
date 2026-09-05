#!/usr/bin/env python3
"""Label-blind native-grid NT/P3 pairing smoke; no head training or evaluation."""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
NT_WINDOW = 4096
FIELDS = ("crop_crosses_4096_seam", "log1p_nearest_nt_seam_distance",
          "direction_from_nt_seam_to_gap_midpoint")
SCOPES = {"chr3": "TRAIN", "chr5": "TRAIN", "chr13": "DEV"}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage1 = load_module(ROOT / "scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_train.py",
                     "r2_stage1_train")


@dataclass(frozen=True)
class Geometry:
    candidate_id: str
    seqid: str
    role: str
    gap_start: int
    gap_end: int
    left_run_length: int
    right_run_length: int
    span_length: int

    @property
    def gap_length(self):
        return self.gap_end - self.gap_start

    @property
    def crop_start(self):
        return self.gap_start - 256

    @property
    def crop_end(self):
        return self.gap_end + 256


def read_geometry(path, known_train_only=False):
    """Project geometry only; labels/known/family/support never become inputs."""
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            seqid, role = row["seqid"], row["role"]
            if SCOPES.get(seqid) != role:
                continue
            # Used ONLY by the separate stats fitting command, never inference.
            if known_train_only and (role != "TRAIN" or row["comparator_known"] != "1"):
                continue
            yield Geometry(row["candidate_id"], seqid, role,
                           int(row["gap_start"]), int(row["gap_end"]),
                           int(row["left_run_end"]) - int(row["left_run_start"]),
                           int(row["right_run_end"]) - int(row["right_run_start"]),
                           int(row["right_run_end"]) - int(row["left_run_start"]))


def nt_scalars(candidate):
    center = (candidate.gap_start + candidate.gap_end) / 2
    lower = math.floor(center / NT_WINDOW) * NT_WINDOW
    seam = lower if center - lower <= NT_WINDOW / 2 else lower + NT_WINDOW
    return np.asarray([
        float(candidate.crop_start // NT_WINDOW != (candidate.crop_end - 1) // NT_WINDOW),
        math.log1p(abs(center - seam)), float(np.sign(center - seam)),
    ], dtype=np.float32)


def fit_nt_stats(candidates):
    rows = [nt_scalars(c) for c in candidates if c.role == "TRAIN" and c.seqid in ("chr3", "chr5")]
    if not rows:
        raise ValueError("no TRAIN geometry for NT scalar statistics")
    values = np.asarray(rows, dtype=np.float64)
    scale = values.std(axis=0)
    # A bounded smoke or a real constant stratum can have constant geometry.
    # Centering makes that slot zero; unit scale preserves that meaning.
    scale[scale == 0] = 1
    return {"schema": "gap_bridge_r2_nt_scalar_stats_v1", "fields": list(FIELDS),
            "count": len(rows), "mean": values.mean(axis=0).tolist(), "scale": scale.tolist(),
            "fit_population": "existing comparator_known=1 TRAIN eligibility on chr3+chr5",
            "eligibility_field": "comparator_known; not a model feature", "targets_read": False,
            "nearest_seam_tie": "left", "origin": 0, "stride": 4096}


def pair_inputs(base_channels, base_geometry, nt_probability, candidate, stats):
    length = candidate.crop_end - candidate.crop_start
    probability = np.asarray(nt_probability, dtype=np.float64)
    if base_channels.shape != (143, 1024) or np.shape(base_geometry) != (7,) or probability.shape != (length,):
        raise ValueError("paired input coordinate/shape mismatch")
    if not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1)):
        raise ValueError("NT output is not a finite probability track")
    h0 = np.zeros((144, 1024), dtype=np.float32)
    h0[:143] = base_channels
    hn = h0.copy()
    p = np.clip(probability, 1 / (1 + np.exp(12)), 1 / (1 + np.exp(-12)))
    hn[143, :length] = np.clip(np.log(p) - np.log1p(-p), -12, 12)
    g0 = np.zeros(10, dtype=np.float32)
    g0[:7] = base_geometry
    gn = g0.copy()
    gn[7:] = (nt_scalars(candidate) - np.asarray(stats["mean"])) / np.asarray(stats["scale"])
    if not all(np.isfinite(a).all() for a in (h0, hn, g0, gn)):
        raise ValueError("non-finite paired input")
    return h0, hn, g0, gn


def sequence_record(row, seqid):
    """No access to row['labels']; preserving unknown bases and every coordinate."""
    if row["chr"] != seqid:
        raise ValueError("region chromosome differs from requested scope")
    start, end, sequence = int(row["start"]), int(row["end"]), row["sequence"].upper()
    if start % 8192 or not 0 < end - start <= 8192 or len(sequence) != end - start:
        raise ValueError("region is not original zero-aligned P3 geometry")
    return start, end, sequence


def selected_regions(path, seqid, starts):
    opener = gzip.open if str(path).endswith(".gz") else open
    remaining = set(starts)
    with opener(path, "rt") as handle:
        for raw in handle:
            row = json.loads(raw)
            if int(row["start"]) not in remaining:
                continue
            record = sequence_record(row, seqid)
            remaining.remove(record[0])
            yield record
            if not remaining:
                return
    raise ValueError(f"missing requested P3 windows: {sorted(remaining)}")


class TokenizationTrace:
    """Observe the actual strict-adapter branch without changing tokenization."""

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.offsets = None
        self.tokens = None

    def __call__(self, *args, **kwargs):
        encoded = self.tokenizer(*args, **kwargs)
        self.offsets = encoded.get("offset_mapping")
        self.tokens = None
        self.max_length = kwargs["max_length"]
        return encoded

    def tokenize(self, sequence):
        self.tokens = self.tokenizer.tokenize(sequence)
        return self.tokens


def native_nt_window(strict, model, tokenizer, sequence, device, label_mode):
    """Native strict forward plus coverage of tokens actually returned by that forward."""
    if label_mode not in {"nt_kmer", "offset_or_kmer"}:
        raise ValueError(f"NTv2 kmer coverage is not defined for label mode {label_mode!r}")
    trace = TokenizationTrace(tokenizer)
    output_tokens = None

    def tracked_model(**inputs):
        nonlocal output_tokens
        output = model(**inputs)
        output_tokens = int(output.logits.shape[1])
        return output

    probability = strict.infer_probs_for_label_mode(
        tracked_model, trace, sequence, NT_WINDOW, device, label_mode)
    probability = np.asarray(probability, dtype=np.float32)
    if probability.shape != (NT_WINDOW,):
        raise ValueError("strict NT output did not preserve 4096 positions")
    coverage = np.zeros(NT_WINDOW, dtype=bool)
    # strict's broad exception handler can switch to its fallback after an
    # offset call. Trace the LAST actual branch, not a second tokenizer call.
    if trace.tokens is not None:
        position = 0
        for index, token in enumerate(trace.tokens, start=1):
            if index >= min(trace.max_length - 1, output_tokens):
                break
            end = min(NT_WINDOW, position + max(1, len(token.replace(" ", ""))))
            coverage[position:end] = True
            position = end
            if position >= NT_WINDOW:
                break
    else:
        offsets = trace.offsets[0].detach().cpu().numpy()
        for start, end in offsets[:output_tokens]:
            start, end = int(start), int(end)
            if start < end:
                coverage[max(0, min(NT_WINDOW, start)):max(0, min(NT_WINDOW, end))] = True
    return probability[:len(sequence)], coverage[:len(sequence)]


def crop_track(track, candidate):
    first = candidate.crop_start // 8192 * 8192
    last = (candidate.crop_end - 1) // 8192 * 8192
    values = np.concatenate([track[start] for start in range(first, last + 1, 8192)])
    return values[candidate.crop_start - first:candidate.crop_end - first]


def require_crop_coverage(coverage, candidate):
    if coverage.shape != (candidate.crop_end - candidate.crop_start,):
        raise ValueError(f"NT coverage coordinate length mismatch: {candidate.candidate_id}")
    missing = np.flatnonzero(~coverage)
    if missing.size:
        raise ValueError(
            f"NT_TOKEN_COVERAGE_FAILED {candidate.candidate_id}: {missing.size} crop bp have no "
            f"inferred token; first={candidate.seqid}:{candidate.crop_start + int(missing[0])}, "
            f"last={candidate.seqid}:{candidate.crop_start + int(missing[-1])}; "
            "do not treat strict adapter's unfilled zero probabilities as NT evidence")


def run(args):
    import torch

    started = time.perf_counter()
    all_geometry = list(read_geometry(args.candidate_manifest))
    candidates = sorted((c for c in all_geometry if c.seqid == args.seqid),
                        key=lambda c: (c.gap_start, c.candidate_id))[:args.max_candidates]
    if not candidates:
        raise ValueError("no candidates in requested TRAIN/DEV scope")
    stats = json.loads(args.nt_scalar_stats.read_text())
    if stats["fields"] != list(FIELDS) or np.shape(stats["mean"]) != (3,) or np.shape(stats["scale"]) != (3,):
        raise ValueError("NT statistics are not the registered three seam scalars")
    base_stats = json.loads(args.p3_scalar_stats.read_text())
    starts = {start for c in candidates for start in range(
        c.crop_start // 8192 * 8192, (c.crop_end - 1) // 8192 * 8192 + 1, 8192)}
    regions = list(selected_regions(args.region, args.seqid, starts))
    # Strict evaluator imports its established loaders relative to project cwd.
    for directory in ("PIPE-TEFM-SEG-SF-20260618", "PIPE-TEFM-SUPP-20260617"):
        sys.path.insert(0, str(ROOT / "pipelines" / directory))
    strict = load_module(ROOT / "pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py", "r2_strict")
    device = torch.device(args.device)
    load_start = time.perf_counter()
    model, tokenizer, metadata = strict.load_trained_model(str(args.nt_model))
    model.to(device).eval()
    model.requires_grad_(False)
    label_mode = str(metadata.get("token_label_mode", ""))
    nt_load_seconds = time.perf_counter() - load_start
    nt, nt_coverage = {}, {}
    nt_window_coverage = []
    infer_start = time.perf_counter()
    window_count = 0
    for start, end, sequence in regions:
        halves, covered_halves = [], []
        for offset in range(0, len(sequence), NT_WINDOW):
            probabilities, covered = native_nt_window(strict, model, tokenizer,
                sequence[offset:offset + NT_WINDOW], device, label_mode)
            halves.append(probabilities)
            covered_halves.append(covered)
            nt_window_coverage.append({"start": start + offset, "end": start + offset + len(covered),
                                       "covered_bp": int(covered.sum()), "uncovered_bp": int((~covered).sum())})
            window_count += 1
        nt[start] = np.concatenate(halves)
        nt_coverage[start] = np.concatenate(covered_halves)
    nt_seconds = time.perf_counter() - infer_start
    for candidate in candidates:
        require_crop_coverage(crop_track(nt_coverage, candidate), candidate)
    model.to("cpu")
    del model, tokenizer
    if device.type == "cuda":
        torch.cuda.empty_cache()
    load_start = time.perf_counter()
    model, tokenizer, metadata_p3, p3_device, _ = stage1.load_c5().load_p3_model(args.p3_model)
    model.to(device).eval().requires_grad_(False)
    p3_device = device
    p3_load_seconds = time.perf_counter() - load_start
    p3 = {}
    infer_start = time.perf_counter()
    for start, end, sequence in regions:
        p3[start] = stage1._p3_forward_window(model, tokenizer, p3_device, start, end, sequence)
    p3_seconds = time.perf_counter() - infer_start
    rows = []
    for candidate in candidates:
        first = candidate.crop_start // 8192 * 8192
        last = (candidate.crop_end - 1) // 8192 * 8192
        sequence, logits, latent = stage1.assemble_crop(p3.get(last - 8192), p3[last],
                                                       candidate.crop_start, candidate.crop_end)
        probability = crop_track(nt, candidate)
        base = stage1.build_channels(sequence, logits, latent, candidate)
        geometry = stage1.standardized_scalars(candidate, base_stats)
        h0, hn, g0, gn = pair_inputs(base, geometry, probability, candidate, stats)
        rows.append({"candidate_id": candidate.candidate_id, "seqid": candidate.seqid, "role": candidate.role,
                     "crop_start": candidate.crop_start, "crop_end": candidate.crop_end,
                     "coordinate_length": len(sequence), "nt_length": len(probability),
                     "nt_crop_token_coverage_complete": True,
                     "finite": True, "base_channels_equal": bool(np.array_equal(h0[:143], hn[:143])),
                     "base_geometry_equal": bool(np.array_equal(g0[:7], gn[:7])),
                     "h0_extra_slots_zero": bool(not h0[143].any() and not g0[7:].any()),
                     "nt_logit_min": float(hn[143, :len(sequence)].min()),
                     "nt_logit_max": float(hn[143, :len(sequence)].max()),
                     "nt_scalars_raw": nt_scalars(candidate).tolist()})
    summary = {"status": "PASS", "scope": "label-blind alignment smoke; claim-ineligible; no training/evaluation",
               "inference_labels_read": False,
               "label_blind_definition": "input files may contain labels; no label fields accessed or interpreted",
               "comparator_features_used": False, "cal_gate_or_chr19_evaluated": False,
               "seqid": args.seqid, "role": SCOPES[args.seqid], "p3_window": 8192,
               "nt_window": 4096, "nt_origin": 0, "nt_stride": 4096,
               "terminal_handling": "native strict tokenizer padding; output trimmed to sequence length",
               "inputs": {"candidate_manifest": str(args.candidate_manifest), "region": str(args.region),
                          "nt_model": str(args.nt_model), "p3_model": str(args.p3_model),
                          "p3_scalar_stats": str(args.p3_scalar_stats), "nt_scalar_stats": str(args.nt_scalar_stats)},
               "nt_stats_fit_count": stats["count"], "device": str(device),
               "nt_label_mode": label_mode, "channels": 144, "scalars": 10,
               "p3_windows": len(regions), "nt_windows": window_count,
               "nt_window_token_coverage": nt_window_coverage,
               "runtime_seconds": {"nt_load": nt_load_seconds, "nt_inference": nt_seconds,
                                   "p3_load": p3_load_seconds, "p3_inference": p3_seconds,
                                   "total": time.perf_counter() - started}, "candidates": rows}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "alignment_smoke.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fit = commands.add_parser("fit-stats", help="fit NT geometry on existing known TRAIN eligibility")
    fit.add_argument("--candidate-manifest", type=Path, required=True)
    fit.add_argument("--output", type=Path, required=True)
    smoke = commands.add_parser("smoke", help="label-blind paired inference using pre-fitted statistics")
    smoke.add_argument("--candidate-manifest", type=Path, required=True)
    smoke.add_argument("--p3-scalar-stats", type=Path, required=True)
    smoke.add_argument("--nt-scalar-stats", type=Path, required=True)
    smoke.add_argument("--region", type=Path, required=True)
    smoke.add_argument("--seqid", choices=tuple(SCOPES), required=True)
    smoke.add_argument("--nt-model", type=Path, required=True)
    smoke.add_argument("--p3-model", type=Path, required=True)
    smoke.add_argument("--max-candidates", type=int, default=8)
    smoke.add_argument("--device", default="cuda")
    smoke.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "fit-stats":
        stats = fit_nt_stats(read_geometry(args.candidate_manifest, known_train_only=True))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as handle:
            handle.write(json.dumps(stats, indent=2) + "\n")
        print(json.dumps(stats, indent=2))
        return
    if args.max_candidates < 1:
        parser.error("--max-candidates must be positive")
    run(args)


if __name__ == "__main__":
    main()
