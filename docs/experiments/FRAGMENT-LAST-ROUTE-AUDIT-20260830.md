# Fragment last-route audit and C5 closure

Date: 2026-08-30

## Decision

The completed evidence does not authorize another pure direct-annotation run
that only changes the post-training loss, segmentation head, decoder, threshold
or smoothing rule. Those variants continue to use the same local sequence and
RepeatMasker-style run labels, and therefore do not add the instance-level
information that the fragment error requires.

The final scientific route was **C5 hybrid discovery/refinement**:

1. use the frozen post-trained P3 model and HiTE only as candidate generators;
2. search the target genome for independent homologous copies;
3. infer boundaries from internal copy homology versus divergent flanks;
4. build seed-derived consensuses and recover short fragments only after the
   boundary mechanism has passed.

This is a hybrid method, not pure direct annotation. It remains potentially
publishable because it tests whether the missing information is target-genome
multi-copy structure rather than another local decision rule.

The deterministic copy-search pilot has now completed for P3, HiTE and their
union. All three failed to establish a usable multi-copy substrate and changed
the structural endpoints by only about 1e-4. ChatGPT Pro reviewed the final
result and agreed that C5 must stop at A1. The frozen result and its claim
boundary are recorded in
[`C5-HYBRID-CLOSURE-20260831.md`](C5-HYBRID-CLOSURE-20260831.md).

## Why post-training alone is now closed

The relevant frozen observations are:

- generic Human MLM-DAPT passed only 4/6 Human fragment gates;
- TE-enriched span-MLM followed by the same CE task passed only 2/6;
- P3-R2 aligned boundary supervision passed 4/6 route gates and failed both
  decisive structure gates;
- the matched spatial-permutation control beat the aligned target in segment
  F1, boundary F1 and fragments/truth;
- Mouse retained high bp recall but had segment F1 0.096592, boundary F1@5
  0.026062 and 2.144423 fragments/truth;
- exact FlyBase positive truth had segment recall 0.078037, boundary recall@5
  0.013475 and 51.557723 fragments/truth;
- long Human truth is detected but reconstructed poorly: for >=1000-bp runs,
  fragments/truth remains 2.3155--2.7271 while boundary F1@5 is only
  0.0294--0.0391.

Together these results show that local TE signal is present, but intact
instance assignment and precise endpoints are not recovered. A new loss can
reweight the same evidence; it cannot create cross-copy evidence.

## Complete route disposition

| Candidate | New information source | Current disposition | What would reopen it |
|---|---|---|---|
| Generic MLM-DAPT | none beyond Human sequence distribution | Closed | nothing in the current route |
| TE-aware span-MLM | TE-enriched local sequence distribution | Closed as fragment solution | independent full-copy data plus an instance-level downstream gain |
| SegmentNT-style U-Net | multiscale local features; same noisy boundaries | Closed on current labels | curated full-length copy boundaries with family-disjoint evaluation |
| Boundary/distance/continuity loss | same coordinate labels, differently weighted | Closed | independent boundary truth |
| CRF/HMM/semi-Markov decoder | hand-written local transition prior | Closed | a validated class-specific TE grammar, not a generic start/body/end copy of Tiberius |
| Threshold, gap merge, minimum length, smoothing | no new biological evidence | Closed by completed experiments | none |
| Longer context/cross-window stitching | more local context | Low priority/closed now | a new model first demonstrates a material edge-specific error; current effect is about 0.009 F1 |
| Full-length supervised post-training | independent intact-copy boundaries | Scientifically valid but asset-blocked | audited full-copy truth, family identity and homology provenance |
| Same-family/copy contrastive post-training | copy/family relationships | Conditional C5 ablation | family-disjoint identities and deterministic C5 information gain |
| Retrieval/copy-conditioned neural decoder | homologous target-genome copies | Conditional C5 ablation | A1/A2 first beat A0 deterministically |
| Synthetic intact-copy augmentation | synthetic boundary ground truth | Diagnostic only | real held-out curated copies also improve |
| Teacher labels/curriculum/distillation | no independent truth under current assets | Rejected | an independently validated teacher signal |
| Dfam/Repbase profile-HMM recovery | known-family library information | Allowed comparator only | must be reported as library-assisted, never de novo |
| C5 target-genome copy search/MSA/flank refinement | independent target-genome multi-copy evidence | **Closed at A1 under the frozen contract** | new independent assets would define a different study |

If full-length Human/Mouse annotations are later assembled, their quality alone
is not sufficient. The experiment must record family/copy identity, exclude
test families or homologous copies from training, and show that aligned
full-copy labels beat a matched-label control. Otherwise it would repeat the
P3-R2 ambiguity.

## Staged C5 experiment matrix

The full frozen C5-H gate remains in
[`P3-R2-CLOSURE-20260830.md`](P3-R2-CLOSURE-20260830.md). The first run below is
an engineering/mechanism preflight, not the complete gate.

| ID | Hypothesis | Only changed variable | Data/split | Tool | Decision metric | Go/no-go | Claim boundary |
|---|---|---|---|---|---|---|---|
| C5-E0 | Frozen P3 scores can define reproducible long seeds | export segment mean TE probability | chr11 selects rule; chr17 evaluates; full hs1 is search universe | frozen P3-R1 | seed count and A0 strict Human metrics | selection uses chr11 only | engineering baseline only |
| C5-E1 | Independent homologous copies add information beyond seeds | add target-genome copy search | source seeds from chr17 prefix; hits may come from full hs1; evaluate only chr17 prefix | minimap2 `asm20` | A1 vs A0 segment/boundary/fragment metrics; copies per seed | continue P3 seed source only if eligible non-self copies produce measurable retained-recall gain | homology expansion, not boundary refinement |
| C5-H1 | Copy MSA and flank divergence improve boundaries | add MSA/flank breakpoint inference | same frozen Human denominator | MAFFT plus deterministic breakpoint code | A2 vs A1 segment F1 or boundary F1@5 >=+0.02 | fail closes this boundary mechanism | hybrid boundary refinement |
| C5-H2 | Seed-derived consensus recovers fragments without re-fragmenting calls | add consensus recovery | same denominator; no Dfam/Repbase | seed/copy consensus search | recall improves over A2; fragments no more than 10% worse | fail removes recovery stage | seed-derived recovery only |
| C5-H3 | Result is not an artifact of one seed source | repeat A0--A3 for HiTE and union | same denominator | pinned HiTE plus C5 | full frozen six-metric C5-H gate | all three seed sources fail: stop modeling | comparative hybrid result |
| C5-F | Human-positive mechanism transfers | exact FlyBase r6.68 positive truth; no tuning | FlyBase evaluation only | frozen winning C5-H route | recall/boundary/fragmentation only; no precision/F1 | allowed only after C5-H GO | positive-truth transfer diagnostic |

### Frozen C5-E0 seed selection

- Backbone/checkpoint, 8192-bp geometry and inference threshold remain frozen.
- Candidate rules are `min_length` in `{500, 1000}` crossed with segment mean
  TE probability in `{0.8, 0.9}`.
- Select on chr11 validation by segment precision@IoU 0.8, requiring at least
  100 seeds. Ties use higher segment recall, then higher probability threshold,
  then longer minimum length.
- chr17 truth is never consulted during seed selection.

### Frozen C5-E1 copy-search contract

- Search the full exact hs1 target genome; restrict reported output and
  evaluation to chr17:0-9,830,400.
- Use minimap2 `asm20` and retain hits with query coverage >=0.8, sequence
  identity >=0.8 and target span >=500 bp.
- Exclude a source self-hit when source and target are on the same chromosome
  with reciprocal overlap >=0.9.
- A1 is the union of A0 seeds and eligible non-self hit intervals within the
  frozen chr17 evaluation prefix.
- Report the fraction of seeds with at least two independent homologous copies.

These thresholds are deliberately fixed before chr17 evaluation. This pilot
answers whether the current P3 seed source exposes copy evidence; it does not
close all of C5 if P3 fails. HiTE and union remain required positive-control
seed sources before the whole hybrid route can be stopped.

## Full C5-H scientific gate

Relative to the seed-only A0 arm, A2/A3 must achieve all of:

- segment F1@0.8: at least +0.05 absolute;
- boundary F1@5: at least +0.03 absolute;
- fragments/truth: at least 20% relative reduction;
- short rate: at least 20% relative reduction;
- bp recall: at least 95% of A0;
- missed-rate increase: no more than 0.03 absolute.

The boundary mechanism additionally requires A2 to beat A1 by at least 0.02
in segment F1 or boundary F1@5. Consensus recovery must improve bp or segment
recall over A2 while worsening fragments/truth by no more than 10%.

## Publication stop rule: reached

P3, HiTE and union all failed to establish the A1 substrate required for the
frozen C5-H gate. The project therefore stops adding post-training objectives,
neural decoders and post-processing modules. The paper is framed as a
controlled negative benchmark and mechanism study:
local genome-language-model signal transfers at base level, but noisy run-edge
supervision and local decoding do not reconstruct intact TE instances. Under
the frozen seed ontology and matched minimap2 A1 contract, target-genome copy
retrieval was too sparse to justify MSA/flank refinement. This is not a claim
that all multi-copy methods fail.
