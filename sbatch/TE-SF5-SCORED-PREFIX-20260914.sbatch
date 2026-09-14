#!/usr/bin/env bash
#SBATCH --job-name=te_sf5_prefix_audit
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_sf5_prefix_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_sf5_prefix_%j.err
set -euo pipefail
ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
cd "$ROOT"
python3 scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/audit_scored_prefix.py --root "$ROOT" \
 --output "$ROOT/outputs/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/scored-prefix-${SLURM_JOB_ID}.json"
