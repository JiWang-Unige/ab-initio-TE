#!/usr/bin/env bash
#SBATCH --job-name=gap-c-container
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=logs/gap-c-container_%j.out
#SBATCH --error=logs/gap-c-container_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_gap_tiberius_c
OUT=/home/users/j/jwang/ab-initio-TE/software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1
test ! -e "$OUT"
mkdir "$OUT"
export SINGULARITY_CACHEDIR="$OUT/cache"
export SINGULARITY_TMPDIR="$OUT/tmp"
mkdir "$SINGULARITY_CACHEDIR" "$SINGULARITY_TMPDIR"
singularity pull "$OUT/tiberius_2.0.7.sif" docker://larsgabriel23/tiberius:2.0.7
singularity exec --cleanenv "$OUT/tiberius_2.0.7.sif" /usr/bin/python3 -c 'import tensorflow as tf; import importlib.metadata; print("tensorflow", tf.__version__); print("tiberius", importlib.metadata.version("tiberius"))'
printf '%s\n' "$SLURM_JOB_ID" > "$OUT/JOBID"
printf '%s\n' COMPLETED > "$OUT/STATUS"
