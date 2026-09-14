#!/usr/bin/env python3
"""Score native NTv2 embeddings with the fixed identity-retrieval contract.

The prototype record IDs are inherited from ``sequence_retrieval.py`` so that
this exploratory GLM arm changes the representation while keeping the natural
copy panel, family set, prototype selection, CAL budget, and EVAL queries
fixed.  Prototype selection is therefore still the established deterministic
k-mer selection rule; this command does not select prototypes in GLM space.

The output is annotation-level family retrieval only.  It does not claim
biological insertion recovery, cross-species independence, or pretraining
independence.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


identity = load_module("te_identity_retrieval_for_glm_scoring", HERE / "identity_retrieval.py")
sequence_retrieval = load_module("te_sequence_retrieval_for_glm_scoring", HERE / "sequence_retrieval.py")


MODEL_ID = "nucleotide-transformer-v2-500m-multi-species"
CONTRACT_VERSION = "te-identity-retrieval-glm-scoring-v1"
SEED = 42
CAL_ALPHA = 0.01
CAL_MIN_NEGATIVES = 100


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _as_float_vector(value: Iterable[object]) -> List[float]:
    vector = [float(item) for item in value]
    if not vector or any(not math.isfinite(item) for item in vector):
        raise ValueError("embedding vectors must be finite and non-empty")
    return vector


def load_embedding_table(embedding_path: Path, ids_path: Path) -> Tuple[List[str], object, dict]:
    """Load production .npy embeddings or a JSONL fixture without fallback."""

    ids = json.loads(ids_path.read_text(encoding="utf-8"))
    if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
        raise ValueError("embedding_ids.json must contain a list of record IDs")
    if embedding_path.suffix == ".npy":
        try:
            import numpy as np
        except Exception as exc:
            raise RuntimeError("numpy is required to read native .npy embeddings") from exc
        matrix = np.load(embedding_path, allow_pickle=False)
        if matrix.ndim != 2 or matrix.shape[0] != len(ids):
            raise ValueError("embedding matrix shape does not match embedding IDs")
        if not np.isfinite(matrix).all():
            raise ValueError("embedding matrix contains non-finite values")
        return ids, matrix, {"format": "npy", "dimension": int(matrix.shape[1]), "dtype": str(matrix.dtype)}
    if embedding_path.suffix in {".jsonl", ".json"}:
        rows = [json.loads(line) for line in embedding_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        vectors = []
        observed_ids = []
        for row in rows:
            observed_ids.append(str(row["record_id"]))
            vectors.append(_as_float_vector(row["embedding"]))
        if observed_ids != ids:
            raise ValueError("JSONL embedding IDs do not match embedding_ids.json")
        dimension = len(vectors[0]) if vectors else 0
        if not dimension or any(len(vector) != dimension for vector in vectors):
            raise ValueError("JSONL embedding dimensions are inconsistent")
        return ids, vectors, {"format": "jsonl", "dimension": dimension, "dtype": "float64_fixture"}
    raise ValueError("unsupported embedding format: %s" % embedding_path)


def vector_at(matrix: object, index: int):
    return matrix[index]


def cosine(left: object, right: object) -> float:
    try:
        import numpy as np
        if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
            numerator = float(np.dot(left, right))
            denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
            return numerator / denominator if denominator else 0.0
    except Exception:
        pass
    numerator = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(a) * float(a) for a in left))
    right_norm = math.sqrt(sum(float(b) * float(b) for b in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def mean_vectors(vectors: Sequence[object]) -> object:
    if not vectors:
        raise ValueError("cannot average an empty prototype set")
    try:
        import numpy as np
        if isinstance(vectors[0], np.ndarray):
            return np.mean(np.stack(vectors, axis=0), axis=0)
    except Exception:
        pass
    dimension = len(vectors[0])
    return [sum(float(vector[index]) for vector in vectors) / len(vectors) for index in range(dimension)]


def family_scores(query_vector: object, prototype_vectors: Mapping[str, Sequence[object]], centroid_method: bool = False) -> Dict[str, float]:
    scores = {}
    for family, prototypes in prototype_vectors.items():
        if centroid_method:
            scores[family] = cosine(query_vector, prototypes[0])
        else:
            scores[family] = max((cosine(query_vector, prototype) for prototype in prototypes), default=0.0)
    return scores


def calibrate_method(
    prototype_vectors: Mapping[str, Sequence[object]],
    cal_rows: Mapping[str, Sequence[Mapping[str, str]]],
    row_vectors: Mapping[str, object],
    families: Sequence[str],
    centroid_method: bool,
) -> dict:
    scores, labels = [], []
    for family in families:
        for query in cal_rows.get(family, []):
            by_family = family_scores(row_vectors[query["record_id"]], prototype_vectors, centroid_method)
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
    output_method: str,
    prototype_vectors: Mapping[str, Sequence[object]],
    cal_rows: Mapping[str, Sequence[Mapping[str, str]]],
    eval_rows: Mapping[str, Sequence[Mapping[str, str]]],
    row_vectors: Mapping[str, object],
    families: Sequence[str],
    centroid_method: bool,
) -> Tuple[dict, List[dict]]:
    calibration = calibrate_method(prototype_vectors, cal_rows, row_vectors, families, centroid_method)
    threshold = calibration.get("threshold")
    rows = []
    for family in families:
        for query in eval_rows.get(family, []):
            scores = family_scores(row_vectors[query["record_id"]], prototype_vectors, centroid_method)
            top_family, top_score = max(scores.items(), key=lambda item: (item[1], item[0]))
            accepted = bool(threshold is not None and math.isfinite(float(threshold)) and top_score >= float(threshold))
            rows.append({
                "method": output_method,
                "record_id": query["record_id"],
                "host_id": query["host_id"],
                "host_locus": query.get("host_locus", ""),
                "source_copy_id": query["source_copy_id"],
                "homology_component_id": query["homology_component_id"],
                "true_family": family,
                "top_family": top_family,
                "top_score": round(float(top_score), 10),
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
    recalls, precisions, f1s = [], [], []
    for family in families:
        tp = family_tp[family]
        recall = tp / float(family_truth[family]) if family_truth[family] else 0.0
        precision = tp / float(family_pred[family]) if family_pred[family] else 0.0
        f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
        recalls.append(recall)
        precisions.append(precision)
        f1s.append(f1)
    return {
        "status": "NUMERIC_ANNOTATION_LEVEL",
        "method": output_method,
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
    }, rows


def write_queries(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    fields = [
        "method", "record_id", "host_id", "host_locus", "source_copy_id", "homology_component_id",
        "true_family", "top_family", "top_score", "threshold", "accepted", "correct",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(
    input_manifest: Path,
    embedding_path: Path,
    embedding_ids_path: Path,
    embedding_meta_path: Path,
    out_dir: Path,
) -> dict:
    raw = identity.load_rows(input_manifest)
    normalized = [identity.normalize_row(row, index) for index, row in enumerate(raw)]
    audit = identity.audit_manifest(normalized)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "input_audit.json", audit)
    if audit["status"] != "PASS_AUDIT":
        status = {"status": "NOTRUN_IDENTITY_AUDIT", "reason": audit["status"], "scientific_claim_status": "NOTRUN"}
        write_json(out_dir / "status.json", status)
        return status
    metadata = json.loads(embedding_meta_path.read_text(encoding="utf-8"))
    if metadata.get("model_id") != MODEL_ID:
        raise ValueError("embedding metadata is not native NTv2-500M")
    if metadata.get("pooling") != "mean" or metadata.get("special_tokens_excluded") is not True:
        raise ValueError("embedding metadata does not match the fixed GLM pooling contract")
    ids, matrix, matrix_info = load_embedding_table(embedding_path, embedding_ids_path)
    expected_ids = [row["record_id"] for row in normalized]
    if ids != expected_ids:
        raise ValueError("embedding record IDs do not match manifest order")
    row_vectors = {record_id: vector_at(matrix, index) for index, record_id in enumerate(ids)}
    method_specs, indexes = sequence_retrieval.select_methods(normalized, k=6)
    matched = indexes["index"]["matched_families"]
    if not matched:
        status = {"status": "NOTRUN_NO_MATCHED_FAMILIES", "scientific_claim_status": "NOTRUN"}
        write_json(out_dir / "status.json", status)
        return status
    glm_methods = {
        "single_consensus": "glm_single_consensus",
        "single_train_medoid": "glm_single_train_medoid",
        "k4_natural_prototypes": "glm_k4_natural_prototypes",
        "random4_natural_prototypes": "glm_random4_natural_prototypes",
        "basic_train_centroid": "glm_train_centroid",
    }
    all_metrics = {}
    all_queries = []
    cal_rows = indexes["cal"]
    eval_rows = indexes["eval"]
    for source_method, output_method in glm_methods.items():
        if source_method not in method_specs:
            continue
        prototype_vectors = {}
        prototype_ids = {}
        for family in matched:
            records = method_specs[source_method][family]
            prototype_ids[family] = [row["record_id"] for row in records]
            if source_method == "basic_train_centroid":
                prototype_vectors[family] = [mean_vectors([row_vectors[row["record_id"]] for row in records])]
            else:
                prototype_vectors[family] = [row_vectors[row["record_id"]] for row in records]
        metrics, queries = evaluate_method(
            output_method,
            prototype_vectors,
            cal_rows,
            eval_rows,
            row_vectors,
            matched,
            centroid_method=source_method == "basic_train_centroid",
        )
        metrics["prototype_record_ids"] = prototype_ids
        metrics["prototype_selection_source"] = "fixed sequence_retrieval.py k-mer-space IDs"
        all_metrics[output_method] = metrics
        all_queries.extend(queries)
    write_queries(out_dir / "per_query.tsv", all_queries)
    summary = {
        "status": "NUMERIC_ANNOTATION_LEVEL",
        "contract_version": CONTRACT_VERSION,
        "seed": SEED,
        "embedding_model_id": MODEL_ID,
        "embedding_meta": str(embedding_meta_path),
        "embedding_info": matrix_info,
        "family_inventory": indexes["index"],
        "methods": all_metrics,
        "prototype_selection": "reuse exact record IDs selected by fixed sequence_retrieval.py; no GLM-space reselection",
        "calibration": {"alpha": CAL_ALPHA, "minimum_negative_pairs": CAL_MIN_NEGATIVES},
        "contrastive_training": "NOTRUN",
        "pretraining_exposure_status": metadata.get("pretraining_exposure_status", "UNRESOLVED"),
        "identity_level": "coordinate_derived_annotated_interval",
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY",
        "exploratory_arm": True,
        "pre_registration_status": "NOT_PREREGISTERED_EXPLORATORY_ARM",
    }
    write_json(out_dir / "metrics.json", summary)
    status = {
        "status": "PASS_NUMERIC_ANNOTATION_LEVEL",
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY",
        "exploratory_arm": True,
        "model_id": MODEL_ID,
        "families": len(matched),
        "methods_scored": sorted(all_metrics),
        "scores_written": True,
        "real_glm_embedding": True,
        "contrastive_training": False,
        "pretraining_exposure_status": metadata.get("pretraining_exposure_status", "UNRESOLVED"),
        "biological_insertion_truth": False,
    }
    write_json(out_dir / "status.json", status)
    return status


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--embedding-ids", type=Path, required=True)
    parser.add_argument("--embedding-meta", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args.input_manifest, args.embeddings, args.embedding_ids, args.embedding_meta, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
