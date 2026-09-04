#!/usr/bin/env python3
"""Launch one bounded L/D upstream-coverage training arm."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType


EXPERIMENT_ID = "CROSS-SPECIES-L1-UPSTREAM-20260904"
PROTOCOL = f"{EXPERIMENT_ID}-V1"
RUN_ROLE = "upstream_coverage_pilot"
SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
ARM_CHOICES = ("L", "D")
PILOT_STEPS = 4000
PILOT_WARMUP_STEPS = 400


def _load_legacy() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[1]
        / "CROSS-SPECIES-L1-20260903"
        / "cross_species_token_task.py"
    )
    spec = importlib.util.spec_from_file_location("cross_species_token_task", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = _load_legacy()


def training_sources(data_root: Path, upstream_root: Path, arm: str) -> list[str]:
    """Return optional legacy ``species=TRAIN-path`` overrides for this arm."""

    if arm not in ARM_CHOICES:
        raise ValueError(f"unsupported upstream arm: {arm}")
    if arm == "L":
        return []
    worm = Path(upstream_root) / "TRAIN" / "c_elegans.jsonl.gz"
    return [f"c_elegans={worm}"]


def train(args) -> None:
    """Use the legacy B1 loop with the new protocol metadata and D override."""

    legacy_args = argparse.Namespace(**vars(args))
    # B1 is the legacy name for one tile per species with uniform ERM weights.
    legacy_args.arm = "B1"
    legacy_args.species = None
    legacy_args.run_role = RUN_ROLE
    legacy_args.protocol = PROTOCOL
    legacy_args.experiment_arm = args.arm
    legacy_args.max_steps = PILOT_STEPS
    legacy_args.warmup_steps = PILOT_WARMUP_STEPS
    legacy_args.species_data = training_sources(
        args.data_root, args.upstream_root, args.arm
    )
    legacy.train(legacy_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARM_CHOICES, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    train(build_parser().parse_args())


if __name__ == "__main__":
    main()
