# Window Matrix Dossier

Status: draft, pending `TE-LEN-VIZ` and backbone context smoke tests.

This dossier records the bounded window/context protocol used for TE-FM backbone comparison.

## 1. Council policy

Default policy from the 2026-06-15 council:
- `2048bp` is the Core shared anchor.
- Models that cannot support true 2048bp may use the nearest native context not exceeding 2048bp and must be marked `2048eq:<actual_bp>`.
- Each backbone gets at most 1-2 native/recommended windows in Core.
- Full `512/1024/2048/4096/8192` sweep is Enhanced and only for the final anchor backbone.
- `4096/8192bp` results are upper-bound or long-context evidence unless promoted by the route.

## 2. Required inputs

- `TE-LEN-VIZ` coverage table by species and superfamily.
- Backbone tokenizer/context limits.
- GPU memory smoke test for each candidate context.
- Comparison rule for fair tables versus upper-bound tables.

## 3. Matrix

| Backbone | True 2048 supported? | Core window(s) | Native/recommended window(s) | Enhanced sweep? | Notes |
|---|---|---|---|---|---|
| TBD | TBD | 2048 or 2048eq | TBD | final anchor only | Pending model shortlist |

## 4. Reopen triggers

- `2048bp` covers too little TE bp for any Core superfamily.
- Candidate backbone cannot be evaluated under any comparable anchor.
- Species panel changes enough to alter length distribution.
- Final paper claim shifts from same-kingdom/production performance to long-context universal modeling.
