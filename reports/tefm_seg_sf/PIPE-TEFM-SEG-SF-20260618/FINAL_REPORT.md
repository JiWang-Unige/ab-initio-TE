# PIPE-TEFM-SEG-SF-20260618 Final Report

Date: 2026-06-18

Status: completed.

Scope: GENERanno-only single-seed follow-up using 2048 bp and 4096 bp windows. The run covers overlap center-merge inference, segment/boundary/fragmentation/postprocess evaluation, token-level superfamily head training, and TE-fragment embedding clustering on B_animal and D_crosskingdom panels.

## Outputs

- Summary status: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/current_status.json`
- Overlap/postprocess: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/overlap_postprocess_summary.tsv`
- Edge bins: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/edge_bin_summary.tsv`
- Superfamily: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/superfamily_summary.tsv`
- Embedding clustering: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/embedding_cluster_summary.tsv`

## Key Results

### Overlap, Segment, and Smoothing

- Raw overlap improves bp-level edge bins, but raw interval quality remains weak: raw segment-F1 ranges from 0.428 to 0.503 across tested windows/strides.
- HMM-style smoothing gives the best segment-level results.
- Best segment-F1: 4096 window, stride 2048, `hmm_penalty2`, bp-F1 0.9427, segment-F1@IoU0.5 0.7442, boundary-F1@100bp 0.6261.
- 4096 stride 1024 is essentially tied: bp-F1 0.9429, segment-F1@IoU0.5 0.7440, boundary-F1@100bp 0.6255.
- 2048 stride 512 with HMM smoothing is slightly lower on segment-F1 but has the best boundary-F1 among top variants: bp-F1 0.9408, segment-F1@IoU0.5 0.7374, boundary-F1@100bp 0.6296.
- Conclusion: use 4096 overlap + center merge as the main setting; keep small-gap/HMM-style smoothing in the postprocess candidate set. Raw threshold alone fragments intervals too much for annotation-quality claims.

### Superfamily Head

- 2048 window: TE detection F1 0.9326, class macro-F1 0.6858, all-6 macro-F1 0.7287.
- 4096 window: TE detection F1 0.9393, class macro-F1 0.7109, all-6 macro-F1 0.7494.
- 4096 improves LINE/LTR/DNA F1 over 2048 while SINE remains high in both.
- Conclusion: 4096 is the better superfamily setting for this screen.

### Embedding Clustering

- All 48 embedding clustering jobs completed after retrying two hardware-placement failures.
- Best individual run: B_animal, length 512, C1 basic sequence features + contrastive projection, ARI 0.9399, NMI 0.9165, holdout macro-F1 0.9083.
- Mean over panels and lengths:
  - C1 basic features + contrastive: ARI 0.8379, NMI 0.8040, holdout macro-F1 0.7405.
  - A1 pretrained GENERanno embedding + contrastive: ARI 0.4878, NMI 0.4834, holdout macro-F1 0.6436.
  - Fine-tuned embedding variants are weaker in this quick clustering screen.
- Conclusion: for current balanced TE fragments, simple sequence composition/k-mer features plus contrastive projection are the strongest clustering baseline; pretrained embeddings improve with contrastive learning but do not beat C1 in this setup.

## Runtime Notes

- The first embedding array exposed CRLF line-ending handling in the command runner; `run_cmd_array.sh` now strips carriage returns.
- 4096 superfamily training OOMed on a 12 GB GPU and was rerun on A100 80 GB.
- Two embedding jobs hit unsupported Blackwell GPU/PyTorch compatibility and were rerun on CPU or non-Blackwell GPU.
- No TFSEGSF jobs remain in the Slurm queue at completion.

## Decision

- Use GENERanno 4096 bp as the main window for the next claim-bearing segment/superfamily stage.
- Treat HMM/small-gap smoothing as required for interval completeness; raw bp threshold is insufficient for annotation-level claims.
- Keep embedding clustering as exploratory evidence; C1 is currently the strongest clustering baseline and must be compared before making a representation-learning claim.
