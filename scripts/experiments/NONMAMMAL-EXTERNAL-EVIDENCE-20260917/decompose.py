#!/usr/bin/env python3
"""Exploratory decomposition of structural support outside the old RM layer.

Added after the first silkworm primary result. No threshold/model/region changes.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import panel


def mask_from_bed(path, regions, lengths, original):
    masks = {key: np.zeros(length, dtype=bool) for key, length in lengths.items()}
    by_sequence = {row["seqid"]: row for row in regions}
    for name, start, end in panel.bed_rows(path):
        if original:
            if name not in by_sequence:
                continue
            row = by_sequence[name]
            start, end = max(0, start - row["start"]), min(lengths[row["panel_id"]], end - row["start"])
            name = row["panel_id"]
        if end > start:
            masks[name][start:end] = True
    return masks


def run(args):
    result = json.loads((args.score / "result.json").read_text())
    sequences = dict(panel.fasta(args.panel / "panel.fa"))
    lengths = {key: len(value) for key, value in sequences.items()}
    regions = result["panel"]["regions"]
    old = mask_from_bed(args.score / "historical_rm_positive.bed", regions, lengths, True)
    structural = mask_from_bed(args.score / "structural_ltr_positive.bed", regions, lengths, True)
    prediction = mask_from_bed(Path(result["inference"]) / "material_runs.bed", regions, lengths, False)
    rows = []
    for key, sequence in sequences.items():
        callable_mask = np.isin(np.frombuffer(sequence.encode("ascii"), dtype="S1"), [b"A", b"C", b"G", b"T"])
        for category, mask in (("structural_inside_old_TE_layer", structural[key] & old[key]),
                               ("structural_outside_old_TE_layer", structural[key] & ~old[key])):
            eligible = mask & callable_mask
            rows.append({"panel_id": key, "category": category,
                         "positive_bp": int(eligible.sum()),
                         "recovered_bp": int((eligible & prediction[key]).sum())})
    totals = {}
    for category in sorted({row["category"] for row in rows}):
        selected = [row for row in rows if row["category"] == category]
        positive, recovered = (sum(row[name] for row in selected) for name in ("positive_bp", "recovered_bp"))
        totals[category] = {"positive_bp": positive, "recovered_bp": recovered,
                            "missed_bp": positive - recovered,
                            "positive_recovery": recovered / positive if positive else None}
    out = {"species": result["species"], "status": "EXPLORATORY_SOURCE_DECOMPOSITION",
           "declared_after_silkworm_primary": True, "totals": totals, "per_region": rows,
           "interpretation": "Outside-old-layer means absent from this historical known-TE annotation, not proven new TE or corrected model TP. Structural calls provide algorithmic support; retain model misses in both strata."}
    panel.dump(args.output, out)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--score", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args())
