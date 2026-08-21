#!/usr/bin/env python3
"""Generate command TSVs for PIPE-TEFM-REPAIR-20260618."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


PIPE = Path("pipelines/PIPE-TEFM-REPAIR-20260618")
SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617")
SEG = Path("pipelines/PIPE-TEFM-SEG-SF-20260618")


def q(s: str) -> str:
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def write_tsv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for name, cmd in rows:
            if "\t" in name or "\t" in cmd:
                raise ValueError(f"tab not allowed in job row: {name}")
            handle.write(f"{name}\t{cmd}\n")


def sample_cmd(sources: list[dict], out_jsonl: Path, out_meta: Path, seed: int) -> str:
    return " ".join([
        "python3", str(PIPE / "sample_jsonl_mix.py"),
        "--sources-json", q(json.dumps(sources)),
        "--out-jsonl", str(out_jsonl),
        "--out-meta", str(out_meta),
        "--seed", str(seed),
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-REPAIR-20260618.yaml")
    ap.add_argument("--out-dir", default="configs/pipelines")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    root = Path(cfg["outputs"]["root"])
    reports = Path(cfg["outputs"]["reports"])
    seed = int(cfg["seed"])
    window = int(cfg["window"])
    stride = int(cfg["stride"])
    qprof = cfg["quick_profile"]
    prep: list[tuple[str, str]] = []
    train: list[tuple[str, str]] = []
    evals: list[tuple[str, str]] = []
    segment: list[tuple[str, str]] = []
    embedding_extract: list[tuple[str, str]] = []
    embedding_diag: list[tuple[str, str]] = []
    summarize: list[tuple[str, str]] = []

    # P5 archive-parity diagnostic pools.
    human_pool = root / "data" / "p5_human_pool_w4096"
    prep.append(("prep_p5_human_pool", " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "human",
        "--manifest", cfg["manifests"]["human_h0"],
        "--out-dir", str(human_pool),
        "--window", str(window),
        "--step", str(window),
        "--max-windows-per-split", "18000",
    ])))
    p5_nonhuman = root / "data" / "p5_nonhuman_pool_w4096"
    prep.append(("prep_p5_nonhuman_pool", " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "mixed",
        "--manifest", cfg["manifests"]["mixed_a2"],
        "--out-dir", str(p5_nonhuman),
        "--window", str(window),
        "--step", str(window),
        "--proportions-json", q(json.dumps(cfg["mixed_variants"]["p5_archive_parity_4096"]["nonhuman_proportions"])),
        "--total-windows", str(qprof["total_p5_nonhuman_windows"]),
        "--seed", str(seed),
    ])))
    p5_data = root / "data" / "p5_archive_parity_4096"
    prep.append(("sample_p5_train", sample_cmd([
        {"path": str(human_pool / "train" / "data.jsonl.gz"), "quota": cfg["mixed_variants"]["p5_archive_parity_4096"]["human_quota_train"], "species_code": "human"},
        {"path": str(p5_nonhuman / "train" / "data.jsonl.gz"), "quota": 4050, "species_code": ""},
    ], p5_data / "train" / "data.jsonl.gz", p5_data / "train" / "sample_meta.json", seed)))
    prep.append(("sample_p5_val", sample_cmd([
        {"path": str(human_pool / "val" / "data.jsonl.gz"), "quota": cfg["mixed_variants"]["p5_archive_parity_4096"]["human_quota_val"], "species_code": "human"},
        {"path": str(p5_nonhuman / "val" / "data.jsonl.gz"), "quota": 450, "species_code": ""},
    ], p5_data / "val" / "data.jsonl.gz", p5_data / "val" / "sample_meta.json", seed)))

    # No-human animal variants.
    for name in ["mouse_core_animal_4096", "invert_boost_animal_4096"]:
        item = cfg["mixed_variants"][name]
        prep.append((f"prep_{name}", " ".join([
            "python3", str(SUPP / "prepare_ucsc_windows.py"), "mixed",
            "--manifest", cfg["manifests"]["mixed_a2"],
            "--out-dir", str(root / "data" / name),
            "--window", str(window),
            "--step", str(window),
            "--proportions-json", q(json.dumps(item["proportions"])),
            "--total-windows", str(qprof["total_mixed_windows"]),
            "--seed", str(seed),
        ])))

    # Superfamily larger-data rerun.
    sf_data = root / "data" / "human_H0_sf_w4096_large"
    prep.append(("prep_sf_w4096_large", " ".join([
        "python3", str(SEG / "prepare_superfamily_windows.py"), "human",
        "--manifest", cfg["manifests"]["human_h0"],
        "--out-dir", str(sf_data),
        "--window", str(window),
        "--step", str(window),
        "--max-windows-per-split", str(qprof["superfamily_max_windows_per_split"]),
    ])))

    # Overlap data for threshold/postprocess sweep.
    overlap_data = root / "data" / "human_H0_overlap_w4096_s2048"
    prep.append(("prep_overlap_w4096_s2048", " ".join([
        "python3", str(SUPP / "prepare_ucsc_windows.py"), "human",
        "--manifest", cfg["manifests"]["human_h0"],
        "--out-dir", str(overlap_data),
        "--window", str(window),
        "--step", str(stride),
        "--max-windows-per-split", "3600",
    ])))

    # Embedding fragment extraction.
    for panel in cfg["embedding"]["panels"]:
        manifest = cfg["manifests"]["animal_b"] if panel == "B_animal" else cfg["manifests"][panel]
        for length in cfg["embedding"]["lengths"]:
            frag = root / "embedding_fragments" / panel / f"fragments_{length}.jsonl.gz"
            embedding_extract.append((f"extract_{panel}_{length}", " ".join([
                "python3", str(SEG / "embedding_cluster.py"), "extract",
                "--manifest", manifest,
                "--length", str(length),
                "--out-jsonl", str(frag),
                "--out-meta", str(root / "embedding_fragments" / panel / f"fragments_{length}.metadata.json"),
                "--max-per-class", str(qprof["embedding_max_per_class"]),
                "--seed", str(seed),
            ])))

    # Training jobs.
    model = cfg["model"]["pretrained_path"]
    for name in ["p5_archive_parity_4096", "mouse_core_animal_4096", "invert_boost_animal_4096"]:
        train.append((f"train_{name}", " ".join([
            "python3", str(SUPP / "te_token_task.py"), "train",
            "--model-path", model,
            "--kind", "auto_token",
            "--token-label-mode", "single_nt",
            "--data-dir", str(root / "data" / name),
            "--output-dir", str(root / "runs" / f"TFREPAIR_{name}_seed42"),
            "--window", str(window),
            "--seed", str(seed),
            "--batch-size", "1",
            "--grad-accum", "16",
            "--learning-rate", "2e-5",
            "--te-class-weight", "3.0",
            "--max-steps", str(qprof["max_train_steps"]),
            "--eval-steps", str(qprof["eval_steps"]),
            "--max-eval-samples", str(qprof["max_eval_samples"]),
            "--bf16",
            "--gradient-checkpointing",
        ])))
    train.append(("train_superfamily_w4096_large", " ".join([
        "python3", str(SEG / "te_superfamily_task.py"), "train",
        "--init-checkpoint", str(Path(cfg["model"]["binary_h0_4096"]) / "best_model"),
        "--data-dir", str(sf_data),
        "--output-dir", str(root / "runs" / "TFSF_generanno_H0_w4096_large_seed42"),
        "--window", str(window),
        "--seed", str(seed),
        "--max-steps", str(qprof["superfamily_max_steps"]),
        "--eval-steps", "250",
        "--max-eval-samples", str(qprof["max_eval_samples"]),
        "--batch-size", "1",
        "--grad-accum", "16",
        "--bf16",
        "--gradient-checkpointing",
    ])))

    # Evaluations for mixed models.
    eval_species = {
        "a2_eval": ["human", "cattle", "horse", "pig", "opossum", "lizard", "x_laevis", "western_honey_bee", "red_flour_beetle"],
        "b_finetune_eval": ["mouse", "zebrafish", "fruit_fly", "c_elegans", "chicken", "western_clawed_frog"],
        "a1_eval": ["human", "cattle", "pig", "horse"],
    }
    for name in ["p5_archive_parity_4096", "mouse_core_animal_4096", "invert_boost_animal_4096"]:
        model_dir = root / "runs" / f"TFREPAIR_{name}_seed42"
        for panel, species_list in eval_species.items():
            base = Path(cfg["eval_panels"][panel])
            for species in species_list:
                data_dir = base / species
                if not data_dir.exists():
                    continue
                evals.append((f"eval_{name}_{panel}_{species}", " ".join([
                    "python3", str(SUPP / "te_token_task.py"), "eval",
                    "--model-dir", str(model_dir),
                    "--data-dir", str(data_dir),
                    "--out-json", str(reports / "mixed_eval" / name / panel / f"{species}.json"),
                    "--batch-size", "1",
                    "--max-samples", str(qprof["max_eval_samples"]),
                    "--stage", f"{name}_to_{panel}",
                    "--model-key", "generanno",
                    "--model", name,
                    "--window", str(window),
                    "--species", species,
                ])))

    # Segment threshold/postprocess sweep.
    for thr in cfg["threshold_sweep"]:
        segment.append((f"segment_thr{thr}", " ".join([
            "python3", str(SEG / "bp_overlap_segment_eval.py"),
            "--exp-id", cfg["pipeline_id"],
            "--model-dir", cfg["model"]["binary_h0_4096"],
            "--data-jsonl", str(overlap_data / "test" / "data.jsonl.gz"),
            "--out-dir", str(reports / "segment_threshold" / f"thr_{thr}"),
            "--window", str(window),
            "--stride", str(stride),
            "--threshold", str(thr),
            "--max-windows", "3600",
        ])))

    # Embedding diagnostics.
    for panel in cfg["embedding"]["panels"]:
        for length in cfg["embedding"]["lengths"]:
            frag = root / "embedding_fragments" / panel / f"fragments_{length}.jsonl.gz"
            for setting in cfg["embedding"]["settings"]:
                cmd = [
                    "python3", str(PIPE / "embedding_diagnostic.py"),
                    "--fragments", str(frag),
                    "--setting", setting["setting"],
                    "--out-dir", str(reports / "embedding_diagnostic" / panel / f"len{length}" / setting["name"]),
                    "--seed", str(seed),
                    "--batch-size", "8",
                    "--max-records", str(qprof["embedding_max_records"]),
                    "--contrastive-epochs", "160",
                ]
                if setting["model_path"]:
                    cmd += ["--model-path", setting["model_path"], "--model-kind", setting["model_kind"]]
                embedding_diag.append((f"embed_{panel}_{length}_{setting['name']}", " ".join(cmd)))

    summarize.append(("summarize", " ".join([
        "python3", str(PIPE / "summarize_results.py"),
        "--config", args.config,
    ])))

    out = Path(args.out_dir)
    prefix = cfg["pipeline_id"]
    write_tsv(out / f"{prefix}.prep_jobs.tsv", prep)
    write_tsv(out / f"{prefix}.train_jobs.tsv", train)
    write_tsv(out / f"{prefix}.eval_jobs.tsv", evals)
    write_tsv(out / f"{prefix}.segment_jobs.tsv", segment)
    write_tsv(out / f"{prefix}.embedding_extract_jobs.tsv", embedding_extract)
    write_tsv(out / f"{prefix}.embedding_diag_jobs.tsv", embedding_diag)
    write_tsv(out / f"{prefix}.summarize_jobs.tsv", summarize)
    print(json.dumps({
        "prep": len(prep),
        "train": len(train),
        "eval": len(evals),
        "segment": len(segment),
        "embedding_extract": len(embedding_extract),
        "embedding_diag": len(embedding_diag),
        "summarize": len(summarize),
    }, indent=2))


if __name__ == "__main__":
    main()
