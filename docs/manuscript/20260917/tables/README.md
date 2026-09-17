# Machine-readable evidence tables

These TSVs preserve protocol identity and do not form one cross-protocol leaderboard.

| Table | Protocol | Rows | Endpoint / scope |
|---|---|---:|---|
| `local_glm_window_matrix.tsv` | `PIPE-TEFM-SUPP-20260617-H0-WINDOW-SWEEP` | 20 | DNABERT2, GENERanno, NTv2-500M, HyenaDNA × 512/1024/2048/4096/8192; human H0 token-proxy quick screen |
| `local_ntv2_ntv3_size_transfer_summary.tsv` | `PIPE-TEFM-FINAL-20260623-TRANSFER-MATRIX` | 90 | NTv2/NTv3 size/window × animal_fine/plant_fine transfer means aggregated from 495 source rows |
| `remote_v2_hg38_backbone_summary.tsv` | `TE-FINAL-V2-HG38-BACKBONE-3SEED` | 5 | Remote v2 hg38 backbone summary, including explicit HyenaDNA `not_found` rows |
| `remote_v2_hg38_window_summary.tsv` | `TE-FINAL-V2-HG38-WINDOW-COMPARISON` | 5 | Remote v2 hg38 window comparison, 3 seeds |
| `archived_human_library_rm_summary.tsv` | `TE-FINAL-ARCHIVE-V1-HUMAN-LIBRARY-RM` | 7 | Archive/v1 RepeatMasker `-species human` on external target chr1 panels |

Every table carries `protocol_id`, `source`, `endpoint`, `split`, and `seed_status`. The local NTv2/NTv3 table carries means and species/window counts rather than silently treating its one-seed transfer screen as a repeated-seed estimate. Raw remote summaries and their provenance are under `reports/HISTORICAL-EVIDENCE-INVENTORY-20260917/source/`; validation is in `source/VALIDATION.json` and `source/VALIDATION.md`.
