#!/usr/bin/env python3
import csv
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent
EXCLUDE = "gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043"


class E0SbatchContractTest(unittest.TestCase):
    def read_and_check_common(self, name: str, walltime: str) -> str:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertIn("#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1", text)
        self.assertIn(f"#SBATCH --exclude={EXCLUDE}", text)
        self.assertIn("#SBATCH --nodes=1", text)
        self.assertIn("#SBATCH --ntasks=1", text)
        self.assertIn("#SBATCH --cpus-per-task=8", text)
        self.assertIn("#SBATCH --mem=96G", text)
        self.assertIn(f"#SBATCH --time={walltime}", text)
        self.assertNotIn("#SBATCH --signal=", text)
        self.assertIn(": \"${ATTEMPT_TAG:?", text)
        self.assertIn("/outputs/GAP-BRIDGE-PHASE0-R1/", text)
        self.assertIn("/logs/GAP-BRIDGE-PHASE0-R1/", text)
        self.assertIn("printf 'PASS\\n'", text)
        subprocess.run(["bash", "-n", str(path)], check=True)
        return text

    def test_identity_resources_paths_and_exact_compare_commands(self):
        text = self.read_and_check_common("submit_e0_chr17_identity.sbatch", "02:00:00")
        self.assertNotIn("#SBATCH --array=", text)
        self.assertIn("e0-chr17-identity-%j.out", text)
        self.assertIn("e0-chr17-identity-%j.err", text)
        self.assertNotIn("data/raw/ucsc/human/hg38/hg38.fa.gz", text)
        self.assertIn("data/human_h0_w8192/test/data.jsonl.gz", text)
        self.assertIn("p3-human-20260828-r2-12097867/unet", text)
        self.assertIn("eval/human.prediction.tsv", text)
        self.assertIn("eval/human.lengths.json", text)
        self.assertIn('python3 "${E0_SCRIPT}" export-p3', text)
        self.assertIn('python3 "${E0_SCRIPT}" identity', text)
        self.assertIn("--max-windows 1200", text)
        self.assertIn("--output-json \"${RUN_ROOT}/identity.json\"", text)
        self.assertNotIn("phase0_gap_table.py", text)

    def test_preflight_array_resources_paths_and_engineering_commands(self):
        text = self.read_and_check_common("submit_e0_preflight.sbatch", "08:00:00")
        self.assertIn("#SBATCH --array=0-1%2", text)
        self.assertIn("e0-preflight-%A_%a.out", text)
        self.assertIn("e0-preflight-%A_%a.err", text)
        self.assertIn("data/raw/ucsc/human/hg38/hg38.fa.gz", text)
        self.assertIn("p3-human-20260828-r2-12097867/unet", text)
        self.assertIn("0) SEQID=chr3", text)
        self.assertIn("1) SEQID=chr5", text)
        self.assertIn("materialize-region", text)
        self.assertIn("--seqid \"${SEQID}\"", text)
        self.assertIn("--start 0", text)
        self.assertIn("--end 50000000", text)
        self.assertIn("--output-jsonl \"${TASK_ROOT}/region.jsonl.gz\"", text)
        self.assertIn("export-p3", text)
        self.assertIn("--output-pte \"${TASK_ROOT}/p_te.npy\"", text)
        self.assertIn("--output-states \"${TASK_ROOT}/states.npy\"", text)
        self.assertIn("--output-canonical \"${TASK_ROOT}/prediction.canonical.tsv\"", text)
        self.assertIn("rmsk_te_strict.bed.gz", text)
        self.assertIn("rmsk_te_plus_unknown.bed.gz", text)
        self.assertIn('python3 "${GAP_SCRIPT}" candidates', text)
        self.assertIn('python3 "${GAP_SCRIPT}" project-labels', text)
        self.assertIn('python3 "${GAP_SCRIPT}" census', text)
        self.assertIn("candidate_census.json", text)
        self.assertNotRegex(text, r"--metrics(?:\s|=)")

    def test_cpu_finalization_reuses_complete_export_without_gpu(self):
        path = ROOT / "submit_e0_finalize_from_export.sbatch"
        text = path.read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertNotIn("#SBATCH --gres=", text)
        self.assertNotIn("#SBATCH --exclude=", text)
        self.assertIn("#SBATCH --cpus-per-task=8", text)
        self.assertIn("#SBATCH --mem=32G", text)
        self.assertIn("#SBATCH --time=02:00:00", text)
        self.assertIn("#SBATCH --array=0-1%2", text)
        self.assertIn("e0-preflight-20260901-r2", text)
        self.assertIn(": \"${ATTEMPT_TAG:?", text)
        self.assertIn('python3 "${GAP_SCRIPT}" candidates', text)
        self.assertIn('python3 "${GAP_SCRIPT}" project-labels', text)
        self.assertIn('python3 "${GAP_SCRIPT}" census', text)
        self.assertIn("candidate_census.json", text)
        self.assertNotIn("export-p3", text)
        self.assertNotRegex(text, r"--metrics(?:\s|=)")
        subprocess.run(["bash", "-n", str(path)], check=True)

    def test_full_chunk_plan_is_complete_and_window_aligned(self):
        with (ROOT / "full_phase0_chunks.tsv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual([int(row["task_id"]) for row in rows], list(range(13)))
        lengths = {"chr3": 198295559, "chr5": 181538259, "chr13": 114364328, "chr19": 58617616}
        for seqid, length in lengths.items():
            chunks = [row for row in rows if row["seqid"] == seqid]
            next_start = 0
            for index, row in enumerate(chunks):
                start, end = int(row["start"]), int(row["end"])
                self.assertEqual(start, next_start)
                if index < len(chunks) - 1:
                    self.assertEqual(end % 8192, 0)
                next_start = end
            self.assertEqual(next_start, length)

    def test_full_gpu_chunk_sbatch_contract(self):
        text = self.read_and_check_common("submit_full_phase0_chunks.sbatch", "05:00:00")
        self.assertIn("#SBATCH --array=0-12%8", text)
        self.assertIn("full_phase0_chunks.tsv", text)
        self.assertIn("materialize-region", text)
        self.assertIn("export-p3", text)
        self.assertNotIn("rmsk_te_strict", text)
        self.assertIn(">/dev/null", text)

    def test_full_cpu_stitch_sbatch_contract(self):
        path = ROOT / "submit_full_phase0_stitch.sbatch"
        text = path.read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertNotIn("#SBATCH --gres=", text)
        self.assertIn("#SBATCH --array=0-3%4", text)
        self.assertIn("#SBATCH --time=04:00:00", text)
        self.assertIn(": \"${SOURCE_TAG:?", text)
        self.assertIn(": \"${ATTEMPT_TAG:?", text)
        self.assertIn("stitch-chunks", text)
        self.assertIn('python3 "${GAP_SCRIPT}" candidates', text)
        self.assertIn('python3 "${GAP_SCRIPT}" project-labels', text)
        self.assertIn('python3 "${GAP_SCRIPT}" census', text)
        self.assertNotRegex(text, r"--metrics(?:\s|=)")
        subprocess.run(["bash", "-n", str(path)], check=True)


if __name__ == "__main__":
    unittest.main()
