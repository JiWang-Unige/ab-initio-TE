#!/usr/bin/env python3
"""Score all label-blind chr13 candidates with the frozen Stage 1 heads."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SEQID = "chr13"
ROLES = ("DEV", "CAL_FIT", "CAL_GATE")
SEEDS = (17, 42, 20260902)
WINDOW = 8192
BATCH_SIZE = 512


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage1_train = _load_module(
    Path(__file__).with_name("stage1_train.py"), "gap_bridge_stage1_score_train",
)


HEAD_COLUMNS = tuple(
    f"{arm}__seed{seed}__raw_risk_logit"
    for arm in ("G_GEOMETRY_LOGITS", "R_RAW_LOCAL", "H_P3_LATENT")
    for seed in SEEDS
)
HEAD_FILENAMES = tuple(column.removesuffix("__raw_risk_logit") + ".pt" for column in HEAD_COLUMNS)

MANIFEST_FIELDS = (
    "candidate_id", "seqid", "role", "chr13_block_index",
    "left_run_start", "left_run_end", "gap_start", "gap_end",
    "right_run_start", "right_run_end", "crop_start", "crop_end",
    "gap_length", "length_stratum",
)


@dataclass(frozen=True)
class ScoringCandidate:
    """A manifest row plus the minimal CandidateRow geometry consumed by Stage 1."""

    geometry: object
    role: str
    block_index: int

    @property
    def candidate_id(self) -> str:
        return self.geometry.candidate_id

    @property
    def seqid(self) -> str:
        return self.geometry.seqid

    @property
    def gap_start(self) -> int:
        return self.geometry.gap_start

    @property
    def gap_end(self) -> int:
        return self.geometry.gap_end

    @property
    def gap_length(self) -> int:
        return self.geometry.gap_length

    @property
    def stratum(self) -> str:
        return self.geometry.stratum

    @property
    def crop_start(self) -> int:
        return self.geometry.crop_start

    @property
    def crop_end(self) -> int:
        return self.geometry.crop_end


def _int_field(row: dict[str, str], field: str) -> int:
    value = int(row[field])
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _manifest_candidate(row: dict[str, str]) -> ScoringCandidate:
    candidate_id = row["candidate_id"]
    left_start = _int_field(row, "left_run_start")
    left_end = _int_field(row, "left_run_end")
    gap_start = _int_field(row, "gap_start")
    gap_end = _int_field(row, "gap_end")
    right_start = _int_field(row, "right_run_start")
    right_end = _int_field(row, "right_run_end")
    crop_start = _int_field(row, "crop_start")
    crop_end = _int_field(row, "crop_end")
    gap_length = _int_field(row, "gap_length")
    if gap_end <= gap_start or gap_end - gap_start != gap_length or gap_length > 512:
        raise ValueError(f"invalid chr13 candidate gap geometry: {candidate_id}")
    if left_end != gap_start or right_start != gap_end:
        raise ValueError(f"candidate runs do not abut gap: {candidate_id}")
    if left_end <= left_start or right_end <= right_start:
        raise ValueError(f"candidate flank run is empty: {candidate_id}")
    if crop_start != gap_start - stage1_train.FLANK_BP:
        raise ValueError(f"candidate crop_start disagrees with gap geometry: {candidate_id}")
    if crop_end != gap_end + stage1_train.FLANK_BP:
        raise ValueError(f"candidate crop_end disagrees with gap geometry: {candidate_id}")
    if crop_end - crop_start > stage1_train.MAX_INPUT_BP:
        raise ValueError(f"candidate crop exceeds frozen Stage 1 input: {candidate_id}")
    stratum = row["length_stratum"]
    if stratum != stage1_train.length_stratum(gap_length):
        raise ValueError(f"candidate length stratum disagrees with gap: {candidate_id}")
    block_text = row["chr13_block_index"].strip()
    if not block_text:
        raise ValueError(f"scored chr13 candidate has no block index: {candidate_id}")
    block_index = int(block_text)
    if block_index < 0:
        raise ValueError(f"chr13 block index must be non-negative: {candidate_id}")
    geometry = stage1_train.CandidateRow(
        candidate_id=candidate_id,
        seqid=SEQID,
        gap_start=gap_start,
        gap_end=gap_end,
        gap_length=gap_length,
        left_run_length=left_end - left_start,
        right_run_length=right_end - right_start,
        span_length=right_end - left_start,
        target=0.0,
        stratum=stratum,
    )
    return ScoringCandidate(geometry=geometry, role=row["role"], block_index=block_index)


def load_scoring_candidates(path: Path) -> tuple[list[ScoringCandidate], dict[str, int]]:
    """Read only label-independent candidate geometry for the three chr13 roles."""
    candidates: list[ScoringCandidate] = []
    seen: set[str] = set()
    excluded: Counter[str] = Counter()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not set(MANIFEST_FIELDS) <= set(reader.fieldnames):
            raise ValueError("candidate manifest lacks frozen label-independent Stage 1 fields")
        for row in reader:
            if row["seqid"] != SEQID:
                excluded["non_chr13"] += 1
                continue
            if row["role"] not in ROLES:
                excluded["non_scored_role"] += 1
                continue
            if not row["chr13_block_index"].strip():
                excluded["quarantined"] += 1
                continue
            candidate = _manifest_candidate(row)
            if candidate.candidate_id in seen:
                raise ValueError(f"duplicate scoring candidate: {candidate.candidate_id}")
            seen.add(candidate.candidate_id)
            candidates.append(candidate)
    if not candidates:
        raise ValueError("candidate manifest contains no scored chr13 DEV/CAL rows")
    return candidates, dict(sorted(excluded.items()))


def chr13_anchor_map(candidates: list[ScoringCandidate]) -> dict[int, list[ScoringCandidate]]:
    """Map each candidate to the one 8192-bp window containing its crop end."""
    anchors: dict[int, list[ScoringCandidate]] = defaultdict(list)
    for candidate in candidates:
        anchor = ((candidate.crop_end - 1) // WINDOW) * WINDOW
        anchors[anchor].append(candidate)
    for rows in anchors.values():
        rows.sort(key=lambda row: (row.crop_start, row.crop_end, row.candidate_id))
    return dict(anchors)


def head_specs() -> tuple[tuple[str, int, str, str], ...]:
    return tuple(
        (arm, seed, f"{arm}__seed{seed}.pt", f"{arm}__seed{seed}__raw_risk_logit")
        for arm in ("G_GEOMETRY_LOGITS", "R_RAW_LOCAL", "H_P3_LATENT")
        for seed in SEEDS
    )


def load_training_artifacts(training_output: Path, device):
    import torch

    stats = json.loads((training_output / "scalar_stats.json").read_text(encoding="utf-8"))
    if stats.get("schema") != "gap_bridge_neural_stage1_scalar_stats_v1":
        raise ValueError("Stage 1 scalar statistics schema is not frozen")
    if tuple(stats.get("fields", ())) != tuple(stage1_train.SCALAR_FIELDS):
        raise ValueError("Stage 1 scalar statistics fields are not frozen")
    heads_dir = training_output / "heads"
    observed = {path.name for path in heads_dir.glob("*.pt")}
    expected = set(HEAD_FILENAMES)
    if observed != expected:
        raise ValueError(f"Stage 1 head set is not exactly the frozen nine heads: {sorted(observed ^ expected)}")
    model_module = stage1_train.load_stage1_model()
    heads: dict[tuple[str, int], object] = {}
    for arm, seed, filename, _column in head_specs():
        head = model_module.GapHead(arm).to(device)
        state = torch.load(heads_dir / filename, map_location="cpu")
        head.load_state_dict(state)
        head.eval()
        heads[(arm, seed)] = head
    return stats, heads, model_module


def _sample(candidate: ScoringCandidate, sequence: str, logits: np.ndarray, latent: np.ndarray, stats):
    geometry = candidate.geometry
    return stage1_train.Sample(
        channels=stage1_train.build_channels(sequence, logits, latent, geometry),
        geometry=stage1_train.standardized_scalars(geometry, stats),
        target=0.0,
        length=candidate.gap_length,
        stratum=candidate.stratum,
        candidate_id=candidate.candidate_id,
    )


def _score_batch(
    candidates: list[ScoringCandidate],
    samples: list[object],
    heads: dict[tuple[str, int], object],
    model_module,
    device,
) -> list[dict[str, float]]:
    import torch

    channels = torch.from_numpy(np.stack([sample.channels for sample in samples])).float().to(device)
    geometry = torch.from_numpy(np.stack([sample.geometry for sample in samples])).float().to(device)
    arm_inputs = {
        arm: model_module.apply_arm_input(channels, arm)
        for arm in model_module.ARMS
    }
    output: list[dict[str, float]] = [dict() for _ in samples]
    with torch.no_grad():
        for arm in model_module.ARMS:
            prepared = arm_inputs[arm]
            for seed in SEEDS:
                values = heads[(arm, seed)].forward_prepared(prepared, geometry)
                column = f"{arm}__seed{seed}__raw_risk_logit"
                for index, value in enumerate(values.detach().cpu().tolist()):
                    output[index][column] = float(value)
    return output


def score(
    candidate_manifest: Path,
    chr13_region: Path,
    model_dir: Path,
    training_output: Path,
    output_dir: Path,
) -> dict[str, object]:
    import torch

    candidates, excluded = load_scoring_candidates(candidate_manifest)
    if output_dir.exists():
        raise ValueError(f"refusing to reuse Stage 1 scoring output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    c5 = stage1_train.load_c5()
    model, tokenizer, metadata, device, _te = c5.load_p3_model(model_dir)
    stats, heads, model_module = load_training_artifacts(training_output, device)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)

    anchors = chr13_anchor_map(candidates)
    output_path = output_dir / "chr13_stage1_raw_logits.tsv"
    output_fields = (
        "candidate_id", "seqid", "role", "chr13_block_index",
        "gap_start", "gap_end", "gap_length", "length_stratum", *HEAD_COLUMNS,
    )
    role_counts: Counter[str] = Counter()
    seen: set[str] = set()
    windows = 0
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        pending_candidates: list[ScoringCandidate] = []
        pending_samples: list[object] = []
        previous = None
        for start, end, sequence in stage1_train.iter_region_records(chr13_region, SEQID):
            current = stage1_train._p3_forward_window(model, tokenizer, device, start, end, sequence)
            windows += 1
            for candidate in anchors.get(start, []):
                crop_sequence, crop_logits, crop_latent = stage1_train.assemble_crop(
                    previous, current, candidate.crop_start, candidate.crop_end,
                )
                pending_candidates.append(candidate)
                pending_samples.append(_sample(candidate, crop_sequence, crop_logits, crop_latent, stats))
                if len(pending_candidates) == BATCH_SIZE:
                    predictions = _score_batch(
                        pending_candidates, pending_samples, heads, model_module, device,
                    )
                    for scored, values in zip(pending_candidates, predictions):
                        writer.writerow({
                            "candidate_id": scored.candidate_id,
                            "seqid": scored.seqid,
                            "role": scored.role,
                            "chr13_block_index": scored.block_index,
                            "gap_start": scored.gap_start,
                            "gap_end": scored.gap_end,
                            "gap_length": scored.gap_length,
                            "length_stratum": scored.stratum,
                            **{column: format(values[column], ".17g") for column in HEAD_COLUMNS},
                        })
                        seen.add(scored.candidate_id)
                        role_counts[scored.role] += 1
                    pending_candidates.clear()
                    pending_samples.clear()
            previous = current
        if pending_candidates:
            predictions = _score_batch(
                pending_candidates, pending_samples, heads, model_module, device,
            )
            for scored, values in zip(pending_candidates, predictions):
                writer.writerow({
                    "candidate_id": scored.candidate_id,
                    "seqid": scored.seqid,
                    "role": scored.role,
                    "chr13_block_index": scored.block_index,
                    "gap_start": scored.gap_start,
                    "gap_end": scored.gap_end,
                    "gap_length": scored.gap_length,
                    "length_stratum": scored.stratum,
                    **{column: format(values[column], ".17g") for column in HEAD_COLUMNS},
                })
                seen.add(scored.candidate_id)
                role_counts[scored.role] += 1
    expected_ids = {candidate.candidate_id for candidate in candidates}
    if seen != expected_ids:
        missing = sorted(expected_ids - seen)
        extra = sorted(seen - expected_ids)
        raise ValueError(f"chr13 scoring did not cover manifest candidates: missing={missing[:3]} extra={extra[:3]}")
    summary = {
        "schema": "gap_bridge_neural_stage1_chr13_raw_score_v1",
        "status": "PASS",
        "seqid": SEQID,
        "roles": list(ROLES),
        "candidate_manifest": str(candidate_manifest),
        "region": str(chr13_region),
        "model_dir": str(model_dir),
        "training_output": str(training_output),
        "model_schema": metadata["schema"],
        "p3_forward_context": {"window": WINDOW, "stride": WINDOW, "forward_once_per_window": True},
        "latent_hook": "TEUNetSegmenter.classifier input decoded map",
        "latent_written_to_disk": False,
        "labels_read": False,
        "rows_scored": len(candidates),
        "rows_scored_by_role": {role: role_counts[role] for role in ROLES},
        "excluded_manifest_rows": excluded,
        "windows_forwarded": windows,
        "batch_size": BATCH_SIZE,
        "head_columns": list(HEAD_COLUMNS),
        "head_files": list(HEAD_FILENAMES),
        "chr19_read": False,
        "scientific_metrics_computed": False,
    }
    (output_dir / "score_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output_dir / "STATUS").write_text("PASS\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--chr13-region", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--training-output", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = score(
        args.candidate_manifest, args.chr13_region, args.model_dir,
        args.training_output, args.output_dir,
    )
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
