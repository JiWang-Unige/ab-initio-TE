#!/usr/bin/env python3
"""T1-positive evaluator. This is the only module permitted to read hidden truth."""

from __future__ import annotations

import argparse
import collections
import itertools
import math
import random
from pathlib import Path

from common import atomic_write_json, read_json, read_tsv, stable_token, write_tsv


SUMMARY_FIELDS = [
    "method", "leaf_count", "parent_count", "mapped_leaf_fraction", "leaf_retention",
    "exact_truth_group_recovery", "complete_truth_group_recovery", "pairwise_same_parent_purity",
    "pairwise_same_parent_recall", "pairwise_same_parent_harmonic", "cross_rm_id_false_fusion_proxy",
    "false_fusion_safety", "mean_truth_fragmentation_count", "topology_truth_group_count", "truth_topology_preservation", "matched_left_boundary_error_bp",
    "matched_right_boundary_error_bp", "matched_boundary_within_5bp", "matched_boundary_within_10bp",
    "matched_boundary_within_25bp", "matched_boundary_within_50bp",
]
STRATUM_FIELDS = ["stratum_key", "stratum_value", *SUMMARY_FIELDS]


def make_parent_rows(public_rows: list[dict[str, str]], method: str, maximum_gap: int | None) -> list[dict[str, object]]:
    by_contig: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for row in public_rows:
        by_contig[row["seqid"]].append(row)
    parents = []
    for seqid in sorted(by_contig):
        leaves = sorted(by_contig[seqid], key=lambda row: (int(row["start0"]), int(row["end0"]), row["leaf_id"]))
        paths: list[list[dict[str, str]]] = []
        current: list[dict[str, str]] = []
        current_end = -1
        for leaf in leaves:
            if not current or maximum_gap is None or int(leaf["start0"]) - current_end > maximum_gap:
                if current:
                    paths.append(current)
                current = [leaf]
                current_end = int(leaf["end0"])
            else:
                current.append(leaf)
                current_end = max(current_end, int(leaf["end0"]))
        if current:
            paths.append(current)
        for path in paths:
            child_ids = sorted(row["leaf_id"] for row in path)
            parents.append({
                "parent_id": "parent_" + stable_token(method, *child_ids),
                "seqid": seqid,
                "start0": min(int(row["start0"]) for row in path),
                "end0": max(int(row["end0"]) for row in path),
                "child_leaf_ids": ",".join(child_ids),
                "child_count": len(child_ids),
                "partition_kind": method,
            })
    return parents


def harmonic(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2.0 * precision * recall / (precision + recall)


def parse_parent_sets(parents: list[dict[str, object]], public_ids: set[str]) -> tuple[dict[str, set[str]], dict[str, str]]:
    sets: dict[str, set[str]] = {}
    assignment: dict[str, str] = {}
    for parent in parents:
        parent_id = str(parent["parent_id"])
        children = {value for value in str(parent["child_leaf_ids"]).split(",") if value}
        if not children or not children <= public_ids:
            raise ValueError(f"parent {parent_id} has empty/unknown children")
        for child in children:
            if child in assignment:
                raise ValueError(f"leaf assigned more than once: {child}")
            assignment[child] = parent_id
        sets[parent_id] = children
    if set(assignment) != public_ids:
        raise ValueError("leaf retention/exactly-once invariant failed in evaluator")
    return sets, assignment


def evaluate_method_with_stats(method: str, public_rows: list[dict[str, str]], truth_rows: list[dict[str, str]], parents: list[dict[str, object]], mapped_ids: set[str], tolerances: list[int]) -> tuple[dict[str, float | int | str], dict[str, int]]:
    public_ids = {row["leaf_id"] for row in public_rows}
    if len(public_ids) != len(public_rows):
        raise ValueError("duplicate public leaf ID")
    truth_by_leaf = {row["leaf_id"]: row for row in truth_rows}
    if set(truth_by_leaf) != public_ids:
        raise ValueError("public and evaluator truth leaf IDs differ")
    predicted_sets, assignment = parse_parent_sets(parents, public_ids)
    truth_sets: dict[str, set[str]] = collections.defaultdict(set)
    for row in truth_rows:
        truth_sets[row["truth_group_id"]].add(row["leaf_id"])

    exact = sum(1 for truth_set in truth_sets.values() if truth_set in predicted_sets.values())
    complete = sum(1 for truth_set in truth_sets.values() if any(truth_set <= predicted for predicted in predicted_sets.values()))
    truth_pair_count = correct_pair_count = predicted_pair_count = 0
    for truth_set in truth_sets.values():
        for left, right in itertools.combinations(sorted(truth_set), 2):
            truth_pair_count += 1
            correct_pair_count += int(assignment[left] == assignment[right])
    for predicted in predicted_sets.values():
        for left, right in itertools.combinations(sorted(predicted), 2):
            predicted_pair_count += 1
    incorrect_predicted_pairs = 0
    for predicted in predicted_sets.values():
        for left, right in itertools.combinations(sorted(predicted), 2):
            incorrect_predicted_pairs += int(truth_by_leaf[left]["truth_group_id"] != truth_by_leaf[right]["truth_group_id"])
    pair_purity = 1.0 if predicted_pair_count == 0 else (predicted_pair_count - incorrect_predicted_pairs) / predicted_pair_count
    pair_recall = 0.0 if truth_pair_count == 0 else correct_pair_count / truth_pair_count

    fragmentation_counts = []
    left_errors: list[int] = []
    right_errors: list[int] = []
    boundary_within = {tolerance: 0 for tolerance in tolerances}
    topology_total = topology_preserved = 0
    for truth_id, truth_set in truth_sets.items():
        overlapping = [(parent_id, len(truth_set & predicted)) for parent_id, predicted in predicted_sets.items() if truth_set & predicted]
        fragmentation_counts.append(len(overlapping))
        best_id = sorted(overlapping, key=lambda item: (-item[1], item[0]))[0][0]
        best = next(parent for parent in parents if str(parent["parent_id"]) == best_id)
        first_truth = truth_by_leaf[next(iter(truth_set))]
        left_error = abs(int(best["start0"]) - int(first_truth["truth_parent_start0"]))
        right_error = abs(int(best["end0"]) - int(first_truth["truth_parent_end0"]))
        left_errors.append(left_error)
        right_errors.append(right_error)
        for tolerance in tolerances:
            boundary_within[tolerance] += int(left_error <= tolerance and right_error <= tolerance)
        if any(truth_by_leaf[leaf]["overlap_marker"].lower() == "true" for leaf in truth_set):
            topology_total += 1
            topology_preserved += int(predicted_sets[best_id] == truth_set)

    group_count = len(truth_sets)
    false_fusion = 0.0 if predicted_pair_count == 0 else incorrect_predicted_pairs / predicted_pair_count
    result: dict[str, float | int | str] = {
        "method": method,
        "leaf_count": len(public_rows),
        "parent_count": len(parents),
        "mapped_leaf_fraction": len(mapped_ids & public_ids) / len(public_ids),
        "leaf_retention": len(assignment) / len(public_ids),
        "exact_truth_group_recovery": exact / group_count,
        "complete_truth_group_recovery": complete / group_count,
        "pairwise_same_parent_purity": pair_purity,
        "pairwise_same_parent_recall": pair_recall,
        "pairwise_same_parent_harmonic": harmonic(pair_purity, pair_recall),
        "cross_rm_id_false_fusion_proxy": false_fusion,
        "false_fusion_safety": 1.0 - false_fusion,
        "mean_truth_fragmentation_count": sum(fragmentation_counts) / len(fragmentation_counts),
        "topology_truth_group_count": topology_total,
        # Zero registered topology groups is unevaluable, never vacuous perfection.
        "truth_topology_preservation": 0.0 if topology_total == 0 else topology_preserved / topology_total,
        "matched_left_boundary_error_bp": sum(left_errors) / len(left_errors),
        "matched_right_boundary_error_bp": sum(right_errors) / len(right_errors),
    }
    for tolerance in tolerances:
        result[f"matched_boundary_within_{tolerance}bp"] = boundary_within[tolerance] / group_count
    stats = {
        "leaf_count": len(public_rows), "parent_count": len(parents),
        "mapped_leaf_count": len(mapped_ids & public_ids), "assigned_leaf_count": len(assignment),
        "truth_group_count": group_count, "exact_group_count": exact, "complete_group_count": complete,
        "truth_pair_count": truth_pair_count, "correct_pair_count": correct_pair_count,
        "predicted_pair_count": predicted_pair_count, "incorrect_predicted_pair_count": incorrect_predicted_pairs,
        "fragmentation_count_sum": sum(fragmentation_counts), "left_error_sum": sum(left_errors),
        "right_error_sum": sum(right_errors), "topology_total": topology_total,
        "topology_preserved": topology_preserved,
    }
    for tolerance in tolerances:
        stats[f"boundary_within_{tolerance}_count"] = boundary_within[tolerance]
    return result, stats


def evaluate_method(method: str, public_rows: list[dict[str, str]], truth_rows: list[dict[str, str]], parents: list[dict[str, object]], mapped_ids: set[str], tolerances: list[int]) -> dict[str, float | int | str]:
    return evaluate_method_with_stats(method, public_rows, truth_rows, parents, mapped_ids, tolerances)[0]


def validate_method_result(result: dict[str, object], schema: dict) -> None:
    expected, observed = set(schema["required_method_fields"]), set(result)
    if expected != observed:
        raise ValueError(f"method result schema mismatch: missing={sorted(expected-observed)}, unexpected={sorted(observed-expected)}")
    for field in schema["finite_numeric_fields"]:
        value = result[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"method result field is not finite numeric: {field}={value!r}")


def validate_metrics_payload(metrics: dict[str, object], config: dict) -> None:
    expected, observed = set(config["result_schema"]["required_metrics_fields"]), set(metrics)
    if expected != observed:
        raise ValueError(f"metrics payload schema mismatch: missing={sorted(expected-observed)}, unexpected={sorted(observed-expected)}")

    def visit(value: object, path: str) -> None:
        if isinstance(value, bool) or value is None or isinstance(value, str):
            return
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                raise ValueError(f"metrics payload contains non-finite numeric value at {path}")
            return
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, f"{path}.{key}")
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
            return
        raise ValueError(f"metrics payload contains unsupported value at {path}: {type(value).__name__}")

    visit(metrics, "metrics")


def summarize_bootstrap(values: list[float]) -> dict[str, float | int | bool]:
    if not values:
        return {"evaluable": False, "valid_replicates": 0}
    values.sort()
    return {"evaluable": True, "valid_replicates": len(values), "mean": sum(values) / len(values), "low": values[int(0.025 * len(values))], "high": values[min(len(values) - 1, int(0.975 * len(values)))]}


def exact_group_vector(truth_rows: list[dict[str, str]], parents: list[dict[str, object]]) -> list[float]:
    truth_sets: dict[str, set[str]] = collections.defaultdict(set)
    for row in truth_rows:
        truth_sets[row["truth_group_id"]].add(row["leaf_id"])
    predicted_sets = [{value for value in str(parent["child_leaf_ids"]).split(",") if value} for parent in parents]
    return [float(truth_sets[group_id] in predicted_sets) for group_id in sorted(truth_sets)]


def restrict_parents(parents: list[dict[str, object]], public_ids: set[str], public_by_leaf: dict[str, dict[str, str]], suffix: str) -> list[dict[str, object]]:
    restricted = []
    for parent in parents:
        children = {value for value in str(parent["child_leaf_ids"]).split(",") if value} & public_ids
        if not children:
            continue
        child_ids = sorted(children)
        child_rows = [public_by_leaf[child_id] for child_id in child_ids]
        restricted.append({
            **parent,
            "parent_id": "parent_" + stable_token(parent["parent_id"], suffix, *child_ids),
            "seqid": child_rows[0]["seqid"],
            "start0": min(int(row["start0"]) for row in child_rows),
            "end0": max(int(row["end0"]) for row in child_rows),
            "child_leaf_ids": ",".join(child_ids),
            "child_count": len(child_ids),
        })
    return restricted


def comparator_maxima(by_method: dict[str, dict[str, object]], promotion_metrics: dict) -> dict[str, dict[str, object]]:
    comparator_ids = ("POSITIVE_ONLY_GAP20", "POSITIVE_ONLY_GAP100")
    maxima: dict[str, dict[str, object]] = {}
    for metric, spec in promotion_metrics.items():
        if not spec["comparator_required"]:
            continue
        if spec["direction"] != "higher":
            raise ValueError(f"promotion metric must use higher-is-better representation: {metric}")
        method = max(comparator_ids, key=lambda name: (float(by_method[name][metric]), name))
        maxima[metric] = {"method": method, "value": float(by_method[method][metric])}
    return maxima


def pooled_metric(stats_rows: list[dict[str, int]], metric: str) -> float | None:
    total = lambda field: sum(row[field] for row in stats_rows)
    leaf_count, group_count = total("leaf_count"), total("truth_group_count")
    predicted_pairs, truth_pairs = total("predicted_pair_count"), total("truth_pair_count")
    if metric == "mapped_leaf_fraction": return total("mapped_leaf_count") / leaf_count
    if metric == "leaf_retention": return total("assigned_leaf_count") / leaf_count
    if metric == "exact_truth_group_recovery": return total("exact_group_count") / group_count
    if metric == "complete_truth_group_recovery": return total("complete_group_count") / group_count
    purity = 1.0 if predicted_pairs == 0 else (predicted_pairs - total("incorrect_predicted_pair_count")) / predicted_pairs
    recall = 0.0 if truth_pairs == 0 else total("correct_pair_count") / truth_pairs
    if metric == "pairwise_same_parent_purity": return purity
    if metric == "pairwise_same_parent_recall": return recall
    if metric == "pairwise_same_parent_harmonic": return harmonic(purity, recall)
    false_fusion = 0.0 if predicted_pairs == 0 else total("incorrect_predicted_pair_count") / predicted_pairs
    if metric == "cross_rm_id_false_fusion_proxy": return false_fusion
    if metric == "false_fusion_safety": return 1.0 - false_fusion
    if metric == "mean_truth_fragmentation_count": return total("fragmentation_count_sum") / group_count
    if metric == "topology_truth_group_count": return float(total("topology_total"))
    if metric == "truth_topology_preservation":
        topology_total = total("topology_total")
        return None if topology_total == 0 else total("topology_preserved") / topology_total
    if metric == "matched_left_boundary_error_bp": return total("left_error_sum") / group_count
    if metric == "matched_right_boundary_error_bp": return total("right_error_sum") / group_count
    for tolerance in (5, 10, 25, 50):
        if metric == f"matched_boundary_within_{tolerance}bp":
            return total(f"boundary_within_{tolerance}_count") / group_count
    if metric == "leaf_count": return float(leaf_count)
    if metric == "parent_count": return float(total("parent_count"))
    raise KeyError(metric)


def promotion_uncertainty(config: dict, chromosome_stats: dict[str, dict[str, dict[str, int]]]) -> dict[str, object]:
    chromosomes = sorted(next(iter(chromosome_stats.values())))
    expected_methods = {"CONSENSUS_COLLINEARITY", "EVIDENCE_SHUFFLE_NULL", "POSITIVE_ONLY_GAP20", "POSITIVE_ONLY_GAP100"}
    if not expected_methods <= set(chromosome_stats) or any(set(chromosome_stats[method]) != set(chromosomes) for method in expected_methods):
        raise ValueError("chromosome-paired uncertainty matrix is incomplete")
    replicates = int(config["evaluation"]["bootstrap_replicates"])
    base_seed = int(config["evaluation"]["bootstrap_seed"])
    result: dict[str, object] = {"unit": "primary_chromosome_block", "estimand": "pooled_sufficient_statistics", "replicates": replicates, "metrics": {}}
    for index, (metric, spec) in enumerate(config["promotion_metrics"].items()):
        rng = random.Random(base_seed + index)
        candidate_values: list[float] = []
        comparator_deltas: list[float] = []
        null_deltas: list[float] = []
        selection_counts = {"POSITIVE_ONLY_GAP20": 0, "POSITIVE_ONLY_GAP100": 0}
        for _ in range(replicates):
            sampled = [chromosomes[rng.randrange(len(chromosomes))] for _ in chromosomes]
            pooled = {
                method: pooled_metric([chromosome_stats[method][chromosome] for chromosome in sampled], metric)
                for method in expected_methods
            }
            candidate_value = pooled["CONSENSUS_COLLINEARITY"]
            if candidate_value is None:
                # A block draw with no topology truth is not a perfect score; it is unevaluable.
                continue
            candidate_values.append(candidate_value)
            if spec["comparator_required"]:
                available = [(float(pooled[name]), name) for name in selection_counts if pooled[name] is not None]
                if not available:
                    continue
                comparator_value, comparator = max(available)
                selection_counts[comparator] += 1
                comparator_deltas.append(candidate_value - comparator_value)
            if metric == "exact_truth_group_recovery":
                if pooled["EVIDENCE_SHUFFLE_NULL"] is None:
                    raise AssertionError("exact-recovery null estimand unexpectedly missing")
                null_deltas.append(candidate_value - float(pooled["EVIDENCE_SHUFFLE_NULL"]))
        entry: dict[str, object] = {"candidate": summarize_bootstrap(candidate_values)}
        if spec["comparator_required"]:
            entry["comparator_reselected_per_replicate"] = True
            entry["comparator_selection_counts"] = selection_counts
            entry["candidate_minus_comparator_max"] = summarize_bootstrap(comparator_deltas)
        if metric == "exact_truth_group_recovery":
            entry["candidate_minus_evidence_shuffle_null"] = summarize_bootstrap(null_deltas)
        result["metrics"][metric] = entry
    if set(result["metrics"]) != set(config["promotion_metrics"]):
        raise AssertionError("paired uncertainty does not cover every promotion metric")
    return result


def evaluate_all(config: dict, public_path: Path, truth_path: Path, evidence_path: Path, method_parent_paths: dict[str, Path], out_dir: Path) -> dict:
    forbidden = set(config["evaluation"]["forbidden_metrics"])
    allowlist = set(config["evaluation"]["allowed_t1_metrics"])
    schema_metrics = set(config["result_schema"]["required_method_fields"]) - {"method"}
    if allowlist != schema_metrics or set(config["result_schema"]["finite_numeric_fields"]) != allowlist:
        raise ValueError("T1 metric allowlist and exact finite method schema differ")
    if forbidden & allowlist:
        raise ValueError("forbidden metric present in allowed T1 metrics")
    public_rows, truth_rows, evidence_rows = read_tsv(public_path), read_tsv(truth_path), read_tsv(evidence_path)
    mapped_ids = {row["leaf_id"] for row in evidence_rows if row["mapping_status"] == "MAPPED"}
    methods: dict[str, list[dict[str, object]]] = {
        "RAW_SINGLETON": make_parent_rows(public_rows, "RAW_SINGLETON", None),
        "POSITIVE_ONLY_GAP20": make_parent_rows(public_rows, "POSITIVE_ONLY_GAP20", int(config["controls"]["comparators"]["POSITIVE_ONLY_GAP20"]["maximum_genomic_gap_bp"])),
        "POSITIVE_ONLY_GAP100": make_parent_rows(public_rows, "POSITIVE_ONLY_GAP100", int(config["controls"]["comparators"]["POSITIVE_ONLY_GAP100"]["maximum_genomic_gap_bp"])),
    }
    for method, path in method_parent_paths.items():
        methods[method] = read_tsv(path)
    results = [evaluate_method(method, public_rows, truth_rows, parents, mapped_ids, list(config["evaluation"]["boundary_tolerances_bp"])) for method, parents in methods.items()]
    for result in results:
        validate_method_result(result, config["result_schema"])
    write_tsv(out_dir / "method_metrics.tsv", results, SUMMARY_FIELDS)
    by_method = {str(row["method"]): row for row in results}
    candidate = by_method["CONSENSUS_COLLINEARITY"]
    comparator_max_by_metric = comparator_maxima(by_method, config["promotion_metrics"])
    null = by_method["EVIDENCE_SHUFFLE_NULL"]
    gates = config["stop_gates"]
    checks = {
        "mapped_leaf_fraction": float(candidate["mapped_leaf_fraction"]) >= float(gates["minimum_mapped_leaf_fraction"]),
        "exact_group_delta_over_comparator_max": float(candidate["exact_truth_group_recovery"]) - float(comparator_max_by_metric["exact_truth_group_recovery"]["value"]) >= float(gates["minimum_exact_group_recovery_delta_over_comparator_max"]),
        "pairwise_harmonic_delta_over_comparator_max": float(candidate["pairwise_same_parent_harmonic"]) - float(comparator_max_by_metric["pairwise_same_parent_harmonic"]["value"]) >= float(gates["minimum_pairwise_harmonic_delta_over_comparator_max"]),
        "false_fusion_proxy": float(candidate["cross_rm_id_false_fusion_proxy"]) <= float(gates["maximum_cross_rm_id_false_fusion_proxy"]),
        "false_fusion_safety_delta_over_comparator_max": float(candidate["false_fusion_safety"]) - float(comparator_max_by_metric["false_fusion_safety"]["value"]) >= float(gates["minimum_false_fusion_safety_delta_over_comparator_max"]),
        "exact_group_delta_over_shuffle_null": float(candidate["exact_truth_group_recovery"]) - float(null["exact_truth_group_recovery"]) >= float(gates["minimum_exact_group_recovery_delta_over_shuffle_null"]),
        "truth_topology_minimum": float(candidate["truth_topology_preservation"]) >= float(gates["minimum_truth_topology_preservation"]),
        "truth_topology_evaluable": int(candidate["topology_truth_group_count"]) >= int(gates["minimum_topology_truth_group_count"]),
        "truth_topology_delta_over_comparator_max": float(candidate["truth_topology_preservation"]) - float(comparator_max_by_metric["truth_topology_preservation"]["value"]) >= float(gates["minimum_truth_topology_delta_over_comparator_max"]),
        "leaf_retention_exact": math.isclose(float(candidate["leaf_retention"]), 1.0),
    }
    for tolerance in config["evaluation"]["boundary_tolerances_bp"]:
        metric = f"matched_boundary_within_{tolerance}bp"
        checks[f"boundary{tolerance}_delta_over_comparator_max"] = float(candidate[metric]) - float(comparator_max_by_metric[metric]["value"]) >= float(gates["minimum_boundary_delta_over_comparator_max"][str(tolerance)])
    information_sufficient = all(checks.values())
    strata_rows: list[dict[str, object]] = []
    chromosome_stats: dict[str, dict[str, dict[str, int]]] = {method: {} for method in methods}
    public_by_leaf = {row["leaf_id"]: row for row in public_rows}
    for stratum_key in config["evaluation"]["report_strata"]:
        for stratum_value in sorted({row[stratum_key] for row in truth_rows}):
            stratum_truth = [row for row in truth_rows if row[stratum_key] == stratum_value]
            stratum_ids = {row["leaf_id"] for row in stratum_truth}
            stratum_public = [public_by_leaf[leaf_id] for leaf_id in sorted(stratum_ids)]
            for method, parents in methods.items():
                result, sufficient = evaluate_method_with_stats(method, stratum_public, stratum_truth, restrict_parents(parents, stratum_ids, public_by_leaf, f"{stratum_key}:{stratum_value}"), mapped_ids, list(config["evaluation"]["boundary_tolerances_bp"]))
                validate_method_result(result, config["result_schema"])
                strata_rows.append({"stratum_key": stratum_key, "stratum_value": stratum_value, **result})
                if stratum_key == "seqid":
                    chromosome_stats[method][str(stratum_value)] = sufficient
    write_tsv(out_dir / "method_stratum_metrics.tsv", strata_rows, STRATUM_FIELDS)
    paired_uncertainty = promotion_uncertainty(config, chromosome_stats)
    metrics = {
        "schema_version": "FRAG-CONSENSUS-COLLINEARITY-METRICS-1.0.0",
        "exp_id": config["exp_id"],
        "profile": config["profile"],
        "truth_tier": "T1",
        "claim_eligible": False,
        "semantic_success": True,
        "scientific_screen_executed": True,
        "primary_metric_name": "information_sufficiency_gate_pass",
        "primary_metric": 1.0 if information_sufficient else 0.0,
        "information_sufficiency_gate_pass": information_sufficient,
        "terminal_status": "INFORMATION_SUFFICIENT_FOR_BOUNDED_FOLLOWUP" if information_sufficient else "VALID_NEGATIVE_INFORMATION_INSUFFICIENT",
        "whole_genome_metrics_authorized": False,
        "methods": by_method,
        "stop_gate_checks": checks,
        "comparator_max_by_promotion_metric": comparator_max_by_metric,
        "paired_bootstrap_uncertainty": paired_uncertainty,
        "stratum_metric_path": "method_stratum_metrics.tsv",
    }
    validate_metrics_payload(metrics, config)
    atomic_write_json(out_dir / "metrics.json", metrics)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--public-leaves", required=True, type=Path)
    parser.add_argument("--truth", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--candidate-parents", required=True, type=Path)
    parser.add_argument("--null-parents", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    config = read_json(args.config)
    evaluate_all(config, args.public_leaves, args.truth, args.evidence, {"CONSENSUS_COLLINEARITY": args.candidate_parents, "EVIDENCE_SHUFFLE_NULL": args.null_parents}, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
