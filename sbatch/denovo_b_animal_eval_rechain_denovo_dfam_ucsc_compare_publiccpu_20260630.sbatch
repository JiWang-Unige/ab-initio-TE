#!/usr/bin/env bash
# Compare de novo+Dfam augmented B-eval annotations against UCSC strict TE.
#SBATCH --job-name=DENOVO_DFAM_B_CMP_R2
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/rechain_20260630/dfam_cmp_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/rechain_20260630/dfam_cmp_%j.err

set -euo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
RUN_ROOT=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
READY_MANIFEST=/home/users/j/jwang/ab-initio-TE/software_outputs/repeatmasker_dfam/02_ready_by_design/manifests/MANIFEST_ALL.tsv
MANIFEST=${RUN_ROOT}/denovo_dfam_ucsc_manifest_full_20260630.tsv
OUT_DIR=${RUN_ROOT}/dfam_augmented/ucsc_compare_full_20260630

mkdir -p "${OUT_DIR}" "${RUN_ROOT}/slurm_logs/rechain_20260630"
cd "${PROJECT_ROOT}"

python3 scripts/experiments/denovo_benchmark/build_denovo_dfam_ucsc_manifest.py \
  --ready-manifest "${READY_MANIFEST}" \
  --run-root "${RUN_ROOT}" \
  --out "${MANIFEST}"

python3 scripts/experiments/denovo_benchmark/compare_denovo_ucsc.py \
  --manifest "${MANIFEST}" \
  --jobs "${SLURM_CPUS_PER_TASK:-8}" \
  --outdir "${OUT_DIR}"

python3 scripts/experiments/denovo_benchmark/finalize_denovo_ucsc_report.py \
  --manifest "${MANIFEST}" \
  --outdir "${OUT_DIR}"
