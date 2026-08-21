#!/usr/bin/env python3
"""
Deterministic helper for Teodoro Slurm routing.

This script does not query Slurm. Supply current queue/window/GPU facts from
sinfo/squeue/scontrol. It returns an approximate routing recommendation.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, asdict
from typing import List, Optional

PRIVATE_LIMIT_HOURS = 168.0
SHARED_LIMIT_HOURS = 12.0
DEFAULT_MIN_VRAM_GB = 20.0


@dataclass
class Candidate:
    name: str
    feasible: bool
    score_hours: Optional[float]
    estimated_completion_hours: Optional[float]
    walltime_hours: Optional[float]
    reasons: List[str]


def yes_no(value: str) -> bool:
    value = value.strip().lower()
    if value in {"yes", "y", "true", "1", "checkpointable"}:
        return True
    if value in {"no", "n", "false", "0", "noncheckpointable", "non-checkpointable"}:
        return False
    raise argparse.ArgumentTypeError("Use yes/no for checkpointable")


def scaled_runtime(expected_hours: float, available_gpus: int, efficient_min_gpus: int) -> tuple[float, List[str]]:
    reasons: List[str] = []
    if available_gpus <= 0:
        return math.inf, ["no GPUs available"]
    if efficient_min_gpus > 0 and available_gpus < efficient_min_gpus:
        factor = efficient_min_gpus / available_gpus
        reasons.append(
            f"available GPUs ({available_gpus}) < efficient_min_gpus ({efficient_min_gpus}); "
            f"runtime scaled by ~{factor:.2f}x"
        )
        return expected_hours * factor, reasons
    return expected_hours, reasons


def make_cpu_candidate(args: argparse.Namespace) -> dict:
    window = min(args.private_window_hours, PRIVATE_LIMIT_HOURS)
    walltime = min(args.expected_hours, window)
    feasible = walltime > 0
    reasons = ["CPU-only job: route to private-teodoro-gpu with 0 GPUs"]
    if args.private_window_hours < args.expected_hours:
        reasons.append("private window is shorter than expected runtime; use shortened walltime only if partial progress is useful")
    return {
        "chosen": "private-teodoro-gpu",
        "request": {"gpus": 0, "walltime_hours": walltime},
        "feasible": feasible,
        "reasons": reasons,
    }


def private_candidate(args: argparse.Namespace) -> Candidate:
    reasons: List[str] = []
    effective_vram = max(args.required_vram_gb, DEFAULT_MIN_VRAM_GB)
    if args.private_available_gpus < args.min_gpus:
        return Candidate("private-teodoro-gpu", False, None, None, None, ["private has fewer GPUs than min_gpus"])

    runtime, scale_reasons = scaled_runtime(args.expected_hours, args.private_available_gpus, args.efficient_min_gpus)
    reasons.extend(scale_reasons)

    window = min(args.private_window_hours, PRIVATE_LIMIT_HOURS)
    if window <= 0:
        return Candidate("private-teodoro-gpu", False, None, None, None, ["no private maintenance-free window"])

    if runtime > window and not args.checkpointable:
        return Candidate(
            "private-teodoro-gpu",
            False,
            None,
            min(runtime, window),
            window,
            reasons + ["non-checkpointable runtime exceeds private maintenance-free window"],
        )

    walltime = min(runtime, window, PRIVATE_LIMIT_HOURS)
    completion = args.private_queue_hours + runtime
    score = completion - args.private_bonus_hours
    reasons.append(f"effective VRAM requirement is {effective_vram:g}GB; ensure chosen private GPUs satisfy it")
    if args.private_bonus_hours:
        reasons.append(f"private bonus applied: {args.private_bonus_hours:g}h")
    return Candidate("private-teodoro-gpu", True, score, completion, walltime, reasons)


def shared_candidate(args: argparse.Namespace) -> Candidate:
    reasons: List[str] = []
    effective_vram = max(args.required_vram_gb, DEFAULT_MIN_VRAM_GB)
    if args.shared_available_gpus < args.min_gpus:
        return Candidate("shared-gpu", False, None, None, None, ["shared has fewer GPUs than min_gpus"])

    runtime, scale_reasons = scaled_runtime(args.expected_hours, args.shared_available_gpus, args.efficient_min_gpus)
    reasons.extend(scale_reasons)

    window = min(args.shared_window_hours, SHARED_LIMIT_HOURS)
    if window <= 0:
        return Candidate("shared-gpu", False, None, None, None, ["no shared maintenance-free window"])

    if runtime > window and not args.checkpointable:
        return Candidate(
            "shared-gpu",
            False,
            None,
            min(runtime, window),
            window,
            reasons + ["non-checkpointable runtime exceeds 12h shared limit"],
        )

    if runtime > window and args.checkpointable:
        segments = math.ceil(runtime / window)
        overhead = max(0, segments - 1) * args.checkpoint_overhead_hours
        reasons.append(f"checkpointable shared run split into ~{segments} segment(s)")
    else:
        segments = 1
        overhead = 0.0

    walltime = min(runtime, window, SHARED_LIMIT_HOURS)
    completion = args.shared_queue_hours + runtime + overhead
    reasons.append(f"effective VRAM requirement is {effective_vram:g}GB; ensure chosen shared GPUs satisfy it")
    return Candidate("shared-gpu", True, completion, completion, walltime, reasons)


def main() -> None:
    parser = argparse.ArgumentParser(description="Choose Teodoro Slurm partition for CPU/GPU jobs")
    parser.add_argument("--task", choices=["cpu", "gpu"], required=True)
    parser.add_argument("--expected-hours", type=float, required=True)
    parser.add_argument("--checkpointable", type=yes_no, default=False)
    parser.add_argument("--min-gpus", type=int, default=0)
    parser.add_argument("--efficient-min-gpus", type=int, default=0)
    parser.add_argument("--required-vram-gb", type=float, default=DEFAULT_MIN_VRAM_GB)
    parser.add_argument("--private-queue-hours", type=float, default=0.0)
    parser.add_argument("--shared-queue-hours", type=float, default=0.0)
    parser.add_argument("--private-available-gpus", type=int, default=0)
    parser.add_argument("--shared-available-gpus", type=int, default=0)
    parser.add_argument("--private-window-hours", type=float, default=PRIVATE_LIMIT_HOURS)
    parser.add_argument("--shared-window-hours", type=float, default=SHARED_LIMIT_HOURS)
    parser.add_argument("--checkpoint-overhead-hours", type=float, default=0.25)
    parser.add_argument("--private-bonus-hours", type=float, default=0.0,
                        help="Optional willingness-to-wait bonus for free private quota; set 0 for pure speed")
    args = parser.parse_args()

    if args.task == "cpu":
        print(json.dumps(make_cpu_candidate(args), indent=2, ensure_ascii=False))
        return

    candidates = [private_candidate(args), shared_candidate(args)]
    feasible = [c for c in candidates if c.feasible and c.score_hours is not None]
    if feasible:
        chosen = min(feasible, key=lambda c: c.score_hours if c.score_hours is not None else math.inf)
    else:
        chosen = None

    result = {
        "chosen": chosen.name if chosen else None,
        "request": {
            "gpus": args.min_gpus if chosen else None,
            "walltime_hours": chosen.walltime_hours if chosen else None,
        },
        "candidates": [asdict(c) for c in candidates],
        "notes": [
            "This helper is approximate; verify current Slurm state and exact GPU types before submitting.",
            "Large-model jobs should use >=20GB VRAM and exclude RTX 3080 by default.",
        ],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
