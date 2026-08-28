#!/usr/bin/env bash
# CPU-only D1 rescue: both GPU predictions from 12097785 completed before its
# stdout flush failed, so only run the frozen length-stratified evaluator.
#SBATCH --job-name=TE_D1_H_EVAL
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/d1-human-eval-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/d1-human-eval-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
SOURCE_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/human-d1-12097785
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/human-d1-eval-${SLURM_JOB_ID}

mkdir "${RUN_ROOT}"
cd "${ROOT}"

for method in base_ce dapt_ce; do
  python "${SCRIPT_ROOT}/length_stratified_eval.py" \
    --truth "${SOURCE_ROOT}/truth.canonical.tsv" \
    --prediction "${SOURCE_ROOT}/${method}.canonical.tsv" \
    --lengths "${SOURCE_ROOT}/lengths.json" --truth-tier T0 \
    --out-json "${RUN_ROOT}/${method}.length-stratified.json"
done

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
