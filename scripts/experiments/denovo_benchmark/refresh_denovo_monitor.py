#!/usr/bin/env python3
"""Refresh all de novo benchmark monitor snapshots and the merged report."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()

    run_root = Path(args.run_root).resolve()
    project_root = Path(__file__).resolve().parents[3]

    state_script = project_root / "scripts" / "experiments" / "denovo_benchmark" / "summarize_benchmark_state.py"
    progress_script = project_root / "scripts" / "experiments" / "denovo_benchmark" / "monitor_denovo_progress.py"
    report_script = project_root / "scripts" / "experiments" / "denovo_benchmark" / "build_denovo_monitor_report.py"

    run(
        [
            "python",
            str(state_script),
            "--run-root",
            str(run_root),
            "--out",
            str(run_root / "current_matrix_status_20260629_refresh.tsv"),
        ]
    )
    run(
        [
            "python",
            str(state_script),
            "--run-root",
            str(run_root),
            "--data-root",
            str(run_root / "dfam_augmented"),
            "--out",
            str(run_root / "dfam_augmented" / "current_matrix_status_20260629.tsv"),
        ]
    )
    run(
        [
            "python",
            str(progress_script),
            "--run-root",
            str(run_root),
            "--out",
            str(run_root / "progress_snapshot_20260629.tsv"),
        ]
    )
    run(
        [
            "python",
            str(progress_script),
            "--run-root",
            str(run_root),
            "--data-root",
            str(run_root / "dfam_augmented"),
            "--out",
            str(run_root / "dfam_augmented" / "progress_snapshot_20260629.tsv"),
        ]
    )
    run(
        [
            "python",
            str(report_script),
            "--run-root",
            str(run_root),
            "--out",
            str(run_root / "MONITOR_REPORT_20260629.md"),
        ]
    )
    print(run_root / "MONITOR_REPORT_20260629.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
