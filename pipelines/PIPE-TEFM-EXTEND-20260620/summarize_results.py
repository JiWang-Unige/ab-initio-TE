#!/usr/bin/env python3
"""Summarize PIPE-TEFM-EXTEND-20260620 outputs into compact TSVs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml


def json_rows(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.rglob("*.json")):
        if "_tmp" in path.parts:
            continue
        try:
            item = json.loads(path.read_text())
        except Exception:
            continue
        item["_path"] = str(path)
        rows.append(item)
    return rows


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields = sorted({k for row in rows for k in row if not isinstance(row.get(k), (dict, list))})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def collect_segment(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.rglob("summary_w*.tsv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                row["_path"] = str(path)
                parts = path.parts
                if len(parts) >= 3:
                    row["model"] = parts[-3]
                    row["species"] = parts[-2]
                rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-EXTEND-20260620.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    reports = Path(cfg["outputs"]["reports"])
    summaries = reports / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)

    eval_rows = []
    for base in [reports / "plant_transfer", reports / "cross_eval", reports / "stress_anchor"]:
        for row in json_rows(base):
            if "te_f1" in row:
                eval_rows.append(row)
    write_tsv(summaries / "transfer_eval.tsv", eval_rows)

    emb_rows = []
    for row in json_rows(reports / "embedding_strict"):
        if "ari" in row or row.get("status") == "skipped":
            emb_rows.append(row)
    write_tsv(summaries / "embedding_strict.tsv", emb_rows)

    sf5_rows = []
    for row in json_rows(Path(cfg["outputs"]["root"]) / "runs" / "sf5_base_pretrained"):
        if "main4_conditional_macro_f1" in row:
            sf5_rows.append(row)
    write_tsv(summaries / "sf5_base.tsv", sf5_rows)

    seg_rows = collect_segment(reports / "pu_segment")
    write_tsv(summaries / "pu_segment.tsv", seg_rows)

    status = {
        "pipeline_id": cfg["pipeline_id"],
        "transfer_rows": len(eval_rows),
        "embedding_rows": len(emb_rows),
        "sf5_rows": len(sf5_rows),
        "segment_rows": len(seg_rows),
        "decay_formula": str(reports / "decay_formula" / "formula_fits.json"),
    }
    (summaries / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
