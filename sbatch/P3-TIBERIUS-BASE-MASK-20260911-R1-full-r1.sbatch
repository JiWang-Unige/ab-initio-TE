#!/usr/bin/env bash
#SBATCH --job-name=p3-base-mask-full-r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=48:00:00
#SBATCH --output=logs/p3-base-mask-full-r1_%j.out
#SBATCH --error=logs/p3-base-mask-full-r1_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
TASK_ROOT=$(pwd -P)
CFG=configs/P3-TIBERIUS-BASE-MASK-20260911-R1.json
RUN=full
REVISION=r1
SCRIPT=scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py
OBS=scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/observed_tiberius.py
OUT=outputs/P3-TIBERIUS-BASE-MASK-20260911-R1/${RUN}-${REVISION}
IMAGE="$TASK_ROOT/software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1/tiberius_2.0.7.sif"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME="$TASK_ROOT/.cache/huggingface"

test "$(git -C refs/repos/Tiberius-gap-c-r1 rev-parse HEAD)" = 4d657012a3ed4e923f5d0ac5cef65fecae8109bd
test -d outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
test ! -e "$OUT"
python -m unittest scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/test_base_mask.py -v
python "$SCRIPT" prepare --config "$CFG" --run "$RUN" --revision "$REVISION"

for CHROM in chr16 chr18; do
  for INDEX in {0..9}; do
    CORE="$CHROM:$INDEX"
    python "$SCRIPT" run-core --config "$CFG" --run "$RUN" --revision "$REVISION" --core "$CORE"
  done
done

container=(singularity exec --nv --cleanenv --env "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" --bind "$TASK_ROOT:/work/te" --bind "$TASK_ROOT/refs/repos/Tiberius-gap-c-r1:/opt/Tiberius" --pwd /work/te "$IMAGE" /usr/bin/python3)
for CHROM in chr16 chr18; do
  for INDEX in {0..9}; do
    CORE="$CHROM:$INDEX"
    "${container[@]}" "/work/te/$SCRIPT" preflight-core --config "/work/te/$CFG" --run "$RUN" --revision "$REVISION" --core "$CORE"
  done
done

for CHROM in chr16 chr18; do
  for INDEX in {0..9}; do
    CORE="$CHROM:$INDEX"
    CELL="$OUT/core-$CHROM-$INDEX"
    for MODE in U P R; do
      printf 'START core=%s mode=%s\n' "$CORE" "$MODE"
      mode_container=(singularity exec --nv --cleanenv \
        --env "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" \
        --env "BASE_MASK_OBSERVATION=/work/te/$CELL/$MODE.observation.json" \
        --bind "$TASK_ROOT:/work/te" \
        --bind "$TASK_ROOT/refs/repos/Tiberius-gap-c-r1:/opt/Tiberius" \
        --pwd /work/te "$IMAGE" /usr/bin/python3)
      "${mode_container[@]}" "/work/te/$OBS" \
        --genome "/work/te/$CELL/$MODE.fasta" \
        --model_cfg /opt/Tiberius/model_cfg/mammalia_softmasking_v2.yaml \
        --seq_len 400050 --batch_size 1 \
        --out "/work/te/$CELL/$MODE.gtf" "/work/te/$CELL/$MODE.gff3" \
        > "$CELL/$MODE.stdout.log" 2> "$CELL/$MODE.stderr.log"
      printf 'DONE core=%s mode=%s\n' "$CORE" "$MODE"
    done
  done
done
printf 'FULL_COMPLETED_NO_SCORE\n' > "$OUT/STATUS"
