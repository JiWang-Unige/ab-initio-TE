#!/usr/bin/env python3
"""Run one fixed-D historical-candidate external screen.

This wrapper reuses the existing RC0 scorer for forward, reverse-complement,
mean and one predeclared phase arm. The explicit calibration reader verifies
the shared CAL scope and frozen seed without refitting anything. The current
artifact already carries the X0 calibration_protocol accepted by the original
FASTA reader; its upstream protocol field is experiment provenance, not an
incompatibility requiring a new protocol alias.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any


TRAINING_SPECIES = {"human", "mouse", "chicken", "zebrafish", "pig", "c_elegans"}
EXPECTED_SCOPE = "six-species-shared"
EXPECTED_SPLIT = "CAL"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def fixed_calibration_loader(args: Any) -> dict[str, Any]:
    calibration = read_json(Path(args.calibration_json))
    if calibration.get("calibration_scope") != EXPECTED_SCOPE:
        raise ValueError("calibration is not the six-species shared CAL artifact")
    if calibration.get("fit_split") != EXPECTED_SPLIT:
        raise ValueError("calibration fit split is not CAL")
    if int(calibration.get("seed")) != 42:
        raise ValueError("fixed external screen requires D seed42")
    for key in ("platt_slope", "platt_intercept", "threshold"):
        value = float(calibration[key])
        if not math.isfinite(value):
            raise ValueError(f"non-finite calibration value: {key}")
    # Current artifact includes both fields.  Accept only these known protocol
    # identities; do not bypass an unrelated calibration by dropping a guard.
    accepted = {
        "CROSS-SPECIES-L1-X0-PLATT-V1",
        "CROSS-SPECIES-L1-UPSTREAM-20260904-V1",
    }
    identities = {calibration.get("calibration_protocol"), calibration.get("protocol")}
    if not identities.intersection(accepted):
        raise ValueError(f"unsupported calibration protocol fields: {sorted(str(v) for v in identities)}")
    return calibration


def load_rc0(repo_root: Path):
    return load_module(
        repo_root / "scripts/experiments/D-EXTERNAL-RC0-20260914/rc0.py",
        "fixed_d_rc0_core",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    config = read_json(args.config)
    candidates = config.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("config candidates must be a list")
    candidate = next((row for row in candidates if row.get("id") == args.candidate), None)
    if candidate is None:
        raise ValueError(f"candidate not found: {args.candidate}")
    if bool(candidate.get("sealed")):
        raise ValueError("sealed candidate is not permitted")
    if args.candidate in TRAINING_SPECIES:
        raise ValueError("candidate is a D supervised training species")
    if candidate.get("pretraining_exclusion") != "not established":
        raise ValueError("unexpected pretraining exclusion claim")
    if not Path(str(candidate["label_out"])).is_file():
        raise FileNotFoundError(f"prepared label subset missing: {candidate['label_out']}")
    if len(candidate.get("regions", [])) != 4:
        raise ValueError("fixed screen requires exactly four regions")
    if config.get("selection_rule", {}).get("score_or_label_selection") is not False:
        raise ValueError("score/label-based region selection is not allowed")

    repo_root = Path(__file__).resolve().parents[3]
    rc0 = load_rc0(repo_root)
    rc0.inference.load_calibration = fixed_calibration_loader
    config["remote_root"] = str(config["remote_data_root"])
    # rc0.run takes a small argparse-like namespace.  Keeping this call here
    # preserves the existing calibrated model loading and evaluator semantics.
    run_args = argparse.Namespace(
        config=args.config,
        candidate=args.candidate,
        output_dir=args.output_dir,
        remote_root=Path(config["remote_data_root"]),
        model_dir=None,
        tokenizer_dir=None,
        model_code_dir=None,
        calibration_json=None,
        batch_size=args.batch_size,
        cpu=args.cpu,
    )
    summary = rc0.run(run_args)
    summary.update(
        {
            "closure_protocol": "ANIMAL-GENERALIZATION-CLOSURE-20260917-FIXED-PANEL-V1",
            "screen_class": "historical-candidate source-dependent external screen",
            "task_training_status": "candidate not in six-species D supervised training table",
            "pretraining_exclusion": "not established",
            "region_selection": {
                "rule": "first four source chrom.sizes rows, centered 1,048,576-bp intervals",
                "score_or_label_selection": False,
                "label_trim_only_after_region_freeze": True,
            },
            "phase_policy": {
                "phase_offset_bp": int(config["selection_rule"].get("phase_offset_bp", 3)),
                "status": "one predeclared RC0 phase arm; no phase search",
                "ordinary_window_origin": 0,
            },
            "claim_boundary": "same-assembly source-dependent comparator; unlabelled sequence is not negative; no full-genome biological accuracy claim",
        }
    )
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (args.output_dir / "screen_qualification.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "candidate": args.candidate,
                "species": candidate["species"],
                "assembly": candidate["assembly"],
                "historical_exposure": candidate["historical_exposure"],
                "pretraining_exclusion": candidate["pretraining_exclusion"],
                "label_status": candidate["label_status"],
                "label_audit": candidate.get("label_audit"),
                "summary": str(summary_path.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "COMPLETED", "candidate": args.candidate, "output_dir": str(args.output_dir.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
