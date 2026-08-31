#!/usr/bin/env python3
"""Evaluate the frozen Gate L-R reproducibility estimand.

The three response directories are normalized bundles produced by
``validate_gate_l_pass1.py``.  This command deliberately evaluates only
pre-adjudication reproducibility on the 120 main packages.  Provenance (L-P),
denominator discovery (L-D), and the final Gate L status are outside its
scope.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping, Sequence


MAIN_PACKAGE_COUNT = 120
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260831
BOOTSTRAP_LOWER_INDEX = 249  # one-based order statistic 250

S0_CELLS = ("S0-L1", "S0-L2", "S0-L3", "S0-L4")
S1_CELLS = ("S1-C1", "S1-C2", "S1-C3")
BOOTSTRAP_CELL_QUOTAS = {
    **{cell: 15 for cell in S0_CELLS},
    **{cell: 20 for cell in S1_CELLS},
}
EDGE_TYPES = ("material_of", "nested_in", "distinct_locus", "overlap_unresolved")
BOUNDARY_CATEGORIES = ("point", "interval", "unidentifiable")

TABLE_FIELDS = {
    "package_reviews.tsv": (
        "package_id",
        "actor_id",
        "package_status",
        "topology_resolution",
        "topology_reason",
    ),
    "loci.tsv": (
        "package_id",
        "actor_id",
        "locus_id",
        "locus_status",
        "locus_envelope_start",
        "locus_envelope_end",
    ),
    "material_segments.tsv": (
        "package_id",
        "actor_id",
        "segment_id",
        "locus_id",
        "seqid",
        "start",
        "end",
        "evidence_codes",
        "locus_assignment_status",
    ),
    "boundaries.tsv": (
        "package_id",
        "actor_id",
        "locus_id",
        "side",
        "identifiability",
        "lower_pos",
        "upper_pos",
        "evidence_codes",
    ),
    "interruptions.tsv": (
        "package_id",
        "actor_id",
        "interruption_id",
        "locus_id",
        "child_locus_id",
        "seqid",
        "start",
        "end",
        "interruption_type",
        "evidence_codes",
    ),
    "relations.tsv": (
        "package_id",
        "actor_id",
        "relation_id",
        "relation_type",
        "subject_locus_id",
        "object_locus_id",
        "evidence_codes",
    ),
}


@dataclass(frozen=True)
class Locus:
    locus_id: str
    status: str
    seqid: str
    envelope_start: int
    envelope_end: int

    @property
    def coordinate_key(self) -> tuple[str, int, int]:
        return (self.seqid, self.envelope_start, self.envelope_end)


@dataclass(frozen=True)
class Segment:
    segment_id: str
    locus_id: str | None
    assignment_status: str
    seqid: str
    start: int
    end: int

    @property
    def coordinate_key(self) -> tuple[str, int, int]:
        return (self.seqid, self.start, self.end)


@dataclass(frozen=True)
class Review:
    package_status: str
    topology_resolution: str


@dataclass
class Bundle:
    reviews: dict[str, Review]
    loci: dict[str, list[Locus]]
    materials: dict[str, list[Segment]]
    boundaries: dict[str, dict[tuple[str, str], str]]
    relations: dict[str, list[tuple[str, str, str]]]


@dataclass(frozen=True)
class EdgeCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def __add__(self, other: "EdgeCounts") -> "EdgeCounts":
        return EdgeCounts(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)


@dataclass(frozen=True)
class PackageScore:
    package_id: str
    hard_cell: str
    material_iou: float
    locus_count_equal: bool
    edge_counts: Mapping[str, EdgeCounts]
    boundary_ratings: tuple[tuple[str, str], ...]
    matched_locus_pairs: int


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing TSV header: {path}")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"duplicate TSV columns: {path}")
        rows = list(reader)
    for line_number, row in enumerate(rows, start=2):
        if any(value is None for value in row.values()):
            raise ValueError(f"malformed TSV row at {path}:{line_number}")
    return rows


def _require_fields(rows: list[dict[str, str]], fields: Sequence[str], path: Path) -> None:
    observed = set(rows[0]) if rows else set()
    if not rows:
        # Empty response tables still need their headers checked.
        with path.open(newline="", encoding="utf-8") as handle:
            observed = set(csv.DictReader(handle, delimiter="\t").fieldnames or ())
    expected = set(fields)
    if observed != expected:
        raise ValueError(f"{path.name} schema must be {list(fields)}, got {sorted(observed)}")


def read_packages(path: Path) -> dict[str, str]:
    rows = read_tsv(path)
    if not rows:
        raise ValueError("packages.tsv is empty")
    required = {"package_id", "role", "hard_cell"}
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"packages.tsv missing fields: {missing}")
    packages: dict[str, str] = {}
    for row in rows:
        package_id = row["package_id"]
        if not package_id or package_id in packages:
            raise ValueError(f"duplicate or empty package_id: {package_id!r}")
        if row["role"] == "main":
            packages[package_id] = row["hard_cell"]
    if len(packages) != MAIN_PACKAGE_COUNT:
        raise ValueError(f"expected {MAIN_PACKAGE_COUNT} main packages, got {len(packages)}")
    if set(packages.values()) != set(BOOTSTRAP_CELL_QUOTAS):
        raise ValueError("main packages do not contain the seven frozen hard cells")
    observed_quotas = Counter(packages.values())
    expected_quotas = Counter({cell: quota for cell, quota in BOOTSTRAP_CELL_QUOTAS.items()})
    if observed_quotas != expected_quotas:
        raise ValueError(f"main hard-cell quotas disagree with frozen panel: {dict(observed_quotas)}")
    return packages


def _integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer for {label}: {value!r}") from error


def read_bundle(path: Path) -> Bundle:
    raw: dict[str, list[dict[str, str]]] = {}
    for filename, fields in TABLE_FIELDS.items():
        table_path = path / filename
        rows = read_tsv(table_path)
        _require_fields(rows, fields, table_path)
        raw[filename] = rows

    reviews: dict[str, Review] = {}
    for row in raw["package_reviews.tsv"]:
        package_id = row["package_id"]
        if package_id in reviews:
            raise ValueError(f"duplicate package review: {package_id}")
        reviews[package_id] = Review(row["package_status"], row["topology_resolution"])

    loci: dict[str, list[Locus]] = {}
    for row in raw["loci.tsv"]:
        package_id = row["package_id"]
        loci.setdefault(package_id, []).append(
            Locus(
                row["locus_id"],
                row["locus_status"],
                # loci.tsv has no seqid; the package seqid is used at scoring time.
                "",
                _integer(row["locus_envelope_start"], f"{package_id}.locus_envelope_start"),
                _integer(row["locus_envelope_end"], f"{package_id}.locus_envelope_end"),
            )
        )

    materials: dict[str, list[Segment]] = {}
    for row in raw["material_segments.tsv"]:
        package_id = row["package_id"]
        assignment = row["locus_assignment_status"]
        materials.setdefault(package_id, []).append(
            Segment(
                row["segment_id"],
                row["locus_id"] or None,
                assignment,
                row["seqid"],
                _integer(row["start"], f"{package_id}/{row['segment_id']}.start"),
                _integer(row["end"], f"{package_id}/{row['segment_id']}.end"),
            )
        )

    boundaries: dict[str, dict[tuple[str, str], str]] = {}
    for row in raw["boundaries.tsv"]:
        package_id = row["package_id"]
        key = (row["locus_id"], row["side"])
        if key in boundaries.setdefault(package_id, {}):
            raise ValueError(f"duplicate boundary row: {package_id}/{key}")
        boundaries[package_id][key] = row["identifiability"]

    relations: dict[str, list[tuple[str, str, str]]] = {}
    for row in raw["relations.tsv"]:
        relations.setdefault(row["package_id"], []).append(
            (row["relation_type"], row["subject_locus_id"], row["object_locus_id"])
        )

    return Bundle(reviews, loci, materials, boundaries, relations)


def _merge_intervals(intervals: Iterable[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    ordered = sorted(intervals)
    merged: list[tuple[str, int, int]] = []
    for seqid, start, end in ordered:
        if merged and merged[-1][0] == seqid and start <= merged[-1][2]:
            previous = merged[-1]
            merged[-1] = (seqid, previous[1], max(previous[2], end))
        else:
            merged.append((seqid, start, end))
    return merged


def interval_union_length(intervals: Iterable[tuple[str, int, int]]) -> int:
    return sum(end - start for _, start, end in _merge_intervals(intervals))


def interval_intersection_length(
    left: Iterable[tuple[str, int, int]], right: Iterable[tuple[str, int, int]]
) -> int:
    left_merged = _merge_intervals(left)
    right_merged = _merge_intervals(right)
    total = 0
    j = 0
    for left_seqid, left_start, left_end in left_merged:
        while j < len(right_merged) and (
            right_merged[j][0] < left_seqid
            or (right_merged[j][0] == left_seqid and right_merged[j][2] <= left_start)
        ):
            j += 1
        k = j
        while k < len(right_merged) and right_merged[k][0] == left_seqid and right_merged[k][1] < left_end:
            total += max(0, min(left_end, right_merged[k][2]) - max(left_start, right_merged[k][1]))
            k += 1
    return total


def interval_iou(
    left: Iterable[tuple[str, int, int]], right: Iterable[tuple[str, int, int]]
) -> float:
    left_list = list(left)
    right_list = list(right)
    union = interval_union_length(left_list + right_list)
    if union == 0:
        return 0.0
    return interval_intersection_length(left_list, right_list) / union


def _coordinate_key(item: object) -> tuple:
    return tuple(getattr(item, "coordinate_key"))


def _maximum_bipartite_matching(
    left: Sequence[object],
    right: Sequence[object],
    score: Mapping[tuple[int, int], float],
) -> list[tuple[int, int]]:
    """Return max-cardinality, max-total-score matching with coordinate ties.

    Only pairs present in ``score`` are eligible.  The final tie-break uses
    canonical coordinate tuples, never actor-local IDs.
    """

    # Keep the DP mask on the smaller side.  Package-local locus counts are
    # small; this also makes the exact cardinality-first rule explicit.
    swapped = len(right) > len(left)
    if swapped:
        left, right = right, left
        score = {(j, i): value for (i, j), value in score.items()}

    @lru_cache(maxsize=None)
    def solve(index: int, used_mask: int) -> tuple[int, float, tuple[tuple[tuple, tuple], ...], tuple[tuple[int, int], ...]]:
        if index == len(left):
            return (0, 0.0, (), ())
        best = solve(index + 1, used_mask)
        for right_index in range(len(right)):
            if used_mask & (1 << right_index) or (index, right_index) not in score:
                continue
            cardinality, total, tie, pairs = solve(index + 1, used_mask | (1 << right_index))
            pair_key = (_coordinate_key(left[index]), _coordinate_key(right[right_index]))
            candidate = (
                cardinality + 1,
                total + score[(index, right_index)],
                tuple(sorted((pair_key,) + tie)),
                ((index, right_index),) + pairs,
            )
            if _matching_better(candidate, best):
                best = candidate
        return best

    result = solve(0, 0)[3]
    if swapped:
        return [(right_index, left_index) for left_index, right_index in result]
    return list(result)


def _matching_better(left: tuple, right: tuple) -> bool:
    if left[0] != right[0]:
        return left[0] > right[0]
    if left[1] != right[1]:
        return left[1] > right[1]
    return left[2] < right[2]


def _locus_material(bundle: Bundle, package_id: str, locus: Locus) -> list[tuple[str, int, int]]:
    return [
        (segment.seqid, segment.start, segment.end)
        for segment in bundle.materials.get(package_id, ())
        if segment.assignment_status == "assigned" and segment.locus_id == locus.locus_id
    ]


def _locus_matches(
    package_id: str,
    left_bundle: Bundle,
    right_bundle: Bundle,
    left_seqid: str,
    right_seqid: str,
) -> tuple[list[tuple[Locus, Locus]], dict[str, str], dict[str, str]]:
    left_loci = [
        Locus(locus.locus_id, locus.status, left_seqid, locus.envelope_start, locus.envelope_end)
        for locus in left_bundle.loci.get(package_id, ())
        if locus.status in {"resolved", "partially_resolved"}
    ]
    right_loci = [
        Locus(locus.locus_id, locus.status, right_seqid, locus.envelope_start, locus.envelope_end)
        for locus in right_bundle.loci.get(package_id, ())
        if locus.status in {"resolved", "partially_resolved"}
    ]
    score: dict[tuple[int, int], float] = {}
    for left_index, left in enumerate(left_loci):
        for right_index, right in enumerate(right_loci):
            value = interval_iou(
                _locus_material(left_bundle, package_id, left),
                _locus_material(right_bundle, package_id, right),
            )
            if value >= 0.50:
                score[(left_index, right_index)] = value
    pairs = _maximum_bipartite_matching(left_loci, right_loci, score)
    matched = [(left_loci[i], right_loci[j]) for i, j in pairs]
    left_to_pair = {left.locus_id: str(index) for index, (left, _) in enumerate(matched)}
    right_to_pair = {right.locus_id: str(index) for index, (_, right) in enumerate(matched)}
    return matched, left_to_pair, right_to_pair


def _segment_matches(
    package_id: str,
    left_bundle: Bundle,
    right_bundle: Bundle,
    left_locus: Locus,
    right_locus: Locus,
) -> int:
    left_segments = [
        segment
        for segment in left_bundle.materials.get(package_id, ())
        if segment.assignment_status == "assigned" and segment.locus_id == left_locus.locus_id
    ]
    right_segments = [
        segment
        for segment in right_bundle.materials.get(package_id, ())
        if segment.assignment_status == "assigned" and segment.locus_id == right_locus.locus_id
    ]
    score: dict[tuple[int, int], float] = {}
    for left_index, left in enumerate(left_segments):
        for right_index, right in enumerate(right_segments):
            value = interval_iou(
                [(left.seqid, left.start, left.end)],
                [(right.seqid, right.start, right.end)],
            )
            if value >= 0.50:
                score[(left_index, right_index)] = value
    return len(_maximum_bipartite_matching(left_segments, right_segments, score))


def _relation_key(
    relation: tuple[str, str, str], pair_map: Mapping[str, str]
) -> tuple[str, str, str] | None:
    relation_type, subject, object_ = relation
    if subject not in pair_map or object_ not in pair_map:
        return None
    left, right = pair_map[subject], pair_map[object_]
    if relation_type in {"distinct_locus", "overlap_unresolved"}:
        left, right = sorted((left, right))
    return (relation_type, left, right)


def _edge_counts_for_package(
    package_id: str,
    left_bundle: Bundle,
    right_bundle: Bundle,
    left_seqid: str,
    right_seqid: str,
) -> tuple[dict[str, EdgeCounts], tuple[tuple[str, str], ...], int]:
    matched, left_map, right_map = _locus_matches(
        package_id, left_bundle, right_bundle, left_seqid, right_seqid
    )

    left_assigned = [
        segment
        for segment in left_bundle.materials.get(package_id, ())
        if segment.assignment_status == "assigned"
    ]
    right_assigned = [
        segment
        for segment in right_bundle.materials.get(package_id, ())
        if segment.assignment_status == "assigned"
    ]
    material_tp = sum(
        _segment_matches(package_id, left_bundle, right_bundle, left, right)
        for left, right in matched
    )
    counts: dict[str, EdgeCounts] = {
        "material_of": EdgeCounts(material_tp, len(left_assigned) - material_tp, len(right_assigned) - material_tp)
    }

    left_relations = left_bundle.relations.get(package_id, ())
    right_relations = right_bundle.relations.get(package_id, ())
    for relation_type in ("nested_in", "distinct_locus", "overlap_unresolved"):
        left_keys = {
            key for relation in left_relations if relation[0] == relation_type
            for key in [_relation_key(relation, left_map)]
            if key is not None
        }
        right_keys = {
            key for relation in right_relations if relation[0] == relation_type
            for key in [_relation_key(relation, right_map)]
            if key is not None
        }
        left_total = sum(relation[0] == relation_type for relation in left_relations)
        right_total = sum(relation[0] == relation_type for relation in right_relations)
        tp = len(left_keys & right_keys)
        counts[relation_type] = EdgeCounts(tp, left_total - tp, right_total - tp)

    boundary_ratings: list[tuple[str, str]] = []
    for left, right in matched:
        for side in ("left", "right"):
            left_category = left_bundle.boundaries.get(package_id, {}).get((left.locus_id, side))
            right_category = right_bundle.boundaries.get(package_id, {}).get((right.locus_id, side))
            if left_category is None or right_category is None:
                raise ValueError(f"matched locus lacks boundary row: {package_id}/{side}")
            boundary_ratings.append((left_category, right_category))
    return counts, tuple(boundary_ratings), len(matched)


def _material_union(bundle: Bundle, package_id: str) -> list[tuple[str, int, int]]:
    return [
        (segment.seqid, segment.start, segment.end)
        for segment in bundle.materials.get(package_id, ())
    ]


def _active_edge_types(
    package_ids: Iterable[str], left_bundle: Bundle, right_bundle: Bundle
) -> tuple[str, ...]:
    active: set[str] = set()
    for package_id in package_ids:
        if any(segment.assignment_status == "assigned" for segment in left_bundle.materials.get(package_id, ())):
            active.add("material_of")
        if any(segment.assignment_status == "assigned" for segment in right_bundle.materials.get(package_id, ())):
            active.add("material_of")
        for bundle in (left_bundle, right_bundle):
            active.update(relation[0] for relation in bundle.relations.get(package_id, ()))
    return tuple(edge_type for edge_type in EDGE_TYPES if edge_type in active)


def _f1(counts: EdgeCounts) -> float:
    denominator = 2 * counts.tp + counts.fp + counts.fn
    return 0.0 if denominator == 0 else 2 * counts.tp / denominator


def _sum_counts(scores: Iterable[PackageScore], edge_type: str) -> EdgeCounts:
    total = EdgeCounts()
    for score in scores:
        total += score.edge_counts[edge_type]
    return total


def compute_gwet_ac1(ratings: Sequence[tuple[str, str]]) -> dict[str, object]:
    """Compute nominal three-class Gwet AC1 and expose its rating denominator."""

    n = len(ratings)
    if n == 0:
        return {
            "value": None,
            "status": "AC1_UNEVALUABLE",
            "rating_count": 0,
            "denominator": 0,
            "agreement_count": 0,
            "categories": list(BOUNDARY_CATEGORIES),
        }
    observed = sum(left == right for left, right in ratings) / n
    counts = {category: 0 for category in BOUNDARY_CATEGORIES}
    for left, right in ratings:
        counts[left] += 1
        counts[right] += 1
    proportions = {category: count / (2 * n) for category, count in counts.items()}
    chance = sum(p * (1 - p) for p in proportions.values()) / (len(BOUNDARY_CATEGORIES) - 1)
    denominator = 1 - chance
    if denominator == 0:
        value = None
        status = "AC1_UNEVALUABLE"
    else:
        value = (observed - chance) / denominator
        status = "EVALUATED"
    return {
        "value": value,
        "status": status,
        "rating_count": n,
        "denominator": n,
        "agreement_count": sum(left == right for left, right in ratings),
        "categories": list(BOUNDARY_CATEGORIES),
        "category_rating_counts": counts,
    }


def _bootstrap_samples(
    cell_to_package_indices: Mapping[str, Sequence[int]],
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> list[list[int]]:
    try:
        import numpy as np
    except ModuleNotFoundError as error:
        raise RuntimeError("Gate L-R bootstrap requires NumPy PCG64") from error

    generator = np.random.Generator(np.random.PCG64(seed))
    samples: list[list[int]] = []
    for _ in range(replicates):
        replicate: list[int] = []
        for cell in (*S0_CELLS, *S1_CELLS):
            indices = cell_to_package_indices[cell]
            quota = BOOTSTRAP_CELL_QUOTAS[cell]
            draw = generator.choice(len(indices), size=quota, replace=True)
            replicate.extend(indices[int(index)] for index in draw)
        samples.append(replicate)
    return samples


def _bootstrap_summary(
    scores: Sequence[PackageScore],
    cell_to_package_indices: Mapping[str, Sequence[int]],
    active_edge_types: Sequence[str],
) -> dict[str, object]:
    material_values: list[float] = []
    macro_values: list[float] = []
    for sample in _bootstrap_samples(cell_to_package_indices):
        sampled_scores = [scores[index] for index in sample]
        material_values.append(statistics.median(score.material_iou for score in sampled_scores))
        f1_values = []
        for edge_type in active_edge_types:
            f1_values.append(_f1(_sum_counts(sampled_scores, edge_type)))
        macro_values.append(statistics.fmean(f1_values) if f1_values else 0.0)
    material_values.sort()
    macro_values.sort()
    return {
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": BOOTSTRAP_SEED,
        "sampling": "within each of seven frozen hard cells with replacement",
        "lower_order_statistic": 250,
        "median_material_union_iou": material_values[BOOTSTRAP_LOWER_INDEX],
        "ontology_edge_macro_f1": macro_values[BOOTSTRAP_LOWER_INDEX],
    }


def evaluate_gate_l_reproducibility(
    packages_path: Path,
    a1_path: Path,
    a2_path: Path,
    adj_path: Path,
) -> dict[str, object]:
    package_cells = read_packages(packages_path)
    a1 = read_bundle(a1_path)
    a2 = read_bundle(a2_path)
    adj = read_bundle(adj_path)
    package_ids = tuple(package_cells)
    if not set(package_ids) <= set(a1.reviews) or not set(package_ids) <= set(a2.reviews) or not set(package_ids) <= set(adj.reviews):
        raise ValueError("A1, A2 and ADJ bundles must contain every main package review")

    active_edge_types = _active_edge_types(package_ids, a1, a2)
    scores: list[PackageScore] = []
    for package_id in package_ids:
        # Material rows carry the package contig; locus envelopes do not.
        material_counts, ratings, matched_count = _edge_counts_for_package(
            package_id,
            a1,
            a2,
            a1.materials.get(package_id, [Segment("", None, "", "", 0, 0)])[0].seqid
            if a1.materials.get(package_id)
            else "",
            a2.materials.get(package_id, [Segment("", None, "", "", 0, 0)])[0].seqid
            if a2.materials.get(package_id)
            else "",
        )
        scores.append(
            PackageScore(
                package_id,
                package_cells[package_id],
                interval_iou(_material_union(a1, package_id), _material_union(a2, package_id)),
                len(a1.loci.get(package_id, ())) == len(a2.loci.get(package_id, ())),
                material_counts,
                ratings,
                matched_count,
            )
        )

    median_iou = statistics.median(score.material_iou for score in scores)
    count_numerator = sum(score.locus_count_equal for score in scores)
    point_counts = {edge_type: _sum_counts(scores, edge_type) for edge_type in EDGE_TYPES}
    edge_f1 = {edge_type: _f1(point_counts[edge_type]) for edge_type in active_edge_types}
    macro_f1 = statistics.fmean(edge_f1.values()) if edge_f1 else 0.0
    ratings = [rating for score in scores for rating in score.boundary_ratings]
    matched_locus_pairs = sum(score.matched_locus_pairs for score in scores)
    matched_package_count = sum(bool(score.boundary_ratings) for score in scores)
    boundary = compute_gwet_ac1(ratings)
    if matched_locus_pairs < 40 or matched_package_count < 20:
        boundary["status"] = "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS"
        boundary["value"] = None
    major_numerator = sum(
        adj.reviews[package_id].topology_resolution == "new_topology" for package_id in package_ids
    )
    resolved_numerator = sum(
        adj.reviews[package_id].package_status in {"resolved", "partially_resolved"}
        for package_id in package_ids
    )

    cell_to_indices: dict[str, list[int]] = {cell: [] for cell in BOOTSTRAP_CELL_QUOTAS}
    for index, score in enumerate(scores):
        cell_to_indices[score.hard_cell].append(index)
    bootstrap = _bootstrap_summary(scores, cell_to_indices, active_edge_types)

    metrics: dict[str, object] = {
        "median_material_union_iou": {
            "value": median_iou,
            "numerator": median_iou,
            "denominator": MAIN_PACKAGE_COUNT,
            "threshold": 0.80,
            "direction": "ge",
        },
        "bootstrap_lower_bound_median_material_union_iou": {
            "value": bootstrap["median_material_union_iou"],
            "numerator": bootstrap["median_material_union_iou"],
            "denominator": BOOTSTRAP_REPLICATES,
            "threshold": 0.70,
            "direction": "ge",
        },
        "exact_locus_count_agreement": {
            "value": count_numerator / MAIN_PACKAGE_COUNT,
            "numerator": count_numerator,
            "denominator": MAIN_PACKAGE_COUNT,
            "threshold": 0.70,
            "direction": "ge",
        },
        "ontology_edge_macro_f1": {
            "value": macro_f1,
            "numerator": sum(edge_f1.values()),
            "denominator": len(active_edge_types),
            "threshold": 0.75,
            "direction": "ge",
            "active_edge_types": list(active_edge_types),
            "per_edge_type": {
                edge_type: {
                    "value": edge_f1[edge_type],
                    "tp": point_counts[edge_type].tp,
                    "fp": point_counts[edge_type].fp,
                    "fn": point_counts[edge_type].fn,
                }
                for edge_type in active_edge_types
            },
        },
        "bootstrap_lower_bound_ontology_edge_macro_f1": {
            "value": bootstrap["ontology_edge_macro_f1"],
            "numerator": bootstrap["ontology_edge_macro_f1"],
            "denominator": BOOTSTRAP_REPLICATES,
            "threshold": 0.65,
            "direction": "ge",
        },
        "boundary_identifiability_gwet_ac1": {
            **boundary,
            "matched_locus_pairs": matched_locus_pairs,
            "matched_package_count": matched_package_count,
            "threshold": 0.60,
            "direction": "ge",
        },
        "major_topology_adjudication_fraction": {
            "value": major_numerator / MAIN_PACKAGE_COUNT,
            "numerator": major_numerator,
            "denominator": MAIN_PACKAGE_COUNT,
            "threshold": 0.35,
            "direction": "le",
        },
        "resolved_plus_partially_resolved_package_fraction": {
            "value": resolved_numerator / MAIN_PACKAGE_COUNT,
            "numerator": resolved_numerator,
            "denominator": MAIN_PACKAGE_COUNT,
            "threshold": 0.65,
            "direction": "ge",
        },
    }

    failed = [
        metrics["median_material_union_iou"]["value"] < 0.80,
        metrics["bootstrap_lower_bound_median_material_union_iou"]["value"] < 0.70,
        metrics["exact_locus_count_agreement"]["value"] < 0.70,
        metrics["ontology_edge_macro_f1"]["value"] < 0.75,
        metrics["bootstrap_lower_bound_ontology_edge_macro_f1"]["value"] < 0.65,
        metrics["major_topology_adjudication_fraction"]["value"] > 0.35,
        metrics["resolved_plus_partially_resolved_package_fraction"]["value"] < 0.65,
    ]
    if boundary["status"] == "AC1_UNEVALUABLE":
        failed.append(True)
    elif boundary["status"] == "EVALUATED" and boundary["value"] < 0.60:
        failed.append(True)
    status = "NO_GO_LR" if any(failed) else (
        "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS"
        if boundary["status"] == "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS"
        else "PASS"
    )
    return {
        "schema": "gate_l_lr_v1",
        "status": status,
        "estimand_scope": "conditional_challenge_panel",
        "panel": {"main_packages": MAIN_PACKAGE_COUNT, "strata": list(S0_CELLS + S1_CELLS)},
        "bootstrap": bootstrap,
        "boundary_status": boundary["status"],
        "metrics": metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--a1", type=Path, required=True)
    parser.add_argument("--a2", type=Path, required=True)
    parser.add_argument("--adj", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_gate_l_reproducibility(args.packages, args.a1, args.a2, args.adj)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
