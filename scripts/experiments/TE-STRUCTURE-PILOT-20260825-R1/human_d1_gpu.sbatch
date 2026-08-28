#!/usr/bin/env bash
# Human D1: materialize the first 1,200 chr17 test windows for both matched
# checkpoints, then run the frozen length-stratified evaluator.
# Submit only after the remote smart-sbatch Phase-1/2 checks.
#SBATCH --job-name=TE_D1_HUMAN
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_a100_80gb_pcie:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/d1-human-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/d1-human-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
DATA=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/test/data.jsonl.gz
BASE_MODEL=${ROOT}/software_outputs/dapt_direct_annotation/DAPT-DIRECT-ANNOTATION-20260824-CE/runs/matched-12066158-0
DAPT_MODEL=${ROOT}/software_outputs/dapt_direct_annotation/DAPT-DIRECT-ANNOTATION-20260824-CE/runs/matched-12066158-1
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/human-d1-${SLURM_JOB_ID:?numeric SLURM_JOB_ID is required}

eval "$(conda shell.bash hook)"
conda activate te_benchmark
mkdir -p "${RUN_ROOT}"
cd "${ROOT}"

python "${SCRIPT_ROOT}/human_d1_canonical.py" truth \
  --data-jsonl "${DATA}" \
  --out-truth "${RUN_ROOT}/truth.canonical.tsv" \
  --out-unknown "${RUN_ROOT}/unknown.canonical.tsv" \
  --out-lengths "${RUN_ROOT}/lengths.json" \
  --out-manifest "${RUN_ROOT}/truth.manifest.json"

python "${SCRIPT_ROOT}/human_d1_canonical.py" predict \
  --data-jsonl "${DATA}" --model-dir "${BASE_MODEL}" --model-name base_ce \
  --out-prediction "${RUN_ROOT}/base_ce.canonical.tsv" \
  --out-manifest "${RUN_ROOT}/base_ce.manifest.json" --device cuda

python "${SCRIPT_ROOT}/human_d1_canonical.py" predict \
  --data-jsonl "${DATA}" --model-dir "${DAPT_MODEL}" --model-name dapt_ce \
  --out-prediction "${RUN_ROOT}/dapt_ce.canonical.tsv" \
  --out-manifest "${RUN_ROOT}/dapt_ce.manifest.json" --device cuda

for method in base_ce dapt_ce; do
  python "${SCRIPT_ROOT}/length_stratified_eval.py" \
    --truth "${RUN_ROOT}/truth.canonical.tsv" \
    --prediction "${RUN_ROOT}/${method}.canonical.tsv" \
    --lengths "${RUN_ROOT}/lengths.json" --truth-tier T0 \
    --out-json "${RUN_ROOT}/${method}.length-stratified.json"
done

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
