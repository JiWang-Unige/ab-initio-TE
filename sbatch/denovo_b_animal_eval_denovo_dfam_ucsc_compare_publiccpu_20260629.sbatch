#!/usr/bin/env bash
# Compare de novo+Dfam augmented B-eval annotations against UCSC strict TE.
#SBATCH --job-name=DENOVO_DFAM_B_CMP
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/denovo_dfam_cmp_20260629/slurm_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/denovo_dfam_cmp_20260629/slurm_%j.err

set -euo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
RUN_ROOT=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
READY_MANIFEST=/home/users/j/jwang/ab-initio-TE/software_outputs/repeatmasker_dfam/02_ready_by_design/manifests/MANIFEST_ALL.tsv
OUT_DIR=${RUN_ROOT}/denovo_dfam_vs_ucsc_B_eval_20260629
MANIFEST=${OUT_DIR}/pair_manifest.tsv
LOG_DIR=${RUN_ROOT}/slurm_logs/denovo_dfam_cmp_20260629

mkdir -p "${OUT_DIR}" "${LOG_DIR}"

cd "${PROJECT_ROOT}"

python3 scripts/experiments/denovo_benchmark/build_denovo_dfam_ucsc_manifest.py \
  --ready-manifest "${READY_MANIFEST}" \
  --run-root "${RUN_ROOT}" \
  --out "${MANIFEST}"

python3 scripts/experiments/denovo_benchmark/compare_denovo_ucsc.py \
  --manifest "${MANIFEST}" \
  --jobs 1 \
  --outdir "${OUT_DIR}"

python3 scripts/experiments/denovo_benchmark/finalize_denovo_ucsc_report.py \
  --manifest "${MANIFEST}" \
  --outdir "${OUT_DIR}"
