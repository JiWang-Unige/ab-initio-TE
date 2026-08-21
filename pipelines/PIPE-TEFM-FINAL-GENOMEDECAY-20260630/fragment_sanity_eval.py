#!/usr/bin/env python3
"""Fragmentation sanity experiments for forward/RC inference and oracle merging.

This is a bounded, screen-grade evaluator. It reuses the trained bp classifier,
reconstructs per-bp probability tracks, compares forward and reverse-complement
inference merges, and estimates an oracle same-true-interval repair upper bound.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

FINAL = Path("pipelines/PIPE-TEFM-FINAL-20260623").resolve()
sys.path.insert(0, str(FINAL))

from strict_segment_eval import (  # noqa: E402
    binary_metrics,
    center_weights,
    fragmentation_truth_diagnostics,
    infer_probs_for_label_mode,
    load_trained_model,
    runs_from_bool,
    strict_segment_metrics,
    viterbi_smooth,
)


TRANS = str.maketrans("ACGTNacgtn", "TGCANtgcan")


def reverse_complement(seq: str) -> str:
    return seq.translate(TRANS)[::-1]


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p.astype(np.float32), 1e-5, 1.0 - 1e-5)
    return np.log(p / (1.0 - p))


def sigmoid(x: np.ndarray) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-x))).astype(np.float32)


def read_jsonl(path: Path, max_records: int | None = None):
    with gzip.open(path, "rt") as handle:
        for i, line in enumerate(handle):
            if max_records is not None and i >= max_records:
                break
            yield json.loads(line)


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def oracle_fill_supported_true_intervals(truth: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Upper bound: if a true interval has any prediction, fill that true interval.

    This is intentionally truth-aware and cannot be deployed. It estimates whether
    a future interval refiner could repair internal valleys if it had perfect
    interval-continuity decisions.
    """
    out = np.zeros_like(mask, dtype=bool)
    pred_seg = runs_from_bool(mask.astype(bool))
    pred_idx = 0
    for ts, te in runs_from_bool(truth.astype(bool)):
        while pred_idx < len(pred_seg) and pred_seg[pred_idx][1] <= ts:
            pred_idx += 1
        pi = pred_idx
        supported = False
        while pi < len(pred_seg):
            ps, pe = pred_seg[pi]
            if ps >= te:
                break
            if min(pe, te) > max(ps, ts):
                supported = True
                break
            pi += 1
        if supported:
            out[ts:te] = True
    return out


def oracle_connect_fragments_within_true(truth: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Less permissive upper bound: connect predicted pieces inside each true TE."""
    out = mask.copy().astype(bool)
    pred_seg = runs_from_bool(mask.astype(bool))
    pred_idx = 0
    for ts, te in runs_from_bool(truth.astype(bool)):
        while pred_idx < len(pred_seg) and pred_seg[pred_idx][1] <= ts:
            pred_idx += 1
        overlaps: list[tuple[int, int]] = []
        pi = pred_idx
        while pi < len(pred_seg):
            ps, pe = pred_seg[pi]
            if ps >= te:
                break
            if min(pe, te) > max(ps, ts):
                overlaps.append((max(ps, ts), min(pe, te)))
            pi += 1
        if overlaps:
            out[overlaps[0][0] : overlaps[-1][1]] = True
    return out


def mask_deleted_backing_metrics(truth: np.ndarray, before: np.ndarray, after: np.ndarray) -> dict:
    deleted = before.astype(bool) & ~after.astype(bool)
    deleted_segments = runs_from_bool(deleted)
    true_seg = runs_from_bool(truth.astype(bool))
    true_backed = 0
    for ds, de in deleted_segments:
        for ts, te in true_seg:
            if te <= ds:
                continue
            if ts >= de:
                break
            if min(de, te) > max(ds, ts):
                true_backed += 1
                break
    return {
        "deleted_segments": len(deleted_segments),
        "deleted_true_backed_segments": true_backed,
        "deleted_true_backed_rate": true_backed / len(deleted_segments) if deleted_segments else 0.0,
    }


def build_tracks(args) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, np.ndarray], int]:
    model, tokenizer, meta = load_trained_model(args.model_dir)
    label_mode = str(meta.get("token_label_mode", ""))
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model.to(device)
    model.eval()
    weights = center_weights(args.window, args.weight_mode)
    merge_modes = ["forward", "reverse", "mean_logit", "max_prob", "consensus_min"]
    chrom_sum: dict[str, dict[str, np.ndarray]] = {}
    chrom_w: dict[str, np.ndarray] = {}
    chrom_truth: dict[str, np.ndarray] = {}
    n = 0
    for rec in read_jsonl(Path(args.data_jsonl), args.max_windows):
        n += 1
        chrom = rec["chr"]
        start = int(rec["start"])
        end = int(rec["end"])
        seq = rec["sequence"][: args.window]
        labels = np.asarray(rec["labels"][: args.window], dtype=np.int8)
        fwd = infer_probs_for_label_mode(model, tokenizer, seq, args.window, device, label_mode)
        rev_raw = infer_probs_for_label_mode(model, tokenizer, reverse_complement(seq), args.window, device, label_mode)
        rev = rev_raw[::-1].copy()
        probs = {
            "forward": fwd,
            "reverse": rev,
            "mean_logit": sigmoid((logit(fwd) + logit(rev)) / 2.0),
            "max_prob": np.maximum(fwd, rev).astype(np.float32),
            "consensus_min": np.minimum(fwd, rev).astype(np.float32),
        }
        if chrom not in chrom_sum or chrom_w[chrom].size < end:
            old_sum = chrom_sum.get(chrom)
            old_w = chrom_w.get(chrom)
            old_t = chrom_truth.get(chrom)
            chrom_sum[chrom] = {mode: np.zeros(end, dtype=np.float32) for mode in merge_modes}
            chrom_w[chrom] = np.zeros(end, dtype=np.float32)
            chrom_truth[chrom] = np.zeros(end, dtype=np.int8)
            if old_sum is not None:
                for mode in merge_modes:
                    chrom_sum[chrom][mode][: old_sum[mode].size] = old_sum[mode]
                chrom_w[chrom][: old_w.size] = old_w
                chrom_truth[chrom][: old_t.size] = old_t
        for mode in merge_modes:
            chrom_sum[chrom][mode][start:end] += probs[mode] * weights
        chrom_w[chrom][start:end] += weights
        chrom_truth[chrom][start:end] = labels
        if n % 50 == 0:
            print(f"predicted {n} windows", flush=True)
    chrom_prob: dict[str, dict[str, np.ndarray]] = {}
    for chrom in chrom_sum:
        valid = chrom_w[chrom] > 0
        chrom_prob[chrom] = {}
        for mode in merge_modes:
            prob = np.zeros_like(chrom_sum[chrom][mode])
            prob[valid] = chrom_sum[chrom][mode][valid] / chrom_w[chrom][valid]
            chrom_prob[chrom][mode] = prob[valid]
        chrom_truth[chrom] = chrom_truth[chrom][valid]
    return chrom_prob, chrom_truth, n


def add_eval_rows(rows: list[dict], base: dict, truth: np.ndarray, prob: np.ndarray, merge_mode: str, postprocess: str, mask: np.ndarray) -> None:
    known = truth >= 0
    truth_binary = truth == 1
    eval_mask = mask.astype(bool).copy()
    eval_mask[~known] = False
    for iou in base["iou_thresholds"]:
        for tol in base["boundary_tolerances"]:
            row = {k: v for k, v in base.items() if k not in {"iou_thresholds", "boundary_tolerances"}}
            row.update({
                "merge_mode": merge_mode,
                "postprocess": postprocess,
                "iou_threshold": iou,
                "boundary_tol_bp": tol,
                "ignored_bp": int((~known).sum()),
            })
            row.update(binary_metrics(truth_binary[known], eval_mask[known].astype(np.float32), 0.5))
            row.update(strict_segment_metrics(truth_binary, eval_mask, iou, tol))
            row.update(fragmentation_truth_diagnostics(truth_binary, eval_mask))
            raw_mask = prob >= float(base["threshold"])
            row.update(mask_deleted_backing_metrics(truth_binary, raw_mask, eval_mask))
            rows.append(row)


def run(args) -> None:
    chrom_prob, chrom_truth, n_windows = build_tracks(args)
    rows: list[dict] = []
    for chrom in sorted(chrom_prob):
        truth = chrom_truth[chrom]
        for merge_mode, prob in chrom_prob[chrom].items():
            raw = prob >= args.threshold
            variants = {
                "raw_threshold": raw,
                "crf_style_penalty4": viterbi_smooth(prob, 4.0),
                "oracle_connect_same_true": oracle_connect_fragments_within_true(truth == 1, raw),
                "oracle_fill_supported_true": oracle_fill_supported_true_intervals(truth == 1, raw),
            }
            for postprocess, mask in variants.items():
                base = {
                    "exp_id": args.exp_id,
                    "model_dir": args.model_dir,
                    "data_jsonl": args.data_jsonl,
                    "chrom": chrom,
                    "window": args.window,
                    "stride": args.stride,
                    "weight_mode": args.weight_mode,
                    "threshold": args.threshold,
                    "n_windows": n_windows,
                    "iou_thresholds": args.iou_thresholds,
                    "boundary_tolerances": args.boundary_tolerances,
                }
                add_eval_rows(rows, base, truth, prob, merge_mode, postprocess, mask)
    write_tsv(Path(args.out_tsv), rows)
    status = {"ok": True, "rows": len(rows), "out_tsv": args.out_tsv, "n_windows": n_windows}
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-id", default="PIPE-TEFM-FINAL-FRAGSANITY-20260630")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--data-jsonl", required=True)
    ap.add_argument("--out-tsv", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--window", type=int, required=True)
    ap.add_argument("--stride", type=int, required=True)
    ap.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--iou-thresholds", type=float, nargs="+", default=[0.8, 0.9])
    ap.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5, 10, 25])
    ap.add_argument("--max-windows", type=int, default=300)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
