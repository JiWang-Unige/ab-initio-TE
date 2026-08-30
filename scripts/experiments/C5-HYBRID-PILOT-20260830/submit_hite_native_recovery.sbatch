#!/usr/bin/env bash
# Re-run the pinned HiTE 3.3.3 Human chr17 pilot only to persist native artifacts.
#SBATCH --job-name=TE_C5_HITE_NATIVE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=40
#SBATCH --mem=128G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/C5-HYBRID-PILOT-20260830/hite-native-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/C5-HYBRID-PILOT-20260830/hite-native-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1/run_hite_chr17_pilot.py
ASSEMBLY=${ROOT}/.backup/data/genome_data/current_eukaryotes/animals/human/hs1.fa
STRICT_BED=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_ANIMALS_20260617/human_hs1/human_hs1.rmsk_te_strict.bed
PLUS_UNKNOWN_BED=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_ANIMALS_20260617/human_hs1/human_hs1.rmsk_te_plus_unknown.bed
SIF=${ROOT}/software_outputs/tefm_new_directions/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/hite/hite_3_3_3.sif
RUN_ROOT=${ROOT}/outputs/C5-HYBRID-PILOT-20260830/hite-native-${SLURM_JOB_ID}

HITE_NODE_SCRATCH=$(mktemp -d "/tmp/te-hite-native-${SLURM_JOB_ID}-XXXXXX")
export HITE_NODE_SCRATCH
trap 'rm -rf -- "${HITE_NODE_SCRATCH}"' EXIT

cd "${ROOT}"
python "${SCRIPT}" \
  --project-root "${ROOT}" \
  --assembly "${ASSEMBLY}" \
  --strict-bed "${STRICT_BED}" \
  --plus-unknown-bed "${PLUS_UNKNOWN_BED}" \
  --sif "${SIF}" \
  --output-root "${RUN_ROOT}" \
  --threads "${SLURM_CPUS_PER_TASK}" \
  --persist-native-output

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
