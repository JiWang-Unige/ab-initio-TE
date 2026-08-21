#!/usr/bin/env python3
"""Calibrated deployable anchor-selector diagnostics.

This does not claim deployment readiness. It asks whether genome-derived
features are good enough to guide new-species anchor trust: anchor choice,
risk tiers, regret, and uncertainty coverage under leave-species/clade splits.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score


BASE_FEATURES = [
    "log_distance_mya",
    "target_gc",
    "same_group_anchor",
    "target_insect",
    "target_other",
    "target_plant",
    "target_vertebrate",
    "anchor_animal",
    "anchor_cross",
    "anchor_human_h0_ntv2_250m",
    "anchor_human_h0_ntv2_500m",
    "anchor_human_h0_ntv3_100m",
    "anchor_insect",
    "anchor_other_anchor",
    "anchor_plant",
]


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def feature_matrix(pair: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    cats = pd.get_dummies(pair[["species_group", "anchor_type"]], prefix=["target", "anchor"], dtype=float)
    base = pd.concat([pair[["log_distance_mya", "target_gc", "same_group_anchor"]].astype(float), cats], axis=1)
    for col in BASE_FEATURES:
        if col not in base.columns:
            base[col] = 0.0
    base = base[BASE_FEATURES]

    assembly_cols = [
        "log_genome_size_bp",
        "log_contig_count",
        "log_assembly_n50_bp",
        "log_max_contig_bp",
        "assembly_l50",
        "n_fraction",
        "sampled_gc",
    ]
    kmer_cols = ["kmer_js_to_anchor_proto", "kmer_cosine_to_anchor_proto"]
    missing = [c for c in assembly_cols + kmer_cols if c not in pair.columns]
    for col in missing:
        pair[col] = 0.0
    assembly = pair[assembly_cols].astype(float)
    kmer = pair[kmer_cols].astype(float)

    if feature_set == "baseline_deployable":
        out = base
    elif feature_set == "baseline_plus_kmer":
        out = pd.concat([base, kmer], axis=1)
    elif feature_set == "baseline_plus_assembly_kmer":
        out = pd.concat([base, assembly, kmer], axis=1)
    elif feature_set == "genome_only":
        out = pd.concat([pair[["same_group_anchor"]].astype(float), cats, assembly, kmer], axis=1)
    else:
        raise ValueError(feature_set)
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def rf_predict_with_uncertainty(model: RandomForestRegressor, x: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    tree_preds = np.vstack([tree.predict(x) for tree in model.estimators_])
    return tree_preds.mean(axis=0), tree_preds.std(axis=0)


def cv_predictions(pair: pd.DataFrame, feature_set: str, split: str, seed: int) -> pd.DataFrame:
    xdf = feature_matrix(pair.copy(), feature_set)
    y = pair["te_f1"].astype(float).to_numpy()
    if split == "leave_species_out":
        groups = pair["species"].astype(str).to_numpy()
    elif split == "leave_clade_out":
        groups = pair["species_group"].astype(str).to_numpy()
    else:
        raise ValueError(split)
    pred = np.zeros_like(y, dtype=float)
    unc = np.zeros_like(y, dtype=float)
    fold_ok = np.zeros_like(y, dtype=bool)
    for group in sorted(set(groups)):
        train = groups != group
        test = ~train
        if train.sum() < 20 or test.sum() == 0:
            continue
        model = RandomForestRegressor(
            n_estimators=500,
            min_samples_leaf=3,
            random_state=seed,
            n_jobs=2,
        )
        model.fit(xdf.loc[train], y[train])
        pred[test], unc[test] = rf_predict_with_uncertainty(model, xdf.loc[test])
        fold_ok[test] = True
    out = pair.copy()
    out["feature_set"] = feature_set
    out["split"] = split
    out["pred_te_f1"] = pred
    out["rf_tree_sd"] = unc
    out["abs_error"] = np.abs(out["te_f1"].astype(float) - out["pred_te_f1"])
    out["fold_ok"] = fold_ok
    return out.loc[out["fold_ok"]].copy()


def bin_name(score: float) -> str:
    if score >= 0.80:
        return "high_ge0.80"
    if score >= 0.60:
        return "medium_0.60_0.80"
    if score >= 0.40:
        return "low_0.40_0.60"
    return "very_low_lt0.40"


def summarize_predictions(pred: pd.DataFrame) -> tuple[dict, list[dict], list[dict]]:
    y = pred["te_f1"].astype(float).to_numpy()
    p = pred["pred_te_f1"].astype(float).to_numpy()
    abs_err = np.abs(y - p)
    pred = pred.copy()
    pred["risk_bin"] = pred["pred_te_f1"].map(bin_name)
    bin_rows = []
    ece = 0.0
    for risk_bin, sub in pred.groupby("risk_bin"):
        weight = len(sub) / len(pred) if len(pred) else 0.0
        gap = abs(float(sub["pred_te_f1"].mean()) - float(sub["te_f1"].mean()))
        ece += weight * gap
        bin_rows.append({
            "feature_set": sub["feature_set"].iloc[0],
            "split": sub["split"].iloc[0],
            "risk_bin": risk_bin,
            "n": int(len(sub)),
            "mean_pred": float(sub["pred_te_f1"].mean()),
            "mean_actual": float(sub["te_f1"].mean()),
            "calibration_gap": gap,
            "actual_ge0.8_rate": float((sub["te_f1"] >= 0.8).mean()),
            "actual_lt0.5_rate": float((sub["te_f1"] < 0.5).mean()),
        })
    q80 = float(np.quantile(abs_err, 0.80)) if len(abs_err) else math.nan
    q90 = float(np.quantile(abs_err, 0.90)) if len(abs_err) else math.nan
    interval80 = (pred["te_f1"] >= pred["pred_te_f1"] - q80) & (pred["te_f1"] <= pred["pred_te_f1"] + q80)
    interval90 = (pred["te_f1"] >= pred["pred_te_f1"] - q90) & (pred["te_f1"] <= pred["pred_te_f1"] + q90)

    species_rows = []
    for species, sub in pred.groupby("species"):
        best_idx = sub["te_f1"].astype(float).idxmax()
        chosen_idx = sub["pred_te_f1"].astype(float).idxmax()
        true_best = float(sub.loc[best_idx, "te_f1"])
        chosen_actual = float(sub.loc[chosen_idx, "te_f1"])
        sorted_true = sub.sort_values("te_f1", ascending=False)
        true_top2 = set(sorted_true.head(2)["anchor_type"].astype(str))
        chosen_anchor = str(sub.loc[chosen_idx, "anchor_type"])
        species_rows.append({
            "feature_set": sub["feature_set"].iloc[0],
            "split": sub["split"].iloc[0],
            "species": species,
            "species_group": sub["species_group"].iloc[0],
            "chosen_anchor": chosen_anchor,
            "true_best_anchor": str(sub.loc[best_idx, "anchor_type"]),
            "chosen_actual_te_f1": chosen_actual,
            "true_best_te_f1": true_best,
            "anchor_top1_hit": int(chosen_anchor == str(sub.loc[best_idx, "anchor_type"])),
            "anchor_top2_hit": int(chosen_anchor in true_top2),
            "regret": true_best - chosen_actual,
            "predicted_score": float(sub.loc[chosen_idx, "pred_te_f1"]),
            "predicted_uncertainty_sd": float(sub.loc[chosen_idx, "rf_tree_sd"]),
            "risk_bin": bin_name(float(sub.loc[chosen_idx, "pred_te_f1"])),
        })
    sp = pd.DataFrame(species_rows)
    summary = {
        "feature_set": str(pred["feature_set"].iloc[0]),
        "split": str(pred["split"].iloc[0]),
        "n_rows": int(len(pred)),
        "n_species": int(pred["species"].nunique()),
        "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
        "mae": float(mean_absolute_error(y, p)),
        "r2": float(r2_score(y, p)) if len(set(y.tolist())) > 1 else math.nan,
        "ece_by_predicted_bin": float(ece),
        "q80_abs_error": q80,
        "q90_abs_error": q90,
        "coverage_q80_interval": float(interval80.mean()) if len(pred) else math.nan,
        "coverage_q90_interval": float(interval90.mean()) if len(pred) else math.nan,
        "anchor_top1_accuracy": float(sp["anchor_top1_hit"].mean()) if len(sp) else math.nan,
        "anchor_top2_accuracy": float(sp["anchor_top2_hit"].mean()) if len(sp) else math.nan,
        "mean_regret": float(sp["regret"].mean()) if len(sp) else math.nan,
        "p90_regret": float(np.quantile(sp["regret"], 0.90)) if len(sp) else math.nan,
        "usable_screen": bool(
            len(sp) >= 10
            and float(sp["anchor_top2_hit"].mean()) >= 0.75
            and float(sp["regret"].mean()) <= 0.10
            and float(ece) <= 0.10
            and float(np.sqrt(np.mean((y - p) ** 2))) <= 0.20
        ) if len(sp) else False,
    }
    return summary, bin_rows, species_rows


def write_report(out_dir: Path, summaries: list[dict]) -> None:
    ranked = sorted(summaries, key=lambda r: (not r["usable_screen"], r["rmse"], r["mean_regret"]))
    best = ranked[0] if ranked else {}
    lines = [
        "# PIPE-TEFM-NEXT-DECAY-FRAG-20260630 selector calibration",
        "",
        "## Scope",
        "",
        "This report asks whether the deployable genome-derived selector is usable as a new-species trust guide.",
        "It evaluates leave-species-out and leave-clade-out prediction, anchor-choice accuracy, regret, risk-bin calibration, and empirical uncertainty intervals.",
        "",
        "## Headline",
        "",
    ]
    if best:
        lines += [
            f"- Best screen row: `{best['feature_set']}` / `{best['split']}`.",
            f"- RMSE: {best['rmse']:.4f}; ECE: {best['ece_by_predicted_bin']:.4f}; top-1 anchor accuracy: {best['anchor_top1_accuracy']:.4f}; top-2: {best['anchor_top2_accuracy']:.4f}; mean regret: {best['mean_regret']:.4f}.",
            f"- Usable screen gate: {best['usable_screen']}.",
        ]
    lines += [
        "",
        "## Usability Gate",
        "",
        "A selector is marked screen-usable only if it meets all provisional thresholds: at least 10 held-out species, top-2 anchor accuracy >=0.75, mean regret <=0.10, ECE <=0.10, and RMSE <=0.20.",
        "Failing this gate means the selector can still support a paper discussion as triage/risk stratification, but it should not be presented as a reliable deployment confidence formula.",
        "",
        "## Outputs",
        "",
        "- `selector_calibration_summary.tsv`",
        "- `selector_calibration_bins.tsv`",
        "- `selector_species_recommendations.tsv`",
        "- `selector_row_predictions.tsv`",
        "- `selector_calibration_status.json`",
    ]
    (out_dir / "SELECTOR_CALIBRATION_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair-features", default="reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/anchor_pair_genome_features.tsv")
    ap.add_argument("--out-dir", default="reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_calibration")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pair = pd.read_csv(args.pair_features, sep="\t")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries, bins, species_rows, pred_rows = [], [], [], []
    for feature_set in ["baseline_deployable", "baseline_plus_kmer", "baseline_plus_assembly_kmer", "genome_only"]:
        for split in ["leave_species_out", "leave_clade_out"]:
            pred = cv_predictions(pair, feature_set, split, args.seed)
            if pred.empty:
                continue
            summary, bin_rows, sp_rows = summarize_predictions(pred)
            summaries.append(summary)
            bins.extend(bin_rows)
            species_rows.extend(sp_rows)
            pred_rows.extend(pred.to_dict("records"))

    write_tsv(out_dir / "selector_calibration_summary.tsv", summaries)
    write_tsv(out_dir / "selector_calibration_bins.tsv", bins)
    write_tsv(out_dir / "selector_species_recommendations.tsv", species_rows)
    write_tsv(out_dir / "selector_row_predictions.tsv", pred_rows)
    status = {
        "ok": True,
        "n_summary_rows": len(summaries),
        "any_usable_screen": any(bool(row["usable_screen"]) for row in summaries),
        "best": sorted(summaries, key=lambda r: (not r["usable_screen"], r["rmse"], r["mean_regret"]))[0] if summaries else {},
        "outputs": {
            "summary": str(out_dir / "selector_calibration_summary.tsv"),
            "bins": str(out_dir / "selector_calibration_bins.tsv"),
            "species": str(out_dir / "selector_species_recommendations.tsv"),
            "predictions": str(out_dir / "selector_row_predictions.tsv"),
            "report": str(out_dir / "SELECTOR_CALIBRATION_REPORT.md"),
        },
    }
    (out_dir / "selector_calibration_status.json").write_text(json.dumps(status, indent=2) + "\n")
    write_report(out_dir, summaries)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
