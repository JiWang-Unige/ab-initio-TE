#!/usr/bin/env python3
"""Read-only F-route asset audit; never executes a scientific screen."""

import argparse
import hashlib
import json
import math
import os
import platform
import socket
from pathlib import Path


EXP_ID = "FRAG-PARENT-LATTICE-SCREEN-20260811-R1"
STATUS = "FOUNDATIONAL_TYPED_BLOCK"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--config", type=Path, default=Path("configs") / f"{EXP_ID}.yaml")
    args = parser.parse_args()
    root = args.project_root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    output_dir = root / "outputs" / EXP_ID
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "STATUS").write_text("RUNNING\n")

    observations = []
    evidence_docs = {}
    integrity_ok = True
    for item in config["evidence"]:
        path = root / item["path"]
        exists = path.is_file()
        observed = sha256(path) if exists else None
        matched = exists and observed == item["sha256"]
        integrity_ok = integrity_ok and matched
        observations.append({**item, "exists": exists, "observed_sha256": observed, "hash_match": matched})
        if exists and path.suffix == ".json":
            evidence_docs[item["id"]] = load_json(path)

    expected = config["expected"]
    semantic_checks = {
        "a0_blocked": evidence_docs.get("a0_identity_lock", {}).get("status") == expected["a0_status"],
        "a2_synthetic_only_pass": evidence_docs.get("a2_synthetic_t0", {}).get("status") == expected["a2_status"],
        "a3_evaluator_pass": evidence_docs.get("a3_evaluator", {}).get("status") == expected["a3_status"],
        "a4_real_t0_blocked": evidence_docs.get("a4_real_t0", {}).get("status") == expected["a4_status"],
        "a5_comparators_blocked": evidence_docs.get("a5_comparator", {}).get("status") == expected["a5_status"],
        "a5_exact_blocked_set": sorted(evidence_docs.get("a5_comparator", {}).get("blocked_comparators", []))
        == sorted(expected["blocked_comparators"]),
        "a6_not_ready": evidence_docs.get("a6_readiness", {}).get("status") == expected["a6_status"],
        "a6_no_scientific_authorization": evidence_docs.get("a6_readiness", {}).get("scientific_run_authorized") is False,
    }
    current_block_reproduced = integrity_ok and all(semantic_checks.values())
    status = STATUS if current_block_reproduced else "INVALID_RUN"
    semantic_success = current_block_reproduced
    block_codes = config["required_block_codes"] if current_block_reproduced else ["F_ASSET_STATE_MISSING_OR_CHANGED_REVIEW_REQUIRED"]

    metrics = {
        "schema_version": "metrics-v1",
        "exp_id": EXP_ID,
        "profile": "smoke",
        "requested_profile": "screen",
        "primary_metric_name": "asset_gate_pass",
        "primary_metric": 0.0,
        "semantic_success": semantic_success,
        "metrics": {
            "asset_gate_pass": 0.0,
            "evidence_integrity_pass": float(integrity_ok),
            "current_block_reproduced": float(current_block_reproduced),
            "a0_pass": float(not semantic_checks["a0_blocked"]),
            "a2_semantics_pass": float(semantic_checks["a2_synthetic_only_pass"]),
            "a3_evaluator_pass": float(semantic_checks["a3_evaluator_pass"]),
            "a4_pass": float(not semantic_checks["a4_real_t0_blocked"]),
            "a5_pass": float(not semantic_checks["a5_comparators_blocked"]),
            "a6_pass": float(not semantic_checks["a6_not_ready"]),
            "blocked_comparator_count": float(len(expected["blocked_comparators"])) if semantic_checks["a5_exact_blocked_set"] else 0.0,
            "real_t0_candidate_count": 0.0 if semantic_checks["a4_real_t0_blocked"] else -1.0,
            "scientific_execution_performed": 0.0
        },
        "finite_metrics": True,
        "claim_eligible": False,
        "scientific_screen_executed": False,
        "dataset": {"name": "frozen asset-gate evidence", "version": "sha256_manifest", "split": "not_applicable_pre_scientific_gate"},
        "evaluator": {"path": str(Path(__file__).resolve()), "version": "TEFM-ASSET-GATE-1.1.0", "type": "deterministic_asset_gate"},
        "status": status
    }
    assert all(math.isfinite(float(value)) for value in metrics["metrics"].values())
    report = {
        "schema_version": "asset-gate-report-v1",
        "exp_id": EXP_ID,
        "status": status,
        "verdict": "F route cannot start a biological scientific screen",
        "current_block_reproduced": current_block_reproduced,
        "block_codes": block_codes,
        "semantic_checks": semantic_checks,
        "scientific_execution_performed": False,
        "claim_eligible": False,
        "allowed_scope": "synthetic mechanism/evaluator validation only",
        "forbidden_scope": "biological screen, whole-genome precision claim, or silent postprocessor selection",
        "observations": observations
    }
    environment = {
        "schema_version": "environment-manifest-v1",
        "exp_id": EXP_ID,
        "execution_mode": "asset_gate_only",
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "cwd": str(Path.cwd()),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "scientific_dependencies_required": []
    }
    config_record = {"id": "config", "path": str(config_path.relative_to(root)), "sha256": sha256(config_path),
                     "exists": True, "observed_sha256": sha256(config_path), "hash_match": True}
    script_path = Path(__file__).resolve()
    script_record = {"id": "verifier", "path": str(script_path.relative_to(root)), "sha256": sha256(script_path),
                     "exists": True, "observed_sha256": sha256(script_path), "hash_match": True}
    manifest_rows = [config_record, script_record] + observations
    dump_json(output_dir / "metrics.json", metrics)
    dump_json(output_dir / "verifier_report.json", report)
    dump_json(output_dir / "environment_manifest.json", environment)
    (output_dir / "STATUS").write_text(status + "\n")
    with (output_dir / "input_manifest.tsv").open("w", encoding="utf-8") as handle:
        handle.write("id\tpath\texpected_sha256\tobserved_sha256\thash_match\n")
        for row in manifest_rows:
            handle.write(f"{row['id']}\t{row['path']}\t{row['sha256']}\t{row['observed_sha256'] or ''}\t{str(row['hash_match']).lower()}\n")
    outputs = ["STATUS", "environment_manifest.json", "input_manifest.tsv", "metrics.json", "verifier_report.json"]
    with (output_dir / "output_manifest.tsv").open("w", encoding="utf-8") as handle:
        handle.write("path\tsha256\n")
        for name in outputs:
            handle.write(f"{name}\t{sha256(output_dir / name)}\n")
    return 2 if semantic_success else 3


if __name__ == "__main__":
    raise SystemExit(main())
