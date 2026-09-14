#!/bin/bash
# Local/compute-node engineering fixture only.  No natural data or training.
#SBATCH --job-name=frag_link_p1
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=frag_link_p1_%j.out
#SBATCH --error=frag_link_p1_%j.err

set -euo pipefail

project_root="${TE_PROJECT_ROOT:-$PWD}"
output_dir="${TE_FRAGMENT_LINKING_OUT:-$project_root/reports/FRAGMENT-LINKING-PHASE1-20260914/slurm_%j}"
script="$project_root/scripts/experiments/FRAGMENT-LINKING-PHASE1-20260914/fragment_linking_phase1.py"
if [[ ! -f "$script" ]]; then
  echo "missing Phase 1 script: $script" >&2
  exit 2
fi
python3 "$script" --out-dir "$output_dir"
