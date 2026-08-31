#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("sample_joint_panel", HERE / "sample_joint_panel.py")
assert SPEC is not None and SPEC.loader is not None
sample = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sample)


def manifest_fixture() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    panel_rank = {panel: 0 for panel in sample.PANELS}
    package_index = 0
    for stratum, cells in (("S0", sample.S0_CELLS), ("S1", sample.S1_CELLS)):
        for cell in cells:
            for panel in sample.PANELS:
                if panel == "main":
                    count = 15 if stratum == "S0" else 20
                elif panel == "calibration":
                    count = 2 if stratum == "S1" else (2 if cell in ("S0-L1", "S0-L2") else 1)
                else:
                    count = 20 if cell == cells[0] else 0
                for _ in range(count):
                    panel_rank[panel] += 1
                    start = package_index * 100
                    rows.append(
                        {
                            "package_id": f"{stratum}-{package_index:03d}",
                            "role": panel,
                            "role_rank": str(panel_rank[panel]),
                            "reserve_pair_rank": "",
                            "unit_type": stratum,
                            "hard_cell": cell,
                            "seqid": "2L",
                            "package_start0": str(start),
                            "package_end0": str(start + 10),
                        }
                    )
                    package_index += 1

    reserve = [row for row in rows if row["role"] == "reserve"]
    reserve_s0 = [row for row in reserve if row["unit_type"] == "S0"]
    reserve_s1 = [row for row in reserve if row["unit_type"] == "S1"]
    for rank, pair in enumerate(zip(reserve_s0, reserve_s1), start=1):
        for row in pair:
            row["reserve_pair_rank"] = str(rank)
    return rows


class SampleJointPanelTest(unittest.TestCase):
    def test_package_manifest_is_the_v1_challenge_panel_schema(self) -> None:
        self.assertIn("selection_priority", sample.PACKAGE_FIELDS)
        self.assertIn("hard_cell", sample.PACKAGE_FIELDS)
        self.assertNotIn("inclusion_probability", sample.PACKAGE_FIELDS)

    def test_s0_and_s1_hard_cells(self) -> None:
        self.assertEqual(sample.challenge_cell({"unit_id": "a", "unit_type": "S0", "core_length": "79"}), "S0-L1")
        self.assertEqual(sample.challenge_cell({"unit_id": "b", "unit_type": "S0", "core_length": "499"}), "S0-L2")
        self.assertEqual(sample.challenge_cell({"unit_id": "c", "unit_type": "S0", "core_length": "999"}), "S0-L3")
        self.assertEqual(sample.challenge_cell({"unit_id": "d", "unit_type": "S0", "core_length": "1000"}), "S0-L4")
        self.assertEqual(
            sample.challenge_cell({"unit_id": "e", "unit_type": "S1", "feature_count": "2", "max_overlap_depth": "2"}),
            "S1-C1",
        )
        self.assertEqual(
            sample.challenge_cell({"unit_id": "f", "unit_type": "S1", "feature_count": "3", "max_overlap_depth": "2"}),
            "S1-C2",
        )
        self.assertEqual(
            sample.challenge_cell({"unit_id": "g", "unit_type": "S1", "feature_count": "2", "max_overlap_depth": "3"}),
            "S1-C3",
        )

    def test_touching_intervals_do_not_conflict_but_overlap_does(self) -> None:
        rows = [
            {"unit_id": "a", "seqid": "2L", "package_start0": "0", "package_end0": "10"},
            {"unit_id": "b", "seqid": "2L", "package_start0": "10", "package_end0": "20"},
            {"unit_id": "c", "seqid": "2L", "package_start0": "19", "package_end0": "30"},
            {"unit_id": "d", "seqid": "3R", "package_start0": "0", "package_end0": "100"},
        ]
        self.assertEqual(sample.overlapping_pairs(rows), [(1, 2)])

    def test_fixture_has_exact_quotas_and_global_nonoverlap(self) -> None:
        sample.validate_manifest(manifest_fixture())

    def test_validation_rejects_selected_overlap(self) -> None:
        rows = manifest_fixture()
        rows[1]["package_start0"] = rows[0]["package_start0"]
        with self.assertRaisesRegex(ValueError, "expanded packages overlap"):
            sample.validate_manifest(rows)

    def test_sbatch_is_cpu_only_and_attempt_scoped(self) -> None:
        text = (HERE / "submit_joint_panel.sbatch").read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertNotIn("#SBATCH --gres", text)
        self.assertIn("joint-panel-${ATTEMPT_TAG}", text)
        self.assertIn("joint-panel-%j.out", text)
        self.assertIn("POPULATION_ATTEMPT_TAG", text)


if __name__ == "__main__":
    unittest.main()
