# WHOLE-GENOME-BENCHMARK-20260918

This directory contains the frozen runners for the chicken `galGal6` and zebrafish `danRer11` whole-assembly comparison. Native discovery and masking are CPU-only. The D model has separate CPU-pilot, CPU-full, and RTX 3090-full scripts. Native output is never selected using a score, and the score remains comparator-relative to the same-assembly UCSC `rmsk.txt.gz` layer.

The normal submission order is:

```bash
mkdir -p logs
sbatch --export=ALL,SPECIES=chicken,METHOD=EDTA run_native.sbatch
sbatch --export=ALL,SPECIES=chicken,METHOD=RM2 run_native.sbatch
sbatch --export=ALL,SPECIES=chicken run_d_cpu_pilot.sbatch
sbatch --export=ALL,SPECIES=chicken run_d_gpu.sbatch
```

After the chicken pilot is inspected for the fixed feasibility rule, repeat it for zebrafish and submit the corresponding full cells. A CPU full cell may be submitted only when the pilot does not exceed the seven-day budget rule; otherwise its terminal record is a typed resource limit and is not replaced by a runtime extrapolation. Use `--dependency=afterok:<jobid>` for the final score after all required native and D GPU cells are terminal.

`run_native.py` passes the complete FASTA to EDTA or to the RM2 BuildDatabase/RepeatModeler/RepeatMasker chain. RM2 uses one pooled full-assembly library including Unknown entries and RepeatMasker `-pa 4`; RMBlast documents four cores per worker, matching the 16-CPU allocation. EDTA uses one combined native discovery/annotation stage with no target curated library. `summarize_native.py` retains native broad class, family, and Unknown counts.

`score.py` reads labels only after inference, preserves Unknown comparator rows as an audit stratum, and reports whole-assembly plus pre-specified test-chromosome summaries. It does not treat comparator-relative F1 as exhaustive biological truth.
