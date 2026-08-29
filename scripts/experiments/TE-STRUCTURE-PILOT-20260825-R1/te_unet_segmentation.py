#!/usr/bin/env python3
"""Minimal joint backbone + 1D U-Net pilot for comparator-run segmentation."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import sys
from pathlib import Path

WINDOW = 8192
IGNORE = -100
BOUNDARY_RADIUS = 16


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


def _known_label(value: int, sequence: str | None, index: int) -> bool:
    """Return whether a label/base pair is usable for supervised targets."""
    return value in (0, 1) and (sequence is None or sequence[index].upper() != "N")


def _positive_runs_for_targets(labels: list[int], sequence: str | None) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    index = 0
    while index < len(labels):
        if not _known_label(labels[index], sequence, index) or labels[index] != 1:
            index += 1
            continue
        start = index
        index += 1
        while (
            index < len(labels)
            and _known_label(labels[index], sequence, index)
            and labels[index] == 1
        ):
            index += 1
        runs.append((start, index))
    return runs


def _boundary_valid_mask(
    labels: list[int], sequence: str | None, radius: int,
) -> list[bool]:
    """Mask positions whose +/- radius context cannot support a boundary loss."""
    known = [_known_label(value, sequence, index) for index, value in enumerate(labels)]
    valid = list(known)
    for index, is_known in enumerate(known):
        if is_known:
            continue
        for masked in range(max(0, index - radius), min(len(labels), index + radius + 1)):
            valid[masked] = False
    for index in range(min(radius, len(labels))):
        valid[index] = False
    for index in range(max(0, len(labels) - radius), len(labels)):
        valid[index] = False
    return valid


def _boundary_centers(
    labels: list[int], sequence: str | None, radius: int,
) -> list[tuple[str, int]]:
    """Return individually legal, fully-known comparator boundary centers.

    ``left`` is the first base of a run and ``right`` is its last base, matching
    the four-state comparator labels.  A center is omitted when its +/- radius
    support is outside the window or contains unknown bases.  Overlapping
    centers are retained because the left/right heads are independent and the
    target map resolves overlap by taking the larger triangular value.
    """
    if radius <= 0:
        raise ValueError("radius must be positive")
    candidates = _raw_boundary_centers(labels, sequence)
    usable: list[tuple[str, int]] = []
    for side, center in candidates:
        left, right = center - radius, center + radius + 1
        if left < 0 or right > len(labels):
            continue
        if not all(_known_label(labels[index], sequence, index) for index in range(left, right)):
            continue
        usable.append((side, center))

    # Keep every individually legal center.  Overlapping supports are valid
    # supervision for independent heads; target construction uses the maximum
    # triangular value at a base and the matched control preserves that map.
    return usable


def _raw_boundary_centers(
    labels: list[int], sequence: str | None,
) -> list[tuple[str, int]]:
    """Return all known run transitions before support eligibility filtering."""
    candidates: list[tuple[str, int]] = []
    for start, end in _positive_runs_for_targets(labels, sequence):
        if start > 0 and _known_label(labels[start - 1], sequence, start - 1) and labels[start - 1] == 0:
            candidates.append(("left", start))
        if end < len(labels) and _known_label(labels[end], sequence, end) and labels[end] == 0:
            candidates.append(("right", end - 1))
    return candidates


def _shuffle_boundary_centers(
    centers: list[tuple[str, int]], labels: list[int], sequence: str | None,
    radius: int, seed: int,
) -> tuple[list[tuple[str, int]], int]:
    """Cyclically translate both target maps away from true boundaries.

    One shared legal shift preserves center count, cyclic spacing, overlap and
    triangular-map mass across both heads.  Shifts are
    deterministic and reject edge/unknown support and any change in either raw
    or valid target-map mass.  Dense TE windows need not permit every shifted
    center to be isolated from every true center; the non-zero shared shift is
    the negative-control intervention.
    """
    if not centers:
        return [], 0
    window = len(labels)
    if window == 0:
        raise ValueError("cannot shuffle boundary targets in an empty window")

    # Prefix sums make the fully-known +/- radius support test O(1) per center.
    unknown_prefix = [0]
    for index in range(window):
        unknown_prefix.append(
            unknown_prefix[-1] + int(not _known_label(labels[index], sequence, index))
        )
    boundary_valid = _boundary_valid_mask(labels, sequence, radius)

    def support_known(center: int) -> bool:
        left, right = center - radius, center + radius + 1
        return (
            left >= 0
            and right <= window
            and unknown_prefix[right] == unknown_prefix[left]
        )

    def map_mass(side_centers: list[int], valid_mask: list[bool] | None = None) -> float:
        values = [0.0] * window
        for center in side_centers:
            for offset in range(-radius, radius + 1):
                index = center + offset
                if 0 <= index < window:
                    values[index] = max(values[index], 1.0 - abs(offset) / radius)
        if valid_mask is not None:
            values = [value if valid_mask[index] else 0.0 for index, value in enumerate(values)]
        return sum(values)

    source_by_side = {
        side: [center for center_side, center in centers if center_side == side]
        for side in ("left", "right")
    }
    source_masses = {
        side: map_mass(side_centers)
        for side, side_centers in source_by_side.items()
        if side_centers
    }
    source_valid_masses = {
        side: map_mass(side_centers, boundary_valid)
        for side, side_centers in source_by_side.items()
        if side_centers
    }
    start = seed * 1103515245 + 12345
    for ordinal in range(window):
        delta = (start + ordinal) % window
        if delta == 0:
            continue
        shifted_by_side = {
            side: [(center + delta) % window for center in side_centers]
            for side, side_centers in source_by_side.items()
        }
        shifted = [center for side_centers in shifted_by_side.values() for center in side_centers]
        if any(not support_known(center) for center in shifted):
            continue
        if any(
            not math.isclose(
                map_mass(shifted_by_side[side]), source_masses[side],
                rel_tol=0.0, abs_tol=1e-9,
            )
            or not math.isclose(
                map_mass(shifted_by_side[side], boundary_valid), source_valid_masses[side],
                rel_tol=0.0, abs_tol=1e-9,
            )
            for side in source_masses
        ):
            continue
        return [
            (side, (center + delta) % window)
            for side, center in centers
        ], delta
    raise ValueError(
        "cannot place matched cyclically shifted boundary targets "
        f"in a {window}-bp window with one shared cyclic shift"
    )


def decoupled_boundary_targets(
    labels: list[int],
    sequence: str | None = None,
    *,
    mode: str = "true",
    radius: int = BOUNDARY_RADIUS,
    seed: int = 0,
) -> dict[str, list[int] | list[float] | list[bool]]:
    """Build P3-R2 body and independent triangular boundary targets.

    The body target is binary on known bases and ``IGNORE`` elsewhere.  Left
    and right targets are zero except for a triangular +/- ``radius`` profile
    centered at a usable comparator transition.  ``boundary_valid_mask`` also
    removes unknown/edge neighborhoods from boundary losses.  ``mode='shuffled'``
    keeps the number and profile of targets but relocates their centers
    deterministically within the same window using one non-zero shared cyclic
    shift.
    """
    if mode not in {"true", "shuffled"}:
        raise ValueError("mode must be 'true' or 'shuffled'")
    if radius <= 0:
        raise ValueError("radius must be positive")
    if sequence is not None and len(sequence) != len(labels):
        raise ValueError("sequence and labels must have the same length")
    if any(value not in (IGNORE, 0, 1) for value in labels):
        raise ValueError("labels must contain only -100, 0 and 1")

    body = [
        int(value) if _known_label(value, sequence, index) else IGNORE
        for index, value in enumerate(labels)
    ]
    valid = _boundary_valid_mask(labels, sequence, radius)
    left_target = [0.0] * len(labels)
    right_target = [0.0] * len(labels)
    all_centers = _raw_boundary_centers(labels, sequence)
    centers = _boundary_centers(labels, sequence, radius)
    target_centers: list[tuple[str, int]]
    shuffle_delta = 0
    if mode == "true":
        target_centers = centers
    else:
        target_centers, shuffle_delta = _shuffle_boundary_centers(
            centers, labels, sequence, radius, seed,
        )

    for side, center in target_centers:
        target = left_target if side == "left" else right_target
        for offset in range(-radius, radius + 1):
            index = center + offset
            if 0 <= index < len(labels):
                target[index] = max(target[index], 1.0 - abs(offset) / radius)
    return {
        "body_labels": body,
        "left_boundary_targets": left_target,
        "right_boundary_targets": right_target,
        "boundary_valid_mask": valid,
        "boundary_centers": [center for _side, center in centers],
        "all_boundary_centers": [center for _side, center in all_centers],
        "target_centers": [center for _side, center in target_centers],
        "shuffle_delta": shuffle_delta,
        "true_centers_by_side": {
            "left": [center for side, center in centers if side == "left"],
            "right": [center for side, center in centers if side == "right"],
        },
        "target_centers_by_side": {
            "left": [center for side, center in target_centers if side == "left"],
            "right": [center for side, center in target_centers if side == "right"],
        },
    }


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


def decoupled_model_class():
    """Return the P3-R2 U-Net with independent body/left/right heads."""
    torch, nn, functional, _Dataset, AutoModel, _AutoTokenizer, _Trainer, _TrainingArguments, _collator, _seed, TokenClassifierOutput = runtime()

    class TEUNetDecoupledSegmenter(nn.Module):
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
            self.body_head = nn.Conv1d(width, 1, 1)
            self.left_boundary_head = nn.Conv1d(width, 1, 1)
            self.right_boundary_head = nn.Conv1d(width, 1, 1)
            self.register_buffer("body_pos_weight", torch.tensor(3.0))

        def forward(
            self,
            input_ids=None,
            attention_mask=None,
            body_labels=None,
            left_boundary_targets=None,
            right_boundary_targets=None,
            boundary_valid_mask=None,
        ):
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
            body_logits = self.body_head(decoded).transpose(1, 2).squeeze(-1)
            left_logits = self.left_boundary_head(decoded).transpose(1, 2).squeeze(-1)
            right_logits = self.right_boundary_head(decoded).transpose(1, 2).squeeze(-1)
            logits = torch.stack((body_logits, left_logits, right_logits), dim=-1)
            loss = None
            if body_labels is not None:
                body_valid = body_labels != IGNORE
                body_loss = functional.binary_cross_entropy_with_logits(
                    body_logits,
                    body_labels.float().masked_fill(~body_valid, 0.0),
                    reduction="none",
                    pos_weight=self.body_pos_weight,
                )
                body_loss = body_loss[body_valid].mean()
                if boundary_valid_mask is None:
                    boundary_valid_mask = body_valid
                else:
                    boundary_valid_mask = boundary_valid_mask.bool() & body_valid
                left_loss = functional.binary_cross_entropy_with_logits(
                    left_logits, left_boundary_targets.float(), reduction="none",
                )
                right_loss = functional.binary_cross_entropy_with_logits(
                    right_logits, right_boundary_targets.float(), reduction="none",
                )
                valid_count = boundary_valid_mask.sum().clamp_min(1)
                left_loss = (left_loss * boundary_valid_mask).sum() / valid_count
                right_loss = (right_loss * boundary_valid_mask).sum() / valid_count
                loss = body_loss + left_loss + right_loss
            return TokenClassifierOutput(loss=loss, logits=logits)

        def gradient_checkpointing_enable(self, *args, **kwargs):
            return self.backbone.gradient_checkpointing_enable(*args, **kwargs)

    return TEUNetDecoupledSegmenter


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


def decoupled_dataset_class(boundary_mode: str, seed: int):
    torch, _nn, _functional, Dataset, _AutoModel, _AutoTokenizer, _Trainer, _TrainingArguments, _collator, _seed, _output = runtime()

    class DecoupledWindowDataset(Dataset):
        def __init__(self, path: Path, tokenizer, limit: int | None = None):
            self.rows = []
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                for index, line in enumerate(handle):
                    if limit is not None and index >= limit:
                        break
                    self.rows.append(json.loads(line))
            self.tokenizer = tokenizer
            self.boundary_mode = boundary_mode
            self.seed = seed

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, index):
            row = self.rows[index]
            sequence = row["sequence"][:WINDOW]
            labels = row["labels"][:WINDOW]
            if len(sequence) != WINDOW or len(labels) != WINDOW:
                raise ValueError(f"P3-R2 windows must contain exactly {WINDOW} bases")
            targets = decoupled_boundary_targets(
                labels,
                sequence,
                mode=self.boundary_mode,
                seed=self.seed + index * 1009,
            )
            encoded = self.tokenizer(
                sequence, add_special_tokens=False, truncation=True,
                max_length=WINDOW, padding="max_length",
            )
            return {
                "input_ids": torch.tensor(encoded["input_ids"], dtype=torch.long),
                "attention_mask": torch.tensor(encoded["attention_mask"], dtype=torch.long),
                "body_labels": torch.tensor(targets["body_labels"], dtype=torch.long),
                "left_boundary_targets": torch.tensor(targets["left_boundary_targets"], dtype=torch.float32),
                "right_boundary_targets": torch.tensor(targets["right_boundary_targets"], dtype=torch.float32),
                "boundary_valid_mask": torch.tensor(targets["boundary_valid_mask"], dtype=torch.bool),
            }

    return DecoupledWindowDataset


def train_decoupled(args) -> None:
    torch, _nn, _functional, _Dataset, _AutoModel, AutoTokenizer, Trainer, TrainingArguments, collator, set_seed, _output = runtime()
    set_seed(args.seed)
    local = os.environ.get("TEFM_LOCAL_FILES_ONLY", "1") != "0"
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, trust_remote_code=True, local_files_only=local)
    DatasetType = decoupled_dataset_class(args.boundary_target_mode, args.seed)
    train_data = DatasetType(args.data_dir / "train" / "data.jsonl.gz", tokenizer)
    validation = DatasetType(args.data_dir / "val" / "data.jsonl.gz", tokenizer, args.max_eval_samples)
    Model = decoupled_model_class()
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
        disable_tqdm=True,
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
        "schema": "comparator_run_decoupled_boundary_unet_v1",
        "checkpoint": str(args.checkpoint),
        "data_dir": str(args.data_dir),
        "window": WINDOW,
        "heads": ["body", "left_boundary", "right_boundary"],
        "body_positive_weight": 3.0,
        "boundary_target_mode": args.boundary_target_mode,
        "boundary_radius": BOUNDARY_RADIUS,
        "boundary_target": "triangular_pm16_bp_center_one_linear_to_zero",
        "control_shift": "single_shared_cyclic_shift_per_window_recorded_in_preflight",
        "boundary_overlap": "retain_centers_max_profile",
        "boundary_unknown_policy": "mask_unknown_pm16_and_window_edge_pm16_in_boundary_loss",
        "design": "supervised_label_loss_decomposition",
        "width": args.width,
        "max_steps": args.max_steps,
        "seed": args.seed,
        "claim_scope": "RepeatMasker-style comparator-run engineering pilot",
    }, indent=2) + "\n", encoding="utf-8")


def train(args) -> None:
    if args.r2:
        return train_decoupled(args)
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
        disable_tqdm=True,
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


def preflight_decoupled(args) -> None:
    """Validate all Human train/val windows before allocating GPU training."""
    split_summaries: dict[str, dict[str, object]] = {}
    for split in ("train", "val"):
        path = args.data_dir / split / "data.jsonl.gz"
        rows = 0
        total_true_centers = 0
        total_target_centers = 0
        details: list[dict[str, object]] = []
        limit = None if split == "train" else args.max_eval_samples
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if limit is not None and index >= limit:
                    break
                row = json.loads(line)
                sequence = row["sequence"][:WINDOW]
                labels = row["labels"][:WINDOW]
                if len(sequence) != WINDOW or len(labels) != WINDOW:
                    raise ValueError(
                        f"{split} row {index} must contain exactly {WINDOW} bases and labels"
                    )
                true = decoupled_boundary_targets(labels, sequence, mode="true", seed=args.seed + index * 1009)
                target = decoupled_boundary_targets(
                    labels, sequence, mode=args.boundary_target_mode,
                    seed=args.seed + index * 1009,
                )
                if true["body_labels"] != target["body_labels"]:
                    raise ValueError(f"{split} row {index} changes body labels across P3-R2 arms")
                if true["boundary_valid_mask"] != target["boundary_valid_mask"]:
                    raise ValueError(f"{split} row {index} changes boundary-valid negatives across P3-R2 arms")
                for side in ("left", "right"):
                    true_centers = true["true_centers_by_side"][side]
                    target_centers = target["target_centers_by_side"][side]
                    if len(true_centers) != len(target_centers):
                        raise ValueError(f"{split} row {index} changes {side} center count in control")
                    true_mass = sum(true[f"{side}_boundary_targets"])
                    target_mass = sum(target[f"{side}_boundary_targets"])
                    if not math.isclose(true_mass, target_mass, rel_tol=0.0, abs_tol=1e-9):
                        raise ValueError(f"{split} row {index} changes {side} target mass in control")
                    valid_mask = true["boundary_valid_mask"]
                    true_valid_mass = sum(
                        value for value, valid in zip(true[f"{side}_boundary_targets"], valid_mask) if valid
                    )
                    target_valid_mass = sum(
                        value for value, valid in zip(target[f"{side}_boundary_targets"], valid_mask) if valid
                    )
                    if not math.isclose(true_valid_mass, target_valid_mass, rel_tol=0.0, abs_tol=1e-9):
                        raise ValueError(f"{split} row {index} changes valid {side} target mass in control")
                rows += 1
                total_true_centers += len(true["boundary_centers"])
                total_target_centers += len(target["target_centers"])
                details.append({
                    "index": index,
                    "seqid": row.get("chr"),
                    "start": row.get("start"),
                    "true_centers_by_side": true["true_centers_by_side"],
                    "target_centers_by_side": target["target_centers_by_side"],
                    "shuffle_delta": target["shuffle_delta"],
                    "true_mass_by_side": {
                        side: sum(true[f"{side}_boundary_targets"])
                        for side in ("left", "right")
                    },
                    "target_mass_by_side": {
                        side: sum(target[f"{side}_boundary_targets"])
                        for side in ("left", "right")
                    },
                })
        split_summaries[split] = {
            "rows": rows,
            "true_boundary_centers": total_true_centers,
            "target_boundary_centers": total_target_centers,
            "details": details,
        }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps({
        "schema": "p3_r2_preflight_v1",
        "status": "PASS",
        "data_dir": str(args.data_dir),
        "boundary_target_mode": args.boundary_target_mode,
        "boundary_radius": BOUNDARY_RADIUS,
        "control_shift": "single_shared_cyclic_shift_per_window",
        "seed": args.seed,
        "splits": split_summaries,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def evaluate_decoupled(args) -> None:
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
    if metadata.get("schema") != "comparator_run_decoupled_boundary_unet_v1":
        raise ValueError("model metadata is not a P3-R2 decoupled-boundary checkpoint")
    local = os.environ.get("TEFM_LOCAL_FILES_ONLY", "1") != "0"
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir / "tokenizer", trust_remote_code=True, local_files_only=local)
    Model = decoupled_model_class()
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
            body_logits = model(**inputs).logits[..., 0]
            probability = torch.sigmoid(body_logits)[0].cpu().numpy()[: end - start]
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

    _write_canonical(args.prediction_tsv, prediction_rows, "P3_R2_prediction")
    _write_canonical(args.truth_tsv, truth_rows, "comparator_truth")
    args.lengths_json.parent.mkdir(parents=True, exist_ok=True)
    args.lengths_json.write_text(json.dumps(lengths, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.metrics_json.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_json.write_text(json.dumps({
        "profile": "P3_R2_decoupled_boundary_engineering_pilot",
        "claim_scope": "RepeatMasker-style comparator agreement only",
        "boundary_target_mode": metadata["boundary_target_mode"],
        "boundary_radius": metadata["boundary_radius"],
        "weight_mode": args.weight_mode,
        "max_windows": args.max_windows,
        "rows": metric_rows,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def evaluate(args) -> None:
    if args.r2:
        return evaluate_decoupled(args)
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
    train_parser.add_argument("--r2", action="store_true", help="use the decoupled body/left/right P3-R2 heads")
    train_parser.add_argument(
        "--boundary-target-mode", choices=["true", "shuffled"], default="true",
        help="true comparator boundaries or matched same-window shuffled control (P3-R2)",
    )
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
    eval_parser.add_argument("--r2", action="store_true", help="use the decoupled body head for P3-R2")
    preflight_parser = sub.add_parser("preflight")
    preflight_parser.add_argument("--data-dir", type=Path, required=True)
    preflight_parser.add_argument("--output-json", type=Path, required=True)
    preflight_parser.add_argument("--seed", type=int, default=42)
    preflight_parser.add_argument("--max-eval-samples", type=int, default=800)
    preflight_parser.add_argument(
        "--boundary-target-mode", choices=["true", "shuffled"], default="true",
    )
    args = parser.parse_args()
    if args.command == "train":
        train(args)
    elif args.command == "evaluate":
        evaluate(args)
    else:
        preflight_decoupled(args)


if __name__ == "__main__":
    main()
