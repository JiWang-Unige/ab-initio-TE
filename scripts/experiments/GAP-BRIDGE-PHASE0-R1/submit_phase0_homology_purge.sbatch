#!/usr/bin/env bash
# Label-blind homology-purge membership, run after whole-chromosome stitching.
#SBATCH --job-name=TE_GAP_PURGE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/purge-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/purge-%j.err

set -euo pipefail

: "${SOURCE_TAG:?set SOURCE_TAG to the completed whole-chromosome attempt}"
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG for purge membership}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_homology_purge.py
MINIMAP2=/home/users/j/jwang/.conda/envs/edta_native/bin/minimap2
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-${SOURCE_TAG}
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/homology-purge-${ATTEMPT_TAG}

for required_path in \
  "${SCRIPT}" \
  "${MINIMAP2}" \
  "${SOURCE_ROOT}/chr3/candidates.tsv" \
  "${SOURCE_ROOT}/chr3/region.jsonl.gz" \
  "${SOURCE_ROOT}/chr5/candidates.tsv" \
  "${SOURCE_ROOT}/chr5/region.jsonl.gz" \
  "${SOURCE_ROOT}/chr13/candidates.tsv" \
  "${SOURCE_ROOT}/chr13/region.jsonl.gz" \
  "${SOURCE_ROOT}/chr19/candidates.tsv" \
  "${SOURCE_ROOT}/chr19/region.jsonl.gz" \
  "${SOURCE_ROOT}/chr19/TEST_LABELS_SEALED"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing homology-purge asset: ${required_path}" >&2
    exit 2
  fi
done
if [[ -e "${SOURCE_ROOT}/chr19/labeled.tsv" ]]; then
  echo "chr19 labels exist before homology-purge membership" >&2
  exit 2
fi
if [[ -e "${RUN_ROOT}" ]]; then
  echo "refusing to reuse homology-purge output: ${RUN_ROOT}" >&2
  exit 2
fi

LOCAL_SCRATCH=${SLURM_TMPDIR:-/tmp}
TASK_ROOT=$(mktemp -d "${LOCAL_SCRATCH}/te-gap-purge-${SLURM_JOB_ID}-XXXXXX")
trap 'rm -rf "${TASK_ROOT}"' EXIT

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

for seqid in chr3 chr5 chr13; do
  python3 "${SCRIPT}" export-flanks \
    --candidates "${SOURCE_ROOT}/${seqid}/candidates.tsv" \
    --region-jsonl "${SOURCE_ROOT}/${seqid}/region.jsonl.gz" \
    --role train \
    --output-fasta "${TASK_ROOT}/${seqid}.fa"
done
cat "${TASK_ROOT}/chr3.fa" "${TASK_ROOT}/chr5.fa" "${TASK_ROOT}/chr13.fa" > "${TASK_ROOT}/train.fa"

python3 "${SCRIPT}" export-flanks \
  --candidates "${SOURCE_ROOT}/chr19/candidates.tsv" \
  --region-jsonl "${SOURCE_ROOT}/chr19/region.jsonl.gz" \
  --role test \
  --output-fasta "${TASK_ROOT}/chr19.fa"

"${MINIMAP2}" -x sr --secondary=no -t "${SLURM_CPUS_PER_TASK}" \
  "${TASK_ROOT}/train.fa" "${TASK_ROOT}/chr19.fa" > "${TASK_ROOT}/flanks.paf"

mkdir "${TASK_ROOT}/result"
python3 "${SCRIPT}" summarize-paf \
  --candidates "${SOURCE_ROOT}/chr19/candidates.tsv" \
  --paf "${TASK_ROOT}/flanks.paf" \
  --output-tsv "${TASK_ROOT}/result/purge_membership.tsv" \
  --output-json "${TASK_ROOT}/result/purge_census.json"

"${MINIMAP2}" --version > "${TASK_ROOT}/result/minimap2.version.txt"
printf '%s\n' 'minimap2 -x sr --secondary=no; flank=256; identity>=0.80; reciprocal_coverage>=0.50; aligned_bp>=100' > "${TASK_ROOT}/result/CONTRACT"
printf '%s\n' "${SLURM_JOB_ID}" > "${TASK_ROOT}/result/JOBID"
printf 'PASS\n' > "${TASK_ROOT}/result/STATUS"

mkdir -p "$(dirname "${RUN_ROOT}")"
TRANSFER_ROOT=$(dirname "${RUN_ROOT}")/.transfer-purge-${SLURM_JOB_ID}
mkdir "${TRANSFER_ROOT}"
cp -a "${TASK_ROOT}/result/." "${TRANSFER_ROOT}/"
mv "${TRANSFER_ROOT}" "${RUN_ROOT}"
