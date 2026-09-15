#!/usr/bin/env bash
# Train the new eight-label head and evaluate full validation/test coverage.
#SBATCH --job-name=sf5_ontology_train
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/sf5_ontology_train_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/sf5_ontology_train_%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
CODE=${ROOT}/scripts/experiments/SF5-ONTOLOGY-CLOSURE-20260915
DATA=${ROOT}/software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/data/animal_sf5_ontology_w4096_20260915
INIT=/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base
RUN=${ROOT}/software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/runs/SF5_ONTOLOGY_CLOSURE_base_seed42_${SLURM_JOB_ID}
REPORT=${ROOT}/reports/SF5-ONTOLOGY-CLOSURE-20260915/run-${SLURM_JOB_ID}
OLD=${ROOT}/software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/runs/SF5_base_pretrained_seed42

for required in "${CODE}/ontology_task.py" "${CODE}/evaluate_legacy_baseline.py" \
  "${DATA}/metadata.json" "${DATA}/train/data.jsonl.gz" \
  "${DATA}/val/data.jsonl.gz" "${DATA}/test/data.jsonl.gz" \
  "${INIT}/config.json" "${OLD}/best_model"; do
  [[ -e "${required}" ]] || { echo "missing SF5 ontology asset: ${required}" >&2; exit 2; }
done
if [[ -e "${RUN}" ]]; then
  echo "refusing to reuse training output: ${RUN}" >&2
  exit 2
fi

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export TRANSFORMERS_OFFLINE=1
export TEFM_LOCAL_FILES_ONLY=1
export WANDB_DISABLED=true
export PYTHONUNBUFFERED=1

python3 -m unittest discover -s "${CODE}" -p 'test_ontology_contract.py'

mkdir -p "${REPORT}"
python3 "${CODE}/ontology_task.py" train \
  --init-checkpoint "${INIT}" \
  --data-dir "${DATA}" \
  --output-dir "${RUN}" \
  --window 4096 --seed 42 --batch-size 1 --grad-accum 16 \
  --learning-rate 2e-5 --max-steps 900 --eval-steps 150 \
  --bf16 --gradient-checkpointing

python3 "${CODE}/evaluate_legacy_baseline.py" \
  --model-dir "${OLD}" \
  --data-dir "${DATA}" \
  --out-json "${REPORT}/legacy_collapsed_full_test.json" \
  --window 4096 --batch-size 1

cp "${DATA}/metadata.json" "${REPORT}/dataset_metadata.json"
cp "${DATA}/label_map.json" "${REPORT}/label_map.json"
cp "${RUN}/training_meta.json" "${REPORT}/training_meta.json"
cp "${RUN}/validation_results.json" "${REPORT}/validation_results.json"
cp "${RUN}/test_results.json" "${REPORT}/test_results.json"
python3 - "${REPORT}/status.json" "${RUN}" "${DATA}" <<'PY'
import json, pathlib, sys
out, run, data = map(pathlib.Path, sys.argv[1:])
meta = json.loads((data / "metadata.json").read_text())
status = {
    "status": "COMPLETED",
    "job_id": "__SLURM_JOB_ID__",
    "run_dir": str(run),
    "data_dir": str(data),
    "split_windows": {k: int(v["windows"]) for k, v in meta["splits"].items()},
    "full_validation": True,
    "full_test": True,
}
out.write_text(json.dumps(status, indent=2) + "\n")
PY
sed -i "s/__SLURM_JOB_ID__/${SLURM_JOB_ID}/" "${REPORT}/status.json"
printf '%s\n' "${SLURM_JOB_ID}" > "${REPORT}/JOBID"
printf '%s\n' 'COMPLETED' > "${REPORT}/STATUS"
