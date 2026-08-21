#!/usr/bin/env python3
"""Run one offline, hash-pinned HiTE 3.3.3 validity cell."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

EXP_ID = "BENCH-HITE-ISOLATED-20260811-R1"
CELL = "hite"
FIELDS = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]
IDENTITY_RE = re.compile(r"^#+\s+HiTE, version 3\.3\.3\s+#+\s*$", re.MULTILINE)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atom(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}.{uuid.uuid4().hex}")
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


class StopRuleError(RuntimeError):
    """A durable timeout stop sentinel forbids another asset/container attempt."""


class CaughtTermination(RuntimeError):
    """A catchable scheduler termination was converted to a typed failure."""


def require_numeric_slurm_job_id(environment: dict[str, str] | os._Environ[str] = os.environ) -> str:
    job_id = environment.get("SLURM_JOB_ID", "")
    if not re.fullmatch(r"[1-9][0-9]*", job_id):
        raise RuntimeError("numeric SLURM_JOB_ID is required before any asset or container action")
    return job_id


def ensure_retry_allowed(stop_path: Path) -> None:
    """Read the sentinel before hashing assets or constructing/executing a container command."""
    if not stop_path.exists():
        return
    try:
        sentinel = json.loads(stop_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StopRuleError(f"STOP sentinel is unparseable; fail closed: {exc}") from exc
    if (sentinel.get("exp_id") != EXP_ID or sentinel.get("stop_rule_triggered") is not True
            or sentinel.get("further_retry_allowed") is not False):
        raise StopRuleError("STOP sentinel has invalid schema/state; fail closed")
    raise StopRuleError("durable HiTE timeout STOP sentinel forbids further retry")


def pre_asset_guards(stop_path: Path, environment: dict[str, str] | os._Environ[str] = os.environ) -> str:
    job_id = require_numeric_slurm_job_id(environment)
    ensure_retry_allowed(stop_path)
    return job_id


def fasta_bp(path: Path) -> int:
    return sum(len(line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith(">"))


class RuntimeBudget:
    def __init__(self, spec: dict[str, int], limits: dict[str, int]) -> None:
        self.spec = spec
        calculated = limits["identity"] + limits["minimum_input"]
        if calculated != spec["command_timeout_sum_seconds"]:
            raise ValueError("command timeout sum mismatch")
        accounted = (calculated + spec["max_command_count"] * limits["kill_after"]
                     + spec["preflight_hash_budget_seconds"]
                     + spec["required_post_command_headroom_seconds"])
        if accounted > spec["walltime_seconds"]:
            raise ValueError("runtime budget exceeds walltime")
        if spec["required_post_command_headroom_seconds"] < 600:
            raise ValueError("less than 600 seconds post-command headroom")
        self.accounted_seconds = accounted
        self.started = time.monotonic()
        self.commands_started = 0

    def command_limit(self, requested: int) -> int:
        if self.commands_started >= self.spec["max_command_count"]:
            raise RuntimeError("command-count budget exhausted")
        elapsed = time.monotonic() - self.started
        slots = self.spec["max_command_count"] - self.commands_started
        reserve = (self.spec["required_post_command_headroom_seconds"]
                   + slots * self.spec["kill_after_seconds"])
        available = int(self.spec["walltime_seconds"] - elapsed - reserve)
        if available < 1:
            raise RuntimeError("walltime budget exhausted while preserving publish headroom")
        self.commands_started += 1
        return min(requested, available)

    def snapshot(self) -> dict[str, Any]:
        elapsed = time.monotonic() - self.started
        return {**self.spec, "accounted_seconds": self.accounted_seconds,
                "commands_started": self.commands_started, "elapsed_seconds": elapsed,
                "remaining_walltime_seconds": max(0.0, self.spec["walltime_seconds"] - elapsed)}


def bounded_command(name: str, argv: list[str], directory: Path, requested: int,
                    budget: RuntimeBudget) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    out, err, timing = (directory / f"{name}.{suffix}" for suffix in ("out", "err", "time"))
    limit = budget.command_limit(requested)
    kill_after = int(budget.spec.get("kill_after_seconds", 10))
    with out.open("wb") as stdout, err.open("wb") as stderr:
        proc = subprocess.run(["/usr/bin/time", "-v", "-o", str(timing), "timeout", "--signal=TERM",
                               f"--kill-after={kill_after}", str(limit), *argv],
                              stdout=stdout, stderr=stderr, check=False)
    timing_text = timing.read_text(errors="replace") if timing.is_file() else ""
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", timing_text)
    return {"name": name, "argv": argv, "argv_shell_escaped": shlex.join(argv),
            "exit_code": proc.returncode, "timed_out": proc.returncode in {124, 137},
            "configured_timeout_seconds": requested, "effective_timeout_seconds": limit,
            "kill_after_seconds": kill_after, "stdout": str(out), "stderr": str(err),
            "time": str(timing), "peak_rss_kb": int(rss.group(1)) if rss else None}


def cexec_direct(sif: Path, work: Path, guest_argv: list[str]) -> list[str]:
    offline = [
        "HOME=/work/home", "TMPDIR=/work/tmp", "http_proxy=http://127.0.0.1:9",
        "https_proxy=http://127.0.0.1:9", "ftp_proxy=http://127.0.0.1:9",
        "all_proxy=socks5://127.0.0.1:9", "HTTP_PROXY=http://127.0.0.1:9",
        "HTTPS_PROXY=http://127.0.0.1:9", "FTP_PROXY=http://127.0.0.1:9",
        "ALL_PROXY=socks5://127.0.0.1:9", "NO_PROXY=localhost,127.0.0.1",
        "no_proxy=localhost,127.0.0.1",
    ]
    return ["apptainer", "exec", "--cleanenv", "--bind", f"{work}:/work", str(sif),
            "env", *offline, *guest_argv]


def strict_identity(command: dict[str, Any]) -> bool:
    if command.get("exit_code") != 0 or command.get("timed_out") is not False:
        return False
    path = Path(command["stdout"])
    return path.is_file() and bool(IDENTITY_RE.search(path.read_text(encoding="utf-8", errors="replace")))


def observed_identity(command: dict[str, Any]) -> dict[str, Any]:
    path = Path(command["stdout"])
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    return {"stdout_path": str(path), "stdout_sha256": sha(path) if path.is_file() else None,
            "actual_banner_lines": [x.strip() for x in text.splitlines() if "version" in x.lower()][:20]}


def _pin(root: Path, item: dict[str, str], role: str) -> tuple[Path, dict[str, Any]]:
    path = (root / item["path"]).resolve()
    actual = sha(path) if path.is_file() else None
    return path, {"role": role, "path": str(path), "expected_sha256": item["sha256"],
                  "actual_sha256": actual, "pass": actual == item["sha256"]}


def verify_hite_assets(root: Path, config: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    spec = config["hite"]
    rows: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for key in ("sif", "manifest", "help", "inspect", "fixture", "preparation_code",
                "preparation_environment", "adapter"):
        paths[key], rows[key] = _pin(root, spec[key], key)
    checks: dict[str, bool] = {f"pin_{k}": v["pass"] for k, v in rows.items()}
    manifest: dict[str, Any] = {}
    try:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        checks.update({
            "schema": manifest.get("schema_version") == "TEFM-HITE-OCI-2.0.0",
            "reference": manifest.get("reference") == spec["reference"],
            "source_commit": manifest.get("source_commit") == spec["source_commit"],
            "sif_hash": manifest.get("sha256") == spec["sif"]["sha256"],
            "help_hash": manifest.get("help_sha256") == spec["help"]["sha256"],
            "inspect_hash": manifest.get("inspect_sha256") == spec["inspect"]["sha256"],
            "environment_hash": manifest.get("environment_sha256") == spec["preparation_environment"]["sha256"],
            "preparation_code_hash": manifest.get("preparation_code_sha256") == spec["preparation_code"]["sha256"],
            "preparation_config_hash": manifest.get("config_sha256") == spec["preparation_parent_config_sha256"],
            "preparation_job": bool(str(manifest.get("preparation_slurm_job_id", "")).strip()),
            "manifest_sif_path": Path(manifest.get("sif", "")).resolve() == paths["sif"],
            "manifest_help_path": Path(manifest.get("help_path", "")).resolve() == paths["help"],
            "manifest_inspect_path": Path(manifest.get("inspect_path", "")).resolve() == paths["inspect"],
            "manifest_environment_path": Path(manifest.get("environment_path", "")).resolve() == paths["preparation_environment"],
            "fixture_minimum_bp": paths["fixture"].is_file() and fasta_bp(paths["fixture"]) >= spec["fixture"]["minimum_bp"],
            "direct_argv_exact": spec["direct_argv"] == ["python", "/HiTE/main.py", "--genome", "/work/input/hite.fa", "--thread", "2", "--annotate", "1", "--out_dir", "/work/hite"],
        })
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        checks["manifest_parse"] = False
        manifest = {"error": f"{type(exc).__name__}: {exc}"}
    evidence = {"pass": all(checks.values()), "checks": checks, "pins": rows,
                "manifest_schema": manifest.get("schema_version"),
                "resolved": {key: str(value) for key, value in paths.items()}}
    return bool(evidence["pass"]), evidence


def _find_artifact(artifacts: list[dict[str, Any]], path: str, digest: str) -> bool:
    matches = [row for row in artifacts if row.get("path") == path]
    return len(matches) == 1 and matches[0].get("sha256") == digest


def verify_parent_rm_evidence(root: Path, config: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    spec = config["parent_rm_evidence"]
    pins: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for key in ("aggregate_status", "aggregate_metrics", "rm_cell_result", "hite_cell_result", "artifact_manifest",
                "command_manifest", "input_manifest", "config", "runner"):
        paths[key], pins[key] = _pin(root, spec[key], key)
    checks = {f"pin_{k}": v["pass"] for k, v in pins.items()}
    try:
        status = paths["aggregate_status"].read_text(encoding="utf-8").strip()
        metrics = json.loads(paths["aggregate_metrics"].read_text(encoding="utf-8"))
        result = json.loads(paths["rm_cell_result"].read_text(encoding="utf-8"))
        hite_result = json.loads(paths["hite_cell_result"].read_text(encoding="utf-8"))
        artifacts = json.loads(paths["artifact_manifest"].read_text(encoding="utf-8"))["artifacts"]
        commands = json.loads(paths["command_manifest"].read_text(encoding="utf-8"))["cell_commands"]
        inputs = json.loads(paths["input_manifest"].read_text(encoding="utf-8"))
        parent_config = json.loads(paths["config"].read_text(encoding="utf-8"))
        adapter = result.get("adapter", {})
        hite_commands = hite_result.get("commands", [])
        parent_timeout = hite_commands[1] if len(hite_commands) == 2 else {}
        checks.update({
            "parent_id": parent_config.get("exp_id") == spec["exp_id"] == inputs.get("exp_id"),
            "job_id": spec["slurm_job_id"] in str(paths["rm_cell_result"]),
            "aggregate_failed": status == spec["aggregate_status"]["expected_text"] == "FAILED",
            "aggregate_semantic_false": metrics.get("semantic_success") is False and metrics.get("repair_goal_success") is False,
            "rm_cell_pass": result.get("status") == "ENGINEERING_PASS",
            "rm_identity": result.get("identity", {}).get("satisfied") is True,
            "rm_adapter": adapter.get("attempted") is True and adapter.get("pass") is True and int(adapter.get("rows", 0)) > 0,
            "command_mapping": commands.get("repeatmodeler2_repeatmasker") == result.get("commands"),
            "hite_command_mapping": commands.get("hite") == hite_commands,
            "parent_hite_invalid": hite_result.get("status") == "INVALID_RUN",
            "parent_hite_help_pass": len(hite_commands) == 2 and hite_commands[0].get("name") == "hite_help_identity"
                                     and hite_commands[0].get("exit_code") == 0
                                     and hite_commands[0].get("timed_out") is False,
            "parent_hite_timeout_600": parent_timeout.get("name") == "hite_min"
                                       and parent_timeout.get("configured_timeout_seconds") == 600
                                       and parent_timeout.get("effective_timeout_seconds") == 600
                                       and parent_timeout.get("exit_code") == 124
                                       and parent_timeout.get("timed_out") is True,
            "parent_cells_exact": inputs.get("approved_cell_keys") == ["repeatmodeler2_repeatmasker", "hite"],
            "config_input_hash": any(row.get("path") == str(paths["config"]) and row.get("sha256") == spec["config"]["sha256"] for row in inputs.get("new_namespace_hashes", [])),
            "result_artifact_mapping": _find_artifact(artifacts, str(paths["rm_cell_result"]), spec["rm_cell_result"]["sha256"]),
            "hite_result_artifact_mapping": _find_artifact(artifacts, str(paths["hite_cell_result"]), spec["hite_cell_result"]["sha256"]),
            "adapter_artifact_mapping": _find_artifact(artifacts, adapter.get("output", ""), adapter.get("sha256", "")),
            "source_artifact_mapping": _find_artifact(artifacts, adapter.get("source", ""), sha(Path(adapter["source"])) if Path(adapter.get("source", "x")).is_file() else ""),
            "input_artifact_mapping": _find_artifact(artifacts, str(paths["input_manifest"]), spec["input_manifest"]["sha256"]),
        })
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        checks["parent_evidence_parse"] = False
        pins["parse_error"] = {"error": f"{type(exc).__name__}: {exc}"}
    timeout_evidence = {"path": str(paths.get("hite_cell_result", "")),
                        "sha256": spec["hite_cell_result"]["sha256"],
                        "configured_timeout_seconds": 600, "effective_timeout_seconds": 600,
                        "exit_code": 124, "timed_out": True}
    evidence = {"pass": all(checks.values()), "checks": checks, "pins": pins,
                "parent_hite_timeout_evidence": timeout_evidence,
                "reuse_mode": "cross_run_hash_reconciliation", "parent_aggregate_status": "FAILED"}
    return bool(evidence["pass"]), evidence


def load_adapter(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("hite_pinned_adapter", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pinned adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adapt_final_gff(adapter: ModuleType, gff: Path, output: Path) -> dict[str, Any]:
    evidence: dict[str, Any] = {"attempted": True, "pass": False, "source": str(gff), "output": str(output)}
    try:
        if not gff.is_file() or gff.stat().st_size == 0:
            raise ValueError("exact final HiTE.gff is absent or empty")
        rows = int(adapter.convert(gff, output, "gff"))
        with output.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if reader.fieldnames != FIELDS:
                raise ValueError("canonical header mismatch")
            parsed = list(reader)
        if rows <= 0 or len(parsed) != rows:
            raise ValueError("canonical row count mismatch or empty")
        for row in parsed:
            start, end = int(row["start"]), int(row["end"])
            if not row["seqid"] or start < 0 or end <= start or row["strand"] not in {"+", "-", ".", "?"}:
                raise ValueError("invalid canonical row")
        evidence.update({"pass": True, "rows": rows, "source_sha256": sha(gff), "sha256": sha(output)})
    except Exception as exc:  # adapter failures are deliberately typed INVALID_RUN
        evidence["reason"] = f"{type(exc).__name__}: {exc}"
    return evidence


def persist_timeout_stop(stop_path: Path, job_id: str, parent_evidence: dict[str, Any],
                         command: dict[str, Any]) -> dict[str, Any]:
    current = {key: command.get(key) for key in (
        "name", "exit_code", "timed_out", "configured_timeout_seconds",
        "effective_timeout_seconds", "kill_after_seconds", "stdout", "stderr", "time")}
    for role in ("stdout", "stderr", "time"):
        path = Path(str(command.get(role, "")))
        current[f"{role}_sha256"] = sha(path) if path.is_file() else None
    sentinel = {
        "schema_version": "TEFM-HITE-TIMEOUT-STOP-1.0.0", "exp_id": EXP_ID,
        "slurm_job_id": job_id, "created_unix": time.time(),
        "stop_rule_triggered": True, "further_retry_allowed": False,
        "reason": "isolated 1800s retry timed out after the pinned parent 600s timeout",
        "parent_timeout_evidence": parent_evidence.get("parent_hite_timeout_evidence"),
        "current_timeout_evidence": current,
    }
    atom(stop_path, sentinel)
    return sentinel


def run_hite_cell(config: dict[str, Any], asset_evidence: dict[str, Any], parent_evidence: dict[str, Any],
                  attempt: Path, budget: RuntimeBudget, stop_path: Path, slurm_job_id: str,
                  command_runner=bounded_command, adapter_module: ModuleType | None = None) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    base = {"cell_key": CELL, "commands": commands, "blockers": [],
            "identity": {"satisfied": False}, "adapter": {"attempted": False, "pass": False}}
    if not asset_evidence.get("pass") or not parent_evidence.get("pass"):
        base.update({"status": "INVALID_RUN", "blockers": ["immutable asset or parent RM evidence hash contract failed"]})
        return base
    root = Path(config["project_root"]).resolve()
    work, logs = attempt / "work", attempt / "logs" / CELL
    for directory in (work / "input", work / "hite", work / "home", work / "tmp"):
        directory.mkdir(parents=True, exist_ok=True)
    fixture = root / config["hite"]["fixture"]["path"]
    shutil.copyfile(fixture, work / "input" / "hite.fa")
    sif = root / config["hite"]["sif"]["path"]
    help_command = command_runner("hite_help_identity", cexec_direct(sif, work, ["python", "/HiTE/main.py", "-h"]),
                                  logs, config["timeouts_seconds"]["identity"], budget)
    commands.append(help_command)
    base["identity"] = {"satisfied": strict_identity(help_command), "observed": observed_identity(help_command)}
    if not base["identity"]["satisfied"]:
        base.update({"status": "INVALID_RUN", "blockers": ["HiTE help identity failed/nonzero/timed out/mismatched"]})
        return base
    minimum = command_runner("hite_min", cexec_direct(sif, work, config["hite"]["direct_argv"]), logs,
                             config["timeouts_seconds"]["minimum_input"], budget)
    commands.append(minimum)
    if minimum.get("exit_code") != 0 or minimum.get("timed_out") is not False:
        if minimum.get("timed_out") is True:
            stop = persist_timeout_stop(stop_path, slurm_job_id, parent_evidence, minimum)
            base.update({"stop_rule_triggered": True, "further_retry_allowed": False,
                         "stop_sentinel": {"path": str(stop_path), "sha256": sha(stop_path),
                                           "schema_version": stop["schema_version"]}})
        base.update({"status": "INVALID_RUN", "blockers": ["executed HiTE minimum command failed or timed out"]})
        return base
    try:
        adapter_module = adapter_module or load_adapter(root / config["hite"]["adapter"]["path"])
        adapter_result = adapt_final_gff(adapter_module, work / "hite" / "HiTE.gff", work / "hite.canonical.tsv")
    except Exception as exc:
        adapter_result = {"attempted": True, "pass": False,
                          "reason": f"{type(exc).__name__}: {exc}"}
    base["adapter"] = adapter_result
    if not adapter_result["pass"]:
        base.update({"status": "INVALID_RUN", "blockers": ["exact final HiTE.gff/adapter contract failed"]})
        return base
    base.update({"status": "ENGINEERING_PASS", "minimum_input": {"pass": True}, "blockers": []})
    return base


def acquire_lock(lock: Path, token: str, stale_seconds: int, current_job_id: str,
                 squeue_runner=subprocess.run, now_fn=time.time) -> None:
    lock.parent.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r"[1-9][0-9]*", current_job_id):
        raise RuntimeError("current lock owner must be a numeric Slurm job id")
    now = float(now_fn())
    if not math.isfinite(now):
        raise RuntimeError("current time is non-finite; fail closed")
    payload = {"token": token, "job_id": current_job_id, "pid": os.getpid(), "created": now}
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream)
        return
    except FileExistsError:
        pass
    try:
        owner = json.loads(lock.read_text(encoding="utf-8"))
        owner_job = str(owner["job_id"])
        created = float(owner["created"])
    except Exception as exc:
        raise RuntimeError(f"unparseable lock; fail closed: {exc}") from exc
    if not re.fullmatch(r"[1-9][0-9]*", owner_job):
        raise RuntimeError("non-numeric lock owner; fail closed")
    if not math.isfinite(created) or created <= 0 or created > now:
        raise RuntimeError("lock created timestamp is non-finite/non-positive/future; fail closed")
    try:
        query = squeue_runner(["squeue", "-h", "-j", owner_job, "-o", "%A"],
                              text=True, capture_output=True, check=False)
    except OSError as exc:
        raise RuntimeError(f"squeue unavailable; fail closed: {exc}") from exc
    if query.returncode != 0:
        raise RuntimeError("squeue failed; lock state unknown and fail closed")
    if query.stderr != "":
        raise RuntimeError("squeue wrote stderr; lock state unknown and fail closed")
    if query.stdout not in {"", owner_job, owner_job + "\n"}:
        raise RuntimeError("squeue output must be exactly the owner job id or empty")
    if query.stdout.strip() == owner_job or now - created <= stale_seconds:
        raise RuntimeError("active or not-yet-stale lock")
    archived = lock.with_name(lock.name + f".stale.{int(now)}.{uuid.uuid4().hex}")
    os.replace(lock, archived)
    acquire_lock(lock, token, stale_seconds, current_job_id, squeue_runner=squeue_runner, now_fn=now_fn)


def release_lock(lock: Path, token: str) -> None:
    try:
        if json.loads(lock.read_text(encoding="utf-8")).get("token") == token:
            lock.unlink()
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return


def artifact_manifest(attempt: Path, cell: dict[str, Any], input_manifest: Path,
                      extra_paths: list[Path] | None = None) -> dict[str, Any]:
    selected = [input_manifest, attempt / "cells" / CELL / "result.json", attempt / "runtime_budget.json"]
    for command in cell["commands"]:
        selected.extend(Path(command[key]) for key in ("stdout", "stderr", "time"))
    if cell.get("adapter", {}).get("pass"):
        selected.extend([Path(cell["adapter"]["source"]), Path(cell["adapter"]["output"])])
    selected.extend(extra_paths or [])
    expected = sorted(str(path.resolve()) for path in set(selected))
    rows = [{"path": path, "sha256": sha(Path(path))} for path in expected if Path(path).is_file()]
    return {"schema_version": "TEFM-HITE-ISOLATED-ARTIFACTS-1.0.0",
            "expected_paths": expected, "artifacts": rows, "exact_row_count": len(expected)}


def artifact_manifest_closed(manifest: dict[str, Any]) -> bool:
    rows = manifest.get("artifacts")
    expected = manifest.get("expected_paths")
    if (not isinstance(rows, list) or not isinstance(expected, list) or
            manifest.get("exact_row_count") != len(expected) or not rows):
        return False
    paths = [row.get("path") for row in rows]
    if len(paths) != len(set(paths)) or paths != expected:
        return False
    return all(isinstance(path, str) and Path(path).is_file()
               and row.get("sha256") == sha(Path(path)) for path, row in zip(paths, rows))


CANONICAL_NAMES = (
    "metrics.json", "semantic_success.json", "command_manifest.json", "reconciliation.json",
    "latest_attempt.json", "failure.json", "artifact_manifest.json", "canonical_manifest.json",
)


def begin_run(output: Path, job_id: str) -> Path:
    """Atomically leave the old terminal state before archiving every old canonical result."""
    prior_status = (output / "STATUS").read_text(encoding="utf-8") if (output / "STATUS").is_file() else None
    atom(output / "STATUS", "RUNNING\n")
    archive = output / "archive" / f"pre-run-{job_id}-{int(time.time())}-{uuid.uuid4().hex}"
    if prior_status is not None:
        atom(archive / "STATUS", prior_status)
    for name in CANONICAL_NAMES:
        target = output / name
        if target.exists():
            archive.mkdir(parents=True, exist_ok=True)
            os.replace(target, archive / name)
    return archive


def runtime_environment_evidence(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise RuntimeError("runtime environment snapshot is missing or empty")
    return {"role": "runtime_environment", "path": str(resolved), "sha256": sha(resolved),
            "size_bytes": resolved.stat().st_size}


def stage_canonical_bundle(attempt: Path, output: Path, payloads: dict[str, Any],
                           environment: dict[str, Any]) -> tuple[dict[str, Path], dict[str, Any]]:
    required = {"metrics.json", "semantic_success.json", "command_manifest.json",
                "reconciliation.json", "latest_attempt.json"}
    if not required.issubset(payloads) or not set(payloads).issubset(set(CANONICAL_NAMES)):
        raise RuntimeError("canonical payload namespace mismatch")
    stage = attempt / "canonical_stage"
    staged: dict[str, Path] = {}
    for name, payload in payloads.items():
        path = stage / name
        atom(path, payload)
        staged[name] = path
    environment_stage = stage / "runtime_environment.snapshot"
    environment_tmp = environment_stage.with_name(environment_stage.name + f".tmp.{uuid.uuid4().hex}")
    shutil.copyfile(Path(environment["path"]), environment_tmp)
    os.replace(environment_tmp, environment_stage)
    if sha(environment_stage) != environment["sha256"]:
        raise RuntimeError("runtime environment staging hash mismatch")
    rows = [{"name": name, "staged_path": str(path.resolve()),
             "canonical_path": str((output / name).resolve()), "sha256": sha(path)}
            for name, path in sorted(staged.items())]
    environment_closure = {**environment, "staged_path": str(environment_stage.resolve()),
                           "canonical_path": environment["path"]}
    manifest = {"schema_version": "TEFM-HITE-CANONICAL-BUNDLE-1.0.0", "exp_id": EXP_ID,
                "required_payload_names": sorted(payloads), "payloads": rows,
                "runtime_environment": environment_closure, "exact_payload_count": len(rows)}
    if not canonical_bundle_closed(manifest):
        raise RuntimeError("staged canonical bundle failed hash closure")
    manifest_path = stage / "canonical_manifest.json"
    atom(manifest_path, manifest)
    staged["canonical_manifest.json"] = manifest_path
    return staged, manifest


def canonical_bundle_closed(manifest: dict[str, Any]) -> bool:
    rows = manifest.get("payloads")
    names = manifest.get("required_payload_names")
    environment = manifest.get("runtime_environment", {})
    if (not isinstance(rows, list) or not isinstance(names, list) or
            manifest.get("exact_payload_count") != len(rows) or
            [row.get("name") for row in rows] != names or len(names) != len(set(names))):
        return False
    env_stage = Path(str(environment.get("staged_path", "")))
    env_canonical = Path(str(environment.get("canonical_path", "")))
    if (environment.get("role") != "runtime_environment"
            or not env_stage.is_file() or not env_canonical.is_file()
            or environment.get("sha256") != sha(env_stage)
            or environment.get("sha256") != sha(env_canonical)):
        return False
    for row in rows:
        staged = Path(str(row.get("staged_path", "")))
        canonical = Path(str(row.get("canonical_path", "")))
        existing = [path for path in (staged, canonical) if path.is_file()]
        if not existing or any(row.get("sha256") != sha(path) for path in existing):
            return False
    return True


def publish_staged(output: Path, staged: dict[str, Path], manifest: dict[str, Any], status: str) -> None:
    expected = {row["name"]: row["sha256"] for row in manifest["payloads"]}
    expected["canonical_manifest.json"] = sha(staged["canonical_manifest.json"])
    for name, path in staged.items():
        expected.setdefault(name, sha(path))
    for name, path in staged.items():
        os.replace(path, output / name)
    for name, digest in expected.items():
        target = output / name
        if not target.is_file() or sha(target) != digest:
            raise RuntimeError(f"canonical publish hash mismatch: {name}")
    atom(output / "STATUS", status + "\n")


def fallback_environment_snapshot(attempt: Path, requested: Path, reason: str) -> dict[str, Any]:
    path = attempt / "runtime_environment_fallback.json"
    atom(path, {"reason": reason, "requested_path": str(requested), "python": sys.version,
                "platform": platform.platform(), "conda_prefix": os.environ.get("CONDA_PREFIX"),
                "slurm_job_id": os.environ.get("SLURM_JOB_ID")})
    return runtime_environment_evidence(path)


def finalize_attempt(output: Path, attempt: Path, input_manifest: Path, cell: dict[str, Any],
                     config: dict[str, Any], environment: dict[str, Any], assets_ok: bool,
                     parent_ok: bool, failure: dict[str, Any] | None = None) -> int:
    cell_path = attempt / "cells" / CELL / "result.json"
    atom(cell_path, cell)
    extra = [Path(environment["path"])]
    stop_path = output / "STOP.json"
    if stop_path.is_file():
        extra.append(stop_path)
    if failure is not None:
        failure_attempt = attempt / "failure.json"
        atom(failure_attempt, failure)
        extra.append(failure_attempt)
    manifest = artifact_manifest(attempt, cell, input_manifest, extra)
    manifest_closed = artifact_manifest_closed(manifest)
    if not manifest_closed:
        cell["status"] = "INVALID_RUN"
        cell.setdefault("blockers", []).append("artifact manifest closure failed")
        atom(cell_path, cell)
        manifest = artifact_manifest(attempt, cell, input_manifest, extra)
        manifest_closed = artifact_manifest_closed(manifest)
    semantic = (failure is None and assets_ok and parent_ok
                and cell.get("status") == "ENGINEERING_PASS" and manifest_closed)
    primary_name = config["primary_metric"]
    primary_value = int(cell.get("status") == "ENGINEERING_PASS")
    reconciliation = {"schema_version": "TEFM-HITE-RM-CROSS-RUN-1.0.0",
                      "parent_exp_id": config["parent_rm_evidence"]["exp_id"],
                      "parent_slurm_job_id": config["parent_rm_evidence"]["slurm_job_id"],
                      "parent_aggregate_status": "FAILED",
                      "parent_rm_status": "ENGINEERING_PASS_REUSED_BY_HASH" if parent_ok else "PARENT_EVIDENCE_INVALID",
                      "parent_hite_timeout_600_verified": parent_ok,
                      "isolated_hite_status": cell.get("status", "INVALID_RUN"),
                      "stop_rule_triggered": cell.get("stop_rule_triggered", False),
                      "further_retry_allowed": cell.get("further_retry_allowed", True),
                      "two_cell_evidence_ready": semantic, "single_successful_run": False,
                      "accuracy_claim": False, "claim_eligible": False}
    metrics = {"schema_version": "TEFM-HITE-ISOLATED-METRICS-1.0.0", "exp_id": EXP_ID,
               "primary_metric": primary_name, primary_name: primary_value,
               "expected_cell_keys": [CELL], "observed_cell_keys": [CELL], "missing_cell_keys": [],
               "unexpected_cell_keys": [], "semantic_success": semantic, "claim_eligible": False,
               "attempt": str(attempt), "artifact_manifest_closed": manifest_closed,
               "reconciliation_two_cell_evidence_ready": semantic}
    semantic_payload = {"exp_id": EXP_ID, "semantic_success": semantic,
                        "reason": "isolated HiTE pass plus byte-verified parent RM pass" if semantic
                                  else "isolated HiTE validity contract not satisfied",
                        "process_exit_code": 0 if semantic else 2}
    command_manifest = {"schema_version": "TEFM-HITE-ISOLATED-COMMANDS-1.0.0",
                        "attempt": str(attempt), "cell_commands": {CELL: cell.get("commands", [])}}
    payloads: dict[str, Any] = {
        "metrics.json": metrics, "semantic_success.json": semantic_payload,
        "command_manifest.json": command_manifest, "reconciliation.json": reconciliation,
        "latest_attempt.json": {"attempt": str(attempt), "status": "COMPLETED" if semantic else "FAILED"},
    }
    if failure is not None:
        payloads["failure.json"] = failure
    staged, canonical = stage_canonical_bundle(attempt, output, payloads, environment)
    artifact_path = attempt / "artifact_manifest.json"
    atom(artifact_path, manifest)
    artifact_stage = attempt / "canonical_stage" / "artifact_manifest.json"
    atom(artifact_stage, manifest)
    staged["artifact_manifest.json"] = artifact_stage
    atom(attempt / "canonical_manifest.json", canonical)
    publish_staged(output, staged, canonical, "COMPLETED" if semantic else "FAILED")
    return 0 if semantic else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--environment-snapshot", required=True)
    args = parser.parse_args()
    # This guard deliberately precedes config reads, asset hashes, squeue, and container construction.
    job_id = require_numeric_slurm_job_id()
    root = Path(args.root).resolve()
    config_path = Path(args.config).resolve()
    environment_path = Path(args.environment_snapshot).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("exp_id") != EXP_ID or config.get("expected_cell_keys") != [CELL]:
        raise SystemExit("isolated namespace/config mismatch")
    output = root / "outputs" / EXP_ID
    stop_path = (root / config["stop_policy"]["sentinel"]).resolve()
    token = uuid.uuid4().hex
    lock = output / ".run.lock"
    acquire_lock(lock, token, int(config["ownership"]["stale_lock_seconds"]), job_id)
    attempt = output / "attempts" / f"attempt-{job_id}"
    if attempt.exists():
        attempt = output / "attempts" / f"attempt-{job_id}-{int(time.time())}-{uuid.uuid4().hex}"
    attempt.mkdir(parents=True)
    old_handlers: dict[int, Any] = {}

    def caught_signal(signum: int, _frame: Any) -> None:
        raise CaughtTermination(f"caught signal {signum}")

    for signum in (signal.SIGTERM, signal.SIGINT):
        old_handlers[signum] = signal.signal(signum, caught_signal)
    environment: dict[str, Any] | None = None
    budget: RuntimeBudget | None = None
    input_manifest = attempt / "input_manifest.json"
    cell: dict[str, Any] = {"cell_key": CELL, "status": "INVALID_RUN", "commands": [],
                            "identity": {"satisfied": False},
                            "adapter": {"attempted": False, "pass": False}, "blockers": []}
    assets_ok = parent_ok = False
    try:
        begin_run(output, job_id)
        # STOP is read after ownership is acquired but before any runtime asset hash/container action.
        pre_asset_guards(stop_path)
        environment = runtime_environment_evidence(environment_path)
        budget_spec = dict(config["runtime_budget"])
        budget_spec["kill_after_seconds"] = config["timeouts_seconds"]["kill_after"]
        budget = RuntimeBudget(budget_spec, config["timeouts_seconds"])
        assets_ok, assets = verify_hite_assets(root, config)
        parent_ok, parent = verify_parent_rm_evidence(root, config)
        atom(input_manifest, {"schema_version": "TEFM-HITE-ISOLATED-INPUT-1.0.0", "exp_id": EXP_ID,
                              "expected_cell_keys": [CELL], "offline": True,
                              "config": {"path": str(config_path), "sha256": sha(config_path)},
                              "environment": {"python": sys.version, "platform": platform.platform(),
                                              "conda_prefix": os.environ.get("CONDA_PREFIX"),
                                              "slurm_job_id": job_id, "snapshot": environment},
                              "hite_assets": assets, "parent_rm_evidence": parent})
        cell = run_hite_cell(config, assets, parent, attempt, budget, stop_path, job_id)
        atom(attempt / "runtime_budget.json", budget.snapshot())
        return finalize_attempt(output, attempt, input_manifest, cell, config, environment,
                                assets_ok, parent_ok)
    except Exception as exc:
        failure = {"schema_version": "TEFM-HITE-ISOLATED-FAILURE-1.0.0", "exp_id": EXP_ID,
                   "slurm_job_id": job_id, "exception_type": type(exc).__name__, "message": str(exc),
                   "traceback": traceback.format_exc(), "stop_rule_rejection": isinstance(exc, StopRuleError)}
        cell["status"] = "INVALID_RUN"
        cell.setdefault("blockers", []).append(f"caught failure: {type(exc).__name__}: {exc}")
        if isinstance(exc, StopRuleError) and stop_path.is_file():
            cell.update({"stop_rule_triggered": True, "further_retry_allowed": False,
                         "stop_sentinel": {"path": str(stop_path), "sha256": sha(stop_path)}})
        if environment is None:
            environment = fallback_environment_snapshot(attempt, environment_path, str(exc))
        if not input_manifest.exists():
            atom(input_manifest, {"schema_version": "TEFM-HITE-ISOLATED-INPUT-1.0.0", "exp_id": EXP_ID,
                                  "expected_cell_keys": [CELL], "offline": True,
                                  "config": {"path": str(config_path), "sha256": sha(config_path)},
                                  "environment": {"slurm_job_id": job_id, "snapshot": environment},
                                  "pre_asset_failure": True})
        if not (attempt / "runtime_budget.json").exists():
            atom(attempt / "runtime_budget.json", budget.snapshot() if budget else
                 {"commands_started": 0, "failure_before_budget_initialization": True})
        return finalize_attempt(output, attempt, input_manifest, cell, config, environment,
                                assets_ok, parent_ok, failure=failure)
    finally:
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
        release_lock(lock, token)


if __name__ == "__main__":
    raise SystemExit(main())
