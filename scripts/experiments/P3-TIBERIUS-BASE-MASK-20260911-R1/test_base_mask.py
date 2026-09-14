import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
SMOKE_SCRIPT = HERE.parents[2] / "sbatch" / "P3-TIBERIUS-BASE-MASK-20260911-R1-smoke.sbatch"
SMOKE_R2_SCRIPT = HERE.parents[2] / "sbatch" / "P3-TIBERIUS-BASE-MASK-20260911-R1-smoke-r2.sbatch"
spec = importlib.util.spec_from_file_location("base_mask", HERE / "base_mask.py")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


class BaseMaskUnitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.core = base.Core("chr16", 0, 100, 200, 80, 230)

    def tearDown(self):
        self.tmp.cleanup()

    def test_normalize_and_intervals(self):
        self.assertEqual(base.normalize([(5, 8), (1, 3), (3, 5)]), ((1, 8),))
        mask = base.interval_mask([(90, 102), (105, 110), (108, 115)], 100, 120)
        self.assertEqual(mask.sum(), 12)
        self.assertTrue(mask[0])
        self.assertFalse(mask[4])

    def test_native_cds_gff_and_gtf_agree(self):
        gtf = self.root / "U.gtf"
        gff = self.root / "U.gff3"
        rows = [
            f'{self.core.record_id}\tT\tCDS\t26\t35\t.\t+\t0\ttranscript_id "a";',
            f'{self.core.record_id}\tT\tCDS\t46\t55\t.\t+\t0\ttranscript_id "a";',
            f'{self.core.record_id}\tT\tCDS\t66\t75\t.\t-\t0\ttranscript_id "b";',
        ]
        gtf.write_text("\n".join(rows) + "\n")
        gff.write_text("\n".join(
            row.replace('transcript_id "a";', "Parent=a").replace('transcript_id "b";', "Parent=b")
            for row in rows) + "\n")
        chains_a, content_a = base.parse_predictions(gtf, self.core, "gtf")
        chains_b, content_b = base.parse_predictions(gff, self.core, "gff3")
        self.assertEqual(chains_a, chains_b)
        self.assertEqual(content_a, content_b)
        self.assertEqual(len(chains_a), 2)
        self.assertIn(base.Chain("+", ((105, 115), (125, 135))), chains_a)

    def test_bootstrap_uses_count_fields_only(self):
        cfg = {"score": {"bootstrap_seed": 1, "bootstrap_replicates": 10}}
        row = {"modes": {"P": {"metric": base.metrics(4, 1, 2)},
                         "U": {"metric": base.metrics(3, 2, 3)}}}
        result = base.bootstrap([row, row], "P", "U", cfg)
        self.assertEqual(result["resamples"], 10)
        self.assertEqual(len(result["ci95"]), 2)


class SmokeLaunchContractTest(unittest.TestCase):
    def test_cleanenv_receives_per_mode_observation_target(self):
        script = SMOKE_SCRIPT.read_text()
        target_env = '--env "BASE_MASK_OBSERVATION=/work/te/$OUT/core-chr16-0/$MODE.observation.json"'
        self.assertIn(target_env, script)
        self.assertNotIn('  BASE_MASK_OBSERVATION="/work/te/$OUT/core-chr16-0/$MODE.observation.json" \\\n', script)
        start = script.index("for MODE in U P R; do")
        end = script.index("done\n", start) + len("done\n")
        loop = script[start:end]
        self.assertLess(loop.index(target_env), loop.index('"$IMAGE" /usr/bin/python3'))

        # Execute the exact mode loop with a recording Singularity shim. This
        # checks the argv seen by Singularity under --cleanenv, rather than
        # only checking that the source contains an --env spelling.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            trace = root / "singularity.argv"
            fake = fake_bin / "singularity"
            fake.write_text(
                "#!/usr/bin/env bash\n"
                "{ printf '<argv>\\n'; printf '%s\\n' \"$@\"; printf '<end>\\n'; } >> \"$TRACE_FILE\"\n"
            )
            fake.chmod(0o755)
            runner = (
                f"set -euo pipefail\n"
                f"cd {root}\n"
                f"export TRACE_FILE={trace}\n"
                f"export PATH={fake_bin}:$PATH\n"
                "TASK_ROOT=/tmp/tiberius-project\n"
                "OUT=outputs/P3-TIBERIUS-BASE-MASK-20260911-R1/smoke-r1\n"
                "IMAGE=/tmp/tiberius.sif\n"
                "OBS=scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/observed_tiberius.py\n"
                "CUDA_VISIBLE_DEVICES=0\n"
                "mkdir -p \"$OUT/core-chr16-0\"\n"
                f"{loop}"
            )
            subprocess.run(["bash", "-c", runner], check=True, capture_output=True, text=True)
            calls = []
            current = None
            for line in trace.read_text().splitlines():
                if line == "<argv>":
                    current = []
                elif line == "<end>":
                    calls.append(current)
                    current = None
                elif current is not None:
                    current.append(line)
            self.assertEqual(len(calls), 3)
            image = "/tmp/tiberius.sif"
            for mode, argv in zip(("U", "P", "R"), calls):
                image_index = argv.index(image)
                self.assertIn("--cleanenv", argv[:image_index])
                expected = (
                    "BASE_MASK_OBSERVATION=/work/te/"
                    f"outputs/P3-TIBERIUS-BASE-MASK-20260911-R1/smoke-r1/"
                    f"core-chr16-0/{mode}.observation.json"
                )
                self.assertIn(expected, argv[:image_index])
                self.assertLess(argv.index(expected), image_index)


class OutputRevisionContractTest(unittest.TestCase):
    def test_r2_launcher_and_internal_path_are_isolated_from_r1(self):
        cfg = {"runs": {"smoke": {"core_ids": ["chr16:0"]}},
               "output_base": "outputs/P3-TIBERIUS-BASE-MASK-20260911-R1"}
        self.assertEqual(base.run_root(cfg, "smoke").name, "smoke-r1")
        self.assertEqual(base.run_root(cfg, "smoke", "r1").name, "smoke-r1")
        self.assertEqual(base.run_root(cfg, "smoke", "r2").name, "smoke-r2")
        self.assertNotEqual(base.run_root(cfg, "smoke").name, base.run_root(cfg, "smoke", "r2").name)

        script = SMOKE_R2_SCRIPT.read_text()
        self.assertIn("RUN=smoke\nREVISION=r2\n", script)
        self.assertIn("OUT=outputs/P3-TIBERIUS-BASE-MASK-20260911-R1/${RUN}-${REVISION}", script)
        self.assertIn('test ! -e "$OUT"', script)
        self.assertNotIn("smoke-r1", script)
        self.assertGreaterEqual(script.count('--revision "$REVISION"'), 3)


if __name__ == "__main__":
    unittest.main()
