#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
import os
import tempfile
import tracemalloc
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXP = "SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-AUDIT-20260812-R1"
CONFIG = ROOT / f"configs/{EXP}.yaml"
SPEC = importlib.util.spec_from_file_location("allfamily", HERE / "audit_allfamily.py")
audit = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(audit)


def cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def target(identifier: str, occurrences: int = 1, label: str = "LINE", species: str = "human") -> dict:
    return {"identifier": identifier, "occurrences": str(occurrences), "labels": label, "species": species,
            "status": "missing", "resolution_status": "missing", "resolution_method": "none"}


def record(accession: str, nm: str, sequence: str = "ACGT", aliases: list[tuple[str, str]] | None = None,
           version: int = 1) -> str:
    lines = [f"ID   {accession}; SV {version}; linear; DNA; STD; UNC; {len(sequence)} BP."]
    if nm:
        lines.append(f"NM   {nm}")
    lines.extend([f"AC   {accession};"])
    for field, value in aliases or []:
        lines.append(f"{field}   {value}")
    lines.extend([f"SQ   Sequence {len(sequence)} BP;", f"     {sequence.lower()}  {len(sequence)}", "//"])
    return "\n".join(lines) + "\n"


def write_gzip(path: Path, text: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)


def curated_candidate(identifier: str = "A") -> dict:
    sequence_sha = audit.hashlib.sha256(b"ACGT").hexdigest()
    return {"identifier": identifier, "relation_field": "NM", "relation_database": "Dfam",
            "official_alias_exact": identifier, "accession": "DF000000001", "version": "1",
            "versioned_accession": "DF000000001.1", "canonical_name": "A",
            "consensus_sha256": sequence_sha, "consensus_length": "4"}


def frozen_resolution(rows: list[tuple[str, str, int]]) -> dict:
    targets, resolution = [], []
    for identifier, status, occurrences in rows:
        targets.append(target(identifier, occurrences))
        resolution.append({"identifier": identifier, "occurrences": str(occurrences),
                           "resolution_status": status,
                           "versioned_accession": "DF1.1" if status == "resolved_unique" else "",
                           "consensus_sha256": "x" if status == "resolved_unique" else ""})
    return {"targets": targets, "resolution": resolution, "target_identifier_count": len(targets),
            "target_occurrence_mass": sum(value for _, _, value in rows)}


class AllFamilyTests(unittest.TestCase):
    def test_real_topology_and_small_pins_without_reading_full_source(self):
        config = cfg(); source = ROOT / config["full_embl"]["path"]
        original = audit.hash_file
        def guarded(path, algorithm="sha256"):
            if Path(path) == source:
                raise AssertionError("static validation must not read 2.68GB source")
            return original(Path(path), algorithm)
        with mock.patch.object(audit, "hash_file", side_effect=guarded):
            observed, topology = audit.verify_source_topology(ROOT, config)
            frozen = audit.load_frozen_inputs(ROOT, config)
        self.assertEqual(observed, source)
        self.assertEqual(topology["source_stat"]["st_size"], 2677249806)
        self.assertEqual((frozen["target_identifier_count"], frozen["target_occurrence_mass"]), (279, 6432583))

    def test_target_only_parser_stratifies_df_and_raw_dr(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"
            write_gzip(path, record("DF000000001", "A") +
                       record("DR000000002", "RAW", aliases=[("DR", "Repbase; B.")]))
            rows, telemetry = audit.stream_target_candidates(path, [target("A"), target("B")], 20)
        self.assertEqual([(row["identifier"], row["source_tier"], row["evidence_status"]) for row in rows],
                         [("A", "DF_CURATED", "CURATED_RECONCILE"),
                          ("B", "RAW_DR", "RAW_ONLY_SUPPORT")])
        self.assertEqual(telemetry["scanned_record_count"], 2)
        self.assertFalse(telemetry["full_catalog_materialized"])

    def test_pi_semicolon_token_list_exact_hits_and_counts(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"
            write_gzip(path, record("DF000000001", "CANON", aliases=[("PI", "OLD1; TARGET;")]))
            rows, telemetry = audit.stream_target_candidates(
                path, [target("TARGET"), target("target"), target("TARG")], 20)
        self.assertEqual([(row["identifier"], row["relation_field"]) for row in rows], [("TARGET", "PI")])
        counts = telemetry["relation_grammar_counts"]["DF"]["PI"]
        self.assertEqual(counts, {"line_count": 1, "token_count": 2, "terminator_count": 1,
            "terminator_counts_by_symbol": {"semicolon": 1, "period": 0, "none": 0},
            "target_hit_count": 1})

    def test_dr_semicolon_and_period_terminators_are_distinct_and_exact(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"
            write_gzip(path, record("DF000000001", "A", aliases=[("DR", "Repbase; TARGET;")])
                       + record("DR000000002", "B", aliases=[("DR", "Repbase; TARGET.")]))
            rows, telemetry = audit.stream_target_candidates(
                path, [target("TARGET"), target("target"), target("TARG")], 20)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["identifier"] == "TARGET" and row["relation_field"] == "DR" for row in rows))
        df = telemetry["relation_grammar_counts"]["DF"]["DR"]
        raw = telemetry["relation_grammar_counts"]["DR"]["DR"]
        self.assertEqual(df["terminator_counts_by_symbol"]["semicolon"], 1)
        self.assertEqual(raw["terminator_counts_by_symbol"]["period"], 1)
        self.assertEqual((df["target_hit_count"], raw["target_hit_count"]), (1, 1))
        frozen = {"target_identifier_count": 1, "target_occurrence_mass": 1,
                  "curated_metrics": {"resolved_unique_identifier_count": 0,
                                      "ambiguous_identifier_count": 0, "missing_identifier_count": 1}}
        _status, metrics, report = audit.semantic_result(cfg(), frozen, {}, telemetry, {}, {})
        self.assertEqual(metrics["relation_grammar_counts"], telemetry["relation_grammar_counts"])
        self.assertEqual(report["metrics"]["relation_grammar_counts"], telemetry["relation_grammar_counts"])
        manifest = audit.source_manifest_payload(cfg(), {}, telemetry)
        self.assertEqual(manifest["relation_grammar_counts"], telemetry["relation_grammar_counts"])

    def test_empty_and_malformed_pi_dr_are_rejected(self):
        malformed = [("PI", ";", "PI_EMPTY_OR_MALFORMED"),
                     ("PI", "OLD1;; TARGET;", "PI_EMPTY_OR_MALFORMED"),
                     ("PI", "OLD1; TARGET", "PI_FIELD_SCHEMA"),
                     ("DR", "; TARGET.", "DR_EMPTY_DATABASE_OR_PRIMARY"),
                     ("DR", "Repbase; .", "DR_EMPTY_DATABASE_OR_PRIMARY"),
                     ("DR", "Repbase; TARGET", "DR_TERMINATOR_SCHEMA"),
                     ("DR", "Repbase; TARGET; EXTRA.", "DR_FIELD_SCHEMA")]
        for index, (field, value, error) in enumerate(malformed):
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as name:
                path = Path(name) / f"x{index}.gz"
                write_gzip(path, record("DF000000001", "A", aliases=[(field, value)]))
                with self.assertRaisesRegex(audit.IntegrityFailure, error):
                    audit.stream_target_candidates(path, [target("TARGET")], 20)

    def test_exact_case_sensitive_no_prefix_or_substring(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"; write_gzip(path, record("DF000000001", "ExactName"))
            rows, _ = audit.stream_target_candidates(path,
                [target("exactname"), target("Exact"), target("ExactName_extra")], 20)
        self.assertEqual(rows, [])

    def test_ac_id_only_accession_shaped_targets(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"; write_gzip(path, record("DF000000001", "NAME", version=3))
            rows, _ = audit.stream_target_candidates(path,
                [target("DF000000001"), target("DF000000001.3"), target("NAME")], 20)
        fields = {(row["identifier"], row["relation_field"]) for row in rows}
        self.assertEqual(fields, {("DF000000001", "AC"), ("DF000000001.3", "ID"), ("NAME", "NM")})

    def test_truncated_gzip_crc_eof_fails_closed(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"; write_gzip(path, record("DF000000001", "A"))
            path.write_bytes(path.read_bytes()[:-6])
            with self.assertRaisesRegex(audit.IntegrityFailure, "GZIP_EOF_CRC_OR_STREAM_FAILURE"):
                audit.stream_target_candidates(path, [target("A")], 20)

    def test_missing_terminator_and_bad_target_sequence_fail(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"; write_gzip(path, record("DF000000001", "A").replace("//\n", ""))
            with self.assertRaisesRegex(audit.IntegrityFailure, "FINAL_RECORD_UNTERMINATED"):
                audit.stream_target_candidates(path, [target("A")], 20)
            write_gzip(path, record("DF000000001", "A", "ACGX"))
            with self.assertRaisesRegex(audit.IntegrityFailure, "TARGET_RECORD_SEQUENCE_INVALID"):
                audit.stream_target_candidates(path, [target("A")], 20)

    def test_bounded_memory_proxy_retains_no_nontarget_catalog(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "many.gz"
            write_gzip(path, "".join(record(f"DR{index:09d}", f"NON{index}") for index in range(6000))
                       + record("DF999999999", "TARGET"))
            tracemalloc.start()
            rows, telemetry = audit.stream_target_candidates(path, [target("TARGET")], 10)
            _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        self.assertEqual(len(rows), 1)
        self.assertEqual(telemetry["scanned_record_count"], 6001)
        self.assertLess(peak, 8 * 1024 * 1024)

    def test_candidate_bound_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"
            write_gzip(path, record("DF000000001", "A", aliases=[("SN", "A"), ("PI", "A;")]))
            with self.assertRaisesRegex(audit.ResourceFailure, "CANDIDATE_ROW_BOUND"):
                audit.stream_target_candidates(path, [target("A")], 1)

    def test_df_subset_exactly_reconciles_curated_payload(self):
        expected = curated_candidate()
        observed = {**expected, "version": 1, "consensus_length": 4,
                    "source_tier": "DF_CURATED", "evidence_status": "CURATED_RECONCILE"}
        result = audit.reconcile_curated_df([observed], [expected])
        self.assertTrue(result["curated_reconciliation_exact"])
        with self.assertRaisesRegex(audit.IntegrityFailure, "DF_CURATED_RECONCILIATION_MISMATCH"):
            audit.reconcile_curated_df([{**observed, "consensus_sha256": "tamper"}], [expected])

    def test_raw_cannot_override_curated_resolved_or_ambiguity(self):
        frozen = frozen_resolution([("RES", "resolved_unique", 3), ("AMB", "ambiguous", 5),
                                    ("MISS", "missing", 7)])
        raw = [{"identifier": value, "source_tier": "RAW_DR", "versioned_accession": f"DR{index}.1",
                "consensus_sha256": str(index)} for index, value in enumerate(("RES", "AMB", "MISS"), 1)]
        rows, metrics = audit.layered_resolution(frozen, raw)
        statuses = {row["identifier"]: row["layered_status"] for row in rows}
        self.assertEqual(statuses, {"RES": "CURATED_RESOLVED_UNCHANGED",
                                    "AMB": "CURATED_AMBIGUOUS_UNCHANGED", "MISS": "RAW_ONLY_SUPPORT"})
        self.assertEqual(metrics["curated_resolved_overridden_count"], 0)
        self.assertEqual(metrics["curated_ambiguity_resolved_by_raw_count"], 0)

    def test_resolution_identifier_and_occurrence_conservation(self):
        frozen = frozen_resolution([("A", "missing", 3), ("B", "missing", 7)])
        rows, metrics = audit.layered_resolution(frozen, [])
        self.assertEqual((len(rows), sum(row["occurrences"] for row in rows)), (2, 10))
        self.assertEqual((metrics["identifier_conservation_delta"], metrics["occurrence_conservation_delta"]), (0, 0))

    def test_label_species_permutation_is_postjoin_only(self):
        frozen = frozen_resolution([("A", "missing", 2)])
        rows1, _ = audit.layered_resolution(frozen, [])
        permuted = {**frozen, "targets": [target("A", 2, "DNA", "mouse")]}
        rows2, _ = audit.layered_resolution(permuted, [])
        self.assertEqual(audit.stable_json(rows1), audit.stable_json(rows2))
        self.assertNotEqual(audit.postjoin_audits(frozen["targets"], rows1),
                            audit.postjoin_audits(permuted["targets"], rows2))

    def test_compressed_sha_md5_and_same_size_stat_drift(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "x.gz"; write_gzip(path, record("DF000000001", "A"))
            config = cfg(); config["full_embl"] = dict(config["full_embl"])
            config["full_embl"].update({"sha256": audit.hash_file(path), "md5": audit.hash_file(path, "md5"),
                                        "size_bytes": path.stat().st_size})
            before = audit.exact_stat(path)
            observed = audit.hash_compressed_source(path, config, before)
            self.assertEqual(observed["size_bytes"], path.stat().st_size)
            drift = dict(before); drift["st_mtime_ns"] -= 1
            with self.assertRaisesRegex(audit.IntegrityFailure, "STAT_DRIFT_DURING_HASH"):
                audit.hash_compressed_source(path, config, drift)

    def test_source_manifest_identity_drift_fails_without_full_read(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = root / "full.gz"; source.write_bytes(b"x")
            sidecar = root / "full.md5"; sidecar.write_text("a  Dfam-1.embl.gz\n")
            manifest = root / "source.json"; manifest.write_text(json.dumps({"schema_version": "X"}))
            config = cfg(); config["full_embl"] = {**config["full_embl"], "path": "full.gz",
                "size_bytes": 1, "md5": "a", "md5_sidecar_path": "full.md5",
                "md5_sidecar_sha256": audit.hash_file(sidecar), "source_manifest_path": "source.json",
                "source_manifest_sha256": audit.hash_file(manifest)}
            with self.assertRaisesRegex(audit.IntegrityFailure, "SOURCE_MANIFEST_SCHEMA"):
                audit.verify_source_topology(root, config)

    def test_valid_negative_semantics_and_exit_codes(self):
        config = cfg(); frozen = {"target_identifier_count": 279, "target_occurrence_mass": 6432583,
            "curated_metrics": {"resolved_unique_identifier_count": 50, "ambiguous_identifier_count": 2,
                                "missing_identifier_count": 227}}
        status, metrics, report = audit.semantic_result(config, frozen, {}, {}, {}, {})
        self.assertEqual(status, "ALLFAMILY_TARGET_CROSSWALK_TYPED_BLOCK")
        self.assertTrue(metrics["semantic_success"]); self.assertTrue(metrics["valid_negative"])
        self.assertEqual(report["answer"], "COMPLETE_SCAN_BUT_INSUFFICIENT_AUTHORITATIVE_CROSSWALK")
        self.assertEqual(audit.exit_code(status), 0); self.assertEqual(audit.exit_code("AUDIT_FAILED_INTEGRITY"), 2)

    def test_exact_resource_guard_1cpu_4g_0gpu(self):
        config = cfg(); valid = {"SLURM_CPUS_PER_TASK": "1", "SLURM_MEM_PER_NODE": "4096",
            "SLURM_JOB_GPUS": "", "SLURM_GPUS_ON_NODE": ""}
        for memory in ("4096", "4096M", "4G"):
            with mock.patch.dict(os.environ, {**valid, "SLURM_MEM_PER_NODE": memory}, clear=True):
                self.assertEqual(audit.validate_resources(config)["memory_mib"], 4096)
        for changed, message in [({"SLURM_CPUS_PER_TASK": "2"}, "CPU_RESOURCE"),
                                 ({"SLURM_MEM_PER_NODE": "8192"}, "MEMORY_RESOURCE"),
                                 ({"SLURM_JOB_GPUS": "0"}, "GPU_RESOURCE")]:
            with mock.patch.dict(os.environ, {**valid, **changed}, clear=True), \
                    self.assertRaisesRegex(audit.ResourceFailure, message):
                audit.validate_resources(config)

    def test_payload_has_14_files_and_rejects_tamper_extra(self):
        with tempfile.TemporaryDirectory() as name:
            stage = Path(name)
            for filename in audit.PAYLOAD_REQUIRED:
                (stage / filename).write_text("{}\n")
            audit.create_payload_manifest(stage); audit.verify_payload(stage)
            self.assertEqual(len(list(stage.iterdir())), 14)
            self.assertEqual(len(json.loads((stage / "PAYLOAD_MANIFEST.json").read_text())["files"]), 13)
            (stage / "extra").write_text("x")
            with self.assertRaisesRegex(audit.IntegrityFailure, "PAYLOAD_EXACT_FILE_SET"):
                audit.verify_payload(stage)

    def test_immutable_state_exact_set_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); config = {"preview_root": "preview", "exp_id": "X"}
            audit.publish_state(root, config, "IMPLEMENTED_NOT_RUN", "static", {"semantic_success": False}, {}, {}, {})
            closed = audit.verify_state(root, config); (closed["state"] / "extra").write_text("x")
            with self.assertRaisesRegex(audit.IntegrityFailure, "STATE_EXACT_FILE_SET"):
                audit.verify_state(root, config)

    def test_formal_order_stops_before_source_without_live_writes(self):
        live = ROOT / cfg()["preview_root"] / "CURRENT_STATE.json"
        live_before = audit.hash_file(live) if live.exists() else None
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); config = cfg(); config["project_root"] = str(root)
            config["preview_root"] = "preview"; config["code_review_gate_path"] = "gate.json"
            env = {"SLURM_JOB_ID": "123", "SLURM_CPUS_PER_TASK": "1", "SLURM_MEM_PER_NODE": "4G",
                   "SLURM_JOB_GPUS": "", "SLURM_GPUS_ON_NODE": ""}
            relative = f"sbatch/{EXP}.sbatch"; sbatch = root / relative; sbatch.parent.mkdir(); sbatch.write_text("x")
            reviewed = {relative: audit.hash_file(sbatch)}
            (root / "gate.json").write_text(json.dumps({"verdict": "PASS", "reviewed_files": reviewed}))
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
                    audit, "package_hashes", return_value=reviewed), \
                    mock.patch.object(audit, "verify_source_topology", side_effect=RuntimeError("SOURCE_REACHED")):
                with self.assertRaisesRegex(RuntimeError, "SOURCE_REACHED"):
                    audit.formal_run(root, config, "x")
            self.assertFalse((root / "preview/CURRENT_STATE.json").exists())
        if live_before is not None:
            self.assertEqual(audit.hash_file(live), live_before)


if __name__ == "__main__":
    unittest.main()
