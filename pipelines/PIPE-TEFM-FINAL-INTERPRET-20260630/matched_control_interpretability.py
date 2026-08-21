#!/usr/bin/env python3
"""Matched-control checks for short TE interpretability candidates.

This is a local synthesis script. It reads completed fragment/SF5 artifacts,
builds composition-matched controls for two contrasts, and extracts lightweight
method notes from the requested PDFs when pypdf is available.
"""

from __future__ import annotations

import collections
import gzip
import json
import math
import re
from pathlib import Path

import pandas as pd


EXP_ID = "PIPE-TEFM-FINAL-INTERPRET-20260630"
ROOT = Path(".")
REPORT_DIR = ROOT / "reports" / "tefm_final" / EXP_ID
FRAGMENT_TABLE = REPORT_DIR / "fragment_feature_table.tsv"
FRAGMENT_JSONL = (
    ROOT
    / "software_outputs"
    / "tefm_anchor"
    / "PIPE-TEFM-ANCHOR-20260621"
    / "fragments"
    / "unknown_highscore_len512.jsonl.gz"
)
PDFS = [
    ROOT / "docs" / "inputs" / "1703.01365v2.pdf",
    ROOT / "docs" / "inputs" / "2009.07896v1.pdf",
    ROOT / "docs" / "inputs" / "ocag070.pdf",
]


MATCH_FEATURES = ["gc", "entropy_2bit_max", "top_6mer_frac", "max_homopolymer"]
DNA_RE = re.compile("[^ACGT]")


def read_sequences() -> dict[int, str]:
    seqs: dict[int, str] = {}
    with gzip.open(FRAGMENT_JSONL, "rt") as handle:
        for idx, line in enumerate(handle):
            rec = json.loads(line)
            seqs[idx] = rec["sequence"].upper()
    return seqs


def zscore_frame(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in features:
        vals = pd.to_numeric(out[col], errors="coerce")
        mean = vals.mean()
        std = vals.std(ddof=0)
        if not math.isfinite(std) or std == 0:
            std = 1.0
        out[f"z_{col}"] = (vals - mean) / std
    return out


def nearest_match(
    cases: pd.DataFrame,
    pool: pd.DataFrame,
    contrast: str,
    extra_group_col: str | None = None,
) -> pd.DataFrame:
    rows = []
    used: set[int] = set()
    combo = pd.concat([cases, pool], ignore_index=True)
    combo = zscore_frame(combo, MATCH_FEATURES)
    case_z = combo.iloc[: len(cases)].copy()
    pool_z = combo.iloc[len(cases) :].copy()

    for _, case in case_z.iterrows():
        candidates = pool_z[~pool_z["idx"].isin(used)].copy()
        if extra_group_col and pd.notna(case.get(extra_group_col)):
            grouped = candidates[candidates[extra_group_col] == case[extra_group_col]]
            if len(grouped) > 0:
                candidates = grouped
        if len(candidates) == 0:
            candidates = pool_z.copy()
        dist = 0.0
        for feat in MATCH_FEATURES:
            dist = dist + (candidates[f"z_{feat}"] - case[f"z_{feat}"]) ** 2
        candidates = candidates.assign(match_distance=dist.pow(0.5))
        match = candidates.sort_values(["match_distance", "idx"]).iloc[0]
        used.add(int(match["idx"]))
        row = {
            "contrast": contrast,
            "case_idx": int(case["idx"]),
            "control_idx": int(match["idx"]),
            "case_source": case["source"],
            "control_source": match["source"],
            "case_species": case["species"],
            "control_species": match["species"],
            "case_chrom": case["chrom"],
            "control_chrom": match["chrom"],
            "case_label": case["label_name"],
            "control_label": match.get("label_name", match.get("sf5_best_main4_for_match", "")),
            "case_sf5_best_main4": case.get("sf5_best_main4", ""),
            "control_sf5_best_main4": match.get("sf5_best_main4", ""),
            "match_distance": float(match["match_distance"]),
        }
        for feat in MATCH_FEATURES:
            row[f"case_{feat}"] = case[feat]
            row[f"control_{feat}"] = match[feat]
            row[f"delta_{feat}"] = float(case[feat]) - float(match[feat])
        rows.append(row)
    return pd.DataFrame(rows)


def kmer_counts(seqs: list[str], k: int = 6) -> collections.Counter[str]:
    counts: collections.Counter[str] = collections.Counter()
    for seq in seqs:
        clean = DNA_RE.sub("N", seq.upper())
        for i in range(0, max(0, len(clean) - k + 1)):
            kmer = clean[i : i + k]
            if "N" not in kmer:
                counts[kmer] += 1
    return counts


def kmer_enrichment(
    feature_df: pd.DataFrame,
    pairs: pd.DataFrame,
    contrast: str,
    top_n: int = 30,
) -> pd.DataFrame:
    sub = pairs[pairs["contrast"] == contrast]
    case_seqs = feature_df.set_index("idx").loc[sub["case_idx"], "sequence"].tolist()
    ctrl_seqs = feature_df.set_index("idx").loc[sub["control_idx"], "sequence"].tolist()
    case_counts = kmer_counts(case_seqs)
    ctrl_counts = kmer_counts(ctrl_seqs)
    total_case = sum(case_counts.values())
    total_ctrl = sum(ctrl_counts.values())
    all_kmers = set(case_counts) | set(ctrl_counts)
    rows = []
    for kmer in all_kmers:
        c = case_counts[kmer]
        b = ctrl_counts[kmer]
        case_rate = (c + 0.5) / (total_case + 0.5 * max(1, len(all_kmers)))
        ctrl_rate = (b + 0.5) / (total_ctrl + 0.5 * max(1, len(all_kmers)))
        rows.append(
            {
                "contrast": contrast,
                "kmer": kmer,
                "case_count": c,
                "control_count": b,
                "case_rate": case_rate,
                "control_rate": ctrl_rate,
                "log2_fold_case_vs_control": math.log2(case_rate / ctrl_rate),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["abs_log2_fold"] = out["log2_fold_case_vs_control"].abs()
    return out.sort_values(["abs_log2_fold", "case_count"], ascending=[False, False]).head(top_n)


def group_summary(feature_df: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    idxed = feature_df.set_index("idx")
    for contrast in sorted(pairs["contrast"].unique()):
        sub = pairs[pairs["contrast"] == contrast]
        for side, col in [("case", "case_idx"), ("control", "control_idx")]:
            data = idxed.loc[sub[col]].copy()
            row = {
                "contrast": contrast,
                "side": side,
                "n": len(data),
                "species": ",".join(sorted(map(str, data["species"].dropna().unique()))[:8]),
                "chrom": ",".join(sorted(map(str, data["chrom"].dropna().unique()))[:8]),
            }
            for feat in MATCH_FEATURES:
                vals = pd.to_numeric(data[feat], errors="coerce")
                row[f"{feat}_mean"] = vals.mean()
                row[f"{feat}_sd"] = vals.std(ddof=1)
            if "sf5_best_main4_frac" in data:
                row["sf5_best_main4_frac_mean"] = pd.to_numeric(
                    data["sf5_best_main4_frac"], errors="coerce"
                ).mean()
                row["sf5_bg_frac_mean"] = pd.to_numeric(
                    data["sf5_bg_frac"], errors="coerce"
                ).mean()
            rows.append(row)
    return pd.DataFrame(rows)


def match_quality(pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for contrast, sub in pairs.groupby("contrast"):
        row = {"contrast": contrast, "n_pairs": len(sub)}
        for feat in MATCH_FEATURES:
            vals = pd.to_numeric(sub[f"delta_{feat}"], errors="coerce").abs()
            row[f"abs_delta_{feat}_mean"] = vals.mean()
            row[f"abs_delta_{feat}_max"] = vals.max()
        row["match_distance_mean"] = pd.to_numeric(sub["match_distance"], errors="coerce").mean()
        row["match_distance_max"] = pd.to_numeric(sub["match_distance"], errors="coerce").max()
        row["quality_flag"] = (
            "POOR_GC_MATCH"
            if row["abs_delta_gc_mean"] > 0.10
            else "ACCEPTABLE_COMPOSITION_SCREEN"
        )
        rows.append(row)
    return pd.DataFrame(rows)


def extract_pdf_notes() -> tuple[str, dict[str, object]]:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - depends on local env
        return (
            "# PDF Method Alignment\n\n"
            f"PDF extraction unavailable: `{type(exc).__name__}: {exc}`.\n",
            {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
        )

    keywords = [
        "saliency",
        "occlusion",
        "motif",
        "k-mer",
        "kmer",
        "interpret",
        "attention",
        "attribution",
        "in silico mutagenesis",
        "integrated gradients",
    ]
    lines = ["# PDF Method Alignment", ""]
    status: dict[str, object] = {"ok": True, "pdfs": {}}
    for pdf in PDFS:
        pdf_status: dict[str, object] = {"exists": pdf.exists()}
        lines.append(f"## {pdf.name}")
        if not pdf.exists():
            lines.append("- Missing.")
            status["pdfs"][pdf.name] = pdf_status
            continue
        reader = PdfReader(str(pdf))
        text_parts = []
        for page in reader.pages[:8]:
            try:
                text_parts.append(page.extract_text() or "")
            except Exception:
                text_parts.append("")
        text = "\n".join(text_parts)
        lower = text.lower()
        hits = {kw: lower.count(kw) for kw in keywords if lower.count(kw) > 0}
        title = ""
        for line in text.splitlines()[:25]:
            clean = " ".join(line.split())
            if len(clean) >= 12 and not clean.lower().startswith("arxiv"):
                title = clean
                break
        pdf_status.update({"pages_scanned": min(8, len(reader.pages)), "keyword_hits": hits})
        status["pdfs"][pdf.name] = pdf_status
        lines.append(f"- Pages scanned: {pdf_status['pages_scanned']}")
        if title:
            lines.append(f"- First title-like line: {title[:180]}")
        if hits:
            lines.append("- Keyword hits: " + ", ".join(f"{k}={v}" for k, v in sorted(hits.items())))
        else:
            lines.append("- Keyword hits: none in first scanned pages.")
        lines.append("")
    lines.extend(
        [
            "## Conservative alignment decision",
            "",
            "- Matched controls and k-mer enrichment are aligned with the reviewers' requested sanity checks.",
            "- Model-level saliency/occlusion remains pending; this script does not load a TE model or perform attribution.",
            "- Any manuscript text should cite this as method scoping, not as completed mechanistic interpretation.",
        ]
    )
    return "\n".join(lines) + "\n", status


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(FRAGMENT_TABLE, sep="\t")
    seqs = read_sequences()
    df["sequence"] = df["idx"].map(seqs)
    for col in MATCH_FEATURES + ["sf5_best_main4_frac", "sf5_bg_frac", "sf5_unknown_frac"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    high_cases = df[df["source"] == "high_score_strict_bg"].copy()
    high_pool = df[
        (df["source"] == "background_strict_negative")
        & (df["species"].isin(high_cases["species"].unique()))
        & (df["chrom"].isin(high_cases["chrom"].unique()))
    ].copy()
    high_pairs = nearest_match(
        high_cases,
        high_pool,
        "high_score_strict_bg_vs_matched_bg",
    )

    unknown_cases = df[
        (df["source"] == "unknown_annotation")
        & (df["species"] == "human")
        & (df["sf5_best_main4_frac"] >= 0.8)
        & (df["sf5_best_main4"].isin(["DNA", "LINE", "LTR", "SINE"]))
    ].copy()
    known_pool = df[
        (df["source"] == "known_main4")
        & (df["species"] == "human")
        & (df["label_name"].isin(["DNA", "LINE", "LTR", "SINE"]))
    ].copy()
    known_pool = known_pool.rename(columns={"label_name": "sf5_best_main4_for_match"})
    unknown_cases["sf5_best_main4_for_match"] = unknown_cases["sf5_best_main4"]
    unknown_pairs = nearest_match(
        unknown_cases,
        known_pool,
        "unknown_main4like_vs_matched_known_main4",
        extra_group_col="sf5_best_main4_for_match",
    )

    pairs = pd.concat([high_pairs, unknown_pairs], ignore_index=True)
    pairs.to_csv(REPORT_DIR / "matched_control_pairs.tsv", sep="\t", index=False)
    summary = group_summary(df, pairs)
    summary.to_csv(REPORT_DIR / "matched_group_summary.tsv", sep="\t", index=False)
    quality = match_quality(pairs)
    quality.to_csv(REPORT_DIR / "matched_quality_summary.tsv", sep="\t", index=False)

    kmer_tables = []
    for contrast in pairs["contrast"].unique():
        kmer_tables.append(kmer_enrichment(df, pairs, contrast))
    kmer = pd.concat(kmer_tables, ignore_index=True) if kmer_tables else pd.DataFrame()
    kmer.to_csv(REPORT_DIR / "matched_kmer_enrichment.tsv", sep="\t", index=False)

    pdf_md, pdf_status = extract_pdf_notes()
    (REPORT_DIR / "pdf_method_alignment.md").write_text(pdf_md)

    status = {
        "ok": True,
        "exp_id": EXP_ID,
        "high_score_cases": int(len(high_cases)),
        "high_score_control_pool": int(len(high_pool)),
        "high_score_pairs": int(len(high_pairs)),
        "unknown_main4like_cases_ge_0p8": int(len(unknown_cases)),
        "unknown_known_control_pool": int(len(known_pool)),
        "unknown_pairs": int(len(unknown_pairs)),
        "pdf_extraction": pdf_status,
        "outputs": {
            "matched_control_pairs": str(REPORT_DIR / "matched_control_pairs.tsv"),
            "matched_group_summary": str(REPORT_DIR / "matched_group_summary.tsv"),
            "matched_quality_summary": str(REPORT_DIR / "matched_quality_summary.tsv"),
            "matched_kmer_enrichment": str(REPORT_DIR / "matched_kmer_enrichment.tsv"),
            "pdf_method_alignment": str(REPORT_DIR / "pdf_method_alignment.md"),
        },
    }
    (REPORT_DIR / "matched_control_status.json").write_text(json.dumps(status, indent=2))

    report = [
        f"# {EXP_ID} matched-control sanity check",
        "",
        "## Summary",
        "",
        f"- High-score strict-BG cases matched: {len(high_pairs)} / {len(high_cases)} from a same-species/same-chromosome BG pool of {len(high_pool)}.",
        f"- Unknown main4-like cases at SF5 best-main4 fraction >= 0.8 matched: {len(unknown_pairs)} / {len(unknown_cases)} from a human known-main4 pool of {len(known_pool)}.",
        "- This is a composition/control sanity analysis, not model-level saliency or occlusion.",
        f"- Match-quality flags: {', '.join(quality['contrast'] + '=' + quality['quality_flag'])}.",
        "",
        "## Interpretation",
        "",
        "- The high-score strict-BG contrast is now controlled within western_honey_bee GroupUn, but sample size remains only 9. Use it to diagnose binary false-positive triggers, not hidden TE prevalence.",
        "- The Unknown-main4-like contrast has enough cases for audit prioritization, but match quality must be checked before interpreting it as true main4 relabeling.",
        "- If the Unknown contrast is flagged as `POOR_GC_MATCH`, treat the signal as a high-GC/SVA/model-bias audit first, not as annotation correction.",
        "- K-mer enrichment is descriptive and must be followed by model occlusion/saliency before mechanistic claims.",
        "- PDF text extraction was attempted with pypdf; see `pdf_method_alignment.md` for extracted keyword-level alignment.",
    ]
    (REPORT_DIR / "MATCHED_CONTROL_REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
