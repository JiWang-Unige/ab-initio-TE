#!/usr/bin/env python3
"""Frozen seed42 B0/B1 train gap and CAL-scope diagnostic; no weight updates."""

import argparse
import gc
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903"))
import calibrate_evaluate_x0 as ev


def score(tiles, calibration):
    return ev.evaluate_species_tiles(tiles, calibration["platt_slope"], calibration["platt_intercept"], calibration["threshold"])


def ranking_diagnostics(margins, truth, prevalence):
    order = np.argsort(-margins, kind="stable")
    y, scores = truth[order], margins[order]
    ends = np.flatnonzero(np.r_[scores[1:] != scores[:-1], True])
    tp = np.cumsum(y)[ends]
    fp = ends + 1 - tp
    positive, negative = truth.sum(), len(truth) - truth.sum()
    recall = tp / positive
    precision = np.divide(prevalence * recall, prevalence * recall + (1 - prevalence) * fp / negative)
    return {
        "ap_at_cal_prevalence": float(np.sum(precision * np.diff(np.r_[0, recall]))),
        "label_oracle_threshold_f1": float(np.max(2 * tp / (positive + tp + fp))),
        "pooled_unweighted_bp_nll": float(np.mean(np.logaddexp(0, margins) - truth * margins)),
    }


def cache_tiles(path, tiles):
    np.savez_compressed(path, margin=np.stack([t["margin"] for t in tiles]).astype(np.float32),
                        truth=np.stack([t["truth"] for t in tiles]), callable=np.stack([t["callable"] for t in tiles]),
                        hard_negative=np.stack([t["hard_negative"] for t in tiles]),
                        tile_id=np.array([t["tile_id"] for t in tiles]), chrom=np.array([t["chrom"] for t in tiles]),
                        start=np.array([t["start"] for t in tiles]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    args.output_dir.mkdir(parents=True, exist_ok=False)
    data = root / "outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202"
    evidence = root / "outputs/CROSS-SPECIES-L1-B0-C-ELEGANS-EVAL-20260903/seed42/12261866_1"
    paths = {
        "B0": (root / "outputs/CROSS-SPECIES-L1-B0-C-ELEGANS-20260903/seed42/12261865_1/final_model", evidence / "specialist_calibration.json", evidence / "specialist_dev_metrics.json"),
        "B1": (root / "outputs/CROSS-SPECIES-L1-SEED42-FROZEN-20260903/B1/12177426_1/final_model", root / "outputs/CROSS-SPECIES-L1-EVAL-20260903/B1/12178443_1/calibration.json", evidence / "shared_dev_metrics.json"),
    }
    code = root / ".backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
    result = {"role": "retrospective_diagnostic", "seed": 42, "arms": {}}
    for arm, (model_path, calibration_path, previous_path) in paths.items():
        model, tokenizer, device = ev.load_final_model(model_path, model_path, False, code)
        if device.type != "cuda":
            raise RuntimeError("GPU diagnostic has no allocated CUDA device")
        frozen = json.loads(calibration_path.read_text())
        panels = {}
        for split in ("TRAIN", "CAL", "DEV", "SCREEN"):
            source = args.upstream_root if split == "SCREEN" else data
            panels[split] = ev.infer_inputs(model, tokenizer, device, [("c_elegans", source / split / "c_elegans.jsonl.gz")], 12)["c_elegans"]
            if {t["split"] for t in panels[split]} != {split}:
                raise ValueError("diagnostic input split mismatch")
            print(f"{arm} {split} inference complete", flush=True)
            cache_tiles(args.output_dir / f"{arm}_{split}_margins.npz", panels[split])
        metrics = {split: score(tiles, frozen) for split, tiles in panels.items()}
        previous = json.loads(previous_path.read_text())["per_species"]["c_elegans"]
        differences = {key: metrics["DEV"][key] - value for key, value in previous.items()}
        if max(abs(x) for x in differences.values()) > 1e-6:
            raise ValueError(f"{arm} frozen DEV metrics failed reproduction: {differences}")
        row = {"model": str(model_path), "calibration": str(calibration_path), "frozen_scope_metrics": metrics, "reproduction_deltas": differences}
        raw_cal = ev.callable_arrays({"c_elegans": panels["CAL"]})["c_elegans"]
        prevalence = float(raw_cal[1].mean())
        row["reference_prevalence"] = prevalence
        row["ranking"] = {split: ranking_diagnostics(*ev.callable_arrays({"c_elegans": tiles})["c_elegans"], prevalence) for split, tiles in panels.items()}
        if arm == "B1":
            ev.require_cal_split({"c_elegans": panels["CAL"]})
            raw = ev.callable_arrays({"c_elegans": panels["CAL"]})
            slope, intercept, loss = ev.fit_platt(raw)
            selection = ev.select_global_threshold({s: (ev.sigmoid(slope * m + intercept), y) for s, (m, y) in raw.items()})
            calibration = {"platt_slope": slope, "platt_intercept": intercept, "threshold": selection["threshold"], "fit_split": "CAL", "scope": "diagnostic_worm_only", "calibration_loss": loss}
            row["worm_calibration"] = calibration
            row["worm_scope_metrics"] = {split: score(tiles, calibration) for split, tiles in panels.items()}
        block_metrics = {}
        for split in ("CAL", "DEV"):
            blocks = defaultdict(list)
            for tile in panels[split]:
                blocks[f'{tile["chrom"]}:{tile["start"] // 524288}'].append(tile)
            block_metrics[split] = {block: score(tiles, frozen) for block, tiles in sorted(blocks.items())}
        row["spatial_blocks_512kb"] = block_metrics
        row["train_minus_cal"] = {metric: metrics["TRAIN"][metric] - metrics["CAL"][metric] for metric in ("bp_f1", "bp_average_precision")}
        result["arms"][arm] = row
        ev.write_json(args.output_dir / "diagnostic.json", result)
        del model, tokenizer, panels
        gc.collect()
        import torch
        torch.cuda.empty_cache()
    ranking = result["arms"]["B0"]["ranking"]
    train_ap = ranking["TRAIN"]["ap_at_cal_prevalence"]
    train_f1 = ranking["TRAIN"]["label_oracle_threshold_f1"]
    result["branch"] = (
        "CHECK_ENGINEERING_THEN_INITIALIZATION_PAIR" if train_ap < .90 and train_f1 < .90
        else "COVERAGE_PAIR_HIGH_TRAIN_GAP" if train_ap >= .95 and all(train_ap - ranking[s]["ap_at_cal_prevalence"] >= .05 for s in ("CAL", "SCREEN"))
        else "COVERAGE_PAIR_HYPOTHESIS_UNRESOLVED"
    )
    result["additional_b1_calibration_seeds"] = {}
    for index, seed in enumerate((17, 20260903)):
        model_path = root / f"outputs/CROSS-SPECIES-L1-B1-CONFIRMATION-20260903/seed{seed}/12181383_{index}/final_model"
        model, tokenizer, device = ev.load_final_model(model_path, model_path, False, code)
        panels = {split: ev.infer_inputs(model, tokenizer, device, [("c_elegans", data / split / "c_elegans.jsonl.gz")], 12)["c_elegans"] for split in ("CAL", "DEV")}
        for split, tiles in panels.items():
            cache_tiles(args.output_dir / f"B1_seed{seed}_{split}_margins.npz", tiles)
        raw = ev.callable_arrays({"c_elegans": panels["CAL"]})
        slope, intercept, loss = ev.fit_platt(raw)
        selection = ev.select_global_threshold({s: (ev.sigmoid(slope * m + intercept), y) for s, (m, y) in raw.items()})
        cal = {"platt_slope": slope, "platt_intercept": intercept, "threshold": selection["threshold"], "fit_split": "CAL", "scope": "diagnostic_worm_only"}
        global_cal = json.loads((root / f"outputs/CROSS-SPECIES-L1-EVAL-20260903/B1/seed{seed}/12181384_{index}/calibration.json").read_text())
        global_metrics = score(panels["DEV"], global_cal)
        old_index = 0 if seed == 17 else 2
        prior = json.loads((evidence.parents[1] / f"seed{seed}/12261866_{old_index}/shared_dev_metrics.json").read_text())["per_species"]["c_elegans"]
        if max(abs(global_metrics[k] - v) for k, v in prior.items()) > 1e-6:
            raise ValueError(f"seed{seed} B1 DEV failed reproduction")
        result["additional_b1_calibration_seeds"][str(seed)] = {"worm_calibration": cal, "global_dev": global_metrics, "worm_dev": score(panels["DEV"], cal)}
        del model, tokenizer, panels
        gc.collect()
        torch.cuda.empty_cache()
    ev.write_json(args.output_dir / "diagnostic.json", result)


if __name__ == "__main__":
    main()
