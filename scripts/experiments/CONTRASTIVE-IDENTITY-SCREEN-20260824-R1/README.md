# Contrastive identity screen (R1)

This is a small, independent replacement screen for the historical Module 5
contrastive experiment. It fails closed when family/copy/homology identity is
not present. The archived Module 5 records are expected to stop at this gate:
they contain `species/chrom/start/end/class/family/sequence`, but not stable
`id`, `superfamily_id`, `copy_id`, or `homology_component_id`.

## Run

```bash
python scripts/experiments/CONTRASTIVE-IDENTITY-SCREEN-20260824-R1/contrastive_identity_screen.py \
  --input /path/to/fragments.jsonl \
  --output reports/contrastive_identity_screen/R1 \
  --crop-length 512 --augment
```

The input may be JSONL (or `.jsonl.gz`) or TSV. A valid scientific input must
contain `id`, `sequence`, `superfamily_id`, `family_id`, `copy_id`, and
`homology_component_id`; `fragment_id`/`record_id` and `family` are transparent
aliases. Copy IDs are namespaced as `(family_id, copy_id)`; coordinates are
never promoted to copy identity.

The gate always writes `input_manifest.json` and `screen_manifest.tsv`.
Incomplete identity writes `STATUS=BLOCKED_IDENTITY_FIELDS`, null ARI/NMI, and
no clustering result. With complete identity, family/copy/component connected
groups are assigned to train/val/test first; crop and reverse-complement
augmentation happen afterward. Leakage is audited before metrics.

The primary comparator is frozen 6-mer frequency + DBSCAN (`oracle_k_used:
false`). An optional frozen `.npy` base embedding can be compared with the same
procedure. ARI/NMI are evaluated only when the test denominator has more than
one family; DBSCAN eps sensitivity (not multi-seed stability) and noise fraction
are reported. B-cubed precision/recall/F1, family purity, and same-superfamily
different-family false-link rate are also reported. Any supervised family contrastive run belongs
under `supervised_family_contrastive_upper_bound` and can never be primary.

Exit code 2 means a typed block; exit code 0 means the screen completed with a
valid leakage audit. No Slurm submission is performed by this screen.
