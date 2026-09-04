import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "decide_upstream", ROOT / "decide_upstream.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def row(
    f1=0.80,
    ap=0.80,
    precision=0.80,
    recall=0.80,
    segment=0.80,
    boundary=0.80,
    fragments=1.0,
    split=0.10,
    missed=0.10,
):
    return {
        "bp_f1": f1,
        "bp_average_precision": ap,
        "bp_precision": precision,
        "bp_recall": recall,
        "segment_f1_iou_0_8": segment,
        "boundary_f1_5bp": boundary,
        "fragments_per_truth": fragments,
        "split_rate": split,
        "missed_rate": missed,
    }


def metrics(rows, macro_f1=None, hardn=0.10):
    return {
        "per_species": rows,
        "summary": {
            "macro_bp_f1": macro_f1 if macro_f1 is not None else sum(r["bp_f1"] for r in rows.values()) / len(rows),
            "macro_hardN_fp_rate": hardn,
        },
    }


class UpstreamDecisionTest(unittest.TestCase):
    def setUp(self):
        self.l_dev = metrics({species: row() for species in MODULE.SPECIES}, macro_f1=0.84)
        self.l_screen = metrics({"c_elegans": row(ap=0.80)})

    def test_paired_release_requires_and_accepts_both_screen_gains(self):
        d_dev = metrics({species: row() for species in MODULE.SPECIES}, macro_f1=0.84)
        d_screen = metrics({"c_elegans": row(f1=0.82, ap=0.82)})
        result = MODULE.decide_pair(self.l_dev, self.l_screen, d_dev, d_screen)
        self.assertEqual(result["decision"], MODULE.RELEASE_PAIRED)
        self.assertTrue(result["paired_gate_pass"])

    def test_weak_positive_screen_with_nonworm_regression_stops(self):
        l_dev = metrics(
            {
                species: row(f1=0.70, precision=0.70, recall=0.70)
                for species in MODULE.SPECIES
            },
            macro_f1=0.70,
        )
        l_screen = metrics({"c_elegans": row(f1=0.70, ap=0.70, precision=0.70, recall=0.70)})
        d_rows = {species: row(f1=0.70, precision=0.70, recall=0.70) for species in MODULE.SPECIES}
        d_rows["human"] = row(f1=0.65)
        d_dev = metrics(d_rows, macro_f1=0.828)
        d_screen = metrics({"c_elegans": row(f1=0.72, ap=0.72, precision=0.70, recall=0.70)})
        result = MODULE.decide_pair(l_dev, l_screen, d_dev, d_screen)
        self.assertFalse(result["nonworm_dev_f1_gate"]["pass"])
        self.assertEqual(result["decision"], MODULE.STOP)

    def test_L_fallback_is_released_only_when_internal_targets_hold(self):
        l_dev = metrics({species: row() for species in MODULE.SPECIES}, macro_f1=0.84)
        d_dev = metrics({species: row() for species in MODULE.SPECIES}, macro_f1=0.84)
        d_screen = metrics({"c_elegans": row(f1=0.80, ap=0.80)})
        result = MODULE.decide_pair(l_dev, self.l_screen, d_dev, d_screen)
        self.assertEqual(result["decision"], MODULE.RELEASE_L)

    def test_fragment_decrease_does_not_mask_split_rate_regression(self):
        l_dev = metrics({species: row(f1=0.70, precision=0.70, recall=0.70) for species in MODULE.SPECIES}, macro_f1=0.70)
        d_rows = {
            species: row(f1=0.70, precision=0.70, recall=0.70, fragments=0.50, split=0.13)
            for species in MODULE.SPECIES
        }
        d_dev = metrics(d_rows, macro_f1=0.70)
        d_screen = metrics({"c_elegans": row(f1=0.82, ap=0.82)})
        result = MODULE.decide_pair(l_dev, self.l_screen, d_dev, d_screen)
        human = result["topology_guardrails"]["panels"]["DEV"]["human"]
        self.assertTrue(human["pass_fragments_per_truth"])
        self.assertFalse(human["pass_split_rate"])
        self.assertEqual(result["decision"], MODULE.STOP)


if __name__ == "__main__":
    unittest.main()
