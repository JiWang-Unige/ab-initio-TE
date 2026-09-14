#!/usr/bin/env python3
"""Deterministic short-query and coordinate lifting for the D panel comparator."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _read_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    name: str | None = None
    sequence: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(">"):
            if name is not None:
                records.append((name, "".join(sequence)))
            name = line[1:].split()[0]
            sequence = []
        elif name is not None:
            sequence.append(line.strip())
    if name is not None:
        records.append((name, "".join(sequence)))
    return records


def write_short_panel(
    panel: Path,
    regions_json: Path,
    short_panel: Path,
    id_map: Path,
) -> dict[str, Any]:
    """Write four deterministic <=50-character query IDs and their bounds."""
    regions = json.loads(regions_json.read_text(encoding="utf-8"))
    regions_by_id = {str(row["id"]): row for row in regions}
    records = _read_fasta(panel)
    if len(records) != 4 or any(not seq for _, seq in records):
        raise ValueError(f"expected four non-empty frozen panel records, got {len(records)}")
    with short_panel.open("w", encoding="utf-8") as fasta, id_map.open(
        "w", encoding="utf-8"
    ) as mapping:
        mapping.write("short_id\tfrozen_region_id\tfrozen_start_bp\tfrozen_end_bp\n")
        for index, (original, sequence) in enumerate(records, 1):
            if original not in regions_by_id:
                raise ValueError(f"panel FASTA ID absent from frozen region record: {original}")
            region = regions_by_id[original]
            start_bp = int(region["start_bp"])
            end_bp = int(region["end_bp"])
            if end_bp - start_bp != len(sequence):
                raise ValueError(f"panel sequence length disagrees with frozen coordinates: {original}")
            short = f"sea_r{index:02d}"
            fasta.write(f">{short}\n{sequence}\n")
            mapping.write(f"{short}\t{original}\t{start_bp}\t{end_bp}\n")
    return {"records": len(records), "id_map": str(id_map.resolve())}


def lift_repeatmasker_out(raw_out: Path, id_map: Path, mapped_out: Path) -> dict[str, Any]:
    """Map query IDs and lift .out 1-based coordinates to assembly coordinates."""
    mapping: dict[str, tuple[str, int, int]] = {}
    lines = id_map.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:
        short, original, offset, absolute_end = line.split("\t", 3)
        offset = int(offset)
        absolute_end = int(absolute_end)
        if absolute_end <= offset:
            raise ValueError(f"invalid frozen bounds for {short}")
        mapping[short] = (original, offset, absolute_end - offset)
    if len(mapping) != 4:
        raise ValueError(f"expected four short-ID mappings, got {len(mapping)}")

    seen: set[str] = set()
    rows = 0
    with raw_out.open(encoding="utf-8", errors="replace") as source, mapped_out.open(
        "w", encoding="utf-8"
    ) as target:
        for line in source:
            if re.match(r"^\s*\d+\s+", line):
                fields = line.split()
                if len(fields) < 7 or fields[4] not in mapping:
                    raise ValueError(f"annotation row has an unmapped query ID: {line.rstrip()}")
                original, offset, panel_length = mapping[fields[4]]
                begin1, end1 = int(fields[5]), int(fields[6])
                if begin1 < 1 or end1 < begin1 or end1 > panel_length:
                    raise ValueError(f"annotation row is outside its short panel query: {line.rstrip()}")
                lifted_begin = begin1 + offset
                lifted_end = end1 + offset
                if lifted_begin < offset + 1 or lifted_end > offset + panel_length:
                    raise ValueError(f"lifted annotation row exceeds frozen region: {line.rstrip()}")
                fields[4] = original
                fields[5] = str(lifted_begin)
                fields[6] = str(lifted_end)
                target.write(" ".join(fields) + "\n")
                seen.add(original)
                rows += 1
            else:
                target.write(line)
    if rows == 0:
        raise ValueError("RepeatMasker produced no annotation rows")
    return {"rows": rows, "mapped_region_ids": sorted(seen)}
