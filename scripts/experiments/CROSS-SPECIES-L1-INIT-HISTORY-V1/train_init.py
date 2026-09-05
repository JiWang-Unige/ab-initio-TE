#!/usr/bin/env python3
"""Registered 4000-step initialization pair; optional separate engineering smoke."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from functools import partial
from pathlib import Path

import init_model

LEGACY_PATH = Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903" / "cross_species_token_task.py"
spec = importlib.util.spec_from_file_location("init_history_legacy_training", LEGACY_PATH)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def train(args):
    if args.seed not in {42, 17}:
        raise ValueError("only registered seeds 42/17 are allowed")
    if args.engineering_smoke and not 1 <= args.smoke_steps <= 4:
        raise ValueError("engineering smoke is bounded to 1-4 steps")
    forwarded = argparse.Namespace(**vars(args))
    forwarded.arm = "B1"
    forwarded.species = None
    forwarded.experiment_arm = args.arm
    forwarded.protocol = init_model.PROTOCOL
    forwarded.run_role = "initialization_engineering_smoke" if args.engineering_smoke else "initialization_history_pilot"
    forwarded.max_steps = args.smoke_steps if args.engineering_smoke else 4000
    forwarded.warmup_steps = 400
    forwarded.collect_exposure = True
    forwarded.species_data = [f"c_elegans={Path(args.upstream_root) / 'TRAIN' / 'c_elegans.jsonl.gz'}"]
    legacy.train(forwarded, model_loader=partial(
        init_model.load_model_and_tokenizer, args.arm, args.seed,
        base_model=args.base_model, h0_checkpoint=args.h0_checkpoint,
    ))
    if args.engineering_smoke:
        rows = [json.loads(line) for line in (Path(args.output_dir) / "train_log.jsonl").read_text().splitlines()]
        if len(rows) != args.smoke_steps or any(
            not math.isfinite(value) for row in rows for value in row["loss"].values()
        ):
            raise ValueError("engineering smoke did not complete its bounded steps with finite losses")
        (Path(args.output_dir) / "smoke_summary.json").write_text(json.dumps({
            "status": "PASS", "role": forwarded.run_role,
            "scientific_evidence": False, "steps": args.smoke_steps,
            "arm": args.arm, "seed": args.seed,
            "finite_losses": True, "protocol": init_model.PROTOCOL,
        }, indent=2) + "\n")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("H0R", "P0R"), required=True)
    parser.add_argument("--seed", type=int, choices=(42, 17), default=42)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-model", type=Path, default=init_model.BASE_MODEL)
    parser.add_argument("--h0-checkpoint", type=Path, default=init_model.H0_CHECKPOINT)
    parser.add_argument("--engineering-smoke", action="store_true")
    parser.add_argument("--smoke-steps", type=int, default=4)
    return parser


if __name__ == "__main__":
    train(build_parser().parse_args())
