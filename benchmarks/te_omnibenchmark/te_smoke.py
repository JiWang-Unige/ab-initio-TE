#!/usr/bin/env python3
"""Run the small ENGINEERING_ONLY OmniBenchmark adapter smoke.

This entrypoint deliberately exercises only the existing adapter's format
conversion and T0/T1 evaluator.  It is shared by the fixture, conversion,
metric, and collector nodes so the smoke does not create placeholder wrappers
for external TE callers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER = REPO_ROOT / "scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _run_adapter(*args: str) -> dict[str, object]:
    if not ADAPTER.is_file():
        raise FileNotFoundError(f"existing adapter not found: {ADAPTER}")
    completed = subprocess.run(
        [sys.executable, str(ADAPTER), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"adapter did not return JSON: {completed.stdout!r}"
        ) from exc
    if not isinstance(value, dict):
        raise TypeError(f"adapter returned {type(value).__name__}, expected object")
    return value


def run_fixture(output_dir: Path) -> None:
    """Write deterministic source-format records and the registry."""
    lengths = {"chrA": 120, "chrB": 100}
    genome = ">chrA\n" + "A" * lengths["chrA"] + "\n>chrB\n" + "C" * lengths["chrB"] + "\n"

    # BED is zero-based, half-open.  The first and last records exercise both
    # contig boundaries; T1 deliberately omits chrB as an unlabelled region.
    truth_t0 = """chrA\t0\t5\tleft_edge\nchrA\t10\t20\tmiddle\nchrB\t95\t100\tright_edge\n"""
    truth_t1 = """chrA\t0\t5\tleft_edge\nchrA\t10\t20\tmiddle\n"""

    # GFF3 is one-based, inclusive.  The two left records overlap, the middle
    # record is fragmented by a one-base gap, and chrB contains an explicit
    # false-positive candidate plus an exact right-edge match.
    prediction = """##gff-version 3
chrA\tsynthetic\trepeat_region\t1\t5\t.\t+\t.\tID=left_exact
chrA\tsynthetic\trepeat_region\t4\t6\t.\t+\t.\tID=left_overlap
chrA\tsynthetic\trepeat_region\t11\t15\t.\t+\t.\tID=middle_fragment_a
chrA\tsynthetic\trepeat_region\t17\t20\t.\t+\t.\tID=middle_fragment_b
chrB\tsynthetic\trepeat_region\t50\t52\t.\t-\t.\tID=explicit_candidate
chrB\tsynthetic\trepeat_region\t96\t100\t.\t-\t.\tID=right_exact
"""

    registry = {
        "schema": "te_engineering_status_v1",
        "engineering_only": True,
        "denominator_policy": "all registry rows remain in the summary",
        "fixture_cases": {
            "left_edge": {"seqid": "chrA", "start": 0, "end": 5},
            "right_edge": {"seqid": "chrB", "start": 95, "end": 100},
            "overlapping_source_records": True,
            "fragment_gap_bp": 1,
            "t1_unknown_chr": "chrB",
        },
        "expected_cells": [
            {
                "cell_id": "adapter_convert|convert|host",
                "method": "adapter_convert",
                "task": "convert",
                "device": "host",
                "expected_status": "COMPLETED",
            },
            {
                "cell_id": "evaluate|T0|host",
                "method": "evaluate",
                "task": "T0",
                "device": "host",
                "expected_status": "COMPLETED",
            },
            {
                "cell_id": "evaluate|T1|host",
                "method": "evaluate",
                "task": "T1",
                "device": "host",
                "expected_status": "COMPLETED",
            },
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

    _write(output_dir / "genome.fa", genome)
    _write(output_dir / "truth_t0.bed", truth_t0)
    _write(output_dir / "truth_t1.bed", truth_t1)
    _write(output_dir / "prediction.gff3", prediction)
    _write_json(output_dir / "lengths.json", lengths)
    _write_json(output_dir / "cell_registry.json", registry)


def _path_arg(parser: argparse.ArgumentParser, option: str, *, many: bool = False) -> None:
    parser.add_argument(
        option,
        dest=option[2:].replace(".", "_"),
        type=Path,
        nargs="+" if many else None,
    )


def run_convert(args: argparse.Namespace) -> None:
    truth_t0 = args.data_truth_t0_source
    truth_t1 = args.data_truth_t1_source
    prediction = args.data_prediction_source
    if not all((truth_t0, truth_t1, prediction)):
        raise ValueError("adapter_convert requires all three source-format inputs")

    _run_adapter(
        "convert",
        "--input",
        str(truth_t0),
        "--output",
        str(args.output_dir / "truth_t0.tsv"),
        "--format",
        "bed",
    )
    _run_adapter(
        "convert",
        "--input",
        str(truth_t1),
        "--output",
        str(args.output_dir / "truth_t1.tsv"),
        "--format",
        "bed",
    )
    _run_adapter(
        "convert",
        "--input",
        str(prediction),
        "--output",
        str(args.output_dir / "prediction.tsv"),
        "--format",
        "gff3",
    )

    _write_json(
        args.output_dir / "cell_status.json",
        {
            "schema": "te_engineering_status_v1",
            "engineering_only": True,
            "cells": [
                {
                    "cell_id": "adapter_convert|convert|host",
                    "method": "adapter_convert",
                    "task": "convert",
                    "device": "host",
                    "status": "COMPLETED",
                },
                {
                    "cell_id": "synthetic_status_unsupported|status|host",
                    "method": "synthetic_status_unsupported",
                    "task": "status",
                    "device": "host",
                    "status": "UNSUPPORTED",
                    "reason": "deliberate denominator-preservation fixture",
                },
                {
                    "cell_id": "synthetic_status_blocked|status|host",
                    "method": "synthetic_status_blocked",
                    "task": "status",
                    "device": "host",
                    "status": "BLOCKED",
                    "reason": "deliberate denominator-preservation fixture",
                },
            ],
        },
    )


def run_evaluate(args: argparse.Namespace) -> None:
    if args.tier not in {"T0", "T1"}:
        raise ValueError(f"unsupported smoke tier: {args.tier}")
    truth = args.methods_truth_t0_canonical if args.tier == "T0" else args.methods_truth_t1_canonical
    if not truth or not args.methods_prediction_canonical or not args.data_lengths:
        raise ValueError("evaluate requires canonical truth, prediction, and lengths")

    result = _run_adapter(
        "evaluate",
        "--truth",
        str(truth),
        "--prediction",
        str(args.methods_prediction_canonical),
        "--lengths",
        str(args.data_lengths),
        "--truth-tier",
        args.tier,
    )
    _write_json(
        args.output_dir / "metrics.json",
        {
            "schema": "te_engineering_metrics_v1",
            "engineering_only": True,
            "status": "COMPLETED",
            "cell_id": f"evaluate|{args.tier}|host",
            "method": "evaluate",
            "task": args.tier,
            "device": "host",
            "truth_tier": args.tier,
            "metrics": result,
        },
    )


def _iter_paths(groups: Iterable[Path] | None) -> Iterable[Path]:
    if groups:
        yield from groups


def _load_json_paths(paths: Iterable[Path]) -> list[tuple[Path, object]]:
    loaded: list[tuple[Path, object]] = []
    for path in paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        loaded.append((path, value))
    return loaded


def run_collect(args: argparse.Namespace) -> None:
    data_values = _load_json_paths(_iter_paths(args.data_cell_registry))
    status_values = _load_json_paths(_iter_paths(args.methods_cell_status))
    metric_values = _load_json_paths(_iter_paths(args.metrics_score))

    registries = [
        value
        for _, value in data_values
        if isinstance(value, dict) and "expected_cells" in value
    ]
    if len(registries) != 1:
        raise ValueError(f"expected one cell registry, found {len(registries)}")
    registry = registries[0]

    observed: dict[str, dict[str, object]] = {}
    for _, value in status_values + metric_values:
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

    expected = registry.get("expected_cells")
    if not isinstance(expected, list) or not all(isinstance(row, dict) for row in expected):
        raise ValueError("cell registry expected_cells must be a list of objects")

    rows: list[dict[str, object]] = []
    for row in expected:
        cell_id = row.get("cell_id")
        if not isinstance(cell_id, str):
            raise ValueError("registry row is missing cell_id")
        evidence = observed.get(cell_id)
        if evidence is not None and isinstance(evidence.get("status"), str):
            status = evidence["status"]
            evidence_state = "observed"
            reason = evidence.get("reason")
        else:
            expected_status = row.get("expected_status", "FAILED")
            # A missing output cannot satisfy an expected COMPLETED cell.  Keep
            # deliberate non-completed registry states, but expose absent
            # completion evidence as a failure instead of scoring it as zero or
            # silently counting it as completed.
            status = "FAILED" if expected_status == "COMPLETED" else expected_status
            evidence_state = "registry_only"
            reason = (
                "no output evidence for expected completed cell"
                if expected_status == "COMPLETED"
                else row.get("reason", "no output evidence")
            )
        rows.append(
            {
                "cell_id": cell_id,
                "method": row.get("method"),
                "task": row.get("task"),
                "device": row.get("device"),
                "expected_status": row.get("expected_status"),
                "status": status,
                "evidence": evidence_state,
                "reason": reason,
            }
        )

    status_counts = Counter(str(row["status"]) for row in rows)
    _write_json(
        args.output_dir / "collector_summary.json",
        {
            "schema": "te_engineering_summary_v1",
            "engineering_only": True,
            "claim_scope": "workflow connectivity and status-denominator preservation only",
            "expected_cell_count": len(rows),
            "observed_cell_count": sum(row["evidence"] == "observed" for row in rows),
            "status_counts": dict(sorted(status_counts.items())),
            "cells": rows,
            "fixture_cases": registry.get("fixture_cases", {}),
            "metric_files": [str(path) for path, _ in metric_values],
            "status_files": [str(path) for path, _ in status_values],
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--tier", choices=["T0", "T1"])

    for option in (
        "--data.truth_t0_source",
        "--data.truth_t1_source",
        "--data.prediction_source",
        "--data.lengths",
        "--methods.truth_t0_canonical",
        "--methods.truth_t1_canonical",
        "--methods.prediction_canonical",
    ):
        _path_arg(parser, option)
    for option in ("--metrics.score", "--methods.cell_status", "--data.cell_registry"):
        _path_arg(parser, option, many=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.name == "fixture":
        run_fixture(args.output_dir)
    elif args.name == "adapter_convert":
        run_convert(args)
    elif args.name == "evaluate":
        run_evaluate(args)
    elif args.name == "summary":
        run_collect(args)
    else:
        raise ValueError(f"unexpected smoke module name: {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
