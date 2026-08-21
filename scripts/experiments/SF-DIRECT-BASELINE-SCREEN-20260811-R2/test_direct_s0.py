#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec); assert spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module)
    return module


data, task = load("direct_s0_data"), load("direct_s0_task")
cpu_runner, gpu_runner = load("run_cpu_data_stage"), load("run_direct_screen")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rm_line(score: int, chrom: str, start: int, end: int, name: str, cls: str) -> str:
    return f"{score} 0 0 0 {chrom} {start+1} {end} (0) + {name} {cls} 1 {end-start} (0) 1\n"


class TorchMock:
    long = np.int64
    @staticmethod
    def tensor(value, dtype=None): return np.asarray(value, dtype=dtype)


class TokenizerMock:
    def __call__(self, sequence, truncation, max_length, padding):
        assert truncation and padding == "max_length"
        return {"input_ids": [1] + [5] * len(sequence) + [2], "attention_mask": [1] * max_length}


class DirectS0Tests(unittest.TestCase):
    def test_ontology_alias_and_precedence_masks(self):
        with tempfile.TemporaryDirectory() as name:
            onto = Path(name) / "o.txt"
            onto.write_text("LINE_element SO:0000194 LINE,LINE/L1\nlow_complexity SO:0001004 Simple_repeat\n", encoding="utf-8")
            ontology = data.load_ontology(onto)
            self.assertEqual(data.classify_annotation("LINE/L1", ontology, {"low_complexity"})[:2], ("P", 2))
            self.assertEqual(data.classify_annotation("Simple_repeat", ontology, {"low_complexity"})[:2], ("hardN", 0))
            anns = [data.Annotation(0, 4, "U", -100, "", 1, "UNRESOLVED", "UNRESOLVED", "UNRESOLVED"),
                    data.Annotation(1, 3, "hardN", 0, "", 2, "low_complexity", "SO:0001004", "EXACT_ALIAS"),
                    data.Annotation(2, 3, "P", 2, "L1", 3, "LINE_element", "SO:0000194", "EXACT_ALIAS")]
            painted = data.paint_window("ACGN", 0, 4, anns, [(0, 4)])
            self.assertEqual(painted["states"], ["U", "hardN", "P", "U"])
            self.assertEqual(painted["labels"], [-100, 0, 2, -100])
            self.assertEqual(painted["counts"]["label_b_only_masked_bp"], 2)

    def test_tokenizer_padding_and_u_ignore(self):
        rec = {"sequence": "ACGT", "labels": [0, -100, 2, 0]}
        encoded = task.encode_record(rec, TokenizerMock(), 4, TorchMock)
        self.assertEqual(encoded["labels"].tolist(), [-100, 0, -100, 2, 0, -100])
        y, pred, states = np.array([0, 0]), np.array([1, 0]), np.array([task.STATE2ID["hardN"], task.STATE2ID["RN"]])
        metric = task.score_arrays(y, pred, states=states)
        self.assertEqual(metric["hardN_te_fpr"], 1.0)
        self.assertEqual(metric["RN_te_fpr"], 0.0)

    def test_rejoin_9000_duplicate_and_missing(self):
        expected = {"train": 5400, "val": 1440, "test": 2160}
        rows = []
        index = 0
        for split, count in expected.items():
            for _ in range(count):
                rows.append({"historical_split": split, "species_code": "fit", "chr": "chr1", "start": str(index),
                             "end": str(index + 1), "historical_sequence_sha256": f"{index:064x}", "rejoin_status": "EXACT"})
                index += 1
        result = data.validate_rejoin_rows(rows, expected)
        self.assertEqual(result["unique_keys"], 9000)
        with self.assertRaises(ValueError): data.validate_rejoin_rows(rows + [rows[0]], expected)
        with self.assertRaises(ValueError): data.validate_rejoin_rows(rows[:-1], expected)

    def test_pinned_chunk_manifest_bounded_wide_fields_and_real_contract(self):
        original_limit = csv.field_size_limit()
        try:
            csv.field_size_limit(777_777)
            with tempfile.TemporaryDirectory() as name:
                valid = Path(name) / "valid.tsv"
                valid.write_text("key\twide\nrow\t" + "A" * 1_300_000 + "\n", encoding="utf-8")
                rows = data.read_pinned_chunk_manifest(valid, enforce_source_contract=False)
                self.assertEqual(len(rows[0]["wide"]), 1_300_000)
                self.assertEqual(csv.field_size_limit(), 777_777)
                oversized = Path(name) / "oversized.tsv"
                oversized.write_text("key\twide\nrow\t" + "A" * 2_000_001 + "\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "2000000 character field limit"):
                    data.read_pinned_chunk_manifest(oversized, enforce_source_contract=False)
                self.assertEqual(csv.field_size_limit(), 777_777)
            pinned = PROJECT / "software_outputs/repeatmasker_dfam/raw_runs/self_labelA/RMDFAM_FULLPARTITIONS_RERUN_20260617/chunk_manifest.tsv"
            self.assertEqual(digest(pinned), "63554cacefeddf3950259c7af3fa183504f3e43e8f5b24cd5d1149daa1fe8600")
            real_rows = data.read_pinned_chunk_manifest(pinned)
            self.assertEqual(len(real_rows), 495)
            self.assertEqual(tuple(real_rows[0]), data.PINNED_CHUNK_COLUMNS)
            self.assertGreater(max(len(value) for row in real_rows for value in row.values()), 1_000_000)
            self.assertEqual(csv.field_size_limit(), 777_777)
        finally:
            csv.field_size_limit(original_limit)

    def test_attempt_staging_refuses_dirty_paths(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            _stage, _final = cpu_runner.create_stage(root, "data", "x")
            with self.assertRaises(FileExistsError): cpu_runner.create_stage(root, "data", "x")
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            _stage, _final = gpu_runner.create_stage(root, "x")
            with self.assertRaises(FileExistsError): gpu_runner.create_stage(root, "x")

    def test_family_label_conflict_is_typed_block(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            onto = root / "onto.txt"
            onto.write_text("LINE_element SO:0000194 LINE,LINE/L1\nDNA_transposon SO:0000182 DNA,DNA/hAT\n")
            (root / "a.out").write_text(rm_line(10, "chr1", 0, 4, "SAME", "LINE/L1"))
            (root / "b.out").write_text(rm_line(10, "chr1", 0, 4, "SAME", "DNA/hAT"))
            rows = [{"self_out": "a.out", "role": "train_core"}, {"self_out": "b.out", "role": "mammal_holdout"}]
            with self.assertRaisesRegex(data.DataContractTypedBlock, "FAMILY_COMPONENT_LABEL_CONFLICT"):
                data.assign_family_components(rows, root, {"label_state_policy": {"hard_negative_terms": []}}, data.load_ontology(onto), True)

    def test_homology_component_label_conflict_is_typed_block(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); onto = root / "onto.txt"
            onto.write_text("LINE_element SO:0000194 LINE,LINE/L1\nDNA_transposon SO:0000182 DNA,DNA/hAT\n")
            (root / "a.out").write_text(rm_line(10, "chr1", 0, 4, "F1", "LINE/L1"))
            (root / "b.out").write_text(rm_line(10, "chr1", 0, 4, "F2", "DNA/hAT"))
            cfg = {"label_state_policy": {"hard_negative_terms": []},
                   "synthetic_dfam_identities": {"F1": {"accession": "DFX.1", "consensus_sha256": "a" * 64},
                                                 "F2": {"accession": "DFX.1", "consensus_sha256": "a" * 64}}}
            rows = [{"self_out": "a.out", "role": "train_core"}, {"self_out": "b.out", "role": "train_core"}]
            with self.assertRaisesRegex(data.DataContractTypedBlock, "HOMOLOGY_COMPONENT_LABEL_CONFLICT"):
                data.assign_family_components(rows, root, cfg, data.load_ontology(onto), True)

    def test_gpu_consumed_asset_tamper_fails(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root / "base").mkdir(); (root / "head").mkdir()
            (root / "base/config.json").write_text("base"); (root / "head/config.json").write_text("head")
            contract = {"base_checkpoint_files": {"config.json": digest(root / "base/config.json")},
                        "historical_head_files": {"config.json": digest(root / "head/config.json")}}
            (root / "assets.json").write_text(json.dumps(contract))
            cfg = {"asset_contract": "assets.json", "asset_contract_sha256": digest(root / "assets.json"),
                   "base_checkpoint": "base", "historical_head": "head"}
            self.assertEqual(len(gpu_runner.verify_consumed_model_assets(root, cfg)), 2)
            (root / "head/config.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "asset drift"):
                gpu_runner.verify_consumed_model_assets(root, cfg)

    def test_payload_manifest_schema_and_tamper(self):
        with tempfile.TemporaryDirectory() as name:
            stage = Path(name)
            required = ["metrics.json", "report.json", "RUN_MANIFEST.json", "runtime_environment.json", "external_environment_manifest.txt",
                        "gpu_smoke.json",
                        "clean_direct_head/training_meta.json", "clean_direct_head/calibration.json",
                        "clean_direct_head/best_model/config.json", "clean_direct_head/best_model/pytorch_model.bin"]
            for relpath in required:
                path = stage / relpath; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(relpath)
            manifest = gpu_runner.create_payload_manifest(stage)
            self.assertFalse(manifest["self_included"])
            self.assertNotIn("PAYLOAD_MANIFEST.json", manifest["files"])
            self.assertEqual(len(gpu_runner.verify_payload_manifest(stage)), 64)
            (stage / "metrics.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "artifact drift"):
                gpu_runner.verify_payload_manifest(stage)

    def test_published_manifest_schema_and_tamper(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); final = root / "attempts/gpu-x"; final.mkdir(parents=True)
            (final / "PAYLOAD_MANIFEST.json").write_text("payload")
            cfg = {"output_root": "outputs/exp", "report_path": "reports/exp.json"}
            gpu_runner.publish_top_level(root, cfg, final, digest(final / "PAYLOAD_MANIFEST.json"), {"x": 1}, {"y": 2})
            self.assertEqual(gpu_runner.verify_published_manifest(root, cfg)["schema_version"], "TEFM-SF-DIRECT-PUBLISHED-1.0.0")
            (root / "reports/exp.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "publication verification failed"):
                gpu_runner.verify_published_manifest(root, cfg)

    def test_canonical_output_manifest_terminal_transitions(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); out = root / "outputs/X"; out.mkdir(parents=True)
            cfg = {"project_root": str(root), "exp_id": "X", "profile": "screen", "output_root": "outputs/X",
                   "data_pass_pointer": "outputs/X/DATA_PASS_MANIFEST.json", "report_path": "reports/X.json"}
            static = {"schema_version": "STATIC", "package_hashes": {"x": "y"}}
            gpu_runner.atomic_json(out / "code_review_gate.json", {"verdict": "BLOCKED"})
            gpu_runner.atomic_json(out / "input_manifest.json", static)
            gpu_runner.write_static_not_run(root, cfg, static)
            static_entries = gpu_runner.verify_canonical_output_manifest(root, cfg)
            static_status_sha = static_entries["outputs/X/STATUS"]
            static_metrics_sha = static_entries["outputs/X/metrics.json"]

            gpu_runner.atomic_json(out / "DATA_PASS_MANIFEST.json", {"status": "PASS"})
            ready = gpu_runner.finalize_terminal_state(root, cfg, "DATA_READY", "data-1")
            self.assertIn("outputs/X/DATA_PASS_MANIFEST.json", ready)
            self.assertNotIn(static_status_sha, ready.values())
            self.assertNotIn(static_metrics_sha, ready.values())
            ready_pointer_sha = ready["outputs/X/DATA_PASS_MANIFEST.json"]
            ready_status_sha = ready["outputs/X/STATUS"]
            typed = out / "attempts/data-2.tmp/typed_block.json"; typed.parent.mkdir(parents=True)
            typed.write_text('{"status":"DATA_TYPED_BLOCK"}\n', encoding="utf-8")
            failed = typed.parent / "failure.json"; failed.write_text('{"error":"unresolved"}\n', encoding="utf-8")
            blocked = gpu_runner.finalize_terminal_state(root, cfg, "DATA_TYPED_BLOCK", "data-2", (typed, failed), "unresolved")
            self.assertNotIn("outputs/X/DATA_PASS_MANIFEST.json", blocked)
            self.assertNotIn(ready_pointer_sha, blocked.values())
            self.assertNotIn(ready_status_sha, blocked.values())

            gpu_runner.atomic_json(out / "input_manifest.json", static)
            gpu_runner.write_static_not_run(root, cfg, static)
            gpu_runner.atomic_json(out / "metrics.json", {"status": "COMPLETED", "primary_metric": 0.9})
            completed_metrics_sha = digest(out / "metrics.json")
            gpu_runner.atomic_json(out / "PUBLISHED_MANIFEST.json", {"status": "PUBLISHED"})
            report = root / "reports/X.json"; report.parent.mkdir(parents=True); report.write_text('{"result":1}\n', encoding="utf-8")
            completed = gpu_runner.finalize_terminal_state(root, cfg, "COMPLETED", "gpu-1")
            self.assertIn("outputs/X/PUBLISHED_MANIFEST.json", completed)
            self.assertIn("reports/X.json", completed)
            self.assertFalse(any(Path(path).is_absolute() for path in completed))
            completed_published_sha = completed["outputs/X/PUBLISHED_MANIFEST.json"]
            failure = out / "attempts/gpu-2.tmp/failure.json"; failure.parent.mkdir(parents=True)
            failure.write_text('{"error":"boom"}\n', encoding="utf-8")
            terminal_failure = gpu_runner.finalize_terminal_state(root, cfg, "FAILED", "gpu-2", (failure,), "boom")
            self.assertNotIn("outputs/X/PUBLISHED_MANIFEST.json", terminal_failure)
            self.assertNotIn("reports/X.json", terminal_failure)
            self.assertNotIn(completed_published_sha, terminal_failure.values())
            self.assertNotIn(completed_metrics_sha, terminal_failure.values())
            self.assertEqual(json.loads((out / "TERMINAL_STATE.json").read_text())["unlisted_artifacts_are_superseded"], True)

    def test_conda_activation_with_unset_mkl_and_delayed_nounset(self):
        for conda_env in ("te_benchmark", "generanno"):
            command = ("unset MKL_INTERFACE_LAYER; set -eo pipefail; "
                       "source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh; "
                       f"conda activate {conda_env}; set -u; test -n \"${{CONDA_DEFAULT_ENV}}\"")
            result = subprocess.run(["bash", "-c", command], env={k: v for k, v in os.environ.items() if k != "MKL_INTERFACE_LAYER"},
                                    text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_sbatch_preflight_log_contract_and_shared_owner_lock(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            cfg = {"project_root": str(root), "exp_id": "X", "output_root": "outputs/X",
                   "data_pass_pointer": "outputs/X/DATA_PASS_MANIFEST.json"}
            config = root / "config.json"; config.write_text(json.dumps(cfg), encoding="utf-8")
            command = [sys.executable, str(HERE / "preflight_sbatch.py"), "--config", str(config), "--stage", "cpu"]
            passed = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertTrue((root / "logs/X").is_dir())
            lock = root / "outputs/X/.stage_owner.lock"; lock.mkdir(parents=True)
            blocked = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("owner lock", blocked.stderr)

    def test_audit_never_changes_numeric_gate_and_report_schema(self):
        with tempfile.TemporaryDirectory() as name:
            root, stage, dat = Path(name), Path(name) / "gpu", Path(name) / "data_attempt"
            stage.mkdir(); (stage / "clean_direct_head").mkdir(); (dat / "data").mkdir(parents=True)
            cfg = {"project_root": str(PROJECT), "exp_id": "SF-DIRECT-BASELINE-SCREEN-20260811-R2", "profile": "screen",
                   "base_checkpoint": "BASE", "canonical_split_sha256": "c", "ontology_sha256": "o",
                   "acceptance": {"main4_conditional_macro_f1": .8, "te_detect_f1": .85, "unknown_recall": .3,
                                  "main4_false_unknown_rate_max": .02, "eligible_main4_coverage": .7,
                                  "minimum_clade_main4_macro_f1": .6, "homology_component_overlap_count_max": 0,
                                  "primary_clade_overlap_count_max": 0}}
            primary = {"main4_conditional_macro_f1": .9, "te_detect_f1": .9, "unknown_recall": .4, "main4_false_unknown_rate": .01,
                       "minimum_clade_main4_macro_f1": .7, "test_calibration_count": 0, "hierarchical_path_distance": 1.0,
                       "overconfident_leaf_error": .1, "RN_te_fpr": .01, "hardN_te_fpr": .02, "partition": "test_primary",
                       "per_clade": {}, "per_species_secondary": {}}
            terrible_audit = {**primary, "main4_conditional_macro_f1": 0.0, "partition": "audit_optional_stress"}
            for filename, value in (("clean_primary_metrics.json", primary), ("historical_primary_metrics.json", primary),
                                    ("clean_audit_metrics.json", terrible_audit), ("historical_audit_metrics.json", terrible_audit),
                                    ("gpu_smoke.json", {"pass": True})):
                (stage / filename).write_text(json.dumps(value), encoding="utf-8")
            config_sha, data_sha = "config", "data"
            (stage / "clean_direct_head/training_meta.json").write_text(json.dumps({"initialization": "BASE", "historical_head_used_for_initialization": False,
                "initialization_asset_contract_sha256": "asset", "data_pass_manifest_sha256": data_sha, "config_sha256": config_sha}), encoding="utf-8")
            cfg["asset_contract_sha256"] = "asset"
            (dat / "leakage_audit.json").write_text(json.dumps({"homology_component_overlap_count": 0, "primary_clade_overlap_count": 0}), encoding="utf-8")
            (dat / "data/metadata.json").write_text(json.dumps({"eligible_main4_coverage": .9}), encoding="utf-8")
            metrics, report = gpu_runner.aggregate(cfg, dat, data_sha, stage, config_sha)
            self.assertTrue(metrics["s0_numeric_gate_pass"])
            self.assertFalse(metrics["audit_in_numeric_gate"])
            self.assertFalse(metrics["hierarchical_stage_authorized"])
            self.assertEqual(set(("exp_id", "profile", "primary_metric", "metrics", "dataset", "evaluator", "semantic_success", "claim_eligible")) - set(report), set())

    def test_full_synthetic_build_physical_isolation_coverage_and_schema(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); exp = root / "exp"; exp.mkdir()
            ontology = root / "ontology.txt"
            ontology.write_text("SINE_element SO:0000206 SINE,SINE/Alu\nLINE_element SO:0000194 LINE,LINE/L1\n"
                                "LTR_retrotransposon SO:0000186 LTR,LTR/ERV\nDNA_transposon SO:0000182 DNA,DNA/hAT\n"
                                "low_complexity SO:0001004 Simple_repeat\nrepeat_fragment SO:0001050 Unknown\n", encoding="utf-8")
            salt = "salt"
            train_f = next(f"TR{i}" for i in range(999) if data.stable_score(salt, f"TR{i}") % 100 >= 50)
            val_f = next(f"VA{i}" for i in range(999) if data.stable_score(salt, f"VA{i}") % 100 < 50)
            species = [("fit", "Fit species", "1", "10", "FitOrder", "train_core", "fit_only"),
                       ("primary", "Primary species", "2", "20", "PrimaryOrder", "mammal_holdout", "primary_test"),
                       ("audit", "Audit species", "3", "30", "AuditOrder", "optional_stress", "audit_only")]
            manifest_rows, provenance_rows = [], []
            for code, scientific, taxid, order_taxid, order_name, role, partition in species:
                seq = "A" * 36000 if code == "fit" else "AAAAAAANAAA" if code == "primary" else "A" * 8
                (root / f"{code}.fa").write_text(f">chr1\n{seq}\n", encoding="utf-8")
                if code == "fit":
                    rm = rm_line(100, "chr1", 0, 2, train_f, "LINE/L1") + rm_line(100, "chr1", 2, 4, val_f, "DNA/hAT")
                    rm += rm_line(100, "chr1", 4, 8, train_f, "LINE/L1") + rm_line(100, "chr1", 8, 12, val_f, "DNA/hAT")
                elif code == "primary":
                    rm = (rm_line(100, "chr1", 0, 4, "HELD", "LTR/ERV") +
                          rm_line(100, "chr1", 4, 7, "HELD2", "SINE/Alu") +
                          rm_line(100, "chr1", 8, 11, "HELD3", "DNA/hAT"))
                else: rm = rm_line(100, "chr1", 0, 4, "AUD", "LINE/L1")
                (root / f"{code}.out").write_text(rm, encoding="utf-8")
                (root / f"{code}.bed").write_text("chr1\t0\t1\n", encoding="utf-8")
                manifest_rows.append(f"{code}\t{role}\t{code}.fa\t{code}.out\t{code}.bed\n")
            manifest = root / "manifest.tsv"; manifest.write_text("species_code\trole\tgenome\tself_out\tcomparator_plus_unknown\n" + "".join(manifest_rows), encoding="utf-8")
            provenance = root / "provenance.tsv"; provenance.write_text("rewritten_manifest_path_value\tfrozen_copy_project_relpath\tfrozen_copy_sha256\tstatus\n", encoding="utf-8")
            report = root / "snapshot.json"; report.write_text(json.dumps({"s0_input_contract_ready": True, "failure_codes": []}), encoding="utf-8")
            frozen = root / "species.tsv"; frozen.write_text("species_code\tscientific_name\ttaxid\torder_taxid\torder_name\trole\tevaluation_partition\n" +
                "".join("\t".join(x) + "\n" for x in species), encoding="utf-8")
            source = root / "source.tsv"; source.write_text("species_code\tscientific_name\ttaxid\n" +
                "".join(f"{x[0]}\t{x[1]}\t{x[2]}\n" for x in species), encoding="utf-8")
            readme = root / "README"; readme.write_text("Dfam 3.9\n", encoding="utf-8")
            chunk_rows = []
            for code, *_ in species:
                outdir = root / f"chunk_{code}"; outdir.mkdir(); (outdir / "RUN_METADATA.txt").write_text("RepeatMasker version 4.2.2\nsource_libdir=rm_lib_overlay\n")
                chunk_rows.append(f"{code}\t{outdir}\n")
            chunks = root / "chunks.tsv"; chunks.write_text("species_code\toutput_dir\n" + "".join(chunk_rows), encoding="utf-8")
            base, hist_head = root / "base", root / "head"; base.mkdir(); hist_head.mkdir()
            base_names = {"config.json", "model.safetensors", "configuration_generanno.py", "modeling_generanno.py",
                          "tokenizer.py", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"}
            head_names = {"config.json", "pytorch_model.bin", "configuration_generanno.py", "modeling_generanno.py",
                          "tokenizer.py", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"}
            for filename in base_names: (base / filename).write_text(filename)
            for filename in head_names: (hist_head / filename).write_text(filename)
            (base / "config.json").write_text(json.dumps({"model_type": "generanno", "auto_map": {"AutoModelForTokenClassification": "x"}}))
            (hist_head / "config.json").write_text(json.dumps({"architectures": ["GenerannoForTokenClassification"],
                "id2label": {str(k): v for k, v in data.ID2LABEL.items()}}))
            historical = root / "historical"; cursor = 0; hist_specs = {}
            for split, count in (("train", 5400), ("val", 1440), ("test", 2160)):
                p = historical / split / "data.jsonl.gz"; p.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(p, "wt", encoding="utf-8") as handle:
                    for _ in range(count):
                        handle.write(json.dumps({"species_code": "fit", "chr": "chr1", "start": cursor, "end": cursor + 4,
                                                 "sequence": "AAAA", "labels": [0, 0, 0, 0]}) + "\n"); cursor += 4
                hist_specs[f"{split}/data.jsonl.gz"] = {"sha256": digest(p), "records": count}
            for filename in ("metadata.json", "label_map.json"):
                p = historical / filename; p.write_text("{}") ; hist_specs[filename] = {"sha256": digest(p)}
            assets = root / "assets.json"; assets.write_text(json.dumps({"base_checkpoint_files": {x: digest(base/x) for x in base_names},
                "historical_head_files": {x: digest(hist_head/x) for x in head_names}, "historical_data_files": hist_specs,
                "historical_expected_total_records": 9000, "repeatmasker_version": "RepeatMasker version 4.2.2", "dfam_release": "Dfam 3.9"}), encoding="utf-8")
            cfg = {"project_root": str(root), "canonical_split_manifest": "manifest.tsv", "canonical_split_sha256": digest(manifest),
                "canonical_snapshot_report": "snapshot.json", "canonical_snapshot_report_sha256": digest(report),
                "canonical_snapshot_provenance": "provenance.tsv", "canonical_snapshot_provenance_sha256": digest(provenance),
                "ontology": "ontology.txt", "ontology_sha256": digest(ontology), "asset_contract": "assets.json", "asset_contract_sha256": digest(assets),
                "species_holdout_manifest": "species.tsv", "species_holdout_manifest_sha256": digest(frozen),
                "source_species_manifest": "source.tsv", "source_species_manifest_sha256": digest(source),
                "source_chunk_manifest": "chunks.tsv", "source_chunk_manifest_sha256": digest(chunks),
                "source_run_readme": "README", "source_run_readme_sha256": digest(readme), "base_checkpoint": "base",
                "historical_head": "head", "historical_data_dir": "historical", "window": 4, "max_n_fraction": .2, "seed": 42,
                "homology_component_policy": {"test_if_observed_in_roles": ["mammal_holdout", "optional_stress"], "validation_hash_percent": 50, "salt": salt},
                "holdout_policy": {"fit_role": "train_core", "primary_test_roles": ["mammal_holdout"], "audit_only_roles": ["optional_stress"]},
                "label_state_policy": {"hard_negative_terms": ["low_complexity"]},
                "candidate_window_caps_per_species": {"train_core": 20, "mammal_holdout": 20, "optional_stress": 20}}
            cfg["synthetic_dfam_identities"] = {x: {"accession": x, "consensus_sha256": hashlib.sha256(x.encode()).hexdigest()}
                                                for x in (train_f, val_f, "HELD", "HELD2", "HELD3", "AUD")}
            config = root / "config.json"; config.write_text(json.dumps(cfg))
            attempt = root / "attempt"; attempt.mkdir()
            meta = data.build(config, attempt, verify_target_hashes=False)
            audit_result = data.verify(config, attempt, attempt / "leakage.json")
            self.assertTrue(audit_result["pass"]); self.assertTrue(audit_result["audit_physically_separate"])
            self.assertEqual(audit_result["homology_component_overlap_count"], 0)
            self.assertEqual(audit_result["primary_clade_overlap_count"], 0)
            self.assertEqual(audit_result["historical_rejoin"]["unique_keys"], 9000)
            self.assertGreater(meta["counts"].get("decision_CROSS_SPLIT_MIXED", 0), 0)
            self.assertGreater(meta["counts"].get("decision_EXCESS_N", 0), 0)
            self.assertGreater(meta["counts"].get("decision_SHORT_WINDOW", 0), 0)
            self.assertAlmostEqual(meta["eligible_main4_coverage"], 4 / 10)
            with gzip.open(attempt / "data/audit_optional_stress/data.jsonl.gz", "rt") as h: self.assertGreater(sum(1 for _ in h), 0)
            with gzip.open(attempt / "data/test_primary/data.jsonl.gz", "rt") as h:
                rows = [json.loads(x) for x in h]
            self.assertTrue(all(x["evaluation_partition"] == "primary_test" for x in rows))
            self.assertTrue(all(x["clade_id"] == "20" for x in rows))


if __name__ == "__main__": unittest.main()
