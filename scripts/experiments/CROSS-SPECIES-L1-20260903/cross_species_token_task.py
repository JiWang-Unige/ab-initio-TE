#!/usr/bin/env python3
"""Frozen B1/B2/H1 cross-species NTv2 training pilot."""

from __future__ import annotations

import argparse
import gzip
import json
import math
import random
from pathlib import Path

import torch
import torch.nn.functional as F


SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
BASE_MODEL = Path(
    "/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/"
    "nucleotide-transformer-v2-500m-multi-species"
)
H0_CHECKPOINT = Path(
    "/home/users/j/jwang/ab-initio-TE/software_outputs/tefm_supp/"
    "PIPE-TEFM-SUPP-20260617/runs/TFSUPP_ntv2_500m_H0_w4096_seed42/"
    "checkpoints/checkpoint-800"
)
WINDOW_BP = 4096
KMER_BP = 6
MAX_STEPS = 2000
WARMUP_STEPS = 200
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 0.01
TE_BP_WEIGHT = 3.0
MAX_GRAD_NORM = 1.0
GROUPDRO_ETA = 0.01


class SpeciesTileDataset:
    """In-memory index of the two 4096-bp halves for each 8192-bp tile."""

    def __init__(self, path: Path, species: str):
        tiles: dict[str, dict[int, dict]] = {}
        with gzip.open(path, "rt") as handle:
            for line in handle:
                record = json.loads(line)
                if record["species_code"] != species or record["split"] != "TRAIN":
                    raise ValueError(f"unexpected record identity in {path}")
                if len(record["sequence"]) != WINDOW_BP or len(record["labels"]) != WINDOW_BP:
                    raise ValueError(f"non-{WINDOW_BP} record in {path}")
                half = int(record["half"])
                tile_id = str(record["tile_id"])
                tile = tiles.setdefault(tile_id, {})
                if half in tile:
                    raise ValueError(f"duplicate half {half} for {tile_id}")
                tile[half] = record
        for tile_id, halves in tiles.items():
            if set(halves) != {0, 1}:
                raise ValueError(f"tile {tile_id} does not contain halves 0 and 1")
        self.tiles = tiles
        self.tile_ids = list(tiles)

    def pair(self, tile_id: str) -> tuple[dict, dict]:
        halves = self.tiles[tile_id]
        return halves[0], halves[1]


class SpeciesTileSampler:
    """Draw one tile per species, or six Human tiles for H1, per optimizer step."""

    def __init__(self, tile_ids: dict[str, list[str]], seed: int, arm: str = "B1"):
        self.arm = arm
        self.active_species = ("human",) if arm == "H1" else SPECIES
        self.orders = {
            species: list(tile_ids[species]) for species in self.active_species
        }
        self.positions = {species: 0 for species in self.active_species}
        self.random = {
            species: random.Random(seed + index)
            for index, species in enumerate(self.active_species)
        }
        for species in self.active_species:
            self.random[species].shuffle(self.orders[species])

    def next_step(self) -> list[tuple[str, str]]:
        selected = []
        species_order = ("human",) * len(SPECIES) if self.arm == "H1" else SPECIES
        for species in species_order:
            if self.positions[species] == len(self.orders[species]):
                self.random[species].shuffle(self.orders[species])
                self.positions[species] = 0
            position = self.positions[species]
            selected.append((species, self.orders[species][position]))
            self.positions[species] = position + 1
        return selected


def label_chunk_masses(labels: str, width: int = KMER_BP) -> tuple[list[int], list[int]]:
    positive = []
    negative = []
    full_length = len(labels) // width * width
    for start in range(0, full_length, width):
        chunk = labels[start : start + width]
        positive.append(chunk.count("1"))
        negative.append(chunk.count("0") + chunk.count("H"))
    for symbol in labels[full_length:]:
        positive.append(symbol == "1")
        negative.append(symbol in {"0", "H"})
    return positive, negative


def sequence_tokens(sequence: str, width: int = KMER_BP) -> list[str]:
    full_length = len(sequence) // width * width
    tokens = [
        sequence[start : start + width] for start in range(0, full_length, width)
    ]
    tokens.extend(sequence[full_length:])
    return [
        token if set(token) <= {"A", "C", "G", "T"} else "<unk>"
        for token in tokens
    ]


def encode_record(tokenizer, record: dict) -> dict[str, torch.Tensor]:
    sequence = record["sequence"]
    positive, negative = label_chunk_masses(record["labels"])
    tokens = sequence_tokens(sequence)
    tensor_tokens = ((len(positive) + 2 + 7) // 8) * 8
    encoded = tokenizer(
        tokens,
        is_split_into_words=True,
        truncation=True,
        max_length=tensor_tokens,
        padding="max_length",
        return_special_tokens_mask=True,
    )
    token_positions = [
        index
        for index, (attention, special) in enumerate(
            zip(encoded["attention_mask"], encoded["special_tokens_mask"])
        )
        if attention and not special
    ]
    if len(token_positions) != len(positive):
        raise ValueError("NTv2 token count does not match 6-bp chunks")
    positive_bp = torch.zeros(tensor_tokens, dtype=torch.float32)
    negative_bp = torch.zeros(tensor_tokens, dtype=torch.float32)
    positive_bp[token_positions] = torch.tensor(positive, dtype=torch.float32)
    negative_bp[token_positions] = torch.tensor(negative, dtype=torch.float32)
    return {
        "input_ids": torch.tensor(encoded["input_ids"], dtype=torch.long),
        "attention_mask": torch.tensor(encoded["attention_mask"], dtype=torch.long),
        "positive_bp": positive_bp,
        "negative_bp": negative_bp,
    }


def encode_pair(tokenizer, records: tuple[dict, dict]) -> dict[str, torch.Tensor]:
    halves = [encode_record(tokenizer, record) for record in records]
    return {
        key: torch.stack([half[key] for half in halves])
        for key in halves[0]
    }


def bp_weighted_pair_loss(
    logits: torch.Tensor,
    positive_bp: torch.Tensor,
    negative_bp: torch.Tensor,
    te_bp_weight: float = TE_BP_WEIGHT,
) -> torch.Tensor:
    """Average two independently callable-bp-normalized half losses."""

    log_probability = F.log_softmax(logits.float(), dim=-1)
    numerator = -(
        negative_bp * log_probability[..., 0]
        + te_bp_weight * positive_bp * log_probability[..., 1]
    ).sum(dim=1)
    weighted_bp = (te_bp_weight * positive_bp + negative_bp).sum(dim=1)
    if torch.any(weighted_bp == 0):
        raise ValueError("a 4096-bp half has no callable bases")
    return (numerator / weighted_bp).mean()


def arm_weights(arm: str, log_q: torch.Tensor) -> torch.Tensor:
    if arm in {"B1", "H1"}:
        return torch.full_like(log_q, 1.0 / len(SPECIES))
    return torch.exp(log_q)


def update_groupdro_log_q(
    log_q: torch.Tensor,
    losses: torch.Tensor,
    eta: float = GROUPDRO_ETA,
) -> torch.Tensor:
    updated = log_q + eta * losses.detach().to(dtype=torch.float64, device="cpu")
    return updated - torch.logsumexp(updated, dim=0)


def load_model_and_tokenizer():
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer

    config = AutoConfig.from_pretrained(
        BASE_MODEL, trust_remote_code=True, local_files_only=True
    )
    config.num_labels = 2
    model = AutoModelForTokenClassification.from_config(config, trust_remote_code=True)
    state = torch.load(H0_CHECKPOINT / "pytorch_model.bin", map_location="cpu")
    model.load_state_dict(state, strict=True)
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, trust_remote_code=True, local_files_only=True
    )
    return model, tokenizer


def build_optimizer(model):
    from transformers.pytorch_utils import ALL_LAYERNORM_LAYERS
    from transformers.trainer_pt_utils import get_parameter_names

    decay_names = set(get_parameter_names(model, ALL_LAYERNORM_LAYERS))
    decay_names = {name for name in decay_names if "bias" not in name}
    parameters = dict(model.named_parameters())
    groups = [
        {
            "params": [
                parameter
                for name, parameter in parameters.items()
                if name in decay_names and parameter.requires_grad
            ],
            "weight_decay": WEIGHT_DECAY,
        },
        {
            "params": [
                parameter
                for name, parameter in parameters.items()
                if name not in decay_names and parameter.requires_grad
            ],
            "weight_decay": 0.0,
        },
    ]
    return torch.optim.AdamW(groups, lr=LEARNING_RATE)


def train(args) -> None:
    from transformers import get_linear_schedule_with_warmup

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    datasets = {
        species: SpeciesTileDataset(
            Path(args.data_root) / "TRAIN" / f"{species}.jsonl.gz", species
        )
        for species in SPECIES
    }
    sampler = SpeciesTileSampler(
        {species: dataset.tile_ids for species, dataset in datasets.items()},
        args.seed,
        args.arm,
    )
    model, tokenizer = load_model_and_tokenizer()
    model.config.use_cache = False
    device = torch.device("cuda")
    model.to(device)
    model.train()
    optimizer = build_optimizer(model)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=args.warmup_steps,
        num_training_steps=args.max_steps,
    )
    log_q = torch.full(
        (len(SPECIES),), -math.log(len(SPECIES)), dtype=torch.float64
    )
    step_keys = (
        [f"human_pair_{index}" for index in range(len(SPECIES))]
        if args.arm == "H1"
        else list(SPECIES)
    )

    metadata = {
        "arm": args.arm,
        "run_role": (
            "frozen_training"
            if (args.max_steps, args.warmup_steps) == (MAX_STEPS, WARMUP_STEPS)
            else "engineering_throughput_smoke"
        ),
        "seed": args.seed,
        "species": ["human"] if args.arm == "H1" else list(SPECIES),
        "tiles_per_species": {
            species: len(datasets[species].tile_ids)
            for species in (("human",) if args.arm == "H1" else SPECIES)
        },
        "data_root": str(Path(args.data_root)),
        "base_model": str(BASE_MODEL),
        "initial_weights": str(H0_CHECKPOINT / "pytorch_model.bin"),
        "window_bp": WINDOW_BP,
        "model_windows_per_species_per_step": (
            2 * len(SPECIES) if args.arm == "H1" else 2
        ),
        "species_per_step": 1 if args.arm == "H1" else len(SPECIES),
        "tiles_per_step": len(SPECIES),
        "training_sampling": (
            "six Human TRAIN tiles per step"
            if args.arm == "H1"
            else "one TRAIN tile per species per step"
        ),
        "max_steps": args.max_steps,
        "warmup_steps": args.warmup_steps,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "te_bp_weight": TE_BP_WEIGHT,
        "max_grad_norm": MAX_GRAD_NORM,
        "groupdro_eta": GROUPDRO_ETA if args.arm == "B2" else None,
        "groupdro_smoothing": None,
        "loss": "per-token P/N bp mass; per-half class-weighted-mass normalization; pair mean",
        "label_mapping": {"1": "P", "0": "N", "?": "ignore", "H": "N"},
        "checkpoint_policy": "final-step-only",
    }
    (output_dir / "training_meta.json").write_text(json.dumps(metadata, indent=2) + "\n")

    optimizer.zero_grad(set_to_none=True)
    with (output_dir / "train_log.jsonl").open("w", buffering=1) as log_handle:
        for step in range(1, args.max_steps + 1):
            q_before = arm_weights(args.arm, log_q)
            raw_losses = []
            learning_rate = optimizer.param_groups[0]["lr"]
            sampled_tiles = sampler.next_step()
            for species_index, (species, tile_id) in enumerate(sampled_tiles):
                batch = encode_pair(tokenizer, datasets[species].pair(tile_id))
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                positive_bp = batch["positive_bp"].to(device)
                negative_bp = batch["negative_bp"].to(device)
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    logits = model(
                        input_ids=input_ids, attention_mask=attention_mask
                    ).logits
                    raw_loss = bp_weighted_pair_loss(
                        logits, positive_bp, negative_bp
                    )
                    weighted_loss = raw_loss * float(q_before[species_index])
                weighted_loss.backward()
                raw_losses.append(float(raw_loss.detach()))

            torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            if args.arm == "B2":
                log_q = update_groupdro_log_q(
                    log_q, torch.tensor(raw_losses, dtype=torch.float64)
                )
            q_after = arm_weights(args.arm, log_q)
            log_handle.write(
                json.dumps(
                    {
                        "step": step,
                        "learning_rate": learning_rate,
                        "loss": dict(zip(step_keys, raw_losses)),
                        "q_before": dict(zip(step_keys, q_before.tolist())),
                        "q_after": dict(zip(step_keys, q_after.tolist())),
                    }
                )
                + "\n"
            )

    final_model = output_dir / "final_model"
    model.save_pretrained(final_model, safe_serialization=False)
    tokenizer.save_pretrained(final_model)
    (output_dir / "q.json").write_text(
        json.dumps(
            {
                "arm": args.arm,
                "eta": GROUPDRO_ETA if args.arm == "B2" else None,
                "log_q": dict(zip(step_keys, log_q.tolist())),
                "q": dict(zip(step_keys, arm_weights(args.arm, log_q).tolist())),
            },
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--arm", choices=("B1", "B2", "H1"), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS)
    parser.add_argument("--warmup-steps", type=int, default=WARMUP_STEPS)
    train(parser.parse_args())


if __name__ == "__main__":
    main()
