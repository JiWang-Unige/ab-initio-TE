# Unified NTv2 representation comparison (2026-09-18)

## Purpose

This experiment closes the same-backbone representation comparison requested
for the paper.  The three arms are evaluated on the exact same SIB 512-bp
records and split: native NTv2-500M pretrained, the completed six-species
binary D checkpoint, and a matched eight-state class checkpoint initialized
from D.  The experiment does not reuse the older GENERanno SF5 class result;
that result has a different backbone and species panel.

The intended interpretation is descriptive: supervised readouts and
label-scored unsupervised partitions quantify how the representations align
with the declared ontology.  A class arm initialized from D and unfreezing
the last two encoder blocks is an ontology-adapted representation, so an
improvement cannot be presented as a strict causal effect of the class head
alone.

## Frozen inputs and class construction

The binary D materialization is read from
`outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202`, with the D
training override for `c_elegans` TRAIN at
`outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000/TRAIN/c_elegans.jsonl.gz`.
The class labels are painted on those exact coordinates from the six-species
`comparator_plus_unknown` BED entries in
`software_outputs/repeatmasker_dfam/02_ready_by_design/B_animal_production/SPLIT_MANIFEST.tsv`.
The mapping is the frozen SF5 ontology: BG, SINE, LINE, LTR, DNA,
KNOWN_OTHER_TE, AMBIGUOUS_TE, and UNCLASSIFIED.  Unresolved/Unknown source
annotations remain UNCLASSIFIED; they are never converted into BG.  Overlap
painting uses the deterministic `(start, end, label)` order inherited from
the SF5 preparation.  A 6-bp native token receives the majority base label,
with the lowest numeric label breaking ties.  This projection is fixed for
TRAIN, CAL, and DEV before training.

The class materialization contains 21,000 TRAIN half-records (the worm
override contributes 6,000), and 6,000 each in CAL and DEV.  These correspond
to 1,500/3,000 paired 8,192-bp tiles in TRAIN and 500 paired tiles per
species in CAL/DEV.  The materialization job completed as Slurm job
`12887930`; its `STATUS` and `PREP_STATUS` are `PREPARED` and `PASS`.

## Class training

The class arm uses the native NTv2 token-classification implementation and
strictly transfers every D state-dict entry except the binary classifier
weight and bias, which are replaced by a fresh eight-class native linear
head.  Only the final two encoder blocks and the class head are trainable.
The six species each contribute one sixth of the optimizer gradient per step,
matching the D training loop.  The frozen protocol is seed 42, 900 optimizer
steps, 90 warmup steps, validation every 150 steps, AdamW learning rate
`2e-5`, weight decay `0.01` on the same parameter groups as D, gradient clip
1.0, and bfloat16 on the 3090.  The best checkpoint is selected by pooled
all-eight token-level macro-F1 on CAL only; DEV is evaluated once afterward.
In the same forward pass, each token argmax is expanded over its native 6-bp
(or tail 1-bp) span and compared with the original 4,096-bp class labels.
The resulting base-pair confusion, precision/recall/F1, and per-species
metrics are reported separately; they do not alter checkpoint selection.
This keeps possible TE-map use from being inferred from a token-majority score
alone.

The resulting class probabilities define material probability as
`sum(p[class])` over the seven non-BG states.  This definition is recorded for
the downstream map, but it does not replace the frozen binary D evidence.

## Representation extraction

All three arms use the native NTv2 tokenizer and the final encoder hidden
state.  Each 512-bp sequence is passed through the same `max_length=2048`
tokenizer bound.  Pooling is the attention-mask-weighted mean after removing
padding and structural special tokens (CLS, PAD, MASK, and any declared
BOS/EOS).  The tokenizer UNK id is retained because it is an input token;
native N k-mer tokens are retained as well.  No sequence, record order, label,
or split is changed during extraction.  Features are saved as float32.

The representation evaluator reports:

* supervised cosine distance-weighted 5-NN and train-fitted standardized
  multinomial logistic readouts for known-five, full-eight, and conditional
  TE-four endpoints;
* train-only standardized K-means at fixed K=2,4,5,8, scored by ARI/NMI;
* a separately named full-eight K=2 partition scored on known-support binary
  truth; and
* pooled, per-label, and per-species sequence composition summaries for GC,
  N, sequence length, and the window-level TE indicator.

Known-five and TE-four clustering fits are annotation-filtered by endpoint.
They are unsupervised partition fits, but their ARI/NMI scores use labels, so
they are not claims of completely label-free biological discovery.  UMAP is
not a primary endpoint.  The older UMAP figure used a different
TE-enriched/balanced panel and an exploratory PCA/UMAP projection; it should
remain a diagnostic illustration only.

## Bounded context-length diagnostic

The same central 512 bp of selected 4,096-bp source half-windows is encoded
at 512, 2,048, and 4,096 bp.  Only flanking sequence changes.  The target
label is the dominant eight-state class in the central span, with numeric
ties resolved deterministically and Unknown/ambiguous classes retained.
Source-order selection is evenly spaced within each D species: 64 TRAIN, 32
CAL, and 32 DEV half-windows per species (384/192/192 total).

The native NTv2 tokenizer is a slow tokenizer without an offset API.  The
diagnostic reconstructs the same six-bp token spans used by D, verifies that
the native content-token count and input IDs match those spans, and pools only
the exact target overlap with weights summing to 512 bp.  Any mismatch blocks
the extraction; no target position is inferred from token count alone.  The
first attempt exposed a source/context indexing bug and was retained as a
blocked engineering attempt.  The repaired length-only run (`12897975`, with
CPU evaluator `12897980`) used source slices `[1792,2304)`, `[1024,3072)`,
and `[0,4096)` for contexts 512, 2,048, and 4,096 bp, respectively, with
local target spans `[0,512)`, `[768,1280)`, and `[1792,2304)`.  All 3 models x
3 contexts produced 768 finite 1,024-D rows and every target-pooling weight
sum was exactly 512 bp.  CPU readouts use train-to-DEV 5-NN and standardized
linear probes plus a train-fitted composition baseline from target/context GC
and N fractions and context length.  The complete context table is in
`reports/UNIFIED-NTV2-REPRESENTATION-20260918/LENGTH-RETRY-RESULTS-12897975.md`;
the primary SIB 512-bp panel remains the main representation comparison.

## Exposure and interpretation boundary

The SIB records are fixed for all three arms.  A separate audit of the full
1,580-record TEST panel found exact coordinate-and-sequence overlap with prior
D material for 3 chicken records in D TRAIN, 9 zebrafish records in D CAL, and
7 zebrafish plus 149 *C. elegans* records in D DEV.  Every overlapping base
matched the recorded D input.  This makes the panel a retrospective matched
representation diagnostic: CAL/DEV exposure is not gradient-training exposure,
but the panel cannot be described as untouched evidence.  The audit did not
test sequence homology outside exact coordinates or NTv2 pretraining exposure,
so those remain unresolved.  No records are removed from the fixed panel.

The class labels are derived from the same comparator family used to construct
the training material, so class readout gains are ontology-agreement evidence
rather than independent biological validation.  The exposure audit is Slurm
`12889831`; its complete per-record output is
`reports/UNIFIED-NTV2-REPRESENTATION-20260918/exposure-audit.json`.

## Files

* Protocol: `configs/UNIFIED-NTV2-REPRESENTATION-20260918.yaml`
* Class preparation/training: `scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918/`
* Compact results: `reports/UNIFIED-NTV2-REPRESENTATION-20260918/RESULTS.md`
