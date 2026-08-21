# UNIGE-PRO-INTAKE-20260811-R1 Protocol

## Purpose

This is a bootstrap and intake iteration, not a claim-bearing experiment. Its
purpose is to reconcile the current publication-validation state with the
older research history already present on Unige, identify exactly which
candidate packages are available, and prevent unreviewed Pro code from being
submitted to Slurm.

## Source-of-truth order

1. Exact remote files and Slurm evidence on Unige.
2. This dated handoff snapshot and its SHA-256 manifest.
3. The archived collaboration documents bundled with this handoff.
4. Existing remote `docs/` as historical context. Do not overwrite them during
   this intake because the remote `docs/11_master_plan.md` still contains a
   June-oriented mainline not reconciled with the August Pro collaboration.
5. ChatGPT Pro prose is advisory only and never execution authority.

## Accepted remote evidence

| Track | Accepted evidence | Scientific authority |
|---|---|---|
| Common audit | job 11468096: 18 frozen inputs and five verified result hashes | audit only |
| Fragmentation | job 11477415: nine-file H0 identity, 1,973,418,475 bytes; job 11477481: complete 48-symlink metadata census | no fragmentation performance claim |
| Superfamily | job 11477775: CPython 3.9.25 code gate, 87/87 tests; job 11477914: 120-payload canonical snapshot, 37,567,650,960 bytes | snapshot only; S0-S4 unrun |
| Generalization | historical P1 check: all five fixed-anchor run records missing | valid provenance block, no decay result |
| Embedding | exact coordinate contract for 2,200 fragments | no embedding/clustering result |
| Benchmark | job 11486982: complete candidate census, 26,514 project entries and 252,552 Conda entries visited | no tool invoked; no benchmark result |

## Pro candidate deliveries awaiting independent acceptance

These values identify candidate transport objects. They do not authorize
execution and the packages may not yet exist on Unige.

| Track | Candidate | ZIP bytes | ZIP SHA-256 | Known remaining external gate |
|---|---|---:|---|---|
| Fragmentation | R4.4 | 153,708 | `50236EBD30CD626FC17528D48AE3D118813E8B027B2DDF7355BDE7ED1920D379` | real CPython 3.9 runtime/trust freeze and independent review |
| Superfamily | snapshot-bound v4 | 191,301 | `61DEFF312BE71A7E7B0714C9C020E83A09401CE9473132D419CE118019C6A4D3` | external pin registry, producer/verifier identities, real Python 3.9 gate |
| Generalization | V4.6 | 907,229 | `C37771663CFAA609AB084C2993A4D3DC14D7D6F5F5EA3B05D3F2482408A81E8F` | Python 3.9 + NumPy 1.26.4 trust instance and authority seals |
| Embedding | R6 | 125,410 | `1DB7FF0D4FB652F9C36BCB690C5F8287E6E842B917115D4877F4C1A4F40C78EC` | Transformers/GPU/model pins and independent review |
| Benchmark | five-tool smoke | 63,480 | `250A4E3E12D644D690E9022C4873E73A4755C0922ECBF9798848B59FCE6B8020` | exact versions, dependencies, databases, offline launch and adapters |

If the exact object, declared size, SHA-256, closed member manifest and
independent acceptance report are not all present, use the typed status
`PACKAGE_NOT_STAGED` or `PACKAGE_NOT_ACCEPTED` and stop that track.

## Comparator state

Candidate paths were found for RepeatModeler2/RepeatMasker, EDTA, Earl Grey,
HiTE and TEtrimmer. No MCHelper pathname match was found. Candidate discovery
does not establish readiness. Known version conflicts must fail closed:

- EDTA local metadata is approximately 2.2.0 while the frozen target is 2.3.0.
- The TEtrimmer container name indicates approximately 1.7.2 while the
  conditional target is 1.7.4.
- HiTE exact version is not yet frozen.

Do not substitute a different version after seeing results. TE_Bench is an
evaluator anchor, not one of the five end-to-end annotation workflows.

## Scientific launch order

1. Five-tool exact version/dependency/database/offline-launch smoke.
2. Preservation-constrained fragmentation pilot: raw positives immutable;
   parent-aware joins; false-fusion, retention, nesting and boundary metrics.
3. Hierarchical open-set direct-superfamily pilot: deepest supported ontology
   node or abstention; family/homology-blocked and clade-held-out evaluation.
4. Generalization kill-gate: fixed-anchor transfer surface and uncertainty-aware
   top-k/abstention, not a universal scalar confidence formula.
5. Embedding kill-gate: identical sealed splits and clustering budget against
   k-mer, MinHash, alignment, length/GC, random Gaussian and untrained-network
   controls; UMAP alone is not evidence.

## Package intake gate

For every candidate package:

1. Copy into a new immutable intake directory; never replace a previous intake.
2. Verify declared bytes and SHA-256 before extraction.
3. Reject absolute paths, traversal, links, special files, duplicate members,
   case collisions and manifest non-closure.
4. Run credential/secret scanning without printing secret values.
5. Reconstruct the declared predecessor delta where applicable.
6. Perform an independent read-only code review; Pro self-tests are supporting
   evidence only.
7. Freeze external interpreter, dependency, asset and verifier identities.
8. Only after PASS, materialize a unique smart-sbatch wrapper and execute the
   smallest claim-ineligible real-environment gate.

## Smart-sbatch contract

- Read `cluster_config.yaml` and determine `submission.mode` first.
- Always collect live `sinfo`, `squeue`, `scontrol show reservation`, recent
  `sacct`, disk/quota and output-path evidence.
- Phase 1 is mandatory. Any failed hard rule means `BLOCKED` and no command.
- Review existing sbatch scripts in Mode B; do not regenerate their headers.
- CPU-only gates use the configured CPU fast path and request zero GPUs.
- GPU jobs must distinguish minimum from efficient GPU count, filter VRAM,
  avoid excluded RTX 3080 nodes unless the task explicitly qualifies them, and
  respect shared-partition checkpoint/walltime rules.
- Each experiment has unique output, log, checkpoint and metrics paths.
- After completion, run semantic result validation and retain failed evidence.

## Required output files

Write only below
`codex_jobs/handoffs/UNIGE-PRO-INTAKE-20260811-R1/`:

- `REMOTE_STATE_DIFF.md`
- `TRACK_STATUS.tsv`
- `REMOTE_UPLOAD_INVENTORY.tsv`
- `MISSING_UPLOADS.tsv`
- `RESEARCH_FLOW_GUARD.json`
- `SLURM_SNAPSHOT.txt`
- `NEXT_ACTION.md`
- `OUTPUT_SHA256.tsv`

End with exactly one of:

- `READY_FOR_PACKAGE_INTAKE`
- `READY_FOR_REVIEWED_SMOKE`
- `BLOCKED_WITH_EVIDENCE`

Never emit `READY_FOR_SCIENCE` from this bootstrap iteration.

