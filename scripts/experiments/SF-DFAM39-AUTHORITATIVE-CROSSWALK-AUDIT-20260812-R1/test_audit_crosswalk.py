#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXP = "SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1"
CONFIG = ROOT / f"configs/{EXP}.yaml"
SPEC = importlib.util.spec_from_file_location("crosswalk_audit", HERE / "audit_crosswalk.py")
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(audit)


def cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def target(identifier: str, occurrences: int = 1, label: str = "LINE", species: str = "human") -> dict:
    return {"identifier": identifier, "occurrences": str(occurrences), "labels": label, "species": species,
            "status": "missing", "resolution_status": "missing", "resolution_method": "none"}


def embl_record(accession: str, version: int, sequence: str, nm: str = "", aliases: list[tuple[str, str]] | None = None) -> str:
    lines = [f"ID   {accession}; SV {version}; linear; DNA; STD; UNC; {len(sequence)} BP."]
    if nm:
        lines.append(f"NM   {nm}")
    lines += ["XX", f"AC   {accession};", "XX"]
    for field, value in aliases or []:
        lines.append(f"{field}   {value}")
    lines += ["XX", f"SQ   Sequence {len(sequence)} BP;", f"     {sequence.lower()}  {len(sequence)}", "//"]
    return "\n".join(lines) + "\n"


def write_fixture(path: Path, records: list[str]) -> dict:
    text = "CC   Release: Dfam_3.9\n" + "".join(records)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)
    config = cfg()
    counts = {field: sum(1 for line in text.splitlines() if line.startswith(field + "   "))
              for field in ("ID", "NM", "AC", "PI", "SN", "DR", "SQ")}
    config["curated_embl"] = dict(config["curated_embl"])
    config["curated_embl"]["expected_record_count"] = len(records)
    config["curated_embl"]["expected_sequence_record_count"] = len(records)
    config["curated_embl"]["expected_field_counts"] = counts
    return config


class CrosswalkAuditTests(unittest.TestCase):
    def test_real_frozen_inputs_and_contract_are_exact(self):
        config = cfg()
        inputs = audit.validate_pinned_inputs(ROOT, config)
        self.assertEqual((len(inputs["targets"]), inputs["target_occurrence_mass"]), (279, 6432583))
        self.assertEqual((len(inputs["excluded"]), inputs["excluded_occurrence_mass"]), (10, 43728))
        self.assertEqual((inputs["x13"][0]["identifier"], inputs["x13_occurrence_mass"]), ("X13_LINE", 686))
        self.assertEqual(config["source_contract"]["exact_relation_fields"],
                         ["NM", "PI", "SN", "DR", "AC", "ID"])
        self.assertEqual(config["source_contract"]["exact_alias_fields"], ["NM", "PI", "SN", "DR"])
        self.assertEqual(config["source_contract"]["exact_identity_fields"], ["AC", "ID"])
        self.assertEqual(config["resource_contract"], {"cpus": 1, "memory_gib": 2,
                                                       "walltime_minutes": 20, "gpus": 0})
        self.assertTrue(all(value is False for value in audit.authorization_flags().values()))

    def test_parser_nm_canonical_id_version_and_sequence_hash(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"
            config = write_fixture(path, [embl_record("DF000000001", 4, "ACGU", "MIR",
                                                        [("DR", "Repbase; MIR_ALIAS.")])])
            records, shape = audit.parse_curated_embl(path, config)
            self.assertEqual(shape["field_counts"], {"ID": 1, "NM": 1, "AC": 1,
                                                       "PI": 0, "SN": 0, "DR": 1, "SQ": 1})
            self.assertEqual(records[0]["canonical_name"], "MIR")
            self.assertEqual(records[0]["versioned_accession"], "DF000000001.4")
            self.assertEqual(records[0]["consensus_sha256"], audit.sha256_text("ACGT"))

    def test_nm_missing_record_is_legal_but_cannot_nm_match(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"
            config = write_fixture(path, [embl_record("DF000000010", 1, "ACGT", "",
                                                        [("DR", "Repbase; LEGACY.")])])
            records, shape = audit.parse_curated_embl(path, config)
            self.assertEqual(shape["field_counts"]["NM"], 0)
            candidates, resolution, metrics = audit.build_crosswalk([target("LEGACY")], records)
            self.assertEqual(candidates[0]["relation_field"], "DR")
            self.assertEqual(resolution[0]["resolution_status"], "invalid_metadata")
            self.assertEqual(metrics["invalid_metadata_identifier_count"], 1)
            missing_candidates, missing_resolution, _ = audit.build_crosswalk([target("NOT_PRESENT")], records)
            self.assertEqual(missing_candidates, [])
            self.assertEqual(missing_resolution[0]["resolution_status"], "missing")

    def test_exact_alias_and_accession_identity_no_prefix_or_casefold(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"
            config = write_fixture(path, [embl_record("DF000000010", 2, "ACGT", "Canonical",
                                                        [("DR", "Repbase; LegacyName.")])])
            records, _ = audit.parse_curated_embl(path, config)
            targets = [target(value) for value in ("Canonical", "LegacyName", "DF000000010",
                                                    "DF000000010.2", "legacyname", "Legacy")]
            candidates, resolution, _ = audit.build_crosswalk(targets, records)
            relation = {row["identifier"]: row["relation_field"] for row in candidates}
            self.assertEqual(relation, {"Canonical": "NM", "LegacyName": "DR",
                                        "DF000000010": "AC", "DF000000010.2": "ID"})
            statuses = {row["identifier"]: row["resolution_status"] for row in resolution}
            self.assertEqual(statuses["legacyname"], "missing")
            self.assertEqual(statuses["Legacy"], "missing")

    def test_ambiguity_same_identity_duplicate_and_label_conflict_postjoin(self):
        records = [
            {"accession": "DF1", "version": 1, "versioned_accession": "DF1.1", "canonical_name": "A",
             "consensus_sha256": "x", "consensus_length": 4,
             "aliases": [{"relation_field": "NM", "relation_database": "Dfam", "alias": "A"},
                         {"relation_field": "DR", "relation_database": "Repbase", "alias": "SHARED"},
                         {"relation_field": "DR", "relation_database": "Repbase", "alias": "SAME"}]},
            {"accession": "DF2", "version": 1, "versioned_accession": "DF2.1", "canonical_name": "B",
             "consensus_sha256": "y", "consensus_length": 4,
             "aliases": [{"relation_field": "DR", "relation_database": "Repbase", "alias": "SHARED"}]},
            {"accession": "DF1", "version": 1, "versioned_accession": "DF1.1", "canonical_name": "A",
             "consensus_sha256": "x", "consensus_length": 4,
             "aliases": [{"relation_field": "SN", "relation_database": "Dfam", "alias": "SAME"}]},
        ]
        targets = [target("SHARED"), target("SAME", label="DNA"), target("A", label="LINE")]
        _candidates, resolution, metrics = audit.build_crosswalk(targets, records)
        self.assertEqual({row["identifier"]: row["resolution_status"] for row in resolution},
                         {"A": "resolved_unique", "SAME": "resolved_unique", "SHARED": "ambiguous"})
        self.assertEqual(metrics["ambiguous_identifier_count"], 1)
        _species, conflicts, count = audit.build_postjoin_audits(targets, resolution)
        self.assertEqual(count, 1)
        self.assertTrue(any(row["label_conflict"] for row in conflicts))

    def test_label_species_split_permutation_cannot_change_identity_payload(self):
        records = [{"accession": "DF1", "version": 1, "versioned_accession": "DF1.1",
                    "canonical_name": "A", "consensus_sha256": "x", "consensus_length": 4,
                    "aliases": [{"relation_field": "NM", "relation_database": "Dfam", "alias": "A"}]}]
        first = [target("A", 7, "LINE", "human")]
        permuted = [target("A", 7, "DNA", "mouse")]
        c1, r1, _ = audit.build_crosswalk(first, records)
        c2, r2, _ = audit.build_crosswalk(permuted, records)
        self.assertEqual(audit.sha256_text(audit.stable_json(c1)), audit.sha256_text(audit.stable_json(c2)))
        self.assertEqual(audit.sha256_text(audit.stable_json(r1)), audit.sha256_text(audit.stable_json(r2)))
        with tempfile.TemporaryDirectory() as name:
            first_path, second_path = Path(name) / "first.tsv", Path(name) / "second.tsv"
            fields = ["identifier", "occurrences", "candidate_row_count", "distinct_identity_count",
                      "resolution_status", "versioned_accession", "canonical_name", "consensus_sha256", "detail"]
            audit.write_tsv(first_path, r1, fields)
            audit.write_tsv(second_path, r2, fields)
            self.assertEqual(audit.sha256_file(first_path), audit.sha256_file(second_path))
        self.assertNotEqual(audit.build_postjoin_audits(first, r1)[0],
                            audit.build_postjoin_audits(permuted, r2)[0])

    def test_parser_shape_and_sequence_length_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"
            config = write_fixture(path, [embl_record("DF000000001", 1, "ACGT", "A")])
            config["curated_embl"]["expected_sequence_record_count"] = 2
            with self.assertRaisesRegex(audit.IntegrityFailure, "FIELD_OR_RECORD_COUNT_DRIFT"):
                audit.parse_curated_embl(path, config)
            bad = embl_record("DF000000001", 1, "ACGT", "A").replace("4 BP.", "5 BP.", 1)
            config = write_fixture(path, [bad])
            with self.assertRaisesRegex(audit.IntegrityFailure, "EMBL_SEQUENCE_LENGTH"):
                audit.parse_curated_embl(path, config)

    def test_exact_relation_contract_drift_is_rejected(self):
        config = cfg()
        config["source_contract"] = dict(config["source_contract"])
        config["source_contract"]["exact_relation_fields"] = ["NM", "PI", "SN", "DR"]
        with self.assertRaisesRegex(audit.IntegrityFailure, "EXACT_RELATION_FIELD_CONTRACT_DRIFT"):
            audit.validate_pinned_inputs(ROOT, config)

    def test_real_export_shape_and_preliminary_probe_regression(self):
        config = cfg()
        source = ROOT / config["curated_embl"]["path"]
        records, shape = audit.parse_curated_embl(source, config)
        targets = audit.read_tsv(ROOT / config["frozen_inputs"]["targets_path"])
        candidates, resolution, metrics = audit.build_crosswalk(targets, records)
        self.assertEqual(shape["field_counts"], {"ID": 26279, "NM": 22937, "AC": 26279,
                                                  "PI": 0, "SN": 0, "DR": 3570, "SQ": 26279})
        self.assertEqual((shape["record_count"], shape["sequence_record_count"]), (26279, 26279))
        self.assertEqual((metrics["authoritative_hit_identifier_count"],
                          metrics["resolved_unique_identifier_count"], metrics["ambiguous_identifier_count"]),
                         (52, 50, 2))
        self.assertEqual(sorted(row["identifier"] for row in resolution
                                if row["resolution_status"] == "ambiguous"), ["L1HS", "L1PREC2"])
        self.assertEqual(metrics["candidate_row_count"], len(candidates))
        self.assertEqual(metrics["occurrence_conservation_delta"], 0)

    def test_semantic_terminal_is_typed_block_not_complete(self):
        config = cfg()
        input_audit = {"target_identifier_count": 279, "target_occurrence_mass": 6432583,
                       "excluded_identifier_count": 10, "excluded_occurrence_mass": 43728,
                       "x13_identifier_count": 1, "x13_occurrence_mass": 686}
        crosswalk = {"authoritative_hit_identifier_count": 52, "resolved_unique_identifier_count": 50,
                     "ambiguous_identifier_count": 2, "invalid_metadata_identifier_count": 0,
                     "missing_identifier_count": 227, "resolved_unique_occurrence_mass": 1710715,
                     "ambiguous_occurrence_mass": 11352, "invalid_metadata_occurrence_mass": 0,
                     "missing_occurrence_mass": 4710516, "candidate_row_count": 57,
                     "identifier_conservation_delta": 0, "occurrence_conservation_delta": 0}
        resolution = [{"identifier": value, "resolution_status": "ambiguous"}
                      for value in ("L1HS", "L1PREC2")]
        status, metrics, report = audit.semantic_result(config, input_audit, {"record_count": 26279},
                                                        [], resolution, crosswalk)
        self.assertEqual(status, "IDENTITY_SOURCE_TYPED_BLOCK")
        self.assertTrue(metrics["semantic_success"])
        self.assertFalse(metrics["full_catalog_human_gate_eligible"])
        self.assertEqual(report["answer"], "NO_TYPED_BLOCK")

    def test_state_exact_closure_and_extra_file_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); config = {"preview_root": "preview", "exp_id": "X"}
            audit.publish_state(root, config, "IMPLEMENTED_NOT_RUN", "static", {"semantic_success": False},
                                {}, {}, {})
            closed = audit.verify_state(root, config)
            (closed["state"] / "extra").write_text("tamper")
            with self.assertRaisesRegex(audit.IntegrityFailure, "STATE_EXACT_FILE_SET"):
                audit.verify_state(root, config)

    def test_payload_tamper_and_exact_file_set_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            stage = Path(name)
            required = ["SOURCE_MANIFEST.json", "RUN_MANIFEST.json", "env.json", "OUTPUT_INDEX.json",
                        "authoritative_candidates.tsv", "identity_resolution.tsv", "species_audit.tsv",
                        "label_conflict_audit.tsv", "frozen_targets.tsv", "label_contract_excluded.tsv",
                        "x13_audit_only.tsv", "metrics.json", "report.json"]
            for filename in required:
                (stage / filename).write_text("{}\n")
            audit.create_payload_manifest(stage)
            audit.verify_payload(stage)
            (stage / "metrics.json").write_text("tamper\n")
            with self.assertRaisesRegex(audit.IntegrityFailure, "PAYLOAD_HASH_DRIFT"):
                audit.verify_payload(stage)

    def test_formal_guards_and_mock_gate_precede_source_audit_without_live_writes(self):
        class SourceAuditReached(RuntimeError):
            pass

        live_pointer = ROOT / cfg()["preview_root"] / "CURRENT_STATE.json"
        live_hash_before = audit.sha256_file(live_pointer)
        with tempfile.TemporaryDirectory() as name:
            temp_root = Path(name)
            config = cfg()
            config["project_root"] = str(temp_root)
            config["preview_root"] = "preview"
            config["code_review_gate_path"] = "code_review_gate.json"
            formal_env = {"SLURM_JOB_ID": "123", "SLURM_CPUS_PER_TASK": "1",
                          "SLURM_MEM_PER_NODE": "2G", "SLURM_JOB_GPUS": "",
                          "SLURM_GPUS_ON_NODE": ""}
            with mock.patch.dict(os.environ, {}, clear=True), \
                    mock.patch.object(audit, "validate_pinned_inputs",
                                      side_effect=SourceAuditReached) as source_audit:
                with self.assertRaisesRegex(audit.IntegrityFailure, "FORMAL_SLURM_GUARD"):
                    audit.formal_run(temp_root, config, "x")
                source_audit.assert_not_called()
            with mock.patch.dict(os.environ, formal_env, clear=True), \
                    mock.patch.object(audit, "validate_pinned_inputs",
                                      side_effect=SourceAuditReached) as source_audit:
                with self.assertRaisesRegex(audit.IntegrityFailure, "CODE_REVIEW_GATE_MISSING"):
                    audit.formal_run(temp_root, config, "x")
                source_audit.assert_not_called()
            sbatch_relative = f"sbatch/{EXP}.sbatch"
            sbatch_path = temp_root / sbatch_relative
            sbatch_path.parent.mkdir()
            sbatch_path.write_text("#SBATCH --time=00:20:00\n")
            (temp_root / "code_review_gate.json").write_text(json.dumps({"verdict": "PASS",
                "reviewed_files": {sbatch_relative: audit.sha256_file(sbatch_path)}}) + "\n")
            with mock.patch.dict(os.environ, formal_env, clear=True), \
                    mock.patch.object(audit, "validate_pinned_inputs",
                                      side_effect=SourceAuditReached) as source_audit:
                with self.assertRaises(SourceAuditReached):
                    audit.formal_run(temp_root, config, "x")
                source_audit.assert_called_once()
            self.assertFalse((temp_root / "preview/CURRENT_STATE.json").exists())
        self.assertEqual(audit.sha256_file(live_pointer), live_hash_before)

    def test_resource_guard_rejects_gpu_cpu_and_memory_drift(self):
        config = cfg()
        valid = {"SLURM_CPUS_PER_TASK": "1", "SLURM_MEM_PER_NODE": "2048",
                 "SLURM_JOB_GPUS": "", "SLURM_GPUS_ON_NODE": ""}
        with mock.patch.dict(os.environ, valid, clear=True):
            observed = audit.validate_formal_resources(config)
            self.assertEqual(observed["slurm_mem_per_node_mb"], 2048)
        for changed, message in [({"SLURM_JOB_GPUS": "0"}, "GPU_RESOURCE_CONTRACT"),
                                 ({"SLURM_CPUS_PER_TASK": "2"}, "CPU_RESOURCE_CONTRACT"),
                                 ({"SLURM_MEM_PER_NODE": "2047"}, "MEMORY_RESOURCE_CONTRACT"),
                                 ({"SLURM_MEM_PER_NODE": "4096"}, "MEMORY_RESOURCE_CONTRACT"),
                                 ({"SLURM_MEM_PER_NODE": "4G"}, "MEMORY_RESOURCE_CONTRACT"),
                                 ({"SLURM_MEM_PER_NODE": "2GB"}, "MEM_PER_NODE_FORMAT")]:
            env = {**valid, **changed}
            with mock.patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(
                    audit.ResourceFailure, message):
                audit.validate_formal_resources(config)

    def test_exact_memory_equivalent_formats_and_reviewed_sbatch_binding(self):
        config = cfg()
        for memory in ("2048", "2048M", "2G"):
            env = {"SLURM_CPUS_PER_TASK": "1", "SLURM_MEM_PER_NODE": memory,
                   "SLURM_JOB_GPUS": "", "SLURM_GPUS_ON_NODE": ""}
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(audit.validate_formal_resources(config)["slurm_mem_per_node_mb"], 2048)
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            relative = f"sbatch/{EXP}.sbatch"
            path = root / relative
            path.parent.mkdir()
            path.write_text("#SBATCH --time=00:20:00\n")
            valid = {"reviewed_files": {relative: audit.sha256_file(path)}}
            self.assertEqual(audit.validate_reviewed_submission(root, config, valid)
                             ["authorized_submission_command"], f"sbatch {relative}")
            with self.assertRaisesRegex(audit.IntegrityFailure, "REVIEWED_SBATCH_BINDING"):
                audit.validate_reviewed_submission(root, config, {"reviewed_files": {}})


if __name__ == "__main__":
    unittest.main()
