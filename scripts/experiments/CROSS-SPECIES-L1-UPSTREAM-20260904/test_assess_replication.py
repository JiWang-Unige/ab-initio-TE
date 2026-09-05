import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("assess_replication", ROOT / "assess_replication.py")
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


def metrics(rows, arm, split, seed=17, scope="six-species-shared", hardn=0.10):
    return {
        "experiment": MODULE.EXPERIMENT_ID,
        "protocol": MODULE.PROTOCOL,
        "run_role": MODULE.RUN_ROLE,
        "arm": arm,
        "seed": seed,
        "calibration_scope": scope,
        "split": split,
        "conf_evaluated": False,
        "species": sorted(rows),
        "per_species": rows,
        "summary": {"macro_hardN_fp_rate": hardn},
    }


def valid_pair():
    species = set(MODULE.NONWORM) | {MODULE.WORM}
    l_dev = metrics({species_name: row() for species_name in species}, "L", "DEV")
    d_dev = metrics({species_name: row() for species_name in species}, "D", "DEV")
    l_screen = metrics({MODULE.WORM: row()}, "L", "SCREEN")
    d_screen = metrics({MODULE.WORM: row(f1=0.805, ap=0.805)}, "D", "SCREEN")
    return l_dev, l_screen, d_dev, d_screen


class ReplicationAssessmentTest(unittest.TestCase):
    def test_valid_seed17_pair_supports_conf_without_release_claim(self):
        result = MODULE.assess_pair(*valid_pair())
        self.assertTrue(result["consistent_positive_screen_signal"])
        self.assertTrue(result["proceed_to_conf"])
        self.assertEqual(result["decision"], MODULE.PROCEED)
        self.assertFalse(result["release_claim"])
        self.assertEqual(result["seed"], 17)

    def test_swapped_arm_or_seed_is_rejected(self):
        pair = valid_pair()
        swapped_arm = list(pair)
        swapped_arm[3] = copy.deepcopy(swapped_arm[3])
        swapped_arm[3]["arm"] = "L"
        with self.assertRaises(ValueError):
            MODULE.assess_pair(*swapped_arm)

        swapped_seed = list(pair)
        swapped_seed[0] = copy.deepcopy(swapped_seed[0])
        swapped_seed[0]["seed"] = 42
        with self.assertRaises(ValueError):
            MODULE.assess_pair(*swapped_seed)

    def test_guardrail_failure_is_separate_from_positive_direction(self):
        pair = list(valid_pair())
        pair[2] = copy.deepcopy(pair[2])
        pair[2]["per_species"]["human"]["bp_f1"] = 0.70
        result = MODULE.assess_pair(*pair)
        self.assertTrue(result["direction"]["pass"])
        self.assertFalse(result["guardrails"]["pass"])
        self.assertFalse(result["proceed_to_conf"])
        self.assertEqual(result["decision"], MODULE.STOP)

    def test_direction_failure_is_separate_from_guardrails(self):
        pair = list(valid_pair())
        pair[3] = copy.deepcopy(pair[3])
        pair[3]["per_species"][MODULE.WORM]["bp_f1"] = 0.79
        pair[3]["per_species"][MODULE.WORM]["bp_average_precision"] = 0.79
        result = MODULE.assess_pair(*pair)
        self.assertFalse(result["direction"]["pass"])
        self.assertTrue(result["guardrails"]["pass"])
        self.assertFalse(result["proceed_to_conf"])
        self.assertEqual(result["decision"], MODULE.STOP)


if __name__ == "__main__":
    unittest.main()
