#!/usr/bin/env python3
"""Apply frozen CAL calibration to the sealed worm CONF panel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from diagnose_worm_generalization import cache_tiles  # noqa: E402
import evaluate_upstream as upstream  # noqa: E402


EXPERIMENT_ID = upstream.EXPERIMENT_ID
PROTOCOL = upstream.PROTOCOL
RUN_ROLE = upstream.RUN_ROLE
ARM_CHOICES = upstream.ARM_CHOICES
SPECIES = tuple(upstream.SPECIES)
WORM = upstream.WORM
CONF_SPLIT = "CONF"
CONF_TILES = 256
CALIBRATION_PROTOCOL = "CROSS-SPECIES-L1-X0-PLATT-V1"


def _expected_model_code_dir(value: Path | None) -> str | None:
    return str(value.resolve()) if value is not None else None


def load_calibration(
    path: Path,
    arm: str,
    seed: int,
    model_dir: Path,
    model_code_dir: Path | None,
) -> dict:
    """Read and validate the frozen six-species CAL calibration."""

    calibration = json.loads(path.read_text())
    expected = {
        "experiment": EXPERIMENT_ID,
        "protocol": PROTOCOL,
        "run_role": RUN_ROLE,
        "arm": arm,
        "seed": seed,
        "calibration_protocol": CALIBRATION_PROTOCOL,
        "calibration_scope": "six-species-shared",
        "fit_split": "CAL",
    }
    for key, value in expected.items():
        if calibration.get(key) != value:
            raise ValueError(
                f"calibration metadata mismatch for {key}: "
                f"{calibration.get(key)!r} != {value!r}"
            )
    if set(calibration.get("species", [])) != set(SPECIES):
        raise ValueError("calibration must cover exactly the six shared CAL species")
    if calibration.get("model_dir") != str(model_dir.resolve()):
        raise ValueError("calibration artifact belongs to a different final_model")
    if calibration.get("tokenizer_dir") != str(model_dir.resolve()):
        raise ValueError("CONF evaluation requires the model directory tokenizer")
    if calibration.get("model_code_dir") != _expected_model_code_dir(model_code_dir):
        raise ValueError("calibration artifact belongs to a different model code directory")

    contract = calibration.get("evaluation_contract")
    if not isinstance(contract, dict):
        raise ValueError("calibration is missing its evaluation contract")
    if contract.get("dev_split") != "DEV" or contract.get("screen_split") != "SCREEN":
        raise ValueError("calibration evaluation contract has unexpected DEV/SCREEN splits")
    if contract.get("forbidden_split") != CONF_SPLIT:
        raise ValueError("calibration does not forbid CONF during calibration")
    if contract.get("conf_status") != "sealed_not_evaluated":
        raise ValueError("calibration artifact is not the pre-CONF frozen calibration")
    return calibration


def conf_data_specs(data_root: Path) -> list[tuple[str, Path]]:
    """Return the sole materialized worm CONF input."""

    return [(WORM, data_root / CONF_SPLIT / f"{WORM}.jsonl.gz")]


def _check_conf_panel(panel: dict[str, list[dict]]) -> None:
    if set(panel) != {WORM}:
        raise ValueError(f"CONF must contain only {WORM}, observed {sorted(panel)}")
    tiles = panel[WORM]
    observed = {tile["split"] for tile in tiles}
    if observed != {CONF_SPLIT}:
        raise ValueError(f"expected CONF records, observed {sorted(observed)}")
    if len(tiles) != CONF_TILES:
        raise ValueError(f"expected {CONF_TILES} CONF tiles, observed {len(tiles)}")


def _metric_artifact(
    panel: dict[str, list[dict]],
    calibration: dict,
    args,
    calibration_path: Path,
    cache_path: Path,
) -> dict:
    per_species, summary = upstream.legacy.evaluate(
        panel,
        float(calibration["platt_slope"]),
        float(calibration["platt_intercept"]),
        float(calibration["threshold"]),
    )
    return {
        "experiment": EXPERIMENT_ID,
        "protocol": PROTOCOL,
        "run_role": RUN_ROLE,
        "arm": args.arm,
        "seed": args.seed,
        "model_dir": str(Path(args.model_dir).resolve()),
        "calibration_json": str(calibration_path.resolve()),
        "calibration_scope": "six-species-shared",
        "calibration_fit_split": "CAL",
        "split": CONF_SPLIT,
        "species": [WORM],
        "conf_evaluated": True,
        "per_species": per_species,
        "summary": summary,
        "cache_npz": str(cache_path.resolve()),
        "data_root": str(Path(args.data_root).resolve()),
    }


def evaluate_conf(args) -> dict:
    """Infer CONF once and apply, but never fit, the supplied calibration."""

    if args.arm not in ARM_CHOICES:
        raise ValueError(f"unsupported arm: {args.arm}")
    if args.seed not in (17, 42):
        raise ValueError(f"unsupported seed: {args.seed}")

    model_dir = Path(args.model_dir)
    calibration_path = Path(args.calibration_json)
    calibration = load_calibration(
        calibration_path,
        args.arm,
        args.seed,
        model_dir,
        args.model_code_dir,
    )
    specs = conf_data_specs(Path(args.data_root))
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)

    model, tokenizer, device = upstream.legacy.load_final_model(
        model_dir, model_dir, args.cpu, args.model_code_dir
    )
    try:
        panel = upstream.legacy.infer_inputs(
            model, tokenizer, device, specs, args.batch_size
        )
        _check_conf_panel(panel)
        cache_path = output / "CONF_margins.npz"
        cache_tiles(cache_path, panel[WORM])
        artifact = _metric_artifact(
            panel, calibration, args, calibration_path, cache_path
        )
        upstream.legacy.write_json(output / "conf_metrics.json", artifact)
    finally:
        del model, tokenizer
    return artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARM_CHOICES, required=True)
    parser.add_argument("--seed", type=int, choices=(17, 42), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--calibration-json", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--model-code-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--cpu", action="store_true")
    return parser


def main() -> None:
    print(json.dumps(evaluate_conf(build_parser().parse_args()), indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
