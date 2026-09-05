from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("downstream_c_evaluate_chains", HERE / "evaluate_chains.py")
evaluate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evaluate
SPEC.loader.exec_module(evaluate)


def ref_row(name, strand, intervals, gene=None, frames=None, completeness=("cmpl", "cmpl"), chrom="chr13"):
    start, end = intervals[0][0], intervals[-1][1]
    return "\t".join(map(str, [
        0, name, chrom, strand, start, end, start, end, len(intervals),
        ",".join(str(x[0]) for x in intervals) + ",",
        ",".join(str(x[1]) for x in intervals) + ",", 0, gene or name,
        *completeness, ",".join(map(str, frames if frames is not None else [0] * len(intervals))) + ",",
    ])) + "\n"


def gtf_rows(core, name, strand, cds, stops=(), phase="0"):
    lines = []
    for feature, intervals in (("CDS", cds), ("stop_codon", stops)):
        for start, end in intervals:
            lines.append("\t".join(map(str, [core.record_id, "Tiberius", feature,
                start - core.halo_start + 1, end - core.halo_start, ".", strand, phase,
                f'gene_id "g{name}"; transcript_id "{name}";'])))
    return "\n".join(lines) + ("\n" if lines else "")


class EvaluateChainsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cores = [evaluate.Core(0, 100, 200, 50, 250), evaluate.Core(1, 200, 300, 150, 350)]
        self.geometry = self.root / "geometry.tsv"
        with self.geometry.open("w", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["block_index", "core_start", "core_end", "halo_start", "halo_end"])
            for c in self.cores:
                writer.writerow([c.index, c.start, c.end, c.halo_start, c.halo_end])
        self.refseq = self.root / "refseq.tsv"

    def test_reference_completeness_frames_dedup_and_other_chromosome(self):
        """Catch inflated reference denominators; correct eligibility/dedup before using real counts."""
        self.refseq.write_text(
            ref_row("a", "+", [(110, 119), (140, 149)], gene="G")
            + ref_row("a_duplicate", "+", [(110, 119), (140, 149)], gene="G")
            + ref_row("other_strand", "-", [(110, 119), (140, 149)])
            + ref_row("partial", "+", [(160, 169)], completeness=("cmpl", "incmpl"))
            + ref_row("invalid_frame", "+", [(170, 179)], frames=[-1])
            + ref_row("boundary", "+", [(190, 199), (260, 269)])
            + ref_row("outside", "+", [(80, 89)])
            + ref_row("sealed", "+", [(110, 119)], chrom="chr19"))
        truth, metadata, report = evaluate.read_reference(self.refseq, self.cores)
        self.assertEqual(len(truth[0]), 2)
        self.assertEqual(report["distinct_complete_chains"], 2)
        self.assertEqual(report["duplicate_eligible_transcript_rows"], 1)
        self.assertEqual(report["counts"]["incomplete_reference_cds"], 1)
        self.assertEqual(report["counts"]["invalid_exon_frames"], 1)
        self.assertEqual(report["counts"]["boundary_incomplete"], 1)
        self.assertEqual(report["counts"]["outside_dev_core"], 1)
        self.assertEqual(report["counts"]["chr13_transcript_rows"], 7)
        plus = evaluate.Chain("+", ((110, 119), (140, 149)))
        self.assertEqual(metadata[plus]["transcript_ids"], {"a", "a_duplicate"})

    def test_utr_exons_and_15_column_genepred(self):
        """Catch CDS-vs-exon denominator drift; clip coding bounds and preserve noncoding frames."""
        fields = ref_row("utr", "+", [(100, 110), (120, 150), (160, 180)], frames=[-1, 0, -1]).strip().split("\t")
        fields[6:8] = ["125", "149"]
        self.refseq.write_text("\t".join(fields[1:]) + "\n")
        truth, _, report = evaluate.read_reference(self.refseq, self.cores)
        self.assertEqual(truth[0], {evaluate.Chain("+", ((125, 149),))})
        self.assertEqual(report["distinct_complete_chains"], 1)

    def test_minus_owner_is_minimum_genomic_start_and_halo_duplicate(self):
        """Catch strand-dependent ownership or duplicate halo TP; fix record conversion/owner filtering."""
        path = self.root / "minus.gtf"
        chain = [(190, 199), (210, 219)]
        path.write_text(gtf_rows(self.cores[0], "a", "-", chain)
                        + gtf_rows(self.cores[1], "a", "-", chain))
        predicted, report = evaluate.read_predictions(path, self.cores, "include_stop_union")
        self.assertEqual(predicted[0], {evaluate.Chain("-", tuple(chain))})
        self.assertEqual(predicted[1], set())
        self.assertEqual(report["counts"]["nonowner_halo_copy"], 1)
        self.assertEqual(report["distinct_chains"], 1)

    def test_explicit_stop_union_on_both_strands_and_phase_preserved(self):
        """Catch omitted/double-added stop bases; union only explicit features and retain raw phase."""
        path = self.root / "stops.gtf"
        path.write_text(
            gtf_rows(self.cores[0], "plus", "+", [(110, 116)], [(116, 119)], phase="2")
            + gtf_rows(self.cores[0], "minus", "-", [(143, 149)], [(140, 143)], phase="1")
            + gtf_rows(self.cores[0], "included", "+", [(160, 169)], [(166, 169)])
            + gtf_rows(self.cores[0], "no_explicit", "+", [(180, 186)]))
        predicted, report = evaluate.read_predictions(path, self.cores, "include_stop_union")
        self.assertIn(evaluate.Chain("+", ((110, 119),)), predicted[0])
        self.assertIn(evaluate.Chain("-", ((140, 149),)), predicted[0])
        self.assertIn(evaluate.Chain("+", ((160, 169),)), predicted[0])
        self.assertIn(evaluate.Chain("+", ((180, 186),)), predicted[0])
        self.assertEqual(report["phase_counts"]["CDS:2"], 1)
        self.assertEqual(report["phase_records"][0]["features"][0]["feature"], "CDS")

    def test_micro_counts_exact_chains_and_m0_loss_denominator(self):
        """Catch macro averaging, overlap-only matches and wrong loss denominator; fix aggregation."""
        self.refseq.write_text(ref_row("a", "+", [(110, 119)])
                              + ref_row("b", "-", [(140, 149)])
                              + ref_row("c", "+", [(160, 169)])
                              + ref_row("d", "+", [(220, 229)]))
        m0 = gtf_rows(self.cores[0], "a", "+", [(110, 119)]) + gtf_rows(self.cores[1], "d", "+", [(220, 229)])
        mw = gtf_rows(self.cores[0], "a", "+", [(110, 119)]) + gtf_rows(self.cores[0], "b", "-", [(140, 149)])
        # One-base mismatch remains FP and FN, even at high interval overlap.
        mp = m0 + gtf_rows(self.cores[0], "almost_b", "-", [(140, 148)])
        files = {}
        for mode, text in zip(evaluate.MODES, (m0, mw, mp)):
            files[mode] = self.root / f"{mode}.gtf"
            files[mode].write_text(text)
        report = evaluate.evaluate_reference(self.refseq, self.geometry, 2, files, "include_stop_union")
        self.assertAlmostEqual(report["modes"]["M0"]["metrics"]["micro_f1"], 2 / 3)
        self.assertNotAlmostEqual(report["modes"]["M0"]["metrics"]["micro_f1"], .75)
        self.assertEqual(report["modes"]["MP"]["metrics"]["fp"], 1)
        self.assertEqual(report["modes"]["MP"]["metrics"]["fn"], 2)
        self.assertEqual(report["paired_vs_m0"]["MW"]["lost_correct_chains"], 1)
        self.assertEqual(report["paired_vs_m0"]["MW"]["gained_correct_chains"], 1)
        self.assertEqual(report["paired_vs_m0"]["MW"]["m0_correct_chain_denominator"], 2)
        self.assertEqual(report["paired_vs_m0"]["MW"]["lost_correct_fraction_of_m0"], .5)
        self.assertEqual(report["paired_vs_m0"]["MP"]["new_unmatched_predictions"], 1)
        self.assertFalse(report["scientific_scoring_enabled"])
        self.assertFalse(report["pass_criteria_applied"])

    def test_reference_only_cli_no_scientific_result(self):
        """Catch a misleading readiness label or missing denominator output; fix CLI report semantics."""
        self.refseq.write_text(ref_row("a", "+", [(110, 119)]))
        output = self.root / "reference.json"
        evaluate.main(["--geometry", str(self.geometry), "--refseq", str(self.refseq),
                       "--expected-cores", "2", "--reference-only", "--output", str(output)])
        report = json.loads(output.read_text())
        self.assertEqual(report["reference"]["distinct_complete_chains"], 1)
        self.assertNotIn("modes", report)
        self.assertFalse(report["scientific_claim"])
        self.assertFalse(report["real_tiberius_export_convention_verified"])

    def test_zero_denominators_and_unknown_gtf_record(self):
        """Catch false perfect scores or unmapped GTF coordinates; report undefined or reject input."""
        self.assertIsNone(evaluate.metrics(0, 0, 0)["micro_f1"])
        path = self.root / "wrong.gtf"
        path.write_text('chr13\tTiberius\tCDS\t1\t9\t.\t+\t0\ttranscript_id "a";\n')
        with self.assertRaisesRegex(ValueError, "unknown GTF record"):
            evaluate.read_predictions(path, self.cores, "include_stop_union")
        with self.assertRaisesRegex(ValueError, "nine|9 distinct"):
            evaluate.load_geometry(self.geometry)


if __name__ == "__main__":
    unittest.main()
