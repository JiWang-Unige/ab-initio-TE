#!/usr/bin/env bash
# Build the complete six-species ontology dataset on Baobab.
# Heavy source/FASTA I/O is deliberately kept on a CPU Slurm node.
#SBATCH --job-name=sf5_ontology_prep
#SBATCH --partition=shared-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/sf5_ontology_prep_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/sf5_ontology_prep_%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
CODE=${ROOT}/scripts/experiments/SF5-ONTOLOGY-CLOSURE-20260915
MANIFEST=${ROOT}/software_outputs/repeatmasker_dfam/02_ready_by_design/B_animal_production/SPLIT_MANIFEST.tsv
OUT=${ROOT}/software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/data/animal_sf5_ontology_w4096_20260915

if [[ -e "${OUT}/metadata.json" ]]; then
  echo "refusing to overwrite existing ontology dataset: ${OUT}" >&2
  exit 2
fi

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export PYTHONUNBUFFERED=1

python3 "${CODE}/prepare_ontology_data.py" \
  --manifest "${MANIFEST}" \
  --out-dir "${OUT}" \
  --species mouse zebrafish chicken western_clawed_frog fruit_fly c_elegans \
  --window 4096 --step 4096 --max-n-frac 0.2

python3 - "${OUT}/metadata.json" <<'PY'
import json, sys
p = sys.argv[1]
x = json.load(open(p))
expected = {"train": 5400, "val": 1440, "test": 2160}
got = {k: int(v["windows"]) for k, v in x["splits"].items()}
if got != expected:
    raise SystemExit(f"unexpected complete split counts: {got} != {expected}")
print(json.dumps({"status": "PASS", "windows": got}))
PY

printf '%s\n' "${SLURM_JOB_ID}" > "${OUT}/PREP_JOBID"
printf '%s\n' 'PASS' > "${OUT}/PREP_STATUS"
