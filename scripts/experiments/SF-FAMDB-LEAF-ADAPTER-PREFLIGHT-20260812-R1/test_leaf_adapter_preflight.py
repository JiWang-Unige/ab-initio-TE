#!/usr/bin/env python3
import importlib.util
import ast
import json
import os
import signal
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("adapter", HERE / "leaf_adapter_preflight.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ROOT = HERE.parents[2]
CFG = m.load_config(ROOT / "configs" / (m.EXP_ID + ".yaml"))


def parent_cfg(): return json.loads((ROOT / CFG["parent_contract"]["config"]).read_text())


def rows():
    out = []
    names = ["A", "B", "C", "D", "E", ""]
    classes = ["SINE/Alu", "LINE/L1", "LINE/L1", "LTR/ERVL", "DNA/hAT-Blackjack", "RC/Helitron"]
    for i in range(6):
        accession = ("DR" if i == 5 else "DF") + ("%09d" % (i + 1)); seq = "ACGT" * (i + 2)
        out.append({"index": i, "accession": accession, "versioned_accession": accession + ".2",
          "canonical_name": names[i], "raw_class": classes[i], "partition": 3 if i == 5 else 7,
          "consensus_length": len(seq), "consensus_sha256": m.sha256_bytes(seq.encode()), "sequence": seq,
          "parent_audited_manifest_sha256": CFG["parent_contract"]["artifacts"][
            "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256"]})
    return out


def slurm_env():
    return {"SLURM_JOB_ID": "17", "SLURM_CPUS_PER_TASK": "1", "SLURM_MEM_PER_NODE": "4G",
            "SLURM_JOB_PARTITION": "private-teodoro-gpu"}


def scontrol_line(**changes):
    c = CFG["slurm_contract"]
    fields = {"JobId": "17", "Partition": c["partition"], "TimeLimit": c["time_limit"], "NumCPUs": "1",
      "ReqTRES": "cpu=1,mem=4G,node=1,billing=2", "AllocTRES": "cpu=1,mem=4G,node=1,billing=2",
      "Command": c["command"], "SubmitLine": c["submit_line"]}
    fields.update(changes); return " ".join("%s=%s" % x for x in fields.items()) + "\n"


def minimal_files(status):
    allowed = m.OUTPUT_PASS if status == "LEAF_ADAPTER_PREFLIGHT_PASS" else m.OUTPUT_COMMON
    files = {name: "{}\n" for name in allowed}
    files["metrics.json"] = m.canonical_json({"status": status})
    files["report.json"] = m.canonical_json({"status": status})
    return files


def running_files():
    return {"metrics.json": m.canonical_json({"status": "FORMAL_RUNNING"}),
            "report.json": m.canonical_json({"status": "FORMAL_RUNNING"}), "RUN_MANIFEST.json": "{}\n"}


def static_files():
    return {"metrics.json": m.canonical_json({"status": "IMPLEMENTED_NOT_RUN"}),
            "report.json": m.canonical_json({"status": "IMPLEMENTED_NOT_RUN"}), "RUN_MANIFEST.json": "{}\n"}


class Handle:
    def __init__(self, fail=False): self.calls = 0; self.fail = fail; self.id = types.SimpleNamespace(valid=1)
    def close(self):
        self.calls += 1
        if self.fail: raise OSError("close fail")
        self.id.valid = 0


class Leaf:
    def __init__(self, part, targets, fail=False): self.part = part; self.targets = targets; self.calls = 0; self.file = Handle(fail)
    def get_family_by_accession(self, accession):
        self.calls += 1; target = next(x for x in self.targets if x["accession"] == accession)
        if target["partition"] != self.part: return None
        head = target["raw_class"].split("/", 1)
        family = types.SimpleNamespace(accession=target["accession"], version=int(target["versioned_accession"].split(".")[-1]),
          name=target["canonical_name"], repeat_type=head[0], repeat_subtype=head[1] if len(head) == 2 else None,
          consensus="A" * target["consensus_length"])
        family.accession_with_optional_version = lambda: target["versioned_accession"]
        return family


class Tests(unittest.TestCase):
    def test_01_config_and_parent_evidence_contract(self):
        m.validate_config(CFG); pcfg, pins = m.validate_parent_evidence(ROOT, CFG)
        self.assertEqual(len(pcfg["selected_records"]), 6); self.assertEqual(len(pins), 4)

    def test_02_parent_component_gate_result_and_runner_are_hash_pinned(self):
        p = CFG["parent_contract"]
        self.assertEqual(m.sha256_file(ROOT / p["runner"]), p["runner_sha256"])
        self.assertEqual(m.sha256_file(ROOT / p["config"]), p["config_sha256"])
        for rel, digest in p["artifacts"].items(): self.assertEqual(m.sha256_file(ROOT / rel), digest)

    def test_03_exact_paired_views_and_output_derived_manifest(self):
        result = m.materialize_views(rows())
        self.assertFalse(result["typed_block"]); self.assertEqual(len(result["records"]), 6)
        left = m.parse_fasta(result["canonical_name_view.fa"]); right = m.parse_fasta(result["accession_version_view.fa"])
        self.assertEqual([x[1] for x in left], [x[1] for x in right])
        self.assertEqual(result["ordered_sequence_class_semantic_sha256_control"],
                         result["ordered_sequence_class_semantic_sha256_candidate"])
        self.assertEqual([x["index"] for x in result["records"]], list(range(6)))

    def test_04_dr_empty_name_falls_back_to_unversioned_accession(self):
        result = m.materialize_views(rows()); row = result["records"][-1]
        self.assertEqual(row["canonical_name"], "")
        self.assertEqual(row["control_header"], ">DR000000006#RC/Helitron")
        self.assertEqual(row["candidate_header"], ">DR000000006.2#RC/Helitron")
        self.assertEqual(row["provenance_namespace"], "DR")

    def test_05_header_grammar_case_version_and_injection(self):
        row = rows()[0]
        for value in ("bad name", "bad#name", "bad\nname", "é"):
            bad = dict(row, canonical_name=value)
            with self.subTest(value=value), self.assertRaises(m.AdapterTypedBlock): m.make_header("canonical_name", bad)
        with self.assertRaises(m.AdapterTypedBlock): m.make_header("accession.version", dict(row, versioned_accession=row["accession"]))
        with self.assertRaises(m.IntegrityError): m.parse_header(">A#B#C")
        self.assertEqual(m.parse_header(m.make_header("canonical_name", row)), ("A", "SINE/Alu"))

    def test_06_order_omit_duplicate_extra_rejected(self):
        variants = [rows()[::-1], rows()[:-1], rows() + [dict(rows()[0], index=6)], rows()[:5] + [rows()[4]]]
        for variant in variants:
            with self.subTest(n=len(variant)), self.assertRaises(m.AdapterTypedBlock): m.materialize_views(variant)

    def test_07_sequence_class_and_collision_mutations_rejected(self):
        bad = rows(); bad[1] = dict(bad[1], sequence="TT", consensus_length=2,
                                    consensus_sha256=m.sha256_bytes(b"TT"))
        result = m.materialize_views(bad)
        self.assertNotEqual(result["records"][0]["consensus_sha256"], result["records"][1]["consensus_sha256"])
        collision = rows(); collision[1] = dict(collision[1], canonical_name=collision[0]["canonical_name"])
        with self.assertRaises(m.AdapterTypedBlock): m.materialize_views(collision)
        with self.assertRaises(m.AdapterTypedBlock): m.materialize_views([dict(x, raw_class="bad class") if x["index"] == 2 else x for x in rows()])

    def test_08_missing_duplicate_identity_and_sequence_are_typed_blocks(self):
        pcfg = {"selected_records": [{k: v for k, v in x.items() if k not in {"index", "sequence", "parent_audited_manifest_sha256"}}
                                      for x in rows()], "source_contract": {"expected_partition_order": list(range(12))}}
        observations = []
        for target in pcfg["selected_records"]:
            for part in range(12): observations.append({"queried_accession": target["accession"], "partition": part, "record": None})
        self.assertTrue(m.evaluate_actual(pcfg, observations)["typed_block"])
        target = pcfg["selected_records"][0]; observations[0]["record"] = dict(target, sequence=rows()[0]["sequence"])
        observations[1]["record"] = dict(target, partition=1, sequence=rows()[0]["sequence"])
        self.assertEqual(m.evaluate_actual(pcfg, observations)["failures"][0]["reason"], "duplicate")

    def test_09_observation_manifest_mapping_tamper_and_preexisting_attempt(self):
        result = m.materialize_views(rows()); result["observations"] = []
        with tempfile.TemporaryDirectory() as td:
            bundle, digest = m.stage_precleanup(td, "x", result)
            self.assertEqual(m.verify_observation(bundle, "x"), digest)
            (bundle / "record_manifest.json").write_text("[]\n")
            with self.assertRaises(m.IntegrityError): m.verify_observation(bundle, "x")
            with self.assertRaises(m.IntegrityError): m.stage_precleanup(td, "x", result)

    def test_10_exact_72_api_calls_close_12_and_no_fallback(self):
        parent = m.import_parent(ROOT, CFG); pcfg = parent_cfg(); targets = pcfg["selected_records"]
        leaves = {p: Leaf(p, targets) for p in pcfg["source_contract"]["expected_partition_order"]}
        class DB:
            def __new__(cls): obj = object.__new__(cls); obj.files = {}; return obj
            def __init__(self, _path, _mode): self.files = leaves
        module = types.SimpleNamespace(FamDB=DB)
        controller = parent.DeferredCleanupSignals().enter()
        try:
            with tempfile.TemporaryDirectory() as td, mock.patch.dict(sys.modules, {"famdb_classes": module}):
                result = m.probe_with_lifecycle(Path(td), CFG, parent, pcfg, controller, Path(td) / "preview", "x")
            self.assertEqual(sum(x.calls for x in leaves.values()), 72)
            self.assertEqual(sum(x.file.calls for x in leaves.values()), 12)
            self.assertTrue(result["typed_block"])  # synthetic A-sequences intentionally mismatch pinned SHA.
        finally:
            if controller.active: controller.restore_for_tests()

        controller = parent.DeferredCleanupSignals().enter()
        try:
            with tempfile.TemporaryDirectory() as td:
                files = {k: "{}\n" for k in m.OUTPUT_PASS}; m.publish(td, "old", "FORMAL_RUNNING", False,
                  running_files())
                os.kill(os.getpid(), signal.SIGTERM)
                with self.assertRaises(parent.TerminationRequested):
                    m.publish(td, "terminal", "LEAF_ADAPTER_PREFLIGHT_PASS", True, files, controller=controller)
                self.assertEqual(m.verify_bundle(td)["status"], "FORMAL_RUNNING")
        finally:
            if controller.active: controller.restore_for_tests()

    def test_11_close_error_is_runtime_not_typed(self):
        parent = m.import_parent(ROOT, CFG); pcfg = parent_cfg()
        files = {p: Leaf(p, pcfg["selected_records"], fail=(p == 3)) for p in pcfg["source_contract"]["expected_partition_order"]}
        with self.assertRaises(parent.CleanupError): parent.close_leaf_handles(files, pcfg)
        self.assertEqual(sum(x.file.calls for x in files.values()), 12)

    def test_12_resource_and_scontrol_exactness(self):
        m.validate_resource_env(slurm_env())
        for key, value in (("SLURM_JOB_ID", "x"), ("SLURM_CPUS_PER_TASK", "2"),
                           ("SLURM_MEM_PER_NODE", "4097"), ("SLURM_JOB_PARTITION", "debug-cpu"),
                           ("CUDA_VISIBLE_DEVICES", "0")):
            env = slurm_env(); env[key] = value
            with self.subTest(key=key), self.assertRaises(m.IntegrityError): m.validate_resource_env(env)
        audit = m.query_slurm(ROOT, CFG, slurm_env(), executor=lambda *_: (0, scontrol_line(), ""))
        self.assertEqual(audit["fields"]["JobId"], "17")
        for changes in ({"TimeLimit": "00:11:00"}, {"ReqTRES": "cpu=1,cpu=1,mem=4G,node=1,billing=2"},
                        {"Command": "/tmp/bad"}, {"SubmitLine": "sbatch --mem=8G x"}):
            with self.subTest(changes=changes), self.assertRaises(m.IntegrityError):
                m.query_slurm(ROOT, CFG, slurm_env(), executor=lambda *_, c=changes: (0, scontrol_line(**c), ""))

    def test_13_immutable_bundle_exact_set_and_tamper(self):
        files = minimal_files("LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK")
        with tempfile.TemporaryDirectory() as td:
            m.publish(td, "x", "LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK", True, files)
            self.assertEqual(m.verify_bundle(td)["status"], "LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK")
            bundle = Path(td) / (Path(td) / "CURRENT").read_text().strip(); (bundle / "extra").write_text("x")
            with self.assertRaises(m.IntegrityError): m.verify_bundle(td)

    def test_14_new_gate_is_independent_and_exact_package(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root / CFG["code_review_gate_path"]; path.parent.mkdir(parents=True)
            package = {"x": "0" * 64}; path.write_text(m.canonical_json({"exp_id": m.EXP_ID, "verdict": "PASS",
              "blockers_open": 0, "reviewed_files": package}))
            with mock.patch.object(m, "package_hashes", return_value=package): self.assertEqual(m.validate_gate(root, CFG), m.sha256_file(path))
            gate = json.loads(path.read_text()); gate["exp_id"] = CFG["parent_contract"]["exp_id"]; path.write_text(m.canonical_json(gate))
            with mock.patch.object(m, "package_hashes", return_value=package), self.assertRaises(m.IntegrityError): m.validate_gate(root, CFG)

    def test_15_static_never_opens_h5_or_calls_api(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = dict(CFG, project_root=str(root), preview_root="preview")
            with mock.patch.object(m, "validate_parent_evidence", return_value=(parent_cfg(), {})), \
                 mock.patch.object(m, "import_parent", return_value=object()), \
                 mock.patch.object(m, "package_hashes", return_value={}), \
                 mock.patch.object(m, "probe_with_lifecycle", side_effect=AssertionError("H5/API forbidden")):
                m.static_preview(root, cfg, "static")
            self.assertEqual(m.verify_bundle(root / "preview")["status"], "IMPLEMENTED_NOT_RUN")

    def test_16_scheduler_guard_precedes_parent_import(self):
        order = []
        with mock.patch.object(m, "load_config", return_value=CFG), mock.patch.object(m, "validate_config"), \
             mock.patch.object(m, "query_slurm", side_effect=lambda *_: order.append("scheduler") or {}), \
             mock.patch.object(m, "import_parent", side_effect=lambda *_: order.append("parent") or (_ for _ in ()).throw(m.IntegrityError("stop"))), \
             mock.patch.object(m, "attempt_failure"), mock.patch.object(sys, "stderr"), mock.patch.dict(os.environ, slurm_env(), clear=True):
            self.assertEqual(m.main(["--config", "x"]), 2)
        self.assertEqual(order, ["scheduler", "parent"])

    def test_17_parent_hash_drift_refused_before_api(self):
        cfg = json.loads(json.dumps(CFG)); cfg["parent_contract"]["runner_sha256"] = "0" * 64
        with self.assertRaises(m.IntegrityError): m.import_parent(ROOT, cfg)

    def test_18_forbidden_actions_absent(self):
        source = (HERE / "leaf_adapter_preflight.py").read_text()
        tree = ast.parse(source); forbidden_calls = ("RepeatMasker", "rmblastn", "mmseqs", "cd-hit", "sbatch", "srun")
        command_literals = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"run", "Popen", "call"}:
                command_literals.extend(x.value for x in ast.walk(node) if isinstance(x, ast.Constant) and isinstance(x.value, str))
        for token in forbidden_calls:
            self.assertFalse(any(token in literal for literal in command_literals), (token, command_literals))
        self.assertNotIn("genome_copy", source); self.assertNotIn("prefix_fallback", source)

    def test_19_sbatch_contract_and_no_cli_override(self):
        text = (ROOT / "sbatch" / (m.EXP_ID + ".sbatch")).read_text()
        for token in ("#SBATCH --partition=private-teodoro-gpu", "#SBATCH --cpus-per-task=1", "#SBATCH --mem=4G",
                      "#SBATCH --time=00:10:00", "conda activate te_benchmark", "--kill-after=30s 480s"):
            self.assertIn(token, text)
        self.assertIn("pre_submit_gate.py", text); self.assertNotIn("sbatch --", text)

    def test_20_machine_report_anti_overclaim_fields(self):
        result = m.materialize_views(rows()); result.update({"observations": [], "close_audit": {}})
        authority = {"source": {}, "slurm": {}, "package_sha256": {}, "gate_sha256": "g",
                     "owner_sha256": "o", "parent_pins": {}}
        files = m.result_files(result, "LEAF_ADAPTER_PREFLIGHT_PASS", authority, authority, "obs", "h")
        metrics = json.loads(files["metrics.json"])
        for key in ("representative", "concordance_evidence", "annotation_executed", "RepeatMasker_executed",
                    "geometry_evaluated", "claim_eligible", "data_authorized", "gpu_authorized", "s1_authorized"):
            self.assertFalse(metrics[key])
        self.assertEqual(metrics["denominator"], 6)

    def test_21_output_mapping_rejects_self_consistent_manifest_tamper(self):
        result = m.materialize_views(rows()); manifest = json.loads(json.dumps(result["records"]))
        manifest[0]["canonical_name"] = "WRONG"
        with self.assertRaises(m.IntegrityError):
            m.validate_output_mapping(result["canonical_name_view.fa"], result["accession_version_view.fa"],
                                      manifest, rows()[0]["parent_audited_manifest_sha256"])
        # Same biological sequence with a noncanonical line break must still fail byte-level grammar.
        drift = result["canonical_name_view.fa"].replace(b"ACGTACGT\n", b"ACGT\nACGT\n", 1)
        with self.assertRaises(m.IntegrityError):
            m.validate_output_mapping(drift, result["accession_version_view.fa"], result["records"],
                                      rows()[0]["parent_audited_manifest_sha256"])
        manifest = json.loads(json.dumps(result["records"])); manifest[0]["parent_audited_manifest_sha256"] = "0" * 64
        with self.assertRaises(m.IntegrityError):
            m.validate_output_mapping(result["canonical_name_view.fa"], result["accession_version_view.fa"],
                                      manifest, rows()[0]["parent_audited_manifest_sha256"])

    def test_22_owner_and_writer_lock_races_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = dict(CFG, preview_root="preview"); owner = root / "preview" / cfg["owner_lock_name"]
            owner.mkdir(parents=True); (owner / "job_id").write_text("17\n")
            self.assertRegex(m.validate_owner(root, cfg, slurm_env()), r"^[0-9a-f]{64}$")
            (owner / "extra").write_text("x")
            with self.assertRaises(m.IntegrityError): m.validate_owner(root, cfg, slurm_env())
        with tempfile.TemporaryDirectory() as td, m.writer_mutex(td):
            with self.assertRaises(m.IntegrityError):
                m.publish(td, "x", "IMPLEMENTED_NOT_RUN", False,
                  static_files())

    def test_23_static_rejects_formal_state_owner_and_current_cas(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cfg = dict(CFG, project_root=str(root), preview_root="preview")
            preview = root / "preview"; m.publish(preview, "formal", "FORMAL_RUNNING", False, running_files())
            with mock.patch.object(m, "validate_parent_evidence", return_value=(parent_cfg(), {})), \
                 mock.patch.object(m, "import_parent", return_value=object()):
                with self.assertRaises(m.IntegrityError): m.static_preview(root, cfg, "static")
        with tempfile.TemporaryDirectory() as td:
            m.publish(td, "a", "IMPLEMENTED_NOT_RUN", False, static_files())
            current = m.current_bytes(td)
            m.publish(td, "intervening", "IMPLEMENTED_NOT_RUN", False, static_files())
            with self.assertRaises(m.IntegrityError):
                m.publish(td, "b", "IMPLEMENTED_NOT_RUN", False,
                  static_files(), expected=current)

    def test_24_partial_constructor_cleanup_and_signal_before_pointer(self):
        parent = m.import_parent(ROOT, CFG); pcfg = parent_cfg(); made = []
        class PartialDB:
            def __new__(cls): obj = object.__new__(cls); obj.files = {}; return obj
            def __init__(self, *_):
                for part in pcfg["source_contract"]["expected_partition_order"][:5]:
                    leaf = Leaf(part, pcfg["selected_records"]); self.files[part] = leaf; made.append(leaf)
                raise OSError("constructor interrupted")
        controller = parent.DeferredCleanupSignals().enter()
        try:
            with tempfile.TemporaryDirectory() as td, mock.patch.dict(sys.modules, {"famdb_classes": types.SimpleNamespace(FamDB=PartialDB)}), \
                 self.assertRaisesRegex(OSError, "constructor interrupted"):
                m.probe_with_lifecycle(Path(td), CFG, parent, pcfg, controller, Path(td) / "preview", "partial")
            self.assertEqual(sum(x.file.calls for x in made), 5)
        finally:
            if controller.active: controller.restore_for_tests()

    def test_25_before_pointer_bundle_and_fasta_tamper_preserve_old_current(self):
        with tempfile.TemporaryDirectory() as td:
            preview = Path(td); m.publish(preview, "old", "FORMAL_RUNNING", False, running_files())
            old = m.current_bytes(preview)
            def corrupt_metrics(bundle): (bundle / "metrics.json").write_text("tampered\n")
            with self.assertRaises(m.IntegrityError):
                m.publish(preview, "typed", "LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK", True,
                          minimal_files("LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK"), corrupt_metrics)
            self.assertEqual(m.current_bytes(preview), old)

            result = m.materialize_views(rows()); result.update({"observations": [], "close_audit": {}})
            authority = {"source": {}, "slurm": {}, "package_sha256": {}, "gate_sha256": "g",
                         "owner_sha256": "o", "parent_pins": {}}
            files = m.result_files(result, "LEAF_ADAPTER_PREFLIGHT_PASS", authority, authority, "obs", "h")
            parent_hash = rows()[0]["parent_audited_manifest_sha256"]
            def corrupt_fasta(bundle):
                path = bundle / "accession_version_view.fa"; path.write_bytes(path.read_bytes() + b"A\n")
            with self.assertRaises(m.IntegrityError):
                m.publish(preview, "pass", "LEAF_ADAPTER_PREFLIGHT_PASS", True, files, corrupt_fasta,
                          expected_parent_hash=parent_hash)
            self.assertEqual(m.current_bytes(preview), old)

    def test_26_states_symlink_external_and_bundle_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            preview = Path(td) / "preview"; preview.mkdir(); (preview / "states").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(m.IntegrityError):
                m.publish(preview, "x", "IMPLEMENTED_NOT_RUN", False, static_files())
            self.assertFalse((preview / "CURRENT").exists())
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            preview = Path(td); (preview / "states").mkdir(); (Path(outside) / "bundle").mkdir()
            (preview / "states" / "escape").symlink_to(Path(outside) / "bundle", target_is_directory=True)
            (preview / "CURRENT").write_text("states/escape\n")
            with self.assertRaises(m.IntegrityError): m.verify_bundle(preview)

    def test_27_wrapper_does_not_overwrite_same_attempt_specific_terminal(self):
        parent_hash = CFG["parent_contract"]["artifacts"][
          "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256"]
        for status in ("LEAF_ADAPTER_PREFLIGHT_FAILED", "LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as td:
                root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["project_root"] = str(root); cfg["preview_root"] = "preview"
                preview = root / "preview"; m.publish(preview, "slurm-17", status, status != "LEAF_ADAPTER_PREFLIGHT_FAILED",
                                                      minimal_files(status))
                before = m.current_bytes(preview)
                with mock.patch.object(m, "load_config", return_value=cfg), mock.patch.object(m, "query_slurm", return_value={}), \
                     mock.patch.object(m, "import_parent", side_effect=AssertionError("wrapper must stop before parent/H5")), \
                     mock.patch.object(m, "publish_failure", side_effect=AssertionError("must not publish generic failure")), \
                     mock.patch.dict(os.environ, slurm_env(), clear=True):
                    self.assertEqual(m.main(["--config", "x", "--attempt-id", "slurm-17", "--record-wrapper-failure"]), 0)
                self.assertEqual(m.current_bytes(preview), before)
                self.assertTrue(m.wrapper_terminal_already_closed(preview, "slurm-17", parent_hash))

    def test_28_full_mock_formal_pass_and_typed_block_publish_bound_parent_hash(self):
        parent_hash = CFG["parent_contract"]["artifacts"][
          "outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/AUDITED_MANIFEST_11534847.sha256"]
        for typed, expected_status in ((False, "LEAF_ADAPTER_PREFLIGHT_PASS"),
                                       (True, "LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK")):
            with self.subTest(typed=typed), tempfile.TemporaryDirectory() as td:
                root = Path(td); cfg = json.loads(json.dumps(CFG)); cfg["project_root"] = str(root); cfg["preview_root"] = "preview"
                observation = root / "attempt_observations" / "slurm-17" / ("typed" if typed else "pass")
                result = m.materialize_views(rows())
                result.update({"typed_block": typed, "failures": ([{"reason": "synthetic_missing"}] if typed else []),
                               "observations": [], "close_audit": {}, "observation_bundle": observation,
                               "observation_manifest_sha256": "a" * 64})
                if typed: result["records"] = []
                authority = {"source": {"asset": "frozen"}, "slurm": {"JobId": "17"},
                             "package_sha256": {"runner": "1" * 64}, "gate_sha256": "2" * 64,
                             "owner_sha256": "3" * 64,
                             "parent_pins": {"parent_audited_manifest_sha256": parent_hash},
                             "parent_cfg": parent_cfg(), "parent": object()}
                controller = types.SimpleNamespace(pending_rows=lambda: [])
                parent_module = types.SimpleNamespace(
                    DeferredCleanupSignals=lambda: types.SimpleNamespace(enter=lambda: controller))
                calls = []
                def fake_publish(*args, **kwargs):
                    calls.append((args, kwargs))
                    if len(args) > 5 and args[5] is not None: args[5](Path("unused-bundle"))
                    return Path(td) / "published"
                with mock.patch.object(m, "load_config", return_value=cfg), \
                     mock.patch.object(m, "query_slurm", return_value=authority["slurm"]), \
                     mock.patch.object(m, "import_parent", return_value=parent_module), \
                     mock.patch.object(m, "prepare_authority", return_value=authority), \
                     mock.patch.object(m, "revalidate", return_value=authority), \
                     mock.patch.object(m, "probe_with_lifecycle", return_value=result), \
                     mock.patch.object(m, "verify_observation", return_value="a" * 64) as verify_observation, \
                     mock.patch.object(m, "publish", side_effect=fake_publish), \
                     mock.patch.object(m, "publish_failure", side_effect=AssertionError("formal must not fail")), \
                     mock.patch.dict(os.environ, slurm_env(), clear=True):
                    rc = m.main(["--config", "unused", "--attempt-id", "slurm-17"])
                self.assertEqual(rc, 0)
                self.assertEqual(len(calls), 2)
                terminal_args, terminal_kwargs = calls[-1]
                self.assertEqual(terminal_args[2:4], (expected_status, True))
                self.assertEqual(terminal_kwargs["expected_parent_hash"], parent_hash)
                verify_observation.assert_called_once_with(observation, "slurm-17", parent_hash)

    def test_29_formal_parent_hash_scope_binding_drift_precedes_publish(self):
        authority = {"parent_pins": {"parent_audited_manifest_sha256": "0" * 64}}
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(m, "prepare_authority", return_value=authority), \
             mock.patch.object(m, "publish") as publish, \
             self.assertRaisesRegex(m.IntegrityError, "parent observation hash binding drift"):
            m.formal(Path(td), CFG, "slurm-17", object(), scheduler={})
        publish.assert_not_called()

if __name__ == "__main__": unittest.main(verbosity=2)
