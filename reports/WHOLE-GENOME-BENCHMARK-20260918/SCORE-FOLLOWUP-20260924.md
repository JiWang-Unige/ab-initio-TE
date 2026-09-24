# Follow-up scores after chicken EDTA attempt 13189201

Observed at 2026-09-24 19:29 UTC. Chicken EDTA attempt `13189201` failed
after 2,669 Slurm seconds. Its TIR stage completed successfully, including
Module 4 and postprocessing; the native checkpoint-consumption check passed.
The subsequent `edta_filter_final_annotation` stage exited 2 after 88.98 s.
There is still no terminal chicken EDTA annotation. The TIR output is an
intermediate product, not a complete EDTA comparator.

The two `afterany` follow-up scorers completed:

| Job | Endpoint | Private CPU resources | Slurm seconds |
| --- | --- | --- | ---: |
| 13189350 | whole assembly and independent chr10/20 binary | 4 CPU, 32 GB, no GPU | 103 |
| 13189351 | fixed chr10/20 class map | 8 CPU, 32 GB, no GPU | 197 |

Both output directories are named `score-edta-retry-20260924`. All binary
TSV rows and all class numeric fields are exactly unchanged from jobs
`13180901` / `13180902`. Both EDTA species remain explicit NA; the chicken
reason now points to the failed `13189201` root. The repaired RM2 native
composition is present in the binary JSON, replacing the invalid descriptive
GFF-derived metadata in the earlier snapshot without changing any scores.

The complete native JSON/TSV files are retained in the corresponding report
directories. Earlier scores and failed native outputs are not overwritten.
The successful scoring jobs do not establish a completed EDTA matrix. A
contract-preserving downstream recovery is being prepared separately: the
filter stderr identifies missing `galGal6.fa.mod.Helitron.intact.raw.fa`.
The original interruption had left the native Helitron branch unexecuted;
the previous recovery driver incorrectly jumped directly to filter after
TIR. Continuation must complete that original branch before filtering,
without `--force`, a fallback library, or recomputing the completed TIR.
The 2,669-second failed recovery leaves 434,936 seconds of the original
604,800-second native cell budget.

Continuation `13189902` is running in
`EDTA-helitron-cont-13189902` on the private partition with 16 CPU/128 GB
and no GPU. The completed TIR is reused. Binary/class score jobs
`13189916`/`13189917` wait on `afterany:13189902` and write separate
`score-helitron-cont-20260924` outputs. These submissions are not new
scientific results; unsuccessful native cells will remain NA.
