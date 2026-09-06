"""Regression cases for the scientific errors identified in the Pro review.

Load pure functions from their actual source so these small CPU tests do not
require training frameworks or checkpoints. The strict run test executes the
real run() with fixed predictions, not a reimplementation of its assembly.
"""
from __future__ import annotations

import ast
import bisect
import collections
import csv
import gzip
import itertools
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SUPP = ROOT / "pipelines/PIPE-TEFM-SUPP-20260617"
SEG = ROOT / "pipelines/PIPE-TEFM-SEG-SF-20260618"
FINAL = ROOT / "pipelines/PIPE-TEFM-FINAL-20260623"


def functions(path, names, **extra):
    source = ast.parse(path.read_text())
    selected = [node for node in source.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    scope = dict(np=np, bisect=bisect, collections=collections, itertools=itertools,
                 gzip=gzip, csv=csv, json=json, math=math, Path=Path)
    scope.update(extra)
    module = ast.Module(body=ast.parse("from __future__ import annotations").body + selected, type_ignores=[])
    exec(compile(module, str(path), "exec"), scope)
    return scope


class PainterTests(unittest.TestCase):
    def test_nested_intervals_in_three_actual_loaders(self):
        cases = [(SUPP / "prepare_ucsc_windows.py", "load_intervals", "paint", [1]),
                 (ROOT / "pipelines/PIPE-TEFM-EXTEND-20260620/prepare_pu_windows.py",
                  "load_intervals", "paint_positive", []),
                 (SEG / "prepare_superfamily_windows.py", "load_class_intervals", "paint", [])]
        with tempfile.TemporaryDirectory() as tmp:
            bed = Path(tmp) / "nested.bed"
            bed.write_text("chr1\t0\t1000\ta\t0\t+\tLINE\n"
                           "chr1\t100\t200\tb\t0\t+\tSINE\n"
                           "chr1\t300\t400\tc\t0\t+\tLTR\n")
            for path, loader, painter, extra_args in cases:
                with self.subTest(path=path.name):
                    scope = functions(path, {"opener", "map_class", loader, painter}, opener=open)
                    labels = [0] * 100
                    scope[painter](labels, "chr1", 500, 600, scope[loader](str(bed)), *extra_args)
                    expected = 2 if loader == "load_class_intervals" else 1
                    self.assertEqual(labels, [expected] * 100)

    def test_multiclass_overlap_keeps_existing_sorted_overwrite_priority(self):
        scope = functions(SEG / "prepare_superfamily_windows.py",
                          {"opener", "map_class", "load_class_intervals", "paint"})
        with tempfile.TemporaryDirectory() as tmp:
            bed = Path(tmp) / "classes.bed"
            bed.write_text("chr1\t0\t1000\ta\t0\t+\tLINE\n"
                           "chr1\t100\t200\tb\t0\t+\tSINE\n")
            labels = [0] * 200
            scope["paint"](labels, "chr1", 50, 250, scope["load_class_intervals"](str(bed)))
            self.assertEqual(labels, [2] * 50 + [1] * 100 + [2] * 50)

    def test_union_and_half_open_boundaries_match_brute_force(self):
        scope = functions(SUPP / "prepare_ucsc_windows.py", {"opener", "load_intervals", "paint"})
        intervals = [(0, 100), (10, 20), (30, 40), (95, 110), (140, 150)]
        with tempfile.TemporaryDirectory() as tmp:
            bed = Path(tmp) / "overlap.bed"
            bed.write_text("".join(f"chr1\t{a}\t{b}\n" for a, b in intervals))
            packed = scope["load_intervals"](str(bed))
            for start in (0, 20, 50, 100, 110, 130, 150):
                labels = [0] * 30
                scope["paint"](labels, "chr1", start, start + 30, packed, 1)
                self.assertEqual(labels, [int(any(a <= p < b for a, b in intervals))
                                          for p in range(start, start + 30)])


class APTests(unittest.TestCase):
    def setUp(self):
        self.ap = functions(SUPP / "te_token_task.py", {"average_precision_binary"})["average_precision_binary"]

    def test_tied_scores_are_order_invariant(self):
        self.assertEqual(self.ap([1, 0], [.5, .5]), .5)
        self.assertEqual(self.ap([0, 1], [.5, .5]), .5)
        self.assertAlmostEqual(self.ap([1, 0, 1, 0], [.9, .9, .5, .1]), 7 / 12)

    def test_untied_and_undefined_contract_is_preserved(self):
        self.assertEqual(self.ap([1, 0], [.9, .1]), 1.)
        self.assertEqual(self.ap([0, 1], [.9, .1]), .5)
        self.assertTrue(math.isnan(self.ap([], [])))
        self.assertTrue(math.isnan(self.ap([0, 0], [.9, .1])))


class StrictCoordinateTests(unittest.TestCase):
    def run_fixed(self, records):
        helper_names = {"binary_metrics", "runs_from_bool", "center_weights", "merge_small_gaps",
                        "min_length_filter", "viterbi_smooth"}
        helpers = functions(SEG / "bp_overlap_segment_eval.py", helper_names)
        rows = []
        scope = functions(FINAL / "strict_segment_eval.py",
                          {"best_overlap", "strict_segment_metrics", "fragmentation_truth_diagnostics",
                           "transform_covered", "run"}, **{k: helpers[k] for k in helper_names})
        fake_model = SimpleNamespace(to=lambda _: None, eval=lambda: None)
        scope.update(torch=SimpleNamespace(device=lambda x: x, cuda=SimpleNamespace(is_available=lambda: False)),
                     load_trained_model=lambda _: (fake_model, None, {}),
                     read_jsonl=lambda *_: iter(records),
                     infer_probs_for_label_mode=lambda _m, _t, seq, *_: np.full(len(seq), .9, dtype=np.float32),
                     write_tsv=lambda _path, output: rows.extend(output))
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(model_dir="unused", cpu=True, window=100, weight_mode="flat",
                                   data_jsonl="unused", max_windows=10, exp_id="fixed-test", stride=100,
                                   threshold=.5, iou_thresholds=[.8], boundary_tolerances=[5],
                                   out_tsv=str(Path(tmp) / "rows.tsv"), out_json=str(Path(tmp) / "status.json"))
            scope["run"](args)
        return {row["variant"]: row for row in rows}

    def test_disconnected_windows_never_merge_or_shrink(self):
        records = [dict(chr="chr1", start=a, end=a + 100, labels=[1] * 100, sequence="A" * 100)
                   for a in (0, 130)]
        rows = self.run_fixed(records)
        for variant, row in rows.items():
            with self.subTest(variant=variant):
                self.assertEqual(row["true_segments"], 2)
                self.assertEqual(row["pred_segments"], 2)
                self.assertEqual(row["segment_f1"], 1.)

    def test_adjacent_windows_remain_one_real_run(self):
        records = [dict(chr="chr1", start=a, end=a + 100, labels=[1] * 100, sequence="A" * 100)
                   for a in (0, 100)]
        for row in self.run_fixed(records).values():
            self.assertEqual(row["true_segments"], 1)
            self.assertEqual(row["pred_segments"], 1)
            self.assertEqual(row["segment_f1"], 1.)


if __name__ == "__main__":
    unittest.main()
