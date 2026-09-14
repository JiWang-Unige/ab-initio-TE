"""Frozen PAIR8 gates against BOTH BLOCK4 and same-seed archived D."""
import argparse
import importlib.util
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-INIT-HISTORY-V1" / "assess_init.py"
spec = importlib.util.spec_from_file_location("pair_context_metric_helpers", SOURCE)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
PROTOCOL = "CROSS-SPECIES-L1-PAIR-CONTEXT-V1"
helpers.EXPERIMENT_ID = helpers.PROTOCOL = PROTOCOL
helpers.RUN_ROLE = "pair_context_registered_evaluation"


def contrast(candidate, reference, seed):
    # All AP/nonworm/topology/hardN definitions are identical to the earlier
    # evaluator. Replace only the two explicitly newly approved effect gates.
    result = helpers.contrast(candidate, reference, seed)
    for split, key in (("SCREEN", "screen_f1"), ("DEV", "worm_dev_f1")):
        result["gates"][key] = helpers.bounded_delta(
            candidate[split]["per_species"][helpers.WORM],
            reference[split]["per_species"][helpers.WORM], "bp_f1",
            "0.005" if seed == 42 else "0", strict=seed == 17,
        )
    result["pass"] = (all(row["pass"] for row in result["gates"].values()) and
                      all(row["pass"] for panel in result["topology"].values() for row in panel.values()))
    return result


def assess(candidate, control, anchor, seed, seed42=None):
    if seed not in (42, 17):
        raise ValueError("registered seeds are 42 and conditional 17")
    for arm, panels in (("PAIR8", candidate), ("BLOCK4", control), ("D", anchor)):
        for split in ("DEV", "SCREEN"):
            helpers.validate(panels[split], arm, split, seed)
    if seed == 17:
        if (seed42 is None or seed42.get("protocol") != PROTOCOL or seed42.get("seed") != 42
                or seed42.get("release_seed17") is not True):
            raise ValueError("seed17 requires this protocol's complete seed42 release")
    elif seed42 is not None:
        raise ValueError("seed42 does not consume a previous-seed decision")
    comparisons = {"PAIR8_minus_BLOCK4": contrast(candidate, control, seed),
                   "PAIR8_minus_D": contrast(candidate, anchor, seed)}
    readiness = helpers.absolute_readiness(candidate)
    passed = readiness["pass"] and all(row["pass"] for row in comparisons.values())
    decision = ("RELEASE_MATCHED_SEED17" if seed == 42 else "INTERNAL_CANDIDATE_ONLY") if passed else "STOP_PAIR_CONTEXT_SCIENTIFIC_NO_GO"
    return {"experiment": PROTOCOL, "protocol": PROTOCOL, "seed": seed,
            "decision": decision, "scientific_gate_pass": passed,
            "absolute_readiness": readiness, "contrasts": comparisons,
            "release_seed17": seed == 42 and passed,
            "two_seed_internal_candidate": seed == 17 and passed,
            "conf_opening_authorized": False, "external_success_claim": False,
            "scientific_scope": "effective sequence context; reused internal development panels"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pair8-dir", "block4-dir", "d-dir", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(42, 17), required=True)
    parser.add_argument("--seed42-decision", type=Path)
    args = parser.parse_args()
    panels, paths = [], {}
    for arm, root in (("PAIR8", args.pair8_dir), ("BLOCK4", args.block4_dir), ("D", args.d_dir)):
        panels.append({split: json.loads((root / f"{split.lower()}_metrics.json").read_text())
                       for split in ("DEV", "SCREEN")})
        paths[arm] = str(root.resolve())
    previous = json.loads(args.seed42_decision.read_text()) if args.seed42_decision else None
    result = assess(*panels, args.seed, previous)
    result["inputs"] = paths
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
