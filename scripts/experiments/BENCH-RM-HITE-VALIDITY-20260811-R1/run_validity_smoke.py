#!/usr/bin/env python3
"""Independent, offline validity smoke for the RM2/RM4 and HiTE cells only."""
from __future__ import annotations

import argparse
import atexit
import hashlib
import importlib.util
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


ALLOWED_CELL_KEYS = ("repeatmodeler2_repeatmasker", "hite")
TERMINAL = {"ENGINEERING_PASS", "FOUNDATIONAL_TYPED_BLOCK", "VERSION_MISMATCH", "INVALID_RUN"}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atom(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    if isinstance(payload, str):
        temporary.write_text(payload, encoding="utf-8")
    else:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class RuntimeBudget:
    """Enforce a global deadline while preserving publish and 15-minute headroom."""

    def __init__(self, spec: dict[str, int], timeouts: dict[str, int]) -> None:
        self.spec = spec
        expected_sum = 2 * timeouts["identity"] + 3 * timeouts["db_probe"] + 3 * timeouts["minimum_input"]
        if expected_sum != spec["command_timeout_sum_seconds"]:
            raise ValueError(f"command timeout sum mismatch: calculated={expected_sum}")
        accounted = (
            expected_sum
            + spec["max_command_count"] * spec["kill_after_seconds"]
            + spec["asset_hash_budget_seconds"]
            + spec["publish_budget_seconds"]
            + spec["required_headroom_seconds"]
        )
        if accounted > spec["walltime_seconds"]:
            raise ValueError(f"runtime budget exceeds walltime: accounted={accounted}")
        if spec["required_headroom_seconds"] < 900:
            raise ValueError("runtime budget must preserve at least 15 minutes of headroom")
        self.started_monotonic = time.monotonic()
        self.commands_started = 0

    def command_limit(self, requested_seconds: int) -> int:
        if self.commands_started >= self.spec["max_command_count"]:
            raise RuntimeError("runtime command count exceeds declared maximum")
        elapsed = time.monotonic() - self.started_monotonic
        remaining_slots = self.spec["max_command_count"] - self.commands_started
        reserve = (
            self.spec["publish_budget_seconds"]
            + self.spec["required_headroom_seconds"]
            + remaining_slots * self.spec["kill_after_seconds"]
        )
        available = int(self.spec["walltime_seconds"] - elapsed - reserve)
        if available < 1:
            raise RuntimeError("global runtime budget exhausted before command; publish/headroom preserved")
        self.commands_started += 1
        return min(int(requested_seconds), available)

    def snapshot(self) -> dict[str, Any]:
        elapsed = time.monotonic() - self.started_monotonic
        return {
            **self.spec,
            "commands_started": self.commands_started,
            "elapsed_seconds": elapsed,
            "remaining_walltime_seconds": max(0.0, self.spec["walltime_seconds"] - elapsed),
        }


def bounded_command(
    name: str,
    argv: list[str],
    directory: Path,
    requested_limit: int,
    budget: RuntimeBudget,
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    out, err, timing = directory / f"{name}.out", directory / f"{name}.err", directory / f"{name}.time"
    effective_limit = budget.command_limit(requested_limit)
    kill_after = int(budget.spec["kill_after_seconds"])
    with out.open("wb") as stdout_handle, err.open("wb") as stderr_handle:
        proc = subprocess.run(
            [
                "/usr/bin/time", "-v", "-o", str(timing),
                "timeout", "--signal=TERM", f"--kill-after={kill_after}", str(effective_limit), *argv,
            ],
            stdout=stdout_handle,
            stderr=stderr_handle,
            check=False,
        )
    timing_text = timing.read_text(errors="replace") if timing.is_file() else ""
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", timing_text)
    return {
        "name": name,
        "argv": argv,
        "argv_shell_escaped": shlex.join(argv),
        "exit_code": proc.returncode,
        "timed_out": proc.returncode in {124, 137},
        "configured_timeout_seconds": requested_limit,
        "effective_timeout_seconds": effective_limit,
        "kill_after_seconds": kill_after,
        "stdout": str(out),
        "stderr": str(err),
        "time": str(timing),
        "peak_rss_kb": int(match.group(1)) if match else None,
    }


def require_exact_cell_namespace(expected: list[str]) -> None:
    if expected != list(ALLOWED_CELL_KEYS) or len(expected) != len(set(expected)):
        raise ValueError(f"expected_cell_keys must be exactly {list(ALLOWED_CELL_KEYS)!r}")


def execute_selected_cells(
    expected: list[str], handlers: dict[str, Callable[[], dict[str, Any]]]
) -> dict[str, dict[str, Any]]:
    """Invoke exactly the two approved handlers; no dynamic/fallback tool dispatch."""
    require_exact_cell_namespace(expected)
    if set(handlers) != set(ALLOWED_CELL_KEYS):
        raise ValueError(f"handler namespace must be exactly {list(ALLOWED_CELL_KEYS)!r}")
    return {name: handlers[name]() for name in expected}


def verify_parent_contract(root: Path, config: dict[str, Any]) -> tuple[ModuleType, dict[str, Any], list[dict[str, str]]]:
    parent_spec = config["parent_contract"]
    if parent_spec["exp_id"] != "BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2":
        raise RuntimeError("unapproved parent experiment")
    verified: list[dict[str, str]] = []
    resolved: dict[str, Path] = {}
    for key in ("config", "runner", "adapter", "hite_preparation_code", "famdb_preparation_code"):
        item = parent_spec[key]
        path = (root / item["path"]).resolve()
        actual = sha(path) if path.is_file() else None
        if actual != item["sha256"]:
            raise RuntimeError(f"parent contract hash mismatch: {key}: expected={item['sha256']} actual={actual}")
        resolved[key] = path
        verified.append({"role": key, "path": str(path), "sha256": actual})
    parent_config = json.loads(resolved["config"].read_text(encoding="utf-8"))
    if parent_config.get("exp_id") != parent_spec["exp_id"]:
        raise RuntimeError("parent config exp_id mismatch")
    projections = (
        (config["fixture_inputs"]["repeatmodeler_repeatmasker"], parent_config["fixture_inputs"]["repeatmodeler_repeatmasker"], "RM fixture"),
        (config["fixture_inputs"]["hite"], parent_config["fixture_inputs"]["hite"], "HiTE fixture"),
        (config["asset_root"], parent_config["asset_root"], "asset_root"),
        (config["dfam40"], parent_config["dfam40"], "Dfam contract"),
        (config["components"]["repeatmodeler_2_0_9"], parent_config["components"]["repeatmodeler_2_0_9"], "RepeatModeler component"),
        (config["components"]["repeatmasker_4_2_4"], parent_config["components"]["repeatmasker_4_2_4"], "RepeatMasker component"),
        (config["exact_sources"]["hite"], parent_config["exact_sources"]["hite"], "HiTE source"),
        (config["license_evidence"]["repeatmodeler2_repeatmasker"], parent_config["license_evidence"]["repeatmodeler2_repeatmasker"], "RM license"),
        (config["license_evidence"]["hite"], parent_config["license_evidence"]["hite"], "HiTE license"),
    )
    for actual, expected, label in projections:
        if actual != expected:
            raise RuntimeError(f"new experiment diverges from hash-pinned parent {label}")
    module_spec = importlib.util.spec_from_file_location("tefm_b5_parent_contract", resolved["runner"])
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("cannot load hash-pinned parent runner")
    parent = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(parent)
    return parent, parent_config, verified


def verify_hite_manifest(
    root: Path, new_config: dict[str, Any], parent_config: dict[str, Any]
) -> tuple[bool, Path, Path, dict[str, Any]]:
    source = new_config["exact_sources"]["hite"]
    sif = root / source["local_sif"]
    manifest_path = sif.with_suffix(sif.suffix + ".manifest.json")
    evidence: dict[str, Any] = {"path": str(manifest_path), "pass": False}
    if not sif.is_file() or not manifest_path.is_file():
        evidence["reason"] = "immutable SIF or manifest absent"
        return False, sif, manifest_path, evidence
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        sif_actual_sha256 = sha(sif)
        manifest_actual_sha256 = sha(manifest_path)
        help_path = Path(manifest.get("help_path", ""))
        inspect_path = Path(manifest.get("inspect_path", ""))
        env_path = Path(manifest.get("environment_path", ""))
        prep_path = root / new_config["parent_contract"]["hite_preparation_code"]["path"]
        parent_config_path = root / new_config["parent_contract"]["config"]["path"]
        sif_pin = new_config["asset_pins"]["hite_sif"]
        manifest_pin = new_config["asset_pins"]["hite_manifest"]
        checks = {
            "schema": manifest.get("schema_version") == "TEFM-HITE-OCI-2.0.0",
            "reference": manifest.get("reference") == source["reference"],
            "sif_sha256": manifest.get("sha256") == sif_actual_sha256,
            "new_config_sif_pin": sif == (root / sif_pin["path"]).resolve() and sif_actual_sha256 == sif_pin["sha256"],
            "new_config_manifest_pin": manifest_path == (root / manifest_pin["path"]).resolve() and manifest_actual_sha256 == manifest_pin["sha256"],
            "source_commit": manifest.get("source_commit") == source["commit"],
            "help": help_path.is_file() and manifest.get("help_sha256") == (sha(help_path) if help_path.is_file() else None),
            "inspect": inspect_path.is_file() and manifest.get("inspect_sha256") == (sha(inspect_path) if inspect_path.is_file() else None),
            "preparation_job": bool(manifest.get("preparation_slurm_job_id")),
            "preparation_code": manifest.get("preparation_code_sha256") == sha(prep_path),
            "parent_config": manifest.get("config_sha256") == sha(parent_config_path),
            "environment": env_path.is_file() and manifest.get("environment_sha256") == (sha(env_path) if env_path.is_file() else None),
            "parent_projection": source == parent_config["exact_sources"]["hite"],
        }
        evidence.update({"checks": checks, "manifest_sha256": manifest_actual_sha256, "sif_sha256": sif_actual_sha256, "pass": all(checks.values())})
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        evidence["reason"] = f"manifest parse/validation failure: {type(exc).__name__}: {exc}"
    return bool(evidence["pass"]), sif, manifest_path, evidence


def command_identity_evidence(command: dict[str, Any]) -> dict[str, Any]:
    stdout_path = Path(command["stdout"])
    text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    banners = [line.strip() for line in text.splitlines() if re.search(r"(?:HiTE|version)", line, re.I)]
    return {
        "command_name": command.get("name"),
        "stdout_path": str(stdout_path),
        "stdout_sha256": sha(stdout_path) if stdout_path.is_file() else None,
        "actual_banner_lines": banners[:20],
    }


def not_attempted(reason: str) -> dict[str, Any]:
    return {"attempted": False, "pass": False, "reason": reason}


def hite_333_identity(command: dict[str, Any]) -> bool:
    """Require the exact official banner line, not an unrelated dependency version."""
    if command.get("exit_code") != 0 or command.get("timed_out") is not False:
        return False
    path = Path(command["stdout"])
    text = path.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(r"^#+\s+HiTE, version 3\.3\.3\s+#+\s*$", text, re.MULTILINE))


def run_hite_commands_strict(
    parent: ModuleType, sif: Path, work: Path, directory: Path, limits: dict[str, int], budget: RuntimeBudget
) -> list[dict[str, Any]]:
    help_result = bounded_command(
        "hite_help_identity",
        parent.cexec_direct(sif, work, ["python", "/HiTE/main.py", "-h"]),
        directory,
        limits["identity"],
        budget,
    )
    commands = [help_result]
    if not hite_333_identity(help_result):
        return commands
    commands.append(bounded_command(
        "hite_min",
        parent.cexec_direct(sif, work, [
            "python", "/HiTE/main.py", "--genome", "/work/input/hite.fa",
            "--thread", "2", "--annotate", "1", "--out_dir", "/work/hite",
        ]),
        directory,
        limits["minimum_input"],
        budget,
    ))
    return commands


def assert_hite_identity_stop(
    commands: list[dict[str, Any]], identity_ok: bool, adapter: dict[str, Any]
) -> None:
    """Prove that VERSION_MISMATCH stopped before minimum and adapter execution."""
    if len(commands) != 1:
        raise ValueError("HiTE identity stop requires exactly one command")
    item = commands[0]
    if item.get("name") != "hite_help_identity":
        raise ValueError("HiTE identity stop requires hite_help_identity")
    if item.get("exit_code") != 0 or item.get("timed_out") is not False:
        raise ValueError("HiTE identity stop requires successful, non-timeout help")
    if identity_ok:
        raise ValueError("HiTE identity stop requires an actual banner mismatch")
    if adapter.get("attempted") is not False:
        raise ValueError("HiTE identity stop must not attempt the adapter")
    if any(item.get("name") == "hite_min" for item in commands):
        raise ValueError("HiTE identity stop must not attempt minimum input")


def build_metrics(
    exp_id: str, expected: list[str], cells: dict[str, dict[str, Any]], attempt: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    require_exact_cell_namespace(expected)
    expected_set, observed_set = set(expected), set(cells)
    missing = sorted(expected_set - observed_set)
    unexpected = sorted(observed_set - expected_set)
    counts = {
        status: sum(cells[name].get("status") == status for name in expected_set if name in cells)
        for status in sorted(TERMINAL)
    }
    terminal_count = sum(counts.values())
    substitutions = sum(
        cells[name].get("status") == "ENGINEERING_PASS"
        and cells[name].get("identity", {}).get("satisfied") is not True
        for name in expected_set if name in cells
    )
    semantic_success = (
        not missing and not unexpected and terminal_count == len(expected)
        and counts["INVALID_RUN"] == 0 and substitutions == 0
    )
    engineering_pass_count = counts["ENGINEERING_PASS"]
    repair_goal_success = semantic_success and engineering_pass_count == len(expected)
    metrics = {
        "schema_version": "TEFM-BENCH-RM-HITE-VALIDITY-1.0.0",
        "exp_id": exp_id,
        "claim_eligible": False,
        "primary_metric": "engineering_pass_count",
        "expected_cell_count": len(expected),
        "expected_cell_keys": expected,
        "observed_cell_keys": sorted(cells),
        "missing_cell_keys": missing,
        "unexpected_cell_keys": unexpected,
        "terminal_cell_count": terminal_count,
        "engineering_pass_count": engineering_pass_count,
        "engineering_pass_fraction": engineering_pass_count / len(expected),
        "invalid_cell_fraction": counts["INVALID_RUN"] / len(expected),
        "silent_substitution_count": substitutions,
        "semantic_success": semantic_success,
        "repair_goal_success": repair_goal_success,
        "counts": counts,
        "attempt": str(attempt),
    }
    semantic = {
        "semantic_success": semantic_success,
        "repair_goal_success": repair_goal_success,
        "expected_cell_count": len(expected),
        "terminal_cell_count": terminal_count,
        "engineering_pass_count": engineering_pass_count,
        "missing_cell_keys": missing,
        "unexpected_cell_keys": unexpected,
        "invalid_cell_fraction": metrics["invalid_cell_fraction"],
        "silent_substitution_count": substitutions,
    }
    return metrics, semantic


def semantic_exit_code(semantic: dict[str, Any]) -> int:
    return 0 if semantic.get("semantic_success") is True else 2


def run_repeatmodeler_repeatmasker(
    parent: ModuleType,
    config: dict[str, Any],
    parent_config: dict[str, Any],
    root: Path,
    attempt: Path,
    work: Path,
    fixture: dict[str, Any],
    components: dict[str, dict[str, Any]],
    licenses: dict[str, dict[str, Any]],
    famdb: dict[str, Any],
    famdb_path: Path,
    budget: RuntimeBudget,
) -> dict[str, Any]:
    required = {"RepeatModeler": "2.0.9", "RepeatMasker": "4.2.4", "Dfam": "4.0"}
    prerequisite = all((
        fixture["pass"], components["repeatmasker_4_2_4"]["pass"],
        components["repeatmodeler_2_0_9"]["pass"], famdb["pass"],
        licenses["repeatmodeler2_repeatmasker"]["readable"],
    ))
    if not prerequisite:
        return parent.blocked("pre-execution immutable RM2/RM4/Dfam/fixture/license asset absent or mismatched", required)
    shutil.copy2(fixture["resolved"], work / "input" / "rm.fa")
    rm = Path(components["repeatmasker_4_2_4"]["resolved"])
    rm2 = Path(components["repeatmodeler_2_0_9"]["resolved"])
    limits = config["timeouts_seconds"]
    famdb_cli = "/usr/local/share/famdb-3.0.0/famdb.py -i /usr/local/share/famdb-3.0.0/Libraries/famdb"
    commands = [
        bounded_command("famdb_info", parent.cexec(rm, work, f"{famdb_cli} info", famdb_path), attempt / "logs/rm", limits["db_probe"], budget),
        bounded_command("famdb_family", parent.cexec(rm, work, f"{famdb_cli} family --format fasta_acc MIR3", famdb_path), attempt / "logs/rm", limits["db_probe"], budget),
        bounded_command("rm2_version", parent.cexec(rm2, work, "RepeatModeler -version", famdb_path), attempt / "logs/rm", limits["identity"], budget),
        bounded_command("rm2_famdb", parent.cexec(rm2, work, f"{famdb_cli} info", famdb_path), attempt / "logs/rm", limits["db_probe"], budget),
        bounded_command("rm2_min", parent.cexec(rm2, work, "cd /work/input && BuildDatabase -name r1db rm.fa && RepeatModeler -database r1db -threads 2", famdb_path), attempt / "logs/rm", limits["minimum_input"], budget),
        bounded_command("rm_min", parent.cexec(rm, work, "cd /work/input && RepeatMasker -pa 2 -nolow -gff -species 'Homo sapiens' rm.fa", famdb_path), attempt / "logs/rm", limits["minimum_input"], budget),
    ]
    adapter = parent.adapt(work / "input" / "rm.fa.out", "repeatmasker_out")
    identity_ok = (
        parent.exact(commands[0], r"Version\s*:\s*4\.0")
        and commands[1]["exit_code"] == 0
        and parent.exact(commands[2], r"2\.0\.9")
        and parent.exact(commands[3], r"Version\s*:\s*4\.0")
        and parent.repeatmasker_424_identity(commands[5])
    )
    run_ok = all(item["exit_code"] == 0 for item in commands[4:]) and adapter["pass"]
    observed = {item["name"]: command_identity_evidence(item) for item in (commands[0], commands[2], commands[3], commands[5])}
    return parent.executed_cell(
        required, commands, identity_ok, run_ok, "identity/db/minimum/adapter gate failed",
        adapter={"attempted": True, **adapter}, observed_identity=observed,
        parent_config_sha256=sha(root / config["parent_contract"]["config"]["path"]),
        parent_exp_id=parent_config["exp_id"],
    )


def run_hite(
    parent: ModuleType,
    config: dict[str, Any],
    parent_config: dict[str, Any],
    root: Path,
    attempt: Path,
    work: Path,
    fixture: dict[str, Any],
    licenses: dict[str, dict[str, Any]],
    manifest_ok: bool,
    sif: Path,
    manifest_path: Path,
    manifest_evidence: dict[str, Any],
    budget: RuntimeBudget,
) -> dict[str, Any]:
    source = config["exact_sources"]["hite"]
    required = {"HiTE": source["version"], "OCI": source["reference"], "source_commit": source["commit"]}
    prerequisite = all((fixture["pass"], licenses["hite"]["readable"], manifest_ok))
    if not prerequisite:
        return parent.blocked(
            "pre-execution immutable HiTE SIF/manifest/fixture/license asset absent or mismatched",
            required, manifest=manifest_evidence,
        )
    shutil.copy2(fixture["resolved"], work / "input" / "hite.fa")
    commands = run_hite_commands_strict(parent, sif, work, attempt / "logs/hite", config["timeouts_seconds"], budget)
    if len(commands) not in (1, 2):
        raise RuntimeError(f"HiTE command count outside identity-gated contract: {len(commands)}")
    identity_ok = hite_333_identity(commands[0])
    if len(commands) == 1:
        adapter = not_attempted("minimum and adapter gated by help identity/runtime")
        identity_stop = commands[0].get("exit_code") == 0 and commands[0].get("timed_out") is False and not identity_ok
        if identity_stop:
            assert_hite_identity_stop(commands, identity_ok, adapter)
        run_ok = False
    else:
        adapter = {"attempted": True, **parent.adapt(work / "hite" / "HiTE.gff", "gff")}
        identity_stop = False
        run_ok = commands[1]["exit_code"] == 0 and adapter["pass"]
    observed = command_identity_evidence(commands[0])
    return parent.executed_cell(
        required, commands, identity_ok, run_ok, "HiTE identity/minimum/final GFF adapter gate failed",
        identity_mismatch_stopped_before_minimum=identity_stop,
        adapter=adapter,
        observed_identity=observed,
        manifest_sha256=sha(manifest_path),
        parent_exp_id=parent_config["exp_id"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    job_id = os.environ.get("SLURM_JOB_ID")
    if not job_id:
        raise SystemExit("requires SLURM_JOB_ID")
    config_path = Path(args.config).resolve()
    output = Path(args.output).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    require_exact_cell_namespace(config["expected_cell_keys"])
    if config.get("offline") is not True:
        raise RuntimeError("offline must be true")
    budget = RuntimeBudget(config["runtime_budget"], config["timeouts_seconds"])
    root = Path(config["project_root"]).resolve()
    parent, parent_config, parent_hashes = verify_parent_contract(root, config)
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".collector.lock"
    lock_owner = parent.acquire_lock(lock, job_id, int(config["ownership"]["stale_lock_seconds"]))
    atexit.register(lambda: parent.release_lock(lock, lock_owner))
    attempt = output / "attempts" / f"attempt-{job_id}"
    if attempt.exists():
        raise SystemExit(f"attempt already exists: {attempt}")
    attempt.mkdir(parents=True)
    work = attempt / "work"
    for directory in (work / "input", work / "home", work / "tmp"):
        directory.mkdir(parents=True, exist_ok=True)
    parent.begin_rerun(output, job_id)
    try:
        fixtures: dict[str, dict[str, Any]] = {}
        for key, item in config["fixture_inputs"].items():
            path = root / item["path"]
            actual = sha(path) if path.is_file() else None
            bp = parent.fasta_bp(path) if path.is_file() else None
            fixtures[key] = {
                **item, "resolved": str(path), "actual_sha256": actual, "bp": bp,
                "pass": actual == item["sha256"] and (bp or 0) >= item["minimum_bp"],
            }
        components: dict[str, dict[str, Any]] = {}
        for key, item in config["components"].items():
            path = root / item["path"]
            actual = sha(path) if path.is_file() else None
            components[key] = {**item, "resolved": str(path), "actual_sha256": actual, "pass": actual == item["sha256"]}
        license_pin_by_key = {
            "repeatmodeler2_repeatmasker": config["asset_pins"]["rm_license"],
            "hite": config["asset_pins"]["hite_license"],
        }
        licenses = {
            key: {
                "path": str(root / rel),
                "readable": (
                    (root / rel).is_file() and os.access(root / rel, os.R_OK)
                    and (root / rel).resolve() == (root / license_pin_by_key[key]["path"]).resolve()
                    and sha(root / rel) == license_pin_by_key[key]["sha256"]
                ),
                "sha256": sha(root / rel) if (root / rel).is_file() else None,
            }
            for key, rel in config["license_evidence"].items()
        }
        famdb_path = root / config["asset_root"] / config["dfam40"]["asset_subdir"]
        famdb = parent.verify_famdb(famdb_path, parent_config, root)
        famdb_pin = config["asset_pins"]["famdb_manifest"]
        famdb_manifest_path = (root / famdb_pin["path"]).resolve()
        famdb["new_config_manifest_pin_ok"] = (
            famdb_manifest_path == (famdb_path / "manifest.json").resolve()
            and famdb_manifest_path.is_file() and sha(famdb_manifest_path) == famdb_pin["sha256"]
        )
        famdb["pass"] = bool(famdb["pass"] and famdb["new_config_manifest_pin_ok"])
        hite_manifest_ok, hite_sif, hite_manifest_path, hite_manifest = verify_hite_manifest(root, config, parent_config)
        conda_snapshot = Path(os.environ.get("TEFM_ENV_FILE", ""))
        if not conda_snapshot.is_file() or conda_snapshot.stat().st_size == 0:
            raise RuntimeError("sbatch environment snapshot is missing or empty")
        tracked = [
            config_path, Path(__file__).resolve(), Path(__file__).resolve().parent / "test_contract.py",
            root / "sbatch" / f"{config['exp_id']}.sbatch",
            root / "docs" / "experiments" / f"{config['exp_id']}.md",
        ]
        input_manifest = {
            "schema_version": "TEFM-BENCH-RM-HITE-INPUT-MANIFEST-1.0.0",
            "exp_id": config["exp_id"],
            "offline": True,
            "approved_cell_keys": list(ALLOWED_CELL_KEYS),
            "fixtures": fixtures,
            "components": components,
            "licenses": licenses,
            "famdb": famdb,
            "hite_manifest": hite_manifest,
            "parent_contract_hashes": parent_hashes,
            "new_namespace_hashes": [{"path": str(path), "sha256": sha(path) if path.is_file() else None} for path in tracked],
            "runtime_budget_before_commands": budget.snapshot(),
            "environment": {
                "python": sys.version, "platform": platform.platform(),
                "apptainer": subprocess.run(["apptainer", "--version"], text=True, capture_output=True, check=False).stdout.strip(),
                "slurm_job_id": job_id, "conda_prefix": os.environ.get("CONDA_PREFIX"),
                "conda_explicit_path": str(conda_snapshot), "conda_explicit_sha256": sha(conda_snapshot),
            },
        }
        atom(attempt / "input_manifest.json", input_manifest)
        adapter_self_test = parent.synthetic_self_test(attempt / "adapter_self_test")
        atom(attempt / "adapter_self_test.json", adapter_self_test)
        cells = execute_selected_cells(config["expected_cell_keys"], {
            "repeatmodeler2_repeatmasker": lambda: run_repeatmodeler_repeatmasker(
                parent, config, parent_config, root, attempt, work,
                fixtures["repeatmodeler_repeatmasker"], components, licenses, famdb, famdb_path, budget,
            ),
            "hite": lambda: run_hite(
                parent, config, parent_config, root, attempt, work, fixtures["hite"], licenses,
                hite_manifest_ok, hite_sif, hite_manifest_path, hite_manifest, budget,
            ),
        })
        atom(attempt / "runtime_budget.json", budget.snapshot())
        for name, cell in cells.items():
            atom(attempt / "cells" / name / "result.json", cell)
        metrics, semantic = build_metrics(config["exp_id"], config["expected_cell_keys"], cells, attempt)
        publish = attempt / "publish"
        publish.mkdir()
        atom(publish / "metrics.json", metrics)
        atom(publish / "semantic_validation.json", semantic)
        atom(publish / "command_manifest.json", {
            "schema_version": "TEFM-BENCH-RM-HITE-COMMAND-MANIFEST-1.0.0",
            "attempt": str(attempt),
            "expected_cell_keys": list(ALLOWED_CELL_KEYS),
            "cell_commands": {name: cells[name].get("commands", []) for name in ALLOWED_CELL_KEYS},
        })
        artifacts = [
            {"path": str(path), "sha256": sha(path)}
            for path in sorted(item for item in attempt.rglob("*") if item.is_file() and publish not in item.parents)
        ]
        for name in ("metrics.json", "semantic_validation.json", "command_manifest.json"):
            artifacts.append({"path": str(output / name), "staged_sha256": sha(publish / name)})
        atom(publish / "artifact_manifest.json", {
            "schema_version": "TEFM-BENCH-RM-HITE-OUTPUT-MANIFEST-1.0.0",
            "exp_id": config["exp_id"], "attempt": str(attempt), "artifacts": artifacts,
        })
        for name in ("metrics.json", "semantic_validation.json", "command_manifest.json", "artifact_manifest.json"):
            os.replace(publish / name, output / name)
        atom(output / "STATUS", "COMPLETED\n" if semantic["semantic_success"] else "FAILED\n")
        return semantic_exit_code(semantic)
    except BaseException as exc:
        atom(output / "failure.json", {
            "type": type(exc).__name__, "message": str(exc), "attempt": str(attempt),
            "runtime_budget": budget.snapshot(),
        })
        atom(output / "STATUS", "FAILED\n")
        raise
    finally:
        parent.release_lock(lock, lock_owner)


if __name__ == "__main__":
    raise SystemExit(main())
