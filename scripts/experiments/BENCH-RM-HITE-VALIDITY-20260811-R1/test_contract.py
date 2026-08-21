#!/usr/bin/env python3
"""Static and behavioral contract tests; never launches containers."""
from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "BENCH-RM-HITE-VALIDITY-20260811-R1.yaml"
SPEC = importlib.util.spec_from_file_location("rm_hite_validity", HERE / "run_validity_smoke.py")
assert SPEC and SPEC.loader
validity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validity)


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.parent, cls.parent_config, cls.parent_hashes = validity.verify_parent_contract(ROOT, cls.config)

    def test_namespace_is_exactly_two_and_handlers_cannot_expand_it(self) -> None:
        expected = ["repeatmodeler2_repeatmasker", "hite"]
        calls: list[str] = []
        cells = validity.execute_selected_cells(expected, {
            "repeatmodeler2_repeatmasker": lambda: calls.append("repeatmodeler2_repeatmasker") or {"status": "ENGINEERING_PASS"},
            "hite": lambda: calls.append("hite") or {"status": "ENGINEERING_PASS"},
        })
        self.assertEqual(calls, expected)
        self.assertEqual(list(cells), expected)
        with self.assertRaisesRegex(ValueError, "handler namespace"):
            validity.execute_selected_cells(expected, {
                "repeatmodeler2_repeatmasker": lambda: {}, "hite": lambda: {}, "extra": lambda: {},
            })
        with self.assertRaisesRegex(ValueError, "expected_cell_keys"):
            validity.execute_selected_cells(["repeatmodeler2_repeatmasker"], {
                "repeatmodeler2_repeatmasker": lambda: {}, "hite": lambda: {},
            })

    def test_executable_command_ast_contains_only_the_two_cell_contract(self) -> None:
        tree = ast.parse((HERE / "run_validity_smoke.py").read_text(encoding="utf-8"))
        command_names: set[str] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "bounded_command" and node.args
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
            ):
                command_names.add(node.args[0].value)
        self.assertEqual(command_names, {
            "famdb_info", "famdb_family", "rm2_version", "rm2_famdb", "rm2_min", "rm_min",
            "hite_help_identity", "hite_min",
        })
        self.assertFalse(any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "command"
            for node in ast.walk(tree)
        ))

    def test_config_is_offline_parent_pinned_and_cpu_bounded(self) -> None:
        self.assertTrue(self.config["offline"])
        self.assertEqual(self.config["expected_cell_keys"], list(validity.ALLOWED_CELL_KEYS))
        self.assertEqual(self.config["resources"], {
            "partition": "private-teodoro-gpu", "cpus": 4, "memory_gb": 48,
            "walltime": "01:00:00", "gpus": 0,
        })
        self.assertEqual({row["role"] for row in self.parent_hashes}, {
            "config", "runner", "adapter", "hite_preparation_code", "famdb_preparation_code",
        })
        self.assertEqual(self.parent_config["exp_id"], self.config["parent_contract"]["exp_id"])
        self.assertEqual(set(self.config["asset_pins"]), {
            "famdb_manifest", "hite_sif", "hite_manifest", "rm_license", "hite_license",
        })

    def test_metrics_require_exact_keys_and_two_engineering_passes_for_repair(self) -> None:
        expected = list(validity.ALLOWED_CELL_KEYS)
        passed = {
            key: {"status": "ENGINEERING_PASS", "identity": {"satisfied": True}}
            for key in expected
        }
        metrics, semantic = validity.build_metrics("x", expected, passed, Path("attempt"))
        self.assertTrue(semantic["semantic_success"])
        self.assertTrue(semantic["repair_goal_success"])
        self.assertEqual(metrics["primary_metric"], "engineering_pass_count")
        self.assertEqual(metrics["engineering_pass_count"], 2)
        self.assertEqual(validity.semantic_exit_code(semantic), 0)

        version = dict(passed)
        version["hite"] = {"status": "VERSION_MISMATCH", "identity": {"satisfied": False}}
        metrics, semantic = validity.build_metrics("x", expected, version, Path("attempt"))
        self.assertTrue(semantic["semantic_success"])
        self.assertFalse(semantic["repair_goal_success"])
        self.assertEqual(metrics["engineering_pass_count"], 1)
        self.assertEqual(validity.semantic_exit_code(semantic), 0)

        invalid = dict(passed)
        invalid["hite"] = {"status": "INVALID_RUN", "identity": {"satisfied": False}}
        _, semantic = validity.build_metrics("x", expected, invalid, Path("attempt"))
        self.assertFalse(semantic["semantic_success"])
        self.assertEqual(validity.semantic_exit_code(semantic), 2)

        missing = {"hite": passed["hite"]}
        _, semantic = validity.build_metrics("x", expected, missing, Path("attempt"))
        self.assertFalse(semantic["semantic_success"])
        unexpected = {**passed, "forbidden": passed["hite"]}
        _, semantic = validity.build_metrics("x", expected, unexpected, Path("attempt"))
        self.assertFalse(semantic["semantic_success"])

    def test_hite_identity_stop_assertion_checks_every_condition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = Path(tmp) / "help.out"
            stdout.write_text("################ HiTE, version 9.9.9 ################\n", encoding="utf-8")
            base = {"name": "hite_help_identity", "exit_code": 0, "timed_out": False, "stdout": str(stdout)}
            adapter = validity.not_attempted("identity mismatch")
            validity.assert_hite_identity_stop([base], False, adapter)
            variants = (
                ([base, {"name": "hite_min", "exit_code": 0}], False, adapter),
                ([{**base, "name": "other"}], False, adapter),
                ([{**base, "exit_code": 2}], False, adapter),
                ([{**base, "timed_out": True}], False, adapter),
                ([base], True, adapter),
                ([base], False, {"attempted": True}),
            )
            for commands, identity_ok, adapter_value in variants:
                with self.subTest(commands=commands, identity_ok=identity_ok, adapter=adapter_value):
                    with self.assertRaises(ValueError):
                        validity.assert_hite_identity_stop(commands, identity_ok, adapter_value)

    def test_hite_exact_version_token_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = Path(tmp) / "help.out"
            command = {"exit_code": 0, "timed_out": False, "stdout": str(stdout)}
            stdout.write_text("########################## HiTE, version 3.3.3 ##########################\n", encoding="utf-8")
            self.assertTrue(validity.hite_333_identity(command))
            for banner in (
                "dependency version 3.3.3\n",
                "logo version 3.3.3\n",
                "################ HiTE, version 13.3.30 ################\n",
                "################ HiTE, version 3.3.30 ################\n",
                "HiTE, version 3.3.3\n",
            ):
                stdout.write_text(banner, encoding="utf-8")
                self.assertFalse(validity.hite_333_identity(command), banner)

    def test_hite_strict_runner_uses_direct_argv_and_gates_minimum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            help_out = root / "help.out"
            min_out = root / "min.out"
            help_result = {"name": "hite_help_identity", "exit_code": 0, "timed_out": False, "stdout": str(help_out)}
            min_result = {"name": "hite_min", "exit_code": 0, "timed_out": False, "stdout": str(min_out)}
            help_out.write_text("dependency version 3.3.3\n", encoding="utf-8")
            with mock.patch.object(validity, "bounded_command", return_value=help_result) as command:
                results = validity.run_hite_commands_strict(self.parent, Path("hite.sif"), root, root / "logs", {"identity": 10, "minimum_input": 20}, mock.Mock())
            self.assertEqual(results, [help_result])
            self.assertEqual(command.call_count, 1)
            help_argv = command.call_args.args[1]
            self.assertEqual(help_argv[-3:], ["python", "/HiTE/main.py", "-h"])
            self.assertNotIn("bash", help_argv)
            self.assertNotIn("-lc", help_argv)

            help_out.write_text("########################## HiTE, version 3.3.3 ##########################\n", encoding="utf-8")
            min_out.write_text("done\n", encoding="utf-8")
            with mock.patch.object(validity, "bounded_command", side_effect=[help_result, min_result]) as command:
                results = validity.run_hite_commands_strict(self.parent, Path("hite.sif"), root, root / "logs", {"identity": 10, "minimum_input": 20}, mock.Mock())
            self.assertEqual(results, [help_result, min_result])
            min_argv = command.call_args_list[1].args[1]
            self.assertEqual(min_argv[-10:], [
                "python", "/HiTE/main.py", "--genome", "/work/input/hite.fa", "--thread", "2",
                "--annotate", "1", "--out_dir", "/work/hite",
            ])
            self.assertNotIn("bash", min_argv)

    def test_hite_mismatch_records_actual_evidence_and_never_attempts_min_or_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            help_out = root / "help.out"
            help_out.write_text("dependency version 3.3.3\n", encoding="utf-8")
            command = {
                "name": "hite_help_identity", "exit_code": 0, "timed_out": False,
                "stdout": str(help_out), "stderr": str(root / "help.err"),
            }
            fixture_path = root / "hite.fa"
            fixture_path.write_text(">x\nACGT\n", encoding="utf-8")
            fixture = {"pass": True, "resolved": str(fixture_path)}
            licenses = {"hite": {"readable": True}}
            manifest = root / "hite.sif.manifest.json"
            manifest.write_text("{}\n", encoding="utf-8")
            (root / "work" / "input").mkdir(parents=True)
            with mock.patch.object(validity, "run_hite_commands_strict", return_value=[command]), \
                 mock.patch.object(self.parent, "adapt", side_effect=AssertionError("adapter must not run")):
                cell = validity.run_hite(
                    self.parent, self.config, self.parent_config, ROOT, root / "attempt", root / "work",
                    fixture, licenses, True, root / "hite.sif", manifest, {"pass": True}, mock.Mock(),
                )
            self.assertEqual(cell["status"], "VERSION_MISMATCH")
            self.assertFalse(cell["adapter"]["attempted"])
            self.assertEqual([item["name"] for item in cell["commands"]], ["hite_help_identity"])
            observed = cell["identity"]["observed"]
            self.assertEqual(observed["actual_banner_lines"], ["dependency version 3.3.3"])
            self.assertEqual(observed["stdout_path"], str(help_out))
            self.assertEqual(observed["stdout_sha256"], validity.sha(help_out))
            self.assertNotEqual(observed.get("runtime_help"), "3.3.3")

    def test_hite_runtime_or_adapter_failures_are_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture_path = root / "hite.fa"
            fixture_path.write_text(">x\nACGT\n", encoding="utf-8")
            fixture = {"pass": True, "resolved": str(fixture_path)}
            licenses = {"hite": {"readable": True}}
            manifest = root / "manifest.json"; manifest.write_text("{}\n", encoding="utf-8")
            (root / "w1" / "input").mkdir(parents=True)
            (root / "w2" / "input").mkdir(parents=True)
            help_out = root / "help.out"; help_out.write_text("########################## HiTE, version 3.3.3 ##########################\n", encoding="utf-8")
            min_out = root / "min.out"; min_out.write_text("done\n", encoding="utf-8")
            failed_help = {"name": "hite_help_identity", "exit_code": 2, "timed_out": False, "stdout": str(help_out)}
            with mock.patch.object(validity, "run_hite_commands_strict", return_value=[failed_help]), \
                 mock.patch.object(self.parent, "adapt", side_effect=AssertionError("adapter must not run")):
                cell = validity.run_hite(self.parent, self.config, self.parent_config, ROOT, root / "a1", root / "w1", fixture, licenses, True, root / "hite.sif", manifest, {"pass": True}, mock.Mock())
            self.assertEqual(cell["status"], "INVALID_RUN")

            ok_help = {"name": "hite_help_identity", "exit_code": 0, "timed_out": False, "stdout": str(help_out)}
            ok_min = {"name": "hite_min", "exit_code": 0, "timed_out": False, "stdout": str(min_out)}
            with mock.patch.object(validity, "run_hite_commands_strict", return_value=[ok_help, ok_min]), \
                 mock.patch.object(self.parent, "adapt", return_value={"pass": False, "reason": "missing GFF"}):
                cell = validity.run_hite(self.parent, self.config, self.parent_config, ROOT, root / "a2", root / "w2", fixture, licenses, True, root / "hite.sif", manifest, {"pass": True}, mock.Mock())
            self.assertEqual(cell["status"], "INVALID_RUN")

    def test_runtime_budget_and_kill_after_are_enforced(self) -> None:
        budget = validity.RuntimeBudget(self.config["runtime_budget"], self.config["timeouts_seconds"])
        accounted = (
            self.config["runtime_budget"]["command_timeout_sum_seconds"]
            + self.config["runtime_budget"]["max_command_count"] * self.config["runtime_budget"]["kill_after_seconds"]
            + self.config["runtime_budget"]["asset_hash_budget_seconds"]
            + self.config["runtime_budget"]["publish_budget_seconds"]
            + self.config["runtime_budget"]["required_headroom_seconds"]
        )
        self.assertLessEqual(accounted, 3600)
        self.assertGreaterEqual(self.config["runtime_budget"]["required_headroom_seconds"], 900)
        bad = dict(self.config["runtime_budget"], required_headroom_seconds=899)
        with self.assertRaisesRegex(ValueError, "15 minutes"):
            validity.RuntimeBudget(bad, self.config["timeouts_seconds"])

        with mock.patch.object(validity.time, "monotonic", side_effect=[0.0, 2000.0]):
            delayed = validity.RuntimeBudget(self.config["runtime_budget"], self.config["timeouts_seconds"])
            self.assertEqual(delayed.command_limit(600), 500)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            captured: list[str] = []
            def fake_run(argv, **kwargs):
                captured.extend(argv)
                Path(argv[argv.index("-o") + 1]).write_text("Maximum resident set size (kbytes): 1\n")
                return subprocess.CompletedProcess(argv, 124)
            with mock.patch.object(validity.subprocess, "run", side_effect=fake_run):
                result = validity.bounded_command("probe", ["false"], root, 60, budget)
            self.assertTrue(result["timed_out"])
            self.assertIn("--kill-after=10", captured)
            self.assertEqual(result["configured_timeout_seconds"], 60)

    def _rm_commands(self, root: Path, rm_banner: str = "RepeatMasker version 4.2.4\n") -> list[dict]:
        texts = {
            "famdb_info": "Version : 4.0\n",
            "famdb_family": ">DF0000001.4 MIR3\nACGT\n",
            "rm2_version": "RepeatModeler version 2.0.9\n",
            "rm2_famdb": "Version : 4.0\n",
            "rm2_min": "completed\n",
            "rm_min": rm_banner,
        }
        commands = []
        for name, text in texts.items():
            out = root / f"{name}.out"; out.write_text(text, encoding="utf-8")
            commands.append({"name": name, "exit_code": 0, "timed_out": False, "stdout": str(out)})
        return commands

    def _run_rm(self, root: Path, commands: list[dict], adapter: dict, prerequisite: bool = True):
        fixture_path = root / "fixture.fa"; fixture_path.write_text(">x\nACGT\n", encoding="utf-8")
        work = root / "work"; (work / "input").mkdir(parents=True)
        fixture = {"pass": prerequisite, "resolved": str(fixture_path)}
        components = {
            "repeatmasker_4_2_4": {"pass": prerequisite, "resolved": str(root / "rm.sif")},
            "repeatmodeler_2_0_9": {"pass": prerequisite, "resolved": str(root / "rm2.sif")},
        }
        licenses = {"repeatmodeler2_repeatmasker": {"readable": prerequisite}}
        famdb = {"pass": prerequisite}
        with mock.patch.object(validity, "bounded_command", side_effect=commands) as invoked, \
             mock.patch.object(self.parent, "adapt", return_value=adapter):
            cell = validity.run_repeatmodeler_repeatmasker(
                self.parent, self.config, self.parent_config, ROOT, root / "attempt", work,
                fixture, components, licenses, famdb, root / "famdb", mock.Mock(),
            )
        return cell, invoked

    def test_rm_handler_behavior_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cell, invoked = self._run_rm(Path(tmp), [], {"pass": True}, prerequisite=False)
            self.assertEqual(cell["status"], "FOUNDATIONAL_TYPED_BLOCK")
            self.assertEqual(cell["commands"], [])
            invoked.assert_not_called()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cell, invoked = self._run_rm(root, self._rm_commands(root), {"pass": True, "rows": 1})
            self.assertEqual(cell["status"], "ENGINEERING_PASS")
            self.assertTrue(cell["adapter"]["pass"])
            self.assertEqual(invoked.call_count, 6)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cell, _ = self._run_rm(root, self._rm_commands(root, "RepeatMasker version 4.2.3\n"), {"pass": True})
            self.assertEqual(cell["status"], "VERSION_MISMATCH")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); commands = self._rm_commands(root); commands[4] = {**commands[4], "exit_code": 1}
            cell, _ = self._run_rm(root, commands, {"pass": True})
            self.assertEqual(cell["status"], "INVALID_RUN")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); commands = self._rm_commands(root); commands[4] = {**commands[4], "exit_code": 124, "timed_out": True}
            cell, _ = self._run_rm(root, commands, {"pass": True})
            self.assertEqual(cell["status"], "INVALID_RUN")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cell, _ = self._run_rm(root, self._rm_commands(root), {"pass": False, "reason": "adapter failed"})
            self.assertEqual(cell["status"], "INVALID_RUN")

    def test_repeatmasker_identity_comes_from_exit_zero_minimum_evidence(self) -> None:
        source = (HERE / "run_validity_smoke.py").read_text(encoding="utf-8")
        self.assertNotIn("RepeatMasker -version", source)
        self.assertIn("repeatmasker_424_identity(commands[5])", source)
        self.assertIn('"rm_min"', source)

    def test_pre_submit_gate_block_pass_and_stale_in_temp_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviewed = root / "runner.py"; reviewed.write_text("v1\n", encoding="utf-8")
            gate_path = root / "outputs" / "x" / "code_review_gate.json"
            gate_path.parent.mkdir(parents=True)
            base = {
                "exp_id": "x", "reviewer_backend": "test", "independence": "separate_codex",
                "profile": "smoke", "reviewed_files": {"runner.py": validity.sha(reviewed)},
                "blockers_open": 0, "timestamp": "test",
            }
            def run_gate():
                return subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "pre_submit_gate.py"), "--exp-id", "x", str(root), "--format", "json"],
                    cwd="/", text=True, capture_output=True, check=False,
                )
            gate_path.write_text(json.dumps({**base, "verdict": "BLOCKED", "blockers_open": 1}))
            self.assertEqual(run_gate().returncode, 3)
            gate_path.write_text(json.dumps({**base, "verdict": "PASS"}))
            self.assertEqual(run_gate().returncode, 0)
            reviewed.write_text("v2\n", encoding="utf-8")
            stale = run_gate()
            self.assertEqual(stale.returncode, 3)
            self.assertIn("过期", stale.stdout)

    def test_sbatch_is_cwd_independent_and_bounded(self) -> None:
        sbatch = (ROOT / "sbatch" / "BENCH-RM-HITE-VALIDITY-20260811-R1.sbatch").read_text(encoding="utf-8")
        self.assertIn("#SBATCH --cpus-per-task=4", sbatch)
        self.assertIn("#SBATCH --mem=48G", sbatch)
        self.assertIn("#SBATCH --time=01:00:00", sbatch)
        self.assertNotIn("--gres", sbatch)
        self.assertIn("pre_submit_gate.py", sbatch)
        self.assertIn("conda activate benchmark_core", sbatch)
        self.assertIn('cd "${TEFM_ROOT}"', sbatch)
        self.assertIn('--exp-id "${TEFM_EXP}" "${TEFM_ROOT}"', sbatch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
