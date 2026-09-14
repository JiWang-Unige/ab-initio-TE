#!/usr/bin/env python3
"""Materialize the fixed four-region sea-urchin annotation into 8192-bp tiles.

The source label is the saved RepeatMasker ``.out`` table.  Coordinates are
parsed with the project's existing RepeatMasker adapter (1-based inclusive to
zero-based half-open).  Strict TE classes become ``1``; unknown, ambiguous,
and PLE rows become ``?``; all remaining bases stay reference-negative ``0``.
Unknown masks take precedence over positive rows at an overlapping base.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import re
import traceback
from pathlib import Path


WINDOW_BP = 4096
TILE_BP = 8192
REGION_BP = 1048576
STRICT_TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "Retroposon"}


def _load_adapter():
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py"
    spec = importlib.util.spec_from_file_location("sea_repeatmasker_adapter", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load RepeatMasker adapter from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_fasta(path: Path) -> dict[str, str]:
    sequences: dict[str, str] = {}
    name = None
    chunks: list[str] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    sequences[name] = "".join(chunks).upper()
                name = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line)
    if name is not None:
        sequences[name] = "".join(chunks).upper()
    if not sequences:
        raise ValueError(f"empty FASTA: {path}")
    return sequences


def class_family(row: dict[str, object]) -> str:
    attributes = str(row.get("attributes", ""))
    marker = "class_family="
    for item in attributes.split(";"):
        if item.startswith(marker):
            return item[len(marker) :]
    return ""


def row_bucket(class_value: str) -> str:
    value = str(class_value).strip()
    top = value.split("/", 1)[0].strip()
    upper = top.upper()
    if "?" in value or upper in {"UNKNOWN", "UNCLASSIFIED", "PLE"}:
        return "unknown_or_ambiguous"
    if upper in {item.upper() for item in STRICT_TE_CLASSES}:
        return "known_te"
    return "reference_negative"


def region_number(region_id: str) -> int:
    match = re.search(r"__r(\d+)__", region_id)
    if not match:
        raise ValueError(f"cannot derive region number from {region_id}")
    return int(match.group(1))


def load_regions(path: Path) -> list[dict]:
    regions = json.loads(path.read_text())
    if not isinstance(regions, list) or len(regions) != 4:
        raise ValueError("fixed sea panel must contain four regions")
    for region in regions:
        if int(region["length_bp"]) != REGION_BP:
            raise ValueError("sea panel region is not the fixed 1,048,576 bp length")
    return regions


def build_labels(
    region: dict,
    sequence: str,
    rows: list[dict[str, object]],
) -> tuple[str, dict]:
    region_start_bp = int(region.get("start_bp", 0))
    region_end_bp = int(region.get("end_bp", region_start_bp + len(sequence)))
    if region_end_bp - region_start_bp != len(sequence):
        raise ValueError(
            f"{region.get('id', '<region>')}: region coordinates do not match FASTA length"
        )
    labels = bytearray(b"0" * len(sequence))
    counts = {"known_te_rows": 0, "unknown_or_ambiguous_rows": 0, "reference_negative_rows": 0}
    covered = {key: 0 for key in counts}
    intervals = []
    for row in rows:
        absolute_start = int(row["start"])
        absolute_end = int(row["end"])
        if absolute_start < region_start_bp or absolute_end > region_end_bp:
            raise ValueError(
                f"{region.get('id', '<region>')}: annotation interval "
                f"{absolute_start}-{absolute_end} is outside "
                f"{region_start_bp}-{region_end_bp}"
            )
        # The lifted RepeatMasker table uses the source scaffold coordinate
        # system, while panel FASTA positions are region-relative.
        start = absolute_start - region_start_bp
        end = absolute_end - region_start_bp
        if end <= start:
            continue
        bucket = row_bucket(class_family(row))
        key = f"{bucket}_rows"
        counts[key] += 1
        covered[key] += end - start
        intervals.append((start, end, bucket, class_family(row)))
    # Unknown/ambiguous has priority to keep uncertain annotation masked.
    for start, end, bucket, _ in intervals:
        if bucket == "unknown_or_ambiguous":
            labels[start:end] = b"?" * (end - start)
    for start, end, bucket, _ in intervals:
        if bucket == "known_te":
            for index in range(start, end):
                if labels[index] != ord("?"):
                    labels[index] = ord("1")
    non_acgt_masked = 0
    for index, base in enumerate(sequence):
        if base not in "ACGT":
            non_acgt_masked += 1
            labels[index] = ord("?")
    label_text = labels.decode("ascii")
    return label_text, {
        "region_id": str(region["id"]),
        "region_number": region_number(str(region["id"])),
        "sequence_bp": len(sequence),
        "label_counts_raw_rows": counts,
        "label_covered_bp_raw_overlap_sum": covered,
        "positive_bp": label_text.count("1"),
        "masked_bp": label_text.count("?"),
        "reference_negative_bp": label_text.count("0"),
        "non_acgt_masked_bp": non_acgt_masked,
    }


def run(config_path: Path, output_dir: Path) -> dict:
    config = json.loads(config_path.read_text())
    root = Path(config["remote"]["project_root"])
    fasta_path = root / config["remote"]["sea_panel_fasta"]
    regions_path = root / config["remote"]["sea_panel_regions"]
    labels_path = root / config["remote"]["sea_labels"]
    for path in (fasta_path, regions_path, labels_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    regions = load_regions(regions_path)
    sequences = read_fasta(fasta_path)
    adapter = _load_adapter()
    rows_by_region: dict[str, list[dict[str, object]]] = {str(r["id"]): [] for r in regions}
    raw_rows = 0
    for row in adapter.parse_repeatmasker_out(labels_path):
        seqid = str(row["seqid"])
        if seqid in rows_by_region:
            rows_by_region[seqid].append(row)
            raw_rows += 1
    output_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = output_dir / "sea_urchin_tiles.jsonl.gz"
    region_stats = []
    tile_count = {"TRAIN": 0, "CAL": 0, "EVAL": 0}
    split_label_totals = {
        split: {
            "positive_bp": 0,
            "reference_negative_bp": 0,
            "masked_bp": 0,
            "total_bp": 0,
        }
        for split in ("TRAIN", "CAL", "EVAL")
    }
    record_count = 0
    with gzip.open(out_jsonl, "wt") as handle:
        for region in regions:
            rid = str(region["id"])
            sequence = sequences.get(rid)
            if sequence is None:
                raise ValueError(f"panel FASTA is missing {rid}")
            if len(sequence) != REGION_BP:
                raise ValueError(f"{rid}: sequence length {len(sequence)} != {REGION_BP}")
            labels, stats = build_labels(region, sequence, rows_by_region[rid])
            number = stats["region_number"]
            split = "TRAIN" if number in {1, 2} else "CAL" if number == 3 else "EVAL"
            stats["split"] = split
            stats["repeatmasker_rows_seen"] = len(rows_by_region[rid])
            region_stats.append(stats)
            split_label_totals[split]["positive_bp"] += int(stats["positive_bp"])
            split_label_totals[split]["reference_negative_bp"] += int(stats["reference_negative_bp"])
            split_label_totals[split]["masked_bp"] += int(stats["masked_bp"])
            split_label_totals[split]["total_bp"] += int(stats["sequence_bp"])
            for tile_start in range(0, REGION_BP, TILE_BP):
                tile_id = f"sea_urchin|r{number:02d}|{tile_start}-{tile_start + TILE_BP}"
                tile_sequence = sequence[tile_start : tile_start + TILE_BP]
                tile_labels = labels[tile_start : tile_start + TILE_BP]
                for half in (0, 1):
                    left = half * WINDOW_BP
                    right = left + WINDOW_BP
                    record = {
                        "species_code": "sea_urchin",
                        "assembly": "sea_urchin_fixed_panel",
                        "split": split,
                        "tile_id": tile_id,
                        "half": half,
                        "chrom": rid,
                        "start": tile_start + left,
                        "end": tile_start + right,
                        "sequence": tile_sequence[left:right],
                        "labels": tile_labels[left:right],
                    }
                    if len(record["sequence"]) != WINDOW_BP or len(record["labels"]) != WINDOW_BP:
                        raise AssertionError("materialized half is not 4096 bp")
                    handle.write(json.dumps(record, separators=(",", ":")) + "\n")
                    record_count += 1
                tile_count[split] += 1
    manifest = {
        "status": "COMPLETED",
        "species": "sea_urchin",
        "assembly": "sea_urchin_fixed_panel",
        "source_fasta": str(fasta_path),
        "source_regions": str(regions_path),
        "source_repeatmasker_out": str(labels_path),
        "coordinate_contract": "project RepeatMasker adapter: 1-based inclusive to zero-based half-open",
        "label_policy": {
            "known_te": "strict LINE/SINE/LTR/DNA/RC/Retroposon -> 1",
            "unknown_or_ambiguous": "Unknown/Unclassified/PLE or class containing ? -> ?; masks take precedence",
            "reference_negative": "all remaining bases -> 0",
        },
        "split_policy": {"TRAIN": [1, 2], "CAL": [3], "EVAL": [4]},
        "raw_rows_retained_on_four_regions": raw_rows,
        "tile_bp": TILE_BP,
        "half_bp": WINDOW_BP,
        "tile_count": tile_count,
        "record_count": record_count,
        "region_stats": region_stats,
        "split_label_totals": split_label_totals,
        "output_jsonl_gz": str(out_jsonl),
    }
    (output_dir / "materialization_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.config, args.output_dir)
        print(json.dumps({"status": result["status"], "tile_count": result["tile_count"]}, indent=2), flush=True)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "failure.json").write_text(
            json.dumps({"status": "FAILED", "error": str(exc), "traceback": traceback.format_exc()}, indent=2) + "\n"
        )
        raise


if __name__ == "__main__":
    main()
