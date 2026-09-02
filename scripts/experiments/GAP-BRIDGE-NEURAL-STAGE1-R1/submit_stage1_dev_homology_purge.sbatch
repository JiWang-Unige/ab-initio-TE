#!/usr/bin/env bash
# Label-blind Stage 1 DEV-to-TRAIN flank homology membership; CPU only.
# The manifest and three source regions are explicit; no sealed-test sequence is read.
#SBATCH --job-name=gap-s1-dev-purge
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=logs/gap-neural-s1-dev-purge_%j.out
#SBATCH --error=logs/gap-neural-s1-dev-purge_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_dev_homology_purge.py
MANIFEST=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG for Stage 1 DEV purge}"
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/dev-homology-purge-${ATTEMPT_TAG}

for required_path in \
  "${SCRIPT}" \
  "/home/users/j/jwang/.conda/envs/edta_native/bin/minimap2" \
  "${MANIFEST}" \
  "${SOURCE_ROOT}/chr3/region.jsonl.gz" \
  "${SOURCE_ROOT}/chr5/region.jsonl.gz" \
  "${SOURCE_ROOT}/chr13/region.jsonl.gz"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing Stage 1 DEV purge asset: ${required_path}" >&2
    exit 2
  fi
done
if [[ -e "${RUN_ROOT}" ]]; then
  echo "refusing to reuse Stage 1 DEV purge output: ${RUN_ROOT}" >&2
  exit 2
fi

MINIMAP2=/home/users/j/jwang/.conda/envs/edta_native/bin/minimap2
LOCAL_SCRATCH=${SLURM_TMPDIR:-/tmp}
TASK_ROOT=$(mktemp -d "${LOCAL_SCRATCH}/te-gap-s1-dev-purge-${SLURM_JOB_ID}-XXXXXX")
trap 'rm -rf "${TASK_ROOT}"' EXIT

mkdir -p "${TASK_ROOT}/input" "${TASK_ROOT}/result"
cp "${MANIFEST}" "${TASK_ROOT}/input/candidate_manifest.tsv"
for seqid in chr3 chr5 chr13; do
  cp "${SOURCE_ROOT}/${seqid}/region.jsonl.gz" "${TASK_ROOT}/input/${seqid}.region.jsonl.gz"
done

python3 "${SCRIPT}" export-flanks \
  --manifest "${TASK_ROOT}/input/candidate_manifest.tsv" \
  --region-jsonl "${TASK_ROOT}/input/chr3.region.jsonl.gz" \
  --role TRAIN \
  --output-fasta "${TASK_ROOT}/chr3.train.fa"
python3 "${SCRIPT}" export-flanks \
  --manifest "${TASK_ROOT}/input/candidate_manifest.tsv" \
  --region-jsonl "${TASK_ROOT}/input/chr5.region.jsonl.gz" \
  --role TRAIN \
  --output-fasta "${TASK_ROOT}/chr5.train.fa"
cat "${TASK_ROOT}/chr3.train.fa" "${TASK_ROOT}/chr5.train.fa" > "${TASK_ROOT}/train.fa"

python3 "${SCRIPT}" export-flanks \
  --manifest "${TASK_ROOT}/input/candidate_manifest.tsv" \
  --region-jsonl "${TASK_ROOT}/input/chr13.region.jsonl.gz" \
  --role DEV \
  --output-fasta "${TASK_ROOT}/dev.fa"

"${MINIMAP2}" -x sr --secondary=no -t "${SLURM_CPUS_PER_TASK}" \
  "${TASK_ROOT}/train.fa" "${TASK_ROOT}/dev.fa" > "${TASK_ROOT}/dev-to-train.paf"

python3 "${SCRIPT}" summarize-paf \
  --manifest "${TASK_ROOT}/input/candidate_manifest.tsv" \
  --paf "${TASK_ROOT}/dev-to-train.paf" \
  --output-tsv "${TASK_ROOT}/result/dev_purge_membership.tsv" \
  --output-json "${TASK_ROOT}/result/dev_purge_census.json"

"${MINIMAP2}" --version > "${TASK_ROOT}/result/minimap2.version.txt"
printf '%s\n' 'DEV query chr13 -> TRAIN target chr3/chr5; minimap2 -x sr --secondary=no; flank=256; identity>=0.80; reciprocal_coverage>=0.50; aligned_bp>=100' > "${TASK_ROOT}/result/CONTRACT"
printf '%s\n' "${SLURM_JOB_ID}" > "${TASK_ROOT}/result/JOBID"
printf 'PASS\n' > "${TASK_ROOT}/result/STATUS"

mkdir -p "$(dirname "${RUN_ROOT}")"
TRANSFER_ROOT=$(dirname "${RUN_ROOT}")/.transfer-dev-purge-${SLURM_JOB_ID}
mkdir "${TRANSFER_ROOT}"
cp -a "${TASK_ROOT}/result/." "${TRANSFER_ROOT}/"
mv "${TRANSFER_ROOT}" "${RUN_ROOT}"
