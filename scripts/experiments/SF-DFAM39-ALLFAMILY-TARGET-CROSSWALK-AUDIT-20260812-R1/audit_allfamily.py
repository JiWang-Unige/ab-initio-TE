#!/usr/bin/env python3
"""Target-only streaming audit of the frozen Dfam 3.9 all-family EMBL export."""
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
import stat
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath


class IntegrityFailure(RuntimeError):
    pass


class ResourceFailure(RuntimeError):
    pass


AUTHORIZATION = {"full_catalog_stage_authorized": False, "homology_split_authorized": False,
                 "data_stage_authorized": False, "gpu_authorized": False, "s1_authorized": False}
ALIAS_FIELDS = ("NM", "PI", "SN", "DR")
IUPAC = set("ACGTRYSWKMBDHVN")
ID_RE = re.compile(r"^((?:DF|DR)[0-9]+); SV ([0-9]+); .*; ([0-9]+) BP\.$")
ACCESSION_TARGET_RE = re.compile(r"^(?:DF|DR)[0-9]+(?:\.[0-9]+)?$")


def hash_file(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def safe_path(root: Path, relative: str) -> Path:
    rel = PurePosixPath(relative)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        raise IntegrityFailure(f"UNSAFE_ROOT_RELATIVE_PATH:{relative}")
    return root.joinpath(*rel.parts)


def verify_file(root: Path, relative: str, digest: str, size: int | None = None) -> Path:
    path = safe_path(root, relative)
    if not path.is_file() or path.is_symlink() or hash_file(path) != digest:
        raise IntegrityFailure(f"PINNED_FILE_DRIFT:{relative}")
    if size is not None and path.stat().st_size != int(size):
        raise IntegrityFailure(f"PINNED_FILE_SIZE_DRIFT:{relative}")
    return path


def package_hashes(root: Path, cfg: dict) -> dict[str, str]:
    exp = cfg["exp_id"]
    relatives = [f"configs/{exp}.yaml", f"scripts/experiments/{exp}/audit_allfamily.py",
                 f"scripts/experiments/{exp}/test_audit_allfamily.py", f"sbatch/{exp}.sbatch",
                 cfg["experiment_doc_path"]]
    return {relative: hash_file(safe_path(root, relative)) for relative in relatives}


def exact_stat(path: Path) -> dict[str, int]:
    value = path.stat()
    return {"st_dev": value.st_dev, "st_ino": value.st_ino, "st_size": value.st_size,
            "st_mtime_ns": value.st_mtime_ns, "st_mode": stat.S_IMODE(value.st_mode)}


def verify_source_topology(root: Path, cfg: dict) -> tuple[Path, dict]:
    full = cfg["full_embl"]
    source = safe_path(root, full["path"])
    if not source.is_file() or source.is_symlink() or source.stat().st_size != full["size_bytes"]:
        raise IntegrityFailure("FULL_SOURCE_TOPOLOGY_OR_SIZE_DRIFT")
    sidecar = verify_file(root, full["md5_sidecar_path"], full["md5_sidecar_sha256"])
    manifest_path = verify_file(root, full["source_manifest_path"], full["source_manifest_sha256"])
    if full["md5"] not in sidecar.read_text(encoding="utf-8"):
        raise IntegrityFailure("FULL_MD5_SIDECAR_CONTENT_DRIFT")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {"schema_version", "release", "license", "compressed_size_bytes", "md5", "sha256",
                "gzip_crc_test", "authorization"}
    if not required <= set(manifest) or manifest["schema_version"] != full["source_manifest_schema"]:
        raise IntegrityFailure("FULL_SOURCE_MANIFEST_SCHEMA")
    if (manifest["release"] != cfg["source_contract"]["release"]
            or manifest["license"] != cfg["source_contract"]["license"]
            or manifest["compressed_size_bytes"] != full["size_bytes"]
            or manifest["md5"] != full["md5"] or manifest["sha256"] != full["sha256"]
            or manifest["gzip_crc_test"] != "PASS"):
        raise IntegrityFailure("FULL_SOURCE_MANIFEST_IDENTITY_DRIFT")
    expected_auth = {"curated_crosswalk_override": False, "raw_dr_support_only": True,
                     "homology_split_authorized": False, "data_stage_authorized": False,
                     "gpu_authorized": False, "s1_authorized": False}
    if manifest["authorization"] != expected_auth:
        raise IntegrityFailure("FULL_SOURCE_MANIFEST_AUTHORIZATION_DRIFT")
    return source, {"source_stat": exact_stat(source), "source_manifest": manifest,
                    "source_root_relative": full["path"]}


def verify_payload_manifest(attempt: Path, expected_sha: str) -> None:
    path = attempt / "PAYLOAD_MANIFEST.json"
    if hash_file(path) != expected_sha:
        raise IntegrityFailure("CURATED_PAYLOAD_MANIFEST_PIN_DRIFT")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if set(manifest) != {"schema_version", "self_included", "files"} or manifest["self_included"] is not False:
        raise IntegrityFailure("CURATED_PAYLOAD_MANIFEST_SCHEMA")
    actual = {member.name for member in attempt.iterdir() if member.is_file() and not member.is_symlink()}
    if actual != set(manifest["files"]) | {"PAYLOAD_MANIFEST.json"} or any(
            not member.is_file() or member.is_symlink() for member in attempt.iterdir()):
        raise IntegrityFailure("CURATED_PAYLOAD_EXACT_FILE_SET")
    for name, digest in manifest["files"].items():
        candidate = attempt / name
        if not candidate.is_file() or candidate.is_symlink() or hash_file(candidate) != digest:
            raise IntegrityFailure(f"CURATED_PAYLOAD_MEMBER_DRIFT:{name}")


def load_frozen_inputs(root: Path, cfg: dict) -> dict:
    frozen = cfg["curated_job11527999"]
    attempt = safe_path(root, frozen["attempt_root"])
    verify_payload_manifest(attempt, frozen["payload_manifest_sha256"])
    named = {"candidates": ("authoritative_candidates.tsv", frozen["candidates_sha256"]),
             "resolution": ("identity_resolution.tsv", frozen["resolution_sha256"]),
             "metrics": ("metrics.json", frozen["metrics_sha256"]),
             "targets": ("frozen_targets.tsv", frozen["targets_sha256"]),
             "excluded": ("label_contract_excluded.tsv", frozen["excluded_sha256"]),
             "x13": ("x13_audit_only.tsv", frozen["x13_sha256"])}
    paths = {}
    for key, (name, digest) in named.items():
        path = attempt / name
        if not path.is_file() or path.is_symlink() or hash_file(path) != digest:
            raise IntegrityFailure(f"CURATED_INPUT_DRIFT:{name}")
        paths[key] = path
    contracts = cfg["frozen_contracts"]
    verify_file(root, contracts["direct_labeler_path"], contracts["direct_labeler_sha256"])
    verify_file(root, contracts["evaluator_contract_path"], contracts["evaluator_contract_sha256"])
    candidates, resolution = read_tsv(paths["candidates"]), read_tsv(paths["resolution"])
    targets, excluded, x13 = read_tsv(paths["targets"]), read_tsv(paths["excluded"]), read_tsv(paths["x13"])
    metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))
    target_ids = {row["identifier"] for row in targets}
    if (len(targets) != frozen["target_identifier_count"] or len(target_ids) != len(targets)
            or sum(int(row["occurrences"]) for row in targets) != frozen["target_occurrence_mass"]
            or len(resolution) != len(targets)
            or {row["identifier"] for row in resolution} != target_ids):
        raise IntegrityFailure("CURATED_DENOMINATOR_OR_CONSERVATION_DRIFT")
    if (metrics.get("resolved_unique_identifier_count") != frozen["curated_resolved_unique_count"]
            or metrics.get("ambiguous_identifier_count") != frozen["curated_ambiguous_count"]
            or sorted(row["identifier"] for row in resolution if row["resolution_status"] == "ambiguous")
            != sorted(frozen["curated_ambiguous_identifiers"])):
        raise IntegrityFailure("CURATED_SCIENTIFIC_PAYLOAD_DRIFT")
    denominator = cfg["denominator"]
    if (len(excluded) != denominator["u_ignore_identifier_count"]
            or sum(int(row["occurrences"]) for row in excluded) != denominator["u_ignore_occurrence_mass"]
            or any(row["labeler_state"] != "U" for row in excluded)
            or len(x13) != 1 or x13[0]["identifier"] != denominator["x13_identifier"]
            or int(x13[0]["occurrences"]) != denominator["x13_occurrence_mass"]
            or target_ids & {row["identifier"] for row in excluded}
            or denominator["x13_identifier"] in target_ids):
        raise IntegrityFailure("LABEL_CONTRACT_STRATA_DRIFT")
    if cfg["authorization"] != AUTHORIZATION:
        raise IntegrityFailure("AUTHORIZATION_MUST_REMAIN_FALSE")
    return {"attempt_root_relative": frozen["attempt_root"], "candidates": candidates,
            "resolution": resolution, "targets": targets, "excluded": excluded, "x13": x13,
            "curated_metrics": metrics, "target_identifier_count": len(targets),
            "target_occurrence_mass": sum(int(row["occurrences"]) for row in targets), **AUTHORIZATION}


def hash_compressed_source(path: Path, cfg: dict, expected_stat: dict) -> dict:
    sha, md5, byte_count = hashlib.sha256(), hashlib.md5(), 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            sha.update(block); md5.update(block); byte_count += len(block)
    observed = {"sha256": sha.hexdigest(), "md5": md5.hexdigest(), "size_bytes": byte_count}
    expected = cfg["full_embl"]
    if observed != {"sha256": expected["sha256"], "md5": expected["md5"],
                    "size_bytes": expected["size_bytes"]}:
        raise IntegrityFailure(f"FULL_SOURCE_CONTENT_HASH_DRIFT:{observed}")
    if exact_stat(path) != expected_stat:
        raise IntegrityFailure("FULL_SOURCE_STAT_DRIFT_DURING_HASH")
    return observed


def parse_alias_line(field: str, value: str) -> tuple[list[tuple[str, str]], str]:
    """Return exact (token,database) pairs and the field-specific terminator symbol."""
    value = value.strip()
    if field in {"NM", "SN"}:
        if not value:
            raise IntegrityFailure(f"EMPTY_SINGLE_ALIAS:{field}")
        return [(value, "Dfam")], "none"
    if field == "PI":
        if not value or not value.endswith(";"):
            raise IntegrityFailure(f"PI_FIELD_SCHEMA:{value}")
        pieces = value[:-1].split(";")
        tokens = [piece.strip() for piece in pieces]
        if not tokens or any(not token for token in tokens):
            raise IntegrityFailure(f"PI_EMPTY_OR_MALFORMED_TOKEN:{value}")
        return [(token, "Dfam") for token in tokens], "semicolon"
    if field == "DR":
        if not value or value[-1] not in ";.":
            raise IntegrityFailure(f"DR_TERMINATOR_SCHEMA:{value}")
        terminator = "semicolon" if value[-1] == ";" else "period"
        body = value[:-1]
        if body.count(";") != 1:
            raise IntegrityFailure(f"DR_FIELD_SCHEMA:{value}")
        database, primary = (part.strip() for part in body.split(";", 1))
        if not database or not primary:
            raise IntegrityFailure(f"DR_EMPTY_DATABASE_OR_PRIMARY:{value}")
        return [(primary, database)], terminator
    raise IntegrityFailure(f"UNSUPPORTED_ALIAS_FIELD:{field}")


def parse_ac_value(value: str) -> str:
    value = value.strip()
    if not value.endswith(";") or value[:-1].count(";") or not value[:-1].strip():
        raise IntegrityFailure(f"AC_FIELD_SCHEMA:{value}")
    return value[:-1].strip()


def stream_target_candidates(path: Path, targets: list[dict], max_candidates: int) -> tuple[list[dict], dict]:
    """One decompression pass; retains one current record plus target-hit candidate rows only."""
    target_ids = {row["identifier"] for row in targets}
    accession_targets = {value for value in target_ids if ACCESSION_TARGET_RE.fullmatch(value)}
    candidates: list[dict] = []
    current = None
    sequence_parts: list[str] = []
    in_sequence = False
    counts = Counter()
    relation_counts = {tier: {field: {"line_count": 0, "token_count": 0,
                                      "terminator_count": 0,
                                      "terminator_counts_by_symbol": {"semicolon": 0, "period": 0, "none": 0},
                                      "target_hit_count": 0}
                              for field in ALIAS_FIELDS}
                       for tier in ("DF", "DR")}
    max_retained_relations = 0

    def add_hit(field: str, database: str, alias: str) -> None:
        nonlocal max_retained_relations
        if alias in target_ids:
            key = (field, database, alias)
            if key not in current["hit_relations"]:
                current["hit_relations"].add(key)
                max_retained_relations = max(max_retained_relations, len(current["hit_relations"]))

    def finish() -> None:
        nonlocal current, sequence_parts, in_sequence
        if current is None:
            return
        counts["terminated_records"] += 1
        if current["hit_relations"]:
            normalized = "".join(sequence_parts).upper().replace("U", "T")
            if not normalized or set(normalized) - IUPAC or len(normalized) != current["declared_length"]:
                raise IntegrityFailure(f"TARGET_RECORD_SEQUENCE_INVALID:{current['accession']}")
            consensus_sha = hashlib.sha256(normalized.encode("ascii")).hexdigest()
            tier = "DF_CURATED" if current["accession"].startswith("DF") else "RAW_DR"
            evidence = "CURATED_RECONCILE" if tier == "DF_CURATED" else "RAW_ONLY_SUPPORT"
            for field, database, alias in sorted(current["hit_relations"]):
                candidates.append({"identifier": alias, "relation_field": field,
                    "relation_database": database, "official_alias_exact": alias,
                    "accession": current["accession"], "version": current["version"],
                    "versioned_accession": f"{current['accession']}.{current['version']}",
                    "canonical_name": current["canonical_name"], "consensus_sha256": consensus_sha,
                    "consensus_length": len(normalized), "source_tier": tier,
                    "evidence_status": evidence})
                if len(candidates) > max_candidates:
                    raise ResourceFailure("TARGET_CANDIDATE_ROW_BOUND_EXCEEDED")
        current, sequence_parts, in_sequence = None, [], False

    try:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            for raw in handle:
                line = raw.rstrip("\r\n")
                if line.startswith("ID   "):
                    if current is not None:
                        raise IntegrityFailure("RECORD_MISSING_TERMINATOR")
                    match = ID_RE.match(line[5:])
                    if not match:
                        raise IntegrityFailure(f"ID_FIELD_SCHEMA:{line[:160]}")
                    accession, version, length = match.group(1), int(match.group(2)), int(match.group(3))
                    counts["records"] += 1
                    counts["df_records" if accession.startswith("DF") else "dr_records"] += 1
                    current = {"accession": accession, "version": version, "declared_length": length,
                               "canonical_name": "", "ac": "", "hit_relations": set()}
                    if accession in accession_targets:
                        add_hit("AC", "Dfam_identity", accession)
                    versioned = f"{accession}.{version}"
                    if versioned in accession_targets:
                        add_hit("ID", "Dfam_identity", versioned)
                    continue
                if current is None:
                    continue
                if line == "//":
                    finish(); continue
                if in_sequence:
                    if current["hit_relations"]:
                        letters = "".join(character for character in line if character.isalpha())
                        if letters:
                            sequence_parts.append(letters)
                    continue
                field = line[:2] if len(line) >= 5 and line[2:5] == "   " else ""
                value = line[5:] if field else ""
                if field in ALIAS_FIELDS:
                    relations, terminator = parse_alias_line(field, value)
                    tier = "DF" if current["accession"].startswith("DF") else "DR"
                    grammar = relation_counts[tier][field]
                    grammar["line_count"] += 1
                    grammar["token_count"] += len(relations)
                    grammar["terminator_counts_by_symbol"][terminator] += 1
                    if terminator != "none":
                        grammar["terminator_count"] += 1
                    if field == "NM":
                        if current["canonical_name"]:
                            raise IntegrityFailure(f"DUPLICATE_NM:{current['accession']}")
                        current["canonical_name"] = relations[0][0]
                    for alias, database in relations:
                        if alias in target_ids:
                            grammar["target_hit_count"] += 1
                        add_hit(field, database, alias)
                elif field == "AC":
                    alias = parse_ac_value(value)
                    if current["ac"]:
                        raise IntegrityFailure(f"DUPLICATE_AC:{current['accession']}")
                    current["ac"] = alias
                    if alias != current["accession"]:
                        raise IntegrityFailure(f"AC_ID_MISMATCH:{current['accession']}")
                    if alias in accession_targets:
                        add_hit("AC", "Dfam_identity", alias)
                elif field == "SQ":
                    counts["sq_records"] += 1
                    in_sequence = True
    except (gzip.BadGzipFile, EOFError, UnicodeDecodeError, OSError) as exc:
        raise IntegrityFailure(f"GZIP_EOF_CRC_OR_STREAM_FAILURE:{type(exc).__name__}:{exc}") from exc
    if current is not None:
        raise IntegrityFailure("FINAL_RECORD_UNTERMINATED")
    if counts["records"] <= 0 or counts["terminated_records"] != counts["records"]:
        raise IntegrityFailure("FULL_STREAM_RECORD_CONSERVATION")
    candidates.sort(key=lambda row: (row["source_tier"], row["identifier"], row["versioned_accession"],
                                     row["relation_field"], row["relation_database"]))
    telemetry = {"scanned_record_count": counts["records"], "scanned_df_record_count": counts["df_records"],
                 "scanned_dr_record_count": counts["dr_records"], "sq_record_count": counts["sq_records"],
                 "retained_target_candidate_row_count": len(candidates),
                 "max_retained_relations_in_one_record": max_retained_relations,
                 "relation_grammar_counts": relation_counts,
                 "full_catalog_materialized": False, "gzip_eof_crc_verified_by_complete_read": True,
                 "single_decompression_pass": True}
    return candidates, telemetry


CURATED_FIELDS = ["identifier", "relation_field", "relation_database", "official_alias_exact", "accession",
                  "version", "versioned_accession", "canonical_name", "consensus_sha256", "consensus_length"]


def canonical_curated_rows(rows: list[dict]) -> list[dict[str, str]]:
    return sorted(({field: str(row[field]) for field in CURATED_FIELDS} for row in rows),
                  key=lambda row: tuple(row[field] for field in CURATED_FIELDS))


def reconcile_curated_df(full_candidates: list[dict], curated_candidates: list[dict]) -> dict:
    observed = canonical_curated_rows([row for row in full_candidates if row["source_tier"] == "DF_CURATED"])
    expected = canonical_curated_rows(curated_candidates)
    if observed != expected:
        observed_set = {stable_json(row) for row in observed}; expected_set = {stable_json(row) for row in expected}
        raise IntegrityFailure(f"DF_CURATED_RECONCILIATION_MISMATCH:missing={len(expected_set-observed_set)}:extra={len(observed_set-expected_set)}")
    payload = stable_json(expected)
    return {"df_curated_candidate_row_count": len(observed), "curated_reconciliation_exact": True,
            "df_curated_candidate_semantic_sha256": hashlib.sha256(payload.encode()).hexdigest()}


def layered_resolution(frozen: dict, candidates: list[dict]) -> tuple[list[dict], dict]:
    raw_by_id = defaultdict(list)
    for row in candidates:
        if row["source_tier"] == "RAW_DR":
            raw_by_id[row["identifier"]].append(row)
    output, counts, mass = [], Counter(), Counter()
    for curated in sorted(frozen["resolution"], key=lambda row: row["identifier"]):
        identifier = curated["identifier"]
        raw = raw_by_id[identifier]
        raw_identities = {(row["versioned_accession"], row["consensus_sha256"]) for row in raw}
        original = curated["resolution_status"]
        if original == "resolved_unique":
            layered = "CURATED_RESOLVED_UNCHANGED"
        elif original == "ambiguous":
            layered = "CURATED_AMBIGUOUS_UNCHANGED"
        elif raw:
            layered = "RAW_ONLY_SUPPORT"
        else:
            layered = "MISSING"
        row = {"identifier": identifier, "occurrences": int(curated["occurrences"]),
               "curated_resolution_status": original, "layered_status": layered,
               "curated_versioned_accession": curated["versioned_accession"],
               "curated_consensus_sha256": curated["consensus_sha256"],
               "raw_candidate_row_count": len(raw), "raw_distinct_identity_count": len(raw_identities),
               "raw_evidence_semantics": "RAW_ONLY_SUPPORT" if raw else "NONE",
               "authoritative_resolution_changed": False}
        output.append(row); counts[layered] += 1; mass[layered] += row["occurrences"]
    audit = {"layered_status_identifier_counts": dict(counts), "layered_status_occurrence_mass": dict(mass),
             "identifier_conservation_delta": len(output) - frozen["target_identifier_count"],
             "occurrence_conservation_delta": sum(row["occurrences"] for row in output)
                                              - frozen["target_occurrence_mass"],
             "curated_resolved_overridden_count": 0, "curated_ambiguity_resolved_by_raw_count": 0,
             "raw_only_support_identifier_count": counts["RAW_ONLY_SUPPORT"]}
    if audit["identifier_conservation_delta"] or audit["occurrence_conservation_delta"]:
        raise IntegrityFailure("LAYERED_RESOLUTION_CONSERVATION")
    return output, audit


def postjoin_audits(targets: list[dict], resolution: list[dict]) -> tuple[list[dict], list[dict]]:
    by_id = {row["identifier"]: row for row in targets}
    species = [{"identifier": row["identifier"], "species": by_id[row["identifier"]]["species"]}
               for row in resolution]
    labels = [{"identifier": row["identifier"], "direct_labels": by_id[row["identifier"]]["labels"],
               "layered_status": row["layered_status"]} for row in resolution]
    return species, labels


def semantic_result(cfg: dict, frozen: dict, source_audit: dict, scan: dict, reconciliation: dict,
                    resolution_audit: dict) -> tuple[str, dict, dict]:
    status = "ALLFAMILY_TARGET_CROSSWALK_TYPED_BLOCK"
    metrics = {"profile": cfg["profile"], "status": status, "primary_metric":
               frozen["curated_metrics"]["resolved_unique_identifier_count"] / frozen["target_identifier_count"],
               "semantic_success": True, "valid_negative": True, "claim_eligible": False,
               "scientific_audit_executed": 1, "target_identifier_count": frozen["target_identifier_count"],
               "target_occurrence_mass": frozen["target_occurrence_mass"],
               "curated_resolved_unique_identifier_count": frozen["curated_metrics"]["resolved_unique_identifier_count"],
               "curated_ambiguous_identifier_count": frozen["curated_metrics"]["ambiguous_identifier_count"],
               "curated_missing_identifier_count": frozen["curated_metrics"]["missing_identifier_count"],
               **scan, **reconciliation, **resolution_audit, **AUTHORIZATION}
    if not all(math.isfinite(float(value)) for value in metrics.values() if isinstance(value, (int, float))):
        raise IntegrityFailure("NONFINITE_METRIC")
    report = {"schema_version": "SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-REPORT-1.0.0",
              "exp_id": cfg["exp_id"], "status": status, "semantic_success": True,
              "answer": "COMPLETE_SCAN_BUT_INSUFFICIENT_AUTHORITATIVE_CROSSWALK",
              "df_semantics": "exact reconciliation only", "dr_semantics": "RAW_ONLY_SUPPORT",
              "source_audit": source_audit, "metrics": metrics, "authorization": AUTHORIZATION}
    return status, metrics, report


def source_manifest_payload(cfg: dict, source_audit: dict, scan: dict) -> dict:
    counts = scan.get("relation_grammar_counts")
    if not isinstance(counts, dict) or set(counts) != {"DF", "DR"} or any(
            set(counts[tier]) != set(ALIAS_FIELDS) for tier in ("DF", "DR")):
        raise IntegrityFailure("RELATION_GRAMMAR_COUNTS_SCHEMA")
    return {"source_contract": cfg["source_contract"], "full_embl": cfg["full_embl"],
            "source_audit": source_audit, "relation_grammar_counts": counts}


def parse_memory_mib(value: str) -> int:
    match = re.fullmatch(r"([1-9][0-9]*)([KkMmGgTt]?)", value.strip())
    if not match:
        raise ResourceFailure(f"SLURM_MEM_PER_NODE_FORMAT:{value}")
    amount, suffix = int(match.group(1)), match.group(2).upper()
    multiplier = {"": 1, "K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}[suffix]
    return int(amount * multiplier)


def validate_resources(cfg: dict) -> dict:
    contract = cfg["resource_contract"]
    cpus = os.environ.get("SLURM_CPUS_PER_TASK", "")
    memory = os.environ.get("SLURM_MEM_PER_NODE", "")
    gpu_vars = {key: os.environ.get(key, "") for key in ("SLURM_JOB_GPUS", "SLURM_GPUS_ON_NODE")}
    if not cpus.isdigit() or int(cpus) != contract["cpus"]:
        raise ResourceFailure(f"CPU_RESOURCE_CONTRACT:{cpus}")
    if parse_memory_mib(memory) != contract["memory_mib"]:
        raise ResourceFailure(f"MEMORY_RESOURCE_CONTRACT:{memory}")
    if contract["gpus"] != 0 or any(value.strip().lower() not in {"", "none", "n/a", "(null)"}
                                     for value in gpu_vars.values()):
        raise ResourceFailure(f"GPU_RESOURCE_CONTRACT:{gpu_vars}")
    return {"cpus": int(cpus), "memory_mib": parse_memory_mib(memory), "gpus": 0,
            "walltime_minutes_from_reviewed_sbatch": contract["walltime_minutes"],
            "sbatch_cli_resource_overrides_prohibited": True}


def validate_review_gate(root: Path, cfg: dict) -> tuple[Path, dict]:
    gate_path = safe_path(root, cfg["code_review_gate_path"])
    if not gate_path.is_file() or gate_path.is_symlink():
        raise IntegrityFailure("CODE_REVIEW_GATE_MISSING")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("verdict") not in {"PASS", "PASS_WITH_WARNINGS"}:
        raise IntegrityFailure("CODE_REVIEW_GATE_NOT_PASS")
    current_package = package_hashes(root, cfg)
    reviewed_files = gate.get("reviewed_files", {})
    if any(reviewed_files.get(relative) != digest for relative, digest in current_package.items()):
        raise IntegrityFailure("REVIEWED_PACKAGE_BINDING_MISSING_OR_STALE")
    relative = f"sbatch/{cfg['exp_id']}.sbatch"
    sbatch = safe_path(root, relative)
    if reviewed_files.get(relative) != hash_file(sbatch):
        raise IntegrityFailure("REVIEWED_SBATCH_BINDING_MISSING_OR_STALE")
    return gate_path, {"authorized_command": f"sbatch {relative}",
                       "cli_resource_overrides_prohibited": True,
                       "reviewed_sbatch_sha256": hash_file(sbatch)}


def environment_snapshot() -> dict:
    keys = ("CONDA_DEFAULT_ENV", "CONDA_PREFIX", "SLURM_JOB_ID", "SLURM_CPUS_PER_TASK",
            "SLURM_MEM_PER_NODE", "SLURM_JOB_GPUS", "SLURM_GPUS_ON_NODE")
    return {"python_version": sys.version, "python_executable": sys.executable,
            "platform": platform.platform(), "hostname": socket.gethostname(),
            "selected_environment": {key: os.environ.get(key, "") for key in keys}}


PAYLOAD_REQUIRED = {"SOURCE_MANIFEST.json", "RUN_MANIFEST.json", "env.json", "OUTPUT_INDEX.json",
                    "allfamily_target_candidates.tsv", "identity_resolution.tsv", "species_audit.tsv",
                    "label_audit.tsv", "frozen_targets.tsv", "label_contract_excluded.tsv",
                    "x13_audit_only.tsv", "metrics.json", "report.json"}


def create_payload_manifest(stage: Path) -> None:
    files = {path.name: hash_file(path) for path in sorted(stage.iterdir())
             if path.is_file() and path.name != "PAYLOAD_MANIFEST.json"}
    if set(files) != PAYLOAD_REQUIRED:
        raise IntegrityFailure(f"PAYLOAD_EXACT_SET_BEFORE_MANIFEST:{sorted(set(files)^PAYLOAD_REQUIRED)}")
    atomic_json(stage / "PAYLOAD_MANIFEST.json", {"schema_version": "SF-DFAM39-ALLFAMILY-PAYLOAD-1.0.0",
                                                   "self_included": False, "files": files})


def verify_payload(stage: Path) -> None:
    manifest = json.loads((stage / "PAYLOAD_MANIFEST.json").read_text(encoding="utf-8"))
    if set(manifest) != {"schema_version", "self_included", "files"} or manifest["self_included"] is not False:
        raise IntegrityFailure("PAYLOAD_MANIFEST_SCHEMA")
    actual = {path.name for path in stage.iterdir() if path.is_file() and not path.is_symlink()}
    if actual != set(manifest["files"]) | {"PAYLOAD_MANIFEST.json"} or any(
            not path.is_file() or path.is_symlink() for path in stage.iterdir()):
        raise IntegrityFailure("PAYLOAD_EXACT_FILE_SET")
    for name, digest in manifest["files"].items():
        if hash_file(stage / name) != digest:
            raise IntegrityFailure(f"PAYLOAD_HASH_DRIFT:{name}")


STATE_FILES = {"STATUS", "TERMINAL_STATE.json", "metrics.json", "report.json", "input_manifest.json",
               "static_contract.json", "external_artifacts.json"}


def publish_state(root: Path, cfg: dict, status: str, attempt: str, metrics: dict, report: dict,
                  input_manifest: dict, static_contract: dict, external: tuple[Path, ...] = ()) -> None:
    preview = safe_path(root, cfg["preview_root"]); states = preview / "states"; states.mkdir(parents=True, exist_ok=True)
    terminal = {"schema_version": "SF-DFAM39-ALLFAMILY-TERMINAL-1.0.0", "exp_id": cfg["exp_id"],
                "status": status, "attempt_id": attempt,
                "semantic_success": bool(metrics.get("semantic_success", False)), **AUTHORIZATION}
    artifacts = {"artifacts": [{"root_relative_path": str(path.relative_to(root)), "sha256": hash_file(path)}
                                for path in sorted(external)]}
    docs = {"STATUS": status + "\n", "TERMINAL_STATE.json": terminal, "metrics.json": metrics,
            "report.json": report, "input_manifest.json": input_manifest,
            "static_contract.json": static_contract, "external_artifacts.json": artifacts}
    state_id = hashlib.sha256(stable_json(docs).encode()).hexdigest(); final = states / state_id
    if not final.exists():
        stage = states / f".tmp.{state_id}.{os.getpid()}"; stage.mkdir()
        for name, value in docs.items():
            atomic_text(stage / name, value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + "\n")
        atomic_text(stage / "STATE_MANIFEST.sha256", "".join(
            f"{hash_file(stage/name)}  {name}\n" for name in sorted(STATE_FILES)))
        os.replace(stage, final)
    pointer = {"schema_version": "SF-DFAM39-ALLFAMILY-CURRENT-1.0.0", "status": status,
               "attempt_id": attempt, "state_root_relative": str(final.relative_to(root)),
               "state_manifest_sha256": hash_file(final / "STATE_MANIFEST.sha256")}
    verify_state(root, cfg, pointer); atomic_json(preview / "CURRENT_STATE.json", pointer); verify_state(root, cfg)


def verify_state(root: Path, cfg: dict, pointer: dict | None = None) -> dict:
    preview = safe_path(root, cfg["preview_root"])
    pointer = pointer or json.loads((preview / "CURRENT_STATE.json").read_text(encoding="utf-8"))
    state = safe_path(root, pointer["state_root_relative"])
    if state.parent != preview / "states" or state.is_symlink() or not state.is_dir():
        raise IntegrityFailure("STATE_POINTER_PATH")
    actual = {path.name for path in state.iterdir() if path.is_file() and not path.is_symlink()}
    if actual != STATE_FILES | {"STATE_MANIFEST.sha256"} or any(not p.is_file() or p.is_symlink() for p in state.iterdir()):
        raise IntegrityFailure("STATE_EXACT_FILE_SET")
    manifest = state / "STATE_MANIFEST.sha256"
    if hash_file(manifest) != pointer["state_manifest_sha256"]:
        raise IntegrityFailure("STATE_MANIFEST_POINTER_HASH")
    entries = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if name in entries or name not in STATE_FILES:
            raise IntegrityFailure("STATE_MANIFEST_SCHEMA")
        entries[name] = digest
    if set(entries) != STATE_FILES or any(hash_file(state / name) != digest for name, digest in entries.items()):
        raise IntegrityFailure("STATE_MANIFEST_MEMBER_DRIFT")
    terminal = json.loads((state / "TERMINAL_STATE.json").read_text(encoding="utf-8"))
    if terminal["status"] != pointer["status"] or terminal["attempt_id"] != pointer["attempt_id"]:
        raise IntegrityFailure("STATE_POINTER_TERMINAL_MISMATCH")
    return {"state": state, "pointer": pointer,
            "input_manifest": json.loads((state / "input_manifest.json").read_text()),
            "static_contract": json.loads((state / "static_contract.json").read_text())}


def static_preview(root: Path, cfg: dict) -> None:
    source, topology = verify_source_topology(root, cfg)
    frozen = load_frozen_inputs(root, cfg)
    preview = safe_path(root, cfg["preview_root"]); (preview / "logs").mkdir(parents=True, exist_ok=True)
    atomic_json(preview / "logs/.slurm_parent_precreated.json",
                {"root_relative_log_dir": cfg["slurm_log_dir"], "precreated": True})
    contract = {"schema_version": "SF-DFAM39-ALLFAMILY-STATIC-1.0.0",
                "package_hashes": package_hashes(root, cfg), "source_topology": topology,
                "frozen_denominator": {key: frozen[key] for key in ("target_identifier_count", "target_occurrence_mass")},
                "formal_full_source_read_executed": False, "formal_slurm_required": True, "gpus": 0}
    metrics = {"profile": cfg["profile"], "status": "IMPLEMENTED_NOT_RUN_REPAIR", "primary_metric": 0.0,
               "semantic_success": False, "scientific_audit_executed": 0, **AUTHORIZATION}
    publish_state(root, cfg, "IMPLEMENTED_NOT_RUN_REPAIR", "static-preview-repair", metrics,
                  {"exp_id": cfg["exp_id"], "status": "IMPLEMENTED_NOT_RUN_REPAIR", "answer": "REPAIR_NOT_RUN"},
                  contract, contract)


def failure_state(root: Path, cfg: dict, attempt: str, error: str, resource: bool = False) -> tuple[str, dict]:
    current = verify_state(root, cfg); status = "AUDIT_FAILED_RESOURCE" if resource else "AUDIT_FAILED_INTEGRITY"
    metrics = {"profile": cfg["profile"], "status": status, "primary_metric": 0.0,
               "semantic_success": False, "scientific_audit_executed": 0, "error": error, **AUTHORIZATION}
    report = {"exp_id": cfg["exp_id"], "status": status, "semantic_success": False,
              "answer": "NOT_ESTABLISHED", "error": error}
    publish_state(root, cfg, status, attempt, metrics, report, current["input_manifest"], current["static_contract"])
    return status, metrics


def formal_run(root: Path, cfg: dict, attempt: str) -> tuple[str, dict]:
    job = os.environ.get("SLURM_JOB_ID", "")
    if not job.isdigit() or int(job) <= 0:
        raise IntegrityFailure("FORMAL_SLURM_GUARD")
    resources = validate_resources(cfg); gate_path, submission = validate_review_gate(root, cfg)
    source, topology = verify_source_topology(root, cfg); frozen = load_frozen_inputs(root, cfg)
    preview = safe_path(root, cfg["preview_root"]); attempts = preview / "attempts"; attempts.mkdir(parents=True, exist_ok=True)
    final, stage = attempts / attempt, attempts / f"{attempt}.tmp"
    if final.exists() or stage.exists():
        raise IntegrityFailure("DIRTY_ATTEMPT_REFUSED")
    input_manifest = {"package_hashes": package_hashes(root, cfg), "source_topology": topology,
                      "curated_attempt_root_relative": frozen["attempt_root_relative"],
                      "code_review_gate_sha256": hash_file(gate_path), "resources": resources,
                      "submission": submission, "environment": environment_snapshot(), "slurm_job_id": job}
    publish_state(root, cfg, "FORMAL_RUNNING", attempt,
                  {"profile": cfg["profile"], "status": "FORMAL_RUNNING", "primary_metric": 0.0,
                   "semantic_success": False, **AUTHORIZATION},
                  {"exp_id": cfg["exp_id"], "status": "FORMAL_RUNNING"}, input_manifest, input_manifest)
    stage.mkdir()
    try:
        pre_stat = exact_stat(source)
        compressed = hash_compressed_source(source, cfg, pre_stat)
        candidates, scan = stream_target_candidates(source, frozen["targets"], cfg["full_embl"]["max_target_candidate_rows"])
        post_stat = exact_stat(source)
        if post_stat != pre_stat:
            raise IntegrityFailure("FULL_SOURCE_STAT_DRIFT_DURING_GZIP_SCAN")
        reconciliation = reconcile_curated_df(candidates, frozen["candidates"])
        resolution, resolution_audit = layered_resolution(frozen, candidates)
        species, labels = postjoin_audits(frozen["targets"], resolution)
        source_audit = {"pre_stat": pre_stat, "post_stat": post_stat, "compressed_content": compressed,
                        "gzip_eof_crc_verified": True, **topology}
        status, metrics, report = semantic_result(cfg, frozen, source_audit, scan, reconciliation, resolution_audit)
        write_tsv(stage / "allfamily_target_candidates.tsv", candidates, CURATED_FIELDS + ["source_tier", "evidence_status"])
        write_tsv(stage / "identity_resolution.tsv", resolution,
                  ["identifier", "occurrences", "curated_resolution_status", "layered_status",
                   "curated_versioned_accession", "curated_consensus_sha256", "raw_candidate_row_count",
                   "raw_distinct_identity_count", "raw_evidence_semantics", "authoritative_resolution_changed"])
        write_tsv(stage / "species_audit.tsv", species, ["identifier", "species"])
        write_tsv(stage / "label_audit.tsv", labels, ["identifier", "direct_labels", "layered_status"])
        write_tsv(stage / "frozen_targets.tsv", frozen["targets"], list(frozen["targets"][0]))
        write_tsv(stage / "label_contract_excluded.tsv", frozen["excluded"], list(frozen["excluded"][0]))
        write_tsv(stage / "x13_audit_only.tsv", frozen["x13"], list(frozen["x13"][0]))
        atomic_json(stage / "metrics.json", metrics); atomic_json(stage / "report.json", report)
        atomic_json(stage / "SOURCE_MANIFEST.json", source_manifest_payload(cfg, source_audit, scan))
        atomic_json(stage / "RUN_MANIFEST.json", {"attempt_id": attempt, "slurm_job_id": job,
                    "package_hashes": package_hashes(root, cfg), "code_review_gate_sha256": hash_file(gate_path),
                    "resources": resources, "submission": submission})
        atomic_json(stage / "env.json", environment_snapshot())
        atomic_json(stage / "OUTPUT_INDEX.json", {"attempt_root_relative": str(final.relative_to(root)),
                    "canonical_pointer": f"{cfg['preview_root']}/CURRENT_STATE.json",
                    "payload_manifest": str((final / "PAYLOAD_MANIFEST.json").relative_to(root))})
        create_payload_manifest(stage); verify_payload(stage); os.replace(stage, final); verify_payload(final)
        if exact_stat(source) != pre_stat:
            raise IntegrityFailure("FULL_SOURCE_STAT_DRIFT_BEFORE_POINTER")
        publish_state(root, cfg, status, attempt, metrics, report, input_manifest, input_manifest,
                      (final / "PAYLOAD_MANIFEST.json",))
        return status, metrics
    except Exception:
        if stage.exists():
            atomic_json(stage / "failure.json", {"traceback": traceback.format_exc()})
        raise


def exit_code(status: str) -> int:
    return 0 if status in {"IMPLEMENTED_NOT_RUN", "IMPLEMENTED_NOT_RUN_REPAIR",
                           "ALLFAMILY_TARGET_CROSSWALK_TYPED_BLOCK"} else 2


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--attempt-id", default="static-preview"); parser.add_argument("--static-check-only", action="store_true")
    parser.add_argument("--record-wrapper-failure", action="store_true"); args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8")); root = Path(cfg["project_root"])
    if args.static_check_only:
        static_preview(root, cfg); print(json.dumps({"status": "IMPLEMENTED_NOT_RUN_REPAIR", "gpus": 0})); return
    if args.record_wrapper_failure:
        current = verify_state(root, cfg)
        if (current["pointer"]["attempt_id"] == args.attempt_id
                and current["pointer"]["status"] in {"AUDIT_FAILED_INTEGRITY", "AUDIT_FAILED_RESOURCE"}):
            status = current["pointer"]["status"]
        else:
            status, _ = failure_state(root, cfg, args.attempt_id, "SBATCH_WRAPPER_OR_TEST_FAILURE")
        raise SystemExit(exit_code(status))
    try:
        status, _ = formal_run(root, cfg, args.attempt_id)
    except ResourceFailure as exc:
        status, _ = failure_state(root, cfg, args.attempt_id, f"{type(exc).__name__}:{exc}", True)
    except Exception as exc:
        status, _ = failure_state(root, cfg, args.attempt_id, f"{type(exc).__name__}:{exc}")
    print(json.dumps({"status": status, "gpus": 0}, sort_keys=True)); raise SystemExit(exit_code(status))


if __name__ == "__main__":
    main()
