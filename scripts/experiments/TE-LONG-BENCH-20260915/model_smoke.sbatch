#!/bin/bash
#SBATCH --job-name=te-long-model
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/model-%j.log
set -euo pipefail
TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
TE_SOURCE="$TASK_ROOT/refs/external/TE_Bench-e7b92c5"
TE_OUTPUT="$TASK_ROOT/software_outputs/TE-LONG-BENCH-20260915"
TE_MODEL="$TE_OUTPUT/model-$SLURM_JOB_ID"
mkdir -p "$TE_MODEL"
perl "$TE_SOURCE/scripts/createModel.pl" -v -m droMelDFTEST \
  -f "$TE_SOURCE/input/modeldata/testing/droMelDFTEST.fa" \
  -r "$TE_SOURCE/input/modeldata/testing/droMelDFTEST.dfam.align" \
  -t "$TE_SOURCE/input/modeldata/testing/droMelDFTEST.trf.bed" \
  -g "$TE_SOURCE/input/modeldata/testing/droMelDFTEST.gtf" -d "$TE_MODEL" \
  > "$TE_MODEL/build.stdout" 2> "$TE_MODEL/build.stderr"
export PERL5LIB="$TASK_ROOT/scripts/experiments/TE-LONG-BENCH-20260915"
export PERL5OPT=-MTEBenchSeed PERL_HASH_SEED=42 PERL_PERTURB_KEYS=0
perl "$TE_SOURCE/scripts/createFakeSequence_dfam.pl" -m droMelDFTEST \
  -s 1Mb -N 1 -o "$TE_MODEL/smoke" -d "$TE_MODEL" \
  --repbase_file "$TE_OUTPUT/source/Dfam3.9-curated.embl.gz" \
  --useBED --no_simple --write_base -v \
  > "$TE_MODEL/smoke.stdout" 2> "$TE_MODEL/smoke.stderr"
python3 scripts/experiments/TE-LONG-BENCH-20260915/qualify_simulation.py \
  --prefix "$TE_MODEL/smoke" --expected-bp 1000000
