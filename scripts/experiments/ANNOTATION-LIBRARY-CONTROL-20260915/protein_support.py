#!/usr/bin/env python3
"""Build and summarize a fixed source-only RepeatPeps blastx evidence layer."""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ALLOWED_CHROMOSOMES = {"chr2", "chr3", "chr4"}
EVALUE_CUTOFF = 1e-5
STRONG_BITSCORE = 50.0
STRONG_QCOV_HSP = 20.0


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
        raise ValueError(f"FASTA is missing allowed chromosomes: {sorted(missing)}")
    return records


def _interval(row: Mapping[str, str], prefix: str) -> Tuple[str, int, int]:
    chrom = row[f"{prefix}_source_chrom"]
    start = int(row[f"{prefix}_source_start0"])
    end = int(row[f"{prefix}_source_end"])
    if chrom not in ALLOWED_CHROMOSOMES or start < 0 or end <= start:
        raise ValueError(f"invalid {prefix} source interval: {chrom}:{start}-{end}")
    return chrom, start, end


def _read_match_rows(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"match table has no header: {matched_controls}")
        required = {
            "fp_mapping_id", "fp_source_chrom", "fp_source_start0", "fp_source_end",
            "fp_source_length", "fp_old_te_relation", "match_status",
            "control_mapping_id", "control_source_chrom", "control_source_start0",
            "control_source_end", "control_source_length", "control_old_te_relation",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"match table {path} missing fields: {sorted(missing)}")
        rows.extend(reader)
    return rows


def build_queries(
    matched_controls: Path,
    source_fasta: Path,
    output: Path,
    additional_matches: Optional[Path] = None,
) -> dict:
    rows = _read_match_rows(matched_controls)
    if not rows:
        raise ValueError("empty matched-control table")
    additional_rows = _read_match_rows(additional_matches) if additional_matches is not None else []
    source = fasta_records(source_fasta, ALLOWED_CHROMOSOMES)
    query_rows: List[dict] = []
    seen_fp: set[str] = set()
    fp_index = 0
    for row_index, row in enumerate(rows):
        fp_id = row["fp_mapping_id"]
        if fp_id in seen_fp:
            raise ValueError(f"duplicate FP mapping id at match row {row_index + 2}: {fp_id}")
        seen_fp.add(fp_id)
        chrom, start, end = _interval(row, "fp")
        sequence = source[chrom][start:end]
        if len(sequence) != end - start:
            raise ValueError(f"FP interval is outside source FASTA: {fp_id}")
        query_rows.append(
            {
                "query_id": f"fp{fp_index:08d}",
                "role": "FP",
                "mapping_id": fp_id,
                "source_chrom": chrom,
                "source_start0": start,
                "source_end": end,
                "source_length": end - start,
                "old_te_relation": row["fp_old_te_relation"],
                "match_status": row["match_status"],
                "control_mapping_id": row["control_mapping_id"],
                "control_reuse": row.get("control_reused", "False"),
                "sequence": sequence,
            }
        )
        fp_index += 1
    seen_controls: Dict[str, dict] = {}
    control_use_counts: collections.Counter[str] = collections.Counter(
        row["control_mapping_id"]
        for row in rows
        if row["match_status"] == "MATCHED_TN" and row["control_mapping_id"]
    )
    for row in rows + additional_rows:
        if row["match_status"] != "MATCHED_TN":
            continue
        control_id = row["control_mapping_id"]
        if not control_id:
            raise ValueError("MATCHED_TN row has empty control mapping id")
        if control_id in seen_controls:
            continue
        chrom, start, end = _interval(row, "control")
        sequence = source[chrom][start:end]
        if len(sequence) != end - start:
            raise ValueError(f"TN interval is outside source FASTA: {control_id}")
        seen_controls[control_id] = {
            "query_id": f"tn{len(seen_controls):08d}",
            "role": "TN",
            "mapping_id": control_id,
            "source_chrom": chrom,
            "source_start0": start,
            "source_end": end,
            "source_length": end - start,
            "old_te_relation": row["control_old_te_relation"],
            "match_status": "MATCHED_TN",
            "control_mapping_id": "",
            "control_reuse": False,
            "sequence": sequence,
        }
    query_rows.extend(seen_controls.values())
    fields = [
        "query_id", "role", "mapping_id", "source_chrom", "source_start0", "source_end",
        "source_length", "old_te_relation", "match_status", "control_mapping_id", "control_reuse",
    ]
    output.mkdir(parents=True, exist_ok=False)
    with (output / "queries.fa").open("w", encoding="utf-8") as fasta, (output / "query_manifest.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in query_rows:
            writer.writerow({field: row[field] for field in fields})
            fasta.write(f">{row['query_id']}\n")
            sequence = row["sequence"]
            for offset in range(0, len(sequence), 80):
                fasta.write(sequence[offset : offset + 80] + "\n")
    manifest = {
        "status": "PROTEIN_QUERY_PANEL_PREPARED",
        "query_count": len(query_rows),
        "fp_query_count": sum(row["role"] == "FP" for row in query_rows),
        "tn_query_count": sum(row["role"] == "TN" for row in query_rows),
        "total_bp": sum(int(row["source_length"]) for row in query_rows),
        "shorter_than_30bp": sum(int(row["source_length"]) < 30 for row in query_rows),
        "matched_control_rows": sum(row["match_status"] == "MATCHED_TN" for row in rows),
        "additional_no_reuse_rows": sum(row["match_status"] == "MATCHED_TN" for row in additional_rows),
        "unique_controls": len(seen_controls),
        "original_control_reuse_max": max(control_use_counts.values(), default=0),
        "original_control_reuse_histogram": {str(k): v for k, v in sorted(collections.Counter(control_use_counts.values()).items())},
        "source_fasta": str(source_fasta.resolve()),
        "additional_no_reuse_table": None if additional_matches is None else str(additional_matches.resolve()),
        "allowed_chromosomes": sorted(ALLOWED_CHROMOSOMES),
        "model_scores_read": False,
        "target_annotation_read": False,
        "selection_uses_new_library_support": False,
    }
    (output / "query_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def read_query_manifest(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"query manifest has no header: {path}")
        for row in reader:
            row["source_length"] = int(row["source_length"])
            rows.append(row)
    if not rows:
        raise ValueError(f"empty query manifest: {path}")
    return rows


def parse_blast_hits(path: Path, query_ids: Iterable[str]) -> Dict[str, dict]:
    query_set = set(query_ids)
    best: Dict[str, dict] = {}
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 11:
                raise ValueError(f"{path}:{line_no}: expected 11 blastx fields, got {len(fields)}")
            query_id = fields[0]
            if query_id not in query_set:
                raise ValueError(f"{path}:{line_no}: unknown query id {query_id}")
            try:
                hit = {
                    "subject_id": fields[1],
                    "evalue": float(fields[2]),
                    "bitscore": float(fields[3]),
                    "alignment_length": int(fields[4]),
                    "qstart": int(fields[5]),
                    "qend": int(fields[6]),
                    "sstart": int(fields[7]),
                    "send": int(fields[8]),
                    "qlen": int(fields[9]),
                    "qcovhsp": float(fields[10]),
                }
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid blastx numeric field") from exc
            previous = best.get(query_id)
            if previous is None or (-hit["bitscore"], hit["evalue"], -hit["qcovhsp"]) < (
                -previous["bitscore"], previous["evalue"], -previous["qcovhsp"]
            ):
                best[query_id] = hit
    return best


def summarize(query_dir: Path, blast_path: Path, output: Path, no_reuse_matches: Optional[Path] = None) -> dict:
    rows = read_query_manifest(query_dir / "query_manifest.tsv")
    hits = parse_blast_hits(blast_path, (row["query_id"] for row in rows))
    support_rows: List[dict] = []
    for row in rows:
        hit = hits.get(row["query_id"])
        any_hit = bool(hit and hit["evalue"] <= EVALUE_CUTOFF)
        strong_hit = bool(any_hit and hit["bitscore"] >= STRONG_BITSCORE and hit["qcovhsp"] >= STRONG_QCOV_HSP)
        support_rows.append(
            {
                **row,
                "any_hit": any_hit,
                "strong_hit": strong_hit,
                "best_subject_id": "" if hit is None else hit["subject_id"],
                "best_evalue": "" if hit is None else hit["evalue"],
                "best_bitscore": "" if hit is None else hit["bitscore"],
                "best_qcovhsp": "" if hit is None else hit["qcovhsp"],
                "best_alignment_length": "" if hit is None else hit["alignment_length"],
            }
        )
    output.mkdir(parents=True, exist_ok=False)
    table_fields = list(support_rows[0])
    with (output / "query_support.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=table_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(support_rows)
    by_mapping_role = {(row["mapping_id"], row["role"]): row for row in support_rows}

    def role_summary(role: str) -> dict:
        subset = [row for row in support_rows if row["role"] == role]
        return {
            "n": len(subset),
            "total_bp": sum(int(row["source_length"]) for row in subset),
            "shorter_than_30bp": sum(int(row["source_length"]) < 30 for row in subset),
            "any_hit_n": sum(bool(row["any_hit"]) for row in subset),
            "strong_hit_n": sum(bool(row["strong_hit"]) for row in subset),
            "any_hit_fraction": sum(bool(row["any_hit"]) for row in subset) / float(len(subset)) if subset else None,
            "strong_hit_fraction": sum(bool(row["strong_hit"]) for row in subset) / float(len(subset)) if subset else None,
        }

    relation_summary: Dict[str, dict] = {}
    for relation in sorted({row["old_te_relation"] for row in support_rows if row["role"] == "FP"}):
        subset = [row for row in support_rows if row["role"] == "FP" and row["old_te_relation"] == relation]
        relation_summary[relation] = {
            "n": len(subset),
            "any_hit_n": sum(bool(row["any_hit"]) for row in subset),
            "strong_hit_n": sum(bool(row["strong_hit"]) for row in subset),
        }

    match_path = no_reuse_matches
    if match_path is None:
        raise ValueError("an explicit no-reuse match table is required for pair summaries")
    pairs: List[dict] = []
    with match_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"no-reuse match table has no header: {match_path}")
        for row in reader:
            fp = by_mapping_role.get((row["fp_mapping_id"], "FP"))
            if fp is None:
                raise ValueError(f"no-reuse match references missing FP query {row['fp_mapping_id']}")
            control = by_mapping_role.get((row["control_mapping_id"], "TN")) if row["match_status"] == "MATCHED_TN" else None
            if row["match_status"] == "MATCHED_TN" and control is None:
                raise ValueError(f"no-reuse match references missing TN query {row['control_mapping_id']}")
            pairs.append({"fp": fp, "tn": control, "match_status": row["match_status"], "relation": row.get("fp_old_te_relation", "")})

    pair_summary: Dict[str, dict] = {}
    for evidence in ("any_hit", "strong_hit"):
        matched = [pair for pair in pairs if pair["match_status"] == "MATCHED_TN"]
        unmatched = [pair for pair in pairs if pair["match_status"] != "MATCHED_TN"]
        fp_n = sum(bool(pair["fp"][evidence]) for pair in pairs)
        fp_matched_n = sum(bool(pair["fp"][evidence]) for pair in matched)
        tn_n = sum(bool(pair["tn"][evidence]) for pair in matched)
        pair_summary[evidence] = {
            "matched_pairs_n": len(matched),
            "unmatched_fp_n": len(unmatched),
            "all_fp_supported_n": fp_n,
            "matched_fp_supported_n": fp_matched_n,
            "matched_tn_supported_n": tn_n,
            "matched_fp_fraction": fp_matched_n / float(len(matched)) if matched else None,
            "matched_tn_fraction": tn_n / float(len(matched)) if matched else None,
            "matched_fp_minus_tn_difference_pp": 100.0 * (fp_matched_n - tn_n) / float(len(matched)) if matched else None,
            "unmatched_fp_supported_n": sum(bool(pair["fp"][evidence]) for pair in unmatched),
        }
    summary = {
        "status": "PROTEIN_ORTHOGONAL_SUPPORT_COMPLETED",
        "database": "refs/repos/hite_3_3_3/library/RepeatPeps.lib",
        "database_description": "HiTE RepeatPeps library; 18,011 predicted proteins, 16.1 million aa, readme retained with the asset",
        "blastx": {
            "evalue_cutoff": EVALUE_CUTOFF,
            "strong_bitscore_cutoff": STRONG_BITSCORE,
            "strong_qcovhsp_cutoff_percent": STRONG_QCOV_HSP,
            "seg": "yes",
            "max_target_seqs": 5,
            "max_hsps": 1,
            "strand": "blastx default translated both strands",
        },
        "queries": {
            "total": len(support_rows),
            "fp": role_summary("FP"),
            "tn": role_summary("TN"),
            "source_only_match_table": str(match_path.resolve()),
            "selection_uses_model_scores": False,
            "selection_uses_new_library_support": False,
            "target_annotation_read": False,
        },
        "fp_by_old_te_relation": relation_summary,
        "no_reuse_matched_pair_support": pair_summary,
        "claim_policy": {
            "computational_orthogonal_support": True,
            "manual_or_experimental_truth": False,
            "independent_biological_truth": False,
            "fp_rescue_claim": False,
            "same_base_f1_computed": False,
            "model_scores_read": False,
            "target_annotation_read": False,
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "STATUS").write_text(summary["status"] + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build-queries")
    build.add_argument("--matched-controls", type=Path, required=True)
    build.add_argument("--additional-matches", type=Path)
    build.add_argument("--source-fasta", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("summarize")
    score.add_argument("--query-dir", type=Path, required=True)
    score.add_argument("--blastx", type=Path, required=True)
    score.add_argument("--no-reuse-matches", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build-queries":
        result = build_queries(
            args.matched_controls.resolve(),
            args.source_fasta.resolve(),
            args.output.resolve(),
            None if args.additional_matches is None else args.additional_matches.resolve(),
        )
    else:
        result = summarize(args.query_dir.resolve(), args.blastx.resolve(), args.output.resolve(), args.no_reuse_matches.resolve())
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
