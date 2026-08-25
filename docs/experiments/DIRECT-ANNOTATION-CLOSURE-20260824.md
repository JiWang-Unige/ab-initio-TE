# Direct annotation closure and next-study decision, 2026-08-24

## Scope

This report closes the current direct-annotation iteration with matched model
training, a frozen external positive-truth benchmark, an external de novo caller,
and an identity audit for the proposed contrastive branch.  It distinguishes
completed evidence from blocked or still-running work; cancelled engineering
attempts never enter scientific denominators.

## Decision summary

- **DAPT direct annotation:** scientifically promising but the pre-registered
  closure gate fails (4/6 conditions pass).  Segment and boundary F1 improve,
  while the short-prediction and fragments/truth reductions are too small.
- **Edge-position consistency (C2):** closed as a primary explanation.  The
  observed edge penalty is about 0.9 F1 points and is too small to explain the
  boundary/fragmentation deficit.
- **Contrastive learning:** provenance enrichment is complete, but training is
  blocked until copy, superfamily, and homology-component identities are
  authoritative.  Coordinates or family strings will not be used as invented
  identities.
- **External de novo comparator:** HiTE 3.3.3 has a valid FlyBase T1 positive-only
  result.  Whole-genome precision/F1 remains non-claimable because the frozen
  truth is not exhaustive negative truth.
- **Base-CE/DAPT-CE FlyBase comparison:** complete.  DAPT raises positive-truth
  bp recall but produces dense local fragments rather than correct TE segments;
  HiTE is decisively stronger on the claimable T1 metrics.

## 1. Matched direct-annotation experiment

### Fixed design

- DAPT source: the first 3,000 exact 8,192-nt human chromosome 1 windows from
  the existing training JSONL; labels are ignored.
- Objective: full masked-language modelling, 15% dynamic masking with 80/10/10
  mask/random/unchanged replacement.
- DAPT optimization: 800 steps, batch 1, gradient accumulation 16, learning
  rate `1e-5`, weight decay `0.01`, 10% warm-up, BF16 and gradient
  checkpointing.
- Matched token classification: Base and DAPT start points use the same
  `auto_token` head, data, seed 42, 800 steps, batch 1, accumulation 16,
  learning rate `2e-5`, and TE class weight 3.0.
- Evaluation: the same first 1,200 held-out windows, threshold 0.5, 8,192-bp
  non-overlapping geometry, IoU 0.8 and boundary tolerance 5 bp.

The loading audit for both branches permits only the expected head transition:
`lm_head.weight` is unexpected and `score.weight` is missing; there are no
backbone shape mismatches.

### Pre-registered decision rule

DAPT is accepted only if all six conditions hold against the matched Base-CE
branch:

1. segment F1 at IoU 0.8 improves by at least 0.02;
2. boundary F1 at 5 bp improves by at least 0.02;
3. short-prediction rate falls by at least 20% relatively;
4. mean predicted fragments per truth falls by at least 15% relatively;
5. bp F1 drops by no more than 0.01;
6. missed-truth rate rises by no more than 0.03.

| Metric | Matched Base-CE | DAPT-CE | Change | Gate |
|---|---:|---:|---:|---|
| Segment F1, IoU 0.8 | 0.339956 | 0.380724 | +0.040768 | pass |
| Boundary F1, 5 bp | 0.199781 | 0.224286 | +0.024505 | pass |
| Short-prediction rate | 0.622414 | 0.547001 | -12.12% relative | fail; needs -20% |
| Mean fragments / truth | 1.388409 | 1.263032 | -9.03% relative | fail; needs -15% |
| bp F1 | 0.933773 | 0.934173 | +0.000400 | pass |
| Missed-truth rate | 0.057532 | 0.060198 | +0.002666 | pass |

Short-prediction rate is `short_pred_segments / pred_segments`, not a count:
Base is 18,383/29,535 and DAPT is 13,407/24,510.  The six-condition gate is
therefore a formal **NO-GO for claiming that this exact DAPT recipe solves the
fragment problem**, despite real segment/boundary improvements.

Scientific jobs:

- DAPT profile: Slurm `12066157`, completed.
- matched Base-CE/DAPT-CE array: Slurm `12066158`, both tasks completed with
  exit code 0 (Base 04:01:23; DAPT 03:59:15).

The initial one-step DAPT attempt `12066035` failed before optimization because
the masked-LM model does not accept tokenizer `token_type_ids`.  The minimal
field filter was tested; replacement smoke `12066112` completed.  The failed
engineering attempt is not a scientific result.

## 2. Fragmentation mechanism screen

The exact current Base-CE model was evaluated on 1,200 windows by relative
position (Slurm `12066036`):

| Bin | bp F1 |
|---|---:|
| Left 10% | 0.927068 |
| Inner left | 0.938828 |
| Center | 0.935399 |
| Inner right | 0.935087 |
| Right 10% | 0.925676 |

Edge mean minus center is `-0.009027`.  This mild effect cannot account for the
existing Base-CE strict result (segment F1 0.329669, boundary F1 0.195520,
mean fragments/truth 1.418789, missed-truth rate 0.059566).  Therefore a paired
edge-to-centre consistency loss is not prioritized in this iteration.

## 3. Contrastive branch

The identity screen (Slurm `12066037`) correctly returned the expected typed
blocker on 73,676 rows: every row lacks `id`, `superfamily_id`, `copy_id`, and
`homology_component_id`; 442 exact duplicate canonical sequences also exist.
No clustering or contrastive metric was fabricated.

An exact provenance enrichment was then run as Slurm `12073047`:

- 73,676/73,676 records uniquely joined across 13 species;
- join key: `(species, chrom, start, end, class, family)`;
- restored fields: RepeatMasker name, strand, raw BED row/columns, source row
  hash, and source-file hash;
- generated identity fields: none.

This resolves row-level source provenance, not biological identity.  The next
minimum asset is a fully frozen 13-species RepeatMasker output/library manifest,
an exact Dfam accession crosswalk that preserves unresolved/ambiguous records,
and fixed homology components.  Until that passes an identity and leakage gate,
same-superfamily contrastive training remains blocked.

## 4. Frozen FlyBase external benchmark

### Benchmark contract

- FlyBase FB2026_02, *D. melanogaster* r6.68.
- Assembly SHA256:
  `81751d3b66bc504525ab88342aa91817eee80bfff136c893e9cda76ea05643b1`.
- Truth SHA256:
  `d47d94aa56b4c65ce8199838c3c71a37a58bc54590ce277f1ffdf14b10413bd2`.
- 1,870 contigs and 143,726,002 genomic bp.
- 5,734 raw curated-positive intervals; flat-union evaluation yields 4,972
  dense-mask truth runs.
- T1 positive-only scope: recall, boundary and fragmentation are claimable;
  whole-genome precision/F1, FP and TN are not.

### HiTE 3.3.3

The valid animal-mode run is Slurm `12066193`; the earlier plant-default run
was cancelled and excluded.

| Claimable T1 metric | HiTE |
|---|---:|
| bp truth coverage / recall | 0.448982 |
| Segment recall, IoU 0.8 | 0.216412 |
| Boundary recall, 5 bp | 0.119670 |
| Median matched boundary error | 2.5 bp |
| Mean matched IoU | 0.972959 |
| Mean fragments / truth | 1.023733 |
| Split-truth rate | 0.193081 |
| Missed-truth rate | 0.492961 |

### Foundation-model comparison

The inference bridge fixes 8,192-bp windows/stride, threshold 0.5, complete
contig coverage, N-padding with zero attention for padding, and cropping to
real contig length.  The matched Base-CE and DAPT-CE models were evaluated on
this identical FlyBase T1 contract.

| Claimable T1 metric | HiTE | Base-CE | DAPT-CE |
|---|---:|---:|---:|
| bp truth coverage / recall | 0.448982 | 0.003408 | 0.018514 |
| Segment recall, IoU 0.8 | 0.216412 | 0 | 0.000402 |
| Boundary recall, 5 bp | 0.119670 | 0 | 0.000201 |
| Median matched boundary error, bp | 2.5 | not defined; no match | 5.5 |
| Mean matched IoU | 0.972959 | 0 | 0.877056 |
| Mean fragments / truth | 1.023733 | 2.927595 | 11.703138 |
| Split-truth rate | 0.193081 | 0.076830 | 0.465205 |
| Missed-truth rate | 0.492961 | 0.897828 | 0.461585 |
| Short-prediction rate | 0.838667 | 0.999506 | 0.998044 |
| Predicted segments | 110,126 | 159,832 | 388,073 |

The valid FM array is Slurm `12094740`: Base completed in 05:41:53 and
DAPT in 05:42:30.  Both coverage manifests contain 1,870 contigs,
143,726,002 bp and 18,935/18,935 windows, with zero missing or overlap bp.
The first FM wrapper attempt `12094732` failed during environment loading and
is excluded; it produced no scientific prediction.

DAPT is better than Base on bp recall (about 5.43-fold) and missed-truth rate,
but this is not successful direct annotation.  It finds only 2/4,972 truth
segments at IoU 0.8 and one at the 5-bp boundary criterion while generating
11.70 fragments per truth.  The result is consistent with dense local signal,
not intact-element recovery.  HiTE is much stronger on segment, boundary and
bp recall while remaining close to one fragment per truth.

## 5. Direction after the closure gate

The next experiment is selected from evidence, not run as an unranked sweep:

1. Record this exact DAPT recipe as a mixed but gate-negative result: it
   improves segment/boundary F1, yet does not reduce fragmentation enough.
   Do not claim that all continued pretraining is impossible, but do not scale
   this recipe blindly.
2. Do not prioritize MoE without evidence of separable, stable routing groups;
   the current failure is continuity/boundary quality, not demonstrated expert
   interference.
3. Do not train the contrastive branch until authoritative biological identity
   fields and homology-safe splits are available.
4. Treat FlyBase T1 comparisons as recall/boundary/fragmentation evidence only.
   A separate exhaustive T0 truth is required before whole-genome precision or
   F1 claims.
5. If direct DAPT fails, the next engineering fallback is a long, high-confidence
   model seed followed by sequence-homology expansion and/or caller-conditioned
   refinement.  That is a hybrid discovery/refinement claim, not unrestricted
   ab initio direct annotation.

### Minimal next experiment, in order

1. Run one controlled, species-balanced DAPT ablation before abandoning
   continued pretraining: keep 3,000 windows, 800 steps and every CE setting
   fixed, but sample 250 unlabeled windows from each of 12 non-*Drosophila*
   assemblies (`anoGam3`, `bosTau9`, `canFam6`, `ce11`, `danRer11`, `galGal6`,
   `gasAcu1`, `hg38`, `mm39`, `oryLat2`, `rn7`, `xenTro10`).  Excluding `dm6`
   preserves the FlyBase screen as a species holdout.  Reapply the same six
   human gates and the frozen FlyBase T1 screen.  The availability and hashes
   of all 12 assembly FASTAs have not yet been audited; that is a required CPU
   preflight, not an assumption.
2. Only if balanced DAPT improves zero-shot recall but leaves fragmentation
   high, test span masking as a separate ablation; do not change sampling and
   masking together.
3. In parallel, finish the identity asset for contrastive learning: freeze the
   complete 13-species RepeatMasker output/library provenance, exact Dfam
   accessions, and MMseqs homology components.  Then build positives from
   different copies in the same superfamily and split homology components
   before augmentation.
4. Treat HiTE as the current external de novo comparator.  The next genuinely
   traditional cell is RepeatModeler2 followed by RepeatMasker on the exact
   FlyBase assembly, using only the run-derived library (no Dfam augmentation).
   Freeze its container/version/library hashes before execution.  EDTA is
   secondary because its animal-genome suitability and exact runtime contract
   still require audit; neither method is a result in this R1.
5. In parallel with balanced DAPT, run a no-training long-seed feasibility
   analysis.  Stratify truth and predictions into `<80`, `80-499`, `500-999`
   and `>=1000 bp`; report segment/boundary recall and fragmentation separately
   on the human held-out set and FlyBase T1.  This tests, rather than assumes,
   that intact long elements are the model's easier and useful output.
6. If balanced DAPT fails but the long-seed gate is positive, build the hybrid
   experiment on a held-out chromosome/species: take only FM seeds of at least
   500 or 1,000 bp, cluster with a fixed MMseqs2 configuration, derive a
   seed-only consensus library, and use RepeatMasker homology search to recover
   short copies.  Compare direct FM, seed expansion, HiTE and the frozen
   RepeatModeler2+RepeatMasker cell under the same truth contract.
7. If balanced DAPT and the long-seed gate both fail, stop the unrestricted
   direct-annotation claim.  Caller-conditioned refinement remains a possible
   engineering paper, but it must be described as hybrid refinement rather
   than ab initio discovery.

## 6. Publication consequence

The current evidence is not sufficient for a paper claiming accurate,
cross-species, direct ab initio TE annotation.  The positive result is narrower:
human-only DAPT improves matched human segment and boundary F1, but it misses
the pre-registered fragmentation gates and does not transfer into intact
FlyBase TE segments.  A publishable endpoint now needs one of two outcomes:

- species-balanced DAPT passes both the human closure gates and a held-out
  species screen, establishing a direct-annotation contribution; or
- direct annotation is explicitly closed as negative, while the long-seed plus
  homology-expansion route shows a reproducible improvement over direct FM and
  traditional callers on short-fragment recovery.

Regardless of route, independent seeds/replicates, a second traditional caller
cell, and an exhaustive T0 instance are still needed for uncertainty and
whole-genome precision/F1 claims.  The present FlyBase T1 result alone cannot
provide them.
