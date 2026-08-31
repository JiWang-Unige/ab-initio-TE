# C5 hybrid copy-evidence closure

Date: 2026-08-31

## Decision

C5-H stops at A1. A2 multi-copy alignment/flank refinement, A3 consensus
recovery and C5-F are not authorized. No additional post-training, retrieval
retuning, ranker or decoder run is justified by the frozen evidence.

The result is deliberately narrow:

> Under the frozen seed definitions and matched minimap2 copy-search contract,
> target-genome homologous-copy retrieval was too sparse to provide a usable
> multi-copy substrate for downstream MSA-based TE-instance refinement.

It does not show that Human TEs lack homologous copies, that minimap2 is
generally unsuitable, or that all multi-copy, consensus or structure-aware
methods are ineffective. HiTE and RepeatModeler-like systems use discovery,
clustering and structural stages that are outside the tested A1 contract.

ChatGPT Pro reviewed the final three-source result and agreed with this stop
decision and claim boundary.

## Frozen contract

- Human evaluation: chr17:0-9,830,400, the unchanged comparator-strict truth,
  callable mask, evaluator and 14,253-truth denominator.
- Search universe: full exact hs1 assembly.
- Search: minimap2 `asm20`.
- Retain hits with query coverage >=0.8, identity >=0.8 and target span >=500
  bp.
- Exclude a same-chromosome source self-hit at reciprocal overlap >=0.9.
- A1 is A0 plus eligible non-self target intervals returning to the frozen
  chr17 prefix.
- P3, HiTE and union use the same copy-search and evaluation contract.

## Three-source A0--A1 result

| Seed source | Queries | Qualified non-self hits | Returned to chr17 | Seeds with >=2 copies | Segment F1 A0 -> A1 | Boundary F1@5 A0 -> A1 | Fragments/truth A0 -> A1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| P3 frozen long/high-confidence | 2,259 | 43 | 14 | 6 (0.2656%) | 0.122335 -> 0.122578 | 0.039486 -> 0.039608 | 0.294464 -> 0.294534 |
| HiTE 3.3.3 tool-native `te_intact` | 2,561 | 1 | 1 | 0 | 0.120352 -> 0.120466 | 0.012916 -> 0.012916 | 0.229425 -> 0.229496 |
| Union | 4,820 | 44 | 15 | 6 (0.1245%) | 0.189411 -> 0.189637 | 0.037520 -> 0.037634 | 0.426577 -> 0.426647 |

For the union, 24/4,820 queries had at least one independent copy and only
5/4,820 had at least three. Union bp recall increased from 0.600614 to
0.600913, while missed rate changed from 0.582755 to 0.582614. The structural
endpoints changed by about 1e-4 and fragmentation became slightly worse.

The absence of denominator-scale multi-copy groups is the decisive failure.
This is not an A2 failure: A2 was not run because the evidence needed for an
MSA/flank-boundary test was not established.

## Frozen stop-rule result

The planned C5-H endpoint required, relative to A0, segment F1 +0.05,
boundary F1@5 +0.03, fragments/truth 20% lower, short rate 20% lower, bp recall
retention and a missed-rate guardrail. A1 was also required to establish enough
independent copies to make A2 mechanistically interpretable.

All three sources failed the substrate condition and produced negligible A1
endpoint changes. Continuing by changing minimap thresholds or searchers would
replace the frozen experiment with a new rescue experiment. Therefore:

- A2 and A3 are not run;
- C5-F is not run;
- pure direct P3 remains closed;
- no post-training-plus-post-processing re-entry is authorized;
- independently curated biological full-copy truth remains a future data
  condition, not an experiment available from current assets.

## Job and denominator ledger

| Job | Outcome | Treatment |
|---|---|---|
| `12117786` | Complete P3 A0 payload written; wrapper failed at shared stdout flush with exit 120 | Retained as engineering failure; payload used by the successful recovery, not counted as a successful job |
| `12117787` | Cancelled because `afterok` dependency could not be satisfied | Excluded |
| `12117899` | P3 A1 recovery completed | Included |
| `12117941` | Pinned HiTE 3.3.3 native-artifact recovery completed | Included as engineering artifact recovery |
| `12117971` | HiTE A0/A1 completed | Included |
| `12118011` | Union A0/A1 completed | Included |

HiTE A0 used every tool-native `te_intact` record in
`HiTE.full_length.gff`: 2,561 calls, without truth-, length- or score-based
selection. These are HiTE-designated intact/full-length seeds, not independent
biological truth.

## Evidence classification

- **Scientific route-selection evidence:** the same-denominator A0/A1 endpoint
  deltas and the frozen stop-rule application.
- **Mechanism preflight:** retrieval yield and independent-copy counts under
  the frozen A1 contract.
- **Engineering evidence:** HiTE native artifact persistence, canonical output
  conversion and Slurm recovery behavior.
- **Not established:** biological full-copy truth, universal failure of
  multi-copy methods, novel-family discovery, or a biological comparison of
  P3 versus HiTE.

## Publication closure

The project now stops model and retrieval experimentation and moves to a
controlled negative benchmark/mechanism diagnosis. The central result is that
high base-pair recovery is not sufficient for intact TE-instance annotation:
generic continuation training, TE-conditioned span-MLM, multiscale
segmentation, explicit boundary supervision and the frozen target-genome copy
expansion all failed their prespecified structural gates.

Only no-training paper work remains:

1. a same-denominator Human failure-chain table/figure;
2. Human length-stratified fragmentation and boundary figures;
3. the P3-R2 aligned-versus-matched-control mechanism figure;
4. Mouse and FlyBase external transfer diagnostics, with FlyBase restricted to
   recall/fragmentation measures;
5. the C5 retrieval-yield and A0--A1 delta figure;
6. a preregistered-gate and failed-job denominator ledger.

No standalone checksum inventory is added because no project consumer uses
one. Reproducibility is carried by the committed scripts/configuration, exact
job IDs, tool versions, frozen data contracts and canonical outputs.
