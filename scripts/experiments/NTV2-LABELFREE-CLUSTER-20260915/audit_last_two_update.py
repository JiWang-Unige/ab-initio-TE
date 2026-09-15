#!/usr/bin/env python3
"""Audit that the saved last-two NTv2 encoder state differs from the base model.

This is a read-only post-run check.  It compares the saved layer-27/28 tensors
against the corresponding tensors in the native safetensors file.  It does not
retrain, score, or inspect family labels.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


LAYER_RE = re.compile(r"(?:^|\.)encoder\.layer\.(27|28)\.")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _state_mapping(state: Mapping[str, Any]) -> Mapping[str, Any]:
    value = state.get("encoder_last_two")
    if not isinstance(value, Mapping):
        raise ValueError("saved state has no encoder_last_two mapping")
    return value


def _key_candidates(key: str) -> Iterable[str]:
    """Yield common wrapper variants without guessing a different model."""

    seen = set()
    values = [key]
    for prefix in ("module.", "base_model.", "base_model.model.", "model."):
        if key.startswith(prefix):
            values.append(key[len(prefix):])
    if key.startswith("esm."):
        values.append(key[len("esm."):])
    else:
        values.append("esm." + key)
    for value in values:
        if value not in seen:
            seen.add(value)
            yield value


def _tensor_stats(updated: Any, base: Any) -> dict:
    import torch  # type: ignore

    if tuple(updated.shape) != tuple(base.shape):
        raise ValueError("shape mismatch: %s versus %s" % (tuple(updated.shape), tuple(base.shape)))
    updated_float = updated.detach().to(dtype=torch.float64, device="cpu")
    base_float = base.detach().to(dtype=torch.float64, device="cpu")
    difference = updated_float - base_float
    absolute = difference.abs()
    changed = int((absolute > 0).sum().item())
    return {
        "shape": list(updated.shape),
        "numel": int(updated.numel()),
        "changed_elements_exact": changed,
        "max_abs_difference": float(absolute.max().item()) if difference.numel() else 0.0,
        "mean_abs_difference": float(absolute.mean().item()) if difference.numel() else 0.0,
        "l2_difference": float(torch.linalg.vector_norm(difference).item()) if difference.numel() else 0.0,
        "base_l2": float(torch.linalg.vector_norm(base_float).item()) if base_float.numel() else 0.0,
    }


def audit(state_path: Path, model_dir: Path, output_path: Path) -> dict:
    import torch  # type: ignore
    from safetensors.torch import load_file  # type: ignore

    if model_dir.name != "nucleotide-transformer-v2-500m-multi-species":
        raise ValueError("refusing non-native model directory: %s" % model_dir)
    if not state_path.is_file() or not (model_dir / "model.safetensors").is_file():
        raise FileNotFoundError("saved state or native safetensors is missing")

    try:
        state = torch.load(str(state_path), map_location="cpu", weights_only=False)
    except TypeError:
        state = torch.load(str(state_path), map_location="cpu")
    if not isinstance(state, Mapping):
        raise ValueError("saved state is not a mapping")
    updated_state = _state_mapping(state)
    base_state = load_file(str(model_dir / "model.safetensors"), device="cpu")

    matched: List[Tuple[str, str]] = []
    unmatched: List[str] = []
    for key in sorted(updated_state):
        if not LAYER_RE.search(str(key)):
            continue
        resolved: Optional[str] = None
        for candidate in _key_candidates(str(key)):
            if candidate in base_state:
                resolved = candidate
                break
        if resolved is None:
            unmatched.append(str(key))
        else:
            matched.append((str(key), resolved))
    if not matched:
        raise ValueError("no layer-27/28 saved tensors matched the native model")

    per_layer: Dict[str, dict] = {}
    sample_stats: List[dict] = []
    total_numel = 0
    total_changed = 0
    global_max = 0.0
    global_l1 = 0.0
    global_l2_sq = 0.0
    changed_tensors = 0
    for saved_key, base_key in matched:
        stats = _tensor_stats(updated_state[saved_key], base_state[base_key])
        layer_match = LAYER_RE.search(saved_key)
        layer = layer_match.group(1) if layer_match else "unknown"
        layer_entry = per_layer.setdefault(layer, {"tensor_count": 0, "numel": 0, "changed_elements_exact": 0, "max_abs_difference": 0.0, "l2_difference_squared": 0.0})
        layer_entry["tensor_count"] += 1
        layer_entry["numel"] += stats["numel"]
        layer_entry["changed_elements_exact"] += stats["changed_elements_exact"]
        layer_entry["max_abs_difference"] = max(layer_entry["max_abs_difference"], stats["max_abs_difference"])
        layer_entry["l2_difference_squared"] += stats["l2_difference"] ** 2
        total_numel += stats["numel"]
        total_changed += stats["changed_elements_exact"]
        global_max = max(global_max, stats["max_abs_difference"])
        global_l1 += stats["mean_abs_difference"] * stats["numel"]
        global_l2_sq += stats["l2_difference"] ** 2
        if stats["changed_elements_exact"]:
            changed_tensors += 1
        # Keep three representative tensors per layer in the compact report.
        if sum(1 for item in sample_stats if item["layer"] == layer) < 3:
            sample_stats.append({"layer": layer, "saved_key": saved_key, "base_key": base_key, **stats})

    for layer_entry in per_layer.values():
        layer_entry["l2_difference"] = layer_entry.pop("l2_difference_squared") ** 0.5
    result = {
        "status": "PASS_NUMERIC_UPDATE_AUDIT" if total_changed else "FAIL_NO_NUMERIC_CHANGE",
        "scope": {
            "saved_state": str(state_path),
            "native_model_dir": str(model_dir),
            "compared_layers": [27, 28],
            "comparison": "saved encoder_last_two tensors versus native model.safetensors",
            "retraining": False,
            "family_labels_read": False,
        },
        "matching": {
            "saved_layer_tensor_count": len(matched) + len(unmatched),
            "matched_tensor_count": len(matched),
            "unmatched_tensor_count": len(unmatched),
            "unmatched_examples": unmatched[:10],
        },
        "aggregate": {
            "matched_numel": total_numel,
            "changed_tensors_exact": changed_tensors,
            "changed_elements_exact": total_changed,
            "max_abs_difference": global_max,
            "mean_abs_difference": global_l1 / float(total_numel) if total_numel else 0.0,
            "l2_difference": global_l2_sq ** 0.5,
        },
        "per_layer": per_layer,
        "representative_tensors": sample_stats,
        "torch_version": str(torch.__version__),
    }
    write_json(output_path, result)
    return result


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


if __name__ == "__main__":
    arguments = make_parser().parse_args()
    audit(arguments.state, arguments.model_dir, arguments.output)
