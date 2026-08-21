#!/usr/bin/env python3
"""Rebuild the Wave-1 F registry as a valid typed block or integrity failure.

The command performs identity/truth/comparator semantic audits only. It never
runs H0 inference, a biological screen, or a scientific lattice.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import stat
import sys
from pathlib import Path


EXP_ID = "FRAG-EVIDENCE-REGISTRY-20260811-R2"
EXPECTED_BLOCKERS = ["ACCEPTED_POSTPROCESSOR_UNFROZEN", "SCIENTIFIC_LATTICE_UNIMPLEMENTED"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, payload):
    atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def directory_inventory(path: Path):
    if stat.S_ISLNK(os.lstat(path).st_mode) or not path.is_dir():
        raise ValueError("H0 directory root must be a real directory")
    rows, total = [], 0
    for base, dirnames, filenames in os.walk(path, topdown=True, followlinks=False):
        dirnames.sort(); filenames.sort(); base_path = Path(base)
        for name in dirnames:
            mode = os.lstat(base_path / name).st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise ValueError("H0 inventory rejects linked/non-directory entries")
        for name in filenames:
            item = base_path / name; before = os.lstat(item)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("H0 inventory rejects nonregular files")
            digest = sha256_file(item); after = os.lstat(item)
            if (before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns):
                raise ValueError("H0 input race detected")
            rows.append({"path": item.relative_to(path).as_posix(), "bytes": int(after.st_size), "sha256": digest})
            total += int(after.st_size)
    rows.sort(key=lambda row: row["path"])
    digest = hashlib.sha256()
    for row in rows:
        digest.update(f"{row['sha256']}\t{row['bytes']}\t{row['path']}\n".encode())
    return rows, total, digest.hexdigest()


def load_semantics(root: Path):
    path = root / "scripts" / "experiments" / EXP_ID / "frozen_semantics.py"
    spec = importlib.util.spec_from_file_location("frag_r2_frozen_semantics", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def verify_file_rows(root: Path, assets):
    rows = []
    for asset in assets:
        path = root / asset["path"]
        observed = sha256_file(path) if path.is_file() and not path.is_symlink() else None
        rows.append({**asset, "observed_sha256": observed, "pass": observed == asset["sha256"]})
    return rows


def command_rows(root: Path, config_path: Path, config: dict):
    rows = [{"id": "config", "path": str(config_path.relative_to(root)), "expected_sha256": "DYNAMIC_SELF", "observed_sha256": sha256_file(config_path), "pass": True}]
    for item in config["command_assets"]:
        path = root / item["path"]
        observed = sha256_file(path) if path.is_file() else None
        rows.append({"id": item["id"], "path": item["path"], "expected_sha256": item["sha256"], "observed_sha256": observed, "pass": observed == item["sha256"]})
    return rows


def static_check(root: Path, config_path: Path, config: dict):
    assert config["schema_version"] == "FRAG-EVIDENCE-REGISTRY-CONFIG-2.1"
    assert config["execution_contract"]["pre_run_status"] == "IMPLEMENTED_NOT_RUN"
    assert config["execution_contract"]["typed_block_status"] == "FOUNDATIONAL_TYPED_BLOCK"
    assert config["execution_contract"]["integrity_failure_status"] == "INVALID_ASSET_INTEGRITY"
    assert config["execution_contract"]["formal_requires_slurm_job_id"] is True
    assert config["same_input_contract"]["accepted_postprocessor"] is None
    assert config["same_input_contract"]["comparators"]["HMM2"]["role"] == "historical_fixed_comparator"
    assert config["scientific_lattice"]["implemented"] is False
    assert config["truth_registry"]["real_T0_available"] is False
    assert config["truth_registry"]["T2"] == []
    assert set(config["t1_only_metric_contract"]["allowed"]).isdisjoint(config["t1_only_metric_contract"]["forbidden"])
    commands = command_rows(root, config_path, config)
    assert all(row["pass"] for row in commands)
    probes = load_semantics(root).run_semantic_probes()
    assert probes["pass"]
    return {"semantic_probes": probes, "command_rows": commands}


def environment_payload(root: Path):
    git_present = (root / ".git").exists()
    return {
        "schema_version": "environment-manifest-v2", "exp_id": EXP_ID,
        "python_version": platform.python_version(), "python_executable": sys.executable,
        "platform": platform.platform(), "conda_default_env": os.environ.get("CONDA_DEFAULT_ENV"),
        "conda_prefix": os.environ.get("CONDA_PREFIX"), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "git_metadata_present": git_present,
        "git_state": "GIT_METADATA_PRESENT_UNPINNED" if git_present else "NO_GIT_METADATA",
        "scientific_dependencies_required": [], "scientific_execution_performed": False,
    }


def write_tsv(path: Path, headers, rows):
    lines = ["\t".join(headers)]
    for row in rows:
        lines.append("\t".join(str(row.get(header, "")) for header in headers))
    atomic_text(path, "\n".join(lines) + "\n")


def write_invalid(output: Path, reason: str, integrity_checks=None):
    integrity_check_count_passed = sum(1 for passed in (integrity_checks or {}).values() if passed)
    report = {
        "schema_version": "FRAG-EVIDENCE-ASSET-GATE-2.1", "exp_id": EXP_ID,
        "status": "INVALID_ASSET_INTEGRITY", "result_kind": "formal_integrity_failure",
        "semantic_success": False, "expected_typed_block_reached": False,
        "scientific_screen_authorized": False, "scientific_execution_performed": False,
        "integrity_failures": [reason], "typed_blockers": EXPECTED_BLOCKERS,
    }
    metrics = {
        "schema_version": "metrics-v1", "exp_id": EXP_ID, "profile": "smoke",
        "result_kind": "formal_integrity_failure", "primary_metric_name": "registry_integrity_valid",
        "primary_metric": 0.0, "semantic_success": False, "claim_eligible": False,
        "integrity_check_count_passed": integrity_check_count_passed,
        "scientific_screen_executed": False, "status": "INVALID_ASSET_INTEGRITY",
        "metrics": {"registry_integrity_valid": 0.0, "expected_typed_block_reached": 0.0,
                    "integrity_check_count_passed": float(integrity_check_count_passed),
                    "accepted_postprocessor_count": 0.0, "scientific_lattice_implementation_count": 0.0,
                    "scientific_execution_performed": 0.0},
    }
    atomic_json(output / "asset_gate_report.json", report); atomic_json(output / "metrics.json", metrics)
    write_tsv(output / "output_manifest.tsv", ["path", "sha256"], [
        {"path": "asset_gate_report.json", "sha256": sha256_file(output / "asset_gate_report.json")},
        {"path": "metrics.json", "sha256": sha256_file(output / "metrics.json")},
    ])
    atomic_text(output / "STATUS", "INVALID_ASSET_INTEGRITY\n")
    return 2


def build(root: Path, config_path: Path, config: dict):
    if not os.environ.get("SLURM_JOB_ID"):
        print(json.dumps({
            "status": "REFUSED_NO_SLURM_JOB_ID",
            "exp_id": EXP_ID,
            "message": "formal non-static execution requires SLURM_JOB_ID; no result files were written",
        }, sort_keys=True), file=sys.stderr)
        return 2
    output = root / "outputs" / EXP_ID; output.mkdir(parents=True, exist_ok=True)
    atomic_text(output / "STATUS", "RUNNING\n")
    integrity_checks = {}
    try:
        static = static_check(root, config_path, config)
        environment = environment_payload(root)
        asset_rows = verify_file_rows(root, config["assets"])
        command_manifest_rows = static["command_rows"]
        h0 = config["h0_directory_pin"]
        inventory, total, directory_digest = directory_inventory(root / h0["path"])
        h0_pass = total == h0["expected_bytes"] and len(inventory) == h0["expected_file_count"] and directory_digest == h0["sha256"]
        fly_summary = json.loads((root / next(x["path"] for x in config["assets"] if x["id"] == "flybase_summary")).read_text())
        rice_summary = json.loads((root / next(x["path"] for x in config["assets"] if x["id"] == "rice_summary")).read_text())
        fly_verify = json.loads((root / next(x["path"] for x in config["assets"] if x["id"] == "flybase_verification")).read_text())
        rice_verify = json.loads((root / next(x["path"] for x in config["assets"] if x["id"] == "rice_verification")).read_text())
        truth_pass = (fly_summary.get("truth_tier") == "T1_curated_positive_only"
                      and rice_summary.get("truth_tier") == "T1_reference_positive_segments_only"
                      and fly_summary.get("coordinate_contract", {}).get("unlabeled_space_is_negative") is False
                      and rice_summary.get("coordinate_contract", {}).get("unlabeled_space_is_negative") is False
                      and fly_verify.get("pass") is True and rice_verify.get("pass") is True)
        probes = static["semantic_probes"]
        comparator_probe_names = config["same_input_contract"]["required_semantic_probes"]
        comparator_pass = all(probes["checks"].get(name) is True for name in comparator_probe_names)
        environment_pass = environment["conda_default_env"] == "benchmark_core" and environment["git_metadata_present"] is False
        integrity_checks = {
            "asset_hashes": all(row["pass"] for row in asset_rows), "command_hashes": all(row["pass"] for row in command_manifest_rows),
            "h0_directory_pin": h0_pass, "truth_semantics": truth_pass,
            "comparator_aggregation_and_leaf_probes": comparator_pass, "environment": environment_pass,
        }
        integrity_valid = all(integrity_checks.values())
        integrity_check_count_passed = sum(1 for passed in integrity_checks.values() if passed)
        status = "FOUNDATIONAL_TYPED_BLOCK" if integrity_valid else "INVALID_ASSET_INTEGRITY"
        semantic_success = integrity_valid
        registry = {
            "schema_version": "FRAG-TIERED-INPUT-TRUTH-REGISTRY-2.1", "exp_id": EXP_ID,
            "status": status, "T0": config["truth_registry"]["T0"], "T1": config["truth_registry"]["T1"],
            "T2": [], "real_T0_available": False, "claim_boundary": config["t1_only_metric_contract"]["claim_boundary"],
            "scientific_screen_authorized": False,
        }
        comparator = {
            "schema_version": "FRAG-SAME-INPUT-COMPARATOR-FREEZE-2.1", "exp_id": EXP_ID,
            "status": "PASS" if comparator_pass else "INVALID", **config["same_input_contract"],
            "accepted_postprocessor_count": 0,
        }
        audit = {
            "schema_version": "FRAG-TRUTH-LEAKAGE-AUDIT-1.1", "status": "PASS" if truth_pass else "INVALID",
            "training_or_fit_performed": False, "split_required_for_this_asset_only_stage": False,
            "unlabeled_space_treated_as_negative": False, "whole_genome_precision_or_f1_authorized": False,
            "allowed_metrics": config["t1_only_metric_contract"]["allowed"], "forbidden_metrics": config["t1_only_metric_contract"]["forbidden"],
        }
        report = {
            "schema_version": "FRAG-EVIDENCE-ASSET-GATE-2.1", "exp_id": EXP_ID,
            "status": status, "result_kind": "formal_typed_block" if integrity_valid else "formal_integrity_failure",
            "semantic_success": semantic_success, "integrity_checks": integrity_checks,
            "expected_typed_block_reached": integrity_valid, "typed_blockers": EXPECTED_BLOCKERS,
            "accepted_postprocessor_count": 0, "scientific_lattice_implementation_count": 0,
            "historical_fixed_comparators": ["HMM2"], "scientific_screen_authorized": False,
            "scientific_execution_performed": False,
        }
        metrics = {
            "schema_version": "metrics-v1", "exp_id": EXP_ID, "profile": "smoke",
            "result_kind": report["result_kind"], "primary_metric_name": "registry_integrity_valid",
            "primary_metric": float(integrity_valid), "semantic_success": semantic_success,
            "integrity_check_count_passed": integrity_check_count_passed,
            "claim_eligible": False, "scientific_screen_executed": False, "status": status,
            "metrics": {
                "registry_integrity_valid": float(integrity_valid), "expected_typed_block_reached": float(integrity_valid),
                "integrity_check_count_passed": float(integrity_check_count_passed),
                "h0_directory_pin_pass": float(h0_pass), "truth_registry_pass": float(truth_pass),
                "same_input_comparator_gate_pass": float(comparator_pass), "accepted_postprocessor_count": 0.0,
                "scientific_lattice_implementation_count": 0.0, "typed_blocker_count": 2.0,
                "scientific_execution_performed": 0.0,
            },
        }
        assert all(math.isfinite(float(value)) for value in metrics["metrics"].values())
        payloads = {
            "h0_directory_pin.json": {"schema_version": "FRAG-R2-DIRECTORY-PINS-1.1", "expected": h0,
                                      "observed": {"bytes": total, "file_count": len(inventory), "sha256": directory_digest}, "pass": h0_pass},
            "tiered_truth_registry.json": registry, "comparator_freeze.json": comparator,
            "predicted_loci_schema.json": config["predicted_loci_schema"], "truth_leakage_audit.json": audit,
            "semantic_probe_report.json": probes, "asset_gate_report.json": report,
            "metrics.json": metrics, "environment_manifest.json": environment,
        }
        for name, payload in payloads.items(): atomic_json(output / name, payload)
        write_tsv(output / "h0_directory_inventory.tsv", ["path", "bytes", "sha256"], inventory)
        input_rows = [{"id": row["id"], "path": row["path"], "expected_sha256": row["sha256"],
                       "observed_sha256": row["observed_sha256"] or "", "pass": str(row["pass"]).lower()} for row in asset_rows]
        input_rows.append({"id": "h0_checkpoint", "path": h0["path"], "expected_sha256": h0["sha256"],
                           "observed_sha256": directory_digest, "pass": str(h0_pass).lower()})
        write_tsv(output / "input_manifest.tsv", ["id", "path", "expected_sha256", "observed_sha256", "pass"], input_rows)
        write_tsv(output / "command_manifest.tsv", ["id", "path", "expected_sha256", "observed_sha256", "pass"], command_manifest_rows)
        output_names = sorted(list(payloads) + ["h0_directory_inventory.tsv", "input_manifest.tsv", "command_manifest.tsv"])
        if (output / "env.txt").is_file(): output_names.append("env.txt")
        write_tsv(output / "output_manifest.tsv", ["path", "sha256"], [{"path": name, "sha256": sha256_file(output / name)} for name in output_names])
        atomic_text(output / "STATUS", status + "\n")
        return 0 if integrity_valid else 2
    except Exception as exc:
        return write_invalid(output, f"{type(exc).__name__}: {exc}", integrity_checks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--config", type=Path, default=Path("configs") / f"{EXP_ID}.yaml")
    parser.add_argument("--static-check", action="store_true")
    args = parser.parse_args(); root = args.project_root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = json.loads(config_path.read_text())
    if args.static_check:
        result = static_check(root, config_path, config)
        print(json.dumps({"status": "PASS_STATIC_ONLY", "semantic_probes": result["semantic_probes"]}, sort_keys=True)); return 0
    return build(root, config_path, config)


if __name__ == "__main__":
    raise SystemExit(main())
