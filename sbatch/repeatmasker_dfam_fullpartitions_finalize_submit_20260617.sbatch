#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_FULLPART_PREP
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_FULLPART_PREP_20260617_%j.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_FULLPART_PREP_20260617_%j.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_FULLPARTITIONS_RERUN_20260617}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
RUN_ROOT="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/raw_runs/self_labelA/${RUN_ID}"
FAMDB="${FAMDB:-${RUN_ROOT}/famdb_fullpartitions}"
RM_LIBRARIES="${RM_LIBRARIES:-/home/users/j/jwang/.conda/envs/te_benchmark/share/RepeatMasker/Libraries}"
OVERLAY="${RUN_ROOT}/rm_lib_overlay"
SPECIES_TABLE="${PROJECT_ROOT}/configs/${RUN_ID}/species_table.tsv"
REPORT_DIR="${PROJECT_ROOT}/reports/repeatmasker_dfam/${RUN_ID}"
PARTS=(1 2 3 4 5 6 12 13 15)

cd "${PROJECT_ROOT}"
mkdir -p logs/repeatmasker_dfam "${REPORT_DIR}" "${RUN_ROOT}"

for p in "${PARTS[@]}"; do
  h5="${FAMDB}/dfam39_full.${p}.h5"
  if [[ ! -s "${h5}" ]]; then
    echo "Missing required FamDB h5 partition: ${h5}" >&2
    exit 2
  fi
done

python3 scripts/experiments/update_famdb_rmlib_config.py \
  --famdb-dir "${FAMDB}" \
  --backup-suffix "${RUN_ID}"

python3 scripts/experiments/prepare_repeatmasker_fullpartition_overlay.py \
  --repeatmasker-libraries "${RM_LIBRARIES}" \
  --overlay "${OVERLAY}" \
  --famdb-dir "${FAMDB}" \
  --force

python3 scripts/experiments/prebuild_repeatmasker_specieslibs.py \
  --species-table "${SPECIES_TABLE}" \
  --overlay "${OVERLAY}" \
  --probe-root "${RUN_ROOT}/specieslib_probe" \
  --summary-out "${REPORT_DIR}/specieslib_prebuild_summary.tsv" \
  --parallel 1 \
  --min-bytes 1 \
  --min-records 1

python3 scripts/pre_submit_gate.py --exp-id repeatmasker_dfam_fullpartitions_chunks_20260617 "${PROJECT_ROOT}"
python3 scripts/pre_submit_gate.py --exp-id repeatmasker_dfam_fullpartitions_merge_20260617 "${PROJECT_ROOT}"
python3 scripts/pre_submit_gate.py --exp-id repeatmasker_dfam_fullpartitions_qc_20260617 "${PROJECT_ROOT}"

chunk_job="$(
  sbatch --parsable \
    -p shared-cpu \
    --time=12:00:00 \
    --array=1-495%72 \
    sbatch/repeatmasker_dfam_fullpartitions_chunks_20260617.sbatch
)"
echo "${chunk_job}" > "${RUN_ROOT}/CHUNK_JOBID"
echo "submitted_chunk_job=${chunk_job}"

merge_job="$(
  sbatch --parsable \
    -p shared-cpu \
    --time=12:00:00 \
    --dependency=afterok:${chunk_job} \
    sbatch/repeatmasker_dfam_fullpartitions_merge_20260617.sbatch
)"
echo "${merge_job}" > "${RUN_ROOT}/MERGE_JOBID"
echo "submitted_merge_job=${merge_job}"

qc_job="$(
  sbatch --parsable \
    -p shared-cpu \
    --time=04:00:00 \
    --dependency=afterok:${merge_job} \
    sbatch/repeatmasker_dfam_fullpartitions_qc_20260617.sbatch
)"
echo "${qc_job}" > "${RUN_ROOT}/QC_JOBID"
echo "submitted_qc_job=${qc_job}"

touch "${RUN_ROOT}/SUBMITTED_ANNOTATION_CHAIN"
