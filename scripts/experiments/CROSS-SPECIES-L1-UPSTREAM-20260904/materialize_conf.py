#!/usr/bin/env python3
"""Materialize the frozen 256-tile CONF panel without selecting new coordinates."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import materialize_upstream as upstream  # noqa: E402


PROTOCOL = "CROSS-SPECIES-L1-UPSTREAM-20260904"
ROLE = "CONF"
SPECIES = "c_elegans"
ASSEMBLY = "ce11"
VALIDATION_CHROM = "chrIV"
EXPECTED_TILES = 256


def read_frozen_conf_tiles(upstream_root: Path) -> list[tuple[str, int, int, str, str]]:
    """Read exactly the CONF rows already frozen by materialization/12306000."""

    manifest = upstream_root / "manifest.tsv"
    with manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = set(upstream.MANIFEST_FIELDS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"CONF manifest missing columns: {', '.join(sorted(missing))}")
        rows = list(reader)

    conf_rows = [row for row in rows if row["role"] == ROLE]
    if len(conf_rows) != EXPECTED_TILES:
        raise ValueError(
            f"frozen CONF manifest must contain {EXPECTED_TILES} rows, found {len(conf_rows)}"
        )

    tiles: list[tuple[str, int, int, str, str]] = []
    seen: set[tuple[str, int, int]] = set()
    for row in conf_rows:
        if (
            row["species_code"] != SPECIES
            or row["assembly"] != ASSEMBLY
            or row["chrom"] != VALIDATION_CHROM
        ):
            raise ValueError("frozen CONF manifest contains a non-c_elegans row")
        if row["split"] != ROLE or row["source"] != "new_conf":
            raise ValueError("frozen CONF row has an unexpected split or source")
        if row["coordinate_only"] != "true":
            raise ValueError("frozen CONF rows must remain coordinate-only in the source manifest")
        if row["sequence_materialized"] != "false" or row["labels_materialized"] != "false":
            raise ValueError("frozen CONF rows must not already contain sequence or labels")
        try:
            start, end = int(row["start"]), int(row["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("frozen CONF row has non-integer coordinates") from exc
        if start < 0 or end - start != upstream.TILE_BP or start % upstream.TILE_BP:
            raise ValueError(f"invalid frozen CONF coordinates: {row['chrom']}:{start}-{end}")
        expected_id = f"{SPECIES}|{ASSEMBLY}|{row['chrom']}:{start}-{end}"
        if row["tile_id"] != expected_id:
            raise ValueError(f"frozen CONF tile_id does not match coordinates: {row['tile_id']}")
        key = (row["chrom"], start, end)
        if key in seen:
            raise ValueError(f"duplicate frozen CONF coordinates: {key}")
        seen.add(key)
        tiles.append((row["chrom"], start, end, ROLE, row["source"]))
    return tiles


def run(root: Path, upstream_root: Path, output_dir: Path) -> dict[str, object]:
    root = root.expanduser()
    upstream_root = upstream_root.expanduser()
    output_dir = output_dir.expanduser()
    if output_dir.exists():
        raise FileExistsError(output_dir)

    tiles = read_frozen_conf_tiles(upstream_root)
    table = root / "scripts/experiments/CROSS-SPECIES-L1-20260903/species_x0_r2.tsv"
    worm, _ = upstream.table_rows(table)
    if worm["assembly"] != ASSEMBLY:
        raise ValueError(f"species table assembly mismatch: {worm['assembly']} != {ASSEMBLY}")

    wanted = {tile[0] for tile in tiles}
    sequences = upstream.read_sequences(Path(worm["fasta"]), wanted)
    missing = wanted - set(sequences)
    if missing:
        raise ValueError(f"frozen CONF contigs absent from FASTA: {', '.join(sorted(missing))}")
    lengths = {chrom: len(sequence) for chrom, sequence in sequences.items()}
    intervals, rm_stats = upstream.parse_rm(Path(worm["self_out"]), lengths, wanted)
    if rm_stats["out_of_bounds_records"]:
        raise ValueError(f"Label-A coordinates disagree with FASTA: {rm_stats}")

    records = upstream.new_records(tiles, sequences, intervals)
    if len(records) != EXPECTED_TILES * 2:
        raise ValueError(f"CONF materialization must contain {EXPECTED_TILES * 2} halves, found {len(records)}")
    if {record["split"] for record in records} != {ROLE}:
        raise ValueError("CONF materialization emitted an unexpected split")

    output_dir.mkdir(parents=True, exist_ok=False)
    output = output_dir / "CONF" / f"{SPECIES}.jsonl.gz"
    upstream.write_jsonl(output, [], records)
    summary = {
        "protocol": PROTOCOL,
        "status": "PASS",
        "role": ROLE,
        "species_code": SPECIES,
        "assembly": ASSEMBLY,
        "chromosome": VALIDATION_CHROM,
        "job_id": output_dir.name,
        "tile_bp": upstream.TILE_BP,
        "half_bp": upstream.HALF_BP,
        "tile_count": EXPECTED_TILES,
        "record_count": len(records),
        "counts": upstream.counts(records),
        "label_contract": {
            "N": "0",
            "P": "1",
            "U": "?",
            "hardN": "H",
            "priority": "P>U>N",
        },
        "selection": {
            "source": str(upstream_root / "manifest.tsv"),
            "manifest_role": ROLE,
            "resampled": False,
            "new_coordinates": False,
        },
        "inputs": {
            "species_table": str(table),
            "fasta": worm["fasta"],
            "repeatmasker": worm["self_out"],
        },
        "repeatmasker_stats": rm_stats,
        "output": str(output),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.upstream_root, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
