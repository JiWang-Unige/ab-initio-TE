# Fragment gap topology audit

Date: 2026-08-31

Status: **complete; descriptive only, no rescue rule selected**

## Decision being tested

The repository has measured fragments per comparator run, but it has not yet
measured the error process that creates those fragments. This audit asks
whether false-negative intervals inside continuous comparator-positive
material look like sparse independent errors, first-order correlated dropout,
or a heavier and context-dependent process.

It does not fill a gap, choose a merge threshold, infer a biological insertion
or alter Gate L. A short gap is not evidence that two material segments belong
to the same extant locus, and a locus relation would not make the intervening
bases TE-positive material.

## Why FlyBase is not rebuilt

Raw FlyBase r6.68 was read once to construct the frozen P3-blind annotation
packets. Slurm `12122769` produced the reusable 348 KB bundle. Annotation must
reuse that bundle rather than parse the 2.4 GB release again.

This gap audit also reuses the already frozen exact-r6.68 prediction and
positive-material truth tracks. It does not read raw FlyBase GFF. All truth
runs overlapping any of the 172 frozen calibration/main/reserve package spans
are removed from the Fly descriptive denominator so that the pre-Gate-L blind
panel is not inspected through P3 output.

The species have different roles:

| Source | Role | Legal interpretation |
|---|---|---|
| Human chr17 | Same-species frozen test; Base/DAPT/P3 share 14,253 comparator truth runs | TE-material gap topology and comparator-run fragmentation; no biological copy identity |
| Mouse chr1 observed panel | Untuned mammalian transfer diagnostic | External material topology only; unobserved chr1 prefix and `-100` positions are not model gaps |
| FlyBase exact r6.68 | Distant positive-only diagnostic and separate provenance source for Gate L | Positive-material recovery only; no whole-genome precision/F1 and no per-FBti split claim from flat-union runs |

Human remains the only rule-development species. The existing Human test,
Mouse and Fly results may be described but cannot select a cutoff. Any later
rule must be frozen on Human chr11 validation before it is evaluated elsewhere.

## Frozen inputs

| Arm | Truth | Prediction | Window source | Null parameter source |
|---|---|---|---|---|
| Human Base | Human chr17 comparator runs | frozen Base-CE canonical track | 1,200 Human test JSONL windows | same-arm in-sample diagnostic |
| Human DAPT | same Human truth | frozen DAPT-CE canonical track | same windows | same-arm in-sample diagnostic |
| Human P3 | same Human truth | frozen P3-R1 canonical track | same windows | same-arm in-sample diagnostic |
| Mouse P3 | observed-panel comparator runs | frozen P3-R1 transfer track | 1,200 Mouse test JSONL windows | Mouse in-sample descriptive diagnostic |
| Fly P3 | flat-union curated-positive runs outside all 172 frozen packages | frozen exact-r6.68 P3 track | existing inference JSONL | Fly in-sample descriptive diagnostic outside the packages |

The in-sample nulls are exploratory goodness-of-fit references. They cannot
authorize a post-processing rule. A predictive Human null would require one
frozen chr11 inference pass; it is deferred until the descriptive audit shows
that such a pass would change the H1 decision.

## Measurements

For each continuous truth-material interval, the audit records:

- length stratum: `<80`, `80-499`, `500-999`, or `>=1000` bp;
- covered and uncovered bp, positive runs, missed and split indicators;
- internal false-negative gaps separately from left/right terminal omission;
- each gap's length, relative position, distance to each truth boundary,
  preceding/following positive-run length and nearest window-seam distance;
- observed interval topology versus an IID Bernoulli null and a two-state
  first-order Markov null, including exact expected split probability.

Each truth run is a separate null-model sequence, so transitions are never
created across two biological/comparator intervals. Interval, package or
chromosome—not individual bp—is the future uncertainty unit.

The committed script emits raw interval/event tables. Tail quantiles and
observed/expected ratios are calculated from those tables in the result
section; no threshold is selected from them.

## Interpretation gates

1. **IID sufficient:** IID approximately explains split rate, gap counts and
   gap-length tail. Sparse bp errors are a plausible fragmentation mechanism,
   but this still does not identify which individual gap is safe to fill.
2. **Markov adds information:** Markov materially improves topology/tail fit.
   Correlated dropout becomes eligible for a later held-out Human chr11
   mechanism test; continual learning remains closed until independent
   material truth distinguishes dropout from annotation disagreement.
3. **Both insufficient:** long-tail, positional or cross-species patterns
   remain unexplained. Do not add another smoother; investigate comparator,
   sequence context and ontology mismatch.
4. **Post-processing:** material gap filling remains closed in every branch.
   A distance-only same-locus baseline may be tested only after Gate L and
   Gate O provide independent same-locus, distinct, nested and unresolved
   labels, with zero new positive bp and explicit fusion/child-absorption
   guardrails.

## ChatGPT Pro convergence

The second independent Pro review agreed on the following order:

`Gate L -> Gate O -> Gate E -> at most one restricted relation model`

The gap audit can run in parallel only as a mechanism diagnosis and an H1
eligibility screen. The current FBTI ontology is already the defensible part
of the gene analogy: observed material, locus identity and typed interruption
are separate layers. Tiberius/Helixer-style gene-specific splice, frame and
codon grammar cannot be copied into a universal TE decoder.

## Execution ledger

Slurm array `12124904` used the frozen inputs above and made no model or
threshold change.

| Task | Arm | State | Scientific denominator |
|---|---|---|---|
| `12124904_0` | Human Base | `COMPLETED` | included |
| `12124904_1` | Human DAPT | `COMPLETED` | included |
| `12124904_2` | Human P3 | `COMPLETED` | included |
| `12124904_3` | Mouse P3 | `COMPLETED` | included as a descriptive transfer diagnostic |
| `12124904_4` | Fly P3 | `FAILED` | excluded |
| `12124968_4` | Fly P3 flat-union recovery | `COMPLETED` | included as positive-only descriptive evidence |

The Fly task failed before producing a calibration track or metrics because
the frozen canonical truth retains overlapping FBti records. The historical
evaluator flat-unions those rows at evaluation time; the first audit version
incorrectly assumed that union had already been materialized. The exact error
was `ValueError: truth intervals overlap: FBti0059713 and FBti0019760`.

The minimal recovery explicitly unions overlapping or touching Fly truth rows
before excluding the 172 frozen-package spans. It does not alter Human or
Mouse inputs, read raw FlyBase, or recover FBti instance identity. The failed
directory and error remain retained, and the recovery uses a new output
directory. Recovery `12124968_4` flat-unioned 4,972 positive-material runs,
excluded 1,123 runs overlapping the 172 frozen packages and evaluated the
remaining 3,849 runs. Its `STATUS` is `PASS`.

The initial array and recovery inherited `public-short-cpu` from the first
script version. That routing diverged from the current `smart-sbatch` CPU-only
fast path, which requires `private-teodoro-gpu` with zero GPUs. This affects
queue/cost routing, not the calculations. The committed script now uses the
required private partition; no scientific task was rerun merely to change
partition provenance.

## Frozen results

The reproducible compact result is
`outputs/FRAGMENT-GAP-TOPOLOGY-20260831-R1/summary-r1/gap_topology_summary.tsv`.
All percentages below use the frozen truth-material denominator. Fly remains
positive-only.

| Arm | bp recall | missed truth | split truth | fragments/truth | internal gaps/kb truth | internal-gap bp/truth bp | gap length p50 / p90 / p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Human Base | 94.288% | 5.753% | 15.912% | 1.388 | 1.296 | 1.155% | 1 / 8 / 108 bp |
| Human DAPT | 94.101% | 6.020% | 11.976% | 1.263 | 0.939 | 1.155% | 2 / 15 / 129.94 bp |
| Human P3 | 94.315% | 5.564% | 13.794% | 1.292 | 1.012 | 1.154% | 2 / 13 / 137.4 bp |
| Mouse P3 | 95.298% | 5.696% | 18.515% | 2.144 | 2.107 | 1.273% | 1 / 8 / 89 bp |
| Fly P3 positive-only | 80.479% | 10.548% | 66.069% | 52.058 | 35.148 | 14.761% | 1 / 5 / 38 bp |

### What P3 changed on Human

P3 has the highest bp recall and lowest missed rate of the three Human arms,
but it is not the best Human fragment-topology arm. Relative to Base, P3 has
21.9% fewer internal gaps and lowers fragments/truth from 1.388 to 1.292.
Generic DAPT has still fewer gaps and lower fragments/truth than P3, despite
slightly worse bp recall.

Under the current definition,
`fragments/truth = 1 - missed_rate + internal_gaps/truth`. A fully missed truth
run contributes zero fragments. DAPT's lower fragments/truth therefore partly
reflects its higher missed rate and cannot be interpreted alone as improved
continuity. Missed rate, internal gap count, gap-bp mass and gap length must be
reported together.

The three Human arms leave essentially the same internal false-negative mass:
1.154-1.155% of truth bp. DAPT and P3 therefore convert that mass into fewer,
longer dropout runs rather than recovering it. This is a change in error
correlation/topology, not evidence that P3 learned biological insertion
identity. P3 remains the best of these arms for material recall, but cannot be
called the uniquely best fragment solution.

### Human P3 gap shape

P3 produced 4,961 internal gaps in 14,253 comparator runs:

- 48.84% are 1 bp, 64.77% are at most 2 bp, 80.91% at most 5 bp,
  88.47% at most 10 bp, 93.99% at most 25 bp and 98.39% at most 100 bp;
- the tail is real: p95 is 33 bp, p99 is 137.4 bp and the maximum is
  16,384 bp;
- preceding positive-run length is 3 / 305 / 499 bp at p50/p90/p95;
- distance between consecutive internal gaps is 2 / 74.6 / 296 bp at
  p50/p90/p95. Many gaps occur in local alternating-error bursts, while a
  minority follows a long correct run;
- the first and last 10% of a truth run contain 20.22% and 18.06% of internal
  gaps. The outer 20% therefore contains 38.28% of events, while the middle
  50% contains 35.11%;
- 1.43% of gaps touch an 8,192-bp window seam exactly and 5.10% lie within
  100 bp. Seam-associated gaps are a minority and cannot explain the other
  94.9%, but callable truth-bp exposure has not been normalized. A rough
  uniform opportunity is `200/8192 = 2.44%`, so the observed 5.10% could still
  be locally enriched. The exact 16,384-bp P3/DAPT maximum is also a suspicious
  `2 x 8192` engineering signature, not proof of a window mechanism.

Short-gap prevalence is a mechanism observation, not a merge permission. The
current test truth can show that a gap lies inside one continuous comparator
run; it cannot show that an arbitrary short gap between two predicted atoms
is safe with respect to adjacent or nested biological loci.

### Length is exposure, not local difficulty

| Human P3 truth length | truth runs | bp recall | missed | split | internal gaps/kb | fragments/truth |
|---|---:|---:|---:|---:|---:|---:|
| `<80` | 1,089 | 69.396% | 25.344% | 10.744% | 3.840 | 0.973 |
| `80-499` | 11,125 | 93.895% | 4.539% | 10.948% | 0.989 | 1.196 |
| `500-999` | 1,405 | 94.714% | 0.854% | 28.043% | 1.185 | 1.797 |
| `>=1000` | 634 | 96.339% | 0% | 37.382% | 0.767 | 2.413 |

Long truth runs are not locally harder under this comparator: they have higher
bp recall and lower gap density than the shortest runs. They split more often
because a longer run presents more opportunities for at least one correlated
dropout. Mouse independently shows the same qualitative contrast at
`>=1000` bp (98.054% bp recall, 37.437% split, 1.548 gaps/kb), although Mouse
has no matched Base arm and is not a confirmatory Human replicate.

### IID and first-order Markov diagnostics

For Human P3, observed internal gaps are only 1.90% of the IID expectation.
Independent sparse bp errors are therefore an inadequate generative account.
A global first-order Markov model is closer for gap count
(`observed/expected = 0.797`) but predicts more than twice as many split truth
runs (`observed/expected split = 0.459`). Base and DAPT show the same pattern;
Mouse is closer in gap count (`0.918`) but still overpredicts split dispersion.

These nulls were fitted in-sample. The audit establishes clustered,
heterogeneous errors; it does not identify sequence cause, prove that a gap is
true TE material independently of the comparator, or license continual
learning.

### Cross-species scope

Mouse preserves high material recall but has 2.144 fragments/truth, reinforcing
the separation between material signal and topology. Fly is a substantially
different failure regime: after all frozen Gate-L packages are excluded, its
positive-only material has 35.148 gaps/kb and 52.058 prediction fragments per
flat-union run. This is a distant positive-recovery diagnostic only. It is not
a Fly whole-genome F1 result and not per-FBti locus fragmentation.

## Consequences for post-training and post-processing

1. **Do not repeatedly rebuild FlyBase.** Frozen exact-r6.68 inputs and the
   348 KB P3-blind packet bundle are the reusable assets. Human remains the
   primary development species; Mouse and Fly are transfer/ontology checks.
2. **Do not fill material gaps from these lengths.** The 5/10/25-bp frequencies
   were measured on consumed test data and provide no distinct-locus or nested
   child denominator.
3. **The defensible gene analogy has two output layers.** Keep the P3
   `material_mask` unchanged. A later `same_extant_locus(atom_i, atom_j)`
   relation may group multiple observed-material atoms while leaving the
   interruption typed as non-TE, nested child, unknown or unresolved. The
   convex hull is never relabelled as parent TE material.
4. **The only mechanism-distinct post-training candidate is relational.**
   After Gate L/O/E, train calibrated atom-pair decisions for `same_locus`,
   `distinct_locus`, `nested` and `unresolved` using information not contained
   in the binary mask: atom/flank sequence, partial alignment and order,
   strand/orientation, family-specific terminal or TSD evidence, third-copy
   support, child-locus evidence and assembly uncertainty. A conservative graph
   partition may join only high-confidence same-locus edges; distinct/nested
   edges are hard conflicts, unresolved edges never force transitive closure,
   and contradictory components abstain. This is not bp smoothing or material
   gap filling.
5. **Continual/hard-example learning remains closed.** `comparator positive AND
   model negative` is not independent material truth. It becomes eligible only
   after blinded annotation distinguishes true continuous-material dropout
   from interruption, nested child, adjacent locus and unresolved evidence,
   with family/locus-blocked splits and a held-out negative denominator.
6. **No new chr11 rule is frozen from this audit.** A chr11 predictive pass is
   justified only if Gate L/O shows that atom recall, rather than relation
   ambiguity, is the limiting variable. Otherwise it would optimize the wrong
   target.

## Post-result ChatGPT Pro review

The Pro review of the frozen numbers reached the same route decision:

- H1 now has a statistical motivation—errors are locally bursty and
  interval-heterogeneous—but still lacks independent supervision. It remains
  `NO-GO` rather than being disproved.
- P3 should be retained as the highest-recall frozen material substrate, not
  described as the most promising fragment solution. DAPT/P3 redistribute
  internal FN mass into different run topology.
- `fragments/truth` is an incomplete and potentially misleading endpoint
  because it ignores gap length and rewards fully missed truth runs.
- a pooled IID process is rejected descriptively; a pooled first-order Markov
  process improves total-gap fit but spreads those gaps across too many truth
  intervals. This supports heterogeneity or higher-order dependence, not a
  unique causal mechanism.
- the one new method class is instance-aware relational post-training followed
  by abstaining typed locus assembly. It is authorized only after Gate L, then
  Gate O, then Gate E; a Human biological-locus panel remains necessary for a
  Human logical-instance claim even if the Fly route-selection panel passes.
- a Human chr11 predictive gap audit could strengthen error-process
  description, but no outcome would currently identify same-locus relations
  or distinguish dropout from interruption. It is therefore not the next
  decision experiment and no GPU run is authorized now.

## Final claim status

- **Engineering:** Human, Mouse and exact Fly frozen tracks were audited with
  raw event tables and a reusable summary; failed Fly `12124904_4` is retained
  but excluded, and recovery `12124968_4` passed.
- **Scientific:** high bp recall coexists with substantial comparator-run
  splitting; errors are correlated and heterogeneous; longer runs split more
  through cumulative exposure even when local gap density is lower; P3/DAPT
  mainly alter error clustering rather than internal FN mass.
- **Descriptive only:** exact gap tails, position/seam enrichment, Mouse
  transfer topology and all Fly positive-only values.
- **Closed:** raw FlyBase reconstruction, threshold/gap filling from these
  test sets, generic hard-example mining and direct gene-HMM transfer.
- **Next only:** `Gate L -> Gate O -> Gate E -> at most one abstaining,
  nested-preserving same-locus relation model`; continue atom detection work
  only if those gates show independently confirmed material dropout is the
  bottleneck.
