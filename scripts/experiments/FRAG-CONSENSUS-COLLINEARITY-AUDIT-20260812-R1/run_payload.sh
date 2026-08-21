#!/usr/bin/env bash
set -eo pipefail
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate benchmark_core
set -u
exec python "$@"
