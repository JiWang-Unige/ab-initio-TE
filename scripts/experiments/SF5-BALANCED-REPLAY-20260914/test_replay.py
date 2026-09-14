#!/usr/bin/env python3
"""Focused tests for the fixed balanced SF5 replay selection and metrics."""
from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path

from replay import select_species_quota, validate_config


def test_actual_config_entry_contract() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    config_path = repo_root / "configs" / "SF5-BALANCED-REPLAY-20260914.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert set(config) == {
        "protocol",
        "status",
        "seed",
        "window",
        "selection",
        "model_paths",
        "outputs",
        "resources",
        "metric_contract",
        "execution_policy",
    }
    assert set(config["selection"]) == {
        "data_relpath",
        "legacy_scored_prefix_limit",
        "species_order",
        "per_species_quota",
        "selected_windows",
        "old_scored_population",
        "excluded_from_new_scoring",
    }
    assert set(config["outputs"]) == {"remote_relroot", "raw_predictions_policy"}
    assert set(config["resources"]) == {
        "partition",
        "gpu",
        "cpus_per_task",
        "memory",
        "time",
    }
    assert set(config["metric_contract"]) == {
        "labels",
        "confusion_orientation",
        "main4_macro_f1",
        "binary_material",
        "raw_position_count",
    }
    assert set(config["execution_policy"]) == {
        "inference_only",
        "legacy_loader",
        "training_path_called",
        "tokenization",
        "new_validation",
        "independent_validation",
    }
    validated = validate_config(config)
    assert validated["data_relpath"].endswith("data.jsonl.gz")
    assert set(validated["model_paths"]) == {
        "SF5_base_pretrained_seed42",
        "SF5_binary_h0_seed42",
    }
    assert validated["prefix_limit"] == 1200
    assert validated["window"] == 4096


def _record(species: str, index: int) -> dict:
    return {
        "species_code": species,
        "sequence": "ACGT",
        "labels": [0, 1, 2, 5],
        "chr": f"chr{index + 1}",
        "start": index * 4,
        "end": index * 4 + 4,
    }


def test_first_quota_within_prefix_excludes_other_species() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.jsonl.gz"
        rows = []
        for species in ("mouse", "fruit_fly", "zebrafish", "chicken", "western_clawed_frog"):
            for index in range(3):
                rows.append(_record(species, len(rows)))
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

        selected, metadata = select_species_quota(
            path,
            ("mouse", "zebrafish", "chicken", "western_clawed_frog"),
            per_species=2,
            prefix_limit=15,
        )

    assert metadata["selected_total"] == 8
    assert metadata["all_selected_within_prefix"] is True
    assert metadata["species_counts"] == {
        "mouse": 2,
        "zebrafish": 2,
        "chicken": 2,
        "western_clawed_frog": 2,
    }
    assert [item["record_index"] for item in selected] == sorted(
        item["record_index"] for item in selected
    )
    assert {item["species_code"] for item in selected} == {
        "mouse",
        "zebrafish",
        "chicken",
        "western_clawed_frog",
    }
    assert "fruit_fly" not in {item["species_code"] for item in selected}


def test_missing_species_quota_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            handle.write(json.dumps(_record("mouse", 0)) + "\n")
        try:
            select_species_quota(path, ("mouse", "zebrafish"), 1, 1)
        except ValueError as error:
            assert "zebrafish" in str(error)
        else:
            raise AssertionError("missing species quota was accepted")


if __name__ == "__main__":
    test_first_quota_within_prefix_excludes_other_species()
    test_missing_species_quota_fails_closed()
    print("SF5 balanced replay contract tests: PASS")
