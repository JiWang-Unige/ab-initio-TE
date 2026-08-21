#!/usr/bin/env python3
"""Summarize PIPE-TEFM-CALIB-20260621 outputs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml


def json_rows(root: Path) -> list[dict]:
    rows = []
    if not root.exists():
        return rows
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipelines/PIPE-TEFM-CALIB-20260621.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    reports = Path(cfg["outputs"]["reports"])
    summaries = reports / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)

    eval_rows = [r for r in json_rows(reports / "binary_eval") + json_rows(reports / "direct_species") if "te_f1" in r]
    emb_rows = [r for r in json_rows(reports / "embedding_strict") if "ari" in r or r.get("status") == "skipped"]
    write_tsv(summaries / "binary_eval.tsv", eval_rows)
    write_tsv(summaries / "embedding_dfam_consensus.tsv", emb_rows)

    formula_path = reports / "decay_formula_extended" / "formula_fits_extended.json"
    status = {
        "pipeline_id": cfg["pipeline_id"],
        "binary_eval_rows": len(eval_rows),
        "embedding_rows": len(emb_rows),
        "decay_formula_extended": str(formula_path),
    }
    (summaries / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
