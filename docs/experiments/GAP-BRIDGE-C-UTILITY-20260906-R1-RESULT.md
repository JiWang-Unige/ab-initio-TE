# C utility closure — 2026-09-08 UTC

**Engineering PASS; frozen exploratory utility gate FAIL for both arms.**
User's 2026-09-06 automatic decision closes this gene-utility expansion route.
No A training, repeat C, gate tuning, new masking or sealed-panel access follows.
This is not completion of the cross-species TE masking-model terminal goal.

## Execution and semantic validation

- Job `12416179`: live sacct `COMPLETED`, exit `0:0`, elapsed 2972 s (49m32s),
  1 RTX3090 on gpu034, private/4CPU/48GiB/2h. Prior shared A/C GPU time 400 s;
  combined 3372 s = 0.9367 GPUh, below the existing 24 GPUh budget.
- Original output remains `outputs/GAP-BRIDGE-C-UTILITY-20260906-R1/run-r1`.
  Complete 148 MiB run copied locally without overwriting existing files; original
  logs at `logs/gap-c-utility_12416179.{out,err}`. No new job submitted.
- All 27 native GTF/GFF3 cells and actual model-input observations re-read locally
  with the frozen `utility.read_cell`; all audit objects exactly match result.json.
  Original RefSeq and geometry reconstruct 330 eligible source rows/243 distinct
  chains. `paired_metrics` recomputation exactly matches all per-core, micro and
  identity gain/loss outputs. Includes the three zero-reference cores.
- Metrics JSON exists, parses and contains finite nondegenerate absolute F1 values;
  zero *delta* for MW is legitimate, not an all-zero predictor. No training or loss
  curve applies. Fixed model loading is evidenced by 27 completed predictions and
  successful actual six-channel observations; no newly trained checkpoint exists.
  Main job logs contain no OOM/Traceback/NaN-loss/ResourceExhausted match.
- Existing independent code-review PASS and allocation 8/8 tests retained;
  no implementation/evaluator changes. Current local base HEAD
  `852b65e1accb560cce62ffdb3c9b99260511fe63` is not claimed as a clean run commit;
  reviewed code/config provenance remains the original code_review_gate.json.

## Fixed complete-CDS-chain result

| Arm | TP | FP | FN | Micro F1 | Delta vs M0 | Gained | Lost | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| M0 | 54 | 37 | 189 | 0.32335329341317365 | — | — | — | control |
| MW | 54 | 37 | 189 | 0.32335329341317365 | 0 | 0 | 0 | FAIL |
| MP | 54 | 36 | 189 | 0.32432432432432434 | 0.0009710309111506943 | 0 | 0 | FAIL |

MP's aggregate improvement is a net loss of one unmatched prediction, not recovery
of a correct chain. MP has two *new* unmatched identities (core10/core20), so the
net FP reduction must not be described as an unchanged prediction set with one
simple deletion. Their complete coordinates remain in result.json.
MW has zero new unmatched identities. Every arm has five excluded records and
zero halo-edge-touching records; the full exclusion reasons/identities, sequence
audits and per-core results remain in the copied result.json, not silently dropped.

| Added-mask risk | MW | MP |
|---|---:|---:|
| Added mask bp | 143476 | 461752 |
| CDS overlap bp / genes | 6 / 3 | 80 / 3 |
| Exon overlap bp / genes | 773 / 39 | 2010 / 54 |
| Intronic splice dinucleotide bp / genes | 5 / 4 | 13 / 8 |

These union overlaps use all chr13 RefSeq transcripts, including scoring-ineligible
ones. They are descriptive risks, not measured gene damage or new selection gates.

## Deterministic gate and automatic decision

Both per-arm invocations of `scripts/validate_goal.py` return `not_yet`, with
`run_ok=true`, `semantic_ok=true`, denominator/completeness guardrails PASS and
primary_progress_gate FAIL. Input sidecars are in
`reports/GAP-BRIDGE-C-UTILITY-20260906-R1-validation/{contract,MW,MP}.json`.
The sidecar transcribes the already approved three predicates; it does not change
ACTIVE_GOAL.json or the platform goal. Absolute micro F1 is the generic semantic
check; delta/gained/lost remain the decision-bearing predicates.

The generic validator's MP `claim_gate=true` only means F1 exceeds M0; its generic
`tuning_allowed=true` is not authority to tune this frozen experiment. Both are
subordinate to the failed conjunctive utility gate and the explicit user stop rule.
No SOTA, independent confirmation or cross-species utility claim is eligible.
Separate tri-review is not needed to execute the user's already frozen closure rule.

## Next boundary

Close C-derived whole-gap A/gene-utility expansion. Preserve P3, old Stage1/INIT/B0
stop decisions and all seals. C does not disprove TE material masking generally.
For the still-active cross-species goal, return to existing L1/upstream evidence:
prepare a bounded, discriminating upstream label/data/objective/backbone proposal
against missed material and terminal loss, without restarting rejected arms or
changing thresholds. Existing-result synthesis is authorized; a materially new
scientific training contract requires its scope/resource approval before execution.
