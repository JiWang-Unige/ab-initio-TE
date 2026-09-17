# Historical evidence source provenance

Retrieved on 2026-09-17 from the validated `baobab` SSH route. Only four small summary tables were copied; no FASTA, checkpoint, run directory, log directory, or large result asset was copied.

## Copied source files

| Local copy | Remote source | SHA-256 |
|---|---|---|
| `hg38_backbone_finetune_eval_metrics.csv` | `/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/results/tables/hg38_backbone_finetune_eval_metrics.csv` | `32b66fc1f37b02f124d58d8c863eebee507b9cafab876e07c42af1e7dd262133` |
| `hg38_backbone_finetune_eval_seed_metrics.csv` | `/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/results/tables/hg38_backbone_finetune_eval_seed_metrics.csv` | `c26347ee9b2014e56422767621f415967e8d5aa99449c699dcd0179188213de5` |
| `fig2_backbone_comparison.csv` | `/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/results/tables/fig2_backbone_comparison.csv` | `9df4b4eb69b80e1591efa53270f2a602352b783207a24202e1eae84ab8b9d1a3` |
| `repeatmasker_human_library_comparison.tsv` | `/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/archive/v1_modules/module2_repeatmasker/results/full/repeatmasker_comparison.tsv` | `d17ef62b9a975688dd2faee37ba36795eeed5896d83fe0e6c97b14c7cb69f9a5` |

## Protocol identities

- **Remote v2 hg38 backbone table:** hg38 main split; training chromosomes `chr1,chr3,chr5,chr7,chr9`; validation `chr11,chr13,chr15`; test `chr17,chr19,chr20,chr21,chr22`; bp-level binary TE detection; seeds `0,1,2` for completed N1/N2/N3 and N9/N9b window rows. The HyenaDNA rows in the primary summary are retained as `not_found`, not converted to missing zeros.
- **Archived human-library RepeatMasker table:** archive/v1; each target is evaluated on `chr1`; `RepeatMasker -species human -pa 16 -xsmall -gff`; scored against the target species' `rmsk_te.bed.gz`; one completed run per target species. It is historical and uses a different version/protocol from v2/v6.
- **Local GLM window table:** `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/window_sweep.tsv`; human H0 quick screen, token-proxy binary TE detection, seed 42, 800 steps. The source contains 20 rows (four backbones × five windows); the similarly named `window_sweep_current.tsv` contains only 18 rows and was not used for the complete matrix table.
- **Local NTv2/NTv3 transfer table:** `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`; 495 source rows, aggregated to 90 model × window × panel groups; one seed (42), 1200 windows/species, animal/plant one-chromosome transfer screen. Aggregation is reported as `mean_te_f1`; it is not merged with the remote v2 bp-level table.

## Copy and validation method

The four remote files were copied with `scp baobab:<remote-path> <local-path>`. SHA-256 was computed locally and on baobab after copying. Derived TSVs under `docs/manuscript/20260917/tables/` were generated from the local source summaries, retaining protocol/source/endpoint/split/seed fields. Validation results are recorded in the sibling `VALIDATION.json` and `VALIDATION.md` files.

The current paper direction is the multispecies TE-map plus downstream-utility manuscript. The earlier P3-only proposal remains in the manuscript discussion files as historical decision context; it does not replace this multi-species evidence inventory.

Commit formatting: derived manuscript TSVs use `NA` for missing cells and omit surplus blank EOF lines. Numeric values are unchanged. Copied source CSV/TSV files retain their original CRLF endings and exact bytes; the whitespace check treats CR-at-EOL as intentional.
