#!/usr/bin/env python3
"""Evaluate the frozen Stage 1 gap-risk arms on chr13.

This runner joins the label-independent manifest and raw Stage 1 scores only
after the score file is complete.  CAL-FIT fits the only calibrator; DEV is
the mechanism set and CAL-GATE is the one-use action-lock set.  Whole-mask
endpoints are rebuilt with the existing Stage 0 interval code so a selected
gap is never treated as an automatic one-fragment improvement.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SEQID = "chr13"
ROLES = ("DEV", "CAL_FIT", "CAL_GATE")
ARMS = ("G_GEOMETRY_LOGITS", "R_RAW_LOCAL", "H_P3_LATENT")
SEEDS = (17, 42, 20260902)
WINDOW = 8192
BLOCK_SIZE = 1_000_000
MECHANISM_BUDGET = 1e-5
UNKNOWN_BUDGET = 20.0
HEAD_COLUMNS = tuple(
    f"{arm}__seed{seed}__raw_risk_logit" for arm in ARMS for seed in SEEDS
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage0 = _load_module(HERE / "stage0_oracle.py", "gap_bridge_stage1_eval_stage0")
metrics = _load_module(HERE / "stage1_metrics.py", "gap_bridge_stage1_eval_metrics")


@dataclass(frozen=True)
class EvalCandidate:
    candidate_id: str
    role: str
    block_index: int
    base: object
    relation: str
    positive_bp: int
    negative_bp: int
    unknown_bp: int

    @property
    def length(self) -> int:
        return self.base.gap_end - self.base.gap_start

    @property
    def target(self) -> float:
        return self.negative_bp / self.length

    @property
    def stratum(self) -> str:
        return stage0.length_stratum(self.length)

    @property
    def seam(self) -> bool:
        crop_start = self.base.gap_start - 256
        crop_end = self.base.gap_end + 256
        return crop_start // WINDOW != (crop_end - 1) // WINDOW

    @property
    def midpoint(self) -> float:
        return (self.base.gap_start + self.base.gap_end) / 2.0


def _int(row: dict[str, str], field: str) -> int:
    value = int(row[field])
    if value < 0:
        raise ValueError(f"{field} is negative: {row.get('candidate_id', '')}")
    return value


def read_manifest(path: Path) -> dict[str, EvalCandidate]:
    required = {
        "candidate_id", "seqid", "role", "chr13_block_index", "left_run_start",
        "left_run_end", "gap_start", "gap_end", "right_run_start", "right_run_end",
        "crop_start", "crop_end", "gap_length", "length_stratum", "comparator_known",
        "positive_bp", "negative_bp", "unknown_bp", "comparator_relation",
        "target_negative_fraction",
    }
    result: dict[str, EvalCandidate] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("candidate manifest lacks frozen Stage 1 evaluation fields")
        for row in reader:
            if row["seqid"] != SEQID or row["role"] not in ROLES:
                continue
            candidate_id = row["candidate_id"]
            if candidate_id in result:
                raise ValueError(f"duplicate candidate in manifest: {candidate_id}")
            block_text = row["chr13_block_index"].strip()
            if not block_text:
                raise ValueError(f"CAL/DEV candidate has no block index: {candidate_id}")
            left_start, left_end = _int(row, "left_run_start"), _int(row, "left_run_end")
            gap_start, gap_end = _int(row, "gap_start"), _int(row, "gap_end")
            right_start, right_end = _int(row, "right_run_start"), _int(row, "right_run_end")
            crop_start, crop_end = _int(row, "crop_start"), _int(row, "crop_end")
            gap_length = _int(row, "gap_length")
            if gap_end <= gap_start or gap_end - gap_start != gap_length or gap_length > 512:
                raise ValueError(f"invalid candidate gap geometry: {candidate_id}")
            if left_end != gap_start or right_start != gap_end:
                raise ValueError(f"candidate runs do not abut gap: {candidate_id}")
            if left_end <= left_start or right_end <= right_start:
                raise ValueError(f"candidate flank is empty: {candidate_id}")
            if crop_start != gap_start - 256 or crop_end != gap_end + 256:
                raise ValueError(f"candidate crop disagrees with gap: {candidate_id}")
            if row["length_stratum"] != stage0.length_stratum(gap_length):
                raise ValueError(f"candidate stratum disagrees with gap: {candidate_id}")
            positive, negative, unknown = (_int(row, field) for field in ("positive_bp", "negative_bp", "unknown_bp"))
            if positive + negative + unknown != gap_length:
                raise ValueError(f"candidate label masses do not sum to gap: {candidate_id}")
            known = row["comparator_known"] == "1"
            if known and unknown:
                raise ValueError(f"known candidate has unknown bp: {candidate_id}")
            target = row["target_negative_fraction"].strip()
            if known and (not target or not math.isclose(float(target), negative / gap_length, rel_tol=0.0, abs_tol=1e-12)):
                raise ValueError(f"candidate target disagrees with label: {candidate_id}")
            base = stage0.BaseCandidate(
                candidate_id, SEQID, left_start, left_end, gap_start, gap_end,
                right_start, right_end,
            )
            result[candidate_id] = EvalCandidate(
                candidate_id, row["role"], int(block_text), base, row["comparator_relation"],
                positive, negative, unknown,
            )
    if not result:
        raise ValueError("manifest contains no chr13 DEV/CAL candidates")
    return result


def read_scores(path: Path, candidates: dict[str, EvalCandidate]) -> dict[str, dict[str, float]]:
    required = {"candidate_id", "seqid", "role", "gap_start", "gap_end", "gap_length", "length_stratum", *HEAD_COLUMNS}
    result: dict[str, dict[str, float]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("raw score file lacks frozen head columns")
        for row in reader:
            candidate_id = row["candidate_id"]
            candidate = candidates.get(candidate_id)
            if candidate is None:
                raise ValueError(f"score row not in manifest: {candidate_id}")
            if row["seqid"] != SEQID or row["role"] != candidate.role:
                raise ValueError(f"score geometry role mismatch: {candidate_id}")
            if int(row["gap_start"]) != candidate.base.gap_start or int(row["gap_end"]) != candidate.base.gap_end:
                raise ValueError(f"score geometry mismatch: {candidate_id}")
            if int(row["gap_length"]) != candidate.length or row["length_stratum"] != candidate.stratum:
                raise ValueError(f"score length mismatch: {candidate_id}")
            if candidate_id in result:
                raise ValueError(f"duplicate score row: {candidate_id}")
            values = {column: float(row[column]) for column in HEAD_COLUMNS}
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError(f"non-finite raw score: {candidate_id}")
            result[candidate_id] = values
    if set(result) != set(candidates):
        missing = sorted(set(candidates) - set(result))
        extra = sorted(set(result) - set(candidates))
        raise ValueError(f"raw score denominator mismatch: missing={missing[:3]} extra={extra[:3]}")
    return result


def read_purge(path: Path, candidates: dict[str, EvalCandidate]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    required = {"candidate_id", "seqid", "purged"}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("homology purge output lacks required fields")
        for row in reader:
            cid = row["candidate_id"]
            if cid not in candidates or candidates[cid].role != "DEV":
                raise ValueError(f"purge row is not a DEV candidate: {cid}")
            if cid in result:
                raise ValueError(f"duplicate purge row: {cid}")
            result[cid] = row["purged"] == "1"
    dev_ids = {cid for cid, candidate in candidates.items() if candidate.role == "DEV"}
    if set(result) != dev_ids:
        raise ValueError("homology purge denominator does not equal DEV manifest")
    return result


def read_family(path: Path, candidates: dict[str, EvalCandidate]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    required = {"candidate_id", "seqid", "role", "status", "family_stratum"}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("family projection lacks required fields")
        for row in reader:
            cid = row["candidate_id"]
            if cid not in candidates:
                raise ValueError(f"family row not in manifest: {cid}")
            if row["seqid"] != SEQID or row["role"] != candidates[cid].role:
                raise ValueError(f"family row role mismatch: {cid}")
            if cid in result:
                raise ValueError(f"duplicate family row: {cid}")
            result[cid] = {"status": row["status"], "family_stratum": row["family_stratum"]}
    if set(result) != set(candidates):
        raise ValueError("family projection denominator differs from scored candidates")
    return result


def role_regions(sequence: str, role: str) -> list[tuple[int, int]]:
    _role_by_block, manifest = stage0.chr13_split(len(sequence))
    return [
        (int(row["start"]), int(row["end"]))
        for row in manifest if row["role"] == role
    ]


def build_role_data(
    sequence: str,
    positive_intervals: list[tuple[int, int]],
    unknown_intervals: list[tuple[int, int]],
    raw_mask_intervals: list[tuple[int, int]],
    candidates: dict[str, EvalCandidate],
    role: str,
) -> object:
    regions = role_regions(sequence, role)
    all_acgt = stage0.acgt_runs(sequence)
    genome_callable = stage0.intersect_intervals(all_acgt, regions)
    positive = stage0.intersect_intervals(positive_intervals, regions)
    unknown = stage0.intersect_intervals(stage0.subtract_intervals(unknown_intervals, positive_intervals), regions)
    callable_regions = stage0.subtract_intervals(genome_callable, unknown)
    raw_mask = stage0.intersect_intervals(raw_mask_intervals, regions)
    role_candidates = [candidate for candidate in candidates.values() if candidate.role == role]
    return stage0.ChromData(
        SEQID, len(sequence), regions, genome_callable, callable_regions,
        positive, unknown, raw_mask,
        [stage0.Candidate(candidate.base, candidate.relation, candidate.positive_bp, candidate.negative_bp, candidate.unknown_bp) for candidate in role_candidates],
    )


def _interval_metrics(truth: tuple[int, int], components: Iterable[tuple[int, int]]) -> dict[str, int]:
    covered = sorted(
        (max(start, truth[0]), min(end, truth[1]))
        for start, end in components if start < truth[1] and end > truth[0]
    )
    covered = [(start, end) for start, end in covered if start < end]
    if not covered:
        return {
            "truth_runs": 1, "truth_bp": truth[1] - truth[0], "fragments": 0,
            "missed_truth_runs": 1, "split_truth_runs": 0,
            "left_terminal_omission_truth_runs": 1, "right_terminal_omission_truth_runs": 1,
            "terminal_omission_truth_runs": 1, "terminal_omitted_bp": truth[1] - truth[0],
            "internal_gap_count": 0, "internal_gap_bp": 0,
        }
    left = covered[0][0] > truth[0]
    right = covered[-1][1] < truth[1]
    internal = [(prev[1], cur[0]) for prev, cur in zip(covered, covered[1:]) if prev[1] < cur[0]]
    return {
        "truth_runs": 1, "truth_bp": truth[1] - truth[0], "fragments": len(covered),
        "missed_truth_runs": 0, "split_truth_runs": int(len(covered) >= 2),
        "left_terminal_omission_truth_runs": int(left), "right_terminal_omission_truth_runs": int(right),
        "terminal_omission_truth_runs": int(left or right),
        "terminal_omitted_bp": (covered[0][0] - truth[0] if left else 0) + (truth[1] - covered[-1][1] if right else 0),
        "internal_gap_count": len(internal), "internal_gap_bp": sum(end - start for start, end in internal),
    }


class FragmentState:
    """Exact truth-run fragmentation state under complete candidate fills."""

    def __init__(self, raw_mask: list[tuple[int, int]], truth: list[tuple[int, int]], candidates: Iterable[EvalCandidate]):
        self.runs = stage0.merge_intervals(raw_mask)
        self.truth = stage0.merge_intervals(truth)
        self.parent = list(range(len(self.runs)))
        self.start = [start for start, _end in self.runs]
        self.end = [end for _start, end in self.runs]
        self.truth_to_roots = [set() for _ in self.truth]
        self.root_to_truth = [set() for _ in self.runs]
        truth_starts = [start for start, _end in self.truth]

        def overlapping_truth(start: int, end: int) -> set[int]:
            if not self.truth:
                return set()
            index = max(0, bisect.bisect_right(truth_starts, start) - 1)
            result: set[int] = set()
            while index < len(self.truth) and self.truth[index][0] < end:
                if self.truth[index][1] > start:
                    result.add(index)
                index += 1
            return result

        for root, (start, end) in enumerate(self.runs):
            for index in overlapping_truth(start, end):
                self.truth_to_roots[index].add(root)
                self.root_to_truth[root].add(index)
        self.gap_runs: dict[str, tuple[int, int]] = {}
        self.gap_truth: dict[str, set[int]] = {}
        by_end = {end: index for index, (_start, end) in enumerate(self.runs)}
        by_start = {start: index for index, (start, _end) in enumerate(self.runs)}
        for candidate in candidates:
            left = by_end.get(candidate.base.gap_start)
            right = by_start.get(candidate.base.gap_end)
            if left is None or right is None:
                raise ValueError(f"candidate does not join raw P3 runs: {candidate.candidate_id}")
            self.gap_runs[candidate.candidate_id] = (left, right)
            self.gap_truth[candidate.candidate_id] = overlapping_truth(
                candidate.base.gap_start, candidate.base.gap_end,
            )
        self.values = [self._value(index) for index in range(len(self.truth))]
        self.totals = self._sum_values(self.values)

    def find(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    @staticmethod
    def _sum_values(values: Iterable[dict[str, int]]) -> dict[str, int]:
        keys = (
            "truth_runs", "truth_bp", "fragments", "missed_truth_runs", "split_truth_runs",
            "left_terminal_omission_truth_runs", "right_terminal_omission_truth_runs",
            "terminal_omission_truth_runs", "terminal_omitted_bp", "internal_gap_count", "internal_gap_bp",
        )
        return {key: sum(item[key] for item in values) for key in keys}

    def _value(self, index: int) -> dict[str, int]:
        components = []
        for root in self.truth_to_roots[index]:
            root = self.find(root)
            components.append((self.start[root], self.end[root]))
        return _interval_metrics(self.truth[index], components)

    def add(self, candidate: EvalCandidate) -> None:
        left_index, right_index = self.gap_runs[candidate.candidate_id]
        left, right = self.find(left_index), self.find(right_index)
        if left == right:
            return
        affected = set(self.root_to_truth[left]) | set(self.root_to_truth[right]) | self.gap_truth[candidate.candidate_id]
        for index in affected:
            old = self.values[index]
            for key, value in old.items():
                self.totals[key] -= value
        if len(self.root_to_truth[left]) < len(self.root_to_truth[right]):
            left, right = right, left
        self.parent[right] = left
        self.start[left] = min(self.start[left], self.start[right])
        self.end[left] = max(self.end[left], self.end[right])
        merged_truth = self.root_to_truth[left] | self.root_to_truth[right]
        for index in merged_truth:
            self.truth_to_roots[index].discard(right)
            self.truth_to_roots[index].add(left)
        for index in self.gap_truth[candidate.candidate_id]:
            self.truth_to_roots[index].add(left)
        self.root_to_truth[left] = merged_truth | self.gap_truth[candidate.candidate_id]
        self.root_to_truth[right] = set()
        for index in affected:
            self.values[index] = self._value(index)
            for key, value in self.values[index].items():
                self.totals[key] += value

    def summary(self) -> dict[str, int | float | None]:
        truth_count, truth_bp = self.totals["truth_runs"], self.totals["truth_bp"]
        return {
            **self.totals,
            "fragments_per_truth": self.totals["fragments"] / truth_count if truth_count else None,
            "missed_rate": self.totals["missed_truth_runs"] / truth_count if truth_count else None,
            "split_rate": self.totals["split_truth_runs"] / truth_count if truth_count else None,
            "terminal_omission_rate": self.totals["terminal_omission_truth_runs"] / truth_count if truth_count else None,
            "terminal_omitted_bp_rate": self.totals["terminal_omitted_bp"] / truth_bp if truth_bp else None,
        }


class PolicyState:
    """Incrementally exact whole-mask and fragmentation endpoints."""

    def __init__(self, data: object, candidates: list[EvalCandidate]):
        self.data = data
        self.candidates = {candidate.candidate_id: candidate for candidate in candidates}
        self.selected: set[str] = set()
        self.selected_gap_bp = 0
        self.selected_positive = self.selected_negative = self.selected_unknown = 0
        self.selected_long_positive = 0
        self.positive_denominator = sum(candidate.positive_bp for candidate in candidates if candidate.unknown_bp == 0)
        self.long_positive_denominator = sum(candidate.positive_bp for candidate in candidates if candidate.unknown_bp == 0 and candidate.length > 5)
        self.known_universe = sum(candidate.unknown_bp == 0 for candidate in candidates)
        self.genome_callable_bp = stage0.interval_bp(data.genome_callable_regions)
        self.raw_whole = stage0.mask_counts(data.raw_mask, data.positive, data.callable_regions)
        self.truth = stage0.intersect_intervals(data.positive, data.callable_regions)
        self.raw_fragments = FragmentState(data.raw_mask, self.truth, candidates)
        self.raw_fragment_summary = dict(self.raw_fragments.summary())
        self.short = stage0.ShortUnion(self.raw_fragments.runs)
        self.raw_short_rate = self.short.short / self.short.components if self.short.components else None
        self.refined_whole = dict(self.raw_whole)

    @staticmethod
    def _confusion(raw: dict[str, int | float | None], positive: int, negative: int) -> dict[str, int | float | None]:
        result = dict(raw)
        result["predicted_bp"] = int(raw["predicted_bp"]) + positive + negative
        result["true_positive_bp"] = int(raw["true_positive_bp"]) + positive
        result["false_positive_bp"] = int(raw["false_positive_bp"]) + negative
        result["false_negative_bp"] = int(raw["false_negative_bp"]) - positive
        result["true_negative_bp"] = int(raw["true_negative_bp"]) - negative
        tp, fp = int(result["true_positive_bp"]), int(result["false_positive_bp"])
        fn, tn = int(result["false_negative_bp"]), int(result["true_negative_bp"])
        result["precision"] = tp / (tp + fp) if tp + fp else None
        result["recall"] = tp / (tp + fn) if tp + fn else None
        result["f1"] = 2 * result["precision"] * result["recall"] / (result["precision"] + result["recall"]) if result["precision"] and result["recall"] else None
        denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        result["mcc"] = (tp * tn - fp * fn) / denominator if denominator else None
        return result

    def add(self, candidate: EvalCandidate) -> None:
        if candidate.candidate_id in self.selected:
            return
        self.selected.add(candidate.candidate_id)
        self.selected_gap_bp += candidate.length
        self.selected_positive += candidate.positive_bp
        self.selected_negative += candidate.negative_bp
        self.selected_unknown += candidate.unknown_bp
        if candidate.length > 5:
            self.selected_long_positive += candidate.positive_bp
        self.refined_whole = self._confusion(self.raw_whole, self.selected_positive, self.selected_negative)
        self.raw_fragments.add(candidate)
        self.short.add_gap(stage0.Candidate(candidate.base, candidate.relation, candidate.positive_bp, candidate.negative_bp, candidate.unknown_bp))

    def summary(self) -> dict[str, object]:
        fragment = self.raw_fragments.summary()
        short_rate = self.short.short / self.short.components if self.short.components else None
        return {
            "selected_candidates": len(self.selected),
            "selected_gap_bp": self.selected_gap_bp,
            "selected_positive_bp": self.selected_positive,
            "selected_negative_bp": self.selected_negative,
            "selected_unknown_bp": self.selected_unknown,
            "whole_mask": {"raw": self.raw_whole, "refined": self.refined_whole},
            "fragmentation": {"raw": self.raw_fragment_summary, "refined": fragment},
            "short_predictions": {
                "raw": {"predicted_runs": len(self.raw_fragments.runs), "short_predicted_runs": sum(end - start < stage0.SHORT_BP for start, end in self.raw_fragments.runs), "short_rate": self.raw_short_rate},
                "refined": {"predicted_runs": self.short.components, "short_predicted_runs": self.short.short, "short_rate": short_rate},
            },
        }


def relative_decrease(before: float | None, after: float | None) -> float | None:
    if before is None or after is None or before == 0:
        return None
    return (before - after) / before


def worst_case_data(data: object) -> object:
    return replace(data, unknown=[], candidates=[
        replace(candidate, negative_bp=candidate.negative_bp + candidate.unknown_bp, unknown_bp=0)
        for candidate in data.candidates
    ])


def _non_gene_gates(state: PolicyState) -> dict[str, bool]:
    raw_whole, refined_whole = state.raw_whole, state.refined_whole
    raw_fragment, refined_fragment = state.raw_fragment_summary, state.raw_fragments.summary()
    split = relative_decrease(raw_fragment["split_rate"], refined_fragment["split_rate"])
    fragment = relative_decrease(raw_fragment["fragments_per_truth"], refined_fragment["fragments_per_truth"])
    minimum = max(1000, math.ceil(0.01 * state.known_universe))
    return {
        "selected_candidate_minimum": len(state.selected) >= minimum,
        "known_negative_bp_per_mb": state.selected_negative * 1_000_000 / state.genome_callable_bp <= 10,
        "whole_mask_precision_drop": refined_whole["precision"] is not None and raw_whole["precision"] is not None and refined_whole["precision"] >= raw_whole["precision"] - 0.001,
        "whole_mask_f1_non_decrease": refined_whole["f1"] is not None and raw_whole["f1"] is not None and refined_whole["f1"] >= raw_whole["f1"],
        "whole_mask_recall_non_decrease": refined_whole["recall"] is not None and raw_whole["recall"] is not None and refined_whole["recall"] >= raw_whole["recall"],
        "split_rate_relative_decrease": split is not None and split >= 0.10,
        "fragments_per_truth_relative_decrease": fragment is not None and fragment >= 0.10,
        "short_rate_non_increase": state.raw_short_rate is not None and state.short.short / state.short.components <= state.raw_short_rate,
        "positive_gap_bp_recovery": state.positive_denominator > 0 and state.selected_positive / state.positive_denominator >= 0.10,
        "positive_gap_gt5_bp_recovery": state.long_positive_denominator > 0 and state.selected_long_positive / state.long_positive_denominator >= 0.05,
    }


def action_gate(state: PolicyState, transcripts: dict[str, list[dict[str, object]]]) -> tuple[dict[str, bool], dict[str, object]]:
    gates = cheap_action_gates(state)
    ids = state.selected
    safety = stage0.gene_safety([worst_case_data(state.data)], ids, transcripts)
    gates.update(safety["gates"])
    return gates, safety


def cheap_action_gates(state: PolicyState) -> dict[str, bool]:
    gates = _non_gene_gates(state)
    worst = state.selected_negative + state.selected_unknown
    gates["worst_case_negative_or_unknown_bp_per_mb"] = worst * 1_000_000 / state.genome_callable_bp <= UNKNOWN_BUDGET
    return gates


def metrics_bundle(
    rows: list[EvalCandidate],
    raw: dict[str, dict[str, float]],
    calibrated: np.ndarray,
    arm: str,
) -> dict[str, object]:
    known = [candidate for candidate in rows if candidate.unknown_bp == 0]
    indices = [candidate.candidate_id for candidate in known]
    positive = np.asarray([candidate.positive_bp for candidate in known], dtype=np.float64)
    negative = np.asarray([candidate.negative_bp for candidate in known], dtype=np.float64)
    strata = [candidate.stratum for candidate in known]
    if not known:
        return {"status": "NO_KNOWN_CANDIDATES"}
    result: dict[str, object] = {"known_candidates": len(known), "known_gap_bp": int(positive.sum() + negative.sum())}
    seed_values: dict[str, object] = {}
    for seed in SEEDS:
        action = np.asarray([-raw[cid][f"{arm}__seed{seed}__raw_risk_logit"] for cid in indices], dtype=np.float64)
        seed_values[str(seed)] = metrics.weighted_action_metrics(action, positive, negative)
    result["raw_seed_action_metrics"] = seed_values
    ensemble_logits = np.asarray([np.mean([raw[cid][f"{arm}__seed{seed}__raw_risk_logit"] for seed in SEEDS]) for cid in indices], dtype=np.float64)
    result["raw_ensemble_action_metrics"] = metrics.weighted_action_metrics(-ensemble_logits, positive, negative)
    row_index = {candidate.candidate_id: index for index, candidate in enumerate(rows)}
    p = calibrated[np.asarray([row_index[candidate.candidate_id] for candidate in known], dtype=np.int64)]
    result["calibrated_risk_metrics"] = metrics.calibrated_risk_metrics(p, positive, negative, strata)
    result["calibration"] = metrics.equal_bp_mass_ece(p, positive, negative)
    return result


def optional_action_metrics(scores: np.ndarray, positive: np.ndarray, negative: np.ndarray) -> dict[str, object]:
    if positive.sum() <= 0 or negative.sum() <= 0:
        return {"status": "NOT_COMPUTED", "reason": "stratum lacks positive or negative comparator bp"}
    return metrics.weighted_action_metrics(scores, positive, negative)


def optional_risk_metrics(
    probabilities: np.ndarray,
    positive: np.ndarray,
    negative: np.ndarray,
    strata: list[str],
) -> dict[str, object]:
    if positive.sum() <= 0 or negative.sum() <= 0 or set(strata) != set(metrics.LENGTH_STRATA):
        return {"status": "NOT_COMPUTED", "reason": "stratum lacks required comparator bp or six length strata"}
    return metrics.calibrated_risk_metrics(probabilities, positive, negative, strata)


def secondary_metrics(
    rows: list[EvalCandidate],
    raw: dict[str, dict[str, float]],
    calibrated: np.ndarray,
    family: dict[str, dict[str, str]],
    arm: str,
) -> dict[str, object]:
    categories: dict[str, dict[str, list[EvalCandidate]]] = defaultdict(lambda: defaultdict(list))
    for candidate in rows:
        if candidate.unknown_bp:
            continue
        categories["length_stratum"][candidate.stratum].append(candidate)
        categories["short_group"]["L<=2" if candidate.length <= 2 else "L>5" if candidate.length > 5 else "3-5"].append(candidate)
        categories["seam"]["seam" if candidate.seam else "non_seam"].append(candidate)
        categories["flank_relation"][candidate.relation].append(candidate)
        categories["family_status"][family[candidate.candidate_id]["status"]].append(candidate)
        if family[candidate.candidate_id]["status"] == "SAME_UNIQUE":
            categories["family"][family[candidate.candidate_id]["family_stratum"]].append(candidate)
    result: dict[str, object] = {}
    order = {candidate.candidate_id: index for index, candidate in enumerate(rows)}
    for category, groups in categories.items():
        result[category] = {}
        for name, group in sorted(groups.items()):
            positive = np.asarray([candidate.positive_bp for candidate in group], dtype=np.float64)
            negative = np.asarray([candidate.negative_bp for candidate in group], dtype=np.float64)
            indices = np.asarray([order[candidate.candidate_id] for candidate in group], dtype=np.int64)
            ensemble = -np.asarray([np.mean([raw[candidate.candidate_id][f"{arm}__seed{seed}__raw_risk_logit"] for seed in SEEDS]) for candidate in group], dtype=np.float64)
            result[category][name] = {
                "candidate_count": len(group),
                "gap_bp": int(positive.sum() + negative.sum()),
                "action_metrics": optional_action_metrics(ensemble, positive, negative),
                "calibrated_risk_metrics": optional_risk_metrics(calibrated[indices], positive, negative, [candidate.stratum for candidate in group]),
            }
    return result


def block_universe(regions: list[tuple[int, int]]) -> list[str]:
    result: list[str] = []
    for start, end in regions:
        for block in range(start // BLOCK_SIZE, (end - 1) // BLOCK_SIZE + 1):
            value = f"{SEQID}:{block}"
            if value not in result:
                result.append(value)
    return result


def mechanism_comparison(
    rows: list[EvalCandidate],
    raw: dict[str, dict[str, float]],
    arm_a: str,
    arm_b: str,
    purge: dict[str, bool],
    regions: list[tuple[int, int]],
    purged: bool,
) -> dict[str, object]:
    selected = [candidate for candidate in rows if candidate.unknown_bp == 0 and (not purged or not purge[candidate.candidate_id])]
    positive = np.asarray([candidate.positive_bp for candidate in selected], dtype=np.float64)
    negative = np.asarray([candidate.negative_bp for candidate in selected], dtype=np.float64)
    scores_a = np.asarray([-np.mean([raw[candidate.candidate_id][f"{arm_a}__seed{seed}__raw_risk_logit"] for seed in SEEDS]) for candidate in selected], dtype=np.float64)
    scores_b = np.asarray([-np.mean([raw[candidate.candidate_id][f"{arm_b}__seed{seed}__raw_risk_logit"] for seed in SEEDS]) for candidate in selected], dtype=np.float64)
    blocks = [f"{SEQID}:{int(candidate.midpoint) // BLOCK_SIZE}" for candidate in selected]
    result: dict[str, object] = {
        "arm_a": arm_a, "arm_b": arm_b, "homology_purged": purged,
        "candidate_count": len(selected),
        "action_metrics_a": metrics.weighted_action_metrics(scores_a, positive, negative),
        "action_metrics_b": metrics.weighted_action_metrics(scores_b, positive, negative),
    }
    result["paired_ap_bootstrap"] = metrics.bootstrap_action_ap_difference(
        scores_a, scores_b, positive, negative, blocks, block_universe(regions), 1000, 20260902,
    )
    if purged:
        result["denominator_note"] = "same unpurged/purged candidate mask for both arms; full DEV 1-Mb block universe retained"
    return result


def mechanism_budget_result(
    rows: list[EvalCandidate],
    probabilities: np.ndarray,
    data: object,
    transcripts: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    positive = np.asarray([candidate.positive_bp for candidate in rows], dtype=np.float64)
    negative = np.asarray([candidate.negative_bp for candidate in rows], dtype=np.float64)
    unknown = np.asarray([candidate.unknown_bp for candidate in rows], dtype=np.float64)
    frontier = metrics.frozen_budget_frontier(
        probabilities, positive, negative, unknown,
        stage0.interval_bp(data.genome_callable_regions), MECHANISM_BUDGET,
    )
    selected_ids = {
        candidate.candidate_id
        for candidate, keep in zip(rows, frontier["selected_mask"])
        if keep
    }
    result: dict[str, object] = {
        key: value for key, value in frontier.items() if key != "selected_mask"
    }
    result["selected_evaluation"] = selected_policy_evaluation(
        data, rows, selected_ids, transcripts,
    ) if selected_ids else None
    return result


def _budget_utility_values(result: dict[str, object]) -> tuple[float, float]:
    evaluation = result.get("selected_evaluation")
    if not isinstance(evaluation, dict):
        return 0.0, 0.0
    state = evaluation["incremental_state"]
    fragmentation = state["fragmentation"]
    resolved_edges = (
        float(fragmentation["raw"]["internal_gap_count"])
        - float(fragmentation["refined"]["internal_gap_count"])
    )
    return float(state["selected_positive_bp"]), resolved_edges


def registered_mechanism_gate(
    novel_arm: str,
    baseline_arm: str,
    full_comparison: dict[str, object],
    purged_comparison: dict[str, object],
    dev_metrics: dict[str, object],
    budget_results: dict[str, dict[str, object]],
) -> dict[str, object]:
    novel = dev_metrics[novel_arm]
    baseline = dev_metrics[baseline_arm]
    novel_ap = float(novel["raw_ensemble_action_metrics"]["ap"])
    baseline_ap = float(baseline["raw_ensemble_action_metrics"]["ap"])
    ap_delta = novel_ap - baseline_ap
    novel_brier = float(novel["calibrated_risk_metrics"]["pseudo_base_brier"])
    baseline_brier = float(baseline["calibrated_risk_metrics"]["pseudo_base_brier"])
    brier_decrease = (baseline_brier - novel_brier) / baseline_brier
    seed_deltas = {
        str(seed): (
            float(novel["raw_seed_action_metrics"][str(seed)]["ap"])
            - float(baseline["raw_seed_action_metrics"][str(seed)]["ap"])
        )
        for seed in SEEDS
    }
    novel_positive, novel_edges = _budget_utility_values(budget_results[novel_arm])
    baseline_positive, baseline_edges = _budget_utility_values(budget_results[baseline_arm])
    utility = metrics.utility_gate(
        novel_positive, baseline_positive, novel_edges, baseline_edges,
    )
    purged_delta = (
        float(purged_comparison["action_metrics_a"]["ap"])
        - float(purged_comparison["action_metrics_b"]["ap"])
    )
    bootstrap = full_comparison["paired_ap_bootstrap"]
    gates = {
        "action_ap_delta_at_least_0.010": ap_delta >= 0.010,
        "paired_ap_lower_95_positive": float(bootstrap["lower_95"]) > 0.0,
        "pseudo_base_brier_decrease_at_least_5pct": brier_decrease >= 0.05,
        "common_budget_registered_utility": bool(utility["passed"]),
        "all_three_seed_action_ap_higher": all(delta > 0.0 for delta in seed_deltas.values()),
        "homology_purged_action_ap_delta_positive": purged_delta > 0.0,
    }
    return {
        "novel_arm": novel_arm,
        "baseline_arm": baseline_arm,
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "action_ap_delta": ap_delta,
        "paired_ap_lower_95": float(bootstrap["lower_95"]),
        "paired_ap_upper_95": float(bootstrap["upper_95"]),
        "pseudo_base_brier_relative_decrease": brier_decrease,
        "seed_action_ap_deltas": seed_deltas,
        "homology_purged_action_ap_delta": purged_delta,
        "common_budget_utility": utility,
    }


def calibration_gate(bundle: dict[str, object]) -> dict[str, object]:
    values = bundle["calibration"]
    gates = {
        "equal_bp_mass_ece_at_most_0.025": float(values["ece"]) <= 0.025,
        "citl_abs_at_most_0.01": float(values["citl_abs"]) <= 0.01,
    }
    return {"status": "PASS" if all(gates.values()) else "FAIL", "gates": gates}


def _frontier_row(state: PolicyState, threshold: float, gates: dict[str, bool]) -> dict[str, object]:
    summary = state.summary()
    refined = summary["whole_mask"]["refined"]
    fragment = summary["fragmentation"]["refined"]
    return {
        "threshold": threshold,
        "selected_candidates": len(state.selected),
        "selected_positive_bp": state.selected_positive,
        "selected_negative_bp": state.selected_negative,
        "selected_unknown_bp": state.selected_unknown,
        "worst_case_negative_or_unknown_bp_per_mb": (state.selected_negative + state.selected_unknown) * 1_000_000 / state.genome_callable_bp,
        "whole_precision": refined["precision"], "whole_recall": refined["recall"], "whole_f1": refined["f1"],
        "split_rate": fragment["split_rate"], "fragments_per_truth": fragment["fragments_per_truth"],
        "missed_rate": fragment["missed_rate"], "short_rate": summary["short_predictions"]["refined"]["short_rate"],
        "gates": gates,
        "admissible": False,
    }


def cal_gate_frontier(
    rows: list[EvalCandidate],
    p: np.ndarray,
    data: object,
    transcripts: dict[str, list[dict[str, object]]],
) -> tuple[dict[str, object], set[str] | None]:
    order = sorted(range(len(rows)), key=lambda index: (p[index], rows[index].candidate_id))
    state = PolicyState(data, rows)
    frontier: list[dict[str, object]] = []
    group_ends: list[int] = []
    keys: list[tuple[float, float, float, float] | None] = []
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and p[order[end]] == p[order[index]]:
            end += 1
        for position in order[index:end]:
            state.add(rows[position])
        gates = cheap_action_gates(state)
        row = _frontier_row(state, float(p[order[index]]), gates)
        frontier.append(row)
        group_ends.append(end)
        if all(gates.values()):
            split_reduction = relative_decrease(state.raw_fragment_summary["split_rate"], state.raw_fragments.summary()["split_rate"]) or -math.inf
            keys.append((split_reduction, -float(state.selected_negative), float(state.selected_positive), -float(p[order[index]])))
        else:
            keys.append(None)
        index = end

    # Every registered gene-safety numerator is monotone under nested whole-gap
    # filling. Locate the last passing threshold with logarithmically many exact
    # Stage 0 gene scans, then combine that boundary with each cheap gate.
    last_gene_safe = -1
    low, high = -1, len(frontier)
    gene_safety_scans = 0
    while high - low > 1:
        middle = (low + high) // 2
        ids = {rows[position].candidate_id for position in order[:group_ends[middle]]}
        safety = stage0.gene_safety([worst_case_data(data)], ids, transcripts)
        gene_safety_scans += 1
        if all(safety["gates"].values()):
            low = middle
        else:
            high = middle
    last_gene_safe = low

    selected_index: int | None = None
    best_key: tuple[float, float, float, float] | None = None
    for frontier_index, (row, key) in enumerate(zip(frontier, keys)):
        row["gene_safety_within_monotone_boundary"] = frontier_index <= last_gene_safe
        row["admissible"] = key is not None and frontier_index <= last_gene_safe
        if row["admissible"] and (best_key is None or key > best_key):
            best_key = key
            selected_index = frontier_index
    selected_ids = None if selected_index is None else {
        rows[position].candidate_id for position in order[:group_ends[selected_index]]
    }
    return {
        "status": "PASS" if selected_ids is not None else "NO_ADMISSIBLE_CAL_GATE_POINT",
        "frontier_rows": frontier,
        "selected_threshold": None,
        "selected_candidate_count": None if selected_ids is None else len(selected_ids),
        "last_gene_safe_frontier_index": last_gene_safe,
        "gene_safety_scans": gene_safety_scans,
    }, selected_ids


def selected_policy_evaluation(
    data: object,
    rows: list[EvalCandidate],
    selected_ids: set[str],
    transcripts: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    state = PolicyState(data, rows)
    for candidate in rows:
        if candidate.candidate_id in selected_ids:
            state.add(candidate)
    gates, safety = action_gate(state, transcripts)
    exact = stage0.evaluate_dataset([data], selected_ids)
    return {
        "incremental_state": state.summary(),
        "stage0_exact": exact,
        "selection_diagnostics": stage0.selection_diagnostics([data], selected_ids),
        "gates": gates,
        "gene_safety": safety,
    }


def write_frontier(path: Path, arm_frontiers: dict[str, dict[str, object]]) -> None:
    fields = ["arm", "threshold", "selected_candidates", "selected_positive_bp", "selected_negative_bp", "selected_unknown_bp", "worst_case_negative_or_unknown_bp_per_mb", "whole_precision", "whole_recall", "whole_f1", "split_rate", "fragments_per_truth", "missed_rate", "short_rate", "admissible"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for arm, result in arm_frontiers.items():
            for row in result["frontier_rows"]:
                writer.writerow({field: row.get(field, "") for field in fields} | {"arm": arm})


def evaluate(
    candidate_manifest: Path,
    raw_score: Path,
    purge_path: Path,
    family_path: Path,
    source_root: Path,
    positive_path: Path,
    unknown_path: Path,
    refgene_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    candidates_by_id = read_manifest(candidate_manifest)
    raw = read_scores(raw_score, candidates_by_id)
    purge = read_purge(purge_path, candidates_by_id)
    family = read_family(family_path, candidates_by_id)
    rows_by_role = {role: [candidate for candidate in candidates_by_id.values() if candidate.role == role] for role in ROLES}
    rows_by_role = {role: sorted(rows, key=lambda candidate: candidate.candidate_id) for role, rows in rows_by_role.items()}
    sequence = stage0.read_region_sequence(source_root / SEQID / "region.jsonl.gz", SEQID)
    positive_intervals = stage0.read_bed(positive_path, {SEQID})[SEQID]
    unknown_intervals = stage0.read_bed(unknown_path, {SEQID})[SEQID]
    raw_mask_intervals = stage0.read_bed(source_root / SEQID / "prediction.canonical.tsv", {SEQID})[SEQID]
    data_by_role = {
        role: build_role_data(
            sequence, positive_intervals, unknown_intervals,
            raw_mask_intervals, candidates_by_id, role,
        )
        for role in ROLES
    }
    transcripts = stage0.parse_refgene(refgene_path, {SEQID})
    fit: dict[str, dict[str, object]] = {}
    calibrated_by_role: dict[str, dict[str, np.ndarray]] = {}
    row_order = {role: {candidate.candidate_id: index for index, candidate in enumerate(rows_by_role[role])} for role in ROLES}
    for arm in ARMS:
        fit_rows = rows_by_role["CAL_FIT"]
        z = np.asarray([np.mean([raw[candidate.candidate_id][f"{arm}__seed{seed}__raw_risk_logit"] for seed in SEEDS]) for candidate in fit_rows if candidate.unknown_bp == 0], dtype=np.float64)
        positive = np.asarray([candidate.positive_bp for candidate in fit_rows if candidate.unknown_bp == 0], dtype=np.float64)
        negative = np.asarray([candidate.negative_bp for candidate in fit_rows if candidate.unknown_bp == 0], dtype=np.float64)
        fitted = metrics.fit_monotone_platt(z, positive, negative)
        if not fitted.get("success", False):
            raise ValueError(f"Platt calibration failed for {arm}: {fitted.get('message', '')}")
        fit[arm] = fitted
        calibrated_by_role[arm] = {}
        for role in ROLES:
            rows = rows_by_role[role]
            z_all = np.asarray([np.mean([raw[candidate.candidate_id][f"{arm}__seed{seed}__raw_risk_logit"] for seed in SEEDS]) for candidate in rows], dtype=np.float64)
            calibrated_by_role[arm][role] = metrics.apply_monotone_platt(z_all, fitted)
    role_metrics: dict[str, object] = {}
    for role in ROLES:
        role_metrics[role] = {
            arm: metrics_bundle(rows_by_role[role], raw, calibrated_by_role[arm][role], arm)
            for arm in ARMS
        }
    dev_regions = data_by_role["DEV"].eval_regions
    mechanism = {
        "R_vs_G": mechanism_comparison(rows_by_role["DEV"], raw, "R_RAW_LOCAL", "G_GEOMETRY_LOGITS", purge, dev_regions, False),
        "H_vs_R": mechanism_comparison(rows_by_role["DEV"], raw, "H_P3_LATENT", "R_RAW_LOCAL", purge, dev_regions, False),
        "R_vs_G_homology_purged": mechanism_comparison(rows_by_role["DEV"], raw, "R_RAW_LOCAL", "G_GEOMETRY_LOGITS", purge, dev_regions, True),
        "H_vs_R_homology_purged": mechanism_comparison(rows_by_role["DEV"], raw, "H_P3_LATENT", "R_RAW_LOCAL", purge, dev_regions, True),
    }
    secondary = {
        role: {arm: secondary_metrics(rows_by_role[role], raw, calibrated_by_role[arm][role], family, arm) for arm in ARMS}
        for role in ROLES
    }
    mechanism_budget = {
        arm: mechanism_budget_result(
            rows_by_role["DEV"], calibrated_by_role[arm]["DEV"],
            data_by_role["DEV"], transcripts,
        )
        for arm in ARMS
    }
    mechanism_gates = {
        "R_vs_G": registered_mechanism_gate(
            "R_RAW_LOCAL", "G_GEOMETRY_LOGITS",
            mechanism["R_vs_G"], mechanism["R_vs_G_homology_purged"],
            role_metrics["DEV"], mechanism_budget,
        ),
        "H_vs_R": registered_mechanism_gate(
            "H_P3_LATENT", "R_RAW_LOCAL",
            mechanism["H_vs_R"], mechanism["H_vs_R_homology_purged"],
            role_metrics["DEV"], mechanism_budget,
        ),
    }
    frontiers: dict[str, dict[str, object]] = {}
    selected: dict[str, set[str] | None] = {}
    for arm in ARMS:
        result, selected_ids = cal_gate_frontier(
            rows_by_role["CAL_GATE"], calibrated_by_role[arm]["CAL_GATE"],
            data_by_role["CAL_GATE"], transcripts,
        )
        # Keep the exact selected threshold by identifying the selected set's
        # maximum risk; no tie group is ever partially selected.
        if selected_ids is not None:
            selected_threshold = max(calibrated_by_role[arm]["CAL_GATE"][row_order["CAL_GATE"][cid]] for cid in selected_ids)
            result["selected_threshold"] = float(selected_threshold)
            result["selected_ids"] = sorted(selected_ids)
        frontiers[arm] = result
        selected[arm] = selected_ids
        if selected_ids is not None:
            result["selected_evaluation"] = selected_policy_evaluation(
                data_by_role["CAL_GATE"], rows_by_role["CAL_GATE"], selected_ids, transcripts,
            )
    calibration_gates = {
        arm: calibration_gate(role_metrics["CAL_GATE"][arm]) for arm in ARMS
    }
    actionable = {
        arm: frontiers[arm]["status"] == "PASS" and calibration_gates[arm]["status"] == "PASS"
        for arm in ARMS
    }
    if mechanism_gates["H_vs_R"]["status"] == "PASS" and actionable["H_P3_LATENT"]:
        selected_arm = "H_P3_LATENT"
    elif mechanism_gates["R_vs_G"]["status"] == "PASS" and actionable["R_RAW_LOCAL"]:
        selected_arm = "R_RAW_LOCAL"
    elif actionable["G_GEOMETRY_LOGITS"]:
        selected_arm = "G_GEOMETRY_LOGITS"
    else:
        selected_arm = None
    pretest_lock = {
        "status": "PASS_PRETEST_LOCK" if selected_arm is not None else "NO_ACTIONABLE_ARM",
        "selected_arm": selected_arm,
        "selected_threshold": None if selected_arm is None else frontiers[selected_arm]["selected_threshold"],
        "calibrator": None if selected_arm is None else fit[selected_arm],
        "chr19_release_authorized": selected_arm is not None,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    write_frontier(output_dir / "cal_gate_frontier.tsv", frontiers)
    with (output_dir / "cal_gate_selected.tsv").open("w", newline="", encoding="utf-8") as handle:
        fields = ("arm", "candidate_id", "risk", "selected", "positive_bp", "negative_bp", "unknown_bp")
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for arm in ARMS:
            selected_ids = selected[arm] or set()
            rows = rows_by_role["CAL_GATE"]
            p = calibrated_by_role[arm]["CAL_GATE"]
            for index, candidate in enumerate(rows):
                writer.writerow({"arm": arm, "candidate_id": candidate.candidate_id, "risk": format(float(p[index]), ".17g"), "selected": int(candidate.candidate_id in selected_ids), "positive_bp": candidate.positive_bp, "negative_bp": candidate.negative_bp, "unknown_bp": candidate.unknown_bp})
    summary: dict[str, object] = {
        "schema": "gap_bridge_neural_stage1_evaluation_v1",
        "status": "PASS",
        "protocol": "GAP_BRIDGE_NEURAL_STAGE1_R1",
        "candidate_manifest": str(candidate_manifest),
        "raw_score": str(raw_score),
        "homology_purge": str(purge_path),
        "family_projection": str(family_path),
        "calibrators": fit,
        "role_counts": {role: len(rows) for role, rows in rows_by_role.items()},
        "role_metrics": role_metrics,
        "mechanism_comparisons": mechanism,
        "mechanism_budget_1e-5": mechanism_budget,
        "mechanism_gates": mechanism_gates,
        "secondary_strata": secondary,
        "cal_gate": {arm: {key: value for key, value in result.items() if key != "frontier_rows"} for arm, result in frontiers.items()},
        "calibration_gates": calibration_gates,
        "actionable_arms": actionable,
        "pretest_lock": pretest_lock,
        "claim_boundary": "comparator-consistent secondary softmask continuity; no biological instance identity",
        "unknown_deployment_rule": "selected comparator-unknown bp counts as negative in the 1e-5 mechanism budget and 20/Mb CAL-GATE safety budget",
        "chr19_read": False,
        "chr13_sequence_bp": len(sequence),
    }
    (output_dir / "evaluation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=lambda value: value.tolist() if isinstance(value, np.ndarray) else value) + "\n", encoding="utf-8")
    (output_dir / "STATUS").write_text("PASS\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--raw-score", required=True, type=Path)
    parser.add_argument("--homology-purge", required=True, type=Path)
    parser.add_argument("--family-projection", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--comparator-positive", required=True, type=Path)
    parser.add_argument("--comparator-unknown", required=True, type=Path)
    parser.add_argument("--refgene", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = evaluate(
        args.candidate_manifest, args.raw_score, args.homology_purge,
        args.family_projection, args.source_root, args.comparator_positive,
        args.comparator_unknown, args.refgene, args.output_dir,
    )
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
