#!/usr/bin/env python3
"""Bounded postprocess diagnostics for TE fragmentation.

This is not a new architecture claim. It sweeps probability thresholds and
length-adaptive postprocess variants on the same small human/mouse panel used
by the fragmentation capability screens. The goal is to expose tradeoffs:
fragmentation reduction, boundary quality, missed true TE, and deletion of
true-backed raw fragments.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import sys
from pathlib import Path
from typing import Callable

os.environ.setdefault("TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD", "1")
os.environ.setdefault("WANDB_DISABLED", "true")

import numpy as np
import torch
from torch.utils.data import DataLoader

SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
FINAL = Path("pipelines/PIPE-TEFM-FINAL-20260623").resolve()
ROUND1 = Path("pipelines/PIPE-TEFM-CAP-FRAGARCH-20260701").resolve()
sys.path.insert(0, str(SUPP))
sys.path.insert(0, str(FINAL))
sys.path.insert(0, str(ROUND1))

from te_token_task import WindowDataset, load_tokenizer, load_trained_model  # noqa: E402
from strict_segment_eval import (  # noqa: E402
    binary_metrics,
    fragmentation_truth_diagnostics,
    runs_from_bool,
    strict_segment_metrics,
    viterbi_smooth,
)
from train_interval_architectures import deleted_fragment_diagnostics, overmerge_rate, write_tsv  # noqa: E402


def valid_arrays(labels: torch.Tensor, prob: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
    keep = labels.detach().cpu().numpy() >= 0
    return labels.detach().cpu().numpy()[keep], prob.detach().cpu().numpy()[keep]


def merge_small_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    out = mask.astype(bool).copy()
    segs = runs_from_bool(out)
    for (_, e1), (s2, _) in zip(segs, segs[1:]):
        if 0 < s2 - e1 <= max_gap:
            out[e1:s2] = True
    return out


def min_length_filter(mask: np.ndarray, min_len: int) -> np.ndarray:
    out = mask.astype(bool).copy()
    for s, e in runs_from_bool(out):
        if e - s < min_len:
            out[s:e] = False
    return out


def length_adaptive(raw: np.ndarray, smooth: np.ndarray, short_cutoff: int) -> np.ndarray:
    """Keep short raw islands, use smoothed calls for longer intervals."""
    out = np.zeros_like(raw, dtype=bool)
    for s, e in runs_from_bool(raw):
        if e - s < short_cutoff:
            out[s:e] = True
    for s, e in runs_from_bool(smooth):
        if e - s >= short_cutoff:
            out[s:e] = True
    return out


def high_confidence_rescue(base: np.ndarray, prob: np.ndarray, rescue_threshold: float, max_len: int) -> np.ndarray:
    """Add high-confidence short fragments back to a smoothed baseline."""
    out = base.astype(bool).copy()
    rescue = prob >= rescue_threshold
    for s, e in runs_from_bool(rescue):
        if e - s <= max_len:
            out[s:e] = True
    return out


def true_length_bin_rows(panel: str, variant: str, truth: np.ndarray, pred: np.ndarray) -> list[dict]:
    bins = [
        ("lt80", 0, 80),
        ("80_300", 80, 300),
        ("300_1000", 300, 1000),
        ("ge1000", 1000, 10**12),
    ]
    rows: list[dict] = []
    pred_seg = runs_from_bool(pred.astype(bool))
    for bin_name, lo, hi in bins:
        true_seg = [(s, e) for s, e in runs_from_bool((truth == 1).astype(bool)) if lo <= e - s < hi]
        counts = []
        for ts, te in true_seg:
            c = 0
            for ps, pe in pred_seg:
                if pe <= ts:
                    continue
                if ps >= te:
                    break
                if min(pe, te) > max(ps, ts):
                    c += 1
            counts.append(c)
        rows.append({
            "panel": panel,
            "variant": variant,
            "true_len_bin": bin_name,
            "true_segments_bin": len(true_seg),
            "missed_true_rate_bin": sum(1 for x in counts if x == 0) / len(counts) if counts else 0.0,
            "split_true_rate_bin": sum(1 for x in counts if x > 1) / len(counts) if counts else 0.0,
            "mean_fragments_per_true_bin": float(np.mean(counts)) if counts else 0.0,
        })
    return rows


def eval_rows(
    panel: str,
    variant: str,
    truth: np.ndarray,
    pred: np.ndarray,
    raw_baseline: np.ndarray,
    iou_thresholds: list[float],
    boundary_tols: list[int],
    meta: dict,
) -> list[dict]:
    known = truth >= 0
    y = truth == 1
    p = pred.astype(bool)
    base = {"panel": panel, "variant": variant}
    base.update(meta)
    base.update(binary_metrics(y[known], p[known].astype(np.float32), 0.5))
    base.update(fragmentation_truth_diagnostics(y, p))
    base.update(deleted_fragment_diagnostics(y, raw_baseline, p))
    base["overmerge_rate"] = overmerge_rate(y, p)
    rows = []
    for iou in iou_thresholds:
        for tol in boundary_tols:
            row = dict(base)
            row.update({"iou_threshold": iou, "boundary_tol_bp": tol})
            row.update(strict_segment_metrics(y, p, iou, tol))
            rows.append(row)
    return rows


def infer_panel(args, model, tokenizer, meta: dict, panel_path: Path, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    ds = WindowDataset(str(panel_path), tokenizer, args.window, meta["token_label_mode"], args.max_eval_samples)
    loader = DataLoader(ds, batch_size=1, shuffle=False)
    truths = []
    probs = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            labels = batch["labels"][0]
            logits = model(input_ids=batch["input_ids"], attention_mask=batch.get("attention_mask")).logits[0]
            y, prob = valid_arrays(labels, torch.softmax(logits, dim=-1)[:, 1])
            truths.append(y.astype(np.int8))
            probs.append(prob.astype(np.float32))
    return np.concatenate(truths), np.concatenate(probs)


def build_variants(prob: np.ndarray, args) -> list[tuple[str, np.ndarray, dict]]:
    variants: list[tuple[str, np.ndarray, dict]] = []
    for t in args.thresholds:
        raw = prob >= t
        variants.append((f"raw_t{t:.2f}", raw, {"threshold": t, "postprocess_family": "raw"}))
        for gap, min_len in [(25, 40), (50, 80), (100, 100)]:
            name = f"gap{gap}_min{min_len}_t{t:.2f}"
            mask = min_length_filter(merge_small_gaps(raw, gap), min_len)
            variants.append((name, mask, {"threshold": t, "postprocess_family": "gap_minlen", "gap": gap, "min_len": min_len}))
    for penalty in args.hmm_penalties:
        smooth = viterbi_smooth(prob, penalty).astype(bool)
        variants.append((f"hmm_p{penalty:g}", smooth, {"postprocess_family": "hmm", "hmm_penalty": penalty}))
        for rescue_t in args.rescue_thresholds:
            for max_len in args.rescue_max_lens:
                name = f"hmm_p{penalty:g}_rescue_t{rescue_t:.2f}_max{max_len}"
                mask = high_confidence_rescue(smooth, prob, rescue_t, max_len)
                variants.append((name, mask, {
                    "postprocess_family": "hmm_rescue_short",
                    "hmm_penalty": penalty,
                    "rescue_threshold": rescue_t,
                    "rescue_max_len": max_len,
                }))
        for raw_t in args.thresholds:
            raw = prob >= raw_t
            for cutoff in args.short_cutoffs:
                name = f"lenadaptive_raw{raw_t:.2f}_hmm{penalty:g}_cut{cutoff}"
                mask = length_adaptive(raw, smooth, cutoff)
                variants.append((name, mask, {
                    "postprocess_family": "length_adaptive",
                    "threshold": raw_t,
                    "hmm_penalty": penalty,
                    "short_cutoff": cutoff,
                }))
    return variants


def summarize(rows: list[dict], args) -> dict:
    focal = [
        r for r in rows
        if float(r.get("iou_threshold", -1)) == args.primary_iou
        and int(r.get("boundary_tol_bp", -1)) == args.primary_boundary
    ]
    by_panel: dict[str, dict[str, dict]] = {}
    for r in focal:
        by_panel.setdefault(str(r["panel"]), {})[str(r["variant"])] = r
    panel_summaries = {}
    for panel, variants in by_panel.items():
        baseline = variants.get("raw_t0.50") or next((v for k, v in variants.items() if k.startswith("raw_t")), None)
        best_segment = max(variants.values(), key=lambda r: float(r["segment_f1"]))
        best_boundary = max(variants.values(), key=lambda r: float(r["boundary_f1"]))
        safe = []
        if baseline is not None:
            for r in variants.values():
                if (
                    float(r["missed_true_rate"]) <= float(baseline["missed_true_rate"]) + args.max_missed_delta
                    and float(r["deleted_true_backed_fraction"]) <= args.max_deleted_true_backed_fraction
                    and float(r["pred_true_backed_rate"]) >= args.min_pred_true_backed_rate
                ):
                    safe.append(r)
        best_safe = max(safe, key=lambda r: (float(r["segment_f1"]), float(r["boundary_f1"]))) if safe else None
        panel_summaries[panel] = {
            "baseline_raw_t0.50": baseline,
            "best_segment": best_segment,
            "best_boundary": best_boundary,
            "best_guardrail_safe": best_safe,
            "n_guardrail_safe": len(safe),
        }
    return {
        "ok": True,
        "profile": "bounded diagnostic only; not capability promotion",
        "primary_iou": args.primary_iou,
        "primary_boundary": args.primary_boundary,
        "panels": panel_summaries,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-id", default="PIPE-TEFM-CAP-POSTPROC-20260701")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--eval-panel", action="append", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-eval-samples", type=int, default=40)
    ap.add_argument("--thresholds", type=float, nargs="+", default=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    ap.add_argument("--hmm-penalties", type=float, nargs="+", default=[1.0, 2.0, 4.0])
    ap.add_argument("--short-cutoffs", type=int, nargs="+", default=[80, 150, 300])
    ap.add_argument("--rescue-thresholds", type=float, nargs="+", default=[0.5, 0.6, 0.7])
    ap.add_argument("--rescue-max-lens", type=int, nargs="+", default=[80, 150, 300])
    ap.add_argument("--iou-thresholds", type=float, nargs="+", default=[0.5, 0.7, 0.8, 0.9])
    ap.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5, 10, 25])
    ap.add_argument("--primary-iou", type=float, default=0.8)
    ap.add_argument("--primary-boundary", type=int, default=5)
    ap.add_argument("--max-missed-delta", type=float, default=0.03)
    ap.add_argument("--max-deleted-true-backed-fraction", type=float, default=0.15)
    ap.add_argument("--min-pred-true-backed-rate", type=float, default=0.5)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")

    model, tokenizer, meta = load_trained_model(args.model_dir)
    model.to(device)
    model.eval()
    best = Path(args.model_dir) / "best_model"
    if (best / "tokenizer_config.json").exists():
        tokenizer = load_tokenizer(str(best))

    all_rows: list[dict] = []
    bin_rows: list[dict] = []
    for spec in args.eval_panel:
        panel, path_str = spec.split(":", 1)
        truth, prob = infer_panel(args, model, tokenizer, meta, Path(path_str), device)
        raw_baseline = prob >= 0.5
        for name, pred, vmeta in build_variants(prob, args):
            meta_row = {
                "exp_id": args.exp_id,
                "seed": args.seed,
                "window": args.window,
                "max_eval_samples": args.max_eval_samples,
                "n_bp": int(truth.size),
                "token_label_mode": meta["token_label_mode"],
            }
            meta_row.update(vmeta)
            all_rows.extend(eval_rows(panel, name, truth, pred, raw_baseline, args.iou_thresholds, args.boundary_tolerances, meta_row))
            bin_rows.extend(true_length_bin_rows(panel, name, truth, pred))

    metrics_tsv = out_dir / "postprocess_threshold_metrics.tsv"
    length_tsv = out_dir / "postprocess_true_length_bins.tsv"
    write_tsv(metrics_tsv, all_rows)
    write_tsv(length_tsv, bin_rows)
    status = summarize(all_rows, args)
    status.update({
        "exp_id": args.exp_id,
        "seed": args.seed,
        "device": str(device),
        "metrics_tsv": str(metrics_tsv),
        "true_length_bins_tsv": str(length_tsv),
        "non_goal": "Diagnostic postprocess sweep only; does not reopen DEC-001/DEC-002 architecture routes or claim fragmentation solved.",
    })
    (out_dir / "postprocess_threshold_status.json").write_text(json.dumps(status, indent=2) + "\n")
    report = [
        "# Threshold and Length-Adaptive Postprocess Diagnostic",
        "",
        f"- Exp ID: `{args.exp_id}`",
        f"- Seed: `{args.seed}`",
        f"- Metrics: `{metrics_tsv}`",
        f"- True-length bins: `{length_tsv}`",
        "",
        "This bounded screen answers whether the previous fixed threshold looked too harsh and whether short-fragment rescue plus long-region smoothing can improve the fragmentation tradeoff. It is not a new architecture or SOTA claim.",
    ]
    (out_dir / "POSTPROCESS_THRESHOLD_REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
