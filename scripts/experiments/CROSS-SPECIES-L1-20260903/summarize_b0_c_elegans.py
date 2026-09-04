#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


SEEDS = (17, 42, 20260903)
SPECIES = "c_elegans"
METRICS = (
    "bp_precision",
    "bp_recall",
    "bp_f1",
    "bp_average_precision",
    "segment_f1_iou_0_8",
    "boundary_f1_5bp",
    "boundary_f1_25bp",
    "short_prediction_rate",
    "fragments_per_truth",
    "split_rate",
    "missed_rate",
    "hardN_fp_rate",
)


def load_metrics(path: Path, seed: int) -> dict:
    payload = json.loads(path.read_text())
    if payload["mode"] != "apply-only" or payload["observed_splits"] != ["DEV"]:
        raise ValueError(f"seed {seed} input is not a DEV apply-only result")
    if payload["seed"] != seed:
        raise ValueError(f"seed {seed} input has the wrong seed")
    if set(payload["per_species"]) != {SPECIES}:
        raise ValueError(f"seed {seed} input must contain only {SPECIES}")
    values = [float(payload["per_species"][SPECIES][metric]) for metric in METRICS]
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"seed {seed} input contains non-finite metrics")
    return payload["per_species"][SPECIES]


def check(name: str, value: float, threshold: float, rule: str) -> dict:
    passed = value >= threshold if rule == ">=" else value <= threshold
    return {
        "name": name,
        "pass": passed,
        "evidence": {"value": value, "threshold": threshold, "rule": rule},
    }


def summarize(shared_paths: dict[int, Path], specialist_paths: dict[int, Path]) -> dict:
    shared = {seed: load_metrics(shared_paths[seed], seed) for seed in SEEDS}
    specialist = {seed: load_metrics(specialist_paths[seed], seed) for seed in SEEDS}
    by_seed = {}
    checks = []
    for seed in SEEDS:
        base = shared[seed]
        candidate = specialist[seed]
        seed_checks = [
            check(f"seed{seed}_specialist_bp_f1", candidate["bp_f1"], 0.85, ">="),
            check(
                f"seed{seed}_bp_f1_gain",
                candidate["bp_f1"] - base["bp_f1"],
                0.05,
                ">=",
            ),
            check(
                f"seed{seed}_bp_average_precision_gain",
                candidate["bp_average_precision"] - base["bp_average_precision"],
                0.03,
                ">=",
            ),
            check(
                f"seed{seed}_segment_f1_regression",
                candidate["segment_f1_iou_0_8"] - base["segment_f1_iou_0_8"],
                -0.05,
                ">=",
            ),
            check(
                f"seed{seed}_boundary_f1_5bp_regression",
                candidate["boundary_f1_5bp"] - base["boundary_f1_5bp"],
                -0.05,
                ">=",
            ),
            check(
                f"seed{seed}_fragments_per_truth",
                candidate["fragments_per_truth"],
                1.25 * base["fragments_per_truth"],
                "<=",
            ),
            check(
                f"seed{seed}_split_rate",
                candidate["split_rate"],
                1.25 * base["split_rate"],
                "<=",
            ),
            check(
                f"seed{seed}_missed_rate",
                candidate["missed_rate"] - base["missed_rate"],
                0.03,
                "<=",
            ),
        ]
        checks.extend(seed_checks)
        by_seed[str(seed)] = {
            "shared": base,
            "specialist": candidate,
            "delta": {
                metric: float(candidate[metric]) - float(base[metric])
                for metric in METRICS
            },
            "all_checks_pass": all(item["pass"] for item in seed_checks),
        }

    all_pass = all(item["pass"] for item in checks)
    return {
        "schema_version": "CROSS-SPECIES-L1-B0-C-ELEGANS-GATE-1.0.0",
        "species": SPECIES,
        "seeds": list(SEEDS),
        "shared_inputs": {str(seed): str(shared_paths[seed]) for seed in SEEDS},
        "specialist_inputs": {
            str(seed): str(specialist_paths[seed]) for seed in SEEDS
        },
        "by_seed": by_seed,
        "gate": {"all_pass": all_pass, "checks": checks},
        "decision": (
            "B0_RECOVERABLE_SPECIALIST_GAP"
            if all_pass
            else "B0_RECOVERY_GATE_FAIL"
        ),
        "conditional_model_admission": False,
        "conditional_model_admission_reason": (
            "one C. elegans specialist cannot identify a transferable clade adapter or MoE"
        ),
        "external_remains_sealed": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    for seed in SEEDS:
        parser.add_argument(f"--shared-seed{seed}", type=Path, required=True)
        parser.add_argument(f"--specialist-seed{seed}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    shared_paths = {seed: getattr(args, f"shared_seed{seed}") for seed in SEEDS}
    specialist_paths = {
        seed: getattr(args, f"specialist_seed{seed}") for seed in SEEDS
    }
    result = summarize(shared_paths, specialist_paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
