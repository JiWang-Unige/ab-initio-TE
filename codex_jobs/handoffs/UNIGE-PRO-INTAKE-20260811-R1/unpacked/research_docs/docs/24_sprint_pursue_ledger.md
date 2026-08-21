# Evidence-sprint ledger

## [Evidence-Sprint] BENCH-TOOL-SMOKE-20260810

- Question: do exact local candidates for the preregistered five end-to-end TE
  annotation methods have independently frozen identities, start offline under
  the available runtime, report task-matching versions/entry points, expose the
  required databases/weights, and support a deterministic adapter contract
  strongly enough to authorize `BENCH-PILOT`?
- Hypothesis: RepeatModeler2+RepeatMasker, EDTA and Earl Grey will pass the
  candidate smoke; HiTE and TEtrimmer will require either a corrected canonical
  candidate or an explicit denominator decision because the census paths do not
  yet match the preregistered versions.
- Evidence needed: no-follow file identities and SHA-256 for every selected
  executable/container/config/database root; exact runtime and tool-reported
  version; offline launch rc/stdout/stderr; dependency and bundled database/
  weight census; frozen argv/help evidence; deterministic adapter fixture tests;
  typed PASS/BLOCK/ERROR terminal for every tool and the five-tool panel.
- Initial candidates from job `11486982`:
  - RepeatModeler `2.0.9` container plus RepeatMasker `4.2.4` container.
  - EDTA Conda environment currently records package `2.2.0`, below the
    preregistered `2.3.0` target.
  - Earl Grey `7.3.0` container.
  - HiTE backup container with version not yet independently established.
  - TEtrimmer `1.7.2` container, below the conditional `1.7.4` code snapshot.
- Budget: one reviewed CPU-only Slurm smoke job; at most one minimal corrected
  rerun if the first job exposes a wrapper/transport defect. No network access,
  package installation, nested scheduler submission, genome annotation or
  training.
- Non-goals: no performance ranking, no sensitivity/precision estimate, no
  biological output, no benchmark denominator substitution, no claim that a
  `--help`/version command proves end-to-end comparability.
- Acceptance criteria: exact candidate and runtime identities close; every
  command is executed from an isolated reviewed envelope on Unige; no tool may
  silently use network or an unpinned external database; per-tool status is
  typed and durable; `BENCH-PILOT` is authorized only if all five exact slots
  match the frozen benchmark contract. A version/task mismatch must yield
  `answered_mixed` or `inconclusive`, never an inferred pass.
- Current state: evidence card frozen; implementation and code review pending.
