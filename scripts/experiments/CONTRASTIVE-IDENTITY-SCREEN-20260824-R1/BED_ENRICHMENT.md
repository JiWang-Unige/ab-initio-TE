# Exact Module 5 BED enrichment

This utility restores only metadata that was dropped by the historical Module
5 extractor. For each JSONL row it performs an exact join to the canonical
species BED at:

```text
<bed-root>/<species>/rmsk_te.bed.gz
```

The key is `(species, chrom, start, end, class, family)`. The join must have
exactly one source BED row; missing or duplicate source matches fail with exit
code 2 and no partial output. Output rows add `repeat_name`, `strand`, all raw
BED columns, source-file SHA256, source-row SHA256, and source line number.

No `copy_id`, `superfamily_id`, or `homology_component_id` is created. The
manifest explicitly records those fields as `not_generated_identity_fields`.
Coordinates and family names remain annotation metadata, never copy identity.

Example on Baobab (CPU; no Slurm is required):

```bash
python3 scripts/experiments/CONTRASTIVE-IDENTITY-SCREEN-20260824-R1/enrich_module5_from_bed.py \
  --fragments /home/users/j/jwang/TE_final/archive/v1_modules/module5_contrastive/data/te_fragments.jsonl \
  --bed-root /home/users/j/jwang/TE_final/genome_data/animals \
  --output /home/users/j/jwang/ab-initio-TE/outputs/contrastive_identity_screen_r1/enriched_fragments.jsonl
```
