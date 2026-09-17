#!/usr/bin/env python3
"""Validate the fixed D external-panel manifest without reading sealed data.

This is a readiness helper only. It validates the frozen checkpoint/calibration
identity, candidate roles, and resource limits. It does not open FASTA/labels,
run inference, submit Slurm jobs, or fit a threshold.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TRAINING_SPECIES = {
    "human",
    "mouse",
    "chicken",
    "zebrafish",
    "pig",
    "c_elegans",
}
FORBIDDEN_ROLES = {"sealed", "reserved", "old_conf", "chr19_to_chr22"}
REQUIRED_FIELDS = {
    "species",
    "scientific_name",
    "assembly",
    "kingdom_group",
    "tiberius_config",
    "panel_role",
    "label_status",
    "sealed",
}


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != "ANIMAL-GENERALIZATION-CLOSURE-20260917-V1":
        raise ValueError("unexpected readiness schema")
    if payload.get("execution_authorized") is not False:
        raise ValueError("readiness manifest must remain execution-disabled")
    return payload


def validate(payload: dict) -> dict:
    model = payload["model"]
    if model["calibration_scope"] != "six-species-shared":
        raise ValueError("external evaluation must use the six-species calibration")
    if model["fit_split"] != "CAL":
        raise ValueError("external evaluation calibration must be CAL-only")
    if abs(float(model["threshold"]) - 0.42330056285498807) > 1e-15:
        raise ValueError("frozen seed42 threshold changed")
    if model["window_bp"] != 4096 or model["batch_size"] != 12:
        raise ValueError("frozen D inference geometry changed")
    if set(payload["training_species"]) != TRAINING_SPECIES:
        raise ValueError("training species differ from the audited D model")
    seen = set()
    for row in payload["candidate_panel"]:
        missing = REQUIRED_FIELDS - set(row)
        if missing:
            raise ValueError(f"candidate {row.get('species')} missing {sorted(missing)}")
        species = row["species"]
        if species in seen:
            raise ValueError(f"duplicate candidate {species}")
        seen.add(species)
        if species in TRAINING_SPECIES:
            raise ValueError(f"candidate is a D training species: {species}")
        if row["sealed"]:
            raise ValueError(f"sealed candidate is forbidden: {species}")
        if str(row["panel_role"]).lower() in FORBIDDEN_ROLES:
            raise ValueError(f"forbidden panel role: {species}")
    resources = payload["resources"]
    if resources["new_training_gpu_hours"] != 0:
        raise ValueError("this manifest cannot authorize training")
    if resources["max_parallel_species"] > 2:
        raise ValueError("readiness resource cap allows at most two parallel species")
    return {
        "status": "READY_FOR_SEPARATE_PROTOCOL",
        "execution_authorized": False,
        "sealed_inputs_opened": False,
        "training_species": sorted(TRAINING_SPECIES),
        "candidate_species": sorted(seen),
        "frozen_threshold": model["threshold"],
        "new_training_gpu_hours": resources["new_training_gpu_hours"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(load(args.config)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
