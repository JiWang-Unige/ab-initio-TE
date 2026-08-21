#!/usr/bin/env python3
"""Generate command TSVs for PIPE-TEFM-FINAL-20260623."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

PIPE = Path("pipelines/PIPE-TEFM-FINAL-20260623")
SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617")
CALIB = Path("pipelines/PIPE-TEFM-CALIB-20260621")


def q(s: object) -> str:
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def write_tsv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for name, cmd in rows:
            if "\t" in name or "\t" in cmd:
                raise ValueError(f"tab in job row {name}")
            handle.write(f"{name}\t{cmd}\n")


def env_prefix(model_cfg: dict) -> str:
    if model_cfg.get("local_files_only", True):
        return "TEFM_LOCAL_FILES_ONLY=1"
    return "TEFM_LOCAL_FILES_ONLY=0 HF_HOME=/home/users/j/jwang/ab-initio-TE/.cache/huggingface"


def prep_human(manifest: str, out_dir: Path, window: int, cfg: dict) -> str:
    qp = cfg["quick_profile"]
    return " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "human",
        "--manifest", q(manifest),
        "--out-dir", q(out_dir),
        "--species", "human",
        "--window", str(window),
        "--step", str(window),
        "--max-windows-per-split", str(qp["max_train_windows_per_split"]),
    ])


def prep_eval(manifest: str, out_dir: Path, split: str, species: list[str], window: int, cfg: dict) -> str:
    qp = cfg["quick_profile"]
    return " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "eval",
        "--manifest", q(manifest),
        "--out-dir", q(out_dir),
        "--split", split,
        "--species", *species,
        "--window", str(window),
        "--step", str(window),
        "--max-windows-per-species", str(qp["max_eval_windows_per_species"]),
    ])


def train_cmd(model_key: str, model_cfg: dict, window: int, data_dir: Path, out_dir: Path, cfg: dict, seed: int | None = None) -> str:
    qp = cfg["quick_profile"]
    return " ".join([
        env_prefix(model_cfg),
        "python3", str(SUPP / "te_token_task.py"), "train",
        "--model-path", q(model_cfg["path"]),
        "--kind", model_cfg["kind"],
        "--token-label-mode", model_cfg["token_label_mode"],
        "--data-dir", q(data_dir),
        "--output-dir", q(out_dir),
        "--window", str(window),
        "--seed", str(seed if seed is not None else cfg["seed"]),
        "--batch-size", str(model_cfg.get("batch_size", 1)),
        "--grad-accum", str(model_cfg.get("grad_accum", 16)),
        "--learning-rate", "2e-5",
        "--te-class-weight", str(qp["te_class_weight"]),
        "--max-steps", str(qp["max_steps"]),
        "--eval-steps", str(qp["eval_steps"]),
        "--max-eval-samples", str(qp["max_eval_samples"]),
        "--bf16",
    ])


def eval_cmd(model_dir: Path | str, data_dir: Path, out_json: Path, model_key: str, window: int, cfg: dict, species: str, stage: str, env: str = "") -> str:
    prefix = [env] if env else []
    return " ".join([
        *prefix,
        "python3", str(SUPP / "te_token_task.py"), "eval",
        "--model-dir", q(model_dir),
        "--data-dir", q(data_dir),
        "--out-json", q(out_json),
        "--batch-size", "1",
        "--max-samples", str(cfg["quick_profile"]["max_eval_samples"]),
        "--stage", stage,
        "--model-key", model_key,
        "--model", Path(str(model_dir)).name,
        "--window", str(window),
        "--species", species,
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-FINAL-20260623.yaml")
    ap.add_argument("--out-dir", default="configs/pipelines")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    root = Path(cfg["outputs"]["root"])
    reports = Path(cfg["outputs"]["reports"])
    prefix = cfg["pipeline_id"]
    qp = cfg["quick_profile"]

    download: list[tuple[str, str]] = []
    smoke: list[tuple[str, str]] = []
    prep: list[tuple[str, str]] = []
    train: list[tuple[str, str]] = []
    evals: list[tuple[str, str]] = []
    species_probe_prep: list[tuple[str, str]] = []
    species_probe_train: list[tuple[str, str]] = []
    species_probe_eval: list[tuple[str, str]] = []
    strict_segment: list[tuple[str, str]] = []
    summary: list[tuple[str, str]] = []

    for model_key, model_cfg in cfg["models"].items():
        download.append((f"download_{model_key}", " ".join([
            "python3", str(PIPE / "download_snapshot.py"),
            "--repo-id", q(model_cfg["repo_id"]),
            "--local-dir", q(model_cfg["path"]),
            "--out-json", q(reports / "download" / f"{model_key}.json"),
        ])))
        smoke.append((f"smoke_{model_key}", " ".join([
            env_prefix(model_cfg),
            "python3", str(SUPP / "te_token_task.py"), "smoke",
            "--model-path", q(model_cfg["path"]),
            "--kind", model_cfg["kind"],
            "--out-json", q(reports / "smoke" / f"{model_key}.json"),
        ])))

    for window in cfg["windows"]:
        prep.append((f"prep_human_w{window}", prep_human(cfg["manifests"]["human_h0"], root / "data" / f"human_h0_w{window}", window, cfg)))
        prep.append((f"prep_animal_fine_w{window}", prep_eval(cfg["manifests"]["animal_b"], root / "data" / f"animal_fine_w{window}", "fine_tune", cfg["species"]["animal_fine"], window, cfg)))
        prep.append((f"prep_plant_fine_w{window}", prep_eval(cfg["manifests"]["plant_c"], root / "data" / f"plant_fine_w{window}", "fine_tune", cfg["species"]["plant_fine"], window, cfg)))

    for model_key, model_cfg in cfg["models"].items():
        for window in cfg["windows"]:
            data = root / "data" / f"human_h0_w{window}"
            run = root / "runs" / f"{model_key}_H0_w{window}_seed42"
            train.append((f"train_{model_key}_w{window}", train_cmd(model_key, model_cfg, window, data, run, cfg)))
            for panel, species_list in [("animal_fine", cfg["species"]["animal_fine"]), ("plant_fine", cfg["species"]["plant_fine"])]:
                for species in species_list:
                    data_dir = root / "data" / f"{panel}_w{window}" / species
                    out_json = reports / "matrix_eval" / model_key / f"w{window}" / panel / f"{species}.json"
                    evals.append((f"eval_{model_key}_w{window}_{panel}_{species}", eval_cmd(run, data_dir, out_json, model_key, window, cfg, species, f"{model_key}_w{window}_to_{panel}", env_prefix(model_cfg))))

    ntv2_probe = {
        "path": cfg["existing_models"]["ntv2_500m_4096"],
        "kind": "auto_token",
        "token_label_mode": "nt_kmer",
        "batch_size": 1,
        "grad_accum": 16,
        "local_files_only": True,
    }
    for species in cfg["species"]["probe_all"]:
        manifest = cfg["manifests"]["animal_b"] if species not in cfg["species"]["plant_fine"] + ["teosinte", "soybean"] else cfg["manifests"]["plant_c"]
        data_dir = root / "data" / "species_probe_ntv2_500m" / species
        species_probe_prep.append((f"prep_probe_{species}", " ".join([
            "python3", str(CALIB / "prepare_species_holdout.py"),
            "--manifest", q(manifest),
            "--out-dir", q(data_dir),
            "--species", species,
            "--split", "fine_tune" if species in cfg["species"]["animal_fine"] + cfg["species"]["plant_fine"] + ["human"] else "eval_only",
            "--window", "4096",
            "--step", "4096",
            "--train-windows", str(qp["species_probe_train_windows"]),
            "--val-windows", str(qp["species_probe_val_windows"]),
            "--test-windows", str(qp["species_probe_test_windows"]),
        ])))
        run = root / "runs" / f"species_probe_ntv2_500m_{species}_w4096_seed42"
        species_probe_train.append((f"train_probe_{species}", train_cmd("ntv2_500m_probe", ntv2_probe, 4096, data_dir, run, {**cfg, "quick_profile": {**qp, "max_steps": qp["species_probe_max_steps"]}})))
        species_probe_eval.append((f"eval_probe_{species}", eval_cmd(run, data_dir, reports / "species_probe" / f"{species}.json", "ntv2_500m_probe", 4096, cfg, species, "species_specific_holdout", env_prefix(ntv2_probe))))

    seg_cfg = cfg["strict_segment"]
    for model_key, model_dir in {
        "generanno_4096": cfg["existing_models"]["generanno_4096"],
        "animal_invert_boost_4096": cfg["existing_models"]["animal_invert_boost_4096"],
    }.items():
        for species in ["human", "mouse", "fruit_fly", "western_honey_bee", "rice", "maize"]:
            if species == "human":
                data_jsonl = root / "data" / "human_h0_w4096" / "test" / "data.jsonl.gz"
                panel = "human_h0"
            elif species == "western_honey_bee":
                data_jsonl = root / "data" / "species_probe_ntv2_500m" / species / "test" / "data.jsonl.gz"
                panel = "species_probe"
            elif species in cfg["species"]["plant_fine"]:
                data_jsonl = root / "data" / "plant_fine_w4096" / species / "test" / "data.jsonl.gz"
                panel = "plant_fine"
            else:
                data_jsonl = root / "data" / "animal_fine_w4096" / species / "test" / "data.jsonl.gz"
                panel = "animal_fine"
            strict_segment.append((f"strictseg_{model_key}_{species}", " ".join([
                "python3", str(PIPE / "strict_segment_eval.py"),
                "--exp-id", prefix,
                "--model-dir", q(model_dir),
                "--data-jsonl", q(data_jsonl),
                "--out-tsv", q(reports / "strict_segment" / model_key / f"{panel}_{species}.tsv"),
                "--out-json", q(reports / "strict_segment" / model_key / f"{panel}_{species}.json"),
                "--window", "4096",
                "--stride", "4096",
                "--weight-mode", seg_cfg["weight_mode"],
                "--threshold", str(seg_cfg["threshold"]),
                "--iou-thresholds", *[str(x) for x in seg_cfg["iou_thresholds"]],
                "--boundary-tolerances", *[str(x) for x in seg_cfg["boundary_tolerances_bp"]],
                "--max-windows", str(qp["strict_segment_max_windows"]),
            ])))

    summary.append(("summarize_final", " ".join([
        "python3", str(PIPE / "summarize_results.py"),
        "--config", q(args.config),
    ])))

    out = Path(args.out_dir)
    for suffix, rows in [
        ("download_jobs", download),
        ("smoke_jobs", smoke),
        ("prep_jobs", prep),
        ("train_jobs", train),
        ("eval_jobs", evals),
        ("species_probe_prep_jobs", species_probe_prep),
        ("species_probe_train_jobs", species_probe_train),
        ("species_probe_eval_jobs", species_probe_eval),
        ("strict_segment_jobs", strict_segment),
        ("summarize_jobs", summary),
    ]:
        write_tsv(out / f"{prefix}.{suffix}.tsv", rows)
    print(json.dumps({
        "download": len(download),
        "smoke": len(smoke),
        "prep": len(prep),
        "train": len(train),
        "eval": len(evals),
        "species_probe_prep": len(species_probe_prep),
        "species_probe_train": len(species_probe_train),
        "species_probe_eval": len(species_probe_eval),
        "strict_segment": len(strict_segment),
        "summarize": len(summary),
    }, indent=2))


if __name__ == "__main__":
    main()
