#!/bin/bash
#SBATCH --job-name=te_braker_score_arm
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/BRAKER-MASK-UTILITY-20260925/logs/%x-%j.out
#SBATCH --error=outputs/BRAKER-MASK-UTILITY-20260925/logs/%x-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
python3 -u - "$@" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

species, *arms = sys.argv[1:]
if not arms:
    raise ValueError('Provide at least one completed arm')
root = Path('outputs/BRAKER-MASK-UTILITY-20260925')
arm_args = []
for arm in arms:
    status = json.loads((root / species / 'arms' / arm / 'status.json').read_text())
    if status['status'] != 'PREDICTION_READY':
        raise ValueError('Score only a completed native prediction: ' + arm)
    arm_args.extend(['--arm', arm + '=' + status['final_gtf']])
preparation = json.loads((root / 'evaluation/preparation.json').read_text())
evaluation = Path(preparation['species'][species]['evaluation_dir'])
for domain in ('primary', 'full'):
    subprocess.run([
        sys.executable, '-u', 'scripts/experiments/BRAKER-MASK-UTILITY-20260925/evaluation.py',
        'score', '--species', species, '--evaluation-dir', str(evaluation),
        '--domain', domain, *arm_args,
        '--output', str(evaluation / ('score-' + '-'.join(arms) + '-' + domain + '.json')),
    ], check=True)
PY
