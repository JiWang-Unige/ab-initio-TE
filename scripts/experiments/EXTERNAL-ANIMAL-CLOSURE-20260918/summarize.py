#!/usr/bin/env python3
"""Summarize qualification and completed fixed external scores."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for quality in sorted(args.reports.glob("*/quality.json")):
        result = json.loads(quality.read_text())
        score_path = quality.parent / "score" / "result.json"
        score = json.loads(score_path.read_text()) if score_path.exists() else None
        rows.append((result, score))
    text = ["# External animal closure: fixed label-rich vertebrate panel", "",
            "Species and 20 × 5-MiB regions were fixed from source contig lengths before any model output was read.", "",
            "| Species | Assembly | Full-source known TE bp | Panel known TE bp | Panel fraction | Qualification | Positive recovery | Source-comparator F1 |", "|---|---|---:|---:|---:|---|---:|---:|"]
    for quality, score in rows:
        metrics = quality["quality_metrics"]
        recovery = score["pooled"]["positive_recovery"] if score else None
        comparator = score["pooled"].get("source_comparator") if score else None
        comparator_f1 = comparator.get("f1") if comparator else None
        recovery_text = f"{recovery:.2%}" if recovery is not None else "pending"
        f1_text = f"{comparator_f1:.2%}" if comparator_f1 is not None else "pending"
        text.append(f"| {quality['scientific_name']} | {quality['assembly']} | {metrics['full_assembly_known_te_bp_union']:,} | {metrics['selected_panel_known_te_bp_union']:,} | {metrics['selected_panel_positive_fraction']:.2%} | {quality['status']} | {recovery_text} | {f1_text} |")
    text += ["", "The historical RepeatMasker layer is source-dependent and is used to quantify documented positive-layer recovery. The source-comparator F1 excludes Unknown/ambiguous/ARTEFACT intervals and defines remaining callable non-positive bases as comparator background; it is not biological truth. No whole-genome or independent truth claim is made.", ""]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(text))


if __name__ == "__main__":
    main()
