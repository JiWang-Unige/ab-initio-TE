# Matched NTv2 representation diagnostic — run 12849477

Status: `COMPLETED` (GPU extraction job `12849477`; corrected CPU readout
job `12849665`, following intermediate readout `12849630`). This is a paired representation diagnostic, not a new
generalization benchmark.

## Frozen input and extraction

- Source: the non-sealed SIB RETREAT 512-bp panel from
  `SIB-RETREAT-EMBED-REPLICATION-20260917/data_512`.
- Split sizes: train 1,843; validation 809; test 1,580.
- Test support: BG 360, SINE 75, LINE 306, LTR 280, DNA 260,
  KNOWN_OTHER_TE 125, AMBIGUOUS_TE 120, UNCLASSIFIED 54.
- Checkpoints: native NTv2-500M pretrained and the six-species D checkpoint
  `CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model`.
- Both arms used the same native tokenizer, batch order, records and
  `attention_mask_mean_excluding_padding_and_special_tokens` pooling. All
  tokenizer special IDs `[0, 1, 2, 3]` and padding positions were excluded.
- The train/validation/test record keys are byte-for-byte identical between
  the two feature roots. The test panel contains mouse, chicken, zebrafish,
  *C. elegans*, frog and fruit fly. D training species are human, mouse,
  chicken, zebrafish, pig and *C. elegans*; whether any SIB coordinates or
  homologous source records were exposed during D training is unresolved.

## Frozen readouts

`supervised_knn5` is a train-fitted 5-NN readout. Its conditional TE row fits
and evaluates only SINE/LINE/LTR/DNA. BG remains its own class in the
known-five and full-eight rows. A separate binary diagnostic reports BG versus
the four main TE classes on the known-five support only; the 299 non-main4
rows are explicitly excluded and are never relabelled as BG. They comprise
KNOWN_OTHER_TE 125, AMBIGUOUS_TE 120 and UNCLASSIFIED 54.
`unsupervised_kmeans` is train-fitted with predeclared K and does not use
labels for fitting; UMAP is not used.

| checkpoint | endpoint | n | accuracy | balanced accuracy | macro-F1 |
|---|---|---:|---:|---:|---:|
| NTv2 pretrained | known five | 1,281 | 0.4575 | 0.5079 | 0.4885 |
| NTv2 D | known five | 1,281 | 0.6245 | 0.6484 | 0.6394 |
| NTv2 pretrained | full eight | 1,580 | 0.4316 | 0.4895 | 0.4730 |
| NTv2 D | full eight | 1,580 | 0.5829 | 0.6072 | 0.5944 |
| NTv2 pretrained | conditional TE four | 921 | 0.6189 | 0.6491 | 0.6342 |
| NTv2 D | conditional TE four | 921 | 0.7101 | 0.7191 | 0.7197 |

The separate known-support binary BG-versus-known-TE KNN macro-F1 was 0.5211
for pretrained and 0.7211 for D (balanced accuracy 0.5362 and 0.7049,
respectively; n=1,281 in both cases). The full test denominator is 1,580;
the excluded non-main4 states are KNOWN_OTHER_TE 125, AMBIGUOUS_TE 120 and
UNCLASSIFIED 54. Using the same full-eight TRAIN K=2 clustering and scoring
only known-support binary truth gave ARI 0.0118/NMI 0.0127 for pretrained and
0.2181/0.1851 for D. These binary rows are a diagnostic of detection
decodability, while the known-five/full-eight rows retain the original class
semantics.

The D minus pretrained macro-F1 deltas are +0.1509 known-five, +0.1215
full-eight and +0.0855 conditional-TE. The corresponding train-fitted
K-means rows do not move uniformly: D improves full-eight K=8 ARI from
0.0623 to 0.1096 and known-five K=5 ARI from 0.0386 to 0.1105, while its
conditional-TE K=4 ARI is 0.0424 versus 0.0713 for pretrained. Thus the
strongest claim is improved supervised decodability after D fine-tuning,
with only partial evidence for unsupervised geometry reorganization.

Per-species known-five supervised macro-F1 (pretrained → D) was: *C. elegans*
0.2937 → 0.5385; chicken 0.3575 → 0.5516; fruit fly 0.3800 → 0.4364;
mouse 0.3151 → 0.5272; western clawed frog 0.4994 → 0.6453; zebrafish
0.4805 → 0.5887. These values are descriptive because the SIB panel is
already observed and D-training exposure is not independently audited here.

## Interpretation boundary

This result supports a matched, same-backbone statement that D fine-tuning
made broad source-state labels more decodable from pooled hidden states on
this fixed panel. It does not prove independent generalization, erase the
annotation/comparator dependence of SIB labels, or establish family-level
unsupervised discovery. The older cached SIB features used a different
special-token-inclusive pooling contract and were not reused.

This run did not add a logistic linear probe, k-mer/permutation control, new
contrastive training, or UMAP evidence. Those remain separate historical
experiments or future work; this report must not be read as a claim that the
entire explanatory-control suite has been completed.

The full machine-readable outputs are the two `metrics.json` files in this
directory; the authoritative feature arrays remain at the Baobab run root:
`/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run-12849477`.

The paired plot is available as [PNG](paired-ntv2-readout.png),
[PDF](paired-ntv2-readout.pdf) and [SVG](paired-ntv2-readout.svg), generated
directly from these two metric JSONs by the experiment's `plot.py`.
