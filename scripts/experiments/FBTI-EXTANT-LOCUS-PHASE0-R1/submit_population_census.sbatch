#!/usr/bin/env bash
# Gate-L label-blind S0/S1 population census; no panel sampling or annotation.
#SBATCH --job-name=FBTI_L_CENSUS
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/population-census-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/population-census-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submission}"

ROOT=/home/users/j/jwang/ab-initio-TE
ASSET=${ROOT}/data/raw/benchmark_v1/flybase/FB2026_02/dmel_r6.68
TRUTH=${ASSET}/derived/curated_positive_truth_v1
P3=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flybase-shards-20260830-fly4-r1/prediction.tsv
LENGTHS=${ROOT}/outputs/LEMMI-TE-BENCH-20260824-R1/attempt-12066076/contig_lengths.json
ASSEMBLY=${ASSET}/dmel-all-chromosome-r6.68.fasta.gz
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/population-census-${ATTEMPT_TAG}
SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/build_population.py

if [[ -e "${OUT}" ]]; then
  echo "refusing to reuse output directory: ${OUT}" >&2
  exit 2
fi

cd "${ROOT}"
python3 "${SCRIPT}" \
  --truth-metadata "${TRUTH}/flybase_r668_curated_positive_instances.tsv" \
  --overlap-pairs "${TRUTH}/flybase_r668_curated_positive_overlap_pairs.tsv" \
  --p3-atoms "${P3}" \
  --contig-lengths "${LENGTHS}" \
  --assembly-fasta "${ASSEMBLY}" \
  --output-dir "${OUT}"

printf 'PASS\n' > "${OUT}/STATUS"
