"""Check complete matched training artifacts before registered evaluation.

This does not replace Slurm completion evidence and does not authorize seed17.
It reads small logs/metadata only; checkpoint tensors are checked by eval loading.
"""
import argparse
import csv
import json
import math
from pathlib import Path

PROTOCOL = "CROSS-SPECIES-L1-PAIR-CONTEXT-V1"
SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
COUNTS = {s: 3000 if s == "c_elegans" else 1500 for s in SPECIES}


def check(root, arm, seed):
    metadata = json.loads((root / "training_meta.json").read_text())
    expected = {"protocol": PROTOCOL, "arm": arm, "seed": seed,
                "run_role": "pair_context_registered_training", "max_steps": 4000,
                "warmup_steps": 400, "learning_rate": 2e-5, "weight_decay": 0.01,
                "te_bp_weight": 3.0, "max_grad_norm": 1.0,
                "species": list(SPECIES), "tiles_per_species": COUNTS,
                "window_bp": 4096, "tiles_per_step": 6, "species_per_step": 6,
                "checkpoint_policy": "final-step-only"}
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"{arm}: unexpected {key}: {metadata.get(key)!r}")
    initialization = metadata["initialization"]
    if (initialization["head_source"] != "same complete H0 checkpoint; no reinitialization"
            or initialization["activation_checkpointing"] is not True):
        raise ValueError(f"{arm}: wrong initialization/memory strategy")
    rows = [json.loads(line) for line in (root / "train_log.jsonl").read_text().splitlines()]
    if len(rows) != 4000:
        raise ValueError(f"{arm}: incomplete training ({len(rows)} updates)")
    for index, row in enumerate(rows):
        if row["step"] != index + 1 or set(row["loss"]) != set(SPECIES):
            raise ValueError(f"{arm}: incorrect update/species at index {index}")
        if not all(math.isfinite(v) for v in row["loss"].values()):
            raise ValueError(f"{arm}: nonfinite loss at step {index + 1}")
        expected_lr = 2e-5 * (index / 400 if index < 400 else (4000 - index) / 3600)
        if not math.isclose(row["learning_rate"], expected_lr, rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError(f"{arm}: incorrect learning rate at step {index + 1}")
        for key in ("q_before", "q_after"):
            if set(row[key]) != set(SPECIES) or any(abs(v - 1 / 6) > 1e-12 for v in row[key].values()):
                raise ValueError(f"{arm}: nonuniform species weight at step {index + 1}")
    with (root / "exposure.tsv").open() as handle:
        exposure_rows = list(csv.DictReader(handle, delimiter="\t"))
    exposure = {r["species"]: {k: int(v) for k, v in r.items() if k != "species"} for r in exposure_rows}
    if len(exposure_rows) != 6 or set(exposure) != set(SPECIES):
        raise ValueError(f"{arm}: incomplete exposure table")
    for species, row in exposure.items():
        if row["presentations"] != 4000 or row["unique_tiles"] != COUNTS[species]:
            raise ValueError(f"{arm}: wrong exposure for {species}")
    config = json.loads((root / "final_model" / "config.json").read_text())
    for key, value in (("pair_context_arm", arm), ("pair_context_protocol", PROTOCOL),
                       ("pair_activation_checkpointing", True)):
        if config.get(key) != value:
            raise ValueError(f"{arm}: incorrect saved {key}")
    if not (root / "final_model" / "pytorch_model.bin").is_file():
        raise ValueError(f"{arm}: missing final weights")
    return metadata, exposure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block4-dir", type=Path, required=True)
    parser.add_argument("--pair8-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(42, 17), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    block, block_exposure = check(args.block4_dir, "BLOCK4", args.seed)
    pair, pair_exposure = check(args.pair8_dir, "PAIR8", args.seed)
    for key in ("data_root", "base_model", "initial_weights", "train_data_by_species", "loss", "label_mapping"):
        if block[key] != pair[key]:
            raise ValueError(f"unmatched training {key}")
    if block_exposure != pair_exposure:
        raise ValueError("two-arm exposure tables differ")
    result = {"protocol": PROTOCOL, "seed": args.seed, "status": "PASS",
              "steps_per_arm": 4000, "matched_exposure": block_exposure,
              "scope": "complete training artifacts; Slurm completion must be verified separately",
              "inputs": {"BLOCK4": str(args.block4_dir.resolve()), "PAIR8": str(args.pair8_dir.resolve())}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
