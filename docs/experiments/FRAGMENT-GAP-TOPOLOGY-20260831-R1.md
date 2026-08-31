# Fragment gap topology audit

Date: 2026-08-31

Status: **frozen CPU-only descriptive protocol; results pending**

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

## Claim status before execution

- **Engineering:** reusable FlyBase packets and all frozen binary tracks exist;
  the audit implementation is CPU-only and applies no rescue.
- **Scientific:** current results already support that high bp recovery does
  not guarantee comparator-run topology.
- **Closed:** raw FlyBase reconstruction, generic hard-example mining,
  material gap filling and direct transfer of gene HMM grammar.
- **Next only:** complete this descriptive audit while Gate L annotation
  calibration proceeds independently.
