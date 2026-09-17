#!/usr/bin/env bash
#SBATCH --job-name=external_ltr_evidence
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=logs/external_ltr_evidence_%j.log
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
SPECIES=${1:?species is required}
WORK="$ROOT/outputs/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/$SPECIES/structure-$SLURM_JOB_ID"
mkdir -p "$WORK/home" "$WORK/tmp"
cp "$ROOT/outputs/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/$SPECIES/prepared/panel.fa" "$WORK/panel.fa"
IMAGE="$ROOT/container_candidates/E1B-OCI-ACQUIRE-20260809A/edta_2_3_0.sif"
SOURCE="$ROOT/software_outputs/tefm_new_directions/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/edta/source-2.3.0"
cd "$WORK"
set +e
timeout --kill-after=30s 7000 /usr/bin/time -v -o native.time \
  apptainer exec --cleanenv --pwd /work --bind "$WORK:/work" --bind "$SOURCE:/opt/edta230:ro" \
  "$IMAGE" env HOME=/work/home TMPDIR=/work/tmp OMP_NUM_THREADS=4 \
  perl /opt/edta230/EDTA_raw.pl --genome /work/panel.fa --type ltr \
  --species others --threads 4 --convert_seq_name 0 --overwrite 1 \
  > native.stdout 2> native.stderr
NATIVE_EXIT=$?
set -e
printf '%s\n' "$NATIVE_EXIT" > native.exit_code
exit "$NATIVE_EXIT"
