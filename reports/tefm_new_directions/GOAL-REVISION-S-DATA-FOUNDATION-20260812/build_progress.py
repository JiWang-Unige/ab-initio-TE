#!/usr/bin/env python3
"""Create/check/advance immutable ordered milestone snapshots without editing the goal."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath

SCHEMA = "ordered_milestone_progress_snapshot_v2"
GOAL_ID = "TEFM_S_ACCESSION_DATA_FOUNDATION_R1"
PRIMARY = "data_foundation_gate_count_passed"
FLAGS = [
    "leaf_exact_access_gate_pass", "leaf_adapter_syntax_gate_pass",
    "paired_repeatmasker_roundtrip_gate_pass", "representative_annotation_gate_pass",
    "accession_preserving_dataset_gate_pass", "homology_split_data_gate_pass",
]
GLOBAL_ZEROS = [
    "training_executed", "gpu_executed", "gpu_hours", "direct_s0_executed", "s1_executed",
    "claim_eligible", "training_authorized", "gpu_authorized", "direct_s0_authorized",
    "s1_authorized", "claim_authorized", "full_scale_authorized",
    "silent_identifier_substitution_count", "denominator_shrinkage_count",
    "homology_component_overlap_count", "test_calibration_count",
]
EXECUTION_METRICS = [
    "leaf_exact_access_executed", "leaf_adapter_syntax_executed",
    "paired_repeatmasker_roundtrip_executed", "repeatmasker_executed", "annotation_executed",
    "geometry_evaluated", "representative_annotation_executed", "representative_prefreeze_verified",
    "occurrence_categories_exact_once_verified", "accession_dataset_executed", "data_stage_executed",
    "occurrence_ledger_conservation_verified", "per_p_identity_completeness_verified",
    "raw_class_label_source_verified", "u_x13_boundary_verified", "homology_split_executed",
    "homology_data_audit_executed", "label_blind_all_species_homology_verified",
    "component_before_split_verified", "zero_component_overlap_verified",
    "component_conflicts_typed_block_verified",
]
GATE_EXECUTION = [
    ["leaf_exact_access_executed"],
    ["leaf_adapter_syntax_executed"],
    ["paired_repeatmasker_roundtrip_executed", "repeatmasker_executed", "annotation_executed", "geometry_evaluated"],
    ["representative_annotation_executed", "representative_prefreeze_verified", "occurrence_categories_exact_once_verified"],
    ["accession_dataset_executed", "data_stage_executed", "occurrence_ledger_conservation_verified",
     "per_p_identity_completeness_verified", "raw_class_label_source_verified", "u_x13_boundary_verified"],
    ["homology_split_executed", "homology_data_audit_executed", "label_blind_all_species_homology_verified",
     "component_before_split_verified", "zero_component_overlap_verified", "component_conflicts_typed_block_verified"],
]
SCIENCE_REL = "reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/SCIENTIFIC_GATE_CONTRACT.json"
CHAIN_REL = "reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/progress_chain"
POINTER_REL = "reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/CURRENT"
REVIEW_REQUEST_REL = "reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/CARRY_FORWARD_REVIEW_REQUEST.json"
REATTESTATION_REL = "reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/CARRY_FORWARD_REATTESTATION.json"
EXPECTED_REQUEST_SHA = "dd3f85cd5d4fd155511b05bcf7415c7083273b809d30820118acf5dbc8899adc"
EXPECTED_REATTESTATION_SHA = "5db46ec5544ea2ffb9a3fdf3330b1f34bba30dac5d3a3eb0f71ffc8db429f2f3"
WRITER_LOCK_REL = "reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/.progress_writer.lock"
BEFORE_POINTER_HOOK = None

SOURCES = [
    {
      "metric": FLAGS[0], "exp_id": "SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1", "job_id": "11534847",
      "result_path": "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/result_semantic_audit.11534847.json",
      "result_sha256": "2c3d828adf339e667011981cda65aa76968ecb143f0ca9f712f4b4fe7344cd10",
      "audited_manifest_path": "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256",
      "audited_manifest_sha256": "e863e1b9d85171fa99cd3f2b47752543707a5f839325abe29df1fe972843a33a",
      "code_review_gate_path": "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/code_review_gate.json",
      "code_review_gate_sha256": "add65cea7e5cd259603b4e54cb4c8a94a5e6dd2b3019a066d5c8fdda216ed222",
      "required_reviewed_files": {
        "config": "configs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1.yaml",
        "runner": "scripts/experiments/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/close_only_probe.py",
        "evaluator_or_tests": "scripts/experiments/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/test_close_only_probe.py",
        "sbatch": "sbatch/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1.sbatch",
        "experiment_doc": "docs/experiments/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1.md"
      },
      "audited_manifest_expected_paths": [
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/preview/CURRENT",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/preview/states/slurm-11534847-leaf_close_only_pass-1786527568165971572/PAYLOAD_MANIFEST.json",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/preview/attempt_observations/slurm-11534847/3dc3bdffd78a83c4a117f45b7e6221b086ea9ded03d9714441fb38e777709476/OBSERVATION_MANIFEST.json",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/preview/states/slurm-11534847-leaf_close_only_pass-1786527568165971572/metrics.json",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/preview/states/slurm-11534847-leaf_close_only_pass-1786527568165971572/report.json",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/preview/states/slurm-11534847-leaf_close_only_pass-1786527568165971572/STATUS.json",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/result_semantic_audit.11534847.json",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/validate_goal.11534847.json",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/code_review_gate.json",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/preview/logs/slurm-11534847.out",
        "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/preview/logs/slurm-11534847.err"
      ],
      "legacy_validate_goal": {"path": "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/validate_goal.11534847.json",
        "sha256": "0be870802e4ad7567882fc2235eea7bdec7db40699e8223cb24f3d3239b14efb",
        "classification": "legacy_goal_contract_mismatch"},
      "expected_result": {"status": "LEAF_CLOSE_ONLY_PASS", "verdict": "PASS_LEAF_EXACT_ACCESS_COMPONENT",
        "semantic_success": True, "valid_negative": False, "claim_eligible": False,
        "scope_fields": {"scientific_call_count": 72, "target_count": 6, "resolved_count": 6,
          "exact_once_across_partitions": True, "fallback_count": 0, "unique_handle_count": 12,
          "closed_count": 12, "authorization.repeatmasker_authorized": False,
          "authorization.annotation_authorized": False, "authorization.annotation_roundtrip_authorized": False,
          "authorization.full_catalog_stage_authorized": False, "authorization.homology_split_authorized": False,
          "authorization.data_stage_authorized": False, "authorization.gpu_authorized": False,
          "authorization.s1_authorized": False}},
      "transition_metadata": {"eligibility_only": {"authorization.leaf_adapter_preflight_human_gate_eligible": True},
                              "authorization_promoted": False},
    },
    {
      "metric": FLAGS[1], "exp_id": "SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1", "job_id": "11535362",
      "result_path": "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/result_semantic_audit.11535362.json",
      "result_sha256": "e9b8555ea7f3febc41136e62125e9cb764692a02d48b57d651f1f8387b8a950e",
      "audited_manifest_path": "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/AUDITED_MANIFEST_11535362.sha256",
      "audited_manifest_sha256": "4e55204f1c508468ba7c917e526a67efb06bc99d20b684592e749ddccbcbd142",
      "code_review_gate_path": "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/code_review_gate.json",
      "code_review_gate_sha256": "37b679af624beddbe08d4a9b459f765db30b24daf2b4cd05ae16c82f4c4a3edb",
      "required_reviewed_files": {
        "config": "configs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1.yaml",
        "runner": "scripts/experiments/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/leaf_adapter_preflight.py",
        "evaluator_or_tests": "scripts/experiments/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/test_leaf_adapter_preflight.py",
        "sbatch": "sbatch/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1.sbatch",
        "experiment_doc": "docs/experiments/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1.md"
      },
      "audited_manifest_expected_paths": [
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/CURRENT",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/states/slurm-11535362-leaf_adapter_preflight_pass-1786531152608961344/PAYLOAD_MANIFEST.json",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/attempt_observations/slurm-11535362/cb2c5dbe13c6e91b210ab302533bf383ae4903d634b854ba92bfa14ebf749524/OBSERVATION_MANIFEST.json",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/states/slurm-11535362-leaf_adapter_preflight_pass-1786531152608961344/metrics.json",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/states/slurm-11535362-leaf_adapter_preflight_pass-1786531152608961344/report.json",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/states/slurm-11535362-leaf_adapter_preflight_pass-1786531152608961344/record_manifest.json",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/result_semantic_audit.11535362.json",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/validate_goal.11535362.json",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/code_review_gate.json",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/logs/slurm-11535362.out",
        "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/logs/slurm-11535362.err"
      ],
      "legacy_validate_goal": {"path": "outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/validate_goal.11535362.json",
        "sha256": "1fb4837f0ae30a6acd2fb0eee345c3ea5b9bad538ed23bfa0189b9a065599a60",
        "classification": "legacy_goal_contract_mismatch"},
      "expected_result": {"status": "LEAF_ADAPTER_PREFLIGHT_PASS", "verdict": "PASS_LEAF_ADAPTER_SYNTACTIC_COMPONENT",
        "semantic_success": True, "valid_negative": False, "claim_eligible": False,
        "scope_fields": {"denominator_records": 6, "materialized_record_count": 6, "probe_call_count": 72,
          "sequence_order_raw_class_identical": True, "unique_handle_count": 12, "closed_count": 12,
          "integrity.fasta_record_manifest_mapping_verified": True,
          "authorization.repeatmasker_authorized": False, "authorization.annotation_authorized": False,
          "authorization.representative_catalog_authorized": False,
          "authorization.full_catalog_stage_authorized": False, "authorization.homology_split_authorized": False,
          "authorization.data_stage_authorized": False, "authorization.training_authorized": False,
          "authorization.gpu_authorized": False, "authorization.s1_authorized": False}},
      "transition_metadata": {"eligibility_only": {"authorization.representative_cpu_proposal_human_gate_eligible": True},
                              "authorization_promoted": False},
    },
]


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def checked(root, rel, digest):
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != rel: raise RuntimeError("unsafe path: " + rel)
    path = root / rel
    cursor = root
    for part in pure.parts:
        cursor = cursor / part
        if os.path.lexists(cursor) and cursor.is_symlink(): raise RuntimeError("symlink path: " + rel)
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise RuntimeError("path escaped root: " + rel) from exc
    if not path.is_file() or path.is_symlink() or sha256_file(path) != digest: raise RuntimeError("hash/shape drift: " + rel)
    return path


def verify_manifest(root, path):
    seen = set()
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\n]+)", line)
        if not match or match.group(2) in seen: raise RuntimeError("audited manifest grammar/duplicate")
        seen.add(match.group(2)); checked(root, match.group(2), match.group(1))
    if not seen: raise RuntimeError("audited manifest empty")
    return seen


def dotted_get(value, dotted):
    for key in dotted.split("."): value = value[key]
    return value


def verify_carry_forward_reattestation(root):
    request_path = checked(root, REVIEW_REQUEST_REL, EXPECTED_REQUEST_SHA)
    request_sha = sha256_file(request_path)
    request = json.loads(request_path.read_text())
    if set(request) != {"schema_version", "goal_id", "reason", "required_verdict", "entries"} or \
       request["schema_version"] != "carry_forward_review_request_v1" or request["goal_id"] != GOAL_ID or \
       request["required_verdict"] != "PASS_OR_PASS_WITH_WARNINGS" or not isinstance(request["entries"], list) or \
       len(request["entries"]) != 2:
        raise RuntimeError("carry-forward review request schema")
    path = checked(root, REATTESTATION_REL, EXPECTED_REATTESTATION_SHA)
    value = json.loads(path.read_text())
    keys = {"schema_version", "goal_id", "status", "verdict", "blockers_open", "reviewer_backend",
            "reviewer_independence", "timestamp", "authorization", "review_request_path",
            "review_request_sha256", "reviewed_entries"}
    if set(value) != keys or value["schema_version"] != "carry_forward_reattestation_v1" or \
       value["goal_id"] != GOAL_ID or value["review_request_path"] != REVIEW_REQUEST_REL or \
       value["review_request_sha256"] != request_sha:
        raise RuntimeError("carry-forward reattestation identity/schema")
    if value["reviewer_backend"] != "independent_codex_review_b_r2" or value["reviewer_independence"] != {
      "implementer_is_reviewer": False, "review_mode": "read_only",
      "review_scope": "carry_forward_current_files_and_evidence_closure"} or \
       not re.fullmatch(r"2026-08-12T\d\d:\d\d:\d\d\+02:00", value["timestamp"]) or value["authorization"] != {
      "carry_forward_genesis_authorized": True, "goal_installation_authorized": False,
      "job_submission_authorized": False, "gpu_training_direct_s0_s1_claim_authorized": False}:
        raise RuntimeError("carry-forward reviewer metadata/authorization")
    if value["status"] != "REVIEWED" or value["verdict"] not in {"PASS", "PASS_WITH_WARNINGS"} or \
       value["blockers_open"] != 0:
        raise RuntimeError("carry-forward reattestation is NOT_REVIEWED/BLOCKED")
    entries = value["reviewed_entries"]
    if not isinstance(entries, list) or len(entries) != 2:
        raise RuntimeError("carry-forward reattestation entries")
    result = {}
    for index, entry in enumerate(entries):
        requested = request["entries"][index]
        expected_keys = {"gate_index", "gate_metric", "exp_id", "job_id", "original_code_review_gate",
                         "result_semantic_audit", "audited_manifest", "reviewed_files_current"}
        if not isinstance(entry, dict) or set(entry) != expected_keys or entry["gate_index"] != index or \
           entry["gate_metric"] != FLAGS[index] or not isinstance(entry["exp_id"], str) or not entry["exp_id"] or \
           not str(entry["job_id"]).isdigit():
            raise RuntimeError("carry-forward reattestation entry identity")
        for key in ("gate_index", "gate_metric", "exp_id", "job_id", "original_code_review_gate",
                    "result_semantic_audit", "audited_manifest"):
            if entry[key] != requested.get(key): raise RuntimeError("reattestation differs from frozen review request")
        for field in ("original_code_review_gate", "result_semantic_audit", "audited_manifest"):
            if not isinstance(entry[field], dict) or set(entry[field]) != {"path", "sha256"}:
                raise RuntimeError("carry-forward reattestation source anchor")
            checked(root, entry[field]["path"], entry[field]["sha256"])
        reviewed = entry["reviewed_files_current"]
        if not isinstance(reviewed, dict) or set(reviewed) != {"config", "runner", "evaluator_or_tests", "sbatch", "experiment_doc"}:
            raise RuntimeError("carry-forward reattestation reviewed roles")
        for role, pin in reviewed.items():
            if not isinstance(pin, dict) or set(pin) != {"path", "sha256"}:
                raise RuntimeError("carry-forward reviewed-file identity")
            checked(root, pin["path"], pin["sha256"])
            requested_pin = requested.get("reviewed_files_current", {}).get(role)
            if not isinstance(requested_pin, dict) or pin != {"path": requested_pin.get("path"), "sha256": requested_pin.get("sha256")}:
                raise RuntimeError("reattested reviewed file differs from request")
        result[entry["exp_id"]] = entry
    return result


class WriterLock:
    def __init__(self, root): self.path = root / WRITER_LOCK_REL; self.held = False
    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try: self.path.mkdir()
        except FileExistsError as exc: raise RuntimeError("progress writer lock busy") from exc
        self.held = True; return self
    def __exit__(self, *_):
        if self.held:
            self.path.rmdir(); self.held = False


def verify_evidence(root, source, passed=True, reattested=None):
    evidence_keys = {"metric", "exp_id", "job_id", "result_path", "result_sha256", "audited_manifest_path",
      "audited_manifest_sha256", "code_review_gate_path", "code_review_gate_sha256", "expected_result",
      "required_reviewed_files", "audited_manifest_expected_paths", "legacy_validate_goal", "transition_metadata"}
    if not isinstance(source, dict) or set(source) != evidence_keys or source.get("metric") not in FLAGS:
        raise RuntimeError("evidence exact schema")
    result_path = checked(root, source["result_path"], source["result_sha256"])
    manifest_path = checked(root, source["audited_manifest_path"], source["audited_manifest_sha256"])
    manifest_paths = verify_manifest(root, manifest_path)
    expected_manifest_paths = source["audited_manifest_expected_paths"]
    if not isinstance(expected_manifest_paths, list) or len(expected_manifest_paths) != len(set(expected_manifest_paths)) or \
       manifest_paths != set(expected_manifest_paths) or source["result_path"] not in manifest_paths or \
       source["code_review_gate_path"] not in manifest_paths:
        raise RuntimeError("audited manifest exact closure/anchors")
    gate_path = checked(root, source["code_review_gate_path"], source["code_review_gate_sha256"])
    gate = json.loads(gate_path.read_text())
    if gate.get("exp_id") != source["exp_id"] or gate.get("verdict") not in {"PASS", "PASS_WITH_WARNINGS"} or \
       gate.get("blockers_open") != 0 or not isinstance(gate.get("reviewed_files"), dict) or not gate["reviewed_files"]:
        raise RuntimeError("code review gate invalid")
    roles = source["required_reviewed_files"]
    if not isinstance(roles, dict) or set(roles) != {"config", "runner", "evaluator_or_tests", "sbatch", "experiment_doc"} or \
       set(roles.values()) != set(gate["reviewed_files"]):
        raise RuntimeError("required reviewed files exact set")
    replacement = None if reattested is None else reattested.get(source["exp_id"])
    if replacement is None:
        for rel, digest in gate["reviewed_files"].items(): checked(root, rel, digest)
    else:
        if replacement["original_code_review_gate"] != {"path": source["code_review_gate_path"], "sha256": source["code_review_gate_sha256"]} or \
           replacement["result_semantic_audit"] != {"path": source["result_path"], "sha256": source["result_sha256"]} or \
           replacement["audited_manifest"] != {"path": source["audited_manifest_path"], "sha256": source["audited_manifest_sha256"]}:
            raise RuntimeError("reattestation source anchor mismatch")
        replacement_files = replacement["reviewed_files_current"]
        if set(gate["reviewed_files"]) != {pin["path"] for pin in replacement_files.values()}:
            raise RuntimeError("reattestation does not cover original reviewed-file set")
        for pin in replacement_files.values(): checked(root, pin["path"], pin["sha256"])
    legacy = source.get("legacy_validate_goal")
    if legacy is not None: checked(root, legacy["path"], legacy["sha256"])
    result = json.loads(result_path.read_text()); expected = source["expected_result"]
    if not isinstance(expected, dict) or set(expected) != {"status", "verdict", "semantic_success", "valid_negative",
                                                           "claim_eligible", "scope_fields"}:
        raise RuntimeError("expected result schema")
    if passed and (not str(expected["status"]).endswith("PASS") or not str(expected["verdict"]).startswith("PASS") or \
                   expected["semantic_success"] is not True or expected["valid_negative"] is not False or expected["claim_eligible"] is not False):
        raise RuntimeError("passed evidence polarity")
    if not passed and ("TYPED_BLOCK" not in str(expected["status"]) or expected["semantic_success"] is not True or \
                       expected["valid_negative"] is not True or expected["claim_eligible"] is not False):
        raise RuntimeError("stop evidence polarity")
    if result.get("exp_id") != source["exp_id"] or str(result.get("job_id")) != str(source["job_id"]):
        raise RuntimeError("result exp/job drift")
    for key in ("status", "verdict", "semantic_success", "valid_negative", "claim_eligible"):
        if result.get(key) != expected[key]: raise RuntimeError("result semantic drift: " + key)
    if any(dotted_get(result, key) != value for key, value in expected["scope_fields"].items()):
        raise RuntimeError("result scope drift")
    index = FLAGS.index(source["metric"])
    if passed and index >= 2:
        mandatory = {"scientific_gate_contract_sha256": sha256_file(root / SCIENCE_REL),
          "gate_index": index, "gate_metric": source["metric"],
          **{"execution." + name: 1 for name in GATE_EXECUTION[index]}}
        if not mandatory.items() <= expected["scope_fields"].items():
            raise RuntimeError("extension evidence lacks scientific execution binding")
    transition = source["transition_metadata"]
    if not isinstance(transition, dict) or set(transition) != {"eligibility_only", "authorization_promoted"} or \
       not isinstance(transition["eligibility_only"], dict) or not transition["eligibility_only"] or \
       transition["authorization_promoted"] is not False:
        raise RuntimeError("transition schema")
    if any(dotted_get(result, key) != value for key, value in transition["eligibility_only"].items()):
        raise RuntimeError("transition eligibility drift")
    science = json.loads((root / SCIENCE_REL).read_text()); allowed_key = science["gates"][index]["allowed_true_authorization"]
    allowed_true = {allowed_key} if passed else set()
    declared_true = {key.split(".", 1)[1] for key, value in transition["eligibility_only"].items()
                     if key.startswith("authorization.") and value is True}
    if declared_true != allowed_true: raise RuntimeError("transition eligibility allowlist")
    authorization = result.get("authorization")
    if not isinstance(authorization, dict) or {key for key, value in authorization.items() if value is True} != allowed_true:
        raise RuntimeError("eligibility promoted to authorization")


def evidence_payload(source):
    return {key: source[key] for key in ("metric", "exp_id", "job_id", "result_path", "result_sha256",
      "audited_manifest_path", "audited_manifest_sha256", "code_review_gate_path", "code_review_gate_sha256",
      "required_reviewed_files", "audited_manifest_expected_paths", "expected_result", "legacy_validate_goal",
      "transition_metadata")}


def immutable_write(path, text):
    payload = text.encode()
    if os.path.lexists(path):
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload: raise RuntimeError("immutable collision: " + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_name(".%s.tmp.%d" % (path.name, os.getpid()))
    try:
        with tmp.open("xb") as fh: fh.write(payload); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists(): tmp.unlink()


def snapshot_name(count, digest): return "progress-%02d-%s.json" % (count, digest)


def write_snapshot(root, out_dir, snapshot):
    payload = canonical(snapshot); digest = hashlib.sha256(payload.encode()).hexdigest()
    rel = "%s/%s" % (CHAIN_REL, snapshot_name(snapshot["count"], digest))
    path = root / rel; immutable_write(path, payload)
    metrics = {PRIMARY: snapshot["count"], **{name: int(i < snapshot["count"]) for i, name in enumerate(FLAGS)},
      **snapshot["global_zero_metrics"], **snapshot["execution_metrics"], **snapshot["route_control"],
      "progress_snapshot_path": rel, "progress_snapshot_sha256": digest}
    metrics_name = "metrics-%02d-%s.json" % (snapshot["count"], digest)
    metrics_path = out_dir / metrics_name; immutable_write(metrics_path, canonical(metrics))
    return rel, digest, metrics_path


def pointer_payload(rel, digest, snapshot):
    return canonical({"schema_version": "ordered_milestone_current_v1", "path": rel, "sha256": digest,
                      "count": snapshot["count"], "event_type": snapshot["event_type"]})


def publish_pointer(root, rel, digest, snapshot, expected=None):
    path = root / POINTER_REL; path.parent.mkdir(parents=True, exist_ok=True)
    before = path.read_bytes() if path.is_file() and not path.is_symlink() else None
    if expected is not None and before != expected: raise RuntimeError("CURRENT compare-and-swap drift")
    if expected is None and os.path.lexists(path): raise RuntimeError("CURRENT already exists")
    tmp = path.with_name(".CURRENT.tmp.%d" % os.getpid())
    payload = pointer_payload(rel, digest, snapshot).encode()
    try:
        with tmp.open("xb") as fh: fh.write(payload); fh.flush(); os.fsync(fh.fileno())
        if BEFORE_POINTER_HOOK is not None: BEFORE_POINTER_HOOK()
        verify_carry_forward_reattestation(root)
        if expected is not None and path.read_bytes() != expected: raise RuntimeError("CURRENT changed before replace")
        os.replace(tmp, path)
    finally:
        if tmp.exists(): tmp.unlink()


def genesis(root, out_dir):
    with WriterLock(root):
        reattested = verify_carry_forward_reattestation(root)
        for source in SOURCES: verify_evidence(root, source, reattested=reattested)
        execution = {name: 0 for name in EXECUTION_METRICS}
        execution["leaf_exact_access_executed"] = 1; execution["leaf_adapter_syntax_executed"] = 1
        science_sha = sha256_file(root / SCIENCE_REL)
        snapshot = {"schema_version": SCHEMA, "goal_id": GOAL_ID, "count": 2, "previous": None,
          "event_type": "progress", "stop_event": None,
          "gate_order_sha256": hashlib.sha256(json.dumps(FLAGS, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
          "scientific_contract": {"path": SCIENCE_REL, "sha256": science_sha},
          "carry_forward_reattestation": {"path": REATTESTATION_REL, "sha256": EXPECTED_REATTESTATION_SHA},
          "passed_rows": [{"index": i, "metric": FLAGS[i], "evidence": evidence_payload(SOURCES[i])} for i in range(2)],
          "execution_metrics": execution, "global_zero_metrics": {name: 0 for name in GLOBAL_ZEROS},
          "route_control": {"route_stop_required": 0, "continuation_allowed": 1}}
        pointer = root / POINTER_REL
        expected = pointer.read_bytes() if pointer.is_file() and not pointer.is_symlink() else None
        result = write_snapshot(root, out_dir, snapshot)
        publish_pointer(root, result[0], result[1], snapshot, expected); return result


def advance(root, out_dir, previous_rel, evidence_path, execution_path, route_stop):
    with WriterLock(root):
      return _advance_locked(root, out_dir, previous_rel, evidence_path, execution_path, route_stop)


def _advance_locked(root, out_dir, previous_rel, evidence_path, execution_path, route_stop):
    verify_chain(root, previous_rel)
    previous_path = root / previous_rel
    if not previous_path.is_file() or previous_path.is_symlink(): raise RuntimeError("previous snapshot missing")
    previous = json.loads(previous_path.read_text()); previous_sha = sha256_file(previous_path)
    count = previous["count"] if route_stop else previous["count"] + 1
    if count > 6: raise RuntimeError("chain already complete")
    if previous["route_control"] != {"route_stop_required": 0, "continuation_allowed": 1}:
        raise RuntimeError("previous snapshot does not permit a reviewed extension")
    source = json.loads(Path(evidence_path).read_text())
    attempted_index = previous["count"]
    if attempted_index >= 6 or source.get("metric") != FLAGS[attempted_index]: raise RuntimeError("advance must address exactly next gate")
    verify_evidence(root, source, passed=not route_stop)
    execution = json.loads(Path(execution_path).read_text())
    if set(execution) != set(EXECUTION_METRICS) or any(type(v) is not int or v not in {0, 1} for v in execution.values()):
        raise RuntimeError("execution metrics exact schema")
    for index, required in enumerate(GATE_EXECUTION):
        expected = int(index < count and not (route_stop and index == attempted_index))
        if any(execution[name] != expected for name in required): raise RuntimeError("gate/execution semantic mismatch")
    snapshot = {"schema_version": SCHEMA, "goal_id": GOAL_ID, "count": count,
      "event_type": "stop" if route_stop else "progress",
      "stop_event": ({"attempted_index": attempted_index, "metric": FLAGS[attempted_index],
                       "evidence": evidence_payload(source)} if route_stop else None),
      "previous": {"path": previous_rel, "sha256": previous_sha, "count": previous["count"]},
      "gate_order_sha256": previous["gate_order_sha256"], "scientific_contract": previous["scientific_contract"],
      "carry_forward_reattestation": previous["carry_forward_reattestation"],
      "passed_rows": previous["passed_rows"] + ([] if route_stop else [{"index": attempted_index,
                     "metric": FLAGS[attempted_index], "evidence": evidence_payload(source)}]),
      "execution_metrics": execution, "global_zero_metrics": {name: 0 for name in GLOBAL_ZEROS},
      "route_control": {"route_stop_required": int(route_stop), "continuation_allowed": int(count < 6 and not route_stop)}}
    current_path = root / POINTER_REL
    if not current_path.is_file() or current_path.is_symlink(): raise RuntimeError("CURRENT missing/shape")
    expected_current = current_path.read_bytes()
    expected_pointer = json.loads(expected_current)
    if expected_pointer.get("path") != previous_rel or expected_pointer.get("sha256") != previous_sha:
        raise RuntimeError("previous is not authoritative CURRENT")
    result = write_snapshot(root, out_dir, snapshot)
    publish_pointer(root, result[0], result[1], snapshot, expected_current); return result


def verify_chain(root, snapshot_rel):
    reattested = verify_carry_forward_reattestation(root)
    initial = root / snapshot_rel
    path = checked(root, snapshot_rel, sha256_file(initial))
    snapshot = json.loads(path.read_text()); current = snapshot
    seen = set()
    while True:
        digest = sha256_file(path)
        if digest in seen: raise RuntimeError("snapshot cycle")
        seen.add(digest)
        expected_keys = {"schema_version", "goal_id", "count", "event_type", "stop_event", "previous",
                         "gate_order_sha256", "scientific_contract", "carry_forward_reattestation", "passed_rows", "execution_metrics",
                         "global_zero_metrics", "route_control"}
        if set(current) != expected_keys or current["schema_version"] != SCHEMA or current["goal_id"] != GOAL_ID or \
           current["scientific_contract"] != snapshot["scientific_contract"] or \
           current["carry_forward_reattestation"] != {"path": REATTESTATION_REL, "sha256": EXPECTED_REATTESTATION_SHA} or \
           current["gate_order_sha256"] != hashlib.sha256(json.dumps(FLAGS, sort_keys=True, separators=(",", ":")).encode()).hexdigest():
            raise RuntimeError("snapshot identity/schema drift")
        count = current["count"]
        if type(count) is not int or not 2 <= count <= 6 or path.name != snapshot_name(count, digest):
            raise RuntimeError("snapshot count/name/hash drift")
        if len(current["passed_rows"]) != count or [(x.get("index"), x.get("metric")) for x in current["passed_rows"]] != list(enumerate(FLAGS[:count])):
            raise RuntimeError("snapshot ordered rows drift")
        if current["event_type"] not in {"progress", "stop"} or (current["event_type"] == "progress") != (current["stop_event"] is None):
            raise RuntimeError("event schema")
        if current["event_type"] == "stop":
            event = current["stop_event"]
            if count >= 6 or not isinstance(event, dict) or set(event) != {"attempted_index", "metric", "evidence"} or \
               event["attempted_index"] != count or event["metric"] != FLAGS[count]:
                raise RuntimeError("stop event identity")
            verify_evidence(root, event["evidence"], passed=False, reattested=reattested)
        if set(current["execution_metrics"]) != set(EXECUTION_METRICS) or any(type(v) is not int or v not in {0, 1} for v in current["execution_metrics"].values()):
            raise RuntimeError("execution schema")
        for index, required in enumerate(GATE_EXECUTION):
            if any(current["execution_metrics"][name] != int(index < count) for name in required):
                raise RuntimeError("gate/execution mismatch")
        if current["global_zero_metrics"] != {name: 0 for name in GLOBAL_ZEROS}:
            raise RuntimeError("global zero drift")
        expected_route = {(0, 0)} if count == 6 else {(0, 1), (1, 0)}
        route = current["route_control"]
        if set(route) != {"route_stop_required", "continuation_allowed"} or \
           (route["route_stop_required"], route["continuation_allowed"]) not in expected_route:
            raise RuntimeError("route controls invalid")
        if current["event_type"] == "stop" and route != {"route_stop_required": 1, "continuation_allowed": 0}:
            raise RuntimeError("stop event route controls")
        for row in current["passed_rows"]: verify_evidence(root, row["evidence"], reattested=reattested)
        previous = current["previous"]
        if previous is None: break
        path = checked(root, previous["path"], previous["sha256"]); parent = json.loads(path.read_text())
        if parent["count"] != previous["count"]: raise RuntimeError("previous count drift")
        if current["event_type"] == "progress":
            if current["count"] != parent["count"] + 1 or current["passed_rows"][:-1] != parent["passed_rows"]:
                raise RuntimeError("non-append progress chain")
        elif current["count"] != parent["count"] or current["passed_rows"] != parent["passed_rows"]:
            raise RuntimeError("stop event changed passed progress")
        current = parent
    science = snapshot["scientific_contract"]
    checked(root, science["path"], science["sha256"])
    pointer_path = root / POINTER_REL
    if not pointer_path.is_file() or pointer_path.is_symlink(): raise RuntimeError("CURRENT shape")
    pointer = json.loads(pointer_path.read_text())
    expected_pointer = {"schema_version": "ordered_milestone_current_v1", "path": snapshot_rel,
                        "sha256": sha256_file(root / snapshot_rel), "count": snapshot["count"],
                        "event_type": snapshot["event_type"]}
    if pointer != expected_pointer: raise RuntimeError("snapshot is not authoritative CURRENT tip")
    return snapshot["count"], sha256_file(root / snapshot_rel)


def check(root, snapshot_rel):
    count, digest = verify_chain(root, snapshot_rel)
    print(canonical({"status": "PASS", "count": count, "snapshot_sha256": digest}), end="")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=None); ap.add_argument("--check")
    ap.add_argument("--advance-evidence"); ap.add_argument("--previous"); ap.add_argument("--execution-metrics")
    ap.add_argument("--route-stop", action="store_true"); args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]; out_dir = Path(__file__).resolve().parent
    if args.check:
        check(root, args.check); return
    if args.advance_evidence:
        if not args.previous or not args.execution_metrics: raise SystemExit("--advance-evidence requires --previous and --execution-metrics")
        result = advance(root, out_dir, args.previous, args.advance_evidence, args.execution_metrics, args.route_stop)
    else:
        if args.previous or args.execution_metrics or args.route_stop: raise SystemExit("advance-only arguments without --advance-evidence")
        result = genesis(root, out_dir)
    print(canonical({"snapshot_path": result[0], "snapshot_sha256": result[1], "metrics_path": result[2].as_posix()}), end="")


if __name__ == "__main__": main()
