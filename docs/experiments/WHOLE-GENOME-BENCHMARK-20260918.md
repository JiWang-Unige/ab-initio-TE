# Whole-genome benchmark: chicken and zebrafish

**Experiment:** `WHOLE-GENOME-BENCHMARK-20260918`

**Protocol status:** frozen before native execution; result claims remain closed until terminal manifests and label-source audits are complete.

This benchmark closes the gap between the earlier 1-Mb/4-Mb feasibility tests and a whole-assembly comparison. The primary animal is *Gallus gallus* galGal6, for which the repository already contains the complete FASTA and a same-assembly UCSC `rmsk.txt.gz` layer. The second assembly is *Danio rerio* danRer11, selected from the existing same-assembly high-coverage reference and label assets. Both species were fixed before reading any new native output. The older *Drosophila simulans* positive-only asset remains an external-evidence result outside this primary accuracy matrix.

The core native methods are EDTA 2.3.0 and RepeatModeler2 2.0.9 followed by RepeatMasker 4.2.4. Each receives the complete assembly with unchanged contig boundaries. RM2 performs one library discovery over the full input and then one masking pass with the complete native `consensi.fa.classified` library, including Unknown entries. RepeatMasker 4.2.4 documents four RMBlast cores per `-pa` worker, so the frozen native masking call explicitly selects `-e rmblast -pa 4` under the 16-CPU allocation. EDTA runs its frozen native `EDTA.pl` workflow with `--species others`, `--sensitive 1`, `--anno 1`, `--overwrite 1`, and 16 threads, without a curated library, CDS input, or exclude BED. EDTA's native workflow combines discovery and annotation, so its timed stage is reported as one combined native stage. The versions, commits, images, source overlay, and exact commands are recorded in `configs/WHOLE-GENOME-BENCHMARK-20260918.json`.

The frozen D model is run on the identical full FASTA for both CPU and RTX 3090 inference. It uses the existing six-species CAL calibration, 4,096-bp non-overlapping windows, batch size 12, and the already fixed threshold. D produces binary material runs and cannot be interpreted as a family map. GPU and CPU timings are separate deployment measurements; neither is ranked against the native discovery pipelines as though they were the same task. The CPU feasibility pilot uses the first 1,048,576 bp of the explicitly frozen `chr1` primary record for each species. This avoids silently selecting the short alternate scaffold that precedes `chr1` in danRer11; a missing or short named pilot record is an engineering failure.

Every native runner records lightweight input/software file metadata, command-line identity, discovery walltime and peak RSS, masking walltime and peak RSS, end-to-end walltime and peak RSS, output paths, library record counts, class/family counts, and Unknown counts. The D runner records model-load, forward, write, walltime, peak RSS, callable bp/s, device and batch size. The scoring step calculates union and overlap on 0-based half-open coordinates and keeps all class categories, including Unknown. It never uses labels to select calls or filter native libraries.

The score geometry is fixed before scoring: `Unknown`, `?`, and `ARTEFACT`
comparator rows remain in the audit but are excluded from both positive truth
and negative callable truth. The denominator is A/C/G/T sequence after that
exclusion, with raw FASTA length and excluded uncertain bp reported separately.
Each species has its own whole-assembly and D-independent chromosome strata.
GFF parsing retains EDTA's `repeat_region` material span and skips its child
subfeatures (such as LTR and target-site rows), while excluding rRNA and
target-site rows. RM2 is parsed from its native `.out` class column: LINE,
SINE, LTR, DNA, RC, Retroposon, and Unknown are retained, while simple,
low-complexity, satellite, and RNA classes are excluded. Native class/family
output is reported as a composition audit; this binary score makes no class
confusion or class precision claim, and D is class N/A.

The same-assembly RepeatMasker layers are valuable for assessing label coverage and comparator agreement, but they are not independent exhaustive biological truth. Therefore the main accuracy table is explicitly labelled comparator-relative. The *D. simulans* layer is source-dependent and supports positive-layer recall/agreement analyses only. A high comparator F1 cannot be described as complete annotation, and a disagreement cannot by itself identify a false positive or a false negative.

For the D accuracy claim, the benchmark uses the actual checkpoint exposure audit recorded in `configs/WHOLE-GENOME-BENCHMARK-20260918.json`. The D training manifests contain chicken `chr2/chr3/chr4/chr7/chr8` and zebrafish `chr1/chr3/chr4/chr7/chr9`; the calibration and model-selection DEV manifests contain chicken `chr1/chr5/chr6` and zebrafish `chr2/chr5/chr6`. The D-independent chromosome stratum is therefore fixed as chicken `chr10/chr20` and zebrafish `chr10/chr20`, before score inspection. This is a conservative chromosome-level audit: unresolved homologous or historical exposure is reported as a caveat rather than silently treated as absent. The SF5 chromosome contract is retained only as a retrospective secondary stratum and is not called D-independent. Native discovery and timing still receive the complete assembly, while D class/family is N/A because this frozen model emits binary material runs.

## Submission plan

1. Validate both complete FASTA inputs, source labels, exact versions, and the frozen model/calibration paths.
2. Submit chicken EDTA and chicken RM2 as CPU-only jobs on `private-teodoro-gpu`, with identical 16-CPU/128-GB allocations and no GPU request.
3. Run a fixed 1-Mb D CPU pilot before committing to full-assembly CPU inference. The pilot is an empirical feasibility check; it cannot be reported as a whole-genome runtime. Submit a full CPU cell only when the pre-specified linear feasibility estimate from the pilot is within the private seven-day ceiling; otherwise record CPU as resource-limited while retaining the pilot as the measured CPU deployment datum. The estimate is never presented as a measured whole-genome runtime.
4. Submit the two D inference modes on chicken and danRer11 with the frozen model, subject to the pilot decision.
5. Submit the danRer11 EDTA/RM2 cells with the same native resource contract.
6. Run one score job only after all terminal native and D cells are reconciled. Failures and timeouts remain in the cell registry and are not converted to zero scores or silently replaced.

## Current status

This document is the pre-run contract. Native and D job IDs, terminal statuses, lightweight file metadata, and compact result summaries will be appended under `reports/WHOLE-GENOME-BENCHMARK-20260918/`. A submitted job is not a completed result; any scheduler timeout, native empty output, or missing label segment remains visible.

## Interpretation boundary

The benchmark supports a transparent whole-assembly comparison of the frozen callers under the stated input and resource contracts. It can test whether the sequence-only model's callable material and runtime are useful relative to native discovery pipelines and how outputs agree with existing same-assembly labels. It does not establish universal TE truth, an all-species F1 predictor, or a claim that either label source is complete. Native algorithm randomness and internal parallelism are recorded as supplied by each tool; identical CPU allocation and input do not make their stochastic procedures mathematically identical.
