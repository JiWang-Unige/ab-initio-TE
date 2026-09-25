#!/usr/bin/env python3
"""Collect native completion metadata or validate the compact two-species export.

`native SPECIES` runs beside Baobab outputs and only reads small JSON/GFF stats.
`validate` runs locally after collection; it does not rerun prediction/scoring.
It also repairs a descriptive source-stratum summary using retained selections,
preserving the old compact summary and leaving native masks/results untouched.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NAME = "FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925"
REPORT = ROOT / "reports" / NAME
NEW = ("RM2_FULL", "D_COMMON_RANDOM", "RM2_COMMON_RANDOM", "RM2_COMMON_CONF")


def read(path):
    return json.loads(path.read_text())


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def native(species):
    out = ROOT / "outputs" / NAME / species
    result = read(out / "result.json")
    cells = []
    for row in result["per_core"]:
        cell = out / row["id"]
        status = read(cell / "status.json")
        assert status["status"] == "COMPLETED"
        evidence = {"core": row["id"], "status": status["status"],
                    "job_id": status["job_id"], "arms": {}}
        for arm in NEW:
            command = read(cell / (arm + ".command.json"))
            size = (cell / (arm + ".gff3")).stat().st_size
            assert command["exit_code"] == 0 and size > 0
            evidence["arms"][arm] = {"native_command": command, "gff_bytes": size,
                                      "predicted_chains": status["arms"][arm]["predicted_chains"]}
        cells.append(evidence)
    write(REPORT / species / "native-terminal.json", {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NATIVE_OUTPUTS_VERIFIED", "cells": cells})


def validate():
    summary_path = REPORT / "prepare-summary.json"
    original = REPORT / "prepare-summary-pre-source-field-fix.json"
    if not original.exists():
        original.write_text(summary_path.read_text())
    compact = read(original)
    repaired = []
    for species in ("chicken", "zebrafish"):
        result = read(REPORT / species / "result.json")
        old = read(ROOT / "reports/NONMAMMAL-GENE-UTILITY-20260918" / species / "result.json")
        native_data = read(REPORT / species / "native-terminal.json")
        assert result["status"] == "COMPLETED" and len(result["per_core"]) == 10
        assert result["metrics"]["U"] == old["metrics"]["U"]
        assert result["metrics"]["D_FIXED"] == old["metrics"]["D"]
        assert len(native_data["cells"]) == 10
        assert {r["core"] for r in native_data["cells"]} == {r["id"] for r in result["per_core"]}
        assert sum(r["reference_loci"] for r in result["per_core"]) == result["reference_loci"]
        for cell in native_data["cells"]:
            assert cell["status"] == "COMPLETED" and set(cell["arms"]) == set(NEW)
            for arm in cell["arms"].values():
                assert arm["native_command"]["exit_code"] == 0 and arm["gff_bytes"] > 0
        for arm, metric in result["metrics"].items():
            for key in ("tp", "fp", "fn"):
                assert sum(r["metrics"][arm][key] for r in result["per_core"]) == metric[key]
            assert metric["tp"] + metric["fn"] == result["reference_loci"]
            for m in [metric] + [r["metrics"][arm] for r in result["per_core"]]:
                expected = 2 * m["tp"] / (2 * m["tp"] + m["fp"] + m["fn"])
                assert math.isclose(m["f1"], expected, abs_tol=1e-12)
        for name, comparison in result["comparisons"].items():
            left, right = name.split("_minus_")
            a, b = result["metrics"][left], result["metrics"][right]
            assert math.isclose(comparison["f1_delta"], a["f1"] - b["f1"], abs_tol=1e-12)
            gained, lost = set(comparison["gained_loci"]), set(comparison["lost_loci"])
            assert not gained & lost
            assert len(gained) - len(lost) == a["tp"] - b["tp"]
        manifest = read(REPORT / (species + "-manifest.json"))
        by_id = {r["id"]: r for r in compact["species"][species]["cores"]}
        for cell in manifest["cores"]:
            for arm, records in cell["selection_records"].items():
                bp, counts = Counter(), Counter()
                for selection in records:
                    assert selection["length"] == selection["selected"][1] - selection["selected"][0]
                    bp[selection["stratum"]] += selection["length"]
                    counts[selection["stratum"]] += 1
                expected_bp = [bp[i] for i in range(8)]
                assert expected_bp == cell["common_budget_by_stratum_bp"]
                stats = by_id[cell["id"]]["mask_summaries"][arm]
                assert sum(expected_bp) == stats["bp"] == cell["common_budget_bp"]
                stats["source_length_strata_bp"] = expected_bp
                stats["source_length_strata_runs"] = [counts[i] for i in range(8)]
                repaired.append({"species": species, "core": cell["id"], "arm": arm,
                                 "source_quota_verified_bp": expected_bp})
        write(REPORT / species / "validation.json", {
            "status": "PASS", "reference_loci": result["reference_loci"],
            "cores": 10, "arms": 6, "new_native_arms": 4,
            "U_and_D_exactly_unchanged": True, "per_core_counts_sum_to_total": True,
            "TP_plus_FN_equals_reference_loci": True, "F1_recomputed_from_counts": True,
            "pair_deltas_and_gain_loss_counts_consistent": True,
            "source_stratum_quotas_verified_from_selection_records": True,
            "boundary": "Development-panel reference consistency; bootstrap is regional sensitivity, not independent confirmation."})
    compact["descriptive_field_correction"] = (
        "source_length_strata fields originally duplicated actual post-truncation strata. "
        "Corrected from retained selection records, whose assigned bp equal each frozen quota. "
        "Original compact/native manifests are retained; masks, GFFs and scores are unchanged.")
    write(summary_path, compact)
    write(REPORT / "source-stratum-audit.json", {"status": "PASS", "rows": repaired,
          "scope": "Descriptive summary correction only; all 60 selection-source budgets match frozen quotas."})
    print("Both species: native outputs, counts, old U/D and 60 source-budget records verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("native", "validate"))
    parser.add_argument("species", nargs="?", choices=("chicken", "zebrafish"))
    args = parser.parse_args()
    if args.action == "native":
        if args.species is None:
            parser.error("native requires species")
        native(args.species)
    else:
        validate()
