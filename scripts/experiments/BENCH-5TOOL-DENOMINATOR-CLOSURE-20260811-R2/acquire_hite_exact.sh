#!/usr/bin/env bash
# Explicit opt-in acquisition; mutable tags and the legacy 3.0 image are rejected.
set -euo pipefail
if [[ $# -ne 2 ]]; then echo "usage: $0 <config.json> <project-root>" >&2; exit 64; fi
if [[ -z ${SLURM_JOB_ID:-} ]]; then echo "HiTE image acquisition requires dedicated CPU Slurm preparation" >&2; exit 63; fi
TEFM_CONFIG=$1; TEFM_ROOT=$2
if [[ ${TEFM_ALLOW_NETWORK:-0} != 1 ]]; then echo "typed-block: set TEFM_ALLOW_NETWORK=1 before exact HiTE OCI acquisition" >&2; exit 65; fi
TEFM_REF=$(python3 - "$TEFM_CONFIG" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['exact_sources']['hite']['reference'])
PY
)
TEFM_COMMIT=$(python3 - "$TEFM_CONFIG" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['exact_sources']['hite']['commit'])
PY
)
TEFM_TARGET=$(python3 - "$TEFM_CONFIG" "$TEFM_ROOT" <<'PY'
import json,pathlib,sys
c=json.load(open(sys.argv[1])); print(pathlib.Path(sys.argv[2], c['exact_sources']['hite']['local_sif']).resolve())
PY
)
mkdir -p "$(dirname "$TEFM_TARGET")"
if [[ -e ${TEFM_TARGET} || -e ${TEFM_TARGET}.manifest.json || -e ${TEFM_TARGET}.help.txt || -e ${TEFM_TARGET}.inspect.json ]]; then echo "refusing to overwrite existing/partial HiTE asset: ${TEFM_TARGET}" >&2; exit 66; fi
TEFM_TMP=${TEFM_TARGET}.tmp.$$
apptainer pull "$TEFM_TMP" "$TEFM_REF"
TEFM_SHA=$(sha256sum "$TEFM_TMP" | awk '{print $1}')
apptainer exec --cleanenv "$TEFM_TMP" python /HiTE/main.py -h > "${TEFM_TMP}.help.txt"
grep -Eq 'version[[:space:]]+3\.3\.3|HiTE, version 3\.3\.3' "${TEFM_TMP}.help.txt"
apptainer inspect --json "$TEFM_TMP" > "${TEFM_TMP}.inspect.json"
TEFM_PREP_SHA=$(sha256sum "$0" | awk '{print $1}')
TEFM_CONFIG_SHA=$(sha256sum "$TEFM_CONFIG" | awk '{print $1}')
TEFM_ENV_SHA=${TEFM_PREP_ENV_SHA256:?preparation sbatch must export TEFM_PREP_ENV_SHA256}
TEFM_ENV_PATH=${TEFM_PREP_ENV_FILE:?preparation sbatch must export TEFM_PREP_ENV_FILE}
TEFM_HELP=${TEFM_TARGET}.help.txt
TEFM_INSPECT=${TEFM_TARGET}.inspect.json
TEFM_MANIFEST_TMP=${TEFM_TARGET}.manifest.json.tmp.$$
mv "${TEFM_TMP}.help.txt" "$TEFM_HELP"
mv "${TEFM_TMP}.inspect.json" "$TEFM_INSPECT"
python3 - "$TEFM_REF" "$TEFM_TARGET" "$TEFM_SHA" "$TEFM_HELP" "$(sha256sum "$TEFM_HELP" | awk '{print $1}')" "$TEFM_INSPECT" "$(sha256sum "$TEFM_INSPECT" | awk '{print $1}')" "$TEFM_COMMIT" "$SLURM_JOB_ID" "$TEFM_PREP_SHA" "$TEFM_CONFIG_SHA" "$TEFM_ENV_PATH" "$TEFM_ENV_SHA" > "$TEFM_MANIFEST_TMP" <<'PY'
import json,sys
print(json.dumps({'schema_version':'TEFM-HITE-OCI-2.0.0','reference':sys.argv[1],'sif':sys.argv[2],'sha256':sys.argv[3],'help_path':sys.argv[4],'help_sha256':sys.argv[5],'inspect_path':sys.argv[6],'inspect_sha256':sys.argv[7],'source_commit':sys.argv[8],'preparation_slurm_job_id':sys.argv[9],'preparation_code_sha256':sys.argv[10],'config_sha256':sys.argv[11],'environment_path':sys.argv[12],'environment_sha256':sys.argv[13]}, sort_keys=True))
PY
mv "$TEFM_TMP" "$TEFM_TARGET"
mv "$TEFM_MANIFEST_TMP" "${TEFM_TARGET}.manifest.json"
