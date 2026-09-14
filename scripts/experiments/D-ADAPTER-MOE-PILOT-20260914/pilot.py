#!/usr/bin/env python3
"""Bounded frozen-feature adapter and prediction-head MoE pilot.

The backbone is loaded once from the frozen six-species D checkpoint.  Final
token hidden states and D logits are materialized in memory for a fixed small
selection of tiles.  Only the residual prediction heads below are trained;
the model is not a sparse/routed backbone.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import importlib.util
import json
import math
import os
import random
import sys
import time
import traceback
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
WINDOW_BP = 4096
TE_BP_WEIGHT = 3.0


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY = _load_module(
    "d_adapter_legacy_calibration",
    REPO_ROOT / "scripts/experiments/CROSS-SPECIES-L1-20260903/calibrate_evaluate_x0.py",
)
TOKEN_TASK = _load_module(
    "d_adapter_token_task",
    REPO_ROOT / "scripts/experiments/CROSS-SPECIES-L1-20260903/cross_species_token_task.py",
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_config(path: Path) -> dict:
    value = json.loads(path.read_text())
    if value.get("experiment") != "D-ADAPTER-MOE-PILOT-20260914":
        raise ValueError("unexpected adapter/MoE config")
    return value


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def source_path(config: dict, key: str, root: Path) -> Path:
    value = Path(config["remote"][key])
    return value if value.is_absolute() else root / value


def data_path(config: dict, root: Path, species: str, split: str) -> Path:
    if species == "c_elegans" and split == "TRAIN":
        return source_path(config, "worm_train_override", root)
    return source_path(config, "data_root", root) / split / f"{species}.jsonl.gz"


def _record_is_complete(record: dict, species: str, split: str) -> bool:
    return (
        record.get("species_code") == species
        and record.get("split") == split
        and len(str(record.get("sequence", ""))) == WINDOW_BP
        and len(str(record.get("labels", ""))) == WINDOW_BP
        and int(record.get("half", -1)) in (0, 1)
    )


def read_first_complete_tiles(
    path: Path, species: str, split: str, count: int
) -> tuple[list[dict], dict]:
    """Read a bounded source-order selection of complete two-half tiles."""

    groups: OrderedDict[str, dict[int, dict]] = OrderedDict()
    invalid: set[str] = set()
    selected_ids: list[str] = []
    invalid_records = 0
    duplicate_halves = 0
    with gzip.open(path, "rt") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = json.loads(line)
            tile_id = str(record.get("tile_id", ""))
            if not _record_is_complete(record, species, split):
                invalid_records += 1
                if tile_id:
                    invalid.add(tile_id)
                continue
            half = int(record["half"])
            tile = groups.setdefault(tile_id, {})
            if half in tile:
                duplicate_halves += 1
                invalid.add(tile_id)
                continue
            tile[half] = record
            if set(tile) == {0, 1} and tile_id not in invalid:
                selected_ids.append(tile_id)
                if len(selected_ids) == count:
                    break
    if len(selected_ids) != count:
        raise RuntimeError(
            f"{path}: found {len(selected_ids)} complete tiles, expected {count}"
        )
    records: list[dict] = []
    for tile_id in selected_ids:
        halves = groups[tile_id]
        records.extend((halves[0], halves[1]))
    return records, {
        "path": str(path),
        "species": species,
        "split": split,
        "selection": "first complete tiles in source order",
        "tiles": len(selected_ids),
        "records": len(records),
        "tile_ids": selected_ids,
        "invalid_records_seen_before_stop": invalid_records,
        "duplicate_halves_seen_before_stop": duplicate_halves,
    }


def _encoding_with_positions(tokenizer, record: dict) -> tuple[dict, np.ndarray]:
    """Use the project encoder and retain its attended non-special positions."""

    encoded = TOKEN_TASK.encode_record(tokenizer, record)
    tokens = TOKEN_TASK.sequence_tokens(record["sequence"])
    tensor_tokens = ((len(tokens) + 2 + 7) // 8) * 8
    raw = tokenizer(
        tokens,
        is_split_into_words=True,
        truncation=True,
        max_length=tensor_tokens,
        padding="max_length",
        return_special_tokens_mask=True,
    )
    positions = np.asarray(
        [
            index
            for index, (attention, special) in enumerate(
                zip(raw["attention_mask"], raw["special_tokens_mask"])
            )
            if attention and not special
        ],
        dtype=np.int64,
    )
    if len(positions) != len(TOKEN_TASK.label_chunk_masses(record["labels"])[0]):
        raise ValueError("encoder token count differs from label chunk count")
    if not np.array_equal(np.asarray(raw["input_ids"]), encoded["input_ids"].numpy()):
        raise ValueError("project encoder and position probe disagree on input_ids")
    return encoded, positions


def _make_tile_feature(species: str, split: str, records: list[dict]) -> dict:
    by_tile: OrderedDict[str, dict[int, dict]] = OrderedDict()
    for record in records:
        by_tile.setdefault(str(record["tile_id"]), {})[int(record["half"])] = record
    return {
        "species": species,
        "split": split,
        "tile_id": str(records[0]["tile_id"]),
        "assembly": records[0]["assembly"],
        "chrom": records[0]["chrom"],
        "start": int(records[0]["start"]),
        "end": int(records[1]["end"]),
        "halves": {},
    }


def _group_records(records: list[dict]) -> list[tuple[dict, dict]]:
    grouped: OrderedDict[str, dict[int, dict]] = OrderedDict()
    for record in records:
        grouped.setdefault(str(record["tile_id"]), {})[int(record["half"])] = record
    if any(set(halves) != {0, 1} for halves in grouped.values()):
        raise ValueError("selected tile is missing half 0 or half 1")
    return [(halves[0], halves[1]) for halves in grouped.values()]


def extract_features(
    model,
    tokenizer,
    device: torch.device,
    selected: dict[str, dict[str, list[dict]]],
    batch_size: int,
    species_order: tuple[str, ...] = SPECIES,
) -> dict[str, dict[str, list[dict]]]:
    """Extract D final hidden states and base logits for selected halves."""

    features: dict[str, dict[str, list[dict]]] = {}
    model.eval()
    for species in species_order:
        features[species] = {}
        for split in selected[species]:
            print(f"[extract] {species} {split}", flush=True)
            pairs = _group_records(selected[species][split])
            tiles = []
            for left, right in pairs:
                tile = _make_tile_feature(species, split, [left, right])
                tile["tile_id"] = str(left["tile_id"])
                tile["halves"] = {0: None, 1: None}
                tiles.append(tile)
            flat_records = [record for pair in pairs for record in pair]
            probes = [_encoding_with_positions(tokenizer, record) for record in flat_records]
            for offset in range(0, len(flat_records), batch_size):
                batch_records = flat_records[offset : offset + batch_size]
                batch_probes = probes[offset : offset + batch_size]
                input_ids = torch.stack([probe[0]["input_ids"] for probe in batch_probes]).to(device)
                attention_mask = torch.stack(
                    [probe[0]["attention_mask"] for probe in batch_probes]
                ).to(device)
                with torch.no_grad():
                    output = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        output_hidden_states=True,
                    )
                if output.hidden_states is None or len(output.hidden_states) == 0:
                    raise RuntimeError("D model did not return hidden states")
                final_hidden = output.hidden_states[-1].detach().float().cpu()
                base_logits = output.logits.detach().float().cpu()
                for local, (record, probe) in enumerate(zip(batch_records, batch_probes)):
                    encoded, positions = probe
                    token_positions = torch.as_tensor(positions, dtype=torch.long)
                    positive = encoded["positive_bp"][token_positions].numpy().astype(np.float32)
                    negative = encoded["negative_bp"][token_positions].numpy().astype(np.float32)
                    truth, callable_mask, hard_negative = LEGACY.decode_labels(record["labels"])
                    hidden = final_hidden[local, token_positions].numpy().astype(np.float16)
                    logits = base_logits[local, token_positions].numpy().astype(np.float32)
                    tile_index = offset + local
                    tile = tiles[tile_index // 2]
                    half = int(record["half"])
                    tile["halves"][half] = {
                        "hidden": hidden,
                        "base_logits": logits,
                        "positive_bp": positive,
                        "negative_bp": negative,
                        "truth": truth.astype(bool),
                        "callable": callable_mask.astype(bool),
                        "hard_negative": hard_negative.astype(bool),
                        "token_count": int(len(positions)),
                    }
                del output, final_hidden, base_logits, input_ids, attention_mask
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            for tile in tiles:
                if tile["halves"][0] is None or tile["halves"][1] is None:
                    raise RuntimeError(f"missing extracted half for {tile['tile_id']}")
            features[species][split] = tiles
    return features


def _base_margin(half: dict) -> np.ndarray:
    logits = half["base_logits"]
    return (logits[:, 1] - logits[:, 0]).astype(np.float32)


def _tile_records_from_features(
    features: dict[str, list[dict]], arm, device: torch.device,
    species_order: tuple[str, ...] = SPECIES,
) -> dict[str, list[dict]]:
    """Project token margins from a frozen or trained head back to BP tiles."""

    result: dict[str, list[dict]] = {}
    for species in species_order:
        result[species] = []
        for tile in features[species]:
            bp_parts = []
            truth_parts = []
            callable_parts = []
            hard_parts = []
            for half_index in (0, 1):
                half = tile["halves"][half_index]
                if arm is None:
                    token_margin = _base_margin(half)
                else:
                    hidden = torch.from_numpy(half["hidden"].astype(np.float32)).to(device)
                    base_logits = torch.from_numpy(half["base_logits"]).to(device)
                    with torch.no_grad():
                        logits, _ = arm(hidden, base_logits)
                    token_margin = (
                        logits[:, 1] - logits[:, 0]
                    ).detach().cpu().numpy().astype(np.float32)
                bp_margin = LEGACY.project_token_margins(
                    token_margin,
                    list(range(len(token_margin))),
                    WINDOW_BP,
                )
                bp_parts.append(bp_margin)
                truth_parts.append(tile["halves"][half_index]["truth"])
                callable_parts.append(tile["halves"][half_index]["callable"])
                hard_parts.append(tile["halves"][half_index]["hard_negative"])
            result[species].append(
                {
                    "species": species,
                    "assembly": tile["assembly"],
                    "split": tile["split"],
                    "tile_id": tile["tile_id"],
                    "chrom": tile["chrom"],
                    "start": tile["start"],
                    "end": tile["end"],
                    "margin": np.concatenate(bp_parts),
                    "truth": np.concatenate(truth_parts),
                    "callable": np.concatenate(callable_parts),
                    "hard_negative": np.concatenate(hard_parts),
                }
            )
    return result


def calibration_for_tiles(tiles: dict[str, list[dict]]) -> dict:
    data = LEGACY.callable_arrays(tiles)
    slope, intercept, loss = LEGACY.fit_platt(data)
    calibrated = {
        species: (LEGACY.sigmoid(slope * margins + intercept), truth)
        for species, (margins, truth) in data.items()
    }
    selection = LEGACY.select_global_threshold(calibrated)
    per_species, summary = LEGACY.evaluate(
        tiles, slope, intercept, selection["threshold"]
    )
    return {
        "platt_slope": float(slope),
        "platt_intercept": float(intercept),
        "calibration_loss": float(loss),
        "threshold": float(selection["threshold"]),
        "threshold_selection": selection,
        "per_species": per_species,
        "summary": summary,
    }


def _weighted_token_loss(
    logits: torch.Tensor,
    positive_bp: torch.Tensor,
    negative_bp: torch.Tensor,
) -> torch.Tensor | None:
    valid = (positive_bp + negative_bp) > 0
    if not torch.any(valid):
        return None
    log_probability = F.log_softmax(logits.float(), dim=-1)
    pos = positive_bp[valid]
    neg = negative_bp[valid]
    lp = log_probability[valid]
    numerator = -(neg * lp[:, 0] + TE_BP_WEIGHT * pos * lp[:, 1]).sum()
    denominator = (neg + TE_BP_WEIGHT * pos).sum()
    if float(denominator.detach().cpu()) <= 0:
        return None
    return numerator / denominator


class ResidualExpert(nn.Module):
    def __init__(self, hidden_size: int, bottleneck_width: int):
        super().__init__()
        self.down = nn.Linear(hidden_size, bottleneck_width)
        self.up = nn.Linear(bottleneck_width, 2)
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.up(torch.tanh(self.down(hidden)))


class DenseResidualAdapter(nn.Module):
    arm_name = "dense_residual_adapter"

    def __init__(self, hidden_size: int = 1024):
        super().__init__()
        self.expert = ResidualExpert(hidden_size, 64)

    def forward(
        self, hidden: torch.Tensor, base_logits: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        return base_logits + self.expert(hidden), None


class TwoExpertSoftGate(nn.Module):
    arm_name = "two_expert_soft_gate_residual_adapter"

    def __init__(self, hidden_size: int = 1024):
        super().__init__()
        self.experts = nn.ModuleList(
            [ResidualExpert(hidden_size, 32), ResidualExpert(hidden_size, 32)]
        )
        self.gate = nn.Linear(hidden_size, 2)

    def forward(
        self, hidden: torch.Tensor, base_logits: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        residuals = torch.stack([expert(hidden) for expert in self.experts], dim=-2)
        weights = torch.softmax(self.gate(hidden.detach()), dim=-1)
        residual = (weights.unsqueeze(-1) * residuals).sum(dim=-2)
        return base_logits + residual, weights


class ConstantAverageExperts(nn.Module):
    arm_name = "constant_average_experts"

    def __init__(self, hidden_size: int = 1024):
        super().__init__()
        self.experts = nn.ModuleList(
            [ResidualExpert(hidden_size, 32), ResidualExpert(hidden_size, 32)]
        )

    def forward(
        self, hidden: torch.Tensor, base_logits: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        residual = torch.stack([expert(hidden) for expert in self.experts], dim=0).mean(dim=0)
        weights = torch.full(
            (hidden.shape[0], 2), 0.5, dtype=hidden.dtype, device=hidden.device
        )
        return base_logits + residual, weights


def parameter_count(module: nn.Module) -> int:
    return int(sum(parameter.numel() for parameter in module.parameters() if parameter.requires_grad))


def _move_half(half: dict, device: torch.device) -> tuple[torch.Tensor, ...]:
    return (
        torch.from_numpy(half["hidden"].astype(np.float32)).to(device),
        torch.from_numpy(half["base_logits"]).to(device),
        torch.from_numpy(half["positive_bp"]).to(device),
        torch.from_numpy(half["negative_bp"]).to(device),
    )


def train_one_arm(
    arm: nn.Module,
    train_features: dict[str, list[dict]],
    cal_features: dict[str, list[dict]],
    device: torch.device,
    epochs: int,
    seed: int,
    species_order: tuple[str, ...] = SPECIES,
) -> dict:
    optimizer = torch.optim.AdamW(arm.parameters(), lr=1e-3, weight_decay=0.0)
    arm.to(device)
    arm.train()
    best_key = None
    best_epoch = None
    best_state = None
    trace = []
    steps_per_epoch = min(len(train_features[species]) for species in species_order)
    for epoch in range(1, epochs + 1):
        arm.train()
        epoch_losses = []
        skipped_masked_steps = 0
        for tile_index in range(steps_per_epoch):
            optimizer.zero_grad(set_to_none=True)
            species_losses = []
            for species in species_order:
                half_losses = []
                tile = train_features[species][tile_index]
                for half_index in (0, 1):
                    hidden, base_logits, positive, negative = _move_half(
                        tile["halves"][half_index], device
                    )
                    logits, _ = arm(hidden, base_logits)
                    loss = _weighted_token_loss(logits, positive, negative)
                    if loss is not None:
                        half_losses.append(loss)
                if half_losses:
                    species_losses.append(torch.stack(half_losses).mean())
            if not species_losses:
                # A whole sea tile can be masked by uncertain annotations.
                # It supplies no loss; retain its selection entry but no update.
                skipped_masked_steps += 1
                continue
            loss = torch.stack(species_losses).mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(arm.parameters(), 1.0)
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))

        if not epoch_losses:
            raise RuntimeError("entire TRAIN epoch has no callable bases")
        cal_tiles = _tile_records_from_features(
            cal_features, arm, device, species_order=species_order
        )
        cal = calibration_for_tiles(cal_tiles)
        key = (
            float(cal["summary"]["minimum_species_bp_f1"]),
            float(cal["summary"]["macro_bp_f1"]),
        )
        if best_key is None or key > best_key:
            best_key = key
            best_epoch = epoch
            best_state = copy.deepcopy(arm.state_dict())
        trace.append(
            {
                "epoch": epoch,
                "optimizer_steps": len(epoch_losses),
                "skipped_fully_masked_steps": skipped_masked_steps,
                "train_loss": float(np.mean(epoch_losses)),
                "cal_minimum_species_bp_f1": key[0],
                "cal_macro_bp_f1": key[1],
                "cal_threshold": float(cal["threshold"]),
                "cal_platt_slope": float(cal["platt_slope"]),
                "cal_platt_intercept": float(cal["platt_intercept"]),
            }
        )
        print(
            f"[train] {arm.arm_name} epoch={epoch} loss={trace[-1]['train_loss']:.6f} "
            f"cal_min={key[0]:.4f} cal_macro={key[1]:.4f}",
            flush=True,
        )
    if best_state is None or best_epoch is None:
        raise RuntimeError("no adapter epoch was selected")
    arm.load_state_dict(best_state)
    final_cal_tiles = _tile_records_from_features(
        cal_features, arm, device, species_order=species_order
    )
    final_cal = calibration_for_tiles(final_cal_tiles)
    return {
        "arm": arm,
        "selected_epoch": int(best_epoch),
        "train_steps_per_epoch": int(steps_per_epoch),
        "train_epochs": int(epochs),
        "trace": trace,
        "calibration": final_cal,
        "seed": seed,
    }


def route_statistics(
    arm: nn.Module,
    features: dict[str, list[dict]],
    device: torch.device,
    species_order: tuple[str, ...] = SPECIES,
) -> dict[str, dict]:
    if not isinstance(arm, (TwoExpertSoftGate, ConstantAverageExperts)):
        return {}
    result = {}
    arm.eval()
    with torch.no_grad():
        for species in species_order:
            weight_sum = np.zeros(2, dtype=np.float64)
            mass_sum = 0.0
            token_count = 0
            for tile in features[species]:
                for half_index in (0, 1):
                    half = tile["halves"][half_index]
                    hidden, base_logits, positive, negative = _move_half(half, device)
                    _, weights = arm(hidden, base_logits)
                    weights_np = weights.detach().cpu().numpy().astype(np.float64)
                    mass = (positive + negative).detach().cpu().numpy().astype(np.float64)
                    weight_sum += (weights_np * mass[:, None]).sum(axis=0)
                    mass_sum += float(mass.sum())
                    token_count += int(np.sum(mass > 0))
            result[species] = {
                "callable_bp_mass": mass_sum,
                "valid_token_count": token_count,
                "mean_expert_weight": (weight_sum / mass_sum).tolist()
                if mass_sum
                else [None, None],
            }
    return result


def smoke(config: dict) -> dict:
    """Small local engineering check that does not load data or a model."""
    set_seed(int(config["seed"]))
    hidden_size = int(config["model"]["hidden_size"])
    hidden = torch.zeros((7, hidden_size))
    base = torch.zeros((7, 2))
    outputs = {}
    arms = [DenseResidualAdapter(hidden_size), TwoExpertSoftGate(hidden_size), ConstantAverageExperts(hidden_size)]
    expected = [65730, 67782, 65732]
    for arm, expected_count in zip(arms, expected):
        logits, route = arm(hidden, base)
        if logits.shape != (7, 2):
            raise AssertionError(f"unexpected logits shape for {arm.arm_name}")
        if parameter_count(arm) != expected_count:
            raise AssertionError(
                f"{arm.arm_name}: {parameter_count(arm)} != {expected_count}"
            )
        outputs[arm.arm_name] = {
            "parameters": parameter_count(arm),
            "route_shape": list(route.shape) if route is not None else None,
        }
    loss = _weighted_token_loss(
        torch.zeros((7, 2)),
        torch.tensor([1, 0, 0, 2, 0, 0, 0], dtype=torch.float32),
        torch.tensor([5, 6, 1, 4, 0, 0, 0], dtype=torch.float32),
    )
    if loss is None or not math.isfinite(float(loss)):
        raise AssertionError("weighted token loss smoke failed")
    projected = LEGACY.project_token_margins(
        np.arange(686, dtype=np.float32), list(range(686)), WINDOW_BP
    )
    if projected.shape != (WINDOW_BP,) or not np.all(projected[:6] == 0):
        raise AssertionError("6-mer to base projection smoke failed")
    return {"status": "smoke_pass", "arms": outputs, "loss": float(loss)}


def _environment() -> dict:
    import transformers

    return {
        "python": sys.version,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def run(config_path: Path, output_dir: Path) -> dict:
    config = read_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "status.json",
        {"status": "starting", "config": str(config_path), "started_at": time.time()},
    )
    seed = int(config["seed"])
    set_seed(seed)
    root = Path(config["remote"]["project_root"])
    model_dir = source_path(config, "d_model", root)
    native_code_dir = source_path(config, "native_model_code", root)
    selected: dict[str, dict[str, list[dict]]] = {}
    manifest: dict[str, dict[str, dict]] = {}
    for species in SPECIES:
        selected[species] = {}
        manifest[species] = {}
        for split in ("TRAIN", "CAL", "DEV"):
            records, selection = read_first_complete_tiles(
                data_path(config, root, species, split),
                species,
                split,
                int(config["selection"]["tiles_per_species_per_split"]),
            )
            selected[species][split] = records
            manifest[species][split] = selection
    write_json(output_dir / "input_manifest.json", manifest)
    model, tokenizer, device = LEGACY.load_final_model(
        model_dir,
        model_dir,
        cpu=False,
        model_code_dir=native_code_dir,
    )
    if device.type != "cuda":
        raise RuntimeError("pilot requires the requested CUDA device")
    hidden_size = int(getattr(model.config, "hidden_size", 0))
    if hidden_size != int(config["model"]["hidden_size"]):
        raise RuntimeError(f"hidden size {hidden_size} differs from locked config")
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    features = extract_features(
        model,
        tokenizer,
        device,
        selected,
        int(config["training"]["feature_batch_size"]),
    )
    write_json(
        output_dir / "feature_manifest.json",
        {
            "status": "extracted_in_memory",
            "hidden_size": hidden_size,
            "feature_dtype": "float16_on_host",
            "base_logits_dtype": "float32_on_host",
            "model_dir": str(model_dir),
            "native_model_code": str(native_code_dir),
            "non_special_token_definition": config["model"]["final_hidden_definition"],
            "halves": sum(
                len(features[species][split]) * 2
                for species in SPECIES
                for split in ("TRAIN", "CAL", "DEV")
            ),
            "tokens": sum(
                half["token_count"]
                for species in SPECIES
                for split in ("TRAIN", "CAL", "DEV")
                for tile in features[species][split]
                for half in tile["halves"].values()
            ),
        },
    )
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    cal_base_tiles = _tile_records_from_features(
        {species: features[species]["CAL"] for species in SPECIES}, None, device
    )
    dev_base_tiles = _tile_records_from_features(
        {species: features[species]["DEV"] for species in SPECIES}, None, device
    )
    base_cal = calibration_for_tiles(cal_base_tiles)
    historical_path = source_path(config, "historical_calibration", root)
    historical = {"status": "missing", "path": str(historical_path)}
    if historical_path.is_file():
        historical_artifact = json.loads(historical_path.read_text())
        required = ("platt_slope", "platt_intercept", "threshold")
        if not all(key in historical_artifact for key in required):
            raise RuntimeError("historical D calibration is missing required parameters")
        old_slope = float(historical_artifact["platt_slope"])
        old_intercept = float(historical_artifact["platt_intercept"])
        old_threshold = float(historical_artifact["threshold"])
        old_per_species, old_summary = LEGACY.evaluate(
            dev_base_tiles, old_slope, old_intercept, old_threshold
        )
        historical = {
            "status": "loaded_full_calibration_artifact",
            "path": str(historical_path),
            "fit_split": historical_artifact.get("fit_split"),
            "calibration_scope": historical_artifact.get("calibration_scope"),
            "platt_slope": old_slope,
            "platt_intercept": old_intercept,
            "threshold": old_threshold,
            "source_threshold_selection": historical_artifact.get("threshold_selection"),
            "bounded_dev_descriptive": {
                "per_species": old_per_species,
                "summary": old_summary,
            },
        }
    base_dev_per_species, base_dev_summary = LEGACY.evaluate(
        dev_base_tiles,
        base_cal["platt_slope"],
        base_cal["platt_intercept"],
        base_cal["threshold"],
    )
    base_result = {
        "kind": "frozen_base_logits",
        "trainable_parameters": 0,
        "calibration": base_cal,
        "historical_full_calibration": historical,
        "dev": {"per_species": base_dev_per_species, "summary": base_dev_summary},
        "route_statistics": {},
    }
    arms: dict[str, dict] = {"D_recalibrated": base_result}
    train_features = {species: features[species]["TRAIN"] for species in SPECIES}
    cal_features = {species: features[species]["CAL"] for species in SPECIES}
    dev_features = {species: features[species]["DEV"] for species in SPECIES}
    arm_classes = (DenseResidualAdapter, TwoExpertSoftGate, ConstantAverageExperts)
    for arm_class in arm_classes:
        set_seed(seed)
        arm = arm_class(hidden_size)
        train_result = train_one_arm(
            arm,
            train_features,
            cal_features,
            device,
            int(config["training"]["epochs"]),
            seed,
        )
        cal = train_result["calibration"]
        dev_tiles = _tile_records_from_features(dev_features, arm, device)
        dev_per_species, dev_summary = LEGACY.evaluate(
            dev_tiles,
            cal["platt_slope"],
            cal["platt_intercept"],
            cal["threshold"],
        )
        arms[arm.arm_name] = {
            "kind": config["model"]["arms"][arm.arm_name]["kind"],
            "trainable_parameters": parameter_count(arm),
            "selected_epoch": train_result["selected_epoch"],
            "train_steps_per_epoch": train_result["train_steps_per_epoch"],
            "train_epochs": train_result["train_epochs"],
            "calibration": {
                key: value
                for key, value in cal.items()
                if key not in {"per_species", "summary"}
            },
            "cal_selection_metrics": {
                "per_species": cal["per_species"],
                "summary": cal["summary"],
            },
            "dev": {"per_species": dev_per_species, "summary": dev_summary},
            "route_statistics_dev": route_statistics(arm, dev_features, device),
            "training_trace": train_result["trace"],
        }
        del arm
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    result = {
        "experiment": config["experiment"],
        "status": "completed",
        "scientific_status": "exploratory_single_seed42_bounded_feature_head_pilot",
        "config": str(config_path),
        "output_dir": str(output_dir),
        "environment": _environment(),
        "model_dir": str(model_dir),
        "native_model_code": str(native_code_dir),
        "selection": manifest,
        "feature_contract": {
            "hidden_size": hidden_size,
            "kmer_bp": 6,
            "quality_unit": "bp",
            "projection": "legacy project_token_margins with stripped non-special token order",
            "train_species_balance": "one source-order tile per species per step, both halves",
            "calibration": "shared six-species Platt and legacy global threshold",
            "dev_touched_only_after_selected_epoch": True,
        },
        "arms": arms,
        "sea_urchin": config["sea_urchin_exploration"],
    }
    write_json(output_dir / "results.json", result)
    write_json(
        output_dir / "status.json",
        {"status": "completed", "finished_at": time.time(), "results": str(output_dir / "results.json")},
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        config = read_config(args.config)
        if args.smoke:
            result = smoke(config)
            print(json.dumps(result, indent=2, sort_keys=True), flush=True)
            return
        result = run(args.config, args.output_dir)
        print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2), flush=True)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            args.output_dir / "failure.json",
            {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise


if __name__ == "__main__":
    main()
