#!/usr/bin/env python3
"""Fail-closed asset verifier only; it cannot execute a scientific screen."""

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def nested(value, dotted):
    for key in dotted.split("."):
        value = value[key]
    return value


def evaluate(root, assertion):
    path = root / assertion["path"]
    kind = assertion["kind"]
    observed = None
    passed = False
    try:
        if kind == "json_equals":
            observed = nested(json.loads(path.read_text(encoding="utf-8")), assertion["key"])
            passed = observed == assertion["expected"]
        elif kind == "tsv_has_columns":
            with path.open(encoding="utf-8", newline="") as handle:
                columns = next(csv.reader(handle, delimiter="\t"))
            missing = sorted(set(assertion["columns"]) - set(columns))
            observed = {"columns": columns, "missing": missing}
            passed = not missing
        elif kind == "text_excludes_all":
            text = path.read_text(encoding="utf-8")
            found = [needle for needle in assertion["needles"] if needle in text]
            observed = {"forbidden_text_found": found}
            passed = not found
        elif kind == "jsonl_records_have_fields":
            opener = gzip.open if path.suffix == ".gz" else open
            records = 0
            incomplete = 0
            missing_counts = {field: 0 for field in assertion["fields"]}
            with opener(path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    records += 1
                    row_missing = False
                    for field in assertion["fields"]:
                        if field not in row or row[field] in (None, ""):
                            missing_counts[field] += 1
                            row_missing = True
                    incomplete += int(row_missing)
            observed = {"records": records, "incomplete_records": incomplete, "missing_field_counts": missing_counts}
            passed = records == assertion["expected_records"] and incomplete == 0
        else:
            raise ValueError(f"unsupported assertion kind: {kind}")
    except Exception as exc:  # fail closed on malformed or missing evidence
        observed = {"error": f"{type(exc).__name__}: {exc}"}
        passed = False
    return {"id": assertion["id"], "kind": kind, "passed": passed, "observed": observed, "blocker": assertion["blocker"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "STATUS").write_text("RUNNING\n", encoding="utf-8")

    script_path = Path(__file__).resolve()
    implementation_path = Path(globals().get("_ASSET_GATE_IMPLEMENTATION", __file__)).resolve()
    evidence_rows = []
    evidence_ok = True
    for item in config["evidence"]:
        path = root / item["path"]
        exists = path.is_file()
        digest = sha256(path) if exists else None
        identity_ok = exists and digest == item["sha256"]
        evidence_ok &= identity_ok
        evidence_rows.append({**item, "exists": exists, "bytes": path.stat().st_size if exists else 0, "observed_sha256": digest, "identity_ok": identity_ok})

    checks = [evaluate(root, item) for item in config["required_gate_assertions"]]
    identity_blockers = [f"evidence identity mismatch: {item['id']}" for item in evidence_rows if not item["identity_ok"]]
    blockers = identity_blockers + [item["blocker"] for item in checks if not item["passed"]]
    gate_pass = evidence_ok and not blockers
    semantic_success = evidence_ok and bool(blockers) and not gate_pass
    status = config["terminal_status_on_failed_gate"] if semantic_success else "INVALID_RUN"
    if gate_pass:
        blockers = ["asset gate unexpectedly passed; this verifier cannot authorize or execute the scientific screen"]

    generated = datetime.now(timezone.utc).isoformat()
    atomic_json(output / "input_manifest.json", {
        "schema_version": "TEFM-ASSET-GATE-INPUT-MANIFEST-1.0.0",
        "exp_id": config["exp_id"],
        "generated_at_utc": generated,
        "config": {"path": str(config_path), "sha256": sha256(config_path)},
        "verifier_launcher": {"path": str(script_path), "sha256": sha256(script_path)},
        "verifier_implementation": {"path": str(implementation_path), "sha256": sha256(implementation_path)},
        "evidence": evidence_rows,
        "all_evidence_identities_match": evidence_ok,
    })
    atomic_json(output / "environment_manifest.json", {
        "schema_version": "TEFM-ASSET-GATE-ENVIRONMENT-1.0.0",
        "exp_id": config["exp_id"],
        "generated_at_utc": generated,
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "hostname": platform.node(),
        "cwd": str(Path.cwd()),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "logical_project_root": config["project_root"],
        "physical_project_root": str(root),
        "scientific_dependencies_loaded": [],
        "gpu_requested": False,
    })
    atomic_json(output / "asset_gate_report.json", {
        "schema_version": "TEFM-FAIL-CLOSED-ASSET-GATE-1.0.0",
        "exp_id": config["exp_id"],
        "route": config["route"],
        "generated_at_utc": generated,
        "semantic_success": semantic_success,
        "asset_gate_pass": gate_pass,
        "status": status,
        "scientific_screen_executed": False,
        "claim_eligible": False,
        "evidence_identity_ok": evidence_ok,
        "checks": checks,
        "blockers": blockers,
    })
    metrics = {
        "schema_version": "TEFM-TYPED-BLOCK-METRICS-1.0.0",
        "exp_id": config["exp_id"],
        "profile": "smoke",
        "requested_profile": config["profile"],
        "status": status,
        "primary_metric": 0.0,
        "asset_gate_pass": 0.0,
        "evidence_identity_ok": float(evidence_ok),
        "required_gate_checks": float(len(checks)),
        "passed_gate_checks": float(sum(item["passed"] for item in checks)),
        "blocker_count": float(len(blockers)),
        "scientific_screen_executed": 0.0,
        "claim_eligible": False,
        "semantic_success": semantic_success,
        "metrics": {
            "asset_gate_pass": 0.0,
            "evidence_identity_ok": float(evidence_ok),
            "required_gate_checks": float(len(checks)),
            "passed_gate_checks": float(sum(item["passed"] for item in checks)),
            "blocker_count": float(len(blockers)),
            "scientific_screen_executed": 0.0
        },
        "dataset": {"name": "frozen asset-gate evidence", "version": "sha256_manifest", "split": "not_applicable_pre_scientific_gate"},
        "evaluator": {"path": str(script_path), "version": "TEFM-ASSET-GATE-1.1.0", "type": "deterministic_asset_gate"},
    }
    if not all(math.isfinite(value) for key, value in metrics.items() if isinstance(value, float)):
        raise RuntimeError("non-finite metric")
    atomic_json(output / "metrics.json", metrics)
    (output / "STATUS").write_text(status + "\n", encoding="utf-8")

    manifest_lines = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "output_manifest.sha256":
            manifest_lines.append(f"{sha256(path)}  {path.name}")
    (output / "output_manifest.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(json.dumps({"exp_id": config["exp_id"], "status": status, "blockers": len(blockers)}, sort_keys=True))
    return 2 if semantic_success else 3


if __name__ == "__main__":
    raise SystemExit(main())
