# Native NTv2 frozen-embedding retrieval (2026-09-14)

This report records a bounded exploratory arm added after the exact-name
natural-copy panel was fixed.  It uses the native frozen
`nucleotide-transformer-v2-500m-multi-species` checkpoint only for encoder
inference.  It does not train a contrastive projection, fine-tune the model,
change the split, fill gaps, or change the CAL/EVAL rule.

## Input and implementation

- Panel: 1,600 coordinate-derived hg38 annotated intervals from 40 exact
  RepeatMasker `repName` families, plus 29 exact Dfam consensus rows.
- Matched evaluation: 29 families, 235 EVAL queries, and 6,328 known CAL
  negative pairs.
- Model: native NTv2-500M at
  `/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species`;
  hidden size 1,024.
- Loader: native `AutoModelForMaskedLM` remote-code mapping, with final
  hidden states used for inference and no logits.  The initial generic
  `AutoModel` attempt is invalid because its non-GLU ESM class expects a
  4,096-wide intermediate weight while the native checkpoint stores an
  8,192-wide GLU projection.
- Pooling: mean over non-special tokens from the native 6-mer tokenizer.
  Content tokens are split at token boundaries without overlap when needed and
  combined by content-token-count weighted mean.  This panel had zero
  multi-segment records.
- Embeddings: `(1629, 1024)`, `float32`, finite; no random or k-mer fallback.
- Prototype IDs, family set, split roles, and selection were inherited from
  the fixed `sequence_retrieval.py` k-mer-space selection.  Prototypes were
  not reselected in GLM space.

## Results

Every arm used the same CAL alpha `0.01`, with 63 false accepts among 6,328
known negatives (`0.00996`), followed by a frozen EVAL threshold.

| arm | top-1 | family macro F1 | accepted EVAL | accepted accuracy |
|---|---:|---:|---:|---:|
| single Dfam consensus | 0.1277 | 0.1022 | 44 | 0.2955 |
| single TRAIN medoid | 0.2043 | 0.1759 | 72 | 0.2083 |
| k=4 TRAIN natural prototypes | 0.2638 | 0.2460 | 51 | 0.1961 |
| random-4 TRAIN copies | 0.2340 | 0.1971 | 37 | 0.2162 |
| TRAIN centroid | 0.3234 | 0.3103 | 49 | 0.3469 |

The strongest frozen-embedding arm in this fixed selection was the TRAIN
centroid.  k=4 was higher than one TRAIN medoid but lower than the centroid;
the results do not establish a general multi-prototype benefit. Comparing
the external Dfam consensus with TRAIN natural-copy references is not a
causal one-versus-many test, because those reference pools have different
construction histories. The 6-mer versus GLM comparison does retain the same
reference IDs. Pretraining exposure to related sequences is unresolved, and all
scores are annotation-level numeric results rather than biological insertion
recovery.

## Provenance and status

- GPU extraction: Slurm `12705597`, `COMPLETED`, output directory
  `/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_20260914/run_glm_ntv2_native_fixed/`.
- CPU retrieval: Slurm `12705619`, `COMPLETED`, output subdirectory
  `.../run_glm_ntv2_native_fixed/retrieval/`.
- Compact copied evidence: `remote_runs/12705597_12705619_ntv2_glm/`.
- Machine status: `PASS_NUMERIC_ANNOTATION_LEVEL`.
- Scientific status: exploratory, non-preregistered, annotation-level only;
  contrastive training, GLM-space prototype reselection, profile-HMM scoring,
  and biological insertion truth remain open.
