#!/usr/bin/env python3
"""Generate command TSVs for PIPE-TEFM-SEG-SF-20260618."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML is required: {exc}")


def write_tsv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        for row in rows:
            writer.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-SEG-SF-20260618.yaml")
    ap.add_argument("--out-dir", default="configs/pipelines")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    root = Path(cfg["outputs"]["root"])
    reports = Path(cfg["outputs"]["reports"])
    pipe = Path("pipelines/PIPE-TEFM-SEG-SF-20260618")
    prep_rows = []
    eval_rows = []
    sf_rows = []
    emb_extract_rows = []
    emb_cluster_rows = []
    h0_manifest = cfg["manifests"]["human_h0"]
    for item in cfg["windows"]:
        w = int(item["window"])
        data_dir = root / "data" / f"human_H0_sf_w{w}"
        prep_rows.append((
            f"sf_data_w{w}",
            " ".join([
                "python3", str(pipe / "prepare_superfamily_windows.py"), "human",
                "--manifest", h0_manifest,
                "--out-dir", str(data_dir),
                "--window", str(w),
                "--step", str(w),
                "--max-windows-per-split", str(cfg["quick_profile"]["max_train_windows_per_split"]),
            ]),
        ))
        for stride in item["strides"]:
            span_matched_windows = int(cfg["quick_profile"]["max_eval_windows"] * (w / int(stride)))
            overlap_data = root / "data" / f"human_H0_overlap_w{w}_s{stride}"
            prep_rows.append((
                f"overlap_data_w{w}_s{stride}",
                " ".join([
                    "python3", "pipelines/PIPE-TEFM-SUPP-20260617/prepare_ucsc_windows.py", "human",
                    "--manifest", h0_manifest,
                    "--out-dir", str(overlap_data),
                    "--window", str(w),
                    "--step", str(stride),
                    "--max-windows-per-split", str(span_matched_windows),
                ]),
            ))
            model_dir = cfg["model"][f"binary_{w}"]
            eval_rows.append((
                f"overlap_eval_w{w}_s{stride}",
                " ".join([
                    "python3", str(pipe / "bp_overlap_segment_eval.py"),
                    "--model-dir", model_dir,
                    "--data-jsonl", str(overlap_data / "test" / "data.jsonl.gz"),
                    "--out-dir", str(reports / "overlap_segment"),
                    "--window", str(w),
                    "--stride", str(stride),
                    "--max-windows", str(span_matched_windows),
                ]),
            ))
        sf_rows.append((
            f"sf_train_w{w}",
            " ".join([
                "python3", str(pipe / "te_superfamily_task.py"), "train",
                "--init-checkpoint", str(Path(cfg["model"][f"binary_{w}"]) / "best_model"),
                "--data-dir", str(data_dir),
                "--output-dir", str(root / "runs" / f"TFSF_generanno_H0_w{w}_seed42"),
                "--window", str(w),
                "--seed", str(cfg["seed"]),
                "--max-steps", "900",
                "--eval-steps", "150",
                "--batch-size", "1",
                "--grad-accum", "16",
                "--bf16",
                "--gradient-checkpointing",
            ]),
        ))
    for panel_key, manifest in [("B_animal", cfg["manifests"]["animal_b"]), ("D_crosskingdom", cfg["manifests"]["cross_kingdom_d"])]:
        for length in [128, 256, 512]:
            frag = root / "embedding_fragments" / panel_key / f"fragments_{length}.jsonl.gz"
            emb_extract_rows.append((
                f"extract_{panel_key}_{length}",
                " ".join([
                    "python3", str(pipe / "embedding_cluster.py"), "extract",
                    "--manifest", manifest,
                    "--length", str(length),
                    "--out-jsonl", str(frag),
                    "--out-meta", str(root / "embedding_fragments" / panel_key / f"fragments_{length}.metadata.json"),
                    "--max-per-class", str(cfg["quick_profile"]["max_cluster_per_class"]),
                    "--seed", str(cfg["seed"]),
                ]),
            ))
            settings = [
                ("A0", cfg["model"]["pretrained_path"], "base"),
                ("A1", cfg["model"]["pretrained_path"], "base"),
                ("B0_w2048", str(Path(cfg["model"]["binary_2048"]) / "best_model"), "token"),
                ("B1_w2048", str(Path(cfg["model"]["binary_2048"]) / "best_model"), "token"),
                ("B0_w4096", str(Path(cfg["model"]["binary_4096"]) / "best_model"), "token"),
                ("B1_w4096", str(Path(cfg["model"]["binary_4096"]) / "best_model"), "token"),
                ("C0", "", "base"),
                ("C1", "", "base"),
            ]
            for setting, model_path, kind in settings:
                canonical = setting.split("_")[0]
                cmd = [
                    "python3", str(pipe / "embedding_cluster.py"), "cluster",
                    "--fragments", str(frag),
                    "--setting", canonical,
                    "--out-dir", str(reports / "embedding_cluster" / panel_key / f"len{length}" / setting),
                    "--seed", str(cfg["seed"]),
                    "--batch-size", "8",
                    "--max-records", str(cfg["quick_profile"]["max_cluster_total_per_setting"]),
                ]
                if canonical in {"A0", "A1", "B0", "B1"}:
                    cmd += ["--model-path", model_path, "--model-kind", kind]
                emb_cluster_rows.append((f"cluster_{panel_key}_{length}_{setting}", " ".join(cmd)))
    out = Path(args.out_dir)
    prefix = "PIPE-TEFM-SEG-SF-20260618"
    write_tsv(out / f"{prefix}.prep_jobs.tsv", prep_rows)
    write_tsv(out / f"{prefix}.overlap_eval_jobs.tsv", eval_rows)
    write_tsv(out / f"{prefix}.superfamily_jobs.tsv", sf_rows)
    write_tsv(out / f"{prefix}.embedding_extract_jobs.tsv", emb_extract_rows)
    write_tsv(out / f"{prefix}.embedding_cluster_jobs.tsv", emb_cluster_rows)
    print({
        "prep": len(prep_rows),
        "overlap_eval": len(eval_rows),
        "superfamily": len(sf_rows),
        "embedding_extract": len(emb_extract_rows),
        "embedding_cluster": len(emb_cluster_rows),
    })


if __name__ == "__main__":
    main()
