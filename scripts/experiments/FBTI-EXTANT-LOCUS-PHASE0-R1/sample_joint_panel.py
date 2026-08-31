#!/usr/bin/env python3
"""Freeze a label-blind, jointly sampled FlyBase challenge panel.

The input is the population TSV produced by ``build_population.py``.  A
single mixed-integer program chooses calibration, main and reserve packages
for both strata while enforcing the fixed main/calibration challenge cells,
stratum-level reserve quotas and global expanded-package non-overlap.  P3
multiplicity and nearest-FBti gap are retained as diagnostics only.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys
from typing import Iterable


SEED = 20260831
ASSEMBLY_ID = "dmel_r6.68"
PANELS = ("calibration", "main", "reserve")
STRATA = ("S0", "S1")
PANEL_COUNTS = {"calibration": 6, "main": 60, "reserve": 20}

S0_CELLS = ("S0-L1", "S0-L2", "S0-L3", "S0-L4")
S1_CELLS = ("S1-C1", "S1-C2", "S1-C3")

EXACT_QUOTAS = {
    ("S0", "S0-L1", "main"): 15,
    ("S0", "S0-L2", "main"): 15,
    ("S0", "S0-L3", "main"): 15,
    ("S0", "S0-L4", "main"): 15,
    ("S1", "S1-C1", "calibration"): 2,
    ("S1", "S1-C2", "calibration"): 2,
    ("S1", "S1-C3", "calibration"): 2,
    ("S1", "S1-C1", "main"): 20,
    ("S1", "S1-C2", "main"): 20,
    ("S1", "S1-C3", "main"): 20,
}

# S0 calibration has only a lower bound per length cell.  The two remaining
# packages and both reserve strata are selected by the seeded label-blind
# priority objective.
MIN_QUOTAS = {
    ("S0", "S0-L1", "calibration"): 1,
    ("S0", "S0-L2", "calibration"): 1,
    ("S0", "S0-L3", "calibration"): 1,
    ("S0", "S0-L4", "calibration"): 1,
}

POPULATION_FIELDS = {
    "unit_id",
    "unit_type",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
    "feature_ids",
    "feature_count",
    "core_length",
    "max_overlap_depth",
    "p3_atoms_core",
    "p3_atoms_package",
    "nearest_fbti_gap",
}

PACKAGE_FIELDS = [
    "package_id",
    "role",
    "role_rank",
    "reserve_pair_rank",
    "unit_type",
    "hard_cell",
    "selection_priority",
    "deep_audit_feature_id",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
    "feature_ids",
    "core_length",
    "feature_count",
    "max_overlap_depth",
    "p3_atoms_core",
    "p3_atoms_package",
    "nearest_fbti_gap",
]


class PanelInfeasible(RuntimeError):
    """The fixed panel contract has no feasible solution."""


def challenge_cell(row: dict[str, str]) -> str:
    """Return the one hard challenge cell for a population row."""

    unit_type = row["unit_type"]
    if unit_type == "S0":
        length = int(row["core_length"])
        if length < 80:
            return "S0-L1"
        if length < 500:
            return "S0-L2"
        if length < 1000:
            return "S0-L3"
        return "S0-L4"
    if unit_type == "S1":
        size = int(row["feature_count"])
        depth = int(row["max_overlap_depth"])
        if size == 2 and depth == 2:
            return "S1-C1"
        if size >= 3 and depth == 2:
            return "S1-C2"
        if depth >= 3:
            return "S1-C3"
    raise ValueError(f"row does not fit a hard challenge cell: {row['unit_id']}")


def read_population(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = set(reader.fieldnames or ())
        if not POPULATION_FIELDS.issubset(fields):
            raise ValueError(f"population fields must include {sorted(POPULATION_FIELDS)}")
        rows = list(reader)

    seen: set[str] = set()
    for row in rows:
        unit_id = row["unit_id"]
        if unit_id in seen:
            raise ValueError(f"duplicate population unit_id: {unit_id}")
        seen.add(unit_id)
        if row["unit_type"] not in STRATA:
            raise ValueError(f"unexpected population stratum: {unit_id}")
        if int(row["package_start0"]) < 0 or int(row["package_end0"]) <= int(row["package_start0"]):
            raise ValueError(f"invalid expanded interval: {unit_id}")
        row["challenge_cell"] = challenge_cell(row)

    return sorted(rows, key=lambda row: row["unit_id"])


def intervals_overlap(left: dict[str, str], right: dict[str, str]) -> bool:
    left_start = int(left["package_start0"])
    left_end = int(left["package_end0"])
    right_start = int(right["package_start0"])
    right_end = int(right["package_end0"])
    return (
        left["seqid"] == right["seqid"]
        and left_start < right_end
        and right_start < left_end
    )


def overlapping_pairs(rows: Iterable[dict[str, str]]) -> list[tuple[int, int]]:
    """Return row-index pairs whose expanded half-open intervals overlap."""

    ordered = sorted(
        enumerate(rows),
        key=lambda item: (
            item[1]["seqid"],
            int(item[1]["package_start0"]),
            int(item[1]["package_end0"]),
            item[1].get("unit_id", item[1].get("package_id", "")),
        ),
    )
    pairs: list[tuple[int, int]] = []
    active_by_seqid: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for original_index, row in ordered:
        active = active_by_seqid[row["seqid"]]
        start = int(row["package_start0"])
        active[:] = [
            item
            for item in active
            if int(item[1]["package_end0"]) > start
        ]
        for prior_index, prior in active:
            if intervals_overlap(prior, row):
                pairs.append(tuple(sorted((prior_index, original_index))))
        active.append((original_index, row))
    return pairs


def context_conflict_pairs(
    rows: list[dict[str, str]], truth_path: Path
) -> list[tuple[int, int]]:
    with truth_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"feature_id", "seqid", "start0", "end0"}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError(f"truth fields must include {sorted(required)}")
        truth = list(reader)

    by_seqid: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_seqid[row["seqid"]].append((index, row))
    for packages in by_seqid.values():
        packages.sort(key=lambda item: (int(item[1]["package_start0"]), item[0]))

    conflicts: set[tuple[int, int]] = set()
    seen_features: set[str] = set()
    for feature in truth:
        feature_id = feature["feature_id"]
        if feature_id in seen_features:
            raise ValueError(f"duplicate truth feature_id: {feature_id}")
        seen_features.add(feature_id)
        start = int(feature["start0"])
        end = int(feature["end0"])
        if start < 0 or end <= start:
            raise ValueError(f"invalid truth interval: {feature_id}")
        hits = [
            index
            for index, row in by_seqid.get(feature["seqid"], ())
            if int(row["package_start0"]) < end and start < int(row["package_end0"])
        ]
        for offset, left in enumerate(hits):
            for right in hits[offset + 1 :]:
                conflicts.add(tuple(sorted((left, right))))
    return sorted(conflicts)


def _quota_key(row: dict[str, str]) -> tuple[str, str, str]:
    return row["unit_type"], row["hard_cell"], row["role"]


def validate_manifest(rows: list[dict[str, str]]) -> None:
    """Validate the complete fixed panel contract without scipy."""

    expected_total = sum(PANEL_COUNTS.values()) * len(STRATA)
    if len(rows) != expected_total:
        raise ValueError(f"expected {expected_total} selected packages, got {len(rows)}")
    if len({row["package_id"] for row in rows}) != len(rows):
        raise ValueError("selected packages contain duplicate package_id")

    panel_counts = Counter((row["unit_type"], row["role"]) for row in rows)
    expected_panel_counts = Counter(
        {
            (stratum, panel): count
            for stratum in STRATA
            for panel, count in PANEL_COUNTS.items()
        }
    )
    if panel_counts != expected_panel_counts:
        raise ValueError(f"stratum/panel counts do not match contract: {panel_counts}")
    quota_counts = Counter(_quota_key(row) for row in rows)
    for key, expected in EXACT_QUOTAS.items():
        if quota_counts[key] != expected:
            raise ValueError(f"challenge-cell quota does not match contract for {key}: {quota_counts[key]}")
    for key, minimum in MIN_QUOTAS.items():
        if quota_counts[key] < minimum:
            raise ValueError(f"challenge-cell minimum does not match contract for {key}: {quota_counts[key]}")
    if overlapping_pairs(rows):
        raise ValueError("selected expanded packages overlap")

    panel_ranks = defaultdict(list)
    for row in rows:
        panel_ranks[row["role"]].append(int(row["role_rank"]))
    for panel, ranks in panel_ranks.items():
        expected = list(range(1, len(ranks) + 1))
        if sorted(ranks) != expected:
            raise ValueError(f"panel ranks are not 1..N for {panel}")

    reserve = [row for row in rows if row["role"] == "reserve"]
    by_pair_rank = defaultdict(list)
    for row in reserve:
        by_pair_rank[int(row["reserve_pair_rank"])].append(row["unit_type"])
    if sorted(by_pair_rank) != list(range(1, PANEL_COUNTS["reserve"] + 1)):
        raise ValueError("reserve pair ranks are not the fixed 1..20 prefix")
    if any(sorted(strata) != ["S0", "S1"] for strata in by_pair_rank.values()):
        raise ValueError("each reserve pair rank must contain one S0 and one S1 package")

    deep_audit = [row for row in rows if row["deep_audit_feature_id"]]
    if Counter(row["unit_type"] for row in deep_audit) != Counter({"S0": 20, "S1": 20}):
        raise ValueError("deep audit must contain 20 S0 and 20 S1 main records")
    if any(row["role"] != "main" for row in deep_audit):
        raise ValueError("deep audit records must come from main packages")
    deep_ids = [row["deep_audit_feature_id"] for row in deep_audit]
    if len(set(deep_ids)) != 40:
        raise ValueError("deep audit feature IDs must be distinct")
    if any(
        row["deep_audit_feature_id"] not in row["feature_ids"].split(",")
        for row in deep_audit
    ):
        raise ValueError("deep audit feature ID must belong to its focal package")


def _package_row(row: dict[str, str], role: str, priority: float) -> dict[str, str]:
    cell = row["challenge_cell"]
    return {
        "package_id": row["unit_id"],
        "role": role,
        "role_rank": "",
        "reserve_pair_rank": "",
        "unit_type": row["unit_type"],
        "hard_cell": cell,
        "selection_priority": format(priority, ".17g"),
        "deep_audit_feature_id": "",
        "assembly_id": ASSEMBLY_ID,
        "seqid": row["seqid"],
        "core_start0": row["core_start0"],
        "core_end0": row["core_end0"],
        "package_start0": row["package_start0"],
        "package_end0": row["package_end0"],
        "feature_ids": row["feature_ids"],
        "core_length": row["core_length"],
        "feature_count": row["feature_count"],
        "max_overlap_depth": row["max_overlap_depth"],
        "p3_atoms_core": row["p3_atoms_core"],
        "p3_atoms_package": row["p3_atoms_package"],
        "nearest_fbti_gap": row["nearest_fbti_gap"],
    }


def make_manifest(
    rows: list[dict[str, str]],
    selected_panels: dict[int, str],
    selected_priorities: dict[int, float],
) -> list[dict[str, str]]:
    selected = [
        _package_row(rows[index], panel, selected_priorities[index])
        for index, panel in selected_panels.items()
    ]
    for panel in PANELS:
        panel_rows = sorted(
            (row for row in selected if row["role"] == panel),
            key=lambda row: (row["unit_type"], row["hard_cell"], row["package_id"]),
        )
        for rank, row in enumerate(panel_rows, start=1):
            row["role_rank"] = str(rank)

    reserve = [row for row in selected if row["role"] == "reserve"]
    by_stratum = {
        stratum: sorted(
            (row for row in reserve if row["unit_type"] == stratum),
            key=lambda row: row["package_id"],
        )
        for stratum in STRATA
    }
    for rank, pair in enumerate(zip(by_stratum["S0"], by_stratum["S1"]), start=1):
        for row in pair:
            row["reserve_pair_rank"] = str(rank)

    for stratum in STRATA:
        main_rows = sorted(
            (
                row
                for row in selected
                if row["role"] == "main" and row["unit_type"] == stratum
            ),
            key=lambda row: (float(row["selection_priority"]), row["package_id"]),
        )
        for row in main_rows[:20]:
            row["deep_audit_feature_id"] = sorted(row["feature_ids"].split(","))[0]

    validate_manifest(selected)
    return sorted(selected, key=lambda row: (PANELS.index(row["role"]), int(row["role_rank"])))


def _constraint_rows(
    rows: list[dict[str, str]],
    variable_count: int,
    context_conflicts: list[tuple[int, int]],
):
    """Construct sparse MILP rows; scipy is imported only on the solver path."""

    import numpy as np
    from scipy.sparse import coo_matrix

    row_indices: list[int] = []
    col_indices: list[int] = []
    values: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    constraint_index = 0

    def add_constraint(columns: Iterable[int], low: float, high: float) -> None:
        nonlocal constraint_index
        for column in columns:
            row_indices.append(constraint_index)
            col_indices.append(column)
            values.append(1.0)
        lower.append(low)
        upper.append(high)
        constraint_index += 1

    for index in range(len(rows)):
        add_constraint((3 * index + role for role in range(len(PANELS))), 0.0, 1.0)

    for (stratum, cell, panel), quota in EXACT_QUOTAS.items():
        panel_index = PANELS.index(panel)
        columns = (
            3 * index + panel_index
            for index, row in enumerate(rows)
            if row["unit_type"] == stratum and row["challenge_cell"] == cell
        )
        add_constraint(columns, quota, quota)

    for (stratum, cell, panel), minimum in MIN_QUOTAS.items():
        panel_index = PANELS.index(panel)
        columns = (
            3 * index + panel_index
            for index, row in enumerate(rows)
            if row["unit_type"] == stratum and row["challenge_cell"] == cell
        )
        add_constraint(columns, minimum, float("inf"))

    for stratum in STRATA:
        for panel, quota in PANEL_COUNTS.items():
            panel_index = PANELS.index(panel)
            columns = (
                3 * index + panel_index
                for index, row in enumerate(rows)
                if row["unit_type"] == stratum
            )
            add_constraint(columns, quota, quota)

    for left, right in sorted(set(overlapping_pairs(rows)) | set(context_conflicts)):
        add_constraint(
            tuple(3 * left + role for role in range(len(PANELS)))
            + tuple(3 * right + role for role in range(len(PANELS))),
            0.0,
            1.0,
        )

    matrix = coo_matrix(
        (np.asarray(values), (np.asarray(row_indices), np.asarray(col_indices))),
        shape=(constraint_index, variable_count),
    ).tocsc()
    return matrix, np.asarray(lower), np.asarray(upper)


def solve_joint_panel(
    rows: list[dict[str, str]], truth_path: Path
) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Solve the fixed joint panel and return its manifest and solver record."""

    import numpy as np
    import scipy
    from scipy.optimize import Bounds, LinearConstraint, milp

    rows = sorted(rows, key=lambda row: row["unit_id"])
    variable_count = len(rows) * len(PANELS)
    context_conflicts = context_conflict_pairs(rows, truth_path)
    matrix, lower, upper = _constraint_rows(rows, variable_count, context_conflicts)
    rng = np.random.Generator(np.random.PCG64(SEED))
    priority = rng.random((len(rows), len(PANELS)), dtype=np.float64)
    objective = priority.reshape(-1, order="C")
    result = milp(
        c=objective,
        integrality=np.ones(variable_count),
        bounds=Bounds(np.zeros(variable_count), np.ones(variable_count)),
        constraints=LinearConstraint(matrix, lower, upper),
        options={"mip_rel_gap": 0.0},
    )
    if not result.success:
        message = f"MILP status={result.status}: {result.message}"
        if result.status == 2:
            raise PanelInfeasible(f"INFEASIBLE: {message}")
        raise RuntimeError(message)
    if result.status != 0 or float(result.mip_gap) != 0.0:
        raise RuntimeError(
            f"panel solution is not proven optimal with zero gap: status={result.status} gap={result.mip_gap}"
        )

    selected_panels: dict[int, str] = {}
    selected_priorities: dict[int, float] = {}
    for index in range(len(rows)):
        selected = [role for role in range(len(PANELS)) if result.x[3 * index + role] > 0.5]
        if len(selected) == 1:
            role = selected[0]
            selected_panels[index] = PANELS[role]
            selected_priorities[index] = float(objective[3 * index + role])
    manifest = make_manifest(rows, selected_panels, selected_priorities)
    return manifest, {
        "solver_status": int(result.status),
        "solver_message": str(result.message),
        "mip_gap": float(result.mip_gap),
        "objective_value": float(result.fun),
        "constraint_count": int(matrix.shape[0]),
        "context_conflict_pairs": len(context_conflicts),
        "variable_count": variable_count,
        "priority_schema": "pcg64_candidate_role_float64_v1",
        "priority_shape": [len(rows), len(PANELS)],
        "candidate_order": "unit_id_lexicographic",
        "role_order": list(PANELS),
        "flatten_order": "C",
        "objective_direction": "minimize",
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
    }


def panel_summary(
    population: list[dict[str, str]],
    manifest: list[dict[str, str]],
    solver: dict[str, object],
    input_path: Path,
    population_summary: dict[str, object],
    git_commit: str,
) -> dict[str, object]:
    selected_counts = Counter((row["unit_type"], row["role"]) for row in manifest)
    cell_counts = Counter((row["unit_type"], row["hard_cell"], row["role"]) for row in manifest)
    population_cells = Counter((row["unit_type"], row["challenge_cell"]) for row in population)
    return {
        "schema": "fbti_extant_locus_joint_panel_v1",
        "status": "PANEL_FREEZE_PASS",
        "claim_scope": "label-blind joint challenge panel selection; no annotation packet or inclusion-probability estimate",
        "estimand_scope": "conditional_challenge_panel",
        "population_representative": False,
        "seed": SEED,
        "rng": "numpy.PCG64",
        "priority_scope": "candidate_role",
        "solver": "scipy.optimize.milp",
        "assembly_id": ASSEMBLY_ID,
        "panel_git_commit": git_commit,
        "population_census_git_commit": population_summary["git_commit"],
        "population_units": len(population),
        "selected_packages": len(manifest),
        "selected_by_stratum_panel": {
            f"{stratum}:{panel}": selected_counts[(stratum, panel)]
            for stratum in STRATA
            for panel in PANELS
        },
        "selected_by_challenge_cell": {
            f"{stratum}:{cell}:{panel}": cell_counts[(stratum, cell, panel)]
            for stratum, cells in (("S0", S0_CELLS), ("S1", S1_CELLS))
            for cell in cells
            for panel in PANELS
        },
        "candidate_by_challenge_cell": {
            f"{stratum}:{cell}": population_cells[(stratum, cell)]
            for stratum, cells in (("S0", S0_CELLS), ("S1", S1_CELLS))
            for cell in cells
        },
        "expanded_packages_pairwise_nonoverlap": True,
        "p3_multiplicity_and_nearest_gap": "diagnostic columns only; no hard cross-quota",
        "inputs": {"population": str(input_path)},
        **solver,
    }


def write_outputs(manifest: list[dict[str, str]], summary: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=False, exist_ok=False)
    with (output_dir / "packages.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PACKAGE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=Path, required=True)
    parser.add_argument("--population-summary", type=Path, required=True)
    parser.add_argument("--truth-metadata", type=Path, required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    population = read_population(args.population)
    population_summary = json.loads(args.population_summary.read_text(encoding="utf-8"))
    if population_summary.get("status") != "PREFLIGHT_PASS":
        raise ValueError("population census did not pass")
    if int(population_summary["S0_units"]) + int(population_summary["S1_units"]) != len(population):
        raise ValueError("population census summary does not match population rows")
    manifest, solver = solve_joint_panel(population, args.truth_metadata)
    summary = panel_summary(
        population,
        manifest,
        solver,
        args.population,
        population_summary,
        args.git_commit,
    )
    write_outputs(manifest, summary, args.output_dir)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PanelInfeasible as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
