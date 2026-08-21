# Joint Structured Decoder Smoke

- Seed: `42`
- Init model: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42`
- Data: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick`
- Best test variant: `interval_survival_decoder` segment-F1 `0.3756`, boundary-F1 `0.1805`, missed_true_rate `0.2910`
- Best gate-eligible variant: `interval_survival_decoder`
- CE test baseline: segment-F1 `0.3069`, boundary-F1 `0.1414`, missed_true_rate `0.2623`
- Promotion gate pass: `True`

This is a bounded single-seed smoke. It tests structured losses attached to model logits during fine-tuning, not post-hoc smoothing alone.
The retention variant directly penalizes missed true TE bases; deleted-fragment diagnostics compare each variant against the CE baseline to distinguish false-fragment removal from true-backed fragment deletion.
