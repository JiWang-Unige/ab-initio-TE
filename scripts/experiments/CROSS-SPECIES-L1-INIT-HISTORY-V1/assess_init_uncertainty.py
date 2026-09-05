#!/usr/bin/env python3
"""Paired spatial uncertainty on reused worm SCREEN/DEV, never CONF or a release gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assess_init as decision
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-UPSTREAM-20260904"))
import assess_conf as core  # Numerical helpers only; never its CONF loader or decisions.

EXPERIMENT_ID = decision.EXPERIMENT_ID
PANELS = ("SCREEN", "DEV")
ARMS = ("P0R", "H0R", "D")
METRICS = core.METRICS
BLOCK_BP = core.BLOCK_BP
REPLICATES = core.BOOTSTRAP_REPLICATES
RNG_SEED = core.BOOTSTRAP_SEED
CACHE_KEYS = ("margin", "truth", "callable", "hard_negative", "tile_id", "chrom", "start")


def load_panel(directory: Path, seed: int, arm: str, split: str) -> dict:
    if split not in PANELS:
        raise ValueError("only worm SCREEN/DEV are allowed; CONF inference/diagnostics are forbidden")
    if arm not in ARMS or seed not in (42, 17):
        raise ValueError("only registered seed42/17 P0R/H0R/D panels are allowed")
    directory = Path(directory)
    if arm == "D":
        report_path = directory / "diagnostic.json"
        report = json.loads(report_path.read_text())
        if any(report.get(k) != v for k, v in {
            "protocol": EXPERIMENT_ID, "stage": "J0-A", "seed": seed,
            "mode": "apply-only", "status": "COMPLETED",
        }.items()):
            raise ValueError(f"{report_path}: expected completed same-seed J0-A")
        metrics_path = Path(report["panels"][split]["expected_metrics_path"])
    else:
        report_path = None
        metrics_path = directory / f"{split.lower()}_metrics.json"
    metadata = json.loads(metrics_path.read_text())
    decision.validate(metadata, arm, split, seed)
    calibration_path = Path(metadata["calibration_json"])
    calibration = json.loads(calibration_path.read_text())
    for key, value in {"arm": arm, "seed": seed, "calibration_scope": "six-species-shared", "fit_split": "CAL"}.items():
        if calibration.get(key) != value:
            raise ValueError(f"{calibration_path}: calibration {key} mismatch")
    if set(calibration["species"]) != set(decision.SPECIES):
        raise ValueError("calibration must use the frozen six-species CAL")
    if Path(calibration["model_dir"]).resolve() != Path(metadata["model_dir"]).resolve():
        raise ValueError("metrics and calibrator belong to different models")
    if arm == "D" and (Path(report["calibration_json"]).resolve() != calibration_path.resolve()
                       or Path(report["model_dir"]).resolve() != Path(metadata["model_dir"]).resolve()):
        raise ValueError("J0 cache provenance differs from archived D metrics/calibration")
    cache_path = directory / "margins" / split / f"{decision.WORM}.npz"
    with np.load(cache_path, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in CACHE_KEYS}
        if "split" in archive and set(archive["split"].tolist()) != {split}:
            raise ValueError("cache split differs from requested SCREEN/DEV panel")
        if "species" in archive and set(archive["species"].tolist()) != {decision.WORM}:
            raise ValueError("only worm cache is eligible for this consumer")
    margin = arrays["margin"]
    if margin.dtype != np.float32 or margin.ndim != 2 or not margin.size or not np.all(np.isfinite(margin)):
        raise ValueError("cache requires nonempty finite raw float32 tile margins")
    for key in ("truth", "callable", "hard_negative"):
        if arrays[key].shape != margin.shape:
            raise ValueError(f"cache {key} shape differs from margins")
        arrays[key] = arrays[key].astype(bool)
    for key in ("tile_id", "chrom", "start"):
        if arrays[key].shape != (margin.shape[0],):
            raise ValueError(f"cache {key} does not match tile count")
    order = np.lexsort((arrays["tile_id"], arrays["start"], arrays["chrom"]))
    arrays = {key: value[order] for key, value in arrays.items()}
    return {
        **arrays, "tile_id": arrays["tile_id"].tolist(), "chrom": arrays["chrom"].tolist(),
        "metadata": metadata, "metrics_path": metrics_path.resolve(),
        "calibration": {key: core._finite(calibration[key], key)
                        for key in ("platt_slope", "platt_intercept", "threshold")},
        "inputs": {"directory": str(directory.resolve()), "metrics": str(metrics_path.resolve()),
                   "calibration_json": str(calibration_path.resolve()), "margins": str(cache_path.resolve()),
                   "j0_report": str(report_path.resolve()) if report_path else None},
    }


def align_panels(panels: dict[str, dict]) -> None:
    first = next(iter(panels.values()))
    for name, panel in panels.items():
        for key in CACHE_KEYS[1:]:
            if not np.array_equal(panel[key], first[key]):
                raise ValueError(f"{name}: paired coordinate/label alignment differs for {key}")
        if panel["margin"].shape != first["margin"].shape:
            raise ValueError(f"{name}: paired margin shape differs")
    # The registered 8192-bp tile grid fits in the existing occupied-block scheme.
    # Refuse a crossing tile rather than incorrectly assign its far side to the start block.
    starts = np.asarray(first["start"], dtype=np.int64)
    if np.any(starts // BLOCK_BP != (starts + first["margin"].shape[1] - 1) // BLOCK_BP):
        raise ValueError("a tile crosses a 512kb block; cannot reuse registered tile-block assignment")


def mean_or_none(values):
    return None if any(value is None for value in values) else float(np.mean(values))


def assess_panel(panels: dict[str, dict], seeds: tuple[int, ...], *, replicates=REPLICATES) -> dict:
    """Use one set of occupied-block draws for every arm and seed on this panel."""
    align_panels(panels)
    first = next(iter(panels.values()))
    blocks = core.occupied_blocks(first["chrom"], first["start"])
    prepared = {key: core._prepared_arm(panel) for key, panel in panels.items()}
    points, counts = {}, {}
    for key, arm in prepared.items():
        points[key], counts[key] = core._metric_values(
            arm["margin"], arm["truth"], arm["callable"], arm["slope"], arm["intercept"], arm["threshold"],
            ap_order=arm["ap_order"], ap_tie_ends=arm["ap_tie_ends"],
        )
        core._check_point_reproduction(panels[key], points[key])
    draws = np.random.default_rng(RNG_SEED).integers(0, len(blocks), size=(replicates, len(blocks)))
    values = {key: {metric: [] for metric in METRICS} for key in prepared}
    for draw in draws:
        tile_weights = np.zeros(first["margin"].shape[0], dtype=np.float64)
        for block, multiplicity in zip(blocks, np.bincount(draw, minlength=len(blocks))):
            tile_weights[block] = multiplicity
        weights = np.repeat(tile_weights, first["margin"].shape[1])
        for key, arm in prepared.items():
            row, _ = core._metric_values(
                arm["margin"], arm["truth"], arm["callable"], arm["slope"], arm["intercept"], arm["threshold"],
                weights=weights, ap_order=arm["ap_order"], ap_tie_ends=arm["ap_tie_ends"],
            )
            for metric in METRICS:
                values[key][metric].append(row[metric])
    absolute = {key: {metric: core._summary(points[key][metric], values[key][metric]) for metric in METRICS}
                for key in prepared}
    paired, mean = {}, {}
    for reference in ("H0R", "D"):
        name = f"P0R_minus_{'D_anchor' if reference == 'D' else reference}"
        paired[name] = {}
        delta_draws, delta_points = {}, {}
        for seed in seeds:
            candidate, ref = f"seed{seed}_P0R", f"seed{seed}_{reference}"
            delta_draws[seed], delta_points[seed] = {}, {}
            for metric in METRICS:
                delta_points[seed][metric] = core._delta(points[ref][metric], points[candidate][metric])
                delta_draws[seed][metric] = [core._delta(left, right)
                    for left, right in zip(values[ref][metric], values[candidate][metric])]
            paired[name][f"seed{seed}"] = {
                metric: core._summary(delta_points[seed][metric], delta_draws[seed][metric]) for metric in METRICS}
        if len(seeds) == 2:
            mean[name] = {
                metric: core._summary(mean_or_none([delta_points[seed][metric] for seed in seeds]),
                    [mean_or_none([delta_draws[seed][metric][i] for seed in seeds]) for i in range(replicates)])
                for metric in METRICS}
    return {
        "inputs": {key: panel["inputs"] for key, panel in panels.items()},
        "alignment": {"identical_coordinates_truth_callable_hardN": True,
                      "tiles": int(first["margin"].shape[0]), "bp_per_tile": int(first["margin"].shape[1]),
                      "occupied_blocks": len(blocks), "block_bp": BLOCK_BP},
        "point_reproduction": {"all_metrics_within": 1e-6, "pass": True},
        "point_counts": counts, "absolute": absolute, "paired": paired,
        "two_seed_arithmetic_mean_effects": mean if len(seeds) == 2 else None,
    }


def run_assessment(directories: dict[int, dict[str, Path]], output: Path) -> dict:
    seeds = tuple(sorted(directories))
    if not seeds or not set(seeds) <= {42, 17} or any(set(row) != set(ARMS) for row in directories.values()):
        raise ValueError("provide one or both complete same-seed P0R/H0R/D directory groups")
    panels = {}
    for split in PANELS:
        loaded = {f"seed{seed}_{arm}": load_panel(directories[seed][arm], seed, arm, split)
                  for seed in seeds for arm in ARMS}
        panels[split] = assess_panel(loaded, seeds)
        del loaded
    result = {
        "experiment": EXPERIMENT_ID, "protocol": EXPERIMENT_ID, "seeds": list(seeds),
        "species": decision.WORM, "panels": panels,
        "scope": "reused internal worm SCREEN/DEV; conditional spatial uncertainty, not seed-population CI",
        "bootstrap": {"replicates": REPLICATES, "rng": "numpy default_rng", "seed": RNG_SEED,
            "block_bp": BLOCK_BP, "draws": "B occupied blocks with replacement; shared across all arms/seeds within each panel",
            "estimand": "pooled callable bp with sampled block multiplicities, not mean window metrics",
            "ap": "exact raw float32 tie-group weighted AP",
            "ci": "percentile 2.5/97.5; numpy quantile method=linear",
            "seed_resampling": False, "undefined_draw_policy": "retain undefined count; any undefined draw makes affected CI null"},
        "conf_status": decision.CONF_STATUS,
        "claim_boundary": {"ensemble": False, "ci_sign_gate": False, "release_authorized": False,
                           "external_success_claim": False, "conf_opening_authorized": False},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    for seed in (42, 17):
        for arm in ("p0r", "h0r", "d-anchor-j0"):
            parser.add_argument(f"--seed{seed}-{arm}-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main():
    args = build_parser().parse_args()
    directories = {}
    for seed in (42, 17):
        group = {arm: getattr(args, f"seed{seed}_{name}_dir")
                 for arm, name in (("P0R", "p0r"), ("H0R", "h0r"), ("D", "d_anchor_j0"))}
        if any(value is not None for value in group.values()):
            if any(value is None for value in group.values()):
                raise ValueError(f"seed{seed} requires all three registered directories")
            directories[seed] = group
    print(json.dumps(run_assessment(directories, args.output), indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
