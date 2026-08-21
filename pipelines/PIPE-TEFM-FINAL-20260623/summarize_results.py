#!/usr/bin/env python3
"""Summarize PIPE-TEFM-FINAL-20260623 outputs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-FINAL-20260623.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    reports = Path(cfg["outputs"]["reports"])
    summaries = reports / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)

    smoke_rows = []
    for path in sorted((reports / "smoke").glob("*.json")):
        data = read_json(path)
        if data:
            smoke_rows.append({"model_key": path.stem, **data})
    write_tsv(summaries / "smoke.tsv", smoke_rows)

    matrix_rows = []
    for path in sorted((reports / "matrix_eval").rglob("*.json")):
        data = read_json(path)
        if data:
            row = {"path": str(path)}
            for key in ["stage", "model_key", "model", "window", "species", "te_f1", "te_precision", "te_recall", "te_auprc", "macro_f1", "n_windows"]:
                row[key] = data.get(key)
            matrix_rows.append(row)
    write_tsv(summaries / "matrix_eval.tsv", matrix_rows)

    probe_rows = []
    for path in sorted((reports / "species_probe").glob("*.json")):
        data = read_json(path)
        if data:
            row = {"path": str(path), "species": path.stem}
            for key in ["te_f1", "te_precision", "te_recall", "te_auprc", "macro_f1", "n_windows"]:
                row[key] = data.get(key)
            probe_rows.append(row)
    write_tsv(summaries / "species_probe.tsv", probe_rows)

    strict_rows = []
    for path in sorted((reports / "strict_segment").rglob("*.tsv")):
        with path.open() as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                row["path"] = str(path)
                strict_rows.append(row)
    write_tsv(summaries / "strict_segment.tsv", strict_rows)

    status = {
        "pipeline_id": cfg["pipeline_id"],
        "smoke_rows": len(smoke_rows),
        "matrix_eval_rows": len(matrix_rows),
        "species_probe_rows": len(probe_rows),
        "strict_segment_rows": len(strict_rows),
        "summaries": {
            "smoke": str(summaries / "smoke.tsv"),
            "matrix_eval": str(summaries / "matrix_eval.tsv"),
            "species_probe": str(summaries / "species_probe.tsv"),
            "strict_segment": str(summaries / "strict_segment.tsv"),
        },
    }
    (summaries / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
