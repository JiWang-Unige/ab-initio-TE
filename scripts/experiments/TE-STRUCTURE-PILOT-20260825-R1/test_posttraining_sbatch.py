#!/usr/bin/env python3
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent
EXCLUDE = "gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043"


class PosttrainingSbatchContractTest(unittest.TestCase):
    def check_common_header(self, path: Path, walltime: str) -> str:
        text = path.read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertIn("#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1", text)
        self.assertIn(f"#SBATCH --exclude={EXCLUDE}", text)
        self.assertIn(f"#SBATCH --time={walltime}", text)
        self.assertIn(": \"${ATTEMPT_TAG:?", text)
        self.assertNotRegex(text.lower(), r"drosophila|flybase|dm6")
        subprocess.run(["bash", "-n", str(path)], check=True)
        return text

    def test_p2_corpus_contract(self):
        path = ROOT / "submit_p2_human_corpus_cpu.sbatch"
        text = path.read_text(encoding="utf-8")
        self.assertIn("#SBATCH --cpus-per-task=4", text)
        self.assertIn("build_high_conf_repeatmasker_sidecar.py", text)
        self.assertIn(
            "software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/"
            "UCSC_RMSK_SPECIES_ANIMALS_20260617/human_hs1/raw/"
            "human_hs1.repeatmasker.out.gz",
            text,
        )
        self.assertIn("--seqid chr1", text)
        self.assertIn("24576000", text)
        self.assertIn("--annotation-bed", text)
        self.assertIn("--max-records 3000", text)
        self.assertIn("--retain-packable-windows 3000", text)
        self.assertIn("SLURM_JOB_ID", text)
        self.assertIn("retained_records", text)
        self.assertIn("selected_span_fractions", text)
        self.assertIn("expected_selected_bp", text)
        self.assertIn("selected_fraction_of_callable_matches_15pct_fixed_span_budget", text)
        self.assertIn("audit-corpus", text)
        self.assertIn("RETAINED_RECORDS", text)
        self.assertIn("decision", text)
        self.assertIn('"GO"', text)
        subprocess.run(["bash", "-n", str(path)], check=True)

    def test_p2_contract(self):
        text = self.check_common_header(ROOT / "submit_p2_human_span_mlm_ce.sbatch", "08:00:00")
        self.assertIn('"${P2_CORPUS_ROOT:?', text)
        self.assertIn("retained_records", text)
        self.assertIn('"decision"', text)
        self.assertIn('== GO', text)
        self.assertNotIn("build_annotation_span_corpus.py", text)
        self.assertNotIn('te_span_mlm.py\" audit-corpus', text)
        for value in (
            "te_span_mlm.py\" train",
            "te_token_task.py\" train",
            "strict_segment_eval.py\"",
            '--records "${RETAINED_RECORDS}"',
            "--max-steps 800",
            "--span-length 32",
            "--window 8192",
            "--max-windows 1200",
            "human_h0_w8192",
            "single_nt_nospecial",
        ):
            self.assertIn(value, text)

    def test_p3_contract(self):
        text = self.check_common_header(ROOT / "submit_p3_human_unet.sbatch", "10:00:00")
        for value in (
            "te_unet_segmentation.py\" train",
            "te_unet_segmentation.py\" evaluate",
            "--checkpoint",
            "--max-steps 800",
            "--max-windows 1200",
            "--width 128",
            "human_h0_w8192",
            "--data-dir \"${DATA_DIR}\"",
        ):
            self.assertIn(value, text)

    def test_mechanism_smoke_contract(self):
        path = ROOT / "submit_p2_p3_mechanism_smoke.sbatch"
        text = path.read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertIn("#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1", text)
        self.assertIn(f"#SBATCH --exclude={EXCLUDE}", text)
        self.assertIn("#SBATCH --array=0-1%2", text)
        self.assertIn("#SBATCH --time=00:30:00", text)
        self.assertIn("mechanism-smoke-%j_%a.out", text)
        self.assertIn("mechanism-smoke-%j_%a.err", text)
        self.assertIn(": \"${ATTEMPT_TAG:?", text)
        self.assertNotRegex(text.lower(), r"drosophila|flybase|dm6")
        self.assertNotIn("strict_segment_eval", text)
        self.assertNotIn("te_token_task.py", text)
        self.assertIn("P2_CORPUS_ROOT", text)
        self.assertIn('"decision"', text)
        for value in (
            "te_span_mlm.py\" train",
            "human_reference_run_masks.jsonl.gz",
            "--records 2",
            "--max-steps 1",
            "te_unet_segmentation.py\" train",
            "--max-eval-samples 2",
            "--data-dir \"${DATA_DIR}\"",
        ):
            self.assertIn(value, text)
        subprocess.run(["bash", "-n", str(path)], check=True)


if __name__ == "__main__":
    unittest.main()
