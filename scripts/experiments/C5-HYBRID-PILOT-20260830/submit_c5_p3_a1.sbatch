#!/usr/bin/env bash
# Deterministic full-hs1 copy search and same-denominator A0/A1 evaluation.
# Submit afterok on the matching A0 job with the same ATTEMPT_TAG.
#SBATCH --job-name=TE_C5_P3_A1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=06:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/C5-HYBRID-PILOT-20260830/p3-a1-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/C5-HYBRID-PILOT-20260830/p3-a1-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set the same ATTEMPT_TAG used by C5 P3 A0}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/C5-HYBRID-PILOT-20260830/c5_hybrid_pilot.py
ASSEMBLY=${ROOT}/.backup/data/genome_data/current_eukaryotes/animals/human/hs1.fa
RUN_ROOT=${ROOT}/outputs/C5-HYBRID-PILOT-20260830/${ATTEMPT_TAG}
REFERENCE=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/hite-chr17-12097868
LENGTHS=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/eval/human.lengths.json

mkdir "${RUN_ROOT}/a1"
mkdir "${RUN_ROOT}/evaluation"
cd "${ROOT}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
module load GCCcore/10.3.0 minimap2/2.20

python "${SCRIPT}" a1 \
  --seeds-tsv "${RUN_ROOT}/a0/a0.seeds.tsv" \
  --seeds-fasta "${RUN_ROOT}/a0/a0.seeds.fa" \
  --assembly "${ASSEMBLY}" \
  --prefix-seqid chr17 \
  --prefix-end 9830400 \
  --out-dir "${RUN_ROOT}/a1"

python "${SCRIPT}" evaluate \
  --truth "${REFERENCE}/truth.canonical.tsv" \
  --unknown "${REFERENCE}/unknown.canonical.tsv" \
  --lengths "${LENGTHS}" \
  --a0 "${RUN_ROOT}/a0/a0.canonical.tsv" \
  --a1 "${RUN_ROOT}/a1/a1.canonical.tsv" \
  --out-dir "${RUN_ROOT}/evaluation/work" \
  --result-json "${RUN_ROOT}/evaluation/a0-a1.result.json"

printf 'PASS\n' > "${RUN_ROOT}/A1_STATUS"
