#!/usr/bin/env python3
"""Summarize running de novo benchmark progress from status files and logs."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


PCT_RE = re.compile(
    r"^\s*(?P<pct>\d+)% completed,\s+(?P<eta>\S+)\s+\(hh:mm:ss\)\s+est\. time remaining\."
)
RM_BATCH_RE = re.compile(
    r"batch\s+(?P<done>\d+)\s+of\s+(?P<total>\d+)", re.IGNORECASE
)
RECON_STEP_RE = re.compile(r"RECON:\s+Running\s+(?P<step>.+?)\.\.$")
RECON_ELAPSED_RE = re.compile(r"RECON Elapsed:\s+(?P<elapsed>\S+)\s+\(hh:mm:ss\)")


def load_status(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def tail_lines(path: Path, max_lines: int = 200) -> list[str]:
    if not path.exists():
        return []
    with path.open(errors="ignore") as handle:
        lines = handle.readlines()
    return [line.rstrip("\n") for line in lines[-max_lines:]]


def parse_progress(lines: list[str]) -> tuple[str, str, str]:
    pct = ""
    eta = ""
    step = ""
    recon_elapsed = ""
    rm_done = ""
    rm_total = ""
    for line in lines:
        m = PCT_RE.search(line)
        if m:
            pct = m.group("pct")
            eta = m.group("eta")
        m = RM_BATCH_RE.search(line)
        if m:
            rm_done = m.group("done")
            rm_total = m.group("total")
        m = RECON_STEP_RE.search(line)
        if m:
            step = m.group("step")
        m = RECON_ELAPSED_RE.search(line)
        if m:
            recon_elapsed = m.group("elapsed")

    if step:
        detail = step
        if recon_elapsed:
            detail += f" elapsed={recon_elapsed}"
        return "recon", detail, ""
    if pct:
        detail = f"{pct}%"
        if eta:
            detail += f" eta={eta}"
        return "percent", detail, ""
    if rm_done and rm_total:
        return "batch", f"{rm_done}/{rm_total}", ""
    return "", "", lines[-1] if lines else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument(
        "--data-root",
        help="Optional override for per-species/per-tool output root. Defaults to <run-root>/raw_outputs.",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    run_root = Path(args.run_root)
    data_root = Path(args.data_root) if args.data_root else run_root / "raw_outputs"
    species_manifest = run_root / "manifests" / "species_manifest.tsv"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with species_manifest.open() as handle:
        species_rows = list(csv.DictReader(handle, delimiter="\t"))

    fieldnames = [
        "species_code",
        "tool",
        "status",
        "progress_kind",
        "progress_value",
        "last_line",
        "runner_log_bytes",
        "output_dir",
    ]
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in species_rows:
            species = row["species_code"]
            for tool in ("repeatmodeler", "edta", "repeatscout", "earlgrey"):
                outdir = data_root / species / tool
                status = load_status(outdir / "status.json").get("status", "")
                lines = tail_lines(outdir / "runner.log")
                kind, value, last_line = parse_progress(lines)
                writer.writerow(
                    {
                        "species_code": species,
                        "tool": tool,
                        "status": status,
                        "progress_kind": kind,
                        "progress_value": value,
                        "last_line": last_line,
                        "runner_log_bytes": (outdir / "runner.log").stat().st_size
                        if (outdir / "runner.log").exists()
                        else 0,
                        "output_dir": str(outdir),
                    }
                )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
