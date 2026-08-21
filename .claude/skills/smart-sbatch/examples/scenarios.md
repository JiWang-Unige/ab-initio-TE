# Worked Scenarios

## Scenario 1: CPU-only command, 3 days

Request:

```text
Run a CPU preprocessing command for about 72h.
```

Decision:

```text
partition = private-teodoro-gpu
gpus = 0
walltime = min(72h, private available window, 7 days)
```

Reason: CPU-only jobs should use `private-teodoro-gpu` with no GPU request because other CPU nodes are time-limited.

## Scenario 2: GPU job needs 3h, private queue is 12h

Decision: use `shared-gpu` if eligible GPUs are available. Waiting 12h for private is worse than finishing in around 3h on shared.

## Scenario 3: Long checkpointable training, private has only 2 GPUs

Job facts:
- expected runtime > 12h
- checkpoints reliable
- `min_gpus=2`
- `efficient_min_gpus=4`
- private has only 2 GPUs
- shared has a 4-GPU or 8-GPU eligible node

Decision: prefer `shared-gpu` in 12h chunks unless private queue/GPU availability improves. Running too slowly on 2 private GPUs wastes time even if private is free.

## Scenario 4: Long non-checkpointable training, 3–4 days

Decision: prefer `private-teodoro-gpu`. Waiting can be meaningful because a 12h shared limit is not appropriate for a non-checkpointable multi-day command.

## Scenario 5: Private maintenance starts in 3 days

Job A: expected runtime 2 days.

Decision: submit to private with `--time` less than the maintenance-free window, not `7-00:00:00`.

Job B: expected runtime 5 days and non-checkpointable.

Decision: do not submit into this private window. Wait for a longer private window or restructure the job to checkpoint.

## Scenario 6: Ambiguous RTX 5000

Decision: do not use gpu050 for a large-model job until confirming VRAM. If it is RTX 5000 Ada 32GB, it is eligible. If it is older RTX 5000 16GB, exclude it.
