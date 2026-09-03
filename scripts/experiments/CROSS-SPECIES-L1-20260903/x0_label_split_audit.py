#!/usr/bin/env python3
"""Materialize and audit the frozen cross-species Label-A tile panels."""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import json
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


TILE_BP = 8192
BLOCK_BP = 512 * 1024
TRAIN_TILES = 1500
CAL_TILES = 500
DEV_TILES = 500
TEST_TILES = 1200
LABEL_RUN_ID = "RMDFAM_FULLPARTITIONS_RERUN_20260617"
STRICT_TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "Retroposon"}
UNKNOWN_CLASSES = {"unknown", "unclassified"}
HARD_NEGATIVE_CLASSES = {
    "low_complexity",
    "rna",
    "rrna",
    "satellite",
    "scrna",
    "simple_repeat",
    "snrna",
    "srprna",
    "tandem_repeat",
    "trna",
}


def open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open("rt")


def read_species_table(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {
        "species_code",
        "assembly",
        "cohort_role",
        "fasta",
        "self_out",
        "primary_regex",
        "train_chromosomes",
        "validation_chromosomes",
        "test_chromosomes",
        "explicit_contigs",
    }
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"species table missing columns: {', '.join(sorted(missing))}")
    seen = set()
    for row in rows:
        key = row["species_code"]
        if key in seen:
            raise ValueError(f"duplicate species_code: {key}")
        seen.add(key)
        for field in ("fasta", "self_out"):
            if not Path(row[field]).is_file():
                raise FileNotFoundError(row[field])
    return rows


def fasta_stats(path: Path) -> tuple[dict[str, int], dict[str, int]]:
    lengths: dict[str, int] = {}
    non_acgt: dict[str, int] = {}
    chrom = None
    length = ambiguous = 0
    with open_text(path) as handle:
        for raw in handle:
            if raw.startswith(">"):
                if chrom is not None:
                    lengths[chrom] = length
                    non_acgt[chrom] = ambiguous
                chrom = raw[1:].split()[0]
                if chrom in lengths:
                    raise ValueError(f"duplicate FASTA contig: {chrom}")
                length = ambiguous = 0
                continue
            sequence = raw.strip().upper()
            length += len(sequence)
            ambiguous += len(sequence) - sum(sequence.count(base) for base in "ACGT")
    if chrom is not None:
        lengths[chrom] = length
        non_acgt[chrom] = ambiguous
    return lengths, non_acgt


def iter_fasta(path: Path, wanted: set[str]):
    chrom = None
    parts: list[str] = []
    with open_text(path) as handle:
        for raw in handle:
            if raw.startswith(">"):
                if chrom in wanted:
                    yield chrom, "".join(parts).upper()
                chrom = raw[1:].split()[0]
                parts = []
            elif chrom in wanted:
                parts.append(raw.strip())
        if chrom in wanted:
            yield chrom, "".join(parts).upper()


def merge_intervals(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(values):
        if end <= start:
            continue
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        elif end > merged[-1][1]:
            merged[-1] = (merged[-1][0], end)
    return merged


def parse_repeatmasker(
    path: Path, lengths: dict[str, int], wanted: set[str]
) -> tuple[dict[str, dict[str, tuple[list[tuple[int, int]], list[int]]]], dict[str, int]]:
    raw: dict[str, dict[str, list[tuple[int, int]]]] = {
        kind: defaultdict(list) for kind in ("positive", "unknown", "hard_negative")
    }
    stats = {"records": 0, "missing_contig_records": 0, "out_of_bounds_records": 0}
    with open_text(path) as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) < 11 or not parts[0].isdigit():
                continue
            stats["records"] += 1
            chrom = parts[4]
            if chrom not in lengths:
                stats["missing_contig_records"] += 1
                continue
            start = int(parts[5]) - 1
            end = int(parts[6])
            if start < 0 or end > lengths[chrom] or end <= start:
                stats["out_of_bounds_records"] += 1
                continue
            if chrom not in wanted:
                continue
            class_family = parts[10]
            top = class_family.split("/", 1)[0]
            top_lower = top.lower()
            if top in STRICT_TE_CLASSES:
                raw["positive"][chrom].append((start, end))
            elif any(top_lower.startswith(value) for value in UNKNOWN_CLASSES):
                raw["unknown"][chrom].append((start, end))
            elif top_lower in HARD_NEGATIVE_CLASSES:
                raw["hard_negative"][chrom].append((start, end))

    packed: dict[str, dict[str, tuple[list[tuple[int, int]], list[int]]]] = {}
    for kind, by_chrom in raw.items():
        packed[kind] = {}
        for chrom, values in by_chrom.items():
            merged = merge_intervals(values)
            packed[kind][chrom] = (merged, [end for _, end in merged])
    return packed, stats


def paint(labels: bytearray, chrom: str, tile_start: int, intervals, value: int) -> None:
    item = intervals.get(chrom)
    if not item:
        return
    values, ends = item
    tile_end = tile_start + len(labels)
    index = bisect.bisect_right(ends, tile_start)
    for start, end in values[index:]:
        if start >= tile_end:
            break
        left = max(start, tile_start) - tile_start
        right = min(end, tile_end) - tile_start
        if right > left:
            labels[left:right] = bytes([value]) * (right - left)


def stable_order(*parts: object) -> bytes:
    value = "|".join(str(part) for part in parts).encode()
    return hashlib.sha256(value).digest()


def allocate_quotas(
    available: dict[str, int], total: int, lower_fraction: float, upper_fraction: float
) -> dict[str, int]:
    if sum(available.values()) < total:
        raise ValueError(f"only {sum(available.values())} eligible tiles for requested {total}")
    chroms = sorted(available)
    lower = int(total * lower_fraction)
    upper = int(total * upper_fraction + 0.999999)
    quotas = {chrom: min(lower, available[chrom]) for chrom in chroms}
    targets = {
        chrom: total * available[chrom] / sum(available.values()) for chrom in chroms
    }
    while sum(quotas.values()) < total:
        choices = [
            chrom
            for chrom in chroms
            if quotas[chrom] < min(upper, available[chrom])
        ]
        if not choices:
            raise ValueError("chromosome contribution bounds cannot satisfy tile count")
        chrom = max(choices, key=lambda value: (targets[value] - quotas[value], value))
        quotas[chrom] += 1
    return quotas


def candidate_tiles(sequence: str) -> list[int]:
    starts = []
    for start in range(0, len(sequence) - TILE_BP + 1, TILE_BP):
        tile = sequence[start : start + TILE_BP]
        non_acgt = len(tile) - sum(tile.count(base) for base in "ACGT")
        if non_acgt / TILE_BP <= 0.01:
            starts.append(start)
    return starts


def choose_tiles(
    species: str,
    assembly: str,
    split: str,
    candidates: dict[str, list[int]],
    count: int,
    lower_fraction: float,
    upper_fraction: float,
) -> list[tuple[str, int, str]]:
    quotas = allocate_quotas(
        {chrom: len(starts) for chrom, starts in candidates.items()},
        count,
        lower_fraction,
        upper_fraction,
    )
    selected = []
    for chrom, starts in candidates.items():
        ranked = sorted(
            starts,
            key=lambda start: stable_order(
                "TE_L1_ANIMAL_X0_R2", species, assembly, split, chrom, start, start + TILE_BP
            ),
        )
        selected.extend((chrom, start, split) for start in ranked[: quotas[chrom]])
    return selected


def split_validation_tiles(
    species: str,
    assembly: str,
    candidates: dict[str, list[int]],
) -> list[tuple[str, int, str]]:
    blocks = sorted(
        {(chrom, start // BLOCK_BP) for chrom, starts in candidates.items() for start in starts},
        key=lambda item: stable_order("TE_L1_ANIMAL_X0_R2", species, assembly, *item),
    )
    block_role = {block: ("CAL" if index % 2 == 0 else "DEV") for index, block in enumerate(blocks)}
    by_role = {"CAL": defaultdict(list), "DEV": defaultdict(list)}
    for chrom, starts in candidates.items():
        for start in starts:
            role = block_role[(chrom, start // BLOCK_BP)]
            by_role[role][chrom].append(start)
    result = []
    counts = {"CAL": CAL_TILES, "DEV": DEV_TILES}
    for role in ("CAL", "DEV"):
        lower, upper = (0.0, 1.0) if len(by_role[role]) == 1 else (0.20, 0.45)
        result.extend(
            choose_tiles(species, assembly, role, by_role[role], counts[role], lower, upper)
        )
    return result


def select_chromosomes(row: dict[str, str], lengths: dict[str, int], non_acgt: dict[str, int]):
    pattern = re.compile(row["primary_regex"])
    primary = [
        chrom
        for chrom, length in lengths.items()
        if pattern.fullmatch(chrom) and length >= TILE_BP and non_acgt[chrom] < length
    ]
    primary.sort(key=lambda chrom: (-lengths[chrom], chrom))
    explicit = [] if row["explicit_contigs"] == "." else row["explicit_contigs"].split(",")
    if explicit:
        missing = set(explicit) - set(primary)
        if missing:
            raise ValueError(f"explicit primary contigs missing: {', '.join(sorted(missing))}")
        return {"TEST": explicit}
    if row["cohort_role"] == "train":
        n_train = int(row["train_chromosomes"])
        n_val = int(row["validation_chromosomes"])
        pool = primary[: n_train + n_val]
        if len(pool) < n_train + n_val:
            raise ValueError("not enough primary chromosomes for TRAIN/validation split")
        pool.sort(
            key=lambda chrom: stable_order(
                "TE_L1_ANIMAL_X0_R2", row["species_code"], row["assembly"], chrom
            )
        )
        return {"TRAIN": pool[:n_train], "VALIDATION": pool[n_train:]}
    n_test = int(row["test_chromosomes"])
    if len(primary) < n_test:
        raise ValueError("not enough primary chromosomes for TEST panel")
    return {"TEST": primary[:n_test]}


def interval_overlap(a: tuple[str, int, int], b: tuple[str, int, int]) -> bool:
    return a[0] == b[0] and max(a[1], b[1]) < min(a[2], b[2])


def label_selected_tiles(
    fasta: Path,
    selected: list[tuple[str, int, str]],
    intervals,
    species: str,
    assembly: str,
    cohort_role: str,
) -> list[dict[str, object]]:
    wanted = {chrom for chrom, _, _ in selected}
    by_chrom: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for chrom, start, split in selected:
        by_chrom[chrom].append((start, split))
    rows = []
    for chrom, sequence in iter_fasta(fasta, wanted):
        for start, split in by_chrom[chrom]:
            piece = sequence[start : start + TILE_BP]
            labels = bytearray(TILE_BP)
            paint(labels, chrom, start, intervals["hard_negative"], 3)
            for index, base in enumerate(piece):
                if base not in "ACGT":
                    labels[index] = 2
            paint(labels, chrom, start, intervals["unknown"], 2)
            paint(labels, chrom, start, intervals["positive"], 1)
            positive = labels.count(1)
            unknown = labels.count(2)
            hard_negative = labels.count(3)
            negative = TILE_BP - positive - unknown
            callable_bp = positive + negative
            rows.append(
                {
                    "species_code": species,
                    "assembly": assembly,
                    "cohort_role": cohort_role,
                    "split": split,
                    "chrom": chrom,
                    "start": start,
                    "end": start + TILE_BP,
                    "block_id": f"{chrom}:{start // BLOCK_BP}",
                    "positive_bp": positive,
                    "negative_bp": negative,
                    "unknown_bp": unknown,
                    "hard_negative_bp": hard_negative,
                    "callable_bp": callable_bp,
                    "positive_prevalence": positive / callable_bp if callable_bp else 0.0,
                }
            )
    if len(rows) != len(selected):
        raise ValueError(f"selected {len(selected)} tiles but labelled {len(rows)}")
    return rows


def audit_species(row: dict[str, str]) -> dict[str, object]:
    fasta = Path(row["fasta"])
    lengths, non_acgt = fasta_stats(fasta)
    chrom_roles = select_chromosomes(row, lengths, non_acgt)
    wanted = {chrom for chroms in chrom_roles.values() for chrom in chroms}
    intervals, rm_stats = parse_repeatmasker(Path(row["self_out"]), lengths, wanted)
    candidates = {}
    for chrom, sequence in iter_fasta(fasta, wanted):
        candidates[chrom] = candidate_tiles(sequence)

    if row["cohort_role"] == "train":
        train_candidates = {chrom: candidates[chrom] for chrom in chrom_roles["TRAIN"]}
        val_candidates = {chrom: candidates[chrom] for chrom in chrom_roles["VALIDATION"]}
        selected = choose_tiles(
            row["species_code"], row["assembly"], "TRAIN", train_candidates, TRAIN_TILES, 0.10, 0.30
        )
        selected.extend(split_validation_tiles(row["species_code"], row["assembly"], val_candidates))
    else:
        test_candidates = {chrom: candidates[chrom] for chrom in chrom_roles["TEST"]}
        selected = choose_tiles(
            row["species_code"], row["assembly"], "TEST", test_candidates, TEST_TILES, 0.15, 0.35
        )

    tile_rows = label_selected_tiles(
        fasta,
        selected,
        intervals,
        row["species_code"],
        row["assembly"],
        row["cohort_role"],
    )
    return {
        "species_code": row["species_code"],
        "assembly": row["assembly"],
        "cohort_role": row["cohort_role"],
        "fasta": row["fasta"],
        "self_out": row["self_out"],
        "selected_chromosomes": chrom_roles,
        "repeatmasker_stats": rm_stats,
        "tile_rows": tile_rows,
    }


def summarize_species(result: dict[str, object]) -> list[dict[str, object]]:
    rows = result["tile_rows"]
    summaries = []
    for split in sorted({row["split"] for row in rows}):
        subset = [row for row in rows if row["split"] == split]
        positive = sum(row["positive_bp"] for row in subset)
        negative = sum(row["negative_bp"] for row in subset)
        unknown = sum(row["unknown_bp"] for row in subset)
        callable_bp = positive + negative
        chrom_counts: dict[str, int] = defaultdict(int)
        block_classes: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in subset:
            chrom_counts[row["chrom"]] += TILE_BP
            block_classes[row["block_id"]][0] += row["positive_bp"]
            block_classes[row["block_id"]][1] += row["negative_bp"]
        mixed_blocks = sum(positive_bp > 0 and negative_bp > 0 for positive_bp, negative_bp in block_classes.values())
        max_chrom_fraction = max(chrom_counts.values()) / (len(subset) * TILE_BP)
        gates = {
            "assembly_contigs": result["repeatmasker_stats"]["missing_contig_records"] == 0,
            "coordinates": result["repeatmasker_stats"]["out_of_bounds_records"] == 0,
            "unknown": unknown / (len(subset) * TILE_BP) <= 0.10,
            "prevalence": callable_bp > 0 and 0.005 <= positive / callable_bp <= 0.80,
        }
        if split in {"CAL", "DEV"}:
            gates["mass"] = positive >= 100_000 and negative >= 500_000
        elif split == "TEST":
            gates["mass"] = positive >= 250_000 and negative >= 2_000_000
            gates["mixed_blocks"] = mixed_blocks >= 16
            gates["chromosome_balance"] = max_chrom_fraction <= 0.40
        summary = {
            "species_code": result["species_code"],
            "assembly": result["assembly"],
            "cohort_role": result["cohort_role"],
            "split": split,
            "tiles": len(subset),
            "chromosomes": len(chrom_counts),
            "positive_bp": positive,
            "negative_bp": negative,
            "unknown_bp": unknown,
            "hard_negative_bp": sum(row["hard_negative_bp"] for row in subset),
            "positive_prevalence": positive / callable_bp if callable_bp else 0.0,
            "unknown_fraction": unknown / (len(subset) * TILE_BP),
            "mixed_512kb_blocks": mixed_blocks,
            "max_chromosome_fraction": max_chrom_fraction,
            "gate_status": "PASS" if all(gates.values()) else "FAIL",
            "failed_gates": ",".join(key for key, passed in gates.items() if not passed),
        }
        summaries.append(summary)
    return summaries


def assert_no_split_overlap(tile_rows: list[dict[str, object]]) -> None:
    by_species: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in tile_rows:
        by_species[row["species_code"]].append(row)
    for species, rows in by_species.items():
        ordered = sorted(rows, key=lambda row: (row["chrom"], row["start"]))
        for previous, current in zip(ordered, ordered[1:]):
            if previous["split"] != current["split"] and interval_overlap(
                (previous["chrom"], previous["start"], previous["end"]),
                (current["chrom"], current["start"], current["end"]),
            ):
                raise ValueError(f"coordinate overlap between splits for {species}")


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species-table", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    rows = read_species_table(args.species_table)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(audit_species, rows))
    tile_rows = [row for result in results for row in result["tile_rows"]]
    assert_no_split_overlap(tile_rows)
    summaries = [row for result in results for row in summarize_species(result)]

    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_tsv(args.output_dir / "tiles.tsv", tile_rows)
    write_tsv(args.output_dir / "species_readiness.tsv", summaries)
    decision = {
        "protocol": "CROSS-SPECIES-L1-MATERIAL-X0-R2",
        "label_run_id": LABEL_RUN_ID,
        "label_contract": {
            "positive": "self Label-A LINE/SINE/LTR/DNA/RC/Retroposon",
            "unknown": "self Label-A Unknown/Unclassified plus non-ACGT assembly bases",
            "negative": "other callable ACGT bases",
            "priority": "positive > unknown > negative",
        },
        "tile_counts": {
            "TRAIN": TRAIN_TILES,
            "CAL": CAL_TILES,
            "DEV": DEV_TILES,
            "TEST": TEST_TILES,
        },
        "status": "X0_PASS_TO_TRAIN" if all(row["gate_status"] == "PASS" for row in summaries) else "X0_FAIL_NO_GPU",
        "species": [
            {
                key: result[key]
                for key in ("species_code", "assembly", "cohort_role", "fasta", "self_out", "selected_chromosomes", "repeatmasker_stats")
            }
            for result in results
        ],
        "failed_panels": [
            f"{row['species_code']}:{row['split']}:{row['failed_gates']}"
            for row in summaries
            if row["gate_status"] == "FAIL"
        ],
    }
    (args.output_dir / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
