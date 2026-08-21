#!/usr/bin/env python3
"""Static and behavioral contract tests; never launches Apptainer or HiTE."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONFIG = ROOT / "configs" / "BENCH-HITE-ISOLATED-20260811-R1.yaml"
RUNNER = HERE / "run_hite_isolated.py"
SBATCH = ROOT / "sbatch" / "BENCH-HITE-ISOLATED-20260811-R1.sbatch"

spec = importlib.util.spec_from_file_location("isolated_hite_runner", RUNNER)
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FakeBudget:
    pass


class CellHarness:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.calls: list[tuple[str, list[str], int]] = []

    def __call__(self, name, argv, directory, requested, budget):
        directory.mkdir(parents=True, exist_ok=True)
        stdout, stderr, timing = (directory / f"{name}.{suffix}" for suffix in ("out", "err", "time"))
        stdout.write_text("################ HiTE, version 3.3.3 ################\n" if name == "hite_help_identity" else "done\n")
        stderr.write_text("")
        timing.write_text("")
        self.calls.append((name, argv, requested))
        timed_out = self.mode == "timeout" and name == "hite_min"
        if name == "hite_min" and not timed_out:
            bind = argv[argv.index("--bind") + 1].split(":/work", 1)[0]
            gff = Path(bind) / "hite" / "HiTE.gff"
            if self.mode != "missing":
                gff.write_text("bad\n" if self.mode == "malformed" else
                               "##gff-version 3\nchr1\tHiTE\trepeat_region\t1\t20\t.\t+\t.\tID=h1;Name=h1\n")
        return {"name": name, "argv": argv, "exit_code": 124 if timed_out else 0,
                "timed_out": timed_out, "stdout": str(stdout), "stderr": str(stderr),
                "time": str(timing), "configured_timeout_seconds": requested,
                "effective_timeout_seconds": requested, "kill_after_seconds": 10}


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text())
        cls.adapter = runner.load_adapter(ROOT / cls.config["hite"]["adapter"]["path"])

    def _run(self, mode: str):
        harness = CellHarness(mode)
        with tempfile.TemporaryDirectory() as td:
            parent = {"pass": True, "parent_hite_timeout_evidence": {
                "configured_timeout_seconds": 600, "effective_timeout_seconds": 600,
                "exit_code": 124, "timed_out": True, "sha256": "parent"}}
            stop_path = Path(td) / "STOP.json"
            result = runner.run_hite_cell(self.config, {"pass": True}, parent, Path(td),
                                          FakeBudget(), stop_path, "12345", command_runner=harness,
                                          adapter_module=self.adapter)
            stop = json.loads(stop_path.read_text()) if stop_path.is_file() else None
            return result, harness.calls, stop

    def test_config_is_single_cell_exact_and_offline(self):
        c = self.config
        self.assertEqual(c["expected_cell_keys"], ["hite"])
        self.assertTrue(c["offline"])
        self.assertEqual(c["hite"]["version"], "3.3.3")
        self.assertEqual(c["hite"]["direct_argv"], ["python", "/HiTE/main.py", "--genome",
                         "/work/input/hite.fa", "--thread", "2", "--annotate", "1", "--out_dir", "/work/hite"])

    def test_identity_is_anchored_official_banner(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "help"
            command = {"exit_code": 0, "timed_out": False, "stdout": str(out)}
            out.write_text("dependency version 3.3.3\n")
            self.assertFalse(runner.strict_identity(command))
            out.write_text("################ HiTE, version 3.3.3 ################\n")
            self.assertTrue(runner.strict_identity(command))
            out.write_text("################ HiTE, version 3.3.4 ################\n")
            self.assertFalse(runner.strict_identity(command))

    def test_success_requires_exact_gff_and_adapter_rows(self):
        result, calls, stop = self._run("success")
        self.assertEqual(result["status"], "ENGINEERING_PASS")
        self.assertTrue(result["adapter"]["pass"])
        self.assertGreater(result["adapter"]["rows"], 0)
        self.assertEqual([x[0] for x in calls], ["hite_help_identity", "hite_min"])
        self.assertIsNone(stop)

    def test_timeout_is_invalid_and_adapter_not_attempted(self):
        result, calls, stop = self._run("timeout")
        self.assertEqual(result["status"], "INVALID_RUN")
        self.assertFalse(result["adapter"]["attempted"])
        self.assertEqual(calls[1][2], 1800)
        self.assertTrue(stop["stop_rule_triggered"])
        self.assertFalse(stop["further_retry_allowed"])
        self.assertEqual(stop["parent_timeout_evidence"]["configured_timeout_seconds"], 600)
        self.assertEqual(stop["current_timeout_evidence"]["configured_timeout_seconds"], 1800)
        self.assertTrue(result["stop_rule_triggered"])

    def test_missing_and_malformed_gff_are_invalid(self):
        for mode in ("missing", "malformed"):
            with self.subTest(mode=mode):
                result, _, _ = self._run(mode)
                self.assertEqual(result["status"], "INVALID_RUN")
                self.assertTrue(result["adapter"]["attempted"])
                self.assertFalse(result["adapter"]["pass"])

    def test_invalid_canonical_rows_are_rejected(self):
        class BadAdapter:
            @staticmethod
            def convert(source, output, fmt):
                output.write_text("\t".join(runner.FIELDS) + "\nchr1\t20\t10\tx\t.\t+\tHiTE\t.\n")
                return 1
        with tempfile.TemporaryDirectory() as td:
            gff = Path(td) / "HiTE.gff"
            gff.write_text("chr1\tHiTE\tx\t1\t2\t.\t+\t.\tID=x\n")
            evidence = runner.adapt_final_gff(BadAdapter(), gff, Path(td) / "canonical.tsv")
            self.assertFalse(evidence["pass"])

    def test_asset_and_parent_evidence_are_behaviorally_verified(self):
        assets_ok, assets = runner.verify_hite_assets(ROOT, self.config)
        parent_ok, parent = runner.verify_parent_rm_evidence(ROOT, self.config)
        self.assertTrue(assets_ok, assets)
        self.assertTrue(parent_ok, parent)
        self.assertTrue(parent["checks"]["pin_hite_cell_result"])
        self.assertTrue(parent["checks"]["parent_hite_timeout_600"])
        self.assertTrue(parent["checks"]["hite_result_artifact_mapping"])
        self.assertEqual(parent["parent_hite_timeout_evidence"]["sha256"],
                         self.config["parent_rm_evidence"]["hite_cell_result"]["sha256"])
        drifted = json.loads(json.dumps(self.config))
        drifted["parent_rm_evidence"]["rm_cell_result"]["sha256"] = "0" * 64
        ok, evidence = runner.verify_parent_rm_evidence(ROOT, drifted)
        self.assertFalse(ok)
        self.assertFalse(evidence["checks"]["pin_rm_cell_result"])
        drifted = json.loads(json.dumps(self.config))
        drifted["parent_rm_evidence"]["hite_cell_result"]["sha256"] = "f" * 64
        ok, evidence = runner.verify_parent_rm_evidence(ROOT, drifted)
        self.assertFalse(ok)
        self.assertFalse(evidence["checks"]["pin_hite_cell_result"])

    def test_only_hite_commands_can_be_executed(self):
        _, calls, _ = self._run("success")
        flattened = [token for _, argv, _ in calls for token in argv]
        self.assertEqual([name for name, _, _ in calls], ["hite_help_identity", "hite_min"])
        self.assertNotIn("bash", flattened)
        self.assertIn("--cleanenv", flattened)
        self.assertNotIn("RepeatMasker", flattened)
        self.assertNotIn("EDTA.pl", flattened)
        self.assertNotIn("EarlGrey", flattened)
        self.assertNotIn("TEtrimmer", flattened)
        self.assertNotIn("pfam_scan.pl", flattened)

    def test_runtime_budget_preserves_headroom_and_kill_after(self):
        c = self.config
        budget_spec = dict(c["runtime_budget"])
        budget_spec["kill_after_seconds"] = c["timeouts_seconds"]["kill_after"]
        budget = runner.RuntimeBudget(budget_spec, c["timeouts_seconds"])
        self.assertGreaterEqual(c["runtime_budget"]["required_post_command_headroom_seconds"], 600)
        self.assertLessEqual(budget.accounted_seconds, 3600)
        self.assertEqual(c["timeouts_seconds"]["minimum_input"], 1800)
        with tempfile.TemporaryDirectory() as td, mock.patch.object(subprocess, "run") as call:
            call.return_value.returncode = 0
            result = runner.bounded_command("probe", ["true"], Path(td), 1, budget)
            argv = call.call_args.args[0]
            self.assertIn("--kill-after=10", argv)
            self.assertEqual(result["kill_after_seconds"], 10)

    def test_lock_release_is_owner_only(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "lock"
            lock.write_text(json.dumps({"token": "owner"}))
            runner.release_lock(lock, "other")
            self.assertTrue(lock.exists())
            runner.release_lock(lock, "owner")
            self.assertFalse(lock.exists())

    def test_lock_tri_state_is_strict_and_fail_closed(self):
        def response(rc=0, stdout="", stderr=""):
            return subprocess.CompletedProcess([], rc, stdout, stderr)

        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "lock"
            lock.write_text("{broken")
            with self.assertRaises(RuntimeError):
                runner.acquire_lock(lock, "new", 10, "456", now_fn=lambda: 1000.0,
                                    squeue_runner=lambda *a, **k: response())
            self.assertEqual(lock.read_text(), "{broken")

        invalid_owners = [
            {"token": "x", "job_id": "abc", "created": 1.0},
            {"token": "x", "job_id": "123", "created": float("nan")},
            {"token": "x", "job_id": "123", "created": float("inf")},
            {"token": "x", "job_id": "123", "created": 1001.0},
        ]
        for owner in invalid_owners:
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as td:
                lock = Path(td) / "lock"
                lock.write_text(json.dumps(owner))
                with self.assertRaises(RuntimeError):
                    runner.acquire_lock(lock, "new", 10, "456", now_fn=lambda: 1000.0,
                                        squeue_runner=lambda *a, **k: response())
                self.assertEqual(json.loads(lock.read_text())["token"], "x")

        failures = [response(2), response(0, "", "warning"), response(0, "123\n123\n", ""),
                    response(0, "999\n", "")]
        for result in failures:
            with self.subTest(result=result), tempfile.TemporaryDirectory() as td:
                lock = Path(td) / "lock"
                lock.write_text(json.dumps({"token": "x", "job_id": "123", "created": 1.0}))
                with self.assertRaises(RuntimeError):
                    runner.acquire_lock(lock, "new", 10, "456", now_fn=lambda: 1000.0,
                                        squeue_runner=lambda *a, result=result, **k: result)
                self.assertEqual(json.loads(lock.read_text())["token"], "x")

        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "lock"
            lock.write_text(json.dumps({"token": "x", "job_id": "123", "created": 1.0}))
            with self.assertRaises(RuntimeError):
                runner.acquire_lock(lock, "new", 10, "456", now_fn=lambda: 1000.0,
                                    squeue_runner=lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("squeue")))
            self.assertEqual(json.loads(lock.read_text())["token"], "x")

        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "lock"
            lock.write_text(json.dumps({"token": "x", "job_id": "123", "created": 1.0}))
            with self.assertRaises(RuntimeError):
                runner.acquire_lock(lock, "new", 10, "456", now_fn=lambda: 1000.0,
                                    squeue_runner=lambda *a, **k: response(0, "123\n", ""))
            self.assertEqual(json.loads(lock.read_text())["token"], "x")

        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "lock"
            lock.write_text(json.dumps({"token": "x", "job_id": "123", "created": 995.0}))
            with self.assertRaises(RuntimeError):
                runner.acquire_lock(lock, "new", 10, "456", now_fn=lambda: 1000.0,
                                    squeue_runner=lambda *a, **k: response())

        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "lock"
            lock.write_text(json.dumps({"token": "old", "job_id": "123", "created": 1.0}))
            runner.acquire_lock(lock, "new", 10, "456", now_fn=lambda: 1000.0,
                                squeue_runner=lambda *a, **k: response())
            acquired = json.loads(lock.read_text())
            self.assertEqual((acquired["token"], acquired["job_id"]), ("new", "456"))
            self.assertEqual(len(list(Path(td).glob("lock.stale.*"))), 1)

    def test_stop_sentinel_rejects_before_assets_or_commands(self):
        with tempfile.TemporaryDirectory() as td:
            stop = Path(td) / "STOP.json"
            runner.atom(stop, {"exp_id": runner.EXP_ID, "stop_rule_triggered": True,
                               "further_retry_allowed": False})
            with mock.patch.object(runner, "verify_hite_assets") as assets, \
                    mock.patch.object(runner, "bounded_command") as command:
                with self.assertRaises(runner.StopRuleError):
                    runner.pre_asset_guards(stop, {"SLURM_JOB_ID": "12345"})
                assets.assert_not_called()
                command.assert_not_called()

    def test_future_main_attempt_rejects_stop_and_publishes_failure_without_commands(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root / "outputs" / runner.EXP_ID
            output.mkdir(parents=True)
            stop = output / "STOP.json"
            runner.atom(stop, {"schema_version": "TEFM-HITE-TIMEOUT-STOP-1.0.0",
                               "exp_id": runner.EXP_ID, "stop_rule_triggered": True,
                               "further_retry_allowed": False})
            config = root / "config.json"
            config.write_text(json.dumps({
                "exp_id": runner.EXP_ID, "expected_cell_keys": ["hite"],
                "primary_metric": "hite_engineering_pass", "ownership": {"stale_lock_seconds": 10},
                "stop_policy": {"sentinel": f"outputs/{runner.EXP_ID}/STOP.json"},
                "parent_rm_evidence": {"exp_id": "BENCH-RM-HITE-VALIDITY-20260811-R1",
                                       "slurm_job_id": "11523819"},
            }))
            missing_env = output / "unused-env.txt"
            environment = dict(os.environ)
            environment["SLURM_JOB_ID"] = "987654"
            proc = subprocess.run([sys.executable, str(RUNNER), "--root", str(root),
                                   "--config", str(config), "--environment-snapshot", str(missing_env)],
                                  env=environment, text=True, capture_output=True, check=False)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertEqual((output / "STATUS").read_text(), "FAILED\n")
            failure = json.loads((output / "failure.json").read_text())
            self.assertTrue(failure["stop_rule_rejection"])
            commands = json.loads((output / "command_manifest.json").read_text())
            self.assertEqual(commands["cell_commands"], {"hite": []})
            reconciliation = json.loads((output / "reconciliation.json").read_text())
            self.assertTrue(reconciliation["stop_rule_triggered"])
            self.assertFalse(reconciliation["further_retry_allowed"])
            latest = json.loads((output / "latest_attempt.json").read_text())
            inputs = json.loads((Path(latest["attempt"]) / "input_manifest.json").read_text())
            snapshot = inputs["environment"]["snapshot"]
            self.assertEqual(snapshot["sha256"], runner.sha(Path(snapshot["path"])))

    def test_non_slurm_is_rejected_before_container_construction(self):
        for environment in ({}, {"SLURM_JOB_ID": ""}, {"SLURM_JOB_ID": "local-1"},
                            {"SLURM_JOB_ID": "0"}, {"SLURM_JOB_ID": "1.5"}):
            with self.subTest(environment=environment), mock.patch.object(runner, "cexec_direct") as container:
                with self.assertRaises(RuntimeError):
                    runner.require_numeric_slurm_job_id(environment)
                container.assert_not_called()
        self.assertEqual(runner.require_numeric_slurm_job_id({"SLURM_JOB_ID": "12345"}), "12345")

    def test_running_transition_archives_old_terminal_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            (output / "STATUS").write_text("COMPLETED\n")
            (output / "metrics.json").write_text("old\n")
            archive = runner.begin_run(output, "12345")
            self.assertEqual((output / "STATUS").read_text(), "RUNNING\n")
            self.assertEqual((archive / "STATUS").read_text(), "COMPLETED\n")
            self.assertEqual((archive / "metrics.json").read_text(), "old\n")
            self.assertFalse((output / "metrics.json").exists())

    def test_metrics_primary_key_failure_bundle_and_environment_hash_closure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output, attempt = root / "output", root / "attempt"
            output.mkdir(); attempt.mkdir()
            (output / "STATUS").write_text("RUNNING\n")
            environment_path = root / "env.txt"
            environment_path.write_text("environment\n")
            environment = runner.runtime_environment_evidence(environment_path)
            input_manifest = attempt / "input_manifest.json"
            runner.atom(input_manifest, {"environment": {"snapshot": environment}})
            runner.atom(attempt / "runtime_budget.json", {"commands_started": 0})
            cell = {"cell_key": "hite", "status": "INVALID_RUN", "commands": [],
                    "identity": {"satisfied": False}, "adapter": {"attempted": False, "pass": False},
                    "blockers": ["test failure"]}
            failure = {"exception_type": "TestFailure", "message": "bounded"}
            rc = runner.finalize_attempt(output, attempt, input_manifest, cell, self.config,
                                         environment, False, False, failure=failure)
            self.assertEqual(rc, 2)
            self.assertEqual((output / "STATUS").read_text(), "FAILED\n")
            metrics = json.loads((output / "metrics.json").read_text())
            self.assertEqual(metrics["primary_metric"], "hite_engineering_pass")
            self.assertEqual(metrics["hite_engineering_pass"], 0)
            self.assertFalse(metrics["semantic_success"])
            self.assertTrue((output / "failure.json").is_file())
            canonical = json.loads((output / "canonical_manifest.json").read_text())
            self.assertTrue(runner.canonical_bundle_closed(canonical))
            self.assertEqual(canonical["runtime_environment"]["sha256"], runner.sha(environment_path))
            self.assertEqual(runner.sha(Path(canonical["runtime_environment"]["staged_path"])),
                             runner.sha(Path(canonical["runtime_environment"]["canonical_path"])))
            self.assertEqual(set(canonical["required_payload_names"]),
                             {"metrics.json", "semantic_success.json", "command_manifest.json",
                              "reconciliation.json", "latest_attempt.json", "failure.json"})

    def test_artifact_manifest_closure_detects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x"
            path.write_text("v1")
            manifest = {"expected_paths": [str(path)],
                        "artifacts": [{"path": str(path), "sha256": runner.sha(path)}],
                        "exact_row_count": 1}
            self.assertTrue(runner.artifact_manifest_closed(manifest))
            path.write_text("v2")
            self.assertFalse(runner.artifact_manifest_closed(manifest))
            manifest["artifacts"] = []
            self.assertFalse(runner.artifact_manifest_closed(manifest))

    def test_sbatch_any_cwd_and_pre_submit_gate(self):
        text = SBATCH.read_text()
        self.assertIn('cd "$PROJECT_ROOT"', text)
        self.assertIn('scripts/pre_submit_gate.py --exp-id "$EXP_ID" "$PROJECT_ROOT"', text)
        self.assertIn("#SBATCH --time=01:00:00", text)
        self.assertIn("#SBATCH --cpus-per-task=4", text)
        self.assertIn("#SBATCH --mem=48G", text)
        self.assertNotIn("--gres", text)
        self.assertIn('ENV_SNAPSHOT_TMP="$ENV_SNAPSHOT.tmp.$$"', text)
        self.assertIn('conda list --explicit > "$ENV_SNAPSHOT_TMP" || environment_failure', text)
        self.assertIn('mv "$ENV_SNAPSHOT_TMP" "$ENV_SNAPSHOT" || environment_failure', text)
        self.assertIn('--environment-snapshot "$ENV_SNAPSHOT"', text)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "outputs" / runner.EXP_ID).mkdir(parents=True)
            review = root / "outputs" / runner.EXP_ID / "code_review_gate.json"
            reviewed = root / "runner.py"
            reviewed.write_text("v1\n")
            base = {"exp_id": runner.EXP_ID, "profile": "smoke", "reviewer_backend": "test",
                    "independence": "separate_test", "blockers_open": 0, "timestamp": "test",
                    "reviewed_files": {"runner.py": runner.sha(reviewed)}}
            gate = ROOT / "scripts" / "pre_submit_gate.py"
            def run_gate():
                return subprocess.run([sys.executable, str(gate), "--exp-id", runner.EXP_ID,
                                       str(root), "--format", "json"], cwd="/", text=True,
                                      capture_output=True, check=False)
            review.write_text(json.dumps({**base, "verdict": "BLOCKED", "blockers_open": 1}))
            self.assertEqual(run_gate().returncode, 3)
            review.write_text(json.dumps({**base, "verdict": "PASS"}))
            self.assertEqual(run_gate().returncode, 0)
            reviewed.write_text("v2\n")
            stale = run_gate()
            self.assertEqual(stale.returncode, 3)
            self.assertIn("过期", stale.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
