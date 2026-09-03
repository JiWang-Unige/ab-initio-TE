#!/usr/bin/env python3
"""Materialize the selected X0 8192-bp tiles as paired 4096-bp records."""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
from collections import defaultdict
from pathlib import Path


AUDIT_PATH = Path(__file__).with_name("x0_label_split_audit.py")
AUDIT_SPEC = importlib.util.spec_from_file_location("x0_label_split_audit", AUDIT_PATH)
if AUDIT_SPEC is None or AUDIT_SPEC.loader is None:
    raise ImportError(f"cannot load X0 audit module: {AUDIT_PATH}")
AUDIT = importlib.util.module_from_spec(AUDIT_SPEC)
AUDIT_SPEC.loader.exec_module(AUDIT)


TILE_BP = AUDIT.TILE_BP
HALF_BP = TILE_BP // 2
LABEL_SYMBOLS = {0: "0", 1: "1", 2: "?", 3: "H"}
COHORT_ROLES = ("train", "primary", "replication")
REQUIRED_TABLE_COLUMNS = {
    "species_code",
    "assembly",
    "cohort_role",
    "fasta",
    "self_out",
}
REQUIRED_TILE_COLUMNS = {
    "species_code",
    "assembly",
    "cohort_role",
    "split",
    "chrom",
    "start",
    "end",
    "positive_bp",
    "negative_bp",
    "unknown_bp",
    "hard_negative_bp",
    "callable_bp",
}
ROLE_SPLITS = {
    "train": ("TRAIN", "CAL", "DEV"),
    "primary": ("TEST",),
    "replication": ("TEST",),
}
ROLE_COUNTS = {
    "train": {
        "TRAIN": AUDIT.TRAIN_TILES,
        "CAL": AUDIT.CAL_TILES,
        "DEV": AUDIT.DEV_TILES,
    },
    "primary": {"TEST": AUDIT.TEST_TILES},
    "replication": {"TEST": AUDIT.TEST_TILES},
}


def read_species_rows(path: Path, cohort_role: str) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
        columns = set(reader.fieldnames or ())
    missing = REQUIRED_TABLE_COLUMNS - columns
    if missing:
        raise ValueError(f"species table missing columns: {', '.join(sorted(missing))}")
    if not rows:
        raise ValueError(f"species table has no rows: {path}")

    seen: set[str] = set()
    for row in rows:
        species = row["species_code"]
        if not species:
            raise ValueError("species table has an empty species_code")
        if species in seen:
            raise ValueError(f"duplicate species_code: {species}")
        seen.add(species)
        if row["cohort_role"] not in COHORT_ROLES:
            raise ValueError(f"unsupported cohort_role for {species}: {row['cohort_role']}")

    selected = [row for row in rows if row["cohort_role"] == cohort_role]
    if not selected:
        raise ValueError(f"species table has no rows for cohort_role={cohort_role}")
    for row in selected:
        for field in ("fasta", "self_out"):
            source = Path(row[field])
            if not source.is_file():
                raise FileNotFoundError(source)
    return selected


def _parse_int(row: dict[str, str], field: str, line_number: int) -> int:
    try:
        return int(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"tiles.tsv line {line_number} has non-integer {field}") from exc


def read_tile_rows(
    path: Path, species_rows: list[dict[str, str]], cohort_role: str
) -> dict[str, list[dict[str, object]]]:
    expected_by_species = {row["species_code"]: row for row in species_rows}
    rows_by_species: dict[str, list[dict[str, object]]] = defaultdict(list)
    seen: set[tuple[str, str, str, str, int, int]] = set()

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = REQUIRED_TILE_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"tiles.tsv missing columns: {', '.join(sorted(missing))}")
        for line_number, raw in enumerate(reader, 2):
            species = raw["species_code"]
            if species not in expected_by_species:
                continue
            expected = expected_by_species[species]
            if raw["assembly"] != expected["assembly"]:
                raise ValueError(
                    f"tiles.tsv line {line_number} assembly mismatch for {species}: "
                    f"{raw['assembly']} != {expected['assembly']}"
                )
            if raw["cohort_role"] != cohort_role:
                raise ValueError(
                    f"tiles.tsv line {line_number} cohort_role mismatch for {species}"
                )
            split = raw["split"]
            if split not in ROLE_SPLITS[cohort_role]:
                raise ValueError(f"tiles.tsv line {line_number} invalid split: {split}")

            start = _parse_int(raw, "start", line_number)
            end = _parse_int(raw, "end", line_number)
            if start < 0 or end - start != TILE_BP or start % TILE_BP:
                raise ValueError(f"tiles.tsv line {line_number} invalid 8192 tile coordinates")

            counts: dict[str, int] = {}
            for field in (
                "positive_bp",
                "negative_bp",
                "unknown_bp",
                "hard_negative_bp",
                "callable_bp",
            ):
                counts[field] = _parse_int(raw, field, line_number)
                if counts[field] < 0:
                    raise ValueError(f"tiles.tsv line {line_number} has negative {field}")
            if counts["positive_bp"] + counts["negative_bp"] + counts["unknown_bp"] != TILE_BP:
                raise ValueError(f"tiles.tsv line {line_number} bp counts do not sum to 8192")
            if counts["callable_bp"] != counts["positive_bp"] + counts["negative_bp"]:
                raise ValueError(f"tiles.tsv line {line_number} callable_bp mismatch")
            if counts["hard_negative_bp"] > counts["negative_bp"]:
                raise ValueError(f"tiles.tsv line {line_number} hard_negative_bp exceeds negative_bp")

            key = (species, raw["assembly"], split, raw["chrom"], start, end)
            if key in seen:
                raise ValueError(f"duplicate tile row at line {line_number}: {key}")
            seen.add(key)
            rows_by_species[species].append(
                {
                    "species_code": species,
                    "assembly": raw["assembly"],
                    "cohort_role": raw["cohort_role"],
                    "split": split,
                    "chrom": raw["chrom"],
                    "start": start,
                    "end": end,
                    **counts,
                }
            )

    for species, species_row in expected_by_species.items():
        rows = rows_by_species.get(species, [])
        counts = {split: 0 for split in ROLE_SPLITS[cohort_role]}
        for row in rows:
            counts[row["split"]] += 1
        expected = ROLE_COUNTS[cohort_role]
        if counts != expected:
            raise ValueError(
                f"tiles.tsv counts for {species} do not match X0: {counts} != {expected}"
            )
        rows.sort(key=lambda row: (ROLE_SPLITS[cohort_role].index(row["split"]), row["chrom"], row["start"]))

        by_chrom: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            by_chrom[row["chrom"]].append(row)
        for chrom_rows in by_chrom.values():
            chrom_rows.sort(key=lambda row: row["start"])
            for previous, current in zip(chrom_rows, chrom_rows[1:]):
                if previous["split"] != current["split"] and AUDIT.interval_overlap(
                    (previous["chrom"], previous["start"], previous["end"]),
                    (current["chrom"], current["start"], current["end"]),
                ):
                    raise ValueError(f"coordinate overlap between splits for {species}")
    return dict(rows_by_species)


def _tile_id(species: str, assembly: str, chrom: str, start: int, end: int) -> str:
    return f"{species}|{assembly}|{chrom}:{start}-{end}"


def _paint_tile(sequence: str, chrom: str, start: int, intervals) -> tuple[str, bytearray]:
    piece = sequence[start : start + TILE_BP]
    if len(piece) != TILE_BP:
        raise ValueError(f"FASTA tile is not 8192 bp: {chrom}:{start}")
    labels = bytearray(TILE_BP)
    AUDIT.paint(labels, chrom, start, intervals["hard_negative"], 3)
    for index, base in enumerate(piece):
        if base not in "ACGT":
            labels[index] = 2
    AUDIT.paint(labels, chrom, start, intervals["unknown"], 2)
    AUDIT.paint(labels, chrom, start, intervals["positive"], 1)
    return piece, labels


def _label_string(labels: bytearray) -> str:
    return "".join(LABEL_SYMBOLS[value] for value in labels)


def _check_counts(row: dict[str, object], labels: bytearray) -> dict[str, int]:
    counts = {
        "positive_bp": labels.count(1),
        "unknown_bp": labels.count(2),
        "hard_negative_bp": labels.count(3),
    }
    counts["negative_bp"] = TILE_BP - counts["positive_bp"] - counts["unknown_bp"]
    counts["callable_bp"] = counts["positive_bp"] + counts["negative_bp"]
    for field, value in counts.items():
        if row[field] != value:
            raise ValueError(
                f"recomputed {field} mismatch at {row['species_code']}:{row['chrom']}:{row['start']}: "
                f"{value} != {row[field]}"
            )
    return counts


def materialize_species(
    species_row: dict[str, str], tile_rows: list[dict[str, object]], output_dir: Path
) -> list[dict[str, object]]:
    fasta = Path(species_row["fasta"])
    self_out = Path(species_row["self_out"])
    lengths, _ = AUDIT.fasta_stats(fasta)
    wanted = {row["chrom"] for row in tile_rows}
    missing = wanted - set(lengths)
    if missing:
        raise ValueError(
            f"tiles refer to FASTA contigs absent from {fasta}: {', '.join(sorted(missing))}"
        )
    for row in tile_rows:
        if row["end"] > lengths[row["chrom"]]:
            raise ValueError(
                f"tile exceeds FASTA contig at {row['chrom']}:{row['start']}-{row['end']}"
            )

    intervals, rm_stats = AUDIT.parse_repeatmasker(self_out, lengths, wanted)
    if rm_stats["missing_contig_records"] or rm_stats["out_of_bounds_records"]:
        raise ValueError(f"Label-A coordinates do not agree with FASTA for {species_row['species_code']}: {rm_stats}")

    rows_by_chrom: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in tile_rows:
        rows_by_chrom[row["chrom"]].append(row)
    for chrom_rows in rows_by_chrom.values():
        chrom_rows.sort(key=lambda row: (ROLE_SPLITS[species_row["cohort_role"]].index(row["split"]), row["start"]))

    writers: dict[str, object] = {}
    try:
        for split in ROLE_SPLITS[species_row["cohort_role"]]:
            split_dir = output_dir / split
            split_dir.mkdir(parents=True, exist_ok=True)
            writers[split] = gzip.open(
                split_dir / f"{species_row['species_code']}.jsonl.gz",
                "wt",
                encoding="utf-8",
                newline="\n",
            )

        summary_by_split: dict[str, dict[str, object]] = {
            split: {
                "species_code": species_row["species_code"],
                "assembly": species_row["assembly"],
                "cohort_role": species_row["cohort_role"],
                "split": split,
                "tiles": 0,
                "halves": 0,
                "positive_bp": 0,
                "negative_bp": 0,
                "unknown_bp": 0,
                "hard_negative_bp": 0,
                "callable_bp": 0,
            }
            for split in ROLE_SPLITS[species_row["cohort_role"]]
        }
        seen_chroms: set[str] = set()
        for chrom, sequence in AUDIT.iter_fasta(fasta, wanted):
            seen_chroms.add(chrom)
            for row in rows_by_chrom[chrom]:
                piece, labels = _paint_tile(sequence, chrom, row["start"], intervals)
                counts = _check_counts(row, labels)
                tile_start = row["start"]
                tile_end = row["end"]
                tile_id = _tile_id(
                    species_row["species_code"], species_row["assembly"], chrom, tile_start, tile_end
                )
                writer = writers[row["split"]]
                for half in (0, 1):
                    half_start = tile_start + half * HALF_BP
                    half_end = half_start + HALF_BP
                    record = {
                        "species_code": species_row["species_code"],
                        "assembly": species_row["assembly"],
                        "split": row["split"],
                        "tile_id": tile_id,
                        "half": half,
                        "chrom": chrom,
                        "start": half_start,
                        "end": half_end,
                        "sequence": piece[half * HALF_BP : (half + 1) * HALF_BP],
                        "labels": _label_string(labels[half * HALF_BP : (half + 1) * HALF_BP]),
                    }
                    writer.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
                    summary_by_split[row["split"]]["halves"] += 1
                summary = summary_by_split[row["split"]]
                summary["tiles"] += 1
                for field, value in counts.items():
                    summary[field] += value
        if seen_chroms != wanted:
            missing = wanted - seen_chroms
            raise ValueError(f"FASTA iteration missed selected contigs: {', '.join(sorted(missing))}")
        return list(summary_by_split.values())
    finally:
        for writer in writers.values():
            writer.close()


def write_summary(output_dir: Path, summaries: list[dict[str, object]]) -> None:
    summaries.sort(key=lambda row: (row["species_code"], ROLE_SPLITS[row["cohort_role"]].index(row["split"])))
    fields = [
        "species_code",
        "assembly",
        "cohort_role",
        "split",
        "tiles",
        "halves",
        "positive_bp",
        "negative_bp",
        "unknown_bp",
        "hard_negative_bp",
        "callable_bp",
    ]
    with (output_dir / "summary.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "tile_bp": TILE_BP,
                "half_bp": HALF_BP,
                "label_symbols": {"N": "0", "P": "1", "U": "?", "hardN": "H"},
                "records": summaries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species-table", type=Path, required=True)
    parser.add_argument("--tiles-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cohort-role", choices=COHORT_ROLES, default="train")
    args = parser.parse_args()

    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    species_rows = read_species_rows(args.species_table, args.cohort_role)
    tile_rows = read_tile_rows(args.tiles_tsv, species_rows, args.cohort_role)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    summaries: list[dict[str, object]] = []
    for species_row in species_rows:
        summaries.extend(materialize_species(species_row, tile_rows[species_row["species_code"]], args.output_dir))
    write_summary(args.output_dir, summaries)
    print(json.dumps({"cohort_role": args.cohort_role, "summary": summaries}, indent=2))


if __name__ == "__main__":
    main()
