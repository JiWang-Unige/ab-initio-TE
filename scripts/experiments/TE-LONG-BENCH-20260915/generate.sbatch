#!/bin/bash
#SBATCH --job-name=te-long-sim100
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=24:00:00
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/sim-%j.log
set -euo pipefail
TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
TE_SOURCE="$TASK_ROOT/refs/external/TE_Bench-e7b92c5"
TE_DATA="$TASK_ROOT/software_outputs/TE-LONG-BENCH-20260915"
TE_MODEL="$TE_DATA/model-12731809"
TE_SCRIPT=scripts/experiments/TE-LONG-BENCH-20260915
python3 "$TE_SCRIPT/qualify_simulation.py" --prefix "$TE_MODEL/smoke" \
  --expected-bp 1000000 --output-prefix "$TE_MODEL/smoke-qualified-r2"
TE_OUTPUT="$TE_DATA/sim100-$SLURM_JOB_ID"
mkdir "$TE_OUTPUT"
export PERL5LIB="$TASK_ROOT/$TE_SCRIPT"
export PERL5OPT=-MTEBenchSeed PERL_HASH_SEED=42 PERL_PERTURB_KEYS=0
perl "$TE_SOURCE/scripts/createFakeSequence_dfam.pl" -m droMelDFTEST \
  -s 100000000 -N 1 -o "$TE_OUTPUT/sim100" -d "$TE_MODEL" \
  --repbase_file "$TE_DATA/source/Dfam3.9-curated.embl.gz" \
  --useBED --no_simple --write_base \
  > "$TE_OUTPUT/generate.stdout" 2> "$TE_OUTPUT/generate.stderr"
python3 "$TE_SCRIPT/qualify_simulation.py" --prefix "$TE_OUTPUT/sim100" --expected-bp 100000000
