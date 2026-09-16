# EDTA terminal evidence

Protocol: `TE-LONG-BENCH-20260915`
Corrected retry: Slurm array `12738464`
Source recovery outputs: `native-12738464`

| Cell | Slurm result | EDTA result | Compact evidence |
| --- | --- | --- | --- |
| `c_briggsae` | `12738464_0` (raw JobID `12738465`) `FAILED`, `00:22:22`, Slurm exit `1:0`; native EDTA exit 255 | **FAILED** | `LTR.raw.fa`: 13 records / 28,305 B; `LTR.intact.raw.fa`: 0 records / 0 B; `TIR.intact.raw.fa`: 1,154 records / 1,762,574 B; `Helitron.intact.raw.fa`: 53 records / 479,188 B. Default EDTA gate rejects the cell because both LTR files must be non-empty. |
| `sim100` | `12738464_1` (raw JobID `12738464`) `COMPLETED`, `01:03:10`, Slurm exit `0:0` | **COMPLETED** | `panel.fa.mod.EDTA.TEanno.gff3`: 22,332,849 B; adapter `predictions.tsv`: 123,471 rows / 25,306,221 B. |

CB4 remains a failed full-method cell. No `--force`, new input, new budget, or
accuracy-based method selection was used. The original failures and both
recovery attempts remain preserved.
