#!/usr/bin/env bash
#SBATCH --job-name=gap-c-masks
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/gap-c-masks_%j.out
#SBATCH --error=logs/gap-c-masks_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_gap_tiberius_c
export PYTHONUNBUFFERED=1
python -m unittest discover -s scripts/experiments/GAP-BRIDGE-DOWNSTREAM-C-R1 -p test_build_masks.py -v
python scripts/experiments/GAP-BRIDGE-DOWNSTREAM-C-R1/build_masks.py \
  --region outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1/chr13/region.jsonl.gz \
  --p3-canonical outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1/chr13/prediction.canonical.tsv \
  --candidate-manifest outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv \
  --stage0-json outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/stage0-oracle-20260902-r1/stage0_oracle.json \
  --comparator-positive software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz \
  --stage0-json outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/stage0-oracle-20260902-r1/stage0_oracle.json \
  --halo-bp 100000 --output-dir outputs/GAP-BRIDGE-DOWNSTREAM-C-R1/masks-20260905-r2
