#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("te_span_mlm", HERE / "te_span_mlm.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

BUILDER_SPEC = importlib.util.spec_from_file_location(
    "build_annotation_span_corpus", HERE / "build_annotation_span_corpus.py"
)
BUILDER = importlib.util.module_from_spec(BUILDER_SPEC)
assert BUILDER_SPEC.loader
BUILDER_SPEC.loader.exec_module(BUILDER)


def masks(interior=(100, 1000), boundary=(1000, 1100), flank=(1100, 2200)):
    return {
        "interior": [interior[0] <= i < interior[1] for i in range(MODULE.WINDOW)],
        "boundary": [boundary[0] <= i < boundary[1] for i in range(MODULE.WINDOW)],
        "flank": [flank[0] <= i < flank[1] for i in range(MODULE.WINDOW)],
    }


class SpanMaskMechanismTests(unittest.TestCase):
    def test_spans_are_contiguous_and_stratum_pure(self):
        result = MODULE.sample_contiguous_spans(masks(), target_fraction=0.15, span_length=32, seed=7)
        selected = result["selected"]
        for row in result["spans"]:
            start, end = int(row["start"]), int(row["end"])
            self.assertEqual(end - start, 32)
            self.assertTrue(all(selected[start:end]))
            stratum = row["stratum"]
            for index in range(start, end):
                self.assertTrue(masks()[stratum][index])
        runs = MODULE._runs(selected)
        self.assertEqual(sum(end - start for start, end in runs), result["selected_bp"])
        intervals = sorted((int(row["start"]), int(row["end"])) for row in result["spans"])
        self.assertTrue(all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:])))

    def test_unknown_and_n_positions_are_not_selected(self):
        unknown = [500 <= i < 540 for i in range(MODULE.WINDOW)]
        n_mask = [1500 <= i < 1540 for i in range(MODULE.WINDOW)]
        result = MODULE.sample_contiguous_spans(
            masks(), unknown_mask=unknown, n_mask=n_mask, target_fraction=0.15, span_length=32, seed=7
        )
        self.assertFalse(any(selected and blocked for selected, blocked in zip(result["selected"], unknown)))
        self.assertFalse(any(selected and blocked for selected, blocked in zip(result["selected"], n_mask)))

    def test_mlm_labels_remain_original_nucleotide_targets(self):
        try:
            import torch
        except ModuleNotFoundError:
            self.skipTest("torch is available in the te_benchmark training environment")

        result = MODULE.sample_contiguous_spans(masks(), target_fraction=0.15, span_length=32, seed=7)
        input_ids = torch.ones((1, MODULE.WINDOW), dtype=torch.long)
        attention = torch.ones_like(input_ids)
        special = torch.zeros_like(input_ids)
        masked, labels, selected = MODULE.apply_span_mask(
            input_ids,
            attention,
            special,
            torch.tensor([result["selected"]], dtype=torch.bool),
            n_token_ids={4},
            pad_token_id=None,
            mask_token_id=9,
            acgt_token_ids=(1, 2, 3, 4),
            vocab_size=10,
            generator=torch.Generator().manual_seed(7),
        )
        self.assertGreater(int(selected.sum()), 0)
        self.assertTrue(torch.equal(labels[selected], input_ids[selected]))
        self.assertTrue(torch.equal(labels[~selected], torch.full_like(labels[~selected], -100)))
        self.assertTrue(torch.equal(masked[~selected], input_ids[~selected]))

    def test_overlapping_strata_are_rejected(self):
        bad = masks()
        bad["boundary"][150] = True
        with self.assertRaisesRegex(ValueError, "candidate strata overlap"):
            MODULE.sample_contiguous_spans(bad, target_fraction=0.15, span_length=32)

    def test_boundary_is_taken_from_explicit_mask_not_label_transition(self):
        candidate = masks(interior=(100, 1000), boundary=(3000, 3100), flank=(1100, 2200))
        result = MODULE.sample_contiguous_spans(candidate, target_fraction=0.15, span_length=32, seed=3)
        boundary_spans = [row for row in result["spans"] if row["stratum"] == "boundary"]
        self.assertTrue(boundary_spans)
        self.assertTrue(all(3000 <= int(row["start"]) and int(row["end"]) <= 3100 for row in boundary_spans))

    def test_wrong_window_length_is_rejected(self):
        bad = masks()
        bad["flank"] = bad["flank"][:-1]
        with self.assertRaisesRegex(ValueError, "flank length"):
            MODULE.sample_contiguous_spans(bad, target_fraction=0.15, span_length=32)

    def test_copy_level_gate(self):
        self.assertTrue(MODULE.metadata_allows_training({"copy_level": True}))
        self.assertTrue(MODULE.metadata_allows_training({"label_level": "copy_level"}))
        self.assertFalse(MODULE.metadata_allows_training({"copy_level": False}))
        self.assertFalse(MODULE.metadata_allows_training({"label_level": "reference_run"}))

    def test_default_stratum_weights_are_frozen(self):
        self.assertEqual(MODULE.STRATUM_WEIGHTS, {
            "interior": 0.45,
            "boundary": 0.30,
            "flank": 0.25,
        })

    def test_smoke_exercises_explicit_masks_and_exclusions(self):
        result = MODULE.smoke()
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(result["selected_bp"], 0)
        self.assertEqual(result["unknown_excluded_bp"], 50)
        self.assertEqual(result["n_excluded_bp"], 40)

    def test_reference_annotation_run_gate(self):
        self.assertTrue(MODULE.metadata_allows_training({
            "annotation_level": "reference_annotation_run",
            "biological_copy_claim": False,
        }))
        self.assertFalse(MODULE.metadata_allows_training({
            "annotation_level": "reference_annotation_run",
            "biological_copy_claim": True,
        }))

    def test_corpus_audit_requires_full_record_count_and_reports_selected_mass(self):
        record = {
            "sequence": "A" * MODULE.WINDOW,
            "candidate_masks": masks(),
            "unknown_mask": [False] * MODULE.WINDOW,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corpus.jsonl"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            result = MODULE.audit_corpus(path, 1)
            self.assertEqual(result["status"], "PASS")
            self.assertGreater(result["selected_bp"], 0)
            self.assertAlmostEqual(sum(result["selected_span_fractions"].values()), 1.0)
            with self.assertRaisesRegex(ValueError, "expected exactly 2 records"):
                MODULE.audit_corpus(path, 2)

    def test_strict_selection_refills_scarce_stratum(self):
        candidate = {
            "interior": [100 <= i < 132 for i in range(MODULE.WINDOW)],
            "boundary": [1000 <= i < 1016 for i in range(MODULE.WINDOW)],
            "flank": [2000 <= i < 2320 for i in range(MODULE.WINDOW)],
        }
        result = MODULE.sample_contiguous_spans(
            candidate, target_fraction=0.03, span_length=32, seed=7, strict_selected_bp=True
        )
        self.assertEqual(result["selected_bp"], result["target_selected_bp"])
        self.assertGreater(result["selected_by_stratum"]["flank"], 2)

    def test_strict_selection_reports_real_shortage(self):
        candidate = {
            "interior": [100 <= i < 116 for i in range(MODULE.WINDOW)],
            "boundary": [1000 <= i < 1016 for i in range(MODULE.WINDOW)],
            "flank": [2000 <= i < 2016 for i in range(MODULE.WINDOW)],
        }
        with self.assertRaisesRegex(ValueError, "no contiguous eligible span"):
            MODULE.sample_contiguous_spans(
                candidate, target_fraction=0.1, span_length=32, seed=7, strict_selected_bp=True
            )

    def test_interval_sampler_does_not_waste_a_packable_span(self):
        candidate = {
            "interior": [100 <= i < 164 for i in range(MODULE.WINDOW)],
            "boundary": [False] * MODULE.WINDOW,
            "flank": [False] * MODULE.WINDOW,
        }
        result = MODULE.sample_contiguous_spans(
            candidate,
            target_fraction=64 / MODULE.WINDOW,
            span_length=32,
            seed=7,
            strict_selected_bp=True,
        )
        self.assertEqual(result["selected_bp"], 64)

    def test_refill_preserves_the_maximum_packable_set(self):
        candidate = {
            "interior": [100 <= i < 132 for i in range(MODULE.WINDOW)],
            "boundary": [1000 <= i < 1032 for i in range(MODULE.WINDOW)],
            "flank": [2000 <= i < 3152 for i in range(MODULE.WINDOW)],
        }
        result = MODULE.sample_contiguous_spans(
            candidate,
            target_fraction=0.15,
            span_length=32,
            seed=7,
            strict_selected_bp=True,
        )
        self.assertEqual(result["selected_bp"], 38 * 32)

    def test_mask_budget_is_fraction_of_callable_window_not_candidate_subset(self):
        candidate = masks(interior=(100, 2100), boundary=(3000, 3100), flank=(4000, 6000))
        result = MODULE.sample_contiguous_spans(
            candidate, target_fraction=0.15, span_length=32, seed=7
        )
        self.assertEqual(result["callable_bp"], MODULE.WINDOW)
        self.assertEqual(result["target_selected_bp"], 38 * 32)
        self.assertEqual(result["selected_bp"], 38 * 32)


class AnnotationSpanCorpusTests(unittest.TestCase):
    def _record(self, positive_runs, unknown=(), n_positions=()):
        labels = [0] * BUILDER.WINDOW
        for start, end in positive_runs:
            labels[start:end] = [1] * (end - start)
        for start, end in unknown:
            labels[start:end] = [-100] * (end - start)
        sequence = ["A"] * BUILDER.WINDOW
        for start, end in n_positions:
            sequence[start:end] = ["N"] * (end - start)
        return {"sequence": "".join(sequence), "labels": labels, "chr": "chrTest", "start": 0, "end": BUILDER.WINDOW}

    def test_boundary_spans_cross_only_single_known_transition(self):
        record = self._record([(300, 500), (900, 1100)])
        result = BUILDER.build_record(record)
        self.assertEqual(
            result["boundary_intervals"],
            [[276, 324], [476, 524], [876, 924], [1076, 1124]],
        )
        boundary = result["candidate_masks"]["boundary"]
        transitions = (300, 500, 900, 1100)
        for row in result["boundary_intervals"]:
            left, right = row
            edge = min(transitions, key=lambda value: abs(value - (left + right) // 2))
            for start in range(left, right - MODULE.SPAN_LENGTH + 1):
                end = start + MODULE.SPAN_LENGTH
                self.assertTrue(start < edge < end)
                self.assertGreaterEqual(edge - start, BUILDER.BOUNDARY_MIN_EACH_SIDE)
                self.assertGreaterEqual(end - edge, BUILDER.BOUNDARY_MIN_EACH_SIDE)
        for start in MODULE._span_starts(boundary, MODULE.SPAN_LENGTH):
            end = start + MODULE.SPAN_LENGTH
            self.assertTrue(any(start < edge < end for edge in transitions))
        for index, value in enumerate(result["candidate_masks"]["interior"]):
            self.assertFalse(value and boundary[index])

    def test_window_edge_unknown_and_n_transitions_are_not_boundaries(self):
        edge_result = BUILDER.build_record(self._record([(0, 300)]))
        self.assertEqual(edge_result["boundary_intervals"], [[276, 324]])
        self.assertNotIn([-24, 24], edge_result["boundary_intervals"])

        unknown_result = BUILDER.build_record(self._record([(300, 500)], unknown=((299, 300),)))
        self.assertNotIn([276, 324], unknown_result["boundary_intervals"])
        self.assertEqual(unknown_result["boundary_intervals"], [[476, 524]])

        n_result = BUILDER.build_record(self._record([(800, 1000)], n_positions=((799, 800),)))
        self.assertNotIn([776, 824], n_result["boundary_intervals"])
        self.assertEqual(n_result["boundary_intervals"], [[976, 1024]])

    def test_boundary_with_another_run_in_clean_outer_128_is_rejected(self):
        result = BUILDER.build_record(self._record([(300, 500), (600, 700)]))
        self.assertEqual(result["boundary_intervals"], [[276, 324], [676, 724]])
        self.assertNotIn([476, 524], result["boundary_intervals"])
        self.assertNotIn([576, 624], result["boundary_intervals"])

    def test_long_flanks_do_not_overlap_another_run_boundary_bucket(self):
        result = BUILDER.build_record(self._record([(300, 500), (700, 900)]))
        boundary = result["candidate_masks"]["boundary"]
        flank = result["candidate_masks"]["flank"]
        self.assertFalse(any(left and right for left, right in zip(boundary, flank)))

    def test_flank_is_not_emitted_for_a_boundary_with_ambiguous_candidate_band(self):
        result = BUILDER.build_record(self._record([(300, 340)]))
        self.assertEqual(result["boundary_intervals"], [])
        self.assertEqual(sum(result["candidate_masks"]["boundary"]), 0)
        self.assertEqual(sum(result["candidate_masks"]["flank"]), 0)

    def test_interior_is_outside_64bp_exclusion_and_flank_is_64_to_256bp(self):
        result = BUILDER.build_record(self._record([(300, 500)]))
        interior_runs = MODULE._runs(result["candidate_masks"]["interior"])
        flank_runs = MODULE._runs(result["candidate_masks"]["flank"])
        self.assertEqual(interior_runs, [(364, 436)])
        self.assertEqual(flank_runs, [(44, 237), (564, 757)])
        for start, end in flank_runs:
            self.assertTrue(end <= 237 or start >= 564)

    def test_separated_runs_are_not_connected_by_candidate_masks(self):
        result = BUILDER.build_record(self._record([(300, 500), (650, 850)]))
        interior_runs = MODULE._runs(result["candidate_masks"]["interior"])
        boundary_runs = MODULE._runs(result["candidate_masks"]["boundary"])
        self.assertFalse(any(start < 575 < end for start, end in interior_runs))
        self.assertFalse(any(start < 575 < end for start, end in boundary_runs))

    def test_metadata_declares_reference_run_semantics(self):
        record = self._record([(100, 300)])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            output_path = root / "output.jsonl"
            metadata_path = root / "metadata.json"
            input_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            metadata = BUILDER.build(
                type("Args", (), {
                    "input_jsonl": input_path,
                    "output_jsonl": output_path,
                    "metadata": metadata_path,
                    "flank_bp": 256,
                    "max_records": None,
                })()
            )
            self.assertEqual(metadata["annotation_level"], "reference_annotation_run")
            self.assertEqual(metadata["boundary_semantics"], "reference_run_boundary")
            self.assertFalse(metadata["biological_copy_claim"])
            self.assertEqual(metadata["boundary_exclusion_half_width_bp"], 64)
            self.assertEqual(metadata["boundary_exclusion_band_bp"], 64)
            self.assertEqual(metadata["boundary_min_each_side_bp"], 8)
            self.assertEqual(metadata["flank_range_bp"], [64, 256])
            written = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(written["claim_scope"], "reference annotation run only; not biological full-copy")
            output = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(set(output["candidate_masks"]), {"interior", "boundary", "flank"})

    def test_packable_retention_skips_sparse_window(self):
        record = self._record([(300, 340)])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            output_path = root / "output.jsonl"
            metadata_path = root / "metadata.json"
            input_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            metadata = BUILDER.build(
                type("Args", (), {
                    "input_jsonl": input_path,
                    "output_jsonl": output_path,
                    "metadata": metadata_path,
                    "flank_bp": 256,
                    "max_records": None,
                    "retain_packable_windows": 1,
                })()
            )
            self.assertEqual(metadata["scanned_records"], 1)
            self.assertEqual(metadata["retained_records"], 0)
            self.assertEqual(metadata["filtered_records"], 1)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "")
            self.assertIn("clean boundary span", metadata["filter_rule"])

    def test_packable_retention_scans_until_requested_count(self):
        sparse = self._record([(300, 340)])
        rich_runs = [(300 + index * 700, 600 + index * 700) for index in range(11)]
        first_rich = self._record(rich_runs)
        first_rich["start"] = 10
        second_sparse = self._record([(600, 640)])
        second_rich = self._record(rich_runs)
        second_rich["start"] = 30
        rows = [sparse, first_rich, second_sparse, second_rich]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            output_path = root / "output.jsonl"
            metadata_path = root / "metadata.json"
            input_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            metadata = BUILDER.build(
                type("Args", (), {
                    "input_jsonl": input_path,
                    "output_jsonl": output_path,
                    "metadata": metadata_path,
                    "flank_bp": 256,
                    "max_records": None,
                    "retain_packable_windows": 2,
                })()
            )
            output_rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["start"] for row in output_rows], [10, 30])
            self.assertEqual(metadata["scanned_records"], 4)
            self.assertEqual(metadata["retained_records"], 2)
            self.assertEqual(metadata["filtered_records"], 2)
            self.assertEqual(metadata["retention_limit"], 2)

    def test_packable_retention_requires_total_capacity_and_boundary(self):
        record = self._record([(1000, 7000)])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            output_path = root / "output.jsonl"
            metadata_path = root / "metadata.json"
            input_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            metadata = BUILDER.build(
                type("Args", (), {
                    "input_jsonl": input_path,
                    "output_jsonl": output_path,
                    "metadata": metadata_path,
                    "flank_bp": 256,
                    "max_records": None,
                    "retain_packable_windows": 1,
                })()
            )
            self.assertEqual(metadata["retained_records"], 1)
            self.assertEqual(metadata["filtered_records"], 0)


if __name__ == "__main__":
    unittest.main()
