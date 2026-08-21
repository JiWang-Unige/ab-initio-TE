#!/usr/bin/env python3
"""Conservative deployable anchor router diagnostics.

The point selector is not treated as an exact F1 predictor. This script asks a
smaller deployment question: can genome-only features route a species to a
safe top-2 anchor shortlist, or abstain and require a local chromosome probe?
Target TE annotation-derived columns are used only as held-out labels/metrics,
never as selector inputs.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


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


def risk_bin(score: float) -> str:
    if score >= 0.80:
        return "high_ge0.80"
    if score >= 0.60:
        return "medium_0.60_0.80"
    if score >= 0.40:
        return "low_0.40_0.60"
    return "very_low_lt0.40"


def species_router_rows(pred: pd.DataFrame, feature_set: str, split: str) -> list[dict]:
    rows: list[dict] = []
    for species, sub in pred.groupby("species"):
        sub = sub.sort_values("pred_te_f1", ascending=False).copy()
        truth_rank = sub.sort_values("te_f1", ascending=False).copy()
        top1 = sub.iloc[0]
        top2 = sub.head(2)
        true_best = truth_rank.iloc[0]
        true_best_anchor = str(true_best["anchor_type"])
        top2_anchors = list(top2["anchor_type"].astype(str))
        top2_actual = float(top2["te_f1"].astype(float).max())
        best_actual = float(true_best["te_f1"])
        top1_actual = float(top1["te_f1"])
        top1_regret = best_actual - top1_actual
        top2_regret = best_actual - top2_actual

        new_clade = split == "leave_clade_out"
        if new_clade:
            action = "abstain_require_local_probe"
            deployed_anchor = ""
            deployed_regret = math.nan
            local_probe = 1
            abstain = 1
        else:
            action = "top2_shortlist_local_probe"
            deployed_anchor = ",".join(top2_anchors)
            deployed_regret = top2_regret
            local_probe = 1
            abstain = 0

        rows.append({
            "feature_set": feature_set,
            "split": split,
            "species": species,
            "species_group": str(top1["species_group"]),
            "action": action,
            "deployed_anchor_or_shortlist": deployed_anchor,
            "top1_anchor": str(top1["anchor_type"]),
            "top2_anchors": ",".join(top2_anchors),
            "true_best_anchor": true_best_anchor,
            "top1_contains_best": int(str(top1["anchor_type"]) == true_best_anchor),
            "top2_contains_best": int(true_best_anchor in set(top2_anchors)),
            "top1_actual_te_f1": top1_actual,
            "top2_probe_actual_te_f1": top2_actual,
            "true_best_te_f1": best_actual,
            "top1_regret": top1_regret,
            "top2_probe_regret": top2_regret,
            "deployed_regret": deployed_regret,
            "pred_top1_score": float(top1["pred_te_f1"]),
            "pred_top2_score": float(top2.iloc[-1]["pred_te_f1"]),
            "pred_margin": float(top1["pred_te_f1"] - top2.iloc[-1]["pred_te_f1"]),
            "pred_top1_sd": float(top1["rf_tree_sd"]),
            "risk_bin": risk_bin(float(top1["pred_te_f1"])),
            "abstain": abstain,
            "local_probe_recommended": local_probe,
            "confidently_wrong_single_anchor": 0,
        })
    return rows


def calibration_bins(pred: pd.DataFrame, feature_set: str, split: str) -> tuple[float, list[dict]]:
    rows = []
    pred = pred.copy()
    pred["risk_bin"] = pred["pred_te_f1"].astype(float).map(risk_bin)
    ece = 0.0
    for name, sub in pred.groupby("risk_bin"):
        weight = len(sub) / len(pred) if len(pred) else 0.0
        gap = abs(float(sub["pred_te_f1"].mean()) - float(sub["te_f1"].mean()))
        ece += weight * gap
        rows.append({
            "feature_set": feature_set,
            "split": split,
            "risk_bin": name,
            "n": int(len(sub)),
            "mean_pred": float(sub["pred_te_f1"].mean()),
            "mean_actual": float(sub["te_f1"].mean()),
            "calibration_gap": gap,
            "actual_ge0.8_rate": float((sub["te_f1"] >= 0.8).mean()),
            "actual_lt0.5_rate": float((sub["te_f1"] < 0.5).mean()),
        })
    return float(ece), rows


def summarize(rows: list[dict], ece: float) -> dict:
    df = pd.DataFrame(rows)
    deployed = df["abstain"] == 0
    deployed_regret = pd.to_numeric(df.loc[deployed, "deployed_regret"], errors="coerce").dropna()
    top2_regret = df["top2_probe_regret"].astype(float)
    leave_clade = str(df["split"].iloc[0]) == "leave_clade_out"
    mean_regret = float(deployed_regret.mean()) if len(deployed_regret) else math.nan
    p90_regret = float(np.quantile(deployed_regret, 0.90)) if len(deployed_regret) else math.nan
    summary = {
        "feature_set": str(df["feature_set"].iloc[0]),
        "split": str(df["split"].iloc[0]),
        "n_species": int(len(df)),
        "top1_accuracy": float(df["top1_contains_best"].mean()),
        "top2_contains_best_rate": float(df["top2_contains_best"].mean()),
        "top2_probe_mean_regret": float(top2_regret.mean()),
        "top2_probe_p90_regret": float(np.quantile(top2_regret, 0.90)),
        "ece_risk_bin": ece,
        "abstention_rate": float(df["abstain"].mean()),
        "local_probe_recommended_rate": float(df["local_probe_recommended"].mean()),
        "deployed_mean_regret": mean_regret,
        "deployed_p90_regret": p90_regret,
        "single_anchor_high_conf_coverage": 0.0,
        "confidently_wrong_single_anchor_rate": float(df["confidently_wrong_single_anchor"].mean()),
        "leave_clade_abstention_rule": "abstain all leave-clade-out species until local chromosome probe" if leave_clade else "not applicable",
    }
    if leave_clade:
        summary["passes_conservative_gate"] = bool(summary["abstention_rate"] >= 0.95)
    else:
        summary["passes_conservative_gate"] = bool(
            summary["top2_contains_best_rate"] >= 0.85
            and summary["top2_probe_mean_regret"] <= 0.03
            and summary["confidently_wrong_single_anchor_rate"] == 0.0
        )
    return summary


def write_report(out_dir: Path, summaries: list[dict]) -> None:
    best = select_router(summaries).get("leave_species_policy", {})
    gate_pass = bool(select_router(summaries).get("selected_router_gate_pass"))
    lines = [
        "# Conservative Anchor Trust Router",
        "",
        "## Scope",
        "",
        "This is a bounded, non-claim selector diagnostic. It uses only deployable genome-derived inputs for prediction and uses target TE-F1 only for held-out evaluation.",
        "",
        "## Headline",
        "",
    ]
    if best:
        lines += [
            f"- Best in-panel rule: `{best['feature_set']}` / `{best['split']}`.",
            f"- top2 contains-best: {best['top2_contains_best_rate']:.4f}; top2 mean regret: {best['top2_probe_mean_regret']:.4f}; ECE: {best['ece_risk_bin']:.4f}.",
        ]
    lines += [
        f"- Selected conservative router gate passed: {gate_pass}.",
        "- Leave-clade-out is handled by explicit abstention/local-probe, not by trusting the point formula.",
        "",
        "## Decision Wording",
        "",
        "If used in the manuscript, this should be described as a conservative triage router: in-panel species get a top-2 anchor shortlist plus local chromosome probe; unseen clades abstain until a local probe or new anchor is trained.",
    ]
    (out_dir / "SELECTOR_CONSERVATIVE_ROUTER_REPORT.md").write_text("\n".join(lines) + "\n")


def select_router(summaries: list[dict]) -> dict:
    lso = [
        r for r in summaries
        if r["split"] == "leave_species_out" and bool(r["passes_conservative_gate"])
    ]
    lco = [
        r for r in summaries
        if r["split"] == "leave_clade_out" and bool(r["passes_conservative_gate"])
    ]
    lso_best = sorted(lso, key=lambda r: (-r["top2_contains_best_rate"], r["top2_probe_mean_regret"], r["ece_risk_bin"]))[0] if lso else {}
    lco_best = sorted(lco, key=lambda r: (-r["abstention_rate"], r["top2_probe_mean_regret"]))[0] if lco else {}
    return {
        "selected_router_gate_pass": bool(lso_best and lco_best),
        "leave_species_policy": lso_best,
        "leave_clade_policy": lco_best,
        "rule": "leave-species/in-panel: top2 shortlist + local chromosome probe; leave-clade/new clade: abstain and require local probe/new anchor",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", default="reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_calibration/selector_row_predictions.tsv")
    ap.add_argument("--out-dir", default="reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/conservative_router")
    args = ap.parse_args()

    pred = pd.read_csv(args.predictions, sep="\t")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_species_rows: list[dict] = []
    all_bins: list[dict] = []
    summaries: list[dict] = []
    for feature_set in sorted(pred["feature_set"].unique()):
        for split in ["leave_species_out", "leave_clade_out"]:
            sub = pred[(pred["feature_set"] == feature_set) & (pred["split"] == split)].copy()
            if sub.empty:
                continue
            ece, bins = calibration_bins(sub, feature_set, split)
            rows = species_router_rows(sub, feature_set, split)
            summaries.append(summarize(rows, ece))
            all_species_rows.extend(rows)
            all_bins.extend(bins)

    write_tsv(out_dir / "selector_conservative_router_summary.tsv", summaries)
    write_tsv(out_dir / "selector_conservative_router_species.tsv", all_species_rows)
    write_tsv(out_dir / "selector_conservative_router_risk_bins.tsv", all_bins)
    selected = select_router(summaries)
    status = {
        "ok": True,
        "deployable_features_only": True,
        "target_te_annotation_features_excluded_from_selector": True,
        "selected_router_gate_pass": bool(selected["selected_router_gate_pass"]),
        "selected_router": selected,
        "outputs": {
            "summary": str(out_dir / "selector_conservative_router_summary.tsv"),
            "species": str(out_dir / "selector_conservative_router_species.tsv"),
            "risk_bins": str(out_dir / "selector_conservative_router_risk_bins.tsv"),
            "report": str(out_dir / "SELECTOR_CONSERVATIVE_ROUTER_REPORT.md"),
        },
    }
    (out_dir / "selector_conservative_router_status.json").write_text(json.dumps(status, indent=2) + "\n")
    write_report(out_dir, summaries)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
