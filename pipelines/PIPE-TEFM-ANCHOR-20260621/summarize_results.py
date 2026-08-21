#!/usr/bin/env python3
"""Summarize PIPE-TEFM-ANCHOR-20260621 outputs."""
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
        try:
            item = json.loads(path.read_text())
        except Exception:
            continue
        if "te_f1" not in item:
            continue
        item["_path"] = str(path)
        item.setdefault("species", path.stem)
        rows.append(item)
    return rows


def metric_rows(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.rglob("metrics.json")):
        try:
            item = json.loads(path.read_text())
        except Exception:
            continue
        item["_path"] = str(path)
        parts = path.parts
        if len(parts) >= 3:
            item.setdefault("fragment_set", parts[-3])
        rows.append(item)
    return rows


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    reports = Path(cfg["outputs"]["reports"])
    summaries = reports / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)

    binary = json_rows(reports / "binary_eval")
    emb = metric_rows(reports / "embedding")
    write_tsv(summaries / "binary_eval.tsv", binary)
    write_tsv(summaries / "embedding_bg_unknown.tsv", emb)

    sf5_summary = {}
    sf5_path = reports / "sf5_candidate_summary.json"
    if sf5_path.exists():
        sf5_summary = json.loads(sf5_path.read_text())
    formula = {}
    formula_path = reports / "anchor_formula" / "anchor_formula_results.json"
    if formula_path.exists():
        formula = json.loads(formula_path.read_text())

    by_model = {}
    for row in binary:
        model = row.get("model") or row.get("model_dir") or row.get("stage", "unknown")
        by_model.setdefault(model, []).append(float(row.get("te_f1", 0.0)))
    model_summary = {m: {"n": len(v), "mean_te_f1": mean(v), "min_te_f1": min(v), "max_te_f1": max(v)} for m, v in sorted(by_model.items())}

    emb_summary = {}
    for row in emb:
        fs = row.get("fragment_set", "")
        setting = row.get("setting", "")
        emb_summary[f"{fs}:{setting}"] = {
            "ari": row.get("ari", row.get("ARI", "")),
            "nmi": row.get("nmi", row.get("NMI", "")),
            "holdout_macro_f1": row.get("holdout_macro_f1", ""),
            "status": row.get("status", "ok"),
        }

    status = {
        "pipeline_id": cfg["pipeline_id"],
        "binary_eval_rows": len(binary),
        "embedding_rows": len(emb),
        "sf5_candidate_summary": str(sf5_path) if sf5_path.exists() else "",
        "anchor_formula": str(formula_path) if formula_path.exists() else "",
        "model_summary": model_summary,
        "embedding_summary": emb_summary,
        "sf5_summary": sf5_summary,
        "formula_keys": sorted(formula.keys()) if formula else [],
    }
    (summaries / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")

    report = reports / "FINAL_REPORT.md"
    lines = [
        f"# FINAL REPORT: {cfg['pipeline_id']}",
        "",
        "Status: generated summary. This is a single-seed screen and is not claim-grade.",
        "",
        "## Output Files",
        f"- Binary eval: `{summaries / 'binary_eval.tsv'}`",
        f"- Embedding: `{summaries / 'embedding_bg_unknown.tsv'}`",
        f"- SF5 candidates: `{reports / 'sf5_candidate_summary.json'}`",
        f"- Anchor formula: `{reports / 'anchor_formula' / 'anchor_formula_results.json'}`",
        "",
        "## Binary Model Summary",
    ]
    for model, vals in model_summary.items():
        lines.append(f"- `{model}`: n={vals['n']} mean_TE_F1={vals['mean_te_f1']:.4f} min={vals['min_te_f1']:.4f} max={vals['max_te_f1']:.4f}")
    lines.extend(["", "## Embedding Summary"])
    for key, vals in emb_summary.items():
        lines.append(f"- `{key}`: ARI={vals['ari']} NMI={vals['nmi']} holdout_macro_F1={vals['holdout_macro_f1']} status={vals['status']}")
    if sf5_summary:
        lines.extend(["", "## SF5 Candidate Summary", "```json", json.dumps(sf5_summary, indent=2), "```"])
    if formula:
        dep = formula.get("deployable_linear", {})
        aware = formula.get("annotation_aware_linear", {})
        lines.extend([
            "",
            "## Anchor Formula Summary",
            f"- deployable_linear: status={dep.get('status')} R2={dep.get('r2')} LOO_RMSE={dep.get('leave_species_out_rmse')}",
            f"- annotation_aware_linear: status={aware.get('status')} R2={aware.get('r2')} LOO_RMSE={aware.get('leave_species_out_rmse')}",
        ])
    report.write_text("\n".join(lines) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
