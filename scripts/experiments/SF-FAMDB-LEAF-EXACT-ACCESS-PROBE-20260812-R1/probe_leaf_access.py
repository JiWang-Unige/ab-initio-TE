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

EXP_ID = "SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1"
SCHEMA = "TEFM-SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-1.0.0"
AUTH_FALSE = {"annotation_roundtrip_authorized": False, "full_catalog_stage_authorized": False,
              "homology_split_authorized": False, "data_stage_authorized": False,
              "gpu_authorized": False, "s1_authorized": False}


class IntegrityError(RuntimeError):
    pass


class TypedBlock(RuntimeError):
    def __init__(self, metrics, audit, resolved):
        super().__init__("one or more leaf exact-access contracts failed")
        self.metrics, self.audit, self.resolved = metrics, audit, resolved


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


def atomic_write(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("wb") as fh:
        fh.write(data); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)


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
                                  "all_partitions_queried_per_accession": True, "exact_match_count": 1,
                                  "name_prefix_case_alias_copy_fallback_forbidden": True}:
        raise IntegrityError("probe contract drift")


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
            "scripts/experiments/%s/probe_leaf_access.py" % EXP_ID,
            "scripts/experiments/%s/test_probe_leaf_access.py" % EXP_ID,
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


def probe_installed(root, cfg):
    code = cfg["source_contract"]["famdb_code_dir"]
    db = None
    sys.path.insert(0, code)
    try:
        module = importlib.import_module("famdb_classes")
        cls = getattr(module, "FamDB", None)
        if cls is None: raise IntegrityError("FamDB class API drift")
        db = cls(str(root / cfg["source_contract"]["famdb_dir"]), "r")
        result = probe_leaf_mapping(cfg, db.files)
    finally:
        if db is not None:
            db.finalize()
        sys.path.remove(code)
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


def publish(preview, attempt, status, semantic, files, before_pointer=None, mutex_held=False, expected=None):
    preview = Path(preview)
    if not mutex_held:
        with writer_mutex(preview): return publish(preview, attempt, status, semantic, files, before_pointer, True, expected)
    states = preview / "states"; states.mkdir(parents=True, exist_ok=True)
    bundle_id = "%s-%s-%d" % (attempt, status.lower(), time.time_ns()); stage = states / ("." + bundle_id + ".tmp")
    final = states / bundle_id; stage.mkdir()
    for name, value in files.items():
        p = stage / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value if isinstance(value, bytes) else str(value).encode())
    auth = dict(AUTH_FALSE, leaf_adapter_preflight_human_gate_eligible=(status == "LEAF_EXACT_ACCESS_PASS"))
    write_json(stage / "STATUS.json", {"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt,
                                       "status": status, "semantic_success": semantic, "authorization": auth})
    entries = [{"path": p.relative_to(stage).as_posix(), "size": p.stat().st_size, "sha256": sha256_file(p)}
               for p in sorted(stage.rglob("*")) if p.is_file()]
    write_json(stage / "PAYLOAD_MANIFEST.json", {"schema_version": SCHEMA, "files": entries})
    os.replace(stage, final)
    if before_pointer: before_pointer(final)
    if expected is not None and current_bytes(preview) != expected: raise IntegrityError("CURRENT CAS failed")
    atomic_write(preview / "CURRENT", ("states/%s\n" % bundle_id).encode())
    return final


def verify_bundle(preview):
    preview = Path(preview); rel = (preview / "CURRENT").read_text().strip()
    if not rel.startswith("states/") or ".." in rel: raise IntegrityError("bad CURRENT")
    bundle = preview / rel; manifest = json.loads((bundle / "PAYLOAD_MANIFEST.json").read_text())
    expected = {x["path"] for x in manifest["files"]} | {"PAYLOAD_MANIFEST.json"}
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    if expected != actual or any(p.is_symlink() for p in bundle.rglob("*")): raise IntegrityError("bundle exact set failure")
    for x in manifest["files"]:
        p = bundle / x["path"]
        if p.stat().st_size != x["size"] or sha256_file(p) != x["sha256"]: raise IntegrityError("bundle hash failure")
    return json.loads((bundle / "STATUS.json").read_text())


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


def formal(root, cfg, attempt, authority_context=None):
    initial = prepare_authority(root, cfg, os.environ)
    if authority_context is not None:
        authority_context.clear(); authority_context.update(initial)
    slurm0 = initial["slurm"]; owner_sha = initial["owner_sha256"]; gate_sha = initial["gate_sha256"]
    package0 = initial["package_sha256"]; source0 = initial["source"]; preview = root / cfg["preview_root"]
    with writer_mutex(preview):
        publish(preview, attempt, "FORMAL_RUNNING", False,
                {"metrics.json": canonical_json({"status": "FORMAL_RUNNING"})},
                before_pointer=lambda _b: validate_owner(root, cfg, os.environ), mutex_held=True)
    metrics, audit, resolved = probe_installed(root, cfg)
    status = "LEAF_EXACT_ACCESS_PASS" if not metrics["route_stop"] else "LEAF_EXACT_ACCESS_TYPED_BLOCK"
    semantic_hash = sha256_bytes(canonical_json({"metrics": metrics, "audit": audit, "resolved": resolved}).encode())
    source1 = validate_source(root, cfg)
    if source1 != source0 or package_hashes(root) != package0: raise IntegrityError("source/package drift during probe")
    slurm1 = query_slurm(root, cfg, os.environ)
    files = {"leaf_probe_matrix.json": canonical_json(audit), "exact_records.json": canonical_json(resolved),
             "metrics.json": canonical_json(dict(metrics, status=status, semantic_success=True)),
             "report.json": canonical_json({"status": status, "semantic_success": True,
                                              "route_stop": metrics["route_stop"], "fallback_used": False}),
             "SOURCE_MANIFEST.json": canonical_json({"pre": source0, "post": source1}),
             "SLURM_AUTHORITY.json": canonical_json({"initial": slurm0, "pre_publish": slurm1}),
             "env.json": canonical_json({"python": sys.version, "slurm_job_id": os.environ["SLURM_JOB_ID"],
                                           "cpus": os.environ["SLURM_CPUS_PER_TASK"],
                                           "memory": os.environ["SLURM_MEM_PER_NODE"],
                                           "partition": os.environ["SLURM_JOB_PARTITION"],
                                           "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "")}),
             "RUN_MANIFEST.json": canonical_json({"package_sha256": package0, "gate_sha256": gate_sha,
                                                   "owner_sha256": owner_sha, "semantic_payload_sha256": semantic_hash})}
    def terminal(_bundle):
        revalidate_authority(root, cfg, os.environ, initial)
    return publish(preview, attempt, status, True, files, terminal)


def attempt_failure(root, cfg, attempt, exc):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", attempt)[:128] or "unknown"
    write_json(root / cfg["preview_root"] / "attempt_failures" / (safe + ".json"),
               {"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt,
                "semantic_success": False, "canonical_pointer_changed": False,
                "error_type": type(exc).__name__, "error": str(exc)})


def publish_failure_if_owned(root, cfg, attempt, exc, env, initial):
    try:
        revalidate_authority(root, cfg, env, initial)
    except Exception:
        return False
    owner_sha = initial["owner_sha256"]
    files = {"metrics.json": canonical_json({"status": "LEAF_EXACT_ACCESS_FAILED", "semantic_success": False}),
             "report.json": canonical_json({"status": "LEAF_EXACT_ACCESS_FAILED", "semantic_success": False,
                                              "error_type": type(exc).__name__, "error": str(exc)}),
             "SOURCE_MANIFEST.json": canonical_json({"initial": initial["source"], "pre_pointer_revalidation": True}),
             "SLURM_AUTHORITY.json": canonical_json({"initial": initial["slurm"], "pre_pointer_revalidation": True}),
             "RUN_MANIFEST.json": canonical_json({"package_sha256": initial["package_sha256"],
                                                   "gate_sha256": initial["gate_sha256"],
                                                   "owner_sha256": owner_sha})}
    try:
        def same_owner(_bundle):
            revalidate_authority(root, cfg, env, initial)
        publish(root / cfg["preview_root"], attempt, "LEAF_EXACT_ACCESS_FAILED", False, files,
                before_pointer=same_owner)
        return True
    except Exception:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--attempt-id", default="manual")
    ap.add_argument("--static-preview", action="store_true"); ap.add_argument("--record-wrapper-failure", action="store_true")
    args = ap.parse_args(argv); cfg = load_config(args.config); root = Path(cfg["project_root"])
    authority = {}
    try:
        if args.static_preview: static_preview(root, cfg, args.attempt_id); return 0
        if args.record_wrapper_failure:
            authority.update(prepare_authority(root, cfg, os.environ))
            raise IntegrityError("sbatch wrapper failure")
        formal(root, cfg, args.attempt_id, authority); return 0
    except Exception as exc:
        if args.static_preview or not publish_failure_if_owned(root, cfg, args.attempt_id, exc, os.environ, authority):
            attempt_failure(root, cfg, args.attempt_id, exc)
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 0 if isinstance(exc, TypedBlock) else 2


if __name__ == "__main__": raise SystemExit(main())
