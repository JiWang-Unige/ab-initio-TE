#!/usr/bin/env python3
"""Extract frozen native NTv2-500M sequence embeddings for the identity panel.

This command is deliberately an inference-only arm.  It accepts the audited
identity manifest produced by ``build_natural_panel.py``, loads only the native
``nucleotide-transformer-v2-500m-multi-species`` directory, and writes one
mean-pooled embedding per manifest record.  Special tokens are excluded from
the mean.  If a sequence exceeds the native token budget it is split at token
boundaries and the segment means are combined with weights equal to the number
of non-special content tokens in each segment.

The current hg38 panel is shorter than the 2048-token native limit, but the
segmentation rule is fixed here so a later panel cannot silently truncate a
sequence.  No contrastive projection, fine-tuning, checkpoint selection, or
gap operation is performed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import random
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple


HERE = Path(__file__).resolve().parent
IDENTITY_SPEC = importlib.util.spec_from_file_location(
    "te_identity_retrieval_for_glm", HERE / "identity_retrieval.py"
)
assert IDENTITY_SPEC is not None and IDENTITY_SPEC.loader is not None
identity = importlib.util.module_from_spec(IDENTITY_SPEC)
IDENTITY_SPEC.loader.exec_module(identity)


MODEL_ID = "nucleotide-transformer-v2-500m-multi-species"
CONTRACT_VERSION = "te-identity-retrieval-glm-v1"
SEED = 42
DEFAULT_MAX_TOKENS = 2048


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


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


def require_native_model(model_path: Path) -> dict:
    """Fail closed if the requested directory is not the native NTv2 model."""

    if model_path.name != MODEL_ID:
        raise ValueError(
            "refusing a non-native model directory: expected %s, got %s"
            % (MODEL_ID, model_path.name)
        )
    if not model_path.is_dir():
        raise FileNotFoundError("native model directory does not exist: %s" % model_path)
    config_path = model_path / "config.json"
    tokenizer_path = model_path / "vocab.txt"
    if not config_path.is_file() or not tokenizer_path.is_file():
        raise FileNotFoundError("native model is missing config.json or vocab.txt: %s" % model_path)
    weight_files = [model_path / "model.safetensors", model_path / "pytorch_model.bin"]
    if not any(path.is_file() for path in weight_files):
        raise FileNotFoundError("native model has no local weight file: %s" % model_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    metadata_path = model_path / "download_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    if metadata.get("key") and metadata["key"] != MODEL_ID:
        raise ValueError("native model metadata key does not match %s" % MODEL_ID)
    return {
        "model_id": MODEL_ID,
        "config_path": str(config_path),
        "config_hidden_size": int(config.get("hidden_size", 0)),
        "config_max_position_embeddings": int(config.get("max_position_embeddings", 0)),
        "weight_files_present": [str(path) for path in weight_files if path.is_file()],
        "download_metadata": metadata,
    }


def _flatten_token_ids(value: object) -> List[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list) and value and isinstance(value[0], list):
        value = value[0]
    return [int(item) for item in (value or [])]


def token_segments(tokenizer, sequence: str, max_token_length: int = DEFAULT_MAX_TOKENS) -> List[List[int]]:
    """Tokenize without specials and split at content-token boundaries."""

    if max_token_length < 2:
        raise ValueError("max_token_length must leave room for special tokens")
    encoded = tokenizer(sequence, add_special_tokens=False, truncation=False)
    content_ids = _flatten_token_ids(encoded["input_ids"])
    special_count = len(tokenizer.build_inputs_with_special_tokens([]))
    content_budget = max_token_length - special_count
    if content_budget < 1:
        raise ValueError("tokenizer special-token count exceeds max token length")
    if not content_ids:
        return [[]]
    return [content_ids[start:start + content_budget] for start in range(0, len(content_ids), content_budget)]


def non_special_mask(input_ids: Sequence[int], attention_mask: Sequence[int], special_ids: Iterable[int]) -> List[int]:
    specials = set(int(value) for value in special_ids)
    return [int(bool(attention) and int(token) not in specials) for token, attention in zip(input_ids, attention_mask)]


def weighted_segment_mean(segment_vectors: Sequence[Sequence[float]], weights: Sequence[int]) -> List[float]:
    """Pure-Python weighted mean used by tests and as a clear contract oracle."""

    if len(segment_vectors) != len(weights) or not segment_vectors:
        raise ValueError("segment vectors and weights must be non-empty and aligned")
    total = sum(int(weight) for weight in weights)
    if total <= 0:
        raise ValueError("segment weights must contain a positive content-token count")
    dimension = len(segment_vectors[0])
    if not dimension or any(len(vector) != dimension for vector in segment_vectors):
        raise ValueError("segment vectors must have one non-empty common dimension")
    return [
        sum(float(vector[index]) * int(weight) for vector, weight in zip(segment_vectors, weights)) / total
        for index in range(dimension)
    ]


def _effective_max_tokens(tokenizer, model, requested: int) -> int:
    limits = [int(requested)]
    tokenizer_limit = getattr(tokenizer, "model_max_length", None)
    if tokenizer_limit is not None and int(tokenizer_limit) < 1000000:
        limits.append(int(tokenizer_limit))
    model_limit = getattr(getattr(model, "config", None), "max_position_embeddings", None)
    if model_limit is not None and int(model_limit) > 0:
        limits.append(int(model_limit))
    return min(limits)


def embed_records(
    records: Sequence[Mapping[str, str]],
    tokenizer,
    model,
    device,
    batch_size: int,
    max_token_length: int,
) -> Tuple[object, dict]:
    """Return one CPU float32 matrix and segmentation metadata."""

    import numpy as np
    import torch

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    effective_max = _effective_max_tokens(tokenizer, model, max_token_length)
    special_ids = set(int(value) for value in getattr(tokenizer, "all_special_ids", []))
    segment_ids: List[List[int]] = []
    segment_record_indices: List[int] = []
    record_segments: List[List[int]] = [[] for _ in records]
    record_lengths: List[int] = []
    for record_index, row in enumerate(records):
        sequence = sequence_for(row)
        if not sequence:
            raise ValueError("record %s has no inline or readable sequence" % row.get("record_id", record_index))
        parts = token_segments(tokenizer, sequence, effective_max)
        record_lengths.append(len(parts))
        for part in parts:
            segment_index = len(segment_ids)
            segment_ids.append(part)
            segment_record_indices.append(record_index)
            record_segments[record_index].append(segment_index)

    segment_vectors: List[np.ndarray] = []
    segment_weights: List[int] = []
    model.eval()
    for start in range(0, len(segment_ids), batch_size):
        current = segment_ids[start:start + batch_size]
        full_ids = [tokenizer.build_inputs_with_special_tokens(part) for part in current]
        encoded = tokenizer.pad({"input_ids": full_ids}, padding=True, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in encoded.items() if key in {"input_ids", "attention_mask"}}
        with torch.inference_mode():
            outputs = model(**inputs, output_hidden_states=True, return_dict=True)
        hidden = outputs.hidden_states[-1] if getattr(outputs, "hidden_states", None) is not None else outputs.last_hidden_state
        attention = inputs["attention_mask"].to(dtype=torch.bool)
        token_mask = attention.clone()
        for special_id in special_ids:
            token_mask &= inputs["input_ids"].ne(special_id)
        counts = token_mask.sum(dim=1)
        if bool((counts <= 0).any()):
            raise ValueError("a segment has no non-special content tokens")
        pooled = (hidden * token_mask.unsqueeze(-1).to(dtype=hidden.dtype)).sum(dim=1)
        pooled = pooled / counts.unsqueeze(-1).to(dtype=hidden.dtype)
        segment_vectors.extend(pooled.detach().float().cpu().numpy())
        segment_weights.extend(int(value) for value in counts.detach().cpu().tolist())

    if len(segment_vectors) != len(segment_ids):
        raise ValueError("embedding segment count does not match tokenized input")
    vectors = []
    for indices in record_segments:
        vectors.append(
            np.asarray(
                weighted_segment_mean(
                    [segment_vectors[index].tolist() for index in indices],
                    [segment_weights[index] for index in indices],
                ),
                dtype=np.float32,
            )
        )
    matrix = np.vstack(vectors).astype(np.float32, copy=False)
    if not np.isfinite(matrix).all():
        raise ValueError("native encoder produced a non-finite embedding")
    return matrix, {
        "effective_max_token_length": effective_max,
        "total_segments": len(segment_ids),
        "records_with_multiple_segments": sum(length > 1 for length in record_lengths),
        "max_segments_per_record": max(record_lengths) if record_lengths else 0,
        "segment_content_token_counts": segment_weights,
    }


def run(
    input_manifest: Path,
    model_path: Path,
    out_dir: Path,
    batch_size: int = 1,
    max_token_length: int = DEFAULT_MAX_TOKENS,
) -> dict:
    """Audit and extract embeddings; return the machine-readable status."""

    import numpy as np
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    out_dir.mkdir(parents=True, exist_ok=True)
    model_info = require_native_model(model_path)
    raw = identity.load_rows(input_manifest)
    normalized = [identity.normalize_row(row, index) for index, row in enumerate(raw)]
    audit = identity.audit_manifest(normalized)
    write_json(out_dir / "input_audit.json", audit)
    if audit["status"] != "PASS_AUDIT":
        status = {
            "status": "NOTRUN_IDENTITY_AUDIT",
            "reason": audit["status"],
            "model_id": MODEL_ID,
            "scientific_claim_status": "NOTRUN",
        }
        write_json(out_dir / "status.json", status)
        return status
    if not normalized:
        raise ValueError("identity manifest contains no records")

    random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    # The native NTv2 directory exposes its GLU-compatible architecture through
    # AutoModelForMaskedLM.  AutoModel falls back to the built-in ESM class,
    # whose non-GLU intermediate layer is shape-incompatible with these native
    # weights; using the masked-LM wrapper is still encoder-only inference and
    # we read its final hidden state without evaluating logits.
    model = AutoModelForMaskedLM.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    model.to(device)
    matrix, segment_info = embed_records(
        normalized,
        tokenizer,
        model,
        device,
        batch_size=batch_size,
        max_token_length=max_token_length,
    )
    np.save(out_dir / "embeddings.npy", matrix)
    record_ids = [row["record_id"] for row in normalized]
    (out_dir / "embedding_ids.json").write_text(json.dumps(record_ids, indent=2) + "\n", encoding="utf-8")
    metadata = {
        "contract_version": CONTRACT_VERSION,
        "model_id": MODEL_ID,
        "model_path": str(model_path.resolve()),
        "model_info": model_info,
        "device": str(device),
        "seed": SEED,
        "records": len(normalized),
        "embedding_shape": [int(matrix.shape[0]), int(matrix.shape[1])],
        "embedding_dtype": str(matrix.dtype),
        "pooling": "mean",
        "special_tokens_excluded": True,
        "special_token_ids": sorted(int(value) for value in getattr(tokenizer, "all_special_ids", [])),
        "segmentation": {
            "max_token_length_requested": max_token_length,
            "content_token_boundary_split": True,
            "segment_aggregation": "content_token_count_weighted_mean",
            "overlap_tokens": 0,
            **segment_info,
        },
        "pretraining_exposure_status": "UNRESOLVED",
        "contrastive_training": "NOTRUN",
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY_PENDING_RETRIEVAL",
    }
    write_json(out_dir / "embedding_meta.json", metadata)
    status = {
        "status": "PASS_GLM_EMBEDDING_EXTRACTION",
        "scientific_claim_status": "ANNOTATION_LEVEL_ONLY_PENDING_RETRIEVAL",
        "model_id": MODEL_ID,
        "records": len(normalized),
        "embedding_shape": [int(matrix.shape[0]), int(matrix.shape[1])],
        "scores_written": False,
        "real_glm_embedding": True,
        "contrastive_training": False,
        "pretraining_exposure_status": "UNRESOLVED",
    }
    write_json(out_dir / "status.json", status)
    return status


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-token-length", type=int, default=DEFAULT_MAX_TOKENS)
    args = parser.parse_args(argv)
    run(
        args.input_manifest,
        args.model_path,
        args.out_dir,
        batch_size=args.batch_size,
        max_token_length=args.max_token_length,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
