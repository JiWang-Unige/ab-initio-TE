#!/usr/bin/env python3
"""Compare the direct H0 checkpoint loader with the continuation loader."""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
from pathlib import Path


N_RECORDS = 16
MAX_LENGTH = 688
TOLERANCE = 1e-6


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_records(path: Path) -> list[dict]:
    records = []
    with gzip.open(path, "rt") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
            if len(records) == N_RECORDS:
                break
    if len(records) != N_RECORDS:
        raise ValueError(f"expected {N_RECORDS} Human CAL records, found {len(records)}")
    if any(
        record["species_code"] != "human"
        or record["split"] != "CAL"
        or len(record["sequence"]) != 4096
        for record in records
    ):
        raise ValueError("identity inputs must be 4096-bp Human CAL records")
    return records


def encode(tokenizer, sequences: list[str]):
    return tokenizer(
        sequences,
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
        return_special_tokens_mask=True,
        return_tensors="pt",
    )


def infer(model, encoded):
    import torch

    inputs = {
        "input_ids": encoded["input_ids"],
        "attention_mask": encoded["attention_mask"],
    }
    model.to("cpu").float().eval()
    with torch.no_grad():
        return model(**inputs).logits.detach().float().cpu()


def compare(
    reference_model,
    reference_tokenizer,
    candidate_model,
    candidate_tokenizer,
    records: list[dict],
    project_token_margins,
) -> dict:
    import numpy as np
    import torch

    sequences = [record["sequence"] for record in records]
    reference = encode(reference_tokenizer, sequences)
    candidate = encode(candidate_tokenizer, sequences)
    ids_equal = torch.equal(reference["input_ids"], candidate["input_ids"])
    attention_equal = torch.equal(
        reference["attention_mask"], candidate["attention_mask"]
    )
    special_equal = torch.equal(
        reference["special_tokens_mask"], candidate["special_tokens_mask"]
    )
    if not (ids_equal and attention_equal and special_equal):
        return {
            "status": "FAIL",
            "next_action": "repair loader",
            "records": len(records),
            "input_ids_exact_equal": ids_equal,
            "attention_mask_exact_equal": attention_equal,
            "special_tokens_mask_exact_equal": special_equal,
        }

    reference_logits = infer(reference_model, reference)
    candidate_logits = infer(candidate_model, candidate)
    if reference_logits.shape != candidate_logits.shape:
        raise ValueError(
            f"logit shape mismatch: {reference_logits.shape} != {candidate_logits.shape}"
        )
    logit_diff = float((reference_logits - candidate_logits).abs().max())
    reference_margin = reference_logits[:, :, 1] - reference_logits[:, :, 0]
    candidate_margin = candidate_logits[:, :, 1] - candidate_logits[:, :, 0]
    active = reference["attention_mask"].bool() & ~reference[
        "special_tokens_mask"
    ].bool()
    sign_mismatches = int(
        torch.count_nonzero(
            torch.sign(reference_margin[active]) != torch.sign(candidate_margin[active])
        )
    )
    bp_diff = 0.0
    compared_bp = 0
    for index, sequence in enumerate(sequences):
        positions = torch.nonzero(active[index], as_tuple=False).flatten().tolist()
        reference_bp = project_token_margins(
            reference_margin[index].numpy(), positions, len(sequence)
        )
        candidate_bp = project_token_margins(
            candidate_margin[index].numpy(), positions, len(sequence)
        )
        bp_diff = max(
            bp_diff,
            float(np.max(np.abs(reference_bp.astype(np.float64) - candidate_bp))),
        )
        compared_bp += len(sequence)

    passed = (
        logit_diff <= TOLERANCE
        and sign_mismatches == 0
        and bp_diff <= TOLERANCE
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "next_action": None if passed else "repair loader",
        "records": len(records),
        "input_ids_exact_equal": ids_equal,
        "attention_mask_exact_equal": attention_equal,
        "special_tokens_mask_exact_equal": special_equal,
        "logit_max_abs_diff": logit_diff,
        "token_margin_sign_mismatches": sign_mismatches,
        "bp_margin_max_abs_diff": bp_diff,
        "compared_bp": compared_bp,
        "tolerance": TOLERANCE,
    }


def run(cal_jsonl: Path) -> dict:
    import torch
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer

    task = load_module(
        Path(__file__).with_name("cross_species_token_task.py"), "cross_species_task"
    )
    evaluator = load_module(
        Path(__file__).with_name("calibrate_evaluate_x0.py"), "cross_species_eval"
    )
    reference_config = AutoConfig.from_pretrained(
        task.H0_CHECKPOINT, trust_remote_code=True, local_files_only=True
    )
    reference_state = torch.load(
        task.H0_CHECKPOINT / "pytorch_model.bin", map_location="cpu"
    )
    reference_model = AutoModelForTokenClassification.from_pretrained(
        task.BASE_MODEL,
        config=reference_config,
        state_dict=reference_state,
        trust_remote_code=True,
        local_files_only=True,
    )
    reference_tokenizer = AutoTokenizer.from_pretrained(
        task.BASE_MODEL, trust_remote_code=True, local_files_only=True
    )
    candidate_model, candidate_tokenizer = task.load_model_and_tokenizer()
    return compare(
        reference_model,
        reference_tokenizer,
        candidate_model,
        candidate_tokenizer,
        read_records(cal_jsonl),
        evaluator.project_token_margins,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cal-jsonl", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.cal_jsonl)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
