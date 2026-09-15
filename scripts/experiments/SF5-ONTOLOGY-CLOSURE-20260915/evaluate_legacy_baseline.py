#!/usr/bin/env python3
"""Evaluate the historical six-label SF5 checkpoint on the complete test set.

This is a collapsed baseline only.  New ontology labels 5--7 are mapped to
the old Unknown id for this evaluation; the old checkpoint is not reselected
using the repaired validation set.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset
from transformers import AutoModelForTokenClassification, AutoTokenizer, Trainer, TrainingArguments


ID2LABEL = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}


class CollapsedDataset(Dataset):
    def __init__(self, path: str, tokenizer, window: int):
        self.records = []
        with gzip.open(path, "rt") as handle:
            for line in handle:
                self.records.append(json.loads(line))
        self.tokenizer = tokenizer
        self.window = window

    @property
    def species(self):
        return [str(rec.get("species_code", "unknown")) for rec in self.records]

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        rec = self.records[idx]
        seq = rec["sequence"][: self.window]
        true_labels = [int(x) for x in rec["labels"][: self.window]]
        labels = [x if x <= 4 else 5 for x in true_labels]
        max_len = self.window + 2
        enc = self.tokenizer(seq, truncation=True, max_length=max_len, padding="max_length")
        token_labels = [-100] + labels + [-100]
        token_labels.extend([-100] * (max_len - len(token_labels)))
        return {
            "input_ids": torch.tensor(enc["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(
                enc.get("attention_mask", [1] * len(enc["input_ids"])), dtype=torch.long
            ),
            "labels": torch.tensor(token_labels[:max_len], dtype=torch.long),
        }


def safe_prf(y_true, y_pred, label):
    tp = int(((y_true == label) & (y_pred == label)).sum())
    fp = int(((y_true != label) & (y_pred == label)).sum())
    fn = int(((y_true == label) & (y_pred != label)).sum())
    support = int((y_true == label).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f, support, tp, fp, fn


def metrics(y_true, y_pred):
    out = {}
    fs = []
    main_fs = []
    for label, name in ID2LABEL.items():
        p, r, f, support, tp, fp, fn = safe_prf(y_true, y_pred, label)
        key = name.lower()
        out.update(
            {
                f"{key}_precision": p,
                f"{key}_recall": r,
                f"{key}_f1": f,
                f"{key}_support": support,
                f"{key}_tp": tp,
                f"{key}_fp": fp,
                f"{key}_fn": fn,
            }
        )
        if support:
            fs.append(f)
            if label in {1, 2, 3, 4}:
                main_fs.append(f)
    true_te = (y_true != 0).astype(np.int8)
    pred_te = (y_pred != 0).astype(np.int8)
    _, _, te_f1, te_support, _, _, _ = safe_prf(true_te, pred_te, 1)
    out.update(
        {
            "macro_f1_all6": float(np.mean(fs)) if fs else 0.0,
            "main4_macro_f1": float(np.mean(main_fs)) if main_fs else 0.0,
            "te_material_f1": te_f1,
            "te_material_support": te_support,
            "accuracy": float((y_true == y_pred).mean()) if y_true.size else 0.0,
            "support_total": int(y_true.size),
        }
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--batch-size", type=int, default=1)
    args = ap.parse_args()
    model_path = Path(args.model_dir)
    if (model_path / "best_model").is_dir():
        model_path = model_path / "best_model"
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_path), trust_remote_code=True, local_files_only=True
    )
    model = AutoModelForTokenClassification.from_pretrained(
        str(model_path), trust_remote_code=True, local_files_only=True
    )
    ds = CollapsedDataset(str(Path(args.data_dir) / "test" / "data.jsonl.gz"), tokenizer, args.window)
    targs = TrainingArguments(
        output_dir=str(Path(args.out_json).parent / "_tmp_legacy_eval"),
        per_device_eval_batch_size=args.batch_size,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=targs)
    result = trainer.predict(ds)
    logits = result.predictions[0] if isinstance(result.predictions, tuple) else result.predictions
    pred = np.argmax(logits, axis=-1)
    labels = np.asarray(result.label_ids)
    mask = labels != -100
    y_true = labels[mask].astype(np.int64)
    y_pred = pred[mask].astype(np.int64)
    all_metrics = {"aggregate": metrics(y_true, y_pred)}
    token_species = np.repeat(np.asarray(ds.species, dtype=object), labels.shape[1])
    flat_species = token_species[mask.reshape(-1)]
    all_metrics["per_species"] = {}
    for species in sorted(set(ds.species)):
        select = flat_species == species
        all_metrics["per_species"][species] = metrics(y_true[select], y_pred[select])
    all_metrics.update(
        {
            "protocol": "SF5_ONTOLOGY_CLOSURE_20260915_COLLAPSED_LEGACY_BASELINE",
            "model_dir": str(model_path),
            "data_dir": args.data_dir,
            "n_windows": len(ds),
            "true_label_mapping": "new ontology ids 5,6,7 -> legacy Unknown(5)",
            "selection_note": "historical checkpoint retained; no repaired-validation reselection",
        }
    )
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(all_metrics, indent=2) + "\n")
    print(json.dumps(all_metrics, indent=2))


if __name__ == "__main__":
    main()
