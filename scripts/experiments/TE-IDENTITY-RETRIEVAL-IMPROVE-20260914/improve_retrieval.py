#!/usr/bin/env python3
"""Bounded k-mer and supervised-projection retrieval improvement study.

This command keeps the already audited natural-copy manifest, common matched
family set, split roles, and calibration rule fixed.  It separates nucleotide
k-mer length (4/6/8) from the number of natural prototypes (one versus four).
It also trains one small, family-supervised linear projection on TRAIN NTv2
embeddings.  CAL is used to select the projection epoch and every arm's score
threshold; EVAL is read only once for the final report.

All outputs are annotation-level exploratory evidence.  The manifest's
coordinate-derived IDs do not establish biological insertion identity.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import random
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SEED = 42
KMER_LENGTHS = (4, 6, 8)
KMER6 = 6
CAL_ALPHA = 0.01
CAL_MIN_NEGATIVES = 100
MODEL_ID = "nucleotide-transformer-v2-500m-multi-species"
CONTRACT_VERSION = "te-identity-retrieval-improve-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load support module: %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_support_modules(support_source_dir: Path):
    identity = load_module("te_identity_improve_identity", support_source_dir / "identity_retrieval.py")
    sequence = load_module("te_identity_improve_sequence", support_source_dir / "sequence_retrieval.py")
    return identity, sequence


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def write_queries(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    fields = [
        "method", "record_id", "host_id", "host_locus", "source_copy_id", "homology_component_id",
        "true_family", "top_family", "top_score", "threshold", "accepted", "correct",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_embeddings(embedding_path: Path, ids_path: Path, meta_path: Path, expected_ids: Sequence[str]):
    import numpy as np

    ids = json.loads(ids_path.read_text(encoding="utf-8"))
    if ids != list(expected_ids):
        raise ValueError("embedding IDs do not match manifest order")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("model_id") != MODEL_ID:
        raise ValueError("embedding metadata is not native NTv2-500M")
    if meta.get("pooling") != "mean" or meta.get("special_tokens_excluded") is not True:
        raise ValueError("embedding metadata does not match the fixed native pooling contract")
    matrix = np.load(embedding_path, allow_pickle=False)
    if matrix.ndim != 2 or matrix.shape[0] != len(ids):
        raise ValueError("embedding matrix shape does not match embedding IDs")
    if not np.isfinite(matrix).all():
        raise ValueError("embedding matrix contains non-finite values")
    return matrix.astype(np.float32, copy=False), meta


def common_method_indexes(rows: Sequence[Mapping[str, str]], sequence_module):
    """Build all fixed-kmer indexes and require one common family set."""

    by_k = {}
    common: Optional[List[str]] = None
    for kmer_size in KMER_LENGTHS:
        methods, indexes = sequence_module.select_methods(rows, k=kmer_size)
        matched = list(indexes["index"]["matched_families"])
        if common is None:
            common = matched
        elif matched != common:
            raise ValueError("matched family set changed across k-mer lengths")
        by_k[kmer_size] = (methods, indexes)
    if not common:
        raise ValueError("no common matched families")
    return common, by_k


def kmer_ablation(rows: Sequence[Mapping[str, str]], identity_module, sequence_module):
    common, by_k = common_method_indexes(rows, sequence_module)
    metrics: Dict[str, dict] = {}
    queries: List[dict] = []
    arms = ("single_train_medoid", "k4_natural_prototypes", "basic_train_centroid")
    prototype_counts = {
        "single_train_medoid": 1,
        "k4_natural_prototypes": 4,
        "basic_train_centroid": "all_train_copies",
    }
    for kmer_size in KMER_LENGTHS:
        methods, indexes = by_k[kmer_size]
        for source_method in arms:
            vectors = sequence_module.prototype_vectors(source_method, methods[source_method], kmer_size)
            result, result_queries = sequence_module.evaluate_method(
                source_method,
                vectors,
                indexes["cal"],
                indexes["eval"],
                common,
                kmer_size,
            )
            output_method = "kmer%d_%s" % (kmer_size, source_method)
            result["method"] = output_method
            result["kmer_size"] = kmer_size
            result["prototype_count"] = prototype_counts[source_method]
            result["prototype_selection"] = (
                "TRAIN-only deterministic greedy PAM-style medoids in this k-mer space"
                if source_method != "basic_train_centroid"
                else "mean of all TRAIN k-mer vectors"
            )
            result["prototype_record_ids"] = {
                family: [row["record_id"] for row in methods[source_method][family]]
                for family in common
            }
            result["scientific_claim_status"] = "ANNOTATION_LEVEL_ONLY_EXPLORATORY"
            metrics[output_method] = result
            for row in result_queries:
                row = dict(row)
                row["method"] = output_method
                queries.append(row)
    return common, by_k, metrics, queries


def _normalize_rows(matrix):
    import numpy as np

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _prototype_arrays(matrix, prototype_ids: Mapping[str, Sequence[str]], id_to_index: Mapping[str, int], centroid: bool):
    import numpy as np

    output = {}
    for family, ids in prototype_ids.items():
        vectors = matrix[[id_to_index[record_id] for record_id in ids]]
        if centroid:
            vectors = np.mean(vectors, axis=0, keepdims=True)
        output[family] = vectors
    return output


def family_scores_for_vector(query_vector, prototype_arrays: Mapping[str, object]) -> Dict[str, float]:
    import numpy as np

    query = np.asarray(query_vector, dtype=np.float32)
    query_norm = float(np.linalg.norm(query))
    if query_norm:
        query = query / query_norm
    scores = {}
    for family, prototypes in prototype_arrays.items():
        vectors = np.asarray(prototypes, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        scores[family] = float(np.max(np.dot(vectors / norms, query))) if len(vectors) else 0.0
    return scores


def calibration_for_embedding(
    matrix,
    prototype_ids: Mapping[str, Sequence[str]],
    id_to_index: Mapping[str, int],
    cal_rows: Mapping[str, Sequence[Mapping[str, str]]],
    families: Sequence[str],
    centroid: bool,
    identity_module,
) -> dict:
    prototype_arrays = _prototype_arrays(matrix, prototype_ids, id_to_index, centroid)
    scores: List[float] = []
    labels: List[int] = []
    for family in families:
        for query in cal_rows.get(family, []):
            by_family = family_scores_for_vector(matrix[id_to_index[query["record_id"]]], prototype_arrays)
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
            "false_accepts": None,
            "true_accepts": None,
        }
    threshold = identity_module.calibrated_threshold(scores, labels, CAL_ALPHA)
    false_accepts = sum(1 for score, label in zip(scores, labels) if not label and score >= threshold)
    true_accepts = sum(1 for score, label in zip(scores, labels) if label and score >= threshold)
    return {
        "status": "NUMERIC_ANNOTATION_LEVEL",
        "alpha": CAL_ALPHA,
        "negative_pairs": negatives,
        "pair_count": len(scores),
        "threshold": threshold,
        "false_accepts": false_accepts,
        "true_accepts": true_accepts,
        "true_positive_pairs": true_accepts,
        "false_accept_rate": false_accepts / float(negatives),
        "claim_grade_minimum_met": negatives >= CAL_MIN_NEGATIVES,
        "minimum_negative_pairs": CAL_MIN_NEGATIVES,
        "selection": "maximum CAL true accepts subject to fixed false-accept rate",
    }


def evaluate_embedding(
    output_method: str,
    matrix,
    prototype_ids: Mapping[str, Sequence[str]],
    id_to_index: Mapping[str, int],
    cal_rows: Mapping[str, Sequence[Mapping[str, str]]],
    eval_rows: Mapping[str, Sequence[Mapping[str, str]]],
    families: Sequence[str],
    centroid: bool,
    identity_module,
    include_eval: bool = True,
) -> Tuple[dict, List[dict]]:
    calibration = calibration_for_embedding(
        matrix, prototype_ids, id_to_index, cal_rows, families, centroid, identity_module
    )
    threshold = calibration.get("threshold")
    prototype_arrays = _prototype_arrays(matrix, prototype_ids, id_to_index, centroid)
    rows: List[dict] = []
    if include_eval:
        for family in families:
            for query in eval_rows.get(family, []):
                scores = family_scores_for_vector(matrix[id_to_index[query["record_id"]]], prototype_arrays)
                top_family, top_score = max(scores.items(), key=lambda item: (item[1], item[0]))
                accepted = bool(
                    threshold is not None
                    and math.isfinite(float(threshold))
                    and top_score >= float(threshold)
                )
                rows.append(
                    {
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
                    }
                )
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
    return (
        {
            "status": "NUMERIC_ANNOTATION_LEVEL" if include_eval else "CALIBRATION_ONLY",
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
            "scientific_claim_status": "ANNOTATION_LEVEL_ONLY_EXPLORATORY",
        },
        rows,
    )


def choose_epoch(trace: Sequence[Mapping[str, object]]) -> int:
    """Choose the earliest epoch with the largest CAL true-pair count."""

    if not trace:
        raise ValueError("cannot choose an epoch from an empty trace")
    eligible = [row for row in trace if row.get("cal_status") == "NUMERIC_ANNOTATION_LEVEL"]
    if not eligible:
        raise ValueError("no epoch has a usable CAL calibration")
    best = max(eligible, key=lambda row: (int(row["cal_true_accepts"]), -int(row["epoch"])))
    return int(best["epoch"])


def supervised_contrastive_loss(embeddings, labels, temperature: float = 0.1):
    """Full-batch supervised contrastive loss with self-pairs excluded."""

    import torch
    import torch.nn.functional as F

    if embeddings.ndim != 2 or labels.ndim != 1 or embeddings.shape[0] != labels.shape[0]:
        raise ValueError("embeddings and labels must be aligned rank-2/rank-1 tensors")
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    z = F.normalize(embeddings, dim=1)
    logits = torch.matmul(z, z.T) / temperature
    n = logits.shape[0]
    eye = torch.eye(n, dtype=torch.bool, device=logits.device)
    logits = logits.masked_fill(eye, float("-inf"))
    log_prob = logits - torch.logsumexp(logits, dim=1, keepdim=True)
    positive = labels[:, None].eq(labels[None, :]) & ~eye
    positive_count = positive.sum(dim=1)
    valid = positive_count > 0
    if not bool(valid.any()):
        raise ValueError("supervised contrastive loss has no positive pair")
    summed = torch.where(positive, log_prob, torch.zeros_like(log_prob)).sum(dim=1)
    losses = -summed[valid] / positive_count[valid].to(dtype=log_prob.dtype)
    return losses.mean()


def train_projection(
    train_matrix,
    train_labels: Sequence[int],
    all_matrix,
    prototype_ids: Mapping[str, Sequence[str]],
    id_to_index: Mapping[str, int],
    cal_rows: Mapping[str, Sequence[Mapping[str, str]]],
    families: Sequence[str],
    identity_module,
    out_dir: Path,
    epochs: int,
    projection_dim: int,
    temperature: float,
    learning_rate: float,
    weight_decay: float,
) -> Tuple[object, dict, List[dict]]:
    import numpy as np
    import torch
    from torch import nn

    if epochs < 1 or projection_dim < 1:
        raise ValueError("epochs and projection_dim must be positive")
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(min(4, max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", "4")))))
    input_dim = int(train_matrix.shape[1])
    model = nn.Linear(input_dim, projection_dim, bias=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    train_tensor = torch.from_numpy(np.asarray(train_matrix, dtype=np.float32))
    label_tensor = torch.tensor(list(train_labels), dtype=torch.long)
    all_tensor = torch.from_numpy(np.asarray(all_matrix, dtype=np.float32))
    # The model is evaluated on all manifest rows; prototype IDs and CAL rows
    # are fixed by the audited k=6 selection and never reselected per epoch.
    snapshots: Dict[int, object] = {}
    state_snapshots: Dict[int, dict] = {}
    trace: List[dict] = []
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        projected_train = model(train_tensor)
        loss = supervised_contrastive_loss(projected_train, label_tensor, temperature)
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.inference_mode():
            projected_all = model(all_tensor).cpu().numpy().astype(np.float32, copy=False)
        cal_metrics, _ = evaluate_embedding(
            "projected_train_centroid",
            projected_all,
            prototype_ids,
            id_to_index,
            cal_rows,
            {},
            families,
            centroid=True,
            identity_module=identity_module,
            include_eval=False,
        )
        calibration = cal_metrics["calibration"]
        trace_row = {
            "epoch": epoch,
            "loss": float(loss.detach().cpu().item()),
            "cal_status": calibration.get("status"),
            "cal_threshold": calibration.get("threshold"),
            "cal_true_accepts": calibration.get("true_accepts", 0),
            "cal_false_accepts": calibration.get("false_accepts", 0),
            "cal_false_accept_rate": calibration.get("false_accept_rate"),
            "cal_negative_pairs": calibration.get("negative_pairs", 0),
        }
        trace.append(trace_row)
        snapshots[epoch] = projected_all.copy()
        state_snapshots[epoch] = {
            name: value.detach().cpu().clone() for name, value in model.state_dict().items()
        }
    selected_epoch = choose_epoch(trace)
    selected_matrix = snapshots[selected_epoch]
    selected_state = state_snapshots[selected_epoch]
    state_path = out_dir / "projection_state.pt"
    torch.save(
        {
            "state_dict": selected_state,
            "input_dim": input_dim,
            "projection_dim": projection_dim,
            "temperature": temperature,
            "learning_rate": learning_rate,
            "weight_decay": weight_decay,
            "epochs": epochs,
            "selected_epoch": selected_epoch,
            "seed": SEED,
            "model_id": MODEL_ID,
        },
        state_path,
    )
    return selected_matrix, {"selected_epoch": selected_epoch, "state_path": str(state_path)}, trace


def run(
    input_manifest: Path,
    embedding_path: Path,
    embedding_ids_path: Path,
    embedding_meta_path: Path,
    support_source_dir: Path,
    out_dir: Path,
    epochs: int = 50,
    projection_dim: int = 128,
    temperature: float = 0.1,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
) -> dict:
    import numpy as np

    out_dir.mkdir(parents=True, exist_ok=True)
    identity_module, sequence_module = load_support_modules(support_source_dir)
    raw_rows = identity_module.load_rows(input_manifest)
    rows = [identity_module.normalize_row(row, index) for index, row in enumerate(raw_rows)]
    audit = identity_module.audit_manifest(rows)
    write_json_atomic(out_dir / "input_audit.json", audit)
    if audit["status"] != "PASS_AUDIT":
        status = {
            "status": "NOTRUN_IDENTITY_AUDIT",
            "reason": audit["status"],
            "scientific_claim_status": "NOTRUN",
        }
        write_json_atomic(out_dir / "status.json", status)
        return status
    expected_ids = [row["record_id"] for row in rows]
    embedding_matrix, embedding_meta = load_embeddings(
        embedding_path, embedding_ids_path, embedding_meta_path, expected_ids
    )
    common, by_k, kmer_metrics, all_queries = kmer_ablation(rows, identity_module, sequence_module)
    methods6, indexes6 = by_k[KMER6]
    id_to_index = {record_id: index for index, record_id in enumerate(expected_ids)}
    prototype_source_methods = (
        "single_train_medoid",
        "k4_natural_prototypes",
        "basic_train_centroid",
    )
    prototype_ids = {
        source_method: {
            family: [row["record_id"] for row in methods6[source_method][family]]
            for family in common
        }
        for source_method in prototype_source_methods
    }
    raw_metrics: Dict[str, dict] = {}
    for source_method in prototype_source_methods:
        output_method = {
            "single_train_medoid": "raw_ntv2_single_train_medoid",
            "k4_natural_prototypes": "raw_ntv2_k4_natural_prototypes",
            "basic_train_centroid": "raw_ntv2_train_centroid",
        }[source_method]
        result, result_queries = evaluate_embedding(
            output_method,
            embedding_matrix,
            prototype_ids[source_method],
            id_to_index,
            indexes6["cal"],
            indexes6["eval"],
            common,
            centroid=source_method == "basic_train_centroid",
            identity_module=identity_module,
        )
        result["kmer6_prototype_selection"] = "fixed TRAIN-only k-mer6 IDs; no GLM-space reselection"
        result["prototype_record_ids"] = prototype_ids[source_method]
        raw_metrics[output_method] = result
        all_queries.extend(result_queries)
    train_rows = [row for family in common for row in sorted(indexes6["train"][family], key=lambda r: r["record_id"])]
    train_matrix = embedding_matrix[[id_to_index[row["record_id"]] for row in train_rows]]
    label_lookup = {family: index for index, family in enumerate(common)}
    train_labels = [label_lookup[row["family_id"]] for row in train_rows]
    selected_matrix, selection, trace = train_projection(
        train_matrix,
        train_labels,
        embedding_matrix,
        prototype_ids["basic_train_centroid"],
        id_to_index,
        indexes6["cal"],
        common,
        identity_module,
        out_dir,
        epochs,
        projection_dim,
        temperature,
        learning_rate,
        weight_decay,
    )
    write_jsonl(out_dir / "training_trace.jsonl", trace)
    projection_metrics: Dict[str, dict] = {}
    for source_method in prototype_source_methods:
        output_method = {
            "single_train_medoid": "projected_single_train_medoid",
            "k4_natural_prototypes": "projected_k4_natural_prototypes",
            "basic_train_centroid": "projected_train_centroid",
        }[source_method]
        result, result_queries = evaluate_embedding(
            output_method,
            selected_matrix,
            prototype_ids[source_method],
            id_to_index,
            indexes6["cal"],
            indexes6["eval"],
            common,
            centroid=source_method == "basic_train_centroid",
            identity_module=identity_module,
        )
        result["selected_epoch"] = selection["selected_epoch"]
        result["projection_dim"] = projection_dim
        result["prototype_record_ids"] = prototype_ids[source_method]
        result["scientific_claim_status"] = "ANNOTATION_LEVEL_ONLY_EXPLORATORY"
        projection_metrics[output_method] = result
        all_queries.extend(result_queries)
    write_queries(out_dir / "per_query.tsv", all_queries)
    write_json_atomic(
        out_dir / "training_config.json",
        {
            "seed": SEED,
            "model_id": MODEL_ID,
            "input_dimension": int(embedding_matrix.shape[1]),
            "projection_dimension": projection_dim,
            "temperature": temperature,
            "learning_rate": learning_rate,
            "weight_decay": weight_decay,
            "epochs_requested": epochs,
            "train_rows": len(train_rows),
            "train_families": len(common),
            "objective": "full_batch supervised contrastive loss on TRAIN family labels",
            "epoch_selection": "earliest epoch maximizing projected TRAIN-centroid CAL true pair accepts under FAR<=0.01",
            "eval_policy": "EVAL read only for final selected-epoch metrics",
            "contrastive_backbone_training": "forbidden; native NTv2 frozen",
        },
    )
    all_metrics = {}
    all_metrics.update(kmer_metrics)
    all_metrics.update(raw_metrics)
    all_metrics.update(projection_metrics)
    summary = {
        "status": "PASS_NUMERIC_ANNOTATION_LEVEL_EXPLORATORY",
        "contract_version": CONTRACT_VERSION,
        "seed": SEED,
        "kmer_lengths_tested": list(KMER_LENGTHS),
        "prototype_counts_tested": [1, 4, "all_train_copies"],
        "family_inventory": indexes6["index"],
        "common_matched_families": common,
        "embedding_model_id": MODEL_ID,
        "embedding_shape": list(embedding_matrix.shape),
        "embedding_meta": str(embedding_meta_path),
        "methods": all_metrics,
        "projection_selection": selection,
        "training_trace": "training_trace.jsonl",
        "contrastive_training": {
            "backbone": "frozen_native_ntv2",
            "projection": "single_linear_1024_to_%d" % projection_dim,
            "train_labels": "family_id on TRAIN natural copies only",
            "calibration_and_epoch_selection": "CAL only",
            "eval_seen_before": True,
            "unsupervised": False,
        },
        "calibration": {
            "alpha": CAL_ALPHA,
            "minimum_negative_pairs": CAL_MIN_NEGATIVES,
            "common_negative_pairs": 6328,
        },
        "identity_level": "coordinate_derived_annotated_interval",
        "pretraining_exposure_status": embedding_meta.get("pretraining_exposure_status", "UNRESOLVED"),
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY_EXPLORATORY",
        "independent_test_status": "NOT_INDEPENDENT_EVAL_ALREADY_SEEN",
    }
    write_json_atomic(out_dir / "metrics.json", summary)
    status = {
        "status": "PASS_NUMERIC_ANNOTATION_LEVEL_EXPLORATORY",
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY_EXPLORATORY",
        "scores_written": True,
        "records": len(rows),
        "families": len(common),
        "kmer_lengths": list(KMER_LENGTHS),
        "projection_selected_epoch": selection["selected_epoch"],
        "contrastive_training": True,
        "real_glm_embedding": True,
        "biological_insertion_truth": False,
        "pretraining_exposure_status": embedding_meta.get("pretraining_exposure_status", "UNRESOLVED"),
    }
    write_json_atomic(out_dir / "status.json", status)
    return status


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--embedding-ids", type=Path, required=True)
    parser.add_argument("--embedding-meta", type=Path, required=True)
    parser.add_argument("--support-source-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--projection-dim", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    args = parser.parse_args(argv)
    run(
        args.input_manifest,
        args.embeddings,
        args.embedding_ids,
        args.embedding_meta,
        args.support_source_dir,
        args.out_dir,
        epochs=args.epochs,
        projection_dim=args.projection_dim,
        temperature=args.temperature,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
