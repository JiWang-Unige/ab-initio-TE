# PIPE-TEFM-SEG-SF-20260618

Follow-up screen after `PIPE-TEFM-SUPP-20260617`.

Scope:

- GENERanno only.
- Windows: 2048 and 4096.
- Single seed 42.
- Overlap sliding inference and center-weight merge.
- Segment-level, boundary, and fragmentation metrics.
- Postprocess smoothing: overlap merge, gap merge, min-length filter, and HMM/CRF-style Viterbi smoothing.
- Superfamily token head initialized from the binary fine-tuned GENERanno checkpoint.
- UCSC-derived TE fragment embedding clustering with pretrained, fine-tuned, contrastive-projected, and sequence-only baselines.
