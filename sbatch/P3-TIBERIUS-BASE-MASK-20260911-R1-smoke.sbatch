#!/usr/bin/env bash
#SBATCH --job-name=p3-base-mask-smoke
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/p3-base-mask-smoke_%j.out
#SBATCH --error=logs/p3-base-mask-smoke_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
TASK_ROOT=$(pwd -P)
CFG=configs/P3-TIBERIUS-BASE-MASK-20260911-R1.json
RUN=smoke
REVISION=r1
CORE=chr16:0
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
python "$SCRIPT" run-core --config "$CFG" --run "$RUN" --revision "$REVISION" --core "$CORE"

container=(singularity exec --nv --cleanenv --env "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" --bind "$TASK_ROOT:/work/te" --bind "$TASK_ROOT/refs/repos/Tiberius-gap-c-r1:/opt/Tiberius" --pwd /work/te "$IMAGE" /usr/bin/python3)
"${container[@]}" "/work/te/$SCRIPT" preflight-core --config "/work/te/$CFG" --run "$RUN" --revision "$REVISION" --core "$CORE"
for MODE in U P R; do
  mode_container=(singularity exec --nv --cleanenv \
    --env "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" \
    --env "BASE_MASK_OBSERVATION=/work/te/$OUT/core-chr16-0/$MODE.observation.json" \
    --bind "$TASK_ROOT:/work/te" \
    --bind "$TASK_ROOT/refs/repos/Tiberius-gap-c-r1:/opt/Tiberius" \
    --pwd /work/te "$IMAGE" /usr/bin/python3)
  "${mode_container[@]}" "/work/te/$OBS" \
    --genome "/work/te/$OUT/core-chr16-0/$MODE.fasta" \
    --model_cfg /opt/Tiberius/model_cfg/mammalia_softmasking_v2.yaml \
    --seq_len 400050 --batch_size 1 \
    --out "/work/te/$OUT/core-chr16-0/$MODE.gtf" "/work/te/$OUT/core-chr16-0/$MODE.gff3" \
    > "$OUT/core-chr16-0/$MODE.stdout.log" 2> "$OUT/core-chr16-0/$MODE.stderr.log"
done
printf 'SMOKE_COMPLETED_NO_EFFECT_GATE\n' > "$OUT/STATUS"
