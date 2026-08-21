# Experiment iterations

## ITER-1 — EVSPRINT-CLAIM-ANCHORS-20260809A

- Track: cross-track evidence audit
- Path / milestone: publication validation → denominator/provenance lock
- Execution mode: run-and-evaluate
- Hypothesis: existing result artifacts can be hash-pinned and internally audited strongly enough to choose the next bounded experiment without treating screens as biological replication
- Mechanism delta: no model; added fail-closed hash/schema/metric-identity evidence layer
- Slurm: 11468033 FAILED, 11468053 FAILED, 11468096 COMPLETED on `private-teodoro-gpu`; successful walltime 3 seconds
- Result: audit verdict PASS; 18 inputs; zero hard errors; four duplicate-key warnings
- Tri-review: not applicable to a non-claim evidence sprint; four independent external design reviews are recorded separately
- Pivot: pending feasibility inventory
- Links: `docs/06_results_log.md`; local `codex_pro_collaboration/scientific_evidence/EVSPRINT-CLAIM-ANCHORS-20260809A`; remote `software_outputs/scientific_evidence/EVSPRINT-CLAIM-ANCHORS-20260809A/run_11468096`

## ITER-2 — EVSPRINT-PILOT-FEASIBILITY-20260809B

- Track: cross-track prerequisite/asset audit
- Path / milestone: publication validation → pilot readiness gate
- Execution mode: run-and-evaluate, read-only
- Hypothesis: current unige assets can support at least one leakage-safe bounded pilot without inventing truth, ontology, identity or training provenance
- Mechanism delta: no model; fail-closed exact inventory, schema, source, tool and provenance gates
- Slurm: 11473644 `FAILED 2:0` on `private-teodoro-gpu`; walltime 2m24s; semantically valid audit failure
- Result: wrapper/integrity PASS, audit verdict FAIL with one symlink hard error; all four tracks blocked by explicit prerequisite contracts
- Tri-review: not applicable before a scientific result; exact evidence is routed to four isolated Pro Round-2 reviews
- Pivot: remediate/freeze minimum assets separately; do not implement models
- Links: `docs/06_results_log.md`; `docs/experiments/EVSPRINT-PILOT-FEASIBILITY-20260809B.md`; local evidence `codex_pro_collaboration/evidence/EVSPRINT-PILOT-FEASIBILITY-20260809B_run11473644`

## ITER-3 — EVSPRINT-BENCH-TOOL-CENSUS-20260810-R1

- Track: five-tool benchmark readiness
- Path / milestone: PUB-B1 candidate discovery before candidate freeze/smoke
- Execution mode: read-only, claim-ineligible evidence sprint
- Hypothesis: the frozen project and Conda scopes contain locally reusable candidates for an exact five-tool panel
- Mechanism delta: no model or annotation tool; added bounded no-follow metadata census with immutable terminal evidence
- Slurm: `11486982` COMPLETED `0:0` on `private-teodoro-gpu` / `gpu035`; payload wall time 53.355034 seconds
- Result: complete frozen-scope census; local candidates found for RepeatModeler2/RepeatMasker, EDTA, Earl Grey, HiTE and TEtrimmer; no MCHelper pathname match
- Tri-review: not applicable before a scientific/benchmark result; execution envelope passed independent static review before submission
- Pivot: freeze exact candidates and run version/dependency/input/output smokes before `BENCH-PILOT`
- Links: `docs/06_results_log.md`; `docs/experiments/EVSPRINT-BENCH-TOOL-CENSUS-20260810-R1_RESULT.md`; local evidence `codex_pro_collaboration/scientific_evidence/EVSPRINT-BENCH-TOOL-CENSUS-20260810-R1`
