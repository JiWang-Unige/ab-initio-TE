# Length diagnostic repair record

## Observed failure

The original length branch in extraction job `12889676` stopped at
`target_pool()` with `target span coverage mismatch: covered=0, target=512`.
This was a real engineering failure, not a scientific length result. The
three-arm SIB extraction had already completed successfully before the bounded
length branch ran and remains valid.

## Root cause

The source record target is the fixed central span `[1792,2304)` in a 4,096-bp
record. The code computed `left_flank=(L-512)/2` and sliced the source at that
offset, but passed `TARGET_START-left_flank` as though the slice began at the
source target center. Consequently, the 512-bp input was `[0,512)` while the
pool target was `[1792,2304)`, the 2,048-bp input began at 768 rather than
1,024, and the 4,096-bp input attempted a slice beyond the source end.

## Repair

`extract_length_context.py` now computes separate source and context-local
coordinates around the fixed target:

| context length | source slice | local target slice |
|---:|---|---|
| 512 | `[1792,2304)` | `[0,512)` |
| 2048 | `[1024,3072)` | `[768,1280)` |
| 4096 | `[0,4096)` | `[1792,2304)` |

The script asserts that each slice has the requested length and that its local
target sequence equals the fixed source target before any model call. The
Baobab `te_benchmark` synthetic fixture passed all three checks and remote
Python compilation passed. The original blocked output is preserved.

## Retry submission

Length-only GPU job `12897975` uses `private-teodoro-gpu`, one GPU, four CPUs,
32 GB, and 45 minutes. Its fresh output is
`outputs/UNIFIED-NTV2-REPRESENTATION-20260918/length-retry-12897975`.
CPU evaluator `12897980` depends on `afterok:12897975` and uses the same
private partition without any GPU request (four CPUs, 16 GB, 15 minutes;
partition explicitly overridden at submission). The three weights, fixed
record identities, target labels, contexts, and readout settings are unchanged.
No SIB extraction or model training was rerun. The retry completed with
`PASS_EXTRACTION`; the CPU evaluator completed with `PASS`. All three models
x three contexts have 768 finite feature rows, 768 labels, and 768
composition rows, and the target-pooling assertion passed for every record.
Full readouts are in `LENGTH-RETRY-RESULTS-12897975.md`. Both the original
failure and retry costs remain part of the record.
