#!/usr/bin/env bash
# CPU-only exact provenance enrichment. Resources are supplied by sbatch CLI.
#SBATCH --job-name=contrastive_bed_enrichment_r1
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/contrastive_bed_enrichment_r1_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/contrastive_bed_enrichment_r1_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
INPUT=/home/users/j/jwang/TE_final/archive/v1_modules/module5_contrastive/data/te_fragments.jsonl
BED_ROOT=/home/users/j/jwang/TE_final/genome_data/animals
OUTPUT_ROOT="$ROOT/outputs/contrastive_bed_enrichment_r1_$SLURM_JOB_ID"

mkdir -p "$ROOT/logs" "$OUTPUT_ROOT"
python3 "$ROOT/scripts/experiments/CONTRASTIVE-IDENTITY-SCREEN-20260824-R1/enrich_module5_from_bed.py" \
  --fragments "$INPUT" \
  --bed-root "$BED_ROOT" \
  --output "$OUTPUT_ROOT/enriched_fragments.jsonl"
printf 'COMPLETED\n' > "$OUTPUT_ROOT/STATUS"
