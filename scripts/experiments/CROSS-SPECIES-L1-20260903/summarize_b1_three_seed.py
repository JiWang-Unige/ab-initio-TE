#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
SEEDS = (17, 42, 20260903)

PER_SPECIES_METRICS = (
    "bp_precision",
    "bp_recall",
    "bp_f1",
    "segment_f1_iou_0_8",
    "boundary_f1_5bp",
    "boundary_f1_25bp",
    "short_prediction_rate",
    "fragments_per_truth",
    "split_rate",
    "missed_rate",
    "hardN_fp_rate",
)

SUMMARY_METRICS = (
    "macro_bp_precision",
    "macro_bp_recall",
    "macro_bp_f1",
    "macro_segment_f1_iou_0_8",
    "macro_boundary_f1_5bp",
    "macro_boundary_f1_25bp",
    "macro_short_prediction_rate",
    "macro_fragments_per_truth",
    "macro_split_rate",
    "macro_missed_rate",
    "macro_hardN_fp_rate",
    "minimum_species_bp_f1",
)

TOPOLOGY_METRICS = (
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
    if set(payload["per_species"]) != set(SPECIES):
        raise ValueError(f"seed {seed} input must contain the frozen six species")
    values = [
        float(payload["per_species"][species][metric])
        for species in SPECIES
        for metric in PER_SPECIES_METRICS
    ] + [float(payload["summary"][metric]) for metric in SUMMARY_METRICS]
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"seed {seed} input contains non-finite metrics")
    return payload


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def summarize(paths: dict[int, Path]) -> dict:
    arms = {seed: load_metrics(paths[seed], seed) for seed in SEEDS}
    species_mean = {
        species: {
            metric: mean(
                [float(arms[seed]["per_species"][species][metric]) for seed in SEEDS]
            )
            for metric in PER_SPECIES_METRICS
        }
        for species in SPECIES
    }
    summary_mean = {
        metric: mean([float(arms[seed]["summary"][metric]) for seed in SEEDS])
        for metric in SUMMARY_METRICS
    }
    macro_species_bp_f1_by_seed = {
        str(seed): mean(
            [float(arms[seed]["per_species"][species]["bp_f1"]) for species in SPECIES]
        )
        for seed in SEEDS
    }
    macro_species_bp_f1_mean = mean(list(macro_species_bp_f1_by_seed.values()))

    checks = []
    failed_species = []
    for species in SPECIES:
        row = species_mean[species]
        species_checks = (
            ("bp_f1_mean", row["bp_f1"], 0.80),
            ("bp_precision_mean", row["bp_precision"], 0.75),
            ("bp_recall_mean", row["bp_recall"], 0.75),
        )
        species_failed = False
        for metric, value, threshold in species_checks:
            passed = value >= threshold
            checks.append(
                {
                    "name": f"{species}_{metric}",
                    "pass": passed,
                    "evidence": {
                        "species": species,
                        "value": value,
                        "threshold": threshold,
                        "rule": ">= threshold",
                    },
                }
            )
            species_failed = species_failed or not passed
        if species_failed:
            failed_species.append(species)

    checks.append(
        {
            "name": "three_seed_macro_species_bp_f1_mean",
            "pass": macro_species_bp_f1_mean >= 0.83,
            "evidence": {
                "value": macro_species_bp_f1_mean,
                "by_seed": macro_species_bp_f1_by_seed,
                "threshold": 0.83,
                "rule": ">= threshold",
            },
        }
    )
    all_pass = all(item["pass"] for item in checks)
    if all_pass:
        decision = "OPEN_E1_PREPARATION"
    elif failed_species:
        decision = "RUN_B0_FOR_FAILED_SPECIES"
    else:
        decision = "INTERNAL_GATE_FAIL_NO_B0_TARGET"
    return {
        "schema_version": "CROSS-SPECIES-L1-B1-THREE-SEED-GATE-1.0.0",
        "status": "B1_reference_arm",
        "arm": "B1",
        "seeds": list(SEEDS),
        "species": list(SPECIES),
        "inputs": {str(seed): str(paths[seed]) for seed in SEEDS},
        "initialization": {
            "all_seeds_from_same_h0_seed42_initialization": True,
            "claim_scope": "continuation robustness only",
        },
        "per_species_mean": species_mean,
        "summary_mean": summary_mean,
        "three_seed_macro_species_bp_f1_mean": macro_species_bp_f1_mean,
        "topology_summary": {
            "per_species_mean": {
                species: {
                    metric: species_mean[species][metric]
                    for metric in TOPOLOGY_METRICS
                }
                for species in SPECIES
            },
            "summary_mean": {
                metric: summary_mean[f"macro_{metric}"]
                for metric in TOPOLOGY_METRICS
            },
            "gate_applied": False,
            "reason": "B1 is the reference arm; no relative candidate exists",
        },
        "gate": {
            "all_pass": all_pass,
            "checks": checks,
            "failed_species": failed_species,
        },
        "failed_species": failed_species,
        "decision": decision,
        "external_remains_sealed_until_explicit_release": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed17", type=Path, required=True)
    parser.add_argument("--seed42", type=Path, required=True)
    parser.add_argument("--seed20260903", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = summarize(
        {
            17: args.seed17,
            42: args.seed42,
            20260903: args.seed20260903,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
