#!/usr/bin/env python3
"""Summarise raw-RNA support for a frozen, blind prediction union.

The candidate panel is made before this script is run and contains the union of
all D/U_soft/R_TE transcript exon chains.  No reference annotation is needed
for the primary endpoints.  A reference join can be supplied for a separate,
post-hoc audit of the historical gain/loss sets; it never changes the primary
denominators.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--junctions", type=Path, required=True)
    ap.add_argument("--stringtie", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--hisat2-summary", type=Path)
    ap.add_argument("--geometry", type=Path)
    ap.add_argument(
        "--coordinate-mode",
        choices=("panel", "assembly"),
        default="assembly",
        help="panel keeps native local coordinates; assembly projects them via geometry",
    )
    ap.add_argument("--reference-json", type=Path)
    ap.add_argument("--historical-result", type=Path)
    return ap.parse_args()


def parse_attrs(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in re.finditer(r'([^\s;]+)\s+"([^"]*)"', text):
        result[match.group(1)] = match.group(2)
    return result


def as_chain(exons: Iterable[Iterable[int]]) -> tuple[tuple[int, int], ...]:
    return tuple(sorted((int(a), int(b)) for a, b in exons))


def parse_junctions(path: Path) -> dict[tuple[str, int, int], dict[str, int]]:
    """Read the custom six-column CIGAR junction summary.

    The columns are contig, intron start/end, all NH=1 templates, strict
    overhang NH=1 templates, and maximum overhang.  This is intentionally not
    STAR's ``SJ.out.tab``.  The unstranded protocol keys on contig and
    coordinates; read-strand labels are not used to reject evidence.
    """

    rows: dict[tuple[str, int, int], dict[str, int]] = {}
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 6:
                raise ValueError(f"{path}:{line_no}: expected six CIGAR-junction columns")
            seqname = fields[0]
            key = (seqname, int(fields[1]), int(fields[2]))
            current = {
                "unique": int(fields[3]),
                "strict_unique": int(fields[4]),
                "overhang": int(fields[5]),
            }
            previous = rows.get(key)
            if previous is None or (current["unique"], current["strict_unique"], current["overhang"]) > (
                previous["unique"],
                previous["strict_unique"],
                previous["overhang"],
            ):
                rows[key] = current
    return rows


def parse_stringtie(path: Path) -> list[dict]:
    """Read de-novo StringTie transcript exon chains."""

    transcripts: dict[tuple[str, str, str], dict] = {}
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"{path}:{line_no}: expected 9 GTF columns")
            seqname, _source, feature, start, end, _score, strand, _frame, raw = fields
            if feature != "exon":
                continue
            a = parse_attrs(raw)
            tid = a.get("transcript_id")
            if not tid:
                continue
            key = (seqname, strand, tid)
            row = transcripts.setdefault(
                key,
                {"seqname": seqname, "strand": strand, "transcript_id": tid, "exons": []},
            )
            row["exons"].append([int(start), int(end)])
    out = []
    for row in transcripts.values():
        row["exons"] = [list(x) for x in as_chain(row["exons"])]
        row["intron_count"] = len(row["exons"]) - 1
        out.append(row)
    return out


def candidate_evidence(
    candidate: dict,
    sj: dict,
    stringtie_by_intron: dict,
    stringtie_any_intron: dict,
    stringtie_by_full: dict,
    stringtie_any_full: dict,
) -> dict:
    # ``evidence_*`` is the native coordinate contract for the alignment
    # reference.  The original candidate fields remain the local panel fields.
    seq = candidate.get("evidence_seqname", candidate["seqname"])
    exons = [tuple(x) for x in candidate.get("evidence_exons", candidate["exons"])]
    expected = [
        (left[1] + 1, right[0] - 1)
        for left, right in zip(exons, exons[1:])
    ]
    junction_rows = [sj.get((seq, start, end)) for start, end in expected]
    strict = [bool(row and row["strict_unique"] >= 3) for row in junction_rows]
    any_unique = [bool(row and row["unique"] >= 1) for row in junction_rows]
    unique_counts = [row["unique"] if row else 0 for row in junction_rows]
    overhangs = [row["overhang"] if row else 0 for row in junction_rows]
    intron_chain = tuple((left[1] + 1, right[0] - 1) for left, right in zip(exons, exons[1:]))
    intron_key = (seq, candidate["strand"], intron_chain)
    any_intron_key = (seq, intron_chain)
    full_key = (seq, candidate["strand"], tuple(exons))
    any_full_key = (seq, tuple(exons))
    # With unstranded RNA, StringTie can emit '.', so the strand-aware endpoint
    # permits '.' as an unknown strand while retaining a separate any-strand
    # diagnostic below.
    stringtie_intron = bool(stringtie_by_intron.get(intron_key, False) or stringtie_by_intron.get(
        (seq, ".", intron_chain), False
    ))
    stringtie_intron_any = bool(stringtie_any_intron.get(any_intron_key, False))
    stringtie_full = bool(stringtie_by_full.get(full_key, False) or stringtie_by_full.get(
        (seq, ".", tuple(exons)), False
    ))
    stringtie_full_any = bool(stringtie_any_full.get(any_full_key, False))
    result = {
        "candidate_id": candidate["candidate_id"],
        "seqname": candidate["seqname"],
        "evidence_seqname": seq,
        "strand": candidate["strand"],
        "evidence_exons": [list(x) for x in exons],
        "arms": candidate["arms"],
        "intron_count": len(expected),
        "strict_supported_introns": sum(strict),
        "any_unique_supported_introns": sum(any_unique),
        "strict_intron_fraction": (sum(strict) / len(expected)) if expected else None,
        "any_unique_intron_fraction": (sum(any_unique) / len(expected)) if expected else None,
        "all_introns_strict": bool(expected) and all(strict),
        "any_intron_strict": bool(expected) and any(strict),
        "max_unique_junction_reads": max(unique_counts, default=0),
        "max_splice_overhang": max(overhangs, default=0),
        "stringtie_exact_intron_chain": bool(expected) and stringtie_intron,
        "stringtie_exact_intron_chain_any_strand": bool(expected) and stringtie_intron_any,
        "stringtie_exact_full_chain": stringtie_full,
        "stringtie_exact_full_chain_any_strand": stringtie_full_any,
        "occurrences": candidate["occurrences"],
    }
    return result


def aggregate(rows: list[dict]) -> dict:
    by_arm: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        for arm in row["arms"]:
            by_arm[arm].append(row)

    def summarize(subset: list[dict]) -> dict:
        intron_rows = [x for x in subset if x["intron_count"] > 0]
        return {
            "candidate_count": len(subset),
            "multi_exon_count": len(intron_rows),
            "all_introns_strict_count": sum(x["all_introns_strict"] for x in intron_rows),
            "all_introns_strict_rate": (
                sum(x["all_introns_strict"] for x in intron_rows) / len(intron_rows)
                if intron_rows
                else None
            ),
            "any_intron_strict_count": sum(x["any_intron_strict"] for x in intron_rows),
            "any_intron_strict_rate": (
                sum(x["any_intron_strict"] for x in intron_rows) / len(intron_rows)
                if intron_rows
                else None
            ),
            "mean_strict_intron_fraction": (
                sum(x["strict_intron_fraction"] for x in intron_rows) / len(intron_rows)
                if intron_rows
                else None
            ),
            "stringtie_exact_intron_chain_count": sum(x["stringtie_exact_intron_chain"] for x in intron_rows),
            "stringtie_exact_intron_chain_rate": (
                sum(x["stringtie_exact_intron_chain"] for x in intron_rows) / len(intron_rows)
                if intron_rows
                else None
            ),
            "stringtie_exact_intron_chain_any_strand_count": sum(
                x["stringtie_exact_intron_chain_any_strand"] for x in intron_rows
            ),
            "stringtie_exact_intron_chain_any_strand_rate": (
                sum(x["stringtie_exact_intron_chain_any_strand"] for x in intron_rows) / len(intron_rows)
                if intron_rows
                else None
            ),
            "stringtie_exact_full_chain_count": sum(x["stringtie_exact_full_chain"] for x in subset),
            "stringtie_exact_full_chain_rate": (
                sum(x["stringtie_exact_full_chain"] for x in subset) / len(subset)
                if subset
                else None
            ),
            "stringtie_exact_full_chain_any_strand_count": sum(
                x["stringtie_exact_full_chain_any_strand"] for x in subset
            ),
            "stringtie_exact_full_chain_any_strand_rate": (
                sum(x["stringtie_exact_full_chain_any_strand"] for x in subset) / len(subset)
                if subset
                else None
            ),
        }

    overlap = Counter("+".join(row["arms"]) for row in rows)
    return {
        "by_arm": {arm: summarize(by_arm[arm]) for arm in sorted(by_arm)},
        "by_arm_overlap": dict(sorted(overlap.items())),
        "all_candidates": summarize(rows),
    }


def parse_hisat2_summary(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {"available": False}
    lines = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    stats: dict[str, object] = {"available": True, "lines": lines}
    if lines:
        match = re.match(r"\s*([0-9,]+) reads;", lines[0])
        if match:
            stats["total_reads"] = int(match.group(1).replace(",", ""))
    return stats


def reference_join(rows: list[dict], reference_path: Path, historical_path: Path, geometry_path: Path) -> dict:
    """Join candidate chains to the NCBI reference only after evidence scoring."""

    geometry = {x["id"]: x for x in json.loads(geometry_path.read_text(encoding="utf-8"))}
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    # Candidate coordinates are local 1-based coordinates on a half-open
    # sequence beginning at halo_start.  Convert reference's assembly 1-based
    # coordinates into the same local contract.
    ref_lookup: dict[tuple[str, str, tuple[tuple[int, int], ...]], set[str]] = defaultdict(set)
    for unit in reference.get("units", []):
        core = geometry[unit["core_id"]]
        record_id = next(
            x["record_id"] for x in geometry.values() if x["id"] == unit["core_id"]
        )
        for iso in unit.get("isoforms", []):
            local = []
            for start, end in iso["intervals"]:
                # Reference intervals are zero-based half-open.  Candidate
                # GTF intervals are one-based inclusive on the local panel.
                local.append(
                    (
                        int(start) - int(core["halo_start"]) + 1,
                        int(end) - int(core["halo_start"]),
                    )
                )
            ref_lookup[(record_id, iso["strand"], tuple(local))].add(unit["unit_id"])

    matched: dict[str, set[str]] = defaultdict(set)
    # Re-read the candidate chains so matching remains independent from the
    # historical result's gene labels.
    candidates = json.loads(Path(rows[0]["_candidate_source"]).read_text(encoding="utf-8")) if rows and rows[0].get("_candidate_source") else None
    if candidates is None:
        raise ValueError("internal candidate source marker missing")
    for candidate in candidates["candidates"]:
        local_chain = tuple(tuple(x) for x in candidate["exons"])
        for unit_id in ref_lookup.get((candidate["seqname"], candidate["strand"], local_chain), set()):
            matched[candidate["candidate_id"]].add(unit_id)
        # Permit an unknown strand in a reference join only as a diagnostic.
        for unit_id in ref_lookup.get((candidate["seqname"], ".", local_chain), set()):
            matched[candidate["candidate_id"]].add(unit_id)

    historical = json.loads(historical_path.read_text(encoding="utf-8"))
    row_by_id = {row["candidate_id"]: row for row in rows}
    unit_to_candidates: dict[str, list[str]] = defaultdict(list)
    for cid, units in matched.items():
        for unit in units:
            unit_to_candidates[unit].append(cid)

    comparison_summary = {}
    for name, comp in historical.get("comparisons", {}).items():
        for label in ("gained_loci", "lost_loci"):
            units = comp.get(label, [])
            cids = [cid for unit in units for cid in unit_to_candidates.get(unit, [])]
            ev = [row_by_id[cid] for cid in cids]
            comparison_summary.setdefault(name, {})[label] = {
                "historical_unit_count": len(units),
                "matched_candidate_count": len(set(cids)),
                "matched_unit_count": sum(bool(unit_to_candidates.get(unit)) for unit in units),
                "all_introns_strict_count": sum(x["all_introns_strict"] for x in ev),
                "stringtie_exact_intron_chain_count": sum(x["stringtie_exact_intron_chain"] for x in ev),
                "stringtie_exact_full_chain_count": sum(x["stringtie_exact_full_chain"] for x in ev),
                "candidate_ids": sorted(set(cids)),
            }
    return {
        "performed_posthoc": True,
        "reference_annotation_used_for_primary_selection": False,
        "matched_reference_isoform_chains": sum(bool(x) for x in matched.values()),
        "comparison_sets": comparison_summary,
    }


def main() -> None:
    args = parse_args()
    payload = json.loads(args.candidates.read_text(encoding="utf-8"))
    candidates = payload["candidates"]
    sj = parse_junctions(args.junctions)
    stringtie = parse_stringtie(args.stringtie)
    stringtie_by_intron = {}
    stringtie_any_intron = {}
    stringtie_by_full = {}
    stringtie_any_full = {}
    for x in stringtie:
        exons = tuple(tuple(e) for e in x["exons"])
        introns = tuple((left[1] + 1, right[0] - 1) for left, right in zip(exons, exons[1:]))
        stringtie_by_intron[(x["seqname"], x["strand"], introns)] = True
        stringtie_any_intron[(x["seqname"], introns)] = True
        stringtie_by_full[(x["seqname"], x["strand"], exons)] = True
        stringtie_any_full[(x["seqname"], exons)] = True
    if args.coordinate_mode == "assembly":
        if args.geometry is None:
            raise SystemExit("--geometry is required in assembly coordinate mode")
        geometry = json.loads(args.geometry.read_text(encoding="utf-8"))
        by_record = {x["record_id"]: x for x in geometry}
        projected = []
        for candidate in candidates:
            record = by_record.get(candidate["seqname"])
            if record is None:
                raise SystemExit(f"candidate contig is absent from geometry: {candidate['seqname']}")
            chrom = record["chrom"]
            # Candidate GTF intervals are one-based inclusive; the assembly
            # reference and StringTie GTF use the same visible convention.
            # geometry.halo_start is a zero-based half-open assembly offset.
            offset = int(record["halo_start"])
            item = dict(candidate)
            item["evidence_seqname"] = chrom
            item["evidence_exons"] = [
                [int(start) + offset, int(end) + offset] for start, end in candidate["exons"]
            ]
            projected.append(item)
    else:
        projected = candidates
    rows = [
        candidate_evidence(
            x,
            sj,
            stringtie_by_intron,
            stringtie_any_intron,
            stringtie_by_full,
            stringtie_any_full,
        )
        for x in projected
    ]
    result = {
        "schema": "platypus_gene_evidence_v1",
        "status": "COMPLETED",
        "protocol": "PLATYPUS-GENE-EVIDENCE-20260917",
        "candidate_count": len(rows),
        "junction_count": len(sj),
        "stringtie_transcript_count": len(stringtie),
        "candidate_selection": payload.get("selection"),
        "coordinate_mode": args.coordinate_mode,
        "reference_annotation_used_for_primary_selection": False,
        "raw_rna_support": aggregate(rows),
        "hisat2": parse_hisat2_summary(args.hisat2_summary),
        "notes": [
            "RNA support is evidence for transcription/splicing in one adult-male fibroblast run.",
            "Absence of support is not evidence that a predicted gene is false.",
            "StringTie support is de novo assembly from the same raw RNA run, not an independent gold standard.",
            "The primary StringTie endpoint is exact multi-exon intron-chain support; full exon-chain equality is a stricter diagnostic because UTR endpoints can differ.",
        ],
    }
    if args.reference_json or args.historical_result:
        if not (args.reference_json and args.historical_result and args.geometry):
            raise SystemExit("reference join requires --reference-json, --historical-result, and --geometry")
        # The helper needs input chains without making them part of the public
        # result.  Use a private marker, then remove it before writing.
        for row in rows:
            row["_candidate_source"] = str(args.candidates)
        result["posthoc_reference_join"] = reference_join(
            rows, args.reference_json, args.historical_result, args.geometry
        )
        for row in rows:
            row.pop("_candidate_source", None)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "evidence_by_candidate.json").write_text(
        json.dumps({"schema": "platypus_gene_evidence_candidates_v1", "candidates": rows}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    with (args.out_dir / "evidence_by_candidate.tsv").open("w", encoding="utf-8") as out:
        out.write(
            "candidate_id\tseqname\tstrand\tarms\tintron_count\tstrict_supported_introns\t"
            "strict_intron_fraction\tall_introns_strict\tstringtie_exact_intron_chain\t"
            "stringtie_exact_intron_chain_any_strand\tstringtie_exact_full_chain\t"
            "stringtie_exact_full_chain_any_strand\n"
        )
        for row in rows:
            out.write(
                "\t".join(
                    [
                        row["candidate_id"],
                        row["seqname"],
                        row["strand"],
                        ",".join(row["arms"]),
                        str(row["intron_count"]),
                        str(row["strict_supported_introns"]),
                        "" if row["strict_intron_fraction"] is None else f'{row["strict_intron_fraction"]:.6f}',
                        str(int(row["all_introns_strict"])),
                        str(int(row["stringtie_exact_intron_chain"])),
                        str(int(row["stringtie_exact_intron_chain_any_strand"])),
                        str(int(row["stringtie_exact_full_chain"])),
                        str(int(row["stringtie_exact_full_chain_any_strand"])),
                    ]
                )
                + "\n"
            )
    (args.out_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_count": len(rows), "junction_count": len(sj), "stringtie_transcript_count": len(stringtie)}, indent=2))


if __name__ == "__main__":
    main()
