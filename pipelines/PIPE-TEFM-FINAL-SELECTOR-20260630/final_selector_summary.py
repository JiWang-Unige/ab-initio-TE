#!/usr/bin/env python3
"""Build final multi-anchor and species-quality summaries from existing evidence."""
from __future__ import annotations

import csv
import gzip
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


EXP_ID = "PIPE-TEFM-FINAL-SELECTOR-20260630"

DIST_MYA = {
    "human": 6,
    "mouse": 90,
    "cattle": 96,
    "horse": 96,
    "pig": 96,
    "opossum": 160,
    "chicken": 310,
    "lizard": 320,
    "western_clawed_frog": 360,
    "x_laevis": 370,
    "zebrafish": 430,
    "fruit_fly": 780,
    "western_honey_bee": 820,
    "red_flour_beetle": 820,
    "c_elegans": 900,
    "rice": 1500,
    "maize": 1500,
    "sorghum": 1500,
    "brachypodium": 1500,
    "teosinte": 1500,
    "thale_cress": 1550,
    "soybean": 1550,
}
PLANTS = {"rice", "maize", "sorghum", "brachypodium", "teosinte", "thale_cress", "soybean"}
INSECTS = {"fruit_fly", "western_honey_bee", "red_flour_beetle"}
VERTEBRATES = {
    "human",
    "mouse",
    "cattle",
    "horse",
    "pig",
    "opossum",
    "chicken",
    "lizard",
    "western_clawed_frog",
    "x_laevis",
    "zebrafish",
}


def read_tsv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, sep="\t")


def write_tsv(path: Path, rows: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(path, sep="\t", index=False)


def species_group(species: str) -> str:
    if species in PLANTS:
        return "plant"
    if species in INSECTS:
        return "insect"
    if species in VERTEBRATES:
        return "vertebrate"
    return "other"


def anchor_type(model: str, source: str = "") -> str:
    text = f"{model} {source}".lower()
    if "species_probe" in text or "species_specific" in text:
        return "species_specific"
    if "ntv2_250m" in text:
        return "human_h0_ntv2_250m"
    if "ntv3_100m" in text:
        return "human_h0_ntv3_100m"
    if "plant_supervised" in text:
        return "plant"
    if "cross_supervised" in text:
        return "cross"
    if "insect_primary" in text or "insect_no_beetle" in text:
        return "insect"
    if "invert_boost_animal" in text or "animal_invert_boost" in text:
        return "animal"
    if "ntv2_500m" in text:
        return "human_h0_ntv2_500m"
    return "other_anchor"


def species_gc_from_jsonl(path: Path, max_records: int = 200) -> float:
    gc = total = n = 0
    with gzip.open(path, "rt") as handle:
        for line in handle:
            rec = json.loads(line)
            seq = rec.get("sequence", "").upper()
            gc += seq.count("G") + seq.count("C")
            total += sum(1 for base in seq if base in "ACGT")
            n += 1
            if n >= max_records:
                break
    return gc / total if total else math.nan


def collect_gc(root: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for path in root.rglob("test/data.jsonl.gz"):
        species = path.parent.parent.name
        out.setdefault(species, species_gc_from_jsonl(path))
    return out


def concordance(path: Path) -> pd.DataFrame:
    df = read_tsv(path)
    if df.empty:
        return pd.DataFrame(columns=["species", "label_jaccard", "ucsc_bp_covered_by_self", "self_bp_covered_by_ucsc"])
    return df.rename(columns={"species_code": "species"})[
        ["species", "jaccard", "ucsc_bp_covered_by_self", "self_bp_covered_by_ucsc", "self_merged_bp", "ucsc_merged_bp"]
    ].rename(columns={"jaccard": "label_jaccard"})


def build_species_probe_quality(out_dir: Path, conc: pd.DataFrame) -> pd.DataFrame:
    probe = read_tsv("reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/species_probe.tsv")
    baseline = read_tsv("reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/transfer_by_species.tsv")
    if not baseline.empty:
        baseline = baseline[
            (baseline["stage"] == "transfer_BC_w4096")
            & (baseline["model_key"] == "ntv2_500m")
            & (baseline["window"] == 4096)
        ][["species", "te_f1", "te_auprc"]].rename(
            columns={"te_f1": "h0_ntv2_500m_te_f1", "te_auprc": "h0_ntv2_500m_te_auprc"}
        )
    else:
        baseline = pd.DataFrame(columns=["species", "h0_ntv2_500m_te_f1", "h0_ntv2_500m_te_auprc"])
    audit = probe.rename(
        columns={
            "te_f1": "species_probe_te_f1",
            "te_auprc": "species_probe_te_auprc",
            "te_precision": "species_probe_te_precision",
            "te_recall": "species_probe_te_recall",
        }
    ).merge(baseline, on="species", how="left")
    audit["probe_delta_vs_h0"] = audit["species_probe_te_f1"] - audit["h0_ntv2_500m_te_f1"]
    audit = audit.merge(conc, on="species", how="left")
    audit["species_group"] = audit["species"].map(species_group)

    def verdict(row: pd.Series) -> str:
        f1 = float(row["species_probe_te_f1"])
        if f1 < 0.50:
            return "poor_after_species_ft_audit_labels"
        if f1 < 0.80:
            return "partial_recovery_use_with_caution"
        if pd.notna(row.get("h0_ntv2_500m_te_f1")) and float(row["probe_delta_vs_h0"]) < 0.05:
            return "already_good_or_limited_gain"
        return "calibratable"

    audit["quality_verdict"] = audit.apply(verdict, axis=1)
    audit = audit.sort_values(["species_probe_te_f1", "species"])
    write_tsv(out_dir / "species_probe_quality_audit.tsv", audit)
    return audit


def add_perf_row(rows: list[dict], source: str, model: str, species: str, te_f1, extra: dict | None = None) -> None:
    try:
        f1 = float(te_f1)
    except Exception:
        return
    if not species or not math.isfinite(f1):
        return
    row = {
        "source": source,
        "model": model,
        "species": species,
        "te_f1": f1,
        "anchor_type": anchor_type(model, source),
        "species_group": species_group(species),
    }
    if extra:
        row.update(extra)
    rows.append(row)


def build_anchor_performance(out_dir: Path, conc: pd.DataFrame, gc: dict[str, float]) -> pd.DataFrame:
    rows: list[dict] = []
    ebar = read_tsv("reports/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/summaries/eval_chrom_repeat_summary.tsv")
    for _, r in ebar.iterrows():
        add_perf_row(
            rows,
            "final_errorbar",
            str(r["model_tag"]),
            str(r["species"]),
            r["mean_te_f1"],
            {"panel": r.get("panel"), "n_chrom": r.get("n_chrom"), "sd_te_f1": r.get("sd_te_f1")},
        )
    for path, source in [
        ("reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/binary_eval.tsv", "calib_anchor"),
        ("reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summaries/binary_eval.tsv", "anchor_anchor"),
    ]:
        df = read_tsv(path)
        for _, r in df.iterrows():
            add_perf_row(rows, source, str(r.get("model") or r.get("stage")), str(r["species"]), r["te_f1"], {"stage": r.get("stage")})
    supp = read_tsv("reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/transfer_by_species.tsv")
    supp = supp[(supp["stage"] == "transfer_BC_w4096") & (supp["model_key"] == "ntv2_500m") & (supp["window"] == 4096)]
    for _, r in supp.iterrows():
        add_perf_row(rows, "supp_h0_transfer", "ntv2_500m_H0_w4096", str(r["species"]), r["te_f1"], {"stage": r.get("stage")})
    perf = pd.DataFrame(rows)
    perf = perf.merge(conc, on="species", how="left")
    perf["target_gc"] = perf["species"].map(gc)
    perf["distance_mya_proxy"] = perf["species"].map(lambda sp: float(DIST_MYA.get(sp, 1000)))
    perf["log_distance_mya"] = perf["distance_mya_proxy"].map(lambda x: math.log10(max(1.0, x)))
    perf["same_group_anchor"] = perf.apply(
        lambda r: int(
            (r["anchor_type"] == "plant" and r["species_group"] == "plant")
            or (r["anchor_type"] == "insect" and r["species_group"] == "insect")
            or (r["anchor_type"] == "animal" and r["species_group"] in {"vertebrate", "insect"})
        ),
        axis=1,
    )
    perf = perf.sort_values(["species", "te_f1"], ascending=[True, False])
    write_tsv(out_dir / "anchor_performance_matrix.tsv", perf)
    return perf


def fit_selector(perf: pd.DataFrame, out_dir: Path) -> dict:
    features = ["log_distance_mya", "target_gc", "same_group_anchor"]
    cats = pd.get_dummies(perf[["species_group", "anchor_type"]], prefix=["target", "anchor"], dtype=float)
    xdf = pd.concat([perf[features].fillna(0.0).astype(float), cats], axis=1)
    y = perf["te_f1"].astype(float).to_numpy()
    species = perf["species"].astype(str).to_numpy()
    results: dict[str, object] = {"n_rows": int(len(perf)), "features": list(xdf.columns)}
    if len(perf) >= 20:
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.metrics import r2_score

            model = RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=42)
            model.fit(xdf, y)
            pred = model.predict(xdf)
            cv_pred = np.zeros_like(y)
            for sp in sorted(set(species)):
                train = species != sp
                test = ~train
                m = RandomForestRegressor(n_estimators=150, min_samples_leaf=3, random_state=42)
                m.fit(xdf.loc[train], y[train])
                cv_pred[test] = m.predict(xdf.loc[test])
            results["deployable_random_forest"] = {
                "status": "ok",
                "r2_in_sample": float(r2_score(y, pred)),
                "rmse_in_sample": float(np.sqrt(np.mean((y - pred) ** 2))),
                "leave_species_out_rmse": float(np.sqrt(np.mean((y - cv_pred) ** 2))),
                "feature_importance": {k: float(v) for k, v in zip(xdf.columns, model.feature_importances_)},
            }
        except Exception as exc:
            results["deployable_random_forest"] = {"status": "skipped", "reason": repr(exc)}

    aware_cols = ["label_jaccard", "ucsc_bp_covered_by_self", "self_bp_covered_by_ucsc"]
    if set(aware_cols).issubset(perf.columns):
        aware = pd.concat([xdf, perf[aware_cols].fillna(0.0).astype(float)], axis=1)
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.metrics import r2_score

            model = RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=42)
            model.fit(aware, y)
            pred = model.predict(aware)
            cv_pred = np.zeros_like(y)
            for sp in sorted(set(species)):
                train = species != sp
                test = ~train
                m = RandomForestRegressor(n_estimators=150, min_samples_leaf=3, random_state=42)
                m.fit(aware.loc[train], y[train])
                cv_pred[test] = m.predict(aware.loc[test])
            results["annotation_aware_random_forest"] = {
                "status": "ok",
                "r2_in_sample": float(r2_score(y, pred)),
                "rmse_in_sample": float(np.sqrt(np.mean((y - pred) ** 2))),
                "leave_species_out_rmse": float(np.sqrt(np.mean((y - cv_pred) ** 2))),
                "feature_importance": {k: float(v) for k, v in zip(aware.columns, model.feature_importances_)},
            }
        except Exception as exc:
            results["annotation_aware_random_forest"] = {"status": "skipped", "reason": repr(exc)}

    (out_dir / "selector_formula_results.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def build_recommendations(perf: pd.DataFrame, audit: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    best = perf.sort_values(["species", "te_f1"], ascending=[True, False]).groupby("species", as_index=False).first()
    audit_small = audit[["species", "species_probe_te_f1", "quality_verdict"]]
    rec = best.merge(audit_small, on="species", how="left")

    def verdict(row: pd.Series) -> str:
        if row.get("quality_verdict") == "poor_after_species_ft_audit_labels":
            return "audit_labels_before_anchor_claim"
        if float(row["te_f1"]) >= 0.80:
            return "reuse_observed_best_anchor"
        if float(row["te_f1"]) >= 0.50:
            return "reuse_with_calibration_or_clade_anchor"
        return "train_new_anchor_or_audit_labels"

    rec["recommendation"] = rec.apply(verdict, axis=1)
    rec = rec[
        [
            "species",
            "species_group",
            "model",
            "anchor_type",
            "source",
            "te_f1",
            "species_probe_te_f1",
            "quality_verdict",
            "recommendation",
            "label_jaccard",
            "target_gc",
            "distance_mya_proxy",
        ]
    ].sort_values(["species_group", "species"])
    write_tsv(out_dir / "multi_anchor_recommendations.tsv", rec)
    return rec


def write_report(out_dir: Path, audit: pd.DataFrame, perf: pd.DataFrame, rec: pd.DataFrame, selector: dict) -> None:
    poor = audit[audit["quality_verdict"] == "poor_after_species_ft_audit_labels"]["species"].tolist()
    partial = audit[audit["quality_verdict"] == "partial_recovery_use_with_caution"]["species"].tolist()
    oracle_mean = float(rec["te_f1"].mean()) if not rec.empty else math.nan
    model_means = perf.groupby("model")["te_f1"].agg(["count", "mean"]).reset_index()
    model_means = model_means[model_means["count"] >= 5].sort_values("mean", ascending=False)
    best_single = model_means.iloc[0].to_dict() if not model_means.empty else {}
    rf = selector.get("deployable_random_forest", {})
    lines = [
        f"# {EXP_ID}",
        "",
        "## Summary",
        "",
        f"- Species-probe audit rows: {len(audit)}.",
        f"- Poor after species-specific NTv2-500M fine-tune: {', '.join(poor) if poor else 'none'}.",
        f"- Partial recovery / use with caution: {', '.join(partial) if partial else 'none'}.",
        f"- Non-species-specific anchor performance rows: {len(perf)}.",
        f"- Observed multi-anchor oracle mean over species: {oracle_mean:.4f}.",
    ]
    if best_single:
        lines.append(f"- Best broad single model with >=5 rows: `{best_single['model']}` mean TE-F1 {float(best_single['mean']):.4f} over {int(best_single['count'])} rows.")
    if isinstance(rf, dict) and rf.get("status") == "ok":
        lines.append(
            f"- Deployable selector RF: in-sample R2 {rf['r2_in_sample']:.4f}, leave-species-out RMSE {rf['leave_species_out_rmse']:.4f}."
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Species-specific NTv2-500M recovery should be treated as a soft annotation-quality audit, not an automatic exclusion rule.",
        "- Multi-anchor reporting is supported: animal/human, plant/cross, and insect-specific anchors solve different target panels.",
        "- Deployable selector features deliberately exclude target TE annotations; annotation-aware formulas are explanatory controls only.",
        "- Red flour beetle remains the clearest hard label/library/domain-risk species because it stays poor even after species-specific fine-tuning.",
        "",
        "## Outputs",
        "",
        "- `species_probe_quality_audit.tsv`",
        "- `anchor_performance_matrix.tsv`",
        "- `multi_anchor_recommendations.tsv`",
        "- `selector_formula_results.json`",
    ]
    (out_dir / "FINAL_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    out_dir = Path("reports/tefm_final") / EXP_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    conc = concordance(Path("reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260629_V6/summary.tsv"))
    gc = collect_gc(Path("software_outputs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/data"))
    audit = build_species_probe_quality(out_dir, conc)
    perf = build_anchor_performance(out_dir, conc, gc)
    selector = fit_selector(perf, out_dir)
    rec = build_recommendations(perf, audit, out_dir)
    write_report(out_dir, audit, perf, rec, selector)
    status = {
        "ok": True,
        "exp_id": EXP_ID,
        "species_probe_rows": int(len(audit)),
        "anchor_perf_rows": int(len(perf)),
        "recommendation_rows": int(len(rec)),
        "poor_species_after_species_probe": audit[audit["quality_verdict"] == "poor_after_species_ft_audit_labels"][
            "species"
        ].tolist(),
        "partial_recovery_species": audit[audit["quality_verdict"] == "partial_recovery_use_with_caution"]["species"].tolist(),
        "outputs": {
            "species_probe_quality": str(out_dir / "species_probe_quality_audit.tsv"),
            "anchor_performance": str(out_dir / "anchor_performance_matrix.tsv"),
            "recommendations": str(out_dir / "multi_anchor_recommendations.tsv"),
            "selector": str(out_dir / "selector_formula_results.json"),
            "report": str(out_dir / "FINAL_REPORT.md"),
        },
    }
    (out_dir / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
