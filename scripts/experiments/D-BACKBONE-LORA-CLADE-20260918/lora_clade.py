#!/usr/bin/env python3
"""Finite clade-conditioned LoRA comparison for the frozen D model.

The script deliberately keeps the D tokenization, binary head, calibration,
and base-pair projection contract.  Only query/value projections in the last
two encoder layers receive trainable LoRA parameters.  The routed arm uses a
fixed taxonomy route and has no learned gate.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import importlib.util
import json
import random
import re
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


REPO_ROOT = Path(__file__).resolve().parents[3]
PILOT_PATH = REPO_ROOT / "scripts/experiments/D-ADAPTER-MOE-PILOT-20260914/pilot.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PILOT = load_module("d_lora_pilot_support", PILOT_PATH)
LEGACY = PILOT.LEGACY
TOKEN_TASK = PILOT.TOKEN_TASK

SPECIES = tuple(PILOT.SPECIES)
WINDOW_BP = 4096
TRAIN_TILE_COUNT = 256
KNOWN_ROUTES = {
    "human": 0,
    "mouse": 0,
    "pig": 0,
    "chicken": 0,
    "zebrafish": 0,
    "c_elegans": 1,
}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_config(path: Path) -> dict:
    value = json.loads(path.read_text())
    if value.get("experiment") != "D-BACKBONE-LORA-CLADE-20260918":
        raise ValueError("unexpected LoRA clade config")
    return value


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def source_path(config: dict, key: str, root: Path) -> Path:
    value = Path(config["data"][key])
    return value if value.is_absolute() else root / value


def data_path(config: dict, root: Path, species: str, split: str) -> Path:
    if species == "c_elegans" and split == "TRAIN":
        return source_path(config, "worm_train_override", root)
    return source_path(config, "data_root", root) / split / f"{species}.jsonl.gz"


class LoRALinear(nn.Module):
    """Frozen linear projection plus one or more fixed-route LoRA deltas."""

    def __init__(
        self,
        base: nn.Linear,
        ranks: tuple[int, ...],
        alphas: tuple[float, ...],
        dropout: float = 0.0,
    ):
        super().__init__()
        if len(ranks) == 0 or len(ranks) != len(alphas):
            raise ValueError("LoRA ranks and alphas must be non-empty and aligned")
        if any(rank <= 0 for rank in ranks):
            raise ValueError("LoRA ranks must be positive")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("invalid LoRA dropout")
        self.base = base
        for parameter in self.base.parameters():
            parameter.requires_grad_(False)
        self.ranks = tuple(int(rank) for rank in ranks)
        self.alphas = tuple(float(alpha) for alpha in alphas)
        self.dropout = float(dropout)
        self.active_route = 0
        self.down = nn.ParameterList()
        self.up = nn.ParameterList()
        for rank in self.ranks:
            down = nn.Parameter(torch.empty(rank, base.in_features))
            up = nn.Parameter(torch.zeros(base.out_features, rank))
            nn.init.kaiming_uniform_(down, a=5**0.5)
            self.down.append(down)
            self.up.append(up)

    @property
    def route_count(self) -> int:
        return len(self.ranks)

    @property
    def lora_parameter_count(self) -> int:
        return int(sum(2 * rank * self.base.in_features for rank in self.ranks))

    def set_route(self, route: int) -> None:
        route = int(route)
        if not 0 <= route < self.route_count:
            raise ValueError(f"route {route} outside 0..{self.route_count - 1}")
        self.active_route = route

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        result = self.base(hidden_states)
        route = self.active_route
        delta = F.linear(hidden_states, self.down[route])
        if self.training and self.dropout:
            delta = F.dropout(delta, p=self.dropout)
        delta = F.linear(delta, self.up[route])
        delta = delta * (self.alphas[route] / self.ranks[route])
        return result + delta


def _get_submodule(root: nn.Module, dotted: str) -> nn.Module:
    current = root
    for part in dotted.split("."):
        current = getattr(current, part)
    return current


def install_lora(model: nn.Module, ranks: tuple[int, ...], alphas: tuple[float, ...], dropout: float) -> dict:
    """Replace exactly query/value modules in encoder layers 27 and 28."""

    targets = []
    for name, module in list(model.named_modules()):
        match = re.search(r"\.encoder\.layer\.(\d+)\.attention\.self\.(query|value)$", name)
        if match is None:
            continue
        if int(match.group(1)) not in (27, 28):
            continue
        if not isinstance(module, nn.Linear):
            raise TypeError(f"LoRA target is not Linear: {name} ({type(module)})")
        parent_name, attribute = name.rsplit(".", 1)
        parent = _get_submodule(model, parent_name)
        setattr(parent, attribute, LoRALinear(module, ranks, alphas, dropout))
        targets.append(name)
    expected = {
        f"{prefix}.encoder.layer.{layer}.attention.self.{projection}"
        for prefix in ("esm", "base_model", "")
        for layer in (27, 28)
        for projection in ("query", "value")
    }
    if len(targets) != 4:
        raise RuntimeError(f"expected four last-layer query/value targets, found {targets}")
    return {"targets": targets, "modules": 4}


def set_model_route(model: nn.Module, route: int) -> None:
    modules = [module for module in model.modules() if isinstance(module, LoRALinear)]
    for module in modules:
        module.set_route(route)


def route_for(arm: str, species: str) -> int:
    if arm == "shared_lora_rank16":
        return 0
    if arm == "clade_lora_two_rank8":
        if species not in KNOWN_ROUTES:
            raise ValueError(f"unknown taxonomy is not routed: {species}")
        return KNOWN_ROUTES[species]
    return 0


def _prepare_half(tokenizer, record: dict) -> dict:
    encoded, positions = PILOT._encoding_with_positions(tokenizer, record)
    token_positions = torch.as_tensor(positions, dtype=torch.long)
    positive = encoded["positive_bp"][token_positions].numpy().astype(np.float32)
    negative = encoded["negative_bp"][token_positions].numpy().astype(np.float32)
    truth, callable_mask, hard_negative = LEGACY.decode_labels(record["labels"])
    return {
        "record": {
            "species": record.get("species_code"),
            "split": record.get("split"),
            "tile_id": str(record["tile_id"]),
            "assembly": record["assembly"],
            "chrom": record["chrom"],
            "start": int(record["start"]),
            "end": int(record["end"]),
            "half": int(record["half"]),
        },
        "input_ids": encoded["input_ids"].detach().cpu(),
        "attention_mask": encoded["attention_mask"].detach().cpu(),
        "positions": positions,
        "positive_bp": positive,
        "negative_bp": negative,
        "truth": truth.astype(bool),
        "callable": callable_mask.astype(bool),
        "hard_negative": hard_negative.astype(bool),
    }


def load_selected(config: dict, tokenizer, root: Path) -> tuple[dict, dict]:
    selected: dict[str, dict[str, list[dict]]] = {}
    manifest: dict[str, dict[str, dict]] = {}
    for species in config["data"]["species"]:
        selected[species] = {}
        manifest[species] = {}
        for split, count in config["data"]["splits"].items():
            records, selection = PILOT.read_first_complete_tiles(
                data_path(config, root, species, split),
                species,
                split,
                int(count),
            )
            tiles = []
            for left, right in PILOT._group_records(records):
                tiles.append(
                    {
                        "species": species,
                        "split": split,
                        "tile_id": str(left["tile_id"]),
                        "assembly": left["assembly"],
                        "chrom": left["chrom"],
                        "start": int(left["start"]),
                        "end": int(right["end"]),
                        "halves": {
                            0: _prepare_half(tokenizer, left),
                            1: _prepare_half(tokenizer, right),
                        },
                    }
                )
            selected[species][split] = tiles
            manifest[species][split] = selection
    return selected, manifest


def _move_half(half: dict, device: torch.device) -> tuple[torch.Tensor, ...]:
    return (
        half["input_ids"].unsqueeze(0).to(device),
        half["attention_mask"].unsqueeze(0).to(device),
        torch.as_tensor(half["positions"], dtype=torch.long, device=device),
        torch.as_tensor(half["positive_bp"], dtype=torch.float32, device=device),
        torch.as_tensor(half["negative_bp"], dtype=torch.float32, device=device),
    )


def predict_split(
    model: nn.Module,
    selected: dict[str, dict[str, list[dict]]],
    split: str,
    device: torch.device,
    arm: str,
) -> dict[str, list[dict]]:
    """Run one fixed split and project logits to exactly 4096 bp per half."""

    model.eval()
    result: dict[str, list[dict]] = {}
    with torch.no_grad():
        for species in SPECIES:
            result[species] = []
            set_model_route(model, route_for(arm, species))
            for tile in selected[species][split]:
                margins = []
                truths = []
                callable_parts = []
                hard_parts = []
                for half_index in (0, 1):
                    half = tile["halves"][half_index]
                    input_ids = half["input_ids"].unsqueeze(0).to(device)
                    attention_mask = half["attention_mask"].unsqueeze(0).to(device)
                    positions = torch.as_tensor(half["positions"], dtype=torch.long, device=device)
                    output = model(input_ids=input_ids, attention_mask=attention_mask)
                    token_logits = output.logits[0, positions].detach().float().cpu().numpy()
                    token_margin = token_logits[:, 1] - token_logits[:, 0]
                    margins.append(
                        LEGACY.project_token_margins(
                            token_margin,
                            list(range(len(token_margin))),
                            WINDOW_BP,
                        )
                    )
                    truths.append(half["truth"])
                    callable_parts.append(half["callable"])
                    hard_parts.append(half["hard_negative"])
                result[species].append(
                    {
                        "species": species,
                        "assembly": tile["assembly"],
                        "split": split,
                        "tile_id": tile["tile_id"],
                        "chrom": tile["chrom"],
                        "start": tile["start"],
                        "end": tile["end"],
                        "margin": np.concatenate(margins),
                        "truth": np.concatenate(truths),
                        "callable": np.concatenate(callable_parts),
                        "hard_negative": np.concatenate(hard_parts),
                    }
                )
    return result


def weighted_loss_from_half(model, half: dict, device: torch.device) -> torch.Tensor | None:
    input_ids, attention_mask, positions, positive, negative = _move_half(half, device)
    output = model(input_ids=input_ids, attention_mask=attention_mask)
    logits = output.logits[0, positions]
    return PILOT._weighted_token_loss(logits, positive, negative)


def train_arm(
    model: nn.Module,
    selected: dict[str, dict[str, list[dict]]],
    device: torch.device,
    arm: str,
    steps: int,
    seed: int,
    learning_rate: float,
    weight_decay: float,
    clip_norm: float,
) -> dict:
    model.eval()  # keep the frozen D path deterministic; LoRA parameters still receive gradients
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable:
        raise RuntimeError(f"{arm} has no trainable parameters")
    optimizer = torch.optim.AdamW(trainable, lr=learning_rate, weight_decay=weight_decay)
    optimizer_steps = 0
    skipped = 0
    loss_trace = []
    started = time.time()
    for step in range(int(steps)):
        optimizer.zero_grad(set_to_none=True)
        tile_index = step % TRAIN_TILE_COUNT
        valid_terms = 0
        loss_sum = 0.0
        for species in SPECIES:
            set_model_route(model, route_for(arm, species))
            tile = selected[species]["TRAIN"][tile_index]
            for half_index in (0, 1):
                loss = weighted_loss_from_half(model, tile["halves"][half_index], device)
                if loss is None:
                    continue
                valid_terms += 1
                loss_sum += float(loss.detach().cpu())
                # Every nominal step has six species and two halves; fixed normalization
                # preserves the original species-balanced training scale.
                (loss / float(len(SPECIES) * 2)).backward()
        if valid_terms == 0:
            skipped += 1
            continue
        torch.nn.utils.clip_grad_norm_(trainable, clip_norm)
        optimizer.step()
        optimizer_steps += 1
        if step == 0 or (step + 1) % 64 == 0 or step + 1 == steps:
            loss_trace.append(
                {
                    "step": step + 1,
                    "valid_half_terms": valid_terms,
                    "mean_half_loss": loss_sum / valid_terms,
                }
            )
            print(
                f"[train] {arm} step={step + 1}/{steps} "
                f"valid={valid_terms} mean_loss={loss_sum / valid_terms:.6f}",
                flush=True,
            )
    if optimizer_steps == 0:
        raise RuntimeError(f"{arm} had no optimizer updates")
    elapsed = time.time() - started
    return {
        "requested_steps": int(steps),
        "optimizer_steps": int(optimizer_steps),
        "skipped_steps": int(skipped),
        "loss_trace": loss_trace,
        "elapsed_seconds": elapsed,
        "seed": int(seed),
        "trainable_parameters": int(sum(parameter.numel() for parameter in trainable)),
        "total_model_parameters": int(sum(parameter.numel() for parameter in model.parameters())),
    }


def arm_result(
    model: nn.Module,
    selected: dict[str, dict[str, list[dict]]],
    device: torch.device,
    arm: str,
    config: dict,
) -> dict:
    cal_tiles = predict_split(model, selected, "CAL", device, arm)
    dev_tiles = predict_split(model, selected, "DEV", device, arm)
    cal = PILOT.calibration_for_tiles(cal_tiles)
    dev_per_species, dev_summary = LEGACY.evaluate(
        dev_tiles,
        cal["platt_slope"],
        cal["platt_intercept"],
        cal["threshold"],
    )
    return {
        "kind": config["model"]["arms"][arm]["kind"],
        "trainable_parameters": int(
            sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
        ),
        "calibration": {
            key: value for key, value in cal.items() if key not in {"per_species", "summary"}
        },
        "cal_selection_metrics": {
            "per_species": cal["per_species"],
            "summary": cal["summary"],
        },
        "dev": {"per_species": dev_per_species, "summary": dev_summary},
        "route": {
            "human": "vertebrate expert0" if arm.startswith("clade") else "shared",
            "mouse": "vertebrate expert0" if arm.startswith("clade") else "shared",
            "pig": "vertebrate expert0" if arm.startswith("clade") else "shared",
            "chicken": "vertebrate expert0" if arm.startswith("clade") else "shared",
            "zebrafish": "vertebrate expert0" if arm.startswith("clade") else "shared",
            "c_elegans": "worm-only expert1" if arm.startswith("clade") else "shared",
            "unknown_taxonomy": "frozen D logits",
        },
    }


def historical_and_d_reference(
    model: nn.Module,
    selected: dict[str, dict[str, list[dict]]],
    device: torch.device,
    config: dict,
    root: Path,
) -> dict:
    cal_tiles = predict_split(model, selected, "CAL", device, "D")
    dev_tiles = predict_split(model, selected, "DEV", device, "D")
    cal = PILOT.calibration_for_tiles(cal_tiles)
    per_species, summary = LEGACY.evaluate(
        dev_tiles,
        cal["platt_slope"],
        cal["platt_intercept"],
        cal["threshold"],
    )
    reference = {
        "kind": "frozen_D_logits",
        "trainable_parameters": 0,
        "cal_refit": {"calibration": {key: value for key, value in cal.items() if key not in {"per_species", "summary"}}, "dev": {"per_species": per_species, "summary": summary}},
    }
    # This is the saved full-CAL artifact from the same D run.  It is used
    # only as a descriptive reference and never for LoRA selection.
    historical_path = root / "outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1/calibration.json"
    if historical_path.is_file():
        artifact = json.loads(historical_path.read_text())
        old_slope = float(artifact["platt_slope"])
        old_intercept = float(artifact["platt_intercept"])
        old_threshold = float(artifact["threshold"])
        old_per_species, old_summary = LEGACY.evaluate(
            dev_tiles, old_slope, old_intercept, old_threshold
        )
        reference["historical_full_cal"] = {
            "path": str(historical_path),
            "platt_slope": old_slope,
            "platt_intercept": old_intercept,
            "threshold": old_threshold,
            "dev": {"per_species": old_per_species, "summary": old_summary},
        }
    else:
        reference["historical_full_cal"] = {"status": "missing", "path": str(historical_path)}
    return reference


def lora_state(model: nn.Module) -> dict[str, torch.Tensor]:
    return {
        name: parameter.detach().cpu()
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    }


def load_base_model(config: dict, root: Path):
    model_dir = root / config["model"]["checkpoint"]
    native_code = root / config["model"]["native_model_code"]
    model, tokenizer, device = LEGACY.load_final_model(
        model_dir,
        model_dir,
        cpu=False,
        model_code_dir=native_code,
    )
    if device.type != "cuda":
        raise RuntimeError("LoRA formal run requires CUDA")
    hidden_size = int(getattr(model.config, "hidden_size", 0))
    if hidden_size != int(config["model"]["hidden_size"]):
        raise RuntimeError(f"hidden size {hidden_size} differs from config")
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model, tokenizer, device


def smoke(config: dict) -> dict:
    set_seed(int(config["seed"]))
    hidden_size = int(config["model"]["hidden_size"])
    base = nn.Linear(hidden_size, hidden_size)
    x = torch.randn(3, hidden_size)
    expected = 2 * hidden_size * 16
    shared = LoRALinear(base, (16,), (16,), 0.0)
    if shared.lora_parameter_count != expected:
        raise AssertionError(f"shared count {shared.lora_parameter_count} != {expected}")
    y0 = shared(x)
    if not torch.allclose(y0, base(x)):
        raise AssertionError("zero-initialized LoRA changed the D projection")
    routed = LoRALinear(nn.Linear(hidden_size, hidden_size), (8, 8), (8, 8), 0.0)
    if routed.lora_parameter_count != expected:
        raise AssertionError(f"routed count {routed.lora_parameter_count} != {expected}")
    routed.set_route(1)
    routed.down[1].data.fill_(1.0)
    routed.up[1].data.fill_(1.0)
    route1 = routed(x)
    routed.set_route(0)
    route0 = routed(x)
    if torch.allclose(route1, route0):
        raise AssertionError("fixed route did not select a distinct expert")
    if route_for("clade_lora_two_rank8", "c_elegans") != 1:
        raise AssertionError("worm route mismatch")
    if route_for("clade_lora_two_rank8", "zebrafish") != 0:
        raise AssertionError("vertebrate route mismatch")
    return {
        "status": "smoke_pass",
        "per_projection_shared_parameters": shared.lora_parameter_count,
        "per_projection_clade_parameters": routed.lora_parameter_count,
        "full_four_target_shared_parameters": 4 * shared.lora_parameter_count,
        "full_four_target_clade_parameters": 4 * routed.lora_parameter_count,
        "route": {species: route_for("clade_lora_two_rank8", species) for species in SPECIES},
        "unknown_taxonomy_fallback": "frozen_D_logits",
    }


def run(config_path: Path, output_dir: Path) -> dict:
    config = read_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "status.json", {"status": "starting", "started_at": time.time()})
    seed = int(config["seed"])
    set_seed(seed)
    root = Path(config["data"]["project_root"])
    print("[stage] loading frozen D checkpoint", flush=True)
    model, tokenizer, device = load_base_model(config, root)
    print(f"[stage] checkpoint loaded on {device}; preparing fixed tiles", flush=True)
    selected, manifest = load_selected(config, tokenizer, root)
    write_json(output_dir / "input_manifest.json", manifest)
    print("[stage] fixed TRAIN/CAL/DEV tiles materialized", flush=True)
    base_reference = historical_and_d_reference(model, selected, device, config, root)
    print("[stage] D historical and CAL-refit references evaluated", flush=True)
    del model
    torch.cuda.empty_cache()

    arms = {"D_recalibrated": base_reference}
    train_reports = {}
    for arm_name, ranks, alphas in (
        ("shared_lora_rank16", (16,), (16.0,)),
        ("clade_lora_two_rank8", (8, 8), (8.0, 8.0)),
    ):
        set_seed(seed)
        print(f"[arm] starting {arm_name}", flush=True)
        model, _, device = load_base_model(config, root)
        install = install_lora(model, ranks, alphas, float(config["model"]["arms"][arm_name]["dropout"]))
        # The checkpoint loader places the frozen D model on CUDA, while new
        # LoRA Parameters are constructed on CPU.  Move the complete wrapped
        # model before the first routed forward so base and adapter weights
        # share one device.
        model.to(device)
        if len([m for m in model.modules() if isinstance(m, LoRALinear)]) != 4:
            raise RuntimeError("unexpected installed LoRA module count")
        train = train_arm(
            model,
            selected,
            device,
            arm_name,
            int(config["training"]["steps_per_arm"]),
            seed,
            float(config["training"]["learning_rate"]),
            float(config["training"]["weight_decay"]),
            float(config["training"]["gradient_clip_norm"]),
        )
        train_reports[arm_name] = {"installation": install, "training": train}
        arms[arm_name] = {**arm_result(model, selected, device, arm_name, config), "training": train}
        print(f"[arm] completed {arm_name}", flush=True)
        torch.save(lora_state(model), output_dir / f"{arm_name}.pt")
        del model
        torch.cuda.empty_cache()

    result = {
        "experiment": config["experiment"],
        "status": "completed",
        "scientific_status": "finite_seed42_clade_conditioned_last_two_layer_lora",
        "config": str(config_path),
        "output_dir": str(output_dir),
        "model": config["model"],
        "data": config["data"],
        "training": config["training"],
        "resources": config["resources"],
        "selection": manifest,
        "arms": arms,
        "train_reports": train_reports,
        "claim_boundary": config["scientific_boundary"],
    }
    write_json(output_dir / "results.json", result)
    write_json(output_dir / "status.json", {"status": "completed", "finished_at": time.time(), "results": str(output_dir / "results.json")})
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
            print(json.dumps(smoke(config), indent=2, sort_keys=True), flush=True)
            return
        result = run(args.config, args.output_dir)
        print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2), flush=True)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(args.output_dir / "failure.json", {"status": "failed", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    main()
