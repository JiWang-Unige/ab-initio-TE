#!/usr/bin/env python3
"""Reference denominators and provisional exact CDS-chain comparisons for C.

The pinned Tiberius 2.0.7 main.py exports through bricks2marble (lines 486-503
at commit 4d657012a3ed4e923f5d0ac5cef65fecae8109bd), not the legacy
genome_anno.py. Its installed exporter and real output have not yet been
validated here. Consequently every output disables scientific scoring.
Explicit stop-codon union is a provisional coordinate convention; this code
never invents three terminal bases or moves CDS boundaries using GTF phase.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


SEQID = "chr13"
MODES = ("M0", "MW", "MP")


@dataclass(frozen=True)
class Core:
    index: int
    start: int
    end: int
    halo_start: int
    halo_end: int

    @property
    def record_id(self) -> str:
        return (f"{SEQID}|dev_block={self.index}|core={self.start}-{self.end}|"
                f"halo={self.halo_start}-{self.halo_end}")


@dataclass(frozen=True, order=True)
class Chain:
    strand: str
    intervals: tuple[tuple[int, int], ...]


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open(encoding="utf-8")


def load_geometry(path: Path, expected_cores: int = 9) -> list[Core]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    cores = [Core(*(int(row[key]) for key in (
        "block_index", "core_start", "core_end", "halo_start", "halo_end"))) for row in rows]
    if len(cores) != expected_cores or len({c.index for c in cores}) != len(cores):
        raise ValueError(f"geometry must contain {expected_cores} distinct DEV cores")
    cores.sort(key=lambda c: c.start)
    for core in cores:
        if not (0 <= core.halo_start <= core.start < core.end <= core.halo_end):
            raise ValueError("invalid core/halo geometry")
    if any(a.end > b.start for a, b in zip(cores, cores[1:])):
        raise ValueError("DEV cores overlap")
    return cores


def normalize_intervals(intervals) -> tuple[tuple[int, int], ...]:
    """Union touching/overlapping CDS and explicit stops, never bridge introns."""
    result = []
    for start, end in sorted(set(intervals)):
        if start < 0 or end <= start:
            raise ValueError("invalid CDS interval")
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    if not result:
        raise ValueError("empty CDS chain")
    return tuple(result)


def ownership(chain: Chain, cores: list[Core]) -> tuple[Core | None, str | None]:
    owner = next((c for c in cores if c.start <= chain.intervals[0][0] < c.end), None)
    if owner is None:
        return None, "outside_dev_core"
    if chain.intervals[0][0] < owner.halo_start or chain.intervals[-1][1] > owner.halo_end:
        return owner, "boundary_incomplete"
    return owner, None


def chain_record(chain: Chain, owner: Core, source: dict | None = None) -> dict:
    row = {"seqid": SEQID, "strand": chain.strand,
           "cds_intervals": [list(x) for x in chain.intervals], "owner_block_index": owner.index}
    if source:
        row.update(source)
    return row


def read_reference(path: Path, cores: list[Core]):
    """Read only chr13 transcript fields; retain all eligible distinct isoforms."""
    by_core = {core.index: set() for core in cores}
    metadata = {}
    counts = Counter()
    excluded = []
    with open_text(path) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) not in (15, 16):
                raise ValueError(f"genePredExtended line {line_number}: expected 15/16 columns")
            f = fields[1:] if len(fields) == 16 else fields
            if f[1] != SEQID:
                continue
            counts["chr13_transcript_rows"] += 1
            transcript, strand, gene = f[0], f[2], f[11] or f[0]
            if strand not in ("+", "-"):
                raise ValueError(f"invalid strand for {transcript}")
            tx_start, tx_end, cds_start, cds_end, exon_count = map(int, f[3:8])
            starts = [int(x) for x in f[8].rstrip(",").split(",") if x]
            ends = [int(x) for x in f[9].rstrip(",").split(",") if x]
            frames = [int(x) for x in f[14].rstrip(",").split(",") if x]
            if not (0 <= tx_start < tx_end and tx_start <= cds_start <= cds_end <= tx_end):
                raise ValueError(f"invalid transcript/CDS span for {transcript}")
            if not (len(starts) == len(ends) == len(frames) == exon_count and exon_count > 0):
                raise ValueError(f"exon/frame count mismatch for {transcript}")
            if any(s < tx_start or e > tx_end or e <= s for s, e in zip(starts, ends)):
                raise ValueError(f"invalid exon for {transcript}")
            if any(e > s for e, s in zip(ends, starts[1:])):
                raise ValueError(f"unordered/overlapping exons for {transcript}")
            reason = None
            if cds_start == cds_end:
                reason = "noncoding"
            elif f[12] != "cmpl" or f[13] != "cmpl":
                reason = "incomplete_reference_cds"
            intervals = []
            for start, end, frame in zip(starts, ends, frames):
                left, right = max(start, cds_start), min(end, cds_end)
                coding = left < right
                if (coding and frame not in (0, 1, 2)) or (not coding and frame != -1):
                    reason = reason or "invalid_exon_frames"
                if coding:
                    intervals.append((left, right))
            if reason:
                counts[reason] += 1
                excluded.append({"transcript_id": transcript, "reason": reason})
                continue
            chain = Chain(strand, normalize_intervals(intervals))
            owner, reason = ownership(chain, cores)
            if reason:
                counts[reason] += 1
                excluded.append({"transcript_id": transcript, "reason": reason,
                                 "cds_intervals": [list(x) for x in chain.intervals]})
                continue
            counts["eligible_transcript_rows"] += 1
            by_core[owner.index].add(chain)
            entry = metadata.setdefault(chain, {"transcript_ids": set(), "gene_ids": set(), "exon_frames": {}})
            entry["transcript_ids"].add(transcript)
            entry["gene_ids"].add(gene)
            entry["exon_frames"][transcript] = frames
    rows = []
    for core in cores:
        for chain in sorted(by_core[core.index]):
            source = metadata[chain]
            rows.append(chain_record(chain, core, {
                "transcript_ids": sorted(source["transcript_ids"]),
                "gene_ids": sorted(source["gene_ids"]), "exon_frames": source["exon_frames"]}))
    total = sum(map(len, by_core.values()))
    report = {"source": str(path), "counts": dict(counts), "distinct_complete_chains": total,
              "duplicate_eligible_transcript_rows": counts["eligible_transcript_rows"] - total,
              "per_core_denominators": {str(k): len(v) for k, v in by_core.items()},
              "chains": rows, "excluded": excluded,
              "frame_validation": "one entry per exon; coding frames 0/1/2, noncoding -1; phase progression not inferred"}
    return by_core, metadata, report


def read_predictions(path: Path, cores: list[Core], stop_codon_policy: str):
    if stop_codon_policy != "include_stop_union":
        raise ValueError("explicit provisional stop-codon policy include_stop_union is required")
    records = {core.record_id: core for core in cores}
    transcripts = {}
    with open_text(path) as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"GTF line {line_number}: expected nine columns")
            record, _, feature, start, end, _, strand, phase, attrs = fields
            if feature not in ("CDS", "stop_codon"):
                continue
            if record not in records:
                raise ValueError(f"unknown GTF record {record}; expected full mask FASTA record IDs")
            attr = dict(re.findall(r'(\w+)\s+"([^"]*)"', attrs))
            transcript = attr.get("transcript_id")
            if not transcript or strand not in ("+", "-") or phase not in ("0", "1", "2", "."):
                raise ValueError(f"invalid transcript/strand/phase at GTF line {line_number}")
            core = records[record]
            start, end = int(start) - 1, int(end)
            if not 0 <= start < end <= core.halo_end - core.halo_start:
                raise ValueError(f"record-relative GTF coordinates outside input at line {line_number}")
            interval = (start + core.halo_start, end + core.halo_start)
            tx = transcripts.setdefault((record, transcript), {
                "strand": strand, "CDS": [], "stop_codon": [], "phases": [], "core": core})
            if tx["strand"] != strand:
                raise ValueError(f"inconsistent strand for transcript {transcript}")
            tx[feature].append(interval)
            tx["phases"].append({"feature": feature, "genomic_interval": list(interval), "phase": phase})
    by_core = {core.index: set() for core in cores}
    counts, phases = Counter(), Counter()
    phase_records, excluded = [], []
    for (record, transcript), tx in sorted(transcripts.items()):
        counts["transcript_records"] += 1
        phase_records.append({"record_id": record, "transcript_id": transcript, "features": tx["phases"]})
        phases.update(f"{row['feature']}:{row['phase']}" for row in tx["phases"])
        if not tx["CDS"]:
            reason = "no_cds"
        else:
            chain = Chain(tx["strand"], normalize_intervals(tx["CDS"] + tx["stop_codon"]))
            owner, reason = ownership(chain, cores)
            if reason is None and owner.index != tx["core"].index:
                reason = "nonowner_halo_copy"
        if reason:
            counts[reason] += 1
            excluded.append({"record_id": record, "transcript_id": transcript, "reason": reason})
            continue
        counts["eligible_transcript_records"] += 1
        counts["explicit_stop_transcript_records"] += bool(tx["stop_codon"])
        by_core[owner.index].add(chain)
    distinct = sum(map(len, by_core.values()))
    return by_core, {"source": str(path), "counts": dict(counts), "distinct_chains": distinct,
                     "duplicate_eligible_transcript_records": counts["eligible_transcript_records"] - distinct,
                     "excluded": excluded, "phase_counts": dict(phases), "phase_records": phase_records}


def metrics(tp: int, fp: int, fn: int) -> dict:
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "micro_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def evaluate_reference(refseq: Path, geometry: Path, expected_cores: int = 9,
                       predictions: dict[str, Path] | None = None,
                       stop_codon_policy: str | None = None) -> dict:
    cores = load_geometry(geometry, expected_cores)
    truth, metadata, reference_report = read_reference(refseq, cores)
    result = {
        "schema": "gap_bridge_downstream_c_cds_chains_v1",
        "status": "REFERENCE_DENOMINATOR_READY" if predictions is None else "PROVISIONAL_PAIRED_ENGINEERING_ONLY",
        "scientific_claim": False, "scientific_scoring_enabled": False,
        "real_tiberius_export_convention_verified": False,
        "scope": "chr13 DEV only; no confirmatory release",
        "geometry": str(geometry), "core_count": len(cores),
        "ownership": "minimum genomic CDS start in core; entire chain within owner halo; owner record only",
        "reference": reference_report,
        "stop_codon_policy": stop_codon_policy,
        "stop_codon_policy_status": "provisional; explicit stop_codon union only; no inferred extension or phase trimming",
        "exporter_evidence": "Tiberius 2.0.7 commit 4d657012a3ed4e923f5d0ac5cef65fecae8109bd main.py uses bricks2marble; installed exporter and real output not verified",
    }
    if predictions is None:
        return result
    if set(predictions) != set(MODES):
        raise ValueError("paired comparison requires exactly M0, MW and MP")
    if stop_codon_policy != "include_stop_union":
        raise ValueError("paired evaluation requires --stop-codon-policy include_stop_union")
    correct, all_predictions, reports = {}, {}, {}
    for mode in MODES:
        predicted, report = read_predictions(predictions[mode], cores, stop_codon_policy)
        per_core = {}
        tp = fp = fn = 0
        correct[mode], all_predictions[mode] = set(), set()
        for core in cores:
            t, p = truth[core.index], predicted[core.index]
            ct, cf, cn = len(t & p), len(p - t), len(t - p)
            per_core[str(core.index)] = metrics(ct, cf, cn)
            tp, fp, fn = tp + ct, fp + cf, fn + cn
            correct[mode].update(t & p)
            all_predictions[mode].update(p)
        reports[mode] = {"metrics": metrics(tp, fp, fn), "per_core": per_core, "input_audit": report}
    m0_correct = correct["M0"]
    truth_union = set().union(*truth.values())
    paired = {}
    for mode in ("MW", "MP"):
        lost, gained = m0_correct - correct[mode], correct[mode] - m0_correct
        def describe(chains):
            return [chain_record(chain, ownership(chain, cores)[0], {
                "gene_ids": sorted(metadata[chain]["gene_ids"]),
                "transcript_ids": sorted(metadata[chain]["transcript_ids"])}) for chain in sorted(chains)]
        new_unmatched = (all_predictions[mode] - truth_union) - (all_predictions["M0"] - truth_union)
        paired[mode] = {
            "gained_correct_chains": len(gained), "lost_correct_chains": len(lost),
            "m0_correct_chain_denominator": len(m0_correct),
            "lost_correct_fraction_of_m0": len(lost) / len(m0_correct) if m0_correct else None,
            "gained": describe(gained), "lost": describe(lost),
            "new_unmatched_predictions": len(new_unmatched),
            "micro_f1_delta_vs_m0": (
                reports[mode]["metrics"]["micro_f1"] - reports["M0"]["metrics"]["micro_f1"]
                if reports[mode]["metrics"]["micro_f1"] is not None
                and reports["M0"]["metrics"]["micro_f1"] is not None else None),
        }
    result.update({"modes": reports, "paired_vs_m0": paired,
                   "pass_criteria_applied": False,
                   "limitation": "exact coordinate chain comparison only; real exporter/stop convention remains unverified; no biological sequence validation"})
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", required=True, type=Path)
    parser.add_argument("--refseq", required=True, type=Path)
    parser.add_argument("--expected-cores", type=int, default=9)
    parser.add_argument("--reference-only", action="store_true")
    for mode in MODES:
        parser.add_argument(f"--{mode.lower()}", type=Path)
    parser.add_argument("--stop-codon-policy", choices=["include_stop_union"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    predictions = {mode: getattr(args, mode.lower()) for mode in MODES}
    if args.reference_only:
        if any(predictions.values()):
            parser.error("--reference-only cannot receive predicted GTF files")
        predictions = None
    elif not all(predictions.values()) or args.stop_codon_policy is None:
        parser.error("provide --reference-only or all three GTF files plus --stop-codon-policy")
    if args.output.exists():
        parser.error("output already exists; choose a fresh result path")
    result = evaluate_reference(args.refseq, args.geometry, args.expected_cores,
                                predictions, args.stop_codon_policy)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "reference_chains": result["reference"]["distinct_complete_chains"],
                      "scientific_scoring_enabled": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
