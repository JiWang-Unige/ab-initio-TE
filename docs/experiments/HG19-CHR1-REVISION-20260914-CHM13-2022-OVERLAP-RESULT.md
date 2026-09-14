# Descriptive hg19-to-CHM13 annotation-overlap result

Slurm job `12705941` completed the fixed overlap pass, and Slurm job
`12706180` aggregated its per-interval table. The input contains all 97,242
source intervals: TP 25,775, FP 21,402, FN 24,588, and TN 25,477. The
qualified subset contains 93,116 unique reciprocal same-length mappings:

| state | all source intervals | qualified intervals |
| --- | ---: | ---: |
| TP | 25,775 | 23,962 |
| FP | 21,402 | 21,235 |
| FN | 24,588 | 24,333 |
| TN | 25,477 | 23,586 |

The target is the fixed `CHM13v2.0_RepeatMasker_4.1.2p1.2022Apr14.out`
release. Only target chr2, chr3, and chr4 were read. After interval union,
the annotation rows and union base pairs were:

| category | rows (chr2 + chr3 + chr4) | union bp (chr2 + chr3 + chr4) |
| --- | ---: | ---: |
| TE | 938,061 | 300,555,498 |
| UNKNOWN | 1,831 | 523,302 |
| NONTE | 177,683 | 24,823,941 |
| UNRECOGNIZED | 0 | 0 |

`TE` is the parallel union of the RepeatMasker base classes SINE, LINE,
LTR, DNA, RC, and RETROPOSON. `UNKNOWN` contains base class UNKNOWN or a
class/family field containing `?`. `NONTE` is limited to the known
simple/low/satellite/RNA classes; any other class would remain
`UNRECOGNIZED` rather than being silently treated as a negative class.

The following are descriptive support fractions among qualified intervals.
The full source denominator remains the first table; failed mappings have no
annotation support value and are not counted as unsupported evidence.

| category / layer | TP | FP | FN | TN | all qualified |
| --- | ---: | ---: | ---: | ---: | ---: |
| TE / any | 22,780/23,962 (95.07%) | 4,059/21,235 (19.11%) | 21,133/24,333 (86.85%) | 4,436/23,586 (18.81%) | 52,408/93,116 (56.28%) |
| TE / >=50% | 22,680/23,962 (94.65%) | 3,570/21,235 (16.81%) | 20,398/24,333 (83.83%) | 1,342/23,586 (5.69%) | 47,990/93,116 (51.54%) |
| TE / >=80% | 22,341/23,962 (93.24%) | 3,171/21,235 (14.93%) | 20,003/24,333 (82.21%) | 1,002/23,586 (4.25%) | 46,517/93,116 (49.96%) |
| UNKNOWN / any | 0/23,962 (0.00%) | 0/21,235 (0.00%) | 0/24,333 (0.00%) | 33/23,586 (0.14%) | 33/93,116 (0.04%) |
| UNKNOWN / >=50% | 0/23,962 (0.00%) | 0/21,235 (0.00%) | 0/24,333 (0.00%) | 3/23,586 (0.01%) | 3/93,116 (0.00%) |
| UNKNOWN / >=80% | 0/23,962 (0.00%) | 0/21,235 (0.00%) | 0/24,333 (0.00%) | 0/23,586 (0.00%) | 0/93,116 (0.00%) |
| NONTE / any | 334/23,962 (1.39%) | 666/21,235 (3.14%) | 368/24,333 (1.51%) | 3,151/23,586 (13.36%) | 4,519/93,116 (4.85%) |
| NONTE / >=50% | 30/23,962 (0.13%) | 495/21,235 (2.33%) | 259/24,333 (1.06%) | 588/23,586 (2.49%) | 1,372/93,116 (1.47%) |
| NONTE / >=80% | 25/23,962 (0.10%) | 427/21,235 (2.01%) | 201/24,333 (0.83%) | 395/23,586 (1.67%) | 1,048/93,116 (1.13%) |
| UNRECOGNIZED / any, >=50%, or >=80% | 0 | 0 | 0 | 0 | 0 |

The high TE support in TP and FN is compatible with the observation that
many missed source intervals map into TE annotation in the newer assembly.
The FP-any rate is 19.11%, close to the TN-any rate of 18.81%; the higher FP
than TN rates at the 50% and 80% layers are descriptive only. This run has no
matched-background control, no same-base bijection proof inside equal-span
intervals, and no F1 recomputation. Therefore it does not identify a true FP
rescue or establish that annotation error caused a particular source FP.
The result supports a follow-up hypothesis about annotation/reference
coverage, but the hypothesis requires a separately specified matched control
or independently adjudicated examples.

Compact machine-readable output:

- `reports/HG19-CHR1-REVISION-20260914/chm13-2022-overlap-summary-12706180/summary.json`
- remote full per-interval table:
  `outputs/HG19-CHR1-REVISION-20260914/chm13-2022-overlap-12705941/annotation_overlap.tsv`

The fixed overlap definition and claim boundary are in
`docs/experiments/HG19-CHR1-REVISION-20260914-CHM13-2022-OVERLAP.md`.
