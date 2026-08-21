# PIPE-TEFM-FINAL-INTERPRET-20260630 occlusion smoke

## Summary

- Slurm job: `9853298`, completed `0:0` on GPU.
- Inputs: matched-control fragment pairs from `matched_control_pairs.tsv`.
- Scope: bounded fragment-level occlusion smoke, not claim-grade attribution.
- Context: fragment length plus special tokens for both binary and SF5 models.
- Perturbation: 64 bp chunks replaced with `N`.
- Output rows: 34 fragments, 612 detail rows.

## Key results

- High-score strict-BG no longer reproduces as high-score under 512 bp fragment context. Original binary mean is `0.0205` for cases and `0.0045` for matched BG controls. This means the earlier binary high-score signal depends on the original full-window/flanking context or scoring protocol and should not be interpreted from isolated 512 bp fragments.
- High-score strict-BG SF5 main4 score is zero and unchanged by occlusion. This further rejects hidden-TE language for this candidate set.
- Unknown-main4-like cases retain high SF5 main4 scores in fragment context: original mean `0.8982` for cases versus `0.6250` for matched known-main4 controls.
- Unknown-main4-like SF5 scores are strongly occlusion-sensitive: mean delta `0.3028`, max delta `0.7285`. Controls are also occlusion-sensitive but weaker on average: mean delta `0.0630`.
- Binary scores for Unknown-main4-like cases are also occlusion-sensitive: mean delta `0.0916` for cases versus `0.0698` for controls.

## Interpretation

- The strict-BG branch should be treated as a full-window false-positive/context-trigger diagnostic, not a fragment-level hidden-TE signal.
- The Unknown branch has real model-level local sensitivity, especially under SF5, but the matched-control addendum already showed poor GC matching. The safe conclusion is high-GC/SVA-like/model-bias annotation audit, not automatic main4 relabeling.
- Claim-grade attribution would need full-window context, alternate perturbation baselines, better GC-matched controls, and coordinate-level RepeatMasker/Dfam/UCSC audit.

## Outputs

- `occlusion_smoke/occlusion_status.json`
- `occlusion_smoke/occlusion_summary.tsv`
- `occlusion_smoke/occlusion_detail.tsv`
