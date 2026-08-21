#!/usr/bin/env python3
"""Summarize de novo benchmark per-species/per-tool state from disk."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


TOOLS = ("repeatmodeler", "edta", "repeatscout", "earlgrey")


def load_status(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def classify(outdir: Path, status: dict) -> str:
    if (outdir / "ACCEPT_DONE").exists():
        return "accept_done"
    if (outdir / "FAILED").exists():
        return "failed"
    if (outdir / "DONE").exists():
        return "done_no_accept"
    state = status.get("status")
    if state in {"running", "submitted", "success", "completed", "failed"}:
        return str(state)
    if any((outdir / name).exists() for name in ("annotation.gff3", "annotation.bed", "library.fasta")):
        return "partial_outputs"
    return "missing"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument(
        "--data-root",
        help="Optional override for the per-species/per-tool output root. "
        "Defaults to <run-root>/raw_outputs.",
    )
    parser.add_argument(
        "--tools",
        default=",".join(TOOLS),
        help="Comma-separated tool list to summarize. "
        f"Default: {','.join(TOOLS)}",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    run_root = Path(args.run_root)
    species_manifest = run_root / "manifests" / "species_manifest.tsv"
    data_root = Path(args.data_root) if args.data_root else run_root / "raw_outputs"
    tools = tuple(tool.strip() for tool in args.tools.split(",") if tool.strip())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    species_rows = []
    with species_manifest.open() as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        species_rows = list(reader)

    fieldnames = [
        "species_code",
        "tool",
        "state",
        "status_json_state",
        "done",
        "accept_done",
        "failed_marker",
        "annotation_gff3",
        "annotation_bed",
        "library_fasta",
        "runner_log_bytes",
        "status_json",
        "output_dir",
    ]
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in species_rows:
            species = row["species_code"]
            for tool in tools:
                outdir = data_root / species / tool
                status_path = outdir / "status.json"
                status = load_status(status_path)
                runner_log = outdir / "runner.log"
                writer.writerow(
                    {
                        "species_code": species,
                        "tool": tool,
                        "state": classify(outdir, status),
                        "status_json_state": status.get("status", ""),
                        "done": int((outdir / "DONE").exists()),
                        "accept_done": int((outdir / "ACCEPT_DONE").exists()),
                        "failed_marker": int((outdir / "FAILED").exists()),
                        "annotation_gff3": int((outdir / "annotation.gff3").exists()),
                        "annotation_bed": int((outdir / "annotation.bed").exists()),
                        "library_fasta": int((outdir / "library.fasta").exists()),
                        "runner_log_bytes": runner_log.stat().st_size if runner_log.exists() else 0,
                        "status_json": str(status_path) if status_path.exists() else "",
                        "output_dir": str(outdir),
                    }
                )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
