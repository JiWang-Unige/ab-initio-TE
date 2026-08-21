#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("preflight", HERE / "run_preflight.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ROOT = HERE.parents[2]
CFG = m.load_config(ROOT / "configs" / (m.EXP_ID + ".yaml"))


def hit(q, rid, cls, start=1):
    return {"score": 100, "div": "0.0", "del": "0.0", "ins": "0.0", "query_id": q,
            "query_start": start, "query_end": start + 9, "query_left": "(0)", "strand": "+",
            "repeat_id": rid, "raw_class": cls, "repeat_begin": "1", "repeat_end": "10",
            "repeat_left": "(0)", "rm_hit_id": "1", "overlap_flag": ""}


def fixtures():
    rows = []
    for r in CFG["selected_records"]:
        seq = "A" * r["consensus_length"]
        rows.append(dict(r, consensus=seq, consensus_sha256=m.sha256_bytes(seq.encode())))
    _, _, _, manifest = m.build_fastas(rows)
    c = [hit(x["query_id"], x["control_repeat_id"], x["raw_class"]) for x in manifest]
    a = [hit(x["query_id"], x["candidate_repeat_id"], x["raw_class"]) for x in manifest]
    return rows, manifest, c, a


def slurm_env(job="17"):
    return {"SLURM_JOB_ID": job, "SLURM_CPUS_PER_TASK": "1", "SLURM_MEM_PER_NODE": "4G",
            "SLURM_JOB_PARTITION": "private-teodoro-gpu"}


def scontrol_line(job="17"):
    c = CFG["slurm_authority_contract"]
    return ("JobId=%s JobState=RUNNING Partition=%s TimeLimit=%s NumCPUs=%s "
            "ReqTRES=%s AllocTRES=%s Command=%s SubmitLine=%s WorkDir=%s\n") % \
           (job, c["partition"], c["time_limit"], c["num_cpus"], c["req_tres"], c["alloc_tres"],
            c["command"], c["submit_line"], c["work_dir"])


class Tests(unittest.TestCase):
    def test_01_selected_contract(self):
        m.validate_selected(CFG)

    def test_02_assets_small_hashes(self):
        m.validate_assets(ROOT, CFG, include_large_stat=False)

    def test_03_family_drift_fail(self):
        obs = [dict(r, consensus="A") for r in CFG["selected_records"]]
        obs[0]["consensus_sha256"] = "0" * 64
        with self.assertRaises(m.IntegrityError): m.verify_family_rows(CFG, obs)

    def test_04_fastas_headers_and_same_sequence(self):
        rows, manifest, _, _ = fixtures(); q, c, a, _ = m.build_fastas(rows)
        self.assertIn(">AluY#SINE/Alu", c); self.assertIn(">DF000000002.4#SINE/Alu", a)
        self.assertIn(">DR002419729#RC/Helitron", c); self.assertEqual(q.count(">probe_"), 6)
        self.assertEqual(len(manifest), 6)
        self.assertEqual({x["partition"] for x in manifest}, {"dfam39_full.3.h5", "dfam39_full.7.h5"})
        self.assertEqual(manifest[-1]["provenance_tier"], "DR_UNCURATED")

    def test_05_duplicate_header_fail(self):
        rows, _, _, _ = fixtures(); rows[1]["canonical_name"] = rows[0]["canonical_name"]
        with self.assertRaises(m.IntegrityError): m.build_fastas(rows)

    def test_05b_export_pair_rejects_sequence_or_class_drift(self):
        rows, _, _, _ = fixtures(); _, c, a, manifest = m.build_fastas(rows)
        with self.assertRaises(m.IntegrityError): m.verify_export_pair(c, a.replace("A", "C", 1), manifest)
        with self.assertRaises(m.IntegrityError): m.verify_export_pair(c, a.replace("#SINE/Alu", "#LINE/L1", 1), manifest)

    def test_06_parse_out(self):
        text = "  100 0.0 0.0 0.0 probe_01 1 10 (0) C DF000000002.4 SINE/Alu (0) 10 1 7 *\n"
        row = m.parse_repeatmasker_out(text)[0]
        self.assertEqual((row["strand"], row["repeat_id"], row["raw_class"]), ("C", "DF000000002.4", "SINE/Alu"))
        self.assertEqual(row["overlap_flag"], "*")

    def test_07_empty_out_fail(self):
        self.assertEqual(m.parse_repeatmasker_out("SW perc perc query\nscore divergence deletion insertion\n"), [])
        with self.assertRaises(m.IntegrityError): m.parse_repeatmasker_out("")
        with self.assertRaises(m.IntegrityError): m.parse_repeatmasker_out("100 0.0 bad\n")

    def test_08_geometry_and_join_pass(self):
        _, manifest, c, a = fixtures()
        labeler = lambda x: ("P", {"SINE": 1, "LINE": 2, "LTR": 3, "DNA": 4, "RC": 5}[x.split('/')[0]])
        metrics, _ = m.evaluate_pair(c, a, manifest, labeler)
        self.assertTrue(metrics["geometry_semantic_hash_equal"])

    def test_09_missing_join_valid_negative(self):
        _, manifest, c, a = fixtures(); a[0]["repeat_id"] = "WRONG"
        with self.assertRaises(m.ValidNegative): m.evaluate_pair(c, a, manifest, lambda x: ("P", manifest[0]["expected_label"]))

    def test_09b_multiple_fragments_same_accession_not_ambiguous(self):
        _, manifest, c, a = fixtures(); c.append(dict(c[0], query_start=20, query_end=29)); a.append(dict(a[0], query_start=20, query_end=29))
        mapping = {x["raw_class"]: x["expected_label"] for x in manifest}
        metrics, _ = m.evaluate_pair(c, a, manifest, lambda raw: ("P", mapping[raw]))
        self.assertEqual(metrics["ambiguous_join_count"], 0)

    def test_10_geometry_mismatch_valid_negative(self):
        _, manifest, c, a = fixtures(); a[0]["query_start"] = 2
        mapping = {x["raw_class"]: x["expected_label"] for x in manifest}
        with self.assertRaises(m.ValidNegative): m.evaluate_pair(c, a, manifest, lambda x: ("P", mapping[x]))

    def test_11_raw_class_is_only_label_input(self):
        _, manifest, c, a = fixtures(); seen = []
        def labeler(raw): seen.append(raw); return "P", {x["raw_class"]: x["expected_label"] for x in manifest}[raw]
        m.evaluate_pair(c, a, manifest, labeler)
        self.assertEqual(set(seen), {x["raw_class"] for x in manifest})

    def test_12_raw_class_mismatch_valid_negative(self):
        _, manifest, c, a = fixtures(); a[0]["raw_class"] = "LINE/L1"
        mapping = {x["raw_class"]: x["expected_label"] for x in manifest}
        with self.assertRaises(m.ValidNegative): m.evaluate_pair(c, a, manifest, lambda x: ("P", mapping.get(x, -1)))

    def test_13_resource_guard(self):
        base = slurm_env("7")
        m.validate_formal_resources(base)
        missing_time = dict(base); missing_time.pop("SLURM_TIMELIMIT", None)
        m.validate_formal_resources(missing_time)
        for key, value in (("SLURM_JOB_ID", "x"), ("SLURM_CPUS_PER_TASK", "2"), ("SLURM_MEM_PER_NODE", "4097M"),
                           ("SLURM_JOB_PARTITION", "debug-cpu"), ("SLURM_GPUS", "1")):
            bad = dict(base, **{key: value})
            with self.assertRaises(m.IntegrityError): m.validate_formal_resources(bad)

    def test_13a_scontrol_authority_exact_and_bounded_command(self):
        calls = []
        def execute(cmd, timeout): calls.append((cmd, timeout)); return 0, scontrol_line(), ""
        audit = m.query_slurm_authority(ROOT, CFG, slurm_env(), executor=execute)
        self.assertEqual(audit["fields"]["TimeLimit"], "00:20:00")
        self.assertEqual(calls[0][0][:4], ["/usr/bin/timeout", "--signal=TERM", "--kill-after=2s", "10s"])
        self.assertEqual(calls[0][0][-5:], ["/usr/bin/scontrol", "show", "job", "17", "-o"])
        self.assertEqual(calls[0][1], 15)

    def test_13aa_scontrol_unknown_stderr_malformed_and_override_fail(self):
        for result in ((1, "", "Invalid job id specified"), (0, scontrol_line(), "warning"),
                       (0, "JobId=17 Partition=private-teodoro-gpu\n", ""),
                       (0, scontrol_line() + "\n", "")):
            with self.subTest(result=result):
                with self.assertRaises(m.IntegrityError):
                    m.query_slurm_authority(ROOT, CFG, slurm_env(), executor=lambda *_args, r=result: r)
        mutations = [
            ("TimeLimit=00:20:00", "TimeLimit=00:19:59"),
            ("TimeLimit=00:20:00", "TimeLimit=00:20:01"),
            ("JobId=17", "JobId=18"),
            ("Partition=private-teodoro-gpu", "Partition=debug-cpu"),
            ("NumCPUs=1", "NumCPUs=2"),
            ("ReqTRES=cpu=1,mem=4G,node=1,billing=2", "ReqTRES=cpu=2,mem=4G,node=1,billing=2"),
            ("AllocTRES=cpu=1,mem=4G,node=1,billing=2", "AllocTRES=cpu=1,mem=4G,node=1,billing=2,gres/gpu=1"),
            ("SubmitLine=sbatch sbatch/", "SubmitLine=sbatch --time=00:30:00 sbatch/"),
            ("Command=" + CFG["slurm_authority_contract"]["command"], "Command=/tmp/other.sbatch"),
        ]
        for old, new in mutations:
            line = scontrol_line().replace(old, new)
            with self.subTest(new=new), self.assertRaises(m.IntegrityError):
                m.query_slurm_authority(ROOT, CFG, slurm_env(), executor=lambda *_args, x=line: (0, x, ""))

    def test_13ab_precommand_and_prepointer_requery_detect_drift(self):
        before = {"fields": {"TimeLimit": "00:20:00"}, "command": ["q"],
                  "scontrol_sha256": "s", "sbatch_sha256": "b", "stdout_sha256": "old"}
        telemetry_only = dict(before, stdout_sha256="new")
        with mock.patch.object(m, "query_slurm_authority", return_value=telemetry_only):
            self.assertEqual(m.requery_same_slurm_authority(ROOT, CFG, slurm_env(), before,
                                                            "RepeatMasker command"), telemetry_only)
        changed = json.loads(json.dumps(before)); changed["fields"]["TimeLimit"] = "00:30:00"
        with mock.patch.object(m, "query_slurm_authority", return_value=changed):
            with self.assertRaisesRegex(m.IntegrityError, "terminal pointer"):
                m.requery_same_slurm_authority(ROOT, CFG, slurm_env(), before, "terminal pointer")

    def test_13b_sbatch_route_activation_lock_and_signal_guards(self):
        text = (ROOT / "sbatch" / (m.EXP_ID + ".sbatch")).read_text()
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertNotIn("#SBATCH --gres", text)
        self.assertLess(text.index("set -eo pipefail"), text.index("source /opt/ebsofts"))
        self.assertLess(text.index("conda activate te_benchmark"), text.index("set -u"))
        self.assertIn("trap 'exit 143' TERM", text); self.assertIn("OWNS_LOCK=1", text)
        self.assertIn('STATE_LOCK="${PROJECT_ROOT}/outputs/${EXP_ID}/preview/.state-writer.lock"', text)
        self.assertIn("flock -n 9", text)
        self.assertLess(text.index("scripts/pre_submit_gate.py"), text.index('python "${TEST_PATH}"'))

    def test_14_rm_nonzero_fail(self):
        execution = CFG["execution_contract"]
        with tempfile.TemporaryDirectory() as td, mock.patch.object(m, "run_bounded_command", return_value=(124, "", "timeout")) as bounded:
            with self.assertRaises(m.IntegrityError):
                m.run_rm("rm", [], Path(td)/"l", Path(td)/"p", Path(td)/"o", execution)
            cmd = bounded.call_args.args[0]
            self.assertEqual(cmd[:4], ["/usr/bin/timeout", "--signal=TERM", "--kill-after=15s", "300s"])
            self.assertEqual(bounded.call_args.args[1], 330)

    def test_14b_outer_timeout_kills_and_waits(self):
        proc = mock.Mock(pid=123, returncode=None)
        proc.communicate.side_effect = [subprocess.TimeoutExpired(["x"], 1), ("", "")]
        with mock.patch.object(m.subprocess, "Popen", return_value=proc), mock.patch.object(m.os, "killpg") as kill:
            with self.assertRaises(m.IntegrityError): m.run_bounded_command(["x"], 1)
        kill.assert_called_once_with(123, m.signal.SIGKILL)
        self.assertEqual(proc.communicate.call_count, 2)

    def test_15_bundle_exact_set_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); m.publish_bundle(p, "a", {"metrics.json": "{}\n"}, "IMPLEMENTED_NOT_RUN", False)
            self.assertEqual(m.verify_bundle(p)["status"], "IMPLEMENTED_NOT_RUN")
            bundle = p / p.joinpath("CURRENT").read_text().strip(); (bundle / "extra").write_text("x")
            with self.assertRaises(m.IntegrityError): m.verify_bundle(p)

    def test_16_atomic_pointer_interruption_preserves_old(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); m.publish_bundle(p, "a", {}, "IMPLEMENTED_NOT_RUN", False); old = (p/"CURRENT").read_text()
            def boom(_): raise RuntimeError("interrupt")
            with self.assertRaises(RuntimeError): m.publish_bundle(p, "b", {}, "PREFLIGHT_PASS", True, boom)
            self.assertEqual((p/"CURRENT").read_text(), old); m.verify_bundle(p)

    def test_16b_static_cannot_supersede_formal_pass(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); m.publish_bundle(p, "formal", {}, "PREFLIGHT_PASS", True); old = (p / "CURRENT").read_text()
            cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = td
            with self.assertRaises(m.IntegrityError): m.static_preview(ROOT, cfg, "late-static")
            self.assertEqual((p / "CURRENT").read_text(), old)

    def test_16c_ownerless_and_nonowner_failure_never_change_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = "preview"
            preview = root / "preview"; m.publish_bundle(preview, "old", {}, "PREFLIGHT_PASS", True)
            old = (preview / "CURRENT").read_text(); exc = m.IntegrityError("failure")
            self.assertFalse(m.publish_canonical_failure_if_owned(root, cfg, "new", exc,
                                                                  {"SLURM_JOB_ID": "17"}, "missing"))
            self.assertEqual((preview / "CURRENT").read_text(), old)
            lock = preview / cfg["owner_lock_name"]; lock.mkdir(); (lock / "job_id").write_text("18\n")
            self.assertFalse(m.publish_canonical_failure_if_owned(root, cfg, "new", exc,
                                                                  {"SLURM_JOB_ID": "17"}, "wrong-owner"))
            self.assertEqual((preview / "CURRENT").read_text(), old)
            m.write_attempt_local_failure(root, cfg, "new", exc)
            self.assertTrue((preview / "attempt_failures" / "new.json").is_file())

    def test_16d_wrapper_ownerless_is_attempt_local_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["project_root"] = str(root)
            cfg["preview_root"] = "outputs/%s/preview" % m.EXP_ID
            cp = root / "config.json"; cp.write_text(json.dumps(cfg))
            env = slurm_env()
            with mock.patch.dict(os.environ, env, clear=True), \
                 mock.patch.object(m, "query_slurm_authority", return_value={"fields": {}}):
                rc = m.main(["--config", str(cp), "--attempt-id", "wrapper", "--record-wrapper-failure"])
            preview = root / cfg["preview_root"]
            self.assertEqual(rc, 2); self.assertFalse((preview / "CURRENT").exists())
            self.assertTrue((preview / "attempt_failures" / "wrapper.json").is_file())

    def test_16e_writer_mutex_blocks_concurrent_pointer_writer(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with m.state_writer_mutex(p):
                with self.assertRaises(m.IntegrityError):
                    m.publish_bundle(p, "concurrent", {}, "PREFLIGHT_PASS", True)

    def test_16f_static_cas_rejects_injected_formal_pointer(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            m.publish_bundle(p, "old", {}, "IMPLEMENTED_NOT_RUN", False); old = m.current_bytes(p)
            m.publish_bundle(p, "formal", {}, "PREFLIGHT_PASS", True); formal = m.current_bytes(p)
            m.atomic_write(p / "CURRENT", old)
            with m.state_writer_mutex(p):
                initial = m.current_bytes(p)
                def inject(_): m.atomic_write(p / "CURRENT", formal)
                with self.assertRaises(m.IntegrityError):
                    m.publish_bundle(p, "late-static", {}, "IMPLEMENTED_NOT_RUN", False,
                                     before_pointer=inject, mutex_held=True, expected_current=initial)
            self.assertEqual(m.current_bytes(p), formal)
            self.assertEqual(m.verify_bundle(p)["status"], "PREFLIGHT_PASS")

    def test_16g_static_rejects_formal_owner_even_without_current(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = td
            (p / cfg["owner_lock_name"]).mkdir()
            with self.assertRaises(m.IntegrityError): m.static_preview(ROOT, cfg, "static")
            self.assertFalse((p / "CURRENT").exists())
            (p / cfg["owner_lock_name"]).rmdir(); (p / cfg["owner_lock_name"]).symlink_to("missing")
            with self.assertRaises(m.IntegrityError): m.static_preview(ROOT, cfg, "static-symlink")

    def test_17_static_never_reads_h5_or_runs_rm(self):
        with mock.patch.object(m, "read_selected_families", side_effect=AssertionError), mock.patch.object(m, "run_rm", side_effect=AssertionError):
            with tempfile.TemporaryDirectory() as td:
                cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = td
                m.static_preview(ROOT, cfg, "test")

    def test_18_formal_guard_precedes_source(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(m, "read_selected_families", side_effect=AssertionError):
            with self.assertRaises(m.IntegrityError): m.formal(ROOT, CFG, "x")

    def test_18b_code_review_hash_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = json.loads(json.dumps(CFG))
            cfg["code_review_gate_path"] = "outputs/%s/code_review_gate.json" % m.EXP_ID
            paths = ["configs/%s.yaml" % m.EXP_ID,
                     "scripts/experiments/%s/run_preflight.py" % m.EXP_ID,
                     "scripts/experiments/%s/test_preflight.py" % m.EXP_ID,
                     "sbatch/%s.sbatch" % m.EXP_ID, "docs/experiments/%s.md" % m.EXP_ID]
            reviewed = {}
            for rel in paths:
                p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(rel)
                reviewed[rel] = m.sha256_file(p)
            gate = root / cfg["code_review_gate_path"]; gate.parent.mkdir(parents=True)
            gate.write_text(json.dumps({"exp_id": m.EXP_ID, "verdict": "PASS_WITH_WARNINGS",
                                        "blockers_open": 0, "profile": "smoke", "reviewed_files": reviewed}))
            m.validate_code_review_gate(root, cfg)
            check = subprocess.run([sys.executable, str(ROOT / "scripts/pre_submit_gate.py"),
                                    "--exp-id", m.EXP_ID, str(root)], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            (root / paths[0]).write_text("tamper")
            with self.assertRaises(m.IntegrityError): m.validate_code_review_gate(root, cfg)

    def test_18c_owner_lock_exact_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["preview_root"] = "preview"
            lock = root / "preview" / cfg["owner_lock_name"]; lock.mkdir(parents=True); (lock / "job_id").write_text("17\n")
            m.validate_owner_lock(root, cfg, {"SLURM_JOB_ID": "17"})
            (lock / "extra").write_text("x")
            with self.assertRaises(m.IntegrityError): m.validate_owner_lock(root, cfg, {"SLURM_JOB_ID": "17"})

    def test_18d_valid_negative_payload_closes_rm_and_source_artifacts(self):
        metrics = {"acceptance_pass": False}; source = {"pin": "x"}; export = {"records": []}
        files = m.build_formal_payload(CFG, "PREFLIGHT_VALID_NEGATIVE", metrics, [], "probe", "control", "candidate",
                                       "control-out", "candidate-out", {"control": [], "candidate": []}, export,
                                       source, source, {"code": "hash"}, "g" * 64, "l" * 64,
                                       {"python": "x", "slurm_job_id": "1"}, {"initial": {}})
        for name in ("control.repeatmasker.out", "candidate.repeatmasker.out", "SOURCE_MANIFEST.json",
                     "selected_family_manifest.json", "hit_provenance.json", "commands.json", "SLURM_AUTHORITY.json"):
            self.assertIn(name, files)
        self.assertTrue(json.loads(files["metrics.json"])["semantic_success"])

    def test_18e_prepointer_revalidation_rejects_any_drift(self):
        slurm = {"fields": {}, "command": [], "scontrol_sha256": "s", "sbatch_sha256": "b"}
        args = (ROOT, CFG, {"SLURM_JOB_ID": "1"}, {"p": "h"}, "g", {"s": "h"}, "l", [{"r": 1}], slurm)
        patches = [mock.patch.object(m, "validate_owner_lock", return_value="l"),
                   mock.patch.object(m, "validate_code_review_gate"),
                   mock.patch.object(m, "sha256_file", return_value="g"),
                   mock.patch.object(m, "package_hashes", return_value={"p": "h"}),
                   mock.patch.object(m, "validate_assets", return_value={"s": "h"}),
                   mock.patch.object(m, "read_selected_families", return_value=[{"r": 1}]),
                   mock.patch.object(m, "query_slurm_authority", return_value=slurm)]
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            m.revalidate_before_pointer(*args)
        with mock.patch.object(m, "validate_owner_lock", return_value="changed"):
            with self.assertRaises(m.IntegrityError): m.revalidate_before_pointer(*args)
        common = [mock.patch.object(m, "validate_owner_lock", return_value="l"),
                  mock.patch.object(m, "validate_code_review_gate"), mock.patch.object(m, "sha256_file", return_value="g")]
        with common[0], common[1], common[2], mock.patch.object(m, "package_hashes", return_value={"p": "changed"}):
            with self.assertRaises(m.IntegrityError): m.revalidate_before_pointer(*args)
        with common[0], common[1], common[2], mock.patch.object(m, "package_hashes", return_value={"p": "h"}), \
             mock.patch.object(m, "validate_assets", return_value={"s": "changed"}):
            with self.assertRaises(m.IntegrityError): m.revalidate_before_pointer(*args)
        with common[0], common[1], common[2], mock.patch.object(m, "package_hashes", return_value={"p": "h"}), \
             mock.patch.object(m, "validate_assets", return_value={"s": "h"}), \
             mock.patch.object(m, "read_selected_families", return_value=[]), \
             mock.patch.object(m, "query_slurm_authority", return_value=slurm):
            with self.assertRaises(m.IntegrityError): m.revalidate_before_pointer(*args)

    def test_18f_slurm_authority_precedes_any_h5_or_rm(self):
        with mock.patch.dict(os.environ, slurm_env(), clear=True), \
             mock.patch.object(m, "query_slurm_authority", side_effect=m.IntegrityError("bad allocation")), \
             mock.patch.object(m, "read_selected_families", side_effect=AssertionError("H5 must not open")), \
             mock.patch.object(m, "run_rm", side_effect=AssertionError("RM must not run")):
            with self.assertRaisesRegex(m.IntegrityError, "bad allocation"):
                m.formal(ROOT, CFG, "bad-slurm")

    def test_19_label_name_permutation_invariant(self):
        _, manifest, c, a = fixtures(); mapping = {x["raw_class"]: x["expected_label"] for x in manifest}
        x = m.evaluate_pair(c, a, manifest, lambda raw: ("P", mapping[raw]))[0]
        for row, hit in zip(manifest, c):
            row["control_repeat_id"] = hit["repeat_id"] = "renamed_" + row["query_id"]
        for row, hit in zip(manifest, a):
            row["candidate_repeat_id"] = hit["repeat_id"] = "DF999" + row["query_id"]
        y = m.evaluate_pair(c, a, manifest, lambda raw: ("P", mapping[raw]))[0]
        self.assertEqual(x["candidate_direct_label_payload_sha256"], y["candidate_direct_label_payload_sha256"])


if __name__ == "__main__": unittest.main(verbosity=2)
