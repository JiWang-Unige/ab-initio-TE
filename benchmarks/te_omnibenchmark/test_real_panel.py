#!/usr/bin/env python3
"""Small interval and denominator-contract tests for the real panel module."""
from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from benchmarks.te_omnibenchmark import real_panel


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_canonical(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\t".join(real_panel.CANONICAL_FIELDS) + "\n")
        for row in rows:
            handle.write("\t".join(row.get(field, ".") for field in real_panel.CANONICAL_FIELDS) + "\n")


class RealPanelContractTests(unittest.TestCase):
    def test_explicit_repeatmasker_class_precedes_subtype_or_name(self) -> None:
        for label, expected in [
            ("SINE/tRNA", "known_te"),
            ("tRNA", "non_te"),
            ("LINE/L1", "known_te"),
            ("PLE/Chlamys", "unknown_or_ambiguous"),
            ("DNA?", "unknown_or_ambiguous"),
            ("Unrecognized/family", "unknown_or_ambiguous"),
        ]:
            with self.subTest(label=label):
                self.assertEqual(real_panel.classify_bucket({
                    "name": "RNA_like_fragment", "source": "RepeatMasker",
                    "attributes": f"class_family={label}",
                }), expected)
        self.assertEqual(real_panel.classify_bucket({"name": "LINE_fragment"}), "unknown_or_ambiguous")

    def make_bundle(self, root: Path) -> tuple[Path, Path]:
        panels = {}
        for species in real_panel.SPECIES:
            path = root / "panels" / f"{species}.json"
            write_json(
                path,
                {
                    "schema": "te_real_panel_compact_panel_v1",
                    "species": species,
                    "regions": [
                        {
                            "short_id": "r01",
                            "length_bp": 20,
                            "callable_bp": 18,
                            "callable_intervals": [[0, 10], [12, 20]],
                        }
                    ],
                    "input_bp": 20,
                    "callable_bp": 18,
                },
            )
            panels[species] = str(path.relative_to(root))

        completed_id = "platypus|fixed_rm"
        blocked_id = "platypus|hite"
        completed_dir = root / "cells" / "platypus__fixed_rm"
        blocked_dir = root / "cells" / "platypus__hite"
        write_json(completed_dir / "status.json", {"status": "COMPLETED", "cell_id": completed_id})
        write_json(blocked_dir / "status.json", {"status": "BLOCKED", "cell_id": blocked_id, "reason": "fixture blocked"})
        rows = [
            {
                "seqid": "r01", "start": "0", "end": "5", "name": "L1_fragment",
                "score": ".", "strand": "+", "source": "RepeatMasker",
                "attributes": "class_family=LINE/L1",
            },
            {
                "seqid": "r01", "start": "5", "end": "8", "name": "simple_repeat",
                "score": ".", "strand": "+", "source": "RepeatMasker",
                "attributes": "class_family=Simple_repeat",
            },
            {
                "seqid": "r01", "start": "12", "end": "15", "name": "Unknown",
                "score": ".", "strand": "+", "source": "RepeatMasker",
                "attributes": "class_family=Unknown",
            },
        ]
        write_canonical(completed_dir / "predictions.tsv", rows)
        expected = [
            {
                "cell_id": completed_id, "species": "platypus", "method": "fixed_rm",
                "task": "T2", "device": "cpu", "role": "native_slurm", "expected_status": "COMPLETED",
            },
            {
                "cell_id": blocked_id, "species": "platypus", "method": "hite",
                "task": "T2", "device": "cpu", "role": "native_slurm", "expected_status": "COMPLETED",
            },
        ]
        registry = {
            "schema": "te_real_panel_registry_v1",
            "protocol": "TE-REAL-PANEL-BENCH-20260914",
            "truth_available": False,
            "expected_cells": expected,
        }
        write_json(root / "cell_registry.json", registry)
        manifest = {
            "schema": "te_real_panel_compact_bundle_v1",
            "protocol": "TE-REAL-PANEL-BENCH-20260914",
            "bundle_root": str(root),
            "cell_registry": "cell_registry.json",
            "panels": panels,
            "cells": [
                {
                    "cell_id": completed_id,
                    "status": "COMPLETED",
                    "status_path": "cells/platypus__fixed_rm/status.json",
                    "prediction_path": "cells/platypus__fixed_rm/predictions.tsv",
                },
                {
                    "cell_id": blocked_id,
                    "status": "BLOCKED",
                    "status_path": "cells/platypus__hite/status.json",
                    "prediction_path": None,
                },
            ],
            "raw_fasta_copied": False,
            "probabilities_copied": False,
        }
        write_json(root / "manifest.json", manifest)
        return root / "manifest.json", root / "cell_registry.json"

    def test_interval_contract(self) -> None:
        self.assertEqual(
            real_panel.merge_intervals([(0, 4), (4, 8), (10, 12), (11, 15)]),
            [(0, 8), (10, 15)],
        )
        self.assertEqual(real_panel.intersection_length([(0, 8), (10, 15)], [(4, 12)]), 6)

    def test_score_buckets_callable_and_blocked_denominator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, registry = self.make_bundle(Path(temporary))
            output = Path(temporary) / "metrics"
            result = real_panel.score_bundle(manifest, registry, output)
            self.assertEqual(result["expected_cell_count"], 2)
            self.assertIsNone(result["absolute_precision"])
            self.assertIsNone(result["absolute_f1"])
            scored = next(row for row in result["cells"] if row["cell_id"] == "platypus|fixed_rm")
            self.assertEqual(scored["status"], "COMPLETED")
            self.assertEqual(scored["metrics"]["coverage_bp"], 11)
            self.assertEqual(scored["metrics"]["callable_coverage_bp"], 11)
            self.assertEqual(scored["metrics"]["candidate_fragment_count"], 3)
            buckets = scored["metrics"]["by_bucket"]
            self.assertEqual(buckets["known_te"]["callable_coverage_bp"], 5)
            self.assertEqual(buckets["non_te"]["callable_coverage_bp"], 3)
            self.assertEqual(buckets["unknown_or_ambiguous"]["callable_coverage_bp"], 3)
            blocked = next(row for row in result["cells"] if row["cell_id"] == "platypus|hite")
            self.assertEqual(blocked["status"], "BLOCKED")
            self.assertIsNone(blocked["metrics"])
            self.assertEqual(result["pairwise"][0]["status"], "NOT_SCORED")

    def test_collector_missing_cell_is_notrun(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, registry = self.make_bundle(root)
            metrics_path = root / "metrics.json"
            write_json(
                metrics_path,
                {
                    "schema": "te_real_panel_t2_metrics_v1",
                    "cells": [{"cell_id": "platypus|fixed_rm", "status": "COMPLETED", "metrics": {"candidate_fragment_count": 3}}],
                },
            )
            result = real_panel.collect_summary([metrics_path], [registry], root / "summary")
            missing = next(row for row in result["cells"] if row["cell_id"] == "platypus|hite")
            self.assertEqual(missing["status"], "NOTRUN")
            self.assertEqual(missing["evidence"], "registry_only")
            self.assertIsNone(missing["metrics"])
            self.assertEqual(result["status_counts"]["NOTRUN"], 1)

    def test_data_stage_materializes_only_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            manifest, _ = self.make_bundle(bundle)
            source_manifest = json.loads(manifest.read_text())
            source_manifest['bundle_root'] = '/remote/baobab/compact_bundle'
            write_json(manifest, source_manifest)
            output = Path(temporary) / "data"
            real_panel.run_data(Namespace(bundle=bundle, output_dir=output))
            self.assertTrue((output / "bundle_manifest.json").is_file())
            self.assertTrue((output / "cell_registry.json").is_file())
            self.assertFalse((output / "panel_regions.fa").exists())
            materialized = json.loads((output / "bundle_manifest.json").read_text())
            self.assertEqual(materialized["stage_source_manifest"], str(manifest.resolve()))
            self.assertEqual(materialized["bundle_root"], str(bundle.resolve()))
            self.assertEqual(materialized["bundle_root_source"], '/remote/baobab/compact_bundle')
            result = real_panel.score_bundle(output/'bundle_manifest.json', output/'cell_registry.json', Path(temporary)/'scores')
            self.assertEqual(result['expected_cell_count'], 2)
            self.assertEqual(result['cells'][0]['status'], 'COMPLETED')


if __name__ == "__main__":
    unittest.main()
