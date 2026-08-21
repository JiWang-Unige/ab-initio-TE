#!/usr/bin/env bash
# Source overlay is only accepted when the frozen commit itself declares v2.3.0.
set -euo pipefail
if [[ $# -ne 2 ]]; then echo "usage: $0 <config.json> <project-root>" >&2; exit 64; fi
if [[ -z ${SLURM_JOB_ID:-} ]]; then echo "EDTA source preparation requires dedicated CPU Slurm preparation" >&2; exit 63; fi
TEFM_CONFIG=$1; TEFM_ROOT=$2
if [[ ${TEFM_ALLOW_NETWORK:-0} != 1 ]]; then echo "typed-block: exact EDTA source acquisition needs TEFM_ALLOW_NETWORK=1" >&2; exit 65; fi
read -r TEFM_COMMIT TEFM_TARGET <<EOF
$(python3 - "$TEFM_CONFIG" "$TEFM_ROOT" <<'PY'
import json,pathlib,sys
c=json.load(open(sys.argv[1]))['exact_sources']['edta']; print(c['commit'], pathlib.Path(sys.argv[2],c['overlay_dir']).resolve())
PY
)
EOF
if [[ -e ${TEFM_TARGET} ]]; then echo "refusing to overwrite ${TEFM_TARGET}" >&2; exit 66; fi
TEFM_TMP=${TEFM_TARGET}.tmp.$$
git clone --filter=blob:none https://github.com/oushujun/EDTA.git "$TEFM_TMP"
git -C "$TEFM_TMP" fetch --tags --force origin
git -C "$TEFM_TMP" fetch --depth 1 origin "$TEFM_COMMIT"
git -C "$TEFM_TMP" checkout --detach "$TEFM_COMMIT"
test "$(git -C "$TEFM_TMP" rev-parse HEAD)" = "$TEFM_COMMIT"
test "$(git -C "$TEFM_TMP" rev-parse 'refs/tags/v2.3.0^{commit}')" = "$TEFM_COMMIT"
rm -rf "$TEFM_TMP/.git"
TEFM_TREE_SHA=$(python3 - "$TEFM_TMP" <<'PY'
import hashlib,pathlib,sys
root=pathlib.Path(sys.argv[1]); h=hashlib.sha256()
for p in sorted(x for x in root.rglob('*') if x.is_file()):
    h.update(p.relative_to(root).as_posix().encode()+b'\0')
    q=hashlib.sha256(p.read_bytes()).hexdigest(); h.update(q.encode()+b'\n')
print(h.hexdigest())
PY
)
TEFM_PREP_SHA=$(sha256sum "$0" | awk '{print $1}')
TEFM_CONFIG_SHA=$(sha256sum "$TEFM_CONFIG" | awk '{print $1}')
TEFM_ENV_SHA=${TEFM_PREP_ENV_SHA256:?preparation sbatch must export TEFM_PREP_ENV_SHA256}
TEFM_ENV_PATH=${TEFM_PREP_ENV_FILE:?preparation sbatch must export TEFM_PREP_ENV_FILE}
TEFM_MANIFEST_TMP=${TEFM_TARGET}.manifest.json.tmp.$$
python3 - "$TEFM_COMMIT" "$TEFM_TARGET" "$(sha256sum "$TEFM_TMP/EDTA.pl" | awk '{print $1}')" "$TEFM_TREE_SHA" "$SLURM_JOB_ID" "$TEFM_PREP_SHA" "$TEFM_CONFIG_SHA" "$TEFM_ENV_PATH" "$TEFM_ENV_SHA" > "$TEFM_MANIFEST_TMP" <<'PY'
import json,sys
print(json.dumps({'schema_version':'TEFM-EDTA-SOURCE-OVERLAY-2.0.0','release_tag':'v2.3.0','commit':sys.argv[1],'overlay':sys.argv[2],'edta_pl_sha256':sys.argv[3],'source_tree_sha256':sys.argv[4],'preparation_slurm_job_id':sys.argv[5],'preparation_code_sha256':sys.argv[6],'config_sha256':sys.argv[7],'environment_path':sys.argv[8],'environment_sha256':sys.argv[9]}, sort_keys=True))
PY
mv "$TEFM_TMP" "$TEFM_TARGET"
mv "$TEFM_MANIFEST_TMP" "${TEFM_TARGET}.manifest.json"
