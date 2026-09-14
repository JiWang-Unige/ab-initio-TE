#!/usr/bin/env python3
"""Phase 0 contract and synthetic screen for TE fragment linking.

This module is deliberately an engineering fixture.  It does not infer a gap,
modify a material mask, call a GLM, or report a biological score.  It creates
small interval records with independently stored truth and predicted fields,
then emits two deterministic association-edge rules:

* B0: link a candidate when the coordinate distance is within the fixed bound.
* B1: B0 plus agreement of predicted family, predicted orientation, and a
  predicted-length ratio.

The fixture makes the important failure modes visible: adjacent independent
insertions, nesting, unknown orientation, a true pair outside the candidate
window, unresolved truth, and transitive component over-merging.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


CONTRACT_VERSION = "fragment-linking-phase0-v1"
ENGINEERING_ONLY = "ENGINEERING_ONLY"
KNOWN = "known"
UNRESOLVED = "unresolved"
SPLITS = ("train", "dev", "test")


@dataclass(frozen=True)
class Fragment:
    """One model-predicted fragment and its separate truth metadata.

    ``start`` and ``end`` use the half-open convention ``[start, end)``.
    ``parent_insertion_id`` is an explicit truth identity and is never inferred
    from ``source_copy_id`` or ``family_group_id``.  Unresolved truth has no
    parent identity and must not be treated as a negative pair.
    """

    fragment_id: str
    contig: str
    start: int
    end: int
    source_copy_id: str
    family_group_id: str
    parent_insertion_id: Optional[str]
    truth_status: str
    truth_family: Optional[str]
    truth_orientation: Optional[str]
    predicted_family: Optional[str]
    predicted_orientation: Optional[str]
    predicted_length: Optional[int]
    case: str
    annotation_provenance: str = ENGINEERING_ONLY

    @property
    def interval(self) -> Tuple[int, int]:
        return self.start, self.end

    @property
    def observed_length(self) -> int:
        return self.end - self.start

    def to_record(self) -> dict:
        """Return the contract record with truth/prediction namespaces split."""

        return {
            "fragment_id": self.fragment_id,
            "contig": self.contig,
            "interval": {"start": self.start, "end": self.end, "convention": "[start,end)"},
            "source_copy_id": self.source_copy_id,
            "family_group_id": self.family_group_id,
            "case": self.case,
            "truth": {
                "status": self.truth_status,
                "parent_insertion_id": self.parent_insertion_id,
                "family": self.truth_family,
                "orientation": self.truth_orientation,
            },
            "prediction": {
                "family": self.predicted_family,
                "orientation": self.predicted_orientation,
                "length": self.predicted_length,
            },
            "annotation_provenance": self.annotation_provenance,
        }


def _known(
    fragment_id: str,
    start: int,
    end: int,
    source_copy_id: str,
    family_group_id: str,
    parent_insertion_id: str,
    truth_family: str,
    truth_orientation: str,
    predicted_family: Optional[str],
    predicted_orientation: Optional[str],
    predicted_length: Optional[int],
    case: str,
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        contig="toy_chr",
        start=start,
        end=end,
        source_copy_id=source_copy_id,
        family_group_id=family_group_id,
        parent_insertion_id=parent_insertion_id,
        truth_status=KNOWN,
        truth_family=truth_family,
        truth_orientation=truth_orientation,
        predicted_family=predicted_family,
        predicted_orientation=predicted_orientation,
        predicted_length=predicted_length,
        case=case,
    )


def _unresolved(
    fragment_id: str,
    start: int,
    end: int,
    source_copy_id: str,
    family_group_id: str,
    predicted_family: Optional[str],
    predicted_orientation: Optional[str],
    predicted_length: Optional[int],
    case: str,
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        contig="toy_chr",
        start=start,
        end=end,
        source_copy_id=source_copy_id,
        family_group_id=family_group_id,
        parent_insertion_id=None,
        truth_status=UNRESOLVED,
        truth_family=None,
        truth_orientation=None,
        predicted_family=predicted_family,
        predicted_orientation=predicted_orientation,
        predicted_length=predicted_length,
        case=case,
    )


def make_fixture() -> List[Fragment]:
    """Create the deterministic, manually annotated engineering fixture.

    Every family/orientation prediction below is hand-entered synthetic input;
    it is not a model output and has no biological validity claim.
    """

    return [
        # Same insertion: a true positive for B0 and B1.
        _known("same_a", 100, 140, "copy_same", "Fam_LTR_A", "ins_same", "Fam_LTR_A", "+", "Fam_LTR_A", "+", 40, "same_insertion"),
        _known("same_b", 160, 200, "copy_same", "Fam_LTR_A", "ins_same", "Fam_LTR_A", "+", "Fam_LTR_A", "+", 42, "same_insertion"),
        # Adjacent independent insertions with identical predictions: B1 false positive.
        _known("adj_a", 300, 340, "copy_adj_a", "Fam_LINE_A", "ins_adj_a", "Fam_LINE_A", "+", "Fam_LINE_A", "+", 40, "adjacent_independent"),
        _known("adj_b", 350, 390, "copy_adj_b", "Fam_LINE_A", "ins_adj_b", "Fam_LINE_A", "+", "Fam_LINE_A", "+", 40, "adjacent_independent"),
        # Nested insertion: B0 links through distance; family disagreement blocks B1.
        _known("outer_left", 500, 540, "copy_outer", "Fam_LINE_A", "ins_outer", "Fam_LINE_A", "+", "Fam_LINE_A", "+", 40, "nested_outer"),
        _known("inner", 545, 575, "copy_inner", "Fam_DNA_A", "ins_inner", "Fam_DNA_A", "+", "Fam_DNA_A", "+", 30, "nested_inner"),
        _known("outer_right", 580, 620, "copy_outer", "Fam_LINE_A", "ins_outer", "Fam_LINE_A", "+", "Fam_LINE_A", "+", 40, "nested_outer"),
        # Same insertion with unknown predicted orientation: B1 must abstain.
        _known("unknown_a", 700, 740, "copy_unknown", "Fam_SINE_A", "ins_unknown", "Fam_SINE_A", "+", "Fam_SINE_A", None, 40, "unknown_orientation"),
        _known("unknown_b", 755, 795, "copy_unknown", "Fam_SINE_A", "ins_unknown", "Fam_SINE_A", "+", "Fam_SINE_A", "+", 40, "unknown_orientation"),
        # Three independent insertions form a B1 chain; connected components over-merge transitively.
        _known("chain_a", 900, 940, "copy_chain_a", "Fam_LINE_A", "ins_chain_a", "Fam_LINE_A", "+", "Fam_LINE_A", "+", 40, "transitive_chain"),
        _known("chain_b", 950, 990, "copy_chain_b", "Fam_LINE_A", "ins_chain_b", "Fam_LINE_A", "+", "Fam_LINE_A", "+", 42, "transitive_chain"),
        _known("chain_c", 1000, 1040, "copy_chain_c", "Fam_LINE_A", "ins_chain_c", "Fam_LINE_A", "+", "Fam_LINE_A", "+", 38, "transitive_chain"),
        # Same insertion beyond the candidate window: recall denominator must expose this miss.
        _known("far_a", 1200, 1240, "copy_far", "Fam_RC_A", "ins_far", "Fam_RC_A", "+", "Fam_RC_A", "+", 40, "far_same_insertion"),
        _known("far_b", 1400, 1440, "copy_far", "Fam_RC_A", "ins_far", "Fam_RC_A", "+", "Fam_RC_A", "+", 40, "far_same_insertion"),
        # Unresolved truth is intentionally near and prediction-compatible; it is excluded from FP/FN.
        _unresolved("unresolved_a", 1500, 1540, "copy_unresolved", "Fam_LINE_A", "Fam_LINE_A", "+", 40, "unresolved_truth"),
        _unresolved("unresolved_b", 1550, 1590, "copy_unresolved", "Fam_LINE_A", "Fam_LINE_A", "+", 40, "unresolved_truth"),
    ]


def validate_fragments(fragments: Sequence[Fragment]) -> None:
    """Validate contract invariants that change interpretation of the screen."""

    ids: Set[str] = set()
    for fragment in fragments:
        if fragment.fragment_id in ids:
            raise ValueError("duplicate fragment_id: %s" % fragment.fragment_id)
        ids.add(fragment.fragment_id)
        if fragment.start < 0 or fragment.end <= fragment.start:
            raise ValueError("invalid half-open interval for %s" % fragment.fragment_id)
        if fragment.truth_status not in (KNOWN, UNRESOLVED):
            raise ValueError("invalid truth status for %s" % fragment.fragment_id)
        if fragment.truth_status == KNOWN and not fragment.parent_insertion_id:
            raise ValueError("known fragment has no parent_insertion_id: %s" % fragment.fragment_id)
        if fragment.truth_status == UNRESOLVED and fragment.parent_insertion_id is not None:
            raise ValueError("unresolved fragment has a parent identity: %s" % fragment.fragment_id)
        if fragment.truth_status == UNRESOLVED and (fragment.truth_family is not None or fragment.truth_orientation is not None):
            raise ValueError("unresolved fragment has truth family/orientation: %s" % fragment.fragment_id)
        if fragment.predicted_length is not None and fragment.predicted_length <= 0:
            raise ValueError("predicted_length must be positive or null: %s" % fragment.fragment_id)
        if fragment.annotation_provenance != ENGINEERING_ONLY:
            raise ValueError("fixture feature provenance must remain ENGINEERING_ONLY: %s" % fragment.fragment_id)


def interval_snapshot(fragments: Sequence[Fragment]) -> Dict[str, Tuple[str, int, int]]:
    return {f.fragment_id: (f.contig, f.start, f.end) for f in fragments}


def assert_intervals_unchanged(before: Mapping[str, Tuple[str, int, int]], after: Sequence[Fragment]) -> None:
    """Ensure graph preparation never changes material coordinates."""

    current = interval_snapshot(after)
    if dict(before) != current:
        raise AssertionError("fragment intervals changed during linking preparation")


def assign_group_splits(
    fragments: Sequence[Fragment], group_field: str, seed: int = 42
) -> Dict[str, str]:
    """Assign whole source-copy or family groups to splits, never fragments."""

    if group_field not in ("source_copy_id", "family_group_id"):
        raise ValueError("group_field must be source_copy_id or family_group_id")
    groups = sorted({str(getattr(fragment, group_field)) for fragment in fragments})
    random.Random(seed).shuffle(groups)
    n = len(groups)
    if n == 0:
        return {}
    n_train = max(1, int(round(n * 0.6)))
    n_dev = max(1, int(round(n * 0.2))) if n >= 3 else 0
    if n_train + n_dev >= n and n >= 3:
        n_dev = max(1, n - n_train - 1)
    assignments: Dict[str, str] = {}
    for index, group in enumerate(groups):
        if index < n_train:
            assignments[group] = "train"
        elif index < n_train + n_dev:
            assignments[group] = "dev"
        else:
            assignments[group] = "test"
    return assignments


def build_split_role_records(
    fragments: Sequence[Fragment], source_splits: Mapping[str, str], family_splits: Mapping[str, str]
) -> List[dict]:
    """Materialize fragment->role rows before checking group leakage."""

    return [
        {
            "fragment_id": fragment.fragment_id,
            "source_copy_id": fragment.source_copy_id,
            "source_copy_split": source_splits[fragment.source_copy_id],
            "family_group_id": fragment.family_group_id,
            "family_group_split": family_splits[fragment.family_group_id],
        }
        for fragment in fragments
    ]


def validate_group_split(records: Sequence[Mapping[str, object]], group_field: str, role_field: str) -> None:
    """Check the emitted fragment->role records, rather than a group map."""

    observed: Dict[str, Set[str]] = {}
    for record in records:
        if group_field not in record or role_field not in record:
            raise ValueError("split record lacks %s or %s" % (group_field, role_field))
        group = str(record[group_field])
        role = str(record[role_field])
        if role not in SPLITS:
            raise ValueError("invalid split role %s for group %s" % (role, group))
        observed.setdefault(group, set()).add(role)
    leaked = {group: sorted(values) for group, values in observed.items() if len(values) != 1}
    if leaked:
        raise AssertionError("group split leakage in %s/%s: %s" % (group_field, role_field, leaked))


def build_candidate_pairs(fragments: Sequence[Fragment], max_distance_bp: int) -> List[Tuple[Fragment, Fragment]]:
    """Enumerate nearby/overlapping pairs while retaining nested intervals."""

    if max_distance_bp < 0:
        raise ValueError("max_distance_bp must be non-negative")
    ordered = sorted(fragments, key=lambda f: (f.contig, f.start, f.end, f.fragment_id))
    pairs: List[Tuple[Fragment, Fragment]] = []
    for i, left in enumerate(ordered):
        for right in ordered[i + 1 :]:
            if right.contig != left.contig:
                if right.contig > left.contig:
                    break
                continue
            signed_gap = right.start - left.end
            if signed_gap > max_distance_bp:
                # Starts are sorted, so later fragments cannot re-enter the window.
                break
            # signed_gap < 0 means overlap; this includes nested insertions.
            pairs.append((left, right))
    return pairs


def _truth_pair(left: Fragment, right: Fragment) -> Tuple[str, Optional[bool]]:
    if left.truth_status != KNOWN or right.truth_status != KNOWN:
        return "unresolved", None
    same = left.parent_insertion_id == right.parent_insertion_id
    return ("same_insertion" if same else "different_insertion"), same


def _predicted_length_ratio(left: Fragment, right: Fragment) -> Optional[float]:
    if left.predicted_length is None or right.predicted_length is None:
        return None
    larger = max(left.predicted_length, right.predicted_length)
    if larger <= 0:
        return None
    return min(left.predicted_length, right.predicted_length) / float(larger)


def _pair_split_role(
    left_group: str, right_group: str, assignments: Optional[Mapping[str, str]]
) -> Tuple[Optional[str], Optional[str], str]:
    if assignments is None:
        return None, None, "NOT_APPLIED"
    left_role = assignments[left_group]
    right_role = assignments[right_group]
    if left_role == right_role:
        return left_role, right_role, "ELIGIBLE_SAME_ROLE"
    return left_role, right_role, "EXCLUDED_CROSS_SPLIT"


def pair_row(
    left: Fragment,
    right: Fragment,
    max_distance_bp: int,
    min_length_ratio: float,
    source_splits: Optional[Mapping[str, str]] = None,
    family_splits: Optional[Mapping[str, str]] = None,
) -> dict:
    """Build one candidate row; truth and predicted features stay namespaced."""

    signed_gap = right.start - left.end
    distance = max(0, signed_gap)
    overlap = max(0, min(left.end, right.end) - max(left.start, right.start))
    truth_status, truth_same = _truth_pair(left, right)
    ratio = _predicted_length_ratio(left, right)
    left_source_role, right_source_role, source_gate = _pair_split_role(
        left.source_copy_id, right.source_copy_id, source_splits
    )
    left_family_role, right_family_role, family_gate = _pair_split_role(
        left.family_group_id, right.family_group_id, family_splits
    )
    if source_gate == "NOT_APPLIED" or family_gate == "NOT_APPLIED":
        edge_split_gate = "NOT_APPLIED"
    elif source_gate == "ELIGIBLE_SAME_ROLE" and family_gate == "ELIGIBLE_SAME_ROLE":
        edge_split_gate = "ELIGIBLE_SAME_ROLE"
    else:
        edge_split_gate = "EXCLUDED_CROSS_SPLIT"
    family_equal = bool(left.predicted_family and right.predicted_family and left.predicted_family == right.predicted_family)
    orientation_equal = bool(
        left.predicted_orientation
        and right.predicted_orientation
        and left.predicted_orientation == right.predicted_orientation
    )
    b1_reasons: List[str] = []
    b1_edge = True
    if distance > max_distance_bp:
        b1_edge = False
        b1_reasons.append("distance_outside_window")
    if not family_equal:
        b1_edge = False
        b1_reasons.append("predicted_family_missing_or_mismatch")
    if not orientation_equal:
        b1_edge = False
        b1_reasons.append("predicted_orientation_missing_or_mismatch")
    if ratio is None or ratio < min_length_ratio:
        b1_edge = False
        b1_reasons.append("predicted_length_missing_or_incompatible")
    pair_id = "%s__%s" % (left.fragment_id, right.fragment_id)
    return {
        "pair_id": pair_id,
        "left_fragment_id": left.fragment_id,
        "right_fragment_id": right.fragment_id,
        "candidate": True,
        "distance_bp": distance,
        "signed_gap_bp": signed_gap,
        "overlap_bp": overlap,
        "predicted_length_left": left.predicted_length,
        "predicted_length_right": right.predicted_length,
        "predicted_length_ratio": ratio,
        "predicted_family_left": left.predicted_family,
        "predicted_family_right": right.predicted_family,
        "predicted_orientation_left": left.predicted_orientation,
        "predicted_orientation_right": right.predicted_orientation,
        "predicted_family_equal": family_equal,
        "predicted_orientation_equal": orientation_equal,
        "left_source_copy_role": left_source_role,
        "right_source_copy_role": right_source_role,
        "source_copy_pair_role": left_source_role if source_gate == "ELIGIBLE_SAME_ROLE" else None,
        "source_copy_pair_gate": source_gate,
        "left_family_group_role": left_family_role,
        "right_family_group_role": right_family_role,
        "family_group_pair_role": left_family_role if family_gate == "ELIGIBLE_SAME_ROLE" else None,
        "family_group_pair_gate": family_gate,
        "edge_split_gate": edge_split_gate,
        "truth_pair_status": truth_status,
        "truth_same_insertion": truth_same,
        "truth_parent_left": left.parent_insertion_id,
        "truth_parent_right": right.parent_insertion_id,
        "case_left": left.case,
        "case_right": right.case,
        "B0_distance_edge": distance <= max_distance_bp,
        "B1_rule_edge": b1_edge,
        "B1_rule_reasons": ";".join(b1_reasons) if b1_reasons else "all_rules_pass",
    }


class UnionFind:
    def __init__(self, items: Iterable[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            nxt = self.parent[item]
            self.parent[item] = root
            item = nxt
        return root

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root

    def components(self) -> List[List[str]]:
        grouped: Dict[str, List[str]] = {}
        for item in sorted(self.parent):
            grouped.setdefault(self.find(item), []).append(item)
        return sorted((sorted(items) for items in grouped.values()), key=lambda values: values[0])


def components_for_edges(fragments: Sequence[Fragment], rows: Sequence[Mapping[str, object]], edge_key: str) -> List[List[str]]:
    uf = UnionFind(f.fragment_id for f in fragments)
    for row in rows:
        if bool(row[edge_key]):
            uf.union(str(row["left_fragment_id"]), str(row["right_fragment_id"]))
    return uf.components()


def _safe_div(numerator: int, denominator: int) -> Optional[float]:
    return numerator / float(denominator) if denominator else None


def evaluate_method(
    fragments: Sequence[Fragment], rows: Sequence[Mapping[str, object]], edge_key: str, method: str
) -> dict:
    known_candidates = [row for row in rows if row["truth_pair_status"] != "unresolved"]
    same_candidates = [row for row in known_candidates if row["truth_pair_status"] == "same_insertion"]
    different_candidates = [row for row in known_candidates if row["truth_pair_status"] == "different_insertion"]
    unresolved_candidates = [row for row in rows if row["truth_pair_status"] == "unresolved"]
    predicted = [row for row in rows if bool(row[edge_key])]
    tp = sum(1 for row in same_candidates if bool(row[edge_key]))
    fp = sum(1 for row in different_candidates if bool(row[edge_key]))
    fn = sum(1 for row in same_candidates if not bool(row[edge_key]))
    unresolved_predicted_edges = sum(1 for row in unresolved_candidates if bool(row[edge_key]))
    components = components_for_edges(fragments, rows, edge_key)
    by_id = {f.fragment_id: f for f in fragments}
    overmerged_components: List[List[str]] = []
    for component in components:
        parents = {
            by_id[item].parent_insertion_id
            for item in component
            if by_id[item].truth_status == KNOWN and by_id[item].parent_insertion_id is not None
        }
        if len(parents) > 1:
            overmerged_components.append(component)
    chain_ids = {"chain_a", "chain_b", "chain_c"}
    chain_component = next((component for component in components if chain_ids.issubset(component)), [])
    chain_parents = {
        by_id[item].parent_insertion_id
        for item in chain_component
        if by_id[item].truth_status == KNOWN and by_id[item].parent_insertion_id is not None
    }
    return {
        "method": method,
        "candidate_pairs": len(rows),
        "predicted_edges": len(predicted),
        "known_candidate_pairs": len(known_candidates),
        "same_insertion_candidate_pairs": len(same_candidates),
        "different_insertion_candidate_pairs": len(different_candidates),
        "unresolved_candidate_pairs_excluded": len(unresolved_candidates),
        "edge_true_positive": tp,
        "edge_false_positive_known_different_insertion": fp,
        "edge_false_negative_within_candidates": fn,
        "edge_precision_known_only": _safe_div(tp, tp + fp),
        "edge_recall_given_candidate": _safe_div(tp, tp + fn),
        "unresolved_predicted_edges_excluded": unresolved_predicted_edges,
        "unresolved_never_counted_as_negative": all(
            row["truth_pair_status"] == "unresolved" or row["truth_pair_status"] in ("same_insertion", "different_insertion")
            for row in rows
        ),
        "component_count": len(components),
        "overmerged_component_count": len(overmerged_components),
        "overmerged_component_rate": _safe_div(len(overmerged_components), len(components)),
        "overmerged_components": overmerged_components,
        "transitive_chain_false_merge_detected": len(chain_component) > 0 and len(chain_parents) > 1,
        "components": components,
    }


def evaluate(
    fragments: Sequence[Fragment], rows: Sequence[Mapping[str, object]], max_distance_bp: int
) -> dict:
    all_known_pairs = [
        (left, right)
        for left, right in itertools.combinations(fragments, 2)
        if left.truth_status == KNOWN and right.truth_status == KNOWN
    ]
    all_same = [
        (left, right)
        for left, right in all_known_pairs
        if left.parent_insertion_id == right.parent_insertion_id
    ]
    candidate_same = [row for row in rows if row["truth_pair_status"] == "same_insertion"]
    denominator = len(all_same)
    numerator = len(candidate_same)
    before = interval_snapshot(fragments)
    assert_intervals_unchanged(before, fragments)
    return {
        "contract_version": CONTRACT_VERSION,
        "fixture_provenance": ENGINEERING_ONLY,
        "candidate_window_bp": max_distance_bp,
        "candidate_recall_denominator_all_known_same_insertion_pairs": denominator,
        "candidate_recall_numerator_same_insertion_pairs_in_candidates": numerator,
        "candidate_recall": _safe_div(numerator, denominator),
        "unresolved_pairs_in_candidate_table": sum(1 for row in rows if row["truth_pair_status"] == "unresolved"),
        "gap_filling_applied": False,
        "material_mask_changed": False,
        "material_mask_input": None,
        "intervals_unchanged": True,
        "methods": {
            "B0_distance": evaluate_method(fragments, rows, "B0_distance_edge", "B0_distance"),
            "B1_predicted_family_orientation_length": evaluate_method(
                fragments, rows, "B1_rule_edge", "B1_predicted_family_orientation_length"
            ),
        },
        "scientific_status": "ENGINEERING_ONLY; no model score and no biological claim",
    }


PAIR_FIELDS = [
    "pair_id",
    "left_fragment_id",
    "right_fragment_id",
    "candidate",
    "distance_bp",
    "signed_gap_bp",
    "overlap_bp",
    "predicted_length_left",
    "predicted_length_right",
    "predicted_length_ratio",
    "predicted_family_left",
    "predicted_family_right",
    "predicted_orientation_left",
    "predicted_orientation_right",
    "predicted_family_equal",
    "predicted_orientation_equal",
    "left_source_copy_role",
    "right_source_copy_role",
    "source_copy_pair_role",
    "source_copy_pair_gate",
    "left_family_group_role",
    "right_family_group_role",
    "family_group_pair_role",
    "family_group_pair_gate",
    "edge_split_gate",
    "truth_pair_status",
    "truth_same_insertion",
    "truth_parent_left",
    "truth_parent_right",
    "case_left",
    "case_right",
    "B0_distance_edge",
    "B1_rule_edge",
    "B1_rule_reasons",
]


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_tsv(path: Path, rows: Sequence[Mapping[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _text(row.get(field)) for field in fields})


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: Path, records: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def write_clusters(path: Path, fragments: Sequence[Fragment], components: Sequence[Sequence[str]]) -> None:
    by_id = {f.fragment_id: f for f in fragments}
    rows: List[dict] = []
    for cluster_id, component in enumerate(components):
        for fragment_id in component:
            fragment = by_id[fragment_id]
            rows.append(
                {
                    "cluster_id": cluster_id,
                    "fragment_id": fragment_id,
                    "truth_status": fragment.truth_status,
                    "truth_parent_insertion_id": fragment.parent_insertion_id,
                    "case": fragment.case,
                }
            )
    write_tsv(path, rows, ["cluster_id", "fragment_id", "truth_status", "truth_parent_insertion_id", "case"])


def contract_record(max_distance_bp: int, min_length_ratio: float) -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "ENGINEERING_ONLY",
        "interval_convention": "[start,end)",
        "fragment_identity": ["fragment_id", "contig", "start", "end"],
        "truth_namespace": {
            "parent_insertion_id": "independent insertion identity; null only when truth_status=unresolved",
            "truth_status": [KNOWN, UNRESOLVED],
            "truth_same_insertion": "null whenever either endpoint is unresolved",
        },
        "prediction_namespace": {
            "predicted_family": "feature supplied by a detector; null means unknown",
            "predicted_orientation": "feature supplied by a detector; null means unknown",
            "predicted_length": "positive detector feature; not substituted with interval length",
        },
        "split_contract": {
            "source_copy_group": "source_copy_id; all fragments from one source copy stay in one split",
            "family_group": "family_group_id; all rows in one family group stay in one split",
            "split_names": list(SPLITS),
            "note": "source-copy and family-group split assignments are emitted separately",
            "pair_gate": "a role-specific edge may enter a role only when both endpoints share that role; otherwise EXCLUDED_CROSS_SPLIT",
        },
        "edge_rules": {
            "B0_distance": "candidate distance_bp <= %d" % max_distance_bp,
            "B1_predicted_family_orientation_length": {
                "distance_bp": "<= %d" % max_distance_bp,
                "predicted_family": "both known and equal",
                "predicted_orientation": "both known and equal",
                "predicted_length_ratio": ">= %.3f" % min_length_ratio,
            },
        },
        "decode_policy": {
            "fill_gap": False,
            "change_material_mask": False,
            "output": "association edges and connected components only; no merged interval is emitted",
            "role_gated_edge_files": ["edges_B0_distance.tsv", "edges_B1_predicted_rules.tsv"],
            "all_fixture_edge_files": ["edges_B0_distance_all_fixture.tsv", "edges_B1_predicted_rules_all_fixture.tsv"],
        },
        "future_stages": {
            "M2": {
                "status": "INPUT_CONTRACT_ONLY",
                "requires": "verified model edge scores and an approved training/evaluation split",
                "real_truth_gap": "no verified insertion-level ground truth supplied in Phase0",
            },
            "M3": {
                "status": "INPUT_CONTRACT_ONLY",
                "requires": "context-aware sequence evidence and an independent truth panel",
                "real_truth_gap": "no verified biological fragment-to-insertion linkage truth supplied in Phase0",
            },
        },
    }


def run(out_dir: Path, max_distance_bp: int = 25, min_length_ratio: float = 0.5, seed: int = 42) -> dict:
    """Run the toy contract screen and write only small engineering outputs."""

    fragments = make_fixture()
    validate_fragments(fragments)
    before = interval_snapshot(fragments)
    source_splits = assign_group_splits(fragments, "source_copy_id", seed)
    family_splits = assign_group_splits(fragments, "family_group_id", seed)
    split_rows = build_split_role_records(fragments, source_splits, family_splits)
    validate_group_split(split_rows, "source_copy_id", "source_copy_split")
    validate_group_split(split_rows, "family_group_id", "family_group_split")
    candidates = build_candidate_pairs(fragments, max_distance_bp)
    rows = [
        pair_row(left, right, max_distance_bp, min_length_ratio, source_splits, family_splits)
        for left, right in candidates
    ]
    summary = evaluate(fragments, rows, max_distance_bp)
    assert_intervals_unchanged(before, fragments)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "contract.json", contract_record(max_distance_bp, min_length_ratio))
    write_json(out_dir / "fixture_metadata.json", {
        "fixture_provenance": ENGINEERING_ONLY,
        "manual_features": ["predicted_family", "predicted_orientation", "predicted_length", "truth_parent_insertion_id"],
        "family_id_policy": "synthetic Fam_* identifiers; no coarse class is presented as a family",
        "max_distance_bp": max_distance_bp,
        "min_length_ratio": min_length_ratio,
        "seed_for_group_split": seed,
        "cases": sorted({fragment.case for fragment in fragments}),
    })
    write_jsonl(out_dir / "fixture_fragments.jsonl", (fragment.to_record() for fragment in fragments))
    split_rows = sorted(split_rows, key=lambda row: str(row["fragment_id"]))
    write_tsv(out_dir / "split_assignments.tsv", split_rows, [
        "fragment_id", "source_copy_id", "source_copy_split", "family_group_id", "family_group_split"
    ])
    write_tsv(out_dir / "pairs.tsv", rows, PAIR_FIELDS)
    b0_rows_all = [row for row in rows if bool(row["B0_distance_edge"])]
    b1_rows_all = [row for row in rows if bool(row["B1_rule_edge"])]
    b0_rows = [row for row in b0_rows_all if row["edge_split_gate"] == "ELIGIBLE_SAME_ROLE"]
    b1_rows = [row for row in b1_rows_all if row["edge_split_gate"] == "ELIGIBLE_SAME_ROLE"]
    write_tsv(out_dir / "edges_B0_distance.tsv", b0_rows, PAIR_FIELDS)
    write_tsv(out_dir / "edges_B1_predicted_rules.tsv", b1_rows, PAIR_FIELDS)
    write_tsv(out_dir / "edges_B0_distance_all_fixture.tsv", b0_rows_all, PAIR_FIELDS)
    write_tsv(out_dir / "edges_B1_predicted_rules_all_fixture.tsv", b1_rows_all, PAIR_FIELDS)
    b0_role_rows = [row for row in b0_rows_all if row["edge_split_gate"] == "ELIGIBLE_SAME_ROLE"]
    b1_role_rows = [row for row in b1_rows_all if row["edge_split_gate"] == "ELIGIBLE_SAME_ROLE"]
    b0_components = components_for_edges(fragments, b0_role_rows, "B0_distance_edge")
    b1_components = components_for_edges(fragments, b1_role_rows, "B1_rule_edge")
    write_clusters(out_dir / "clusters_B0_distance.tsv", fragments, b0_components)
    write_clusters(out_dir / "clusters_B1_predicted_rules.tsv", fragments, b1_components)
    write_clusters(
        out_dir / "clusters_B0_distance_all_fixture.tsv",
        fragments,
        components_for_edges(fragments, b0_rows_all, "B0_distance_edge"),
    )
    write_clusters(
        out_dir / "clusters_B1_predicted_rules_all_fixture.tsv",
        fragments,
        components_for_edges(fragments, b1_rows_all, "B1_rule_edge"),
    )
    summary["split_group_leakage"] = {"source_copy_id": False, "family_group_id": False}
    summary["metric_scope"] = "all fixture pairs; engineering diagnostic, not a heldout evaluation"
    summary["edge_file_policy"] = "edges_B0_distance.tsv and edges_B1_predicted_rules.tsv keep only same-role pairs under both split views; *_all_fixture.tsv preserves all toy predictions"
    summary["output_policy"] = "edges/components only; input intervals are immutable and no gap/mask output exists"
    write_json(out_dir / "metrics.json", summary)
    report = {
        "report_type": "engineering_fixture",
        "contract_version": CONTRACT_VERSION,
        "status": "PASS_ENGINEERING_ONLY",
        "fixture_fragments": len(fragments),
        "candidate_pairs": len(rows),
        "metric_scope": "all fixture pairs; engineering diagnostic, not a heldout evaluation",
        "role_gated_B0_edges": len(b0_rows),
        "role_gated_B1_edges": len(b1_rows),
        "candidate_recall": summary["candidate_recall"],
        "unresolved_pairs_excluded": summary["unresolved_pairs_in_candidate_table"],
        "B0_overmerged_components": summary["methods"]["B0_distance"]["overmerged_component_count"],
        "B1_overmerged_components": summary["methods"]["B1_predicted_family_orientation_length"]["overmerged_component_count"],
        "B1_transitive_chain_false_merge_detected": summary["methods"]["B1_predicted_family_orientation_length"]["transitive_chain_false_merge_detected"],
        "intervals_unchanged": summary["intervals_unchanged"],
        "gap_filling_applied": summary["gap_filling_applied"],
        "material_mask_changed": summary["material_mask_changed"],
        "M2": "INPUT_CONTRACT_ONLY; no model or score",
        "M3": "INPUT_CONTRACT_ONLY; no model or score",
    }
    write_json(out_dir / "engineering_report.json", report)
    return summary


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="reports/FRAGMENT-LINKING-PHASE0-20260914/toy_run",
        help="small output directory for the synthetic fixture",
    )
    parser.add_argument("--max-distance-bp", type=int, default=25)
    parser.add_argument("--min-length-ratio", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    summary = run(Path(args.out_dir), args.max_distance_bp, args.min_length_ratio, args.seed)
    print(json.dumps({
        "status": "PASS_ENGINEERING_ONLY",
        "out_dir": str(Path(args.out_dir)),
        "candidate_recall": summary["candidate_recall"],
        "B1_transitive_chain_false_merge_detected": summary["methods"]["B1_predicted_family_orientation_length"]["transitive_chain_false_merge_detected"],
        "intervals_unchanged": summary["intervals_unchanged"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
