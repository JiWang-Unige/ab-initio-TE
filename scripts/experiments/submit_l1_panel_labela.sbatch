#!/usr/bin/env bash
# Label preparation only: exact approved assemblies, historical Label-A semantics.
#SBATCH --job-name=L1_PANEL_LABELA
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=7-00:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/L1-PANEL-LABELA-20260908-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/L1-PANEL-LABELA-20260908-%A_%a.err

set -euo pipefail
ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
INPUT=${ROOT}/software_outputs/L1-PANEL-PREP-20260908-kqZrej
HIST=${ROOT}/software_outputs/repeatmasker_dfam/raw_runs/self_labelA/RMDFAM_FULLPARTITIONS_RERUN_20260617/rm_lib_overlay
SHARE=/home/users/j/jwang/.conda/envs/te_benchmark/share/RepeatMasker
export PATH=/home/users/j/jwang/.conda/envs/te_benchmark/bin:${PATH}
case "${SLURM_ARRAY_TASK_ID}" in
  0) STEM=GCF_004115215.2_mOrnAna1.pri.v4; SPECIES='Ornithorhynchus anatinus';;
  1) STEM=GCF_000002235.5_Spur_5.0; SPECIES='Strongylocentrotus purpuratus';;
  2) STEM=GCA_000004555.3_CB4; SPECIES='Caenorhabditis briggsae';;
  *) exit 2;;
esac
RUN=${INPUT}/labela-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
# Exclusive directory protects existing attempts and their failure evidence.
mkdir "${RUN}"
mkdir "${RUN}/RepeatMasker" "${RUN}/Libraries" "${RUN}/Libraries/CONS-Dfam_3.9" "${RUN}/annotation"
find "${SHARE}" -maxdepth 1 -type f -exec cp -p '{}' "${RUN}/RepeatMasker/" \;
# Historical Label-A jobs materialized matrices; do not depend on a live home link.
cp -RL "${SHARE}/Matrices" "${RUN}/RepeatMasker/Matrices"
test -r "${RUN}/RepeatMasker/Matrices/crossmatch/simple1.matrix"
test -r "${RUN}/RepeatMasker/Matrices/crossmatch/18p35g.matrix"
ln -s "${RUN}/Libraries" "${RUN}/RepeatMasker/Libraries"
find "${HIST}" -mindepth 1 -maxdepth 1 ! -name 'CONS-Dfam_3.9' -exec ln -s '{}' "${RUN}/Libraries/" \;
export LIBDIR=${RUN}/Libraries
export TMPDIR=${RUN}/tmp
mkdir "${TMPDIR}"
python - "${HIST}/famdb/dfam39_full.0.h5" <<'PY'
import h5py, sys
with h5py.File(sys.argv[1], 'r') as f:
    assert str(f.attrs['db_name']) == 'Dfam'
    assert str(f.attrs['db_version']) == '3.9'
PY
VERSION=$("${RUN}/RepeatMasker/RepeatMasker" -v)
test "${VERSION}" = 'RepeatMasker version 4.2.2'
printf '%s\n' "assembly=${STEM}" "species=${SPECIES}" "source=${INPUT}/${STEM}_genomic.fna.gz" \
  "version=${VERSION}" "library=${HIST}/famdb" 'Dfam=3.9' \
  "command=-pa 4 -xsmall -gff -species ${SPECIES}; no -a" \
  "job=${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" > "${RUN}/RUN_METADATA.txt"
gzip -dc "${INPUT}/${STEM}_genomic.fna.gz" > "${RUN}/assembly.fa"
"${RUN}/RepeatMasker/RepeatMasker" -pa 4 -xsmall -gff -species "${SPECIES}" \
  -dir "${RUN}/annotation" "${RUN}/assembly.fa" > "${RUN}/repeatmasker.log" 2>&1
# RepeatMasker can emit this Matrix parsing error yet return zero; such output
# omits TRF processing and is not a valid Label-A materialization.
if grep -Fq 'Matrix::Matrix::parseFromFile:' "${RUN}/repeatmasker.log"; then
  printf '%s\n' 'RepeatMasker matrix parsing failed; retaining incomplete outputs.' >&2
  exit 1
fi
test -s "${RUN}/annotation/assembly.fa.out"
test -s "${RUN}/annotation/assembly.fa.tbl"
test -s "${RUN}/annotation/assembly.fa.out.gff"
printf 'LABEL_GENERATION_COMPLETED_NOT_SCIENTIFIC_PASS\n' > "${RUN}/STATUS"
