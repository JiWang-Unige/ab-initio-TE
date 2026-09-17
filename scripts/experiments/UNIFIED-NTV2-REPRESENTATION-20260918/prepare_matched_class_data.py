#!/usr/bin/env python3
"""Attach the frozen eight-state ontology to the exact six-species D windows.

The binary D materialization already contains the sequences, coordinates, and
TRAIN/CAL/DEV split.  This script does not resample or read a new FASTA.  It
replays the SF5 ontology mapping on the corresponding comparator-plus-unknown
BED intervals and writes compact single-character class labels (0--7).  The
result is the only training data used by the matched NTv2 class arm.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import json
from pathlib import Path
from typing import Any


ID2LABEL = {
    0: "BG",
    1: "SINE",
    2: "LINE",
    3: "LTR",
    4: "DNA",
    5: "KNOWN_OTHER_TE",
    6: "AMBIGUOUS_TE",
    7: "UNCLASSIFIED",
}
MAIN4 = {"SINE": 1, "LINE": 2, "LTR": 3, "DNA": 4}
KNOWN_OTHER = {"RC", "RETROPOSON"}
UNKNOWN = {"UNKNOWN", "UNSPECIFIED"}
SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
SOURCE_SPLITS = {"train": "TRAIN", "val": "CAL", "test": "DEV"}


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open("rt", encoding="utf-8")


def ontology_label(rep_class: str, rep_family: str) -> int:
    cls = (rep_class or "").strip().upper()
    fam = (rep_family or "").strip().upper()
    if "?" in cls or "?" in fam:
        return 6
    base = cls.split("/", 1)[0].strip().rstrip("?")
    if base in MAIN4:
        return MAIN4[base]
    if base in KNOWN_OTHER:
        return 5
    # This is deliberately the SF5 policy: unresolved source annotations are
    # retained as UNCLASSIFIED and are not converted into biological BG.
    if not base or base in UNKNOWN or fam in UNKNOWN:
        return 7
    return 7


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    result = {row["species_code"]: row for row in rows}
    missing = sorted(set(SPECIES) - set(result))
    if missing:
        raise ValueError(f"manifest is missing D species: {missing}")
    return result


class IntervalIndex:
    """Sorted BED intervals with the same ordered paint semantics as SF5."""

    def __init__(self, path: Path):
        by_chrom: dict[str, list[tuple[int, int, int]]] = collections.defaultdict(list)
        source_counts: collections.Counter[str] = collections.Counter()
        source_bp: collections.Counter[str] = collections.Counter()
        with open_text(path) as handle:
            for raw in handle:
                if not raw.strip() or raw.startswith("#"):
                    continue
                fields = raw.rstrip("\n\r").split("\t")
                if len(fields) < 3:
                    continue
                try:
                    start, end = int(fields[1]), int(fields[2])
                except ValueError:
                    continue
                if start < 0 or end <= start:
                    continue
                rep_class = fields[6] if len(fields) > 6 else ""
                rep_family = fields[7] if len(fields) > 7 else ""
                label = ontology_label(rep_class, rep_family)
                by_chrom[fields[0]].append((start, end, label))
                source_counts[rep_class or "<EMPTY>"] += 1
                source_bp[rep_class or "<EMPTY>"] += end - start

        self.intervals: dict[str, list[tuple[int, int, int]]] = {}
        self.prefix_max_end: dict[str, list[int]] = {}
        for chrom, values in by_chrom.items():
            # This is the deterministic ordering used by the existing SF5
            # materializer.  Later overlapping rows overwrite earlier rows.
            values.sort(key=lambda item: (item[0], item[1], item[2]))
            current = -1
            prefix: list[int] = []
            for _, end, _ in values:
                current = max(current, end)
                prefix.append(current)
            self.intervals[chrom] = values
            self.prefix_max_end[chrom] = prefix
        self.source_stats = {
            "records": int(sum(source_counts.values())),
            "bp": int(sum(source_bp.values())),
            "class_records": dict(sorted(source_counts.items())),
            "class_bp": dict(sorted(source_bp.items())),
        }

    def paint(self, chrom: str, start: int, length: int) -> list[int]:
        labels = [0] * length
        values = self.intervals.get(chrom, [])
        if not values:
            return labels
        end = start + length
        index = bisect.bisect_right(self.prefix_max_end[chrom], start)
        for item_start, item_end, label in values[index:]:
            if item_start >= end:
                break
            left = max(item_start, start) - start
            right = min(item_end, end) - start
            if right > left:
                labels[left:right] = [label] * (right - left)
        return labels


def read_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            record = json.loads(raw)
            if len(str(record.get("sequence", ""))) != 4096:
                raise ValueError(f"{path}:{line_no}: sequence is not 4096 bp")
            if len(str(record.get("labels", ""))) != 4096:
                raise ValueError(f"{path}:{line_no}: binary labels are not 4096 bp")
            if record.get("species_code") not in SPECIES:
                raise ValueError(f"{path}:{line_no}: unexpected species {record.get('species_code')!r}")
            records.append(record)
    return records


def compact_record(record: dict[str, Any], labels: list[int]) -> dict[str, Any]:
    if any(label < 0 or label > 7 for label in labels):
        raise ValueError("ontology labels must be one digit in 0..7")
    return {
        "sequence": str(record["sequence"]),
        "labels": "".join(str(label) for label in labels),
        "species_code": str(record["species_code"]),
        "assembly": record.get("assembly"),
        "split": SOURCE_SPLITS_INV[str(record["split"])],
        "tile_id": record.get("tile_id"),
        "half": int(record.get("half", 0)),
        "chrom": record.get("chrom"),
        "start": int(record["start"]),
        "end": int(record["end"]),
    }


SOURCE_SPLITS_INV = {value: key for key, value in SOURCE_SPLITS.items()}


def summarize_binary_vs_class(binary: str, class_labels: list[int]) -> dict[str, int]:
    if len(binary) != len(class_labels):
        raise ValueError("binary and class label lengths disagree")
    counts: collections.Counter[str] = collections.Counter()
    for old, new in zip(binary, class_labels):
        old_group = {"1": "binary_TE", "0": "binary_BG", "H": "binary_H", "?": "binary_ignored"}.get(old)
        if old_group is None:
            raise ValueError(f"unexpected binary label {old!r}")
        counts[f"{old_group}__class_{ID2LABEL[new]}"] += 1
    return dict(sorted(counts.items()))


def process_split(
    source_dir: Path,
    output_dir: Path,
    indexes: dict[str, IntervalIndex],
    split: str,
    source_overrides: dict[tuple[str, str], Path],
) -> dict[str, Any]:
    source_split = SOURCE_SPLITS[split]
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate: collections.Counter[str] = collections.Counter()
    per_species: dict[str, dict[str, int]] = {}
    n_records = 0
    out_path = output_dir / "data.jsonl.gz"
    with gzip.open(out_path, "wt", encoding="utf-8", newline="\n") as handle:
        for species in SPECIES:
            source = source_overrides.get(
                (species, source_split), source_dir / source_split / f"{species}.jsonl.gz"
            )
            records = read_records(source)
            if any(str(record["split"]) != source_split for record in records):
                raise ValueError(f"{source}: source split field does not equal {source_split}")
            class_counts: collections.Counter[str] = collections.Counter()
            cross_counts: collections.Counter[str] = collections.Counter()
            for record in records:
                class_labels = indexes[species].paint(
                    str(record["chrom"]), int(record["start"]), len(record["sequence"])
                )
                class_counts.update(ID2LABEL[label] for label in class_labels)
                cross_counts.update(summarize_binary_vs_class(str(record["labels"]), class_labels))
                handle.write(json.dumps(compact_record(record, class_labels), separators=(",", ":")) + "\n")
                n_records += 1
            aggregate.update(class_counts)
            per_species[species] = {
                "records": len(records),
                "class_bp": dict(sorted(class_counts.items())),
                "binary_class_cross_counts": dict(sorted(cross_counts.items())),
            }
    return {
        "source_split": source_split,
        "records": n_records,
        "class_bp": dict(sorted(aggregate.items())),
        "species": per_species,
        "path": str(out_path),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary-data-root", type=Path, required=True)
    ap.add_argument("--source-manifest", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument(
        "--source-override",
        action="append",
        default=[],
        metavar="SPECIES:SPLIT=PATH",
        help="Use an exact D source file for one species/split, e.g. c_elegans:TRAIN=...",
    )
    args = ap.parse_args()
    if (args.out_dir / "metadata.json").exists():
        raise SystemExit(f"refusing to overwrite existing matched class data: {args.out_dir}")
    manifest = read_manifest(args.source_manifest)
    source_overrides: dict[tuple[str, str], Path] = {}
    for raw in args.source_override:
        try:
            key, path = raw.split("=", 1)
            species, source_split = key.split(":", 1)
        except ValueError as exc:
            raise SystemExit(f"invalid --source-override {raw!r}; expected SPECIES:SPLIT=PATH") from exc
        if species not in SPECIES or source_split not in SOURCE_SPLITS_INV:
            raise SystemExit(f"invalid source override key {key!r}")
        source_overrides[(species, source_split)] = Path(path)
    for (species, source_split), path in source_overrides.items():
        if not path.is_file():
            raise FileNotFoundError(f"source override missing for {species}/{source_split}: {path}")
    indexes: dict[str, IntervalIndex] = {}
    source_meta: dict[str, Any] = {}
    for species in SPECIES:
        path = Path(manifest[species]["comparator_plus_unknown"])
        if not path.is_file():
            raise FileNotFoundError(f"{species}: missing comparator_plus_unknown BED: {path}")
        indexes[species] = IntervalIndex(path)
        source_meta[species] = {
            "comparator_plus_unknown": str(path),
            "source_stats": indexes[species].source_stats,
        }

    split_meta = {
        split: process_split(
            args.binary_data_root, args.out_dir / split, indexes, split, source_overrides
        )
        for split in ("train", "val", "test")
    }
    expected = {"train": 21000, "val": 6000, "test": 6000}
    observed = {split: int(meta["records"]) for split, meta in split_meta.items()}
    if observed != expected:
        raise RuntimeError(f"matched class split counts {observed} != {expected}")
    metadata = {
        "schema": "unified_ntv2_matched_class_data_v1",
        "protocol": "UNIFIED-NTV2-REPRESENTATION-20260918",
        "seed": 42,
        "source_binary_data_root": str(args.binary_data_root),
        "source_manifest": str(args.source_manifest),
        "species": list(SPECIES),
        "source_split_map": SOURCE_SPLITS,
        "source_overrides": {
            f"{species}:{source_split}": str(path)
            for (species, source_split), path in sorted(source_overrides.items())
        },
        "window_bp": 4096,
        "step_bp": 4096,
        "label_map": {str(k): value for k, value in ID2LABEL.items()},
        "label_storage": "single_character_digit_string",
        "class_source_policy": "comparator_plus_unknown; unknown/unspecified -> UNCLASSIFIED; question-mark class/family -> AMBIGUOUS_TE; unresolved is never BG",
        "overlap_policy": "sorted by (start,end,label), ordered paint matching SF5 preparation",
        "splits": split_meta,
        "source_meta": source_meta,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / "STATUS").write_text("PREPARED\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "records": observed, "class_bp": {k: v["class_bp"] for k, v in split_meta.items()}}, indent=2))


if __name__ == "__main__":
    main()
