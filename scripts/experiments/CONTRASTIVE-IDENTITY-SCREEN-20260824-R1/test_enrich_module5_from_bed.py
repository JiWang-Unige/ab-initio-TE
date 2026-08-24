import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("enrich_module5_from_bed", HERE / "enrich_module5_from_bed.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MOD)


class BedEnrichmentTests(unittest.TestCase):
    def _fixture(self):
        root = Path(tempfile.mkdtemp())
        bed_root = root / "animals" / "hg38"
        bed_root.mkdir(parents=True)
        bed = bed_root / "rmsk_te.bed.gz"
        with gzip.open(bed, "wt", encoding="utf-8") as handle:
            handle.write("chr1\t10\t20\tL1PA1\t500\t-\tLINE\tL1\t1\t10\t0\n")
            handle.write("chr1\t30\t42\tAluY\t400\t+\tSINE\tAlu\t1\t12\t0\n")
        fragments = root / "fragments.jsonl"
        rows = [
            {"species": "hg38", "chrom": "chr1", "start": 10, "end": 20, "class": "LINE", "family": "L1", "sequence": "ACGT"},
            {"species": "hg38", "chrom": "chr1", "start": 30, "end": 42, "class": "SINE", "family": "Alu", "sequence": "TGCA"},
        ]
        fragments.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        # The production CLI receives the canonical animals root, whose
        # layout is <bed_root>/<species>/rmsk_te.bed.gz.
        return root, root / "animals", fragments, rows

    def test_exact_enrichment_preserves_input_and_only_adds_source_metadata(self):
        root, bed_root, fragments, rows = self._fixture()
        enriched, manifest = MOD.exact_enrich(rows, bed_root)
        self.assertEqual([row["repeat_name"] for row in enriched], ["L1PA1", "AluY"])
        self.assertEqual([row["strand"] for row in enriched], ["-", "+"])
        self.assertEqual(manifest["input_records"], 2)
        self.assertEqual(manifest["generated_identity_fields"], [])
        for row in enriched:
            self.assertNotIn("copy_id", row)
            self.assertNotIn("superfamily_id", row)
            self.assertNotIn("homology_component_id", row)
            self.assertEqual(row["enrichment_status"], "exact_canonical_bed_join")
            self.assertIn("\t", row["raw"])
            self.assertEqual(len(row["source_bed_fields"]), 11)

    def test_missing_source_row_is_a_typed_error(self):
        _root, bed_root, _fragments, rows = self._fixture()
        rows[1]["start"] = 31
        with self.assertRaisesRegex(MOD.EnrichmentError, "BED_JOIN_MISSING"):
            MOD.exact_enrich(rows, bed_root)

    def test_duplicate_source_key_is_a_typed_ambiguity(self):
        _root, bed_root, _fragments, rows = self._fixture()
        bed = bed_root / "hg38" / "rmsk_te.bed.gz"
        with gzip.open(bed, "at", encoding="utf-8") as handle:
            handle.write("chr1\t10\t20\tL1PA2\t500\t-\tLINE\tL1\t1\t10\t0\n")
        with self.assertRaisesRegex(MOD.EnrichmentError, "BED_JOIN_AMBIGUOUS"):
            MOD.exact_enrich(rows, bed_root)


if __name__ == "__main__":
    unittest.main()
