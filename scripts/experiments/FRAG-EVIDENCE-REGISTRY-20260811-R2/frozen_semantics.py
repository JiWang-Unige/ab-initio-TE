#!/usr/bin/env python3
"""Frozen comparator semantics for the Wave-1 F evidence registry.

No model loading, genome inference, evaluator, or scientific lattice is present.
Coordinates are zero-based half-open. MERGE_* are historical comparator
projections only: they preserve source leaves and append comparator parents.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Mapping, Sequence, Tuple


PREDICTED_LOCI_FIELDS = (
    "input_id", "comparator_id", "genome_id", "contig_id", "locus_id",
    "locus_type", "start0", "end0", "score", "active_for_scoring",
    "immutable", "parent_id", "child_leaf_ids", "source_window_ids",
)


def _finite_probability(value: object) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or not 0.0 <= parsed <= 1.0:
        raise ValueError("probabilities must be finite values in [0,1]")
    return parsed


def _runs(mask: Sequence[bool]) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    start = None
    for index, value in enumerate(list(mask) + [False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            runs.append((start, index)); start = None
    return runs


def raw_threshold(probabilities: Sequence[float], threshold: float = 0.5) -> List[Tuple[int, int]]:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0,1]")
    values = [_finite_probability(value) for value in probabilities]
    return _runs([value >= threshold for value in values])


def aggregate_overlapping_windows(windows: Sequence[Mapping[str, object]], center70_only: bool) -> dict:
    """Mean-aggregate overlapping windows onto one contig probability track.

    Every row must contain the same input/genome/contig, a stable window_id,
    window_start0/window_end0, and one probability per base. CENTER70 retains
    exactly relative [615,3481) from each 4096-bp window before aggregation.
    """
    if not windows:
        raise ValueError("at least one window is required")
    keys = ("input_id", "genome_id", "contig_id")
    identity = tuple(str(windows[0][key]) for key in keys)
    starts = [int(row["window_start0"]) for row in windows]
    ends = [int(row["window_end0"]) for row in windows]
    origin, limit = min(starts), max(ends)
    sums = [0.0] * (limit - origin)
    counts = [0] * (limit - origin)
    sources = [set() for _ in range(limit - origin)]
    seen_window_ids = set()
    for row in windows:
        if tuple(str(row[key]) for key in keys) != identity:
            raise ValueError("aggregation cannot cross input/genome/contig")
        window_id = str(row["window_id"])
        if not window_id or window_id in seen_window_ids:
            raise ValueError("window_id must be nonempty and unique")
        seen_window_ids.add(window_id)
        start0, end0 = int(row["window_start0"]), int(row["window_end0"])
        probabilities = [_finite_probability(value) for value in row["probabilities"]]
        if start0 < 0 or end0 <= start0 or len(probabilities) != end0 - start0:
            raise ValueError("window coordinate/probability length mismatch")
        if center70_only:
            if len(probabilities) != 4096:
                raise ValueError("CENTER70 aggregation requires 4096-bp windows")
            relative_start, relative_end = 615, 3481
        else:
            relative_start, relative_end = 0, len(probabilities)
        for relative in range(relative_start, relative_end):
            index = start0 + relative - origin
            sums[index] += probabilities[relative]
            counts[index] += 1
            sources[index].add(window_id)
    probabilities = [None if count == 0 else sums[index] / count for index, count in enumerate(counts)]
    return {
        "input_id": identity[0], "genome_id": identity[1], "contig_id": identity[2],
        "start0": origin, "end0": limit, "probabilities": probabilities,
        "coverage_counts": counts,
        "source_window_ids": [",".join(sorted(value)) for value in sources],
        "aggregation": "CONTIG_MEAN_CENTER70_V1" if center70_only else "CONTIG_MEAN_FULL_V1",
    }


def source_leaves_from_aggregated(track: Mapping[str, object], comparator_id: str, threshold: float = 0.5) -> List[dict]:
    """Decode covered aggregated positions into stable immutable source leaves."""
    probabilities = list(track["probabilities"])
    mask = [value is not None and _finite_probability(value) >= threshold for value in probabilities]
    leaves = []
    for index, (start, end) in enumerate(_runs(mask), start=1):
        values = [float(value) for value in probabilities[start:end]]
        source_ids = sorted({item for value in track["source_window_ids"][start:end] for item in str(value).split(",") if item})
        leaves.append({
            "input_id": track["input_id"], "comparator_id": comparator_id,
            "genome_id": track["genome_id"], "contig_id": track["contig_id"],
            "locus_id": f"{comparator_id}:L{index:06d}", "locus_type": "source_leaf",
            "start0": int(track["start0"]) + start, "end0": int(track["start0"]) + end,
            "score": sum(values) / len(values), "active_for_scoring": True,
            "immutable": True, "parent_id": "", "child_leaf_ids": "",
            "source_window_ids": ",".join(source_ids),
        })
    return leaves


def viterbi_smooth(probabilities: Sequence[float], switch_penalty: float = 2.0) -> List[Tuple[int, int]]:
    values = [_finite_probability(value) for value in probabilities]
    if not values:
        return []
    eps = 1e-5
    clipped = [min(1.0 - eps, max(eps, value)) for value in values]
    emit0 = [math.log1p(-value) for value in clipped]
    emit1 = [math.log(value) for value in clipped]
    switch = -abs(float(switch_penalty))
    dp0, dp1, back0, back1 = [emit0[0]], [emit1[0]], [0], [0]
    for index in range(1, len(values)):
        stay0, switch0 = dp0[index - 1], dp1[index - 1] + switch
        if stay0 >= switch0:
            dp0.append(stay0 + emit0[index]); back0.append(0)
        else:
            dp0.append(switch0 + emit0[index]); back0.append(1)
        stay1, switch1 = dp1[index - 1], dp0[index - 1] + switch
        if stay1 >= switch1:
            dp1.append(stay1 + emit1[index]); back1.append(1)
        else:
            dp1.append(switch1 + emit1[index]); back1.append(0)
    state = 1 if dp1[-1] >= dp0[-1] else 0
    mask = [False] * len(values)
    for index in range(len(values) - 1, -1, -1):
        mask[index] = bool(state)
        state = back1[index] if state else back0[index]
    return _runs(mask)


def merge_typed_parents(
    leaves: Iterable[Mapping[str, object]], comparator_id: str, max_gap_bp: int
) -> Tuple[List[dict], List[dict]]:
    """Historical MERGE comparator only; not a scientific lattice implementation."""
    if comparator_id not in {"MERGE_STRICT", "MERGE_LOOSE"} or max_gap_bp < 0:
        raise ValueError("unsupported merge comparator or gap")
    copied = [dict(row) for row in leaves]
    required = {"input_id", "genome_id", "contig_id", "locus_id", "start0", "end0", "score"}
    for row in copied:
        if not required.issubset(row) or int(row["start0"]) >= int(row["end0"]):
            raise ValueError("invalid source leaf")
        row["locus_type"] = "source_leaf"; row["immutable"] = True
    copied.sort(key=lambda row: (str(row["input_id"]), str(row["genome_id"]), str(row["contig_id"]), int(row["start0"]), int(row["end0"]), str(row["locus_id"])))
    groups: List[List[dict]] = []
    for row in copied:
        if not groups:
            groups.append([row]); continue
        previous = groups[-1][-1]
        same_track = all(row[key] == previous[key] for key in ("input_id", "genome_id", "contig_id"))
        gap = int(row["start0"]) - int(previous["end0"])
        if same_track and 0 <= gap <= max_gap_bp:
            groups[-1].append(row)
        else:
            groups.append([row])
    parents = []
    for index, group in enumerate(groups, start=1):
        if len(group) < 2:
            continue
        parent_id = f"{comparator_id}:P{index:06d}"
        parents.append({
            "input_id": group[0]["input_id"], "comparator_id": comparator_id,
            "genome_id": group[0]["genome_id"], "contig_id": group[0]["contig_id"],
            "locus_id": parent_id, "locus_type": "comparator_merge_parent",
            "start0": int(group[0]["start0"]), "end0": int(group[-1]["end0"]),
            "score": min(float(row["score"]) for row in group), "active_for_scoring": True,
            "immutable": False, "parent_id": "",
            "child_leaf_ids": ",".join(str(row["locus_id"]) for row in group),
            "source_window_ids": ",".join(sorted({value for row in group for value in str(row.get("source_window_ids", "")).split(",") if value})),
        })
        for row in group:
            row["parent_id"] = parent_id; row["active_for_scoring"] = False
    for row in copied:
        row.setdefault("comparator_id", comparator_id); row.setdefault("active_for_scoring", not bool(row.get("parent_id")))
        row.setdefault("parent_id", ""); row.setdefault("child_leaf_ids", ""); row.setdefault("source_window_ids", "")
    return copied, parents


def run_semantic_probes() -> dict:
    def window(window_id, start0, value):
        return {"input_id": "I", "genome_id": "G", "contig_id": "C", "window_id": window_id,
                "window_start0": start0, "window_end0": start0 + 4096, "probabilities": [value] * 4096}
    full = aggregate_overlapping_windows([window("W1", 0, 0.2), window("W2", 2048, 0.8)], False)
    center = aggregate_overlapping_windows([window("W1", 0, 0.2), window("W2", 2048, 0.8)], True)
    leaf_track = {"input_id": "I", "genome_id": "G", "contig_id": "C", "start0": 10,
                  "probabilities": [0.1, 0.8, 0.9, None, 0.7], "source_window_ids": ["W1"] * 5}
    raw_leaves = source_leaves_from_aggregated(leaf_track, "RAW", 0.5)
    fixture = [
        {"input_id": "I", "genome_id": "G", "contig_id": "C", "locus_id": "L1", "start0": 10, "end0": 20, "score": 0.9},
        {"input_id": "I", "genome_id": "G", "contig_id": "C", "locus_id": "L2", "start0": 30, "end0": 40, "score": 0.8},
        {"input_id": "I", "genome_id": "G", "contig_id": "C", "locus_id": "L3", "start0": 90, "end0": 100, "score": 0.7},
    ]
    strict_leaves, strict_parents = merge_typed_parents(fixture, "MERGE_STRICT", 20)
    loose_leaves, loose_parents = merge_typed_parents(fixture, "MERGE_LOOSE", 100)
    checks = {
        "CONTIG_MEAN_FULL_V1": full["coverage_counts"][2048] == 2 and abs(full["probabilities"][2048] - 0.5) < 1e-12,
        "CONTIG_MEAN_CENTER70_V1": center["coverage_counts"][2663] == 2 and abs(center["probabilities"][2663] - 0.5) < 1e-12,
        "SOURCE_LEAF_RUNS_V1": [(row["start0"], row["end0"]) for row in raw_leaves] == [(11, 13), (14, 15)],
        "RAW_THRESHOLD_V1": raw_threshold([0.1, 0.5, 0.8, 0.2, 0.7]) == [(1, 3), (4, 5)],
        "HISTORICAL_VITERBI_PENALTY_2_V1": viterbi_smooth([0.05, 0.95, 0.95, 0.05], 2.0) == [(1, 3)],
        "MERGE_STRICT_V1": len(strict_parents) == 1 and strict_parents[0]["child_leaf_ids"] == "L1,L2",
        "MERGE_LOOSE_V1": len(loose_parents) == 1 and loose_parents[0]["child_leaf_ids"] == "L1,L2,L3",
        "COMPARATOR_LEAF_RETENTION_V1": all(row["immutable"] for row in strict_leaves + loose_leaves)
        and [(row["locus_id"], row["start0"], row["end0"]) for row in strict_leaves] == [("L1", 10, 20), ("L2", 30, 40), ("L3", 90, 100)],
    }
    return {"checks": checks, "pass": all(checks.values())}
