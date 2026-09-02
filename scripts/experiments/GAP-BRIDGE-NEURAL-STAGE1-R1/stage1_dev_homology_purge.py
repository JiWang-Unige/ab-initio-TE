#!/usr/bin/env python3
"""Materialize label-blind Stage 1 flank-homology membership for chr13 DEV."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from urllib.parse import quote, unquote


FASTA_PREFIX = "gapbridge_stage1"
FLANK_BP = 256
TRAIN_ROLES = frozenset(("TRAIN",))
DEV_ROLES = frozenset(("DEV",))
TRAIN_SEQIDS = frozenset(("chr3", "chr5"))
DEV_SEQIDS = frozenset(("chr13",))
ALIGNED_BP_MIN = 100
IDENTITY_MIN = 0.80
COVERAGE_MIN = 0.50
MANIFEST_FIELDS = frozenset((
    "candidate_id", "seqid", "role", "gap_start", "gap_end", "crop_start", "crop_end",
))


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    seqid: str
    role: str
    gap_start: int
    gap_end: int
    crop_start: int
    crop_end: int

    @property
    def gap_length(self) -> int:
        return self.gap_end - self.gap_start


def _open_text(path: Path) -> TextIO:
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def read_manifest(path: Path) -> list[Candidate]:
    """Read only role and coordinate columns needed to build flank sequences."""
    candidates: list[Candidate] = []
    seen: set[str] = set()
    with _open_text(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not MANIFEST_FIELDS <= set(reader.fieldnames):
            raise ValueError("candidate manifest lacks the Stage 1 flank-export fields")
        for row in reader:
            candidate_id = row["candidate_id"]
            seqid = row["seqid"]
            role = row["role"]
            if not candidate_id or not seqid or not role:
                raise ValueError("manifest candidate has an empty identifier, seqid or role")
            if seqid not in TRAIN_SEQIDS | DEV_SEQIDS:
                raise ValueError(f"unsupported Stage 1 sequence id: {seqid}")
            if candidate_id in seen:
                raise ValueError(f"duplicate manifest candidate_id: {candidate_id}")
            gap_start = int(row["gap_start"])
            gap_end = int(row["gap_end"])
            crop_start = int(row["crop_start"])
            crop_end = int(row["crop_end"])
            if gap_end <= gap_start:
                raise ValueError(f"invalid gap interval: {candidate_id}")
            if crop_start != gap_start - FLANK_BP or crop_end != gap_end + FLANK_BP:
                raise ValueError(f"manifest crop is not a complete 256-bp flank crop: {candidate_id}")
            if crop_end <= crop_start:
                raise ValueError(f"invalid crop interval: {candidate_id}")
            if role == "TRAIN" and seqid not in TRAIN_SEQIDS:
                raise ValueError(f"TRAIN candidate is not on chr3/chr5: {candidate_id}")
            if role in {"DEV", "CAL_FIT", "CAL_GATE"} and seqid not in DEV_SEQIDS:
                raise ValueError(f"chr13 role is not on chr13: {candidate_id}")
            seen.add(candidate_id)
            candidates.append(Candidate(
                candidate_id=candidate_id,
                seqid=seqid,
                role=role,
                gap_start=gap_start,
                gap_end=gap_end,
                crop_start=crop_start,
                crop_end=crop_end,
            ))
    return candidates


def flank_name(role: str, seqid: str, candidate_id: str, side: str) -> str:
    if role not in {"TRAIN", "DEV"}:
        raise ValueError(f"unsupported FASTA role: {role}")
    if role == "TRAIN" and seqid not in TRAIN_SEQIDS:
        raise ValueError(f"TRAIN FASTA record is not on chr3/chr5: {seqid}")
    if role == "DEV" and seqid not in DEV_SEQIDS:
        raise ValueError(f"DEV FASTA record is not on chr13: {seqid}")
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
    role = values["role"]
    seqid = values["seqid"]
    if role not in {"TRAIN", "DEV"} or values["side"] not in {"left", "right"}:
        return None
    if role == "TRAIN" and seqid not in TRAIN_SEQIDS:
        return None
    if role == "DEV" and seqid not in DEV_SEQIDS:
        return None
    if not values["candidate_id"]:
        return None
    return values


def _read_region(path: Path) -> tuple[str, int, int, str]:
    seqid: str | None = None
    region_start: int | None = None
    next_start: int | None = None
    pieces: list[str] = []
    with _open_text(path) as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            row_seqid = str(row["chr"])
            start = int(row["start"])
            end = int(row["end"])
            sequence = str(row["sequence"]).upper()
            if seqid is None:
                seqid = row_seqid
                region_start = start
                next_start = start
            if (
                row_seqid != seqid
                or start != next_start
                or end <= start
                or len(sequence) != end - start
            ):
                raise ValueError("region JSONL must contain one contiguous coordinate sequence")
            pieces.append(sequence)
            next_start = end
    if seqid is None or region_start is None or next_start is None:
        raise ValueError(f"empty region JSONL: {path}")
    return seqid, region_start, next_start, "".join(pieces)


def _role_candidates(candidates: list[Candidate], role: str, seqid: str) -> list[Candidate]:
    if role == "TRAIN":
        roles, seqids = TRAIN_ROLES, TRAIN_SEQIDS
    elif role == "DEV":
        roles, seqids = DEV_ROLES, DEV_SEQIDS
    else:
        raise ValueError(f"unsupported export role: {role}")
    if seqid not in seqids:
        raise ValueError(f"{role} export cannot use region sequence {seqid}")
    selected = [candidate for candidate in candidates if candidate.role in roles and candidate.seqid == seqid]
    return selected


def export_flanks(
    manifest_path: Path,
    region_path: Path,
    role: str,
    output_fasta: Path,
) -> int:
    if role not in {"TRAIN", "DEV"}:
        raise ValueError("role must be TRAIN or DEV")
    seqid, region_start, region_end, sequence = _read_region(region_path)
    candidates = _role_candidates(read_manifest(manifest_path), role, seqid)
    output_fasta.parent.mkdir(parents=True, exist_ok=True)
    records = 0
    with output_fasta.open("w", encoding="ascii", newline="\n") as handle:
        for candidate in candidates:
            if candidate.crop_start < region_start or candidate.crop_end > region_end:
                raise ValueError(f"candidate crop is outside region: {candidate.candidate_id}")
            crop = sequence[candidate.crop_start - region_start:candidate.crop_end - region_start]
            left = crop[:FLANK_BP]
            right = crop[-FLANK_BP:]
            if len(left) != FLANK_BP or len(right) != FLANK_BP:
                raise ValueError(f"candidate crop does not contain complete flanks: {candidate.candidate_id}")
            if not set(crop) <= set("ACGT"):
                raise ValueError(f"candidate crop contains a non-ACGT base: {candidate.candidate_id}")
            for side, flank in (("left", left), ("right", right)):
                handle.write(f">{flank_name(role, seqid, candidate.candidate_id, side)}\n{flank}\n")
                records += 1
    return records


def _read_paf(path: Path) -> list[tuple[str, int, int, int, str, int, int, int, int, int]]:
    rows: list[tuple[str, int, int, int, str, int, int, int, int, int]] = []
    with _open_text(path) as handle:
        for raw in handle:
            if not raw.strip():
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if len(fields) < 12:
                raise ValueError("PAF row has fewer than twelve required columns")
            qname, qlen, qstart, qend = fields[0], int(fields[1]), int(fields[2]), int(fields[3])
            tname, tlen, tstart, tend = fields[5], int(fields[6]), int(fields[7]), int(fields[8])
            nmatch, aligned = int(fields[9]), int(fields[10])
            if (
                qlen <= 0 or tlen <= 0
                or not (0 <= qstart <= qend <= qlen)
                or not (0 <= tstart <= tend <= tlen)
                or nmatch < 0 or aligned < 0 or nmatch > aligned
            ):
                raise ValueError("PAF row has invalid sequence coordinates or match counts")
            rows.append((qname, qlen, qstart, qend, tname, tlen, tstart, tend, nmatch, aligned))
    return rows


def qualifies(row: tuple[str, int, int, int, str, int, int, int, int, int]) -> bool:
    _, qlen, qstart, qend, _, tlen, tstart, tend, nmatch, aligned = row
    return (
        aligned >= ALIGNED_BP_MIN
        and nmatch / aligned >= IDENTITY_MIN
        and (qend - qstart) / qlen >= COVERAGE_MIN
        and (tend - tstart) / tlen >= COVERAGE_MIN
    )


def summarize_paf(
    manifest_path: Path,
    paf_path: Path,
    output_tsv: Path,
    output_json: Path,
) -> dict[str, object]:
    candidates = read_manifest(manifest_path)
    dev = [candidate for candidate in candidates if candidate.role == "DEV"]
    dev_by_id = {candidate.candidate_id: candidate for candidate in dev}
    hits = {candidate_id: {"left": False, "right": False} for candidate_id in dev_by_id}
    paf_rows = _read_paf(paf_path)
    qualifying_alignments = 0
    for row in paf_rows:
        query = parse_flank_name(row[0])
        target = parse_flank_name(row[4])
        if query is None or target is None:
            continue
        if (
            query["role"] != "DEV"
            or target["role"] != "TRAIN"
            or query["candidate_id"] not in dev_by_id
            or not qualifies(row)
        ):
            continue
        hits[query["candidate_id"]][query["side"]] = True
        qualifying_alignments += 1

    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with output_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("candidate_id", "seqid", "left_flank_hit", "right_flank_hit", "purged"),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for candidate in dev:
            candidate_hits = hits[candidate.candidate_id]
            writer.writerow({
                "candidate_id": candidate.candidate_id,
                "seqid": candidate.seqid,
                "left_flank_hit": int(candidate_hits["left"]),
                "right_flank_hit": int(candidate_hits["right"]),
                "purged": int(any(candidate_hits.values())),
            })

    purged = sum(int(any(candidate_hits.values())) for candidate_hits in hits.values())
    census: dict[str, object] = {
        "schema": "gap_bridge_neural_stage1_dev_homology_purge_v1",
        "status": "PASS",
        "manifest_rows": len(candidates),
        "train_candidates": sum(int(candidate.role == "TRAIN") for candidate in candidates),
        "dev_candidates": len(dev),
        "purged_candidates": purged,
        "left_flank_hit_candidates": sum(int(candidate_hits["left"]) for candidate_hits in hits.values()),
        "right_flank_hit_candidates": sum(int(candidate_hits["right"]) for candidate_hits in hits.values()),
        "unpurged_candidates": len(dev) - purged,
        "purged_fraction": None if not dev else purged / len(dev),
        "paf_rows": len(paf_rows),
        "qualifying_alignments": qualifying_alignments,
        "paf_empty": not paf_rows,
        "query_seqids": sorted(DEV_SEQIDS),
        "target_seqids": sorted(TRAIN_SEQIDS),
        "flank_bp": FLANK_BP,
        "contract": {
            "aligned_bp_min": ALIGNED_BP_MIN,
            "identity_min": IDENTITY_MIN,
            "reciprocal_query_target_coverage_min": COVERAGE_MIN,
            "any_dev_flank_hit_purges_candidate": True,
        },
        "output_tsv": str(output_tsv),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return census


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export-flanks")
    export.add_argument("--manifest", type=Path, required=True)
    export.add_argument("--region-jsonl", type=Path, required=True)
    export.add_argument("--role", choices=("TRAIN", "DEV"), required=True)
    export.add_argument("--output-fasta", type=Path, required=True)

    summarize = subparsers.add_parser("summarize-paf")
    summarize.add_argument("--manifest", type=Path, required=True)
    summarize.add_argument("--paf", type=Path, required=True)
    summarize.add_argument("--output-tsv", type=Path, required=True)
    summarize.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "export-flanks":
        export_flanks(args.manifest, args.region_jsonl, args.role, args.output_fasta)
    else:
        summarize_paf(args.manifest, args.paf, args.output_tsv, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
