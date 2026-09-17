# GENERanno matched representation results

Status: `PASS_MATCHED_GENERANNO_REPRESENTATION`

The three frozen GENERanno checkpoints were evaluated on the same SIB
train/validation/test panel with the same tokenizer and mean pooling
excluding structural BOS/EOS/PAD/MASK while retaining N/UNK as sequence
content. kNN is a supervised
train-fitted readout; K-means is an
annotation-filtered, train-fitted geometry diagnostic with K fixed in advance.
These results are a paired representation diagnostic, not an independent
biological truth or homologous-copy-free generalization test.

| checkpoint | dim | known-5 kNN F1 | full-8 kNN F1 | TE-only kNN F1 | binary kNN F1 | known-5 K5 ARI | full-8 K8 ARI | TE-only K4 ARI | binary K2 ARI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pretrained | 1280 | 0.3654 | 0.2748 | 0.4746 | 0.5221 | 0.0247 | 0.0287 | 0.0417 | 0.0339 |
| binary_finetuned | 1280 | 0.4329 | 0.3123 | 0.4990 | 0.6192 | 0.0798 | 0.0634 | 0.0693 | 0.0033 |
| multiclass_finetuned | 1280 | 0.7674 | 0.6857 | 0.9030 | 0.7164 | 0.3334 | 0.2475 | 0.2429 | 0.1686 |

The saved split metadata finds no species-plus-chromosome overlap between
the binary training source and this panel, and no overlap between SF5
training chromosomes and the SIB test chromosomes. Homologous-copy exposure
was not audited. `KNOWN_OTHER_TE`, `AMBIGUOUS_TE`, and `UNCLASSIFIED` remain
separate full-eight states; they are not relabelled as BG.

The binary checkpoint used human-only training; SF5 used six-species
eight-state training. This comparison does not isolate the causal effect of
the training objective from data composition or exposure. Pretrained binary
5-NN macro-F1 of 0.5221 does not establish strong TE/BG separation before
fine-tuning. The positive interpretation is stronger label decodability and
class-aligned geometry after the existing multiclass training, under this
fixed diagnostic. No new encoder or contrastive training was performed.

## Fixed-panel input symbol audit

The audit below is descriptive and leaves every sequence and label in
the frozen panel unchanged. `N` is retained as GENERanno sequence content
because its tokenizer maps `N` to `unk_token`; this is distinct from
structural BOS/EOS/PAD/MASK tokens. Non-ACGT fractions are computed over
all 512-bp records in each split.

| split | records | all-N windows | all-N labels | non-ACGT bases / total | records with non-ACGT |
|---|---:|---:|---|---:|---:|
| train | 1843 | 0 | none | 528 / 943616 (0.055955%) | 6 |
| val | 809 | 0 | none | 452 / 414208 (0.109124%) | 5 |
| test | 1580 | 1 | BG=1 | 1557 / 808960 (0.192469%) | 10 |

The all-N test windows are therefore retained observations, not dropped
or relabelled failure cases. The symbol audit does not establish whether
these windows are biologically representative of the broader species set.

## Execution and figure

Final Slurm job `12854214` completed in 23m09s (4 CPUs, 48G, one GPU).
Two prior extraction failures and their fixes are retained in [attempts.json](attempts.json).
The historical pooling identifier is a schema string; actual excluded token
IDs and retained unknown ID in `feature_metadata` define the contract.

[Paired figure (PDF)](paired-generanno-readout.pdf) / [PNG](paired-generanno-readout.png).
The figure is derived directly from `result.json`; it adds no fitting or selection.
