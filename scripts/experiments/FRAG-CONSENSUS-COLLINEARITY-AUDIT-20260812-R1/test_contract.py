#!/usr/bin/env python3
"""Synthetic/static contract tests; never reads the real Rice payload."""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import build_sample
import evaluate_t1
import map_consensus_evidence
import partition_collinearity
import run_audit
import runtime_hashes
from common import atomic_write_json, iter_fasta, read_tsv, sha256_file, write_fasta, write_tsv


def unique_dna(seed: int, length: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("ACGT") for _ in range(length))


def public_row(leaf_id: str, start0: int, end0: int) -> dict[str, str]:
    return {"leaf_id": leaf_id, "seqid": "Chr1", "start0": str(start0), "end0": str(end0), "length_bp": str(end0 - start0), "sequence_sha256": "synthetic"}


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads((ROOT / "configs" / f"{HERE.name}.yaml").read_text())

    def test_config_scope_resources_and_forbidden_metrics(self) -> None:
        self.assertEqual(self.config["resources"]["cpus"], 8)
        self.assertEqual(self.config["resources"]["memory_gib"], 32)
        self.assertLessEqual(self.config["resources"]["walltime_seconds"], 7200)
        self.assertEqual(self.config["resources"]["gpus"], 0)
        self.assertEqual(self.config["resources"]["partition"], "private-teodoro-gpu")
        self.assertEqual(self.config["resources"]["walltime_seconds"], 7200)
        self.assertEqual(self.config["sequence_evidence"]["workers"], 8)
        self.assertGreaterEqual(self.config["resources"]["required_publish_headroom_seconds"], 900)
        resources = self.config["resources"]
        self.assertLessEqual(resources["preflight_command_timeout_seconds"] + resources["preflight_kill_after_seconds"], 300)
        self.assertLessEqual(resources["preflight_command_timeout_seconds"] + resources["preflight_kill_after_seconds"], resources["preflight_budget_seconds"])
        self.assertLessEqual(resources["preflight_budget_seconds"] + resources["payload_timeout_seconds"] + resources["kill_after_seconds"] + resources["required_publish_headroom_seconds"], resources["walltime_seconds"])
        forbidden = set(self.config["evaluation"]["forbidden_metrics"])
        allowlist = set(self.config["evaluation"]["allowed_t1_metrics"])
        self.assertFalse(forbidden & allowlist)
        self.assertEqual(allowlist, set(self.config["result_schema"]["required_method_fields"]) - {"method"})
        self.assertEqual(allowlist, set(self.config["result_schema"]["finite_numeric_fields"]))
        self.assertEqual(set(evaluate_t1.SUMMARY_FIELDS), set(self.config["result_schema"]["required_method_fields"]))
        self.assertFalse(self.config["global_partition"]["uses_genomic_gap"])
        self.assertFalse(self.config["global_partition"]["uses_truth_rm_id"])
        self.assertFalse(self.config["global_partition"]["uses_truth_parent_boundary"])
        runtime_files = set(self.config["runtime_code_files"])
        self.assertIn("scripts/pre_submit_gate.py", runtime_files)
        self.assertIn(f"scripts/experiments/{HERE.name}/common.py", runtime_files)
        self.assertIn(f"scripts/experiments/{HERE.name}/test_contract.py", runtime_files)
        self.assertIn(f"sbatch/{HERE.name}.sbatch", runtime_files)
        gate = self.config["runtime_contract"]["pre_submit_gate"]
        self.assertEqual(sha256_file(ROOT / gate["path"]), gate["sha256"])

    def test_preview_implementation_manifest_matches_all_listed_files(self) -> None:
        manifest = json.loads((ROOT / "outputs" / HERE.name / "preview" / "implementation_manifest.json").read_text())
        self.assertFalse(manifest["code_review_gate_written"])
        self.assertFalse(manifest["slurm_submitted"])
        self.assertFalse(manifest["real_scientific_payload_executed"])
        for relative, expected_hash in manifest["files"].items():
            self.assertEqual(sha256_file(ROOT / relative), expected_hash, relative)

    def test_duplicate_fasta_identifier_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "duplicate.fa"
            path.write_text(">same\nACGT\n>same\nTGCA\n")
            with self.assertRaisesRegex(ValueError, "duplicate FASTA identifier"):
                list(iter_fasta(path))

    def test_public_bundle_physically_excludes_truth_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            assembly = tmp / "assembly.fa"
            annotation = tmp / "annotation.tsv"
            write_fasta(assembly, [("Chr1", unique_dna(1, 500))])
            fields = ["source_line", "seqid", "start0", "end0", "rm_id", "class_root", "repeat_name", "strand", "overlap_marker"]
            rows = [
                {"source_line": "1", "seqid": "Chr1", "start0": "10", "end0": "50", "rm_id": "SECRET_A", "class_root": "LTR", "repeat_name": "SECRET_NAME", "strand": "+", "overlap_marker": "False"},
                {"source_line": "2", "seqid": "Chr1", "start0": "100", "end0": "140", "rm_id": "SECRET_A", "class_root": "LTR", "repeat_name": "SECRET_NAME", "strand": "+", "overlap_marker": "False"},
            ]
            write_tsv(annotation, rows, fields)
            sampling = dict(self.config["sampling"])
            sampling.update({"eligible_primary_contigs": ["Chr1"], "maximum_groups_per_stratum": 10, "maximum_groups_total": 10})
            build_sample.build_bundle(annotation, assembly, tmp / "bundle", sampling)
            public_text = (tmp / "bundle/public/leaves.tsv").read_text()
            public_fasta = (tmp / "bundle/public/leaves.fa").read_text()
            self.assertNotIn("rm_id", public_text)
            self.assertNotIn("SECRET_A", public_text + public_fasta)
            self.assertNotIn("truth_parent", public_text)
            self.assertIn("SECRET_A", (tmp / "bundle/evaluator_only/truth.tsv").read_text())

    def test_sequence_evidence_and_global_partition_recover_distant_fragments(self) -> None:
        consensus_a = unique_dna(7, 260)
        consensus_b = unique_dna(8, 260)
        leaves = {
            "l1": consensus_a[10:70], "l2": consensus_a[80:140],
            "l3": consensus_a[5:65], "l4": consensus_a[75:135],
        }
        public = [public_row("l1", 100, 160), public_row("l2", 500, 560), public_row("l3", 2000, 2060), public_row("l4", 2500, 2560)]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            leaf_fasta, consensus_fasta, evidence_path = tmp / "leaves.fa", tmp / "consensus.fa", tmp / "evidence.tsv"
            write_fasta(leaf_fasta, sorted(leaves.items()))
            write_fasta(consensus_fasta, [("consA", consensus_a), ("consB", consensus_b)])
            map_consensus_evidence.map_all(leaf_fasta, consensus_fasta, evidence_path, self.config["sequence_evidence"])
            evidence = read_tsv(evidence_path)
            self.assertEqual({row["mapping_status"] for row in evidence}, {"MAPPED"})
            self.assertEqual({row["consensus_id"] for row in evidence}, {"consA"})
            parents, assignments = partition_collinearity.partition(public, evidence, self.config["global_partition"], "CONSENSUS_COLLINEARITY")
            child_sets = {frozenset(row["child_leaf_ids"].split(",")) for row in parents}
            self.assertEqual(child_sets, {frozenset({"l1", "l2"}), frozenset({"l3", "l4"})})
            self.assertEqual(len(assignments), 4)
            self.assertTrue(all(row["immutable"] == "true" for row in assignments))

    def test_truth_tamper_cannot_change_assembler_output(self) -> None:
        public = [public_row("a", 10, 30), public_row("b", 1000, 1020)]
        evidence = [
            {"leaf_id": "a", "mapping_status": "MAPPED", "consensus_id": "C", "consensus_strand": "+", "consensus_start0": "10", "consensus_end0": "30", "consensus_length": "100", "seed_coverage": "1", "inlier_seed_count": "5", "second_seed_coverage": "0"},
            {"leaf_id": "b", "mapping_status": "MAPPED", "consensus_id": "C", "consensus_strand": "+", "consensus_start0": "40", "consensus_end0": "60", "consensus_length": "100", "seed_coverage": "1", "inlier_seed_count": "5", "second_seed_coverage": "0"},
        ]
        before = partition_collinearity.partition(public, evidence, self.config["global_partition"], "CONSENSUS_COLLINEARITY")
        hidden_truth_a = [{"leaf_id": "a", "rm_id": "1", "truth_parent_start0": "0"}, {"leaf_id": "b", "rm_id": "1", "truth_parent_start0": "0"}]
        hidden_truth_b = [{"leaf_id": "a", "rm_id": "X", "truth_parent_start0": "999"}, {"leaf_id": "b", "rm_id": "Y", "truth_parent_start0": "888"}]
        self.assertNotEqual(hidden_truth_a, hidden_truth_b)
        after = partition_collinearity.partition(public, evidence, self.config["global_partition"], "CONSENSUS_COLLINEARITY")
        self.assertEqual(before, after)
        source = (HERE / "partition_collinearity.py").read_text()
        self.assertNotIn('"rm_id"', source)
        self.assertNotIn('"truth_parent_start0"', source)
        self.assertNotIn('"truth_parent_end0"', source)

    def test_evaluator_reports_t1_metrics_and_no_whole_genome_metrics(self) -> None:
        public = [public_row("a", 10, 30), public_row("b", 100, 120), public_row("c", 1000, 1020), public_row("d", 1100, 1120)]
        truth = []
        for leaf, group, pstart, pend in [("a", "g1", 10, 120), ("b", "g1", 10, 120), ("c", "g2", 1000, 1120), ("d", "g2", 1000, 1120)]:
            truth.append({"leaf_id": leaf, "seqid": "Chr1", "rm_id": group, "truth_group_id": group, "truth_parent_start0": str(pstart), "truth_parent_end0": str(pend), "class_root": "LTR", "repeat_name": "R", "truth_strand": "+", "overlap_marker": "False", "row_count_bin": "two"})
        parents = [
            {"parent_id": "p1", "seqid": "Chr1", "start0": "10", "end0": "120", "child_leaf_ids": "a,b"},
            {"parent_id": "p2", "seqid": "Chr1", "start0": "1000", "end0": "1120", "child_leaf_ids": "c,d"},
        ]
        result = evaluate_t1.evaluate_method("TEST", public, truth, parents, {"a", "b", "c", "d"}, [5, 10, 25, 50])
        self.assertEqual(result["exact_truth_group_recovery"], 1.0)
        self.assertEqual(result["leaf_retention"], 1.0)
        self.assertEqual(result["cross_rm_id_false_fusion_proxy"], 0.0)
        self.assertEqual(result["topology_truth_group_count"], 0)
        self.assertEqual(result["truth_topology_preservation"], 0.0)
        self.assertFalse(any("whole_genome" in key or key in {"segment_f1", "bp_f1"} for key in result))
        evaluate_t1.validate_method_result(result, self.config["result_schema"])
        broken = dict(result)
        broken["exact_truth_group_recovery"] = float("nan")
        with self.assertRaisesRegex(ValueError, "not finite numeric"):
            evaluate_t1.validate_method_result(broken, self.config["result_schema"])
        missing = dict(result)
        del missing["leaf_retention"]
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            evaluate_t1.validate_method_result(missing, self.config["result_schema"])
        extra = dict(result)
        extra["unreviewed_metric"] = 1.0
        with self.assertRaisesRegex(ValueError, "unexpected"):
            evaluate_t1.validate_method_result(extra, self.config["result_schema"])

    def test_per_metric_comparator_maxima_are_independent(self) -> None:
        metrics = self.config["promotion_metrics"]
        gap20 = {metric: 0.2 for metric in metrics}
        gap100 = {metric: 0.1 for metric in metrics}
        gap20["exact_truth_group_recovery"] = 0.9
        gap100["exact_truth_group_recovery"] = 0.3
        gap20["pairwise_same_parent_harmonic"] = 0.4
        gap100["pairwise_same_parent_harmonic"] = 0.8
        maxima = evaluate_t1.comparator_maxima({"POSITIVE_ONLY_GAP20": gap20, "POSITIVE_ONLY_GAP100": gap100}, metrics)
        self.assertEqual(maxima["exact_truth_group_recovery"]["method"], "POSITIVE_ONLY_GAP20")
        self.assertEqual(maxima["pairwise_same_parent_harmonic"]["method"], "POSITIVE_ONLY_GAP100")

    def test_restricted_parent_boundaries_are_recomputed_from_retained_leaves(self) -> None:
        public = {"a": public_row("a", 10, 20), "b": public_row("b", 100, 120)}
        parents = [{"parent_id": "p", "seqid": "Chr1", "start0": 10, "end0": 120, "child_leaf_ids": "a,b", "child_count": 2}]
        restricted = evaluate_t1.restrict_parents(parents, {"b"}, public, "stratum")
        self.assertEqual(len(restricted), 1)
        self.assertEqual((restricted[0]["start0"], restricted[0]["end0"]), (100, 120))
        self.assertEqual(restricted[0]["child_leaf_ids"], "b")

    def test_block_bootstrap_pools_counts_reselects_comparator_and_excludes_no_topology_blocks(self) -> None:
        def stats(exact: int, topology_total: int, topology_preserved: int) -> dict[str, int]:
            row = {
                "leaf_count": 2, "parent_count": 1, "mapped_leaf_count": 2, "assigned_leaf_count": 2,
                "truth_group_count": 1, "exact_group_count": exact, "complete_group_count": exact,
                "truth_pair_count": 1, "correct_pair_count": exact, "predicted_pair_count": 1,
                "incorrect_predicted_pair_count": 1 - exact, "fragmentation_count_sum": 1,
                "left_error_sum": 0, "right_error_sum": 0, "topology_total": topology_total,
                "topology_preserved": topology_preserved,
            }
            for tolerance in (5, 10, 25, 50):
                row[f"boundary_within_{tolerance}_count"] = exact
            return row
        chromosome_stats = {
            "CONSENSUS_COLLINEARITY": {"ChrA": stats(1, 1, 0), "ChrB": stats(1, 0, 0)},
            "EVIDENCE_SHUFFLE_NULL": {"ChrA": stats(0, 1, 0), "ChrB": stats(0, 0, 0)},
            "POSITIVE_ONLY_GAP20": {"ChrA": stats(1, 1, 0), "ChrB": stats(0, 0, 0)},
            "POSITIVE_ONLY_GAP100": {"ChrA": stats(0, 1, 1), "ChrB": stats(1, 0, 0)},
        }
        uncertainty = evaluate_t1.promotion_uncertainty(self.config, chromosome_stats)
        exact = uncertainty["metrics"]["exact_truth_group_recovery"]
        self.assertTrue(exact["comparator_reselected_per_replicate"])
        self.assertGreater(exact["comparator_selection_counts"]["POSITIVE_ONLY_GAP20"], 0)
        self.assertGreater(exact["comparator_selection_counts"]["POSITIVE_ONLY_GAP100"], 0)
        topology = uncertainty["metrics"]["truth_topology_preservation"]["candidate"]
        self.assertTrue(topology["evaluable"])
        self.assertGreater(topology["valid_replicates"], 0)
        self.assertLess(topology["valid_replicates"], self.config["evaluation"]["bootstrap_replicates"])
        self.assertEqual(topology["mean"], 0.0)

    def test_full_synthetic_evaluator_writes_strata_uncertainty_and_stop_gates(self) -> None:
        public = [public_row("a", 10, 30), public_row("b", 100, 120), public_row("c", 1000, 1020), public_row("d", 1100, 1120)]
        truth = []
        for leaf, group, pstart, pend, seqid in [("a", "g1", 10, 120, "Chr1"), ("b", "g1", 10, 120, "Chr1"), ("c", "g2", 1000, 1120, "Chr1"), ("d", "g2", 1000, 1120, "Chr1")]:
            truth.append({"leaf_id": leaf, "seqid": seqid, "rm_id": group, "truth_group_id": group, "truth_parent_start0": str(pstart), "truth_parent_end0": str(pend), "class_root": "LTR", "repeat_name": "R", "truth_strand": "+", "overlap_marker": "False", "row_count_bin": "two"})
        evidence = [{"leaf_id": leaf, "mapping_status": "MAPPED", "consensus_id": "C", "consensus_strand": "+", "consensus_start0": str(index * 20), "consensus_end0": str(index * 20 + 10), "consensus_length": "100", "seed_coverage": "1", "inlier_seed_count": "5", "second_seed_coverage": "0"} for index, leaf in enumerate(["a", "b", "c", "d"])]
        candidate = [
            {"parent_id": "p1", "seqid": "Chr1", "start0": "10", "end0": "120", "child_leaf_ids": "a,b", "child_count": "2", "partition_kind": "CONSENSUS_COLLINEARITY"},
            {"parent_id": "p2", "seqid": "Chr1", "start0": "1000", "end0": "1120", "child_leaf_ids": "c,d", "child_count": "2", "partition_kind": "CONSENSUS_COLLINEARITY"},
        ]
        null = [
            {"parent_id": f"n_{leaf}", "seqid": "Chr1", "start0": row["start0"], "end0": row["end0"], "child_leaf_ids": leaf, "child_count": "1", "partition_kind": "EVIDENCE_SHUFFLE_NULL"}
            for leaf, row in zip(["a", "b", "c", "d"], public)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            public_path, truth_path, evidence_path = tmp / "public.tsv", tmp / "truth.tsv", tmp / "evidence.tsv"
            candidate_path, null_path = tmp / "candidate.tsv", tmp / "null.tsv"
            write_tsv(public_path, public, build_sample.PUBLIC_FIELDS)
            write_tsv(truth_path, truth, build_sample.TRUTH_FIELDS)
            write_tsv(evidence_path, evidence, map_consensus_evidence.EVIDENCE_FIELDS)
            write_tsv(candidate_path, candidate, partition_collinearity.PARENT_FIELDS)
            write_tsv(null_path, null, partition_collinearity.PARENT_FIELDS)
            metrics = evaluate_t1.evaluate_all(self.config, public_path, truth_path, evidence_path, {"CONSENSUS_COLLINEARITY": candidate_path, "EVIDENCE_SHUFFLE_NULL": null_path}, tmp)
            self.assertIn("paired_bootstrap_uncertainty", metrics)
            self.assertEqual(set(metrics["paired_bootstrap_uncertainty"]["metrics"]), set(self.config["promotion_metrics"]))
            for metric, spec in self.config["promotion_metrics"].items():
                entry = metrics["paired_bootstrap_uncertainty"]["metrics"][metric]
                self.assertIn("candidate", entry)
                if spec["comparator_required"]:
                    self.assertIn("candidate_minus_comparator_max", entry)
            self.assertTrue((tmp / "method_stratum_metrics.tsv").is_file())
            self.assertFalse(metrics["whole_genome_metrics_authorized"])
            self.assertEqual(metrics["methods"]["CONSENSUS_COLLINEARITY"]["leaf_retention"], 1.0)
            self.assertNotIn("MERGE_STRICT", metrics["methods"])
            self.assertNotIn("MERGE_LOOSE", metrics["methods"])
            for tolerance in (5, 10, 25, 50):
                self.assertIn(f"boundary{tolerance}_delta_over_comparator_max", metrics["stop_gate_checks"])
            self.assertIn("truth_topology_minimum", metrics["stop_gate_checks"])
            self.assertIn("truth_topology_delta_over_comparator_max", metrics["stop_gate_checks"])
            with self.assertRaisesRegex(ValueError, "unexpected"):
                evaluate_t1.validate_metrics_payload({**metrics, "unreviewed_top_level_metric": 1.0}, self.config)

    def test_non_slurm_runner_rejects_before_asset_access(self) -> None:
        runner = HERE / "run_audit.py"
        env = dict(os.environ)
        env.pop("SLURM_JOB_ID", None)
        process = subprocess.run([sys.executable, str(runner), "--root", "/definitely/missing", "--config", "/definitely/missing/config", "--environment-snapshot", "/definitely/missing/env", "--owner-token", "synthetic"], text=True, capture_output=True, env=env)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("positive numeric SLURM_JOB_ID required", process.stderr)

    def test_runtime_resource_contract_is_exact_and_fail_closed(self) -> None:
        env = {
            "SLURM_CPUS_PER_TASK": "8", "SLURM_JOB_PARTITION": "private-teodoro-gpu",
            "SLURM_MEM_PER_NODE": "32768", "SLURM_GPUS_ON_NODE": "0", "CUDA_VISIBLE_DEVICES": "",
        }
        run_audit.validate_runtime_resources(self.config, env)
        for key, bad in [("SLURM_CPUS_PER_TASK", "7"), ("SLURM_MEM_PER_NODE", "32000"), ("SLURM_JOB_PARTITION", "public-cpu"), ("SLURM_GPUS_ON_NODE", "1")]:
            broken = dict(env)
            broken[key] = bad
            with self.assertRaises(RuntimeError):
                run_audit.validate_runtime_resources(self.config, broken)
        redacted = run_audit.redacted_argv(["run", "--owner-token", "secret", "--config", "x"])
        self.assertNotIn("secret", redacted)
        self.assertIn("<REDACTED_OWNER_TOKEN>", redacted)

    def test_runtime_walltime_is_exact_and_missing_short_long_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = pathlib.Path(tmp) / "job.txt"
            snapshot.write_text("JobId=123 TimeLimit=02:00:00 Partition=private-teodoro-gpu\n")
            run_audit.validate_runtime_walltime(snapshot, 7200)
            for text in (
                "JobId=123 Partition=private-teodoro-gpu\n",
                "JobId=123 TimeLimit=01:59:59\n",
                "JobId=123 TimeLimit=02:00:01\n",
                "JobId=123 TimeLimit=UNLIMITED\n",
            ):
                snapshot.write_text(text)
                with self.assertRaises(RuntimeError):
                    run_audit.validate_runtime_walltime(snapshot, 7200)

    def test_reviewed_runtime_hashes_are_checked_pre_and_post(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            config_relative = pathlib.Path("configs") / f"{HERE.name}.yaml"
            paths = [config_relative, *map(pathlib.Path, self.config["runtime_code_files"])]
            for relative in paths:
                source = ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            reviewed = {relative.as_posix(): sha256_file(root / relative) for relative in paths}
            gate_path = root / "outputs" / HERE.name / "code_review_gate.json"
            atomic_write_json(gate_path, {"verdict": "PASS", "blockers_open": 0, "reviewed_files": reviewed})
            before = runtime_hashes.verify_reviewed_runtime(root, root / config_relative, HERE.name)
            after = runtime_hashes.verify_reviewed_runtime(root, root / config_relative, HERE.name)
            runtime_hashes.assert_same_reviewed_runtime(before, after)
            victim = root / f"scripts/experiments/{HERE.name}/partition_collinearity.py"
            victim.write_text(victim.read_text() + "\n# drift\n")
            with self.assertRaisesRegex(RuntimeError, "hash drift"):
                runtime_hashes.verify_reviewed_runtime(root, root / config_relative, HERE.name)
            changed_gate = json.loads(gate_path.read_text())
            changed_gate["note"] = "post-preflight drift"
            atomic_write_json(gate_path, changed_gate)
            with self.assertRaises(RuntimeError):
                runtime_hashes.assert_same_reviewed_runtime(before, {**before, "gate_sha256": sha256_file(gate_path)})

    def test_wrapper_failure_requires_owner_and_never_overwrites_runner_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            output = root / "outputs" / HERE.name
            lock = output / ".owner.lock"
            lock.mkdir(parents=True)
            (lock / "token").write_text("owner\n")
            atomic_write_json(output / "CURRENT_STATE.json", {"attempt_id": "slurm-123", "status": "RUNNING"})
            with self.assertRaises(RuntimeError):
                run_audit.record_wrapper_failure(root, "123", "not-owner", 124)
            self.assertEqual(json.loads((output / "CURRENT_STATE.json").read_text())["status"], "RUNNING")
            self.assertTrue(run_audit.record_wrapper_failure(root, "123", "owner", 124))
            self.assertEqual(json.loads((output / "CURRENT_STATE.json").read_text())["status"], "FAILED_WRAPPER")
            atomic_write_json(output / "CURRENT_STATE.json", {"attempt_id": "slurm-123", "status": "FAILED"})
            (output / "STATUS").write_text("FAILED\n")
            self.assertFalse(run_audit.record_wrapper_failure(root, "123", "owner", 2))
            self.assertEqual(json.loads((output / "CURRENT_STATE.json").read_text())["status"], "FAILED")
            self.assertEqual((output / "STATUS").read_text(), "FAILED\n")

    def test_sbatch_any_cwd_and_no_gpu(self) -> None:
        sbatch = (ROOT / "sbatch" / f"{HERE.name}.sbatch").read_text()
        self.assertIn("#SBATCH --cpus-per-task=8", sbatch)
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", sbatch)
        self.assertIn("#SBATCH --mem=32G", sbatch)
        self.assertIn("#SBATCH --time=02:00:00", sbatch)
        self.assertNotIn("--gres=gpu", sbatch)
        self.assertIn('cd "${PROJECT_ROOT}"', sbatch)
        self.assertIn(f'scripts/experiments/${{EXP_ID}}/preflight.sh', sbatch)
        self.assertIn("preflight_gate_and_tests_${SLURM_JOB_ID}.log", sbatch)
        self.assertIn("--preflight-receipt", sbatch)
        self.assertIn("--kill-after=5s 295s", sbatch)
        self.assertIn("--scheduler-snapshot", sbatch)
        self.assertIn("--runtime-prehash", sbatch)
        self.assertIn("--kill-after=30s 5940s", sbatch)
        self.assertIn('--owner-token "${LOCK_TOKEN}"', sbatch)
        self.assertIn("--record-wrapper-failure", sbatch)
        runner_source = (HERE / "run_audit.py").read_text()
        self.assertIn('stage / "COMMAND_MANIFEST.json"', runner_source)
        preflight = (HERE / "preflight.sh").read_text()
        first_child = next(line for line in preflight.splitlines() if line.startswith('"${'))
        self.assertIn("BENCHMARK_PYTHON", first_child)
        self.assertIn("runtime_hashes.py", preflight)


if __name__ == "__main__":
    unittest.main(verbosity=2)
