# Embedding evidence and closure design

Date: 2026-09-17

This note separates the completed representation results from the experiment
that would be needed for a checkpoint-before/after interpretation. It is a
planning and evidence note; it does not authorize a new training run and it
does not change any frozen result.

## What is already completed

There are four different experiments that have been called “embedding” in
the project. They answer different questions.

| Artifact | Input and labels | What was trained | Main result | Scientific status |
|---|---|---|---|---|
| `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/embedding_objective.tsv` | 2,000 512-bp TE fragments, four broad classes (SINE/LINE/LTR/DNA), mostly human and zebrafish with three mouse records | A0 is raw pretrained GENERanno; A1 adds a class-supervised contrastive projection; B0/B1 use a binary-fine-tuned token model; C0/C1 are k-mer controls | A1: ARI 0.7987, NMI 0.7683, pair AUC 0.9532, probe macro-F1 0.8273. C1 is stronger: ARI 0.9208, NMI 0.8890. B1 is weak: ARI 0.2822, NMI 0.2845 | Completed screen. A1 is a positive **label-guided broad-class representation** result, not unsupervised discovery and not a TE-vs-background result |
| `reports/NTV2-LABELFREE-CLUSTER-20260915/run-12732191/RESULTS.md` | 1,331 natural copies, 40 exact families, train/CAL/EVAL split with homology and 50-kb locus blocking | Same-record masked reverse-complement SSL; no family labels in loss or model selection; NTv2 last two blocks optionally updated | Frozen NTv2 EVAL ARI/NMI 0.2361/0.6160; encoder adaptation 0.2567/0.6129; inductive ARI 0.2168; k-mer SSL 0.2367 | Completed exploratory result. It is family-label-free adaptation of a TE-enriched panel, not fully unsupervised TE discovery; no consistent improvement |
| `reports/TE-FINAL-DFAM-RECOVERY-20260914/local_current/summaries/embedding_dfam_consensus.tsv` | 1,800 Dfam consensus fragments, ten families | Frozen pretrained GENERanno or sequence-feature controls, with a supervised projection in A1/C1 | A1 ARI/NMI 0.2242/0.3119; C1 0.7083/0.7135 | Completed family-level diagnostic. Sequence controls outperform the foundation-model arm; do not present it as foundation-model superiority |
| `reports/SIB-RETREAT-EMBED-REPLICATION-20260917` on Baobab | Six species, eight comparator labels, 512-bp chunks from the fixed SF5 train/val/test chromosomes | Frozen pretrained GENERanno/NTv2; projection trained with class-conditioned InfoNCE | On the held-out test, NTv2 raw/projection eight-label macro-F1 is 0.488/0.517 and K=8 ARI is 0.056/0.166; GENERanno raw/projection macro-F1 is 0.273/0.369 and ARI 0.020/0.090 | Completed exploratory replication. The projection is supervised; `BG` is comparator-relative, not independent biological truth |

The older `TE_final` archive contains a genuine strong-looking figure, but
its interpretation must be precise. The archived pipeline uses a warm
TE-fine-tuned model and a class-conditioned supervised contrastive projection.
The projection receives class labels. The archived machine table reports
class ARI/NMI 0.045/0.101 for B1, while an older five-class/hg38 prose summary
reports 0.6928/0.7164. These are different panels or summaries; they must not
be merged. In either case, the result is not unsupervised evidence and does
not show that an untouched pretrained model separates TE from background.

The strongest current positive conclusion is therefore narrower and useful:
pretrained GENERanno features contain enough information for a supervised
projection to organize four broad TE classes on a balanced, TE-enriched
fragment panel. The strongest class geometry in that screen comes from the
k-mer plus contrastive control, so a claim of foundation-model-specific
family understanding would be unsupported.

## What “before versus after fine-tuning” should mean

The claim-bearing paired experiment should use the same sequences, split,
pooling rule, and evaluation code for the two checkpoints of the same NTv2
backbone that are directly comparable:

1. **Pretrained:** the untouched `nucleotide-transformer-v2-500m-multi-species`
   checkpoint.
2. **Six-species fine-tuned:** the frozen D checkpoint at
   `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model`.

The GENERanno H0 binary checkpoint and the current SF5 eight-state checkpoint
(`SF5_ONTOLOGY_CLOSURE_base_seed42_12731987/best_model`) can be extracted as a
secondary panel, within the GENERanno backbone. They differ in task-training species,
objectives and exposure, so they cannot isolate the causal effect of the
training objective. They must not be substituted for either NTv2 checkpoint.

The checkpoints should be extracted on the already fixed six-species SF5
512-bp panel. No sequence, coordinate, chromosome split, or pooling change
is allowed between checkpoints. The existing SIB replication has 1,843 train,
809 validation, and 1,580 test chunks and records the split chromosomes and
all eight source states. It is the appropriate paired substrate for this
comparison, although it is a comparator-relative panel rather than
independent biological truth.

The primary endpoints should be reported in separate rows. BG stays an
explicit class throughout; no endpoint silently relabels BG as TE:

* **Known five-class:** BG/SINE/LINE/LTR/DNA only; report macro-F1 and
  confusion matrix. This is the cleanest test of whether a checkpoint changes
  broad TE geometry.
* **Eight-state full endpoint:** retain KNOWN_OTHER_TE, AMBIGUOUS_TE and
  UNCLASSIFIED. Report it as a separate diagnostic with all supports. Do not
  relabel these states as BG or silently remove them.
* **Conditional TE-only:** SINE/LINE/LTR/DNA only, with BG excluded from both
  training of a readout and evaluation. This measures within-TE class
  organization and must not be confused with detection.

For each checkpoint, first evaluate the raw mean-pooled hidden state without
labels. Fit K-means only with predeclared K (2, 4, 5 and 8), with the endpoint
subset and standardization fit on TRAIN only; never choose K from test labels.
Then fit a 5-NN readout on the same endpoint subset of TRAIN and apply it once
to TEST. This readout is explicitly named **supervised**; its score is not an
unsupervised result. Report per-species metrics and the pooled metric; a pooled
score alone can hide the *C. elegans* or frog loss.

The minimal paired comparison is a single extraction job for the two frozen
NTv2 checkpoints and a CPU evaluator. It does not require new encoder training or
multiple seeds. The requested figure should be a matrix of checkpoint ×
endpoint with per-species points, accompanied by a confusion matrix. UMAP
can be shown as a visual aid only; it is never the evidence for separation.

## Optional label-free branch

The NTv2 family-label-free result already closes the question “was a truly
label-free objective attempted?” It should be retained as a supplementary
diagnostic, with its raw frozen, k-mer SSL, frozen-head, encoder-adaptation,
and inductive rows. Re-running it merely to obtain a more attractive plot is
not justified by the current evidence. If a label-free checkpoint comparison
is later desired, it must reuse the same six-species sequences and split and
must keep the eight-state endpoint separate.

## Interpretation rules for the paper

The following claims are supportable if the paired extraction gives the
corresponding direction:

* “Pretraining provides a non-random starting representation” requires a
  pretrained-versus-random or pretrained-versus-k-mer control on the same
  test panel.
* “Fine-tuning reorganizes broad TE classes” requires a raw hidden-state
  improvement from the pretrained checkpoint to a fine-tuned checkpoint under
  the known five-class endpoint. A supervised projection improvement alone
  only shows that the labels are usable by a readout.
* “The model learned family-level information” requires exact family labels,
  copy/homology blocking, a sequence control, and an untouched held-out
  evaluation. The current family experiment is annotation-level and does
  not meet that claim by itself.
* “The model separates the known TE classes from BG before fine-tuning” is not
  supported by the current TE-only A1 screen. It needs the paired panel and
  the explicit known-five endpoint.

The current results already provide a useful but modest interpretation
section: class-guided geometry is reproducible in a narrow TE fragment
setting; it is not automatically a family-discovery tool; and binary
fine-tuning can reduce broad-class geometry even when binary detection is
strong. This is a more defensible explanation of the model than selecting
the most attractive UMAP or the historical five-class number.

## Execution boundary and budget

No training is included in this closure protocol. The only new claim-bearing
operation is inference-time feature extraction for the two frozen NTv2
checkpoints on the fixed SIB panel, followed by a CPU-only evaluator. One GPU
with the existing local model environment is sufficient for extraction; the
1,580-test-row metric calculation and figures are CPU work. The run should
stop if the checkpoint loader, split manifest, or pooling metadata differ.

The reusable evaluator is
`scripts/experiments/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/evaluate_matched_embeddings.py`.
Its non-submitting wrapper and frozen parameters are in
`configs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917.yaml` and
`scripts/experiments/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run.sbatch`.
The batch files contain explicit Baobab paths for the reviewed execution
environment; they do not submit a job unless invoked with `sbatch`.

## Matched run completed 2026-09-17

The two-checkpoint NTv2 extraction completed as GPU job `12849477`; the
final CPU readout completed as job `12849665` (after the intermediate
`12849630` readout). The two feature roots have
identical record keys for train (1,843), validation (809), and test (1,580),
and both use the special-token-free pooling contract. On the test panel, the
supervised 5-NN macro-F1 improved from 0.4885 to 0.6394 for known five-class,
from 0.4730 to 0.5944 for full eight-state, and from 0.6342 to 0.7197 for
conditional four-class TE. The corresponding train-fitted unsupervised
K-means geometry improved for full eight-state K=8 (ARI 0.0623 to 0.1096) and
known-five K=5 (0.0386 to 0.1105), but conditional TE K=4 decreased (0.0713
to 0.0424). A separate known-support binary BG-versus-known-TE 5-NN diagnostic
gave macro-F1 0.5211 to 0.7211, with the non-main4 states excluded from the
binary denominator (KNOWN_OTHER_TE 125, AMBIGUOUS_TE 120 and UNCLASSIFIED
54); the same full-eight TRAIN K=2 clustering scored
ARI 0.0118 to 0.2181 on known-support binary truth. This is therefore
evidence for improved supervised decodability with only partial evidence for
label-free geometric reorganization.

The SIB panel was already observed and contains four species represented in
the D training panel plus frog and fruit fly; exact D training-coordinate or
homology exposure has not been audited. The result must remain a paired
representation diagnostic rather than an independent generalization claim.
The complete numbers and per-species rows are recorded in
`reports/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run-12849477/RESULTS.md`.
The matched run did not add a logistic linear probe, k-mer/permutation
control, new contrastive training, or UMAP evidence, so it does not close the
entire explanatory-control suite by itself.

## GENERanno three-checkpoint diagnostic completed

The separate same-backbone GENERanno run `12854214` completed on the identical
SIB records. Known-five 5-NN macro-F1 was 0.3654 / 0.4329 / 0.7674 for
pretrained / human binary FT / six-species class FT; full-eight values were
0.2748 / 0.3123 / 0.6857 and conditional TE-four values 0.4746 / 0.4990 /
0.9030. TE-four K-means ARI was 0.0417 / 0.0693 / 0.2429. The class-trained
checkpoint therefore supplies a positive matched geometry result, without
proving label-free family discovery or a causal objective advantage. The
pretrained binary 5-NN score (0.5221) does not establish strong TE/BG separation.

GEN pooling excludes structural specials and retains N/UNK sequence tokens,
including the one all-N TEST BG record. This tokenizer-specific contract is
explicitly separate from NTv2. Saved split metadata supports train/test
chromosome separation for SF5, but homology exclusion remains unresolved.
See [results and figure](../../../reports/GENERANNO-MATCHED-REPRESENTATION-20260917/run-12854214/RESULTS.md).
