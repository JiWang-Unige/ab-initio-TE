#!/usr/bin/env python3
"""Train the frozen Stage 1 G/R/H whole-gap risk heads.

The P3 backbone is evaluated once per original 8192-bp window.  A small
candidate crop is assembled from the current window and, when necessary, the
previous window's in-memory decoded map.  No P3 latent track is written to
disk.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
WINDOW = 8192
MAX_INPUT_BP = 1024
FLANK_BP = 256
LATENT_WIDTH = 128
CHANNELS = 143
GEOMETRY_SCALARS = 7
BATCH_SIZE = 512
PASSES = 2
SEEDS = (17, 42, 20260902)
CHROMOSOMES = ("chr3", "chr5")
LENGTH_STRATA = ("1", "2", "3-5", "6-20", "21-100", "101-512")
SCALAR_FIELDS = (
    "log1p_gap_length", "log1p_left_run_length", "log1p_right_run_length",
    "log1p_span_length", "crop_crosses_8192_seam", "log1p_nearest_seam_distance",
    "nearest_seam_direction",
)
BASES = "ACGT"


@dataclass(frozen=True)
class CandidateRow:
    candidate_id: str
    seqid: str
    gap_start: int
    gap_end: int
    gap_length: int
    left_run_length: int
    right_run_length: int
    span_length: int
    target: float
    stratum: str

    @property
    def crop_start(self) -> int:
        return self.gap_start - FLANK_BP

    @property
    def crop_end(self) -> int:
        return self.gap_end + FLANK_BP


@dataclass
class WindowFeatures:
    start: int
    end: int
    sequence: str
    logits: np.ndarray
    latent: np.ndarray


@dataclass(frozen=True)
class Sample:
    channels: np.ndarray
    geometry: np.ndarray
    target: float
    length: int
    stratum: str
    candidate_id: str


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_stage1_model():
    return _load_module(
        Path(__file__).with_name("stage1_model.py"), "gap_bridge_stage1_model",
    )


def load_c5():
    return _load_module(
        ROOT / "scripts/experiments/C5-HYBRID-PILOT-20260830/c5_hybrid_pilot.py",
        "gap_bridge_stage1_c5",
    )


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def length_stratum(length: int) -> str:
    if length == 1:
        return "1"
    if length == 2:
        return "2"
    if length <= 5:
        return "3-5"
    if length <= 20:
        return "6-20"
    if length <= 100:
        return "21-100"
    if length <= 512:
        return "101-512"
    raise ValueError(f"gap length outside frozen Stage 1 range: {length}")


def _parse_int(row: dict[str, str], field: str) -> int:
    value = int(row[field])
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def load_training_candidates(path: Path) -> list[CandidateRow]:
    required = {
        "candidate_id", "seqid", "role", "comparator_known", "gap_start", "gap_end",
        "gap_length", "left_run_start", "left_run_end", "right_run_start", "right_run_end",
        "target_negative_fraction", "length_stratum",
        "positive_bp", "negative_bp", "unknown_bp",
    }
    rows: list[CandidateRow] = []
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("candidate manifest lacks frozen Stage 1 fields")
        for row in reader:
            seqid = row["seqid"]
            if row["role"] == "TRAIN" and seqid not in CHROMOSOMES:
                raise ValueError(f"TRAIN candidate outside explicit chromosomes: {seqid}")
            if seqid not in CHROMOSOMES or row["role"] != "TRAIN":
                continue
            if row["comparator_known"] != "1":
                continue
            candidate_id = row["candidate_id"]
            if candidate_id in seen:
                raise ValueError(f"duplicate training candidate: {candidate_id}")
            seen.add(candidate_id)
            gap_start, gap_end = _parse_int(row, "gap_start"), _parse_int(row, "gap_end")
            gap_length = _parse_int(row, "gap_length")
            left_start, left_end = _parse_int(row, "left_run_start"), _parse_int(row, "left_run_end")
            right_start, right_end = _parse_int(row, "right_run_start"), _parse_int(row, "right_run_end")
            span_length = right_end - left_start
            if gap_end <= gap_start or gap_end - gap_start != gap_length or gap_length > 512:
                raise ValueError(f"invalid candidate gap geometry: {candidate_id}")
            if left_end - left_start <= 0 or right_end - right_start <= 0:
                raise ValueError(f"invalid P3 flank geometry: {candidate_id}")
            positive = _parse_int(row, "positive_bp")
            negative = _parse_int(row, "negative_bp")
            unknown = _parse_int(row, "unknown_bp")
            if unknown != 0 or positive + negative != gap_length:
                raise ValueError(f"known candidate label does not sum to its gap: {candidate_id}")
            target = float(row["target_negative_fraction"])
            if not math.isfinite(target) or target < 0 or target > 1:
                raise ValueError(f"invalid candidate target: {candidate_id}")
            if not math.isclose(target, negative / gap_length, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError(f"candidate target disagrees with negative bp: {candidate_id}")
            stratum = row["length_stratum"]
            if stratum != length_stratum(gap_length):
                raise ValueError(f"candidate length stratum disagrees with gap: {candidate_id}")
            rows.append(CandidateRow(
                candidate_id=candidate_id,
                seqid=seqid,
                gap_start=gap_start,
                gap_end=gap_end,
                gap_length=gap_length,
                left_run_length=left_end - left_start,
                right_run_length=right_end - right_start,
                span_length=span_length,
                target=target,
                stratum=stratum,
            ))
    if not rows:
        raise ValueError("candidate manifest contains no known TRAIN rows on chr3/chr5")
    missing = set(LENGTH_STRATA) - {row.stratum for row in rows}
    if missing:
        raise ValueError(f"training manifest lacks frozen length strata: {sorted(missing)}")
    return rows


def scalar_values(candidate: CandidateRow) -> np.ndarray:
    center = (candidate.gap_start + candidate.gap_end) / 2.0
    remainder = center % WINDOW
    left_distance = remainder
    right_distance = WINDOW - remainder
    lower_boundary = math.floor(center / WINDOW) * WINDOW
    upper_boundary = lower_boundary + WINDOW
    boundary = lower_boundary if left_distance <= right_distance else upper_boundary
    distance = abs(boundary - center)
    direction = float(np.sign(boundary - center))
    crosses = int(candidate.crop_start // WINDOW != (candidate.crop_end - 1) // WINDOW)
    values = np.asarray([
        math.log1p(candidate.gap_length),
        math.log1p(candidate.left_run_length),
        math.log1p(candidate.right_run_length),
        math.log1p(candidate.span_length),
        float(crosses),
        math.log1p(distance),
        direction,
    ], dtype=np.float32)
    if not np.all(np.isfinite(values)):
        raise ValueError(f"non-finite geometry scalars: {candidate.candidate_id}")
    return values


def scalar_stats(candidates: Iterable[CandidateRow]) -> dict[str, object]:
    values = np.asarray([scalar_values(candidate) for candidate in candidates], dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != GEOMETRY_SCALARS or not len(values):
        raise ValueError("cannot fit scalar statistics on empty candidates")
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    if np.any(scale == 0):
        zero_fields = [SCALAR_FIELDS[index] for index, value in enumerate(scale) if value == 0]
        raise ValueError(f"zero-variance geometry scalar(s): {zero_fields}")
    return {
        "schema": "gap_bridge_neural_stage1_scalar_stats_v1",
        "fields": list(SCALAR_FIELDS),
        "count": int(values.shape[0]),
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "fit_population": "role=TRAIN and comparator_known=1 on chr3+chr5 only",
    }


def standardized_scalars(candidate: CandidateRow, stats: dict[str, object]) -> np.ndarray:
    raw = scalar_values(candidate).astype(np.float32)
    mean = np.asarray(stats["mean"], dtype=np.float32)
    scale = np.asarray(stats["scale"], dtype=np.float32)
    if mean.shape != (GEOMETRY_SCALARS,) or scale.shape != (GEOMETRY_SCALARS,):
        raise ValueError("scalar stats shape is not frozen seven-dimensional geometry")
    result = (raw - mean) / scale
    if not np.all(np.isfinite(result)):
        raise ValueError(f"non-finite standardized geometry: {candidate.candidate_id}")
    return result


def iter_region_records(path: Path, seqid: str) -> Iterator[tuple[int, int, str]]:
    expected_start = 0
    windows = 0
    with _open_text(path) as handle:
        for index, raw in enumerate(handle):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row.get("chr") != seqid:
                raise ValueError(f"region row {index} is not {seqid}")
            start, end = int(row["start"]), int(row["end"])
            sequence = str(row["sequence"]).upper()
            if start != expected_start or end <= start or end - start != len(sequence):
                raise ValueError(f"non-contiguous region rows for {seqid}")
            if end - start > WINDOW or start % WINDOW != 0:
                raise ValueError(f"region row is not a frozen 8192 window: {seqid}:{start}-{end}")
            labels = row.get("labels")
            if labels is not None and len(labels) != end - start:
                raise ValueError(f"region labels disagree with sequence length: {seqid}:{start}-{end}")
            yield start, end, sequence
            expected_start = end
            windows += 1
    if windows == 0:
        raise ValueError(f"empty region asset for {seqid}")


def _slice_array(array: np.ndarray, start: int, end: int, region_start: int, axis: int = 0) -> np.ndarray:
    left, right = start - region_start, end - region_start
    if axis == 0:
        return array[left:right]
    return array[:, left:right]


def assemble_crop(
    previous: WindowFeatures | None,
    current: WindowFeatures,
    crop_start: int,
    crop_end: int,
) -> tuple[str, np.ndarray, np.ndarray]:
    """Assemble one crop from current data and at most one previous carry."""
    if crop_end <= crop_start or crop_end - crop_start > MAX_INPUT_BP:
        raise ValueError("candidate crop length is outside the frozen 1024-bp input")
    if current.start <= crop_start and crop_end <= current.end:
        return (
            current.sequence[crop_start - current.start:crop_end - current.start],
            _slice_array(current.logits, crop_start, crop_end, current.start),
            _slice_array(current.latent, crop_start, crop_end, current.start, axis=1),
        )
    if previous is None or previous.end != current.start:
        raise ValueError("cross-window crop has no contiguous previous carry")
    if previous.start <= crop_start < previous.end and current.start < crop_end <= current.end:
        previous_sequence = previous.sequence[crop_start - previous.start:]
        current_sequence = current.sequence[:crop_end - current.start]
        sequence = previous_sequence + current_sequence
        logits = np.concatenate((
            _slice_array(previous.logits, crop_start, previous.end, previous.start),
            _slice_array(current.logits, current.start, crop_end, current.start),
        ), axis=0)
        latent = np.concatenate((
            _slice_array(previous.latent, crop_start, previous.end, previous.start, axis=1),
            _slice_array(current.latent, current.start, crop_end, current.start, axis=1),
        ), axis=1)
        return sequence, logits, latent
    raise ValueError("candidate crop crosses more than the retained adjacent window carry")


def build_channels(
    sequence: str,
    logits: np.ndarray,
    latent: np.ndarray,
    candidate: CandidateRow,
) -> np.ndarray:
    length = len(sequence)
    if length != candidate.crop_end - candidate.crop_start or length > MAX_INPUT_BP:
        raise ValueError(f"candidate crop sequence length disagrees: {candidate.candidate_id}")
    if logits.shape != (length, 4):
        raise ValueError(f"P3 logits have wrong crop shape: {candidate.candidate_id}")
    if latent.shape != (LATENT_WIDTH, length):
        raise ValueError(f"decoded latent has wrong crop shape: {candidate.candidate_id}")
    if not set(sequence) <= set(BASES):
        raise ValueError(f"training crop contains non-ACGT base: {candidate.candidate_id}")
    channels = np.zeros((CHANNELS, MAX_INPUT_BP), dtype=np.float32)
    channels[0:3, :length] = (logits[:, 1:] - logits[:, :1]).T
    logits_max = logits - logits.max(axis=1, keepdims=True)
    probabilities = np.exp(logits_max)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    channels[3, :length] = (probabilities[:, 1:].sum(axis=1) >= 0.5).astype(np.float32)
    channels[4, :FLANK_BP] = 1.0
    channels[5, FLANK_BP:FLANK_BP + candidate.gap_length] = 1.0
    channels[6, FLANK_BP + candidate.gap_length:length] = 1.0
    relative_positions = np.arange(length, dtype=np.float32) - FLANK_BP
    channels[7, :length] = np.clip(relative_positions / 512.0, -1.0, 1.0)
    channels[8, :length] = np.clip(
        (relative_positions - candidate.gap_length) / 512.0, -1.0, 1.0,
    )
    channels[9, :length] = 1.0
    for index, base in enumerate(BASES):
        channels[10 + index, :length] = np.fromiter(
            (float(value == base) for value in sequence), dtype=np.float32, count=length,
        )
    channels[14, length:] = 1.0
    channels[15:, :length] = latent
    if not np.all(np.isfinite(channels)):
        raise ValueError(f"non-finite Stage 1 input channels: {candidate.candidate_id}")
    return channels


def _p3_forward(model, tokenizer, device, sequence: str) -> WindowFeatures:
    import torch

    if len(sequence) > WINDOW:
        raise ValueError("P3 input sequence exceeds frozen 8192 context")
    encoded = tokenizer(
        sequence, add_special_tokens=False, truncation=True,
        max_length=WINDOW, padding="max_length", return_tensors="pt",
    )
    inputs = {
        key: value.to(device)
        for key, value in encoded.items()
        if key in {"input_ids", "attention_mask"}
    }
    captured: dict[str, torch.Tensor] = {}

    def capture_classifier(_module, inputs, _output):
        captured["decoded"] = inputs[0]

    handle = model.classifier.register_forward_hook(capture_classifier)
    try:
        with torch.no_grad():
            output = model(**inputs)
    finally:
        handle.remove()
    logits = output.logits
    if tuple(logits.shape) != (1, WINDOW, 4):
        raise ValueError(f"frozen P3 logits have unexpected shape: {tuple(logits.shape)}")
    decoded = captured.get("decoded")
    if decoded is None or tuple(decoded.shape) != (1, LATENT_WIDTH, WINDOW):
        shape = None if decoded is None else tuple(decoded.shape)
        raise ValueError(f"frozen P3 decoded hook has unexpected shape: {shape}")
    length = len(sequence)
    return WindowFeatures(
        start=0,
        end=length,
        sequence=sequence,
        logits=logits[0, :length].detach().cpu().numpy().astype(np.float32, copy=False),
        latent=decoded[0, :, :length].detach().cpu().numpy().astype(np.float32, copy=False),
    )


def _p3_forward_window(model, tokenizer, device, start: int, end: int, sequence: str) -> WindowFeatures:
    features = _p3_forward(model, tokenizer, device, sequence)
    features.start = start
    features.end = end
    return features


def _pop_ready_batch(pending: list[Sample], final: bool = False) -> list[Sample] | None:
    if not pending:
        return None
    if len(pending) < BATCH_SIZE and not final:
        return None
    size = min(BATCH_SIZE, len(pending))
    selected = pending[:size]
    del pending[:size]
    return selected


def _make_batch(samples: list[Sample], stats: dict[str, object]):
    import torch

    channels = torch.from_numpy(np.stack([sample.channels for sample in samples])).float()
    geometry = torch.from_numpy(np.stack([sample.geometry for sample in samples])).float()
    targets = torch.as_tensor([sample.target for sample in samples], dtype=torch.float32)
    lengths = torch.as_tensor([sample.length for sample in samples], dtype=torch.float32)
    strata = [sample.stratum for sample in samples]
    return channels, geometry, targets, lengths, strata


def _sample_from_crop(
    candidate: CandidateRow,
    sequence: str,
    logits: np.ndarray,
    latent: np.ndarray,
    stats: dict[str, object],
) -> Sample:
    return Sample(
        channels=build_channels(sequence, logits, latent, candidate),
        geometry=standardized_scalars(candidate, stats),
        target=candidate.target,
        length=candidate.gap_length,
        stratum=candidate.stratum,
        candidate_id=candidate.candidate_id,
    )


def _train_one_batch(
    heads,
    optimizer,
    samples: list[Sample],
    stats: dict[str, object],
    global_weights: dict[str, float],
    device,
) -> dict[str, float]:
    import torch

    channels, geometry, targets, _lengths, _strata = _make_batch(samples, stats)
    channels = channels.to(device)
    geometry = geometry.to(device)
    targets = targets.to(device)
    weights = torch.as_tensor(
        [global_weights[sample.candidate_id] for sample in samples],
        dtype=torch.float32,
        device=device,
    )
    batch_weight_mean = weights.mean()
    if not torch.isfinite(weights).all() or torch.any(weights <= 0) or not torch.isfinite(batch_weight_mean):
        raise ValueError("frozen global sample weights are not finite and positive")
    # The frozen model API validates a mean-one weight vector.  Normalizing only
    # this call and restoring its mean leaves the batch BCE exactly weighted by
    # the globally fitted candidate weights, including a final partial batch.
    normalized_weights = weights / batch_weight_mean
    optimizer.zero_grad(set_to_none=True)
    losses: dict[str, float] = {}
    stage1_model = heads["_stage1_model"]
    arm_inputs = {
        arm: stage1_model.apply_arm_input(channels, arm)
        for arm in stage1_model.ARMS
    }
    train_heads = {
        key: head for key, head in heads.items() if key != "_stage1_model"
    }
    for key, head in train_heads.items():
        arm = key.split("__", 1)[0]
        logits = head.forward_prepared(arm_inputs[arm], geometry)
        loss = stage1_model.soft_target_bce(
            logits, targets, normalized_weights,
        ) * batch_weight_mean
        loss.backward()
        torch.nn.utils.clip_grad_norm_(head.parameters(), 1.0)
        losses[key] = float(loss.detach().cpu())
    optimizer.step()
    return losses


def global_sample_weights(stage1_model, candidates: list[CandidateRow]) -> dict[str, float]:
    """Fit the frozen six-stratum weights once on the complete TRAIN population."""
    import torch

    lengths = torch.as_tensor([candidate.gap_length for candidate in candidates], dtype=torch.float32)
    strata = [candidate.stratum for candidate in candidates]
    weights = stage1_model.stratum_sample_weights(lengths, strata)
    if not torch.isfinite(weights).all() or torch.any(weights <= 0):
        raise ValueError("frozen global sample weights are not finite and positive")
    if not torch.isclose(weights.mean(), weights.new_tensor(1.0), atol=1e-6, rtol=1e-6):
        raise ValueError("frozen global sample weights are not mean-one")
    return {
        candidate.candidate_id: float(weight)
        for candidate, weight in zip(candidates, weights.tolist())
    }


def _make_heads(stage1_model, device):
    import torch

    heads: dict[str, object] = {"_stage1_model": stage1_model}
    for seed in SEEDS:
        for arm in stage1_model.ARMS:
            torch.manual_seed(seed)
            head = stage1_model.GapHead(arm).to(device)
            head.train()
            heads[f"{arm}__seed{seed}"] = head
    return heads


def _candidate_anchors(candidates: Iterable[CandidateRow]) -> dict[str, dict[int, list[CandidateRow]]]:
    result: dict[str, dict[int, list[CandidateRow]]] = {
        seqid: defaultdict(list) for seqid in CHROMOSOMES
    }
    for candidate in candidates:
        anchor = (candidate.crop_end - 1) // WINDOW
        result[candidate.seqid][anchor].append(candidate)
    for by_anchor in result.values():
        for rows in by_anchor.values():
            rows.sort(key=lambda row: (row.crop_start, row.crop_end, row.candidate_id))
    return result


def _train_pass(
    model,
    tokenizer,
    device,
    region_paths: dict[str, Path],
    candidates: list[CandidateRow],
    stats: dict[str, object],
    global_weights: dict[str, float],
    heads,
    optimizer,
) -> dict[str, object]:
    anchors = _candidate_anchors(candidates)
    pending: list[Sample] = []
    seen: set[str] = set()
    batches = 0
    samples_seen = 0
    windows_forwarded = {seqid: 0 for seqid in CHROMOSOMES}
    losses = {key: 0.0 for key in heads if key != "_stage1_model"}
    for seqid in CHROMOSOMES:
        previous: WindowFeatures | None = None
        for start, end, sequence in iter_region_records(region_paths[seqid], seqid):
            current = _p3_forward_window(model, tokenizer, device, start, end, sequence)
            windows_forwarded[seqid] += 1
            for candidate in anchors[seqid].get(start // WINDOW, []):
                crop_sequence, crop_logits, crop_latent = assemble_crop(
                    previous, current, candidate.crop_start, candidate.crop_end,
                )
                sample = _sample_from_crop(
                    candidate, crop_sequence, crop_logits, crop_latent, stats,
                )
                pending.append(sample)
                seen.add(candidate.candidate_id)
                while True:
                    batch = _pop_ready_batch(pending)
                    if batch is None:
                        break
                    batch_losses = _train_one_batch(
                        heads, optimizer, batch, stats, global_weights, device,
                    )
                    batches += 1
                    samples_seen += len(batch)
                    for key, value in batch_losses.items():
                        losses[key] += value
            previous = current
    if seen != {candidate.candidate_id for candidate in candidates}:
        missing = sorted({candidate.candidate_id for candidate in candidates} - seen)
        raise ValueError(f"training candidates were not covered by region windows: {missing[:3]}")
    while True:
        batch = _pop_ready_batch(pending, final=True)
        if batch is None:
            break
        batch_losses = _train_one_batch(
            heads, optimizer, batch, stats, global_weights, device,
        )
        batches += 1
        samples_seen += len(batch)
        for key, value in batch_losses.items():
            losses[key] += value
    return {
        "batches": batches,
        "samples_optimized": samples_seen,
        "samples_deferred_or_unoptimized": len(pending),
        "loss_sum_by_head": losses,
        "windows_forwarded_by_chromosome": windows_forwarded,
    }


def _paired_initialization_check(heads) -> bool:
    for seed in SEEDS:
        states = [heads[f"{arm}__seed{seed}"].state_dict() for arm in heads["_stage1_model"].ARMS]
        keys = list(states[0])
        if any(not all(torch_equal(states[0][key], state[key]) for state in states[1:]) for key in keys):
            return False
    return True


def torch_equal(left, right) -> bool:
    import torch
    return torch.equal(left, right)


def train(
    candidate_manifest: Path,
    chr3_region: Path,
    chr5_region: Path,
    model_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    import torch

    stage1_model = load_stage1_model()
    candidates = load_training_candidates(candidate_manifest)
    stats = scalar_stats(candidates)
    global_weights = global_sample_weights(stage1_model, candidates)
    if output_dir.exists():
        raise ValueError(f"refusing to reuse Stage 1 training output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "scalar_stats.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )

    c5 = load_c5()
    model, tokenizer, metadata, device, _te = c5.load_p3_model(model_dir)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    heads = _make_heads(stage1_model, device)
    if not _paired_initialization_check(heads):
        raise RuntimeError("paired Stage 1 arm initialization is not identical")
    train_heads = [head for key, head in heads.items() if key != "_stage1_model"]
    optimizer = torch.optim.AdamW(
        [parameter for head in train_heads for parameter in head.parameters()],
        lr=3e-4, weight_decay=1e-4, betas=(0.9, 0.999),
    )
    region_paths = {"chr3": chr3_region, "chr5": chr5_region}
    pass_summaries = []
    for pass_index in range(PASSES):
        pass_result = _train_pass(
            model, tokenizer, device, region_paths, candidates, stats,
            global_weights, heads, optimizer,
        )
        pass_result["pass"] = pass_index + 1
        pass_summaries.append(pass_result)

    heads_dir = output_dir / "heads"
    heads_dir.mkdir()
    for key, head in heads.items():
        if key == "_stage1_model":
            continue
        torch.save(
            {name: value.detach().cpu() for name, value in head.state_dict().items()},
            heads_dir / f"{key}.pt",
        )
    summary: dict[str, object] = {
        "schema": "gap_bridge_neural_stage1_training_v1",
        "status": "PASS",
        "candidate_manifest": str(candidate_manifest),
        "model_dir": str(model_dir),
        "model_schema": metadata["schema"],
        "backbone_frozen_eval": True,
        "p3_forward_context": {"window": WINDOW, "stride": WINDOW, "forward_once_per_window": True},
        "latent_hook": "TEUNetSegmenter.classifier input decoded map",
        "latent_shape_per_window": [1, LATENT_WIDTH, WINDOW],
        "latent_written_to_disk": False,
        "crop": {"left_flank_bp": FLANK_BP, "right_flank_bp": FLANK_BP, "max_bp": MAX_INPUT_BP, "right_pad": True},
        "arms": list(stage1_model.ARMS),
        "seeds": list(SEEDS),
        "paired_initialization": True,
        "optimizer": {"name": "AdamW", "lr": 3e-4, "weight_decay": 1e-4, "betas": [0.9, 0.999]},
        "batch_size": BATCH_SIZE,
        "passes": PASSES,
        "gradient_clip_norm": 1.0,
        "dropout": 0.1,
        "sample_weighting": {
            "fit_population": "all role=TRAIN and comparator_known=1 rows on chr3+chr5",
            "normalization": "global mean one; equal total weight per length stratum; proportional to gap length within stratum",
            "candidate_count": len(global_weights),
        },
        "training_rows": len(candidates),
        "training_rows_by_chromosome": {
            seqid: sum(row.seqid == seqid for row in candidates) for seqid in CHROMOSOMES
        },
        "training_rows_by_stratum": {
            stratum: sum(row.stratum == stratum for row in candidates) for stratum in LENGTH_STRATA
        },
        "pass_summaries": pass_summaries,
        "output_heads": [str(path.relative_to(output_dir)) for path in sorted(heads_dir.glob("*.pt"))],
        "chr13_read": False,
        "chr19_read": False,
        "calibration_or_scoring_executed": False,
        "scientific_metrics_computed": False,
    }
    (output_dir / "training_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output_dir / "STATUS").write_text("PASS\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--chr3-region", required=True, type=Path)
    parser.add_argument("--chr5-region", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = train(
        args.candidate_manifest, args.chr3_region, args.chr5_region,
        args.model_dir, args.output_dir,
    )
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
