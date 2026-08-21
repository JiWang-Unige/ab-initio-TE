#!/usr/bin/env python3
"""Generate command TSVs for PIPE-TEFM-EXTEND-20260620."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

PIPE = Path("pipelines/PIPE-TEFM-EXTEND-20260620")
SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617")
LOCK = Path("pipelines/PIPE-TEFM-LOCK-20260619")
SEG = Path("pipelines/PIPE-TEFM-SEG-SF-20260618")


def q(s: str) -> str:
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def write_tsv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for name, cmd in rows:
            if "\t" in name or "\t" in cmd:
                raise ValueError(f"tab not allowed in job row {name}")
            handle.write(f"{name}\t{cmd}\n")


def prep_eval_cmd(manifest: str, out_dir: Path, split: str, species: list[str], window: int, max_windows: int) -> str:
    return " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "eval",
        "--manifest", manifest,
        "--out-dir", str(out_dir),
        "--split", split,
        "--species", *species,
        "--window", str(window),
        "--step", str(window),
        "--max-windows-per-species", str(max_windows),
    ])


def train_binary_cmd(data_dir: Path, out_dir: Path, init: str, cfg: dict, steps: int, eval_steps: int) -> str:
    return " ".join([
        "python3", str(SUPP / "te_token_task.py"), "train",
        "--model-path", init,
        "--kind", "auto_token",
        "--token-label-mode", "single_nt",
        "--data-dir", str(data_dir),
        "--output-dir", str(out_dir),
        "--window", str(cfg["window"]),
        "--seed", str(cfg["seed"]),
        "--batch-size", "1",
        "--grad-accum", "16",
        "--learning-rate", "2e-5",
        "--te-class-weight", "3.0",
        "--max-steps", str(steps),
        "--eval-steps", str(eval_steps),
        "--max-eval-samples", str(cfg["quick_profile"]["max_eval_samples"]),
        "--bf16",
        "--gradient-checkpointing",
    ])


def train_pu_cmd(data_dir: Path, out_dir: Path, init: str, cfg: dict, u_penalty: float, tv_weight: float, steps: int) -> str:
    return " ".join([
        "python3", str(PIPE / "pu_token_task.py"), "train",
        "--init-checkpoint", init,
        "--data-dir", str(data_dir),
        "--output-dir", str(out_dir),
        "--window", str(cfg["window"]),
        "--seed", str(cfg["seed"]),
        "--batch-size", "1",
        "--grad-accum", "16",
        "--learning-rate", "2e-5",
        "--te-class-weight", "3.0",
        "--u-penalty", str(u_penalty),
        "--tv-weight", str(tv_weight),
        "--max-steps", str(steps),
        "--eval-steps", str(cfg["quick_profile"]["pu_eval_steps"]),
        "--max-eval-samples", str(cfg["quick_profile"]["max_eval_samples"]),
        "--bf16",
        "--gradient-checkpointing",
    ])


def eval_binary_cmd(model_dir: str | Path, data_dir: Path, out_json: Path, cfg: dict, stage: str, species: str) -> str:
    return " ".join([
        "python3", str(SUPP / "te_token_task.py"), "eval",
        "--model-dir", str(model_dir),
        "--data-dir", str(data_dir),
        "--out-json", str(out_json),
        "--batch-size", "1",
        "--max-samples", str(cfg["quick_profile"]["max_eval_samples"]),
        "--stage", stage,
        "--model-key", "generanno",
        "--model", Path(str(model_dir)).name,
        "--window", str(cfg["window"]),
        "--species", species,
    ])


def eval_pu_cmd(model_dir: Path, data_dir: Path, out_json: Path, cfg: dict, stage: str, species: str) -> str:
    return " ".join([
        "python3", str(PIPE / "pu_token_task.py"), "eval",
        "--model-dir", str(model_dir),
        "--data-dir", str(data_dir),
        "--out-json", str(out_json),
        "--window", str(cfg["window"]),
        "--batch-size", "1",
        "--max-samples", str(cfg["quick_profile"]["max_eval_samples"]),
        "--stage", stage,
        "--species", species,
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-EXTEND-20260620.yaml")
    ap.add_argument("--out-dir", default="configs/pipelines")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    root = Path(cfg["outputs"]["root"])
    reports = Path(cfg["outputs"]["reports"])
    window = int(cfg["window"])
    qp = cfg["quick_profile"]
    model = cfg["model"]

    prep: list[tuple[str, str]] = []
    train: list[tuple[str, str]] = []
    evals: list[tuple[str, str]] = []
    segment: list[tuple[str, str]] = []
    embed_extract: list[tuple[str, str]] = []
    embed_cluster: list[tuple[str, str]] = []
    formula: list[tuple[str, str]] = []
    summary: list[tuple[str, str]] = []

    plant_eval_fine = root / "data" / "plant_eval_fine"
    plant_eval_only = root / "data" / "plant_eval_only"
    cross_eval = root / "data" / "cross_eval"
    stress_eval = root / "data" / "stress_eval"
    prep.append(("prep_plant_eval_fine", prep_eval_cmd(cfg["manifests"]["plant"], plant_eval_fine, "fine_tune", cfg["species"]["plant_fine_eval"], window, qp["eval_windows_per_species"])))
    prep.append(("prep_plant_eval_only", prep_eval_cmd(cfg["manifests"]["plant"], plant_eval_only, "eval_only", cfg["species"]["plant_eval_only"], window, qp["eval_windows_per_species"])))
    prep.append(("prep_cross_eval", prep_eval_cmd(cfg["manifests"]["cross"], cross_eval, "eval_only", cfg["species"]["cross_eval"], window, qp["eval_windows_per_species"])))
    prep.append(("prep_stress_eval", prep_eval_cmd(cfg["manifests"]["animal_b"], stress_eval, "eval_only", cfg["species"]["stress_eval"], window, qp["eval_windows_per_species"])))

    plant_pu = root / "data" / "plant_pu_positive"
    prep.append(("prep_plant_pu_positive", " ".join([
        "python3", str(PIPE / "prepare_pu_windows.py"),
        "--manifest", cfg["manifests"]["plant"],
        "--out-dir", str(plant_pu),
        "--species", *cfg["species"]["plant_train"],
        "--window", str(window),
        "--train-windows", str(qp["pu_train_windows"]),
        "--val-windows", str(qp["pu_val_windows"]),
        "--seed", str(cfg["seed"]),
    ])))
    cross_pu = root / "data" / "cross_pu_positive"
    prep.append(("prep_cross_pu_positive", " ".join([
        "python3", str(PIPE / "prepare_pu_windows.py"),
        "--manifest", cfg["manifests"]["cross"],
        "--out-dir", str(cross_pu),
        "--species", *cfg["species"]["cross_train"],
        "--proportions-json", q(json.dumps(cfg["mixtures"]["cross_kingdom_50_50"])),
        "--window", str(window),
        "--train-windows", str(qp["pu_train_windows"]),
        "--val-windows", str(qp["pu_val_windows"]),
        "--seed", str(cfg["seed"]),
    ])))
    for name, props in cfg["mixtures"]["stress_anchors"].items():
        prep.append((f"prep_anchor_{name}", " ".join([
            "python3", str(SUPP / "prepare_ucsc_windows.py"), "mixed",
            "--manifest", cfg["manifests"]["animal_b"],
            "--out-dir", str(root / "data" / f"anchor_{name}"),
            "--window", str(window),
            "--step", str(window),
            "--proportions-json", q(json.dumps(props)),
            "--total-windows", str(qp["anchor_total_windows"]),
            "--seed", str(cfg["seed"]),
        ])))

    # SF5 base-pretrained replicate/continuation.
    sf5_data = root / "data" / "animal_sf5_w4096"
    prep.append(("prep_sf5_base", " ".join([
        "python3", str(LOCK / "prepare_superfamily5_data.py"),
        "--manifest", cfg["manifests"]["animal_b"],
        "--out-dir", str(sf5_data),
        "--species", *cfg["species"]["sf5_train"],
        "--window", str(window),
        "--step", str(window),
        "--max-train-per-species", str(qp["sf5_train_per_species"]),
        "--max-val-per-species", str(qp["sf5_val_per_species"]),
        "--max-test-per-species", str(qp["sf5_test_per_species"]),
    ])))

    # Embedding strict fragments.
    for panel, manifest in [("B_animal", cfg["manifests"]["animal_b"]), ("D_cross", cfg["manifests"]["cross"])]:
        for source in ["genomic_internal", "genomic_boundary"]:
            frag = root / "embedding_fragments" / panel / source / "family_len512.jsonl.gz"
            embed_extract.append((f"extract_{panel}_{source}_family512", " ".join([
                "python3", str(PIPE / "embedding_strict.py"), "extract-genomic",
                "--manifest", manifest,
                "--out-jsonl", str(frag),
                "--out-meta", str(frag.with_suffix(".metadata.json")),
                "--source", source,
                "--label-level", "family",
                "--length", "512",
                "--top-labels", str(qp["embedding_top_families"]),
                "--max-per-label", str(qp["embedding_max_per_label"]),
                "--min-per-label", str(qp["embedding_min_per_label"]),
                "--seed", str(cfg["seed"]),
            ])))
    cons_frag = root / "embedding_fragments" / "Dfam_consensus" / "family_len512.jsonl.gz"
    cons_cmd = [
        "python3", str(PIPE / "embedding_strict.py"), "extract-consensus",
        "--out-jsonl", str(cons_frag),
        "--out-meta", str(cons_frag.with_suffix(".metadata.json")),
        "--label-level", "family",
        "--length", "512",
        "--top-labels", str(qp["embedding_top_families"]),
        "--max-per-label", str(qp["embedding_max_per_label"]),
        "--min-per-label", str(qp["embedding_min_per_label"]),
        "--seed", str(cfg["seed"]),
    ]
    if cfg.get("dfam_consensus_fasta"):
        cons_cmd[3:3] = ["--consensus-fasta", str(cfg["dfam_consensus_fasta"])]
    embed_extract.append(("extract_dfam_consensus_family512", " ".join(cons_cmd)))

    # Training.
    plant_models = {
        "plant_base_pu": (model["pretrained_path"], 0.10, 0.00),
        "plant_from_invert_pu": (str(Path(model["invert_boost_4096"]) / "best_model"), 0.10, 0.00),
        "plant_from_invert_pu_tv": (str(Path(model["invert_boost_4096"]) / "best_model"), 0.15, 0.05),
        "plant_from_invert_positive_only": (str(Path(model["invert_boost_4096"]) / "best_model"), 0.00, 0.00),
    }
    for name, (init, u_pen, tv) in plant_models.items():
        train.append((f"train_{name}", train_pu_cmd(plant_pu, root / "runs" / name, init, cfg, u_pen, tv, qp["pu_max_steps"])))
    train.append(("train_cross_kingdom_pu", train_pu_cmd(cross_pu, root / "runs" / "cross_kingdom_pu", model["pretrained_path"], cfg, 0.10, 0.03, qp["pu_max_steps"])))
    for name in cfg["mixtures"]["stress_anchors"]:
        train.append((f"train_anchor_{name}", train_binary_cmd(root / "data" / f"anchor_{name}", root / "runs" / f"anchor_{name}", model["pretrained_path"], cfg, qp["anchor_max_steps"], qp["anchor_eval_steps"])))
    train.append(("train_sf5_base_pretrained", " ".join([
        "python3", str(LOCK / "superfamily5_task.py"), "train",
        "--init-checkpoint", model["pretrained_path"],
        "--data-dir", str(sf5_data),
        "--output-dir", str(root / "runs" / "sf5_base_pretrained"),
        "--window", str(window),
        "--stage", "sf5_base_pretrained_extend",
        "--seed", str(cfg["seed"]),
        "--max-steps", str(qp["sf5_max_steps"]),
        "--eval-steps", str(qp["sf5_eval_steps"]),
        "--max-eval-samples", str(qp["max_eval_samples"]),
        "--batch-size", "1",
        "--grad-accum", "16",
        "--bf16",
        "--gradient-checkpointing",
    ])))

    # Baseline animal model on plants.
    for panel, base in [("plant_fine", plant_eval_fine), ("plant_eval", plant_eval_only)]:
        for species in cfg["species"]["plant_fine_eval" if panel == "plant_fine" else "plant_eval_only"]:
            data_dir = base / species
            evals.append((f"eval_invert_to_{panel}_{species}", eval_binary_cmd(model["invert_boost_4096"], data_dir, reports / "plant_transfer" / "invert_boost" / panel / f"{species}.json", cfg, f"invert_to_{panel}", species)))
            for m in plant_models:
                evals.append((f"eval_{m}_to_{panel}_{species}", eval_pu_cmd(root / "runs" / m, data_dir, reports / "plant_transfer" / m / panel / f"{species}.json", cfg, f"{m}_to_{panel}", species)))
            evals.append((f"eval_cross_to_{panel}_{species}", eval_pu_cmd(root / "runs" / "cross_kingdom_pu", data_dir, reports / "plant_transfer" / "cross_kingdom_pu" / panel / f"{species}.json", cfg, f"cross_to_{panel}", species)))

    # Cross-kingdom eval against animal and plant heldouts.
    for species in cfg["species"]["cross_eval"]:
        data_dir = cross_eval / species
        evals.append((f"eval_invert_cross_{species}", eval_binary_cmd(model["invert_boost_4096"], data_dir, reports / "cross_eval" / "invert_boost" / f"{species}.json", cfg, "invert_cross_eval", species)))
        evals.append((f"eval_cross_cross_{species}", eval_pu_cmd(root / "runs" / "cross_kingdom_pu", data_dir, reports / "cross_eval" / "cross_kingdom_pu" / f"{species}.json", cfg, "cross_kingdom_eval", species)))
        evals.append((f"eval_plant_cross_{species}", eval_pu_cmd(root / "runs" / "plant_from_invert_pu_tv", data_dir, reports / "cross_eval" / "plant_from_invert_pu_tv" / f"{species}.json", cfg, "plant_model_cross_eval", species)))

    # Stress anchor eval.
    for species in cfg["species"]["stress_eval"]:
        data_dir = stress_eval / species
        evals.append((f"eval_stress_baseline_{species}", eval_binary_cmd(model["invert_boost_4096"], data_dir, reports / "stress_anchor" / "invert_boost" / f"{species}.json", cfg, "stress_baseline", species)))
        for anchor in cfg["mixtures"]["stress_anchors"]:
            evals.append((f"eval_anchor_{anchor}_{species}", eval_binary_cmd(root / "runs" / f"anchor_{anchor}", data_dir, reports / "stress_anchor" / anchor / f"{species}.json", cfg, f"anchor_{anchor}", species)))

    # Segment checks for PU/smoothing on plant eval.
    for model_name in ["plant_from_invert_positive_only", "plant_from_invert_pu", "plant_from_invert_pu_tv"]:
        for species in cfg["species"]["plant_eval_only"]:
            segment.append((f"segment_{model_name}_{species}", " ".join([
                "python3", str(SEG / "bp_overlap_segment_eval.py"),
                "--exp-id", cfg["pipeline_id"],
                "--model-dir", str(root / "runs" / model_name),
                "--data-jsonl", str(plant_eval_only / species / "test" / "data.jsonl.gz"),
                "--out-dir", str(reports / "pu_segment" / model_name / species),
                "--window", str(window),
                "--stride", str(window),
                "--threshold", "0.35",
                "--max-windows", str(qp["segment_max_windows"]),
            ])))

    # Embedding clusters.
    fragment_roots = [
        ("B_animal", "genomic_internal", root / "embedding_fragments" / "B_animal" / "genomic_internal" / "family_len512.jsonl.gz"),
        ("B_animal", "genomic_boundary", root / "embedding_fragments" / "B_animal" / "genomic_boundary" / "family_len512.jsonl.gz"),
        ("D_cross", "genomic_internal", root / "embedding_fragments" / "D_cross" / "genomic_internal" / "family_len512.jsonl.gz"),
        ("D_cross", "genomic_boundary", root / "embedding_fragments" / "D_cross" / "genomic_boundary" / "family_len512.jsonl.gz"),
        ("Dfam_consensus", "dfam_consensus", cons_frag),
    ]
    settings = [
        ("C0", "", "base"),
        ("C1", "", "base"),
        ("A0", model["pretrained_path"], "base"),
        ("A1", model["pretrained_path"], "base"),
    ]
    for panel, source, frag in fragment_roots:
        for setting, model_path, kind in settings:
            cmd = [
                "python3", str(PIPE / "embedding_strict.py"), "cluster",
                "--fragments", str(frag),
                "--setting", setting,
                "--out-dir", str(reports / "embedding_strict" / panel / source / setting),
                "--source", source,
                "--label-level", "family",
                "--batch-size", "8",
                "--max-records", str(qp["embedding_max_records"]),
                "--contrastive-epochs", "120",
                "--seed", str(cfg["seed"]),
            ]
            if model_path:
                cmd += ["--model-path", model_path, "--model-kind", kind]
            embed_cluster.append((f"cluster_{panel}_{source}_{setting}", " ".join(cmd)))

    formula.append(("fit_decay_formula", " ".join([
        "python3", str(PIPE / "fit_decay_formula.py"),
        "--lock-recovery", "reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/recovery_eval.tsv",
        "--repair-mixed", "reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/mixed_eval.tsv",
        "--new-eval-root", str(reports),
        "--concordance", cfg["manifests"]["concordance"],
        "--out-dir", str(reports / "decay_formula"),
    ])))
    summary.append(("summarize", " ".join(["python3", str(PIPE / "summarize_results.py"), "--config", args.config])))

    out = Path(args.out_dir)
    prefix = cfg["pipeline_id"]
    for suffix, rows in [
        ("prep_jobs", prep),
        ("train_jobs", train),
        ("eval_jobs", evals),
        ("segment_jobs", segment),
        ("embedding_extract_jobs", embed_extract),
        ("embedding_cluster_jobs", embed_cluster),
        ("formula_jobs", formula),
        ("summarize_jobs", summary),
    ]:
        write_tsv(out / f"{prefix}.{suffix}.tsv", rows)
    print(json.dumps({k: len(v) for k, v in {
        "prep": prep,
        "train": train,
        "eval": evals,
        "segment": segment,
        "embedding_extract": embed_extract,
        "embedding_cluster": embed_cluster,
        "formula": formula,
        "summarize": summary,
    }.items()}, indent=2))


if __name__ == "__main__":
    main()
