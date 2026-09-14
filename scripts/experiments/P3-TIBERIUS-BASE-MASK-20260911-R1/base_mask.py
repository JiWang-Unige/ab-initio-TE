#!/usr/bin/env python3
"""Finite P3-mask versus unmasked Tiberius experiment; no fitting or labels."""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PHASE0 = ROOT / "scripts/experiments/GAP-BRIDGE-PHASE0-R1/gap_bridge_e0.py"
CANONICAL_HEADER = ("seqid", "start", "end", "name", "score", "strand", "source", "attributes")


@dataclass(frozen=True, order=True)
class Core:
    chrom: str
    index: int
    start: int
    end: int
    halo_start: int
    halo_end: int

    @property
    def key(self) -> str:
        return f"{self.chrom}:{self.index}"

    @property
    def record_id(self) -> str:
        return f"{self.chrom}|base_mask_core={self.index}|core={self.start}-{self.end}|halo={self.halo_start}-{self.halo_end}"


@dataclass(frozen=True, order=True)
class Chain:
    strand: str
    intervals: tuple[tuple[int, int], ...]


def write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    tmp.rename(path)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_cfg(path: Path) -> dict:
    cfg = json.loads(path.read_text())
    if cfg["experiment_id"] != "P3-TIBERIUS-BASE-MASK-20260911-R1":
        raise ValueError("unexpected experiment id")
    if cfg["modes"] != ["U", "P", "R"]:
        raise ValueError("exact U/P/R modes required")
    if cfg["p3_mask_rule"] != {"p_te_threshold": 0.5, "states": ["interior", "left_boundary", "right_boundary"]}:
        raise ValueError("frozen P3 mask rule changed")
    if cfg["score"]["primary_comparison"] != "P_minus_U":
        raise ValueError("unexpected primary comparison")
    if cfg["claim_eligible"]:
        raise ValueError("this paired input experiment is not a generalization claim")
    return cfg


def cores(cfg: dict) -> list[Core]:
    g = cfg["geometry"]
    result = []
    for chrom in g["chromosomes"]:
        for index in range(g["core_count_per_chromosome"]):
            start = index * g["stride_bp"]
            result.append(Core(chrom, index, start, start + g["core_bp"],
                               max(0, start - g["halo_bp"]), start + g["core_bp"] + g["halo_bp"]))
    if len(result) != 20 or len({c.key for c in result}) != 20:
        raise ValueError("frozen geometry must be exactly twenty distinct cores")
    return result


def run_root(cfg: dict, run: str, revision: str = "r1") -> Path:
    if run not in cfg["runs"]:
        raise ValueError(f"unknown run: {run}")
    if revision not in ("r1", "r2"):
        raise ValueError(f"unknown output revision: {revision}")
    return ROOT / cfg["output_base"] / f"{run}-{revision}"


def selected(cfg: dict, run: str) -> list[Core]:
    by_key = {core.key: core for core in cores(cfg)}
    keys = cfg["runs"][run]["core_ids"]
    if len(keys) != len(set(keys)) or not keys:
        raise ValueError("run must have nonempty distinct core keys")
    try:
        return [by_key[key] for key in keys]
    except KeyError as error:
        raise ValueError(f"unknown selected core: {error}") from error


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open(encoding="utf-8")


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


def owner(chain: Chain, all_cores: list[Core]) -> tuple[Core | None, str | None]:
    core = next((c for c in all_cores if c.chrom == CURRENT_CHROM.get(chain) and c.start <= chain.intervals[0][0] < c.end), None)
    if core is None:
        return None, "outside_fixed_core"
    if chain.intervals[-1][1] > core.halo_end:
        return core, "boundary_incomplete"
    return core, None


# Chromosome is information external to a Chain. Keeping this map local prevents
# chromosome strings from accidentally participating in exact CDS comparisons.
CURRENT_CHROM: dict[Chain, str] = {}


def parse_reference(cfg: dict, all_cores: list[Core]) -> tuple[dict, dict]:
    raw: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    excluded = Counter()
    with open_text(ROOT / cfg["refseq"]) as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            f = line.rstrip("\r\n").split("\t")
            if len(f) != 16:
                raise ValueError(f"genePredExtended line {line_no}: expected 16 columns")
            chrom, strand = f[2], f[3]
            if chrom not in cfg["geometry"]["chromosomes"]:
                continue
            if strand not in ("+", "-"):
                raise ValueError("invalid reference strand")
            tx_start, tx_end, cds_start, cds_end, exon_count = map(int, f[4:9])
            starts = [int(x) for x in f[9].rstrip(",").split(",") if x]
            ends = [int(x) for x in f[10].rstrip(",").split(",") if x]
            frames = [int(x) for x in f[15].rstrip(",").split(",") if x]
            if not (0 <= tx_start < tx_end and tx_start <= cds_start <= cds_end <= tx_end):
                raise ValueError("invalid reference transcript span")
            if not (len(starts) == len(ends) == len(frames) == exon_count and exon_count > 0):
                raise ValueError("reference exon/frame count mismatch")
            if cds_start == cds_end or f[13] != "cmpl" or f[14] != "cmpl":
                excluded["noncoding_or_incomplete"] += 1
                continue
            pieces = []
            for start, end, frame in zip(starts, ends, frames):
                left, right = max(start, cds_start), min(end, cds_end)
                if left < right:
                    if frame not in (0, 1, 2):
                        raise ValueError("invalid coding exon frame")
                    pieces.append((left, right))
                elif frame != -1:
                    raise ValueError("invalid noncoding exon frame")
            chain = Chain(strand, normalize(pieces))
            CURRENT_CHROM[chain] = chrom
            core, reason = owner(chain, all_cores)
            if reason:
                excluded[reason] += 1
                continue
            key = (chrom, strand, f[12] or f[1])
            raw[key].append({"transcript_id": f[1], "chain": chain, "core": core})
    units = {}
    chain_to_units = defaultdict(set)
    by_core = defaultdict(set)
    disjoint = []
    for key, rows in sorted(raw.items()):
        components = []
        end = -1
        for row in sorted(rows, key=lambda x: x["chain"].intervals[0][0]):
            start, stop = row["chain"].intervals[0][0], row["chain"].intervals[-1][1]
            if start > end:
                components.append([start, stop])
            else:
                components[-1][1] = max(components[-1][1], stop)
            end = max(end, stop)
        if len(components) != 1:
            disjoint.append({"key": list(key), "components": components})
            continue
        owner_keys = {row["core"].key for row in rows}
        if len(owner_keys) != 1:
            raise ValueError(f"gene key crosses core owner: {key}")
        core = rows[0]["core"]
        unit_id = f"{key[0]}|{key[1]}|{key[2]}|{components[0][0]}-{components[0][1]}"
        isoforms = sorted(set(row["chain"] for row in rows))
        units[unit_id] = {"unit_id": unit_id, "chrom": key[0], "strand": key[1], "name2": key[2],
                          "owner": core.key, "span": components[0],
                          "isoforms": [{"intervals": [list(x) for x in c.intervals]} for c in isoforms],
                          "transcript_ids": sorted(row["transcript_id"] for row in rows)}
        by_core[core.key].add(unit_id)
        for c in isoforms:
            chain_to_units[(key[0], c)].add(unit_id)
    if disjoint:
        raise ValueError(f"name2/strand has noncontiguous loci: {disjoint[:3]}")
    ambiguous = {str(key): sorted(value) for key, value in chain_to_units.items() if len(value) != 1}
    if ambiguous:
        raise ValueError(f"CDS chain maps to multiple units: {list(ambiguous)[:3]}")
    report = {"reference_source": cfg["refseq"], "unit_definition": "(chrom,strand,name2), one contiguous locus",
              "unit_count": len(units), "per_core_unit_count": {c.key: len(by_core[c.key]) for c in all_cores},
              "excluded_transcript_rows": dict(excluded), "units": list(units.values()),
              "disjoint_name2_keys": disjoint}
    lookup = {"units": units, "by_core": {key: sorted(value) for key, value in by_core.items()},
              "chain_to_unit": {(chrom, chain.strand, chain.intervals): next(iter(ids))
                                for (chrom, chain), ids in chain_to_units.items()}}
    return report, lookup


def prepare(cfg: dict, run: str, revision: str = "r1") -> None:
    out = run_root(cfg, run, revision)
    out.mkdir(parents=True, exist_ok=False)
    all_cores = cores(cfg)
    report, _ = parse_reference(cfg, all_cores)
    write_json(out / "config.json", cfg)
    with (out / "geometry.tsv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["core_id", "chrom", "index", "core_start", "core_end", "halo_start", "halo_end"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for core in all_cores:
            writer.writerow({"core_id": core.key, "chrom": core.chrom, "index": core.index,
                             "core_start": core.start, "core_end": core.end,
                             "halo_start": core.halo_start, "halo_end": core.halo_end})
    write_json(out / "reference_contract.json", report)
    write_json(out / "status.json", {"status": "PREPARED_NO_MODEL_OUTPUTS", "run": run,
                                      "selected_cores": [c.key for c in selected(cfg, run)],
                                      "labels_read": False, "sealed_labels_read": False,
                                      "reference_units": report["unit_count"]})


def canonical_intervals(path: Path, chrom: str) -> list[tuple[int, int]]:
    rows = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != CANONICAL_HEADER:
            raise ValueError("unexpected P3 canonical header")
        for row in reader:
            if row["seqid"] != chrom:
                raise ValueError("wrong P3 canonical chromosome")
            start, end = int(row["start"]), int(row["end"])
            if start >= end:
                raise ValueError("invalid canonical interval")
            rows.append((start, end))
    return rows


def repeat_intervals(path: Path, core: Core) -> list[tuple[int, int]]:
    rows = []
    with open_text(path) as handle:
        for line in handle:
            f = line.rstrip("\n").split("\t")
            if len(f) != 17:
                raise ValueError("raw rmsk expected 17 columns")
            if f[5] != core.chrom:
                continue
            start, end = int(f[6]), int(f[7])
            left, right = max(start, core.halo_start), min(end, core.halo_end)
            if left < right:
                rows.append((left, right))
    return rows


def interval_mask(intervals, start: int, end: int) -> np.ndarray:
    mask = np.zeros(end - start, dtype=bool)
    for left, right in intervals:
        left, right = max(left, start), min(right, end)
        if left < right:
            mask[left-start:right-start] = True
    return mask


def write_fasta(path: Path, record: str, sequence: str) -> None:
    with path.open("x", encoding="ascii") as handle:
        handle.write(f">{record}\n")
        for i in range(0, len(sequence), 80):
            handle.write(sequence[i:i+80] + "\n")


def run_core(cfg: dict, run: str, requested: str, revision: str = "r1") -> None:
    current = next((c for c in selected(cfg, run) if c.key == requested), None)
    if current is None:
        raise ValueError("core is not in this frozen run")
    out = run_root(cfg, run, revision)
    if not (out / "reference_contract.json").exists():
        raise ValueError("prepare must run first")
    cell = out / f"core-{current.chrom}-{current.index}"
    cell.mkdir()
    phase0 = load_module(PHASE0, "base_mask_phase0")
    region = cell / "region.jsonl.gz"
    phase0.write_region_jsonl(ROOT / cfg["genome"], current.chrom, current.halo_start, current.halo_end,
                              region, cell / "region.manifest.json")
    phase0.export_frozen_p3(ROOT / cfg["p3_model"], region, cell / "p3_pte.npy", cell / "p3_states.npy",
                             cell / "P.canonical.tsv", cell / "p3_export.json", None)
    p3 = json.loads((cell / "p3_export.json").read_text())
    if p3["model_schema"] != cfg["p3_expected_schema"] or p3["threshold"] != cfg["p3_mask_rule"]["p_te_threshold"]:
        raise ValueError("frozen P3 model/mask contract changed")
    sequence = "".join(phase0.iter_region_chunks(ROOT / cfg["genome"], current.chrom, current.halo_start, current.halo_end))
    if len(sequence) != current.halo_end-current.halo_start or sequence != sequence.upper():
        raise ValueError("assembly sequence contract failed")
    p_mask = interval_mask(canonical_intervals(cell / "P.canonical.tsv", current.chrom), current.halo_start, current.halo_end)
    r_mask = interval_mask(repeat_intervals(ROOT / cfg["repeat_mask"], current), current.halo_start, current.halo_end)
    values = {"U": np.zeros(len(sequence), dtype=bool), "P": p_mask, "R": r_mask}
    for mode, mask in values.items():
        masked = "".join(base.lower() if flag and base in "ACGT" else base for base, flag in zip(sequence, mask))
        if masked.upper() != sequence:
            raise ValueError("mask changed sequence letters")
        write_fasta(cell / f"{mode}.fasta", current.record_id, masked)
    write_json(cell / "input_manifest.json", {
        "core": asdict(current), "record_id": current.record_id, "fasta_uppercase_letters_equal": True,
        "modes": {mode: {"lowercase_acgt_bp": int(mask.sum()), "fasta": f"{mode}.fasta"} for mode, mask in values.items()},
        "p3_export": p3, "repeat_mask_source": cfg["repeat_mask"], "labels_read": False})


def fasta(path: Path):
    name, chunks = None, []
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks)
                name, chunks = line[1:].strip(), []
            else:
                chunks.append(line.strip())
    if name is not None:
        yield name, "".join(chunks)


def preflight_core(cfg: dict, run: str, requested: str, revision: str = "r1") -> None:
    from bricks2marble.io import load_fasta
    current = next(c for c in selected(cfg, run) if c.key == requested)
    cell = run_root(cfg, run, revision) / f"core-{current.chrom}-{current.index}"
    records = []
    first_five = None
    for mode in cfg["modes"]:
        path = cell / f"{mode}.fasta"
        raw = list(fasta(path))
        if len(raw) != 1 or raw[0][0] != current.record_id:
            raise ValueError("wrong FASTA record")
        encoded = load_fasta(path).one_hot()
        expected = np.fromiter((base in "acgt" for base in raw[0][1]), dtype=bool)
        if encoded.shape != (1, len(expected), 6) or not np.array_equal(encoded[0, :, 5], expected):
            raise ValueError("actual FASTA one_hot softmask does not match sequence case")
        if first_five is None:
            first_five = encoded[0, :, :5]
        elif not np.array_equal(first_five, encoded[0, :, :5]):
            raise ValueError("mask changed an ACGTN channel")
        records.append({"mode": mode, "shape": list(encoded.shape), "masked_bp": int(expected.sum())})
    if records[0]["masked_bp"] != 0 or records[1]["masked_bp"] <= 0 or records[2]["masked_bp"] <= 0:
        raise ValueError("U/P/R expected mask content absent")
    write_json(cell / "preflight.json", {"status": "INPUT_PREFLIGHT_PASS", "records": records,
                                         "actual_loader": "bricks2marble.io.load_fasta().one_hot",
                                         "first_five_tracks_equal": True})


def parse_predictions(path: Path, core: Core, fmt: str) -> tuple[set[Chain], Counter]:
    txs = {}
    with path.open() as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            f = line.rstrip().split("\t")
            if len(f) != 9:
                raise ValueError(f"annotation line {line_no}: expected 9 fields")
            record, _, feature, start, end, _, strand, phase, attrs = f
            if feature != "CDS":
                continue
            if record != core.record_id or strand not in ("+", "-") or phase not in (".", "0", "1", "2"):
                raise ValueError("invalid native CDS row")
            if fmt == "gtf":
                tid = dict(re.findall(r'(\w+)\s+"([^"]*)"', attrs)).get("transcript_id")
                ids = [tid]
            else:
                fields = dict(x.split("=", 1) for x in attrs.split(";") if "=" in x)
                ids = fields.get("Parent", "").split(",")
            if not all(ids):
                raise ValueError("missing prediction transcript id")
            left, right = int(start)-1, int(end)
            if not 0 <= left < right <= core.halo_end-core.halo_start:
                raise ValueError("CDS outside input halo")
            for tid in ids:
                entry = txs.setdefault(tid, {"strand": strand, "intervals": []})
                if entry["strand"] != strand:
                    raise ValueError("inconsistent prediction strand")
                entry["intervals"].append((left+core.halo_start, right+core.halo_start))
    content = Counter()
    chains = set()
    for tid, value in txs.items():
        chain = Chain(value["strand"], normalize(value["intervals"]))
        if not (core.start <= chain.intervals[0][0] < core.end and chain.intervals[-1][1] <= core.halo_end):
            continue
        content[(chain.strand, chain.intervals)] += 1
        chains.add(chain)
    return chains, content


def metrics(tp: int, fp: int, fn: int) -> dict:
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp+fp) if tp+fp else None,
            "recall": tp / (tp+fn) if tp+fn else None,
            "f1": 2*tp / (2*tp+fp+fn) if 2*tp+fp+fn else None}


def load_contract(out: Path):
    report = json.loads((out / "reference_contract.json").read_text())
    units = {unit["unit_id"]: unit for unit in report["units"]}
    mapping = {}
    for unit in report["units"]:
        for isoform in unit["isoforms"]:
            key = (unit["chrom"], unit["strand"], tuple(tuple(x) for x in isoform["intervals"]))
            if key in mapping and mapping[key] != unit["unit_id"]:
                raise ValueError("ambiguous reference CDS chain")
            mapping[key] = unit["unit_id"]
    return report, units, mapping


def score_core(cfg: dict, out: Path, core: Core, units: dict, mapping: dict) -> dict:
    cell = out / f"core-{core.chrom}-{core.index}"
    if not (cell / "preflight.json").exists():
        raise ValueError(f"no preflight for {core.key}")
    truth = {unit_id for unit_id, unit in units.items() if unit["owner"] == core.key}
    values = {}
    for mode in cfg["modes"]:
        gtf, gff3 = cell / f"{mode}.gtf", cell / f"{mode}.gff3"
        chains, a = parse_predictions(gtf, core, "gtf")
        other, b = parse_predictions(gff3, core, "gff3")
        if a != b or chains != other:
            raise ValueError(f"GTF/GFF3 mismatch for {core.key}/{mode}")
        obs = json.loads((cell / f"{mode}.observation.json").read_text())
        if obs.get("calls", 0) < 1 or not obs.get("passed"):
            raise ValueError(f"missing actual model input observation for {core.key}/{mode}")
        if mode == "U" and obs.get("masked_positions") != 0:
            raise ValueError("U reached model with a nonzero softmask")
        if mode != "U" and obs.get("masked_positions", 0) <= 0:
            raise ValueError(f"{mode} reached model with no observed softmask")
        matched_chains = {chain for chain in chains
                          if (core.chrom, chain.strand, chain.intervals) in mapping}
        correct = {mapping[(core.chrom, chain.strand, chain.intervals)] for chain in matched_chains}
        unmatched = chains - matched_chains
        values[mode] = {"predicted": chains, "correct": correct,
                        "unmatched": unmatched,
                        "metric": metrics(len(correct), len(unmatched), len(truth-correct)),
                        "observation": obs}
    return {"truth": truth, "modes": values}


def bootstrap(per_core: list[dict], left: str, right: str, cfg: dict) -> dict:
    rng = np.random.default_rng(cfg["score"]["bootstrap_seed"])
    n, reps = len(per_core), cfg["score"]["bootstrap_replicates"]
    diffs = np.empty(reps)
    for i in range(reps):
        sample = rng.integers(0, n, size=n)
        sums = {mode: Counter() for mode in (left, right)}
        for index in sample:
            for mode in sums:
                metric = per_core[index]["modes"][mode]["metric"]
                sums[mode].update({key: metric[key] for key in ("tp", "fp", "fn")})
        diffs[i] = metrics(**sums[left])["f1"] - metrics(**sums[right])["f1"]
    return {"resamples": reps, "seed": cfg["score"]["bootstrap_seed"],
            "ci95": [float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))]}


def score(cfg: dict, run: str, revision: str = "r1") -> None:
    out = run_root(cfg, run, revision)
    expected = selected(cfg, run)
    report, units, mapping = load_contract(out)
    if run != "full":
        raise ValueError("the fixed effect gate is computed only for the full twenty-core run")
    if len(expected) != 20 or report["unit_count"] <= 0:
        raise ValueError("full run must retain all frozen cores and reference units")
    per_core = [score_core(cfg, out, core, units, mapping) for core in expected]
    totals = {mode: Counter() for mode in cfg["modes"]}
    correct = {mode: set() for mode in cfg["modes"]}
    unmatched = {mode: set() for mode in cfg["modes"]}
    for core, cell in zip(expected, per_core):
        for mode, values in cell["modes"].items():
            totals[mode].update(values["metric"])
            correct[mode].update((core.key, unit) for unit in values["correct"])
            unmatched[mode].update((core.key, chain.strand, chain.intervals) for chain in values["unmatched"])
    summary = {mode: metrics(**totals[mode]) for mode in cfg["modes"]}
    comparisons = {}
    for left, right in (("P", "U"), ("R", "U"), ("P", "R")):
        delta = summary[left]["f1"] - summary[right]["f1"]
        comparisons[f"{left}_minus_{right}"] = {"locus_f1_delta": delta,
            "recall_delta": summary[left]["recall"] - summary[right]["recall"],
            "gained_units": sorted(correct[left]-correct[right]),
            "lost_units": sorted(correct[right]-correct[left]),
            "new_unmatched": sorted(unmatched[left]-unmatched[right]),
            "bootstrap": bootstrap(per_core, left, right, cfg)}
    p_u = comparisons["P_minus_U"]
    lost_fraction = len(p_u["lost_units"]) / len(correct["U"]) if correct["U"] else None
    gate = (p_u["locus_f1_delta"] >= cfg["score"]["min_absolute_locus_f1_delta"] and
            p_u["bootstrap"]["ci95"][0] > cfg["score"]["min_bootstrap_ci95_lower"] and
            p_u["recall_delta"] >= cfg["score"]["min_recall_delta"] and
            lost_fraction is not None and lost_fraction <= cfg["score"]["max_lost_u_correct_fraction"])
    result = {"experiment_id": cfg["experiment_id"], "status": "COMPLETED",
              "decision": "P3_BASE_MASK_UTILITY_SUPPORT" if gate else "P3_BASE_MASK_UTILITY_GATE_NOT_MET",
              "scope": "fixed P3-R1 and fixed Tiberius on predeclared chr16/18 panel; not generalization evidence",
              "claim_eligible": False, "primary_comparison": "P_minus_U",
              "reference_unit_count": report["unit_count"], "core_count": len(expected),
              "completed_cells": len(expected)*len(cfg["modes"]), "metrics": summary,
              "comparisons": comparisons, "lost_u_correct_fraction": lost_fraction,
              "gate": {**cfg["score"], "passed": gate},
              "per_core": [{"core": core.key, "metrics": {mode: cell["modes"][mode]["metric"] for mode in cfg["modes"]}}
                           for core, cell in zip(expected, per_core)],
              "model_predictions_read": True, "sealed_labels_read": False}
    write_json(out / "result.json", result)
    print(json.dumps({"decision": result["decision"], "P_minus_U": p_u, "gate_passed": gate}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "run-core", "preflight-core", "score"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run", choices=["smoke", "full"], required=True)
    parser.add_argument("--revision", choices=["r1", "r2"], default="r1")
    parser.add_argument("--core")
    args = parser.parse_args()
    cfg = load_cfg(args.config)
    if args.action == "prepare":
        prepare(cfg, args.run, args.revision)
    elif args.action == "run-core":
        if args.core is None:
            parser.error("run-core requires --core")
        run_core(cfg, args.run, args.core, args.revision)
    elif args.action == "preflight-core":
        if args.core is None:
            parser.error("preflight-core requires --core")
        preflight_core(cfg, args.run, args.core, args.revision)
    else:
        score(cfg, args.run, args.revision)


if __name__ == "__main__":
    main()
