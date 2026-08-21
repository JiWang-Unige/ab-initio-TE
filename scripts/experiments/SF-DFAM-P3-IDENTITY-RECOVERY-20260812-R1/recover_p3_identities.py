#!/usr/bin/env python3
"""Recover frozen missing RM identifiers by exhaustive exact-name scan of Dfam p3."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: Iterable[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    os.replace(temporary, path)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); assert spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module)
    return module


def verify_pin(root: Path, cfg: dict, path_key: str, hash_key: str) -> Path:
    path = root / cfg[path_key]
    if not path.is_file() or sha256_file(path) != cfg[hash_key]:
        raise ValueError(f"PINNED_INPUT_DRIFT:{path_key}")
    return path


def decode_attr(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def validate_inputs(root: Path, cfg: dict) -> tuple[list[dict], dict]:
    for path_key, hash_key in (
        ("identity_config", "identity_config_sha256"),
        ("identity_evaluator", "identity_evaluator_sha256"),
        ("identity_layout_manifest", "identity_layout_manifest_sha256"),
        ("identity_payload", "identity_payload_sha256"),
        ("identity_identifier_audit", "identity_identifier_audit_sha256"),
        ("evaluator_contract", "evaluator_contract_sha256"),
        ("famdb_rmlib_config", "famdb_rmlib_config_sha256"),
    ):
        verify_pin(root, cfg, path_key, hash_key)
    payload_path = root / cfg["identity_payload"]
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    if payload.get("self_included") is not False:
        raise ValueError("IDENTITY_PAYLOAD_SCHEMA")
    for relpath, expected in payload.get("files", {}).items():
        if sha256_file(payload_path.parent / relpath) != expected:
            raise ValueError(f"IDENTITY_PAYLOAD_DRIFT:{relpath}")
    identity_cfg = json.loads((root / cfg["identity_config"]).read_text(encoding="utf-8"))
    identity = load_module("p3_recovery_identity_contract", root / cfg["identity_evaluator"])
    layout, summary = identity.validate_dfam_index_layout(root, identity_cfg)
    p3 = [item for item in layout["partitions"] if int(item["partition"]) == int(cfg["famdb_partition"])]
    if len(p3) != 1 or p3[0]["lookup_by_name"] is not False:
        raise ValueError("P3_EXPECTED_EXPLICIT_BYNAME_ABSENCE")
    partition_path = root / cfg["famdb_partition_path"]
    if partition_path.stat().st_size != int(cfg["famdb_partition_size_bytes"]):
        raise ValueError("P3_SIZE_DRIFT")
    rows = read_tsv(root / cfg["identity_identifier_audit"])
    targets = [row for row in rows if row["resolution_status"] == cfg["target_resolution_status"]]
    excluded = set(cfg["excluded_existing_ambiguity_identifiers"])
    if any(row["identifier"] in excluded for row in targets):
        raise ValueError("EXISTING_AMBIGUITY_ENTERED_MISSING_TARGETS")
    if len(targets) != int(cfg["expected_target_identifier_count"]) or len({x["identifier"] for x in targets}) != len(targets):
        raise ValueError(f"FROZEN_TARGET_COUNT_MISMATCH:{len(targets)}")
    occurrence_mass = sum(int(row["occurrences"]) for row in targets)
    if occurrence_mass <= 0:
        raise ValueError("FROZEN_TARGET_OCCURRENCE_MASS_EMPTY")
    ambiguity = [row for row in rows if row["identifier"] in set(cfg["audit_ambiguity_identifiers"])]
    if len(ambiguity) != len(cfg["audit_ambiguity_identifiers"]) or any(row["resolution_status"] != "ambiguous" for row in ambiguity):
        raise ValueError("FROZEN_AMBIGUITY_AUDIT_DRIFT")
    audit = {"target_identifier_count": len(targets), "target_occurrence_mass": occurrence_mass,
             "existing_ambiguity_audit_identifier_count": len(ambiguity),
             "existing_ambiguity_audit_occurrence_mass": sum(int(row["occurrences"]) for row in ambiguity),
             "partition": 3, "partition_size_bytes": partition_path.stat().st_size,
             "layout_manifest_sha256": summary["layout_manifest_sha256"],
             "rmlib_config_sha256": cfg["famdb_rmlib_config_sha256"],
             "full_partition_content_hashing_used": False,
             "prefix_guess_used": False, "casefold_used": False, "copy_derived_proxy_used": False,
             "clustering_run": False, "split_built": False, "model_run": False}
    return targets, audit


def iter_family_datasets(families_group):
    import h5py
    stack = [families_group]
    while stack:
        group = stack.pop()
        for key in sorted(group.keys(), reverse=True):
            item = group[key]
            if isinstance(item, h5py.Dataset):
                yield item
            elif isinstance(item, h5py.Group):
                stack.append(item)
            else:
                raise ValueError(f"P3_FAMILY_OBJECT_WRONG_TYPE:{item.name}")


def scan_partition(partition_path: Path, target_names: set[str], expected_dataset_count: int | None = None,
                   expected_consensus_count: int | None = None, expected_model_count: int | None = None,
                   progress_interval: int = 10000, progress_path: Path | None = None) -> tuple[list[dict], dict]:
    """Exhaustively scan canonical Families datasets; no ByName/API/fuzzy fallback."""
    import h5py
    candidates, scanned, attribute_counts = [], 0, Counter()
    if progress_interval <= 0:
        raise ValueError("INVALID_PROGRESS_INTERVAL")
    progress_handle = None
    if progress_path is not None:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_handle = progress_path.open("w", encoding="utf-8")
    try:
        with h5py.File(partition_path, "r") as handle:
            if "Lookup/ByName" in handle:
                raise ValueError("P3_LAYOUT_DRIFT_BYNAME_PRESENT")
            families = handle.get("Families")
            if not isinstance(families, h5py.Group):
                raise ValueError("P3_FAMILIES_GROUP_MISSING")
            for dataset in iter_family_datasets(families):
                scanned += 1
                for field in ("accession", "name", "version", "consensus", "model"):
                    attribute_counts[field] += int(field in dataset.attrs)
                if progress_handle is not None and scanned % progress_interval == 0:
                    progress_handle.write(json.dumps({"event": "p3_family_scan_progress", "datasets_scanned": scanned,
                                                       "exact_candidate_rows": len(candidates)}, sort_keys=True) + "\n")
                    progress_handle.flush(); os.fsync(progress_handle.fileno())
                name = decode_attr(dataset.attrs.get("name"))
                if name not in target_names:
                    continue
                accession = decode_attr(dataset.attrs.get("accession"))
                version_raw = dataset.attrs.get("version")
                version = int(version_raw) if version_raw is not None else None
                consensus = decode_attr(dataset.attrs.get("consensus")).upper().replace("U", "T")
                candidates.append({"identifier": name, "accession": accession, "version": version,
                                   "versioned_accession": f"{accession}.{version}" if accession and version is not None else "",
                                   "consensus_sha256": sha256_text(consensus) if consensus else "",
                                   "consensus_length": len(consensus), "h5_dataset_path": dataset.name,
                                   "source_partition": 3})
        if progress_handle is not None:
            progress_handle.write(json.dumps({"event": "p3_family_scan_complete", "datasets_scanned": scanned,
                                               "exact_candidate_rows": len(candidates)}, sort_keys=True) + "\n")
    finally:
        if progress_handle is not None:
            progress_handle.close()
    if expected_dataset_count is not None and scanned != expected_dataset_count:
        raise ValueError(f"P3_FAMILY_DATASET_COUNT_DRIFT:{scanned}:{expected_dataset_count}")
    if expected_consensus_count is not None and attribute_counts["consensus"] != expected_consensus_count:
        raise ValueError(f"P3_CONSENSUS_ATTRIBUTE_COUNT_DRIFT:{attribute_counts['consensus']}:{expected_consensus_count}")
    if expected_model_count is not None and attribute_counts["model"] != expected_model_count:
        raise ValueError(f"P3_MODEL_ATTRIBUTE_COUNT_DRIFT:{attribute_counts['model']}:{expected_model_count}")
    return sorted(candidates, key=lambda x: (x["identifier"], x["versioned_accession"], x["h5_dataset_path"])), {
        "family_datasets_scanned": scanned, "exact_candidate_rows": len(candidates),
        "target_names_requested": len(target_names), "match_semantics": "case_sensitive_exact_name_attr",
        "attribute_presence_counts": dict(sorted(attribute_counts.items())),
        "consensus_attribute_count": attribute_counts["consensus"], "model_attribute_count": attribute_counts["model"]}


def resolve_targets(targets: list[dict], candidates: list[dict]) -> tuple[list[dict], dict]:
    by_name = defaultdict(list)
    for candidate in candidates:
        by_name[candidate["identifier"]].append(candidate)
    results, counts, mass = [], Counter(), Counter()
    for target in sorted(targets, key=lambda x: x["identifier"]):
        identifier, occurrences = target["identifier"], int(target["occurrences"])
        items = by_name.get(identifier, [])
        valid = [x for x in items if x["versioned_accession"] and x["consensus_sha256"] and x["consensus_length"] > 0]
        unique = {(x["versioned_accession"], x["consensus_sha256"]): x for x in valid}
        if not items:
            status, detail = "missing", "no exact name attribute match"
        elif len(valid) != len(items):
            status, detail = "invalid_metadata", "exact candidate lacks accession/version/consensus"
        elif len(unique) != 1:
            status, detail = "ambiguous", f"{len(unique)} distinct accession/consensus identities"
        else:
            status, detail = "recovered", ""
        counts[status] += 1; mass[status] += occurrences
        chosen = next(iter(unique.values())) if status == "recovered" else {}
        results.append({"identifier": identifier, "occurrences": occurrences, "labels": target["labels"],
                        "species": target["species"], "status": status, "candidate_row_count": len(items),
                        "distinct_identity_count": len(unique), "versioned_accession": chosen.get("versioned_accession", ""),
                        "consensus_sha256": chosen.get("consensus_sha256", ""),
                        "consensus_length": chosen.get("consensus_length", ""), "detail": detail})
    target_mass = sum(int(x["occurrences"]) for x in targets)
    if sum(counts.values()) != len(targets) or sum(mass.values()) != target_mass:
        raise ValueError("TARGET_RECOVERY_CONSERVATION_FAILED")
    metrics = {f"{status}_identifier_count": counts[status] for status in ("recovered", "missing", "ambiguous", "invalid_metadata")}
    metrics.update({f"{status}_occurrence_mass": mass[status] for status in ("recovered", "missing", "ambiguous", "invalid_metadata")})
    metrics.update({"target_identifier_count": len(targets), "target_occurrence_mass": target_mass,
                    "identifier_conservation_delta": sum(counts.values()) - len(targets),
                    "occurrence_mass_conservation_delta": sum(mass.values()) - target_mass,
                    "recovered_identifier_coverage": counts["recovered"] / len(targets),
                    "recovered_occurrence_coverage": mass["recovered"] / target_mass})
    return results, metrics


def package_hashes(root: Path, exp_id: str) -> dict[str, str]:
    paths = [root / "configs" / f"{exp_id}.yaml", root / "scripts/experiments" / exp_id / "recover_p3_identities.py",
             root / "scripts/experiments" / exp_id / "test_recover_p3_identities.py", root / "sbatch" / f"{exp_id}.sbatch"]
    return {str(path.relative_to(root)): sha256_file(path) for path in paths}


def create_payload_manifest(stage: Path) -> str:
    files = {str(path.relative_to(stage)): sha256_file(path) for path in sorted(stage.rglob("*"))
             if path.is_file() and path.name != "PAYLOAD_MANIFEST.json"}
    required = {"frozen_targets.tsv", "existing_ambiguity_audit.tsv", "exact_candidates.tsv", "resolution.tsv",
                "scan_progress.jsonl", "metrics.json", "report.json", "RUN_MANIFEST.json", "env.json"}
    if required - set(files):
        raise ValueError(f"RECOVERY_PAYLOAD_MISSING:{sorted(required-set(files))}")
    atomic_json(stage / "PAYLOAD_MANIFEST.json", {"schema_version": "SF-P3-RECOVERY-PAYLOAD-1.0.0",
                "self_included": False, "files": files})
    return sha256_file(stage / "PAYLOAD_MANIFEST.json")


def verify_payload(stage: Path) -> str:
    path = stage / "PAYLOAD_MANIFEST.json"; manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("self_included") is not False or "PAYLOAD_MANIFEST.json" in manifest.get("files", {}):
        raise ValueError("SELF_REFERENTIAL_RECOVERY_PAYLOAD")
    for relpath, expected in manifest["files"].items():
        if not (stage / relpath).is_file() or sha256_file(stage / relpath) != expected:
            raise ValueError(f"RECOVERY_PAYLOAD_DRIFT:{relpath}")
    return sha256_file(path)


def finalize_preview(root: Path, cfg: dict, status: str, attempt_id: str, metrics: dict, report: dict,
                     extra_paths: tuple[Path, ...] = ()) -> None:
    preview = root / cfg["preview_root"]
    atomic_json(preview / "metrics.json", metrics); atomic_json(preview / "report.json", report)
    atomic_text(preview / "STATUS", status + "\n")
    atomic_json(preview / "TERMINAL_STATE.json", {"schema_version": "SF-P3-RECOVERY-TERMINAL-1.0.0",
                "exp_id": cfg["exp_id"], "status": status, "attempt_id": attempt_id,
                "semantic_success": bool(metrics.get("semantic_success", False)),
                "full_catalog_stage_authorized": status == "RECOVERY_COMPLETE",
                "homology_split_authorized": False, "unlisted_artifacts_are_superseded": True})
    paths = [preview / x for x in ("STATUS", "TERMINAL_STATE.json", "metrics.json", "report.json",
                                    "input_manifest.json", "static_contract.json")] + list(extra_paths)
    if any(not path.is_file() for path in paths):
        raise ValueError("RECOVERY_PREVIEW_ARTIFACT_MISSING")
    unique = {str(path.relative_to(root)): path for path in paths}
    atomic_text(preview / "output_manifest.sha256", "".join(
        f"{sha256_file(unique[name])}  {name}\n" for name in sorted(unique)))
    for line in (preview / "output_manifest.sha256").read_text(encoding="utf-8").splitlines():
        expected, relpath = line.split("  ", 1)
        if sha256_file(root / relpath) != expected:
            raise ValueError(f"RECOVERY_PREVIEW_MANIFEST_DRIFT:{relpath}")


def static_preview(root: Path, cfg: dict) -> None:
    _targets, input_audit = validate_inputs(root, cfg)
    preview = root / cfg["preview_root"]; preview.mkdir(parents=True, exist_ok=True)
    static = {"schema_version": "SF-P3-RECOVERY-STATIC-1.0.0", "package_hashes": package_hashes(root, cfg["exp_id"]),
              "input_contract": input_audit, "gpus": 0, "formal_slurm_required": True}
    metrics = {"profile": cfg["profile"], "status": "IMPLEMENTED_NOT_RUN", "primary_metric": 0.0,
               "semantic_success": False, "scientific_recovery_executed": 0, "claim_eligible": False,
               "full_catalog_stage_authorized": False, "homology_split_authorized": False, **input_audit}
    report = {"exp_id": cfg["exp_id"], "status": "IMPLEMENTED_NOT_RUN", "semantic_success": False,
              "question": "Can exhaustive p3 Families metadata recover all 279 frozen missing exact names?",
              "answer": "NOT_RUN", "resolver_contract": cfg["resolver_contract"], "input_contract": input_audit}
    atomic_json(preview / "input_manifest.json", static); atomic_json(preview / "static_contract.json", static)
    finalize_preview(root, cfg, "IMPLEMENTED_NOT_RUN", "static-preview", metrics, report)


def prepare_running(root: Path, cfg: dict, attempt_id: str) -> dict:
    job_id = os.environ.get("SLURM_JOB_ID", "")
    if not job_id.isdigit() or int(job_id) <= 0:
        raise ValueError("FORMAL_SLURM_GUARD")
    preview = root / cfg["preview_root"]
    lock_job = preview / ".owner.lock/job_id"
    if not lock_job.is_file() or lock_job.read_text(encoding="utf-8").strip() != job_id:
        raise ValueError("FORMAL_OWNER_LOCK_MISMATCH")
    _targets, input_audit = validate_inputs(root, cfg)
    run_manifest = {"schema_version": "SF-P3-RECOVERY-RUNNING-1.0.0", "attempt_id": attempt_id,
                    "slurm_job_id": job_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "package_hashes": package_hashes(root, cfg["exp_id"]),
                    "identity_payload_sha256": cfg["identity_payload_sha256"],
                    "evaluator_contract_sha256": cfg["evaluator_contract_sha256"], "gpus": 0}
    env = {"python_version": sys.version, "h5py_version": __import__("h5py").__version__,
           "slurm_job_id": job_id, "gpus": 0}
    atomic_json(preview / "RUNNING_MANIFEST.json", run_manifest)
    atomic_json(preview / "input_manifest.json", run_manifest)
    atomic_json(preview / "static_contract.json", {"package_hashes": package_hashes(root, cfg["exp_id"]),
                "input_contract": input_audit, "gpus": 0})
    atomic_json(preview / "env.json", env)
    metrics = {"profile": cfg["profile"], "status": "RUNNING", "primary_metric": 0.0,
               "semantic_success": False, "scientific_recovery_executed": 0,
               "full_catalog_stage_authorized": False, "homology_split_authorized": False, **input_audit}
    finalize_preview(root, cfg, "RUNNING", attempt_id, metrics,
                     {"exp_id": cfg["exp_id"], "status": "RUNNING", "semantic_success": False},
                     (preview / "RUNNING_MANIFEST.json", preview / "env.json"))
    return input_audit


def run_formal(root: Path, cfg: dict, attempt_id: str) -> tuple[str, dict]:
    job_id = os.environ.get("SLURM_JOB_ID", "")
    if not job_id.isdigit() or int(job_id) <= 0:
        raise ValueError("FORMAL_SLURM_GUARD")
    preview = root / cfg["preview_root"]; attempts = preview / "attempts"; attempts.mkdir(parents=True, exist_ok=True)
    final, staging = attempts / attempt_id, attempts / (attempt_id + ".tmp")
    if final.exists() or staging.exists():
        raise ValueError("DIRTY_RECOVERY_ATTEMPT_REFUSED")
    staging.mkdir()
    try:
        targets, input_audit = validate_inputs(root, cfg)
        lock_job = preview / ".owner.lock/job_id"
        if not lock_job.is_file() or lock_job.read_text(encoding="utf-8").strip() != job_id:
            raise ValueError("FORMAL_OWNER_LOCK_MISMATCH")
        run_manifest = {"schema_version": "SF-P3-RECOVERY-RUN-1.0.0", "attempt_id": attempt_id,
                        "slurm_job_id": job_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                        "package_hashes": package_hashes(root, cfg["exp_id"]),
                        "identity_payload_sha256": cfg["identity_payload_sha256"],
                        "evaluator_contract_sha256": cfg["evaluator_contract_sha256"], "gpus": 0}
        env = {"python_version": sys.version, "h5py_version": __import__("h5py").__version__,
               "slurm_job_id": job_id, "gpus": 0}
        atomic_json(staging / "RUN_MANIFEST.json", run_manifest); atomic_json(staging / "env.json", env)
        atomic_json(preview / "input_manifest.json", run_manifest)
        atomic_json(preview / "static_contract.json", {"package_hashes": package_hashes(root, cfg["exp_id"]),
                    "input_contract": input_audit, "gpus": 0})
        atomic_json(preview / "env.json", env)
        running_metrics = {"profile": cfg["profile"], "status": "RUNNING", "primary_metric": 0.0,
                           "semantic_success": False, "scientific_recovery_executed": 0,
                           "full_catalog_stage_authorized": False, "homology_split_authorized": False, **input_audit}
        finalize_preview(root, cfg, "RUNNING", attempt_id, running_metrics,
                         {"exp_id": cfg["exp_id"], "status": "RUNNING", "semantic_success": False},
                         (staging / "RUN_MANIFEST.json", preview / "env.json"))
        candidates, scan_audit = scan_partition(root / cfg["famdb_partition_path"], {x["identifier"] for x in targets},
                                                int(cfg["famdb_expected_family_dataset_count"]),
                                                int(cfg["famdb_expected_consensus_attribute_count"]),
                                                int(cfg["famdb_expected_model_attribute_count"]),
                                                int(cfg["progress_interval_datasets"]), staging / "scan_progress.jsonl")
        resolution, recovery = resolve_targets(targets, candidates)
        blockers = recovery["missing_identifier_count"] + recovery["ambiguous_identifier_count"] + recovery["invalid_metadata_identifier_count"]
        status = "RECOVERY_COMPLETE" if blockers == 0 else "IDENTITY_RECOVERY_TYPED_BLOCK"
        metrics = {"profile": cfg["profile"], "status": status, "primary_metric": recovery["recovered_identifier_coverage"],
                   "semantic_success": True, "valid_negative": blockers > 0, "scientific_recovery_executed": 1,
                   "claim_eligible": False, "full_catalog_stage_authorized": status == "RECOVERY_COMPLETE",
                   "homology_split_authorized": False,
                   **input_audit, **scan_audit, **recovery}
        if not all(math.isfinite(float(x)) for x in metrics.values() if isinstance(x, (int, float))):
            raise ValueError("NONFINITE_RECOVERY_METRIC")
        report = {"exp_id": cfg["exp_id"], "status": status, "semantic_success": True,
                  "question": "Can exhaustive p3 Families metadata recover all 279 frozen missing exact names?",
                  "answer": "YES" if status == "RECOVERY_COMPLETE" else "NO_TYPED_BLOCK",
                  "metrics": metrics, "resolver_contract": cfg["resolver_contract"]}
        write_tsv(staging / "frozen_targets.tsv", targets,
                  ["identifier", "occurrences", "labels", "species", "status", "resolution_status", "resolution_method"])
        all_identity_rows = read_tsv(root / cfg["identity_identifier_audit"])
        ambiguity_rows = [row for row in all_identity_rows if row["identifier"] in set(cfg["audit_ambiguity_identifiers"])]
        write_tsv(staging / "existing_ambiguity_audit.tsv", ambiguity_rows,
                  ["identifier", "occurrences", "labels", "species", "status", "resolution_status", "resolution_method",
                   "candidate_count", "detail"])
        write_tsv(staging / "exact_candidates.tsv", candidates,
                  ["identifier", "accession", "version", "versioned_accession", "consensus_sha256", "consensus_length",
                   "h5_dataset_path", "source_partition"])
        write_tsv(staging / "resolution.tsv", resolution,
                  ["identifier", "occurrences", "labels", "species", "status", "candidate_row_count", "distinct_identity_count",
                   "versioned_accession", "consensus_sha256", "consensus_length", "detail"])
        atomic_json(staging / "metrics.json", metrics); atomic_json(staging / "report.json", report)
        atomic_json(staging / "RUN_MANIFEST.json", run_manifest)
        create_payload_manifest(staging); verify_payload(staging); os.replace(staging, final); verify_payload(final)
        atomic_json(preview / "input_manifest.json", json.loads((final / "RUN_MANIFEST.json").read_text(encoding="utf-8")))
        atomic_json(preview / "static_contract.json", {"package_hashes": package_hashes(root, cfg["exp_id"]), "gpus": 0})
        finalize_preview(root, cfg, status, attempt_id, metrics, report, (final / "PAYLOAD_MANIFEST.json",))
        return status, metrics
    except Exception as exc:
        failure = staging / "failure.json" if staging.exists() else preview / f"failure.{attempt_id}.json"
        atomic_json(failure, {"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        metrics = {"profile": cfg.get("profile", "cpu_asset_identity_recovery"), "status": "RECOVERY_FAILED",
                   "primary_metric": 0.0, "semantic_success": False, "scientific_recovery_executed": 0,
                   "full_catalog_stage_authorized": False, "homology_split_authorized": False, "error": str(exc)}
        report = {"exp_id": cfg.get("exp_id"), "status": "RECOVERY_FAILED", "semantic_success": False,
                  "answer": "NOT_ESTABLISHED", "error": str(exc)}
        finalize_preview(root, cfg, "RECOVERY_FAILED", attempt_id, metrics, report, (failure,)); raise


def terminal_exit_code(status: str) -> int:
    return 0 if status in {"IMPLEMENTED_NOT_RUN", "RECOVERY_COMPLETE", "IDENTITY_RECOVERY_TYPED_BLOCK"} else 2


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--attempt-id", default="static-preview"); parser.add_argument("--static-check-only", action="store_true")
    parser.add_argument("--prepare-running-only", action="store_true")
    args = parser.parse_args(); cfg = json.loads(args.config.read_text(encoding="utf-8")); root = Path(cfg["project_root"]).resolve()
    if args.static_check_only:
        static_preview(root, cfg); print(json.dumps({"status": "IMPLEMENTED_NOT_RUN", "gpus": 0}, sort_keys=True)); return
    if args.prepare_running_only:
        prepare_running(root, cfg, args.attempt_id); print(json.dumps({"status": "RUNNING", "gpus": 0}, sort_keys=True)); return
    try:
        status, _metrics = run_formal(root, cfg, args.attempt_id)
    except Exception as exc:
        print(json.dumps({"status": "RECOVERY_FAILED", "semantic_success": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps({"status": status, "gpus": 0}, sort_keys=True)); raise SystemExit(terminal_exit_code(status))


if __name__ == "__main__":
    main()
