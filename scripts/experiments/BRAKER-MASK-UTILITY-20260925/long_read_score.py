#!/usr/bin/env python3
"""Freeze and score positive-only splice evidence, never infer RNA negatives."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import evaluation as e


def key(row):
    return (row["chrom"], row["strand"], tuple(tuple(x) for x in row["introns"]))


def freeze(directory):
    """Use prepared source coordinates/classes only; no prediction is opened."""
    source = json.loads((directory / "long-read-structures.json").read_text())
    domains = {}
    for domain, filename in (("primary", "primary_regions.tsv"), ("full", "full_autosome_regions.tsv")):
        regions = e.load_regions(directory / filename)
        allowed = defaultdict(list)
        for region in regions:
            allowed[region.chrom].append((region.start, region.end))
        eligible_ids = defaultdict(list)
        for row in source["structures"]:
            chain = e.Chain(row["strand"], tuple(tuple(x) for x in row["exons"]))
            if e._chain_in_regions(row["chrom"], chain, allowed):
                eligible_ids[key(row)].append(row["transcript_id"])
        selected = []
        for row in sorted(source["deduplicated_structures"], key=key):
            ids = eligible_ids.get(key(row))
            if ids:
                selected.append({"structure_id": "lr-%06d" % (len(selected) + 1),
                    "chrom": row["chrom"], "strand": row["strand"], "introns": row["introns"],
                    "eligible_transcript_ids": sorted(ids), "class_codes": row["class_codes"],
                    "reference_cds_compatible": bool(row["coding_supported_" + domain])})
        domains[domain] = {"structures": selected, "structure_count": len(selected),
            "reference_cds_compatible_count": sum(r["reference_cds_compatible"] for r in selected)}
    result = {"protocol": e.NAME, "status": "LONG_READ_DENOMINATORS_FIXED", "predictions_read": False,
        "source": str(directory / "long-read-structures.json"),
        "eligibility": "at least one source multi-exon transcript has its full exon span inside one fixed allowed region; unique chrom/strand/intron chains",
        "endpoint": "exact equality between predicted CDS intron chain and observed long-read intron chain; no CDS endpoint or RNA-negative truth",
        "domains": domains}
    out = directory / "long-read-denominators.json"
    if out.exists():
        raise FileExistsError(out)
    e.dump(out, result)
    print(json.dumps({"status": result["status"], "domains": {d: {k: v for k, v in x.items() if k != "structures"} for d, x in domains.items()}}))
    return result


def score(prediction_results, frozen, domain):
    """Positive-set recovery; absence of a match is never called an FP."""
    if frozen["status"] != "LONG_READ_DENOMINATORS_FIXED":
        raise ValueError("long-read eligibility not frozen")
    rows = frozen["domains"][domain]["structures"]
    groups = {"all_observed_structures": rows,
              "reference_cds_compatible": [r for r in rows if r["reference_cds_compatible"]]}
    for code in sorted({c for r in rows for c in r["class_codes"]}):
        groups["source_class_" + code] = [r for r in rows if code in r["class_codes"]]
    scored = {}
    for arm, result in prediction_results.items():
        predicted = set()
        for chain in result["predicted_chains"]:
            introns = e.chain_introns(chain["intervals"])
            if introns:
                predicted.add((chain["chrom"], chain["strand"], introns))
        metrics = {}
        for name, targets in groups.items():
            hits = [r["structure_id"] for r in targets if key(r) in predicted]
            by_chrom = {}
            for chrom in sorted({r["chrom"] for r in targets}):
                subset = [r for r in targets if r["chrom"] == chrom]
                by_chrom[chrom] = {"observed": len(subset), "recovered": sum(key(r) in predicted for r in subset)}
            metrics[name] = {"observed": len(targets), "recovered": len(hits),
                             "recovery_fraction": len(hits) / len(targets) if targets else None,
                             "recovered_structure_ids": hits, "per_chromosome": by_chrom}
        scored[arm] = metrics
    comparisons = {}
    if "D" in scored:
        for comparator in ("RM2_FULL", "RED_FULL"):
            if comparator not in scored:
                continue
            comparisons["D_minus_" + comparator] = {}
            for group in groups:
                d, r = scored["D"][group], scored[comparator][group]
                ds, rs = set(d["recovered_structure_ids"]), set(r["recovered_structure_ids"])
                comparisons["D_minus_" + comparator][group] = {
                    "recovery_fraction_delta": (d["recovery_fraction"] - r["recovery_fraction"]) if d["observed"] else None,
                    "gained_structure_ids": sorted(ds - rs), "lost_structure_ids": sorted(rs - ds)}
    return {"domains_source": frozen["source"], "domain": domain, "arms": scored, "comparisons": comparisons,
            "interpretation": "positive-only structural recovery; no precision/FP derived from unobserved RNA; source class u may include noncoding transcripts",
            "boundary": "BRAKER UTR-off CDS intron chains are compared to observed transcript intron chains; UTR introns can prevent equality. RefSeq-CDS-compatible subset is explicitly reference-assisted, not independent CDS endpoint truth."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("evaluation_dir", type=Path)
    freeze(p.parse_args().evaluation_dir.resolve())
