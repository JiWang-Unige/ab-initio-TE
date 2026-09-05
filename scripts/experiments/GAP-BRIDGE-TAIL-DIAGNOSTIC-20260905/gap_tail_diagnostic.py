#!/usr/bin/env python3
"""Diagnose the frozen Stage 1 low-risk DEV tail.

This is a retrospective, standard-library-only reader.  It consumes the
already-produced chr13 score/evaluation artifacts, applies the calibrators and
the per-arm 1e-5 thresholds recorded in ``evaluation_summary.json``, and
reports how the selected candidates are composed.  It does not fit a
calibrator, search a threshold, inspect CAL-GATE rows, or read chr19.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence


SEQID = "chr13"
ROLE = "DEV"
WINDOW = 8192
FLANK = 256
BLOCK_SIZE = 1_000_000
MECHANISM_BUDGET_KEY = "mechanism_budget_1e-5"
ARMS = ("G_GEOMETRY_LOGITS", "R_RAW_LOCAL", "H_P3_LATENT")
SEEDS = (17, 42, 20260902)
LENGTH_STRATA = ("1", "2", "3-5", "6-20", "21-100", "101-512")
HEAD_COLUMNS = tuple(
    f"{arm}__seed{seed}__raw_risk_logit"
    for arm in ARMS
    for seed in SEEDS
)


@dataclass(frozen=True)
class Candidate:
    """The label and geometry needed for this diagnostic's DEV rows."""

    candidate_id: str
    block_index: int
    gap_start: int
    gap_end: int
    length: int
    length_stratum: str
    relation: str
    positive_bp: int
    negative_bp: int
    unknown_bp: int

    @property
    def crop_crosses_seam(self) -> bool:
        crop_start = self.gap_start - FLANK
        crop_end = self.gap_end + FLANK
        return crop_start // WINDOW != (crop_end - 1) // WINDOW

    @property
    def seam(self) -> bool:
        """Backward-compatible name for the frozen crop-seam indicator."""
        return self.crop_crosses_seam

    @property
    def gap_internal_crosses_seam(self) -> bool:
        return self.gap_start // WINDOW != (self.gap_end - 1) // WINDOW

    @property
    def gap_endpoint_at_seam(self) -> bool:
        return self.gap_start % WINDOW == 0 or self.gap_end % WINDOW == 0

    @property
    def flank_only_crop_crosses_seam(self) -> bool:
        return (
            self.crop_crosses_seam
            and not self.gap_internal_crosses_seam
            and not self.gap_endpoint_at_seam
        )

    @property
    def one_mb_block(self) -> str:
        midpoint = (self.gap_start + self.gap_end) // 2
        return f"{SEQID}:{midpoint // BLOCK_SIZE}"

    @property
    def category(self) -> str:
        if self.unknown_bp:
            return "unknown"
        if self.negative_bp == 0:
            return "all_positive"
        if self.positive_bp == 0:
            return "all_negative"
        return "mixed"


def _int(row: Mapping[str, str], field: str) -> int:
    try:
        value = int(row[field])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid integer field: {field}") from error
    if value < 0:
        raise ValueError(f"negative field: {field}")
    return value


def _finite_float(value: object, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid float: {label}") from error
    if not math.isfinite(result):
        raise ValueError(f"non-finite float: {label}")
    return result


def length_stratum(length: int) -> str:
    if length == 1:
        return "1"
    if length == 2:
        return "2"
    if length <= 5:
        return "3-5"
    if length <= 20:
        return "6-20"
    if length <= 100:
        return "21-100"
    if length <= 512:
        return "101-512"
    raise ValueError(f"gap length is outside the frozen range: {length}")


def read_manifest(path: Path) -> dict[str, Candidate]:
    """Read only chr13/DEV rows from the manifest.

    Rows for TRAIN, CAL_FIT, CAL_GATE, and other chromosomes are skipped
    before any Stage 1 label fields are interpreted.  This keeps the reader
    scoped to the requested DEV diagnostic.
    """
    required = {
        "candidate_id", "seqid", "role", "chr13_block_index",
        "left_run_start", "left_run_end", "gap_start", "gap_end",
        "right_run_start", "right_run_end", "crop_start", "crop_end",
        "gap_length", "length_stratum", "comparator_known", "positive_bp",
        "negative_bp", "unknown_bp", "target_negative_fraction",
        "comparator_relation",
    }
    result: dict[str, Candidate] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("candidate manifest lacks frozen Stage 1 fields")
        for row in reader:
            if row.get("seqid") != SEQID or row.get("role") != ROLE:
                continue
            candidate_id = row["candidate_id"]
            if candidate_id in result:
                raise ValueError("duplicate chr13 DEV candidate in manifest")
            block_text = row["chr13_block_index"].strip()
            if not block_text:
                raise ValueError("chr13 DEV candidate has no block index")
            block_index = _int({"value": block_text}, "value")
            left_start = _int(row, "left_run_start")
            left_end = _int(row, "left_run_end")
            gap_start = _int(row, "gap_start")
            gap_end = _int(row, "gap_end")
            right_start = _int(row, "right_run_start")
            right_end = _int(row, "right_run_end")
            crop_start = _int(row, "crop_start")
            crop_end = _int(row, "crop_end")
            length = _int(row, "gap_length")
            if gap_end <= gap_start or gap_end - gap_start != length or length > 512:
                raise ValueError("invalid chr13 DEV candidate gap geometry")
            if left_end != gap_start or right_start != gap_end:
                raise ValueError("chr13 DEV flank runs do not abut gap")
            if left_end <= left_start or right_end <= right_start:
                raise ValueError("chr13 DEV candidate flank is empty")
            if crop_start != gap_start - FLANK or crop_end != gap_end + FLANK:
                raise ValueError("chr13 DEV crop disagrees with gap geometry")
            stratum = row["length_stratum"]
            if stratum != length_stratum(length):
                raise ValueError("chr13 DEV length stratum disagrees with gap")
            positive = _int(row, "positive_bp")
            negative = _int(row, "negative_bp")
            unknown = _int(row, "unknown_bp")
            if positive + negative + unknown != length:
                raise ValueError("chr13 DEV label masses do not sum to gap length")
            if row["comparator_known"].strip() == "1" and unknown:
                raise ValueError("known chr13 DEV candidate has unknown bp")
            if unknown == 0:
                target = row["target_negative_fraction"].strip()
                if not target or not math.isclose(
                    _finite_float(target, "target_negative_fraction"),
                    negative / float(length),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    raise ValueError("chr13 DEV target disagrees with label masses")
            result[candidate_id] = Candidate(
                candidate_id=candidate_id,
                block_index=block_index,
                gap_start=gap_start,
                gap_end=gap_end,
                length=length,
                length_stratum=stratum,
                relation=row["comparator_relation"],
                positive_bp=positive,
                negative_bp=negative,
                unknown_bp=unknown,
            )
    if not result:
        raise ValueError("manifest contains no chr13 DEV candidates")
    return result


def read_scores(path: Path, candidates: Mapping[str, Candidate]) -> dict[str, dict[str, float]]:
    """Read scores for the DEV IDs, ignoring non-DEV rows in the full score TSV."""
    required = {
        "candidate_id", "seqid", "role", "gap_start", "gap_end",
        "gap_length", "length_stratum", *HEAD_COLUMNS,
    }
    result: dict[str, dict[str, float]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("raw score file lacks frozen Stage 1 head columns")
        for row in reader:
            candidate_id = row.get("candidate_id", "")
            candidate = candidates.get(candidate_id)
            if candidate is None:
                if row.get("seqid") == SEQID and row.get("role") == ROLE:
                    raise ValueError("score file contains an unmanifested chr13 DEV row")
                continue
            if row.get("seqid") != SEQID or row.get("role") != ROLE:
                raise ValueError("score geometry role mismatch for a DEV candidate")
            if _int(row, "gap_start") != candidate.gap_start or _int(row, "gap_end") != candidate.gap_end:
                raise ValueError("score geometry mismatch for a DEV candidate")
            if _int(row, "gap_length") != candidate.length or row.get("length_stratum") != candidate.length_stratum:
                raise ValueError("score length mismatch for a DEV candidate")
            if candidate_id in result:
                raise ValueError("duplicate chr13 DEV score row")
            values = {
                column: _finite_float(row[column], column)
                for column in HEAD_COLUMNS
            }
            result[candidate_id] = values
    expected = set(candidates)
    if set(result) != expected:
        raise ValueError("raw score denominator does not equal chr13 DEV manifest")
    return result


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _mean_seed_logits(raw: Mapping[str, float], arm: str) -> float:
    # This is the same three-value arithmetic used by the frozen evaluator's
    # np.mean on the raw risk-logit list, without importing NumPy.
    return sum(raw[f"{arm}__seed{seed}__raw_risk_logit"] for seed in SEEDS) / float(len(SEEDS))


def _calibrated_risk(raw: Mapping[str, float], arm: str, calibrator: Mapping[str, object]) -> float:
    if calibrator.get("success") is not True:
        raise ValueError(f"calibrator is not successful for {arm}")
    intercept = _finite_float(calibrator.get("intercept"), f"{arm}.intercept")
    slope = _finite_float(calibrator.get("slope"), f"{arm}.slope")
    if slope < 0.0:
        raise ValueError(f"calibrator slope is negative for {arm}")
    return _sigmoid(intercept + slope * _mean_seed_logits(raw, arm))


def _summary_int(value: object, label: str) -> int:
    numeric = _finite_float(value, label)
    rounded = int(round(numeric))
    if numeric != float(rounded):
        raise ValueError(f"summary field is not an integer: {label}")
    return rounded


def _summary_float(value: object, label: str) -> float:
    return _finite_float(value, label)


def _require_summary_match(actual: int, expected: object, label: str) -> None:
    expected_int = _summary_int(expected, label)
    if actual != expected_int:
        raise ValueError(f"DEV selection does not reproduce summary field: {label}")


def load_summary(path: Path, candidates: Mapping[str, Candidate]) -> tuple[dict[str, object], dict[str, dict[str, float]], dict[str, set[str]], dict[str, dict[str, object]]]:
    """Load only the existing DEV mechanism thresholds and calibrators."""
    with path.open(encoding="utf-8") as handle:
        summary = json.load(handle)
    if not isinstance(summary, dict):
        raise ValueError("evaluation summary root is not an object")
    role_counts = summary.get("role_counts")
    if not isinstance(role_counts, dict) or "DEV" not in role_counts:
        raise ValueError("evaluation summary lacks DEV role count")
    dev_count = _summary_int(role_counts["DEV"], "role_counts.DEV")
    if dev_count != len(candidates):
        raise ValueError("DEV manifest count differs from evaluation summary")
    calibrators = summary.get("calibrators")
    budget_summary = summary.get(MECHANISM_BUDGET_KEY)
    if not isinstance(calibrators, dict) or not isinstance(budget_summary, dict):
        raise ValueError("evaluation summary lacks frozen calibrators or mechanism budgets")
    risks: dict[str, dict[str, float]] = {arm: {} for arm in ARMS}
    selected: dict[str, set[str]] = {arm: set() for arm in ARMS}
    thresholds: dict[str, dict[str, object]] = {}
    dev_metrics = summary.get("role_metrics")
    if not isinstance(dev_metrics, dict) or not isinstance(dev_metrics.get("DEV"), dict):
        raise ValueError("evaluation summary lacks DEV metrics")
    for arm in ARMS:
        calibrator = calibrators.get(arm)
        if not isinstance(calibrator, dict):
            raise ValueError(f"missing calibrator for {arm}")
        budget = budget_summary.get(arm)
        if not isinstance(budget, dict) or "threshold" not in budget:
            raise ValueError(f"missing frozen mechanism threshold for {arm}")
        threshold_value = budget["threshold"]
        threshold: Optional[float]
        if threshold_value is None:
            threshold = None
        else:
            threshold = _summary_float(threshold_value, f"{arm}.threshold")
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(f"mechanism threshold is outside [0,1] for {arm}")
        thresholds[arm] = {
            "threshold": threshold,
            "summary": budget,
            "calibrator": calibrator,
        }
        arm_metrics = dev_metrics["DEV"].get(arm)
        if not isinstance(arm_metrics, dict):
            raise ValueError(f"missing DEV metrics for {arm}")
        _require_summary_match(
            sum(candidate.unknown_bp == 0 for candidate in candidates.values()),
            arm_metrics.get("known_candidates"),
            f"role_metrics.DEV.{arm}.known_candidates",
        )
        known_gap_bp = sum(
            candidate.length for candidate in candidates.values() if candidate.unknown_bp == 0
        )
        _require_summary_match(
            known_gap_bp,
            arm_metrics.get("known_gap_bp"),
            f"role_metrics.DEV.{arm}.known_gap_bp",
        )
    return summary, risks, selected, thresholds


def reconstruct_selection(
    candidates: Mapping[str, Candidate],
    raw: Mapping[str, Mapping[str, float]],
    summary: Mapping[str, object],
) -> tuple[dict[str, dict[str, float]], dict[str, set[str]], dict[str, dict[str, object]]]:
    """Apply, without scanning, the thresholds saved by Stage 1 evaluation."""
    calibrators = summary["calibrators"]
    budgets = summary[MECHANISM_BUDGET_KEY]
    assert isinstance(calibrators, dict) and isinstance(budgets, dict)
    risks: dict[str, dict[str, float]] = {arm: {} for arm in ARMS}
    selected: dict[str, set[str]] = {arm: set() for arm in ARMS}
    validation: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        calibrator = calibrators[arm]
        budget = budgets[arm]
        assert isinstance(calibrator, dict) and isinstance(budget, dict)
        threshold_value = budget.get("threshold")
        threshold = None if threshold_value is None else _summary_float(threshold_value, f"{arm}.threshold")
        for candidate_id, candidate in candidates.items():
            risk = _calibrated_risk(raw[candidate_id], arm, calibrator)
            risks[arm][candidate_id] = risk
            if threshold is not None and risk <= threshold:
                selected[arm].add(candidate_id)
        selected_candidates = [candidates[candidate_id] for candidate_id in selected[arm]]
        actual = {
            "selected_candidates": len(selected_candidates),
            "selected_positive_bp": sum(candidate.positive_bp for candidate in selected_candidates),
            "selected_known_negative_bp": sum(candidate.negative_bp for candidate in selected_candidates),
            "selected_unknown_bp": sum(candidate.unknown_bp for candidate in selected_candidates),
        }
        for field, value in actual.items():
            _require_summary_match(value, budget.get(field), f"{arm}.{field}")
        if "worst_case_negative_bp" in budget:
            _require_summary_match(
                actual["selected_known_negative_bp"] + actual["selected_unknown_bp"],
                budget["worst_case_negative_bp"],
                f"{arm}.worst_case_negative_bp",
            )
        validation[arm] = {
            **actual,
            "summary_match": True,
            "threshold": threshold,
        }
    return risks, selected, validation


def _mass_summary(candidates: Iterable[Candidate]) -> dict[str, int]:
    rows = list(candidates)
    return {
        "candidate_count": len(rows),
        "gap_bp": sum(candidate.length for candidate in rows),
        "positive_bp": sum(candidate.positive_bp for candidate in rows),
        "negative_bp": sum(candidate.negative_bp for candidate in rows),
        "unknown_bp": sum(candidate.unknown_bp for candidate in rows),
    }


def _grouped_mass(
    candidates: Iterable[Candidate],
    key_function,
) -> dict[str, dict[str, int]]:
    groups: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        groups[str(key_function(candidate))].append(candidate)
    return {
        key: _mass_summary(groups[key])
        for key in sorted(groups, key=_group_sort_key)
    }


def _group_sort_key(value: str):
    if value in LENGTH_STRATA:
        return (0, LENGTH_STRATA.index(value))
    if value.startswith(f"{SEQID}:"):
        try:
            return (2, int(value.rsplit(":", 1)[1]))
        except ValueError:
            pass
    if value in ("seam", "non_seam"):
        return (1, 0 if value == "seam" else 1)
    return (3, value)


def _binary_seam_groups(
    rows: Sequence[Candidate],
    predicate,
    true_name: str = "true",
    false_name: str = "false",
) -> dict[str, dict[str, int]]:
    true_rows = [candidate for candidate in rows if predicate(candidate)]
    false_rows = [candidate for candidate in rows if not predicate(candidate)]
    return {
        true_name: _mass_summary(true_rows),
        false_name: _mass_summary(false_rows),
    }


def _seam_groups(rows: Sequence[Candidate]) -> dict[str, dict[str, dict[str, int]]]:
    """Keep the crop, internal-gap, endpoint, and flank-only seam flags separate."""
    return {
        "crop_crosses_seam": _binary_seam_groups(
            rows, lambda candidate: candidate.crop_crosses_seam,
            true_name="seam", false_name="non_seam",
        ),
        "gap_internal_crosses_seam": _binary_seam_groups(
            rows, lambda candidate: candidate.gap_internal_crosses_seam,
        ),
        "gap_endpoint_at_seam": _binary_seam_groups(
            rows, lambda candidate: candidate.gap_endpoint_at_seam,
        ),
        "flank_only_crop_crosses_seam": _binary_seam_groups(
            rows, lambda candidate: candidate.flank_only_crop_crosses_seam,
        ),
    }


def _seam_length_groups(rows: Sequence[Candidate]) -> dict[str, dict[str, dict[str, dict[str, int]]]]:
    """Cross each independent seam flag with the frozen six length strata."""
    predicates = {
        "crop_crosses_seam": lambda candidate: candidate.crop_crosses_seam,
        "gap_internal_crosses_seam": lambda candidate: candidate.gap_internal_crosses_seam,
        "gap_endpoint_at_seam": lambda candidate: candidate.gap_endpoint_at_seam,
        "flank_only_crop_crosses_seam": lambda candidate: candidate.flank_only_crop_crosses_seam,
    }
    result: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
    for name, predicate in predicates.items():
        true_rows = [candidate for candidate in rows if predicate(candidate)]
        false_rows = [candidate for candidate in rows if not predicate(candidate)]
        result[name] = {
            "true": _grouped_mass(true_rows, lambda candidate: candidate.length_stratum),
            "false": _grouped_mass(false_rows, lambda candidate: candidate.length_stratum),
        }
    return result


def _tail_strata(rows: Sequence[Candidate]) -> dict[str, dict[str, dict[str, int]]]:
    return {
        "length_stratum": _grouped_mass(rows, lambda candidate: candidate.length_stratum),
        "comparator_relation": _grouped_mass(rows, lambda candidate: candidate.relation),
        "seam": _seam_groups(rows),
        "seam_by_length_stratum": _seam_length_groups(rows),
        "one_mb_block": _grouped_mass(rows, lambda candidate: candidate.one_mb_block),
    }


def _composition(rows: Sequence[Candidate]) -> dict[str, dict[str, int]]:
    return {
        category: _mass_summary(candidate for candidate in rows if candidate.category == category)
        for category in ("all_positive", "mixed", "all_negative", "unknown")
    }


def _negative_distribution(rows: Sequence[Candidate], total_negative_bp: int) -> dict[str, dict[str, dict[str, object]]]:
    groups: dict[str, dict[str, list[Candidate]]] = {
        "category": defaultdict(list),
        "length_stratum": defaultdict(list),
        "comparator_relation": defaultdict(list),
        "seam": defaultdict(list),
        "one_mb_block": defaultdict(list),
    }
    for candidate in rows:
        groups["category"][candidate.category].append(candidate)
        groups["length_stratum"][candidate.length_stratum].append(candidate)
        groups["comparator_relation"][candidate.relation].append(candidate)
        groups["seam"]["seam" if candidate.seam else "non_seam"].append(candidate)
        groups["one_mb_block"][candidate.one_mb_block].append(candidate)
    result: dict[str, dict[str, dict[str, object]]] = {}
    for dimension, dimension_groups in groups.items():
        result[dimension] = {}
        for name in sorted(dimension_groups, key=_group_sort_key):
            negative_bp = sum(candidate.negative_bp for candidate in dimension_groups[name])
            result[dimension][name] = {
                "candidate_count": len(dimension_groups[name]),
                "negative_bp": negative_bp,
                "share_of_selected_negative_bp": (
                    negative_bp / float(total_negative_bp) if total_negative_bp else None
                ),
            }
    return result


def _negative_contributors(rows: Sequence[Candidate]) -> dict[str, object]:
    total_negative_bp = sum(candidate.negative_bp for candidate in rows)
    ordered = sorted(rows, key=lambda candidate: (-candidate.negative_bp, candidate.candidate_id))
    top_k: dict[str, object] = {}
    for requested in (1, 5, 10):
        top = ordered[:requested]
        mass = sum(candidate.negative_bp for candidate in top)
        top_k[str(requested)] = {
            "candidate_count": len(top),
            "negative_bp": mass,
            "share_of_selected_negative_bp": mass / float(total_negative_bp) if total_negative_bp else None,
            "distribution": _negative_distribution(top, total_negative_bp),
        }
    return {
        "selected_negative_bp": total_negative_bp,
        "top_k": top_k,
        "tie_break": "candidate_id_ascending",
    }


def _pseudo_base_brier(rows: Sequence[Candidate], risks: Mapping[str, float]) -> float:
    known = [candidate for candidate in rows if candidate.unknown_bp == 0]
    denominator = sum(candidate.length for candidate in known)
    if denominator <= 0:
        raise ValueError("DEV known denominator has no bp")
    numerator = sum(
        candidate.negative_bp * (1.0 - risks[candidate.candidate_id]) ** 2
        + candidate.positive_bp * risks[candidate.candidate_id] ** 2
        for candidate in known
    )
    return numerator / float(denominator)


def _fraction_mse(rows: Sequence[Candidate], risks: Mapping[str, float]) -> Optional[float]:
    """Return the unweighted candidate-level squared fraction error."""
    if not rows:
        return None
    return sum(
        (
            risks[candidate.candidate_id]
            - candidate.negative_bp / float(candidate.length)
        ) ** 2
        for candidate in rows
    ) / float(len(rows))


def _denominator_distribution(rows: Sequence[Candidate]) -> dict[str, object]:
    """Summarize a known or unknown DEV denominator and its fixed strata."""
    return {
        **_mass_summary(rows),
        "by_length_stratum": _grouped_mass(rows, lambda candidate: candidate.length_stratum),
        "by_seam": _seam_groups(rows),
        "by_seam_and_length_stratum": _seam_length_groups(rows),
        "by_comparator_relation": _grouped_mass(rows, lambda candidate: candidate.relation),
    }


def _length_stratum_brier(
    known: Sequence[Candidate],
    risks: Mapping[str, Mapping[str, float]],
) -> dict[str, object]:
    """Report the frozen pseudo-base Brier and fraction MSE per length stratum."""
    result: dict[str, object] = {}
    for stratum in LENGTH_STRATA:
        rows = [candidate for candidate in known if candidate.length_stratum == stratum]
        length_bp = sum(candidate.length for candidate in rows)
        if not rows or length_bp <= 0:
            result[stratum] = {
                "candidate_count": len(rows),
                "gap_bp": length_bp,
                "within_gap_irreducible_brier": None,
                "arms": {
                    arm: {"pseudo_base_brier": None, "candidate_fraction_mse": None}
                    for arm in ARMS
                },
            }
            continue
        irreducible_numerator = sum(
            candidate.negative_bp * candidate.positive_bp / float(candidate.length)
            for candidate in rows
        )
        irreducible = irreducible_numerator / float(length_bp)
        arm_values: dict[str, object] = {}
        for arm in ARMS:
            pseudo = _pseudo_base_brier(rows, risks[arm])
            arm_values[arm] = {
                "pseudo_base_brier": pseudo,
                "within_gap_irreducible_brier_reference": irreducible,
                "excess_fraction_brier": pseudo - irreducible,
                "candidate_fraction_mse": _fraction_mse(rows, risks[arm]),
            }
        result[stratum] = {
            "candidate_count": len(rows),
            "gap_bp": length_bp,
            "positive_bp": sum(candidate.positive_bp for candidate in rows),
            "negative_bp": sum(candidate.negative_bp for candidate in rows),
            "within_gap_irreducible_brier": {
                "numerator": irreducible_numerator,
                "denominator_gap_bp": length_bp,
                "value": irreducible,
            },
            "arms": arm_values,
        }
    return result


def _known_dev_report(
    candidates: Mapping[str, Candidate],
    risks: Mapping[str, Mapping[str, float]],
    selected: Mapping[str, set[str]],
) -> dict[str, object]:
    rows = list(candidates.values())
    known = [candidate for candidate in rows if candidate.unknown_bp == 0]
    mixed = [candidate for candidate in known if candidate.category == "mixed"]
    known_length = sum(candidate.length for candidate in known)
    mixed_length = sum(candidate.length for candidate in mixed)
    mixed_positive = sum(candidate.positive_bp for candidate in mixed)
    mixed_negative = sum(candidate.negative_bp for candidate in mixed)
    irreducible_numerator = sum(
        candidate.length
        * (candidate.negative_bp / float(candidate.length))
        * (candidate.positive_bp / float(candidate.length))
        for candidate in mixed
    )
    irreducible = irreducible_numerator / float(known_length) if known_length else None
    mixed_report: dict[str, object] = {
        "candidate_count": len(mixed),
        "gap_bp": mixed_length,
        "positive_bp": mixed_positive,
        "negative_bp": mixed_negative,
        "selected_by_arm": {},
    }
    selected_by_arm = mixed_report["selected_by_arm"]
    assert isinstance(selected_by_arm, dict)
    for arm in ARMS:
        selected_mixed = [
            candidate for candidate in mixed
            if candidate.candidate_id in selected[arm]
        ]
        selected_positive = sum(candidate.positive_bp for candidate in selected_mixed)
        selected_negative = sum(candidate.negative_bp for candidate in selected_mixed)
        selected_by_arm[arm] = {
            "candidate_count": len(selected_mixed),
            "gap_bp": sum(candidate.length for candidate in selected_mixed),
            "positive_bp": selected_positive,
            "negative_bp": selected_negative,
            "positive_bp_coverage": selected_positive / float(mixed_positive) if mixed_positive else None,
            "negative_bp_coverage": selected_negative / float(mixed_negative) if mixed_negative else None,
        }
    arm_brier: dict[str, object] = {}
    for arm in ARMS:
        pseudo = _pseudo_base_brier(rows, risks[arm])
        excess = pseudo - (irreducible or 0.0)
        arm_brier[arm] = {
            "pseudo_base_brier": pseudo,
            "within_gap_irreducible_brier_reference": irreducible,
            "excess_fraction_brier": excess,
        }
    return {
        "candidate_count": len(known),
        "gap_bp": known_length,
        "positive_bp": sum(candidate.positive_bp for candidate in known),
        "negative_bp": sum(candidate.negative_bp for candidate in known),
        "mixed": mixed_report,
        "within_gap_irreducible_brier": {
            "numerator": irreducible_numerator,
            "denominator_known_gap_bp": known_length,
            "value": irreducible,
        },
        "length_stratum_brier": _length_stratum_brier(known, risks),
        "arms": arm_brier,
    }


def _pairwise_report(
    candidates: Mapping[str, Candidate],
    selected: Mapping[str, set[str]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for index, arm_a in enumerate(ARMS):
        for arm_b in ARMS[index + 1:]:
            overlap_ids = selected[arm_a] & selected[arm_b]
            a_only_ids = selected[arm_a] - selected[arm_b]
            b_only_ids = selected[arm_b] - selected[arm_a]
            key = f"{arm_a}_vs_{arm_b}"
            result[key] = {
                "arm_a": arm_a,
                "arm_b": arm_b,
                "overlap": _mass_summary(candidates[candidate_id] for candidate_id in overlap_ids),
                "arm_a_exclusive": _mass_summary(candidates[candidate_id] for candidate_id in a_only_ids),
                "arm_b_exclusive": _mass_summary(candidates[candidate_id] for candidate_id in b_only_ids),
            }
    return result


def analyze(
    manifest_path: Path,
    scores_path: Path,
    summary_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    candidates = read_manifest(manifest_path)
    raw = read_scores(scores_path, candidates)
    summary, _unused_risks, _unused_selected, _unused_thresholds = load_summary(summary_path, candidates)
    risks, selected, validation = reconstruct_selection(candidates, raw, summary)
    arms: dict[str, object] = {}
    for arm in ARMS:
        tail = [candidates[candidate_id] for candidate_id in selected[arm]]
        arms[arm] = {
            "threshold": validation[arm]["threshold"],
            "selection_reconstruction": validation[arm],
            "tail": {
                **_mass_summary(tail),
                "composition": _composition(tail),
                "strata": _tail_strata(tail),
                "negative_contributors": _negative_contributors(tail),
            },
        }
    result: dict[str, object] = {
        "schema": "gap_bridge_tail_diagnostic_v1",
        "status": "PASS",
        "seqid": SEQID,
        "role": ROLE,
        "arms": arms,
        "pairwise_selected": _pairwise_report(candidates, selected),
        "dev_known": _known_dev_report(candidates, risks, selected),
        "dev_denominator": {
            "known": _denominator_distribution(
                [candidate for candidate in candidates.values() if candidate.unknown_bp == 0]
            ),
            "unknown": _denominator_distribution(
                [candidate for candidate in candidates.values() if candidate.unknown_bp != 0]
            ),
        },
        "selection_source": {
            "thresholds": MECHANISM_BUDGET_KEY,
            "calibrators": "evaluation_summary.json.calibrators",
            "new_threshold_scan": False,
            "chr19_read": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    output_path = output_dir / "gap_tail_diagnostic.json"
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--scores", required=True, type=Path)
    parser.add_argument("--evaluation-summary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = analyze(args.manifest, args.scores, args.evaluation_summary, args.output_dir)
    print(json.dumps({"status": result["status"], "output": str(args.output_dir / "gap_tail_diagnostic.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
