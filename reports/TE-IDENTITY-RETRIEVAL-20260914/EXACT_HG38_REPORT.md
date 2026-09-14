# Exact-repName natural-copy retrieval report

Date: 2026-09-14  
Status: `PASS_NUMERIC_ANNOTATION_LEVEL`  
Scientific claim status: `ANNOTATION_LEVEL_ONLY`

## What was run

The corrected panel job was Slurm `12698062` (`te_identity_hg38`, completed,
4 CPUs, 12G requested, 00:04:23).  It used the real hg38 FASTA and
`rmsk_te.bed.gz` under:

`/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/genome_data/animals/hg38/`

The panel was restricted to `chr1`, `chr11`, and `chr13`, selected at most 40
exact RepeatMasker `repName` labels, and retained 40 non-overlapping intervals
per selected name.  `family_id` is the exact `repName`; broad `repFamily` is
stored separately as `superfamily_id`.  The source-copy key is coordinate
derived and must not be interpreted as a biological insertion ID.

The builder produced 40 families, 1600 natural intervals, and 1570 whole-panel
sequence/locus homology components.  Every selected family has TRAIN/CAL/EVAL
roles and at least four TRAIN copies.  The components block split leakage; they
are not biological insertion calls.  The copied panel audit is
`remote_runs/12698062_exact/panel/panel_status.json`.

Exact lookup against
`/srv/beegfs/scratch/users/j/jwang/Pretrain/TE_Contrastive_Clean/data/Dfam38_curated.strict_te_only.fa`
found one record for 29 selected names and no record for these 11 names:

`L1M5`, `L1ME1`, `L1ME4a`, `L1PA16`, `L1PA3`, `L1PA4`, `L1PA5`, `L1PA7`,
`L2a`, `L2b`, `L2c`.

No selected name had an ambiguous exact match.  Missing names were excluded
from the matched comparison; they were not silently replaced by a broad
family or another consensus.  The matched set therefore contains 29 families.

The sequence retrieval job was Slurm `12698062` for the original four arms and
Slurm `12698524` (`te_identity_seq`, completed, 1 CPU, 4G requested,
00:01:01) for the updated single-TRAIN-medoid arm.  The second job reused the
same audited manifest and sequences, with the same seed 42, k-mer size 6, and
CAL rule.  It did not train a model.  Its compact output is under
`remote_runs/12698524_exact_medoid/retrieval/`.

## Numeric result

All five sequence arms used 235 EVAL queries and 6328 known CAL negatives.  The
CAL budget was a pair-level false-accept rate of at most 0.01 (63/6328 =
0.00995575 in this run).  This pair-level calibration does not imply that the
accepted-query error rate is at most 1%; the latter is reported separately.

| arm | top-1 | family macro F1 | accepted EVAL | accepted accuracy |
|---|---:|---:|---:|---:|
| single Dfam consensus | 0.6000 | 0.5578 | 10 | 0.9000 |
| single TRAIN medoid | 0.2766 | 0.2334 | 18 | 0.2778 |
| k=4 TRAIN medoids | 0.3191 | 0.2778 | 18 | 0.2778 |
| random-4 TRAIN copies | 0.3021 | 0.2692 | 12 | 0.0833 |
| TRAIN k-mer centroid | 0.4255 | 0.4141 | 23 | 0.2609 |

The exact machine-readable metrics are
`remote_runs/12698524_exact_medoid/retrieval/metrics.json`; the original four
arm output is retained under
`remote_runs/12698062_exact/retrieval/metrics.json`.

## Interpretation boundary

The matched single-medoid versus k=4 comparison gives a small numerical gain
for k=4 over one medoid, but both are below the TRAIN centroid in this run.
The single Dfam consensus is an external-reference operational baseline.  It
was not generated as a single consensus from the same TRAIN-copy pool, so its
advantage cannot be attributed solely to one versus four prototype capacity.
The result therefore does not support a claim that multi-prototype retrieval
improves performance under this protocol.

The numbers are exact-family annotation retrieval scores on coordinate-derived
annotated intervals.  They do not measure biological insertion recovery,
cross-species generalization, or GLM quality.  Frozen GLM embeddings and
training-copy profile-HMM arms remain `NOTRUN`.  The natural-copy manifest was
left on Baobab rather than copied into the repository; its remote path is:

`/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_20260914/run_exact/panel/identity_manifest.jsonl`

The first broad-family panel job (`12696619`) remains explicitly invalid and is
not used in any result because it keyed `Alu`/`MIR` broad families instead of
exact `repName` labels.
