#!/usr/bin/env python3
"""Genome-derived feature prototype for TE-FM anchor selection.

This script extends PIPE-TEFM-FINAL-SELECTOR-20260630 without using target TE
annotations. It adds deployable genome-only features: assembly statistics and
sampled whole-genome k-mer distances to anchor prototypes.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import shutil
from collections import Counter
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


EXP_ID = "PIPE-TEFM-FINAL-GENOMEDECAY-20260630"
ROOT = Path(".")
OUT_DIR = Path("reports/tefm_final") / EXP_ID
CACHE_DIR = OUT_DIR / "feature_cache"
PERF_PATH = Path("reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/anchor_performance_matrix.tsv")
MANIFEST_PATH = Path("software_outputs/repeatmasker_dfam/02_ready_by_design/manifests/MANIFEST_ALL.tsv")

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

ANCHOR_PROTOTYPES = {
    "animal": ["mouse", "zebrafish", "chicken", "fruit_fly", "c_elegans", "western_honey_bee"],
    "human_h0_ntv2_250m": ["human"],
    "human_h0_ntv2_500m": ["human"],
    "human_h0_ntv3_100m": ["human"],
    "insect": ["fruit_fly", "western_honey_bee"],
    "plant": ["rice", "maize", "sorghum", "brachypodium", "thale_cress"],
    "cross": ["mouse", "zebrafish", "fruit_fly", "c_elegans", "rice", "maize", "sorghum", "brachypodium"],
    "other_anchor": ["human"],
}


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def find_fai(path: Path) -> Path | None:
    candidates = [
        Path(str(path) + ".fai"),
        path.with_suffix(path.suffix + ".fai"),
        path.with_suffix(".fa.fai"),
        path.with_suffix(".fai"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def n50(lengths: list[int]) -> tuple[int, int]:
    if not lengths:
        return 0, 0
    total = sum(lengths)
    acc = 0
    for i, length in enumerate(sorted(lengths, reverse=True), start=1):
        acc += length
        if acc >= total / 2:
            return int(length), int(i)
    return int(lengths[-1]), len(lengths)


def lengths_from_fai(path: Path) -> list[int]:
    lengths: list[int] = []
    with path.open() as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                try:
                    lengths.append(int(parts[1]))
                except ValueError:
                    pass
    return lengths


def iter_fasta_sequences(path: Path) -> Iterable[str]:
    seq_parts: list[str] = []
    with open_text(path) as handle:
        for line in handle:
            if line.startswith(">"):
                if seq_parts:
                    yield "".join(seq_parts)
                    seq_parts.clear()
            else:
                seq_parts.append(line.strip().upper())
        if seq_parts:
            yield "".join(seq_parts)


def canonical_kmers(k: int) -> list[str]:
    alphabet = "ACGT"
    kmers = [""]
    for _ in range(k):
        kmers = [prefix + base for prefix in kmers for base in alphabet]
    return kmers


def vector_from_counts(counts: Counter[str], kmer_index: list[str]) -> np.ndarray:
    vec = np.array([counts.get(kmer, 0) for kmer in kmer_index], dtype=float)
    total = vec.sum()
    if total:
        vec /= total
    return vec


def js_distance(p: np.ndarray, q: np.ndarray) -> float:
    eps = 1e-12
    p = p + eps
    q = q + eps
    p /= p.sum()
    q /= q.sum()
    m = 0.5 * (p + q)
    kl_pm = np.sum(p * np.log2(p / m))
    kl_qm = np.sum(q * np.log2(q / m))
    return float(math.sqrt(max(0.0, 0.5 * (kl_pm + kl_qm))))


def cosine_distance(p: np.ndarray, q: np.ndarray) -> float:
    denom = float(np.linalg.norm(p) * np.linalg.norm(q))
    if denom == 0.0:
        return 1.0
    return float(1.0 - np.dot(p, q) / denom)


def compute_genome_features(species: str, genome: Path, k: int, max_sample_bases: int) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{species}.k{k}.bounded_prefix.sample{max_sample_bases}.json"
    if cache.exists():
        return json.loads(cache.read_text())

    fai = find_fai(genome)
    lengths = lengths_from_fai(fai) if fai else []
    length_source = "fai" if lengths else "bounded_fasta_scan"
    if not lengths:
        lengths = []
        scanned = 0
        for seq in iter_fasta_sequences(genome):
            lengths.append(len(seq))
            scanned += len(seq)
            if scanned >= 50_000_000:
                break

    genome_size = int(sum(lengths))
    contig_count = int(len(lengths))
    n50_value, l50_value = n50(lengths)
    max_contig = int(max(lengths) if lengths else 0)
    kmer_counts: Counter[str] = Counter()
    valid_sampled = 0
    gc = 0
    acgt = 0
    n_bases = 0
    tail = ""

    for seq in iter_fasta_sequences(genome):
        for base in seq:
            if valid_sampled >= max_sample_bases:
                break
            if base in "ACGT":
                acgt += 1
                gc += int(base in "GC")
                tail += base
                valid_sampled += 1
                if len(tail) >= k:
                    kmer_counts[tail[-k:]] += 1
                    if len(tail) > k:
                        tail = tail[-k:]
            else:
                n_bases += 1
                tail = ""
        if valid_sampled >= max_sample_bases:
            break

    kmer_index = canonical_kmers(k)
    kmer_freq = {kmer: float(v) for kmer, v in zip(kmer_index, vector_from_counts(kmer_counts, kmer_index))}
    result = {
        "species": species,
        "genome": str(genome),
        "fai_used": str(fai) if fai else "",
        "assembly_stats_source": length_source,
        "genome_size_bp": genome_size,
        "contig_count": contig_count,
        "max_contig_bp": max_contig,
        "assembly_n50_bp": int(n50_value),
        "assembly_l50": int(l50_value),
        "n_fraction": float(n_bases / (acgt + n_bases)) if (acgt + n_bases) else math.nan,
        "sampled_gc": float(gc / acgt) if acgt else math.nan,
        "kmer_k": k,
        "kmer_sampling_mode": "bounded_prefix_stream",
        "kmer_sampled_bases": valid_sampled,
        "kmer_counts_total": int(sum(kmer_counts.values())),
        "kmer_freq": kmer_freq,
    }
    cache.write_text(json.dumps(result, indent=2) + "\n")
    return result


def load_manifest() -> dict[str, Path]:
    manifest = pd.read_csv(MANIFEST_PATH, sep="\t")
    out: dict[str, Path] = {}
    for _, row in manifest.drop_duplicates("species_code").iterrows():
        path = Path(str(row["genome"]))
        if path.exists():
            out[str(row["species_code"])] = path
    return out


def anchor_type_to_proto(anchor_type: str) -> str:
    return anchor_type if anchor_type in ANCHOR_PROTOTYPES else "other_anchor"


def build_feature_tables(k: int, max_sample_bases: int) -> tuple[pd.DataFrame, dict[str, np.ndarray], dict[str, np.ndarray]]:
    perf = pd.read_csv(PERF_PATH, sep="\t")
    needed_species = sorted(set(perf["species"].astype(str)))
    manifest = load_manifest()
    kmer_index = canonical_kmers(k)
    rows = []
    species_vecs: dict[str, np.ndarray] = {}
    for species in needed_species:
        if species not in manifest:
            continue
        features = compute_genome_features(species, manifest[species], k=k, max_sample_bases=max_sample_bases)
        vec = np.array([features["kmer_freq"][kmer] for kmer in kmer_index], dtype=float)
        species_vecs[species] = vec
        row = {key: value for key, value in features.items() if key != "kmer_freq"}
        rows.append(row)
    species_df = pd.DataFrame(rows).sort_values("species")

    proto_vecs: dict[str, np.ndarray] = {}
    for proto, species_list in ANCHOR_PROTOTYPES.items():
        vecs = [species_vecs[sp] for sp in species_list if sp in species_vecs]
        if vecs:
            arr = np.mean(np.vstack(vecs), axis=0)
            arr /= arr.sum() if arr.sum() else 1.0
            proto_vecs[proto] = arr
    return species_df, species_vecs, proto_vecs


def add_pair_features(perf: pd.DataFrame, species_df: pd.DataFrame, species_vecs: dict[str, np.ndarray], proto_vecs: dict[str, np.ndarray]) -> pd.DataFrame:
    stats = species_df.set_index("species")
    pair = perf.copy()
    for col in ["genome_size_bp", "contig_count", "max_contig_bp", "assembly_n50_bp", "assembly_l50", "n_fraction", "sampled_gc", "kmer_sampled_bases"]:
        pair[col] = pair["species"].map(stats[col] if col in stats.columns else {})
    pair["log_genome_size_bp"] = pair["genome_size_bp"].map(lambda x: math.log10(float(x)) if pd.notna(x) and float(x) > 0 else 0.0)
    pair["log_contig_count"] = pair["contig_count"].map(lambda x: math.log10(float(x)) if pd.notna(x) and float(x) > 0 else 0.0)
    pair["log_assembly_n50_bp"] = pair["assembly_n50_bp"].map(lambda x: math.log10(float(x)) if pd.notna(x) and float(x) > 0 else 0.0)
    pair["log_max_contig_bp"] = pair["max_contig_bp"].map(lambda x: math.log10(float(x)) if pd.notna(x) and float(x) > 0 else 0.0)

    js_vals = []
    cos_vals = []
    for _, row in pair.iterrows():
        sp = str(row["species"])
        proto = anchor_type_to_proto(str(row["anchor_type"]))
        sv = species_vecs.get(sp)
        pv = proto_vecs.get(proto)
        if sv is None or pv is None:
            js_vals.append(math.nan)
            cos_vals.append(math.nan)
        else:
            js_vals.append(js_distance(sv, pv))
            cos_vals.append(cosine_distance(sv, pv))
    pair["kmer_js_to_anchor_proto"] = js_vals
    pair["kmer_cosine_to_anchor_proto"] = cos_vals
    return pair


def feature_matrix(pair: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    cats = pd.get_dummies(pair[["species_group", "anchor_type"]], prefix=["target", "anchor"], dtype=float)
    base = pd.concat([pair[["log_distance_mya", "target_gc", "same_group_anchor"]].astype(float), cats], axis=1)
    for col in BASE_FEATURES:
        if col not in base.columns:
            base[col] = 0.0
    base = base[BASE_FEATURES]

    assembly = pair[
        [
            "log_genome_size_bp",
            "log_contig_count",
            "log_assembly_n50_bp",
            "log_max_contig_bp",
            "assembly_l50",
            "n_fraction",
            "sampled_gc",
        ]
    ].astype(float)
    kmer = pair[["kmer_js_to_anchor_proto", "kmer_cosine_to_anchor_proto"]].astype(float)

    if feature_set == "baseline_deployable":
        out = base
    elif feature_set == "baseline_plus_assembly":
        out = pd.concat([base, assembly], axis=1)
    elif feature_set == "baseline_plus_kmer":
        out = pd.concat([base, kmer], axis=1)
    elif feature_set == "baseline_plus_assembly_kmer":
        out = pd.concat([base, assembly, kmer], axis=1)
    elif feature_set == "genome_only":
        out = pd.concat([pair[["same_group_anchor"]].astype(float), cats, assembly, kmer], axis=1)
    else:
        raise ValueError(feature_set)
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def evaluate_selector(pair: pd.DataFrame) -> dict:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score

    y = pair["te_f1"].astype(float).to_numpy()
    species = pair["species"].astype(str).to_numpy()
    results: dict[str, dict] = {}
    for name in [
        "baseline_deployable",
        "baseline_plus_assembly",
        "baseline_plus_kmer",
        "baseline_plus_assembly_kmer",
        "genome_only",
    ]:
        xdf = feature_matrix(pair, name)
        model = RandomForestRegressor(n_estimators=400, min_samples_leaf=3, random_state=42)
        model.fit(xdf, y)
        pred = model.predict(xdf)
        cv_pred = np.zeros_like(y)
        for sp in sorted(set(species)):
            train = species != sp
            test = ~train
            m = RandomForestRegressor(n_estimators=200, min_samples_leaf=3, random_state=42)
            m.fit(xdf.loc[train], y[train])
            cv_pred[test] = m.predict(xdf.loc[test])
        results[name] = {
            "n_features": int(xdf.shape[1]),
            "r2_in_sample": float(r2_score(y, pred)),
            "rmse_in_sample": float(np.sqrt(np.mean((y - pred) ** 2))),
            "mae_in_sample": float(mean_absolute_error(y, pred)),
            "leave_species_out_rmse": float(np.sqrt(np.mean((y - cv_pred) ** 2))),
            "leave_species_out_mae": float(mean_absolute_error(y, cv_pred)),
            "feature_importance_top15": {
                key: float(val)
                for key, val in sorted(zip(xdf.columns, model.feature_importances_), key=lambda kv: kv[1], reverse=True)[:15]
            },
        }
    return results


def write_report(pair: pd.DataFrame, species_df: pd.DataFrame, results: dict, out_dir: Path, k: int, max_sample_bases: int) -> None:
    base = results["baseline_deployable"]["leave_species_out_rmse"]
    best_name = min(results, key=lambda name: results[name]["leave_species_out_rmse"])
    best = results[best_name]["leave_species_out_rmse"]
    mash_status = "available" if shutil.which("mash") else "unavailable"
    sourmash_status = "available" if shutil.which("sourmash") else "unavailable"
    lines = [
        f"# {EXP_ID}",
        "",
        "## Scope",
        "",
        "This is a screen-grade deployable selector extension. It only uses features computable from the target genome and anchor identity; target TE annotations are excluded.",
        "",
        "## Feature Sources",
        "",
        f"- Anchor-performance rows: {len(pair)} from `PIPE-TEFM-FINAL-SELECTOR-20260630/anchor_performance_matrix.tsv`.",
        f"- Species genome rows with features: {len(species_df)}.",
        f"- Sampled k-mer setting: k={k}, bounded prefix-stream max sampled bases/species={max_sample_bases}. This is a fast screen proxy, not a Mash/sourmash replacement.",
        f"- `mash`: {mash_status}; `sourmash`: {sourmash_status}. No Mash/sourmash distances were used in this run.",
        "",
        "## Selector Result",
        "",
        f"- Baseline deployable leave-species-out RMSE: {base:.4f}.",
        f"- Best genome-derived feature set: `{best_name}` with leave-species-out RMSE {best:.4f}.",
        f"- Delta vs baseline: {best - base:+.4f} RMSE.",
        "",
        "## Interpretation",
        "",
        "- Assembly statistics and sampled k-mer shift are valid deployable variables because they can be computed before TE annotation.",
        "- This run is a speed-first prototype: k-mer vectors use bounded prefix-stream sampling, while claim-grade work should use genome-wide MinHash/Mash/sourmash or indexed stratified sampling.",
        "- If the best delta is small or positive, the current screen does not yet justify a claim-grade selector formula; it instead supports reporting anchor families plus uncertainty.",
        "- Mash/sourmash and public phylogenetic matrices remain useful next additions, but should be installed/versioned before being treated as claim-grade evidence.",
        "",
        "## Outputs",
        "",
        "- `genome_feature_table.tsv`",
        "- `anchor_pair_genome_features.tsv`",
        "- `selector_genome_feature_results.json`",
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "GENOME_DECAY_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    k = 4
    max_sample_bases = 1_000_000
    perf = pd.read_csv(PERF_PATH, sep="\t")
    species_df, species_vecs, proto_vecs = build_feature_tables(k=k, max_sample_bases=max_sample_bases)
    pair = add_pair_features(perf, species_df, species_vecs, proto_vecs)
    results = evaluate_selector(pair)
    species_df.to_csv(OUT_DIR / "genome_feature_table.tsv", sep="\t", index=False)
    pair.to_csv(OUT_DIR / "anchor_pair_genome_features.tsv", sep="\t", index=False)
    (OUT_DIR / "selector_genome_feature_results.json").write_text(json.dumps(results, indent=2) + "\n")
    write_report(pair, species_df, results, OUT_DIR, k=k, max_sample_bases=max_sample_bases)
    status = {
        "ok": True,
        "exp_id": EXP_ID,
        "n_species": int(len(species_df)),
        "n_anchor_rows": int(len(pair)),
        "mash_available": bool(shutil.which("mash")),
        "sourmash_available": bool(shutil.which("sourmash")),
        "outputs": {
            "features": str(OUT_DIR / "genome_feature_table.tsv"),
            "pair_features": str(OUT_DIR / "anchor_pair_genome_features.tsv"),
            "selector": str(OUT_DIR / "selector_genome_feature_results.json"),
            "report": str(OUT_DIR / "GENOME_DECAY_REPORT.md"),
        },
    }
    (OUT_DIR / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
