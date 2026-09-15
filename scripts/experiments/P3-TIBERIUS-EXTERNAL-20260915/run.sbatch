#!/bin/bash
#SBATCH --job-name=tib-external-five
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=06:00:00
#SBATCH --array=0,20%2
#SBATCH --output=outputs/P3-TIBERIUS-EXTERNAL-20260915/logs/core-%A_%a.log
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1 WANDB_DISABLED=true TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=/home/users/j/jwang/ab-initio-TE/.cache/huggingface
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
python3 scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/run_core.py "$SLURM_ARRAY_TASK_ID"
