#!/usr/bin/env python3
"""Build a concise de novo benchmark monitor report from existing snapshots."""

from __future__ import annotations

import argparse
import csv
import time
from collections import Counter
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def count_states(rows: list[dict[str, str]]) -> dict[str, int]:
    return dict(Counter(row.get("state", "") or row.get("status", "") for row in rows))


def log_age_seconds(path_str: str) -> int:
    outdir = Path(path_str)
    log = outdir / "runner.log"
    if not log.exists():
        return -1
    return int(time.time() - log.stat().st_mtime)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    run_root = Path(args.run_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    base_state = read_tsv(run_root / "current_matrix_status_20260629_refresh.tsv")
    base_progress = read_tsv(run_root / "progress_snapshot_20260629.tsv")
    dfam_state = read_tsv(run_root / "dfam_augmented" / "current_matrix_status_20260629.tsv")
    dfam_progress = read_tsv(run_root / "dfam_augmented" / "progress_snapshot_20260629.tsv")

    base_progress_map = {
        (row["species_code"], row["tool"]): row for row in base_progress
    }
    dfam_progress_map = {
        (row["species_code"], row["tool"]): row for row in dfam_progress
    }

    lines: list[str] = []
    lines.append(f"# {run_root.name} Monitor Report")
    lines.append("")
    lines.append(f"- Generated at unix={int(time.time())}")
    lines.append(f"- Base states: {count_states(base_state)}")
    lines.append(f"- Dfam states: {count_states(dfam_state)}")
    lines.append("")
    lines.append("## Active base jobs")
    lines.append("")
    lines.append("| species | tool | state | progress | log_age_s |")
    lines.append("|---|---|---:|---|---:|")
    for row in base_state:
        if row["state"] != "running":
            continue
        prog = base_progress_map.get((row["species_code"], row["tool"]), {})
        progress = " ".join(
            part
            for part in [prog.get("progress_kind", ""), prog.get("progress_value", "")]
            if part
        )
        lines.append(
            f"| {row['species_code']} | {row['tool']} | {row['state']} | "
            f"{progress or '-'} | {log_age_seconds(row['output_dir'])} |"
        )

    lines.append("")
    lines.append("## Active Dfam jobs")
    lines.append("")
    lines.append("| species | tool | state | progress | log_age_s |")
    lines.append("|---|---|---:|---|---:|")
    for row in dfam_state:
        if row["state"] != "running":
            continue
        prog = dfam_progress_map.get((row["species_code"], row["tool"]), {})
        progress = " ".join(
            part
            for part in [prog.get("progress_kind", ""), prog.get("progress_value", "")]
            if part
        )
        lines.append(
            f"| {row['species_code']} | {row['tool']} | {row['state']} | "
            f"{progress or '-'} | {log_age_seconds(row['output_dir'])} |"
        )

    out.write_text("\n".join(lines) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
