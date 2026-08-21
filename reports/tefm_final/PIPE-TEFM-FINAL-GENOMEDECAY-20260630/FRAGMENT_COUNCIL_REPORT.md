# PIPE-TEFM-FINAL-GENOMEDECAY-20260630 Fragment Council

## Scope

This council addresses the strict segment/boundary failure mode in `PIPE-TEFM-FINAL-STRICTSEG-20260629`: many TE-positive bp predictions are locally correct, but interval completeness and boundary accuracy are poor under biologically stricter thresholds.

Raw council outputs:

- Claude: `/tmp/fragment_council_20260630_claude.md`
- Codex: `/tmp/fragment_council_20260630_codex.md`
- Antigravity: `/tmp/fragment_council_20260630_agy.md`

## Consensus

All three reviewers converge on the same high-level diagnosis:

- More threshold/gap/HMM/CRF penalty tuning is not the main path forward.
- The main failure is a mismatch between bp-level token classification and interval-level TE annotation.
- Double-strand prediction is worth a small no-training sanity check, but it should not be the primary fix.
- The next component should explicitly model intervals or boundaries.

## Mechanism Attribution

Likely contributors:

- **Training objective**: bp-level BCE/CE does not penalize internal probability valleys that split one true TE into several predicted fragments.
- **Windowing/stitching**: predicted breaks may concentrate near window seams or low-context edge regions; this needs coordinate-level seam-distance diagnostics.
- **Strand/orientation**: possible but not yet evidenced as the dominant mechanism; test by forward vs reverse-complement logit concordance and strand-stratified segment metrics.
- **Postprocess**: current smoothing can reduce short fragments, but aggressive gap/min filters increase missed true rate, indicating deletion rather than repair.
- **Label biology/quality**: plant labels remain too confounded for architecture decisions; animal labels are better but still contain nested TE, solo LTR, truncation, and RepeatMasker fragmentation.

## Recommended Next Component

Priority order:

1. Frozen bp model + lightweight interval refiner.
2. Boundary-aware multi-task head.
3. Double-strand prediction sanity check.
4. Segment-aware / semi-Markov decoder if the first two fail or clearly saturate.
5. Do not continue broad CRF/HMM/gap penalty tuning as the main route.

Minimal interval refiner design:

- Input: bp logits/probabilities, candidate interval features, neighboring-gap features, edge slopes, internal valley counts, optional local sequence features.
- Output: keep/drop/merge/refine candidate intervals or refined interval mask.
- Labels: true interval matching by IoU and boundary distance, using chromosome split.
- Goal: improve strict segment-F1 and boundary-F1 without raising missed true rate.

## Double-Strand Sanity Check

Run only as a cheap inference experiment:

- forward-only baseline;
- reverse-complement flipped-only;
- mean-logit merge;
- max-logit merge;
- consensus/min-logit merge.

Primary acceptance rule: segment-F1 and boundary-F1 must improve without increasing unsupported predicted segments or missed true rate. If the gain is less than about 0.03 segment-F1 and 0.02 boundary-F1, stop this route.

## Required Guardrails

Any future fragmentation fix must report:

- bp precision/recall/F1;
- segment precision/recall/F1 at IoU 0.5/0.8/0.9;
- boundary precision/recall/F1 at 5/10/25 bp;
- mean/median fragments per true TE;
- missed true rate;
- pred true-backed rate;
- short predicted segment count;
- short true-backed rate;
- deleted true-backed vs deleted false-positive fragment rate;
- length-bin and nested-TE stratified recall.

The key test is not "fewer fragments"; it is "fewer false fragments while preserving true-backed short TE and true-interval recall."
