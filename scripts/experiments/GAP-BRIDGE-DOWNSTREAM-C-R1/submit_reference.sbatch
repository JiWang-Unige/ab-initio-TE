#!/usr/bin/env bash
#SBATCH --job-name=gap-c-reference
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=logs/gap-c-reference_%j.out
#SBATCH --error=logs/gap-c-reference_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_gap_tiberius_c
OUT=outputs/GAP-BRIDGE-DOWNSTREAM-C-R1/reference-20260905-r1
test ! -e "$OUT"
mkdir "$OUT"
python -m unittest discover -s scripts/experiments/GAP-BRIDGE-DOWNSTREAM-C-R1 -p test_evaluate_chains.py -v
python scripts/experiments/GAP-BRIDGE-DOWNSTREAM-C-R1/evaluate_chains.py --reference-only \
  --geometry outputs/GAP-BRIDGE-DOWNSTREAM-C-R1/masks-20260905-r2/geometry.tsv \
  --refseq data/raw/ucsc/human/hg38/genes/ncbiRefSeqCurated-20250813.txt.gz \
  --output "$OUT/reference_chains.json"
printf '%s\n' "$SLURM_JOB_ID" > "$OUT/JOBID"
printf '%s\n' COMPLETED > "$OUT/STATUS"
