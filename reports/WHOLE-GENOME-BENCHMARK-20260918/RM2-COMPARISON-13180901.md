# Completed RM2 comparison — 13180901

RepeatModeler2 discovery, classification and full-input RepeatMasker annotation have completed for both fixed species. Mask-only jobs 13180772/13180877 ended successfully in 2h12m28s/8h40m19s and produced native `.out`, GFF, masked FASTA and classified libraries. CPU score 13180901 completed in 121 seconds; its two EDTA rows remain NA, so this is a completed RM2 comparison rather than a complete three-method benchmark.

## Binary material endpoint

| Species | Fixed stratum | D precision | D recall | D F1 | RM2 precision | RM2 recall | RM2 F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Chicken | Independent chr10/20 | 0.938901 | 0.321670 | 0.479174 | 0.594979 | 0.849583 | 0.699844 |
| Zebrafish | Independent chr10/20 | 0.815321 | 0.951810 | 0.878294 | 0.799611 | 0.958290 | 0.871789 |
| Chicken | Whole assembly | 0.972136 | 0.392693 | 0.559412 | 0.677663 | 0.909158 | 0.776525 |
| Zebrafish | Whole assembly | 0.806360 | 0.948686 | 0.871752 | 0.786937 | 0.951263 | 0.861332 |

The independent-chromosome F1 difference D−RM2 is −0.220670 in chicken and +0.006505 in zebrafish. Chicken D is more conservative: higher comparator-relative precision accompanies substantially lower recall. Zebrafish is close in F1, with D precision higher and recall slightly lower. These are descriptive results from the fixed runs, not a demonstrated general or statistically significant superiority.

Whole-assembly rows include training/model-selection chromosomes. The independent chr10/20 stratum was fixed using D TRAIN/CAL/DEV exposure manifests; both species themselves were used in fine-tuning. UCSC RepeatMasker is a comparator, not exhaustive biological truth. Unknown/question-mark/ARTEFACT source intervals stay excluded from binary truth as specified before scoring. Native Unknown predictions remain candidate TE material. No threshold, species or denominator was changed.

The frozen RM2 binary parser admits LINE/SINE/LTR/DNA/RC/Retroposon and Unknown roots; it is not an all-native-label union. Zebrafish emits 6,068 `PLE` rows outside that explicit list, preserved in the native audit but not admitted by this binary endpoint. The class pipeline instead retains these as UNCLASSIFIED (414 target-chromosome rows). This pre-existing mapping difference is disclosed rather than changed after seeing the small F1 difference. It further limits any assertion of broad binary superiority or equivalence between binary and class-derived TE unions.

## Cost boundary

| Completed workflow | Allocated CPUs | GPU | Slurm elapsed used here |
| --- | ---: | --- | --- |
| Chicken RM2 discovery + classification/mask recovery | 16 | none | 137,916 s = 38h18m36s |
| Zebrafish RM2 discovery + classification/mask recovery | 16 | none | 128,945 s = 35h49m05s |
| Chicken D full-input CPU inference | 16 | none | 398,344 s = 110h39m04s |
| Chicken D full-input GPU inference | 8 | RTX3090 | 17,242 s = 4h47m22s |
| Zebrafish D full-input GPU inference | 8 | RTX3090 | 27,116 s = 7h31m56s |

RM2 totals retain original discovery and the failed initial classification/mask continuation: chicken 129,491 + 477 + 7,948 seconds; zebrafish 96,792 + 934 + 31,219 seconds. Shared tiny environment probes and common scoring are engineering/evaluation costs recorded separately. D rows are full inference jobs, excluding pretraining/fine-tuning, calibration and earlier CPU feasibility pilots; their history remains in the existing reports. All CPU-only native/full-D cells had 128 GB limits. GPU jobs had different hardware and 96 GB limits and must stay separate.

Chicken D CPU inference alone took about 2.89 times the observed RM2 complete workflow allocation. Thus these data do not support a CPU speed advantage. GPU deployment is faster in these runs, but that comparison changes hardware and does not establish algorithmic superiority or equal-budget training cost. Full zebrafish CPU inference was not run under the predeclared feasibility rule.

## Integrity and compact export

Binary scores parse native `annotation.out` directly; the class scorer does the same. The descriptive `annotation_summary.json` originally misread the RM GFF `Target "Motif:..."` attribute as a class, generated spurious family keys, and merged per-class coordinates across contigs. Those descriptive fields were corrected by CPU job 13189316 (70 seconds), retaining the original versioned GFF summary and corrected sidecars. They never supplied predictions, comparator labels or denominators to either scientific scorer.

The complete original score remains on Baobab at `outputs/WHOLE-GENOME-BENCHMARK-20260918/score-recovery-20260924/result.json`. The [compact export](score-recovery-20260924/result.compact.json) excludes only that invalid `native_composition` section and explicitly records the omission; [metrics.tsv](score-recovery-20260924/metrics.tsv) is unchanged. All eight binary F1 values agree with raw TP/FP/FN, and both D result objects are exactly unchanged from 13180826. No native annotations or completed score values are rewritten to repair the descriptive metadata.

Chicken EDTA recovery 13180896 failed during checkpoint-file validation before running TIR. Its 306 seconds and original error are preserved; the authorized filename correction is continuing in a fresh attempt. Zebrafish EDTA remains OOM/NA. A later EDTA-complete comparison must use a new score output directory and keep this result.
