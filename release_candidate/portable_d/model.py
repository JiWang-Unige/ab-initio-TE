"""NTv2 D checkpoint loading and exact six-base inference semantics."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from .bundle import KMER_BP, WINDOW_BP, Bundle


def sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    out = np.empty_like(values)
    positive = values >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    out[~positive] = exp_values / (1.0 + exp_values)
    return out


def sequence_tokens(sequence: str) -> list[str]:
    """Tokenize exactly as the frozen D evaluator: six-mer blocks plus a tail."""
    full_length = len(sequence) // KMER_BP * KMER_BP
    tokens = [
        sequence[start : start + KMER_BP]
        for start in range(0, full_length, KMER_BP)
    ]
    tokens.extend(sequence[full_length:])
    return [
        token if set(token) <= {"A", "C", "G", "T"} else "<unk>"
        for token in tokens
    ]


def project_token_margins(
    token_margins: np.ndarray, token_positions: list[int], bp_length: int
) -> np.ndarray:
    """Expand token margins to base margins using the frozen D projection."""
    projected = np.empty(bp_length, dtype=np.float32)
    full_chunks, tail_bp = divmod(bp_length, KMER_BP)
    expected = full_chunks + tail_bp
    if len(token_positions) != expected:
        raise ValueError(f"expected {expected} sequence tokens, observed {len(token_positions)}")
    for chunk, token_position in enumerate(token_positions[:full_chunks]):
        start = chunk * KMER_BP
        projected[start : start + KMER_BP] = token_margins[token_position]
    tail_start = full_chunks * KMER_BP
    for offset, token_position in enumerate(token_positions[full_chunks:]):
        projected[tail_start + offset] = token_margins[token_position]
    return projected


def _load_model_code(code_dir: Path) -> tuple[type[Any], type[Any]]:
    """Load copied upstream model code without relying on the research repo."""
    init_path = code_dir / "__init__.py"
    if not init_path.is_file():
        raise FileNotFoundError(f"model code package is missing __init__.py: {code_dir}")
    package_name = "portable_d_model_code"
    package_spec = importlib.util.spec_from_file_location(
        package_name,
        init_path,
        submodule_search_locations=[str(code_dir)],
    )
    if package_spec is None or package_spec.loader is None:
        raise ImportError(f"cannot load model code package: {code_dir}")
    package = importlib.util.module_from_spec(package_spec)
    sys.modules[package_name] = package
    package_spec.loader.exec_module(package)
    config_module: ModuleType = importlib.import_module(f"{package_name}.esm_config")
    model_module: ModuleType = importlib.import_module(f"{package_name}.modeling_esm")
    return config_module.EsmConfig, model_module.EsmForTokenClassification


def _torch_load(path: Path):
    import torch

    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:  # torch versions before the weights_only argument
        return torch.load(path, map_location="cpu")


def resolve_device(requested: str):
    import torch

    if requested not in {"auto", "cpu", "cuda"}:
        raise ValueError(f"unsupported device: {requested}")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but CUDA is unavailable")
    return torch.device(
        "cuda" if requested == "cuda" or (requested == "auto" and torch.cuda.is_available()) else "cpu"
    )


def load_model_and_tokenizer(bundle: Bundle, device_request: str = "auto", cpu_threads: int = 0):
    """Load the D model from bundle-relative files and return model/tokenizer/device."""
    import torch
    from transformers import AutoTokenizer

    weights = bundle.model_dir / "pytorch_model.bin"
    if not weights.is_file():
        raise FileNotFoundError(
            f"D checkpoint weights are not included; place pytorch_model.bin at {weights}"
        )
    if cpu_threads > 0:
        torch.set_num_threads(cpu_threads)
    config_class, model_class = _load_model_code(bundle.model_code_dir)
    config = config_class.from_pretrained(str(bundle.model_dir), local_files_only=True)
    # Match the historical loader's construction path before the strict state
    # restore. `_from_config` also preserves Transformers' dtype/init context.
    model = model_class._from_config(config)
    state = _torch_load(weights)
    model.load_state_dict(state, strict=True)
    tokenizer = AutoTokenizer.from_pretrained(
        str(bundle.tokenizer_dir), trust_remote_code=True, local_files_only=True
    )
    device = resolve_device(device_request)
    model.to(device)
    model.eval()
    return model, tokenizer, device


def infer_half_margins(model, tokenizer, device, sequences: list[str], batch_size: int):
    """Return per-base TE-minus-background margins for 4096-bp windows."""
    import torch

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if any(len(sequence) > WINDOW_BP for sequence in sequences):
        raise ValueError("infer_half_margins accepts at most 4096 bp per sequence")
    max_length = ((WINDOW_BP + 5) // 6 + 2 + 7) // 8 * 8
    results: list[np.ndarray] = []
    for offset in range(0, len(sequences), batch_size):
        batch = sequences[offset : offset + batch_size]
        encoded = tokenizer(
            [sequence_tokens(sequence) for sequence in batch],
            is_split_into_words=True,
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_special_tokens_mask=True,
            return_tensors="pt",
        )
        special_tokens_mask = encoded.pop("special_tokens_mask").detach().cpu().numpy()
        attention_mask = encoded["attention_mask"].detach().cpu().numpy()
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
        margins = (logits[:, :, 1] - logits[:, :, 0]).detach().cpu().numpy()
        for sequence, token_margin, attention, special in zip(
            batch, margins, attention_mask, special_tokens_mask
        ):
            token_positions = [
                index
                for index, (attended, is_special) in enumerate(zip(attention, special))
                if attended and not is_special
            ]
            results.append(
                project_token_margins(token_margin, token_positions, len(sequence))
            )
    return results
