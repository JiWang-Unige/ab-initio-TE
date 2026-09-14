#!/usr/bin/env python3
"""Plot completed fixed-panel adaptation and original-species retention."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / "reports/D-ADAPTER-MOE-PILOT-20260914/sea-12709175/sea-summary.json"
data = json.loads(source.read_text())
out = ROOT / "docs/manuscript/20260914/figures"
out.mkdir(parents=True, exist_ok=True)
arms = ["D_historical_six_species_calibration", "D_sea_cal_recalibrated",
        "dense_residual_adapter", "two_expert_soft_gate_residual_adapter", "constant_average_experts"]
labels = ["D\nhistorical\nCAL", "D\nsea CAL", "Dense\nadapter", "Gated\n2 experts", "Average\n2 experts"]
colors = ["#7F8B96", "#354A5F", "#1B8A84", "#CC7744", "#8271A1"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "svg.fonttype": "none"})
fig, axes = plt.subplots(1, 3, figsize=(14, 5.1), gridspec_kw={"width_ratios": [1, 1, 1.25]})
for ax, key, title in zip(axes[:2], ["macro_bp_f1", "macro_segment_f1_iou_0_8"],
                         ["A  Sea-urchin bp agreement", "B  Sea-urchin fragment agreement"]):
    values = [data["arms"][name]["eval"]["summary"][key] for name in arms]
    bars = ax.bar(np.arange(5), values, color=colors, width=.72)
    ax.bar_label(bars, labels=[f"{v:.3f}" for v in values], padding=4, fontsize=9)
    ax.set_xticks(np.arange(5), labels)
    ax.set_ylim(0, 1 if key == "macro_bp_f1" else .25)
    ax.set_ylabel("Comparator bp-F1" if key == "macro_bp_f1" else "Comparator segment-F1 at IoU 0.8")
    ax.set_title(title, loc="left", fontsize=10.5, weight="bold", pad=13)
    ax.grid(axis="y", color="#E5E8EB", linewidth=.6)
    ax.set_axisbelow(True)
retention = data["retention"]
direct = [retention["D_sea_cal_recalibrated_direct_on_six_dev"]["dev"]["summary"]["macro_bp_f1"]]
refit = [retention["D_recalibrated_six_species_cal_refit"]["dev"]["summary"]["macro_bp_f1"]]
for arm in arms[2:]:
    item = retention["adapted_heads"][arm]
    direct.append(item["sea_selected_calibration_direct_on_six_dev"]["dev"]["summary"]["macro_bp_f1"])
    refit.append(item["six_species_cal_refit"]["dev"]["summary"]["macro_bp_f1"])
ax = axes[2]
x = np.arange(4)
for offset, values, label, color in [(-.19, direct, "Sea-selected CAL", "#D0A581"),
                                      (.19, refit, "Original-six CAL refit", "#354A5F")]:
    bars = ax.bar(x + offset, values, width=.36, color=color, label=label)
    ax.bar_label(bars, labels=[f"{v:.3f}" for v in values], padding=3, fontsize=8)
ax.axhline(refit[0], color="#1B8A84", linestyle="--", linewidth=1)
ax.set_xticks(x, ["Frozen D", "Dense\nadapter", "Gated\n2 experts", "Average\n2 experts"])
ax.set_ylim(0, 1)
ax.set_ylabel("Macro bp-F1 on original six-species DEV")
ax.set_title("C  Retention after sea adaptation", loc="left", fontsize=10.5, weight="bold", pad=13)
ax.grid(axis="y", color="#E5E8EB", linewidth=.6)
ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="none", framealpha=1, fontsize=8)
fig.subplots_adjust(left=.055, right=.992, top=.84, bottom=.29, wspace=.30)
fig.suptitle("Adaptation improves sea-urchin material agreement, with topology and retention costs",
             x=.055, y=.985, ha="left", fontsize=13, weight="bold")
fig.text(.055, .035, "Exploratory, seed 42. Sea regions 1–2 TRAIN, 3 CAL, 4 EVAL; the panel was previously viewed.\n"
         "All sea arms use the same uncertain-label mask. Original-six retention uses 32 DEV tiles per species.\n"
         "The reference is an uncurated-library comparator, not independent truth. Panels A–C have different endpoints.",
         ha="left", va="bottom", fontsize=8.5, color="#414951")
for suffix in ("png", "pdf", "svg"):
    fig.savefig(out / f"sea-adaptation-retention.{suffix}", dpi=200)
plt.close(fig)
print(source.relative_to(ROOT))
