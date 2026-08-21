#!/usr/bin/env python3
"""Embedding diagnostic with clustering, linear-probe, and pairwise similarity metrics."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

SEG_DIR = Path("pipelines/PIPE-TEFM-SEG-SF-20260618").resolve()
sys.path.insert(0, str(SEG_DIR))

from embedding_cluster import (  # noqa: E402
    choose_split,
    evaluate_embeddings,
    load_records,
    model_embeddings,
    seq_features,
    standardize,
    supervised_contrastive_project,
)


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = standardize(a)
    b = standardize(b)
    a = a / np.clip(np.linalg.norm(a, axis=1, keepdims=True), 1e-8, None)
    b = b / np.clip(np.linalg.norm(b, axis=1, keepdims=True), 1e-8, None)
    return (a * b).sum(axis=1)


def rank_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1)
    pos = labels == 1
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def pairwise_metrics(x: np.ndarray, y: np.ndarray, seed: int, n_pairs: int = 10000) -> dict:
    rng = np.random.default_rng(seed)
    by_label = {int(v): np.flatnonzero(y == v) for v in sorted(set(y.tolist()))}
    pairs = []
    labels = []
    for _ in range(n_pairs // 2):
        lab = int(rng.choice(list(by_label)))
        idx = by_label[lab]
        if len(idx) >= 2:
            a, b = rng.choice(idx, size=2, replace=False)
            pairs.append((a, b))
            labels.append(1)
    labs = list(by_label)
    for _ in range(n_pairs // 2):
        la, lb = rng.choice(labs, size=2, replace=False)
        a = int(rng.choice(by_label[int(la)]))
        b = int(rng.choice(by_label[int(lb)]))
        pairs.append((a, b))
        labels.append(0)
    if not pairs:
        return {}
    ii = np.asarray([p[0] for p in pairs], dtype=np.int64)
    jj = np.asarray([p[1] for p in pairs], dtype=np.int64)
    lab = np.asarray(labels, dtype=np.int8)
    sim = cosine(x[ii], x[jj])
    return {
        "pair_pos_sim_mean": float(sim[lab == 1].mean()) if (lab == 1).any() else math.nan,
        "pair_neg_sim_mean": float(sim[lab == 0].mean()) if (lab == 0).any() else math.nan,
        "pair_auc": rank_auc(lab, sim),
        "n_pairs": int(len(lab)),
    }


def linear_probe(x: np.ndarray, y: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray) -> dict:
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, f1_score
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", n_jobs=1)
        clf.fit(standardize(x[train_idx]), y[train_idx])
        pred = clf.predict(standardize(x[test_idx]))
        return {
            "linear_probe_accuracy": float(accuracy_score(y[test_idx], pred)),
            "linear_probe_macro_f1": float(f1_score(y[test_idx], pred, average="macro", zero_division=0)),
        }
    except Exception as exc:
        return {"linear_probe_error": repr(exc)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragments", required=True)
    ap.add_argument("--setting", choices=["A0", "A1", "B0", "B1", "C0", "C1"], required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model-path")
    ap.add_argument("--model-kind", choices=["base", "token"], default="base")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-records", type=int, default=2500)
    ap.add_argument("--contrastive-epochs", type=int, default=160)
    ap.add_argument("--kmer", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    import torch

    records = load_records(args.fragments, args.max_records)
    y = np.asarray([int(r["label"]) for r in records], dtype=np.int64)
    train_idx, test_idx = choose_split(y, args.seed)
    if args.setting in {"C0", "C1"}:
        x = seq_features(records, args.kmer)
    else:
        if not args.model_path:
            raise SystemExit("--model-path is required for model embedding settings")
        device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
        x = model_embeddings(records, args.model_path, args.model_kind, args.batch_size, device)
    if args.setting.endswith("1"):
        x = supervised_contrastive_project(x, y, args.seed, train_idx, args.contrastive_epochs)
    metrics, _clusters = evaluate_embeddings(x, y, args.seed, train_idx, test_idx)
    metrics.update(pairwise_metrics(x, y, args.seed))
    metrics.update(linear_probe(x, y, train_idx, test_idx))
    metrics.update({
        "setting": args.setting,
        "fragments": args.fragments,
        "model_path": args.model_path or "",
        "model_kind": args.model_kind,
        "n_records": int(len(records)),
        "length": len(records[0]["sequence"]) if records else 0,
    })
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "diagnostic_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
