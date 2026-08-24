#!/usr/bin/env python3
"""Literal Human-chr1 DAPT followed by a direct-annotation loading audit.

The training path is deliberately small and fixed: it consumes sequence only,
uses nucleotide-level dynamic MLM masking, and writes one final HF MLM
checkpoint.  Token-classification training remains in ``te_token_task.py``;
``audit`` below verifies the matched Base->CE/DAPT->CE loading contract used by
its ``auto_token`` mode.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Iterator

os.environ.setdefault("TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD", "1")
os.environ.setdefault("WANDB_DISABLED", "true")

WINDOW = 8192
TRAIN_RECORDS = 3000
MASK_PROBABILITY = 0.15
SEED = 42
OPTIMIZER_STEPS = 800
GRADIENT_ACCUMULATION = 16
LEARNING_RATE = 1e-5
WARMUP_RATIO = 0.1
WEIGHT_DECAY = 0.01


def _open_jsonl(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open("rt", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_sequences(path: Path, limit: int = TRAIN_RECORDS, window: int = WINDOW) -> Iterator[str]:
    """Yield exactly sequence fields; labels and all annotation fields are never read."""
    with _open_jsonl(path) as handle:
        for index, line in enumerate(handle):
            if index >= limit:
                break
            record = json.loads(line)
            sequence = record["sequence"]
            if not isinstance(sequence, str) or len(sequence) != window:
                raise ValueError(f"record {index} sequence length is not {window}")
            yield sequence


def _require_torch():
    try:
        import torch
    except ImportError as exc:  # pragma: no cover - exercised only on a training host
        raise RuntimeError("DAPT requires the generanno PyTorch/Transformers environment") from exc
    return torch


def mask_inputs(
    input_ids,
    attention_mask,
    special_tokens_mask,
    *,
    n_token_ids: set[int],
    pad_token_id: int | None,
    mask_token_id: int,
    acgt_token_ids: tuple[int, int, int, int],
    vocab_size: int,
    generator,
):
    """Apply 80/10/10 masking and return ``(masked_ids, mlm_labels, selected)``.

    This function intentionally takes masks and token IDs explicitly so it can
    be tested without loading a model or tokenizer.
    """
    torch = _require_torch()
    if len(acgt_token_ids) != 4 or any(token_id < 0 or token_id >= vocab_size for token_id in acgt_token_ids):
        raise ValueError("A/C/G/T token IDs must be four valid vocabulary IDs")
    candidate = attention_mask.bool() & ~special_tokens_mask.bool()
    for token_id in n_token_ids:
        candidate &= input_ids.ne(int(token_id))
    if pad_token_id is not None:
        candidate &= input_ids.ne(int(pad_token_id))
    selected = torch.rand(input_ids.shape, generator=generator, device=input_ids.device) < MASK_PROBABILITY
    selected &= candidate
    labels = input_ids.clone().masked_fill(~selected, -100)
    masked = input_ids.clone()
    branch = torch.rand(input_ids.shape, generator=generator, device=input_ids.device)
    replace_mask = selected & branch.lt(0.8)
    replace_random = selected & branch.ge(0.8) & branch.lt(0.9)
    masked[replace_mask] = mask_token_id
    if replace_random.any():
        choices = torch.tensor(acgt_token_ids, dtype=input_ids.dtype, device=input_ids.device)
        indices = torch.randint(0, 4, (int(replace_random.sum()),), generator=generator, device=input_ids.device)
        masked[replace_random] = choices[indices]
    return masked, labels, selected


def _runtime():
    import torch
    from torch.utils.data import Dataset
    from transformers import AutoModel, AutoModelForMaskedLM, AutoTokenizer, Trainer, TrainingArguments, set_seed
    return torch, Dataset, AutoModel, AutoModelForMaskedLM, AutoTokenizer, Trainer, TrainingArguments, set_seed


def build_dataset(torch, Dataset, tokenizer, sequences: list[str]):
    class SequenceDataset(Dataset):
        def __len__(self):
            return len(sequences)

        def __getitem__(self, index):
            encoded = tokenizer(
                sequences[index], add_special_tokens=False, truncation=True, max_length=WINDOW,
                padding="max_length", return_special_tokens_mask=True,
            )
            if len(encoded["input_ids"]) != WINDOW:
                raise ValueError("tokenizer did not preserve the frozen 8192-token geometry")
            return {
                key: torch.tensor(encoded[key], dtype=torch.long)
                for key in ("input_ids", "attention_mask", "special_tokens_mask")
            }

    return SequenceDataset()


class DynamicMaskingCollator:
    def __init__(self, tokenizer, torch_module, seed: int = SEED):
        self.tokenizer = tokenizer
        self.torch = torch_module
        self.generator = torch_module.Generator()
        self.generator.manual_seed(seed)
        self.mask_token_id = tokenizer.mask_token_id
        if self.mask_token_id is None:
            raise ValueError("tokenizer has no mask token")
        self.pad_token_id = tokenizer.pad_token_id
        self.n_token_ids = {int(x) for x in tokenizer.convert_tokens_to_ids(["N", "n"]) if x is not None and int(x) >= 0}
        acgt = tokenizer.convert_tokens_to_ids(["A", "C", "G", "T"])
        self.acgt_token_ids = tuple(int(x) for x in acgt)
        self.vocab_size = int(getattr(tokenizer, "vocab_size", len(tokenizer)))

    def __call__(self, examples):
        torch = self.torch
        batch = {key: torch.stack([row[key] for row in examples]) for key in examples[0]}
        special = batch.pop("special_tokens_mask", torch.zeros_like(batch["input_ids"]))
        masked, labels, _selected = mask_inputs(
            batch["input_ids"], batch["attention_mask"], special,
            n_token_ids=self.n_token_ids, pad_token_id=self.pad_token_id,
            mask_token_id=int(self.mask_token_id), acgt_token_ids=self.acgt_token_ids,
            vocab_size=self.vocab_size, generator=self.generator,
        )
        batch["input_ids"], batch["labels"] = masked, labels
        return batch


def train(args) -> None:
    torch, Dataset, _AutoModel, AutoModelForMaskedLM, AutoTokenizer, Trainer, TrainingArguments, set_seed = _runtime()
    if not args.smoke and (args.records != TRAIN_RECORDS or args.window != WINDOW or args.max_steps != OPTIMIZER_STEPS):
        raise ValueError("frozen DAPT requires records=3000, window=8192, max_steps=800")
    set_seed(SEED)
    sequences = list(iter_sequences(args.data_jsonl, args.records, args.window))
    expected_records = args.records
    if len(sequences) != expected_records:
        raise ValueError(f"expected exactly {expected_records} Human chr1 train records, got {len(sequences)}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_checkpoint, trust_remote_code=True, local_files_only=True)
    model = AutoModelForMaskedLM.from_pretrained(args.base_checkpoint, trust_remote_code=True, local_files_only=True)
    if model.__class__.__name__ != "GenerannoForMaskedLM":
        raise TypeError(f"unexpected MLM class: {model.__class__.__name__}")
    if not all(parameter.requires_grad for parameter in model.parameters()):
        raise ValueError("DAPT requires the full backbone and MLM head to be trainable")
    model.config.use_cache = False
    dataset = build_dataset(torch, Dataset, tokenizer, sequences)
    collator = DynamicMaskingCollator(tokenizer, torch, SEED)
    output = args.output_dir
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=False)
    training_args = TrainingArguments(
        output_dir=str(output / "trainer_state"), overwrite_output_dir=True,
        per_device_train_batch_size=1, gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        learning_rate=LEARNING_RATE, warmup_ratio=WARMUP_RATIO, weight_decay=WEIGHT_DECAY,
        max_steps=args.max_steps, save_strategy="no", eval_strategy="no", logging_steps=20,
        bf16=True, fp16=False, gradient_checkpointing=True, seed=SEED, report_to="none",
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=dataset, data_collator=collator)
    trainer.train()
    trainer.save_model(str(output))
    tokenizer.save_pretrained(str(output))
    (output / "dapt_meta.json").write_text(json.dumps({
        "recipe": "literal_human_chr1_dapt",
        "source_jsonl": str(args.data_jsonl), "source_sha256": sha256_file(args.data_jsonl),
        "records": expected_records, "window": args.window,
        "add_special_tokens": False, "mask_probability": MASK_PROBABILITY,
        "mask_replacement": {"mask": 0.8, "random_acgt": 0.1, "unchanged": 0.1},
        "excluded_from_targets": ["N", "padding", "special_tokens", "metadata"],
        "base_checkpoint": str(args.base_checkpoint), "model_class": model.__class__.__name__,
        "seed": SEED, "batch_size": 1, "gradient_accumulation_steps": GRADIENT_ACCUMULATION,
        "optimizer_steps": args.max_steps, "learning_rate": LEARNING_RATE,
        "warmup_ratio": WARMUP_RATIO, "weight_decay": WEIGHT_DECAY, "bf16": True,
        "gradient_checkpointing": True, "checkpoint_policy": "fixed_final",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def audit_one(checkpoint: Path):
    _torch, _Dataset, _AutoModel, _AutoModelForMaskedLM, _AutoTokenizer, _Trainer, _TrainingArguments, _set_seed = _runtime()
    from transformers import AutoModelForTokenClassification
    model, loading_info = AutoModelForTokenClassification.from_pretrained(
        checkpoint, num_labels=2, trust_remote_code=True, local_files_only=True,
        ignore_mismatched_sizes=True, output_loading_info=True,
    )
    missing = set(loading_info.get("missing_keys", []))
    mismatched_rows = loading_info.get("mismatched_keys", [])
    mismatched = {row[0] if isinstance(row, (tuple, list)) else row for row in mismatched_rows}
    score_keys = {"score.weight"}
    if hasattr(model, "score") and getattr(model.score, "bias", None) is not None:
        score_keys.add("score.bias")
    if (missing | mismatched) != score_keys:
        raise ValueError(
            "checkpoint audit rejected score initialization: "
            f"missing={sorted(missing)} mismatched={sorted(mismatched)} expected={sorted(score_keys)}"
        )
    unexpected = set(loading_info.get("unexpected_keys", []))
    allowed = {"lm_head.weight"}
    if unexpected != allowed:
        raise ValueError(f"checkpoint audit rejected unexpected keys: {sorted(unexpected)}")
    return {"checkpoint": str(checkpoint), "missing_keys": sorted(missing), "mismatched_keys": sorted(mismatched),
            "unexpected_keys": sorted(unexpected), "discarded": sorted(allowed),
            "new_score": {"class": model.score.__class__.__name__, "in_features": int(model.score.in_features),
                          "out_features": int(model.score.out_features), "keys": sorted(score_keys)},
            "token_classifier_class": model.__class__.__name__}


def audit(args) -> None:
    result = {"base_to_ce": audit_one(args.base_checkpoint), "dapt_to_ce": audit_one(args.dapt_checkpoint),
              "contract": "only lm_head is discarded; a fresh 2-way score is created"}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    train_parser = sub.add_parser("train")
    train_parser.add_argument("--data-jsonl", type=Path, required=True)
    train_parser.add_argument("--base-checkpoint", type=Path, default=Path("/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base"))
    train_parser.add_argument("--output-dir", type=Path, required=True)
    train_parser.add_argument("--records", type=int, default=TRAIN_RECORDS)
    train_parser.add_argument("--window", type=int, default=WINDOW)
    train_parser.add_argument("--max-steps", type=int, default=OPTIMIZER_STEPS)
    train_parser.add_argument("--smoke", action="store_true", help="allow a short one-record/one-step GPU smoke")
    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--base-checkpoint", type=Path, required=True)
    audit_parser.add_argument("--dapt-checkpoint", type=Path, required=True)
    audit_parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "train":
        train(args)
    else:
        audit(args)


if __name__ == "__main__":
    main()
