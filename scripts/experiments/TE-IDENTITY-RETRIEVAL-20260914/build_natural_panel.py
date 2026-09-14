#!/usr/bin/env python3
"""Build a small identity-aware human natural-copy panel on a compute node.

The source unit is an annotated, non-overlapping genomic interval from the
RepeatMasker export.  Its ``source_copy_id`` is explicitly coordinate
derived; it is not asserted to be a biological insertion identity.  The
script extracts only the selected intervals, computes whole-panel sequence
homology components while retaining exact family labels, and assigns whole components to
TRAIN/CAL/EVAL.  It never scans a whole genome into memory and never treats a
chromosome as a host.

The output is deliberately small (at most ``max_families * target_per_family``
natural sequences plus one consensus per family) and is suitable as input to
the audit and sequence retrieval scripts.  Heavy use belongs in Slurm; the
login node should only be used for path checks and metadata inspection.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


SEED = 42
CONTRACT_VERSION = "te-identity-retrieval-natural-panel-v1"
TE_CLASSES = {"SINE", "LINE", "LTR", "DNA", "RC", "Retroposon"}
CHUNK = 1 << 20


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open("r", encoding="utf-8")


def parse_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_bed_row(parts: Sequence[str], row_number: int) -> Optional[dict]:
    if len(parts) < 11:
        return None
    try:
        start, end = int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if end <= start:
        return None
    # RepeatMasker BED columns are: chrom, start, end, repName, score,
    # strand, repClass, repFamily, ... .  The exact repeat name is the
    # retrieval family key; repFamily is retained as a broad superfamily
    # context and must never replace a missing exact consensus lookup.
    repeat_name = parts[3].strip()
    superfamily = parts[7].strip()
    repeat_class = parts[6].strip()
    if not repeat_name or repeat_name.lower().startswith("unknown") or "?" in repeat_name:
        return None
    if repeat_class not in TE_CLASSES:
        return None
    divergence = parse_float(parts[10])
    return {
        "row_number": row_number,
        "chrom": parts[0].strip(),
        "start": start,
        "end": end,
        "repeat_name": repeat_name,
        "score": parse_float(parts[4]),
        "strand": parts[5].strip() or ".",
        "repeat_class": repeat_class,
        "family_id": repeat_name,
        "superfamily_id": superfamily,
        "repeat_begin": parts[8].strip(),
        "repeat_end": parts[9].strip(),
        "divergence": divergence,
    }


def load_candidates(bed_path: Path, chromosomes: Set[str], max_divergence: float, min_length: int, max_length: int) -> List[dict]:
    rows = []
    with open_text(bed_path) as handle:
        for row_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            row = parse_bed_row(line.rstrip("\n").split("\t"), row_number)
            if row is None or row["chrom"] not in chromosomes:
                continue
            length = row["end"] - row["start"]
            if length < min_length or length > max_length:
                continue
            if row["divergence"] is not None and row["divergence"] > max_divergence:
                continue
            row["length"] = length
            rows.append(row)
    return rows


def parse_fai(path: Path) -> Dict[str, Tuple[int, int, int, int]]:
    result = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            result[parts[0]] = (int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
    return result


def fetch_sequence(handle, fai: Mapping[str, Tuple[int, int, int, int]], chrom: str, start: int, end: int, strand: str) -> str:
    if chrom not in fai:
        raise ValueError("chromosome absent from FAI: %s" % chrom)
    length, offset, line_bases, line_width = fai[chrom]
    if start < 0 or end > length or start >= end:
        raise ValueError("interval outside FASTA: %s:%d-%d" % (chrom, start, end))
    first_line = start // line_bases
    last_line = (end - 1) // line_bases
    handle.seek(offset + first_line * line_width)
    raw = handle.read((last_line - first_line + 1) * line_width + line_width)
    sequence = b"".join(raw.split())
    sequence = sequence[start % line_bases:start % line_bases + (end - start)].decode("ascii").upper()
    if strand == "-":
        sequence = sequence.translate(str.maketrans("ACGTN", "TGCAN"))[::-1]
    return sequence


def non_overlapping_select(rows: Sequence[dict], max_families: int, target_per_family: int) -> Tuple[List[dict], Dict[str, dict]]:
    by_family: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        by_family[row["family_id"]].append(dict(row))
    ranked_families = sorted(by_family, key=lambda family: (-len(by_family[family]), family))[:max_families]
    selected: List[dict] = []
    diagnostics = {}

    # A single host has one coordinate system.  The panel selection is global
    # across the requested chromosomes, so no overlapping interval is reused.
    occupied: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for family in ranked_families:
        candidates = sorted(
            by_family[family],
            key=lambda row: (-row["length"], row["divergence"] if row["divergence"] is not None else 999.0,
                             row["chrom"], row["start"], row["end"], row["row_number"]),
        )
        kept = []
        for row in candidates:
            if len(kept) >= target_per_family:
                break
            overlaps = any(
                not (row["end"] <= old_start or row["start"] >= old_end)
                for old_start, old_end in occupied[row["chrom"]]
            )
            if overlaps:
                continue
            kept.append(row)
            occupied[row["chrom"]].append((row["start"], row["end"]))
            selected.append(row)
        diagnostics[family] = {
            "candidate_count": len(candidates),
            "selected_count": len(kept),
            "target_count": target_per_family,
            "meets_minimum": len(kept) >= min(30, target_per_family),
        }
    return selected, diagnostics


def kmer_set(sequence: str, k: int = 7) -> Set[str]:
    sequence = sequence.upper()
    if len(sequence) < k:
        return set()
    return {sequence[index:index + k] for index in range(len(sequence) - k + 1) if "N" not in sequence[index:index + k]}


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def union(self, left: int, right: int) -> None:
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[right] = left


def homology_components(
    rows: Sequence[dict], jaccard_threshold: float, k: int = 7, nearby_distance: int = 25
) -> Dict[int, str]:
    """Build whole-panel sequence/locus components for split blocking.

    Components deliberately span exact repeat names when the sequence or
    locus evidence connects them.  They are leakage-control groups only; a
    component is not a biological insertion call.  The locus rule includes
    overlap and a small nearby window to avoid placing adjacent fragments of a
    local homologous region in different roles.
    """

    uf = UnionFind(len(rows))
    signatures = [kmer_set(row["sequence"], k) for row in rows]
    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            first, second = signatures[left], signatures[right]
            sequence_link = False
            if first and second:
                jaccard = len(first & second) / float(len(first | second))
                sequence_link = jaccard >= jaccard_threshold
            locus_link = False
            if rows[left]["chrom"] == rows[right]["chrom"]:
                gap = max(0, max(rows[left]["start"], rows[right]["start"]) - min(rows[left]["end"], rows[right]["end"]))
                locus_link = gap <= nearby_distance
            if sequence_link or locus_link:
                uf.union(left, right)
    roots = sorted({uf.find(index) for index in range(len(rows))})
    root_to_number = {root: number for number, root in enumerate(roots)}
    return {index: "hc|%04d" % root_to_number[uf.find(index)] for index in range(len(rows))}


def assign_component_splits(rows: Sequence[dict], component_ids: Mapping[int, str]) -> Dict[str, str]:
    components = sorted(set(component_ids.values()))
    random.Random(SEED).shuffle(components)
    assignments = {}
    n = len(components)
    train_n = max(1, int(round(n * 0.6))) if n else 0
    cal_n = max(1, int(round(n * 0.2))) if n >= 3 else 0
    if train_n + cal_n >= n and n >= 3:
        cal_n = max(1, n - train_n - 1)
    for index, component in enumerate(components):
        assignments[component] = "train" if index < train_n else "cal" if index < train_n + cal_n else "eval"
    return assignments


def read_consensus(path: Optional[Path], selected_families: Set[str]) -> Tuple[List[dict], dict]:
    if path is None or not path.is_file():
        return [], {"missing_families": sorted(selected_families), "ambiguous_families": [], "exact_matches": []}
    by_name: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    header = None
    sequence_parts: List[str] = []

    def flush() -> None:
        nonlocal header, sequence_parts
        if not header:
            return
        token = header.split()[0]
        token = token[1:] if token.startswith(">") else token
        name, sep, taxonomy = token.partition("#")
        family = taxonomy.split("/", 1)[1] if "/" in taxonomy else ""
        sequence = "".join(sequence_parts).upper()
        if name and sequence:
            by_name[name].append((sequence, family))
        header, sequence_parts = None, []

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                flush()
                header = line
            else:
                sequence_parts.append(line)
    flush()
    records = []
    missing_families = []
    ambiguous_families = []
    exact_matches = []
    for exact_family in sorted(selected_families):
        candidates = by_name.get(exact_family, [])
        if len(candidates) == 1:
            sequence, taxonomy_family = candidates[0]
            records.append({
                "record_id": "consensus|%s" % exact_family,
                "source_kind": "consensus",
                "assembly": "",
                "host_id": "",
                "host_locus": "",
                "source_copy_id": "",
                "homology_component_id": "",
                "family_id": exact_family,
                "family_level": "repeat_name_exact",
                "consensus_superfamily_id": taxonomy_family,
                "split": "",
                "sequence": sequence,
                "sequence_path": "",
                "embedding_path": "",
                "embedding_model_id": "",
                "profile_path": "",
                "origin_id": exact_family,
                "prototype_eligible": "yes",
                "consensus_name": exact_family,
            })
            exact_matches.append(exact_family)
        elif not candidates:
            missing_families.append(exact_family)
        else:
            ambiguous_families.append(exact_family)
    return records, {
        "missing_families": missing_families,
        "ambiguous_families": ambiguous_families,
        "exact_matches": exact_matches,
    }


def write_jsonl(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_selection(path: Path, diagnostics: Mapping[str, Mapping[str, object]], rows: Sequence[dict], component_ids: Mapping[int, str], split_by_component: Mapping[str, str]) -> None:
    by_family = defaultdict(list)
    for index, row in enumerate(rows):
        by_family[row["family_id"]].append(index)
    fields = ["family_id", "candidate_count", "selected_count", "target_count", "component_count", "train_count", "cal_count", "eval_count", "meets_minimum"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for family in sorted(diagnostics):
            indices = by_family[family]
            components = {component_ids[index] for index in indices}
            role_counts = Counter(split_by_component.get(component, "") for component in components)
            writer.writerow({
                "family_id": family,
                "candidate_count": diagnostics[family]["candidate_count"],
                "selected_count": diagnostics[family]["selected_count"],
                "target_count": diagnostics[family]["target_count"],
                "component_count": len(components),
                "train_count": role_counts.get("train", 0),
                "cal_count": role_counts.get("cal", 0),
                "eval_count": role_counts.get("eval", 0),
                "meets_minimum": diagnostics[family]["meets_minimum"],
            })


def write_fasta(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(">%s\n%s\n" % (row["record_id"], row["sequence"]))


def run(args: argparse.Namespace) -> dict:
    root = Path(args.te_final_root)
    assembly_root = root / "genome_data" / "animals" / args.assembly
    bed_path = Path(args.bed) if args.bed else assembly_root / "rmsk_te.bed.gz"
    fasta_path = Path(args.fasta) if args.fasta else assembly_root / (args.assembly + ".fa")
    fai_path = Path(args.fai) if args.fai else Path(str(fasta_path) + ".fai")
    if not bed_path.is_file() or not fasta_path.is_file() or not fai_path.is_file():
        raise FileNotFoundError("required bed/fasta/fai missing: %s %s %s" % (bed_path, fasta_path, fai_path))
    chromosomes = set(args.chromosomes)
    candidates = load_candidates(bed_path, chromosomes, args.max_divergence, args.min_length, args.max_length)
    selected, diagnostics = non_overlapping_select(candidates, args.max_families, args.target_per_family)
    if not selected:
        raise RuntimeError("no natural intervals survived the panel filters")
    fai = parse_fai(fai_path)
    with fasta_path.open("rb") as handle:
        for row in selected:
            row["sequence"] = fetch_sequence(handle, fai, row["chrom"], row["start"], row["end"], row["strand"])
    component_ids = homology_components(selected, args.homology_jaccard, args.kmer_size, args.nearby_distance)
    split_by_component = assign_component_splits(selected, component_ids)

    host_id = "%s:%s" % (args.species, args.assembly)
    natural_rows = []
    for index, row in enumerate(selected):
        component = component_ids[index]
        natural_rows.append({
            "record_id": "interval|%s|%s|%d|%d|%s|%d" % (
                args.assembly, row["chrom"], row["start"], row["end"], row["strand"], row["row_number"]
            ),
            "source_kind": "natural_copy",
            "assembly": args.assembly,
            "host_id": host_id,
            "host_locus": row["chrom"],
            "source_copy_id": "coord|%s|%s|%d|%d|%s|%d" % (
                host_id, row["chrom"], row["start"], row["end"], row["strand"], row["row_number"]
            ),
            "homology_component_id": component,
            "family_id": row["family_id"],
            "family_level": "repeat_name_exact",
            "superfamily_id": row["superfamily_id"],
            "repeat_class": row["repeat_class"],
            "repeat_name": row["repeat_name"],
            "strand": row["strand"],
            "divergence": row["divergence"],
            "repeat_begin": row["repeat_begin"],
            "repeat_end": row["repeat_end"],
            "split": split_by_component[component],
            "sequence": row["sequence"],
            "sequence_path": "",
            "embedding_path": "",
            "embedding_model_id": "",
            "profile_path": "",
            "origin_id": "rmsk_te_row|%d" % row["row_number"],
            "prototype_eligible": "yes",
            "identity_level": "coordinate_derived_annotated_interval",
            "biological_insertion_id": "",
            "sequence_origin": "genome_interval_extracted",
        })
    selected_families = {row["family_id"] for row in natural_rows}
    consensus_rows, consensus_audit = read_consensus(Path(args.consensus_fasta) if args.consensus_fasta else None, selected_families)
    manifest_rows = natural_rows + consensus_rows
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "identity_manifest.jsonl", manifest_rows)
    write_fasta(out_dir / "selected_sequences.fa", manifest_rows)
    write_selection(out_dir / "family_selection.tsv", diagnostics, selected, component_ids, split_by_component)
    component_counter = Counter(component_ids.values())
    family_components = defaultdict(set)
    for index, row in enumerate(selected):
        family_components[row["family_id"]].add(component_ids[index])
    family_roles = {
        family: Counter(split_by_component.get(component, "") for component in components)
        for family, components in sorted(family_components.items())
    }
    complete_families = [
        family for family, info in diagnostics.items()
        if info["selected_count"] >= args.min_intervals
    ]
    component_isolated_families = [
        family for family, roles in family_roles.items()
        if all(roles.get(role, 0) > 0 for role in ("train", "cal", "eval"))
    ]
    status = {
        "status": "PASS_ENGINEERING_PANEL" if len(complete_families) else "NOTRUN_NO_FAMILY_MEETS_MINIMUM",
        "scientific_claim_status": "NOTRUN",
        "contract_version": CONTRACT_VERSION,
        "seed": SEED,
        "assembly": args.assembly,
        "host_id": host_id,
        "host_loci": sorted(chromosomes),
        "source_kind": "natural_copy_coordinate_derived_interval",
        "natural_rows": len(natural_rows),
        "consensus_rows": len(consensus_rows),
        "consensus_exact_match_audit": consensus_audit,
        "families_selected": len(diagnostics),
        "families_meeting_minimum": len(complete_families),
        "families_with_component_isolated_train_cal_eval": len(component_isolated_families),
        "component_count": len(component_counter),
        "homology": {
            "method": "whole-panel pairwise k-mer Jaccard plus same-locus nearby/overlap connected components",
            "k": args.kmer_size,
            "jaccard_threshold": args.homology_jaccard,
            "nearby_distance": args.nearby_distance,
            "interpretation": "split-blocking homology component; not biological insertion truth",
        },
        "filters": {
            "max_families": args.max_families,
            "target_per_family": args.target_per_family,
            "min_intervals": args.min_intervals,
            "max_divergence": args.max_divergence,
            "min_length": args.min_length,
            "max_length": args.max_length,
            "panel_nonoverlap": True,
        },
        "family_selection": str(out_dir / "family_selection.tsv"),
        "identity_policy": {
            "source_copy_id": "coordinate-derived annotated interval; never called biological insertion ID",
            "host_id": "genome identity; host_locus stores chromosome",
            "empty_biological_insertion_id": "unknown and not used as positive truth",
        },
        "no_go_conditions": {
            "families_without_minimum": sorted(set(diagnostics) - set(complete_families)),
            "families_without_component_isolated_roles": sorted(set(diagnostics) - set(component_isolated_families)),
        },
        "paths": {
            "bed": str(bed_path),
            "fasta": str(fasta_path),
            "fai": str(fai_path),
            "consensus": str(args.consensus_fasta) if args.consensus_fasta else None,
        },
        "outputs": ["identity_manifest.jsonl", "selected_sequences.fa", "family_selection.tsv", "panel_status.json"],
    }
    write_json(out_dir / "panel_status.json", status)
    return status


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--te-final-root", required=True)
    parser.add_argument("--assembly", default="hg38")
    parser.add_argument("--species", default="human")
    parser.add_argument("--chromosomes", nargs="+", default=["chr1", "chr11", "chr13"])
    parser.add_argument("--bed")
    parser.add_argument("--fasta")
    parser.add_argument("--fai")
    parser.add_argument("--consensus-fasta")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-families", type=int, default=40)
    parser.add_argument("--target-per-family", type=int, default=40)
    parser.add_argument("--min-intervals", type=int, default=30)
    parser.add_argument("--max-divergence", type=float, default=20.0)
    parser.add_argument("--min-length", type=int, default=80)
    parser.add_argument("--max-length", type=int, default=10000)
    parser.add_argument("--kmer-size", type=int, default=7)
    parser.add_argument("--homology-jaccard", type=float, default=0.70)
    parser.add_argument("--nearby-distance", type=int, default=25)
    args = parser.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
