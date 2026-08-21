#!/usr/bin/env bash
# PFAM requires URL+digest supplied before download; it never calls TEtrimmer's implicit downloader.
set -euo pipefail
if [[ $# -ne 3 ]]; then echo "usage: $0 <config.json> <project-root> <tetrimmer-sif>" >&2; exit 64; fi
if [[ -z ${SLURM_JOB_ID:-} ]]; then echo "Pfam download/hmmpress requires dedicated CPU Slurm preparation" >&2; exit 63; fi
TEFM_CONFIG=$1; TEFM_ROOT=$2; TEFM_SIF=$3
read -r PFAM_HMM_URL PFAM_DAT_URL PFAM_HMM_SHA256 PFAM_DAT_SHA256 <<EOF
$(python3 - "$TEFM_CONFIG" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))['exact_sources']['tetrimmer']
print(x['pfam_hmm_url'],x['pfam_dat_url'],x['pfam_hmm_sha256'],x['pfam_dat_sha256'])
PY
)
EOF
if [[ ${PFAM_HMM_SHA256} == REQUIRED_* || ${PFAM_DAT_SHA256} == REQUIRED_* ]]; then echo "typed-block: Pfam release hashes are not frozen in config" >&2; exit 65; fi
TEFM_TARGET=$(python3 - "$TEFM_CONFIG" "$TEFM_ROOT" <<'PY'
import json,pathlib,sys
c=json.load(open(sys.argv[1])); print(pathlib.Path(sys.argv[2],c['exact_sources']['tetrimmer']['pfam_dir']).resolve())
PY
)
if [[ -e ${TEFM_TARGET} ]]; then echo "refusing to overwrite ${TEFM_TARGET}" >&2; exit 66; fi
TEFM_TMP=${TEFM_TARGET}.tmp.$$; mkdir -p "$TEFM_TMP"
curl --fail --location --proto '=https' --tlsv1.2 "$PFAM_HMM_URL" -o "$TEFM_TMP/Pfam-A.hmm.gz"
curl --fail --location --proto '=https' --tlsv1.2 "$PFAM_DAT_URL" -o "$TEFM_TMP/Pfam-A.hmm.dat.gz"
echo "${PFAM_HMM_SHA256}  ${TEFM_TMP}/Pfam-A.hmm.gz" | sha256sum -c -
echo "${PFAM_DAT_SHA256}  ${TEFM_TMP}/Pfam-A.hmm.dat.gz" | sha256sum -c -
gzip -dc "$TEFM_TMP/Pfam-A.hmm.gz" > "$TEFM_TMP/Pfam-A.hmm"
gzip -dc "$TEFM_TMP/Pfam-A.hmm.dat.gz" > "$TEFM_TMP/Pfam-A.hmm.dat"
apptainer exec --cleanenv --bind "$TEFM_TMP:/work/pfam" "$TEFM_SIF" hmmpress /work/pfam/Pfam-A.hmm
for suffix in Pfam-A.hmm Pfam-A.hmm.dat Pfam-A.hmm.h3f Pfam-A.hmm.h3m Pfam-A.hmm.h3i Pfam-A.hmm.h3p; do test -s "$TEFM_TMP/$suffix"; done
mv "$TEFM_TMP" "$TEFM_TARGET"
sha256sum "$TEFM_TARGET"/Pfam-A.hmm* > "${TEFM_TARGET}/manifest.sha256"
python3 - "$PFAM_HMM_URL" "$PFAM_DAT_URL" "$PFAM_HMM_SHA256" "$PFAM_DAT_SHA256" "$SLURM_JOB_ID" > "${TEFM_TARGET}/provenance.json" <<'PY'
import json,sys
print(json.dumps({'schema_version':'TEFM-PFAM-1.0.0','hmm_url':sys.argv[1],'dat_url':sys.argv[2],'hmm_gz_sha256':sys.argv[3],'dat_gz_sha256':sys.argv[4],'preparation_slurm_job_id':sys.argv[5]},sort_keys=True))
PY
