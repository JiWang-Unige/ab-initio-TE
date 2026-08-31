#!/usr/bin/env python3
"""Evaluate frozen Gate L-P/L-D and combine them with an L-R result.

This command does not calculate L-R, Gate O, or Gate E.  Input construction
errors produce ``CONTRACT_INVALID`` and a non-zero exit; evaluable provenance
failures remain scientific ``NO_GO_LP`` results.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


LP_INTEGRITY_THRESHOLD = 1.0
LP_DEEP_THRESHOLD = 36 / 40
LP_UNSUPPORTED_POINT_THRESHOLD = 0.20
RESERVE_PAIRS = 20

LD_THRESHOLDS = {
    "resolved_multipart_loci": 30,
    "resolved_multipart_locus_packages": 20,
    "nested_relations": 20,
    "nested_relation_packages": 10,
    "distinct_locus_pairs": 30,
    "distinct_locus_pair_packages": 15,
    "positive_co_locus_atom_pairs": 50,
    "positive_co_locus_atom_pair_packages": 25,
    "mixed_unresolved_atoms": 15,
    "mixed_unresolved_atom_packages": 10,
}

PACKAGE_FIELDS = {
    "package_id", "role", "reserve_pair_rank", "unit_type", "assembly_id",
    "seqid", "feature_ids", "deep_audit_feature_id",
}
CONTEXT_FIELDS = {"package_id", "feature_id", "seqid", "start0", "end0"}
REGISTRY_FIELDS = {"evidence_code", "independent_of_fbti_endpoint"}
PROVENANCE_FIELDS = {
    "package_id", "feature_id", "manifest_assembly_id", "source_assembly_id",
    "manifest_seqid", "source_seqid", "manifest_start", "manifest_end",
    "source_start", "source_end", "source_feature_id", "evidence_packet_id",
    "evidence_codes", "deep_audit", "anchor_interpretability", "audit_note",
}
REVIEW_FIELDS = {"package_id", "actor_id", "package_status"}
LOCUS_FIELDS = {"package_id", "actor_id", "locus_id", "locus_status"}
MATERIAL_FIELDS = {
    "package_id", "actor_id", "segment_id", "locus_id", "start", "end",
    "locus_assignment_status",
}
BOUNDARY_FIELDS = {
    "package_id", "actor_id", "locus_id", "side", "identifiability",
    "lower_pos", "upper_pos", "evidence_codes",
}
RELATION_FIELDS = {
    "package_id", "actor_id", "relation_id", "relation_type",
    "subject_locus_id", "object_locus_id",
}
PROJECTION_FIELDS = {
    "package_id", "atom_id", "seqid", "start", "end", "assignment",
    "assigned_locus_id", "assigned_segment_ids", "projection_eligibility",
}


class ContractError(ValueError):
    """An input/schema/construction error outside the scientific gate."""


def read_tsv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        if fields is None:
            raise ContractError(f"missing TSV header: {path}")
        missing = sorted(required - set(fields))
        if missing:
            raise ContractError(f"{path} missing fields: {missing}")
        rows = list(reader)
    if any(value is None for row in rows for value in row.values()):
        raise ContractError(f"malformed TSV row: {path}")
    return rows


def _integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ContractError(f"invalid integer for {label}: {value!r}") from error


def _ratio_metric(
    numerator: int, denominator: int, threshold: float, operator: str,
) -> dict[str, Any]:
    value = numerator / denominator if denominator else 0.0
    passed = value >= threshold if operator == ">=" else value <= threshold
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "threshold": threshold,
        "operator": operator,
        "passed": passed,
    }


def _count_metric(value: int, threshold: int) -> dict[str, Any]:
    return {
        "numerator": value,
        "denominator": None,
        "value": value,
        "threshold": threshold,
        "operator": ">=",
        "passed": value >= threshold,
    }


def _index_packages(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    packages: dict[str, dict[str, str]] = {}
    reserve_by_rank: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        package_id = row["package_id"]
        if not package_id or package_id in packages:
            raise ContractError(f"duplicate or empty package_id: {package_id!r}")
        if row["role"] not in {"calibration", "main", "reserve"}:
            raise ContractError(f"invalid package role: {package_id}/{row['role']}")
        if row["unit_type"] not in {"S0", "S1"}:
            raise ContractError(f"invalid unit_type: {package_id}/{row['unit_type']}")
        if not row["assembly_id"] or not row["seqid"]:
            raise ContractError(f"empty assembly/seqid: {package_id}")
        feature_ids = row["feature_ids"].split(",") if row["feature_ids"] else []
        if not feature_ids or feature_ids != sorted(set(feature_ids)):
            raise ContractError(f"feature_ids must be non-empty, unique and sorted: {package_id}")
        if row["role"] == "reserve":
            rank = _integer(row["reserve_pair_rank"], f"{package_id}.reserve_pair_rank")
            reserve_by_rank[rank].append(row)
        elif row["reserve_pair_rank"]:
            raise ContractError(f"non-reserve package has reserve_pair_rank: {package_id}")
        packages[package_id] = row

    main = [row for row in rows if row["role"] == "main"]
    if len(main) != 120 or {row["unit_type"] for row in main} != {"S0", "S1"}:
        raise ContractError("package manifest must contain the fixed 120-package main panel")
    if sum(row["unit_type"] == "S0" for row in main) != 60:
        raise ContractError("main panel must contain 60 S0 and 60 S1 packages")
    if set(reserve_by_rank) != set(range(1, RESERVE_PAIRS + 1)):
        raise ContractError("reserve_pair_rank must cover exactly 1..20")
    for rank, pair in reserve_by_rank.items():
        if len(pair) != 2 or {row["unit_type"] for row in pair} != {"S0", "S1"}:
            raise ContractError(f"reserve rank {rank} is not one S0/S1 pair")
    return packages


def _active_packages(
    packages: dict[str, dict[str, str]], reviews: list[dict[str, str]],
) -> tuple[set[str], int, dict[int, list[str]]]:
    active: set[str] = set()
    for row in reviews:
        package_id = row["package_id"]
        if row["actor_id"] != "ADJ":
            raise ContractError(f"package review is not ADJ: {package_id}")
        if package_id not in packages or package_id in active:
            raise ContractError(f"unknown or duplicate package review: {package_id}")
        if packages[package_id]["role"] == "calibration":
            raise ContractError(f"calibration package entered Gate L: {package_id}")
        active.add(package_id)

    main = {key for key, row in packages.items() if row["role"] == "main"}
    if not main <= active:
        raise ContractError("ADJ bundle does not contain every main package")
    reserve_pairs: dict[int, list[str]] = defaultdict(list)
    for package_id in active - main:
        row = packages[package_id]
        if row["role"] != "reserve":
            raise ContractError(f"unexpected active package: {package_id}")
        reserve_pairs[int(row["reserve_pair_rank"])].append(package_id)
    if reserve_pairs:
        maximum = max(reserve_pairs)
        if set(reserve_pairs) != set(range(1, maximum + 1)):
            raise ContractError("activated reserve ranks are not a contiguous prefix")
        for rank, package_ids in reserve_pairs.items():
            expected = {
                key for key, row in packages.items()
                if row["role"] == "reserve" and int(row["reserve_pair_rank"]) == rank
            }
            if set(package_ids) != expected:
                raise ContractError(f"activated reserve rank {rank} is not a complete S0/S1 pair")
    else:
        maximum = 0
    all_pairs = {
        rank: sorted(
            key for key, row in packages.items()
            if row["role"] == "reserve" and int(row["reserve_pair_rank"]) == rank
        )
        for rank in range(1, RESERVE_PAIRS + 1)
    }
    return active, maximum, all_pairs


def _context_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["package_id"], row["feature_id"])
        if not all(key) or key in result:
            raise ContractError(f"duplicate or empty context feature key: {key}")
        start = _integer(row["start0"], f"{key}.start0")
        end = _integer(row["end0"], f"{key}.end0")
        if start < 0 or end <= start:
            raise ContractError(f"invalid context interval: {key}")
        result[key] = row
    return result


def _registry(rows: list[dict[str, str]]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for row in rows:
        code = row["evidence_code"]
        if not code or code in result:
            raise ContractError(f"duplicate or empty evidence_code: {code!r}")
        if row["independent_of_fbti_endpoint"] not in {"0", "1"}:
            raise ContractError(f"invalid independent flag: {code}")
        result[code] = row["independent_of_fbti_endpoint"] == "1"
    return result


def _evidence_codes(value: str, registry: dict[str, bool]) -> list[str]:
    codes = [] if not value else value.split(",")
    if codes != sorted(set(codes)):
        raise ContractError("evidence_codes must be unique and sorted")
    unknown = [code for code in codes if code not in registry]
    if unknown:
        raise ContractError(f"unknown evidence_code: {unknown[0]}")
    return codes


def evaluate_lp(
    packages: dict[str, dict[str, str]],
    active: set[str],
    context: dict[tuple[str, str], dict[str, str]],
    registry: dict[str, bool],
    provenance: list[dict[str, str]],
    boundaries: list[dict[str, str]],
) -> dict[str, Any]:
    expected: dict[str, set[str]] = {}
    for package_id in active:
        features = set(packages[package_id]["feature_ids"].split(","))
        expected[package_id] = features
        missing = [feature for feature in features if (package_id, feature) not in context]
        if missing:
            raise ContractError(f"context missing anchor feature: {package_id}/{missing[0]}")

    rows_by_package: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in provenance:
        if row["package_id"] in active:
            rows_by_package[row["package_id"]].append(row)
    aligned: list[tuple[dict[str, str], dict[str, str], dict[str, str]]] = []
    for package_id, features in expected.items():
        rows = rows_by_package.get(package_id, [])
        if len(rows) != len(features):
            raise ContractError(f"provenance row count mismatch: {package_id}")
        used: set[str] = set()
        for row in rows:
            candidates = [
                feature for feature in (row["feature_id"], row["source_feature_id"])
                if feature in features
            ]
            if not candidates:
                raise ContractError(f"provenance row cannot be aligned: {package_id}")
            feature = candidates[0]
            if feature in used:
                raise ContractError(f"duplicate aligned provenance feature: {package_id}/{feature}")
            used.add(feature)
            aligned.append((row, packages[package_id], context[(package_id, feature)]))
        if used != features:
            raise ContractError(f"provenance feature coverage mismatch: {package_id}")

    denominator = len(aligned)
    assembly_pass = 0
    contig_pass = 0
    coordinate_pass = 0
    feature_pass = 0
    deep_expected: set[tuple[str, str]] = set()
    deep_good = 0
    for row, package, feature in aligned:
        feature_id = feature["feature_id"]
        key = (package["package_id"], feature_id)
        expected_deep = (
            package["role"] == "main"
            and package["deep_audit_feature_id"] == feature_id
        )
        if expected_deep:
            deep_expected.add(key)
        if row["deep_audit"] != ("1" if expected_deep else "0"):
            raise ContractError(f"deep_audit flag disagrees with manifest: {key}")
        evidence_codes = _evidence_codes(row["evidence_codes"], registry)
        if expected_deep and not evidence_codes:
            raise ContractError(f"deep anchor requires evidence_codes: {key}")
        interpretation = row["anchor_interpretability"]
        if expected_deep:
            if interpretation not in {
                "interpretable_extant_locus", "explicit_uncertain", "uninterpretable",
            }:
                raise ContractError(f"invalid deep anchor interpretation: {key}")
            if interpretation in {"explicit_uncertain", "uninterpretable"} and not row["audit_note"]:
                raise ContractError(f"deep anchor requires audit_note: {key}")
            deep_good += interpretation in {"interpretable_extant_locus", "explicit_uncertain"}
        elif interpretation:
            raise ContractError(f"non-deep provenance row has interpretation: {key}")

        assembly_pass += (
            row["manifest_assembly_id"] == package["assembly_id"]
            and row["source_assembly_id"] == package["assembly_id"]
        )
        contig_pass += (
            row["manifest_seqid"] == feature["seqid"] == package["seqid"]
            and row["source_seqid"] == feature["seqid"]
        )
        coordinate_pass += (
            row["manifest_start"] == feature["start0"]
            and row["manifest_end"] == feature["end0"]
            and row["source_start"] == feature["start0"]
            and row["source_end"] == feature["end0"]
        )
        feature_pass += row["feature_id"] == feature_id == row["source_feature_id"]

    if len(deep_expected) != 40:
        raise ContractError(f"main panel must contain exactly 40 deep-audit anchors, got {len(deep_expected)}")

    endpoints: dict[str, set[int]] = defaultdict(set)
    for package_id, features in expected.items():
        if packages[package_id]["role"] != "main":
            continue
        for feature_id in features:
            row = context[(package_id, feature_id)]
            endpoints[package_id].update((int(row["start0"]), int(row["end0"])))
    point_total = 0
    unsupported = 0
    seen_boundaries: set[tuple[str, str, str]] = set()
    for row in boundaries:
        package_id = row["package_id"]
        if package_id not in active:
            raise ContractError(f"boundary references inactive package: {package_id}")
        if row["actor_id"] != "ADJ":
            raise ContractError(f"boundary is not ADJ: {package_id}")
        boundary_key = (package_id, row["locus_id"], row["side"])
        if boundary_key in seen_boundaries:
            raise ContractError(f"duplicate boundary: {boundary_key}")
        seen_boundaries.add(boundary_key)
        codes = _evidence_codes(row["evidence_codes"], registry)
        if packages[package_id]["role"] != "main" or row["identifiability"] != "point":
            continue
        lower = _integer(row["lower_pos"], f"{boundary_key}.lower_pos")
        upper = _integer(row["upper_pos"], f"{boundary_key}.upper_pos")
        if lower != upper:
            raise ContractError(f"point boundary is not a point: {boundary_key}")
        point_total += 1
        copied = lower in endpoints[package_id]
        independently_supported = any(registry[code] for code in codes)
        unsupported += copied and not independently_supported

    checks = {
        "assembly_integrity": _ratio_metric(assembly_pass, denominator, 1.0, ">="),
        "contig_integrity": _ratio_metric(contig_pass, denominator, 1.0, ">="),
        "coordinate_integrity": _ratio_metric(coordinate_pass, denominator, 1.0, ">="),
        "feature_id_integrity": _ratio_metric(feature_pass, denominator, 1.0, ">="),
        "deep_anchor_interpretability": _ratio_metric(deep_good, 40, LP_DEEP_THRESHOLD, ">="),
        "unsupported_copied_point_fraction": _ratio_metric(
            unsupported, point_total, LP_UNSUPPORTED_POINT_THRESHOLD, "<="
        ),
    }
    return {"status": "PASS" if all(item["passed"] for item in checks.values()) else "NO_GO_LP", "checks": checks}


def _validate_adj_rows(
    active: set[str], rows: list[dict[str, str]], label: str,
) -> None:
    for row in rows:
        if row["package_id"] not in active:
            raise ContractError(f"{label} references inactive package: {row['package_id']}")
        if row["actor_id"] != "ADJ":
            raise ContractError(f"{label} row is not ADJ: {row['package_id']}")


def evaluate_ld(
    active: set[str],
    loci: list[dict[str, str]],
    materials: list[dict[str, str]],
    relations: list[dict[str, str]],
    projections: list[dict[str, str]],
) -> dict[str, Any]:
    _validate_adj_rows(active, loci, "loci")
    _validate_adj_rows(active, materials, "material_segments")
    _validate_adj_rows(active, relations, "relations")

    locus_status: dict[tuple[str, str], str] = {}
    for row in loci:
        key = (row["package_id"], row["locus_id"])
        if not row["locus_id"] or key in locus_status:
            raise ContractError(f"duplicate or empty ADJ locus: {key}")
        if row["locus_status"] not in {"resolved", "partially_resolved", "unresolved"}:
            raise ContractError(f"invalid locus_status: {key}")
        locus_status[key] = row["locus_status"]

    segments_by_locus: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for row in materials:
        if row["locus_assignment_status"] not in {"assigned", "unresolved"}:
            raise ContractError(f"invalid locus_assignment_status: {row['segment_id']}")
        if row["locus_assignment_status"] != "assigned":
            continue
        key = (row["package_id"], row["locus_id"])
        if key not in locus_status:
            raise ContractError(f"material references unknown locus: {key}")
        start = _integer(row["start"], f"{row['segment_id']}.start")
        end = _integer(row["end"], f"{row['segment_id']}.end")
        if end <= start:
            raise ContractError(f"invalid material interval: {row['segment_id']}")
        segments_by_locus[key].append((start, end))

    resolved_multipart: set[tuple[str, str]] = set()
    for key, segments in segments_by_locus.items():
        if locus_status[key] != "resolved" or len(segments) < 2:
            continue
        ordered = sorted(segments)
        if all(right[0] > left[1] for left, right in zip(ordered, ordered[1:])):
            resolved_multipart.add(key)

    atoms_by_locus: dict[tuple[str, str], set[str]] = defaultdict(set)
    mixed_unresolved: set[tuple[str, str]] = set()
    seen_atoms: set[tuple[str, str]] = set()
    for row in projections:
        package_id = row["package_id"]
        if package_id not in active:
            raise ContractError(f"atom projection references inactive package: {package_id}")
        atom_key = (package_id, row["atom_id"])
        if not row["atom_id"] or atom_key in seen_atoms:
            raise ContractError(f"duplicate or empty projected atom: {atom_key}")
        seen_atoms.add(atom_key)
        if row["projection_eligibility"] not in {"eligible", "package_censored"}:
            raise ContractError(f"invalid projection_eligibility: {atom_key}")
        if row["projection_eligibility"] == "package_censored":
            if row["assignment"] or row["assigned_locus_id"] or row["assigned_segment_ids"]:
                raise ContractError(f"package-censored atom must have blank projection fields: {atom_key}")
            continue
        if row["assignment"] not in {"unique", "mixed", "unassigned", "unresolved"}:
            raise ContractError(f"invalid atom assignment: {atom_key}")
        if row["assignment"] == "unique":
            locus_key = (package_id, row["assigned_locus_id"])
            if not row["assigned_locus_id"] or locus_key not in locus_status:
                raise ContractError(f"unique atom references unknown locus: {atom_key}")
            atoms_by_locus[locus_key].add(row["atom_id"])
        elif row["assigned_locus_id"]:
            raise ContractError(f"non-unique atom names a locus: {atom_key}")
        if row["assignment"] in {"mixed", "unresolved"}:
            mixed_unresolved.add(atom_key)

    nested: set[tuple[str, str, str]] = set()
    distinct: set[tuple[str, str, str]] = set()
    for row in relations:
        package_id = row["package_id"]
        subject = row["subject_locus_id"]
        obj = row["object_locus_id"]
        subject_key = (package_id, subject)
        object_key = (package_id, obj)
        if subject_key not in locus_status or object_key not in locus_status:
            raise ContractError(f"relation references unknown locus: {row['relation_id']}")
        eligible_endpoints = (
            locus_status[subject_key] != "unresolved"
            and locus_status[object_key] != "unresolved"
            and bool(atoms_by_locus.get(subject_key))
            and bool(atoms_by_locus.get(object_key))
        )
        if row["relation_type"] == "nested_in" and eligible_endpoints:
            nested.add((package_id, subject, obj))
        elif row["relation_type"] == "distinct_locus" and eligible_endpoints:
            left, right = sorted((subject, obj))
            distinct.add((package_id, left, right))

    positive_pairs: set[tuple[str, str, str, str]] = set()
    for locus_key, atoms in atoms_by_locus.items():
        if locus_status[locus_key] != "resolved":
            continue
        ordered = sorted(atoms)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                positive_pairs.add((locus_key[0], locus_key[1], left, right))

    observed = {
        "resolved_multipart_loci": len(resolved_multipart),
        "resolved_multipart_locus_packages": len({key[0] for key in resolved_multipart}),
        "nested_relations": len(nested),
        "nested_relation_packages": len({key[0] for key in nested}),
        "distinct_locus_pairs": len(distinct),
        "distinct_locus_pair_packages": len({key[0] for key in distinct}),
        "positive_co_locus_atom_pairs": len(positive_pairs),
        "positive_co_locus_atom_pair_packages": len({key[0] for key in positive_pairs}),
        "mixed_unresolved_atoms": len(mixed_unresolved),
        "mixed_unresolved_atom_packages": len({key[0] for key in mixed_unresolved}),
    }
    checks = {
        name: _count_metric(value, LD_THRESHOLDS[name])
        for name, value in observed.items()
    }
    return {"status": "PASS" if all(item["passed"] for item in checks.values()) else "SHORT", "checks": checks}


def combine_status(
    lp: dict[str, Any], lr: dict[str, Any], ld: dict[str, Any],
    active_reserve_pairs: int,
) -> str:
    lr_status = lr.get("status")
    if lr_status not in {
        "PASS", "NO_GO_LR", "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS",
    }:
        raise ContractError(f"invalid L-R status: {lr_status!r}")
    if lp["status"] == "NO_GO_LP":
        return "NO_GO_LP"
    if lr_status == "NO_GO_LR":
        return "NO_GO_LR"
    if lr_status == "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS":
        return "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS"
    if ld["status"] == "PASS":
        return "PASS"
    if active_reserve_pairs < RESERVE_PAIRS:
        return "INCOMPLETE"
    return "LABEL_DENOMINATOR_INSUFFICIENT"


def validate_lr_metrics(lr: dict[str, Any]) -> None:
    if not isinstance(lr, dict):
        raise ContractError("L-R metrics JSON must be an object")
    status = lr.get("status")
    boundary_status = lr.get("boundary_status")
    if status not in {
        "PASS", "NO_GO_LR", "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS",
    }:
        raise ContractError(f"invalid L-R status: {status!r}")
    if boundary_status not in {
        "EVALUATED", "AC1_UNEVALUABLE",
        "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS",
    }:
        raise ContractError(f"invalid L-R boundary_status: {boundary_status!r}")
    try:
        boundary = lr["metrics"]["boundary_identifiability_gwet_ac1"]
        boundary["denominator"]
        boundary["threshold"]
    except (KeyError, TypeError) as error:
        raise ContractError("L-R JSON lacks explicit boundary denominator/threshold") from error
    if status == "PASS" and boundary_status != "EVALUATED":
        raise ContractError("L-R PASS requires an evaluated boundary denominator")
    if (
        status == "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS"
        and boundary_status != "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS"
    ):
        raise ContractError("L-R boundary-denominator status is inconsistent")


def evaluate_gate_l(
    package_rows: list[dict[str, str]],
    context_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
    provenance_rows: list[dict[str, str]],
    reviews: list[dict[str, str]],
    loci: list[dict[str, str]],
    materials: list[dict[str, str]],
    boundaries: list[dict[str, str]],
    relations: list[dict[str, str]],
    projections: list[dict[str, str]],
    lr_metrics: dict[str, Any],
) -> dict[str, Any]:
    packages = _index_packages(package_rows)
    active, active_reserve_pairs, reserve_pairs = _active_packages(packages, reviews)
    context = _context_index(context_rows)
    registry = _registry(registry_rows)
    validate_lr_metrics(lr_metrics)
    lp = evaluate_lp(packages, active, context, registry, provenance_rows, boundaries)
    ld = evaluate_ld(active, loci, materials, relations, projections)
    status = combine_status(lp, lr_metrics, ld, active_reserve_pairs)
    result: dict[str, Any] = {
        "schema": "gate_l_lp_ld_v1",
        "status": status,
        "active_main_packages": sum(packages[key]["role"] == "main" for key in active),
        "active_reserve_pairs": active_reserve_pairs,
        "active_reserve_packages": 2 * active_reserve_pairs,
        "lp": lp,
        "lr": lr_metrics,
        "ld": ld,
    }
    if status == "INCOMPLETE":
        rank = active_reserve_pairs + 1
        result["next_reserve_pair"] = {
            "reserve_pair_rank": rank,
            "package_ids": reserve_pairs[rank],
        }
    return result


def _load_inputs(args: argparse.Namespace) -> dict[str, Any]:
    with args.lr_metrics.open(encoding="utf-8") as handle:
        lr_metrics = json.load(handle)
    return {
        "package_rows": read_tsv(args.packages, PACKAGE_FIELDS),
        "context_rows": read_tsv(args.context, CONTEXT_FIELDS),
        "registry_rows": read_tsv(args.evidence_registry, REGISTRY_FIELDS),
        "provenance_rows": read_tsv(args.provenance_audit, PROVENANCE_FIELDS),
        "reviews": read_tsv(args.adj_bundle / "package_reviews.tsv", REVIEW_FIELDS),
        "loci": read_tsv(args.adj_bundle / "loci.tsv", LOCUS_FIELDS),
        "materials": read_tsv(args.adj_bundle / "material_segments.tsv", MATERIAL_FIELDS),
        "boundaries": read_tsv(args.adj_bundle / "boundaries.tsv", BOUNDARY_FIELDS),
        "relations": read_tsv(args.adj_bundle / "relations.tsv", RELATION_FIELDS),
        "projections": read_tsv(args.atom_projection, PROJECTION_FIELDS),
        "lr_metrics": lr_metrics,
    }


def _write_result(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gate_l_lp_ld.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "STATUS").write_text(result["status"] + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--evidence-registry", type=Path, required=True)
    parser.add_argument("--provenance-audit", type=Path, required=True)
    parser.add_argument("--adj-bundle", type=Path, required=True)
    parser.add_argument("--atom-projection", type=Path, required=True)
    parser.add_argument("--lr-metrics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate_gate_l(**_load_inputs(args))
    except (ContractError, OSError, json.JSONDecodeError) as error:
        _write_result(args.output_dir, {
            "schema": "gate_l_lp_ld_v1",
            "status": "CONTRACT_INVALID",
            "error": str(error),
        })
        return 2
    _write_result(args.output_dir, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
