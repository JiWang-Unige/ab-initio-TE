"""Check domain isolation, exact splice recovery and positive-only accounting."""
import json
import argparse
from pathlib import Path
import tempfile
import unittest

import long_read_score as lr


class LongReadScoreTest(unittest.TestCase):
    def test_frozen_span_and_exact_strand(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            header = "chrom\tstart\tend\tkind\tregion_id\n"
            (p / "primary_regions.tsv").write_text(header + "chr1\t0\t100\tprimary\ta\nchr1\t200\t300\tprimary\tb\n")
            (p / "full_autosome_regions.tsv").write_text(header + "chr1\t0\t300\tfull\tc\n")
            targets = [
                {"transcript_id": "plus", "chrom": "chr1", "strand": "+", "exons": [[10, 20], [30, 40]], "introns": [[20, 30]], "class_code": ["="]},
                {"transcript_id": "minus", "chrom": "chr1", "strand": "-", "exons": [[210, 220], [230, 240]], "introns": [[220, 230]], "class_code": ["u"]},
                {"transcript_id": "cross_old_halo", "chrom": "chr1", "strand": "+", "exons": [[80, 90], [210, 220]], "introns": [[90, 210]], "class_code": ["j"]},
            ]
            dedup = [{"chrom": r["chrom"], "strand": r["strand"], "introns": r["introns"],
                      "class_codes": r["class_code"], "coding_supported_primary": r["transcript_id"] == "plus",
                      "coding_supported_full": r["transcript_id"] == "plus"} for r in targets]
            (p / "long-read-structures.json").write_text(json.dumps({"structures": targets, "deduplicated_structures": dedup}))
            frozen = lr.freeze(p)
            self.assertEqual(frozen["domains"]["primary"]["structure_count"], 2)
            self.assertEqual(frozen["domains"]["full"]["structure_count"], 3)
            predictions = {"D": {"predicted_chains": [
                {"chrom": "chr1", "strand": "+", "intervals": [[5, 20], [30, 45]]},
                {"chrom": "chr1", "strand": "+", "intervals": [[210, 220], [230, 240]]}]},
                "RM2_FULL": {"predicted_chains": [{"chrom": "chr1", "strand": "-", "intervals": [[210, 220], [230, 240]]}]}}
            result = lr.score(predictions, frozen, "primary")
            self.assertEqual(result["arms"]["D"]["all_observed_structures"]["recovered"], 1)
            self.assertEqual(result["arms"]["D"]["source_class_u"]["recovered"], 0)
            self.assertEqual(result["arms"]["RM2_FULL"]["source_class_u"]["recovered"], 1)
            self.assertNotIn("fp", result["arms"]["D"]["all_observed_structures"])
            delta = result["comparisons"]["D_minus_RM2_FULL"]["all_observed_structures"]
            self.assertEqual(len(delta["gained_structure_ids"]), 1)
            self.assertEqual(len(delta["lost_structure_ids"]), 1)
            with self.assertRaises(FileExistsError):
                lr.freeze(p)

            # Exercise the complete scorer with genuine GTF-style coordinates:
            # exact RefSeq match, one unmatched partial prediction and an empty
            # comparator. Primary and full-domain scores must both survive.
            reference = {"reference_source": "fixture", "isoform_count": 1, "unit_count": 1,
                         "excluded_transcript_rows": {}, "units": [{"unit_id": "u1", "chrom": "chr1",
                         "strand": "+", "isoforms": [{"intervals": [[5, 20], [30, 45]]}]}]}
            (p / "evaluation-manifest.json").write_text("{}")
            for domain in ("primary", "full"):
                (p / ("reference-" + domain + ".json")).write_text(json.dumps(reference))
            gtf = p / "D.gtf"
            gtf.write_text('chr1\tTEST\tCDS\t6\t20\t.\t+\t0\ttranscript_id "good";\n'
                           'chr1\tTEST\tCDS\t31\t45\t.\t+\t0\ttranscript_id "good";\n'
                           'chr1\tTEST\tCDS\t51\t60\t.\t+\t0\ttranscript_id "partial";\n')
            (p / "R.gtf").write_text("")
            args = argparse.Namespace(evaluation_dir=p, species="zebrafish", domain="primary", gtf=None,
                name="BRAKER", arm=["D=" + str(gtf), "RM2_FULL=" + str(p / "R.gtf")],
                bootstrap_replicates=10000, output=None)
            primary = lr.e.score(args)
            self.assertEqual(primary["arms"]["D"]["metrics"]["fp"], 1)
            self.assertEqual(primary["arms"]["D"]["metrics"]["tp"], 1)
            self.assertEqual(primary["long_read"]["arms"]["D"]["all_observed_structures"]["recovered"], 1)
            args.domain = "full"
            lr.e.score(args)
            self.assertEqual(json.loads((p / "score-primary.json").read_text())["domain"], "primary")
            self.assertEqual(json.loads((p / "score-full.json").read_text())["domain"], "full")


if __name__ == "__main__":
    unittest.main()
