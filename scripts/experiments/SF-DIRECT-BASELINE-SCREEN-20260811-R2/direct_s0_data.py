#!/usr/bin/env python3
"""Build/verify the frozen order-clade-held-out direct-SF5 dataset.

Scientific invariants:
* split groups are exact Dfam 3.9 accession identities (`homology_component`);
* order-level NCBI clades are frozen and fit/primary-test clades do not overlap;
* optional stress is physically separate and cannot enter the numeric gate;
* one precedence painter defines labels, P/U/hardN/RN masks and coverage;
* U is -100 for loss/scoring, while hardN and RN are explicit BG guardrails;
* historical 5,400/1,440/2,160 windows must exact-rejoin uniquely (9,000).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import heapq
import json
import os
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

ID2LABEL = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}
MAIN4 = {1, 2, 3, 4}
STATE2ID = {"P": 0, "U": 1, "hardN": 2, "RN": 3}
ID2STATE = {v: k for k, v in STATE2ID.items()}
PINNED_CHUNK_MAX_FIELD_CHARS = 2_000_000
PINNED_CHUNK_ROWS = 495
PINNED_CHUNK_COLUMNS = (
    "chunk_index", "species_code", "scientific_name", "repeatmasker_species", "taxid", "priority",
    "source_fasta", "source_fasta_bytes", "source_fasta_md5", "chunk_id", "chunk_fasta", "chunk_bases",
    "record_count", "records", "output_dir", "species_output_dir", "repeatmasker_custom_lib",
)


class DataContractTypedBlock(RuntimeError):
    """A missing preregistered scientific asset/identity, not a runnable dataset."""


def opener(path: Path, mode: str = "rt"):
    if str(path).endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8" if "t" in mode else None)
    return path.open(mode, encoding="utf-8" if "t" in mode else None)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(value, encoding="utf-8")
    os.replace(tmp, path)


def atomic_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: Iterable[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def stable_score(*parts: object) -> int:
    return int.from_bytes(hashlib.sha256("\x1f".join(map(str, parts)).encode()).digest()[:8], "big")


def normalize_family(name: str) -> str:
    value = unicodedata.normalize("NFKC", name).strip().upper()
    if not value or value in {".", "-", "NA", "N/A"}:
        raise ValueError(f"invalid RepeatMasker repeat_name {name!r}")
    return value


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_pinned_chunk_manifest(path: Path, enforce_source_contract: bool = True) -> list[dict[str, str]]:
    """Read the one pinned wide TSV without relaxing CSV limits process-wide."""
    previous_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(PINNED_CHUNK_MAX_FIELD_CHARS)
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                rows = list(reader)
                columns = tuple(reader.fieldnames or ())
        except csv.Error as exc:
            raise ValueError(
                f"pinned chunk manifest exceeds {PINNED_CHUNK_MAX_FIELD_CHARS} character field limit") from exc
    finally:
        csv.field_size_limit(previous_limit)
    if enforce_source_contract and (columns != PINNED_CHUNK_COLUMNS or len(rows) != PINNED_CHUNK_ROWS):
        raise ValueError(
            f"pinned chunk manifest shape mismatch: columns={len(columns)} rows={len(rows)}; "
            f"expected columns={len(PINNED_CHUNK_COLUMNS)} rows={PINNED_CHUNK_ROWS}")
    return rows


def load_ontology(path: Path) -> dict:
    exact: dict[str, tuple[str, str]] = {}
    folded: dict[str, tuple[str, str]] = {}
    conflicts = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3 or not parts[1].startswith("SO:"):
            continue
        term, so_id = parts[0], parts[1]
        for alias in " ".join(parts[2:]).split(","):
            alias = alias.strip()
            if not alias:
                continue
            value = (term, so_id)
            if alias in exact and exact[alias] != value:
                conflicts.add(alias)
            exact[alias] = value
            key = alias.casefold()
            if key in folded and folded[key] != value:
                conflicts.add(key)
            folded[key] = value
    if conflicts:
        raise ValueError(f"ontology alias conflicts: {sorted(conflicts)[:5]}")
    return {"exact": exact, "folded": folded}


def canonicalize(raw_class: str, ontology: dict) -> tuple[str, str, str]:
    raw = raw_class.strip()
    if raw in ontology["exact"]:
        term, so_id = ontology["exact"][raw]
        return term, so_id, "EXACT_ALIAS"
    if raw.casefold() in ontology["folded"]:
        term, so_id = ontology["folded"][raw.casefold()]
        return term, so_id, "CASEFOLD_ALIAS"
    head = raw.split("/", 1)[0]
    candidates = {"SINE": "SINE", "LINE": "LINE", "LTR": "LTR", "DNA": "DNA", "RC": "RC/Helitron"}
    alias = candidates.get(head.upper())
    if alias and alias in ontology["exact"]:
        term, so_id = ontology["exact"][alias]
        return term, so_id, "CANONICAL_HEAD_FALLBACK"
    return "UNRESOLVED", "UNRESOLVED", "UNRESOLVED"


def classify_annotation(raw_class: str, ontology: dict, hard_terms: set[str]) -> tuple[str, int, str, str, str]:
    term, so_id, alias_status = canonicalize(raw_class, ontology)
    head = raw_class.strip().split("/", 1)[0].upper()
    if term in hard_terms:
        return "hardN", 0, term, so_id, alias_status
    if alias_status == "UNRESOLVED":
        return "U", -100, term, so_id, alias_status
    if head == "SINE":
        return "P", 1, term, so_id, alias_status
    if head == "LINE":
        return "P", 2, term, so_id, alias_status
    if head == "LTR":
        return "P", 3, term, so_id, alias_status
    if head == "DNA":
        return "P", 4, term, so_id, alias_status
    if head in {"RC", "RETROPOSON"} or "UNKNOWN" in raw_class.upper() or "?" in raw_class:
        return "P", 5, term, so_id, alias_status
    return "U", -100, term, so_id, alias_status


@dataclass(frozen=True)
class Annotation:
    start: int
    end: int
    state: str
    label: int
    family_component: str
    score: int
    ontology_term: str
    so_id: str
    alias_status: str
    dfam_name: str = ""


def iter_rm(path: Path, ontology: dict, hard_terms: set[str]) -> Iterator[tuple[str, Annotation]]:
    with opener(path) as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < 15 or not fields[0].isdigit():
                continue
            start, end = int(fields[5]) - 1, int(fields[6])
            if start < 0 or end <= start:
                continue
            state, label, term, so_id, alias_status = classify_annotation(fields[10], ontology, hard_terms)
            component = normalize_family(fields[9]) if state == "P" else ""
            yield fields[4], Annotation(start, end, state, label, component, int(fields[0]), term, so_id, alias_status,
                                        fields[9] if state == "P" else "")


def read_b_intervals(path: Path) -> dict[str, list[tuple[int, int]]]:
    result: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with opener(path) as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip().split("\t")
            if len(fields) < 3:
                continue
            try:
                start, end = int(fields[1]), int(fields[2])
            except ValueError:
                continue
            if start >= 0 and end > start:
                result[fields[0]].append((start, end))
    for values in result.values():
        values.sort()
    return result


def overlaps(values: list, start: int, end: int) -> list:
    return [x for x in values if x[0] < end and x[1] > start] if values and isinstance(values[0], tuple) else [x for x in values if x.start < end and x.end > start]


def resolve_dfam_identities(raw_names: dict[str, set[str]], root: Path, cfg: dict, allow_synthetic: bool = False) -> tuple[dict[str, str], dict[str, dict]]:
    """Resolve every RM family to one exact Dfam accession identity; no inferred clustering."""
    if allow_synthetic and cfg.get("synthetic_dfam_identities"):
        identities = cfg["synthetic_dfam_identities"]
        mapping = {family: identities[family]["accession"] for family in raw_names}
        details = {identities[f]["accession"]: {"homology_component": identities[f]["accession"], "dfam_names": ";".join(sorted(raw_names[f])),
                    "consensus_sha256": identities[f]["consensus_sha256"], "source": "SYNTHETIC_TEST_ONLY"} for f in raw_names}
        return mapping, details
    rmlib = root / cfg["famdb_rmlib_config"]
    if sha256_file(rmlib) != cfg["famdb_rmlib_config_sha256"]:
        raise DataContractTypedBlock("FAMDB_RMLIB_CONFIG_IDENTITY_MISMATCH")
    code_dir = Path(cfg["famdb_code_dir"])
    if not code_dir.is_dir():
        raise DataContractTypedBlock("FAMDB_CODE_DIR_MISSING")
    for filename, expected in cfg["famdb_code_sha256"].items():
        if sha256_file(code_dir / filename) != expected:
            raise DataContractTypedBlock(f"FAMDB_CODE_IDENTITY_MISMATCH:{filename}")
    sys.path.insert(0, str(code_dir))
    try:
        from famdb_classes import FamDB
    except Exception as exc:
        raise DataContractTypedBlock(f"FAMDB_RUNTIME_UNAVAILABLE:{type(exc).__name__}") from exc
    db = FamDB(str(root / cfg["famdb_dir"]), "r")
    mapping, details, missing = {}, {}, []
    try:
        metadata = db.get_metadata()
        if metadata.get("name") != "Dfam" or metadata.get("db_version") != "3.9" or metadata.get("famdb_version") != "2.0.0":
            raise DataContractTypedBlock(f"FAMDB_RELEASE_IDENTITY_MISMATCH:{metadata}")
        for family in sorted(raw_names):
            resolved = []
            for raw_name in sorted(raw_names[family]):
                item = db.get_family_by_name(raw_name)
                if item is None or item.name != raw_name or not item.accession or not item.consensus:
                    missing.append(raw_name)
                    continue
                resolved.append((item.accession_with_optional_version(), raw_name,
                                 sha256_bytes(str(item.consensus).upper().encode())))
            accessions = {x[0] for x in resolved}
            consensus_hashes = {x[2] for x in resolved}
            if len(resolved) != len(raw_names[family]) or len(accessions) != 1 or len(consensus_hashes) != 1:
                missing.extend(sorted(raw_names[family]))
                continue
            accession = next(iter(accessions))
            mapping[family] = accession
            details[accession] = {"homology_component": accession, "dfam_names": ";".join(x[1] for x in resolved),
                                  "consensus_sha256": next(iter(consensus_hashes)), "source": "Dfam_3.9_exact_family_identity"}
    finally:
        db.close()
    if missing or len(mapping) != len(raw_names):
        raise DataContractTypedBlock("DFAM_FAMILY_IDENTITY_UNRESOLVED:" + ",".join(sorted(set(missing))[:50]))
    return mapping, details


def assign_family_components(rows: list[dict], root: Path, cfg: dict, ontology: dict, allow_synthetic: bool = False) -> tuple[dict[str, str], dict[str, dict], dict[str, str], dict[str, dict], Counter]:
    roles: dict[str, set[str]] = defaultdict(set)
    labels: dict[str, set[int]] = defaultdict(set)
    terms: dict[str, set[str]] = defaultdict(set)
    records = Counter()
    raw_names: dict[str, set[str]] = defaultdict(set)
    mapping = Counter()
    hard_terms = set(cfg["label_state_policy"]["hard_negative_terms"])
    for row in rows:
        for _chrom, ann in iter_rm(root / row["self_out"], ontology, hard_terms):
            mapping[(ann.state, ann.alias_status, ann.ontology_term)] += 1
            if ann.state != "P":
                continue
            roles[ann.family_component].add(row["role"])
            labels[ann.family_component].add(ann.label)
            terms[ann.family_component].add(ann.ontology_term)
            raw_names[ann.family_component].add(ann.dfam_name)
            records[ann.family_component] += 1
    conflicts = sorted(family for family, values in labels.items() if len(values) != 1)
    if conflicts:
        raise DataContractTypedBlock("FAMILY_COMPONENT_LABEL_CONFLICT:" + ",".join(conflicts[:50]))
    family_to_homology, homology_details = resolve_dfam_identities(raw_names, root, cfg, allow_synthetic)
    component_roles: dict[str, set[str]] = defaultdict(set)
    component_labels: dict[str, set[int]] = defaultdict(set)
    component_families: dict[str, set[str]] = defaultdict(set)
    for family, component in family_to_homology.items():
        component_roles[component].update(roles[family]); component_labels[component].update(labels[family]); component_families[component].add(family)
    component_conflicts = sorted(component for component, values in component_labels.items() if len(values) != 1)
    if component_conflicts:
        raise DataContractTypedBlock("HOMOLOGY_COMPONENT_LABEL_CONFLICT:" + ",".join(component_conflicts[:50]))
    policy = cfg["homology_component_policy"]
    heldout = set(policy["test_if_observed_in_roles"])
    component_split = {}
    for component in sorted(component_roles):
        if component_roles[component] & heldout:
            split, reason = "test", "observed_in_species_holdout"
        elif stable_score(policy["salt"], component) % 100 < int(policy["validation_hash_percent"]):
            split, reason = "val", "frozen_hash_validation"
        else:
            split, reason = "train", "frozen_hash_train"
        component_split[component] = split
        homology_details[component].update({"split": split, "reason": reason, "roles": ";".join(sorted(component_roles[component])),
                                             "labels": ";".join(ID2LABEL[x] for x in sorted(component_labels[component])),
                                             "family_components": ";".join(sorted(component_families[component])), "label_conflict": False})
    family_split, details = {}, {}
    for family in sorted(roles):
        component = family_to_homology[family]
        split = component_split[component]
        family_split[family] = split
        details[family] = {
            "family_component": family, "homology_component": component, "split": split, "roles": ";".join(sorted(roles[family])),
            "labels": ";".join(ID2LABEL[x] for x in sorted(labels[family])), "ontology_terms": ";".join(sorted(terms[family])),
            "annotation_records": records[family], "label_conflict": False,
        }
    return family_split, details, family_to_homology, homology_details, mapping


def rm_by_chrom(path: Path, ontology: dict, hard_terms: set[str]) -> dict[str, list[Annotation]]:
    result: dict[str, list[Annotation]] = defaultdict(list)
    for chrom, ann in iter_rm(path, ontology, hard_terms):
        result[chrom].append(ann)
    for values in result.values():
        values.sort(key=lambda x: (x.start, x.end, -x.score, x.family_component))
    return result


def candidate_coordinates(species: str, anns: dict[str, list[Annotation]], cap: int, window: int, seed: int) -> list[tuple[str, int]]:
    heap: list[tuple[int, int, tuple[str, int]]] = []
    serial = 0
    for chrom, values in sorted(anns.items()):
        tiles = set()
        for ann in values:
            if ann.state != "P":
                continue
            tiles.update(range(ann.start // window, (ann.end - 1) // window + 1))
        for tile in tiles:
            coord = (chrom, tile * window)
            item = (-stable_score("SF-DIRECT-R2-WINDOW-V2", seed, species, *coord), serial, coord)
            serial += 1
            if len(heap) < cap:
                heapq.heappush(heap, item)
            elif item > heap[0]:
                heapq.heapreplace(heap, item)
    return sorted((x[2] for x in heap), key=lambda x: (x[0], x[1]))


def classify_window(p_anns: list[Annotation], family_split: dict[str, str], role: str, cfg: dict) -> tuple[str | None, str, list[str]]:
    families = sorted({x.family_component for x in p_anns})
    splits = {family_split[x] for x in families}
    if not families:
        return None, "NO_P_COMPONENT", families
    if len(splits) != 1:
        return None, "CROSS_SPLIT_MIXED", families
    split = next(iter(splits))
    policy = cfg["holdout_policy"]
    if role == policy["fit_role"] and split in {"train", "val"}:
        return split, "RETAINED", families
    if role in set(policy["primary_test_roles"]) and split == "test":
        return "test_primary", "RETAINED", families
    if role in set(policy["audit_only_roles"]) and split == "test":
        return "audit_optional_stress", "RETAINED_AUDIT_ONLY", families
    return None, "ROLE_SPLIT_MISMATCH", families


def rle_states(states: list[str]) -> list[list[int]]:
    result: list[list[int]] = []
    for state in states:
        sid = STATE2ID[state]
        if result and result[-1][0] == sid:
            result[-1][1] += 1
        else:
            result.append([sid, 1])
    return result


def expand_state_rle(rle: list[list[int]], expected: int) -> list[str]:
    states = [ID2STATE[int(sid)] for sid, length in rle for _ in range(int(length))]
    if len(states) != expected:
        raise ValueError(f"state_rle length {len(states)} != {expected}")
    return states


def paint_window(sequence: str, start: int, window: int, anns: list[Annotation], b_intervals: list[tuple[int, int]]) -> dict:
    seq = (sequence[:window] + "N" * window)[:window]
    states = ["RN" if base in "ACGT" else "U" for base in seq]
    labels = [0 if state == "RN" else -100 for state in states]
    b_mask = [False] * window
    for left0, right0 in b_intervals:
        left, right = max(start, left0) - start, min(start + window, right0) - start
        for i in range(max(0, left), min(window, right)):
            b_mask[i] = True
            if states[i] == "RN":
                states[i], labels[i] = "U", -100
    for ann in sorted((x for x in anns if x.state == "U"), key=lambda x: (x.score, x.start, x.end)):
        for i in range(max(start, ann.start) - start, min(start + window, ann.end) - start):
            if states[i] == "RN":
                states[i], labels[i] = "U", -100
    for ann in sorted((x for x in anns if x.state == "hardN"), key=lambda x: (x.score, x.start, x.end)):
        for i in range(max(start, ann.start) - start, min(start + window, ann.end) - start):
            states[i], labels[i] = "hardN", 0
    score = [-1] * window
    for ann in sorted((x for x in anns if x.state == "P"), key=lambda x: (x.score, x.family_component)):
        for i in range(max(start, ann.start) - start, min(start + window, ann.end) - start):
            if ann.score >= score[i]:
                score[i] = ann.score
                states[i], labels[i] = "P", ann.label
    counts = Counter(states)
    counts["label_a_only_bp"] = sum(s == "P" and not b for s, b in zip(states, b_mask))
    counts["label_a_b_overlap_bp"] = sum(s == "P" and b for s, b in zip(states, b_mask))
    counts["label_b_only_masked_bp"] = sum(s == "U" and b for s, b in zip(states, b_mask))
    counts["main4_p_bp"] = sum(s == "P" and y in MAIN4 for s, y in zip(states, labels))
    return {"sequence": seq, "labels": labels, "states": states, "state_rle": rle_states(states), "counts": dict(counts)}


def iter_fasta(path: Path) -> Iterator[tuple[str, str]]:
    chrom, chunks = None, []
    with opener(path) as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith(">"):
                if chrom is not None:
                    yield chrom, "".join(chunks).upper()
                chrom, chunks = line[1:].split()[0], []
            elif chrom is not None:
                chunks.append(line)
    if chrom is not None:
        yield chrom, "".join(chunks).upper()


def validate_asset_tree(root: Path, cfg: dict) -> dict:
    contract_path = root / cfg["asset_contract"]
    if sha256_file(contract_path) != cfg["asset_contract_sha256"]:
        raise ValueError("asset contract identity mismatch")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    required = {
        "base_checkpoint_files": {"config.json", "model.safetensors", "configuration_generanno.py", "modeling_generanno.py",
                                  "tokenizer.py", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"},
        "historical_head_files": {"config.json", "pytorch_model.bin", "configuration_generanno.py", "modeling_generanno.py",
                                  "tokenizer.py", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"},
    }
    checked = []
    for key, base in (("base_checkpoint_files", root / cfg["base_checkpoint"]), ("historical_head_files", root / cfg["historical_head"])):
        missing = required[key] - set(contract[key])
        if missing:
            raise ValueError(f"asset contract omits required {key}: {sorted(missing)}")
        for relpath, expected in contract[key].items():
            path = base / relpath
            observed = sha256_file(path)
            if observed != expected:
                raise ValueError(f"checkpoint asset mismatch: {path}")
            checked.append({"path": str(path.relative_to(root)), "sha256": observed})
    for relpath, spec in contract["historical_data_files"].items():
        path = root / cfg["historical_data_dir"] / relpath
        observed = sha256_file(path)
        if observed != spec["sha256"]:
            raise ValueError(f"historical data asset mismatch: {path}")
        checked.append({"path": str(path.relative_to(root)), "sha256": observed})
    base_cfg = json.loads((root / cfg["base_checkpoint"] / "config.json").read_text(encoding="utf-8"))
    historical_cfg = json.loads((root / cfg["historical_head"] / "config.json").read_text(encoding="utf-8"))
    if base_cfg.get("model_type") != "generanno" or "AutoModelForTokenClassification" not in base_cfg.get("auto_map", {}):
        raise ValueError("base checkpoint is not a usable GENERanno token-classification initialization")
    expected_id2label = {str(k): v for k, v in ID2LABEL.items()}
    if historical_cfg.get("architectures") != ["GenerannoForTokenClassification"] or historical_cfg.get("id2label") != expected_id2label:
        raise ValueError("historical head is not the pinned six-class SF5 token head")
    return {"contract": contract, "checkpoint_files": checked}


def load_and_validate_historical(root: Path, cfg: dict, contract: dict) -> tuple[dict[str, list[dict]], dict]:
    result: dict[str, list[dict]] = defaultdict(list)
    keys, split_counts = set(), Counter()
    for split in ("train", "val", "test"):
        relpath = f"{split}/data.jsonl.gz"
        spec = contract["historical_data_files"][relpath]
        path = root / cfg["historical_data_dir"] / relpath
        if sha256_file(path) != spec["sha256"]:
            raise ValueError(f"historical data identity mismatch: {relpath}")
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                rec = json.loads(line)
                required = {"species_code", "chr", "start", "end", "sequence", "labels"}
                if not required.issubset(rec):
                    raise ValueError(f"{relpath}:{line_number} missing rejoin/schema fields")
                if int(rec["end"]) - int(rec["start"]) != len(rec["sequence"]) or len(rec["sequence"]) != len(rec["labels"]):
                    raise ValueError(f"{relpath}:{line_number} coordinate/sequence/labels length mismatch")
                if int(rec["start"]) < 0 or len(rec["sequence"]) != int(cfg["window"]):
                    raise ValueError(f"{relpath}:{line_number} invalid coordinate or non-frozen window length")
                if any(int(x) not in ID2LABEL for x in rec["labels"]):
                    raise ValueError(f"{relpath}:{line_number} invalid historical label")
                key = (rec["species_code"], rec["chr"], int(rec["start"]), int(rec["end"]), sha256_bytes(rec["sequence"].encode()))
                if key in keys:
                    raise ValueError(f"duplicate historical exact-rejoin key: {key}")
                keys.add(key)
                rec.update({"historical_split": split, "historical_line": line_number, "historical_key": key})
                result[rec["species_code"]].append(rec)
                split_counts[split] += 1
        if split_counts[split] != int(spec["records"]):
            raise ValueError(f"historical {split} records {split_counts[split]} != {spec['records']}")
    total = sum(split_counts.values())
    if total != int(contract["historical_expected_total_records"]):
        raise ValueError(f"historical total records {total} != {contract['historical_expected_total_records']}")
    return result, {"records_by_split": dict(split_counts), "total_records": total, "unique_keys": len(keys)}


def validate_species_holdout(root: Path, cfg: dict, canonical_rows: list[dict], allow_synthetic: bool = False) -> tuple[dict[str, dict], dict]:
    frozen_path = root / cfg["species_holdout_manifest"]
    source_path = root / cfg["source_species_manifest"]
    if sha256_file(frozen_path) != cfg["species_holdout_manifest_sha256"] or sha256_file(source_path) != cfg["source_species_manifest_sha256"]:
        raise ValueError("species manifest identity mismatch")
    frozen = {x["species_code"]: x for x in read_tsv(frozen_path)}
    source = {x["species_code"]: x for x in read_tsv(source_path)}
    for row in canonical_rows:
        species = row["species_code"]
        if species not in frozen or species not in source:
            raise ValueError(f"species missing frozen/source taxonomy: {species}")
        if frozen[species]["taxid"] != source[species]["taxid"] or frozen[species]["scientific_name"] != source[species]["scientific_name"]:
            raise ValueError(f"species taxonomy drift: {species}")
        if frozen[species]["role"] != row["role"]:
            raise ValueError(f"species role drift: {species}")
    if not allow_synthetic:
        taxonomy = Path(cfg["taxonomy_asset"])
        if sha256_file(taxonomy) != cfg["taxonomy_asset_sha256"]:
            raise DataContractTypedBlock("OFFICIAL_TAXONOMY_ASSET_IDENTITY_MISMATCH")
        try:
            import h5py
        except Exception as exc:
            raise DataContractTypedBlock(f"H5PY_TAXONOMY_RUNTIME_UNAVAILABLE:{type(exc).__name__}") from exc
        with h5py.File(taxonomy, "r") as handle:
            nodes = handle["Taxonomy"]
            for species, row in frozen.items():
                cursor, ancestors = int(row["taxid"]), set()
                species_names = [[v.decode() for v in pair] for pair in nodes[str(cursor)]["TaxaNames"][()]]
                species_scientific = next((name for kind, name in species_names if kind == "scientific name"), None)
                if species_scientific != row["scientific_name"]:
                    raise DataContractTypedBlock(
                        f"OFFICIAL_SPECIES_MAPPING_INVALID:{species}:{cursor}:{species_scientific}")
                while True:
                    ancestors.add(cursor)
                    node = nodes[str(cursor)]
                    if "Parent" not in node:
                        break
                    cursor = int(node["Parent"][0])
                order_id = int(row["order_taxid"])
                names = [[v.decode() for v in pair] for pair in nodes[str(order_id)]["TaxaNames"][()]]
                scientific = next((name for kind, name in names if kind == "scientific name"), None)
                if order_id not in ancestors or scientific != row["order_name"]:
                    raise DataContractTypedBlock(f"OFFICIAL_ORDER_MAPPING_INVALID:{species}:{order_id}:{scientific}")
    fit = {x["order_taxid"] for x in frozen.values() if x["evaluation_partition"] == "fit_only"}
    primary = {x["order_taxid"] for x in frozen.values() if x["evaluation_partition"] == "primary_test"}
    overlap = sorted(fit & primary)
    if overlap:
        raise DataContractTypedBlock(f"order-level clade overlap between fit and primary test: {overlap}")
    return frozen, {"holdout_unit": "order_taxid", "clade_generalization_claim": True, "fit_clade_ids": sorted(fit),
                    "primary_test_clade_ids": sorted(primary), "primary_clade_overlap_count": len(overlap),
                    "taxonomy_asset_sha256": cfg.get("taxonomy_asset_sha256", "SYNTHETIC_TEST_ONLY")}


def validate_rm_dfam_identity(root: Path, cfg: dict, species: set[str], contract: dict,
                              enforce_chunk_source_contract: bool = True) -> dict:
    readme = root / cfg["source_run_readme"]
    chunk_manifest = root / cfg["source_chunk_manifest"]
    if sha256_file(readme) != cfg["source_run_readme_sha256"] or sha256_file(chunk_manifest) != cfg["source_chunk_manifest_sha256"]:
        raise ValueError("RepeatMasker/Dfam source manifest identity mismatch")
    readme_text = readme.read_text(encoding="utf-8")
    if contract["dfam_release"] not in readme_text:
        raise ValueError("Dfam release not proven by frozen source README")
    checked = 0
    for row in read_pinned_chunk_manifest(chunk_manifest, enforce_chunk_source_contract):
        if row["species_code"] not in species:
            continue
        metadata = Path(row["output_dir"]) / "RUN_METADATA.txt"
        text = metadata.read_text(encoding="utf-8")
        if contract["repeatmasker_version"] not in text or "rm_lib_overlay" not in text:
            raise ValueError(f"RM/Dfam runtime identity missing: {metadata}")
        checked += 1
    if not checked:
        raise ValueError("no relevant RepeatMasker chunk metadata checked")
    return {"repeatmasker_version": contract["repeatmasker_version"], "dfam_release": contract["dfam_release"], "chunk_metadata_checked": checked}


def validate_canonical_targets(root: Path, cfg: dict, rows: list[dict]) -> dict:
    provenance_path = root / cfg["canonical_snapshot_provenance"]
    provenance = {x["rewritten_manifest_path_value"]: x for x in read_tsv(provenance_path)}
    checked = []
    for row in rows:
        for column in ("genome", "self_out", "comparator_plus_unknown"):
            relpath = row[column]
            if relpath not in provenance:
                raise ValueError(f"canonical target absent from provenance: {relpath}")
            item = provenance[relpath]
            ready, frozen = root / relpath, root / item["frozen_copy_project_relpath"]
            if ready.resolve() != frozen.resolve() or item["status"] != "FROZEN":
                raise ValueError(f"canonical alias/frozen target mismatch: {relpath}")
            observed = sha256_file(ready)
            if observed != item["frozen_copy_sha256"]:
                raise ValueError(f"canonical target content mismatch: {relpath}")
            checked.append({"species_code": row["species_code"], "column": column, "ready": relpath,
                            "canonical": item["frozen_copy_project_relpath"], "sha256": observed})
    return {"targets_checked": len(checked), "targets": checked}


def build(config_path: Path, attempt_dir: Path, verify_target_hashes: bool = True) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    for path_key, hash_key in (("canonical_split_manifest", "canonical_split_sha256"), ("canonical_snapshot_report", "canonical_snapshot_report_sha256"),
                               ("canonical_snapshot_provenance", "canonical_snapshot_provenance_sha256"), ("ontology", "ontology_sha256")):
        if sha256_file(root / cfg[path_key]) != cfg[hash_key]:
            raise ValueError(f"identity mismatch: {path_key}")
    snapshot = json.loads((root / cfg["canonical_snapshot_report"]).read_text(encoding="utf-8"))
    if not snapshot.get("s0_input_contract_ready") or snapshot.get("failure_codes"):
        raise ValueError("canonical snapshot S0 contract is not ready")
    rows = read_tsv(root / cfg["canonical_split_manifest"])
    species_manifest, holdout_audit = validate_species_holdout(root, cfg, rows, not verify_target_hashes)
    assets = validate_asset_tree(root, cfg)
    historical, historical_schema = load_and_validate_historical(root, cfg, assets["contract"])
    rm_dfam = validate_rm_dfam_identity(root, cfg, set(species_manifest), assets["contract"], verify_target_hashes)
    target_audit = validate_canonical_targets(root, cfg, rows) if verify_target_hashes else {"targets_checked": 0, "skipped_for_synthetic_test": True}
    ontology = load_ontology(root / cfg["ontology"])
    family_split, family_details, family_to_homology, homology_details, mapping_counts = assign_family_components(
        rows, root, cfg, ontology, not verify_target_hashes)
    data_dir = attempt_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=False)
    write_tsv(data_dir / "family_components.tsv", family_details.values(),
              ["family_component", "homology_component", "split", "roles", "labels", "ontology_terms", "annotation_records", "label_conflict"])
    write_tsv(data_dir / "homology_components.tsv", homology_details.values(),
              ["homology_component", "dfam_names", "consensus_sha256", "source", "split", "reason", "roles", "labels",
               "family_components", "label_conflict"])
    mapping_rows = [{"state": k[0], "alias_status": k[1], "ontology_term": k[2], "records": v} for k, v in sorted(mapping_counts.items())]
    write_tsv(data_dir / "ontology_mapping_audit.tsv", mapping_rows, ["state", "alias_status", "ontology_term", "records"])

    partitions = ("train", "val", "test_primary", "audit_optional_stress")
    tmp_paths = {p: data_dir / p / "data.jsonl.gz.tmp" for p in partitions}
    writers = {}
    for partition, path in tmp_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        writers[partition] = gzip.open(path, "wt", encoding="utf-8")
    counts, state_bp, class_bp, coverage = Counter(), {p: Counter() for p in partitions}, {p: Counter() for p in partitions}, Counter()
    audit_rows, rejoin_rows = [], []
    hard_terms = set(cfg["label_state_policy"]["hard_negative_terms"])
    try:
        for row in rows:
            species, role = row["species_code"], row["role"]
            tax = species_manifest[species]
            ann_by_chrom = rm_by_chrom(root / row["self_out"], ontology, hard_terms)
            b_by_chrom = read_b_intervals(root / row["comparator_plus_unknown"])
            coords = candidate_coordinates(species, ann_by_chrom, int(cfg["candidate_window_caps_per_species"][role]), int(cfg["window"]), int(cfg["seed"]))
            candidates: dict[tuple[str, int], dict] = {}
            for chrom, start in coords:
                anns = overlaps(ann_by_chrom.get(chrom, []), start, start + int(cfg["window"]))
                p_anns = [x for x in anns if x.state == "P"]
                partition, decision, families = classify_window(p_anns, family_split, role, cfg)
                candidates[(chrom, start)] = {"anns": anns, "partition": partition, "decision": decision, "families": families}
            hist_by_chrom: dict[str, list[dict]] = defaultdict(list)
            for rec in historical.get(species, []):
                hist_by_chrom[rec["chr"]].append(rec)
            wanted = {x[0] for x in coords} | set(hist_by_chrom)
            seen = set()
            for chrom, chromosome in iter_fasta(root / row["genome"]):
                if chrom not in wanted:
                    continue
                seen.add(chrom)
                for cchrom, start in (x for x in coords if x[0] == chrom):
                    desc = candidates[(cchrom, start)]
                    raw = chromosome[start:start + int(cfg["window"])]
                    painted = paint_window(raw, start, int(cfg["window"]), desc["anns"], overlaps(b_by_chrom.get(chrom, []), start, start + int(cfg["window"])))
                    n_fraction = sum(x not in "ACGT" for x in painted["sequence"]) / int(cfg["window"])
                    actual_partition, decision = desc["partition"], desc["decision"]
                    if len(raw) != int(cfg["window"]):
                        actual_partition, decision = None, "SHORT_WINDOW"
                    elif n_fraction > float(cfg["max_n_fraction"]):
                        actual_partition, decision = None, "EXCESS_N"
                    primary = role in set(cfg["holdout_policy"]["primary_test_roles"])
                    if primary:
                        coverage["primary_denominator_main4_p_bp"] += painted["counts"]["main4_p_bp"]
                    if actual_partition:
                        rec = {"sequence": painted["sequence"], "labels": painted["labels"], "state_rle": painted["state_rle"],
                               "chr": chrom, "start": start, "end": start + int(cfg["window"]), "species_code": species,
                               "species_taxid": tax["taxid"], "clade_id": tax["order_taxid"], "clade_name": tax["order_name"],
                               "role": role, "evaluation_partition": tax["evaluation_partition"], "split": actual_partition,
                               "family_components": desc["families"],
                               "homology_components": sorted({family_to_homology[x] for x in desc["families"]})}
                        writers[actual_partition].write(json.dumps(rec, separators=(",", ":")) + "\n")
                        counts[f"written_{actual_partition}"] += 1
                        state_bp[actual_partition].update(painted["states"])
                        class_bp[actual_partition].update(x for x in painted["labels"] if x != -100)
                        for key in ("label_a_only_bp", "label_a_b_overlap_bp", "label_b_only_masked_bp"):
                            counts[f"{actual_partition}_{key}"] += painted["counts"][key]
                        if actual_partition == "test_primary":
                            coverage["primary_numerator_main4_p_bp"] += painted["counts"]["main4_p_bp"]
                    counts[f"decision_{decision}"] += 1
                    audit_rows.append({"species_code": species, "species_taxid": tax["taxid"], "clade_id": tax["order_taxid"],
                                       "clade_name": tax["order_name"], "role": role, "evaluation_partition": tax["evaluation_partition"],
                                       "chr": chrom, "start": start, "end": start + int(cfg["window"]), "assigned_partition": actual_partition or "EXCLUDED",
                                       "decision": decision, "family_components": ";".join(desc["families"]),
                                       "homology_components": ";".join(sorted({family_to_homology[x] for x in desc["families"]})),
                                       "homology_component_splits": ";".join(sorted({family_split[x] for x in desc["families"]})),
                                       "main4_p_bp_same_painter": painted["counts"]["main4_p_bp"], "n_fraction": n_fraction})
                for old in hist_by_chrom.get(chrom, []):
                    start, end = int(old["start"]), int(old["end"])
                    canonical = chromosome[start:end]
                    p_anns = [x for x in overlaps(ann_by_chrom.get(chrom, []), start, end) if x.state == "P"]
                    families = sorted({x.family_component for x in p_anns})
                    exact = canonical == old["sequence"] and len(canonical) == end - start == len(old["labels"])
                    rejoin_rows.append({"historical_split": old["historical_split"], "historical_line": old["historical_line"],
                                        "species_code": species, "chr": chrom, "start": start, "end": end,
                                        "historical_sequence_sha256": old["historical_key"][4], "canonical_sequence_sha256": sha256_bytes(canonical.encode()),
                                        "rejoin_status": "EXACT" if exact else "MISMATCH", "family_components": ";".join(families),
                                        "homology_components": ";".join(sorted({family_to_homology[x] for x in families})),
                                        "homology_component_splits": ";".join(sorted({family_split[x] for x in families})),
                                        "historical_head_role": "CONTINUITY_COMPARATOR_ONLY"})
            if wanted - seen:
                raise ValueError(f"canonical FASTA chromosomes absent for {species}: {sorted(wanted-seen)[:5]}")
    finally:
        for handle in writers.values():
            handle.close()
    for partition, tmp in tmp_paths.items():
        os.replace(tmp, data_dir / partition / "data.jsonl.gz")
    write_tsv(data_dir / "window_split_audit.tsv", audit_rows,
              ["species_code", "species_taxid", "clade_id", "clade_name", "role", "evaluation_partition", "chr", "start", "end",
               "assigned_partition", "decision", "family_components", "homology_components", "homology_component_splits",
               "main4_p_bp_same_painter", "n_fraction"])
    write_tsv(data_dir / "HISTORICAL_HEAD_CANONICAL_REJOIN_V1.tsv", rejoin_rows,
              ["historical_split", "historical_line", "species_code", "chr", "start", "end", "historical_sequence_sha256",
               "canonical_sequence_sha256", "rejoin_status", "family_components", "homology_components", "homology_component_splits",
               "historical_head_role"])
    exact_by_split = Counter(x["historical_split"] for x in rejoin_rows if x["rejoin_status"] == "EXACT")
    if len(rejoin_rows) != historical_schema["total_records"] or sum(exact_by_split.values()) != historical_schema["total_records"]:
        raise ValueError(f"historical exact rejoin incomplete: {sum(exact_by_split.values())}/{historical_schema['total_records']}")
    denominator = coverage["primary_denominator_main4_p_bp"]
    numerator = coverage["primary_numerator_main4_p_bp"]
    metadata = {
        "schema_version": "TEFM-SF5-HOMOLOGY-CLADE-BLOCKED-DATA-3.0.0", "holdout": holdout_audit,
        "homology_component_policy": cfg["homology_component_policy"],
        "homology_component_counts": dict(Counter(x["split"] for x in homology_details.values())),
        "counts": dict(counts), "state_bp": {p: dict(v) for p, v in state_bp.items()},
        "class_bp": {p: {ID2LABEL[k]: int(v) for k, v in sorted(c.items())} for p, c in class_bp.items()},
        "coverage_contract": {"painter": "P>hardN>U>RN", "denominator": "all deterministic primary candidate main4 P bp including mixed/mismatch/short/N exclusions",
                              "numerator": "main4 P bp physically written to test_primary only"},
        "eligible_main4_coverage": numerator / denominator if denominator else 0.0,
        "primary_denominator_main4_p_bp": denominator, "primary_numerator_main4_p_bp": numerator,
        "historical_rejoin": {**historical_schema, "exact_by_split": dict(exact_by_split), "exact_total": sum(exact_by_split.values()),
                              "role": "CONTINUITY_COMPARATOR_ONLY"},
        "ontology_sha256": cfg["ontology_sha256"], "canonical_target_audit": target_audit, "rm_dfam_identity": rm_dfam,
        "checkpoint_asset_count": len(assets["checkpoint_files"]), "random_split_used": False, "chromosome_split_used": False,
        "test_calibration_count": 0, "audit_physically_separate": True,
    }
    atomic_json(data_dir / "metadata.json", metadata)
    atomic_json(data_dir / "label_map.json", {str(k): v for k, v in ID2LABEL.items()})
    atomic_json(data_dir / "state_map.json", {str(k): v for k, v in ID2STATE.items()})
    atomic_json(attempt_dir / "asset_verification.json", {"checkpoints": assets["checkpoint_files"], "canonical": target_audit,
                                                           "rm_dfam": rm_dfam, "historical": historical_schema})
    return metadata


def validate_rejoin_rows(rows: list[dict], expected_by_split: dict[str, int]) -> dict:
    seen, counts, exact = set(), Counter(), Counter()
    for row in rows:
        key = (row["species_code"], row["chr"], row["start"], row["end"], row["historical_sequence_sha256"])
        if key in seen:
            raise ValueError(f"duplicate rejoin manifest key: {key}")
        seen.add(key)
        counts[row["historical_split"]] += 1
        exact[row["historical_split"]] += row["rejoin_status"] == "EXACT"
    if dict(counts) != expected_by_split or dict(exact) != expected_by_split:
        raise ValueError(f"rejoin split counts/exact mismatch: rows={dict(counts)} exact={dict(exact)} expected={expected_by_split}")
    return {"rows_by_split": dict(counts), "exact_by_split": dict(exact), "unique_keys": len(seen)}


def verify(config_path: Path, attempt_dir: Path, output: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    data = attempt_dir / "data"
    families = {x["family_component"]: x for x in read_tsv(data / "family_components.tsv")}
    homology = {x["homology_component"]: x for x in read_tsv(data / "homology_components.tsv")}
    errors, observed, observed_families, windows = [], defaultdict(set), defaultdict(set), Counter()
    partition_roles = {"train": {cfg["holdout_policy"]["fit_role"]}, "val": {cfg["holdout_policy"]["fit_role"]},
                       "test_primary": set(cfg["holdout_policy"]["primary_test_roles"]),
                       "audit_optional_stress": set(cfg["holdout_policy"]["audit_only_roles"])}
    fit_clades, primary_clades, fit_species, primary_species, primary_species_codes = set(), set(), set(), set(), set()
    for partition, roles in partition_roles.items():
        with gzip.open(data / partition / "data.jsonl.gz", "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                rec = json.loads(line)
                states = expand_state_rle(rec["state_rle"], len(rec["labels"]))
                if rec["role"] not in roles or rec["split"] != partition:
                    errors.append(f"{partition}:{line_number}: role/split mismatch")
                expected = "test" if partition in {"test_primary", "audit_optional_stress"} else partition
                split_set = {homology[x]["split"] for x in rec["homology_components"]}
                if split_set != {expected}:
                    errors.append(f"{partition}:{line_number}: homology component splits={sorted(split_set)}")
                mapped = {families[x]["homology_component"] for x in rec["family_components"]}
                if mapped != set(rec["homology_components"]):
                    errors.append(f"{partition}:{line_number}: family-to-homology mapping mismatch")
                if any((state == "U") != (int(label) == -100) for state, label in zip(states, rec["labels"])):
                    errors.append(f"{partition}:{line_number}: U/loss-mask mismatch")
                for component in rec["homology_components"]:
                    observed[component].add(partition)
                for family in rec["family_components"]:
                    observed_families[family].add(partition)
                (fit_clades if partition in {"train", "val"} else primary_clades if partition == "test_primary" else set()).add(rec["clade_id"])
                (fit_species if partition in {"train", "val"} else primary_species if partition == "test_primary" else set()).add(rec["species_taxid"])
                if partition == "test_primary":
                    primary_species_codes.add(rec["species_code"])
                windows[partition] += 1
    component_overlap = {x: sorted(v) for x, v in observed.items() if ({"train", "val"} <= v or (v & {"train", "val"} and v & {"test_primary", "audit_optional_stress"}))}
    if component_overlap:
        errors.append(f"homology component overlap count={len(component_overlap)}")
    clade_overlap = fit_clades & primary_clades
    if clade_overlap:
        errors.append(f"fit/primary clade overlap={sorted(clade_overlap)}")
    family_overlap = {x: sorted(v) for x, v in observed_families.items() if ({"train", "val"} <= v or
                      (v & {"train", "val"} and v & {"test_primary", "audit_optional_stress"}))}
    species_overlap = fit_species & primary_species
    frozen_species_rows = read_tsv(Path(cfg["project_root"]) / cfg["species_holdout_manifest"])
    expected_primary_species = {x["species_code"] for x in frozen_species_rows if x["evaluation_partition"] == "primary_test"}
    expected_primary_clades = {x["order_taxid"] for x in frozen_species_rows if x["evaluation_partition"] == "primary_test"}
    if primary_species_codes != expected_primary_species:
        errors.append(f"primary species support mismatch observed={sorted(primary_species_codes)} expected={sorted(expected_primary_species)}")
    if primary_clades != expected_primary_clades:
        errors.append(f"primary clade support mismatch observed={sorted(primary_clades)} expected={sorted(expected_primary_clades)}")
    contract = json.loads((Path(cfg["project_root"]) / cfg["asset_contract"]).read_text(encoding="utf-8"))
    rejoin = validate_rejoin_rows(read_tsv(data / "HISTORICAL_HEAD_CANONICAL_REJOIN_V1.tsv"),
                                  {k: int(contract["historical_data_files"][f"{k}/data.jsonl.gz"]["records"]) for k in ("train", "val", "test")})
    metadata = json.loads((data / "metadata.json").read_text(encoding="utf-8"))
    if metadata["counts"].get("written_audit_optional_stress", 0) != windows["audit_optional_stress"]:
        errors.append("audit window count mismatch")
    result = {"schema_version": "TEFM-SF5-HOMOLOGY-CLADE-LEAKAGE-AUDIT-3.0.0", "pass": not errors,
              "homology_component_overlap_count": len(component_overlap), "primary_clade_overlap_count": len(clade_overlap),
              "family_component_overlap_count_secondary": len(family_overlap),
              "primary_species_overlap_count_secondary": len(species_overlap),
              "holdout_unit": "order_taxid", "clade_generalization_claim": True, "window_counts": dict(windows),
              "primary_species_codes": sorted(primary_species_codes), "expected_primary_species_codes": sorted(expected_primary_species),
              "primary_clade_ids": sorted(primary_clades), "expected_primary_clade_ids": sorted(expected_primary_clades),
              "audit_physically_separate": True, "audit_in_numeric_gate": False,
              "cross_split_mixed_windows_excluded": metadata["counts"].get("decision_CROSS_SPLIT_MIXED", 0),
              "eligible_main4_coverage": metadata["eligible_main4_coverage"], "historical_rejoin": rejoin,
              "test_calibration_count": 0, "random_split_used": False, "chromosome_split_used": False, "errors": errors}
    atomic_json(output, result)
    if errors:
        raise SystemExit("data/leakage audit failed: " + "; ".join(errors[:5]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--config", required=True, type=Path)
        p.add_argument("--attempt-dir", required=True, type=Path)
        p.add_argument("--output", type=Path)
        p.add_argument("--skip-target-hashes", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "build":
            value = build(args.config.resolve(), args.attempt_dir.resolve(), not args.skip_target_hashes)
        else:
            if args.output is None:
                raise SystemExit("verify requires --output")
            value = verify(args.config.resolve(), args.attempt_dir.resolve(), args.output.resolve())
    except DataContractTypedBlock as exc:
        atomic_json(args.attempt_dir.resolve() / "typed_block.json", {"status": "DATA_TYPED_BLOCK", "reason": str(exc),
                    "scientific_screen_executed": False, "gpu_stage_authorized": False})
        raise SystemExit(2)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
