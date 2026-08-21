#!/usr/bin/env python3
"""Six-record, CPU-only FamDB leaf adapter syntactic preflight."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

EXP_ID = "SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1"
SCHEMA = "TEFM-SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-1.0.0"
AUTH = {"representative_cpu_proposal_human_gate_eligible": False,
        "repeatmasker_authorized": False, "genome_authorized": False,
        "representative_catalog_authorized": False, "full_catalog_stage_authorized": False,
        "homology_split_authorized": False, "data_stage_authorized": False,
        "training_authorized": False, "gpu_authorized": False, "s1_authorized": False}
OUTPUT_COMMON = {"metrics.json", "report.json", "probe_matrix.json", "record_manifest.json",
                 "SOURCE_MANIFEST.json", "SLURM_AUTHORITY.json", "env.json", "RUN_MANIFEST.json"}
OUTPUT_PASS = OUTPUT_COMMON | {"canonical_name_view.fa", "accession_version_view.fa"}


class IntegrityError(RuntimeError): pass


class AdapterTypedBlock(RuntimeError):
    def __init__(self, result): super().__init__("adapter scientific contract block"); self.result = result


def canonical_json(obj): return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
def sha256_bytes(data): return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def atomic_write(path, data, pre_replace=None):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("wb") as fh: fh.write(data); fh.flush(); os.fsync(fh.fileno())
    if pre_replace: pre_replace()
    os.replace(tmp, path)


def load_config(path):
    cfg = json.loads(Path(path).read_text())
    if cfg.get("schema_version") != SCHEMA or cfg.get("exp_id") != EXP_ID: raise IntegrityError("config identity drift")
    return cfg


def validate_config(cfg):
    a = cfg.get("adapter_contract", {})
    if a != {"target_count": 6, "partition_count": 12, "exact_api_call_count": 72,
             "lookup": "FamDBLeaf.get_family_by_accession",
             "lookup_key": "unversioned_accession_exact_case_sensitive",
             "views": ["canonical_name", "accession.version"],
             "sequence_normalization": "uppercase_U_to_T", "fasta_line_width": 60,
             "control_header_grammar": ">{canonical_name_if_nonempty_else_unversioned_accession}#{raw_class}",
             "candidate_header_grammar": ">{accession.version}#{raw_class}",
             "header_ascii_exact_case_single_hash_no_whitespace": True,
             "empty_canonical_name_explicit": True, "sequence_order_raw_class_identical_required": True,
             "name_prefix_case_alias_copy_fallback_forbidden": True}:
        raise IntegrityError("adapter contract drift")
    if cfg.get("resource_contract") != {"cpus": 1, "memory_mib": 4096, "walltime_minutes": 10, "gpus": 0}:
        raise IntegrityError("resource contract drift")
    if cfg.get("authorization") != AUTH: raise IntegrityError("authorization drift")
    p = cfg.get("parent_contract", {})
    if p.get("job_id") != "11534847" or p.get("exp_id") != "SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1":
        raise IntegrityError("parent identity drift")


def package_hashes(root):
    rels = ["configs/%s.yaml" % EXP_ID,
            "scripts/experiments/%s/leaf_adapter_preflight.py" % EXP_ID,
            "scripts/experiments/%s/test_leaf_adapter_preflight.py" % EXP_ID,
            "sbatch/%s.sbatch" % EXP_ID, "docs/experiments/%s.md" % EXP_ID]
    return {rel: sha256_file(root / rel) for rel in rels}


def import_parent(root, cfg):
    p = cfg["parent_contract"]; runner = root / p["runner"]
    if not runner.is_file() or runner.is_symlink() or sha256_file(runner) != p["runner_sha256"]:
        raise IntegrityError("parent runner hash drift")
    spec = importlib.util.spec_from_file_location("audited_close_only_parent", runner)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def validate_parent_evidence(root, cfg):
    p = cfg["parent_contract"]
    for rel, want in p["artifacts"].items():
        path = root / rel
        if not path.is_file() or path.is_symlink() or sha256_file(path) != want: raise IntegrityError("parent artifact drift: " + rel)
    parent_cfg_path = root / p["config"]
    if not parent_cfg_path.is_file() or parent_cfg_path.is_symlink() or sha256_file(parent_cfg_path) != p["config_sha256"]:
        raise IntegrityError("parent config drift")
    pcfg = json.loads(parent_cfg_path.read_text()); selected = pcfg.get("selected_records")
    selected_sha = sha256_bytes(json.dumps(selected, sort_keys=True, separators=(",", ":")).encode())
    if selected_sha != p["selected_records_sha256"] or not isinstance(selected, list) or len(selected) != 6:
        raise IntegrityError("parent six-record denominator drift")
    if selected[-1] != {"versioned_accession": "DR002419729.2", "accession": "DR002419729",
                        "canonical_name": "", "raw_class": "RC/Helitron", "consensus_length": 1176,
                        "consensus_sha256": "6c1be53b8c9787cb3a0b8ff81e99e830b4320259cc429f098d577adc5cffe4f4",
                        "partition": 3}:
        raise IntegrityError("DR frozen identity drift")
    result = json.loads((root / "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/result_semantic_audit.11534847.json").read_text())
    expected = p["expected_result"]
    if any(result.get(k) != v for k, v in expected.items()): raise IntegrityError("parent component result drift")
    audited = root / "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256"
    lines = audited.read_text().splitlines()
    if len(lines) != 11: raise IntegrityError("parent audited manifest shape drift")
    seen = set()
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\n]+)", line)
        if not match: raise IntegrityError("parent audited manifest grammar drift")
        digest, rel = match.groups(); rp = Path(rel)
        if rp.is_absolute() or ".." in rp.parts or rel in seen: raise IntegrityError("parent audited manifest unsafe path")
        seen.add(rel); path = root / rel
        if not path.is_file() or path.is_symlink() or sha256_file(path) != digest: raise IntegrityError("parent audited payload drift")
    return pcfg, {"parent_config_sha256": p["config_sha256"], "parent_runner_sha256": p["runner_sha256"],
                  "parent_audited_manifest_sha256": p["artifacts"][audited.relative_to(root).as_posix()],
                  "selected_records_sha256": selected_sha}


def validate_gate(root, cfg):
    path = root / cfg["code_review_gate_path"]
    if not path.is_file() or path.is_symlink(): raise IntegrityError("new experiment review gate missing")
    gate = json.loads(path.read_text()); reviewed = gate.get("reviewed_files")
    if gate.get("exp_id") != EXP_ID or gate.get("verdict") not in {"PASS", "PASS_WITH_WARNINGS"} or \
       gate.get("blockers_open") != 0 or isinstance(gate.get("blockers_open"), bool) or not isinstance(reviewed, dict):
        raise IntegrityError("new experiment review gate invalid")
    package = package_hashes(root)
    if reviewed != package: raise IntegrityError("reviewed package is not exact current package")
    return sha256_file(path)


def parse_mem_mib(value):
    m = re.fullmatch(r"([0-9]+)([KMG]?)", str(value).upper())
    if not m: raise IntegrityError("invalid Slurm memory")
    n, unit = int(m.group(1)), m.group(2)
    if unit == "K":
        if n % 1024: raise IntegrityError("non-integral MiB")
        return n // 1024
    return n * {"": 1, "M": 1, "G": 1024}[unit]


def validate_resource_env(env):
    if not re.fullmatch(r"[1-9][0-9]*", env.get("SLURM_JOB_ID", "")): raise IntegrityError("positive numeric job required")
    if env.get("SLURM_CPUS_PER_TASK") != "1" or parse_mem_mib(env.get("SLURM_MEM_PER_NODE", "")) != 4096:
        raise IntegrityError("exact CPU/memory required")
    if env.get("SLURM_JOB_PARTITION") != "private-teodoro-gpu": raise IntegrityError("partition drift")
    if any(env.get(k, "").strip() not in {"", "NoDevFiles"} for k in
           ("CUDA_VISIBLE_DEVICES", "SLURM_GPUS", "SLURM_JOB_GPUS", "SLURM_GPUS_ON_NODE")):
        raise IntegrityError("0 GPU required")


def parse_scontrol(text):
    if not text.endswith("\n") or text.count("\n") != 1: raise IntegrityError("scontrol one-line required")
    line = text[:-1]; matches = list(re.finditer(r"(?:^| )([A-Za-z][A-Za-z0-9/:]*)=", line)); out = {}
    for i, match in enumerate(matches):
        key = match.group(1); end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        if key in out: raise IntegrityError("duplicate scontrol key")
        out[key] = line[match.end():end].strip()
    return out


def parse_tres(value, expected):
    out = {}
    for token in str(value).split(","):
        if token.count("=") != 1: raise IntegrityError("TRES grammar")
        key, val = token.split("=", 1)
        if not key or not val or key in out or key not in expected: raise IntegrityError("TRES duplicate/unknown")
        out[key] = val
    if out != expected: raise IntegrityError("TRES mismatch")


def query_slurm(root, cfg, env, executor=None):
    validate_resource_env(env); c = cfg["slurm_contract"]; job = env["SLURM_JOB_ID"]
    binary = Path(c["scontrol_binary"]); sbatch = root / "sbatch" / (EXP_ID + ".sbatch")
    if not binary.is_file() or binary.is_symlink() or sha256_file(binary) != c["scontrol_sha256"]: raise IntegrityError("scontrol drift")
    if not sbatch.is_file() or sbatch.is_symlink() or sbatch.resolve() != Path(c["command"]) or sha256_file(sbatch) != c["sbatch_sha256"]:
        raise IntegrityError("sbatch drift")
    cmd = ["/usr/bin/timeout", "--signal=TERM", "--kill-after=2s", "%ss" % c["query_timeout_seconds"],
           str(binary), "show", "job", job, "-o"]
    if executor is None:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=c["query_timeout_seconds"] + 5)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    else: rc, out, err = executor(cmd, c["query_timeout_seconds"] + 5)
    if rc or err: raise IntegrityError("scontrol rc/stderr")
    fields = parse_scontrol(out); expected = {"JobId": job, "Partition": c["partition"], "TimeLimit": c["time_limit"],
        "NumCPUs": c["num_cpus"], "Command": c["command"], "SubmitLine": c["submit_line"]}
    if any(fields.get(k) != v for k, v in expected.items()): raise IntegrityError("scheduler identity mismatch")
    parse_tres(fields.get("ReqTRES", ""), c["exact_tres"]); parse_tres(fields.get("AllocTRES", ""), c["exact_tres"])
    return {"fields": {k: fields[k] for k in sorted(set(expected) | {"ReqTRES", "AllocTRES"})}, "command": cmd}


def validate_owner(root, cfg, env):
    owner = root / cfg["preview_root"] / cfg["owner_lock_name"]
    if owner.is_symlink() or not owner.is_dir(): raise IntegrityError("owner missing")
    entries = list(owner.iterdir())
    if len(entries) != 1 or entries[0].name != "job_id" or entries[0].is_symlink() or not entries[0].is_file():
        raise IntegrityError("owner shape drift")
    if entries[0].read_text() != env["SLURM_JOB_ID"] + "\n": raise IntegrityError("owner job drift")
    return sha256_file(entries[0])


def valid_header_token(value):
    return isinstance(value, str) and value and value.isascii() and "#" not in value and \
        not any(ch.isspace() or ord(ch) < 33 or ord(ch) == 127 for ch in value)


def make_header(kind, row):
    ident = (row["canonical_name"] or row["accession"]) if kind == "canonical_name" else row["versioned_accession"]
    raw_class = row["raw_class"]
    if kind == "accession.version" and not re.fullmatch(r"(?:DF|DR)[0-9]{9}\.[1-9][0-9]*", ident):
        raise AdapterTypedBlock({"failures": [{"reason": "candidate_not_versioned", "identifier": ident}]})
    if not valid_header_token(ident) or not valid_header_token(raw_class):
        raise AdapterTypedBlock({"failures": [{"reason": "ambiguous_header_token", "identifier": ident}]})
    return ">%s#%s" % (ident, raw_class)


def parse_header(header):
    if not isinstance(header, str) or not header.startswith(">") or header.count("#") != 1: raise IntegrityError("header grammar")
    ident, raw_class = header[1:].split("#")
    if not valid_header_token(ident) or not valid_header_token(raw_class): raise IntegrityError("header token grammar")
    return ident, raw_class


def wrap_fasta(header, sequence, width=60):
    if parse_header(header)[1] == "": raise IntegrityError("empty class")
    seq = sequence.upper().replace("U", "T")
    if not seq or not re.fullmatch(r"[A-Z*.-]+", seq): raise IntegrityError("sequence grammar")
    return (header + "\n" + "\n".join(seq[i:i + width] for i in range(0, len(seq), width)) + "\n").encode()


def parse_fasta(data):
    try: text = data.decode("ascii")
    except UnicodeDecodeError as exc: raise IntegrityError("FASTA must be ASCII") from exc
    if not text.endswith("\n"): raise IntegrityError("FASTA final newline")
    records, current, chunks = [], None, []
    for line in text.splitlines():
        if line.startswith(">"):
            if current is not None: records.append((current, "".join(chunks)))
            current, chunks = line, []
        else:
            if current is None or not line or len(line) > 60: raise IntegrityError("FASTA body grammar")
            chunks.append(line)
    if current is not None: records.append((current, "".join(chunks)))
    return records


def evaluate_actual(parent_cfg, observations):
    expected = parent_cfg["selected_records"]; parts = parent_cfg["source_contract"]["expected_partition_order"]
    keys = [(x.get("queried_accession"), x.get("partition")) for x in observations]
    expected_keys = [(x["accession"], p) for x in expected for p in parts]
    if len(keys) != 72 or len(set(keys)) != 72 or sorted(keys) != sorted(expected_keys): raise IntegrityError("actual probe matrix not 6x12")
    actual, failures = [], []
    for index, target in enumerate(expected):
        hits = [x["record"] for x in observations if x["queried_accession"] == target["accession"] and x["record"]]
        if len(hits) != 1:
            failures.append({"index": index, "accession": target["accession"], "reason": "missing" if not hits else "duplicate",
                             "match_count": len(hits)}); continue
        row = hits[0]; drift = [k for k in ("accession", "versioned_accession", "canonical_name", "raw_class",
                    "consensus_length", "consensus_sha256", "partition") if row.get(k) != target[k]]
        seq = row.get("sequence")
        if not isinstance(seq, str): drift.append("sequence")
        else:
            seq = seq.upper().replace("U", "T")
            if len(seq) != target["consensus_length"] or sha256_bytes(seq.encode()) != target["consensus_sha256"]: drift.append("sequence")
        if drift: failures.append({"index": index, "accession": target["accession"], "reason": "identity_drift", "fields": sorted(set(drift))})
        else: actual.append(dict(row, sequence=seq, index=index))
    if failures: return {"typed_block": True, "failures": failures, "records": [], "probe_call_count": 72}
    if [x["accession"] for x in actual] != [x["accession"] for x in expected]: raise IntegrityError("actual fixed order drift")
    try: return materialize_views(actual)
    except AdapterTypedBlock as exc:
        return {"typed_block": True, "failures": exc.result["failures"], "records": [], "probe_call_count": 72}


def materialize_views(rows):
    if len(rows) != 6 or [x.get("index") for x in rows] != list(range(6)): raise AdapterTypedBlock({"failures": [{"reason": "row_order_or_count"}]})
    control_parts, candidate_parts = [], []
    for row in rows:
        control_parts.append(wrap_fasta(make_header("canonical_name", row), row["sequence"]))
        candidate_parts.append(wrap_fasta(make_header("accession.version", row), row["sequence"]))
    control, candidate = b"".join(control_parts), b"".join(candidate_parts)
    cr, ar = parse_fasta(control), parse_fasta(candidate)
    if len(cr) != 6 or len(ar) != 6: raise AdapterTypedBlock({"failures": [{"reason": "view_count"}]})
    manifest, semantic = [], []
    control_ids, candidate_ids = set(), set()
    for index, (row, left, right, left_bytes, right_bytes) in enumerate(zip(rows, cr, ar, control_parts, candidate_parts)):
        lid, lclass = parse_header(left[0]); rid, rclass = parse_header(right[0])
        if left[1] != right[1] or left[1] != row["sequence"] or lclass != rclass or lclass != row["raw_class"]:
            raise AdapterTypedBlock({"failures": [{"reason": "paired_sequence_or_class", "index": index}]})
        if lid in control_ids or rid in candidate_ids: raise AdapterTypedBlock({"failures": [{"reason": "header_collision", "index": index}]})
        control_ids.add(lid); candidate_ids.add(rid); semantic.append({"index": index, "sequence": left[1], "raw_class": lclass})
        manifest.append({"index": index, "control_header": left[0], "candidate_header": right[0],
            "control_identifier": lid, "candidate_identifier": rid, "accession": row["accession"],
            "versioned_accession": row["versioned_accession"], "canonical_name": row["canonical_name"],
            "raw_class": row["raw_class"], "partition": row["partition"], "consensus_length": len(left[1]),
            "consensus_sha256": sha256_bytes(left[1].encode()), "provenance_namespace": row["accession"][:2],
            "control_record_fasta_sha256": sha256_bytes(left_bytes),
            "candidate_record_fasta_sha256": sha256_bytes(right_bytes),
            "parent_audited_manifest_sha256": row["parent_audited_manifest_sha256"]})
    semantic_sha = sha256_bytes(canonical_json(semantic).encode())
    return {"typed_block": False, "failures": [], "records": manifest, "probe_call_count": 72,
            "canonical_name_view.fa": control, "accession_version_view.fa": candidate,
            "ordered_sequence_class_semantic_sha256_control": semantic_sha,
            "ordered_sequence_class_semantic_sha256_candidate": semantic_sha,
            "control_library_sha256": sha256_bytes(control), "candidate_library_sha256": sha256_bytes(candidate)}


def validate_output_mapping(control, candidate, manifest, expected_parent_hash):
    """Re-read actual FASTA bytes and prove every manifest field maps to them."""
    left, right = parse_fasta(control), parse_fasta(candidate)
    if len(left) != 6 or len(right) != 6 or not isinstance(manifest, list) or len(manifest) != 6:
        raise IntegrityError("output/manifest denominator drift")
    semantic_left, semantic_right = [], []
    expected_control, expected_candidate = [], []
    for index, (lrow, rrow, row) in enumerate(zip(left, right, manifest)):
        if row.get("index") != index or lrow[0] != row.get("control_header") or rrow[0] != row.get("candidate_header"):
            raise IntegrityError("output/manifest order/header mapping drift")
        lid, lclass = parse_header(lrow[0]); rid, rclass = parse_header(rrow[0])
        expected_lid = row.get("canonical_name") or row.get("accession")
        if lid != expected_lid or rid != row.get("versioned_accession") or lclass != row.get("raw_class") or rclass != lclass:
            raise IntegrityError("output/manifest identifier/class mapping drift")
        if lrow[1] != rrow[1] or len(lrow[1]) != row.get("consensus_length") or \
           sha256_bytes(lrow[1].encode()) != row.get("consensus_sha256"):
            raise IntegrityError("output/manifest sequence mapping drift")
        if sha256_bytes(wrap_fasta(lrow[0], lrow[1])) != row.get("control_record_fasta_sha256") or \
           sha256_bytes(wrap_fasta(rrow[0], rrow[1])) != row.get("candidate_record_fasta_sha256"):
            raise IntegrityError("record FASTA hash mapping drift")
        expected_control.append(wrap_fasta(lrow[0], lrow[1])); expected_candidate.append(wrap_fasta(rrow[0], rrow[1]))
        if row.get("provenance_namespace") != row.get("accession", "")[:2] or \
           row.get("parent_audited_manifest_sha256") != expected_parent_hash:
            raise IntegrityError("record provenance mapping drift")
        semantic_left.append({"index": index, "sequence": lrow[1], "raw_class": lclass})
        semantic_right.append({"index": index, "sequence": rrow[1], "raw_class": rclass})
    lhash = sha256_bytes(canonical_json(semantic_left).encode()); rhash = sha256_bytes(canonical_json(semantic_right).encode())
    if lhash != rhash or control != b"".join(expected_control) or candidate != b"".join(expected_candidate):
        raise IntegrityError("ordered semantic hash or exact FASTA wrapping drift")
    return {"control": lhash, "candidate": rhash}


def probe_with_lifecycle(root, cfg, parent, parent_cfg, controller, preview, attempt):
    lifecycle = parent.HandleLifecycle(parent_cfg); primary = None; trace = None; result = None; cleanup_error = None
    try:
        code = parent_cfg["source_contract"]["famdb_code_dir"]; sys.path.insert(0, code)
        try:
            import importlib
            module = importlib.import_module("famdb_classes"); cls = getattr(module, "FamDB", None)
            if cls is None: raise IntegrityError("FamDB class missing")
            db = cls.__new__(cls); lifecycle.attach_db(db); cls.__init__(db, str(root / parent_cfg["source_contract"]["famdb_dir"]), "r")
            files = getattr(db, "files", None); valid, errors = parent.inspect_leaf_mapping(files, parent_cfg, require_exact=True)
            if errors or len(valid) != 12: raise IntegrityError("leaf mapping identity drift")
            observations = []
            for target in parent_cfg["selected_records"]:
                for part in parent_cfg["source_contract"]["expected_partition_order"]:
                    family = files[part].get_family_by_accession(target["accession"])
                    row = None
                    if family is not None:
                        base = parent.family_row(family, part, target["accession"])
                        sequence = (family.consensus or "").upper().replace("U", "T")
                        row = dict(base, sequence=sequence,
                                   parent_audited_manifest_sha256=cfg["parent_contract"]["artifacts"][
                                     "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256"])
                    observations.append({"queried_accession": target["accession"], "partition": part, "record": row})
            result = evaluate_actual(parent_cfg, observations); result["observations"] = observations
            observation, observation_sha = stage_precleanup(preview, attempt, result)
            result["observation_bundle"] = observation; result["observation_manifest_sha256"] = observation_sha
        finally:
            if sys.path and sys.path[0] == code: sys.path.pop(0)
    except BaseException as exc: primary, trace = exc, exc.__traceback__
    finally:
        try: lifecycle.ensure_cleanup(primary=primary, attempt="adapter")
        except BaseException as exc: cleanup_error = exc
        if primary is not None:
            parent.reconcile_pending_signals(primary, controller)
            if cleanup_error is not None: parent.attach_cleanup_secondary(primary, cleanup_error)
    if primary is not None: raise primary.with_traceback(trace)
    controller.raise_if_pending(cleanup_secondary=cleanup_error)
    if cleanup_error is not None:
        if result is not None and result.get("observation_bundle") is not None:
            cleanup_error.observation_bundle = result["observation_bundle"]
            cleanup_error.observation_manifest_sha256 = result["observation_manifest_sha256"]
        raise cleanup_error
    result["close_audit"] = lifecycle.close_audit
    return result


def safe_attempt(value):
    out = re.sub(r"[^A-Za-z0-9_.-]", "_", str(value))[:128]
    if not out or out in {".", ".."}: raise IntegrityError("unsafe attempt")
    return out


def stage_precleanup(preview, attempt, result):
    preview = Path(preview); parent = preview / "attempt_observations" / safe_attempt(attempt)
    if parent.exists(): raise IntegrityError("preexisting attempt observation namespace")
    payload = {"probe_matrix.json": canonical_json({"observations": result["observations"], "failures": result["failures"]}).encode(),
               "record_manifest.json": canonical_json(result["records"]).encode()}
    if not result["typed_block"]:
        payload["canonical_name_view.fa"] = result["canonical_name_view.fa"]
        payload["accession_version_view.fa"] = result["accession_version_view.fa"]
    digest = sha256_bytes(b"".join(k.encode() + b"\0" + payload[k] for k in sorted(payload)))
    stage = parent.with_name("." + parent.name + ".tmp"); bundle = parent / digest
    stage.mkdir(parents=True)
    try:
        for name, data in payload.items(): (stage / name).write_bytes(data)
        if not result["typed_block"]:
            actual_control = (stage / "canonical_name_view.fa").read_bytes()
            actual_candidate = (stage / "accession_version_view.fa").read_bytes()
            actual_manifest = json.loads((stage / "record_manifest.json").read_text())
            semantic = validate_output_mapping(actual_control, actual_candidate, actual_manifest,
              result["records"][0]["parent_audited_manifest_sha256"])
            if sha256_bytes(actual_control) != result["control_library_sha256"] or \
               sha256_bytes(actual_candidate) != result["candidate_library_sha256"] or \
               semantic["control"] != result["ordered_sequence_class_semantic_sha256_control"] or \
               semantic["candidate"] != result["ordered_sequence_class_semantic_sha256_candidate"]:
                raise IntegrityError("materialized library hash drift")
        manifest = {"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt, "payload_sha256": digest,
                    "files": [{"path": k, "size": len(payload[k]), "sha256": sha256_bytes(payload[k])} for k in sorted(payload)]}
        (stage / "OBSERVATION_MANIFEST.json").write_text(canonical_json(manifest)); stage.parent.mkdir(parents=True, exist_ok=True)
        parent.mkdir(); os.replace(stage, bundle)
    except BaseException:
        raise
    return bundle, sha256_file(bundle / "OBSERVATION_MANIFEST.json")


def verify_observation(bundle, attempt, expected_parent_hash=None):
    bundle = Path(bundle)
    if bundle.is_symlink() or not bundle.is_dir() or any(p.is_symlink() or p.is_dir() for p in bundle.iterdir()):
        raise IntegrityError("observation bundle shape")
    manifest = json.loads((bundle / "OBSERVATION_MANIFEST.json").read_text())
    if manifest.get("exp_id") != EXP_ID or manifest.get("attempt_id") != attempt or bundle.name != manifest.get("payload_sha256"):
        raise IntegrityError("observation identity")
    expected = {x["path"] for x in manifest["files"]} | {"OBSERVATION_MANIFEST.json"}
    if expected != {p.name for p in bundle.iterdir()}: raise IntegrityError("observation exact set")
    payload = {}
    for row in manifest["files"]:
        p = bundle / row["path"]
        if p.stat().st_size != row["size"] or sha256_file(p) != row["sha256"]: raise IntegrityError("observation hash")
        payload[row["path"]] = p.read_bytes()
    if sha256_bytes(b"".join(k.encode() + b"\0" + payload[k] for k in sorted(payload))) != manifest["payload_sha256"]:
        raise IntegrityError("observation payload hash")
    if "canonical_name_view.fa" in payload:
        rows = json.loads(payload["record_manifest.json"])
        if expected_parent_hash is None:
            expected_parent_hash = rows[0].get("parent_audited_manifest_sha256") if rows else ""
        validate_output_mapping(payload["canonical_name_view.fa"], payload["accession_version_view.fa"],
                                rows, expected_parent_hash)
    return sha256_file(bundle / "OBSERVATION_MANIFEST.json")


def writer_mutex(preview):
    class Lock:
        def __enter__(self):
            ensure_state_root(preview, create=True)
            self.fh = (Path(preview) / ".state-writer.lock").open("a+")
            try: fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                self.fh.close(); raise IntegrityError("state writer busy") from exc
        def __exit__(self, *_): fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN); self.fh.close()
    return Lock()


def no_symlink_path(path):
    """Reject every existing symlink from filesystem root through path."""
    absolute = Path(path).absolute()
    for item in list(reversed(absolute.parents)) + [absolute]:
        if os.path.lexists(item) and item.is_symlink():
            raise IntegrityError("state path contains symlink: " + str(item))


def ensure_state_root(preview, create=False):
    preview = Path(preview).absolute()
    no_symlink_path(preview)
    if create: preview.mkdir(parents=True, exist_ok=True)
    if not preview.is_dir() or preview.is_symlink(): raise IntegrityError("preview root shape")
    no_symlink_path(preview)
    states = preview / "states"
    if create: states.mkdir(exist_ok=True)
    if not states.is_dir() or states.is_symlink(): raise IntegrityError("states root shape")
    no_symlink_path(states)
    if states.resolve(strict=True).parent != preview.resolve(strict=True): raise IntegrityError("states containment failure")
    return preview, states


def build_bundle(preview, attempt, status, semantic, files):
    allowed = OUTPUT_PASS if status == "LEAF_ADAPTER_PREFLIGHT_PASS" else OUTPUT_COMMON
    if status in {"IMPLEMENTED_NOT_RUN", "FORMAL_RUNNING"}:
        allowed = {"metrics.json", "report.json", "RUN_MANIFEST.json"}
    if set(files) != allowed: raise IntegrityError("terminal exact output allowlist")
    preview, states = ensure_state_root(preview, create=True)
    ident = "%s-%s-%d" % (safe_attempt(attempt), status.lower(), time.time_ns()); stage = states / ("." + ident + ".tmp"); final = states / ident
    stage.mkdir()
    for name, data in files.items(): (stage / name).write_bytes(data if isinstance(data, bytes) else str(data).encode())
    auth = dict(AUTH); auth["representative_cpu_proposal_human_gate_eligible"] = status == "LEAF_ADAPTER_PREFLIGHT_PASS"
    (stage / "STATUS.json").write_text(canonical_json({"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt,
        "status": status, "semantic_success": semantic, "authorization": auth}))
    entries = [{"path": p.name, "size": p.stat().st_size, "sha256": sha256_file(p)} for p in sorted(stage.iterdir())]
    (stage / "PAYLOAD_MANIFEST.json").write_text(canonical_json({"schema_version": SCHEMA, "files": entries}))
    os.replace(stage, final)
    no_symlink_path(final)
    if final.resolve(strict=True).parent != states.resolve(strict=True): raise IntegrityError("bundle containment failure")
    return final, ("states/%s\n" % ident).encode()


def current_bytes(preview):
    p = Path(preview) / "CURRENT"; return p.read_bytes() if p.is_file() else None


def publish(preview, attempt, status, semantic, files, before_pointer=None, controller=None, expected=None,
            expected_parent_hash=None):
    preview = Path(preview)
    with writer_mutex(preview):
        old = current_bytes(preview)
        if expected is not None and old != expected: raise IntegrityError("CURRENT CAS drift")
        final, pointer = build_bundle(preview, attempt, status, semantic, files)
        if controller is None:
            if before_pointer: before_pointer(final)
            def verify_then_replace():
                if expected is not None and current_bytes(preview) != expected: raise IntegrityError("CURRENT CAS drift")
                verify_state_bundle(preview, final, attempt, status, semantic, expected_parent_hash)
            atomic_write(preview / "CURRENT", pointer, verify_then_replace); return final
        controller.begin_terminal_commit(); controller.drain_masked()
        if semantic and controller.pending_rows(): controller.raise_if_pending()
        if before_pointer: before_pointer(final)
        controller.drain_masked()
        if semantic and controller.pending_rows(): controller.raise_if_pending()
        def pre():
            controller.drain_masked()
            if semantic and controller.pending_rows(): controller.raise_if_pending()
            if expected is not None and current_bytes(preview) != expected: raise IntegrityError("CURRENT CAS drift")
            verify_state_bundle(preview, final, attempt, status, semantic, expected_parent_hash)
        atomic_write(preview / "CURRENT", pointer, pre); controller.drain_masked()
        if semantic and controller.pending_rows():
            if old is not None: atomic_write(preview / "CURRENT", old)
            raise parent_termination(controller)
        return final


def parent_termination(controller):
    term = RuntimeError("termination during adapter terminal commit"); term.pending_cleanup_signals = controller.pending_rows(); return term


def verify_state_bundle(preview, bundle, expected_attempt=None, expected_status=None, expected_semantic=None,
                        expected_parent_hash=None):
    preview, states = ensure_state_root(preview, create=False); bundle = Path(bundle).absolute()
    no_symlink_path(bundle)
    if bundle.is_symlink() or not bundle.is_dir() or bundle.resolve(strict=True).parent != states.resolve(strict=True):
        raise IntegrityError("bundle containment/shape failure")
    entries = list(bundle.iterdir())
    if any(p.is_symlink() or p.is_dir() for p in entries): raise IntegrityError("bundle entry shape")
    for entry in entries:
        no_symlink_path(entry)
        if entry.resolve(strict=True).parent != bundle.resolve(strict=True): raise IntegrityError("bundle entry containment")
    try:
        manifest = json.loads((bundle / "PAYLOAD_MANIFEST.json").read_text())
    except Exception as exc: raise IntegrityError("payload manifest parse failure") from exc
    rows = manifest.get("files")
    if set(manifest) != {"schema_version", "files"} or manifest.get("schema_version") != SCHEMA or not isinstance(rows, list):
        raise IntegrityError("payload manifest schema")
    names = [row.get("path") for row in rows if isinstance(row, dict)]
    if len(names) != len(rows) or len(names) != len(set(names)) or any(
            set(row) != {"path", "size", "sha256"} for row in rows if isinstance(row, dict)) or any(
            not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name == "PAYLOAD_MANIFEST.json"
            for name in names): raise IntegrityError("payload manifest path/schema")
    expected_set = set(names) | {"PAYLOAD_MANIFEST.json"}
    if expected_set != {p.name for p in entries}: raise IntegrityError("bundle exact set")
    for row in rows:
        p = bundle / row["path"]
        if isinstance(row["size"], bool) or not isinstance(row["size"], int) or row["size"] < 0 or \
           not re.fullmatch(r"[0-9a-f]{64}", str(row["sha256"])) or p.stat().st_size != row["size"] or \
           sha256_file(p) != row["sha256"]: raise IntegrityError("bundle payload hash/schema")
    try: status_row = json.loads((bundle / "STATUS.json").read_text())
    except Exception as exc: raise IntegrityError("STATUS parse failure") from exc
    if set(status_row) != {"schema_version", "exp_id", "attempt_id", "status", "semantic_success", "authorization"} or \
       status_row.get("schema_version") != SCHEMA or status_row.get("exp_id") != EXP_ID or \
       not isinstance(status_row.get("semantic_success"), bool) or status_row.get("authorization") != dict(
         AUTH, representative_cpu_proposal_human_gate_eligible=status_row.get("status") == "LEAF_ADAPTER_PREFLIGHT_PASS"):
        raise IntegrityError("STATUS schema/identity")
    if expected_attempt is not None and status_row["attempt_id"] != expected_attempt: raise IntegrityError("attempt drift")
    if expected_status is not None and status_row["status"] != expected_status: raise IntegrityError("status drift")
    if expected_semantic is not None and status_row["semantic_success"] != expected_semantic: raise IntegrityError("semantic drift")
    allowed = OUTPUT_PASS if status_row["status"] == "LEAF_ADAPTER_PREFLIGHT_PASS" else OUTPUT_COMMON
    if status_row["status"] in {"IMPLEMENTED_NOT_RUN", "FORMAL_RUNNING"}:
        allowed = {"metrics.json", "report.json", "RUN_MANIFEST.json"}
    if set(names) != allowed | {"STATUS.json"}: raise IntegrityError("status-specific payload allowlist")
    try:
        metrics = json.loads((bundle / "metrics.json").read_text()); report = json.loads((bundle / "report.json").read_text())
    except Exception as exc: raise IntegrityError("metrics/report parse failure") from exc
    if metrics.get("status") != status_row["status"] or report.get("status") != status_row["status"]:
        raise IntegrityError("metrics/report status drift")
    if status_row["status"] == "LEAF_ADAPTER_PREFLIGHT_PASS":
        records = json.loads((bundle / "record_manifest.json").read_text())
        validate_output_mapping((bundle / "canonical_name_view.fa").read_bytes(),
                                (bundle / "accession_version_view.fa").read_bytes(), records,
                                expected_parent_hash or "")
    return status_row


def verify_bundle(preview, expected_parent_hash=None):
    preview, states = ensure_state_root(preview, create=False); current = preview / "CURRENT"
    if current.is_symlink() or not current.is_file(): raise IntegrityError("CURRENT shape")
    rel = current.read_text().strip()
    if not re.fullmatch(r"states/[A-Za-z0-9_.-]+", rel): raise IntegrityError("CURRENT path")
    bundle = preview / rel
    if bundle.resolve(strict=True).parent != states.resolve(strict=True): raise IntegrityError("CURRENT containment")
    return verify_state_bundle(preview, bundle, expected_parent_hash=expected_parent_hash)


def wrapper_terminal_already_closed(preview, attempt, expected_parent_hash):
    try: status = verify_bundle(preview, expected_parent_hash)
    except BaseException: return False
    return status.get("attempt_id") == attempt and status.get("status") in {
      "LEAF_ADAPTER_PREFLIGHT_PASS", "LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK", "LEAF_ADAPTER_PREFLIGHT_FAILED"}


def prepare_authority(root, cfg, env, scheduler=None):
    # Scheduler is deliberately first, before any parent asset or H5 access.
    slurm = scheduler if scheduler is not None else query_slurm(root, cfg, env)
    owner = validate_owner(root, cfg, env); gate = validate_gate(root, cfg)
    package = package_hashes(root); pcfg, parent_pins = validate_parent_evidence(root, cfg); parent = import_parent(root, cfg)
    parent.validate_small_assets(root, pcfg); source = parent.validate_source(root, pcfg)
    return {"slurm": slurm, "owner_sha256": owner, "gate_sha256": gate, "package_sha256": package,
            "parent_pins": parent_pins, "source": source, "parent_cfg": pcfg, "parent": parent}


def revalidate(root, cfg, env, initial):
    current = prepare_authority(root, cfg, env)
    for key in ("slurm", "owner_sha256", "gate_sha256", "package_sha256", "parent_pins", "source"):
        if current[key] != initial[key]: raise IntegrityError("authority drift: " + key)
    return current


def result_files(result, status, initial, post, observation_rel, observation_sha):
    passed = status == "LEAF_ADAPTER_PREFLIGHT_PASS"
    metrics = {"status": status, "semantic_success": True, "denominator": 6, "target_count": 6,
        "probe_call_count": result["probe_call_count"], "materialized_record_count": len(result["records"]),
        "typed_block": result["typed_block"], "representative": False, "concordance_evidence": False,
        "annotation_executed": False, "RepeatMasker_executed": False, "geometry_evaluated": False,
        "claim_eligible": False, "data_authorized": False, "gpu_authorized": False, "s1_authorized": False}
    if passed:
        metrics.update({"sequence_order_raw_class_identical": True,
          "ordered_sequence_class_semantic_sha256_control": result["ordered_sequence_class_semantic_sha256_control"],
          "ordered_sequence_class_semantic_sha256_candidate": result["ordered_sequence_class_semantic_sha256_candidate"],
          "control_library_sha256": result["control_library_sha256"], "candidate_library_sha256": result["candidate_library_sha256"]})
    report = dict(metrics, interpretation="syntactic six-record leaf adapter contract only",
                  failures=result["failures"], close_audit=result["close_audit"],
                  observation_bundle=observation_rel, observation_manifest_sha256=observation_sha)
    files = {"metrics.json": canonical_json(metrics), "report.json": canonical_json(report),
        "probe_matrix.json": canonical_json({"observations": result["observations"], "failures": result["failures"]}),
        "record_manifest.json": canonical_json(result["records"]),
        "SOURCE_MANIFEST.json": canonical_json({"initial": initial["source"], "post_probe": post["source"],
                                                  "parent_pins": initial["parent_pins"]}),
        "SLURM_AUTHORITY.json": canonical_json({"initial": initial["slurm"], "post_probe": post["slurm"]}),
        "env.json": canonical_json({"python": sys.version, "slurm_job_id": os.environ.get("SLURM_JOB_ID")}),
        "RUN_MANIFEST.json": canonical_json({"package_sha256_initial": initial["package_sha256"],
            "package_sha256_post_probe": post["package_sha256"], "gate_sha256_initial": initial["gate_sha256"],
            "gate_sha256_post_probe": post["gate_sha256"], "owner_sha256_initial": initial["owner_sha256"],
            "owner_sha256_post_probe": post["owner_sha256"], "parent_pins": initial["parent_pins"],
            "observation_manifest_sha256": observation_sha})}
    if passed:
        files["canonical_name_view.fa"] = result["canonical_name_view.fa"]
        files["accession_version_view.fa"] = result["accession_version_view.fa"]
    return files


def formal(root, cfg, attempt, controller, authority_out=None, scheduler=None):
    initial = prepare_authority(root, cfg, os.environ, scheduler)
    if authority_out is not None: authority_out.update(initial)
    expected_parent_hash = initial["parent_pins"]["parent_audited_manifest_sha256"]
    configured_parent_hash = cfg["parent_contract"]["artifacts"][
      "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256"]
    if expected_parent_hash != configured_parent_hash:
        raise IntegrityError("parent observation hash binding drift")
    preview = root / cfg["preview_root"]
    publish(preview, attempt, "FORMAL_RUNNING", False,
            {"metrics.json": canonical_json({"status": "FORMAL_RUNNING"}),
             "report.json": canonical_json({"status": "FORMAL_RUNNING"}),
             "RUN_MANIFEST.json": canonical_json({"package_sha256": initial["package_sha256"]})})
    result = probe_with_lifecycle(root, cfg, initial["parent"], initial["parent_cfg"], controller,
                                  preview, attempt)
    observation = result["observation_bundle"]; observation_sha = result["observation_manifest_sha256"]
    status = "LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK" if result["typed_block"] else "LEAF_ADAPTER_PREFLIGHT_PASS"
    post = revalidate(root, cfg, os.environ, initial)
    files = result_files(result, status, initial, post, observation.relative_to(root).as_posix(), observation_sha)
    def terminal(_):
        revalidate(root, cfg, os.environ, initial)
        if verify_observation(observation, attempt, expected_parent_hash) != observation_sha:
            raise IntegrityError("observation drift before pointer")
    publish(preview, attempt, status, True, files, terminal, controller,
            expected_parent_hash=expected_parent_hash)
    return status


def failure_files(exc, initial):
    metrics = {"status": "LEAF_ADAPTER_PREFLIGHT_FAILED", "semantic_success": False, "denominator": 6,
      "representative": False, "concordance_evidence": False, "annotation_executed": False,
      "RepeatMasker_executed": False, "geometry_evaluated": False, "claim_eligible": False,
      "data_authorized": False, "gpu_authorized": False, "s1_authorized": False}
    return {"metrics.json": canonical_json(metrics), "report.json": canonical_json(dict(metrics,
             error_type=type(exc).__name__, error=str(exc))), "probe_matrix.json": canonical_json({"observations": [], "failures": []}),
        "record_manifest.json": "[]\n", "SOURCE_MANIFEST.json": canonical_json({"initial": initial.get("source")}),
        "SLURM_AUTHORITY.json": canonical_json({"initial": initial.get("slurm")}), "env.json": canonical_json({"python": sys.version}),
        "RUN_MANIFEST.json": canonical_json({"package_sha256": initial.get("package_sha256"),
             "gate_sha256": initial.get("gate_sha256"), "owner_sha256": initial.get("owner_sha256"),
             "parent_pins": initial.get("parent_pins")})}


def publish_failure(root, cfg, attempt, exc, initial, controller):
    try:
        revalidate(root, cfg, os.environ, initial)
        observation = getattr(exc, "observation_bundle", None); observation_sha = getattr(exc, "observation_manifest_sha256", None)
        expected_parent_hash = cfg["parent_contract"]["artifacts"][
          "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256"]
        if observation is not None and verify_observation(observation, attempt, expected_parent_hash) != observation_sha:
            raise IntegrityError("failure observation evidence drift")
        publish(root / cfg["preview_root"], attempt, "LEAF_ADAPTER_PREFLIGHT_FAILED", False,
                failure_files(exc, initial), lambda _: revalidate(root, cfg, os.environ, initial), controller)
        return True
    except BaseException: return False


def attempt_failure(root, cfg, attempt, exc):
    path = root / cfg["preview_root"] / "attempt_failures" / (safe_attempt(attempt) + ".json")
    atomic_write(path, canonical_json({"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt,
        "semantic_success": False, "error_type": type(exc).__name__, "error": str(exc)}).encode())


def static_preview(root, cfg, attempt):
    validate_config(cfg); validate_parent_evidence(root, cfg); import_parent(root, cfg)
    preview = root / cfg["preview_root"]; (preview / "logs").mkdir(parents=True, exist_ok=True)
    current = current_bytes(preview)
    if os.path.lexists(preview / cfg["owner_lock_name"]): raise IntegrityError("formal owner exists")
    if current is not None and verify_bundle(preview)["status"] != "IMPLEMENTED_NOT_RUN": raise IntegrityError("static cannot supersede formal")
    publish(preview, attempt, "IMPLEMENTED_NOT_RUN", False,
       {"metrics.json": canonical_json({"status": "IMPLEMENTED_NOT_RUN", "semantic_success": False}),
        "report.json": canonical_json({"status": "IMPLEMENTED_NOT_RUN", "real_h5_opened": False,
          "real_famdb_api_called": False, "RepeatMasker_executed": False}),
        "RUN_MANIFEST.json": canonical_json({"package_sha256": package_hashes(root)})},
       before_pointer=lambda _: (_ for _ in ()).throw(IntegrityError("formal owner appeared"))
         if os.path.lexists(preview / cfg["owner_lock_name"]) else None,
       expected=current)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--attempt-id", default="manual")
    ap.add_argument("--static-preview", action="store_true"); ap.add_argument("--record-wrapper-failure", action="store_true")
    args = ap.parse_args(argv); cfg = load_config(args.config); root = Path(cfg["project_root"]); initial = {}; controller = None
    try:
        validate_config(cfg)
        if args.static_preview: static_preview(root, cfg, args.attempt_id); return 0
        # Allocation authority precedes every parent artifact import and every H5 access.
        scheduler = query_slurm(root, cfg, os.environ)
        if args.record_wrapper_failure:
            parent_hash = cfg["parent_contract"]["artifacts"][
              "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256"]
            if wrapper_terminal_already_closed(root / cfg["preview_root"], args.attempt_id, parent_hash):
                return 0
        parent = import_parent(root, cfg); controller = parent.DeferredCleanupSignals().enter()
        if args.record_wrapper_failure:
            initial.update(prepare_authority(root, cfg, os.environ, scheduler)); raise IntegrityError("sbatch wrapper failure")
        status = formal(root, cfg, args.attempt_id, controller, initial, scheduler)
        return 0 if status in {"LEAF_ADAPTER_PREFLIGHT_PASS", "LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK"} else 2
    except BaseException as exc:
        if controller is not None:
            try: controller_rows = controller.pending_rows(); exc.pending_cleanup_signals = controller_rows
            except BaseException: pass
        if not args.static_preview and initial and publish_failure(root, cfg, args.attempt_id, exc, initial, controller): pass
        else: attempt_failure(root, cfg, args.attempt_id, exc)
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
