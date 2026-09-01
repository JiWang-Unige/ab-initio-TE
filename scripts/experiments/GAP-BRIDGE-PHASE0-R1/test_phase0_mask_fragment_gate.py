from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("phase0_mask_fragment_gate", HERE / "phase0_mask_fragment_gate.py")
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class MaskFragmentGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.lock = self.root / "feature_lock.json"
        self.evaluation = self.root / "candidate_evaluation.json"
        self.labeled = self.root / "chr19-labeled.tsv"
        self.p3 = self.root / "p3.canonical.tsv"
        self.positive = self.root / "comparator-positive.tsv"
        self.unknown = self.root / "comparator-unknown.tsv"
        self.output = self.root / "mask-fragment-gate.json"
        self.refined = self.root / "refined.canonical.tsv"
        self.selected_sidecar = self.root / "selected.tsv"
        self._write_lock()
        self._write_p3()
        self._write_comparator(self.positive, [(0, 50)])
        self._write_comparator(self.unknown, [(48, 53)])
        self._write_labeled()
        self._write_candidate_evaluation()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_lock(self) -> None:
        groups: dict[str, dict[str, object]] = {}
        for name, fields in gate.FEATURE_GROUPS.items():
            groups[name] = {
                "features": fields,
                "regularization_c": 1.0,
                "imputation_median": [0.0] * len(fields),
                "standardization_mean": [0.0] * len(fields),
                "standardization_scale": [1.0] * len(fields),
                "coefficient": [0.0] * len(fields),
                "intercept": 0.0,
                "validation": {
                    "average_precision": 0.5,
                    "operating_threshold": {"status": "NO_NONEMPTY_THRESHOLD", "threshold": None},
                },
            }
        groups["G2_FULL_LIBRARY_FREE"]["coefficient"][0] = 1.0
        groups["G2_FULL_LIBRARY_FREE"]["validation"] = {
            "average_precision": 0.8,
            "operating_threshold": {"status": "PASS", "threshold": 0.9},
        }
        self.lock.write_text(json.dumps({
            "schema": "gap_bridge_phase0_feature_lock_v1",
            "status": "PASS_TO_TEST",
            "selection_locked": True,
            "test_labels_read": False,
            "test_label_release_allowed": True,
            "selected_deployment_group": "G2_FULL_LIBRARY_FREE",
            "baselines": {
                "simple_gap_length_cutoff": {
                    "status": "PASS", "maximum_gap_length": 4,
                    "validation_average_precision": 0.9,
                },
                "A0_consensus_alignment": {"status": "ASSET_BLOCKED_PRETEST"},
            },
            "groups": groups,
        }), encoding="utf-8")

    @staticmethod
    def _write_canonical(path: Path, intervals: list[tuple[int, int]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["seqid", "start", "end", "source", "name", "score", "strand", "attributes"])
            for start, end in intervals:
                writer.writerow(["chr19", start, end, "P3", ".", ".", ".", "."])

    def _write_p3(self) -> None:
        self._write_canonical(self.p3, [(0, 10), (12, 30), (40, 50), (55, 58)])

    @staticmethod
    def _write_comparator(path: Path, intervals: list[tuple[int, int]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["seqid", "start", "end"])
            writer.writerow(["chr3", 0, 1])
            for start, end in intervals:
                writer.writerow(["chr19", start, end])

    def _write_labeled(self) -> None:
        fields = [
            "candidate_id", "seqid", "gap_start", "gap_end", "gap_length", "eligible_main", "clean_target",
            "comparator_relation", "gap_comparator_positive_bp", "gap_comparator_negative_bp",
            "gap_comparator_unknown_bp",
            "left_run_length", "right_run_length", "span_length", "touches_window_seam",
            "nearest_window_seam_abs_distance", "gap_max_homopolymer", "microhomology_bp",
        ] + list(gate.G2)
        candidates = [
            ("chr19:10-12", 10, 12, "1", gate.BRIDGE, 2, 0, 0),
            ("chr19:30-40", 30, 40, "1", gate.BRIDGE, 10, 0, 0),
            ("chr19:50-55", 50, 55, "", gate.AMBIGUOUS, 0, 2, 3),
        ]
        with self.labeled.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for candidate_id, start, end, target, relation, positive, negative, unknown in candidates:
                row = {field: "0" for field in fields}
                row.update({
                    "candidate_id": candidate_id,
                    "seqid": "chr19",
                    "gap_start": str(start),
                    "gap_end": str(end),
                    "gap_length": str(end - start),
                    "eligible_main": "1",
                    "clean_target": target,
                    "comparator_relation": relation,
                    "gap_comparator_positive_bp": str(positive),
                    "gap_comparator_negative_bp": str(negative),
                    "gap_comparator_unknown_bp": str(unknown),
                    "left_run_length": "10",
                    "right_run_length": "10",
                    "span_length": "20",
                    "touches_window_seam": "0",
                    "nearest_window_seam_abs_distance": "100",
                    "gap_max_homopolymer": "1",
                    "microhomology_bp": "0",
                })
                writer.writerow(row)

    def _write_candidate_evaluation(self, threshold: float = 0.9) -> None:
        self.evaluation.write_text(json.dumps({
            "schema": "gap_bridge_phase0_chr19_evaluation_v1",
            "status": "PARTIAL_EVALUATION_UNAVAILABLE_ASSETS",
            "test_chromosome": "chr19",
            "test_labels_read": True,
            "candidate_count": 2,
            "comparison": {
                "best_ranking_baseline": "SIMPLE_LENGTH",
                "best_operating_baseline": "SIMPLE_LENGTH",
            },
            "group_metrics": {
                "SIMPLE_LENGTH": {
                    "candidate_metrics": {
                        "threshold_kind": "maximum_gap_length",
                        "threshold": 4,
                        "selected_candidates": 1,
                    },
                },
                "G2_FULL_LIBRARY_FREE": {
                    "candidate_metrics": {
                        "threshold_kind": "score",
                        "threshold": threshold,
                        "selected_candidates": 1,
                    },
                },
            },
        }), encoding="utf-8")

    def test_locked_g2_threshold_adds_only_selected_gap_and_reports_fragment_metrics(self) -> None:
        result = gate.evaluate_mask_fragment_gate(
            self.lock, self.evaluation, self.labeled, self.p3, self.positive, self.unknown,
            60, self.output, self.refined, self.selected_sidecar,
        )
        self.assertEqual(result["status"], "PARTIAL_GATE_NO_GENE_SAFETY")
        self.assertEqual(result["excluded_unknown_candidates"], 1)
        self.assertEqual(result["comparator_unknown_source_bp"], 5)
        self.assertEqual(result["comparator_unknown_effective_bp"], 3)
        self.assertEqual(result["selected_gap_count"], 1)
        self.assertEqual(result["selected_gap_ids"], ["chr19:30-40"])
        self.assertEqual(gate.read_intervals(self.refined, 60), [(0, 10), (12, 50), (55, 58)])
        with self.selected_sidecar.open(newline="", encoding="utf-8") as handle:
            sidecar = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual([row["selected"] for row in sidecar], ["0", "1"])
        self.assertEqual(sidecar[1]["candidate_id"], "chr19:30-40")
        self.assertEqual(sidecar[1]["unknown_bp"], "0")

        metrics = result["metrics"]
        self.assertAlmostEqual(metrics["whole_mask"]["raw"]["recall"], 38 / 50)
        self.assertAlmostEqual(metrics["whole_mask"]["refined"]["recall"], 48 / 50)
        self.assertAlmostEqual(metrics["fragmentation"]["raw"]["fragments_per_truth"], 3.0)
        self.assertAlmostEqual(metrics["fragmentation"]["refined"]["fragments_per_truth"], 2.0)
        self.assertEqual(metrics["fragmentation"]["raw"]["split_truth_runs"], 1)
        self.assertEqual(metrics["fragmentation"]["refined"]["split_truth_runs"], 1)
        self.assertAlmostEqual(metrics["internal_gap_recovery"]["internal_gap_positive_bp_recall"], 10 / 12)
        self.assertAlmostEqual(metrics["internal_gap_recovery"]["internal_gap_gt5_positive_bp_recall"], 1.0)
        self.assertAlmostEqual(metrics["added_bp"]["precision"], 1.0)
        self.assertEqual(metrics["added_bp"]["precision_bootstrap"]["replicates"], 1000)
        self.assertEqual(metrics["added_bp"]["precision_bootstrap"]["seed"], 20260901)
        self.assertEqual(metrics["added_bp"]["precision_bootstrap"]["valid_replicates"], 1000)
        self.assertEqual(metrics["baseline"]["best_operating_baseline"], "SIMPLE_LENGTH")
        self.assertEqual(metrics["baseline"]["selected_candidates"], 1)
        self.assertAlmostEqual(metrics["baseline"]["whole_mask"]["refined"]["recall"], 40 / 50)
        self.assertEqual(result["prospective_gate"]["status"], "NOT_EVALUATED")

    def test_candidate_evaluation_threshold_is_frozen_and_not_rematched_on_chr19(self) -> None:
        self._write_candidate_evaluation(threshold=0.8)
        with self.assertRaisesRegex(ValueError, "threshold differs"):
            gate.evaluate_mask_fragment_gate(
                self.lock, self.evaluation, self.labeled, self.p3, self.positive, self.unknown,
                60, self.output, self.refined, self.selected_sidecar,
            )

    def test_reports_g2_only_when_no_frozen_precision_floor_baseline_exists(self) -> None:
        lock = json.loads(self.lock.read_text(encoding="utf-8"))
        lock["baselines"]["simple_gap_length_cutoff"] = {
            "status": "NO_NONEMPTY_THRESHOLD", "maximum_gap_length": None,
            "validation_average_precision": 0.9,
        }
        self.lock.write_text(json.dumps(lock), encoding="utf-8")
        evaluation = json.loads(self.evaluation.read_text(encoding="utf-8"))
        evaluation["comparison"]["best_operating_baseline"] = None
        self.evaluation.write_text(json.dumps(evaluation), encoding="utf-8")
        result = gate.evaluate_mask_fragment_gate(
            self.lock, self.evaluation, self.labeled, self.p3, self.positive, self.unknown,
            60, self.output, self.refined, self.selected_sidecar,
        )
        self.assertEqual(result["operating_route"], "G2_ONLY_SAFE_OPERATING_POINT")
        self.assertEqual(result["metrics"]["baseline"]["status"], "NO_BASELINE_OPERATING_POINT")

    def test_rejects_consumed_feature_lock(self) -> None:
        lock = json.loads(self.lock.read_text(encoding="utf-8"))
        lock["test_labels_read"] = True
        self.lock.write_text(json.dumps(lock), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "test_labels_read"):
            gate.evaluate_mask_fragment_gate(
                self.lock, self.evaluation, self.labeled, self.p3, self.positive, self.unknown,
                60, self.output, self.refined, self.selected_sidecar,
            )


if __name__ == "__main__":
    unittest.main()
