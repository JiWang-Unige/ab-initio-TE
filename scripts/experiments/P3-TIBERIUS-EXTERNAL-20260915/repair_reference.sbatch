#!/bin/bash
#SBATCH --job-name=tib-reference-full
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=12:00:00
#SBATCH --array=0-1
#SBATCH --output=outputs/P3-TIBERIUS-EXTERNAL-20260915/logs/reference-%A_%a.log
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
TE_SPECIES=(cow platypus)
python3 scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/repair_reference.py "${TE_SPECIES[$SLURM_ARRAY_TASK_ID]}"
