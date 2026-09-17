#!/usr/bin/env python3
"""Plot the fixed 20-core D utility result, without re-fitting or selection."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-dir", type=Path, required=True)
    args = ap.parse_args()
    result = json.loads((args.report_dir / "result.json").read_text())
    arms = ["U_nosm", "U_soft", "P", "R_all", "R_TE", "D"]
    names = ["Official nosm", "Unmasked / soft receiver", "P3 mask", "RM all repeats", "RM TE", "D mask"]
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1, 1.15]})
    scores = [result["metrics"][arm]["f1"] for arm in arms]
    axes[0].barh(names, scores, color=["#9CA4AD"] * 5 + ["#267A8A"])
    for i, score in enumerate(scores):
        axes[0].text(score + .008, i, f"{score:.4f}", va="center")
    axes[0].set(xlim=(0, .7), xlabel="Pooled reference-relative F1",
                title="A  Exact CDS-chain / locus matching")
    controls = ["U_soft", "U_nosm", "R_TE", "R_all", "P"]
    comparison_names = ["D − U_soft", "D − U_nosm", "D − RM TE", "D − RM all", "D − P3"]
    y = np.arange(len(controls))
    for i, control in enumerate(controls):
        row = result["comparisons"][f"D_minus_{control}"]
        point = row["f1_delta"] * 100
        low, high = [x * 100 for x in row["bootstrap"]["ci95"]]
        color = "#267A8A" if control.startswith("U_") else "#737B87"
        axes[1].errorbar(point, i, xerr=[[point-low], [high-point]],
                         fmt="o", capsize=4, color=color)
    axes[1].axvline(0, color="#333333", lw=1, linestyle="--")
    axes[1].set_yticks(y, comparison_names)
    axes[1].invert_yaxis()
    axes[1].set(xlim=(-2, 10), xlabel="Paired F1 difference (percentage points)",
                title="B  Ten-chromosome bootstrap, 95% interval")
    for ax in axes:
        ax.grid(axis="x", alpha=.18)
        ax.set_axisbelow(True)
    fig.text(.5, .035,
             "Platypus: fixed 20 cores, 100 Mb, 639 reference loci. "
             "D vs U_soft: 49 gains / 18 losses. Comparator annotation, not independent biological truth.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .08, 1, 1))
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(args.report_dir / f"d-tiberius-utility.{suffix}", dpi=180)
    svg = args.report_dir / "d-tiberius-utility.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")


if __name__ == "__main__":
    main()
