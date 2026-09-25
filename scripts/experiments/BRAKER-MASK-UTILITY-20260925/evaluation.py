#!/usr/bin/env python3
"""Prepare and score the bounded BRAKER application evaluation.

The preparation step is deliberately independent of BRAKER predictions.  It
freezes the chromosome domains and the complete RefSeq CDS-chain denominator
before any GTF is read.  The score step can then be run once per BRAKER mask or
with several ``--arm NAME=GTF`` arguments.  Coordinates in the manifest and in
the internal representation are zero-based, half-open.

The CDS-chain normalization follows the semantics of the historical
``P3-TIBERIUS-BASE-MASK``/``NONMAMMAL-GENE-UTILITY`` scorer: coding portions of
complete genePredExtended records are normalized in genomic order, and loci
are connected components of transcript spans for one (chromosome, strand,
name2) key.  This small local implementation avoids importing the optional
NumPy dependency of the old scorer on a preparation node.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import random
import re
import shutil
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Set, Tuple


ROOT = Path(__file__).resolve().parents[3]
NAME = "BRAKER-MASK-UTILITY-20260925"
DEFAULT_OUT = ROOT / "outputs" / NAME / "evaluation"
LONG_READ_URL = (
    "https://raw.githubusercontent.com/crystalBo/zebrafish_full-length_iso-seq/"
    "f5a23b0baed4c3032b7615d279f6c5d0da71d2b5/merge.annotated.gtf.gz"
)
LONG_READ_BYTES = 5921281
EXON_FEATURES = {"exon"}


@dataclass(frozen=True, order=True)
class Chain:
    strand: str
    intervals: Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class RefIsoform:
    transcript_id: str
    gene_id: str
    chrom: str
    strand: str
    tx_start: int
    tx_end: int
    cds_start: int
    cds_end: int
    chain: Chain
    source_line: int


@dataclass(frozen=True)
class Region:
    chrom: str
    start: int
    end: int
    kind: str
    region_id: str


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    tmp.replace(path)


def normalize(intervals: Iterable[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
    """Normalize genomic intervals as the existing gene-locus scorer does."""
    result: List[Tuple[int, int]] = []
    for start, end in sorted(set(intervals)):
        if start < 0 or end <= start:
            raise ValueError("invalid interval")
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    if not result:
        raise ValueError("empty interval chain")
    return tuple(result)


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open(encoding="utf-8")


def parse_attrs(attrs: str) -> Dict[str, str]:
    """Parse the GTF attributes used by BRAKER and the long-read source."""
    result: Dict[str, str] = {}
    for match in re.finditer(r"([A-Za-z_][\w.-]*)\s+(?:\"([^\"]*)\"|([^;\s]+))", attrs):
        result[match.group(1)] = match.group(2) if match.group(2) is not None else match.group(3)
    return result


def path_from_config(root: Path, species: str) -> Dict[str, Path]:
    """Resolve the already-existing evaluation inputs without downloading them."""
    utility = json.loads((root / "configs/NONMAMMAL-GENE-UTILITY-20260918.json").read_text())
    whole = json.loads((root / "configs/WHOLE-GENOME-BENCHMARK-20260918.json").read_text())
    assembly = utility["species"][species]["assembly"]
    old = root / "outputs/NONMAMMAL-GENE-UTILITY-20260918" / species
    report_old = root / "reports/NONMAMMAL-GENE-UTILITY-20260918" / species
    genome_value = whole["species"][species]["fasta"]
    genome = Path(genome_value)
    if not genome.is_absolute():
        genome = root / genome
    candidates = {
        "genome": genome,
        "refseq": old / "ncbiRefSeq.txt.gz",
        "geometry": old / "geometry.json",
    }
    if not candidates["refseq"].exists():
        candidates["refseq"] = report_old / "ncbiRefSeq.txt.gz"
    if not candidates["geometry"].exists():
        candidates["geometry"] = report_old / "geometry.json"
    for key, path in candidates.items():
        if not path.exists():
            raise FileNotFoundError(f"missing {key} input for {species}: {path}")
    candidates["whole_config"] = root / "configs/WHOLE-GENOME-BENCHMARK-20260918.json"
    candidates["assembly"] = Path(assembly)
    return candidates


def fasta_lengths(path: Path) -> Dict[str, int]:
    """Read lengths from .fai where available, otherwise stream the FASTA."""
    fai = Path(str(path) + ".fai")
    if fai.exists():
        result = {}
        for line in fai.read_text().splitlines():
            fields = line.split("\t")
            if len(fields) < 2:
                raise ValueError("malformed FASTA index row")
            result[fields[0]] = int(fields[1])
        return result
    lengths: Dict[str, int] = {}
    current: Optional[str] = None
    size = 0
    with path.open(encoding="ascii") as handle:
        for line in handle:
            if line.startswith(">"):
                if current is not None:
                    lengths[current] = size
                current = line[1:].split()[0]
                size = 0
            else:
                size += len(line.strip())
    if current is not None:
        lengths[current] = size
    return lengths


def numeric_autosomes(lengths: Mapping[str, int]) -> List[str]:
    names = [name for name in lengths
             if re.fullmatch(r"chr[0-9]+", name) and int(name[3:]) >= 1]
    return sorted(names, key=lambda name: int(name[3:]))


def subtract_regions(chrom: str, length: int, excluded: Sequence[Tuple[int, int]], kind: str) -> List[Region]:
    clipped = []
    for left, right in excluded:
        left, right = max(0, left), min(length, right)
        if left < right:
            clipped.append((left, right))
    merged: List[Tuple[int, int]] = []
    for left, right in sorted(clipped):
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    result: List[Region] = []
    cursor = 0
    index = 0
    for left, right in merged:
        if cursor < left:
            result.append(Region(chrom, cursor, left, kind, f"{kind}-{index:05d}"))
            index += 1
        cursor = max(cursor, right)
    if cursor < length:
        result.append(Region(chrom, cursor, length, kind, f"{kind}-{index:05d}"))
    return result


def region_rows(regions: Sequence[Region]) -> List[Dict[str, object]]:
    return [{"region_id": r.region_id, "chrom": r.chrom, "start": r.start, "end": r.end,
             "length": r.end - r.start, "kind": r.kind} for r in regions]


def write_regions(path: Path, regions: Sequence[Region]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["region_id", "chrom", "start", "end", "length", "kind"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(region_rows(regions))


def parse_geometry(path: Path) -> List[Dict[str, object]]:
    rows = json.loads(path.read_text())
    if not isinstance(rows, list) or not rows:
        raise ValueError("old utility geometry must be a non-empty list")
    result = []
    for row in rows:
        required = ("chrom", "halo_start", "halo_end")
        if any(key not in row for key in required):
            raise ValueError("old geometry is missing halo coordinates")
        start, end = int(row["halo_start"]), int(row["halo_end"])
        if start < 0 or end <= start:
            raise ValueError("invalid old geometry halo")
        result.append({**row, "halo_start": start, "halo_end": end})
    return result


def parse_refseq(path: Path, autosomes: Set[str], regions: Sequence[Region], domain: str) -> Tuple[List[RefIsoform], Counter]:
    """Read complete coding genePredExtended isoforms for one domain."""
    allowed = defaultdict(list)
    for region in regions:
        allowed[region.chrom].append((region.start, region.end))
    rows: List[RefIsoform] = []
    excluded = Counter()
    with gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 16:
                raise ValueError(f"genePredExtended line {line_no}: expected 16 fields")
            chrom, strand = fields[2], fields[3]
            if chrom not in autosomes:
                excluded["non_autosome"] += 1
                continue
            tx_start, tx_end, cds_start, cds_end, exon_count = map(int, fields[4:9])
            starts = [int(value) for value in fields[9].rstrip(",").split(",") if value]
            ends = [int(value) for value in fields[10].rstrip(",").split(",") if value]
            frames = [int(value) for value in fields[15].rstrip(",").split(",") if value]
            if strand not in ("+", "-") or not (0 <= tx_start < tx_end and tx_start <= cds_start <= cds_end <= tx_end):
                raise ValueError(f"invalid genePred coordinates at line {line_no}")
            if not (exon_count > 0 and len(starts) == len(ends) == len(frames) == exon_count):
                raise ValueError(f"genePred exon/frame mismatch at line {line_no}")
            if cds_start == cds_end or fields[13] != "cmpl" or fields[14] != "cmpl":
                excluded["noncoding_or_incomplete"] += 1
                continue
            pieces = []
            for start, end, frame in zip(starts, ends, frames):
                if not (tx_start <= start < end <= tx_end):
                    raise ValueError(f"invalid exon interval at line {line_no}")
                left, right = max(start, cds_start), min(end, cds_end)
                if left < right:
                    if frame not in (0, 1, 2):
                        raise ValueError(f"invalid coding frame at line {line_no}")
                    pieces.append((left, right))
            chain = Chain(strand, normalize(pieces))
            if not _chain_in_regions(chrom, chain, allowed):
                excluded["outside_" + domain] += 1
                continue
            rows.append(RefIsoform(fields[1], fields[12] or fields[1], chrom, strand,
                                   tx_start, tx_end, cds_start, cds_end, chain, line_no))
    return rows, excluded


def _chain_in_regions(chrom: str, chain: Chain, allowed: Mapping[str, Sequence[Tuple[int, int]]]) -> bool:
    intervals = allowed.get(chrom, ())
    # A CDS chain is one contiguous biological unit for this endpoint.  Testing
    # each exon independently could admit a chain whose intron crosses a
    # removed old-halo interval; the complete span must fit one allowed region.
    return any(left <= chain.intervals[0][0] and chain.intervals[-1][1] <= right
               for left, right in intervals)


def locus_report(isoforms: Sequence[RefIsoform], source: str, domain: str, excluded: Mapping[str, int]) -> Dict[str, object]:
    grouped: Dict[Tuple[str, str, str], List[RefIsoform]] = defaultdict(list)
    for iso in isoforms:
        grouped[(iso.chrom, iso.strand, iso.gene_id)].append(iso)
    candidates: List[Dict[str, object]] = []
    disjoint = []
    for (chrom, strand, gene_id), values in sorted(grouped.items()):
        components: List[List[RefIsoform]] = []
        current_end = -1
        for iso in sorted(values, key=lambda row: (row.tx_start, row.tx_end, row.transcript_id)):
            if components and iso.tx_start > current_end:
                components.append([])
            elif not components:
                components.append([])
            components[-1].append(iso)
            current_end = max(current_end, iso.tx_end)
        if len(components) > 1:
            disjoint.append({"chrom": chrom, "strand": strand, "gene_id": gene_id, "loci": len(components)})
        for component in components:
            lo = min(iso.tx_start for iso in component)
            hi = max(iso.tx_end for iso in component)
            unit_id = f"{chrom}|{strand}|{gene_id}|{lo}-{hi}"
            unit = {
                "candidate_unit_id": unit_id, "chrom": chrom, "strand": strand, "gene_id": gene_id,
                "span": [lo, hi], "transcript_ids": sorted({iso.transcript_id for iso in component}),
                "isoforms": [{"transcript_id": iso.transcript_id,
                              "intervals": [list(value) for value in iso.chain.intervals],
                              "source_line": iso.source_line}
                             for iso in sorted(component, key=lambda row: row.transcript_id)],
            }
            candidates.append(unit)

    # RefSeq can expose one exact CDS chain under multiple gene-name aliases
    # or transcript records.  Treating those aliases as independent loci would
    # make the exact-chain lookup ambiguous and would count one biological
    # chain twice.  Union candidates connected by an exact chain, preserving
    # every raw gene/transcript/source-line identifier in the merged unit.
    parent = list(range(len(candidates)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left, right = find(left), find(right)
        if left != right:
            parent[right] = left

    chain_candidates: Dict[Tuple[str, str, Tuple[Tuple[int, int], ...]], List[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        for iso in candidate["isoforms"]:
            chain = tuple(tuple(value) for value in iso["intervals"])
            chain_candidates[(candidate["chrom"], candidate["strand"], chain)].append(index)
    duplicate_chain_merges = []
    for key, indexes in sorted(chain_candidates.items()):
        indexes = sorted(set(indexes))
        if len(indexes) <= 1:
            continue
        for index in indexes[1:]:
            union(indexes[0], index)
        isoforms_for_key = []
        for index in indexes:
            candidate = candidates[index]
            isoforms_for_key.extend({
                "gene_id": candidate["gene_id"], "candidate_unit_id": candidate["candidate_unit_id"],
                "transcript_id": iso["transcript_id"], "source_line": iso.get("source_line")}
                for iso in candidate["isoforms"]
                if tuple(tuple(value) for value in iso["intervals"]) == key[2])
        duplicate_chain_merges.append({"chrom": key[0], "strand": key[1],
                                       "cds_intervals": [list(value) for value in key[2]],
                                       "candidate_count": len(indexes),
                                       "candidate_unit_ids": [candidates[i]["candidate_unit_id"] for i in indexes],
                                       "gene_ids": sorted({candidates[i]["gene_id"] for i in indexes}),
                                       "isoforms": sorted(isoforms_for_key, key=lambda row: (row["gene_id"], row["transcript_id"]))})

    merged: Dict[int, List[Dict[str, object]]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        merged[find(index)].append(candidate)
    units: List[Dict[str, object]] = []
    chain_to_unit: Dict[Tuple[str, str, Tuple[Tuple[int, int], ...]], str] = {}
    for group in sorted(merged.values(), key=lambda values: (values[0]["chrom"], values[0]["span"][0], values[0]["gene_id"])):
        raw_gene_ids = sorted({candidate["gene_id"] for candidate in group})
        chrom, strand = group[0]["chrom"], group[0]["strand"]
        lo = min(candidate["span"][0] for candidate in group)
        hi = max(candidate["span"][1] for candidate in group)
        merged_group = len(group) > 1
        if merged_group:
            unit_id = f"{chrom}|{strand}|merged({'+'.join(raw_gene_ids)})|{lo}-{hi}"
        else:
            unit_id = group[0]["candidate_unit_id"]
        all_isoforms = []
        for candidate in group:
            all_isoforms.extend(candidate["isoforms"])
        unique_isoforms = {(iso["transcript_id"], tuple(tuple(value) for value in iso["intervals"])): iso
                           for iso in all_isoforms}
        unit = {
            "unit_id": unit_id, "chrom": chrom, "strand": strand,
            "gene_id": ";".join(raw_gene_ids), "raw_gene_ids": raw_gene_ids,
            "merged_gene_id_count": len(raw_gene_ids), "merged_from_unit_count": len(group),
            "merge_reason": "same_exact_cds_chain_across_gene_ids" if merged_group else None,
            "merged_from_unit_ids": sorted(candidate["candidate_unit_id"] for candidate in group),
            "span": [lo, hi],
            "transcript_ids": sorted({iso["transcript_id"] for iso in unique_isoforms.values()}),
            "isoforms": [unique_isoforms[key] for key in sorted(unique_isoforms)],
        }
        units.append(unit)
        for iso in unit["isoforms"]:
            chain = tuple(tuple(value) for value in iso["intervals"])
            key = (chrom, strand, chain)
            if key in chain_to_unit and chain_to_unit[key] != unit_id:
                raise ValueError("complete RefSeq CDS chain maps to multiple merged loci")
            chain_to_unit[key] = unit_id
    return {"domain": domain, "reference_source": source,
            "unit_definition": "(chrom,strand,name2), connected complete-coding transcript-span locus; exact duplicate CDS chains across aliases merged",
            "isoform_count": len(isoforms), "unit_count": len(units), "units": units,
            "chain_to_unit": {json.dumps([key[0], key[1], [list(v) for v in key[2]]]): value
                               for key, value in chain_to_unit.items()},
            "excluded_transcript_rows": dict(excluded), "disjoint_name2_keys_split": disjoint,
            "exact_chain_alias_merge_count": len(duplicate_chain_merges),
            "exact_chain_alias_merged_candidate_loci": sum(max(0, row["candidate_count"] - 1) for row in duplicate_chain_merges),
            "exact_chain_alias_merges": duplicate_chain_merges}


def ref_mapping(report: Mapping[str, object]) -> Dict[Tuple[str, str, Tuple[Tuple[int, int], ...]], str]:
    mapping = {}
    for unit in report["units"]:
        for iso in unit["isoforms"]:
            key = (unit["chrom"], unit["strand"], tuple(tuple(value) for value in iso["intervals"]))
            if key in mapping and mapping[key] != unit["unit_id"]:
                raise ValueError("ambiguous reference mapping")
            mapping[key] = unit["unit_id"]
    return mapping


def chain_introns(intervals: Sequence[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
    return tuple((left[1], right[0]) for left, right in zip(intervals, intervals[1:]) if left[1] < right[0])


def prepare_reference(root: Path, species: str, out: Path) -> Dict[str, object]:
    paths = path_from_config(root, species)
    lengths = fasta_lengths(paths["genome"])
    autosomes = numeric_autosomes(lengths)
    if not autosomes:
        raise ValueError("no chrN autosomes found in the assembly")
    full = [Region(chrom, 0, lengths[chrom], "full_autosome", f"full-{index:05d}")
            for index, chrom in enumerate(autosomes)]
    whole_cfg = json.loads(paths["whole_config"].read_text())
    exposure = whole_cfg["d_exposure_audit"]["exposure_chromosomes"][species]
    excluded_chromosomes = sorted(set(exposure["train"]) | set(exposure["calibration"]))
    geometry = parse_geometry(paths["geometry"])
    halo_by_chrom = defaultdict(list)
    for row in geometry:
        halo_by_chrom[row["chrom"]].append((row["halo_start"], row["halo_end"]))
    primary: List[Region] = []
    for chrom in autosomes:
        if chrom in excluded_chromosomes:
            continue
        primary.extend(subtract_regions(chrom, lengths[chrom], halo_by_chrom[chrom], "primary"))
    exclusions = []
    for chrom in excluded_chromosomes:
        if chrom in lengths:
            exclusions.append({"kind": "D_train_or_calibration_chromosome", "chrom": chrom,
                               "start": 0, "end": lengths[chrom], "length": lengths[chrom]})
    for chrom, values in sorted(halo_by_chrom.items()):
        for start, end in values:
            exclusions.append({"kind": "old_gene_utility_halo", "chrom": chrom, "start": start,
                               "end": end, "length": end - start})
    out.mkdir(parents=True, exist_ok=False)
    write_regions(out / "full_autosome_regions.tsv", full)
    write_regions(out / "primary_regions.tsv", primary)
    with (out / "exclusions.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["kind", "chrom", "start", "end", "length"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(exclusions)

    full_iso, full_excl = parse_refseq(paths["refseq"], set(autosomes), full, "full")
    primary_iso, primary_excl = parse_refseq(paths["refseq"], set(autosomes), primary, "primary")
    full_report = locus_report(full_iso, str(paths["refseq"]), "full_autosome", full_excl)
    primary_report = locus_report(primary_iso, str(paths["refseq"]), "primary", primary_excl)
    dump(out / "reference-full.json", full_report)
    dump(out / "reference-primary.json", primary_report)
    write_isoforms(out / "refseq-complete-coding-isoforms-full.tsv", full_iso, "full_autosome")
    write_isoforms(out / "refseq-complete-coding-isoforms-primary.tsv", primary_iso, "primary")
    write_units(out / "refseq-gene-loci-full.tsv", full_report["units"])
    write_units(out / "refseq-gene-loci-primary.tsv", primary_report["units"])
    manifest = {
        "protocol": NAME, "species": species, "assembly": str(paths["assembly"]),
        "genome": str(paths["genome"]), "refseq": str(paths["refseq"]),
        "geometry": str(paths["geometry"]), "coordinate_convention": "zero_based_half_open",
        "autosomes": autosomes, "autosome_lengths": {chrom: lengths[chrom] for chrom in autosomes},
        "d_train_chromosomes": list(exposure["train"]),
        "d_calibration_chromosomes": list(exposure["calibration"]),
        "excluded_d_chromosomes": excluded_chromosomes,
        "old_geometry_halos": geometry, "full_region_count": len(full), "primary_region_count": len(primary),
        "full_autosome_bp": sum(region.end - region.start for region in full),
        "primary_bp": sum(region.end - region.start for region in primary),
        "reference_full": {"isoforms": full_report["isoform_count"], "gene_loci": full_report["unit_count"],
                           "excluded": full_report["excluded_transcript_rows"]},
        "reference_primary": {"isoforms": primary_report["isoform_count"], "gene_loci": primary_report["unit_count"],
                               "excluded": primary_report["excluded_transcript_rows"]},
        "predictions_read": False, "sealed_labels_read": False,
        "primary_domain_definition": "all chrN autosomes minus every D TRAIN/CAL chromosome and old utility halo intervals",
        "primary_endpoint": "exact normalized CDS-chain gene-locus agreement to complete protein-coding RefSeq; prediction start/stop completeness reported separately",
    }
    dump(out / "evaluation-manifest.json", manifest)
    return manifest


def write_isoforms(path: Path, isoforms: Sequence[RefIsoform], domain: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["domain", "source_line", "transcript_id", "gene_id", "chrom", "strand", "tx_start", "tx_end", "cds_start", "cds_end", "cds_intervals"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for iso in isoforms:
            writer.writerow({"domain": domain, "source_line": iso.source_line, "transcript_id": iso.transcript_id,
                             "gene_id": iso.gene_id, "chrom": iso.chrom, "strand": iso.strand,
                             "tx_start": iso.tx_start, "tx_end": iso.tx_end, "cds_start": iso.cds_start,
                             "cds_end": iso.cds_end, "cds_intervals": json.dumps([list(value) for value in iso.chain.intervals], separators=(",", ":"))})


def write_units(path: Path, units: Sequence[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["unit_id", "chrom", "strand", "gene_id", "raw_gene_ids", "merged_gene_id_count",
                  "merged_from_unit_count", "merge_reason", "span_start", "span_end", "transcript_ids", "isoform_count"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for unit in units:
            writer.writerow({"unit_id": unit["unit_id"], "chrom": unit["chrom"], "strand": unit["strand"],
                             "gene_id": unit["gene_id"], "raw_gene_ids": ";".join(unit.get("raw_gene_ids", [unit["gene_id"]])),
                             "merged_gene_id_count": unit.get("merged_gene_id_count", 1),
                             "merged_from_unit_count": unit.get("merged_from_unit_count", 1),
                             "merge_reason": unit.get("merge_reason") or "",
                             "span_start": unit["span"][0], "span_end": unit["span"][1],
                             "transcript_ids": ",".join(unit["transcript_ids"]), "isoform_count": len(unit["isoforms"])})


def download_long_read(out: Path) -> Path:
    path = out / "inputs" / "zebrafish" / "merge.annotated.gtf.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size == LONG_READ_BYTES:
        return path
    if path.exists():
        raise ValueError(f"existing long-read GTF has unexpected size: {path.stat().st_size}")
    partial = path.with_suffix(path.suffix + ".part")
    if partial.exists():
        partial.unlink()
    request = urllib.request.Request(LONG_READ_URL, headers={"User-Agent": "ab-initio-TE/20260925"})
    with urllib.request.urlopen(request, timeout=1800) as source, partial.open("wb") as dest:
        shutil.copyfileobj(source, dest)
        headers = dict(source.headers)
    if partial.stat().st_size != LONG_READ_BYTES:
        raise ValueError(f"long-read GTF length differs from frozen {LONG_READ_BYTES}: {partial.stat().st_size}")
    partial.replace(path)
    dump(path.parent / "download.json", {"url": LONG_READ_URL, "expected_bytes": LONG_READ_BYTES,
                                          "observed_bytes": path.stat().st_size, "headers": headers})
    return path


def canonical_zebrafish_contig(name: str) -> str:
    """Map the source study's ``1..25`` contigs to UCSC ``chr1..chr25``."""
    match = re.fullmatch(r"(?:chr)?([0-9]+)", name)
    if match and 1 <= int(match.group(1)) <= 25:
        return "chr" + str(int(match.group(1)))
    return name


def parse_long_read(path: Path, full_report: Mapping[str, object], primary_report: Mapping[str, object], out: Path) -> Dict[str, object]:
    records: Dict[str, Dict[str, object]] = {}
    malformed = Counter()
    source_contigs = Counter()
    canonical_contigs = Counter()
    with gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 9:
                malformed["columns"] += 1
                continue
            source_chrom, _, feature, start, end, _, strand, _, attrs_text = fields
            if strand not in ("+", "-"):
                continue
            attrs = parse_attrs(attrs_text)
            transcript = attrs.get("transcript_id") or attrs.get("transcript")
            if not transcript:
                malformed["missing_transcript_id"] += 1
                continue
            chrom = canonical_zebrafish_contig(source_chrom)
            source_contigs[source_chrom] += 1
            canonical_contigs[chrom] += 1
            # The source GTF stores class_code on the transcript row.  Keep
            # that provenance, but never use the transcript span as an exon.
            if feature == "transcript":
                row = records.setdefault(transcript, {"transcript_id": transcript, "chrom": chrom,
                                                       "source_chroms": set(), "strand": strand, "exons": [],
                                                       "class_codes": set(), "source_lines": []})
                if row["chrom"] != chrom or row["strand"] != strand:
                    malformed["transcript_multiple_loci"] += 1
                    continue
                row["source_chroms"].add(source_chrom)
                row["source_lines"].append(line_no)
                if "class_code" in attrs:
                    row["class_codes"].add(attrs["class_code"])
                continue
            if feature not in EXON_FEATURES:
                continue
            try:
                left, right = int(start) - 1, int(end)
            except ValueError:
                malformed["coordinates"] += 1
                continue
            if left < 0 or right <= left:
                malformed["coordinates"] += 1
                continue
            row = records.setdefault(transcript, {"transcript_id": transcript, "chrom": chrom,
                                                   "source_chroms": set(), "strand": strand, "exons": [],
                                                   "class_codes": set(), "source_lines": []})
            if row["chrom"] != chrom or row["strand"] != strand:
                malformed["transcript_multiple_loci"] += 1
                continue
            row["source_chroms"].add(source_chrom)
            row["exons"].append((left, right))
            row["source_lines"].append(line_no)
            if "class_code" in attrs:
                row["class_codes"].add(attrs["class_code"])
    full_mapping = _intron_mapping(full_report)
    primary_mapping = _intron_mapping(primary_report)
    structures = []
    for transcript, row in sorted(records.items()):
        try:
            exons = normalize(row["exons"])
        except ValueError:
            malformed["empty_exons"] += 1
            continue
        if len(exons) < 2:
            continue
        introns = chain_introns(exons)
        full_hits = sorted(full_mapping.get((row["chrom"], row["strand"], introns), []))
        primary_hits = sorted(primary_mapping.get((row["chrom"], row["strand"], introns), []))
        structures.append({"transcript_id": transcript, "chrom": row["chrom"],
                           "source_chroms": sorted(row["source_chroms"]), "strand": row["strand"],
                           "exons": [list(value) for value in exons], "introns": [list(value) for value in introns],
                           "class_code": sorted(row["class_codes"]),
                           "class_code_source": "transcript_attribute" if row["class_codes"] else "missing",
                           "source_lines": row["source_lines"],
                           "full_refseq_cds_intron_chain_units": full_hits,
                           "primary_refseq_cds_intron_chain_units": primary_hits,
                           "coding_supported_full": bool(full_hits),
                           "coding_supported_primary": bool(primary_hits)})
    unique = {}
    for row in structures:
        key = (row["chrom"], row["strand"], tuple(tuple(value) for value in row["introns"]))
        entry = unique.setdefault(key, {"chrom": row["chrom"], "strand": row["strand"],
                                        "introns": [list(value) for value in row["introns"]],
                                        "transcript_ids": [], "class_codes": set(),
                                        "full_refseq_cds_intron_chain_units": set(),
                                        "primary_refseq_cds_intron_chain_units": set()})
        entry["transcript_ids"].append(row["transcript_id"])
        entry["class_codes"].update(row["class_code"])
        entry["full_refseq_cds_intron_chain_units"].update(row["full_refseq_cds_intron_chain_units"])
        entry["primary_refseq_cds_intron_chain_units"].update(row["primary_refseq_cds_intron_chain_units"])
    dedup = []
    for entry in unique.values():
        dedup.append({**entry, "transcript_ids": sorted(entry["transcript_ids"]),
                      "class_codes": sorted(entry["class_codes"]),
                      "coding_supported_full": bool(entry["full_refseq_cds_intron_chain_units"]),
                      "coding_supported_primary": bool(entry["primary_refseq_cds_intron_chain_units"]),
                      "full_refseq_cds_intron_chain_units": sorted(entry["full_refseq_cds_intron_chain_units"]),
                      "primary_refseq_cds_intron_chain_units": sorted(entry["primary_refseq_cds_intron_chain_units"])})
    with (out / "long-read-structures.tsv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["structure_id", "chrom", "strand", "intron_count", "transcript_ids", "class_codes", "coding_supported_full", "coding_supported_primary"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for index, row in enumerate(sorted(dedup, key=lambda value: (value["chrom"], value["introns"], value["strand"])), 1):
            writer.writerow({"structure_id": f"lr-{index:06d}", "chrom": row["chrom"], "strand": row["strand"],
                             "intron_count": len(row["introns"]), "transcript_ids": ",".join(row["transcript_ids"]),
                             "class_codes": ",".join(row["class_codes"]), "coding_supported_full": row["coding_supported_full"],
                             "coding_supported_primary": row["coding_supported_primary"]})
    summary = {"source": str(path), "url": LONG_READ_URL, "source_bytes": path.stat().st_size,
               "all_multi_exon_transcripts": len(structures), "deduplicated_multi_exon_structures": len(dedup),
               "coding_supported_full_structures": sum(row["coding_supported_full"] for row in dedup),
               "coding_supported_primary_structures": sum(row["coding_supported_primary"] for row in dedup),
               "class_code_counts_transcripts": dict(Counter(value for row in structures for value in row["class_code"] or ["missing"])),
               "class_code_counts_structures": dict(Counter(value for row in dedup for value in row["class_codes"] or ["missing"])),
               "source_contig_counts": dict(source_contigs), "canonical_contig_counts": dict(canonical_contigs),
               "contig_mapping": "numeric zebrafish contigs 1..25 mapped to UCSC chr1..chr25; other contigs retained",
               "malformed_or_skipped": dict(malformed),
               "interpretation": "multi-exon splice-structure support; exact RefSeq CDS intron matches do not establish complete CDS start/stop/frame truth; class_code=u is retained as structural provenance and is not treated as coding"}
    dump(out / "long-read-structures.json", {"structures": structures, "deduplicated_structures": dedup})
    dump(out / "long-read-summary.json", summary)
    return summary


def _intron_mapping(report: Mapping[str, object]) -> Dict[Tuple[str, str, Tuple[Tuple[int, int], ...]], Set[str]]:
    mapping: Dict[Tuple[str, str, Tuple[Tuple[int, int], ...]], Set[str]] = defaultdict(set)
    for unit in report["units"]:
        for iso in unit["isoforms"]:
            intervals = tuple(tuple(value) for value in iso["intervals"])
            key = (unit["chrom"], unit["strand"], chain_introns(intervals))
            if key[2]:
                mapping[key].add(unit["unit_id"])
    return mapping


def prepare(args: argparse.Namespace) -> Dict[str, object]:
    root = Path(args.root).resolve()
    out = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUT / args.species
    manifest = prepare_reference(root, args.species, out)
    # ``run.py`` uses one small gate shared by the six future BRAKER arms.  It
    # is deliberately written only after the species-specific coordinates and
    # RefSeq denominators are complete; it does not mean that BRAKER has run.
    gate_path = out.parent / "preparation.json"
    gate = {"protocol": NAME, "status": "PARTIAL",
            "species": {}, "predictions_read": False, "sealed_labels_read": False,
            "primary_endpoint": manifest["primary_endpoint"]}
    if gate_path.exists():
        existing = json.loads(gate_path.read_text())
        if existing.get("protocol") != NAME or existing.get("status") not in ("PARTIAL", "EVALUATION_READY"):
            raise ValueError("existing evaluation preparation gate is incompatible")
        gate.update(existing)
    gate.setdefault("species", {})[args.species] = {"evaluation_dir": str(out),
                                                      "primary_regions": manifest["primary_region_count"],
                                                      "primary_bp": manifest["primary_bp"],
                                                      "reference_isoforms": manifest["reference_primary"]["isoforms"],
                                                      "reference_gene_loci": manifest["reference_primary"]["gene_loci"]}
    if args.long_read_gtf or args.download_long_read:
        if args.species != "zebrafish":
            raise ValueError("the fixed long-read GTF is zebrafish-only")
        path = Path(args.long_read_gtf).resolve() if args.long_read_gtf else download_long_read(out)
        summary = parse_long_read(path, json.loads((out / "reference-full.json").read_text()),
                                  json.loads((out / "reference-primary.json").read_text()), out)
        manifest["long_read"] = summary
        dump(out / "evaluation-manifest.json", manifest)
        gate["species"][args.species]["long_read_summary"] = str(out / "long-read-summary.json")
    # Both species' denominators must exist, and the fish independent
    # structure source must have been parsed, before the expensive run.py gate
    # is opened.  A one-species preparation is intentionally only PARTIAL.
    chicken = gate["species"].get("chicken", {})
    fish = gate["species"].get("zebrafish", {})
    ready = bool(chicken.get("evaluation_dir") and fish.get("evaluation_dir") and
                 fish.get("long_read_summary"))
    gate["status"] = "EVALUATION_READY" if ready else "PARTIAL"
    gate["ready_requirements"] = {"chicken_reference_prepared": bool(chicken.get("evaluation_dir")),
                                   "zebrafish_reference_prepared": bool(fish.get("evaluation_dir")),
                                   "zebrafish_long_read_parsed": bool(fish.get("long_read_summary"))}
    dump(gate_path, gate)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def parse_gtf_predictions(path: Path, regions: Sequence[Region], mapping: Mapping[Tuple[str, str, Tuple[Tuple[int, int], ...]], str], units: Mapping[str, object]) -> Dict[str, object]:
    allowed = defaultdict(list)
    for region in regions:
        allowed[region.chrom].append((region.start, region.end))
    transcripts: Dict[str, Dict[str, object]] = {}
    skipped = Counter()
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"GTF line {line_no}: expected 9 columns")
            chrom, _, feature, start, end, _, strand, phase, attrs_text = fields
            attrs = parse_attrs(attrs_text)
            transcript = attrs.get("transcript_id") or attrs.get("transcript")
            if feature not in {"CDS", "start_codon", "stop_codon"}:
                continue
            if not transcript or chrom not in allowed or strand not in ("+", "-"):
                skipped["missing_id_or_non_autosome"] += 1
                continue
            try:
                left, right = int(start) - 1, int(end)
            except ValueError:
                raise ValueError(f"GTF line {line_no}: invalid coordinates")
            if left < 0 or right <= left:
                raise ValueError(f"GTF line {line_no}: invalid interval")
            row = transcripts.setdefault(transcript, {"transcript_id": transcript, "chrom": chrom,
                                                       "strand": strand, "cds": [], "start_codon": [],
                                                       "stop_codon": []})
            if row["chrom"] != chrom or row["strand"] != strand:
                raise ValueError(f"GTF transcript changes locus at line {line_no}")
            if feature == "CDS":
                row["cds"].append((left, right))
            elif feature == "start_codon":
                row["start_codon"].append((left, right))
            elif feature == "stop_codon":
                row["stop_codon"].append((left, right))
    predicted = []
    for row in transcripts.values():
        if not row["cds"]:
            skipped["no_cds"] += 1
            continue
        # BRAKER emits start_codon/stop_codon as separate GTF features in
        # many versions.  They are part of the CDS coordinates for exact
        # genePred-style matching, so add them before normalization.  If a
        # CDS row already contains the codon, normalization removes the
        # duplicate interval without changing the chain.
        chain = Chain(row["strand"], normalize(row["cds"] + row["start_codon"] + row["stop_codon"]))
        if not _chain_in_regions(row["chrom"], chain, allowed):
            skipped["outside_primary_domain"] += 1
            continue
        key = (row["chrom"], chain.strand, chain.intervals)
        unit = mapping.get(key)
        predicted.append({"transcript_id": row["transcript_id"], "chrom": row["chrom"],
                          "strand": row["strand"], "intervals": [list(value) for value in chain.intervals],
                          "unit_id": unit, "matched": unit is not None,
                          "complete_cds_features": bool(row["start_codon"] and row["stop_codon"]),
                          "start_codon_features": len(row["start_codon"]),
                          "stop_codon_features": len(row["stop_codon"])})
    unique = {}
    for row in predicted:
        key = (row["chrom"], row["strand"], tuple(tuple(value) for value in row["intervals"]))
        unique.setdefault(key, row)
    chains = list(unique.values())
    matched_units = {row["unit_id"] for row in chains if row["matched"]}
    fp = sum(not row["matched"] for row in chains)
    tp = len(matched_units)
    fn = len(units) - tp
    complete = sum(bool(row["complete_cds_features"]) for row in chains)
    return {"predicted_chains": chains, "matched_units": sorted(matched_units),
            "metrics": metric(tp, fp, fn), "skipped": dict(skipped), "transcript_count": len(transcripts),
            "unique_cds_chains": len(chains), "complete_cds_feature_chains": complete,
            "partial_cds_feature_chains": len(chains) - complete,
            "prediction_endpoint_rule": "all domain-contained unique CDS chains enter TP/FP; start/stop feature presence is reported as a completeness stratum"}


def metric(tp: int, fp: int, fn: int) -> Dict[str, Optional[float]]:
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": (2 * tp) / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def score(args: argparse.Namespace) -> Dict[str, object]:
    evaluation = Path(args.evaluation_dir).resolve() if args.evaluation_dir else DEFAULT_OUT / args.species
    manifest = json.loads((evaluation / "evaluation-manifest.json").read_text())
    report = json.loads((evaluation / ("reference-primary.json" if args.domain == "primary" else "reference-full.json")).read_text())
    regions = load_regions(evaluation / ("primary_regions.tsv" if args.domain == "primary" else "full_autosome_regions.tsv"))
    mapping = ref_mapping(report)
    units = {unit["unit_id"]: unit for unit in report["units"]}
    arms = parse_arms(args)
    if not arms:
        raise ValueError("score requires --gtf or at least one --arm NAME=GTF")
    results = {}
    for name, path in arms.items():
        result = parse_gtf_predictions(Path(path), regions, mapping, units)
        result["gtf"] = str(Path(path).resolve())
        results[name] = result
    comparisons = {}
    for right in ("RM2_FULL", "RED_FULL"):
        if "D" not in results or right not in results:
            continue
        comparisons["D_minus_" + right] = bootstrap_difference(results, report, right)
    result = {"protocol": NAME, "species": args.species, "domain": args.domain,
              "reference": {"source": report["reference_source"], "isoform_count": report["isoform_count"],
                            "gene_loci": report["unit_count"], "excluded": report["excluded_transcript_rows"]},
              "primary_endpoint": "exact normalized CDS-chain gene-locus agreement to complete RefSeq; all domain-contained prediction CDS chains enter the denominator and start/stop completeness is stratified",
              "arms": results, "comparisons": comparisons, "bootstrap": {"seed": 42, "replicates": args.bootstrap_replicates,
                                                                            "unit": "chromosome-resampled regional sensitivity, not biological replication"},
              "predictions_read": True, "sealed_labels_read": False}
    dump(evaluation / "score.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def parse_arms(args: argparse.Namespace) -> Dict[str, str]:
    arms: Dict[str, str] = {}
    if args.gtf:
        arms[args.name] = args.gtf
    for value in args.arm:
        if "=" not in value:
            raise ValueError("--arm must be NAME=GTF")
        name, path = value.split("=", 1)
        if not name or not path or name in arms:
            raise ValueError("duplicate or empty BRAKER arm")
        arms[name] = path
    return arms


def load_regions(path: Path) -> List[Region]:
    result = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            result.append(Region(row["chrom"], int(row["start"]), int(row["end"]), row["kind"], row["region_id"]))
    return result


def bootstrap_difference(results: Mapping[str, Mapping[str, object]], report: Mapping[str, object], right: str) -> Dict[str, object]:
    # Region-level predictions are reconstructed from per-chromosome exact units.
    # This is intentionally a fixed chromosome sensitivity interval, not a claim
    # of biological replication.  A score-only input with no chromosome details
    # therefore reports the point delta and omits the interval.
    left_rows = _per_chrom_counts(results["D"], report)
    right_rows = _per_chrom_counts(results[right], report)
    chroms = sorted(set(left_rows) | set(right_rows))
    point = results["D"]["metrics"]["f1"] - results[right]["metrics"]["f1"]
    if not chroms:
        return {"f1_delta": point, "ci95": None, "gained_units": [], "lost_units": []}
    rng = random.Random(42)
    values = []
    for _ in range(10000):
        sample = [chroms[rng.randrange(len(chroms))] for _ in chroms]
        d = Counter()
        r = Counter()
        for chrom in sample:
            d.update(left_rows.get(chrom, {}))
            r.update(right_rows.get(chrom, {}))
        values.append(metric(d["tp"], d["fp"], d["fn"])["f1"] - metric(r["tp"], r["fp"], r["fn"])["f1"])
    values.sort()
    return {"f1_delta": point, "ci95": [quantile(values, 0.025), quantile(values, 0.975)],
            "gained_units": sorted(set(results["D"]["matched_units"]) - set(results[right]["matched_units"])),
            "lost_units": sorted(set(results[right]["matched_units"]) - set(results["D"]["matched_units"]))}


def _per_chrom_counts(result: Mapping[str, object], report: Mapping[str, object]) -> Dict[str, Counter]:
    truth = Counter(unit["chrom"] for unit in report["units"])
    result_rows = defaultdict(list)
    for row in result["predicted_chains"]:
        result_rows[row["chrom"]].append(row)
    values = {}
    for chrom in set(truth) | set(result_rows):
        rows = result_rows.get(chrom, [])
        matched = {row["unit_id"] for row in rows if row["matched"]}
        values[chrom] = Counter(tp=len(matched), fp=sum(not row["matched"] for row in rows), fn=truth[chrom] - len(matched))
    return values


def quantile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("empty bootstrap sample")
    position = (len(values) - 1) * fraction
    low, high = int(position), min(len(values) - 1, int(position) + 1)
    weight = position - low
    return float(values[low] * (1 - weight) + values[high] * weight)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--species", choices=("chicken", "zebrafish"), required=True)
    prepare_parser.add_argument("--root", type=Path, default=ROOT)
    prepare_parser.add_argument("--output-dir", type=Path)
    prepare_parser.add_argument("--download-long-read", action="store_true")
    prepare_parser.add_argument("--long-read-gtf", type=Path)
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--species", choices=("chicken", "zebrafish"), required=True)
    score_parser.add_argument("--evaluation-dir", type=Path)
    score_parser.add_argument("--domain", choices=("primary", "full"), default="primary")
    score_parser.add_argument("--gtf", type=Path)
    score_parser.add_argument("--name", default="BRAKER")
    score_parser.add_argument("--arm", action="append", default=[], metavar="NAME=GTF")
    score_parser.add_argument("--bootstrap-replicates", type=int, default=10000)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args)
    else:
        if args.bootstrap_replicates != 10000:
            raise ValueError("the frozen score contract uses exactly 10000 chromosome bootstrap replicates")
        score(args)


if __name__ == "__main__":
    main()
