#!/usr/bin/env python3
"""Compare the already-materialized confidence arm with the corrected rule.

This is a read-only audit of prepared FASTAs.  It never rewrites a mask or
reads the gene reference.  The old rule is the rule used by the first
preparation attempt (raw SW score after divergence); the corrected rule uses
SW/aligned-length as frozen in the protocol.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[3]
NAME = "FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925"
OUT = ROOT / "outputs" / NAME
REPORT = ROOT / "reports" / NAME


def load_module():
    path = ROOT / "scripts/experiments" / NAME / "pilot.py"
    spec = importlib.util.spec_from_file_location("functional_mask_pilot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def old_quality_key(row):
    quality = row["quality"] or {}
    return (
        0 if row["quality"] is not None else 1,
        quality.get("divergence", float("inf")),
        -quality.get("sw_score", -1),
        -quality.get("alignment_length", -1),
        quality.get("query_begin", 10**18),
        quality.get("query_end", 10**18),
        quality.get("native_id", 10**18),
        row["interval"][0],
        row["interval"][1],
    )


def sequence(path: Path):
    return "".join(line.strip() for line in path.open() if not line.startswith(">"))


def overlap_bp(left_runs, right_runs):
    i = j = total = 0
    while i < len(left_runs) and j < len(right_runs):
        left = max(left_runs[i][0], right_runs[j][0])
        right = min(left_runs[i][1], right_runs[j][1])
        if right > left:
            total += right - left
        if left_runs[i][1] <= right_runs[j][1]:
            i += 1
        else:
            j += 1
    return total


def run(species: str):
    pilot = load_module()
    species_dir = OUT / species
    manifest = json.loads((species_dir / "manifest.json").read_text())
    rm2_path = ROOT / pilot.CFG["inputs"]["rm2_annotation_out"].replace("{species}", species)
    geometry = {row["id"]: row for row in manifest["cores"]}
    records = pilot.parse_rm2_out(rm2_path, {row["chrom"] for row in manifest["cores"]})
    comparisons = []
    for core_id, row in geometry.items():
        rm2 = pilot.lowercase_runs(sequence(species_dir / core_id / "RM2_FULL.fasta"))
        quality = pilot.attach_native_quality(rm2, records[row["chrom"]], row["halo"][0])
        grouped = pilot.runs_by_bin(rm2)
        lookup = {(item["interval"][0], item["interval"][1]): item for item in quality}
        quality_grouped = [[lookup[(left, right)] for left, right in group] for group in grouped]
        quotas = row["common_budget_by_stratum_bp"]
        old_selected, _ = pilot.select_exact(quality_grouped, quotas, old_quality_key)
        new_selected, _ = pilot.select_exact(quality_grouped, quotas, pilot.quality_key)
        actual_selected = pilot.lowercase_runs(sequence(species_dir / core_id / "RM2_COMMON_CONF.fasta"))
        comparisons.append({
            "core": core_id,
            "old_reconstruction_matches_materialized": old_selected == actual_selected,
            "new_reconstruction_matches_materialized": new_selected == actual_selected,
            "old_run_count": len(old_selected),
            "new_run_count": len(new_selected),
            "changed": old_selected != new_selected,
            "old_bp": sum(right-left for left, right in old_selected),
            "new_bp": sum(right-left for left, right in new_selected),
            "changed_bp_symmetric_difference": (
                sum(right-left for left, right in old_selected)
                + sum(right-left for left, right in new_selected)
                - 2 * overlap_bp(old_selected, new_selected)
            ),
        })
    result = {
        "protocol": NAME,
        "status": "COMPLETED_READ_ONLY_CONFIDENCE_RULE_AUDIT",
        "species": species,
        "old_rule": "divergence ascending, raw SW score descending, alignment length descending, coordinates/ID",
        "new_rule": "divergence ascending, SW/aligned_length descending, alignment length descending, coordinates/ID",
        "materialized_old_rule_verified": all(row["old_reconstruction_matches_materialized"] for row in comparisons),
        "materialized_new_rule_verified": all(row["new_reconstruction_matches_materialized"] for row in comparisons),
        "changed_core_count": sum(row["changed"] for row in comparisons),
        "cores": comparisons,
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / f"conf-rule-comparison-v2-{species}.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("species", choices=("chicken", "zebrafish"))
    run(parser.parse_args().species)
