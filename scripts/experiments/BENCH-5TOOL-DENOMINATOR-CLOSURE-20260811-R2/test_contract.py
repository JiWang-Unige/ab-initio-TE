#!/usr/bin/env python3
"""Offline contract tests for the R2 collector; no containers or research runs."""
from __future__ import annotations

import importlib.util
import ast
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("closure", HERE / "run_closure_smoke.py")
assert SPEC and SPEC.loader
closure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(closure)
LOCK_SPEC = importlib.util.spec_from_file_location("prep_lock", HERE / "prep_lock.py")
assert LOCK_SPEC and LOCK_SPEC.loader
prep_lock = importlib.util.module_from_spec(LOCK_SPEC)
LOCK_SPEC.loader.exec_module(prep_lock)


class ClosureContractTest(unittest.TestCase):
    def test_metrics_are_derived_and_semantic_failure_is_nonzero(self) -> None:
        expected = ["a", "b"]
        cells = {"a": {"status": "ENGINEERING_PASS", "identity": {"satisfied": True}}}
        metrics, semantic = closure.build_metrics("x", expected, cells, Path("attempt"))
        self.assertEqual(metrics["expected_cell_count"], 2)
        self.assertEqual(metrics["terminal_cell_count"], 1)
        self.assertEqual(metrics["missing_cell_keys"], ["b"])
        self.assertFalse(metrics["semantic_success"])
        self.assertFalse(semantic["semantic_success"])
        self.assertEqual(closure.semantic_exit_code(semantic), 2)

    def test_engineering_pass_with_wrong_identity_is_not_semantically_valid(self) -> None:
        cells = {"a": {"status": "ENGINEERING_PASS", "identity": {"satisfied": False}}}
        metrics, semantic = closure.build_metrics("x", ["a"], cells, Path("attempt"))
        self.assertEqual(metrics["silent_substitution_count"], 1)
        self.assertFalse(semantic["semantic_success"])

    def test_executed_runtime_failures_are_invalid_and_only_preexecution_is_blocked(self) -> None:
        required = {"tool": "frozen"}
        cells = {}
        for name, exit_code in (("rm", 1), ("eg", 1), ("hite", 127), ("edta", 2)):
            commands = [{"name": f"{name}_runtime", "exit_code": exit_code, "timed_out": False}]
            # A non-zero execution must dominate even inconsistent caller booleans.
            cells[name] = closure.executed_cell(required, commands, True, True, "runtime failed")
            self.assertEqual(cells[name]["status"], "INVALID_RUN")
            self.assertTrue(cells[name]["commands"])
        cells["tetrimmer"] = closure.blocked("immutable Pfam asset absent", required)
        self.assertEqual(cells["tetrimmer"]["status"], "FOUNDATIONAL_TYPED_BLOCK")
        self.assertEqual(cells["tetrimmer"]["commands"], [])

        metrics, semantic = closure.build_metrics("x", list(cells), cells, Path("attempt"))
        self.assertEqual(metrics["counts"]["INVALID_RUN"], 4)
        self.assertEqual(metrics["counts"]["FOUNDATIONAL_TYPED_BLOCK"], 1)
        self.assertFalse(metrics["semantic_success"])
        self.assertFalse(semantic["semantic_success"])
        self.assertEqual(closure.semantic_exit_code(semantic), 2)

    def test_exit_zero_identity_mismatch_is_not_a_foundational_block(self) -> None:
        cell = closure.executed_cell(
            {"tool": "1.0"}, [{"name": "help", "exit_code": 0, "timed_out": False}],
            identity_ok=False, run_ok=True, blocker="wrong version",
        )
        self.assertEqual(cell["status"], "VERSION_MISMATCH")

    def test_identity_gate_stop_is_version_terminal_but_real_failures_remain_invalid(self) -> None:
        exit_zero_help = [{"name": "hite_help_identity", "exit_code": 0, "timed_out": False}]
        version = closure.executed_cell(
            {"HiTE": "3.3.3"}, exit_zero_help, identity_ok=False, run_ok=False,
            blocker="wrong banner", identity_mismatch_stopped_before_minimum=True,
        )
        self.assertEqual(version["status"], "VERSION_MISMATCH")

        nonzero_help = [{"name": "hite_help_identity", "exit_code": 127, "timed_out": False}]
        with self.assertRaisesRegex(ValueError, "exit-zero mismatch"):
            closure.executed_cell(
                {"HiTE": "3.3.3"}, nonzero_help, identity_ok=False, run_ok=False,
                blocker="launcher failed", identity_mismatch_stopped_before_minimum=True,
            )
        runtime_invalid = closure.executed_cell(
            {"HiTE": "3.3.3"}, nonzero_help, identity_ok=False, run_ok=False,
            blocker="launcher failed",
        )
        self.assertEqual(runtime_invalid["status"], "INVALID_RUN")

        help_and_min = [
            {"name": "hite_help_identity", "exit_code": 0, "timed_out": False},
            {"name": "hite_min", "exit_code": 0, "timed_out": False},
        ]
        adapter_invalid = closure.executed_cell(
            {"HiTE": "3.3.3"}, help_and_min, identity_ok=True, run_ok=False,
            blocker="adapter failed",
        )
        self.assertEqual(adapter_invalid["status"], "INVALID_RUN")

        metrics, semantic = closure.build_metrics("x", ["hite"], {"hite": version}, Path("attempt"))
        self.assertEqual(metrics["counts"]["VERSION_MISMATCH"], 1)
        self.assertEqual(metrics["engineering_pass_fraction"], 0.0)
        self.assertTrue(metrics["semantic_success"])
        self.assertTrue(semantic["semantic_success"])
        self.assertEqual(closure.semantic_exit_code(semantic), 0)

    def test_repeatmasker_identity_uses_successful_minimum_or_adapter_banner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rm_min.out"
            out.write_text("RepeatMasker version 4.2.4\n\nSearch Engine: RMBlast\n", encoding="utf-8")
            result = {"exit_code": 0, "stdout": str(out)}
            self.assertTrue(closure.repeatmasker_424_identity(result))
            self.assertFalse(closure.repeatmasker_424_identity({**result, "exit_code": 1}))
            out.write_text("RepeatMasker version 4.2.3\n", encoding="utf-8")
            self.assertFalse(closure.repeatmasker_424_identity(result))
        runner = (HERE / "run_closure_smoke.py").read_text(encoding="utf-8")
        self.assertNotIn("RepeatMasker -version", runner)

    def test_hite_direct_argv_and_help_gates_minimum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            failed_out = root / "failed.out"
            failed_out.write_text("python missing\n", encoding="utf-8")
            failed = {"name": "hite_help_identity", "exit_code": 127, "timed_out": False, "stdout": str(failed_out)}
            with mock.patch.object(closure, "command", return_value=failed) as run:
                commands = closure.run_hite_commands(Path("hite.sif"), root, root / "logs", {"identity": 10, "minimum_input": 20})
            self.assertEqual(commands, [failed])
            self.assertEqual(run.call_count, 1)
            help_argv = run.call_args.args[1]
            self.assertEqual(help_argv[-3:], ["python", "/HiTE/main.py", "-h"])
            self.assertNotIn("bash", help_argv)
            self.assertNotIn("-lc", help_argv)

            help_out = root / "help.out"
            help_out.write_text("HiTE version 3.3.3\n", encoding="utf-8")
            minimum_out = root / "minimum.out"
            minimum_out.write_text("done\n", encoding="utf-8")
            passed_help = {"name": "hite_help_identity", "exit_code": 0, "timed_out": False, "stdout": str(help_out)}
            passed_min = {"name": "hite_min", "exit_code": 0, "timed_out": False, "stdout": str(minimum_out)}
            with mock.patch.object(closure, "command", side_effect=[passed_help, passed_min]) as run:
                commands = closure.run_hite_commands(Path("hite.sif"), root, root / "logs", {"identity": 10, "minimum_input": 20})
            self.assertEqual(commands, [passed_help, passed_min])
            self.assertEqual(run.call_count, 2)
            min_argv = run.call_args_list[1].args[1]
            self.assertEqual(min_argv[-10:], [
                "python", "/HiTE/main.py", "--genome", "/work/input/hite.fa", "--thread", "2",
                "--annotate", "1", "--out_dir", "/work/hite",
            ])
            self.assertNotIn("bash", min_argv)

    def test_famdb_layout_is_libraries_famdb(self) -> None:
        argv = closure.cexec(Path("x.sif"), Path("work"), "true", Path("famdb"))
        joined = " ".join(map(str, argv))
        self.assertIn("/usr/local/share/famdb-3.0.0/Libraries/famdb:ro", joined)
        self.assertIn("FAMDB_DIR=/usr/local/share/famdb-3.0.0/Libraries/famdb", joined)

    def test_legacy_and_current_famdb_manifests_are_fully_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "full.gz").write_bytes(b"full")
            (source / "curated.gz").write_bytes(b"curated")
            config = {
                "exp_id": "x",
                "dfam40": {
                    "full": {"path": "source/full.gz", "sha256": closure.sha(source / "full.gz")},
                    "curated_consensus": {"path": "source/curated.gz", "sha256": closure.sha(source / "curated.gz")},
                    "required_database": "Dfam 4.0",
                }
            }
            (root / "configs").mkdir()
            (root / "configs" / "x.yaml").write_text(json.dumps(config), encoding="utf-8")
            env_file = root / "environment.txt"
            env_file.write_text("frozen-env\n", encoding="utf-8")
            asset = root / "asset"
            asset.mkdir()
            (asset / "dfam40.0.h5").write_bytes(b"h5-full")
            (asset / "dfam40.curated.consensus.0.h5").write_bytes(b"h5-curated")
            (asset / "famdb.py").write_text("wrapper", encoding="utf-8")
            (asset / ".earlgrey.config.complete").touch()
            inputs = [
                {"id": "full", "source": str((source / "full.gz").resolve()), "source_sha256": config["dfam40"]["full"]["sha256"], "output": "dfam40.0.h5"},
                {"id": "curated_consensus", "source": str((source / "curated.gz").resolve()), "source_sha256": config["dfam40"]["curated_consensus"]["sha256"], "output": "dfam40.curated.consensus.0.h5"},
            ]
            base = {
                "required_database": "Dfam 4.0", "inputs": inputs,
                "outputs": [
                    {"name": "dfam40.0.h5", "sha256": closure.sha(asset / "dfam40.0.h5")},
                    {"name": "dfam40.curated.consensus.0.h5", "sha256": closure.sha(asset / "dfam40.curated.consensus.0.h5")},
                ],
                "famdb_wrapper_sha256": closure.sha(asset / "famdb.py"),
            }
            for schema in ("TEFM-FAMDB-ASSET-1.0.0", "TEFM-FAMDB-ASSET-2.0.0"):
                manifest = {**base, "schema_version": schema}
                if schema.endswith("2.0.0"):
                    manifest.update({
                        "preparation_slurm_job_id": "123",
                        "preparation_code_sha256": closure.sha(HERE / "prepare_famdb.py"),
                        "config_sha256": closure.sha(root / "configs" / "x.yaml"),
                        "environment_path": str(env_file),
                        "environment_sha256": closure.sha(env_file),
                    })
                (asset / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                result = closure.verify_famdb(asset, config, root)
                self.assertTrue(result["asset_integrity_pass"])
                self.assertEqual(result["pass"], schema.endswith("2.0.0"))
                if schema.endswith("1.0.0"):
                    self.assertTrue(result["provenance_limited_typed_block"])
            (asset / "dfam40.0.h5").write_bytes(b"tampered")
            self.assertFalse(closure.verify_famdb(asset, config, root)["pass"])

    def test_famdb_rejects_mapping_tamper_and_extra_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            sources = root / "sources"
            sources.mkdir()
            for name in ("full.gz", "curated.gz"):
                (sources / name).write_bytes(name.encode())
            config = {
                "exp_id": "x",
                "dfam40": {
                    "full": {"path": "sources/full.gz", "sha256": closure.sha(sources / "full.gz")},
                    "curated_consensus": {"path": "sources/curated.gz", "sha256": closure.sha(sources / "curated.gz")},
                    "required_database": "Dfam 4.0",
                },
            }
            (root / "configs" / "x.yaml").write_text(json.dumps(config), encoding="utf-8")
            asset = root / "asset"
            asset.mkdir()
            for name, content in (("dfam40.0.h5", b"a"), ("dfam40.curated.consensus.0.h5", b"b"), ("famdb.py", b"w")):
                (asset / name).write_bytes(content)
            (asset / ".earlgrey.config.complete").touch()
            env = root / "env.txt"; env.write_text("env", encoding="utf-8")
            inputs = [
                {"id": "full", "source": str((sources / "full.gz").resolve()), "source_sha256": closure.sha(sources / "full.gz"), "output": "WRONG.h5"},
                {"id": "curated_consensus", "source": str((sources / "curated.gz").resolve()), "source_sha256": closure.sha(sources / "curated.gz"), "output": "dfam40.curated.consensus.0.h5"},
            ]
            manifest = {
                "schema_version": "TEFM-FAMDB-ASSET-2.0.0", "required_database": "Dfam 4.0", "inputs": inputs,
                "outputs": [{"name": name, "sha256": closure.sha(asset / name)} for name in ("dfam40.0.h5", "dfam40.curated.consensus.0.h5")],
                "famdb_wrapper_sha256": closure.sha(asset / "famdb.py"), "preparation_slurm_job_id": "1",
                "preparation_code_sha256": closure.sha(HERE / "prepare_famdb.py"), "config_sha256": closure.sha(root / "configs" / "x.yaml"),
                "environment_path": str(env), "environment_sha256": closure.sha(env),
            }
            (asset / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertFalse(closure.verify_famdb(asset, config, root)["source_output_mapping_ok"])
            manifest["inputs"][0]["output"] = "dfam40.0.h5"
            manifest["inputs"].append(dict(manifest["inputs"][0], id="extra"))
            (asset / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertFalse(closure.verify_famdb(asset, config, root)["exact_input_row_set"])

    def test_scripts_pin_final_outputs_and_forbid_unfrozen_pfam_action(self) -> None:
        runner = (HERE / "run_closure_smoke.py").read_text(encoding="utf-8")
        prep = (Path("sbatch") / "BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2-preparation.sbatch").read_text(encoding="utf-8")
        main = (Path("sbatch") / "BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2.sbatch").read_text(encoding="utf-8")
        self.assertIn("r2_summaryFiles", runner)
        self.assertIn("TEtrimmer_consensus_merged.fasta", runner)
        self.assertIn("PREPARATION_TYPED_BLOCK", prep)
        self.assertNotIn("pfam) bash", prep)
        for text in (prep, main):
            self.assertIn("pre_submit_gate.py", text)
            self.assertIn("conda activate benchmark_core", text)

    def test_asset_manifests_are_complete_and_runtime_reverified(self) -> None:
        runner = (HERE / "run_closure_smoke.py").read_text(encoding="utf-8")
        hite = (HERE / "acquire_hite_exact.sh").read_text(encoding="utf-8")
        edta = (HERE / "acquire_edta_230_overlay.sh").read_text(encoding="utf-8")
        for field in ("inspect_sha256", "help_sha256", "source_commit", "preparation_slurm_job_id", "preparation_code_sha256", "config_sha256", "environment_sha256"):
            self.assertIn(field, hite)
            self.assertIn(field, runner)
        for field in ("source_tree_sha256", "edta_pl_sha256", "release_tag", "commit", "preparation_slurm_job_id", "preparation_code_sha256", "config_sha256", "environment_sha256"):
            self.assertIn(field, edta)
            self.assertIn(field, runner)
        self.assertIn("hite_help_identity", runner)
        self.assertIn("edta_help_identity", runner)

    def test_official_help_identity_contracts(self) -> None:
        edta_help = "##### Extensive de-novo TE Annotator (EDTA) v2.3  #####\nParameters: -h\n"
        self.assertTrue(closure.edta_help_identity(edta_help))
        self.assertFalse(closure.edta_help_identity(edta_help.replace("v2.3  ", "v2.3.2  ")))
        self.assertEqual(closure.edta_identity_command(), "perl /work/edta/EDTA.pl -h")
        tetrimmer_help = "TEtrimmer\n                Version: 1.7.4\nUsage\n"
        self.assertTrue(closure.tetrimmer_help_identity(tetrimmer_help))
        self.assertFalse(closure.tetrimmer_help_identity(tetrimmer_help.replace("1.7.4", "1.7.2")))
        command = closure.tetrimmer_identity_command("/work/source/tetrimmer/TEtrimmer.py")
        self.assertTrue(command.endswith(" --help"))
        self.assertNotIn("--version", command)

    def test_cells_do_not_share_a_global_prerequisite(self) -> None:
        runner = (HERE / "run_closure_smoke.py").read_text(encoding="utf-8")
        names = {node.id for node in ast.walk(ast.parse(runner)) if isinstance(node, ast.Name)}
        self.assertNotIn("base_ok", names)
        for gate in ("rm_prereq", "eg_prereq", "hite_prereq", "edta_prereq", "tetrimmer_prereq"):
            self.assertIn(gate, runner)

    def test_output_ownership_hash_and_stale_recovery_contracts_exist(self) -> None:
        runner = (HERE / "run_closure_smoke.py").read_text(encoding="utf-8")
        prep = (Path("sbatch") / "BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2-preparation.sbatch").read_text(encoding="utf-8")
        for token in ("acquire_lock", "job_is_active", "before-{job_id}", "code_prep_docs_hashes", "conda_explicit_sha256", "attempt / \"publish\""):
            self.assertIn(token, runner)
        for token in (".preparation-${TEFM_PREP_ACTION}.lock", "prep_lock.py", "TEFM_PREP_ENV_SHA256"):
            self.assertIn(token, prep)

    def test_lock_release_is_owner_checked_and_squeue_failure_is_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "lock"
            owner = {"job_id": "1", "host": "h", "pid": 1, "created_unix": 1.0}
            lock.write_text(json.dumps(owner), encoding="utf-8")
            self.assertFalse(closure.release_lock(lock, {**owner, "pid": 2}))
            self.assertTrue(lock.exists())
            self.assertTrue(closure.release_lock(lock, owner))
            lock.write_text("111:host:1:old\n", encoding="utf-8")
            failed = __import__("subprocess").CompletedProcess([], 2, stdout="", stderr="scheduler unavailable")
            with mock.patch.object(prep_lock.subprocess, "run", return_value=failed):
                with self.assertRaisesRegex(RuntimeError, "fail closed"):
                    prep_lock.acquire(lock, "222")
            self.assertEqual(lock.read_text(encoding="utf-8").strip(), "111:host:1:old")
            inactive = __import__("subprocess").CompletedProcess([], 0, stdout="", stderr="")
            with mock.patch.object(prep_lock.subprocess, "run", return_value=inactive):
                token = prep_lock.acquire(lock, "222")
            self.assertTrue(lock.read_text(encoding="utf-8").strip() == token)
            self.assertFalse(prep_lock.release(lock, "wrong-token"))
            self.assertTrue(lock.exists())
            self.assertTrue(prep_lock.release(lock, token))

    def test_main_lock_reconciliation_is_strictly_tristate(self) -> None:
        completed_process = __import__("subprocess").CompletedProcess
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "collector.lock"
            old_owner = {"job_id": "111", "host": "old", "pid": 1, "created_unix": 1.0}

            lock.write_text(json.dumps(old_owner), encoding="utf-8")
            with mock.patch.object(closure.subprocess, "run", return_value=completed_process([], 2, stdout="", stderr="scheduler down")):
                with self.assertRaisesRegex(RuntimeError, "fail closed"):
                    closure.acquire_lock(lock, "222", stale_seconds=1)
            self.assertEqual(json.loads(lock.read_text(encoding="utf-8")), old_owner)

            lock.write_text("not-json", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unparseable collector lock"):
                closure.acquire_lock(lock, "222", stale_seconds=1)
            self.assertEqual(lock.read_text(encoding="utf-8"), "not-json")

            nonnumeric_owner = {**old_owner, "job_id": "unknown"}
            lock.write_text(json.dumps(nonnumeric_owner), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unparseable collector lock owner"):
                closure.acquire_lock(lock, "222", stale_seconds=1)
            self.assertEqual(json.loads(lock.read_text(encoding="utf-8")), nonnumeric_owner)

            lock.write_text(json.dumps(old_owner), encoding="utf-8")
            with mock.patch.object(closure.subprocess, "run", return_value=completed_process([], 0, stdout="999\n", stderr="")):
                with self.assertRaisesRegex(RuntimeError, "unexpected squeue owner output"):
                    closure.acquire_lock(lock, "222", stale_seconds=1)
            self.assertEqual(json.loads(lock.read_text(encoding="utf-8")), old_owner)

            lock.write_text(json.dumps(old_owner), encoding="utf-8")
            with mock.patch.object(closure.subprocess, "run", return_value=completed_process([], 0, stdout="111\n", stderr="")):
                with self.assertRaises(SystemExit):
                    closure.acquire_lock(lock, "222", stale_seconds=1)
            self.assertEqual(json.loads(lock.read_text(encoding="utf-8")), old_owner)

            lock.write_text(json.dumps(old_owner), encoding="utf-8")
            with mock.patch.object(closure.subprocess, "run", return_value=completed_process([], 0, stdout="", stderr="")):
                new_owner = closure.acquire_lock(lock, "222", stale_seconds=1)
            self.assertEqual(json.loads(lock.read_text(encoding="utf-8")), new_owner)
            self.assertTrue(list(Path(tmp).glob("collector.lock.stale.*.111")))
            self.assertFalse(closure.release_lock(lock, {**new_owner, "pid": -1}))
            self.assertTrue(lock.exists())
            self.assertTrue(closure.release_lock(lock, new_owner))

    def test_rerun_enters_running_before_archiving_old_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "STATUS").write_text("COMPLETED\n", encoding="utf-8")
            (output / "metrics.json").write_text('{"old":true}\n', encoding="utf-8")
            archive = closure.begin_rerun(output, "321", timestamp=7)
            self.assertEqual((output / "STATUS").read_text(encoding="utf-8"), "RUNNING\n")
            self.assertFalse((output / "metrics.json").exists())
            self.assertIsNotNone(archive)
            assert archive is not None
            self.assertEqual((archive / "STATUS").read_text(encoding="utf-8"), "COMPLETED\n")
            self.assertEqual((archive / "metrics.json").read_text(encoding="utf-8"), '{"old":true}\n')

    def test_config_explicitly_blocks_mutable_pfam(self) -> None:
        config = json.loads((Path("configs") / "BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2.yaml").read_text(encoding="utf-8"))
        pfam = config["exact_sources"]["tetrimmer"]
        self.assertFalse(pfam["preparation_submittable"])
        self.assertEqual(pfam["pfam_release"], "UNFROZEN_CURRENT_RELEASE_TYPED_BLOCK")
        self.assertTrue(pfam["pfam_hmm_sha256"].startswith("REQUIRED_"))
        self.assertTrue(pfam["pfam_dat_sha256"].startswith("REQUIRED_"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
