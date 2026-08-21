# Threshold and Length-Adaptive Postprocess Diagnostic

- Exp ID: `PIPE-TEFM-CAP-POSTPROC-20260701`
- Profile: bounded diagnostic only; no SOTA or capability claim.
- Primary view: segment-F1@IoU0.8 and boundary-F1@5bp, with missed/deletion/overmerge guardrails.

## Key Results

### human_test

- Raw t=0.50: bp-F1 `0.8369`, segment-F1 `0.1542`, boundary-F1 `0.0763`, missed `0.2869`, deleted_true_backed `0.0000`.
- Best observed segment row: `lenadaptive_raw0.80_hmm1_cut80` segment-F1 `0.4354`, boundary-F1 `0.2086`, missed `0.2992`, deleted_true_backed `0.8583`, overmerge `0.0964`.
- Best strict-guardrail-safe row: `raw_t0.20` segment-F1 `0.2422`, boundary-F1 `0.1143`, missed `0.2541`, deleted_true_backed `0.0000`, pred_true_backed `0.6721`, overmerge `0.0550`.

### mouse_quick

- Raw t=0.50: bp-F1 `0.8232`, segment-F1 `0.1437`, boundary-F1 `0.0513`, missed `0.1133`, deleted_true_backed `0.0000`.
- Best observed segment row: `gap25_min40_t0.60` segment-F1 `0.5034`, boundary-F1 `0.1724`, missed `0.1200`, deleted_true_backed `0.4370`, overmerge `0.1071`.
- Best strict-guardrail-safe row: `gap25_min40_t0.50` segment-F1 `0.4589`, boundary-F1 `0.1575`, missed `0.1133`, deleted_true_backed `0.1042`, pred_true_backed `0.7606`, overmerge `0.1127`.

## Interpretation

- Multi-threshold/postprocess choices explain part of the observed fragmentation gap, especially on mouse, but the best segment rows often violate true-backed deletion guardrails.
- Human and mouse prefer different safe settings; therefore no universal fixed recipe is promoted from this screen.
- Length-adaptive short-raw/long-HMM variants can preserve some short calls, but they also increase split/fragment counts for long TE in this bounded panel.
- This result stays in diagnostic/comparator territory and does not reopen DEC-001 or DEC-002.
