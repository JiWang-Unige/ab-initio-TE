# Long-benchmark score replay

`score_replay.py` is a standalone Python 3 standard-library script for the
arithmetic part of the long-input benchmark. It reuses the metric calculation
from [`benchmarks/te_omnibenchmark/long_panel.py`](https://github.com/JiWang-Unige/ab-initio-TE/blob/14386820c45ea617127dbefc4f5d293749347f3f/benchmarks/te_omnibenchmark/long_panel.py),
but imports no research-repository code and runs no native annotation caller.

Download the public input bundle linked below, then run from the installed
candidate directory with explicit input and output paths:

```sh
python3 benchmark/score_replay.py \
  --bundle /path/to/downloaded/result.json \
  --output replay-12739923.json
```

The public input bundle is the validated score artifact at
[`score-12739923/result.json`](https://github.com/JiWang-Unige/ab-initio-TE/blob/14386820c45ea617127dbefc4f5d293749347f3f/reports/TE-LONG-BENCH-20260915/score-12739923/result.json).
The original workflow is [`long_panel.yaml`](https://github.com/JiWang-Unige/ab-initio-TE/blob/14386820c45ea617127dbefc4f5d293749347f3f/benchmarks/te_omnibenchmark/long_panel.yaml),
and the accepted Omnibenchmark replay is documented in the
[`omni-12739923` report](https://github.com/JiWang-Unige/ab-initio-TE/blob/14386820c45ea617127dbefc4f5d293749347f3f/reports/TE-LONG-BENCH-20260915/omni-12739923/README.md).

## What the replay reproduces

The command recomputes all **14 planned cells** from validated per-block
sufficient statistics: **13 `COMPLETED` qualified cells and one `FAILED` cell**
(CB4 EDTA). The failed cell retains `metrics: null`; it is not converted to a
zero score. The output matches the accepted replay's counts, metric values,
failure status and nulls. It also retains native wall time and CPU/GPU
provenance as separate historical fields. Those fields describe the recorded
native runs and are not measured by this local command.

This is a CPU arithmetic replay, not a speed benchmark and not a rerun of the
five native callers. It does not establish independent biological truth,
absolute CB4 precision/F1, or L3 insertion identity. No DNA, model weights,
probability arrays, containers or reference libraries are bundled here.
Historical `source_attempt`, command and HPC path fields are provenance only;
they are not required to exist and must not be edited to run the replay.

## Boundary for a future portable native benchmark

The current candidate should not be advertised as a fully portable native
benchmark. A future native release still needs the following concrete inputs
and runtime assets:

* the qualified `sim100` and CB4 input FASTA/reference artifacts and their
  denominator metadata, rather than path-only references;
* the exact caller containers and versions used for RepeatMasker, RepeatModeler2,
  HiTE, EDTA and EarlGrey, including their Dfam/library and lineage-library
  inputs;
* the licensed D checkpoint, tokenizer, calibration and CPU/GPU inference
  wrapper;
* portable parsers for each caller's output format plus the frozen block-count
  and callable-denominator checks; and
* a fresh run of all 14 native cells on declared CPU/GPU hardware, preserving
  the separate native CPU and model GPU timing endpoints.

Until those inputs are packaged and the native callers are rerun, this
directory provides reproducible score aggregation only.
