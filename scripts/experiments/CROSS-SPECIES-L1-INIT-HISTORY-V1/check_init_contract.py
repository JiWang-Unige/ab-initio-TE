#!/usr/bin/env python3
"""CPU-only J0 loading contract: exact sources, heads, RNG and bounded inputs."""
from __future__ import annotations

import argparse
import gc
import gzip
import json
import random
from pathlib import Path

import torch

import init_model
from train_init import legacy


def training_index(data_root, upstream_root):
    """Read TRAIN indexes and retain only the first tile's two halves/species."""
    indexes, examples, counts = {}, {}, {}
    for species in legacy.SPECIES:
        root = upstream_root if species == "c_elegans" else data_root
        path = Path(root) / "TRAIN" / f"{species}.jsonl.gz"
        halves, first = {}, {}
        with gzip.open(path, "rt") as handle:
            for line in handle:
                row = json.loads(line)
                if row["species_code"] != species or row["split"] != "TRAIN":
                    raise ValueError(f"unexpected TRAIN identity: {path}")
                tile = str(row["tile_id"])
                half = int(row["half"])
                if half in halves.setdefault(tile, set()):
                    raise ValueError(f"duplicate TRAIN half: {tile}/{half}")
                halves[tile].add(half)
                if tile == next(iter(halves)):
                    if len(row["sequence"]) != 4096 or len(row["labels"]) != 4096:
                        raise ValueError("bounded example is not a 4096-bp half")
                    first[half] = row
        expected = 3000 if species == "c_elegans" else 1500
        if len(halves) != expected or any(value != {0, 1} for value in halves.values()):
            raise ValueError(f"D materialization count/pair mismatch: {species}, {len(halves)}, expected {expected}")
        indexes[species] = list(halves)
        examples[species] = (first[0], first[1])
        counts[species] = {"tiles": len(halves), "path": str(path)}
    return indexes, examples, counts


def sampling_trace(indexes, seed, steps):
    sampler = legacy.SpeciesTileSampler(indexes, seed, "B1")
    return [sampler.next_step() for _ in range(steps)]


def check(args):
    if not 1 <= args.sample_steps <= 16:
        raise ValueError("CPU input smoke is bounded to 1-16 sampling steps")
    if any(seed not in {42, 17} for seed in args.seeds):
        raise ValueError("only registered seeds 42/17 are allowed")
    indexes, examples, counts = training_index(args.data_root, args.upstream_root)
    results = []
    # Sequential construction avoids retaining two 500M models in RAM.
    for seed in args.seeds:
        baseline_head, baseline_inputs, baseline_tokens, baseline_trace = None, None, None, None
        arms = {}
        for arm in ("H0R", "P0R"):
            random.seed(seed)
            torch.manual_seed(seed)
            python_rng, torch_rng = random.getstate(), torch.get_rng_state().clone()
            model, tokenizer, report = init_model.load_model_and_tokenizer(
                arm, seed, args.base_model, args.h0_checkpoint
            )
            if python_rng != random.getstate() or not torch.equal(torch_rng, torch.get_rng_state()):
                raise ValueError("construction changed subsequent training RNG")
            head = {key: value.detach().cpu().clone() for key, value in model.classifier.state_dict().items()}
            inputs = {species: legacy.encode_pair(tokenizer, pair) for species, pair in examples.items()}
            tokens = {"vocab": tokenizer.get_vocab(), "special_tokens_map": tokenizer.special_tokens_map}
            trace = sampling_trace(indexes, seed, args.sample_steps)
            if baseline_head is None:
                baseline_head, baseline_inputs, baseline_tokens, baseline_trace = head, inputs, tokens, trace
            else:
                if head.keys() != baseline_head.keys() or not all(torch.equal(head[k], baseline_head[k]) for k in head):
                    raise ValueError("paired fresh heads are not exactly equal")
                if tokens != baseline_tokens or trace != baseline_trace:
                    raise ValueError("paired tokenizer/sample stream differs")
                if not all(torch.equal(batch[k], baseline_inputs[species][k]) for species, batch in inputs.items() for k in batch):
                    raise ValueError("paired token IDs/masks/loss masses differ")
            for species, batch in inputs.items():
                if torch.any((3 * batch["positive_bp"] + batch["negative_bp"]).sum(dim=1) == 0):
                    raise ValueError(f"bounded TRAIN example has zero loss mass: {species}")
            report["construction_rng_direct_equality"] = True
            arms[arm] = report
            del model, tokenizer
            gc.collect()
        results.append({
            "seed": seed, "arms": arms,
            "fresh_head_direct_equality": True, "tokenizer_direct_equality": True,
            "input_ids_masks_loss_masses_direct_equality": True,
            "sampling_stream_direct_equality": True,
            "sampling_steps": args.sample_steps, "sampling_trace": baseline_trace,
            "bounded_input_tiles": {sp: str(pair[0]["tile_id"]) for sp, pair in examples.items()},
            "bounded_loss_masses": {sp: {
                "positive_bp": b["positive_bp"].sum(dim=1).tolist(),
                "negative_bp": b["negative_bp"].sum(dim=1).tolist(),
                "weighted_bp": (3 * b["positive_bp"] + b["negative_bp"]).sum(dim=1).tolist(),
            } for sp, b in baseline_inputs.items()},
        })
    return {
        "protocol": init_model.PROTOCOL, "status": "PASS",
        "role": "engineering_loading_contract", "scientific_evidence": False,
        "model_forward_performed": False, "training_sources": counts,
        "seed_contracts": results,
        "gpu_smoke_required_before_J1": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--base-model", type=Path, default=init_model.BASE_MODEL)
    parser.add_argument("--h0-checkpoint", type=Path, default=init_model.H0_CHECKPOINT)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 17])
    parser.add_argument("--sample-steps", type=int, default=4)
    args = parser.parse_args()
    if args.output_json.exists():
        raise FileExistsError(args.output_json)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = check(args)
    except Exception as exc:
        args.output_json.write_text(json.dumps({"protocol": init_model.PROTOCOL, "status": "BLOCKED", "error": str(exc)}, indent=2) + "\n")
        raise
    args.output_json.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "output": str(args.output_json)}))


if __name__ == "__main__":
    main()
