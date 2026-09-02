#!/usr/bin/env python3
"""Build the frozen chr3/chr5/chr13 Stage 1 candidate manifest."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CHROMOSOMES = ("chr3", "chr5", "chr13")
FIELDS = (
    "row_id", "candidate_id", "seqid", "role", "chr13_block_index",
    "left_run_start", "left_run_end", "gap_start", "gap_end",
    "right_run_start", "right_run_end", "crop_start", "crop_end",
    "gap_length", "length_stratum", "comparator_known", "positive_bp",
    "negative_bp", "unknown_bp", "target_negative_fraction",
    "comparator_relation",
)


def load_stage0():
    path = Path(__file__).with_name("stage0_oracle.py")
    spec = importlib.util.spec_from_file_location("stage1_manifest_stage0", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(source_root: Path, stage0_json: Path, output_dir: Path) -> dict[str, object]:
    stage0 = load_stage0()
    frozen = json.loads(stage0_json.read_text(encoding="utf-8"))
    if frozen["status"] != "PASS_TO_STAGE1":
        raise ValueError("Stage 1 manifest requires a PASS_TO_STAGE1 oracle")
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = output_dir / "candidate_manifest.tsv"
    counts: Counter[tuple[str, str]] = Counter()
    excluded: Counter[tuple[str, str]] = Counter()
    row_id = 0
    recomputed_chr13_split: list[dict[str, object]] = []

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for seqid in CHROMOSOMES:
            chromosome_root = source_root / seqid
            bases = stage0.load_base_candidates(chromosome_root / "candidates.tsv", seqid)
            sequence = stage0.read_region_sequence(chromosome_root / "region.jsonl.gz", seqid)
            if seqid == "chr13":
                role_by_block, recomputed_chr13_split = stage0.chr13_split(len(sequence))
            else:
                role_by_block = {}
            eligible: dict[str, object] = {}
            roles: dict[str, tuple[str, int | None]] = {}
            for candidate in bases:
                crop_start = candidate.gap_start - stage0.FLANK_BP
                crop_end = candidate.gap_end + stage0.FLANK_BP
                if candidate.length > stage0.MAX_GAP_BP:
                    excluded[(seqid, "gap_gt_512")] += 1
                    continue
                if crop_start < 0 or crop_end > len(sequence):
                    excluded[(seqid, "crop_outside_chromosome")] += 1
                    continue
                block_index: int | None = None
                role = "TRAIN"
                if seqid == "chr13":
                    first_block = crop_start // stage0.SUPERBLOCK_BP
                    last_block = (crop_end - 1) // stage0.SUPERBLOCK_BP
                    if first_block != last_block:
                        excluded[(seqid, "crop_crosses_superblock")] += 1
                        continue
                    block_index = first_block
                    role = role_by_block[block_index]
                if not set(sequence[crop_start:crop_end]) <= stage0.ACGT:
                    excluded[(seqid, "crop_non_acgt")] += 1
                    continue
                eligible[candidate.candidate_id] = candidate
                roles[candidate.candidate_id] = (role, block_index)
            labels = {
                candidate.base.candidate_id: candidate
                for candidate in stage0.load_labels(
                    chromosome_root / "labeled.tsv", eligible, seqid,
                )
            }
            for candidate in bases:
                label = labels.get(candidate.candidate_id)
                if label is None:
                    continue
                role, block_index = roles[candidate.candidate_id]
                known = label.unknown_bp == 0
                writer.writerow({
                    "row_id": row_id,
                    "candidate_id": candidate.candidate_id,
                    "seqid": seqid,
                    "role": role,
                    "chr13_block_index": "" if block_index is None else block_index,
                    "left_run_start": candidate.left_run_start,
                    "left_run_end": candidate.left_run_end,
                    "gap_start": candidate.gap_start,
                    "gap_end": candidate.gap_end,
                    "right_run_start": candidate.right_run_start,
                    "right_run_end": candidate.right_run_end,
                    "crop_start": candidate.gap_start - stage0.FLANK_BP,
                    "crop_end": candidate.gap_end + stage0.FLANK_BP,
                    "gap_length": candidate.length,
                    "length_stratum": stage0.length_stratum(candidate.length),
                    "comparator_known": int(known),
                    "positive_bp": label.positive_bp,
                    "negative_bp": label.negative_bp,
                    "unknown_bp": label.unknown_bp,
                    "target_negative_fraction": (
                        format(label.negative_bp / candidate.length, ".17g") if known else ""
                    ),
                    "comparator_relation": label.relation,
                })
                counts[(role, "all")] += 1
                counts[(role, "known" if known else "unknown")] += 1
                row_id += 1
            del sequence

    if recomputed_chr13_split != frozen["chr13_split"]:
        raise ValueError("recomputed chr13 split differs from frozen Stage 0 split")
    expected = frozen["candidate_label_census"]
    observed_train_known = counts[("TRAIN", "known")]
    observed_train_unknown = counts[("TRAIN", "unknown")]
    observed_dev_known = counts[("DEV", "known")]
    observed_dev_unknown = counts[("DEV", "unknown")]
    if (
        observed_train_known != expected["train"]["comparator_known_candidates"]
        or observed_train_unknown != expected["train"]["comparator_unknown_candidates"]
        or observed_dev_known != expected["chr13_dev"]["comparator_known_candidates"]
        or observed_dev_unknown != expected["chr13_dev"]["comparator_unknown_candidates"]
    ):
        raise ValueError("Stage 1 manifest denominator differs from the Stage 0 oracle")

    summary = {
        "schema": "gap_bridge_neural_stage1_candidate_manifest_v1",
        "status": "PASS",
        "source_chromosomes": list(CHROMOSOMES),
        "chr19_read": False,
        "rows": row_id,
        "role_counts": {
            role: {
                "all": counts[(role, "all")],
                "known": counts[(role, "known")],
                "unknown": counts[(role, "unknown")],
            }
            for role in ("TRAIN", "DEV", "CAL_FIT", "CAL_GATE")
        },
        "excluded_counts": {
            seqid: {
                reason: count
                for (chromosome, reason), count in sorted(excluded.items())
                if chromosome == seqid
            }
            for seqid in CHROMOSOMES
        },
        "candidate_manifest": str(manifest_path),
        "scientific_metrics_computed": False,
    }
    (output_dir / "manifest_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output_dir / "STATUS").write_text("PASS\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--stage0-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.source_root, args.stage0_json, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
