# PIPE-TEFM-REPAIR-20260618

Follow-up confirmation and repair pipeline after two surprising screen results:

- A2 mixed animal model had very poor held-out invertebrate TE-F1.
- GENERanno embedding clustering underperformed a strong k-mer/GC contrastive baseline.

This pipeline keeps the base fixed to GENERanno, window fixed to 4096 bp, and seed fixed to 42.
It runs three mixed-training variants, segment threshold/postprocess sweeps, a larger 4096
superfamily rerun, and archive-parity embedding diagnostics.
