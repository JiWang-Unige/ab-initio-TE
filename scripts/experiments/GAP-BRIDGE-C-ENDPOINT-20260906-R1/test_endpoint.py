import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("endpoint", Path(__file__).with_name("endpoint.py"))
ep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep)

class NativeCDSTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cores = [ep.Core(6, 100, 200, 80, 230), ep.Core(10, 200, 300, 170, 330)]

    def tearDown(self):
        self.tmp.cleanup()

    def row(self, feature="CDS", start=26, end=35, strand="+", tid="t", core=0, fmt="gtf"):
        attrs = f'transcript_id "{tid}";' if fmt == "gtf" else f"Parent={tid}"
        return f"{self.cores[core].record_id}\tT\t{feature}\t{start}\t{end}\t.\t{strand}\t0\t{attrs}\n"

    def parse(self, text, fmt="gtf"):
        p = self.root / f"file.{fmt}"
        p.write_text(text)
        return ep.read_cds(p, self.cores, fmt)

    def test_auxiliary_stop_not_union_and_offset_dedup(self):
        text = self.row() + self.row(feature="stop_codon", start=36, end=38)
        text += self.row(tid="duplicate") + self.row(start=60, end=70, strand="-", tid="minus")
        chains, report = self.parse(text)
        self.assertIn(ep.Chain("+", ((105, 115),)), chains[6])
        self.assertIn(ep.Chain("-", ((139, 150),)), chains[6])
        self.assertEqual(report["duplicate_eligible_transcript_records"], 1)

    def test_exact_one_base_and_strand_rejection(self):
        expected = ep.Chain("+", ((105, 115),))
        for text in [self.row(start=27), self.row(strand="-")]:
            chains, _ = self.parse(text)
            self.assertNotIn(expected, chains[6])

    def test_halo_owner_and_boundary(self):
        # core6 record predicts CDS owned by core10: exclude nonowner copy.
        _, report = self.parse(self.row(start=126, end=140))
        self.assertEqual(report["counts"]["nonowner_halo_copy"], 1)
        with self.assertRaisesRegex(ValueError, "outside halo"):
            self.parse(self.row(end=151))

    def test_gtf_gff3_coordinate_equivalence(self):
        a, ar = self.parse(self.row() + self.row(start=45, end=60))
        b, br = self.parse(self.row(fmt="gff3") + self.row(start=45, end=60, fmt="gff3"), "gff3")
        self.assertEqual(a, b)
        self.assertEqual(ar["all_cds_signatures"], br["all_cds_signatures"])

    def test_strand_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "inconsistent strand"):
            self.parse(self.row() + self.row(start=45, end=60, strand="-"))

    def test_empty_annotation(self):
        p, report = self.parse("# no predictions\n")
        self.assertEqual(report["cds_rows"], 0)
        self.assertFalse(p[6])

    def test_real_container_exporter_negative_controls(self):
        try:
            from bricks2marble.struct.annotation import Transcript, CDS
        except ImportError:
            self.skipTest("real exporter only available in pinned container")
        for strand in ("+", "-"):
            tx = Transcript(name="native", sequence=self.cores[0].record_id, strand=strand,
                            cds=[CDS(start=25, end=35), CDS(start=45, end=60)])
            text = tx.to_gtf_rows() + "\n"
            expected = ep.Chain(strand, ((105, 115), (125, 140)))
            parsed, _ = self.parse(text)
            self.assertIn(expected, parsed[6])
            for error in ("one_bp", "strand"):
                rows = []
                for row in text.splitlines():
                    fields = row.split("\t")
                    if fields[2] == "CDS":
                        if error == "one_bp":
                            fields[3] = str(int(fields[3])+1)
                        else:
                            fields[6] = "-" if strand == "+" else "+"
                    rows.append("\t".join(fields))
                parsed, _ = self.parse("\n".join(rows) + "\n")
                self.assertNotIn(expected, parsed[6])

    def test_codon_audit_plus_minus_without_filter(self):
        core = self.cores[0]
        # ATG AAA TAA plus; reverse complement is TTA TTT CAT.
        seq = "N" * 25 + "ATGAAATAA" + "N" * 10 + "TTATTTCAT" + "N" * 97
        path = self.root / "M0.fasta"
        path.write_text(f">{core.record_id}\n{seq}\n")
        report = ep.audit_coding_sequences([
            (core.record_id, "+", ((105, 114),)),
            (core.record_id, "-", ((124, 133),))], path, self.cores)
        self.assertEqual(report["terminal_stop_records"], 2)
        self.assertEqual(report["atg_start_records"], 2)
        self.assertEqual(report["length_mod3_counts"], {"0": 2})
        self.assertFalse(report["filter_applied"])

if __name__ == "__main__":
    unittest.main()
