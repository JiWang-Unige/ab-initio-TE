#!/usr/bin/env python3
"""Plot the completed fixed GENERanno diagnostic; no fitting or selection."""
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
    rows = {row["model_id"]: row for row in result["models"]}
    ids = ["pretrained", "binary_finetuned", "multiclass_finetuned"]
    names = ["Pretrained", "Binary FT (human)", "Class FT (six species)"]
    colors = ["#737B87", "#337EB3", "#CC7145"]
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), gridspec_kw={"width_ratios": [1, 1, 1.3]})
    endpoints = ["known_five", "full_eight", "conditional_te_four"]
    labels = ["BG + TE4", "Full 8", "True TE4"]
    x = np.arange(3)
    for model_id, name, color in zip(ids, names, colors):
        row = rows[model_id]
        axes[0].plot(x, [row[f"{e}_knn_macro_f1"] for e in endpoints],
                     marker="o", color=color, label=name)
        axes[1].plot(x, [row[f"{e}_kmeans_k{k}_ari"] for e, k in zip(endpoints, [5, 8, 4])],
                     marker="o", color=color)
    for ax in axes[:2]:
        ax.set_xticks(x, labels)
    axes[0].set(title="A  Supervised 5-NN readout", ylabel="Test macro-F1", ylim=(0, 1))
    axes[1].set(title="B  TRAIN-fitted K-means", ylabel="Test adjusted Rand index", ylim=(0, .4))
    species = list(rows[ids[0]]["knn_by_species"]["known_five"])
    display = {"c_elegans": "Worm", "chicken": "Chicken", "fruit_fly": "Fly",
               "mouse": "Mouse", "western_clawed_frog": "Frog", "zebrafish": "Zebrafish"}
    for model_id, color in zip(ids, colors):
        metrics = rows[model_id]["knn_by_species"]["known_five"]
        axes[2].plot(np.arange(len(species)), [metrics[s]["macro_f1"] for s in species],
                     marker="o", color=color)
    axes[2].set_xticks(np.arange(len(species)), [display.get(s, s) for s in species], rotation=25)
    axes[2].set(title="C  BG + TE4 readout by species", ylabel="Test macro-F1", ylim=(0, 1))
    for ax in axes:
        ax.grid(axis="y", alpha=.18)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=3,
               bbox_to_anchor=(.5, .085), frameon=False)
    fig.text(.5, .025,
             "Same 1,580 TEST records; fixed K. Known/TE-only clustering subsets use annotations. "
             "Training species/objectives differ; no causal objective comparison.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .16, 1, 1))
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(args.report_dir / f"paired-generanno-readout.{suffix}", dpi=180)


if __name__ == "__main__":
    main()
