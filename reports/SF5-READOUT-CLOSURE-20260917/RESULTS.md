# Frozen SF5 readout: full and known-label subsets

No training or inference was repeated. The completed 12779829 replay matrix exactly reproduces all original TP/FP/FN/support counts on 2,160 windows.

| Reference subset | Positions | Coverage | Main4 macro F1 | Material F1 |
|---|---:|---:|---:|---:|
| all_eight | 8847360 | 1.000000 | 0.833687 | 0.884305 |
| known_reference_bg_main4_other | 8692271 | 0.982471 | 0.838882 | 0.885630 |
| known_reference_bg_main4 | 8608940 | 0.973052 | 0.839961 | 0.886264 |
| conditional_true_main4 | 3412750 | 0.385737 | 0.902870 | 0.953459 |

Only reference rows were restricted. Predictions of BG or uncertain states remain errors on known TE rows; no uncertain prediction was removed to improve the score.

These subsets answer different conditional questions. They do not constitute retraining, representation improvement, unseen-species generalization, or independent correction of Unknown annotations. In particular, conditional_true_main4 excludes background and cannot measure genome-wide detection precision.

The recovered compact matrix is pooled; existing per-species full metrics remain available, but per-species conditional metrics cannot be reconstructed from this pooled matrix. No per-species values are imputed.

The merged AMBIGUOUS_TE/UNCLASSIFIED state has exact F1 0.592255. KNOWN_OTHER_TE is kept separate because it is a known broad-category label, not an uncertainty state.

Source: source/frozen-confusion-12779829.json; original: ../SF5-ONTOLOGY-CLOSURE-20260915/run-12731987/test_results.json.
