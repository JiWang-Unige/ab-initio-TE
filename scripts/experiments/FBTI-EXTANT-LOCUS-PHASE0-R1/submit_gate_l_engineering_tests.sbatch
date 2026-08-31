#!/usr/bin/env bash
# Exercise the complete machine-side Gate-L implementation in the cluster runtime.
#SBATCH --job-name=FBTI_L_TEST
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/gate-l-tests-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/gate-l-tests-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submission}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

ROOT=/home/users/j/jwang/ab-initio-TE
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/gate-l-engineering-tests-${ATTEMPT_TAG}

mkdir "${OUT}"
cd "${ROOT}"
python -m unittest \
  scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/test_build_provenance_audit.py \
  scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/test_assemble_gate_l_delivery.py \
  scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/test_validate_gate_l_pass1.py \
  scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/test_project_gate_l_atoms.py \
  scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/test_gate_l_end_to_end.py \
  scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/test_evaluate_gate_l_reproducibility.py \
  scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/test_evaluate_gate_l_lp_ld.py \
  -v > "${OUT}/unittest.log" 2>&1

printf '%s\n' "${SLURM_JOB_ID}" > "${OUT}/JOBID"
printf 'PASS\n' > "${OUT}/STATUS"
