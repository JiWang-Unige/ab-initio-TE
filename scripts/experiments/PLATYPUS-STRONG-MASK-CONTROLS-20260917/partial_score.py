#!/usr/bin/env python3
"""Score the completed RED arm while the independent RM2 arm is pending.

This is deliberately a separate artifact.  It reuses the frozen D/U/R/P
control metrics and the same GTF/GFF3 receiver parser as the final scorer, but
never writes or labels the eventual two-arm final result.
"""
from __future__ import annotations

from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT / "outputs/P3-TIBERIUS-EXTERNAL-20260915/prepared/platypus"
BASE = ROOT / "outputs/PLATYPUS-STRONG-MASK-CONTROLS-20260917"
OLD = ROOT / "outputs/D-TIBERIUS-PLATYPUS-20260917/run/result.json"
MODES = ("RED", "D", "U_soft", "U_nosm", "R_TE", "R_all", "P")


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import %s" % path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def metrics(tp: int, fp: int, fn: int) -> dict:
    return {"tp": int(tp), "fp": int(fp), "fn": int(fn),
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def bootstrap(rows: list, left: str, right: str) -> dict:
    chromosomes = sorted({row["chrom"] for row in rows})
    grouped = {chrom: {left: Counter(), right: Counter()} for chrom in chromosomes}
    for row in rows:
        for mode in (left, right):
            grouped[row["chrom"]][mode].update({k: row["metrics"][mode][k] for k in ("tp", "fp", "fn")})
    rng = np.random.default_rng(42)
    values = []
    for _ in range(10000):
        counts = {left: Counter(), right: Counter()}
        for idx in rng.integers(0, len(chromosomes), len(chromosomes)):
            for mode in counts:
                counts[mode].update(grouped[chromosomes[idx]][mode])
        values.append(metrics(**counts[left])["f1"] - metrics(**counts[right])["f1"])
    return {"unit": "chromosome; paired fixed cores", "clusters": len(chromosomes), "replicates": 10000,
            "seed": 42, "ci95": np.quantile(values, [0.025, 0.975]).tolist()}


def main() -> None:
    if not OLD.exists():
        raise FileNotFoundError("qualified frozen D/control result is missing")
    old = json.loads(OLD.read_text())
    if old.get("status") != "COMPLETED" or old.get("reference_loci") != 639:
        raise ValueError("frozen D/control result is not qualified")
    geometry = json.loads((PREP / "geometry.json").read_text())
    reference = json.loads((PREP / "reference.json").read_text())
    units = {unit["unit_id"]: unit for unit in reference["units"]}
    mapping = {}
    for uid, unit in units.items():
        for iso in unit["isoforms"]:
            key = (unit["chrom"], unit["strand"], tuple(tuple(x) for x in iso["intervals"]))
            if key in mapping and mapping[key] != uid:
                raise ValueError("ambiguous reference chain")
            mapping[key] = uid
    base = module(ROOT / "scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py", "strong_partial_base")
    totals = {mode: Counter() for mode in MODES}
    correct = {mode: set(old["correct_loci"][mode]) for mode in ("D", "U_soft", "U_nosm", "R_TE", "R_all", "P")}
    rows = []
    old_rows = {row["id"]: row for row in old["per_core"]}
    for core in geometry:
        row = {"id": core["id"], "chrom": core["chrom"], "reference_loci": old_rows[core["id"]]["reference_loci"], "metrics": {}}
        for mode in ("D", "U_soft", "U_nosm", "R_TE", "R_all", "P"):
            value = old_rows[core["id"]]["metrics"][mode]
            row["metrics"][mode] = value
            totals[mode].update({key: value[key] for key in ("tp", "fp", "fn")})
        rows.append(row)
    for core in geometry:
        cell = BASE / "tiberius-r2" / "RED" / core["id"]
        status_path = cell / "status.json"
        if not status_path.exists() or json.loads(status_path.read_text()).get("status") != "COMPLETED":
            raise ValueError("RED receiver is not complete: %s" % cell)
        b = base.Core(**{key: core[key] for key in ("chrom", "index", "start", "end", "halo_start", "halo_end")})
        gtf, gtf_counts = base.parse_predictions(cell / "RED.gtf", b, "gtf")
        gff, gff_counts = base.parse_predictions(cell / "RED.gff3", b, "gff3")
        if gtf != gff or gtf_counts != gff_counts:
            raise ValueError("GTF/GFF3 mismatch for RED/%s" % core["id"])
        truth = {uid for uid, unit in units.items() if unit["core_id"] == core["id"]}
        matched = {chain for chain in gtf if (core["chrom"], chain.strand, chain.intervals) in mapping}
        found = {mapping[(core["chrom"], chain.strand, chain.intervals)] for chain in matched}
        if not found <= truth:
            raise ValueError("RED reference assigned to wrong core %s" % core["id"])
        value = metrics(len(found), len(gtf - matched), len(truth - found))
        next(row for row in rows if row["id"] == core["id"])["metrics"]["RED"] = value
        totals["RED"].update({key: value[key] for key in ("tp", "fp", "fn")})
        correct.setdefault("RED", set()).update(found)
    # Verify controls are exactly the frozen record before using their totals.
    for mode in ("D", "U_soft", "U_nosm", "R_TE", "R_all", "P"):
        if metrics(**totals[mode]) != old["metrics"][mode]:
            raise ValueError("reused control counts differ for %s" % mode)
    summary = {mode: metrics(**totals[mode]) for mode in MODES}
    comparisons = {}
    for control in ("D", "U_nosm", "U_soft", "R_TE", "R_all", "P"):
        gained = sorted(correct["RED"] - correct[control])
        lost = sorted(correct[control] - correct["RED"])
        comparisons["RED_minus_" + control] = {
            "f1_delta": summary["RED"]["f1"] - summary[control]["f1"],
            "precision_delta": summary["RED"]["precision"] - summary[control]["precision"],
            "recall_delta": summary["RED"]["recall"] - summary[control]["recall"],
            "gained_loci": gained, "lost_loci": lost,
            "lost_correct_fraction": len(lost) / len(correct[control]) if correct[control] else None,
            "bootstrap": bootstrap(rows, "RED", control),
        }
    result = {
        "protocol": "PLATYPUS-STRONG-MASK-CONTROLS-20260917",
        "status": "PARTIAL_RED_ONLY_RM2_PENDING",
        "scientific_final": False,
        "species": "platypus",
        "scope": "completed RED all-repeat mask through the frozen Tiberius receiver; RM2 arm intentionally absent",
        "new_mask_cells": 20, "reused_control_cells": 120, "reference_loci": len(units),
        "coverage_denominator": {"mask_panel_bp": 104000000, "gene_score_core_bp": 100000000,
                                 "per_core_panel_bp": 5200000, "halo_bp_per_core": 100000},
        "metrics": summary, "comparisons": comparisons, "per_core": rows,
        "correct_loci": {mode: sorted(values) for mode, values in correct.items()},
        "controls_reused_from": "outputs/D-TIBERIUS-PLATYPUS-20260917/run/result.json",
        "rm2_status": json.loads((BASE / "mask" / "RM2" / "status.json").read_text()) if (BASE / "mask" / "RM2" / "status.json").exists() else {"status": "PENDING_OR_MISSING"},
        "red_semantics": "all-repeat mask without family classification",
        "final_score_rule": "Do not use this artifact as the two-arm final score; run score.py only after all RM2 receiver cells are terminal-success",
    }
    out = BASE / "score" / "partial-red-20260918" / "result.json"
    if out.exists():
        raise FileExistsError("partial result already exists: %s" % out)
    out.parent.mkdir(parents=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "metrics": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
