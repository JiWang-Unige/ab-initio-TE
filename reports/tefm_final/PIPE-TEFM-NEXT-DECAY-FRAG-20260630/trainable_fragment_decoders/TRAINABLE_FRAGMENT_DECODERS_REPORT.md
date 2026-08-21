# PIPE-TEFM-NEXT-DECAY-FRAG-20260630 trainable fragment decoders

## Scope

Bounded smoke for trainable downstream decoders on frozen forward/reverse bp probability tracks.
This tests whether learned boundary/CRF/duration components show signal before integrating them into backbone training.

## Headline

- Windows: 40; train fraction: 0.6.
- Best test variant: `consensus_min_crf_posthoc` segment-F1 0.4685, boundary-F1 0.1261, missed true rate 0.0161.

## Interpretation rules

- Promote only if a trainable decoder beats consensus+CRF and does not increase missed_true_rate or true-backed deletion.
- This is not yet end-to-end HMM/CRF training on the backbone; it is a low-cost structural screen to decide which component deserves full integration.
