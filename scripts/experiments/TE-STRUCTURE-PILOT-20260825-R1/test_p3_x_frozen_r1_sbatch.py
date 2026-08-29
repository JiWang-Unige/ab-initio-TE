#!/usr/bin/env python3
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent
EXCLUDE = "gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043"


class P3XFrozenR1SbatchTest(unittest.TestCase):
    def test_contract_and_shell_syntax(self):
        path = ROOT / "submit_p3_x_frozen_r1.sbatch"
        text = path.read_text(encoding="utf-8")
        for value in (
            "#SBATCH --partition=private-teodoro-gpu",
            "#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1",
            f"#SBATCH --exclude={EXCLUDE}",
            "#SBATCH --time=06:00:00",
            "#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-%j.out",
            "${ATTEMPT_TAG:?",
            "p3-x-${ATTEMPT_TAG}",
            "p3_x_prepare_inference.py",
            "dmel_r6.68/dmel-all-chromosome-r6.68.fasta.gz",
            "flybase_r668_curated_positive_instances.bed",
            "expected = {\"contigs\": 1870, \"total_bp\": 143726002, \"windows\": 18935}",
            "--max-windows 18935",
            "p3_x_flybase_t1_eval.py",
            "--iou-threshold 0.8",
            "--boundary-tolerances 5 25",
            "flybase.t1.json",
            "truth.canonical.tsv",
            "contig_lengths.json",
            "printf 'PASS\\n' > \"${RUN_ROOT}/STATUS\"",
        ):
            self.assertIn(value, text)
        self.assertNotIn("--truth-tier T0", text)
        self.assertNotIn("--truth-tier T1", text)
        subprocess.run(["bash", "-n", str(path)], check=True)


if __name__ == "__main__":
    unittest.main()
