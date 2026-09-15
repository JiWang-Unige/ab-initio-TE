# P3 external Tiberius smoke recovery

Date: 2026-09-15 (Europe/Zurich)

The original smoke array `12732021_[0,20]` failed before any Tiberius model call. Both cells stopped at the first `U_soft` container launch with exit code 255 from Singularity:

```text
destination /opt/Tiberius/model_weights/tiberius_nosm_weights_v2 doesn't exist in container
```

The host Tiberius checkout was bound to `/opt/Tiberius`, hiding the image's `model_weights` tree. The nested checkpoint bind therefore had no target. This is a shared container-interface failure; it is not a scientific result and does not indicate a cow/platypus difference.

Failed outputs were preserved unchanged at:

`outputs/P3-TIBERIUS-EXTERNAL-20260915/run-r1-failed-12732021/{cow,platypus}/c00`

The bounded repair creates the nested target directory before each cell's container launch. A remote lightweight Singularity check confirmed that the staged official no-soft checkpoint is visible at the original target path. The local and remote `run_core.py` contain this repair.

The same-protocol smoke retry is `12735505_[0,20]`, using the original inputs, frozen P3/Tiberius checkpoints, threshold, and 1×3090/8 CPU/96 GB/6 h cell budget. At this record, it is pending GPU resources and has no scientific result. Full array `12732547_[0-39%2]` was updated with `afterok:12735505` and remains gated; score `12732548` remains downstream of full. No full cell should run until both smoke cells complete all five arms and pass the runner's qualification checks.
