# Traditional gene-annotation receiver readiness

The author authorized strengthening the traditional gene-annotation route on
2026-09-25. The scope and interpretation are recorded in the
[protocol](../../docs/experiments/TRADITIONAL-GENE-PIPELINE-20260925.md).

## Current state

Job **13193436** is acquiring the official `teambraker/braker3:v3.1.1` image
and will check BRAKER, AUGUSTUS and GeneMark entry points. It uses private
4-CPU/16-GB allocation, a one-hour limit, and no GPU. This is software
readiness work, not an annotation or training experiment. See [job record](jobs.json)
and the timestamped [readiness snapshot](readiness-snapshot.json). The snapshot
is still `RUNNING`; no native-entrypoint result is being claimed yet.

The existing fixed-parameter AUGUSTUS chicken pilot is scientifically
interpretable, with [all controls retained](../FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/chicken/RESULTS.md).
Its zebrafish counterpart is still running. Tiberius results remain part of
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
