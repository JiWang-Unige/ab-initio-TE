#!/usr/bin/env python3
"""Supervised four-region sea-urchin adaptation using the frozen D features."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PILOT_PATH = REPO_ROOT / "scripts/experiments/D-ADAPTER-MOE-PILOT-20260914/pilot.py"
spec = importlib.util.spec_from_file_location("d_adapter_pilot_support", PILOT_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"cannot load support pilot from {PILOT_PATH}")
pilot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pilot
spec.loader.exec_module(pilot)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(config_path: Path, output_dir: Path) -> dict:
    config = pilot.read_config(config_path)
    root = Path(config["remote"]["project_root"])
    materialized = root / "outputs/D-ADAPTER-MOE-PILOT-20260914/sea-materialized/sea_urchin_tiles.jsonl.gz"
    materialized_manifest = root / "outputs/D-ADAPTER-MOE-PILOT-20260914/sea-materialized/materialization_manifest.json"
    if not materialized.is_file() or not materialized_manifest.is_file():
        raise FileNotFoundError(
            "sea materialization is required before adaptation: "
            f"{materialized}"
        )
    materialization = json.loads(materialized_manifest.read_text())
    split_label_totals = materialization.get("split_label_totals")
    if not isinstance(split_label_totals, dict) or set(split_label_totals) != {"TRAIN", "CAL", "EVAL"}:
        raise RuntimeError("materialization manifest lacks split-level positive/negative/masked bp totals")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "status.json", {"status": "starting", "started_at": time.time()})
    seed = int(config["seed"])
    pilot.set_seed(seed)
    species_order = ("sea_urchin",)
    tile_counts = {"TRAIN": 256, "CAL": 128, "EVAL": 128}
    selected = {"sea_urchin": {}}
    manifest = {"sea_urchin": {}}
    for split, count in tile_counts.items():
        records, selection = pilot.read_first_complete_tiles(
            materialized, "sea_urchin", split, count
        )
        selected["sea_urchin"][split] = records
        manifest["sea_urchin"][split] = selection
    write_json(output_dir / "input_manifest.json", manifest)

    model_dir = pilot.source_path(config, "d_model", root)
    native_code_dir = pilot.source_path(config, "native_model_code", root)
    model, tokenizer, device = pilot.LEGACY.load_final_model(
        model_dir, model_dir, cpu=False, model_code_dir=native_code_dir
    )
    if device.type != "cuda":
        raise RuntimeError("sea adaptation requires the requested CUDA device")
    hidden_size = int(getattr(model.config, "hidden_size", 0))
    if hidden_size != int(config["model"]["hidden_size"]):
        raise RuntimeError(f"hidden size {hidden_size} differs from locked config")
    for parameter in model.parameters():
        parameter.requires_grad_(False)

    # EVAL is intentionally omitted until after the TRAIN/CAL epoch selection.
    train_cal_selected = {
        "sea_urchin": {
            "TRAIN": selected["sea_urchin"]["TRAIN"],
            "CAL": selected["sea_urchin"]["CAL"],
        }
    }
    train_cal_features = pilot.extract_features(
        model,
        tokenizer,
        device,
        train_cal_selected,
        int(config["training"]["feature_batch_size"]),
        species_order=species_order,
    )
    write_json(
        output_dir / "feature_manifest_train_cal.json",
        {
            "status": "extracted_in_memory",
            "scope": ["TRAIN", "CAL"],
            "hidden_size": hidden_size,
            "feature_dtype": "float16_on_host",
            "base_logits_dtype": "float32_on_host",
            "tokens": sum(
                half["token_count"]
                for split in ("TRAIN", "CAL")
                for tile in train_cal_features["sea_urchin"][split]
                for half in tile["halves"].values()
            ),
        },
    )
    train_features = {"sea_urchin": train_cal_features["sea_urchin"]["TRAIN"]}
    cal_features = {"sea_urchin": train_cal_features["sea_urchin"]["CAL"]}
    arm_results = {}

    # The historical six-species calibration is an explicit frozen reference;
    # it is not refit on sea data and is reported before adapted arms.
    historical_path = pilot.source_path(config, "historical_calibration", root)
    historical_artifact = json.loads(historical_path.read_text())
    historical = {
        "status": "loaded_full_six_species_calibration",
        "path": str(historical_path),
        "platt_slope": float(historical_artifact["platt_slope"]),
        "platt_intercept": float(historical_artifact["platt_intercept"]),
        "threshold": float(historical_artifact["threshold"]),
    }

    arm_classes = (pilot.DenseResidualAdapter, pilot.TwoExpertSoftGate, pilot.ConstantAverageExperts)
    for arm_class in arm_classes:
        pilot.set_seed(seed)
        arm = arm_class(hidden_size)
        trained = pilot.train_one_arm(
            arm,
            train_features,
            cal_features,
            device,
            int(config["training"]["epochs"]),
            seed,
            species_order=species_order,
        )
        arm_results[arm.arm_name] = {
            "arm": arm,
            "train": trained,
        }

    # Only now extract and evaluate region 4.
    eval_selected = {"sea_urchin": {"EVAL": selected["sea_urchin"]["EVAL"]}}
    eval_features = pilot.extract_features(
        model,
        tokenizer,
        device,
        eval_selected,
        int(config["training"]["feature_batch_size"]),
        species_order=species_order,
    )
    write_json(
        output_dir / "feature_manifest_eval.json",
        {
            "status": "extracted_after_cal_selection",
            "scope": ["EVAL"],
            "hidden_size": hidden_size,
            "tokens": sum(
                half["token_count"]
                for tile in eval_features["sea_urchin"]["EVAL"]
                for half in tile["halves"].values()
            ),
        },
    )
    eval_features_flat = {"sea_urchin": eval_features["sea_urchin"]["EVAL"]}

    eval_base_tiles = pilot._tile_records_from_features(
        eval_features_flat, None, device, species_order=species_order
    )
    historical_per_species, historical_summary = pilot.LEGACY.evaluate(
        eval_base_tiles,
        historical["platt_slope"],
        historical["platt_intercept"],
        historical["threshold"],
    )
    sea_cal_base_tiles = pilot._tile_records_from_features(
        {"sea_urchin": train_cal_features["sea_urchin"]["CAL"]},
        None,
        device,
        species_order=species_order,
    )
    sea_cal = pilot.calibration_for_tiles(sea_cal_base_tiles)
    recal_per_species, recal_summary = pilot.LEGACY.evaluate(
        eval_base_tiles,
        sea_cal["platt_slope"],
        sea_cal["platt_intercept"],
        sea_cal["threshold"],
    )
    arms = {
        "D_historical_six_species_calibration": {
            "kind": "frozen_base_logits_with_historical_full_CAL_parameters",
            "trainable_parameters": 0,
            "calibration": historical,
            "eval": {"per_species": historical_per_species, "summary": historical_summary},
        },
        "D_sea_cal_recalibrated": {
            "kind": "frozen_base_logits_recalibrated_on_region3_CAL",
            "trainable_parameters": 0,
            "calibration": {
                key: value
                for key, value in sea_cal.items()
                if key not in {"per_species", "summary"}
            },
            "cal_selection_metrics": {
                "per_species": sea_cal["per_species"],
                "summary": sea_cal["summary"],
            },
            "eval": {"per_species": recal_per_species, "summary": recal_summary},
        },
    }
    for name, item in arm_results.items():
        arm = item["arm"]
        trained = item["train"]
        cal = trained["calibration"]
        eval_tiles = pilot._tile_records_from_features(
            eval_features_flat, arm, device, species_order=species_order
        )
        per_species, summary = pilot.LEGACY.evaluate(
            eval_tiles,
            cal["platt_slope"],
            cal["platt_intercept"],
            cal["threshold"],
        )
        arms[name] = {
            "kind": config["model"]["arms"][name]["kind"],
            "trainable_parameters": pilot.parameter_count(arm),
            "selected_epoch": trained["selected_epoch"],
            "train_steps_per_epoch": trained["train_steps_per_epoch"],
            "train_epochs": trained["train_epochs"],
            "calibration": {
                key: value
                for key, value in cal.items()
                if key not in {"per_species", "summary"}
            },
            "cal_selection_metrics": {
                "per_species": cal["per_species"],
                "summary": cal["summary"],
            },
            "eval": {"per_species": per_species, "summary": summary},
            "route_statistics_eval": pilot.route_statistics(
                arm, eval_features_flat, device, species_order=species_order
            ),
            "training_trace": trained["trace"],
        }

    # Retention/forgetting diagnostic on the original six species.  This is
    # deliberately after sea CAL selection and uses a separate six-species
    # CAL fit; the six-species DEV labels cannot influence any head choice.
    six_selected = {species: {} for species in pilot.SPECIES}
    six_manifest = {species: {} for species in pilot.SPECIES}
    for species in pilot.SPECIES:
        for split in ("CAL", "DEV"):
            records, selection = pilot.read_first_complete_tiles(
                pilot.data_path(config, root, species, split),
                species,
                split,
                int(config["selection"]["tiles_per_species_per_split"]),
            )
            six_selected[species][split] = records
            six_manifest[species][split] = selection
    six_features = pilot.extract_features(
        model,
        tokenizer,
        device,
        six_selected,
        int(config["training"]["feature_batch_size"]),
        species_order=pilot.SPECIES,
    )
    write_json(output_dir / "six_species_retention_input_manifest.json", six_manifest)
    six_cal_features = {species: six_features[species]["CAL"] for species in pilot.SPECIES}
    six_dev_features = {species: six_features[species]["DEV"] for species in pilot.SPECIES}
    six_cal_base_tiles = pilot._tile_records_from_features(
        six_cal_features, None, device, species_order=pilot.SPECIES
    )
    six_dev_base_tiles = pilot._tile_records_from_features(
        six_dev_features, None, device, species_order=pilot.SPECIES
    )
    six_base_cal = pilot.calibration_for_tiles(six_cal_base_tiles)
    six_base_dev_per_species, six_base_dev_summary = pilot.LEGACY.evaluate(
        six_dev_base_tiles,
        six_base_cal["platt_slope"],
        six_base_cal["platt_intercept"],
        six_base_cal["threshold"],
    )
    six_historical_per_species, six_historical_summary = pilot.LEGACY.evaluate(
        six_dev_base_tiles,
        historical["platt_slope"],
        historical["platt_intercept"],
        historical["threshold"],
    )
    six_sea_cal_per_species, six_sea_cal_summary = pilot.LEGACY.evaluate(
        six_dev_base_tiles,
        sea_cal["platt_slope"],
        sea_cal["platt_intercept"],
        sea_cal["threshold"],
    )
    retention = {
        "calibration_scope": "original six species first-32 CAL tiles; fitted after sea adaptation",
        "dev_scope": "original six species first-32 DEV tiles; no DEV-based selection",
        "direct_sea_calibration_scope": "apply the sea TRAIN/CAL-selected parameters directly to original six-species DEV",
        "D_recalibrated": {
            "calibration": {
                key: value
                for key, value in six_base_cal.items()
                if key not in {"per_species", "summary"}
            },
            "dev": {"per_species": six_base_dev_per_species, "summary": six_base_dev_summary},
        },
        "D_historical_six_species_calibration": {
            "calibration": historical,
            "dev": {
                "per_species": six_historical_per_species,
                "summary": six_historical_summary,
            },
        },
        "D_sea_cal_recalibrated": {
            "calibration": {
                key: value
                for key, value in sea_cal.items()
                if key not in {"per_species", "summary"}
            },
            "dev": {"per_species": six_sea_cal_per_species, "summary": six_sea_cal_summary},
        },
        "adapted_heads": {},
    }
    for name, item in arm_results.items():
        arm = item["arm"]
        six_cal_tiles = pilot._tile_records_from_features(
            six_cal_features, arm, device, species_order=pilot.SPECIES
        )
        six_dev_tiles = pilot._tile_records_from_features(
            six_dev_features, arm, device, species_order=pilot.SPECIES
        )
        adapted_six_cal = pilot.calibration_for_tiles(six_cal_tiles)
        adapted_six_dev_per_species, adapted_six_dev_summary = pilot.LEGACY.evaluate(
            six_dev_tiles,
            adapted_six_cal["platt_slope"],
            adapted_six_cal["platt_intercept"],
            adapted_six_cal["threshold"],
        )
        sea_selected_cal = item["train"]["calibration"]
        sea_selected_six_dev_per_species, sea_selected_six_dev_summary = pilot.LEGACY.evaluate(
            six_dev_tiles,
            sea_selected_cal["platt_slope"],
            sea_selected_cal["platt_intercept"],
            sea_selected_cal["threshold"],
        )
        retention["adapted_heads"][name] = {
            "calibration": {
                key: value
                for key, value in adapted_six_cal.items()
                if key not in {"per_species", "summary"}
            },
            "dev": {
                "per_species": adapted_six_dev_per_species,
                "summary": adapted_six_dev_summary,
            },
            "dev_using_sea_selected_calibration": {
                "calibration": {
                    key: value
                    for key, value in sea_selected_cal.items()
                    if key not in {"per_species", "summary"}
                },
                "per_species": sea_selected_six_dev_per_species,
                "summary": sea_selected_six_dev_summary,
            },
            "route_statistics_dev": pilot.route_statistics(
                arm, six_dev_features, device, species_order=pilot.SPECIES
            ),
        }
        arms[name]["original_six_species_retention"] = retention["adapted_heads"][name]
    arms["D_historical_six_species_calibration"]["original_six_species_retention"] = retention[
        "D_historical_six_species_calibration"
    ]
    arms["D_sea_cal_recalibrated"]["original_six_species_retention"] = retention[
        "D_sea_cal_recalibrated"
    ]
    write_json(output_dir / "original_six_species_retention.json", retention)
    for item in arm_results.values():
        del item["arm"]
    del model
    if pilot.torch.cuda.is_available():
        pilot.torch.cuda.empty_cache()
    result = {
        "experiment": config["experiment"],
        "status": "completed",
        "scientific_status": "exploratory_supervised_sea_urchin_adaptation_not_zero_shot",
        "config": str(config_path),
        "output_dir": str(output_dir),
        "materialization_manifest": str(materialized_manifest),
        "label_denominators": {
            "split_label_totals": split_label_totals,
            "evaluation_split": "EVAL",
            "positive": "label == 1",
            "reference_negative": "label == 0 on A/C/G/T bases after unknown-over-positive masking",
            "masked": "label == ? (unknown/ambiguous/PLE or non-ACGT)",
            "same_mask_for_all_arms": True,
            "comparison_boundary": "These denominators are specific to the new sea mask and are not the old T1 knownTE union denominator.",
        },
        "split_policy": {
            "TRAIN": "regions 1+2",
            "CAL": "region 3",
            "EVAL": "region 4, touched only after CAL epoch selection",
        },
        "model_dir": str(model_dir),
        "native_model_code": str(native_code_dir),
        "selection": manifest,
        "feature_contract": {
            "hidden_size": hidden_size,
            "kmer_bp": 6,
            "quality_unit": "bp",
            "unknown_and_ambiguous_masked": True,
            "ple_masked": True,
            "other_acgt_reference_negative": True,
        },
        "retention": retention,
        "arms": arms,
    }
    write_json(output_dir / "results.json", result)
    write_json(output_dir / "status.json", {"status": "completed", "finished_at": time.time()})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.config, args.output_dir)
        print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2), flush=True)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            args.output_dir / "failure.json",
            {"status": "failed", "error": str(exc), "traceback": traceback.format_exc()},
        )
        raise


if __name__ == "__main__":
    main()
