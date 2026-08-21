#!/usr/bin/env python3
"""Slurm-only atomic orchestrator for the Rice T1 information-sufficiency audit."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import re
from pathlib import Path

from common import atomic_write_json, atomic_write_text, read_json, require_hash, sha256_file
from runtime_hashes import assert_same_reviewed_runtime, verify_reviewed_runtime


EXP_ID = "FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def require_slurm_job_id() -> str:
    job_id = os.environ.get("SLURM_JOB_ID", "")
    if not job_id.isdigit() or int(job_id) <= 0:
        raise RuntimeError("positive numeric SLURM_JOB_ID required before any asset read or command")
    return job_id


def run_checked(name: str, argv: list[str], timeout: int, commands: list[dict[str, object]]) -> None:
    started = time.monotonic()
    record: dict[str, object] = {"name": name, "argv": argv, "timeout_seconds": timeout}
    commands.append(record)
    try:
        completed = subprocess.run(argv, check=True, timeout=timeout)
        record.update({"returncode": completed.returncode, "timed_out": False, "elapsed_seconds": time.monotonic() - started})
    except subprocess.TimeoutExpired:
        record.update({"returncode": None, "timed_out": True, "elapsed_seconds": time.monotonic() - started})
        raise
    except subprocess.CalledProcessError as exc:
        record.update({"returncode": exc.returncode, "timed_out": False, "elapsed_seconds": time.monotonic() - started})
        raise


def verify_owner(root: Path, token: str) -> None:
    token_path = root / "outputs" / EXP_ID / ".owner.lock" / "token"
    if not token or not token_path.is_file() or token_path.read_text(encoding="utf-8").strip() != token:
        raise RuntimeError("experiment owner token mismatch")


def record_wrapper_failure(root: Path, job_id: str, token: str, wrapper_exit_code: int) -> bool:
    """Only the live owner may replace its own RUNNING state; terminal runner state wins."""
    verify_owner(root, token)
    output = root / "outputs" / EXP_ID
    state_path = output / "CURRENT_STATE.json"
    if not state_path.is_file():
        return False
    state = read_json(state_path)
    if state.get("attempt_id") != f"slurm-{job_id}" or state.get("status") != "RUNNING":
        return False
    failure = {
        "schema_version": "FRAG-COLLINEARITY-WRAPPER-FAILURE-1.0.0",
        "attempt_id": f"slurm-{job_id}", "status": "FAILED_WRAPPER",
        "wrapper_exit_code": wrapper_exit_code, "recorded_at": now(), "owner_token_sha256": hashlib.sha256(token.encode()).hexdigest(),
    }
    atomic_write_json(output / "wrapper_failures" / f"slurm-{job_id}.json", failure)
    atomic_write_json(state_path, failure)
    atomic_write_text(output / "STATUS", "FAILED_WRAPPER\n")
    return True


def validate_runtime_resources(config: dict, environ: dict[str, str]) -> None:
    resources = config["resources"]
    expected = {
        "SLURM_CPUS_PER_TASK": str(resources["cpus"]),
        "SLURM_JOB_PARTITION": str(resources["partition"]),
        "SLURM_MEM_PER_NODE": str(int(resources["memory_gib"]) * 1024),
    }
    for key, value in expected.items():
        if environ.get(key) != value:
            raise RuntimeError(f"runtime resource mismatch: {key} expected {value}, observed {environ.get(key)!r}")
    if int(resources["gpus"]) != 0:
        raise RuntimeError("this experiment contract requires exactly zero GPUs")
    for key in ("SLURM_GPUS", "SLURM_GPUS_ON_NODE", "SLURM_GPUS_PER_TASK"):
        observed = environ.get(key, "").strip()
        if observed and observed != "0":
            raise RuntimeError(f"runtime GPU resource present: {key}={observed}")
    cuda_visible = environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if cuda_visible not in ("", "NoDevFiles"):
        raise RuntimeError(f"CUDA_VISIBLE_DEVICES must be empty for zero-GPU audit, observed {cuda_visible!r}")


def parse_slurm_duration(value: str) -> int:
    match = re.fullmatch(r"(?:(\d+)-)?(\d+):(\d{2}):(\d{2})", value)
    if not match:
        raise RuntimeError(f"unparseable Slurm duration: {value!r}")
    days, hours, minutes, seconds = match.groups()
    if int(minutes) >= 60 or int(seconds) >= 60:
        raise RuntimeError(f"invalid Slurm duration: {value!r}")
    return int(days or 0) * 86400 + int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def validate_runtime_walltime(snapshot_path: Path, expected_seconds: int) -> None:
    if not snapshot_path.is_file():
        raise RuntimeError("job-scoped scheduler snapshot is missing")
    text = snapshot_path.read_text(encoding="utf-8")
    matches = re.findall(r"(?:^|\s)TimeLimit=(\S+)", text)
    if len(matches) != 1:
        raise RuntimeError("scheduler snapshot must contain exactly one TimeLimit field")
    observed = parse_slurm_duration(matches[0])
    if observed != expected_seconds:
        raise RuntimeError(f"Slurm walltime mismatch: expected {expected_seconds}s, observed {observed}s")


def build_manifest(root: Path, stage: Path, environment_snapshot: Path, preflight_receipt: Path, scheduler_snapshot: Path, runtime_prehash: Path, config_path: Path) -> dict:
    files = []
    for path in sorted(value for value in stage.rglob("*") if value.is_file()):
        files.append({"path": path.relative_to(stage).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    inputs = [
        {"role": "runtime_environment", "path": str(environment_snapshot.relative_to(root)), "bytes": environment_snapshot.stat().st_size, "sha256": sha256_file(environment_snapshot)},
        {"role": "pre_submit_gate_and_synthetic_tests", "path": str(preflight_receipt.relative_to(root)), "bytes": preflight_receipt.stat().st_size, "sha256": sha256_file(preflight_receipt)},
        {"role": "slurm_scheduler_snapshot", "path": str(scheduler_snapshot.relative_to(root)), "bytes": scheduler_snapshot.stat().st_size, "sha256": sha256_file(scheduler_snapshot)},
        {"role": "reviewed_runtime_pre_hashes", "path": str(runtime_prehash.relative_to(root)), "bytes": runtime_prehash.stat().st_size, "sha256": sha256_file(runtime_prehash)},
    ]
    for path in [config_path] + [root / value for value in read_json(config_path)["runtime_code_files"]]:
        inputs.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"schema_version": "FRAG-COLLINEARITY-PAYLOAD-MANIFEST-1.0.0", "files": files, "runtime_inputs": inputs}


def redacted_argv(argv: list[str]) -> list[str]:
    result = list(argv)
    if "--owner-token" in result:
        index = result.index("--owner-token") + 1
        if index < len(result):
            result[index] = "<REDACTED_OWNER_TOKEN>"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--environment-snapshot", type=Path)
    parser.add_argument("--preflight-receipt", type=Path)
    parser.add_argument("--scheduler-snapshot", type=Path)
    parser.add_argument("--runtime-prehash", type=Path)
    parser.add_argument("--owner-token", required=True)
    parser.add_argument("--record-wrapper-failure", action="store_true")
    parser.add_argument("--wrapper-exit-code", type=int)
    args = parser.parse_args()
    job_id = require_slurm_job_id()
    root = args.root.resolve()
    if args.record_wrapper_failure:
        if args.wrapper_exit_code is None:
            raise RuntimeError("--wrapper-exit-code is required in wrapper-failure mode")
        record_wrapper_failure(root, job_id, args.owner_token, args.wrapper_exit_code)
        return 0
    if any(value is None for value in (args.config, args.environment_snapshot, args.preflight_receipt, args.scheduler_snapshot, args.runtime_prehash)):
        raise RuntimeError("config, environment, preflight, scheduler, and runtime-prehash inputs are required for audit mode")
    verify_owner(root, args.owner_token)
    config_path = args.config.resolve()
    config = read_json(config_path)
    if config.get("exp_id") != EXP_ID:
        raise RuntimeError("config exp_id mismatch")
    budget = config["resources"]
    if int(budget["preflight_command_timeout_seconds"]) + int(budget["preflight_kill_after_seconds"]) > int(budget["preflight_budget_seconds"]):
        raise RuntimeError("machine-bounded preflight exceeds its 300-second budget")
    if int(budget["payload_timeout_seconds"]) + int(budget["kill_after_seconds"]) + int(budget["preflight_budget_seconds"]) + int(budget["required_publish_headroom_seconds"]) > int(budget["walltime_seconds"]):
        raise RuntimeError("runtime budget lacks required publish headroom")
    if not args.runtime_prehash.is_file():
        raise RuntimeError("reviewed runtime pre-hash manifest is missing")
    reviewed_pre = read_json(args.runtime_prehash)
    reviewed_now = verify_reviewed_runtime(root, config_path, EXP_ID)
    assert_same_reviewed_runtime(reviewed_pre, reviewed_now)
    validate_runtime_resources(config, os.environ)
    validate_runtime_walltime(args.scheduler_snapshot, int(budget["walltime_seconds"]))
    require_hash(root, config["runtime_contract"]["pre_submit_gate"])

    output = root / "outputs" / EXP_ID
    attempts = output / "attempts"
    attempt_id = f"slurm-{job_id}"
    final_attempt = attempts / attempt_id
    if final_attempt.exists():
        raise RuntimeError(f"attempt already exists: {attempt_id}")
    stage = output / f".{attempt_id}.stage.{os.getpid()}"
    stage.mkdir(parents=True, exist_ok=False)
    # Persist the verified pre-hash before any scientific input access so both
    # successful and failed attempt namespaces retain the reviewed baseline.
    atomic_write_json(stage / "REVIEWED_RUNTIME_PRE.json", reviewed_pre)
    prior_state = None
    if (output / "CURRENT_STATE.json").is_file():
        prior_state = read_json(output / "CURRENT_STATE.json")
    atomic_write_json(output / "CURRENT_STATE.json", {"attempt_id": attempt_id, "status": "RUNNING", "updated_at": now(), "prior_state": prior_state})
    if (output / "STATUS").is_file() or (output / "metrics.json").is_file():
        archive = output / "history" / f"before-{attempt_id}"
        archive.mkdir(parents=True, exist_ok=False)
        for name in ("STATUS", "metrics.json"):
            if (output / name).is_file():
                os.replace(output / name, archive / name)
    commands: list[dict[str, object]] = []
    try:
        assembly = require_hash(root, config["inputs"]["assembly"])
        annotation = require_hash(root, config["inputs"]["positive_segments"])
        consensus = require_hash(root, config["inputs"]["consensus_library"])
        if not args.environment_snapshot.is_file():
            raise FileNotFoundError(args.environment_snapshot)
        if not args.preflight_receipt.is_file():
            raise FileNotFoundError(args.preflight_receipt)
        script_dir = root / "scripts" / "experiments" / EXP_ID
        py = sys.executable
        timeout = int(budget["payload_timeout_seconds"])
        atomic_write_json(stage / "INPUT_MANIFEST.json", {
            "schema_version": "FRAG-COLLINEARITY-INPUT-MANIFEST-1.0.0",
            "assets": [
                {"role": "assembly", "path": str(assembly.relative_to(root)), "bytes": assembly.stat().st_size, "sha256": sha256_file(assembly)},
                {"role": "positive_segments", "path": str(annotation.relative_to(root)), "bytes": annotation.stat().st_size, "sha256": sha256_file(annotation), "truth_tier": "T1", "unlabelled_space_is_negative": False},
                {"role": "consensus_library", "path": str(consensus.relative_to(root)), "bytes": consensus.stat().st_size, "sha256": sha256_file(consensus)},
            ],
        })
        run_checked("build_sample", [py, str(script_dir / "build_sample.py"), "--config", str(config_path), "--annotation", str(annotation), "--assembly", str(assembly), "--out-dir", str(stage / "sample")], timeout, commands)
        run_checked("map_consensus_evidence", [py, str(script_dir / "map_consensus_evidence.py"), "--config", str(config_path), "--leaves-fasta", str(stage / "sample/public/leaves.fa"), "--consensus-fasta", str(consensus), "--out", str(stage / "sequence_evidence.tsv")], timeout, commands)
        for kind, seed in [("CONSENSUS_COLLINEARITY", None), ("EVIDENCE_SHUFFLE_NULL", int(config["controls"]["evidence_shuffle_null"]["seed"]))]:
            argv = [py, str(script_dir / "partition_collinearity.py"), "--config", str(config_path), "--public-leaves", str(stage / "sample/public/leaves.tsv"), "--evidence", str(stage / "sequence_evidence.tsv"), "--parents-out", str(stage / f"{kind}.parents.tsv"), "--assignments-out", str(stage / f"{kind}.assignments.tsv"), "--partition-kind", kind]
            if seed is not None:
                argv.extend(["--shuffle-seed", str(seed)])
            run_checked(f"partition_{kind.lower()}", argv, timeout, commands)
        run_checked("evaluate_t1", [py, str(script_dir / "evaluate_t1.py"), "--config", str(config_path), "--public-leaves", str(stage / "sample/public/leaves.tsv"), "--truth", str(stage / "sample/evaluator_only/truth.tsv"), "--evidence", str(stage / "sequence_evidence.tsv"), "--candidate-parents", str(stage / "CONSENSUS_COLLINEARITY.parents.tsv"), "--null-parents", str(stage / "EVIDENCE_SHUFFLE_NULL.parents.tsv"), "--out-dir", str(stage)], timeout, commands)
        atomic_write_json(stage / "COMMAND_MANIFEST.json", {"schema_version": "FRAG-COLLINEARITY-COMMAND-MANIFEST-1.0.0", "commands": commands})
        metrics = read_json(stage / "metrics.json")
        atomic_write_json(stage / "RUN_MANIFEST.json", {
            "schema_version": "FRAG-COLLINEARITY-RUN-MANIFEST-1.0.0", "exp_id": EXP_ID,
            "attempt_id": attempt_id, "slurm_job_id": job_id, "started_under_slurm": True,
            "config_sha256": sha256_file(config_path), "environment_snapshot_path": str(args.environment_snapshot.relative_to(root)),
            "environment_snapshot_sha256": sha256_file(args.environment_snapshot), "terminal_status": metrics["terminal_status"],
            "preflight_receipt_path": str(args.preflight_receipt.relative_to(root)), "preflight_receipt_sha256": sha256_file(args.preflight_receipt),
            "scheduler_snapshot_path": str(args.scheduler_snapshot.relative_to(root)), "scheduler_snapshot_sha256": sha256_file(args.scheduler_snapshot),
            "reviewed_runtime_prehash_path": str(args.runtime_prehash.relative_to(root)), "reviewed_runtime_prehash_sha256": sha256_file(args.runtime_prehash),
            "runner_argv": redacted_argv(sys.argv),
        })
        reviewed_post = verify_reviewed_runtime(root, config_path, EXP_ID)
        assert_same_reviewed_runtime(reviewed_pre, reviewed_post)
        atomic_write_json(stage / "REVIEWED_RUNTIME_POST.json", reviewed_post)
        atomic_write_json(stage / "PAYLOAD_MANIFEST.json", build_manifest(root, stage, args.environment_snapshot, args.preflight_receipt, args.scheduler_snapshot, args.runtime_prehash, config_path))
        final_reviewed_post = verify_reviewed_runtime(root, config_path, EXP_ID)
        assert_same_reviewed_runtime(reviewed_pre, final_reviewed_post)
        if final_reviewed_post != reviewed_post:
            raise RuntimeError("reviewed runtime changed after payload manifest construction")
        final_attempt.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage, final_attempt)
        latest_tmp = output / f".latest.tmp.{os.getpid()}"
        latest_tmp.symlink_to(final_attempt.relative_to(output))
        os.replace(latest_tmp, output / "latest")
        shutil.copy2(final_attempt / "metrics.json", output / ".metrics.tmp")
        os.replace(output / ".metrics.tmp", output / "metrics.json")
        atomic_write_json(output / "CURRENT_STATE.json", {"attempt_id": attempt_id, "status": metrics["terminal_status"], "updated_at": now(), "metrics_sha256": sha256_file(output / "metrics.json")})
        atomic_write_text(output / "STATUS", metrics["terminal_status"] + "\n")
        return 0
    except Exception as exc:
        if stage.exists():
            atomic_write_json(stage / "COMMAND_MANIFEST.json", {"schema_version": "FRAG-COLLINEARITY-COMMAND-MANIFEST-1.0.0", "commands": commands})
        atomic_write_json(stage / "failure.json", {"schema_version": "FRAG-COLLINEARITY-FAILURE-1.0.0", "attempt_id": attempt_id, "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(), "failed_at": now()})
        attempts.mkdir(parents=True, exist_ok=True)
        failed = attempts / f"{attempt_id}-failed"
        if not failed.exists():
            os.replace(stage, failed)
        atomic_write_json(output / "CURRENT_STATE.json", {"attempt_id": attempt_id, "status": "FAILED", "updated_at": now(), "failure_path": str(failed.relative_to(root))})
        atomic_write_text(output / "STATUS", "FAILED\n")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
