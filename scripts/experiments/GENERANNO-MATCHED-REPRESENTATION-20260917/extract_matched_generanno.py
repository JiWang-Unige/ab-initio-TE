#!/usr/bin/env python3
"""Extract matched GENERanno hidden states on the fixed SIB 512-bp panel.

The three checkpoints are loaded for inference only: untouched GENERanno,
binary token-classification fine tuning, and the eight-state SF5 token-classifier
checkpoint.  Every checkpoint uses the untouched GENERanno tokenizer and the
same mean pooling excluding structural specials while retaining N/UNK.
The output schema intentionally matches
``evaluate_matched_embeddings.py`` so that the predeclared readouts and
K-means diagnostics are reused without changing their denominator.
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
from pathlib import Path
from typing import Any


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
POOLING = "attention_mask_mean_excluding_padding_and_special_tokens"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--tokenizer-checkpoint", type=Path, required=True)
    ap.add_argument("--model", action="append", required=True, help="ID=PATH=KIND")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-length", type=int, default=2048)
    ap.add_argument("--max-records", type=int, default=None)
    ap.add_argument("--device", default="cuda")
    return ap.parse_args()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_records(path: Path, max_records: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            sequence = str(row.get("sequence", "")).upper()
            if len(sequence) != 512:
                raise ValueError(f"{path}:{line_no}: expected a 512-bp sequence, got {len(sequence)}")
            label = row.get("label")
            if label is None or int(label) not in range(len(LABEL_NAMES)):
                raise ValueError(f"{path}:{line_no}: invalid label {label!r}")
            for key in ("species_code", "chr", "start", "end"):
                if key not in row:
                    raise ValueError(f"{path}:{line_no}: missing identity field {key}")
            normalized = dict(row)
            normalized["sequence"] = sequence
            normalized["label"] = int(label)
            rows.append(normalized)
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


def hidden_output(output: Any) -> Any:
    hidden_states = getattr(output, "hidden_states", None)
    if hidden_states is not None:
        return hidden_states[-1]
    last = getattr(output, "last_hidden_state", None)
    if last is not None:
        return last
    raise RuntimeError("model output has neither hidden_states nor last_hidden_state")


def encoder_forward(model: Any, encoded: dict[str, Any]) -> Any:
    """Call the shared GENERanno encoder, bypassing task-specific heads.

    The native masked-LM wrapper can return a ``MaskedLMOutput`` whose
    ``hidden_states`` field is empty under some Transformers versions even
    when the encoder was asked for hidden states.  Both fine-tuned wrappers
    contain the same ``GenerannoModel`` under ``.model``.  Calling that encoder
    directly makes the representation contract explicit and keeps all three
    arms independent of their classifier/LM heads.
    """

    encoder = getattr(model, "model", None)
    if encoder is None:
        raise RuntimeError(f"{model.__class__.__name__} has no GENERanno encoder at .model")
    return encoder(**encoded, output_hidden_states=True, return_dict=True)


def load_model(model_path: Path, kind: str, tokenizer_checkpoint: Path, device: Any):
    from transformers import AutoModelForMaskedLM, AutoModelForTokenClassification, AutoTokenizer

    if not model_path.is_dir():
        raise FileNotFoundError(model_path)
    tokenizer = AutoTokenizer.from_pretrained(
        str(tokenizer_checkpoint), trust_remote_code=True, local_files_only=True
    )
    if kind == "pretrained":
        model = AutoModelForMaskedLM.from_pretrained(
            str(model_path), trust_remote_code=True, local_files_only=True
        )
    else:
        model = AutoModelForTokenClassification.from_pretrained(
            str(model_path), trust_remote_code=True, local_files_only=True
        )
    model.to(device)
    model.eval()
    return model, tokenizer


def extract_model(
    *,
    model_id: str,
    model_path: Path,
    kind: str,
    tokenizer_checkpoint: Path,
    rows_by_split: dict[str, list[dict[str, Any]]],
    out_root: Path,
    batch_size: int,
    max_length: int,
    device_name: str,
) -> dict[str, Any]:
    import numpy as np
    import torch

    device = torch.device(device_name)
    model, tokenizer = load_model(model_path, kind, tokenizer_checkpoint, device)
    tokenizer_special_ids = sorted({int(value) for value in getattr(tokenizer, "all_special_ids", [])})
    # GENERanno declares the ambiguity symbol N as unk_token.  N is still a
    # sequence observation, and the fixed SIB panel contains windows made
    # entirely of N.  Exclude structural specials while retaining unk/N so an
    # ambiguity window has a valid pooled representation.
    unknown_id = getattr(tokenizer, "unk_token_id", None)
    special_ids = [
        value for value in tokenizer_special_ids if unknown_id is None or value != int(unknown_id)
    ]
    model_out_root = out_root / model_id
    model_out_root.mkdir(parents=True, exist_ok=True)
    hidden_dim: int | None = None
    meta: dict[str, Any] = {
        "schema": "matched_generanno_embedding_v1",
        "model_id": model_id,
        "model_path": str(model_path),
        "model_kind": kind,
        "tokenizer_path": str(tokenizer_checkpoint),
        "data_contract": "SIB-RETREAT-EMBED-REPLICATION-20260917/data_512",
        "pooling": POOLING,
        "tokenizer_special_token_ids": tokenizer_special_ids,
        "pooling_excluded_token_ids": special_ids,
        "preserved_unknown_token_id": None if unknown_id is None else int(unknown_id),
        "max_length": max_length,
        "dtype_saved": "float32",
        "device": str(device),
        "model_class": model.__class__.__name__,
        "splits": {},
    }
    try:
        import torch

        with torch.inference_mode():
            for split in SPLITS:
                rows = rows_by_split[split]
                vectors = []
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
                    output = encoder_forward(model, encoded)
                    hidden = hidden_output(output)
                    token_mask = encoded["attention_mask"].to(dtype=torch.bool)
                    for special_id in special_ids:
                        token_mask &= encoded["input_ids"].ne(special_id)
                    counts = token_mask.sum(dim=1)
                    if bool((counts <= 0).any()):
                        raise RuntimeError(f"{model_id}/{split}: a record has no content tokens")
                    pooled = (hidden * token_mask.unsqueeze(-1).to(dtype=hidden.dtype)).sum(dim=1)
                    pooled = pooled / counts.unsqueeze(-1).to(dtype=hidden.dtype)
                    if hidden_dim is None:
                        hidden_dim = int(pooled.shape[1])
                    elif int(pooled.shape[1]) != hidden_dim:
                        raise RuntimeError("hidden dimension changed within extraction")
                    vectors.append(pooled.float().cpu().numpy())
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
                                    "species_code": row.get("species_code"),
                                    "chr": row.get("chr"),
                                    "start": row.get("start"),
                                    "end": row.get("end"),
                                    "source_record": row.get("source_record"),
                                    "source_chunk": row.get("source_chunk"),
                                    "label": int(row["label"]),
                                    "label_name": LABEL_NAMES[int(row["label"])],
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
    if args.batch_size < 1 or args.max_length < 514:
        raise SystemExit("batch size must be positive and max_length must preserve 512 bp plus specials")
    models = [parse_model_spec(spec) for spec in args.model]
    rows_by_split = {
        split: load_records(args.data_dir / split / "data.jsonl.gz", args.max_records)
        for split in SPLITS
    }
    identities = {split: [record_key(row) for row in rows] for split, rows in rows_by_split.items()}
    if any(not keys for keys in identities.values()):
        raise RuntimeError("empty input split")
    args.out_root.mkdir(parents=True, exist_ok=True)
    write_json(
        args.out_root / "input_manifest.json",
        {
            "schema": "matched_generanno_embedding_manifest_v1",
            "data_dir": str(args.data_dir),
            "tokenizer_checkpoint": str(args.tokenizer_checkpoint),
            "pooling": POOLING,
            "special_tokens_are_excluded": True,
            "split_counts": {split: len(rows) for split, rows in rows_by_split.items()},
            "record_keys": identities,
            "models": [{"id": mid, "path": str(path), "kind": kind} for mid, path, kind in models],
            "max_records": args.max_records,
        },
    )
    results = []
    for model_id, model_path, kind in models:
        results.append(
            extract_model(
                model_id=model_id,
                model_path=model_path,
                kind=kind,
                tokenizer_checkpoint=args.tokenizer_checkpoint,
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
