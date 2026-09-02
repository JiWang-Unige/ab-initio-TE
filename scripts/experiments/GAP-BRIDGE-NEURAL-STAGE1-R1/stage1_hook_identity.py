#!/usr/bin/env python3
"""Verify that the frozen P3 classifier-input hook leaves chr17 predictions unchanged."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
WINDOW = 8192
THRESHOLD = 0.5


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(
    model_dir: Path,
    data_jsonl: Path,
    expected_canonical: Path,
    expected_lengths_json: Path,
    output_dir: Path,
    max_windows: int,
) -> dict[str, object]:
    import torch

    output_dir.mkdir(parents=True, exist_ok=False)
    e0 = load_module(
        ROOT / "scripts/experiments/GAP-BRIDGE-PHASE0-R1/gap_bridge_e0.py",
        "gap_bridge_stage1_hook_e0",
    )
    c5 = load_module(
        ROOT / "scripts/experiments/C5-HYBRID-PILOT-20260830/c5_hybrid_pilot.py",
        "gap_bridge_stage1_hook_c5",
    )
    strict = c5._strict_module()
    model, tokenizer, metadata, device, _te = c5.load_p3_model(model_dir)
    width = int(metadata["width"])
    weights = strict.center_weights(WINDOW, "triangular")
    captured: dict[str, torch.Tensor] = {}
    hook_windows = 0
    latent_shape: list[int] | None = None
    classifier_shape: list[int] | None = None

    def capture_classifier(_module, inputs, output):
        captured["decoded"] = inputs[0]
        captured["classifier_output"] = output

    def infer(sequence: str) -> np.ndarray:
        nonlocal hook_windows, latent_shape, classifier_shape
        captured.clear()
        encoded = tokenizer(
            sequence[:WINDOW], add_special_tokens=False, truncation=True,
            max_length=WINDOW, padding="max_length", return_tensors="pt",
        )
        inputs = {
            key: value.to(device)
            for key, value in encoded.items()
            if key in {"input_ids", "attention_mask"}
        }
        with torch.no_grad():
            unhooked_logits = model(**inputs).logits
            handle = model.classifier.register_forward_hook(capture_classifier)
            try:
                logits = model(**inputs).logits
            finally:
                handle.remove()
            if not torch.equal(unhooked_logits, logits):
                raise RuntimeError("read-only hook changed frozen P3 logits")
            classifier_logits = captured["classifier_output"].transpose(1, 2)
            if not torch.equal(classifier_logits, logits):
                raise RuntimeError("classifier hook output disagrees with forward logits")
            decoded = captured["decoded"]
            if tuple(decoded.shape) != (1, width, WINDOW):
                raise RuntimeError(f"unexpected decoded hook shape: {tuple(decoded.shape)}")
            latent_shape = list(decoded.shape)
            classifier_shape = list(captured["classifier_output"].shape)
            hook_windows += 1
            state_probability = torch.softmax(logits, dim=-1)[0].cpu().numpy()
        return state_probability[:len(sequence)]

    seqid, region_start, _states, probability, known, windows = e0.stitch_track(
        e0.iter_jsonl(data_jsonl, max_windows), infer, weights,
    )

    prediction = (probability >= THRESHOLD) & known
    observed_canonical = output_dir / "observed.canonical.tsv"
    interval_count = e0.write_canonical(
        observed_canonical,
        seqid,
        ((start + region_start, end + region_start) for start, end in strict.runs_from_bool(prediction)),
    )
    expected_lengths = {
        str(key): int(value)
        for key, value in json.loads(expected_lengths_json.read_text(encoding="utf-8")).items()
    }
    identity = e0.identity_result(
        e0.canonical_tuples(expected_canonical),
        e0.canonical_tuples(observed_canonical),
        expected_lengths,
        seqid,
        int(probability.size),
    )
    status = "PASS" if identity["status"] == "PASS" and hook_windows == windows else "FAIL"
    result: dict[str, object] = {
        "schema": "gap_bridge_neural_stage1_hook_identity_v1",
        "status": status,
        "model_schema": metadata["schema"],
        "hook": "TEUNetSegmenter.classifier input",
        "hooked_vs_unhooked_logits_equal": True,
        "classifier_output_matches_forward_logits": True,
        "hook_windows": hook_windows,
        "inference_windows": windows,
        "decoded_shape": latent_shape,
        "classifier_output_shape": classifier_shape,
        "decoded_written_to_disk": False,
        "seqid": seqid,
        "region_start": region_start,
        "region_end": region_start + int(probability.size),
        "known_bp": int(known.sum()),
        "unknown_bp": int((~known).sum()),
        "prediction_intervals": interval_count,
        "canonical_identity": identity,
        "scientific_metrics_computed": False,
    }
    (output_dir / "hook_identity.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output_dir / "STATUS").write_text(status + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--data-jsonl", required=True, type=Path)
    parser.add_argument("--expected-canonical", required=True, type=Path)
    parser.add_argument("--expected-lengths-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-windows", type=int, default=1200)
    args = parser.parse_args()
    result = run(
        args.model_dir, args.data_jsonl, args.expected_canonical,
        args.expected_lengths_json, args.output_dir, args.max_windows,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
