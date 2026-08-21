#!/usr/bin/env python3
"""Read-only G-route asset audit; never executes a scientific screen."""

import argparse
import hashlib
import json
import math
import os
import platform
import socket
from pathlib import Path


EXP_ID = "DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1"
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

    seal = evidence_docs.get("p1_readiness_seal", {})
    summary = evidence_docs.get("p1_slurm_summary", {})
    expected = config["expected"]
    expected_statuses = expected["anchor_statuses"]
    semantic_checks = {
        "seal_readiness_blocked": seal.get("readiness") == expected["readiness"],
        "summary_readiness_blocked": summary.get("p1_readiness_status") == expected["readiness"],
        "seal_anchor_statuses_exact": seal.get("anchor_statuses") == expected_statuses,
        "summary_anchor_statuses_exact": summary.get("anchor_statuses") == expected_statuses,
        "anchor_count_exact": summary.get("anchor_count") == expected["anchor_count"],
        "all_five_prov_invalid": seal.get("all_five_prov_valid") is False and summary.get("all_five_prov_valid") is False,
        "next_stage_unauthorized": seal.get("next_stage_authorized") is False and summary.get("next_stage_authorized") is False,
        "no_scientific_execution": summary.get("scientific_execution_performed") is False
    }
    current_block_reproduced = integrity_ok and all(semantic_checks.values())
    status = STATUS if current_block_reproduced else "INVALID_RUN"
    semantic_success = current_block_reproduced
    block_codes = config["required_block_codes"] if current_block_reproduced else ["G_ASSET_STATE_MISSING_OR_CHANGED_REVIEW_REQUIRED"]
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
            "anchor_count": float(expected["anchor_count"]),
            "valid_anchor_count": float(sum(value != "PROV_RUN_RECORD_MISSING" for value in seal.get("anchor_statuses", {}).values())),
            "missing_run_record_count": float(sum(value == "PROV_RUN_RECORD_MISSING" for value in seal.get("anchor_statuses", {}).values())),
            "next_stage_authorized": float(bool(seal.get("next_stage_authorized"))),
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
        "verdict": "G route cannot start a scientific transfer/decay screen",
        "current_block_reproduced": current_block_reproduced,
        "block_codes": block_codes,
        "missing_anchor_run_records": sorted(expected_statuses),
        "semantic_checks": semantic_checks,
        "scientific_execution_performed": False,
        "claim_eligible": False,
        "forbidden_scope": "Mash acquisition/execution, panel or cube build, checkpoint evaluation, FATS/PAS fitting, model training, or scientific claim",
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
