# Superfamily Target Set Dossier

Status: draft, pending `SF-TARGET` Step 1 EDA.

This dossier records the provisional frozen superfamily set used for TE-FM training and evaluation. It is the source of truth for which superfamilies enter headline macro-F1 and which are merged, masked, or reported only as audit classes.

## 1. Decision rule

Default policy from the 2026-06-15 council:
- Use per-kingdom primary rules plus a global sensitivity check.
- Do not hard-code final numeric thresholds before EDA.
- Rare, single-species, low-sample, or low-concordance superfamilies do not enter headline macro-F1.
- Such classes are routed to `Other_TE`, `SPECIES_SPECIFIC_RARE`, or audit-only reporting.

## 2. Required Step 1 report

Before freezing the target set, produce:
- global superfamily TE bp percentage;
- per-kingdom superfamily TE bp percentage;
- species coverage matrix;
- interval count and bp count by species and superfamily;
- Label-A/B concordance by superfamily;
- rare/single-species candidate list.

## 3. Provisional class table

| Superfamily | Kingdom scope | Keep / Other_TE / Rare / Audit-only | Evidence summary | Rationale | Reopen trigger |
|---|---|---|---|---|---|
| TBD | TBD | TBD | Pending EDA | Pending EDA | Species panel or label source changes |

## 4. Evaluator impact

The final table must be propagated to:
- `docs/19_evaluator_contract.md` rare class masks;
- training label mapping configs;
- report schemas for per-superfamily metrics;
- `docs/14_validation_matrix.md` P8 cell metric definitions.
