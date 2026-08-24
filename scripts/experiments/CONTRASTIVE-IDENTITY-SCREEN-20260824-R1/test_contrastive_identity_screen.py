import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("contrastive_identity_screen", HERE / "contrastive_identity_screen.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MOD)


class IdentityScreenTests(unittest.TestCase):
    def test_module5_shape_is_blocked_without_fabricating_copy_identity(self):
        rows = [{"species": "hg38", "chrom": "chr1", "start": 1, "end": 9,
                 "class": "LINE", "family": "L1", "sequence": "ACGTACGT"}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "module5.jsonl"; out = root / "out"
            source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            result = subprocess.run([sys.executable, str(HERE / "contrastive_identity_screen.py"), "--input", str(source), "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual((out / "STATUS").read_text().strip(), "BLOCKED_IDENTITY_FIELDS")
            report = json.loads((out / "screen_report.json").read_text())
            self.assertFalse(report["scientific_screen_executed"])
            self.assertIsNone(report["metrics"]["ari"])
            self.assertIsNone(report["metrics"]["bcubed_f1"])
            self.assertIsNone(report["metrics"]["same_superfamily_different_family_false_link_rate"])
            audit = report["identity_audit"]
            self.assertEqual(audit["missing_field_counts"]["copy_id"], 1)
            self.assertEqual(audit["missing_field_counts"]["homology_component_id"], 1)

    def test_group_split_is_family_copy_component_safe_and_transform_is_after_split(self):
        rows = []
        for family, component in (("F1", "H1"), ("F2", "H2"), ("F3", "H3"), ("F4", "H4"), ("F5", "H5"), ("F6", "H6")):
            for copy in ("a", "b"):
                rows.append({"id": f"{family}-{copy}", "sequence": "ACGT" * 20,
                             "superfamily_id": "S1", "family_id": family, "copy_id": copy,
                             "homology_component_id": component})
        split, groups = MOD.assign_splits(rows, 42)
        self.assertEqual(len(groups), 6)
        self.assertEqual(sum(len(x) for x in groups.values()), len(rows))
        # a/b are local copy names; they must not merge unrelated families
        self.assertTrue(all(len(ids) == 2 for ids in groups.values()))
        audit = MOD.leakage_audit(rows, split)
        self.assertTrue(audit["pass"])
        transformed = MOD.crop_and_augment(rows, split, 16, True)
        self.assertTrue(all(row["transform_stage"] == "after_group_split" for row in transformed))
        self.assertTrue(all(row["split"] == split[row["id"].split("::")[0]] for row in transformed))
        self.assertTrue(all(len(row["sequence"]) == 16 for row in transformed))

    def test_no_oracle_k_and_upper_bound_label_are_explicit(self):
        source = (HERE / "contrastive_identity_screen.py").read_text()
        self.assertIn('"oracle_k_used": False', source)
        self.assertIn("supervised_family_contrastive_upper_bound", source)
        self.assertIn("upper_bound_only", source)

    def test_copy_leakage_key_is_namespaced_and_pair_diagnostics_are_defined(self):
        rows = [
            {"id": "a1", "sequence": "ACGT", "superfamily_id": "S", "family_id": "F1", "copy_id": "a", "homology_component_id": "H1"},
            {"id": "a2", "sequence": "TGCA", "superfamily_id": "S", "family_id": "F2", "copy_id": "a", "homology_component_id": "H2"},
        ]
        # Same local copy name in different families is not a leakage overlap.
        self.assertEqual(MOD.leakage_audit(rows, {"a1": "train", "a2": "test"})["cross_split_overlap_counts"]["copy_id"], 0)
        diagnostics = MOD._bcubed_and_purity([0, 0, 0], ["F1", "F1", "F2"], ["S", "S", "S"])
        self.assertEqual(diagnostics["same_superfamily_different_family_false_link_pairs"], 2)
        self.assertAlmostEqual(diagnostics["family_purity_weighted_non_noise"], 2 / 3)
        self.assertIn("bcubed_f1", diagnostics)


if __name__ == "__main__":
    unittest.main()
