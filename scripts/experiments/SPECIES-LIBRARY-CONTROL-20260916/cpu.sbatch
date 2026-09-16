#!/bin/bash
#SBATCH --job-name=te-species-library
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=outputs/SPECIES-LIBRARY-CONTROL-20260916/%x-%j.log
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
python3 scripts/experiments/SPECIES-LIBRARY-CONTROL-20260916/diagnostic.py "${1:?prepare or score}"
