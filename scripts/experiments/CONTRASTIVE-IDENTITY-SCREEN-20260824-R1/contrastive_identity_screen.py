#!/usr/bin/env python3
"""Fail-closed, identity-aware contrastive-learning screen.

This is deliberately a small standalone screen rather than a replacement for
the historical Module 5 code.  It accepts JSONL/TSV fragment records and has
two safe outcomes:

* incomplete family/copy/component provenance -> emit manifests and a typed
  ``BLOCKED_IDENTITY_FIELDS`` report, without inventing identities or metrics;
* complete provenance -> split connected identity groups first, then crop or
  augment, and run frozen 6-mer (and optional frozen base embedding)
  clustering with DBSCAN.  DBSCAN is used so the primary result never takes an
  oracle K.  A supervised family projection, when requested, is written only
  under ``supervised_family_contrastive_upper_bound``.

The expected record schema is intentionally explicit.  ``family`` and
``fragment_id`` are accepted as transparent aliases, but coordinates are not
silently converted into copy identities.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REQUIRED_FIELDS = ("id", "sequence", "superfamily_id", "family_id", "copy_id", "homology_component_id")
ALIASES = {"id": ("fragment_id", "record_id"), "family_id": ("family",)}
MISSING = {"", "na", "n/a", "none", "null", "unknown", "missing", "."}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def atomic_json(path: Path, value: object) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")


def load_rows(path: Path) -> list[dict]:
    with open_text(path) as handle:
        if path.name.endswith((".jsonl", ".jsonl.gz")):
            return [json.loads(line) for line in handle if line.strip()]
        return list(csv.DictReader(handle, delimiter="\t"))


def value(row: dict, field: str) -> str:
    if field in row:
        return "" if row[field] is None else str(row[field]).strip()
    for alias in ALIASES.get(field, ()):
        if alias in row:
            return "" if row[alias] is None else str(row[alias]).strip()
    return ""


def normalize_rows(rows: Iterable[dict]) -> list[dict]:
    normalized = []
    for index, row in enumerate(rows):
        item = dict(row)
        for field in REQUIRED_FIELDS:
            item[field] = value(row, field)
        item["_input_row"] = index
        normalized.append(item)
    return normalized


def identity_audit(rows: list[dict]) -> dict:
    missing_counts = Counter()
    duplicate_ids = Counter()
    sequence_hashes = Counter()
    for row in rows:
        for field in REQUIRED_FIELDS:
            if row[field].lower() in MISSING:
                missing_counts[field] += 1
        if row["id"]:
            duplicate_ids[row["id"]] += 1
        if row["sequence"]:
            sequence_hashes[hashlib.sha256(row["sequence"].upper().encode()).hexdigest()] += 1
    duplicate_id_count = sum(n - 1 for n in duplicate_ids.values() if n > 1)
    duplicate_sequence_count = sum(n - 1 for n in sequence_hashes.values() if n > 1)
    missing_fields = {field: count for field, count in missing_counts.items() if count}
    blockers = []
    if missing_fields:
        blockers.append("missing_required_identity_fields")
    if duplicate_id_count:
        blockers.append("duplicate_fragment_ids")
    return {
        "status": "PASS" if not blockers else "BLOCKED_IDENTITY_FIELDS",
        "records": len(rows),
        "required_fields": list(REQUIRED_FIELDS),
        "accepted_aliases": ALIASES,
        "missing_field_counts": {field: missing_fields.get(field, 0) for field in REQUIRED_FIELDS},
        "duplicate_fragment_id_count": duplicate_id_count,
        "duplicate_canonical_sequence_count": duplicate_sequence_count,
        "blockers": blockers,
    }


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[b] = a


def build_identity_groups(rows: list[dict]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Connect family, namespaced copy, and homology IDs; no group can split.

    Copy identifiers in RepeatMasker/fragment exports are often only unique
    within a family.  Therefore ``copy_id`` is *never* used as a global key;
    its union key is ``(family_id, copy_id)``.  Homology components remain
    global because they are explicitly intended to join homologous families.
    """
    uf = UnionFind(len(rows))
    by_key = defaultdict(list)
    for index, row in enumerate(rows):
        by_key[("family_id", row["family_id"])].append(index)
        by_key[("copy_id", row["family_id"], row["copy_id"])].append(index)
        by_key[("homology_component_id", row["homology_component_id"])].append(index)
    for indices in by_key.values():
        for index in indices[1:]:
            uf.union(indices[0], index)
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        groups[uf.find(index)].append(row["id"])
    group_by_id = {}
    group_rows = {}
    for number, ids in enumerate(sorted(groups.values(), key=lambda x: x[0])):
        group = f"identity_group_{number:06d}"
        group_rows[group] = ids
        group_by_id.update({record_id: group for record_id in ids})
    return group_by_id, group_rows


def assign_splits(rows: list[dict], seed: int) -> tuple[dict[str, str], dict[str, list[str]]]:
    by_id, groups = build_identity_groups(rows)
    split_by_group = {}
    for group in groups:
        digest = hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()
        fraction = int(digest[:12], 16) / float(16**12)
        split_by_group[group] = "train" if fraction < 0.8 else "val" if fraction < 0.9 else "test"
    split_by_id = {record_id: split_by_group[group] for record_id, group in by_id.items()}
    return split_by_id, groups


def leakage_audit(rows: list[dict], split_by_id: dict[str, str]) -> dict:
    fields = ("family_id", "copy_id", "homology_component_id")
    overlap = {}
    for field in fields:
        memberships = defaultdict(set)
        for row in rows:
            key = (row["family_id"], row["copy_id"]) if field == "copy_id" else row[field]
            memberships[key].add(split_by_id[row["id"]])
        overlap[field] = sorted(key for key, splits in memberships.items() if len(splits) > 1)
    seq_splits = defaultdict(set)
    for row in rows:
        digest = hashlib.sha256(row["sequence"].upper().encode()).hexdigest()
        seq_splits[digest].add(split_by_id[row["id"]])
    exact_sequence_cross_split = sum(1 for splits in seq_splits.values() if len(splits) > 1)
    return {
        "group_fields": list(fields),
        "cross_split_overlap_counts": {field: len(keys) for field, keys in overlap.items()},
        "cross_split_overlap_examples": {field: keys[:10] for field, keys in overlap.items()},
        "exact_canonical_sequence_cross_split_count": exact_sequence_cross_split,
        "pass": not any(overlap.values()) and exact_sequence_cross_split == 0,
    }


def crop_and_augment(rows: list[dict], split_by_id: dict[str, str], crop_length: int | None, augment: bool) -> list[dict]:
    """Transform after split; the caller must pass an already assigned split."""
    output = []
    for row in rows:
        seq = row["sequence"].upper()
        if crop_length and len(seq) > crop_length:
            start = (len(seq) - crop_length) // 2
            seq = seq[start:start + crop_length]
        transformed = dict(row)
        transformed["sequence"] = seq
        transformed["split"] = split_by_id[row["id"]]
        transformed["transform_stage"] = "after_group_split"
        output.append(transformed)
        if augment:
            reverse = str.maketrans("ACGTN", "TGCAN")
            augmented = dict(transformed)
            augmented["id"] = row["id"] + "::revcomp"
            augmented["sequence"] = seq.translate(reverse)[::-1]
            augmented["augmentation_of"] = row["id"]
            augmented["transform_stage"] = "after_group_split"
            output.append(augmented)
    return output


def kmer_features(sequences: list[str], k: int = 6):
    import numpy as np
    alphabet = "ACGT"
    kmers = ["".join(parts) for parts in itertools.product(alphabet, repeat=k)]
    index = {item: i for i, item in enumerate(kmers)}
    features = np.zeros((len(sequences), len(kmers)), dtype=np.float32)
    for row_index, sequence in enumerate(sequences):
        for start in range(max(0, len(sequence) - k + 1)):
            token = sequence[start:start + k]
            if token in index:
                features[row_index, index[token]] += 1
        total = features[row_index].sum()
        if total:
            features[row_index] /= total
    return features


def pair_count(rows: list[dict], split: str = "train") -> dict:
    by_family = defaultdict(Counter)
    for row in rows:
        if row.get("split") == split:
            by_family[row["family_id"]][row["copy_id"]] += 1
    pairs = 0
    family_count = 0
    eligible_rows = 0
    for copies in by_family.values():
        if len(copies) > 1:
            family_count += 1
            eligible_rows += sum(copies.values())
            total = sum(copies.values())
            pairs += (total * total - sum(n * n for n in copies.values())) // 2
    return {"families_with_different_copy_positives": family_count, "eligible_rows": eligible_rows, "positive_pair_count": pairs}


def _bcubed_and_purity(assignments, family_labels: list[str], superfamily_labels: list[str]) -> dict:
    """Return label-aware diagnostics without fitting or selecting K."""
    from collections import defaultdict
    import itertools

    cluster_members = defaultdict(list)
    family_members = defaultdict(list)
    for index, cluster in enumerate(assignments):
        cluster_members[int(cluster)].append(index)
        family_members[family_labels[index]].append(index)

    precision = []
    recall = []
    for index, cluster in enumerate(assignments):
        cluster_set = set(cluster_members[int(cluster)])
        family_set = set(family_members[family_labels[index]])
        overlap = len(cluster_set & family_set)
        precision.append(overlap / len(cluster_set))
        recall.append(overlap / len(family_set))
    bc_precision = sum(precision) / len(precision) if precision else None
    bc_recall = sum(recall) / len(recall) if recall else None
    bc_f1 = (2 * bc_precision * bc_recall / (bc_precision + bc_recall)) if bc_precision is not None and bc_recall is not None and bc_precision + bc_recall else None

    assigned = [cluster for cluster in cluster_members if cluster != -1]
    purity_denominator = sum(len(cluster_members[cluster]) for cluster in assigned)
    purity_numerator = sum(max(Counter(family_labels[index] for index in cluster_members[cluster]).values()) for cluster in assigned)
    family_purity = purity_numerator / purity_denominator if purity_denominator else None

    false_link_pairs = 0
    linked_pairs = 0
    for cluster in assigned:
        members = cluster_members[cluster]
        for left, right in itertools.combinations(members, 2):
            linked_pairs += 1
            if superfamily_labels[left] == superfamily_labels[right] and family_labels[left] != family_labels[right]:
                false_link_pairs += 1
    return {
        "bcubed_precision": bc_precision,
        "bcubed_recall": bc_recall,
        "bcubed_f1": bc_f1,
        "family_purity_weighted_non_noise": family_purity,
        "same_superfamily_different_family_false_link_rate": (false_link_pairs / linked_pairs) if linked_pairs else None,
        "same_superfamily_different_family_false_link_pairs": false_link_pairs,
        "same_cluster_pair_denominator_non_noise": linked_pairs,
    }


def cluster_metrics(features, labels: list[str], superfamily_labels: list[str], method: str, eps: float, min_samples: int, eps_multipliers: list[float]) -> dict:
    from sklearn.cluster import DBSCAN
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    import numpy as np
    # Standardization is fitted on the train-free feature matrix only; no labels
    # or K are consulted.  The frozen representation itself is never updated.
    matrix = np.asarray(features, dtype=np.float32)
    assignments = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit_predict(matrix)
    valid_labels = len(set(labels)) > 1
    ari = float(adjusted_rand_score(labels, assignments)) if valid_labels else None
    nmi = float(normalized_mutual_info_score(labels, assignments)) if valid_labels else None
    repeat_assignments = []
    for multiplier in eps_multipliers:
        repeat_assignments.append(DBSCAN(eps=eps * multiplier, min_samples=min_samples, metric="cosine").fit_predict(matrix))
    pairwise = [adjusted_rand_score(a, b) for a, b in itertools.combinations(repeat_assignments, 2)]
    noise = float(np.mean(assignments == -1)) if len(assignments) else None
    result = {
        "status": "PASS",
        "cluster_method": method,
        "oracle_k_used": False,
        "k_source": "algorithm/no-k",
        "n_clusters": int(len(set(assignments)) - (1 if -1 in assignments else 0)),
        "noise_fraction": noise,
        "ari": ari,
        "nmi": nmi,
        "eps_sensitivity_pairwise_ari": float(np.mean(pairwise)) if pairwise else None,
        "eps_sensitivity_multipliers": eps_multipliers,
        "denominator": len(labels),
    }
    result.update(_bcubed_and_purity(assignments, labels, superfamily_labels))
    return result


def write_manifest(output: Path, rows: list[dict], split_by_id: dict[str, str] | None) -> None:
    fields = ["id", "split", "family_id", "copy_id", "homology_component_id", "sequence_length", "transform_stage"]
    lines = ["\t".join(fields)]
    for row in rows:
        split = row.get("split") or (split_by_id.get(row["id"], "BLOCKED") if split_by_id else "BLOCKED")
        lines.append("\t".join(str(x) for x in (row["id"], split, row["family_id"], row["copy_id"], row["homology_component_id"], len(row["sequence"]), row.get("transform_stage", "not_run"))))
    atomic_write(output / "screen_manifest.tsv", "\n".join(lines) + "\n")


def blocked_outputs(output: Path, config: dict, audit: dict, reason: str) -> int:
    report = {
        "schema_version": "TEFM-CONTRASTIVE-ID-GATE-1.0.0",
        "status": "BLOCKED_IDENTITY_FIELDS",
        "scientific_screen_executed": False,
        "claim_eligible": False,
        "reason": reason,
        "identity_audit": audit,
        "metrics": {
            "denominator": audit["records"],
            "ari": None,
            "nmi": None,
            "eps_sensitivity_pairwise_ari": None,
            "noise_fraction": None,
            "bcubed_precision": None,
            "bcubed_recall": None,
            "bcubed_f1": None,
            "family_purity_weighted_non_noise": None,
            "same_superfamily_different_family_false_link_rate": None,
            "oracle_k_used": False,
        },
    }
    atomic_json(output / "metrics.json", report["metrics"])
    atomic_json(output / "screen_report.json", report)
    atomic_write(output / "STATUS", "BLOCKED_IDENTITY_FIELDS\n")
    return 2


def run(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve(); output.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        atomic_write(output / "STATUS", "BLOCKED_INPUT_MISSING\n")
        atomic_json(output / "screen_report.json", {"status": "BLOCKED_INPUT_MISSING", "input": str(input_path), "claim_eligible": False})
        return 2
    raw = load_rows(input_path)
    rows = normalize_rows(raw)
    audit = identity_audit(rows)
    config = {"input": str(input_path), "input_sha256": sha256_file(input_path), "seed": args.seed, "crop_length": args.crop_length, "augment": args.augment, "split_before_crop_or_augment": True, "oracle_k_used": False}
    atomic_json(output / "input_manifest.json", {"schema_version": "TEFM-CONTRASTIVE-INPUT-1.0.0", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "config": config, "denominator": {"records": len(rows)}, "identity_audit": audit})
    if audit["status"] != "PASS":
        write_manifest(output, rows, None)
        return blocked_outputs(output, config, audit, "family/copy/superfamily/component identity is not complete; no labels or copies were inferred")

    split_by_id, groups = assign_splits(rows, args.seed)
    transformed = crop_and_augment(rows, split_by_id, args.crop_length, args.augment)
    atomic_json(output / "split_manifest.json", {"split_policy": "connected family/copy/homology-component groups", "groups": len(groups), "split_counts": dict(Counter(split_by_id.values())), "split_before_crop_or_augment": True})
    audit_leak = leakage_audit(rows, split_by_id)
    atomic_json(output / "leakage_audit.json", audit_leak)
    write_manifest(output, transformed, split_by_id)
    metrics = {"schema_version": "TEFM-CONTRASTIVE-METRICS-1.0.0", "status": "PASS" if audit_leak["pass"] else "BLOCKED_LEAKAGE", "claim_eligible": audit_leak["pass"], "denominator": {"input_rows": len(rows), "transformed_rows": len(transformed), "train_rows": sum(r["split"] == "train" for r in transformed), "val_rows": sum(r["split"] == "val" for r in transformed), "test_rows": sum(r["split"] == "test" for r in transformed)}, "leakage_audit": audit_leak, "positive_pair_audit": pair_count(transformed), "oracle_k_used": False, "representations": {}}
    if not audit_leak["pass"]:
        atomic_json(output / "metrics.json", metrics); atomic_write(output / "STATUS", "BLOCKED_LEAKAGE\n"); return 2

    test_rows = [r for r in transformed if r["split"] == "test"]
    if len(test_rows) < 2:
        metrics["status"] = "BLOCKED_TEST_DENOMINATOR"; metrics["claim_eligible"] = False
    else:
        try:
            sequence_features = kmer_features([r["sequence"] for r in test_rows])
            metrics["representations"]["frozen_6mer"] = cluster_metrics(sequence_features, [r["family_id"] for r in test_rows], [r["superfamily_id"] for r in test_rows], "DBSCAN", args.eps, args.min_samples, args.eps_sensitivity_multipliers)
            if args.base_embeddings:
                import numpy as np
                base = np.load(args.base_embeddings, mmap_mode="r")
                if base.shape[0] != len(rows):
                    raise ValueError(f"base embedding row denominator mismatch: {base.shape[0]} != {len(rows)}")
                by_input = {r["_input_row"]: r for r in test_rows}
                base_test = np.asarray([base[r["_input_row"]] for r in test_rows])
                metrics["representations"]["frozen_base_embedding"] = cluster_metrics(base_test, [r["family_id"] for r in test_rows], [r["superfamily_id"] for r in test_rows], "DBSCAN", args.eps, args.min_samples, args.eps_sensitivity_multipliers)
        except (ImportError, ValueError) as exc:
            metrics["status"] = "BLOCKED_DEPENDENCY_OR_EMBEDDING"; metrics["claim_eligible"] = False; metrics["blocker"] = str(exc)
    metrics["supervised_family_contrastive_upper_bound"] = {"status": "NOT_RUN", "claim_type": "upper_bound_only", "never_primary": True, "label_source": "family_id", "split": "train_only"}
    atomic_json(output / "metrics.json", metrics)
    atomic_write(output / "STATUS", metrics["status"] + "\n")
    atomic_json(output / "screen_report.json", {"schema_version": "TEFM-CONTRASTIVE-SCREEN-1.0.0", "status": metrics["status"], "claim_eligible": metrics["claim_eligible"], "scientific_screen_executed": metrics["status"] == "PASS", "config": config, "metrics_path": "metrics.json", "representation_policy": "frozen label-free 6mer/base comparator; no oracle K; family contrastive is upper bound only"})
    return 0 if metrics["status"] == "PASS" else 2


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, help="JSONL/JSONL.GZ or TSV fragments")
    p.add_argument("--output", required=True)
    p.add_argument("--base-embeddings", help="Optional frozen .npy matrix in input-row order")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--crop-length", type=int, default=None)
    p.add_argument("--augment", action="store_true", help="Reverse-complement after split")
    p.add_argument("--eps", type=float, default=0.25)
    p.add_argument("--min-samples", type=int, default=5)
    p.add_argument("--eps-sensitivity-multipliers", type=float, nargs="+", default=[1.0, 1.05, 1.10], help="DBSCAN eps multipliers for sensitivity, not random seeds")
    return p


if __name__ == "__main__":
    raise SystemExit(run(parser().parse_args()))
