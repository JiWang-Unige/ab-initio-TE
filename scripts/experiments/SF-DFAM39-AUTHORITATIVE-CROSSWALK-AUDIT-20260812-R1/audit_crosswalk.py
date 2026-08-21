#!/usr/bin/env python3
"""Dfam 3.9 curated-EMBL authoritative exact crosswalk CPU gate."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import platform
import re
import socket
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath


class IntegrityFailure(RuntimeError):
    pass


class ResourceFailure(RuntimeError):
    pass


EXACT_ALIAS_FIELDS = ("NM", "PI", "SN", "DR")
EXACT_IDENTITY_FIELDS = ("AC", "ID")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def authorization_flags() -> dict[str, bool]:
    return {"full_catalog_stage_authorized": False, "homology_split_authorized": False,
            "data_stage_authorized": False, "gpu_authorized": False, "s1_authorized": False}


def verify_path(root: Path, relative: str, digest: str, size: int | None = None) -> Path:
    rel = PurePosixPath(relative)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        raise IntegrityFailure(f"INPUT_PATH_NOT_ROOT_RELATIVE:{relative}")
    path = root.joinpath(*rel.parts)
    if not path.is_file() or path.is_symlink() or sha256_file(path) != digest:
        raise IntegrityFailure(f"PINNED_INPUT_DRIFT:{relative}")
    if size is not None and path.stat().st_size != int(size):
        raise IntegrityFailure(f"PINNED_INPUT_SIZE_DRIFT:{relative}")
    return path


def package_hashes(root: Path, cfg: dict) -> dict[str, str]:
    exp = cfg["exp_id"]
    paths = [root / "configs" / f"{exp}.yaml",
             root / "scripts/experiments" / exp / "audit_crosswalk.py",
             root / "scripts/experiments" / exp / "test_audit_crosswalk.py",
             root / "sbatch" / f"{exp}.sbatch", root / cfg["experiment_doc_path"]]
    return {str(path.relative_to(root)): sha256_file(path) for path in paths}


def environment_snapshot() -> dict:
    keys = ("CONDA_DEFAULT_ENV", "CONDA_PREFIX", "SLURM_JOB_ID", "SLURM_JOB_PARTITION",
            "SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE", "SLURM_JOB_GPUS",
            "MKL_NUM_THREADS", "MKL_DYNAMIC", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")
    return {"python_version": sys.version, "python_executable": sys.executable,
            "python_implementation": platform.python_implementation(), "platform": platform.platform(),
            "hostname": socket.gethostname(), "selected_environment": {key: os.environ.get(key, "") for key in keys},
            "gpu_count_contract": 0}


def parse_slurm_memory_mb(value: str) -> int:
    """Parse SLURM_MEM_PER_NODE (normally integer MiB; tolerate explicit K/M/G/T suffix)."""
    match = re.fullmatch(r"([1-9][0-9]*)([KkMmGgTt]?)", value.strip())
    if not match:
        raise ResourceFailure(f"SLURM_MEM_PER_NODE_FORMAT:{value}")
    amount, suffix = int(match.group(1)), match.group(2).upper()
    multiplier = {"": 1, "K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}[suffix]
    return int(amount * multiplier)


def validate_formal_resources(cfg: dict) -> dict:
    expected = cfg["resource_contract"]
    gpu_tokens = {"", "none", "n/a", "(null)"}
    observed_gpu_vars = {key: os.environ.get(key, "")
                         for key in ("SLURM_JOB_GPUS", "SLURM_GPUS_ON_NODE")}
    if expected["gpus"] != 0 or any(value.strip().lower() not in gpu_tokens
                                     for value in observed_gpu_vars.values()):
        raise ResourceFailure(f"GPU_RESOURCE_CONTRACT:{observed_gpu_vars}")
    cpus = os.environ.get("SLURM_CPUS_PER_TASK", "")
    if not cpus.isdigit() or int(cpus) != int(expected["cpus"]):
        raise ResourceFailure(f"CPU_RESOURCE_CONTRACT:{cpus}")
    memory_raw = os.environ.get("SLURM_MEM_PER_NODE", "")
    memory_mb = parse_slurm_memory_mb(memory_raw)
    expected_memory_mb = int(expected["memory_gib"]) * 1024
    if memory_mb != expected_memory_mb:
        raise ResourceFailure(f"MEMORY_RESOURCE_CONTRACT:{memory_mb}")
    return {"slurm_cpus_per_task": int(cpus), "slurm_mem_per_node_raw": memory_raw,
            "slurm_mem_per_node_mb": memory_mb, "observed_gpu_variables": observed_gpu_vars,
            "gpus": 0, "walltime_minutes_contract": int(expected["walltime_minutes"]),
            "walltime_runtime_env_verified": False,
            "walltime_env_reason": "Slurm exposes no cross-version reliable allocation walltime variable",
            "sbatch_cli_resource_overrides_prohibited": True}


def validate_reviewed_submission(root: Path, cfg: dict, gate: dict) -> dict:
    """Bind formal execution to the independently reviewed sbatch; CLI overrides remain prohibited."""
    relative = f"sbatch/{cfg['exp_id']}.sbatch"
    path = root / relative
    reviewed = gate.get("reviewed_files", {})
    if not path.is_file() or reviewed.get(relative) != sha256_file(path):
        raise IntegrityFailure("REVIEWED_SBATCH_BINDING_MISSING_OR_STALE")
    return {"authorized_sbatch_root_relative": relative, "reviewed_sbatch_sha256": sha256_file(path),
            "authorized_submission_command": f"sbatch {relative}",
            "sbatch_cli_resource_overrides_prohibited": True,
            "walltime_minutes_from_reviewed_sbatch": int(cfg["resource_contract"]["walltime_minutes"])}


def validate_pinned_inputs(root: Path, cfg: dict) -> dict:
    source_contract = cfg["source_contract"]
    if (source_contract.get("exact_alias_fields") != list(EXACT_ALIAS_FIELDS)
            or source_contract.get("exact_identity_fields") != list(EXACT_IDENTITY_FIELDS)
            or source_contract.get("exact_relation_fields")
            != list(EXACT_ALIAS_FIELDS + EXACT_IDENTITY_FIELDS)):
        raise IntegrityFailure("EXACT_RELATION_FIELD_CONTRACT_DRIFT")
    source = cfg["curated_embl"]
    source_path = verify_path(root, source["path"], source["sha256"], source["size_bytes"])
    sidecar = verify_path(root, cfg["md5_sidecar"]["path"], cfg["md5_sidecar"]["sha256"],
                          cfg["md5_sidecar"]["size_bytes"])
    notes = verify_path(root, cfg["release_notes"]["path"], cfg["release_notes"]["sha256"],
                        cfg["release_notes"]["size_bytes"])
    if md5_file(source_path) != source["md5"]:
        raise IntegrityFailure("CURATED_EMBL_MD5_DRIFT")
    sidecar_text = sidecar.read_text(encoding="utf-8")
    if source["md5"] not in sidecar_text or "Dfam-curated_only-1.embl.gz" not in sidecar_text:
        raise IntegrityFailure("MD5_SIDECAR_SEMANTICS_DRIFT")
    notes_text = notes.read_text(encoding="utf-8")
    for token in ("RELEASE 3.9", "CC0 1.0", "Dfam"):
        if token not in notes_text:
            raise IntegrityFailure(f"RELEASE_NOTES_CONTRACT_DRIFT:{token}")
    frozen = cfg["frozen_inputs"]
    files = {}
    for stem in ("targets", "identifier_audit", "excluded", "x13", "job11526905_audit",
                 "direct_labeler", "evaluator_contract"):
        files[stem] = verify_path(root, frozen[f"{stem}_path"], frozen[f"{stem}_sha256"])
    targets = read_tsv(files["targets"])
    excluded = read_tsv(files["excluded"])
    x13 = read_tsv(files["x13"])
    universe = read_tsv(files["identifier_audit"])
    target_ids = {row["identifier"] for row in targets}
    excluded_ids = {row["identifier"] for row in excluded}
    if (len(targets) != frozen["target_identifier_count"]
            or len({row["identifier"] for row in targets}) != len(targets)
            or sum(int(row["occurrences"]) for row in targets) != frozen["target_occurrence_mass"]):
        raise IntegrityFailure("TARGET_DENOMINATOR_DRIFT")
    if any(row["status"] != "missing" or row["resolution_status"] != "missing" for row in targets):
        raise IntegrityFailure("TARGET_STATUS_DRIFT")
    if (len(universe) != frozen["identifier_audit_count"]
            or len({row["identifier"] for row in universe}) != len(universe)):
        raise IntegrityFailure("IDENTIFIER_UNIVERSE_DRIFT")
    if not target_ids <= {row["identifier"] for row in universe}:
        raise IntegrityFailure("TARGET_NOT_IN_FROZEN_IDENTIFIER_UNIVERSE")
    if (len(excluded) != frozen["excluded_identifier_count"]
            or sum(int(row["occurrences"]) for row in excluded) != frozen["excluded_occurrence_mass"]
            or any(row["labeler_state"] != "U" or row["status"] != "label_contract_excluded"
                   for row in excluded)):
        raise IntegrityFailure("U_IGNORE_CONTRACT_DRIFT")
    if target_ids & excluded_ids:
        raise IntegrityFailure("U_IGNORE_ENTERED_PRIMARY_DENOMINATOR")
    if (len(x13) != 1 or x13[0]["identifier"] != frozen["x13_identifier"]
            or int(x13[0]["occurrences"]) != frozen["x13_occurrence_mass"]
            or x13[0]["status"] != "ambiguous"):
        raise IntegrityFailure("X13_AUDIT_ONLY_DRIFT")
    if frozen["x13_identifier"] in target_ids:
        raise IntegrityFailure("X13_ENTERED_PRIMARY_DENOMINATOR")
    old = json.loads(files["job11526905_audit"].read_text(encoding="utf-8"))
    if (old.get("job_id") != "11526905" or old.get("resolution", {}).get("missing_identifier_count") != 279
            or old.get("denominator", {}).get("target_occurrence_mass") != 6432583):
        raise IntegrityFailure("JOB11526905_VALID_NEGATIVE_DRIFT")
    if cfg["authorization"] != authorization_flags():
        raise IntegrityFailure("AUTHORIZATION_MUST_REMAIN_FALSE")
    return {"source_root_relative": str(source_path.relative_to(root)),
            "targets": targets, "excluded": excluded, "x13": x13,
            "universe": universe, "source_sha256": source["sha256"],
            "target_identifier_count": len(targets),
            "target_occurrence_mass": sum(int(row["occurrences"]) for row in targets),
            "excluded_identifier_count": len(excluded),
            "excluded_occurrence_mass": sum(int(row["occurrences"]) for row in excluded),
            "x13_identifier_count": 1, "x13_occurrence_mass": int(x13[0]["occurrences"]),
            "direct_label_contract_unchanged": True, "label_blind_resolution": True,
            **authorization_flags()}


ID_RE = re.compile(r"^(DF\d+); SV (\d+); .*; (\d+) BP\.$")
IUPAC = set("ACGTRYSWKMBDHVN")


def clean_alias(value: str, field: str) -> tuple[str, str]:
    value = value.strip()
    if field == "DR":
        if ";" not in value:
            raise IntegrityFailure(f"EMBL_DR_SCHEMA:{value}")
        database, value = value.split(";", 1)
        value = value.strip()
        return value[:-1] if value.endswith(".") else value, database.strip()
    while value.endswith(";") or value.endswith("."):
        value = value[:-1].rstrip()
    return value, "Dfam"


def parse_curated_embl(path: Path, cfg: dict) -> tuple[list[dict], dict]:
    records, counts, current, sequence, in_sequence = [], Counter(), None, [], False

    def finish() -> None:
        nonlocal current, sequence, in_sequence
        if current is None:
            return
        required = {"accession", "version", "declared_length", "ac", "nm", "aliases"}
        if set(current) != required:
            raise IntegrityFailure(f"EMBL_RECORD_INTERNAL_SCHEMA:{current.get('accession', '')}")
        normalized = "".join(sequence).upper().replace("U", "T")
        if not normalized or set(normalized) - IUPAC:
            raise IntegrityFailure(f"EMBL_SEQUENCE_ALPHABET:{current['accession']}")
        if len(normalized) != current["declared_length"]:
            raise IntegrityFailure(f"EMBL_SEQUENCE_LENGTH:{current['accession']}:{len(normalized)}")
        if current["ac"] != current["accession"]:
            raise IntegrityFailure(f"EMBL_AC_ID_MISMATCH:{current['accession']}")
        records.append({**current, "versioned_accession": f"{current['accession']}.{current['version']}",
                        "canonical_name": current["nm"], "consensus_sha256": sha256_text(normalized),
                        "consensus_length": len(normalized)})
        current, sequence, in_sequence = None, [], False

    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for raw in handle:
            line = raw.rstrip("\r\n")
            if line.startswith("ID   "):
                if current is not None:
                    raise IntegrityFailure("EMBL_RECORD_MISSING_TERMINATOR")
                counts["ID"] += 1
                match = ID_RE.match(line[5:])
                if not match:
                    raise IntegrityFailure(f"EMBL_ID_SCHEMA:{line}")
                current = {"accession": match.group(1), "version": int(match.group(2)),
                           "declared_length": int(match.group(3)), "ac": "", "nm": "", "aliases": []}
                continue
            if current is None:
                continue
            if line == "//":
                finish()
                continue
            if in_sequence:
                letters = "".join(character for character in line if character.isalpha())
                if letters:
                    sequence.append(letters)
                continue
            field = line[:2] if len(line) >= 5 and line[2:5] == "   " else ""
            value = line[5:] if field else ""
            if field in {"NM", "AC", "PI", "SN", "DR", "SQ"}:
                counts[field] += 1
            if field == "NM":
                if current["nm"]:
                    raise IntegrityFailure(f"EMBL_DUPLICATE_NM:{current['accession']}")
                current["nm"] = clean_alias(value, "NM")[0]
            elif field == "AC":
                if current["ac"]:
                    raise IntegrityFailure(f"EMBL_DUPLICATE_AC:{current['accession']}")
                current["ac"] = clean_alias(value, "AC")[0]
            elif field in {"PI", "SN", "DR"}:
                alias, database = clean_alias(value, field)
                if not alias:
                    raise IntegrityFailure(f"EMBL_EMPTY_ALIAS:{current['accession']}:{field}")
                current["aliases"].append({"relation_field": field, "relation_database": database,
                                           "alias": alias})
            elif field == "SQ":
                in_sequence = True
    if current is not None:
        raise IntegrityFailure("EMBL_FINAL_RECORD_UNTERMINATED")
    expected = cfg["curated_embl"]["expected_field_counts"]
    observed = {field: counts[field] for field in expected}
    if (observed != expected or len(records) != cfg["curated_embl"]["expected_record_count"]
            or len(records) != cfg["curated_embl"]["expected_sequence_record_count"]):
        raise IntegrityFailure(f"EMBL_FIELD_OR_RECORD_COUNT_DRIFT:{observed}:{len(records)}")
    if len({row["versioned_accession"] for row in records}) != len(records):
        raise IntegrityFailure("EMBL_DUPLICATE_VERSIONED_ACCESSION")
    for row in records:
        if row["canonical_name"]:
            row["aliases"].append({"relation_field": "NM", "relation_database": "Dfam",
                                   "alias": row["canonical_name"]})
    audit = {"record_count": len(records), "field_counts": observed,
             "sequence_record_count": sum(1 for row in records if row["consensus_length"] > 0),
             "unique_versioned_accession_count": len({row["versioned_accession"] for row in records}),
             "export_dialect": cfg["source_contract"]["export_dialect"]}
    return records, audit


def build_crosswalk(targets: list[dict], records: list[dict]) -> tuple[list[dict], list[dict], dict]:
    target_names = {row["identifier"] for row in targets}
    candidates = []
    for record in records:
        relations = list(record["aliases"])
        relations.extend([{"relation_field": "AC", "relation_database": "Dfam_identity",
                           "alias": record["accession"]},
                          {"relation_field": "ID", "relation_database": "Dfam_identity",
                           "alias": record["versioned_accession"]}])
        seen = set()
        for relation in relations:
            identifier = relation["alias"]
            key = (identifier, record["versioned_accession"], relation["relation_field"],
                   relation["relation_database"])
            if identifier not in target_names or key in seen:
                continue
            seen.add(key)
            candidates.append({"identifier": identifier, "relation_field": relation["relation_field"],
                               "relation_database": relation["relation_database"],
                               "official_alias_exact": identifier, "accession": record["accession"],
                               "version": record["version"], "versioned_accession": record["versioned_accession"],
                               "canonical_name": record["canonical_name"],
                               "consensus_sha256": record["consensus_sha256"],
                               "consensus_length": record["consensus_length"]})
    candidates.sort(key=lambda row: (row["identifier"], row["versioned_accession"],
                                     row["relation_field"], row["relation_database"]))
    by_identifier = defaultdict(list)
    for row in candidates:
        by_identifier[row["identifier"]].append(row)
    resolution = []
    for target in sorted(targets, key=lambda row: row["identifier"]):
        rows = by_identifier[target["identifier"]]
        identities = {(row["versioned_accession"], row["consensus_sha256"]) for row in rows}
        invalid = [row for row in rows if not row["canonical_name"] or not row["consensus_sha256"]]
        if not rows:
            status, detail = "missing", "no exact NM/PI/SN/DR alias or exact AC/ID identity in frozen curated EMBL"
        elif invalid:
            status, detail = "invalid_metadata", "candidate lacks NM canonical name or consensus"
        elif len(identities) == 1:
            status, detail = "resolved_unique", "one distinct accession+consensus identity"
        else:
            status, detail = "ambiguous", "multiple distinct accession+consensus identities"
        unique = rows[0] if status == "resolved_unique" else {}
        resolution.append({"identifier": target["identifier"], "occurrences": int(target["occurrences"]),
                           "candidate_row_count": len(rows), "distinct_identity_count": len(identities),
                           "resolution_status": status,
                           "versioned_accession": unique.get("versioned_accession", ""),
                           "canonical_name": unique.get("canonical_name", ""),
                           "consensus_sha256": unique.get("consensus_sha256", ""), "detail": detail})
    counts = Counter(row["resolution_status"] for row in resolution)
    mass = Counter()
    for row in resolution:
        mass[row["resolution_status"]] += row["occurrences"]
    audit = {"authoritative_hit_identifier_count": sum(1 for row in resolution if row["candidate_row_count"] > 0),
             "resolved_unique_identifier_count": counts["resolved_unique"],
             "ambiguous_identifier_count": counts["ambiguous"],
             "invalid_metadata_identifier_count": counts["invalid_metadata"],
             "missing_identifier_count": counts["missing"],
             "resolved_unique_occurrence_mass": mass["resolved_unique"],
             "ambiguous_occurrence_mass": mass["ambiguous"],
             "invalid_metadata_occurrence_mass": mass["invalid_metadata"],
             "missing_occurrence_mass": mass["missing"],
             "candidate_row_count": len(candidates),
             "identifier_conservation_delta": len(resolution) - len(targets),
             "occurrence_conservation_delta": sum(row["occurrences"] for row in resolution)
                                              - sum(int(row["occurrences"]) for row in targets)}
    return candidates, resolution, audit


def build_postjoin_audits(targets: list[dict], resolution: list[dict]) -> tuple[list[dict], list[dict], int]:
    """Join labels/species only after identity resolution; never feeds candidate selection."""
    target_by_id = {row["identifier"]: row for row in targets}
    species_audit = [{"identifier": row["identifier"], "species": target_by_id[row["identifier"]]["species"]}
                     for row in resolution]
    by_identity = defaultdict(list)
    for row in resolution:
        if row["resolution_status"] == "resolved_unique":
            by_identity[(row["versioned_accession"], row["consensus_sha256"])].append(row["identifier"])
    conflict_audit = []
    for identity, identifiers in sorted(by_identity.items()):
        labels = sorted({target_by_id[identifier]["labels"] for identifier in identifiers})
        conflict_audit.append({"versioned_accession": identity[0], "consensus_sha256": identity[1],
                               "identifiers": ";".join(sorted(identifiers)), "direct_labels": ";".join(labels),
                               "label_conflict": len(labels) > 1})
    return species_audit, conflict_audit, sum(bool(row["label_conflict"]) for row in conflict_audit)


def semantic_result(cfg: dict, input_audit: dict, embl_audit: dict, candidates: list[dict],
                    resolution: list[dict], crosswalk_audit: dict,
                    label_conflict_count: int = 0) -> tuple[str, dict, dict]:
    blockers = (crosswalk_audit["ambiguous_identifier_count"]
                + crosswalk_audit["invalid_metadata_identifier_count"]
                + crosswalk_audit["missing_identifier_count"] + label_conflict_count)
    status = "CROSSWALK_RECOVERY_COMPLETE" if blockers == 0 else "IDENTITY_SOURCE_TYPED_BLOCK"
    expected = cfg["preliminary_probe_expectation"]
    probe_match = (crosswalk_audit["authoritative_hit_identifier_count"] == expected["authoritative_hit_identifier_count"]
                   and crosswalk_audit["resolved_unique_identifier_count"] == expected["resolved_unique_identifier_count"]
                   and crosswalk_audit["ambiguous_identifier_count"] == expected["ambiguous_identifier_count"]
                   and sorted(row["identifier"] for row in resolution if row["resolution_status"] == "ambiguous")
                   == sorted(expected["ambiguous_identifiers"]))
    if not probe_match:
        raise IntegrityFailure("PRELIMINARY_PROBE_SHAPE_DRIFT")
    metrics = {"profile": cfg["profile"], "status": status, "primary_metric":
               crosswalk_audit["resolved_unique_identifier_count"] / input_audit["target_identifier_count"],
               "semantic_success": True, "valid_negative": status == "IDENTITY_SOURCE_TYPED_BLOCK",
               "claim_eligible": False, "scientific_audit_executed": 1,
               "full_catalog_human_gate_eligible": status == "CROSSWALK_RECOVERY_COMPLETE",
               "homology_split_only_contract": True, "direct_label_contract_unchanged": True,
               "u_ignore_identifier_count": input_audit["excluded_identifier_count"],
               "u_ignore_occurrence_mass": input_audit["excluded_occurrence_mass"],
               "x13_audit_only_identifier_count": input_audit["x13_identifier_count"],
               "x13_audit_only_occurrence_mass": input_audit["x13_occurrence_mass"],
               "target_identifier_count": input_audit["target_identifier_count"],
               "target_occurrence_mass": input_audit["target_occurrence_mass"],
               "preliminary_probe_shape_match": probe_match, **embl_audit, **crosswalk_audit,
               "label_conflict_identity_count": label_conflict_count,
               **authorization_flags()}
    if not all(math.isfinite(float(value)) for value in metrics.values() if isinstance(value, (int, float))):
        raise IntegrityFailure("NONFINITE_METRIC")
    report = {"schema_version": "SF-DFAM39-CROSSWALK-REPORT-1.0.0", "exp_id": cfg["exp_id"],
              "status": status, "semantic_success": True,
              "question": "Can frozen Dfam 3.9 curated EMBL exact relations uniquely resolve all 279 identifiers?",
              "answer": "YES" if status == "CROSSWALK_RECOVERY_COMPLETE" else "NO_TYPED_BLOCK",
              "source_contract": cfg["source_contract"], "metrics": metrics,
              "ambiguous_identifiers": [row["identifier"] for row in resolution
                                         if row["resolution_status"] == "ambiguous"]}
    return status, metrics, report


def create_payload_manifest(stage: Path) -> str:
    files = {path.name: sha256_file(path) for path in sorted(stage.iterdir())
             if path.is_file() and path.name != "PAYLOAD_MANIFEST.json"}
    required = {"SOURCE_MANIFEST.json", "RUN_MANIFEST.json", "env.json", "OUTPUT_INDEX.json",
                "authoritative_candidates.tsv", "identity_resolution.tsv", "species_audit.tsv",
                "label_conflict_audit.tsv",
                "frozen_targets.tsv", "label_contract_excluded.tsv", "x13_audit_only.tsv",
                "metrics.json", "report.json"}
    if required - set(files):
        raise IntegrityFailure(f"PAYLOAD_MISSING:{sorted(required - set(files))}")
    atomic_json(stage / "PAYLOAD_MANIFEST.json",
                {"schema_version": "SF-DFAM39-CROSSWALK-PAYLOAD-1.0.0",
                 "self_included": False, "files": files})
    return sha256_file(stage / "PAYLOAD_MANIFEST.json")


def verify_payload(stage: Path) -> None:
    manifest = json.loads((stage / "PAYLOAD_MANIFEST.json").read_text(encoding="utf-8"))
    if set(manifest) != {"schema_version", "self_included", "files"} or manifest["self_included"] is not False:
        raise IntegrityFailure("PAYLOAD_MANIFEST_SCHEMA")
    actual = {path.name for path in stage.iterdir() if path.is_file()}
    if actual != set(manifest["files"]) | {"PAYLOAD_MANIFEST.json"}:
        raise IntegrityFailure("PAYLOAD_EXACT_FILE_SET")
    for name, digest in manifest["files"].items():
        if sha256_file(stage / name) != digest:
            raise IntegrityFailure(f"PAYLOAD_HASH_DRIFT:{name}")


STATE_FILES = {"STATUS", "TERMINAL_STATE.json", "metrics.json", "report.json", "input_manifest.json",
               "static_contract.json", "external_artifacts.json"}


def publish_state(root: Path, cfg: dict, status: str, attempt_id: str, metrics: dict, report: dict,
                  input_manifest: dict, static_contract: dict, external: tuple[Path, ...] = ()) -> None:
    preview = root / cfg["preview_root"]
    states = preview / "states"
    states.mkdir(parents=True, exist_ok=True)
    terminal = {"schema_version": "SF-DFAM39-CROSSWALK-TERMINAL-1.0.0", "exp_id": cfg["exp_id"],
                "status": status, "attempt_id": attempt_id,
                "semantic_success": bool(metrics.get("semantic_success", False)), **authorization_flags()}
    links = {"artifacts": [{"root_relative_path": str(path.relative_to(root)), "sha256": sha256_file(path)}
                            for path in sorted(external)]}
    docs = {"STATUS": status + "\n", "TERMINAL_STATE.json": terminal, "metrics.json": metrics,
            "report.json": report, "input_manifest.json": input_manifest,
            "static_contract.json": static_contract, "external_artifacts.json": links}
    state_id = sha256_text(stable_json(docs))
    final = states / state_id
    if not final.exists():
        stage = states / f".tmp.{state_id}.{os.getpid()}"
        stage.mkdir()
        for name, value in docs.items():
            atomic_text(stage / name, value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + "\n")
        atomic_text(stage / "STATE_MANIFEST.sha256", "".join(
            f"{sha256_file(stage / name)}  {name}\n" for name in sorted(STATE_FILES)))
        os.replace(stage, final)
    pointer = {"schema_version": "SF-DFAM39-CROSSWALK-CURRENT-1.0.0", "status": status,
               "attempt_id": attempt_id, "state_root_relative": str(final.relative_to(root)),
               "state_manifest_sha256": sha256_file(final / "STATE_MANIFEST.sha256")}
    verify_state(root, cfg, pointer)
    atomic_json(preview / "CURRENT_STATE.json", pointer)
    verify_state(root, cfg)


def verify_state(root: Path, cfg: dict, pointer: dict | None = None) -> dict:
    preview = root / cfg["preview_root"]
    pointer = pointer or json.loads((preview / "CURRENT_STATE.json").read_text(encoding="utf-8"))
    state = root / pointer["state_root_relative"]
    if state.parent != preview / "states" or state.is_symlink() or not state.is_dir():
        raise IntegrityFailure("STATE_POINTER_PATH")
    actual = {path.name for path in state.iterdir() if path.is_file() and not path.is_symlink()}
    if actual != STATE_FILES | {"STATE_MANIFEST.sha256"} or any(not path.is_file() or path.is_symlink()
                                                                  for path in state.iterdir()):
        raise IntegrityFailure("STATE_EXACT_FILE_SET")
    manifest = state / "STATE_MANIFEST.sha256"
    if sha256_file(manifest) != pointer["state_manifest_sha256"]:
        raise IntegrityFailure("STATE_MANIFEST_POINTER_HASH")
    entries = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if name in entries or name not in STATE_FILES:
            raise IntegrityFailure("STATE_MANIFEST_PATH_SCHEMA")
        entries[name] = digest
    if set(entries) != STATE_FILES:
        raise IntegrityFailure("STATE_MANIFEST_EXACT_SET")
    for name, digest in entries.items():
        if sha256_file(state / name) != digest:
            raise IntegrityFailure(f"STATE_HASH_DRIFT:{name}")
    terminal = json.loads((state / "TERMINAL_STATE.json").read_text(encoding="utf-8"))
    if terminal["status"] != pointer["status"] or terminal["attempt_id"] != pointer["attempt_id"]:
        raise IntegrityFailure("STATE_POINTER_TERMINAL_MISMATCH")
    return {"state": state, "pointer": pointer, "terminal": terminal,
            "metrics": json.loads((state / "metrics.json").read_text(encoding="utf-8")),
            "input_manifest": json.loads((state / "input_manifest.json").read_text(encoding="utf-8")),
            "static_contract": json.loads((state / "static_contract.json").read_text(encoding="utf-8"))}


def failure_state(root: Path, cfg: dict, attempt: str, status: str, error: str) -> tuple[str, dict]:
    current = verify_state(root, cfg)
    metrics = {"profile": cfg["profile"], "status": status, "primary_metric": 0.0,
               "semantic_success": False, "scientific_audit_executed": 0, "error": error,
               **authorization_flags()}
    report = {"exp_id": cfg["exp_id"], "status": status, "semantic_success": False,
              "answer": "NOT_ESTABLISHED", "error": error}
    publish_state(root, cfg, status, attempt, metrics, report, current["input_manifest"], current["static_contract"])
    return status, metrics


def static_preview(root: Path, cfg: dict) -> None:
    audit = validate_pinned_inputs(root, cfg)
    preview = root / cfg["preview_root"]
    (preview / "logs").mkdir(parents=True, exist_ok=True)
    atomic_json(preview / "logs/.slurm_parent_precreated.json",
                {"root_relative_log_dir": cfg["slurm_log_dir"], "precreated": True})
    static = {"schema_version": "SF-DFAM39-CROSSWALK-STATIC-1.0.0",
              "package_hashes": package_hashes(root, cfg), "input_contract": audit,
              "formal_slurm_required": True, "formal_audit_executed": False, "gpus": 0}
    metrics = {"profile": cfg["profile"], "status": "IMPLEMENTED_NOT_RUN", "primary_metric": 0.0,
               "semantic_success": False, "scientific_audit_executed": 0, **authorization_flags()}
    publish_state(root, cfg, "IMPLEMENTED_NOT_RUN", "static-preview", metrics,
                  {"exp_id": cfg["exp_id"], "status": "IMPLEMENTED_NOT_RUN", "answer": "NOT_RUN"},
                  static, static)


def formal_run(root: Path, cfg: dict, attempt: str) -> tuple[str, dict]:
    job = os.environ.get("SLURM_JOB_ID", "")
    if not job.isdigit() or int(job) <= 0:
        raise IntegrityFailure("FORMAL_SLURM_GUARD")
    resource_audit = validate_formal_resources(cfg)
    gate_path = root / cfg["code_review_gate_path"]
    if not gate_path.is_file():
        raise IntegrityFailure("CODE_REVIEW_GATE_MISSING")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("verdict") not in {"PASS", "PASS_WITH_WARNINGS"}:
        raise IntegrityFailure("CODE_REVIEW_GATE_NOT_PASS")
    submission_audit = validate_reviewed_submission(root, cfg, gate)
    preview = root / cfg["preview_root"]
    attempts = preview / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    final, stage = attempts / attempt, attempts / f"{attempt}.tmp"
    if final.exists() or stage.exists():
        raise IntegrityFailure("DIRTY_ATTEMPT_REFUSED")
    input_audit = validate_pinned_inputs(root, cfg)
    env = environment_snapshot()
    input_manifest = {"package_hashes": package_hashes(root, cfg), "input_contract": input_audit,
                      "code_review_gate_root_relative": cfg["code_review_gate_path"],
                      "code_review_gate_sha256": sha256_file(gate_path),
                      "environment": env, "resource_audit": resource_audit,
                      "submission_audit": submission_audit,
                      "slurm_job_id": job, "gpus": 0}
    publish_state(root, cfg, "FORMAL_RUNNING", attempt,
                  {"profile": cfg["profile"], "status": "FORMAL_RUNNING", "primary_metric": 0.0,
                   "semantic_success": False, **authorization_flags()},
                  {"exp_id": cfg["exp_id"], "status": "FORMAL_RUNNING"}, input_manifest, input_manifest)
    stage.mkdir()
    try:
        records, embl_audit = parse_curated_embl(root / input_audit["source_root_relative"], cfg)
        candidates, resolution, crosswalk_audit = build_crosswalk(input_audit["targets"], records)
        species_audit, conflict_audit, label_conflicts = build_postjoin_audits(input_audit["targets"], resolution)
        status, metrics, report = semantic_result(cfg, input_audit, embl_audit, candidates,
                                                  resolution, crosswalk_audit, label_conflicts)
        write_tsv(stage / "authoritative_candidates.tsv", candidates,
                  ["identifier", "relation_field", "relation_database", "official_alias_exact", "accession",
                   "version", "versioned_accession", "canonical_name", "consensus_sha256", "consensus_length"])
        write_tsv(stage / "identity_resolution.tsv", resolution,
                  ["identifier", "occurrences", "candidate_row_count",
                   "distinct_identity_count", "resolution_status", "versioned_accession", "canonical_name",
                   "consensus_sha256", "detail"])
        write_tsv(stage / "species_audit.tsv", species_audit, ["identifier", "species"])
        write_tsv(stage / "label_conflict_audit.tsv", conflict_audit,
                  ["versioned_accession", "consensus_sha256", "identifiers", "direct_labels", "label_conflict"])
        write_tsv(stage / "frozen_targets.tsv", input_audit["targets"],
                  ["identifier", "occurrences", "labels", "species", "status", "resolution_status", "resolution_method"])
        write_tsv(stage / "label_contract_excluded.tsv", input_audit["excluded"],
                  ["identifier", "occurrences", "raw_classes", "species", "labeler_state", "status"])
        write_tsv(stage / "x13_audit_only.tsv", input_audit["x13"], list(input_audit["x13"][0]))
        atomic_json(stage / "metrics.json", metrics)
        atomic_json(stage / "report.json", report)
        atomic_json(stage / "SOURCE_MANIFEST.json",
                    {"source_contract": cfg["source_contract"], "curated_embl": cfg["curated_embl"],
                     "md5_sidecar": cfg["md5_sidecar"], "release_notes": cfg["release_notes"],
                     "embl_audit": embl_audit})
        atomic_json(stage / "RUN_MANIFEST.json", {"attempt_id": attempt, "slurm_job_id": job,
                    "package_hashes": package_hashes(root, cfg),
                    "code_review_gate_sha256": sha256_file(gate_path),
                    "resource_audit": resource_audit, "submission_audit": submission_audit, "gpus": 0})
        atomic_json(stage / "env.json", env)
        atomic_json(stage / "OUTPUT_INDEX.json", {"attempt_root_relative": str(final.relative_to(root)),
                    "canonical_pointer": f"{cfg['preview_root']}/CURRENT_STATE.json",
                    "payload_manifest": str((final / "PAYLOAD_MANIFEST.json").relative_to(root))})
        create_payload_manifest(stage)
        verify_payload(stage)
        os.replace(stage, final)
        verify_payload(final)
        validate_pinned_inputs(root, cfg)
        publish_state(root, cfg, status, attempt, metrics, report, input_manifest, input_manifest,
                      (final / "PAYLOAD_MANIFEST.json",))
        return status, metrics
    except Exception:
        if stage.exists():
            atomic_json(stage / "failure.json", {"traceback": traceback.format_exc()})
        raise


def terminal_exit_code(status: str) -> int:
    if status in {"IMPLEMENTED_NOT_RUN", "IDENTITY_SOURCE_TYPED_BLOCK", "CROSSWALK_RECOVERY_COMPLETE"}:
        return 0
    return 70 if status == "AUDIT_FAILED_RESOURCE" else 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--attempt-id", default="static-preview")
    parser.add_argument("--static-check-only", action="store_true")
    parser.add_argument("--record-wrapper-failure", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"])
    if args.record_wrapper_failure:
        current = verify_state(root, cfg)
        if (current["pointer"]["attempt_id"] == args.attempt_id
                and current["pointer"]["status"] in {"AUDIT_FAILED_INTEGRITY", "AUDIT_FAILED_RESOURCE"}):
            status = current["pointer"]["status"]
        else:
            status, _ = failure_state(root, cfg, args.attempt_id, "AUDIT_FAILED_INTEGRITY",
                                      "SBATCH_WRAPPER_OR_TEST_FAILURE")
        print(json.dumps({"status": status, "gpus": 0}, sort_keys=True))
        raise SystemExit(2)
    if args.static_check_only:
        static_preview(root, cfg)
        print(json.dumps({"status": "IMPLEMENTED_NOT_RUN", "gpus": 0}, sort_keys=True))
        return
    try:
        status, _metrics = formal_run(root, cfg, args.attempt_id)
    except ResourceFailure as exc:
        status, _metrics = failure_state(root, cfg, args.attempt_id, "AUDIT_FAILED_RESOURCE",
                                         f"{type(exc).__name__}:{exc}")
    except Exception as exc:
        status, _metrics = failure_state(root, cfg, args.attempt_id, "AUDIT_FAILED_INTEGRITY",
                                         f"{type(exc).__name__}:{exc}")
    print(json.dumps({"status": status, "gpus": 0}, sort_keys=True))
    raise SystemExit(terminal_exit_code(status))


if __name__ == "__main__":
    main()
