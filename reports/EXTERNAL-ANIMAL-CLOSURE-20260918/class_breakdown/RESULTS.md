# External class-breakdown diagnostic (completed)

Slurm array `12889181_[0-1]` ran CPU-only on `private-teodoro-gpu` (4 CPUs, 16G, 30 min). It reused the completed frozen-D `material_runs.bed` outputs from inference jobs `12887633` and `12887634`; no score threshold, calibration, model, species panel, or expert training was changed.

The table uses the same callable-base convention as the pooled score: only A/C/G/T are eligible and N/non-callable bases are excluded. Each strict-known broad class is independently unioned from the original RepeatMasker `.class` value. Unknown, `?`, and ARTEFACT intervals remain uncertain metadata. Cross-class overlaps are reported separately, so class rows must not be summed into one strict-known total.

| species / assembly | broad class | reference bp (callable) | recovered bp | missed bp | recall |
|---|---|---:|---:|---:|---:|
| torafugu / fr3 / Fugu rubripes v3 | DNA | 631,843 | 481,753 | 150,090 | 0.762457 |
| torafugu / fr3 / Fugu rubripes v3 | LINE | 1,171,942 | 1,041,649 | 130,293 | 0.888823 |
| torafugu / fr3 / Fugu rubripes v3 | LTR | 298,369 | 250,423 | 47,946 | 0.839306 |
| torafugu / fr3 / Fugu rubripes v3 | RC | 0 | 0 | 0 | NA |
| torafugu / fr3 / Fugu rubripes v3 | Retroposon | 0 | 0 | 0 | NA |
| torafugu / fr3 / Fugu rubripes v3 | SINE | 187,744 | 135,312 | 52,432 | 0.720726 |

*torafugu: panel=104,857,600 bp; callable=101,522,896 bp; strict-known union=2,295,569 bp; class-union sum=2,296,009 bp; cross-class overlap excess=440 bp; uncertain=320,484 bp.*

| zebra_finch / taeGut2 / WashU taeGut2 | DNA | 50,861 | 8,931 | 41,930 | 0.175596 |
| zebra_finch / taeGut2 / WashU taeGut2 | LINE | 2,279,570 | 793,954 | 1,485,616 | 0.348291 |
| zebra_finch / taeGut2 / WashU taeGut2 | LTR | 2,054,042 | 150,800 | 1,903,242 | 0.073416 |
| zebra_finch / taeGut2 / WashU taeGut2 | RC | 0 | 0 | 0 | NA |
| zebra_finch / taeGut2 / WashU taeGut2 | Retroposon | 0 | 0 | 0 | NA |
| zebra_finch / taeGut2 / WashU taeGut2 | SINE | 94,941 | 36,714 | 58,227 | 0.386703 |

*zebra_finch: panel=104,857,600 bp; callable=104,279,300 bp; strict-known union=4,479,542 bp; class-union sum=4,482,814 bp; cross-class overlap excess=3,272 bp; uncertain=76,795 bp.*

## Interpretation

The zebra-finch deficit is class-localized rather than explainable solely by comparator background: LTR is the largest strict-known callable class (2,054,042 bp) and has 150,800 bp recovered, 1,903,242 bp missed, and recall 0.073416. LINE contributes 1,485,616 missed bp at recall 0.348291; DNA and SINE are smaller (41,930 and 58,227 missed bp). Thus the low pooled recovery is dominated by LTR and secondarily LINE.

For *T. rubripes*, LINE is the largest class (1,171,942 bp) with 1,041,649 bp recovered and recall 0.888823; DNA and SINE have lower recall (0.762457 and 0.720726), but their smaller denominators do not dominate the pooled result. This class diagnostic supports a model/class-specific transfer limitation for taeGut2, while it cannot determine whether missed regions are absent from the model or absent from the source annotation.

The source layer is qualified and assembly-matched, but it is not complete biological truth. Some apparent misses may be unannotated source-layer positives; this diagnostic does not quantify that ambiguity.
