#!/usr/bin/env python3
"""GENERanno overlap inference plus bp/segment/fragmentation metrics.

The script consumes JSONL windows produced by the previous UCSC-window builder.
It predicts per-bp TE probabilities for each window, merges overlapping windows
with optional center weights, then evaluates both bp and interval usability.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

SCRIPT_DIR = Path(__file__).resolve().parent
SUPP_DIR = SCRIPT_DIR.parent / "PIPE-TEFM-SUPP-20260617"
sys.path.insert(0, str(SUPP_DIR))

from te_token_task import load_trained_model  # noqa: E402


BIN_DEFS = [
    ("edge_left_10", 0.00, 0.10),
    ("inner_left_10_25", 0.10, 0.25),
    ("center_25_75", 0.25, 0.75),
    ("inner_right_75_90", 0.75, 0.90),
    ("edge_right_10", 0.90, 1.01),
]


def read_jsonl(path: Path, max_records: int | None = None):
    with gzip.open(path, "rt") as handle:
        for i, line in enumerate(handle):
            if max_records is not None and i >= max_records:
                break
            yield json.loads(line)


def center_weights(n: int, mode: str) -> np.ndarray:
    if mode == "flat":
        return np.ones(n, dtype=np.float32)
    x = np.linspace(-1.0, 1.0, n, dtype=np.float32)
    if mode == "triangular":
        return np.maximum(0.05, 1.0 - np.abs(x)).astype(np.float32)
    if mode == "cosine":
        return (0.05 + 0.95 * (0.5 + 0.5 * np.cos(np.pi * x))).astype(np.float32)
    raise ValueError(f"unknown weight mode: {mode}")


def infer_probs(model, tokenizer, seq: str, window: int, device: torch.device) -> np.ndarray:
    tok_max = window + 2
    enc = tokenizer(seq[:window], truncation=True, max_length=tok_max, padding="max_length", return_tensors="pt")
    enc = {k: v.to(device) for k, v in enc.items() if k in {"input_ids", "attention_mask"}}
    with torch.no_grad():
        logits = model(**enc).logits[0]
    prob = torch.softmax(logits, dim=-1)[:, 1].detach().cpu().numpy()
    out = np.zeros(window, dtype=np.float32)
    n = min(window, max(0, prob.shape[0] - 2))
    out[:n] = prob[1:1 + n]
    return out


def runs_from_bool(arr: np.ndarray) -> list[tuple[int, int]]:
    out = []
    i = 0
    n = int(arr.size)
    while i < n:
        if arr[i]:
            j = i + 1
            while j < n and arr[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def binary_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_true = y_true.astype(np.int8)
    y_pred = (y_prob >= threshold).astype(np.int8)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "bp_tp": tp, "bp_fp": fp, "bp_fn": fn, "bp_tn": tn,
        "bp_precision": precision, "bp_recall": recall, "bp_f1": f1,
        "bp_positive_rate_true": float((y_true == 1).mean()) if y_true.size else 0.0,
        "bp_positive_rate_pred": float((y_pred == 1).mean()) if y_pred.size else 0.0,
        "bp_n": int(y_true.size),
    }


def segment_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5,
                    iou_threshold: float = 0.5, boundary_tol: int = 100) -> dict:
    true_seg = runs_from_bool(y_true.astype(bool))
    pred_seg = runs_from_bool(y_prob >= threshold)
    matched_t: set[int] = set()
    matched_p: set[int] = set()
    ious = []
    boundary_hits = 0
    boundary_errors = []
    for pi, (ps, pe) in enumerate(pred_seg):
        best = (0.0, -1)
        for ti, (ts, te) in enumerate(true_seg):
            if ti in matched_t:
                continue
            inter = max(0, min(pe, te) - max(ps, ts))
            if inter <= 0:
                continue
            union = max(pe, te) - min(ps, ts)
            iou = inter / union if union else 0.0
            if iou > best[0]:
                best = (iou, ti)
        if best[0] >= iou_threshold and best[1] >= 0:
            ti = best[1]
            matched_t.add(ti)
            matched_p.add(pi)
            ious.append(best[0])
            ts, te = true_seg[ti]
            err = (abs(ps - ts) + abs(pe - te)) / 2
            boundary_errors.append(err)
            if abs(ps - ts) <= boundary_tol and abs(pe - te) <= boundary_tol:
                boundary_hits += 1
    tp = len(matched_p)
    fp = len(pred_seg) - tp
    fn = len(true_seg) - len(matched_t)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    bprec = boundary_hits / len(pred_seg) if pred_seg else 0.0
    brec = boundary_hits / len(true_seg) if true_seg else 0.0
    bf1 = 2 * bprec * brec / (bprec + brec) if bprec + brec else 0.0
    return {
        "true_segments": len(true_seg),
        "pred_segments": len(pred_seg),
        "segment_tp": tp,
        "segment_fp": fp,
        "segment_fn": fn,
        "segment_precision_iou50": prec,
        "segment_recall_iou50": rec,
        "segment_f1_iou50": f1,
        "mean_matched_iou": float(np.mean(ious)) if ious else 0.0,
        "boundary_precision_100bp": bprec,
        "boundary_recall_100bp": brec,
        "boundary_f1_100bp": bf1,
        "median_boundary_error_bp": float(np.median(boundary_errors)) if boundary_errors else math.nan,
    }


def fragmentation_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5,
                          short_len: int = 80) -> dict:
    true_seg = runs_from_bool(y_true.astype(bool))
    pred_seg = runs_from_bool(y_prob >= threshold)
    fragments_per_true = []
    split_true = 0
    missed_true = 0
    for ts, te in true_seg:
        count = 0
        for ps, pe in pred_seg:
            if pe <= ts:
                continue
            if ps >= te:
                break
            if min(pe, te) > max(ps, ts):
                count += 1
        fragments_per_true.append(count)
        if count == 0:
            missed_true += 1
        if count > 1:
            split_true += 1
    pred_lengths = [e - s for s, e in pred_seg]
    return {
        "mean_pred_fragments_per_true_te": float(np.mean(fragments_per_true)) if fragments_per_true else 0.0,
        "median_pred_fragments_per_true_te": float(np.median(fragments_per_true)) if fragments_per_true else 0.0,
        "split_true_te_rate": split_true / len(true_seg) if true_seg else 0.0,
        "missed_true_te_rate": missed_true / len(true_seg) if true_seg else 0.0,
        "pred_short_fragment_rate": sum(1 for x in pred_lengths if x < short_len) / len(pred_lengths) if pred_lengths else 0.0,
        "mean_pred_segment_len": float(np.mean(pred_lengths)) if pred_lengths else 0.0,
    }


def merge_small_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    out = mask.copy()
    seg = runs_from_bool(out)
    for (_, e1), (s2, _) in zip(seg, seg[1:]):
        if 0 < s2 - e1 <= max_gap:
            out[e1:s2] = True
    return out


def min_length_filter(mask: np.ndarray, min_len: int) -> np.ndarray:
    out = mask.copy()
    for s, e in runs_from_bool(out):
        if e - s < min_len:
            out[s:e] = False
    return out


def viterbi_smooth(y_prob: np.ndarray, switch_penalty: float) -> np.ndarray:
    eps = 1e-5
    p1 = np.clip(y_prob, eps, 1 - eps)
    emit0 = np.log1p(-p1)
    emit1 = np.log(p1)
    stay = 0.0
    switch = -abs(float(switch_penalty))
    dp0 = np.empty_like(p1, dtype=np.float64)
    dp1 = np.empty_like(p1, dtype=np.float64)
    back0 = np.zeros_like(p1, dtype=np.int8)
    back1 = np.zeros_like(p1, dtype=np.int8)
    dp0[0] = emit0[0]
    dp1[0] = emit1[0]
    for i in range(1, p1.size):
        a0 = dp0[i - 1] + stay
        b0 = dp1[i - 1] + switch
        if a0 >= b0:
            dp0[i] = a0 + emit0[i]
            back0[i] = 0
        else:
            dp0[i] = b0 + emit0[i]
            back0[i] = 1
        a1 = dp1[i - 1] + stay
        b1 = dp0[i - 1] + switch
        if a1 >= b1:
            dp1[i] = a1 + emit1[i]
            back1[i] = 1
        else:
            dp1[i] = b1 + emit1[i]
            back1[i] = 0
    state = 1 if dp1[-1] >= dp0[-1] else 0
    out = np.zeros_like(p1, dtype=bool)
    for i in range(p1.size - 1, -1, -1):
        out[i] = bool(state)
        state = int(back1[i] if state else back0[i])
    return out


def evaluate_mask(y_true: np.ndarray, y_prob_or_mask: np.ndarray, variant: str, threshold: float) -> dict:
    if y_prob_or_mask.dtype == bool:
        y_prob = y_prob_or_mask.astype(np.float32)
    else:
        y_prob = y_prob_or_mask.astype(np.float32)
    row = {"variant": variant, "threshold": threshold}
    row.update(binary_metrics(y_true, y_prob, threshold))
    row.update(segment_metrics(y_true, y_prob, threshold))
    row.update(fragmentation_metrics(y_true, y_prob, threshold))
    return row


def evaluate_by_chrom(truth_by_chrom: dict[str, np.ndarray], prob_by_chrom: dict[str, np.ndarray],
                      weight_by_chrom: dict[str, np.ndarray], variant: str,
                      threshold: float, transform) -> list[dict]:
    rows = []
    weighted = []
    for chrom in sorted(prob_by_chrom):
        valid = weight_by_chrom[chrom] > 0
        if not valid.any():
            continue
        yt = truth_by_chrom[chrom][valid]
        yp = prob_by_chrom[chrom][valid]
        arr = transform(yp)
        row = evaluate_mask(yt, arr, variant, threshold)
        row["chrom"] = chrom
        rows.append(row)
        weighted.append(row)
    if not weighted:
        return rows
    total_bp = sum(float(r["bp_n"]) for r in weighted)
    total_true_segments = sum(float(r["true_segments"]) for r in weighted)
    summary = {"chrom": "WEIGHTED_MEAN", "variant": variant, "threshold": threshold}
    for key in weighted[0]:
        if key in {"chrom", "variant", "threshold"}:
            continue
        vals = []
        weights = []
        for r in weighted:
            try:
                val = float(r[key])
            except Exception:
                continue
            if key.startswith("segment_") or key.startswith("boundary_") or key in {
                "true_segments", "pred_segments", "mean_pred_fragments_per_true_te",
                "median_pred_fragments_per_true_te", "split_true_te_rate",
                "missed_true_te_rate", "pred_short_fragment_rate", "mean_pred_segment_len",
                "mean_matched_iou", "median_boundary_error_bp",
            }:
                weight = max(1.0, float(r.get("true_segments", 1)))
            else:
                weight = max(1.0, float(r.get("bp_n", 1)))
            vals.append(val)
            weights.append(weight)
        if vals:
            summary[key] = float(np.average(vals, weights=weights))
    rows.append(summary)
    return rows


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_eval(args) -> None:
    model, tokenizer, meta = load_trained_model(args.model_dir)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model.to(device)
    model.eval()
    window = int(args.window)
    weights = center_weights(window, args.weight_mode)
    chrom_sum: dict[str, np.ndarray] = {}
    chrom_w: dict[str, np.ndarray] = {}
    chrom_truth: dict[str, np.ndarray] = {}
    records = []
    raw_edge = defaultdict(lambda: [[], []])
    merged_edge_index = []
    n = 0
    for rec in read_jsonl(Path(args.data_jsonl), args.max_windows):
        n += 1
        chrom = rec["chr"]
        start = int(rec["start"])
        end = int(rec["end"])
        seq = rec["sequence"][:window]
        labels = np.asarray(rec["labels"][:window], dtype=np.int8)
        prob = infer_probs(model, tokenizer, seq, window, device)
        if chrom not in chrom_sum or chrom_sum[chrom].size < end:
            old = chrom_sum.get(chrom)
            oldw = chrom_w.get(chrom)
            oldt = chrom_truth.get(chrom)
            chrom_sum[chrom] = np.zeros(end, dtype=np.float32)
            chrom_w[chrom] = np.zeros(end, dtype=np.float32)
            chrom_truth[chrom] = np.zeros(end, dtype=np.int8)
            if old is not None:
                chrom_sum[chrom][:old.size] = old
                chrom_w[chrom][:oldw.size] = oldw
                chrom_truth[chrom][:oldt.size] = oldt
        chrom_sum[chrom][start:end] += prob * weights
        chrom_w[chrom][start:end] += weights
        chrom_truth[chrom][start:end] = labels
        pred_raw = (prob >= args.threshold).astype(np.int8)
        frac = np.arange(window) / max(1, window - 1)
        for name, lo, hi in BIN_DEFS:
            take = (frac >= lo) & (frac < hi)
            raw_edge[name][0].append(labels[take])
            raw_edge[name][1].append(prob[take])
            merged_edge_index.append((name, chrom, start, end, take))
        records.append({"chrom": chrom, "start": start, "end": end})
        if n % 100 == 0:
            print(f"predicted {n} windows", flush=True)

    merged_by_chrom = {}
    truth_by_chrom = {}
    for chrom in sorted(chrom_sum):
        valid = chrom_w[chrom] > 0
        prob = np.zeros_like(chrom_sum[chrom])
        prob[valid] = chrom_sum[chrom][valid] / chrom_w[chrom][valid]
        merged_by_chrom[chrom] = prob
        truth_by_chrom[chrom] = chrom_truth[chrom]

    summary_rows = []
    base = {
        "exp_id": args.exp_id, "model_key": "generanno", "window": window,
        "stride": args.stride, "weight_mode": args.weight_mode,
        "data_jsonl": str(args.data_jsonl), "model_dir": str(args.model_dir),
        "n_windows": n,
    }
    transforms = [
        ("raw_threshold", lambda yp: yp),
        ("gap50_min80", lambda yp: min_length_filter(merge_small_gaps(yp >= args.threshold, 50), 80)),
        ("gap100_min100", lambda yp: min_length_filter(merge_small_gaps(yp >= args.threshold, 100), 100)),
        ("gap200_min100", lambda yp: min_length_filter(merge_small_gaps(yp >= args.threshold, 200), 100)),
        ("hmm_penalty2", lambda yp: viterbi_smooth(yp, 2.0)),
        ("crf_style_penalty4", lambda yp: viterbi_smooth(yp, 4.0)),
    ]
    for variant, transform in transforms:
        for row in evaluate_by_chrom(truth_by_chrom, merged_by_chrom, chrom_w, variant, args.threshold, transform):
            out = dict(base)
            out.update(row)
            summary_rows.append(out)

    edge_rows = []
    for source, edge_dict in [("raw_window", raw_edge)]:
        for name, (ys, ps) in edge_dict.items():
            yt = np.concatenate(ys) if ys else np.asarray([], dtype=np.int8)
            yp = np.concatenate(ps) if ps else np.asarray([], dtype=np.float32)
            row = dict(base)
            row.update({"edge_source": source, "position_bin": name})
            row.update(binary_metrics(yt, yp, args.threshold))
            edge_rows.append(row)
    merged_edge = defaultdict(lambda: [[], []])
    for name, chrom, start, end, take in merged_edge_index:
        merged_edge[name][0].append(truth_by_chrom[chrom][start:end][take])
        merged_edge[name][1].append(merged_by_chrom[chrom][start:end][take])
    for name, (ys, ps) in merged_edge.items():
        yt = np.concatenate(ys) if ys else np.asarray([], dtype=np.int8)
        yp = np.concatenate(ps) if ps else np.asarray([], dtype=np.float32)
        row = dict(base)
        row.update({"edge_source": "merged_coordinate", "position_bin": name})
        row.update(binary_metrics(yt, yp, args.threshold))
        edge_rows.append(row)

    out_dir = Path(args.out_dir)
    write_tsv(out_dir / f"summary_w{window}_s{args.stride}.tsv", summary_rows)
    write_tsv(out_dir / f"edge_bins_w{window}_s{args.stride}.tsv", edge_rows)
    meta_out = {
        "exp_id": args.exp_id,
        "window": window,
        "stride": args.stride,
        "n_windows": n,
        "chroms": sorted(chrom_sum),
        "summary_tsv": str(out_dir / f"summary_w{window}_s{args.stride}.tsv"),
        "edge_tsv": str(out_dir / f"edge_bins_w{window}_s{args.stride}.tsv"),
    }
    (out_dir / f"status_w{window}_s{args.stride}.json").write_text(json.dumps(meta_out, indent=2) + "\n")
    print(json.dumps(meta_out, indent=2), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-id", default="PIPE-TEFM-SEG-SF-20260618")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--data-jsonl", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--window", type=int, required=True)
    ap.add_argument("--stride", type=int, required=True)
    ap.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--max-windows", type=int, default=1200)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()
    run_eval(args)


if __name__ == "__main__":
    main()
