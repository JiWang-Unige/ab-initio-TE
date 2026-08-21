#!/usr/bin/env python3
"""Generate command TSVs for PIPE-TEFM-LOCK-20260619."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

PIPE = Path("pipelines/PIPE-TEFM-LOCK-20260619")
SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617")
SEG = Path("pipelines/PIPE-TEFM-SEG-SF-20260618")
REPAIR = Path("pipelines/PIPE-TEFM-REPAIR-20260618")


def q(s: str) -> str:
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def write_tsv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for name, cmd in rows:
            handle.write(f"{name}\t{cmd}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-LOCK-20260619.yaml")
    ap.add_argument("--out-dir", default="configs/pipelines")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    root = Path(cfg["outputs"]["root"])
    reports = Path(cfg["outputs"]["reports"])
    seed = int(cfg["seed"])
    window = int(cfg["window"])
    stride = int(cfg["stride"])
    qp = cfg["quick_profile"]
    prep: list[tuple[str, str]] = []
    train: list[tuple[str, str]] = []
    evals: list[tuple[str, str]] = []
    segment: list[tuple[str, str]] = []
    embedding: list[tuple[str, str]] = []
    summary: list[tuple[str, str]] = []

    recovery_data = root / "data" / "stress_recovery"
    prep.append(("prep_stress_recovery", " ".join([
        "python3", str(PIPE / "stress_recovery_data.py"),
        "--manifest", cfg["manifests"]["stress_pool"],
        "--out-dir", str(recovery_data),
        "--species", *cfg["species"]["recovery"],
        "--window", str(window),
        "--step", str(window),
        "--max-train-windows", str(qp["recovery_max_train_windows"]),
        "--max-val-windows", str(qp["recovery_max_val_windows"]),
        "--max-test-windows", str(qp["recovery_max_test_windows"]),
    ])))

    sf5_data = root / "data" / "animal_sf5_w4096"
    prep.append(("prep_sf5_animal", " ".join([
        "python3", str(PIPE / "prepare_superfamily5_data.py"),
        "--manifest", cfg["manifests"]["animal_b"],
        "--out-dir", str(sf5_data),
        "--species", *cfg["species"]["sf5_train"],
        "--window", str(window),
        "--step", str(window),
        "--max-train-per-species", str(qp["sf5_max_train_per_species"]),
        "--max-val-per-species", str(qp["sf5_max_val_per_species"]),
        "--max-test-per-species", str(qp["sf5_max_test_per_species"]),
    ])))

    # Segment datasets: one held-out chromosome per species, with overlap stride.
    for species in cfg["species"]["primary_segment"]:
        out = root / "data" / "segment_primary" / species
        prep.append((f"prep_segment_primary_{species}", " ".join([
            "python3", str(SUPP / "prepare_ucsc_windows.py"), "eval",
            "--manifest", cfg["manifests"]["animal_b"],
            "--out-dir", str(out.parent),
            "--split", "fine_tune",
            "--species", species,
            "--window", str(window),
            "--step", str(stride),
            "--max-windows-per-species", str(qp["segment_max_windows"]),
        ])))
    for species in cfg["species"]["stress_segment"]:
        out = root / "data" / "segment_stress" / species
        prep.append((f"prep_segment_stress_{species}", " ".join([
            "python3", str(SUPP / "prepare_ucsc_windows.py"), "eval",
            "--manifest", cfg["manifests"]["stress_pool"],
            "--out-dir", str(out.parent),
            "--split", "eval_only",
            "--species", species,
            "--window", str(window),
            "--step", str(stride),
            "--max-windows-per-species", str(qp["segment_max_windows"]),
        ])))

    prep.append(("stress_panel_audit", " ".join([
        "python3", str(PIPE / "stress_panel_audit.py"),
        "--mixed-eval", cfg["manifests"]["mixed_eval"],
        "--concordance", cfg["manifests"]["concordance"],
        "--out-tsv", str(reports / "summaries" / "stress_panel_audit.tsv"),
    ])))

    # Stress recovery: start from current invert-boost branch, then compare before/after.
    for species in cfg["species"]["recovery"]:
        data_dir = recovery_data / species
        out_dir = root / "runs" / f"RECOVERY_{species}_from_invert_seed42"
        train.append((f"train_recovery_{species}", " ".join([
            "python3", str(SUPP / "te_token_task.py"), "train",
            "--model-path", str(Path(cfg["model"]["invert_boost_4096"]) / "best_model"),
            "--kind", "auto_token",
            "--token-label-mode", "single_nt",
            "--data-dir", str(data_dir),
            "--output-dir", str(out_dir),
            "--window", str(window),
            "--seed", str(seed),
            "--batch-size", "1",
            "--grad-accum", "16",
            "--learning-rate", "2e-5",
            "--te-class-weight", "3.0",
            "--max-steps", str(qp["recovery_max_steps"]),
            "--eval-steps", str(qp["recovery_eval_steps"]),
            "--max-eval-samples", str(qp["max_eval_samples"]),
            "--bf16",
            "--gradient-checkpointing",
        ])))
        evals.append((f"eval_recovery_baseline_{species}", " ".join([
            "python3", str(SUPP / "te_token_task.py"), "eval",
            "--model-dir", cfg["model"]["invert_boost_4096"],
            "--data-dir", str(data_dir),
            "--out-json", str(reports / "recovery_eval" / species / "baseline_invert_boost.json"),
            "--batch-size", "1",
            "--max-samples", str(qp["max_eval_samples"]),
            "--stage", "stress_recovery_baseline",
            "--model-key", "generanno",
            "--model", "invert_boost_animal_4096",
            "--window", str(window),
            "--species", species,
        ])))
        evals.append((f"eval_recovery_adapted_{species}", " ".join([
            "python3", str(SUPP / "te_token_task.py"), "eval",
            "--model-dir", str(out_dir),
            "--data-dir", str(data_dir),
            "--out-json", str(reports / "recovery_eval" / species / "adapted_same_species.json"),
            "--batch-size", "1",
            "--max-samples", str(qp["max_eval_samples"]),
            "--stage", "stress_recovery_adapted",
            "--model-key", "generanno",
            "--model", f"recovery_{species}",
            "--window", str(window),
            "--species", species,
        ])))

    # Main4+Unknown token head: base init vs binary-init.
    sf5_inits = [
        ("base_pretrained", cfg["model"]["pretrained_path"]),
        ("binary_h0", str(Path(cfg["model"]["binary_h0_4096"]) / "best_model")),
    ]
    for name, init in sf5_inits:
        train.append((f"train_sf5_{name}", " ".join([
            "python3", str(PIPE / "superfamily5_task.py"), "train",
            "--init-checkpoint", init,
            "--data-dir", str(sf5_data),
            "--output-dir", str(root / "runs" / f"SF5_{name}_seed42"),
            "--window", str(window),
            "--stage", f"animal_sf5_{name}",
            "--seed", str(seed),
            "--max-steps", str(qp["sf5_max_steps"]),
            "--eval-steps", str(qp["sf5_eval_steps"]),
            "--max-eval-samples", str(qp["max_eval_samples"]),
            "--batch-size", "1",
            "--grad-accum", "16",
            "--bf16",
            "--gradient-checkpointing",
        ])))

    # Segment multi-species postprocess validation with current invert-boost model.
    for panel, species_list in [("primary", cfg["species"]["primary_segment"]), ("stress", cfg["species"]["stress_segment"])]:
        data_base = root / "data" / f"segment_{panel}"
        for species in species_list:
            segment.append((f"segment_{panel}_{species}", " ".join([
                "python3", str(SEG / "bp_overlap_segment_eval.py"),
                "--exp-id", cfg["pipeline_id"],
                "--model-dir", cfg["model"]["invert_boost_4096"],
                "--data-jsonl", str(data_base / species / "test" / "data.jsonl.gz"),
                "--out-dir", str(reports / "segment_multi_species" / panel / species),
                "--window", str(window),
                "--stride", str(stride),
                "--threshold", "0.35",
                "--max-windows", str(qp["segment_max_windows"]),
            ])))

    # Sequence-level superfamily classifier/probe via embedding diagnostic.
    frag = "software_outputs/tefm_repair/PIPE-TEFM-REPAIR-20260618/embedding_fragments/B_animal/fragments_512.jsonl.gz"
    settings = [
        ("C0_basic_seq", "C0", "", "base"),
        ("C1_basic_seq_contrastive", "C1", "", "base"),
        ("A0_pretrained", "A0", cfg["model"]["pretrained_path"], "base"),
        ("A1_pretrained_contrastive", "A1", cfg["model"]["pretrained_path"], "base"),
        ("B0_binary_h0", "B0", str(Path(cfg["model"]["binary_h0_4096"]) / "best_model"), "token"),
        ("B1_binary_h0_contrastive", "B1", str(Path(cfg["model"]["binary_h0_4096"]) / "best_model"), "token"),
    ]
    for name, setting, model_path, kind in settings:
        cmd = [
            "python3", str(REPAIR / "embedding_diagnostic.py"),
            "--fragments", frag,
            "--setting", setting,
            "--out-dir", str(reports / "embedding_objective" / "B_animal_len512" / name),
            "--seed", str(seed),
            "--batch-size", "8",
            "--max-records", str(qp["embedding_max_records"]),
            "--contrastive-epochs", "160",
        ]
        if model_path:
            cmd += ["--model-path", model_path, "--model-kind", kind]
        embedding.append((f"embed_obj_{name}", " ".join(cmd)))

    summary.append(("summarize", " ".join([
        "python3", str(PIPE / "summarize_results.py"),
        "--config", args.config,
    ])))

    out = Path(args.out_dir)
    prefix = cfg["pipeline_id"]
    for suffix, rows in [
        ("prep_jobs", prep),
        ("train_jobs", train),
        ("eval_jobs", evals),
        ("segment_jobs", segment),
        ("embedding_jobs", embedding),
        ("summarize_jobs", summary),
    ]:
        write_tsv(out / f"{prefix}.{suffix}.tsv", rows)
    print(json.dumps({k: len(v) for k, v in {
        "prep": prep, "train": train, "eval": evals, "segment": segment, "embedding": embedding, "summarize": summary,
    }.items()}, indent=2))


if __name__ == "__main__":
    main()
