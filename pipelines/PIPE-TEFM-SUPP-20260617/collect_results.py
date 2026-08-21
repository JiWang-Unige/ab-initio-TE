#!/usr/bin/env python3
"""Collect JSON metrics from PIPE-TEFM-SUPP-20260617 into TSV summaries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="reports/tefm_supp/PIPE-TEFM-SUPP-20260617")
    ap.add_argument("--out-tsv", default="reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summary.tsv")
    args = ap.parse_args()
    rows = []
    for path in sorted(Path(args.root).rglob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        row = {"path": str(path)}
        row.update({k: data.get(k) for k in [
            "model", "model_key", "window", "stage", "species", "te_f1",
            "te_precision", "te_recall", "te_auprc", "macro_f1", "n_windows",
        ]})
        rows.append(row)
    keys = ["path", "stage", "model_key", "model", "window", "species", "te_f1",
            "te_precision", "te_recall", "te_auprc", "macro_f1", "n_windows"]
    out = Path(args.out_tsv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as handle:
        handle.write("\t".join(keys) + "\n")
        for row in rows:
            handle.write("\t".join("" if row.get(k) is None else str(row.get(k)) for k in keys) + "\n")
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
