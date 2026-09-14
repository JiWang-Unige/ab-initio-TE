#!/usr/bin/env bash
#SBATCH --job-name=te-hg19-native
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/te-hg19-native_%j.out
#SBATCH --error=logs/te-hg19-native_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
DATA_DIR=${1:?prepared data path required}
MODE=${2:-smoke}
SMOKE_DIR=${3:-}
CFG=configs/HG19-CHR1-REVISION-20260914.json
if [[ "$MODE" == smoke ]]; then
  EXTRA=(--smoke)
elif [[ "$MODE" == full ]]; then
  test -n "$SMOKE_DIR"
  python3 - "$SMOKE_DIR" "$DATA_DIR" <<'PY'
import json,sys
from pathlib import Path
s=Path(sys.argv[1]);c=json.loads((s/'completion.json').read_text());m=json.loads((s/'training_meta.json').read_text())
assert c['status']=='ENGINEERING_SMOKE_PASS' and c['steps']==2
assert Path(m['data_root']).resolve()==Path(sys.argv[2]).resolve()
assert m['protocol']=='HG19-CHR1-REVISION-20260914' and m['species']==['human']
PY
  EXTRA=()
else
  echo "MODE must be smoke or full" >&2
  exit 2
fi
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=8
python scripts/experiments/HG19-CHR1-REVISION-20260914/train.py --config "$CFG" --data "$DATA_DIR" --output "outputs/HG19-CHR1-REVISION-20260914/${MODE}-${SLURM_JOB_ID}" "${EXTRA[@]}"
