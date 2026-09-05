#!/usr/bin/env python3
"""Strict encoder-only initialization with a seed-matched fresh TE head."""
from __future__ import annotations

import contextlib
import json
import random
from pathlib import Path

import torch

PROTOCOL = "CROSS-SPECIES-L1-INIT-HISTORY-V1"
BASE_MODEL = Path("/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species")
H0_CHECKPOINT = Path("/home/users/j/jwang/ab-initio-TE/software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_ntv2_500m_H0_w4096_seed42/checkpoints/checkpoint-800")
HEAD_KEYS = {"classifier.weight", "classifier.bias"}
LM_HEAD_KEYS = {"lm_head.dense.weight", "lm_head.dense.bias", "lm_head.layer_norm.weight", "lm_head.layer_norm.bias", "lm_head.decoder.weight", "lm_head.bias"}
CONFIG_FIELDS = (
    "model_type", "vocab_size", "hidden_size", "num_hidden_layers",
    "num_attention_heads", "intermediate_size", "hidden_dropout_prob",
    "attention_probs_dropout_prob", "max_position_embeddings",
    "position_embedding_type", "layer_norm_eps", "emb_layer_norm_before",
    "token_dropout", "is_decoder", "add_cross_attention", "pad_token_id",
    "mask_token_id",
)


@contextlib.contextmanager
def preserve_rng():
    """Model construction cannot shift the training dropout or Python stream."""
    python_state = random.getstate()
    devices = list(range(torch.cuda.device_count())) if torch.cuda.is_initialized() else []
    try:
        with torch.random.fork_rng(devices=devices):
            yield
    finally:
        random.setstate(python_state)


def load_encoder_state(model, state, arm):
    """Partition every checkpoint key; fail on missing/unknown/shape mismatch."""
    if arm not in {"H0R", "P0R"}:
        raise ValueError(f"unsupported initialization arm: {arm}")
    target = model.state_dict()
    encoder_keys = {key for key in target if key.startswith("esm.")}
    if not encoder_keys or set(target) - encoder_keys != HEAD_KEYS:
        raise ValueError("target is not the registered ESM encoder + linear TE head")
    ignored = HEAD_KEYS if arm == "H0R" else LM_HEAD_KEYS
    expected = encoder_keys | ignored
    missing, unknown = expected - set(state), set(state) - expected
    if missing or unknown:
        raise ValueError(f"checkpoint key partition mismatch: missing={sorted(missing)}, unknown={sorted(unknown)}")
    encoder = {}
    for key in sorted(encoder_keys):
        if target[key].shape != state[key].shape or target[key].dtype != state[key].dtype:
            raise ValueError(f"encoder tensor shape/dtype mismatch: {key}")
        encoder[key.removeprefix("esm.")] = state[key]
    model.esm.load_state_dict(encoder, strict=True)
    actual = model.state_dict()
    if not all(torch.equal(actual[key], state[key]) for key in encoder_keys):
        raise ValueError("encoder source tensors differ after loading")
    return {
        "encoder_keys": sorted(encoder_keys),
        "reinitialized_target_keys": sorted(HEAD_KEYS),
        "unused_source_keys": sorted(ignored),
        "encoder_tensor_count": len(encoder_keys),
        "encoder_parameter_count": sum(p.numel() for p in model.esm.parameters()),
        "encoder_direct_tensor_equality": True,
        "unknown_missing_keys": [],
        "unknown_unused_keys": [],
    }


def reset_shared_head(model, seed):
    """Use the native ESM classifier initialization law, with a local seed."""
    if not isinstance(model.classifier, torch.nn.Linear):
        raise ValueError("registered classifier must be torch.nn.Linear")
    with preserve_rng():
        torch.random.default_generator.manual_seed(seed)
        torch.nn.init.normal_(model.classifier.weight, mean=0.0, std=model.config.initializer_range)
        torch.nn.init.zeros_(model.classifier.bias)


def compare_config(config, h0_checkpoint):
    path = Path(h0_checkpoint) / "config.json"
    if not path.is_file():
        raise ValueError(f"H0 architecture configuration missing: {path}")
    h0 = json.loads(path.read_text())
    differences = {
        key: {"native": getattr(config, key, None), "H0": h0[key]}
        for key in CONFIG_FIELDS
        if key in h0 and getattr(config, key, None) != h0[key]
    }
    if differences:
        raise ValueError(f"native/H0 architecture configuration differs: {differences}")
    return {key: getattr(config, key, None) for key in CONFIG_FIELDS}


def existing_download_revision(base_model, filename):
    path = Path(base_model) / ".cache" / "huggingface" / "download" / f"{filename}.metadata"
    if not path.is_file():
        return None
    lines = path.read_text().splitlines()
    return {"metadata_file": str(path), "revision": lines[0] if lines else None}


def load_model_and_tokenizer(arm, seed, base_model=BASE_MODEL, h0_checkpoint=H0_CHECKPOINT):
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer

    base_model, h0_checkpoint = Path(base_model).resolve(), Path(h0_checkpoint).resolve()
    source = (h0_checkpoint if arm == "H0R" else base_model) / "pytorch_model.bin"
    if arm not in {"H0R", "P0R"} or not source.is_file():
        raise ValueError(f"invalid arm/source: {arm}, {source}")
    with preserve_rng():
        config = AutoConfig.from_pretrained(base_model, trust_remote_code=True, local_files_only=True)
        architecture = compare_config(config, h0_checkpoint)
        config.num_labels = 2
        model = AutoModelForTokenClassification.from_config(config, trust_remote_code=True)
        state = torch.load(source, map_location="cpu")
        partition = load_encoder_state(model, state, arm)
        del state
        reset_shared_head(model, seed)
        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True, local_files_only=True)
    if any(not parameter.requires_grad for parameter in model.parameters()):
        raise ValueError("registered run requires full encoder and head fine-tuning")
    report = {
        "protocol": PROTOCOL, "arm": arm, "seed": seed,
        "base_model": str(base_model), "encoder_source": str(source),
        "config_source": str(base_model / "config.json"),
        "tokenizer_source": str(base_model), "architecture": architecture,
        "head_source": "fresh native-law linear classifier h(seed)",
        "head_seed": seed, "head_initializer_std": config.initializer_range,
        "rng_after_construction": "restored Python, torch CPU and initialized CUDA generators",
        "full_model_trainable": True,
        "existing_native_download_revisions": {
            filename: existing_download_revision(base_model, filename)
            for filename in ("config.json", "pytorch_model.bin")
        },
        "ancestry_status": "path provenance only; exact H0 ancestry unverified",
        "interpretation": "checkpoint initialization choice, not isolated Human history",
        **partition,
    }
    return model, tokenizer, report
