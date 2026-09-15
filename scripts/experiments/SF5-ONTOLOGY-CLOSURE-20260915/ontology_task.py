#!/usr/bin/env python3
"""Train and evaluate the seed-42 SF5 ontology-closure classifier.

The old SF5 head has six labels and a mixed ``Unknown`` bucket.  This file
uses a new eight-label head and never changes the old checkpoint or scores.
Validation and test defaults intentionally consume the complete six-species
files so that a prefix limit cannot silently reappear.
"""
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
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    default_data_collator,
    set_seed,
)


ID2LABEL = {
    0: "BG",
    1: "SINE",
    2: "LINE",
    3: "LTR",
    4: "DNA",
    5: "KNOWN_OTHER_TE",
    6: "AMBIGUOUS_TE",
    7: "UNCLASSIFIED",
}
NUM_LABELS = len(ID2LABEL)
MAIN4 = {1, 2, 3, 4}
STATUS = {5, 6, 7}
# Fixed before training; no validation-derived class reweighting is used.
CLASS_WEIGHTS = [1.0, 3.0, 3.0, 3.0, 3.0, 3.0, 2.0, 2.0]


class OntologyDataset(Dataset):
    def __init__(self, jsonl_gz: str, tokenizer, window: int, max_samples: int | None = None):
        self.records = []
        with gzip.open(jsonl_gz, "rt") as handle:
            for i, line in enumerate(handle):
                if max_samples is not None and i >= max_samples:
                    break
                self.records.append(json.loads(line))
        self.tokenizer = tokenizer
        self.window = window

    @property
    def species(self) -> list[str]:
        return [str(rec.get("species_code", "unknown")) for rec in self.records]

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx: int):
        rec = self.records[idx]
        seq = rec["sequence"][: self.window]
        labels = [int(x) for x in rec["labels"][: self.window]]
        if len(seq) != self.window or len(labels) != self.window:
            raise ValueError(f"record {idx} does not have exactly {self.window} bases")
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


def safe_prf(y_true: np.ndarray, y_pred: np.ndarray, label: int) -> tuple[float, float, float, int, int, int, int]:
    tp = int(((y_true == label) & (y_pred == label)).sum())
    fp = int(((y_true != label) & (y_pred == label)).sum())
    fn = int(((y_true == label) & (y_pred != label)).sum())
    support = int((y_true == label).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1, support, tp, fp, fn


def metrics_from_arrays(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    out: dict[str, object] = {}
    all_f1 = []
    main4_f1 = []
    status_f1 = []
    for label, name in ID2LABEL.items():
        precision, recall, f1, support, tp, fp, fn = safe_prf(y_true, y_pred, label)
        key = name.lower()
        out[f"{key}_precision"] = precision
        out[f"{key}_recall"] = recall
        out[f"{key}_f1"] = f1
        out[f"{key}_support"] = support
        out[f"{key}_tp"] = tp
        out[f"{key}_fp"] = fp
        out[f"{key}_fn"] = fn
        if support > 0:
            all_f1.append(f1)
            if label in MAIN4:
                main4_f1.append(f1)
            if label in STATUS:
                status_f1.append(f1)

    true_material = (y_true != 0).astype(np.int8)
    pred_material = (y_pred != 0).astype(np.int8)
    material_p, material_r, material_f1, material_support, _, _, _ = safe_prf(
        true_material, pred_material, 1
    )
    out.update(
        {
            "ontology_macro_f1": float(np.mean(all_f1)) if all_f1 else 0.0,
            "main4_macro_f1": float(np.mean(main4_f1)) if main4_f1 else 0.0,
            "status_macro_f1": float(np.mean(status_f1)) if status_f1 else 0.0,
            "material_precision": material_p,
            "material_recall": material_r,
            "material_f1": material_f1,
            "material_support": material_support,
            "accuracy": float((y_true == y_pred).mean()) if y_true.size else 0.0,
            "support_total": int(y_true.size),
        }
    )
    pred_counts = collections.Counter(y_pred.tolist())
    total = max(1, int(y_pred.size))
    for label, name in ID2LABEL.items():
        out[f"pred_{name.lower()}_ratio"] = pred_counts.get(label, 0) / total
    return out


def metrics_from_prediction(predictions, label_ids, species: list[str] | None = None) -> dict:
    logits = predictions[0] if isinstance(predictions, tuple) else predictions
    pred = np.argmax(logits, axis=-1)
    labels = np.asarray(label_ids)
    mask = labels != -100
    y_true = labels[mask].astype(np.int64)
    y_pred = pred[mask].astype(np.int64)
    result = {"aggregate": metrics_from_arrays(y_true, y_pred)}
    if species is not None:
        token_species = np.repeat(np.asarray(species, dtype=object), labels.shape[1])
        flat_species = token_species[mask.reshape(-1)]
        by_species = {}
        for current in species:
            select = flat_species == current
            if select.any():
                by_species[current] = metrics_from_arrays(y_true[select], y_pred[select])
        result["per_species"] = by_species
    return result


class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = torch.tensor(class_weights or CLASS_WEIGHTS, dtype=torch.float32)

    def _loss(self, logits, labels):
        loss_fn = torch.nn.CrossEntropyLoss(
            weight=self.class_weights.to(logits.device), ignore_index=-100
        )
        return loss_fn(logits.reshape(-1, NUM_LABELS), labels.reshape(-1))

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss = self._loss(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss

    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        inputs = self._prepare_inputs(inputs)
        labels = inputs.pop("labels", None)
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits.detach()
        loss = self._loss(logits, labels).detach() if labels is not None else None
        if prediction_loss_only:
            return loss, None, None
        return loss, logits, labels


def load_model(checkpoint: str):
    tokenizer = AutoTokenizer.from_pretrained(
        checkpoint, trust_remote_code=True, local_files_only=True
    )
    label2id = {name: idx for idx, name in ID2LABEL.items()}
    model = AutoModelForTokenClassification.from_pretrained(
        checkpoint,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=label2id,
        trust_remote_code=True,
        local_files_only=True,
        ignore_mismatched_sizes=True,
    )
    return model, tokenizer


def _dataset(data_dir: str, split: str, tokenizer, window: int, max_samples: int | None):
    return OntologyDataset(
        str(Path(data_dir) / split / "data.jsonl.gz"), tokenizer, window, max_samples
    )


def train(args) -> None:
    set_seed(args.seed)
    model, tokenizer = load_model(args.init_checkpoint)
    train_ds = _dataset(args.data_dir, "train", tokenizer, args.window, None)
    val_ds = _dataset(args.data_dir, "val", tokenizer, args.window, args.max_val_samples)
    if args.max_val_samples is not None and len(val_ds) != args.max_val_samples:
        raise RuntimeError(f"validation prefix shorter than requested: {len(val_ds)}")
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
        metric_for_best_model="ontology_macro_f1",
        greater_is_better=True,
        logging_steps=50,
        bf16=args.bf16,
        gradient_checkpointing=args.gradient_checkpointing,
        seed=args.seed,
        report_to="none",
        remove_unused_columns=False,
        save_safetensors=False,
    )
    trainer = WeightedTrainer(
        model=model,
        args=targs,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=lambda pred: metrics_from_prediction(pred.predictions, pred.label_ids)[
            "aggregate"
        ],
        data_collator=default_data_collator,
        class_weights=CLASS_WEIGHTS,
    )
    trainer.train()
    best = out / "best_model"
    trainer.save_model(str(best))
    tokenizer.save_pretrained(str(best))

    val_result = trainer.predict(val_ds)
    validation = metrics_from_prediction(val_result.predictions, val_result.label_ids, val_ds.species)
    test_ds = _dataset(args.data_dir, "test", tokenizer, args.window, args.max_test_samples)
    test_result = trainer.predict(test_ds)
    testing = metrics_from_prediction(test_result.predictions, test_result.label_ids, test_ds.species)
    meta = vars(args).copy()
    meta.update(
        {
            "protocol": "SF5_ONTOLOGY_CLOSURE_20260915",
            "label_map": {str(k): v for k, v in ID2LABEL.items()},
            "class_weights": CLASS_WEIGHTS,
            "n_train_windows": len(train_ds),
            "n_val_windows": len(val_ds),
            "n_test_windows": len(test_ds),
            "best_model_checkpoint": trainer.state.best_model_checkpoint,
            "best_metric": trainer.state.best_metric,
        }
    )
    (out / "training_meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    (out / "validation_results.json").write_text(json.dumps(validation, indent=2) + "\n")
    (out / "test_results.json").write_text(json.dumps(testing, indent=2) + "\n")
    print(json.dumps({"validation": validation, "test": testing, "meta": meta}, indent=2, default=str))


def evaluate(args) -> None:
    model, tokenizer = load_model(str(Path(args.model_dir) / "best_model"))
    ds = _dataset(args.data_dir, "test", tokenizer, args.window, args.max_samples)
    targs = TrainingArguments(
        output_dir=str(Path(args.out_json).parent / "_tmp_ontology_eval"),
        per_device_eval_batch_size=args.batch_size,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = WeightedTrainer(
        model=model,
        args=targs,
        compute_metrics=lambda pred: metrics_from_prediction(pred.predictions, pred.label_ids)[
            "aggregate"
        ],
        data_collator=default_data_collator,
        class_weights=CLASS_WEIGHTS,
    )
    result = trainer.predict(ds)
    metrics = metrics_from_prediction(result.predictions, result.label_ids, ds.species)
    metrics.update(
        {
            "protocol": "SF5_ONTOLOGY_CLOSURE_20260915",
            "model_dir": args.model_dir,
            "data_dir": args.data_dir,
            "window": args.window,
            "n_windows": len(ds),
        }
    )
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("train")
    p.add_argument("--init-checkpoint", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--window", type=int, default=4096)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=2e-5)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--max-steps", type=int, default=900)
    p.add_argument("--eval-steps", type=int, default=150)
    p.add_argument("--max-val-samples", type=int, default=None)
    p.add_argument("--max-test-samples", type=int, default=None)
    p.add_argument("--bf16", action="store_true")
    p.add_argument("--gradient-checkpointing", action="store_true")
    p = sub.add_parser("eval")
    p.add_argument("--model-dir", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--window", type=int, default=4096)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--max-samples", type=int, default=None)
    args = ap.parse_args()
    if args.cmd == "train":
        train(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
