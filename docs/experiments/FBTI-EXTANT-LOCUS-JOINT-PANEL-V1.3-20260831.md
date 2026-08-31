# FBTI-EXTANT-LOCUS-PHASE0-R1 V1.3 joint panel freeze

Date: 2026-08-31

Status: **engineering panel freeze passed; Gate L has not been evaluated**

## Frozen execution

- frozen census: job `12121962`, `COMPLETED 0:0`, 4 CPU, 32 GB, 0 GPU,
  10 seconds; Git commit `85098de9fb305c57ed90a937df375cbba91793bc`;
- joint panel and sidecars: job `12121966`, `COMPLETED 0:0`, 4 CPU,
  32 GB, 0 GPU, 1 minute 48 seconds; Git commit
  `0b88bae7821c01cf4de77b1754abb3e745358ad5`;
- exact remote output:
  `/home/users/j/jwang/ab-initio-TE/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/joint-panel-v1-3-freeze-20260831-r1`.

The committed manifests are under
`docs/experiments/manifests/FBTI-EXTANT-LOCUS-PHASE0-R1-V1.3/`.
They, rather than a rerun of the solver, are the authoritative downstream
panel input.

## Question answered

This engineering experiment asked whether one fixed, label-blind challenge
panel can satisfy all registered calibration/main/reserve and hard-cell
quotas while simultaneously enforcing:

- pairwise non-overlap of all 172 expanded packages;
- no frozen FlyBase truth feature shared between two package contexts;
- deterministic candidate-role priorities from one PCG64 stream;
- a proven-optimal MILP solution with zero reported gap;
- 40 pre-annotation deep-audit records;
- complete truth-context and canonical-P3 atom sidecars.

It did not ask whether the extant-locus ontology is reproducible. No package
has yet been annotated, so this result cannot pass Gate L.

## Result

| Quantity | Observed |
|---|---:|
| Candidate units | 5,226 |
| Candidate-role variables | 15,678 |
| Context-sharing conflict pairs | 30,098 |
| Total MILP constraints | 37,141 |
| Solver status | proven optimal |
| Reported MIP gap | 0.0 |
| Selected packages | 172 |
| Calibration | 6 S0 + 6 S1 |
| Main | 60 S0 + 60 S1 |
| Reserve | 20 S0 + 20 S1 |
| Frozen deep-audit records | 20 S0 + 20 S1 |
| Context truth rows | 1,572, all feature IDs package-unique |
| Package-atom rows | 80,683 |
| Unique canonical atom IDs | 80,682 |
| Package-censored atom rows | 85 |
| Atoms crossing two packages | 1, censored in both |

Main quotas are exactly 15 per S0 length cell and 20 per S1 geometry cell.
S0 calibration counts are `1/2/1/2` across `S0-L1..L4`; S1 calibration is
`2/2/2`. Reserve has no registered cell quota. All 40 deep-audit feature IDs
are distinct, belong to main packages and were frozen before annotation.

The panel estimand is explicitly conditional on this challenge mixture:
`population_representative=false`. No inclusion probability or FlyBase-wide
prevalence claim is available.

## Failure ledger

The following attempts remain engineering failures and enter no scientific
denominator:

- `12121043`: the V1 sidecar incorrectly assumed a non-overlapping package
  panel implied unique package ownership for every long P3 atom;
- `12121050`: deliberately cancelled after discovering that candidate-only
  objective coefficients left role assignment underidentified;
- `12121518`: `FAILED 120:0`, zero Slurm logs and no output directory during a
  login/shared-filesystem outage; the cause was not observable. Identical
  V1.2 census job `12121962` subsequently completed;
- `12121964`: V1.2 solved to zero gap but truth feature `FBti0059698` entered
  two package contexts, violating package-level bootstrap independence.

V1.1, V1.2 and V1.3 record the corresponding minimal contract corrections.
No failed package list was repaired manually and no seed, quota, flank or
annotation outcome was changed.

## Status classification

### Engineering

- Exact r6.68 contig-name/length mapping, truth, overlap graph and P3 inputs
  passed the frozen census and were retained as remote input snapshots.
- The 172-package challenge panel, role assignments, deep-audit records and
  context/atom manifests are frozen and committed.
- CPU-only Slurm execution and downstream manifest generation are complete.

### Scientific

No new scientific result. Gate L-P, L-R and L-D have not been evaluated;
there is no evidence yet that two annotators can reproduce the proposed
extant-locus ontology.

### Closed

- candidate-only role priorities;
- treating package non-overlap as sufficient for atom ownership;
- treating package non-overlap as sufficient for independent truth context;
- post hoc package swapping or seed changes after diagnostics.

### Next-only

1. Build the 12 calibration evidence packets from the committed panel without
   changing package membership.
2. Train two annotators on the ontology and run the registered 12-package
   calibration before any main annotation.
3. Only after calibration is version-locked, double-annotate the 120 main
   packages and execute Gate L; activate reserve pairs only for L-D.

The registered main-panel workload remains approximately 140--180 person-hours
plus 30--40 hours only if all reserve pairs are needed. No GPU, post-training,
new decoder or relation model is authorized before Gates L and O pass.
