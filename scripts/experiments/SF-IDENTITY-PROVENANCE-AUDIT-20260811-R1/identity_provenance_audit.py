#!/usr/bin/env python3
"""CPU-only audit of exact canonical RepeatMasker identifier provenance."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import traceback
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

LABELS = {1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}


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
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def opener(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if str(path).endswith(".gz") else path.open(encoding="utf-8")


def load_s0_label_contract(root: Path, cfg: dict):
    labeler_path, reference_config_path = root / cfg["s0_reference_labeler"], root / cfg["s0_reference_config"]
    if sha256_file(labeler_path) != cfg["s0_reference_labeler_sha256"]:
        raise ValueError("S0_REFERENCE_LABELER_IDENTITY_MISMATCH")
    if sha256_file(reference_config_path) != cfg["s0_reference_config_sha256"]:
        raise ValueError("S0_REFERENCE_CONFIG_IDENTITY_MISMATCH")
    reference_cfg = json.loads(reference_config_path.read_text(encoding="utf-8"))
    if reference_cfg["ontology_sha256"] != cfg["ontology_sha256"] or reference_cfg["ontology"] != cfg["ontology"]:
        raise ValueError("S0_REFERENCE_ONTOLOGY_CONTRACT_MISMATCH")
    spec = importlib.util.spec_from_file_location("sf_direct_s0_pinned_labeler", labeler_path)
    module = importlib.util.module_from_spec(spec); assert spec.loader
    sys.modules[spec.name] = module; spec.loader.exec_module(module)
    ontology = module.load_ontology(root / cfg["ontology"])
    hard_terms = set(reference_cfg["label_state_policy"]["hard_negative_terms"])
    return module, ontology, hard_terms


def p_label(raw_class: str, labeler, ontology: dict, hard_terms: set[str]) -> int | None:
    state, label, _term, _so_id, _alias = labeler.classify_annotation(raw_class, ontology, hard_terms)
    return int(label) if state == "P" else None


def is_label_contract_excluded(raw_class: str, state: str) -> bool:
    upper = raw_class.upper()
    return state == "U" and ("?" in raw_class or "RETROPOSON" in upper)


def enumerate_p_identifiers(root: Path, canonical_rows: list[dict], labeler, ontology: dict,
                            hard_terms: set[str]) -> tuple[dict[str, dict], dict[str, dict], dict[str, int]]:
    inventory: dict[str, dict] = defaultdict(lambda: {"occurrences": 0, "labels": set(), "species": set()})
    excluded: dict[str, dict] = defaultdict(lambda: {"occurrences": 0, "raw_classes": set(), "species": set()})
    stats = Counter()
    for row in canonical_rows:
        with opener(root / row["self_out"]) as handle:
            for line_number, line in enumerate(handle, 1):
                fields = line.split()
                if len(fields) < 15 or not fields[0].lstrip("+-").isdigit():
                    continue
                stats["parsed_annotation_records"] += 1
                raw_class = fields[10]
                state, label, _term, _so_id, _alias = labeler.classify_annotation(raw_class, ontology, hard_terms)
                identifier = fields[9].strip()
                if not identifier:
                    raise ValueError(f"blank annotation identifier: {row['self_out']}:{line_number}")
                if state == "P":
                    item = inventory[identifier]
                    item["occurrences"] += 1
                    item["labels"].add(int(label))
                    item["species"].add(row["species_code"])
                    stats["p_records"] += 1
                    stats["provenance_candidate_records"] += 1
                elif is_label_contract_excluded(raw_class, state):
                    item = excluded[identifier]
                    item["occurrences"] += 1
                    item["raw_classes"].add(raw_class)
                    item["species"].add(row["species_code"])
                    stats["label_contract_excluded_candidate_records"] += 1
                    stats["provenance_candidate_records"] += 1
    return dict(inventory), dict(excluded), dict(stats)


def validate_enumeration(inventory: dict[str, dict], excluded: dict[str, dict], stats: dict[str, int]) -> None:
    parsed = int(stats.get("parsed_annotation_records", 0))
    p_records = int(stats.get("p_records", 0))
    excluded_records = int(stats.get("label_contract_excluded_candidate_records", 0))
    candidates = int(stats.get("provenance_candidate_records", 0))
    errors = []
    if parsed <= 0:
        errors.append("total_records<=0")
    if p_records <= 0 or not inventory:
        errors.append("P inventory empty")
    if sum(int(item["occurrences"]) for item in inventory.values()) != p_records:
        errors.append("sum(identifier occurrences)!=P record count")
    if sum(int(item["occurrences"]) for item in excluded.values()) != excluded_records:
        errors.append("sum(excluded occurrences)!=excluded candidate record count")
    if p_records + excluded_records != candidates or candidates > parsed:
        errors.append("P+excluded candidate count conservation failed")
    if errors:
        raise ValueError("ANNOTATION_ENUMERATION_INTEGRITY_FAILED:" + ";".join(errors))


@dataclass(frozen=True)
class Candidate:
    accession: str
    versioned_accession: str
    name: str
    consensus_sha256: str
    source_asset_path: str
    source_asset_size_bytes: int
    source_asset_identity_sha256: str


def validate_partition_layout(path: Path, spec: dict, database: dict, lookup_paths: dict) -> None:
    import h5py
    if path.stat().st_size != int(spec["size_bytes"]):
        raise ValueError(f"FAMDB_PARTITION_SIZE_DRIFT:{spec['partition']}:{path.stat().st_size}")
    with h5py.File(path, "r") as handle:
        expected_attrs = {"db_version": database["db_version"], "famdb_version": database["famdb_version"],
                          "partition_num": str(spec["partition"])}
        for key, expected in expected_attrs.items():
            if str(handle.attrs.get(key)) != expected:
                raise ValueError(f"FAMDB_PARTITION_METADATA_DRIFT:{spec['partition']}:{key}")
        for field, h5_path in lookup_paths.items():
            expected_present = bool(spec[field])
            observed_present = h5_path in handle
            if observed_present != expected_present:
                raise ValueError(f"FAMDB_INDEX_LAYOUT_DRIFT:{spec['partition']}:{h5_path}")
            if observed_present and not isinstance(handle[h5_path], h5py.Group):
                raise ValueError(f"FAMDB_INDEX_WRONG_TYPE:{spec['partition']}:{h5_path}")


def validate_dfam_index_layout(root: Path, cfg: dict) -> tuple[dict, dict]:
    if sha256_file(root / cfg["famdb_rmlib_config"]) != cfg["famdb_rmlib_config_sha256"]:
        raise ValueError("FAMDB_RMLIB_CONFIG_IDENTITY_MISMATCH")
    manifest_path = root / cfg["famdb_index_layout_manifest"]
    if sha256_file(manifest_path) != cfg["famdb_index_layout_manifest_sha256"]:
        raise ValueError("FAMDB_INDEX_LAYOUT_MANIFEST_IDENTITY_MISMATCH")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "SF-DFAM-H5-INDEX-LAYOUT-1.0.0":
        raise ValueError("FAMDB_INDEX_LAYOUT_MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("rmlib_config_sha256") != cfg["famdb_rmlib_config_sha256"]:
        raise ValueError("FAMDB_INDEX_LAYOUT_RMLIB_BINDING_MISMATCH")
    partitions = manifest.get("partitions", [])
    if len(partitions) != 12 or len({int(item["partition"]) for item in partitions}) != 12:
        raise ValueError("FAMDB_INDEX_LAYOUT_PARTITION_SET_INVALID")
    famdb_dir = root / cfg["famdb_dir"]
    expected_files = {item["filename"] for item in partitions}
    observed_files = {path.name for path in famdb_dir.glob("*.h5")}
    if observed_files != expected_files:
        raise ValueError(f"FAMDB_H5_FILE_SET_DRIFT:missing={sorted(expected_files-observed_files)}:extra={sorted(observed_files-expected_files)}")
    for item in partitions:
        validate_partition_layout(famdb_dir / item["filename"], item, manifest["database"], manifest["lookup_paths"])
    skipped = sorted(int(item["partition"]) for item in partitions if not item["lookup_by_name"])
    summary = {"layout_manifest_path": cfg["famdb_index_layout_manifest"],
               "layout_manifest_sha256": cfg["famdb_index_layout_manifest_sha256"],
               "rmlib_config_sha256": cfg["famdb_rmlib_config_sha256"], "partition_count": len(partitions),
               "name_lookup_skipped_partition_count": len(skipped), "name_lookup_skipped_partitions": skipped,
               "database": manifest["database"], "full_partition_content_hashing_used": False}
    return manifest, summary


def exact_name_query(leaf, identifier: str, by_name_present: bool):
    if not by_name_present:
        return None, True
    return leaf.get_family_by_name(identifier), False


class FamDBBackend:
    def __init__(self, root: Path, cfg: dict, layout_manifest: dict):
        rmlib = root / cfg["famdb_rmlib_config"]
        if sha256_file(rmlib) != cfg["famdb_rmlib_config_sha256"]:
            raise ValueError("FAMDB_RMLIB_CONFIG_IDENTITY_MISMATCH")
        code_dir = Path(cfg["famdb_code_dir"])
        for filename, expected in cfg["famdb_code_sha256"].items():
            if sha256_file(code_dir / filename) != expected:
                raise ValueError(f"FAMDB_CODE_IDENTITY_MISMATCH:{filename}")
        sys.path.insert(0, str(code_dir))
        from famdb_classes import FamDB
        self.root = root
        self.cfg = cfg
        self.layout = {int(item["partition"]): item for item in layout_manifest["partitions"]}
        self.database = layout_manifest["database"]
        self.name_lookup_skipped_partitions = sorted(
            partition for partition, item in self.layout.items() if not item["lookup_by_name"])
        self.db = FamDB(str(root / cfg["famdb_dir"]), "r")
        metadata = self.db.get_metadata()
        if any(str(metadata.get(key)) != str(value) for key, value in self.database.items()):
            raise ValueError(f"FAMDB_RELEASE_IDENTITY_MISMATCH:{metadata}")

    def close(self) -> None:
        self.db.close()

    def _candidate(self, item, leaf) -> Candidate:
        path = Path(leaf.filename)
        relpath = str(path.relative_to(self.root))
        partition = int(leaf.get_partition_num())
        layout = self.layout[partition]
        identity_payload = {"database": self.database, "filename": layout["filename"], "partition": partition,
                            "size_bytes": int(layout["size_bytes"]),
                            "rmlib_config_sha256": self.cfg["famdb_rmlib_config_sha256"],
                            "layout_manifest_sha256": self.cfg["famdb_index_layout_manifest_sha256"]}
        identity_sha = sha256_text(json.dumps(identity_payload, sort_keys=True, separators=(",", ":")))
        consensus = str(item.consensus).upper() if item.consensus else ""
        return Candidate(str(item.accession or ""), str(item.accession_with_optional_version() or ""), str(item.name or ""),
                         sha256_text(consensus) if consensus else "", relpath, int(layout["size_bytes"]), identity_sha)

    def exact_name(self, identifier: str) -> list[Candidate]:
        result = []
        for partition in sorted(self.db.files):
            leaf = self.db.files[partition]
            item, skipped = exact_name_query(leaf, identifier, bool(self.layout[partition]["lookup_by_name"]))
            if skipped:
                continue
            if item is not None and item.name == identifier:
                result.append(self._candidate(item, leaf))
        return result

    def exact_accession(self, identifier: str) -> list[Candidate]:
        result = []
        for partition in sorted(self.db.files):
            leaf = self.db.files[partition]
            item = leaf.get_family_by_accession(identifier)
            if item is not None and identifier in {str(item.accession), str(item.accession_with_optional_version())}:
                result.append(self._candidate(item, leaf))
        return result


def resolve_identifier(identifier: str, backend) -> dict:
    for method, getter in (("exact_dfam_name", backend.exact_name), ("exact_dfam_accession", backend.exact_accession)):
        candidates = getter(identifier)
        if not candidates:
            continue
        unique = {tuple(asdict(candidate).values()): candidate for candidate in candidates}
        candidates = list(unique.values())
        if len(candidates) != 1:
            return {"identifier": identifier, "status": "ambiguous", "resolution_method": method,
                    "candidate_count": len(candidates), "detail": "multiple exact candidates with distinct provenance"}
        candidate = candidates[0]
        if not candidate.versioned_accession or not candidate.consensus_sha256 or not candidate.source_asset_identity_sha256:
            return {"identifier": identifier, "status": "missing", "resolution_method": method,
                    "candidate_count": 1, "detail": "exact candidate lacks accession/consensus/source provenance"}
        return {"identifier": identifier, "status": "resolved", "resolution_method": method,
                "candidate_count": 1, **asdict(candidate), "detail": ""}
    return {"identifier": identifier, "status": "missing", "resolution_method": "none", "candidate_count": 0,
            "detail": "no exact Dfam name or exact Dfam accession"}


def audit_inventory(inventory: dict[str, dict], backend, required_accessions: list[str], total_records: int) -> tuple[list[dict], dict]:
    rows, resolution_counts = [], Counter()
    label_conflict_count = 0
    for identifier in sorted(inventory):
        observed = inventory[identifier]
        resolved = resolve_identifier(identifier, backend)
        resolution_status = resolved["status"]
        resolution_counts[resolution_status] += 1
        labels = sorted(observed["labels"])
        label_conflict = len(labels) != 1
        if label_conflict:
            label_conflict_count += 1
            resolved["status"] = "label_conflict"
        resolved.update({"resolution_status": resolution_status, "occurrences": int(observed["occurrences"]),
                         "labels": ";".join(LABELS[x] for x in labels),
                         "species": ";".join(sorted(observed["species"])), "label_conflict": label_conflict,
                         "duplicate_consensus": False})
        rows.append(resolved)
    consensus_groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["resolution_status"] == "resolved":
            consensus_groups[row["consensus_sha256"]].append(row)
    duplicate_groups = {key: group for key, group in consensus_groups.items() if len(group) > 1}
    for group in duplicate_groups.values():
        for row in group:
            row["duplicate_consensus"] = True
    required_failures = [identifier for identifier in required_accessions if not any(
        row["identifier"] == identifier and row["resolution_status"] == "resolved" and row["resolution_method"] == "exact_dfam_accession"
        for row in rows)]
    total_identifiers = len(rows)
    resolved_count = resolution_counts["resolved"]
    blocking = resolution_counts["missing"] + resolution_counts["ambiguous"] + label_conflict_count + len(duplicate_groups) + len(required_failures)
    complete = total_identifiers > 0 and resolved_count == total_identifiers and blocking == 0
    metrics = {
        "profile": "asset_audit", "semantic_success": True, "valid_negative": not complete,
        "total_unique_p_identifiers": total_identifiers, "total_p_records": int(total_records),
        "resolved_unique_identifier_count": resolved_count, "missing_identifier_count": resolution_counts["missing"],
        "ambiguous_identifier_count": resolution_counts["ambiguous"], "label_conflict_identifier_count": label_conflict_count,
        "duplicate_consensus_group_count": len(duplicate_groups),
        "duplicate_consensus_identifier_count": sum(len(group) for group in duplicate_groups.values()),
        "required_accession_failure_count": len(required_failures),
        "unique_provenance_coverage": resolved_count / total_identifiers if total_identifiers else 0.0,
        "accession_contract_100pct_unique_provenance": complete, "human_gate_revision_required": not complete,
        "automatic_cluster_authorized": False, "prefix_guess_used": False, "positive_identifiers_deleted": 0,
        "split_built": False, "clustering_run": False, "training_run": False,
    }
    if not all(math.isfinite(float(value)) for value in metrics.values() if isinstance(value, (int, float))):
        raise ValueError("non-finite audit metric")
    return rows, {**metrics, "required_accession_failures": required_failures,
                  "duplicate_consensus_groups": {key: sorted(row["identifier"] for row in group) for key, group in duplicate_groups.items()}}


def apply_label_contract_audit(metrics: dict, excluded: dict[str, dict], stats: dict[str, int]) -> tuple[dict, list[dict]]:
    excluded_rows = [{"identifier": identifier, "occurrences": int(item["occurrences"]),
                      "raw_classes": ";".join(sorted(item["raw_classes"])),
                      "species": ";".join(sorted(item["species"])), "labeler_state": "U",
                      "status": "label_contract_excluded"}
                     for identifier, item in sorted(excluded.items())]
    p_records = int(stats["p_records"])
    excluded_records = int(stats.get("label_contract_excluded_candidate_records", 0))
    candidates = int(stats["provenance_candidate_records"])
    metrics.update({"parsed_annotation_records": int(stats["parsed_annotation_records"]),
                    "total_p_records": p_records,
                    "label_contract_excluded_candidate_records": excluded_records,
                    "label_contract_excluded_identifier_count": len(excluded_rows),
                    "provenance_candidate_records": candidates,
                    "p_plus_excluded_conservation_delta": p_records + excluded_records - candidates,
                    "label_contract_candidate_coverage": p_records / candidates,
                    "label_contract_exclusion_blocker": excluded_records > 0})
    if excluded_records:
        metrics["accession_contract_100pct_unique_provenance"] = False
        metrics["human_gate_revision_required"] = True
        metrics["valid_negative"] = True
    return metrics, excluded_rows


def provenance_terminal(metrics: dict) -> str:
    return "PROVENANCE_COMPLETE" if metrics["accession_contract_100pct_unique_provenance"] else "IDENTITY_PROVENANCE_TYPED_BLOCK"


def validate_canonical_inputs(root: Path, cfg: dict) -> list[dict]:
    for path_key, hash_key in (("canonical_split_manifest", "canonical_split_sha256"),
                               ("canonical_snapshot_report", "canonical_snapshot_report_sha256"),
                               ("canonical_snapshot_provenance", "canonical_snapshot_provenance_sha256"),
                               ("ontology", "ontology_sha256")):
        if sha256_file(root / cfg[path_key]) != cfg[hash_key]:
            raise ValueError(f"PINNED_INPUT_IDENTITY_MISMATCH:{path_key}")
    snapshot = json.loads((root / cfg["canonical_snapshot_report"]).read_text(encoding="utf-8"))
    if not snapshot.get("s0_input_contract_ready") or snapshot.get("failure_codes"):
        raise ValueError("CANONICAL_SNAPSHOT_NOT_READY")
    rows = read_tsv(root / cfg["canonical_split_manifest"])
    if len(rows) != int(cfg["canonical_expected_species_rows"]):
        raise ValueError(f"CANONICAL_SPECIES_ROW_COUNT_MISMATCH:{len(rows)}")
    provenance = {row["rewritten_manifest_path_value"]: row for row in read_tsv(root / cfg["canonical_snapshot_provenance"])}
    for row in rows:
        relpath = row["self_out"]
        if relpath not in provenance:
            raise ValueError(f"CANONICAL_SELF_OUT_PROVENANCE_MISSING:{relpath}")
        item = provenance[relpath]
        ready, frozen = root / relpath, root / item["frozen_copy_project_relpath"]
        if item["status"] != "FROZEN" or ready.resolve() != frozen.resolve() or sha256_file(ready) != item["frozen_copy_sha256"]:
            raise ValueError(f"CANONICAL_SELF_OUT_PROVENANCE_DRIFT:{relpath}")
    return rows


def create_payload_manifest(stage: Path) -> str:
    files = {str(path.relative_to(stage)): sha256_file(path) for path in sorted(stage.rglob("*"))
             if path.is_file() and path.name != "PAYLOAD_MANIFEST.json"}
    required = {"identifier_audit.tsv", "label_contract_excluded.tsv", "metrics.json", "report.json", "RUN_MANIFEST.json"}
    if required - set(files):
        raise ValueError(f"audit payload missing: {sorted(required - set(files))}")
    atomic_json(stage / "PAYLOAD_MANIFEST.json", {"schema_version": "SF-IDENTITY-PAYLOAD-1.0.0",
                "self_included": False, "files": files})
    return sha256_file(stage / "PAYLOAD_MANIFEST.json")


def verify_payload_manifest(stage: Path) -> str:
    path = stage / "PAYLOAD_MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("self_included") is not False or "PAYLOAD_MANIFEST.json" in manifest.get("files", {}):
        raise ValueError("self-referential audit payload manifest")
    for relpath, expected in manifest.get("files", {}).items():
        target = stage / relpath
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f"audit payload drift:{relpath}")
    return sha256_file(path)


def finalize_preview(root: Path, cfg: dict, status: str, attempt_id: str, metrics: dict, report: dict,
                     extra_paths: tuple[Path, ...] = ()) -> None:
    preview = root / cfg["preview_root"]
    atomic_json(preview / "metrics.json", metrics)
    atomic_json(preview / "report.json", report)
    atomic_text(preview / "STATUS", status + "\n")
    atomic_json(preview / "TERMINAL_STATE.json", {"schema_version": "SF-IDENTITY-TERMINAL-1.0.0",
                "exp_id": cfg["exp_id"], "status": status, "attempt_id": attempt_id,
                "human_gate_revision_required": bool(metrics.get("human_gate_revision_required", False)),
                "automatic_cluster_authorized": False, "unlisted_artifacts_are_superseded": True})
    paths = [preview / name for name in ("STATUS", "TERMINAL_STATE.json", "metrics.json", "report.json",
                                         "input_manifest.json", "static_contract.json")] + list(extra_paths)
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"preview manifest missing artifacts:{missing}")
    unique = {str(path.relative_to(root)): path for path in paths}
    atomic_text(preview / "output_manifest.sha256", "".join(
        f"{sha256_file(unique[relpath])}  {relpath}\n" for relpath in sorted(unique)))
    for line in (preview / "output_manifest.sha256").read_text(encoding="utf-8").splitlines():
        expected, relpath = line.split("  ", 1)
        if relpath == str((preview / "output_manifest.sha256").relative_to(root)) or sha256_file(root / relpath) != expected:
            raise ValueError(f"invalid preview output manifest:{relpath}")


def package_hashes(root: Path, exp_id: str) -> dict[str, str]:
    paths = [root / "configs" / f"{exp_id}.yaml", root / "scripts/experiments" / exp_id / "identity_provenance_audit.py",
             root / "scripts/experiments" / exp_id / "test_identity_audit.py",
             root / "scripts/experiments" / exp_id / "FROZEN_DFAM_H5_INDEX_LAYOUT_V1.json",
             root / "sbatch" / f"{exp_id}.sbatch"]
    return {str(path.relative_to(root)): sha256_file(path) for path in paths}


def terminal_exit_code(status: str) -> int:
    return 0 if status in {"PROVENANCE_COMPLETE", "IDENTITY_PROVENANCE_TYPED_BLOCK", "IMPLEMENTED_NOT_RUN"} else 2


def static_preview(root: Path, cfg: dict) -> None:
    preview = root / cfg["preview_root"]
    _layout_manifest, layout_summary = validate_dfam_index_layout(root, cfg)
    static = {"schema_version": "SF-IDENTITY-STATIC-1.0.0", "config_sha256": sha256_file(
        root / "configs" / f"{cfg['exp_id']}.yaml"), "package_hashes": package_hashes(root, cfg["exp_id"]),
        "resolver_order": cfg["resolver_order"], "forbidden_actions": cfg["forbidden_actions"]}
    atomic_json(preview / "input_manifest.json", static)
    atomic_json(preview / "static_contract.json", static)
    evaluator_sha = sha256_file(Path(__file__))
    metrics = {"profile": cfg["profile"], "status": "IMPLEMENTED_NOT_RUN", "semantic_success": False,
               "valid_negative": False, "parsed_annotation_records": 0, "total_unique_p_identifiers": 0,
               "total_p_records": 0, "label_contract_excluded_candidate_records": 0,
               "label_contract_excluded_identifier_count": 0, "provenance_candidate_records": 0,
               "p_plus_excluded_conservation_delta": 0, "label_contract_candidate_coverage": 0.0,
               "label_contract_exclusion_blocker": False,
               "resolved_unique_identifier_count": 0, "missing_identifier_count": 0, "ambiguous_identifier_count": 0,
               "label_conflict_identifier_count": 0, "duplicate_consensus_group_count": 0,
               "duplicate_consensus_identifier_count": 0, "required_accession_failure_count": 0,
               "unique_provenance_coverage": 0.0, "accession_contract_100pct_unique_provenance": False,
               "human_gate_revision_required": False, "automatic_cluster_authorized": False,
               "scientific_audit_executed": 0, "claim_eligible": False, "evaluator_sha256": evaluator_sha,
               "s0_reference_labeler_sha256": cfg["s0_reference_labeler_sha256"], **layout_summary}
    report = {"exp_id": cfg["exp_id"], "profile": cfg["profile"], "status": "IMPLEMENTED_NOT_RUN",
              "semantic_success": False, "valid_negative": False, "claim_eligible": False,
              "question": "Can every canonical P-state identifier be assigned 100% unique exact Dfam provenance?",
              "answer": "NOT_RUN", "automatic_cluster_authorized": False,
              "evaluator": {"path": str(Path(__file__).resolve().relative_to(root)), "sha256": evaluator_sha},
              "s0_label_contract": {"path": cfg["s0_reference_labeler"], "sha256": cfg["s0_reference_labeler_sha256"]},
              "dfam_index_layout": layout_summary}
    finalize_preview(root, cfg, "IMPLEMENTED_NOT_RUN", "static-preview", metrics, report)


def run_audit(root: Path, cfg: dict, attempt_id: str) -> tuple[str, dict]:
    preview = root / cfg["preview_root"]
    if not os.environ.get("SLURM_JOB_ID"):
        raise ValueError("FORMAL_SLURM_GUARD: real audit requires a Slurm allocation")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", attempt_id):
        raise ValueError("invalid attempt id")
    staging, final = preview / "attempts" / f"audit-{attempt_id}.tmp", preview / "attempts" / f"audit-{attempt_id}"
    backend = None
    try:
        if staging.exists() or final.exists():
            raise FileExistsError("refusing dirty audit attempt")
        staging.mkdir(parents=True)
        canonical_rows = validate_canonical_inputs(root, cfg)
        layout_manifest, layout_summary = validate_dfam_index_layout(root, cfg)
        labeler, ontology, hard_terms = load_s0_label_contract(root, cfg)
        inventory, excluded, enumeration_stats = enumerate_p_identifiers(
            root, canonical_rows, labeler, ontology, hard_terms)
        validate_enumeration(inventory, excluded, enumeration_stats)
        backend = FamDBBackend(root, cfg, layout_manifest)
        audit_rows, metrics = audit_inventory(
            inventory, backend, list(cfg["required_accession_identifiers"]), int(enumeration_stats["p_records"]))
        backend.close()
        backend = None
        metrics, excluded_rows = apply_label_contract_audit(metrics, excluded, enumeration_stats)
        metrics.update(layout_summary)
        fields = ["identifier", "occurrences", "labels", "species", "status", "resolution_status", "resolution_method", "candidate_count",
                  "accession", "versioned_accession", "name", "consensus_sha256", "source_asset_path",
                  "source_asset_size_bytes", "source_asset_identity_sha256", "label_conflict", "duplicate_consensus", "detail"]
        write_tsv(staging / "identifier_audit.tsv", audit_rows, fields)
        write_tsv(staging / "label_contract_excluded.tsv", excluded_rows,
                  ["identifier", "occurrences", "raw_classes", "species", "labeler_state", "status"])
        terminal = provenance_terminal(metrics)
        evaluator_sha = sha256_file(Path(__file__))
        metrics.update({"status": terminal, "scientific_audit_executed": 1, "claim_eligible": False,
                        "evaluator_sha256": evaluator_sha, "s0_reference_labeler_sha256": cfg["s0_reference_labeler_sha256"]})
        report = {"exp_id": cfg["exp_id"], "profile": cfg["profile"], "status": terminal,
                  "semantic_success": True, "valid_negative": terminal == "IDENTITY_PROVENANCE_TYPED_BLOCK", "claim_eligible": False,
                  "question": "Can every canonical P-state identifier be assigned 100% unique exact Dfam provenance?",
                  "answer": "YES" if terminal == "PROVENANCE_COMPLETE" else "NO_HUMAN_GATE_REVISION_REQUIRED",
                  "metrics": metrics, "resolver_order": cfg["resolver_order"], "automatic_cluster_authorized": False,
                  "evaluator": {"path": str(Path(__file__).resolve().relative_to(root)), "sha256": evaluator_sha},
                  "s0_label_contract": {"path": cfg["s0_reference_labeler"], "sha256": cfg["s0_reference_labeler_sha256"]},
                  "dfam_index_layout": layout_summary}
        atomic_json(staging / "metrics.json", metrics)
        atomic_json(staging / "report.json", report)
        atomic_json(staging / "RUN_MANIFEST.json", {"schema_version": "SF-IDENTITY-RUN-1.0.0",
                    "attempt_id": attempt_id, "slurm_job_id": os.environ["SLURM_JOB_ID"],
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "config_sha256": sha256_file(root / "configs" / f"{cfg['exp_id']}.yaml"),
                    "package_hashes": package_hashes(root, cfg["exp_id"]), "gpus": 0})
        payload_sha = create_payload_manifest(staging)
        if verify_payload_manifest(staging) != payload_sha:
            raise ValueError("audit payload changed before promotion")
        os.replace(staging, final)
        if verify_payload_manifest(final) != payload_sha:
            raise ValueError("audit payload changed during promotion")
        atomic_json(preview / "input_manifest.json", json.loads((final / "RUN_MANIFEST.json").read_text(encoding="utf-8")))
        atomic_json(preview / "static_contract.json", {"package_hashes": package_hashes(root, cfg["exp_id"]),
                    "resolver_order": cfg["resolver_order"], "forbidden_actions": cfg["forbidden_actions"]})
        finalize_preview(root, cfg, terminal, attempt_id, metrics, report, (final / "PAYLOAD_MANIFEST.json",))
        return terminal, metrics
    except Exception as exc:
        failure = staging / "failure.json" if staging.exists() else preview / f"failure.{attempt_id}.json"
        atomic_json(failure, {"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        metrics = {"profile": "asset_audit", "status": "AUDIT_FAILED", "primary_metric": 0.0,
                   "semantic_success": False, "valid_negative": False, "scientific_audit_executed": 0,
                   "accession_contract_100pct_unique_provenance": False, "human_gate_revision_required": True,
                   "automatic_cluster_authorized": False, "claim_eligible": False}
        report = {"exp_id": cfg["exp_id"], "profile": cfg.get("profile", "asset_audit"), "status": "AUDIT_FAILED",
                  "semantic_success": False, "valid_negative": False, "answer": "NOT_ESTABLISHED",
                  "error": str(exc), "human_gate_revision_required": True, "automatic_cluster_authorized": False}
        finalize_preview(root, cfg, "AUDIT_FAILED", attempt_id, metrics, report, (failure,))
        raise
    finally:
        if backend is not None:
            backend.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--attempt-id", default="static-preview")
    parser.add_argument("--static-check-only", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    if args.static_check_only:
        static_preview(root, cfg)
        print(json.dumps({"status": "IMPLEMENTED_NOT_RUN", "gpus": 0}, sort_keys=True))
        return
    try:
        status, _metrics = run_audit(root, cfg, args.attempt_id)
    except Exception as exc:
        print(json.dumps({"status": "AUDIT_FAILED", "semantic_success": False,
                          "error_type": type(exc).__name__, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps({"status": status, "automatic_cluster_authorized": False}, sort_keys=True))
    exit_code = terminal_exit_code(status)
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
