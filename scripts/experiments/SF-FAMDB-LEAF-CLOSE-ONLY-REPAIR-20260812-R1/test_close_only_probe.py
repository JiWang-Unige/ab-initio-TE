#!/usr/bin/env python3
import importlib.util
import contextlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("leaf_probe", HERE / "close_only_probe.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ROOT = HERE.parents[2]
CFG = m.load_config(ROOT / "configs" / (m.EXP_ID + ".yaml"))


class FakeFamily:
    def __init__(self, row, sequence=None):
        self.accession = row["accession"]; self.version = int(row["versioned_accession"].split(".")[-1])
        self.name = row["canonical_name"]; head = row["raw_class"].split("/", 1)
        self.repeat_type = head[0]; self.repeat_subtype = head[1] if len(head) == 2 else None
        self.consensus = sequence if sequence is not None else "A" * row["consensus_length"]
    def accession_with_optional_version(self): return "%s.%d" % (self.accession, self.version)


class FakeHandleId:
    def __init__(self): self.valid = 1


class FakeHandle:
    def __init__(self, fail=False, raised=None): self.id = FakeHandleId(); self.fail = fail; self.raised = raised; self.calls = 0
    def close(self):
        self.calls += 1
        if self.raised is not None: raise self.raised
        if self.fail: raise OSError("injected close failure")
        self.id.valid = 0


class FakeLeaf:
    def __init__(self, fail=False, handle=None, raised=None): self.file = handle or FakeHandle(fail=fail, raised=raised)


def exact_observations():
    out = []
    for target in CFG["selected_records"]:
        for part in CFG["source_contract"]["expected_partition_order"]:
            record = None
            if part == target["partition"]:
                record = dict(target, queried_accession=target["accession"])
            out.append({"queried_accession": target["accession"], "partition": part, "record": record})
    return out


def slurm_env():
    return {"SLURM_JOB_ID": "17", "SLURM_CPUS_PER_TASK": "1", "SLURM_MEM_PER_NODE": "4G",
            "SLURM_JOB_PARTITION": "private-teodoro-gpu"}


def scontrol_line(**overrides):
    c = CFG["slurm_contract"]
    fields = {"JobId": "17", "Partition": c["partition"], "TimeLimit": c["time_limit"],
              "NumCPUs": c["num_cpus"], "ReqTRES": "cpu=1,mem=4G,node=1,billing=2",
              "AllocTRES": "cpu=1,mem=4G,node=1,billing=2", "Command": c["command"],
              "SubmitLine": c["submit_line"]}
    fields.update(overrides)
    return " ".join("%s=%s" % x for x in fields.items()) + "\n"


@contextlib.contextmanager
def termination_controller():
    controller = m.DeferredCleanupSignals().enter()
    try: yield controller
    finally:
        if controller.active: controller.restore_for_tests()


class Tests(unittest.TestCase):
    def test_01_config_contract(self):
        m.validate_config(CFG)

    def test_02_small_assets_only_static(self):
        m.validate_small_assets(ROOT, CFG)

    def test_03_exact_once_pass(self):
        metrics, _, resolved = m.evaluate_observations(CFG, exact_observations())
        self.assertTrue(metrics["exact_once_across_partitions"]); self.assertEqual(len(resolved), 6)

    def test_04_missing_typed_block(self):
        obs = exact_observations(); obs[7]["record"] = None
        with self.assertRaises(m.TypedBlock) as cm: m.evaluate_observations(CFG, obs)
        self.assertTrue(cm.exception.metrics["route_stop"])

    def test_05_duplicate_across_partitions_typed_block(self):
        obs = exact_observations(); target = CFG["selected_records"][0]
        row = dict(target, partition=3); obs[3]["record"] = row
        with self.assertRaises(m.TypedBlock) as cm: m.evaluate_observations(CFG, obs)
        self.assertEqual(cm.exception.audit["failures"][0]["reason"], "duplicate")

    def test_06_version_drift_typed_block(self):
        obs = exact_observations(); obs[7]["record"]["versioned_accession"] = "DF000000002.5"
        with self.assertRaises(m.TypedBlock) as cm: m.evaluate_observations(CFG, obs)
        self.assertIn("versioned_accession", cm.exception.audit["failures"][0]["fields"])

    def test_07_name_class_length_sha_partition_drift_block(self):
        for key, value in (("canonical_name", "other"), ("raw_class", "LINE/L1"),
                           ("consensus_length", 1), ("consensus_sha256", "0" * 64), ("partition", 3)):
            obs = exact_observations(); obs[7]["record"][key] = value
            with self.subTest(key=key), self.assertRaises(m.TypedBlock): m.evaluate_observations(CFG, obs)

    def test_08_matrix_missing_duplicate_schema_integrity(self):
        obs = exact_observations()
        with self.assertRaises(m.IntegrityError): m.evaluate_observations(CFG, obs[:-1])
        obs = exact_observations(); obs[-1] = dict(obs[0])
        with self.assertRaises(m.IntegrityError): m.evaluate_observations(CFG, obs)

    def test_09_family_schema_and_api_drift(self):
        target = CFG["selected_records"][0]; fam = FakeFamily(target)
        row = m.family_row(fam, target["partition"], target["accession"])
        self.assertEqual(row["versioned_accession"], target["versioned_accession"])
        del fam.consensus
        with self.assertRaises(m.IntegrityError): m.family_row(fam, 7, target["accession"])
        fam = FakeFamily(target); fam.version = "4"
        with self.assertRaises(m.IntegrityError): m.family_row(fam, 7, target["accession"])
        fam = FakeFamily(target); fam.version = None; fam.accession_with_optional_version = lambda: fam.accession
        row = m.family_row(fam, 7, target["accession"])
        self.assertEqual(row["versioned_accession"], target["accession"])

    def test_09b_leaf_api_and_partition_mapping_drift(self):
        cfg = json.loads(json.dumps(CFG))
        for row in cfg["selected_records"]:
            row["consensus_sha256"] = m.sha256_bytes(("A" * row["consensus_length"]).encode())
        parts = cfg["source_contract"]["expected_partition_order"]
        files = {part: mock.Mock() for part in parts}
        for leaf in files.values(): leaf.get_family_by_accession.return_value = None
        files[7].get_family_by_accession.side_effect = lambda acc: FakeFamily(next(x for x in cfg["selected_records"] if x["accession"] == acc)) if acc.startswith("DF") else None
        files[3].get_family_by_accession.side_effect = lambda acc: FakeFamily(next(x for x in cfg["selected_records"] if x["accession"] == acc)) if acc.startswith("DR") else None
        metrics, _, _ = m.probe_leaf_mapping(cfg, files); self.assertFalse(metrics["route_stop"])
        self.assertEqual(metrics["probe_call_count"], 72)
        self.assertEqual(sum(x.get_family_by_accession.call_count for x in files.values()), 72)
        broken = dict(files); broken[0] = object()
        with self.assertRaises(m.IntegrityError): m.probe_leaf_mapping(cfg, broken)
        broken = dict(files); broken.pop(16)
        with self.assertRaises(m.IntegrityError): m.probe_leaf_mapping(cfg, broken)

    def test_10_no_fallback_surface(self):
        source = (HERE / "close_only_probe.py").read_text()
        self.assertNotIn("get_family_by_name", source)
        self.assertNotIn("startswith(target", source)
        self.assertNotIn("final" + "ize", source)
        self.assertEqual(CFG["probe_contract"]["lookup_key"], "unversioned_accession_exact_case_sensitive")

    def test_11_resource_guard_missing_timelimit_ok(self):
        m.validate_resource_env(slurm_env())
        for key, value in (("SLURM_JOB_ID", "x"), ("SLURM_CPUS_PER_TASK", "2"),
                           ("SLURM_MEM_PER_NODE", "8G"), ("SLURM_JOB_PARTITION", "debug-cpu"),
                           ("SLURM_GPUS", "1")):
            env = dict(slurm_env(), **{key: value})
            with self.assertRaises(m.IntegrityError): m.validate_resource_env(env)

    def test_12_scontrol_exact_and_anomalies(self):
        ok = lambda *_: (0, scontrol_line(), "")
        audit = m.query_slurm(ROOT, CFG, slurm_env(), executor=ok)
        self.assertEqual(audit["fields"]["TimeLimit"], "00:10:00")
        for result in ((1, "", "unknown"), (0, scontrol_line(), "warn"), (0, "JobId=17\n", "")):
            with self.subTest(result=result), self.assertRaises(m.IntegrityError):
                m.query_slurm(ROOT, CFG, slurm_env(), executor=lambda *_args, r=result: r)
        for key, value in (("JobId", "18"), ("TimeLimit", "00:09:59"), ("TimeLimit", "00:10:01"),
                           ("NumCPUs", "2"), ("SubmitLine", "sbatch --time=20 x"),
                           ("ReqTRES", "cpu=1,mem=4G,gres/gpu=1"),
                           ("ReqTRES", "cpu=1,cpu=2,mem=4G,node=1,billing=2"),
                           ("AllocTRES", "cpu=1,mem=4G,node=1,billing=2,unknown=1"),
                           ("AllocTRES", "cpu=1,mem=4G,node=1,billing")):
            with self.subTest(key=key), self.assertRaises(m.IntegrityError):
                m.query_slurm(ROOT, CFG, slurm_env(), executor=lambda *_args, k=key, v=value: (0, scontrol_line(**{k: v}), ""))

    def test_13_bundle_exact_set_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); m.publish(p, "x", "IMPLEMENTED_NOT_RUN", False, {"metrics.json": "{}\n"})
            self.assertEqual(m.verify_bundle(p)["status"], "IMPLEMENTED_NOT_RUN")
            bundle = p / (p / "CURRENT").read_text().strip(); (bundle / "extra").write_text("x")
            with self.assertRaises(m.IntegrityError): m.verify_bundle(p)

    def test_14_static_never_opens_h5_or_calls_api(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(m, "probe_installed_open", side_effect=AssertionError), \
             mock.patch.object(m, "validate_source", side_effect=AssertionError):
            cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = td
            m.static_preview(ROOT, cfg, "static")
            self.assertEqual(m.verify_bundle(td)["status"], "IMPLEMENTED_NOT_RUN")

    def test_15_static_rejects_owner_and_formal_state(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = td
            (p / cfg["owner_lock_name"]).mkdir()
            with self.assertRaises(m.IntegrityError): m.static_preview(ROOT, cfg, "static")
            (p / cfg["owner_lock_name"]).rmdir(); m.publish(p, "f", "LEAF_CLOSE_ONLY_PASS", True, {})
            with self.assertRaises(m.IntegrityError): m.static_preview(ROOT, cfg, "late")

    def test_16_writer_mutex(self):
        with tempfile.TemporaryDirectory() as td:
            with m.writer_mutex(td):
                with self.assertRaises(m.IntegrityError): m.publish(td, "x", "IMPLEMENTED_NOT_RUN", False, {})

    def test_17_formal_slurm_precedes_h5(self):
        with termination_controller() as controller, mock.patch.dict(os.environ, slurm_env(), clear=True), \
             mock.patch.object(m, "query_slurm", side_effect=m.IntegrityError("bad Slurm")), \
             mock.patch.object(m, "probe_installed_open", side_effect=AssertionError):
            with self.assertRaisesRegex(m.IntegrityError, "bad Slurm"): m.formal(ROOT, CFG, "x", controller)

    def test_18_sbatch_contract(self):
        text = (ROOT / "sbatch" / (m.EXP_ID + ".sbatch")).read_text()
        self.assertIn("#SBATCH --time=00:10:00", text); self.assertIn("#SBATCH --mem=4G", text)
        self.assertIn("#SBATCH --cpus-per-task=1", text); self.assertNotIn("#SBATCH --gres", text)
        self.assertLess(text.index("set -eo pipefail"), text.index("source /opt/ebsofts"))
        self.assertLess(text.index("conda activate te_benchmark"), text.index("set -u"))
        self.assertLess(text.index("pre_submit_gate.py"), text.index('python "${TEST_PATH}"'))
        self.assertIn('"${PROJECT_ROOT}/scripts/pre_submit_gate.py" --exp-id "${EXP_ID}" "${PROJECT_ROOT}"', text)
        self.assertIn("timeout --signal=TERM --kill-after=30s 480s", text)

    def test_19_typed_block_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); m.publish(p, "x", "LEAF_CLOSE_ONLY_TYPED_BLOCK", True, {})
            status = m.verify_bundle(p)
            self.assertFalse(status["authorization"]["leaf_adapter_preflight_human_gate_eligible"])
            self.assertFalse(status["authorization"]["gpu_authorized"])

    def test_20_integrity_failure_publish_requires_same_owner(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = "preview"
            preview = root / "preview"; preview.mkdir(); m.publish(preview, "old", "FORMAL_RUNNING", False, {})
            old = m.current_bytes(preview); env = slurm_env()
            initial = {"slurm": {"fields": {}, "command": []}, "owner_sha256": "o", "gate_sha256": "g",
                       "package_sha256": {"x": "h"}, "source": {"s": "h"}}
            with mock.patch.object(m, "revalidate_authority", return_value=None):
                self.assertTrue(m.publish_failure_if_owned(root, cfg, "new", m.IntegrityError("x"), env, initial))
            self.assertEqual(m.verify_bundle(preview)["status"], "LEAF_CLOSE_ONLY_FAILED")
            m.atomic_write(preview / "CURRENT", old)
            with mock.patch.object(m, "revalidate_authority", side_effect=[None, m.IntegrityError("prepointer drift")]):
                self.assertFalse(m.publish_failure_if_owned(root, cfg, "other", m.IntegrityError("x"), env, initial))
            self.assertEqual(m.current_bytes(preview), old)

    def test_21_formal_scientific_probe_exactly_once_72_calls(self):
        initial = {"slurm": {"fields": {}, "command": []}, "owner_sha256": "o", "gate_sha256": "g",
                   "package_sha256": {"x": "h"}, "source": {"s": "h"}}
        metrics = {"route_stop": False, "probe_call_count": 72, "target_count": 6, "partition_count": 12,
                   "resolved_count": 6, "blocked_count": 0, "exact_once_across_partitions": True, "fallback_count": 0}
        files = {part: FakeLeaf() for part in CFG["source_contract"]["expected_partition_order"]}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = "preview"
            observations = exact_observations(); resolved_rows = [x["record"] for x in observations if x["record"]]
            probe = mock.Mock(return_value=(metrics, {"observations": observations, "failures": []}, resolved_rows))
            with termination_controller() as controller, mock.patch.dict(os.environ, slurm_env(), clear=True), \
                 mock.patch.object(m, "prepare_authority", return_value=initial), \
                 mock.patch.object(m, "probe_installed_open", side_effect=lambda _r, _c, lifecycle: (lifecycle.attach_db(
                     types.SimpleNamespace(files=files)) or probe())), \
                 mock.patch.object(m, "validate_owner", return_value="o"), \
                 mock.patch.object(m, "validate_source", return_value=initial["source"]), \
                 mock.patch.object(m, "package_hashes", return_value=initial["package_sha256"]), \
                 mock.patch.object(m, "query_slurm", return_value=initial["slurm"]), \
                 mock.patch.object(m, "revalidate_authority", return_value=None):
                m.formal(root, cfg, "synthetic", controller)
            probe.assert_called_once_with()
            self.assertEqual(sum(x.file.calls for x in files.values()), 12)
            self.assertEqual(m.verify_bundle(root / "preview")["status"], "LEAF_CLOSE_ONLY_PASS")

    def test_22_failure_authority_revalidation_all_axes(self):
        slurm = {"fields": {"JobId": "17"}, "command": ["scontrol"], "stdout_sha256": "telemetry"}
        initial = {"slurm": slurm, "owner_sha256": "o", "gate_sha256": "g",
                   "package_sha256": {"p": "h"}, "source": {"s": "h"}}
        stable = {"validate_owner": "o", "validate_review_gate": "g", "package_hashes": {"p": "h"},
                  "validate_source": {"s": "h"}, "query_slurm": slurm}
        with mock.patch.object(m, "validate_resource_env"), \
             mock.patch.object(m, "validate_owner", return_value=stable["validate_owner"]), \
             mock.patch.object(m, "validate_review_gate", return_value=stable["validate_review_gate"]), \
             mock.patch.object(m, "package_hashes", return_value=stable["package_hashes"]), \
             mock.patch.object(m, "validate_source", return_value=stable["validate_source"]), \
             mock.patch.object(m, "query_slurm", return_value=stable["query_slurm"]):
            m.revalidate_authority(ROOT, CFG, slurm_env(), initial)
        drift_cases = {
            "validate_owner": "changed", "validate_review_gate": "changed",
            "package_hashes": {"p": "changed"}, "validate_source": {"s": "changed"},
            "query_slurm": {"fields": {"JobId": "18"}, "command": ["scontrol"]},
        }
        for axis, value in drift_cases.items():
            returns = dict(stable); returns[axis] = value
            with self.subTest(axis=axis), mock.patch.object(m, "validate_resource_env"), \
                 mock.patch.object(m, "validate_owner", return_value=returns["validate_owner"]), \
                 mock.patch.object(m, "validate_review_gate", return_value=returns["validate_review_gate"]), \
                 mock.patch.object(m, "package_hashes", return_value=returns["package_hashes"]), \
                 mock.patch.object(m, "validate_source", return_value=returns["validate_source"]), \
                 mock.patch.object(m, "query_slurm", return_value=returns["query_slurm"]), \
                 self.assertRaises(m.IntegrityError):
                m.revalidate_authority(ROOT, CFG, slurm_env(), initial)

    def test_23_explicit_handle_close_attempts_all_and_detects_failure(self):
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf(fail=(part == 3)) for part in parts}
        with self.assertRaises(m.CleanupError) as cm:
            m.close_leaf_handles(files, CFG)
        self.assertEqual(sum(x.file.calls for x in files.values()), 12)
        self.assertEqual(cm.exception.close_audit["closed_count"], 11)
        clean = {part: FakeLeaf() for part in parts}
        audit = m.close_leaf_handles(clean, CFG)
        self.assertEqual(audit["closed_count"], 12)
        self.assertTrue(all(x.file.id.valid == 0 for x in clean.values()))

    def test_24_precleanup_stage_immutable_and_tamper_detected(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        with tempfile.TemporaryDirectory() as td:
            bundle, digest = m.stage_observations(td, "slurm-17", metrics, audit, resolved)
            self.assertEqual(m.verify_observation_bundle(bundle), digest)
            self.assertEqual(json.loads((bundle / "OBSERVATION_MANIFEST.json").read_text())["scientific_call_count"], 72)
            (bundle / "metrics.precleanup.json").chmod(0o644)
            (bundle / "metrics.precleanup.json").write_text("tampered\n")
            with self.assertRaises(m.IntegrityError): m.verify_observation_bundle(bundle)

    def test_25_cleanup_failure_preserves_observation_and_cannot_pass(self):
        initial = {"slurm": {"fields": {}, "command": []}, "owner_sha256": "o", "gate_sha256": "g",
                   "package_sha256": {"x": "h"}, "source": {"s": "h"}}
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf(fail=(part == 3)) for part in parts}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = "preview"
            with termination_controller() as controller, mock.patch.dict(os.environ, slurm_env(), clear=True), \
                 mock.patch.object(m, "prepare_authority", return_value=initial), \
                 mock.patch.object(m, "probe_installed_open", side_effect=lambda _r, _c, lifecycle: (lifecycle.attach_db(
                     types.SimpleNamespace(files=files)) or (metrics, audit, resolved))), \
                 mock.patch.object(m, "validate_owner", return_value="o"):
                with self.assertRaises(m.CleanupError) as cm: m.formal(root, cfg, "cleanup-fail", controller)
            exc = cm.exception; evidence = root / exc.observation_bundle
            before = m.sha256_file(evidence / "OBSERVATION_MANIFEST.json")
            self.assertEqual(before, exc.observation_manifest_sha256)
            with mock.patch.object(m, "revalidate_authority", return_value=None):
                self.assertTrue(m.publish_failure_if_owned(root, cfg, "cleanup-fail", exc, slurm_env(), initial))
            status = m.verify_bundle(root / "preview")
            self.assertEqual(status["status"], "LEAF_CLOSE_ONLY_FAILED")
            self.assertFalse(status["semantic_success"])
            self.assertEqual(before, m.sha256_file(evidence / "OBSERVATION_MANIFEST.json"))
            current = m.current_bytes(root / "preview")
            (evidence / "metrics.precleanup.json").chmod(0o644)
            (evidence / "metrics.precleanup.json").write_text("tampered\n")
            with mock.patch.object(m, "revalidate_authority", return_value=None):
                self.assertFalse(m.publish_failure_if_owned(root, cfg, "cleanup-tampered", exc, slurm_env(), initial))
            self.assertEqual(current, m.current_bytes(root / "preview"))

    def test_26_parent_job_evidence_and_science_are_hash_pinned(self):
        parent = CFG["parent_job_identity"]
        self.assertEqual(parent["slurm_job_id"], "11533175")
        self.assertEqual(len(parent["artifacts"]), 4)
        for rel, digest in parent["artifacts"].items(): self.assertEqual(m.sha256_file(ROOT / rel), digest)
        self.assertEqual(m.sha256_file(ROOT / "configs" / (parent["exp_id"] + ".yaml")),
                         parent["audited_science_config_sha256"])

    def test_27_observation_dirty_attempt_and_bundle_extra_fail_closed(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        with tempfile.TemporaryDirectory() as td:
            bundle, _ = m.stage_observations(td, "x", metrics, audit, resolved)
            bundle.chmod(0o755)
            (bundle / "extra").write_text("x")
            with self.assertRaises(m.IntegrityError): m.verify_observation_bundle(bundle)
            with self.assertRaises(m.IntegrityError): m.stage_observations(td, "x", metrics, audit, resolved)

    def test_28_wrapper_cannot_overwrite_attempt_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            preview = Path(td)
            m.publish(preview, "slurm-17", "LEAF_CLOSE_ONLY_FAILED", False,
                      {"report.json": m.canonical_json({"error": "cleanup"})})
            before = m.current_bytes(preview)
            self.assertTrue(m.wrapper_failure_already_closed(preview, "slurm-17"))
            self.assertFalse(m.wrapper_failure_already_closed(preview, "slurm-18"))
            self.assertEqual(before, m.current_bytes(preview))

    def test_29_local_science_scheduler_match_parent_job(self):
        cfg = json.loads(json.dumps(CFG)); cfg["selected_records"][0]["canonical_name"] = "drift"
        m.validate_config(cfg)
        with self.assertRaisesRegex(m.IntegrityError, "scientific/source payload"):
            m.validate_small_assets(ROOT, cfg)
        cfg = json.loads(json.dumps(CFG)); cfg["parent_job_identity"]["audited_scheduler"]["memory"] = "8G"
        with self.assertRaisesRegex(m.IntegrityError, "scheduler identity"):
            m.validate_config(cfg)

    def test_30_staging_or_term_failure_still_closes_all_handles(self):
        initial = {"slurm": {"fields": {}, "command": []}, "owner_sha256": "o", "gate_sha256": "g",
                   "package_sha256": {"x": "h"}, "source": {"s": "h"}}
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        for injected in (OSError("stage failed"), m.TerminationRequested("term")):
            files = {part: FakeLeaf() for part in parts}
            with tempfile.TemporaryDirectory() as td:
                root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = "preview"
                with termination_controller() as controller, mock.patch.dict(os.environ, slurm_env(), clear=True), \
                     mock.patch.object(m, "prepare_authority", return_value=initial), \
                     mock.patch.object(m, "probe_installed_open", side_effect=lambda _r, _c, lifecycle: (lifecycle.attach_db(
                         types.SimpleNamespace(files=files)) or (metrics, audit, resolved))), \
                     mock.patch.object(m, "stage_observations", side_effect=injected), \
                     mock.patch.object(m, "validate_owner", return_value="o"), \
                     self.assertRaises(type(injected)):
                    m.formal(root, cfg, "failure-before-cleanup", controller)
                self.assertEqual(sum(x.file.calls for x in files.values()), 12)
                self.assertTrue(all(x.file.id.valid == 0 for x in files.values()))

    def test_31_partial_constructor_baseexception_closes_every_present_handle(self):
        class InjectedBase(BaseException): pass
        parts = CFG["source_contract"]["expected_partition_order"]
        class PartialDB:
            last = None
            def __init__(self, _path, _mode):
                type(self).last = self; self.files = {}
                for part in parts[:5]: self.files[part] = FakeLeaf()
                raise InjectedBase("after five handles")
        fake_module = types.SimpleNamespace(FamDB=PartialDB)
        with termination_controller() as controller, tempfile.TemporaryDirectory() as td, mock.patch.object(m.importlib, "import_module", return_value=fake_module), \
             self.assertRaises(InjectedBase) as cm:
            m.execute_probe_stage_cleanup(ROOT, CFG, td, "constructor-base", controller)
        self.assertEqual(len(PartialDB.last.files), 5)
        self.assertEqual(sum(x.file.calls for x in PartialDB.last.files.values()), 5)
        self.assertTrue(all(x.file.id.valid == 0 for x in PartialDB.last.files.values()))
        self.assertTrue(cm.exception.cleanup_secondary)

    def test_32_partial_unexpected_keys_cleanup_then_reject(self):
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {parts[0]: FakeLeaf(), parts[1]: FakeLeaf(), "3": FakeLeaf(), 99: FakeLeaf()}
        with self.assertRaises(m.CleanupError) as cm: m.close_leaf_handles(files, CFG)
        self.assertEqual(files[parts[0]].file.calls, 1); self.assertEqual(files[parts[1]].file.calls, 1)
        self.assertEqual(files["3"].file.calls, 0); self.assertEqual(files[99].file.calls, 0)
        errors = cm.exception.close_audit["errors"]
        self.assertTrue(any(x.get("error") == "non-integer partition key" for x in errors))
        self.assertTrue(any(x.get("error") == "unexpected partition key" for x in errors))
        self.assertTrue(any(x.get("error") == "partial frozen partition keyset" for x in errors))

    def test_33_leaf_and_handle_alias_close_each_unique_handle_once(self):
        parts = CFG["source_contract"]["expected_partition_order"]
        for mode in ("leaf", "handle"):
            files = {part: FakeLeaf() for part in parts}
            if mode == "leaf": files[parts[1]] = files[parts[0]]
            else: files[parts[1]].file = files[parts[0]].file
            shared = files[parts[0]].file
            with self.subTest(mode=mode), self.assertRaises(m.CleanupError) as cm:
                m.close_leaf_handles(files, CFG)
            self.assertEqual(shared.calls, 1)
            self.assertEqual(cm.exception.close_audit["unique_handle_count"], 11)
            self.assertTrue(any("shared" in x.get("error", "") for x in cm.exception.close_audit["errors"]))

    def test_34_double_close_and_baseexception_close_fail_closed(self):
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf() for part in parts}
        m.close_leaf_handles(files, CFG)
        with self.assertRaises(m.CleanupError): m.close_leaf_handles(files, CFG)
        self.assertTrue(all(x.file.calls == 1 for x in files.values()))
        class CloseBase(BaseException): pass
        files = {part: FakeLeaf(raised=CloseBase("close base")) if part == 3 else FakeLeaf() for part in parts}
        with self.assertRaises(m.CleanupError) as cm: m.close_leaf_handles(files, CFG)
        self.assertEqual(sum(x.file.calls for x in files.values()), 12)
        self.assertTrue(any(x.get("error_type") == "CloseBase" for x in cm.exception.close_audit["errors"]))

    def test_35_observation_manifest_identity_schema_matrix(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        mutations = {
            "wrong_exp": lambda x: x.__setitem__("exp_id", "evil"),
            "wrong_attempt": lambda x: x.__setitem__("attempt_id", "other"),
            "wrong_count": lambda x: x.__setitem__("scientific_call_count", 71),
            "wrong_status": lambda x: x.__setitem__("status", "evil"),
            "wrong_schema": lambda x: x.__setitem__("schema_version", "evil"),
            "wrong_payload_hash": lambda x: x.__setitem__("payload_sha256", "0" * 64),
            "self_entry": lambda x: x["files"].__setitem__(0, dict(x["files"][0], path="OBSERVATION_MANIFEST.json")),
            "traversal": lambda x: x["files"].__setitem__(0, dict(x["files"][0], path="../evil")),
            "duplicate": lambda x: x["files"].__setitem__(1, dict(x["files"][1], path=x["files"][0]["path"])),
            "missing": lambda x: x["files"].pop(),
            "extra_manifest_key": lambda x: x.__setitem__("evil", True),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                bundle, _ = m.stage_observations(td, "slurm-17", metrics, audit, resolved)
                manifest = bundle / "OBSERVATION_MANIFEST.json"; manifest.chmod(0o644)
                obj = json.loads(manifest.read_text()); mutate(obj); manifest.write_text(m.canonical_json(obj))
                with self.assertRaises(m.IntegrityError): m.verify_observation_bundle(bundle, "slurm-17")

    def test_36_observation_evil_only_extra_symlink_and_collision_rejected(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); evil = root / "attempt_observations" / "x" / ("0" * 64); evil.mkdir(parents=True)
            (evil / "evil.json").write_text("{}\n")
            m.write_json(evil / "OBSERVATION_MANIFEST.json",
                         {"schema_version": m.SCHEMA, "exp_id": m.EXP_ID, "attempt_id": "x",
                          "status": m.OBSERVATION_STATUS, "scientific_call_count": 72,
                          "payload_sha256": "0" * 64,
                          "files": [{"path": "evil.json", "size": 3, "sha256": m.sha256_file(evil / "evil.json")}]})
            with self.assertRaises(m.IntegrityError): m.verify_observation_bundle(evil, "x")
        with tempfile.TemporaryDirectory() as td:
            bundle, _ = m.stage_observations(td, "x", metrics, audit, resolved); bundle.chmod(0o755)
            (bundle / "extra").write_text("x")
            with self.assertRaises(m.IntegrityError): m.verify_observation_bundle(bundle, "x")
        with tempfile.TemporaryDirectory() as td:
            real = Path(td) / "real"; real.mkdir(); m.stage_observations(real, "x", metrics, audit, resolved)
            link = Path(td) / "linked"; link.symlink_to(real, target_is_directory=True)
            linked_bundle = next((link / "attempt_observations" / "x").iterdir())
            with self.assertRaisesRegex(m.IntegrityError, "symlink ancestor"):
                m.verify_observation_bundle(linked_bundle, "x")
        with tempfile.TemporaryDirectory() as td:
            bundle, _ = m.stage_observations(td, "x", metrics, audit, resolved); bundle.chmod(0o755)
            victim = bundle / "exact_records.json"; victim.chmod(0o644); victim.unlink()
            victim.symlink_to(bundle / "leaf_probe_matrix.json")
            with self.assertRaisesRegex(m.IntegrityError, "symlink/directory entry"):
                m.verify_observation_bundle(bundle, "x")
        with tempfile.TemporaryDirectory() as td:
            preview = Path(td); parent = preview / "attempt_observations" / "x"; parent.mkdir(parents=True)
            (parent / "precreated-collision").mkdir()
            with self.assertRaisesRegex(m.IntegrityError, "dirty attempt"):
                m.stage_observations(preview, "x", metrics, audit, resolved)

    def test_37_payload_basename_hash_and_resolved_containment(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        with tempfile.TemporaryDirectory() as td:
            bundle, _ = m.stage_observations(td, "x", metrics, audit, resolved)
            wrong = bundle.with_name("f" * 64); bundle.rename(wrong)
            with self.assertRaisesRegex(m.IntegrityError, "payload/directory"):
                m.verify_observation_bundle(wrong, "x")
        with tempfile.TemporaryDirectory() as td:
            bundle, _ = m.stage_observations(td, "x", metrics, audit, resolved)
            bundle.chmod(0o755)
            target = bundle / "exact_records.json"; target.chmod(0o644)
            not_observed = dict(resolved[0]); not_observed["canonical_name"] = "not-observed"
            target.write_text(m.canonical_json([not_observed]))
            metrics_path = bundle / "metrics.precleanup.json"; metrics_path.chmod(0o644)
            metrics_obj = json.loads(metrics_path.read_text()); metrics_obj["resolved_count"] = 1
            metrics_path.write_text(m.canonical_json(metrics_obj))
            manifest = bundle / "OBSERVATION_MANIFEST.json"; manifest.chmod(0o644)
            obj = json.loads(manifest.read_text())
            for row in obj["files"]:
                path = bundle / row["path"]
                row["size"] = path.stat().st_size; row["sha256"] = m.sha256_file(path)
            payload = {name: (bundle / name).read_bytes() for name in m.OBSERVATION_FILES}
            new_hash = m.observation_payload_hash(payload); obj["payload_sha256"] = new_hash
            manifest.write_text(m.canonical_json(obj)); new_bundle = bundle.with_name(new_hash); bundle.rename(new_bundle)
            with self.assertRaisesRegex(m.IntegrityError, "resolved rows"):
                m.verify_observation_bundle(new_bundle, "x")

    def test_38_signal_window_matrix_exact_once_cleanup_and_stage_preservation(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        stage_expected = {"stage_after_promote", "after_stage", "close_before", "close_inside", "postclose"}
        for event in ("probe_inside", "after_probe", "before_stage", "stage_inside", "stage_after_promote",
                      "after_stage", "close_before", "close_inside", "postclose"):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as td:
                root = Path(td); preview = root / "preview"; cfg = dict(CFG, preview_root="preview")
                files = {part: FakeLeaf() for part in parts}
                db = types.SimpleNamespace(files=files); fired = {"value": False}
                m.publish(preview, "window", "FORMAL_RUNNING", False, {})
                current_before = m.current_bytes(preview)
                def probe(_root, _cfg, lifecycle):
                    lifecycle.attach_db(db)
                    m._lifecycle_event("probe_inside")
                    return metrics, audit, resolved
                def inject(name):
                    if name == event and not fired["value"]:
                        fired["value"] = True
                        raise m.TerminationRequested("injected at " + name)
                with termination_controller() as controller, mock.patch.object(m, "probe_installed_open", side_effect=probe), \
                     mock.patch.object(m, "_lifecycle_event", side_effect=inject), \
                     self.assertRaises(m.TerminationRequested) as cm:
                    m.execute_probe_stage_cleanup(root, cfg, preview, "window", controller)
                self.assertTrue(fired["value"])
                self.assertEqual(m.current_bytes(preview), current_before)
                self.assertEqual(m.verify_bundle(preview)["status"], "FORMAL_RUNNING")
                self.assertEqual(sum(x.file.calls for x in files.values()), 12)
                self.assertTrue(all(x.file.calls == 1 and x.file.id.valid == 0 for x in files.values()))
                evidence = m.failure_lifecycle_evidence(root, cfg, "window", cm.exception)
                if event in stage_expected:
                    self.assertIn("precleanup_observation_manifest_sha256", evidence)
                    self.assertEqual(len(list((preview / "attempt_observations" / "window").iterdir())), 1)
                else:
                    self.assertNotIn("precleanup_observation_manifest_sha256", evidence)

    def test_39_primary_error_preserved_cleanup_secondary_structured(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf(fail=(part == 3)) for part in parts}
        db = types.SimpleNamespace(files=files)
        def probe(_root, _cfg, lifecycle):
            lifecycle.attach_db(db); return metrics, audit, resolved
        def inject(name):
            if name == "after_probe": raise OSError("primary stage-boundary error")
        with termination_controller() as controller, tempfile.TemporaryDirectory() as td, \
             mock.patch.object(m, "probe_installed_open", side_effect=probe), \
             mock.patch.object(m, "_lifecycle_event", side_effect=inject), \
             self.assertRaisesRegex(OSError, "primary stage-boundary") as cm:
            m.execute_probe_stage_cleanup(ROOT, CFG, td, "secondary", controller)
        self.assertEqual(sum(x.file.calls for x in files.values()), 12)
        self.assertTrue(cm.exception.cleanup_secondary)
        self.assertEqual(cm.exception.cleanup_secondary[0]["error_type"], "CleanupError")

    def test_40_no_primary_cleanup_failure_is_cleanup_error(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf(fail=(part == 3)) for part in parts}
        db = types.SimpleNamespace(files=files)
        def probe(_root, _cfg, lifecycle):
            lifecycle.attach_db(db); return metrics, audit, resolved
        with termination_controller() as controller, tempfile.TemporaryDirectory() as td, mock.patch.object(m, "probe_installed_open", side_effect=probe):
            root = Path(td); cfg = dict(CFG, preview_root="preview")
            with self.assertRaises(m.CleanupError) as cm:
                m.execute_probe_stage_cleanup(root, cfg, root / "preview", "cleanup-only", controller)
            self.assertEqual(sum(x.file.calls for x in files.values()), 12)
            evidence = m.failure_lifecycle_evidence(root, cfg, "cleanup-only", cm.exception)
            self.assertIn("precleanup_observation_manifest_sha256", evidence)

    def test_41_real_term_cleanup_entry_preserves_probe_primary(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf() for part in parts}; db = types.SimpleNamespace(files=files)
        fired = {"primary": False, "term": False}
        def probe(_root, _cfg, lifecycle): lifecycle.attach_db(db); return metrics, audit, resolved
        def events(name):
            if name == "after_probe" and not fired["primary"]:
                fired["primary"] = True; raise OSError("probe primary")
            if name == "cleanup_guard_entered" and not fired["term"]:
                fired["term"] = True; os.kill(os.getpid(), signal.SIGTERM)
        old = {x: signal.getsignal(x) for x in m.DeferredCleanupSignals.SIGNALS}
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
        with tempfile.TemporaryDirectory() as td:
            try:
                root = Path(td)
                with termination_controller() as controller, mock.patch.object(m, "probe_installed_open", side_effect=probe), \
                     mock.patch.object(m, "_lifecycle_event", side_effect=events), \
                     self.assertRaisesRegex(OSError, "probe primary") as cm:
                    m.execute_probe_stage_cleanup(root, CFG, root / "preview", "real-term-primary", controller)
                self.assertEqual(sum(x.file.calls for x in files.values()), 12)
                self.assertEqual([x["name"] for x in cm.exception.pending_cleanup_signals], ["SIGTERM"])
                evidence = m.failure_lifecycle_evidence(root, CFG, "real-term-primary", cm.exception)
                self.assertEqual(evidence["pending_cleanup_signals"][0]["name"], "SIGTERM")
                self.assertEqual({x: signal.getsignal(x) for x in old}, old)
                self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, []), old_mask)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)

    def test_42_real_term_without_primary_replayed_after_all_close(self):
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf() for part in parts}; lifecycle = m.HandleLifecycle(CFG)
        lifecycle.attach_db(types.SimpleNamespace(files=files)); fired = {"value": False}
        def events(name):
            if name == "close_inside" and not fired["value"]:
                fired["value"] = True; os.kill(os.getpid(), signal.SIGTERM)
        with termination_controller() as controller, mock.patch.object(m, "_lifecycle_event", side_effect=events), \
             self.assertRaises(m.TerminationRequested) as cm:
            lifecycle.ensure_cleanup(attempt="real-term"); controller.raise_if_pending()
        self.assertEqual(sum(x.file.calls for x in files.values()), 12)
        self.assertTrue(lifecycle.cleanup_done)
        self.assertEqual([x["name"] for x in cm.exception.pending_cleanup_signals], ["SIGTERM"])

    def test_43_close_error_plus_real_term_signal_primary_cleanup_secondary(self):
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf(fail=(part == 3)) for part in parts}; lifecycle = m.HandleLifecycle(CFG)
        lifecycle.attach_db(types.SimpleNamespace(files=files)); fired = {"value": False}
        def events(name):
            if name == "cleanup_guard_entered" and not fired["value"]:
                fired["value"] = True; os.kill(os.getpid(), signal.SIGTERM)
        with termination_controller() as controller, mock.patch.object(m, "_lifecycle_event", side_effect=events), \
             self.assertRaises(m.TerminationRequested) as cm:
            cleanup = None
            try: lifecycle.ensure_cleanup(attempt="term-close-error")
            except m.CleanupError as exc: cleanup = exc
            controller.raise_if_pending(cleanup_secondary=cleanup)
        self.assertEqual(sum(x.file.calls for x in files.values()), 12)
        self.assertEqual(cm.exception.cleanup_secondary[0]["error_type"], "CleanupError")
        self.assertEqual(cm.exception.pending_cleanup_signals[0]["name"], "SIGTERM")

    def test_44_real_sigint_and_multiple_signals_are_deferred(self):
        parts = CFG["source_contract"]["expected_partition_order"]
        for signals, expected in (((signal.SIGINT,), ["SIGINT"]),
                                  ((signal.SIGTERM, signal.SIGINT), ["SIGTERM", "SIGINT"])):
            with self.subTest(signals=signals):
                files = {part: FakeLeaf() for part in parts}; lifecycle = m.HandleLifecycle(CFG)
                lifecycle.attach_db(types.SimpleNamespace(files=files)); fired = {"value": False}
                def events(name):
                    if name == "cleanup_guard_entered" and not fired["value"]:
                        fired["value"] = True
                        for item in signals: os.kill(os.getpid(), item)
                with termination_controller() as controller, mock.patch.object(m, "_lifecycle_event", side_effect=events), \
                     self.assertRaises(m.TerminationRequested) as cm:
                    lifecycle.ensure_cleanup(attempt="multi-signal"); controller.raise_if_pending()
                self.assertEqual(sum(x.file.calls for x in files.values()), 12)
                self.assertEqual([x["name"] for x in cm.exception.pending_cleanup_signals], expected)

    def test_45_signal_handler_restore_and_no_signal_regression(self):
        parts = CFG["source_contract"]["expected_partition_order"]
        before_handlers = {x: signal.getsignal(x) for x in m.DeferredCleanupSignals.SIGNALS}
        before_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
        files = {part: FakeLeaf() for part in parts}; lifecycle = m.HandleLifecycle(CFG)
        with termination_controller() as controller:
            lifecycle.attach_db(types.SimpleNamespace(files=files)); lifecycle.ensure_cleanup(attempt="no-signal")
            controller.raise_if_pending()
        self.assertEqual(sum(x.file.calls for x in files.values()), 12)
        self.assertEqual({x: signal.getsignal(x) for x in before_handlers}, before_handlers)
        self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, []), before_mask)

    def test_46_real_signal_constructor_probe_stage_envelope(self):
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        class EnvelopeDB:
            last = None
            def __init__(self, _path, _mode):
                type(self).last = self; self.files = {part: FakeLeaf() for part in parts}
        module = types.SimpleNamespace(FamDB=EnvelopeDB)
        for event in ("constructor_before", "constructor_after", "probe_inside", "stage_inside",
                      "stage_after_promote", "after_stage", "cleanup_guard_entered", "close_inside"):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as td, termination_controller() as controller:
                fired = {"value": False}; root = Path(td); cfg = dict(CFG, preview_root="preview")
                def events(name):
                    if name == event and not fired["value"]:
                        fired["value"] = True; os.kill(os.getpid(), signal.SIGTERM)
                with mock.patch.object(m.importlib, "import_module", return_value=module), \
                     mock.patch.object(m, "probe_leaf_mapping", return_value=(metrics, audit, resolved)), \
                     mock.patch.object(m, "_lifecycle_event", side_effect=events), \
                     self.assertRaises(m.TerminationRequested) as cm:
                    m.execute_probe_stage_cleanup(root, cfg, root / "preview", "os-envelope", controller)
                files = EnvelopeDB.last.files
                self.assertTrue(fired["value"]); self.assertEqual(sum(x.file.calls for x in files.values()), 12)
                self.assertTrue(all(x.file.calls == 1 and x.file.id.valid == 0 for x in files.values()))
                self.assertEqual(cm.exception.pending_cleanup_signals[0]["name"], "SIGTERM")
                evidence = m.failure_lifecycle_evidence(root, cfg, "os-envelope", cm.exception)
                self.assertIn("precleanup_observation_manifest_sha256", evidence)

    def test_47_sys_settrace_real_term_old_gap_and_finally_entry(self):
        source = (HERE / "close_only_probe.py").read_text().splitlines()
        targets = []
        for needle in ("metrics, audit, resolved = probe_installed_open", "lifecycle.ensure_cleanup(primary=primary"):
            matches = [i + 1 for i, line in enumerate(source) if needle in line]
            self.assertEqual(len(matches), 1); targets.append(matches[0])
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        for target_line in targets:
            with self.subTest(line=target_line), tempfile.TemporaryDirectory() as td, termination_controller() as controller:
                files = {part: FakeLeaf() for part in parts}; root = Path(td); cfg = dict(CFG, preview_root="preview")
                fired = {"value": False}; primary_line = targets[1] == target_line
                def probe(_root, _cfg, lifecycle):
                    lifecycle.attach_db(types.SimpleNamespace(files=files))
                    if primary_line: raise OSError("trace primary")
                    return metrics, audit, resolved
                def tracer(frame, event, _arg):
                    if event == "line" and Path(frame.f_code.co_filename) == HERE / "close_only_probe.py" and \
                       frame.f_lineno == target_line and not fired["value"]:
                        fired["value"] = True; os.kill(os.getpid(), signal.SIGTERM)
                    return tracer
                sys.settrace(tracer)
                try:
                    if primary_line:
                        with mock.patch.object(m, "probe_installed_open", side_effect=probe), \
                             self.assertRaisesRegex(OSError, "trace primary") as cm:
                            m.execute_probe_stage_cleanup(root, cfg, root / "preview", "trace", controller)
                        self.assertEqual(cm.exception.pending_cleanup_signals[0]["name"], "SIGTERM")
                    else:
                        with mock.patch.object(m, "probe_installed_open", side_effect=probe), \
                             self.assertRaises(m.TerminationRequested):
                            m.execute_probe_stage_cleanup(root, cfg, root / "preview", "trace", controller)
                finally:
                    sys.settrace(None)
                self.assertTrue(fired["value"]); self.assertEqual(sum(x.file.calls for x in files.values()), 12)

    def test_48_restore_lines_real_signals_are_process_isolated(self):
        runner = HERE / "close_only_probe.py"
        code = r'''
import importlib.util, os, signal, sys
path=sys.argv[1]; event=sys.argv[2]; signum=int(sys.argv[3])
spec=importlib.util.spec_from_file_location("x",path); x=importlib.util.module_from_spec(spec); spec.loader.exec_module(x)
seen=[]
def old(sig, frame): seen.append(sig); raise RuntimeError("old handler invoked")
signal.signal(signal.SIGTERM, old); signal.signal(signal.SIGINT, old)
c=x.DeferredCleanupSignals().enter(); fired=[False]
def hook(name):
    if name==event and not fired[0]: fired[0]=True; os.kill(os.getpid(),signum)
pending=c.restore_for_tests(hook)
assert fired[0] and signum in pending and not seen
assert signal.getsignal(signal.SIGTERM) is old and signal.getsignal(signal.SIGINT) is old
'''
        for event in ("controller_restore_handlers", "controller_restore_mask"):
            for signum in (signal.SIGTERM, signal.SIGINT):
                result = subprocess.run([sys.executable, "-c", code, str(runner), event, str(int(signum))],
                                        text=True, capture_output=True, timeout=10)
                with self.subTest(event=event, signum=signum):
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_49_production_main_never_restores_deferred_handlers(self):
        source = (HERE / "close_only_probe.py").read_text()
        main_source = source[source.index("def main("):]
        self.assertNotIn("restore_for_tests(", main_source)
        self.assertIn("retains deferred TERM/INT handlers", main_source)

    def test_50_real_term_after_stage_never_upgrades_canonical(self):
        initial = {"slurm": {"fields": {}, "command": []}, "owner_sha256": "o", "gate_sha256": "g",
                   "package_sha256": {"x": "h"}, "source": {"s": "h"}}
        metrics, audit, resolved = m.evaluate_observations(CFG, exact_observations())
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf() for part in parts}; fired = {"value": False}
        def probe(_root, _cfg, lifecycle):
            lifecycle.attach_db(types.SimpleNamespace(files=files)); return metrics, audit, resolved
        def events(name):
            if name == "after_stage" and not fired["value"]:
                fired["value"] = True; os.kill(os.getpid(), signal.SIGTERM)
        with tempfile.TemporaryDirectory() as td, termination_controller() as controller:
            root = Path(td); cfg = dict(CFG, preview_root="preview")
            with mock.patch.dict(os.environ, slurm_env(), clear=True), \
                 mock.patch.object(m, "prepare_authority", return_value=initial), \
                 mock.patch.object(m, "validate_owner", return_value="o"), \
                 mock.patch.object(m, "probe_installed_open", side_effect=probe), \
                 mock.patch.object(m, "_lifecycle_event", side_effect=events), \
                 self.assertRaises(m.TerminationRequested):
                m.formal(root, cfg, "canonical-term", controller)
            self.assertEqual(sum(x.file.calls for x in files.values()), 12)
            self.assertEqual(m.verify_bundle(root / "preview")["status"], "FORMAL_RUNNING")

    def _run_main_signal_failure(self, action, attempt):
        """Exercise top-level reconciliation and the real attempt_failure writer."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = json.loads(json.dumps(CFG))
            cfg["project_root"] = str(root); cfg["preview_root"] = "preview"
            controller = m.DeferredCleanupSignals()
            def fake_formal(_root, _cfg, _attempt, passed_controller, _authority):
                self.assertIs(passed_controller, controller)
                action(passed_controller)
            try:
                with mock.patch.object(m, "load_config", return_value=cfg), \
                     mock.patch.object(m, "DeferredCleanupSignals", return_value=controller), \
                     mock.patch.object(m, "formal", side_effect=fake_formal), \
                     mock.patch.object(m, "publish_failure_if_owned", return_value=False), \
                     mock.patch.object(sys, "stderr"):
                    rc = m.main(["--config", "synthetic.json", "--attempt-id", attempt])
                self.assertEqual(rc, 2)
                payload = json.loads((root / "preview" / "attempt_failures" / (attempt + ".json")).read_text())
                return payload
            finally:
                if controller.active:
                    controller.restore_for_tests()

    def test_51_main_signal_evidence_exact_delta_and_repetitions(self):
        def send(*signums, primary=None, late=None):
            def action(controller):
                for signum in signums: os.kill(os.getpid(), signum)
                if primary is not None: raise primary
                if late is not None:
                    try:
                        controller.raise_if_pending()
                    except m.TerminationRequested:
                        os.kill(os.getpid(), late)
                        raise
                controller.raise_if_pending()
            return action

        cases = [
            ("one-term", send(signal.SIGTERM), ["SIGTERM"], "TerminationRequested"),
            ("term-int", send(signal.SIGTERM, signal.SIGINT), ["SIGTERM", "SIGINT"],
             "TerminationRequested"),
            ("term-term", send(signal.SIGTERM, signal.SIGTERM), ["SIGTERM", "SIGTERM"],
             "TerminationRequested"),
            ("primary-term", send(signal.SIGTERM, primary=OSError("primary retained")), ["SIGTERM"],
             "OSError"),
            ("late-int", send(signal.SIGTERM, late=signal.SIGINT), ["SIGTERM", "SIGINT"],
             "TerminationRequested"),
            ("no-signal", send(primary=OSError("no signal")), [], "OSError"),
        ]
        for attempt, action, names, error_type in cases:
            with self.subTest(attempt=attempt):
                payload = self._run_main_signal_failure(action, attempt)
                events = payload["pending_cleanup_signals"]
                self.assertEqual([row["name"] for row in events], names)
                self.assertEqual([row["order"] for row in events], list(range(1, len(events) + 1)))
                self.assertEqual(payload["error_type"], error_type)
                self.assertEqual(m.validate_signal_events(events), events)
                for row in events:
                    self.assertEqual(set(row), {"signum", "name", "order", "timestamp_monotonic_ns"})

    def test_52_signal_event_schema_and_prefix_fail_closed(self):
        valid = {"signum": int(signal.SIGTERM), "name": "SIGTERM", "order": 1,
                 "timestamp_monotonic_ns": 1}
        bad_rows = [
            None,
            [dict(valid, order=2)],
            [dict(valid, signum=True)],
            [dict(valid, name="SIGINT")],
            [dict(valid, timestamp_monotonic_ns="1")],
            [dict(valid, extra=True)],
        ]
        for rows in bad_rows:
            with self.subTest(rows=rows), self.assertRaises(m.IntegrityError):
                m.validate_signal_events(rows)
        with termination_controller() as controller:
            os.kill(os.getpid(), signal.SIGTERM)
            exc = OSError("prefix drift")
            exc.pending_cleanup_signals = [dict(valid, signum=int(signal.SIGINT), name="SIGINT")]
            with self.assertRaisesRegex(m.IntegrityError, "not a controller prefix"):
                m.reconcile_pending_signals(exc, controller)

    def _formal_terminal_commit_case(self, route_stop, event=None, authority_failure=False, trace_signal=False):
        initial = {"slurm": {"fields": {}, "command": []}, "owner_sha256": "o", "gate_sha256": "g",
                   "package_sha256": {"x": "h"}, "source": {"s": "h"}}
        observations = exact_observations()
        if route_stop:
            observations[7]["record"] = None
        metrics, audit, resolved = m.evaluate_observations(CFG, observations, raise_on_block=False)
        parts = CFG["source_contract"]["expected_partition_order"]
        files = {part: FakeLeaf() for part in parts}; fired = {"value": False}
        def probe(_root, _cfg, lifecycle):
            lifecycle.attach_db(types.SimpleNamespace(files=files)); return metrics, audit, resolved
        def events(name):
            if name == event and not fired["value"]:
                fired["value"] = True; os.kill(os.getpid(), signal.SIGTERM)
        trace_line = None
        if trace_signal:
            source = (HERE / "close_only_probe.py").read_text().splitlines()
            needle = '_lifecycle_event("%s")' % event
            matches = [index + 1 for index, line in enumerate(source) if needle in line]
            self.assertEqual(matches, [matches[0]] if matches else [], "missing/duplicate trace seam: " + needle)
            self.assertEqual(len(matches), 1); trace_line = matches[0]
        def tracer(frame, trace_event, _arg):
            if trace_event == "line" and Path(frame.f_code.co_filename) == HERE / "close_only_probe.py" and \
               frame.f_lineno == trace_line and not fired["value"]:
                fired["value"] = True; os.kill(os.getpid(), signal.SIGTERM)
            return tracer
        calls = {"value": 0}
        def revalidate(*_args):
            calls["value"] += 1
            if authority_failure and calls["value"] >= 2:
                raise m.IntegrityError("injected supersession authority drift")
        with tempfile.TemporaryDirectory() as td, termination_controller() as controller:
            root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = "preview"
            patches = [mock.patch.dict(os.environ, slurm_env(), clear=True),
                       mock.patch.object(m, "prepare_authority", return_value=initial),
                       mock.patch.object(m, "validate_owner", return_value="o"),
                       mock.patch.object(m, "validate_source", return_value=initial["source"]),
                       mock.patch.object(m, "package_hashes", return_value=initial["package_sha256"]),
                       mock.patch.object(m, "query_slurm", return_value=initial["slurm"]),
                       mock.patch.object(m, "revalidate_authority", side_effect=revalidate),
                       mock.patch.object(m, "probe_installed_open", side_effect=probe)]
            if not trace_signal:
                patches.append(mock.patch.object(m, "_lifecycle_event", side_effect=events))
            with contextlib.ExitStack() as stack:
                for patch in patches: stack.enter_context(patch)
                if trace_signal: sys.settrace(tracer)
                try:
                    if event is None:
                        result = m.formal(root, cfg, "commit", controller)
                        exc = None
                    else:
                        with self.assertRaises((m.TerminationRequested, m.IntegrityError)) as cm:
                            m.formal(root, cfg, "commit", controller)
                        result = None; exc = cm.exception
                finally:
                    if trace_signal: sys.settrace(None)
            status = m.verify_bundle(root / "preview")
            report_path = root / "preview" / (root / "preview" / "CURRENT").read_text().strip() / "report.json"
            report = json.loads(report_path.read_text()) if report_path.is_file() else None
            current_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
            return {"status": status, "report": report, "exception": exc, "result": result,
                    "fired": fired["value"], "close_calls": sum(x.file.calls for x in files.values()),
                    "terminal_mask_retained": controller.terminal_mask_retained,
                    "term_int_blocked": set(controller.SIGNALS).issubset(set(current_mask)),
                    "controller_pending_rows": controller.pending_rows(),
                    "os_pending": set(signal.sigpending())}

    def test_53_signal_aware_terminal_commit_windows_pass_and_typed_block(self):
        pre_replace = ("terminal_commit_publish_entry", "terminal_commit_after_callback",
                       "terminal_commit_before_current_write", "terminal_current_before_replace")
        post_replace = ("terminal_current_after_replace", "terminal_commit_postreplace_check")
        for route_stop in (False, True):
            for event in pre_replace + post_replace:
                with self.subTest(route_stop=route_stop, event=event):
                    out = self._formal_terminal_commit_case(route_stop, event)
                    self.assertTrue(out["fired"]); self.assertEqual(out["close_calls"], 12)
                    events = out["exception"].pending_cleanup_signals
                    self.assertEqual([row["name"] for row in events], ["SIGTERM"])
                    if event in pre_replace:
                        self.assertEqual(out["status"]["status"], "FORMAL_RUNNING")
                    else:
                        self.assertEqual(out["status"]["status"], "LEAF_CLOSE_ONLY_FAILED")
                        self.assertFalse(out["status"]["semantic_success"])
                        self.assertTrue(out["report"]["commit_superseded"])
                        self.assertTrue(out["report"]["pass_pointer_was_temporarily_published"])
                        self.assertEqual([x["name"] for x in out["report"]["pending_cleanup_signals"]],
                                         ["SIGTERM"])
                        self.assertTrue(out["exception"].canonical_failure_published)

    def test_54_terminal_commit_without_signal_pass_and_typed_block(self):
        passed = self._formal_terminal_commit_case(False)
        blocked = self._formal_terminal_commit_case(True)
        self.assertEqual(passed["status"]["status"], "LEAF_CLOSE_ONLY_PASS")
        self.assertEqual(blocked["status"]["status"], "LEAF_CLOSE_ONLY_TYPED_BLOCK")
        self.assertTrue(passed["status"]["semantic_success"])
        self.assertTrue(blocked["status"]["semantic_success"])
        self.assertEqual(passed["close_calls"], 12); self.assertEqual(blocked["close_calls"], 12)
        self.assertTrue(passed["terminal_mask_retained"] and blocked["terminal_mask_retained"])
        self.assertTrue(passed["term_int_blocked"] and blocked["term_int_blocked"])

    def test_55_supersession_authority_failure_restores_formal_running(self):
        out = self._formal_terminal_commit_case(False, "terminal_current_after_replace", authority_failure=True)
        self.assertIsInstance(out["exception"], m.IntegrityError)
        self.assertEqual(out["status"]["status"], "FORMAL_RUNNING")
        self.assertEqual(out["close_calls"], 12)

    def test_56_sys_settrace_real_signal_all_terminal_commit_windows(self):
        windows = ("terminal_commit_publish_entry", "terminal_commit_after_callback",
                   "terminal_commit_before_current_write", "terminal_current_before_replace",
                   "terminal_current_after_replace", "terminal_commit_postreplace_check")
        for route_stop in (False, True):
            for event in windows:
                with self.subTest(route_stop=route_stop, event=event):
                    out = self._formal_terminal_commit_case(route_stop, event, trace_signal=True)
                    self.assertTrue(out["fired"]); self.assertEqual(out["close_calls"], 12)
                    self.assertNotIn(out["status"]["status"],
                                     {"LEAF_CLOSE_ONLY_PASS", "LEAF_CLOSE_ONLY_TYPED_BLOCK"})
                    self.assertEqual(len(out["exception"].pending_cleanup_signals), 1)

    def test_57_post_linearization_signals_remain_os_pending_to_normal_process_exit(self):
        runner = HERE / "close_only_probe.py"
        code = r'''
import importlib.util,json,os,signal,sys,tempfile
from pathlib import Path
path=Path(sys.argv[1]); seam=sys.argv[2]; status=sys.argv[3]
spec=importlib.util.spec_from_file_location("x",path); x=importlib.util.module_from_spec(spec); spec.loader.exec_module(x)
source=path.read_text().splitlines(); start=next(i for i,l in enumerate(source) if l.startswith("def publish("))
end=next(i for i,l in enumerate(source[start+1:],start+1) if l.startswith("def verify_bundle("))
if seam in {"return_final","return_result"}:
    token="return final" if seam=="return_final" else "return result"
    matches=[i+1 for i,l in enumerate(source[start:end],start) if l.strip()==token]
    target=max(matches)
else:
    needle='_lifecycle_event("%s")' % seam
    matches=[i+1 for i,l in enumerate(source) if needle in l]
    assert len(matches)==1, (seam,matches); target=matches[0]
fired=[False]
def tracer(frame,event,arg):
    if event=="line" and Path(frame.f_code.co_filename)==path and frame.f_lineno==target and not fired[0]:
        fired[0]=True; os.kill(os.getpid(),signal.SIGTERM)
    return tracer
with tempfile.TemporaryDirectory() as td:
    preview=Path(td); x.publish(preview,"old","FORMAL_RUNNING",False,{})
    controller=x.DeferredCleanupSignals().enter(); sys.settrace(tracer)
    try:
        x.publish(preview,"terminal",status,True,{"report.json":x.canonical_json({"status":status})},
                  termination_controller=controller,
                  termination_failure_builder=lambda events,changed: {})
    finally:
        sys.settrace(None)
    observed=x.verify_bundle(preview); mask=signal.pthread_sigmask(signal.SIG_BLOCK,[])
    assert fired[0] and observed["status"]==status
    assert controller.terminal_mask_retained and set(controller.SIGNALS).issubset(set(mask))
    assert controller.pending_rows()==[]
    assert signal.SIGTERM in signal.sigpending()
    print(json.dumps({"status":observed["status"],"blocked":True,"handler_rows":0,"os_pending":"SIGTERM"}),flush=True)
sys.exit(0)
'''
        seams = ("terminal_commit_linearized", "terminal_commit_mask_retained_to_process_exit", "return_final",
                 "terminal_commit_after_writer_mutex_exit", "terminal_publish_function_return", "return_result")
        for status in ("LEAF_CLOSE_ONLY_PASS", "LEAF_CLOSE_ONLY_TYPED_BLOCK"):
            for seam in seams:
                result = subprocess.run([sys.executable, "-c", code, str(runner), seam, status],
                                        text=True, capture_output=True, timeout=10)
                with self.subTest(status=status, seam=seam):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload, {"status": status, "blocked": True,
                                               "handler_rows": 0, "os_pending": "SIGTERM"})

    def test_58_production_terminal_mask_has_no_contextmanager_restore(self):
        source = (HERE / "close_only_probe.py").read_text()
        publish_source = source[source.index("def publish("):source.index("def verify_bundle(")]
        begin_source = source[source.index("def begin_terminal_commit("):source.index("def raise_if_pending(")]
        self.assertNotIn("with termination_controller.commit_mask", publish_source)
        self.assertNotIn("SIG_SETMASK", begin_source)
        self.assertIn("begin_terminal_commit()", publish_source)
        self.assertIn("terminal_commit_linearized", publish_source)


if __name__ == "__main__": unittest.main(verbosity=2)
