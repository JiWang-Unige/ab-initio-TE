# Fixed chromosome class comparison — 13180902

CPU job 13180902 completed in 170 seconds on the private partition (8 CPUs, 32 GB, no GPU). Both fixed NTv2 maps and the completed RM2 whole-genome annotations were scored on the same chr10/20 positions. EDTA remains NA for both species. The actual result and complete confusion matrices are in [result.json](results/score-recovery-20260924/result.json).

| Species | Endpoint | NTv2 class macro-F1 | RM2 macro-F1 | Difference |
| --- | --- | ---: | ---: | ---: |
| Chicken | Primary BG + main four TE classes | 0.625913 | 0.609440 | +0.016474 |
| Zebrafish | Primary BG + main four TE classes | 0.760377 | 0.688569 | +0.071807 |
| Chicken | Full eight-state endpoint | 0.446293 | 0.434748 | +0.011546 |
| Zebrafish | Full eight-state endpoint | 0.463252 | 0.457081 | +0.006171 |
| Chicken | Conditional true-main-four TE | 0.641398 | 0.654189 | −0.012790 |
| Zebrafish | Conditional true-main-four TE | 0.786190 | 0.711482 | +0.074708 |

Primary known-five support is 34,478,839 bp for chicken and 95,026,056 bp for zebrafish. Full callable support is 34,515,527/100,505,689 bp. Conditional true-TE support is 1,485,085/41,938,694 bp. Corresponding denominators match exactly between methods. NTv2 result objects are unchanged from the completed NTv2-only score 13180671.

Primary known-five per-class F1, under its fixed source-row denominator:

| Species / method | BG | SINE | LINE | LTR | DNA |
| --- | ---: | ---: | ---: | ---: | ---: |
| Chicken NTv2 | 0.991170 | 0.251809 | 0.848604 | 0.624628 | 0.413354 |
| Chicken RM2 | 0.983412 | 0.353797 | 0.809192 | 0.472353 | 0.428444 |
| Zebrafish NTv2 | 0.901428 | 0.715361 | 0.587482 | 0.747530 | 0.850082 |
| Zebrafish RM2 | 0.873814 | 0.309565 | 0.731082 | 0.699724 | 0.828662 |

NTv2 has a higher primary macro-F1 in both fixed species, but the advantage is not uniform across classes: RM2 is better on chicken SINE/DNA and zebrafish LINE. Chicken conditional-TE macro-F1 is also lower for NTv2. Full-eight differences are small, and NTv2 has zero recall for source AMBIGUOUS_TE/UNCLASSIFIED in both species and KNOWN_OTHER_TE in zebrafish. RM2 retains nonzero performance for zebrafish KNOWN_OTHER_TE (F1 0.279612) and UNCLASSIFIED (0.008954). This supports a bounded main-class annotation result, not a solved open-set or universal TE-map claim.

The full-eight matrix always preserves eight rows/columns; macro averages only source-supported classes under the frozen implementation (seven in chicken, eight in zebrafish). Primary precision excludes other source states by design. Conditional true-TE precision excludes background by design and cannot be presented as whole-genome annotation precision.

Both species are fine-tuning species; chr10/20 were absent from the observed D TRAIN/CAL/DEV chromosome manifests. The comparison is same-species chromosome transfer against same-assembly UCSC RepeatMasker, not independent biological truth or unseen-species generalization. The class head and binary D have different weights/tasks, so the class result does not establish the binary D mask's material recall or downstream gene utility. RM2 discovery used the whole assembly, followed by classification with the fixed Dfam 4.0 asset and masking; it is a de novo discovery workflow with explicit reference knowledge at classification.

The RM2 descriptive GFF-summary error documented in the whole-genome report did not affect this score: `native_method()` passes `annotation.out` to `parse_rm2()`, while the summary file is only checked for existence. Raw class counts, native Unknown rows, normalized maps and all native failures remain recorded. No seed, threshold, class denominator, chromosome or native classification rule was changed after observing scores.
