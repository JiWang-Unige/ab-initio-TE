#!/usr/bin/env python3
"""Summarize Unknown/high-score fragment evidence for interpretability planning."""
from __future__ import annotations

import collections
import gzip
import json
import importlib.util
import math
from pathlib import Path

import pandas as pd


EXP_ID = "PIPE-TEFM-FINAL-INTERPRET-20260630"
FRAGMENTS = Path("software_outputs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/fragments/unknown_highscore_len512.jsonl.gz")
SF5 = Path("reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/sf5_candidate_predictions.tsv")


def shannon(seq: str) -> float:
    counts = collections.Counter(seq.upper())
    total = sum(counts.get(b, 0) for b in "ACGT")
    if total == 0:
        return 0.0
    return -sum((counts[b] / total) * math.log(counts[b] / total, 2) for b in "ACGT" if counts[b] > 0)


def max_homopolymer(seq: str) -> int:
    best = cur = 0
    prev = ""
    for base in seq.upper():
        if base == prev:
            cur += 1
        else:
            prev = base
            cur = 1
        best = max(best, cur)
    return best


def top_kmer(seq: str, k: int = 6) -> tuple[str, int, float]:
    seq = seq.upper()
    counts = collections.Counter(seq[i : i + k] for i in range(max(0, len(seq) - k + 1)) if set(seq[i : i + k]) <= set("ACGT"))
    if not counts:
        return "", 0, 0.0
    mer, count = counts.most_common(1)[0]
    return mer, count, count / max(1, sum(counts.values()))


def read_fragments() -> pd.DataFrame:
    rows = []
    with gzip.open(FRAGMENTS, "rt") as handle:
        for idx, line in enumerate(handle):
            rec = json.loads(line)
            seq = rec.get("sequence", "").upper()
            gc = (seq.count("G") + seq.count("C")) / max(1, sum(1 for c in seq if c in "ACGT"))
            mer, mer_n, mer_frac = top_kmer(seq)
            rows.append(
                {
                    "idx": idx,
                    "source": rec.get("source", ""),
                    "species": rec.get("species", ""),
                    "chrom": rec.get("chrom", ""),
                    "start": rec.get("start", ""),
                    "end": rec.get("end", ""),
                    "label_name": rec.get("label_name", ""),
                    "rep_class": rec.get("rep_class", ""),
                    "rep_family": rec.get("rep_family", ""),
                    "binary_mean_prob": rec.get("binary_mean_prob", math.nan),
                    "gc": gc,
                    "entropy_2bit_max": shannon(seq),
                    "max_homopolymer": max_homopolymer(seq),
                    "top_6mer": mer,
                    "top_6mer_count": mer_n,
                    "top_6mer_frac": mer_frac,
                    "sequence_prefix80": seq[:80],
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    out = Path("reports/tefm_final") / EXP_ID
    out.mkdir(parents=True, exist_ok=True)
    frag = read_fragments()
    sf5 = pd.read_csv(SF5, sep="\t")
    merged = frag.merge(
        sf5[
            [
                "source",
                "species",
                "chrom",
                "start",
                "end",
                "sf5_best_main4",
                "sf5_best_main4_frac",
                "sf5_unknown_frac",
                "sf5_bg_frac",
            ]
        ],
        on=["source", "species", "chrom", "start", "end"],
        how="left",
    )
    merged.to_csv(out / "fragment_feature_table.tsv", sep="\t", index=False)
    numeric = ["gc", "entropy_2bit_max", "max_homopolymer", "top_6mer_frac", "binary_mean_prob", "sf5_best_main4_frac", "sf5_unknown_frac", "sf5_bg_frac"]
    summary = merged.groupby("source")[numeric].agg(["count", "mean", "std", "min", "max"]).reset_index()
    summary.columns = ["_".join([str(x) for x in c if x]) if isinstance(c, tuple) else c for c in summary.columns]
    summary.to_csv(out / "source_feature_summary.tsv", sep="\t", index=False)
    high = merged[merged["source"] == "high_score_strict_bg"].copy()
    high = high.sort_values("binary_mean_prob", ascending=False)
    high.to_csv(out / "high_score_strict_bg_cases.tsv", sep="\t", index=False)
    unknown = merged[merged["source"] == "unknown_annotation"].copy()
    unknown_main4 = unknown.sort_values("sf5_best_main4_frac", ascending=False).head(30)
    unknown_main4.to_csv(out / "unknown_main4_like_top30.tsv", sep="\t", index=False)
    pdf_available = importlib.util.find_spec("pypdf") is not None
    pdf_note = (
        "docs/inputs PDFs are present and pypdf is available; see pdf_method_alignment.md for keyword-level method scoping."
        if pdf_available
        else "docs/inputs PDFs are present, but no local PDF text extraction library is installed in this environment."
    )
    status = {
        "ok": True,
        "exp_id": EXP_ID,
        "fragment_rows": int(len(merged)),
        "source_counts": {str(k): int(v) for k, v in merged["source"].value_counts().items()},
        "high_score_n": int(len(high)),
        "high_score_mean_binary_prob": float(high["binary_mean_prob"].mean()) if len(high) else math.nan,
        "high_score_mean_sf5_bg_frac": float(high["sf5_bg_frac"].mean()) if len(high) else math.nan,
        "unknown_n": int(len(unknown)),
        "unknown_mean_best_main4_frac": float(unknown["sf5_best_main4_frac"].mean()) if len(unknown) else math.nan,
        "outputs": {
            "feature_table": str(out / "fragment_feature_table.tsv"),
            "source_summary": str(out / "source_feature_summary.tsv"),
            "high_score_cases": str(out / "high_score_strict_bg_cases.tsv"),
            "unknown_main4_like": str(out / "unknown_main4_like_top30.tsv"),
        },
        "pdf_note": pdf_note,
    }
    (out / "current_status.json").write_text(json.dumps(status, indent=2) + "\n")
    report = [
        f"# {EXP_ID}",
        "",
        "## Summary",
        "",
        f"- Total fragment rows: {len(merged)}.",
        f"- High-score strict background rows: {len(high)}; mean binary probability {status['high_score_mean_binary_prob']:.4f}; mean SF5 background fraction {status['high_score_mean_sf5_bg_frac']:.4f}.",
        f"- Unknown annotation rows: {len(unknown)}; mean best-main4 SF5 fraction {status['unknown_mean_best_main4_frac']:.4f}.",
        "",
        "## Interpretation",
        "",
        "- The existing high-score strict-background candidates do not currently support a hidden-TE claim: they are high under the binary model but almost entirely BG under SF5.",
        "- Unknown-annotation fragments are more promising for annotation audit because many have strong main4-like SF5 signal.",
        "- The next interpretability step should target two contrasts: high-score strict-BG versus matched BG, and Unknown-main4-like versus known main4, using saliency/occlusion/k-mer motif enrichment on the same 512 bp fragments.",
        "- Full model-level paper-method alignment remains pending; PDF keyword-level method scoping is available in `pdf_method_alignment.md` when `pypdf` is installed.",
        "",
        "## Outputs",
        "",
        "- `fragment_feature_table.tsv`",
        "- `source_feature_summary.tsv`",
        "- `high_score_strict_bg_cases.tsv`",
        "- `unknown_main4_like_top30.tsv`",
    ]
    (out / "INTERPRETABILITY_REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
