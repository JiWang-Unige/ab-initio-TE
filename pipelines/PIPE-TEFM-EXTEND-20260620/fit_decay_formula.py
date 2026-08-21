#!/usr/bin/env python3
"""Fit lightweight generalization-decay formulas from accumulated screen results."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def read_tsv(path: str) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_jsons(root: Path) -> list[dict]:
    rows = []
    for path in root.rglob("*.json"):
        if "_tmp" in path.parts:
            continue
        try:
            item = json.loads(path.read_text())
        except Exception:
            continue
        if "te_f1" not in item:
            continue
        item["_path"] = str(path)
        item.setdefault("species", path.stem)
        item.setdefault("model", path.parent.name)
        rows.append(item)
    return rows


def species_covariates(concordance_tsv: str) -> dict[str, dict]:
    cov = {}
    for row in read_tsv(concordance_tsv):
        species = row.get("species_code") or row.get("species") or row.get("name")
        if not species:
            continue
        def f(*keys, default=0.0):
            for key in keys:
                if key in row and row[key] not in {"", "nan", "NA"}:
                    try:
                        return float(row[key])
                    except ValueError:
                        pass
            return default
        cov[species] = {
            "label_jaccard": f("jaccard", "strict_te_jaccard"),
            "self_te_bp": f("self_strict_te_bp", "self_bp"),
            "comparator_te_bp": f("ucsc_strict_te_bp", "comparator_bp", "ucsc_bp"),
        }
    return cov


DISTANCE_BUCKET = {
    "human": 0.10, "human_hg38": 0.10, "human_hg19": 0.10,
    "mouse": 0.20, "cattle": 0.28, "horse": 0.28, "pig": 0.28, "opossum": 0.35,
    "chicken": 0.45, "lizard": 0.50, "western_clawed_frog": 0.55, "x_laevis": 0.58, "zebrafish": 0.65,
    "fruit_fly": 0.85, "western_honey_bee": 0.90, "red_flour_beetle": 0.90, "c_elegans": 0.95,
    "rice": 1.20, "maize": 1.20, "sorghum": 1.20, "brachypodium": 1.20,
    "thale_cress": 1.25, "teosinte": 1.20, "soybean": 1.25,
}


def collect_rows(args) -> list[dict]:
    cov = species_covariates(args.concordance)
    rows = []
    for row in read_tsv(args.lock_recovery):
        species = row.get("species") or row.get("species_code")
        if not species or row.get("condition", row.get("model", "")) not in {"baseline", "baseline_invert_boost", "invert_boost_animal_4096"}:
            pass
        try:
            f1 = float(row.get("te_f1", "nan"))
        except ValueError:
            continue
        if np.isfinite(f1):
            rows.append({"source": "lock_recovery", "species": species, "model": row.get("model", ""), "te_f1": f1})
    for row in read_tsv(args.repair_mixed):
        species = row.get("species") or row.get("species_code")
        try:
            f1 = float(row.get("te_f1", "nan"))
        except ValueError:
            continue
        if species and np.isfinite(f1):
            rows.append({"source": "repair_mixed", "species": species, "model": row.get("model", ""), "te_f1": f1})
    for item in read_jsons(Path(args.new_eval_root)):
        species = item.get("species")
        rows.append({"source": "extend_json", "species": species, "model": item.get("model", ""), "te_f1": float(item["te_f1"]), "path": item["_path"]})
    for row in rows:
        sp = row.get("species", "")
        c = cov.get(sp, {})
        row["distance_bucket"] = DISTANCE_BUCKET.get(sp, 1.0)
        row["label_jaccard"] = float(c.get("label_jaccard", 0.0))
        row["te_bp_log10"] = float(np.log10(max(1.0, c.get("comparator_te_bp", 0.0))))
        row["kingdom_plant"] = 1.0 if sp in {"rice", "maize", "sorghum", "brachypodium", "thale_cress", "teosinte", "soybean"} else 0.0
    return [r for r in rows if r.get("species")]


def fit_formula(rows: list[dict], features: list[str]) -> dict:
    clean = [r for r in rows if np.isfinite(float(r["te_f1"]))]
    if len(clean) <= len(features) + 1:
        return {"features": features, "status": "too_few_rows", "n": len(clean)}
    y = np.asarray([float(r["te_f1"]) for r in clean], dtype=np.float64)
    x = np.ones((len(clean), len(features) + 1), dtype=np.float64)
    for j, feat in enumerate(features, start=1):
        x[:, j] = np.asarray([float(r.get(feat, 0.0)) for r in clean], dtype=np.float64)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    pred = x @ coef
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {
        "features": ["intercept", *features],
        "coef": {name: float(val) for name, val in zip(["intercept", *features], coef)},
        "r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0,
        "rmse": float(np.sqrt(np.mean((y - pred) ** 2))),
        "n": len(clean),
        "status": "ok",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock-recovery", required=True)
    ap.add_argument("--repair-mixed", required=True)
    ap.add_argument("--new-eval-root", required=True)
    ap.add_argument("--concordance", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    rows = collect_rows(args)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "decay_rows.tsv").open("w", newline="") as handle:
        fields = ["source", "species", "model", "te_f1", "distance_bucket", "label_jaccard", "te_bp_log10", "kingdom_plant", "path"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    formulas = [
        fit_formula(rows, ["distance_bucket"]),
        fit_formula(rows, ["distance_bucket", "label_jaccard"]),
        fit_formula(rows, ["distance_bucket", "label_jaccard", "te_bp_log10", "kingdom_plant"]),
    ]
    (out / "formula_fits.json").write_text(json.dumps({"n_rows": len(rows), "formulas": formulas}, indent=2) + "\n")
    print(json.dumps({"n_rows": len(rows), "formulas": formulas}, indent=2))


if __name__ == "__main__":
    main()
