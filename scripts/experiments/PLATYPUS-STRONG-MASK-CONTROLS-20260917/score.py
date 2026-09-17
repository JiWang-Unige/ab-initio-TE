#!/usr/bin/env python3
"""Score the two complete strong-mask receiver arms against frozen controls."""
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
MODES = ("RM2", "RED", "D", "U_soft", "U_nosm", "R_TE", "R_all", "P")


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def bootstrap(rows: list[dict], left: str, right: str) -> dict:
    chromosomes = sorted({row["chrom"] for row in rows})
    grouped = {chrom: {mode: Counter() for mode in (left, right)} for chrom in chromosomes}
    for row in rows:
        for mode in (left, right):
            grouped[row["chrom"]][mode].update({k: row["metrics"][mode][k] for k in ("tp", "fp", "fn")})
    rng = np.random.default_rng(42)
    values = []
    for _ in range(10000):
        counts = {mode: Counter() for mode in (left, right)}
        for idx in rng.integers(0, len(chromosomes), len(chromosomes)):
            for mode in counts:
                counts[mode].update(grouped[chromosomes[idx]][mode])
        a, b = metrics(**counts[left])["f1"], metrics(**counts[right])["f1"]
        if a is not None and b is not None:
            values.append(a - b)
    return {"unit": "chromosome; paired fixed cores", "clusters": len(chromosomes), "replicates": 10000,
            "valid_replicates": len(values), "seed": 42,
            "ci95": np.quantile(values, [0.025, 0.975]).tolist() if values else None}


def metrics(tp: int, fp: int, fn: int) -> dict:
    return {"tp": int(tp), "fp": int(fp), "fn": int(fn),
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main() -> None:
    if not OLD.exists():
        raise ValueError("completed D/control result is missing")
    old = json.loads(OLD.read_text())
    if old.get("status") != "COMPLETED" or old.get("reference_loci") != 639:
        raise ValueError("frozen D/control result is not qualified")
    geometry = json.loads((PREP / "geometry.json").read_text())
    if len(geometry) != 20:
        raise ValueError("fixed geometry changed")
    reference = json.loads((PREP / "reference.json").read_text())
    units = {unit["unit_id"]: unit for unit in reference["units"]}
    mapping = {}
    for uid, unit in units.items():
        for iso in unit["isoforms"]:
            key = (unit["chrom"], unit["strand"], tuple(tuple(x) for x in iso["intervals"]))
            if key in mapping and mapping[key] != uid:
                raise ValueError("ambiguous reference chain")
            mapping[key] = uid
    base = module(ROOT / "scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py", "strong_score_base")
    totals = {mode: Counter() for mode in MODES}
    correct = {mode: set() for mode in MODES}
    rows = []
    old_rows = {row["id"]: row for row in old["per_core"]}
    for core in geometry:
        if core["id"] not in old_rows:
            raise ValueError(f"frozen control lacks core {core['id']}")
        row = {"id": core["id"], "chrom": core["chrom"], "reference_loci": old_rows[core["id"]]["reference_loci"], "metrics": {}}
        for mode in ("D", "U_soft", "U_nosm", "R_TE", "R_all", "P"):
            value = old_rows[core["id"]]["metrics"][mode]
            row["metrics"][mode] = value
            totals[mode].update({key: value[key] for key in ("tp", "fp", "fn")})
        rows.append(row)
    for method in ("RM2", "RED"):
        method_root = BASE / "tiberius-r2" / method
        for core in geometry:
            cell = method_root / core["id"]
            status_path = cell / "status.json"
            if not status_path.exists() or json.loads(status_path.read_text()).get("status") != "COMPLETED":
                raise ValueError(f"all 20 {method} receiver cells must complete before score: {cell}")
            b = base.Core(**{key: core[key] for key in ("chrom", "index", "start", "end", "halo_start", "halo_end")})
            gtf, a_counts = base.parse_predictions(cell / f"{method}.gtf", b, "gtf")
            gff, b_counts = base.parse_predictions(cell / f"{method}.gff3", b, "gff3")
            if gtf != gff or a_counts != b_counts:
                raise ValueError(f"GTF/GFF3 mismatch {method}/{core['id']}")
            truth = {uid for uid, unit in units.items() if unit["core_id"] == core["id"]}
            matched = {chain for chain in gtf if (core["chrom"], chain.strand, chain.intervals) in mapping}
            found = {mapping[(core["chrom"], chain.strand, chain.intervals)] for chain in matched}
            if not found <= truth:
                raise ValueError(f"reference locus assigned to wrong core {method}/{core['id']}")
            value = metrics(len(found), len(gtf - matched), len(truth - found))
            totals[method].update({key: value[key] for key in ("tp", "fp", "fn")})
            correct[method].update(found)
            row = next(item for item in rows if item["id"] == core["id"])
            row["metrics"][method] = value
    # The old result is the qualified control record; these assignments make the
    # exact reusable correct-locus sets explicit without rescoring old cells.
    for mode in ("D", "U_soft", "U_nosm", "R_TE", "R_all", "P"):
        correct[mode] = set(old["correct_loci"][mode])
        expected = old["metrics"][mode]
        got = metrics(**totals[mode])
        if any(got[k] != expected[k] for k in ("tp", "fp", "fn")):
            raise ValueError(f"reused control counts differ for {mode}")
    summary = {mode: metrics(**totals[mode]) for mode in MODES}
    comparisons = {}
    for method in ("RM2", "RED"):
        for control in ("D", "U_nosm", "U_soft", "R_TE", "R_all", "P"):
            gained = sorted(correct[method] - correct[control])
            lost = sorted(correct[control] - correct[method])
            fraction = len(lost) / len(correct[control]) if correct[control] else None
            comparisons[f"{method}_minus_{control}"] = {
                "f1_delta": summary[method]["f1"] - summary[control]["f1"],
                "precision_delta": (summary[method]["precision"] - summary[control]["precision"]
                                    if summary[method]["precision"] is not None and summary[control]["precision"] is not None else None),
                "recall_delta": summary[method]["recall"] - summary[control]["recall"],
                "gained_loci": gained, "lost_loci": lost,
                "lost_correct_fraction": fraction,
                "bootstrap": bootstrap(rows, method, control)}
    masks = {}
    for method in ("RM2", "RED"):
        manifests = [json.loads((BASE / "mask" / method / core["id"] / "manifest.json").read_text()) for core in geometry]
        masks[method] = {
            "completed_cells": len(manifests),
            "panel_input_bp": sum(m["panel_input_bp"] for m in manifests),
            "gene_score_core_denominator_bp": 100000000,
            "masked_acgt_bp": sum(m["masked_acgt_bp"] for m in manifests),
            "lowercase_bp": sum(m["lowercase_bp"] for m in manifests),
            "per_core": [{"core": m["core"]["id"], "masked_acgt_bp": m["masked_acgt_bp"],
                          "repeatmasker_summary": m.get("repeatmasker_summary")} for m in manifests]}
    result = {"protocol": "PLATYPUS-STRONG-MASK-CONTROLS-20260917", "status": "COMPLETED",
              "species": "platypus", "scope": "fixed 20-core mask comparison through the identical Tiberius receiver; comparator-relative, not independent biological truth",
              "new_mask_cells": 40, "reused_control_cells": 120, "reference_loci": len(units),
              "coverage_denominator": {"mask_panel_bp": 104000000, "gene_score_core_bp": 100000000,
                                       "per_core_panel_bp": 5200000, "halo_bp_per_core": 100000},
              "metrics": summary, "masks": masks, "comparisons": comparisons,
              "controls_reused_from": "outputs/D-TIBERIUS-PLATYPUS-20260917/run/result.json",
              "per_core": rows, "correct_loci": {mode: sorted(values) for mode, values in correct.items()},
              "native_library_policy": "RM2 complete consensi.fa.classified including Unknown; no downstream filtering",
              "red_semantics": "all-repeat mask without family classification"}
    out = BASE / "score" / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, result)
    print(json.dumps({"status": "COMPLETED", "metrics": summary,
                      "deltas": {key: value["f1_delta"] for key, value in comparisons.items()}}, indent=2))


if __name__ == "__main__":
    main()
