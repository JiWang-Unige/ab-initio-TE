#!/usr/bin/env python3
"""Fit deployable and annotation-aware anchor recommendation formulas."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from pathlib import Path

import numpy as np


DIST_MYA = {
    "human": 6, "human_hg38": 6, "human_hg19": 6,
    "mouse": 90, "cattle": 96, "horse": 96, "pig": 96, "opossum": 160,
    "chicken": 310, "lizard": 320, "western_clawed_frog": 360, "x_laevis": 370, "zebrafish": 430,
    "fruit_fly": 780, "western_honey_bee": 820, "red_flour_beetle": 820, "c_elegans": 900,
    "rice": 1500, "maize": 1500, "sorghum": 1500, "brachypodium": 1500,
    "teosinte": 1500, "thale_cress": 1550, "soybean": 1550,
}
PLANTS = {"rice", "maize", "sorghum", "brachypodium", "teosinte", "thale_cress", "soybean"}
INSECTS = {"fruit_fly", "western_honey_bee", "red_flour_beetle"}
VERTEBRATES = {"human", "human_hg38", "human_hg19", "mouse", "cattle", "horse", "pig", "opossum", "chicken", "lizard", "western_clawed_frog", "x_laevis", "zebrafish"}


def read_tsv(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_jsons(root: str | Path) -> list[dict]:
    rows = []
    root = Path(root)
    if not root.exists():
        return rows
    for path in root.rglob("*.json"):
        try:
            item = json.loads(path.read_text())
        except Exception:
            continue
        if "te_f1" not in item:
            continue
        item["_path"] = str(path)
        item.setdefault("species", path.stem)
        rows.append(item)
    return rows


def add_row(rows: list[dict], source: str, species: str, model: str, te_f1, path: str = "") -> None:
    try:
        f1 = float(te_f1)
    except Exception:
        return
    if species and math.isfinite(f1):
        rows.append({"source": source, "species": species, "model": model or "", "te_f1": f1, "path": path})


def collect_rows(args) -> list[dict]:
    rows = []
    for path, source in [
        (args.calib_binary_eval, "calib_summary"),
        (args.lock_recovery, "lock_recovery"),
        (args.repair_mixed, "repair_mixed"),
        (args.extend_transfer, "extend_transfer"),
    ]:
        for r in read_tsv(path):
            add_row(rows, source, r.get("species") or r.get("species_code"), r.get("model") or r.get("condition") or r.get("stage"), r.get("te_f1"), r.get("_path", ""))
    for item in read_jsons(args.new_eval_root):
        model = item.get("model") or item.get("model_dir") or Path(item["_path"]).parts[-3]
        add_row(rows, "anchor_json", item.get("species"), model, item.get("te_f1"), item["_path"])
    return rows


def species_gc_from_jsonl(path: Path, max_records: int = 200) -> float:
    if not path.exists():
        return 0.0
    gc = total = n = 0
    with gzip.open(path, "rt") as handle:
        for line in handle:
            rec = json.loads(line)
            seq = rec.get("sequence", "").upper()
            gc += seq.count("G") + seq.count("C")
            total += sum(1 for c in seq if c in "ACGT")
            n += 1
            if n >= max_records:
                break
    return gc / total if total else 0.0


def gc_cov(eval_roots: list[str]) -> dict[str, float]:
    out = {}
    for root in eval_roots:
        for path in Path(root).rglob("test/data.jsonl.gz"):
            species = path.parent.parent.name
            out.setdefault(species, species_gc_from_jsonl(path))
    return out


def concordance_cov(path: str) -> dict[str, dict]:
    out = {}
    for r in read_tsv(path):
        sp = r.get("species_code") or r.get("species")
        if not sp:
            continue
        def f(k):
            try:
                return float(r.get(k, 0) or 0)
            except Exception:
                return 0.0
        out[sp] = {
            "label_jaccard": f("jaccard"),
            "library_completeness": f("ucsc_bp_covered_by_self"),
            "self_ucsc_ratio_log": math.log10(max(1.0, f("self_merged_bp")) / max(1.0, f("ucsc_merged_bp"))),
        }
    return out


def anchor_type(model: str) -> str:
    m = model.lower()
    if "plant" in m:
        return "plant"
    if "cross" in m:
        return "cross"
    if "insect" in m or "honey" in m or "beetle" in m:
        return "insect"
    if "animal" in m or "invert" in m or "mouse" in m or "vertebrate" in m:
        return "animal"
    return "unknown"


def kingdom(sp: str) -> str:
    if sp in PLANTS:
        return "plant"
    if sp in INSECTS:
        return "insect"
    if sp in VERTEBRATES:
        return "vertebrate"
    return "other"


def enrich(rows: list[dict], gc: dict[str, float], conc: dict[str, dict]) -> list[dict]:
    for r in rows:
        sp = r["species"]
        at = anchor_type(r["model"])
        kg = kingdom(sp)
        r["target_kingdom"] = kg
        r["anchor_type"] = at
        r["target_gc"] = gc.get(sp, 0.0)
        r["distance_mya"] = float(DIST_MYA.get(sp, 1000))
        r["log_distance_mya"] = math.log10(max(1.0, r["distance_mya"]))
        r["same_kingdom_anchor"] = 1.0 if (
            (at == "plant" and kg == "plant") or
            (at == "insect" and kg == "insect") or
            (at == "animal" and kg in {"vertebrate", "insect"})
        ) else 0.0
        r["cross_anchor"] = 1.0 if at == "cross" else 0.0
        r["plant_target"] = 1.0 if kg == "plant" else 0.0
        r["insect_target"] = 1.0 if kg == "insect" else 0.0
        r["vertebrate_target"] = 1.0 if kg == "vertebrate" else 0.0
        r.update(conc.get(sp, {}))
        r.setdefault("label_jaccard", 0.0)
        r.setdefault("library_completeness", 0.0)
        r.setdefault("self_ucsc_ratio_log", 0.0)
    return rows


def matrix(rows: list[dict], features: list[str]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    clean = [r for r in rows if math.isfinite(float(r["te_f1"]))]
    x = np.ones((len(clean), len(features) + 1), dtype=np.float64)
    for j, feat in enumerate(features, start=1):
        x[:, j] = [float(r.get(feat, 0.0)) for r in clean]
    y = np.asarray([float(r["te_f1"]) for r in clean], dtype=np.float64)
    return x, y, [r["species"] for r in clean]


def fit_linear(rows: list[dict], features: list[str]) -> dict:
    x, y, species = matrix(rows, features)
    if len(y) <= len(features) + 2:
        return {"status": "too_few_rows", "features": features, "n": int(len(y))}
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    pred = x @ coef
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    # Leave-one-species-out sanity check.
    cv_pred = np.zeros_like(y)
    for sp in sorted(set(species)):
        train = np.asarray([s != sp for s in species])
        test = ~train
        if train.sum() <= len(features) + 1:
            cv_pred[test] = y[train].mean() if train.any() else y.mean()
            continue
        c, *_ = np.linalg.lstsq(x[train], y[train], rcond=None)
        cv_pred[test] = x[test] @ c
    cv_rmse = float(np.sqrt(np.mean((y - cv_pred) ** 2)))
    return {
        "status": "ok",
        "features": ["intercept", *features],
        "coef": {k: float(v) for k, v in zip(["intercept", *features], coef)},
        "r2": 1.0 - ss_res / ss_tot if ss_tot else 0.0,
        "rmse": float(np.sqrt(np.mean((y - pred) ** 2))),
        "leave_species_out_rmse": cv_rmse,
        "n": int(len(y)),
    }


def fit_ml(rows: list[dict], features: list[str]) -> dict:
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import r2_score
    except Exception as exc:
        return {"status": "skipped", "reason": repr(exc), "features": features}
    x, y, species = matrix(rows, features)
    if len(y) < 30:
        return {"status": "too_few_rows", "features": features, "n": int(len(y))}
    def rmse(a, b):
        return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))

    model = RandomForestRegressor(n_estimators=200, random_state=42, min_samples_leaf=3)
    model.fit(x[:, 1:], y)
    pred = model.predict(x[:, 1:])
    cv_pred = np.zeros_like(y)
    for sp in sorted(set(species)):
        train = np.asarray([s != sp for s in species])
        test = ~train
        m = RandomForestRegressor(n_estimators=120, random_state=42, min_samples_leaf=3)
        m.fit(x[train, 1:], y[train])
        cv_pred[test] = m.predict(x[test, 1:])
    return {
        "status": "ok",
        "model": "RandomForestRegressor",
        "features": features,
        "r2": float(r2_score(y, pred)),
        "rmse": rmse(y, pred),
        "leave_species_out_rmse": rmse(y, cv_pred),
        "feature_importance": {f: float(v) for f, v in zip(features, model.feature_importances_)},
        "n": int(len(y)),
    }


def recommendations(rows: list[dict]) -> list[dict]:
    best = {}
    for r in rows:
        sp = r["species"]
        if sp not in best or float(r["te_f1"]) > float(best[sp]["te_f1"]):
            best[sp] = r
    out = []
    for sp, r in sorted(best.items()):
        f1 = float(r["te_f1"])
        dist = float(r.get("distance_mya", 1000))
        if f1 >= 0.80:
            verdict = "reuse_current_anchor"
        elif f1 >= 0.50:
            verdict = "reuse_with_calibration"
        else:
            verdict = "train_new_anchor_or_audit_labels"
        out.append({
            "species": sp,
            "best_model": r["model"],
            "best_anchor_type": r["anchor_type"],
            "target_kingdom": r["target_kingdom"],
            "te_f1": f1,
            "distance_mya_proxy": dist,
            "verdict": verdict,
            "note": "MYA is a coarse proxy; label/source audit overrides distance when concordance is low.",
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib-binary-eval", required=True)
    ap.add_argument("--lock-recovery", required=True)
    ap.add_argument("--repair-mixed", required=True)
    ap.add_argument("--extend-transfer", required=True)
    ap.add_argument("--new-eval-root", required=True)
    ap.add_argument("--concordance", required=True)
    ap.add_argument("--eval-data-root", nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    rows = enrich(collect_rows(args), gc_cov(args.eval_data_root), concordance_cov(args.concordance))
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fields = [
        "source", "species", "model", "te_f1", "target_kingdom", "anchor_type",
        "distance_mya", "log_distance_mya", "target_gc", "same_kingdom_anchor",
        "cross_anchor", "plant_target", "insect_target", "vertebrate_target",
        "label_jaccard", "library_completeness", "self_ucsc_ratio_log", "path",
    ]
    with (out / "anchor_decay_rows.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    deployable = ["log_distance_mya", "target_gc", "same_kingdom_anchor", "cross_anchor", "plant_target", "insect_target", "vertebrate_target"]
    annotation_aware = deployable + ["label_jaccard", "library_completeness", "self_ucsc_ratio_log"]
    result = {
        "n_rows": len(rows),
        "deployable_linear": fit_linear(rows, deployable),
        "annotation_aware_linear": fit_linear(rows, annotation_aware),
        "deployable_random_forest": fit_ml(rows, deployable),
        "annotation_aware_random_forest": fit_ml(rows, annotation_aware),
        "anchor_recommendations": recommendations(rows),
        "publication_note": "Deployable models deliberately exclude TE annotation-derived variables; annotation-aware models are explanatory controls only.",
    }
    (out / "anchor_formula_results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (out / "anchor_recommendations.tsv").open("w", newline="") as handle:
        recs = result["anchor_recommendations"]
        writer = csv.DictWriter(handle, fieldnames=list(recs[0]) if recs else ["species"], delimiter="\t")
        writer.writeheader()
        writer.writerows(recs)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
