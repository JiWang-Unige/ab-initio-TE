# External animal closure: fixed nonmammalian vertebrate panel (2026-09-18)

## Purpose

This experiment extends evaluation of the frozen six-species D binary model
to non-supervision vertebrates with a same-assembly RepeatMasker source layer.
Species eligibility used source-annotation coverage and class-diversity gates
before inference; no model score was used. Within each eligible species, the
20 contigs and centred regions were selected by assembly length only, without
using model scores, thresholds, labels, or regional positive counts. The
earlier frog/bee/beetle screen remains historical exploratory exposure; it is
not replaced retroactively. Takifugu and zebra finch are therefore fixed
external diagnostics, not claims of a completely untouched blind test.

## Completed results

The frozen-D inference and source-layer scores are complete: jobs `12887633`
and `12887634` inferred the two fixed panels, and score jobs `12887635` and
`12887636` completed after switching to the private CPU-only allocation. The
class-specific post-hoc diagnostic is job `12889181_[0-1]`; its compact
results are in
[`class-breakdown RESULTS`](../../reports/EXTERNAL-ANIMAL-CLOSURE-20260918/class_breakdown/RESULTS.md)
and [`summary.json`](../../reports/EXTERNAL-ANIMAL-CLOSURE-20260918/class_breakdown/summary.json).

## Source and panel contract

Both assemblies use the UCSC FASTA and database RepeatMasker `.out` source
for the matching assembly, with the project legacy `.bed` source retained for
provenance. Strict positives are exact broad classes `DNA`, `LINE`, `SINE`,
`LTR`, `RC`, and `Retroposon`; classes containing `?`, `Unknown`, and
`ARTEFACT` are excluded from the strict positive layer and retained as
uncertain metadata. The positive layer is not treated as biological truth.

The selection rule is deterministic: take the 20 longest source contigs and
extract the centred 5,242,880-bp interval from each, giving 104,857,600 bp per
species. A species is qualified only when the full source contains at least
5 Mb of strict known TE, the fixed panel contains at least 0.5 Mb, at least 12
of 20 regions contain both positive and callable background sequence, and at
least three broad classes are present. These thresholds are quality gates for
an informative fixed panel, not a score-based inclusion rule.

| species | assembly | full FASTA bp | full strict-known TE union | panel bp | panel strict-known TE union | panel positive fraction | full Unknown rows | qualification |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| *Takifugu rubripes* | fr3 | 391,484,715 | 18,582,705 | 104,857,600 | 2,295,569 | 2.19% | 6,825 | QUALIFIED |
| *Taeniopygia guttata* | taeGut2 | 1,232,135,591 | 81,160,964 | 104,857,600 | 4,479,542 | 4.27% | 2,487 | QUALIFIED |

The zebra finch source also has 2,288 rows in uncertain broad classes
(`DNA?`, `SINE?`, and `LTR?`). The fixed panel has 20/20 mixed
positive/background regions and four broad classes for each species. This is
why the panel is preferable to sparse candidates: eligibility follows
assembly-matched source coverage and diversity, while Unknown/ambiguous mass
is explicitly reported.

The source assets are:

* `fr3.fa.gz`, `fr3.fa.out.gz`, `fr3.chrom.sizes`, and `rmsk_te.bed.gz` under
  `.backup/data/genome_data/current_eukaryotes/animals/torafugu/`;
* `taeGut2.fa.gz`, `taeGut2.fa.out.gz`, `taeGut2.chrom.sizes`, and
  `rmsk_te.bed.gz` under
  `.backup/data/genome_data/current_eukaryotes/animals/zebra_finch/`.

The source URLs recorded in the machine-readable qualification outputs are
the UCSC `fr3` and `taeGut2` FASTA and `database/rmsk.txt.gz` endpoints. Both
species are absent from D's six supervision species; pretraining exposure is
unknown and the project records historical transfer exposure. The resulting
claim is same-assembly source-layer recovery, not a claim that every
unannotated base is negative or that this layer is complete.

## Frozen model and execution

Inference uses D-NTv2-500M, the six-species D final checkpoint, the shared D
calibration, and the locked global threshold. Each fixed panel is inferred as
4096-bp windows with the existing FASTA inference implementation. The quality
and preparation stages are CPU-only on `private-teodoro-gpu`; each inference
stage uses one private GPU. The current chain is:

| stage | Takifugu | zebra finch |
| --- | ---: | ---: |
| quality | 12887623 (completed) | 12887624 (completed) |
| prepare | 12887631 (completed) | 12887632 (completed) |
| inference | 12887633 (completed) | 12887634 (completed) |
| score | 12887635 (completed) | 12887636 (completed) |

The job outputs are under
`outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/{torafugu,zebra_finch}/`. The
class-specific post-hoc CPU diagnostic reuses these outputs and does not
change the frozen threshold or calibration.

## Metrics and interpretation

The primary fixed-panel score reports strict-positive recovery, predicted
callable coverage, and the amount of prediction outside the strict source
positive layer. Because the `.out` layer contains Unknown, ambiguous, and
unannotated sequence, these quantities are kept separate from precision,
recall, and F1 claims about biological TE truth.

If a source-comparator P/R/F1 is reported, it must be labelled exactly as a
source-comparator metric: strict known classes are positives, callable bases
inside Unknown/ambiguous/ARTEFACT rows are excluded, and the remaining
callable bases are source-comparator background. This background convention
is useful for comparing a fixed source layer but cannot establish that the
remaining sequence is biologically non-TE. Positive-only recovery and this
source-comparator metric must never be pooled into one headline score.

### Completed external results

| species | callable bp | strict-known positive bp | recovered positive bp | positive-only recovery | predicted bp | no source support bp | source-comparator P / R / F1 | unknown or unlabelled callable bp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| *Takifugu rubripes* (fr3) | 101,522,896 | 2,289,458 | 1,908,739 | 0.833708 | 3,219,224 | 1,310,485 | 0.599147 / 0.833769 / 0.697250 | 99,233,438 |
| *Taeniopygia guttata* (taeGut2) | 104,279,300 | 4,476,142 | 990,248 | 0.221228 | 1,227,922 | 237,674 | 0.810570 / 0.221227 / 0.347588 | 99,803,158 |

Across the fixed 20-region panels, positive-only recovery was 0.7285--0.9043
(mean 0.7949, SD 0.0529) for fr3 and 0.1335--0.3141 (mean 0.2267, SD
0.0417) for taeGut2. The corresponding source-comparator F1 ranges were
0.5770--0.8071 (mean 0.6550, SD 0.0621) and 0.2210--0.4583 (mean 0.3484,
SD 0.0539). The transfer signal is heterogeneous and does not support a
universal nonmammalian claim.

The completed class breakdown localizes the taeGut2 recovery deficit: LTR has
2,054,042 callable source-positive bp with 1,903,242 missed (recall 0.073416),
and LINE has 2,279,570 bp with 1,485,616 missed (recall 0.348291). For fr3,
LINE is the largest class and has 1,041,649 recovered of 1,171,942 callable bp
(recall 0.888823). Class-specific intervals are independently unioned from
the original `.class` field; cross-class overlap is reported and class bp are
not summed into a strict-known total. The source layer remains a qualified
same-assembly comparator, not complete biological truth, so this diagnostic
cannot quantify how many apparent misses are unannotated TEs.

## Architecture follow-up

The existing D prediction-head pilot remains the bounded exploratory adapter
result. A new finite architecture comparison is running separately in
`D-BACKBONE-LORA-CLADE-20260918`: frozen D with query/value LoRA in encoder
layers 27 and 28, shared rank 16 versus two fixed-taxonomy rank-8 experts.
Both have 131,072 trainable parameters across four targets. The vertebrate
route covers the five vertebrate supervision species; the second route is
explicitly *C. elegans*-only. Unknown taxonomy falls back to frozen D logits.
There is no learned gate, and the experiment does not claim an unconditional
invertebrate MoE or sparse backbone routing.

Formal Slurm job `12888288` uses the first 256 complete TRAIN tiles and first
128 CAL/DEV tiles per species, seed 42, 1,024 optimizer steps per arm,
AdamW (`lr=1e-4`, `weight_decay=0.01`), LoRA `alpha=rank`, zero dropout, and
the fixed TE base-pair weight of 3.0. D historical full-CAL and fresh
six-species CAL-refit references are reported separately; each LoRA arm fits
its own CAL calibration, and DEV is touched only after the fixed steps.

The first submission (`12888116`) stopped before any adapter update because
new LoRA parameters were initially left on CPU while the frozen checkpoint
was on CUDA. The interface failure is retained in its output directory. The
repair moves the complete wrapped model to the checkpoint device before the
first forward and was resubmitted under the same contract as job `12888288`;
its output is the only source of a LoRA scientific result.

This architecture run is a controlled route-conditioned adaptation test. If
the shared arm does not improve and the worm-only route is unstable, the
direction is closed as a negative/limited architecture result rather than
expanded into a larger MoE search.

## Downstream receiver boundary

The current Tiberius vertebrate and insect configurations have
`softmasking: False`; the mammalian softmask configuration is not a valid
nonmammalian receiver. Nonmammalian gene-utility results must therefore use a
receiver with a verified native softmask contract or be labelled as an
out-of-domain diagnostic. No invalid Tiberius comparison is included in this
external panel experiment.
