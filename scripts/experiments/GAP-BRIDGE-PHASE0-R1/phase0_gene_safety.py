#!/usr/bin/env python3
"""Audit selected chr19 gaps against a frozen UCSC refGene annotation."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


CHROMOSOME = "chr19"
FEATURE_NAMES = (
    "cds",
    "coding_exon",
    "all_exon",
    "splice_core_pm2",
    "promoter_pm200",
)


@dataclass(frozen=True)
class SelectedInterval:
    start: int
    end: int


@dataclass(frozen=True)
class Transcript:
    transcript_id: str
    gene_id: str
    seqid: str
    strand: str
    tx_start: int
    tx_end: int
    cds_start: int
    cds_end: int
    exons: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class Feature:
    seqid: str
    start: int
    end: int
    owner: str
    gene_id: str


def _open_text(path: Path) -> TextIO:
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def _parse_int(value: str, field: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer in {field}: {value}") from error


def _interval_columns(fieldnames: list[str]) -> tuple[str, str, str, str | None]:
    names = {field.strip().lower(): field for field in fieldnames}
    if {"seqid", "start", "end"} <= set(names):
        seqid_field, start_field, end_field = names["seqid"], names["start"], names["end"]
    elif {"seqid", "gap_start", "gap_end"} <= set(names):
        seqid_field = names["seqid"]
        start_field, end_field = names["gap_start"], names["gap_end"]
    else:
        raise ValueError("selected interval TSV needs seqid/start/end or seqid/gap_start/gap_end")
    selected_field = names.get("selected")
    return seqid_field, start_field, end_field, selected_field


def load_selected_intervals(path: Path) -> list[SelectedInterval]:
    """Read only selected coordinates; comparator/label columns are ignored."""
    with _open_text(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError("selected interval TSV has no header")
        seqid_field, start_field, end_field, selected_field = _interval_columns(reader.fieldnames)
        intervals: list[SelectedInterval] = []
        for row in reader:
            if selected_field is not None and row[selected_field] not in {"1", "true", "True"}:
                continue
            if row[seqid_field] != CHROMOSOME:
                raise ValueError(f"selected interval is not on {CHROMOSOME}: {row[seqid_field]}")
            start = _parse_int(row[start_field], start_field)
            end = _parse_int(row[end_field], end_field)
            if start < 0 or end <= start:
                raise ValueError(f"invalid selected interval: {CHROMOSOME}:{start}-{end}")
            intervals.append(SelectedInterval(start, end))
    intervals.sort(key=lambda interval: (interval.start, interval.end))
    for previous, current in zip(intervals, intervals[1:]):
        if current.start < previous.end:
            raise ValueError("selected intervals overlap; provide disjoint selected gaps")
    return intervals


def _parse_refgene_row(fields: list[str], line_number: int) -> Transcript:
    if len(fields) == 16:
        name, chrom, strand = fields[1], fields[2], fields[3]
        tx_start, tx_end = _parse_int(fields[4], "txStart"), _parse_int(fields[5], "txEnd")
        cds_start, cds_end = _parse_int(fields[6], "cdsStart"), _parse_int(fields[7], "cdsEnd")
        exon_count = _parse_int(fields[8], "exonCount")
        exon_starts, exon_ends, gene_id = fields[9], fields[10], fields[12]
    elif len(fields) == 15:
        name, chrom, strand = fields[0], fields[1], fields[2]
        tx_start, tx_end = _parse_int(fields[3], "txStart"), _parse_int(fields[4], "txEnd")
        cds_start, cds_end = _parse_int(fields[5], "cdsStart"), _parse_int(fields[6], "cdsEnd")
        exon_count = _parse_int(fields[7], "exonCount")
        exon_starts, exon_ends, gene_id = fields[8], fields[9], fields[11]
    else:
        raise ValueError(f"refGene line {line_number} has {len(fields)} columns, expected 15 or 16")
    if strand not in {"+", "-"} or tx_start < 0 or tx_end <= tx_start:
        raise ValueError(f"invalid refGene transcript at line {line_number}")
    starts = [_parse_int(value, "exonStarts") for value in exon_starts.rstrip(",").split(",") if value]
    ends = [_parse_int(value, "exonEnds") for value in exon_ends.rstrip(",").split(",") if value]
    if len(starts) != exon_count or len(ends) != exon_count or not starts:
        raise ValueError(f"refGene exon count disagrees at line {line_number}")
    exons = tuple((start, end) for start, end in zip(starts, ends))
    if any(start < 0 or end <= start for start, end in exons):
        raise ValueError(f"invalid refGene exon at line {line_number}")
    if cds_start < 0 or cds_end < cds_start:
        raise ValueError(f"invalid refGene CDS at line {line_number}")
    return Transcript(
        transcript_id=name,
        gene_id=gene_id or name,
        seqid=chrom,
        strand=strand,
        tx_start=tx_start,
        tx_end=tx_end,
        cds_start=cds_start,
        cds_end=cds_end,
        exons=exons,
    )


def load_refgene(path: Path) -> list[Transcript]:
    transcripts: list[Transcript] = []
    with _open_text(path) as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if (len(fields) == 16 and fields[2] != CHROMOSOME) or (
                len(fields) == 15 and fields[1] != CHROMOSOME
            ):
                continue
            transcript = _parse_refgene_row(fields, line_number)
            transcripts.append(transcript)
    return transcripts


def load_bed_intervals(path: Path) -> list[tuple[int, int]]:
    """Read a genome-wide BED-like track and retain merged chr19 intervals."""
    intervals: list[tuple[int, int]] = []
    with _open_text(path) as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if fields[0].lower() in {"seqid", "chrom", "#chrom"}:
                continue
            if len(fields) < 3 or fields[0] != CHROMOSOME:
                continue
            start = _parse_int(fields[1], "BED start")
            end = _parse_int(fields[2], "BED end")
            if start < 0 or end <= start:
                raise ValueError(f"invalid interval at line {line_number}: {CHROMOSOME}:{start}-{end}")
            intervals.append((start, end))
    return _merge_intervals(intervals)


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted((start, end) for start, end in intervals if start < end):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _subtract_intervals(
    source: list[tuple[int, int]], masks: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    merged_masks = _merge_intervals(masks)
    for start, end in source:
        cursor = start
        for mask_start, mask_end in merged_masks:
            if mask_end <= cursor:
                continue
            if mask_start >= end:
                break
            if mask_start > cursor:
                result.append((cursor, min(mask_start, end)))
            cursor = max(cursor, mask_end)
            if cursor >= end:
                break
        if cursor < end:
            result.append((cursor, end))
    return result


def _interval_bp(intervals: list[tuple[int, int]]) -> int:
    return sum(end - start for start, end in intervals)


def _intersection_bp(
    left: list[tuple[int, int]], right: list[tuple[int, int]],
) -> int:
    left_union = _merge_intervals(left)
    right_union = _merge_intervals(right)
    total = 0
    right_index = 0
    for left_start, left_end in left_union:
        while right_index < len(right_union) and right_union[right_index][1] <= left_start:
            right_index += 1
        index = right_index
        while index < len(right_union) and right_union[index][0] < left_end:
            right_start, right_end = right_union[index]
            overlap_start = max(left_start, right_start)
            overlap_end = min(left_end, right_end)
            if overlap_start < overlap_end:
                total += overlap_end - overlap_start
            index += 1
    return total


def _feature_intersection_bp(
    selected: list[tuple[int, int]], features: list[Feature],
) -> int:
    return _intersection_bp(selected, [(feature.start, feature.end) for feature in features])


def _feature_hits(
    selected: list[tuple[int, int]], features: list[Feature],
) -> set[str]:
    return {
        feature.owner
        for feature in features
        if any(feature.start < end and start < feature.end for start, end in selected)
    }


def _feature_gene_hits(
    selected: list[tuple[int, int]], features: list[Feature],
) -> set[str]:
    return {
        feature.gene_id
        for feature in features
        if any(feature.start < end and start < feature.end for start, end in selected)
    }


def _build_features(transcripts: list[Transcript]) -> dict[str, list[Feature]]:
    features: dict[str, list[Feature]] = {
        "cds": [],
        "coding_exon": [],
        "all_exon": [],
        "splice_core_pm2": [],
        "promoter_pm200": [],
    }
    for transcript in transcripts:
        for exon_index, (start, end) in enumerate(transcript.exons, 1):
            exon_owner = f"{transcript.transcript_id}:{exon_index}"
            features["all_exon"].append(
                Feature(transcript.seqid, start, end, exon_owner, transcript.gene_id),
            )
            coding_start = max(start, transcript.cds_start)
            coding_end = min(end, transcript.cds_end)
            if coding_start < coding_end:
                features["cds"].append(
                    Feature(transcript.seqid, coding_start, coding_end, transcript.transcript_id, transcript.gene_id),
                )
                features["coding_exon"].append(
                    Feature(transcript.seqid, start, end, exon_owner, transcript.gene_id),
                )
            if exon_index < len(transcript.exons):
                exon_end_boundary = end
                exon_start_boundary = transcript.exons[exon_index][0]
                features["splice_core_pm2"].append(
                    Feature(
                        transcript.seqid,
                        max(0, exon_end_boundary - 2),
                        exon_end_boundary + 2,
                        f"{transcript.transcript_id}:internal_boundary:{exon_index}:exon_end",
                        transcript.gene_id,
                    ),
                )
                features["splice_core_pm2"].append(
                    Feature(
                        transcript.seqid,
                        max(0, exon_start_boundary - 2),
                        exon_start_boundary + 2,
                        f"{transcript.transcript_id}:internal_boundary:{exon_index}:exon_start",
                        transcript.gene_id,
                    ),
                )
        tss = transcript.tx_start if transcript.strand == "+" else transcript.tx_end
        features["promoter_pm200"].append(
            Feature(
                transcript.seqid,
                max(0, tss - 200),
                tss + 200,
                transcript.gene_id,
                transcript.gene_id,
            ),
        )
    return features


def _selected_tuples(intervals: list[SelectedInterval]) -> list[tuple[int, int]]:
    return [(interval.start, interval.end) for interval in intervals]


def _transcript_cds_intervals(transcript: Transcript) -> list[tuple[int, int]]:
    return _merge_intervals([
        (max(start, transcript.cds_start), min(end, transcript.cds_end))
        for start, end in transcript.exons
        if max(start, transcript.cds_start) < min(end, transcript.cds_end)
    ])


def _intersection_summary(
    selected: list[tuple[int, int]],
    negative: list[tuple[int, int]],
    features: list[Feature],
) -> dict[str, object]:
    feature_union_bp = _interval_bp(
        _merge_intervals([(feature.start, feature.end) for feature in features]),
    )
    selected_added_bp = _feature_intersection_bp(selected, features)
    return {
        "feature_union_bp": feature_union_bp,
        "union_denominator_bp": feature_union_bp,
        "selected_added_bp": selected_added_bp,
        "selected_added_fraction": (
            selected_added_bp / feature_union_bp if feature_union_bp else None
        ),
        "added_comparator_negative_bp": _feature_intersection_bp(negative, features),
        "affected_annotation_records": len(_feature_hits(selected, features)),
        "negative_projection_status": "EXACT_FROM_POSITIVE_AND_UNKNOWN_INTERVALS",
    }


def audit_gene_safety(
    intervals_path: Path,
    comparator_positive_path: Path,
    comparator_unknown_path: Path,
    refgene_path: Path,
    output_json: Path,
    output_tsv: Path,
    annotation_version: str,
    annotation_url: str,
    positive_version: str | None = None,
    positive_url: str | None = None,
    unknown_version: str | None = None,
    unknown_url: str | None = None,
) -> dict[str, object]:
    intervals = load_selected_intervals(intervals_path)
    positive = load_bed_intervals(comparator_positive_path)
    unknown_source = load_bed_intervals(comparator_unknown_path)
    effective_unknown = _subtract_intervals(unknown_source, positive)
    selected = _selected_tuples(intervals)
    negative = _subtract_intervals(selected, _merge_intervals([*positive, *effective_unknown]))
    transcripts = load_refgene(refgene_path)
    features = _build_features(transcripts)
    selected_bp = _interval_bp(selected)
    negative_bp = _interval_bp(negative)
    intersections = {
        name: _intersection_summary(selected, negative, features[name])
        for name in FEATURE_NAMES
    }

    feature_union = _merge_intervals([
        (feature.start, feature.end)
        for name in FEATURE_NAMES
        for feature in features[name]
    ])
    gene_overlap_candidates = [
        interval
        for interval in selected
        if any(feature_start < interval[1] and interval[0] < feature_end for feature_start, feature_end in feature_union)
    ]
    gene_overlap_selected_bp = _interval_bp(gene_overlap_candidates)
    gene_overlap_negative_bp = _intersection_bp(negative, gene_overlap_candidates)
    gene_overlap_precision = (
        (gene_overlap_selected_bp - gene_overlap_negative_bp) / gene_overlap_selected_bp
        if gene_overlap_selected_bp
        else None
    )

    cds_union = _merge_intervals([
        (feature.start, feature.end) for feature in features["cds"]
    ])
    callable_cds = _subtract_intervals(cds_union, effective_unknown)
    callable_cds_bp = _interval_bp(callable_cds)
    callable_cds_negative_bp = _intersection_bp(negative, callable_cds)
    callable_cds_negative_fill_rate = (
        callable_cds_negative_bp / callable_cds_bp if callable_cds_bp else None
    )

    annotated_cds_records = []
    for transcript in transcripts:
        transcript_cds = _transcript_cds_intervals(transcript)
        annotated_cds_records.append({
            "transcript_id": transcript.transcript_id,
            "gene_id": transcript.gene_id,
            "cds_bp": _interval_bp(transcript_cds),
            "comparator_negative_bp": _intersection_bp(negative, transcript_cds),
        })
    max_single_cds_negative_bp = max(
        (record["comparator_negative_bp"] for record in annotated_cds_records),
        default=0,
    )

    annotation_features = [
        feature
        for name in FEATURE_NAMES
        for feature in features[name]
    ]
    affected_genes = _feature_gene_hits(selected, annotation_features)
    affected_exons = _feature_hits(selected, features["all_exon"])
    result: dict[str, object] = {
        "schema": "phase0_gene_safety_v1",
        "status": "PASS",
        "seqid": CHROMOSOME,
        "selected_interval_count": len(intervals),
        "selected_added_bp": selected_bp,
        "added_comparator_negative_bp": negative_bp,
        "added_comparator_negative_bp_status": "EXACT_FROM_POSITIVE_AND_UNKNOWN_INTERVALS",
        "negative_interval_count": len(negative),
        "comparator_projection": {
            "positive_path": str(comparator_positive_path),
            "positive_version": positive_version,
            "positive_url": positive_url,
            "positive_bp_chr19": _interval_bp(positive),
            "unknown_path": str(comparator_unknown_path),
            "unknown_version": unknown_version,
            "unknown_url": unknown_url,
            "unknown_source_bp_chr19": _interval_bp(unknown_source),
            "effective_unknown_bp_chr19": _interval_bp(effective_unknown),
            "effective_unknown_interval_count": len(effective_unknown),
            "negative_definition": "selected gaps - comparator-positive union - (comparator-unknown union - comparator-positive union)",
        },
        "annotation": {
            "source": "UCSC hg38 refGene schema",
            "assembly": "hg38",
            "version": annotation_version,
            "url": annotation_url,
            "path": str(refgene_path),
            "transcripts_chr19": len(transcripts),
        },
        "feature_definitions": {
            "coordinate_system": "zero-based half-open",
            "cds": "union of exon intersect transcript CDS intervals",
            "coding_exon": "entire exon when it intersects transcript CDS",
            "all_exon": "union is used for bp; transcript_id:exon_index for affected exon count",
            "splice_core_pm2": "each internal exon-intron boundary [boundary-2,boundary+2), four bases",
            "promoter_pm200": "TSS +/-200 bp, [TSS-200,TSS+200), clipped at coordinate zero",
            "gene_overlap": "whole selected gaps intersecting the union of all_exon, coding_exon, cds, splice_core_pm2, and promoter_pm200",
        },
        "definition_ambiguities": [],
        "aggregation_notes": [
            "All curated transcript records are retained.",
            "Feature bp values are unioned across transcript records; affected exon records retain transcript identity.",
        ],
        "intersections": intersections,
        "affected_gene_count": len(affected_genes),
        "affected_exon_count": len(affected_exons),
        "affected_genes": sorted(affected_genes),
        "affected_exons": sorted(affected_exons),
        "annotated_cds_records": annotated_cds_records,
        "max_single_cds_comparator_negative_bp": max_single_cds_negative_bp,
        "max_single_annotated_cds_negative_bp": max_single_cds_negative_bp,
        "callable_cds_bp": callable_cds_bp,
        "callable_cds_definition": "union annotated CDS minus effective comparator-unknown intervals",
        "callable_cds_negative_bp": callable_cds_negative_bp,
        "callable_cds_negative_fill_rate": callable_cds_negative_fill_rate,
        "gene_overlap_candidate_count": len(gene_overlap_candidates),
        "gene_overlap_selected_added_bp": gene_overlap_selected_bp,
        "gene_overlap_added_comparator_negative_bp": gene_overlap_negative_bp,
        "gene_overlap_added_bp_precision": gene_overlap_precision,
        "gene_overlap_precision_status": "EXACT",
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "seqid": CHROMOSOME,
        "selected_added_bp": selected_bp,
        "added_comparator_negative_bp": negative_bp,
        "cds_union_bp": intersections["cds"]["feature_union_bp"],
        "cds_selected_added_fraction": intersections["cds"]["selected_added_fraction"],
        "cds_negative_bp": intersections["cds"]["added_comparator_negative_bp"],
        "coding_exon_union_bp": intersections["coding_exon"]["feature_union_bp"],
        "coding_exon_selected_added_fraction": intersections["coding_exon"]["selected_added_fraction"],
        "coding_exon_negative_bp": intersections["coding_exon"]["added_comparator_negative_bp"],
        "all_exon_union_bp": intersections["all_exon"]["feature_union_bp"],
        "all_exon_selected_added_fraction": intersections["all_exon"]["selected_added_fraction"],
        "all_exon_negative_bp": intersections["all_exon"]["added_comparator_negative_bp"],
        "splice_core_pm2_union_bp": intersections["splice_core_pm2"]["feature_union_bp"],
        "splice_core_pm2_selected_added_fraction": intersections["splice_core_pm2"]["selected_added_fraction"],
        "splice_core_pm2_negative_bp": intersections["splice_core_pm2"]["added_comparator_negative_bp"],
        "promoter_pm200_union_bp": intersections["promoter_pm200"]["feature_union_bp"],
        "promoter_pm200_selected_added_fraction": intersections["promoter_pm200"]["selected_added_fraction"],
        "promoter_pm200_negative_bp": intersections["promoter_pm200"]["added_comparator_negative_bp"],
        "affected_genes": len(affected_genes),
        "affected_exons": len(affected_exons),
        "callable_cds_bp": callable_cds_bp,
        "callable_cds_negative_fill_rate": "" if callable_cds_negative_fill_rate is None else callable_cds_negative_fill_rate,
        "max_single_cds_comparator_negative_bp": max_single_cds_negative_bp,
        "gene_overlap_candidate_count": len(gene_overlap_candidates),
        "gene_overlap_selected_added_bp": gene_overlap_selected_bp,
        "gene_overlap_added_comparator_negative_bp": gene_overlap_negative_bp,
        "gene_overlap_added_bp_precision": "" if gene_overlap_precision is None else gene_overlap_precision,
    }
    with output_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--comparator-positive", type=Path, required=True)
    parser.add_argument("--comparator-unknown", type=Path, required=True)
    parser.add_argument("--refgene", type=Path, required=True)
    parser.add_argument("--annotation-version", required=True)
    parser.add_argument("--annotation-url", required=True)
    parser.add_argument("--positive-version")
    parser.add_argument("--positive-url")
    parser.add_argument("--unknown-version")
    parser.add_argument("--unknown-url")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_gene_safety(
        args.intervals,
        args.comparator_positive,
        args.comparator_unknown,
        args.refgene,
        args.output_json,
        args.output_tsv,
        args.annotation_version,
        args.annotation_url,
        args.positive_version,
        args.positive_url,
        args.unknown_version,
        args.unknown_url,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
