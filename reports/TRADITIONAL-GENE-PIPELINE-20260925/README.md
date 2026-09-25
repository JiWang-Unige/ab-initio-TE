# Traditional gene-annotation receiver readiness

The author authorized strengthening the traditional gene-annotation route on
2026-09-25. The scope and interpretation are recorded in the
[protocol](../../docs/experiments/TRADITIONAL-GENE-PIPELINE-20260925.md).

## Current state

**`ENTRYPOINTS_READY` — bounded preparation completed.** The official
`teambraker/braker3:v3.1.1` OCI image was unpacked, but job **13193436**
timed out after 3,000 s while packaging the SIF (Slurm elapsed 3,002 s).
The [original failure](readiness-13193436.json) and [log excerpt](pull-13193436-excerpt.log)
are retained. No finished SIF is claimed.

Recovery **13193511** reused that extracted directory directly as an
Apptainer sandbox. It requested only 590 s of the original one-hour budget's
remaining 598 s and completed in **7 s**, without another pull or compression.
Both jobs used private 4 CPU/16 GB and no GPU. Cumulative allocated time is
**3,009 s (50m09s; 3.3433 allocated CPU-hours)**, including the failure.
See [job record](jobs.json), [native status](native-13193511/status.json),
and the timestamped [readiness snapshot](readiness-snapshot.json).

The actual programs report **BRAKER 3.0.8** and **AUGUSTUS 3.5.0**; the
container tag `v3.1.1` must not be substituted for the measured BRAKER version.
The GeneMark executable path `/opt/ETP/bin/gmetp.pl` is present. Version
commands returned 0 and their outputs were read; GeneMark was only located,
not trained or otherwise functionally exercised. The full workflow's
dependencies/licensing and mask consumption are still untested.

The reusable artifact is the original extraction directory
`outputs/TRADITIONAL-GENE-PIPELINE-20260925/preflight-13193436/tmp/build-temp-1854282490/rootfs`
on Baobab. Retain this directory despite its historical `tmp` parent name;
the native command records point to it. No container data are exported to Git.

The existing fixed-parameter AUGUSTUS chicken pilot is scientifically
interpretable, with [all controls retained](../FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/chicken/RESULTS.md).
Its zebrafish counterpart has also [completed](../FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/zebrafish/RESULTS.md).
Tiberius results remain part of
the evidence; the official preference for unmasked weights does not invalidate
all softmask-aware experiments or establish that a traditional receiver is
more accurate.

## What must be fixed before a full BRAKER comparison

- One evidence mode, identical genome/RNA/protein inputs and resource limits
  for all mask arms. Use full RM2-to-RepeatMasker and whole-genome RED as
  realistic alternatives; the historical panel-only RED result is distinct.
- An evaluation set independent of the RNA/protein evidence supplied to
  training or hints. The existing platypus RNA library cannot serve both
  roles in the same comparison.
- Whether the endpoint is a fixed-receiver mask effect or a complete workflow
  effect including GeneMark/AUGUSTUS training. Do not conflate the two.
- Independent host complete-CDS and autonomous-TE evidence sufficient for the
  proposed functional-selectivity claim. Current evidence readiness does not
  satisfy this requirement; general annotation F1 alone cannot replace it.

No full-genome BRAKER run, new model training, species expansion or large RNA
download has started under this protocol. Version/entrypoint success will not
be treated as training, licensing, mask-consumption or accuracy validation.
