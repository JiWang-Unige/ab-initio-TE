#!/usr/bin/env python3
"""Independent replay of the fixed P3/Tiberius score and gate contract."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

REVISIONS = ("r1", "r2")
MODES = ("U", "P", "R")
CORE_COUNT = 20


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    tmp.rename(path)


def run_root(root: Path, cfg: dict, run: str, revision: str) -> Path:
    if run != "full":
        raise ValueError("independent scientific replay requires the full run")
    if revision not in REVISIONS:
        raise ValueError(f"unknown output revision: {revision}")
    return root / cfg["output_base"] / f"{run}-{revision}"


def read_geometry(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != CORE_COUNT:
        raise ValueError(f"expected {CORE_COUNT} geometry rows, got {len(rows)}")
    result = []
    seen = set()
    for row in rows:
        required = {"core_id", "chrom", "index", "core_start", "core_end", "halo_start", "halo_end"}
        if set(row) != required:
            raise ValueError("unexpected geometry schema")
        core = {
            "key": row["core_id"],
            "chrom": row["chrom"],
            "index": int(row["index"]),
            "start": int(row["core_start"]),
            "end": int(row["core_end"]),
            "halo_start": int(row["halo_start"]),
            "halo_end": int(row["halo_end"]),
        }
        if core["key"] in seen or core["key"] != f'{core["chrom"]}:{core["index"]}':
            raise ValueError("geometry core ids are not unique/canonical")
        if not (0 <= core["start"] < core["end"] <= core["halo_end"] and
                0 <= core["halo_start"] <= core["start"]):
            raise ValueError("invalid geometry interval")
        seen.add(core["key"])
        result.append(core)
    return result


def normalize(intervals) -> tuple[tuple[int, int], ...]:
    result = []
    for start, end in sorted(set(intervals)):
        if start < 0 or end <= start:
            raise ValueError("invalid CDS interval")
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    if not result:
        raise ValueError("empty CDS chain")
    return tuple(result)


def reference_mapping(contract: dict) -> tuple[dict, dict]:
    units = {}
    mapping = {}
    for unit in contract.get("units", []):
        unit_id = unit["unit_id"]
        if unit_id in units:
            raise ValueError("duplicate reference unit id")
        units[unit_id] = unit
        for isoform in unit["isoforms"]:
            key = (unit["chrom"], unit["strand"],
                   tuple(tuple(interval) for interval in isoform["intervals"]))
            if key in mapping and mapping[key] != unit_id:
                raise ValueError("ambiguous reference CDS chain")
            mapping[key] = unit_id
    return units, mapping


def parse_attributes(attrs: str, fmt: str) -> list[str]:
    if fmt == "gtf":
        tid = dict(re.findall(r'(\w+)\s+"([^"]*)"', attrs)).get("transcript_id")
        ids = [tid]
    elif fmt == "gff3":
        fields = dict(x.split("=", 1) for x in attrs.split(";") if "=" in x)
        ids = fields.get("Parent", "").split(",")
    else:
        raise ValueError(f"unknown annotation format: {fmt}")
    if not all(ids):
        raise ValueError("missing prediction transcript id")
    return ids


def parse_native(path: Path, core: dict, record_id: str, fmt: str) -> tuple[set, Counter]:
    transcripts = {}
    halo_length = core["halo_end"] - core["halo_start"]
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"{path}:{line_no}: expected 9 fields")
            record, _, feature, start, end, _, strand, phase, attrs = fields
            if feature != "CDS":
                continue
            if record != record_id or strand not in ("+", "-") or phase not in (".", "0", "1", "2"):
                raise ValueError(f"{path}:{line_no}: invalid native CDS row")
            left, right = int(start) - 1, int(end)
            if not 0 <= left < right <= halo_length:
                raise ValueError(f"{path}:{line_no}: CDS outside input halo")
            for tid in parse_attributes(attrs, fmt):
                entry = transcripts.setdefault(tid, {"strand": strand, "intervals": []})
                if entry["strand"] != strand:
                    raise ValueError(f"{path}:{line_no}: inconsistent transcript strand")
                entry["intervals"].append((left + core["halo_start"], right + core["halo_start"]))
    chains = set()
    content = Counter()
    for value in transcripts.values():
        chain = (value["strand"], normalize(value["intervals"]))
        if not (core["start"] <= chain[1][0][0] < core["end"] and chain[1][-1][1] <= core["halo_end"]):
            continue
        chains.add(chain)
        content[chain] += 1
    return chains, content


def metrics(tp: int, fp: int, fn: int) -> dict:
    return {
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
    }


def observe_model(cell: Path, mode: str) -> dict:
    observation = load_json(cell / f"{mode}.observation.json")
    if observation.get("calls", 0) < 1 or not observation.get("passed"):
        raise ValueError(f"missing model observation: {cell}/{mode}")
    masked = observation.get("masked_positions")
    if mode == "U" and masked != 0:
        raise ValueError("U observation has a nonzero mask")
    if mode != "U" and (not isinstance(masked, int) or masked <= 0):
        raise ValueError(f"{mode} observation has no mask")
    return observation


def replay_cells(root: Path, cfg: dict, run: str, revision: str) -> tuple[list[dict], dict, dict]:
    out = run_root(root, cfg, run, revision)
    geometry = read_geometry(out / "geometry.tsv")
    contract = load_json(out / "reference_contract.json")
    units, mapping = reference_mapping(contract)
    per_core = []
    correct = {mode: set() for mode in MODES}
    unmatched = {mode: set() for mode in MODES}
    for core in geometry:
        cell = out / f'core-{core["chrom"]}-{core["index"]}'
        manifest = load_json(cell / "input_manifest.json")
        record_id = manifest["record_id"]
        truth = {unit_id for unit_id, unit in units.items() if unit["owner"] == core["key"]}
        row = {"core": core["key"], "metrics": {}, "correct": {}, "unmatched": {}}
        for mode in MODES:
            observe_model(cell, mode)
            gtf_chains, gtf_content = parse_native(cell / f"{mode}.gtf", core, record_id, "gtf")
            gff_chains, gff_content = parse_native(cell / f"{mode}.gff3", core, record_id, "gff3")
            if gtf_chains != gff_chains or gtf_content != gff_content:
                raise ValueError(f"GTF/GFF3 mismatch for {core['key']}/{mode}")
            chains = gtf_chains
            hits = {mapping[(core["chrom"], strand, intervals)] for strand, intervals in chains
                    if (core["chrom"], strand, intervals) in mapping}
            misses = {(strand, intervals) for strand, intervals in chains
                      if (core["chrom"], strand, intervals) not in mapping}
            row["metrics"][mode] = metrics(len(hits), len(misses), len(truth - hits))
            row["correct"][mode] = {(core["key"], unit_id) for unit_id in hits}
            row["unmatched"][mode] = {(core["key"], strand, intervals) for strand, intervals in misses}
            correct[mode].update(row["correct"][mode])
            unmatched[mode].update(row["unmatched"][mode])
        per_core.append(row)
    if len(per_core) != CORE_COUNT:
        raise ValueError("did not replay exactly twenty cores")
    return per_core, correct, unmatched


def aggregate(per_core: list[dict], mode: str) -> dict:
    counts = Counter()
    for row in per_core:
        counts.update({key: row["metrics"][mode][key] for key in ("tp", "fp", "fn")})
    return metrics(counts["tp"], counts["fp"], counts["fn"])


def bootstrap(per_core: list[dict], left: str, right: str, cfg: dict) -> dict:
    score = cfg["score"]
    rng = np.random.default_rng(score["bootstrap_seed"])
    n, reps = len(per_core), score["bootstrap_replicates"]
    diffs = np.empty(reps)
    for index in range(reps):
        sample = rng.integers(0, n, size=n)
        left_counts = Counter()
        right_counts = Counter()
        for selected in sample:
            for mode, counts in ((left, left_counts), (right, right_counts)):
                counts.update({key: per_core[selected]["metrics"][mode][key] for key in ("tp", "fp", "fn")})
        diffs[index] = metrics(**left_counts)["f1"] - metrics(**right_counts)["f1"]
    return {
        "resamples": reps,
        "seed": score["bootstrap_seed"],
        "ci95": [float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))],
    }


def json_chain(value) -> list:
    return [value[0], [list(interval) for interval in value[1]]]


def json_unmatched(value) -> list:
    return [value[0], value[1], [list(interval) for interval in value[2]]]


def close(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)


def compare_metric(observed: dict, expected: dict, label: str) -> None:
    for key in ("tp", "fp", "fn"):
        if observed.get(key) != expected.get(key):
            raise ValueError(f"{label}.{key} mismatch: {observed.get(key)} != {expected.get(key)}")
    for key in ("precision", "recall", "f1"):
        if not close(observed.get(key), expected.get(key)):
            raise ValueError(f"{label}.{key} mismatch: {observed.get(key)} != {expected.get(key)}")


def compare_bootstrap(observed: dict, expected: dict, label: str) -> None:
    if observed.get("resamples") != expected.get("resamples") or observed.get("seed") != expected.get("seed"):
        raise ValueError(f"{label} metadata mismatch")
    if len(observed.get("ci95", [])) != 2 or len(expected.get("ci95", [])) != 2:
        raise ValueError(f"{label}.ci95 schema mismatch")
    if not all(close(a, b) for a, b in zip(observed["ci95"], expected["ci95"])):
        raise ValueError(f"{label}.ci95 mismatch: {observed['ci95']} != {expected['ci95']}")


def recheck(root: Path, cfg: dict, run: str, revision: str, result_path: Path) -> dict:
    canonical = load_json(result_path)
    if canonical.get("experiment_id") != cfg["experiment_id"] or canonical.get("claim_eligible") is not False:
        raise ValueError("canonical result identity/claim contract mismatch")
    per_core, correct, unmatched = replay_cells(root, cfg, run, revision)
    if canonical.get("core_count") != CORE_COUNT or canonical.get("completed_cells") != CORE_COUNT * len(MODES):
        raise ValueError("canonical result does not declare the fixed 20x3 scope")
    for row, expected in zip(canonical.get("per_core", []), per_core):
        if row.get("core") != expected["core"]:
            raise ValueError("canonical per-core order mismatch")
        for mode in MODES:
            compare_metric(row["metrics"][mode], expected["metrics"][mode], f'{expected["core"]}/{mode}')
    if len(canonical.get("per_core", [])) != CORE_COUNT:
        raise ValueError("canonical per-core metric count mismatch")

    summary = {mode: aggregate(per_core, mode) for mode in MODES}
    for mode in MODES:
        compare_metric(canonical["metrics"][mode], summary[mode], f"metrics/{mode}")

    comparisons = {}
    for left, right in (("P", "U"), ("R", "U"), ("P", "R")):
        left_right = f"{left}_minus_{right}"
        left_summary, right_summary = summary[left], summary[right]
        gained = sorted(correct[left] - correct[right])
        lost = sorted(correct[right] - correct[left])
        new_unmatched = sorted(unmatched[left] - unmatched[right])
        expected = {
            "locus_f1_delta": left_summary["f1"] - right_summary["f1"],
            "recall_delta": left_summary["recall"] - right_summary["recall"],
            "gained_units": [list(item) for item in gained],
            "lost_units": [list(item) for item in lost],
            "new_unmatched": [json_unmatched(item) for item in new_unmatched],
            "bootstrap": bootstrap(per_core, left, right, cfg),
        }
        observed = canonical["comparisons"][left_right]
        for key in ("locus_f1_delta", "recall_delta"):
            if not close(observed.get(key), expected[key]):
                raise ValueError(f"comparisons/{left_right}/{key} mismatch")
        for key in ("gained_units", "lost_units", "new_unmatched"):
            if observed.get(key) != expected[key]:
                raise ValueError(f"comparisons/{left_right}/{key} mismatch")
        compare_bootstrap(observed["bootstrap"], expected["bootstrap"], f"comparisons/{left_right}/bootstrap")
        comparisons[left_right] = expected

    p_u = comparisons["P_minus_U"]
    u_correct_count = len(correct["U"])
    lost_fraction = len(p_u["lost_units"]) / u_correct_count if u_correct_count else None
    score = cfg["score"]
    gate = (
        p_u["locus_f1_delta"] >= score["min_absolute_locus_f1_delta"] and
        p_u["bootstrap"]["ci95"][0] > score["min_bootstrap_ci95_lower"] and
        p_u["recall_delta"] >= score["min_recall_delta"] and
        lost_fraction is not None and lost_fraction <= score["max_lost_u_correct_fraction"]
    )
    expected_decision = "P3_BASE_MASK_UTILITY_SUPPORT" if gate else "P3_BASE_MASK_UTILITY_GATE_NOT_MET"
    if canonical.get("decision") != expected_decision or canonical.get("gate", {}).get("passed") is not gate:
        raise ValueError("canonical four-gate decision mismatch")
    return {
        "status": "INDEPENDENT_RECHECK_PASS",
        "experiment_id": cfg["experiment_id"],
        "scope": "independent replay of fixed full 20-core U/P/R result and protocol gates",
        "source_result": str(result_path),
        "core_count": CORE_COUNT,
        "cell_count": CORE_COUNT * len(MODES),
        "metrics": summary,
        "comparisons": comparisons,
        "lost_u_correct_fraction": lost_fraction,
        "gate": {**score, "passed": gate},
        "canonical_match": {
            "per_core_counts": True,
            "aggregate_counts": True,
            "p_minus_u": True,
            "r_minus_u": True,
            "p_minus_r": True,
            "four_gate_decision": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run", choices=["full"], required=True)
    parser.add_argument("--revision", choices=list(REVISIONS), default="r1")
    parser.add_argument("--result", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    cfg_path = args.config if args.config.is_absolute() else root / args.config
    cfg = load_json(cfg_path)
    out = run_root(root, cfg, args.run, args.revision)
    result_path = args.result or out / "result.json"
    if not result_path.is_absolute():
        result_path = root / result_path
    report = recheck(root, cfg, args.run, args.revision, result_path)
    output = args.output or out / "independent_recheck.json"
    if not output.is_absolute():
        output = root / output
    write_json(output, report)
    print(json.dumps({"status": report["status"], "gate_passed": report["gate"]["passed"],
                      "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
