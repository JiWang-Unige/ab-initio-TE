#!/usr/bin/env python3
"""Materialize the bounded, label-blind *C. elegans* upstream panels."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path


X0_DIR = Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903"
sys.path.insert(0, str(X0_DIR))
import materialize_x0_windows as x0_materialize  # noqa: E402
import x0_label_split_audit as x0_audit  # noqa: E402


TILE_BP = x0_audit.TILE_BP
HALF_BP = x0_materialize.HALF_BP
BUFFER_BP = TILE_BP
SEED = 20260904
SPECIES = "c_elegans"
ASSEMBLY = "ce11"
OLD_TRAIN = 1500
NEW_TRAIN = 1500
SCREEN = 512
CONF = 256
TRAIN = "TRAIN"
MANIFEST_FIELDS = (
    "role",
    "species_code",
    "assembly",
    "split",
    "chrom",
    "start",
    "end",
    "tile_id",
    "source",
    "coordinate_only",
    "sequence_materialized",
    "labels_materialized",
)


def old_root(root: Path) -> Path:
    return root / "outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202"


def table_rows(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    worm = next(row for row in rows if row["species_code"] == SPECIES)
    return worm, [row for row in rows if row.get("cohort_role") == "train"]


def read_old(path: Path, split: str) -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    raw_rows: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for raw in handle:
            if raw.strip():
                rows.append(json.loads(raw))
                raw_rows.append(raw.rstrip("\n"))
    if {row["split"] for row in rows} != {split}:
        raise ValueError(f"unexpected split in {path}")
    return rows, raw_rows


def old_tiles(rows: list[dict[str, object]], expected: int | None = None) -> list[tuple[str, int, int, str, str]]:
    by_tile: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        start = int(row["start"]) - int(row["half"]) * HALF_BP
        by_tile[(str(row["chrom"]), start)].append(row)
    tiles = []
    for (chrom, start), halves in by_tile.items():
        if sorted(int(row["half"]) for row in halves) != [0, 1]:
            raise ValueError(f"unpaired old tile {chrom}:{start}")
        if start % TILE_BP:
            raise ValueError(f"old tile is not aligned {chrom}:{start}")
        tiles.append((chrom, start, start + TILE_BP, str(halves[0]["split"]), "existing_train"))
    tiles.sort(key=lambda tile: (tile[0], tile[1]))
    if expected is not None and len(tiles) != expected:
        raise ValueError(f"expected {expected} old tiles, found {len(tiles)}")
    return tiles


def overlap(a, b) -> bool:
    return a[0] == b[0] and max(a[1], b[1]) < min(a[2], b[2])


def distance(a, b) -> int:
    if a[0] != b[0]:
        return math.inf  # type: ignore[return-value]
    if a[2] <= b[1]:
        return b[1] - a[2]
    if b[2] <= a[1]:
        return a[1] - b[2]
    return 0


def candidate_grid(sequences: dict[str, str]) -> dict[str, list[int]]:
    """Exact X0 grid, including its label-blind <=1% non-ACGT filter."""

    return {chrom: x0_audit.candidate_tiles(sequence) for chrom, sequence in sequences.items()}


def filter_pool(candidates, excluded, gap, overlap_only=False):
    result = {}
    for chrom, starts in candidates.items():
        prior = [tile for tile in excluded if tile[0] == chrom]
        kept = []
        for start in starts:
            candidate = (chrom, start, start + TILE_BP, "", "candidate")
            okay = (
                all(not overlap(candidate, old) for old in prior)
                if overlap_only
                else all(distance(candidate, old) >= gap for old in prior)
            )
            if okay:
                kept.append(start)
        result[chrom] = kept
    return result


def quotas(available: dict[str, int], count: int, lower=0.0, upper=1.0) -> dict[str, int]:
    total = sum(available.values())
    if total < count:
        raise ValueError(f"only {total} eligible tiles for requested {count}")
    if not count:
        return {chrom: 0 for chrom in available}
    exact = {chrom: count * value / total for chrom, value in available.items()}
    lo, hi = int(count * lower), int(count * upper + 0.999999)
    result = {chrom: min(lo, hi, available[chrom]) for chrom in available}
    while sum(result.values()) < count:
        choices = [chrom for chrom in available if result[chrom] < min(hi, available[chrom])]
        if not choices:
            raise ValueError("chromosome quota bounds cannot satisfy requested count")
        chrom = sorted(choices, key=lambda value: (-(exact[value] - result[value]), value))[0]
        result[chrom] += 1
    return result


def choose(role: str, candidates, count: int):
    lower, upper = (0.0, 1.0) if role == "CONF" else (0.10, 0.30)
    quota = quotas({chrom: len(starts) for chrom, starts in candidates.items()}, count, lower, upper)
    split = "SCREEN" if role == "SCREEN" else "CONF" if role == "CONF" else TRAIN
    selected = []
    for chrom in sorted(candidates):
        starts = list(dict.fromkeys(candidates[chrom]))
        random.Random(f"{SEED}:{role}:{chrom}").shuffle(starts)
        selected.extend(
            (chrom, start, start + TILE_BP, split, "new_" + role.lower())
            for start in starts[: quota[chrom]]
        )
    return selected


def read_sequences(fasta: Path, wanted: set[str]) -> dict[str, str]:
    return {chrom: sequence for chrom, sequence in x0_audit.iter_fasta(fasta, wanted)}


def parse_rm(path: Path, lengths, wanted):
    raw = {kind: defaultdict(list) for kind in ("positive", "unknown", "hard_negative")}
    stats = {"records": 0, "used_records": 0, "ignored_nonwanted_records": 0, "out_of_bounds_records": 0}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) < 11 or not parts[0].isdigit():
                continue
            stats["records"] += 1
            chrom = parts[4]
            if chrom not in wanted:
                stats["ignored_nonwanted_records"] += 1
                continue
            stats["used_records"] += 1
            start, end = int(parts[5]) - 1, int(parts[6])
            if start < 0 or end > lengths[chrom] or end <= start:
                stats["out_of_bounds_records"] += 1
                continue
            top = parts[10].split("/", 1)[0]
            lower = top.lower()
            if top in x0_audit.STRICT_TE_CLASSES:
                raw["positive"][chrom].append((start, end))
            elif any(lower.startswith(value) for value in x0_audit.UNKNOWN_CLASSES):
                raw["unknown"][chrom].append((start, end))
            elif lower in x0_audit.HARD_NEGATIVE_CLASSES:
                raw["hard_negative"][chrom].append((start, end))
    return {
        kind: {
            chrom: (merged := x0_audit.merge_intervals(values), [end for _, end in merged])
            for chrom, values in by_chrom.items()
        }
        for kind, by_chrom in raw.items()
    }, stats


def new_records(tiles, sequences, intervals):
    records = []
    for chrom in sorted({tile[0] for tile in tiles}):
        for tile in sorted((tile for tile in tiles if tile[0] == chrom), key=lambda tile: tile[1]):
            piece, labels = x0_materialize._paint_tile(sequences[chrom], chrom, tile[1], intervals)
            for half in (0, 1):
                start = tile[1] + half * HALF_BP
                records.append(
                    {
                        "species_code": SPECIES,
                        "assembly": ASSEMBLY,
                        "split": tile[3],
                        "tile_id": f"{SPECIES}|{ASSEMBLY}|{chrom}:{tile[1]}-{tile[2]}",
                        "half": half,
                        "chrom": chrom,
                        "start": start,
                        "end": start + HALF_BP,
                        "sequence": piece[half * HALF_BP : (half + 1) * HALF_BP],
                        "labels": x0_materialize._label_string(labels[half * HALF_BP : (half + 1) * HALF_BP]),
                    }
                )
    return records


def write_jsonl(path: Path, old_raw, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for raw in old_raw:
            handle.write(raw + "\n")
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")


def manifest_row(role, tile, coordinate_only=False):
    materialized = not coordinate_only
    return {
        "role": role,
        "species_code": SPECIES,
        "assembly": ASSEMBLY,
        "split": tile[3],
        "chrom": tile[0],
        "start": tile[1],
        "end": tile[2],
        "tile_id": f"{SPECIES}|{ASSEMBLY}|{tile[0]}:{tile[1]}-{tile[2]}",
        "source": tile[4],
        "coordinate_only": str(coordinate_only).lower(),
        "sequence_materialized": str(materialized).lower(),
        "labels_materialized": str(materialized).lower(),
    }


def write_manifest(path: Path, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def counts(records):
    labels = "".join(str(record["labels"]) for record in records)
    positive, unknown, hard = labels.count("1"), labels.count("?"), labels.count("H")
    halves = len(records)
    negative = halves * HALF_BP - positive - unknown
    return {
        "tiles": halves // 2,
        "halves": halves,
        "positive_bp": positive,
        "negative_bp": negative,
        "unknown_bp": unknown,
        "hard_negative_bp": hard,
        "callable_bp": positive + negative,
    }


def role_summary(role, requested, tiles, records=None, coordinate_only=False):
    row = {
        "role": role,
        "requested_tiles": requested,
        "actual_tiles": len(tiles),
        "chromosomes": sorted({tile[0] for tile in tiles}),
        "coordinate_only": coordinate_only,
        "labels_materialized": records is not None,
    }
    row.update(counts(records) if records is not None else {
        "halves": 0,
        "positive_bp": None,
        "negative_bp": None,
        "unknown_bp": None,
        "hard_negative_bp": None,
        "callable_bp": None,
    })
    return row


def check_gap(left, right, minimum):
    violations = [
        (a[0], a[1], b[1], distance(a, b))
        for a in left
        for b in right
        if a[0] == b[0] and distance(a, b) < minimum
    ]
    return {"minimum_distance_bp": minimum, "violations": violations, "passed": not violations}


def check_nonoverlap(left, right):
    violations = [(a[0], a[1], b[1]) for a in left for b in right if overlap(a, b)]
    return {"violations": violations, "passed": not violations}


def metadata_paths(root, rows, table, old):
    return {
        "repository_root": str(root),
        "species_table": str(table),
        "old_materialization_root": str(old),
        "original_species_split_paths": {
            row["species_code"]: {
                split: str(old / split / f"{row['species_code']}.jsonl.gz")
                for split in ("TRAIN", "CAL", "DEV")
            }
            for row in rows
        },
    }


def run(root: Path, output_dir: Path, species_table: Path | None = None):
    root = root.expanduser()
    output_dir = output_dir.expanduser()
    table = species_table or root / "scripts/experiments/CROSS-SPECIES-L1-20260903/species_x0_r2.tsv"
    old = old_root(root)
    if output_dir.exists():
        raise FileExistsError(output_dir)

    worm, all_species = table_rows(table)
    train_path = old / "TRAIN" / f"{SPECIES}.jsonl.gz"
    cal_path = old / "CAL" / f"{SPECIES}.jsonl.gz"
    dev_path = old / "DEV" / f"{SPECIES}.jsonl.gz"
    old_train_rows, old_train_raw = read_old(train_path, "TRAIN")
    old_cal_rows, _ = read_old(cal_path, "CAL")
    old_dev_rows, _ = read_old(dev_path, "DEV")
    old_train = old_tiles(old_train_rows, OLD_TRAIN)
    old_validation = old_tiles(old_cal_rows) + old_tiles(old_dev_rows)
    train_chroms = {tile[0] for tile in old_train}
    validation_chroms = {tile[0] for tile in old_validation}
    if len(train_chroms) != 4 or len(validation_chroms) != 1:
        raise ValueError("old worm panel chromosome contract is not four TRAIN plus one CAL/DEV")

    # Candidate selection reads only these five selected chromosomes.  The
    # same X0 sequence-only callable-tile filter is label blind.
    sequences = read_sequences(Path(worm["fasta"]), train_chroms | validation_chroms)
    candidates = candidate_grid(sequences)
    train_candidates = {chrom: candidates[chrom] for chrom in sorted(train_chroms)}
    validation_candidates = {chrom: candidates[chrom] for chrom in sorted(validation_chroms)}

    screen_pool = filter_pool(train_candidates, old_train, BUFFER_BP)
    screen_capacity = sum(map(len, screen_pool.values()))
    screen_quota_error = None
    screen_tiles = []
    if screen_capacity >= SCREEN:
        try:
            screen_tiles = choose("SCREEN", screen_pool, SCREEN)
        except ValueError as exc:
            screen_quota_error = str(exc)
    screen_feasible = screen_capacity >= SCREEN and not screen_quota_error
    new_pool = {}
    if screen_feasible:
        new_pool = filter_pool(
            filter_pool(train_candidates, old_train, 0, overlap_only=True),
            screen_tiles,
            BUFFER_BP,
        )
    new_capacity = sum(map(len, new_pool.values()))
    new_quota_error = None
    new_train = []
    if new_capacity >= NEW_TRAIN:
        try:
            new_train = choose("TRAIN3000_NEW", new_pool, NEW_TRAIN)
        except ValueError as exc:
            new_quota_error = str(exc)
    new_feasible = new_capacity >= NEW_TRAIN and not new_quota_error

    conf_pool = filter_pool(validation_candidates, old_validation, BUFFER_BP)
    conf_capacity = sum(map(len, conf_pool.values()))
    conf_quota_error = None
    conf_tiles = []
    if conf_capacity >= CONF:
        try:
            conf_tiles = choose("CONF", conf_pool, CONF)
        except ValueError as exc:
            conf_quota_error = str(exc)
    conf_feasible = conf_capacity >= CONF and not conf_quota_error
    feasibility = {
        "SCREEN": {
            "requested_tiles": SCREEN,
            "available_tiles": sum(map(len, screen_pool.values())),
            "available_by_chrom": {chrom: len(starts) for chrom, starts in sorted(screen_pool.items())},
            "sufficient": screen_feasible,
            "quota_error": screen_quota_error,
        },
        "TRAIN3000_NEW": {
            "requested_tiles": NEW_TRAIN,
            "available_tiles": sum(map(len, new_pool.values())),
            "available_by_chrom": {chrom: len(starts) for chrom, starts in sorted(new_pool.items())},
            "sufficient": new_feasible,
            "quota_error": new_quota_error,
        },
        "CONF": {
            "requested_tiles": CONF,
            "available_tiles": sum(map(len, conf_pool.values())),
            "available_by_chrom": {chrom: len(starts) for chrom, starts in sorted(conf_pool.items())},
            "sufficient": conf_feasible,
            "quota_error": conf_quota_error,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = []
    if not screen_feasible or not new_feasible:
        blocked_reasons = []
        if not screen_feasible:
            blocked_reasons.append("SCREEN: " + (screen_quota_error or "insufficient eligible coordinates"))
        if not new_feasible:
            blocked_reasons.append("TRAIN3000_NEW: " + (new_quota_error or "insufficient eligible coordinates"))
        manifest.extend(manifest_row("TRAIN1500", tile) for tile in old_train)
        manifest.extend(manifest_row("TRAIN3000", tile) for tile in old_train)
        write_manifest(output_dir / "manifest.tsv", manifest)
        summary = {
            "protocol": "CROSS-SPECIES-L1-UPSTREAM-20260904",
            "status": "BLOCKED",
            "decision": "BLOCKED_SCREEN_OR_TRAIN_COORDINATE_INSUFFICIENCY",
            "reason": "; ".join(blocked_reasons),
            "seed": SEED,
            "tile_bp": TILE_BP,
            "half_bp": HALF_BP,
            "species_code": SPECIES,
            "assembly": ASSEMBLY,
            "selected_train_chromosomes": sorted(train_chroms),
            "selected_validation_chromosomes": sorted(validation_chroms),
            "feasibility": feasibility,
            "training_status": "BLOCKED",
            "conf_status": "CONF_NOT_FEASIBLE" if not conf_feasible else "NOT_REACHED_DUE_TRAINING_BLOCK",
            "roles": {
                "TRAIN1500": role_summary("TRAIN1500", OLD_TRAIN, old_train, old_train_rows),
                "TRAIN3000": role_summary("TRAIN3000", OLD_TRAIN + NEW_TRAIN, old_train, old_train_rows),
                "SCREEN": role_summary("SCREEN", SCREEN, []),
                "CONF": role_summary("CONF", CONF, [], coordinate_only=True),
            },
            "candidate_freeze": False,
            "actual_materialized_files": [],
            "metadata_paths": metadata_paths(root, all_species, table, old),
        }
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return summary

    sequences = {chrom: sequences[chrom] for chrom in train_chroms}
    intervals, rm_stats = parse_rm(
        Path(worm["self_out"]),
        {chrom: len(sequences[chrom]) for chrom in train_chroms},
        train_chroms,
    )
    if rm_stats["out_of_bounds_records"]:
        raise ValueError(f"used Label-A coordinates disagree with FASTA: {rm_stats}")
    new_train_records = new_records(new_train, sequences, intervals)
    screen_records = new_records(screen_tiles, sequences, intervals)
    train_output = output_dir / "TRAIN" / f"{SPECIES}.jsonl.gz"
    screen_output = output_dir / "SCREEN" / f"{SPECIES}.jsonl.gz"
    write_jsonl(train_output, old_train_raw, new_train_records)
    write_jsonl(screen_output, [], screen_records)

    manifest.extend(manifest_row("TRAIN1500", tile) for tile in old_train)
    manifest.extend(manifest_row("TRAIN3000", tile) for tile in old_train + new_train)
    manifest.extend(manifest_row("SCREEN", tile) for tile in screen_tiles)
    if conf_feasible:
        manifest.extend(manifest_row("CONF", tile, coordinate_only=True) for tile in conf_tiles)
    write_manifest(output_dir / "manifest.tsv", manifest)

    checks = {
        "retained_old_train": {"passed": {tile[:3] for tile in old_train} <= {tile[:3] for tile in old_train + new_train}},
        "screen_vs_old_train_gap": check_gap(screen_tiles, old_train, BUFFER_BP),
        "new_train_vs_old_train_nonoverlap": check_nonoverlap(new_train, old_train),
        "new_train_vs_screen_gap": check_gap(new_train, screen_tiles, BUFFER_BP),
        "conf_vs_old_cal_dev_gap": check_gap(conf_tiles, old_validation, BUFFER_BP) if conf_feasible else {"passed": True, "skipped": "CONF_NOT_FEASIBLE"},
    }
    checks["all_passed"] = all(item["passed"] for item in checks.values())
    if not checks["all_passed"]:
        raise ValueError(f"coordinate checks failed: {checks}")
    train_records = old_train_rows + new_train_records
    summary = {
        "protocol": "CROSS-SPECIES-L1-UPSTREAM-20260904",
        "status": "PASS" if conf_feasible else "CONF_NOT_FEASIBLE",
        "decision": "READY_FOR_FUTURE_CONF_FREEZE_AND_SCREEN_DIAGNOSTIC" if conf_feasible else "TRAIN_SCREEN_READY_CONF_NOT_FEASIBLE",
        "seed": SEED,
        "tile_bp": TILE_BP,
        "half_bp": HALF_BP,
        "species_code": SPECIES,
        "assembly": ASSEMBLY,
        "selected_train_chromosomes": sorted(train_chroms),
        "selected_validation_chromosomes": sorted(validation_chroms),
        "reserved_worm_chromosomes": "not retained or materialized",
        "feasibility": feasibility,
        "training_status": "READY",
        "conf_status": "READY_COORDINATE_ONLY" if conf_feasible else "CONF_NOT_FEASIBLE",
        "repeatmasker_stats_used_train_screen": rm_stats,
        "roles": {
            "TRAIN1500": role_summary("TRAIN1500", OLD_TRAIN, old_train, old_train_rows),
            "TRAIN3000": role_summary("TRAIN3000", OLD_TRAIN + NEW_TRAIN, old_train + new_train, train_records),
            "SCREEN": role_summary("SCREEN", SCREEN, screen_tiles, screen_records),
            "CONF": role_summary("CONF", CONF, conf_tiles, None, coordinate_only=True),
        },
        "overlap_checks": checks,
        "candidate_freeze": True,
        "actual_materialized_files": [str(train_output), str(screen_output)],
        "metadata_paths": metadata_paths(root, all_species, table, old),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--species-table", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.output_dir, args.species_table), indent=2))


if __name__ == "__main__":
    main()
