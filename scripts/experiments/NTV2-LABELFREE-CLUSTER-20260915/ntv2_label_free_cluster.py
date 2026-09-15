#!/usr/bin/env python3
"""A bounded, family-label-free NTv2 representation experiment.

The input panel is a TE-enriched natural-copy panel.  Family labels are
retained in the manifest for *post hoc* clustering metrics only.  They never
enter the split assignment, view construction, SSL loss, model selection, or
the TRAIN-only choice of the cluster count.  The two SSL views are deterministic masked
versions of the same sequence and its reverse complement.

This file deliberately contains the small end-to-end runner instead of
depending on the older identity-retrieval modules.  That keeps the new
experiment's label-free contract auditable and prevents the old family
supervised projection from being silently reused.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


MODEL_ID = "nucleotide-transformer-v2-500m-multi-species"
CONTRACT_VERSION = "ntv2-label-free-cluster-v1"
DEFAULT_SEED = 42
DEFAULT_LOCUS_BLOCK_BP = 2_000_000
DEFAULT_MAX_TRAIN_VIEW_BP = 2_048
DEFAULT_MAX_TOKENS = 2_050
DEFAULT_K = 40
MASK_FRACTION = 0.05


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
    temporary.replace(path)


def load_natural_rows(path: Path) -> List[dict]:
    """Read only natural copies and fail closed on missing core identity."""

    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("source_kind") != "natural_copy":
                continue
            sequence = str(row.get("sequence", "")).upper()
            if not sequence:
                raise ValueError("natural copy has no inline sequence at line %d" % line_number)
            # The family field is retained in each row for the final external
            # score, but is deliberately not touched during input validation,
            # splitting, feature extraction, or training.
            for field in ("record_id", "host_id", "source_copy_id", "homology_component_id", "host_locus"):
                if not str(row.get(field, "")):
                    raise ValueError("natural copy missing %s at line %d" % (field, line_number))
            row = dict(row)
            row["sequence"] = sequence
            rows.append(row)
    if not rows:
        raise ValueError("no natural_copy rows in %s" % path)
    if len({row["record_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate natural-copy record_id")
    return rows


def load_query_record_ids(path: Path) -> List[str]:
    """Read record IDs from a prior query table, never its labels or scores."""

    ids: List[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            record_id = str(row.get("record_id", ""))
            if record_id:
                ids.append(record_id)
    return sorted(set(ids))


def interval_start(row: Mapping[str, Any]) -> int:
    """Extract the coordinate start from the audited interval record ID."""

    record_id = str(row.get("record_id", ""))
    parts = record_id.split("|")
    if len(parts) >= 5 and parts[0] == "interval":
        return int(parts[3])
    for field in ("start", "repeat_start", "begin"):
        if str(row.get(field, "")):
            return int(row[field])
    raise ValueError("cannot parse interval start for %s" % record_id)


class DisjointSet:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        parent = self.parent
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left = self.find(left)
        right = self.find(right)
        if left == right:
            return
        if self.rank[left] < self.rank[right]:
            left, right = right, left
        self.parent[right] = left
        if self.rank[left] == self.rank[right]:
            self.rank[left] += 1


def _connect_groups(dsu: DisjointSet, groups: Mapping[Any, Sequence[int]]) -> None:
    for members in groups.values():
        if not members:
            continue
        first = members[0]
        for member in members[1:]:
            dsu.union(first, member)


def build_isolated_split(
    rows: Sequence[Mapping[str, Any]],
    seed: int = DEFAULT_SEED,
    locus_block_bp: int = DEFAULT_LOCUS_BLOCK_BP,
) -> Tuple[List[dict], dict]:
    """Build a group/locus-isolated train/CAL/EVAL split without labels.

    Connected components join records sharing a host-scoped source copy,
    homology component, or host-locus block.  Components, rather than rows,
    are shuffled with a fixed seed and assigned a 6:2:2 role pattern.  The
    family field is used only for a support audit returned after assignment;
    it is never consulted by the role assignment.
    """

    if locus_block_bp <= 0:
        raise ValueError("locus_block_bp must be positive")
    dsu = DisjointSet(len(rows))
    by_copy: Dict[Tuple[str, str], List[int]] = collections.defaultdict(list)
    by_homology: Dict[str, List[int]] = collections.defaultdict(list)
    by_block: Dict[Tuple[str, str, int], List[int]] = collections.defaultdict(list)
    row_blocks: List[str] = []
    for index, row in enumerate(rows):
        host = str(row["host_id"])
        copy_id = str(row["source_copy_id"])
        by_copy[(host, copy_id)].append(index)
        homology = str(row.get("homology_component_id", ""))
        if homology:
            by_homology[homology].append(index)
        block_number = interval_start(row) // locus_block_bp
        block_key = (host, str(row["host_locus"]), block_number)
        by_block[block_key].append(index)
        row_blocks.append("%s:%s:%d" % block_key)
    _connect_groups(dsu, by_copy)
    _connect_groups(dsu, by_homology)
    _connect_groups(dsu, by_block)

    components: Dict[int, List[int]] = collections.defaultdict(list)
    for index in range(len(rows)):
        components[dsu.find(index)].append(index)
    component_records: List[Tuple[str, List[int]]] = []
    for members in components.values():
        signature = "|".join(sorted({row_blocks[index] for index in members}))
        component_records.append((signature, sorted(members)))
    component_records.sort(key=lambda item: item[0])
    shuffled = list(component_records)
    random.Random(seed).shuffle(shuffled)
    role_pattern = (["train"] * 6) + (["cal"] * 2) + (["eval"] * 2)
    assignments: Dict[int, str] = {}
    component_ids: Dict[int, str] = {}
    for component_number, (signature, members) in enumerate(shuffled):
        role = role_pattern[component_number % len(role_pattern)]
        component_id = "locus_component_%04d" % component_number
        for index in members:
            assignments[index] = role
            component_ids[index] = component_id

    split_rows: List[dict] = []
    for index, row in enumerate(rows):
        new_row = dict(row)
        new_row["split"] = assignments[index]
        new_row["label_free_component_id"] = component_ids[index]
        new_row["label_free_locus_block"] = row_blocks[index]
        split_rows.append(new_row)

    def cross_split(field: str, scoped: bool = False) -> List[str]:
        memberships: Dict[str, set] = collections.defaultdict(set)
        for row in split_rows:
            key = str(row[field])
            if scoped:
                key = "%s::%s" % (row["host_id"], key)
            memberships[key].add(row["split"])
        return sorted(key for key, values in memberships.items() if len(values) > 1)

    audit = {
        "contract_version": CONTRACT_VERSION,
        "seed": seed,
        "locus_block_bp": locus_block_bp,
        "assignment": "component_shuffle_6_train_2_cal_2_eval",
        "family_labels_used_for_assignment": False,
        "records": len(split_rows),
        "components": len(component_records),
        "rows_by_split": dict(sorted(collections.Counter(row["split"] for row in split_rows).items())),
        "components_by_split": dict(sorted(collections.Counter(assignments[index] for index in assignments).items())),
        "cross_split_source_copy": {"count": len(cross_split("source_copy_id", scoped=True)), "examples": cross_split("source_copy_id", scoped=True)[:10]},
        "cross_split_homology_component": {"count": len(cross_split("homology_component_id")), "examples": cross_split("homology_component_id")[:10]},
        "cross_split_locus_block": {"count": len(cross_split("label_free_locus_block")), "examples": cross_split("label_free_locus_block")[:10]},
        "family_support_external_audit": None,
        "families_in_all_splits": None,
        "family_labels_read_for_assignment_or_split_audit": False,
        "no_species_holdout": True,
        "host_is_context_not_split_unit": True,
    }
    if any(audit[key]["count"] for key in ("cross_split_source_copy", "cross_split_homology_component", "cross_split_locus_block")):
        raise ValueError("split leakage detected: %s" % json.dumps(audit, sort_keys=True))
    return split_rows, audit


def exclude_prior_query_neighborhood(
    rows: Sequence[Mapping[str, Any]],
    prior_query_ids: Sequence[str],
    locus_block_bp: int,
) -> Tuple[List[dict], dict]:
    """Remove prior query records and their homology/locus neighborhoods.

    Only identifiers and coordinates are used.  Prior family labels and model
    scores are intentionally ignored.  This keeps a new evaluation away from
    the already viewed development panel while retaining enough natural
    copies for a fresh train/CAL/EVAL split.
    """

    prior_ids = set(str(value) for value in prior_query_ids)
    prior_rows = [row for row in rows if str(row["record_id"]) in prior_ids]

    def block_key(row: Mapping[str, Any]) -> str:
        return "%s:%s:%d" % (
            row["host_id"],
            row["host_locus"],
            interval_start(row) // locus_block_bp,
        )

    prior_homology = {str(row["homology_component_id"]) for row in prior_rows if str(row.get("homology_component_id", ""))}
    prior_blocks = {block_key(row) for row in prior_rows}
    kept: List[dict] = []
    excluded_by_id = 0
    excluded_by_homology = 0
    excluded_by_block = 0
    for row in rows:
        record_id = str(row["record_id"])
        block = block_key(row)
        if record_id in prior_ids:
            excluded_by_id += 1
            continue
        if str(row["homology_component_id"]) in prior_homology:
            excluded_by_homology += 1
            continue
        if block in prior_blocks:
            excluded_by_block += 1
            continue
        kept.append(dict(row))
    audit = {
        "prior_query_id_count": len(prior_ids),
        "prior_query_rows_found": len(prior_rows),
        "prior_homology_component_count": len(prior_homology),
        "prior_locus_block_count": len(prior_blocks),
        "excluded_by_record_id": excluded_by_id,
        "excluded_by_homology_component_after_id": excluded_by_homology,
        "excluded_by_locus_block_after_id_and_homology": excluded_by_block,
        "kept_records": len(kept),
        "prior_query_labels_or_scores_read": False,
    }
    return kept, audit


def reverse_complement(sequence: str) -> str:
    table = str.maketrans("ACGTN", "TGCAN")
    return sequence.translate(table)[::-1]


def center_crop(sequence: str, max_bp: int) -> str:
    if max_bp <= 0:
        raise ValueError("max_bp must be positive")
    if len(sequence) <= max_bp:
        return sequence
    start = (len(sequence) - max_bp) // 2
    return sequence[start:start + max_bp]


def sanitize_sequence(sequence: str) -> str:
    return "".join(base if base in "ACGTN" else "N" for base in sequence.upper())


def _mask_sequence(sequence: str, rng: random.Random, fraction: float = MASK_FRACTION) -> str:
    chars = list(sequence)
    eligible = [index for index, base in enumerate(chars) if base in "ACGT"]
    if eligible and fraction > 0:
        count = max(1, int(round(len(chars) * fraction)))
        count = min(count, len(eligible))
        for index in rng.sample(eligible, count):
            chars[index] = "N"
    return "".join(chars)


def make_label_free_views(sequence: str, record_index: int, seed: int = DEFAULT_SEED) -> Tuple[str, str]:
    """Create two deterministic views of one sequence; no family input."""

    sequence = sanitize_sequence(sequence)
    first_rng = random.Random(seed * 1_000_003 + record_index * 2 + 1)
    second_rng = random.Random(seed * 1_000_003 + record_index * 2 + 2)
    view_one = _mask_sequence(sequence, first_rng)
    view_two = _mask_sequence(reverse_complement(sequence), second_rng)
    return view_one, view_two


def kmer_vector(sequence: str, k: int = 6) -> List[float]:
    """Return a normalized A/C/G/T k-mer vector; ambiguous windows are ignored."""

    if k <= 0:
        raise ValueError("k must be positive")
    dimension = 4 ** k
    counts = [0.0] * dimension
    sequence = sanitize_sequence(sequence)
    total = 0
    base_index = {"A": 0, "C": 1, "G": 2, "T": 3}
    for start in range(0, max(0, len(sequence) - k + 1)):
        value = 0
        valid = True
        for base in sequence[start:start + k]:
            if base not in base_index:
                valid = False
                break
            value = value * 4 + base_index[base]
        if valid:
            counts[value] += 1.0
            total += 1
    if total:
        counts = [value / float(total) for value in counts]
    return counts


def mlp_parameter_count(input_dim: int, hidden_dim: int, output_dim: int) -> int:
    return (input_dim * hidden_dim + hidden_dim) + (hidden_dim * output_dim + output_dim)


def nt_xent_positive_indices(batch_size: int) -> List[int]:
    if batch_size < 2:
        raise ValueError("contrastive batch must contain at least two records")
    return list(range(batch_size, 2 * batch_size)) + list(range(0, batch_size))


def _import_numeric_runtime():
    import numpy as np  # type: ignore
    import torch  # type: ignore
    return np, torch


def _token_ids(tokenizer: Any, sequence: str, max_tokens: int) -> List[List[int]]:
    encoded = tokenizer(sequence, add_special_tokens=False, truncation=False)
    content = encoded["input_ids"]
    if hasattr(content, "tolist"):
        content = content.tolist()
    if content and isinstance(content[0], list):
        content = content[0]
    content_ids = [int(value) for value in content]
    special_count = len(tokenizer.build_inputs_with_special_tokens([]))
    budget = max_tokens - special_count
    if budget < 1:
        raise ValueError("native tokenizer special-token budget is invalid")
    if not content_ids:
        return [[]]
    return [content_ids[start:start + budget] for start in range(0, len(content_ids), budget)]


def _base_model(model: Any) -> Any:
    if hasattr(model, "esm"):
        return model.esm
    if hasattr(model, "base_model"):
        return model.base_model
    raise AttributeError("native model has no ESM base model")


def _pool_hidden(hidden: Any, input_ids: Any, attention_mask: Any, special_ids: Sequence[int]) -> Any:
    token_mask = attention_mask.to(dtype=bool)
    for special_id in special_ids:
        token_mask = token_mask & input_ids.ne(int(special_id))
    counts = token_mask.sum(dim=1)
    if bool((counts <= 0).any()):
        raise ValueError("a tokenized view has no non-special content tokens")
    pooled = (hidden * token_mask.unsqueeze(-1).to(dtype=hidden.dtype)).sum(dim=1)
    return pooled / counts.unsqueeze(-1).to(dtype=hidden.dtype)


def embed_sequences(
    sequences: Sequence[str],
    tokenizer: Any,
    model: Any,
    device: Any,
    batch_size: int,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    requires_grad: bool = False,
) -> Any:
    """Mean-pool native hidden states and preserve gradients when requested."""

    np, torch = _import_numeric_runtime()
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    base = _base_model(model)
    special_ids = [int(value) for value in getattr(tokenizer, "all_special_ids", [])]
    segment_ids: List[List[int]] = []
    segment_record: List[int] = []
    record_segments: List[List[int]] = [[] for _ in sequences]
    for record_index, sequence in enumerate(sequences):
        parts = _token_ids(tokenizer, sanitize_sequence(sequence), max_tokens)
        for part in parts:
            segment_index = len(segment_ids)
            segment_ids.append(part)
            segment_record.append(record_index)
            record_segments[record_index].append(segment_index)
    segment_vectors: List[Any] = []
    segment_weights: List[int] = []
    if not segment_ids:
        raise ValueError("no tokenized segments")
    base.eval() if not requires_grad else base.train()
    context = torch.enable_grad() if requires_grad else torch.inference_mode()
    with context:
        for start in range(0, len(segment_ids), batch_size):
            current = segment_ids[start:start + batch_size]
            full_ids = [tokenizer.build_inputs_with_special_tokens(part) for part in current]
            encoded = tokenizer.pad({"input_ids": full_ids}, padding=True, return_tensors="pt")
            inputs = {key: value.to(device) for key, value in encoded.items() if key in {"input_ids", "attention_mask"}}
            outputs = base(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                output_hidden_states=False,
                return_dict=True,
            )
            hidden = outputs.last_hidden_state
            pooled = _pool_hidden(hidden, inputs["input_ids"], inputs["attention_mask"], special_ids)
            counts = inputs["attention_mask"].to(dtype=bool)
            for special_id in special_ids:
                counts = counts & inputs["input_ids"].ne(int(special_id))
            segment_weights.extend(int(value) for value in counts.sum(dim=1).detach().cpu().tolist())
            if requires_grad:
                segment_vectors.extend([value for value in pooled])
            else:
                segment_vectors.extend(pooled.detach().float().cpu().numpy())
    record_vectors: List[Any] = []
    for indices in record_segments:
        if requires_grad:
            total = float(sum(segment_weights[index] for index in indices))
            value = sum((segment_vectors[index] * segment_weights[index] for index in indices)) / total
            record_vectors.append(value)
        else:
            value = sum((segment_vectors[index] * segment_weights[index] for index in indices)) / float(sum(segment_weights[index] for index in indices))
            record_vectors.append(value)
    if requires_grad:
        return torch.stack(record_vectors, dim=0)
    matrix = np.asarray(record_vectors, dtype=np.float32)
    if not np.isfinite(matrix).all():
        raise ValueError("native embeddings contain non-finite values")
    return matrix


def _make_mlp(torch: Any, input_dim: int, hidden_dim: int, output_dim: int) -> Any:
    import torch.nn as nn  # type: ignore

    class Projection(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, output_dim),
            )

        def forward(self, value: Any) -> Any:
            return nn.functional.normalize(self.net(value), dim=-1)

    return Projection()


def _contrastive_loss(torch: Any, first: Any, second: Any, temperature: float) -> Any:
    import torch.nn.functional as F  # type: ignore

    if first.shape[0] < 2:
        raise ValueError("contrastive batch must contain at least two records")
    z = F.normalize(torch.cat([first, second], dim=0), dim=-1)
    logits = torch.matmul(z, z.T) / float(temperature)
    diagonal = torch.eye(logits.shape[0], dtype=torch.bool, device=logits.device)
    logits = logits.masked_fill(diagonal, float("-inf"))
    targets = torch.as_tensor(nt_xent_positive_indices(first.shape[0]), device=logits.device)
    return F.cross_entropy(logits, targets)


def _batch_indices(n: int, batch_size: int, update: int, order: List[int]) -> List[int]:
    if n < 2:
        raise ValueError("need at least two training records")
    start = (update * batch_size) % n
    selected = [order[(start + offset) % n] for offset in range(batch_size)]
    return selected


def train_head(
    name: str,
    first: Any,
    second: Any,
    input_dim: int,
    hidden_dim: int,
    output_dim: int,
    device: Any,
    seed: int,
    max_updates: int,
    batch_size: int,
    temperature: float,
    learning_rate: float,
    weight_decay: float,
) -> Tuple[Any, List[dict], dict]:
    """Train an SSL projection from precomputed label-free view features."""

    np, torch = _import_numeric_runtime()
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    head = _make_mlp(torch, input_dim, hidden_dim, output_dim).to(device)
    optimizer = torch.optim.AdamW(head.parameters(), lr=learning_rate, weight_decay=weight_decay)
    n = int(first.shape[0])
    if n != int(second.shape[0]) or int(first.shape[1]) != input_dim:
        raise ValueError("view feature shape mismatch for %s" % name)
    if batch_size > n:
        batch_size = n
    if batch_size < 2:
        raise ValueError("batch size must be at least two")
    order = list(range(n))
    random.Random(seed + 901).shuffle(order)
    trace: List[dict] = []
    for update in range(max_updates):
        if update and update % max(1, n // batch_size) == 0:
            random.Random(seed + 901 + update).shuffle(order)
        indices = _batch_indices(n, batch_size, update, order)
        x1 = torch.as_tensor(np.asarray(first[indices], dtype=np.float32), device=device)
        x2 = torch.as_tensor(np.asarray(second[indices], dtype=np.float32), device=device)
        optimizer.zero_grad(set_to_none=True)
        z1 = head(x1)
        z2 = head(x2)
        loss = _contrastive_loss(torch, z1, z2, temperature)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(head.parameters(), 1.0)
        optimizer.step()
        if update == 0 or (update + 1) % 50 == 0 or update + 1 == max_updates:
            trace.append({"update": update + 1, "loss": float(loss.detach().cpu())})
    return head, trace, {
        "name": name,
        "input_dim": input_dim,
        "hidden_dim": hidden_dim,
        "output_dim": output_dim,
        "trainable_parameters": mlp_parameter_count(input_dim, hidden_dim, output_dim),
        "max_updates": max_updates,
        "batch_size": batch_size,
        "temperature": temperature,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "objective": "same_record_masked_reverse_complement_nt_xent",
        "family_labels_in_loss": False,
    }


def _encoder_layers(model: Any) -> Sequence[Any]:
    base = _base_model(model)
    encoder = getattr(base, "encoder", None)
    layers = getattr(encoder, "layer", None)
    if layers is None or len(layers) < 2:
        raise ValueError("native model does not expose at least two encoder layers")
    return layers


def freeze_all_but_last_two(model: Any) -> dict:
    for parameter in model.parameters():
        parameter.requires_grad = False
    layers = _encoder_layers(model)
    for layer in layers[-2:]:
        for parameter in layer.parameters():
            parameter.requires_grad = True
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    return {
        "total_encoder_layers": len(layers),
        "trainable_encoder_layers": [len(layers) - 2, len(layers) - 1],
        "trainable_backbone_parameters": int(sum(parameter.numel() for parameter in trainable)),
    }


def train_last_two(
    sequences_one: Sequence[str],
    sequences_two: Sequence[str],
    model: Any,
    tokenizer: Any,
    device: Any,
    seed: int,
    max_updates: int,
    batch_size: int,
    temperature: float,
    encoder_learning_rate: float,
    head_learning_rate: float,
    weight_decay: float,
    max_tokens: int,
) -> Tuple[Any, Any, List[dict], dict]:
    """Train the final two native NTv2 blocks with a label-free SSL loss."""

    np, torch = _import_numeric_runtime()
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    backbone_audit = freeze_all_but_last_two(model)
    head = _make_mlp(torch, 1024, 256, 128).to(device)
    encoder_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(
        [
            {"params": encoder_parameters, "lr": encoder_learning_rate},
            {"params": list(head.parameters()), "lr": head_learning_rate},
        ],
        weight_decay=weight_decay,
    )
    n = len(sequences_one)
    if n != len(sequences_two) or n < 2:
        raise ValueError("last-two SSL sequence views are misaligned")
    batch_size = min(batch_size, n)
    order = list(range(n))
    random.Random(seed + 1701).shuffle(order)
    trace: List[dict] = []
    use_amp = bool(torch.cuda.is_available())
    for update in range(max_updates):
        if update and update % max(1, n // batch_size) == 0:
            random.Random(seed + 1701 + update).shuffle(order)
        indices = _batch_indices(n, batch_size, update, order)
        batch_one = [sequences_one[index] for index in indices]
        batch_two = [sequences_two[index] for index in indices]
        optimizer.zero_grad(set_to_none=True)
        if use_amp:
            autocast = torch.autocast(device_type="cuda", dtype=torch.bfloat16)
        else:
            autocast = torch.autocast(device_type="cpu", enabled=False)
        with autocast:
            embeddings_one = embed_sequences(batch_one, tokenizer, model, device, batch_size, max_tokens, requires_grad=True)
            embeddings_two = embed_sequences(batch_two, tokenizer, model, device, batch_size, max_tokens, requires_grad=True)
            z1 = head(embeddings_one.float())
            z2 = head(embeddings_two.float())
            loss = _contrastive_loss(torch, z1, z2, temperature)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(encoder_parameters + list(head.parameters()), 1.0)
        optimizer.step()
        if update == 0 or (update + 1) % 50 == 0 or update + 1 == max_updates:
            trace.append({"update": update + 1, "loss": float(loss.detach().cpu())})
    return model, head, trace, {
        "name": "last_two_ntv2_ssl",
        "input_dim": 1024,
        "hidden_dim": 256,
        "output_dim": 128,
        "projection_trainable_parameters": mlp_parameter_count(1024, 256, 128),
        "max_updates": max_updates,
        "batch_size": batch_size,
        "temperature": temperature,
        "encoder_learning_rate": encoder_learning_rate,
        "head_learning_rate": head_learning_rate,
        "weight_decay": weight_decay,
        "objective": "same_record_masked_reverse_complement_nt_xent",
        "family_labels_in_loss": False,
        "backbone_updated": True,
        "backbone_update_scope": "last_two_encoder_blocks_only",
        **backbone_audit,
    }


def _standardize_train_eval(train_value: Any, eval_value: Any) -> Tuple[Any, Any]:
    np, _ = _import_numeric_runtime()
    mean = np.asarray(train_value, dtype=np.float64).mean(axis=0)
    scale = np.asarray(train_value, dtype=np.float64).std(axis=0)
    scale[scale < 1e-8] = 1.0
    return ((np.asarray(train_value, dtype=np.float64) - mean) / scale).astype(np.float32), ((np.asarray(eval_value, dtype=np.float64) - mean) / scale).astype(np.float32)


def _purity(labels_true: Any, labels_pred: Any) -> float:
    np, _ = _import_numeric_runtime()
    by_cluster: Dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    for true_value, predicted_value in zip(labels_true.tolist(), labels_pred.tolist()):
        by_cluster[int(predicted_value)][int(true_value)] += 1
    correct = sum(max(counter.values()) for counter in by_cluster.values())
    return float(correct) / float(len(labels_true)) if len(labels_true) else 0.0


def _fallback_kmeans_fit(value: Any, n_clusters: int, seed: int, max_iter: int = 100) -> Tuple[Any, Any]:
    np, _ = _import_numeric_runtime()
    if len(value) < n_clusters:
        raise ValueError("evaluation rows fewer than fixed K")
    rng = np.random.default_rng(seed)
    centers = value[rng.choice(len(value), n_clusters, replace=False)].copy()
    labels = np.zeros(len(value), dtype=np.int64)
    for _ in range(max_iter):
        distances = ((value[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = distances.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for cluster in range(n_clusters):
            if np.any(labels == cluster):
                centers[cluster] = value[labels == cluster].mean(axis=0)
    return centers, labels


def _fallback_kmeans_predict(value: Any, centers: Any) -> Any:
    return ((value[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)


def _cluster_metrics(train_value: Any, eval_value: Any, labels: Sequence[int], k: int, seed: int) -> dict:
    np, _ = _import_numeric_runtime()
    train_std, eval_std = _standardize_train_eval(train_value, eval_value)
    true_labels = np.asarray(labels, dtype=np.int64)
    try:
        from sklearn.cluster import KMeans  # type: ignore
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score  # type: ignore

        transductive_pred = KMeans(n_clusters=k, n_init=20, random_state=seed, algorithm="lloyd").fit_predict(eval_std)
        inductive_model = KMeans(n_clusters=k, n_init=20, random_state=seed, algorithm="lloyd").fit(train_std)
        inductive_pred = inductive_model.predict(eval_std)
        silhouette = float(silhouette_score(eval_std, transductive_pred)) if len(set(transductive_pred.tolist())) > 1 else float("nan")
        metric_fn = {
            "ari": lambda pred: float(adjusted_rand_score(true_labels, pred)),
            "nmi": lambda pred: float(normalized_mutual_info_score(true_labels, pred)),
        }
        result = {
            "transductive_eval_kmeans": {
                "ari": metric_fn["ari"](transductive_pred),
                "nmi": metric_fn["nmi"](transductive_pred),
                "purity": _purity(true_labels, transductive_pred),
                "silhouette": silhouette,
            },
            "inductive_train_kmeans": {
                "ari": metric_fn["ari"](inductive_pred),
                "nmi": metric_fn["nmi"](inductive_pred),
                "purity": _purity(true_labels, inductive_pred),
                "silhouette": float("nan"),
            },
            "sklearn": True,
        }
    except Exception as exc:
        eval_centers, transductive_pred = _fallback_kmeans_fit(eval_std, k, seed)
        train_centers, _ = _fallback_kmeans_fit(train_std, k, seed)
        inductive_pred = _fallback_kmeans_predict(eval_std, train_centers)
        result = {
            "transductive_eval_kmeans": {
                "ari": None,
                "nmi": None,
                "purity": _purity(true_labels, transductive_pred),
                "silhouette": None,
            },
            "inductive_train_kmeans": {
                "ari": None,
                "nmi": None,
                "purity": _purity(true_labels, inductive_pred),
                "silhouette": None,
            },
            "sklearn": False,
            "sklearn_error": type(exc).__name__ + ": " + str(exc),
        }
    result.update({
        "n_eval": int(len(eval_std)),
        "n_train": int(len(train_std)),
        "k_used": int(k),
        "k_selected_using_family_labels": False,
        "labels_used_only_for_metrics": True,
    })
    return result


def select_k_from_train(train_value: Any, candidates: Sequence[int], seed: int) -> Tuple[int, List[dict]]:
    """Select one K from TRAIN features and silhouette only, without labels."""

    np, _ = _import_numeric_runtime()
    train_std, _ = _standardize_train_eval(train_value, train_value)
    valid = sorted({int(value) for value in candidates if 2 <= int(value) < len(train_std)})
    if not valid:
        raise ValueError("no valid label-free K candidates")
    try:
        from sklearn.cluster import KMeans  # type: ignore
        from sklearn.metrics import silhouette_score  # type: ignore
    except Exception as exc:
        raise RuntimeError("label-free K selection requires sklearn") from exc
    scores: List[dict] = []
    for candidate in valid:
        model = KMeans(n_clusters=candidate, n_init=20, random_state=seed, algorithm="lloyd")
        prediction = model.fit_predict(train_std)
        score = float(silhouette_score(train_std, prediction)) if len(set(prediction.tolist())) > 1 else float("-inf")
        scores.append({"k": candidate, "train_silhouette": score})
    winner = max(scores, key=lambda item: (item["train_silhouette"], -item["k"]))
    return int(winner["k"]), scores


def _load_native_model(model_dir: Path, device: Any) -> Tuple[Any, Any, dict]:
    if model_dir.name != MODEL_ID:
        raise ValueError("refusing non-native model directory: %s" % model_dir)
    config_path = model_dir / "config.json"
    vocab_path = model_dir / "vocab.txt"
    weight_path = model_dir / "model.safetensors"
    if not config_path.is_file() or not vocab_path.is_file() or not weight_path.is_file():
        raise FileNotFoundError("native model files are incomplete: %s" % model_dir)
    import torch  # type: ignore
    from transformers import AutoModelForMaskedLM, AutoTokenizer  # type: ignore

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True, local_files_only=True)
    model = AutoModelForMaskedLM.from_pretrained(str(model_dir), trust_remote_code=True, local_files_only=True)
    model.to(device)
    model.eval()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return tokenizer, model, {
        "model_id": MODEL_ID,
        "config_hidden_size": int(config.get("hidden_size", 0)),
        "config_layers": int(config.get("num_hidden_layers", 0)),
        "config_max_position_embeddings": int(config.get("max_position_embeddings", 0)),
        "model_path": str(model_dir),
        "weights": str(weight_path),
        "device": str(device),
        "torch_version": str(torch.__version__),
    }


def _save_state(path: Path, value: Any) -> None:
    _, torch = _import_numeric_runtime()
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(value, str(path))


def run(args: argparse.Namespace) -> dict:
    np, torch = _import_numeric_runtime()
    if not torch.cuda.is_available() and not args.allow_cpu:
        raise RuntimeError("GPU is required for this experiment; pass --allow-cpu only for a bounded diagnostic")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_rows = load_natural_rows(Path(args.manifest))
    exclusion_audit = {
        "enabled": False,
        "prior_query_record_ids_read": False,
        "prior_query_labels_or_scores_read": False,
    }
    rows = all_rows
    if args.exclude_query_tsv is not None:
        prior_ids = load_query_record_ids(Path(args.exclude_query_tsv))
        rows, exclusion_audit = exclude_prior_query_neighborhood(rows, prior_ids, args.locus_block_bp)
        exclusion_audit["enabled"] = True
        exclusion_audit["source_tsv"] = str(args.exclude_query_tsv)
    split_rows, split_audit = build_isolated_split(rows, args.seed, args.locus_block_bp)
    split_audit["prior_query_exclusion"] = exclusion_audit
    write_jsonl(out_dir / "split_manifest.jsonl", split_rows)
    write_json(out_dir / "split_audit.json", split_audit)
    roles = [str(row["split"]) for row in split_rows]
    indices = {role: [index for index, value in enumerate(roles) if value == role] for role in ("train", "cal", "eval")}
    if len(indices["train"]) < args.batch_size or len(indices["eval"]) < 2:
        raise ValueError("split is too small for batch/clustering: %s" % {key: len(value) for key, value in indices.items()})

    tokenizer, model, model_info = _load_native_model(Path(args.model_dir), device)
    sequences = [sanitize_sequence(str(row["sequence"])) for row in split_rows]
    training_sequences = [center_crop(sequence, args.max_train_view_bp) for sequence in sequences]
    view_sequences = [make_label_free_views(sequence, index, args.seed) for index, sequence in enumerate(training_sequences)]
    view_one_sequences = [pair[0] for pair in view_sequences]
    view_two_sequences = [pair[1] for pair in view_sequences]

    # Base representations and all frozen view features are computed before
    # any backbone update.  They contain no labels and are retained remotely.
    base_original = embed_sequences(sequences, tokenizer, model, device, args.embedding_batch_size, args.max_tokens, requires_grad=False)
    base_view_one = embed_sequences(view_one_sequences, tokenizer, model, device, args.embedding_batch_size, args.max_tokens, requires_grad=False)
    base_view_two = embed_sequences(view_two_sequences, tokenizer, model, device, args.embedding_batch_size, args.max_tokens, requires_grad=False)
    kmer_original = np.asarray([kmer_vector(sequence, args.kmer_length) for sequence in sequences], dtype=np.float32)
    kmer_view_one = np.asarray([kmer_vector(sequence, args.kmer_length) for sequence in view_one_sequences], dtype=np.float32)
    kmer_view_two = np.asarray([kmer_vector(sequence, args.kmer_length) for sequence in view_two_sequences], dtype=np.float32)
    np.savez_compressed(out_dir / "label_free_feature_cache.npz", base_original=base_original, base_view_one=base_view_one, base_view_two=base_view_two, kmer_original=kmer_original, kmer_view_one=kmer_view_one, kmer_view_two=kmer_view_two)

    train_idx = np.asarray(indices["train"], dtype=np.int64)
    eval_idx = np.asarray(indices["eval"], dtype=np.int64)
    candidate_values = [int(value.strip()) for value in str(args.k_grid).split(",") if value.strip()]
    if args.fixed_k is not None:
        selected_k = int(args.fixed_k)
        k_grid = [{"k": selected_k, "selection": "fixed_override"}]
        k_selection_mode = "fixed_override_for_exploratory_run"
    else:
        selected_k, k_grid = select_k_from_train(base_original[train_idx], candidate_values, args.seed)
        k_selection_mode = "train_only_silhouette"
    if selected_k < 2 or selected_k >= len(eval_idx):
        raise ValueError("selected K is incompatible with split sizes: K=%d sizes=%s" % (selected_k, {key: len(value) for key, value in indices.items()}))
    k_selection = {
        "mode": k_selection_mode,
        "selected_k": int(selected_k),
        "candidate_grid": k_grid,
        "selection_features": "raw_frozen_ntv2_original_train_only",
        "selection_labels_read": False,
        "selection_split": "train",
        "seed": int(args.seed),
        "family_labels_used": False,
    }
    write_json(out_dir / "k_selection.json", k_selection)

    arm_representations: Dict[str, Tuple[Any, dict]] = {}
    traces: Dict[str, List[dict]] = {}

    arm_representations["raw_6mer"] = (kmer_original, {
        "kind": "raw_sequence_composition",
        "dimension": int(kmer_original.shape[1]),
        "training_updates": 0,
        "family_labels_in_training": False,
    })
    arm_representations["raw_frozen_ntv2"] = (base_original, {
        "kind": "native_ntv2_mean_pooled_hidden",
        "dimension": int(base_original.shape[1]),
        "backbone_frozen": True,
        "training_updates": 0,
        "family_labels_in_training": False,
    })

    def train_cached_head(name: str, first_cache: Any, second_cache: Any, original_cache: Any, input_dim: int, hidden_dim: int) -> None:
        head, trace, info = train_head(name, first_cache[train_idx], second_cache[train_idx], input_dim, hidden_dim, 128, device, args.seed, args.max_updates, args.batch_size, args.temperature, args.head_learning_rate, args.weight_decay)
        traces[name] = trace
        with torch.inference_mode():
            projected = head(torch.as_tensor(np.asarray(original_cache, dtype=np.float32), device=device)).detach().float().cpu().numpy()
        arm_representations[name] = (projected, info)
        _save_state(out_dir / (name + "_projection.pt"), head.state_dict())

    train_cached_head("kmer_ssl_head", kmer_view_one, kmer_view_two, kmer_original, int(kmer_view_one.shape[1]), args.kmer_head_hidden)
    train_cached_head("frozen_ntv2_ssl_head", base_view_one, base_view_two, base_original, int(base_view_one.shape[1]), args.ntv2_head_hidden)
    train_cached_head("frozen_ntv2_capacity_matched_head", base_view_one, base_view_two, base_original, int(base_view_one.shape[1]), args.capacity_head_hidden)

    # Update the real NTv2 encoder's final two blocks.  This is intentionally
    # after all frozen arms so their cached representations remain identical.
    model, last_two_head, last_two_trace, last_two_info = train_last_two(
        [view_one_sequences[index] for index in train_idx.tolist()],
        [view_two_sequences[index] for index in train_idx.tolist()],
        model,
        tokenizer,
        device,
        args.seed,
        args.max_updates,
        args.batch_size,
        args.temperature,
        args.encoder_learning_rate,
        args.head_learning_rate,
        args.weight_decay,
        args.max_tokens,
    )
    traces["last_two_ntv2_ssl"] = last_two_trace
    final_tuned_original = embed_sequences(sequences, tokenizer, model, device, args.embedding_batch_size, args.max_tokens, requires_grad=False)
    with torch.inference_mode():
        projected_tuned = last_two_head(torch.as_tensor(np.asarray(final_tuned_original, dtype=np.float32), device=device)).detach().float().cpu().numpy()
    arm_representations["last_two_ntv2_ssl"] = (projected_tuned, last_two_info)
    _save_state(out_dir / "last_two_ntv2_ssl_state.pt", {
        "encoder_last_two": {name: value.detach().cpu() for name, value in model.state_dict().items() if any(token in name for token in ("encoder.layer.27", "encoder.layer.28"))},
        "projection": last_two_head.state_dict(),
    })

    # Family identities are loaded only after all label-free training and K
    # selection have completed.  They are external scoring labels, never
    # inputs to the split, views, objective, or model selection.
    eval_family_labels = [str(split_rows[index]["family_id"]) for index in eval_idx.tolist()]
    family_names = sorted(set(eval_family_labels))
    family_to_int = {family: index for index, family in enumerate(family_names)}
    external_labels = np.asarray([family_to_int[family] for family in eval_family_labels], dtype=np.int64)
    family_support: Dict[str, Dict[str, int]] = {}
    by_family: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in split_rows:
        by_family[str(row["family_id"])][str(row["split"])] += 1
    for family in sorted(by_family):
        family_support[family] = {role: int(by_family[family].get(role, 0)) for role in ("train", "cal", "eval")}
    families_in_all_splits = sum(
        1 for support in family_support.values() if all(support[role] > 0 for role in ("train", "cal", "eval"))
    )
    arm_metrics: Dict[str, dict] = {}
    for name, (representation, arm_info) in arm_representations.items():
        arm_metrics[name] = {
            "representation": arm_info,
            "clustering": _cluster_metrics(representation[train_idx], representation[eval_idx], external_labels, selected_k, args.seed),
        }

    write_json(out_dir / "training_trace.json", traces)
    write_json(out_dir / "metrics.json", {
        "contract_version": CONTRACT_VERSION,
        "status": "PASS_NUMERIC_EXPLORATORY" if arm_metrics else "NOTRUN_NO_ARMS",
        "scientific_claim_status": "EXPLORATORY_LABEL_FREE_OBJECTIVE_WITH_EXTERNAL_CLUSTERING_LABELS",
        "input": {
            "manifest": str(args.manifest),
            "source_kind": "natural_copy",
            "records_before_prior_query_exclusion": len(all_rows),
            "records": len(split_rows),
            "train_records": len(indices["train"]),
            "cal_records": len(indices["cal"]),
            "eval_records": len(indices["eval"]),
            "eval_families": len(family_names),
            "te_enriched_family_label_free_training_input": True,
            "family_labels_used_for_training_or_selection": False,
            "old_query_record_ids_read_for_exclusion": bool(args.exclude_query_tsv is not None),
            "old_query_labels_or_scores_read": False,
            "prior_query_exclusion": exclusion_audit,
        },
        "model": model_info,
        "split_audit": split_audit,
        "views": {
            "view_one": "masked_original",
            "view_two": "masked_reverse_complement",
            "mask_fraction": MASK_FRACTION,
            "max_train_view_bp": args.max_train_view_bp,
            "same_record_positive_only": True,
            "family_labels_in_views": False,
        },
        "training": {
            "seed": args.seed,
            "max_updates_per_trained_arm": args.max_updates,
            "batch_size": args.batch_size,
            "temperature": args.temperature,
            "head_learning_rate": args.head_learning_rate,
            "encoder_learning_rate": args.encoder_learning_rate,
            "weight_decay": args.weight_decay,
            "family_labels_in_ssl_loss": False,
            "calibration_or_epoch_selection": "none_fixed_final_updates",
        },
        "capacity": {
            "kmer_head": mlp_parameter_count(4096, args.kmer_head_hidden, 128),
            "ntv2_standard_head": mlp_parameter_count(1024, args.ntv2_head_hidden, 128),
            "ntv2_capacity_matched_head": mlp_parameter_count(1024, args.capacity_head_hidden, 128),
            "kmer_head_hidden": args.kmer_head_hidden,
            "ntv2_head_hidden": args.ntv2_head_hidden,
            "capacity_head_hidden": args.capacity_head_hidden,
        },
        "k_selection": k_selection,
        "posthoc_family_support": {
            "family_names_seen_in_eval": family_names,
            "family_support_by_split": family_support,
            "families_in_all_splits": int(families_in_all_splits),
            "labels_loaded_after_all_label_free_training": True,
        },
        "arms": arm_metrics,
        "label_use_audit": {
            "family_field_loaded_only_for_posthoc_eval": True,
            "family_labels_in_split_assignment": False,
            "family_labels_in_view_generation": False,
            "family_labels_in_ssl_loss": False,
            "family_labels_in_update_or_epoch_selection": False,
            "k_used": int(selected_k),
            "k_selection_mode": k_selection_mode,
            "k_grid": k_grid,
            "k_selection_labels_read": False,
            "k_selected_using_family_labels": False,
        },
        "provenance_limits": [
            "TE annotation was used to select the natural-copy input panel; training is family-label-free conditional on this TE-enriched input.",
            "EVAL family labels are external scoring labels, not a self-supervised training signal.",
            "This is exploratory and single-seed; it does not establish broad species generalization or biological insertion recovery.",
        ],
    })
    write_json(out_dir / "status.json", {
        "status": "PASS_NUMERIC_EXPLORATORY",
        "job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "finished_unix": time.time(),
        "arms": sorted(arm_metrics),
        "family_labels_in_ssl_loss": False,
        "backbone_updated": bool(last_two_info.get("backbone_updated")),
    })
    return arm_metrics


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--locus-block-bp", type=int, default=DEFAULT_LOCUS_BLOCK_BP)
    parser.add_argument("--exclude-query-tsv", type=Path, default=None)
    parser.add_argument("--max-train-view-bp", type=int, default=DEFAULT_MAX_TRAIN_VIEW_BP)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--embedding-batch-size", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-updates", type=int, default=2000)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--head-learning-rate", type=float, default=1e-3)
    parser.add_argument("--encoder-learning-rate", type=float, default=1e-5)
    parser.add_argument("--weight-decay", type=float, default=1e-2)
    parser.add_argument("--kmer-length", type=int, default=6)
    parser.add_argument("--fixed-k", type=int, default=None)
    parser.add_argument("--k-grid", default="20,30,40,50")
    parser.add_argument("--kmer-head-hidden", type=int, default=256)
    parser.add_argument("--ntv2-head-hidden", type=int, default=256)
    parser.add_argument("--capacity-head-hidden", type=int, default=938)
    parser.add_argument("--allow-cpu", action="store_true")
    return parser


if __name__ == "__main__":
    arguments = make_parser().parse_args()
    run(arguments)
