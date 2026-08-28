#!/usr/bin/env bash
#SBATCH --job-name=TE_D1H_D2_R1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/outputs/TE-STRUCTURE-PILOT-20260825-R1/decision-20260828-rescue-1/logs/d1h-d2-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/outputs/TE-STRUCTURE-PILOT-20260825-R1/decision-20260828-rescue-1/logs/d1h-d2-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/decision-20260828-rescue-1
LEMMI=${ROOT}/outputs/LEMMI-TE-BENCH-20260824-R1
ATTEMPT=${LEMMI}/attempt-12066076
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1

mkdir -p "${RUN_ROOT}/d1-flybase" "${RUN_ROOT}/d2-flybase"
cd "${ROOT}"

python "${SCRIPT_ROOT}/length_stratified_eval.py" \
  --truth "${ATTEMPT}/truth.canonical.tsv" \
  --prediction "${LEMMI}/hite-claim-attempt-12066193/hite.canonical.tsv" \
  --lengths "${ATTEMPT}/contig_lengths.json" \
  --truth-tier T1 \
  --out-json "${RUN_ROOT}/d1-flybase/hite.json" \
  >/dev/null

python "${SCRIPT_ROOT}/repeatmasker_flybase_alignment.py" \
  --flybase-truth "${ROOT}/data/raw/benchmark_v1/flybase/FB2026_02/dmel_r6.68/derived/curated_positive_truth_v1/flybase_r668_curated_positive_instances.bed" \
  --repeatmasker-prediction "${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_ANIMALS_20260617/fruit_fly/fruit_fly.rmsk_te_strict.bed" \
  --contig-lengths "${ATTEMPT}/contig_lengths.json" \
  --truth-format bed \
  --prediction-format bed \
  --output "${RUN_ROOT}/d2-flybase/repeatmasker_vs_flybase.json" \
  >/dev/null
