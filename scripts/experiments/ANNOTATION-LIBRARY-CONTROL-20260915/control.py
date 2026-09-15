#!/usr/bin/env python3
"""Controlled RepeatMasker library comparison on fixed hg19 EVAL tiles.

The annotation pass intentionally knows nothing about model scores.  It
creates one deterministic panel from the already fixed hg19 EVAL tiles and
the two library-specific annotations are run by the Slurm wrapper with the
same RepeatMasker executable and flags.  The score pass joins the resulting
annotations to the frozen confusion and source-only matched-control tables
only after both annotations exist.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


TE_CLASSES = {"SINE", "LINE", "LTR", "DNA", "RC", "RETROPOSON"}
KNOWN_NONTE_CLASSES = {
    "SIMPLE_REPEAT",
    "LOW_COMPLEXITY",
    "SATELLITE",
    "RNA",
    "SNRNA",
    "SCRNA",
    "SRPRNA",
    "TRNA",
    "RRNA",
}
CATEGORIES = ("TE", "UNKNOWN", "NONTE", "UNRECOGNIZED")
LAYERS = (("any", 0.0), ("ge50", 0.50), ("ge80", 0.80))
VALID_STATES = ("TP", "FP", "FN", "TN")
QUALIFIED_STATUS = "UNIQUE_RECIPROCAL_SAME_LENGTH"


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def annotation_category(class_field: str) -> str:
    normalized = class_field.strip().upper()
    base = normalized.split("/", 1)[0]
    if base == "UNKNOWN" or "?" in normalized:
        return "UNKNOWN"
    if base in TE_CLASSES:
        return "TE"
    if base in KNOWN_NONTE_CLASSES:
        return "NONTE"
    return "UNRECOGNIZED"


def parse_tile_id(tile_id: str) -> Tuple[str, int, int]:
    parts = tile_id.split("|")
    if len(parts) != 5 or parts[1] != "hg19":
        raise ValueError(f"unexpected fixed tile id: {tile_id!r}")
    try:
        start, end = int(parts[3]), int(parts[4])
    except ValueError as exc:
        raise ValueError(f"invalid fixed tile coordinates: {tile_id!r}") from exc
    if start < 0 or end <= start:
        raise ValueError(f"invalid fixed tile interval: {tile_id!r}")
    return parts[2], start, end


def load_fixed_tiles(path: Path, config: Mapping[str, object]) -> List[dict]:
    allowed = set(config["allowed_chromosomes"])
    tile_bp = int(config["tile_bp"])
    by_id: Dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 7:
                raise ValueError(f"{path}:{line_no}: expected BED6+tile_id")
            chrom = fields[0]
            if chrom not in allowed:
                continue
            start, end = int(fields[1]), int(fields[2])
            tile_id = fields[6]
            tile_chrom, tile_start, tile_end = parse_tile_id(tile_id)
            if chrom != tile_chrom or start < tile_start or end > tile_end or end <= start:
                raise ValueError(f"{path}:{line_no}: BED row is outside its fixed tile")
            if tile_end - tile_start != tile_bp:
                raise ValueError(f"{path}:{line_no}: tile id length is not {tile_bp}")
            by_id[tile_id] = {
                "tile_id": tile_id,
                "chrom": tile_chrom,
                "tile_start0": tile_start,
                "tile_end": tile_end,
                "tile_bp": tile_end - tile_start,
            }
    tiles = sorted(by_id.values(), key=lambda row: (row["chrom"], row["tile_start0"]))
    expected = config.get("expected_tile_count")
    if expected is not None and len(tiles) != int(expected):
        raise ValueError(f"fixed tile count {len(tiles)} != expected {expected}")
    return tiles


def fasta_records(path: Path, wanted: Iterable[str]) -> Dict[str, str]:
    wanted_set = set(wanted)
    opener = gzip.open if path.name.endswith(".gz") else open
    records: Dict[str, str] = {}
    current: Optional[str] = None
    pieces: List[str] = []
    with opener(path, "rt", encoding="utf-8") as handle:  # type: ignore[arg-type]
        for line in handle:
            if line.startswith(">"):
                if current in wanted_set:
                    records[current] = "".join(pieces).upper()
                current = line[1:].split()[0]
                pieces = []
            elif current in wanted_set:
                pieces.append(line.strip())
        if current in wanted_set:
            records[current] = "".join(pieces).upper()
    missing = wanted_set - set(records)
    if missing:
        raise ValueError(f"FASTA is missing fixed chromosomes: {sorted(missing)}")
    return records


def prepare_panel(config: Mapping[str, object], root: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    tiles = load_fixed_tiles(resolve(root, str(config["old_confusion_intervals"])), config)
    sequences = fasta_records(resolve(root, str(config["source_fasta"])), {r["chrom"] for r in tiles})
    halo = int(config["halo_bp"])
    panel_path = output / "panel.fa"
    panel_table = output / "panel.tsv"
    with panel_path.open("w", encoding="utf-8") as fasta, panel_table.open(
        "w", encoding="utf-8", newline=""
    ) as table_handle:
        fields = [
            "query_id",
            "tile_id",
            "chrom",
            "tile_start0",
            "tile_end",
            "query_start0",
            "query_end",
            "center_offset0",
            "center_end_offset",
            "tile_bp",
        ]
        writer = csv.DictWriter(table_handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for index, tile in enumerate(tiles):
            seq = sequences[tile["chrom"]]
            query_start = max(0, tile["tile_start0"] - halo)
            query_end = min(len(seq), tile["tile_end"] + halo)
            center_offset = tile["tile_start0"] - query_start
            tile["query_start0"] = query_start
            tile["query_end"] = query_end
            tile["center_offset0"] = center_offset
            tile["center_end_offset"] = center_offset + tile["tile_bp"]
            query_id = f"tile{index:04d}"
            query_seq = seq[query_start:query_end]
            if len(query_seq) < tile["tile_bp"]:
                raise ValueError(f"query sequence shorter than center tile: {tile['tile_id']}")
            fasta.write(f">{query_id}\n")
            for offset in range(0, len(query_seq), 80):
                fasta.write(query_seq[offset : offset + 80] + "\n")
            writer.writerow(
                {
                    "query_id": query_id,
                    "tile_id": tile["tile_id"],
                    "chrom": tile["chrom"],
                    "tile_start0": tile["tile_start0"],
                    "tile_end": tile["tile_end"],
                    "query_start0": query_start,
                    "query_end": query_end,
                    "center_offset0": center_offset,
                    "center_end_offset": center_offset + tile["tile_bp"],
                    "tile_bp": tile["tile_bp"],
                }
            )
    manifest = {
        "status": "PANEL_PREPARED",
        "source_assembly": config["source_assembly"],
        "source_fasta": str(resolve(root, str(config["source_fasta"]))),
        "old_confusion_intervals": str(resolve(root, str(config["old_confusion_intervals"]))),
        "tile_count": len(tiles),
        "tile_bp": int(config["tile_bp"]),
        "halo_bp": halo,
        "panel_bp": sum(int(row["query_end"]) - int(row["query_start0"]) for row in tiles),
        "center_bp": sum(int(row["tile_bp"]) for row in tiles),
        "query_count": len(tiles),
        "model_scores_read": False,
        "target_annotation_read": False,
        "libraries_compared_after_same_panel": True,
    }
    (output / "panel_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def read_panel(path: Path) -> Dict[str, dict]:
    rows: Dict[str, dict] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"panel table has no header: {path}")
        for row in reader:
            query_id = row["query_id"]
            if query_id in rows:
                raise ValueError(f"duplicate panel query: {query_id}")
            rows[query_id] = row
    if not rows:
        raise ValueError(f"empty panel table: {path}")
    return rows


def audit_library(path: Path, label: str, output: Path) -> dict:
    """Record FASTA counts without loading the sequences into memory."""
    records = 0
    total_bp = 0
    min_bp: Optional[int] = None
    max_bp: Optional[int] = None
    seen: set[str] = set()
    current_name: Optional[str] = None
    current_len = 0
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:  # type: ignore[arg-type]
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_name is not None:
                    records += 1
                    total_bp += current_len
                    min_bp = current_len if min_bp is None else min(min_bp, current_len)
                    max_bp = current_len if max_bp is None else max(max_bp, current_len)
                current_name = line[1:].split()[0]
                if not current_name:
                    raise ValueError(f"{path}:{line_no}: empty FASTA identifier")
                if current_name in seen:
                    raise ValueError(f"{path}:{line_no}: duplicate FASTA identifier {current_name!r}")
                seen.add(current_name)
                current_len = 0
            else:
                if current_name is None:
                    raise ValueError(f"{path}:{line_no}: sequence precedes FASTA header")
                current_len += len(line)
    if current_name is not None:
        records += 1
        total_bp += current_len
        min_bp = current_len if min_bp is None else min(min_bp, current_len)
        max_bp = current_len if max_bp is None else max(max_bp, current_len)
    if records == 0 or not total_bp:
        raise ValueError(f"empty FASTA library: {path}")
    manifest = {
        "status": "LIBRARY_AUDITED",
        "label": label,
        "path": str(path.resolve()),
        "record_count": records,
        "total_bp": total_bp,
        "min_bp": min_bp,
        "max_bp": max_bp,
        "duplicate_identifiers": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_repeatmasker_out(path: Path, panel: Mapping[str, Mapping[str, str]]) -> Dict[str, Dict[str, List[Tuple[int, int]]]]:
    intervals: Dict[str, Dict[str, List[Tuple[int, int]]]] = {
        query: {category: [] for category in CATEGORIES} for query in panel
    }
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.split()
            if len(fields) < 11 or not fields[0].isdigit():
                continue
            query = fields[4]
            if query not in panel:
                raise ValueError(f"{path}:{line_no}: unknown query id {query!r}")
            try:
                begin1, end1 = int(fields[5]), int(fields[6])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid RepeatMasker coordinates") from exc
            if begin1 < 1 or end1 < begin1:
                raise ValueError(f"{path}:{line_no}: invalid RepeatMasker interval")
            row = panel[query]
            start0, end0 = begin1 - 1, end1
            center_start = int(row["center_offset0"])
            center_end = int(row["center_end_offset"])
            clipped_start = max(start0, center_start)
            clipped_end = min(end0, center_end)
            if clipped_start >= clipped_end:
                continue
            category = annotation_category(fields[10])
            intervals[query][category].append((clipped_start, clipped_end))
    return {query: {category: merge_intervals(values) for category, values in categories.items()} for query, categories in intervals.items()}


def merge_intervals(intervals: Iterable[Tuple[int, int]]) -> List[Tuple[int, int]]:
    merged: List[Tuple[int, int]] = []
    for start, end in sorted(intervals):
        if start < 0 or end <= start:
            raise ValueError(f"invalid interval {start}-{end}")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def overlap_bp(
    intervals: Sequence[Tuple[int, int]],
    start: int,
    end: int,
    starts: Optional[Sequence[int]] = None,
) -> int:
    if end <= start:
        raise ValueError("invalid query interval")
    left_boundaries = starts if starts is not None else [left for left, _ in intervals]
    if len(left_boundaries) != len(intervals):
        raise ValueError("interval start index length does not match intervals")
    index = max(0, bisect.bisect_left(left_boundaries, start) - 1)
    total = 0
    while index < len(intervals):
        left, right = intervals[index]
        if left >= end:
            break
        total += max(0, min(end, right) - max(start, left))
        index += 1
    return total


def parse_qualification(path: Path, allowed: set[str]) -> Dict[str, dict]:
    rows: Dict[str, dict] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"qualification table has no header: {path}")
        required = {"mapping_id", "state", "source_chrom", "source_start0", "source_end", "tile_id", "mapping_status"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"qualification table missing fields: {sorted(missing)}")
        for row_number, row in enumerate(reader, 2):
            if row["source_chrom"] not in allowed:
                continue
            mapping_id = row["mapping_id"]
            if mapping_id in rows:
                raise ValueError(f"duplicate mapping id at row {row_number}: {mapping_id}")
            if row["state"] not in VALID_STATES:
                raise ValueError(f"unexpected state at row {row_number}: {row['state']!r}")
            start, end = int(row["source_start0"]), int(row["source_end"])
            if start < 0 or end <= start:
                raise ValueError(f"invalid source interval at row {row_number}")
            row["source_start0_int"] = start
            row["source_end_int"] = end
            rows[mapping_id] = row
    if not rows:
        raise ValueError(f"empty qualification table: {path}")
    return rows


def parse_old_union(path: Path, allowed: set[str]) -> Dict[str, List[Tuple[int, int]]]:
    raw: MutableMapping[str, List[Tuple[int, int]]] = {chrom: [] for chrom in allowed}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.split()
            if len(fields) < 12:
                continue
            chrom = fields[5]
            if chrom not in allowed:
                continue
            try:
                start, end = int(fields[6]), int(fields[7])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid old comparator coordinates") from exc
            if end <= start or start < 0:
                raise ValueError(f"{path}:{line_no}: invalid old comparator interval")
            if fields[11].strip().upper().split("/", 1)[0] in TE_CLASSES:
                raw[chrom].append((start, end))
    return {chrom: merge_intervals(intervals) for chrom, intervals in raw.items()}


def parse_matches(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"match table has no header: {path}")
        required = {"fp_mapping_id", "control_mapping_id", "match_status", "fp_old_te_relation"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"match table missing fields: {sorted(missing)}")
        for row in reader:
            if row["match_status"] not in {"MATCHED_TN", "UNMATCHED_FP"}:
                raise ValueError(f"unexpected match status: {row['match_status']!r}")
            rows.append(row)
    return rows


def support_record(
    row: Mapping[str, str],
    panel_by_tile: Mapping[str, Mapping[str, str]],
    annotation: Mapping[str, Mapping[str, Sequence[Tuple[int, int]]]],
    old_union: Mapping[str, Sequence[Tuple[int, int]]],
    old_starts: Optional[Mapping[str, Sequence[int]]] = None,
) -> dict:
    tile = panel_by_tile[row["tile_id"]]
    query = tile["query_id"]
    start = int(row["source_start0_int"])
    end = int(row["source_end_int"])
    relative_start = int(tile["center_offset0"]) + (start - int(tile["tile_start0"]))
    relative_end = relative_start + (end - start)
    old_intervals = old_union[row["source_chrom"]]
    old_overlap = overlap_bp(
        old_intervals,
        start,
        end,
        None if old_starts is None else old_starts.get(row["source_chrom"]),
    )
    result = {
        "mapping_id": row["mapping_id"],
        "state": row["state"],
        "source_chrom": row["source_chrom"],
        "source_start0": start,
        "source_end": end,
        "source_length": end - start,
        "tile_id": row["tile_id"],
        "mapping_status": row.get("mapping_status", ""),
        "old_te_overlap_bp": old_overlap,
        "old_te_supported": old_overlap > 0,
    }
    for category in CATEGORIES:
        amount = overlap_bp(annotation[query][category], relative_start, relative_end)
        result[f"{category}_overlap_bp"] = amount
        result[f"{category}_fraction"] = amount / float(end - start)
        for layer, threshold in LAYERS:
            result[f"{category}_{layer}_supported"] = amount >= 1 if layer == "any" else amount / float(end - start) >= threshold
    return result


def bool_count(records: Sequence[Mapping[str, object]], field: str) -> int:
    return sum(bool(record[field]) for record in records)


def aggregate_library(
    records: Sequence[Mapping[str, object]], matches: Sequence[Mapping[str, str]],
    by_id: Mapping[str, Mapping[str, object]], label: str,
) -> dict:
    state_counts = collections.Counter(str(row["state"]) for row in records)
    by_state: Dict[str, dict] = {}
    for category in ("old_te",) + CATEGORIES:
        for layer, _ in LAYERS:
            field = "old_te_supported" if category == "old_te" else f"{category}_{layer}_supported"
            by_state[f"{category}:{layer}"] = {
                state: {
                    "n": sum(1 for row in records if row["state"] == state),
                    "supported": sum(1 for row in records if row["state"] == state and bool(row[field])),
                    "fraction": (
                        sum(1 for row in records if row["state"] == state and bool(row[field]))
                        / float(sum(1 for row in records if row["state"] == state))
                    ) if sum(1 for row in records if row["state"] == state) else None,
                }
                for state in VALID_STATES
            }
    pair_rows: List[dict] = []
    for match in matches:
        fp_id = match["fp_mapping_id"]
        fp = by_id.get(fp_id)
        if fp is None:
            raise ValueError(f"match references missing FP mapping id {fp_id}")
        pair = {
            "fp_mapping_id": fp_id,
            "control_mapping_id": match["control_mapping_id"],
            "match_status": match["match_status"],
            "old_te_relation": match["fp_old_te_relation"],
        }
        for category in ("old_te",) + CATEGORIES:
            for layer, _ in LAYERS:
                suffix = layer
                fp_field = "old_te_supported" if category == "old_te" else f"{category}_{layer}_supported"
                pair[f"fp_{category}_{suffix}"] = bool(fp[fp_field])
                if match["match_status"] == "MATCHED_TN":
                    control = by_id.get(match["control_mapping_id"])
                    if control is None:
                        raise ValueError(f"match references missing control {match['control_mapping_id']}")
                    pair[f"tn_{category}_{suffix}"] = bool(control[fp_field])
        pair_rows.append(pair)
    pair_summary: Dict[str, dict] = {}
    for category in ("old_te",) + CATEGORIES:
        for layer, _ in LAYERS:
            fp_field = f"fp_{category}_{layer}"
            tn_field = f"tn_{category}_{layer}"
            matched = [p for p in pair_rows if p["match_status"] == "MATCHED_TN"]
            pair_summary[f"{category}:{layer}"] = {
                "matched_pairs": len(matched),
                "unmatched_fp": sum(p["match_status"] == "UNMATCHED_FP" for p in pair_rows),
                "fp_supported": sum(bool(p[fp_field]) for p in pair_rows),
                "matched_tn_supported": sum(bool(p[tn_field]) for p in matched),
                "fp_fraction_of_all_cases": (sum(bool(p[fp_field]) for p in pair_rows) / float(len(pair_rows))) if pair_rows else None,
                "tn_fraction_of_matched_pairs": (sum(bool(p[tn_field]) for p in matched) / float(len(matched))) if matched else None,
                "difference_pp": (
                    100.0 * (sum(bool(p[fp_field]) for p in matched) / float(len(matched)) - sum(bool(p[tn_field]) for p in matched) / float(len(matched)))
                    if matched else None
                ),
            }
    transitions = collections.Counter(
        (bool(row["old_te_supported"]), bool(row[f"TE_{layer}_supported"]))
        for row in records for layer, _ in LAYERS
    )
    return {
        "label": label,
        "record_count": len(records),
        "state_counts": dict(state_counts),
        "support_by_state": by_state,
        "source_only_matched_pairs": pair_summary,
        "old_te_to_library_te_transition_counts_repeated_by_layer": {str(key): value for key, value in transitions.items()},
    }


def write_interval_table(path: Path, records: Sequence[Mapping[str, object]]) -> None:
    if not records:
        raise ValueError("cannot write empty interval table")
    fields = list(records[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def score(config: Mapping[str, object], root: Path, panel_dir: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    panel = read_panel(panel_dir / "panel.tsv")
    by_tile = {row["tile_id"]: row for row in panel.values()}
    qualification = parse_qualification(resolve(root, str(config["interval_qualification"])), set(config["allowed_chromosomes"]))
    old_union = parse_old_union(resolve(root, str(config["old_comparator"])), set(config["allowed_chromosomes"]))
    old_starts = {chrom: [left for left, _ in intervals] for chrom, intervals in old_union.items()}
    matches = parse_matches(resolve(root, str(config["matched_controls"])))
    all_records_by_library: Dict[str, List[dict]] = {}
    library_summaries: Dict[str, dict] = {}
    for lib_cfg in config["libraries"]:  # type: ignore[union-attr]
        label = str(lib_cfg["label"])
        annotation_path = resolve(root, str(lib_cfg["annotation_out"]))
        if not annotation_path.is_file():
            raise FileNotFoundError(f"annotation output missing for {label}: {annotation_path}")
        annotation = parse_repeatmasker_out(annotation_path, panel)
        records: List[dict] = []
        for row in qualification.values():
            if row["tile_id"] not in by_tile:
                raise ValueError(f"qualification row references missing tile {row['tile_id']}")
            records.append(support_record(row, by_tile, annotation, old_union, old_starts))
        records.sort(key=lambda row: str(row["mapping_id"]))
        all_records_by_library[label] = records
        write_interval_table(output / f"interval_support.{label}.tsv", records)
        by_id = {str(row["mapping_id"]): row for row in records}
        library_summaries[label] = aggregate_library(records, matches, by_id, label)
    if not all_records_by_library:
        raise ValueError("no libraries configured")
    labels = sorted(all_records_by_library)
    first_label = labels[0]
    second_label = labels[1] if len(labels) > 1 else None
    transition: Optional[dict] = None
    if second_label is not None:
        first = {str(row["mapping_id"]): row for row in all_records_by_library[first_label]}
        second = {str(row["mapping_id"]): row for row in all_records_by_library[second_label]}
        transition = {}
        for category in CATEGORIES:
            for layer, _ in LAYERS:
                field = f"{category}_{layer}_supported"
                counter = collections.Counter((bool(first[k][field]), bool(second[k][field])) for k in first)
                transition[f"{category}:{layer}"] = {str(key): value for key, value in counter.items()}
    summary = {
        "status": "ANNOTATION_LIBRARY_CONTROL_COMPLETED",
        "protocol": config["protocol"],
        "seed": config["seed"],
        "source_assembly": config["source_assembly"],
        "engine_control": config["engine_control"],
        "panel": {
            "query_count": len(panel),
            "tile_bp": config["tile_bp"],
            "halo_bp": config["halo_bp"],
            "center_bp": sum(int(row["tile_bp"]) for row in panel.values()),
            "panel_fasta": str((panel_dir / "panel.fa").resolve()),
        },
        "source_denominator": {
            "all_allowed_interval_rows": len(qualification),
            "state_counts": dict(collections.Counter(row["state"] for row in qualification.values())),
            "matched_control_rows": len(matches),
            "matched_pairs": sum(row["match_status"] == "MATCHED_TN" for row in matches),
            "unmatched_fp": sum(row["match_status"] == "UNMATCHED_FP" for row in matches),
            "selection_source": str(resolve(root, str(config["matched_controls"]))),
            "selection_uses_model_scores": False,
            "selection_uses_new_library_support": False,
        },
        "libraries": library_summaries,
        "library_to_library_transition": transition,
        "external_evidence_layer": {
            "same_sequence_qualification_is_reported": True,
            "source_target_chain_sequence_is_not_biological_truth": True,
            "independent_manual_or_experimental_truth_available": False,
            "new_target_annotation_used_for_selection": False,
        },
        "claim_policy": {
            "same_engine_same_query_panel": True,
            "same_base_f1_computed": False,
            "fp_rescue_claim": False,
            "independent_biological_truth": False,
            "model_scores_read": False,
            "target_annotation_read": False,
            "annotation_support_is_descriptive": True,
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if transition is not None:
        (output / "library_transition.json").write_text(json.dumps(transition, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "STATUS.json").write_text(json.dumps({"status": summary["status"], "libraries": labels}, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--config", type=Path, required=True)
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--config", type=Path, required=True)
    score_parser.add_argument("--root", type=Path, required=True)
    score_parser.add_argument("--panel-dir", type=Path, required=True)
    score_parser.add_argument("--output", type=Path, required=True)
    audit_parser = sub.add_parser("audit-library")
    audit_parser.add_argument("--library", type=Path, required=True)
    audit_parser.add_argument("--label", required=True)
    audit_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        config = json.loads(args.config.read_text(encoding="utf-8"))
        result = prepare_panel(config, args.root.resolve(), args.output.resolve())
    elif args.command == "score":
        config = json.loads(args.config.read_text(encoding="utf-8"))
        result = score(config, args.root.resolve(), args.panel_dir.resolve(), args.output.resolve())
    else:
        result = audit_library(args.library.resolve(), args.label, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
