#!/usr/bin/env python3
"""MinHash-equivalent deployable selector/router screen.

Mash/sourmash are not available in this environment, so this bounded screen
computes deterministic bottom-k MinHash sketches directly from genome FASTA
files and adds Mash-like distances to anchor prototypes. The target TE labels
are used only for held-out evaluation, not as selector features.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

SEL = Path("pipelines/PIPE-TEFM-NEXT-DECAY-FRAG-20260630").resolve()
sys.path.insert(0, str(SEL))

from selector_calibration import cv_predictions, write_tsv  # noqa: E402
from selector_conservative_router import select_router, species_router_rows, summarize as summarize_router  # noqa: E402


MANIFEST_PATH = Path("software_outputs/repeatmasker_dfam/02_ready_by_design/manifests/MANIFEST_ALL.tsv")
PAIR_FEATURES = Path("reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/anchor_pair_genome_features.tsv")
CACHE_DIR = Path("reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/minhash_cache")

ANCHOR_PROTOTYPES = {
    "animal": ["mouse", "zebrafish", "chicken", "fruit_fly", "c_elegans", "western_honey_bee"],
    "human_h0_ntv2_250m": ["human"],
    "human_h0_ntv2_500m": ["human"],
    "human_h0_ntv3_100m": ["human"],
    "human_h0_ntv3_650m": ["human"],
    "insect": ["fruit_fly", "western_honey_bee"],
    "plant": ["rice", "maize", "sorghum", "brachypodium", "thale_cress"],
    "cross": ["mouse", "zebrafish", "fruit_fly", "c_elegans", "rice", "maize", "sorghum", "brachypodium"],
    "other_anchor": ["human"],
}


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt")
    return path.open("rt")


def load_manifest() -> dict[str, Path]:
    manifest = pd.read_csv(MANIFEST_PATH, sep="\t")
    out: dict[str, Path] = {}
    for _, row in manifest.drop_duplicates("species_code").iterrows():
        path = Path(str(row["genome"]))
        if path.exists():
            out[str(row["species_code"])] = path
    return out


def revcomp(seq: str) -> str:
    return seq.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def canonical(seq: str) -> str:
    rc = revcomp(seq)
    return seq if seq <= rc else rc


def stable_hash64(seq: str) -> int:
    return int.from_bytes(hashlib.blake2b(seq.encode("ascii"), digest_size=8).digest(), "big")


def iter_fasta_bases(path: Path):
    with open_text(path) as handle:
        for line in handle:
            if line.startswith(">"):
                yield "N"
                continue
            for base in line.strip().upper():
                yield base


def sketch_species(species: str, genome: Path, k: int, sketch_size: int, max_bases: int) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{species}.k{k}.sketch{sketch_size}.bases{max_bases}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    hashes: set[int] = set()
    window = ""
    sampled = 0
    valid = 0
    for base in iter_fasta_bases(genome):
        if sampled >= max_bases:
            break
        sampled += 1
        if base in "ACGT":
            valid += 1
            window += base
            if len(window) >= k:
                hashes.add(stable_hash64(canonical(window[-k:])))
                if len(window) > k:
                    window = window[-k:]
        else:
            window = ""
    sketch = sorted(hashes)[:sketch_size]
    result = {
        "species": species,
        "genome": str(genome),
        "k": k,
        "sketch_size": sketch_size,
        "max_bases": max_bases,
        "sampled_bases": sampled,
        "valid_bases": valid,
        "unique_kmers_seen": len(hashes),
        "sketch": sketch,
    }
    cache.write_text(json.dumps(result, indent=2) + "\n")
    return result


def jaccard(a: set[int], b: set[int]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def mash_distance(j: float, k: int) -> float:
    if j <= 0:
        return 1.0
    x = (2.0 * j) / (1.0 + j)
    if x <= 0:
        return 1.0
    return float(max(0.0, min(1.0, -math.log(x) / k)))


def anchor_proto(anchor_type: str) -> str:
    return anchor_type if anchor_type in ANCHOR_PROTOTYPES else "other_anchor"


def augment_pair_features(pair: pd.DataFrame, k: int, sketch_size: int, max_bases: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = load_manifest()
    species_needed = sorted(set(pair["species"].astype(str)))
    proto_species = sorted({sp for members in ANCHOR_PROTOTYPES.values() for sp in members})
    all_needed = sorted(set(species_needed) | set(proto_species))
    sketches: dict[str, set[int]] = {}
    sketch_rows = []
    for species in all_needed:
        if species not in manifest:
            continue
        rec = sketch_species(species, manifest[species], k=k, sketch_size=sketch_size, max_bases=max_bases)
        sketches[species] = set(int(x) for x in rec["sketch"])
        sketch_rows.append({k2: v for k2, v in rec.items() if k2 != "sketch"})

    rows = []
    for _, row in pair.iterrows():
        sp = str(row["species"])
        proto = anchor_proto(str(row["anchor_type"]))
        target = sketches.get(sp, set())
        member_vals = []
        for member in ANCHOR_PROTOTYPES.get(proto, []):
            if member in sketches:
                jj = jaccard(target, sketches[member])
                member_vals.append((member, jj, mash_distance(jj, k)))
        if member_vals:
            best_member, best_j, best_d = max(member_vals, key=lambda x: x[1])
            mean_j = float(np.mean([x[1] for x in member_vals]))
            mean_d = float(np.mean([x[2] for x in member_vals]))
        else:
            best_member, best_j, best_d, mean_j, mean_d = "", 0.0, 1.0, 0.0, 1.0
        rows.append({
            "minhash_anchor_proto": proto,
            "minhash_best_anchor_member": best_member,
            "minhash_jaccard_best_member": best_j,
            "minhash_mash_distance_best_member": best_d,
            "minhash_jaccard_mean_proto": mean_j,
            "minhash_mash_distance_mean_proto": mean_d,
        })
    out = pd.concat([pair.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    return out, pd.DataFrame(sketch_rows)


def feature_matrix(pair: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    from selector_calibration import feature_matrix as base_feature_matrix

    if feature_set in {"baseline_deployable", "baseline_plus_kmer", "baseline_plus_assembly_kmer", "genome_only"}:
        return base_feature_matrix(pair.copy(), feature_set)
    base = base_feature_matrix(pair.copy(), "baseline_plus_kmer")
    minhash = pair[
        [
            "minhash_jaccard_best_member",
            "minhash_mash_distance_best_member",
            "minhash_jaccard_mean_proto",
            "minhash_mash_distance_mean_proto",
        ]
    ].astype(float)
    if feature_set == "baseline_plus_kmer_minhash":
        return pd.concat([base, minhash], axis=1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if feature_set == "minhash_only_router":
        cats = pd.get_dummies(pair[["species_group", "anchor_type"]], prefix=["target", "anchor"], dtype=float)
        return pd.concat([pair[["same_group_anchor"]].astype(float), cats, minhash], axis=1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    raise ValueError(feature_set)


def cv_predictions_local(pair: pd.DataFrame, feature_set: str, split: str, seed: int) -> pd.DataFrame:
    if feature_set in {"baseline_deployable", "baseline_plus_kmer", "baseline_plus_assembly_kmer", "genome_only"}:
        return cv_predictions(pair, feature_set, split, seed)
    xdf = feature_matrix(pair, feature_set)
    y = pair["te_f1"].astype(float).to_numpy()
    groups = pair["species"].astype(str).to_numpy() if split == "leave_species_out" else pair["species_group"].astype(str).to_numpy()
    pred = np.zeros_like(y, dtype=float)
    unc = np.zeros_like(y, dtype=float)
    fold_ok = np.zeros_like(y, dtype=bool)
    for group in sorted(set(groups)):
        train = groups != group
        test = ~train
        if train.sum() < 20 or test.sum() == 0:
            continue
        model = RandomForestRegressor(n_estimators=500, min_samples_leaf=3, random_state=seed, n_jobs=2)
        model.fit(xdf.loc[train], y[train])
        tree_preds = np.vstack([tree.predict(xdf.loc[test]) for tree in model.estimators_])
        pred[test] = tree_preds.mean(axis=0)
        unc[test] = tree_preds.std(axis=0)
        fold_ok[test] = True
    out = pair.copy()
    out["feature_set"] = feature_set
    out["split"] = split
    out["pred_te_f1"] = pred
    out["rf_tree_sd"] = unc
    out["abs_error"] = np.abs(out["te_f1"].astype(float) - out["pred_te_f1"])
    out["fold_ok"] = fold_ok
    return out.loc[out["fold_ok"]].copy()


def calibration_summary(pred: pd.DataFrame) -> dict:
    pred = pred.copy()
    species_rows = species_router_rows(pred, str(pred["feature_set"].iloc[0]), str(pred["split"].iloc[0]))
    y = pred["te_f1"].astype(float).to_numpy()
    p = pred["pred_te_f1"].astype(float).to_numpy()
    return {
        "feature_set": str(pred["feature_set"].iloc[0]),
        "split": str(pred["split"].iloc[0]),
        "n_rows": int(len(pred)),
        "n_species": int(pred["species"].nunique()),
        "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
        "mae": float(np.mean(np.abs(y - p))),
        "top2_contains_best_rate": float(pd.DataFrame(species_rows)["top2_contains_best"].mean()) if species_rows else math.nan,
        "top2_probe_mean_regret": float(pd.DataFrame(species_rows)["top2_probe_regret"].mean()) if species_rows else math.nan,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair-features", default=str(PAIR_FEATURES))
    ap.add_argument("--out-dir", default="reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--k", type=int, default=15)
    ap.add_argument("--sketch-size", type=int, default=2000)
    ap.add_argument("--max-bases", type=int, default=2000000)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pair = pd.read_csv(args.pair_features, sep="\t")
    pair_aug, sketch_meta = augment_pair_features(pair, args.k, args.sketch_size, args.max_bases)
    pair_aug_path = out_dir / "anchor_pair_minhash_features.tsv"
    pair_aug.to_csv(pair_aug_path, sep="\t", index=False)
    sketch_meta.to_csv(out_dir / "minhash_sketch_meta.tsv", sep="\t", index=False)

    all_pred = []
    cal_rows = []
    router_rows = []
    router_summaries = []
    for feature_set in [
        "baseline_plus_kmer",
        "baseline_plus_kmer_minhash",
        "minhash_only_router",
    ]:
        for split in ["leave_species_out", "leave_clade_out"]:
            pred = cv_predictions_local(pair_aug, feature_set, split, args.seed)
            if pred.empty:
                continue
            all_pred.extend(pred.to_dict("records"))
            cal_rows.append(calibration_summary(pred))
            rows = species_router_rows(pred, feature_set, split)
            router_rows.extend(rows)
            router_summaries.append(summarize_router(rows, ece=math.nan))

    write_tsv(out_dir / "selector_minhash_calibration_summary.tsv", cal_rows)
    write_tsv(out_dir / "selector_minhash_row_predictions.tsv", all_pred)
    write_tsv(out_dir / "selector_minhash_router_species.tsv", router_rows)
    write_tsv(out_dir / "selector_minhash_router_summary.tsv", router_summaries)
    selected = select_router(router_summaries)
    status = {
        "ok": True,
        "method": "deterministic bottom-k MinHash equivalent; Mash/sourmash binaries unavailable",
        "seed": args.seed,
        "k": args.k,
        "sketch_size": args.sketch_size,
        "max_bases": args.max_bases,
        "deployable_features_only": True,
        "target_te_annotation_features_excluded_from_selector": True,
        "selected_router_gate_pass": bool(selected["selected_router_gate_pass"]),
        "selected_router": selected,
        "outputs": {
            "pair_features": str(pair_aug_path),
            "calibration_summary": str(out_dir / "selector_minhash_calibration_summary.tsv"),
            "router_summary": str(out_dir / "selector_minhash_router_summary.tsv"),
            "router_species": str(out_dir / "selector_minhash_router_species.tsv"),
        },
    }
    (out_dir / "selector_minhash_status.json").write_text(json.dumps(status, indent=2) + "\n")
    report = [
        "# MinHash Conservative Selector Router",
        "",
        f"- Method: deterministic bottom-k MinHash equivalent, k={args.k}, sketch={args.sketch_size}, max_bases={args.max_bases}.",
        "- External `mash`/`sourmash` binaries were unavailable; this is a bounded equivalent screen.",
        f"- Selected router gate pass: `{bool(selected['selected_router_gate_pass'])}`.",
    ]
    if selected.get("leave_species_policy"):
        row = selected["leave_species_policy"]
        report.append(f"- In-panel selected policy: `{row['feature_set']}` top2 contains-best `{row['top2_contains_best_rate']:.4f}`, mean regret `{row['top2_probe_mean_regret']:.4f}`.")
    if selected.get("leave_clade_policy"):
        row = selected["leave_clade_policy"]
        report.append(f"- Leave-clade policy: abstention `{row['abstention_rate']:.4f}`; do not use point formula for new clades.")
    (out_dir / "SELECTOR_MINHASH_ROUTER_REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
