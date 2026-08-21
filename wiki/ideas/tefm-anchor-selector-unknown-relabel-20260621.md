# Idea: TE-FM anchor selector and Unknown/high-score relabel diagnostics

- slug: `tefm-anchor-selector-unknown-relabel-20260621` · status: **untried** · added: 2026-06-21
- refs: 

## Hypothesis
TE-FM should be offered as kingdom/panel-specific anchors plus a deployable anchor selector, while Unknown and high-score strict-background candidates can be triaged by SF5 main4 predictions and background-inclusive embedding clusters.

## Why it matters
User requested moving beyond a single universal model, testing whether annotation Unknown/high-score unannotated regions are biologically main4-like, checking whether background-inclusive embedding still favors kmer/basic features, and building an annotation-free anchor recommendation formula.

## Next step
Run PIPE-TEFM-ANCHOR-20260621 to completion, then use BG+main4 embedding, SF5 candidate predictions, insect-primary eval, and deployable formula metrics to decide whether to carry forward into publication validation.

## Log
- 2026-06-21: created (status=untried)
