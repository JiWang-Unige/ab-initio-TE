#!/usr/bin/env bash
#SBATCH --job-name=gap-c-runtime
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=logs/gap-c-runtime_%j.out
#SBATCH --error=logs/gap-c-runtime_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
# The login path is a symlink; bind its actual BeeGFS directory, not the alias.
ROOT=$(pwd -P)
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_gap_tiberius_c
OUT="$ROOT/outputs/GAP-BRIDGE-DOWNSTREAM-C-R1/runtime-20260906-r2"
CONTAINER_OUT=/work/te/outputs/GAP-BRIDGE-DOWNSTREAM-C-R1/runtime-20260906-r2
IMAGE="$ROOT/software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1/tiberius_2.0.7.sif"
test -f "$IMAGE"
python scripts/experiments/GAP-BRIDGE-DOWNSTREAM-C-R1/prepare_runtime_smoke.py \
  --masks outputs/GAP-BRIDGE-DOWNSTREAM-C-R1/masks-20260905-r2 \
  --candidate-manifest outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv \
  --output-dir "$OUT"
printf '%s\n' RUNNING > "$OUT/STATUS"
printf 'job=%s\nproject=%s\ncontainer_project=/work/te\nimage=%s\n' "$SLURM_JOB_ID" "$ROOT" "$IMAGE" > "$OUT/env.txt"
singularity exec --nv --cleanenv --env "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" \
  --bind "$ROOT:/work/te" --bind "$ROOT/refs/repos/Tiberius-gap-c-r1:/opt/Tiberius" --pwd /work/te \
  "$IMAGE" /usr/bin/python3 -c 'import sys; from pathlib import Path; import tensorflow as tf; files=[Path(sys.argv[1])/f"{m}.fasta" for m in ("M0","MW","MP")]; assert all(p.is_file() for p in files), files; devices=tf.config.list_physical_devices("GPU"); print("tensorflow",tf.__version__,"GPU",devices,"inputs",files); assert devices, "allocated GPU is not visible to TensorFlow"' "$CONTAINER_OUT"
for MODE in M0 MW MP; do
  /usr/bin/time -v singularity exec --nv --cleanenv \
    --env "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" \
    --bind "$ROOT:/work/te" --bind "$ROOT/refs/repos/Tiberius-gap-c-r1:/opt/Tiberius" --pwd /work/te \
    "$IMAGE" /usr/bin/python3 /opt/Tiberius/tiberius.py \
    --genome "$CONTAINER_OUT/$MODE.fasta" --model_cfg /opt/Tiberius/model_cfg/mammalia_softmasking_v2.yaml \
    --seq_len 400050 --batch_size 1 --out "$CONTAINER_OUT/$MODE.gtf" "$CONTAINER_OUT/$MODE.gff3"
done
printf '%s\n' "$SLURM_JOB_ID" > "$OUT/JOBID"
printf '%s\n' COMPLETED > "$OUT/STATUS"
