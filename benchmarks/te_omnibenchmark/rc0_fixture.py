#!/usr/bin/env python3
"""ENGINEERING_ONLY four-arm RC0 fixture for OmniBenchmark 0.6.0.

The fixture has no model or biological labels.  It checks the data flow used by
the real RC0 runner: fixed forward/RC/mean/phase arms, existing adapter
conversion, T0/T1 metric semantics, and collector denominator preservation.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER = REPO_ROOT / "scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py"
ARMS = ("F", "RC", "mean", "phase_mean")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def path_arg(parser: argparse.ArgumentParser, option: str, many: bool = False) -> None:
    parser.add_argument(option, dest=option[2:].replace(".", "_"), type=Path, nargs="+" if many else None)


def adapter_call(*args: str) -> dict[str, object]:
    completed = subprocess.run([sys.executable, str(ADAPTER), *args], check=True, text=True, capture_output=True)
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise TypeError("existing adapter returned a non-object")
    return value


def fixture(output_dir: Path) -> None:
    lengths = {"chrA": 96, "chrB": 96}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "genome.fa").write_text(">chrA\n" + "A" * 96 + "\n>chrB\n" + "C" * 96 + "\n", encoding="utf-8")
    # Complete synthetic truth for T0.  T1 intentionally omits chrB so its
    # unlabelled part exercises the evaluator's unknown-negative policy.
    (output_dir / "truth_t0.bed").write_text(
        "chrA\t0\t16\ttruth_a\nchrA\t32\t48\ttruth_b\nchrB\t80\t96\ttruth_c\n",
        encoding="utf-8",
    )
    (output_dir / "truth_t1.bed").write_text(
        "chrA\t0\t16\ttruth_a\nchrA\t32\t48\ttruth_b\n",
        encoding="utf-8",
    )
    registry = {
        "schema": "te_rc0_engineering_status_v1",
        "engineering_only": True,
        "four_arms": list(ARMS),
        "coordinate_contract": "zero_based_half_open; RC vectors are mapped in bp coordinates",
        "expected_cells": [
            {
                "cell_id": f"evaluate|{arm}|{tier}|host",
                "method": "evaluate",
                "task": tier,
                "arm": arm,
                "device": "host",
                "expected_status": "COMPLETED",
            }
            for arm in ARMS
            for tier in ("T0", "T1")
        ]
        + [
            {
                "cell_id": "synthetic_status_unsupported|status|host",
                "method": "synthetic_status_unsupported",
                "task": "status",
                "device": "host",
                "expected_status": "UNSUPPORTED",
                "reason": "deliberate denominator-preservation fixture",
            },
            {
                "cell_id": "synthetic_status_blocked|status|host",
                "method": "synthetic_status_blocked",
                "task": "status",
                "device": "host",
                "expected_status": "BLOCKED",
                "reason": "deliberate denominator-preservation fixture",
            },
        ],
    }
    write_json(output_dir / "lengths.json", lengths)
    write_json(output_dir / "cell_registry.json", registry)


def arms(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    # All intervals are generated from this frozen synthetic probability
    # contract; no truth file is read by this method node.
    predictions = {
        "F": ["chrA\t0\t16\tF_a\n", "chrA\t32\t48\tF_b\n", "chrB\t80\t96\tF_c\n"],
        # Mapped-back RC contains a deliberately shifted middle boundary.
        "RC": ["chrA\t0\t16\tRC_a\n", "chrA\t34\t48\tRC_b\n", "chrB\t80\t96\tRC_c\n"],
        # The average recovers the F thresholded material in this fixture.
        "mean": ["chrA\t0\t16\tmean_a\n", "chrA\t32\t48\tmean_b\n", "chrB\t80\t96\tmean_c\n"],
        # Phase control shifts the left boundary of the middle run by one bp.
        "phase_mean": ["chrA\t0\t16\tphase_a\n", "chrA\t33\t48\tphase_b\n", "chrB\t80\t96\tphase_c\n"],
    }
    for arm, rows in predictions.items():
        (output_dir / f"{arm}.bed").write_text("".join(rows), encoding="utf-8")
    write_json(
        output_dir / "arm_status.json",
        {
            "schema": "te_rc0_engineering_status_v1",
            "engineering_only": True,
            "coordinate_mapping": "RC [s,e) -> [L-e,L-s) before thresholded BED export",
            "cells": [
                {"cell_id": f"evaluate|{arm}|{tier}|host", "method": "evaluate", "task": tier, "arm": arm, "device": "host", "status": "COMPLETED"}
                for arm in ARMS
                for tier in ("T0", "T1")
            ]
            + [
                {"cell_id": "synthetic_status_unsupported|status|host", "method": "synthetic_status_unsupported", "task": "status", "device": "host", "status": "UNSUPPORTED", "reason": "deliberate denominator-preservation fixture"},
                {"cell_id": "synthetic_status_blocked|status|host", "method": "synthetic_status_blocked", "task": "status", "device": "host", "status": "BLOCKED", "reason": "deliberate denominator-preservation fixture"},
            ],
        },
    )


def evaluate(args: argparse.Namespace) -> None:
    if args.arm not in ARMS or args.tier not in {"T0", "T1"}:
        raise ValueError("fixture expects one RC0 arm and T0/T1")
    truth_source = args.data_truth_t0_source if args.tier == "T0" else args.data_truth_t1_source
    prediction = getattr(args, f"methods_{args.arm.lower()}_prediction_source")
    if not all((truth_source, prediction, args.data_lengths)):
        raise ValueError("fixture evaluator requires truth, prediction and lengths")
    truth_canonical = args.output_dir / "truth.tsv"
    prediction_canonical = args.output_dir / "prediction.tsv"
    adapter_call("convert", "--input", str(truth_source), "--output", str(truth_canonical), "--format", "bed")
    adapter_call("convert", "--input", str(prediction), "--output", str(prediction_canonical), "--format", "bed")
    metrics = adapter_call(
        "evaluate", "--truth", str(truth_canonical), "--prediction", str(prediction_canonical),
        "--lengths", str(args.data_lengths), "--truth-tier", args.tier,
    )
    write_json(
        args.output_dir / "metrics.json",
        {
            "schema": "te_rc0_engineering_metrics_v1",
            "engineering_only": True,
            "status": "COMPLETED",
            "cell_id": f"evaluate|{args.arm}|{args.tier}|host",
            "method": "evaluate",
            "task": args.tier,
            "arm": args.arm,
            "device": "host",
            "truth_tier": args.tier,
            "coordinate_contract": "zero_based_half_open",
            "metrics": metrics,
        },
    )


def load_paths(paths: list[Path] | Path | None) -> list[object]:
    values = []
    if isinstance(paths, Path):
        paths = [paths]
    for path in paths or []:
        try:
            values.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return values


def collect(args: argparse.Namespace) -> None:
    registries = [v for v in load_paths(args.data_cell_registry) if isinstance(v, dict) and "expected_cells" in v]
    if len(registries) != 1:
        raise ValueError(f"expected one registry, found {len(registries)}")
    registry = registries[0]
    observed: dict[str, dict[str, object]] = {}
    for value in load_paths(args.methods_arm_status) + load_paths(args.metrics_score):
        if not isinstance(value, dict):
            continue
        cells = value.get("cells")
        if isinstance(cells, list):
            for cell in cells:
                if isinstance(cell, dict) and isinstance(cell.get("cell_id"), str):
                    observed[cell["cell_id"]] = cell
        cell_id = value.get("cell_id")
        if isinstance(cell_id, str):
            observed[cell_id] = value
    rows = []
    for expected in registry["expected_cells"]:
        cell_id = expected["cell_id"]
        evidence = observed.get(cell_id)
        if evidence is not None and isinstance(evidence.get("status"), str):
            status, evidence_state = evidence["status"], "observed"
            reason = evidence.get("reason")
        else:
            expected_status = expected.get("expected_status", "FAILED")
            status, evidence_state = ("FAILED" if expected_status == "COMPLETED" else expected_status), "registry_only"
            reason = "no output evidence for expected completed cell" if expected_status == "COMPLETED" else expected.get("reason")
        rows.append({
            "cell_id": cell_id, "method": expected.get("method"), "task": expected.get("task"),
            "arm": expected.get("arm"), "device": expected.get("device"),
            "expected_status": expected.get("expected_status"), "status": status,
            "evidence": evidence_state, "reason": reason,
        })
    counts = Counter(str(row["status"]) for row in rows)
    write_json(
        args.output_dir / "collector_summary.json",
        {
            "schema": "te_rc0_engineering_summary_v1",
            "engineering_only": True,
            "claim_scope": "RC0 wiring and status denominator only",
            "expected_cell_count": len(rows),
            "observed_cell_count": sum(row["evidence"] == "observed" for row in rows),
            "status_counts": dict(sorted(counts.items())),
            "cells": rows,
        },
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output_dir", type=Path, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--arm", choices=ARMS)
    p.add_argument("--tier", choices=("T0", "T1"))
    for option in ("--data.genome", "--data.truth_t0_source", "--data.truth_t1_source", "--data.lengths"):
        path_arg(p, option)
    for arm in ARMS:
        path_arg(p, f"--methods.{arm.lower()}_prediction_source")
    # Omni 0.6.0 passes every output sharing this collection ID prefix to a
    # collector; only arm_status.json is JSON and the loader skips the BEDs.
    path_arg(p, "--methods.arm_status", many=True)
    path_arg(p, "--metrics.score", many=True)
    path_arg(p, "--data.cell_registry", many=True)
    return p


def main() -> int:
    args = parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.name == "fixture":
        fixture(args.output_dir)
    elif args.name == "arms":
        arms(args.output_dir)
    elif args.name == "evaluate":
        evaluate(args)
    elif args.name == "summary":
        collect(args)
    else:
        raise ValueError(f"unexpected RC0 fixture module: {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
