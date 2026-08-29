#!/usr/bin/env python3
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent


class P3R2PreflightSbatchContractTest(unittest.TestCase):
    def test_cpu_preflight_covers_both_target_modes(self):
        path = ROOT / "submit_p3_human_unet_r2_preflight_cpu.sbatch"
        text = path.read_text(encoding="utf-8")
        self.assertIn("#SBATCH --cpus-per-task=4", text)
        self.assertIn("#SBATCH --mem=32G", text)
        self.assertIn("${ATTEMPT_TAG:?", text)
        self.assertIn("--boundary-target-mode true", text)
        self.assertIn("--boundary-target-mode shuffled", text)
        self.assertIn("true.json", text)
        self.assertIn("shuffled.json", text)
        self.assertEqual(text.count("--max-eval-samples 800"), 2)
        self.assertNotIn("--gres=", text)
        subprocess.run(["bash", "-n", str(path)], check=True)


if __name__ == "__main__":
    unittest.main()
