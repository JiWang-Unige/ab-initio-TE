#!/usr/bin/env python3
"""Report completed native RNA evidence; never rescore or select candidates."""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    args = ap.parse_args()
    result = json.loads((args.run / 'result.json').read_text())
    rows = json.loads((args.run / 'evidence_by_candidate.json').read_text())['candidates']
    arms = ('U_soft', 'D', 'R_TE')
    endpoints = ('all_introns_strict', 'stringtie_exact_intron_chain')
    chromosomes = sorted({r['evidence_seqname'] for r in rows})
    # This resampling was added after seeing the native counts. It quantifies
    # region sensitivity, not biological replication or a preregistered test.
    cells = np.zeros((len(chromosomes), len(arms), 3), dtype=int)
    for row in rows:
        if row['intron_count'] == 0:
            continue
        ci = chromosomes.index(row['evidence_seqname'])
        for ai, arm in enumerate(arms):
            if arm in row['arms']:
                cells[ci, ai] += (1, int(row[endpoints[0]]), int(row[endpoints[1]]))
    totals = cells.sum(axis=0)
    # A mismatch indicates candidate loss/duplication in this reporting step.
    for ai, arm in enumerate(arms):
        expected = result['raw_rna_support']['by_arm'][arm]
        assert list(totals[ai]) == [expected['multi_exon_count'], expected['all_introns_strict_count'],
                                  expected['stringtie_exact_intron_chain_count']]
    draws = np.random.default_rng(42).integers(0, len(chromosomes), (10000, len(chromosomes)))
    boot = cells[draws].sum(axis=1)
    comparisons = {}
    for other in ('U_soft', 'R_TE'):
        a, b = arms.index('D'), arms.index(other)
        comp = {}
        for ei, endpoint in enumerate(endpoints, 1):
            difference = boot[:, a, ei] / boot[:, a, 0] - boot[:, b, ei] / boot[:, b, 0]
            count_difference = boot[:, a, ei] - boot[:, b, ei]
            comp[endpoint] = {
                'rate_difference': float(totals[a, ei] / totals[a, 0] - totals[b, ei] / totals[b, 0]),
                'rate_difference_ci95': np.quantile(difference, [.025, .975]).tolist(),
                'count_difference': int(totals[a, ei] - totals[b, ei]),
                'count_difference_ci95': np.quantile(count_difference, [.025, .975]).tolist(),
            }
        comparisons['D_minus_' + other] = comp
    diagnostic = {'status': 'COMPLETED', 'analysis': 'posthoc_chromosome_cluster_bootstrap',
                  'chromosomes': chromosomes, 'replicates': 10000, 'seed': 42,
                  'scope': '104 Mb prediction input, including halos; single RNA run',
                  'not_biological_replication': True, 'comparisons': comparisons}
    (args.run / 'region_sensitivity.json').write_text(json.dumps(diagnostic, indent=2) + '\n')
    lines = [
        '# Independent RNA evidence for platypus gene predictions', '',
        'Native Slurm job **12858354 completed** in 34m34s (exit 0). The fixed study/run '
        '**SRR23268362** contributes 27,485,388 paired templates; HISAT2 reports '
        '**91.84% overall alignment** to the complete GCF_004115215.2 assembly. '
        'This produced 194,293 distinct junctions and 31,233 de novo StringTie transcripts.', '',
        'The blind union contains **1,083 predicted exon chains**, selected from D, U_soft '
        'and R_TE without reading gene-reference correctness or RNA support. All predictions '
        'from twenty 5.2-Mb inference inputs are included: **104 Mb including halos**, '
        'whereas the historical reference-scored gene panel is **100 Mb**. These denominators '
        'must not be conflated. The raw-RNA primary analysis includes 975 multi-exon '
        'candidates; the other 108 single-exon candidates have no intron-support endpoint.', '',
        '| Arm | All predicted chains | Multi-exon | All introns supported | Exact StringTie intron chain |',
        '|---|---:|---:|---:|---:|',
    ]
    for arm in arms:
        x = result['raw_rna_support']['by_arm'][arm]
        lines.append(f"| {arm} | {x['candidate_count']} | {x['multi_exon_count']} | "
                     f"{x['all_introns_strict_count']} ({x['all_introns_strict_rate']:.2%}) | "
                     f"{x['stringtie_exact_intron_chain_count']} ({x['stringtie_exact_intron_chain_rate']:.2%}) |")
    lines += ['', 'Strict support requires **each intron** to have at least three NH=1 primary '
              'templates, each with at least 8 aligned bases on both sides. Mates are counted '
              'once. Alignment/junction evaluation is strand-agnostic. StringTie used no '
              'reference GTF and is a second analysis of the **same RNA run**, not a separate assay.', '',
              '![RNA evidence](rna_support.png)', '', '## Post-hoc region sensitivity', '',
              'Paired resampling of the ten chromosomes (10,000 draws, seed 42) was added '
              'after seeing native counts. It measures regional sensitivity, not independent '
              'biological replication or a prespecified confirmatory test.', '',
              '| Comparison | Endpoint | Rate difference (percentage points) | 95% interval |',
              '|---|---|---:|---:|']
    for comparison, endpoints_result in comparisons.items():
        for endpoint, x in endpoints_result.items():
            lo, hi = x['rate_difference_ci95']
            lines.append(f"| {comparison} | {endpoint} | {100*x['rate_difference']:+.2f} | [{100*lo:+.2f}, {100*hi:+.2f}] |")
    lines += ['', '## RNA support of reference-relative gains and losses', '',
              'The annotation was joined **after** blind RNA scoring. The following two '
              'comparisons have complete candidate coverage; historical comparisons against '
              'U_nosm, R_all or P3 are not claimed because those arms were not all in the blind union.', '',
              '| Comparison | Reference-relative set | Loci | All introns supported | Exact StringTie intron chain |',
              '|---|---|---:|---:|---:|']
    sets = result['posthoc_reference_join']['comparison_sets']
    for comparison in ('D_minus_U_soft', 'D_minus_R_TE'):
        for label in ('gained_loci', 'lost_loci'):
            x = sets[comparison][label]
            assert x['matched_unit_count'] == x['historical_unit_count'] == x['matched_candidate_count']
            lines.append(f"| {comparison} | {label} | {x['historical_unit_count']} | "
                         f"{x['all_introns_strict_count']} | {x['stringtie_exact_intron_chain_count']} |")
    lines += ['', '## Interpretation', '',
              'D has more RNA-supported predicted chains than U_soft, and independent raw '
              'reads support **22 of the 49 reference-relative gains**. They also support '
              '**8 of the 18 losses**. This corroborates a useful gene-annotation effect '
              'with real tradeoffs; it does not validate every gained gene or establish '
              'superiority to RepeatMasker. D and R_TE have similar aggregate support.', '',
              'This single adult-male fibroblast run cannot assess all tissues. No RNA '
              'support is not a false-gene label. Exact full exon-chain agreement is zero '
              'for all arms; predicted coding boundaries and RNA UTR endpoints differ, so '
              'the declared intron-chain endpoint is the relevant comparison. Junction '
              'support alone does not establish correct coding start/stop, gene function, '
              'or transcript strand. The study/run is later than the 2021 annotation '
              'inputs; a distinct biological individual is not established.', '',
              'The primary native outputs are `result.json` and `evidence_by_candidate.tsv/json`. '
              'Raw reads and whole-assembly alignments remain on Baobab. The official source '
              'and independence qualification are in the experiment protocol.']
    (args.run / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(diagnostic, indent=2))


if __name__ == '__main__':
    main()
