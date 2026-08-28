#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SIDECAR = load("build_high_conf_repeatmasker_sidecar")
BUILDER = load("build_annotation_span_corpus")


def out_row(
    score: int,
    div: float,
    deletion: float,
    insertion: float,
    seqid: str,
    query_start: int,
    query_end: int,
    query_left: str,
    strand: str,
    repeat_name: str,
    class_family: str,
    repeat_begin: str,
    repeat_end: str,
    repeat_left: str,
    hit_id: int = 1,
) -> str:
    if strand == "C":
        repeat_columns = (repeat_left, repeat_end, repeat_begin)
    else:
        repeat_columns = (repeat_begin, repeat_end, repeat_left)
    return " ".join(
        [
            str(score), str(div), str(deletion), str(insertion), seqid,
            str(query_start), str(query_end), query_left, strand, repeat_name,
            class_family, *repeat_columns, str(hit_id),
        ]
    ) + "\n"


class RepeatMaskerSidecarTests(unittest.TestCase):
    def test_filters_thresholds_classes_and_selectors(self):
        text = "".join(
            [
                "   SW  perc div.  perc del.  perc ins.\n",
                out_row(300, 10.0, 1.0, 2.0, "chr1", 100, 199, "(1000)", "+", "L1", "LINE/L1", "1", "100", "(6000)"),
                out_row(301, 10.0, 1.0, 2.0, "chr2", 200, 299, "(1000)", "C", "Alu", "SINE/Alu", "1", "100", "(0)"),
                out_row(224, 10.0, 1.0, 2.0, "chr1", 400, 499, "(1000)", "+", "L2", "LINE/L2", "1", "100", "(0)"),
                out_row(300, 51.0, 1.0, 2.0, "chr1", 600, 699, "(1000)", "+", "L3", "LINE/L3", "1", "100", "(0)"),
                out_row(300, 10.0, 1.0, 2.0, "chr1", 800, 850, "(1000)", "+", "L4", "LINE/L4", "1", "100", "(0)"),
                out_row(300, 10.0, 1.0, 2.0, "chr1", 900, 999, "(1000)", "+", "sat", "Satellite", "1", "100", "(0)"),
                out_row(300, 10.0, 1.0, 2.0, "scaffoldA", 100, 199, "(1000)", "+", "L5", "LINE/L5", "1", "100", "(0)"),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "test.out"
            source.write_text(text, encoding="utf-8")
            accepted, counts = SIDECAR.high_confidence_hits(
                source,
                prefixes=["chr"],
            )
        self.assertEqual([(row["seqid"], row["start"], row["end"]) for row in accepted], [
            ("chr1", 99, 199),
            ("chr2", 199, 299),
        ])
        self.assertEqual(accepted[1]["strand"], "-")
        self.assertEqual(counts["accepted_rows"], 2)
        self.assertEqual(counts["rejected_sw"], 1)
        self.assertEqual(counts["rejected_alignment_threshold"], 2)
        self.assertEqual(counts["rejected_class"], 1)
        self.assertEqual(counts["outside_requested_seqids"], 1)

    def test_reverse_row_allows_zero_repeat_left_and_validates_repeat_coordinates(self):
        row = out_row(250, 0.0, 0.0, 0.0, "chr1", 1, 64, "(0)", "C", "L1", "LINE/L1", "1", "64", "(0)")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.out"
            source.write_text(row, encoding="utf-8")
            accepted, _ = SIDECAR.high_confidence_hits(source)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["strand"], "-")
        self.assertEqual(accepted[0]["query_span"], 64)

    def test_reverse_row_allows_repeatmasker_directional_coordinate_reversal(self):
        row = out_row(250, 0.0, 0.0, 0.0, "chr1", 1, 64, "(0)", "C", "L1", "LINE/L1", "137", "136", "(176)")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.out"
            source.write_text(row, encoding="utf-8")
            accepted, _ = SIDECAR.high_confidence_hits(source)
        self.assertEqual(len(accepted), 1)

    def test_reverse_row_allows_negative_repeat_left(self):
        row = out_row(250, 0.0, 0.0, 0.0, "chr1", 1, 64, "(0)", "C", "L1", "LINE/L1", "1", "64", "(-94)")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.out"
            source.write_text(row, encoding="utf-8")
            accepted, _ = SIDECAR.high_confidence_hits(source)
        self.assertEqual(len(accepted), 1)

    def test_forward_row_allows_signed_repeat_coordinates(self):
        row = out_row(250, 0.0, 0.0, 0.0, "chr1", 1, 64, "(0)", "+", "L1", "LINE/L1", "-2", "61", "(-4)")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.out"
            source.write_text(row, encoding="utf-8")
            accepted, _ = SIDECAR.high_confidence_hits(source)
        self.assertEqual(len(accepted), 1)

    def test_malformed_numeric_alignment_row_is_not_silently_dropped(self):
        row = "300 10.0 1.0 2.0 chr1 1 64 (0) + L1 LINE/L1 nope 64 (0) 1\n"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.out"
            source.write_text(row, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "repeat start"):
                SIDECAR.high_confidence_hits(source)

    def test_alignment_percentage_over_100_is_parsed_then_rejected_by_threshold(self):
        row = out_row(425, 23.2, 5.1, 166.5, "chr1", 1, 100, "(0)", "C", "L1", "LINE/L1", "1", "100", "(0)")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.out"
            source.write_text(row, encoding="utf-8")
            accepted, counts = SIDECAR.high_confidence_hits(source)
        self.assertEqual(accepted, [])
        self.assertEqual(counts["rejected_alignment_threshold"], 1)

    def test_writer_outputs_zero_based_half_open_bed(self):
        row = out_row(250, 0.0, 0.0, 0.0, "chr1", 1, 64, "(0)", "+", "L1", "LINE/L1", "1", "64", "(0)")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "test.out"
            output = root / "high_conf.bed"
            source.write_text(row, encoding="utf-8")
            metadata = SIDECAR.write_sidecar(source, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "chr1\t0\t64\tL1\t250\t+\n")
            self.assertEqual(metadata["counts"]["accepted_rows"], 1)


class AnnotationOverlayTests(unittest.TestCase):
    def _record(self):
        labels = [0] * BUILDER.WINDOW
        labels[100:220] = [1] * 120
        labels[500:700] = [1] * 200
        labels[900:940] = [-100] * 40
        return {
            "sequence": "A" * BUILDER.WINDOW,
            "labels": labels,
            "chr": "chr1",
            "start": 0,
            "end": BUILDER.WINDOW,
        }

    def test_touching_sidecar_rows_are_unioned_without_internal_boundaries(self):
        record = self._record()
        result = BUILDER.build_record(
            record,
            annotation_intervals={"chr1": [(500, 600), (600, 700)]},
        )
        self.assertEqual(result["labels"], record["labels"])
        self.assertEqual(result["unknown_mask"][900:940], [True] * 40)
        self.assertEqual(result["boundary_intervals"], [[476, 524], [676, 724]])
        self.assertFalse(any(result["candidate_masks"][name][150] for name in ("interior", "boundary", "flank")))
        self.assertFalse(result["candidate_masks"]["boundary"][600])

    def test_low_quality_positive_is_excluded_from_candidates_but_callable_label_remains(self):
        record = self._record()
        result = BUILDER.build_record(
            record,
            annotation_intervals={"chr1": [(500, 700)]},
        )
        self.assertEqual(result["labels"][150], 1)
        self.assertFalse(result["unknown_mask"][150])
        self.assertFalse(any(result["candidate_masks"][name][150] for name in ("interior", "boundary", "flank")))
        self.assertEqual(sum(label >= 0 for label in result["labels"]), BUILDER.WINDOW - 40)
        self.assertEqual(BUILDER._callable_bp(result), BUILDER.WINDOW - 40)

    def test_bed_reader_unions_overlapping_and_touching_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "annotation.bed"
            path.write_text("# test\nchr1\t100\t200\nchr1\t200\t250\nchr1\t240\t300\nchr2\t1\t4\n", encoding="utf-8")
            self.assertEqual(
                BUILDER.read_annotation_bed(path),
                {"chr1": [(100, 300)], "chr2": [(1, 4)]},
            )

    def test_build_metadata_records_conditioning_and_original_callable_mass(self):
        record = self._record()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            output_path = root / "output.jsonl"
            metadata_path = root / "metadata.json"
            bed_path = root / "annotation.bed"
            input_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            bed_path.write_text("chr1\t500\t700\n", encoding="utf-8")
            metadata = BUILDER.build(
                type("Args", (), {
                    "input_jsonl": input_path,
                    "output_jsonl": output_path,
                    "metadata": metadata_path,
                    "flank_bp": 256,
                    "max_records": None,
                    "annotation_bed": bed_path,
                })()
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(metadata["annotation_conditioning"], "high_confidence_repeatmasker_union_over_original_reference_runs")
        self.assertEqual(metadata["annotation_demoted_positive_bp"], 120)
        self.assertEqual(metadata["annotation_preserved_unknown_bp"], 40)
        self.assertEqual(metadata["annotation_high_confidence_positive_bp"], 200)
        self.assertEqual(sum(label >= 0 for label in written["labels"]), BUILDER.WINDOW - 40)


if __name__ == "__main__":
    unittest.main()
