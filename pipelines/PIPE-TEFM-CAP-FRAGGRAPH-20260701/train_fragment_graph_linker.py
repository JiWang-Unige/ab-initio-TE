#!/usr/bin/env python3
"""Fragment-graph linker screen for TE interval reconstruction.

Round 2 replacement component for TEFM-CAP-FRAGARCH:
raw CE fragments become graph nodes; a learned edge classifier decides whether
adjacent fragments should be linked into one interval. The primary decode keeps
all CE fragments and only learns links/fills, so true-backed fragment deletion
is guarded by architecture rather than by a tuned threshold/gap rule.
"""
from __future__ import annotations

import argparse
import csv
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
from torch.utils.data import DataLoader

SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
FINAL = Path("pipelines/PIPE-TEFM-FINAL-20260623").resolve()
ROUND1 = Path("pipelines/PIPE-TEFM-CAP-FRAGARCH-20260701").resolve()
sys.path.insert(0, str(SUPP))
sys.path.insert(0, str(FINAL))
sys.path.insert(0, str(ROUND1))

from te_token_task import WindowDataset, load_tokenizer, load_trained_model  # noqa: E402
from strict_segment_eval import binary_metrics, fragmentation_truth_diagnostics, runs_from_bool, strict_segment_metrics, viterbi_smooth  # noqa: E402
from train_interval_architectures import deleted_fragment_diagnostics, overmerge_rate, write_tsv  # noqa: E402


def valid_token_arrays(labels: torch.Tensor, values: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
    keep = labels.detach().cpu().numpy() >= 0
    return labels.detach().cpu().numpy()[keep], values.detach().cpu().numpy()[keep]


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
        hidden = torch.cat([logits, torch.softmax(logits, dim=-1)], dim=-1)
    return hidden.detach(), logits.detach()


def span_overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def best_true_segment(span: tuple[int, int], true_segments: list[tuple[int, int]]) -> tuple[int, float]:
    best_idx = -1
    best_frac = 0.0
    length = max(1, span[1] - span[0])
    for i, seg in enumerate(true_segments):
        frac = span_overlap(span, seg) / length
        if frac > best_frac:
            best_idx = i
            best_frac = frac
    return best_idx, best_frac


def graph_spans_from_prob(prob: np.ndarray, threshold: float) -> list[tuple[int, int]]:
    spans = runs_from_bool((prob >= threshold).astype(bool))
    return [(int(s), int(e)) for s, e in spans if e > s]


def masked_hidden(hidden: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    keep = labels >= 0
    return hidden[keep]


def node_feature_matrix(hidden: torch.Tensor, prob: np.ndarray, spans: list[tuple[int, int]]) -> torch.Tensor:
    feats = []
    n = max(1, hidden.shape[0])
    prob_t = torch.as_tensor(prob, dtype=torch.float32, device=hidden.device)
    for s, e in spans:
        seg_h = hidden[s:e]
        seg_p = prob_t[s:e]
        length = max(1, e - s)
        if seg_h.numel() == 0:
            base = torch.zeros(hidden.shape[-1] * 2 + 7, dtype=torch.float32, device=hidden.device)
        else:
            base = torch.cat([
                seg_h.mean(dim=0),
                seg_h.max(dim=0).values,
                torch.stack([
                    torch.tensor(math.log1p(length), device=hidden.device),
                    torch.tensor(s / n, device=hidden.device),
                    torch.tensor(e / n, device=hidden.device),
                    torch.tensor(length / n, device=hidden.device),
                    seg_p.mean(),
                    seg_p.max(),
                    seg_p.min(),
                ]),
            ])
        feats.append(base)
    if not feats:
        return torch.empty(0, hidden.shape[-1] * 2 + 7, device=hidden.device)
    return torch.stack(feats)


def edge_feature_matrix(
    hidden: torch.Tensor,
    prob: np.ndarray,
    spans: list[tuple[int, int]],
    edge_pairs: list[tuple[int, int]],
) -> torch.Tensor:
    feats = []
    n = max(1, hidden.shape[0])
    prob_t = torch.as_tensor(prob, dtype=torch.float32, device=hidden.device)
    for i, j in edge_pairs:
        a, b = spans[i], spans[j]
        gap_s, gap_e = a[1], b[0]
        gap_len = max(0, gap_e - gap_s)
        span_s, span_e = a[0], b[1]
        gap_p = prob_t[gap_s:gap_e] if gap_e > gap_s else torch.empty(0, device=hidden.device)
        span_p = prob_t[span_s:span_e]
        left_h = hidden[a[0]:a[1]].mean(dim=0)
        right_h = hidden[b[0]:b[1]].mean(dim=0)
        cos = F.cosine_similarity(left_h.view(1, -1), right_h.view(1, -1)).squeeze(0)
        feats.append(torch.stack([
            torch.tensor(math.log1p(gap_len), device=hidden.device),
            torch.tensor(gap_len / n, device=hidden.device),
            gap_p.mean() if gap_p.numel() else torch.tensor(1.0, device=hidden.device),
            gap_p.max() if gap_p.numel() else torch.tensor(1.0, device=hidden.device),
            span_p.mean() if span_p.numel() else torch.tensor(0.0, device=hidden.device),
            span_p.min() if span_p.numel() else torch.tensor(0.0, device=hidden.device),
            cos,
            torch.tensor((span_e - span_s) / n, device=hidden.device),
        ]))
    if not feats:
        return torch.empty(0, 8, device=hidden.device)
    return torch.stack(feats)


def build_graph(
    hidden: torch.Tensor,
    labels: np.ndarray,
    prob: np.ndarray,
    args,
) -> dict:
    spans = graph_spans_from_prob(prob, args.threshold)
    true_segments = runs_from_bool((labels == 1).astype(bool))
    if not spans:
        return {"spans": [], "node_x": torch.empty(0, hidden.shape[-1] * 2 + 7, device=hidden.device), "edge_pairs": [], "edge_attr": torch.empty(0, 8, device=hidden.device), "node_y": torch.empty(0, device=hidden.device), "edge_y": torch.empty(0, device=hidden.device)}
    node_x = node_feature_matrix(hidden, prob, spans)
    node_y = []
    node_true_ids = []
    for span in spans:
        tid, frac = best_true_segment(span, true_segments)
        node_true_ids.append(tid if frac >= args.node_true_frac else -1)
        node_y.append(1.0 if frac >= args.node_true_frac else 0.0)
    edge_pairs = []
    edge_y = []
    for i in range(len(spans) - 1):
        j = i + 1
        gap = spans[j][0] - spans[i][1]
        if gap > args.max_edge_gap:
            continue
        edge_pairs.append((i, j))
        same_true = node_true_ids[i] >= 0 and node_true_ids[i] == node_true_ids[j]
        if same_true:
            gap_s, gap_e = spans[i][1], spans[j][0]
            gap_labels = labels[gap_s:gap_e] if gap_e > gap_s else np.asarray([1])
            known = gap_labels >= 0
            gap_true_frac = float((gap_labels[known] == 1).mean()) if known.any() else 0.0
            edge_y.append(1.0 if gap_true_frac >= args.edge_true_gap_frac else 0.0)
        else:
            edge_y.append(0.0)
    edge_attr = edge_feature_matrix(hidden, prob, spans, edge_pairs)
    return {
        "spans": spans,
        "node_x": node_x,
        "edge_pairs": edge_pairs,
        "edge_attr": edge_attr,
        "node_y": torch.tensor(node_y, dtype=torch.float32, device=hidden.device),
        "edge_y": torch.tensor(edge_y, dtype=torch.float32, device=hidden.device),
    }


class FragmentGraphLinker(nn.Module):
    def __init__(self, node_in: int, hidden: int = 128):
        super().__init__()
        self.node_encoder = nn.Sequential(
            nn.Linear(node_in, hidden),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden, hidden),
            nn.GELU(),
        )
        self.node_keep = nn.Linear(hidden, 1)
        self.edge = nn.Sequential(
            nn.Linear(hidden * 2 + 8, hidden),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden, hidden // 2),
            nn.GELU(),
            nn.Linear(hidden // 2, 1),
        )

    def forward(self, node_x: torch.Tensor, edge_pairs: list[tuple[int, int]], edge_attr: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        node_h = self.node_encoder(node_x)
        keep_logits = self.node_keep(node_h).squeeze(-1)
        if not edge_pairs:
            return keep_logits, torch.empty(0, device=node_x.device)
        e_feat = []
        for k, (i, j) in enumerate(edge_pairs):
            e_feat.append(torch.cat([node_h[i], node_h[j], edge_attr[k]], dim=0))
        edge_logits = self.edge(torch.stack(e_feat)).squeeze(-1)
        return keep_logits, edge_logits


def train_graph_model(args, base_model: nn.Module, tokenizer, meta: dict, device: torch.device) -> tuple[FragmentGraphLinker, dict]:
    train_ds = WindowDataset(str(Path(args.train_data_dir) / "train/data.jsonl.gz"), tokenizer, args.window, meta["token_label_mode"], args.max_train_samples)
    loader = DataLoader(train_ds, batch_size=1, shuffle=True)
    base_model.eval()
    graph_model = None
    opt = None
    losses = []
    edge_pos_total = 0
    edge_total = 0
    step = 0
    for _epoch in range(args.epochs):
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            labels_t = batch["labels"][0]
            with torch.no_grad():
                hidden, logits = extract_hidden_and_logits(base_model, {k: v for k, v in batch.items() if k != "labels"})
                y_np, prob = valid_token_arrays(labels_t, torch.softmax(logits[0], dim=-1)[:, 1])
                h = masked_hidden(hidden[0], labels_t)
            graph = build_graph(h, y_np, prob.astype(np.float32), args)
            if graph["node_x"].shape[0] == 0:
                continue
            if graph_model is None:
                graph_model = FragmentGraphLinker(graph["node_x"].shape[-1], args.graph_hidden).to(device)
                opt = torch.optim.AdamW(graph_model.parameters(), lr=args.learning_rate, weight_decay=0.01)
            keep_logits, edge_logits = graph_model(graph["node_x"], graph["edge_pairs"], graph["edge_attr"])
            node_y = graph["node_y"]
            node_loss = F.binary_cross_entropy_with_logits(keep_logits, node_y)
            if edge_logits.numel():
                edge_y = graph["edge_y"]
                pos_weight = torch.tensor([args.edge_pos_weight], dtype=torch.float32, device=device)
                edge_loss = F.binary_cross_entropy_with_logits(edge_logits, edge_y, pos_weight=pos_weight)
                edge_pos_total += int(edge_y.sum().item())
                edge_total += int(edge_y.numel())
            else:
                edge_loss = node_loss * 0.0
            loss = 0.25 * node_loss + edge_loss
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(graph_model.parameters(), 1.0)
            opt.step()
            losses.append(float(loss.detach().cpu()))
            step += 1
            if step >= args.max_steps:
                break
        if step >= args.max_steps:
            break
    if graph_model is None:
        raise RuntimeError("No raw CE fragments were found in training data; graph model was not initialized.")
    info = {
        "train_steps": step,
        "mean_train_loss": float(np.mean(losses)) if losses else math.nan,
        "edge_positive_rate_train": edge_pos_total / edge_total if edge_total else 0.0,
        "token_label_mode": meta["token_label_mode"],
    }
    return graph_model, info


def decode_graph(graph_model: FragmentGraphLinker, hidden: torch.Tensor, labels: np.ndarray, prob: np.ndarray, args, mode: str) -> np.ndarray:
    graph = build_graph(hidden, labels, prob, args)
    spans = graph["spans"]
    out = prob >= args.threshold
    if not spans:
        return out.astype(bool)
    with torch.no_grad():
        keep_logits, edge_logits = graph_model(graph["node_x"], graph["edge_pairs"], graph["edge_attr"])
        keep_scores = torch.sigmoid(keep_logits).detach().cpu().numpy()
        edge_scores = torch.sigmoid(edge_logits).detach().cpu().numpy() if edge_logits.numel() else np.asarray([])
    if mode == "fragment_graph_keepdrop":
        out = np.zeros_like(out, dtype=bool)
        for score, (s, e) in zip(keep_scores, spans):
            if score >= args.node_keep_threshold:
                out[s:e] = True
    else:
        # Primary decode: preserve all CE raw fragments; learn only links/fills.
        out = (prob >= args.threshold).astype(bool)
    for score, (i, j) in zip(edge_scores, graph["edge_pairs"]):
        if score >= args.edge_link_threshold:
            s, e = spans[i][1], spans[j][0]
            if e > s:
                out[s:e] = True
    return out.astype(bool)


def predict_panel(args, base_model, graph_model, tokenizer, meta, data_jsonl: Path, device: torch.device) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    ds = WindowDataset(str(data_jsonl), tokenizer, args.window, meta["token_label_mode"], args.max_eval_samples)
    loader = DataLoader(ds, batch_size=1, shuffle=False)
    parts: dict[str, list[np.ndarray]] = {k: [] for k in ["truth", "ce_raw", "crf_style_penalty4", "fragment_graph_keepall", "fragment_graph_keepdrop"]}
    base_model.eval()
    graph_model.eval()
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            labels_t = batch["labels"][0]
            hidden, logits = extract_hidden_and_logits(base_model, {k: v for k, v in batch.items() if k != "labels"})
            y, prob = valid_token_arrays(labels_t, torch.softmax(logits[0], dim=-1)[:, 1])
            h = masked_hidden(hidden[0], labels_t)
            prob = prob.astype(np.float32)
            parts["truth"].append(y.astype(np.int8))
            parts["ce_raw"].append(prob >= args.threshold)
            parts["crf_style_penalty4"].append(viterbi_smooth(prob, 4.0).astype(bool))
            parts["fragment_graph_keepall"].append(decode_graph(graph_model, h, y, prob, args, "fragment_graph_keepall"))
            parts["fragment_graph_keepdrop"].append(decode_graph(graph_model, h, y, prob, args, "fragment_graph_keepdrop"))
    truth = np.concatenate(parts["truth"])
    return {k: (truth, np.concatenate(v).astype(bool)) for k, v in parts.items() if k != "truth"}


def eval_rows(panel: str, variant: str, truth: np.ndarray, pred: np.ndarray, baseline_pred: np.ndarray | None, info: dict, args) -> list[dict]:
    known = truth >= 0
    y = truth == 1
    p = pred.astype(bool)
    base = {"panel": panel, "variant": variant, "same_panel_comparable": True}
    base.update(info)
    base.update(binary_metrics(y[known], p[known].astype(np.float32), 0.5))
    base.update(fragmentation_truth_diagnostics(y, p))
    base.update(deleted_fragment_diagnostics(y, baseline_pred, p))
    base["overmerge_rate"] = overmerge_rate(y, p)
    rows = []
    for iou in args.iou_thresholds:
        for tol in args.boundary_tolerances:
            row = dict(base)
            row.update({"iou_threshold": iou, "boundary_tol_bp": tol})
            row.update(strict_segment_metrics(y, p, iou, tol))
            rows.append(row)
    return rows


def summarize(rows: list[dict], args) -> dict:
    focal = [r for r in rows if r.get("same_panel_comparable") is True and float(r.get("iou_threshold", -1)) == 0.8 and int(r.get("boundary_tol_bp", -1)) == 5]
    by_panel: dict[str, dict[str, dict]] = {}
    for r in focal:
        by_panel.setdefault(str(r["panel"]), {})[str(r["variant"])] = r
    gate = []
    for panel, variants in by_panel.items():
        ce = variants.get("ce_raw")
        smooth = variants.get("crf_style_penalty4")
        if ce is None or smooth is None:
            continue
        for cand in ["fragment_graph_keepall", "fragment_graph_keepdrop"]:
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
                gate.append({"panel": panel, "variant": cand})
    return {
        "ok": True,
        "promotion_gate_pass": len(gate) >= 2,
        "gate_pass_panels": gate,
        "gate_definition": "candidate beats CE and CRF-style smoothing on segment-F1@0.8 and boundary-F1@5bp; missed_true_rate <= CE+0.03; deleted_true_backed_fraction <= threshold; pred_true_backed_rate retained",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-id", default="PIPE-TEFM-CAP-FRAGGRAPH-20260701")
    ap.add_argument("--init-model-dir", required=True)
    ap.add_argument("--train-data-dir", required=True)
    ap.add_argument("--eval-panel", action="append", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-train-samples", type=int, default=128)
    ap.add_argument("--max-eval-samples", type=int, default=40)
    ap.add_argument("--max-steps", type=int, default=80)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--learning-rate", type=float, default=5e-4)
    ap.add_argument("--graph-hidden", type=int, default=128)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--max-edge-gap", type=int, default=512)
    ap.add_argument("--node-true-frac", type=float, default=0.10)
    ap.add_argument("--edge-true-gap-frac", type=float, default=0.50)
    ap.add_argument("--edge-pos-weight", type=float, default=3.0)
    ap.add_argument("--edge-link-threshold", type=float, default=0.5)
    ap.add_argument("--node-keep-threshold", type=float, default=0.5)
    ap.add_argument("--max-deleted-true-backed-fraction", type=float, default=0.15)
    ap.add_argument("--iou-thresholds", type=float, nargs="+", default=[0.5, 0.7, 0.8, 0.9])
    ap.add_argument("--boundary-tolerances", type=int, nargs="+", default=[5, 10, 25])
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

    graph_model, info = train_graph_model(args, base_model, tokenizer, meta, device)
    rows: list[dict] = []
    for spec in args.eval_panel:
        name, path_str = spec.split(":", 1)
        preds = predict_panel(args, base_model, graph_model, tokenizer, meta, Path(path_str), device)
        baseline = preds["ce_raw"][1]
        for variant, (truth, pred) in preds.items():
            rows.extend(eval_rows(name, variant, truth, pred, baseline, info, args))
    metrics = out_dir / "fragment_graph_metrics.tsv"
    write_tsv(metrics, rows)
    status = summarize(rows, args)
    status.update({
        "exp_id": args.exp_id,
        "seed": args.seed,
        "device": str(device),
        "init_model_dir": args.init_model_dir,
        "train_data_dir": args.train_data_dir,
        "eval_panel": args.eval_panel,
        "metrics": str(metrics),
        "new_architectures": ["fragment_graph_keepall", "fragment_graph_keepdrop"],
        "same_panel_baselines": ["ce_raw", "crf_style_penalty4"],
        "non_goal": "No threshold/gap/HMM/CRF/survival-retention tuning; edge/link thresholds are fixed screen defaults.",
    })
    (out_dir / "fragment_graph_status.json").write_text(json.dumps(status, indent=2) + "\n")
    report = [
        "# Fragment Graph Linker Screen",
        "",
        f"- Exp ID: `{args.exp_id}`",
        f"- Seed: `{args.seed}`",
        f"- Init model: `{args.init_model_dir}`",
        f"- Train data: `{args.train_data_dir}`",
        f"- Eval panels: `{', '.join(args.eval_panel)}`",
        f"- Promotion gate pass: `{status['promotion_gate_pass']}`",
        f"- Gate-pass panels: `{status['gate_pass_panels']}`",
        "",
        "This is a bounded capability-pursue screen. The primary decode preserves all CE raw fragments and learns graph links/fills between adjacent fragments; it is not a gap/threshold/HMM tuning run.",
    ]
    (out_dir / "FRAGMENT_GRAPH_LINKER_REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
