#!/usr/bin/env python3
"""Minimal TE-aware span-MLM mechanism for the 20260825 pilot.

The sampler consumes explicit, disjoint ``interior``, ``boundary`` and
``flank`` candidate masks.  It never infers a boundary from a window edge or
from a binary label transition.  The MLM target is still the nucleotide token
at the selected positions; the candidate masks only choose where to mask.

Training is allowed for an explicit reference-annotation-run sidecar so that
the comparator-conditioned pilot can be exercised.  Its boundaries remain
reference-run boundaries, not biological copy boundaries.  ``smoke`` is
independent of that gate and exercises only the masking mechanism with
synthetic explicit masks.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
from pathlib import Path
from typing import Iterable

WINDOW = 8192
STRATA = ("interior", "boundary", "flank")
STRATUM_WEIGHTS = {"interior": 0.45, "boundary": 0.30, "flank": 0.25}
MASK_PROBABILITY = 0.15
SPAN_LENGTH = 32
SEED = 42


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def _as_bool_mask(values: Iterable[object], name: str, window: int = WINDOW) -> list[bool]:
    mask = [bool(value) for value in values]
    if len(mask) != window:
        raise ValueError(f"{name} length is {len(mask)}, expected {window}")
    return mask


def validate_candidate_masks(candidate_masks: dict[str, Iterable[object]], window: int = WINDOW) -> dict[str, list[bool]]:
    """Validate the explicit three-stratum interface and preserve no inferred labels."""
    missing = [name for name in STRATA if name not in candidate_masks]
    if missing:
        raise ValueError(f"missing explicit candidate strata: {','.join(missing)}")
    masks = {name: _as_bool_mask(candidate_masks[name], name, window) for name in STRATA}
    for i, left in enumerate(STRATA):
        for right in STRATA[i + 1:]:
            if any(a and b for a, b in zip(masks[left], masks[right])):
                raise ValueError(f"candidate strata overlap: {left} and {right}")
    return masks


def _mask_or_false(values: Iterable[object] | None, name: str, window: int) -> list[bool]:
    if values is None:
        return [False] * window
    return _as_bool_mask(values, name, window)


def _runs(mask: list[bool]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(mask + [False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            runs.append((start, index))
            start = None
    return runs


def _span_starts(mask: list[bool], span_length: int) -> list[int]:
    starts: list[int] = []
    for start, end in _runs(mask):
        starts.extend(range(start, end - span_length + 1))
    return starts


def _take_nonoverlapping(
    starts: list[int],
    quota: int,
    span_length: int,
    rng: random.Random,
    occupied: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    # All spans have the same length, so earliest-finish interval scheduling
    # gives the maximum packable set.  Shuffling that set preserves stochastic
    # selection without letting an unlucky middle start reduce the mask budget.
    packable: list[tuple[int, int]] = []
    for start in sorted(starts):
        span = (start, start + span_length)
        if any(span[0] < occupied_end and occupied_start < span[1] for occupied_start, occupied_end in occupied):
            continue
        packable.append(span)
        occupied.append(span)
    for span in packable:
        occupied.remove(span)
    rng.shuffle(packable)
    chosen = packable[:quota]
    occupied.extend(chosen)
    return chosen


def sample_contiguous_spans(
    candidate_masks: dict[str, Iterable[object]],
    *,
    attention_mask: Iterable[object] | None = None,
    unknown_mask: Iterable[object] | None = None,
    n_mask: Iterable[object] | None = None,
    target_fraction: float = MASK_PROBABILITY,
    span_length: int = SPAN_LENGTH,
    seed: int = SEED,
    stratum_weights: dict[str, float] | None = None,
    strict_selected_bp: bool = True,
    window: int = WINDOW,
) -> dict[str, object]:
    """Sample fixed-length, non-overlapping spans from explicit candidate masks.

    A boundary-crossing candidate must be supplied in ``boundary`` by the
    caller.  This function has no sequence or binary-label input and therefore
    cannot manufacture a biological boundary.
    """
    if not 0.0 < target_fraction <= 1.0:
        raise ValueError("target_fraction must be in (0, 1]")
    if span_length < 1 or span_length > window:
        raise ValueError(f"span_length must be in [1, {window}]")
    masks = validate_candidate_masks(candidate_masks, window)
    attention = _mask_or_false(attention_mask, "attention_mask", window) if attention_mask is not None else [True] * window
    unknown = _mask_or_false(unknown_mask, "unknown_mask", window)
    n_values = _mask_or_false(n_mask, "n_mask", window)
    allowed_by_stratum: dict[str, list[bool]] = {
        name: [value and attention[i] and not unknown[i] and not n_values[i] for i, value in enumerate(mask)]
        for name, mask in masks.items()
    }
    starts_by_stratum = {name: _span_starts(mask, span_length) for name, mask in allowed_by_stratum.items()}
    eligible_bp = sum(sum(mask) for mask in allowed_by_stratum.values())
    callable_bp = sum(
        attention[index] and not unknown[index] and not n_values[index]
        for index in range(window)
    )
    target_bp = int(round(callable_bp * target_fraction))
    target_spans = target_bp // span_length
    if target_bp > 0 and target_spans == 0:
        target_spans = 1

    weights = stratum_weights or STRATUM_WEIGHTS
    if set(weights) != set(STRATA) or any(float(weights[name]) < 0 for name in STRATA):
        raise ValueError("stratum_weights must contain non-negative interior/boundary/flank values")
    available = [name for name in STRATA if starts_by_stratum[name]]
    if target_spans and not available:
        raise ValueError("no contiguous eligible span exists in any candidate stratum")
    total_weight = sum(float(weights[name]) for name in available)
    if available and total_weight <= 0:
        raise ValueError("available candidate strata have zero total weight")

    quotas = {name: 0 for name in STRATA}
    if target_spans:
        fractional = []
        for name in available:
            exact = target_spans * float(weights[name]) / total_weight
            quotas[name] = int(exact)
            fractional.append((exact - quotas[name], name))
        for _fraction, name in sorted(fractional, reverse=True)[: target_spans - sum(quotas.values())]:
            quotas[name] += 1

    rng = random.Random(seed)
    occupied: list[tuple[int, int]] = []
    spans_by_stratum: dict[str, list[tuple[int, int]]] = {name: [] for name in STRATA}
    for name in STRATA:
        spans_by_stratum[name] = _take_nonoverlapping(
            starts_by_stratum[name], quotas[name], span_length, rng, occupied
        )

    # A scarce stratum must not silently lower the masking budget.  Reuse any
    # still-eligible, non-overlapping span from the remaining strata; only
    # report a shortage after every eligible start has been considered.
    selected_count = sum(len(spans_by_stratum[name]) for name in STRATA)
    if selected_count < target_spans:
        refillable: list[tuple[str, tuple[int, int]]] = []
        for name in STRATA:
            spans = _take_nonoverlapping(
                starts_by_stratum[name], target_spans, span_length, rng, occupied
            )
            for span in spans:
                occupied.remove(span)
                refillable.append((name, span))
        rng.shuffle(refillable)
        for name, span in refillable[: target_spans - selected_count]:
            spans_by_stratum[name].append(span)
            occupied.append(span)
            selected_count += 1

    required_selected_bp = target_spans * span_length
    if strict_selected_bp and selected_count < target_spans:
        raise ValueError(
            "insufficient non-overlapping eligible spans for strict selected-bp target: "
            f"required={required_selected_bp}, available={selected_count * span_length}"
        )

    selected = [False] * window
    selected_stratum: list[str | None] = [None] * window
    spans: list[dict[str, object]] = []
    for name in STRATA:
        for start, end in sorted(spans_by_stratum[name]):
            for index in range(start, end):
                selected[index] = True
                selected_stratum[index] = name
            spans.append({"stratum": name, "start": start, "end": end})
    return {
        "selected": selected,
        "selected_stratum": selected_stratum,
        "spans": sorted(spans, key=lambda row: int(row["start"])),
        "eligible_bp": eligible_bp,
        "callable_bp": callable_bp,
        "target_bp": target_bp,
        "target_spans": target_spans,
        "target_selected_bp": required_selected_bp,
        "selected_bp": sum(selected),
        "strict_selected_bp": strict_selected_bp,
        "selected_by_stratum": {name: sum(1 for row in spans if row["stratum"] == name) for name in STRATA},
    }


def apply_span_mask(
    input_ids,
    attention_mask,
    special_tokens_mask,
    selected,
    *,
    n_token_ids: set[int],
    pad_token_id: int | None,
    mask_token_id: int,
    acgt_token_ids: tuple[int, int, int, int],
    vocab_size: int,
    generator,
):
    """Apply the original 80/10/10 nucleotide MLM replacement to selected spans."""
    import torch

    if input_ids.ndim != 2 or input_ids.shape[1] != WINDOW:
        raise ValueError(f"input_ids must have shape [batch, {WINDOW}]")
    if len(acgt_token_ids) != 4 or any(token_id < 0 or token_id >= vocab_size for token_id in acgt_token_ids):
        raise ValueError("A/C/G/T token IDs must be four valid vocabulary IDs")
    selected = selected.bool()
    candidate = attention_mask.bool() & ~special_tokens_mask.bool() & selected
    for token_id in n_token_ids:
        candidate &= input_ids.ne(int(token_id))
    if pad_token_id is not None:
        candidate &= input_ids.ne(int(pad_token_id))
    labels = input_ids.clone().masked_fill(~candidate, -100)
    masked = input_ids.clone()
    branch = torch.rand(input_ids.shape, generator=generator, device=input_ids.device)
    replace_mask = candidate & branch.lt(0.8)
    replace_random = candidate & branch.ge(0.8) & branch.lt(0.9)
    masked[replace_mask] = mask_token_id
    if replace_random.any():
        choices = torch.tensor(acgt_token_ids, dtype=input_ids.dtype, device=input_ids.device)
        indices = torch.randint(0, 4, (int(replace_random.sum()),), generator=generator, device=input_ids.device)
        masked[replace_random] = choices[indices]
    return masked, labels, candidate


def metadata_allows_training(metadata: dict) -> bool:
    if metadata.get("annotation_level") == "reference_annotation_run":
        return not bool(metadata.get("biological_copy_claim", False))
    if metadata.get("copy_level") is False:
        return False
    return metadata.get("copy_level") is True or metadata.get("label_level") == "copy_level"


def blocked_status(metadata: dict, reason: str) -> dict[str, object]:
    return {"status": "BLOCKED", "reason": reason, "metadata": metadata}


def _runtime():
    import torch
    from torch.utils.data import Dataset
    from transformers import AutoModelForMaskedLM, AutoTokenizer, Trainer, TrainingArguments, set_seed

    return torch, Dataset, AutoModelForMaskedLM, AutoTokenizer, Trainer, TrainingArguments, set_seed


class SpanDataset:
    def __init__(self, path: Path, tokenizer, torch_module, max_samples: int | None = None):
        self.records = []
        with _open_text(path) as handle:
            for index, line in enumerate(handle):
                if max_samples is not None and index >= max_samples:
                    break
                record = json.loads(line)
                sequence = record["sequence"]
                if not isinstance(sequence, str) or len(sequence) != WINDOW:
                    raise ValueError(f"record {index} sequence length is not {WINDOW}")
                validate_candidate_masks(record["candidate_masks"])
                self.records.append(record)
        self.tokenizer = tokenizer
        self.torch = torch_module

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        record = self.records[index]
        sequence = record["sequence"]
        encoded = self.tokenizer(
            sequence,
            add_special_tokens=False,
            truncation=True,
            max_length=WINDOW,
            padding="max_length",
            return_special_tokens_mask=True,
        )
        if len(encoded["input_ids"]) != WINDOW:
            raise ValueError("tokenizer did not preserve the frozen 8192-token geometry")
        torch = self.torch
        output = {
            key: torch.tensor(encoded[key], dtype=torch.long)
            for key in ("input_ids", "attention_mask", "special_tokens_mask")
        }
        for name, values in validate_candidate_masks(record["candidate_masks"]).items():
            output[f"{name}_mask"] = torch.tensor(values, dtype=torch.bool)
        output["unknown_mask"] = torch.tensor(
            _mask_or_false(record.get("unknown_mask"), "unknown_mask", WINDOW), dtype=torch.bool
        )
        output["n_mask"] = torch.tensor(
            [base.upper() == "N" for base in sequence], dtype=torch.bool
        )
        return output


class SpanMaskingCollator:
    def __init__(self, tokenizer, torch_module, *, seed: int = SEED, target_fraction: float = MASK_PROBABILITY, span_length: int = SPAN_LENGTH, strict_selected_bp: bool = True):
        self.tokenizer = tokenizer
        self.torch = torch_module
        self.generator = torch_module.Generator()
        self.generator.manual_seed(seed)
        self.seed = seed
        self.target_fraction = target_fraction
        self.span_length = span_length
        self.strict_selected_bp = strict_selected_bp
        self.mask_token_id = tokenizer.mask_token_id
        if self.mask_token_id is None:
            raise ValueError("tokenizer has no mask token")
        self.pad_token_id = tokenizer.pad_token_id
        self.n_token_ids = {
            int(value) for value in tokenizer.convert_tokens_to_ids(["N", "n"])
            if value is not None and int(value) >= 0
        }
        self.acgt_token_ids = tuple(int(value) for value in tokenizer.convert_tokens_to_ids(["A", "C", "G", "T"]))
        self.vocab_size = int(getattr(tokenizer, "vocab_size", len(tokenizer)))
        self.sample_seed = seed

    def __call__(self, examples):
        torch = self.torch
        batch_size = len(examples)
        batch = {
            key: torch.stack([row[key] for row in examples])
            for key in ("input_ids", "attention_mask", "special_tokens_mask")
        }
        masked_rows = []
        label_rows = []
        for row_index, row in enumerate(examples):
            candidate = {name: row[f"{name}_mask"].tolist() for name in STRATA}
            sampled = sample_contiguous_spans(
                candidate,
                attention_mask=row["attention_mask"].tolist(),
                unknown_mask=row["unknown_mask"].tolist(),
                n_mask=row["n_mask"].tolist(),
                target_fraction=self.target_fraction,
                span_length=self.span_length,
                seed=self.sample_seed + row_index,
                strict_selected_bp=self.strict_selected_bp,
            )
            masked, labels, _selected = apply_span_mask(
                row["input_ids"].unsqueeze(0),
                row["attention_mask"].unsqueeze(0),
                row["special_tokens_mask"].unsqueeze(0),
                torch.tensor([sampled["selected"]], dtype=torch.bool),
                n_token_ids=self.n_token_ids,
                pad_token_id=self.pad_token_id,
                mask_token_id=int(self.mask_token_id),
                acgt_token_ids=self.acgt_token_ids,
                vocab_size=self.vocab_size,
                generator=self.generator,
            )
            masked_rows.append(masked[0])
            label_rows.append(labels[0])
        self.sample_seed += batch_size
        batch["input_ids"] = torch.stack(masked_rows)
        batch["labels"] = torch.stack(label_rows)
        return batch


def train(args) -> int:
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    if not metadata_allows_training(metadata):
        status = blocked_status(
            metadata,
            "TE-aware span MLM requires explicit copy-level or reference-annotation-run metadata",
        )
        if args.status_json:
            args.status_json.parent.mkdir(parents=True, exist_ok=True)
            args.status_json.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(status, indent=2, sort_keys=True))
        return 3

    torch, Dataset, AutoModelForMaskedLM, AutoTokenizer, Trainer, TrainingArguments, set_seed = _runtime()
    set_seed(SEED)
    tokenizer = AutoTokenizer.from_pretrained(args.base_checkpoint, trust_remote_code=True, local_files_only=True)
    model = AutoModelForMaskedLM.from_pretrained(args.base_checkpoint, trust_remote_code=True, local_files_only=True)
    if model.__class__.__name__ != "GenerannoForMaskedLM":
        raise TypeError(f"unexpected MLM class: {model.__class__.__name__}")
    if not all(parameter.requires_grad for parameter in model.parameters()):
        raise ValueError("TE-aware span MLM requires the full backbone and MLM head to be trainable")
    model.config.use_cache = False
    dataset = SpanDataset(args.data_jsonl, tokenizer, torch, args.records)
    if len(dataset) != args.records:
        raise ValueError(f"expected exactly {args.records} records, got {len(dataset)}")
    collator = SpanMaskingCollator(
        tokenizer,
        torch,
        target_fraction=args.target_fraction,
        span_length=args.span_length,
        strict_selected_bp=True,
    )
    args.output_dir.parent.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir / "trainer_state"),
        overwrite_output_dir=True,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=1e-5,
        warmup_ratio=0.1,
        weight_decay=0.01,
        max_steps=args.max_steps,
        save_strategy="no",
        eval_strategy="no",
        logging_steps=20,
        bf16=True,
        fp16=False,
        gradient_checkpointing=True,
        seed=SEED,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=dataset, data_collator=collator)
    trainer.train()
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    training_metadata = {
        "recipe": "te_aware_span_mlm",
        "source_metadata": str(args.metadata),
        "annotation_level": metadata.get("annotation_level", "unspecified"),
        "boundary_semantics": metadata.get("boundary_semantics", "unspecified"),
        "biological_copy_claim": bool(metadata.get("biological_copy_claim", False)),
        "claim_scope": metadata.get("claim_scope", "not specified"),
        "window": WINDOW,
        "candidate_strata": list(STRATA),
        "target_fraction": args.target_fraction,
        "span_length": args.span_length,
        "mask_replacement": {"mask": 0.8, "random_acgt": 0.1, "unchanged": 0.1},
        "target": "nucleotide_token_only",
        "boundary_source": "explicit_candidate_mask_only",
        "records": len(dataset),
        "optimizer_steps": args.max_steps,
    }
    for key in ("copy_level", "label_level"):
        if key in metadata:
            training_metadata[key] = metadata[key]
    (args.output_dir / "te_span_mlm_meta.json").write_text(
        json.dumps(training_metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


def smoke() -> dict[str, object]:
    candidate_masks = {
        "interior": [128 <= index < 2048 for index in range(WINDOW)],
        "boundary": [2048 <= index < 2112 for index in range(WINDOW)],
        "flank": [2112 <= index < 4096 for index in range(WINDOW)],
    }
    unknown = [3000 <= index < 3050 for index in range(WINDOW)]
    n_mask = [3500 <= index < 3540 for index in range(WINDOW)]
    sampled = sample_contiguous_spans(
        candidate_masks,
        unknown_mask=unknown,
        n_mask=n_mask,
        target_fraction=0.15,
        span_length=32,
        seed=SEED,
    )
    return {
        "status": "PASS",
        "window": WINDOW,
        "boundary_source": "explicit_candidate_mask_only",
        "selected_bp": sampled["selected_bp"],
        "spans": sampled["spans"],
        "selected_by_stratum": sampled["selected_by_stratum"],
        "unknown_excluded_bp": sum(unknown),
        "n_excluded_bp": sum(n_mask),
    }


def audit_corpus(data_jsonl: Path, records: int) -> dict[str, object]:
    selected_bp = 0
    callable_bp = 0
    selected_spans = {name: 0 for name in STRATA}
    observed = 0
    with _open_text(data_jsonl) as handle:
        for index, line in enumerate(handle):
            if index >= records:
                break
            record = json.loads(line)
            sequence = record["sequence"]
            sampled = sample_contiguous_spans(
                record["candidate_masks"],
                unknown_mask=_mask_or_false(record.get("unknown_mask"), "unknown_mask", WINDOW),
                n_mask=[base.upper() == "N" for base in sequence],
                target_fraction=MASK_PROBABILITY,
                span_length=SPAN_LENGTH,
                seed=SEED + index,
                strict_selected_bp=True,
            )
            selected_bp += int(sampled["selected_bp"])
            callable_bp += int(sampled["callable_bp"])
            for name in STRATA:
                selected_spans[name] += int(sampled["selected_by_stratum"][name])
            observed += 1
    if observed != records:
        raise ValueError(f"expected exactly {records} records, got {observed}")
    total_spans = sum(selected_spans.values())
    return {
        "status": "PASS",
        "records": observed,
        "selected_bp": selected_bp,
        "callable_bp": callable_bp,
        "selected_fraction_of_callable": selected_bp / callable_bp,
        "selected_spans": selected_spans,
        "selected_span_fractions": {
            name: selected_spans[name] / total_spans for name in STRATA
        },
        "target_weights": STRATUM_WEIGHTS,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("smoke")
    audit_parser = sub.add_parser("audit-corpus")
    audit_parser.add_argument("--data-jsonl", type=Path, required=True)
    audit_parser.add_argument("--records", type=int, default=3000)
    audit_parser.add_argument("--out-json", type=Path, required=True)
    train_parser = sub.add_parser("train")
    train_parser.add_argument("--data-jsonl", type=Path, required=True)
    train_parser.add_argument("--metadata", type=Path, required=True)
    train_parser.add_argument("--base-checkpoint", type=Path, default=Path("/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base"))
    train_parser.add_argument("--output-dir", type=Path, required=True)
    train_parser.add_argument("--status-json", type=Path)
    train_parser.add_argument("--records", type=int, default=3000)
    train_parser.add_argument("--max-steps", type=int, default=800)
    train_parser.add_argument("--target-fraction", type=float, default=MASK_PROBABILITY)
    train_parser.add_argument("--span-length", type=int, default=SPAN_LENGTH)
    args = parser.parse_args()
    if args.command == "smoke":
        print(json.dumps(smoke(), indent=2, sort_keys=True))
        return
    if args.command == "audit-corpus":
        result = audit_corpus(args.data_jsonl, args.records)
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    raise SystemExit(train(args))


if __name__ == "__main__":
    main()
