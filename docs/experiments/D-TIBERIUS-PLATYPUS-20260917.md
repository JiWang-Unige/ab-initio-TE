# Fixed D mask → Tiberius on the existing platypus panel

Frozen before new inference on 2026-09-17 under the author's request to test the six-species model's gene-annotation utility. This is a retrospective extension of the completed P3 platypus experiment, not a new independent animal confirmation.

Use all 20 existing platypus cores (100 Mb core denominator, the same 100 kb halos), exact `GCF_004115215.2` sequence and existing reference units from `P3-TIBERIUS-EXTERNAL-20260915/prepared/platypus`. Do not select by previous gene or TE scores. Cattle is not included because the D-specific sealed-species boundary remains in force.

Add exactly one arm: D seed42, NTv2-500M, frozen six-species CAL with threshold 0.42330056285498807, no retraining or target calibration. Use the existing 4096-bp nonoverlapping native D inference starting at each halo-region origin; the short tail is projected with the same 6-mer/single-base contract. This is regional inference, not a whole-genome cost claim. Mask only predicted ACGT bases, retaining all original uppercase sequence letters and ambiguity characters.

Run the same `mammalia_softmasking_v2` Tiberius weights, 400050-bp input length, batch 1, native six-channel input observer and Tiberius 2.0.7 container as the completed P3 experiment. Reuse its U_soft, U_nosm, R_TE, R_all and P3 outputs on the identical cores; retain separate provenance and inference costs. Old source outputs remain unchanged.

Primary comparison: D minus species-matched R_TE. Workflow comparison: D minus U_nosm; fixed-receiver mask contrast: D minus U_soft. Also report D minus P3 and R_all descriptively. Score exact CDS-chain/locus with the existing reference mapping, all gain/loss sets, and ten-chromosome paired bootstrap (10000 resamples, seed42). This bootstrap is spatial uncertainty, not extra training seeds. Reference annotations are comparators, not independent biological truth. Do not claim superiority or equivalence from a CI crossing zero.

Complete one preselected c00 engineering smoke, then all c01–c19 without checking intermediate accuracy or choosing only favorable cores. Smoke verifies identical uppercase input, a six-channel softmask tensor, and native GTF/GFF3 equivalence. Stop on a real engineering error and retain its directory; do not change weights, threshold or core list as a repair. Do not calculate the final main comparison before all 20 D cells and all reused controls qualify.

Resources: one 3090 GPU, 8 CPUs, 96 GB, up to 6 hours per core (inherited native-job ceiling); at most one D-utility core concurrently, scheduled around the existing two-GPU global first-batch limit. No new gene-model training, no nonmammalian softmask assumption, no sealed data and no new benchmark timing claim.

If D is later replaced by a fixed adapter/routed material workflow, this result remains a D baseline; the final workflow needs its own utility result. Completion is independent of the direction of the effect.
