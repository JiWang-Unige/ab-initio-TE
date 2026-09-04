#!/usr/bin/env python3
"""Apply the preregistered seed-42 L-versus-D release gate."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


EXPERIMENT_ID = "CROSS-SPECIES-L1-UPSTREAM-20260904"
PROTOCOL = f"{EXPERIMENT_ID}-V1"
RUN_ROLE = "upstream_coverage_pilot"
SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
WORM = "c_elegans"
NONWORM = tuple(species for species in SPECIES if species != WORM)
SCREEN_AP_GAIN, SCREEN_F1_GAIN = 0.01, 0.01
NONWORM_F1_DROP, TOPOLOGY_F1_DROP = 0.01, 0.05
GEOMETRY_MULTIPLIER, MISSED_RATE_INCREASE = 1.25, 0.03
HARDN_INCREASE = 0.005
TARGET_F1, TARGET_PR, TARGET_MACRO_F1 = 0.80, 0.75, 0.83
RELEASE_PAIRED = "RELEASE_PAIRED_LD_SEED17"
RELEASE_L = "RELEASE_L_SEED17"
STOP = "STOP_WEAK_NO_SIGNAL"


def _number(value, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _rows(metrics: dict, expected: set[str], label: str) -> dict[str, dict]:
    rows = metrics["per_species"]
    if set(rows) != expected:
        raise ValueError(f"{label} species mismatch: {sorted(set(rows))} != {sorted(expected)}")
    return rows


def _delta(left: dict, right: dict, key: str, label: str) -> float:
    return _number(right[key], f"D {label}.{key}") - _number(left[key], f"L {label}.{key}")


def _topology(left: dict[str, dict], right: dict[str, dict], panel: str) -> dict:
    result = {}
    for species in sorted(left):
        l, d, label = left[species], right[species], f"{panel}/{species}"
        segment = _delta(l, d, "segment_f1_iou_0_8", label)
        boundary = _delta(l, d, "boundary_f1_5bp", label)
        l_frag, d_frag = _number(l["fragments_per_truth"], f"L {label}.fragments_per_truth"), _number(d["fragments_per_truth"], f"D {label}.fragments_per_truth")
        l_split, d_split = _number(l["split_rate"], f"L {label}.split_rate"), _number(d["split_rate"], f"D {label}.split_rate")
        missed = _delta(l, d, "missed_rate", label)
        row = {
            "segment_f1_iou_0_8_delta": segment,
            "boundary_f1_5bp_delta": boundary,
            "fragments_per_truth_L": l_frag,
            "fragments_per_truth_D": d_frag,
            "split_rate_L": l_split,
            "split_rate_D": d_split,
            "missed_rate_delta": missed,
            "pass_segment_f1_iou_0_8": segment >= -TOPOLOGY_F1_DROP,
            "pass_boundary_f1_5bp": boundary >= -TOPOLOGY_F1_DROP,
            "pass_fragments_per_truth": d_frag <= GEOMETRY_MULTIPLIER * l_frag,
            "pass_split_rate": d_split <= GEOMETRY_MULTIPLIER * l_split,
            "pass_missed_rate": missed <= MISSED_RATE_INCREASE,
        }
        row["pass"] = all(row[key] for key in (
            "pass_segment_f1_iou_0_8", "pass_boundary_f1_5bp",
            "pass_fragments_per_truth", "pass_split_rate", "pass_missed_rate",
        ))
        result[species] = row
    return result


def _targets(rows: dict[str, dict]) -> dict[str, dict[str, bool]]:
    result = {}
    for species, row in sorted(rows.items()):
        checks = {
            "bp_f1": _number(row["bp_f1"], f"L {species}.bp_f1") >= TARGET_F1,
            "bp_precision": _number(row["bp_precision"], f"L {species}.bp_precision") >= TARGET_PR,
            "bp_recall": _number(row["bp_recall"], f"L {species}.bp_recall") >= TARGET_PR,
        }
        checks["pass"] = all(checks.values())
        result[species] = checks
    return result


def decide_pair(l_dev: dict, l_screen: dict, d_dev: dict, d_screen: dict) -> dict:
    """Return gate evidence and one of the three allowed release decisions."""

    artifacts = (l_dev, l_screen, d_dev, d_screen)
    protocols = {a["protocol"] for a in artifacts if "protocol" in a}
    seeds = {a["seed"] for a in artifacts if "seed" in a}
    if protocols and protocols != {PROTOCOL}:
        raise ValueError(f"unexpected protocol(s): {sorted(protocols)}")
    if seeds and seeds != {42}:
        raise ValueError(f"decision requires seed42 artifacts, observed {sorted(seeds)}")

    ld, dd = _rows(l_dev, set(SPECIES), "L DEV"), _rows(d_dev, set(SPECIES), "D DEV")
    ls, ds = _rows(l_screen, {WORM}, "L SCREEN"), _rows(d_screen, {WORM}, "D SCREEN")
    screen_ap = _delta(ls[WORM], ds[WORM], "bp_average_precision", "SCREEN/c_elegans")
    screen_f1 = _delta(ls[WORM], ds[WORM], "bp_f1", "SCREEN/c_elegans")
    screen_gate = {
        "delta_bp_average_precision": screen_ap, "delta_bp_f1": screen_f1,
        "minimum_delta_bp_average_precision": SCREEN_AP_GAIN,
        "minimum_delta_bp_f1": SCREEN_F1_GAIN,
        "pass": screen_ap >= SCREEN_AP_GAIN and screen_f1 >= SCREEN_F1_GAIN,
    }
    nonworm_deltas = {sp: _delta(ld[sp], dd[sp], "bp_f1", f"DEV/{sp}") for sp in NONWORM}
    nonworm_gate = {
        "maximum_drop": NONWORM_F1_DROP, "deltas": nonworm_deltas,
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
    l_summary, d_summary = l_dev["summary"], d_dev["summary"]
    hardn_delta = _delta(l_summary, d_summary, "macro_hardN_fp_rate", "DEV summary")
    hardn_gate = {
        "delta_macro_hardN_fp_rate": hardn_delta, "maximum_increase": HARDN_INCREASE,
        "pass": hardn_delta <= HARDN_INCREASE,
    }
    targets = {"DEV": _targets(ld), "SCREEN": _targets(ls)}
    macro_f1 = _number(l_summary["macro_bp_f1"], "L DEV summary.macro_bp_f1")
    target_gate = {
        "targets": targets, "macro_dev_bp_f1": macro_f1,
        "minimum_macro_dev_bp_f1": TARGET_MACRO_F1,
        "pass": all(row["pass"] for panel in targets.values() for row in panel.values()) and macro_f1 >= TARGET_MACRO_F1,
    }
    paired = all(gate["pass"] for gate in (screen_gate, nonworm_gate, topology_gate, hardn_gate))
    decision = RELEASE_PAIRED if paired else RELEASE_L if target_gate["pass"] else STOP
    return {
        "experiment": EXPERIMENT_ID, "protocol": PROTOCOL, "run_role": RUN_ROLE,
        "comparison_seed": 42, "science_scope": "Label-A comparator; internal pilot",
        "historical_B1": "descriptive_only_not_used", "conf_status": "sealed_not_evaluated",
        "d2_policy": "If D is released, seed17 paired L/D must preserve the same signs on new CONF.",
        "decision": decision, "paired_gate_pass": paired,
        "screen_gain_gate": screen_gate, "nonworm_dev_f1_gate": nonworm_gate,
        "topology_guardrails": topology_gate, "macro_dev_hardN_gate": hardn_gate,
        "L_internal_target": target_gate,
        "release": {
            "seed17": decision in {RELEASE_PAIRED, RELEASE_L},
            "arms": ["L", "D"] if decision == RELEASE_PAIRED else ["L"] if decision == RELEASE_L else [],
            "no_extra_training_or_new_pool_on_stop": decision == STOP,
        },
    }


decide = decide_pair


def run_decision(l_root: Path, d_root: Path, output: Path) -> dict:
    paths = {key: Path(root) / filename for key, root, filename in (
        ("l_dev", l_root, "dev_metrics.json"), ("l_screen", l_root, "screen_metrics.json"),
        ("d_dev", d_root, "dev_metrics.json"), ("d_screen", d_root, "screen_metrics.json"),
    )}
    values = [json.loads(paths[key].read_text()) for key in ("l_dev", "l_screen", "d_dev", "d_screen")]
    result = decide_pair(*values)
    result["inputs"] = {key: str(path.resolve()) for key, path in paths.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l-dir", "--l-root", dest="l_root", type=Path, required=True)
    parser.add_argument("--d-dir", "--d-root", dest="d_root", type=Path, required=True)
    parser.add_argument("--output", "--decision-json", dest="output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    print(json.dumps(run_decision(args.l_root, args.d_root, args.output), indent=2, sort_keys=True), flush=True)
