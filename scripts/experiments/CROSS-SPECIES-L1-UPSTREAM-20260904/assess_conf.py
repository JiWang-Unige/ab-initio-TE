#!/usr/bin/env python3
"""Assess the registered paired spatial uncertainty for the D2 CONF panel.

The four CONF caches contain the same tiles and labels for seed-42/17 L/D.
This consumer resamples occupied 512-kb coordinate blocks with the same draws
for all four models, then pools callable bases with the sampled block weights.
It does not fit a calibration, resample seeds, or make a release decision.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


EXPERIMENT_ID = "CROSS-SPECIES-L1-UPSTREAM-20260904"
PROTOCOL = f"{EXPERIMENT_ID}-V1"
BLOCK_BP = 524_288
BOOTSTRAP_REPLICATES = 1_000
BOOTSTRAP_SEED = 2_026_0905
METRICS = ("bp_average_precision", "bp_f1", "bp_precision", "bp_recall")
TOPOLOGY_DROP = 0.05
GEOMETRY_MULTIPLIER = 1.25
MISSED_RATE_INCREASE = 0.03
TARGET_F1 = 0.80
TARGET_PR = 0.75


def _finite(value: object, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _load_calibration(metrics_path: Path, metadata: dict) -> tuple[Path, dict[str, float]]:
    calibration_path = Path(metadata["calibration_json"])
    calibration = json.loads(calibration_path.read_text())
    values = {
        key: _finite(calibration[key], f"{calibration_path.name}.{key}")
        for key in ("platt_slope", "platt_intercept", "threshold")
    }
    return calibration_path, values


def load_conf_panel(directory: Path, expected_seed: int, expected_arm: str) -> dict:
    """Load one CONF metrics/cache pair and retain its raw float32 margins."""

    directory = Path(directory)
    metrics_path = directory / "conf_metrics.json"
    margins_path = directory / "CONF_margins.npz"
    metadata = json.loads(metrics_path.read_text())
    calibration_path, calibration = _load_calibration(metrics_path, metadata)

    if metadata["seed"] != expected_seed:
        raise ValueError(f"{directory}: seed metadata mismatch")
    if metadata["arm"] != expected_arm:
        raise ValueError(f"{directory}: arm metadata mismatch")
    if metadata["split"] != "CONF":
        raise ValueError(f"{directory}: expected CONF metrics")

    with np.load(margins_path, allow_pickle=False) as archive:
        required = ("margin", "truth", "callable", "hard_negative", "tile_id", "chrom", "start")
        missing = [key for key in required if key not in archive]
        if missing:
            raise ValueError(f"{margins_path}: missing {missing}")
        margin = np.asarray(archive["margin"])
        if margin.dtype != np.float32:
            raise ValueError(f"{margins_path}: margin must be float32, got {margin.dtype}")
        if margin.shape != (256, 8192):
            raise ValueError(f"{margins_path}: expected frozen 256x8192 CONF cache")
        tiles = margin.shape[0]
        arrays = {
            "margin": margin,
            "truth": archive["truth"].astype(bool),
            "callable": archive["callable"].astype(bool),
            "hard_negative": archive["hard_negative"].astype(bool),
        }
        if any(value.shape != margin.shape for value in arrays.values()):
            raise ValueError(f"{margins_path}: base-array shapes are not identical")
        if not np.all(np.isfinite(margin)):
            raise ValueError(f"{margins_path}: margin contains non-finite values")
        tile_id = archive["tile_id"].tolist()
        chrom = archive["chrom"].tolist()
        start = np.asarray(archive["start"], dtype=np.int64).reshape(-1)
        if len(tile_id) != tiles or len(chrom) != tiles or len(start) != tiles:
            raise ValueError(f"{margins_path}: tile metadata does not match margin rows")

    order = np.lexsort((np.asarray(tile_id), start, np.asarray(chrom)))
    arrays = {key: value[order] for key, value in arrays.items()}
    tile_id = [tile_id[index] for index in order]
    chrom = [chrom[index] for index in order]
    start = start[order]
    return {
        "directory": directory.resolve(),
        "metrics_path": metrics_path.resolve(),
        "margins_path": margins_path.resolve(),
        "metadata": metadata,
        "calibration_path": calibration_path.resolve(),
        "calibration": calibration,
        "margin": arrays["margin"],
        "truth": arrays["truth"],
        "callable": arrays["callable"],
        "hard_negative": arrays["hard_negative"],
        "tile_id": tile_id,
        "chrom": chrom,
        "start": start,
    }


def align_panels(panels: dict[str, dict]) -> None:
    """Require the four models to use identical sorted coordinates and masks."""

    first = next(iter(panels.values()))
    for name, panel in panels.items():
        if panel["tile_id"] != first["tile_id"] or panel["chrom"] != first["chrom"]:
            raise ValueError(f"{name}: CONF coordinates differ")
        if not np.array_equal(panel["start"], first["start"]):
            raise ValueError(f"{name}: CONF starts differ")
        for key in ("truth", "callable", "hard_negative"):
            if not np.array_equal(panel[key], first[key]):
                raise ValueError(f"{name}: CONF {key} arrays differ")
        if panel["margin"].shape != first["margin"].shape:
            raise ValueError(f"{name}: CONF margin shape differs")


def occupied_blocks(chrom: list[str], start: np.ndarray) -> list[np.ndarray]:
    by_block: dict[tuple[str, int], list[int]] = defaultdict(list)
    for index, (name, coordinate) in enumerate(zip(chrom, start)):
        by_block[(name, int(coordinate) // BLOCK_BP)].append(index)
    return [np.asarray(by_block[key], dtype=np.int64) for key in sorted(by_block)]


def average_precision_tied(
    truth: np.ndarray,
    scores: np.ndarray,
    weights: np.ndarray | None = None,
    order: np.ndarray | None = None,
    tie_ends: np.ndarray | None = None,
) -> float | None:
    """Compute exact weighted AP with descending, grouped raw-score ties."""

    truth = np.asarray(truth, dtype=bool)
    scores = np.asarray(scores, dtype=np.float32)
    if truth.ndim != 1 or scores.ndim != 1 or truth.shape != scores.shape:
        raise ValueError("AP inputs must be one-dimensional arrays of equal length")
    if not np.all(np.isfinite(scores)):
        raise ValueError("AP scores must be finite")
    if weights is None:
        weights = np.ones(truth.size, dtype=np.float64)
    else:
        weights = np.asarray(weights, dtype=np.float64)
        if weights.shape != truth.shape or np.any(weights < 0) or not np.all(np.isfinite(weights)):
            raise ValueError("AP weights must be finite and nonnegative")
    if float(np.sum(weights)) == 0.0:
        return None
    positive = truth & (weights > 0)
    positive_weight = float(np.sum(weights[positive]))
    if positive_weight == 0.0:
        return None

    if order is None:
        order = np.argsort(-scores, kind="mergesort")
    ordered_scores = scores[order]
    if tie_ends is None:
        tie_ends = np.flatnonzero(np.r_[ordered_scores[1:] != ordered_scores[:-1], True])
    starts = np.r_[0, tie_ends[:-1] + 1]
    ordered_weight = weights[order]
    ordered_positive = ordered_weight * truth[order]
    cumulative_positive = np.cumsum(ordered_positive)
    cumulative_count = np.cumsum(ordered_weight)
    group_positive = np.add.reduceat(ordered_positive, starts)
    precision = np.divide(
        cumulative_positive[tie_ends],
        cumulative_count[tie_ends],
        out=np.zeros_like(cumulative_positive[tie_ends], dtype=np.float64),
        where=cumulative_count[tie_ends] != 0,
    )
    return float(np.sum(precision * group_positive) / positive_weight)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    result = np.empty_like(values)
    positive = values >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exponential = np.exp(values[~positive])
    result[~positive] = exponential / (1.0 + exponential)
    return result


def _metric_values(
    margin: np.ndarray,
    truth: np.ndarray,
    callable_mask: np.ndarray,
    slope: float,
    intercept: float,
    threshold: float,
    weights: np.ndarray | None = None,
    ap_order: np.ndarray | None = None,
    ap_tie_ends: np.ndarray | None = None,
) -> tuple[dict[str, float | None], dict[str, int]]:
    margin = np.asarray(margin, dtype=np.float32).reshape(-1)
    truth = np.asarray(truth, dtype=bool).reshape(-1)
    callable_mask = np.asarray(callable_mask, dtype=bool).reshape(-1)
    if margin.shape != truth.shape or margin.shape != callable_mask.shape:
        raise ValueError("metric arrays must have equal shapes")
    if weights is None:
        weights = np.ones(margin.size, dtype=np.float64)
    else:
        weights = np.asarray(weights, dtype=np.float64).reshape(-1)
        if weights.shape != margin.shape:
            raise ValueError("metric weights have the wrong shape")
    selected = callable_mask
    selected_margin = margin[selected]
    selected_truth = truth[selected]
    selected_weights = weights[selected]
    probability = _sigmoid(slope * selected_margin + intercept)
    predicted = probability >= threshold
    tp = float(np.sum(selected_weights[predicted & selected_truth]))
    fp = float(np.sum(selected_weights[predicted & ~selected_truth]))
    fn = float(np.sum(selected_weights[~predicted & selected_truth]))
    precision = None if tp + fp == 0 else tp / (tp + fp)
    recall = None if tp + fn == 0 else tp / (tp + fn)
    denominator = 2 * tp + fp + fn
    f1 = None if denominator == 0 else 2 * tp / denominator
    if ap_order is not None:
        # The cached order is over the callable arrays, not the full tile grid.
        ap = average_precision_tied(
            selected_truth,
            selected_margin,
            selected_weights,
            order=ap_order,
            tie_ends=ap_tie_ends,
        )
    else:
        ap = average_precision_tied(selected_truth, selected_margin, selected_weights)
    return (
        {
            "bp_average_precision": ap,
            "bp_f1": f1,
            "bp_precision": precision,
            "bp_recall": recall,
        },
        {"tp_bp": int(tp), "fp_bp": int(fp), "fn_bp": int(fn), "positive_bp": int(np.sum(selected_weights[selected_truth]))},
    )


def _prepared_arm(panel: dict) -> dict:
    margin = panel["margin"].reshape(-1)
    truth = panel["truth"].reshape(-1)
    callable_mask = panel["callable"].reshape(-1)
    selected_margin = margin[callable_mask]
    order = np.argsort(-selected_margin, kind="mergesort")
    ends = np.flatnonzero(np.r_[selected_margin[order][1:] != selected_margin[order][:-1], True])
    calibration = panel["calibration"]
    return {
        "margin": margin,
        "truth": truth,
        "callable": callable_mask,
        "slope": calibration["platt_slope"],
        "intercept": calibration["platt_intercept"],
        "threshold": calibration["threshold"],
        "ap_order": order,
        "ap_tie_ends": ends,
        "tiles": panel["margin"].shape[0],
        "bp_per_tile": panel["margin"].shape[1],
    }


def _summary(point: float | None, values: list[float | None]) -> dict:
    undefined = sum(value is None for value in values)
    interval = None
    if undefined == 0:
        numeric = np.asarray(values, dtype=np.float64)
        interval = [
            float(np.quantile(numeric, 0.025, method="linear")),
            float(np.quantile(numeric, 0.975, method="linear")),
        ]
    return {
        "point": point,
        "ci95": interval,
        "valid_replicates": len(values) - undefined,
        "undefined_replicates": undefined,
    }


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return right - left


def _point_row(metadata: dict) -> dict:
    return metadata["per_species"]["c_elegans"]


def _check_point_reproduction(panel: dict, point: dict[str, float | None]) -> None:
    authoritative = _point_row(panel["metadata"])
    for key in METRICS:
        if key not in authoritative:
            raise ValueError(f"{panel['metrics_path']}: missing authoritative {key}")
        expected = _finite(authoritative[key], f"authoritative {key}")
        observed = point[key]
        if observed is None or abs(observed - expected) > 1e-6:
            raise ValueError(
                f"{panel['metrics_path']}: {key} differs from cache by "
                f"{None if observed is None else observed - expected}"
            )


def _topology_row(metadata: dict) -> dict:
    row = _point_row(metadata)
    required = ("segment_f1_iou_0_8", "boundary_f1_5bp", "fragments_per_truth", "split_rate", "missed_rate")
    for key in required:
        if key not in row:
            raise ValueError(f"CONF metrics missing topology field {key}")
    return row


def _conf_decisions(metrics_by_key: dict[str, dict]) -> dict:
    decisions = {}
    for seed in (42, 17):
        left = _topology_row(metrics_by_key[f"seed{seed}_L"])
        right = _topology_row(metrics_by_key[f"seed{seed}_D"])
        left_ap = _finite(left["bp_average_precision"], f"seed{seed} L AP")
        right_ap = _finite(right["bp_average_precision"], f"seed{seed} D AP")
        left_f1 = _finite(left["bp_f1"], f"seed{seed} L F1")
        right_f1 = _finite(right["bp_f1"], f"seed{seed} D F1")
        direction = {
            "delta_bp_average_precision": right_ap - left_ap,
            "delta_bp_f1": right_f1 - left_f1,
            "pass": right_ap > left_ap and right_f1 > left_f1,
            "criterion": "positive point direction only; no CI-sign gate",
        }
        segment_delta = _finite(right["segment_f1_iou_0_8"], f"seed{seed} D segment") - _finite(left["segment_f1_iou_0_8"], f"seed{seed} L segment")
        boundary_delta = _finite(right["boundary_f1_5bp"], f"seed{seed} D boundary") - _finite(left["boundary_f1_5bp"], f"seed{seed} L boundary")
        left_fragments = _finite(left["fragments_per_truth"], f"seed{seed} L fragments")
        right_fragments = _finite(right["fragments_per_truth"], f"seed{seed} D fragments")
        left_split = _finite(left["split_rate"], f"seed{seed} L split")
        right_split = _finite(right["split_rate"], f"seed{seed} D split")
        missed_delta = _finite(right["missed_rate"], f"seed{seed} D missed") - _finite(left["missed_rate"], f"seed{seed} L missed")
        topology = {
            "segment_f1_iou_0_8_delta": segment_delta,
            "boundary_f1_5bp_delta": boundary_delta,
            "fragments_per_truth_L": left_fragments,
            "fragments_per_truth_D": right_fragments,
            "split_rate_L": left_split,
            "split_rate_D": right_split,
            "missed_rate_delta": missed_delta,
            "pass_segment_f1_iou_0_8": segment_delta >= -TOPOLOGY_DROP,
            "pass_boundary_f1_5bp": boundary_delta >= -TOPOLOGY_DROP,
            "pass_fragments_per_truth": right_fragments <= GEOMETRY_MULTIPLIER * left_fragments,
            "pass_split_rate": right_split <= GEOMETRY_MULTIPLIER * left_split,
            "pass_missed_rate": missed_delta <= MISSED_RATE_INCREASE,
        }
        topology["pass"] = all(value for key, value in topology.items() if key.startswith("pass_"))
        d_targets = {
            "bp_f1": _finite(right["bp_f1"], f"seed{seed} D F1") >= TARGET_F1,
            "bp_precision": _finite(right["bp_precision"], f"seed{seed} D precision") >= TARGET_PR,
            "bp_recall": _finite(right["bp_recall"], f"seed{seed} D recall") >= TARGET_PR,
        }
        d_targets["pass"] = all(d_targets.values())
        decisions[str(seed)] = {
            "direction": direction,
            "original_topology_guards": topology,
            "d_conf_absolute_targets": d_targets,
        }
    return decisions


def run_conf(
    directories: dict[str, Path],
    output: Path,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    panels = {
        key: load_conf_panel(path, int(key[4:6]), key[-1])
        for key, path in directories.items()
    }
    if set(panels) != {"seed42_L", "seed42_D", "seed17_L", "seed17_D"}:
        raise ValueError("four CONF inputs must be seed42/17 L/D")
    align_panels(panels)
    reference = next(iter(panels.values()))
    blocks = occupied_blocks(reference["chrom"], reference["start"])
    if not blocks:
        raise ValueError("CONF cache has no occupied spatial blocks")

    prepared = {key: _prepared_arm(panel) for key, panel in panels.items()}
    points = {}
    counts = {}
    for key, arm in prepared.items():
        points[key], counts[key] = _metric_values(
            arm["margin"],
            arm["truth"],
            arm["callable"],
            arm["slope"],
            arm["intercept"],
            arm["threshold"],
            ap_order=arm["ap_order"],
            ap_tie_ends=arm["ap_tie_ends"],
        )
        _check_point_reproduction(panels[key], points[key])

    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(blocks), size=(replicates, len(blocks)))
    values = {key: {metric: [] for metric in METRICS} for key in prepared}
    paired_values = {
        f"seed{model_seed}": {metric: [] for metric in ("bp_average_precision", "bp_f1")}
        for model_seed in (42, 17)
    }
    mean_values = {metric: [] for metric in ("bp_average_precision", "bp_f1")}
    for draw in draws:
        block_multiplicity = np.bincount(draw, minlength=len(blocks))
        tile_weights = np.zeros(reference["margin"].shape[0], dtype=np.float64)
        for block_index, multiplicity in enumerate(block_multiplicity):
            if multiplicity:
                tile_weights[blocks[block_index]] = multiplicity
        per_draw = {}
        for key, arm in prepared.items():
            weight_grid = np.repeat(tile_weights, arm["bp_per_tile"])
            per_draw[key], _ = _metric_values(
                arm["margin"],
                arm["truth"],
                arm["callable"],
                arm["slope"],
                arm["intercept"],
                arm["threshold"],
                weights=weight_grid,
                ap_order=arm["ap_order"],
                ap_tie_ends=arm["ap_tie_ends"],
            )
            for metric in METRICS:
                values[key][metric].append(per_draw[key][metric])
        for model_seed in (42, 17):
            left = per_draw[f"seed{model_seed}_L"]
            right = per_draw[f"seed{model_seed}_D"]
            for metric in ("bp_average_precision", "bp_f1"):
                paired_values[f"seed{model_seed}"][metric].append(_delta(left[metric], right[metric]))
        for metric in ("bp_average_precision", "bp_f1"):
            deltas = [paired_values[f"seed{model_seed}"][metric][-1] for model_seed in (42, 17)]
            mean_values[metric].append(None if any(delta is None for delta in deltas) else float(np.mean(deltas)))

    absolute = {}
    for key in prepared:
        absolute[key] = {
            metric: _summary(points[key][metric], values[key][metric]) for metric in METRICS
        }
    paired = {
        f"seed{model_seed}": {
            metric: _summary(
                _delta(points[f"seed{model_seed}_L"][metric], points[f"seed{model_seed}_D"][metric]),
                paired_values[f"seed{model_seed}"][metric],
            )
            for metric in ("bp_average_precision", "bp_f1")
        }
        for model_seed in (42, 17)
    }
    mean_point = {
        metric: float(np.mean([paired[f"seed{model_seed}"][metric]["point"] for model_seed in (42, 17)]))
        for metric in ("bp_average_precision", "bp_f1")
    }
    result = {
        "experiment": EXPERIMENT_ID,
        "protocol": PROTOCOL,
        "scope": "prospective internal CONF; conditional spatial uncertainty",
        "inputs": {
            key: {
                "directory": str(panels[key]["directory"]),
                "conf_metrics": str(panels[key]["metrics_path"]),
                "margins": str(panels[key]["margins_path"]),
                "calibration_json": str(panels[key]["calibration_path"]),
                "calibration": panels[key]["calibration"],
            }
            for key in sorted(panels)
        },
        "alignment": {
            "identical_sorted_coordinates_truth_callable_hard_negative": True,
            "tiles": int(reference["margin"].shape[0]),
            "bp_per_tile": int(reference["margin"].shape[1]),
            "occupied_blocks": len(blocks),
            "block_bp": BLOCK_BP,
        },
        "bootstrap": {
            "replicates": int(replicates),
            "seed": int(seed),
            "draws": "occupied blocks, B draws with replacement; same draws for all four models",
            "estimand": "pooled callable bp with sampled block multiplicities",
            "ap": "raw float32 margins, descending stable sort and exact tie-group cumulative counts",
            "ci": "percentile 2.5/97.5, numpy quantile method=linear",
            "seed_resampling": False,
            "undefined_draw_policy": "record undefined; no redraw or silent omission; affected CI is null",
        },
        "point_counts": counts,
        "absolute": absolute,
        "paired_d_minus_l": paired,
        "two_seed_arithmetic_mean_delta_d_minus_l": {
            metric: _summary(mean_point[metric], mean_values[metric]) for metric in ("bp_average_precision", "bp_f1")
        },
        "decisions": _conf_decisions({key: panels[key]["metadata"] for key in panels}),
        "claim_boundary": {
            "release_claim": False,
            "ensemble": False,
            "unseen_species_or_genome_claim": False,
            "ci_sign_gate": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("seed42-l-dir", "seed42-d-dir", "seed17-l-dir", "seed17-d-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    directories = {
        "seed42_L": args.seed42_l_dir,
        "seed42_D": args.seed42_d_dir,
        "seed17_L": args.seed17_l_dir,
        "seed17_D": args.seed17_d_dir,
    }
    print(json.dumps(run_conf(directories, args.output), indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
