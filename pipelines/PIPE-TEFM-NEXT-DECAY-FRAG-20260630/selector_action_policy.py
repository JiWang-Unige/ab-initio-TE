#!/usr/bin/env python3
"""Actionable anchor-selector policy from calibrated row predictions.

The prior selector is not accurate enough as a point F1 predictor. This script
tests whether it can still be useful as a decision policy: recommend one anchor,
recommend a top-2 shortlist, or abstain and require local mini fine-tuning.
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


def policy_rows(pred: pd.DataFrame, margin: float, min_pred: float, max_sd: float) -> list[dict]:
    rows = []
    for species, sub in pred.groupby("species"):
        sub = sub.sort_values("pred_te_f1", ascending=False).copy()
        top = sub.iloc[0]
        second = sub.iloc[1] if len(sub) > 1 else top
        true_sorted = sub.sort_values("te_f1", ascending=False)
        true_top1 = str(true_sorted.iloc[0]["anchor_type"])
        true_top2 = set(true_sorted.head(2)["anchor_type"].astype(str))
        top1 = str(top["anchor_type"])
        top2 = [str(top["anchor_type"]), str(second["anchor_type"])]
        pred_margin = float(top["pred_te_f1"] - second["pred_te_f1"])
        confident = pred_margin >= margin and float(top["pred_te_f1"]) >= min_pred and float(top["rf_tree_sd"]) <= max_sd
        if confident:
            action = "single_anchor"
            chosen = [top1]
        else:
            action = "top2_or_local_probe"
            chosen = top2
        chosen_actual = float(sub[sub["anchor_type"].astype(str).isin(chosen)]["te_f1"].max())
        true_best = float(true_sorted.iloc[0]["te_f1"])
        rows.append({
            "feature_set": str(top["feature_set"]),
            "split": str(top["split"]),
            "species": species,
            "species_group": str(top["species_group"]),
            "action": action,
            "recommended_anchors": ",".join(chosen),
            "true_best_anchor": true_top1,
            "top1_anchor": top1,
            "top2_anchors": ",".join(top2),
            "top1_hit": int(top1 == true_top1),
            "top2_hit": int(bool(set(top2) & {true_top1})),
            "recommended_set_contains_true_best": int(true_top1 in set(chosen)),
            "recommended_set_contains_true_top2": int(bool(set(chosen) & true_top2)),
            "pred_top1_score": float(top["pred_te_f1"]),
            "pred_top2_score": float(second["pred_te_f1"]),
            "pred_margin": pred_margin,
            "pred_top1_sd": float(top["rf_tree_sd"]),
            "chosen_actual_te_f1": chosen_actual,
            "true_best_te_f1": true_best,
            "regret_after_action": true_best - chosen_actual,
            "true_best_low_lt0.5": int(true_best < 0.5),
            "chosen_low_lt0.5": int(chosen_actual < 0.5),
        })
    return rows


def summarize(rows: list[dict], margin: float, min_pred: float, max_sd: float) -> dict:
    df = pd.DataFrame(rows)
    if df.empty:
        return {}
    single = df["action"] == "single_anchor"
    return {
        "feature_set": str(df["feature_set"].iloc[0]),
        "split": str(df["split"].iloc[0]),
        "margin": margin,
        "min_pred": min_pred,
        "max_sd": max_sd,
        "n_species": int(len(df)),
        "single_anchor_coverage": float(single.mean()),
        "single_anchor_top1_accuracy": float(df.loc[single, "top1_hit"].mean()) if single.any() else math.nan,
        "top2_or_probe_coverage": float((~single).mean()),
        "action_contains_true_best_rate": float(df["recommended_set_contains_true_best"].mean()),
        "action_contains_true_top2_rate": float(df["recommended_set_contains_true_top2"].mean()),
        "mean_regret_after_action": float(df["regret_after_action"].mean()),
        "p90_regret_after_action": float(np.quantile(df["regret_after_action"], 0.90)),
        "low_best_species_rate": float(df["true_best_low_lt0.5"].mean()),
        "low_chosen_species_rate": float(df["chosen_low_lt0.5"].mean()),
        "usable_action_policy": bool(
            float(df["recommended_set_contains_true_top2"].mean()) >= 0.85
            and float(df["regret_after_action"].mean()) <= 0.06
            and float(np.quantile(df["regret_after_action"], 0.90)) <= 0.20
        ),
    }


def write_report(out_dir: Path, best: dict) -> None:
    lines = [
        "# PIPE-TEFM-NEXT-DECAY-FRAG-20260630 selector action policy",
        "",
        "## Scope",
        "",
        "The point selector is not accurate enough to be a standalone F1 confidence formula. This report tests a safer deployment policy: single-anchor recommendation only when margin and uncertainty are favorable; otherwise return a top-2 shortlist and require a local mini-probe/fine-tune before trust.",
        "",
        "## Headline",
        "",
    ]
    if best:
        lines += [
            f"- Best policy: `{best['feature_set']}` / `{best['split']}`, margin={best['margin']}, min_pred={best['min_pred']}, max_sd={best['max_sd']}.",
            f"- Single-anchor coverage: {best['single_anchor_coverage']:.4f}; top2/probe coverage: {best['top2_or_probe_coverage']:.4f}.",
            f"- Action contains true-top2 rate: {best['action_contains_true_top2_rate']:.4f}; mean regret: {best['mean_regret_after_action']:.4f}; p90 regret: {best['p90_regret_after_action']:.4f}.",
            f"- Usable action-policy gate: {best['usable_action_policy']}.",
        ]
    lines += [
        "",
        "## Interpretation",
        "",
        "If this gate passes, the selector is useful as a conservative routing assistant, not as an exact performance predictor. If it fails under leave-clade-out, new clades require local probing or a new anchor.",
    ]
    (out_dir / "SELECTOR_ACTION_POLICY_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", default="reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_calibration/selector_row_predictions.tsv")
    ap.add_argument("--out-dir", default="reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_action_policy")
    args = ap.parse_args()
    pred = pd.read_csv(args.predictions, sep="\t")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries, all_rows = [], []
    for feature_set in sorted(pred["feature_set"].unique()):
        for split in sorted(pred["split"].unique()):
            sub = pred[(pred["feature_set"] == feature_set) & (pred["split"] == split)]
            for margin in [0.0, 0.05, 0.10, 0.15]:
                for min_pred in [0.0, 0.5, 0.7, 0.8]:
                    for max_sd in [0.05, 0.10, 0.20, 1.00]:
                        rows = policy_rows(sub, margin, min_pred, max_sd)
                        summary = summarize(rows, margin, min_pred, max_sd)
                        if summary:
                            summaries.append(summary)
                            for row in rows:
                                row.update({"margin": margin, "min_pred": min_pred, "max_sd": max_sd})
                            all_rows.extend(rows)
    ranked = sorted(summaries, key=lambda r: (not r["usable_action_policy"], -r["action_contains_true_top2_rate"], r["mean_regret_after_action"], r["top2_or_probe_coverage"]))
    best = ranked[0] if ranked else {}
    write_tsv(out_dir / "selector_action_policy_summary.tsv", summaries)
    write_tsv(out_dir / "selector_action_policy_species.tsv", all_rows)
    status = {
        "ok": True,
        "n_policy_rows": len(summaries),
        "any_usable_action_policy": any(bool(r["usable_action_policy"]) for r in summaries),
        "best": best,
        "outputs": {
            "summary": str(out_dir / "selector_action_policy_summary.tsv"),
            "species": str(out_dir / "selector_action_policy_species.tsv"),
            "report": str(out_dir / "SELECTOR_ACTION_POLICY_REPORT.md"),
        },
    }
    (out_dir / "selector_action_policy_status.json").write_text(json.dumps(status, indent=2) + "\n")
    write_report(out_dir, best)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
