#!/usr/bin/env python3
"""Assess the registered seed-17 L/D replication before opening CONF."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from decide_upstream import (  # noqa: E402
    EXPERIMENT_ID,
    GEOMETRY_MULTIPLIER,
    HARDN_INCREASE,
    MISSED_RATE_INCREASE,
    NONWORM,
    NONWORM_F1_DROP,
    PROTOCOL,
    RUN_ROLE,
    TOPOLOGY_F1_DROP,
    WORM,
    _delta,
    _rows,
    _topology,
)


REPLICATION_SEED = 17
EXPECTED_SCOPE = "six-species-shared"
PROCEED = "PROCEED_TO_PREREGISTERED_CONF"
STOP = "STOP_D2_NO_CONSISTENT_SIGNAL"


def _validate_artifact(
    artifact: dict, expected_arm: str, expected_split: str, expected_species: set[str]
) -> None:
    label = f"{expected_arm} {expected_split}"
    expected = {
        "experiment": EXPERIMENT_ID,
        "protocol": PROTOCOL,
        "run_role": RUN_ROLE,
        "arm": expected_arm,
        "seed": REPLICATION_SEED,
        "calibration_scope": EXPECTED_SCOPE,
        "split": expected_split,
        "conf_evaluated": False,
    }
    for key, value in expected.items():
        if key not in artifact or artifact[key] != value:
            raise ValueError(f"{label} metadata mismatch for {key}: {artifact.get(key)!r}")
    if set(artifact.get("species", [])) != expected_species:
        raise ValueError(f"{label} species metadata mismatch")
    _rows(artifact, expected_species, label)


def _validate_pair(l_dev: dict, l_screen: dict, d_dev: dict, d_screen: dict) -> None:
    _validate_artifact(l_dev, "L", "DEV", set(NONWORM) | {WORM})
    _validate_artifact(l_screen, "L", "SCREEN", {WORM})
    _validate_artifact(d_dev, "D", "DEV", set(NONWORM) | {WORM})
    _validate_artifact(d_screen, "D", "SCREEN", {WORM})


def assess_pair(l_dev: dict, l_screen: dict, d_dev: dict, d_screen: dict) -> dict:
    """Return D2 consistency evidence for the seed-17 paired L/D artifacts.

    The D1 release gate established positive SCREEN AP/F1 direction.  D2 only
    asks whether seed 17 preserves those signs; its stricter seed-42 gains are
    deliberately not reapplied.  CONF remains sealed and this function never
    returns a release decision.
    """

    _validate_pair(l_dev, l_screen, d_dev, d_screen)
    ld = _rows(l_dev, set(NONWORM) | {WORM}, "L DEV")
    dd = _rows(d_dev, set(NONWORM) | {WORM}, "D DEV")
    ls = _rows(l_screen, {WORM}, "L SCREEN")
    ds = _rows(d_screen, {WORM}, "D SCREEN")

    screen_ap = _delta(ls[WORM], ds[WORM], "bp_average_precision", "SCREEN/c_elegans")
    screen_f1 = _delta(ls[WORM], ds[WORM], "bp_f1", "SCREEN/c_elegans")
    direction = {
        "seed": REPLICATION_SEED,
        "required_screen_direction": "positive",
        "delta_bp_average_precision": screen_ap,
        "delta_bp_f1": screen_f1,
        "pass": screen_ap > 0 and screen_f1 > 0,
    }

    nonworm_deltas = {
        species: _delta(ld[species], dd[species], "bp_f1", f"DEV/{species}")
        for species in NONWORM
    }
    nonworm = {
        "maximum_drop": NONWORM_F1_DROP,
        "deltas": nonworm_deltas,
        "pass": all(delta >= -NONWORM_F1_DROP for delta in nonworm_deltas.values()),
    }
    topology = {"DEV": _topology(ld, dd, "DEV"), "SCREEN": _topology(ls, ds, "SCREEN")}
    topology_gate = {
        "segment_and_boundary_drop": TOPOLOGY_F1_DROP,
        "fragments_and_split_multiplier": GEOMETRY_MULTIPLIER,
        "missed_rate_increase": MISSED_RATE_INCREASE,
        "panels": topology,
        "pass": all(row["pass"] for panel in topology.values() for row in panel.values()),
    }
    hardn_delta = _delta(
        l_dev["summary"], d_dev["summary"], "macro_hardN_fp_rate", "DEV summary"
    )
    hardn = {
        "delta_macro_hardN_fp_rate": hardn_delta,
        "maximum_increase": HARDN_INCREASE,
        "pass": hardn_delta <= HARDN_INCREASE,
    }
    guardrails = {
        "nonworm_dev_f1": nonworm,
        "topology": topology_gate,
        "macro_dev_hardN": hardn,
        "pass": all(gate["pass"] for gate in (nonworm, topology_gate, hardn)),
    }
    consistent = direction["pass"] and guardrails["pass"]
    return {
        "experiment": EXPERIMENT_ID,
        "protocol": PROTOCOL,
        "run_role": RUN_ROLE,
        "comparison_seed": REPLICATION_SEED,
        "seed": REPLICATION_SEED,
        "arms": ["L", "D"],
        "science_scope": "Label-A comparator; internal paired replication",
        "direction": direction,
        "guardrails": guardrails,
        "consistent_positive_screen_signal": consistent,
        "conf_status": "sealed_not_evaluated",
        "proceed_to_conf": consistent,
        "conf_opening_note": (
            "Conditional readiness only: freeze the model/calibration list and "
            "register paired spatial-block confidence intervals before opening CONF."
        ),
        "decision": PROCEED if consistent else STOP,
        "release_claim": False,
    }


def run_assessment(l_root: Path, d_root: Path, output: Path) -> dict:
    paths = {
        "l_dev": Path(l_root) / "dev_metrics.json",
        "l_screen": Path(l_root) / "screen_metrics.json",
        "d_dev": Path(d_root) / "dev_metrics.json",
        "d_screen": Path(d_root) / "screen_metrics.json",
    }
    values = [json.loads(paths[key].read_text()) for key in ("l_dev", "l_screen", "d_dev", "d_screen")]
    result = assess_pair(*values)
    result["inputs"] = {key: str(path.resolve()) for key, path in paths.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l-dir", type=Path, required=True)
    parser.add_argument("--d-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    print(json.dumps(run_assessment(args.l_dir, args.d_dir, args.output), indent=2, sort_keys=True), flush=True)
