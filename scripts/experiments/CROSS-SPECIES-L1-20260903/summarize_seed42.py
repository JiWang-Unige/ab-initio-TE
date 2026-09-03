#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")

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


def load_metrics(path: Path) -> dict:
    return json.loads(path.read_text())


def metric_delta(left: dict, right: dict, metrics: tuple[str, ...]) -> dict:
    return {
        metric: float(right[metric]) - float(left[metric])
        for metric in metrics
    }


def attribution_delta(left: dict, right: dict, species: list[str]) -> dict:
    return {
        "per_species": {
            name: metric_delta(
                left["per_species"][name],
                right["per_species"][name],
                PER_SPECIES_METRICS,
            )
            for name in species
        },
        "summary": metric_delta(
            left["summary"], right["summary"], SUMMARY_METRICS
        ),
    }


def relative_increase(before: float, after: float) -> float | None:
    if before == 0.0:
        return 0.0 if after == 0.0 else None
    return (after - before) / before


def relative_increases(
    before: dict, after: dict, metric: str, species: list[str]
) -> dict[str, float | None]:
    return {
        name: relative_increase(
            float(before["per_species"][name][metric]),
            float(after["per_species"][name][metric]),
        )
        for name in species
    }


def gate_check(name: str, passed: bool, evidence: dict) -> dict:
    return {"name": name, "pass": bool(passed), "evidence": evidence}


def summarize(
    i0_path: Path, h1_path: Path, b1_path: Path, b2_path: Path
) -> dict:
    arms = {
        "I0": load_metrics(i0_path),
        "H1": load_metrics(h1_path),
        "B1": load_metrics(b1_path),
        "B2": load_metrics(b2_path),
    }
    species_sets = {
        name: set(payload["per_species"])
        for name, payload in arms.items()
    }
    expected_species = set(SPECIES)
    if any(observed != expected_species for observed in species_sets.values()):
        raise ValueError("I0/H1/B1/B2 must contain the frozen six species")
    for name, payload in arms.items():
        if payload["mode"] != "apply-only" or payload["observed_splits"] != ["DEV"]:
            raise ValueError(f"{name} input is not a DEV apply-only result")
        if payload["seed"] != 42:
            raise ValueError(f"{name} input is not seed 42")
        values = [
            float(payload["per_species"][species][metric])
            for species in SPECIES
            for metric in PER_SPECIES_METRICS
        ] + [float(payload["summary"][metric]) for metric in SUMMARY_METRICS]
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"{name} input contains non-finite metrics")
    species = list(SPECIES)

    b1 = arms["B1"]
    b2 = arms["B2"]
    b1_per_species = b1["per_species"]
    b2_per_species = b2["per_species"]

    minimum_species_delta = float(b2["summary"]["minimum_species_bp_f1"]) - float(
        b1["summary"]["minimum_species_bp_f1"]
    )
    macro_bp_f1_delta = float(b2["summary"]["macro_bp_f1"]) - float(
        b1["summary"]["macro_bp_f1"]
    )
    species_bp_f1_delta = {
        name: float(b2_per_species[name]["bp_f1"])
        - float(b1_per_species[name]["bp_f1"])
        for name in species
    }
    macro_hardn_delta = float(b2["summary"]["macro_hardN_fp_rate"]) - float(
        b1["summary"]["macro_hardN_fp_rate"]
    )
    species_segment_delta = {
        name: float(b2_per_species[name]["segment_f1_iou_0_8"])
        - float(b1_per_species[name]["segment_f1_iou_0_8"])
        for name in species
    }
    species_boundary_delta = {
        name: float(b2_per_species[name]["boundary_f1_5bp"])
        - float(b1_per_species[name]["boundary_f1_5bp"])
        for name in species
    }
    fragments_relative = relative_increases(
        b1, b2, "fragments_per_truth", species
    )
    split_relative = relative_increases(b1, b2, "split_rate", species)
    species_missed_delta = {
        name: float(b2_per_species[name]["missed_rate"])
        - float(b1_per_species[name]["missed_rate"])
        for name in species
    }

    relative_failures = lambda values: [
        name
        for name, value in values.items()
        if value is None or value > 0.25
    ]
    checks = [
        gate_check(
            "minimum_species_bp_f1_gain",
            minimum_species_delta >= 0.02,
            {
                "B1": float(b1["summary"]["minimum_species_bp_f1"]),
                "B2": float(b2["summary"]["minimum_species_bp_f1"]),
                "delta": minimum_species_delta,
                "threshold": 0.02,
                "rule": "delta >= 0.02",
            },
        ),
        gate_check(
            "macro_bp_f1_delta",
            macro_bp_f1_delta >= -0.005,
            {
                "B1": float(b1["summary"]["macro_bp_f1"]),
                "B2": float(b2["summary"]["macro_bp_f1"]),
                "delta": macro_bp_f1_delta,
                "threshold": -0.005,
                "rule": "delta >= -0.005",
            },
        ),
        gate_check(
            "per_species_bp_f1_loss",
            min(species_bp_f1_delta.values()) >= -0.01,
            {
                "delta_by_species": species_bp_f1_delta,
                "minimum_delta": min(species_bp_f1_delta.values()),
                "threshold": -0.01,
                "rule": "every delta >= -0.01",
            },
        ),
        gate_check(
            "macro_hardN_fp_rate_increase",
            macro_hardn_delta <= 0.005,
            {
                "B1": float(b1["summary"]["macro_hardN_fp_rate"]),
                "B2": float(b2["summary"]["macro_hardN_fp_rate"]),
                "delta": macro_hardn_delta,
                "threshold": 0.005,
                "rule": "delta <= 0.005",
            },
        ),
        gate_check(
            "per_species_segment_f1_iou_0_8_loss",
            min(species_segment_delta.values()) >= -0.05,
            {
                "delta_by_species": species_segment_delta,
                "minimum_delta": min(species_segment_delta.values()),
                "threshold": -0.05,
                "rule": "every delta >= -0.05",
            },
        ),
        gate_check(
            "per_species_boundary_f1_5bp_loss",
            min(species_boundary_delta.values()) >= -0.05,
            {
                "delta_by_species": species_boundary_delta,
                "minimum_delta": min(species_boundary_delta.values()),
                "threshold": -0.05,
                "rule": "every delta >= -0.05",
            },
        ),
        gate_check(
            "per_species_fragments_per_truth_relative_increase",
            not relative_failures(fragments_relative),
            {
                "relative_increase_by_species": fragments_relative,
                "violating_species": relative_failures(fragments_relative),
                "threshold": 0.25,
                "rule": "every relative increase <= 0.25",
            },
        ),
        gate_check(
            "per_species_split_rate_relative_increase",
            not relative_failures(split_relative),
            {
                "relative_increase_by_species": split_relative,
                "violating_species": relative_failures(split_relative),
                "threshold": 0.25,
                "rule": "every relative increase <= 0.25",
            },
        ),
        gate_check(
            "per_species_missed_rate_increase",
            max(species_missed_delta.values()) <= 0.03,
            {
                "delta_by_species": species_missed_delta,
                "maximum_delta": max(species_missed_delta.values()),
                "threshold": 0.03,
                "rule": "every delta <= 0.03",
            },
        ),
    ]
    all_pass = all(item["pass"] for item in checks)
    return {
        "schema_version": "CROSS-SPECIES-L1-SEED42-GATE-1.0.0",
        "status": "seed42_engineering_only",
        "seed42_engineering_only": True,
        "three_seed_gate_required": True,
        "three_seed_gate_replaced": False,
        "inputs": {
            "I0": str(i0_path),
            "H1": str(h1_path),
            "B1": str(b1_path),
            "B2": str(b2_path),
        },
        "species": species,
        "attribution": {
            "I0_to_H1": attribution_delta(arms["I0"], arms["H1"], species),
            "H1_to_B1": attribution_delta(arms["H1"], arms["B1"], species),
        },
        "gate": {
            "all_pass": all_pass,
            "checks": checks,
        },
        "selected_arm": "B2" if all_pass else "B1",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--i0", type=Path, required=True)
    parser.add_argument("--h1", type=Path, required=True)
    parser.add_argument("--b1", type=Path, required=True)
    parser.add_argument("--b2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = summarize(args.i0, args.h1, args.b1, args.b2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
