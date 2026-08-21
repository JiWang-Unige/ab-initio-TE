#!/usr/bin/env python3
"""Joint backbone + structured decoder smoke for TE fragmentation.

This bounded experiment differs from the frozen-logit decoder screen: the
structured loss is attached to the token classifier output during fine-tuning,
so gradients can update the model head/backbone instead of only a post-hoc
probability track. It is intentionally small and single-seed.
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

os.environ.setdefault("TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD", "1")
os.environ.setdefault("WANDB_DISABLED", "true")

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader, Dataset

SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
FINAL = Path("pipelines/PIPE-TEFM-FINAL-20260623").resolve()
sys.path.insert(0, str(SUPP))
sys.path.insert(0, str(FINAL))

from te_token_task import WindowDataset, load_tokenizer, load_trained_model  # noqa: E402
from strict_segment_eval import (  # noqa: E402
    binary_metrics,
    fragmentation_truth_diagnostics,
    runs_from_bool,
    strict_segment_metrics,
    viterbi_smooth,
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


class LimitedDataset(Dataset):
    def __init__(self, base: Dataset, max_samples: int | None):
        self.base = base
        self.n = len(base) if max_samples is None else min(len(base), max_samples)

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, idx: int):
        return self.base[idx]


class MarkovDecoder(nn.Module):
    def __init__(self, mode: str):
        super().__init__()
        if mode == "hmm":
            init = torch.tensor([[2.0, -2.0], [-2.0, 2.0]], dtype=torch.float32)
        else:
            init = torch.tensor([[1.5, -1.5], [-1.5, 1.5]], dtype=torch.float32)
        self.transitions = nn.Parameter(init)
        self.mode = mode

    def nll_one(self, emissions: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        known = labels >= 0
        emissions = emissions[known]
        labels = labels[known].long()
        if labels.numel() < 2:
            return emissions.sum() * 0.0
        if self.mode == "hmm":
            # HMM-like: normalized transition rows and normalized emissions.
            em = F.log_softmax(emissions, dim=-1)
            trans = F.log_softmax(self.transitions, dim=-1)
        else:
            # CRF-like: free discriminative transition scores.
            em = emissions
            trans = self.transitions
        gold = em[0, labels[0]]
        for t in range(1, labels.numel()):
            gold = gold + trans[labels[t - 1], labels[t]] + em[t, labels[t]]
        alpha = em[0]
        for t in range(1, labels.numel()):
            alpha = torch.logsumexp(alpha.view(2, 1) + trans + em[t].view(1, 2), dim=0)
        return (torch.logsumexp(alpha, dim=0) - gold) / labels.numel()

    def loss(self, emissions: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        losses = [self.nll_one(emissions[i], labels[i]) for i in range(emissions.shape[0])]
        return torch.stack(losses).mean()

    def decode_one(self, emissions: torch.Tensor, labels: torch.Tensor | None = None) -> np.ndarray:
        if labels is not None:
            known = labels >= 0
            emissions = emissions[known]
        if self.mode == "hmm":
            em = F.log_softmax(emissions, dim=-1)
            trans = F.log_softmax(self.transitions, dim=-1)
        else:
            em = emissions
            trans = self.transitions
        delta = em[0]
        back = []
        for t in range(1, em.shape[0]):
            score = delta.view(2, 1) + trans + em[t].view(1, 2)
            back.append(score.argmax(dim=0))
            delta = score.max(dim=0).values
        state = int(delta.argmax())
        path = [state]
        for bp in reversed(back):
            state = int(bp[state])
            path.append(state)
        return np.asarray(path[::-1], dtype=bool)


def soft_fragment_loss(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    """Differentiable duration-aware auxiliary loss.

    Penalizes short positive islands via expected transition mass while adding
    extra BCE weight near true boundaries. This is a bounded semi-Markov proxy,
    not a full exact semi-Markov dynamic program.
    """
    probs = torch.softmax(logits, dim=-1)[..., 1]
    known = labels >= 0
    y = labels.clamp(min=0).float()
    if known.sum() == 0:
        return logits.sum() * 0.0
    bce = F.binary_cross_entropy(probs[known], y[known], reduction="mean")
    if probs.shape[1] < 3:
        return bce
    trans_mass = torch.abs(probs[:, 1:] - probs[:, :-1])
    true_trans = (labels[:, 1:] != labels[:, :-1]) & (labels[:, 1:] >= 0) & (labels[:, :-1] >= 0)
    false_jitter = trans_mass[~true_trans] if (~true_trans).any() else trans_mass.reshape(-1)
    boundary = true_trans.float()
    boundary_recall = F.binary_cross_entropy(
        trans_mass.clamp(1e-4, 1 - 1e-4),
        boundary,
        reduction="mean",
    )
    return bce + 0.15 * false_jitter.mean() + 0.25 * boundary_recall


def transition_boundary_loss(probs: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    if probs.shape[1] < 2:
        return probs.sum() * 0.0
    known_pair = (labels[:, 1:] >= 0) & (labels[:, :-1] >= 0)
    if not known_pair.any():
        return probs.sum() * 0.0
    target = ((labels[:, 1:] != labels[:, :-1]) & known_pair).float()
    transition_mass = torch.abs(probs[:, 1:] - probs[:, :-1]).clamp(1e-4, 1 - 1e-4)
    return F.binary_cross_entropy(transition_mass[known_pair], target[known_pair], reduction="mean")


def boundary_aux_loss(logits: torch.Tensor, labels: torch.Tensor, te_class_weight: float) -> torch.Tensor:
    probs = torch.softmax(logits, dim=-1)[..., 1]
    known = labels >= 0
    if known.sum() == 0:
        return logits.sum() * 0.0
    weight = torch.tensor([1.0, te_class_weight], device=logits.device)
    ce = F.cross_entropy(logits.reshape(-1, 2), labels.reshape(-1), weight=weight, ignore_index=-100)
    return ce + 0.35 * transition_boundary_loss(probs, labels)


def semimarkov_retention_loss(logits: torch.Tensor, labels: torch.Tensor, te_class_weight: float) -> torch.Tensor:
    probs = torch.softmax(logits, dim=-1)[..., 1]
    known = labels >= 0
    pos = labels == 1
    if known.sum() == 0:
        return logits.sum() * 0.0
    base = soft_fragment_loss(logits, labels)
    weight = torch.tensor([1.0, te_class_weight], device=logits.device)
    ce = F.cross_entropy(logits.reshape(-1, 2), labels.reshape(-1), weight=weight, ignore_index=-100)
    if pos.any():
        retention = (1.0 - probs[pos]).mean()
        positive_bce = F.binary_cross_entropy(probs[pos].clamp(1e-4, 1 - 1e-4), torch.ones_like(probs[pos]), reduction="mean")
    else:
        retention = logits.sum() * 0.0
        positive_bce = logits.sum() * 0.0
    return 0.45 * base + 0.35 * ce + 0.45 * retention + 0.20 * positive_bce


def true_segments_from_labels(row: torch.Tensor) -> list[tuple[int, int]]:
    arr = row.detach().cpu().numpy()
    segments: list[tuple[int, int]] = []
    start = None
    for i, value in enumerate(arr.tolist()):
        if value == 1 and start is None:
            start = i
        elif value != 1 and start is not None:
            segments.append((start, i))
            start = None
    if start is not None:
        segments.append((start, len(arr)))
    return segments


def interval_survival_loss(logits: torch.Tensor, labels: torch.Tensor, te_class_weight: float) -> torch.Tensor:
    """Interval-level true-retention objective.

    Unlike the prior token-level retention proxy, this loss gives each true TE
    interval its own survival term. A true interval is penalized if its mean or
    soft-max positive probability is low, directly targeting missed_true_rate.
    """
    probs = torch.softmax(logits, dim=-1)[..., 1]
    known = labels >= 0
    if known.sum() == 0:
        return logits.sum() * 0.0
    weight = torch.tensor([1.0, te_class_weight], device=logits.device)
    ce = F.cross_entropy(logits.reshape(-1, 2), labels.reshape(-1), weight=weight, ignore_index=-100)
    boundary = transition_boundary_loss(probs, labels)
    survival_terms = []
    valley_terms = []
    beta = 8.0
    for i in range(labels.shape[0]):
        for start, end in true_segments_from_labels(labels[i]):
            seg = probs[i, start:end]
            if seg.numel() == 0:
                continue
            mean_survival = seg.mean().clamp(1e-4, 1 - 1e-4)
            soft_peak = (torch.logsumexp(beta * seg, dim=0) / beta).clamp(1e-4, 1 - 1e-4)
            survival_terms.append(-torch.log(mean_survival))
            survival_terms.append(-torch.log(soft_peak))
            valley_terms.append(((1.0 - seg) ** 2).mean())
    if survival_terms:
        survival = torch.stack(survival_terms).mean()
        valley = torch.stack(valley_terms).mean()
    else:
        survival = logits.sum() * 0.0
        valley = logits.sum() * 0.0
    # Keep false jitter weakly penalized but let true intervals survive first.
    if probs.shape[1] >= 2:
        trans_mass = torch.abs(probs[:, 1:] - probs[:, :-1])
        true_trans = (labels[:, 1:] != labels[:, :-1]) & (labels[:, 1:] >= 0) & (labels[:, :-1] >= 0)
        false_jitter = trans_mass[~true_trans].mean() if (~true_trans).any() else trans_mass.mean()
    else:
        false_jitter = logits.sum() * 0.0
    return 0.35 * ce + 0.85 * survival + 0.35 * valley + 0.20 * boundary + 0.08 * false_jitter


def retention_constrained_interval_loss(logits: torch.Tensor, labels: torch.Tensor, te_class_weight: float) -> torch.Tensor:
    """Cost-sensitive interval retention objective.

    The prior interval-survival loss improved segment/boundary metrics but still
    deleted too many true-backed fragments. This version treats low-confidence
    valleys inside true TE intervals as a first-class loss and keeps CE dominant
    enough to preserve the original bp evidence.
    """
    probs = torch.softmax(logits, dim=-1)[..., 1]
    known = labels >= 0
    if known.sum() == 0:
        return logits.sum() * 0.0
    weight = torch.tensor([1.0, te_class_weight], device=logits.device)
    ce = F.cross_entropy(logits.reshape(-1, 2), labels.reshape(-1), weight=weight, ignore_index=-100)
    pos = labels == 1
    neg = labels == 0
    positive_ce = F.binary_cross_entropy(
        probs[pos].clamp(1e-4, 1 - 1e-4),
        torch.ones_like(probs[pos]),
        reduction="mean",
    ) if pos.any() else logits.sum() * 0.0
    negative_bce = F.binary_cross_entropy(
        probs[neg].clamp(1e-4, 1 - 1e-4),
        torch.zeros_like(probs[neg]),
        reduction="mean",
    ) if neg.any() else logits.sum() * 0.0
    survival_terms = []
    valley_terms = []
    floor_terms = []
    beta = 10.0
    for i in range(labels.shape[0]):
        for start, end in true_segments_from_labels(labels[i]):
            seg = probs[i, start:end]
            if seg.numel() == 0:
                continue
            mean_survival = seg.mean().clamp(1e-4, 1 - 1e-4)
            soft_floor = (-torch.logsumexp(-beta * seg, dim=0) / beta).clamp(1e-4, 1 - 1e-4)
            survival_terms.append(-torch.log(mean_survival))
            valley_terms.append(((1.0 - seg) ** 2).mean())
            floor_terms.append(F.relu(0.45 - soft_floor) ** 2)
            floor_terms.append(F.relu(0.62 - mean_survival) ** 2)
    if survival_terms:
        interval_survival = torch.stack(survival_terms).mean()
        valley = torch.stack(valley_terms).mean()
        floor = torch.stack(floor_terms).mean()
    else:
        interval_survival = logits.sum() * 0.0
        valley = logits.sum() * 0.0
        floor = logits.sum() * 0.0
    boundary = transition_boundary_loss(probs, labels)
    return (
        0.70 * ce
        + 0.80 * positive_ce
        + 0.15 * negative_bce
        + 0.80 * interval_survival
        + 0.55 * valley
        + 1.25 * floor
        + 0.08 * boundary
    )


def segment_labels_from_batch(labels: torch.Tensor) -> list[np.ndarray]:
    out = []
    for row in labels.cpu().numpy():
        keep = row >= 0
        out.append(row[keep].astype(np.int8))
    return out


def segment_aware_rescue_decode(prob: np.ndarray, smooth_penalty: float, raw_threshold: float, rescue_threshold: float, min_rescue_len: int) -> np.ndarray:
    """Segment-aware decode: structured smoothing plus high-confidence island rescue.

    This is not a threshold/gap sweep. The smoothed path is the structured
    decoder output; the rescue step is a conservative true-retention guard that
    keeps candidate intervals whose raw evidence would otherwise be erased.
    """
    smooth = viterbi_smooth(prob, smooth_penalty).astype(bool)
    raw = prob >= raw_threshold
    out = smooth.copy()
    for start, end in runs_from_bool(raw.astype(bool)):
        if end - start < min_rescue_len and float(prob[start:end].mean()) < rescue_threshold:
            continue
        overlaps = out[start:end].any()
        if not overlaps and float(prob[start:end].mean()) >= rescue_threshold:
            out[start:end] = True
    return out


def retention_constrained_decode(prob: np.ndarray, smooth_penalty: float, raw_threshold: float, rescue_threshold: float, min_rescue_len: int) -> np.ndarray:
    """Structured decode with a raw-evidence veto against deleting candidate TE islands."""
    smooth = viterbi_smooth(prob, max(0.5, smooth_penalty * 0.5)).astype(bool)
    raw = prob >= raw_threshold
    out = smooth.copy()
    for start, end in runs_from_bool(raw.astype(bool)):
        length = end - start
        mean_prob = float(prob[start:end].mean())
        max_prob = float(prob[start:end].max())
        if length >= min_rescue_len or mean_prob >= raw_threshold or max_prob >= rescue_threshold:
            out[start:end] = True
    return out


def train_variant(args, variant: str, device: torch.device) -> tuple[nn.Module, MarkovDecoder | None, dict]:
    model, tokenizer, meta = load_trained_model(args.init_model_dir)
    model.to(device)
    model.train()
    if args.freeze_backbone:
        for name, p in model.named_parameters():
            if "classifier" not in name:
                p.requires_grad = False
    decoder = MarkovDecoder("hmm" if variant == "joint_hmm" else "crf").to(device) if variant in {"joint_hmm", "joint_crf"} else None
    train_base = WindowDataset(
        str(Path(args.data_dir) / "train/data.jsonl.gz"),
        tokenizer,
        args.window,
        meta["token_label_mode"],
        args.max_train_samples,
    )
    train_ds = LimitedDataset(train_base, args.max_train_samples)
    loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    params = list(p for p in model.parameters() if p.requires_grad)
    if decoder is not None:
        params += list(decoder.parameters())
    opt = torch.optim.AdamW(params, lr=args.learning_rate, weight_decay=0.01)
    step = 0
    losses = []
    for _epoch in range(args.epochs):
        for batch in loader:
            step += 1
            batch = {k: v.to(device) for k, v in batch.items()}
            labels = batch.pop("labels")
            outputs = model(**batch)
            logits = outputs.logits
            if variant == "ce_baseline":
                weight = torch.tensor([1.0, args.te_class_weight], device=device)
                loss = F.cross_entropy(logits.reshape(-1, 2), labels.reshape(-1), weight=weight, ignore_index=-100)
            elif variant in {"joint_hmm", "joint_crf"}:
                loss = decoder.loss(logits, labels)
            elif variant == "joint_semimarkov_proxy":
                loss = soft_fragment_loss(logits, labels)
            elif variant == "boundary_aux":
                loss = boundary_aux_loss(logits, labels, args.te_class_weight)
            elif variant == "semimarkov_retention":
                loss = semimarkov_retention_loss(logits, labels, args.te_class_weight)
            elif variant in {"interval_survival_raw", "interval_survival_decoder"}:
                loss = interval_survival_loss(logits, labels, args.te_class_weight)
            elif variant in {"retention_constrained_raw", "retention_constrained_decoder"}:
                loss = retention_constrained_interval_loss(logits, labels, args.te_class_weight)
            else:
                raise ValueError(variant)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            losses.append(float(loss.detach().cpu()))
            if step >= args.max_steps:
                break
        if step >= args.max_steps:
            break
    return model, decoder, {"train_steps": step, "mean_train_loss": float(np.mean(losses)) if losses else math.nan, "token_label_mode": meta["token_label_mode"]}


def predict_records(args, model: nn.Module, decoder: MarkovDecoder | None, variant: str, device: torch.device, split: str) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    model.to(device)
    meta = json.loads(Path(args.init_model_dir, "training_meta.json").read_text())
    best = Path(args.init_model_dir) / "best_model"
    tokenizer = load_tokenizer(str(best) if (best / "tokenizer_config.json").exists() else meta["model_path"])
    ds = WindowDataset(
        str(Path(args.data_dir) / split / "data.jsonl.gz"),
        tokenizer,
        args.window,
        meta["token_label_mode"],
        args.max_eval_samples,
    )
    loader = DataLoader(ds, batch_size=1, shuffle=False)
    truth_parts: list[np.ndarray] = []
    pred_parts: list[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            labels = batch.pop("labels")
            logits = model(**batch).logits
            y_list = segment_labels_from_batch(labels)
            if variant in {"joint_hmm", "joint_crf"} and decoder is not None:
                pred = decoder.decode_one(logits[0].detach(), labels[0].detach())
            else:
                keep = labels[0].detach().cpu().numpy() >= 0
                prob = torch.softmax(logits[0].detach().cpu(), dim=-1).numpy()[:, 1][keep]
                if variant == "interval_survival_decoder":
                    pred = segment_aware_rescue_decode(prob, args.smooth_penalty, args.threshold, args.rescue_threshold, args.min_rescue_len)
                elif variant == "retention_constrained_decoder":
                    pred = retention_constrained_decode(prob, args.smooth_penalty, args.threshold, args.rescue_threshold, args.min_rescue_len)
                elif variant in {"joint_semimarkov_proxy", "semimarkov_retention"}:
                    pred = viterbi_smooth(prob, 2.0)
                else:
                    pred = prob >= args.threshold
            truth_parts.append(y_list[0])
            pred_parts.append(np.asarray(pred, dtype=bool))
    return np.concatenate(truth_parts), np.concatenate(pred_parts)


def deleted_fragment_diagnostics(truth: np.ndarray, baseline_pred: np.ndarray | None, pred: np.ndarray) -> dict:
    if baseline_pred is None:
        return {
            "deleted_baseline_fragments": 0,
            "deleted_true_backed_fragments": 0,
            "deleted_false_fragments": 0,
            "deleted_true_backed_fraction": 0.0,
        }
    true_seg = runs_from_bool(truth.astype(bool))
    base_seg = runs_from_bool(baseline_pred.astype(bool))
    cur_seg = runs_from_bool(pred.astype(bool))
    deleted = []
    cur_idx = 0
    for seg in base_seg:
        while cur_idx < len(cur_seg) and cur_seg[cur_idx][1] <= seg[0]:
            cur_idx += 1
        overlaps_current = False
        j = cur_idx
        while j < len(cur_seg):
            if cur_seg[j][0] >= seg[1]:
                break
            if min(cur_seg[j][1], seg[1]) > max(cur_seg[j][0], seg[0]):
                overlaps_current = True
                break
            j += 1
        if not overlaps_current:
            deleted.append(seg)
    true_backed = 0
    true_idx = 0
    for seg in deleted:
        while true_idx < len(true_seg) and true_seg[true_idx][1] <= seg[0]:
            true_idx += 1
        _, pred_frac = best_overlap_local(seg, true_seg, true_idx)
        if pred_frac >= 0.5:
            true_backed += 1
    false_deleted = len(deleted) - true_backed
    return {
        "deleted_baseline_fragments": len(deleted),
        "deleted_true_backed_fragments": true_backed,
        "deleted_false_fragments": false_deleted,
        "deleted_true_backed_fraction": true_backed / len(deleted) if deleted else 0.0,
    }


def best_overlap_local(pred: tuple[int, int], true_seg: list[tuple[int, int]], start_idx: int = 0) -> tuple[float, float]:
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


def eval_prediction(truth: np.ndarray, pred: np.ndarray, variant: str, split: str, info: dict, args, baseline_pred: np.ndarray | None = None) -> dict:
    known = truth >= 0
    y = truth == 1
    p = pred.astype(bool)
    row = {"variant": variant, "split": split, "iou_threshold": args.iou_threshold, "boundary_tol_bp": args.boundary_tol_bp}
    row.update(info)
    row.update(binary_metrics(y[known], p[known].astype(np.float32), 0.5))
    row.update(strict_segment_metrics(y, p, args.iou_threshold, args.boundary_tol_bp))
    row.update(fragmentation_truth_diagnostics(y, p))
    row.update(deleted_fragment_diagnostics(y, baseline_pred, p))
    row["true_segments"] = len(runs_from_bool(y))
    row["pred_segments"] = len(runs_from_bool(p))
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init-model-dir", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-train-samples", type=int, default=96)
    ap.add_argument("--max-eval-samples", type=int, default=40)
    ap.add_argument("--max-steps", type=int, default=40)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--learning-rate", type=float, default=2e-5)
    ap.add_argument("--te-class-weight", type=float, default=3.0)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--rescue-threshold", type=float, default=0.65)
    ap.add_argument("--min-rescue-len", type=int, default=8)
    ap.add_argument("--smooth-penalty", type=float, default=2.0)
    ap.add_argument("--max-deleted-true-backed-fraction", type=float, default=0.15)
    ap.add_argument("--iou-threshold", type=float, default=0.8)
    ap.add_argument("--boundary-tol-bp", type=int, default=5)
    ap.add_argument("--variant-set", choices=["legacy", "interval_survival", "retention_constrained"], default="legacy")
    ap.add_argument("--freeze-backbone", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    if args.variant_set == "legacy":
        variants = ["ce_baseline", "joint_hmm", "joint_crf", "joint_semimarkov_proxy", "boundary_aux", "semimarkov_retention"]
    elif args.variant_set == "interval_survival":
        variants = ["ce_baseline", "interval_survival_raw", "interval_survival_decoder"]
    else:
        variants = ["ce_baseline", "retention_constrained_raw", "retention_constrained_decoder"]
    variant_predictions: dict[tuple[str, str], tuple[np.ndarray, np.ndarray, dict]] = {}
    status = {
        "ok": False,
        "seed": args.seed,
        "device": str(device),
        "init_model_dir": args.init_model_dir,
        "data_dir": args.data_dir,
        "variants": variants,
        "freeze_backbone": args.freeze_backbone,
    }
    for variant in variants:
        model, decoder, info = train_variant(args, variant, device)
        for split in ["val", "test"]:
            truth, pred = predict_records(args, model, decoder, variant, device, split)
            variant_predictions[(variant, split)] = (truth, pred, info)
        del model, decoder
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    rows: list[dict] = []
    for split in ["val", "test"]:
        baseline = variant_predictions.get(("ce_baseline", split))
        baseline_pred = baseline[1] if baseline is not None else None
        for variant in variants:
            truth, pred, info = variant_predictions[(variant, split)]
            rows.append(eval_prediction(truth, pred, variant, split, info, args, baseline_pred))
    metrics = out_dir / "joint_structured_decoder_metrics.tsv"
    write_tsv(metrics, rows)
    ce_test = [r for r in rows if r["split"] == "test" and r["variant"] == "ce_baseline"][0]
    test_rows = [r for r in rows if r["split"] == "test"]
    eligible = [
        r for r in test_rows
        if r["variant"] != "ce_baseline"
        and r["segment_f1"] > ce_test["segment_f1"]
        and r["boundary_f1"] > ce_test["boundary_f1"]
        and r["missed_true_rate"] <= ce_test["missed_true_rate"] + 0.03
        and r["deleted_true_backed_fraction"] <= args.max_deleted_true_backed_fraction
    ]
    best = max(test_rows, key=lambda r: r["segment_f1"])
    best_gate = max(eligible, key=lambda r: r["segment_f1"]) if eligible else None
    gate_pass = (
        best_gate is not None
    )
    status.update({
        "ok": True,
        "metrics": str(metrics),
        "best_test_variant": best["variant"],
        "best_test_segment_f1": best["segment_f1"],
        "best_test_boundary_f1": best["boundary_f1"],
        "best_test_missed_true_rate": best["missed_true_rate"],
        "best_gate_variant": best_gate["variant"] if best_gate else "",
        "best_gate_segment_f1": best_gate["segment_f1"] if best_gate else 0.0,
        "best_gate_boundary_f1": best_gate["boundary_f1"] if best_gate else 0.0,
        "best_gate_missed_true_rate": best_gate["missed_true_rate"] if best_gate else 1.0,
        "ce_test_segment_f1": ce_test["segment_f1"],
        "ce_test_boundary_f1": ce_test["boundary_f1"],
        "ce_test_missed_true_rate": ce_test["missed_true_rate"],
        "max_deleted_true_backed_fraction": args.max_deleted_true_backed_fraction,
        "best_gate_deleted_true_backed_fraction": best_gate["deleted_true_backed_fraction"] if best_gate else 1.0,
        "promotion_gate_pass": bool(gate_pass),
    })
    (out_dir / "joint_structured_decoder_status.json").write_text(json.dumps(status, indent=2) + "\n")
    report = [
        "# Joint Structured Decoder Smoke",
        "",
        f"- Seed: `{args.seed}`",
        f"- Init model: `{args.init_model_dir}`",
        f"- Data: `{args.data_dir}`",
        f"- Best test variant: `{best['variant']}` segment-F1 `{best['segment_f1']:.4f}`, boundary-F1 `{best['boundary_f1']:.4f}`, missed_true_rate `{best['missed_true_rate']:.4f}`",
        f"- Best gate-eligible variant: `{best_gate['variant'] if best_gate else 'none'}`",
        f"- CE test baseline: segment-F1 `{ce_test['segment_f1']:.4f}`, boundary-F1 `{ce_test['boundary_f1']:.4f}`, missed_true_rate `{ce_test['missed_true_rate']:.4f}`",
        f"- Promotion gate pass: `{bool(gate_pass)}`",
        "",
        "This is a bounded single-seed smoke. It tests structured losses attached to model logits during fine-tuning, not post-hoc smoothing alone.",
        "The retention variant directly penalizes missed true TE bases; deleted-fragment diagnostics compare each variant against the CE baseline to distinguish false-fragment removal from true-backed fragment deletion.",
    ]
    (out_dir / "JOINT_STRUCTURED_DECODER_REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
