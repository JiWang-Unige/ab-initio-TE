"""Reference/material readiness only; no sequence, predictions or sealed labels."""
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path.cwd()
CHROMS = ("chr16", "chr18")
OUT = ROOT / "outputs/P3-TIBERIUS-BASE-MASK-READINESS-20260908/run-r1"


def union_bp(intervals):
    end = -1
    total = 0
    for a, b in sorted(intervals):
        assert 0 <= a < b
        total += max(0, b - max(a, end))
        end = max(end, b)
    return total


def main():
    assert union_bp([(1, 4), (2, 5), (5, 7), (9, 10)]) == 7
    data = ROOT / "software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/metadata.json"
    meta = json.loads(data.read_text())
    for split in meta["splits"].values():
        assert not set(CHROMS).intersection(split["chroms"])
    cores = []
    for chrom in CHROMS:
        for i in range(10):
            start = i * 7000000
            cores.append(dict(chrom=chrom, index=i, start=start, end=start + 5000000,
                              halo_start=max(0, start - 100000), halo_end=start + 5100000))
    chains = defaultdict(set)
    symbols = defaultdict(set)
    spans = defaultdict(list)
    excluded = Counter()
    ref = ROOT / "data/raw/ucsc/human/hg38/genes/ncbiRefSeqCurated-20250813.txt.gz"
    with gzip.open(ref, "rt") as handle:
        for line in handle:
            f = line.rstrip().split("\t")
            # Known UCSC 16-column schema: skip other chromosomes before label parsing.
            if f[2] not in CHROMS:
                continue
            assert len(f) == 16
            chrom, strand, symbol = f[2], f[3], f[12]
            assert strand in ("+", "-")
            a, b = int(f[6]), int(f[7])
            if a == b or f[13:15] != ["cmpl", "cmpl"]:
                excluded["noncoding_or_incomplete"] += 1
                continue
            starts = [int(x) for x in f[9].rstrip(",").split(",")]
            ends = [int(x) for x in f[10].rstrip(",").split(",")]
            assert len(starts) == len(ends) == int(f[8])
            cds = tuple((max(s, a), min(e, b)) for s, e in zip(starts, ends)
                        if max(s, a) < min(e, b))
            assert cds
            owner = next((c for c in cores if c["chrom"] == chrom and
                          c["start"] <= cds[0][0] < c["end"]), None)
            if owner is None:
                excluded["outside_core"] += 1
                continue
            if cds[-1][1] > owner["halo_end"]:
                excluded["boundary_incomplete"] += 1
                continue
            key = (chrom, owner["index"])
            chains[key].add((strand, cds))
            symbols[key].add((chrom, strand, symbol))
            spans[(chrom, strand, symbol)].append((int(f[4]), int(f[5])))
    repeat = ROOT / "software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/raw/rmsk.txt.gz"
    mask = defaultdict(list)
    with gzip.open(repeat, "rt") as handle:
        for line in handle:
            f = line.rstrip().split("\t")
            if f[5] not in CHROMS:
                continue
            assert len(f) == 17
            start, end = int(f[6]), int(f[7])
            for c in cores:
                if c["chrom"] == f[5]:
                    a, b = max(start, c["start"]), min(end, c["end"])
                    if a < b:
                        mask[(f[5], c["index"])].append((a, b))
    ambiguous = []
    for key, intervals in spans.items():
        end, components = -1, 0
        for a, b in sorted(intervals):
            if a > end:
                components += 1
            end = max(end, b)
        if components > 1:
            ambiguous.append(dict(symbol_key=key, disjoint_transcript_components=components))
    for c in cores:
        key = (c["chrom"], c["index"])
        c.update(distinct_complete_cds_chains=len(chains[key]),
                 symbol_strand_keys=len(symbols[key]), repeat_union_bp=union_bp(mask[key]))
    result = dict(status="MATERIAL_INVENTORY_COMPLETE_NOT_EXPERIMENT_RELEASE",
                  geometry=cores, distinct_symbol_strand_keys=len(spans),
                  distinct_complete_cds_chains=sum(len(v) for v in chains.values()),
                  disjoint_symbol_keys=ambiguous, exclusions=dict(excluded),
                  reference_source=str(ref), conventional_mask_source=str(repeat),
                  model_predictions_read=False, sealed_labels_parsed=False,
                  full_independence_certified=False)
    assert result["distinct_complete_cds_chains"] > 0
    assert sum(c["repeat_union_bp"] for c in cores) > 0
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
