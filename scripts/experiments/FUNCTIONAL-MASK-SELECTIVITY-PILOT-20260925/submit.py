#!/usr/bin/env python3
"""Submit the fixed pilot without requesting a GPU.

This helper only records jobs for this protocol.  It never touches the older
NONMAMMAL or WHOLE-GENOME job ledgers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
NAME = "FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925"
REPORT = ROOT / "reports" / NAME
SCRIPT = ROOT / "scripts/experiments" / NAME / "run.sbatch"


def submit(action, species, dependency=None, array=None):
    REPORT.mkdir(parents=True, exist_ok=True)
    log = ROOT / "outputs" / NAME / "logs"
    log.mkdir(parents=True, exist_ok=True)
    if action == "prepare":
        cpus, memory, wall = 4, "32G", "02:00:00"
    elif action == "predict":
        cpus, memory, wall = 1, "8G", "24:00:00"
    else:
        cpus, memory, wall = 1, "8G", "01:00:00"
    argv = [
        "sbatch",
        "--parsable",
        "--partition=private-teodoro-gpu",
        "--job-name=fms_" + action + "_" + species,
        "--cpus-per-task=" + str(cpus),
        "--mem=" + memory,
        "--time=" + wall,
        "--export=ALL,ACTION=" + action + ",SPECIES=" + species,
    ]
    if dependency:
        argv.append("--dependency=" + dependency)
    if array:
        argv.append("--array=" + array)
    argv.append(str(SCRIPT))
    job = subprocess.check_output(argv, text=True).strip().split(";")[0]
    row = {
        "job_id": job,
        "action": action,
        "species": species,
        "dependency": dependency,
        "array": array,
        "cpus": cpus,
        "memory": memory,
        "wall": wall,
        "partition": "private-teodoro-gpu",
        "gpu": False,
    }
    with (REPORT / "jobs.jsonl").open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    print(json.dumps(row))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "predict", "score"))
    parser.add_argument("species", choices=("chicken", "zebrafish"))
    parser.add_argument("--dependency")
    parser.add_argument("--array")
    args = parser.parse_args()
    submit(args.action, args.species, args.dependency, args.array)


if __name__ == "__main__":
    main()
