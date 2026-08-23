#!/usr/bin/env python3
"""Smoke, train, and evaluate binary TE token classifiers."""
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
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset
from transformers import (
    AutoModel,
    AutoModelForMaskedLM,
    AutoModelForTokenClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    default_data_collator,
    set_seed,
)
from transformers.modeling_outputs import TokenClassifierOutput


class WindowDataset(Dataset):
    def __init__(self, jsonl_gz: str, tokenizer, window: int, label_mode: str, max_samples: int | None = None):
        self.records = []
        with gzip.open(jsonl_gz, "rt") as handle:
            for i, line in enumerate(handle):
                if max_samples is not None and i >= max_samples:
                    break
                self.records.append(json.loads(line))
        self.tokenizer = tokenizer
        self.window = window
        self.label_mode = label_mode

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        rec = self.records[idx]
        seq = rec["sequence"][:self.window]
        labels = rec["labels"][:self.window]
        enc, token_labels = self.encode_labels(seq, labels)
        return {
            "input_ids": torch.tensor(enc["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(enc.get("attention_mask", [1] * len(enc["input_ids"])), dtype=torch.long),
            "labels": torch.tensor(token_labels, dtype=torch.long),
        }

    def encode_labels(self, seq: str, labels: list[int]):
        if self.label_mode == "ntv3_single":
            max_len = self.window
            enc = self.tokenizer(seq, truncation=True, max_length=max_len, padding="max_length")
            token_labels = labels[:self.window]
            token_labels.extend([-100] * (max_len - len(token_labels)))
            return enc, token_labels[:max_len]

        if self.label_mode == "single_nt_nospecial":
            max_len = self.window
            enc = self.tokenizer(
                seq,
                add_special_tokens=False,
                truncation=True,
                max_length=max_len,
                padding="max_length",
            )
            token_labels = labels[:max_len]
            token_labels.extend([-100] * (max_len - len(token_labels)))
            assert len(enc["input_ids"]) == len(token_labels) == max_len
            return enc, token_labels

        if self.label_mode == "single_nt":
            max_len = self.window + 2
            enc = self.tokenizer(seq, truncation=True, max_length=max_len, padding="max_length")
            token_labels = [-100] + labels[:self.window] + [-100]
            token_labels.extend([-100] * (max_len - len(token_labels)))
            return enc, token_labels[:max_len]

        max_len = self.window
        if self.label_mode in {"nt_kmer", "offset_or_kmer"}:
            max_len = ((self.window + 5) // 6 + 2 + 7) // 8 * 8

        try:
            enc = self.tokenizer(
                seq, truncation=True, max_length=max_len, padding="max_length",
                return_offsets_mapping=True,
            )
            offsets = enc.pop("offset_mapping")
            token_labels = []
            for start, end in offsets:
                if start == end:
                    token_labels.append(-100)
                else:
                    span = labels[start:end]
                    known = [x for x in span if x >= 0]
                    if not known:
                        token_labels.append(-100)
                    else:
                        token_labels.append(1 if sum(known) > len(known) / 2 else 0)
            return enc, token_labels
        except Exception:
            enc = self.tokenizer(seq, truncation=True, max_length=max_len, padding="max_length")
            raw_tokens = self.tokenizer.tokenize(seq)
            token_labels = [-100]
            pos = 0
            for tok in raw_tokens:
                if len(token_labels) >= max_len - 1:
                    break
                k = max(1, len(tok.replace(" ", "")))
                span = labels[pos:pos + k]
                known = [x for x in span if x >= 0]
                if not known:
                    token_labels.append(-100)
                else:
                    token_labels.append(1 if sum(known) > len(known) / 2 else 0)
                pos += k
            token_labels.append(-100)
            token_labels.extend([-100] * (max_len - len(token_labels)))
            return enc, token_labels[:max_len]


class WrappedTokenClassifier(nn.Module):
    def __init__(self, model_path: str, kind: str, num_labels: int = 2, dropout: float = 0.1):
        super().__init__()
        local_files_only = os.environ.get("TEFM_LOCAL_FILES_ONLY", "1") != "0"
        common = {"trust_remote_code": True, "local_files_only": local_files_only}
        if kind == "wrapper_mlm":
            self.backbone = AutoModelForMaskedLM.from_pretrained(model_path, **common)
        else:
            self.backbone = AutoModel.from_pretrained(model_path, **common)
        hidden = getattr(self.backbone.config, "hidden_size", None)
        if hidden is None:
            hidden = getattr(self.backbone.config, "d_model", None)
        if hidden is None:
            hidden = getattr(self.backbone.config, "embed_dim", None)
        if hidden is None:
            raise ValueError("Cannot infer hidden size from backbone config")
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden, num_labels)
        self.kind = kind

    def forward(self, input_ids=None, attention_mask=None, **kwargs):
        if self.kind == "wrapper_mlm":
            out = self.backbone(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)
            hidden = out.hidden_states[-1]
        else:
            try:
                out = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
            except TypeError as exc:
                if "attention_mask" not in str(exc):
                    raise
                out = self.backbone(input_ids=input_ids)
            hidden = out[0] if isinstance(out, tuple) else out.last_hidden_state
        logits = self.classifier(self.dropout(hidden))
        return TokenClassifierOutput(logits=logits)

    def gradient_checkpointing_enable(self, *args, **kwargs):
        if hasattr(self.backbone, "gradient_checkpointing_enable"):
            try:
                return self.backbone.gradient_checkpointing_enable(*args, **kwargs)
            except ValueError as exc:
                print(f"[warn] gradient checkpointing disabled for wrapper backbone: {exc}", flush=True)
                return None

    def gradient_checkpointing_disable(self):
        if hasattr(self.backbone, "gradient_checkpointing_disable"):
            return self.backbone.gradient_checkpointing_disable()


class WeightedTrainer(Trainer):
    def __init__(
        self,
        *args,
        te_class_weight: float = 3.0,
        structure_aux: bool = False,
        boundary_distance_weight: float = 0.0,
        run_contrastive_weight: float = 0.0,
        boundary_distance_cap: int = 256,
        run_temperature: float = 0.07,
        run_min_separation: int = 64,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.te_weight = torch.tensor([1.0, te_class_weight])
        self.structure_aux = structure_aux
        self.boundary_distance_weight = boundary_distance_weight
        self.run_contrastive_weight = run_contrastive_weight
        self.boundary_distance_cap = boundary_distance_cap
        self.run_temperature = run_temperature
        self.run_min_separation = run_min_separation
        self.structure_stats = {
            "train_batches": 0,
            "boundary_targets": 0,
            "contrastive_anchors": 0,
            "contrastive_runs": 0,
            "boundary_loss_sum": 0.0,
            "contrastive_loss_sum": 0.0,
        }

    def run_geometry(self, labels: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        positive = labels.eq(1)
        starts = positive & ~torch.cat([torch.zeros_like(positive[:, :1]), positive[:, :-1]], dim=1)
        stops = positive & ~torch.cat([positive[:, 1:], torch.zeros_like(positive[:, :1])], dim=1)
        run_ids = torch.cumsum(starts.long(), dim=1) - 1
        run_ids[~positive] = -1
        positions = torch.arange(labels.shape[1], device=labels.device)[None, :].expand_as(labels)
        start_positions = torch.cummax(torch.where(starts, positions, -1), dim=1).values
        stop_seeds = torch.where(stops, positions, labels.shape[1])
        stop_positions = torch.flip(torch.cummin(torch.flip(stop_seeds, dims=[1]), dim=1).values, dims=[1])
        left_index = (start_positions - 1).clamp_min(0)
        right_index = (stop_positions + 1).clamp_max(labels.shape[1] - 1)
        left_valid = positive & start_positions.gt(0) & labels.gather(1, left_index).eq(0)
        right_valid = positive & stop_positions.lt(labels.shape[1] - 1) & labels.gather(1, right_index).eq(0)
        run_ids = run_ids + torch.arange(labels.shape[0], device=labels.device)[:, None] * (labels.shape[1] + 1)
        run_ids[~positive] = -1
        return run_ids, start_positions, stop_positions, left_valid, right_valid

    def boundary_distance_loss(self, hidden: torch.Tensor, geometry, model) -> tuple[torch.Tensor, int]:
        _, start_positions, stop_positions, left_valid, right_valid = geometry
        positions = torch.arange(hidden.shape[1], device=hidden.device)[None, :]
        targets = torch.stack(
            [
                (positions - start_positions).clamp(0, self.boundary_distance_cap),
                (stop_positions - positions).clamp(0, self.boundary_distance_cap),
            ],
            dim=-1,
        ).to(hidden.dtype) / float(self.boundary_distance_cap)
        mask = torch.stack([left_valid, right_valid], dim=-1)
        predictions = model.boundary_distance_head(hidden)
        if not mask.any():
            return hidden.sum() * 0.0, 0
        return F.smooth_l1_loss(predictions[mask], targets[mask]), int(mask.sum())

    def run_contrastive_loss(self, hidden: torch.Tensor, geometry) -> tuple[torch.Tensor, int, int]:
        run_ids, start_positions, stop_positions, _, _ = geometry
        positions = torch.arange(hidden.shape[1], device=hidden.device)[None, :]
        run_length = stop_positions - start_positions + 1
        within_run = positions - start_positions
        sample_step = torch.div(run_length + 7, 8, rounding_mode="floor").clamp_min(1)
        selected = run_ids.ge(0) & run_length.gt(self.run_min_separation) & torch.remainder(within_run, sample_step).eq(0)
        coordinates = torch.nonzero(selected, as_tuple=False)[:256]
        if coordinates.shape[0] == 0:
            return hidden.sum() * 0.0, 0, 0
        group = run_ids[coordinates[:, 0], coordinates[:, 1]]
        group_count = int(torch.unique(group).numel())
        if group_count < 2:
            return hidden.sum() * 0.0, 0, group_count
        representation = F.normalize(hidden[coordinates[:, 0], coordinates[:, 1]], dim=-1)
        logits = representation @ representation.T / self.run_temperature
        self_mask = torch.eye(logits.shape[0], dtype=torch.bool, device=hidden.device)
        positive_mask = group[:, None].eq(group[None, :]) & ~self_mask
        denominator = logits.masked_fill(self_mask, float("-inf")).logsumexp(dim=1)
        valid = positive_mask.any(dim=1)
        log_probability = logits - denominator[:, None]
        positive_log_probability = log_probability.masked_fill(~positive_mask, 0.0).sum(dim=1) / positive_mask.sum(dim=1).clamp_min(1)
        loss = -positive_log_probability[valid].mean()
        return loss, int(valid.sum()), group_count

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        if self.structure_aux:
            base_outputs = model.model(**inputs, output_hidden_states=True, return_dict=True)
            hidden = base_outputs.hidden_states[model.feature_layer]
            outputs = TokenClassifierOutput(logits=model.score(hidden), hidden_states=base_outputs.hidden_states)
        else:
            outputs = model(**inputs)
        loss_fn = torch.nn.CrossEntropyLoss(weight=self.te_weight.to(outputs.logits.device), ignore_index=-100)
        loss = loss_fn(outputs.logits.reshape(-1, 2), labels.reshape(-1))
        if self.structure_aux:
            geometry = self.run_geometry(labels)
            boundary_loss, boundary_targets = self.boundary_distance_loss(hidden, geometry, model)
            contrastive_loss, anchors, runs = self.run_contrastive_loss(hidden, geometry)
            loss = loss + self.boundary_distance_weight * boundary_loss + self.run_contrastive_weight * contrastive_loss
            self.structure_stats["train_batches"] += 1
            self.structure_stats["boundary_targets"] += boundary_targets
            self.structure_stats["contrastive_anchors"] += anchors
            self.structure_stats["contrastive_runs"] += runs
            self.structure_stats["boundary_loss_sum"] += float(boundary_loss.detach())
            self.structure_stats["contrastive_loss_sum"] += float(contrastive_loss.detach())
        return (loss, outputs) if return_outputs else loss

    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        inputs = self._prepare_inputs(inputs)
        labels = inputs.pop("labels", None)
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits.detach()
        loss = None
        if labels is not None:
            loss_fn = torch.nn.CrossEntropyLoss(weight=self.te_weight.to(logits.device), ignore_index=-100)
            loss = loss_fn(logits.reshape(-1, 2), labels.reshape(-1)).detach()
        if prediction_loss_only:
            return loss, None, None
        return loss, logits, labels


def metrics(eval_pred):
    logits, labels = eval_pred
    probs = torch.softmax(torch.tensor(logits), dim=-1).numpy()[..., 1]
    pred = np.argmax(logits, axis=-1)
    mask = labels != -100
    y_true = labels[mask].flatten()
    y_pred = pred[mask].flatten()
    y_prob = probs[mask].flatten()
    scores = {}
    f1s = []
    for label, name in [(0, "bg"), (1, "te")]:
        tp = int(((y_true == label) & (y_pred == label)).sum())
        fp = int(((y_true != label) & (y_pred == label)).sum())
        fn = int(((y_true == label) & (y_pred != label)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores[f"{name}_precision"] = precision
        scores[f"{name}_recall"] = recall
        scores[f"{name}_f1"] = f1
        f1s.append(f1)
    auprc = average_precision_binary(y_true, y_prob)
    return {
        "primary_metric": "te_f1",
        "metric_direction": "higher_is_better",
        "te_precision": float(scores["te_precision"]),
        "te_recall": float(scores["te_recall"]),
        "te_f1": float(scores["te_f1"]),
        "bg_f1": float(scores["bg_f1"]),
        "macro_f1": float(sum(f1s) / len(f1s)),
        "te_auprc": float(auprc),
        "n_labeled_tokens": int(mask.sum()),
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


def load_tokenizer(model_path: str):
    local_files_only = os.environ.get("TEFM_LOCAL_FILES_ONLY", "1") != "0"
    return AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, local_files_only=local_files_only)


def build_model(model_path: str, kind: str):
    local_files_only = os.environ.get("TEFM_LOCAL_FILES_ONLY", "1") != "0"
    if kind == "auto_token":
        return AutoModelForTokenClassification.from_pretrained(
            model_path, num_labels=2, trust_remote_code=True, local_files_only=local_files_only, ignore_mismatched_sizes=True
        )
    if kind in {"wrapper_auto", "wrapper_mlm"}:
        return WrappedTokenClassifier(model_path, kind)
    raise ValueError(f"Unsupported model kind for training: {kind}")


def load_trained_model(model_dir: str):
    meta = json.loads(Path(model_dir, "training_meta.json").read_text())
    best = Path(model_dir) / "best_model"
    if meta["kind"] == "auto_token":
        model = build_model(meta["model_path"], meta["kind"])
        state_path = best / "pytorch_model.bin"
        if state_path.exists():
            state = torch.load(state_path, map_location="cpu")
        else:
            from safetensors.torch import load_file

            state = load_file(str(best / "model.safetensors"))
        missing, unexpected = model.load_state_dict(state, strict=False)
        if missing or unexpected:
            print(
                f"[warn] loaded auto_token checkpoint with missing={len(missing)} unexpected={len(unexpected)}",
                flush=True,
            )
    else:
        model = WrappedTokenClassifier(meta["model_path"], meta["kind"])
        state = torch.load(best / "model_state.pt", map_location="cpu")
        cache_suffixes = (
            "rotary_embedding.cos_cached",
            "rotary_embedding.sin_cached",
        )
        state = {k: v for k, v in state.items() if not k.endswith(cache_suffixes)}
        model.load_state_dict(state)
    tokenizer = load_tokenizer(str(best) if (best / "tokenizer_config.json").exists() else meta["model_path"])
    return model, tokenizer, meta


def command_smoke(args) -> None:
    result = {"model_path": args.model_path, "kind": args.kind, "ok": False}
    try:
        tokenizer = load_tokenizer(args.model_path)
        result["tokenizer_class"] = tokenizer.__class__.__name__
        if args.kind == "smoke_only":
            raise RuntimeError("No HF tokenizer/classifier adapter declared for this checkpoint")
        model = build_model(args.model_path, args.kind)
        result["model_class"] = model.__class__.__name__
        result["n_params"] = int(sum(p.numel() for p in model.parameters()))
        result["ok"] = True
    except Exception as exc:
        result["error"] = repr(exc)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        raise SystemExit(2)


def command_train(args) -> None:
    set_seed(args.seed)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    init_model_path = args.model_path
    init_meta_path = Path(init_model_path) / "training_meta.json"
    if init_meta_path.exists():
        model, tokenizer, init_meta = load_trained_model(init_model_path)
        args.model_path = init_meta["model_path"]
        args.kind = init_meta["kind"]
        args.token_label_mode = init_meta["token_label_mode"]
    else:
        tokenizer = load_tokenizer(args.model_path)
        model = build_model(args.model_path, args.kind)
    if args.structure_aux:
        if args.kind != "auto_token":
            raise ValueError("structure-aware training currently requires kind=auto_token")
        model.boundary_distance_head = nn.Linear(model.config.hidden_size, 2)
    train = WindowDataset(str(Path(args.data_dir) / "train/data.jsonl.gz"), tokenizer, args.window, args.token_label_mode)
    val = WindowDataset(str(Path(args.data_dir) / "val/data.jsonl.gz"), tokenizer, args.window, args.token_label_mode, args.max_eval_samples)
    probe = train[0]
    input_geometry = {
        "raw_bp": len(train.records[0]["sequence"][: args.window]),
        "input_tokens": int(probe["attention_mask"].sum()),
        "tensor_tokens": int(probe["input_ids"].numel()),
        "labeled_tokens": int(probe["labels"].ne(-100).sum()),
        "bos_tokens": int(probe["input_ids"].eq(tokenizer.bos_token_id).sum()) if tokenizer.bos_token_id is not None else 0,
        "eos_tokens": int(probe["input_ids"].eq(tokenizer.eos_token_id).sum()) if tokenizer.eos_token_id is not None else 0,
        "first_label": int(probe["labels"][0]),
        "last_label": int(probe["labels"][-1]),
    }
    print(json.dumps({"input_geometry": input_geometry}, indent=2), flush=True)
    targs = TrainingArguments(
        output_dir=str(out / "checkpoints"),
        overwrite_output_dir=True,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=max(1, args.batch_size),
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
        save_safetensors=False,
        load_best_model_at_end=not args.fixed_final_checkpoint,
        metric_for_best_model="te_f1",
        greater_is_better=True,
        logging_steps=50,
        bf16=args.bf16,
        fp16=False,
        gradient_checkpointing=args.gradient_checkpointing,
        seed=args.seed,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = WeightedTrainer(
        model=model,
        args=targs,
        train_dataset=train,
        eval_dataset=val,
        compute_metrics=metrics,
        data_collator=default_data_collator,
        te_class_weight=args.te_class_weight,
        structure_aux=args.structure_aux,
        boundary_distance_weight=args.boundary_distance_weight,
        run_contrastive_weight=args.run_contrastive_weight,
        boundary_distance_cap=args.boundary_distance_cap,
        run_temperature=args.run_temperature,
        run_min_separation=args.run_min_separation,
    )
    trainer.train()
    best = out / "best_model"
    best.mkdir(parents=True, exist_ok=True)
    if args.kind == "auto_token":
        if args.structure_aux:
            del model.boundary_distance_head
        trainer.save_model(str(best))
    else:
        torch.save(model.state_dict(), best / "model_state.pt")
    tokenizer.save_pretrained(str(best))
    meta = vars(args).copy()
    if init_meta_path.exists():
        meta["init_model_path"] = init_model_path
    meta["n_train_windows"] = len(train)
    meta["n_val_windows"] = len(val)
    meta["input_geometry"] = input_geometry
    if args.structure_aux:
        meta["structure_stats"] = trainer.structure_stats
    (out / "training_meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    if (Path(args.data_dir) / "test/data.jsonl.gz").exists():
        test = WindowDataset(str(Path(args.data_dir) / "test/data.jsonl.gz"), tokenizer, args.window, args.token_label_mode, args.max_eval_samples)
        pred = trainer.predict(test)
        out_metrics = metrics((pred.predictions, pred.label_ids))
        (out / "test_results.json").write_text(json.dumps(out_metrics, indent=2) + "\n")


def command_eval(args) -> None:
    model, tokenizer, meta = load_trained_model(args.model_dir)
    data = Path(args.data_dir)
    jsonl = data / "test/data.jsonl.gz"
    ds = WindowDataset(str(jsonl), tokenizer, int(meta["window"]), meta["token_label_mode"], args.max_samples)
    targs = TrainingArguments(
        output_dir=str(Path(args.out_json).parent / "_tmp_eval"),
        per_device_eval_batch_size=args.batch_size,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = WeightedTrainer(model=model, args=targs, compute_metrics=metrics, data_collator=default_data_collator)
    pred = trainer.predict(ds)
    result = metrics((pred.predictions, pred.label_ids))
    result.update({"model_dir": args.model_dir, "data_dir": args.data_dir, "n_windows": len(ds)})
    for key in ["stage", "model_key", "model", "window", "species"]:
        value = getattr(args, key)
        if value is not None:
            result[key] = value
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("smoke")
    p.add_argument("--model-path", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--out-json", required=True)
    p = sub.add_parser("train")
    p.add_argument("--model-path", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--token-label-mode", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--window", type=int, required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=2e-5)
    p.add_argument("--te-class-weight", type=float, default=3.0)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--max-steps", type=int, default=1200)
    p.add_argument("--eval-steps", type=int, default=200)
    p.add_argument("--max-eval-samples", type=int, default=1200)
    p.add_argument("--bf16", action="store_true")
    p.add_argument("--gradient-checkpointing", action="store_true")
    p.add_argument("--fixed-final-checkpoint", action="store_true")
    p.add_argument("--structure-aux", action="store_true")
    p.add_argument("--boundary-distance-weight", type=float, default=0.0)
    p.add_argument("--run-contrastive-weight", type=float, default=0.0)
    p.add_argument("--boundary-distance-cap", type=int, default=256)
    p.add_argument("--run-temperature", type=float, default=0.07)
    p.add_argument("--run-min-separation", type=int, default=64)
    p = sub.add_parser("eval")
    p.add_argument("--model-dir", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--max-samples", type=int, default=1200)
    p.add_argument("--stage")
    p.add_argument("--model-key")
    p.add_argument("--model")
    p.add_argument("--window", type=int)
    p.add_argument("--species")
    args = parser.parse_args()
    if args.cmd == "smoke":
        command_smoke(args)
    elif args.cmd == "train":
        command_train(args)
    elif args.cmd == "eval":
        command_eval(args)


if __name__ == "__main__":
    main()
