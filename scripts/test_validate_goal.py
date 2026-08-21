#!/usr/bin/env python3
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_goal.py"
REPORT_REL = "reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812"
BUILDER = ROOT / REPORT_REL / "build_progress.py"
SPEC = importlib.util.spec_from_file_location("goal_progress_builder", BUILDER)
BUILDER_MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(BUILDER_MODULE)
PROPOSAL = ROOT / REPORT_REL / "PROPOSED_ACTIVE_GOAL.json"
SCIENCE = json.loads((ROOT / REPORT_REL / "SCIENTIFIC_GATE_CONTRACT.json").read_text())
FLAGS = [row["metric"] for row in SCIENCE["gates"]]
ALLOWED = [row["allowed_true_authorization"] for row in SCIENCE["gates"]]
EXECUTION = SCIENCE["execution_metrics"]
REQUIRED = [row["required_execution_metrics"] for row in SCIENCE["gates"]]
ZEROS = ["training_executed", "gpu_executed", "gpu_hours", "direct_s0_executed", "s1_executed",
  "claim_eligible", "training_authorized", "gpu_authorized", "direct_s0_authorized", "s1_authorized",
  "claim_authorized", "full_scale_authorized", "silent_identifier_substitution_count",
  "denominator_shrinkage_count", "homology_component_overlap_count", "test_calibration_count"]
HARD_AUTH = ["training_authorized", "gpu_authorized", "direct_s0_authorized", "s1_authorized",
             "full_scale_authorized", "claim_authorized"]


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ChainCase:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        (self.root / "scripts").mkdir(); (self.root / "scripts/validate_goal.py").write_text("marker\n")
        (self.root / "evidence").mkdir(); (self.root / "chain").mkdir(); (self.root / "contracts").mkdir()
        self.pointer = self.root / REPORT_REL / "CURRENT"; self.pointer.parent.mkdir(parents=True)
        self.protocol_path = self.root / "contracts/protocol.py"; self.protocol_path.write_text("# frozen protocol\n")
        self.science_path = self.root / "contracts/science.json"; self.science_path.write_text(canonical(SCIENCE))
        self.science_pin = {"path": "contracts/science.json", "sha256": digest(self.science_path),
                            "schema_version": "s_data_foundation_scientific_gates_v1"}
        screen = {"metric": "old", "value": .5, "direction": "higher"}
        sota = {"metric": "old", "value": .8, "direction": "higher"}
        self.goal = {"goal_id": SCIENCE["goal_id"], "status": "active", "scope": "milestone",
          "validation_mode": "ordered_evidence_milestone_v1", "primary_metric": "count", "direction": "higher",
          "milestone_gate": {"schema_version": "ordered_milestone_gate_v1",
            "snapshot_schema_version": "ordered_milestone_progress_snapshot_v2", "primary_metric": "count",
            "primary_type": "integer_count", "ordered_flags": FLAGS,
            "gate_order_sha256": hashlib.sha256(json.dumps(FLAGS, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "required_zero_metrics": ZEROS, "execution_metrics": EXECUTION,
            "route_stop_metric": "route_stop_required", "continuation_metric": "continuation_allowed",
            "genesis_snapshot": {}, "snapshot_metrics_fields": {"path": "progress_snapshot_path", "sha256": "progress_snapshot_sha256"},
            "progress_chain_directory": "chain",
            "current_pointer": {"path": REPORT_REL + "/CURRENT", "schema_version": "ordered_milestone_current_v1",
                                "atomic_replace_required": True},
            "scientific_contract": self.science_pin,
            "advancement_protocol": {"path": "contracts/protocol.py", "sha256": digest(self.protocol_path),
                                     "commands": ["--check", "--advance-evidence"]},
            "terminal_status": "success", "human_gate_required": True, "claim_full_scale_gpu_s1_authorized": False},
          "success_criteria": [{"metric": "count", "op": "==", "threshold": 6}] +
                              [{"metric": name, "op": "==", "threshold": 1} for name in FLAGS],
          "guardrails": [{"metric": name, "op": "==", "threshold": 0} for name in ZEROS],
          "parked_metadata": {"source_active_goal_sha256": "0" * 64, "anchors_evaluated": False,
            "screen_anchor": screen, "screen_anchor_sha256": hashlib.sha256(canonical(screen).strip().encode()).hexdigest(),
            "sota_benchmark": sota, "sota_benchmark_sha256": hashlib.sha256(canonical(sota).strip().encode()).hexdigest(),
            "reason": "test provenance"}}
        self.initial_evidence = [self.evidence(0), self.evidence(1)]
        request = self.pointer.parent / "CARRY_FORWARD_REVIEW_REQUEST.json"
        entries = []
        for index, evidence in enumerate(self.initial_evidence):
            entries.append({"gate_index": index, "gate_metric": FLAGS[index], "exp_id": evidence["exp_id"],
              "job_id": evidence["job_id"],
              "original_code_review_gate": {"path": evidence["code_review_gate_path"], "sha256": evidence["code_review_gate_sha256"]},
              "result_semantic_audit": {"path": evidence["result_path"], "sha256": evidence["result_sha256"]},
              "audited_manifest": {"path": evidence["audited_manifest_path"], "sha256": evidence["audited_manifest_sha256"]},
              "reviewed_files_current": {role: {"path": rel, "sha256": digest(self.root / rel)}
                                         for role, rel in evidence["required_reviewed_files"].items()}})
        request.write_text(canonical({"schema_version": "carry_forward_review_request_v1",
          "goal_id": SCIENCE["goal_id"], "reason": "synthetic post-result append",
          "required_verdict": "PASS_OR_PASS_WITH_WARNINGS", "entries": entries}))
        reattestation = self.pointer.parent / "CARRY_FORWARD_REATTESTATION.json"
        reattestation.write_text(canonical({"schema_version": "carry_forward_reattestation_v1",
          "goal_id": SCIENCE["goal_id"], "status": "REVIEWED", "verdict": "PASS", "blockers_open": 0,
          "reviewer_backend": "independent_codex_review_b_r2",
          "reviewer_independence": {"implementer_is_reviewer": False, "review_mode": "read_only",
            "review_scope": "carry_forward_current_files_and_evidence_closure"},
          "timestamp": "2026-08-12T14:18:00+02:00",
          "authorization": {"carry_forward_genesis_authorized": True, "goal_installation_authorized": False,
            "job_submission_authorized": False, "gpu_training_direct_s0_s1_claim_authorized": False},
          "review_request_path": request.relative_to(self.root).as_posix(), "review_request_sha256": digest(request),
          "reviewed_entries": entries}))
        self.goal["milestone_gate"]["carry_forward_reattestation"] = {
          "path": reattestation.relative_to(self.root).as_posix(), "sha256": digest(reattestation),
          "schema_version": "carry_forward_reattestation_v1"}
        self.snapshots = []
        self.add_snapshot()
        rel, sha, _ = self.snapshots[0]
        self.goal["milestone_gate"]["genesis_snapshot"] = {"path": rel, "sha256": sha, "count": 2}
        self.write_goal()

    def evidence(self, index, passed=True, *, result_patch=None, transition_patch=None):
        exp, job = "EXP%d%s" % (index, "P" if passed else "B"), str(100 + index + (0 if passed else 1000))
        reviewed = {}
        role_paths = {}
        for role in ("config", "runner", "evaluator_or_tests", "sbatch", "experiment_doc"):
            path = self.root / "evidence" / ("%s-%s.txt" % (exp, role)); path.write_text(role + "\n")
            rel = path.relative_to(self.root).as_posix(); reviewed[rel] = digest(path); role_paths[role] = rel
        authorization = {name: False for name in HARD_AUTH}
        authorization[ALLOWED[index]] = bool(passed)
        execution = {name: int(passed) for name in REQUIRED[index]}
        result_obj = {"exp_id": exp, "job_id": job,
          "status": "COMPONENT_PASS" if passed else "COMPONENT_TYPED_BLOCK",
          "verdict": "PASS_COMPONENT" if passed else "TYPED_BLOCK_COMPONENT",
          "semantic_success": True, "valid_negative": not passed, "claim_eligible": False,
          "scope": {"scientific_contract_verified": True}, "scientific_gate_contract_sha256": self.science_pin["sha256"],
          "gate_index": index, "gate_metric": FLAGS[index], "execution": execution, "authorization": authorization}
        if result_patch: result_patch(result_obj)
        result = self.root / "evidence" / ("result-%s.json" % exp); result.write_text(canonical(result_obj))
        review = self.root / "evidence" / ("review-%s.json" % exp)
        review.write_text(canonical({"exp_id": exp, "verdict": "PASS", "blockers_open": 0, "reviewed_files": reviewed}))
        manifest_paths = [result.relative_to(self.root).as_posix(), review.relative_to(self.root).as_posix(), *reviewed]
        manifest = self.root / "evidence" / ("manifest-%s.sha256" % exp)
        manifest.write_text("".join("%s  %s\n" % (digest(self.root / rel), rel) for rel in manifest_paths))
        eligibility = {"authorization." + ALLOWED[index]: bool(passed)}
        if transition_patch: transition_patch(eligibility)
        scope = {"scope.scientific_contract_verified": True, "scientific_gate_contract_sha256": self.science_pin["sha256"],
                 "gate_index": index, "gate_metric": FLAGS[index],
                 **{"execution." + name: int(passed) for name in REQUIRED[index]}}
        return {"metric": FLAGS[index], "exp_id": exp, "job_id": job,
          "result_path": result.relative_to(self.root).as_posix(), "result_sha256": digest(result),
          "audited_manifest_path": manifest.relative_to(self.root).as_posix(), "audited_manifest_sha256": digest(manifest),
          "code_review_gate_path": review.relative_to(self.root).as_posix(), "code_review_gate_sha256": digest(review),
          "required_reviewed_files": role_paths, "audited_manifest_expected_paths": manifest_paths,
          "expected_result": {"status": result_obj["status"], "verdict": result_obj["verdict"],
            "semantic_success": result_obj["semantic_success"], "valid_negative": result_obj["valid_negative"],
            "claim_eligible": result_obj["claim_eligible"], "scope_fields": scope},
          "legacy_validate_goal": None,
          "transition_metadata": {"eligibility_only": eligibility, "authorization_promoted": False}}

    def _write_pointer(self, rel, sha, snapshot):
        self.pointer.write_text(canonical({"schema_version": "ordered_milestone_current_v1", "path": rel,
                                           "sha256": sha, "count": snapshot["count"],
                                           "event_type": snapshot["event_type"]}))

    def add_snapshot(self, *, route_stop=False, evidence=None, execution_override=None,
                     row_override=None, previous_override=None, update_pointer=True):
        previous = self.snapshots[-1] if self.snapshots else None
        if previous is None:
            count, rows = 2, [{"index": i, "metric": FLAGS[i], "evidence": copy.deepcopy(self.initial_evidence[i])} for i in range(2)]
            prev = None; stop_event = None; event_type = "progress"
        else:
            attempted = previous[2]["count"]; count = attempted if route_stop else attempted + 1
            rows = copy.deepcopy(previous[2]["passed_rows"])
            ev = evidence or self.evidence(attempted, passed=not route_stop)
            if not route_stop: rows.append({"index": attempted, "metric": FLAGS[attempted], "evidence": ev})
            stop_event = {"attempted_index": attempted, "metric": FLAGS[attempted], "evidence": ev} if route_stop else None
            event_type = "stop" if route_stop else "progress"
            prev = {"path": previous[0], "sha256": previous[1], "count": previous[2]["count"]}
        if row_override: row_override(rows)
        if previous_override is not None: prev = previous_override
        execution = {name: 0 for name in EXECUTION}
        for index in range(count):
            for name in REQUIRED[index]: execution[name] = 1
        if execution_override: execution_override(execution)
        snapshot = {"schema_version": "ordered_milestone_progress_snapshot_v2", "goal_id": SCIENCE["goal_id"],
          "count": count, "event_type": event_type, "stop_event": stop_event, "previous": prev,
          "gate_order_sha256": self.goal["milestone_gate"]["gate_order_sha256"],
          "scientific_contract": {"path": self.science_pin["path"], "sha256": self.science_pin["sha256"]},
          "carry_forward_reattestation": {"path": self.goal["milestone_gate"]["carry_forward_reattestation"]["path"],
                                           "sha256": self.goal["milestone_gate"]["carry_forward_reattestation"]["sha256"]},
          "passed_rows": rows, "execution_metrics": execution, "global_zero_metrics": {name: 0 for name in ZEROS},
          "route_control": {"route_stop_required": int(route_stop), "continuation_allowed": int(count < 6 and not route_stop)}}
        payload = canonical(snapshot); sha = hashlib.sha256(payload.encode()).hexdigest()
        rel = "chain/progress-%02d-%s.json" % (count, sha); (self.root / rel).write_text(payload)
        self.snapshots.append((rel, sha, snapshot))
        if update_pointer: self._write_pointer(rel, sha, snapshot)
        return rel, sha

    def metrics(self, snapshot=None):
        rel, sha, row = snapshot or self.snapshots[-1]; count = row["count"]
        return {"count": count, **{name: int(i < count) for i, name in enumerate(FLAGS)},
          **row["global_zero_metrics"], **row["execution_metrics"], **row["route_control"],
          "progress_snapshot_path": rel, "progress_snapshot_sha256": sha}

    def rewrite_latest(self):
        old_rel, _, row = self.snapshots[-1]; (self.root / old_rel).unlink()
        payload = canonical(row); sha = hashlib.sha256(payload.encode()).hexdigest()
        rel = "chain/progress-%02d-%s.json" % (row["count"], sha); (self.root / rel).write_text(payload)
        self.snapshots[-1] = (rel, sha, row); self._write_pointer(rel, sha, row)

    def refresh_evidence_pins(self, evidence):
        evidence["result_sha256"] = digest(self.root / evidence["result_path"])
        evidence["code_review_gate_sha256"] = digest(self.root / evidence["code_review_gate_path"])
        manifest = self.root / evidence["audited_manifest_path"]
        manifest.write_text("".join("%s  %s\n" % (digest(self.root / rel), rel)
                                    for rel in evidence["audited_manifest_expected_paths"]))
        evidence["audited_manifest_sha256"] = digest(manifest)
        self.rewrite_latest()

    def builder_context(self):
        stack = ExitStack()
        for name, value in (("CHAIN_REL", "chain"), ("POINTER_REL", REPORT_REL + "/CURRENT"),
          ("SCIENCE_REL", "contracts/science.json"), ("PRIMARY", "count"),
          ("EXPECTED_REQUEST_SHA", digest(self.pointer.parent / "CARRY_FORWARD_REVIEW_REQUEST.json")),
          ("EXPECTED_REATTESTATION_SHA", digest(self.pointer.parent / "CARRY_FORWARD_REATTESTATION.json"))):
            stack.enter_context(mock.patch.object(BUILDER_MODULE, name, value))
        return stack

    def write_goal(self): self.goal_path = self.root / "goal.json"; self.goal_path.write_text(canonical(self.goal))
    def run(self, metrics=None, profile="screen"):
        path = self.root / "metrics.json"; path.write_text(canonical(metrics or self.metrics()))
        proc = subprocess.run([sys.executable, str(VALIDATOR), "--goal", str(self.goal_path), "--metrics", str(path),
                               "--profile", profile], cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.returncode, json.loads(proc.stdout)
    def close(self): self.tmp.cleanup()


class Tests(unittest.TestCase):
    def test_01_real_reviewed_genesis_is_authoritative_two_of_six(self):
        proposed = json.loads(PROPOSAL.read_text()); metrics = ROOT / proposed["current_frozen_progress"]["aggregate_metrics"]
        p = subprocess.run([sys.executable, str(VALIDATOR), "--goal", str(PROPOSAL), "--metrics", str(metrics),
                            "--profile", "smoke"], cwd=ROOT, text=True, stdout=subprocess.PIPE)
        out = json.loads(p.stdout)
        self.assertEqual((p.returncode, out["status"], out["milestone_gate"]["count"]), (1, "not_yet", 2))
        self.assertEqual(out["next_action"], "design_next_ordered_cpu_gate_for_fresh_review")

    def test_02_goal_unchanged_advances_three_through_six(self):
        c = ChainCase()
        try:
            original = c.goal_path.read_bytes()
            for count in range(3, 7):
                c.add_snapshot(); rc, out = c.run(); self.assertEqual(rc, 0 if count == 6 else 1)
                self.assertEqual(out["milestone_gate"]["count"], count)
            self.assertEqual(c.goal_path.read_bytes(), original); self.assertEqual(out["status"], "success")
            self.assertFalse(out["claim_achieved"]); self.assertTrue(out["human_gate_required"])
            self.assertEqual(out["next_action"], "stop_for_goal_revision")
        finally: c.close()

    def test_03_typed_stop_keeps_count_and_flag(self):
        c = ChainCase()
        try:
            old = c.metrics(); c.add_snapshot(route_stop=True); rc, out = c.run(); now = c.metrics()
            self.assertEqual((rc, out["status"], now["count"]), (1, "not_yet", 2))
            self.assertEqual([old[x] for x in FLAGS], [now[x] for x in FLAGS])
            self.assertTrue(out["route_stop_required"]); self.assertFalse(out["continuation_allowed"])
        finally: c.close()

    def test_04_old_snapshot_stale_after_stop_success_and_terminal(self):
        for terminal in ("stop", "success", "six"):
            c = ChainCase()
            try:
                old = c.metrics()
                if terminal == "stop": c.add_snapshot(route_stop=True)
                else:
                    c.add_snapshot()
                    if terminal == "six":
                        old = c.metrics()
                        for _ in range(3): c.add_snapshot()
                rc, out = c.run(old); self.assertEqual((rc, out["status"]), (3, "failed_run"))
            finally: c.close()

    def test_05_mutation_skip_and_reuse_fail(self):
        for mode in ("row", "skip", "reuse"):
            c = ChainCase()
            try:
                if mode == "row": c.add_snapshot(row_override=lambda rows: rows[0].update(metric=FLAGS[1]))
                elif mode == "skip": c.add_snapshot(previous_override={"path": c.snapshots[0][0], "sha256": c.snapshots[0][1], "count": 0})
                else: c.add_snapshot(row_override=lambda rows: rows[2].update(evidence=copy.deepcopy(rows[0]["evidence"])))
                rc, out = c.run(); self.assertEqual((rc, out["status"]), (3, "failed_run"))
            finally: c.close()

    def test_06_review_gate_and_manifest_closure_injections_fail(self):
        for mode in ("fake_review_hash", "reviewed_drift", "unrelated_manifest", "missing_anchor", "extra_manifest"):
            c = ChainCase()
            try:
                c.add_snapshot(); e = c.snapshots[-1][2]["passed_rows"][2]["evidence"]
                if mode == "fake_review_hash":
                    review = json.loads((c.root / e["code_review_gate_path"]).read_text()); review["reviewed_files"] = {"x": "0" * 64}
                    (c.root / e["code_review_gate_path"]).write_text(canonical(review))
                    c.refresh_evidence_pins(e)
                elif mode == "reviewed_drift": (c.root / next(iter(e["required_reviewed_files"].values()))).write_text("drift\n")
                elif mode == "unrelated_manifest": (c.root / e["audited_manifest_path"]).write_text("%s  %s\n" % (digest(c.protocol_path), "contracts/protocol.py"))
                elif mode == "missing_anchor": e["audited_manifest_expected_paths"].remove(e["result_path"]); c.rewrite_latest()
                else: e["audited_manifest_expected_paths"].append("contracts/protocol.py"); c.rewrite_latest()
                rc, out = c.run(); self.assertEqual((rc, out["status"]), (3, "failed_run"), mode)
            finally: c.close()

    def test_07_pass_polarity_and_authorization_injections_fail(self):
        cases = [
          lambda r: r.update(status="FAILED", semantic_success=False, valid_negative=True),
          lambda r: r["authorization"].update(gpu_authorized=True),
          lambda r: r["authorization"].update(unrelated_authorized=True),
        ]
        for mutate in cases:
            c = ChainCase()
            try:
                c.add_snapshot(evidence=c.evidence(2, result_patch=mutate)); rc, out = c.run()
                self.assertEqual((rc, out["status"]), (3, "failed_run"))
            finally: c.close()

    def test_08_transition_allowlist_and_execution_binding_fail(self):
        for mode in ("wrong_eligibility", "execution_zero", "future_execution_one"):
            c = ChainCase()
            try:
                if mode == "wrong_eligibility":
                    ev = c.evidence(2, transition_patch=lambda x: x.update({"authorization.gpu_authorized": True}))
                    c.add_snapshot(evidence=ev)
                elif mode == "execution_zero": c.add_snapshot(execution_override=lambda x: x.__setitem__(REQUIRED[2][0], 0))
                else:
                    c.snapshots[-1][2]["execution_metrics"][REQUIRED[2][0]] = 1; c.rewrite_latest()
                    c.goal["milestone_gate"]["genesis_snapshot"] = {"path": c.snapshots[-1][0], "sha256": c.snapshots[-1][1], "count": 2}; c.write_goal()
                rc, out = c.run(); self.assertEqual((rc, out["status"]), (3, "failed_run"))
            finally: c.close()

    def test_09_science_contract_weakening_fails(self):
        for mutate in (lambda x: x["frozen_denominator"].__setitem__("p_occurrence_count", 1),
                       lambda x: x["identity_and_label_contract"].__setitem__("copy_derived_identity_proxy_allowed", True),
                       lambda x: x["split_contract"].__setitem__("homology_input_label_blind", False)):
            c = ChainCase()
            try:
                contract = copy.deepcopy(SCIENCE); mutate(contract); c.science_path.write_text(canonical(contract))
                c.goal["milestone_gate"]["scientific_contract"]["sha256"] = digest(c.science_path); c.write_goal()
                rc, out = c.run(); self.assertEqual((rc, out["status"]), (3, "failed_run"))
            finally: c.close()

    def test_10_metric_and_current_pointer_injections_fail(self):
        for mode in ("gpu", "flag", "bool", "count", "hash", "pointer_symlink"):
            c = ChainCase()
            try:
                metrics = c.metrics()
                if mode == "gpu": metrics["gpu_executed"] = 1
                elif mode == "flag": metrics[FLAGS[3]] = 1
                elif mode == "bool": metrics[FLAGS[0]] = True
                elif mode == "count": metrics["count"] = 99
                elif mode == "hash": metrics["progress_snapshot_sha256"] = "0" * 64
                else:
                    real = c.pointer.with_name("REAL"); c.pointer.replace(real); c.pointer.symlink_to(real)
                rc, out = c.run(metrics); self.assertEqual((rc, out["status"]), (3, "failed_run"))
            finally: c.close()

    def test_11_builder_check_rejects_chain_ancestor_symlink(self):
        c = ChainCase()
        try:
            real = c.root / "real-chain"; (c.root / "chain").replace(real); (c.root / "chain").symlink_to(real)
            with c.builder_context():
                with self.assertRaises(RuntimeError): BUILDER_MODULE.check(c.root, c.snapshots[0][0])
        finally: c.close()

    def test_12_builder_advance_and_typed_stop_are_atomic_authority(self):
        for stop in (False, True):
            c = ChainCase()
            try:
                evidence_path = c.root / "advance.json"; evidence_path.write_text(canonical(c.evidence(2, passed=not stop)))
                execution = {name: 0 for name in EXECUTION}
                for index in range(2 + int(not stop)):
                    for name in REQUIRED[index]: execution[name] = 1
                ep = c.root / "execution.json"; ep.write_text(canonical(execution))
                with c.builder_context():
                    rel, sha, mp = BUILDER_MODULE.advance(c.root, c.root / "out", c.snapshots[0][0], evidence_path, ep, stop)
                data = json.loads(mp.read_text()); self.assertEqual(data["count"], 2 if stop else 3)
                self.assertEqual(data[FLAGS[2]], 0 if stop else 1); self.assertEqual(json.loads(c.pointer.read_text())["sha256"], sha)
                rc, out = c.run(data); self.assertEqual(rc, 1); self.assertEqual(out["route_stop_required"], stop)
            finally: c.close()

    def test_13_legacy_golden_parity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); gp = root / "g.json"; mp = root / "m.json"
            goal = {"status": "active", "primary_metric": "score", "direction": "higher",
              "success_criteria": [{"metric": "score", "op": ">=", "threshold": .8}], "guardrails": [],
              "screen_anchor": {"metric": "score", "value": .7, "direction": "higher"},
              "sota_benchmark": {"metric": "score", "value": .85, "direction": "higher"}}
            gp.write_text(canonical(goal))
            for metrics, profile, expected in [({}, "screen", (3, "failed_run")), ({"score": .5}, "full", (1, "not_yet")),
              ({"score": .8}, "screen", (1, "progress")), ({"score": .9}, "full", (0, "success")),
              ({"score": 1}, "full", (3, "failed_run"))]:
                mp.write_text(canonical(metrics)); p = subprocess.run([sys.executable, str(VALIDATOR), "--goal", str(gp),
                  "--metrics", str(mp), "--profile", profile], text=True, stdout=subprocess.PIPE)
                self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), expected)

    def test_14_active_goal_unchanged(self):
        self.assertEqual(digest(ROOT / "ACTIVE_GOAL.json"), "80b27cae844f75b60f1b97603456b0d1c2922dd07c8878b978e9760fdeffad94")

    def test_15_real_carry_forward_request_and_reattestation_are_closed(self):
        request_path = ROOT / REPORT_REL / "CARRY_FORWARD_REVIEW_REQUEST.json"
        request = json.loads(request_path.read_text())
        self.assertEqual(set(request), {"schema_version", "goal_id", "reason", "required_verdict", "entries"})
        self.assertEqual(len(request["entries"]), 2)
        for index, entry in enumerate(request["entries"]):
            self.assertEqual((entry["gate_index"], entry["gate_metric"]), (index, FLAGS[index]))
            for anchor in ("original_code_review_gate", "result_semantic_audit", "audited_manifest"):
                self.assertEqual(digest(ROOT / entry[anchor]["path"]), entry[anchor]["sha256"])
            for role, pin in entry["reviewed_files_current"].items():
                self.assertEqual(digest(ROOT / pin["path"]), pin["sha256"], role)
            doc = entry["reviewed_files_current"]["experiment_doc"]
            self.assertEqual(doc["drift_reason"], "post-result append")
            self.assertNotEqual(doc["sha256"], doc["original_review_sha256"])
        reattestation = json.loads((ROOT / REPORT_REL / "CARRY_FORWARD_REATTESTATION.json").read_text())
        self.assertEqual((reattestation["status"], reattestation["verdict"], reattestation["blockers_open"]),
                         ("REVIEWED", "PASS", 0))
        self.assertEqual(reattestation["reviewer_backend"], "independent_codex_review_b_r2")
        self.assertFalse(reattestation["reviewer_independence"]["implementer_is_reviewer"])
        self.assertEqual(reattestation["authorization"], {"carry_forward_genesis_authorized": True,
          "goal_installation_authorized": False, "job_submission_authorized": False,
          "gpu_training_direct_s0_s1_claim_authorized": False})
        self.assertEqual(reattestation["review_request_sha256"], digest(request_path))
        self.assertEqual(len(BUILDER_MODULE.verify_carry_forward_reattestation(ROOT)), 2)

    def test_16_not_reviewed_blocked_or_forged_reattestation_fails(self):
        for mode in ("not_reviewed", "blocked", "forged", "metadata_missing", "metadata_forged"):
            c = ChainCase()
            try:
                pin = c.goal["milestone_gate"]["carry_forward_reattestation"]
                path = c.root / pin["path"]; value = json.loads(path.read_text())
                if mode == "not_reviewed": value.update(status="NOT_REVIEWED", verdict=None, blockers_open=None)
                elif mode == "blocked": value.update(status="REVIEWED", verdict="BLOCKED", blockers_open=1)
                elif mode == "forged": value["reviewed_entries"][0]["reviewed_files_current"]["config"]["sha256"] = "0" * 64
                elif mode == "metadata_missing": value.pop("reviewer_backend")
                else: value["authorization"]["job_submission_authorized"] = True
                path.write_text(canonical(value)); pin["sha256"] = digest(path); c.write_goal()
                rc, out = c.run(); self.assertEqual((rc, out["status"]), (3, "failed_run"), mode)
            finally: c.close()

    def test_17_old_pre_reattestation_snapshot_is_stale(self):
        for old in ("6eecb73e1cd5c40492d18aa3594c214b23a66bafa020cd536d93079c31cbe5d4",
                    "2d6a7dcef0b0c56cffb407b0ceb9a3f89ce0b67a19a3a45b825a4b607a90e3bb"):
            old_metrics = ROOT / REPORT_REL / ("metrics-02-%s.json" % old)
            p = subprocess.run([sys.executable, str(VALIDATOR), "--goal", str(PROPOSAL), "--metrics", str(old_metrics),
                                "--profile", "smoke"], cwd=ROOT, text=True, stdout=subprocess.PIPE)
            out = json.loads(p.stdout); self.assertEqual((p.returncode, out["status"]), (3, "failed_run"))
            self.assertIn("authoritative CURRENT", " ".join(out["failures"]))

    def test_18_reattestation_byte_drift_prewrite_and_toctou_preserve_current(self):
        for mode in ("prewrite", "toctou"):
            c = ChainCase()
            try:
                evidence_path = c.root / "advance.json"; evidence_path.write_text(canonical(c.evidence(2)))
                execution = {name: 0 for name in EXECUTION}
                for index in range(3):
                    for name in REQUIRED[index]: execution[name] = 1
                execution_path = c.root / "execution.json"; execution_path.write_text(canonical(execution))
                reattestation = c.pointer.parent / "CARRY_FORWARD_REATTESTATION.json"
                original_artifact = reattestation.read_bytes(); original_current = c.pointer.read_bytes()
                before_chain = set((c.root / "chain").iterdir())
                def drift(): reattestation.write_text(json.dumps(json.loads(original_artifact), indent=4) + "\n")
                with c.builder_context(), mock.patch.object(BUILDER_MODULE, "BEFORE_POINTER_HOOK", drift if mode == "toctou" else None):
                    if mode == "prewrite": drift()
                    with self.assertRaises(RuntimeError):
                        BUILDER_MODULE.advance(c.root, c.root / "out", c.snapshots[0][0], evidence_path, execution_path, False)
                self.assertEqual(c.pointer.read_bytes(), original_current)
                if mode == "prewrite": self.assertEqual(set((c.root / "chain").iterdir()), before_chain)
                reattestation.write_bytes(original_artifact)
                rc, out = c.run(); self.assertEqual((rc, out["status"]), (1, "not_yet"))
            finally: c.close()

    def test_19_orphan_child_and_busy_or_double_writer_do_not_brick_current(self):
        c = ChainCase()
        try:
            parent = c.snapshots[0]; c.add_snapshot(update_pointer=False)
            c.snapshots = [parent]; c._write_pointer(parent[0], parent[1], parent[2])
            rc, out = c.run(c.metrics(parent)); self.assertEqual((rc, out["status"]), (1, "not_yet"))
            evidence_path = c.root / "advance.json"; evidence_path.write_text(canonical(c.evidence(2)))
            execution = {name: 0 for name in EXECUTION}
            for index in range(3):
                for name in REQUIRED[index]: execution[name] = 1
            execution_path = c.root / "execution.json"; execution_path.write_text(canonical(execution))
            lock = c.root / REPORT_REL / ".progress_writer.lock"; lock.mkdir()
            before = c.pointer.read_bytes()
            with c.builder_context():
                with self.assertRaisesRegex(RuntimeError, "lock busy"):
                    BUILDER_MODULE.advance(c.root, c.root / "out", parent[0], evidence_path, execution_path, False)
            self.assertEqual(c.pointer.read_bytes(), before); lock.rmdir()
        finally: c.close()


if __name__ == "__main__": unittest.main(verbosity=2)
