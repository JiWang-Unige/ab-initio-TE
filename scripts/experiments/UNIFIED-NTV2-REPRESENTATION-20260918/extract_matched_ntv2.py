#!/usr/bin/env python3
"""Extract the three matched NTv2 representations on the frozen SIB panel.

The sequence, split, record order, native tokenizer, and pooling contract are
identical for all arms.  A token is content when it is attended and is not a
structural tokenizer token (CLS, PAD, or MASK).  The tokenizer's UNK id is
retained because it represents an input token; an N k-mer is retained as a
native vocabulary token as well.  No label or target is used during
extraction.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from pathlib import Path
from typing import Any

import numpy as np


LABEL_NAMES = [
    "BG",
    "SINE",
    "LINE",
    "LTR",
    "DNA",
    "KNOWN_OTHER_TE",
    "AMBIGUOUS_TE",
    "UNCLASSIFIED",
]
SPLITS = ("train", "val", "test")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--base-model", type=Path, required=True)
    ap.add_argument(
        "--model",
        action="append",
        required=True,
        help="MODEL_ID=PATH=KIND, where KIND is pretrained or token_classifier",
    )
    ap.add_argument("--batch-size", type=int, default=8)
    # 2048 is the max-length used by the completed NTv2 matched extraction;
    # the 512-bp SIB sequences are far shorter than this bound.
    ap.add_argument("--max-length", type=int, default=2048)
    ap.add_argument("--max-records", type=int, default=None)
    ap.add_argument("--device", default="cuda")
    return ap.parse_args()


def load_records(path: Path, max_records: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            sequence = str(row.get("sequence", "")).upper()
            label = row.get("label")
            if not sequence:
                raise ValueError(f"{path}:{line_no}: empty sequence")
            if label is None or int(label) not in range(len(LABEL_NAMES)):
                raise ValueError(f"{path}:{line_no}: invalid label {label!r}")
            for key in ("species_code", "chr", "start", "end"):
                if key not in row:
                    raise ValueError(f"{path}:{line_no}: missing identity field {key}")
            row = dict(row)
            row["sequence"] = sequence
            row["label"] = int(label)
            rows.append(row)
            if max_records is not None and len(rows) >= max_records:
                break
    if not rows:
        raise ValueError(f"no records in {path}")
    return rows


def record_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("species_code")),
            str(row.get("chr")),
            str(row.get("start")),
            str(row.get("end")),
            str(row.get("source_record", row.get("source_chunk", ""))),
        ]
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_model_spec(spec: str) -> tuple[str, Path, str]:
    pieces = spec.split("=", 2)
    if len(pieces) != 3:
        raise ValueError(f"--model must be ID=PATH=KIND, got {spec!r}")
    model_id, path, kind = pieces
    if kind not in {"pretrained", "token_classifier"}:
        raise ValueError(f"unsupported model kind {kind!r}")
    if not model_id or not path:
        raise ValueError(f"invalid model specification {spec!r}")
    return model_id, Path(path), kind


def native_token_classifier(model_path: Path, base_model: Path):
    """Load a native D or class checkpoint with its original implementation."""
    import torch
    from transformers import AutoConfig, AutoTokenizer
    from transformers.dynamic_module_utils import get_class_from_dynamic_module

    config = AutoConfig.from_pretrained(
        str(model_path), trust_remote_code=True, local_files_only=True
    )
    model_class = get_class_from_dynamic_module(
        config.auto_map["AutoModelForTokenClassification"],
        str(base_model),
        local_files_only=True,
    )
    model = model_class._from_config(config)
    state_path = model_path / "pytorch_model.bin"
    if not state_path.is_file():
        raise FileNotFoundError(state_path)
    state = torch.load(state_path, map_location="cpu")
    result = model.load_state_dict(state, strict=True)
    if result.missing_keys or result.unexpected_keys:
        raise RuntimeError(f"strict state load returned mismatch: {result}")
    tokenizer = AutoTokenizer.from_pretrained(
        str(base_model), trust_remote_code=True, local_files_only=True
    )
    return model, tokenizer


def hidden_output(output: Any) -> Any:
    hidden_states = getattr(output, "hidden_states", None)
    if hidden_states is not None:
        return hidden_states[-1]
    last = getattr(output, "last_hidden_state", None)
    if last is not None:
        return last
    raise RuntimeError("model output has neither hidden_states nor last_hidden_state")


def structural_special_ids(tokenizer: Any) -> list[int]:
    """Return IDs removed from pooling while retaining input UNK tokens."""
    all_special = {int(value) for value in getattr(tokenizer, "all_special_ids", [])}
    unk = getattr(tokenizer, "unk_token_id", None)
    if unk is not None:
        all_special.discard(int(unk))
    # The native tokenizer exposes PAD/CLS/MASK as all_special_ids.  If a
    # future checkpoint has declared BOS/EOS, they remain structural too.
    return sorted(all_special)


def extract_model(
    *,
    model_id: str,
    model_path: Path,
    kind: str,
    base_model: Path,
    rows_by_split: dict[str, list[dict[str, Any]]],
    out_root: Path,
    batch_size: int,
    max_length: int,
    device_name: str,
) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    if not model_path.is_dir():
        raise FileNotFoundError(model_path)
    device = torch.device(device_name)
    if kind == "pretrained":
        tokenizer = AutoTokenizer.from_pretrained(
            str(base_model), trust_remote_code=True, local_files_only=True
        )
        model = AutoModelForMaskedLM.from_pretrained(
            str(model_path), trust_remote_code=True, local_files_only=True
        )
    else:
        model, tokenizer = native_token_classifier(model_path, base_model)
    model.to(device)
    model.eval()
    special_ids = structural_special_ids(tokenizer)
    unk_id = getattr(tokenizer, "unk_token_id", None)
    hidden_dim: int | None = None
    model_out_root = out_root / model_id
    model_out_root.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {
        "schema": "unified_ntv2_embedding_v1",
        "model_id": model_id,
        "model_path": str(model_path),
        "model_kind": kind,
        "tokenizer_path": str(base_model),
        "data_contract": "SIB-RETREAT-EMBED-REPLICATION-20260917/data_512",
        "pooling": "attention_mask_mean_excluding_structural_special_tokens_and_padding",
        "structural_special_token_ids": special_ids,
        "unk_token_id_retained": None if unk_id is None else int(unk_id),
        "N_input_tokens_retained": True,
        "max_length": max_length,
        "dtype_saved": "float32",
        "device": str(device),
        "splits": {},
    }
    try:
        with torch.inference_mode():
            for split in SPLITS:
                rows = rows_by_split[split]
                vectors: list[np.ndarray] = []
                pooled_counts: list[int] = []
                started = time.time()
                for start in range(0, len(rows), batch_size):
                    batch = rows[start : start + batch_size]
                    encoded = tokenizer(
                        [row["sequence"] for row in batch],
                        padding=True,
                        truncation=True,
                        max_length=max_length,
                        return_tensors="pt",
                    )
                    encoded = {
                        key: value.to(device)
                        for key, value in encoded.items()
                        if key in {"input_ids", "attention_mask"}
                    }
                    output = model(**encoded, output_hidden_states=True)
                    hidden = hidden_output(output)
                    token_mask = encoded["attention_mask"].to(dtype=torch.bool)
                    for special_id in special_ids:
                        token_mask &= encoded["input_ids"].ne(special_id)
                    counts = token_mask.sum(dim=1)
                    if bool((counts <= 0).any()):
                        bad = int(torch.where(counts <= 0)[0][0].item())
                        raise RuntimeError(
                            f"{model_id}/{split}: record {start + bad} has no content tokens"
                        )
                    pooled = (hidden * token_mask.unsqueeze(-1).to(hidden.dtype)).sum(dim=1)
                    pooled = pooled / counts.unsqueeze(-1).to(hidden.dtype)
                    if hidden_dim is None:
                        hidden_dim = int(pooled.shape[1])
                    elif int(pooled.shape[1]) != hidden_dim:
                        raise RuntimeError("hidden dimension changed within extraction")
                    vectors.append(pooled.float().cpu().numpy())
                    pooled_counts.extend(int(value) for value in counts.cpu().tolist())
                    print(
                        f"{model_id} {split} {min(start + batch_size, len(rows))}/{len(rows)}",
                        flush=True,
                    )
                features = np.vstack(vectors).astype(np.float32, copy=False)
                labels = np.asarray([int(row["label"]) for row in rows], dtype=np.int64)
                np.save(model_out_root / f"{split}_features.npy", features)
                np.save(model_out_root / f"{split}_labels.npy", labels)
                with (model_out_root / f"{split}_records.jsonl").open("w", encoding="utf-8") as handle:
                    for index, row in enumerate(rows):
                        handle.write(
                            json.dumps(
                                {
                                    "index": index,
                                    "record_key": record_key(row),
                                    "sequence": row["sequence"],
                                    "species_code": row.get("species_code"),
                                    "chr": row.get("chr"),
                                    "start": row.get("start"),
                                    "end": row.get("end"),
                                    "source_record": row.get("source_record"),
                                    "source_chunk": row.get("source_chunk"),
                                    "label": int(row["label"]),
                                    "label_name": LABEL_NAMES[int(row["label"])],
                                    "pooled_content_tokens": pooled_counts[index],
                                },
                                sort_keys=True,
                            )
                            + "\n"
                        )
                meta["splits"][split] = {
                    "n": int(len(rows)),
                    "feature_dim": int(features.shape[1]),
                    "elapsed_seconds": time.time() - started,
                    "labels": {name: int((labels == i).sum()) for i, name in enumerate(LABEL_NAMES)},
                    "pooled_content_tokens": {
                        "min": int(min(pooled_counts)),
                        "max": int(max(pooled_counts)),
                        "mean": float(np.mean(pooled_counts)),
                    },
                }
    finally:
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    meta["feature_dim"] = int(hidden_dim or 0)
    write_json(model_out_root / "metadata.json", meta)
    return meta


def main() -> None:
    args = parse_args()
    if args.batch_size < 1 or args.max_length < 1:
        raise SystemExit("batch size and max length must be positive")
    models = [parse_model_spec(spec) for spec in args.model]
    rows_by_split = {
        split: load_records(args.data_dir / split / "data.jsonl.gz", args.max_records)
        for split in SPLITS
    }
    identities = {split: [record_key(row) for row in rows] for split, rows in rows_by_split.items()}
    if any(not keys for keys in identities.values()):
        raise RuntimeError("empty input split")
    args.out_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "unified_ntv2_embedding_manifest_v1",
        "data_dir": str(args.data_dir),
        "base_model": str(args.base_model),
        "pooling": "attention_mask_mean_excluding_structural_special_tokens_and_padding",
        "structural_special_tokens_are_excluded": True,
        "unk_token_is_retained": True,
        "N_input_tokens_are_retained": True,
        "split_counts": {split: len(rows) for split, rows in rows_by_split.items()},
        "record_keys": identities,
        "models": [{"id": mid, "path": str(path), "kind": kind} for mid, path, kind in models],
        "max_records": args.max_records,
    }
    write_json(args.out_root / "input_manifest.json", manifest)
    results = []
    for model_id, model_path, kind in models:
        results.append(
            extract_model(
                model_id=model_id,
                model_path=model_path,
                kind=kind,
                base_model=args.base_model,
                rows_by_split=rows_by_split,
                out_root=args.out_root,
                batch_size=args.batch_size,
                max_length=args.max_length,
                device_name=args.device,
            )
        )
    write_json(args.out_root / "extraction_summary.json", {"models": results})


if __name__ == "__main__":
    main()
