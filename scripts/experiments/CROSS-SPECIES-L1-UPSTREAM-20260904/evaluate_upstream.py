#!/usr/bin/env python3
"""Evaluate one L/D arm with frozen six-species CAL and new worm SCREEN."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_ID = "CROSS-SPECIES-L1-UPSTREAM-20260904"
PROTOCOL = f"{EXPERIMENT_ID}-V1"
RUN_ROLE = "upstream_coverage_pilot"
ARM_CHOICES = ("L", "D")
SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
WORM = "c_elegans"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903"))
import calibrate_evaluate_x0 as legacy


def split_data_specs(data_root: Path, upstream_root: Path) -> dict[str, list[tuple[str, Path]]]:
    """Map CAL/DEV to the old root and SCREEN to new worm coordinates; omit CONF."""

    old, new = Path(data_root), Path(upstream_root)
    return {
        "CAL": [(species, old / "CAL" / f"{species}.jsonl.gz") for species in SPECIES],
        "DEV": [(species, old / "DEV" / f"{species}.jsonl.gz") for species in SPECIES],
        "SCREEN": [(WORM, new / "SCREEN" / f"{WORM}.jsonl.gz")],
    }


def _check_split(
    panel: dict[str, list[dict]], expected: str, expected_species: set[str]
) -> None:
    observed = {tile["split"] for tiles in panel.values() for tile in tiles}
    if observed != {expected}:
        raise ValueError(f"expected {expected} records, observed {sorted(observed)}")
    if set(panel) != expected_species:
        raise ValueError(
            f"{expected} species mismatch: {sorted(panel)} != {sorted(expected_species)}"
        )


def _metric_artifact(split: str, panel: dict, calibration: dict, args, model_dir: Path, calibration_path: Path) -> dict:
    per_species, summary = legacy.evaluate(
        panel,
        calibration["platt_slope"],
        calibration["platt_intercept"],
        calibration["threshold"],
    )
    return {
        "experiment": EXPERIMENT_ID,
        "protocol": PROTOCOL,
        "run_role": RUN_ROLE,
        "arm": args.arm,
        "seed": args.seed,
        "model_dir": str(model_dir.resolve()),
        "calibration_json": str(calibration_path.resolve()),
        "calibration_scope": "six-species-shared",
        "split": split,
        "species": sorted(per_species),
        "conf_evaluated": False,
        "per_species": per_species,
        "summary": summary,
    }


def evaluate_arm(args) -> dict:
    """Load once, infer each of CAL/DEV/SCREEN once, then write three artifacts."""

    if args.arm not in ARM_CHOICES:
        raise ValueError(f"unsupported upstream arm: {args.arm}")
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    model_dir = Path(args.model_dir)
    specs = split_data_specs(args.data_root, args.upstream_root)
    model, tokenizer, device = legacy.load_final_model(
        model_dir, args.tokenizer_dir, args.cpu, args.model_code_dir
    )
    try:
        panels = {}
        for split in ("CAL", "DEV", "SCREEN"):
            panels[split] = legacy.infer_inputs(
                model, tokenizer, device, specs[split], args.batch_size
            )
            _check_split(
                panels[split], split, {WORM} if split == "SCREEN" else set(SPECIES)
            )

        cal = panels["CAL"]
        legacy.require_cal_split(cal)
        raw = legacy.callable_arrays(cal)
        slope, intercept, loss = legacy.fit_platt(raw)
        selected = legacy.select_global_threshold({
            species: (legacy.sigmoid(slope * margins + intercept), truth)
            for species, (margins, truth) in raw.items()
        })
        calibration = {
            "experiment": EXPERIMENT_ID,
            "protocol": PROTOCOL,
            "run_role": RUN_ROLE,
            "arm": args.arm,
            "seed": args.seed,
            "calibration_protocol": "CROSS-SPECIES-L1-X0-PLATT-V1",
            "calibration_scope": "six-species-shared",
            "fit_split": "CAL",
            "species": list(SPECIES),
            "model_dir": str(model_dir.resolve()),
            "tokenizer_dir": str(Path(args.tokenizer_dir or model_dir).resolve()),
            "model_code_dir": str(Path(args.model_code_dir).resolve()) if args.model_code_dir else None,
            "platt_slope": slope,
            "platt_intercept": intercept,
            "calibration_loss": loss,
            "threshold": selected["threshold"],
            "threshold_selection": selected,
            "evaluation_contract": {
                "dev_split": "DEV",
                "screen_split": "SCREEN",
                "screen_species": [WORM],
                "forbidden_split": "CONF",
                "conf_status": "sealed_not_evaluated",
            },
        }
        calibration_path = output / "calibration.json"
        legacy.write_json(calibration_path, calibration)
        for split in ("SCREEN", "DEV"):
            legacy.write_json(
                output / f"{split.lower()}_metrics.json",
                _metric_artifact(split, panels[split], calibration, args, model_dir, calibration_path),
            )
    finally:
        del model, tokenizer
    return {
        "experiment": EXPERIMENT_ID,
        "protocol": PROTOCOL,
        "run_role": RUN_ROLE,
        "arm": args.arm,
        "seed": args.seed,
        "output_dir": str(output.resolve()),
        "calibration_json": str((output / "calibration.json").resolve()),
        "screen_metrics_json": str((output / "screen_metrics.json").resolve()),
        "dev_metrics_json": str((output / "dev_metrics.json").resolve()),
        "evaluated_splits": ["CAL", "DEV", "SCREEN"],
        "forbidden_splits": ["CONF"],
    }


evaluate = evaluate_arm


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARM_CHOICES, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path)
    parser.add_argument("--model-code-dir", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--cpu", action="store_true")
    return parser


def main() -> None:
    print(json.dumps(evaluate_arm(build_parser().parse_args()), indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
