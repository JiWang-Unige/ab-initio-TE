# Joint Structured Decoder Smoke

- Seed: `42`
- Init model: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42`
- Data: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick`
- Best test variant: `joint_semimarkov_proxy` segment-F1 `0.4258`, boundary-F1 `0.2105`, missed_true_rate `0.3033`

This is a bounded single-seed smoke. It tests structured losses attached to model logits during fine-tuning, not post-hoc smoothing alone.

## Test Metrics

All rows use IoU `0.8` and boundary tolerance `5 bp` on the bounded test split.

| Variant | bp-F1 | Segment-F1 | Boundary-F1 | Missed true rate | Pred segments |
|---|---:|---:|---:|---:|---:|
| `ce_baseline` | 0.7406 | 0.3069 | 0.1414 | 0.2623 | 336 |
| `joint_hmm` | 0.8472 | 0.3836 | 0.2046 | 0.3033 | 147 |
| `joint_crf` | 0.8579 | 0.3631 | 0.0921 | 0.1721 | 125 |
| `joint_semimarkov_proxy` | 0.8690 | 0.4258 | 0.2105 | 0.3033 | 174 |

## Interpretation

- This direction had not previously been tested: the structured objective is used during fine-tuning and gradients update the model/head, unlike post-hoc HMM/CRF smoothing or the frozen-logit decoder smoke.
- There is positive signal: all three structured variants improved test segment-F1 over the CE smoke baseline, and the semi-Markov proxy gave the best segment/boundary result.
- The signal is not clean enough to promote directly. `joint_hmm` and `joint_semimarkov_proxy` both raise missed true rate to `0.3033`; `joint_crf` preserves true intervals better (`0.1721`) but loses boundary-F1.
- The right next step is not to declare success, but to run a better bounded version: keep the joint training setup, add explicit boundary loss / true-retention penalty, and evaluate on the same mouse strict segment panel used by prior fragment screens.
