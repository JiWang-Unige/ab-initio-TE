#!/bin/bash
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=outputs/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/logs/fms_conf_audit-%A.out
#SBATCH --error=outputs/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/logs/fms_conf_audit-%A.err
set -euo pipefail
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
cd /home/users/j/jwang/ab-initio-TE
python -u scripts/experiments/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/compare_conf_rule.py chicken
python -u scripts/experiments/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/compare_conf_rule.py zebrafish
