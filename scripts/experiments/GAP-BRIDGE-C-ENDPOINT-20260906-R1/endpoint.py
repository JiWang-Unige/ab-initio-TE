#!/usr/bin/env python3
"""Bounded C readiness: native CDS endpoints, never auxiliary stop union."""
from __future__ import annotations
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

OLD = Path(__file__).resolve().parents[1] / "GAP-BRIDGE-DOWNSTREAM-C-R1/evaluate_chains.py"
spec = importlib.util.spec_from_file_location("c_reference", OLD)
reference = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reference
spec.loader.exec_module(reference)
Core, Chain = reference.Core, reference.Chain

def fasta_rows(path):
    name, parts = None, []
    with Path(path).open() as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(parts)
                name, parts = line[1:].strip(), []
            else:
                parts.append(line.strip())
    if name is not None:
        yield name, "".join(parts)

def save(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")

def read_cds(path, cores, fmt="gtf"):
    records = {c.record_id: c for c in cores}
    txs = {}
    cds_rows = 0
    with Path(path).open() as handle:
        for n, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip().split("\t")
            if len(fields) != 9:
                raise ValueError(f"annotation line {n}: expected 9 columns")
            record, _, feature, left, right, _, strand, phase, attrs = fields
            if feature != "CDS":
                continue
            record = unquote(record) if fmt == "gff3" else record
            if record not in records or strand not in ("+", "-") or phase not in (".", "0", "1", "2"):
                raise ValueError(f"invalid CDS record/strand/phase at line {n}")
            if fmt == "gtf":
                ids = [dict(re.findall(r'(\w+)\s+"([^"]*)"', attrs)).get("transcript_id")]
            else:
                attributes = dict(item.split("=", 1) for item in attrs.split(";") if "=" in item)
                ids = [unquote(x) for x in attributes.get("Parent", "").split(",")]
            if not all(ids):
                raise ValueError(f"missing CDS transcript at line {n}")
            core = records[record]
            start, end = int(left) - 1, int(right)
            if not 0 <= start < end <= core.halo_end - core.halo_start:
                raise ValueError(f"CDS outside halo at line {n}")
            cds_rows += 1
            for tid in ids:
                tx = txs.setdefault((record, tid), {"strand": strand, "intervals": []})
                if tx["strand"] != strand:
                    raise ValueError(f"inconsistent strand for {tid}")
                tx["intervals"].append((start + core.halo_start, end + core.halo_start))
    by_core = {c.index: set() for c in cores}
    counts, signatures = Counter(), []
    for (record, tid), tx in sorted(txs.items()):
        intervals = tuple(sorted(set(tx["intervals"])))
        if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
            raise ValueError(f"overlapping native CDS blocks in {tid}")
        chain = Chain(tx["strand"], intervals)
        # Transcript IDs differ between GTF and GFF3; compare content multiplicity.
        signatures.append((record, chain.strand, chain.intervals))
        owner, reason = reference.ownership(chain, cores)
        if reason is None and owner.index != records[record].index:
            reason = "nonowner_halo_copy"
        if reason:
            counts[reason] += 1
        else:
            counts["eligible_transcript_records"] += 1
            by_core[owner.index].add(chain)
    distinct = sum(map(len, by_core.values()))
    return by_core, {"cds_rows": cds_rows, "transcript_records": len(txs), "distinct_chains": distinct,
                     "counts": dict(counts), "duplicate_eligible_transcript_records": counts["eligible_transcript_records"] - distinct,
                     "all_cds_signatures": sorted(signatures)}

def prepare(cfg, out):
    out.mkdir(parents=True, exist_ok=False)
    cores = reference.load_geometry(Path(cfg["masks"]) / "geometry.tsv")
    selected = [next(c for c in cores if c.index == i) for i in cfg["core_order"]]
    sequences = {}
    for mode in cfg["prepare_modes"]:
        found = {name: seq for name, seq in fasta_rows(Path(cfg["masks"]) / f"{mode}.fasta")
                 if name in {c.record_id for c in selected}}
        if set(found) != {c.record_id for c in selected}:
            raise ValueError("missing selected complete core records")
        sequences[mode] = found
    report = []
    for c in selected:
        target = out / f"core{c.index}"
        target.mkdir()
        baseline = sequences["M0"][c.record_id]
        for mode in cfg["prepare_modes"]:
            seq = sequences[mode][c.record_id]
            if len(seq) != c.halo_end - c.halo_start or seq.upper() != baseline.upper():
                raise ValueError("FASTA letters or full halo length differ")
            with (target / f"{mode}.fasta").open("x") as handle:
                handle.write(f">{c.record_id}\n")
                for offset in range(0, len(seq), 80):
                    handle.write(seq[offset:offset+80] + "\n")
            report.append({"core": c.index, "mode": mode, "bp": len(seq),
                           "lowercase_acgt": sum(x in "acgt" for x in seq)})
    save(out / "preparation.json", {"same_uppercase_letters": True, "full_core_plus_halo": True, "records": report})

def preflight(cfg, out):
    import numpy as np
    from bricks2marble.struct.annotation import Transcript, CDS
    from bricks2marble.io import load_fasta
    cores = reference.load_geometry(Path(cfg["masks"]) / "geometry.tsv")
    truth, metadata, report = reference.read_reference(Path(cfg["refseq"]), cores)
    if report["distinct_complete_chains"] != cfg["reference_expected_distinct_chains"] or report["counts"]["eligible_transcript_rows"] != cfg["reference_expected_eligible_rows"]:
        raise ValueError("reference denominator changed")
    export = out / "reference_native_export.gtf"
    count = 0
    with export.open("x") as handle:
        for core in cores:
            for chain in sorted(truth[core.index]):
                for tid in sorted(metadata[chain]["transcript_ids"]):
                    tx = Transcript(name=f"row{count}_{tid}", sequence=core.record_id, strand=chain.strand,
                                    cds=[CDS(start=s-core.halo_start, end=e-core.halo_start) for s, e in chain.intervals])
                    handle.write(tx.to_gtf_rows(source="real_container_exporter") + "\n")
                    count += 1
    recovered, parsed = read_cds(export, cores)
    if recovered != truth or count != cfg["reference_expected_eligible_rows"] or parsed["transcript_records"] != count:
        raise ValueError("real exporter roundtrip failed")
    tracks = []
    for index in cfg["core_order"]:
        first = None
        for mode in cfg["prepare_modes"]:
            path = out / f"core{index}" / f"{mode}.fasta"
            raw = list(fasta_rows(path))[0][1]
            encoded = load_fasta(path).one_hot()
            expected_mask = np.fromiter((x in "acgt" for x in raw), dtype=np.bool_)
            if encoded.shape != (1, len(raw), 6) or not np.array_equal(encoded[0, :, 5], expected_mask):
                raise ValueError("actual FASTA loader/one_hot softmask differs from input case")
            if first is None:
                first = encoded[0, :, :5].copy()
            elif not np.array_equal(first, encoded[0, :, :5]):
                raise ValueError("one_hot first five tracks change with masking")
            tracks.append({"core": index, "mode": mode, "shape": list(encoded.shape), "masked_bp": int(expected_mask.sum())})
            del encoded
    save(out / "preflight.json", {"status": "PREFLIGHT_PASS", "claim_eligible": False,
         "real_exporter": "bricks2marble.struct.annotation.Transcript.to_gtf_rows",
         "distinct_chains": parsed["distinct_chains"], "source_rows": count,
         "strands": sorted({c.strand for values in truth.values() for c in values}),
         "duplicate_source_rows": count-parsed["distinct_chains"],
         "codon_sequence_and_phase_progression_audit": "not performed; native intervals only",
         "tracks": tracks})

def audit_coding_sequences(signatures, fasta_path, cores):
    """Describe actual predicted CDS sequence; never filter predictions."""
    sequences = dict(fasta_rows(fasta_path))
    geometry = {c.record_id: c for c in cores}
    starts, stops, lengths = Counter(), Counter(), Counter()
    total = terminal_stops = atg_starts = internal_stops = 0
    complement = str.maketrans("ACGTN", "TGCAN")
    for record, strand, intervals in signatures:
        raw, c = sequences[record].upper(), geometry[record]
        coding = "".join(raw[s-c.halo_start:e-c.halo_start] for s, e in intervals)
        if strand == "-":
            coding = coding.translate(complement)[::-1]
        total += 1
        starts[coding[:3]] += 1
        stops[coding[-3:]] += 1
        lengths[str(len(coding) % 3)] += 1
        atg_starts += coding[:3] == "ATG"
        terminal_stops += coding[-3:] in {"TAA", "TAG", "TGA"}
        internal_stops += any(coding[i:i+3] in {"TAA", "TAG", "TGA"} for i in range(0, len(coding)-3, 3))
    return {"transcript_records": total, "start_codon_counts": dict(starts),
            "terminal_codon_counts": dict(stops), "length_mod3_counts": dict(lengths),
            "atg_start_records": atg_starts, "terminal_stop_records": terminal_stops,
            "internal_inframe_stop_records": internal_stops,
            "all_native_cds_include_terminal_stop": bool(total) and terminal_stops == total,
            "filter_applied": False, "phase_progression_audit": "not performed"}

def evaluate(cfg, out, index, gtf, gff3, observation):
    cores = reference.load_geometry(Path(cfg["masks"]) / "geometry.tsv")
    if index not in cfg["core_order"]:
        raise ValueError("core is not predeclared")
    p, report = read_cds(gtf, cores)
    q, other = read_cds(gff3, cores, "gff3")
    if p != q or report["all_cds_signatures"] != other["all_cds_signatures"]:
        raise ValueError("GTF/GFF3 native CDS disagree")
    observed = json.loads(Path(observation).read_text())
    if observed["calls"] < 1 or not observed["passed"]:
        raise ValueError("no verified actual inference Fasta.one_hot call")
    truth, _, _ = reference.read_reference(Path(cfg["refseq"]), cores)
    t, pred = truth[index], p[index]
    codons = audit_coding_sequences(report["all_cds_signatures"], out / f"core{index}" / "M0.fasta", cores)
    report.pop("all_cds_signatures")
    result = {"status": "NONEMPTY_ENDPOINT_READY" if report["cds_rows"] else "EMPTY_M0",
              "primary_metric": int(report["cds_rows"] > 0),
              "primary_metric_name": "engineering_endpoint_nonempty",
              "claim_eligible": False, "scientific_scoring_enabled": False, "core": index, "mode": "M0",
              "native_cds_gtf_gff3_equal": True, "prediction": report,
              "actual_prediction_codon_audit": codons,
              "descriptive_exact_chain_metrics": reference.metrics(len(t & pred), len(pred-t), len(t-pred)),
              "reference_core_chains": len(t), "observation": observed}
    save(out / f"core{index}" / "evaluation.json", result)
    print(result["status"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "preflight", "evaluate"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--core", type=int)
    parser.add_argument("--gtf", type=Path)
    parser.add_argument("--gff3", type=Path)
    parser.add_argument("--observation", type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    out = args.output_dir or Path(cfg["output_dir"])
    if args.action == "prepare":
        prepare(cfg, out)
    elif args.action == "preflight":
        preflight(cfg, out)
    else:
        if any(x is None for x in [args.core, args.gtf, args.gff3, args.observation]):
            parser.error("evaluate requires --core --gtf --gff3 --observation")
        evaluate(cfg, out, args.core, args.gtf, args.gff3, args.observation)

if __name__ == "__main__":
    main()
