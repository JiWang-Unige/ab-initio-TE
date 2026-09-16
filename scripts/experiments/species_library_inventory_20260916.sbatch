#!/bin/bash
#SBATCH --job-name=te-species-library-metadata
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=outputs/SPECIES-ANNOTATION-DIAGNOSTIC-20260916/library-%j.log
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python3 scripts/experiments/species_library_inventory_20260916.py
