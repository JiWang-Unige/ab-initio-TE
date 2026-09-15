#!/usr/bin/env python3
"""Build the complete six-species SF5 ontology-closure dataset.

This is a new protocol.  It deliberately reads the existing plus-unknown
RepeatMasker BEDs and keeps the historical window/chromosome allocation, but
uses an explicit status ontology instead of collapsing every non-main class
to ``Unknown``.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import json
from pathlib import Path


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

# This is the exact allocation represented by the historical full metadata.
SPECIES_CHROMS = {
    "mouse": {"train": "chr1", "val": "chr2", "test": "chrX"},
    "zebrafish": {"train": "chr4", "val": "chr7", "test": "chr5"},
    "chicken": {"train": "chr1", "val": "chr2", "test": "chr3"},
    "western_clawed_frog": {"train": "chr1", "val": "chr2", "test": "chr5"},
    "fruit_fly": {"train": "chr3R", "val": "chr3L", "test": "chr2R"},
    "c_elegans": {"train": "chrV", "val": "chrX", "test": "chrIV"},
}
SPLIT_LIMITS = {"train": 900, "val": 240, "test": 360}


def opener(path: str):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path, "rt")


def read_manifest(path: str) -> list[dict[str, str]]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def ontology_label(rep_class: str, rep_family: str = "", rep_name: str = "") -> int:
    """Map source fields to the predeclared 8-label ontology.

    A question mark in the source class or family is retained as an
    ambiguous TE label.  ``Unknown``/``Unspecified`` source records remain
    explicitly unclassified; they are not treated as biological negatives.
    """
    cls = (rep_class or "").strip().upper()
    fam = (rep_family or "").strip().upper()
    if "?" in cls or "?" in fam:
        return 6
    base = cls.split("/", 1)[0].strip().rstrip("?")
    if base in MAIN4:
        return MAIN4[base]
    if base in KNOWN_OTHER:
        return 5
    if not base or base in UNKNOWN or fam in UNKNOWN:
        return 7
    # The input is the repository's TE-plus-unknown export.  An unrecognised
    # class is retained as unresolved rather than silently becoming BG.
    return 7


def load_intervals(path: str, target_chroms: set[str]) -> tuple[dict[str, tuple[list[tuple[int, int, int]], list[int]]], dict]:
    """Load only target chromosomes and return intervals plus source counts."""
    vals: dict[str, list[tuple[int, int, int]]] = collections.defaultdict(list)
    raw_counts: collections.Counter[str] = collections.Counter()
    raw_bp: collections.Counter[str] = collections.Counter()
    with opener(path) as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 3 or fields[0] not in target_chroms:
                continue
            try:
                start, end = int(fields[1]), int(fields[2])
            except ValueError:
                continue
            if end <= start:
                continue
            rep_class = fields[6] if len(fields) > 6 else ""
            rep_family = fields[7] if len(fields) > 7 else ""
            rep_name = fields[3] if len(fields) > 3 else ""
            label = ontology_label(rep_class, rep_family, rep_name)
            raw_key = rep_class or "<EMPTY>"
            raw_counts[raw_key] += 1
            raw_bp[raw_key] += end - start
            vals[fields[0]].append((start, end, label))

    packed: dict[str, tuple[list[tuple[int, int, int]], list[int]]] = {}
    for chrom, items in vals.items():
        # Stable source-independent ordering gives deterministic overwrite
        # behavior for overlapping records.
        items.sort(key=lambda x: (x[0], x[1], x[2]))
        prefix_max_end: list[int] = []
        current = -1
        for _, end, _ in items:
            current = max(current, end)
            prefix_max_end.append(current)
        packed[chrom] = (items, prefix_max_end)
    return packed, {
        "records": int(sum(raw_counts.values())),
        "bp": int(sum(raw_bp.values())),
        "class_records": dict(sorted(raw_counts.items())),
        "class_bp": dict(sorted(raw_bp.items())),
    }


def paint(labels: list[int], start: int, end: int, packed) -> None:
    item = packed
    if not item:
        return
    values, prefix_max_end = item
    idx = bisect.bisect_right(prefix_max_end, start)
    for te_start, te_end, label in values[idx:]:
        if te_start >= end:
            break
        left = max(te_start, start) - start
        right = min(te_end, end) - start
        if right > left:
            labels[left:right] = [label] * (right - left)


def _fasta_lines(path: str):
    with opener(path) as handle:
        current = None
        for raw in handle:
            line = raw.rstrip("\n\r")
            if line.startswith(">"):
                current = line[1:].split()[0]
                yield current, None
            elif current is not None:
                yield current, line.upper()


def write_species(
    row: dict[str, str],
    handles: dict[str, object],
    window: int,
    step: int,
    max_n_frac: float,
) -> dict:
    species = row["species_code"]
    chroms = SPECIES_CHROMS[species]
    intervals, source_stats = load_intervals(row["comparator_plus_unknown"], set(chroms.values()))
    split_stats = {
        split: {
            "chrom": chroms[split],
            "windows": 0,
            "class_bp": collections.Counter(),
        }
        for split in chroms
    }
    seen_targets: set[str] = set()
    current_chrom = None
    buf = ""
    buf_start = 0

    def emit_available(chrom: str):
        nonlocal buf, buf_start
        split = next(name for name, value in chroms.items() if value == chrom)
        stats = split_stats[split]
        limit = SPLIT_LIMITS[split]
        while len(buf) >= window and stats["windows"] < limit:
            piece = buf[:window]
            start = buf_start
            buf = buf[step:]
            buf_start += step
            if piece.count("N") / max(1, window) > max_n_frac:
                continue
            labels = [0] * window
            paint(labels, start, start + window, intervals.get(chrom))
            rec = {
                "sequence": piece,
                "labels": labels,
                "chr": chrom,
                "start": start,
                "end": start + window,
                "species_code": species,
            }
            handles[split].write(json.dumps(rec, separators=(",", ":")) + "\n")
            stats["windows"] += 1
            stats["class_bp"].update(labels)

    for chrom, sequence_line in _fasta_lines(row["genome"]):
        if sequence_line is None:
            if current_chrom in chroms.values():
                emit_available(current_chrom)
            current_chrom = chrom
            buf = ""
            buf_start = 0
            if chrom in chroms.values():
                seen_targets.add(chrom)
            continue
        if current_chrom in chroms.values():
            if split_stats[next(name for name, value in chroms.items() if value == current_chrom)]["windows"] < SPLIT_LIMITS[next(name for name, value in chroms.items() if value == current_chrom)]:
                buf += sequence_line
                emit_available(current_chrom)

    if current_chrom in chroms.values():
        emit_available(current_chrom)

    missing = sorted(set(chroms.values()) - seen_targets)
    if missing:
        raise RuntimeError(f"{species}: target FASTA chromosomes not seen: {missing}")
    short = {
        split: int(stats["windows"])
        for split, stats in split_stats.items()
        if stats["windows"] != SPLIT_LIMITS[split]
    }
    if short:
        raise RuntimeError(f"{species}: exact window quota not met: {short}")
    return {
        "source": source_stats,
        "splits": {
            split: {
                "chrom": stats["chrom"],
                "windows": int(stats["windows"]),
                "class_bp": {
                    ID2LABEL[int(label)]: int(count)
                    for label, count in sorted(stats["class_bp"].items())
                },
            }
            for split, stats in split_stats.items()
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--species", nargs="+", default=list(SPECIES_CHROMS))
    ap.add_argument("--window", type=int, default=4096)
    ap.add_argument("--step", type=int, default=4096)
    ap.add_argument("--max-n-frac", type=float, default=0.2)
    args = ap.parse_args()

    wanted = list(args.species)
    unknown_species = sorted(set(wanted) - set(SPECIES_CHROMS))
    if unknown_species:
        raise SystemExit(f"unsupported species: {unknown_species}")
    rows = {
        row["species_code"]: row
        for row in read_manifest(args.manifest)
        if row.get("split") == "fine_tune" and row.get("species_code") in wanted
    }
    missing = sorted(set(wanted) - set(rows))
    if missing:
        raise SystemExit(f"missing fine_tune rows: {missing}")
    for species, row in rows.items():
        for field in ("genome", "comparator_plus_unknown"):
            if not row.get(field) or not Path(row[field]).exists():
                raise SystemExit(f"{species}: missing {field}: {row.get(field)}")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    handles = {}
    try:
        for split in SPLIT_LIMITS:
            path = out / split / "data.jsonl.gz"
            path.parent.mkdir(parents=True, exist_ok=True)
            handles[split] = gzip.open(path, "wt")
        species_stats = {}
        for species in wanted:
            species_stats[species] = write_species(
                rows[species], handles, args.window, args.step, args.max_n_frac
            )
    finally:
        for handle in handles.values():
            handle.close()

    aggregate = {split: {"windows": 0, "class_bp": collections.Counter()} for split in SPLIT_LIMITS}
    for info in species_stats.values():
        for split, stats in info["splits"].items():
            aggregate[split]["windows"] += stats["windows"]
            aggregate[split]["class_bp"].update(stats["class_bp"])
    metadata = {
        "protocol": "SF5_ONTOLOGY_CLOSURE_20260915",
        "seed": 42,
        "window": args.window,
        "step": args.step,
        "max_n_frac": args.max_n_frac,
        "ontology": {str(k): v for k, v in ID2LABEL.items()},
        "source_mode": "existing_comparator_plus_unknown",
        "source_semantics": (
            "BG is uncovered by the repository TE-plus-unknown comparator; "
            "Unknown/Unspecified source rows are unresolved candidates, not independent truth."
        ),
        "species_order": wanted,
        "species": species_stats,
        "splits": {
            split: {
                "windows": int(stats["windows"]),
                "class_bp": dict(sorted(stats["class_bp"].items())),
                "expected_windows": len(wanted) * SPLIT_LIMITS[split],
            }
            for split, stats in aggregate.items()
        },
    }
    (out / "label_map.json").write_text(json.dumps(metadata["ontology"], indent=2) + "\n")
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
