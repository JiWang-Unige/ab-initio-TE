#!/usr/bin/env python3
"""Train/evaluate binary TE token classifiers with positive-unlabeled labels."""
from __future__ import annotations

import argparse
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


class PUDataset(Dataset):
    def __init__(self, jsonl_gz: str, tokenizer, window: int, max_samples: int | None = None):
        self.records = []
        with gzip.open(jsonl_gz, "rt") as handle:
            for i, line in enumerate(handle):
                if max_samples is not None and i >= max_samples:
                    break
                self.records.append(json.loads(line))
        self.tokenizer = tokenizer
        self.window = window

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        rec = self.records[idx]
        seq = rec["sequence"][:self.window]
        raw_labels = [int(x) for x in rec["labels"][:self.window]]
        max_len = self.window + 2
        enc = self.tokenizer(seq, truncation=True, max_length=max_len, padding="max_length")
        labels = [-100]
        u_mask = [0]
        for x in raw_labels:
            if x < 0:
                labels.append(-100)
                u_mask.append(1)
            else:
                labels.append(x)
                u_mask.append(0)
        labels.append(-100)
        u_mask.append(0)
        labels.extend([-100] * (max_len - len(labels)))
        u_mask.extend([0] * (max_len - len(u_mask)))
        return {
            "input_ids": torch.tensor(enc["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(enc.get("attention_mask", [1] * len(enc["input_ids"])), dtype=torch.long),
            "labels": torch.tensor(labels[:max_len], dtype=torch.long),
            "u_mask": torch.tensor(u_mask[:max_len], dtype=torch.bool),
        }


def average_precision_binary(y_true, y_score) -> float:
    y_true = np.asarray(y_true).astype(int)
    if y_true.size == 0 or int((y_true == 1).sum()) == 0:
        return float("nan")
    order = np.argsort(-np.asarray(y_score))
    y = y_true[order]
    tp = np.cumsum(y == 1)
    fp = np.cumsum(y == 0)
    precision = tp / np.maximum(tp + fp, 1)
    return float((precision * (y == 1)).sum() / max(1, int((y_true == 1).sum())))


def prf(y_true: np.ndarray, y_pred: np.ndarray, label: int) -> tuple[float, float, float]:
    tp = int(((y_true == label) & (y_pred == label)).sum())
    fp = int(((y_true != label) & (y_pred == label)).sum())
    fn = int(((y_true == label) & (y_pred != label)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def metrics(eval_pred):
    logits, labels = eval_pred
    probs = torch.softmax(torch.tensor(logits), dim=-1).numpy()[..., 1]
    pred = np.argmax(logits, axis=-1)
    mask = labels != -100
    y_true = labels[mask].flatten()
    y_pred = pred[mask].flatten()
    y_prob = probs[mask].flatten()
    bg_p, bg_r, bg_f = prf(y_true, y_pred, 0)
    te_p, te_r, te_f = prf(y_true, y_pred, 1)
    out = {
        "primary_metric": "te_f1",
        "metric_direction": "higher_is_better",
        "te_precision": float(te_p),
        "te_recall": float(te_r),
        "te_f1": float(te_f),
        "bg_precision": float(bg_p),
        "bg_recall": float(bg_r),
        "bg_f1": float(bg_f),
        "macro_f1": float((bg_f + te_f) / 2),
        "te_auprc": float(average_precision_binary(y_true, y_prob)),
        "pred_te_rate": float((y_pred == 1).mean()) if y_pred.size else 0.0,
        "true_te_rate": float((y_true == 1).mean()) if y_true.size else 0.0,
        "n_labeled_tokens": int(mask.sum()),
    }
    return out


class PUTrainer(Trainer):
    def __init__(self, *args, te_class_weight: float = 3.0, u_penalty: float = 0.1,
                 tv_weight: float = 0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = torch.tensor([1.0, te_class_weight], dtype=torch.float32)
        self.u_penalty = float(u_penalty)
        self.tv_weight = float(tv_weight)

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        u_mask = inputs.pop("u_mask", None)
        outputs = model(**inputs)
        logits = outputs.logits
        labeled = labels != -100
        loss = logits.sum() * 0.0
        if labeled.any():
            loss_fn = torch.nn.CrossEntropyLoss(weight=self.class_weights.to(logits.device), ignore_index=-100)
            loss = loss + loss_fn(logits.reshape(-1, 2), labels.reshape(-1))
        probs = torch.softmax(logits, dim=-1)[..., 1]
        if u_mask is not None and self.u_penalty > 0 and u_mask.any():
            loss = loss + self.u_penalty * (probs[u_mask] ** 2).mean()
        if self.tv_weight > 0 and probs.shape[1] > 2:
            valid = inputs.get("attention_mask", torch.ones_like(labels)).bool()
            pair = valid[:, 1:] & valid[:, :-1]
            if pair.any():
                tv = torch.abs(probs[:, 1:] - probs[:, :-1])[pair].mean()
                loss = loss + self.tv_weight * tv
        return (loss, outputs) if return_outputs else loss

    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        inputs = self._prepare_inputs(inputs)
        labels = inputs.pop("labels", None)
        inputs.pop("u_mask", None)
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits.detach()
        loss = None
        if labels is not None:
            loss_fn = torch.nn.CrossEntropyLoss(ignore_index=-100)
            loss = loss_fn(logits.reshape(-1, 2), labels.reshape(-1)).detach()
        if prediction_loss_only:
            return loss, None, None
        return loss, logits, labels


def load_model(checkpoint: str):
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True, local_files_only=True)
    model = AutoModelForTokenClassification.from_pretrained(
        checkpoint,
        num_labels=2,
        trust_remote_code=True,
        local_files_only=True,
        ignore_mismatched_sizes=True,
    )
    return model, tokenizer


def train(args) -> None:
    set_seed(args.seed)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model, tokenizer = load_model(args.init_checkpoint)
    train_ds = PUDataset(str(Path(args.data_dir) / "train/data.jsonl.gz"), tokenizer, args.window)
    val_ds = PUDataset(str(Path(args.data_dir) / "val/data.jsonl.gz"), tokenizer, args.window, args.max_eval_samples)
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
        num_train_epochs=1,
        eval_strategy="steps",
        save_strategy="steps",
        eval_steps=args.eval_steps,
        save_steps=args.eval_steps,
        save_total_limit=1,
        load_best_model_at_end=False,
        logging_steps=50,
        bf16=args.bf16,
        gradient_checkpointing=args.gradient_checkpointing,
        seed=args.seed,
        report_to="none",
        remove_unused_columns=False,
        save_safetensors=False,
    )
    trainer = PUTrainer(
        model=model,
        args=targs,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=metrics,
        data_collator=default_data_collator,
        te_class_weight=args.te_class_weight,
        u_penalty=args.u_penalty,
        tv_weight=args.tv_weight,
    )
    trainer.train()
    best = out / "best_model"
    trainer.save_model(str(best))
    tokenizer.save_pretrained(str(best))
    meta = vars(args).copy()
    meta["model_path"] = args.init_checkpoint
    meta["kind"] = "auto_token"
    meta["token_label_mode"] = "single_nt"
    meta["n_train_windows"] = len(train_ds)
    meta["n_val_windows"] = len(val_ds)
    (out / "training_meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")


def evaluate(args) -> None:
    model, tokenizer = load_model(str(Path(args.model_dir) / "best_model"))
    ds = PUDataset(str(Path(args.data_dir) / "test/data.jsonl.gz"), tokenizer, args.window, args.max_samples)
    targs = TrainingArguments(
        output_dir=str(Path(args.out_json).parent / "_tmp_pu_eval"),
        per_device_eval_batch_size=args.batch_size,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = PUTrainer(model=model, args=targs, compute_metrics=metrics, data_collator=default_data_collator)
    pred = trainer.predict(ds)
    result = metrics((pred.predictions, pred.label_ids))
    result.update({
        "model_dir": args.model_dir,
        "data_dir": args.data_dir,
        "stage": args.stage,
        "species": args.species,
        "window": args.window,
        "n_windows": len(ds),
    })
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
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=2e-5)
    p.add_argument("--te-class-weight", type=float, default=3.0)
    p.add_argument("--u-penalty", type=float, default=0.1)
    p.add_argument("--tv-weight", type=float, default=0.0)
    p.add_argument("--max-steps", type=int, default=700)
    p.add_argument("--eval-steps", type=int, default=140)
    p.add_argument("--max-eval-samples", type=int, default=1000)
    p.add_argument("--bf16", action="store_true")
    p.add_argument("--gradient-checkpointing", action="store_true")
    p = sub.add_parser("eval")
    p.add_argument("--model-dir", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--window", type=int, required=True)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--max-samples", type=int, default=1200)
    p.add_argument("--stage", default="")
    p.add_argument("--species", default="")
    args = ap.parse_args()
    if args.cmd == "train":
        train(args)
    elif args.cmd == "eval":
        evaluate(args)


if __name__ == "__main__":
    main()
