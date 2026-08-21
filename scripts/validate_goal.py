#!/usr/bin/env python3
"""Deterministic goal-validation gate for supervised-autonomy /pursue.

Non-skippable tripwire that fixes the autoloop failure mode. The agent CANNOT
self-judge — this script decides mechanically from metrics + ACTIVE_GOAL.json.

Enforces three disciplines as HARD, scriptable rules (not prose):
  1. Two-tier comparability (--profile): screen is judged ONLY against the
     same-budget `screen_anchor` and can NEVER claim vs published SOTA; only
     full/scale are judged against `sota_benchmark`. Kills the unfair
     "small-sample-vs-large-sample-SOTA" comparison.
  2. Anti-marginal-tuning: when gap_to_target >= tuning_gap_threshold (default
     0.05), `tuning_allowed=false` — /pursue & /pivot MUST pick an architecture
     move, not parameter tuning.
  3. Run/semantic-success: a failed or degenerate run can never pass.

Status (JSON on stdout, exit mirrors severity):
  failed_run (3): run/semantic failure → /pursue STOPS and notifies.
  not_yet (1)   : ran fine, success_criteria not met → continue.
  progress (1)  : progress gate met, claim gate not (or screen profile) → continue.
  success (0)   : legacy claim contract passes, OR an explicitly opted-in ordered
                  evidence milestone reaches exact completion. Milestone success
                  is non-claim and always stops at a human goal-revision gate.
Plus an optional `stale_benchmark` warning when --challenger-sota beats the
current sota_benchmark (a newer SOTA exists → run /revise-goal).

Usage:
  python3 scripts/validate_goal.py --goal ACTIVE_GOAL.json --metrics <m.json> \
      [--profile smoke|screen|full|scale] [--run-status <file>] [--challenger-sota <value>]
"""
import argparse, hashlib, json, math, os, re, sys
from pathlib import Path, PurePosixPath

OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
       ">": lambda a, b: a > b, "<": lambda a, b: a < b, "==": lambda a, b: a == b}

MILESTONE_SCHEMA = "ordered_milestone_gate_v1"


class MilestoneContractError(ValueError):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def project_root_for_goal(goal_path):
    start = Path(goal_path).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "scripts" / "validate_goal.py").is_file():
            return candidate
    raise MilestoneContractError("cannot locate project root from goal path")


def safe_evidence_file(root, rel, expected_hash):
    if not isinstance(rel, str) or not rel or "\\" in rel:
        raise MilestoneContractError("evidence path must be a nonempty POSIX relative path")
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != rel:
        raise MilestoneContractError(f"unsafe evidence path: {rel!r}")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise MilestoneContractError(f"invalid evidence hash for {rel}")
    path = root / rel
    cursor = root
    for part in pure.parts:
        cursor = cursor / part
        if os.path.lexists(cursor) and cursor.is_symlink():
            raise MilestoneContractError(f"symlink evidence path: {rel}")
    if not path.is_file() or path.is_symlink():
        raise MilestoneContractError(f"evidence file missing/not regular: {rel}")
    try:
        if path.resolve(strict=True).relative_to(root.resolve(strict=True)) is None:
            raise MilestoneContractError(f"evidence escaped project root: {rel}")
    except ValueError as exc:
        raise MilestoneContractError(f"evidence escaped project root: {rel}") from exc
    observed = sha256_file(path)
    if observed != expected_hash:
        raise MilestoneContractError(f"evidence hash drift: {rel}")
    return path


def _exact_int(value, *, minimum=None, maximum=None, label="value"):
    if type(value) is not int:
        raise MilestoneContractError(f"{label} must be an exact integer")
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise MilestoneContractError(f"{label} outside [{minimum},{maximum}]")
    return value


def _exact_numeric_zero(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != 0:
        raise MilestoneContractError(f"{label} must be exact numeric zero")


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def dotted_get(value, dotted):
    current = value
    for key in dotted.split("."):
        if not isinstance(current, dict) or key not in current:
            raise MilestoneContractError(f"evidence audit field absent: {dotted}")
        current = current[key]
    return current


def verify_audited_manifest(root, path):
    seen = set()
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        raise MilestoneContractError("audited manifest unreadable") from exc
    if not lines:
        raise MilestoneContractError("audited manifest empty")
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\n]+)", line)
        if not match:
            raise MilestoneContractError("audited manifest line grammar")
        digest, rel = match.groups()
        if rel in seen:
            raise MilestoneContractError("audited manifest duplicate path")
        seen.add(rel)
        safe_evidence_file(root, rel, digest)
    return seen


def validate_parked_metadata(goal):
    parked = goal.get("parked_metadata")
    keys = {"source_active_goal_sha256", "anchors_evaluated", "screen_anchor", "screen_anchor_sha256",
            "sota_benchmark", "sota_benchmark_sha256", "reason"}
    if not isinstance(parked, dict) or set(parked) != keys or parked.get("anchors_evaluated") is not False:
        raise MilestoneContractError("parked_metadata exact schema")
    for name in ("source_active_goal_sha256", "screen_anchor_sha256", "sota_benchmark_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(parked.get(name))):
            raise MilestoneContractError("parked metadata hash grammar")
    if canonical_sha256(parked["screen_anchor"]) != parked["screen_anchor_sha256"] or \
       canonical_sha256(parked["sota_benchmark"]) != parked["sota_benchmark_sha256"]:
        raise MilestoneContractError("parked anchor hash drift")
    if "screen_anchor" in goal or "sota_benchmark" in goal:
        raise MilestoneContractError("parked anchors must not remain active")


def validate_milestone(goal, metrics, goal_path):
    mode = goal.get("validation_mode")
    if mode is None:
        return None
    if mode != "ordered_evidence_milestone_v1":
        raise MilestoneContractError(f"unknown validation_mode: {mode!r}")
    gate = goal.get("milestone_gate")
    gate_keys = {"schema_version", "snapshot_schema_version", "primary_metric", "primary_type", "ordered_flags",
                 "gate_order_sha256", "required_zero_metrics", "execution_metrics", "route_stop_metric",
                 "continuation_metric", "genesis_snapshot", "snapshot_metrics_fields", "progress_chain_directory",
                 "current_pointer", "scientific_contract", "advancement_protocol", "terminal_status", "human_gate_required",
                 "claim_full_scale_gpu_s1_authorized", "carry_forward_reattestation"}
    if not isinstance(gate, dict) or set(gate) != gate_keys:
        raise MilestoneContractError("milestone_gate exact schema mismatch")
    if gate["schema_version"] != MILESTONE_SCHEMA or goal.get("scope") != "milestone" or \
       gate["snapshot_schema_version"] != "ordered_milestone_progress_snapshot_v2" or gate["primary_type"] != "integer_count":
        raise MilestoneContractError("milestone schema/scope/type mismatch")
    if gate["terminal_status"] != "success" or gate["human_gate_required"] is not True or \
       gate["claim_full_scale_gpu_s1_authorized"] is not False:
        raise MilestoneContractError("unsafe milestone terminal authorization")
    validate_parked_metadata(goal)
    primary, flags = gate["primary_metric"], gate["ordered_flags"]
    zeros, execution_names = gate["required_zero_metrics"], gate["execution_metrics"]
    if primary != goal.get("primary_metric") or not isinstance(primary, str) or not primary:
        raise MilestoneContractError("milestone primary_metric mismatch")
    if not isinstance(flags, list) or len(flags) != 6 or any(not isinstance(x, str) or not x for x in flags) or len(set(flags)) != 6:
        raise MilestoneContractError("ordered_flags must contain exact six unique metrics")
    if gate["gate_order_sha256"] != canonical_sha256(flags):
        raise MilestoneContractError("gate order hash drift")
    for label, names in (("required_zero_metrics", zeros), ("execution_metrics", execution_names)):
        if not isinstance(names, list) or not names or any(not isinstance(x, str) or not x for x in names) or len(set(names)) != len(names):
            raise MilestoneContractError(f"{label} must be a unique nonempty string list")
    metric_names = {primary, *flags, *zeros, *execution_names, gate["route_stop_metric"], gate["continuation_metric"]}
    if len(metric_names) != 1 + len(flags) + len(zeros) + len(execution_names) + 2:
        raise MilestoneContractError("milestone metric namespaces overlap")

    required_success = {(primary, "==", 6)} | {(name, "==", 1) for name in flags}
    actual_success = {(r.get("metric"), r.get("op", ">="), r.get("threshold"))
                      for r in goal.get("success_criteria", []) if isinstance(r, dict)}
    if not required_success <= actual_success:
        raise MilestoneContractError("milestone success_criteria do not require exact 6/6")
    required_guardrails = {(name, "==", 0) for name in zeros}
    actual_guardrails = {(r.get("metric"), r.get("op", ">="), r.get("threshold"))
                         for r in goal.get("guardrails", []) if isinstance(r, dict)}
    if not required_guardrails <= actual_guardrails:
        raise MilestoneContractError("milestone guardrails do not require exact zero")

    root = project_root_for_goal(goal_path)
    protocol = gate["advancement_protocol"]
    if not isinstance(protocol, dict) or set(protocol) != {"path", "sha256", "commands"} or \
       protocol["commands"] != ["--check", "--advance-evidence"]:
        raise MilestoneContractError("advancement protocol pin schema")
    safe_evidence_file(root, protocol["path"], protocol["sha256"])
    science = gate["scientific_contract"]
    if not isinstance(science, dict) or set(science) != {"path", "sha256", "schema_version"} or \
       science["schema_version"] != "s_data_foundation_scientific_gates_v1":
        raise MilestoneContractError("scientific contract pin schema")
    science_path = safe_evidence_file(root, science["path"], science["sha256"])
    contract = json.loads(science_path.read_text())
    contract_keys = {"schema_version", "goal_id", "frozen_denominator", "identity_and_label_contract",
                     "split_contract", "execution_metrics", "gates"}
    if set(contract) != contract_keys or contract["schema_version"] != science["schema_version"] or \
       contract["goal_id"] != goal.get("goal_id") or contract["execution_metrics"] != execution_names:
        raise MilestoneContractError("scientific contract identity/schema")
    denominator = contract["frozen_denominator"]
    if denominator != {"name": "canonical_old_occurrence_ledger", "p_occurrence_count": 6432583,
                       "conservation_required": "exact", "shrinkage_allowed": False}:
        raise MilestoneContractError("scientific denominator weakened")
    identity = contract["identity_and_label_contract"]
    required_identity = {"each_p_occurrence_requires_unique_versioned_accession": True,
      "each_p_occurrence_requires_official_consensus_sha256": True,
      "direct_superfamily_label_source": "raw_repeatmasker_class_only", "label_contract_excluded_identifier_count": 10,
      "label_contract_excluded_handling": "U_ignore_and_separate_audit",
      "x13_line_handling": "ambiguity_stratum_audit_only_not_primary", "copy_derived_identity_proxy_allowed": False,
      "prefix_case_or_fuzzy_identity_guess_allowed": False}
    required_split = {"representative_windows_frozen_before_evaluation": True,
      "old_occurrence_categories_exactly_once": True, "homology_input_label_blind": True,
      "homology_scope": "all_species", "component_construction_precedes_split": True,
      "cross_split_component_overlap_required": 0, "component_direct_label_conflict_handling": "typed_block"}
    if identity != required_identity or contract["split_contract"] != required_split:
        raise MilestoneContractError("scientific identity/split contract weakened")
    gate_rows = contract["gates"]
    if not isinstance(gate_rows, list) or len(gate_rows) != 6 or any(set(x) != {"index", "metric", "scientific_semantics", "required_execution_metrics", "allowed_true_authorization"} for x in gate_rows):
        raise MilestoneContractError("scientific gate rows schema")
    if [(x["index"], x["metric"]) for x in gate_rows] != list(enumerate(flags)):
        raise MilestoneContractError("scientific gate order mismatch")
    required_semantics = [
      "Six frozen accessions resolve exact-once over twelve installed FamDB leaves with no name, prefix, case, alias, or copy fallback.",
      "The same six exact leaf records produce paired name/accession-version header views with byte-identical sequence order and raw class.",
      "Paired RepeatMasker CPU smoke executes both libraries; per-hit geometry and raw class are exact and each candidate hit retains one unique versioned accession.",
      "Representative real windows are frozen before evaluation and every frozen old-ledger occurrence is classified into exactly one registered category.",
      "The complete 6,432,583-P-occurrence ledger is conserved exactly; every P occurrence has one unique versioned accession and official consensus SHA256; direct label is raw RepeatMasker class only; ten excluded identifiers remain U/ignore and X13_LINE remains audit-only.",
      "All-species homology construction is label-blind, components are frozen before split, component overlap across splits is zero, and within-component direct-label conflicts are typed blocks.",
    ]
    if [x["scientific_semantics"] for x in gate_rows] != required_semantics:
        raise MilestoneContractError("scientific gate semantics weakened")
    required_by_gate = [x["required_execution_metrics"] for x in gate_rows]
    allowed_authorizations = [x["allowed_true_authorization"] for x in gate_rows]
    if any(not isinstance(x, list) or not x or not set(x) <= set(execution_names) for x in required_by_gate):
        raise MilestoneContractError("scientific execution mapping invalid")
    if any(not isinstance(x, str) or not x.endswith("_human_gate_eligible") for x in allowed_authorizations) or \
       len(set(allowed_authorizations)) != 6:
        raise MilestoneContractError("scientific authorization allowlist invalid")

    reattestation_pin = gate["carry_forward_reattestation"]
    if not isinstance(reattestation_pin, dict) or set(reattestation_pin) != {"path", "sha256", "schema_version"} or \
       reattestation_pin["schema_version"] != "carry_forward_reattestation_v1":
        raise MilestoneContractError("carry-forward reattestation pin schema")
    reattestation_path = safe_evidence_file(root, reattestation_pin["path"], reattestation_pin["sha256"])
    try: reattestation = json.loads(reattestation_path.read_text())
    except (OSError, json.JSONDecodeError) as exc: raise MilestoneContractError("carry-forward reattestation unreadable") from exc
    reattestation_keys = {"schema_version", "goal_id", "status", "verdict", "blockers_open", "reviewer_backend",
                          "reviewer_independence", "timestamp", "authorization", "review_request_path",
                          "review_request_sha256", "reviewed_entries"}
    if set(reattestation) != reattestation_keys or reattestation["schema_version"] != reattestation_pin["schema_version"] or \
       reattestation["goal_id"] != goal.get("goal_id"):
        raise MilestoneContractError("carry-forward reattestation identity/schema")
    if reattestation["reviewer_backend"] != "independent_codex_review_b_r2" or reattestation["reviewer_independence"] != {
      "implementer_is_reviewer": False, "review_mode": "read_only",
      "review_scope": "carry_forward_current_files_and_evidence_closure"} or \
       not re.fullmatch(r"2026-08-12T\d\d:\d\d:\d\d\+02:00", reattestation["timestamp"]) or \
       reattestation["authorization"] != {"carry_forward_genesis_authorized": True,
         "goal_installation_authorized": False, "job_submission_authorized": False,
         "gpu_training_direct_s0_s1_claim_authorized": False}:
        raise MilestoneContractError("carry-forward reviewer metadata/authorization")
    request_path = safe_evidence_file(root, reattestation["review_request_path"], reattestation["review_request_sha256"])
    try: review_request = json.loads(request_path.read_text())
    except (OSError, json.JSONDecodeError) as exc: raise MilestoneContractError("carry-forward review request unreadable") from exc
    if set(review_request) != {"schema_version", "goal_id", "reason", "required_verdict", "entries"} or \
       review_request["schema_version"] != "carry_forward_review_request_v1" or \
       review_request["goal_id"] != goal.get("goal_id") or review_request["required_verdict"] != "PASS_OR_PASS_WITH_WARNINGS" or \
       not isinstance(review_request["entries"], list) or len(review_request["entries"]) != 2:
        raise MilestoneContractError("carry-forward review request schema")
    if reattestation["status"] != "REVIEWED" or reattestation["verdict"] not in {"PASS", "PASS_WITH_WARNINGS"} or \
       reattestation["blockers_open"] != 0:
        raise MilestoneContractError("carry-forward reattestation is NOT_REVIEWED/BLOCKED")
    if not isinstance(reattestation["reviewed_entries"], list) or len(reattestation["reviewed_entries"]) != 2:
        raise MilestoneContractError("carry-forward reattestation entry count")
    reattested = {}
    reattestation_entry_keys = {"gate_index", "gate_metric", "exp_id", "job_id", "original_code_review_gate",
                                "result_semantic_audit", "audited_manifest", "reviewed_files_current"}
    for index, entry in enumerate(reattestation["reviewed_entries"]):
        requested = review_request["entries"][index]
        if not isinstance(entry, dict) or set(entry) != reattestation_entry_keys or entry["gate_index"] != index or \
           entry["gate_metric"] != flags[index]:
            raise MilestoneContractError("carry-forward reattestation entry schema/order")
        for key in ("gate_index", "gate_metric", "exp_id", "job_id", "original_code_review_gate",
                    "result_semantic_audit", "audited_manifest"):
            if entry[key] != requested.get(key):
                raise MilestoneContractError("reattestation differs from frozen review request")
        reviewed = entry["reviewed_files_current"]
        if not isinstance(reviewed, dict) or set(reviewed) != {"config", "runner", "evaluator_or_tests", "sbatch", "experiment_doc"}:
            raise MilestoneContractError("carry-forward reviewed roles")
        for role, pin in reviewed.items():
            if not isinstance(pin, dict) or set(pin) != {"path", "sha256"}: raise MilestoneContractError("carry-forward reviewed pin schema")
            safe_evidence_file(root, pin["path"], pin["sha256"])
            requested_pin = requested.get("reviewed_files_current", {}).get(role)
            if not isinstance(requested_pin, dict) or pin != {"path": requested_pin.get("path"), "sha256": requested_pin.get("sha256")}:
                raise MilestoneContractError("reattested reviewed file differs from request")
        if entry["exp_id"] in reattested: raise MilestoneContractError("duplicate carry-forward exp")
        reattested[entry["exp_id"]] = entry

    genesis = gate["genesis_snapshot"]
    if not isinstance(genesis, dict) or set(genesis) != {"path", "sha256", "count"} or genesis["count"] != 2:
        raise MilestoneContractError("genesis pin schema")
    current_fields = gate["snapshot_metrics_fields"]
    if current_fields != {"path": "progress_snapshot_path", "sha256": "progress_snapshot_sha256"}:
        raise MilestoneContractError("snapshot metrics field contract")
    current_rel, current_sha = metrics.get(current_fields["path"]), metrics.get(current_fields["sha256"])
    if not isinstance(current_rel, str) or not current_rel.startswith(gate["progress_chain_directory"] + "/"):
        raise MilestoneContractError("current snapshot namespace")
    current_path = safe_evidence_file(root, current_rel, current_sha)
    pointer_contract = gate["current_pointer"]
    if pointer_contract != {"path": "reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/CURRENT",
                           "schema_version": "ordered_milestone_current_v1", "atomic_replace_required": True}:
        raise MilestoneContractError("CURRENT pointer contract")
    pointer_path = safe_evidence_file(root, pointer_contract["path"], sha256_file(root / pointer_contract["path"]))
    try: pointer = json.loads(pointer_path.read_text())
    except (OSError, json.JSONDecodeError) as exc: raise MilestoneContractError("CURRENT pointer unreadable") from exc
    if pointer != {"schema_version": pointer_contract["schema_version"], "path": current_rel, "sha256": current_sha,
                   "count": metrics.get(primary), "event_type": pointer.get("event_type")} or \
       pointer.get("event_type") not in {"progress", "stop"}:
        raise MilestoneContractError("metrics do not point to authoritative CURRENT")

    snapshot_keys = {"schema_version", "goal_id", "count", "event_type", "stop_event", "previous", "gate_order_sha256",
                     "scientific_contract", "carry_forward_reattestation", "passed_rows", "execution_metrics",
                     "global_zero_metrics", "route_control"}
    row_keys = {"index", "metric", "evidence"}
    evidence_keys = {"metric", "exp_id", "job_id", "result_path", "result_sha256", "audited_manifest_path",
      "audited_manifest_sha256", "code_review_gate_path", "code_review_gate_sha256", "expected_result",
      "required_reviewed_files", "audited_manifest_expected_paths", "legacy_validate_goal", "transition_metadata"}
    chain, seen_hashes = [], set(); path, observed_sha = current_path, current_sha
    while True:
        try: snapshot = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc: raise MilestoneContractError("snapshot unreadable") from exc
        if observed_sha in seen_hashes: raise MilestoneContractError("snapshot cycle")
        seen_hashes.add(observed_sha); chain.append((path, observed_sha, snapshot))
        if set(snapshot) != snapshot_keys or snapshot["schema_version"] != gate["snapshot_schema_version"] or \
           snapshot["goal_id"] != goal.get("goal_id") or snapshot["gate_order_sha256"] != gate["gate_order_sha256"] or \
           snapshot["scientific_contract"] != {"path": science["path"], "sha256": science["sha256"]} or \
           snapshot["carry_forward_reattestation"] != {"path": reattestation_pin["path"], "sha256": reattestation_pin["sha256"]}:
            raise MilestoneContractError("snapshot identity/schema drift")
        count = _exact_int(snapshot["count"], minimum=2, maximum=6, label="snapshot count")
        if path.name != "progress-%02d-%s.json" % (count, observed_sha):
            raise MilestoneContractError("snapshot filename/hash identity")
        event_type, stop_event = snapshot["event_type"], snapshot["stop_event"]
        if event_type not in {"progress", "stop"} or (event_type == "progress") != (stop_event is None):
            raise MilestoneContractError("snapshot event schema")
        if event_type == "stop":
            if count >= 6 or not isinstance(stop_event, dict) or set(stop_event) != {"attempted_index", "metric", "evidence"} or \
               stop_event["attempted_index"] != count or stop_event["metric"] != flags[count]:
                raise MilestoneContractError("stop event identity")
        rows = snapshot["passed_rows"]
        if not isinstance(rows, list) or len(rows) != count or any(not isinstance(x, dict) or set(x) != row_keys for x in rows) or \
           [(x["index"], x["metric"]) for x in rows] != list(enumerate(flags[:count])):
            raise MilestoneContractError("snapshot ordered rows drift")
        if set(snapshot["execution_metrics"]) != set(execution_names) or any(type(v) is not int or v not in {0, 1} for v in snapshot["execution_metrics"].values()):
            raise MilestoneContractError("snapshot execution schema")
        for index, required in enumerate(required_by_gate):
            expected = int(index < count)
            if any(snapshot["execution_metrics"][name] != expected for name in required):
                raise MilestoneContractError("gate pass/execution mismatch")
        if set(snapshot["global_zero_metrics"]) != set(zeros): raise MilestoneContractError("snapshot zero schema")
        for name in zeros: _exact_numeric_zero(snapshot["global_zero_metrics"][name], name)
        route = snapshot["route_control"]
        if set(route) != {gate["route_stop_metric"], gate["continuation_metric"]}: raise MilestoneContractError("route schema")
        route_stop = _exact_int(route[gate["route_stop_metric"]], minimum=0, maximum=1, label="route_stop")
        continuation = _exact_int(route[gate["continuation_metric"]], minimum=0, maximum=1, label="continuation")
        if (route_stop, continuation) not in ({(0, 0)} if count == 6 else {(0, 1), (1, 0)}):
            raise MilestoneContractError("route controls inconsistent")
        previous = snapshot["previous"]
        if previous is None: break
        expected_parent_count = count - 1 if event_type == "progress" else count
        if not isinstance(previous, dict) or set(previous) != {"path", "sha256", "count"} or previous["count"] != expected_parent_count:
            raise MilestoneContractError("previous link schema/count")
        parent_path = safe_evidence_file(root, previous["path"], previous["sha256"])
        parent = json.loads(parent_path.read_text())
        expected_parent_rows = rows[:-1] if event_type == "progress" else rows
        if parent.get("passed_rows") != expected_parent_rows:
            raise MilestoneContractError("snapshot rewrites old row")
        path, observed_sha = parent_path, previous["sha256"]
    if path.relative_to(root).as_posix() != genesis["path"] or observed_sha != genesis["sha256"] or snapshot["count"] != genesis["count"]:
        raise MilestoneContractError("chain does not terminate at pinned genesis")
    current = chain[0][2]; count = current["count"]
    jobs, evidence_paths = set(), set()
    hard_false_authorizations = {"training_authorized", "gpu_authorized", "direct_s0_authorized",
                                 "s1_authorized", "full_scale_authorized", "claim_authorized"}

    def validate_evidence(row, *, passed):
        evidence_row = row["evidence"]
        if not isinstance(evidence_row, dict) or set(evidence_row) != evidence_keys or evidence_row["metric"] != row["metric"]:
            raise MilestoneContractError("passed evidence exact schema")
        job_key = (evidence_row["exp_id"], evidence_row["job_id"])
        paths_key = (evidence_row["result_path"], evidence_row["audited_manifest_path"], evidence_row["code_review_gate_path"])
        if job_key in jobs or any(p in evidence_paths for p in paths_key):
            raise MilestoneContractError("duplicate milestone evidence/job")
        jobs.add(job_key); evidence_paths.update(paths_key)
        result_path = safe_evidence_file(root, evidence_row["result_path"], evidence_row["result_sha256"])
        manifest_path = safe_evidence_file(root, evidence_row["audited_manifest_path"], evidence_row["audited_manifest_sha256"])
        manifest_paths = verify_audited_manifest(root, manifest_path)
        expected_manifest_paths = evidence_row["audited_manifest_expected_paths"]
        if not isinstance(expected_manifest_paths, list) or not expected_manifest_paths or \
           len(expected_manifest_paths) != len(set(expected_manifest_paths)) or \
           manifest_paths != set(expected_manifest_paths) or evidence_row["result_path"] not in manifest_paths or \
           evidence_row["code_review_gate_path"] not in manifest_paths:
            raise MilestoneContractError("audited manifest exact closure/anchors")
        review_path = safe_evidence_file(root, evidence_row["code_review_gate_path"], evidence_row["code_review_gate_sha256"])
        review = json.loads(review_path.read_text())
        if review.get("exp_id") != evidence_row["exp_id"] or review.get("verdict") not in {"PASS", "PASS_WITH_WARNINGS"} or \
           review.get("blockers_open") != 0 or not isinstance(review.get("reviewed_files"), dict) or not review["reviewed_files"]:
            raise MilestoneContractError("independent code review evidence invalid")
        roles = evidence_row["required_reviewed_files"]
        if not isinstance(roles, dict) or set(roles) != {"config", "runner", "evaluator_or_tests", "sbatch", "experiment_doc"} or \
           set(roles.values()) != set(review["reviewed_files"]):
            raise MilestoneContractError("required reviewed files exact set")
        replacement = reattested.get(evidence_row["exp_id"])
        if replacement is None:
            for rel, digest in review["reviewed_files"].items(): safe_evidence_file(root, rel, digest)
        else:
            if row["index"] >= 2 or replacement["gate_index"] != row["index"] or \
               str(replacement["job_id"]) != str(evidence_row["job_id"]) or \
               replacement["original_code_review_gate"] != {"path": evidence_row["code_review_gate_path"], "sha256": evidence_row["code_review_gate_sha256"]} or \
               replacement["result_semantic_audit"] != {"path": evidence_row["result_path"], "sha256": evidence_row["result_sha256"]} or \
               replacement["audited_manifest"] != {"path": evidence_row["audited_manifest_path"], "sha256": evidence_row["audited_manifest_sha256"]}:
                raise MilestoneContractError("carry-forward evidence anchor mismatch")
            current_reviewed = replacement["reviewed_files_current"]
            if set(review["reviewed_files"]) != {pin["path"] for pin in current_reviewed.values()} or \
               any(roles[role] != pin["path"] for role, pin in current_reviewed.items()):
                raise MilestoneContractError("reattestation reviewed-file set mismatch")
            for pin in current_reviewed.values(): safe_evidence_file(root, pin["path"], pin["sha256"])
        try:
            result = json.loads(result_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise MilestoneContractError("result semantic audit unreadable") from exc
        expected_result = evidence_row["expected_result"]
        if not isinstance(expected_result, dict) or set(expected_result) != {"status", "verdict", "semantic_success",
                                                                                "valid_negative", "claim_eligible", "scope_fields"}:
            raise MilestoneContractError("expected_result schema")
        if passed:
            if not str(expected_result["status"]).endswith("PASS") or not str(expected_result["verdict"]).startswith("PASS") or \
               expected_result["semantic_success"] is not True or expected_result["valid_negative"] is not False or \
               expected_result["claim_eligible"] is not False:
                raise MilestoneContractError("passed evidence polarity")
        elif "TYPED_BLOCK" not in str(expected_result["status"]) or expected_result["semantic_success"] is not True or \
             expected_result["valid_negative"] is not True or expected_result["claim_eligible"] is not False:
            raise MilestoneContractError("typed-stop evidence polarity")
        for name in ("status", "verdict", "semantic_success", "valid_negative", "claim_eligible"):
            if result.get(name) != expected_result[name]:
                raise MilestoneContractError(f"result audit mismatch: {name}")
        if result.get("exp_id") != evidence_row["exp_id"] or str(result.get("job_id")) != str(evidence_row["job_id"]):
            raise MilestoneContractError("result audit exp/job mismatch")
        scope_fields = expected_result["scope_fields"]
        if not isinstance(scope_fields, dict) or not scope_fields or any(dotted_get(result, k) != v for k, v in scope_fields.items()):
            raise MilestoneContractError("result audit scope mismatch")
        if passed and row["index"] >= genesis["count"]:
            mandatory_scope = {"scientific_gate_contract_sha256": science["sha256"],
              "gate_index": row["index"], "gate_metric": row["metric"],
              **{"execution." + name: 1 for name in required_by_gate[row["index"]]}}
            if not mandatory_scope.items() <= scope_fields.items():
                raise MilestoneContractError("extension evidence does not bind scientific execution contract")
        legacy = evidence_row["legacy_validate_goal"]
        if legacy is not None:
            if not isinstance(legacy, dict) or set(legacy) != {"path", "sha256", "classification"} or legacy["classification"] != "legacy_goal_contract_mismatch":
                raise MilestoneContractError("legacy validator evidence schema")
            safe_evidence_file(root, legacy["path"], legacy["sha256"])
        transition = evidence_row["transition_metadata"]
        if not isinstance(transition, dict) or set(transition) != {"eligibility_only", "authorization_promoted"} or \
           not isinstance(transition["eligibility_only"], dict) or not transition["eligibility_only"] or \
           any(dotted_get(result, k) != v for k, v in transition["eligibility_only"].items()) or \
           transition["authorization_promoted"] is not False:
            raise MilestoneContractError("transition metadata unsafe")
        allowed_true = {allowed_authorizations[row["index"]]} if passed else set()
        transition_true = {key.split(".", 1)[1] for key, value in transition["eligibility_only"].items()
                           if key.startswith("authorization.") and value is True}
        if transition_true != allowed_true or any(not key.startswith("authorization.") or type(value) is not bool
                                                  for key, value in transition["eligibility_only"].items()):
            raise MilestoneContractError("transition eligibility allowlist")
        authorization = result.get("authorization")
        if not isinstance(authorization, dict) or any(not isinstance(value, bool) for value in authorization.values()) or \
           {key for key, value in authorization.items() if value is True} != allowed_true:
            raise MilestoneContractError("eligibility was promoted to downstream authorization")
        if any(authorization.get(name) is True for name in hard_false_authorizations):
            raise MilestoneContractError("forbidden authorization is true")

    for row in current["passed_rows"]:
        validate_evidence(row, passed=True)
    if current["event_type"] == "stop":
        validate_evidence({"index": current["stop_event"]["attempted_index"],
                           "metric": current["stop_event"]["metric"],
                           "evidence": current["stop_event"]["evidence"]}, passed=False)
    expected_metrics = {primary: count, **{name: int(i < count) for i, name in enumerate(flags)},
      **current["global_zero_metrics"], **current["execution_metrics"], **current["route_control"],
      current_fields["path"]: current_rel, current_fields["sha256"]: current_sha}
    _exact_int(metrics.get(primary), minimum=0, maximum=6, label=primary)
    for name in flags + execution_names + [gate["route_stop_metric"], gate["continuation_metric"]]:
        _exact_int(metrics.get(name), minimum=0, maximum=1, label=name)
    for name in zeros: _exact_numeric_zero(metrics.get(name), name)
    if metrics != expected_metrics: raise MilestoneContractError("aggregate metrics do not exactly derive from current snapshot")
    route_stop = current["route_control"][gate["route_stop_metric"]]
    continuation = current["route_control"][gate["continuation_metric"]]
    return {"ok": True, "primary_metric": primary, "count": count, "total": 6,
            "ordered_flags": [{"metric": n, "value": int(i < count)} for i, n in enumerate(flags)],
            "required_zero_metrics": current["global_zero_metrics"], "execution_metrics": current["execution_metrics"],
            "progress_snapshot": {"path": current_rel, "sha256": current_sha}, "human_gate_required": True,
            "claim_achieved": False, "automatic_continuation_allowed": False,
            "route_stop_required": bool(route_stop), "continuation_allowed": bool(continuation),
            "next_action": "stop_for_goal_revision" if count == 6 or route_stop else "design_next_ordered_cpu_gate_for_fresh_review",
            "claim_authorized": False, "gpu_authorized": False, "s1_authorized": False}


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"file not found: {path}"
    except json.JSONDecodeError as e:
        return None, f"unparseable JSON in {path}: {e}"


def check(metrics, rules):
    results, all_ok = [], True
    for r in rules:
        m, op, thr = r["metric"], r.get("op", ">="), r["threshold"]
        val = metrics.get(m)
        if val is None:
            ok, note = False, "metric absent"
        elif not isinstance(val, (int, float)) or not math.isfinite(val):
            ok, note = False, f"non-finite value {val!r}"
        else:
            ok, note = OPS[op](val, thr), f"{val} {op} {thr}"
        results.append({"metric": m, "op": op, "threshold": thr, "value": val, "ok": ok, "note": note})
        all_ok = all_ok and ok
    return all_ok, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", required=True)
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--profile", default="screen", choices=["smoke", "screen", "full", "scale"])
    ap.add_argument("--run-status", default=None)
    ap.add_argument("--challenger-sota", type=float, default=None,
                    help="a newly-found verified SOTA value; if it beats sota_benchmark -> stale warning")
    ap.add_argument("--prior-screen", type=float, default=None,
                    help="this candidate's own Track-A screen value; full/scale below it -> regression warning (G8)")
    args = ap.parse_args()

    out = {"status": None, "profile": args.profile, "run_ok": False, "semantic_ok": False,
           "comparison_anchor": None, "primary_progress_gate": {}, "guardrails_gate": {},
           "claim_gate": {}, "tuning_allowed": None, "gap_to_target": None,
           "recommended_axis": None, "observed_metrics": {}, "warnings": [], "failures": [],
           "milestone_gate": None}

    goal, gerr = load_json(args.goal)
    if gerr:
        out["status"] = "failed_run"; out["failures"].append(f"goal contract: {gerr}")
        print(json.dumps(out, indent=2)); sys.exit(3)

    # --- Gate 0a: run status ---
    if args.run_status:
        try:
            st = open(args.run_status).read().strip().upper()
        except OSError:
            st = "MISSING"
        if any(k in st for k in ("FAIL", "CANCEL", "TIMEOUT", "OOM", "ERROR", "NODE_FAIL", "MISSING", "STALE", "UNKNOWN")):
            out["status"] = "failed_run"; out["failures"].append(f"run status not OK: {st}")
            print(json.dumps(out, indent=2)); sys.exit(3)
    out["run_ok"] = True

    # --- Gate 0b: semantic success ---
    metrics, merr = load_json(args.metrics)
    if merr:
        out["status"] = "failed_run"; out["failures"].append(f"semantic-success: {merr}")
        print(json.dumps(out, indent=2)); sys.exit(3)
    try:
        milestone = validate_milestone(goal, metrics, args.goal)
    except Exception as exc:
        out["status"] = "failed_run"; out["failures"].append(f"milestone-integrity: {exc}")
        print(json.dumps(out, indent=2)); sys.exit(3)
    out["milestone_gate"] = milestone
    pm = goal.get("primary_metric")
    pv = metrics.get(pm) if pm else None
    direction = goal.get("direction", "higher")
    if pm and (pv is None or not isinstance(pv, (int, float)) or not math.isfinite(pv)):
        out["status"] = "failed_run"; out["failures"].append(f"semantic-success: primary_metric '{pm}' missing/non-finite ({pv!r})")
        print(json.dumps(out, indent=2)); sys.exit(3)
    # Degenerate/leakage heuristic is only meaningful for higher-is-better, [0,1]-scaled
    # metrics (0.0 = all-wrong, 1.0 = suspiciously perfect / label leakage). For
    # lower-is-better metrics (e.g. loss), 0.0 is a legitimate optimum, so we never
    # auto-fail it here (m1 fix). Range-aware refinement left to project goal.
    if pm and milestone is None and direction == "higher" and pv in (0.0, 1.0):
        out["status"] = "failed_run"; out["failures"].append(f"semantic-success: '{pm}'=={pv} (degenerate/leakage; higher-is-better metric at bound)")
        print(json.dumps(out, indent=2)); sys.exit(3)
    # G9: range-aware "suspiciously good" advisory (does NOT hard-fail — surfaced for
    # pivot/tri-review). Covers leakage that lands just below 1.0 (e.g. AUPRC=0.985) and
    # out-of-range metrics (MCC/Pearson can be negative; the 0/1 degenerate check misses these).
    # Opt-in via goal contract: "sane_upper": <value> and/or "sane_range": [lo, hi].
    if pm and isinstance(pv, (int, float)):
        su = goal.get("sane_upper"); sr = goal.get("sane_range")
        if isinstance(su, (int, float)) and pv > su:
            out["suspicious_high"] = True
            out["warnings"].append(f"suspicious_high: '{pm}'={pv} exceeds sane_upper {su} — possible leakage/eval bug; verify before claim (advisory).")
        if isinstance(sr, (list, tuple)) and len(sr) == 2 and all(isinstance(x, (int, float)) for x in sr):
            if pv < sr[0] or pv > sr[1]:
                out["suspicious_high"] = True
                out["warnings"].append(f"out_of_sane_range: '{pm}'={pv} outside {list(sr)} — likely metric/eval bug; verify (advisory).")

    out["semantic_ok"] = True
    out["observed_metrics"] = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}

    # --- Gate 1: success_criteria + guardrails ---
    crit_ok, crit_res = check(metrics, goal.get("success_criteria", []))
    out["primary_progress_gate"] = {"ok": crit_ok, "rules": crit_res}
    g_ok, g_res = check(metrics, goal.get("guardrails", []))
    out["guardrails_gate"] = {"ok": g_ok, "rules": g_res}

    # Ordered milestone goals are engineering/human-gate contracts, not model/SOTA
    # comparisons. Historical anchors may remain under parked_metadata for audit, but
    # they never participate in milestone evaluation.
    if milestone is not None:
        out["comparison_anchor"] = "none"
        out["anchors_evaluated"] = False
        out["claim_gate"] = {"ok": False, "withheld": True,
                             "reason": "ordered evidence milestone is non-claim"}
        out["tuning_allowed"] = None
        out["recommended_axis"] = "complete the next ordered CPU evidence gate"
        out.update({key: milestone[key] for key in ("claim_achieved", "human_gate_required",
                   "automatic_continuation_allowed", "route_stop_required", "continuation_allowed", "next_action")})

    # --- Two-tier comparison anchor + claim gate (A3/A1 fix) ---
    sota = (goal.get("sota_benchmark") or {}) if milestone is None else {}
    anchor = (goal.get("screen_anchor") or {}) if milestone is None else {}
    is_screen = args.profile in ("smoke", "screen")
    # screen/smoke -> ONLY screen_anchor (same-budget, fair). It must NEVER fall back to
    # published SOTA. full/scale -> ONLY sota_benchmark. A missing anchor yields 'none'
    # (claim is withheld, not silently judged against the wrong reference).
    if is_screen:
        cmp = anchor if anchor else None
    else:
        cmp = sota if sota else None
    out["comparison_anchor"] = ("none" if milestone is not None else
                                ("screen_anchor" if (is_screen and anchor) else
                                 ("sota_benchmark" if (not is_screen and sota) else "none")))
    if milestone is None and is_screen and not anchor:
        out["warnings"].append("screen/smoke profile but no screen_anchor in goal — comparison_anchor='none'; NOT falling back to published SOTA. Build a screen_anchor first (benchmark-roadmap M1).")
    claim_ok = None
    if cmp:
        m = cmp.get("metric", pm); bench = cmp.get("value"); d = cmp.get("direction", direction)
        val = metrics.get(m)
        if isinstance(val, (int, float)) and isinstance(bench, (int, float)):
            claim_ok = (val > bench) if d == "higher" else (val < bench)
            out["claim_gate"] = {"ok": claim_ok, "metric": m, "observed": val, "anchor_value": bench,
                                 "anchor": out["comparison_anchor"], "note": f"{val} {'>' if d=='higher' else '<'} {bench} (strict)"}

    # --- Anti-marginal-tuning gap ALWAYS references published sota_benchmark when present ---
    # (A3 fix) so a large gap to the REAL SOTA forbids tuning even during screen — exactly
    # the phase where marginal tuning is most tempting. Falls back to the claim anchor only
    # when no sota_benchmark exists at all.
    anti = sota if isinstance(sota.get("value"), (int, float)) else (cmp or {})
    av = anti.get("value"); am = anti.get("metric", pm)
    aval = metrics.get(am)
    if isinstance(av, (int, float)) and isinstance(aval, (int, float)):
        out["gap_to_target"] = round(abs(av - aval), 6)
        out["gap_reference"] = "sota_benchmark" if anti is sota else out["comparison_anchor"]

    # --- Anti-marginal-tuning hard rule (B) ---
    thr = goal.get("tuning_gap_threshold", 0.05)
    if out["gap_to_target"] is not None:
        if out["gap_to_target"] >= thr:
            out["tuning_allowed"] = False
            out["recommended_axis"] = "architecture (gap large — parameter tuning FORBIDDEN; pick head/backbone/objective/decoder/data_view axis)"
        else:
            out["tuning_allowed"] = True
            out["recommended_axis"] = "near target — systematic tuning/scaling now reasonable"

    # --- Staleness (A) ---
    if args.challenger_sota is not None and sota.get("value") is not None:
        sd = sota.get("direction", direction); sv = sota["value"]
        beats = (args.challenger_sota > sv) if sd == "higher" else (args.challenger_sota < sv)
        if beats:
            out["warnings"].append(f"stale_benchmark: a verified SOTA ({args.challenger_sota}) beats sota_benchmark ({sv}) — run /revise-goal before claiming.")

    # --- G8: Track-B scale regression vs the candidate's OWN screen value ---
    # validate normally only compares to fixed anchors, so a scale run that drops BELOW
    # its own Track-A screen (architecture not scaling) is invisible. Surface it (advisory,
    # does not change 4-state): /pivot must then consider backbone/abandon, not tuning.
    if milestone is None and args.prior_screen is not None and not is_screen and isinstance(pv, (int, float)):
        regressed = (pv < args.prior_screen) if direction == "higher" else (pv > args.prior_screen)
        if regressed:
            out["regression"] = True
            out["warnings"].append(
                f"regression: {args.profile} '{pm}'={pv} is worse than this candidate's own screen "
                f"({args.prior_screen}) — architecture may NOT scale. /pivot should weigh "
                f"backbone-change/abandon over tuning, not just continue scaling.")

    # --- Pre-decision guards: a draft/placeholder or criteria-less contract can NEVER pass (m5/m2) ---
    draft = str(goal.get("status", "")).lower() == "draft"
    if draft:
        out["warnings"].append("ACTIVE_GOAL.status=='draft': placeholder contract — success is DISABLED until you fill real thresholds (sota_benchmark/screen_anchor/success_criteria).")
    no_criteria = not goal.get("success_criteria")
    if no_criteria:
        out["warnings"].append("no success_criteria defined — progress gate is vacuous; success withheld until at least one criterion exists.")

    # --- Decide ---
    if not crit_ok:
        out["status"] = "not_yet"; out["failures"] = [r["note"] for r in crit_res if not r["ok"]]
        print(json.dumps(out, indent=2)); sys.exit(1)
    if not g_ok:
        out["status"] = "not_yet"; out["failures"] = ["guardrail: " + r["note"] for r in g_res if not r["ok"]]
        print(json.dumps(out, indent=2)); sys.exit(1)
    # criteria + guardrails met:
    if milestone is not None:
        if milestone["route_stop_required"]:
            out["status"] = "not_yet"
            out["failures"] = ["scientific route stop requires human review"]
            print(json.dumps(out, indent=2)); sys.exit(1)
        if milestone["count"] != milestone["total"]:
            out["status"] = "not_yet"
            out["failures"] = [f"ordered milestone incomplete: {milestone['count']}/{milestone['total']}"]
            print(json.dumps(out, indent=2)); sys.exit(1)
        out["status"] = "success"
        out["warnings"].append("Milestone complete: stop for explicit human goal revision; no claim or automatic continuation is authorized.")
        print(json.dumps(out, indent=2)); sys.exit(0)
    if is_screen:
        # HARD: screen/smoke can never claim vs published SOTA
        out["status"] = "progress"
        out["warnings"].append("screen/smoke profile: cannot claim SOTA; passed screen_anchor progress only. Promote to full/scale to test the published-SOTA claim.")
        print(json.dumps(out, indent=2)); sys.exit(1)
    # full/scale: success requires a FILLED contract AND a usable SOTA anchor that is strictly beaten.
    if draft or no_criteria:
        out["status"] = "progress"
        print(json.dumps(out, indent=2)); sys.exit(1)
    if out["comparison_anchor"] == "none" or claim_ok is None:
        # A1 fix: never treat "no comparison possible" as success. Missing/invalid
        # sota_benchmark means we cannot verify strict SOTA exceedance — withhold success.
        out["status"] = "progress"
        out["warnings"].append("full/scale but no usable sota_benchmark anchor — cannot verify strict SOTA exceedance; success WITHHELD (fill sota_benchmark or run /revise-goal).")
        print(json.dumps(out, indent=2)); sys.exit(1)
    if claim_ok is True:
        out["status"] = "success"
        print(json.dumps(out, indent=2)); sys.exit(0)
    out["status"] = "progress"
    print(json.dumps(out, indent=2)); sys.exit(1)


if __name__ == "__main__":
    main()
