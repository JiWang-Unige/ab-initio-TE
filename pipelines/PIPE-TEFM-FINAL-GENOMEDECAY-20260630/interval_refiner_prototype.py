#!/usr/bin/env python3
"""Bounded frozen-bp interval refiner prototype.

The refiner is deployable in the sense that inference uses only frozen bp-model
probabilities and local interval/gap features. Ground truth is used only to fit
the lightweight keep/drop and merge classifiers on a coordinate-heldout split.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

FINAL = Path("pipelines/PIPE-TEFM-FINAL-20260623").resolve()
THIS = Path("pipelines/PIPE-TEFM-FINAL-GENOMEDECAY-20260630").resolve()
sys.path.insert(0, str(FINAL))
sys.path.insert(0, str(THIS))

from strict_segment_eval import (  # noqa: E402
    binary_metrics,
    fragmentation_truth_diagnostics,
    runs_from_bool,
    strict_segment_metrics,
    viterbi_smooth,
)
from fragment_sanity_eval import (  # noqa: E402
    build_tracks,
    mask_deleted_backing_metrics,
    oracle_fill_supported_true_intervals,
)


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


def safe_stats(values: np.ndarray) -> list[float]:
    if values.size == 0:
        return [0.0, 0.0, 0.0, 0.0, 0.0]
    return [
        float(np.mean(values)),
        float(np.max(values)),
        float(np.min(values)),
        float(np.std(values)),
        float(np.quantile(values, 0.1)),
    ]


def segment_feature(prob: np.ndarray, seg: tuple[int, int], prev_gap: int, next_gap: int) -> list[float]:
    s, e = seg
    vals = prob[s:e]
    left = prob[max(0, s - 50) : s]
    right = prob[e : min(prob.size, e + 50)]
    edge = np.concatenate([vals[: min(20, vals.size)], vals[max(0, vals.size - 20) :]]) if vals.size else np.array([])
    valley_frac = float((vals < 0.5).mean()) if vals.size else 0.0
    return [
        math.log1p(max(0, e - s)),
        math.log1p(max(0, prev_gap)),
        math.log1p(max(0, next_gap)),
        valley_frac,
        *safe_stats(vals),
        *safe_stats(edge),
        *safe_stats(left),
        *safe_stats(right),
    ]


def gap_feature(prob: np.ndarray, left: tuple[int, int], right: tuple[int, int]) -> list[float]:
    ls, le = left
    rs, re = right
    gap = prob[le:rs]
    lvals = prob[ls:le]
    rvals = prob[rs:re]
    return [
        math.log1p(max(0, rs - le)),
        math.log1p(max(0, le - ls)),
        math.log1p(max(0, re - rs)),
        *safe_stats(gap),
        *safe_stats(lvals),
        *safe_stats(rvals),
    ]


def best_true_id(seg: tuple[int, int], true_seg: list[tuple[int, int]]) -> tuple[int, float]:
    s, e = seg
    plen = max(1, e - s)
    best = (-1, 0.0)
    for ti, (ts, te) in enumerate(true_seg):
        if te <= s:
            continue
        if ts >= e:
            break
        inter = max(0, min(e, te) - max(s, ts))
        frac = inter / plen if plen else 0.0
        if frac > best[1]:
            best = (ti, frac)
    return best


def build_training_tables(prob: np.ndarray, truth: np.ndarray, mask: np.ndarray):
    pred_seg = runs_from_bool(mask.astype(bool))
    true_seg = runs_from_bool(truth.astype(bool))
    seg_x, seg_y, gap_x, gap_y = [], [], [], []
    for i, seg in enumerate(pred_seg):
        prev_gap = seg[0] - pred_seg[i - 1][1] if i > 0 else 0
        next_gap = pred_seg[i + 1][0] - seg[1] if i + 1 < len(pred_seg) else 0
        tid, frac = best_true_id(seg, true_seg)
        seg_x.append(segment_feature(prob, seg, prev_gap, next_gap))
        seg_y.append(1 if tid >= 0 and frac >= 0.5 else 0)
    best_ids = [best_true_id(seg, true_seg)[0] for seg in pred_seg]
    for i, (left, right) in enumerate(zip(pred_seg, pred_seg[1:])):
        if right[0] <= left[1]:
            continue
        gap_x.append(gap_feature(prob, left, right))
        gap_y.append(1 if best_ids[i] >= 0 and best_ids[i] == best_ids[i + 1] else 0)
    return np.asarray(seg_x, dtype=float), np.asarray(seg_y, dtype=int), np.asarray(gap_x, dtype=float), np.asarray(gap_y, dtype=int)


class ConstantModel:
    def __init__(self, value: int):
        self.value = int(value)

    def predict_proba(self, x):
        n = len(x)
        if self.value == 1:
            return np.column_stack([np.zeros(n), np.ones(n)])
        return np.column_stack([np.ones(n), np.zeros(n)])


def fit_classifier(x: np.ndarray, y: np.ndarray, seed: int, max_samples: int = 5000):
    if x.size == 0 or y.size == 0:
        return ConstantModel(0), {"status": "constant_empty", "n": int(len(y)), "positive_rate": 0.0}
    positive_rate = float(np.mean(y))
    if len(set(y.tolist())) < 2:
        return ConstantModel(int(y[0])), {"status": "constant_one_class", "n": int(len(y)), "positive_rate": positive_rate}
    try:
        from sklearn.ensemble import RandomForestClassifier

        n_total = int(len(y))
        if n_total > max_samples:
            rng = np.random.default_rng(seed)
            pos = np.flatnonzero(y == 1)
            neg = np.flatnonzero(y == 0)
            take_pos = min(len(pos), max_samples // 2)
            take_neg = min(len(neg), max_samples - take_pos)
            if take_pos:
                pos = rng.choice(pos, size=take_pos, replace=False)
            if take_neg:
                neg = rng.choice(neg, size=take_neg, replace=False)
            idx = np.concatenate([pos, neg])
            rng.shuffle(idx)
            x_fit = x[idx]
            y_fit = y[idx]
        else:
            x_fit = x
            y_fit = y
        clf = RandomForestClassifier(
            n_estimators=50,
            min_samples_leaf=4,
            class_weight="balanced_subsample",
            random_state=seed,
            n_jobs=2,
        )
        clf.fit(x_fit, y_fit)
        return clf, {
            "status": "random_forest",
            "n": n_total,
            "fit_n": int(len(y_fit)),
            "positive_rate": positive_rate,
            "fit_positive_rate": float(np.mean(y_fit)) if len(y_fit) else 0.0,
        }
    except Exception as exc:
        return ConstantModel(1 if positive_rate >= 0.5 else 0), {
            "status": "fallback_constant",
            "reason": repr(exc),
            "n": int(len(y)),
            "positive_rate": positive_rate,
        }


def apply_keep_drop(prob: np.ndarray, mask: np.ndarray, keep_model, keep_thr: float) -> np.ndarray:
    pred_seg = runs_from_bool(mask.astype(bool))
    out = np.zeros_like(mask, dtype=bool)
    for i, seg in enumerate(pred_seg):
        prev_gap = seg[0] - pred_seg[i - 1][1] if i > 0 else 0
        next_gap = pred_seg[i + 1][0] - seg[1] if i + 1 < len(pred_seg) else 0
        x = np.asarray([segment_feature(prob, seg, prev_gap, next_gap)], dtype=float)
        keep = float(keep_model.predict_proba(x)[0, 1]) >= keep_thr
        if keep:
            out[seg[0] : seg[1]] = True
    return out


def apply_gap_merge(prob: np.ndarray, mask: np.ndarray, merge_model, merge_thr: float, max_gap: int) -> np.ndarray:
    out = mask.copy().astype(bool)
    pred_seg = runs_from_bool(out)
    for left, right in zip(pred_seg, pred_seg[1:]):
        gap = right[0] - left[1]
        if gap <= 0 or gap > max_gap:
            continue
        x = np.asarray([gap_feature(prob, left, right)], dtype=float)
        merge = float(merge_model.predict_proba(x)[0, 1]) >= merge_thr
        if merge:
            out[left[1] : right[0]] = True
    return out


def evaluate_mask(truth: np.ndarray, prob: np.ndarray, mask: np.ndarray, label: str, threshold: float, iou: float, tol: int, base_mask: np.ndarray) -> dict:
    known = truth >= 0
    truth_binary = truth == 1
    eval_mask = mask.astype(bool).copy()
    eval_mask[~known] = False
    row = {"variant": label, "threshold": threshold, "iou_threshold": iou, "boundary_tol_bp": tol, "ignored_bp": int((~known).sum())}
    row.update(binary_metrics(truth_binary[known], eval_mask[known].astype(np.float32), 0.5))
    row.update(strict_segment_metrics(truth_binary, eval_mask, iou, tol))
    row.update(fragmentation_truth_diagnostics(truth_binary, eval_mask))
    row.update(mask_deleted_backing_metrics(truth_binary, base_mask, eval_mask))
    return row


def train_proxy_score(truth: np.ndarray, mask: np.ndarray) -> float:
    """Cheap threshold-selection proxy; final reporting still uses strict metrics."""
    known = truth >= 0
    if not np.any(known):
        return 0.0
    y = truth[known] == 1
    pred = mask[known].astype(bool)
    tp = float(np.logical_and(y, pred).sum())
    fp = float(np.logical_and(~y, pred).sum())
    fn = float(np.logical_and(y, ~pred).sum())
    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + fn + 1e-9)
    f1 = 2.0 * precision * recall / (precision + recall + 1e-9)
    true_segments = max(1, len(runs_from_bool((truth == 1).astype(bool))))
    pred_segments = max(1, len(runs_from_bool(mask.astype(bool))))
    count_penalty = min(0.2, 0.02 * abs(math.log(pred_segments / true_segments)))
    return float(f1 - count_penalty)


def tune_thresholds(prob_train: np.ndarray, truth_train: np.ndarray, raw_train: np.ndarray, keep_model, merge_model, max_gap: int, iou: float, tol: int) -> dict:
    best = {"variant": "", "proxy_score": -1.0, "keep_thr": 0.5, "merge_thr": 0.5}
    for keep_thr in [0.3, 0.5, 0.7]:
        kept = apply_keep_drop(prob_train, raw_train, keep_model, keep_thr)
        score = train_proxy_score(truth_train, kept)
        if score > best["proxy_score"]:
            best = {"variant": "keep_drop", "proxy_score": score, "keep_thr": keep_thr, "merge_thr": 0.5}
        for merge_thr in [0.3, 0.5, 0.7]:
            merged = apply_gap_merge(prob_train, kept, merge_model, merge_thr, max_gap)
            score = train_proxy_score(truth_train, merged)
            if score > best["proxy_score"]:
                best = {"variant": "keep_drop_gap_merge", "proxy_score": score, "keep_thr": keep_thr, "merge_thr": merge_thr}
    for merge_thr in [0.3, 0.5, 0.7]:
        merged = apply_gap_merge(prob_train, raw_train, merge_model, merge_thr, max_gap)
        score = train_proxy_score(truth_train, merged)
        if score > best["proxy_score"]:
            best = {"variant": "gap_merge", "proxy_score": score, "keep_thr": 0.5, "merge_thr": merge_thr}
    return best


def write_report(out_dir: Path, rows: list[dict], status: dict) -> None:
    headline = [r for r in rows if r["split"] == "test" and r["iou_threshold"] == 0.8 and r["boundary_tol_bp"] == 5]
    best = sorted(headline, key=lambda r: r["segment_f1"], reverse=True)[0] if headline else {}
    raw = next((r for r in headline if r["variant"].endswith("_raw")), {})
    crf = next((r for r in headline if r["variant"].endswith("_crf")), {})
    refiner = next((r for r in headline if r["variant"].startswith("refiner")), {})
    lines = [
        "# PIPE-TEFM-FINAL-INTERVALREFINER-20260630",
        "",
        "## Scope",
        "",
        "Bounded frozen-bp interval-refiner prototype using a coordinate train/test split on mouse chr1 windows.",
        "The refiner trains lightweight RandomForest/constant fallback classifiers on frozen bp probabilities and local interval/gap features.",
        "",
        "## Headline",
        "",
        f"- Windows used: {status.get('n_windows')}; train fraction: {status.get('train_fraction')}.",
        f"- Segment classifier: {status.get('keep_model')}.",
        f"- Gap classifier: {status.get('merge_model')}.",
    ]
    if raw:
        lines.append(f"- Test `{raw['variant']}` segment-F1@IoU0.8/boundary5: {raw['segment_f1']:.4f}.")
    if crf:
        lines.append(f"- Test `{crf['variant']}` segment-F1@IoU0.8/boundary5: {crf['segment_f1']:.4f}.")
    if refiner:
        lines.append(
            f"- Test refiner `{refiner['variant']}` segment-F1 {refiner['segment_f1']:.4f}, boundary-F1 {refiner['boundary_f1']:.4f}, missed true rate {refiner['missed_true_rate']:.4f}."
        )
    if best:
        lines.append(f"- Best test variant: `{best['variant']}` segment-F1 {best['segment_f1']:.4f}.")
    lines += [
        "",
        "## Interpretation",
        "",
        "- This prototype is deployable in form because test-time decisions use only logits and interval/gap features.",
        "- A refiner is only useful if it beats consensus+CRF without raising missed_true_rate or deleting true-backed fragments.",
        "- If bounded performance is weak, the next refiner should use richer features or optimize proposal generation rather than post-hoc threshold tuning.",
        "",
        "## Outputs",
        "",
        "- `interval_refiner_metrics.tsv`",
        "- `interval_refiner_status.json`",
    ]
    (out_dir / "INTERVAL_REFINER_REPORT.md").write_text("\n".join(lines) + "\n")


def run(args) -> None:
    chrom_prob, chrom_truth, n_windows = build_tracks(args)
    rows: list[dict] = []
    statuses = []
    iou = 0.8
    tol = 5
    for chrom in sorted(chrom_prob):
        prob = chrom_prob[chrom][args.prob_mode]
        truth = chrom_truth[chrom]
        print(f"[interval-refiner] chrom={chrom} bp={prob.size} start", flush=True)
        split_idx = int(prob.size * args.train_fraction)
        prob_train, truth_train = prob[:split_idx], truth[:split_idx]
        prob_test, truth_test = prob[split_idx:], truth[split_idx:]
        raw_train = prob_train >= args.threshold
        raw_test = prob_test >= args.threshold
        print(f"[interval-refiner] chrom={chrom} building training tables", flush=True)
        seg_x, seg_y, gap_x, gap_y = build_training_tables(prob_train, truth_train == 1, raw_train)
        print(
            f"[interval-refiner] chrom={chrom} segment_candidates={len(seg_y)} gap_candidates={len(gap_y)} fitting",
            flush=True,
        )
        keep_model, keep_status = fit_classifier(seg_x, seg_y, args.seed)
        merge_model, merge_status = fit_classifier(gap_x, gap_y, args.seed)
        print(f"[interval-refiner] chrom={chrom} tuning thresholds", flush=True)
        tuned = tune_thresholds(prob_train, truth_train, raw_train, keep_model, merge_model, args.max_gap, iou, tol)

        print(f"[interval-refiner] chrom={chrom} applying test variants", flush=True)
        variants = {
            f"{args.prob_mode}_raw": raw_test,
            f"{args.prob_mode}_crf": viterbi_smooth(prob_test, 4.0),
            "oracle_fill_supported_true": oracle_fill_supported_true_intervals(truth_test == 1, raw_test),
        }
        keep_mask = apply_keep_drop(prob_test, raw_test, keep_model, tuned["keep_thr"])
        merge_mask = apply_gap_merge(prob_test, raw_test, merge_model, tuned["merge_thr"], args.max_gap)
        keep_merge_mask = apply_gap_merge(prob_test, keep_mask, merge_model, tuned["merge_thr"], args.max_gap)
        variants["refiner_keep_drop"] = keep_mask
        variants["refiner_gap_merge"] = merge_mask
        variants["refiner_keep_drop_gap_merge"] = keep_merge_mask

        for name, mask in variants.items():
            print(f"[interval-refiner] chrom={chrom} evaluating {name}", flush=True)
            for eval_iou in args.iou_thresholds:
                for eval_tol in args.boundary_tolerances:
                    row = evaluate_mask(truth_test, prob_test, mask, name, args.threshold, eval_iou, eval_tol, raw_test)
                    row.update({
                        "exp_id": args.exp_id,
                        "chrom": chrom,
                        "split": "test",
                        "prob_mode": args.prob_mode,
                        "n_windows": n_windows,
                        "train_fraction": args.train_fraction,
                        "train_segment_candidates": int(len(seg_y)),
                        "train_gap_candidates": int(len(gap_y)),
                        "keep_model_status": keep_status["status"],
                        "merge_model_status": merge_status["status"],
                        "keep_positive_rate": keep_status["positive_rate"],
                        "merge_positive_rate": merge_status["positive_rate"],
                        "tuned_variant": tuned["variant"],
                        "tuned_keep_thr": tuned["keep_thr"],
                        "tuned_merge_thr": tuned["merge_thr"],
                    })
                    rows.append(row)
        statuses.append({
            "chrom": chrom,
            "train_bp": int(split_idx),
            "test_bp": int(prob.size - split_idx),
            "keep_model": keep_status,
            "merge_model": merge_status,
            "tuned": tuned,
        })

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(out_dir / "interval_refiner_metrics.tsv", rows)
    status = {
        "ok": True,
        "exp_id": args.exp_id,
        "n_windows": n_windows,
        "train_fraction": args.train_fraction,
        "prob_mode": args.prob_mode,
        "chrom_status": statuses,
        "keep_model": statuses[0]["keep_model"] if statuses else {},
        "merge_model": statuses[0]["merge_model"] if statuses else {},
        "outputs": {
            "metrics": str(out_dir / "interval_refiner_metrics.tsv"),
            "report": str(out_dir / "INTERVAL_REFINER_REPORT.md"),
            "status": str(out_dir / "interval_refiner_status.json"),
        },
    }
    (out_dir / "interval_refiner_status.json").write_text(json.dumps(status, indent=2) + "\n")
    write_report(out_dir, rows, status)
    print(json.dumps(status, indent=2), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-id", default="PIPE-TEFM-FINAL-INTERVALREFINER-20260630")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--data-jsonl", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--window", type=int, required=True)
    ap.add_argument("--stride", type=int, required=True)
    ap.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--prob-mode", choices=["forward", "reverse", "mean_logit", "max_prob", "consensus_min"], default="consensus_min")
    ap.add_argument("--train-fraction", type=float, default=0.6)
    ap.add_argument("--max-gap", type=int, default=1000)
    ap.add_argument("--iou-thresholds", type=float, nargs="+", default=[0.8, 0.9])
    ap.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5, 10, 25])
    ap.add_argument("--max-windows", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
