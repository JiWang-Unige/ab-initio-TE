#!/usr/bin/env bash
# HiTE-designated full-length A0 and matched deterministic A1 copy search.
#SBATCH --job-name=TE_C5_HITE_A1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/C5-HYBRID-PILOT-20260830/hite-a1-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/C5-HYBRID-PILOT-20260830/hite-a1-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/C5-HYBRID-PILOT-20260830/c5_hybrid_pilot.py
ASSEMBLY=${ROOT}/.backup/data/genome_data/current_eukaryotes/animals/human/hs1.fa
HITE_NATIVE=${ROOT}/outputs/C5-HYBRID-PILOT-20260830/hite-native-12117941/native
REFERENCE=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/hite-chr17-12097868
LENGTHS=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/eval/human.lengths.json
RUN_ROOT=${ROOT}/outputs/C5-HYBRID-PILOT-20260830/hite-a01-${SLURM_JOB_ID}

mkdir "${RUN_ROOT}"
mkdir "${RUN_ROOT}/a0" "${RUN_ROOT}/a1" "${RUN_ROOT}/evaluation"
cd "${ROOT}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
module load GCCcore/10.3.0 minimap2/2.20

python "${SCRIPT}" hite-a0 \
  --full-length-gff "${HITE_NATIVE}/HiTE.full_length.gff" \
  --assembly "${ASSEMBLY}" \
  --prefix-seqid chr17 \
  --prefix-end 9830400 \
  --out-dir "${RUN_ROOT}/a0"

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

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
