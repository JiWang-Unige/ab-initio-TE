#!/usr/bin/env python3
"""Extract target-centered representations under three context lengths.

This is a bounded context diagnostic, not a replacement for the fixed SIB
panel.  Each selected 4096-bp source record contributes the same central
512-bp target and target label under 512-, 2048-, and 4096-bp inputs.  Only
flanking sequence changes.  The native NTv2 tokenizer is slow and does not
provide offsets, so the script reconstructs the six-bp token spans used by D,
then verifies both the content-token count and content input IDs before using
overlap-weighted target pooling.  A mismatch stops the run instead of
guessing a target position.
"""
from __future__ import annotations

import argparse
import collections
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
SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
SPLITS = ("train", "val", "test")
SOURCE_SPLIT = {"train": "TRAIN", "val": "CAL", "test": "DEV"}
CONTEXTS = (512, 2048, 4096)
WINDOW_BP = 4096
TARGET_BP = 512
TARGET_START = (WINDOW_BP - TARGET_BP) // 2
TARGET_END = TARGET_START + TARGET_BP


def context_coordinates(context_length: int) -> tuple[int, int, int, int]:
    """Return source/context bounds for the fixed central target.

    The source record is always 4,096 bp and the target is its central
    ``[TARGET_START, TARGET_END)`` span.  Contexts must be centered on that
    same target; source and context-local coordinates are deliberately kept
    separate so target pooling cannot silently use a source offset as a local
    token offset.
    """
    if context_length not in CONTEXTS:
        raise ValueError(f"unsupported context length: {context_length}")
    context_start = TARGET_START - (context_length - TARGET_BP) // 2
    context_end = context_start + context_length
    target_start = TARGET_START - context_start
    target_end = target_start + TARGET_BP
    if context_start < 0 or context_end > WINDOW_BP:
        raise RuntimeError(
            f"context {context_length} exceeds source: [{context_start},{context_end})"
        )
    if target_start < 0 or target_end > context_length:
        raise RuntimeError(
            f"target {target_start}:{target_end} is outside context {context_length}"
        )
    return context_start, context_end, target_start, target_end


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary-data-root", type=Path, required=True)
    ap.add_argument("--class-data-root", type=Path, required=True)
    ap.add_argument("--worm-train-override", type=Path, required=True)
    ap.add_argument("--base-model", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument(
        "--model",
        action="append",
        required=True,
        help="MODEL_ID=PATH=KIND, where KIND is pretrained or token_classifier",
    )
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()


def open_gzip_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            sequence = str(row.get("sequence", "")).upper()
            if len(sequence) != WINDOW_BP:
                raise ValueError(f"{path}:{line_no}: expected {WINDOW_BP}-bp sequence")
            row = dict(row)
            row["sequence"] = sequence
            rows.append(row)
    if not rows:
        raise ValueError(f"empty source file: {path}")
    return rows


def identity(row: dict[str, Any]) -> tuple[str, str, str, int, int, str, int]:
    return (
        str(row.get("species_code")),
        str(row.get("assembly")),
        str(row.get("chrom", row.get("chr"))),
        int(row["start"]),
        int(row["end"]),
        str(row.get("tile_id", "")),
        int(row.get("half", 0)),
    )


def evenly_spaced(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    if n < 1 or len(rows) < n:
        raise ValueError(f"cannot select {n} rows from {len(rows)} source rows")
    if n == 1:
        indices = [0]
    else:
        indices = [round(i * (len(rows) - 1) / (n - 1)) for i in range(n)]
    if len(set(indices)) != n:
        raise ValueError("evenly spaced source indices are not unique")
    return [rows[index] for index in indices]


def source_rows(args: argparse.Namespace) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    selected: dict[str, list[dict[str, Any]]] = {split: [] for split in SPLITS}
    selection_meta: dict[str, Any] = {}
    for split in SPLITS:
        per_species: dict[str, Any] = {}
        n = {"train": 64, "val": 32, "test": 32}[split]
        for species in SPECIES:
            source = args.binary_data_root / SOURCE_SPLIT[split] / f"{species}.jsonl.gz"
            if species == "c_elegans" and split == "train":
                source = args.worm_train_override
            rows = open_gzip_jsonl(source)
            chosen = evenly_spaced(rows, n)
            for row in chosen:
                if str(row.get("species_code")) != species:
                    raise ValueError(f"source species mismatch in {source}: {row.get('species_code')!r}")
                selected[split].append(row)
            per_species[species] = {
                "source": str(source),
                "source_rows": len(rows),
                "selected_rows": len(chosen),
                "selected_source_indices": [rows.index(row) for row in chosen],
            }
        selection_meta[split] = per_species
    return selected, selection_meta


def class_rows(args: argparse.Namespace) -> dict[tuple[str, str, str, int, int, str, int], dict[str, Any]]:
    lookup: dict[tuple[str, str, str, int, int, str, int], dict[str, Any]] = {}
    for split in SPLITS:
        path = args.class_data_root / split / "data.jsonl.gz"
        for row in open_gzip_jsonl(path):
            key = identity(row)
            if key in lookup:
                raise ValueError(f"duplicate matched class identity: {key}")
            lookup[key] = row
    return lookup


def target_label(row: dict[str, Any]) -> tuple[int, dict[str, int]]:
    labels = str(row.get("labels", ""))
    if len(labels) != WINDOW_BP or any(char not in "01234567" for char in labels):
        raise ValueError("matched class row lacks a 4096-character class label string")
    counts = collections.Counter(labels[TARGET_START:TARGET_END])
    max_count = max(counts.values())
    winners = sorted(int(char) for char, count in counts.items() if count == max_count)
    return winners[0], {LABEL_NAMES[int(char)]: int(count) for char, count in sorted(counts.items())}


def sequence_tokens_with_spans(sequence: str, width: int = 6) -> tuple[list[str], list[tuple[int, int]]]:
    tokens: list[str] = []
    spans: list[tuple[int, int]] = []
    full = len(sequence) // width * width
    for start in range(0, full, width):
        raw = sequence[start : start + width]
        tokens.append(raw if set(raw) <= {"A", "C", "G", "T"} else "<unk>")
        spans.append((start, start + width))
    for offset in range(full, len(sequence)):
        raw = sequence[offset]
        tokens.append(raw if raw in {"A", "C", "G", "T"} else "<unk>")
        spans.append((offset, offset + 1))
    return tokens, spans


def structural_special_ids(tokenizer: Any) -> list[int]:
    ids = {int(value) for value in getattr(tokenizer, "all_special_ids", [])}
    unk = getattr(tokenizer, "unk_token_id", None)
    if unk is not None:
        ids.discard(int(unk))
    return sorted(ids)


def encode_contexts(tokenizer: Any, sequences: list[str], target_start: int, target_end: int, device: Any):
    import torch

    token_batches = []
    spans_batches = []
    for sequence in sequences:
        tokens, spans = sequence_tokens_with_spans(sequence)
        token_batches.append(tokens)
        spans_batches.append(spans)
    lengths = {len(tokens) for tokens in token_batches}
    if len(lengths) != 1:
        raise RuntimeError(f"fixed context batch produced variable token counts: {sorted(lengths)}")
    token_count = len(token_batches[0])
    max_length = ((token_count + 2 + 7) // 8) * 8
    encoded = tokenizer(
        token_batches,
        is_split_into_words=True,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_special_tokens_mask=True,
        return_tensors="pt",
    )
    structural = structural_special_ids(tokenizer)
    content_positions: list[list[int]] = []
    for row_index in range(len(sequences)):
        positions = [
            position
            for position, (attended, is_special) in enumerate(
                zip(encoded["attention_mask"][row_index].tolist(), encoded["special_tokens_mask"][row_index].tolist())
            )
            if attended and not is_special and int(encoded["input_ids"][row_index, position]) not in structural
        ]
        expected_ids = tokenizer.convert_tokens_to_ids(token_batches[row_index])
        actual_ids = [int(encoded["input_ids"][row_index, position]) for position in positions]
        if len(positions) != len(spans_batches[row_index]) or actual_ids != list(expected_ids):
            raise RuntimeError(
                "native token-offset mapping blocked: content token count/IDs do not match "
                f"verified six-bp spans (row={row_index}, content={len(positions)}, spans={len(spans_batches[row_index])})"
            )
        content_positions.append(positions)
    outputs = {key: value.to(device) for key, value in encoded.items() if key in {"input_ids", "attention_mask"}}
    return outputs, content_positions, spans_batches, max_length


def target_pool(hidden: Any, content_positions: list[list[int]], spans_batches: list[list[tuple[int, int]]], target_start: int, target_end: int):
    import torch

    pooled: list[Any] = []
    overlap_counts: list[int] = []
    for row_index, positions in enumerate(content_positions):
        weights = []
        valid_positions = []
        for position, (span_start, span_end) in zip(positions, spans_batches[row_index]):
            overlap = max(0, min(span_end, target_end) - max(span_start, target_start))
            if overlap:
                valid_positions.append(position)
                weights.append(float(overlap))
        if sum(weights) != target_end - target_start:
            raise RuntimeError(
                f"target span coverage mismatch: covered={sum(weights)}, target={target_end - target_start}"
            )
        weight = torch.tensor(weights, dtype=hidden.dtype, device=hidden.device)
        values = hidden[row_index, valid_positions]
        pooled.append((values * (weight / weight.sum()).unsqueeze(-1)).sum(dim=0))
        overlap_counts.append(len(valid_positions))
    return torch.stack(pooled), overlap_counts


def load_model(model_id: str, model_path: Path, kind: str, base_model: Path):
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer
    from transformers.dynamic_module_utils import get_class_from_dynamic_module

    tokenizer = AutoTokenizer.from_pretrained(str(base_model), trust_remote_code=True, local_files_only=True)
    if kind == "pretrained":
        model = AutoModelForMaskedLM.from_pretrained(str(model_path), trust_remote_code=True, local_files_only=True)
    else:
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(str(model_path), trust_remote_code=True, local_files_only=True)
        model_class = get_class_from_dynamic_module(
            config.auto_map["AutoModelForTokenClassification"], str(base_model), local_files_only=True
        )
        model = model_class._from_config(config)
        state = torch.load(model_path / "pytorch_model.bin", map_location="cpu")
        result = model.load_state_dict(state, strict=True)
        if result.missing_keys or result.unexpected_keys:
            raise RuntimeError(f"strict checkpoint load mismatch for {model_id}: {result}")
    return model, tokenizer


def parse_model_spec(spec: str) -> tuple[str, Path, str]:
    pieces = spec.split("=", 2)
    if len(pieces) != 3 or pieces[2] not in {"pretrained", "token_classifier"}:
        raise ValueError(f"--model must be ID=PATH=pretrained|token_classifier: {spec!r}")
    return pieces[0], Path(pieces[1]), pieces[2]


def composition(sequence: str, target_start: int, target_end: int, context_length: int) -> dict[str, float]:
    target = sequence[target_start:target_end]
    return {
        "target_gc_fraction": (target.count("G") + target.count("C")) / len(target),
        "target_N_fraction": target.count("N") / len(target),
        "context_gc_fraction": (sequence.count("G") + sequence.count("C")) / len(sequence),
        "context_N_fraction": sequence.count("N") / len(sequence),
        "context_length_bp": float(context_length),
    }


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("batch-size must be positive")
    models = [parse_model_spec(spec) for spec in args.model]
    if {model_id for model_id, _, _ in models} != {"pretrained", "binary_D", "class_D_last2"}:
        raise ValueError("length diagnostic requires exactly pretrained, binary_D, class_D_last2")
    selected, selection_meta = source_rows(args)
    class_lookup = class_rows(args)
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        for source_row in selected[split]:
            key = identity(source_row)
            matched = class_lookup.get(key)
            if matched is None:
                raise RuntimeError(f"selected source row has no matched class row: {key}")
            if str(matched["sequence"]).upper() != source_row["sequence"]:
                raise RuntimeError(f"sequence mismatch between binary and class rows: {key}")
            label, label_counts = target_label(matched)
            rows.append(
                {
                    "split": split,
                    "species_code": source_row["species_code"],
                    "source_identity": list(key),
                    "sequence_4096": source_row["sequence"],
                    "target_start": TARGET_START,
                    "target_end": TARGET_END,
                    "target_label": label,
                    "target_label_name": LABEL_NAMES[label],
                    "target_label_counts": label_counts,
                    "binary_center_label_counts": dict(collections.Counter(source_row.get("labels", "")[TARGET_START:TARGET_END])),
                }
            )
    expected_counts = {"train": 6 * 64, "val": 6 * 32, "test": 6 * 32}
    observed = collections.Counter(row["split"] for row in rows)
    if dict(observed) != expected_counts:
        raise RuntimeError(f"selected record counts {dict(observed)} != {expected_counts}")
    args.out_root.mkdir(parents=True, exist_ok=True)
    write_meta = {
        "schema": "unified_ntv2_length_context_v1",
        "protocol": "UNIFIED-NTV2-REPRESENTATION-20260918",
        "seed": args.seed,
        "source_selection": selection_meta,
        "source_record_counts": dict(observed),
        "models": [{"id": mid, "path": str(path), "kind": kind} for mid, path, kind in models],
        "context_lengths_bp": list(CONTEXTS),
        "target_span_in_4096_bp": [TARGET_START, TARGET_END],
        "context_coordinates": {
            str(context_length): {
                "source_start": context_coordinates(context_length)[0],
                "source_end": context_coordinates(context_length)[1],
                "target_start_local": context_coordinates(context_length)[2],
                "target_end_local": context_coordinates(context_length)[3],
            }
            for context_length in CONTEXTS
        },
        "target_span_definition": "exact central 512 bp of every selected 4096-bp record",
        "target_pooling": "overlap-weighted mean over native six-bp token spans; overlap weights sum to 512 bp",
        "offset_mapping": "native slow tokenizer has no offsets; explicit D six-bp spans verified by content count and input IDs; failure blocks run",
        "label_definition": "dominant eight-state class in central target; ties lowest numeric; Unknown/ambiguous retained",
        "no_training_or_target_selection": True,
    }
    (args.out_root / "input_manifest.json").write_text(json.dumps(write_meta, indent=2) + "\n", encoding="utf-8")
    with (args.out_root / "records.jsonl").open("w", encoding="utf-8") as handle:
        for index, row in enumerate(rows):
            out = {key: value for key, value in row.items() if key != "sequence_4096"}
            out["index"] = index
            handle.write(json.dumps(out, sort_keys=True) + "\n")

    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise SystemExit("length context extraction requires CUDA; use the CPU evaluator after extraction")
    for model_id, model_path, kind in models:
        model, tokenizer = load_model(model_id, model_path, kind, args.base_model)
        model.to(device).eval()
        model_dir = args.out_root / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        model_meta: dict[str, Any] = {
            "model_id": model_id,
            "model_path": str(model_path),
            "model_kind": kind,
            "pooling": "target_512_overlap_weighted_mean_final_encoder_hidden_state",
            "contexts": {},
        }
        try:
            with torch.inference_mode():
                for context_length in CONTEXTS:
                    source_start, source_end, target_start, target_end = context_coordinates(context_length)
                    context_sequences = [
                        row["sequence_4096"][source_start:source_end] for row in rows
                    ]
                    if any(len(sequence) != context_length for sequence in context_sequences):
                        raise RuntimeError(
                            f"context {context_length}: source slice did not preserve requested length"
                        )
                    if any(
                        sequence[target_start:target_end]
                        != row["sequence_4096"][TARGET_START:TARGET_END]
                        for sequence, row in zip(context_sequences, rows)
                    ):
                        raise RuntimeError(
                            f"context {context_length}: local target is not the fixed source target"
                        )
                    features: list[np.ndarray] = []
                    overlap_counts: list[int] = []
                    started = time.time()
                    for start in range(0, len(rows), args.batch_size):
                        batch_sequences = context_sequences[start : start + args.batch_size]
                        encoded, positions, spans, max_length = encode_contexts(
                            tokenizer, batch_sequences, target_start, target_end, device
                        )
                        output = model(**encoded, output_hidden_states=True)
                        hidden_states = getattr(output, "hidden_states", None)
                        if hidden_states is None:
                            raise RuntimeError(f"{model_id}: model output has no hidden_states")
                        pooled, counts = target_pool(hidden_states[-1], positions, spans, target_start, target_end)
                        features.append(pooled.float().cpu().numpy())
                        overlap_counts.extend(counts)
                    matrix = np.vstack(features).astype(np.float32, copy=False)
                    np.save(model_dir / f"context_{context_length}_features.npy", matrix)
                    np.save(model_dir / f"context_{context_length}_labels.npy", np.asarray([row["target_label"] for row in rows], dtype=np.int64))
                    with (model_dir / f"context_{context_length}_composition.jsonl").open("w", encoding="utf-8") as handle:
                        for row in rows:
                            split = row["split"]
                            # The context string is reconstructed from the
                            # frozen source sequence, so this is not a new
                            # sequence input or a target-label operation.
                            context = row["sequence_4096"][source_start:source_end]
                            handle.write(json.dumps(composition(context, target_start, target_end, context_length)) + "\n")
                    model_meta["contexts"][str(context_length)] = {
                        "n": int(len(rows)),
                        "feature_dim": int(matrix.shape[1]),
                        "elapsed_seconds": time.time() - started,
                        "target_token_count": {
                            "min": int(min(overlap_counts)),
                            "max": int(max(overlap_counts)),
                            "mean": float(np.mean(overlap_counts)),
                        },
                    }
        finally:
            del model
            torch.cuda.empty_cache()
        (model_dir / "metadata.json").write_text(json.dumps(model_meta, indent=2) + "\n", encoding="utf-8")
    (args.out_root / "STATUS").write_text("PASS_EXTRACTION\n", encoding="utf-8")
    print(json.dumps({"status": "PASS_EXTRACTION", "records": dict(observed), "models": [mid for mid, _, _ in models]}, indent=2))


if __name__ == "__main__":
    main()
