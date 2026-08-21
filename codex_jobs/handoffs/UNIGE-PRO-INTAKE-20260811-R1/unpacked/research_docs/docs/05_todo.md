# Research TODO and run tracker

## Current TODO

- [x] Create four isolated ChatGPT Pro scientific design conversations.
- [x] Freeze and audit the four existing claim anchors on unige.
- [x] Preserve successful run 11468096 and both failed-run diagnoses.
- [x] Capture the four complete Pro Round-1 reports with conversation links and hashes.
- [x] Build and submit `EVSPRINT-PILOT-FEASIBILITY-20260809B` (job `11473644`, valid fail-closed).
- [ ] Verify fragmentation T0 generator/truth hierarchy, H0 checkpoint and CRF4 selection provenance.
- [ ] Verify Label-A manifests, family→superfamily crosswalk, consensus/homology groups and old-SF5 overlap.
- [ ] Verify five anchor checkpoints/training genomes, a balanced eligible target matrix and whole-genome sketch availability.
- [ ] Verify Dfam freeze, family-resolved copies, raw clustering inputs and checkpoint provenance.
- [x] Feed verified availability/blockers back to each Pro conversation; minimal corrections are active in all four isolated chats.
- [ ] Implement exactly one pilot per track only after its data gate passes.

## Publication evidence backlog

- [x] PUB-P0: freeze truth-tier, leakage, failure-accounting and smart-sbatch
  governance contracts.
- [x] PUB-F0: pass the Track-F synthetic/evaluator code gate (job `11475001`).
- [x] PUB-F1: review and run real A0-A6 asset handoff; freeze exact T0 and
  comparator blockers/identities -> docs/14 `F-REAL-ASSET`.
- [x] PUB-S0: pass the Track-S S0-S4 code gate (job `11475199`).
- [ ] PUB-S1: review and run real S0-S4 materialization/ontology/homology handoff
  -> docs/14 `S-REAL-ASSET`.
  - [x] Build and independently verify the canonical pre-S0 snapshot (job `11477914`; 120/120 objects; no S0-S4 execution).
  - [ ] Review the exact snapshot-bound S0-S4 envelope before any further submission.
- [x] PUB-G0: run corrected real P1 provenance scan (job `11475198`); result is
  five `PROV_RUN_RECORD_MISSING`, so P2 is blocked.
- [ ] PUB-G1: choose exact historical recovery or clean five-anchor rebuild and
  freeze P1.5 -> docs/14 `G-P1.5`.
- [x] PUB-E0: pass the Track-E security/asset code gate (job `11475322`).
- [ ] PUB-E1: freeze official Parasail authority/build and real R1-R4 asset DAG
  -> docs/14 `E-BACKEND`, `E-ASSET`.
- [ ] PUB-B1: freeze exactly five task-matched end-to-end tools and exactly five
  taxonomy classifiers by pre-result feasibility criteria.
  - [x] Complete a claim-ineligible frozen-scope candidate census (job `11486982`).
  - [ ] Freeze one canonical candidate per tool and pass version/dependency/input/output smokes.
- [ ] PUB-B2: run `BENCH-PILOT` before any full five-tool comparison.
- [ ] PUB-D1: preregister one coverage-matched downstream utility endpoint only
  after a stable topology-aware mask exists.
- [ ] PUB-W1: write Results/Figures only from claim-admitted immutable bundles;
  no placeholder number or code-gate result enters the manuscript as biology.

## Run tracker

| Exp ID | Job | Status | Profile | Metrics / evidence |
|---|---:|---|---|---|
| EVSPRINT-CLAIM-ANCHORS-20260809A | 11468033 | FAILED | smoke | Python 3.9 API incompatibility; invalid |
| EVSPRINT-CLAIM-ANCHORS-20260809A | 11468053 | FAILED | smoke | expected manifest semantic fail; invalid |
| EVSPRINT-CLAIM-ANCHORS-20260809A | 11468096 | DONE | smoke | `run_11468096/results/audit_report.json`; PASS, 4 warnings |
| PIPE-TEFM-FRAG-R2-CODETEST-20260809-R1 | 11475001 | DONE | code gate | 33/33 tests; synthetic contract only |
| PIPE-TEFM-SF-R2-CODETEST-20260809-R2 | 11475199 | DONE | code gate | 51/51 tests; real S0-S4 closed |
| PIPE-TEFM-TRANSFER-R2-P1-20260809-R1 | 11474614 | FAILED | P1 | CSV field limit; invalid P1 output |
| PIPE-TEFM-TRANSFER-R2-P1-20260809-R2 | 11475198 | DONE/BLOCKED | P1 real asset | 5/5 `PROV_RUN_RECORD_MISSING`; valid fail-closed |
| PIPE-TEFM-EMBED-R2-CODETEST-20260809-R1 | 11475322 | DONE | code gate | 30/30 tests; no embedding/science |
| PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R1 | 11475473 | FAILED | transport wrapper | missing output parent; no A0-A6 |
| PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R2 | 11475492 | FAILED/BLOCKED | transport wrapper | frozen parent basename mismatch; no A0-A6 |
| PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3 | 11475540 | DONE/BLOCKED | A0-A6 real asset | A2/A3 pass; A0/A4/A5 block A6; 38/38 hashes |
| PIPE-TEFM-SF-R2-REAL-S0-S4-20260809-R1 | 11475541 | FAILED/BLOCKED | S0 path preflight | symlink project root; 120+120 alias path conflict; no materialization |
| PIPE-TEFM-SF-R2-PRE-S0-CODEGATE-20260810-R4 | 11477775 | DONE | v3 code gate | 87/87 tests; real-layout correction only; no real snapshot |
| PIPE-TEFM-SF-R2-PRE-S0-REAL-20260810-R2 | 11477914 | DONE | real pre-S0 snapshot | 120 frozen files + 120 ready links; independent verify PASS; no S0-S4/science |
| EVSPRINT-BENCH-TOOL-CENSUS-20260810-R1 | 11486982 | DONE | metadata census | 26,514 project + 252,552 Conda entries; candidates only; no tool execution/benchmark |
