#!/usr/bin/env python3
"""Regression for a masked sea tile and single-species calibration routing."""
import importlib.util
from pathlib import Path

import numpy as np
import torch


spec = importlib.util.spec_from_file_location("adapter_pilot_test", Path(__file__).with_name("pilot.py"))
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def tile(masked):
    half = {
        "hidden": np.ones((2, 4), dtype=np.float16),
        "base_logits": np.zeros((2, 2), dtype=np.float32),
        "positive_bp": np.zeros(2, dtype=np.float32) if masked else np.ones(2, dtype=np.float32),
        "negative_bp": np.zeros(2, dtype=np.float32) if masked else np.full(2, 5, dtype=np.float32),
    }
    return {"halves": {0: half, 1: half}}


calls = []


def project(features, arm, device, species_order=pilot.SPECIES):
    assert tuple(species_order) == ("sea_urchin",), species_order
    assert set(features) == {"sea_urchin"}
    calls.append(tuple(species_order))
    return features


pilot._tile_records_from_features = project
pilot.calibration_for_tiles = lambda _: {
    "summary": {"minimum_species_bp_f1": 0.5, "macro_bp_f1": 0.5},
    "threshold": 0.5,
    "platt_slope": 1.0,
    "platt_intercept": 0.0,
}
pilot.set_seed(42)
arm = pilot.DenseResidualAdapter(4)
result = pilot.train_one_arm(
    arm, {"sea_urchin": [tile(True), tile(False)]},
    {"sea_urchin": [tile(False)]}, torch.device("cpu"), 1, 42,
    species_order=("sea_urchin",),
)
assert result["trace"][0]["optimizer_steps"] == 1
assert result["trace"][0]["skipped_fully_masked_steps"] == 1
assert len(calls) == 2  # epoch selection and final frozen calibration
try:
    pilot.train_one_arm(
        pilot.DenseResidualAdapter(4), {"sea_urchin": [tile(True)]},
        {"sea_urchin": [tile(False)]}, torch.device("cpu"), 1, 42,
        species_order=("sea_urchin",),
    )
except RuntimeError as error:
    assert "entire TRAIN epoch" in str(error)
else:
    raise AssertionError("an entirely unlabelled training selection must fail")
print("PASS masked-step handling and single-species CAL routing")
