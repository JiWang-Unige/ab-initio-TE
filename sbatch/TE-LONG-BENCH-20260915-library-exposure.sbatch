#!/bin/bash
# Bounded reference-library exposure audit.  Full parsing runs on CPU Slurm;
# no native caller/model is rerun and no sealed real-genome labels are read.
#SBATCH --job-name=te_library_exposure
#SBATCH --partition=public-short-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=te_library_exposure_%j.out
#SBATCH --error=te_library_exposure_%j.err

set -euo pipefail

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

repo_root="${TE_LONG_REPO_ROOT:-/home/users/j/jwang/ab-initio-TE}"
source_root="${TE_LONG_SOURCE_ROOT:-$repo_root/software_outputs/TE-LONG-BENCH-20260915}"
output_root="${TE_LONG_OUTPUT_ROOT:-$repo_root/outputs/TE-LONG-BENCH-20260915}"
qualification_path="${TE_LONG_QUALIFICATION:-$source_root/sim100-12731886/sim100.qualification.json}"
embl_path="${TE_LONG_EMBL:-$source_root/source/Dfam3.9-curated.embl.gz}"
library_path="${TE_LONG_LIBRARY:-$output_root/native-12731947/sim100-fixed_rm/work/lineage.fa}"
truth_path="${TE_LONG_TRUTH:-$source_root/sim100-12731886/sim100.truth.tsv}"
output_dir="${TE_LONG_EXPOSURE_OUTPUT:-$repo_root/reports/TE-LONG-BENCH-20260915/library-exposure/run_${SLURM_JOB_ID}}"
source_path="$repo_root/scripts/experiments/TE-LONG-BENCH-20260915/library_exposure.py"

if [[ ! -f "$source_path" || ! -f "$qualification_path" || ! -f "$embl_path" || ! -f "$library_path" || ! -f "$truth_path" ]]; then
  echo "required qualification, Dfam EMBL, fixed RM library, truth, or source is missing" >&2
  exit 2
fi

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export PYTHONUNBUFFERED=1

python3 "$source_path" \
  --qualification "$qualification_path" \
  --embl "$embl_path" \
  --library "$library_path" \
  --truth "$truth_path" \
  --output-dir "$output_dir"
