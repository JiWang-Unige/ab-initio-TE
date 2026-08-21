#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("shard_preflight", HERE / "shard_preflight.py")
preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)
CONFIG = PROJECT / "configs/SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1.yaml"


def cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def make_h5(path: Path, unit_sizes=(3, 2)) -> tuple[list[str], list[str]]:
    import h5py
    paths, units = [], []
    with h5py.File(path, "w") as handle:
        for unit_index, size in enumerate(unit_sizes):
            unit = f"Families/Aux/u{unit_index}"
            units.append(unit)
            group = handle.create_group(unit)
            nested = group.create_group("nested")
            for index in range(size):
                parent = nested if index % 2 else group
                item = parent.create_dataset(f"D{unit_index}_{index}", data=[1])
                item.attrs.update({"name": f"N{unit_index}_{index}", "accession": f"D{unit_index}_{index}",
                                   "version": 1, "consensus": "ACGT"})
                paths.append(item.name.lstrip("/"))
        handle.create_group("Families/DR/00/01")
    return paths, units


def minimal_preview(root: Path) -> dict:
    preview = root / "preview"
    preview.mkdir()
    config = {"exp_id": "X", "preview_root": "preview", "slurm_log_dir": "preview/logs",
              "profile": "test", "owner_lock_name": ".lock"}
    preflight.atomic_json(preview / "input_manifest.json", {})
    preflight.atomic_json(preview / "static_contract.json", {})
    return config


class ShardPreflightTests(unittest.TestCase):
    def test_real_topology_and_r0_telemetry_pins_without_dataset_scan(self):
        source, units, audit = preflight.validate_inputs(PROJECT, cfg())
        self.assertEqual(len(units), 35)
        self.assertEqual(audit["topology_unit_list_sha256"],
                         "bfea5e8dfc69eb5f6a38f2fb118a8a59b79050060cfe8078a8014459b10e94c2")
        self.assertEqual(source.stat().st_size, 63939647016)
        self.assertEqual(audit["h5_open_mode"], "read_only")
        self.assertEqual(audit["r0_observed_telemetry_sha256"],
                         "d5605364dd19e86934feef046f0fe57a5e96b949a84b31fbb8f3e713f4f6e32d")
        self.assertFalse(audit["scientific_target_resolution_executed"])

    def test_inventory_independent_rebuild_hash_count_order_and_exactly_once(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "x.h5"
            _paths, units = make_h5(source, (5, 4, 3))
            assignment = preflight.round_robin_unit_assignment(units, 2)
            first, _, _ = preflight.launch_inventory_rebuild(source, units, assignment, root / "r1", 10)
            counts = {unit: len(first[unit]) for unit in units}
            balanced = preflight.balanced_unit_assignment(units, counts, 2)
            second, _, _ = preflight.launch_inventory_rebuild(source, units, balanced, root / "r2", 10)
            paths1, counts1, digest1 = preflight.inventory_identity(first, units)
            paths2, counts2, digest2 = preflight.inventory_identity(second, units)
        self.assertEqual(paths1, paths2)
        self.assertEqual(counts1, counts2)
        self.assertEqual(digest1, digest2)
        self.assertEqual(len(paths1), len(set(paths1)))

    def test_balanced_assignment_deterministic_union_and_skew(self):
        units = ["a", "b", "c", "d", "e"]
        counts = {"a": 10, "b": 8, "c": 6, "d": 4, "e": 2}
        first = preflight.balanced_unit_assignment(units, counts, 2)
        second = preflight.balanced_unit_assignment(units, counts, 2)
        self.assertEqual(first, second)
        self.assertEqual(sorted(unit for values in first.values() for unit in values), sorted(units))
        loads = [sum(counts[unit] for unit in values) for values in first.values()]
        self.assertLessEqual(max(loads) - min(loads), max(counts.values()))

    def test_within_unit_content_drift_changes_inventory_and_workload_hash(self):
        units = ["u0", "u1"]
        first = {"u0": ["u0/a", "u0/b", "u0/c"], "u1": ["u1/a", "u1/b", "u1/c"]}
        second = {"u0": ["u0/a", "u0/b", "u0/d"], "u1": ["u1/a", "u1/b", "u1/c"]}
        _paths1, _counts1, digest1 = preflight.inventory_identity(first, units)
        _paths2, _counts2, digest2 = preflight.inventory_identity(second, units)
        workload1, _audit1 = preflight.build_stratified_workload(first, units, 4)
        workload2, _audit2 = preflight.build_stratified_workload(second, units, 4)
        self.assertNotEqual(digest1, digest2)
        self.assertNotEqual(preflight.sha256_text("".join(path + "\n" for path in workload1)),
                            preflight.sha256_text("".join(path + "\n" for path in workload2)))

    def test_proportional_stratified_sampling_covers_units_depth_and_locality(self):
        units = ["u0", "u1", "u2"]
        by_unit = {"u0": [f"u0/a/{index:03d}" for index in range(80)],
                   "u1": [f"u1/{index:03d}" for index in range(15)],
                   "u2": [f"u2/a/b/{index:03d}" for index in range(5)]}
        first, audit1 = preflight.build_stratified_workload(by_unit, units, 40)
        second, audit2 = preflight.build_stratified_workload(by_unit, units, 40)
        self.assertEqual(first, second)
        self.assertEqual(audit1, audit2)
        self.assertEqual(len(first), 40)
        self.assertTrue(all(row["sample_count"] >= 1 for row in audit1))
        self.assertTrue(all(row["selected_span_fraction"] > 0 for row in audit1))
        self.assertTrue(all(sum(row[f"locality_q{i}"] for i in range(1, 5)) == row["sample_count"]
                            for row in audit1))
        self.assertEqual(cfg()["workload"]["representative_dataset_paths"], 8192)

    def test_shard_union_intersection_exactly_once_and_hash_assignment(self):
        paths = [f"Families/DR/00/01/D{index}" for index in range(100)]
        first = preflight.partition_workload(paths, 4)
        second = preflight.partition_workload(paths, 4)
        self.assertEqual(first, second)
        flattened = [path for values in first.values() for path in values]
        self.assertEqual(set(flattened), set(paths))
        self.assertEqual(len(flattened), len(set(flattened)))
        for shard, values in first.items():
            self.assertTrue(all(preflight.shard_for_path(path, 4) == shard for path in values))

    def test_workload_hash_truncation_and_duplicate_fail_closed(self):
        payload = {"dataset_paths": ["A", "B"], "path_count": 2,
                   "ordered_paths_sha256": preflight.sha256_text("A\nB\n")}
        self.assertEqual(preflight.validate_workload(payload), ["A", "B"])
        with self.assertRaisesRegex(ValueError, "TRUNCATION_OR_HASH"):
            preflight.validate_workload({**payload, "path_count": 1})
        duplicate = {"dataset_paths": ["A", "A"], "path_count": 2,
                     "ordered_paths_sha256": preflight.sha256_text("A\nA\n")}
        with self.assertRaisesRegex(ValueError, "TRUNCATION_OR_HASH"):
            preflight.validate_workload(duplicate)

    def test_worker_read_only_exact_count_batch_remainder_and_output_race(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "x.h5"
            paths, _units = make_h5(source, (3,))
            workload = root / "work.json"
            preflight.write_workload(workload, sorted(paths), "0")
            stage = root / "worker"
            result = preflight.worker_read(source, workload, stage, 2)
            self.assertEqual(result["processed_path_count"], len(paths))
            self.assertEqual([row["records"] for row in result["batch_measurements"]], [2, 1])
            self.assertEqual(result["h5_open_mode"], "read_only")
            with self.assertRaises(FileExistsError):
                preflight.worker_read(source, workload, stage, 2)

    def test_child_nonzero_performance_timeout_and_truncated_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with self.assertRaisesRegex(RuntimeError, "CHILD_NONZERO"):
                preflight.launch_children([[sys.executable, "-c", "raise SystemExit(3)"]],
                                          [root / "s1"], 2, root / "l1")
            with self.assertRaisesRegex(preflight.PerformanceBudgetInfeasible, "PERFORMANCE_TIMEOUT"):
                preflight.launch_children([[sys.executable, "-c", "import time;time.sleep(2)"]],
                                          [root / "s2"], 0.05, root / "l2")
            stage = root / "s3"
            command = [sys.executable, "-c", f"import pathlib;pathlib.Path({str(stage)!r}).mkdir()"]
            with self.assertRaisesRegex(ValueError, "CHILD_OUTPUT_TRUNCATED"):
                preflight.launch_children([command], [stage], 2, root / "l3")

    def test_partial_popen_failure_kills_and_waits_started_children(self):
        class FakeProcess:
            def __init__(self):
                self.killed = False
                self.waited = False

            def poll(self):
                return None

            def kill(self):
                self.killed = True

            def wait(self, timeout=None):
                self.waited = True
                return -9

        with tempfile.TemporaryDirectory() as name:
            fake = FakeProcess()
            with mock.patch.object(preflight.subprocess, "Popen", side_effect=[fake, OSError("spawn failed")]):
                with self.assertRaisesRegex(OSError, "spawn failed"):
                    preflight.run_processes([["one"], ["two"]], 2, Path(name) / "logs")
            self.assertTrue(fake.killed)
            self.assertTrue(fake.waited)

    def test_child_manifest_hash_tamper_fails(self):
        with tempfile.TemporaryDirectory() as name:
            root, stage = Path(name), Path(name) / "s"
            code = ("import json,pathlib; p=pathlib.Path(" + repr(str(stage)) + ");p.mkdir();"
                    "(p/'worker_result.json').write_text(json.dumps({'status':'WORKER_COMPLETE','input_path_count':1,'processed_path_count':1}));"
                    "(p/'worker_manifest.json').write_text(json.dumps({'worker_result_sha256':'bad'}))")
            with self.assertRaisesRegex(ValueError, "OUTPUT_HASH_MISMATCH"):
                preflight.launch_children([[sys.executable, "-c", code]], [stage], 2, root / "logs")

    def test_worker_result_bound_to_exact_workload_hash_and_id(self):
        payload = {"worker_id": "0", "dataset_paths": ["A"], "path_count": 1,
                   "ordered_paths_sha256": preflight.sha256_text("A\n")}
        result = {"worker_id": "0", "input_path_count": 1, "processed_path_count": 1,
                  "input_ordered_paths_sha256": payload["ordered_paths_sha256"]}
        preflight.validate_worker_results([result], [payload])
        with self.assertRaisesRegex(ValueError, "INPUT_OUTPUT_BINDING"):
            preflight.validate_worker_results([{**result, "input_ordered_paths_sha256": "bad"}], [payload])

    def test_end_to_end_eta_includes_discovery_merge_r0_bound_and_headroom(self):
        config = cfg()
        workload = [str(index) for index in range(8)]
        shards = {index: workload[index * 2:(index + 1) * 2] for index in range(4)}
        unit_counts = {f"u{index}": 80464 for index in range(4)}
        assignment = {index: [f"u{index}"] for index in range(4)}
        serial = {"processed_path_count": 8, "elapsed_seconds": 0.4,
                  "batch_measurements": [{"records": 4, "seconds": 0.2}, {"records": 4, "seconds": 0.2}]}
        parallel = [{"processed_path_count": 2,
                     "batch_measurements": [{"records": 2, "seconds": 0.08}]} for _ in range(4)]
        metrics = preflight.aggregate_measurements(config, workload, shards, assignment, unit_counts,
                                                   serial, parallel, 0.15, 30.0, 2.0)
        self.assertTrue(metrics["path_discovery_included_in_eta"])
        self.assertGreaterEqual(metrics["preflight_full_chain_eta_seconds"], 32.0)
        self.assertEqual(metrics["conservative_parallel_full_scan_eta_seconds"],
                         max(metrics["preflight_full_chain_eta_seconds"],
                             metrics["r0_parallel_lower_bound_eta_seconds"]))
        self.assertFalse(metrics["throughput_preflight_feasible"])
        self.assertLess(metrics["estimated_headroom_fraction"], 0.25)

    def test_implausibly_fast_known_path_serial_is_explicit_block(self):
        config = cfg()
        workload = [str(index) for index in range(8)]
        shards = {index: workload[index * 2:(index + 1) * 2] for index in range(4)}
        counts = {f"u{index}": 80464 for index in range(4)}
        assignment = {index: [f"u{index}"] for index in range(4)}
        serial = {"processed_path_count": 8, "elapsed_seconds": 0.001,
                  "batch_measurements": [{"records": 8, "seconds": 0.001}]}
        parallel = [{"processed_path_count": 2,
                     "batch_measurements": [{"records": 2, "seconds": 0.001}]} for _ in range(4)]
        metrics = preflight.aggregate_measurements(config, workload, shards, assignment, counts,
                                                   serial, parallel, 0.001, 1.0, 0.1)
        self.assertTrue(metrics["known_path_speed_anomaly_block"])
        self.assertFalse(metrics["throughput_preflight_feasible"])

    def test_performance_timeout_is_semantic_valid_negative(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = minimal_preview(root)
            status, metrics = preflight.terminal_infeasible(root, config, "a", "CHILD_PERFORMANCE_TIMEOUT")
            self.assertEqual(status, "PREFLIGHT_INFEASIBLE")
            self.assertTrue(metrics["semantic_success"])
            self.assertTrue(metrics["valid_negative"])
            self.assertEqual((root / "preview/STATUS").read_text().strip(), "PREFLIGHT_INFEASIBLE")

    def test_formal_inventory_timeout_is_typed_infeasible_not_failed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = minimal_preview(root)
            config.update({"workload": {"shards": 4}, "materialization": {"per_rebuild_timeout_seconds": 1}})
            source = root / "x.h5"
            source.write_bytes(b"x")
            with mock.patch.object(preflight, "prepare_running", return_value=(source, ["u0"], {})), \
                    mock.patch.object(preflight, "launch_inventory_rebuild",
                                      side_effect=preflight.PerformanceBudgetInfeasible("INVENTORY_TIMEOUT")):
                status, metrics = preflight.run_formal(root, config, "a")
            self.assertEqual(status, "PREFLIGHT_INFEASIBLE")
            self.assertTrue(metrics["semantic_success"])
            self.assertNotEqual((root / "preview/STATUS").read_text().strip(), "PREFLIGHT_FAILED")

    def test_dirty_attempt_refusal_replaces_running_with_failed_terminal(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = minimal_preview(root)
            stage = root / "preview/attempts/a.tmp"
            stage.mkdir(parents=True)
            preflight.atomic_text(root / "preview/STATUS", "RUNNING\n")
            with self.assertRaisesRegex(ValueError, "DIRTY_PREFLIGHT_ATTEMPT_REFUSED"):
                preflight.run_formal(root, config, "a")
            self.assertEqual((root / "preview/STATUS").read_text().strip(), "PREFLIGHT_FAILED")
            metrics = json.loads((root / "preview/metrics.json").read_text())
            self.assertFalse(metrics["semantic_success"])

    def test_post_prepare_test_failure_finalizer_replaces_running(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = minimal_preview(root)
            preflight.finalize_preview(root, config, "RUNNING", "a", {"semantic_success": False}, {})
            preflight.terminal_failure(root, config, "a", "synthetic_test_failure")
            self.assertEqual((root / "preview/STATUS").read_text().strip(), "PREFLIGHT_FAILED")
            self.assertFalse(json.loads((root / "preview/TERMINAL_STATE.json").read_text())["semantic_success"])

    def test_slurm_log_parent_is_precreated_writable_and_manifested(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = minimal_preview(root)
            sentinel = preflight.ensure_slurm_log_dir(root, config)
            self.assertTrue(sentinel.is_file())
            self.assertTrue(os.access(sentinel.parent, os.W_OK))
            preflight.finalize_preview(root, config, "IMPLEMENTED_NOT_RUN", "a", {"semantic_success": False}, {})
            manifest = (root / "preview/output_manifest.sha256").read_text()
            self.assertIn("logs/.slurm_parent_precreated.json", manifest)

    def test_all_authorizations_always_false(self):
        flags = preflight.authorization_flags()
        self.assertTrue(all(value is False for value in flags.values()))
        self.assertEqual(cfg()["authorization"], flags)
        for status in ("IMPLEMENTED_NOT_RUN", "RUNNING", "PREFLIGHT_FEASIBLE", "PREFLIGHT_INFEASIBLE", "PREFLIGHT_FAILED"):
            with tempfile.TemporaryDirectory() as name:
                root = Path(name)
                config = minimal_preview(root)
                preflight.finalize_preview(root, config, status, "a", {"semantic_success": False}, {})
                terminal = json.loads((root / "preview/TERMINAL_STATE.json").read_text())
                self.assertTrue(all(terminal[key] is False for key in flags))

    def test_positive_numeric_slurm_guard(self):
        old = os.environ.pop("SLURM_JOB_ID", None)
        try:
            with self.assertRaisesRegex(ValueError, "FORMAL_SLURM_GUARD"):
                preflight.validate_formal_guard(Path("/tmp"), {"preview_root": "x"})
            os.environ["SLURM_JOB_ID"] = "abc"
            with self.assertRaisesRegex(ValueError, "FORMAL_SLURM_GUARD"):
                preflight.validate_formal_guard(Path("/tmp"), {"preview_root": "x"})
        finally:
            os.environ.pop("SLURM_JOB_ID", None)
            if old is not None:
                os.environ["SLURM_JOB_ID"] = old

    def test_payload_tamper_and_preview_hash_closure(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            stage = root / "stage"
            stage.mkdir()
            for filename in ("topology_units.tsv", "unit_sampling.tsv", "workload.tsv", "metrics.json",
                             "report.json", "RUN_MANIFEST.json", "env.json"):
                (stage / filename).write_text(filename)
            preflight.create_payload_manifest(stage)
            preflight.verify_payload(stage)
            (stage / "metrics.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "PAYLOAD_DRIFT"):
                preflight.verify_payload(stage)

    def test_stage_budgets_fit_twenty_minutes_and_serial_covers_r0_projection(self):
        config = cfg()
        expected_serial = (config["workload"]["representative_dataset_paths"]
                           * config["feasibility"]["r0_observed_elapsed_seconds"]
                           / config["feasibility"]["r0_observed_datasets"])
        self.assertGreaterEqual(config["workload"]["serial_child_timeout_seconds"], expected_serial)
        total = (2 * config["materialization"]["per_rebuild_timeout_seconds"]
                 + config["workload"]["serial_child_timeout_seconds"]
                 + config["workload"]["parallel_child_timeout_seconds"]
                 + config["feasibility"]["reserved_tests_and_publish_seconds"])
        self.assertEqual(total, config["feasibility"]["allocation_seconds"])

    def test_sbatch_resource_route_log_precondition_failure_trap_and_prepare_order(self):
        text = (PROJECT / "sbatch/SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1.sbatch").read_text()
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertIn("#SBATCH --time=00:20:00", text)
        self.assertIn("#SBATCH --cpus-per-task=4", text)
        self.assertIn("#SBATCH --mem=16G", text)
        self.assertNotIn("#SBATCH --gres", text)
        self.assertNotIn('mkdir -p "${PREFLIGHT_PREVIEW}/logs"', text)
        self.assertIn('test -d "${PREFLIGHT_PREVIEW}/logs"', text)
        self.assertIn("--finalize-failed-only", text)
        self.assertIn("PREFLIGHT_PREPARED=1", text)
        self.assertLess(text.index("--prepare-running-only"), text.index("test_shard_preflight.py"))
        self.assertIn('test -z "${SLURM_JOB_GPUS:-}"', text)
        self.assertIn("pre_submit_gate.py", text)


if __name__ == "__main__":
    unittest.main()
