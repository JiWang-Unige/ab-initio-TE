# Matched NTv2 class arm: training and DEV result

Slurm job `12889091` completed with exit code `0:0` in 1:02:05. The run
used the frozen six-species binary-D encoder, a fresh eight-state native
classifier, last-two-block fine-tuning, seed 42, 900 optimizer steps, and the
predeclared class weights and one-tile-per-species sampling. Validation was
performed every 150 steps and selected step 900 by pooled all-eight
token-majority macro-F1 on CAL (`0.6022688433`). DEV was evaluated once after
reloading that selected checkpoint; no DEV-based selection or threshold tuning
was performed.

The selected checkpoint is on Baobab at
`outputs/UNIFIED-NTV2-REPRESENTATION-20260918/class_training/last2-seed42-12889091/best_model`.
The copied raw outputs are in
`results/class_training-12889091/{training_meta,validation_history,test_results}.json`.

## Pooled DEV result

Token metrics use native six-base tokens plus four separate 1-bp tail tokens
(4096 = 682x6 + 4x1; 686 content tokens per record). The base-pair (bp)
metrics expand each token argmax over its represented 6-bp or 1-bp span and
compare with the original 4,096-bp labels. Thus bp metrics are not obtained by
changing the label projection or by selecting a checkpoint.

| endpoint | support | accuracy | macro precision | macro recall | macro-F1 |
|---|---:|---:|---:|---:|---:|
| token majority | 4,116,000 | 0.9053644 | 0.7026265 | 0.6000547 | 0.6066181 |
| expanded bp | 24,576,000 | 0.9053371 | 0.7034569 | 0.5996796 | 0.6067215 |

## Pooled per-class metrics

| class | token support | token P | token R | token F1 | bp support | bp P | bp R | bp F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BG | 2,742,732 | 0.9608 | 0.9386 | 0.9496 | 16,355,145 | 0.9602 | 0.9391 | 0.9495 |
| SINE | 246,173 | 0.8803 | 0.9339 | 0.9063 | 1,475,297 | 0.8814 | 0.9322 | 0.9061 |
| LINE | 525,055 | 0.8509 | 0.9161 | 0.8823 | 3,141,175 | 0.8519 | 0.9158 | 0.8827 |
| LTR | 230,848 | 0.7689 | 0.7908 | 0.7797 | 1,381,150 | 0.7696 | 0.7901 | 0.7797 |
| DNA | 302,498 | 0.6944 | 0.8362 | 0.7587 | 1,811,425 | 0.6954 | 0.8353 | 0.7589 |
| KNOWN_OTHER_TE | 17,271 | 0.6731 | 0.2872 | 0.4026 | 103,414 | 0.6734 | 0.2873 | 0.4028 |
| AMBIGUOUS_TE | 43,584 | 0.0000 | 0.0000 | 0.0000 | 261,269 | 0.0000 | 0.0000 | 0.0000 |
| UNCLASSIFIED | 7,839 | 0.7927 | 0.0976 | 0.1738 | 47,125 | 0.7957 | 0.0977 | 0.1740 |

The model has strong pooled discrimination for BG and the four main TE
classes. The low scores for AMBIGUOUS_TE and UNCLASSIFIED are retained as
observed outcomes; they are rare/uncertain ontology states and should not be
silently folded into BG or the main TE classes. KNOWN_OTHER_TE has moderate
precision but low recall, so this class arm is not by itself evidence of a
complete eight-state TE map.

## Per-species DEV metrics

The following are macro-F1 and accuracy over the classes with positive support
within each species, matching the evaluator's `support > 0` macro rule.
Absent classes remain in the per-class JSON with support zero and F1 zero, but
are excluded from that species-level macro average. Token and bp values are
both shown; bp expansion changes the values only slightly because almost all
content tokens represent six bases.

| species | active/8 classes | absent classes | token macro-F1 | token accuracy | bp macro-F1 | bp accuracy |
|---|---:|---|---:|---:|---:|---:|
| human | 8/8 | none | 0.5455 | 0.9110 | 0.5453 | 0.9107 |
| mouse | 7/8 | AMBIGUOUS_TE | 0.5956 | 0.9093 | 0.5954 | 0.9092 |
| chicken | 7/8 | KNOWN_OTHER_TE | 0.4681 | 0.9682 | 0.4687 | 0.9683 |
| zebrafish | 8/8 | none | 0.4644 | 0.8109 | 0.4644 | 0.8108 |
| pig | 8/8 | none | 0.5189 | 0.8944 | 0.5191 | 0.8946 |
| *C. elegans* | 8/8 | none | 0.4801 | 0.9385 | 0.4803 | 0.9384 |

The species macro-F1 values should be read alongside the pooled per-class
table and the full per-species/per-class JSON, not as a binary TE-versus-BG
ranking. Differences reflect the class mixture and class-specific errors in
each species panel; this report does not isolate a causal effect of a rare
uncertain class. Chicken's high accuracy coexists with low macro-F1 because its
DEV panel is BG-heavy, while zebrafish has lower accuracy under its observed
class mixture and error pattern.

## Interpretation boundary

This is a successful matched class-training run and a complete eight-state
DEV report, but it is not an independent biological validation: the class
labels are painted from the frozen comparator-derived ontology on the exact D
coordinates. The class arm is suitable for the predeclared representation
comparison once the three-arm SIB extraction finishes. The material
probability remains the seven non-BG class probabilities; the zero recall for
AMBIGUOUS_TE and the low UNCLASSIFIED recall should remain visible in any
claim about direct multi-class TE mapping.
