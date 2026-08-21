# PIPE-TEFM-FINAL-INTERVALREFINER-20260630

## Scope

Bounded frozen-bp interval-refiner prototype using a coordinate train/test split on mouse chr1 windows.
The refiner trains lightweight RandomForest/constant fallback classifiers on frozen bp probabilities and local interval/gap features.

## Headline

- Windows used: 40; train fraction: 0.6.
- Segment classifier: {'status': 'random_forest', 'n': 152, 'fit_n': 152, 'positive_rate': 0.7039473684210527, 'fit_positive_rate': 0.7039473684210527}.
- Gap classifier: {'status': 'random_forest', 'n': 151, 'fit_n': 151, 'positive_rate': 0.271523178807947, 'fit_positive_rate': 0.271523178807947}.
- Test `consensus_min_raw` segment-F1@IoU0.8/boundary5: 0.4462.
- Test `consensus_min_crf` segment-F1@IoU0.8/boundary5: 0.4685.
- Test refiner `refiner_keep_drop` segment-F1 0.4603, boundary-F1 0.1429, missed true rate 0.0161.
- Best test variant: `oracle_fill_supported_true` segment-F1 0.9919.

## Test Variants At IoU0.8 / Boundary5

| Variant | Segment-F1 | Boundary-F1 | Missed true rate | Mean fragments per true | Short predicted segments |
|---|---:|---:|---:|---:|---:|
| consensus_min_raw | 0.4462 | 0.1385 | 0.0161 | 1.1935 | 17 |
| consensus_min_crf | 0.4685 | 0.1261 | 0.0161 | 1.0645 | 2 |
| refiner_keep_drop | 0.4603 | 0.1429 | 0.0161 | 1.1935 | 13 |
| refiner_gap_merge | 0.4553 | 0.1138 | 0.0161 | 1.1452 | 11 |
| refiner_keep_drop_gap_merge | 0.4667 | 0.1167 | 0.0161 | 1.1452 | 8 |
| oracle_fill_supported_true | 0.9919 | 0.9919 | 0.0161 | 0.9839 | 5 |

## Interpretation

- This prototype is deployable in form because test-time decisions use only logits and interval/gap features.
- The deployable refiner variants do not beat consensus+CRF in this bounded smoke. This exact post-hoc keep/drop + gap-merge prototype should not be scaled as-is.
- The oracle result shows that bp logits often touch the correct true intervals, so the remaining gap is structural interval/boundary learning rather than lack of additional threshold/gap tuning.
- The next useful component should be a boundary-aware head, segment-aware decoder, richer interval proposal/refiner, or semi-Markov/duration-aware decoder.

## Outputs

- `interval_refiner_metrics.tsv`
- `interval_refiner_status.json`
