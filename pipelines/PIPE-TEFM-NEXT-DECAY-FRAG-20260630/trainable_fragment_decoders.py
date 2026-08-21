#!/usr/bin/env python3
"""Trainable fragmentation decoder smoke on frozen bp-model tracks.

This is a bounded structural screen. It keeps the FM backbone frozen, then trains
small downstream decoders on forward/reverse probability tracks:

- boundary-aware CNN head with an auxiliary transition/boundary loss;
- linear-chain CRF layer trained by sequence NLL;
- duration-prior decoder learned from true interval lengths.

If these beat consensus+CRF under strict interval metrics, the next step is to
integrate the winning objective into backbone fine-tuning.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

THIS = Path("pipelines/PIPE-TEFM-FINAL-GENOMEDECAY-20260630").resolve()
FINAL = Path("pipelines/PIPE-TEFM-FINAL-20260623").resolve()
sys.path.insert(0, str(THIS))
sys.path.insert(0, str(FINAL))

from fragment_sanity_eval import build_tracks  # noqa: E402
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


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p.astype(np.float32), 1e-5, 1.0 - 1e-5)
    return np.log(p / (1.0 - p))


def make_features(prob_modes: dict[str, np.ndarray]) -> np.ndarray:
    fwd = prob_modes["forward"].astype(np.float32)
    rev = prob_modes["reverse"].astype(np.float32)
    mean = prob_modes["mean_logit"].astype(np.float32)
    maxp = prob_modes["max_prob"].astype(np.float32)
    cons = prob_modes["consensus_min"].astype(np.float32)
    agree = 1.0 - np.abs(fwd - rev)
    dens = np.convolve(cons, np.ones(101, dtype=np.float32) / 101.0, mode="same").astype(np.float32)
    return np.stack([fwd, rev, mean, maxp, cons, agree, dens, logit(cons)], axis=1).astype(np.float32)


def chunk_arrays(x: np.ndarray, y: np.ndarray, chunk_len: int) -> list[tuple[np.ndarray, np.ndarray]]:
    chunks = []
    for start in range(0, len(y), chunk_len):
        end = min(len(y), start + chunk_len)
        if end - start >= 64 and np.any(y[start:end] >= 0):
            chunks.append((x[start:end], y[start:end]))
    return chunks


def boundary_targets(y: torch.Tensor) -> torch.Tensor:
    b = torch.zeros_like(y, dtype=torch.float32)
    b[1:] = (y[1:] != y[:-1]).float()
    b[:-1] = torch.maximum(b[:-1], (y[1:] != y[:-1]).float())
    return b


class BoundaryCNN(nn.Module):
    def __init__(self, n_features: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(n_features, 32, kernel_size=9, padding=4),
            nn.ReLU(),
            nn.Conv1d(32, 32, kernel_size=9, padding=4),
            nn.ReLU(),
        )
        self.te_head = nn.Conv1d(32, 1, kernel_size=1)
        self.boundary_head = nn.Conv1d(32, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # x: L x F
        h = self.net(x.T.unsqueeze(0))
        return self.te_head(h).squeeze(), self.boundary_head(h).squeeze()


class LinearCRF(nn.Module):
    def __init__(self, n_features: int):
        super().__init__()
        self.emitter = nn.Linear(n_features, 2)
        self.transitions = nn.Parameter(torch.tensor([[1.5, -1.5], [-1.5, 1.5]], dtype=torch.float32))

    def emissions(self, x: torch.Tensor) -> torch.Tensor:
        return self.emitter(x)

    def nll(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        em = self.emissions(x)
        y = y.long()
        score = em[0, y[0]]
        for t in range(1, len(y)):
            score = score + self.transitions[y[t - 1], y[t]] + em[t, y[t]]
        alpha = em[0]
        for t in range(1, len(y)):
            alpha = torch.logsumexp(alpha.view(2, 1) + self.transitions + em[t].view(1, 2), dim=0)
        return (torch.logsumexp(alpha, dim=0) - score) / max(1, len(y))

    def decode(self, x: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            em = self.emissions(x)
            delta = em[0]
            back = []
            for t in range(1, len(x)):
                scores = delta.view(2, 1) + self.transitions + em[t].view(1, 2)
                best_prev = scores.argmax(dim=0)
                delta = scores.max(dim=0).values
                back.append(best_prev)
            state = int(delta.argmax())
            path = [state]
            for bp in reversed(back):
                state = int(bp[state])
                path.append(state)
            return np.asarray(path[::-1], dtype=bool)


def train_boundary_cnn(chunks, n_features: int, epochs: int, seed: int) -> BoundaryCNN:
    torch.manual_seed(seed)
    model = BoundaryCNN(n_features)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-3)
    for _ in range(epochs):
        for x_np, y_np in chunks:
            known = y_np >= 0
            if not known.any():
                continue
            y_np = y_np.copy()
            y_np[~known] = 0
            x = torch.tensor(x_np, dtype=torch.float32)
            y = torch.tensor(y_np, dtype=torch.float32)
            te_logit, boundary_logit = model(x)
            te_pos = max(1.0, float((y == 0).sum() / max(1, int((y == 1).sum()))))
            b = boundary_targets(y)
            b_pos = max(1.0, float((b == 0).sum() / max(1, int((b == 1).sum()))))
            loss_te = nn.functional.binary_cross_entropy_with_logits(te_logit[known], y[known], pos_weight=torch.tensor(te_pos))
            loss_b = nn.functional.binary_cross_entropy_with_logits(boundary_logit[known], b[known], pos_weight=torch.tensor(b_pos))
            loss = loss_te + 0.35 * loss_b
            opt.zero_grad()
            loss.backward()
            opt.step()
    return model


def train_crf(chunks, n_features: int, epochs: int, seed: int) -> LinearCRF:
    torch.manual_seed(seed)
    model = LinearCRF(n_features)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-2, weight_decay=1e-3)
    for _ in range(epochs):
        for x_np, y_np in chunks:
            known = y_np >= 0
            if not known.all():
                x_np = x_np[known]
                y_np = y_np[known]
            if len(y_np) < 32:
                continue
            x = torch.tensor(x_np, dtype=torch.float32)
            y = torch.tensor(y_np, dtype=torch.long)
            loss = model.nll(x, y)
            opt.zero_grad()
            loss.backward()
            opt.step()
    return model


def duration_prior_mask(prob: np.ndarray, train_truth: np.ndarray, threshold: float) -> np.ndarray:
    mask = prob >= threshold
    true_lens = [e - s for s, e in runs_from_bool((train_truth == 1).astype(bool))]
    if true_lens:
        min_len = max(5, int(np.quantile(true_lens, 0.05)))
        merge_gap = max(5, int(np.quantile(true_lens, 0.02)))
    else:
        min_len = 20
        merge_gap = 20
    out = mask.copy().astype(bool)
    for s, e in runs_from_bool(out):
        if e - s < min_len:
            out[s:e] = False
    segs = runs_from_bool(out)
    for left, right in zip(segs, segs[1:]):
        if 0 < right[0] - left[1] <= merge_gap:
            out[left[1] : right[0]] = True
    return out


def eval_mask(truth: np.ndarray, mask: np.ndarray, label: str, base_mask: np.ndarray, iou: float, tol: int) -> dict:
    known = truth >= 0
    truth_binary = truth == 1
    pred = mask.astype(bool).copy()
    pred[~known] = False
    row = {"variant": label, "iou_threshold": iou, "boundary_tol_bp": tol}
    row.update(binary_metrics(truth_binary[known], pred[known].astype(np.float32), 0.5))
    row.update(strict_segment_metrics(truth_binary, pred, iou, tol))
    row.update(fragmentation_truth_diagnostics(truth_binary, pred))
    deleted = base_mask.astype(bool) & ~pred
    true_backed = 0
    for ds, de in runs_from_bool(deleted):
        for ts, te in runs_from_bool(truth_binary):
            if te <= ds:
                continue
            if ts >= de:
                break
            if min(de, te) > max(ds, ts):
                true_backed += 1
                break
    row["deleted_segments"] = len(runs_from_bool(deleted))
    row["deleted_true_backed_segments"] = true_backed
    row["deleted_true_backed_rate"] = true_backed / row["deleted_segments"] if row["deleted_segments"] else 0.0
    return row


def write_report(out_dir: Path, rows: list[dict], status: dict) -> None:
    headline = [r for r in rows if r["split"] == "test" and r["iou_threshold"] == 0.8 and r["boundary_tol_bp"] == 5]
    best = sorted(headline, key=lambda r: r["segment_f1"], reverse=True)[0] if headline else {}
    lines = [
        "# PIPE-TEFM-NEXT-DECAY-FRAG-20260630 trainable fragment decoders",
        "",
        "## Scope",
        "",
        "Bounded smoke for trainable downstream decoders on frozen forward/reverse bp probability tracks.",
        "This tests whether learned boundary/CRF/duration components show signal before integrating them into backbone training.",
        "",
        "## Headline",
        "",
        f"- Windows: {status.get('n_windows')}; train fraction: {status.get('train_fraction')}.",
    ]
    if best:
        lines.append(f"- Best test variant: `{best['variant']}` segment-F1 {best['segment_f1']:.4f}, boundary-F1 {best['boundary_f1']:.4f}, missed true rate {best['missed_true_rate']:.4f}.")
    lines += [
        "",
        "## Interpretation rules",
        "",
        "- Promote only if a trainable decoder beats consensus+CRF and does not increase missed_true_rate or true-backed deletion.",
        "- This is not yet end-to-end HMM/CRF training on the backbone; it is a low-cost structural screen to decide which component deserves full integration.",
    ]
    (out_dir / "TRAINABLE_FRAGMENT_DECODERS_REPORT.md").write_text("\n".join(lines) + "\n")


def run(args) -> None:
    chrom_prob, chrom_truth, n_windows = build_tracks(args)
    rows = []
    statuses = []
    for chrom in sorted(chrom_prob):
        x = make_features(chrom_prob[chrom])
        truth = chrom_truth[chrom].astype(np.int64)
        split_idx = int(len(truth) * args.train_fraction)
        x_train, y_train = x[:split_idx], truth[:split_idx]
        x_test, y_test = x[split_idx:], truth[split_idx:]
        chunks = chunk_arrays(x_train, y_train, args.chunk_len)
        cnn = train_boundary_cnn(chunks, x.shape[1], args.epochs, args.seed)
        crf = train_crf(chunks, x.shape[1], args.epochs, args.seed)
        with torch.no_grad():
            cnn_logit, _ = cnn(torch.tensor(x_test, dtype=torch.float32))
            cnn_mask = (torch.sigmoid(cnn_logit).numpy() >= args.threshold)
        crf_mask = crf.decode(torch.tensor(x_test, dtype=torch.float32))
        cons_test = chrom_prob[chrom]["consensus_min"][split_idx:]
        raw_mask = cons_test >= args.threshold
        variants = {
            "consensus_min_raw": raw_mask,
            "consensus_min_crf_posthoc": viterbi_smooth(cons_test, 4.0),
            "duration_prior_decoder": duration_prior_mask(cons_test, y_train, args.threshold),
            "trainable_boundary_cnn": cnn_mask,
            "trainable_linear_crf": crf_mask,
        }
        for name, mask in variants.items():
            for iou in args.iou_thresholds:
                for tol in args.boundary_tolerances:
                    row = eval_mask(y_test, mask, name, raw_mask, iou, tol)
                    row.update({
                        "exp_id": args.exp_id,
                        "chrom": chrom,
                        "split": "test",
                        "n_windows": n_windows,
                        "train_fraction": args.train_fraction,
                        "train_chunks": len(chunks),
                        "epochs": args.epochs,
                    })
                    rows.append(row)
        statuses.append({
            "chrom": chrom,
            "bp": int(len(truth)),
            "train_bp": int(split_idx),
            "test_bp": int(len(truth) - split_idx),
            "train_chunks": len(chunks),
        })
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(out_dir / "trainable_fragment_decoder_metrics.tsv", rows)
    status = {
        "ok": True,
        "exp_id": args.exp_id,
        "n_windows": n_windows,
        "train_fraction": args.train_fraction,
        "chrom_status": statuses,
        "outputs": {
            "metrics": str(out_dir / "trainable_fragment_decoder_metrics.tsv"),
            "report": str(out_dir / "TRAINABLE_FRAGMENT_DECODERS_REPORT.md"),
            "status": str(out_dir / "trainable_fragment_decoder_status.json"),
        },
    }
    (out_dir / "trainable_fragment_decoder_status.json").write_text(json.dumps(status, indent=2) + "\n")
    write_report(out_dir, rows, status)
    print(json.dumps(status, indent=2), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-id", default="PIPE-TEFM-NEXT-DECAY-FRAG-20260630")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--data-jsonl", required=True)
    ap.add_argument("--out-dir", default="reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/trainable_fragment_decoders")
    ap.add_argument("--window", type=int, required=True)
    ap.add_argument("--stride", type=int, required=True)
    ap.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--train-fraction", type=float, default=0.6)
    ap.add_argument("--chunk-len", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--iou-thresholds", type=float, nargs="+", default=[0.8])
    ap.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5])
    ap.add_argument("--max-windows", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
