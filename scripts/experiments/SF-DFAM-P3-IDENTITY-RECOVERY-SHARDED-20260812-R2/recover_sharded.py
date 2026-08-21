#!/usr/bin/env python3
"""Resumable four-worker exact-name recovery over frozen Dfam partition 3 units."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import signal
import subprocess
import sys
import time
import traceback
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Iterable

STOP_REQUESTED = False


class IntegrityFailure(RuntimeError):
    pass


class GlobalPinDrift(IntegrityFailure):
    pass


class ResourceFailure(RuntimeError):
    pass


class IncompleteRetryable(RuntimeError):
    pass


class UnreapedChildren(ResourceFailure):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def atomic_text(path: Path, value: str, before_replace_hook=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    if before_replace_hook is not None:
        try:
            before_replace_hook()
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, path)


def atomic_json(path: Path, value: object, before_replace_hook=None) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n", before_replace_hook)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: Iterable[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_pin(root: Path, cfg: dict, path_key: str, hash_key: str) -> Path:
    path = root / cfg[path_key]
    if not path.is_file() or sha256_file(path) != cfg[hash_key]:
        raise IntegrityFailure(f"PINNED_INPUT_DRIFT:{path_key}")
    return path


def package_hashes(root: Path, exp_id: str) -> dict[str, str]:
    paths = [root / "configs" / f"{exp_id}.yaml",
             root / "scripts/experiments" / exp_id / "recover_sharded.py",
             root / "scripts/experiments" / exp_id / "test_recover_sharded.py",
             root / "sbatch" / f"{exp_id}.sbatch"]
    return {str(path.relative_to(root)): sha256_file(path) for path in paths}


def authorization_flags() -> dict:
    return {"full_catalog_stage_authorized": False, "homology_split_authorized": False,
            "gpu_authorized": False, "s1_authorized": False}


SOURCE_STABLE_IDENTITY_FIELDS = ("symlink_target_sha256", "resolved_inode", "resolved_size",
                                 "resolved_mtime_ns", "resolved_mode_octal")
SOURCE_DEVICE_AUDIT_FIELDS = {"binding", "expected_resolved_device",
                              "observed_resolved_device", "device_match"}


def resolve_project_root(cfg: dict) -> Path:
    """Accept only the two frozen project-root spellings; do not generalize realpath aliases."""
    contract = cfg.get("project_root_alias_contract", {})
    configured = str(cfg.get("project_root", ""))
    allowed = contract.get("allowed_aliases", [])
    canonical = str(contract.get("canonical_root", ""))
    expected_aliases = {"/home/users/j/jwang/ab-initio-TE",
                        "/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE"}
    if set(allowed) != expected_aliases or canonical not in expected_aliases or configured not in expected_aliases:
        raise IntegrityFailure(f"PROJECT_ROOT_ALIAS_NOT_ALLOWED:{configured}")
    resolved = Path(configured).resolve(strict=True)
    canonical_path = Path(canonical)
    if resolved != canonical_path or not canonical_path.is_dir():
        raise IntegrityFailure(f"PROJECT_ROOT_ALIAS_RESOLUTION_DRIFT:{configured}:{resolved}")
    return canonical_path


def validate_asset_logical_path(root: Path, cfg: dict) -> Path:
    relative = PurePosixPath(str(cfg["famdb_partition_path"]))
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise IntegrityFailure("SOURCE_ASSET_PATH_NOT_ROOT_RELATIVE")
    source = root.joinpath(*relative.parts)
    normalized = str(source.resolve(strict=True))
    if normalized != cfg.get("famdb_partition_normalized_realpath"):
        raise GlobalPinDrift(f"SOURCE_ASSET_REALPATH_DRIFT:{normalized}")
    return source


def source_identity(path: Path) -> dict:
    stat_result = path.stat()
    link_target = os.readlink(path) if path.is_symlink() else str(path.resolve())
    return {"symlink_target_sha256": sha256_text(link_target), "resolved_device": stat_result.st_dev,
            "resolved_inode": stat_result.st_ino, "resolved_size": stat_result.st_size,
            "resolved_mtime_ns": stat_result.st_mtime_ns,
            "resolved_mode_octal": oct(stat_result.st_mode & 0o777)}


def validate_source_identity(path: Path, expected: dict) -> dict:
    observed = source_identity(path)
    expected_stable = {key: expected[key] for key in SOURCE_STABLE_IDENTITY_FIELDS}
    observed_stable = {key: observed[key] for key in SOURCE_STABLE_IDENTITY_FIELDS}
    if observed_stable != expected_stable:
        raise GlobalPinDrift(f"SOURCE_IDENTITY_DRIFT:{observed}")
    return observed


def validate_source_device_audit(audit: object, expected_device: object, context: str) -> dict:
    """Validate audit provenance while allowing only observed device to vary across nodes."""
    if (not isinstance(audit, dict) or set(audit) != SOURCE_DEVICE_AUDIT_FIELDS
            or audit.get("binding") != "audit_only"):
        raise IntegrityFailure(f"SOURCE_DEVICE_AUDIT_SCHEMA:{context}")
    if isinstance(expected_device, bool) or not isinstance(expected_device, int) or expected_device < 0:
        raise IntegrityFailure(f"SOURCE_DEVICE_EXPECTED_CONFIG_TYPE:{context}")
    stored_expected = audit["expected_resolved_device"]
    observed = audit["observed_resolved_device"]
    match = audit["device_match"]
    if (isinstance(stored_expected, bool) or not isinstance(stored_expected, int)
            or stored_expected < 0 or stored_expected != expected_device):
        raise IntegrityFailure(f"SOURCE_DEVICE_AUDIT_EXPECTED:{context}")
    if isinstance(observed, bool) or not isinstance(observed, int) or observed < 0:
        raise IntegrityFailure(f"SOURCE_DEVICE_AUDIT_OBSERVED:{context}")
    if not isinstance(match, bool) or match != (stored_expected == observed):
        raise IntegrityFailure(f"SOURCE_DEVICE_AUDIT_MATCH:{context}")
    return audit


def discover_topology_units(handle) -> list[str]:
    import h5py
    aux, dr = handle.get("Families/Aux"), handle.get("Families/DR")
    if not isinstance(aux, h5py.Group) or not isinstance(dr, h5py.Group):
        raise IntegrityFailure("TOPOLOGY_ROOT_MISSING")
    units = [f"Families/Aux/{key}" for key in sorted(aux.keys())]
    for first in sorted(dr.keys()):
        group = dr[first]
        if not isinstance(group, h5py.Group):
            raise IntegrityFailure(f"TOPOLOGY_WRONG_TYPE:{group.name}")
        units.extend(f"Families/DR/{first}/{second}" for second in sorted(group.keys()))
    return units


def validate_topology_units(units: list[str], expected_count: int, expected_hash: str) -> None:
    if len(units) != expected_count or len(units) != len(set(units)):
        raise IntegrityFailure("TOPOLOGY_UNIT_COUNT_OR_DUPLICATE")
    for left in units:
        for right in units:
            if left != right and right.startswith(left.rstrip("/") + "/"):
                raise IntegrityFailure(f"TOPOLOGY_ANCESTOR_OVERLAP:{left}:{right}")
    digest = sha256_text("".join(unit + "\n" for unit in units))
    if digest != expected_hash:
        raise IntegrityFailure(f"TOPOLOGY_ORDER_HASH_DRIFT:{digest}")


def validate_hdf5_handle_contract(handle, cfg: dict) -> list[str]:
    import h5py
    metadata = {key: str(handle.attrs.get(key)) for key in ("db_version", "famdb_version", "partition_num")}
    expected_metadata = {"db_version": cfg["famdb_database"]["db_version"],
                         "famdb_version": cfg["famdb_database"]["famdb_version"],
                         "partition_num": str(cfg["famdb_partition"])}
    if metadata != expected_metadata or "Lookup/ByName" in handle:
        raise GlobalPinDrift(f"SOURCE_METADATA_OR_LAYOUT_DRIFT:{metadata}")
    families = handle.get("Families")
    if not isinstance(families, h5py.Group) or sorted(families.keys()) != cfg["topology"]["expected_families_root_keys"]:
        raise GlobalPinDrift("FAMILIES_ROOT_KEY_DRIFT")
    return discover_topology_units(handle)


def validate_hdf5_source_contract(source: Path, cfg: dict) -> list[str]:
    import h5py
    with h5py.File(source, "r") as handle:
        return validate_hdf5_handle_contract(handle, cfg)


def revalidate_frozen_source_contract(root: Path, cfg: dict) -> tuple[Path, dict, list[str]]:
    """Bounded shallow revalidation; never enumerates family datasets."""
    source = validate_asset_logical_path(root, cfg)
    observed = validate_source_identity(source, cfg["famdb_source_identity"])
    verify_pin(root, cfg, "identity_layout_manifest", "identity_layout_manifest_sha256")
    verify_pin(root, cfg, "famdb_rmlib_config", "famdb_rmlib_config_sha256")
    units = validate_hdf5_source_contract(source, cfg)
    expected_units = [row[0] for row in cfg["topology"]["ordered_units_with_estimated_counts"]]
    if units != expected_units:
        raise GlobalPinDrift("SOURCE_SHALLOW_TOPOLOGY_DRIFT")
    validate_topology_units(units, int(cfg["topology"]["expected_unit_count"]),
                            cfg["topology"]["ordered_unit_list_sha256"])
    return source, observed, units


def validate_inputs(root: Path, cfg: dict):
    if cfg.get("authorization") != authorization_flags():
        raise IntegrityFailure("AUTHORIZATION_MUST_REMAIN_FALSE")
    for path_key, hash_key in (("parent_r0_config", "parent_r0_config_sha256"),
                               ("parent_r0_evaluator", "parent_r0_evaluator_sha256"),
                               ("parent_r0_observed_telemetry", "parent_r0_observed_telemetry_sha256"),
                               ("identity_config", "identity_config_sha256"),
                               ("identity_evaluator", "identity_evaluator_sha256"),
                               ("identity_layout_manifest", "identity_layout_manifest_sha256"),
                               ("identity_payload", "identity_payload_sha256"),
                               ("identity_identifier_audit", "identity_identifier_audit_sha256"),
                               ("evaluator_contract", "evaluator_contract_sha256"),
                               ("famdb_rmlib_config", "famdb_rmlib_config_sha256")):
        verify_pin(root, cfg, path_key, hash_key)
    parent = load_module("sharded_recovery_parent_contract", root / cfg["parent_r0_evaluator"])
    targets, parent_audit = parent.validate_inputs(root, cfg)
    target_mass = sum(int(row["occurrences"]) for row in targets)
    if len(targets) != int(cfg["expected_target_identifier_count"]) or target_mass != int(cfg["expected_target_occurrence_mass"]):
        raise IntegrityFailure(f"TARGET_CONTRACT_DRIFT:{len(targets)}:{target_mass}")
    all_rows = read_tsv(root / cfg["identity_identifier_audit"])
    x13 = [row for row in all_rows if row["identifier"] in set(cfg["audit_ambiguity_identifiers"])]
    if (len(x13) != 1 or x13[0]["identifier"] != "X13_LINE" or x13[0]["resolution_status"] != "ambiguous"
            or int(x13[0]["occurrences"]) != int(cfg["expected_x13_occurrence_mass"])):
        raise IntegrityFailure("X13_AUDIT_ONLY_CONTRACT_DRIFT")
    if any(row["identifier"] == "X13_LINE" for row in targets):
        raise IntegrityFailure("X13_ENTERED_RECOVERY_TARGETS")
    telemetry = json.loads((root / cfg["parent_r0_observed_telemetry"]).read_text(encoding="utf-8"))
    if int(telemetry.get("projected_full_scan_seconds", -1)) != int(cfg["resource_evidence"]["observed_serial_bound_seconds"]):
        raise IntegrityFailure("PARENT_TELEMETRY_DRIFT")
    source = validate_asset_logical_path(root, cfg)
    observed_source = validate_source_identity(source, cfg["famdb_source_identity"])
    units = validate_hdf5_source_contract(source, cfg)
    expected_pairs = cfg["topology"]["ordered_units_with_estimated_counts"]
    expected_units = [row[0] for row in expected_pairs]
    if units != expected_units or sum(int(row[1]) for row in expected_pairs) != int(cfg["famdb_expected_family_dataset_count"]):
        raise IntegrityFailure("TOPOLOGY_ESTIMATE_CONTRACT_DRIFT")
    validate_topology_units(units, int(cfg["topology"]["expected_unit_count"]),
                            cfg["topology"]["ordered_unit_list_sha256"])
    audit = {**parent_audit, "target_identifier_count": len(targets), "target_occurrence_mass": target_mass,
             "x13_audit_only_identifier_count": 1, "x13_audit_only_occurrence_mass": int(x13[0]["occurrences"]),
             "topology_unit_count": len(units), "topology_unit_list_sha256": cfg["topology"]["ordered_unit_list_sha256"],
             "source_identity": observed_source,
             "source_device_audit": {"binding": "audit_only",
                                     "expected_resolved_device": cfg["famdb_source_identity"]["resolved_device"],
                                     "observed_resolved_device": observed_source["resolved_device"],
                                     "device_match": (cfg["famdb_source_identity"]["resolved_device"]
                                                      == observed_source["resolved_device"])},
             "source_identity_full_content_sha256": False,
             "source_identity_limitation": cfg["famdb_source_identity"]["limitation"],
             "real_dataset_enumeration_executed": False, **authorization_flags()}
    return targets, x13, source, units, audit, parent


def ensure_slurm_log_dir(root: Path, cfg: dict) -> Path:
    log_dir, preview = root / cfg["slurm_log_dir"], root / cfg["preview_root"]
    if log_dir.parent != preview or log_dir.is_symlink():
        raise IntegrityFailure("SLURM_LOG_DIR_CONTRACT")
    log_dir.mkdir(parents=True, exist_ok=True)
    probe = log_dir / ".write_probe.tmp"
    descriptor = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, b"writable\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
        probe.unlink(missing_ok=True)
    sentinel = log_dir / ".slurm_parent_precreated.json"
    contract = {"schema_version": "SF-P3-R2-SLURM-LOG-1.0.0",
                "root_relative_log_dir": str(log_dir.relative_to(root)),
                "precreated_before_submission": True, "writable_probe_passed": True}
    if sentinel.exists():
        try:
            if json.loads(sentinel.read_text(encoding="utf-8")) != contract:
                raise IntegrityFailure("SLURM_LOG_SENTINEL_DRIFT")
        except (OSError, json.JSONDecodeError) as exc:
            raise IntegrityFailure("SLURM_LOG_SENTINEL_CORRUPT") from exc
    else:
        atomic_json(sentinel, contract)
    return sentinel


def archive_pre_bundle_preview_files(preview: Path) -> list[str]:
    """One-time recoverable migration of the pre-review mutable preview contract."""
    legacy_names = ("STATUS", "TERMINAL_STATE.json", "CANONICAL_TERMINAL.json", "metrics.json", "report.json",
                    "input_manifest.json", "static_contract.json", "output_manifest.sha256")
    archive = preview / "legacy_pre_immutable_bundle"
    moved = []
    for name in legacy_names:
        source = preview / name
        if not source.is_file():
            continue
        archive.mkdir(parents=True, exist_ok=True)
        destination = archive / name
        if destination.exists():
            destination = archive / f"{name}.{sha256_file(source)}"
        os.replace(source, destination)
        moved.append(str(destination))
    return moved


def query_job_state(job_id: str, runner=subprocess.run) -> str:
    result = runner(["squeue", "-h", "-j", job_id, "-o", "%T"], capture_output=True, text=True)
    if result.returncode != 0:
        return "UNKNOWN"
    return "DEAD" if not result.stdout.strip() else "LIVE"


def acquire_owner_lock(preview: Path, lock_name: str, job_id: str, runner=subprocess.run) -> str:
    if not job_id.isdigit() or int(job_id) <= 0:
        raise IntegrityFailure("FORMAL_SLURM_GUARD")
    lock = preview / lock_name
    try:
        lock.mkdir(parents=False)
    except FileExistsError:
        owner_path = lock / "job_id"
        owner = owner_path.read_text(encoding="utf-8").strip() if owner_path.is_file() else ""
        if not owner.isdigit() or int(owner) <= 0:
            raise IntegrityFailure("OWNER_LOCK_MALFORMED_UNKNOWN")
        state = query_job_state(owner, runner)
        if state == "LIVE":
            raise ResourceFailure(f"OWNER_LOCK_LIVE:{owner}")
        if state == "UNKNOWN":
            raise ResourceFailure(f"OWNER_LOCK_STATE_UNKNOWN:{owner}")
        quarantine = preview / f"{lock_name}.stale.{owner}.{job_id}"
        if quarantine.exists():
            raise IntegrityFailure("OWNER_LOCK_STALE_QUARANTINE_COLLISION")
        os.replace(lock, quarantine)
        lock.mkdir()
    atomic_text(lock / "job_id", job_id + "\n")
    return "ACQUIRED"


def release_owner_lock(preview: Path, lock_name: str, job_id: str) -> None:
    lock = preview / lock_name
    owner = lock / "job_id"
    if owner.is_file() and owner.read_text(encoding="utf-8").strip() == job_id:
        owner.unlink()
        lock.rmdir()


def validate_formal_guard(root: Path, cfg: dict) -> str:
    job_id = os.environ.get("SLURM_JOB_ID", "")
    if not job_id.isdigit() or int(job_id) <= 0:
        raise IntegrityFailure("FORMAL_SLURM_GUARD")
    owner = root / cfg["preview_root"] / cfg["owner_lock_name"] / "job_id"
    if not owner.is_file() or owner.read_text(encoding="utf-8").strip() != job_id:
        raise IntegrityFailure("FORMAL_OWNER_LOCK_MISMATCH")
    return job_id


def install_signal_handler() -> None:
    def handler(_signum, _frame):
        global STOP_REQUESTED
        STOP_REQUESTED = True
    signal.signal(signal.SIGTERM, handler)


def deadline_contract(attempt_start_epoch: float, cfg: dict) -> dict[str, float]:
    if not math.isfinite(attempt_start_epoch) or attempt_start_epoch <= 0:
        raise IntegrityFailure("ATTEMPT_START_EPOCH_INVALID")
    cutoff = float(cfg["runtime"]["work_completion_cutoff_seconds"])
    if cutoff != float(cfg["resource_evidence"]["headroom_target_seconds"]):
        raise IntegrityFailure("WORK_CUTOFF_HEADROOM_CONTRACT_DRIFT")
    completion = attempt_start_epoch + cutoff
    reserve = float(cfg["runtime"]["publish_reserve_seconds"])
    if reserve <= 0 or reserve >= float(cfg["resource_evidence"]["headroom_target_seconds"]):
        raise IntegrityFailure("PUBLISH_RESERVE_INVALID")
    claim_offset = cutoff - reserve
    if claim_offset != float(cfg["runtime"]["new_unit_claim_cutoff_seconds"]):
        raise IntegrityFailure("CLAIM_CUTOFF_RESERVE_CONTRACT_DRIFT")
    return {"attempt_start_epoch": attempt_start_epoch,
            "claim_deadline_epoch": attempt_start_epoch + claim_offset,
            "completion_deadline_epoch": completion,
            "publish_reserve_seconds": reserve}


def require_before_deadline(clock, deadline: float, phase: str) -> None:
    if clock() >= deadline:
        raise IncompleteRetryable(f"ABSOLUTE_DEADLINE_REACHED:{phase}")


def iter_unit_datasets(group):
    import h5py
    stack = [group]
    while stack:
        current = stack.pop()
        for key in sorted(current.keys(), reverse=True):
            link = current.get(key, getlink=True)
            if isinstance(link, (h5py.SoftLink, h5py.ExternalLink)):
                raise IntegrityFailure(f"NONCANONICAL_H5_LINK:{current.name}/{key}")
            item = current[key]
            if isinstance(item, h5py.Dataset):
                yield item
            elif isinstance(item, h5py.Group):
                stack.append(item)
            else:
                raise IntegrityFailure(f"UNIT_OBJECT_WRONG_TYPE:{item.name}")


def decode_attr(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def unit_slug(unit: str) -> str:
    return sha256_text(unit)[:20]


def unit_pin_contract(root: Path, cfg: dict, unit: str) -> dict:
    packages = package_hashes(root, cfg["exp_id"])
    source = validate_asset_logical_path(root, cfg)
    observed_source = validate_source_identity(source, cfg["famdb_source_identity"])
    verify_pin(root, cfg, "identity_layout_manifest", "identity_layout_manifest_sha256")
    verify_pin(root, cfg, "famdb_rmlib_config", "famdb_rmlib_config_sha256")
    expected_source = {key: cfg["famdb_source_identity"][key] for key in SOURCE_STABLE_IDENTITY_FIELDS}
    observed_stable = {key: observed_source[key] for key in SOURCE_STABLE_IDENTITY_FIELDS}
    return {"expected_source_identity": expected_source, "observed_source_identity": observed_stable,
            "source_device_audit": {"binding": "audit_only",
                                    "expected_resolved_device": cfg["famdb_source_identity"]["resolved_device"],
                                    "observed_resolved_device": observed_source["resolved_device"],
                                    "device_match": (cfg["famdb_source_identity"]["resolved_device"]
                                                     == observed_source["resolved_device"])},
            "source_asset_path": cfg["famdb_partition_path"],
            "source_normalized_realpath": cfg["famdb_partition_normalized_realpath"],
            "identity_layout_manifest_sha256": cfg["identity_layout_manifest_sha256"],
            "rmlib_config_sha256": cfg["famdb_rmlib_config_sha256"],
            "evaluator_contract_sha256": cfg["evaluator_contract_sha256"],
            "config_sha256": packages[f"configs/{cfg['exp_id']}.yaml"],
            "code_sha256": packages[f"scripts/experiments/{cfg['exp_id']}/recover_sharded.py"],
            "unit": unit}


def create_unit_payload_manifest(stage: Path) -> str:
    required = ("dataset_inventory.tsv", "exact_candidates.tsv", "unit_summary.json")
    files = {name: sha256_file(stage / name) for name in required if (stage / name).is_file()}
    if set(files) != set(required):
        raise IntegrityFailure("UNIT_PAYLOAD_MISSING")
    atomic_json(stage / "UNIT_PAYLOAD_MANIFEST.json",
                {"schema_version": "SF-P3-R2-UNIT-PAYLOAD-1.0.0", "self_included": False, "files": files})
    return sha256_file(stage / "UNIT_PAYLOAD_MANIFEST.json")


def verify_unit_checkpoint(root: Path, cfg: dict, unit: str) -> dict:
    validate_source_identity(validate_asset_logical_path(root, cfg), cfg["famdb_source_identity"])
    complete = root / cfg["checkpoint_root"] / "units" / f"{unit_slug(unit)}.COMPLETE"
    if not complete.is_dir():
        raise FileNotFoundError(unit)
    manifest_path = complete / "UNIT_COMPLETE_MANIFEST.json"
    payload_path = complete / "UNIT_PAYLOAD_MANIFEST.json"
    if not manifest_path.is_file() or not payload_path.is_file():
        raise IntegrityFailure(f"COMPLETE_UNIT_MANIFEST_MISSING:{unit}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_manifest_fields = {"schema_version", "status", "unit", "created_attempt_id",
                                "created_worker_id", "pin_contract", "path_inventory_count",
                                "path_inventory_sha256", "unit_payload_manifest_sha256"}
    if (set(manifest) != required_manifest_fields
            or manifest.get("schema_version") != "SF-P3-R2-UNIT-COMPLETE-1.0.0"
            or manifest.get("status") != "UNIT_COMPLETE" or manifest.get("unit") != unit
            or not str(manifest.get("created_attempt_id", ""))
            or not str(manifest.get("created_worker_id", ""))):
        raise IntegrityFailure(f"COMPLETE_UNIT_SCHEMA:{unit}")
    stored_pin = manifest.get("pin_contract", {})
    current_pin = unit_pin_contract(root, cfg, unit)
    validate_source_device_audit(stored_pin.get("source_device_audit"),
                                 cfg["famdb_source_identity"]["resolved_device"], f"stored:{unit}")
    validate_source_device_audit(current_pin.get("source_device_audit"),
                                 cfg["famdb_source_identity"]["resolved_device"], f"current:{unit}")
    stored_binding = {key: value for key, value in stored_pin.items() if key != "source_device_audit"}
    current_binding = {key: value for key, value in current_pin.items() if key != "source_device_audit"}
    if stored_binding != current_binding:
        raise GlobalPinDrift(f"COMPLETE_UNIT_PIN_DRIFT:{unit}")
    if sha256_file(payload_path) != manifest.get("unit_payload_manifest_sha256"):
        raise IntegrityFailure(f"COMPLETE_UNIT_PAYLOAD_MANIFEST_DRIFT:{unit}")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    required_payload_files = {"dataset_inventory.tsv", "exact_candidates.tsv", "unit_summary.json"}
    if (set(payload) != {"schema_version", "self_included", "files"}
            or payload.get("schema_version") != "SF-P3-R2-UNIT-PAYLOAD-1.0.0"
            or payload.get("self_included") is not False
            or set(payload.get("files", {})) != required_payload_files):
        raise IntegrityFailure(f"COMPLETE_UNIT_PAYLOAD_SCHEMA:{unit}")
    for relpath, expected in payload.get("files", {}).items():
        if not (complete / relpath).is_file() or sha256_file(complete / relpath) != expected:
            raise IntegrityFailure(f"COMPLETE_UNIT_PAYLOAD_HASH_DRIFT:{unit}:{relpath}")
    summary = json.loads((complete / "unit_summary.json").read_text(encoding="utf-8"))
    inventory = read_tsv(complete / "dataset_inventory.tsv")
    if (summary.get("unit") != unit or int(summary.get("dataset_count", -1)) != len(inventory)
            or summary.get("ordered_path_inventory_sha256") != sha256_text("".join(row["dataset_path"] + "\n" for row in inventory))
            or int(manifest.get("path_inventory_count", -1)) != len(inventory)
            or manifest.get("path_inventory_sha256") != summary.get("ordered_path_inventory_sha256")
            or len(inventory) != len({row["dataset_path"] for row in inventory})
            or len(inventory) != len({row["object_address"] for row in inventory})):
        raise IntegrityFailure(f"COMPLETE_UNIT_INVENTORY_DRIFT:{unit}")
    if any(not row["dataset_path"].startswith(unit.rstrip("/") + "/") for row in inventory):
        raise IntegrityFailure(f"COMPLETE_UNIT_PATH_ESCAPE:{unit}")
    return {"complete_dir": complete, "manifest": manifest, "summary": summary,
            "inventory": inventory, "candidates": read_tsv(complete / "exact_candidates.tsv")}


def quarantine_partial_units(root: Path, cfg: dict, unit: str, attempt_id: str) -> list[str]:
    units_root = root / cfg["checkpoint_root"] / "units"
    quarantine = root / cfg["checkpoint_root"] / "quarantine"
    quarantine.mkdir(parents=True, exist_ok=True)
    moved = []
    for partial in sorted(units_root.glob(f"{unit_slug(unit)}.tmp.*")):
        destination = quarantine / f"{partial.name}.before-{attempt_id}"
        if destination.exists():
            raise IntegrityFailure(f"PARTIAL_QUARANTINE_COLLISION:{partial.name}")
        os.replace(partial, destination)
        try:
            moved.append(str(destination.relative_to(root)))
        except ValueError:
            moved.append(str(destination))
    return moved


def quarantine_bad_complete_unit(root: Path, cfg: dict, unit: str, attempt_id: str, error: str) -> str:
    """Quarantine a locally corrupt payload; pin/source drift remains a global integrity failure."""
    complete = root / cfg["checkpoint_root"] / "units" / f"{unit_slug(unit)}.COMPLETE"
    quarantine = root / cfg["checkpoint_root"] / "quarantine"
    quarantine.mkdir(parents=True, exist_ok=True)
    destination = quarantine / f"{complete.name}.bad.before-{attempt_id}"
    if destination.exists():
        raise IntegrityFailure(f"BAD_COMPLETE_QUARANTINE_COLLISION:{unit}")
    os.replace(complete, destination)
    atomic_json(destination / "QUARANTINE_REASON.json", {"unit": unit, "error": error})
    try:
        return str(destination.relative_to(root))
    except ValueError:
        return str(destination)


def resume_or_quarantine_unit(root: Path, cfg: dict, unit: str, attempt_id: str) -> tuple[bool, str | None]:
    """Reuse a valid COMPLETE, quarantine local parse/hash/schema corruption, never absorb global pin drift."""
    try:
        verify_unit_checkpoint(root, cfg, unit)
        return True, None
    except GlobalPinDrift:
        raise
    except Exception as exc:
        moved = quarantine_bad_complete_unit(root, cfg, unit, attempt_id, f"{type(exc).__name__}:{exc}")
        return False, moved


def scan_and_publish_unit(root: Path, cfg: dict, handle, unit: str, target_names: set[str],
                          attempt_id: str, worker_id: str, pre_publish_hook=None) -> dict:
    import h5py
    units_root = root / cfg["checkpoint_root"] / "units"
    units_root.mkdir(parents=True, exist_ok=True)
    complete = units_root / f"{unit_slug(unit)}.COMPLETE"
    if complete.exists():
        return verify_unit_checkpoint(root, cfg, unit)["summary"]
    stage = units_root / f"{unit_slug(unit)}.tmp.{attempt_id}.{worker_id}.{os.getpid()}"
    stage.mkdir(parents=False, exist_ok=False)
    inventory, candidates, counts = [], [], Counter()
    try:
        source = validate_asset_logical_path(root, cfg)
        validate_source_identity(source, cfg["famdb_source_identity"])
        validate_hdf5_handle_contract(handle, cfg)
        group = handle.get(unit)
        if not isinstance(group, h5py.Group):
            raise IntegrityFailure(f"UNIT_GROUP_MISSING:{unit}")
        for dataset in iter_unit_datasets(group):
            path = dataset.name.lstrip("/")
            if not path.startswith(unit.rstrip("/") + "/"):
                raise IntegrityFailure(f"UNIT_DATASET_PATH_ESCAPE:{unit}:{path}")
            object_address = str(h5py.h5o.get_info(dataset.id).addr)
            inventory.append({"dataset_path": path, "object_address": object_address})
            for field in ("accession", "name", "version", "consensus", "model"):
                counts[field] += int(field in dataset.attrs)
            name = decode_attr(dataset.attrs.get("name"))
            if name not in target_names:
                continue
            accession = decode_attr(dataset.attrs.get("accession"))
            version_raw = dataset.attrs.get("version")
            try:
                version = int(version_raw) if version_raw is not None else None
            except (TypeError, ValueError, OverflowError):
                # Preserve an exact-name source row with incomplete identity so
                # the frozen resolver emits invalid_metadata/typed block.
                version = None
            consensus = decode_attr(dataset.attrs.get("consensus")).upper().replace("U", "T")
            candidates.append({"identifier": name, "accession": accession,
                               "version": version if version is not None else "",
                               "versioned_accession": f"{accession}.{version}" if accession and version is not None else "",
                               "consensus_sha256": sha256_text(consensus) if consensus else "",
                               "consensus_length": len(consensus), "h5_dataset_path": dataset.name,
                               "source_partition": int(cfg["famdb_partition"]), "source_unit": unit})
        inventory.sort(key=lambda row: row["dataset_path"])
        candidates.sort(key=lambda row: (row["identifier"], row["versioned_accession"], row["h5_dataset_path"]))
        if len(inventory) != len({row["dataset_path"] for row in inventory}) or len(inventory) != len({row["object_address"] for row in inventory}):
            raise IntegrityFailure(f"UNIT_PATH_OR_HARDLINK_DUPLICATE:{unit}")
        write_tsv(stage / "dataset_inventory.tsv", inventory, ["dataset_path", "object_address"])
        write_tsv(stage / "exact_candidates.tsv", candidates,
                  ["identifier", "accession", "version", "versioned_accession", "consensus_sha256",
                   "consensus_length", "h5_dataset_path", "source_partition", "source_unit"])
        summary = {"schema_version": "SF-P3-R2-UNIT-SUMMARY-1.0.0", "unit": unit,
                   "dataset_count": len(inventory), "consensus_attribute_count": counts["consensus"],
                   "model_attribute_count": counts["model"], "name_attribute_count": counts["name"],
                   "accession_attribute_count": counts["accession"], "version_attribute_count": counts["version"],
                   "exact_candidate_row_count": len(candidates),
                   "ordered_path_inventory_sha256": sha256_text("".join(row["dataset_path"] + "\n" for row in inventory)),
                   "ordered_object_address_sha256": sha256_text("".join(row["object_address"] + "\n" for row in inventory))}
        atomic_json(stage / "unit_summary.json", summary)
        payload_hash = create_unit_payload_manifest(stage)
        if pre_publish_hook is not None:
            pre_publish_hook()
        # Revalidate after all H5 reads and immediately before COMPLETE publication.
        validate_source_identity(validate_asset_logical_path(root, cfg), cfg["famdb_source_identity"])
        validate_hdf5_handle_contract(handle, cfg)
        atomic_json(stage / "UNIT_COMPLETE_MANIFEST.json",
                    {"schema_version": "SF-P3-R2-UNIT-COMPLETE-1.0.0", "status": "UNIT_COMPLETE",
                     "unit": unit, "created_attempt_id": attempt_id, "created_worker_id": worker_id,
                     "pin_contract": unit_pin_contract(root, cfg, unit),
                     "path_inventory_count": len(inventory),
                     "path_inventory_sha256": summary["ordered_path_inventory_sha256"],
                     "unit_payload_manifest_sha256": payload_hash})
        for file_path in stage.iterdir():
            if file_path.is_file():
                with file_path.open("rb") as handle_for_sync:
                    os.fsync(handle_for_sync.fileno())
        fsync_directory(stage)
        if complete.exists():
            raise IntegrityFailure(f"UNIT_COMPLETE_RACE:{unit}")
        os.replace(stage, complete)
        fsync_directory(units_root)
        return verify_unit_checkpoint(root, cfg, unit)["summary"]
    except Exception:
        # A .tmp directory is deliberately left for next-attempt quarantine/recompute.
        raise


def estimated_balance_plan(cfg: dict) -> dict[int, list[str]]:
    workers = int(cfg["runtime"]["workers"])
    result, loads = {index: [] for index in range(workers)}, [0] * workers
    pairs = [(str(unit), int(count)) for unit, count in cfg["topology"]["ordered_units_with_estimated_counts"]]
    order_index = {unit: index for index, (unit, _count) in enumerate(pairs)}
    for unit, count in sorted(pairs, key=lambda row: (-row[1], order_index[row[0]])):
        worker = min(range(workers), key=lambda index: (loads[index], index))
        result[worker].append(unit)
        loads[worker] += count
    return result


def initialize_dynamic_queue(queue_root: Path, units: list[str], plan: dict[int, list[str]], estimates: dict[str, int]) -> None:
    if queue_root.exists():
        raise IntegrityFailure("DYNAMIC_QUEUE_DIRTY")
    available = queue_root / "available"
    claimed = queue_root / "claimed"
    done = queue_root / "done"
    for path in (available, claimed, done):
        path.mkdir(parents=True, exist_ok=True)
    preference = {unit: worker for worker, values in plan.items() for unit in values}
    for unit in units:
        name = f"{999999999-estimates[unit]:09d}.{unit_slug(unit)}.json"
        atomic_json(available / name, {"unit": unit, "preferred_worker": preference[unit],
                                      "estimated_count": estimates[unit]})


def claim_next_unit(queue_root: Path, worker_id: int) -> tuple[Path, dict] | None:
    available = queue_root / "available"
    tasks = sorted(available.glob("*.json"))
    preferred, steal = [], []
    for task in tasks:
        payload = json.loads(task.read_text(encoding="utf-8"))
        (preferred if int(payload["preferred_worker"]) == worker_id else steal).append((task, payload))
    for task, payload in preferred + steal:
        claimed = queue_root / "claimed" / f"worker-{worker_id}.{task.name}"
        try:
            os.replace(task, claimed)
            return claimed, payload
        except FileNotFoundError:
            continue
    return None


def worker_run(root: Path, cfg: dict, attempt_id: str, worker_id: int, queue_root: Path,
               result_stage: Path, claim_deadline_epoch: float, clock=time.time) -> int:
    global STOP_REQUESTED
    STOP_REQUESTED = False
    install_signal_handler()
    targets, _x13, source, _units, _audit, _parent = validate_inputs(root, cfg)
    result_stage.mkdir(parents=True, exist_ok=False)
    completed = []
    import h5py
    with h5py.File(source, "r") as handle:
        if handle.mode != "r":
            raise IntegrityFailure("WORKER_H5_NOT_READ_ONLY")
        while True:
            if STOP_REQUESTED or (queue_root / "STOP").exists() or clock() >= claim_deadline_epoch:
                if clock() >= claim_deadline_epoch and not (queue_root / "STOP").exists():
                    atomic_text(queue_root / "STOP", "absolute-claim-deadline\n")
                break
            claim = claim_next_unit(queue_root, worker_id)
            if claim is None:
                break
            claim_path, task = claim
            unit = task["unit"]
            summary = scan_and_publish_unit(root, cfg, handle, unit,
                                            {row["identifier"] for row in targets}, attempt_id, str(worker_id))
            completed.append({"unit": unit, "dataset_count": summary["dataset_count"]})
            os.replace(claim_path, queue_root / "done" / claim_path.name)
    remaining = list((queue_root / "available").glob("*.json")) + list((queue_root / "claimed").glob("*.json"))
    status = "WORKER_STOPPED_RETRYABLE" if (STOP_REQUESTED or (queue_root / "STOP").exists()) and remaining else "WORKER_COMPLETE"
    result = {"schema_version": "SF-P3-R2-WORKER-1.0.0", "status": status, "worker_id": worker_id,
              "completed_units": completed, "completed_unit_count": len(completed), "h5_open_mode": "read_only"}
    atomic_json(result_stage / "worker_result.json", result)
    atomic_json(result_stage / "worker_manifest.json",
                {"worker_result_sha256": sha256_file(result_stage / "worker_result.json"),
                 "config_sha256": sha256_file(root / "configs" / f"{cfg['exp_id']}.yaml")})
    return 75 if status == "WORKER_STOPPED_RETRYABLE" else 0


def terminate_and_wait(processes: list[subprocess.Popen], grace: float, terminate_first: bool = True) -> bool:
    for process in processes:
        if process.poll() is None:
            try:
                process.terminate() if terminate_first else process.kill()
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + grace
    while any(process.poll() is None for process in processes) and time.monotonic() < deadline:
        time.sleep(0.05)
    if any(process.poll() is None for process in processes):
        for process in processes:
            if process.poll() is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                return False
    else:
        for process in processes:
            process.wait()
    return True


def launch_workers(commands: list[list[str]], result_stages: list[Path], log_dir: Path,
                   claim_deadline_epoch: float, signal_grace: float, poll_seconds: float,
                   stop_file: Path, clock=time.time) -> list[dict]:
    if len(commands) != len(result_stages) or not commands:
        raise IntegrityFailure("WORKER_COMMAND_CARDINALITY")
    require_before_deadline(clock, claim_deadline_epoch, "launch_workers_before_popen")
    log_dir.mkdir(parents=True, exist_ok=False)
    processes, handles = [], []
    try:
        for index, command in enumerate(commands):
            stdout = (log_dir / f"worker_{index}.out").open("w", encoding="utf-8")
            handles.append(stdout)
            stderr = (log_dir / f"worker_{index}.err").open("w", encoding="utf-8")
            handles.append(stderr)
            processes.append(subprocess.Popen(command, stdout=stdout, stderr=stderr, text=True))
        stop_sent = False
        stop_started = None
        while True:
            returncodes = [process.poll() for process in processes]
            # Completed nonzero always wins over timeout/hang classification.
            hard_nonzero = [(index, code) for index, code in enumerate(returncodes)
                            if code is not None and code not in (0, 75) and not (stop_sent and code == -15)]
            if hard_nonzero:
                if not terminate_and_wait(processes, 30):
                    raise UnreapedChildren("HARD_NONZERO_SIBLING_NOT_REAPED")
                if any(code in (-9, 137) for _index, code in hard_nonzero):
                    raise ResourceFailure(f"WORKER_RESOURCE_NONZERO:{hard_nonzero}")
                raise IntegrityFailure(f"WORKER_NONZERO:{hard_nonzero}")
            retryable = [(index, code) for index, code in enumerate(returncodes) if code == 75]
            if retryable and not stop_sent:
                atomic_text(stop_file, "worker-requested-stop\n")
                stop_sent = True
                stop_started = time.monotonic()
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
            deadline_reached = clock() >= claim_deadline_epoch
            if (STOP_REQUESTED or deadline_reached) and not stop_sent:
                atomic_text(stop_file, "parent-sigterm\n" if STOP_REQUESTED else "hard-time-cutoff\n")
                stop_sent = True
                stop_started = time.monotonic()
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
            if all(code is not None for code in returncodes):
                break
            if stop_sent and stop_started is not None and time.monotonic() - stop_started >= signal_grace:
                if not terminate_and_wait(processes, 30, terminate_first=False):
                    raise UnreapedChildren("WORKER_KILL_WAIT_FAILED")
                raise ResourceFailure("WORKER_CHECKPOINT_GRACE_EXHAUSTED")
            time.sleep(poll_seconds)
        final_codes = [process.returncode for process in processes]
        if any(code == 75 for code in final_codes) or stop_sent:
            raise IncompleteRetryable(f"WORKER_PRESTOP:{final_codes}")
    except BaseException:
        if not terminate_and_wait(processes, 30):
            raise UnreapedChildren("EXCEPTION_CLEANUP_CHILD_NOT_REAPED")
        raise
    finally:
        for handle in handles:
            handle.close()
    results = []
    for stage in result_stages:
        result_path, manifest_path = stage / "worker_result.json", stage / "worker_manifest.json"
        if not result_path.is_file() or not manifest_path.is_file():
            raise IntegrityFailure(f"WORKER_OUTPUT_MISSING:{stage}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sha256_file(result_path) != manifest.get("worker_result_sha256"):
            raise IntegrityFailure(f"WORKER_OUTPUT_HASH_DRIFT:{stage}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "WORKER_COMPLETE":
            raise IntegrityFailure(f"WORKER_OUTPUT_SCHEMA:{stage}")
        results.append(result)
    return results


def collect_complete_units(root: Path, cfg: dict, units: list[str], attempt_id: str | None = None) -> tuple[list[dict], list[dict], dict]:
    all_inventory, candidates, unit_summaries = [], [], []
    for unit in units:
        try:
            checkpoint = verify_unit_checkpoint(root, cfg, unit)
        except GlobalPinDrift:
            raise
        except Exception as exc:
            if attempt_id is None:
                raise
            quarantine_bad_complete_unit(root, cfg, unit, attempt_id, f"{type(exc).__name__}:{exc}")
            raise IncompleteRetryable(f"LOCAL_CHECKPOINT_CORRUPTION_RECOMPUTE:{unit}") from exc
        unit_summaries.append(checkpoint["summary"])
        all_inventory.extend({**row, "source_unit": unit} for row in checkpoint["inventory"])
        candidates.extend(checkpoint["candidates"])
    if len(unit_summaries) != int(cfg["topology"]["expected_unit_count"]):
        raise IntegrityFailure("UNIT_COMPLETENESS_34_OF_35")
    paths = [row["dataset_path"] for row in all_inventory]
    addresses = [row["object_address"] for row in all_inventory]
    if len(paths) != int(cfg["famdb_expected_family_dataset_count"]):
        raise IntegrityFailure(f"GLOBAL_DATASET_COUNT:{len(paths)}")
    if len(paths) != len(set(paths)):
        raise IntegrityFailure("GLOBAL_PATH_DUPLICATE")
    if len(addresses) != len(set(addresses)):
        raise IntegrityFailure("GLOBAL_HARDLINK_DUPLICATE")
    consensus = sum(int(row["consensus_attribute_count"]) for row in unit_summaries)
    model = sum(int(row["model_attribute_count"]) for row in unit_summaries)
    if consensus != int(cfg["famdb_expected_consensus_attribute_count"]):
        raise IntegrityFailure(f"GLOBAL_CONSENSUS_COUNT:{consensus}")
    if model != int(cfg["famdb_expected_model_attribute_count"]):
        raise IntegrityFailure(f"GLOBAL_MODEL_COUNT:{model}")
    canonical_inventory = sorted(all_inventory, key=lambda row: (row["source_unit"], row["dataset_path"]))
    canonical_candidates = sorted(candidates, key=lambda row: (row["identifier"], row["versioned_accession"],
                                                                row["h5_dataset_path"], row["source_unit"]))
    audit = {"complete_unit_count": len(unit_summaries), "family_datasets_scanned": len(paths),
             "consensus_attribute_count": consensus, "model_attribute_count": model,
             "global_unique_path_count": len(set(paths)), "global_unique_object_address_count": len(set(addresses)),
             "canonical_path_inventory_sha256": sha256_text("".join(row["dataset_path"] + "\n" for row in canonical_inventory)),
             "exact_candidate_rows": len(canonical_candidates)}
    return canonical_inventory, canonical_candidates, audit


def candidate_for_parent(row: dict) -> dict:
    return {"identifier": row["identifier"], "versioned_accession": row["versioned_accession"],
            "consensus_sha256": row["consensus_sha256"], "consensus_length": int(row["consensus_length"] or 0)}


def deterministic_semantic_payload(targets: list[dict], x13: list[dict], candidates: list[dict],
                                   scan_audit: dict, cfg: dict, parent) -> dict:
    candidates = sorted(candidates, key=lambda row: (row["identifier"], row["versioned_accession"],
                                                      row["h5_dataset_path"], row.get("source_unit", "")))
    resolution, recovery = parent.resolve_targets(targets, [candidate_for_parent(row) for row in candidates])
    blockers = (recovery["missing_identifier_count"] + recovery["ambiguous_identifier_count"]
                + recovery["invalid_metadata_identifier_count"])
    status = "RECOVERY_COMPLETE" if blockers == 0 else "IDENTITY_RECOVERY_TYPED_BLOCK"
    metrics = {"profile": cfg["profile"], "status": status,
               "primary_metric": recovery["recovered_identifier_coverage"], "semantic_success": True,
               "valid_negative": blockers > 0, "scientific_recovery_executed": 1, "claim_eligible": False,
               "full_catalog_human_gate_eligible": status == "RECOVERY_COMPLETE",
               **authorization_flags(), **scan_audit, **recovery,
               "target_identifier_count": int(cfg["expected_target_identifier_count"]),
               "target_occurrence_mass": int(cfg["expected_target_occurrence_mass"]),
               "x13_audit_only_identifier_count": 1,
               "x13_audit_only_occurrence_mass": int(cfg["expected_x13_occurrence_mass"])}
    if not all(math.isfinite(float(value)) for value in metrics.values() if isinstance(value, (int, float))):
        raise IntegrityFailure("NONFINITE_METRIC")
    report = {"schema_version": "SF-P3-R2-SEMANTIC-REPORT-1.0.0", "exp_id": cfg["exp_id"],
              "status": status, "semantic_success": True,
              "question": "Can exact case-sensitive Dfam p3 metadata recover all 279 frozen missing names?",
              "answer": "YES" if status == "RECOVERY_COMPLETE" else "NO_TYPED_BLOCK",
              "resolver_contract": cfg["resolver_contract"], "metrics": metrics}
    return {"status": status, "metrics": metrics, "report": report,
            "resolution": resolution, "targets": sorted(targets, key=lambda row: row["identifier"]),
            "x13": sorted(x13, key=lambda row: row["identifier"]), "candidates": candidates}


def write_semantic_payload(stage: Path, payload: dict, inventory: list[dict] | None = None) -> str:
    write_tsv(stage / "frozen_targets.tsv", payload["targets"],
              ["identifier", "occurrences", "labels", "species", "status", "resolution_status", "resolution_method"])
    write_tsv(stage / "x13_audit_only.tsv", payload["x13"],
              ["identifier", "occurrences", "labels", "species", "status", "resolution_status", "resolution_method",
               "candidate_count", "detail"])
    write_tsv(stage / "exact_candidates.tsv", payload["candidates"],
              ["identifier", "accession", "version", "versioned_accession", "consensus_sha256", "consensus_length",
               "h5_dataset_path", "source_partition", "source_unit"])
    write_tsv(stage / "resolution.tsv", payload["resolution"],
              ["identifier", "occurrences", "labels", "species", "status", "candidate_row_count",
               "distinct_identity_count", "versioned_accession", "consensus_sha256", "consensus_length", "detail"])
    atomic_json(stage / "metrics.json", payload["metrics"])
    atomic_json(stage / "report.json", payload["report"])
    files = ["frozen_targets.tsv", "x13_audit_only.tsv", "exact_candidates.tsv", "resolution.tsv", "metrics.json", "report.json"]
    if inventory is not None:
        write_tsv(stage / "canonical_dataset_inventory.tsv", inventory,
                  ["source_unit", "dataset_path", "object_address"])
        files.append("canonical_dataset_inventory.tsv")
    manifest = {"schema_version": "SF-P3-R2-SEMANTIC-PAYLOAD-1.0.0", "self_included": False,
                "files": {name: sha256_file(stage / name) for name in files}}
    atomic_json(stage / "SEMANTIC_PAYLOAD_MANIFEST.json", manifest)
    return sha256_file(stage / "SEMANTIC_PAYLOAD_MANIFEST.json")


def create_final_payload_manifest(stage: Path) -> str:
    files = {str(path.relative_to(stage)): sha256_file(path) for path in sorted(stage.rglob("*"))
             if path.is_file() and path.name != "PAYLOAD_MANIFEST.json"}
    required = {"SEMANTIC_PAYLOAD_MANIFEST.json", "canonical_dataset_inventory.tsv", "metrics.json", "report.json", "resolution.tsv",
                "telemetry.json", "RUN_MANIFEST.json", "env.json", "unit_manifests.json"}
    if required - set(files):
        raise IntegrityFailure(f"FINAL_PAYLOAD_MISSING:{sorted(required - set(files))}")
    atomic_json(stage / "PAYLOAD_MANIFEST.json",
                {"schema_version": "SF-P3-R2-FINAL-PAYLOAD-1.0.0", "self_included": False, "files": files})
    return sha256_file(stage / "PAYLOAD_MANIFEST.json")


def verify_final_payload(stage: Path) -> str:
    path = stage / "PAYLOAD_MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("self_included") is not False or "PAYLOAD_MANIFEST.json" in manifest.get("files", {}):
        raise IntegrityFailure("FINAL_PAYLOAD_SELF_REFERENCE")
    for relpath, expected in manifest["files"].items():
        if not (stage / relpath).is_file() or sha256_file(stage / relpath) != expected:
            raise IntegrityFailure(f"FINAL_PAYLOAD_DRIFT:{relpath}")
    return sha256_file(path)


def verify_state_bundle(root: Path, cfg: dict, pointer: dict | None = None) -> dict:
    preview = root / cfg["preview_root"]
    if pointer is None:
        pointer = json.loads((preview / "CURRENT_STATE.json").read_text(encoding="utf-8"))
    state = root / pointer["state_root_relative"]
    if state.parent != preview / "states" or state.name.startswith(".tmp") or state.is_symlink():
        raise IntegrityFailure("STATE_POINTER_PATH_ESCAPE")
    manifest = state / "STATE_MANIFEST.sha256"
    if (not state.is_dir() or not manifest.is_file()
            or manifest.is_symlink()
            or sha256_file(manifest) != pointer.get("state_manifest_sha256")):
        raise IntegrityFailure("STATE_POINTER_OR_MANIFEST_DRIFT")
    required_payload = {"STATUS", "TERMINAL_STATE.json", "metrics.json", "report.json",
                        "input_manifest.json", "static_contract.json", "external_artifacts.json"}
    actual_entries: set[str] = set()
    for path in state.rglob("*"):
        relative = path.relative_to(state).as_posix()
        if path.is_symlink() or not path.is_file():
            raise IntegrityFailure(f"STATE_UNMANIFESTED_NONREGULAR:{relative}")
        actual_entries.add(relative)
    if actual_entries != required_payload | {"STATE_MANIFEST.sha256"}:
        raise IntegrityFailure(f"STATE_EXACT_FILE_SET_DRIFT:{sorted(actual_entries)}")
    manifest_entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            expected, relpath = line.split("  ", 1)
        except ValueError as exc:
            raise IntegrityFailure("STATE_MANIFEST_LINE_SCHEMA") from exc
        relative = PurePosixPath(relpath)
        if (not relpath or relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts)
                or relpath == "STATE_MANIFEST.sha256"):
            raise IntegrityFailure(f"STATE_MANIFEST_PATH_ESCAPE_OR_SELF_REFERENCE:{relpath}")
        if relpath in manifest_entries:
            raise IntegrityFailure(f"STATE_MANIFEST_DUPLICATE_PATH:{relpath}")
        manifest_entries[relpath] = expected
    if set(manifest_entries) != required_payload:
        raise IntegrityFailure(f"STATE_MANIFEST_EXACT_SET_DRIFT:{sorted(manifest_entries)}")
    for relpath, expected in manifest_entries.items():
        path = state / relpath
        if path.is_symlink() or not path.is_file() or sha256_file(path) != expected:
            raise IntegrityFailure(f"STATE_BUNDLE_HASH_DRIFT:{relpath}")
    links = json.loads((state / "external_artifacts.json").read_text(encoding="utf-8"))
    for row in links["artifacts"]:
        path = root / row["root_relative_path"]
        if not path.is_file() or sha256_file(path) != row["sha256"]:
            raise IntegrityFailure(f"STATE_EXTERNAL_ARTIFACT_DRIFT:{row['root_relative_path']}")
    terminal = json.loads((state / "TERMINAL_STATE.json").read_text(encoding="utf-8"))
    if terminal["status"] != pointer["status"] or terminal["attempt_id"] != pointer["attempt_id"]:
        raise IntegrityFailure("STATE_POINTER_TERMINAL_MISMATCH")
    state_documents = {"STATUS": (state / "STATUS").read_text(encoding="utf-8"),
                       **{name: json.loads((state / name).read_text(encoding="utf-8"))
                          for name in ("TERMINAL_STATE.json", "metrics.json", "report.json",
                                       "input_manifest.json", "static_contract.json",
                                       "external_artifacts.json")}}
    if state.name != sha256_text(stable_json(state_documents)):
        raise IntegrityFailure("STATE_CONTENT_ADDRESS_DRIFT")
    return {"pointer": pointer, "state": state, "terminal": terminal,
            "metrics": json.loads((state / "metrics.json").read_text(encoding="utf-8")),
            "input_manifest": json.loads((state / "input_manifest.json").read_text(encoding="utf-8")),
            "static_contract": json.loads((state / "static_contract.json").read_text(encoding="utf-8"))}


def finalize_preview(root: Path, cfg: dict, status: str, attempt_id: str, metrics: dict, report: dict,
                     extra_paths: tuple[Path, ...] = (), input_manifest: dict | None = None,
                     static_contract: dict | None = None, pointer_deadline: float | None = None,
                     clock=time.time, before_pointer_hook=None) -> None:
    """Publish an immutable content-addressed state, then atomically switch the sole canonical pointer."""
    preview = root / cfg["preview_root"]
    sentinel = ensure_slurm_log_dir(root, cfg)
    if input_manifest is None or static_contract is None:
        current = verify_state_bundle(root, cfg)
        input_manifest = current["input_manifest"] if input_manifest is None else input_manifest
        static_contract = current["static_contract"] if static_contract is None else static_contract
    terminal = {"schema_version": "SF-P3-R2-TERMINAL-2.0.0", "exp_id": cfg["exp_id"],
                "status": status, "attempt_id": attempt_id,
                "semantic_success": bool(metrics.get("semantic_success", False)),
                "full_catalog_human_gate_eligible": bool(metrics.get("full_catalog_human_gate_eligible", False)),
                **authorization_flags(), "canonical_pointer": "preview/CURRENT_STATE.json"}
    external_paths = [sentinel] + list(extra_paths)
    external = {"schema_version": "SF-P3-R2-STATE-EXTERNAL-1.0.0",
                "artifacts": [{"root_relative_path": str(path.relative_to(root)), "sha256": sha256_file(path)}
                              for path in sorted(external_paths)]}
    documents = {"STATUS": status + "\n", "TERMINAL_STATE.json": terminal, "metrics.json": metrics,
                 "report.json": report, "input_manifest.json": input_manifest,
                 "static_contract.json": static_contract, "external_artifacts.json": external}
    state_id = sha256_text(stable_json(documents))
    states = preview / "states"
    states.mkdir(parents=True, exist_ok=True)
    final_state = states / state_id
    if not final_state.exists():
        stage = states / f".tmp.{state_id}.{os.getpid()}"
        stage.mkdir(parents=False, exist_ok=False)
        for name, value in documents.items():
            atomic_text(stage / name, value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + "\n")
        files = {path.name: sha256_file(path) for path in sorted(stage.iterdir()) if path.is_file()}
        atomic_text(stage / "STATE_MANIFEST.sha256",
                    "".join(f"{files[name]}  {name}\n" for name in sorted(files)))
        fsync_directory(stage)
        os.replace(stage, final_state)
        fsync_directory(states)
    state_manifest = final_state / "STATE_MANIFEST.sha256"
    pointer = {"schema_version": "SF-P3-R2-CURRENT-STATE-1.0.0", "status": status,
               "attempt_id": attempt_id, "semantic_success": bool(metrics.get("semantic_success", False)),
               "state_root_relative": str(final_state.relative_to(root)),
               "state_manifest_sha256": sha256_file(state_manifest)}
    verify_state_bundle(root, cfg, pointer)
    if pointer_deadline is not None:
        require_before_deadline(clock, pointer_deadline, "before_atomic_state_pointer")
    if before_pointer_hook is not None:
        before_pointer_hook()
    # The guard runs after pointer temporary-file fsync and immediately before
    # os.replace, so source hooks and pointer serialization time are included.
    pointer_guard = (None if pointer_deadline is None else
                     lambda: require_before_deadline(
                         clock, pointer_deadline, "after_pointer_hook_before_atomic_state_pointer"))
    atomic_json(preview / "CURRENT_STATE.json", pointer, before_replace_hook=pointer_guard)
    verify_state_bundle(root, cfg)


def static_preview(root: Path, cfg: dict) -> None:
    _targets, _x13, _source, units, input_audit, _parent = validate_inputs(root, cfg)
    preview = root / cfg["preview_root"]
    preview.mkdir(parents=True, exist_ok=True)
    archive_pre_bundle_preview_files(preview)
    ensure_slurm_log_dir(root, cfg)
    static = {"schema_version": "SF-P3-R2-STATIC-1.0.0", "package_hashes": package_hashes(root, cfg["exp_id"]),
              "input_contract": input_audit, "topology_units": units, "formal_slurm_required": True,
              "login_node_real_dataset_enumeration_executed": False, "gpus": 0}
    metrics = {"profile": cfg["profile"], "status": "IMPLEMENTED_NOT_RUN", "primary_metric": 0.0,
               "semantic_success": False, "scientific_recovery_executed": 0,
               "full_catalog_human_gate_eligible": False, **authorization_flags(), **input_audit}
    report = {"exp_id": cfg["exp_id"], "status": "IMPLEMENTED_NOT_RUN", "semantic_success": False,
              "answer": "NOT_RUN", "resolver_contract": cfg["resolver_contract"]}
    finalize_preview(root, cfg, "IMPLEMENTED_NOT_RUN", "static-preview", metrics, report,
                     input_manifest=static, static_contract=static)


def prepare_running(root: Path, cfg: dict, attempt_id: str, attempt_start_epoch: float, clock=time.time) -> None:
    deadlines = deadline_contract(attempt_start_epoch, cfg)
    require_before_deadline(clock, deadlines["claim_deadline_epoch"], "prepare_running_entry")
    job_id = validate_formal_guard(root, cfg)
    _targets, _x13, _source, _units, audit, _parent = validate_inputs(root, cfg)
    require_before_deadline(clock, deadlines["claim_deadline_epoch"], "prepare_running_after_validation")
    preview = root / cfg["preview_root"]
    run_manifest = {"schema_version": "SF-P3-R2-RUNNING-1.0.0", "attempt_id": attempt_id,
                    "slurm_job_id": job_id, "package_hashes": package_hashes(root, cfg["exp_id"]), "gpus": 0}
    run_manifest["deadline_contract"] = deadlines
    static_contract = {"package_hashes": package_hashes(root, cfg["exp_id"]),
                       "input_contract": audit, "gpus": 0}
    metrics = {"profile": cfg["profile"], "status": "FORMAL_RUNNING", "primary_metric": 0.0,
               "semantic_success": False, "scientific_recovery_executed": 0,
               "full_catalog_human_gate_eligible": False, **authorization_flags(), **audit}
    finalize_preview(root, cfg, "FORMAL_RUNNING", attempt_id, metrics,
                     {"exp_id": cfg["exp_id"], "status": "FORMAL_RUNNING", "semantic_success": False},
                     input_manifest=run_manifest, static_contract=static_contract,
                     pointer_deadline=deadlines["completion_deadline_epoch"], clock=clock)


def failure_terminal(root: Path, cfg: dict, attempt_id: str, status: str, error: str) -> tuple[str, dict]:
    if status not in {"FORMAL_INCOMPLETE_RETRYABLE", "FORMAL_FAILED_INTEGRITY", "FORMAL_FAILED_RESOURCE"}:
        raise ValueError(status)
    metrics = {"profile": cfg["profile"], "status": status, "primary_metric": 0.0,
               "semantic_success": False, "scientific_recovery_executed": 0,
               "full_catalog_human_gate_eligible": False, **authorization_flags(), "error": error}
    report = {"exp_id": cfg["exp_id"], "status": status, "semantic_success": False,
              "answer": "NOT_ESTABLISHED", "error": error}
    finalize_preview(root, cfg, status, attempt_id, metrics, report)
    return status, metrics


def run_formal(root: Path, cfg: dict, attempt_id: str, attempt_start_epoch: float,
               clock=time.time) -> tuple[str, dict]:
    global STOP_REQUESTED
    STOP_REQUESTED = False
    install_signal_handler()
    deadlines = deadline_contract(attempt_start_epoch, cfg)
    require_before_deadline(clock, deadlines["claim_deadline_epoch"], "formal_entry")
    validate_formal_guard(root, cfg)
    preview = root / cfg["preview_root"]
    attempts = preview / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    final, stage = attempts / attempt_id, attempts / f"{attempt_id}.tmp"
    if final.exists() or stage.exists():
        return failure_terminal(root, cfg, attempt_id, "FORMAL_FAILED_INTEGRITY", "DIRTY_ATTEMPT_REFUSED")
    stage.mkdir()
    started = time.monotonic()
    try:
        targets, x13, source, units, input_audit, parent = validate_inputs(root, cfg)
        require_before_deadline(clock, deadlines["claim_deadline_epoch"], "after_formal_validation")
        checkpoint_units = root / cfg["checkpoint_root"] / "units"
        checkpoint_units.mkdir(parents=True, exist_ok=True)
        reused, quarantined, missing = [], [], []
        for unit in units:
            quarantined.extend(quarantine_partial_units(root, cfg, unit, attempt_id))
            complete = checkpoint_units / f"{unit_slug(unit)}.COMPLETE"
            if complete.exists():
                try:
                    reused_ok, quarantined_path = resume_or_quarantine_unit(root, cfg, unit, attempt_id)
                    if reused_ok:
                        reused.append(unit)
                    else:
                        quarantined.append(str(quarantined_path))
                        missing.append(unit)
                except GlobalPinDrift:
                    raise
            else:
                missing.append(unit)
        require_before_deadline(clock, deadlines["claim_deadline_epoch"], "after_resume_and_quarantine")
        plan = estimated_balance_plan(cfg)
        estimates = {str(unit): int(count) for unit, count in cfg["topology"]["ordered_units_with_estimated_counts"]}
        queue_root = stage / "dynamic_queue"
        initialize_dynamic_queue(queue_root, missing, plan, estimates)
        write_tsv(stage / "estimated_balance_plan.tsv",
                  [{"worker": worker, "unit": unit, "estimated_count": estimates[unit]}
                   for worker, values in plan.items() for unit in values],
                  ["worker", "unit", "estimated_count"])
        worker_count = int(cfg["runtime"]["workers"])
        result_stages = [stage / f"worker_{index}" for index in range(worker_count)]
        executable, python = str(Path(__file__).resolve()), sys.executable
        commands = [[python, executable, "--config", str(root / "configs" / f"{cfg['exp_id']}.yaml"),
                     "--attempt-id", attempt_id, "--worker", "--worker-id", str(index),
                     "--queue-root", str(queue_root), "--worker-stage", str(result_stages[index]),
                     "--claim-deadline-epoch", str(deadlines["claim_deadline_epoch"])]
                    for index in range(worker_count)]
        require_before_deadline(clock, deadlines["claim_deadline_epoch"], "before_worker_launch")
        if missing:
            launch_workers(commands, result_stages, stage / "worker_logs",
                           deadlines["claim_deadline_epoch"],
                           float(cfg["runtime"]["sigterm_checkpoint_grace_seconds"]),
                           float(cfg["runtime"]["child_poll_seconds"]), queue_root / "STOP", clock=clock)
        require_before_deadline(clock, deadlines["claim_deadline_epoch"], "before_final_collect")
        revalidate_frozen_source_contract(root, cfg)
        inventory, candidates, scan_audit = collect_complete_units(root, cfg, units, attempt_id)
        revalidate_frozen_source_contract(root, cfg)
        scan_audit["source_device_audit"] = input_audit["source_device_audit"]
        scan_audit["source_identity_limitation"] = input_audit["source_identity_limitation"]
        # Scientific collection/conservation must finish before the claim
        # deadline.  The last 120 seconds are reserved only for publication.
        require_before_deadline(clock, deadlines["claim_deadline_epoch"], "after_final_collect")
        semantic = deterministic_semantic_payload(targets, x13, candidates, scan_audit, cfg, parent)
        semantic_hash = write_semantic_payload(stage, semantic, inventory)
        unit_manifests = []
        for unit in units:
            complete = root / cfg["checkpoint_root"] / "units" / f"{unit_slug(unit)}.COMPLETE"
            unit_manifests.append({"unit": unit,
                                   "manifest": str((complete / "UNIT_COMPLETE_MANIFEST.json").relative_to(root)),
                                   "manifest_sha256": sha256_file(complete / "UNIT_COMPLETE_MANIFEST.json")})
        atomic_json(stage / "unit_manifests.json", {"units": unit_manifests})
        telemetry = {"attempt_id": attempt_id, "elapsed_seconds": time.monotonic() - started,
                     "reused_unit_count": len(reused), "new_unit_count": len(units) - len(reused),
                     "quarantined_partial_units": quarantined,
                     "estimated_balance_plan": plan,
                     "beegfs_speedup_guaranteed": False,
                     "minimum_required_parallel_speedup": cfg["resource_evidence"]["minimum_required_parallel_speedup"]}
        atomic_json(stage / "telemetry.json", telemetry)
        run_manifest = {"schema_version": "SF-P3-R2-RUN-1.0.0", "attempt_id": attempt_id,
                        "slurm_job_id": os.environ["SLURM_JOB_ID"],
                        "package_hashes": package_hashes(root, cfg["exp_id"]),
                        "semantic_payload_manifest_sha256": semantic_hash,
                        "canonical_path_inventory_sha256": scan_audit["canonical_path_inventory_sha256"],
                        "deadline_contract": deadlines, "gpus": 0}
        atomic_json(stage / "RUN_MANIFEST.json", run_manifest)
        atomic_json(stage / "env.json", {"python_version": sys.version,
                    "h5py_version": __import__("h5py").__version__, "gpus": 0})
        create_final_payload_manifest(stage)
        verify_final_payload(stage)
        if STOP_REQUESTED:
            raise IncompleteRetryable("SIGTERM_BEFORE_ATOMIC_FINAL_PUBLISH")
        require_before_deadline(clock, deadlines["claim_deadline_epoch"], "before_final_attempt_publish")
        os.replace(stage, final)
        fsync_directory(attempts)
        verify_final_payload(final)
        revalidate_frozen_source_contract(root, cfg)
        static_contract = {"package_hashes": package_hashes(root, cfg["exp_id"]),
                           "input_contract": input_audit, "gpus": 0}
        finalize_preview(root, cfg, semantic["status"], attempt_id, semantic["metrics"], semantic["report"],
                         (final / "PAYLOAD_MANIFEST.json", final / "SEMANTIC_PAYLOAD_MANIFEST.json"),
                         input_manifest=run_manifest, static_contract=static_contract,
                         pointer_deadline=deadlines["completion_deadline_epoch"], clock=clock,
                         before_pointer_hook=lambda: revalidate_frozen_source_contract(root, cfg))
        return semantic["status"], semantic["metrics"]
    except IncompleteRetryable as exc:
        return failure_terminal(root, cfg, attempt_id, "FORMAL_INCOMPLETE_RETRYABLE", str(exc))
    except UnreapedChildren:
        atomic_json(stage / "UNREAPED_CHILDREN.json",
                    {"status": "HARD_FAILURE_UNREAPED_CHILDREN", "terminal_publish_forbidden": True})
        raise
    except ResourceFailure as exc:
        return failure_terminal(root, cfg, attempt_id, "FORMAL_FAILED_RESOURCE", str(exc))
    except Exception as exc:
        failure = stage / "failure.json" if stage.exists() else preview / f"failure.{attempt_id}.json"
        atomic_json(failure, {"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        return failure_terminal(root, cfg, attempt_id, "FORMAL_FAILED_INTEGRITY", str(exc))


def shell_failure_finalize(root: Path, cfg: dict, attempt_id: str, exit_code: int) -> tuple[str, dict]:
    preview = root / cfg["preview_root"]
    unreaped = preview / "attempts" / f"{attempt_id}.tmp" / "UNREAPED_CHILDREN.json"
    if unreaped.is_file():
        current = verify_state_bundle(root, cfg)
        return current["terminal"]["status"], current["metrics"]
    pointer_path = preview / "CURRENT_STATE.json"
    if pointer_path.is_file():
        current = verify_state_bundle(root, cfg)
        existing = current["terminal"]
        preserved = {"FORMAL_INCOMPLETE_RETRYABLE", "FORMAL_FAILED_INTEGRITY", "FORMAL_FAILED_RESOURCE",
                     "RECOVERY_COMPLETE", "IDENTITY_RECOVERY_TYPED_BLOCK"}
        if existing.get("attempt_id") == attempt_id and existing.get("status") in preserved:
            return existing["status"], current["metrics"]
    status = "FORMAL_INCOMPLETE_RETRYABLE" if exit_code == 75 else (
        "FORMAL_FAILED_RESOURCE" if exit_code in (70, 137) else "FORMAL_FAILED_INTEGRITY")
    return failure_terminal(root, cfg, attempt_id, status, f"SBATCH_POST_PREPARE_EXIT:{exit_code}")


def terminal_exit_code(status: str) -> int:
    if status in {"IMPLEMENTED_NOT_RUN", "RECOVERY_COMPLETE", "IDENTITY_RECOVERY_TYPED_BLOCK"}:
        return 0
    if status == "FORMAL_INCOMPLETE_RETRYABLE":
        return 75
    if status == "FORMAL_FAILED_RESOURCE":
        return 70
    return 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--attempt-id", default="static-preview")
    parser.add_argument("--attempt-start-epoch", type=float)
    parser.add_argument("--static-check-only", action="store_true")
    parser.add_argument("--acquire-owner-lock-only", action="store_true")
    parser.add_argument("--release-owner-lock-only", action="store_true")
    parser.add_argument("--prepare-running-only", action="store_true")
    parser.add_argument("--shell-failure-finalize", action="store_true")
    parser.add_argument("--shell-exit-code", type=int, default=2)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--worker-id", type=int)
    parser.add_argument("--queue-root", type=Path)
    parser.add_argument("--worker-stage", type=Path)
    parser.add_argument("--claim-deadline-epoch", type=float)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = resolve_project_root(cfg)
    job_id = os.environ.get("SLURM_JOB_ID", "")
    preview = root / cfg["preview_root"]
    if args.static_check_only:
        static_preview(root, cfg)
        print(json.dumps({"status": "IMPLEMENTED_NOT_RUN", "gpus": 0}, sort_keys=True))
        return
    if args.acquire_owner_lock_only:
        print(acquire_owner_lock(preview, cfg["owner_lock_name"], job_id))
        return
    if args.release_owner_lock_only:
        release_owner_lock(preview, cfg["owner_lock_name"], job_id)
        return
    if args.worker:
        if (args.worker_id is None or args.queue_root is None or args.worker_stage is None
                or args.claim_deadline_epoch is None):
            raise SystemExit("worker arguments incomplete")
        try:
            code = worker_run(root, cfg, args.attempt_id, args.worker_id, args.queue_root, args.worker_stage,
                              args.claim_deadline_epoch)
        except Exception as exc:
            print(json.dumps({"status": "WORKER_FAILED", "error": str(exc)}, sort_keys=True), file=sys.stderr)
            raise SystemExit(2) from exc
        raise SystemExit(code)
    if args.prepare_running_only:
        if args.attempt_start_epoch is None:
            raise SystemExit("--attempt-start-epoch required")
        try:
            prepare_running(root, cfg, args.attempt_id, args.attempt_start_epoch)
        except IncompleteRetryable as exc:
            failure_terminal(root, cfg, args.attempt_id, "FORMAL_INCOMPLETE_RETRYABLE", str(exc))
            raise SystemExit(75) from exc
        except ResourceFailure as exc:
            failure_terminal(root, cfg, args.attempt_id, "FORMAL_FAILED_RESOURCE",
                             f"{type(exc).__name__}:{exc}")
            raise SystemExit(70) from exc
        except Exception as exc:
            # Preserve the actual failed validation in canonical metrics/report;
            # the sbatch EXIT trap will see and retain this same-attempt terminal.
            failure_terminal(root, cfg, args.attempt_id, "FORMAL_FAILED_INTEGRITY",
                             f"{type(exc).__name__}:{exc}")
            raise SystemExit(2) from exc
        print(json.dumps({"status": "FORMAL_RUNNING", "gpus": 0}, sort_keys=True))
        return
    if args.shell_failure_finalize:
        status, _metrics = shell_failure_finalize(root, cfg, args.attempt_id, args.shell_exit_code)
        print(json.dumps({"status": status}, sort_keys=True))
        return
    if args.attempt_start_epoch is None:
        raise SystemExit("--attempt-start-epoch required")
    try:
        status, _metrics = run_formal(root, cfg, args.attempt_id, args.attempt_start_epoch)
    except IncompleteRetryable as exc:
        status, _metrics = failure_terminal(root, cfg, args.attempt_id,
                                            "FORMAL_INCOMPLETE_RETRYABLE", str(exc))
    except UnreapedChildren as exc:
        print(json.dumps({"status": "HARD_FAILURE_UNREAPED_CHILDREN", "terminal_published": False,
                          "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(70) from exc
    except ResourceFailure as exc:
        status, _metrics = failure_terminal(root, cfg, args.attempt_id,
                                            "FORMAL_FAILED_RESOURCE", f"{type(exc).__name__}:{exc}")
    except Exception as exc:
        status, _metrics = failure_terminal(root, cfg, args.attempt_id,
                                            "FORMAL_FAILED_INTEGRITY", f"{type(exc).__name__}:{exc}")
    print(json.dumps({"status": status, "gpus": 0}, sort_keys=True))
    raise SystemExit(terminal_exit_code(status))


if __name__ == "__main__":
    main()
