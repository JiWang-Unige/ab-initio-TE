#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
import re
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("recover_sharded", HERE / "recover_sharded.py")
recovery = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = recovery
SPEC.loader.exec_module(recovery)
EXP = "SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2"
CONFIG = PROJECT / f"configs/{EXP}.yaml"


def cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def target(identifier: str, occurrences: int = 1) -> dict:
    return {"identifier": identifier, "occurrences": str(occurrences), "labels": "LINE", "species": "human",
            "status": "missing", "resolution_status": "missing", "resolution_method": "none"}


def make_h5(path: Path, units: dict[str, list[dict]], hardlink: bool = False) -> None:
    import h5py
    with h5py.File(path, "w") as handle:
        handle.attrs.update({"db_version": "3.9", "famdb_version": "2.0.0", "partition_num": 3})
        handle.require_group("Families/Aux")
        handle.require_group("Families/DR")
        for unit, rows in units.items():
            group = handle.create_group(unit)
            first = None
            for index, row in enumerate(rows):
                item = group.create_dataset(f"D{index}", data=[1])
                item.attrs.update(row)
                if first is None:
                    first = item
            if hardlink and first is not None:
                group["D_alias"] = first


def synthetic_cfg(source: Path, checkpoint_root: Path) -> dict:
    config = cfg()
    config["famdb_partition_path"] = source.name
    config["famdb_partition_normalized_realpath"] = str(source.resolve())
    config["famdb_source_identity"] = {**recovery.source_identity(source),
                                       "full_64gb_content_sha256_available": False, "limitation": "synthetic"}
    config["checkpoint_root"] = str(checkpoint_root)
    return config


def minimal_preview(root: Path) -> dict:
    preview = root / "preview"
    preview.mkdir()
    config = {"exp_id": "X", "profile": "test", "preview_root": "preview",
              "slurm_log_dir": "preview/logs"}
    return config


def mock_pin(config: dict, unit: str, **extra) -> dict:
    device = config["famdb_source_identity"]["resolved_device"]
    return {"unit": unit,
            "source_device_audit": {"binding": "audit_only", "expected_resolved_device": device,
                                    "observed_resolved_device": device, "device_match": True},
            **extra}


class ShardedRecoveryTests(unittest.TestCase):
    def test_closed_project_root_aliases_and_root_relative_asset_realpath(self):
        config = cfg()
        for alias in config["project_root_alias_contract"]["allowed_aliases"]:
            candidate = dict(config); candidate["project_root"] = alias
            self.assertEqual(recovery.resolve_project_root(candidate), PROJECT)
        unknown = dict(config); unknown["project_root"] = "/tmp/ab-initio-TE"
        with self.assertRaisesRegex(recovery.IntegrityFailure, "PROJECT_ROOT_ALIAS_NOT_ALLOWED"):
            recovery.resolve_project_root(unknown)
        absolute = dict(config); absolute["famdb_partition_path"] = str(PROJECT / config["famdb_partition_path"])
        with self.assertRaisesRegex(recovery.IntegrityFailure, "NOT_ROOT_RELATIVE"):
            recovery.validate_asset_logical_path(PROJECT, absolute)
        wrong_realpath = dict(config); wrong_realpath["famdb_partition_normalized_realpath"] = "/tmp/unknown-alias"
        with self.assertRaisesRegex(recovery.GlobalPinDrift, "SOURCE_ASSET_REALPATH_DRIFT"):
            recovery.validate_asset_logical_path(PROJECT, wrong_realpath)

    def test_device_is_audit_only_but_all_stable_source_fields_bind(self):
        expected = dict(cfg()["famdb_source_identity"])
        observed = {key: expected[key] for key in recovery.SOURCE_STABLE_IDENTITY_FIELDS}
        observed["resolved_device"] = 65
        with mock.patch.object(recovery, "source_identity", return_value=observed):
            self.assertEqual(recovery.validate_source_identity(Path("unused"), expected)["resolved_device"], 65)
        for field in recovery.SOURCE_STABLE_IDENTITY_FIELDS:
            drifted = dict(observed)
            drifted[field] = ("drift" if isinstance(drifted[field], str) else int(drifted[field]) + 1)
            with self.subTest(field=field), mock.patch.object(recovery, "source_identity", return_value=drifted):
                with self.assertRaisesRegex(recovery.GlobalPinDrift, "SOURCE_IDENTITY_DRIFT"):
                    recovery.validate_source_identity(Path("unused"), expected)

    def test_compute_observed_traceback_fixture_device_65_replays_as_valid(self):
        traceback_path = PROJECT / f"outputs/{EXP}/preview/logs/slurm_11526687.err"
        traceback_text = traceback_path.read_text(encoding="utf-8")
        match = re.search(r"SOURCE_IDENTITY_DRIFT:(\{'symlink_target_sha256'[^\n]+\})", traceback_text)
        self.assertIsNotNone(match)
        observed = ast.literal_eval(match.group(1))
        self.assertEqual(observed["resolved_device"], 65)
        self.assertEqual(cfg()["famdb_source_identity"]["resolved_device"], 42)
        with mock.patch.object(recovery, "source_identity", return_value=observed):
            replay = recovery.validate_source_identity(Path("compute-observed-fixture"),
                                                       cfg()["famdb_source_identity"])
        self.assertEqual(replay["resolved_device"], 65)

    def test_hdf5_metadata_and_layout_pins_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = root / "source.h5"
            import h5py
            with h5py.File(source, "w") as handle:
                handle.attrs.update({"db_version": "3.9", "famdb_version": "2.0.0", "partition_num": 3})
                handle.create_group("Families/Aux/ac")
                handle.create_group("Families/DR/00/06")
            config = cfg()
            config["topology"] = dict(config["topology"])
            config["topology"]["expected_families_root_keys"] = ["Aux", "DR"]
            self.assertEqual(recovery.validate_hdf5_source_contract(source, config),
                             ["Families/Aux/ac", "Families/DR/00/06"])
            with h5py.File(source, "r+") as handle:
                handle.attrs.modify("partition_num", 4)
            with self.assertRaisesRegex(recovery.GlobalPinDrift, "SOURCE_METADATA_OR_LAYOUT_DRIFT"):
                recovery.validate_hdf5_source_contract(source, config)
            with h5py.File(source, "r+") as handle:
                handle.attrs.modify("partition_num", 3)
                handle.create_group("Lookup/ByName")
            with self.assertRaisesRegex(recovery.GlobalPinDrift, "SOURCE_METADATA_OR_LAYOUT_DRIFT"):
                recovery.validate_hdf5_source_contract(source, config)

    def test_frozen_denominator_hashes_and_package_hashes_remain_exact(self):
        config = cfg()
        frozen = {
            "parent_r0_config_sha256": "db33924089882afc2f959f71d2326f8a3848eee58cbb08243e63a33e76e1ff84",
            "parent_r0_evaluator_sha256": "4ea7ae30be25930ce5554a2bd87fdcce03ddb6458962d40750269081c0d173e9",
            "identity_identifier_audit_sha256": "c32dd5d6236282c2851676995a5ae0dac4394ff253d9768d396a33731c9da67b",
            "evaluator_contract_sha256": "fe0d63e9b525a0bac5ee03b3b88b83385fc4582f8a1b3f9802d171c72594ade2",
            "famdb_rmlib_config_sha256": "9f789bae6b7d9199382510120305c2099e3928a686f9e06cef4dc85f8846c545",
        }
        self.assertEqual({key: config[key] for key in frozen}, frozen)
        packages = recovery.package_hashes(PROJECT, EXP)
        self.assertTrue(all(recovery.sha256_file(PROJECT / path) == digest
                            for path, digest in packages.items()))

    def test_real_frozen_semantics_source_and_topology_are_shallow_only(self):
        targets, x13, source, units, audit, _parent = recovery.validate_inputs(PROJECT, cfg())
        self.assertEqual(len(targets), 279)
        self.assertEqual(sum(int(row["occurrences"]) for row in targets), 6432583)
        self.assertEqual([(row["identifier"], int(row["occurrences"])) for row in x13], [("X13_LINE", 686)])
        self.assertEqual(len(units), 35)
        self.assertEqual(source.stat().st_size, 63939647016)
        self.assertFalse(audit["real_dataset_enumeration_executed"])
        self.assertFalse(audit["source_identity_full_content_sha256"])
        self.assertTrue(all(value is False for value in recovery.authorization_flags().values()))

    def test_topology_exact_union_duplicate_and_ancestor_overlap(self):
        units = ["A/x", "A/y", "B/z"]
        digest = recovery.sha256_text("".join(unit + "\n" for unit in units))
        recovery.validate_topology_units(units, 3, digest)
        with self.assertRaisesRegex(recovery.IntegrityFailure, "COUNT_OR_DUPLICATE"):
            recovery.validate_topology_units(["A", "A"], 2, recovery.sha256_text("A\nA\n"))
        with self.assertRaisesRegex(recovery.IntegrityFailure, "ANCESTOR_OVERLAP"):
            recovery.validate_topology_units(["A", "A/x"], 2, recovery.sha256_text("A\nA/x\n"))

    def test_source_same_size_attribute_mutation_is_rejected_by_mtime_identity(self):
        with tempfile.TemporaryDirectory() as name:
            source = Path(name) / "x.h5"
            make_h5(source, {"Families/Aux/a": [{"name": "A", "accession": "D", "version": 1,
                                                  "consensus": "AAAA", "model": "M"}]})
            frozen = recovery.source_identity(source)
            size = source.stat().st_size
            import h5py
            with h5py.File(source, "r+") as handle:
                handle["Families/Aux/a/D0"].attrs.modify("name", "B")
            self.assertEqual(source.stat().st_size, size)
            if source.stat().st_mtime_ns == frozen["resolved_mtime_ns"]:
                os.utime(source, ns=(source.stat().st_atime_ns, frozen["resolved_mtime_ns"] + 1))
            with self.assertRaisesRegex(recovery.IntegrityFailure, "SOURCE_IDENTITY_DRIFT"):
                recovery.validate_source_identity(source, frozen)

    def test_same_size_attr_and_inode_mutation_between_unit_read_and_complete_publish_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source, replacement = root / "x.h5", root / "replacement.h5"
            unit = "Families/Aux/a"
            rows = [{"name": "A", "accession": "D", "version": 1, "consensus": "AAAA", "model": "M"}]
            make_h5(source, {unit: rows})
            shutil.copy2(source, replacement)
            import h5py
            with h5py.File(replacement, "r+") as handle:
                handle[f"{unit}/D0"].attrs.modify("name", "B")
            self.assertEqual(source.stat().st_size, replacement.stat().st_size)
            config = synthetic_cfg(source, root / "checkpoints")

            def mutate_source():
                os.replace(replacement, source)

            with mock.patch.object(recovery, "unit_pin_contract", return_value={"unit": unit}):
                with h5py.File(source, "r") as handle:
                    with self.assertRaisesRegex(recovery.GlobalPinDrift, "SOURCE_IDENTITY_DRIFT"):
                        recovery.scan_and_publish_unit(root, config, handle, unit, {"A"}, "a", "0",
                                                       pre_publish_hook=mutate_source)
            complete = root / f"checkpoints/units/{recovery.unit_slug(unit)}.COMPLETE"
            self.assertFalse(complete.exists())

    def test_single_pass_unit_checkpoint_exact_case_and_resume(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "x.h5"
            unit = "Families/Aux/a"
            make_h5(source, {unit: [
                {"name": "L2a", "accession": "DF1", "version": 2, "consensus": "ACGU", "model": "M"},
                {"name": "l2a", "accession": "DF2", "version": 1, "consensus": "CCCC", "model": "M"},
                {"name": "L2a_extra", "accession": "DF3", "version": 1, "consensus": "GGGG", "model": "M"},
                {"name": "BAD", "accession": "DF4", "version": "not-an-integer",
                 "consensus": "TTTT", "model": "M"}]})
            config = synthetic_cfg(source, root / "checkpoints")
            import h5py
            with mock.patch.object(recovery, "unit_pin_contract", return_value=mock_pin(config, unit, pin="x")):
                with h5py.File(source, "r") as handle:
                    summary = recovery.scan_and_publish_unit(root, config, handle, unit, {"L2a", "BAD"}, "a", "0")
                checkpoint = recovery.verify_unit_checkpoint(root, config, unit)
                resumed = recovery.verify_unit_checkpoint(root, config, unit)
            self.assertEqual(summary["dataset_count"], 4)
            self.assertEqual(summary["consensus_attribute_count"], 4)
            self.assertEqual(len(checkpoint["candidates"]), 2)
            by_name = {row["identifier"]: row for row in checkpoint["candidates"]}
            self.assertEqual(by_name["L2a"]["consensus_sha256"], recovery.sha256_text("ACGT"))
            self.assertEqual(by_name["BAD"]["versioned_accession"], "")
            self.assertEqual(resumed["summary"], checkpoint["summary"])

    def test_hardlink_duplicate_rejected_inside_unit(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "x.h5"
            unit = "Families/Aux/a"
            make_h5(source, {unit: [{"name": "A", "accession": "D", "version": 1,
                                     "consensus": "A", "model": "M"}]}, hardlink=True)
            config = synthetic_cfg(source, root / "checkpoints")
            import h5py
            with mock.patch.object(recovery, "unit_pin_contract", return_value={"unit": unit}):
                with h5py.File(source, "r") as handle:
                    with self.assertRaisesRegex(recovery.IntegrityFailure, "HARDLINK_DUPLICATE"):
                        recovery.scan_and_publish_unit(root, config, handle, unit, {"A"}, "a", "0")

    def test_partial_quarantine_payload_tamper_recomputes_only_bad_unit_and_pin_drift_fails(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "x.h5"
            unit = "Families/Aux/a"
            make_h5(source, {unit: [{"name": "A", "accession": "D", "version": 1,
                                     "consensus": "A", "model": "M"}]})
            config = synthetic_cfg(source, root / "checkpoints")
            units_root = root / "checkpoints/units"
            units_root.mkdir(parents=True)
            partial = units_root / f"{recovery.unit_slug(unit)}.tmp.old"
            partial.mkdir()
            moved = recovery.quarantine_partial_units(PROJECT, config, unit, "new")
            self.assertEqual(len(moved), 1)
            import h5py
            pins = mock_pin(config, unit, pin="x")
            with mock.patch.object(recovery, "unit_pin_contract", return_value=pins):
                with h5py.File(source, "r") as handle:
                    recovery.scan_and_publish_unit(root, config, handle, unit, {"A"}, "a", "0")
                complete = units_root / f"{recovery.unit_slug(unit)}.COMPLETE"
                (complete / "exact_candidates.tsv").write_text("tampered\n")
                reused, quarantined = recovery.resume_or_quarantine_unit(root, config, unit, "b")
                self.assertFalse(reused)
                self.assertIn("quarantine", quarantined)
            # Pin/source drift is global and must never be silently recomputed.
            import h5py
            with mock.patch.object(recovery, "unit_pin_contract", return_value=pins):
                with h5py.File(source, "r") as handle:
                    recovery.scan_and_publish_unit(root, config, handle, unit, {"A"}, "c", "0")
            bad_config = dict(config)
            bad_config["famdb_source_identity"] = dict(config["famdb_source_identity"])
            bad_config["famdb_source_identity"]["resolved_mtime_ns"] += 1
            with self.assertRaisesRegex(recovery.GlobalPinDrift, "SOURCE_IDENTITY_DRIFT"):
                recovery.resume_or_quarantine_unit(root, bad_config, unit, "d")

    def test_checkpoint_reuse_ignores_device_audit_difference_only(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = root / "x.h5"; unit = "Families/Aux/a"
            make_h5(source, {unit: [{"name": "A", "accession": "D", "version": 1,
                                     "consensus": "A", "model": "M"}]})
            config = synthetic_cfg(source, root / "checkpoints")
            config["famdb_source_identity"]["resolved_device"] = 42
            stable = {key: config["famdb_source_identity"][key]
                      for key in recovery.SOURCE_STABLE_IDENTITY_FIELDS}
            pin42 = {"unit": unit, "expected_source_identity": stable,
                     "observed_source_identity": stable,
                     "source_device_audit": {"binding": "audit_only", "expected_resolved_device": 42,
                                             "observed_resolved_device": 42, "device_match": True}}
            pin65 = {**pin42, "source_device_audit": {"binding": "audit_only",
                                                      "expected_resolved_device": 42,
                                                      "observed_resolved_device": 65,
                                                      "device_match": False}}
            import h5py
            with mock.patch.object(recovery, "unit_pin_contract", return_value=pin42):
                with h5py.File(source, "r") as handle:
                    recovery.scan_and_publish_unit(root, config, handle, unit, {"A"}, "a", "0")
            with mock.patch.object(recovery, "unit_pin_contract", return_value=pin65):
                checkpoint = recovery.verify_unit_checkpoint(root, config, unit)
            self.assertEqual(checkpoint["manifest"]["pin_contract"]["source_device_audit"]
                             ["observed_resolved_device"], 42)

    def test_checkpoint_device_audit_tamper_is_local_corruption_and_quarantined(self):
        def mutate_missing_audit(pin):
            pin.pop("source_device_audit")

        def mutate_audit_field(pin, field, value):
            pin["source_device_audit"][field] = value

        def mutate_extra(pin):
            pin["source_device_audit"]["extra"] = "forged"

        def mutate_missing_field(pin):
            pin["source_device_audit"].pop("device_match")

        mutations = {
            "missing_audit": mutate_missing_audit,
            "binding": lambda pin: mutate_audit_field(pin, "binding", "binding"),
            "expected_drift": lambda pin: mutate_audit_field(pin, "expected_resolved_device", 43),
            "expected_bool": lambda pin: mutate_audit_field(pin, "expected_resolved_device", True),
            "expected_string": lambda pin: mutate_audit_field(pin, "expected_resolved_device", "42"),
            "observed_bool": lambda pin: mutate_audit_field(pin, "observed_resolved_device", False),
            "observed_string": lambda pin: mutate_audit_field(pin, "observed_resolved_device", "42"),
            "match_inconsistent": lambda pin: mutate_audit_field(pin, "device_match", False),
            "match_wrong_type": lambda pin: mutate_audit_field(pin, "device_match", "true"),
            "extra_field": mutate_extra,
            "missing_field": mutate_missing_field,
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as name:
                root = Path(name); source = root / "x.h5"; unit = "Families/Aux/a"
                make_h5(source, {unit: [{"name": "A", "accession": "D", "version": 1,
                                         "consensus": "A", "model": "M"}]})
                config = synthetic_cfg(source, root / "checkpoints")
                config["famdb_source_identity"]["resolved_device"] = 42
                valid_pin = mock_pin(config, unit)
                import h5py
                with mock.patch.object(recovery, "unit_pin_contract", return_value=valid_pin):
                    with h5py.File(source, "r") as handle:
                        recovery.scan_and_publish_unit(root, config, handle, unit, {"A"}, "a", "0")
                complete = root / f"checkpoints/units/{recovery.unit_slug(unit)}.COMPLETE"
                manifest_path = complete / "UNIT_COMPLETE_MANIFEST.json"
                manifest = json.loads(manifest_path.read_text())
                mutate(manifest["pin_contract"])
                recovery.atomic_json(manifest_path, manifest)
                with mock.patch.object(recovery, "unit_pin_contract", return_value=valid_pin):
                    reused, quarantined = recovery.resume_or_quarantine_unit(root, config, unit, "b")
                self.assertFalse(reused)
                self.assertIn("quarantine", quarantined)
                self.assertFalse(complete.exists())

    def test_current_device_audit_schema_is_validated_too(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = root / "x.h5"; unit = "Families/Aux/a"
            make_h5(source, {unit: [{"name": "A", "accession": "D", "version": 1,
                                     "consensus": "A", "model": "M"}]})
            config = synthetic_cfg(source, root / "checkpoints")
            valid_pin = mock_pin(config, unit)
            import h5py
            with mock.patch.object(recovery, "unit_pin_contract", return_value=valid_pin):
                with h5py.File(source, "r") as handle:
                    recovery.scan_and_publish_unit(root, config, handle, unit, {"A"}, "a", "0")
            malformed_current = json.loads(json.dumps(valid_pin))
            malformed_current["source_device_audit"]["observed_resolved_device"] = True
            with mock.patch.object(recovery, "unit_pin_contract", return_value=malformed_current):
                reused, quarantined = recovery.resume_or_quarantine_unit(root, config, unit, "b")
            self.assertFalse(reused)
            self.assertIn("quarantine", quarantined)

    def test_local_corrupt_json_and_tsv_schema_are_quarantined_for_unit_recompute(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = root / "x.h5"; unit = "Families/Aux/a"
            make_h5(source, {unit: [{"name": "A", "accession": "D", "version": 1,
                                     "consensus": "A", "model": "M"}]})
            config = synthetic_cfg(source, root / "checkpoints")
            import h5py
            pins = mock_pin(config, unit)

            def publish(attempt):
                with h5py.File(source, "r") as handle:
                    recovery.scan_and_publish_unit(root, config, handle, unit, {"A"}, attempt, "0")

            def rebind_payload(complete, filename):
                payload_path = complete / "UNIT_PAYLOAD_MANIFEST.json"
                payload = json.loads(payload_path.read_text())
                payload["files"][filename] = recovery.sha256_file(complete / filename)
                recovery.atomic_json(payload_path, payload)
                manifest_path = complete / "UNIT_COMPLETE_MANIFEST.json"
                manifest = json.loads(manifest_path.read_text())
                manifest["unit_payload_manifest_sha256"] = recovery.sha256_file(payload_path)
                recovery.atomic_json(manifest_path, manifest)

            with mock.patch.object(recovery, "unit_pin_contract", return_value=pins):
                publish("a")
                complete = root / f"checkpoints/units/{recovery.unit_slug(unit)}.COMPLETE"
                (complete / "unit_summary.json").write_text("{bad json\n")
                rebind_payload(complete, "unit_summary.json")
                reused, moved = recovery.resume_or_quarantine_unit(root, config, unit, "b")
                self.assertFalse(reused); self.assertIn("quarantine", moved)
                publish("c")
                complete = root / f"checkpoints/units/{recovery.unit_slug(unit)}.COMPLETE"
                (complete / "dataset_inventory.tsv").write_text("wrong_header\nvalue\n")
                rebind_payload(complete, "dataset_inventory.tsv")
                reused, moved = recovery.resume_or_quarantine_unit(root, config, unit, "d")
                self.assertFalse(reused); self.assertIn("quarantine", moved)

    def test_34_of_35_and_duplicate_omission_offset_and_attribute_gates(self):
        config = cfg()
        units35 = [f"u{index}" for index in range(35)]

        def checkpoint(unit, duplicate=False, low_consensus=False, low_model=False):
            index = int(unit[1:])
            address = "0" if duplicate and index == 34 else str(index)
            summary = {"consensus_attribute_count": 0 if low_consensus and index == 34 else 1,
                       "model_attribute_count": 0 if low_model and index == 34 else 1}
            return {"summary": summary, "inventory": [{"dataset_path": f"{unit}/D", "object_address": address}],
                    "candidates": []}

        config["famdb_expected_family_dataset_count"] = 35
        config["famdb_expected_consensus_attribute_count"] = 35
        config["famdb_expected_model_attribute_count"] = 35
        with mock.patch.object(recovery, "verify_unit_checkpoint", side_effect=lambda _r, _c, unit: checkpoint(unit)):
            inventory, candidates, audit = recovery.collect_complete_units(PROJECT, config, units35)
            self.assertEqual(len(inventory), 35)
            self.assertEqual(candidates, [])
            self.assertEqual(audit["complete_unit_count"], 35)
        with mock.patch.object(recovery, "verify_unit_checkpoint", side_effect=lambda _r, _c, unit: checkpoint(unit)):
            with self.assertRaisesRegex(recovery.IntegrityFailure, "34_OF_35"):
                recovery.collect_complete_units(PROJECT, config, units35[:34])
        with mock.patch.object(recovery, "verify_unit_checkpoint",
                               side_effect=lambda _r, _c, unit: checkpoint(unit, duplicate=True)):
            with self.assertRaisesRegex(recovery.IntegrityFailure, "HARDLINK_DUPLICATE"):
                recovery.collect_complete_units(PROJECT, config, units35)
        with mock.patch.object(recovery, "verify_unit_checkpoint",
                               side_effect=lambda _r, _c, unit: checkpoint(unit, low_consensus=True)):
            with self.assertRaisesRegex(recovery.IntegrityFailure, "CONSENSUS_COUNT"):
                recovery.collect_complete_units(PROJECT, config, units35)
        with mock.patch.object(recovery, "verify_unit_checkpoint",
                               side_effect=lambda _r, _c, unit: checkpoint(unit, low_model=True)):
            with self.assertRaisesRegex(recovery.IntegrityFailure, "MODEL_COUNT"):
                recovery.collect_complete_units(PROJECT, config, units35)

    def test_candidate_merge_same_identity_cross_unit_different_identity_and_bad_metadata(self):
        parent = recovery.load_module("test_parent_resolver", PROJECT / cfg()["parent_r0_evaluator"])
        targets = [target("SAME"), target("DIFF"), target("BAD")]
        base = {"accession": "", "version": "", "h5_dataset_path": "", "source_partition": "3", "source_unit": ""}
        candidates = [
            {**base, "identifier": "SAME", "versioned_accession": "DF1.1", "consensus_sha256": "a", "consensus_length": "10"},
            {**base, "identifier": "SAME", "versioned_accession": "DF1.1", "consensus_sha256": "a", "consensus_length": "10"},
            {**base, "identifier": "DIFF", "versioned_accession": "DF2.1", "consensus_sha256": "b", "consensus_length": "10"},
            {**base, "identifier": "DIFF", "versioned_accession": "DF3.1", "consensus_sha256": "c", "consensus_length": "10"},
            {**base, "identifier": "BAD", "versioned_accession": "", "consensus_sha256": "", "consensus_length": "0"}]
        resolution, metrics = parent.resolve_targets(targets, [recovery.candidate_for_parent(row) for row in candidates])
        self.assertEqual({row["identifier"]: row["status"] for row in resolution},
                         {"BAD": "invalid_metadata", "DIFF": "ambiguous", "SAME": "recovered"})
        self.assertEqual(metrics["target_identifier_count"], 3)
        self.assertEqual(len(candidates), 5)  # Source rows remain auditable; resolver does not delete them.

    def test_semantic_payload_byte_identical_for_oracle_shuffled_and_resume_shapes(self):
        parent = recovery.load_module("test_parent_semantic", PROJECT / cfg()["parent_r0_evaluator"])
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = root / "x.h5"
            units = [f"Families/Aux/u{index}" for index in range(4)]
            make_h5(source, {
                units[0]: [{"name": "A", "accession": "D1", "version": 1, "consensus": "AAAA", "model": "M"}],
                units[1]: [{"name": "B", "accession": "D2", "version": 1, "consensus": "CCCC", "model": "M"}],
                units[2]: [{"name": "OTHER2", "accession": "D3", "version": 1, "consensus": "GGGG", "model": "M"}],
                units[3]: [{"name": "OTHER3", "accession": "D4", "version": 1, "consensus": "TTTT", "model": "M"}]})
            targets = [target("A", 1), target("B", 2)]
            x13 = [{"identifier": "X13_LINE", "occurrences": "686", "labels": "LINE", "species": "s",
                    "status": "ambiguous", "resolution_status": "ambiguous", "resolution_method": "exact",
                    "candidate_count": "2", "detail": "audit"}]

            def execute_shape(label, order, resume_cut):
                checkpoint = root / f"checkpoints-{label}"
                config = synthetic_cfg(source, checkpoint)
                config["topology"]["expected_unit_count"] = 4
                config["famdb_expected_family_dataset_count"] = 4
                config["famdb_expected_consensus_attribute_count"] = 4
                config["famdb_expected_model_attribute_count"] = 4
                pins = lambda unit: mock_pin(
                    config, unit, expected_source_identity=config["famdb_source_identity"],
                    observed_source_identity=recovery.source_identity(source))
                import h5py
                with mock.patch.object(recovery, "unit_pin_contract", side_effect=lambda _r, _c, unit: pins(unit)):
                    with h5py.File(source, "r") as handle:
                        for position, unit in enumerate(order):
                            recovery.scan_and_publish_unit(root, config, handle, unit, {"A", "B"},
                                                           "first" if position < resume_cut else "second",
                                                           str(position % 4))
                            if position + 1 == resume_cut:
                                for prior in order[:resume_cut]:
                                    recovery.verify_unit_checkpoint(root, config, prior)
                    inventory, candidates, audit = recovery.collect_complete_units(root, config, units)
                payload = recovery.deterministic_semantic_payload(targets, x13, candidates, audit, config, parent)
                stage = root / f"semantic-{label}"; stage.mkdir()
                semantic_hash = recovery.write_semantic_payload(stage, payload, inventory)
                recovery.atomic_json(stage / "telemetry.json", {"shape": label, "resume_cut": resume_cut})
                return stage, semantic_hash

            one, h1 = execute_shape("oracle", units, 0)
            four, h2 = execute_shape("four-worker-reversed", list(reversed(units)), 0)
            resumed, h3 = execute_shape("half-resume", units, 2)
            self.assertEqual(h1, h2)
            self.assertEqual(h1, h3)
            for filename in json.loads((one / "SEMANTIC_PAYLOAD_MANIFEST.json").read_text())["files"]:
                self.assertEqual((one / filename).read_bytes(), (four / filename).read_bytes())
                self.assertEqual((one / filename).read_bytes(), (resumed / filename).read_bytes())
            self.assertNotEqual((one / "telemetry.json").read_bytes(), (four / "telemetry.json").read_bytes())

    def test_dynamic_queue_preference_then_steal_and_cutoff_starts_no_unit(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            queue = root / "queue"
            recovery.initialize_dynamic_queue(queue, ["u0", "u1"], {0: ["u0"], 1: ["u1"], 2: [], 3: []},
                                              {"u0": 10, "u1": 9})
            claim = recovery.claim_next_unit(queue, 1)
            self.assertEqual(claim[1]["unit"], "u1")
            # A prestop marker is checked before claim; no unit checkpoint can be started.
            source = root / "x.h5"
            make_h5(source, {"u0": [{"name": "A", "accession": "D", "version": 1,
                                      "consensus": "A", "model": "M"}]})
            (queue / "STOP").write_text("stop\n")
            result_stage = root / "result"
            with mock.patch.object(recovery, "validate_inputs",
                                   return_value=([target("A")], [], source, ["u0"], {}, object())):
                code = recovery.worker_run(PROJECT, cfg(), "a", 0, queue, result_stage, time.time() + 60)
            self.assertEqual(code, 75)
            self.assertFalse(any((root / "checkpoints").glob("**/*.COMPLETE")))

    def test_absolute_deadline_fake_clock_blocks_launch_and_late_complete_pointer(self):
        config = cfg(); start = 1000.0
        deadlines = recovery.deadline_contract(start, config)
        self.assertEqual(deadlines["claim_deadline_epoch"], 8980.0)
        self.assertEqual(deadlines["completion_deadline_epoch"], 9100.0)
        with mock.patch.object(recovery.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(recovery.IncompleteRetryable, "launch_workers_before_popen"):
                recovery.launch_workers([["never"]], [Path("unused")], Path("unused-logs"),
                                        deadlines["claim_deadline_epoch"], 1, 0.01, Path("unused-stop"),
                                        clock=lambda: deadlines["claim_deadline_epoch"])
            popen.assert_not_called()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); preview_cfg = minimal_preview(root); docs = {"x": 1}
            recovery.finalize_preview(root, preview_cfg, "FORMAL_RUNNING", "a", {"semantic_success": False}, {},
                                      input_manifest=docs, static_contract=docs)
            old_pointer = (root / "preview/CURRENT_STATE.json").read_bytes()
            with self.assertRaisesRegex(recovery.IncompleteRetryable, "before_atomic_state_pointer"):
                recovery.finalize_preview(root, preview_cfg, "RECOVERY_COMPLETE", "a",
                                          {"semantic_success": True}, {}, input_manifest=docs,
                                          static_contract=docs, pointer_deadline=9100.0, clock=lambda: 9100.0)
            self.assertEqual((root / "preview/CURRENT_STATE.json").read_bytes(), old_pointer)
        for hook_time in (9100.0, 9100.0001):
            with self.subTest(hook_time=hook_time), tempfile.TemporaryDirectory() as name:
                root = Path(name); preview_cfg = minimal_preview(root); docs = {"x": 1}
                recovery.finalize_preview(root, preview_cfg, "FORMAL_RUNNING", "a",
                                          {"semantic_success": False}, {},
                                          input_manifest=docs, static_contract=docs)
                old_pointer = (root / "preview/CURRENT_STATE.json").read_bytes()
                now = [9099.0]

                def source_revalidation_hook():
                    now[0] = hook_time

                with self.assertRaisesRegex(recovery.IncompleteRetryable,
                                            "after_pointer_hook_before_atomic_state_pointer"):
                    recovery.finalize_preview(root, preview_cfg, "RECOVERY_COMPLETE", "a",
                                              {"semantic_success": True}, {}, input_manifest=docs,
                                              static_contract=docs, pointer_deadline=9100.0,
                                              clock=lambda: now[0],
                                              before_pointer_hook=source_revalidation_hook)
                self.assertEqual((root / "preview/CURRENT_STATE.json").read_bytes(), old_pointer)
                self.assertFalse((root / "preview/CURRENT_STATE.json.tmp").exists())
                self.assertEqual(recovery.verify_state_bundle(root, preview_cfg)["terminal"]["status"],
                                 "FORMAL_RUNNING")

    def test_completed_nonzero_kills_hanging_sibling_fail_fast(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            commands = [[sys.executable, "-c", "raise SystemExit(3)"],
                        [sys.executable, "-c", "import time;time.sleep(60)"]]
            started = time.monotonic()
            with self.assertRaisesRegex(recovery.IntegrityFailure, "WORKER_NONZERO"):
                recovery.launch_workers(commands, [root / "r0", root / "r1"], root / "logs", time.time() + 10, 2, 0.02,
                                        root / "STOP")
            self.assertLess(time.monotonic() - started, 3)

    def test_sigterm_resistant_child_is_killed_reaped_and_false_reap_forbids_terminal_publish(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            resistant = ("import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)")
            with self.assertRaises(recovery.ResourceFailure):
                recovery.launch_workers([[sys.executable, "-c", resistant]], [root / "r"], root / "logs",
                                        time.time() + 0.1, 0.1, 0.02, root / "STOP")
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            failed = types.SimpleNamespace(poll=lambda: 3, returncode=3)
            hanging = types.SimpleNamespace(poll=lambda: None, returncode=None)
            with mock.patch.object(recovery.subprocess, "Popen", side_effect=[failed, hanging]), \
                    mock.patch.object(recovery, "terminate_and_wait", return_value=False):
                with self.assertRaises(recovery.UnreapedChildren):
                    recovery.launch_workers([["failed"], ["hang"]], [root / "r0", root / "r1"], root / "logs",
                                            time.time() + 5, 1, 0.02, root / "STOP")
            preview_cfg = minimal_preview(root); docs = {"x": 1}
            recovery.finalize_preview(root, preview_cfg, "FORMAL_RUNNING", "a", {"semantic_success": False}, {},
                                      input_manifest=docs, static_contract=docs)
            marker = root / "preview/attempts/a.tmp/UNREAPED_CHILDREN.json"
            recovery.atomic_json(marker, {"terminal_publish_forbidden": True})
            status, _metrics = recovery.shell_failure_finalize(root, preview_cfg, "a", 70)
            self.assertEqual(status, "FORMAL_RUNNING")
            self.assertEqual(recovery.verify_state_bundle(root, preview_cfg)["terminal"]["status"], "FORMAL_RUNNING")

    def test_worker_zero_exit_with_hash_or_schema_tamper_is_integrity_failure(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            stage = root / "result"
            code = ("import json,pathlib; p=pathlib.Path(" + repr(str(stage)) + ");p.mkdir();"
                    "(p/'worker_result.json').write_text(json.dumps({'status':'WORKER_COMPLETE'}));"
                    "(p/'worker_manifest.json').write_text(json.dumps({'worker_result_sha256':'bad'}))")
            with self.assertRaisesRegex(recovery.IntegrityFailure, "WORKER_OUTPUT_HASH_DRIFT"):
                recovery.launch_workers([[sys.executable, "-c", code]], [stage], root / "logs", time.time() + 5, 1, 0.02,
                                        root / "STOP")

    def test_owner_lock_squeue_live_dead_unknown_tristate(self):
        def result(rc, stdout=""):
            return types.SimpleNamespace(returncode=rc, stdout=stdout)

        with tempfile.TemporaryDirectory() as name:
            preview = Path(name)
            lock = preview / ".lock"
            lock.mkdir(); (lock / "job_id").write_text("10\n")
            with self.assertRaisesRegex(recovery.ResourceFailure, "OWNER_LOCK_LIVE"):
                recovery.acquire_owner_lock(preview, ".lock", "20", lambda *_a, **_k: result(0, "RUNNING\n"))
            with self.assertRaisesRegex(recovery.ResourceFailure, "STATE_UNKNOWN"):
                recovery.acquire_owner_lock(preview, ".lock", "20", lambda *_a, **_k: result(1))
            self.assertEqual(recovery.acquire_owner_lock(preview, ".lock", "20",
                                                         lambda *_a, **_k: result(0, "")), "ACQUIRED")
            self.assertEqual((preview / ".lock/job_id").read_text().strip(), "20")
            recovery.release_owner_lock(preview, ".lock", "20")
            self.assertFalse((preview / ".lock").exists())

    def test_immutable_state_pointer_interrupt_preserves_old_closed_running_then_switches_complete(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = minimal_preview(root)
            documents = {"x": 1}
            recovery.finalize_preview(root, config, "FORMAL_RUNNING", "a", {"semantic_success": False}, {},
                                      input_manifest=documents, static_contract=documents)
            old_pointer_bytes = (root / "preview/CURRENT_STATE.json").read_bytes()
            old_state = recovery.verify_state_bundle(root, config)

            def interrupted():
                raise OSError("synthetic pointer interruption")

            with self.assertRaisesRegex(OSError, "pointer interruption"):
                recovery.finalize_preview(root, config, "RECOVERY_COMPLETE", "a",
                                          {"semantic_success": True, "full_catalog_human_gate_eligible": True}, {},
                                          input_manifest=documents, static_contract=documents,
                                          before_pointer_hook=interrupted)
            self.assertEqual((root / "preview/CURRENT_STATE.json").read_bytes(), old_pointer_bytes)
            self.assertEqual(recovery.verify_state_bundle(root, config)["terminal"]["status"], "FORMAL_RUNNING")
            # Every line in the old immutable manifest still closes after interrupted new-bundle construction.
            recovery.verify_state_bundle(root, config, old_state["pointer"])
            recovery.finalize_preview(root, config, "RECOVERY_COMPLETE", "a",
                                      {"semantic_success": True, "full_catalog_human_gate_eligible": True}, {},
                                      input_manifest=documents, static_contract=documents)
            new_state = recovery.verify_state_bundle(root, config)
            self.assertEqual(new_state["terminal"]["status"], "RECOVERY_COMPLETE")
            self.assertNotEqual(new_state["pointer"], old_state["pointer"])

    def test_immutable_state_rejects_unmanifested_file_directory_and_symlink(self):
        for kind in ("file", "directory", "symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                config = minimal_preview(root)
                recovery.finalize_preview(root, config, "FORMAL_RUNNING", "a",
                                          {"semantic_success": False}, {},
                                          input_manifest={"x": 1}, static_contract={"x": 1})
                state = recovery.verify_state_bundle(root, config)["state"]
                extra = state / f"UNMANIFESTED-{kind}"
                if kind == "file":
                    extra.write_text("injected\n")
                elif kind == "directory":
                    extra.mkdir()
                else:
                    target = root / "outside.txt"
                    target.write_text("outside\n")
                    extra.symlink_to(target)
                with self.assertRaisesRegex(recovery.IntegrityFailure,
                                            "STATE_(EXACT_FILE_SET_DRIFT|UNMANIFESTED_NONREGULAR)"):
                    recovery.verify_state_bundle(root, config)

    def test_immutable_state_manifest_rejects_duplicate_traversal_self_and_missing_entry(self):
        mutations = {
            "duplicate": lambda lines: lines + [lines[0]],
            "traversal": lambda lines: lines + ["0" * 64 + "  ../escape"],
            "self": lambda lines: lines + ["0" * 64 + "  STATE_MANIFEST.sha256"],
            "missing": lambda lines: lines[:-1],
        }
        for kind, mutate in mutations.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                config = minimal_preview(root)
                recovery.finalize_preview(root, config, "FORMAL_RUNNING", "a",
                                          {"semantic_success": False}, {},
                                          input_manifest={"x": 1}, static_contract={"x": 1})
                pointer_path = root / "preview/CURRENT_STATE.json"
                pointer = json.loads(pointer_path.read_text())
                state = root / pointer["state_root_relative"]
                manifest = state / "STATE_MANIFEST.sha256"
                recovery.atomic_text(manifest, "\n".join(mutate(manifest.read_text().splitlines())) + "\n")
                pointer["state_manifest_sha256"] = recovery.sha256_file(manifest)
                recovery.atomic_json(pointer_path, pointer)
                with self.assertRaises(recovery.IntegrityFailure):
                    recovery.verify_state_bundle(root, config)

    def test_final_source_mutation_before_pointer_keeps_old_state_canonical(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = minimal_preview(root)
            documents = {"x": 1}
            source, replacement = root / "source.h5", root / "replacement.h5"
            unit = "Families/Aux/a"
            rows = [{"name": "A", "accession": "D", "version": 1,
                     "consensus": "AAAA", "model": "M"}]
            make_h5(source, {unit: rows})
            shutil.copy2(source, replacement)
            import h5py
            with h5py.File(replacement, "r+") as handle:
                handle[f"{unit}/D0"].attrs.modify("name", "B")
            self.assertEqual(source.stat().st_size, replacement.stat().st_size)
            expected = recovery.source_identity(source)
            recovery.finalize_preview(root, config, "FORMAL_RUNNING", "a",
                                      {"semantic_success": False}, {},
                                      input_manifest=documents, static_contract=documents)
            old_pointer = (root / "preview/CURRENT_STATE.json").read_bytes()

            def mutate_then_validate():
                os.replace(replacement, source)
                recovery.validate_source_identity(source, expected)

            with self.assertRaisesRegex(recovery.GlobalPinDrift, "SOURCE_IDENTITY_DRIFT"):
                recovery.finalize_preview(root, config, "RECOVERY_COMPLETE", "a",
                                          {"semantic_success": True}, {},
                                          input_manifest=documents, static_contract=documents,
                                          before_pointer_hook=mutate_then_validate)
            self.assertEqual((root / "preview/CURRENT_STATE.json").read_bytes(), old_pointer)
            self.assertEqual(recovery.verify_state_bundle(root, config)["terminal"]["status"],
                             "FORMAL_RUNNING")

    def test_shell_failure_overwrites_static_or_running_but_preserves_same_attempt_terminal(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = minimal_preview(root)
            recovery.finalize_preview(root, config, "IMPLEMENTED_NOT_RUN", "static-preview",
                                      {"semantic_success": False}, {}, input_manifest={}, static_contract={})
            status, _metrics = recovery.shell_failure_finalize(root, config, "a", 3)
            self.assertEqual(status, "FORMAL_FAILED_INTEGRITY")
            self.assertEqual(recovery.verify_state_bundle(root, config)["terminal"]["attempt_id"], "a")
            status2, _metrics2 = recovery.shell_failure_finalize(root, config, "a", 137)
            self.assertEqual(status2, "FORMAL_FAILED_INTEGRITY")

    def test_specific_validation_error_is_canonical_and_generic_trap_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); config = minimal_preview(root)
            recovery.finalize_preview(root, config, "IMPLEMENTED_NOT_RUN", "static-preview",
                                      {"semantic_success": False}, {}, input_manifest={}, static_contract={})
            detail = "GlobalPinDrift:SOURCE_ASSET_REALPATH_DRIFT:/unknown"
            recovery.failure_terminal(root, config, "attempt", "FORMAL_FAILED_INTEGRITY", detail)
            status, metrics = recovery.shell_failure_finalize(root, config, "attempt", 2)
            self.assertEqual(status, "FORMAL_FAILED_INTEGRITY")
            self.assertEqual(metrics["error"], detail)
            current = recovery.verify_state_bundle(root, config)
            self.assertEqual(current["metrics"]["error"], detail)
            self.assertEqual(json.loads((current["state"] / "report.json").read_text())["error"], detail)

    def test_final_payload_manifest_tamper_and_terminal_codes(self):
        with tempfile.TemporaryDirectory() as name:
            stage = Path(name)
            for filename in ("SEMANTIC_PAYLOAD_MANIFEST.json", "canonical_dataset_inventory.tsv", "metrics.json", "report.json", "resolution.tsv",
                             "telemetry.json", "RUN_MANIFEST.json", "env.json", "unit_manifests.json"):
                (stage / filename).write_text(filename)
            recovery.create_final_payload_manifest(stage)
            recovery.verify_final_payload(stage)
            (stage / "metrics.json").write_text("tamper")
            with self.assertRaisesRegex(recovery.IntegrityFailure, "FINAL_PAYLOAD_DRIFT"):
                recovery.verify_final_payload(stage)
        self.assertEqual(recovery.terminal_exit_code("RECOVERY_COMPLETE"), 0)
        self.assertEqual(recovery.terminal_exit_code("IDENTITY_RECOVERY_TYPED_BLOCK"), 0)
        self.assertEqual(recovery.terminal_exit_code("FORMAL_INCOMPLETE_RETRYABLE"), 75)
        self.assertEqual(recovery.terminal_exit_code("FORMAL_FAILED_RESOURCE"), 70)
        self.assertEqual(recovery.terminal_exit_code("FORMAL_FAILED_INTEGRITY"), 2)

    def test_resource_math_no_speedup_guarantee_and_no_scientific_fallback(self):
        config = cfg()
        evidence = config["resource_evidence"]
        self.assertEqual(evidence["headroom_target_seconds"], 8100)
        self.assertEqual(config["runtime"]["work_completion_cutoff_seconds"], 8100)
        self.assertEqual(config["runtime"]["new_unit_claim_cutoff_seconds"], 7980)
        self.assertEqual(config["runtime"]["publish_reserve_seconds"], 120)
        self.assertAlmostEqual(evidence["observed_serial_bound_seconds"] / evidence["headroom_target_seconds"],
                               evidence["minimum_required_parallel_speedup"], places=3)
        self.assertFalse(evidence["beegfs_speedup_guaranteed"])
        contract = config["resolver_contract"]
        self.assertTrue(contract["prefix_guess_forbidden"])
        self.assertTrue(contract["casefold_forbidden"])
        self.assertTrue(contract["copy_derived_proxy_forbidden"])
        source = (HERE / "recover_sharded.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("mmseqs", source)
        self.assertNotIn("blast", source)
        self.assertNotIn("genome_copy", source)

    def test_sbatch_cpu_route_signal_log_guard_activation_and_failure_finalizer(self):
        text = (PROJECT / f"sbatch/{EXP}.sbatch").read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertIn("#SBATCH --time=03:00:00", text)
        self.assertIn("#SBATCH --cpus-per-task=4", text)
        self.assertIn("#SBATCH --mem=48G", text)
        self.assertIn("#SBATCH --signal=B:TERM@900", text)
        self.assertNotIn("#SBATCH --gres", text)
        self.assertIn('test -d "${RECOVERY_PREVIEW}/logs"', text)
        self.assertIn("--acquire-owner-lock-only", text)
        self.assertIn("--shell-failure-finalize", text)
        self.assertIn("kill -TERM", text)
        self.assertLess(text.index("conda activate te_benchmark"), text.index("set -u"))
        self.assertLess(text.index("--prepare-running-only"), text.index("test_recover_sharded.py"))
        self.assertIn("pre_submit_gate.py", text)
        self.assertIn('test -z "${SLURM_JOB_GPUS:-}"', text)


if __name__ == "__main__":
    unittest.main()
