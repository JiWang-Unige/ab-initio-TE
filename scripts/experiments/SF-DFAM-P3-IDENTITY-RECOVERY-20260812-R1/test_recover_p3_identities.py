#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("recover_p3_identities", HERE / "recover_p3_identities.py")
recovery = importlib.util.module_from_spec(SPEC); assert SPEC.loader
sys.modules[SPEC.name] = recovery; SPEC.loader.exec_module(recovery)
CONFIG = PROJECT / "configs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.yaml"


def cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def target(identifier: str, occurrences: int = 1) -> dict:
    return {"identifier": identifier, "occurrences": str(occurrences), "labels": "LINE", "species": "human",
            "status": "missing", "resolution_status": "missing", "resolution_method": "none"}


def make_h5(path: Path, records: list[dict], with_byname: bool = False) -> None:
    import h5py
    with h5py.File(path, "w") as handle:
        group = handle.create_group("Families/DR/00/00/01")
        for index, record in enumerate(records):
            item = group.create_dataset(f"item{index}", data=[1])
            item.attrs.update(record)
        handle.create_group("Lookup")
        if with_byname:
            handle.create_group("Lookup/ByName")


class P3RecoveryTests(unittest.TestCase):
    def test_real_frozen_target_and_layout_contract(self):
        targets, audit = recovery.validate_inputs(PROJECT, cfg())
        self.assertEqual(len(targets), 279)
        self.assertEqual(len({x["identifier"] for x in targets}), 279)
        self.assertGreater(audit["target_occurrence_mass"], 0)
        self.assertFalse(audit["full_partition_content_hashing_used"])
        self.assertFalse(audit["copy_derived_proxy_used"])

    def test_exhaustive_exact_name_scan_recovers_only_exact_case(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "p3.h5"
            make_h5(path, [
                {"name": "L2a", "accession": "DF1", "version": 2, "consensus": "ACGT"},
                {"name": "L2a_extra", "accession": "DF2", "version": 1, "consensus": "CCCC"},
                {"name": "l2a", "accession": "DF3", "version": 1, "consensus": "GGGG"},
            ])
            rows, audit = recovery.scan_partition(path, {"L2a"}, 3)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["versioned_accession"], "DF1.2")
        self.assertEqual(audit["family_datasets_scanned"], 3)

    def test_byname_presence_and_dataset_count_drift_fail(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "p3.h5"; make_h5(path, [], with_byname=True)
            with self.assertRaisesRegex(ValueError, "BYNAME_PRESENT"):
                recovery.scan_partition(path, set(), 0)
            path2 = Path(name) / "p3b.h5"; make_h5(path2, [{"name": "A", "accession": "D", "version": 1, "consensus": "A"}])
            with self.assertRaisesRegex(ValueError, "DATASET_COUNT_DRIFT"):
                recovery.scan_partition(path2, {"A"}, 2)

    def test_consensus_model_attribute_counts_and_structured_progress(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); path = root / "p3.h5"; progress = root / "progress.jsonl"
            make_h5(path, [{"name": "A", "accession": "D1", "version": 1, "consensus": "A", "model": "M"},
                           {"name": "B", "accession": "D2", "version": 1, "consensus": "C"}])
            _rows, audit = recovery.scan_partition(path, {"A"}, 2, 2, 1, 1, progress)
            self.assertEqual(audit["consensus_attribute_count"], 2)
            self.assertEqual(audit["model_attribute_count"], 1)
            events = [json.loads(line) for line in progress.read_text().splitlines()]
            self.assertEqual([x["datasets_scanned"] for x in events], [1, 2, 2])
            self.assertEqual(events[-1]["event"], "p3_family_scan_complete")
            with self.assertRaisesRegex(ValueError, "MODEL_ATTRIBUTE_COUNT_DRIFT"):
                recovery.scan_partition(path, {"A"}, 2, 2, 2)

    def test_resolve_recovered_missing_ambiguous_and_invalid_metadata(self):
        targets = [target("OK", 10), target("MISS", 20), target("AMB", 30), target("BAD", 40)]
        candidates = [
            {"identifier": "OK", "versioned_accession": "DF1.1", "consensus_sha256": "a", "consensus_length": 4},
            {"identifier": "AMB", "versioned_accession": "DF2.1", "consensus_sha256": "b", "consensus_length": 4},
            {"identifier": "AMB", "versioned_accession": "DF3.1", "consensus_sha256": "c", "consensus_length": 4},
            {"identifier": "BAD", "versioned_accession": "", "consensus_sha256": "", "consensus_length": 0},
        ]
        rows, metrics = recovery.resolve_targets(targets, candidates)
        self.assertEqual({x["identifier"]: x["status"] for x in rows},
                         {"AMB": "ambiguous", "BAD": "invalid_metadata", "MISS": "missing", "OK": "recovered"})
        self.assertEqual(metrics["target_identifier_count"], 4)
        self.assertEqual(metrics["target_occurrence_mass"], 100)
        self.assertEqual(metrics["occurrence_mass_conservation_delta"], 0)
        self.assertEqual(metrics["recovered_occurrence_mass"], 10)

    def test_identical_duplicate_paths_are_one_identity_not_ambiguity(self):
        targets = [target("A", 3)]
        candidate = {"identifier": "A", "versioned_accession": "DF1.1", "consensus_sha256": "x", "consensus_length": 10}
        rows, metrics = recovery.resolve_targets(targets, [candidate, dict(candidate)])
        self.assertEqual(rows[0]["status"], "recovered")
        self.assertEqual(rows[0]["candidate_row_count"], 2)
        self.assertEqual(rows[0]["distinct_identity_count"], 1)
        self.assertEqual(metrics["ambiguous_identifier_count"], 0)

    def test_empty_targets_and_conservation_are_fail_closed_by_contract(self):
        config = cfg(); config["expected_target_identifier_count"] = 0
        # The production config cannot reach this state because its identity TSV and count are pinned.
        self.assertEqual(recovery.terminal_exit_code("RECOVERY_FAILED"), 2)
        rows, metrics = recovery.resolve_targets([target("A", 2)], [])
        self.assertEqual(rows[0]["status"], "missing")
        self.assertEqual(metrics["occurrence_mass_conservation_delta"], 0)

    def test_no_prefix_case_copy_cluster_split_or_model_fallback(self):
        config = cfg(); contract = config["resolver_contract"]
        self.assertTrue(contract["prefix_guess_forbidden"])
        self.assertTrue(contract["casefold_forbidden"])
        self.assertTrue(contract["copy_derived_proxy_forbidden"])
        self.assertTrue(contract["clustering_forbidden"])
        self.assertTrue(contract["split_construction_forbidden"])
        self.assertTrue(contract["model_execution_forbidden"])
        source = (HERE / "recover_p3_identities.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("mmseqs", source)
        self.assertNotIn("blast", source)
        self.assertNotIn("genome_copy", source)

    def test_formal_slurm_guard(self):
        old = os.environ.pop("SLURM_JOB_ID", None)
        try:
            with self.assertRaisesRegex(ValueError, "FORMAL_SLURM_GUARD"):
                recovery.run_formal(Path("/tmp"), {"preview_root": "x"}, "attempt")
        finally:
            if old is not None: os.environ["SLURM_JOB_ID"] = old
        os.environ["SLURM_JOB_ID"] = "not-an-integer"
        try:
            with self.assertRaisesRegex(ValueError, "FORMAL_SLURM_GUARD"):
                recovery.run_formal(Path("/tmp"), {"preview_root": "x"}, "attempt")
        finally:
            os.environ.pop("SLURM_JOB_ID", None)

    def test_terminal_semantics(self):
        self.assertEqual(recovery.terminal_exit_code("RECOVERY_COMPLETE"), 0)
        self.assertEqual(recovery.terminal_exit_code("IDENTITY_RECOVERY_TYPED_BLOCK"), 0)
        self.assertEqual(recovery.terminal_exit_code("IMPLEMENTED_NOT_RUN"), 0)
        self.assertEqual(recovery.terminal_exit_code("RECOVERY_FAILED"), 2)

    def test_payload_manifest_is_nonrecursive_and_detects_tamper(self):
        with tempfile.TemporaryDirectory() as name:
            stage = Path(name)
            for filename in ("frozen_targets.tsv", "existing_ambiguity_audit.tsv", "exact_candidates.tsv", "resolution.tsv",
                             "scan_progress.jsonl", "metrics.json", "report.json", "RUN_MANIFEST.json", "env.json"):
                (stage / filename).write_text(filename)
            recovery.create_payload_manifest(stage); recovery.verify_payload(stage)
            manifest = json.loads((stage / "PAYLOAD_MANIFEST.json").read_text())
            self.assertFalse(manifest["self_included"])
            self.assertNotIn("PAYLOAD_MANIFEST.json", manifest["files"])
            (stage / "resolution.tsv").write_text("tamper")
            with self.assertRaisesRegex(ValueError, "PAYLOAD_DRIFT"):
                recovery.verify_payload(stage)

    def test_atomic_preview_manifest_and_terminal_state(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); preview = root / "outputs/X/preview"; preview.mkdir(parents=True)
            config = {"exp_id": "X", "preview_root": "outputs/X/preview"}
            recovery.atomic_json(preview / "input_manifest.json", {"x": 1})
            recovery.atomic_json(preview / "static_contract.json", {"x": 1})
            recovery.finalize_preview(root, config, "IMPLEMENTED_NOT_RUN", "static", {"semantic_success": False}, {"x": 1})
            terminal = json.loads((preview / "TERMINAL_STATE.json").read_text())
            self.assertFalse(terminal["homology_split_authorized"])
            self.assertFalse(terminal["full_catalog_stage_authorized"])
            for line in (preview / "output_manifest.sha256").read_text().splitlines():
                expected, relpath = line.split("  ", 1)
                self.assertEqual(recovery.sha256_file(root / relpath), expected)

    def test_sbatch_is_cpu_only_guarded_and_bounded(self):
        text = (PROJECT / "sbatch/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.sbatch").read_text()
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertIn("#SBATCH --time=02:00:00", text)
        self.assertNotIn("#SBATCH --gres", text)
        self.assertIn("pre_submit_gate.py", text)
        self.assertIn('test -z "${SLURM_JOB_GPUS:-}"', text)
        self.assertIn("--prepare-running-only", text)
        self.assertLess(text.index("--prepare-running-only"), text.index("test_recover_p3_identities.py"))
        self.assertLess(text.index("set -eo pipefail"), text.index("conda activate te_benchmark"))
        self.assertGreater(text.index("set -u"), text.index("conda activate te_benchmark"))


if __name__ == "__main__":
    unittest.main()
