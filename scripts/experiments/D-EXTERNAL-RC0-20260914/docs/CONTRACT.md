# D external evaluation and RC0 contract

Date: 2026-09-14. This is a bounded execution contract and engineering record. It
does not contain external model scores.

## Fixed inputs

The primary model is the preselected D seed42 checkpoint:

```
outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model
outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1/calibration.json
.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species
```

All paths are relative to the remote project root
`/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE`. The calibration remains
the six-species CAL fit and its recorded threshold is used without refitting or
target-species selection. No model training or new seed is part of this run.

The exact public inputs are the three already repaired Label-A preparation
products and their matching assembly FASTAs. The first four rows are selected
from each assembly report using the accession column that the FASTA actually
uses: RefSeq accessions for the two GCF assemblies and GenBank accessions for
the GCA CB4 assembly. Thus CB4 deliberately uses `FR847112.2`, etc.; it is not
silently replaced by the RefSeq `NC_013489.2` aliases.

| candidate | assembly | sequences used | label product |
| --- | --- | --- | --- |
| platypus | GCF_004115215.2 / mOrnAna1.pri.v4 | NC_041728.1--NC_041731.1 | labela-12664906-0 |
| sea urchin | GCF_000002235.5 / Spur_5.0 | NW_022145594.1, NW_022145605.1, NW_022145609.1, NW_022145610.1 | labela-12664906-1 |
| *C. briggsae* | GCA_000004555.3 / CB4 | FR847112.2, FR847113.2, FR847114.2, FR847118.2 | labela-12522308-2 |

The full input paths and assembly-report lengths are in `config/panel.json`.
The source directory is
`software_outputs/L1-PANEL-PREP-20260908-kqZrej`. The two original
Matrix-error products (`labela-12522308-0` and `labela-12522308-1`) are excluded.

For every listed sequence, the only evaluated interval is the centered
1,048,576-bp slice recorded in `panel.json`. Its start is
`(assembly_length - 1048576) // 2`, computed from the assembly report before any
model output or label inspection; there is no score-based region selection.
Each sequence therefore contributes 256 non-overlapping 4,096-bp windows. The
sea-urchin sequences are unplaced scaffolds in Spur_5.0; they are not relabelled
as chromosomes.

The interval start is `(assembly_length - 1048576) // 2`, computed only from the
assembly report; each centered interval is then frozen in `panel.json`. This
avoids choosing a fixed offset that can overrepresent subtelomeric sequence,
while remaining label and score blind. The centered slice still is not a
random genome sample and its representativeness is unknown. The panel is
deliberately finite and exploratory. It tests a fixed D carry-forward and RC
consistency on the same input. It is not a substitute for a whole-genome
external evaluation.

## Feedback and independence audit

The inspected panel-preparation tree contains the three repaired Label-A outputs,
their status and run metadata, but no per-candidate D inference, calibration,
DEV score or model-selection feedback artifact. *C. briggsae* appears in older
planning documents; that is retained as a possible exposure history and is not
rewritten as proof of an untouched species. The audit therefore closes the
available project-record question for this panel, but cannot prove absence of
pretraining exposure, TE-family homology or unpublished use outside those records.

The Label-A status is explicitly
`LABEL_GENERATION_COMPLETED_NOT_SCIENTIFIC_PASS`. RepeatMasker/Dfam-derived
annotations are a sparse comparator. The primary evaluation is T1 positive
recovery on A/C/G/T-callable bases; non-ACGT bases are excluded from that
primary endpoint and are reported as a separate N/IUPAC stratum. Precision/F1
remain undefined for unlabelled sequence. A secondary full-region T0
calculation may be emitted only as
`repeatmasker_comparator_agreement`; it is not independent biological accuracy.
No insertion identity is inferred from binary material runs.

The primary truth class filter is the existing strict Label-A rule: only
top-level `LINE`, `SINE`, `LTR`, `DNA`, `RC`, and `Retroposon` rows enter the
T1 truth. `Unknown`/`Unclassified`, question-marked or otherwise unrecognised
classes are retained in an `unknown_or_ambiguous` audit bucket. Simple repeats,
low-complexity, satellite, tandem and RNA classes are retained as
`hard_non_te`; `ARTEFACT`/`ARTIFACT` are retained as `excluded_non_te`. None of
these buckets is silently turned into a TE-positive row. The runner writes the
row, raw interval overlap bp, and non-overlapping union bp for every bucket to
`truth_repeatmasker_panel_class_audit.json`. If a fixed region has no known-TE
row, its execution can still complete, but the primary endpoint is marked
`NOT_EVALUABLE_NO_KNOWN_TE_IN_PANEL`; a zero recall in that case is not a model
failure result. The evaluator's flat-union mask and recall use the union bp.

## RC0 arms

For each fixed region, the runner projects model margins to base-pair
probabilities before any coordinate transformation:

1. `F`: forward sequence, existing 4,096-bp window and 6-mer phase.
2. `RC`: reverse-complement sequence, then reverse the projected base-pair
   vector back into forward coordinates.
3. `mean`: arithmetic mean of `F` and mapped-back `RC` probabilities.
4. `phase_mean`: arithmetic mean of `F` and one forward pass with a 3-bp
   left-context shift, which changes the window/token phase while retaining the
   same fixed region. Because the shifted input is three bases longer, it can
   require one extra tail window; this is recorded in the actual pass-window
   counts and is not claimed to be strictly equal cost.

The interval map is `[s,e) -> [L-e,L-s)`. The runner records mean absolute
`F`/`RC` probability difference, threshold flip rate, positive material bp,
material runs, boundary/run counts, N/edge strata, T1 recovery and the named
RepeatMasker comparator endpoint. `F` is cached; the mean arms use two forward
passes in total. Arithmetic RC consistency is not treated as biological
accuracy.

## Resource and stop rules

The external GPU array is at most three candidate jobs, one accelerator per job,
4 CPUs, 64 GB and four hours on `shared-gpu`. The CPU timing array uses the same
fixed panel and `--cpu` code path, at most four CPUs, 64 GB and four hours on
`public-longrun-cpu`. CPU output is timing evidence only when the job completes;
it does not replace a missing GPU score. A missing model, calibration, FASTA,
label or assembly-report path stops the job. Partial output without a final
summary is `FAILED`, never a result.

No external threshold, region, model, family mapping or method is selected after
seeing scores. Reports retain statuses and denominators for completed, failed and
out-of-scope cells.

Official assembly records are available from NCBI's assembly FTP directories:

- [GCF_004115215.2 assembly directory](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/004/115/215/GCF_004115215.2_mOrnAna1.pri.v4/)
- [GCF_000002235.5 assembly directory](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/002/235/GCF_000002235.5_Spur_5.0/)
- [GCA_000004555.3 assembly directory](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/004/555/GCA_000004555.3_CB4/)
