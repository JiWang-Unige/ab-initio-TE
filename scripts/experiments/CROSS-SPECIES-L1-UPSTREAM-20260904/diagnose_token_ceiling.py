#!/usr/bin/env python3
"""Label-only ceiling for a binary output constant within each native token."""

import argparse
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903"))
import calibrate_evaluate_x0 as ev


def token_masses(labels):
    full = len(labels) // 6 * 6
    chunks = [labels[i:i + 6] for i in range(0, full, 6)]
    chunks.extend(labels[full:])
    return [(c.count("1"), c.count("0") + c.count("H"), len(c)) for c in chunks]


def optimal_f1(masses):
    """Exact maximum: rank token groups by positive/callable density."""
    groups = Counter()
    for positive, negative, _ in masses:
        if positive + negative:
            groups[(positive, negative)] += 1
    by_density = {}
    for (positive, negative), count in groups.items():
        density = Fraction(positive, positive + negative)
        p, n = by_density.get(density, (0, 0))
        by_density[density] = (p + positive * count, n + negative * count)
    total_positive = sum(p for p, _ in by_density.values())
    tp = fp = 0
    best_f1, best_density = 0.0, 1.0
    for density in sorted(by_density, reverse=True):
        p, n = by_density[density]
        tp += p
        fp += n
        f1 = ev._f1(tp, fp, total_positive - tp)
        if f1 > best_f1:
            best_f1, best_density = f1, float(density)
    return best_f1, best_density


def diagnose(path, species):
    records = ev.read_jsonl(path)
    per_record = [token_masses(r["labels"]) for r in records]
    masses = [mass for row in per_record for mass in row]
    maximum, density = optimal_f1(masses)
    scores = [np.concatenate([
        np.full(width, p / (p + n) if p + n else 0.0, dtype=np.float64)
        for p, n, width in row
    ]) for row in per_record]
    tiles = ev.assemble_tiles(species, records, scores)
    # sigmoid is monotone; use exactly the same transformation on the cutoff.
    metrics = ev.evaluate_species_tiles(tiles, 1.0, 0.0, float(ev.sigmoid(np.array(density))))
    if abs(metrics["bp_f1"] - maximum) > 1e-12:
        raise ValueError("projected oracle does not attain the computed token ceiling")
    return {
        "source": str(path), "species": species,
        "splits": sorted({r["split"] for r in records}),
        "maximum_token_constant_bp_f1": maximum,
        "oracle_density_threshold": density,
        "mixed_token_count": sum(p > 0 and n > 0 for p, n, _ in masses),
        "mixed_token_callable_bp": sum(p + n for p, n, _ in masses if p and n),
        "metrics_at_bp_optimal_oracle": metrics,
        "qualification": "label oracle, not deployable; topology is not independently maximized",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = {}
    for species in ev.CAL_SPECIES:
        splits = ("TRAIN", "CAL", "DEV") if species == "c_elegans" else ("DEV",)
        for split in splits:
            results[f"{species}/{split}"] = diagnose(args.data_root / split / f"{species}.jsonl.gz", species)
    ev.write_json(args.output, {"role": "retrospective_diagnostic", "results": results})


if __name__ == "__main__":
    main()
