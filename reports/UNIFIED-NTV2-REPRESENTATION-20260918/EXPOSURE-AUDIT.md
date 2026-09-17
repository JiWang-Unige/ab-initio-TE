# Representation panel exposure audit

Slurm `12889831` completed in 6 seconds on a private CPU-only allocation.
The audit uses the actual D TRAIN/CAL/DEV JSONL records, including the worm
TRAIN override, and all three fixed SIB representation splits. It does not
change the panel or select a favorable subset.

For the full 1,580-record SIB TEST panel:

| Species | SIB TEST records | Overlap with D TRAIN | D CAL | D DEV |
|---|---:|---:|---:|---:|
| C. elegans | 317 | 0 | 0 | 149 |
| chicken | 150 | 3 | 0 | 0 |
| zebrafish | 363 | 0 | 9 | 7 |
| mouse | 196 | 0 | 0 | 0 |
| fruit fly | 287 | species absent | species absent | species absent |
| western clawed frog | 267 | species absent | species absent | species absent |

Every overlapping TEST record is fully covered by the relevant D interval,
and every overlapping base matches the recorded D input sequence exactly.
Thus three TEST records have direct D training exposure; nine have CAL
exposure; 156 have prior DEV exposure. These roles are not interchangeable:
CAL/DEV exposure is not a gradient-training example, but it prevents treating
the entire panel as untouched evidence relative to prior model development.

This updates the earlier “coordinate overlap unresolved” status. The panel
supports a retrospective matched representation diagnostic, not an
independent estimate of generalization or proof against memorization.
No coordinate overlap does not establish sequence-homology or pretraining
independence. The denominator here is the full eight-state 1,580-record
panel, not the 1,281-record known-five binary readout subset.

Native details, including every overlapping record and all panel splits:
[exposure-audit.json](exposure-audit.json). The prospective class-map quality
comparison remains on the separately fixed chr10/chr20 targets outside
actual D TRAIN/CAL/DEV chromosome exposure.
