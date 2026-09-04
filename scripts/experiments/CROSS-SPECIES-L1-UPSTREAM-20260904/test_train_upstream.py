import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("train_upstream", ROOT / "train_upstream.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None


try:
    SPEC.loader.exec_module(MODULE)
except ModuleNotFoundError as exc:
    if exc.name != "torch":
        raise
    MODULE = None


@unittest.skipIf(MODULE is None, "legacy training dependencies are unavailable")
class UpstreamTrainTest(unittest.TestCase):
    def test_D_overrides_only_worm_train_source(self):
        old = Path("/old")
        upstream = Path("/expanded")
        self.assertEqual(MODULE.training_sources(old, upstream, "L"), [])
        self.assertEqual(
            MODULE.training_sources(old, upstream, "D"),
            ["c_elegans=/expanded/TRAIN/c_elegans.jsonl.gz"],
        )

    def test_first_five_species_streams_are_unchanged_when_worm_pool_doubles(self):
        base = {
            species: [f"{species}:{index}" for index in range(8)]
            for species in MODULE.SPECIES
        }
        expanded = dict(base)
        expanded["c_elegans"] = [f"c_elegans:{index}" for index in range(16)]
        left = MODULE.legacy.SpeciesTileSampler(base, seed=42, arm="B1")
        right = MODULE.legacy.SpeciesTileSampler(expanded, seed=42, arm="B1")
        for _ in range(5):
            left_step = left.next_step()
            right_step = right.next_step()
            self.assertEqual(left_step[:5], right_step[:5])

    def test_train_passes_new_metadata_and_worm_override_to_legacy_loop(self):
        args = SimpleNamespace(
            arm="D",
            data_root=Path("/old"),
            upstream_root=Path("/expanded"),
            output_dir=Path("/out"),
            seed=42,
            max_steps=4000,
            warmup_steps=400,
        )
        with mock.patch.object(MODULE.legacy, "train") as train:
            MODULE.train(args)
        passed = train.call_args.args[0]
        self.assertEqual(passed.arm, "B1")
        self.assertEqual(passed.experiment_arm, "D")
        self.assertEqual(passed.run_role, MODULE.RUN_ROLE)
        self.assertEqual(passed.protocol, MODULE.PROTOCOL)
        self.assertEqual(passed.max_steps, MODULE.PILOT_STEPS)
        self.assertEqual(passed.warmup_steps, MODULE.PILOT_WARMUP_STEPS)
        self.assertEqual(
            passed.species_data,
            ["c_elegans=/expanded/TRAIN/c_elegans.jsonl.gz"],
        )


if __name__ == "__main__":
    unittest.main()
