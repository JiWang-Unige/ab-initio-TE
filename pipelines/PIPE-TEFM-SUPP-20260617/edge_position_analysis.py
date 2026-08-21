#!/usr/bin/env python3
"""Evaluate whether token predictions degrade near non-overlap window edges."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import Trainer, TrainingArguments, default_data_collator

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from te_token_task import WindowDataset, WeightedTrainer, average_precision_binary, load_trained_model  # noqa: E402


BINS = [
    ("edge_left_10", 0.00, 0.10),
    ("inner_left_10_25", 0.10, 0.25),
    ("center_25_75", 0.25, 0.75),
    ("inner_right_75_90", 0.75, 0.90),
    ("edge_right_10", 0.90, 1.01),
]


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    out = {}
    for label, name in [(0, "bg"), (1, "te")]:
        tp = int(((y_true == label) & (y_pred == label)).sum())
        fp = int(((y_true != label) & (y_pred == label)).sum())
        fn = int(((y_true == label) & (y_pred != label)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[f"{name}_precision"] = precision
        out[f"{name}_recall"] = recall
        out[f"{name}_f1"] = f1
    out["macro_f1"] = (out["bg_f1"] + out["te_f1"]) / 2
    out["te_auprc"] = average_precision_binary(y_true, y_prob)
    out["n_labeled_tokens"] = int(y_true.size)
    out["te_positive_rate"] = float((y_true == 1).sum() / max(1, y_true.size))
    return out


def bucket_arrays(logits: np.ndarray, labels: np.ndarray) -> list[dict]:
    probs = torch.softmax(torch.tensor(logits), dim=-1).numpy()[..., 1]
    pred = np.argmax(logits, axis=-1)
    rows = []
    for bin_name, lo, hi in BINS:
        ys_true = []
        ys_pred = []
        ys_prob = []
        for i in range(labels.shape[0]):
            valid = np.flatnonzero(labels[i] != -100)
            if valid.size == 0:
                continue
            denom = max(1, valid.size - 1)
            frac = np.arange(valid.size) / denom
            take = valid[(frac >= lo) & (frac < hi)]
            if take.size == 0:
                continue
            ys_true.append(labels[i, take])
            ys_pred.append(pred[i, take])
            ys_prob.append(probs[i, take])
        if not ys_true:
            continue
        y_true = np.concatenate(ys_true).astype(int)
        y_pred = np.concatenate(ys_pred).astype(int)
        y_prob = np.concatenate(ys_prob).astype(float)
        item = {"position_bin": bin_name, **binary_metrics(y_true, y_pred, y_prob)}
        rows.append(item)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-tsv", required=True)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--max-samples", type=int, default=1200)
    ap.add_argument("--stage", default="")
    ap.add_argument("--model-key", default="")
    ap.add_argument("--window", type=int)
    ap.add_argument("--species", default="")
    args = ap.parse_args()

    model, tokenizer, meta = load_trained_model(args.model_dir)
    ds = WindowDataset(
        str(Path(args.data_dir) / "test/data.jsonl.gz"),
        tokenizer,
        int(meta["window"]),
        meta["token_label_mode"],
        args.max_samples,
    )
    out_path = Path(args.out_tsv)
    targs = TrainingArguments(
        output_dir=str(out_path.parent / "_tmp_edge"),
        per_device_eval_batch_size=args.batch_size,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer: Trainer = WeightedTrainer(model=model, args=targs, data_collator=default_data_collator)
    pred = trainer.predict(ds)
    rows = bucket_arrays(pred.predictions, pred.label_ids)
    for row in rows:
        row.update({
            "stage": args.stage,
            "model_key": args.model_key,
            "window": args.window or meta.get("window"),
            "species": args.species,
            "model_dir": args.model_dir,
            "data_dir": args.data_dir,
            "n_windows": len(ds),
        })
    keys = [
        "stage", "model_key", "window", "species", "position_bin",
        "te_f1", "te_precision", "te_recall", "te_auprc", "macro_f1",
        "bg_f1", "n_labeled_tokens", "te_positive_rate", "n_windows",
        "model_dir", "data_dir",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"out_tsv": str(out_path), "rows": len(rows), "n_windows": len(ds)}, indent=2))


if __name__ == "__main__":
    main()
