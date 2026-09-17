#!/usr/bin/env python3
"""Render the two completed external positive-evidence evaluations."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def run(args):
    labels = {"silkworm": "Silkworm", "d_simulans": "D. simulans"}
    layers = {"historical_repeatmasker": "Historical library\n(all known TE classes)",
              "structural_ltr": "Structural evidence\n(intact LTR candidates)"}
    records = {key: json.loads((args.reports / key / "result.json").read_text()) for key in labels}
    fig, axes = plt.subplots(1, 2, figsize=(8.7, 4.3), sharey=True)
    table = ["| Species | Positive layer | Positive bp | Recovered bp | Recovery |",
             "|---|---|---:|---:|---:|"]
    for ax, (species, result) in zip(axes, records.items()):
        tick_labels = []
        for x, (layer, label) in enumerate(layers.items()):
            measure = result["layers"][layer]
            primary = measure["primary"]
            value = primary["positive_recovery"]
            ax.bar(x, value, width=.58, color=("#4878A8", "#4F9678")[x], alpha=.85)
            for offset, region in zip((-.14, -.047, .047, .14), measure["per_region"]):
                if region["positive_recovery"] is not None:
                    ax.plot(x + offset, region["positive_recovery"], "o", ms=4,
                            color="#242424", markeredgecolor="white", markeredgewidth=.4)
            ax.text(x, value + .045, f"{value:.1%}", ha="center", va="bottom", fontsize=10)
            tick_labels.append(label + f"\n{primary['reference_positive_bp']:,} positive bp")
            table.append(f"| {labels[species]} | {'Historical library' if x == 0 else 'Structural LTR'} | "
                         f"{primary['reference_positive_bp']:,} | {primary['recovered_positive_bp']:,} | {value:.2%} |")
        ax.set_title(labels[species], fontstyle="italic" if species == "d_simulans" else "normal")
        ax.set_xticks([0, 1], tick_labels, fontsize=8)
        ax.set_ylim(0, 1.12)
        ax.set_yticks([0, .2, .4, .6, .8, 1])
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=.15)
    axes[0].set_ylabel("Callable positive-base recovery")
    fig.suptitle("Frozen six-species D on two external insect panels", fontsize=12)
    fig.text(.5, .015, "16.8 Mb/species; dots = four fixed regions; layers have different class/age selection.\n"
             "Positive-only evidence: these values are not biological precision or F1.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .12, 1, .95))
    for ext in ("png", "pdf", "svg"):
        destination = args.reports / f"external_positive_recovery.{ext}"
        fig.savefig(destination, dpi=180)
        if ext == "svg":
            destination.write_text("\n".join(line.rstrip() for line in destination.read_text().splitlines()) + "\n")
    plt.close(fig)
    text = """# Fixed D: external nonmammalian positive-evidence results

Both complete native inferences, structural extractions and primary scores
finished on the preselected 4 × 4,194,304-bp panels. The same frozen D seed42,
CAL artifact, threshold and forward-only 4096-bp tiling were used for both.
Neither species is in the D task-supervision table; pretraining exposure is
unknown. These two new species are insects, not additional independent
vertebrate examples.

""" + "\n".join(table) + "\n\n"
    text += "The structural layer uses native LTRharvest/LTR_FINDER and LTR_retriever pass lists; it is algorithmic support selected toward intact LTRs, not manually confirmed truth. The historical layer contains all eligible known TE classes. Their difference cannot be attributed solely to label quality because class, intactness and age differ.\n\n"
    text += "Unannotated sequence remains unknown. Recovery denominators exclude non-ACGT bases. The plots show all four regional values and pooled positive-base recovery; the dots are not seeds or confidence intervals. No precision/F1, all-species >=0.8 conclusion, or biological insertion reconstruction is claimed.\n\n"
    text += "For each species, `result.json` contains source paths, frozen regions, callable denominator, prediction coverage and native structural counts. Separate `source_decomposition.json` files, where present, are explicitly exploratory analyses added after the first silkworm primary result; they retain model misses both inside and outside the old annotation layer.\n"
    text += "\n## Exploratory support outside the old TE annotation\n\n"
    text += "| Species | Intact LTR candidates | Structural-positive bp outside old TE layer | Recovered bp | Missed bp | Recovery |\n|---|---:|---:|---:|---:|---:|\n"
    for species, result in records.items():
        decomposition = json.loads((args.reports / species / "source_decomposition.json").read_text())
        value = decomposition["totals"]["structural_outside_old_TE_layer"]
        text += f"| {labels[species]} | {result['structure']['insertion_candidates']} | {value['positive_bp']:,} | {value['recovered_bp']:,} | {value['missed_bp']:,} | {value['positive_recovery']:.2%} |\n"
    text += "\nThe silkworm result supplies a concrete candidate annotation-gap observation: D detects 109,380 bp carrying native structural support outside the historical known-TE layer, while missing another 27,754 bp there. This supports coexistence of reference coverage differences and model misses; it does not certify these bases as biological TP. The outside-old-layer denominator in D. simulans is only 1,754 bp and is not a broad gap claim. Neither layer contrast alone explains the zebrafish-versus-pig/chicken ordering.\n"
    (args.reports / "RESULTS.md").write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, required=True)
    run(parser.parse_args())
