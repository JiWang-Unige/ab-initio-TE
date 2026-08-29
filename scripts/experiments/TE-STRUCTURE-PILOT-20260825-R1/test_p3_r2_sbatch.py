#!/usr/bin/env python3
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent
EXCLUDE = "gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043"


class P3R2SbatchContractTest(unittest.TestCase):
    def test_array_uses_matched_true_and_shuffled_arms(self):
        path = ROOT / "submit_p3_human_unet_r2.sbatch"
        text = path.read_text(encoding="utf-8")
        for value in (
            "#SBATCH --partition=private-teodoro-gpu",
            "#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1",
            f"#SBATCH --exclude={EXCLUDE}",
            "#SBATCH --array=0-1%2",
            "#SBATCH --time=08:00:00",
            "${ATTEMPT_TAG:?",
            "TARGET_MODE=true",
            "TARGET_MODE=shuffled",
            "--r2",
            "--boundary-target-mode \"${TARGET_MODE}\"",
            "--max-steps 800",
            "--eval-steps 100",
            "--max-eval-samples 800",
            "--width 128",
            "--seed 42",
            "--max-windows 1200",
            "human_h0_w8192",
            "p3-human-r2-%j_%a.out",
            "p3-human-r2-%j_%a.err",
        ):
            self.assertIn(value, text)
        self.assertNotRegex(text.lower(), r"drosophila|flybase|dm6")
        subprocess.run(["bash", "-n", str(path)], check=True)


if __name__ == "__main__":
    unittest.main()
