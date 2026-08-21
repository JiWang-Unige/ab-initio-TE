# Fragment Graph Linker Screen

- Exp ID: `PIPE-TEFM-CAP-FRAGGRAPH-20260701`
- Seed: `42`
- Init model: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42`
- Train data: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick`
- Eval panels: `human_test:software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick/test/data.jsonl.gz, mouse_quick:software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/mouse_A1_w4096_quick/test/data.jsonl.gz`
- Promotion gate pass: `False`
- Gate-pass panels: `[]`

This is a bounded capability-pursue screen. The primary decode preserves all CE raw fragments and learns graph links/fills between adjacent fragments; it is not a gap/threshold/HMM tuning run.
