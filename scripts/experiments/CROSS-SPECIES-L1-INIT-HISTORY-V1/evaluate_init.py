#!/usr/bin/env python3
"""Fit old CAL once and evaluate the registered initialization arm on DEV/SCREEN."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-UPSTREAM-20260904"))
import evaluate_upstream as upstream

legacy = upstream.legacy
EXPERIMENT_ID = "CROSS-SPECIES-L1-INIT-HISTORY-V1"
PROTOCOL = EXPERIMENT_ID
RUN_ROLE = "initialization_history_comparison"
ARM_CHOICES = ("H0R", "P0R")
SPECIES = upstream.SPECIES
WORM = upstream.WORM
CONF_STATUS = "historical_closure_only_new_inference_forbidden"
split_data_specs = upstream.split_data_specs


def cache_tiles(path: Path, tiles: list[dict]) -> None:
    """Retain raw float32 scores and exact coordinates/labels for paired spatial CI."""
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {
        key: np.stack([tile[key] for tile in tiles])
        for key in ("truth", "callable", "hard_negative")
    }
    arrays["margin"] = np.stack([tile["margin"] for tile in tiles]).astype(np.float32)
    for key in ("tile_id", "chrom", "start", "end", "assembly", "species", "split"):
        arrays[key] = np.asarray([tile[key] for tile in tiles])
    np.savez_compressed(path, **arrays)


def evaluate_arm(args) -> dict:
    if args.arm not in ARM_CHOICES or args.seed not in (42, 17):
        raise ValueError("registered arms are H0R/P0R with seed42/17")
    output, model_dir = Path(args.output_dir), Path(args.model_dir)
    # A new output location makes an accidental second evaluation visible.
    output.mkdir(parents=True, exist_ok=False)
    specs = split_data_specs(args.data_root, args.upstream_root)
    metadata = {
        "experiment": EXPERIMENT_ID, "protocol": PROTOCOL, "run_role": RUN_ROLE,
        "arm": args.arm, "seed": args.seed, "model_dir": str(model_dir.resolve()),
        "calibration_scope": "six-species-shared", "conf_evaluated": False,
        "conf_status": CONF_STATUS,
    }
    cache_paths = {
        split: {species: str((output / "margins" / split / f"{species}.npz").resolve())
                for species, _ in specs[split]}
        for split in ("DEV", "SCREEN")
    }
    model, tokenizer, device = legacy.load_final_model(
        model_dir, args.tokenizer_dir, args.cpu, args.model_code_dir
    )
    try:
        cal = legacy.infer_inputs(model, tokenizer, device, specs["CAL"], args.batch_size)
        upstream._check_split(cal, "CAL", set(SPECIES))
        legacy.require_cal_split(cal)
        raw = legacy.callable_arrays(cal)
        slope, intercept, loss = legacy.fit_platt(raw)
        selected = legacy.select_global_threshold({
            species: (legacy.sigmoid(slope * margins + intercept), truth)
            for species, (margins, truth) in raw.items()
        })
        calibration = {
            **metadata, "calibration_protocol": "CROSS-SPECIES-L1-X0-PLATT-V1",
            "fit_split": "CAL", "species": list(SPECIES),
            "tokenizer_dir": str(Path(args.tokenizer_dir or model_dir).resolve()),
            "model_code_dir": str(Path(args.model_code_dir).resolve()) if args.model_code_dir else None,
            "platt_slope": slope, "platt_intercept": intercept, "calibration_loss": loss,
            "threshold": selected["threshold"], "threshold_selection": selected,
            "margin_caches": cache_paths,
            "evaluation_contract": {
                "dev_split": "DEV", "screen_split": "SCREEN", "screen_species": [WORM],
                "forbidden_split": "CONF", "conf_status": CONF_STATUS,
                "development_panels": "previously_used_not_independent_holdouts",
            },
        }
        calibration_path = output / "calibration.json"
        legacy.write_json(calibration_path, calibration)
        del cal, raw
        for split in ("SCREEN", "DEV"):
            panel = legacy.infer_inputs(model, tokenizer, device, specs[split], args.batch_size)
            upstream._check_split(panel, split, {WORM} if split == "SCREEN" else set(SPECIES))
            for species, tiles in panel.items():
                cache_tiles(Path(cache_paths[split][species]), tiles)
            per_species, summary = legacy.evaluate(panel, slope, intercept, selected["threshold"])
            legacy.write_json(output / f"{split.lower()}_metrics.json", {
                **metadata, "split": split, "species": sorted(per_species),
                "calibration_json": str(calibration_path.resolve()),
                "margin_caches": cache_paths[split], "per_species": per_species, "summary": summary,
            })
            del panel
    finally:
        del model, tokenizer
    return {
        **metadata, "output_dir": str(output.resolve()),
        "calibration_json": str((output / "calibration.json").resolve()),
        "screen_metrics_json": str((output / "screen_metrics.json").resolve()),
        "dev_metrics_json": str((output / "dev_metrics.json").resolve()),
        "margin_caches": cache_paths, "evaluated_splits": ["CAL", "SCREEN", "DEV"],
        "forbidden_splits": ["CONF"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARM_CHOICES, required=True)
    for name in ("model-dir", "data-root", "upstream-root", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path)
    parser.add_argument("--model-code-dir", type=Path)
    parser.add_argument("--seed", type=int, choices=(42, 17), required=True)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--cpu", action="store_true")
    return parser


if __name__ == "__main__":
    print(json.dumps(evaluate_arm(build_parser().parse_args()), indent=2, sort_keys=True), flush=True)
