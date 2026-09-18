#!/usr/bin/env python3
"""Create a compact, auditable summary of the completed LoRA comparison.

The input is the immutable results.json written by the formal Slurm run.  The
script performs no model inference and does not select a checkpoint or
threshold.  It extracts the frozen protocol, calibration values, per-species
DEV metrics, and adapter-versus-D retention from the recorded results.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SPECIES = ("human", "mouse", "pig", "chicken", "zebrafish", "c_elegans")
ADAPTER_ARMS = ("shared_lora_rank16", "clade_lora_two_rank8")
DEV_METRICS = (
    "bp_f1",
    "bp_precision",
    "bp_recall",
    "bp_average_precision",
    "segment_f1_iou_0_8",
    "boundary_f1_25bp",
    "boundary_f1_5bp",
    "missed_rate",
    "short_prediction_rate",
    "split_rate",
    "positive_bp",
    "callable_bp",
    "truth_segments",
    "predicted_segments",
    "bp_tp",
    "bp_fp",
    "bp_fn",
    "hardN_fp_rate",
)


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def metric_row(row: dict) -> dict:
    return {key: row[key] for key in DEV_METRICS if key in row}


def dev_block(arm: dict, *, d_reference: dict | None = None) -> dict:
    dev = arm["dev"]
    per_species = {species: metric_row(dev["per_species"][species]) for species in SPECIES}
    result = {
        "per_species": per_species,
        "summary": dev["summary"],
        "weakest_by_bp_f1": min(SPECIES, key=lambda species: per_species[species]["bp_f1"]),
        "weakest_by_segment_f1_iou_0_8": min(
            SPECIES, key=lambda species: per_species[species]["segment_f1_iou_0_8"]
        ),
    }
    if d_reference is not None:
        d_rows = d_reference["dev"]["per_species"]
        delta = {}
        for species in SPECIES:
            row = per_species[species]
            d_row = d_rows[species]
            delta[species] = {
                "bp_f1_delta_vs_D_CAL_refit": row["bp_f1"] - d_row["bp_f1"],
                "bp_f1_retention_vs_D_CAL_refit": row["bp_f1"] / d_row["bp_f1"],
                "segment_f1_iou_0_8_delta_vs_D_CAL_refit": row["segment_f1_iou_0_8"]
                - d_row["segment_f1_iou_0_8"],
            }
        result["delta_vs_D_CAL_refit"] = delta
        d_macro = d_reference["dev"]["summary"]["macro_bp_f1"]
        result["macro_bp_f1_delta_vs_D_CAL_refit"] = dev["summary"]["macro_bp_f1"] - d_macro
        result["macro_bp_f1_retention_vs_D_CAL_refit"] = dev["summary"]["macro_bp_f1"] / d_macro
    return result


def calibration_block(arm: dict) -> dict:
    calibration = arm["calibration"]
    return {
        key: calibration[key]
        for key in ("threshold", "platt_slope", "platt_intercept", "calibration_loss")
        if key in calibration
    }


def run(input_path: Path, output_path: Path) -> dict:
    raw = json.loads(input_path.read_text())
    if raw.get("status") != "completed":
        raise ValueError(f"input result status is not completed: {raw.get('status')!r}")
    if raw.get("experiment") != "D-BACKBONE-LORA-CLADE-20260918":
        raise ValueError("unexpected experiment name")

    d_arm = raw["arms"]["D_recalibrated"]["cal_refit"]
    d_reference = {"dev": d_arm["dev"]}
    arms = {}
    d_full = raw["arms"]["D_recalibrated"]["historical_full_cal"]
    arms["D_recalibrated"] = {
        "kind": raw["arms"]["D_recalibrated"]["kind"],
        "trainable_parameters": raw["arms"]["D_recalibrated"]["trainable_parameters"],
        "cal_refit": {
            "calibration": calibration_block(d_arm),
            "dev": dev_block(d_arm),
        },
        "historical_full_cal": {
            "path": d_full.get("path"),
            "threshold": d_full.get("threshold"),
            "platt_slope": d_full.get("platt_slope"),
            "platt_intercept": d_full.get("platt_intercept"),
            "dev": {
                "per_species": {
                    species: metric_row(d_full["dev"]["per_species"][species])
                    for species in SPECIES
                },
                "summary": d_full["dev"]["summary"],
            },
        },
    }
    for arm_name in ADAPTER_ARMS:
        arm = raw["arms"][arm_name]
        train = arm["training"]
        arms[arm_name] = {
            "kind": arm["kind"],
            "trainable_parameters": arm["trainable_parameters"],
            "calibration": calibration_block(arm),
            "cal_selection_metrics": arm["cal_selection_metrics"],
            "dev": dev_block(arm, d_reference=d_reference),
            "route": arm["route"],
            "training": {
                key: train[key]
                for key in (
                    "elapsed_seconds",
                    "optimizer_steps",
                    "requested_steps",
                    "seed",
                    "skipped_steps",
                    "total_model_parameters",
                    "trainable_parameters",
                )
            },
        }

    compact = {
        "experiment": raw["experiment"],
        "source_results": str(input_path),
        "status": raw["status"],
        "scientific_status": raw["scientific_status"],
        "selection": {
            "species": raw["data"]["species"],
            "splits": raw["data"]["splits"],
            "selection_rule": raw["data"]["selection"],
            "tiles_per_species": {
                species: {
                    split: raw["selection"][species][split]["tiles"]
                    for split in ("TRAIN", "CAL", "DEV")
                }
                for species in SPECIES
            },
        },
        "model": raw["model"],
        "parameter_accounting": {
            "adapter_augmented_total_parameters": raw["arms"]["shared_lora_rank16"]["training"][
                "total_model_parameters"
            ],
            "frozen_checkpoint_parameters": raw["arms"]["shared_lora_rank16"]["training"][
                "total_model_parameters"
            ]
            - raw["arms"]["shared_lora_rank16"]["training"]["trainable_parameters"],
            "shared_total_trainable_parameters": raw["arms"]["shared_lora_rank16"][
                "trainable_parameters"
            ],
            "clade_total_trainable_parameters": raw["arms"]["clade_lora_two_rank8"][
                "trainable_parameters"
            ],
            "clade_active_parameters_per_route": raw["arms"]["clade_lora_two_rank8"][
                "trainable_parameters"
            ]
            // 2,
        },
        "training_contract": raw["training"],
        "resources": raw["resources"],
        "arms": arms,
        "claim_boundary": raw["claim_boundary"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n")
    return compact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input, args.output)
    print(json.dumps({"status": result["status"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
