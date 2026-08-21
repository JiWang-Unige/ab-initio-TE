# PIPE-TEFM-NEXT-DECAY-FRAG-20260630

## Scope

This iteration responds to two open usability gaps:

1. The genome-derived generalization/anchor selector was screen-complete but not clearly usable as new-species trust guidance.
2. Fragmentation reduction from HMM/CRF was post-hoc smoothing, not a trainable model component.

The run includes targeted tri-review/council, selector calibration/action-policy diagnostics, and a bounded trainable-fragment-decoder smoke on frozen bp-model tracks.

## Tri-Review / Council Consensus

- 3/3 tri-review outputs completed (`claude`, `codex`, `agy`) and agree the selector is only partially usable; it needs risk tiers, uncertainty, top-k regret, abstention, and leave-clade-out validation.
- 3/3 council round-1 and round-2 outputs completed. The final consensus is not to launch a large coupled project. Instead:
  - selector should first become a conservative risk/abstention router;
  - fragmentation should prioritize bounded trainable boundary/interval MVPs with strict true-backed guardrails;
  - heavy semi-Markov/full neural CRF/MinHash expansion should wait until MVP gates pass.

Raw outputs:

- `/tmp/tri_review_PIPE-TEFM-NEXT-DECAY-FRAG-20260630/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-NEXT-DECAY-FRAG-20260630/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-NEXT-DECAY-FRAG-20260630/output_c_antigravity.md`
- `/tmp/council_tefm_decay_fragment_20260630/round1_*`
- `/tmp/council_tefm_decay_fragment_20260630/round2_*`

## Selector Calibration

Point-estimate selector is still not usable as a precise confidence formula.

Best point-estimate row:

- feature set: `baseline_plus_kmer`
- split: `leave_species_out`
- RMSE: `0.2642`
- MAE: `0.2194`
- ECE by predicted bin: `0.0372`
- anchor top-1 accuracy: `0.4545`
- anchor top-2 accuracy: `0.6818`
- mean regret: `0.0680`
- usable point-formula gate: `false`

Leave-clade-out remains poor across feature sets (RMSE about `0.40-0.42`), so this selector must not be advertised as cross-clade trust prediction.

Outputs:

- `selector_calibration/selector_calibration_summary.tsv`
- `selector_calibration/selector_calibration_bins.tsv`
- `selector_calibration/selector_species_recommendations.tsv`
- `selector_calibration/SELECTOR_CALIBRATION_REPORT.md`

## Selector Action Policy

A conservative action policy is usable as a limited routing aid, not as an exact F1 formula.

Best action-policy row:

- feature set: `baseline_plus_kmer`
- split: `leave_species_out`
- policy: top-2 shortlist / local probe for all species under the selected conservative gate
- action contains true-best rate: `0.8636`
- action contains true-top2 rate: `0.8636`
- mean regret after action: `0.0071`
- p90 regret after action: `0.0008`
- single-anchor high-confidence coverage: `0.0`

Interpretation:

- The current selector can recommend a top-2 anchor shortlist and warn that local chromosome probing is required before trusting exact TE-F1.
- It cannot yet give a single high-confidence anchor or a reliable cross-clade F1 estimate.
- `selector_confidence_cards.tsv` is the current safest user-facing form: top-2 anchors plus empirical q80/q90 error intervals and a deployment warning.

Outputs:

- `selector_action_policy/selector_action_policy_summary.tsv`
- `selector_action_policy/selector_action_policy_species.tsv`
- `selector_action_policy/selector_confidence_cards.tsv`
- `selector_action_policy/SELECTOR_ACTION_POLICY_REPORT.md`

## Trainable Fragment Decoder Smoke

The frozen-logit trainable decoder smoke completed successfully but did not improve strict interval usability.

Slurm:

- job: `9858072`
- state: `COMPLETED`
- exit code: `0:0`
- elapsed: `00:01:34`

Metrics at IoU `0.8`, boundary `5 bp`:

| Variant | bp-F1 | Segment-F1 | Boundary-F1 | Missed true rate | Pred true-backed rate | Short true-backed rate |
|---|---:|---:|---:|---:|---:|---:|
| consensus_min_crf_posthoc | 0.9692 | 0.4685 | 0.1261 | 0.0161 | 0.8571 | 1.0000 |
| consensus_min_raw | 0.9690 | 0.4462 | 0.1385 | 0.0161 | 0.7500 | 0.4118 |
| trainable_boundary_cnn | 0.9622 | 0.2778 | 0.0185 | 0.0161 | 0.6739 | 0.3000 |
| duration_prior_decoder | 0.9676 | 0.2366 | 0.0430 | 0.0484 | 0.7742 | 0.0000 |
| trainable_linear_crf | 0.9642 | 0.1798 | 0.0674 | 0.0161 | 0.7778 | 1.0000 |

Interpretation:

- A weak trainable layer fitted after frozen logits is not enough; it performs worse than post-hoc CRF.
- This does not reject trainable CRF/boundary heads generally. It says the useful next version must be closer to the backbone output/embedding level or use a richer interval proposal/scorer, not a tiny model on probability tracks alone.
- Duration-prior suppression reduces fragments but deletes true-backed signal and worsens missed true rate, so it cannot be promoted alone.

Outputs:

- `trainable_fragment_decoders/trainable_fragment_decoder_metrics.tsv`
- `trainable_fragment_decoders/TRAINABLE_FRAGMENT_DECODERS_REPORT.md`
- `trainable_fragment_decoders/trainable_fragment_decoder_status.json`

## Next Decision

Current deployable status:

- Exact selector confidence formula: **not usable**.
- Conservative top-2 selector/router with local-probe warning: **screen-usable within known clades**.
- Leave-clade-out selector confidence: **not usable**.
- Frozen-logit trainable decoder: **failed to beat post-hoc CRF**.

Next implementation should not scale these exact frozen decoder variants. If fragmentation remains claim-bearing, the next bounded experiments should be:

1. end-to-end or near-end-to-end boundary-aware head using backbone embeddings;
2. richer interval proposal/scorer with candidate recall audit;
3. trainable CRF only after boundary/emission features are improved;
4. selector leave-clade-out plus public taxonomy/MinHash variables before any claim-grade confidence formula.

