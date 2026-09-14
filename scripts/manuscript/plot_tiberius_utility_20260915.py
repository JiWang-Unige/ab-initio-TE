#!/usr/bin/env python3
"""Plot the completed P3/Tiberius base-mask utility comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


EXPERIMENT = "P3-TIBERIUS-BASE-MASK-20260911-R1"
RESULT_RELATIVE = Path(
    "reports/P3-TIBERIUS-BASE-MASK-20260911-R1/full-r1-score-12710872/result.json"
)
RECHECK_RELATIVE = Path(
    "reports/P3-TIBERIUS-BASE-MASK-20260911-R1/full-r1-score-12710872/independent_recheck.json"
)
DEFAULT_OUTPUT = Path(
    "docs/manuscript/20260914/figures/tiberius-base-mask-utility"
)


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected an object in {path}")
    return value


def load_and_validate(root: Path) -> tuple[dict, dict]:
    """Load the canonical result and its independent replay before plotting."""

    result = _load_json(root / RESULT_RELATIVE)
    recheck = _load_json(root / RECHECK_RELATIVE)
    if result.get("experiment_id") != EXPERIMENT or recheck.get("experiment_id") != EXPERIMENT:
        raise ValueError("unexpected Tiberius experiment ID")
    if result.get("status") != "COMPLETED":
        raise ValueError("canonical Tiberius result is not completed")
    if recheck.get("status") != "INDEPENDENT_RECHECK_PASS":
        raise ValueError("independent Tiberius recheck did not pass")
    if result.get("claim_eligible") is not False or result.get("gate", {}).get("passed") is not False:
        raise ValueError("figure requires the recorded four-gate failure")
    if recheck.get("canonical_match", {}).get("four_gate_decision") is not True:
        raise ValueError("independent recheck did not confirm the gate decision")
    if result.get("core_count") != 20 or result.get("completed_cells") != 60:
        raise ValueError("figure requires 20 cores and 60 completed cells")
    if result.get("reference_unit_count") != 726:
        raise ValueError("figure requires the fixed 726-unit panel")

    for arm in ("P", "R", "U"):
        if result["metrics"][arm] != recheck["metrics"][arm]:
            raise ValueError(f"independent recheck differs for pooled arm {arm}")
    for comparison in ("P_minus_U", "R_minus_U", "P_minus_R"):
        canonical = result["comparisons"][comparison]
        replay = recheck["comparisons"][comparison]
        for field in ("locus_f1_delta", "recall_delta", "bootstrap"):
            if canonical[field] != replay[field]:
                raise ValueError(f"independent recheck differs for {comparison}.{field}")

    primary = result["comparisons"]["P_minus_U"]
    gained = len(primary["gained_units"])
    lost = len(primary["lost_units"])
    u_tp = int(result["metrics"]["U"]["tp"])
    if gained != 55 or lost != 16 or u_tp != 510:
        raise ValueError(f"unexpected P-U turnover counts: gained={gained}, lost={lost}, U_tp={u_tp}")
    if not np.isclose(result["lost_u_correct_fraction"], lost / u_tp):
        raise ValueError("lost U-correct fraction is inconsistent with counts")
    if not np.isclose(
        result["comparisons"]["P_minus_U"]["locus_f1_delta"],
        result["metrics"]["P"]["f1"] - result["metrics"]["U"]["f1"],
    ):
        raise ValueError("P-U delta is inconsistent with pooled F1 values")

    pu_ci = primary["bootstrap"]["ci95"]
    pr_ci = result["comparisons"]["P_minus_R"]["bootstrap"]["ci95"]
    if pu_ci[0] <= 0 or pr_ci[0] >= 0 or pr_ci[1] <= 0:
        raise ValueError("expected P-U CI above zero and P-R CI crossing zero")
    if primary["bootstrap"]["resamples"] != 10000 or primary["bootstrap"]["seed"] != 20260908:
        raise ValueError("unexpected frozen bootstrap specification")
    return result, recheck


def _save_figure(fig: plt.Figure, output_prefix: Path) -> None:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf", "svg"):
        fig.savefig(
            output_prefix.with_suffix(f".{extension}"),
            dpi=300,
            bbox_inches="tight",
        )
    plt.close(fig)


def make_figure(result: dict, output_prefix: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    pooled_values = [result["metrics"][arm]["f1"] for arm in ("U", "P", "R")]
    pooled_labels = ["U\nno mask", "P\nP3 mask", "R\nrepeat mask"]
    colors = {"U": "#7F8B96", "P": "#178A83", "R": "#CC7744"}

    comparisons = (
        ("P−U", "P_minus_U", "#178A83"),
        ("R−U", "R_minus_U", "#CC7744"),
        ("P−R", "P_minus_R", "#5C6670"),
    )

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.65), gridspec_kw={"wspace": 0.38})
    ax = axes[0]
    bars = ax.bar(np.arange(3), pooled_values, color=[colors[a] for a in ("U", "P", "R")], width=0.62)
    for bar, value in zip(bars, pooled_values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.018,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=10,
            weight="bold",
        )
    ax.set_xticks(np.arange(3), pooled_labels)
    ax.set_ylim(0, 0.80)
    ax.set_ylabel("Pooled locus F1")
    ax.set_title("A  Pooled locus F1", loc="left", weight="bold", pad=12)
    ax.grid(axis="y", color="#E5E8EB", linewidth=0.7)
    ax.set_axisbelow(True)

    ax = axes[1]
    y_positions = np.arange(len(comparisons))[::-1]
    for y, (label, key, color) in zip(y_positions, comparisons):
        item = result["comparisons"][key]
        delta = float(item["locus_f1_delta"])
        low, high = map(float, item["bootstrap"]["ci95"])
        ax.errorbar(
            delta,
            y,
            xerr=np.asarray([[delta - low], [high - delta]]),
            fmt="o",
            color=color,
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=0.8,
            markersize=7,
            capsize=4,
            linewidth=2,
        )
        ax.text(
            min(high + 0.004, 0.112),
            y + 0.13,
            f"{delta:+.4f} [{low:+.4f}, {high:+.4f}]",
            ha="left",
            va="bottom",
            fontsize=8.4,
            color="#30363B",
        )
    ax.axvline(0, color="#30363B", linewidth=0.9, linestyle="--")
    ax.set_yticks(y_positions, [item[0] for item in comparisons])
    ax.set_xlim(-0.02, 0.12)
    ax.set_xticks([-0.02, 0.00, 0.04, 0.08, 0.12])
    ax.set_xlabel("Δ pooled locus F1")
    ax.set_title("B  Paired deltas", loc="left", weight="bold", pad=12)
    ax.grid(axis="x", color="#E5E8EB", linewidth=0.7)
    ax.set_axisbelow(True)
    ax = axes[2]
    turnover_bars = ax.bar(
        np.arange(2),
        [55, 16],
        color=["#178A83", "#B34D4D"],
        width=0.62,
    )
    for bar, value in zip(turnover_bars, (55, 16)):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.4,
            str(value),
            ha="center",
            va="bottom",
            fontsize=11,
            weight="bold",
        )
    ax.set_xticks(np.arange(2), ["Gained", "Lost"])
    ax.set_ylim(0, 67)
    ax.set_ylabel("Locus units")
    ax.set_title("C  P−U locus turnover", loc="left", weight="bold", pad=12)
    ax.grid(axis="y", color="#E5E8EB", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.text(
        0.5,
        0.92,
        "Lost U-correct loci\n16 / 510 = 3.14%\nallowed ≤ 1.00%  →  gate not met",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        color="#8E3333",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#FFF4F2", "edgecolor": "#E4B8B2"},
    )

    fig.suptitle(
        "Average input utility improves, but the four-gate criterion is not met",
        x=0.055,
        y=0.995,
        ha="left",
        va="top",
        fontsize=13,
        weight="bold",
    )
    fig.text(
        0.055,
        0.035,
        "Fixed hg38 chr16/18 panel · 726 reference locus units · 20 cores × 3 arms · 60 completed cells.\n"
        "P−U is prespecified: Δ = +0.0631, 95% CI [+0.0365, +0.1068]; P−R CI crosses 0.\n"
        "No equivalence or P-over-R superiority claim. Exploratory fixed-panel input utility, not independent generalization or no-risk evidence.",
        ha="left",
        va="bottom",
        fontsize=8.4,
        color="#414951",
    )
    fig.subplots_adjust(left=0.06, right=0.985, top=0.79, bottom=0.25)
    _save_figure(fig, output_prefix)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-prefix", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    output_prefix = (args.output_prefix or (root / DEFAULT_OUTPUT)).resolve()
    result, _ = load_and_validate(root)
    make_figure(result, output_prefix)
    print(output_prefix)


if __name__ == "__main__":
    main()
