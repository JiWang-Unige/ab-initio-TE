#!/usr/bin/env python3
"""Collect PIPE-TEFM-SEG-SF-20260618 result tables."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_tsv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return [dict(r, source_path=str(path)) for r in csv.DictReader(handle, delimiter="\t")]


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


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-root", default="reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618")
    args = ap.parse_args()
    root = Path(args.report_root)
    summaries = root / "summaries"
    overlap = []
    edges = []
    for path in sorted((root / "overlap_segment").glob("summary_w*_s*.tsv")):
        overlap.extend(read_tsv(path))
    for path in sorted((root / "overlap_segment").glob("edge_bins_w*_s*.tsv")):
        edges.extend(read_tsv(path))
    sf = []
    run_root = Path("software_outputs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/runs")
    for path in sorted(run_root.glob("TFSF_generanno_H0_w*_seed42/test_results.json")):
        data = read_json(path)
        if data:
            data["source_path"] = str(path)
            sf.append(data)
    emb = []
    for path in sorted((root / "embedding_cluster").glob("*/*/*/metrics.json")):
        data = read_json(path)
        if data:
            data["source_path"] = str(path)
            emb.append(data)
    if overlap:
        write_tsv(summaries / "overlap_postprocess_summary.tsv", overlap)
    if edges:
        write_tsv(summaries / "edge_bin_summary.tsv", edges)
    if sf:
        write_tsv(summaries / "superfamily_summary.tsv", sf)
    if emb:
        write_tsv(summaries / "embedding_cluster_summary.tsv", emb)
    status = {
        "n_overlap_rows": len(overlap),
        "n_edge_rows": len(edges),
        "n_superfamily_rows": len(sf),
        "n_embedding_rows": len(emb),
        "report_root": str(root),
    }
    summaries.mkdir(parents=True, exist_ok=True)
    (summaries / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
