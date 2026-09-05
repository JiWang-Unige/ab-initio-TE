#!/usr/bin/env python3
"""J0-A: apply frozen D anchors to worm SCREEN/DEV; no CAL fit or CONF access.

One seed per invocation. Existing compatible caches may be supplied with
--cache-root (SCREEN/c_elegans.npz and DEV/c_elegans.npz). Missing panels are
inferred once. Outputs: margins/{SCREEN,DEV}/c_elegans.npz and diagnostic.json.
The label-oracle summaries deliberately contain no threshold values.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903"))
import calibrate_evaluate_x0 as ev

SPECIES = "c_elegans"
PANELS = ("SCREEN", "DEV")
ANCHOR_JOBS = {42: "12307410_1", 17: "12361196_1"}
POINT_KEYS = ("bp_f1", "bp_precision", "bp_recall", "bp_average_precision")
CACHE_KEYS = ("margin", "truth", "callable", "hard_negative", "tile_id", "chrom", "start")


def exact_score_summary(margins, truth):
    """All and only realizable raw-score tie groups; never emit oracle cutoffs."""
    margins, truth = np.asarray(margins), np.asarray(truth, bool)
    if margins.ndim != 1 or truth.shape != margins.shape or not np.all(np.isfinite(margins)):
        raise ValueError("score inputs must be finite, aligned one-dimensional arrays")
    positives = int(truth.sum())
    if not truth.size or not positives:
        reason = "no_callable_bp" if not truth.size else "no_positive_bp"
        return {"tie_groups": 0, "constrained_max_f1": None, "constrained_reason": reason,
                "recall_at_precision_0_80": None, "recall_reason": reason}
    order = np.argsort(-margins, kind="stable")
    scores = margins[order]
    ends = np.flatnonzero(np.r_[scores[1:] != scores[:-1], True])
    tp = np.cumsum(truth[order], dtype=np.int64)[ends]
    predicted = ends + 1
    precision, recall = tp / predicted, tp / positives
    f1 = 2 * tp / (positives + predicted)
    eligible = (precision >= .75) & (recall >= .75)
    constrained = None
    if eligible.any():
        indices = np.flatnonzero(eligible)
        best = indices[np.argmax(f1[indices])]
        constrained = {"f1": float(f1[best]), "precision": float(precision[best]),
                       "recall": float(recall[best])}
    eligible_recall = precision >= .80
    return {"tie_groups": int(len(ends)), "constrained_max_f1": constrained,
            "constrained_reason": None if constrained else "no_threshold_with_precision_and_recall_ge_0_75",
            "recall_at_precision_0_80": float(recall[eligible_recall].max()) if eligible_recall.any() else None,
            "recall_reason": None if eligible_recall.any() else "no_threshold_with_precision_ge_0_80"}


def fn_partition(tiles, predictions):
    """Partition FN inside each tile's callable Label-A truth runs, exactly."""
    if len(tiles) != len(predictions):
        raise ValueError("one prediction array required for each tile")
    result = dict.fromkeys(("fn_bp", "complete_miss_bp", "internal_gap_bp", "terminal_missing_bp",
                            "truth_runs", "complete_miss_runs", "partially_hit_runs", "fully_hit_runs"), 0)
    for tile, prediction in zip(tiles, predictions):
        truth = np.asarray(tile["truth"], bool) & np.asarray(tile["callable"], bool)
        prediction = np.asarray(prediction, bool)
        if prediction.shape != truth.shape:
            raise ValueError("prediction/truth shape mismatch")
        result["fn_bp"] += int(np.sum(truth & ~prediction))
        for left, right in ev.runs_from_bool(truth):
            hit = np.flatnonzero(prediction[left:right])
            length = right - left
            result["truth_runs"] += 1
            if not hit.size:
                result["complete_miss_bp"] += length
                result["complete_miss_runs"] += 1
            elif hit.size == length:
                result["fully_hit_runs"] += 1
            else:
                result["partially_hit_runs"] += 1
                result["terminal_missing_bp"] += int(hit[0] + length - 1 - hit[-1])
                result["internal_gap_bp"] += int(hit[-1] - hit[0] + 1 - hit.size)
    total = sum(result[k] for k in ("complete_miss_bp", "internal_gap_bp", "terminal_missing_bp"))
    if total != result["fn_bp"]:
        raise ValueError("FN partition does not exhaust pooled FN bp")
    result["exhaustive"] = True
    result["boundary_interpretation"] = "Callable U breaks and tile edges are evaluation boundaries, not biological insertion ends."
    return result


def point_metrics(tiles, calibration):
    """Match frozen evaluator arithmetic, including float32 affine transform."""
    slope, intercept, threshold = (float(calibration[k]) for k in ("platt_slope", "platt_intercept", "threshold"))
    predictions = [(ev.sigmoid(slope * t["margin"] + intercept) >= threshold) & t["callable"] for t in tiles]
    tp = fp = fn = 0
    for tile, predicted in zip(tiles, predictions):
        truth, callable_mask = tile["truth"], tile["callable"]
        tp += int(np.sum(predicted & truth & callable_mask))
        fp += int(np.sum(predicted & ~truth & callable_mask))
        fn += int(np.sum(~predicted & truth & callable_mask))
    raw = np.concatenate([t["margin"][t["callable"]] for t in tiles])
    truth = np.concatenate([t["truth"][t["callable"]] for t in tiles])
    metrics = {"bp_tp": tp, "bp_fp": fp, "bp_fn": fn,
               "bp_f1": ev._f1(tp, fp, fn), "bp_precision": ev._ratio(tp, tp + fp),
               "bp_recall": ev._ratio(tp, tp + fn),
               "bp_average_precision": ev.average_precision_binary(truth, raw)}
    return metrics, predictions, raw, truth


def reproduce_metrics(observed, expected):
    deltas = {k: abs(float(observed[k]) - float(expected[k])) for k in POINT_KEYS}
    if any(not np.isfinite(d) or d > 1e-6 for d in deltas.values()):
        raise ValueError(f"Archived point metrics mismatch: {deltas}; repair inference/alignment, not science no-go")
    return {"status": "PASS", "absolute_tolerance": 1e-6, "absolute_differences": deltas}


def read_panel(path, split):
    # Read only the two explicitly named development panels; check before inference.
    if any(part.upper() == "CONF" for part in path.parts):
        raise ValueError("Historical CONF is forbidden for J0-A")
    records = ev.read_jsonl(path)
    if not records or any(r["split"] != split or r["species_code"] != SPECIES for r in records):
        raise ValueError(f"Expected only worm {split} records")
    seen = set()
    for r in records:
        key = (str(r["tile_id"]), int(r["half"]))
        if key in seen or key[1] not in (0, 1) or len(r["sequence"]) != 4096 or len(r["labels"]) != 4096:
            raise ValueError("Expected unique, complete 4096-bp tile halves")
        seen.add(key)
    if any((tile_id, 1 - half) not in seen for tile_id, half in seen):
        raise ValueError("Missing tile half")
    return records


def tiles_from_cache(path, records):
    # Directly compare coordinate/label alignment; no fingerprints or lossy margins.
    expected = ev.assemble_tiles(SPECIES, records, [np.zeros(4096, np.float32) for _ in records])
    with np.load(path, allow_pickle=False) as data:
        cache = {k: data[k] for k in CACHE_KEYS}
    if cache["margin"].dtype != np.float32 or cache["margin"].shape != (len(expected), 8192):
        raise ValueError("Compatible cache must preserve float32 8192-bp margins")
    if not np.all(np.isfinite(cache["margin"])):
        raise ValueError("Cache margins are not finite")
    for key in CACHE_KEYS[1:]:
        wanted = np.array([t[key] for t in expected])
        if not np.array_equal(cache[key], wanted):
            raise ValueError(f"Cache/panel alignment mismatch: {key}")
    for tile, margin in zip(expected, cache["margin"]):
        tile["margin"] = margin
    return expected


def save_cache(path, tiles):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **{k: np.array([t[k] for t in tiles], dtype=np.float32 if k == "margin" else None) for k in CACHE_KEYS})


def validate_sources(args, calibration, expected, split):
    if ANCHOR_JOBS[args.seed] not in args.model_dir.parts:
        raise ValueError("J0-A accepts only the registered same-seed D anchor, never B0")
    for key, path in (("model_dir", args.model_dir), ("tokenizer_dir", args.tokenizer_dir or args.model_dir),
                      ("model_code_dir", args.model_code_dir)):
        if calibration[key] != (str(path.resolve()) if path else None):
            raise ValueError(f"Frozen calibration {key} differs from requested source")
    if int(calibration["seed"]) != args.seed or int(expected["seed"]) != args.seed:
        raise ValueError("Frozen calibration/metrics seed mismatch")
    if any(artifact["arm"] != "D" or artifact["calibration_scope"] != "six-species-shared"
           for artifact in (calibration, expected)):
        raise ValueError("J0-A requires D with frozen six-species-shared calibration")
    if calibration["fit_split"] != "CAL" or set(calibration["species"]) != set(ev.CAL_SPECIES):
        raise ValueError("Frozen calibration must be the existing six-species CAL fit")
    if Path(expected["model_dir"]).resolve() != args.model_dir.resolve():
        raise ValueError("Archived metrics belong to another model")
    if Path(expected["calibration_json"]).resolve() != args.calibration_json.resolve():
        raise ValueError("Archived metrics use another calibration artifact")
    if expected["split"] != split:
        raise ValueError("Archived metrics split mismatch")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=sorted(ANCHOR_JOBS), required=True)
    for name in ("model-dir", "calibration-json", "screen-data", "dev-data", "screen-expected", "dev-expected", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("tokenizer-dir", "model-code-dir", "cache-root"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--batch-size", type=int, default=12)
    return parser


def main():
    args = build_parser().parse_args()
    calibration = json.loads(args.calibration_json.read_text())
    inputs = {}
    for split in PANELS:
        path = getattr(args, split.lower() + "_data")
        expected_path = getattr(args, split.lower() + "_expected")
        expected = json.loads(expected_path.read_text())
        validate_sources(args, calibration, expected, split)
        inputs[split] = (path, read_panel(path, split), expected_path, expected)
    model = tokenizer = device = None
    panels = {}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for split, (path, records, expected_path, expected) in inputs.items():
        cache = args.cache_root / split / f"{SPECIES}.npz" if args.cache_root else None
        if cache is not None and cache.exists():
            tiles = tiles_from_cache(cache, records)
            source = "existing_compatible_cache"
        else:
            if model is None:
                model, tokenizer, device = ev.load_final_model(args.model_dir, args.tokenizer_dir, False, args.model_code_dir)
                if device.type != "cuda":
                    raise RuntimeError("Missing cache inference requires allocated CUDA GPU")
            margins = ev.infer_half_margins(model, tokenizer, device, [r["sequence"] for r in records], args.batch_size)
            tiles = ev.assemble_tiles(SPECIES, records, margins)
            source = "single_apply_only_inference"
        save_cache(args.output_dir / "margins" / split / f"{SPECIES}.npz", tiles)
        observed, predictions, raw, truth = point_metrics(tiles, calibration)
        reproduction = reproduce_metrics(observed, expected["per_species"][SPECIES])
        # Diagnostics are only computed after archived metrics have reproduced.
        oracle = exact_score_summary(raw, truth)
        best = oracle["constrained_max_f1"]
        oracle["scalar_threshold_goal_unreachable"] = best is None or best["f1"] < .8
        oracle["oracle_minus_deployed_f1"] = None if best is None else best["f1"] - observed["bp_f1"]
        oracle["substantial_score_alignment_headroom"] = best is not None and best["f1"] - observed["bp_f1"] >= .02
        oracle["interpretation"] = (
            "scalar_threshold_cannot_meet_panel_goal" if oracle["scalar_threshold_goal_unreachable"] else
            "substantial_score_alignment_headroom" if oracle["substantial_score_alignment_headroom"] else "mixed_limitations")
        partition = fn_partition(tiles, predictions)
        if partition["fn_bp"] != observed["bp_fn"]:
            raise ValueError("FN partition differs from reproduced pooled point FN")
        panels[split] = {"panel_path": str(path), "expected_metrics_path": str(expected_path),
                         "cache_source": source, "reused_cache_path": str(cache) if source.startswith("existing") else None,
                         "point_metrics": observed, "reproduction": reproduction,
                         "label_oracle": oracle, "fn_partition": partition}
        print(f"seed{args.seed} {split}: archived point metrics reproduced; J0-A complete", flush=True)
    ev.write_json(args.output_dir / "diagnostic.json", {
        "protocol": "CROSS-SPECIES-L1-INIT-HISTORY-V1", "stage": "J0-A", "seed": args.seed,
        "model_dir": str(args.model_dir), "calibration_json": str(args.calibration_json),
        "mode": "apply-only", "status": "COMPLETED", "panels": panels,
        "scope": "D-anchor worm SCREEN/DEV only; label-oracle diagnosis, not a deployment threshold or training release"})


if __name__ == "__main__":
    main()
