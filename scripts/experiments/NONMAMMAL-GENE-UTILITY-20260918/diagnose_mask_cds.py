#!/usr/bin/env python3
"""Quantify existing mask overlap with the merged reference CDS union.

This is a post-hoc diagnostic for an already completed utility panel.  It
reads only the frozen geometry/reference JSON and existing arm FASTAs; it does
not rerun AUGUSTUS, change a mask, or alter the primary locus score.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
NAME = "NONMAMMAL-GENE-UTILITY-20260918"
BASE = ROOT / "outputs" / NAME
ARMS = ("U", "D", "R_TE", "RED")


def merge(intervals):
    merged = []
    for left, right in sorted(intervals):
        if right <= left:
            continue
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    return [(left, right) for left, right in merged]


def intersection_length(left_intervals, right_intervals):
    i = j = total = 0
    while i < len(left_intervals) and j < len(right_intervals):
        left = max(left_intervals[i][0], right_intervals[j][0])
        right = min(left_intervals[i][1], right_intervals[j][1])
        if right > left:
            total += right - left
        if left_intervals[i][1] <= right_intervals[j][1]:
            i += 1
        else:
            j += 1
    return total


def fasta_sequence(path: Path) -> str:
    return "".join(line.strip() for line in path.read_text().splitlines() if not line.startswith(">"))


def lowercase_runs(sequence: str):
    runs = []
    start = None
    # These are the alphabet symbols accepted by the fixed preparation.  The
    # explicit set preserves the original diagnostic's definition of masked
    # sequence and avoids treating FASTA headers or line endings as bases.
    lowercase_bases = set("acgtnryswkmbdhv")
    for index, base in enumerate(sequence):
        if base in lowercase_bases:
            if start is None:
                start = index
        elif start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(sequence)))
    return runs


def run(species: str, output: Path) -> dict:
    species_dir = BASE / species
    geometry = json.loads((species_dir / "geometry.json").read_text())
    reference = json.loads((species_dir / "reference.json").read_text())
    units = reference["units"]
    per_core = []
    for row in geometry:
        core_start, core_end = int(row["start"]), int(row["end"])
        owner = f"{row['chrom']}:{row['index']}"
        cds = []
        for unit in units:
            if unit["owner"] != owner:
                continue
            for isoform in unit["isoforms"]:
                for left, right in isoform["intervals"]:
                    left, right = int(left), int(right)
                    if right > core_start and left < core_end:
                        cds.append((max(left, core_start), min(right, core_end)))
        cds = merge(cds)
        cds_bp = sum(right - left for left, right in cds)
        arm_values = {}
        for arm in ARMS:
            sequence = fasta_sequence(species_dir / row["id"] / f"{arm}.fasta")
            expected_length = int(row["halo_end"]) - int(row["halo_start"])
            if len(sequence) != expected_length:
                raise ValueError(f"{species}/{row['id']}/{arm}: FASTA length mismatch")
            offset = int(row["halo_start"])
            masked = merge(
                (max(core_start, offset + left), min(core_end, offset + right))
                for left, right in lowercase_runs(sequence)
                if offset + right > core_start and offset + left < core_end
            )
            masked_bp = sum(right - left for left, right in masked)
            masked_cds_bp = intersection_length(masked, cds)
            arm_values[arm] = {
                "masked_core_bp": masked_bp,
                "masked_core_fraction": masked_bp / (core_end - core_start),
                "masked_cds_bp": masked_cds_bp,
                "masked_cds_fraction": masked_cds_bp / cds_bp if cds_bp else None,
            }
        per_core.append({
            "id": row["id"],
            "chrom": row["chrom"],
            "core_bp": core_end - core_start,
            "cds_union_bp": cds_bp,
            "cds_union_intervals": len(cds),
            "arms": arm_values,
        })

    core_bp = sum(row["core_bp"] for row in per_core)
    cds_bp = sum(row["cds_union_bp"] for row in per_core)
    summary = {
        "protocol": NAME,
        "species": species,
        "status": "COMPLETED_POSTHOC_MASK_CDS_DIAGNOSTIC",
        "core_count": len(per_core),
        "core_bp": core_bp,
        "cds_union_bp": cds_bp,
        "arms": {},
        "per_core": per_core,
    }
    for arm in ARMS:
        masked_core_bp = sum(row["arms"][arm]["masked_core_bp"] for row in per_core)
        masked_cds_bp = sum(row["arms"][arm]["masked_cds_bp"] for row in per_core)
        summary["arms"][arm] = {
            "masked_core_bp": masked_core_bp,
            "masked_core_fraction": masked_core_bp / core_bp,
            "masked_cds_bp": masked_cds_bp,
            "masked_cds_fraction": masked_cds_bp / cds_bp if cds_bp else None,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary["arms"], sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", choices=("chicken", "zebrafish"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.species, args.output)


if __name__ == "__main__":
    main()
