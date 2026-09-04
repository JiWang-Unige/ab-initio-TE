import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "evaluate_upstream", ROOT / "evaluate_upstream.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None


try:
    SPEC.loader.exec_module(MODULE)
except ModuleNotFoundError as exc:
    if exc.name != "numpy":
        raise
    MODULE = None


@unittest.skipIf(MODULE is None, "legacy evaluation dependencies are unavailable")
class UpstreamEvaluateTest(unittest.TestCase):
    def test_panels_use_old_cal_dev_and_new_worm_screen_only(self):
        panels = MODULE.split_data_specs(Path("/old"), Path("/expanded"))
        self.assertEqual(set(panels), {"CAL", "DEV", "SCREEN"})
        self.assertNotIn("CONF", panels)
        for split in ("CAL", "DEV"):
            self.assertEqual(
                [species for species, _ in panels[split]], list(MODULE.SPECIES)
            )
            self.assertTrue(all(str(path).startswith("/old/") for _, path in panels[split]))
        self.assertEqual(panels["SCREEN"], [("c_elegans", Path("/expanded/SCREEN/c_elegans.jsonl.gz"))])


if __name__ == "__main__":
    unittest.main()
