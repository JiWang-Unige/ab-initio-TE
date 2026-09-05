#!/usr/bin/env python3
"""Apply registered P0R-vs-H0R and P0R-vs-D release rules; never open CONF."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

EXPERIMENT_ID = "CROSS-SPECIES-L1-INIT-HISTORY-V1"
PROTOCOL = EXPERIMENT_ID
RUN_ROLE = "initialization_history_comparison"
OLD_EXPERIMENT = "CROSS-SPECIES-L1-UPSTREAM-20260904"
SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
WORM = "c_elegans"
CONF_STATUS = "historical_closure_only_new_inference_forbidden"


def number(value) -> Decimal:
    """Compare published decimal values without binary subtraction boundary drift."""
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("decision metrics must be finite")
    return result


def validate(artifact: dict, arm: str, split: str, seed: int) -> dict:
    old = arm == "D"
    expected = {
        "experiment": OLD_EXPERIMENT if old else EXPERIMENT_ID,
        "protocol": f"{OLD_EXPERIMENT}-V1" if old else PROTOCOL,
        "run_role": "upstream_coverage_pilot" if old else RUN_ROLE,
        "arm": arm, "split": split, "seed": seed,
        "calibration_scope": "six-species-shared", "conf_evaluated": False,
    }
    for key, value in expected.items():
        if artifact.get(key) != value:
            raise ValueError(f"{arm}/{split}: unexpected {key}: {artifact.get(key)!r}")
    species = {WORM} if split == "SCREEN" else set(SPECIES)
    if set(artifact["species"]) != species or set(artifact["per_species"]) != species:
        raise ValueError(f"{arm}/{split}: species mismatch")
    return artifact["per_species"]


def difference(candidate: dict, reference: dict, key: str) -> Decimal:
    return number(candidate[key]) - number(reference[key])


def bounded_delta(candidate: dict, reference: dict, key: str, bound: str, *, upper=False, strict=False) -> dict:
    delta, limit = difference(candidate, reference, key), Decimal(bound)
    passed = delta <= limit if upper else delta > limit if strict else delta >= limit
    return {"candidate": float(number(candidate[key])), "reference": float(number(reference[key])),
            "delta": float(delta), "bound": float(limit), "direction": "maximum" if upper else "minimum",
            "strict": strict, "pass": passed}


def topology(candidate: dict, reference: dict) -> dict:
    checks = {
        key: bounded_delta(candidate, reference, key, "-0.05")
        for key in ("segment_f1_iou_0_8", "boundary_f1_5bp")
    }
    checks["missed_rate"] = bounded_delta(candidate, reference, "missed_rate", "0.03", upper=True)
    for key in ("fragments_per_truth", "split_rate"):
        cand, ref = number(candidate[key]), number(reference[key])
        checks[key] = {"candidate": float(cand), "reference": float(ref), "maximum_multiplier": 1.25,
                       "pass": cand <= Decimal("1.25") * ref}
    return {"checks": checks, "pass": all(row["pass"] for row in checks.values())}


def contrast(candidate: dict, reference: dict, seed: int) -> dict:
    cdev, rdev = candidate["DEV"]["per_species"], reference["DEV"]["per_species"]
    cscreen, rscreen = candidate["SCREEN"]["per_species"][WORM], reference["SCREEN"]["per_species"][WORM]
    gates = {
        "screen_f1": bounded_delta(cscreen, rscreen, "bp_f1", "0.010" if seed == 42 else "0", strict=seed == 17),
        "worm_dev_f1": bounded_delta(cdev[WORM], rdev[WORM], "bp_f1", "0"),
        "screen_ap": bounded_delta(cscreen, rscreen, "bp_average_precision", "-0.002"),
        "worm_dev_ap": bounded_delta(cdev[WORM], rdev[WORM], "bp_average_precision", "-0.002"),
        "macro_dev_hardN": bounded_delta(candidate["DEV"]["summary"], reference["DEV"]["summary"],
                                        "macro_hardN_fp_rate", "0.005", upper=True),
    }
    for species in SPECIES:
        if species != WORM:
            gates[f"nonworm_dev_f1/{species}"] = bounded_delta(cdev[species], rdev[species], "bp_f1", "-0.01")
    spatial = {"DEV": {sp: topology(cdev[sp], rdev[sp]) for sp in SPECIES},
               "SCREEN": {WORM: topology(cscreen, rscreen)}}
    # Retain all per-panel F1/P/R/AP contrasts, not merely the gate-driving deltas.
    effects = {
        split: {sp: {key: float(difference(candidate[split]["per_species"][sp], reference[split]["per_species"][sp], key))
                     for key in ("bp_f1", "bp_precision", "bp_recall", "bp_average_precision")}
                for sp in candidate[split]["per_species"]}
        for split in ("DEV", "SCREEN")
    }
    return {"gates": gates, "topology": spatial, "effects": effects,
            "pass": all(row["pass"] for row in gates.values()) and
                    all(row["pass"] for panel in spatial.values() for row in panel.values())}


def absolute_readiness(candidate: dict) -> dict:
    panels = {}
    for split in ("DEV", "SCREEN"):
        panels[split] = {}
        for species, row in candidate[split]["per_species"].items():
            checks = {key: number(row[key]) >= Decimal(limit)
                      for key, limit in (("bp_f1", "0.8"), ("bp_precision", "0.75"), ("bp_recall", "0.75"))}
            panels[split][species] = {**checks, "pass": all(checks.values())}
    macro = number(candidate["DEV"]["summary"]["macro_bp_f1"])
    return {"panels": panels, "macro_dev_f1": float(macro), "minimum_macro_dev_f1": 0.83,
            "pass": macro >= Decimal("0.83") and all(row["pass"] for panel in panels.values() for row in panel.values())}


def assess_seed(p0r: dict, h0r: dict, d_anchor: dict, seed: int, seed42_decision: dict | None = None) -> dict:
    if seed not in (42, 17):
        raise ValueError("only registered seeds42/17 are allowed")
    for arm, pair in (("P0R", p0r), ("H0R", h0r), ("D", d_anchor)):
        for split in ("DEV", "SCREEN"):
            validate(pair[split], arm, split, seed)
    comparisons = {"P0R_minus_H0R": contrast(p0r, h0r, seed),
                   "P0R_minus_D_anchor": contrast(p0r, d_anchor, seed)}
    passed = all(row["pass"] for row in comparisons.values())
    readiness = absolute_readiness(p0r)
    freeze_ready = False
    if seed42_decision is not None:
        if seed != 17 or seed42_decision.get("experiment") != EXPERIMENT_ID or seed42_decision.get("seed") != 42:
            raise ValueError("seed17 aggregation requires this protocol's seed42 decision")
        if not seed42_decision["scientific_gate_pass"]:
            raise ValueError("seed17 was not released by seed42")
        freeze_ready = passed and readiness["pass"] and seed42_decision["absolute_readiness"]["pass"]
    if not passed:
        decision = "STOP_INIT_HISTORY_SCIENTIFIC_NO_GO"
    elif seed == 42:
        decision = "RELEASE_PAIRED_H0R_P0R_SEED17"
    elif freeze_ready:
        decision = "FREEZE_READY_INTERNAL_ONLY"
    elif seed42_decision is None:
        decision = "REPLICATION_PASS_SEED42_READINESS_REQUIRED"
    else:
        decision = "CLOSE_TRAINING_EXPANSION_BELOW_ABSOLUTE_READINESS"
    return {
        "experiment": EXPERIMENT_ID, "protocol": PROTOCOL, "run_role": RUN_ROLE, "seed": seed,
        "decision": decision, "scientific_gate_pass": passed, "contrasts": comparisons,
        "absolute_readiness": readiness, "freeze_ready": freeze_ready,
        "two_seed_readiness_assessed": seed == 17 and seed42_decision is not None,
        "release_seed17": seed == 42 and passed, "conf_status": CONF_STATUS,
        "conf_opening_authorized": False, "external_success_claim": False,
        "ci_is_descriptive_not_release_gate": True,
        "claim_scope": "checkpoint initialization choice; reused internal development panels",
    }


def run_assessment(args) -> dict:
    inputs = {}
    pairs = []
    for name in ("p0r", "h0r", "d_anchor"):
        root = Path(getattr(args, f"{name}_dir"))
        pair = {}
        for split in ("DEV", "SCREEN"):
            path = root / f"{split.lower()}_metrics.json"
            inputs[f"{name}_{split}"] = str(path.resolve())
            pair[split] = json.loads(path.read_text())
        pairs.append(pair)
    previous = json.loads(args.seed42_decision.read_text()) if args.seed42_decision else None
    if args.seed == 17 and previous is None:
        raise ValueError("--seed42-decision is required for final seed17 closure")
    result = assess_seed(*pairs, args.seed, previous)
    result["inputs"] = inputs
    if args.seed42_decision:
        result["inputs"]["seed42_decision"] = str(args.seed42_decision.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("p0r-dir", "h0r-dir", "d-anchor-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(42, 17), required=True)
    parser.add_argument("--seed42-decision", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    print(json.dumps(run_assessment(build_parser().parse_args()), indent=2, sort_keys=True), flush=True)
