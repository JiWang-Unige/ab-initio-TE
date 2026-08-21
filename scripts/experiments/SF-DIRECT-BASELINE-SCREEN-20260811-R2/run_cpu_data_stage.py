#!/usr/bin/env python3
"""Zero-GPU staged data/test/leakage job with atomic PASS promotion."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from run_direct_screen import finalize_terminal_state


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(value, encoding="utf-8")
    os.replace(tmp, path)


def atomic_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def safe_attempt_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
        raise ValueError("attempt_id must match [A-Za-z0-9_.-]{1,80}")
    return value


def create_stage(attempts_root: Path, prefix: str, attempt_id: str) -> tuple[Path, Path]:
    staging = attempts_root / f"{prefix}-{safe_attempt_id(attempt_id)}.tmp"
    final = attempts_root / f"{prefix}-{attempt_id}"
    if staging.exists() or final.exists():
        raise FileExistsError(f"refusing dirty/stale attempt path: {staging} or {final}")
    staging.mkdir(parents=True)
    return staging, final


def package_files(root: Path, exp: str) -> list[Path]:
    d = root / "scripts/experiments" / exp
    return [root / "configs" / f"{exp}.yaml", d / "direct_s0_data.py", d / "direct_s0_task.py", d / "run_cpu_data_stage.py",
            d / "run_direct_screen.py", d / "preflight_sbatch.py", d / "test_direct_s0.py", d / "FROZEN_ASSET_CONTRACT_V1.json", d / "FROZEN_SPECIES_HOLDOUT_V1.tsv",
            root / "sbatch" / f"{exp}.data.sbatch", root / "sbatch" / f"{exp}.sbatch"]


def tree_hashes(base: Path) -> dict[str, str]:
    return {str(path.relative_to(base)): sha256_file(path) for path in sorted(base.rglob("*")) if path.is_file() and path.name != "PASS_MANIFEST.json"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--contract-check-only", action="store_true")
    parser.add_argument("--external-env-manifest", type=Path)
    args = parser.parse_args()
    config = args.config.resolve()
    cfg = json.loads(config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    exp, out = cfg["exp_id"], root / cfg["output_root"]
    scripts = root / "scripts/experiments" / exp
    files = package_files(root, exp)
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
    static = {"schema_version": "TEFM-SF-DIRECT-STATIC-1.0.0", "config_sha256": sha256_file(config),
              "package_hashes": {str(x.relative_to(root)): sha256_file(x) for x in files},
              "goal_sha256": sha256_file(root / cfg["goal_contract"]), "protocol_sha256": sha256_file(root / cfg["protocol"])}
    if static["goal_sha256"] != cfg["goal_contract_sha256"] or static["protocol_sha256"] != cfg["protocol_sha256"]:
        raise ValueError("goal/protocol identity mismatch")
    atomic_json(out / "input_manifest.json", static)
    atomic_json(out / "static_contract.json", static)
    if args.contract_check_only:
        finalize_terminal_state(root, cfg, "IMPLEMENTED_NOT_RUN", "static-contract-check",
                                reason="scientific screen not executed")
        print(json.dumps({"status": "IMPLEMENTED_NOT_RUN", "package_files": len(files)}, sort_keys=True))
        return
    staging = final = None
    atomic_text(out / "STATUS", "DATA_RUNNING\n")
    try:
        staging, final = create_stage(root / cfg["attempts_root"], "data", args.attempt_id)
        if args.external_env_manifest is None or not args.external_env_manifest.is_file():
            raise ValueError("CPU stage requires the sbatch-generated environment manifest")
        shutil.copyfile(args.external_env_manifest, staging / "external_environment_manifest.txt")
        test_command = [sys.executable, str(scripts / "test_direct_s0.py"), "-v"]
        build_command = [sys.executable, str(scripts / "direct_s0_data.py"), "build", "--config", str(config), "--attempt-dir", str(staging)]
        verify_command = [sys.executable, str(scripts / "direct_s0_data.py"), "verify", "--config", str(config), "--attempt-dir", str(staging),
                          "--output", str(staging / "leakage_audit.json")]
        test = subprocess.run(test_command, text=True, capture_output=True)
        test_report = {"command": test_command, "returncode": test.returncode,
                       "stdout": test.stdout, "stderr": test.stderr, "pass": test.returncode == 0}
        atomic_json(staging / "cpu_test_report.json", test_report)
        if test.returncode:
            raise RuntimeError("CPU synthetic/schema test suite failed")
        subprocess.run(build_command, check=True)
        subprocess.run(verify_command, check=True)
        audit = json.loads((staging / "leakage_audit.json").read_text(encoding="utf-8"))
        if not audit["pass"] or audit["audit_in_numeric_gate"]:
            raise ValueError("CPU data audit is not a frozen PASS")
        pass_manifest = {"schema_version": "TEFM-SF-DIRECT-DATA-PASS-1.0.0", "status": "PASS", "exp_id": exp,
                         "attempt_id": args.attempt_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                         "runner_command": sys.argv, "payload_commands": [test_command, build_command, verify_command],
                         "attempt_relpath": str(final.relative_to(root)), "config_sha256": sha256_file(config),
                         "package_hashes": static["package_hashes"], "goal_sha256": static["goal_sha256"], "protocol_sha256": static["protocol_sha256"],
                         "files": tree_hashes(staging), "leakage_audit_pass": True, "cpu_tests_pass": True,
                         "homology_component_overlap_count": audit["homology_component_overlap_count"],
                         "primary_clade_overlap_count": audit["primary_clade_overlap_count"], "audit_physically_separate": True,
                         "audit_in_numeric_gate": False}
        atomic_json(staging / "PASS_MANIFEST.json", pass_manifest)
        os.replace(staging, final)
        manifest_sha = sha256_file(final / "PASS_MANIFEST.json")
        pointer = {"schema_version": "TEFM-SF-DIRECT-DATA-POINTER-1.0.0", "status": "PASS", "exp_id": exp,
                   "attempt_id": args.attempt_id, "attempt_relpath": str(final.relative_to(root)), "pass_manifest_sha256": manifest_sha}
        atomic_json(root / cfg["data_pass_pointer"], pointer)
        finalize_terminal_state(root, cfg, "DATA_READY", args.attempt_id)
        print(json.dumps({"status": "DATA_READY", "attempt": str(final), "pass_manifest_sha256": manifest_sha}, sort_keys=True))
    except Exception as exc:
        failure_root = staging if staging is not None and staging.exists() else final if final is not None and final.exists() else out
        failure = failure_root / f"failure.{args.attempt_id}.json" if failure_root == out else failure_root / "failure.json"
        atomic_json(failure, {"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        typed = failure_root / "typed_block.json"
        state = "DATA_TYPED_BLOCK" if typed.is_file() else "DATA_FAILED"
        extras = (failure, typed) if typed.is_file() else (failure,)
        finalize_terminal_state(root, cfg, state, args.attempt_id, extras, str(exc))
        raise


if __name__ == "__main__":
    main()
