#!/usr/bin/env bash
# Validate the completed custom-library annotation and rescore saved D output.
#SBATCH --job-name=te_d_sea_library_finalize
#SBATCH --partition=public-longrun-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_finalize_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_finalize_%j.err
set -euo pipefail
ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
EXPERIMENT="$ROOT/scripts/experiments/D-EXTERNAL-RC0-20260914"
BASE="$ROOT/outputs/D-EXTERNAL-RC0-20260914/sea_urchin_uncurated_dfam"
SOURCE="$ROOT/outputs/D-EXTERNAL-RC0-20260914/sea_urchin/slurm-12696615_1"
FOUT="$BASE/finalize-${SLURM_JOB_ID}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd "$ROOT"
python3 "$EXPERIMENT/test_panel_coordinate_lift.py"
python3 - "$EXPERIMENT" "$BASE" "$SOURCE" "$FOUT" <<'PY'
import json
import sys
from pathlib import Path

experiment, base, source, out = map(Path, sys.argv[1:])
sys.path.insert(0, str(experiment))
from panel_coordinate_lift import _read_fasta, write_short_panel, lift_repeatmasker_out

out.mkdir(exist_ok=False)
library = base / 'uncurated_lineage_taxon7668.fa'
records = _read_fasta(library)
lengths = [len(sequence) for _, sequence in records]
if len(records) != 3324 or min(lengths) <= 0:
    raise ValueError('fixed lineage library must have 3324 nonempty records')
# Keep the original erroneous first-line-only audit unchanged for provenance.
manifest = json.loads((base / 'library_manifest.json').read_text())
manifest['supersedes_length_audit'] = str(base / 'library_manifest.json')
manifest['length_audit_repair'] = 'sum all FASTA sequence lines per record; library itself unchanged'
manifest['sequence_length_bp'] = dict(count=len(lengths), min=min(lengths), max=max(lengths), total=sum(lengths))
(out / 'library_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

annotation = base / 'annotation_lifted'
short_panel, id_map = out / 'panel.short.fa', out / 'id_map.tsv'
write_short_panel(source / 'panel_regions.fa', source / 'panel_regions.json', short_panel, id_map)
if _read_fasta(short_panel) != _read_fasta(annotation / 'panel_regions.short_ids.fa'):
    raise ValueError('RepeatMasker query sequences differ from the fixed D panel')
lifted = out / 'panel_regions.lifted.out'
validation = lift_repeatmasker_out(annotation / 'panel_regions.short_ids.fa.out', id_map, lifted)
validation['short_query_sequences_equal_frozen_panel'] = True
validation['previous_lifted_out_equal'] = lifted.read_bytes() == (annotation / 'panel_regions.lifted.out').read_bytes()
validation['annotation_job'] = '12705928'
validation['new_annotation_run'] = False
(out / 'coordinate_validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps({'library_lengths': manifest['sequence_length_bp'], 'coordinate_validation': validation}))
PY
python3 "$EXPERIMENT/rescore.py" \
  --config "$EXPERIMENT/config/panel.json" --candidate sea_urchin \
  --existing-output "$SOURCE" --output-dir "$FOUT/rescore" --remote-root "$ROOT" \
  --label-out "$FOUT/panel_regions.lifted.out" \
  --label-source Dfam3.9_uncurated_lineage_taxon7668
printf '%s\n' '{"status":"COMPLETED","inference_rerun":false,"threshold_refit":false,"annotation_rerun":false}' > "$FOUT/completion.json"
