#!/usr/bin/env python3
"""Submit finite private-partition preparation; later actions use explicit dependencies."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[3]
NAME = "NONMAMMAL-GENE-UTILITY-20260918"
LOG = ROOT / "outputs" / NAME / "logs"


def submit(action, species, dependency=None, array=None):
    LOG.mkdir(parents=True, exist_ok=True)
    cpu, mem, wall = {"prepare": (4, "32G", "02:00:00"), "native-smoke": (1, "8G", "00:30:00"), "assess-native-smoke": (1, "4G", "00:05:00"), "d-mask": (4, "32G", "01:00:00"), "predict": (1, "8G", "24:00:00"), "score": (1, "8G", "00:30:00")}[action]
    argv = ["sbatch", "--parsable", "--partition=private-teodoro-gpu", "--job-name=ng_"+action+"_"+species, "--cpus-per-task="+str(cpu), "--mem="+mem, "--time="+wall, "--output="+str(LOG / "%x-%A_%a.out"), "--error="+str(LOG / "%x-%A_%a.err")]
    if action == "d-mask":
        argv += ["--gres=gpu:nvidia_geforce_rtx_3090:1"]
    if dependency:
        argv += ["--dependency="+dependency]
    if array:
        argv += ["--array="+array]
    script = ROOT / "scripts/experiments" / NAME / "utility.py"
    command = shlex.join(["python", "-u", str(script), action, species])
    if action == "predict":
        command += ' --index "$SLURM_ARRAY_TASK_ID"'
    wrap = "\n".join(["#!/bin/bash", "set -euo pipefail", "source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh", "conda activate te_benchmark", "export OMP_NUM_THREADS="+str(cpu), "export MKL_NUM_THREADS="+str(cpu), "export OPENBLAS_NUM_THREADS="+str(cpu), "cd "+shlex.quote(str(ROOT)), command])
    argv += ["--wrap", wrap]
    job = subprocess.check_output(argv, text=True).strip().split(";")[0]
    row = {"job_id": job, "action": action, "species": species, "dependency": dependency, "array": array, "cpus": cpu, "memory": mem, "wall": wall, "partition": "private-teodoro-gpu"}
    with (LOG.parent / "jobs.jsonl").open("a") as f:
        f.write(json.dumps(row)+"\n")
    print(json.dumps(row))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("prepare", "native-smoke", "assess-native-smoke", "d-mask", "predict", "score"))
    p.add_argument("species", choices=("chicken", "zebrafish"))
    p.add_argument("--dependency")
    p.add_argument("--array")
    a = p.parse_args()
    submit(a.action, a.species, a.dependency, a.array)
