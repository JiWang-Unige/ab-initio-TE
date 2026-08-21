#!/usr/bin/env python3
"""Summarize PIPE-TEFM-REPAIR-20260618 outputs."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import yaml


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-REPAIR-20260618.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    reports = Path(cfg["outputs"]["reports"])
    summaries = reports / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)

    mixed_rows = []
    for path in sorted((reports / "mixed_eval").rglob("*.json")):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        row = {"path": str(path)}
        for key in ["stage", "model", "model_key", "window", "species", "te_f1", "te_precision", "te_recall", "te_auprc", "macro_f1", "bg_f1", "n_windows", "n_labeled_tokens"]:
            row[key] = data.get(key)
        mixed_rows.append(row)
    write_tsv(summaries / "mixed_eval.tsv", mixed_rows)

    segment_rows = []
    for path in sorted((reports / "segment_threshold").rglob("summary_w*.tsv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("chrom") != "WEIGHTED_MEAN":
                    continue
                row["path"] = str(path)
                row["threshold_dir"] = path.parent.name
                segment_rows.append(row)
    write_tsv(summaries / "segment_threshold.tsv", segment_rows)

    sf_rows = []
    for path in sorted(Path(cfg["outputs"]["root"]).rglob("test_results.json")):
        if "TFSF_" not in str(path):
            continue
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        row = {"path": str(path)}
        row.update(data)
        vals = [data.get(k) for k in ["sine_f1", "line_f1", "ltr_f1", "dna_f1"]]
        vals = [float(v) for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
        row["main4_macro_f1"] = sum(vals) / len(vals) if vals else ""
        sf_rows.append(row)
    write_tsv(summaries / "superfamily.tsv", sf_rows)

    emb_rows = []
    for path in sorted((reports / "embedding_diagnostic").rglob("diagnostic_metrics.json")):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        row = {"path": str(path)}
        row.update(data)
        emb_rows.append(row)
    write_tsv(summaries / "embedding_diagnostic.tsv", emb_rows)

    status = {
        "mixed_rows": len(mixed_rows),
        "segment_rows": len(segment_rows),
        "superfamily_rows": len(sf_rows),
        "embedding_rows": len(emb_rows),
        "report_root": str(reports),
    }
    (summaries / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
