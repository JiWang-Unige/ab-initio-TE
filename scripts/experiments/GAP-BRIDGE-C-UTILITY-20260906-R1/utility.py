#!/usr/bin/env python3
"""Fixed chr13 DEV paired mask utility; no fitted parameters or label edits."""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter
import importlib.util
import json
from pathlib import Path

EP_PATH = Path(__file__).resolve().parents[1] / "GAP-BRIDGE-C-ENDPOINT-20260906-R1/endpoint.py"
spec = importlib.util.spec_from_file_location("native_endpoint", EP_PATH)
ep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep)
ref = ep.reference
CORE_ORDER = [0, 1, 2, 6, 10, 14, 15, 18, 20]
MODES = ["M0", "MW", "MP"]


def write_json(path, value):
    """Publish only a fully serialized new artifact."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
    temporary.rename(path)


def config(path):
    cfg = json.loads(Path(path).read_text())
    if cfg["core_order"] != CORE_ORDER or cfg["predict_modes"] != MODES or cfg["prepare_modes"] != MODES:
        raise ValueError("all nine fixed DEV cores and all three modes are required")
    if cfg["gate"] != {"micro_f1_delta_strictly_positive": True,
                       "min_gained_correct_chains": 1, "max_lost_correct_chains": 0}:
        raise ValueError("approved gate changed")
    if not cfg["scientific_scoring_enabled"] or cfg["claim_eligible"]:
        raise ValueError("exploratory scoring only")
    cores = ref.load_geometry(Path(cfg["masks"]) / "geometry.tsv")
    if [c.index for c in cores] != CORE_ORDER:
        raise ValueError("geometry does not match original DEV cores")
    return cfg, cores


def annotation_features(path):
    """All chr13 RefSeq transcripts, not just the eligible scoring chains."""
    features = {name: [] for name in ("CDS", "exon", "splice_dinucleotide")}
    with ref.open_text(Path(path)) as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            f = line.rstrip().split("\t")
            if len(f) == 16:
                f = f[1:]
            if len(f) != 15:
                raise ValueError("expected genePredExtended")
            if f[1] != "chr13":
                continue
            starts = [int(x) for x in f[8].rstrip(",").split(",")]
            ends = [int(x) for x in f[9].rstrip(",").split(",")]
            if len(starts) != len(ends) or len(starts) != int(f[7]):
                raise ValueError("exon count mismatch")
            cds_start, cds_end, gene = int(f[5]), int(f[6]), f[11] or f[0]
            for start, end in zip(starts, ends):
                if start >= end:
                    raise ValueError("invalid exon")
                features["exon"].append((start, end, gene))
                left, right = max(start, cds_start), min(end, cds_end)
                if left < right:
                    features["CDS"].append((left, right, gene))
            for left, right in zip(ends, starts[1:]):
                if left > right:
                    raise ValueError("overlapping exons")
                if left < right:
                    features["splice_dinucleotide"].extend(
                        [(left, min(left+2, right), gene), (max(left, right-2), right, gene)])
    return features


def changed_positions(baseline, changed, core):
    if len(baseline) != core.halo_end-core.halo_start or len(changed) != len(baseline):
        raise ValueError("input halo length differs")
    positions = []
    for i, (before, after) in enumerate(zip(baseline, changed)):
        if before == after:
            continue
        if before not in "ACGT" or after != before.lower():
            raise ValueError("mask intervention changed letters, removed mask, or changed N")
        pos = core.halo_start + i
        if not core.start <= pos < core.end:
            raise ValueError("added mask outside owner core")
        positions.append(pos)
    return positions


def feature_risk(positions, features):
    result = {}
    for kind, intervals in features.items():
        hit_positions, genes = set(), set()
        for start, end, gene in intervals:
            left, right = bisect_left(positions, start), bisect_left(positions, end)
            if right > left:
                hit_positions.update(positions[left:right])
                genes.add(gene)
        result[kind] = {"added_mask_overlap_bp": len(hit_positions), "genes": sorted(genes),
                        "gene_count": len(genes)}
    return result


def risk_audit(cfg, cores, out):
    features = annotation_features(cfg["refseq"])
    total = {mode: [] for mode in ("MW", "MP")}
    per_core = {}
    for core in cores:
        sequences = {}
        for mode in MODES:
            records = list(ep.fasta_rows(out / f"core{core.index}" / f"{mode}.fasta"))
            if len(records) != 1 or records[0][0] != core.record_id:
                raise ValueError("wrong core FASTA record")
            sequences[mode] = records[0][1]
        per_core[str(core.index)] = {}
        for mode in ("MW", "MP"):
            positions = changed_positions(sequences["M0"], sequences[mode], core)
            total[mode].extend(positions)
            per_core[str(core.index)][mode] = {"added_mask_bp": len(positions),
                                             "features": feature_risk(positions, features)}
    result = {"reference_scope": "all chr13 RefSeq transcripts, including scoring-ineligible transcripts",
              "splice_definition": "two intronic bp at each intron end; union per feature class",
              "per_core": per_core, "modes": {}}
    for mode, positions in total.items():
        result["modes"][mode] = {"added_mask_bp": len(positions), "features": feature_risk(positions, features)}
    write_json(out / "mask_gene_risk.json", result)


def describe(chain, cores, metadata=None):
    owner, _ = ref.ownership(chain, cores)
    row = {"seqid": "chr13", "strand": chain.strand,
           "cds_intervals": [list(x) for x in chain.intervals],
           "owner_block_index": owner.index if owner else None}
    if metadata is not None:
        row.update({key: sorted(metadata[chain][key]) for key in ("gene_ids", "transcript_ids")})
    return row


def paired_metrics(truth, predictions, cores, metadata):
    mode_results, correct, all_pred = {}, {}, {}
    truth_union = set().union(*truth.values())
    for mode in MODES:
        per_core, totals = {}, Counter(tp=0, fp=0, fn=0)
        correct[mode], all_pred[mode] = set(), set()
        for core in cores:
            t, p = truth[core.index], predictions[mode][core.index]
            tp, fp, fn = len(t & p), len(p - t), len(t - p)
            per_core[str(core.index)] = ref.metrics(tp, fp, fn)
            totals.update(tp=tp, fp=fp, fn=fn)
            correct[mode].update(t & p)
            all_pred[mode].update(p)
        mode_results[mode] = {"metrics": ref.metrics(**totals), "per_core": per_core}
    paired = {}
    for mode in ("MW", "MP"):
        gained, lost = correct[mode]-correct["M0"], correct["M0"]-correct[mode]
        unmatched = (all_pred[mode]-truth_union) - (all_pred["M0"]-truth_union)
        delta = mode_results[mode]["metrics"]["micro_f1"]-mode_results["M0"]["metrics"]["micro_f1"]
        paired[mode] = {"micro_f1_delta_vs_m0": delta, "gained_correct_chains": len(gained),
                        "lost_correct_chains": len(lost), "m0_correct_chains": len(correct["M0"]),
                        "gained": [describe(c, cores, metadata) for c in sorted(gained)],
                        "lost": [describe(c, cores, metadata) for c in sorted(lost)],
                        "new_unmatched_predictions": len(unmatched),
                        "new_unmatched": [describe(c, cores) for c in sorted(unmatched)],
                        "exploratory_gate_pass": delta > 0 and len(gained) >= 1 and len(lost) == 0}
    return mode_results, paired


def read_cell(out, core, mode, cores):
    folder = out / f"core{core.index}"
    p, report = ep.read_cds(folder / f"{mode}.gtf", cores)
    q, other = ep.read_cds(folder / f"{mode}.gff3", cores, "gff3")
    signatures = report.pop("all_cds_signatures")
    if p != q or signatures != other["all_cds_signatures"]:
        raise ValueError("GTF/GFF3 CDS mismatch")
    observed = json.loads((folder / f"{mode}.observation.json").read_text())
    if observed["calls"] < 1 or not observed["passed"]:
        raise ValueError("missing valid actual model input observation")
    exclusions, boundary_touch = [], 0
    for record, strand, intervals in signatures:
        if record != core.record_id:
            raise ValueError("prediction belongs to another core input")
        chain = ep.Chain(strand, intervals)
        owner, reason = ref.ownership(chain, cores)
        if reason is None and owner.index != core.index:
            reason = "nonowner_halo_copy"
        if reason:
            exclusions.append({**describe(chain, cores), "reason": reason, "record_id": record})
        boundary_touch += intervals[0][0] == core.halo_start or intervals[-1][1] == core.halo_end
    report.update(excluded_records=exclusions, halo_edge_touching_records=boundary_touch,
                  observation=observed,
                  coding_sequence_audit=ep.audit_coding_sequences(signatures, folder / f"{mode}.fasta", cores))
    return p[core.index], report


def score(cfg, cores, out):
    truth, metadata, reference = ref.read_reference(Path(cfg["refseq"]), cores)
    if sum(map(len, truth.values())) != 243 or reference["counts"]["eligible_transcript_rows"] != 330:
        raise ValueError("reference denominator changed")
    predictions, audits = {m: {} for m in MODES}, {m: {} for m in MODES}
    for core in cores:
        for mode in MODES:
            predictions[mode][core.index], audits[mode][str(core.index)] = read_cell(out, core, mode, cores)
    modes, paired = paired_metrics(truth, predictions, cores, metadata)
    decision = ("MW_SUPPORTS_WHOLE_GAP_UTILITY" if paired["MW"]["exploratory_gate_pass"] else
                "MP_ONLY_MATERIAL_UTILITY" if paired["MP"]["exploratory_gate_pass"] else
                "NO_MASK_ARM_PASSES_EXPLORATORY_UTILITY_GATE")
    result = {"experiment_id": cfg["experiment_id"], "status": "COMPLETED", "decision": decision,
              "primary_metric_name": "MW_minus_M0_micro_complete_CDS_chain_F1",
              "primary_metric": paired["MW"]["micro_f1_delta_vs_m0"],
              "scientific_scoring_enabled": True, "claim_eligible": False,
              "scope": "fixed chr13 DEV exploratory intervention; no independent confirmation",
              "core_count": len(cores), "completed_cells": len(cores)*len(MODES),
              "reference_distinct_chains": 243, "reference_source_rows": 330,
              "gate": cfg["gate"], "modes": modes, "paired_vs_m0": paired, "prediction_audits": audits,
              "mask_gene_risk": json.loads((out / "mask_gene_risk.json").read_text()),
              "boundary_note": "contract exclusions and halo touching are reported, not proven biological completeness; phase progression not audited",
              "model_postprocessing": "unchanged native Tiberius minimum CDS length 200 and in-frame stop removal; no evaluator filtering"}
    write_json(out / "result.json", result)
    write_json(Path("reports") / f"{cfg['experiment_id']}.json", result)
    print(json.dumps({"decision": decision, "modes": modes, "gate": {m: paired[m]["exploratory_gate_pass"] for m in paired}}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "preflight", "score"])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg, cores = config(args.config)
    out = Path(cfg["output_dir"])
    if args.action == "prepare":
        ep.prepare(cfg, out)
        write_json(out / "config.json", cfg)
    elif args.action == "preflight":
        ep.preflight(cfg, out)
        risk_audit(cfg, cores, out)
    else:
        score(cfg, cores, out)


if __name__ == "__main__":
    main()
