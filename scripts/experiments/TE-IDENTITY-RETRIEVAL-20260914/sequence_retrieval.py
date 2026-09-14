#!/usr/bin/env python3
"""Run the annotation-level sequence retrieval comparison.

The input must be the identity-aware manifest produced by
``build_natural_panel.py``.  This runner uses only natural genomic interval
sequences for the train-copy arms and only the explicit consensus row for the
single-consensus arm.  It computes a standard k-mer cosine representation and
reports top-1 family retrieval with one fixed CAL false-accept budget per arm.

The output is numeric evidence at the annotated-family level.  The source
copy IDs are coordinate-derived and do not establish biological insertion
identity; therefore this command never reports a biological insertion claim.
GLM and profile-HMM arms are listed as NOTRUN unless a later runner supplies
their explicit inputs.  No random embedding is generated here.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("identity_retrieval", HERE / "identity_retrieval.py")
assert SPEC is not None and SPEC.loader is not None
identity = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = identity
SPEC.loader.exec_module(identity)


SEED = 42
KMER_SIZE = 6
CAL_ALPHA = 0.01
CAL_MIN_NEGATIVES = 100
NATURAL = identity.NATURAL_COPY_KINDS
CONSENSUS = identity.CONSENSUS_KINDS


def kmer_vector(sequence: str, k: int = KMER_SIZE) -> Dict[str, float]:
    counts = Counter()
    sequence = sequence.upper()
    for index in range(len(sequence) - k + 1):
        kmer = sequence[index:index + k]
        if "N" not in kmer:
            counts[kmer] += 1
    total = sum(counts.values())
    if not total:
        return {}
    return {key: value / float(total) for key, value in counts.items()}


def cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(value * right.get(key, 0.0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def mean_vectors(vectors: Sequence[Mapping[str, float]]) -> Dict[str, float]:
    output = Counter()
    for vector in vectors:
        for key, value in vector.items():
            output[key] += value
    if not vectors:
        return {}
    return {key: value / float(len(vectors)) for key, value in output.items()}


def sequence_for(row: Mapping[str, str]) -> str:
    sequence = row.get("sequence", "")
    if sequence:
        return sequence.upper()
    path = row.get("sequence_path", "")
    if path:
        candidate = Path(path)
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").replace("\n", "").replace("\r", "").upper()
    return ""


def select_methods(rows: Sequence[Mapping[str, str]], k: int = KMER_SIZE) -> Tuple[Dict[str, Dict[str, object]], dict]:
    natural = [row for row in rows if row["source_kind"] in NATURAL]
    consensus = [row for row in rows if row["source_kind"] in CONSENSUS]
    train_by_family: Dict[str, List[dict]] = defaultdict(list)
    cal_by_family: Dict[str, List[dict]] = defaultdict(list)
    eval_by_family: Dict[str, List[dict]] = defaultdict(list)
    for row in natural:
        if not row["family_id"]:
            continue
        if row["split"] == "train":
            train_by_family[row["family_id"]].append(dict(row))
        elif row["split"] == "cal":
            cal_by_family[row["family_id"]].append(dict(row))
        elif row["split"] == "eval":
            eval_by_family[row["family_id"]].append(dict(row))
    consensus_by_family = {}
    for row in consensus:
        if row["family_id"] and row["family_id"] not in consensus_by_family:
            consensus_by_family[row["family_id"]] = dict(row)
    all_families = set(train_by_family) & set(cal_by_family) & set(eval_by_family)
    matched = sorted(
        family for family in all_families
        if len({identity.canonical_copy_key(row) for row in train_by_family[family]}) >= 4
        and family in consensus_by_family
        and all(sequence_for(row) for row in train_by_family[family] + cal_by_family[family] + eval_by_family[family])
        and sequence_for(consensus_by_family[family])
    )
    methods: Dict[str, Dict[str, object]] = {}
    if matched:
        methods["single_consensus"] = {
            family: [consensus_by_family[family]] for family in matched
        }
        methods["single_train_medoid"] = {
            family: select_k_medoids(train_by_family[family], 1, k)
            for family in matched
        }
        methods["k4_natural_prototypes"] = {
            family: select_k_medoids(train_by_family[family], 4, k)
            for family in matched
        }
        methods["random4_natural_prototypes"] = {}
        for family in matched:
            candidates = sorted(train_by_family[family], key=lambda row: row["record_id"])
            methods["random4_natural_prototypes"][family] = random.Random(SEED).sample(candidates, 4)
        methods["basic_train_centroid"] = {
            family: train_by_family[family] for family in matched
        }
    info = {
        "all_families_with_train_cal_eval": sorted(all_families),
        "matched_families": matched,
        "not_matched_families": sorted(all_families - set(matched)),
        "natural_family_counts": {
            "train": {family: len(train_by_family[family]) for family in sorted(train_by_family)},
            "cal": {family: len(cal_by_family[family]) for family in sorted(cal_by_family)},
            "eval": {family: len(eval_by_family[family]) for family in sorted(eval_by_family)},
        },
        "consensus_families": sorted(consensus_by_family),
    }
    return methods, {"index": info, "train": train_by_family, "cal": cal_by_family, "eval": eval_by_family}


def select_k_medoids(rows: Sequence[Mapping[str, str]], k: int, kmer_size: int = KMER_SIZE) -> List[dict]:
    """Select deterministic TRAIN medoids using the fixed k-mer distance.

    The first medoid minimizes total distance to the family's TRAIN copies.
    Each following medoid is the candidate that minimizes the total distance
    after adding it to the selected set.  This is a bounded greedy PAM-style
    rule: it is easy to audit, uses no EVAL/CAL sequence, and does not pretend
    that the first four records represent family diversity.
    """

    candidates = sorted((dict(row) for row in rows), key=lambda row: (row.get("host_locus", ""), row["source_copy_id"], row["record_id"]))
    if len(candidates) < k:
        raise ValueError("k-medoids requires at least %d TRAIN rows" % k)
    vectors = {row["record_id"]: kmer_vector(sequence_for(row), kmer_size) for row in candidates}

    def distance(left: Mapping[str, str], right: Mapping[str, str]) -> float:
        return 1.0 - cosine(vectors[left["record_id"]], vectors[right["record_id"]])

    first = min(
        candidates,
        key=lambda row: (
            round(sum(distance(row, other) for other in candidates), 12),
            row.get("host_locus", ""), row["source_copy_id"], row["record_id"],
        ),
    )
    selected = [first]
    while len(selected) < k:
        remaining = [row for row in candidates if row["record_id"] not in {item["record_id"] for item in selected}]
        choice = min(
            remaining,
            key=lambda row: (
                round(sum(min(distance(other, medoid) for medoid in selected + [row]) for other in candidates), 12),
                row.get("host_locus", ""), row["source_copy_id"], row["record_id"],
            ),
        )
        selected.append(choice)
    return selected


def prototype_vectors(method: str, prototype_rows: object, k: int) -> Dict[str, object]:
    output = {}
    for family, family_rows in prototype_rows.items():
        if method == "basic_train_centroid":
            vectors = [kmer_vector(sequence_for(row), k) for row in family_rows]
            output[family] = mean_vectors(vectors)
        else:
            output[family] = [kmer_vector(sequence_for(row), k) for row in family_rows]
    return output


def family_scores(query: Mapping[str, str], vectors: Mapping[str, object], method: str, k: int) -> Dict[str, float]:
    query_vector = kmer_vector(sequence_for(query), k)
    scores = {}
    for family, prototypes in vectors.items():
        if method == "basic_train_centroid":
            scores[family] = cosine(query_vector, prototypes)
        else:
            scores[family] = max((cosine(query_vector, prototype) for prototype in prototypes), default=0.0)
    return scores


def calibrate_method(
    method: str,
    vectors: Mapping[str, object],
    cal_rows: Mapping[str, Sequence[Mapping[str, str]]],
    families: Sequence[str],
    k: int,
) -> dict:
    scores, labels = [], []
    for family in families:
        for query in cal_rows.get(family, []):
            by_family = family_scores(query, vectors, method, k)
            for candidate_family in families:
                scores.append(by_family[candidate_family])
                labels.append(int(candidate_family == family))
    negatives = sum(1 for label in labels if not label)
    if not scores or not negatives:
        return {
            "status": "NOTRUN_NO_CAL_NEGATIVES",
            "alpha": CAL_ALPHA,
            "negative_pairs": negatives,
            "threshold": None,
            "claim_grade_minimum_met": False,
        }
    threshold = identity.calibrated_threshold(scores, labels, CAL_ALPHA)
    false_accepts = sum(1 for score, label in zip(scores, labels) if not label and score >= threshold)
    return {
        "status": "NUMERIC_ANNOTATION_LEVEL",
        "alpha": CAL_ALPHA,
        "negative_pairs": negatives,
        "pair_count": len(scores),
        "threshold": threshold,
        "false_accepts": false_accepts,
        "false_accept_rate": false_accepts / float(negatives),
        "claim_grade_minimum_met": negatives >= CAL_MIN_NEGATIVES,
        "minimum_negative_pairs": CAL_MIN_NEGATIVES,
        "selection": "maximum CAL true accepts subject to fixed false-accept rate",
    }


def evaluate_method(
    method: str,
    vectors: Mapping[str, object],
    cal_rows: Mapping[str, Sequence[Mapping[str, str]]],
    eval_rows: Mapping[str, Sequence[Mapping[str, str]]],
    families: Sequence[str],
    k: int,
) -> Tuple[dict, List[dict]]:
    calibration = calibrate_method(method, vectors, cal_rows, families, k)
    threshold = calibration.get("threshold")
    rows = []
    for family in families:
        for query in eval_rows.get(family, []):
            scores = family_scores(query, vectors, method, k)
            top_family, top_score = max(scores.items(), key=lambda item: (item[1], item[0]))
            accepted = bool(threshold is not None and math.isfinite(float(threshold)) and top_score >= float(threshold))
            rows.append({
                "method": method,
                "record_id": query["record_id"],
                "host_id": query["host_id"],
                "host_locus": query.get("host_locus", ""),
                "source_copy_id": query["source_copy_id"],
                "homology_component_id": query["homology_component_id"],
                "true_family": family,
                "top_family": top_family,
                "top_score": round(top_score, 10),
                "threshold": threshold,
                "accepted": int(accepted),
                "correct": int(top_family == family),
            })
    queries = len(rows)
    correct = sum(row["correct"] for row in rows)
    accepted = [row for row in rows if row["accepted"]]
    accepted_correct = sum(row["correct"] for row in accepted)
    family_tp = Counter(row["true_family"] for row in rows if row["correct"])
    family_pred = Counter(row["top_family"] for row in rows)
    family_truth = Counter(row["true_family"] for row in rows)
    recalls = []
    precisions = []
    f1s = []
    for family in families:
        tp = family_tp[family]
        recall = tp / float(family_truth[family]) if family_truth[family] else 0.0
        precision = tp / float(family_pred[family]) if family_pred[family] else 0.0
        f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
        recalls.append(recall)
        precisions.append(precision)
        f1s.append(f1)
    metrics = {
        "status": "NUMERIC_ANNOTATION_LEVEL",
        "method": method,
        "families": len(families),
        "queries": queries,
        "top1_accuracy": correct / float(queries) if queries else None,
        "family_macro_recall": sum(recalls) / len(recalls) if recalls else None,
        "family_macro_precision": sum(precisions) / len(precisions) if precisions else None,
        "family_macro_f1": sum(f1s) / len(f1s) if f1s else None,
        "accepted_queries": len(accepted),
        "accepted_accuracy": accepted_correct / float(len(accepted)) if accepted else None,
        "accepted_wrong_queries": len(accepted) - accepted_correct,
        "calibration": calibration,
        "identity_level": "coordinate_derived_annotated_interval",
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY",
    }
    return metrics, rows


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_queries(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    fields = [
        "method", "record_id", "host_id", "host_locus", "source_copy_id", "homology_component_id",
        "true_family", "top_family", "top_score", "threshold", "accepted", "correct",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(input_manifest: Path, out_dir: Path, k: int = KMER_SIZE) -> dict:
    raw = identity.load_rows(input_manifest)
    normalized = [identity.normalize_row(row, index) for index, row in enumerate(raw)]
    audit = identity.audit_manifest(normalized)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "input_audit.json", audit)
    if audit["status"] != "PASS_AUDIT":
        status = {
            "status": "NOTRUN_IDENTITY_AUDIT",
            "reason": audit["status"],
            "scientific_claim_status": "NOTRUN",
        }
        write_json(out_dir / "status.json", status)
        return status
    method_specs, indexes = select_methods(normalized, k=k)
    matched = indexes["index"]["matched_families"]
    if not matched:
        status = {
            "status": "NOTRUN_NO_MATCHED_FAMILIES",
            "reason": "no family has consensus, >=4 TRAIN natural copies, CAL/EVAL rows, and sequence content",
            "scientific_claim_status": "NOTRUN",
            "family_inventory": indexes["index"],
        }
        write_json(out_dir / "status.json", status)
        write_json(out_dir / "metrics.json", {"status": "NOTRUN", "methods": {}})
        return status
    all_metrics = {}
    all_queries = []
    for method, prototype_rows in sorted(method_specs.items()):
        vectors = prototype_vectors(method, prototype_rows, k)
        metrics, queries = evaluate_method(method, vectors, indexes["cal"], indexes["eval"], matched, k)
        prototype_ids = {
            family: [row["record_id"] for row in prototype_rows[family]]
            for family in matched
        }
        metrics["prototype_record_ids"] = prototype_ids
        all_metrics[method] = metrics
        all_queries.extend(queries)
    write_queries(out_dir / "per_query.tsv", all_queries)
    summary = {
        "status": "NUMERIC_ANNOTATION_LEVEL",
        "contract_version": "te-identity-retrieval-sequence-v1",
        "seed": SEED,
        "kmer_size": k,
        "family_inventory": indexes["index"],
        "methods": all_metrics,
        "not_run_methods": {
            "glm_embedding": "no explicit frozen GLM embedding table was supplied",
            "training_copy_profile_hmm": "no explicit training-copy profile HMM was supplied",
        },
        "identity_level": "coordinate_derived_annotated_interval",
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY",
    }
    write_json(out_dir / "metrics.json", summary)
    status = {
        "status": "PASS_NUMERIC_ANNOTATION_LEVEL",
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY",
        "families": len(matched),
        "methods_scored": sorted(all_metrics),
        "scores_written": True,
        "real_glm_embedding": False,
        "biological_insertion_truth": False,
    }
    write_json(out_dir / "status.json", status)
    return status


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--kmer-size", type=int, default=KMER_SIZE)
    args = parser.parse_args(argv)
    run(args.input_manifest, args.out_dir, k=args.kmer_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
