#!/usr/bin/env python3
"""Build label-blind flank FASTA files and summarize flank homology hits."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import TextIO
from urllib.parse import quote, unquote


MAX_FLANK = 256
TARGET_SEQIDS = frozenset(("chr3", "chr5", "chr13"))
FASTA_PREFIX = "phase0"


def _open_text(path: Path) -> TextIO:
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def _read_region(path: Path) -> tuple[str, int, int, str]:
    rows: list[tuple[str, int, int, str]] = []
    with _open_text(path) as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows.append((str(row["chr"]), int(row["start"]), int(row["end"]), str(row["sequence"])))
    if not rows:
        raise ValueError(f"empty region JSONL: {path}")
    seqid = rows[0][0]
    region_start = rows[0][1]
    next_start = region_start
    sequence: list[str] = []
    for row_seqid, start, end, piece in rows:
        if row_seqid != seqid or start != next_start or end <= start or len(piece) != end - start:
            raise ValueError("region JSONL must contain one contiguous coordinate shard")
        sequence.append(piece.upper())
        next_start = end
    return seqid, region_start, next_start, "".join(sequence)


def _read_candidates(path: Path) -> list[dict[str, object]]:
    with _open_text(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"candidate_id", "seqid", "gap_start", "gap_end", "eligible_main"}
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("candidate TSV lacks the flank-export fields")
        candidates: list[dict[str, object]] = []
        seen: set[str] = set()
        for row in reader:
            if row["eligible_main"] != "1":
                continue
            candidate_id = row["candidate_id"]
            seqid = row["seqid"]
            if not candidate_id or not seqid:
                raise ValueError("eligible candidate has an empty identifier or seqid")
            if candidate_id in seen:
                raise ValueError(f"duplicate eligible candidate_id: {candidate_id}")
            gap_start, gap_end = int(row["gap_start"]), int(row["gap_end"])
            if gap_end <= gap_start:
                raise ValueError(f"invalid candidate interval: {candidate_id}")
            seen.add(candidate_id)
            candidates.append({
                "candidate_id": candidate_id,
                "seqid": seqid,
                "gap_start": gap_start,
                "gap_end": gap_end,
            })
    return candidates


def flank_name(role: str, seqid: str, candidate_id: str, side: str) -> str:
    if role not in {"train", "test"}:
        raise ValueError(f"unsupported role: {role}")
    if side not in {"left", "right"}:
        raise ValueError(f"unsupported flank side: {side}")
    return "|".join((
        FASTA_PREFIX,
        f"role={quote(role, safe='')}",
        f"seqid={quote(seqid, safe='')}",
        f"candidate_id={quote(candidate_id, safe='')}",
        f"side={side}",
    ))


def parse_flank_name(name: str) -> dict[str, str] | None:
    parts = name.split("|")
    if not parts or parts[0] != FASTA_PREFIX:
        return None
    values: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            return None
        key, value = part.split("=", 1)
        if key in values:
            return None
        values[key] = unquote(value)
    if set(values) != {"role", "seqid", "candidate_id", "side"}:
        return None
    if values["role"] not in {"train", "test"} or values["side"] not in {"left", "right"}:
        return None
    return values


def export_flanks(
    candidates_path: Path,
    region_path: Path,
    role: str,
    output_fasta: Path,
) -> int:
    if role not in {"train", "test"}:
        raise ValueError("role must be train or test")
    seqid, region_start, region_end, sequence = _read_region(region_path)
    candidates = _read_candidates(candidates_path)
    output_fasta.parent.mkdir(parents=True, exist_ok=True)
    records = 0
    with output_fasta.open("w", encoding="ascii", newline="\n") as handle:
        for candidate in candidates:
            if candidate["seqid"] != seqid:
                raise ValueError(
                    f"candidate {candidate['candidate_id']} is on {candidate['seqid']}, expected {seqid}",
                )
            gap_start = int(candidate["gap_start"])
            gap_end = int(candidate["gap_end"])
            if gap_start < region_start or gap_end > region_end:
                raise ValueError(f"candidate interval is outside region: {candidate['candidate_id']}")
            left_start = max(region_start, gap_start - MAX_FLANK)
            right_end = min(region_end, gap_end + MAX_FLANK)
            left = sequence[left_start - region_start:gap_start - region_start]
            right = sequence[gap_end - region_start:right_end - region_start]
            for side, flank in (("left", left), ("right", right)):
                handle.write(
                    f">{flank_name(role, seqid, str(candidate['candidate_id']), side)}\n{flank}\n",
                )
                records += 1
    return records


def _read_paf(path: Path) -> list[tuple[str, int, int, int, str, int, int, int, int, int]]:
    rows: list[tuple[str, int, int, int, str, int, int, int, int, int]] = []
    with _open_text(path) as handle:
        for line in handle:
            if not line.strip():
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 12:
                raise ValueError("PAF row has fewer than twelve required columns")
            qname, qlen, qstart, qend = fields[0], int(fields[1]), int(fields[2]), int(fields[3])
            tname, tlen, tstart, tend = fields[5], int(fields[6]), int(fields[7]), int(fields[8])
            nmatch, aln_block = int(fields[9]), int(fields[10])
            if qlen <= 0 or tlen <= 0 or not (0 <= qstart <= qend <= qlen) or not (0 <= tstart <= tend <= tlen):
                raise ValueError("PAF row has invalid sequence coordinates")
            if nmatch < 0 or aln_block < 0 or nmatch > aln_block:
                raise ValueError("PAF row has invalid match counts")
            rows.append((qname, qlen, qstart, qend, tname, tlen, tstart, tend, nmatch, aln_block))
    return rows


def _qualifies(row: tuple[str, int, int, int, str, int, int, int, int, int]) -> bool:
    _, qlen, qstart, qend, _, tlen, tstart, tend, nmatch, aln_block = row
    return (
        aln_block >= 100
        and nmatch / aln_block >= 0.80
        and (qend - qstart) / qlen >= 0.50
        and (tend - tstart) / tlen >= 0.50
    )


def summarize_paf(
    candidates_path: Path,
    paf_path: Path,
    output_tsv: Path,
    output_json: Path,
) -> dict[str, object]:
    candidates = [candidate for candidate in _read_candidates(candidates_path) if candidate["seqid"] == "chr19"]
    hits = {
        str(candidate["candidate_id"]): {"left": False, "right": False}
        for candidate in candidates
    }
    paf_rows = _read_paf(paf_path)
    qualifying_alignments = 0
    for row in paf_rows:
        query = parse_flank_name(row[0])
        target = parse_flank_name(row[4])
        if query is None or target is None:
            continue
        candidate_id = query["candidate_id"]
        if (
            query["role"] != "test"
            or query["seqid"] != "chr19"
            or target["role"] != "train"
            or target["seqid"] not in TARGET_SEQIDS
            or candidate_id not in hits
            or not _qualifies(row)
        ):
            continue
        hits[candidate_id][query["side"]] = True
        qualifying_alignments += 1

    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with output_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("candidate_id", "purged"),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for candidate in candidates:
            candidate_id = str(candidate["candidate_id"])
            left_hit = hits[candidate_id]["left"]
            right_hit = hits[candidate_id]["right"]
            writer.writerow({
                "candidate_id": candidate_id,
                "purged": int(left_hit or right_hit),
            })

    purged = sum(int(any(sides.values())) for sides in hits.values())
    census: dict[str, object] = {
        "schema": "phase0_homology_purge_v1",
        "status": "PASS",
        "candidates": len(candidates),
        "eligible_candidates": len(candidates),
        "purged_candidates": purged,
        "left_flank_hit_candidates": sum(int(sides["left"]) for sides in hits.values()),
        "right_flank_hit_candidates": sum(int(sides["right"]) for sides in hits.values()),
        "unpurged_candidates": len(candidates) - purged,
        "purged_fraction": None if not candidates else purged / len(candidates),
        "paf_rows": len(paf_rows),
        "qualifying_alignments": qualifying_alignments,
        "paf_empty": not paf_rows,
        "target_seqids": sorted(TARGET_SEQIDS),
        "output_tsv": str(output_tsv),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return census


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export-flanks")
    export.add_argument("--candidates", type=Path, required=True)
    export.add_argument("--region-jsonl", type=Path, required=True)
    export.add_argument("--role", choices=("train", "test"), required=True)
    export.add_argument("--output-fasta", type=Path, required=True)

    summarize = subparsers.add_parser("summarize-paf")
    summarize.add_argument("--candidates", type=Path, required=True)
    summarize.add_argument("--paf", type=Path, required=True)
    summarize.add_argument("--output-tsv", type=Path, required=True)
    summarize.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "export-flanks":
        export_flanks(args.candidates, args.region_jsonl, args.role, args.output_fasta)
    else:
        summarize_paf(args.candidates, args.paf, args.output_tsv, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
