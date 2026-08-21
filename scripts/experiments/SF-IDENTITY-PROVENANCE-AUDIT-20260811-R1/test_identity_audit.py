#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("identity_provenance_audit", HERE / "identity_provenance_audit.py")
audit = importlib.util.module_from_spec(SPEC); assert SPEC.loader
sys.modules[SPEC.name] = audit; SPEC.loader.exec_module(audit)


def candidate(accession: str, name: str, consensus: str, source: str = "dfam.0.h5"):
    return audit.Candidate(accession, accession + ".1", name, audit.sha256_text(consensus), source, 123,
                           audit.sha256_text(source))


def rm_line(identifier: str, raw_class: str, index: int) -> str:
    return f"100 0 0 0 chr1 {index + 1} {index + 1} (0) + {identifier} {raw_class} 1 1 (0) {index + 1}\n"


class SyntheticBackend:
    def __init__(self, names=None, accessions=None):
        self.names = names or {}; self.accessions = accessions or {}
    def exact_name(self, identifier): return list(self.names.get(identifier, []))
    def exact_accession(self, identifier): return list(self.accessions.get(identifier, []))


class IdentityAuditTests(unittest.TestCase):
    def test_real_pinned_h5_layout_has_only_partition3_without_byname(self):
        cfg = json.loads((PROJECT / "configs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1.yaml").read_text())
        manifest, summary = audit.validate_dfam_index_layout(PROJECT, cfg)
        self.assertEqual(summary["partition_count"], 12)
        self.assertEqual(summary["name_lookup_skipped_partition_count"], 1)
        self.assertEqual(summary["name_lookup_skipped_partitions"], [3])
        self.assertFalse(summary["full_partition_content_hashing_used"])
        self.assertTrue(all(item["lookup_by_name"] == (item["partition"] != 3) for item in manifest["partitions"]))

    def test_absent_byname_skips_but_present_query_errors_propagate(self):
        class BrokenLeaf:
            def get_family_by_name(self, _identifier):
                raise KeyError("corrupt lookup")
        self.assertEqual(audit.exact_name_query(BrokenLeaf(), "X", False), (None, True))
        with self.assertRaisesRegex(KeyError, "corrupt lookup"):
            audit.exact_name_query(BrokenLeaf(), "X", True)

    def test_h5_layout_missing_wrong_type_unreadable_and_drift_fail(self):
        import h5py
        database = {"name": "Dfam", "db_version": "3.9", "famdb_version": "2.0.0"}
        paths = {"lookup": "Lookup", "lookup_by_name": "Lookup/ByName",
                 "lookup_by_stage": "Lookup/ByStage", "lookup_by_taxon": "Lookup/ByTaxon"}
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            wrong = root / "wrong.h5"
            with h5py.File(wrong, "w") as handle:
                handle.attrs.update({"db_version": "3.9", "famdb_version": "2.0.0", "partition_num": 1})
                lookup = handle.create_group("Lookup")
                lookup.create_dataset("ByName", data=[1])
                lookup.create_group("ByStage"); lookup.create_group("ByTaxon")
            spec = {"partition": 1, "size_bytes": wrong.stat().st_size, "lookup": True, "lookup_by_name": True,
                    "lookup_by_stage": True, "lookup_by_taxon": True}
            with self.assertRaisesRegex(ValueError, "FAMDB_INDEX_WRONG_TYPE"):
                audit.validate_partition_layout(wrong, spec, database, paths)
            absent = root / "absent.h5"
            with h5py.File(absent, "w") as handle:
                handle.attrs.update({"db_version": "3.9", "famdb_version": "2.0.0", "partition_num": 3})
                lookup = handle.create_group("Lookup"); lookup.create_group("ByStage"); lookup.create_group("ByTaxon")
            absent_spec = {"partition": 3, "size_bytes": absent.stat().st_size, "lookup": True, "lookup_by_name": False,
                           "lookup_by_stage": True, "lookup_by_taxon": True}
            audit.validate_partition_layout(absent, absent_spec, database, paths)
            drifted = {**absent_spec, "lookup_by_name": True}
            with self.assertRaisesRegex(ValueError, "FAMDB_INDEX_LAYOUT_DRIFT"):
                audit.validate_partition_layout(absent, drifted, database, paths)
            unreadable = root / "unreadable.h5"; unreadable.write_text("not hdf5", encoding="utf-8")
            unreadable_spec = {**spec, "size_bytes": unreadable.stat().st_size}
            with self.assertRaises(Exception):
                audit.validate_partition_layout(unreadable, unreadable_spec, database, paths)

    def test_p_state_enumeration_is_hash_pinned_to_s0_behavior(self):
        cfg = json.loads((PROJECT / "configs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1.yaml").read_text())
        labeler, ontology, hard_terms = audit.load_s0_label_contract(PROJECT, cfg)
        for raw_class in ("Unknown", "Unknown?", "RC/Helitron", "Retroposon/SVA", "LINE/L1", "Simple_repeat"):
            state, expected, *_ = labeler.classify_annotation(raw_class, ontology, hard_terms)
            observed = audit.p_label(raw_class, labeler, ontology, hard_terms)
            self.assertEqual(observed, int(expected) if state == "P" else None, raw_class)

    def test_synthetic_rm_end_to_end_has_no_silent_label_contract_deletion(self):
        cfg = json.loads((PROJECT / "configs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1.yaml").read_text())
        labeler, ontology, hard_terms = audit.load_s0_label_contract(PROJECT, cfg)
        classes = (("id_unknown", "Unknown"), ("id_rc", "RC/Helitron"),
                   ("id_unknown_q", "Unknown?"), ("id_line_q", "LINE?"),
                   ("id_dna_q", "DNA?"), ("id_retro", "Retroposon/SVA"))
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); rm = root / "synthetic.out"
            rm.write_text("".join(rm_line(identifier, raw_class, index) for index, (identifier, raw_class) in enumerate(classes)),
                          encoding="utf-8")
            inventory, excluded, stats = audit.enumerate_p_identifiers(
                root, [{"self_out": "synthetic.out", "species_code": "synthetic"}], labeler, ontology, hard_terms)
        audit.validate_enumeration(inventory, excluded, stats)
        self.assertEqual(stats, {"parsed_annotation_records": 6, "p_records": 2,
                                 "provenance_candidate_records": 6,
                                 "label_contract_excluded_candidate_records": 4})
        self.assertEqual(set(inventory), {"id_unknown", "id_rc"})
        self.assertTrue(all(item["labels"] == {5} for item in inventory.values()))
        self.assertEqual(set(excluded), {"id_unknown_q", "id_line_q", "id_dna_q", "id_retro"})
        self.assertEqual(sum(item["occurrences"] for item in inventory.values()) +
                         sum(item["occurrences"] for item in excluded.values()), 6)

    def test_empty_zero_and_conservation_fail_as_integrity_errors(self):
        with self.assertRaisesRegex(ValueError, "total_records<=0"):
            audit.validate_enumeration({}, {}, {})
        inventory = {"A": {"occurrences": 1, "labels": {1}, "species": {"s"}}}
        excluded = {"B": {"occurrences": 1, "raw_classes": {"LINE?"}, "species": {"s"}}}
        with self.assertRaisesRegex(ValueError, "sum\(identifier occurrences\)"):
            audit.validate_enumeration(inventory, excluded, {"parsed_annotation_records": 2, "p_records": 2,
                                       "label_contract_excluded_candidate_records": 1, "provenance_candidate_records": 3})
        with self.assertRaisesRegex(ValueError, "P\+excluded candidate count conservation"):
            audit.validate_enumeration(inventory, excluded, {"parsed_annotation_records": 3, "p_records": 1,
                                       "label_contract_excluded_candidate_records": 1, "provenance_candidate_records": 3})
        self.assertEqual(audit.terminal_exit_code("AUDIT_FAILED"), 2)

    def test_exact_name_precedes_accession(self):
        named = candidate("DF0001", "MIR", "AAAA")
        accession = candidate("MIR", "different", "CCCC")
        result = audit.resolve_identifier("MIR", SyntheticBackend({"MIR": [named]}, {"MIR": [accession]}))
        self.assertEqual((result["status"], result["resolution_method"], result["versioned_accession"]),
                         ("resolved", "exact_dfam_name", "DF0001.1"))

    def test_exact_accession_explicitly_covers_dr002419729(self):
        item = candidate("DR002419729", "rnd-1_family-354", "ACGT")
        result = audit.resolve_identifier("DR002419729", SyntheticBackend(accessions={"DR002419729": [item]}))
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["resolution_method"], "exact_dfam_accession")
        self.assertEqual(result["versioned_accession"], "DR002419729.1")

    def test_missing_is_fail_closed_without_prefix_guess(self):
        backend = SyntheticBackend(names={"ABC1": [candidate("DF1", "ABC1", "AAAA")]})
        result = audit.resolve_identifier("ABC", backend)
        self.assertEqual((result["status"], result["candidate_count"]), ("missing", 0))

    def test_ambiguous_exact_accession_is_counted(self):
        backend = SyntheticBackend(accessions={"DR1": [candidate("DR1", "a", "AAAA", "p0"),
                                                         candidate("DR1", "b", "CCCC", "p1")]})
        result = audit.resolve_identifier("DR1", backend)
        self.assertEqual((result["status"], result["candidate_count"]), ("ambiguous", 2))

    def test_same_exact_name_different_consensus_is_ambiguous(self):
        backend = SyntheticBackend(names={"SAME": [candidate("DF1", "SAME", "AAAA", "p0"),
                                                        candidate("DF2", "SAME", "CCCC", "p1")]})
        result = audit.resolve_identifier("SAME", backend)
        self.assertEqual(result["status"], "ambiguous")

    def test_duplicate_consensus_keeps_resolution_unique_but_forces_homology_human_gate(self):
        backend = SyntheticBackend(names={"A": [candidate("DF1", "A", "AAAA")],
                                          "B": [candidate("DF2", "B", "AAAA")]})
        inventory = {"A": {"occurrences": 2, "labels": {1}, "species": {"s1"}},
                     "B": {"occurrences": 3, "labels": {2}, "species": {"s2"}}}
        rows, metrics = audit.audit_inventory(inventory, backend, [], 5)
        self.assertEqual(metrics["duplicate_consensus_group_count"], 1)
        self.assertEqual(metrics["duplicate_consensus_identifier_count"], 2)
        self.assertEqual(metrics["ambiguous_identifier_count"], 0)
        self.assertEqual(metrics["resolved_unique_identifier_count"], 2)
        self.assertEqual(metrics["label_conflict_identifier_count"], 0)
        self.assertFalse(metrics["accession_contract_100pct_unique_provenance"])
        self.assertTrue(metrics["human_gate_revision_required"])
        self.assertFalse(metrics["automatic_cluster_authorized"])
        self.assertTrue(all(math.isfinite(float(value)) for value in metrics.values() if isinstance(value, (int, float))))
        self.assertEqual(sum(bool(row["duplicate_consensus"]) for row in rows), 2)
        self.assertTrue(all(row["resolution_status"] == "resolved" for row in rows))

    def test_label_conflict_is_separate_from_resolution_status(self):
        backend = SyntheticBackend(names={"C": [candidate("DF3", "C", "CCCC")]})
        inventory = {"C": {"occurrences": 2, "labels": {1, 4}, "species": {"s"}}}
        rows, metrics = audit.audit_inventory(inventory, backend, [], 2)
        self.assertEqual(metrics["label_conflict_identifier_count"], 1)
        self.assertEqual(metrics["resolved_unique_identifier_count"], 1)
        self.assertEqual(rows[0]["resolution_status"], "resolved")

    def test_required_accession_must_resolve_by_accession(self):
        backend = SyntheticBackend(names={"DR002419729": [candidate("DF1", "DR002419729", "AAAA")]})
        inventory = {"DR002419729": {"occurrences": 1, "labels": {1}, "species": {"s"}}}
        _rows, metrics = audit.audit_inventory(inventory, backend, ["DR002419729"], 1)
        self.assertEqual(metrics["required_accession_failure_count"], 1)
        self.assertTrue(metrics["human_gate_revision_required"])

    def test_typed_block_is_valid_negative_rc0_but_integrity_failure_is_rc2(self):
        inventory = {"MISSING": {"occurrences": 1, "labels": {1}, "species": {"s"}}}
        _rows, metrics = audit.audit_inventory(inventory, SyntheticBackend(), [], 1)
        status = audit.provenance_terminal(metrics)
        self.assertEqual(status, "IDENTITY_PROVENANCE_TYPED_BLOCK")
        self.assertTrue(metrics["semantic_success"])
        self.assertTrue(metrics["valid_negative"])
        self.assertEqual(audit.terminal_exit_code("IDENTITY_PROVENANCE_TYPED_BLOCK"), 0)
        self.assertEqual(audit.terminal_exit_code("PROVENANCE_COMPLETE"), 0)
        self.assertEqual(audit.terminal_exit_code("AUDIT_FAILED"), 2)

    def test_formal_slurm_guard(self):
        old = os.environ.pop("SLURM_JOB_ID", None)
        try:
            with self.assertRaisesRegex(ValueError, "FORMAL_SLURM_GUARD"):
                audit.run_audit(Path("/tmp"), {"preview_root": "x"}, "x")
        finally:
            if old is not None: os.environ["SLURM_JOB_ID"] = old

    def test_atomic_preview_manifest_and_finite_metrics(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); preview = root / "outputs/X/preview"; preview.mkdir(parents=True)
            cfg = {"exp_id": "X", "preview_root": "outputs/X/preview"}
            audit.atomic_json(preview / "input_manifest.json", {"x": 1})
            audit.atomic_json(preview / "static_contract.json", {"x": 1})
            metrics = {"unique_provenance_coverage": 0.0, "human_gate_revision_required": False}
            report = {"answer": "NOT_RUN"}
            audit.finalize_preview(root, cfg, "IMPLEMENTED_NOT_RUN", "static", metrics, report)
            lines = (preview / "output_manifest.sha256").read_text().splitlines()
            self.assertTrue(lines)
            for line in lines:
                expected, relpath = line.split("  ", 1)
                self.assertFalse(Path(relpath).is_absolute())
                self.assertEqual(audit.sha256_file(root / relpath), expected)
            self.assertNotIn("output_manifest.sha256", "\n".join(lines))
            self.assertEqual((preview / "STATUS").read_text().strip(), "IMPLEMENTED_NOT_RUN")


if __name__ == "__main__":
    unittest.main()
