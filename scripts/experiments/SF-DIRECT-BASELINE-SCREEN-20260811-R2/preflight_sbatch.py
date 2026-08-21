#!/usr/bin/env python3
"""Submission-side preflight: log path exists before Slurm opens stdout/stderr."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--stage", required=True, choices=("cpu", "gpu"))
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    log_dir = root / "logs" / cfg["exp_id"]
    log_dir.mkdir(parents=True, exist_ok=True)
    if not log_dir.is_dir() or not os.access(log_dir, os.W_OK | os.X_OK):
        raise SystemExit(f"log directory unavailable before sbatch: {log_dir}")
    locks = [root / cfg["output_root"] / ".stage_owner.lock",
             root / cfg["output_root"] / ".cpu_owner.lock",
             root / cfg["output_root"] / ".gpu_owner.lock"]
    present = [str(lock) for lock in locks if lock.exists()]
    if present:
        raise SystemExit(f"active/stale stage owner lock must be resolved before submission: {present}")
    if args.stage == "gpu" and not (root / cfg["data_pass_pointer"]).is_file():
        raise SystemExit("GPU submission requires a frozen DATA PASS pointer")
    print(json.dumps({"status": "SBATCH_PREFLIGHT_PASS", "stage": args.stage, "log_dir": str(log_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
