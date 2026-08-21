#!/usr/bin/env bash
#SBATCH --job-name=tefm_t0_sim_audit
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/evidence/t0_simulator_preflight/test_upstream_denovote_simulator.%j.slurm.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/evidence/t0_simulator_preflight/test_upstream_denovote_simulator.%j.slurm.err

set -euo pipefail

/home/users/j/jwang/.conda/envs/te_benchmark/bin/python \
  /home/users/j/jwang/ab-initio-TE/evidence/t0_simulator_preflight/test_upstream_denovote_simulator.py \
  --upstream /home/users/j/jwang/ab-initio-TE/software/external_sources/denovoTE-eval_f735c252
