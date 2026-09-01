from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).parent
SCRIPT = ROOT / "submit_phase0_chr19_candidate_eval.sbatch"


class Phase0Chr19PipelineSbatchTest(unittest.TestCase):
    def test_complete_locked_cpu_chain_and_atomic_outputs(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertNotIn("#SBATCH --gres=", text)
        self.assertIn("#SBATCH --time=04:00:00", text)
        self.assertIn("PASS_TO_TEST True", text)
        self.assertIn("selection_locked", text)
        self.assertIn("test_labels_read", text)
        self.assertIn("test_label_release_allowed", text)
        self.assertIn('purge.get("status") != "PASS"', text)
        self.assertIn('purge_status != "PASS"', text)
        self.assertIn('python3 "${GAP_SCRIPT}" project-labels', text)
        self.assertIn('python3 "${EVAL_SCRIPT}"', text)
        self.assertIn('python3 "${MASK_SCRIPT}"', text)
        self.assertIn('python3 "${GENE_SCRIPT}"', text)
        self.assertIn('python3 "${DECISION_SCRIPT}"', text)
        self.assertIn("--p3-canonical", text)
        self.assertIn("--refined-canonical", text)
        self.assertIn("--selected-sidecar", text)
        self.assertIn("TEST_LABELS_CONSUMED", text)
        self.assertIn("STATUS", text)
        self.assertIn("LOCAL_SCRATCH=${SLURM_TMPDIR:-/tmp}", text)
        self.assertIn('cp -a "${TASK_ROOT}/." "${TRANSFER_ROOT}/"', text)
        self.assertIn('mv "${TRANSFER_ROOT}" "${RUN_ROOT}"', text)
        stages = [
            'CURRENT_STAGE=project_labels',
            'CURRENT_STAGE=candidate_evaluation',
            'CURRENT_STAGE=mask_fragment_gate',
            'CURRENT_STAGE=gene_safety',
            'CURRENT_STAGE=gate_decision',
        ]
        positions = [text.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


if __name__ == "__main__":
    unittest.main()
