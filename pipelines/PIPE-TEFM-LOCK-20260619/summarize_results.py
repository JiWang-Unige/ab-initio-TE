#!/usr/bin/env python3
"""Summarize PIPE-TEFM-LOCK-20260619 outputs."""
from __future__ import annotations

import argparse
import csv
import glob
import json
from pathlib import Path

import yaml


def read_json(path: str) -> dict:
    with open(path) as handle:
        return json.load(handle)


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
        writer.writerows(rows)


def collect_json(pattern: str, extra: dict | None = None) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(pattern)):
        row = read_json(path)
        row["path"] = path
        if extra:
            row.update(extra)
        rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    reports = Path(cfg["outputs"]["reports"])
    summary = reports / "summaries"
    summary.mkdir(parents=True, exist_ok=True)

    recovery_rows = collect_json(str(reports / "recovery_eval" / "*" / "*.json"))
    write_tsv(summary / "recovery_eval.tsv", recovery_rows)

    sf5_rows = collect_json(str(cfg["outputs"]["root"] + "/runs/SF5_*_seed42/test_results.json"))
    write_tsv(summary / "superfamily5.tsv", sf5_rows)

    segment_rows = []
    for path in sorted(glob.glob(str(reports / "segment_multi_species" / "*" / "*" / "summary_*.tsv"))):
        with open(path, newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("chrom") == "WEIGHTED_MEAN":
                    row["path"] = path
                    row["species"] = Path(path).parent.name
                    segment_rows.append(row)
    write_tsv(summary / "segment_multi_species.tsv", segment_rows)

    embed_rows = []
    for path in sorted(glob.glob(str(reports / "embedding_objective" / "*" / "*" / "diagnostic_metrics.json"))):
        row = read_json(path)
        row["path"] = path
        embed_rows.append(row)
    write_tsv(summary / "embedding_objective.tsv", embed_rows)

    status = {
        "pipeline_id": cfg["pipeline_id"],
        "recovery_rows": len(recovery_rows),
        "sf5_rows": len(sf5_rows),
        "segment_rows": len(segment_rows),
        "embedding_rows": len(embed_rows),
        "stress_audit": str(reports / "summaries" / "stress_panel_audit.tsv"),
    }
    (summary / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
