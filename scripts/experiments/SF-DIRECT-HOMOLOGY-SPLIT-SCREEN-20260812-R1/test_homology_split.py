#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("build_homology_split", HERE / "build_homology_split.py")
gate = importlib.util.module_from_spec(SPEC); assert SPEC.loader
sys.modules[SPEC.name] = gate; SPEC.loader.exec_module(gate)
CONFIG = PROJECT / "configs/SF-DIRECT-HOMOLOGY-SPLIT-SCREEN-20260812-R1.yaml"


def cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


class HomologySplitTests(unittest.TestCase):
    def test_real_static_contract_and_partition3_layout(self):
        summary = gate.validate_static_inputs(PROJECT, cfg(), False)
        self.assertEqual(summary["mmseqs_version"], "13.45111")
        self.assertTrue(summary["partition3_only_without_byname"])
        self.assertEqual(summary["canonical_species_rows"], 15)
        self.assertEqual(summary["primary_clade_overlap_count"], 0)

    def test_index_independent_exact_name_scan_only_without_byname(self):
        import h5py
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "p3.h5"
            with h5py.File(path, "w") as handle:
                families = handle.create_group("Families/DR/00/00/01")
                a = families.create_dataset("DF000001", data=[1])
                a.attrs.update({"name": "L2a", "accession": "DF000001", "version": 2, "consensus": "ACGT"})
                b = families.create_dataset("DF000002", data=[1])
                b.attrs.update({"name": "OTHER", "accession": "DF000002", "version": 1, "consensus": "CCCC"})
                handle.create_group("Lookup")
            found, audit = gate.scan_exact_names_without_index(path, {"L2a", "MISSING"})
            self.assertEqual(set(found), {"L2a"})
            self.assertEqual(found["L2a"][0]["versioned_accession"], "DF000001.2")
            self.assertEqual(audit["family_datasets_scanned"], 2)
            with h5py.File(path, "a") as handle:
                handle.create_group("Lookup/ByName")
            with self.assertRaisesRegex(ValueError, "FORBIDDEN_WHEN_BYNAME_PRESENT"):
                gate.scan_exact_names_without_index(path, {"L2a"})

    def test_metadata_duplicate_exact_name_is_preserved_for_ambiguity(self):
        import h5py
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "p3.h5"
            with h5py.File(path, "w") as handle:
                group = handle.create_group("Families/Aux/x1")
                for accession, sequence in (("A", "AAAA"), ("B", "CCCC")):
                    item = group.create_dataset(accession, data=[1])
                    item.attrs.update({"name": "SAME", "accession": accession, "version": 1, "consensus": sequence})
                handle.create_group("Lookup")
            found, _ = gate.scan_exact_names_without_index(path, {"SAME"})
            self.assertEqual(len(found["SAME"]), 2)

    def test_graph_components_are_undirected_and_transitive(self):
        edges = [{"query": "A", "target": "B"}, {"query": "B", "target": "C"}]
        mapping, components = gate.connected_components({"A", "B", "C", "D"}, edges)
        self.assertEqual(mapping["A"], mapping["C"])
        self.assertNotEqual(mapping["A"], mapping["D"])
        self.assertEqual(sorted(map(len, components.values())), [1, 3])

    def test_parse_edges_enforces_identity_and_bilateral_coverage(self):
        policy = {"min_sequence_identity": 0.8, "min_query_and_target_coverage": 0.8}
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "hits.tsv"
            path.write_text("A\tB\t85\t90\t100\t100\t1e-10\t50\nB\tA\t86\t90\t100\t100\t1e-11\t60\n")
            edges = gate.parse_edges(path, {"A", "B"}, policy)
            self.assertEqual(len(edges), 1)
            self.assertAlmostEqual(edges[0]["identity"], 0.86)
            path.write_text("A\tB\t90\t70\t100\t100\t1e-10\t50\n")
            with self.assertRaisesRegex(ValueError, "BELOW_THRESHOLD"):
                gate.parse_edges(path, {"A", "B"}, policy)

    def test_component_main4_label_conflict_is_explicit(self):
        components = {"HC": ["A", "B"], "SINGLE": ["U"]}
        rows = [{"identifier": "A", "labels": "LINE"}, {"identifier": "B", "labels": "LTR"},
                {"identifier": "U", "labels": "Unknown"}]
        conflicts = gate.component_main4_conflicts(components, rows)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["main4_labels"], "LINE;LTR")

    def test_split_precedence_primary_audit_ambiguity_and_stable_fit(self):
        config = cfg(); components = {"p": ["P"], "a": ["A"], "x": ["X13_LINE"], "f": ["F"]}
        counts = Counter({("P", "test"): 1, ("A", "stress"): 1, ("X13_LINE", "train"): 1, ("F", "train"): 1})
        meta = {"test": {"role": "mammal_holdout", "order_taxid": "1"},
                "stress": {"role": "optional_stress", "order_taxid": "2"},
                "train": {"role": "train_core", "order_taxid": "3"}}
        rows, mapping = gate.assign_components(config, components, counts, meta, {"X13_LINE"})
        self.assertEqual(mapping["P"], "test_primary")
        self.assertEqual(mapping["A"], "audit_optional_stress")
        self.assertEqual(mapping["X13_LINE"], "ambiguity_stratum")
        self.assertIn(mapping["F"], {"train", "val"})
        self.assertEqual(len(rows), 4)

    def test_primary_role_dominates_fit_when_component_spans_both(self):
        config = cfg(); components = {"c": ["A", "B"]}
        counts = Counter({("A", "train"): 4, ("B", "test"): 3})
        meta = {"train": {"role": "train_core", "order_taxid": "1"},
                "test": {"role": "invertebrate_holdout", "order_taxid": "2"}}
        _rows, mapping = gate.assign_components(config, components, counts, meta, set())
        self.assertEqual(mapping, {"A": "test_primary", "B": "test_primary"})

    def test_audit_split_conserves_direct_labels_occurrences_and_zero_overlap(self):
        config = cfg(); config["label_contract"]["ambiguity_identifiers"] = []
        identity = [{"identifier": "A", "occurrences": "2", "labels": "LINE"},
                    {"identifier": "B", "occurrences": "1", "labels": "LTR"}]
        excluded = [{"identifier": str(i)} for i in range(10)]
        scan = {"identifier_species": Counter({("A", "train"): 2, ("B", "test"): 1}),
                "labels": {"A": {2}, "B": {3}}}
        stats = {"p_records": 3, "parsed_annotation_records": 5}
        component_map = {"A": "ca", "B": "cb"}; split_map = {"A": "train", "B": "test_primary"}
        meta = {"train": {"role": "train_core", "order_taxid": "1"},
                "test": {"role": "mammal_holdout", "order_taxid": "2"}}
        metrics = gate.audit_split(config, identity, excluded, scan, stats, component_map, split_map, meta, [],
                                   {"ca": ["A"], "cb": ["B"]},
                                   [{"identifier": "A", "sequence_source": "dfam"},
                                    {"identifier": "B", "sequence_source": "dfam"}])
        self.assertEqual(metrics["homology_component_overlap_count"], 0)
        self.assertEqual(metrics["primary_clade_overlap_count"], 0)
        self.assertEqual(metrics["primary_eligible_p_record_coverage"], 1.0)
        self.assertFalse(metrics["sequence_used_as_prediction_label"])

    def test_direct_label_or_occurrence_drift_fails(self):
        config = cfg(); config["label_contract"]["ambiguity_identifiers"] = []
        identity = [{"identifier": "A", "occurrences": "1", "labels": "LINE"}]
        base = dict(cfg=config, identity_rows=identity, excluded_rows=[{}] * 10,
                    stats={"p_records": 1, "parsed_annotation_records": 1}, component_map={"A": "c"},
                    split_map={"A": "train"}, species_meta={"s": {"role": "train_core", "order_taxid": "1"}},
                    edges=[], components={"c": ["A"]}, sequence_rows=[{"sequence_source": "dfam"}])
        with self.assertRaisesRegex(ValueError, "LABEL_CONSERVATION"):
            gate.audit_split(scan={"identifier_species": Counter({("A", "s"): 1}), "labels": {"A": {3}}}, **base)
        with self.assertRaisesRegex(ValueError, "OCCURRENCE_CONSERVATION"):
            gate.audit_split(scan={"identifier_species": Counter({("A", "s"): 2}), "labels": {"A": {2}}}, **base)

    def test_mmseqs_command_is_frozen_and_not_metric_selected(self):
        config = cfg()
        with tempfile.TemporaryDirectory() as name, mock.patch.object(subprocess, "run") as run:
            command = gate.run_mmseqs(config, Path(name) / "in.fa", Path(name) / "hits", Path(name) / "tmp")
        run.assert_called_once_with(command, check=True)
        self.assertIn("--min-seq-id", command); self.assertIn("--cov-mode", command)
        self.assertIn("never selected", config["homology_search"]["threshold_selection_source"])
        self.assertFalse(config["representative_policy"]["genome_copy_fallback"])

    def test_x13_is_graph_external_without_fake_n_sequence(self):
        source = (HERE / "build_homology_split.py").read_text(encoding="utf-8")
        self.assertNotIn('"N" *', source)
        self.assertNotIn("genome_copy_representatives", source)
        mapping, components = gate.connected_components({"A"}, [])
        component = "HC_AMBIGUITY_" + gate.sha256_text("X13_LINE")[:16]
        mapping["X13_LINE"] = component; components[component] = ["X13_LINE"]
        self.assertEqual(components[component], ["X13_LINE"])

    def test_formal_requires_slurm(self):
        old = os.environ.pop("SLURM_JOB_ID", None)
        try:
            with self.assertRaisesRegex(ValueError, "FORMAL_SLURM_GUARD"):
                gate.run_formal(Path("/tmp"), {"preview_root": "x"}, "attempt")
        finally:
            if old is not None: os.environ["SLURM_JOB_ID"] = old

    def test_typed_block_is_semantic_rc0_and_failure_rc2(self):
        exc = gate.DataTypedBlock("UNRESOLVED_DFAM_CONSENSUS", {"unresolved_identifier_count": 2})
        self.assertEqual(exc.code, "UNRESOLVED_DFAM_CONSENSUS")
        self.assertEqual(exc.details["unresolved_identifier_count"], 2)
        self.assertEqual(gate.terminal_exit_code("DATA_TYPED_BLOCK"), 0)
        self.assertEqual(gate.terminal_exit_code("AUDIT_FAILED"), 2)

    def test_atomic_preview_manifest_and_payload_tamper(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); preview = root / "outputs/X/preview"; preview.mkdir(parents=True)
            config = {"exp_id": "X", "preview_root": "outputs/X/preview"}
            gate.atomic_json(preview / "input_manifest.json", {"x": 1})
            gate.atomic_json(preview / "static_contract.json", {"x": 1})
            gate.finalize_preview(root, config, "IMPLEMENTED_NOT_RUN", "static", {"semantic_success": False}, {"x": 1})
            for line in (preview / "output_manifest.sha256").read_text().splitlines():
                expected, relpath = line.split("  ", 1)
                self.assertEqual(gate.sha256_file(root / relpath), expected)
            stage = root / "stage"; stage.mkdir()
            required = ["sequence_sources.tsv", "representatives.split_only.fa", "homology_edges.tsv", "homology_components.tsv",
                        "component_assignments.tsv", "identifier_assignments.tsv", "label_contract_excluded.tsv",
                        "ambiguity_stratum.tsv", "metrics.json", "report.json", "RUN_MANIFEST.json"]
            for filename in required: (stage / filename).write_text(filename)
            gate.create_payload_manifest(stage); gate.verify_payload(stage)
            (stage / "metrics.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "PAYLOAD_DRIFT"):
                gate.verify_payload(stage)

    def test_sbatch_is_cpu_only_guarded_and_bounded(self):
        text = (PROJECT / "sbatch/SF-DIRECT-HOMOLOGY-SPLIT-SCREEN-20260812-R1.sbatch").read_text()
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertIn("#SBATCH --time=06:00:00", text)
        self.assertNotIn("#SBATCH --gres", text)
        self.assertIn("pre_submit_gate.py", text)
        self.assertIn('test -z "${SLURM_JOB_GPUS:-}"', text)
        self.assertLess(text.index("set -eo pipefail"), text.index("conda activate te_benchmark"))
        self.assertGreater(text.index("set -u"), text.index("conda activate te_benchmark"))


if __name__ == "__main__":
    unittest.main()
