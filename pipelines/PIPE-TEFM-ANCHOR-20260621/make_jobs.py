#!/usr/bin/env python3
"""Generate command TSVs for PIPE-TEFM-ANCHOR-20260621."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

PIPE = Path("pipelines/PIPE-TEFM-ANCHOR-20260621")
SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617")
CALIB = Path("pipelines/PIPE-TEFM-CALIB-20260621")
EXT = Path("pipelines/PIPE-TEFM-EXTEND-20260620")


def q(s: str) -> str:
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def write_tsv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for name, cmd in rows:
            if "\t" in name or "\t" in cmd:
                raise ValueError(f"tab in row {name}")
            handle.write(f"{name}\t{cmd}\n")


def prep_eval(manifest: str, out_dir: Path, split: str, species: list[str], cfg: dict) -> str:
    qp = cfg["quick_profile"]
    return " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "eval",
        "--manifest", manifest,
        "--out-dir", str(out_dir),
        "--split", split,
        "--species", *species,
        "--window", str(cfg["window"]),
        "--step", str(cfg["window"]),
        "--max-windows-per-species", str(qp["eval_windows_per_species"]),
    ])


def train_binary(data_dir: Path, out_dir: Path, cfg: dict) -> str:
    qp = cfg["quick_profile"]
    return " ".join([
        "python3", str(SUPP / "te_token_task.py"), "train",
        "--model-path", cfg["model"]["pretrained_path"],
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
        "--max-steps", str(qp["max_steps"]),
        "--eval-steps", str(qp["eval_steps"]),
        "--max-eval-samples", str(qp["max_eval_samples"]),
        "--bf16",
        "--gradient-checkpointing",
    ])


def eval_binary(model_dir: str | Path, data_dir: Path, out_json: Path, cfg: dict, stage: str, species: str) -> str:
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


def cluster_cmd(fragments: Path, out_dir: Path, setting: str, cfg: dict, source: str) -> str:
    cmd = [
        "python3", str(EXT / "embedding_strict.py"), "cluster",
        "--fragments", str(fragments),
        "--setting", setting,
        "--out-dir", str(out_dir),
        "--source", source,
        "--label-level", "sf5_or_bg",
        "--batch-size", "8",
        "--max-records", str(cfg["quick_profile"]["embedding_max_records"]),
        "--contrastive-epochs", str(cfg["quick_profile"]["embedding_contrastive_epochs"]),
        "--seed", str(cfg["seed"]),
    ]
    if setting.startswith("A"):
        cmd += ["--model-path", cfg["model"]["pretrained_path"], "--model-kind", "base"]
    return " ".join(cmd)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-ANCHOR-20260621.yaml")
    ap.add_argument("--out-dir", default="configs/pipelines")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    root = Path(cfg["outputs"]["root"])
    reports = Path(cfg["outputs"]["reports"])
    qp = cfg["quick_profile"]
    prefix = cfg["pipeline_id"]

    prep = []
    train = []
    evals = []
    diag_extract = []
    emb_cluster = []
    sf5 = []
    formula = []
    summary = []

    insect_data = root / "data" / "insect_primary_4096"
    prep.append(("prep_insect_primary_train", " ".join([
        "python3", str(CALIB / "prepare_mixed_any.py"),
        "--manifest", cfg["manifests"]["animal_b"],
        "--out-dir", str(insect_data),
        "--species-split", "fruit_fly:fine_tune", "c_elegans:fine_tune", "western_honey_bee:eval_only",
        "--proportions-json", q(json.dumps(cfg["species"]["insect_primary_train"])),
        "--total-windows", str(qp["total_windows"]),
        "--window", str(cfg["window"]),
        "--step", str(cfg["window"]),
        "--seed", str(cfg["seed"]),
    ])))
    fine_eval = root / "data" / "insect_primary_eval_fine"
    stress_eval = root / "data" / "insect_primary_eval_stress"
    prep.append(("prep_insect_eval_fine", prep_eval(cfg["manifests"]["animal_b"], fine_eval, "fine_tune", cfg["species"]["insect_primary_eval_fine"], cfg)))
    prep.append(("prep_insect_eval_stress", prep_eval(cfg["manifests"]["animal_b"], stress_eval, "eval_only", cfg["species"]["insect_primary_eval_stress"], cfg)))

    train.append(("train_insect_primary", train_binary(insect_data, root / "runs" / "insect_primary_4096", cfg)))

    models = {
        "insect_primary": root / "runs" / "insect_primary_4096",
        "insect_no_beetle": cfg["model"]["insect_no_beetle_4096"],
        "animal_invert_boost": cfg["model"]["animal_invert_boost_4096"],
        "cross_supervised": cfg["model"]["cross_supervised_4096"],
    }
    for panel, base, species_list in [
        ("insect_fine", fine_eval, cfg["species"]["insect_primary_eval_fine"]),
        ("insect_stress", stress_eval, cfg["species"]["insect_primary_eval_stress"]),
    ]:
        for species in species_list:
            data_dir = base / species
            for name, model in models.items():
                evals.append((f"eval_{name}_{panel}_{species}",
                              eval_binary(model, data_dir, reports / "binary_eval" / name / panel / f"{species}.json", cfg, f"{name}_to_{panel}", species)))

    frag_root = root / "fragments"
    bg_main4 = frag_root / "bg_main4_len512.jsonl.gz"
    explore = frag_root / "unknown_highscore_len512.jsonl.gz"
    eval_roots = [
        str(Path(cfg["existing"]["calib_eval_data"]) / "cross_eval"),
        str(Path(cfg["existing"]["calib_eval_data"]) / "plant_eval_fine"),
        str(Path(cfg["existing"]["calib_eval_data"]) / "plant_eval_only"),
        str(fine_eval),
        str(stress_eval),
    ]
    diag_extract.append(("extract_bg_unknown_highscore", " ".join([
        "python3", str(PIPE / "diagnose_fragments.py"), "extract",
        "--manifest", cfg["manifests"]["animal_b"], cfg["manifests"]["plant"], cfg["manifests"]["cross"],
        "--eval-root", *eval_roots,
        "--species", *cfg["species"]["diagnostic_species"],
        "--binary-model", cfg["model"]["cross_supervised_4096"],
        "--frag-len", str(cfg["fragment_len"]),
        "--max-per-label", str(qp["fragment_max_per_label"]),
        "--max-bg", str(qp["fragment_max_bg"]),
        "--max-unknown", str(qp["fragment_max_unknown"]),
        "--max-highscore", str(qp["fragment_max_highscore"]),
        "--highscore-threshold", str(qp["highscore_threshold"]),
        "--highscore-max-windows", str(qp["highscore_max_windows"]),
        "--seed", str(cfg["seed"]),
        "--out-bg-main4", str(bg_main4),
        "--out-bg-main4-meta", str(bg_main4.with_suffix(".metadata.json")),
        "--out-explore", str(explore),
        "--out-explore-meta", str(explore.with_suffix(".metadata.json")),
    ])))

    for fragments, name in [(bg_main4, "bg_main4"), (explore, "unknown_highscore")]:
        for setting in ["C0", "C1", "A0", "A1"]:
            emb_cluster.append((f"cluster_{name}_{setting}",
                                cluster_cmd(fragments, reports / "embedding" / name / setting, setting, cfg, name)))

    sf5.append(("predict_sf5_unknown_highscore", " ".join([
        "python3", str(PIPE / "diagnose_fragments.py"), "predict-sf5",
        "--fragments", str(explore),
        "--sf5-model", cfg["model"]["sf5_base_pretrained"],
        "--sources", "unknown_annotation", "high_score_strict_bg",
        "--out-tsv", str(reports / "sf5_candidate_predictions.tsv"),
        "--out-summary", str(reports / "sf5_candidate_summary.json"),
    ])))

    formula.append(("fit_anchor_formula", " ".join([
        "python3", str(PIPE / "anchor_formula.py"),
        "--calib-binary-eval", cfg["existing"]["calib_binary_eval"],
        "--lock-recovery", cfg["existing"]["lock_recovery"],
        "--repair-mixed", cfg["existing"]["repair_mixed"],
        "--extend-transfer", cfg["existing"]["extend_transfer"],
        "--new-eval-root", str(reports / "binary_eval"),
        "--concordance", cfg["manifests"]["concordance"],
        "--eval-data-root", *eval_roots,
        "--out-dir", str(reports / "anchor_formula"),
    ])))
    summary.append(("summarize_anchor", " ".join([
        "python3", str(PIPE / "summarize_results.py"),
        "--config", args.config,
    ])))

    for suffix, rows in [
        ("prep_jobs", prep),
        ("train_jobs", train),
        ("eval_jobs", evals),
        ("diag_extract_jobs", diag_extract),
        ("embedding_cluster_jobs", emb_cluster),
        ("sf5_jobs", sf5),
        ("formula_jobs", formula),
        ("summarize_jobs", summary),
    ]:
        write_tsv(Path(args.out_dir) / f"{prefix}.{suffix}.tsv", rows)
    print(json.dumps({
        "prep": len(prep), "train": len(train), "eval": len(evals),
        "diag_extract": len(diag_extract), "embedding_cluster": len(emb_cluster),
        "sf5": len(sf5), "formula": len(formula), "summarize": len(summary),
    }, indent=2))


if __name__ == "__main__":
    main()
