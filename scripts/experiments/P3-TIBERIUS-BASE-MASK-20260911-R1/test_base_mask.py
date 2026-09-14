import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).parent
SMOKE_SCRIPT = HERE.parents[2] / "sbatch" / "P3-TIBERIUS-BASE-MASK-20260911-R1-smoke.sbatch"
SMOKE_R2_SCRIPT = HERE.parents[2] / "sbatch" / "P3-TIBERIUS-BASE-MASK-20260911-R1-smoke-r2.sbatch"
SCORE_SCRIPT = HERE.parents[2] / "sbatch" / "P3-TIBERIUS-BASE-MASK-20260911-R1-score-full-r1.sbatch"
spec = importlib.util.spec_from_file_location("base_mask", HERE / "base_mask.py")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
recheck_spec = importlib.util.spec_from_file_location("independent_recheck", HERE / "independent_recheck.py")
independent = importlib.util.module_from_spec(recheck_spec)
sys.modules[recheck_spec.name] = independent
recheck_spec.loader.exec_module(independent)


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
            f'{self.core.record_id}\tT\tgene\t1\t75\t.\t+\t.\tgene_id "g";',
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

    def test_duplicate_isoforms_count_only_unmatched_chain_as_fp(self):
        core = base.Core("chr16", 0, 0, 50, 0, 100)
        out = self.root / "score"
        cell = out / "core-chr16-0"
        cell.mkdir(parents=True)
        (cell / "preflight.json").write_text("{}")
        rows_gtf = [
            f'{core.record_id}\tT\tgene\t1\t50\t.\t+\t.\tgene_id "g";',
            f'{core.record_id}\tT\tCDS\t1\t10\t.\t+\t0\ttranscript_id "tx1";',
            f'{core.record_id}\tT\tCDS\t21\t30\t.\t+\t0\ttranscript_id "tx2";',
            f'{core.record_id}\tT\tCDS\t41\t50\t.\t+\t0\ttranscript_id "tx3";',
        ]
        rows_gff = [
            f"{core.record_id}\tT\tgene\t1\t50\t.\t+\t.\tID=g",
            f"{core.record_id}\tT\tCDS\t1\t10\t.\t+\t0\tParent=tx1",
            f"{core.record_id}\tT\tCDS\t21\t30\t.\t+\t0\tParent=tx2",
            f"{core.record_id}\tT\tCDS\t41\t50\t.\t+\t0\tParent=tx3",
        ]
        units = {"unit": {"owner": self.core.key}}
        mapping = {
            ("chr16", "+", ((0, 10),)): "unit",
            ("chr16", "+", ((20, 30),)): "unit",
        }
        for mode in ("U", "P", "R"):
            (cell / f"{mode}.gtf").write_text("\n".join(rows_gtf) + "\n")
            (cell / f"{mode}.gff3").write_text("\n".join(rows_gff) + "\n")
            masked = 0 if mode == "U" else 1
            (cell / f"{mode}.observation.json").write_text(
                json.dumps({"calls": 1, "passed": True, "masked_positions": masked}))
        units["unit"]["owner"] = core.key
        scored = base.score_core({"modes": ("U", "P", "R")}, out, core, units, mapping)
        for mode in ("U", "P", "R"):
            self.assertEqual(scored["modes"][mode]["metric"]["tp"], 1)
            self.assertEqual(scored["modes"][mode]["metric"]["fp"], 1)
            self.assertEqual(scored["modes"][mode]["metric"]["fn"], 0)

    def test_bootstrap_uses_count_fields_only(self):
        cfg = {"score": {"bootstrap_seed": 1, "bootstrap_replicates": 10}}
        row = {"modes": {"P": {"metric": base.metrics(4, 1, 2)},
                         "U": {"metric": base.metrics(3, 2, 3)}}}
        result = base.bootstrap([row, row], "P", "U", cfg)
        self.assertEqual(result["resamples"], 10)
        self.assertEqual(len(result["ci95"]), 2)

    def test_full_score_retains_fp_from_zero_reference_core(self):
        cfg = base.load_cfg(HERE.parents[2] / "configs" / "P3-TIBERIUS-BASE-MASK-20260911-R1.json")
        cfg["score"]["bootstrap_replicates"] = 10
        rows = []
        for index in range(20):
            # The final core has predictions but no reference loci: its recall
            # is undefined, while both false positives must enter pooled F1.
            correct = {f"unit-{index}"} if index < 19 else set()
            unmatched = set() if index < 19 else {
                base.Chain("+", ((10, 20),)), base.Chain("+", ((30, 40),))}
            rows.append({"modes": {mode: {
                "metric": base.metrics(len(correct), len(unmatched), 0),
                "correct": correct, "unmatched": unmatched,
            } for mode in cfg["modes"]}})
        with mock.patch.object(base, "run_root", return_value=self.root), \
             mock.patch.object(base, "load_contract", return_value=({"unit_count": 19}, {}, {})), \
             mock.patch.object(base, "score_core", side_effect=rows), \
             mock.patch("builtins.print"):
            base.score(cfg, "full")
        result = json.loads((self.root / "result.json").read_text())
        self.assertEqual(result["completed_cells"], 60)
        for mode in cfg["modes"]:
            self.assertEqual(result["metrics"][mode], base.metrics(19, 2, 0))
            self.assertIsNone(result["per_core"][-1]["metrics"][mode]["recall"])


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

    def test_score_launcher_runs_independent_recheck_after_canonical_score(self):
        script = SCORE_SCRIPT.read_text()
        self.assertIn("RECHECK=scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/independent_recheck.py", script)
        score_call = 'python "$SCRIPT" score --config "$CFG" --run "$RUN" --revision "$REVISION"'
        recheck_call = 'python "$RECHECK" --config "$CFG" --run "$RUN" --revision "$REVISION"'
        self.assertIn(score_call, script)
        self.assertIn(recheck_call, script)
        self.assertLess(script.index(score_call), script.index(recheck_call))


class IndependentReplayTest(unittest.TestCase):
    def test_replay_recounts_artifacts_and_reproduces_four_gate_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "outputs" / "full-r1"
            out.mkdir(parents=True)
            geometry = ["core_id\tchrom\tindex\tcore_start\tcore_end\thalo_start\thalo_end"]
            units = []
            ordinary_metric = {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0}
            duplicate_isoform_metric = {"tp": 1, "fp": 1, "fn": 0, "precision": 0.5, "recall": 1.0, "f1": 2 / 3}
            per_core = []
            for index in range(20):
                key = f"chr16:{index}"
                start, end = index * 100, index * 100 + 50
                geometry.append(f"{key}\tchr16\t{index}\t{start}\t{end}\t{start}\t{start + 100}")
                record = f"chr16|base_mask_core={index}|core={start}-{end}|halo={start}-{start + 100}"
                cell = out / f"core-chr16-{index}"
                cell.mkdir()
                (cell / "input_manifest.json").write_text(json.dumps({"record_id": record}))
                if index == 0:
                    units.append({"unit_id": f"unit-{index}", "chrom": "chr16", "strand": "+",
                                  "owner": key, "isoforms": [
                                      {"intervals": [[start, start + 10]]},
                                      {"intervals": [[start + 20, start + 30]]},
                                  ]})
                    # The non-CDS row is a legal annotation record and must be
                    # ignored by both the canonical parser and the replay.
                    gtf = (
                        f'{record}\tT\tgene\t1\t50\t.\t+\t.\tgene_id "g";\n'
                        f'{record}\tT\tCDS\t1\t10\t.\t+\t0\ttranscript_id "tx1";\n'
                        f'{record}\tT\tCDS\t21\t30\t.\t+\t0\ttranscript_id "tx2";\n'
                        f'{record}\tT\tCDS\t41\t50\t.\t+\t0\ttranscript_id "tx3";\n'
                    )
                    gff = (
                        f"{record}\tT\tgene\t1\t50\t.\t+\t.\tID=g\n"
                        f"{record}\tT\tCDS\t1\t10\t.\t+\t0\tParent=tx1\n"
                        f"{record}\tT\tCDS\t21\t30\t.\t+\t0\tParent=tx2\n"
                        f"{record}\tT\tCDS\t41\t50\t.\t+\t0\tParent=tx3\n"
                    )
                    metric = duplicate_isoform_metric
                else:
                    units.append({"unit_id": f"unit-{index}", "chrom": "chr16", "strand": "+",
                                  "owner": key, "isoforms": [{"intervals": [[start, start + 10]]}]})
                    gtf = f'{record}\tT\tCDS\t1\t10\t.\t+\t0\ttranscript_id "tx";\n'
                    gff = f"{record}\tT\tCDS\t1\t10\t.\t+\t0\tParent=tx\n"
                    metric = ordinary_metric
                for mode in ("U", "P", "R"):
                    (cell / f"{mode}.gtf").write_text(gtf)
                    (cell / f"{mode}.gff3").write_text(gff)
                    masked = 0 if mode == "U" else 1
                    (cell / f"{mode}.observation.json").write_text(
                        json.dumps({"calls": 1, "passed": True, "masked_positions": masked}))
                per_core.append({"core": key, "metrics": {mode: dict(metric) for mode in ("U", "P", "R")}})
            (out / "geometry.tsv").write_text("\n".join(geometry) + "\n")
            (out / "reference_contract.json").write_text(json.dumps({"units": units}))
            summary = {mode: {"tp": 20, "fp": 1, "fn": 0, "precision": 20 / 21,
                              "recall": 1.0, "f1": 40 / 41} for mode in ("U", "P", "R")}
            comparison = {"locus_f1_delta": 0.0, "recall_delta": 0.0,
                          "gained_units": [], "lost_units": [], "new_unmatched": [],
                          "bootstrap": {"resamples": 10, "seed": 1, "ci95": [0.0, 0.0]}}
            cfg = {"experiment_id": "P3-TIBERIUS-BASE-MASK-20260911-R1", "output_base": "outputs",
                   "score": {"bootstrap_seed": 1, "bootstrap_replicates": 10,
                             "min_absolute_locus_f1_delta": 0.01,
                             "min_bootstrap_ci95_lower": 0.0, "min_recall_delta": -0.005,
                             "max_lost_u_correct_fraction": 0.01}}
            canonical = {"experiment_id": cfg["experiment_id"], "claim_eligible": False,
                         "core_count": 20, "completed_cells": 60, "per_core": per_core,
                         "metrics": summary,
                         "comparisons": {name: dict(comparison) for name in
                                         ("P_minus_U", "R_minus_U", "P_minus_R")},
                         "decision": "P3_BASE_MASK_UTILITY_GATE_NOT_MET",
                         "gate": {**cfg["score"], "passed": False}}
            result_path = out / "result.json"
            result_path.write_text(json.dumps(canonical))
            report = independent.recheck(root, cfg, "full", "r1", result_path)
            self.assertEqual(report["status"], "INDEPENDENT_RECHECK_PASS")
            self.assertEqual(report["metrics"]["P"]["tp"], 20)
            self.assertEqual(report["metrics"]["P"]["fp"], 1)
            self.assertAlmostEqual(report["metrics"]["P"]["f1"], 40 / 41)
            self.assertFalse(report["gate"]["passed"])
            self.assertTrue(all(report["canonical_match"].values()))


if __name__ == "__main__":
    unittest.main()
