#!/usr/bin/env python3
"""Train/evaluate main4+Unknown token classifier for TE superfamilies."""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import os
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD", "1")
os.environ.setdefault("WANDB_DISABLED", "true")

import numpy as np
import torch
from torch.utils.data import Dataset
from transformers import AutoModelForTokenClassification, AutoTokenizer, Trainer, TrainingArguments, default_data_collator, set_seed

ID2LABEL = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}
NUM_LABELS = len(ID2LABEL)
MAIN4 = {1, 2, 3, 4}
UNKNOWN = 5


class SuperfamilyDataset(Dataset):
    def __init__(self, jsonl_gz: str, tokenizer, window: int, max_samples: int | None = None):
        self.records = []
        with gzip.open(jsonl_gz, "rt") as handle:
            for i, line in enumerate(handle):
                if max_samples is not None and i >= max_samples:
                    break
                self.records.append(json.loads(line))
        self.tokenizer = tokenizer
        self.window = window

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx: int):
        rec = self.records[idx]
        seq = rec["sequence"][:self.window]
        labels = [int(x) for x in rec["labels"][:self.window]]
        max_len = self.window + 2
        enc = self.tokenizer(seq, truncation=True, max_length=max_len, padding="max_length")
        token_labels = [-100] + labels + [-100]
        token_labels.extend([-100] * (max_len - len(token_labels)))
        return {
            "input_ids": torch.tensor(enc["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(enc.get("attention_mask", [1] * len(enc["input_ids"])), dtype=torch.long),
            "labels": torch.tensor(token_labels[:max_len], dtype=torch.long),
        }


def safe_prf(y_true: np.ndarray, y_pred: np.ndarray, label: int) -> tuple[float, float, float, int]:
    tp = int(((y_true == label) & (y_pred == label)).sum())
    fp = int(((y_true != label) & (y_pred == label)).sum())
    fn = int(((y_true == label) & (y_pred != label)).sum())
    sup = int((y_true == label).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f, sup


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    pred = np.argmax(logits, axis=-1)
    mask = labels != -100
    y_true = labels[mask].flatten()
    y_pred = pred[mask].flatten()
    out = {}
    f_all = []
    f_main4 = []
    for label, name in ID2LABEL.items():
        p, r, f, sup = safe_prf(y_true, y_pred, label)
        lname = name.lower()
        out[f"{lname}_precision"] = p
        out[f"{lname}_recall"] = r
        out[f"{lname}_f1"] = f
        out[f"{lname}_support"] = sup
        f_all.append(f)
        if label in MAIN4 and sup > 0:
            f_main4.append(f)
    true_te = (y_true != 0).astype(np.int8)
    pred_te = (y_pred != 0).astype(np.int8)
    _, _, te_f1, _ = safe_prf(true_te, pred_te, 1)
    main_mask = np.isin(y_true, list(MAIN4))
    unknown_mask = y_true == UNKNOWN
    main_false_unknown = float((y_pred[main_mask] == UNKNOWN).mean()) if main_mask.any() else 0.0
    unknown_to_main = float(np.isin(y_pred[unknown_mask], list(MAIN4)).mean()) if unknown_mask.any() else 0.0
    main_cond_acc = float((y_true[main_mask] == y_pred[main_mask]).mean()) if main_mask.any() else 0.0
    out.update({
        "te_detect_f1": te_f1,
        "main4_conditional_macro_f1": float(np.mean(f_main4)) if f_main4 else 0.0,
        "main4_conditional_accuracy": main_cond_acc,
        "macro_f1_all6": float(np.mean(f_all)) if f_all else 0.0,
        "unknown_recall": out.get("unknown_recall", 0.0),
        "main4_false_unknown_rate": main_false_unknown,
        "unknown_to_main4_rate": unknown_to_main,
        "acc": float((y_true == y_pred).mean()) if y_true.size else 0.0,
    })
    counts = collections.Counter(y_pred.tolist())
    total = max(1, y_pred.size)
    for label, name in ID2LABEL.items():
        out[f"pred_{name.lower()}_ratio"] = counts.get(label, 0) / total
    return out


class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = torch.tensor(class_weights or [1.0, 3.0, 3.0, 3.0, 3.0, 1.5], dtype=torch.float32)

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss_fn = torch.nn.CrossEntropyLoss(weight=self.class_weights.to(outputs.logits.device), ignore_index=-100)
        loss = loss_fn(outputs.logits.reshape(-1, NUM_LABELS), labels.reshape(-1))
        return (loss, outputs) if return_outputs else loss

    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        inputs = self._prepare_inputs(inputs)
        labels = inputs.pop("labels", None)
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits.detach()
        loss = None
        if labels is not None:
            loss_fn = torch.nn.CrossEntropyLoss(weight=self.class_weights.to(logits.device), ignore_index=-100)
            loss = loss_fn(logits.reshape(-1, NUM_LABELS), labels.reshape(-1)).detach()
        if prediction_loss_only:
            return loss, None, None
        return loss, logits, labels


def load_model(checkpoint: str):
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True, local_files_only=True)
    id2label = {i: ID2LABEL[i] for i in range(NUM_LABELS)}
    label2id = {v: k for k, v in id2label.items()}
    model = AutoModelForTokenClassification.from_pretrained(
        checkpoint,
        num_labels=NUM_LABELS,
        id2label=id2label,
        label2id=label2id,
        trust_remote_code=True,
        local_files_only=True,
        ignore_mismatched_sizes=True,
    )
    return model, tokenizer


def train(args) -> None:
    set_seed(args.seed)
    model, tokenizer = load_model(args.init_checkpoint)
    train_ds = SuperfamilyDataset(str(Path(args.data_dir) / "train/data.jsonl.gz"), tokenizer, args.window)
    val_ds = SuperfamilyDataset(str(Path(args.data_dir) / "val/data.jsonl.gz"), tokenizer, args.window, args.max_eval_samples)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    targs = TrainingArguments(
        output_dir=str(out / "checkpoints"),
        overwrite_output_dir=True,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        warmup_ratio=0.1,
        weight_decay=0.01,
        max_steps=args.max_steps,
        num_train_epochs=1 if args.max_steps > 0 else args.epochs,
        eval_strategy="steps",
        save_strategy="steps",
        eval_steps=args.eval_steps,
        save_steps=args.eval_steps,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="main4_conditional_macro_f1",
        greater_is_better=True,
        logging_steps=50,
        bf16=args.bf16,
        gradient_checkpointing=args.gradient_checkpointing,
        seed=args.seed,
        report_to="none",
        remove_unused_columns=False,
        save_safetensors=False,
    )
    trainer = WeightedTrainer(model=model, args=targs, train_dataset=train_ds, eval_dataset=val_ds,
                              compute_metrics=compute_metrics, data_collator=default_data_collator)
    trainer.train()
    best = out / "best_model"
    trainer.save_model(str(best))
    tokenizer.save_pretrained(str(best))
    meta = vars(args).copy()
    meta["n_train_windows"] = len(train_ds)
    meta["n_val_windows"] = len(val_ds)
    (out / "training_meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    test_path = Path(args.data_dir) / "test/data.jsonl.gz"
    if test_path.exists():
        test_ds = SuperfamilyDataset(str(test_path), tokenizer, args.window, args.max_eval_samples)
        pred = trainer.predict(test_ds)
        result = compute_metrics((pred.predictions, pred.label_ids))
        result.update({"stage": args.stage, "window": args.window, "n_windows": len(test_ds), "init_checkpoint": args.init_checkpoint})
        (out / "test_results.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


def evaluate(args) -> None:
    model, tokenizer = load_model(str(Path(args.model_dir) / "best_model"))
    ds = SuperfamilyDataset(str(Path(args.data_dir) / "test/data.jsonl.gz"), tokenizer, args.window, args.max_samples)
    targs = TrainingArguments(output_dir=str(Path(args.out_json).parent / "_tmp_sf5_eval"),
                              per_device_eval_batch_size=args.batch_size, report_to="none", remove_unused_columns=False)
    trainer = WeightedTrainer(model=model, args=targs, compute_metrics=compute_metrics, data_collator=default_data_collator)
    pred = trainer.predict(ds)
    result = compute_metrics((pred.predictions, pred.label_ids))
    result.update({"model_dir": args.model_dir, "data_dir": args.data_dir, "window": args.window, "n_windows": len(ds)})
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("train")
    p.add_argument("--init-checkpoint", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--window", type=int, required=True)
    p.add_argument("--stage", default="animal_sf5")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=2e-5)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--max-steps", type=int, default=900)
    p.add_argument("--eval-steps", type=int, default=150)
    p.add_argument("--max-eval-samples", type=int, default=1200)
    p.add_argument("--bf16", action="store_true")
    p.add_argument("--gradient-checkpointing", action="store_true")
    p = sub.add_parser("eval")
    p.add_argument("--model-dir", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--window", type=int, required=True)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--max-samples", type=int, default=1200)
    args = ap.parse_args()
    if args.cmd == "train":
        train(args)
    elif args.cmd == "eval":
        evaluate(args)


if __name__ == "__main__":
    main()
