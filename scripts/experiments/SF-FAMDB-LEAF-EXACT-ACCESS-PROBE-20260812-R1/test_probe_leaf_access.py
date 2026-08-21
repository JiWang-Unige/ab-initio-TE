#!/usr/bin/env python3
import importlib.util
import contextlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("leaf_probe", HERE / "probe_leaf_access.py")
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


def exact_observations():
    out = []
    for target in CFG["selected_records"]:
        for part in CFG["source_contract"]["expected_partition_order"]:
            record = None
            if part == target["partition"]:
                record = dict(target)
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
        source = (HERE / "probe_leaf_access.py").read_text()
        self.assertNotIn("get_family_by_name", source)
        self.assertNotIn("startswith(target", source)
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
        with tempfile.TemporaryDirectory() as td, mock.patch.object(m, "probe_installed", side_effect=AssertionError), \
             mock.patch.object(m, "validate_source", side_effect=AssertionError):
            cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = td
            m.static_preview(ROOT, cfg, "static")
            self.assertEqual(m.verify_bundle(td)["status"], "IMPLEMENTED_NOT_RUN")

    def test_15_static_rejects_owner_and_formal_state(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = td
            (p / cfg["owner_lock_name"]).mkdir()
            with self.assertRaises(m.IntegrityError): m.static_preview(ROOT, cfg, "static")
            (p / cfg["owner_lock_name"]).rmdir(); m.publish(p, "f", "LEAF_EXACT_ACCESS_PASS", True, {})
            with self.assertRaises(m.IntegrityError): m.static_preview(ROOT, cfg, "late")

    def test_16_writer_mutex(self):
        with tempfile.TemporaryDirectory() as td:
            with m.writer_mutex(td):
                with self.assertRaises(m.IntegrityError): m.publish(td, "x", "IMPLEMENTED_NOT_RUN", False, {})

    def test_17_formal_slurm_precedes_h5(self):
        with mock.patch.dict(os.environ, slurm_env(), clear=True), \
             mock.patch.object(m, "query_slurm", side_effect=m.IntegrityError("bad Slurm")), \
             mock.patch.object(m, "probe_installed", side_effect=AssertionError):
            with self.assertRaisesRegex(m.IntegrityError, "bad Slurm"): m.formal(ROOT, CFG, "x")

    def test_18_sbatch_contract(self):
        text = (ROOT / "sbatch" / (m.EXP_ID + ".sbatch")).read_text()
        self.assertIn("#SBATCH --time=00:10:00", text); self.assertIn("#SBATCH --mem=4G", text)
        self.assertIn("#SBATCH --cpus-per-task=1", text); self.assertNotIn("#SBATCH --gres", text)
        self.assertLess(text.index("set -eo pipefail"), text.index("source /opt/ebsofts"))
        self.assertLess(text.index("conda activate te_benchmark"), text.index("set -u"))
        self.assertLess(text.index("pre_submit_gate.py"), text.index('python "${TEST_PATH}"'))

    def test_19_typed_block_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); m.publish(p, "x", "LEAF_EXACT_ACCESS_TYPED_BLOCK", True, {})
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
            self.assertEqual(m.verify_bundle(preview)["status"], "LEAF_EXACT_ACCESS_FAILED")
            m.atomic_write(preview / "CURRENT", old)
            with mock.patch.object(m, "revalidate_authority", side_effect=[None, m.IntegrityError("prepointer drift")]):
                self.assertFalse(m.publish_failure_if_owned(root, cfg, "other", m.IntegrityError("x"), env, initial))
            self.assertEqual(m.current_bytes(preview), old)

    def test_21_formal_scientific_probe_exactly_once_72_calls(self):
        initial = {"slurm": {"fields": {}, "command": []}, "owner_sha256": "o", "gate_sha256": "g",
                   "package_sha256": {"x": "h"}, "source": {"s": "h"}}
        metrics = {"route_stop": False, "probe_call_count": 72, "target_count": 6, "partition_count": 12,
                   "resolved_count": 6, "blocked_count": 0, "exact_once_across_partitions": True, "fallback_count": 0}
        probe = mock.Mock(return_value=(metrics, {"observations": [], "failures": []}, []))
        def fake_publish(_preview, _attempt, status, _semantic, _files, before_pointer=None, **_kwargs):
            if before_pointer and status != "FORMAL_RUNNING": before_pointer(Path("unused"))
            return Path("bundle")
        with mock.patch.dict(os.environ, slurm_env(), clear=True), \
             mock.patch.object(m, "prepare_authority", return_value=initial), \
             mock.patch.object(m, "writer_mutex", return_value=contextlib.nullcontext()), \
             mock.patch.object(m, "publish", side_effect=fake_publish), \
             mock.patch.object(m, "probe_installed", probe), \
             mock.patch.object(m, "validate_source", return_value=initial["source"]), \
             mock.patch.object(m, "package_hashes", return_value=initial["package_sha256"]), \
             mock.patch.object(m, "query_slurm", return_value=initial["slurm"]), \
             mock.patch.object(m, "revalidate_authority", return_value=None):
            m.formal(ROOT, CFG, "synthetic")
        probe.assert_called_once_with(ROOT, CFG)

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


if __name__ == "__main__": unittest.main(verbosity=2)
