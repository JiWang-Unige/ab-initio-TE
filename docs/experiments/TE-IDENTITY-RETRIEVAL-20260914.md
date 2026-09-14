# Identity-aware TE retrieval and multi-prototype contract (2026-09-14)

## Decision

The proposed single-consensus versus multi-prototype question is a valid
experiment, and a bounded hg38 retrieval run is now complete at the
annotation level.  A frozen native NTv2 embedding arm has also been run as a
new exploratory comparison.  These results must not be described as biological
insertion retrieval:
the panel builder creates
coordinate-derived annotated-interval IDs and sequence-based homology
components from a small hg38 panel; these IDs are explicitly not biological
insertion identities.  A later linking experiment still needs a separate
insertion truth source.

The executable input contract is
`scripts/experiments/TE-IDENTITY-RETRIEVAL-20260914/identity_retrieval.py`.
It audits a manifest, writes protocol readiness, and fails closed when a
natural copy has incomplete identity or when groups cross splits.  It does not
load genome FASTA, create embeddings, train a HMM, or report a retrieval score
without explicit inputs.  The panel builder and sequence runner are
`build_natural_panel.py` and `sequence_retrieval.py` in the same directory.
They use only a bounded natural interval panel and the explicit Dfam consensus
FASTA; they do not train a HMM or fill gaps.  The GLM arm only performs frozen
encoder inference and retrieval; it does not fine-tune the encoder or train a
contrastive projection.

## What the comparison must hold fixed

Every representation uses the same three roles: TRAIN for prototype/profile
construction, CAL for the threshold, and EVAL for the final query.  The
default contract keeps `source_copy_id` and `homology_component_id` within one
role; `host_id` remains contextual and scopes the copy key.  `host_id`
identifies the genome (for example `human:hg38`); a chromosome is stored
separately as `host_locus` and is never treated as a new host.  One host can
therefore supply independent TRAIN/CAL/EVAL copies.  Empty IDs are unknown and are excluded from
same-copy positives; two rows with empty IDs are not silently declared the
same copy.

The seven planned arms are:

1. one Dfam/family consensus per family;
2. one distinct TRAIN natural-copy medoid per family, selected by a deterministic
   k-medoids rule in k-mer space;
3. four distinct TRAIN natural copies per family, selected by a deterministic
   greedy k-medoids rule in k-mer space;
4. four distinct TRAIN natural copies per family, sampled with seed 42;
5. a fixed sequence k-mer baseline fitted on TRAIN;
6. an explicitly identified frozen GLM embedding table;
7. a profile HMM trained from TRAIN natural copies.

The single-medoid and k=4 arms require distinct natural `(host_id,
source_copy_id)` keys per family.  The first representative minimizes total
TRAIN distance and each following representative minimizes the residual
distance after it is added; this provides a small, auditable PAM-style medoid
selection instead of taking the first records.  A crop, rotation, or fragment
from one consensus has no new copy identity and cannot satisfy this
requirement.  The same CAL false-accept budget is used for every arm
(`alpha = 0.01`, with at least 100 known negative pairs in this run).
Threshold selection is performed once on CAL and then frozen for EVAL.

The script includes a deterministic threshold helper for later scoring.  The
audit command only emits readiness metadata.  Once the panel builder has
produced a manifest, the sequence runner calls the same fixed CAL rule on
actual sequence similarities; it never calls the rule on made-up scores.

## Bounded natural-copy panel

The prepared Slurm job is
`sbatch/te_identity_panel_and_sequence_retrieval_hg38_20260914.sbatch`.  Its
default panel is human hg38 on `chr1`, `chr11`, and `chr13`, with at most 40
exact RepeatMasker `repName` labels and a target of 40 non-overlapping
intervals per exact name (minimum 30).  `host_id=human:hg38` is shared by all
chromosomes; the chromosome is recorded as `host_locus`.  This avoids the
invalid practice of treating each chromosome as a separate host.

For each selected row, `family_id` is the exact RepeatMasker `repName` (for
example `AluY`), while `superfamily_id` retains the broad `repFamily` value
(for example `Alu`).  `source_copy_id` is a stable coordinate-derived key
containing assembly, host locus, interval, strand, and source row number.  It
is explicitly not a biological insertion ID.  `homology_component_id` is
constructed over the whole panel from pairwise 7-mer Jaccard links plus
same-locus overlap/nearby links.  Components only control split leakage; they
are not insertion calls.  Split assignment uses one deterministic
`Random(42)` shuffle of whole components.  If a component or family cannot
provide all three roles or four TRAIN copies, it is listed in the builder's
no-go fields and excluded from the matched retrieval comparison.

The builder uses the reference FASTA and `.fai` on Baobab and writes a small
inline-sequence manifest.  It can add one exact Dfam consensus row per
selected `repName`.  Consensus rows have no `source_copy_id` or homology
component and are prototype material only.  Exact lookup keeps missing and
ambiguous names in an audit list; it never falls back from `AluY` to broad
`Alu` or from a missing `repName` to another Dfam record.

## Evidence recovered from Baobab

The targeted remote root was:

`/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final`

The compact evidence copies are in
`reports/TE-IDENTITY-RETRIEVAL-20260914/remote_inventory/`.  The real-genome
BED source is:

`TE_final/genome_data/animals/{hg19,hg38,hs1,mm39}/rmsk_te.bed.gz`

These rows contain coordinates, repeat name, class/family, strand, and
divergence.  They identify annotated intervals in a host assembly, but they
do not by themselves establish insertion-level identity or a homology
component.  The compact family-composition summaries show that each assembly
has abundant annotated rows, for example:

| assembly | leading class/family | count in recovered summary |
|---|---|---:|
| hg19 | SINE/Alu | 1,244,709 |
| hg38 | SINE/Alu | 1,282,821 |
| hs1 | SINE/Alu | 1,204,921 |
| mm39 | LINE/L1 | 877,139 |

These counts establish that natural-copy material exists; they are not counts
of independently resolved biological insertions.

The Dfam consensus input is:

`/srv/beegfs/scratch/users/j/jwang/Pretrain/TE_Contrastive_Clean/data/Dfam38_curated.strict_te_only.fa`

It is a 42,457,662-byte FASTA (remote `stat` on 2026-09-14) with headers such
as `>MIR#SINE/MIR` and `>AluY#SINE/Alu`.  This is suitable as consensus
prototype material.  It is not a source of independent genomic copies.

The recovered Phase 7 `consensus.py` creates multiple fragments from one
consensus, while `real_genome.py` extracts annotated genome intervals.  Both
files are copied under `remote_inventory/` for provenance.  The former is
useful for input preparation but cannot be used to claim copy-level
generalization by itself.

The current v2 JSONL genome records contain sequence, labels, chromosome,
coordinates, and species, but no copy or homology identity.  They cannot close
the identity split required here without a separately verified sidecar.

## Current protocol status

The corrected exact-name panel and sequence runs are complete.  They provide
numeric annotation-level evidence; they do not establish a scientific PASS or
biological insertion recovery:

| arm | current status | blocking evidence |
|---|---|---|
| single Dfam consensus | PASS_NUMERIC_ANNOTATION_LEVEL | external consensus baseline; not a same-TRAIN-copy consensus |
| single TRAIN medoid | PASS_NUMERIC_ANNOTATION_LEVEL | coordinate-derived natural-copy identity |
| k=4 natural medoids | PASS_NUMERIC_ANNOTATION_LEVEL | coordinate-derived natural-copy identity |
| random-4 natural copies | PASS_NUMERIC_ANNOTATION_LEVEL | fixed seed 42; coordinate-derived identity |
| basic sequence features | PASS_NUMERIC_ANNOTATION_LEVEL | fixed k-mer representation |
| frozen GLM embedding | PASS_NUMERIC_ANNOTATION_LEVEL | exploratory native NTv2 arm; pretraining exposure unresolved |
| training-copy profile HMM | NOTRUN | no verified HMM/profile input and copy split |

The remote evidence qualification is
`reports/TE-IDENTITY-RETRIEVAL-20260914/remote_inventory/status.json`.
It records the source paths, sizes, the initial identity-audit limitation, and
the subsequent bounded retrieval job paths.  The compact family summaries and
code are copied only as evidence; no genome FASTA, RepeatMasker BED,
checkpoint, or private secret was copied.

The first broad-family job was deliberately cancelled as invalid after its
panel status showed `Alu`/`MIR`-level keys rather than exact `repName` keys.
Its compact disposition is
`reports/TE-IDENTITY-RETRIEVAL-20260914/remote_runs/12696619_BROAD_FAMILY_INVALID.json`;
no figure or claim uses that run.  The corrected exact-name panel job is Slurm
12698062 and the retrieval-only single-medoid rerun is Slurm 12698524; compact
copies of both outputs are under
`reports/TE-IDENTITY-RETRIEVAL-20260914/remote_runs/`.
The rerun launcher is
`sbatch/te_identity_sequence_retrieval_existing_panel_20260914.sbatch`.

After the corrected builder, the exact machine-readable panel output is
`panel/panel_status.json`; after sequence retrieval it is
`retrieval/metrics.json`.  These outputs separate annotation-level numeric
results from biological insertion claims.  The current local empty audit is
`empty_audit/status.json` and intentionally remains `NOTRUN_INPUT_MISSING`.

The exact panel contains 40 `repName` families and 1600 non-overlapping
annotated intervals, with 1570 whole-panel sequence/locus homology components.
All 40 families have TRAIN/CAL/EVAL roles and at least four TRAIN copies.  Dfam
lookup is exact: 29 selected names have one matching consensus, 11 have no
matching record, and none is ambiguous.  Missing names are excluded from the
matched comparison rather than silently mapped to a broad `repFamily`.

For the 29 matched families, all five sequence arms used 235 EVAL queries and
6328 known CAL negatives under the fixed alpha .01 pair false-accept rule.  The
resulting annotation-level metrics are:

| arm | top-1 | family macro F1 | accepted EVAL | accepted accuracy |
|---|---:|---:|---:|---:|
| single Dfam consensus | 0.6000 | 0.5578 | 10 | 0.9000 |
| single TRAIN medoid | 0.2766 | 0.2334 | 18 | 0.2778 |
| k=4 TRAIN medoids | 0.3191 | 0.2778 | 18 | 0.2778 |
| random-4 TRAIN copies | 0.3021 | 0.2692 | 12 | 0.0833 |
| TRAIN k-mer centroid | 0.4255 | 0.4141 | 23 | 0.2609 |

The matched single-medoid versus k=4 comparison does not support a clear
benefit from four prototypes in this run: k=4 improves over one medoid
slightly but remains below the TRAIN centroid.  The Dfam consensus is an
external-reference operational baseline with a different construction history,
so its difference from k=4 cannot be attributed solely to one versus four
prototype capacity.  These scores are family-annotation scores, not biological
insertion recovery scores.  A profile-HMM comparison remains NOTRUN.

## Frozen native NTv2 exploratory arm

The native model was loaded from
`.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species`
(model ID `nucleotide-transformer-v2-500m-multi-species`, hidden size 1024) on
Baobab.  The model's native implementation uses a GLU intermediate layer, so
the extractor uses the native `AutoModelForMaskedLM` mapping with
`trust_remote_code=True` and reads the final hidden state only; it never
computes logits.  The initial `AutoModel` attempt is invalid because it
selects the built-in non-GLU ESM class and cannot load the native weights.

Pooling is the arithmetic mean over non-special content tokens from the native
6-mer tokenizer.  Sequences longer than the effective 2,048-token limit are
split only at token boundaries with no overlap and combined by content-token
count weighted means; no sequence in this panel required more than one
segment.  The embedding matrix has shape `(1629, 1024)`, is `float32`, and
contains 1600 natural intervals plus 29 exact Dfam consensus rows.  The
prototype record IDs, family set, split roles, CAL threshold rule, and EVAL
queries were inherited unchanged from `sequence_retrieval.py`; medoids were
not reselected in GLM space.

The GPU extraction was Slurm `12705597` and the dependent CPU retrieval was
Slurm `12705619`.  The remote output is
`/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_20260914/run_glm_ntv2_native_fixed/`;
compact outputs are under
`reports/TE-IDENTITY-RETRIEVAL-20260914/remote_runs/12705597_12705619_ntv2_glm/`.
The retrieval used the same 235 EVAL queries, 6,328 CAL negative pairs, and
fixed alpha 0.01 false-accept rule for every arm:

| frozen NTv2 arm | top-1 | family macro F1 | accepted EVAL | accepted accuracy |
|---|---:|---:|---:|---:|
| single Dfam consensus | 0.1277 | 0.1022 | 44 | 0.2955 |
| single TRAIN medoid | 0.2043 | 0.1759 | 72 | 0.2083 |
| k=4 TRAIN natural prototypes | 0.2638 | 0.2460 | 51 | 0.1961 |
| random-4 TRAIN copies | 0.2340 | 0.1971 | 37 | 0.2162 |
| TRAIN centroid | 0.3234 | 0.3103 | 49 | 0.3469 |

Each arm calibrated at 63 false accepts among 6,328 known CAL negatives
(`0.00996`).  These are numeric annotation-level results from a
non-preregistered exploratory arm; native pretraining exposure to related
sequences remains unresolved.  Within this fixed prototype selection, the
TRAIN centroid is the strongest frozen-embedding arm, while k=4 does not
outperform it.  The GLM-space results therefore do not establish a general
multi-prototype advantage and should not be combined with the external Dfam
consensus result as a causal one-versus-many comparison.  A GLM-space
prototype reselection study, contrastive training study, and profile-HMM arm
remain separate questions.

## Required next input before a Slurm run

For a subsequent representation, use the builder's manifest with one row per
natural genomic interval or validated consensus prototype.  It includes
`record_id`, `source_kind`, `host_id`, `host_locus`, `source_copy_id`,
`homology_component_id`, exact `family_id`, `split`, and sequence content.  The
builder documents how coordinate-derived source-copy and sequence/locus
homology IDs were obtained.  The corrected CPU job has now run the sequence
features, and the frozen native NTv2 arm has used the same manifest and CAL
budget.  A later profile-HMM run must use the same manifest and CAL budget.

The files `protocol_contract.json`, `input_inventory.tsv`, and `status.json`
are the intended handoff to that later job.  They deliberately separate
engineering readiness from numeric validity and from a scientific PASS.
