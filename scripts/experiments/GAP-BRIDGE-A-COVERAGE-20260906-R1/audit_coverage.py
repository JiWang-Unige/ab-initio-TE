#!/usr/bin/env python3
"""CPU tokenizer geometry audit; no checkpoint loading, inference, or target use."""
from __future__ import annotations

import argparse
import ast
import csv
import gzip
import importlib.util
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ALLOWED = {"chr3": {"TRAIN"}, "chr5": {"TRAIN"},
           "chr13": {"DEV", "CAL_FIT", "CAL_GATE"}}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


pair = module(ROOT / "scripts/experiments/GAP-BRIDGE-P3-NT-R2/prepare_pair.py", "coverage_pair")


def source_function(path, name, namespace):
    """Execute production function source, without importing/loading its models."""
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


def native_runtime(model_dir):
    import torch
    from transformers import AutoTokenizer
    torch.set_num_threads(1)
    metadata = json.loads((model_dir / "training_meta.json").read_text())
    if metadata["kind"] != "auto_token" or metadata["token_label_mode"] != "nt_kmer":
        raise ValueError("audit is grounded only for frozen NT auto_token/nt_kmer")
    best = model_dir / "best_model"
    tokenizer_path = str(best) if (best / "tokenizer_config.json").exists() else metadata["model_path"]
    loader = source_function(ROOT / "pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py",
                             "load_tokenizer", {"os": os, "AutoTokenizer": AutoTokenizer})
    tokenizer = loader(tokenizer_path)
    infer = source_function(ROOT / "pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py",
                            "infer_probs_for_label_mode", {"torch": torch, "np": np})

    def shape_only(**inputs):
        # Auto token classification preserves the encoded token axis. This is
        # a geometry sentinel, not a neural forward or predicted probability.
        return SimpleNamespace(logits=torch.zeros((*inputs["input_ids"].shape, 2)))

    return SimpleNamespace(infer_probs_for_label_mode=infer), shape_only, tokenizer, {
        "tokenizer_path": tokenizer_path, "tokenizer_class": type(tokenizer).__name__,
        "token_label_mode": metadata["token_label_mode"], "kind": metadata["kind"],
        "model_loaded": False, "neural_forward_executed": False,
        "geometry_assumption": "frozen auto_token classifier preserves encoded token axis; does not validate future model runtime",
        "branch_limit": "tokenization/projection branches only; a real model-forward exception could trigger strict fallback and is not tested by this audit"}


def audit_window(strict, shape_only, tokenizer, sequence):
    _, coverage = pair.native_nt_window(strict, shape_only, tokenizer, sequence, "cpu", "nt_kmer")
    return coverage


def candidate_rows(path):
    """Read coordinates and descriptive known/stratum only, not target values."""
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            seqid, role = row["seqid"], row["role"]
            if seqid not in ALLOWED:
                # Sealed rows are never selected; no region file is opened.
                continue
            if role not in ALLOWED[seqid]:
                raise ValueError(f"unexpected role in allowed chromosome: {seqid}/{role}")
            start, end = int(row["gap_start"]), int(row["gap_end"])
            crop_start, crop_end = int(row["crop_start"]), int(row["crop_end"])
            if not 1 <= end-start <= 512 or (crop_start, crop_end) != (start-256, end+256) or crop_start < 0:
                raise ValueError(f"not original complete-gap crop: {row['candidate_id']}")
            yield {"candidate_id": row["candidate_id"], "seqid": seqid, "role": role,
                   "block": row["chr13_block_index"], "gap_start": start, "gap_end": end,
                   "crop_start": crop_start, "crop_end": crop_end,
                   "length_stratum": row["length_stratum"], "known": row["comparator_known"],
                   "seam": str(int(crop_start // 4096 != (crop_end-1) // 4096))}


def intervals(mask, offset=0):
    edges = np.diff(np.r_[False, mask, False].astype(np.int8))
    return [(int(s)+offset, int(e)+offset) for s, e in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1))]


def status(covered, length):
    return "full" if covered == length else "uncovered" if covered == 0 else "partial"


def summarize_candidate(row, tracks):
    first = row["crop_start"] // 4096 * 4096
    last = (row["crop_end"]-1) // 4096 * 4096
    track = np.concatenate([tracks[s] for s in range(first, last+1, 4096)])
    crop = track[row["crop_start"]-first:row["crop_end"]-first]
    if len(crop) != row["crop_end"]-row["crop_start"]:
        raise ValueError("candidate extends beyond real sequence")
    gap = crop[256:256+row["gap_end"]-row["gap_start"]]
    result = {}
    for label, values in (("gap", gap), ("crop", crop)):
        count = int(values.sum())
        result.update({label+"_bp": len(values), label+"_covered_bp": count,
                       label+"_missing_bp": len(values)-count,
                       label+"_status": status(count, len(values))})
    return result


def add_counts(counter, result):
    counter["candidates"] += 1
    for label in ("gap", "crop"):
        counter[label+"_"+result[label+"_status"]+"_candidates"] += 1
        for suffix in ("bp", "covered_bp", "missing_bp"):
            counter[label+"_"+suffix] += result[label+"_"+suffix]


def run(args):
    started = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    strict, shape_only, tokenizer, identity = native_runtime(args.nt_model)
    candidates = defaultdict(list)
    for row in candidate_rows(args.candidate_manifest):
        candidates[row["seqid"]].append(row)
    if set(candidates) != set(ALLOWED):
        raise ValueError("missing original candidate chromosome population")
    aggregate, by_stratum, blocks = Counter(), defaultdict(Counter), defaultdict(Counter)
    window_totals, window_by_chrom = Counter(), defaultdict(Counter)
    sentinel = {}
    for name, sequence in (("all_acgt", "ACGT"*1024), ("leading_800_N", "N"*800+"A"*3296)):
        covered = audit_window(strict, shape_only, tokenizer, sequence)
        sentinel[name] = {"length_bp": len(covered), "covered_bp": int(covered.sum()),
                          "missing_intervals": intervals(~covered)}
    if sentinel["all_acgt"]["covered_bp"] != 4096 or sentinel["leading_800_N"]["covered_bp"] >= 4096:
        raise ValueError("native tokenizer sentinel differs from frozen expected geometry")
    with gzip.open(args.output / "uncovered_windows.tsv.gz", "wt") as window_out, gzip.open(args.output / "partial_candidates.tsv.gz", "wt") as candidate_out:
        window_writer = csv.writer(window_out, delimiter="\t")
        window_writer.writerow(["seqid", "window_start", "window_end", "covered_bp", "missing_intervals_0based_halfopen"])
        candidate_writer = csv.writer(candidate_out, delimiter="\t")
        fields = ["candidate_id", "seqid", "role", "block", "known", "length_stratum", "seam", "gap_start", "gap_end", "crop_start", "crop_end"]
        result_fields = [label+suffix for label in ("gap", "crop") for suffix in ("_bp", "_covered_bp", "_missing_bp", "_status")]
        candidate_writer.writerow(fields+result_fields)
        for seqid in ALLOWED:
            rows = candidates.pop(seqid)
            needed = {s for row in rows for s in range(row["crop_start"]//4096*4096, (row["crop_end"]-1)//4096*4096+1, 4096)}
            tracks = {}
            region_path = args.region_root / seqid / "region.jsonl.gz"
            for start, end, sequence in pair.selected_regions(region_path, seqid, {s//8192*8192 for s in needed}):
                for offset in range(0, len(sequence), 4096):
                    coordinate = start+offset
                    if coordinate not in needed:
                        continue
                    coverage = audit_window(strict, shape_only, tokenizer, sequence[offset:offset+4096])
                    tracks[coordinate] = coverage
                    counts = {"windows": 1, "real_bp": len(coverage), "covered_bp": int(coverage.sum()), "missing_bp": int((~coverage).sum()), status(int(coverage.sum()), len(coverage))+"_windows": 1}
                    window_totals.update(counts)
                    window_by_chrom[seqid].update(counts)
                    if not coverage.all():
                        window_writer.writerow([seqid, coordinate, coordinate+len(coverage), int(coverage.sum()), json.dumps(intervals(~coverage, coordinate))])
            if set(tracks) != needed:
                raise ValueError(f"missing required native windows: {seqid}")
            for row in rows:
                result = summarize_candidate(row, tracks)
                add_counts(aggregate, result)
                key = tuple(row[field] for field in ("seqid", "role", "length_stratum", "seam", "known"))
                add_counts(by_stratum[key], result)
                add_counts(blocks[(seqid, row["role"], row["block"])], result)
                if result["crop_missing_bp"]:
                    candidate_writer.writerow([row[f] for f in fields]+[result[f] for f in result_fields])
            print(json.dumps({"seqid": seqid, "candidates": len(rows), "native_windows": len(tracks), "elapsed_seconds": time.monotonic()-started}), flush=True)
    report = {"experiment_id": "GAP-BRIDGE-A-COVERAGE-20260906-R1", "status": "COMPLETED",
              "primary_metric": 1.0, "primary_metric_name": "engineering_audit_completed",
              "scientific_claim": False, "scientific_pass": False, "training_authorized": False,
              "inputs": {"candidate_manifest": str(args.candidate_manifest), "region_root": str(args.region_root), "nt_model": str(args.nt_model)},
              "scope": {k: sorted(v) for k, v in ALLOWED.items()}, "tokenizer": identity,
              "sentinels": sentinel, "candidate_totals": dict(aggregate),
              "required_native_window_totals": dict(window_totals),
              "required_native_windows_by_chromosome": {k: dict(v) for k,v in window_by_chrom.items()},
              "strata": [{**dict(zip(("seqid", "role", "length_stratum", "crop_crosses_seam", "comparator_known"), key)), **dict(value)} for key,value in sorted(by_stratum.items())],
              "candidate_blocks": [{**dict(zip(("seqid", "role", "block"), key)), **dict(value)} for key,value in sorted(blocks.items())],
              "bp_denominator_note": "candidate gap/crop bp are occurrence-weighted (overlapping crops repeat bp); native window bp are unique within chromosome",
              "boundary": "coverage only; missing positions are not zero-probability evidence; no candidates filtered, donor decisions, inference, fit, cache rebuild, or sealed-region access",
              "next_decision": "any crop missing coverage blocks the unchanged all-candidate A input contract; do not silently filter or retokenize",
              "elapsed_seconds": time.monotonic()-started}
    (args.output / "coverage_audit.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--region-root", type=Path, required=True)
    parser.add_argument("--nt-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
