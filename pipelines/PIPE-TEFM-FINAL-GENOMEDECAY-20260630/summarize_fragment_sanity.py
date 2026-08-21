#!/usr/bin/env python3
"""Summarize forward/RC/oracle fragmentation sanity results."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd


EXP_ID = "PIPE-TEFM-FINAL-FRAGSANITY-20260630"
OUT_DIR = Path("reports/tefm_final") / EXP_ID


def read_tsv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, sep="\t")


def pick_headline(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[(df["iou_threshold"] == 0.8) & (df["boundary_tol_bp"] == 5)].copy()


def write_report(headline: pd.DataFrame, out_dir: Path, source_tsv: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    if headline.empty:
        report = "# PIPE-TEFM-FINAL-FRAGSANITY-20260630\n\nNo headline rows found.\n"
        (out_dir / "FRAGMENT_SANITY_REPORT.md").write_text(report)
        return {"ok": False, "reason": "no_headline_rows"}

    def row(mode: str, post: str):
        sub = headline[(headline["merge_mode"] == mode) & (headline["postprocess"] == post)]
        return sub.iloc[0] if not sub.empty else None

    forward_raw = row("forward", "raw_threshold")
    forward_crf = row("forward", "crf_style_penalty4")
    best_non_oracle = headline[~headline["postprocess"].str.startswith("oracle")].sort_values("segment_f1", ascending=False).iloc[0]
    best_oracle_connect = headline[headline["postprocess"] == "oracle_connect_same_true"].sort_values("segment_f1", ascending=False).iloc[0]
    best_oracle_fill = headline[headline["postprocess"] == "oracle_fill_supported_true"].sort_values("segment_f1", ascending=False).iloc[0]

    summary = {
        "ok": True,
        "source_tsv": str(source_tsv),
        "headline_iou": 0.8,
        "headline_boundary_bp": 5,
        "forward_raw_segment_f1": float(forward_raw["segment_f1"]) if forward_raw is not None else math.nan,
        "forward_crf_segment_f1": float(forward_crf["segment_f1"]) if forward_crf is not None else math.nan,
        "best_non_oracle_merge_mode": str(best_non_oracle["merge_mode"]),
        "best_non_oracle_postprocess": str(best_non_oracle["postprocess"]),
        "best_non_oracle_segment_f1": float(best_non_oracle["segment_f1"]),
        "best_non_oracle_boundary_f1": float(best_non_oracle["boundary_f1"]),
        "best_non_oracle_missed_true_rate": float(best_non_oracle["missed_true_rate"]),
        "best_oracle_connect_segment_f1": float(best_oracle_connect["segment_f1"]),
        "best_oracle_connect_boundary_f1": float(best_oracle_connect["boundary_f1"]),
        "best_oracle_fill_segment_f1": float(best_oracle_fill["segment_f1"]),
        "best_oracle_fill_boundary_f1": float(best_oracle_fill["boundary_f1"]),
    }
    comp_cols = [
        "merge_mode",
        "postprocess",
        "bp_f1",
        "segment_f1",
        "boundary_f1",
        "pred_segments",
        "segment_precision",
        "segment_recall",
        "pred_true_backed_rate",
        "short_pred_segments",
        "short_true_backed_rate",
        "mean_fragments_per_true",
        "split_true_rate",
        "missed_true_rate",
        "deleted_segments",
        "deleted_true_backed_rate",
    ]
    table = headline[comp_cols].sort_values(["postprocess", "merge_mode"])
    table.to_csv(out_dir / "fragment_sanity_headline_iou80_boundary5.tsv", sep="\t", index=False)
    best_table = headline.sort_values("segment_f1", ascending=False)[comp_cols].head(12)
    best_table.to_csv(out_dir / "fragment_sanity_best_iou80_boundary5.tsv", sep="\t", index=False)

    lines = [
        "# PIPE-TEFM-FINAL-FRAGSANITY-20260630",
        "",
        "## Scope",
        "",
        "Forward/reverse-complement inference and oracle interval-repair sanity check on animal `ntv2_250m@4096`, mouse chr1.",
        "This is a screen-grade mechanism test, not a claim-grade full-panel result.",
        "",
        "## Headline",
        "",
        f"- Source TSV: `{source_tsv}`.",
        f"- Forward raw segment-F1@IoU0.8/boundary5: {summary['forward_raw_segment_f1']:.4f}.",
        f"- Forward CRF segment-F1@IoU0.8/boundary5: {summary['forward_crf_segment_f1']:.4f}.",
        f"- Best non-oracle: `{summary['best_non_oracle_merge_mode']} + {summary['best_non_oracle_postprocess']}` segment-F1 {summary['best_non_oracle_segment_f1']:.4f}, boundary-F1 {summary['best_non_oracle_boundary_f1']:.4f}, missed true rate {summary['best_non_oracle_missed_true_rate']:.4f}.",
        f"- Best oracle-connect same true interval segment-F1: {summary['best_oracle_connect_segment_f1']:.4f}.",
        f"- Best oracle-fill supported true interval segment-F1: {summary['best_oracle_fill_segment_f1']:.4f}.",
        "",
        "## Interpretation",
        "",
        "- Double-strand inference is not uniformly helpful; max-prob merge tends to increase unsupported predictions, while conservative consensus can improve this mouse chr1 screen.",
        "- The oracle-fill upper bound is very high, meaning the bp model often touches true intervals even when the final predicted intervals are fragmented. This supports a frozen interval refiner route.",
        "- The deployable next step should not use truth-aware oracle logic; it should train a lightweight interval refiner to approximate keep/drop/merge/refine decisions from logits and local interval features.",
        "",
        "## Outputs",
        "",
        "- `fragment_sanity_headline_iou80_boundary5.tsv`",
        "- `fragment_sanity_best_iou80_boundary5.tsv`",
        "- `fragment_sanity_summary.json`",
    ]
    (out_dir / "FRAGMENT_SANITY_REPORT.md").write_text("\n".join(lines) + "\n")
    (out_dir / "fragment_sanity_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    full = OUT_DIR / "fragment_sanity/mouse_chr1_full.tsv"
    small = OUT_DIR / "fragment_sanity/mouse_chr1.tsv"
    source = full if full.exists() else small
    df = read_tsv(source)
    summary = write_report(pick_headline(df), OUT_DIR, source)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
