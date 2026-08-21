#!/usr/bin/env python3
"""Construct a sequence-homology blocked S0 split without changing RM labels."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class DataTypedBlock(RuntimeError):
    """Scientifically valid inability to construct the preregistered split."""

    def __init__(self, code: str, details: dict | None = None):
        super().__init__(code)
        self.code = code
        self.details = details or {}


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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_file(root: Path, relpath: str, expected: str, code: str) -> Path:
    path = root / relpath
    if not path.is_file() or sha256_file(path) != expected:
        raise ValueError(code)
    return path


def validate_static_inputs(root: Path, cfg: dict, verify_canonical_targets: bool = False) -> dict:
    pins = (
        ("s0_config", "s0_config_sha256"), ("s0_labeler", "s0_labeler_sha256"),
        ("species_holdout_manifest", "species_holdout_manifest_sha256"),
        ("identity_config", "identity_config_sha256"), ("identity_evaluator", "identity_evaluator_sha256"),
        ("identity_layout_manifest", "identity_layout_manifest_sha256"),
        ("identity_payload", "identity_payload_sha256"),
        ("identity_identifier_audit", "identity_identifier_audit_sha256"),
        ("identity_excluded_audit", "identity_excluded_audit_sha256"),
        ("canonical_split_manifest", "canonical_split_sha256"),
        ("canonical_snapshot_report", "canonical_snapshot_report_sha256"),
        ("canonical_snapshot_provenance", "canonical_snapshot_provenance_sha256"),
        ("ontology", "ontology_sha256"), ("famdb_rmlib_config", "famdb_rmlib_config_sha256"),
    )
    for path_key, hash_key in pins:
        verify_file(root, cfg[path_key], cfg[hash_key], f"PINNED_INPUT_DRIFT:{path_key}")
    mmseqs = Path(cfg["mmseqs_binary"])
    if not mmseqs.is_file() or sha256_file(mmseqs) != cfg["mmseqs_binary_sha256"]:
        raise ValueError("MMSEQS_BINARY_IDENTITY_MISMATCH")
    version = subprocess.run([str(mmseqs), "version"], check=True, capture_output=True, text=True).stdout.strip()
    if version != cfg["mmseqs_version"]:
        raise ValueError(f"MMSEQS_VERSION_MISMATCH:{version}")
    partition3 = root / cfg["famdb_partition3"]
    if partition3.stat().st_size != int(cfg["famdb_partition3_size_bytes"]):
        raise ValueError("FAMDB_PARTITION3_SIZE_DRIFT")
    identity = load_module("sf_identity_contract_r1", root / cfg["identity_evaluator"])
    identity_cfg = json.loads((root / cfg["identity_config"]).read_text(encoding="utf-8"))
    _layout, layout_summary = identity.validate_dfam_index_layout(root, identity_cfg)
    if layout_summary["name_lookup_skipped_partitions"] != [3]:
        raise ValueError("FAMDB_EXPECTED_ONLY_PARTITION3_WITHOUT_BYNAME")
    payload = json.loads((root / cfg["identity_payload"]).read_text(encoding="utf-8"))
    payload_root = (root / cfg["identity_payload"]).parent
    for relpath, expected in payload.get("files", {}).items():
        if sha256_file(payload_root / relpath) != expected:
            raise ValueError(f"IDENTITY_PAYLOAD_DRIFT:{relpath}")
    s0 = load_module("sf_direct_s0_contract_r2", root / cfg["s0_labeler"])
    s0_cfg = json.loads((root / cfg["s0_config"]).read_text(encoding="utf-8"))
    for key in ("canonical_split_manifest", "canonical_snapshot_report", "canonical_snapshot_provenance", "ontology"):
        if cfg[key] != s0_cfg[key] or cfg[key.replace("manifest", "sha256") if key == "canonical_split_manifest" else key + "_sha256"] != s0_cfg[key.replace("manifest", "sha256") if key == "canonical_split_manifest" else key + "_sha256"]:
            raise ValueError(f"S0_CANONICAL_CONTRACT_DRIFT:{key}")
    canonical_rows = read_tsv(root / cfg["canonical_split_manifest"])
    if len(canonical_rows) != int(cfg["canonical_expected_species_rows"]):
        raise ValueError("CANONICAL_SPECIES_ROW_COUNT_MISMATCH")
    if verify_canonical_targets:
        s0.validate_canonical_targets(root, s0_cfg, canonical_rows)
    holdout_rows = read_tsv(root / cfg["species_holdout_manifest"])
    if {x["species_code"] for x in holdout_rows} != {x["species_code"] for x in canonical_rows}:
        raise ValueError("SPECIES_HOLDOUT_UNIVERSE_MISMATCH")
    fit_orders = {x["order_taxid"] for x in holdout_rows if x["role"] == cfg["split_policy"]["fit_role"]}
    test_orders = {x["order_taxid"] for x in holdout_rows if x["role"] in cfg["split_policy"]["primary_test_roles"]}
    if fit_orders & test_orders:
        raise ValueError("PRIMARY_CLADE_OVERLAP")
    return {"mmseqs_version": version, "layout_manifest_sha256": layout_summary["layout_manifest_sha256"],
            "partition3_only_without_byname": True, "canonical_species_rows": len(canonical_rows),
            "fit_order_taxids": sorted(fit_orders), "primary_test_order_taxids": sorted(test_orders),
            "primary_clade_overlap_count": 0}


def decode_attr(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def family_from_dataset(dataset) -> dict:
    attrs = dataset.attrs
    accession = decode_attr(attrs.get("accession", ""))
    version = attrs.get("version")
    versioned = f"{accession}.{int(version)}" if accession and version is not None else accession
    return {"name": decode_attr(attrs.get("name", "")), "accession": accession,
            "versioned_accession": versioned, "consensus": decode_attr(attrs.get("consensus", ""))}


def iter_family_datasets(families_group):
    """Traverse the frozen accession-bin tree; yielded objects must be HDF5 datasets."""
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
                raise ValueError(f"FAMDB_FAMILY_OBJECT_WRONG_TYPE:{item.name}")


def scan_exact_names_without_index(partition_path: Path, targets: set[str]) -> tuple[dict[str, list[dict]], dict]:
    """Index-independent exact-name scan, used only for the verified indexless leaf."""
    import h5py
    found: dict[str, list[dict]] = defaultdict(list)
    scanned = 0
    with h5py.File(partition_path, "r") as handle:
        if "Lookup/ByName" in handle:
            raise ValueError("INDEX_INDEPENDENT_SCAN_FORBIDDEN_WHEN_BYNAME_PRESENT")
        families = handle.get("Families")
        if not isinstance(families, h5py.Group):
            raise ValueError("FAMDB_FAMILIES_GROUP_MISSING")
        for dataset in iter_family_datasets(families):
            scanned += 1
            item = family_from_dataset(dataset)
            if item["name"] in targets:
                item["h5_path"] = dataset.name
                found[item["name"]].append(item)
    return dict(found), {"partition": 3, "family_datasets_scanned": scanned,
                         "target_count": len(targets), "matched_target_count": len(found),
                         "resolver": "exact_name_attr_index_independent_full_family_metadata_scan"}


def resolve_sequence_sources(root: Path, cfg: dict, identity_rows: list[dict], scan_results: dict[str, list[dict]]) -> tuple[dict, list[dict], set[str]]:
    """Load Dfam consensus by pinned accession, then recover p3 exact names; no guessing."""
    identity_cfg = json.loads((root / cfg["identity_config"]).read_text(encoding="utf-8"))
    identity = load_module("sf_identity_sequence_backend", root / cfg["identity_evaluator"])
    layout, _summary = identity.validate_dfam_index_layout(root, identity_cfg)
    backend = identity.FamDBBackend(root, identity_cfg, layout)
    resolved, rows, unresolved = {}, [], set()
    ambiguity = set(cfg["label_contract"]["ambiguity_identifiers"])
    try:
        for row in identity_rows:
            identifier = row["identifier"]
            if identifier in ambiguity:
                rows.append({"identifier": identifier, "status": "ambiguity_stratum", "sequence_source": "none"})
                continue
            candidates = []
            if row["resolution_status"] == "resolved" and row.get("versioned_accession"):
                candidates = backend.exact_accession(row["versioned_accession"])
                if not candidates:
                    candidates = backend.exact_accession(row["accession"])
                method = "identity_audit_exact_accession"
            else:
                candidates = scan_results.get(identifier, [])
                method = "partition3_index_independent_exact_name_scan"
            unique = {}
            for item in candidates:
                if hasattr(item, "accession"):
                    leaf_item = None
                    for leaf in backend.db.files.values():
                        leaf_item = leaf.get_family_by_accession(item.versioned_accession) or leaf.get_family_by_accession(item.accession)
                        if leaf_item is not None:
                            break
                    if leaf_item is None:
                        raise ValueError(f"RESOLVED_ACCESSION_SEQUENCE_MISSING:{identifier}")
                    candidate = {"accession": str(leaf_item.accession),
                                 "versioned_accession": str(leaf_item.accession_with_optional_version()),
                                 "consensus": str(leaf_item.consensus or "")}
                else:
                    candidate = item
                key = (candidate["versioned_accession"], sha256_text(candidate["consensus"].upper()))
                unique[key] = candidate
            if len(unique) == 1:
                candidate = next(iter(unique.values()))
                sequence = candidate["consensus"].upper().replace("U", "T")
                if not sequence:
                    unresolved.add(identifier)
                else:
                    resolved[identifier] = sequence
                    rows.append({"identifier": identifier, "status": "resolved", "sequence_source": method,
                                 "versioned_accession": candidate["versioned_accession"],
                                 "sequence_sha256": sha256_text(sequence), "sequence_length": len(sequence)})
            elif len(unique) > 1:
                raise DataTypedBlock(f"INDEX_INDEPENDENT_EXACT_NAME_AMBIGUITY:{identifier}:{len(unique)}")
            else:
                unresolved.add(identifier)
    finally:
        backend.close()
    return resolved, rows, unresolved


def opener(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if str(path).endswith(".gz") else path.open(encoding="utf-8")


def scan_annotations(root: Path, cfg: dict, canonical_rows: list[dict]) -> tuple[dict, dict]:
    s0 = load_module("sf_direct_s0_annotation_scan", root / cfg["s0_labeler"])
    s0_cfg = json.loads((root / cfg["s0_config"]).read_text(encoding="utf-8"))
    ontology = s0.load_ontology(root / cfg["ontology"])
    hard_terms = set(s0_cfg["label_state_policy"]["hard_negative_terms"])
    by_species = Counter(); identifier_species = Counter(); labels = defaultdict(set)
    total_parsed = total_p = 0
    for source in canonical_rows:
        species = source["species_code"]
        with opener(root / source["self_out"]) as handle:
            for line in handle:
                fields = line.split()
                if len(fields) < 15 or not fields[0].lstrip("+-").isdigit():
                    continue
                total_parsed += 1
                state, label, *_ = s0.classify_annotation(fields[10], ontology, hard_terms)
                if state != "P":
                    continue
                identifier = fields[9].strip()
                start, end = int(fields[5]) - 1, int(fields[6])
                if not identifier or start < 0 or end <= start:
                    raise ValueError(f"INVALID_P_ANNOTATION:{species}:{fields[4]}:{start}:{end}")
                total_p += 1; by_species[species] += 1; identifier_species[(identifier, species)] += 1
                labels[identifier].add(int(label))
    stats = {"parsed_annotation_records": total_parsed, "p_records": total_p,
             "p_identifier_species_occurrences": sum(identifier_species.values())}
    if total_parsed <= 0 or total_p <= 0 or sum(by_species.values()) != total_p:
        raise ValueError("ANNOTATION_CONSERVATION_FAILED")
    return {"by_species": by_species, "identifier_species": identifier_species, "labels": labels}, stats


def write_fasta(path: Path, sequences: dict[str, str]) -> None:
    lines = []
    for identifier in sorted(sequences):
        lines.append(f">{identifier}\n")
        sequence = sequences[identifier]
        lines.extend(sequence[i:i + 80] + "\n" for i in range(0, len(sequence), 80))
    atomic_text(path, "".join(lines))


def run_mmseqs(cfg: dict, fasta: Path, hits: Path, temporary: Path) -> list[str]:
    policy = cfg["homology_search"]
    command = [cfg["mmseqs_binary"], "easy-search", str(fasta), str(fasta), str(hits), str(temporary),
               "--search-type", "3", "--min-seq-id", str(policy["min_sequence_identity"]),
               "-c", str(policy["min_query_and_target_coverage"]), "--cov-mode", str(policy["coverage_mode"]),
               "-s", str(policy["sensitivity"]), "--max-seqs", str(policy["max_seqs"]),
               "--threads", str(policy["threads"]), "--format-output", "query,target,fident,alnlen,qlen,tlen,evalue,bits"]
    subprocess.run(command, check=True)
    return command


def parse_edges(hits: Path, identifiers: set[str], policy: dict) -> list[dict]:
    edges = {}
    with hits.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            fields = line.rstrip().split("\t")
            if len(fields) != 8:
                raise ValueError(f"MMSEQS_OUTPUT_SCHEMA:{line_number}")
            query, target = fields[:2]
            if query not in identifiers or target not in identifiers:
                raise ValueError(f"MMSEQS_UNKNOWN_IDENTIFIER:{line_number}")
            if query == target:
                continue
            identity = float(fields[2]); identity = identity / 100 if identity > 1 else identity
            alnlen, qlen, tlen = map(int, fields[3:6])
            qcov, tcov = alnlen / qlen, alnlen / tlen
            if identity + 1e-12 < float(policy["min_sequence_identity"]) or min(qcov, tcov) + 1e-12 < float(policy["min_query_and_target_coverage"]):
                raise ValueError(f"MMSEQS_EMITTED_BELOW_THRESHOLD:{line_number}")
            a, b = sorted((query, target)); key = (a, b)
            row = {"query": a, "target": b, "identity": identity, "query_coverage": qcov,
                   "target_coverage": tcov, "alignment_length": alnlen,
                   "evalue": float(fields[6]), "bits": float(fields[7])}
            if key not in edges or (row["bits"], row["identity"]) > (edges[key]["bits"], edges[key]["identity"]):
                edges[key] = row
    return [edges[key] for key in sorted(edges)]


def connected_components(identifiers: set[str], edges: list[dict]) -> tuple[dict[str, str], dict[str, list[str]]]:
    parent = {x: x for x in identifiers}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)
    for edge in edges:
        union(edge["query"], edge["target"])
    groups = defaultdict(list)
    for identifier in sorted(identifiers):
        groups[find(identifier)].append(identifier)
    component_members, mapping = {}, {}
    for members in sorted(groups.values()):
        component = "HC_" + sha256_text("\n".join(members))[:16]
        component_members[component] = members
        for identifier in members:
            mapping[identifier] = component
    return mapping, component_members


def component_main4_conflicts(component_members: dict[str, list[str]], identity_rows: list[dict]) -> list[dict]:
    labels = {row["identifier"]: set(row.get("labels", "").split(";")) for row in identity_rows}
    main4 = {"SINE", "LINE", "LTR", "DNA"}
    conflicts = []
    for component, members in sorted(component_members.items()):
        observed = sorted(set().union(*(labels.get(identifier, set()) & main4 for identifier in members)))
        if len(observed) > 1:
            conflicts.append({"homology_component": component, "main4_labels": ";".join(observed),
                              "identifiers": ";".join(members), "member_count": len(members)})
    return conflicts


def assign_components(cfg: dict, component_members: dict[str, list[str]], identifier_species: Counter,
                      species_meta: dict[str, dict], ambiguity: set[str]) -> tuple[list[dict], dict[str, str]]:
    policy = cfg["split_policy"]; primary_roles = set(policy["primary_test_roles"]); audit_roles = set(policy["audit_only_roles"])
    by_identifier = defaultdict(set)
    for identifier, species in identifier_species:
        by_identifier[identifier].add(species)
    assignments, mapping = [], {}
    for component, members in sorted(component_members.items()):
        species = sorted(set().union(*(by_identifier[identifier] for identifier in members)))
        roles = {species_meta[x]["role"] for x in species}
        if set(members) & ambiguity:
            split, reason = "ambiguity_stratum", "preregistered_ambiguity_identifier"
        elif roles & primary_roles:
            split, reason = "test_primary", "component_observed_in_primary_holdout"
        elif roles & audit_roles:
            split, reason = "audit_optional_stress", "component_observed_in_optional_stress"
        else:
            score = int(sha256_text(policy["validation_salt"] + "\n" + component)[:16], 16) % 100
            split, reason = ("val", "stable_component_hash") if score < int(policy["validation_hash_percent"]) else ("train", "stable_component_hash")
        orders = sorted({species_meta[x]["order_taxid"] for x in species})
        assignments.append({"homology_component": component, "split": split, "reason": reason,
                            "member_count": len(members), "identifiers": ";".join(members),
                            "species": ";".join(species), "roles": ";".join(sorted(roles)),
                            "order_taxids": ";".join(orders)})
        mapping.update({identifier: split for identifier in members})
    return assignments, mapping


def audit_split(cfg: dict, identity_rows: list[dict], excluded_rows: list[dict], scan: dict, stats: dict,
                component_map: dict[str, str], split_map: dict[str, str], species_meta: dict[str, dict],
                edges: list[dict], components: dict[str, list[str]], sequence_rows: list[dict]) -> dict:
    ambiguity = set(cfg["label_contract"]["ambiguity_identifiers"])
    expected_ids = {row["identifier"] for row in identity_rows}
    if set(component_map) != expected_ids:
        raise ValueError(f"IDENTIFIER_COMPONENT_CONSERVATION:missing={sorted(expected_ids-set(component_map))[:5]}")
    if len(excluded_rows) != int(cfg["label_contract"]["label_contract_excluded_identifiers"]):
        raise ValueError("LABEL_CONTRACT_EXCLUDED_COUNT_DRIFT")
    observed_ids = set(scan["labels"])
    if observed_ids != expected_ids:
        raise ValueError(f"P_IDENTIFIER_UNIVERSE_DRIFT:missing={sorted(expected_ids-observed_ids)[:5]}:extra={sorted(observed_ids-expected_ids)[:5]}")
    old_occurrences = {row["identifier"]: int(row["occurrences"]) for row in identity_rows}
    new_occurrences = Counter()
    for (identifier, _species), count in scan["identifier_species"].items():
        new_occurrences[identifier] += count
    if old_occurrences != dict(new_occurrences):
        raise ValueError("P_IDENTIFIER_OCCURRENCE_CONSERVATION_DRIFT")
    old_labels = {row["identifier"]: set(row["labels"].split(";")) for row in identity_rows}
    label_names = {1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}
    new_labels = {identifier: {label_names[x] for x in values} for identifier, values in scan["labels"].items()}
    if old_labels != new_labels:
        raise ValueError("DIRECT_SUPERFAMILY_LABEL_CONSERVATION_DRIFT")
    if any(split_map[x] != "ambiguity_stratum" for x in ambiguity):
        raise ValueError("AMBIGUITY_ENTERED_PRIMARY")
    component_splits = defaultdict(set)
    for identifier, component in component_map.items():
        component_splits[component].add(split_map[identifier])
    overlap = sum(len(splits) != 1 for splits in component_splits.values())
    if overlap:
        raise ValueError("HOMOLOGY_COMPONENT_SPLIT_OVERLAP")
    primary_roles = set(cfg["split_policy"]["primary_test_roles"]); fit_role = cfg["split_policy"]["fit_role"]
    fit_orders = {x["order_taxid"] for x in species_meta.values() if x["role"] == fit_role}
    test_orders = {x["order_taxid"] for x in species_meta.values() if x["role"] in primary_roles}
    if fit_orders & test_orders:
        raise ValueError("PRIMARY_CLADE_OVERLAP")
    occurrences_by_split = Counter()
    for (identifier, species), count in scan["identifier_species"].items():
        occurrences_by_split[split_map[identifier]] += count
    if sum(occurrences_by_split.values()) != int(stats["p_records"]):
        raise ValueError("P_OCCURRENCE_SPLIT_CONSERVATION")
    primary_records = sum(occurrences_by_split[x] for x in ("train", "val", "test_primary"))
    sources = Counter(row["sequence_source"] for row in sequence_rows)
    metrics = {"profile": cfg["profile"], "semantic_success": True, "claim_eligible": False,
               "scientific_component_gate_executed": 1, "primary_metric": 1.0,
               "total_p_identifiers": len(expected_ids), "total_p_records": int(stats["p_records"]),
               "parsed_annotation_records": int(stats["parsed_annotation_records"]),
               "label_contract_excluded_identifier_count": len(excluded_rows),
               "ambiguity_identifier_count": len(ambiguity), "ambiguity_identifiers": sorted(ambiguity),
               "homology_edge_count": len(edges), "homology_component_count": len(components),
               "homology_component_overlap_count": 0, "primary_clade_overlap_count": 0,
               "primary_eligible_p_records": primary_records,
               "primary_eligible_p_record_coverage": primary_records / int(stats["p_records"]),
               "occurrences_by_split": dict(sorted(occurrences_by_split.items())),
               "sequence_sources": dict(sorted(sources.items())),
               "prediction_label_source": "RepeatMasker plus pinned S0 R2 labeler",
               "sequence_used_as_prediction_label": False,
               "test_metric_used_for_threshold_selection": False,
               "random_fallback_used": False, "chromosome_fallback_used": False,
               "representative_fasta_model_input_authorized": False}
    if not all(math.isfinite(float(x)) for x in metrics.values() if isinstance(x, (int, float))):
        raise ValueError("NONFINITE_METRIC")
    return metrics


def create_payload_manifest(stage: Path) -> str:
    files = {str(path.relative_to(stage)): sha256_file(path) for path in sorted(stage.rglob("*"))
             if path.is_file() and path.name != "PAYLOAD_MANIFEST.json"}
    required = {"sequence_sources.tsv", "representatives.split_only.fa", "homology_edges.tsv", "homology_components.tsv",
                "component_assignments.tsv", "identifier_assignments.tsv", "label_contract_excluded.tsv",
                "ambiguity_stratum.tsv", "metrics.json", "report.json", "RUN_MANIFEST.json"}
    if required - set(files):
        raise ValueError(f"PAYLOAD_MISSING:{sorted(required-set(files))}")
    atomic_json(stage / "PAYLOAD_MANIFEST.json", {"schema_version": "SF-HOMOLOGY-SPLIT-PAYLOAD-1.0.0",
                "self_included": False, "files": files})
    return sha256_file(stage / "PAYLOAD_MANIFEST.json")


def verify_payload(stage: Path) -> str:
    path = stage / "PAYLOAD_MANIFEST.json"; manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("self_included") is not False or "PAYLOAD_MANIFEST.json" in manifest.get("files", {}):
        raise ValueError("SELF_REFERENTIAL_PAYLOAD")
    for relpath, expected in manifest["files"].items():
        if sha256_file(stage / relpath) != expected:
            raise ValueError(f"PAYLOAD_DRIFT:{relpath}")
    return sha256_file(path)


def package_hashes(root: Path, exp_id: str) -> dict[str, str]:
    paths = [root / "configs" / f"{exp_id}.yaml", root / "scripts/experiments" / exp_id / "build_homology_split.py",
             root / "scripts/experiments" / exp_id / "test_homology_split.py", root / "sbatch" / f"{exp_id}.sbatch"]
    return {str(path.relative_to(root)): sha256_file(path) for path in paths}


def finalize_preview(root: Path, cfg: dict, status: str, attempt_id: str, metrics: dict, report: dict,
                     extra_paths: tuple[Path, ...] = ()) -> None:
    preview = root / cfg["preview_root"]
    atomic_json(preview / "metrics.json", metrics); atomic_json(preview / "report.json", report)
    atomic_text(preview / "STATUS", status + "\n")
    atomic_json(preview / "TERMINAL_STATE.json", {"schema_version": "SF-HOMOLOGY-SPLIT-TERMINAL-1.0.0",
                "exp_id": cfg["exp_id"], "status": status, "attempt_id": attempt_id,
                "semantic_success": bool(metrics.get("semantic_success", False)),
                "model_training_authorized": status == "DATA_READY", "unlisted_artifacts_are_superseded": True})
    paths = [preview / x for x in ("STATUS", "TERMINAL_STATE.json", "metrics.json", "report.json",
                                    "input_manifest.json", "static_contract.json")] + list(extra_paths)
    unique = {str(x.relative_to(root)): x for x in paths}
    if any(not x.is_file() for x in unique.values()):
        raise ValueError("PREVIEW_ARTIFACT_MISSING")
    atomic_text(preview / "output_manifest.sha256", "".join(
        f"{sha256_file(unique[name])}  {name}\n" for name in sorted(unique)))
    for line in (preview / "output_manifest.sha256").read_text(encoding="utf-8").splitlines():
        expected, relpath = line.split("  ", 1)
        if sha256_file(root / relpath) != expected:
            raise ValueError(f"PREVIEW_MANIFEST_DRIFT:{relpath}")


def static_preview(root: Path, cfg: dict) -> None:
    summary = validate_static_inputs(root, cfg, False)
    preview = root / cfg["preview_root"]; preview.mkdir(parents=True, exist_ok=True)
    static = {"schema_version": "SF-HOMOLOGY-SPLIT-STATIC-1.0.0", "package_hashes": package_hashes(root, cfg["exp_id"]),
              "input_contract": summary, "gpus": 0, "formal_slurm_required": True}
    metrics = {"profile": cfg["profile"], "status": "IMPLEMENTED_NOT_RUN", "primary_metric": 0.0,
               "semantic_success": False, "claim_eligible": False, "scientific_component_gate_executed": 0,
               "homology_component_overlap_count": 0, "primary_clade_overlap_count": 0,
               "sequence_used_as_prediction_label": False, "test_metric_used_for_threshold_selection": False,
               "random_fallback_used": False, "chromosome_fallback_used": False, **summary}
    report = {"exp_id": cfg["exp_id"], "status": "IMPLEMENTED_NOT_RUN", "semantic_success": False,
              "contract": "RepeatMasker labels; sequence homology only for leakage-safe components",
              "homology_search": cfg["homology_search"], "representative_policy": cfg["representative_policy"],
              "input_contract": summary, "result": "NOT_RUN"}
    atomic_json(preview / "input_manifest.json", static); atomic_json(preview / "static_contract.json", static)
    finalize_preview(root, cfg, "IMPLEMENTED_NOT_RUN", "static-preview", metrics, report)


def run_formal(root: Path, cfg: dict, attempt_id: str) -> tuple[str, dict]:
    if not os.environ.get("SLURM_JOB_ID"):
        raise ValueError("FORMAL_SLURM_GUARD")
    preview = root / cfg["preview_root"]; attempts = preview / "attempts"; attempts.mkdir(parents=True, exist_ok=True)
    final = attempts / attempt_id; staging = attempts / (attempt_id + ".tmp")
    if final.exists() or staging.exists():
        raise ValueError("DIRTY_ATTEMPT_REFUSED")
    staging.mkdir()
    try:
        static_summary = validate_static_inputs(root, cfg, True)
        canonical_rows = read_tsv(root / cfg["canonical_split_manifest"])
        identity_rows = read_tsv(root / cfg["identity_identifier_audit"])
        excluded_rows = read_tsv(root / cfg["identity_excluded_audit"])
        ambiguity = set(cfg["label_contract"]["ambiguity_identifiers"])
        missing = {row["identifier"] for row in identity_rows if row["resolution_status"] != "resolved"} - ambiguity
        scan_results, metadata_scan = scan_exact_names_without_index(root / cfg["famdb_partition3"], missing)
        sequences, sequence_rows, unresolved = resolve_sequence_sources(root, cfg, identity_rows, scan_results)
        scan, annotation_stats = scan_annotations(root, cfg, canonical_rows)
        if unresolved:
            unresolved_occurrences = sum(count for (identifier, _species), count in scan["identifier_species"].items()
                                         if identifier in unresolved)
            raise DataTypedBlock("UNRESOLVED_DFAM_CONSENSUS",
                                 {"unresolved_identifier_count": len(unresolved),
                                  "unresolved_annotation_occurrences": unresolved_occurrences,
                                  "unresolved_identifiers": sorted(unresolved),
                                  "metadata_scan": metadata_scan})
        write_fasta(staging / "representatives.split_only.fa", sequences)
        command = run_mmseqs(cfg, staging / "representatives.split_only.fa", staging / "mmseqs_hits.tsv", staging / "mmseqs_tmp")
        edges = parse_edges(staging / "mmseqs_hits.tsv", set(sequences), cfg["homology_search"])
        component_map, components = connected_components(set(sequences), edges)
        for identifier in sorted(ambiguity):
            component = "HC_AMBIGUITY_" + sha256_text(identifier)[:16]
            component_map[identifier] = component; components[component] = [identifier]
        conflicts = component_main4_conflicts(components, identity_rows)
        if conflicts:
            raise DataTypedBlock("HOMOLOGY_COMPONENT_MAIN4_LABEL_CONFLICT",
                                 {"component_main4_label_conflict_count": len(conflicts), "conflicts": conflicts})
        species_meta = {row["species_code"]: row for row in read_tsv(root / cfg["species_holdout_manifest"])}
        assignments, split_map = assign_components(cfg, components, scan["identifier_species"], species_meta, ambiguity)
        metrics = audit_split(cfg, identity_rows, excluded_rows, scan, annotation_stats, component_map, split_map,
                              species_meta, edges, components, sequence_rows)
        metrics.update({"status": "DATA_READY", "index_independent_metadata_scan": metadata_scan,
                        "mmseqs_command": command, **static_summary})
        id_by_name = {row["identifier"]: row for row in identity_rows}
        source_by_name = {row["identifier"]: row for row in sequence_rows}
        identifier_assignments = [{"identifier": identifier, "homology_component": component_map[identifier],
                                   "split": split_map[identifier], "labels": id_by_name[identifier]["labels"],
                                   "occurrences": id_by_name[identifier]["occurrences"],
                                   "species": id_by_name[identifier]["species"],
                                   "sequence_source": source_by_name.get(identifier, {}).get("sequence_source", "ambiguity_placeholder")}
                                  for identifier in sorted(component_map)]
        component_rows = [{"homology_component": component, "member_count": len(members),
                           "identifiers": ";".join(members)} for component, members in sorted(components.items())]
        write_tsv(staging / "sequence_sources.tsv", sequence_rows,
                  ["identifier", "status", "sequence_source", "versioned_accession", "sequence_sha256", "sequence_length", "representative_locus"])
        write_tsv(staging / "homology_edges.tsv", edges,
                  ["query", "target", "identity", "query_coverage", "target_coverage", "alignment_length", "evalue", "bits"])
        write_tsv(staging / "homology_components.tsv", component_rows, ["homology_component", "member_count", "identifiers"])
        write_tsv(staging / "component_assignments.tsv", assignments,
                  ["homology_component", "split", "reason", "member_count", "identifiers", "species", "roles", "order_taxids"])
        write_tsv(staging / "identifier_assignments.tsv", identifier_assignments,
                  ["identifier", "homology_component", "split", "labels", "occurrences", "species", "sequence_source"])
        shutil.copyfile(root / cfg["identity_excluded_audit"], staging / "label_contract_excluded.tsv")
        write_tsv(staging / "ambiguity_stratum.tsv", [x for x in identifier_assignments if x["split"] == "ambiguity_stratum"],
                  ["identifier", "homology_component", "split", "labels", "occurrences", "species", "sequence_source"])
        report = {"exp_id": cfg["exp_id"], "status": "DATA_READY", "semantic_success": True,
                  "question": "Can frozen sequence-homology components support leakage-safe S0 train/val/primary-test splits?",
                  "answer": "YES", "metrics": metrics, "prediction_labels_unchanged": True,
                  "representative_fasta_model_input_authorized": False}
        atomic_json(staging / "metrics.json", metrics); atomic_json(staging / "report.json", report)
        atomic_json(staging / "RUN_MANIFEST.json", {"schema_version": "SF-HOMOLOGY-SPLIT-RUN-1.0.0",
                    "attempt_id": attempt_id, "slurm_job_id": os.environ["SLURM_JOB_ID"],
                    "created_at_utc": datetime.now(timezone.utc).isoformat(), "package_hashes": package_hashes(root, cfg["exp_id"]),
                    "input_payload_sha256": cfg["identity_payload_sha256"], "gpus": 0})
        payload_sha = create_payload_manifest(staging); verify_payload(staging)
        shutil.rmtree(staging / "mmseqs_tmp", ignore_errors=True); (staging / "mmseqs_hits.tsv").unlink(missing_ok=True)
        # Rebuild after deleting intermediate search state so the manifest remains exact.
        payload_sha = create_payload_manifest(staging); verify_payload(staging)
        os.replace(staging, final); verify_payload(final)
        atomic_json(preview / "input_manifest.json", json.loads((final / "RUN_MANIFEST.json").read_text(encoding="utf-8")))
        atomic_json(preview / "static_contract.json", {"package_hashes": package_hashes(root, cfg["exp_id"]), "gpus": 0})
        finalize_preview(root, cfg, "DATA_READY", attempt_id, metrics, report, (final / "PAYLOAD_MANIFEST.json",))
        return "DATA_READY", metrics
    except DataTypedBlock as exc:
        metrics = {"profile": cfg["profile"], "status": "DATA_TYPED_BLOCK", "primary_metric": 0.0,
                   "semantic_success": True, "valid_negative": True, "scientific_component_gate_executed": 1,
                   "model_training_authorized": False, "blocker": exc.code, **exc.details}
        report = {"exp_id": cfg["exp_id"], "status": "DATA_TYPED_BLOCK", "semantic_success": True,
                  "answer": "NO_TYPED_BLOCK", "blocker": exc.code, "details": exc.details}
        atomic_json(staging / "failure.json", {"blocker_type": type(exc).__name__, "blocker": exc.code,
                    "semantic_success": True, "details": exc.details})
        finalize_preview(root, cfg, "DATA_TYPED_BLOCK", attempt_id, metrics, report, (staging / "failure.json",))
        return "DATA_TYPED_BLOCK", metrics
    except Exception as exc:
        failure = staging / "failure.json" if staging.exists() else preview / f"failure.{attempt_id}.json"
        atomic_json(failure, {"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        metrics = {"profile": cfg.get("profile", "cpu_predata_component_gate"), "status": "AUDIT_FAILED",
                   "primary_metric": 0.0, "semantic_success": False, "scientific_component_gate_executed": 0,
                   "model_training_authorized": False, "error": str(exc)}
        report = {"exp_id": cfg.get("exp_id"), "status": "AUDIT_FAILED", "semantic_success": False,
                  "answer": "NOT_ESTABLISHED", "error": str(exc)}
        finalize_preview(root, cfg, "AUDIT_FAILED", attempt_id, metrics, report, (failure,))
        raise


def terminal_exit_code(status: str) -> int:
    return 0 if status in {"IMPLEMENTED_NOT_RUN", "DATA_READY", "DATA_TYPED_BLOCK"} else 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--attempt-id", default="static-preview")
    parser.add_argument("--static-check-only", action="store_true")
    args = parser.parse_args(); cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    if args.static_check_only:
        static_preview(root, cfg); print(json.dumps({"status": "IMPLEMENTED_NOT_RUN", "gpus": 0}, sort_keys=True)); return
    try:
        status, _metrics = run_formal(root, cfg, args.attempt_id)
    except Exception as exc:
        print(json.dumps({"status": "AUDIT_FAILED", "semantic_success": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps({"status": status, "gpus": 0}, sort_keys=True))
    raise SystemExit(terminal_exit_code(status))


if __name__ == "__main__":
    main()
