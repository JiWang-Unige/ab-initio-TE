#!/usr/bin/env python3
"""Pinned FamDB leaf-level exact-access probe for six accessions."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib
import json
import numbers
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EXP_ID = "SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1"
SCHEMA = "TEFM-SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-1.0.0"
AUTH_FALSE = {"annotation_authorized": False, "repeatmasker_authorized": False,
              "annotation_roundtrip_authorized": False, "full_catalog_stage_authorized": False,
              "homology_split_authorized": False, "data_stage_authorized": False,
              "gpu_authorized": False, "s1_authorized": False}
OBSERVATION_FILES = ("exact_records.json", "leaf_probe_matrix.json", "metrics.precleanup.json")
OBSERVATION_STATUS = "PRECLEANUP_OBSERVATION_COMPLETE"


class IntegrityError(RuntimeError):
    pass


class TerminationRequested(IntegrityError):
    pass


class CleanupError(IntegrityError):
    def __init__(self, message, observation_bundle=None, observation_manifest_sha256=None, close_audit=None):
        super().__init__(message)
        self.observation_bundle = observation_bundle
        self.observation_manifest_sha256 = observation_manifest_sha256
        self.close_audit = close_audit


class TypedBlock(RuntimeError):
    def __init__(self, metrics, audit, resolved):
        super().__init__("one or more leaf exact-access contracts failed")
        self.metrics, self.audit, self.resolved = metrics, audit, resolved


def _lifecycle_event(_name):
    """Synthetic fault-injection seam; production behavior is intentionally empty."""
    return None


def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write(path, data, event_prefix=None, pre_replace=None):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("wb") as fh:
        fh.write(data); fh.flush(); os.fsync(fh.fileno())
    if event_prefix == "terminal_current":
        _lifecycle_event("terminal_current_before_replace")
    elif event_prefix == "termination_failure_current":
        _lifecycle_event("termination_failure_current_before_replace")
    elif event_prefix:
        _lifecycle_event(event_prefix + "_before_replace")
    if pre_replace: pre_replace()
    os.replace(tmp, path)
    if event_prefix == "terminal_current":
        _lifecycle_event("terminal_current_after_replace")
    elif event_prefix == "termination_failure_current":
        _lifecycle_event("termination_failure_current_after_replace")
    elif event_prefix:
        _lifecycle_event(event_prefix + "_after_replace")


def write_json(path, obj):
    atomic_write(path, canonical_json(obj).encode())


def load_config(path):
    cfg = json.loads(Path(path).read_text())
    if cfg.get("schema_version") != SCHEMA or cfg.get("exp_id") != EXP_ID:
        raise IntegrityError("config schema/exp_id mismatch")
    return cfg


def validate_config(cfg):
    selected = cfg.get("selected_records")
    if not isinstance(selected, list) or len(selected) != 6:
        raise IntegrityError("six selected records required")
    if len({x["accession"] for x in selected}) != 6 or len({x["versioned_accession"] for x in selected}) != 6:
        raise IntegrityError("selected accession uniqueness drift")
    if cfg["source_contract"]["expected_partition_order"] != [0, 1, 2, 3, 4, 5, 6, 7, 12, 13, 15, 16]:
        raise IntegrityError("partition order drift")
    if {x["partition"] for x in selected} != {3, 7}:
        raise IntegrityError("selected partition shape drift")
    if cfg["probe_contract"] != {"lookup_method": "FamDBLeaf.get_family_by_accession",
                                  "lookup_key": "unversioned_accession_exact_case_sensitive",
                                  "all_partitions_queried_per_accession": True,
                                  "expected_api_call_count": 72, "exact_match_count": 1,
                                  "name_prefix_case_alias_copy_fallback_forbidden": True}:
        raise IntegrityError("probe contract drift")
    if cfg.get("close_contract") != {"leaf_mapping_attribute": "files", "hdf5_handle_attribute": "file",
                                       "explicit_handle_method": "close", "expected_handle_count": 12,
                                       "unique_leaf_identity_required": True, "unique_handle_identity_required": True,
                                       "partial_constructor_cleanup_required": True,
                                       "single_outer_lifecycle_envelope": True,
                                       "primary_exception_preserved": True,
                                       "cleanup_error_structured_secondary": True,
                                       "each_unique_handle_closed_at_most_once": True,
                                       "observation_stage_precedes_cleanup": True, "cleanup_failure_rc": 2}:
        raise IntegrityError("close-only contract drift")
    if cfg.get("observation_contract") != {"status": OBSERVATION_STATUS,
                                             "exact_payload_files": list(OBSERVATION_FILES),
                                             "manifest_self_excluded": True,
                                             "directory_basename_is_payload_sha256": True,
                                             "preexisting_attempt_namespace_forbidden": True,
                                             "scientific_call_count": 72}:
        raise IntegrityError("observation contract drift")
    if cfg.get("cleanup_signal_contract") != {
            "signals": ["SIGTERM", "SIGINT"], "controller_precedes_handle_ownership": True,
            "covers_constructor_probe_stage_cleanup_and_terminal_structure": True,
            "pthread_mask_required": True, "deferred_handler_installed_under_mask": True,
            "cleanup_not_interrupted": True, "production_handler_retained_until_process_exit": True,
            "test_only_restore_is_process_isolated": True,
            "pending_signal_replayed_after_cleanup": True, "primary_exception_preserved": True,
            "pending_signal_structured_secondary_when_primary_exists": True,
            "machine_evidence_exact_delta_reconcile": True,
            "repeated_signums_preserved": True,
            "event_schema": ["signum", "name", "order", "timestamp_monotonic_ns"],
            "terminal_current_commit_masked": True,
            "production_terminal_mask_retained_to_process_exit": True,
            "terminal_linearization_point": "final_postreplace_drain_and_check",
            "post_linearization_signals_remain_os_pending": True,
            "commit_window_signal_supersedes_science_terminal": True,
            "supersession_failure_authority_revalidated": True,
            "supersession_failure_fallback_is_previous_running": True,
            "sigkill_cleanup_or_artifact_guarantee": False}:
        raise IntegrityError("cleanup signal contract drift")
    parent = cfg.get("parent_job_identity", {})
    if parent.get("slurm_job_id") != "11533175" or parent.get("exp_id") != "SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1":
        raise IntegrityError("parent Job11533175 identity drift")
    expected_scheduler = {"partition": cfg["slurm_contract"]["partition"],
                          "time_limit": cfg["slurm_contract"]["time_limit"],
                          "num_cpus": cfg["slurm_contract"]["num_cpus"],
                          "memory": "4G", "gpus": cfg["slurm_contract"]["gpus"],
                          "exact_tres": cfg["slurm_contract"]["exact_tres"]}
    if parent.get("audited_scheduler") != expected_scheduler:
        raise IntegrityError("Job11533175 scheduler identity drift")


def validate_small_assets(root, cfg):
    s = cfg["source_contract"]
    rels = {s["rmlib_config"]: s["rmlib_config_sha256"],
            s["layout_manifest"]: s["layout_manifest_sha256"],
            s["evaluator_contract"]: s["evaluator_contract_sha256"]}
    for rel, want in rels.items():
        p = root / rel
        if not p.is_file() or p.is_symlink() or sha256_file(p) != want:
            raise IntegrityError("small source asset hash mismatch: " + rel)
    for name, want in s["famdb_code_sha256"].items():
        p = Path(s["famdb_code_dir"]) / name
        if not p.is_file() or p.is_symlink() or sha256_file(p) != want:
            raise IntegrityError("FamDB code hash mismatch: " + name)
    parent = cfg["parent_job_identity"]
    for rel, want in parent["artifacts"].items():
        p = root / rel
        if not p.is_file() or p.is_symlink() or sha256_file(p) != want:
            raise IntegrityError("Job11533175 evidence hash mismatch: " + rel)
    old_cfg = root / "configs" / (parent["exp_id"] + ".yaml")
    if not old_cfg.is_file() or old_cfg.is_symlink() or sha256_file(old_cfg) != parent["audited_science_config_sha256"]:
        raise IntegrityError("Job11533175 scientific config hash mismatch")
    old = json.loads(old_cfg.read_text())
    science_source_keys = ("famdb_dir", "rmlib_config", "rmlib_config_sha256", "layout_manifest",
                           "layout_manifest_sha256", "evaluator_contract", "evaluator_contract_sha256",
                           "famdb_code_dir", "famdb_code_sha256", "partition_sizes",
                           "partition_stat_contract_sha256", "partition_stat_contract", "expected_partition_order")
    if old.get("selected_records") != cfg.get("selected_records") or any(
            old["source_contract"].get(k) != cfg["source_contract"].get(k) for k in science_source_keys):
        raise IntegrityError("Job11533175 scientific/source payload was not reused exactly")


def validate_source(root, cfg):
    validate_small_assets(root, cfg)
    s = cfg["source_contract"]
    layout = json.loads((root / s["layout_manifest"]).read_text())
    rows = layout.get("partitions")
    if not isinstance(rows, list):
        raise IntegrityError("layout manifest schema drift")
    by_part = {x.get("partition"): x for x in rows}
    expected_parts = s["expected_partition_order"]
    if sorted(by_part) != sorted(expected_parts) or len(by_part) != len(rows):
        raise IntegrityError("layout partition exact set/uniqueness drift")
    famdb_dir = root / s["famdb_dir"]
    stat_contract = s.get("partition_stat_contract")
    if not isinstance(stat_contract, dict) or set(stat_contract) != {str(x) for x in expected_parts} or \
       sha256_bytes(canonical_json(stat_contract).encode()) != s.get("partition_stat_contract_sha256"):
        raise IntegrityError("partition stat contract schema/hash drift")
    observed = []
    for part in expected_parts:
        name = "dfam39_full.%d.h5" % part
        p = famdb_dir / name
        want = s["partition_sizes"][str(part)]
        contract = stat_contract[str(part)]
        if not p.is_symlink(): raise IntegrityError("partition symlink missing: " + name)
        lst = p.lstat(); target = os.readlink(p); resolved = p.resolve(strict=True); st = resolved.stat()
        actual = {"filename": name, "symlink_target": target,
                  "symlink_target_sha256": sha256_bytes(target.encode()), "symlink_inode": lst.st_ino,
                  "symlink_mtime_ns": lst.st_mtime_ns, "symlink_mode": lst.st_mode,
                  "resolved_size": st.st_size, "resolved_inode": st.st_ino,
                  "resolved_mtime_ns": st.st_mtime_ns, "resolved_mode": st.st_mode}
        if actual != contract or resolved.name != name or st.st_size != want:
            raise IntegrityError("partition identity/size drift: " + name)
        row = by_part[part]
        if row.get("filename") != name or row.get("size_bytes") != want:
            raise IntegrityError("layout size/name drift: " + name)
        observed.append({"partition": part, "filename": name, "size_bytes": st.st_size,
                         "inode": st.st_ino, "mtime_ns": st.st_mtime_ns, "mode": st.st_mode})
    return {"rmlib_config_sha256": s["rmlib_config_sha256"],
            "layout_manifest_sha256": s["layout_manifest_sha256"], "partitions": observed}


def package_hashes(root):
    rels = ["configs/%s.yaml" % EXP_ID,
            "scripts/experiments/%s/close_only_probe.py" % EXP_ID,
            "scripts/experiments/%s/test_close_only_probe.py" % EXP_ID,
            "sbatch/%s.sbatch" % EXP_ID, "docs/experiments/%s.md" % EXP_ID]
    return {rel: sha256_file(root / rel) for rel in rels}


def parse_mem_mib(value):
    m = re.fullmatch(r"([0-9]+)([KMG]?)", str(value).upper())
    if not m: raise IntegrityError("invalid Slurm memory")
    number, unit = int(m.group(1)), m.group(2)
    if unit == "K":
        if number % 1024: raise IntegrityError("Slurm memory K value is not integral MiB")
        return number // 1024
    return number * {"": 1, "M": 1, "G": 1024}[unit]


def validate_resource_env(env):
    if not re.fullmatch(r"[1-9][0-9]*", env.get("SLURM_JOB_ID", "")):
        raise IntegrityError("positive numeric SLURM_JOB_ID required")
    if env.get("SLURM_CPUS_PER_TASK") != "1" or parse_mem_mib(env.get("SLURM_MEM_PER_NODE", "")) != 4096:
        raise IntegrityError("exact 1 CPU/4096 MiB required")
    if env.get("SLURM_JOB_PARTITION") != "private-teodoro-gpu":
        raise IntegrityError("exact private partition required")
    if any(env.get(k, "").strip() not in {"", "NoDevFiles"}
           for k in ("CUDA_VISIBLE_DEVICES", "SLURM_GPUS", "SLURM_JOB_GPUS", "SLURM_GPUS_ON_NODE")):
        raise IntegrityError("0 GPU required")


def run_bounded(cmd, timeout):
    proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try: os.killpg(proc.pid, signal.SIGKILL)
        finally: proc.communicate()
        raise IntegrityError("bounded child timeout") from exc
    return proc.returncode, out, err


def parse_scontrol(text):
    if not text.endswith("\n") or text.count("\n") != 1 or len(text.encode()) > 1024 * 1024:
        raise IntegrityError("invalid scontrol one-line output")
    line = text[:-1]; matches = list(re.finditer(r"(?:^| )([A-Za-z][A-Za-z0-9/:]*)=", line)); fields = {}
    for i, match in enumerate(matches):
        key = match.group(1); end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        if key in fields: raise IntegrityError("duplicate scontrol field")
        fields[key] = line[match.end():end].strip()
    return fields


def parse_tres(value, expected):
    if not isinstance(value, str) or not value or any(ch.isspace() for ch in value):
        raise IntegrityError("TRES empty/whitespace shape")
    parsed = {}
    for token in value.split(","):
        if token.count("=") != 1:
            raise IntegrityError("TRES malformed token")
        key, item = token.split("=", 1)
        if not key or not item or key in parsed:
            raise IntegrityError("TRES duplicate/empty key")
        if key not in expected:
            raise IntegrityError("TRES unknown key: " + key)
        parsed[key] = item
    if parsed != expected:
        raise IntegrityError("TRES exact resource mismatch")
    return parsed


def query_slurm(root, cfg, env, executor=None):
    validate_resource_env(env); c = cfg["slurm_contract"]; job = env["SLURM_JOB_ID"]
    binary = Path(c["scontrol_binary"]); sbatch = root / "sbatch" / (EXP_ID + ".sbatch")
    if not binary.is_file() or binary.is_symlink() or sha256_file(binary) != c["scontrol_sha256"]:
        raise IntegrityError("scontrol identity drift")
    if sbatch.is_symlink() or sbatch.resolve(strict=True) != Path(c["command"]) or sha256_file(sbatch) != c["sbatch_sha256"]:
        raise IntegrityError("sbatch identity drift")
    cmd = ["/usr/bin/timeout", "--signal=TERM", "--kill-after=2s", "%ss" % c["query_timeout_seconds"],
           str(binary), "show", "job", job, "-o"]
    rc, out, err = (executor or run_bounded)(cmd, c["query_timeout_seconds"] + 5)
    if rc or err: raise IntegrityError("scontrol query rc/stderr failure")
    fields = parse_scontrol(out)
    expected = {"JobId": job, "Partition": c["partition"], "TimeLimit": c["time_limit"],
                "NumCPUs": c["num_cpus"], "Command": c["command"], "SubmitLine": c["submit_line"]}
    for key, want in expected.items():
        if fields.get(key) != want: raise IntegrityError("scontrol %s mismatch" % key)
    for key in ("ReqTRES", "AllocTRES"):
        parse_tres(fields.get(key, ""), c["exact_tres"])
    return {"fields": {k: fields[k] for k in sorted(set(expected) | {"ReqTRES", "AllocTRES"})},
            "stdout_sha256": sha256_bytes(out.encode()), "command": cmd}


def validate_review_gate(root, cfg):
    path = root / cfg["code_review_gate_path"]
    if not path.is_file() or path.is_symlink(): raise IntegrityError("review gate missing")
    gate = json.loads(path.read_text())
    if gate.get("exp_id") != EXP_ID or gate.get("verdict") not in {"PASS", "PASS_WITH_WARNINGS"} or \
       isinstance(gate.get("blockers_open"), bool) or gate.get("blockers_open") != 0:
        raise IntegrityError("review gate verdict/schema invalid")
    reviewed = gate.get("reviewed_files")
    if not isinstance(reviewed, dict): raise IntegrityError("reviewed_files must be dict")
    package = package_hashes(root)
    for rel, want in reviewed.items():
        rp = Path(rel)
        if rp.is_absolute() or ".." in rp.parts or not re.fullmatch(r"[0-9a-f]{64}", str(want)):
            raise IntegrityError("unsafe reviewed file")
        p = root / rel
        if not p.is_file() or p.is_symlink() or sha256_file(p) != want:
            raise IntegrityError("stale reviewed file")
    if not set(package).issubset(reviewed): raise IntegrityError("review package incomplete")
    return sha256_file(path)


def validate_owner(root, cfg, env):
    lock = root / cfg["preview_root"] / cfg["owner_lock_name"]
    if lock.is_symlink() or not lock.is_dir() or {x.name for x in lock.iterdir()} != {"job_id"}:
        raise IntegrityError("owner lock invalid")
    p = lock / "job_id"; job = p.read_text().strip()
    if p.is_symlink() or job != env["SLURM_JOB_ID"] or not re.fullmatch(r"[1-9][0-9]*", job):
        raise IntegrityError("owner/job mismatch")
    return sha256_file(p)


def family_row(family, partition, queried_accession):
    required = ("accession", "version", "name", "repeat_type", "repeat_subtype", "consensus")
    if family is None: return None
    if any(not hasattr(family, x) for x in required) or not callable(getattr(family, "accession_with_optional_version", None)):
        raise IntegrityError("FamDB Family API/schema drift")
    if not isinstance(family.accession, str) or \
       (family.version is not None and (not isinstance(family.version, numbers.Integral) or isinstance(family.version, bool))):
        raise IntegrityError("FamDB accession/version type drift")
    for value in (family.name, family.repeat_type, family.repeat_subtype, family.consensus):
        if value is not None and not isinstance(value, str): raise IntegrityError("FamDB Family field type drift")
    seq = (family.consensus or "").upper().replace("U", "T")
    raw_class = (family.repeat_type or "") + (("/" + family.repeat_subtype) if family.repeat_subtype else "")
    return {"queried_accession": queried_accession, "partition": partition,
            "accession": family.accession, "versioned_accession": family.accession_with_optional_version(),
            "canonical_name": family.name or "", "raw_class": raw_class,
            "consensus_length": len(seq), "consensus_sha256": sha256_bytes(seq.encode())}


def evaluate_observations(cfg, observations, raise_on_block=True):
    parts = cfg["source_contract"]["expected_partition_order"]; selected = cfg["selected_records"]
    keys = [(x.get("queried_accession"), x.get("partition")) for x in observations]
    expected_keys = [(r["accession"], p) for r in selected for p in parts]
    if len(keys) != len(set(keys)) or sorted(keys) != sorted(expected_keys):
        raise IntegrityError("probe matrix is not exact 6x12")
    resolved, failures = [], []
    for expected in selected:
        hits = [x["record"] for x in observations if x["queried_accession"] == expected["accession"] and x["record"]]
        if len(hits) != 1:
            failures.append({"accession": expected["accession"], "reason": "missing" if not hits else "duplicate",
                             "match_count": len(hits)}); continue
        hit = hits[0]; drift = [k for k in ("accession", "versioned_accession", "canonical_name", "raw_class",
                                             "consensus_length", "consensus_sha256", "partition") if hit.get(k) != expected[k]]
        if drift:
            failures.append({"accession": expected["accession"], "reason": "field_drift", "fields": drift}); continue
        resolved.append(hit)
    metrics = {"target_count": 6, "partition_count": 12, "probe_call_count": len(observations),
               "resolved_count": len(resolved), "blocked_count": len(failures),
               "exact_once_across_partitions": not failures, "fallback_count": 0,
               "route_stop": bool(failures)}
    audit = {"observations": observations, "failures": failures}
    if failures and raise_on_block: raise TypedBlock(metrics, audit, resolved)
    return metrics, audit, resolved


def probe_leaf_mapping(cfg, files):
    expected_parts = cfg["source_contract"]["expected_partition_order"]
    if sorted(files) != sorted(expected_parts): raise IntegrityError("FamDB leaf exact partition set drift")
    observations = []
    for target in cfg["selected_records"]:
        for part in expected_parts:
            leaf = files[part]
            method = getattr(leaf, "get_family_by_accession", None)
            if not callable(method): raise IntegrityError("FamDBLeaf exact API drift")
            family = method(target["accession"])
            observations.append({"queried_accession": target["accession"], "partition": part,
                                 "record": family_row(family, part, target["accession"])})
    return evaluate_observations(cfg, observations, raise_on_block=False)


def inspect_leaf_mapping(files, cfg, require_exact=True):
    """Return valid frozen-key leaves and all mapping/identity defects."""
    parts = cfg["source_contract"]["expected_partition_order"]
    errors, valid = [], []
    if not isinstance(files, dict):
        return valid, [{"error": "leaf mapping is not a dict"}]
    for key in files:
        if isinstance(key, bool) or not isinstance(key, int):
            errors.append({"key_repr": repr(key), "error": "non-integer partition key"})
        elif key not in parts:
            errors.append({"partition": key, "error": "unexpected partition key"})
    present = [part for part in parts if part in files]
    if require_exact and present != parts:
        errors.append({"missing_partitions": [part for part in parts if part not in files],
                       "error": "partial frozen partition keyset"})
    leaf_owner, handle_owner = {}, {}
    for part in present:
        leaf = files[part]
        leaf_id = id(leaf)
        if leaf_id in leaf_owner:
            errors.append({"partition": part, "first_partition": leaf_owner[leaf_id], "error": "shared leaf identity"})
        else:
            leaf_owner[leaf_id] = part
        if not hasattr(leaf, "file"):
            errors.append({"partition": part, "error": "missing file handle"})
            continue
        handle = leaf.file
        handle_id = id(handle)
        if handle_id in handle_owner:
            errors.append({"partition": part, "first_partition": handle_owner[handle_id], "error": "shared handle identity"})
        else:
            handle_owner[handle_id] = part
        valid.append((part, leaf, handle))
    return valid, errors


def close_leaf_handles(files, cfg, allow_preclosed=False):
    """Attempt every present frozen-key handle; each unique handle is touched at most once."""
    parts = cfg["source_contract"]["expected_partition_order"]
    _lifecycle_event("close_before")
    leaf_rows, errors = inspect_leaf_mapping(files, cfg, require_exact=True)
    rows, seen_handles, close_invocations, interrupt = [], set(), 0, None
    for part, _leaf, handle in leaf_rows:
        handle_id = id(handle)
        if handle_id in seen_handles:
            continue
        seen_handles.add(handle_id)
        method = getattr(handle, "close", None)
        if not callable(method):
            errors.append({"partition": part, "error": "file.close is not callable"})
            continue
        try:
            before = getattr(getattr(handle, "id", None), "valid", None)
            if before in (0, False):
                if allow_preclosed:
                    rows.append({"partition": part, "explicit_file_close_called": False,
                                 "closed": True, "recovered_preclosed": True})
                    continue
                raise RuntimeError("HDF5 handle was already closed")
            close_invocations += 1
            method()
            _lifecycle_event("close_inside")
            after = getattr(getattr(handle, "id", None), "valid", None)
            if after not in (0, False):
                raise RuntimeError("HDF5 handle remains valid after close")
            rows.append({"partition": part, "explicit_file_close_called": True, "closed": True})
        except BaseException as exc:
            errors.append({"partition": part, "error_type": type(exc).__name__, "error": str(exc)})
            if isinstance(exc, TerminationRequested) and interrupt is None:
                interrupt = exc
    audit = {"expected_handle_count": 12, "present_frozen_key_count": len(leaf_rows),
             "unique_handle_count": len(seen_handles), "close_attempt_count": close_invocations,
             "closed_count": len(rows), "rows": rows, "errors": errors}
    if interrupt is not None:
        interrupt.cleanup_all_handles_processed = True
        interrupt.close_audit = audit
        raise interrupt
    if errors or len(rows) != 12 or len(seen_handles) != 12:
        raise CleanupError("one or more explicit HDF5 handle closes failed", close_audit=audit)
    return audit


def attach_cleanup_secondary(primary, secondary):
    if isinstance(secondary, CleanupError):
        detail = {"error_type": type(secondary).__name__, "error": str(secondary),
                  "close_audit": secondary.close_audit}
    else:
        detail = {"error_type": type(secondary).__name__, "error": str(secondary),
                  "close_audit": getattr(secondary, "close_audit", None)}
    current = getattr(primary, "cleanup_secondary", [])
    try:
        primary.cleanup_secondary = list(current) + [detail]
    except BaseException:
        pass


class DeferredCleanupSignals:
    """Process-level termination controller entered before handle ownership exists."""
    SIGNALS = (signal.SIGTERM, signal.SIGINT)

    def __init__(self):
        self.pending = []; self.pending_events = []; self.previous_handlers = {}; self.previous_mask = None
        self.active = False; self.terminal_mask_retained = False

    def _record(self, signum, _frame=None):
        value = int(signum); self.pending.append(value)
        self.pending_events.append({"signum": value, "name": signal_name(value),
                                    "order": len(self.pending_events) + 1,
                                    "timestamp_monotonic_ns": time.monotonic_ns()})

    def enter(self):
        if self.active: raise IntegrityError("deferred cleanup signal guard re-entry")
        if not hasattr(signal, "pthread_sigmask"):
            raise IntegrityError("pthread_sigmask required for cleanup signal safety")
        blocked_before = signal.pthread_sigmask(signal.SIG_BLOCK, self.SIGNALS)
        self.previous_mask = blocked_before
        try:
            for signum in self.SIGNALS:
                self.previous_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, self._record)
            self.active = True
        except BaseException:
            for signum, handler in self.previous_handlers.items():
                signal.signal(signum, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, blocked_before)
            raise
        # Pending TERM/INT received during installation is delivered only to _record.
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked_before)
        return self

    def pending_rows(self):
        return [dict(row) for row in self.pending_events]

    def drain_masked(self):
        """Move every currently pending TERM/INT into ordered machine evidence."""
        if not self.active or not hasattr(signal, "sigtimedwait"):
            raise IntegrityError("active deferred controller with sigtimedwait required")
        while True:
            info = signal.sigtimedwait(self.SIGNALS, 0)
            if info is None: break
            self._record(int(info.si_signo))
        return self.pending_rows()

    def begin_terminal_commit(self):
        """Block TERM/INT for terminal commit and retain the mask to process exit."""
        if not self.active: raise IntegrityError("active deferred controller required for commit")
        previous = signal.pthread_sigmask(signal.SIG_BLOCK, self.SIGNALS)
        if self.terminal_mask_retained:
            if not set(self.SIGNALS).issubset(set(previous)):
                raise IntegrityError("retained terminal mask drift")
        else:
            self.terminal_mask_retained = True
        self.drain_masked()

    def raise_if_pending(self, cleanup_secondary=None):
        if not self.pending: return
        term = TerminationRequested("deferred ownership-envelope signal(s): " +
                                    ",".join(str(x) for x in self.pending))
        reconcile_pending_signals(term, self)
        if cleanup_secondary is not None: attach_cleanup_secondary(term, cleanup_secondary)
        raise term

    def restore_for_tests(self, event_hook=None):
        """Test-only restore; production keeps deferred handlers until process exit."""
        if not self.active: raise IntegrityError("deferred cleanup signal guard not active")
        signal.pthread_sigmask(signal.SIG_BLOCK, self.SIGNALS)
        try:
            # Drain signals arriving in the restore window while our deferred handler remains installed.
            if hasattr(signal, "sigtimedwait"):
                while True:
                    info = signal.sigtimedwait(self.SIGNALS, 0)
                    if info is None: break
                    self._record(int(info.si_signo))
            if event_hook: event_hook("controller_restore_handlers")
            # A deterministic signal injected at the restore line is still pending under our mask.
            if hasattr(signal, "sigtimedwait"):
                while True:
                    info = signal.sigtimedwait(self.SIGNALS, 0)
                    if info is None: break
                    self._record(int(info.si_signo))
            for signum in self.SIGNALS:
                signal.signal(signum, self.previous_handlers[signum])
            self.active = False; self.terminal_mask_retained = False
        finally:
            if event_hook: event_hook("controller_restore_mask")
            # Drain deterministic line-event injections before the final test-only unmask.
            if hasattr(signal, "sigtimedwait"):
                while True:
                    info = signal.sigtimedwait(self.SIGNALS, 0)
                    if info is None: break
                    self._record(int(info.si_signo))
            signal.pthread_sigmask(signal.SIG_SETMASK, self.previous_mask)
        return list(self.pending)


def signal_name(signum):
    return {int(signal.SIGTERM): "SIGTERM", int(signal.SIGINT): "SIGINT"}.get(int(signum), "UNKNOWN")


def validate_signal_events(rows):
    if not isinstance(rows, list): raise IntegrityError("pending signal evidence must be a list")
    previous_time = -1
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != {
                "signum", "name", "order", "timestamp_monotonic_ns"}:
            raise IntegrityError("pending signal event schema drift")
        signum = row["signum"]
        if isinstance(signum, bool) or signum not in {int(signal.SIGTERM), int(signal.SIGINT)} or \
           row["name"] != signal_name(signum) or isinstance(row["order"], bool) or row["order"] != index or \
           isinstance(row["timestamp_monotonic_ns"], bool) or \
           not isinstance(row["timestamp_monotonic_ns"], int) or \
           row["timestamp_monotonic_ns"] <= 0 or row["timestamp_monotonic_ns"] < previous_time:
            raise IntegrityError("pending signal event identity/order/time drift")
        previous_time = row["timestamp_monotonic_ns"]
    return rows


def reconcile_pending_signals(primary, controller):
    """Append only controller events not already present as an exact evidence prefix."""
    controller_rows = validate_signal_events(controller.pending_rows())
    existing = getattr(primary, "pending_cleanup_signals", [])
    existing = validate_signal_events(existing)
    if len(existing) > len(controller_rows) or existing != controller_rows[:len(existing)]:
        raise IntegrityError("exception pending signal evidence is not a controller prefix")
    merged = existing + controller_rows[len(existing):]
    primary.pending_cleanup_signals = merged
    return controller_rows[len(existing):]


class HandleLifecycle:
    """Own every handle from before construction until exact-once cleanup completes."""
    def __init__(self, cfg):
        self.cfg = cfg; self.db = None; self.cleanup_done = False; self.close_audit = None
        self.observation_bundle = None; self.observation_manifest_sha256 = None
        self.expected_observation_bundle = None; self.expected_observation_sha256 = None

    def attach_db(self, db):
        self.db = db

    def register_expected_observation(self, bundle, payload_sha):
        self.expected_observation_bundle = Path(bundle); self.expected_observation_sha256 = payload_sha

    def capture_observation(self, attempt):
        if self.observation_bundle is not None or self.expected_observation_bundle is None:
            return
        try:
            digest = verify_observation_bundle(self.expected_observation_bundle, expected_attempt=attempt)
        except BaseException:
            return
        self.observation_bundle = self.expected_observation_bundle
        self.observation_manifest_sha256 = digest

    def ensure_cleanup(self, primary=None, attempt=None):
        deferred = None
        _lifecycle_event("cleanup_guard_entered")
        if not self.cleanup_done and self.db is None:
            self.cleanup_done = True
        retry = False
        while not self.cleanup_done:
            try:
                self.close_audit = close_leaf_handles(getattr(self.db, "files", None), self.cfg,
                                                      allow_preclosed=retry)
                self.cleanup_done = True
            except CleanupError as exc:
                self.cleanup_done = True; deferred = exc
            except BaseException as exc:
                if getattr(exc, "cleanup_all_handles_processed", False):
                    self.cleanup_done = True; self.close_audit = getattr(exc, "close_audit", None); deferred = exc
                else:
                    if deferred is None: deferred = exc
                    else: attach_cleanup_secondary(deferred, exc)
                    retry = True
                    continue
        self.capture_observation(attempt)
        if primary is not None:
            if deferred is not None and deferred is not primary:
                attach_cleanup_secondary(primary, deferred)
            return
        if deferred is not None:
            raise deferred


def probe_installed_open(root, cfg, lifecycle):
    code = cfg["source_contract"]["famdb_code_dir"]
    sys.path.insert(0, code)
    try:
        module = importlib.import_module("famdb_classes")
        cls = getattr(module, "FamDB", None)
        if cls is None: raise IntegrityError("FamDB class API drift")
        _lifecycle_event("constructor_before")
        db = cls.__new__(cls)
        lifecycle.attach_db(db)
        cls.__init__(db, str(root / cfg["source_contract"]["famdb_dir"]), "r")
        _lifecycle_event("constructor_after")
        files = getattr(db, "files", None)
        _lifecycle_event("probe_inside")
        _valid, mapping_errors = inspect_leaf_mapping(files, cfg, require_exact=True)
        if mapping_errors:
            raise IntegrityError("FamDB leaf identity/mapping drift: " + canonical_json(mapping_errors).strip())
        result = probe_leaf_mapping(cfg, files)
        if result[0].get("probe_call_count") != 72:
            raise IntegrityError("formal scientific call count is not exactly 72")
        return result
    finally:
        if sys.path and sys.path[0] == code:
            sys.path.pop(0)
        elif code in sys.path:
            sys.path.remove(code)


def safe_attempt_id(attempt):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(attempt))[:128]
    if not safe or safe in {".", ".."}:
        raise IntegrityError("unsafe attempt id")
    return safe


def observation_payload_hash(payload_by_name):
    if set(payload_by_name) != set(OBSERVATION_FILES):
        raise IntegrityError("observation payload exact file set drift")
    return sha256_bytes(b"".join(name.encode() + b"\0" + payload_by_name[name]
                                 for name in sorted(payload_by_name)))


def build_observation_payload(metrics, audit, resolved):
    return {
        "leaf_probe_matrix.json": canonical_json(audit).encode(),
        "exact_records.json": canonical_json(resolved).encode(),
        "metrics.precleanup.json": canonical_json(dict(metrics, observation_stage="PRECLEANUP_FROZEN")).encode(),
    }


def expected_observation_identity(preview, attempt, metrics, audit, resolved):
    payload = build_observation_payload(metrics, audit, resolved)
    payload_hash = observation_payload_hash(payload)
    return Path(preview) / "attempt_observations" / safe_attempt_id(attempt) / payload_hash, payload_hash


def no_symlink_ancestors(path):
    absolute = Path(path).absolute()
    chain = list(reversed(absolute.parents)) + [absolute]
    for item in chain:
        if item.is_symlink():
            raise IntegrityError("observation path contains symlink ancestor")


def verify_observation_bundle(bundle, expected_attempt=None):
    bundle = Path(bundle)
    no_symlink_ancestors(bundle)
    if bundle.is_symlink() or not bundle.is_dir():
        raise IntegrityError("observation bundle missing")
    if any(p.is_symlink() or p.is_dir() for p in bundle.iterdir()):
        raise IntegrityError("observation bundle contains symlink/directory entry")
    manifest_path = bundle / "OBSERVATION_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    entries = manifest.get("files")
    if set(manifest) != {"schema_version", "exp_id", "attempt_id", "status", "scientific_call_count",
                         "payload_sha256", "files"} or manifest.get("schema_version") != SCHEMA or \
       manifest.get("exp_id") != EXP_ID or manifest.get("status") != OBSERVATION_STATUS or \
       manifest.get("scientific_call_count") != 72 or isinstance(manifest.get("scientific_call_count"), bool) or \
       not isinstance(manifest.get("attempt_id"), str) or not isinstance(entries, list):
        raise IntegrityError("observation manifest schema drift")
    if expected_attempt is not None and manifest["attempt_id"] != expected_attempt:
        raise IntegrityError("observation attempt identity drift")
    if safe_attempt_id(manifest["attempt_id"]) != bundle.parent.name:
        raise IntegrityError("observation attempt directory drift")
    if len(entries) != len(OBSERVATION_FILES) or any(not isinstance(x, dict) for x in entries):
        raise IntegrityError("observation manifest path drift")
    names = [x.get("path") for x in entries]
    if set(names) != set(OBSERVATION_FILES) or len(names) != len(set(names)) or \
       any(set(x) != {"path", "size", "sha256"} for x in entries) or \
       any(not isinstance(x, str) or "/" in x or x in {"", ".", "..", "OBSERVATION_MANIFEST.json"} for x in names):
        raise IntegrityError("observation manifest path drift")
    expected = set(names) | {"OBSERVATION_MANIFEST.json"}
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    if expected != actual or any(p.is_symlink() or p.is_dir() for p in bundle.rglob("*")):
        raise IntegrityError("observation bundle exact file set failure")
    payload = {}
    for row in entries:
        p = bundle / row["path"]
        if isinstance(row.get("size"), bool) or not isinstance(row.get("size"), int) or row["size"] < 0 or \
           not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256"))) or \
           p.stat().st_size != row["size"] or sha256_file(p) != row["sha256"]:
            raise IntegrityError("observation bundle payload hash failure")
        payload[row["path"]] = p.read_bytes()
    payload_sha = observation_payload_hash(payload)
    if manifest.get("payload_sha256") != payload_sha or bundle.name != payload_sha:
        raise IntegrityError("observation payload/directory identity drift")
    try:
        matrix = json.loads(payload["leaf_probe_matrix.json"])
        resolved = json.loads(payload["exact_records.json"])
        metrics = json.loads(payload["metrics.precleanup.json"])
    except Exception as exc:
        raise IntegrityError("observation JSON parse failure") from exc
    if not isinstance(matrix, dict) or set(matrix) != {"observations", "failures"} or not isinstance(matrix["failures"], list):
        raise IntegrityError("observation matrix schema drift")
    observations = matrix["observations"]
    record_keys = {"queried_accession", "partition", "accession", "versioned_accession", "canonical_name",
                   "raw_class", "consensus_length", "consensus_sha256"}
    if not isinstance(observations, list) or len(observations) != 72 or \
       any(not isinstance(x, dict) or set(x) != {"queried_accession", "partition", "record"} for x in observations) or \
       len({(x["queried_accession"], x["partition"]) for x in observations}) != 72 or \
       any(x["record"] is not None and (not isinstance(x["record"], dict) or set(x["record"]) != record_keys)
           for x in observations) or not isinstance(resolved, list) or \
       any(not isinstance(x, dict) or set(x) != record_keys for x in resolved) or \
       len({canonical_json(x) for x in resolved}) != len(resolved) or \
       not isinstance(metrics, dict) or metrics.get("probe_call_count") != 72 or \
       metrics.get("observation_stage") != "PRECLEANUP_FROZEN" or metrics.get("resolved_count") != len(resolved):
        raise IntegrityError("observation semantic shape drift")
    observed_records = [x.get("record") for x in observations if isinstance(x, dict) and x.get("record") is not None]
    if any(row not in observed_records for row in resolved):
        raise IntegrityError("resolved rows are not contained in probe observations")
    return sha256_file(manifest_path)


def stage_observations(preview, attempt, metrics, audit, resolved):
    """Atomically freeze complete scientific observations before any handle cleanup."""
    preview = Path(preview); safe = safe_attempt_id(attempt)
    no_symlink_ancestors(preview)
    payload = build_observation_payload(metrics, audit, resolved)
    payload_hash = observation_payload_hash(payload)
    parent = preview / "attempt_observations" / safe
    target = parent / payload_hash
    parent.mkdir(parents=True, exist_ok=True)
    no_symlink_ancestors(parent)
    if any(parent.iterdir()):
        raise IntegrityError("dirty attempt observation namespace")
    stage = parent / ("." + payload_hash + ".tmp")
    stage.mkdir()
    try:
        _lifecycle_event("stage_inside")
        for name, data in payload.items():
            atomic_write(stage / name, data)
        entries = [{"path": name, "size": (stage / name).stat().st_size, "sha256": sha256_file(stage / name)}
                   for name in sorted(payload)]
        write_json(stage / "OBSERVATION_MANIFEST.json",
                   {"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt,
                    "status": OBSERVATION_STATUS,
                    "scientific_call_count": metrics["probe_call_count"], "payload_sha256": payload_hash,
                    "files": entries})
        for p in stage.iterdir():
            p.chmod(0o444)
        os.replace(stage, target)
        _lifecycle_event("stage_after_promote")
        target.chmod(0o555)
    except Exception:
        if stage.exists():
            for p in stage.iterdir():
                p.chmod(0o644)
                p.unlink()
            stage.rmdir()
        raise
    return target, verify_observation_bundle(target, expected_attempt=attempt)


def execute_probe_stage_cleanup(root, cfg, preview, attempt, termination_controller):
    """One ownership envelope for construction, probe, staging, and cleanup."""
    if not isinstance(termination_controller, DeferredCleanupSignals) or not termination_controller.active:
        raise IntegrityError("active process-level termination controller required before handle ownership")
    lifecycle = HandleLifecycle(cfg); primary = None
    traceback_obj = None; result = None; cleanup_error = None
    try:
        metrics, audit, resolved = probe_installed_open(root, cfg, lifecycle)
        _lifecycle_event("after_probe")
        expected_bundle, expected_sha = expected_observation_identity(preview, attempt, metrics, audit, resolved)
        lifecycle.register_expected_observation(expected_bundle, expected_sha)
        _lifecycle_event("before_stage")
        bundle, digest = stage_observations(preview, attempt, metrics, audit, resolved)
        lifecycle.observation_bundle = bundle; lifecycle.observation_manifest_sha256 = digest
        _lifecycle_event("after_stage")
        lifecycle.ensure_cleanup(attempt=attempt)
        _lifecycle_event("postclose")
        result = ((metrics, audit, resolved), lifecycle)
    except BaseException as exc:
        primary = exc; traceback_obj = exc.__traceback__
    finally:
        try:
            lifecycle.ensure_cleanup(primary=primary, attempt=attempt)
        except BaseException as exc:
            cleanup_error = exc
        if primary is not None:
            if lifecycle.observation_bundle is not None:
                try:
                    primary.observation_bundle = lifecycle.observation_bundle
                    primary.observation_manifest_sha256 = lifecycle.observation_manifest_sha256
                except BaseException:
                    pass
            if lifecycle.close_audit is not None:
                try: primary.close_audit = lifecycle.close_audit
                except BaseException: pass
            reconcile_pending_signals(primary, termination_controller)
            if cleanup_error is not None: attach_cleanup_secondary(primary, cleanup_error)
    if primary is not None:
        raise primary.with_traceback(traceback_obj)
    termination_controller.raise_if_pending(cleanup_secondary=cleanup_error)
    if cleanup_error is not None: raise cleanup_error
    return result


@contextlib.contextmanager
def writer_mutex(preview):
    preview = Path(preview); preview.mkdir(parents=True, exist_ok=True)
    with (preview / ".state-writer.lock").open("a+") as fh:
        try: fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise IntegrityError("state writer busy") from exc
        try: yield
        finally: fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def current_bytes(preview):
    p = Path(preview) / "CURRENT"; return p.read_bytes() if p.is_file() else None


def _build_state_bundle(preview, attempt, status, semantic, files):
    """Materialize one immutable state bundle without changing CURRENT."""
    preview = Path(preview)
    states = preview / "states"; states.mkdir(parents=True, exist_ok=True)
    bundle_id = "%s-%s-%d" % (attempt, status.lower(), time.time_ns()); stage = states / ("." + bundle_id + ".tmp")
    final = states / bundle_id; stage.mkdir()
    for name, value in files.items():
        p = stage / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value if isinstance(value, bytes) else str(value).encode())
    auth = dict(AUTH_FALSE, leaf_adapter_preflight_human_gate_eligible=(status == "LEAF_CLOSE_ONLY_PASS"))
    write_json(stage / "STATUS.json", {"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt,
                                       "status": status, "semantic_success": semantic, "authorization": auth})
    entries = [{"path": p.relative_to(stage).as_posix(), "size": p.stat().st_size, "sha256": sha256_file(p)}
               for p in sorted(stage.rglob("*")) if p.is_file()]
    write_json(stage / "PAYLOAD_MANIFEST.json", {"schema_version": SCHEMA, "files": entries})
    os.replace(stage, final)
    return final, ("states/%s\n" % bundle_id).encode()


def publish(preview, attempt, status, semantic, files, before_pointer=None, mutex_held=False, expected=None,
            termination_controller=None, termination_failure_builder=None, allow_pending_failure=False):
    """Pointer-last publish; science terminals are signal-aware through the replace itself."""
    preview = Path(preview)
    if not mutex_held:
        with writer_mutex(preview):
            result = publish(preview, attempt, status, semantic, files, before_pointer, True, expected,
                             termination_controller, termination_failure_builder, allow_pending_failure)
        if termination_controller is not None:
            _lifecycle_event("terminal_commit_after_writer_mutex_exit")
            _lifecycle_event("terminal_publish_function_return")
        return result
    final, pointer_bytes = _build_state_bundle(preview, attempt, status, semantic, files)
    if termination_controller is None:
        if before_pointer: before_pointer(final)
        if expected is not None and current_bytes(preview) != expected: raise IntegrityError("CURRENT CAS failed")
        atomic_write(preview / "CURRENT", pointer_bytes)
        return final

    if not isinstance(termination_controller, DeferredCleanupSignals) or not termination_controller.active:
        raise IntegrityError("active termination controller required for signal-aware publish")
    previous_current = current_bytes(preview)
    pass_pointer_changed = False
    termination_controller.begin_terminal_commit()
    _lifecycle_event("terminal_commit_publish_entry")
    termination_controller.drain_masked()
    if semantic and termination_controller.pending_rows():
        termination_controller.raise_if_pending()
    if before_pointer: before_pointer(final)
    _lifecycle_event("terminal_commit_after_callback")
    termination_controller.drain_masked()
    if semantic and termination_controller.pending_rows():
        termination_controller.raise_if_pending()
    if expected is not None and current_bytes(preview) != expected: raise IntegrityError("CURRENT CAS failed")
    _lifecycle_event("terminal_commit_before_current_write")
    termination_controller.drain_masked()
    if semantic and termination_controller.pending_rows():
        termination_controller.raise_if_pending()

    def pre_replace_check():
        termination_controller.drain_masked()
        if semantic and termination_controller.pending_rows():
            termination_controller.raise_if_pending()

    atomic_write(preview / "CURRENT", pointer_bytes, "terminal_current", pre_replace_check)
    pass_pointer_changed = bool(semantic)
    _lifecycle_event("terminal_commit_postreplace_check")
    termination_controller.drain_masked()
    if semantic and termination_controller.pending_rows():
        # A termination arrived after the final pre-replace check. Never leave
        # canonical CURRENT at PASS/typed-block: supersede with a closed failure.
        try:
            if termination_failure_builder is None:
                raise IntegrityError("termination failure builder required")
            failure_files = termination_failure_builder(
                termination_controller.pending_rows(), pass_pointer_changed)
            failure_final, failure_pointer = _build_state_bundle(
                preview, attempt, "LEAF_CLOSE_ONLY_FAILED", False, failure_files)
            termination_controller.drain_masked()
            atomic_write(preview / "CURRENT", failure_pointer,
                         "termination_failure_current", termination_controller.drain_masked)
            termination_controller.drain_masked()
            term = TerminationRequested("termination during canonical terminal commit")
            reconcile_pending_signals(term, termination_controller)
            term.canonical_failure_published = True
            term.commit_superseded = True
            term.pass_pointer_was_temporarily_published = pass_pointer_changed
            term.terminal_failure_bundle = failure_final
            raise term
        except TerminationRequested:
            raise
        except BaseException as exc:
            # The immutable PASS bundle may exist, but canonical truth returns
            # to the previous FORMAL_RUNNING pointer if failure closure cannot be built.
            if previous_current is not None:
                atomic_write(preview / "CURRENT", previous_current)
            elif (preview / "CURRENT").exists():
                (preview / "CURRENT").unlink()
            raise IntegrityError("termination supersession failed; canonical restored") from exc
    if allow_pending_failure:
        termination_controller.drain_masked()
    # This is the terminal linearization point. No production unmask follows:
    # later TERM/INT remains kernel-pending until normal Python process exit.
    _lifecycle_event("terminal_commit_linearized")
    _lifecycle_event("terminal_commit_mask_retained_to_process_exit")
    return final


def verify_bundle(preview):
    preview = Path(preview); rel = (preview / "CURRENT").read_text().strip()
    if not rel.startswith("states/") or ".." in rel: raise IntegrityError("bad CURRENT")
    bundle = preview / rel; manifest = json.loads((bundle / "PAYLOAD_MANIFEST.json").read_text())
    expected = {x["path"] for x in manifest["files"]} | {"PAYLOAD_MANIFEST.json"}
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    if expected != actual or any(p.is_symlink() or p.is_dir() for p in bundle.rglob("*")): raise IntegrityError("bundle exact set failure")
    for x in manifest["files"]:
        p = bundle / x["path"]
        if p.stat().st_size != x["size"] or sha256_file(p) != x["sha256"]: raise IntegrityError("bundle hash failure")
    return json.loads((bundle / "STATUS.json").read_text())


def wrapper_failure_already_closed(preview, attempt):
    try:
        status = verify_bundle(preview)
    except BaseException:
        return False
    return status.get("attempt_id") == attempt and status.get("status") in {
        "LEAF_CLOSE_ONLY_PASS", "LEAF_CLOSE_ONLY_TYPED_BLOCK", "LEAF_CLOSE_ONLY_FAILED"
    }


def static_preview(root, cfg, attempt):
    validate_config(cfg); validate_small_assets(root, cfg); preview = root / cfg["preview_root"]
    (preview / "logs").mkdir(parents=True, exist_ok=True)
    with writer_mutex(preview):
        initial = current_bytes(preview)
        if os.path.lexists(preview / cfg["owner_lock_name"]): raise IntegrityError("formal owner exists")
        if initial is not None and verify_bundle(preview)["status"] != "IMPLEMENTED_NOT_RUN":
            raise IntegrityError("static cannot supersede formal state")
        package = package_hashes(root)
        files = {"metrics.json": canonical_json({"status": "IMPLEMENTED_NOT_RUN", "semantic_success": False}),
                 "report.json": canonical_json({"status": "IMPLEMENTED_NOT_RUN", "real_h5_opened": False,
                                                  "real_famdb_api_called": False}),
                 "RUN_MANIFEST.json": canonical_json({"package_sha256": package})}
        def cas(_):
            if current_bytes(preview) != initial or os.path.lexists(preview / cfg["owner_lock_name"]):
                raise IntegrityError("static CAS/owner failure")
        return publish(preview, attempt, "IMPLEMENTED_NOT_RUN", False, files, cas, True, initial)


def scheduler_identity(audit):
    return {"fields": audit["fields"], "command": audit["command"]}


def prepare_authority(root, cfg, env):
    validate_config(cfg); validate_resource_env(env)
    return {"slurm": query_slurm(root, cfg, env), "owner_sha256": validate_owner(root, cfg, env),
            "gate_sha256": validate_review_gate(root, cfg), "package_sha256": package_hashes(root),
            "source": validate_source(root, cfg)}


def revalidate_authority(root, cfg, env, initial):
    required = {"slurm", "owner_sha256", "gate_sha256", "package_sha256", "source"}
    if set(initial) != required:
        raise IntegrityError("initial authority context incomplete")
    validate_resource_env(env)
    if validate_owner(root, cfg, env) != initial["owner_sha256"]:
        raise IntegrityError("owner changed before pointer")
    if validate_review_gate(root, cfg) != initial["gate_sha256"]:
        raise IntegrityError("gate changed before pointer")
    if package_hashes(root) != initial["package_sha256"]:
        raise IntegrityError("package changed before pointer")
    if validate_source(root, cfg) != initial["source"]:
        raise IntegrityError("source changed before pointer")
    if scheduler_identity(query_slurm(root, cfg, env)) != scheduler_identity(initial["slurm"]):
        raise IntegrityError("scheduler authority changed before pointer")


def formal(root, cfg, attempt, termination_controller, authority_context=None):
    if not termination_controller.active:
        raise IntegrityError("formal requires active process-level termination controller")
    initial = prepare_authority(root, cfg, os.environ)
    termination_controller.raise_if_pending()
    if authority_context is not None:
        authority_context.clear(); authority_context.update(initial)
    slurm0 = initial["slurm"]; owner_sha = initial["owner_sha256"]; gate_sha = initial["gate_sha256"]
    package0 = initial["package_sha256"]; source0 = initial["source"]; preview = root / cfg["preview_root"]
    with writer_mutex(preview):
        publish(preview, attempt, "FORMAL_RUNNING", False,
                {"metrics.json": canonical_json({"status": "FORMAL_RUNNING"})},
                before_pointer=lambda _b: validate_owner(root, cfg, os.environ), mutex_held=True)
    termination_controller.raise_if_pending()
    (metrics, audit, resolved), lifecycle = execute_probe_stage_cleanup(
        root, cfg, preview, attempt, termination_controller)
    observation_bundle = lifecycle.observation_bundle
    observation_manifest_sha = lifecycle.observation_manifest_sha256
    close_audit = lifecycle.close_audit
    status = "LEAF_CLOSE_ONLY_PASS" if not metrics["route_stop"] else "LEAF_CLOSE_ONLY_TYPED_BLOCK"
    semantic_hash = sha256_bytes(canonical_json({"metrics": metrics, "audit": audit, "resolved": resolved}).encode())
    source1 = validate_source(root, cfg)
    if source1 != source0 or package_hashes(root) != package0: raise IntegrityError("source/package drift during probe")
    slurm1 = query_slurm(root, cfg, os.environ)
    files = {"leaf_probe_matrix.json": canonical_json(audit), "exact_records.json": canonical_json(resolved),
             "metrics.json": canonical_json(dict(metrics, status=status, semantic_success=True)),
             "report.json": canonical_json({"status": status, "semantic_success": True,
                                              "route_stop": metrics["route_stop"], "fallback_used": False,
                                              "observation_frozen_before_cleanup": True,
                                              "explicit_hdf5_close_audit": close_audit}),
             "OBSERVATION_POINTER.json": canonical_json({"root_relative_bundle": observation_bundle.relative_to(root).as_posix(),
                                                           "manifest_sha256": observation_manifest_sha,
                                                           "scientific_call_count": 72}),
             "SOURCE_MANIFEST.json": canonical_json({"pre": source0, "post": source1}),
             "SLURM_AUTHORITY.json": canonical_json({"initial": slurm0, "pre_publish": slurm1}),
             "env.json": canonical_json({"python": sys.version, "slurm_job_id": os.environ["SLURM_JOB_ID"],
                                           "cpus": os.environ["SLURM_CPUS_PER_TASK"],
                                           "memory": os.environ["SLURM_MEM_PER_NODE"],
                                           "partition": os.environ["SLURM_JOB_PARTITION"],
                                           "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "")}),
             "RUN_MANIFEST.json": canonical_json({"package_sha256": package0, "gate_sha256": gate_sha,
                                                   "owner_sha256": owner_sha, "semantic_payload_sha256": semantic_hash,
                                                   "observation_manifest_sha256": observation_manifest_sha})}
    def terminal(_bundle):
        termination_controller.raise_if_pending()
        revalidate_authority(root, cfg, os.environ, initial)
        if verify_observation_bundle(observation_bundle, expected_attempt=attempt) != observation_manifest_sha:
            raise IntegrityError("precleanup observation evidence changed before pointer")
    def termination_failure(events, pass_pointer_changed):
        events = [dict(row) for row in validate_signal_events(events)]
        revalidate_authority(root, cfg, os.environ, initial)
        if verify_observation_bundle(observation_bundle, expected_attempt=attempt) != observation_manifest_sha:
            raise IntegrityError("termination supersession observation evidence drift")
        common = {"status": "LEAF_CLOSE_ONLY_FAILED", "semantic_success": False,
                  "failure_phase": "terminal_commit", "commit_superseded": True,
                  "pass_pointer_was_temporarily_published": bool(pass_pointer_changed),
                  "pending_cleanup_signals": events}
        return {
            "metrics.json": canonical_json(common),
            "report.json": canonical_json(dict(common, error_type="TerminationRequested",
                                                  error="termination during canonical terminal commit",
                                                  explicit_hdf5_close_audit=close_audit,
                                                  precleanup_observation_manifest_sha256=observation_manifest_sha)),
            "OBSERVATION_POINTER.json": files["OBSERVATION_POINTER.json"],
            "SOURCE_MANIFEST.json": canonical_json({"initial": source0, "pre_pointer_revalidation": True}),
            "SLURM_AUTHORITY.json": canonical_json({"initial": slurm0, "pre_pointer_revalidation": True}),
            "RUN_MANIFEST.json": canonical_json({"package_sha256": package0, "gate_sha256": gate_sha,
                                                   "owner_sha256": owner_sha,
                                                   "observation_manifest_sha256": observation_manifest_sha,
                                                   "terminal_commit_supersession": True}),
        }
    return publish(preview, attempt, status, True, files, terminal,
                   termination_controller=termination_controller,
                   termination_failure_builder=termination_failure)


def attempt_failure(root, cfg, attempt, exc):
    safe = safe_attempt_id(attempt)
    payload = {"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt,
               "semantic_success": False,
               "canonical_pointer_changed": bool(getattr(exc, "canonical_failure_published", False)),
               "error_type": type(exc).__name__, "error": str(exc)}
    payload.update(failure_lifecycle_evidence(root, cfg, attempt, exc))
    write_json(root / cfg["preview_root"] / "attempt_failures" / (safe + ".json"), payload)


def failure_lifecycle_evidence(root, cfg, attempt, exc, strict=False):
    bundle = getattr(exc, "observation_bundle", None); digest = getattr(exc, "observation_manifest_sha256", None)
    if bundle is None:
        parent = root / cfg["preview_root"] / "attempt_observations" / safe_attempt_id(attempt)
        try:
            candidates = [p for p in parent.iterdir() if p.is_dir() and not p.is_symlink()]
        except OSError:
            candidates = []
        if len(candidates) == 1:
            try:
                candidate_digest = verify_observation_bundle(candidates[0], expected_attempt=attempt)
                bundle, digest = candidates[0], candidate_digest
            except BaseException:
                pass
    evidence = {}
    if bundle is not None:
        path = Path(bundle)
        if not path.is_absolute(): path = root / path
        try:
            verified = verify_observation_bundle(path, expected_attempt=attempt)
            if digest is not None and verified != digest:
                raise IntegrityError("failure observation digest drift")
            rel = path.relative_to(root).as_posix()
            evidence.update({"precleanup_observation_bundle": rel,
                             "precleanup_observation_manifest_sha256": verified})
        except BaseException:
            if strict: raise
    close_audit = getattr(exc, "close_audit", None)
    if close_audit is not None: evidence["explicit_hdf5_close_audit"] = close_audit
    secondary = getattr(exc, "cleanup_secondary", None)
    if secondary: evidence["cleanup_secondary"] = secondary
    pending = validate_signal_events(getattr(exc, "pending_cleanup_signals", []))
    evidence["pending_cleanup_signals"] = [dict(row) for row in pending]
    return evidence


def publish_failure_if_owned(root, cfg, attempt, exc, env, initial, termination_controller=None):
    try:
        evidence = failure_lifecycle_evidence(root, cfg, attempt, exc, strict=True)
        revalidate_authority(root, cfg, env, initial)
        if evidence.get("precleanup_observation_bundle") and verify_observation_bundle(
                root / evidence["precleanup_observation_bundle"], expected_attempt=attempt) != \
                evidence["precleanup_observation_manifest_sha256"]:
                raise IntegrityError("cleanup failure observation evidence drift")
    except BaseException:
        return False
    owner_sha = initial["owner_sha256"]
    files = {"metrics.json": canonical_json({"status": "LEAF_CLOSE_ONLY_FAILED", "semantic_success": False,
                                               "failure_phase": "cleanup" if isinstance(exc, CleanupError) or
                                               evidence.get("cleanup_secondary") else "runtime_or_integrity"}),
             "report.json": canonical_json(dict({"status": "LEAF_CLOSE_ONLY_FAILED", "semantic_success": False,
                                                   "error_type": type(exc).__name__, "error": str(exc)}, **evidence)),
             "SOURCE_MANIFEST.json": canonical_json({"initial": initial["source"], "pre_pointer_revalidation": True}),
             "SLURM_AUTHORITY.json": canonical_json({"initial": initial["slurm"], "pre_pointer_revalidation": True}),
             "RUN_MANIFEST.json": canonical_json({"package_sha256": initial["package_sha256"],
                                                   "gate_sha256": initial["gate_sha256"],
                                                   "owner_sha256": owner_sha})}
    try:
        def same_owner(_bundle):
            revalidate_authority(root, cfg, env, initial)
            if evidence.get("precleanup_observation_bundle") and verify_observation_bundle(
                    root / evidence["precleanup_observation_bundle"], expected_attempt=attempt) != \
                    evidence["precleanup_observation_manifest_sha256"]:
                raise IntegrityError("cleanup failure observation evidence changed before pointer")
        publish(root / cfg["preview_root"], attempt, "LEAF_CLOSE_ONLY_FAILED", False, files,
                before_pointer=same_owner, termination_controller=termination_controller,
                allow_pending_failure=True)
        return True
    except BaseException:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--attempt-id", default="manual")
    ap.add_argument("--static-preview", action="store_true"); ap.add_argument("--record-wrapper-failure", action="store_true")
    args = ap.parse_args(argv); cfg = load_config(args.config); root = Path(cfg["project_root"])
    authority = {}
    termination_controller = None
    try:
        if args.static_preview: static_preview(root, cfg, args.attempt_id); return 0
        termination_controller = DeferredCleanupSignals().enter()
        if args.record_wrapper_failure:
            if wrapper_failure_already_closed(root / cfg["preview_root"], args.attempt_id):
                return 0
            authority.update(prepare_authority(root, cfg, os.environ))
            raise IntegrityError("sbatch wrapper failure")
        formal(root, cfg, args.attempt_id, termination_controller, authority); return 0
    except BaseException as exc:
        if termination_controller is not None:
            # execute/raise_if_pending may already have attached an exact prefix.
            # Only append signals delivered after that point; repetitions are events,
            # not a signum set, and therefore remain ordered and count-preserving.
            reconcile_pending_signals(exc, termination_controller)
        canonical_closed = bool(getattr(exc, "canonical_failure_published", False))
        if not canonical_closed and not args.static_preview:
            canonical_closed = publish_failure_if_owned(
                root, cfg, args.attempt_id, exc, os.environ, authority, termination_controller)
        if args.static_preview or not canonical_closed or getattr(exc, "canonical_failure_published", False):
            attempt_failure(root, cfg, args.attempt_id, exc)
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 0 if isinstance(exc, TypedBlock) else 2
    finally:
        # Production intentionally retains deferred TERM/INT handlers and mask state until process exit.
        # Restoring here would reintroduce an unclosable race that could replace a structured primary.
        pass


if __name__ == "__main__": raise SystemExit(main())
