#!/usr/bin/env bash
#SBATCH --job-name=gap-c-endpoint
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=logs/gap-c-endpoint_%j.out
#SBATCH --error=logs/gap-c-endpoint_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
ROOT=$(pwd -P)
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_gap_tiberius_c
OUT=outputs/GAP-BRIDGE-C-ENDPOINT-20260906-R1/run-r1
CFG=configs/GAP-BRIDGE-C-ENDPOINT-20260906-R1.json
CODE=scripts/experiments/GAP-BRIDGE-C-ENDPOINT-20260906-R1
IMAGE="$ROOT/software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1/tiberius_2.0.7.sif"
test "$(git -C refs/repos/Tiberius-gap-c-r1 rev-parse HEAD)" = 4d657012a3ed4e923f5d0ac5cef65fecae8109bd
test ! -e "$OUT"
python "$CODE/endpoint.py" prepare --config "$CFG"
printf '%s\n' RUNNING > "$OUT/STATUS"
printf '%s\n' "$SLURM_JOB_ID" > "$OUT/JOBID"
printf 'job=%s\nproject=%s\ncontainer_project=/work/te\nsource_commit=4d657012a3ed4e923f5d0ac5cef65fecae8109bd\n' "$SLURM_JOB_ID" "$ROOT" > "$OUT/env.txt"
container=(singularity exec --nv --cleanenv --env "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES" --bind "$ROOT:/work/te" --bind "$ROOT/refs/repos/Tiberius-gap-c-r1:/opt/Tiberius" --pwd /work/te "$IMAGE" /usr/bin/python3)
"${container[@]}" -c 'import tensorflow as tf; import importlib.metadata as m; print({p:m.version(p) for p in ("tensorflow","bricks2marble")}); devices=tf.config.list_physical_devices("GPU"); print(devices); assert devices, "allocated GPU invisible"'
"${container[@]}" -m unittest discover -s "$CODE" -p 'test_*.py' -v
"${container[@]}" "$CODE/endpoint.py" preflight --config "$CFG"
# Predeclared fallback: core10 only when core6 has zero native CDS rows.
for CORE in 6 10; do
  /usr/bin/time -v "${container[@]}" -c 'import os,runpy,sys; os.environ["C_ENDPOINT_OBSERVATION"]=sys.argv.pop(1); runpy.run_path(sys.argv.pop(1),run_name="__main__")' \
    "/work/te/$OUT/core$CORE/observation.json" "$CODE/observed_tiberius.py" \
    --genome "/work/te/$OUT/core$CORE/M0.fasta" \
    --model_cfg /opt/Tiberius/model_cfg/mammalia_softmasking_v2.yaml \
    --seq_len 400050 --batch_size 1 \
    --out "/work/te/$OUT/core$CORE/M0.gtf" "/work/te/$OUT/core$CORE/M0.gff3"
  RESULT=$("${container[@]}" "$CODE/endpoint.py" evaluate --config "$CFG" --core "$CORE" \
    --gtf "$OUT/core$CORE/M0.gtf" --gff3 "$OUT/core$CORE/M0.gff3" \
    --observation "$OUT/core$CORE/observation.json")
  printf '%s\n' "$RESULT"
  if [[ "$RESULT" == NONEMPTY_ENDPOINT_READY ]]; then
    break
  fi
  test "$RESULT" = EMPTY_M0
done
printf '%s\n' "$RESULT" > "$OUT/READINESS"
printf '%s\n' COMPLETED > "$OUT/STATUS"
