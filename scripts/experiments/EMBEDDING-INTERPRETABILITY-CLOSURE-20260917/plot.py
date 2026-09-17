#!/usr/bin/env python3
"""Plot the frozen paired readout; no fit, tuning, or sample selection."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run-12849477"
data = {
    label: json.loads((REPORT / "metrics" / key / "metrics.json").read_text())
    for label, key in [("Pretrained", "pretrained"), ("Six-species D", "six_species_D")]
}
endpoints = ["known_five", "full_eight", "conditional_te_four"]
names = ["Known five\nn = 1,281", "Full eight\nn = 1,580", "Conditional TE four\nn = 921"]
colors = ["#9bafbc", "#007c83"]
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "pdf.fonttype": 42})
fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.7), gridspec_kw={"width_ratios": [1, 1, 1.15]})
x = np.arange(3)
for idx, (label, values) in enumerate(data.items()):
    supervised = [values["supervised_knn5"][e]["macro_f1"] for e in endpoints]
    unsupervised = [values["unsupervised_kmeans"][e][k]["ari"] for e, k in zip(endpoints, ["k5", "k8", "k4"])]
    for ax, heights in zip(axes[:2], [supervised, unsupervised]):
        bars = ax.bar(x + (idx - .5) * .35, heights, width=.33, color=colors[idx], label=label)
        ax.bar_label(bars, fmt="%.3f", fontsize=8, padding=3)
axes[0].set(title="A  Supervised 5-NN readout", ylabel="Macro-F1", ylim=(0, .84))
axes[1].set(title="B  Unsupervised K-means", ylabel="Adjusted Rand index", ylim=(0, .15))
for ax in axes[:2]:
    ax.set_xticks(x, names, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=.18)
species = ["c_elegans", "chicken", "fruit_fly", "mouse", "western_clawed_frog", "zebrafish"]
species_names = ["C. elegans", "Chicken", "Fruit fly", "Mouse", "X. tropicalis", "Zebrafish"]
for y, species_id in enumerate(species):
    scores = [d["supervised_knn5"]["known_five"]["by_species"][species_id]["macro_f1"] for d in data.values()]
    axes[2].plot(scores, [y, y], color="#bac4cc", lw=2, zorder=1)
    axes[2].scatter(scores, [y, y], c=colors, s=40, zorder=2)
axes[2].set_yticks(range(6), species_names)
axes[2].invert_yaxis()
axes[2].set(title="C  Paired species readouts", xlabel="Known-five macro-F1", xlim=(.2, .75))
axes[2].spines[["top", "right"]].set_visible(False)
axes[2].grid(axis="x", alpha=.18)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5, .99), ncol=2, frameon=False)
fig.subplots_adjust(top=.82, bottom=.25, left=.055, right=.985, wspace=.48)
fig.text(.055, .075, "Same NTv2-500M backbone, sequences, splits and special-token-free pooling. K = 5 / 8 / 4; TRAIN-only fitting.", fontsize=9)
fig.text(.055, .03, "Observed comparator panel; encoder training-coordinate/homology exposure unresolved. Paired diagnostic, not an independent generalization test.", fontsize=8.5, color="#45545d")
for suffix in ("png", "pdf", "svg"):
    target = REPORT / f"paired-ntv2-readout.{suffix}"
    fig.savefig(target, dpi=180, facecolor="white")
    if suffix == "svg":
        target.write_text("\n".join(line.rstrip() for line in target.read_text().splitlines()) + "\n")
print(REPORT / "paired-ntv2-readout.png")
