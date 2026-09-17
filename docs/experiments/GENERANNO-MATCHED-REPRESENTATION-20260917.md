# GENERanno matched representation diagnostic

Date: 2026-09-17

This is a bounded, inference-only comparison of three frozen GENERanno
checkpoints on the exact SIB `data_512` panel already used by the NTv2 matched
representation experiment:

* untouched `GENERanno-eukaryote-0.5b-base`;
* the existing binary TE/background token-classification checkpoint
  `TFSUPP_generanno_H0_w4096_seed42/best_model`;
* the existing eight-state SF5 token-classification checkpoint
  `SF5_ONTOLOGY_CLOSURE_base_seed42_12731987/best_model`.

All three arms use the untouched pretrained GENERanno tokenizer, maximum
length 2048, and mean pooling over attended tokens after excluding structural
special tokens (BOS/EOS/PAD/MASK). GENERanno declares the ambiguity symbol `N`
as `unk_token`; `N` is retained as sequence content because the fixed panel
contains all-`N` windows that would otherwise have no poolable token. The panel
is fixed at 1,843 train, 809
validation, and 1,580 test records; no record or label is changed. The common
CPU evaluator reports the predeclared known-five, full-eight, conditional
four-class TE, and known-support binary endpoints. Its kNN scores are
supervised train-fitted readouts. Its K-means scores are unsupervised
train-fitted geometry diagnostics; neither endpoint uses test labels to select
K. `UMAP` is not a primary endpoint.

This is a matched GENERanno comparison, not a re-run of the NTv2 extraction.
NTv2 uses its own tokenizer and model-specific token IDs; GENERanno maps `N`
to `unk_token` (ID 37 in this checkpoint). Accordingly, the GENERanno contract
excludes only structural BOS/EOS/PAD/MASK IDs and keeps `N` as sequence content.
The common SIB records and evaluator make the endpoint definitions parallel,
but hidden vectors from the two tokenizers are not numerically interchangeable.

The saved split metadata gives a useful, limited exposure check. The binary
checkpoint was trained on human chromosomes 1, 3, 5, 7 and 9, whereas the SIB
panel contains no human records. For the SF5 checkpoint, each SIB test species
uses the chromosome recorded as that species' SF5 test chromosome (mouse X,
zebrafish 5, chicken 3, western clawed frog 5, fruit fly 2R and *C. elegans*
IV), disjoint from the corresponding SF5 training chromosome. Thus no
species-plus-chromosome overlap is detected from the saved split metadata.
This is not a homology or repeated-copy audit; homologous sequence exposure
remains unresolved.

The experiment can support a statement about how broad-class decodability and
raw feature geometry change across the three checkpoints on this comparator
panel. It cannot by itself establish absence of homologous-copy exposure or
biological TE truth. The coordinate-level result above is a split-level check,
not proof of independent sequence novelty.

The final report also includes a descriptive input-symbol audit for each fixed
split: total all-`N` windows, their label distribution, and non-ACGT bases and
records. These observations remain in the panel and are not dropped or
relabelled; the audit does not establish that they are representative of other
genomes.

The extraction script and Slurm wrapper are in
`scripts/experiments/GENERANNO-MATCHED-REPRESENTATION-20260917/`. The wrapper
invokes the already-reviewed evaluator in
`scripts/experiments/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/` and does not
train models or alter sealed checkpoints. The wrapper supports `MAX_RECORDS=8` for a bounded loader smoke; this is
not a scientific endpoint. The actual final full run was job `12854214`,
which completed extraction and evaluation in 23m09s. Initial full-run attempts
`12853107` and `12854043` failed on output extraction and N-token pooling,
respectively; the fixed full run preserves every original sample. See
[results and attempt history](../../reports/GENERANNO-MATCHED-REPRESENTATION-20260917/run-12854214/RESULTS.md).
