#!/usr/bin/env python3
"""Loader and encoder-inheritance smoke for the matched NTv2 class arm."""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
from pathlib import Path


def sequence_tokens(sequence: str, width: int = 6) -> list[str]:
    full_length = len(sequence) // width * width
    tokens = [sequence[start : start + width] for start in range(0, full_length, width)]
    tokens.extend(sequence[full_length:])
    return [token if set(token) <= {"A", "C", "G", "T"} else "<unk>" for token in tokens]


def load_native_class(init_checkpoint: Path, base_model: Path, num_labels: int):
    import torch
    from transformers import AutoConfig, AutoTokenizer
    from transformers.dynamic_module_utils import get_class_from_dynamic_module

    config = AutoConfig.from_pretrained(
        str(init_checkpoint), trust_remote_code=True, local_files_only=True
    )
    config.num_labels = num_labels
    config.id2label = {i: name for i, name in enumerate(
        ["BG", "SINE", "LINE", "LTR", "DNA", "KNOWN_OTHER_TE", "AMBIGUOUS_TE", "UNCLASSIFIED"]
    )}
    config.label2id = {name: i for i, name in config.id2label.items()}
    model_class = get_class_from_dynamic_module(
        config.auto_map["AutoModelForTokenClassification"],
        str(base_model),
        local_files_only=True,
    )
    model = model_class._from_config(config)
    state = torch.load(init_checkpoint / "pytorch_model.bin", map_location="cpu")
    head_keys = {"classifier.weight", "classifier.bias"}
    filtered = {key: value for key, value in state.items() if key not in head_keys}
    missing, unexpected = model.load_state_dict(filtered, strict=False)
    if set(missing) != head_keys or unexpected:
        raise RuntimeError(f"unexpected D->class state transfer: missing={missing}, unexpected={unexpected}")
    return model, config


def load_native_binary(init_checkpoint: Path, base_model: Path):
    import torch
    from transformers import AutoConfig
    from transformers.dynamic_module_utils import get_class_from_dynamic_module

    config = AutoConfig.from_pretrained(
        str(init_checkpoint), trust_remote_code=True, local_files_only=True
    )
    config.num_labels = 2
    model_class = get_class_from_dynamic_module(
        config.auto_map["AutoModelForTokenClassification"],
        str(base_model),
        local_files_only=True,
    )
    model = model_class._from_config(config)
    state = torch.load(init_checkpoint / "pytorch_model.bin", map_location="cpu")
    model.load_state_dict(state, strict=True)
    return model


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init-checkpoint", type=Path, required=True)
    ap.add_argument("--base-model", type=Path, required=True)
    ap.add_argument("--data-record", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    args = ap.parse_args()

    import numpy as np
    import torch
    from transformers import AutoTokenizer

    for path in (args.init_checkpoint, args.base_model, args.data_record):
        if not path.exists():
            raise FileNotFoundError(path)
    with gzip.open(args.data_record, "rt", encoding="utf-8") as handle:
        record = json.loads(next(line for line in handle if line.strip()))
    sequence = str(record["sequence"])
    if len(sequence) != 4096:
        raise ValueError(f"smoke record is not 4096 bp: {len(sequence)}")

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.base_model), trust_remote_code=True, local_files_only=True
    )
    tokens = sequence_tokens(sequence)
    encoded = tokenizer(
        tokens,
        is_split_into_words=True,
        truncation=True,
        max_length=((len(tokens) + 2 + 7) // 8) * 8,
        padding="max_length",
        return_tensors="pt",
    )
    content = encoded["attention_mask"].bool()
    for special_id in getattr(tokenizer, "all_special_ids", []):
        content &= encoded["input_ids"].ne(int(special_id))
    if int(content.sum()) != len(tokens):
        raise RuntimeError(f"token count mismatch: {int(content.sum())} != {len(tokens)}")

    binary = load_native_binary(args.init_checkpoint, args.base_model)
    class_model, class_config = load_native_class(args.init_checkpoint, args.base_model, 8)
    binary.eval()
    class_model.eval()
    with torch.inference_mode():
        binary_out = binary(**encoded, output_hidden_states=True)
        class_out = class_model(**encoded, output_hidden_states=True)
    binary_hidden = binary_out.hidden_states[-1]
    class_hidden = class_out.hidden_states[-1]
    max_hidden_delta = float(torch.max(torch.abs(binary_hidden - class_hidden)).item())
    logits = class_out.logits
    probs = torch.softmax(logits, dim=-1)
    material = probs[..., 1:].sum(dim=-1)
    if logits.shape[-1] != 8 or material.shape[-1] != logits.shape[-2]:
        raise RuntimeError(f"unexpected class output shape: logits={tuple(logits.shape)}")
    finite = bool(torch.isfinite(class_hidden).all() and torch.isfinite(material).all())
    result = {
        "status": "PASS_LOADER_SMOKE",
        "record": {key: record.get(key) for key in ("species_code", "assembly", "split", "chrom", "start", "end")},
        "sequence_bp": len(sequence),
        "native_token_count": len(tokens),
        "pooled_content_tokens": int(content.sum()),
        "binary_model_class": binary.__class__.__name__,
        "class_model_class": class_model.__class__.__name__,
        "class_num_labels": int(class_config.num_labels),
        "class_logits_shape": list(logits.shape),
        "binary_material_definition": "sum(softmax(class_logits)[...,1:])",
        "max_encoder_hidden_delta_D_vs_fresh_class_head": max_hidden_delta,
        "finite_outputs": finite,
        "head_transfer": "D encoder weights strict; classifier.weight/bias intentionally fresh native 8-class head",
    }
    if max_hidden_delta > 1e-4:
        raise RuntimeError(f"D encoder was not inherited exactly: max hidden delta={max_hidden_delta}")
    if not finite:
        raise RuntimeError("non-finite class smoke output")
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
