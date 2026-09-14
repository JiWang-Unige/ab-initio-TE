# TE retrieval improvement study (2026-09-14)

This is a bounded exploratory follow-up on the fixed exact-name hg38 panel.
The previous `k=4` label meant four natural prototypes; it did not test
nucleotide k-mer length.  This study separates those factors by testing
k-mer lengths 4, 6, and 8 with one TRAIN medoid, four TRAIN medoids, and a
TRAIN centroid.  It then trains one small family-supervised projection on the
already extracted frozen NTv2 embeddings.

## Fixed inputs and rules

- Manifest: `/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_20260914/run_exact/panel/identity_manifest.jsonl`.
- The same 1,600 natural annotated intervals, 40 exact `repName` labels, 29
  matched families, source-copy/homology split, and seed 42 are reused.
- The matched comparison has 235 EVAL queries and 6,328 known CAL negative
  pairs.  Every arm calibrates its threshold on CAL at pair false-accept rate
  at most 0.01, then evaluates the already-seen EVAL set.
- Medoids are selected from TRAIN only, in the corresponding k-mer space.
  Centroids are means of all TRAIN vectors.  No EVAL score is used to choose a
  k-mer length, prototype count, or model.
- The embedding input is the native frozen
  `nucleotide-transformer-v2-500m-multi-species` matrix at
  `/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_20260914/run_glm_ntv2_native_fixed/embeddings.npy`.

## K-mer length and prototype-count ablation

The output below is annotation-level family retrieval.  `single` and `k4`
refer to prototype count; the prefix gives the nucleotide k-mer length.

| arm | top-1 | family macro F1 | accepted EVAL | accepted accuracy |
|---|---:|---:|---:|---:|
| kmer4 + single TRAIN medoid | 0.2979 | 0.2572 | 31 | 0.2258 |
| kmer4 + k=4 TRAIN medoids | 0.3021 | 0.2765 | 26 | 0.2692 |
| kmer4 + TRAIN centroid | 0.3872 | 0.3855 | 33 | 0.4242 |
| kmer6 + single TRAIN medoid | 0.2766 | 0.2334 | 18 | 0.2778 |
| kmer6 + k=4 TRAIN medoids | 0.3191 | 0.2778 | 18 | 0.2778 |
| kmer6 + TRAIN centroid | **0.4255** | **0.4141** | 23 | 0.2609 |
| kmer8 + single TRAIN medoid | **0.3404** | **0.3088** | 21 | 0.1429 |
| kmer8 + k=4 TRAIN medoids | 0.3319 | 0.3042 | 12 | 0.0833 |
| kmer8 + TRAIN centroid | 0.3915 | 0.3621 | 19 | 0.3158 |

Every arm used 63 false accepts among 6,328 CAL negatives (`0.00996`).  The
centroid favors k-mer length 6 in this panel, while the medoid arms favor
k-mer length 8.  The effect of increasing prototype count is not uniform:
k=4 improves over one medoid at k-mer lengths 4 and 6, but is slightly worse
at length 8.  The centroid is higher than both medoid choices at all three
lengths.  This is a panel-level exploratory pattern, not evidence that one
k-mer length is generally optimal.

## Family-supervised NTv2 projection

The projection is a single linear 1,024-to-128 layer trained with full-batch
supervised contrastive loss on TRAIN family labels only.  The native 500M
backbone is frozen.  The fixed k-mer-6 prototype record IDs are reused for
raw and projected comparisons; they are not reselected in the projected
space.  AdamW uses learning rate `1e-3`, weight decay `1e-4`, temperature
`0.1`, 50 epochs, and seed 42.

Epoch selection is fixed before reading final EVAL scores: choose the earliest
epoch maximizing projected TRAIN-centroid CAL true-pair accepts under the 1%
pair-FAR rule.  Epoch 49 was selected with 102 CAL true accepts; epoch 50 had
99.  The training loss changed from 6.3933 at epoch 1 to 4.0701 at epoch 50.

| arm | top-1 | family macro F1 | accepted EVAL | accepted accuracy |
|---|---:|---:|---:|---:|
| raw NTv2 + single TRAIN medoid | 0.2043 | 0.1759 | 72 | 0.2083 |
| raw NTv2 + k=4 prototypes | 0.2638 | 0.2460 | 51 | 0.1961 |
| raw NTv2 + TRAIN centroid | 0.3234 | 0.3103 | 49 | 0.3469 |
| projected + single TRAIN medoid | 0.5064 | 0.5000 | 132 | 0.6742 |
| projected + k=4 prototypes | 0.4894 | 0.4919 | 137 | 0.6642 |
| projected + TRAIN centroid | **0.5106** | **0.5048** | 130 | **0.7231** |

The projected arms improve over their raw NTv2 counterparts on this already
examined panel, with the largest gain for the single-medoid arm.  The
projected centroid is marginally strongest, while projected k=4 is lower than
the projected centroid.  The result supports continuing the supervised
projection direction as an engineering/research lead; it does not establish
independent generalization, unsupervised clustering quality, or biological
insertion recovery.

## Provenance and status

### Matched-objective and input-scaling controls

Slurm `12708540` completed three additional fixed 50-epoch, seed42 controls
in 9 minutes 17 seconds. All use per-record L2 input scaling, a 128-dimensional
projection, the same TRAIN family labels, CAL selection rule and centroid
retrieval endpoint. No fitted scaling statistic uses CAL/EVAL. These controls
were specified after the first projection result and remain exploratory.

| input / training objective | top-1 | macro F1 | accepted / 235 | accepted accuracy | trainable parameters |
|---|---:|---:|---:|---:|---:|
| 6-mer frequencies / supervised contrastive | 0.6426 | 0.6057 | 175 | 0.7714 | 524,416 |
| frozen NTv2 / supervised contrastive | 0.5064 | 0.4994 | 129 | 0.6667 | 131,200 |
| frozen NTv2 / cross-entropy | 0.2809 | 0.2687 | 53 | 0.3585 | 134,941 |

The simple sequence representation also benefits strongly from contrastive
training and is higher than frozen NTv2 on this natural-copy panel. Therefore
the earlier raw-to-projected NTv2 improvement does **not** establish a GLM
advantage over a trained basic-feature control. The 6-mer input has 4,096
dimensions versus 1,024 for NTv2 and a larger projection parameter count;
these are equal epoch/objective controls, not exact capacity matches.

The cross-entropy model has an auxiliary TRAIN classifier, while its reported
endpoint is still cosine retrieval using projected TRAIN centroids. CAL
selected epoch1 for this endpoint; the contrastive arms selected epoch49.
This result does not rank optimized cross-entropy classification against
contrastive learning in general. The 1% CAL pair-FAR also does not bound the
accepted-query error rate. No arm establishes broad release readiness.

Evidence: `reports/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914/training-controls-12708540/`
contains exact configs, traces, metrics and query-level assignments. Model
states remain on Baobab under the same job-specific output directory.

- Slurm job: `12708302`, `COMPLETED`, 6 minutes on `public-longrun-cpu`.
- Remote output: `/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_improve_20260914/run1/`.
- Compact local evidence: `reports/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914/remote_runs/12708302/`.
- Machine status: `PASS_NUMERIC_ANNOTATION_LEVEL_EXPLORATORY`.
- Scientific status: exploratory and annotation-level only; EVAL was seen in
  the earlier study, pretraining exposure remains unresolved, and no
  biological insertion truth or unsupervised objective was used.

The executable and fixed parameters are in
`scripts/experiments/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914/improve_retrieval.py`
and
`configs/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914.yaml`.  The remote contract
test passed with Torch available; local syntax, focused contract tests, and
the Slurm shell syntax also passed.
