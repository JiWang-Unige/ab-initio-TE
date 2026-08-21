#!/usr/bin/env python3
"""Fail-closed five-tool runtime closure (CPU Slurm only).

The module intentionally exposes pure manifest/metric helpers.  The accompanying
contract tests exercise those helpers without launching containers or doing
research computation.
"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import math
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Any

R1 = Path(__file__).resolve().parents[1] / "BENCH-5TOOL-SMOKE-20260811-R1"
sys.path.insert(0, str(R1))
from adapter import convert, synthetic_self_test  # noqa: E402

TERMINAL = {"ENGINEERING_PASS", "FOUNDATIONAL_TYPED_BLOCK", "VERSION_MISMATCH", "INVALID_RUN"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atom(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    if isinstance(payload, str):
        tmp.write_text(payload, encoding="utf-8")
    else:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def fasta_bp(path: Path) -> int:
    return sum(len(line.strip()) for line in path.read_text(errors="replace").splitlines() if not line.startswith(">"))


def command(name: str, argv: list[str], directory: Path, limit: int) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    out, err, timing = directory / f"{name}.out", directory / f"{name}.err", directory / f"{name}.time"
    with out.open("wb") as stdout_handle, err.open("wb") as stderr_handle:
        proc = subprocess.run(
            ["/usr/bin/time", "-v", "-o", str(timing), "timeout", "--signal=TERM", str(limit), *argv],
            stdout=stdout_handle,
            stderr=stderr_handle,
            check=False,
        )
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", timing.read_text(errors="replace"))
    return {
        "name": name,
        "argv": argv,
        "argv_shell_escaped": shlex.join(argv),
        "exit_code": proc.returncode,
        "timed_out": proc.returncode == 124,
        "stdout": str(out),
        "stderr": str(err),
        "time": str(timing),
        "peak_rss_kb": int(match.group(1)) if match else None,
    }


def stdout(result: dict[str, Any]) -> str:
    return Path(result["stdout"]).read_text(errors="replace")


def exact(result: dict[str, Any], pattern: str) -> bool:
    return result["exit_code"] == 0 and bool(re.search(pattern, stdout(result), re.I))


def edta_help_identity(text: str) -> bool:
    """Official v2.3.0 tag identifies itself as EDTA v2.3 in `-h`."""
    return bool(re.search(r"^#+\s+Extensive de-novo TE Annotator \(EDTA\) v2\.3\s+#+\s*$", text, re.MULTILINE))


def tetrimmer_help_identity(text: str) -> bool:
    return bool(re.search(r"^\s*Version:\s*1\.7\.4\s*$", text, re.MULTILINE))


def repeatmasker_424_identity(result: dict[str, Any]) -> bool:
    """Accept the exact banner only from a successful supported RM execution."""
    return result.get("exit_code") == 0 and bool(
        re.search(r"^RepeatMasker version 4\.2\.4\s*$", stdout(result), re.MULTILINE)
    )


def edta_identity_command() -> str:
    return "perl /work/edta/EDTA.pl -h"


def tetrimmer_identity_command(script_guest: str) -> str:
    return f"python {script_guest} --help"


def cexec_prefix(
    sif: Path,
    work: Path,
    famdb: Path | None = None,
    extra: tuple[tuple[Path, str], ...] = (),
) -> list[str]:
    binds = ["--bind", f"{work}:/work"]
    for host, guest in extra:
        binds += ["--bind", f"{host}:{guest}:ro"]
    environment = [
        "env", "HOME=/work/home", "TMPDIR=/work/tmp",
        "http_proxy=http://127.0.0.1:9", "https_proxy=http://127.0.0.1:9",
        "ftp_proxy=http://127.0.0.1:9", "all_proxy=socks5://127.0.0.1:9",
        "HTTP_PROXY=http://127.0.0.1:9", "HTTPS_PROXY=http://127.0.0.1:9",
        "FTP_PROXY=http://127.0.0.1:9", "ALL_PROXY=socks5://127.0.0.1:9",
        "NO_PROXY=localhost,127.0.0.1", "no_proxy=localhost,127.0.0.1",
    ]
    if famdb is not None:
        # FamDB 3.x and Earl Grey 7.3.x both require Libraries/famdb, not a
        # flat Libraries bind and not merely a RepeatMasker -lib override.
        guest_famdb = "/usr/local/share/famdb-3.0.0/Libraries/famdb"
        binds += ["--bind", f"{famdb}:{guest_famdb}:ro"]
        environment += [f"FAMDB_DIR={guest_famdb}"]
    return ["apptainer", "exec", "--cleanenv", *binds, str(sif), *environment]


def cexec(
    sif: Path,
    work: Path,
    shell_command: str,
    famdb: Path | None = None,
    extra: tuple[tuple[Path, str], ...] = (),
) -> list[str]:
    return [*cexec_prefix(sif, work, famdb, extra), "bash", "-lc", shell_command]


def cexec_direct(
    sif: Path,
    work: Path,
    command_argv: list[str],
    famdb: Path | None = None,
    extra: tuple[tuple[Path, str], ...] = (),
) -> list[str]:
    """Execute argv directly so a container login shell cannot rewrite PATH."""
    if not command_argv or any(not isinstance(value, str) or not value for value in command_argv):
        raise ValueError("direct container argv must contain non-empty strings")
    return [*cexec_prefix(sif, work, famdb, extra), *command_argv]


def run_hite_commands(sif: Path, work: Path, directory: Path, limits: dict[str, int]) -> list[dict[str, Any]]:
    """Run the preparation-validated direct entrypoint, gating minimum on help."""
    help_result = command(
        "hite_help_identity",
        cexec_direct(sif, work, ["python", "/HiTE/main.py", "-h"]),
        directory,
        limits["identity"],
    )
    commands = [help_result]
    if not exact(help_result, r"3\.3\.3"):
        return commands
    commands.append(command(
        "hite_min",
        cexec_direct(sif, work, [
            "python", "/HiTE/main.py", "--genome", "/work/input/hite.fa",
            "--thread", "2", "--annotate", "1", "--out_dir", "/work/hite",
        ]),
        directory,
        limits["minimum_input"],
    ))
    return commands


def adapt(expected: Path, fmt: str) -> dict[str, Any]:
    if not expected.is_file() or expected.stat().st_size == 0:
        return {"pass": False, "reason": "explicit expected output missing", "expected": str(expected)}
    try:
        output = expected.parent / "canonical_output.tsv"
        rows = convert(expected, output, fmt)
        return {"pass": rows > 0, "source": str(expected), "rows": rows, "output": str(output), "sha256": sha(output)}
    except Exception as exc:  # adapter errors are experiment evidence, not collector crashes
        return {"pass": False, "reason": f"{type(exc).__name__}: {exc}", "expected": str(expected)}


def identity(required: dict[str, str], observed: dict[str, str] | None = None, satisfied: bool = False) -> dict[str, Any]:
    return {"required": required, "observed": observed or {}, "satisfied": bool(satisfied)}


def blocked(reason: str, required_identity: dict[str, str], **extra: Any) -> dict[str, Any]:
    return {
        "status": "FOUNDATIONAL_TYPED_BLOCK",
        "blockers": [reason],
        "commands": [],
        "identity": identity(required_identity),
        **extra,
    }


def executed_cell(
    required_identity: dict[str, str],
    commands: list[dict[str, Any]],
    identity_ok: bool,
    run_ok: bool,
    blocker: str,
    identity_mismatch_stopped_before_minimum: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    """Classify a cell after execution; it can never become foundational."""
    if not commands:
        raise ValueError("executed cell requires command evidence")
    runtime_failures = [
        str(item.get("name", "UNNAMED"))
        for item in commands
        if item.get("exit_code") != 0 or item.get("timed_out") is True
    ]
    if identity_mismatch_stopped_before_minimum and (identity_ok or run_ok or runtime_failures):
        raise ValueError("identity-gated stop requires exit-zero mismatch before minimum")
    if runtime_failures:
        status = "INVALID_RUN"
    elif identity_mismatch_stopped_before_minimum:
        status = "VERSION_MISMATCH"
    elif not run_ok:
        status = "INVALID_RUN"
    elif not identity_ok:
        status = "VERSION_MISMATCH"
    else:
        status = "ENGINEERING_PASS"
    blockers = [] if status == "ENGINEERING_PASS" else [blocker]
    if runtime_failures:
        blockers.append(f"nonzero_or_timeout_commands={','.join(runtime_failures)}")
    return {
        "status": status,
        "commands": commands,
        "blockers": blockers,
        "identity": identity(required_identity, extra.pop("observed_identity", None), identity_ok),
        **extra,
    }


def verify_famdb(asset: Path, config: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Validate both the archived legacy manifest and the current manifest.

    Legacy bytes are audited, but a v1 asset without preparation provenance is
    never runtime-eligible and can only produce a typed block.
    """
    required = [
        asset / "manifest.json", asset / "famdb.py", asset / ".earlgrey.config.complete",
        asset / "dfam40.0.h5", asset / "dfam40.curated.consensus.0.h5",
    ]
    evidence: dict[str, Any] = {"path": str(asset), "pass": False, "files": []}
    for path in required:
        evidence["files"].append({"path": str(path), "sha256": sha(path) if path.is_file() else None})
    if not all(path.is_file() for path in required):
        evidence["reason"] = "required FamDB file missing"
        return evidence
    try:
        manifest = json.loads((asset / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        evidence["reason"] = f"manifest parse failure: {exc}"
        return evidence
    schema = manifest.get("schema_version")
    if schema not in {"TEFM-FAMDB-ASSET-1.0.0", "TEFM-FAMDB-ASSET-2.0.0"}:
        evidence["reason"] = f"unsupported manifest schema: {schema}"
        return evidence
    input_rows = manifest.get("inputs", [])
    output_rows = manifest.get("outputs", [])
    source_rows = {row.get("id"): row for row in input_rows}
    expected_mapping = {"full": "dfam40.0.h5", "curated_consensus": "dfam40.curated.consensus.0.h5"}
    exact_input_set = len(input_rows) == len(expected_mapping) and set(source_rows) == set(expected_mapping)
    source_ok = True
    mapping_ok = exact_input_set
    for source_id, expected_output in expected_mapping.items():
        cfg_entry = config["dfam40"][source_id]
        row = source_rows.get(source_id, {})
        source_path = (project_root / cfg_entry["path"]).resolve()
        source_ok &= (
            row.get("source") == str(source_path)
            and row.get("source_sha256") == cfg_entry["sha256"]
            and source_path.is_file()
            and sha(source_path) == cfg_entry["sha256"]
        )
        mapping_ok &= row.get("output") == expected_output
    declared = {row.get("name"): row.get("sha256") for row in output_rows}
    exact_output_set = len(output_rows) == len(expected_mapping) and set(declared) == set(expected_mapping.values())
    outputs_ok = all(sha(asset / name) == declared.get(name) for name in ("dfam40.0.h5", "dfam40.curated.consensus.0.h5"))
    wrapper_ok = manifest.get("famdb_wrapper_sha256") == sha(asset / "famdb.py")
    marker_ok = (asset / ".earlgrey.config.complete").stat().st_size == 0
    env_path = Path(manifest.get("environment_path", ""))
    current_job_ok = schema == "TEFM-FAMDB-ASSET-2.0.0" and all((
        bool(manifest.get("preparation_slurm_job_id")),
        manifest.get("preparation_code_sha256") == sha(Path(__file__).resolve().parent / "prepare_famdb.py"),
        manifest.get("config_sha256") == sha(project_root / "configs" / f"{config['exp_id']}.yaml"),
        env_path.is_file(), manifest.get("environment_sha256") == (sha(env_path) if env_path.is_file() else None),
    ))
    evidence.update({
        "schema_version": schema,
        "manifest_sha256": sha(asset / "manifest.json"),
        "legacy_manifest": schema == "TEFM-FAMDB-ASSET-1.0.0",
        "provenance_limited_typed_block": schema == "TEFM-FAMDB-ASSET-1.0.0",
        "preparation_slurm_job_id": manifest.get("preparation_slurm_job_id"),
        "current_provenance_ok": current_job_ok,
        "declared_config_sha256": manifest.get("config_sha256"),
        "current_config_sha256": sha(project_root / "configs" / f"{config['exp_id']}.yaml") if config.get("exp_id") else None,
        "legacy_config_hash_nonbinding": schema == "TEFM-FAMDB-ASSET-1.0.0",
        "exact_input_row_set": exact_input_set, "source_output_mapping_ok": bool(mapping_ok),
        "exact_output_row_set": exact_output_set,
        "source_hashes_ok": bool(source_ok), "output_hashes_ok": outputs_ok,
        "wrapper_hash_ok": wrapper_ok, "marker_ok": marker_ok,
        "required_database_ok": manifest.get("required_database") == config["dfam40"]["required_database"],
    })
    evidence["asset_integrity_pass"] = all((exact_input_set, mapping_ok, exact_output_set, source_ok, outputs_ok, wrapper_ok, marker_ok, evidence["required_database_ok"]))
    evidence["pass"] = bool(evidence["asset_integrity_pass"] and current_job_ok)
    if not evidence["pass"]:
        evidence["reason"] = "legacy provenance-limited FamDB is typed-block only" if schema == "TEFM-FAMDB-ASSET-1.0.0" and evidence["asset_integrity_pass"] else "FamDB manifest/source-output mapping/output/wrapper/marker/provenance contract mismatch"
    return evidence


def verify_checksum_manifest(manifest_path: Path, required_files: list[Path]) -> dict[str, Any]:
    if not manifest_path.is_file():
        return {"pass": False, "reason": "checksum manifest missing", "path": str(manifest_path)}
    declared: dict[str, str] = {}
    malformed: list[str] = []
    for raw in manifest_path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.strip().split(maxsplit=1)
        if len(fields) != 2 or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
            malformed.append(raw)
            continue
        declared[Path(fields[1].lstrip("* ")).name] = fields[0]
    rows = [{"path": str(path), "declared": declared.get(path.name), "actual": sha(path) if path.is_file() else None} for path in required_files]
    return {"pass": not malformed and all(row["actual"] is not None and row["actual"] == row["declared"] for row in rows), "path": str(manifest_path), "manifest_sha256": sha(manifest_path), "files": rows, "malformed": malformed}


def build_metrics(exp_id: str, expected: list[str], cells: dict[str, dict[str, Any]], attempt: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_set, observed_set = set(expected), set(cells)
    missing, unexpected = sorted(expected_set - observed_set), sorted(observed_set - expected_set)
    counts = {status: sum(cell.get("status") == status for name, cell in cells.items() if name in expected_set) for status in sorted(TERMINAL)}
    terminal_count = sum(counts.values())
    substitutions = sum(
        cell.get("status") == "ENGINEERING_PASS" and not cell.get("identity", {}).get("satisfied", False)
        for name, cell in cells.items() if name in expected_set
    )
    semantic_success = (
        not missing and not unexpected and terminal_count == len(expected)
        and counts["INVALID_RUN"] == 0 and substitutions == 0
    )
    denominator = len(expected)
    metrics = {
        "schema_version": "TEFM-BENCH-5TOOL-DENOMINATOR-CLOSURE-3.0.0",
        "exp_id": exp_id, "claim_eligible": False,
        "primary_metric": "terminal_cell_count", "expected_cell_count": denominator,
        "expected_cell_keys": expected, "observed_cell_keys": sorted(cells),
        "missing_cell_keys": missing, "unexpected_cell_keys": unexpected,
        "terminal_cell_count": terminal_count,
        "semantic_success": semantic_success,
        "engineering_pass_fraction": counts["ENGINEERING_PASS"] / denominator if denominator else 0.0,
        "invalid_cell_fraction": counts["INVALID_RUN"] / denominator if denominator else 1.0,
        "silent_substitution_count": substitutions, "counts": counts, "attempt": str(attempt),
    }
    semantic = {
        "semantic_success": semantic_success, "expected_cell_count": denominator,
        "terminal_cell_count": terminal_count, "missing_cell_keys": missing,
        "unexpected_cell_keys": unexpected, "invalid_cell_fraction": metrics["invalid_cell_fraction"],
        "silent_substitution_count": substitutions,
    }
    return metrics, semantic


def semantic_exit_code(semantic: dict[str, Any]) -> int:
    return 0 if semantic.get("semantic_success") is True else 2


def job_is_active(job_id: str) -> bool:
    """Return a Slurm activity state; every unknown state fails closed."""
    if not job_id.isdigit():
        raise RuntimeError(f"unparseable lock owner job id; fail closed: {job_id!r}")
    proc = subprocess.run(["squeue", "-h", "-j", job_id, "-o", "%i"], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"cannot reconcile collector lock through squeue; fail closed: rc={proc.returncode}")
    if proc.stderr.strip():
        raise RuntimeError(f"unexpected squeue stderr while reconciling lock; fail closed: {proc.stderr.strip()!r}")
    records = proc.stdout.split()
    if any(record != job_id for record in records):
        raise RuntimeError(f"unexpected squeue owner output; fail closed: {records!r}")
    return bool(records)


def acquire_lock(lock: Path, job_id: str, stale_seconds: int) -> dict[str, Any]:
    lock.parent.mkdir(parents=True, exist_ok=True)
    payload = {"job_id": job_id, "host": socket.gethostname(), "pid": os.getpid(), "created_unix": time.time()}
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True)
            return payload
        except FileExistsError:
            try:
                owner = json.loads(lock.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"unparseable collector lock; fail closed: {exc}") from exc
            if not isinstance(owner, dict):
                raise RuntimeError(f"collector lock is not an object; fail closed: {owner!r}")
            owner_job = str(owner.get("job_id", ""))
            if not owner_job.isdigit():
                raise RuntimeError(f"unparseable collector lock owner; fail closed: {owner_job!r}")
            try:
                created = float(owner["created_unix"])
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError("unparseable collector lock timestamp; fail closed") from exc
            if not math.isfinite(created):
                raise RuntimeError("non-finite collector lock timestamp; fail closed")
            age = time.time() - created
            if age < 0:
                raise RuntimeError("collector lock timestamp is in the future; fail closed")
            if age < stale_seconds:
                raise SystemExit(f"recent collector lock owned by {owner}")
            if job_is_active(owner_job):
                raise SystemExit(f"active collector lock owned by {owner}")
            stale = lock.with_name(f"{lock.name}.stale.{int(time.time())}.{owner_job}")
            os.replace(lock, stale)


def release_lock(lock: Path, owner: dict[str, Any]) -> bool:
    """Delete only the exact lock payload acquired by this process."""
    try:
        current = json.loads(lock.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    if current != owner:
        return False
    lock.unlink()
    return True


def begin_rerun(output: Path, job_id: str, timestamp: int | None = None) -> Path | None:
    """Atomically enter RUNNING, then archive old status and stale result files."""
    old_status_path = output / "STATUS"
    old_status = old_status_path.read_text(encoding="utf-8") if old_status_path.is_file() else None
    atom(old_status_path, "RUNNING\n")
    stale_names = ("metrics.json", "semantic_validation.json", "command_manifest.json", "artifact_manifest.json", "failure.json")
    stale = [output / name for name in stale_names if (output / name).exists()]
    if not stale and old_status is None:
        return None
    archive = output / "archive" / f"before-{job_id}-{timestamp if timestamp is not None else int(time.time())}"
    archive.mkdir(parents=True)
    if old_status is not None:
        atom(archive / "STATUS", old_status)
    for path in stale:
        os.replace(path, archive / path.name)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    job_id = os.environ.get("SLURM_JOB_ID")
    if not job_id:
        raise SystemExit("requires SLURM_JOB_ID")
    config_path, output = Path(args.config).resolve(), Path(args.output).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".collector.lock"
    lock_owner = acquire_lock(lock, job_id, int(config["ownership"]["stale_lock_seconds"]))
    atexit.register(lambda: release_lock(lock, lock_owner))
    attempt = output / "attempts" / f"attempt-{job_id}"
    if attempt.exists():
        raise SystemExit(f"attempt already exists: {attempt}")
    attempt.mkdir(parents=True)
    work = attempt / "work"
    for directory in (work / "input", work / "home", work / "tmp"):
        directory.mkdir(parents=True, exist_ok=True)
    # First atomically leave the old terminal state.  Only then archive stale
    # metrics, so there is never a COMPLETED-without-metrics observation window.
    begin_rerun(output, job_id)
    semantic_success = False
    try:
        fixtures: dict[str, dict[str, Any]] = {}
        for key, spec in config["fixture_inputs"].items():
            path = root / spec["path"]
            actual = sha(path) if path.is_file() else None
            bp = fasta_bp(path) if path.is_file() else None
            ok = actual == spec["sha256"] and ("minimum_bp" not in spec or (bp or 0) >= spec["minimum_bp"])
            fixtures[key] = {**spec, "resolved": str(path), "actual_sha256": actual, "bp": bp, "pass": ok}
        components: dict[str, dict[str, Any]] = {}
        for key, spec in config["components"].items():
            path = root / spec["path"]
            actual = sha(path) if path.is_file() else None
            components[key] = {**spec, "resolved": str(path), "actual_sha256": actual, "pass": actual == spec["sha256"]}
        licenses = {
            key: {"path": str(root / value), "readable": (root / value).is_file() and os.access(root / value, os.R_OK), "sha256": sha(root / value) if (root / value).is_file() else None}
            for key, value in config["license_evidence"].items()
        }
        famdb_path = root / config["asset_root"] / config["dfam40"]["asset_subdir"]
        famdb = verify_famdb(famdb_path, config, root)
        legacy_famdb_path = root / config["asset_root"] / "famdb"
        legacy_famdb = verify_famdb(legacy_famdb_path, config, root) if legacy_famdb_path != famdb_path else None
        tracked = [
            config_path, Path(__file__).resolve(), R1 / "adapter.py",
            root / "sbatch" / f"{config['exp_id']}.sbatch",
            root / "sbatch" / f"{config['exp_id']}-preparation.sbatch",
            root / "docs" / "experiments" / f"{config['exp_id']}.md",
            root / "docs" / "19_evaluator_contract.md",
            *sorted((Path(__file__).resolve().parent).glob("*.py")),
            *sorted((Path(__file__).resolve().parent).glob("*.sh")),
        ]
        conda_snapshot = Path(os.environ.get("TEFM_ENV_FILE", ""))
        if not conda_snapshot.is_file() or conda_snapshot.stat().st_size == 0:
            raise RuntimeError("sbatch environment snapshot is missing or empty")
        input_manifest = {
            "fixtures": fixtures, "components": components, "famdb": famdb,
            "legacy_famdb_audit_only": legacy_famdb, "licenses": licenses,
            "config_sha256": sha(config_path),
            "code_prep_docs_hashes": [{"path": str(path), "sha256": sha(path) if path.is_file() else None} for path in dict.fromkeys(tracked)],
            "evaluator_contract": "TEFM-BENCH-5TOOL-SMOKE-1.0.3",
            "environment": {
                "python": sys.version, "platform": platform.platform(),
                "apptainer": subprocess.run(["apptainer", "--version"], text=True, capture_output=True).stdout.strip(),
                "slurm_job_id": job_id, "conda_prefix": os.environ.get("CONDA_PREFIX"),
                "conda_explicit_path": str(conda_snapshot),
                "conda_explicit_sha256": sha(conda_snapshot) if conda_snapshot.is_file() else None,
            },
        }
        atom(attempt / "input_manifest.json", input_manifest)
        atom(attempt / "adapter_self_test.json", synthetic_self_test(attempt / "adapter_self_test"))

        cells: dict[str, dict[str, Any]] = {}
        limits = config["timeouts_seconds"]
        rm = Path(components["repeatmasker_4_2_4"]["resolved"])
        rm2 = Path(components["repeatmodeler_2_0_9"]["resolved"])
        eg = Path(components["earlgrey_7_3_0"]["resolved"])

        rm_required = {"RepeatModeler": "2.0.9", "RepeatMasker": "4.2.4", "Dfam": "4.0"}
        rm_prereq = fixtures["repeatmodeler_repeatmasker"]["pass"] and components["repeatmasker_4_2_4"]["pass"] and components["repeatmodeler_2_0_9"]["pass"] and famdb["pass"] and licenses["repeatmodeler2_repeatmasker"]["readable"]
        if not rm_prereq:
            cells["repeatmodeler2_repeatmasker"] = blocked("cell-local fixture/component/FamDB/license prerequisite failed", rm_required)
        else:
            shutil.copy2(fixtures["repeatmodeler_repeatmasker"]["resolved"], work / "input" / "rm.fa")
            famdb_cli = "/usr/local/share/famdb-3.0.0/famdb.py -i /usr/local/share/famdb-3.0.0/Libraries/famdb"
            commands = [
                command("famdb_info", cexec(rm, work, f"{famdb_cli} info", famdb_path), attempt / "logs/rm", limits["db_probe"]),
                command("famdb_family", cexec(rm, work, f"{famdb_cli} family --format fasta_acc MIR3", famdb_path), attempt / "logs/rm", limits["db_probe"]),
                command("rm2_version", cexec(rm2, work, "RepeatModeler -version"), attempt / "logs/rm", limits["identity"]),
                command("rm2_famdb", cexec(rm2, work, f"{famdb_cli} info", famdb_path), attempt / "logs/rm", limits["db_probe"]),
                command("rm2_min", cexec(rm2, work, "cd /work/input && BuildDatabase -name r2db rm.fa && RepeatModeler -database r2db -threads 2", famdb_path), attempt / "logs/rm", limits["minimum_input"]),
                command("rm_min", cexec(rm, work, "cd /work/input && RepeatMasker -pa 2 -nolow -gff -species 'Homo sapiens' rm.fa", famdb_path), attempt / "logs/rm", limits["minimum_input"]),
            ]
            adapter = adapt(work / "input" / "rm.fa.out", "repeatmasker_out")
            id_ok = exact(commands[0], r"Version\s*:\s*4\.0") and commands[1]["exit_code"] == 0 and exact(commands[2], r"2\.0\.9") and exact(commands[3], r"Version\s*:\s*4\.0") and repeatmasker_424_identity(commands[5])
            run_ok = all(item["exit_code"] == 0 for item in commands[4:]) and adapter["pass"]
            cells["repeatmodeler2_repeatmasker"] = executed_cell(
                rm_required, commands, id_ok, run_ok, "identity/db/minimum/adapter gate failed",
                adapter=adapter, observed_identity={"stdout_gates": "2.0.9/4.2.4/Dfam4.0", "RepeatMasker_evidence": "rm_min"},
            )

        eg_required = {"EarlGrey": "7.3.0", "Dfam": "4.0", "FamDB_layout": "Libraries/famdb"}
        eg_prereq = fixtures["earlgrey"]["pass"] and components["earlgrey_7_3_0"]["pass"] and famdb["pass"] and licenses["earlgrey"]["readable"]
        if not eg_prereq:
            cells["earlgrey"] = blocked("cell-local Earl Grey fixture/component/FamDB/license prerequisite failed", eg_required)
        else:
            shutil.copy2(fixtures["earlgrey"]["resolved"], work / "input" / "eg.fa")
            famdb_cli = "/usr/local/share/famdb-3.0.0/famdb.py -i /usr/local/share/famdb-3.0.0/Libraries/famdb"
            commands = [
                command("eg_help_identity", cexec(eg, work, "earlGrey -h", famdb_path), attempt / "logs/eg", limits["identity"]),
                command("eg_famdb", cexec(eg, work, f"{famdb_cli} info", famdb_path), attempt / "logs/eg", limits["db_probe"]),
                command("eg_min", cexec(eg, work, "earlGrey -g /work/input/eg.fa -s r2 -o /work/eg -t 4 -q yes -r 9606", famdb_path), attempt / "logs/eg", limits["minimum_input"]),
            ]
            # Official final publication path copied by earlGreyAnnotationOnly.
            final_gff = work / "eg" / "r2_EarlGrey" / "r2_summaryFiles" / "r2.filteredRepeats.gff"
            adapter = adapt(final_gff, "gff")
            id_ok = exact(commands[0], r"7\.3\.0") and exact(commands[1], r"Version\s*:\s*4\.0")
            run_ok = commands[2]["exit_code"] == 0 and adapter["pass"]
            cells["earlgrey"] = executed_cell(
                eg_required, commands, id_ok, run_ok, "identity/Dfam/-r9606/summaryFiles final GFF adapter gate failed",
                adapter=adapter, observed_identity={"stdout_gates": "7.3.0/Dfam4.0", "famdb_guest": "/usr/local/share/famdb-3.0.0/Libraries/famdb"},
            )

        hite_spec = config["exact_sources"]["hite"]
        hite_required = {"HiTE": hite_spec["version"], "OCI": hite_spec["reference"], "source_commit": hite_spec["commit"]}
        hite_sif = root / hite_spec["local_sif"]
        hite_manifest_path = hite_sif.with_suffix(hite_sif.suffix + ".manifest.json")
        hite_prereq = fixtures["hite"]["pass"] and licenses["hite"]["readable"] and hite_sif.is_file() and hite_manifest_path.is_file()
        hite_manifest: dict[str, Any] = {}
        if hite_prereq:
            try:
                hite_manifest = json.loads(hite_manifest_path.read_text(encoding="utf-8"))
                help_path = Path(hite_manifest.get("help_path", ""))
                inspect_path = Path(hite_manifest.get("inspect_path", ""))
                hite_env_path = Path(hite_manifest.get("environment_path", ""))
                hite_prereq = all((
                    hite_manifest.get("schema_version") == "TEFM-HITE-OCI-2.0.0",
                    hite_manifest.get("reference") == hite_spec["reference"],
                    hite_manifest.get("sha256") == sha(hite_sif),
                    hite_manifest.get("source_commit") == hite_spec["commit"],
                    help_path.is_file(), hite_manifest.get("help_sha256") == (sha(help_path) if help_path.is_file() else None),
                    inspect_path.is_file(), hite_manifest.get("inspect_sha256") == (sha(inspect_path) if inspect_path.is_file() else None),
                    bool(hite_manifest.get("preparation_slurm_job_id")),
                    hite_manifest.get("preparation_code_sha256") == sha(Path(__file__).resolve().parent / "acquire_hite_exact.sh"),
                    hite_manifest.get("config_sha256") == sha(config_path),
                    hite_env_path.is_file(), hite_manifest.get("environment_sha256") == (sha(hite_env_path) if hite_env_path.is_file() else None),
                ))
            except (OSError, json.JSONDecodeError):
                hite_prereq = False
        if not hite_prereq:
            cells["hite"] = blocked("complete exact digest-pinned HiTE SIF/runtime manifest absent or mismatched", hite_required, manifest=str(hite_manifest_path))
        else:
            shutil.copy2(fixtures["hite"]["resolved"], work / "input" / "hite.fa")
            commands = run_hite_commands(hite_sif, work, attempt / "logs/hite", limits)
            adapter = adapt(work / "hite" / "HiTE.gff", "gff")
            id_ok = exact(commands[0], r"3\.3\.3")
            run_ok = len(commands) == 2 and commands[1]["exit_code"] == 0 and adapter["pass"]
            cells["hite"] = executed_cell(
                hite_required, commands, id_ok, run_ok, "HiTE identity/minimum/final GFF adapter gate failed",
                identity_mismatch_stopped_before_minimum=len(commands) == 1 and commands[0]["exit_code"] == 0 and not id_ok,
                adapter=adapter, observed_identity={"manifest_sha256": sha(hite_manifest_path), "runtime_help": "3.3.3"},
            )

        edta_spec = config["exact_sources"]["edta"]
        edta_required = {"EDTA": edta_spec["version"], "release_tag": edta_spec["release_tag"], "commit": edta_spec["commit"]}
        edta_dir = root / edta_spec["overlay_dir"]
        edta_manifest_path = Path(str(edta_dir) + ".manifest.json")
        edta_base = Path(components["edta_2_3_0_base"]["resolved"])
        edta_prereq = fixtures["edta"]["pass"] and components["edta_2_3_0_base"]["pass"] and licenses["edta"]["readable"] and (edta_dir / "EDTA.pl").is_file() and edta_manifest_path.is_file()
        edta_manifest: dict[str, Any] = {}
        if edta_prereq:
            try:
                edta_manifest = json.loads(edta_manifest_path.read_text(encoding="utf-8"))
                edta_env_path = Path(edta_manifest.get("environment_path", ""))
                edta_prereq = all((
                    edta_manifest.get("schema_version") == "TEFM-EDTA-SOURCE-OVERLAY-2.0.0",
                    edta_manifest.get("commit") == edta_spec["commit"], edta_manifest.get("release_tag") == edta_spec["release_tag"],
                    edta_manifest.get("edta_pl_sha256") == sha(edta_dir / "EDTA.pl"),
                    edta_manifest.get("source_tree_sha256") == tree_hash(edta_dir),
                    bool(edta_manifest.get("preparation_slurm_job_id")),
                    edta_manifest.get("preparation_code_sha256") == sha(Path(__file__).resolve().parent / "acquire_edta_230_overlay.sh"),
                    edta_manifest.get("config_sha256") == sha(config_path),
                    edta_env_path.is_file(), edta_manifest.get("environment_sha256") == (sha(edta_env_path) if edta_env_path.is_file() else None),
                ))
            except (OSError, json.JSONDecodeError):
                edta_prereq = False
        if not edta_prereq:
            cells["edta"] = blocked("complete official EDTA tag/commit/tree/runtime manifest absent or mismatched", edta_required, manifest=str(edta_manifest_path))
        else:
            shutil.copy2(fixtures["edta"]["resolved"], work / "input" / "edta.fa")
            commands = [
                command("edta_help_identity", cexec(edta_base, work, edta_identity_command(), extra=((edta_dir, "/work/edta"),)), attempt / "logs/edta", limits["identity"]),
                command("edta_min", cexec(edta_base, work, "cd /work/input && perl /work/edta/EDTA.pl --genome edta.fa --overwrite 1 --anno 1 --threads 2", extra=((edta_dir, "/work/edta"),)), attempt / "logs/edta", limits["minimum_input"]),
            ]
            adapter = adapt(work / "input" / "edta.fa.EDTA.TEanno.gff3", "gff")
            id_ok = commands[0]["exit_code"] == 0 and edta_help_identity(stdout(commands[0]))
            run_ok = commands[1]["exit_code"] == 0 and adapter["pass"]
            cells["edta"] = executed_cell(
                edta_required, commands, id_ok, run_ok, "EDTA identity/help/minimum/final GFF adapter gate failed",
                adapter=adapter, observed_identity={"manifest_sha256": sha(edta_manifest_path), "payload_sha256": edta_manifest.get("edta_pl_sha256")},
            )

        tetrimmer_spec = config["exact_sources"]["tetrimmer"]
        tetrimmer_required = {"TEtrimmer": tetrimmer_spec["version"], "source_commit": tetrimmer_spec["commit"], "RepeatMasker": "4.2.4", "Pfam": tetrimmer_spec["pfam_release"]}
        pfam = root / tetrimmer_spec["pfam_dir"]
        pfam_files = [pfam / name for name in ("Pfam-A.hmm", "Pfam-A.hmm.dat", "Pfam-A.hmm.h3f", "Pfam-A.hmm.h3m", "Pfam-A.hmm.h3i", "Pfam-A.hmm.h3p")]
        pfam_check = verify_checksum_manifest(pfam / "manifest.sha256", pfam_files)
        concrete_hashes = all(re.fullmatch(r"[0-9a-f]{64}", str(tetrimmer_spec.get(key, ""))) for key in ("pfam_hmm_sha256", "pfam_dat_sha256"))
        provenance_path = pfam / "provenance.json"
        provenance_ok = False
        if concrete_hashes and tetrimmer_spec.get("preparation_submittable") is True and provenance_path.is_file():
            try:
                provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
                provenance_ok = all((
                    provenance.get("hmm_url") == tetrimmer_spec["pfam_hmm_url"],
                    provenance.get("dat_url") == tetrimmer_spec["pfam_dat_url"],
                    provenance.get("hmm_gz_sha256") == tetrimmer_spec["pfam_hmm_sha256"],
                    provenance.get("dat_gz_sha256") == tetrimmer_spec["pfam_dat_sha256"],
                    bool(provenance.get("preparation_slurm_job_id")),
                ))
            except (OSError, json.JSONDecodeError):
                provenance_ok = False
        pfam_check.update({"config_hashes_concrete": concrete_hashes, "preparation_submittable": tetrimmer_spec.get("preparation_submittable"), "provenance_path": str(provenance_path), "provenance_ok": provenance_ok})
        pfam_check["pass"] = bool(pfam_check["pass"] and concrete_hashes and provenance_ok)
        source_tar = root / tetrimmer_spec["source_tar"]
        tetrimmer_base = Path(components["tetrimmer_dependency_1_7_2"]["resolved"])
        tetrimmer_prereq = all((fixtures["tetrimmer_input"]["pass"], fixtures["tetrimmer_genome"]["pass"], components["tetrimmer_dependency_1_7_2"]["pass"], components["repeatmasker_4_2_4"]["pass"], licenses["tetrimmer"]["readable"], source_tar.is_file(), sha(source_tar) == tetrimmer_spec["source_sha256"], pfam_check["pass"]))
        if not tetrimmer_prereq:
            cells["tetrimmer"] = blocked("PREPARATION_TYPED_BLOCK: exact source/Pfam release+gzip hashes/checksum manifest/index/pinned RepeatMasker prerequisite failed", tetrimmer_required, pfam=pfam_check, source_tar_ok=source_tar.is_file() and sha(source_tar) == tetrimmer_spec["source_sha256"])
        else:
            source_dir = work / "tetrimmer_source"
            source_dir.mkdir()
            with tarfile.open(source_tar, "r:gz") as archive:
                archive.extractall(source_dir, filter="data")
            script_matches = list(source_dir.rglob("tetrimmer/TEtrimmer.py"))
            if len(script_matches) != 1:
                cells["tetrimmer"] = blocked("exactly one tetrimmer/TEtrimmer.py required in pinned source tar", tetrimmer_required, candidates=[str(path) for path in script_matches])
            else:
                script = script_matches[0]
                shutil.copy2(fixtures["tetrimmer_input"]["resolved"], work / "input" / "te.fa")
                shutil.copy2(fixtures["tetrimmer_genome"]["resolved"], work / "input" / "te_genome.fa")
                script_guest = f"/work/{script.relative_to(work)}"
                commands = [
                    command("tetrimmer_help_identity", cexec(tetrimmer_base, work, tetrimmer_identity_command(script_guest), extra=((pfam, "/work/pfam"),)), attempt / "logs/tetrimmer", limits["identity"]),
                    command("tetrimmer_min", cexec(tetrimmer_base, work, f"python {script_guest} --input_file /work/input/te.fa --genome_file /work/input/te_genome.fa --output_dir /work/tetrimmer_out --pfam_dir /work/pfam --num_threads 2", extra=((pfam, "/work/pfam"),)), attempt / "logs/tetrimmer", limits["minimum_input"]),
                ]
                # TEtrimmer 1.7.4 documents this exact final post-dedup library.
                final_library = work / "tetrimmer_out" / "TEtrimmer_consensus_merged.fasta"
                if final_library.is_file() and final_library.stat().st_size > 0:
                    commands.append(command("tetrimmer_repeatmasker_lib", cexec(rm, work, "cd /work/input && RepeatMasker -pa 2 -nolow -lib /work/tetrimmer_out/TEtrimmer_consensus_merged.fasta te_genome.fa"), attempt / "logs/tetrimmer", limits["minimum_input"]))
                    adapter = adapt(work / "input" / "te_genome.fa.out", "repeatmasker_out")
                    rm_adapter_identity_ok = repeatmasker_424_identity(commands[2])
                    run_ok = commands[1]["exit_code"] == 0 and commands[2]["exit_code"] == 0 and adapter["pass"]
                else:
                    adapter = {"pass": False, "reason": "documented TEtrimmer_consensus_merged.fasta missing", "expected": str(final_library)}
                    rm_adapter_identity_ok = False
                    run_ok = False
                id_ok = commands[0]["exit_code"] == 0 and tetrimmer_help_identity(stdout(commands[0])) and rm_adapter_identity_ok
                cells["tetrimmer"] = executed_cell(
                    tetrimmer_required, commands, id_ok, run_ok, "TEtrimmer/Pfam/final merged library/pinned RepeatMasker adapter gate failed",
                    adapter=adapter, pfam=pfam_check,
                    observed_identity={"source_tar_sha256": sha(source_tar), "final_library": str(final_library), "RepeatMasker_runtime": "4.2.4" if rm_adapter_identity_ok else "not_verified"},
                )

        for name, cell in cells.items():
            atom(attempt / "cells" / name / "result.json", cell)
        metrics, semantic = build_metrics(config["exp_id"], config["expected_cell_keys"], cells, attempt)
        publish = attempt / "publish"
        publish.mkdir()
        atom(publish / "metrics.json", metrics)
        atom(publish / "semantic_validation.json", semantic)
        atom(publish / "command_manifest.json", {"attempt": str(attempt), "cell_commands": {name: cell.get("commands", []) for name, cell in cells.items()}})
        artifacts = []
        for path in sorted(path for path in attempt.rglob("*") if path.is_file() and publish not in path.parents):
            artifacts.append({"path": str(path), "sha256": sha(path)})
        for name in ("metrics.json", "semantic_validation.json", "command_manifest.json"):
            artifacts.append({"path": str(output / name), "staged_sha256": sha(publish / name)})
        atom(publish / "artifact_manifest.json", {"schema_version": "TEFM-OUTPUT-MANIFEST-2.0.0", "artifacts": artifacts})
        # Publish only a complete four-file set, each through atomic rename.
        for name in ("metrics.json", "semantic_validation.json", "command_manifest.json", "artifact_manifest.json"):
            os.replace(publish / name, output / name)
        semantic_success = bool(semantic["semantic_success"])
        atom(output / "STATUS", "COMPLETED\n" if semantic_success else "FAILED\n")
        return semantic_exit_code(semantic)
    except BaseException as exc:
        atom(output / "failure.json", {"type": type(exc).__name__, "message": str(exc), "attempt": str(attempt)})
        atom(output / "STATUS", "FAILED\n")
        raise
    finally:
        release_lock(lock, lock_owner)


def tree_hash(directory: Path) -> str:
    """Hash relative names and bytes, excluding external provenance manifests."""
    h = hashlib.sha256()
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        rel = path.relative_to(directory).as_posix()
        h.update(rel.encode("utf-8") + b"\0" + sha(path).encode("ascii") + b"\n")
    return h.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
