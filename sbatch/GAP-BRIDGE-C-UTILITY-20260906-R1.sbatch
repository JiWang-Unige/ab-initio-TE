#!/usr/bin/env bash
#SBATCH --job-name=gap-c-utility
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=logs/gap-c-utility_%j.out
#SBATCH --error=logs/gap-c-utility_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
ROOT=$(pwd -P)
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_gap_tiberius_c
OUT=outputs/GAP-BRIDGE-C-UTILITY-20260906-R1/run-r1
CFG=configs/GAP-BRIDGE-C-UTILITY-20260906-R1.json
CODE=scripts/experiments/GAP-BRIDGE-C-UTILITY-20260906-R1
ENDPOINT=scripts/experiments/GAP-BRIDGE-C-ENDPOINT-20260906-R1
IMAGE="$ROOT/software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1/tiberius_2.0.7.sif"
test "$(git -C refs/repos/Tiberius-gap-c-r1 rev-parse HEAD)" = 4d657012a3ed4e923f5d0ac5cef65fecae8109bd
test -d refs/repos/Tiberius-gap-c-r1/model_weights/tiberius_weights_v2
test "$(< outputs/GAP-BRIDGE-C-ENDPOINT-20260906-R1/run-r1/READINESS)" = NONEMPTY_ENDPOINT_READY
test ! -e "$OUT"
test ! -e reports/GAP-BRIDGE-C-UTILITY-20260906-R1.json
python scripts/pre_submit_gate.py --exp-id GAP-BRIDGE-C-UTILITY-20260906-R1 --format json
python "$CODE/utility.py" prepare --config "$CFG"
printf '%s\n' RUNNING > "$OUT/STATUS"
printf '%s\n' "$SLURM_JOB_ID" > "$OUT/JOBID"
trap 'rc=$?; if (( rc != 0 )); then printf "FAILED exit=%s\n" "$rc" > "$OUT/STATUS"; fi' EXIT
printf 'job=%s\nproject=%s\nsource_commit=4d657012a3ed4e923f5d0ac5cef65fecae8109bd\n' "$SLURM_JOB_ID" "$ROOT" > "$OUT/env.txt"
container=(singularity exec --nv --cleanenv --env "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" --bind "$ROOT:/work/te" --bind "$ROOT/refs/repos/Tiberius-gap-c-r1:/opt/Tiberius" --pwd /work/te "$IMAGE" /usr/bin/python3)
"${container[@]}" -c 'import tensorflow as tf; import importlib.metadata as m; print({p:m.version(p) for p in ("tensorflow","bricks2marble")}); assert tf.config.list_physical_devices("GPU"), "allocated GPU invisible"'
"${container[@]}" -m unittest discover -s "$CODE" -p 'test_*.py' -v
"${container[@]}" "$CODE/utility.py" preflight --config "$CFG"
for CORE in 0 1 2 6 10 14 15 18 20; do
  for MODE in M0 MW MP; do
    printf 'START core=%s mode=%s\n' "$CORE" "$MODE"
    /usr/bin/time -v "${container[@]}" -c 'import os,runpy,sys; os.environ["C_ENDPOINT_OBSERVATION"]=sys.argv.pop(1); runpy.run_path(sys.argv.pop(1),run_name="__main__")' \
      "/work/te/$OUT/core$CORE/$MODE.observation.json" "$ENDPOINT/observed_tiberius.py" \
      --genome "/work/te/$OUT/core$CORE/$MODE.fasta" \
      --model_cfg /opt/Tiberius/model_cfg/mammalia_softmasking_v2.yaml \
      --seq_len 400050 --batch_size 1 \
      --out "/work/te/$OUT/core$CORE/$MODE.gtf" "/work/te/$OUT/core$CORE/$MODE.gff3" \
      > "$OUT/core$CORE/$MODE.stdout.log" 2> "$OUT/core$CORE/$MODE.stderr.log"
    printf 'DONE core=%s mode=%s\n' "$CORE" "$MODE"
  done
done
"${container[@]}" "$CODE/utility.py" score --config "$CFG"
printf '%s\n' COMPLETED > "$OUT/STATUS"
