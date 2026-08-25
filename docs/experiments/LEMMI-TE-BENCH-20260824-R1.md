# LEMMI-TE-BENCH-20260824-R1

## Scope

LEMMI is a continuous benchmarking framework for metagenomics classifiers,
not a TE caller or truth source. This experiment adopts its frozen-instance,
provenance and explicit cell-status discipline for a TE benchmark.

The frozen instance is FlyBase FB2026_02 *D. melanogaster* r6.68 with T1
curated-positive truth. Evaluation uses zero-based half-open coordinates,
flat-union masks, IoU 0.8 and a 5-bp boundary tolerance. T1 supports recall,
boundary and fragmentation claims only. Whole-genome precision/F1, FP and TN
remain non-claimable because unlabelled sequence is not an exhaustive negative
set.

## Frozen identity

- Assembly SHA256:
  `81751d3b66bc504525ab88342aa91817eee80bfff136c893e9cda76ea05643b1`
- Truth SHA256:
  `d47d94aa56b4c65ce8199838c3c71a37a58bc54590ce277f1ffdf14b10413bd2`
- 1,870 contigs; 143,726,002 bp.
- 5,734 raw truth intervals; 594 overlapping pairs; 812 intervals participate
  in overlap; dense flat union contains 4,972 truth runs.
- Preflight Slurm `12066076`: `PASS`.

## Completed cells

| Method | Slurm | Status | Output |
|---|---:|---|---|
| HiTE 3.3.3, animal mode | 12066193 | PASS | `outputs/LEMMI-TE-BENCH-20260824-R1/hite-claim-attempt-12066193` |
| matched Base-CE | 12094741 | PASS | `outputs/LEMMI-TE-BENCH-20260824-R1/fm-claim-attempt-12094741-0` |
| matched DAPT-CE | 12094740 | PASS | `outputs/LEMMI-TE-BENCH-20260824-R1/fm-claim-attempt-12094740-1` |

Both FM manifests cover all 1,870 contigs, 143,726,002 bp and 18,935 windows,
with zero missing or overlapping coverage bp. The first FM wrapper attempt
`12094732` failed before inference because it used the wrong Python environment
and is excluded from scientific results.

## T1 positive-only results

| Metric | HiTE | Base-CE | DAPT-CE |
|---|---:|---:|---:|
| bp recall | 0.448982 | 0.003408 | 0.018514 |
| Segment recall, IoU 0.8 | 0.216412 | 0 | 0.000402 |
| Boundary recall, 5 bp | 0.119670 | 0 | 0.000201 |
| Median matched boundary error, bp | 2.5 | undefined | 5.5 |
| Mean matched IoU | 0.972959 | 0 | 0.877056 |
| Mean fragments / truth | 1.023733 | 2.927595 | 11.703138 |
| Split-truth rate | 0.193081 | 0.076830 | 0.465205 |
| Missed-truth rate | 0.492961 | 0.897828 | 0.461585 |
| Short-prediction rate | 0.838667 | 0.999506 | 0.998044 |
| Predicted segments | 110,126 | 159,832 | 388,073 |

DAPT increases bp recall about 5.43-fold over Base and lowers missed truth, but
it recovers only 2/4,972 truth segments at IoU 0.8 and creates 11.70 fragments
per truth. HiTE is substantially stronger on segment, boundary and bp recall
while remaining near one fragment per truth. None of these T1 results supports
a whole-genome precision or F1 claim.

## Implementation

`scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py` converts BED, GFF3
and RepeatMasker `.out` into a canonical zero-based half-open TSV and evaluates
the shared T1 contract. `pipelines/PIPE-TEFM-FINAL-20260623/infer_fasta_to_bed.py`
provides frozen 8,192/8,192 FM inference with complete tail/short-contig
coverage. The HiTE and FM Slurm wrappers record unique attempts and terminal
statuses.

RepeatModeler2+RepeatMasker, EDTA, EarlGrey and TEtrimmer have engineering or
different-species assets only; they are not results in this R1. A second
traditional cell must first freeze its exact FlyBase software/container,
library provenance and output contract.
