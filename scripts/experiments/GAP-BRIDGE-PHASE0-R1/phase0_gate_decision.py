#!/usr/bin/env python3
"""Combine the frozen chr19 Phase-0 evidence into one prospective decision."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


G2 = "G2_FULL_LIBRARY_FREE"
G1 = "G1_GEOMETRY_LOGITS"


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _value(source: object, *path: str) -> object | None:
    current = source
    for field in path:
        if not isinstance(current, dict) or field not in current:
            return None
        current = current[field]
    return current


def _number(source: object, *path: str) -> float | None:
    value = _value(source, *path)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _all_gate(description: str, checks: dict[str, bool | None], observed: dict[str, object]) -> dict[str, object]:
    if any(value is False for value in checks.values()):
        status = "FAIL"
    elif any(value is None for value in checks.values()):
        status = "BLOCKED"
    else:
        status = "PASS"
    return {
        "description": description,
        "status": status,
        "checks": checks,
        "observed": observed,
    }


def _relative_decrease(raw: float | None, refined: float | None) -> float | None:
    if raw is None or refined is None or raw <= 0:
        return None
    return (raw - refined) / raw


def _candidate_gates(candidate: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    denominator_status = _value(candidate, "prospective_denominator", "status")
    bridge = _number(candidate, "prospective_denominator", "eligible_clean_bridge_candidates")
    separation = _number(candidate, "prospective_denominator", "eligible_clean_separation_candidates")
    bridge_gt5 = _number(candidate, "prospective_denominator", "eligible_bridge_longer_than_5bp")
    blocks = _number(candidate, "prospective_denominator", "independent_1mb_blocks_with_both_clean_classes")
    gate1 = _all_gate(
        "Frozen chr19 test denominator is sufficient.",
        {
            "upstream_denominator_status_is_PASS": True if denominator_status == "PASS" else None,
            "clean_bridge_candidates_ge_1000": None if bridge is None else bridge >= 1000,
            "clean_separation_candidates_ge_1000": None if separation is None else separation >= 1000,
            "bridge_candidates_gt5bp_ge_200": None if bridge_gt5 is None else bridge_gt5 >= 200,
            "both_class_1mb_blocks_ge_20": None if blocks is None else blocks >= 20,
        },
        {
            "upstream_status": denominator_status,
            "clean_bridge_candidates": bridge,
            "clean_separation_candidates": separation,
            "bridge_candidates_gt5bp": bridge_gt5,
            "both_class_1mb_blocks": blocks,
        },
    )

    best_ranking = _value(candidate, "comparison", "best_ranking_baseline")
    ap_delta = _number(candidate, "comparison", "g2_minus_best_baseline_average_precision")
    bootstrap_status = _value(candidate, "bootstrap_ap_difference", "status")
    bootstrap_lower = _number(candidate, "bootstrap_ap_difference", "lower_95")
    gate2 = _all_gate(
        "G2 ranking improves on the validation-selected frozen ranking baseline.",
        {
            "best_ranking_baseline_recorded": True if isinstance(best_ranking, str) else None,
            "g2_ap_gain_ge_0.05": None if ap_delta is None else ap_delta >= 0.05,
            "bootstrap_status_is_PASS": True if bootstrap_status == "PASS" else None,
            "bootstrap_ap_gain_lower95_gt_0": None if bootstrap_lower is None else bootstrap_lower > 0,
        },
        {
            "best_ranking_baseline": best_ranking,
            "g2_minus_best_ranking_baseline_ap": ap_delta,
            "bootstrap_status": bootstrap_status,
            "bootstrap_lower_95": bootstrap_lower,
        },
    )

    purged_status = _value(candidate, "purged_challenge", "status")
    purged_delta = _number(candidate, "purged_challenge", "g2_minus_best_baseline_average_precision")
    g2_ap = _number(candidate, "group_metrics", G2, "candidate_metrics", "average_precision")
    g1_ap = _number(candidate, "group_metrics", G1, "candidate_metrics", "average_precision")
    non_distance_delta = None if g2_ap is None or g1_ap is None else g2_ap - g1_ap
    gate3 = _all_gate(
        "Library-free sequence gain persists after homology purge and exceeds G1.",
        {
            "purged_challenge_status_is_EVALUATED": True if purged_status == "EVALUATED" else None,
            "purged_g2_ap_gain_gt_0": None if purged_delta is None else purged_delta > 0,
            "g2_minus_g1_ap_ge_0.03": None if non_distance_delta is None else non_distance_delta >= 0.03,
        },
        {
            "purged_status": purged_status,
            "purged_g2_minus_best_ranking_baseline_ap": purged_delta,
            "g2_average_precision": g2_ap,
            "g1_average_precision": g1_ap,
            "g2_minus_g1_average_precision": non_distance_delta,
        },
    )
    return gate1, gate2, gate3


def _mask_gates(mask: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    precision = _number(mask, "metrics", "added_bp", "precision")
    precision_bootstrap_status = _value(mask, "metrics", "added_bp", "precision_bootstrap", "status")
    precision_lower = _number(mask, "metrics", "added_bp", "precision_bootstrap", "lower_95")
    gate4 = _all_gate(
        "Added gap bases meet the frozen precision point and interval floors.",
        {
            "added_bp_precision_ge_0.97": None if precision is None else precision >= 0.97,
            "precision_bootstrap_status_is_PASS": True if precision_bootstrap_status == "PASS" else None,
            "added_bp_precision_lower95_ge_0.95": None if precision_lower is None else precision_lower >= 0.95,
        },
        {
            "added_bp_precision": precision,
            "precision_bootstrap_status": precision_bootstrap_status,
            "precision_bootstrap_lower_95": precision_lower,
        },
    )

    internal_recall = _number(mask, "metrics", "internal_gap_recovery", "internal_gap_positive_bp_recall")
    long_recall = _number(mask, "metrics", "internal_gap_recovery", "internal_gap_gt5_positive_bp_recall")
    gate5 = _all_gate(
        "Internal comparator-positive gap bases are recovered at the frozen rates.",
        {
            "internal_gap_bp_recall_ge_0.20": None if internal_recall is None else internal_recall >= 0.20,
            "internal_gap_gt5_bp_recall_ge_0.10": None if long_recall is None else long_recall >= 0.10,
        },
        {
            "internal_gap_bp_recall": internal_recall,
            "internal_gap_gt5_bp_recall": long_recall,
        },
    )

    raw_split = _number(mask, "metrics", "fragmentation", "raw", "split_rate")
    refined_split = _number(mask, "metrics", "fragmentation", "refined", "split_rate")
    raw_fragments = _number(mask, "metrics", "fragmentation", "raw", "fragments_per_truth")
    refined_fragments = _number(mask, "metrics", "fragmentation", "refined", "fragments_per_truth")
    split_decrease = _relative_decrease(raw_split, refined_split)
    fragments_decrease = _relative_decrease(raw_fragments, refined_fragments)
    gate6 = _all_gate(
        "Split rate and fragments per comparator truth run each improve by at least 15%.",
        {
            "split_rate_relative_decrease_ge_0.15": None if split_decrease is None else split_decrease >= 0.15,
            "fragments_per_truth_relative_decrease_ge_0.15": (
                None if fragments_decrease is None else fragments_decrease >= 0.15
            ),
        },
        {
            "raw_split_rate": raw_split,
            "refined_split_rate": refined_split,
            "split_rate_relative_decrease": split_decrease,
            "raw_fragments_per_truth": raw_fragments,
            "refined_fragments_per_truth": refined_fragments,
            "fragments_per_truth_relative_decrease": fragments_decrease,
        },
    )

    raw_precision = _number(mask, "metrics", "whole_mask", "raw", "precision")
    refined_precision = _number(mask, "metrics", "whole_mask", "refined", "precision")
    precision_drop = None if raw_precision is None or refined_precision is None else raw_precision - refined_precision
    raw_f1 = _number(mask, "metrics", "whole_mask", "raw", "f1")
    refined_f1 = _number(mask, "metrics", "whole_mask", "refined", "f1")
    retained = _value(mask, "all_original_p3_positive_bases_retained")
    raw_missed = _number(mask, "metrics", "fragmentation", "raw", "missed_rate")
    refined_missed = _number(mask, "metrics", "fragmentation", "refined", "missed_rate")
    gate7 = _all_gate(
        "The refined whole mask preserves P3 and its frozen precision, F1 and missed-rate guardrails.",
        {
            "whole_mask_precision_drop_le_0.001": None if precision_drop is None else precision_drop <= 0.001,
            "whole_mask_f1_nondecrease": None if raw_f1 is None or refined_f1 is None else refined_f1 >= raw_f1,
            "all_original_p3_positive_bases_retained": retained if isinstance(retained, bool) else None,
            "missed_rate_nonincrease": (
                None if raw_missed is None or refined_missed is None else refined_missed <= raw_missed
            ),
        },
        {
            "raw_whole_mask_precision": raw_precision,
            "refined_whole_mask_precision": refined_precision,
            "whole_mask_precision_drop": precision_drop,
            "raw_whole_mask_f1": raw_f1,
            "refined_whole_mask_f1": refined_f1,
            "all_original_p3_positive_bases_retained": retained,
            "raw_missed_rate": raw_missed,
            "refined_missed_rate": refined_missed,
        },
    )
    return gate4, gate5, gate6, gate7


def _gene_gate(gene: dict[str, object]) -> dict[str, object]:
    source_status = _value(gene, "status")
    splice_negative = _number(gene, "intersections", "splice_core_pm2", "added_comparator_negative_bp")
    callable_cds_rate = _number(gene, "callable_cds_negative_fill_rate")
    gene_precision = _number(gene, "gene_overlap_added_bp_precision")
    max_cds_negative = _number(gene, "max_single_annotated_cds_negative_bp")
    source_ready = source_status == "PASS"
    return _all_gate(
        "Selected fills satisfy all frozen gene-feature safety limits.",
        {
            "gene_safety_status_is_PASS": True if source_ready else None,
            "splice_core_pm2_negative_bp_eq_0": (
                None if not source_ready or splice_negative is None else splice_negative == 0
            ),
            "callable_cds_negative_fill_rate_le_1e-5": (
                None if not source_ready or callable_cds_rate is None else callable_cds_rate <= 1e-5
            ),
            "gene_overlap_added_bp_precision_ge_0.995": (
                None if not source_ready or gene_precision is None else gene_precision >= 0.995
            ),
            "max_single_cds_negative_bp_le_20": (
                None if not source_ready or max_cds_negative is None else max_cds_negative <= 20
            ),
        },
        {
            "gene_safety_status": source_status,
            "splice_core_pm2_negative_bp": splice_negative,
            "callable_cds_negative_fill_rate": callable_cds_rate,
            "gene_overlap_added_bp_precision": gene_precision,
            "max_single_annotated_cds_negative_bp": max_cds_negative,
        },
    )


def _twenty_percent_more(value: float | None, baseline: float | None) -> bool | None:
    if value is None or baseline is None:
        return None
    if baseline == 0:
        return value > 0
    return value >= 1.20 * baseline


def _twenty_percent_fewer(value: float | None, baseline: float | None) -> bool | None:
    if value is None or baseline is None:
        return None
    if baseline <= 0:
        return False
    return value <= 0.80 * baseline


def _ten_percent_greater_split_reduction(
    raw: float | None, g2: float | None, baseline: float | None,
) -> tuple[bool | None, float | None, float | None]:
    g2_reduction = _relative_decrease(raw, g2)
    baseline_reduction = _relative_decrease(raw, baseline)
    if g2_reduction is None or baseline_reduction is None:
        return None, g2_reduction, baseline_reduction
    if baseline_reduction <= 0:
        return g2_reduction > 0, g2_reduction, baseline_reduction
    return g2_reduction >= 1.10 * baseline_reduction, g2_reduction, baseline_reduction


def _relative_operating_comparison(
    candidate: dict[str, object], mask: dict[str, object],
) -> dict[str, object]:
    ranking = _value(candidate, "comparison", "best_ranking_baseline")
    expected = _value(candidate, "comparison", "best_operating_baseline")
    baseline = _value(mask, "metrics", "baseline")
    if not isinstance(baseline, dict):
        return {
            "status": "BLOCKED",
            "best_ranking_baseline": ranking,
            "best_operating_baseline": expected,
            "reason": "mask_fragment JSON lacks metrics.baseline",
        }
    baseline_status = baseline.get("status")
    observed = baseline.get("best_operating_baseline")
    if baseline_status == "NO_BASELINE_OPERATING_POINT" and expected is None:
        return {
            "status": "BASELINE_UNAVAILABLE",
            "best_ranking_baseline": ranking,
            "best_operating_baseline": None,
            "reason": baseline.get("reason"),
        }
    if baseline_status != "EVALUATED" or not isinstance(expected, str) or observed != expected:
        return {
            "status": "BLOCKED",
            "best_ranking_baseline": ranking,
            "best_operating_baseline": expected,
            "mask_baseline_status": baseline_status,
            "mask_best_operating_baseline": observed,
        }

    g2_positive = _number(mask, "metrics", "added_bp", "added_positive_bp")
    g2_negative = _number(mask, "metrics", "added_bp", "added_negative_bp")
    baseline_positive = _number(baseline, "added_bp", "added_positive_bp")
    baseline_negative = _number(baseline, "added_bp", "added_negative_bp")
    raw_split = _number(mask, "metrics", "fragmentation", "raw", "split_rate")
    g2_split = _number(mask, "metrics", "fragmentation", "refined", "split_rate")
    baseline_split = _number(baseline, "fragmentation", "refined", "split_rate")
    positive_gain = _twenty_percent_more(g2_positive, baseline_positive)
    negative_reduction = _twenty_percent_fewer(g2_negative, baseline_negative)
    split_gain, g2_split_reduction, baseline_split_reduction = _ten_percent_greater_split_reduction(
        raw_split, g2_split, baseline_split,
    )
    options = {
        "positive_gap_bp_ge_20_percent_more": positive_gain,
        "negative_bp_ge_20_percent_fewer": negative_reduction,
        "split_reduction_ge_10_percent_greater": split_gain,
    }
    if any(value is True for value in options.values()):
        status = "PASS"
    elif any(value is None for value in options.values()):
        status = "BLOCKED"
    else:
        status = "FAIL"
    return {
        "status": status,
        "best_ranking_baseline": ranking,
        "best_operating_baseline": expected,
        "selection_contract": "both baseline identities and operating thresholds were frozen on chr13; no chr19 threshold selection",
        "options": options,
        "observed": {
            "g2_added_positive_bp": g2_positive,
            "baseline_added_positive_bp": baseline_positive,
            "g2_added_negative_bp": g2_negative,
            "baseline_added_negative_bp": baseline_negative,
            "raw_split_rate": raw_split,
            "g2_split_rate": g2_split,
            "baseline_split_rate": baseline_split,
            "g2_split_relative_decrease": g2_split_reduction,
            "baseline_split_relative_decrease": baseline_split_reduction,
        },
    }


def decide_phase0(
    candidate_path: Path, mask_fragment_path: Path, gene_safety_path: Path, output_path: Path,
) -> dict[str, object]:
    candidate = _read_json(candidate_path)
    mask = _read_json(mask_fragment_path)
    gene = _read_json(gene_safety_path)
    gate1, gate2, gate3 = _candidate_gates(candidate)
    gate4, gate5, gate6, gate7 = _mask_gates(mask)
    gate8 = _gene_gate(gene)
    gates = {
        "1_test_denominator": gate1,
        "2_candidate_information_gain": gate2,
        "3_library_free_persistence": gate3,
        "4_added_bp_precision": gate4,
        "5_internal_gap_recall": gate5,
        "6_fragment_reduction": gate6,
        "7_whole_mask_guardrails": gate7,
        "8_gene_feature_safety": gate8,
    }
    relative = _relative_operating_comparison(candidate, mask)
    gate_statuses = [gate["status"] for gate in gates.values()]
    if "FAIL" in gate_statuses or relative["status"] == "FAIL":
        status = "FAIL"
    elif all(value == "PASS" for value in gate_statuses) and relative["status"] == "PASS":
        status = "PASS"
    else:
        status = "BLOCKED"
    result: dict[str, object] = {
        "schema": "gap_bridge_phase0_gate_decision_v1",
        "status": status,
        "test_chromosome": "chr19",
        "inputs": {
            "candidate_evaluation": str(candidate_path),
            "mask_fragment": str(mask_fragment_path),
            "gene_safety": str(gene_safety_path),
        },
        "deployment_group": G2,
        "gates": gates,
        "relative_operating_comparison": relative,
        "pass_count": sum(value == "PASS" for value in gate_statuses),
        "fail_count": sum(value == "FAIL" for value in gate_statuses),
        "blocked_count": sum(value == "BLOCKED" for value in gate_statuses),
        "decision_rule": "PASS requires all eight prospective gates and the frozen operating-point comparison to PASS",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-evaluation", required=True, type=Path)
    parser.add_argument("--mask-fragment", required=True, type=Path)
    parser.add_argument("--gene-safety", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    result = decide_phase0(args.candidate_evaluation, args.mask_fragment, args.gene_safety, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
