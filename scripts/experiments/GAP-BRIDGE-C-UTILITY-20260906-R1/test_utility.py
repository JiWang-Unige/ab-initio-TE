import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("utility", Path(__file__).with_name("utility.py"))
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class PairedTests(unittest.TestCase):
    def setUp(self):
        self.cores = [u.ep.Core(i, i*100, (i+1)*100, max(0, i*100-20), (i+1)*100+20) for i in range(9)]
        self.a = u.ep.Chain("+", ((310, 320),))
        self.b = u.ep.Chain("-", ((350, 370),))
        self.false = u.ep.Chain("+", ((10, 20),))
        self.truth = {i: set() for i in range(9)}
        self.truth[3] = {self.a, self.b}
        self.meta = {c: {"gene_ids": {f"g{n}"}, "transcript_ids": {f"t{n}"}}
                     for n, c in enumerate((self.a, self.b))}
        self.pred = {m: {i: set() for i in range(9)} for m in u.MODES}
        for mode in u.MODES:
            self.pred[mode][3] = {self.a}
            self.pred[mode][0] = {self.false}

    def test_micro_keeps_zero_reference_core_false_positive(self):
        self.pred["MW"][3].add(self.b)
        modes, paired = u.paired_metrics(self.truth, self.pred, self.cores, self.meta)
        self.assertEqual(modes["M0"]["metrics"]["micro_f1"], .5)
        self.assertEqual(modes["M0"]["per_core"]["0"]["fp"], 1)
        self.assertEqual(len(modes["MW"]["per_core"]), 9)
        self.assertEqual(modes["MW"]["metrics"]["micro_f1"], .8)
        self.assertTrue(paired["MW"]["exploratory_gate_pass"])
        self.assertEqual(paired["MW"]["gained"][0]["gene_ids"], ["g1"])

    def test_equal_counts_do_not_hide_identity_loss(self):
        self.pred["MP"][3] = {self.b}
        _, paired = u.paired_metrics(self.truth, self.pred, self.cores, self.meta)
        self.assertEqual(paired["MP"]["gained_correct_chains"], 1)
        self.assertEqual(paired["MP"]["lost_correct_chains"], 1)
        self.assertFalse(paired["MP"]["exploratory_gate_pass"])

    def test_gain_without_f1_improvement_fails_and_reports_unmatched(self):
        self.pred["MW"][3].add(self.b)
        self.pred["MW"][0].update(u.ep.Chain("+", ((30+i*3, 32+i*3),)) for i in range(5))
        _, paired = u.paired_metrics(self.truth, self.pred, self.cores, self.meta)
        self.assertEqual(paired["MW"]["new_unmatched_predictions"], 5)
        self.assertEqual(len(paired["MW"]["new_unmatched"]), 5)
        self.assertLess(paired["MW"]["micro_f1_delta_vs_m0"], 0)
        self.assertFalse(paired["MW"]["exploratory_gate_pass"])


class InputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name)
        self.core = u.ep.Core(6, 20, 80, 0, 100)
        self.folder = self.out / "core6"
        self.folder.mkdir()
        (self.folder / "M0.fasta").write_text(f">{self.core.record_id}\n" + "A"*100 + "\n")
        (self.folder / "M0.observation.json").write_text(json.dumps({"calls": 1, "passed": True}))

    def tearDown(self):
        self.temp.cleanup()

    def row(self, start=26, end=35, tid="t", fmt="gtf", strand="+"):
        attr = f'transcript_id "{tid}";' if fmt == "gtf" else f"Parent={tid}"
        return f"{self.core.record_id}\tT\tCDS\t{start}\t{end}\t.\t{strand}\t0\t{attr}\n"

    def test_empty_output_valid_but_missing_cell_not_valid(self):
        (self.folder / "M0.gtf").write_text("# empty\n")
        with self.assertRaises(FileNotFoundError):
            u.read_cell(self.out, self.core, "M0", [self.core])
        (self.folder / "M0.gff3").write_text("##gff-version 3\n")
        pred, report = u.read_cell(self.out, self.core, "M0", [self.core])
        self.assertEqual(pred, set())
        self.assertEqual(report["cds_rows"], 0)

    def test_native_duplicate_and_one_base_or_strand_mismatch(self):
        (self.folder / "M0.gtf").write_text(self.row() + self.row(tid="dup"))
        (self.folder / "M0.gff3").write_text(self.row(fmt="gff3") + self.row(fmt="gff3", tid="dup"))
        pred, report = u.read_cell(self.out, self.core, "M0", [self.core])
        self.assertEqual(len(pred), 1)
        self.assertEqual(report["duplicate_eligible_transcript_records"], 1)
        for kw in ({"start": 27}, {"strand": "-"}):
            (self.folder / "M0.gff3").write_text(self.row(fmt="gff3", **kw))
            with self.assertRaisesRegex(ValueError, "mismatch"):
                u.read_cell(self.out, self.core, "M0", [self.core])

    def test_excluded_predictions_remain_visible(self):
        (self.folder / "M0.gtf").write_text(self.row(start=1, end=10))
        (self.folder / "M0.gff3").write_text(self.row(start=1, end=10, fmt="gff3"))
        pred, report = u.read_cell(self.out, self.core, "M0", [self.core])
        self.assertFalse(pred)
        self.assertEqual(report["counts"]["outside_dev_core"], 1)
        self.assertEqual(report["excluded_records"][0]["reason"], "outside_dev_core")
        self.assertEqual(report["halo_edge_touching_records"], 1)

    def test_case_only_mask_changes_stay_in_core(self):
        baseline = "A"*100
        changed = baseline[:30]+"a"*3+baseline[33:]
        self.assertEqual(u.changed_positions(baseline, changed, self.core), [30, 31, 32])
        for wrong in ("a"+baseline[1:], baseline[:30]+"C"+baseline[31:]):
            with self.assertRaises(ValueError):
                u.changed_positions(baseline, wrong, self.core)

    def test_reference_risk_union_and_intronic_splice_both_ends(self):
        fields = ["NM_example", "chr13", "-", "0", "30", "3", "28", "2", "0,20,", "10,30,", "0", "G", "cmpl", "cmpl", "0,2,"]
        path = self.out / "reference.txt"
        path.write_text("\t".join(fields)+"\n"+"\t".join(fields)+"\n")
        features = u.annotation_features(path)
        result = u.feature_risk([3, 9, 10, 11, 18, 19, 20, 28], features)
        self.assertEqual(result["CDS"]["added_mask_overlap_bp"], 3)
        self.assertEqual(result["exon"]["added_mask_overlap_bp"], 4)
        self.assertEqual(result["splice_dinucleotide"]["added_mask_overlap_bp"], 4)
        self.assertEqual(result["CDS"]["genes"], ["G"])


if __name__ == "__main__":
    unittest.main()
