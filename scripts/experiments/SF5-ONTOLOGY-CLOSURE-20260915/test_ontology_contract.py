#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sf5_ontology_prep", HERE / "prepare_ontology_data.py")
prep = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(prep)


class OntologyContractTest(unittest.TestCase):
    def test_source_mapping_keeps_statuses_separate(self):
        self.assertEqual(prep.ontology_label("SINE", "Alu"), 1)
        self.assertEqual(prep.ontology_label("LINE", "L1"), 2)
        self.assertEqual(prep.ontology_label("LTR", "Gypsy"), 3)
        self.assertEqual(prep.ontology_label("DNA", "hAT"), 4)
        self.assertEqual(prep.ontology_label("RC", "Helitron"), 5)
        self.assertEqual(prep.ontology_label("Retroposon", "L1-dep"), 5)
        self.assertEqual(prep.ontology_label("DNA?", "DNA"), 6)
        self.assertEqual(prep.ontology_label("DNA", "PiggyBac?"), 6)
        self.assertEqual(prep.ontology_label("Unknown", "Unknown"), 7)
        self.assertEqual(prep.ontology_label("Unspecified", "Unspecified"), 7)
        self.assertEqual(prep.ontology_label("", ""), 7)

    def test_nonzero_coordinate_overlap_is_deterministic(self):
        # Prefix maxima make an interval beginning before the window visible;
        # the later-starting ambiguous interval deterministically overwrites
        # only its overlap.
        packed = ([(90, 108, 5), (105, 112, 6)], [108, 112])
        labels = [0] * 20
        prep.paint(labels, 100, 120, packed)
        self.assertEqual(labels[0:5], [5] * 5)
        self.assertEqual(labels[5:12], [6] * 7)
        self.assertEqual(labels[12:], [0] * 8)

    def test_frozen_full_six_species_quota(self):
        self.assertEqual(set(prep.SPECIES_CHROMS), {
            "mouse", "zebrafish", "chicken", "western_clawed_frog", "fruit_fly", "c_elegans"
        })
        self.assertEqual(prep.SPLIT_LIMITS, {"train": 900, "val": 240, "test": 360})
        self.assertEqual(len(prep.SPECIES_CHROMS) * prep.SPLIT_LIMITS["val"], 1440)
        self.assertEqual(len(prep.SPECIES_CHROMS) * prep.SPLIT_LIMITS["test"], 2160)

    def test_selected_source_rows_are_preserved_in_manifest_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.bed"
            path.write_text(
                "chrA\t100\t110\tR\t1\t+\tRC\tHelitron\tRC/Helitron\n"
                "chrA\t108\t116\tU\t1\t+\tUnknown\tUnknown\tUnknown/Unknown\n"
                "chrB\t1\t5\tS\t1\t+\tSINE\tAlu\tSINE/Alu\n"
            )
            intervals, stats = prep.load_intervals(str(path), {"chrA"})
            self.assertIn("chrA", intervals)
            self.assertEqual(stats["records"], 2)
            self.assertEqual(stats["class_records"], {"RC": 1, "Unknown": 1})


if __name__ == "__main__":
    unittest.main()
