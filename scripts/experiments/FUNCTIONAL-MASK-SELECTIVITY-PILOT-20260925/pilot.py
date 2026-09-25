#!/usr/bin/env python3
"""Coverage-matched mask-selection pilot on the fixed chicken/fish panels.

The script deliberately reuses the existing D and RM2 artifacts.  It never
trains a model, reads the gene reference during mask construction, changes the
D threshold, or selects a region from a downstream result.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
NAME = "FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925"
CFG = json.loads((ROOT / "configs" / (NAME + ".json")).read_text())
OUT = ROOT / "outputs" / NAME
REPORT = ROOT / "reports" / NAME
NEW_ARMS = ("RM2_FULL", "D_COMMON_RANDOM", "RM2_COMMON_RANDOM", "RM2_COMMON_CONF")
SCORE_ARMS = ("U", "D_FIXED", "RM2_FULL", "D_COMMON_RANDOM", "RM2_COMMON_RANDOM", "RM2_COMMON_CONF")
# The existing D/R_TE arms lowercase only callable A/C/G/T positions.  Keep
# that same material definition when constructing the common budget.
LOWERCASE_BASES = set("acgt")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = load_module(
    ROOT / "scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py",
    "functional_mask_base",
)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def read_json(path: Path):
    return json.loads(path.read_text())


def read_single_fasta(path: Path):
    header = None
    chunks = []
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                if header is not None:
                    raise ValueError(f"expected one FASTA record in {path}")
                header = line[1:].strip().split()[0]
            elif line.strip():
                chunks.append(line.strip())
    if header is None:
        raise ValueError(f"missing FASTA record in {path}")
    return header, "".join(chunks)


def write_fasta(path: Path, record: str, sequence: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        handle.write(">" + record + "\n")
        for left in range(0, len(sequence), 80):
            handle.write(sequence[left:left + 80] + "\n")


def load_target_records(path: Path, wanted):
    """Read only requested records while streaming the potentially 1.6 GB FASTA."""
    wanted = set(wanted)
    result = {}
    current = None
    chunks = []
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                if current in wanted:
                    if current in result:
                        raise ValueError(f"duplicate FASTA record {current} in {path}")
                    result[current] = "".join(chunks)
                current = line[1:].strip().split()[0]
                chunks = []
            elif current in wanted:
                chunks.append(line.strip())
        if current in wanted:
            if current in result:
                raise ValueError(f"duplicate FASTA record {current} in {path}")
            result[current] = "".join(chunks)
    missing = wanted - set(result)
    if missing:
        raise ValueError(f"missing requested FASTA records {sorted(missing)[:8]} from {path}")
    return result


def lowercase_runs(sequence: str):
    runs = []
    start = None
    for i, base_letter in enumerate(sequence):
        if base_letter in LOWERCASE_BASES:
            if start is None:
                start = i
        elif start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(sequence)))
    return runs


def merge_runs(intervals):
    merged = []
    for left, right in sorted((int(a), int(b)) for a, b in intervals if int(b) > int(a)):
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    return [(left, right) for left, right in merged]


def mask_sequence(sequence: str, intervals) -> str:
    data = bytearray(sequence.upper(), "ascii")
    for left, right in intervals:
        if not 0 <= left <= right <= len(data):
            raise ValueError("mask interval outside sequence")
        # Match the existing D/R_TE construction: mask callable A/C/G/T
        # letters, while preserving ambiguous bases and their case semantics.
        data[left:right] = bytes(
            letter + 32 if letter in (65, 67, 71, 84) else letter
            for letter in data[left:right]
        )
    return data.decode("ascii")


def bin_index(length: int) -> int:
    for index, (left, right) in enumerate(CFG["common_budget"]["length_strata_bp"]):
        if length >= left and (right is None or length < right):
            return index
    raise ValueError(f"run length {length} is outside configured strata")


def runs_by_bin(runs):
    grouped = [[] for _ in CFG["common_budget"]["length_strata_bp"]]
    for left, right in runs:
        grouped[bin_index(right - left)].append((left, right))
    return grouped


def stable_priority(species: str, core_id: str, arm: str, run):
    seed = CFG["random"]["seed"]
    text = f"{seed}|{species}|{core_id}|{arm}|{run[0]}|{run[1]}"
    digest = hashlib.sha256(text.encode("ascii")).hexdigest()
    return digest, run[0], run[1]


def quality_key(row):
    quality = row["quality"] or {}
    return (
        0 if row["quality"] is not None else 1,
        quality.get("divergence", float("inf")),
        -quality.get("sw_per_aligned_length", -1.0),
        -quality.get("alignment_length", -1),
        quality.get("query_begin", 10**18),
        quality.get("query_end", 10**18),
        quality.get("native_id", 10**18),
        row["interval"][0],
        row["interval"][1],
    )


def select_exact(grouped, quotas, order_fn):
    selected = []
    selected_meta = []
    for index, quota in enumerate(quotas):
        remaining = int(quota)
        if remaining == 0:
            continue
        ordered = sorted(grouped[index], key=order_fn)
        for item in ordered:
            if remaining <= 0:
                break
            left, right = item["interval"] if isinstance(item, dict) else item
            length = right - left
            take = min(remaining, length)
            if take == length:
                chosen = (left, right)
            else:
                extra = length - take
                chosen = (left + extra // 2, left + extra // 2 + take)
            selected.append(chosen)
            selected_meta.append({"stratum": index, "source": [left, right], "selected": list(chosen), "length": take})
            remaining -= take
        if remaining:
            raise ValueError(f"stratum {index} could not meet exact quota {quota}; remaining {remaining}")
    return merge_runs(selected), selected_meta


def parse_rm2_out(path: Path, wanted):
    """Parse native RepeatMasker alignment rows without looking at any labels."""
    wanted = set(wanted)
    result = defaultdict(list)
    with path.open(errors="replace") as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < 14 or not re.fullmatch(r"\d+", fields[0]):
                continue
            query = fields[4]
            if query not in wanted:
                continue
            try:
                score = int(fields[0])
                divergence = float(fields[1])
                begin = int(fields[5]) - 1
                end = int(fields[6])
                # Standard RepeatMasker .out has 15 data fields and may add
                # an independent trailing '*' column.  Never parse that '*' as
                # the native ID; preserve a numeric fallback for minor format
                # variants while keeping the row deterministic.
                id_candidates = [fields[14].rstrip("*")] if len(fields) > 14 else []
                id_candidates.extend(reversed([field.rstrip("*") for field in fields[15:]]))
                native_id = next(int(value) for value in id_candidates if value.isdigit())
            except ValueError:
                continue
            if not begin < end:
                continue
            result[query].append({
                "start": begin,
                "end": end,
                "sw_score": score,
                "divergence": divergence,
                "alignment_length": end - begin,
                "sw_per_aligned_length": score / (end - begin),
                "query_begin": begin,
                "query_end": end,
                "native_id": native_id,
            })
    for query in result:
        result[query].sort(key=lambda row: (row["start"], row["end"], row["native_id"]))
    return result


def attach_native_quality(runs, records, halo_start):
    """Assign the best overlapping native alignment to each relative run."""
    records = list(records)
    pointer = 0
    result = []
    for left, right in runs:
        absolute_left = halo_start + left
        absolute_right = halo_start + right
        while pointer < len(records) and records[pointer]["end"] <= absolute_left:
            pointer += 1
        best = None
        scan = pointer
        while scan < len(records) and records[scan]["start"] < absolute_right:
            row = records[scan]
            if row["end"] > absolute_left:
                candidate = (
                    row["divergence"],
                    -row["sw_per_aligned_length"],
                    -row["alignment_length"],
                    row["query_begin"],
                    row["query_end"],
                    row["native_id"],
                )
                if best is None or candidate < best[0]:
                    best = (candidate, row)
            scan += 1
        result.append({"interval": [left, right], "quality": None if best is None else best[1]})
    return result


def mask_summary(runs, core_start: int, core_end: int, selection_records=None):
    grouped = runs_by_bin(runs)
    source_bp = [sum(right - left for left, right in group) for group in grouped]
    source_runs = [len(group) for group in grouped]
    if selection_records is not None:
        source_bp, source_runs = [0] * len(grouped), [0] * len(grouped)
        for row in selection_records:
            source_bp[row["stratum"]] += row["length"]
            source_runs[row["stratum"]] += 1
    core_masked = sum(max(0, min(right, core_end) - max(left, core_start)) for left, right in runs)
    left_halo_end = core_start
    right_halo_start = core_end
    left_halo_masked = sum(max(0, min(right, left_halo_end) - left) for left, right in runs)
    right_halo_masked = sum(max(0, right - max(left, right_halo_start)) for left, right in runs)
    return {
        "runs": len(runs),
        "bp": sum(right - left for left, right in runs),
        "core_bp": core_masked,
        "left_halo_bp": left_halo_masked,
        "right_halo_bp": right_halo_masked,
        "source_length_strata_bp": source_bp,
        "source_length_strata_runs": source_runs,
        "actual_length_strata_bp": [sum(right - left for left, right in group) for group in runs_by_bin(runs)],
        "actual_length_strata_runs": [len(group) for group in runs_by_bin(runs)],
    }


def run_command(argv, out: Path, prefix: str, env=None):
    tick = time.monotonic()
    with (out / (prefix + ".stdout")).open("w") as stdout, (out / (prefix + ".stderr")).open("w") as stderr:
        completed = subprocess.run(argv, stdout=stdout, stderr=stderr, env=env)
    row = {"argv": argv, "seconds": time.monotonic() - tick, "exit_code": completed.returncode}
    dump(out / (prefix + ".command.json"), row)
    if completed.returncode:
        raise RuntimeError(f"{prefix} exited {completed.returncode}")
    return row


def old_root(species):
    return ROOT / CFG["inputs"]["utility_root"] / species


def prepare(species):
    out = OUT / species
    if out.exists():
        raise FileExistsError(f"preserve existing pilot output: {out}")
    out.mkdir(parents=True)
    old = old_root(species)
    geometry = read_json(old / "geometry.json")
    wanted = {row["chrom"] for row in geometry}
    rm2_path = ROOT / CFG["inputs"]["rm2_masked_fasta"].replace("{species}", species)
    out_path = ROOT / CFG["inputs"]["rm2_annotation_out"].replace("{species}", species)
    rm2_records = load_target_records(rm2_path, wanted)
    rm2_alignments = parse_rm2_out(out_path, wanted)
    manifest = {
        "protocol": NAME,
        "species": species,
        "status": "PREPARED",
        "inputs": {
            "geometry": str(old / "geometry.json"),
            "existing_reference": str(old / "reference.json"),
            "existing_U_D": str(old),
            "rm2_masked_fasta": str(rm2_path),
            "rm2_annotation_out": str(out_path),
        },
        "selection_used_labels_or_downstream_scores": False,
        "cores": [],
    }
    for geometry_row in geometry:
        core_id = geometry_row["id"]
        cell = out / core_id
        cell.mkdir()
        old_cell = old / core_id
        u_record, u_seq = read_single_fasta(old_cell / "U.fasta")
        d_record, d_seq = read_single_fasta(old_cell / "D.fasta")
        rm2_seq = rm2_records[geometry_row["chrom"]]
        left = int(geometry_row["halo_start"])
        right = int(geometry_row["halo_end"])
        if len(rm2_seq) < right:
            raise ValueError(f"RM2 record too short for {species}/{core_id}")
        rm2_seq = rm2_seq[left:right]
        if u_record != geometry_row["record_id"] or d_record != u_record:
            raise ValueError(f"existing record mismatch for {species}/{core_id}")
        if len(u_seq) != right - left or len(d_seq) != len(u_seq) or d_seq.upper() != u_seq.upper() or rm2_seq.upper() != u_seq.upper():
            raise ValueError(f"same-assembly uppercase sequence check failed for {species}/{core_id}")
        d_runs = lowercase_runs(d_seq)
        rm2_runs = lowercase_runs(rm2_seq)
        d_groups = runs_by_bin(d_runs)
        rm2_groups = runs_by_bin(rm2_runs)
        quotas = [
            min(
                sum(b - a for a, b in d_group),
                sum(b - a for a, b in rm_group),
            )
            for d_group, rm_group in zip(d_groups, rm2_groups)
        ]
        rm2_quality = attach_native_quality(rm2_runs, rm2_alignments[geometry_row["chrom"]], left)
        quality_groups = runs_by_bin(rm2_runs)
        quality_lookup = {(row["interval"][0], row["interval"][1]): row for row in rm2_quality}
        rm2_quality_groups = [[quality_lookup[(a, b)] for a, b in group] for group in quality_groups]
        d_random_groups = [[{"interval": run} for run in group] for group in d_groups]
        rm2_random_groups = [[{"interval": run} for run in group] for group in rm2_groups]
        d_common, d_common_meta = select_exact(
            d_random_groups,
            quotas,
            lambda row: stable_priority(species, core_id, "D_COMMON_RANDOM", tuple(row["interval"])),
        )
        rm2_common_random, rm2_common_random_meta = select_exact(
            rm2_random_groups,
            quotas,
            lambda row: stable_priority(species, core_id, "RM2_COMMON_RANDOM", tuple(row["interval"])),
        )
        rm2_common_conf, rm2_common_conf_meta = select_exact(
            rm2_quality_groups,
            quotas,
            quality_key,
        )
        masks = {
            "D_FIXED": d_runs,
            "RM2_FULL": rm2_runs,
            "D_COMMON_RANDOM": d_common,
            "RM2_COMMON_RANDOM": rm2_common_random,
            "RM2_COMMON_CONF": rm2_common_conf,
        }
        write_fasta(cell / "U.fasta", u_record, u_seq)
        for arm, runs in masks.items():
            write_fasta(cell / (arm + ".fasta"), u_record, mask_sequence(u_seq, runs))
        selections = {
            "D_COMMON_RANDOM": d_common_meta,
            "RM2_COMMON_RANDOM": rm2_common_random_meta,
            "RM2_COMMON_CONF": rm2_common_conf_meta,
        }
        row_manifest = {
            "id": core_id,
            "chrom": geometry_row["chrom"],
            "core": [geometry_row["start"], geometry_row["end"]],
            "halo": [left, right],
            "input_bp": len(u_seq),
            "mask_summaries": {arm: mask_summary(runs, 100000, len(u_seq) - 100000, selections.get(arm)) for arm, runs in masks.items()},
            "common_budget_by_stratum_bp": quotas,
            "common_budget_bp": sum(quotas),
            "rm2_runs_without_native_alignment": sum(1 for row in rm2_quality if row["quality"] is None),
            "selection_records": selections,
        }
        dump(cell / "mask_manifest.json", row_manifest)
        manifest["cores"].append(row_manifest)
    dump(out / "manifest.json", manifest)
    dump(out / "prepare.json", {"status": "PREPARED", "species": species, "core_count": len(geometry), "new_arms": list(NEW_ARMS)})
    print(json.dumps({"species": species, "status": "PREPARED", "cores": len(geometry)}), flush=True)


def augustus_env():
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = "/opt/ebsofts/bzip2/1.0.8-GCCcore-12.2.0/lib:" + env.get("LD_LIBRARY_PATH", "")
    env["AUGUSTUS_CONFIG_PATH"] = "/opt/ebsofts/AUGUSTUS/3.5.0-foss-2022b/config"
    return env


def predict(species: str, index: int):
    out = OUT / species
    manifest = read_json(out / "manifest.json")
    row = manifest["cores"][index]
    cell = out / row["id"]
    status_path = cell / "status.json"
    status = read_json(status_path) if status_path.exists() else {"status": "RUNNING", "species": species, "core": row, "arms": {}}
    binary = "/opt/ebsofts/AUGUSTUS/3.5.0-foss-2022b/bin/augustus"
    for arm in NEW_ARMS:
        gff = cell / (arm + ".gff3")
        if gff.exists():
            command_path = cell / (arm + ".command.json")
            if not command_path.exists() or read_json(command_path).get("exit_code") != 0:
                raise ValueError(f"existing {arm} GFF lacks a successful command record")
            chains, _ = base.parse_predictions(gff, base.Core(row["chrom"], index, row["core"][0], row["core"][1], row["halo"][0], row["halo"][1]), "gff3")
            status["arms"][arm] = {"reused": True, "exit_code": 0, "predicted_chains": len(chains), "command": str(command_path)}
            continue
        argv = [
            binary,
            "--species=" + CFG["species"][species]["augustus_species"],
            "--gff3=on",
            "--softmasking=1",
            "--UTR=off",
            "--stopCodonExcludedFromCDS=false",
            "--alternatives-from-evidence=false",
            "--alternatives-from-sampling=false",
            str(cell / (arm + ".fasta")),
        ]
        command = run_command(argv, cell, arm, augustus_env())
        (cell / (arm + ".stdout")).rename(gff)
        core = base.Core(row["chrom"], index, row["core"][0], row["core"][1], row["halo"][0], row["halo"][1])
        chains, _ = base.parse_predictions(gff, core, "gff3")
        status["arms"][arm] = {**command, "predicted_chains": len(chains), "same_uppercase_letters": True}
        dump(status_path, status)
    status["status"] = "COMPLETED"
    status["job_id"] = os.environ.get("SLURM_JOB_ID")
    dump(status_path, status)
    print(json.dumps(status), flush=True)


def score(species: str):
    import numpy as np

    out = OUT / species
    manifest = read_json(out / "manifest.json")
    old = old_root(species)
    refs = read_json(old / "reference.json")
    units = {u["unit_id"]: u for u in refs["units"]}
    mapping = {
        (u["chrom"], isoform_strand, tuple(map(tuple, iso["intervals"]))): uid
        for uid, u in units.items()
        for iso in u["isoforms"]
        for isoform_strand in (u["strand"],)
    }
    totals = {arm: Counter() for arm in SCORE_ARMS}
    correct = {arm: set() for arm in SCORE_ARMS}
    rows = []
    for index, row in enumerate(manifest["cores"]):
        core = base.Core(row["chrom"], index, row["core"][0], row["core"][1], row["halo"][0], row["halo"][1])
        truth = {uid for uid, unit in units.items() if unit["owner"] == core.key}
        old_status = read_json(old / row["id"] / "status.json")
        if old_status.get("status") != "COMPLETED" or not all(old_status.get("arms", {}).get(arm, {}).get("exit_code") == 0 for arm in ("U", "D")):
            raise ValueError(f"old U/D status is not completed for {species}/{row['id']}")
        pilot_status = read_json(out / row["id"] / "status.json")
        if pilot_status.get("status") != "COMPLETED" or any(pilot_status.get("arms", {}).get(arm, {}).get("exit_code") != 0 for arm in NEW_ARMS):
            raise ValueError(f"new pilot status is not completed for {species}/{row['id']}")
        paths = {
            "U": old / row["id"] / "U.gff3",
            "D_FIXED": old / row["id"] / "D.gff3",
            **{arm: out / row["id"] / (arm + ".gff3") for arm in NEW_ARMS},
        }
        entry = {"id": row["id"], "chrom": row["chrom"], "reference_loci": len(truth), "metrics": {}}
        for arm in SCORE_ARMS:
            if not paths[arm].exists():
                raise ValueError(f"missing prediction {paths[arm]}")
            if arm in ("U", "D_FIXED"):
                # Existing utility cells store command metadata directly next
                # to the arm output as D.command.json/U.command.json.
                command_path = old / row["id"] / (("D" if arm == "D_FIXED" else "U") + ".command.json")
                command = read_json(command_path)
                if command.get("exit_code") != 0:
                    raise ValueError(f"old command failed for {species}/{row['id']}/{arm}")
            chains, _ = base.parse_predictions(paths[arm], core, "gff3")
            matched = {chain for chain in chains if (core.chrom, chain.strand, chain.intervals) in mapping}
            found = {mapping[(core.chrom, chain.strand, chain.intervals)] for chain in matched}
            if not found <= truth:
                raise ValueError(f"locus ownership mismatch for {species}/{row['id']}/{arm}")
            metric = base.metrics(len(found), len(chains - matched), len(truth - found))
            totals[arm].update({key: metric[key] for key in ("tp", "fp", "fn")})
            correct[arm].update(found)
            entry["metrics"][arm] = metric
        rows.append(entry)
    metrics = {arm: base.metrics(**counts) for arm, counts in totals.items()}
    pairs = [("D_FIXED", "RM2_FULL"), ("D_COMMON_RANDOM", "RM2_COMMON_RANDOM"), ("RM2_COMMON_CONF", "RM2_COMMON_RANDOM"), ("D_COMMON_RANDOM", "RM2_COMMON_CONF"), ("D_FIXED", "D_COMMON_RANDOM")]
    comparisons = {}
    for left, right in pairs:
        rng = np.random.default_rng(CFG["score"]["bootstrap"]["seed"])
        values = []
        for _ in range(CFG["score"]["bootstrap"]["replicates"]):
            sampled = rng.integers(0, len(rows), len(rows))
            counts = {arm: Counter() for arm in (left, right)}
            for i in sampled:
                for arm in counts:
                    counts[arm].update({key: rows[i]["metrics"][arm][key] for key in ("tp", "fp", "fn")})
            values.append(base.metrics(**counts[left])["f1"] - base.metrics(**counts[right])["f1"])
        comparisons[f"{left}_minus_{right}"] = {
            "f1_delta": metrics[left]["f1"] - metrics[right]["f1"],
            "ci95": np.quantile(values, [0.025, 0.975]).tolist(),
            "gained_loci": sorted(correct[left] - correct[right]),
            "lost_loci": sorted(correct[right] - correct[left]),
        }
    result = {
        "protocol": NAME,
        "status": "COMPLETED",
        "species": species,
        "reference_loci": len(units),
        "metrics": metrics,
        "comparisons": comparisons,
        "per_core": rows,
        "scope": CFG["scope"],
        "pilot_interpretation": CFG["score"]["interpretation"],
    }
    dump(out / "result.json", result)
    render_report(species, result)
    print(json.dumps({"species": species, "reference_loci": len(units), "metrics": metrics, "comparisons": {k: v["f1_delta"] for k, v in comparisons.items()}}), flush=True)


def render_report(species: str, result):
    out = REPORT / species
    out.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Functional mask selectivity pilot: {species}",
        "",
        "This is a fixed-panel development pilot. Chromosome bootstrap intervals are regional sensitivity intervals, not biological-replicate uncertainty.",
        "",
        "## Arm-level scores",
        "",
        "| arm | TP | FP | FN | precision | recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm in SCORE_ARMS:
        m = result["metrics"][arm]
        lines.append(f"| {arm} | {m['tp']} | {m['fp']} | {m['fn']} | {m['precision']:.6f} | {m['recall']:.6f} | {m['f1']:.6f} |")
    lines.extend(["", "## Paired chromosome-bootstrap comparisons", "", "| comparison | F1 delta | 95% interval |", "| --- | ---: | --- |"])
    for key, value in result["comparisons"].items():
        lines.append(f"| {key} | {value['f1_delta']:.6f} | [{value['ci95'][0]:.6f}, {value['ci95'][1]:.6f}] |")
    lines.extend(["", "The pilot must not be upgraded to an independent confirmation result without a separately frozen evidence panel.", ""])
    (out / "RESULTS.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "predict", "score"))
    parser.add_argument("species", choices=tuple(CFG["species"]))
    parser.add_argument("--index", type=int)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.species)
    elif args.action == "predict":
        if args.index is None:
            raise SystemExit("predict requires --index")
        predict(args.species, args.index)
    else:
        score(args.species)


if __name__ == "__main__":
    main()
