#!/usr/bin/env python3
import importlib.util
import gzip
import json
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path


MODULE = Path(__file__).with_name("te_unet_segmentation.py")
SPEC = importlib.util.spec_from_file_location("te_unet_segmentation", MODULE)
te_unet = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(te_unet)


class FourStateLabelTest(unittest.TestCase):
    def test_known_run_has_two_boundaries(self):
        self.assertEqual(te_unet.four_state_labels([0, 1, 1, 1, 0]), [0, 2, 1, 3, 0])

    def test_window_and_unknown_edges_are_not_boundaries(self):
        self.assertEqual(te_unet.four_state_labels([1, 1, 0, -1, 1, 1]), [1, 3, 0, -100, 1, 1])

    def test_separate_runs_remain_separate(self):
        self.assertEqual(te_unet.four_state_labels([0, 1, 0, 1, 1, 0]), [0, 3, 0, 2, 3, 0])

    def test_evaluation_rows_stop_at_matched_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.jsonl.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                for index in range(3):
                    handle.write(json.dumps({"index": index}) + "\n")
            self.assertEqual(list(te_unet.iter_jsonl_rows(path, 2)), [{"index": 0}, {"index": 1}])


class DecoupledBoundaryTargetTest(unittest.TestCase):
    def setUp(self):
        self.sequence = "A" * 1024
        self.labels = [0] * 1024
        for start, end in ((180, 260), (500, 580), (800, 860)):
            self.labels[start:end] = [1] * (end - start)

    def test_body_and_triangular_left_right_targets(self):
        targets = te_unet.decoupled_boundary_targets(self.labels, self.sequence)
        self.assertEqual(targets["body_labels"][180], 1)
        self.assertEqual(targets["body_labels"][0], 0)
        self.assertEqual(targets["boundary_centers"], [180, 259, 500, 579, 800, 859])
        left = targets["left_boundary_targets"]
        right = targets["right_boundary_targets"]
        self.assertEqual(left[180], 1.0)
        self.assertAlmostEqual(left[164], 0.0)
        self.assertAlmostEqual(left[165], 1.0 - 15.0 / 16.0)
        self.assertEqual(right[259], 1.0)
        self.assertAlmostEqual(right[275], 0.0)
        self.assertAlmostEqual(sum(left), 48.0)
        self.assertAlmostEqual(sum(right), 48.0)

    def test_edge_and_unknown_neighborhoods_are_not_boundary_loss_positions(self):
        labels = [0] * 1024
        labels[400] = -100
        sequence = "A" * 1024
        sequence = sequence[:400] + "N" + sequence[401:]
        targets = te_unet.decoupled_boundary_targets(labels, sequence)
        valid = targets["boundary_valid_mask"]
        self.assertFalse(valid[15])
        self.assertTrue(valid[16])
        self.assertTrue(valid[17])
        self.assertFalse(valid[400])
        self.assertFalse(valid[384])
        self.assertFalse(valid[416])
        self.assertEqual(targets["body_labels"][400], te_unet.IGNORE)

    def test_overlapping_left_right_centers_are_retained(self):
        labels = [0] * 1024
        labels[400] = 1
        targets = te_unet.decoupled_boundary_targets(labels, "A" * 1024)
        self.assertEqual(targets["boundary_centers"], [400, 400])
        self.assertEqual(targets["true_centers_by_side"], {"left": [400], "right": [400]})
        self.assertEqual(targets["left_boundary_targets"][400], 1.0)
        self.assertEqual(targets["right_boundary_targets"][400], 1.0)

    def test_shuffled_control_is_deterministic_shifted_and_mass_matched(self):
        true = te_unet.decoupled_boundary_targets(self.labels, self.sequence, mode="true")
        shuffled = te_unet.decoupled_boundary_targets(
            self.labels, self.sequence, mode="shuffled", seed=42,
        )
        shuffled_again = te_unet.decoupled_boundary_targets(
            self.labels, self.sequence, mode="shuffled", seed=42,
        )
        self.assertEqual(shuffled, shuffled_again)
        self.assertEqual(true["body_labels"], shuffled["body_labels"])
        self.assertTrue(all(center not in true["boundary_centers"] for center in shuffled["target_centers"]))
        self.assertAlmostEqual(
            sum(true["left_boundary_targets"]),
            sum(shuffled["left_boundary_targets"]),
        )
        self.assertAlmostEqual(
            sum(true["right_boundary_targets"]),
            sum(shuffled["right_boundary_targets"]),
        )
        for side in ("left", "right"):
            true_centers_for_side = sorted(true["true_centers_by_side"][side])
            target_centers_for_side = sorted(shuffled["target_centers_by_side"][side])
            self.assertTrue(all(
                (target - source) % 1024 == shuffled["shuffle_delta"]
                for source, target in zip(
                    true["true_centers_by_side"][side],
                    shuffled["target_centers_by_side"][side],
                )
            ))
            true_gaps = [
                right - left for left, right in zip(true_centers_for_side, true_centers_for_side[1:])
            ] + [1024 + true_centers_for_side[0] - true_centers_for_side[-1]]
            target_gaps = [
                right - left for left, right in zip(target_centers_for_side, target_centers_for_side[1:])
            ] + [1024 + target_centers_for_side[0] - target_centers_for_side[-1]]
            self.assertEqual(sorted(true_gaps), sorted(target_gaps))
        self.assertNotEqual(shuffled["shuffle_delta"], 0)

    def test_preflight_checks_all_train_and_validation_rows_without_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            labels = [0] * te_unet.WINDOW
            labels[100:200] = [1] * 100
            row = {"chr": "chrSynthetic", "start": 0, "end": te_unet.WINDOW,
                   "sequence": "A" * te_unet.WINDOW, "labels": labels}
            for split in ("train", "val"):
                split_dir = root / split
                split_dir.mkdir()
                with gzip.open(split_dir / "data.jsonl.gz", "wt", encoding="utf-8") as handle:
                    handle.write(json.dumps(row) + "\n")
            output = root / "preflight.json"
            te_unet.preflight_decoupled(SimpleNamespace(
                data_dir=root, output_json=output, boundary_target_mode="shuffled",
                seed=42, max_eval_samples=800,
            ))
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["splits"]["train"]["rows"], 1)
            self.assertEqual(
                result["splits"]["train"]["details"][0]["target_centers_by_side"],
                result["splits"]["val"]["details"][0]["target_centers_by_side"],
            )


if __name__ == "__main__":
    unittest.main()
