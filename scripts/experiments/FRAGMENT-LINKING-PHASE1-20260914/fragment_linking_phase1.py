#!/usr/bin/env python3
"""Bounded fragment-linking baseline on an independent synthetic fixture.

Phase 1 moves one step beyond the Phase 0 pair contract.  It creates small
semi-simulated *independent insertions* (each fragment sequence has its own
deterministic seed), keeps truth identities separate from predicted features,
and compares distance/rule edges with a tiny logistic pair baseline.  The
baseline is fit on TRAIN, calibrated on CAL under a fixed false-accept budget,
and applied to EVAL.

This remains ``ENGINEERING_ONLY``.  It does not use a consensus crop as an
independent copy, does not call an encoder, does not use random embeddings,
does not fill a gap, and does not alter a material mask.  Real M2/M3 scores
require an identity-verified manifest and an approved Slurm run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


CONTRACT_VERSION = "fragment-linking-phase1-v1"
ENGINEERING_ONLY = "ENGINEERING_ONLY"
SEED = 42
SPLITS = ("train", "cal", "eval")
KNOWN = "known"
UNRESOLVED = "unresolved"
AMBIGUOUS = "ambiguous"
BACKGROUND = "background"
UNRESOLVED_STATUSES = {UNRESOLVED, AMBIGUOUS, BACKGROUND}
ALPHABET = "ACGT"


@dataclass(frozen=True)
class Fragment:
    fragment_id: str
    host_id: str
    contig: str
    start: int
    end: int
    role: str
    source_copy_id: str
    homology_component_id: str
    truth_parent_insertion_id: Optional[str]
    truth_status: str
    truth_family: Optional[str]
    truth_orientation: Optional[str]
    predicted_family: Optional[str]
    predicted_orientation: Optional[str]
    predicted_length: Optional[int]
    sequence: str
    sequence_origin: str = "independent_insertion_semisim"
    annotation_provenance: str = ENGINEERING_ONLY

    @property
    def interval(self) -> Tuple[int, int]:
        return self.start, self.end

    @property
    def observed_length(self) -> int:
        return self.end - self.start

    def to_record(self) -> dict:
        return {
            "fragment_id": self.fragment_id,
            "host_id": self.host_id,
            "contig": self.contig,
            "interval": {"start": self.start, "end": self.end, "convention": "[start,end)"},
            "role": self.role,
            "source_copy_id": self.source_copy_id,
            "homology_component_id": self.homology_component_id,
            "truth": {
                "status": self.truth_status,
                "parent_insertion_id": self.truth_parent_insertion_id,
                "family": self.truth_family,
                "orientation": self.truth_orientation,
            },
            "prediction": {
                "family": self.predicted_family,
                "orientation": self.predicted_orientation,
                "length": self.predicted_length,
            },
            "sequence": self.sequence,
            "sequence_origin": self.sequence_origin,
            "annotation_provenance": self.annotation_provenance,
        }


def deterministic_sequence(label: str, length: int = 96) -> str:
    """Create a sequence for an independent synthetic fragment.

    The seed includes the fragment ID, so no two records are made by slicing a
    shared consensus.  This is a fixture generator, never a biological model.
    """

    digest = hashlib.sha256(label.encode("utf-8")).digest()
    return "".join(ALPHABET[digest[index % len(digest)] % len(ALPHABET)] for index in range(length))


def known_fragment(
    fragment_id: str,
    host_id: str,
    contig: str,
    start: int,
    end: int,
    role: str,
    source_copy_id: str,
    homology_component_id: str,
    parent: str,
    family: str,
    orientation: str,
    predicted_family: Optional[str] = None,
    predicted_orientation: Optional[str] = None,
    predicted_length: Optional[int] = None,
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        host_id=host_id,
        contig=contig,
        start=start,
        end=end,
        role=role,
        source_copy_id=source_copy_id,
        homology_component_id=homology_component_id,
        truth_parent_insertion_id=parent,
        truth_status=KNOWN,
        truth_family=family,
        truth_orientation=orientation,
        predicted_family=family if predicted_family is None else predicted_family,
        predicted_orientation=orientation if predicted_orientation is None else predicted_orientation,
        predicted_length=end - start if predicted_length is None else predicted_length,
        sequence=deterministic_sequence(fragment_id),
    )


def unresolved_fragment(
    fragment_id: str,
    host_id: str,
    contig: str,
    start: int,
    end: int,
    role: str,
    predicted_family: Optional[str],
    predicted_orientation: Optional[str],
) -> Fragment:
    return Fragment(
        fragment_id=fragment_id,
        host_id=host_id,
        contig=contig,
        start=start,
        end=end,
        role=role,
        source_copy_id="",
        homology_component_id="",
        truth_parent_insertion_id=None,
        truth_status=UNRESOLVED,
        truth_family=None,
        truth_orientation=None,
        predicted_family=predicted_family,
        predicted_orientation=predicted_orientation,
        predicted_length=end - start,
        sequence=deterministic_sequence(fragment_id),
    )


def add_insertion(
    output: List[Fragment],
    role: str,
    host_id: str,
    parent: str,
    family: str,
    base: int,
    orientation: str = "+",
    gap: int = 15,
    prediction_overrides: Optional[Mapping[str, Optional[str]]] = None,
) -> None:
    """Add two fragments for one independent insertion identity."""

    source_copy = "copy_%s_%s" % (role, parent)
    homology = "hom_%s_%s" % (role, parent)
    overrides = dict(prediction_overrides or {})
    first_end = base + 40
    second_start = first_end + gap
    output.append(known_fragment(
        "%s_left" % parent, host_id, "chr1", base, first_end, role,
        source_copy, homology, parent, family, orientation,
        predicted_family=overrides.get("family"),
        predicted_orientation=overrides.get("orientation"),
        predicted_length=40,
    ))
    output.append(known_fragment(
        "%s_right" % parent, host_id, "chr1", second_start, second_start + 40, role,
        source_copy, homology, parent, family, orientation,
        predicted_family=overrides.get("family"),
        predicted_orientation=overrides.get("orientation"),
        predicted_length=40,
    ))


def make_fixture() -> List[Fragment]:
    """Build the bounded independent-insertion engineering fixture."""

    rows: List[Fragment] = []

    # TRAIN: independent insertions give the tiny pair learner both positives
    # and same-family adjacent negatives.  All train material is on one host.
    for index in range(6):
        family = "Fam_LINE_A" if index < 4 else "Fam_LTR_B"
        add_insertion(rows, "train", "host_train", "tr_%02d" % index, family, 1000 + index * 500)
    rows.extend([
        known_fragment("tr_adj_a", "host_train", "chr1", 4030, 4070, "train",
                       "copy_train_adj_a", "hom_train_adj_a", "tr_adj_a", "Fam_LINE_A", "+"),
        known_fragment("tr_adj_b", "host_train", "chr1", 4080, 4120, "train",
                       "copy_train_adj_b", "hom_train_adj_b", "tr_adj_b", "Fam_LINE_A", "+"),
    ])

    # CAL: independent hosts and identities.  They provide the fixed
    # false-accept gate; the toy count is intentionally below the claim-grade
    # minimum of 100 negatives recorded in the contract.
    for index in range(3):
        add_insertion(rows, "cal", "host_cal", "cal_%02d" % index, "Fam_LINE_A", 1000 + index * 500)
    rows.extend([
        known_fragment("cal_adj_a", "host_cal", "chr1", 2530, 2570, "cal",
                       "copy_cal_adj_a", "hom_cal_adj_a", "cal_adj_a", "Fam_LINE_A", "+"),
        known_fragment("cal_adj_b", "host_cal", "chr1", 2580, 2620, "cal",
                       "copy_cal_adj_b", "hom_cal_adj_b", "cal_adj_b", "Fam_LINE_A", "+"),
        known_fragment("cal_adj_c", "host_cal", "chr1", 2630, 2670, "cal",
                       "copy_cal_adj_c", "hom_cal_adj_c", "cal_adj_c", "Fam_LINE_A", "+"),
    ])

    # EVAL: one ordinary pair, one nested insertion and one pair with missing
    # orientation.  The truth is explicit and independent of predictions.
    add_insertion(rows, "eval", "host_eval", "ev_regular", "Fam_LINE_A", 100)
    # Empty prediction is intentional unknown orientation; the truth remains
    # known and must be separated from the prediction namespace.
    add_insertion(rows, "eval", "host_eval", "ev_unknown", "Fam_SINE_C", 300,
                  prediction_overrides={"orientation": ""})
    rows.extend([
        # Nested insertion: outer identity is separated by an inner identity.
        known_fragment("ev_outer_left", "host_eval", "chr1", 500, 540, "eval",
                       "copy_eval_outer", "hom_eval_outer", "ev_outer", "Fam_LINE_A", "+"),
        known_fragment("ev_inner", "host_eval", "chr1", 545, 575, "eval",
                       "copy_eval_inner", "hom_eval_inner", "ev_inner", "Fam_DNA_D", "+"),
        known_fragment("ev_outer_right", "host_eval", "chr1", 580, 620, "eval",
                       "copy_eval_outer", "hom_eval_outer", "ev_outer", "Fam_LINE_A", "+"),
        # Three independent insertions whose rule edges form a transitive
        # chain.  This exposes component over-merging after pair prediction.
        known_fragment("ev_chain_a", "host_eval", "chr1", 900, 940, "eval",
                       "copy_eval_chain_a", "hom_eval_chain_a", "ev_chain_a", "Fam_LINE_A", "+"),
        known_fragment("ev_chain_b", "host_eval", "chr1", 955, 995, "eval",
                       "copy_eval_chain_b", "hom_eval_chain_b", "ev_chain_b", "Fam_LINE_A", "+"),
        known_fragment("ev_chain_c", "host_eval", "chr1", 1010, 1050, "eval",
                       "copy_eval_chain_c", "hom_eval_chain_c", "ev_chain_c", "Fam_LINE_A", "+"),
        # Same family and nearby coordinate, but different host: never a
        # candidate edge.  Host identity is kept explicit in the record.
        known_fragment("host2_near", "host_eval_2", "chr1", 110, 150, "eval",
                       "copy_eval2_near", "hom_eval2_near", "ev_host2", "Fam_LINE_A", "+"),
        # Empty source/homology IDs carry no insertion truth.  The prediction
        # is intentionally compatible so the edge is tested but excluded from
        # known-negative statistics.
        unresolved_fragment("ev_unresolved_a", "host_eval", "chr1", 1200, 1240, "eval", "Fam_LINE_A", "+"),
        unresolved_fragment("ev_unresolved_b", "host_eval", "chr1", 1250, 1290, "eval", "Fam_LINE_A", "+"),
    ])
    return rows


def validate_fragments(fragments: Sequence[Fragment]) -> None:
    ids = set()
    for fragment in fragments:
        if fragment.fragment_id in ids:
            raise ValueError("duplicate fragment_id: %s" % fragment.fragment_id)
        ids.add(fragment.fragment_id)
        if fragment.role not in SPLITS:
            raise ValueError("invalid role: %s" % fragment.role)
        if fragment.start < 0 or fragment.end <= fragment.start:
            raise ValueError("invalid half-open interval for %s" % fragment.fragment_id)
        if fragment.sequence_origin != "independent_insertion_semisim":
            raise ValueError("fixture sequence origin is not independent insertion data")
        if fragment.annotation_provenance != ENGINEERING_ONLY:
            raise ValueError("fixture provenance must remain ENGINEERING_ONLY")
        if fragment.truth_status == KNOWN:
            if not fragment.truth_parent_insertion_id or not fragment.truth_family or not fragment.truth_orientation:
                raise ValueError("known fragment has incomplete truth: %s" % fragment.fragment_id)
        elif fragment.truth_status in UNRESOLVED_STATUSES:
            if fragment.truth_parent_insertion_id is not None:
                raise ValueError("unresolved fragment has a parent identity: %s" % fragment.fragment_id)
            if fragment.truth_family is not None or fragment.truth_orientation is not None:
                raise ValueError("unresolved fragment has truth family/orientation: %s" % fragment.fragment_id)
        else:
            raise ValueError("invalid truth status: %s" % fragment.truth_status)
        if fragment.predicted_length is not None and fragment.predicted_length <= 0:
            raise ValueError("predicted length must be positive: %s" % fragment.fragment_id)


def _membership_key(fragment: Fragment, field: str) -> Optional[str]:
    value = getattr(fragment, field)
    if not value:
        return None
    if field == "source_copy_id":
        return "%s::%s" % (fragment.host_id, value)
    if field == "homology_component_id":
        return "%s::%s" % (fragment.host_id, value)
    return value


def validate_role_partition(fragments: Sequence[Fragment]) -> dict:
    """Check materialized role records; empty IDs are excluded from keys."""

    overlaps = {}
    for field in ("host_id", "source_copy_id", "homology_component_id"):
        memberships: Dict[str, set] = defaultdict(set)
        for fragment in fragments:
            key = _membership_key(fragment, field)
            if key is not None:
                memberships[key].add(fragment.role)
        bad = sorted(key for key, roles in memberships.items() if len(roles) > 1)
        overlaps[field] = {"count": len(bad), "examples": bad[:10]}
    return {
        "pass": not any(item["count"] for item in overlaps.values()),
        "group_fields": ["host_id", "source_copy_id", "homology_component_id"],
        "cross_role_overlap": overlaps,
        "empty_ids_excluded_from_group_keys": True,
    }


def _distance(left: Fragment, right: Fragment) -> Tuple[int, int]:
    overlap = max(0, min(left.end, right.end) - max(left.start, right.start))
    if overlap:
        return 0, overlap
    if left.end <= right.start:
        return right.start - left.end, 0
    return left.start - right.end, 0


def pair_record(left: Fragment, right: Fragment) -> dict:
    if left.start > right.start or (left.start == right.start and left.fragment_id > right.fragment_id):
        left, right = right, left
    distance, overlap = _distance(left, right)
    same_role = left.role == right.role
    known_truth = left.truth_status == KNOWN and right.truth_status == KNOWN
    same_insertion = None
    truth_status = "unresolved"
    if known_truth:
        truth_status = KNOWN
        same_insertion = int(left.truth_parent_insertion_id == right.truth_parent_insertion_id)
    family_match = bool(left.predicted_family and right.predicted_family and left.predicted_family == right.predicted_family)
    orientation_match = bool(
        left.predicted_orientation and right.predicted_orientation
        and left.predicted_orientation == right.predicted_orientation
    )
    if left.predicted_length and right.predicted_length:
        length_ratio = min(left.predicted_length, right.predicted_length) / float(
            max(left.predicted_length, right.predicted_length)
        )
    else:
        length_ratio = None
    b1 = bool(family_match and orientation_match and length_ratio is not None and length_ratio >= 0.5)
    return {
        "pair_id": "%s__%s" % (left.fragment_id, right.fragment_id),
        "left_id": left.fragment_id,
        "right_id": right.fragment_id,
        "host_id": left.host_id,
        "contig": left.contig,
        "left_role": left.role,
        "right_role": right.role,
        "pair_role": left.role if same_role else "",
        "cross_split_status": "SAME_ROLE" if same_role else "EXCLUDED_CROSS_SPLIT",
        "distance_bp": distance,
        "overlap_bp": overlap,
        "truth_pair_status": truth_status,
        "truth_same_insertion": same_insertion,
        "pred_family_match": int(family_match),
        "pred_orientation_match": int(orientation_match),
        "pred_length_ratio": "" if length_ratio is None else round(length_ratio, 6),
        "candidate": 1,
        "b0_link": int(same_role),
        "b1_link": int(same_role and b1),
    }


def build_pairs(fragments: Sequence[Fragment], max_distance: Optional[int] = 25) -> List[dict]:
    """Enumerate same-host/contig pairs; max_distance=None means all pairs."""

    ordered = sorted(fragments, key=lambda item: (item.host_id, item.contig, item.start, item.fragment_id))
    pairs = []
    for left, right in itertools.combinations(ordered, 2):
        if left.host_id != right.host_id or left.contig != right.contig:
            continue
        distance, _ = _distance(left, right)
        if max_distance is not None and distance > max_distance:
            continue
        pairs.append(pair_record(left, right))
    return pairs


def vector(pair: Mapping[str, object]) -> List[float]:
    ratio = float(pair["pred_length_ratio"]) if pair["pred_length_ratio"] != "" else 0.0
    return [
        1.0,
        -float(pair["distance_bp"]) / 100.0,
        float(pair["overlap_bp"]) / 40.0,
        float(pair["pred_family_match"]),
        float(pair["pred_orientation_match"]),
        ratio,
    ]


def sigmoid(value: float) -> float:
    if value < -40:
        return 0.0
    if value > 40:
        return 1.0
    return 1.0 / (1.0 + math.exp(-value))


def fit_bounded_logistic(pairs: Sequence[Mapping[str, object]], iterations: int = 300) -> dict:
    training = [
        pair for pair in pairs
        if pair["pair_role"] == "train" and pair["truth_pair_status"] == KNOWN
    ]
    if not training:
        return {"status": "NOTRUN_NO_TRAIN_PAIRS", "weights": [], "pairs": 0}
    weights = [0.0] * len(vector(training[0]))
    learning_rate = 0.15
    l2 = 0.01
    for _ in range(iterations):
        gradients = [0.0] * len(weights)
        for pair in training:
            features = vector(pair)
            label = float(pair["truth_same_insertion"])
            prediction = sigmoid(sum(weight * feature for weight, feature in zip(weights, features)))
            for index, feature in enumerate(features):
                gradients[index] += (prediction - label) * feature
        scale = 1.0 / len(training)
        for index in range(len(weights)):
            regularizer = l2 * weights[index] if index else 0.0
            weights[index] -= learning_rate * (gradients[index] * scale + regularizer)
    return {
        "status": "ENGINEERING_ONLY_FIT",
        "weights": [round(weight, 10) for weight in weights],
        "pairs": len(training),
        "iterations": iterations,
        "learning_rate": learning_rate,
        "l2": l2,
        "seed": SEED,
    }


def score_pair(pair: Mapping[str, object], weights: Sequence[float]) -> float:
    return sigmoid(sum(weight * feature for weight, feature in zip(weights, vector(pair))))


def choose_cal_threshold(pairs: Sequence[Mapping[str, object]], weights: Sequence[float], alpha: float = 0.01) -> dict:
    cal = [pair for pair in pairs if pair["pair_role"] == "cal" and pair["truth_pair_status"] == KNOWN]
    negatives = [pair for pair in cal if pair["truth_same_insertion"] == 0]
    if not negatives:
        return {
            "status": "NOTRUN_NO_CAL_NEGATIVES",
            "alpha": alpha,
            "negative_pairs": 0,
            "threshold": None,
        }
    scores = [(score_pair(pair, weights), pair) for pair in cal]
    candidates = sorted({score for score, _ in scores}, reverse=True)
    acceptable = []
    for threshold in candidates:
        false_accepts = sum(1 for score, pair in scores if score >= threshold and pair["truth_same_insertion"] == 0)
        true_accepts = sum(1 for score, pair in scores if score >= threshold and pair["truth_same_insertion"] == 1)
        rate = false_accepts / float(len(negatives))
        if rate <= alpha:
            acceptable.append((true_accepts, -threshold, threshold, false_accepts, rate))
    if not acceptable:
        return {
            "status": "ENGINEERING_ONLY_NO_ACCEPTABLE_THRESHOLD",
            "alpha": alpha,
            "negative_pairs": len(negatives),
            "threshold": math.inf,
            "false_accepts": 0,
            "false_accept_rate": 0.0,
        }
    acceptable.sort(reverse=True)
    true_accepts, _neg_threshold, threshold, false_accepts, rate = acceptable[0]
    return {
        "status": "ENGINEERING_ONLY_CALIBRATED",
        "alpha": alpha,
        "negative_pairs": len(negatives),
        "threshold": threshold,
        "false_accepts": false_accepts,
        "false_accept_rate": rate,
        "true_accepts": true_accepts,
        "selection": "maximum CAL true accepts subject to fixed false-accept rate",
    }


def attach_model_predictions(pairs: Sequence[Mapping[str, object]], weights: Sequence[float], threshold: object) -> List[dict]:
    output = []
    for pair in pairs:
        row = dict(pair)
        score = score_pair(pair, weights)
        row["m1_score"] = round(score, 10)
        row["m1_link"] = int(
            pair["pair_role"] in SPLITS and threshold is not None and math.isfinite(float(threshold)) and score >= float(threshold)
        )
        output.append(row)
    return output


def _known_all_pair_denominator(all_pairs: Sequence[Mapping[str, object]], role: Optional[str] = None) -> int:
    return sum(
        1 for pair in all_pairs
        if pair["truth_pair_status"] == KNOWN
        and pair["truth_same_insertion"] == 1
        and (role is None or pair["pair_role"] == role)
    )


def _union_components(fragments: Sequence[Fragment], edges: Sequence[Mapping[str, object]], method: str) -> dict:
    parent = {fragment.fragment_id: fragment.fragment_id for fragment in fragments}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for edge in edges:
        if edge["cross_split_status"] == "SAME_ROLE" and edge.get(method):
            union(str(edge["left_id"]), str(edge["right_id"]))
    by_component = defaultdict(list)
    for fragment in fragments:
        by_component[find(fragment.fragment_id)].append(fragment)
    overmerged = []
    for root, members in by_component.items():
        truth_parents = {
            member.truth_parent_insertion_id for member in members
            if member.truth_status == KNOWN and member.truth_parent_insertion_id
        }
        if len(truth_parents) > 1:
            overmerged.append({"root": root, "parent_count": len(truth_parents), "members": [m.fragment_id for m in members]})
    return {
        "components": len(by_component),
        "overmerged_components": len(overmerged),
        "overmerged_examples": overmerged[:10],
    }


def method_metrics(
    fragments: Sequence[Fragment],
    candidate_pairs: Sequence[Mapping[str, object]],
    all_pairs: Sequence[Mapping[str, object]],
    method: str,
) -> dict:
    same_role = [pair for pair in candidate_pairs if pair["cross_split_status"] == "SAME_ROLE"]
    known = [pair for pair in same_role if pair["truth_pair_status"] == KNOWN]
    tp = sum(1 for pair in known if pair["truth_same_insertion"] == 1 and pair.get(method))
    fp = sum(1 for pair in known if pair["truth_same_insertion"] == 0 and pair.get(method))
    candidate_known_same = sum(1 for pair in known if pair["truth_same_insertion"] == 1)
    denominator = _known_all_pair_denominator(all_pairs)
    unresolved_candidates = sum(1 for pair in candidate_pairs if pair["truth_pair_status"] != KNOWN)
    precision = tp / float(tp + fp) if tp + fp else None
    recall = tp / float(denominator) if denominator else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {
        "method": method,
        "candidate_pairs": len(candidate_pairs),
        "same_role_candidate_pairs": len(same_role),
        "known_candidate_pairs": len(known),
        "known_same_insertion_candidate_numerator": candidate_known_same,
        "known_same_insertion_pair_denominator": denominator,
        "candidate_recall_numerator": tp,
        "pair_true_positive": tp,
        "pair_false_positive": fp,
        "pair_precision": precision,
        "pair_recall": recall,
        "pair_f1": f1,
        "unresolved_candidates_excluded_from_negative": unresolved_candidates,
        "cluster": _union_components(fragments, candidate_pairs, method),
    }


def interval_snapshot(fragments: Sequence[Fragment]) -> Dict[str, Tuple[str, str, int, int]]:
    return {fragment.fragment_id: (fragment.host_id, fragment.contig, fragment.start, fragment.end) for fragment in fragments}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def write_pairs(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    fields = [
        "pair_id", "left_id", "right_id", "host_id", "contig", "left_role", "right_role", "pair_role",
        "cross_split_status", "distance_bp", "overlap_bp", "truth_pair_status", "truth_same_insertion",
        "pred_family_match", "pred_orientation_match", "pred_length_ratio", "candidate", "b0_link", "b1_link",
        "m1_score", "m1_link",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_edges(path: Path, rows: Sequence[Mapping[str, object]], method: str) -> None:
    edges = [row for row in rows if row.get(method) and row["cross_split_status"] == "SAME_ROLE"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["pair_id", "left_id", "right_id", "pair_role", "distance_bp", "truth_pair_status", "truth_same_insertion"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(edges)


def contract() -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "status": ENGINEERING_ONLY,
        "seed": SEED,
        "sequence_origin": "independent_insertion_semisim; no consensus cropping",
        "interval_convention": "[start,end)",
        "identity": {
            "positive": "both truth statuses known and parent insertion IDs equal",
            "negative": "both truth statuses known and parent insertion IDs differ",
            "unresolved": "empty/ambiguous truth identity excluded from negative denominator",
            "source_copy_and_homology": "identity split keys; never inferred from family or coordinate",
            "host_gate": "pairs require equal host_id and contig",
        },
        "splits": {
            "roles": list(SPLITS),
            "group_keys": ["host_id", "source_copy_id", "homology_component_id"],
            "cross_role": "EXCLUDED_CROSS_SPLIT",
        },
        "candidate": {"max_distance_bp": 25, "overlap_is_candidate": True},
        "baselines": {
            "B0": "distance candidate edge",
            "B1": "predicted family + orientation + length ratio >= 0.5",
            "M1": "bounded logistic pair features, fit TRAIN and threshold fixed on CAL",
            "M2": "sequence evidence; INPUT_CONTRACT_ONLY until real encoder input exists",
            "M3": "gap/context-aware association; INPUT_CONTRACT_ONLY until real context/truth exists",
        },
        "calibration": {
            "alpha": 0.01,
            "minimum_negative_pairs_claim_grade": 100,
            "toy_negative_pairs_are_engineering_only": True,
            "same_budget_for_all_methods": True,
        },
        "gap_policy": {
            "gap_filling_applied": False,
            "material_mask_changed": False,
            "pair_or_cluster_outputs_do_not_change_intervals": True,
        },
    }


def run(out_dir: Path, max_distance: int = 25) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    fragments = make_fixture()
    validate_fragments(fragments)
    partition = validate_role_partition(fragments)
    if not partition["pass"]:
        raise ValueError("synthetic fixture violates role partition: %s" % partition)
    before = interval_snapshot(fragments)
    candidate_pairs = build_pairs(fragments, max_distance=max_distance)
    all_pairs = build_pairs(fragments, max_distance=None)
    fit = fit_bounded_logistic(candidate_pairs)
    weights = fit.get("weights", [])
    calibration = choose_cal_threshold(candidate_pairs, weights, alpha=0.01) if weights else {
        "status": "NOTRUN_NO_MODEL",
        "alpha": 0.01,
        "negative_pairs": 0,
        "threshold": None,
    }
    pairs = attach_model_predictions(candidate_pairs, weights, calibration.get("threshold")) if weights else [dict(row) for row in candidate_pairs]
    if not weights:
        for pair in pairs:
            pair["m1_score"] = None
            pair["m1_link"] = 0
    metrics = {
        "status": ENGINEERING_ONLY,
        "fragments": len(fragments),
        "candidate_pairs": len(candidate_pairs),
        "all_same_host_pairs": len(all_pairs),
        "role_counts": {role: sum(1 for fragment in fragments if fragment.role == role) for role in SPLITS},
        "partition": partition,
        "methods": {
            "B0_distance": method_metrics(fragments, pairs, all_pairs, "b0_link"),
            "B1_rules": method_metrics(fragments, pairs, all_pairs, "b1_link"),
            "M1_bounded_pair_logistic": method_metrics(fragments, pairs, all_pairs, "m1_link"),
        },
        "known_truth_policy": {
            "unresolved_candidates": sum(1 for pair in pairs if pair["truth_pair_status"] != KNOWN),
            "unresolved_as_negative": 0,
            "known_same_insertion_all_pair_denominator": _known_all_pair_denominator(all_pairs),
        },
        "invariants": {
            "intervals_unchanged": before == interval_snapshot(fragments),
            "gap_filling_applied": False,
            "material_mask_changed": False,
            "cross_host_edges": 0,
            "consensus_crops_used_as_copies": False,
        },
        "scientific_claim_status": "NOTRUN",
    }
    write_json(out_dir / "contract.json", contract())
    with (out_dir / "fragments.jsonl").open("w", encoding="utf-8") as handle:
        for fragment in fragments:
            handle.write(json.dumps(fragment.to_record(), sort_keys=True) + "\n")
    write_pairs(out_dir / "pairs.tsv", pairs)
    write_edges(out_dir / "edges_B0_distance.tsv", pairs, "b0_link")
    write_edges(out_dir / "edges_B1_rules.tsv", pairs, "b1_link")
    write_edges(out_dir / "edges_M1_bounded_logistic.tsv", pairs, "m1_link")
    write_json(out_dir / "calibration.json", calibration)
    write_json(out_dir / "fit.json", fit)
    write_json(out_dir / "metrics.json", metrics)
    status = {
        "status": "PASS_ENGINEERING_ONLY",
        "scientific_claim_status": "NOTRUN",
        "real_encoder_input": "NOTRUN",
        "real_insertion_truth": "NOTRUN",
        "outputs": ["contract.json", "fragments.jsonl", "pairs.tsv", "edges_B0_distance.tsv", "edges_B1_rules.tsv", "edges_M1_bounded_logistic.tsv", "calibration.json", "fit.json", "metrics.json"],
    }
    write_json(out_dir / "status.json", status)
    return metrics


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-distance", type=int, default=25)
    args = parser.parse_args(argv)
    run(args.out_dir, max_distance=args.max_distance)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
