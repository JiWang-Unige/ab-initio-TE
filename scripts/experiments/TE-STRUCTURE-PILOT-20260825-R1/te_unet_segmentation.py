#!/usr/bin/env python3
"""Minimal joint backbone + 1D U-Net pilot for comparator-run segmentation."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
from pathlib import Path

WINDOW = 8192
IGNORE = -100


def four_state_labels(binary: list[int]) -> list[int]:
    """Map known binary runs to background/interior/left/right states.

    A boundary state is emitted only when the adjacent base is known
    background. Window edges and unknown-adjacent transitions remain interior;
    they are not evidence for a biological boundary.
    """
    out = [IGNORE if value < 0 else int(value == 1) for value in binary]
    index = 0
    while index < len(binary):
        if binary[index] != 1:
            index += 1
            continue
        start = index
        while index < len(binary) and binary[index] == 1:
            index += 1
        end = index
        if start > 0 and binary[start - 1] == 0:
            out[start] = 2
        if end < len(binary) and binary[end] == 0:
            out[end - 1] = 3
    return out


def iter_jsonl_rows(path: Path, limit: int):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index >= limit:
                break
            yield json.loads(line)


def te_probability(logits):
    """Return P(interior or either boundary) from four-state logits."""
    import torch

    return torch.softmax(logits, dim=-1)[..., 1:].sum(dim=-1)


def runtime():
    import torch
    import torch.nn as nn
    import torch.nn.functional as functional
    from torch.utils.data import Dataset
    from transformers import AutoModel, AutoTokenizer, Trainer, TrainingArguments, default_data_collator, set_seed
    from transformers.modeling_outputs import TokenClassifierOutput

    return torch, nn, functional, Dataset, AutoModel, AutoTokenizer, Trainer, TrainingArguments, default_data_collator, set_seed, TokenClassifierOutput


def model_class():
    torch, nn, functional, _Dataset, AutoModel, _AutoTokenizer, _Trainer, _TrainingArguments, _collator, _seed, TokenClassifierOutput = runtime()

    class TEUNetSegmenter(nn.Module):
        def __init__(self, checkpoint: str, width: int = 128):
            super().__init__()
            local = os.environ.get("TEFM_LOCAL_FILES_ONLY", "1") != "0"
            self.backbone = AutoModel.from_pretrained(checkpoint, trust_remote_code=True, local_files_only=local)
            hidden = getattr(self.backbone.config, "hidden_size", None)
            if hidden is None:
                raise ValueError("backbone config has no hidden_size")
            self.project = nn.Conv1d(hidden, width, 1)
            self.down1 = nn.Conv1d(width, width, 5, stride=2, padding=2)
            self.down2 = nn.Conv1d(width, width, 5, stride=2, padding=2)
            self.up1 = nn.ConvTranspose1d(width, width, 4, stride=2, padding=1)
            self.up2 = nn.ConvTranspose1d(width, width, 4, stride=2, padding=1)
            self.classifier = nn.Conv1d(width, 4, 1)
            self.register_buffer("class_weight", torch.tensor([1.0, 3.0, 3.0, 3.0]))

        def forward(self, input_ids=None, attention_mask=None, labels=None):
            try:
                encoded = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
            except TypeError as exc:
                if "attention_mask" not in str(exc):
                    raise
                encoded = self.backbone(input_ids=input_ids)
            hidden = encoded[0] if isinstance(encoded, tuple) else encoded.last_hidden_state
            skip0 = functional.gelu(self.project(hidden.transpose(1, 2)))
            skip1 = functional.gelu(self.down1(skip0))
            latent = functional.gelu(self.down2(skip1))
            decoded = functional.gelu(self.up1(latent)) + skip1
            decoded = functional.gelu(self.up2(decoded)) + skip0
            logits = self.classifier(decoded).transpose(1, 2)
            loss = None
            if labels is not None:
                loss = functional.cross_entropy(
                    logits.reshape(-1, 4), labels.reshape(-1),
                    weight=self.class_weight, ignore_index=IGNORE,
                )
            return TokenClassifierOutput(loss=loss, logits=logits)

        def gradient_checkpointing_enable(self, *args, **kwargs):
            return self.backbone.gradient_checkpointing_enable(*args, **kwargs)

    return TEUNetSegmenter


def dataset_class():
    torch, _nn, _functional, Dataset, _AutoModel, _AutoTokenizer, _Trainer, _TrainingArguments, _collator, _seed, _output = runtime()

    class FourStateWindowDataset(Dataset):
        def __init__(self, path: Path, tokenizer, limit: int | None = None):
            self.rows = []
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                for index, line in enumerate(handle):
                    if limit is not None and index >= limit:
                        break
                    self.rows.append(json.loads(line))
            self.tokenizer = tokenizer

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, index):
            row = self.rows[index]
            sequence = row["sequence"][:WINDOW]
            labels = row["labels"][:WINDOW]
            encoded = self.tokenizer(
                sequence, add_special_tokens=False, truncation=True,
                max_length=WINDOW, padding="max_length",
            )
            return {
                "input_ids": torch.tensor(encoded["input_ids"], dtype=torch.long),
                "attention_mask": torch.tensor(encoded["attention_mask"], dtype=torch.long),
                "labels": torch.tensor(four_state_labels(labels), dtype=torch.long),
            }

    return FourStateWindowDataset


def train(args) -> None:
    torch, _nn, _functional, _Dataset, _AutoModel, AutoTokenizer, Trainer, TrainingArguments, collator, set_seed, _output = runtime()
    set_seed(args.seed)
    local = os.environ.get("TEFM_LOCAL_FILES_ONLY", "1") != "0"
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, trust_remote_code=True, local_files_only=local)
    DatasetType = dataset_class()
    train_data = DatasetType(args.data_dir / "train" / "data.jsonl.gz", tokenizer)
    validation = DatasetType(args.data_dir / "val" / "data.jsonl.gz", tokenizer, args.max_eval_samples)
    Model = model_class()
    model = Model(str(args.checkpoint), args.width)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir / "trainer_state"),
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=2e-5,
        max_steps=args.max_steps,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_strategy="no",
        logging_steps=20,
        bf16=args.bf16,
        gradient_checkpointing=True,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=train_data,
                      eval_dataset=validation, data_collator=collator)
    trainer.train()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), args.output_dir / "model_state.pt")
    tokenizer.save_pretrained(args.output_dir / "tokenizer")
    (args.output_dir / "training_meta.json").write_text(json.dumps({
        "schema": "comparator_run_four_state_unet_v1",
        "checkpoint": str(args.checkpoint),
        "data_dir": str(args.data_dir),
        "window": WINDOW,
        "states": ["background", "interior", "left_boundary", "right_boundary"],
        "boundary_target": "one nucleotide only when adjacent known background",
        "width": args.width,
        "max_steps": args.max_steps,
        "seed": args.seed,
        "claim_scope": "RepeatMasker-style comparator-run engineering pilot",
    }, indent=2) + "\n", encoding="utf-8")


def _write_canonical(path: Path, rows: list[tuple[str, int, int]], name: str) -> None:
    fields = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for seqid, start, end in rows:
            writer.writerow({
                "seqid": seqid, "start": start, "end": end, "name": name,
                "score": ".", "strand": ".", "source": "P3", "attributes": ".",
            })


def evaluate(args) -> None:
    import numpy as np

    torch, _nn, _functional, _Dataset, _AutoModel, AutoTokenizer, _Trainer, _TrainingArguments, _collator, _seed, _output = runtime()
    final_pipeline = Path(__file__).resolve().parents[3] / "pipelines" / "PIPE-TEFM-FINAL-20260623"
    sys.path.insert(0, str(final_pipeline))
    from strict_segment_eval import (  # type: ignore
        binary_metrics,
        center_weights,
        fragmentation_truth_diagnostics,
        runs_from_bool,
        strict_segment_metrics,
    )

    metadata = json.loads((args.model_dir / "training_meta.json").read_text(encoding="utf-8"))
    local = os.environ.get("TEFM_LOCAL_FILES_ONLY", "1") != "0"
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir / "tokenizer", trust_remote_code=True, local_files_only=local)
    Model = model_class()
    model = Model(metadata["checkpoint"], int(metadata["width"]))
    model.load_state_dict(torch.load(args.model_dir / "model_state.pt", map_location="cpu"))
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model.to(device).eval()

    weights = center_weights(WINDOW, args.weight_mode)
    sums: dict[str, np.ndarray] = {}
    weight_sums: dict[str, np.ndarray] = {}
    truths: dict[str, np.ndarray] = {}
    for row in iter_jsonl_rows(args.data_jsonl, args.max_windows):
            seqid, start, end = row["chr"], int(row["start"]), int(row["end"])
            encoded = tokenizer(
                row["sequence"][:WINDOW], add_special_tokens=False, truncation=True,
                max_length=WINDOW, padding="max_length", return_tensors="pt",
            )
            inputs = {key: value.to(device) for key, value in encoded.items() if key in {"input_ids", "attention_mask"}}
            with torch.no_grad():
                probability = te_probability(model(**inputs).logits)[0].cpu().numpy()[: end - start]
            if seqid not in sums or sums[seqid].size < end:
                old_sum, old_weight, old_truth = sums.get(seqid), weight_sums.get(seqid), truths.get(seqid)
                sums[seqid] = np.zeros(end, dtype=np.float32)
                weight_sums[seqid] = np.zeros(end, dtype=np.float32)
                truths[seqid] = np.full(end, IGNORE, dtype=np.int16)
                if old_sum is not None:
                    sums[seqid][: old_sum.size] = old_sum
                    weight_sums[seqid][: old_weight.size] = old_weight
                    truths[seqid][: old_truth.size] = old_truth
            sums[seqid][start:end] += probability * weights[: end - start]
            weight_sums[seqid][start:end] += weights[: end - start]
            truths[seqid][start:end] = np.asarray(row["labels"][: end - start], dtype=np.int16)

    prediction_rows: list[tuple[str, int, int]] = []
    truth_rows: list[tuple[str, int, int]] = []
    metric_rows: list[dict[str, object]] = []
    lengths: dict[str, int] = {}
    for seqid in sorted(sums):
        valid = weight_sums[seqid] > 0
        end = int(np.nonzero(valid)[0][-1]) + 1
        lengths[seqid] = end
        probability = np.zeros(end, dtype=np.float32)
        probability[valid[:end]] = sums[seqid][:end][valid[:end]] / weight_sums[seqid][:end][valid[:end]]
        truth = truths[seqid][:end]
        known = truth >= 0
        truth_mask = truth == 1
        pred_mask = probability >= args.threshold
        pred_mask[~known] = False
        truth_mask[~known] = False
        prediction_rows.extend((seqid, start, stop) for start, stop in runs_from_bool(pred_mask))
        truth_rows.extend((seqid, start, stop) for start, stop in runs_from_bool(truth_mask))
        for tolerance in (5, 25):
            metrics = {
                "seqid": seqid,
                "threshold": args.threshold,
                "iou_threshold": 0.8,
                "boundary_tol_bp": tolerance,
                "ignored_bp": int((~known).sum()),
            }
            metrics.update(binary_metrics(truth_mask[known], pred_mask[known].astype(np.float32), 0.5))
            metrics.update(strict_segment_metrics(truth_mask, pred_mask, 0.8, tolerance))
            metrics.update(fragmentation_truth_diagnostics(truth_mask, pred_mask))
            metric_rows.append(metrics)

    _write_canonical(args.prediction_tsv, prediction_rows, "P3_prediction")
    _write_canonical(args.truth_tsv, truth_rows, "comparator_truth")
    args.lengths_json.parent.mkdir(parents=True, exist_ok=True)
    args.lengths_json.write_text(json.dumps(lengths, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.metrics_json.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_json.write_text(json.dumps({
        "profile": "P3_comparator_run_engineering_pilot",
        "claim_scope": "RepeatMasker-style comparator agreement only",
        "weight_mode": args.weight_mode,
        "max_windows": args.max_windows,
        "rows": metric_rows,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    train_parser = sub.add_parser("train")
    train_parser.add_argument("--checkpoint", type=Path, required=True)
    train_parser.add_argument("--data-dir", type=Path, required=True)
    train_parser.add_argument("--output-dir", type=Path, required=True)
    train_parser.add_argument("--max-steps", type=int, default=800)
    train_parser.add_argument("--eval-steps", type=int, default=100)
    train_parser.add_argument("--max-eval-samples", type=int, default=800)
    train_parser.add_argument("--width", type=int, default=128)
    train_parser.add_argument("--seed", type=int, default=42)
    train_parser.add_argument("--bf16", action="store_true")
    eval_parser = sub.add_parser("evaluate")
    eval_parser.add_argument("--model-dir", type=Path, required=True)
    eval_parser.add_argument("--data-jsonl", type=Path, required=True)
    eval_parser.add_argument("--prediction-tsv", type=Path, required=True)
    eval_parser.add_argument("--truth-tsv", type=Path, required=True)
    eval_parser.add_argument("--lengths-json", type=Path, required=True)
    eval_parser.add_argument("--metrics-json", type=Path, required=True)
    eval_parser.add_argument("--threshold", type=float, default=0.5)
    eval_parser.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    eval_parser.add_argument("--max-windows", type=int, default=1200)
    eval_parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    if args.command == "train":
        train(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
