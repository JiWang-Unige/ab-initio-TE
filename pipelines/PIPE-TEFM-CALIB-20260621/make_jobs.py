#!/usr/bin/env python3
"""Generate command TSVs for PIPE-TEFM-CALIB-20260621."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

PIPE = Path("pipelines/PIPE-TEFM-CALIB-20260621")
SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617")
EXT = Path("pipelines/PIPE-TEFM-EXTEND-20260620")


def q(s: str) -> str:
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def write_tsv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for name, cmd in rows:
            if "\t" in name or "\t" in cmd:
                raise ValueError(f"tab not allowed in job row {name}")
            handle.write(f"{name}\t{cmd}\n")


def prep_eval_cmd(manifest: str, out_dir: Path, split: str, species: list[str], cfg: dict) -> str:
    return " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "eval",
        "--manifest", manifest,
        "--out-dir", str(out_dir),
        "--split", split,
        "--species", *species,
        "--window", str(cfg["window"]),
        "--step", str(cfg["window"]),
        "--max-windows-per-species", str(cfg["quick_profile"]["eval_windows_per_species"]),
    ])


def prep_mixed_cmd(manifest: str, out_dir: Path, proportions: dict, cfg: dict) -> str:
    return " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "mixed",
        "--manifest", manifest,
        "--out-dir", str(out_dir),
        "--window", str(cfg["window"]),
        "--step", str(cfg["window"]),
        "--proportions-json", q(json.dumps(proportions)),
        "--total-windows", str(cfg["quick_profile"]["total_windows"]),
        "--seed", str(cfg["seed"]),
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-CALIB-20260621.yaml")
    ap.add_argument("--out-dir", default="configs/pipelines")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    root = Path(cfg["outputs"]["root"])
    reports = Path(cfg["outputs"]["reports"])
    qp = cfg["quick_profile"]
    model = cfg["model"]

    prep: list[tuple[str, str]] = []
    train: list[tuple[str, str]] = []
    evals: list[tuple[str, str]] = []
    embed_extract: list[tuple[str, str]] = []
    embed_cluster: list[tuple[str, str]] = []
    formula: list[tuple[str, str]] = []
    summary: list[tuple[str, str]] = []

    plant_fine = root / "data" / "plant_eval_fine"
    plant_eval = root / "data" / "plant_eval_only"
    cross_eval = root / "data" / "cross_eval"
    stress_eval = root / "data" / "stress_eval"
    prep.append(("prep_plant_eval_fine", prep_eval_cmd(cfg["manifests"]["plant"], plant_fine, "fine_tune", cfg["species"]["plant_eval_fine"], cfg)))
    prep.append(("prep_plant_eval_only", prep_eval_cmd(cfg["manifests"]["plant"], plant_eval, "eval_only", cfg["species"]["plant_eval_only"], cfg)))
    prep.append(("prep_cross_eval", prep_eval_cmd(cfg["manifests"]["cross"], cross_eval, "eval_only", cfg["species"]["cross_eval"], cfg)))
    prep.append(("prep_stress_eval", prep_eval_cmd(cfg["manifests"]["animal_b"], stress_eval, "eval_only", cfg["species"]["stress_eval"], cfg)))

    prep.append(("prep_plant_supervised", prep_mixed_cmd(cfg["manifests"]["plant"], root / "data" / "plant_supervised_4096", cfg["mixtures"]["plant_supervised"], cfg)))
    prep.append(("prep_cross_supervised", prep_mixed_cmd(cfg["manifests"]["cross"], root / "data" / "cross_supervised_4096", cfg["mixtures"]["cross_supervised"], cfg)))
    for species in ["western_honey_bee", "red_flour_beetle"]:
        prep.append((f"prep_direct_{species}", " ".join([
            "python3", str(PIPE / "prepare_species_holdout.py"),
            "--manifest", cfg["manifests"]["animal_b"],
            "--out-dir", str(root / "data" / f"direct_{species}"),
            "--species", species,
            "--split", "eval_only",
            "--window", str(cfg["window"]),
            "--step", str(cfg["window"]),
            "--train-windows", str(qp["direct_species_train_windows"]),
            "--val-windows", str(qp["direct_species_val_windows"]),
            "--test-windows", str(qp["direct_species_test_windows"]),
        ])))
    prep.append(("prep_insect_no_beetle", " ".join([
        "python3", str(PIPE / "prepare_mixed_any.py"),
        "--manifest", cfg["manifests"]["animal_b"],
        "--out-dir", str(root / "data" / "insect_no_beetle_4096"),
        "--species-split", "fruit_fly:fine_tune", "western_honey_bee:eval_only",
        "--proportions-json", q(json.dumps(cfg["mixtures"]["insect_no_beetle"])),
        "--total-windows", str(qp["total_windows"]),
        "--window", str(cfg["window"]),
        "--step", str(cfg["window"]),
        "--seed", str(cfg["seed"]),
    ])))

    cons_frag = root / "embedding_fragments" / "Dfam_consensus" / "family_len512.jsonl.gz"
    embed_extract.append(("extract_dfam_consensus_family512", " ".join([
        "python3", str(EXT / "embedding_strict.py"), "extract-consensus",
        "--consensus-fasta", str(cfg["dfam_consensus_fasta"]),
        "--out-jsonl", str(cons_frag),
        "--out-meta", str(cons_frag.with_suffix(".metadata.json")),
        "--label-level", "family",
        "--length", "512",
        "--top-labels", str(qp["embedding_top_families"]),
        "--max-per-label", str(qp["embedding_max_per_label"]),
        "--min-per-label", str(qp["embedding_min_per_label"]),
        "--seed", str(cfg["seed"]),
    ])))
    for setting, model_path in [("C0", ""), ("C1", ""), ("A0", model["pretrained_path"]), ("A1", model["pretrained_path"])]:
        cmd = [
            "python3", str(EXT / "embedding_strict.py"), "cluster",
            "--fragments", str(cons_frag),
            "--setting", setting,
            "--out-dir", str(reports / "embedding_strict" / "Dfam_consensus" / "family_len512" / setting),
            "--source", "dfam_consensus",
            "--label-level", "family",
            "--batch-size", "8",
            "--max-records", str(qp["embedding_max_records"]),
            "--contrastive-epochs", "120",
            "--seed", str(cfg["seed"]),
        ]
        if model_path:
            cmd += ["--model-path", model_path, "--model-kind", "base"]
        embed_cluster.append((f"cluster_dfam_consensus_{setting}", " ".join(cmd)))

    train.append(("train_plant_supervised", train_binary_cmd(root / "data" / "plant_supervised_4096", root / "runs" / "plant_supervised_4096", model["pretrained_path"], cfg, qp["max_steps"], qp["eval_steps"])))
    train.append(("train_cross_supervised", train_binary_cmd(root / "data" / "cross_supervised_4096", root / "runs" / "cross_supervised_4096", model["pretrained_path"], cfg, qp["max_steps"], qp["eval_steps"])))
    train.append(("train_direct_honeybee", train_binary_cmd(root / "data" / "direct_western_honey_bee", root / "runs" / "direct_western_honey_bee_4096", model["pretrained_path"], cfg, qp["direct_species_max_steps"], qp["direct_species_eval_steps"])))
    train.append(("train_direct_beetle", train_binary_cmd(root / "data" / "direct_red_flour_beetle", root / "runs" / "direct_red_flour_beetle_4096", model["pretrained_path"], cfg, qp["direct_species_max_steps"], qp["direct_species_eval_steps"])))
    train.append(("train_insect_no_beetle", train_binary_cmd(root / "data" / "insect_no_beetle_4096", root / "runs" / "insect_no_beetle_4096", model["pretrained_path"], cfg, qp["max_steps"], qp["eval_steps"])))

    models = {
        "animal_invert_boost": model["invert_boost_4096"],
        "plant_supervised": root / "runs" / "plant_supervised_4096",
        "cross_supervised": root / "runs" / "cross_supervised_4096",
        "insect_no_beetle": root / "runs" / "insect_no_beetle_4096",
        "direct_honeybee": root / "runs" / "direct_western_honey_bee_4096",
        "direct_beetle": root / "runs" / "direct_red_flour_beetle_4096",
    }
    for panel, base, species_list in [
        ("plant_fine", plant_fine, cfg["species"]["plant_eval_fine"]),
        ("plant_eval", plant_eval, cfg["species"]["plant_eval_only"]),
        ("cross_eval", cross_eval, cfg["species"]["cross_eval"]),
        ("stress_eval", stress_eval, cfg["species"]["stress_eval"]),
    ]:
        for species in species_list:
            data_dir = base / species
            for name, mdir in models.items():
                if name in {"direct_honeybee", "direct_beetle"} and species not in {"western_honey_bee", "red_flour_beetle"}:
                    continue
                evals.append((
                    f"eval_{name}_{panel}_{species}",
                    eval_binary_cmd(mdir, data_dir, reports / "binary_eval" / name / panel / f"{species}.json", cfg, f"{name}_to_{panel}", species),
                ))
    for species, name in [("western_honey_bee", "direct_honeybee"), ("red_flour_beetle", "direct_beetle")]:
        evals.append((
            f"eval_{name}_own_holdout",
            eval_binary_cmd(models[name], root / "data" / f"direct_{species}", reports / "direct_species" / name / f"{species}.json", cfg, f"{name}_own_holdout", species),
        ))

    formula.append(("fit_decay_formula_extended", " ".join([
        "python3", str(PIPE / "fit_decay_formula_extended.py"),
        "--lock-recovery", "reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/recovery_eval.tsv",
        "--repair-mixed", "reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/mixed_eval.tsv",
        "--extend-transfer", "reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/transfer_eval.tsv",
        "--new-eval-root", str(reports),
        "--concordance", cfg["manifests"]["concordance"],
        "--manifest", cfg["manifests"]["cross"],
        "--eval-data-root", str(root / "data"),
        "--out-dir", str(reports / "decay_formula_extended"),
    ])))
    summary.append(("summarize", " ".join(["python3", str(PIPE / "summarize_results.py"), "--config", args.config])))

    out = Path(args.out_dir)
    prefix = cfg["pipeline_id"]
    for suffix, rows in [
        ("prep_jobs", prep),
        ("train_jobs", train),
        ("eval_jobs", evals),
        ("embedding_extract_jobs", embed_extract),
        ("embedding_cluster_jobs", embed_cluster),
        ("formula_jobs", formula),
        ("summarize_jobs", summary),
    ]:
        write_tsv(out / f"{prefix}.{suffix}.tsv", rows)
    print(json.dumps({k: len(v) for k, v in {
        "prep": prep, "train": train, "eval": evals,
        "embedding_extract": embed_extract, "embedding_cluster": embed_cluster,
        "formula": formula, "summarize": summary,
    }.items()}, indent=2))


if __name__ == "__main__":
    main()
