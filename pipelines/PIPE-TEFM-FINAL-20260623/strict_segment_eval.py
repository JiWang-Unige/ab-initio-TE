#!/usr/bin/env python3
"""Strict segment/boundary/fragmentation sweep for TE probability tracks."""
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

SEG = Path("pipelines/PIPE-TEFM-SEG-SF-20260618").resolve()
SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
sys.path.insert(0, str(SEG))
sys.path.insert(0, str(SUPP))

from bp_overlap_segment_eval import (  # noqa: E402
    binary_metrics,
    center_weights,
    infer_probs as infer_segment_probs,
    merge_small_gaps,
    min_length_filter,
    runs_from_bool,
    viterbi_smooth,
)
from te_token_task import load_trained_model  # noqa: E402


def read_jsonl(path: Path, max_records: int | None = None):
    with gzip.open(path, "rt") as handle:
        for i, line in enumerate(handle):
            if max_records is not None and i >= max_records:
                break
            yield json.loads(line)


def best_overlap(pred: tuple[int, int], true_seg: list[tuple[int, int]], start_idx: int = 0) -> tuple[float, float]:
    ps, pe = pred
    plen = max(1, pe - ps)
    best_iou = 0.0
    best_pred_frac = 0.0
    ti = start_idx
    while ti < len(true_seg):
        ts, te = true_seg[ti]
        if ts >= pe:
            break
        inter = max(0, min(pe, te) - max(ps, ts))
        if inter > 0:
            union = max(pe, te) - min(ps, ts)
            best_iou = max(best_iou, inter / union if union else 0.0)
            best_pred_frac = max(best_pred_frac, inter / plen)
        ti += 1
    return best_iou, best_pred_frac


def strict_segment_metrics(y_true: np.ndarray, y_mask: np.ndarray, iou_threshold: float, boundary_tol: int) -> dict:
    true_seg = runs_from_bool(y_true.astype(bool))
    pred_seg = runs_from_bool(y_mask.astype(bool))
    matched_t: set[int] = set()
    matched_p: set[int] = set()
    boundary_hits = 0
    boundary_errors = []
    ious = []
    true_start = 0
    for pi, (ps, pe) in enumerate(pred_seg):
        while true_start < len(true_seg) and true_seg[true_start][1] <= ps:
            true_start += 1
        best = (0.0, -1)
        ti = true_start
        while ti < len(true_seg):
            ts, te = true_seg[ti]
            if ts >= pe:
                break
            if ti in matched_t:
                ti += 1
                continue
            inter = max(0, min(pe, te) - max(ps, ts))
            if inter <= 0:
                ti += 1
                continue
            union = max(pe, te) - min(ps, ts)
            iou = inter / union if union else 0.0
            if iou > best[0]:
                best = (iou, ti)
            ti += 1
        if best[0] >= iou_threshold and best[1] >= 0:
            ti = best[1]
            matched_t.add(ti)
            matched_p.add(pi)
            ious.append(best[0])
            ts, te = true_seg[ti]
            boundary_errors.append((abs(ps - ts) + abs(pe - te)) / 2)
            if abs(ps - ts) <= boundary_tol and abs(pe - te) <= boundary_tol:
                boundary_hits += 1
    tp = len(matched_p)
    fp = len(pred_seg) - tp
    fn = len(true_seg) - len(matched_t)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    denom = prec + rec
    f1 = 2 * prec * rec / denom if denom else 0.0
    bprec = boundary_hits / len(pred_seg) if pred_seg else 0.0
    brec = boundary_hits / len(true_seg) if true_seg else 0.0
    bf1 = 2 * bprec * brec / (bprec + brec) if bprec + brec else 0.0
    return {
        "true_segments": len(true_seg),
        "pred_segments": len(pred_seg),
        "segment_tp": tp,
        "segment_fp": fp,
        "segment_fn": fn,
        "segment_precision": prec,
        "segment_recall": rec,
        "segment_f1": f1,
        "mean_matched_iou": float(np.mean(ious)) if ious else 0.0,
        "boundary_precision": bprec,
        "boundary_recall": brec,
        "boundary_f1": bf1,
        "median_boundary_error_bp": float(np.median(boundary_errors)) if boundary_errors else math.nan,
    }


def fragmentation_truth_diagnostics(y_true: np.ndarray, y_mask: np.ndarray, short_len: int = 80) -> dict:
    true_seg = runs_from_bool(y_true.astype(bool))
    pred_seg = runs_from_bool(y_mask.astype(bool))
    short_pred = [seg for seg in pred_seg if seg[1] - seg[0] < short_len]
    pred_backed = 0
    short_backed = 0
    short_iou_sum = 0.0
    true_start = 0
    for seg in pred_seg:
        while true_start < len(true_seg) and true_seg[true_start][1] <= seg[0]:
            true_start += 1
        _, pred_frac = best_overlap(seg, true_seg, true_start)
        if pred_frac >= 0.5:
            pred_backed += 1
    true_start = 0
    for seg in short_pred:
        while true_start < len(true_seg) and true_seg[true_start][1] <= seg[0]:
            true_start += 1
        best_iou, pred_frac = best_overlap(seg, true_seg, true_start)
        short_iou_sum += best_iou
        if pred_frac >= 0.5:
            short_backed += 1
    fragments_per_true = []
    pred_start = 0
    for ts, te in true_seg:
        while pred_start < len(pred_seg) and pred_seg[pred_start][1] <= ts:
            pred_start += 1
        count = 0
        pi = pred_start
        while pi < len(pred_seg):
            ps, pe = pred_seg[pi]
            if ps >= te:
                break
            if min(pe, te) > max(ps, ts):
                count += 1
            pi += 1
        fragments_per_true.append(count)
    return {
        "pred_true_backed_rate": pred_backed / len(pred_seg) if pred_seg else 0.0,
        "short_pred_segments": len(short_pred),
        "short_true_backed_rate": short_backed / len(short_pred) if short_pred else 0.0,
        "short_mean_best_iou": short_iou_sum / len(short_pred) if short_pred else 0.0,
        "mean_fragments_per_true": float(np.mean(fragments_per_true)) if fragments_per_true else 0.0,
        "split_true_rate": sum(1 for x in fragments_per_true if x > 1) / len(fragments_per_true) if fragments_per_true else 0.0,
        "missed_true_rate": sum(1 for x in fragments_per_true if x == 0) / len(fragments_per_true) if fragments_per_true else 0.0,
    }


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


def infer_probs_for_label_mode(
    model,
    tokenizer,
    seq: str,
    window: int,
    device: torch.device,
    label_mode: str,
) -> np.ndarray:
    """Mirror the tokenization/label geometry used during fine-tuning."""
    if label_mode == "single_nt_nospecial":
        enc = tokenizer(
            seq[:window],
            add_special_tokens=False,
            truncation=True,
            max_length=window,
            padding="max_length",
            return_tensors="pt",
        )
        enc = {k: v.to(device) for k, v in enc.items() if k in {"input_ids", "attention_mask"}}
        with torch.no_grad():
            logits = model(**enc).logits[0]
        return torch.softmax(logits, dim=-1)[:, 1].detach().cpu().numpy()[:window]
    if label_mode == "ntv3_single":
        enc = tokenizer(seq[:window], truncation=True, max_length=window, padding="max_length", return_tensors="pt")
        enc = {k: v.to(device) for k, v in enc.items() if k in {"input_ids", "attention_mask"}}
        with torch.no_grad():
            logits = model(**enc).logits[0]
        prob = torch.softmax(logits, dim=-1)[:, 1].detach().cpu().numpy()
        out = np.zeros(window, dtype=np.float32)
        n = min(window, prob.shape[0])
        out[:n] = prob[:n]
        return out
    if label_mode in {"nt_kmer", "offset_or_kmer"}:
        max_len = ((window + 5) // 6 + 2 + 7) // 8 * 8
        try:
            enc = tokenizer(
                seq[:window],
                truncation=True,
                max_length=max_len,
                padding="max_length",
                return_offsets_mapping=True,
                return_tensors="pt",
            )
            offsets = enc.pop("offset_mapping")[0].detach().cpu().numpy()
            enc = {k: v.to(device) for k, v in enc.items() if k in {"input_ids", "attention_mask"}}
            with torch.no_grad():
                logits = model(**enc).logits[0]
            token_prob = torch.softmax(logits, dim=-1)[:, 1].detach().cpu().numpy()
            out = np.zeros(window, dtype=np.float32)
            cov = np.zeros(window, dtype=np.float32)
            for prob, (start, end) in zip(token_prob, offsets):
                start = int(start)
                end = int(end)
                if start < end:
                    s = max(0, min(window, start))
                    e = max(0, min(window, end))
                    out[s:e] += float(prob)
                    cov[s:e] += 1.0
            take = cov > 0
            out[take] /= cov[take]
            return out
        except Exception:
            enc = tokenizer(seq[:window], truncation=True, max_length=max_len, padding="max_length", return_tensors="pt")
            raw_tokens = tokenizer.tokenize(seq[:window])
            enc = {k: v.to(device) for k, v in enc.items() if k in {"input_ids", "attention_mask"}}
            with torch.no_grad():
                logits = model(**enc).logits[0]
            token_prob = torch.softmax(logits, dim=-1)[:, 1].detach().cpu().numpy()
            out = np.zeros(window, dtype=np.float32)
            pos = 0
            for i, tok in enumerate(raw_tokens, start=1):
                if i >= min(max_len - 1, token_prob.shape[0]):
                    break
                span_len = max(1, len(tok.replace(" ", "")))
                end = min(window, pos + span_len)
                if pos < end:
                    out[pos:end] = float(token_prob[i])
                pos = end
                if pos >= window:
                    break
            return out
    return infer_segment_probs(model, tokenizer, seq, window, device)


def run(args) -> None:
    model, tokenizer, meta = load_trained_model(args.model_dir)
    label_mode = str(meta.get("token_label_mode", ""))
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model.to(device)
    model.eval()
    weights = center_weights(args.window, args.weight_mode)
    chrom_sum: dict[str, np.ndarray] = {}
    chrom_w: dict[str, np.ndarray] = {}
    chrom_truth: dict[str, np.ndarray] = {}
    n = 0
    for rec in read_jsonl(Path(args.data_jsonl), args.max_windows):
        n += 1
        chrom = rec["chr"]
        start = int(rec["start"])
        end = int(rec["end"])
        labels = np.asarray(rec["labels"][: args.window], dtype=np.int8)
        prob = infer_probs_for_label_mode(model, tokenizer, rec["sequence"][: args.window], args.window, device, label_mode)
        if chrom not in chrom_sum or chrom_sum[chrom].size < end:
            old_sum, old_w, old_t = chrom_sum.get(chrom), chrom_w.get(chrom), chrom_truth.get(chrom)
            chrom_sum[chrom] = np.zeros(end, dtype=np.float32)
            chrom_w[chrom] = np.zeros(end, dtype=np.float32)
            chrom_truth[chrom] = np.zeros(end, dtype=np.int8)
            if old_sum is not None:
                chrom_sum[chrom][: old_sum.size] = old_sum
                chrom_w[chrom][: old_w.size] = old_w
                chrom_truth[chrom][: old_t.size] = old_t
        chrom_sum[chrom][start:end] += prob * weights
        chrom_w[chrom][start:end] += weights
        chrom_truth[chrom][start:end] = labels
        if n % 100 == 0:
            print(f"predicted {n} windows", flush=True)

    base = {
        "exp_id": args.exp_id,
        "model_dir": args.model_dir,
        "data_jsonl": args.data_jsonl,
        "window": args.window,
        "stride": args.stride,
        "weight_mode": args.weight_mode,
        "n_windows": n,
    }
    transforms = [
        ("raw_threshold", lambda yp: yp >= args.threshold),
        ("gap50_min80", lambda yp: min_length_filter(merge_small_gaps(yp >= args.threshold, 50), 80)),
        ("gap100_min100", lambda yp: min_length_filter(merge_small_gaps(yp >= args.threshold, 100), 100)),
        ("hmm_penalty2", lambda yp: viterbi_smooth(yp, 2.0)),
        ("crf_style_penalty4", lambda yp: viterbi_smooth(yp, 4.0)),
    ]
    rows = []
    for chrom in sorted(chrom_sum):
        valid = chrom_w[chrom] > 0
        if not valid.any():
            continue
        prob = np.zeros_like(chrom_sum[chrom])
        prob[valid] = chrom_sum[chrom][valid] / chrom_w[chrom][valid]
        truth = chrom_truth[chrom][valid]
        prob = prob[valid]
        for variant, transform in transforms:
            known = truth >= 0
            truth_binary = (truth == 1)
            mask = transform(prob).astype(bool)
            mask[~known] = False
            for iou in args.iou_thresholds:
                for tol in args.boundary_tolerances:
                    row = dict(base)
                    row.update({"chrom": chrom, "variant": variant, "threshold": args.threshold, "iou_threshold": iou, "boundary_tol_bp": tol})
                    row["ignored_bp"] = int((~known).sum())
                    row.update(binary_metrics(truth_binary[known], mask[known].astype(np.float32), 0.5))
                    row.update(strict_segment_metrics(truth_binary, mask, iou, tol))
                    row.update(fragmentation_truth_diagnostics(truth_binary, mask))
                    rows.append(row)
    write_tsv(Path(args.out_tsv), rows)
    status = {"ok": True, "rows": len(rows), "out_tsv": args.out_tsv, "n_windows": n}
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-id", default="PIPE-TEFM-FINAL-20260623")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--data-jsonl", required=True)
    ap.add_argument("--out-tsv", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--window", type=int, required=True)
    ap.add_argument("--stride", type=int, required=True)
    ap.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--iou-thresholds", type=float, nargs="+", default=[0.5, 0.7, 0.8, 0.9])
    ap.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5, 10, 25, 50, 100])
    ap.add_argument("--max-windows", type=int, default=1200)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
