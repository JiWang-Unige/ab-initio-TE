# NTV2-LABELFREE-CLUSTER-20260915

## Purpose and status

This is a bounded exploratory test of whether native nucleotide-transformer-v2
(NTv2-500M) gains a useful family geometry from a **family-label-free**
sequence objective. It is separate from the earlier family-supervised
projection and from Dfam consensus clustering. The natural-copy input is
selected from an annotated TE panel, so the accurate scope is
**TE-enriched, family-label-free adaptation**. It is not a fully unsupervised
TE discovery pipeline.

The experiment has user authorization to run on Baobab. It uses one fixed
seed (42), a maximum of 2,000 optimizer updates per trained arm, and one GPU.
The corrected run excludes the previously viewed 235-query panel and its
same-homology/same-50-kb-locus neighborhood using identifiers and coordinates
only. Sealed data and old checkpoints are not used. The runner is
`scripts/experiments/NTV2-LABELFREE-CLUSTER-20260915/ntv2_label_free_cluster.py`.

## Input and independent evaluation

The input is the existing natural-copy manifest:

`/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_20260914/run_exact/panel/identity_manifest.jsonl`

Only its 1,600 `natural_copy` rows are candidates. The 29 consensus rows are
excluded. There are 40 exact family names. Every row already contains an
inline sequence, a coordinate-derived `source_copy_id`, a
`homology_component_id`, and a host locus.

For the corrected run, the runner reads only `record_id` from the prior
development table
`/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_improve_20260914/run1/per_query.tsv`.
It removes matching records, all rows in their homology components, and all
rows in their fixed 50-kb host-locus blocks. It does not read the table's
family labels or scores. The expected retained panel is 1,331 records. The
new split is then built before model loading: records are joined when they
share a host-scoped source-copy ID, homology component, or a 50-kb host-locus
block. Components are shuffled with seed 42 and assigned with a repeating 6
train / 2 CAL / 2 EVAL pattern. Family labels are not consulted for assignment.
The expected counts are 1,205 components and approximately 806 train, 266 CAL,
and 259 EVAL records; the exact counts and cross-split audit are written by
the run.

The initial 12731961 attempt used a 2-Mb split and fixed K=40. Its EVAL
overlapped the previously viewed panel (44 record IDs, 43 homology components,
and 26 locus blocks), so it is retained only as an exploratory
`oracle-K/development-overlap` attempt and cannot support the independent
result. The corrected run is the result eligible for the main exploratory
comparison.

This is a locus/copy/homology-isolated evaluation within one human assembly;
it is not a species holdout. The CAL set is retained for an unlabeled SSL
split role but is not used for training or model selection. It cannot select an
epoch by family score. EVAL family labels are read only after the
representations are frozen and are used only to calculate external clustering
metrics.

## Label-free views and objective

For each training record, the runner makes two deterministic views: a 5%
masked version of the sequence and a 5% masked version of its reverse
complement. The positive pair is always the same record. Other records in the
batch are negatives. The objective is NT-Xent/InfoNCE with temperature 0.07.
No family, class, family prototype, EVAL label, threshold, or cluster label
enters view construction, pair construction, loss, update count, or model
selection. Training views longer than 2,048 bp use one fixed center crop to
bound attention memory. Raw and final evaluation embeddings use the complete
sequence with native token segmentation.

## Six fixed arms

| Arm | Representation/update | Role |
|---|---|---|
| `raw_6mer` | 4^6 composition vector, no updates | strong sequence baseline |
| `raw_frozen_ntv2` | native 1,024-d mean-pooled hidden state, frozen | pretrained zero-shot baseline |
| `kmer_ssl_head` | 4,096→256→128 head trained on same-record views | label-free sequence SSL control |
| `frozen_ntv2_ssl_head` | frozen native NTv2 plus 1,024→256→128 head | projection-only label-free control |
| `last_two_ntv2_ssl` | native NTv2 encoder layers 27–28 updated plus 1,024→256→128 head | actual encoder adaptation |
| `frozen_ntv2_capacity_matched_head` | frozen native NTv2 plus 1,024→938→128 head | head-capacity control for k-mer SSL |

The k-mer head has 1,081,728 trainable parameters. The capacity-matched
NTv2 head has 1,081,642, a difference of 86 parameters. The standard NTv2
head has 295,296 projection parameters. The last-two arm records the exact
number of native parameters updated at runtime and saves only its final two
layers plus projection state in the remote output.

The native model is loaded only from:

`/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species`

The runner requires the native directory name, config, vocabulary, and local
`model.safetensors`. It does not download weights or install packages.

## Evaluation

The corrected run selects one K from a predeclared {20, 30, 40, 50} grid using
silhouette on standardized raw frozen NTv2 TRAIN features only. The selected K
and all grid scores are written before any EVAL family labels are loaded and
then applied identically to every arm. This is a label-free K choice; K=40 is
not treated as the main result. On the new EVAL records, the runner reports
ARI, NMI, purity, and transductive silhouette for K-means fit on EVAL features.
It also reports inductive ARI/NMI/purity for K-means fit on TRAIN features and
applied to EVAL. Standardization statistics are fit on TRAIN features only. No
classification accuracy is reported as a primary endpoint because
cluster-to-family mapping would add a separate supervised choice.

The metrics are exploratory and annotation-level. They do not establish
biological insertion recovery, species generalization, or independence from
pretraining exposure. The family labels are external evaluation labels, so
the result should not be called fully unsupervised discovery.

## Execution record

The Slurm script is
`sbatch/NTV2-LABELFREE-CLUSTER-20260915.sbatch` and requests one GPU on
`shared-gpu`, 8 CPUs, 64 GiB RAM, and 2 hours. The script activates the
existing `te_benchmark` environment. The corrected run `12732191` completed
in 41 min 33 s. Native layer-state comparison `12733074` completed in 19 s
and confirms numerical changes in all 28 layer-27/28 weight tensors; the two
rotary-frequency buffers remained unchanged. The 1,331 retained records form
1,205 split components, distributed 725/240/240 across TRAIN/CAL/EVAL; record
counts are 806/266/259. The native report initially repeated record counts in
`components_by_split`; the compact report corrects this metadata from the
saved manifest without changing split assignment or clustering metrics.
Uncomputed silhouette fields use null.

The six-arm result and audit are in
[the completed report](../../reports/NTV2-LABELFREE-CLUSTER-20260915/run-12732191/RESULTS.md).
Actual adaptation improves transductive ARI from 0.236074 to 0.256677 but
reduces NMI from 0.615995 to 0.612937 and inductive ARI from 0.221511 to
0.216809. There is no consistent improvement over the frozen encoder or the
k-mer SSL baseline. This closes the bounded adaptation experiment and belongs
in supplementary ablations; it does not establish a generally better family
annotation tool. The CAL set was retained and was not used for model selection.

## Local checks before submission

The focused contract tests cover component split isolation, same-record
reverse-complement views, k-mer dimension, parameter matching, and the
label-free NT-Xent target pairing. They passed locally:

`python3 scripts/experiments/NTV2-LABELFREE-CLUSTER-20260915/test_ntv2_label_free_cluster.py`

Python syntax and Slurm shell syntax also passed. These checks do not verify
native model loading or training; those require the Baobab Slurm job.
