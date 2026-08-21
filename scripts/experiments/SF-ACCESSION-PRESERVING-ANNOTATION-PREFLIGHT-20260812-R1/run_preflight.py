#!/usr/bin/env python3
"""Accession-preserving RepeatMasker paired preflight (formal compute is Slurm-only)."""
from __future__ import annotations

import argparse
import csv
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EXP_ID = "SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1"
SCHEMA = "TEFM-SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-1.0.0"
FINAL_AUTH = {"full_catalog_stage_authorized": False, "homology_split_authorized": False,
              "data_stage_authorized": False, "gpu_authorized": False, "s1_authorized": False}


class IntegrityError(RuntimeError):
    pass


class ValidNegative(RuntimeError):
    def __init__(self, metrics):
        super().__init__("paired roundtrip acceptance gate not met")
        self.metrics = metrics


_NO_CAS = object()


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
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(str(tmp), str(path))


def write_json(path, obj):
    atomic_write(path, canonical_json(obj).encode())


def load_config(path):
    cfg = json.loads(Path(path).read_text())
    if cfg.get("schema_version") != SCHEMA or cfg.get("exp_id") != EXP_ID:
        raise IntegrityError("config schema/exp_id mismatch")
    return cfg


def validate_selected(cfg):
    rows = cfg["selected_records"]
    if len(rows) != 6 or len({r["versioned_accession"] for r in rows}) != 6:
        raise IntegrityError("selected record count/uniqueness mismatch")
    if [r["expected_label"] for r in rows] != [1, 2, 2, 3, 4, 5]:
        raise IntegrityError("selected label shape drift")
    if {r["partition"] for r in rows} != {"dfam39_full.3.h5", "dfam39_full.7.h5"}:
        raise IntegrityError("selected partition shape drift")
    l1 = [r for r in rows if r["raw_class"] == "LINE/L1"]
    if len(l1) != 2 or {r["canonical_name"] for r in l1} != {"L1HS_3end", "L1HS_5end"}:
        raise IntegrityError("L1HS split representation drift")
    dr = [r for r in rows if r["accession"] == "DR002419729"]
    if len(dr) != 1 or dr[0]["canonical_name"] or dr[0]["provenance_tier"] != "DR_UNCURATED":
        raise IntegrityError("DR audit record drift")
    export = cfg.get("export_contract", {})
    if export.get("control_header_grammar") != ">{canonical_name_or_unversioned_accession}#{raw_class}" or \
       export.get("candidate_header_grammar") != ">{versioned_accession}#{raw_class}" or \
       export.get("record_order") != "selected_records_config_order" or \
       export.get("only_permitted_arm_difference") != "repeat_identifier":
        raise IntegrityError("paired export contract drift")


def validate_assets(root, cfg, include_large_stat=True):
    a = cfg["asset_contract"]
    small = {
        a["rmlib_config"]: a["rmlib_config_sha256"],
        a["layout_manifest"]: a["layout_manifest_sha256"],
        a["direct_labeler"]: a["direct_labeler_sha256"],
        a["ontology"]: a["ontology_sha256"],
        a["evaluator_contract"]: a["evaluator_contract_sha256"],
        a["repeatmasker"]: a["repeatmasker_sha256"],
        a["rmblastn"]: a["rmblastn_sha256"],
        a["matrix_18p35g"]: a["matrix_18p35g_sha256"],
        a["matrix_simple1"]: a["matrix_simple1_sha256"],
    }
    for rel, expected in small.items():
        p = Path(rel) if Path(rel).is_absolute() else root / rel
        if not p.is_file() or sha256_file(p) != expected:
            raise IntegrityError("asset hash mismatch: " + str(rel))
    for name, expected in a["famdb_code_sha256"].items():
        p = Path(a["famdb_code_dir"]) / name
        if not p.is_file() or sha256_file(p) != expected:
            raise IntegrityError("FamDB code hash mismatch: " + name)
    observed_partitions = {}
    if include_large_stat:
        famdb = root / a["famdb_dir"]
        layout = json.loads((root / a["layout_manifest"]).read_text())
        layout_rows = {x["filename"]: x for x in layout["partitions"]}
        for name, contract in a["required_partitions"].items():
            p = famdb / name
            lst = p.lstat() if p.is_symlink() else None
            target = os.readlink(p) if p.is_symlink() else ""
            if lst is None or target != contract["symlink_target"] or \
               sha256_bytes(target.encode()) != contract["symlink_target_sha256"] or \
               lst.st_ino != contract["symlink_inode"] or lst.st_mtime_ns != contract["symlink_mtime_ns"] or \
               lst.st_mode != contract["symlink_mode"]:
                raise IntegrityError("partition symlink target mismatch: " + name)
            resolved = p.resolve(strict=True)
            lr = layout_rows.get(name, {})
            observed_layout = {k: lr.get(k) for k in contract["layout"]}
            if resolved != Path(contract["symlink_target"]).resolve(strict=True) or resolved.name != name or \
               resolved.stat().st_size != contract["size_bytes"] or lr.get("size_bytes") != contract["size_bytes"] or \
               resolved.stat().st_ino != contract["resolved_inode"] or \
               resolved.stat().st_mtime_ns != contract["resolved_mtime_ns"] or \
               resolved.stat().st_mode != contract["resolved_mode"] or \
               observed_layout != contract["layout"]:
                raise IntegrityError("partition identity/size mismatch: " + name)
            st = resolved.stat()
            observed_partitions[name] = {"symlink_target": os.readlink(p), "resolved_size": st.st_size,
                                          "resolved_inode": st.st_ino, "resolved_mtime_ns": st.st_mtime_ns,
                                          "resolved_mode": st.st_mode, "symlink_inode": lst.st_ino,
                                          "symlink_mtime_ns": lst.st_mtime_ns, "symlink_mode": lst.st_mode,
                                          "layout": observed_layout}
    return {"small_asset_sha256": {str(k): v for k, v in sorted(small.items())},
            "partition_observation": observed_partitions}


def package_hashes(root):
    rels = ["configs/%s.yaml" % EXP_ID,
            "scripts/experiments/%s/run_preflight.py" % EXP_ID,
            "scripts/experiments/%s/test_preflight.py" % EXP_ID,
            "sbatch/%s.sbatch" % EXP_ID,
            "docs/experiments/%s.md" % EXP_ID]
    return {rel: sha256_file(root / rel) for rel in rels}


def parse_mem_mib(value):
    m = re.fullmatch(r"([0-9]+)([KMGTP]?)", str(value).strip().upper())
    if not m:
        raise IntegrityError("invalid SLURM memory format")
    number, unit = int(m.group(1)), m.group(2)
    factors = {"": 1, "K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024, "P": 1024 ** 3}
    return int(number * factors[unit])


def validate_formal_resources(env):
    if not re.fullmatch(r"[1-9][0-9]*", env.get("SLURM_JOB_ID", "")):
        raise IntegrityError("positive numeric SLURM_JOB_ID required")
    if env.get("SLURM_CPUS_PER_TASK") != "1":
        raise IntegrityError("exactly 1 CPU required")
    if parse_mem_mib(env.get("SLURM_MEM_PER_NODE", "")) != 4096:
        raise IntegrityError("exactly 4096 MiB required")
    if env.get("SLURM_JOB_PARTITION") != "private-teodoro-gpu":
        raise IntegrityError("exact reviewed partition required")
    gpu_keys = ("CUDA_VISIBLE_DEVICES", "SLURM_GPUS", "SLURM_JOB_GPUS", "SLURM_GPUS_ON_NODE")
    if any(env.get(k, "").strip() not in ("", "NoDevFiles") for k in gpu_keys):
        raise IntegrityError("0 GPU required")


def parse_scontrol_oneline(text):
    if not isinstance(text, str) or not text.strip() or "\x00" in text or len(text.encode()) > 1024 * 1024:
        raise IntegrityError("scontrol output empty/oversized/invalid")
    if "\r" in text or not text.endswith("\n") or text.count("\n") != 1:
        raise IntegrityError("scontrol must return exactly one record")
    line = text[:-1]
    matches = list(re.finditer(r"(?:^| )([A-Za-z][A-Za-z0-9/:]*)=", line))
    fields = {}
    for idx, match in enumerate(matches):
        key = match.group(1)
        if key in fields:
            raise IntegrityError("duplicate scontrol field: " + key)
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
        value = line[match.end():end].strip()
        if not value:
            raise IntegrityError("empty scontrol field: " + key)
        fields[key] = value
    return fields


def validate_scontrol_fields(fields, cfg, job_id):
    contract = cfg["slurm_authority_contract"]
    expected = {"JobId": job_id, "Partition": contract["partition"],
                "TimeLimit": contract["time_limit"], "NumCPUs": contract["num_cpus"],
                "ReqTRES": contract["req_tres"], "AllocTRES": contract["alloc_tres"],
                "SubmitLine": contract["submit_line"], "Command": contract["command"],
                "WorkDir": contract["work_dir"]}
    missing = sorted(set(expected) - set(fields))
    if missing:
        raise IntegrityError("scontrol required fields missing: " + ",".join(missing))
    for key, value in expected.items():
        if fields[key] != value:
            raise IntegrityError("scontrol %s mismatch" % key)
    if any("gpu" in fields[key].casefold() or "gres" in fields[key].casefold()
           for key in ("ReqTRES", "AllocTRES")):
        raise IntegrityError("scontrol TRES contains GPU/GRES")
    return expected


def query_slurm_authority(root, cfg, env, executor=None):
    validate_formal_resources(env)
    contract = cfg["slurm_authority_contract"]
    job_id = env["SLURM_JOB_ID"]
    scontrol = Path(contract["scontrol_binary"])
    sbatch = root / "sbatch" / (EXP_ID + ".sbatch")
    if not scontrol.is_file() or scontrol.is_symlink() or sha256_file(scontrol) != contract["scontrol_sha256"]:
        raise IntegrityError("scontrol binary identity mismatch")
    if sbatch.resolve(strict=True) != Path(contract["command"]) or sbatch.is_symlink() or \
       sha256_file(sbatch) != contract["sbatch_sha256"]:
        raise IntegrityError("reviewed sbatch identity mismatch")
    timeout_bin = Path(cfg["execution_contract"]["timeout_binary"])
    cmd = [str(timeout_bin), "--signal=TERM", "--kill-after=%ss" % contract["query_kill_after_seconds"],
           "%ss" % contract["query_timeout_seconds"], str(scontrol), "show", "job", job_id, "-o"]
    execute = executor or run_bounded_command
    rc, stdout, stderr = execute(cmd, contract["query_outer_cleanup_timeout_seconds"])
    if rc != 0:
        raise IntegrityError("scontrol query nonzero/timeout exit: %d" % rc)
    if stderr:
        raise IntegrityError("scontrol query emitted stderr")
    fields = parse_scontrol_oneline(stdout)
    selected = validate_scontrol_fields(fields, cfg, job_id)
    return {"fields": selected, "stdout_sha256": sha256_bytes(stdout.encode()), "command": cmd,
            "scontrol_sha256": contract["scontrol_sha256"], "sbatch_sha256": contract["sbatch_sha256"]}


def stable_slurm_identity(audit):
    return {k: audit[k] for k in ("fields", "command", "scontrol_sha256", "sbatch_sha256")}


def requery_same_slurm_authority(root, cfg, env, before, phase):
    current = query_slurm_authority(root, cfg, env)
    if stable_slurm_identity(current) != stable_slurm_identity(before):
        raise IntegrityError("Slurm authority changed before " + phase)
    return current


def validate_code_review_gate(root, cfg):
    gate_path = root / cfg["code_review_gate_path"]
    if not gate_path.is_file():
        raise IntegrityError("fresh code-review PASS gate required")
    gate = json.loads(gate_path.read_text())
    if gate.get("exp_id") != EXP_ID:
        raise IntegrityError("code-review exp_id mismatch")
    if gate.get("verdict") not in {"PASS", "PASS_WITH_WARNINGS"}:
        raise IntegrityError("fresh code-review PASS gate required")
    blockers = gate.get("blockers_open")
    if isinstance(blockers, bool) or not isinstance(blockers, int) or blockers != 0:
        raise IntegrityError("code-review blockers_open must be integer zero")
    reviewed = gate.get("reviewed_files")
    if not isinstance(reviewed, dict):
        raise IntegrityError("code-review reviewed_files missing")
    expected = {
        "configs/%s.yaml" % EXP_ID,
        "scripts/experiments/%s/run_preflight.py" % EXP_ID,
        "scripts/experiments/%s/test_preflight.py" % EXP_ID,
        "sbatch/%s.sbatch" % EXP_ID,
        "docs/experiments/%s.md" % EXP_ID,
    }
    observed = set()
    for rel, expected_sha in reviewed.items():
        if not isinstance(rel, str) or not re.fullmatch(r"[0-9a-f]{64}", str(expected_sha)):
            raise IntegrityError("malformed code-review reviewed_files")
        rp = Path(rel)
        if rp.is_absolute() or ".." in rp.parts:
            raise IntegrityError("unsafe reviewed file path")
        p = root / rel
        if not p.is_file() or p.is_symlink() or sha256_file(p) != expected_sha:
            raise IntegrityError("stale code-review hash: " + rel)
        if rel in expected:
            observed.add(rel)
    if observed != expected:
        raise IntegrityError("code-review package coverage incomplete")
    return gate


def validate_owner_lock(root, cfg, env):
    lock = root / cfg["preview_root"] / cfg["owner_lock_name"]
    if lock.is_symlink() or not lock.is_dir():
        raise IntegrityError("owner lock directory missing or unsafe")
    actual = {p.name for p in lock.iterdir()}
    if actual != {"job_id"} or (lock / "job_id").is_symlink():
        raise IntegrityError("owner lock exact file set mismatch")
    job = (lock / "job_id").read_text().strip()
    if job != env["SLURM_JOB_ID"] or not re.fullmatch(r"[1-9][0-9]*", job):
        raise IntegrityError("owner lock job binding mismatch")
    return sha256_file(lock / "job_id")


def load_labeler(root, cfg):
    path = root / cfg["asset_contract"]["direct_labeler"]
    spec = importlib.util.spec_from_file_location("pinned_direct_s0_data", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    ontology = mod.load_ontology(root / cfg["asset_contract"]["ontology"])
    hard = set(cfg["label_contract"]["hard_negative_terms"])
    return lambda raw_class: mod.classify_annotation(raw_class, ontology, hard)[:2]


def verify_family_rows(cfg, observed):
    by_acc = {r["versioned_accession"]: r for r in observed}
    if len(by_acc) != len(observed):
        raise IntegrityError("duplicate observed family accession")
    verified = []
    for expected in cfg["selected_records"]:
        row = by_acc.get(expected["versioned_accession"])
        if row is None:
            raise IntegrityError("missing selected family: " + expected["versioned_accession"])
        for key in ("accession", "canonical_name", "raw_class", "consensus_length", "consensus_sha256", "partition"):
            if row.get(key) != expected[key]:
                raise IntegrityError("family field drift: %s:%s" % (expected["versioned_accession"], key))
        verified.append(dict(row, expected_label=expected["expected_label"], provenance_tier=expected["provenance_tier"]))
    return verified


def read_selected_families(root, cfg):
    code_dir = cfg["asset_contract"]["famdb_code_dir"]
    sys.path.insert(0, code_dir)
    try:
        from famdb_classes import FamDB
        db = FamDB(str(root / cfg["asset_contract"]["famdb_dir"]), "r")
        out = []
        for expected in cfg["selected_records"]:
            partition_no = int(expected["partition"].rsplit(".", 2)[1])
            if partition_no not in db.files:
                raise IntegrityError("expected FamDB partition unavailable")
            fam = db.files[partition_no].get_family_by_accession(expected["accession"])
            if fam is None:
                raise IntegrityError("FamDB accession missing: " + expected["accession"])
            raw = fam.repeat_type + (("/" + fam.repeat_subtype) if fam.repeat_subtype else "")
            seq = (fam.consensus or "").upper().replace("U", "T")
            out.append({"versioned_accession": fam.accession_with_optional_version(), "accession": fam.accession,
                        "canonical_name": fam.name or "", "raw_class": raw, "consensus": seq,
                        "consensus_length": len(seq), "consensus_sha256": sha256_bytes(seq.encode()),
                        "partition": expected["partition"]})
        db.finalize()
    finally:
        sys.path.remove(code_dir)
    return verify_family_rows(cfg, out)


def fasta_record(header, seq):
    return ">" + header + "\n" + "\n".join(seq[i:i + 60] for i in range(0, len(seq), 60)) + "\n"


def build_fastas(rows):
    query, control, candidate, manifest = [], [], [], []
    for idx, row in enumerate(rows, 1):
        qid = "probe_%02d" % idx
        control_id = row["canonical_name"] or row["accession"]
        candidate_id = row["versioned_accession"]
        seq = row["consensus"]
        query.append(fasta_record(qid, seq))
        control.append(fasta_record(control_id + "#" + row["raw_class"], seq))
        candidate.append(fasta_record(candidate_id + "#" + row["raw_class"], seq))
        manifest.append({"query_id": qid, "control_repeat_id": control_id,
                         "candidate_repeat_id": candidate_id, "raw_class": row["raw_class"],
                         "expected_label": row["expected_label"], "record_order": idx,
                         "versioned_accession": row["versioned_accession"], "accession": row["accession"],
                         "partition": row["partition"], "provenance_tier": row["provenance_tier"],
                         "consensus_length": len(seq), "consensus_sha256": row["consensus_sha256"],
                         "control_record_sha256": sha256_bytes(fasta_record(control_id + "#" + row["raw_class"], seq).encode()),
                         "candidate_record_sha256": sha256_bytes(fasta_record(candidate_id + "#" + row["raw_class"], seq).encode())})
    if len({r["control_repeat_id"] for r in manifest}) != 6:
        raise IntegrityError("control library header collision")
    control_s, candidate_s = "".join(control), "".join(candidate)
    verify_export_pair(control_s, candidate_s, manifest)
    return "".join(query), control_s, candidate_s, manifest


def parse_fasta(text):
    records, header, chunks = [], None, []
    for line in text.splitlines():
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(chunks)))
            header, chunks = line[1:], []
        elif header is None or not line or not re.fullmatch(r"[A-Za-z*.-]+", line):
            raise IntegrityError("malformed exported FASTA")
        else:
            chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def verify_export_pair(control_s, candidate_s, manifest):
    control, candidate = parse_fasta(control_s), parse_fasta(candidate_s)
    if len(control) != 6 or len(candidate) != 6 or len(manifest) != 6:
        raise IntegrityError("export record cardinality mismatch")
    for idx, ((ch, cs), (ah, ass), expected) in enumerate(zip(control, candidate, manifest), 1):
        if idx != expected["record_order"] or cs != ass or sha256_bytes(cs.encode()) != expected["consensus_sha256"]:
            raise IntegrityError("export sequence/order mismatch")
        if ch != expected["control_repeat_id"] + "#" + expected["raw_class"]:
            raise IntegrityError("control header grammar mismatch")
        if ah != expected["candidate_repeat_id"] + "#" + expected["raw_class"]:
            raise IntegrityError("candidate header grammar mismatch")
        if ch.split("#", 1)[1] != ah.split("#", 1)[1]:
            raise IntegrityError("raw class differs between export arms")
        if sha256_bytes(fasta_record(ch, cs).encode()) != expected["control_record_sha256"] or \
           sha256_bytes(fasta_record(ah, ass).encode()) != expected["candidate_record_sha256"]:
            raise IntegrityError("post-export record hash mismatch")


def parse_repeatmasker_out(text):
    rows = []
    if not text.strip():
        raise IntegrityError("empty RepeatMasker output")
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if not fields[0].isdigit():
            continue
        if len(fields) < 15:
            raise IntegrityError("malformed RepeatMasker data row")
        try:
            row = {"score": int(fields[0]), "div": fields[1], "del": fields[2], "ins": fields[3],
                   "query_id": fields[4], "query_start": int(fields[5]), "query_end": int(fields[6]),
                   "query_left": fields[7], "strand": fields[8], "repeat_id": fields[9],
                   "raw_class": fields[10], "repeat_begin": fields[11], "repeat_end": fields[12],
                   "repeat_left": fields[13], "rm_hit_id": fields[14],
                   "overlap_flag": "*" if len(fields) > 15 and fields[15] == "*" else ""}
        except (ValueError, IndexError) as exc:
            raise IntegrityError("malformed RepeatMasker data row") from exc
        rows.append(row)
    return rows


def semantic_geometry(row):
    return {k: row[k] for k in ("score", "div", "del", "ins", "query_id", "query_start", "query_end",
                                             "query_left", "strand", "raw_class", "repeat_begin", "repeat_end",
                                             "repeat_left", "rm_hit_id", "overlap_flag")}


def evaluate_pair(control_rows, candidate_rows, manifest, labeler, raise_on_negative=True):
    expected = {r["query_id"]: r for r in manifest}
    if len(expected) != 6:
        raise IntegrityError("manifest query cardinality mismatch")
    for row in control_rows + candidate_rows:
        if row["query_id"] not in expected:
            raise IntegrityError("unexpected query in RepeatMasker output")
    cgeo = sorted((semantic_geometry(r) for r in control_rows), key=canonical_json)
    ageo = sorted((semantic_geometry(r) for r in candidate_rows), key=canonical_json)
    c_hash, a_hash = sha256_bytes(canonical_json(cgeo).encode()), sha256_bytes(canonical_json(ageo).encode())
    missing = ambiguous = mismatch = control_missing = control_ambiguous = 0
    direct_control, direct_candidate, audit = [], [], []
    for qid, exp in sorted(expected.items()):
        c = [r for r in control_rows if r["query_id"] == qid]
        a = [r for r in candidate_rows if r["query_id"] == qid]
        control_ids = {r["repeat_id"] for r in c}
        candidate_ids = {r["repeat_id"] for r in a}
        if exp["control_repeat_id"] not in control_ids:
            control_missing += 1
        if control_ids and control_ids != {exp["control_repeat_id"]}:
            control_ambiguous += 1
        if exp["candidate_repeat_id"] not in candidate_ids:
            missing += 1
        if candidate_ids and candidate_ids != {exp["candidate_repeat_id"]}:
            ambiguous += 1
        for side, hits, payload in (("control", c, direct_control), ("candidate", a, direct_candidate)):
            for hit in hits:
                state, label = labeler(hit["raw_class"])
                payload.append({"query_id": qid, "raw_class": hit["raw_class"], "state": state, "label": label})
                if state != "P" or label != exp["expected_label"] or hit["raw_class"] != exp["raw_class"]:
                    mismatch += 1
                audit.append(dict(hit, side=side, direct_state=state, direct_label=label))
    dc = sha256_bytes(canonical_json(sorted(direct_control, key=canonical_json)).encode())
    da = sha256_bytes(canonical_json(sorted(direct_candidate, key=canonical_json)).encode())
    metrics = {"selected_record_count": 6, "control_hit_count": len(control_rows),
               "candidate_hit_count": len(candidate_rows), "candidate_hit_join_rate": (6 - missing) / 6,
               "missing_join_count": missing, "ambiguous_join_count": ambiguous,
               "control_missing_join_count": control_missing, "control_ambiguous_join_count": control_ambiguous,
               "raw_class_or_label_mismatch_count": mismatch, "control_geometry_sha256": c_hash,
               "candidate_geometry_sha256": a_hash, "geometry_semantic_hash_equal": c_hash == a_hash,
               "control_direct_label_payload_sha256": dc, "candidate_direct_label_payload_sha256": da,
               "direct_label_payload_hash_equal": dc == da}
    metrics["acceptance_pass"] = not (missing or ambiguous or control_missing or control_ambiguous or mismatch or c_hash != a_hash or dc != da)
    if not metrics["acceptance_pass"] and raise_on_negative:
        raise ValidNegative(metrics)
    return metrics, audit


def run_bounded_command(cmd, outer_timeout):
    proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=outer_timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        finally:
            proc.communicate()
        raise IntegrityError("outer RepeatMasker cleanup timeout") from exc
    return proc.returncode, stdout, stderr


def run_rm(executable, args, library, probe, out_dir, execution):
    out_dir.mkdir(parents=True)
    timeout_bin = Path(execution["timeout_binary"])
    if not timeout_bin.is_file() or not os.access(timeout_bin, os.X_OK):
        raise IntegrityError("pinned timeout binary unavailable")
    cmd = [str(timeout_bin), "--signal=TERM", "--kill-after=%ss" % execution["kill_after_seconds"],
           "%ss" % execution["repeatmasker_timeout_seconds_per_arm"], str(executable)] + list(args) + \
          ["-dir", str(out_dir), "-lib", str(library), str(probe)]
    rc, stdout, stderr = run_bounded_command(cmd, execution["outer_cleanup_timeout_seconds"])
    if rc != 0:
        reason = "timeout" if rc in {124, 137} else "nonzero"
        raise IntegrityError("RepeatMasker %s exit: %d" % (reason, rc))
    candidate = out_dir / (probe.name + ".out")
    if not candidate.is_file():
        raise IntegrityError("RepeatMasker .out missing")
    return cmd, candidate.read_text(), stdout, stderr


def write_tsv(path, rows):
    rows = list(rows)
    fields = sorted({k for row in rows for k in row})
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(Path(path).parent), newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows); tmp = fh.name
        fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)


@contextlib.contextmanager
def state_writer_mutex(preview):
    preview = Path(preview)
    preview.mkdir(parents=True, exist_ok=True)
    lock_path = preview / ".state-writer.lock"
    with lock_path.open("a+") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise IntegrityError("canonical state writer mutex is busy") from exc
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def current_bytes(preview):
    path = Path(preview) / "CURRENT"
    return path.read_bytes() if path.is_file() else None


def owner_entry_present(preview, cfg):
    return os.path.lexists(str(Path(preview) / cfg["owner_lock_name"]))


def publish_bundle(preview, attempt, files, status, semantic_success, before_pointer=None,
                   mutex_held=False, expected_current=_NO_CAS):
    preview = Path(preview)
    if not mutex_held:
        with state_writer_mutex(preview):
            return publish_bundle(preview, attempt, files, status, semantic_success, before_pointer,
                                  mutex_held=True, expected_current=expected_current)
    states = preview / "states"
    states.mkdir(parents=True, exist_ok=True)
    bundle_id = "%s-%s-%s" % (attempt, status.lower(), int(time.time_ns()))
    stage = states / ("." + bundle_id + ".tmp")
    final = states / bundle_id
    stage.mkdir()
    for name, data in files.items():
        p = stage / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else str(data).encode())
    status_obj = {"schema_version": SCHEMA, "exp_id": EXP_ID, "status": status,
                  "semantic_success": semantic_success, "attempt_id": attempt,
                  "authorization": dict(FINAL_AUTH, representative_window_cpu_gate_authorized=(status == "PREFLIGHT_PASS"))}
    write_json(stage / "STATUS.json", status_obj)
    entries = []
    for p in sorted(stage.rglob("*")):
        if p.is_file() and p.name != "PAYLOAD_MANIFEST.json":
            entries.append({"path": p.relative_to(stage).as_posix(), "size": p.stat().st_size, "sha256": sha256_file(p)})
    write_json(stage / "PAYLOAD_MANIFEST.json", {"schema_version": SCHEMA, "files": entries})
    os.replace(stage, final)
    dfd = os.open(str(states), os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    if before_pointer:
        before_pointer(final)
    if expected_current is not _NO_CAS and current_bytes(preview) != expected_current:
        raise IntegrityError("canonical CURRENT compare-and-swap failed")
    atomic_write(preview / "CURRENT", ("states/" + bundle_id + "\n").encode())
    dfd = os.open(str(preview), os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return final


def verify_bundle(preview):
    target = (preview / "CURRENT").read_text().strip()
    if not target.startswith("states/") or ".." in target:
        raise IntegrityError("invalid CURRENT pointer")
    bundle = preview / target
    manifest = json.loads((bundle / "PAYLOAD_MANIFEST.json").read_text())
    expected = {x["path"] for x in manifest["files"]} | {"PAYLOAD_MANIFEST.json"}
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    if actual != expected or any(p.is_symlink() for p in bundle.rglob("*")):
        raise IntegrityError("immutable bundle exact file set mismatch")
    for item in manifest["files"]:
        p = bundle / item["path"]
        if p.stat().st_size != item["size"] or sha256_file(p) != item["sha256"]:
            raise IntegrityError("bundle hash mismatch: " + item["path"])
    return json.loads((bundle / "STATUS.json").read_text())


def static_preview(root, cfg, attempt="static-preview"):
    validate_selected(cfg)
    validate_assets(root, cfg, include_large_stat=False)
    preview = root / cfg["preview_root"]
    (preview / "logs").mkdir(parents=True, exist_ok=True)
    with state_writer_mutex(preview):
        initial = current_bytes(preview)
        if owner_entry_present(preview, cfg):
            raise IntegrityError("static preview forbidden while a formal owner lock exists")
        if initial is not None:
            current = verify_bundle(preview)
            if current.get("status") != "IMPLEMENTED_NOT_RUN":
                raise IntegrityError("static preview cannot supersede a formal canonical state")
        package = {"package_sha256": package_hashes(root), "scientific_result_precomputed": False,
                   "real_repeatmasker_executed": False, "real_h5_opened": False}
        files = {"metrics.json": canonical_json({"profile": cfg["profile"], "semantic_success": False,
                                                   "status": "IMPLEMENTED_NOT_RUN"}),
                 "report.json": canonical_json(package), "RUN_MANIFEST.json": canonical_json(package)}
        def static_cas(_bundle):
            if current_bytes(preview) != initial or owner_entry_present(preview, cfg):
                raise IntegrityError("static preview lost CURRENT/owner compare-and-swap")
        return publish_bundle(preview, attempt, files, "IMPLEMENTED_NOT_RUN", False,
                              before_pointer=static_cas, mutex_held=True, expected_current=initial)


def build_formal_payload(cfg, status, metrics, audit, probe_s, control_s, candidate_s,
                         cout, aout, commands, export_manifest, source_before, source_after,
                         package, gate_sha, owner_lock_sha, env, slurm_authority):
    """Build both PASS and valid-negative bundles from the same complete RM evidence."""
    semantic = status in {"PREFLIGHT_PASS", "PREFLIGHT_VALID_NEGATIVE"}
    return {"probe.fa": probe_s, "control.lib.fa": control_s, "candidate.lib.fa": candidate_s,
            "control.repeatmasker.out": cout, "candidate.repeatmasker.out": aout,
            "selected_family_manifest.json": canonical_json(export_manifest),
            "hit_provenance.json": canonical_json(audit), "commands.json": canonical_json(commands),
            "metrics.json": canonical_json(dict(metrics, profile=cfg["profile"], status=status,
                                                  semantic_success=semantic)),
            "report.json": canonical_json({"status": status, "semantic_success": semantic,
                                             "roundtrip_smoke": True, "representative_concordance": False,
                                             "direct_label_source": "raw_class_only", "metrics": metrics}),
            "SOURCE_MANIFEST.json": canonical_json({"pre": source_before, "post": source_after}),
            "SLURM_AUTHORITY.json": canonical_json(slurm_authority),
            "env.json": canonical_json(env),
            "RUN_MANIFEST.json": canonical_json({"package_sha256": package,
                                                  "code_review_gate_sha256": gate_sha,
                                                  "owner_lock_job_id_sha256": owner_lock_sha,
                                                  "export_manifest_sha256": sha256_bytes(canonical_json(export_manifest).encode())})}


def revalidate_before_pointer(root, cfg, env, package_before, gate_sha, source_before,
                              owner_lock_sha, selected_rows, slurm_authority_before):
    if validate_owner_lock(root, cfg, env) != owner_lock_sha:
        raise IntegrityError("owner lock changed before terminal pointer")
    requery_same_slurm_authority(root, cfg, env, slurm_authority_before, "terminal pointer")
    validate_code_review_gate(root, cfg)
    if sha256_file(root / cfg["code_review_gate_path"]) != gate_sha or package_hashes(root) != package_before:
        raise IntegrityError("gate/package changed before terminal pointer")
    if validate_assets(root, cfg, include_large_stat=True) != source_before:
        raise IntegrityError("source changed before terminal pointer")
    if read_selected_families(root, cfg) != selected_rows:
        raise IntegrityError("selected family payload changed before terminal pointer")


def formal(root, cfg, attempt):
    validate_formal_resources(os.environ)
    validate_selected(cfg)
    slurm_initial = query_slurm_authority(root, cfg, os.environ)
    owner_lock_sha = validate_owner_lock(root, cfg, os.environ)
    try:
        validate_code_review_gate(root, cfg)
        gate_sha = sha256_file(root / cfg["code_review_gate_path"])
        package_before = package_hashes(root)
        source_before = validate_assets(root, cfg, include_large_stat=True)
        preview = root / cfg["preview_root"]
        publish_bundle(preview, attempt, {"metrics.json": canonical_json({"status": "FORMAL_RUNNING", "semantic_success": False}),
                                          "report.json": canonical_json({"status": "FORMAL_RUNNING"})},
                       "FORMAL_RUNNING", False,
                       before_pointer=lambda _b: require_same_owner(root, cfg, os.environ, owner_lock_sha))
        rows = read_selected_families(root, cfg)
        labeler = load_labeler(root, cfg)
        for row in rows:
            state, label = labeler(row["raw_class"])
            if state != "P" or label != row["expected_label"]:
                raise IntegrityError("pinned raw-class label contract mismatch")
        probe_s, control_s, candidate_s, manifest = build_fastas(rows)
        with tempfile.TemporaryDirectory(dir=str(preview), prefix="formal-") as td:
            work = Path(td); probe = work / "probe.fa"; control = work / "control.lib.fa"; candidate = work / "candidate.lib.fa"
            probe.write_text(probe_s); control.write_text(control_s); candidate.write_text(candidate_s)
            exe = Path(cfg["asset_contract"]["repeatmasker"])
            execution = cfg["execution_contract"]
            slurm_pre_command = requery_same_slurm_authority(root, cfg, os.environ, slurm_initial,
                                                             "RepeatMasker command")
            ccmd, cout, cstdout, cstderr = run_rm(exe, cfg["repeatmasker_args"], control, probe, work / "control", execution)
            acmd, aout, astdout, astderr = run_rm(exe, cfg["repeatmasker_args"], candidate, probe, work / "candidate", execution)
            metrics, audit = evaluate_pair(parse_repeatmasker_out(cout), parse_repeatmasker_out(aout), manifest,
                                           labeler, raise_on_negative=False)
            source_after = validate_assets(root, cfg, include_large_stat=True)
            if source_before != source_after:
                raise IntegrityError("source identity changed during paired run")
            export_manifest = {"contract": cfg["export_contract"], "records": manifest,
                               "probe_fasta_sha256": sha256_bytes(probe_s.encode()),
                               "control_library_sha256": sha256_bytes(control_s.encode()),
                               "candidate_library_sha256": sha256_bytes(candidate_s.encode())}
            package = package_hashes(root)
            if package != package_before:
                raise IntegrityError("reviewed package changed during paired run")
            slurm_pre_publish = requery_same_slurm_authority(root, cfg, os.environ, slurm_initial, "publish")
            status = "PREFLIGHT_PASS" if metrics["acceptance_pass"] else "PREFLIGHT_VALID_NEGATIVE"
            commands = {"control": ccmd, "candidate": acmd, "control_stdout": cstdout,
                        "control_stderr": cstderr, "candidate_stdout": astdout, "candidate_stderr": astderr}
            env_payload = {"python": sys.version, "slurm_job_id": os.environ["SLURM_JOB_ID"],
                           "cpus": os.environ["SLURM_CPUS_PER_TASK"], "memory": os.environ["SLURM_MEM_PER_NODE"]}
            files = build_formal_payload(cfg, status, metrics, audit, probe_s, control_s, candidate_s,
                                         cout, aout, commands, export_manifest, source_before, source_after,
                                         package, gate_sha, owner_lock_sha, env_payload,
                                         {"initial": slurm_initial, "pre_command": slurm_pre_command,
                                          "pre_publish": slurm_pre_publish,
                                          "terminal_hook_revalidation_required": True})
            def final_revalidate(_bundle):
                revalidate_before_pointer(root, cfg, os.environ, package_before, gate_sha, source_before,
                                          owner_lock_sha, rows, slurm_initial)
            return publish_bundle(preview, attempt, files, status, True, before_pointer=final_revalidate)
    except Exception as exc:
        if not publish_canonical_failure_if_owned(root, cfg, attempt, exc, os.environ, owner_lock_sha):
            write_attempt_local_failure(root, cfg, attempt, exc)
        raise


def require_same_owner(root, cfg, env, owner_lock_sha):
    if validate_owner_lock(root, cfg, env) != owner_lock_sha:
        raise IntegrityError("formal owner lock changed")


def write_attempt_local_failure(root, cfg, attempt, exc):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", attempt)[:128] or "unknown"
    path = root / cfg["preview_root"] / "attempt_failures" / (safe + ".json")
    write_json(path, {"schema_version": SCHEMA, "exp_id": EXP_ID, "attempt_id": attempt,
                      "canonical_pointer_changed": False, "semantic_success": False,
                      "error_type": type(exc).__name__, "error": str(exc)})


def publish_canonical_failure_if_owned(root, cfg, attempt, exc, env, owner_lock_sha):
    try:
        require_same_owner(root, cfg, env, owner_lock_sha)
    except Exception:
        return False
    status = "PREFLIGHT_FAILED"
    metrics = dict(status=status, semantic_success=False)
    files = {"metrics.json": canonical_json(metrics),
             "report.json": canonical_json({"status": status, "semantic_success": False,
                                              "error_type": type(exc).__name__, "error": str(exc)}),
             "RUN_MANIFEST.json": canonical_json({"package_sha256": package_hashes(root),
                                                   "code_review_gate_sha256": sha256_file(root / cfg["code_review_gate_path"])
                                                   if (root / cfg["code_review_gate_path"]).is_file() else None})}
    try:
        publish_bundle(root / cfg["preview_root"], attempt, files, status, False,
                       before_pointer=lambda _b: require_same_owner(root, cfg, env, owner_lock_sha))
        return True
    except Exception:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--attempt-id", default="manual")
    ap.add_argument("--static-preview", action="store_true")
    ap.add_argument("--record-wrapper-failure", action="store_true")
    args = ap.parse_args(argv)
    cfg_path = Path(args.config).resolve(); cfg = load_config(cfg_path)
    root = Path(cfg["project_root"])
    try:
        if args.record_wrapper_failure:
            preview = root / cfg["preview_root"]
            try:
                current = verify_bundle(preview)
                if current.get("attempt_id") == args.attempt_id and current.get("status") in {
                    "PREFLIGHT_FAILED", "PREFLIGHT_VALID_NEGATIVE", "PREFLIGHT_PASS"}:
                    return 0
            except Exception:
                pass
            wrapper_exc = IntegrityError("sbatch wrapper failure")
            validate_formal_resources(os.environ)
            query_slurm_authority(root, cfg, os.environ)
            owner_sha = validate_owner_lock(root, cfg, os.environ)
            if not publish_canonical_failure_if_owned(root, cfg, args.attempt_id, wrapper_exc,
                                                      os.environ, owner_sha):
                write_attempt_local_failure(root, cfg, args.attempt_id, wrapper_exc)
            return 2
        if args.static_preview:
            static_preview(root, cfg, args.attempt_id); return 0
        formal(root, cfg, args.attempt_id); return 0
    except Exception as exc:
        write_attempt_local_failure(root, cfg, args.attempt_id, exc)
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
