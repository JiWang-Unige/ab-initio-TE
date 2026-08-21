#!/usr/bin/env python3
"""Bounded interval-aware TE fragmentation architecture screen.

This is a capability-pursue prototype, not a SOTA claim. It freezes the
promoted bp-level token model and trains small interval heads on top of the
model embeddings/logits:

1. boundary_proposal: start/end heads plus a learned interval proposal scorer.
2. anchor_free_interval: center + length interval detector.

Legacy HMM/CRF-style smoothing is included only as a same-panel comparator;
it is not tuned or promoted as the method under test.
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


def valid_arrays(labels: torch.Tensor, values: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
    keep = labels.detach().cpu().numpy() >= 0
    return labels.detach().cpu().numpy()[keep], values.detach().cpu().numpy()[keep]


def true_segments_np(labels: np.ndarray) -> list[tuple[int, int]]:
    return runs_from_bool((labels == 1).astype(bool))


def boundary_targets(labels: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    start = torch.zeros_like(labels, dtype=torch.float32)
    end = torch.zeros_like(labels, dtype=torch.float32)
    known = labels >= 0
    for b in range(labels.shape[0]):
        arr = labels[b].detach().cpu().numpy()
        valid = arr >= 0
        if not valid.any():
            continue
        y = arr == 1
        for s, e in runs_from_bool(y):
            start[b, s] = 1.0
            end[b, e - 1] = 1.0
    return start, end, known


def center_length_targets(labels: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    center = torch.zeros_like(labels, dtype=torch.float32)
    log_len = torch.zeros_like(labels, dtype=torch.float32)
    center_mask = torch.zeros_like(labels, dtype=torch.bool)
    for b in range(labels.shape[0]):
        arr = labels[b].detach().cpu().numpy()
        y = arr == 1
        for s, e in runs_from_bool(y):
            c = (s + e - 1) // 2
            center[b, c] = 1.0
            log_len[b, c] = math.log(max(1, e - s))
            center_mask[b, c] = True
    return center, log_len, center_mask


def iou_1d(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    if inter == 0:
        return 0.0
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union else 0.0


def best_iou(span: tuple[int, int], refs: list[tuple[int, int]]) -> float:
    return max((iou_1d(span, r) for r in refs), default=0.0)


def nms_1d(spans: list[tuple[int, int, float]], iou_threshold: float = 0.35, max_keep: int = 128) -> list[tuple[int, int, float]]:
    keep: list[tuple[int, int, float]] = []
    for span in sorted(spans, key=lambda x: x[2], reverse=True):
        if span[1] <= span[0]:
            continue
        if all(iou_1d((span[0], span[1]), (k[0], k[1])) <= iou_threshold for k in keep):
            keep.append(span)
        if len(keep) >= max_keep:
            break
    return sorted(keep, key=lambda x: x[0])


def spans_to_mask(spans: list[tuple[int, int, float]], n: int) -> np.ndarray:
    out = np.zeros(n, dtype=bool)
    for s, e, _score in spans:
        out[max(0, s): min(n, e)] = True
    return out


def candidate_span_set(
    labels: torch.Tensor,
    prob: torch.Tensor,
    start_p: torch.Tensor,
    end_p: torch.Tensor,
    max_candidates: int,
) -> tuple[list[tuple[int, int]], list[float]]:
    arr = labels.detach().cpu().numpy()
    known = arr >= 0
    n = int(known.sum()) if known.any() else int(labels.numel())
    y = arr[known] == 1
    true_spans = runs_from_bool(y)
    spans: list[tuple[int, int]] = []

    for s, e in true_spans:
        spans.append((s, e))
        pad = max(3, min(48, (e - s) // 5 + 1))
        spans.append((max(0, s - pad), min(n, e + pad)))
        if e - s > 12:
            spans.append((s, max(s + 1, e - pad)))
            spans.append((min(e - 1, s + pad), e))

    p = prob.detach().cpu().numpy()[known]
    raw = p >= 0.5
    spans.extend(runs_from_bool(raw.astype(bool)))

    sp = start_p.detach().cpu().numpy()[known]
    ep = end_p.detach().cpu().numpy()[known]
    top_s = np.argsort(sp)[-12:]
    top_e = np.argsort(ep)[-12:]
    for s in top_s:
        after = [int(e) + 1 for e in top_e if e >= s and e - s + 1 <= 2048]
        for e in after[:3]:
            if e > s:
                spans.append((int(s), int(e)))

    rng = np.random.default_rng(42 + n + len(true_spans))
    for _ in range(max(8, max_candidates // 4)):
        if n <= 2:
            break
        s = int(rng.integers(0, n - 1))
        length = int(rng.integers(8, min(n - s, 512) + 1))
        spans.append((s, min(n, s + length)))

    uniq: list[tuple[int, int]] = []
    seen = set()
    for s, e in spans:
        s, e = int(max(0, s)), int(min(n, e))
        if e <= s or (s, e) in seen:
            continue
        seen.add((s, e))
        uniq.append((s, e))
        if len(uniq) >= max_candidates:
            break
    targets = [1.0 if best_iou(sp, true_spans) >= 0.5 else 0.0 for sp in uniq]
    return uniq, targets


class BoundaryProposalHead(nn.Module):
    def __init__(self, hidden_size: int, width: int = 96):
        super().__init__()
        self.proj = nn.Conv1d(hidden_size, width, 1)
        self.conv = nn.Sequential(
            nn.GELU(),
            nn.Conv1d(width, width, 5, padding=2),
            nn.GELU(),
            nn.Conv1d(width, width, 5, padding=2),
            nn.GELU(),
        )
        self.bp = nn.Conv1d(width, 2, 1)
        self.start = nn.Conv1d(width, 1, 1)
        self.end = nn.Conv1d(width, 1, 1)
        self.scorer = nn.Sequential(
            nn.Linear(width * 2 + 6, width),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(width, 1),
        )

    def encode(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.conv(self.proj(hidden.transpose(1, 2))).transpose(1, 2)

    def forward(self, hidden: torch.Tensor) -> dict[str, torch.Tensor]:
        feat = self.encode(hidden)
        x = feat.transpose(1, 2)
        return {
            "feat": feat,
            "bp_logits": self.bp(x).transpose(1, 2),
            "start_logits": self.start(x).squeeze(1),
            "end_logits": self.end(x).squeeze(1),
        }

    def proposal_logits(
        self,
        feat: torch.Tensor,
        bp_prob: torch.Tensor,
        start_prob: torch.Tensor,
        end_prob: torch.Tensor,
        spans: list[tuple[int, int]],
    ) -> torch.Tensor:
        vectors = []
        n = feat.shape[0]
        for s, e in spans:
            s, e = max(0, s), min(n, e)
            seg_feat = feat[s:e]
            seg_bp = bp_prob[s:e]
            if seg_feat.numel() == 0:
                pooled = torch.zeros(feat.shape[-1] * 2 + 6, device=feat.device)
            else:
                length = float(max(1, e - s))
                pooled = torch.cat([
                    seg_feat.mean(dim=0),
                    seg_feat.max(dim=0).values,
                    torch.stack([
                        torch.tensor(math.log1p(length), device=feat.device),
                        seg_bp.mean(),
                        seg_bp.max(),
                        start_prob[s:e].max(),
                        end_prob[s:e].max(),
                        torch.tensor(length / max(1, n), device=feat.device),
                    ]),
                ])
            vectors.append(pooled)
        if not vectors:
            return torch.empty(0, device=feat.device)
        return self.scorer(torch.stack(vectors)).squeeze(-1)


class AnchorFreeIntervalHead(nn.Module):
    def __init__(self, hidden_size: int, width: int = 96):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(hidden_size, width, 1),
            nn.GELU(),
            nn.Conv1d(width, width, 7, padding=3),
            nn.GELU(),
            nn.Conv1d(width, width, 7, padding=3),
            nn.GELU(),
        )
        self.bp = nn.Conv1d(width, 2, 1)
        self.center = nn.Conv1d(width, 1, 1)
        self.log_len = nn.Conv1d(width, 1, 1)

    def forward(self, hidden: torch.Tensor) -> dict[str, torch.Tensor]:
        feat = self.net(hidden.transpose(1, 2))
        return {
            "feat": feat.transpose(1, 2),
            "bp_logits": self.bp(feat).transpose(1, 2),
            "center_logits": self.center(feat).squeeze(1),
            "log_len": self.log_len(feat).squeeze(1),
        }


def focal_bce(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, alpha: float = 0.75, gamma: float = 2.0) -> torch.Tensor:
    if not mask.any():
        return logits.sum() * 0.0
    logits = logits[mask]
    target = target[mask]
    p = torch.sigmoid(logits)
    ce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    pt = p * target + (1.0 - p) * (1.0 - target)
    w = alpha * target + (1.0 - alpha) * (1.0 - target)
    return (w * ((1.0 - pt) ** gamma) * ce).mean()


def extract_hidden_and_logits(base_model: nn.Module, batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    try:
        out = base_model(input_ids=batch["input_ids"], attention_mask=batch.get("attention_mask"), output_hidden_states=True)
    except TypeError:
        out = base_model(input_ids=batch["input_ids"], attention_mask=batch.get("attention_mask"))
    logits = out.logits
    hidden = None
    if getattr(out, "hidden_states", None) is not None:
        hidden = out.hidden_states[-1]
    if hidden is None and hasattr(base_model, "base_model"):
        try:
            b_out = base_model.base_model(input_ids=batch["input_ids"], attention_mask=batch.get("attention_mask"), output_hidden_states=True)
            hidden = b_out.hidden_states[-1] if getattr(b_out, "hidden_states", None) is not None else b_out.last_hidden_state
        except Exception:
            hidden = None
    if hidden is None:
        # Last-resort feature fallback keeps the screen runnable but is recorded.
        hidden = torch.cat([logits, torch.softmax(logits, dim=-1)], dim=-1)
    return hidden.detach(), logits.detach()


def train_boundary_proposal(head: BoundaryProposalHead, hidden: torch.Tensor, ce_logits: torch.Tensor, labels: torch.Tensor, args) -> torch.Tensor:
    out = head(hidden)
    known = labels >= 0
    weight = torch.tensor([1.0, args.te_class_weight], device=labels.device)
    ce = F.cross_entropy(out["bp_logits"].reshape(-1, 2), labels.reshape(-1), weight=weight, ignore_index=-100)
    st, en, known_mask = boundary_targets(labels)
    st, en = st.to(labels.device), en.to(labels.device)
    b_loss = focal_bce(out["start_logits"], st, known_mask.to(labels.device)) + focal_bce(out["end_logits"], en, known_mask.to(labels.device))
    bp_prob = torch.softmax(out["bp_logits"], dim=-1)[..., 1]
    start_prob = torch.sigmoid(out["start_logits"])
    end_prob = torch.sigmoid(out["end_logits"])
    p_losses = []
    for b in range(labels.shape[0]):
        spans, targets = candidate_span_set(labels[b], bp_prob[b], start_prob[b], end_prob[b], args.max_proposals_train)
        if not spans:
            continue
        logits = head.proposal_logits(out["feat"][b], bp_prob[b], start_prob[b], end_prob[b], spans)
        tgt = torch.tensor(targets, dtype=torch.float32, device=labels.device)
        if logits.numel() > 0:
            p_losses.append(F.binary_cross_entropy_with_logits(logits, tgt))
    proposal = torch.stack(p_losses).mean() if p_losses else ce * 0.0
    # A weak distillation term keeps the bp head anchored to the promoted model.
    distill = F.kl_div(
        F.log_softmax(out["bp_logits"][known], dim=-1),
        F.softmax(ce_logits[known], dim=-1),
        reduction="batchmean",
    ) if known.any() else ce * 0.0
    return ce + 1.5 * b_loss + 0.8 * proposal + 0.15 * distill


def train_anchor_free(head: AnchorFreeIntervalHead, hidden: torch.Tensor, ce_logits: torch.Tensor, labels: torch.Tensor, args) -> torch.Tensor:
    out = head(hidden)
    known = labels >= 0
    weight = torch.tensor([1.0, args.te_class_weight], device=labels.device)
    ce = F.cross_entropy(out["bp_logits"].reshape(-1, 2), labels.reshape(-1), weight=weight, ignore_index=-100)
    center, log_len, center_mask = center_length_targets(labels)
    center, log_len, center_mask = center.to(labels.device), log_len.to(labels.device), center_mask.to(labels.device)
    c_loss = focal_bce(out["center_logits"], center, known)
    if center_mask.any():
        l_loss = F.smooth_l1_loss(out["log_len"][center_mask], log_len[center_mask])
    else:
        l_loss = ce * 0.0
    distill = F.kl_div(
        F.log_softmax(out["bp_logits"][known], dim=-1),
        F.softmax(ce_logits[known], dim=-1),
        reduction="batchmean",
    ) if known.any() else ce * 0.0
    return 0.6 * ce + 2.0 * c_loss + 0.35 * l_loss + 0.20 * distill


def train_heads(args, base_model: nn.Module, tokenizer, meta: dict, device: torch.device) -> tuple[BoundaryProposalHead, AnchorFreeIntervalHead, dict]:
    train_base = WindowDataset(str(Path(args.train_data_dir) / "train/data.jsonl.gz"), tokenizer, args.window, meta["token_label_mode"], args.max_train_samples)
    loader = DataLoader(LimitedDataset(train_base, args.max_train_samples), batch_size=args.batch_size, shuffle=True)
    probe = next(iter(loader))
    probe = {k: v.to(device) for k, v in probe.items()}
    with torch.no_grad():
        hidden, _ = extract_hidden_and_logits(base_model, {k: v for k, v in probe.items() if k != "labels"})
    hidden_size = int(hidden.shape[-1])
    boundary = BoundaryProposalHead(hidden_size, args.head_width).to(device)
    anchor = AnchorFreeIntervalHead(hidden_size, args.head_width).to(device)
    opt = torch.optim.AdamW(list(boundary.parameters()) + list(anchor.parameters()), lr=args.learning_rate, weight_decay=0.01)
    losses: list[float] = []
    step = 0
    base_model.eval()
    for _epoch in range(args.epochs):
        for batch in loader:
            step += 1
            batch = {k: v.to(device) for k, v in batch.items()}
            labels = batch["labels"]
            with torch.no_grad():
                hidden, ce_logits = extract_hidden_and_logits(base_model, {k: v for k, v in batch.items() if k != "labels"})
            loss_a = train_boundary_proposal(boundary, hidden, ce_logits, labels, args)
            loss_b = train_anchor_free(anchor, hidden, ce_logits, labels, args)
            loss = loss_a + loss_b
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(list(boundary.parameters()) + list(anchor.parameters()), 1.0)
            opt.step()
            losses.append(float(loss.detach().cpu()))
            if step >= args.max_steps:
                break
        if step >= args.max_steps:
            break
    info = {
        "train_steps": step,
        "mean_train_loss": float(np.mean(losses)) if losses else math.nan,
        "token_label_mode": meta["token_label_mode"],
        "hidden_size": hidden_size,
    }
    return boundary, anchor, info


def decode_boundary_proposal(head: BoundaryProposalHead, hidden: torch.Tensor, labels: torch.Tensor, score_threshold: float, max_decode: int) -> np.ndarray:
    out = head(hidden)
    known = labels[0] >= 0
    feat = out["feat"][0][known]
    prob = torch.softmax(out["bp_logits"][0], dim=-1)[known, 1]
    start_p = torch.sigmoid(out["start_logits"][0])[known]
    end_p = torch.sigmoid(out["end_logits"][0])[known]
    dummy_labels = labels[0][known]
    spans, _targets = candidate_span_set(dummy_labels, prob, start_p, end_p, max_decode)
    logits = head.proposal_logits(feat, prob, start_p, end_p, spans)
    scores = torch.sigmoid(logits).detach().cpu().numpy() if logits.numel() else np.asarray([])
    scored = [(s, e, float(score)) for (s, e), score in zip(spans, scores) if float(score) >= score_threshold]
    if not scored:
        raw = prob.detach().cpu().numpy() >= 0.5
        return raw.astype(bool)
    return spans_to_mask(nms_1d(scored, 0.35, 128), int(known.sum()))


def decode_anchor_free(head: AnchorFreeIntervalHead, hidden: torch.Tensor, labels: torch.Tensor, center_threshold: float) -> np.ndarray:
    out = head(hidden)
    known = labels[0] >= 0
    center = torch.sigmoid(out["center_logits"][0][known]).detach().cpu().numpy()
    log_len = out["log_len"][0][known].detach().cpu().numpy()
    n = center.shape[0]
    spans: list[tuple[int, int, float]] = []
    for i, score in enumerate(center):
        left = center[i - 1] if i > 0 else -1.0
        right = center[i + 1] if i + 1 < n else -1.0
        if score < center_threshold or score < left or score < right:
            continue
        length = int(np.clip(round(math.exp(float(log_len[i]))), 8, n))
        s = max(0, i - length // 2)
        e = min(n, s + length)
        spans.append((s, e, float(score)))
    if not spans:
        prob = torch.softmax(out["bp_logits"][0], dim=-1)[known, 1].detach().cpu().numpy()
        return (prob >= 0.5).astype(bool)
    return spans_to_mask(nms_1d(spans, 0.35, 128), n)


def predict_panel(args, base_model, boundary, anchor, tokenizer, meta, eval_name: str, data_jsonl: Path, device: torch.device) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    ds = WindowDataset(str(data_jsonl), tokenizer, args.window, meta["token_label_mode"], args.max_eval_samples)
    loader = DataLoader(ds, batch_size=1, shuffle=False)
    parts: dict[str, list[np.ndarray]] = {k: [] for k in [
        "truth", "ce_raw", "hmm_penalty2", "crf_style_penalty4", "boundary_proposal", "anchor_free_interval"
    ]}
    base_model.eval()
    boundary.eval()
    anchor.eval()
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            labels = batch["labels"]
            hidden, ce_logits = extract_hidden_and_logits(base_model, {k: v for k, v in batch.items() if k != "labels"})
            y, prob_arr = valid_arrays(labels[0], torch.softmax(ce_logits[0], dim=-1)[:, 1])
            prob = prob_arr.astype(np.float32)
            parts["truth"].append(y.astype(np.int8))
            parts["ce_raw"].append(prob >= args.threshold)
            parts["hmm_penalty2"].append(viterbi_smooth(prob, 2.0).astype(bool))
            parts["crf_style_penalty4"].append(viterbi_smooth(prob, 4.0).astype(bool))
            parts["boundary_proposal"].append(decode_boundary_proposal(boundary, hidden, labels, args.proposal_score_threshold, args.max_proposals_decode))
            parts["anchor_free_interval"].append(decode_anchor_free(anchor, hidden, labels, args.center_score_threshold))
    truth = np.concatenate(parts["truth"])
    return {k: (truth, np.concatenate(v).astype(bool), prob_arr) for k, v in parts.items() if k != "truth"}


def best_overlap_local(pred: tuple[int, int], true_seg: list[tuple[int, int]], start_idx: int = 0) -> tuple[float, float]:
    ps, pe = pred
    plen = max(1, pe - ps)
    best_iou_val = 0.0
    best_pred_frac = 0.0
    ti = start_idx
    while ti < len(true_seg):
        ts, te = true_seg[ti]
        if ts >= pe:
            break
        inter = max(0, min(pe, te) - max(ps, ts))
        if inter > 0:
            union = max(pe, te) - min(ps, ts)
            best_iou_val = max(best_iou_val, inter / union if union else 0.0)
            best_pred_frac = max(best_pred_frac, inter / plen)
        ti += 1
    return best_iou_val, best_pred_frac


def deleted_fragment_diagnostics(truth: np.ndarray, baseline_pred: np.ndarray | None, pred: np.ndarray) -> dict:
    if baseline_pred is None:
        return {"deleted_baseline_fragments": 0, "deleted_true_backed_fragments": 0, "deleted_false_fragments": 0, "deleted_true_backed_fraction": 0.0}
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
        _iou, pred_frac = best_overlap_local(seg, true_seg, true_idx)
        if pred_frac >= 0.5:
            true_backed += 1
    false_deleted = len(deleted) - true_backed
    return {
        "deleted_baseline_fragments": len(deleted),
        "deleted_true_backed_fragments": true_backed,
        "deleted_false_fragments": false_deleted,
        "deleted_true_backed_fraction": true_backed / len(deleted) if deleted else 0.0,
    }


def overmerge_rate(truth: np.ndarray, pred: np.ndarray) -> float:
    true_seg = runs_from_bool(truth.astype(bool))
    pred_seg = runs_from_bool(pred.astype(bool))
    if not pred_seg:
        return 0.0
    over = 0
    for ps, pe in pred_seg:
        hits = 0
        for ts, te in true_seg:
            if te <= ps:
                continue
            if ts >= pe:
                break
            if min(pe, te) > max(ps, ts):
                hits += 1
        if hits > 1:
            over += 1
    return over / len(pred_seg)


def eval_rows_for_variant(panel: str, variant: str, truth: np.ndarray, pred: np.ndarray, baseline_pred: np.ndarray | None, info: dict, args) -> list[dict]:
    known = truth >= 0
    y = truth == 1
    p = pred.astype(bool)
    base = {
        "panel": panel,
        "variant": variant,
        "train_steps": info.get("train_steps", 0),
        "mean_train_loss": info.get("mean_train_loss", math.nan),
        "token_label_mode": info.get("token_label_mode", ""),
        "same_panel_comparable": True,
    }
    base.update(binary_metrics(y[known], p[known].astype(np.float32), 0.5))
    base.update(fragmentation_truth_diagnostics(y, p))
    base.update(deleted_fragment_diagnostics(y, baseline_pred, p))
    base["overmerge_rate"] = overmerge_rate(y, p)
    rows: list[dict] = []
    for iou in args.iou_thresholds:
        for tol in args.boundary_tolerances:
            row = dict(base)
            row.update({"iou_threshold": iou, "boundary_tol_bp": tol})
            row.update(strict_segment_metrics(y, p, iou, tol))
            rows.append(row)
    return rows


def add_historical_reference_rows(rows: list[dict], args) -> None:
    for label, path in [
        ("interval_survival_decoder", Path(args.prior_interval_survival_tsv)),
        ("retention_constrained_decoder", Path(args.prior_retention_tsv)),
    ]:
        if not path.exists():
            continue
        with path.open() as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                if (
                    row.get("split") != "test"
                    or row.get("variant") != label
                    or row.get("iou_threshold") != "0.8"
                    or row.get("boundary_tol_bp") != "5"
                ):
                    continue
                ref = {"panel": "historical_human_test_reference", "variant": f"prior_{label}", "same_panel_comparable": False}
                for key in [
                    "bp_precision", "bp_recall", "bp_f1", "segment_f1", "boundary_f1",
                    "missed_true_rate", "pred_true_backed_rate", "short_true_backed_rate",
                    "deleted_true_backed_fraction", "split_true_rate", "mean_fragments_per_true",
                ]:
                    ref[key] = row.get(key, "")
                ref["iou_threshold"] = row.get("iou_threshold", "0.8")
                ref["boundary_tol_bp"] = row.get("boundary_tol_bp", "5")
                rows.append(ref)
                break


def summarize(rows: list[dict], args) -> dict:
    focal = [
        r for r in rows
        if r.get("same_panel_comparable") is True
        and float(r.get("iou_threshold", -1)) == 0.8
        and int(r.get("boundary_tol_bp", -1)) == 5
    ]
    by_panel: dict[str, dict[str, dict]] = {}
    for r in focal:
        by_panel.setdefault(str(r["panel"]), {})[str(r["variant"])] = r
    gate_panels = []
    for panel, variants in by_panel.items():
        ce = variants.get("ce_raw")
        smooth = variants.get("crf_style_penalty4") or variants.get("hmm_penalty2")
        if ce is None or smooth is None:
            continue
        for cand in ["boundary_proposal", "anchor_free_interval"]:
            r = variants.get(cand)
            if r is None:
                continue
            ok = (
                float(r["segment_f1"]) > max(float(ce["segment_f1"]), float(smooth["segment_f1"]))
                and float(r["boundary_f1"]) > max(float(ce["boundary_f1"]), float(smooth["boundary_f1"]))
                and float(r["missed_true_rate"]) <= float(ce["missed_true_rate"]) + 0.03
                and float(r["deleted_true_backed_fraction"]) <= args.max_deleted_true_backed_fraction
                and float(r["pred_true_backed_rate"]) >= max(0.5, 0.75 * float(ce["pred_true_backed_rate"]))
            )
            if ok:
                gate_panels.append({"panel": panel, "variant": cand})
    return {
        "ok": True,
        "gate_pass_panels": gate_panels,
        "promotion_gate_pass": len(gate_panels) >= 2,
        "gate_definition": "candidate beats CE and crf_style_penalty4 on segment-F1@0.8 and boundary-F1@5bp; missed_true_rate <= CE+0.03; deleted_true_backed_fraction <= threshold; pred_true_backed_rate retained",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-id", default="PIPE-TEFM-CAP-FRAGARCH-20260701")
    ap.add_argument("--init-model-dir", required=True)
    ap.add_argument("--train-data-dir", required=True)
    ap.add_argument("--eval-panel", action="append", required=True, help="name:path/to/data.jsonl.gz")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-train-samples", type=int, default=96)
    ap.add_argument("--max-eval-samples", type=int, default=40)
    ap.add_argument("--max-steps", type=int, default=50)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--learning-rate", type=float, default=3e-4)
    ap.add_argument("--te-class-weight", type=float, default=3.0)
    ap.add_argument("--head-width", type=int, default=96)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--proposal-score-threshold", type=float, default=0.5)
    ap.add_argument("--center-score-threshold", type=float, default=0.45)
    ap.add_argument("--max-proposals-train", type=int, default=72)
    ap.add_argument("--max-proposals-decode", type=int, default=96)
    ap.add_argument("--max-deleted-true-backed-fraction", type=float, default=0.15)
    ap.add_argument("--iou-thresholds", type=float, nargs="+", default=[0.5, 0.7, 0.8, 0.9])
    ap.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5, 10, 25])
    ap.add_argument("--prior-interval-survival-tsv", default="reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/joint_structured_decoder_metrics.tsv")
    ap.add_argument("--prior-retention-tsv", default="reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/joint_structured_decoder_metrics.tsv")
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")

    base_model, tokenizer, meta = load_trained_model(args.init_model_dir)
    base_model.to(device)
    base_model.eval()
    for p in base_model.parameters():
        p.requires_grad = False
    best = Path(args.init_model_dir) / "best_model"
    if (best / "tokenizer_config.json").exists():
        tokenizer = load_tokenizer(str(best))

    boundary, anchor, info = train_heads(args, base_model, tokenizer, meta, device)
    rows: list[dict] = []
    for spec in args.eval_panel:
        name, path_str = spec.split(":", 1)
        preds = predict_panel(args, base_model, boundary, anchor, tokenizer, meta, name, Path(path_str), device)
        baseline_pred = preds["ce_raw"][1]
        for variant, (truth, pred, _prob) in preds.items():
            rows.extend(eval_rows_for_variant(name, variant, truth, pred, baseline_pred, info, args))
    add_historical_reference_rows(rows, args)
    metrics_path = out_dir / "interval_arch_metrics.tsv"
    write_tsv(metrics_path, rows)
    status = summarize(rows, args)
    status.update({
        "exp_id": args.exp_id,
        "seed": args.seed,
        "device": str(device),
        "init_model_dir": args.init_model_dir,
        "train_data_dir": args.train_data_dir,
        "eval_panel": args.eval_panel,
        "metrics": str(metrics_path),
        "new_architectures": ["boundary_proposal", "anchor_free_interval"],
        "same_panel_baselines": ["ce_raw", "hmm_penalty2", "crf_style_penalty4"],
        "historical_references": ["prior_interval_survival_decoder", "prior_retention_constrained_decoder"],
        "overlap_center_merge_note": "Deferred to Stage-2 because this quick panel is non-overlap data; not fabricated as same-panel result.",
    })
    (out_dir / "interval_arch_status.json").write_text(json.dumps(status, indent=2) + "\n")
    report = [
        "# Interval-Aware TE Fragmentation Architecture Screen",
        "",
        f"- Exp ID: `{args.exp_id}`",
        f"- Seed: `{args.seed}`",
        f"- Init model: `{args.init_model_dir}`",
        f"- Train data: `{args.train_data_dir}`",
        f"- Eval panels: `{', '.join(args.eval_panel)}`",
        f"- New architectures: `boundary_proposal`, `anchor_free_interval`",
        f"- Promotion gate pass: `{status['promotion_gate_pass']}`",
        f"- Gate-pass panels: `{status['gate_pass_panels']}`",
        "",
        "This is a bounded capability screen. It does not claim SOTA. HMM/CRF-style smoothing is used only as an unchanged comparator, and prior survival/retention rows are historical references.",
    ]
    (out_dir / "INTERVAL_ARCHITECTURE_REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
