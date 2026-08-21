#!/usr/bin/env python3
"""Fit extended exploratory generalization-decay formulas."""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import math
from pathlib import Path

import numpy as np


DISTANCE_BUCKET = {
    "human": 0.10, "human_hg38": 0.10, "human_hg19": 0.10,
    "mouse": 0.20, "cattle": 0.28, "horse": 0.28, "pig": 0.28, "opossum": 0.35,
    "chicken": 0.45, "lizard": 0.50, "western_clawed_frog": 0.55, "x_laevis": 0.58, "zebrafish": 0.65,
    "fruit_fly": 0.85, "western_honey_bee": 0.90, "red_flour_beetle": 0.90, "c_elegans": 0.95,
    "rice": 1.20, "maize": 1.20, "sorghum": 1.20, "brachypodium": 1.20,
    "thale_cress": 1.25, "teosinte": 1.20, "soybean": 1.25,
}
PLANTS = {"rice", "maize", "sorghum", "brachypodium", "thale_cress", "teosinte", "soybean"}
STRESS = {"lizard", "x_laevis", "western_honey_bee", "red_flour_beetle", "soybean", "thale_cress"}
INSECTS = {"fruit_fly", "western_honey_bee", "red_flour_beetle"}


def read_tsv(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_jsons(root: Path) -> list[dict]:
    rows = []
    if not root.exists():
        return rows
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
        rows.append(item)
    return rows


def species_covariates(path: str) -> dict[str, dict]:
    cov = {}
    for row in read_tsv(path):
        species = row.get("species_code") or row.get("species")
        if not species:
            continue

        def f(key: str, default: float = 0.0) -> float:
            try:
                return float(row.get(key, default) or default)
            except ValueError:
                return default

        ucsc_bp = f("ucsc_merged_bp")
        self_bp = f("self_merged_bp")
        cov[species] = {
            "label_jaccard": f("jaccard"),
            "repeat_library_completeness": f("ucsc_bp_covered_by_self"),
            "self_label_covered_by_ucsc": f("self_bp_covered_by_ucsc"),
            "ucsc_te_bp_log10": math.log10(max(1.0, ucsc_bp)),
            "self_ucsc_bp_ratio_log": math.log10(max(1.0, self_bp) / max(1.0, ucsc_bp)),
        }
    return cov


def opener(path: str):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path, "rt")


def entropy(counts: collections.Counter) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    probs = [v / total for v in counts.values() if v > 0]
    return -sum(p * math.log(p, 2) for p in probs) / max(1.0, math.log(len(probs) or 1, 2))


def class_entropy_from_bed(bed: str) -> float:
    counts = collections.Counter()
    if not bed or not Path(bed).exists():
        return 0.0
    with opener(bed) as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            p = line.rstrip().split("\t")
            if len(p) < 3:
                continue
            cls = p[6] if len(p) > 6 else "Unknown"
            try:
                width = max(0, int(p[2]) - int(p[1]))
            except ValueError:
                width = 1
            head = (cls or "Unknown").split("/")[0]
            counts[head] += width
    return entropy(counts)


def manifest_covariates(path: str) -> dict[str, dict]:
    out = {}
    for row in read_tsv(path):
        species = row.get("species_code")
        if not species or species in out:
            continue
        out[species] = {
            "class_entropy": class_entropy_from_bed(row.get("comparator_strict", "")),
            "panel_has_train_clade": 1.0 if row.get("split") == "fine_tune" else 0.0,
        }
    return out


def gc_from_jsonl(path: Path, max_records: int = 300) -> float:
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


def data_gc_covariates(root: str | Path) -> dict[str, dict]:
    root = Path(root)
    out = {}
    for path in root.rglob("test/data.jsonl.gz"):
        species = path.parent.parent.name
        if species.startswith("direct_"):
            species = species.removeprefix("direct_")
        out.setdefault(species, {})["gc"] = gc_from_jsonl(path)
    return out


def add_row(rows: list[dict], source: str, species: str, model: str, te_f1, path: str = "") -> None:
    try:
        f1 = float(te_f1)
    except (TypeError, ValueError):
        return
    if species and np.isfinite(f1):
        rows.append({"source": source, "species": species, "model": model or "", "te_f1": f1, "path": path})


def collect_rows(args) -> list[dict]:
    rows = []
    for path, source in [(args.lock_recovery, "lock_recovery"), (args.repair_mixed, "repair_mixed"), (args.extend_transfer, "extend_transfer")]:
        for row in read_tsv(path):
            add_row(rows, source, row.get("species") or row.get("species_code"), row.get("model") or row.get("condition"), row.get("te_f1"), row.get("_path", ""))
    for item in read_jsons(Path(args.new_eval_root)):
        add_row(rows, "calib_json", item.get("species"), item.get("model") or Path(item["_path"]).parts[-3], item.get("te_f1"), item["_path"])

    cov = species_covariates(args.concordance)
    manifest_cov = manifest_covariates(args.manifest)
    gc_cov = data_gc_covariates(args.eval_data_root)
    for row in rows:
        sp = row["species"]
        row["distance_bucket"] = DISTANCE_BUCKET.get(sp, 1.0)
        row["kingdom_plant"] = 1.0 if sp in PLANTS else 0.0
        row["stress_panel"] = 1.0 if sp in STRESS else 0.0
        row["insect_panel"] = 1.0 if sp in INSECTS else 0.0
        row.update(cov.get(sp, {}))
        row.update(manifest_cov.get(sp, {}))
        row.update(gc_cov.get(sp, {}))
        model = row.get("model", "")
        row["train_clade_covered"] = 1.0 if (
            ("plant" in model and sp in PLANTS)
            or ("insect" in model and sp in INSECTS)
            or ("cross" in model)
            or (sp not in PLANTS and sp not in INSECTS and "animal" in model)
        ) else 0.0
        row.setdefault("label_jaccard", 0.0)
        row.setdefault("repeat_library_completeness", 0.0)
        row.setdefault("ucsc_te_bp_log10", 0.0)
        row.setdefault("self_ucsc_bp_ratio_log", 0.0)
        row.setdefault("class_entropy", 0.0)
        row.setdefault("gc", 0.0)
    return rows


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
    ap.add_argument("--extend-transfer", required=True)
    ap.add_argument("--new-eval-root", required=True)
    ap.add_argument("--concordance", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--eval-data-root", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    rows = collect_rows(args)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fields = [
        "source", "species", "model", "te_f1", "distance_bucket", "label_jaccard",
        "repeat_library_completeness", "ucsc_te_bp_log10", "self_ucsc_bp_ratio_log",
        "class_entropy", "gc", "train_clade_covered", "kingdom_plant", "stress_panel",
        "insect_panel", "path",
    ]
    with (out / "decay_rows_extended.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    formulas = [
        fit_formula(rows, ["distance_bucket"]),
        fit_formula(rows, ["distance_bucket", "label_jaccard", "repeat_library_completeness"]),
        fit_formula(rows, ["distance_bucket", "label_jaccard", "ucsc_te_bp_log10", "class_entropy", "gc"]),
        fit_formula(rows, ["distance_bucket", "label_jaccard", "repeat_library_completeness", "ucsc_te_bp_log10", "class_entropy", "gc", "train_clade_covered", "stress_panel", "kingdom_plant", "insect_panel"]),
    ]
    result = {"n_rows": len(rows), "formulas": formulas}
    (out / "formula_fits_extended.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
