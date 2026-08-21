# Results Log

> 由 /result-log append。每个 experiment_id 一段。
> 单次失败也进这里(只有 abandon route 才进 docs/09)。

每个 entry 用 ## Result: <exp_id> 开头。模板见 /result-log SKILL.md。

---

## Result: SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1

### Meta

- Date: 2026-08-12 CEST (2026-08-11 UTC).
- Resource profile: bounded CPU asset-identity smoke; Job `11525316`, `private-teodoro-gpu`, 4 CPU/48 GiB/2h limit/0 GPU; claim-ineligible.
- Code review: independent PASS, 0 blockers, 13/13 allocation-side tests.
- Evaluator contract: `docs/19_evaluator_contract.md` SHA-256 `fe0d63e9b525a0bac5ee03b3b88b83385fc4582f8a1b3f9802d171c72594ade2`.

### Semantic-success validation

- Audited terminal status: `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`; `semantic_success=false`; deterministic `validate_goal.py` returned `failed_run` rc3.
- The runner correctly entered `RUNNING` and began an index-independent, case-sensitive scan of Dfam 3.9 partition 3. Structured checkpoints reached 10,000, 20,000 and 30,000 datasets with continuing I/O and no traceback.
- At the preregistered 30,000-dataset resource checkpoint, elapsed time was about 1,480 seconds. Linear projection for the mandatory 321,856-dataset exhaustive scan was about 15,878 seconds (4.41 hours), which could not fit the reviewed 2-hour walltime. The controller cancelled the exact job early at 01:25:01 CEST to avoid a certain Slurm timeout.
- Because the process was externally cancelled, the immutable runner `STATUS` remains `RUNNING`. A separate `AUDITED_STATUS`, audited metrics, semantic audit and 17-entry hash manifest preserve this distinction; all manifest hashes pass.
- `sacct` was unavailable because `slurmdbd` refused the connection. `squeue` terminal disappearance and the Slurm stderr cancellation line establish cancellation; formal billing/MaxRSS accounting remains unknown.

### Interpretation and decision boundary

- The first 30,000 datasets contained zero exact target-name candidates, but this is only 9.321096% of the required catalog and is explicitly non-scientific partial telemetry. It cannot support a zero-hit, missing-identity or valid-negative claim.
- No identity resolution table, full catalog authorization, homology component, split, model, GPU result or S0 metric exists. R1 full catalog, R2 homology split, GPU S0 and S1 all remain forbidden.
- This run identifies a resource/implementation-shape error, not a biological result: serial small-attribute access on the 63.9 GB HDF5 source is too slow for the reviewed 2-hour contract despite low CPU/RSS use.
- Required next action: `$tri-review`, then a single repair pivot. The repair must preserve exact exhaustive semantics while either partitioning the canonical `Families` tree into deterministic disjoint shards or independently reviewing a longer CPU walltime; partial scan reuse cannot satisfy the terminal gate.

### Paths

- Audit: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/{AUDITED_STATUS,metrics.audited.json,result_semantic_audit.json,validate_goal.json,audited_output_manifest.sha256}`.
- Raw runner state/progress: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/preview/`.
- Config/code/sbatch: `configs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.yaml`; `scripts/experiments/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/`; `sbatch/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.sbatch`.

---

## Result: PIPE-TEFM-CAP-FRAGARCH-20260701

### Meta

- Date (UTC): 2026-06-30 / local completion 2026-07-01 CEST
- Resource profile: capability-pursue bounded screen
- Claim eligibility: cannot claim SOTA; this is a publication-validation support prototype.
- Code review gate: `docs/21_code_review_log.md#code-review-gate-pipe-tefm-cap-fragarch-20260701`; machine gate `outputs/PIPE-TEFM-CAP-FRAGARCH-20260701/code_review_gate.json`
- Slurm: job `9865070`, `shared-gpu`, RTX 3090, `COMPLETED`, elapsed `00:03:01`

### Dataset / Split

- Train: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick/train/data.jsonl.gz`
- Eval panels: human H0 quick test and mouse A1 quick test, 40 windows each.
- Split scheme: inherited chromosome/window quick panels from prior TEFM support experiments; no random split introduced in this run.

### Config

- Architecture: frozen promoted GENERanno 4096 token classifier embeddings/logits plus two lightweight interval heads.
- New candidates: `boundary_proposal` start/end + learned interval proposal scorer; `anchor_free_interval` center/length detector.
- Baselines/comparators: same-panel CE raw threshold, HMM penalty2, CRF-style penalty4; historical `interval_survival_decoder` and `retention_constrained_decoder` rows marked non-comparable reference.
- Key hyperparams: seed `42`, max train windows `96`, max eval windows `40`, max steps `50`, batch size `1`, head width `96`, lr `3e-4`.

### Paths

- Script: `pipelines/PIPE-TEFM-CAP-FRAGARCH-20260701/train_interval_architectures.py`
- Sbatch: `pipelines/PIPE-TEFM-CAP-FRAGARCH-20260701/run_interval_arch_screen.sbatch`
- Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/interval_arch_metrics.tsv`
- Status: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/interval_arch_status.json`
- Report: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/INTERVAL_ARCHITECTURE_REPORT.md`
- Logs: `logs/PIPE-TEFM-CAP-FRAGARCH-20260701/TEFM_FRAGARCH_9865070.*`

### Semantic Success

- Metrics file exists and is parseable: pass.
- Status JSON reports `ok=true`: pass.
- Primary strict metrics finite: pass.
- No OOM/NaN/Traceback in final logs: pass.
- Code-review gate passed in job: pass.
- Historical-reference parsing was repaired and rerun; same-panel metrics were unaffected by the first report bug.

### Key Metrics at IoU 0.8 / Boundary 5 bp

| Panel | Variant | bp-F1 | segment-F1 | boundary-F1 | missed_true_rate | pred_true_backed_rate | deleted_true_backed_fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| human_test | CE raw | 0.8369 | 0.1542 | 0.0763 | 0.2869 | 0.8736 | 0.0000 |
| human_test | CRF-style penalty4 | 0.8362 | 0.4126 | 0.2087 | 0.2910 | 0.9345 | 0.8518 |
| human_test | boundary_proposal | 0.6782 | 0.2969 | 0.0521 | 0.3607 | 0.9286 | 0.8683 |
| human_test | anchor_free_interval | 0.8414 | 0.3581 | 0.1878 | 0.3197 | 0.8972 | 0.7419 |
| mouse_quick | CE raw | 0.8232 | 0.1437 | 0.0513 | 0.1133 | 0.6114 | 0.0000 |
| mouse_quick | CRF-style penalty4 | 0.8260 | 0.4904 | 0.1720 | 0.1200 | 0.7744 | 0.4889 |
| mouse_quick | boundary_proposal | 0.7292 | 0.2340 | 0.0922 | 0.1733 | 0.8636 | 0.5489 |
| mouse_quick | anchor_free_interval | 0.2422 | 0.0965 | 0.0429 | 0.6267 | 0.6323 | 0.5701 |

### Gate Check

- Promotion gate: fail.
- No candidate improved both segment-F1@IoU0.8 and boundary-F1@5bp over CE and current smoothing comparator.
- Both new architectures also violate at least one true-retention guardrail: missed_true_rate rises or deleted_true_backed_fraction remains far above `0.15`.

### Interpretation

The run is an engineering success and method failure for this first capability round. The direct interval heads did not beat the unchanged CRF-style smoothing comparator, and the learned interval proposal path still removes many true-backed CE fragments. The result reinforces the earlier conclusion that reducing fragment count alone is not enough; any successful module must learn boundary localization while explicitly preserving true TE fragments.

### Recommended Next Action

- Run `$tri-review` and `$pivot` before deciding whether a second bounded round is justified.
- If continued, next mechanism must be more structural than these lightweight heads, e.g. a proposal generator trained on full coordinate records with differentiable matching/set loss or a boundary-conditioned sequence-to-segment decoder; do not tune thresholds/gaps/HMM penalties.

---

## Result: PIPE-TEFM-CAP-FRAGGRAPH-20260701

### Meta

- Date (UTC): 2026-06-30 / local completion 2026-07-01 CEST
- Resource profile: capability-pursue bounded screen
- Claim eligibility: cannot claim SOTA; support/capability prototype only.
- Code review gate: `docs/21_code_review_log.md#code-review-gate-pipe-tefm-cap-fraggraph-20260701`; machine gate `outputs/PIPE-TEFM-CAP-FRAGGRAPH-20260701/code_review_gate.json`
- Slurm: job `9866570`, `shared-gpu`, RTX 3090, `COMPLETED`, elapsed `00:03:48`

### Dataset / Split

- Train: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick/train/data.jsonl.gz`
- Eval panels: human H0 quick test and mouse A1 quick test, 40 windows each.
- Split scheme: inherited chromosome/window quick panels from prior TEFM support experiments; no random split introduced.

### Config

- Architecture: frozen promoted GENERanno 4096 token classifier embeddings/logits plus fragment graph linker.
- New candidates: `fragment_graph_keepall` preserves all CE raw fragments and learns only adjacency/link fills; `fragment_graph_keepdrop` is a diagnostic learned keep/drop + link variant.
- Baselines/comparators: same-panel CE raw threshold and CRF-style penalty4 smoothing comparator.
- Key hyperparams: seed `42`, max train windows `128`, max eval windows `40`, max steps `80`, batch size `1`, graph hidden `128`, lr `5e-4`, fixed link threshold `0.5`.

### Paths

- Script: `pipelines/PIPE-TEFM-CAP-FRAGGRAPH-20260701/train_fragment_graph_linker.py`
- Sbatch: `pipelines/PIPE-TEFM-CAP-FRAGGRAPH-20260701/run_fragment_graph_screen.sbatch`
- Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_metrics.tsv`
- Status: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_status.json`
- Report: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/FRAGMENT_GRAPH_LINKER_REPORT.md`
- Logs: `logs/PIPE-TEFM-CAP-FRAGGRAPH-20260701/TEFM_FRAGGRAPH_9866570.*`

### Semantic Success

- Metrics file exists and is parseable: pass.
- Status JSON reports `ok=true`: pass.
- Primary strict metrics finite: pass.
- No OOM/NaN/Traceback in final logs: pass.
- Code-review gate passed in job: pass.

### Key Metrics at IoU 0.8 / Boundary 5 bp

| Panel | Variant | bp-F1 | segment-F1 | boundary-F1 | missed_true_rate | pred_true_backed_rate | deleted_true_backed_fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| human_test | CE raw | 0.8369 | 0.1542 | 0.0763 | 0.2869 | 0.8736 | 0.0000 |
| human_test | CRF-style penalty4 | 0.8362 | 0.4126 | 0.2087 | 0.2910 | 0.9345 | 0.8518 |
| human_test | fragment_graph_keepall | 0.8369 | 0.1542 | 0.0763 | 0.2869 | 0.8736 | 0.0000 |
| human_test | fragment_graph_keepdrop | 0.7546 | 0.4964 | 0.2458 | 0.3115 | 0.9298 | 0.8632 |
| mouse_quick | CE raw | 0.8232 | 0.1437 | 0.0513 | 0.1133 | 0.6114 | 0.0000 |
| mouse_quick | CRF-style penalty4 | 0.8260 | 0.4904 | 0.1720 | 0.1200 | 0.7744 | 0.4889 |
| mouse_quick | fragment_graph_keepall | 0.8232 | 0.1437 | 0.0513 | 0.1133 | 0.6114 | 0.0000 |
| mouse_quick | fragment_graph_keepdrop | 0.8159 | 0.3676 | 0.1313 | 0.1267 | 0.8111 | 0.5253 |

### Gate Check

- Promotion gate: fail.
- `fragment_graph_keepall` preserves CE fragments but does not learn useful links; metrics are identical to CE raw.
- `fragment_graph_keepdrop` improves human segment/boundary over smoothing but violates true-backed deletion guardrail and fails to beat smoothing on mouse.

### Interpretation

The fragment graph idea changed the mechanism, but this implementation is not a usable interval module. The preservation-first decode avoids true-backed deletion but does not improve strict interval metrics, implying learned edge links were too weak or too sparse. The keep/drop diagnostic confirms the recurring tradeoff: strong interval-looking gains can still be achieved by deleting true-backed fragments, which is not acceptable for annotation completeness.

### Recommended Next Action

- Run `$tri-review` and `$pivot`.
- Do not scale this graph linker as implemented.
- If reviewers allow another bounded round, it must address the core failure directly: learned links must fire without deleting CE true-backed fragments, or the route should be written as future work.


## Result: PIPE-TEFM-SUPP-20260617

Date: 2026-06-18

Status: semantic success, screen complete.

Scope: UCSC strict-TE supplement screen with seed=42, H0 human quick fine-tuning/window sweep, B/C one-chromosome transfer evaluation, mouse-only downstream, A2 no-human animal mixture downstream, edge-position analysis, and simple decay sanity check.

Primary output:

- Final report: `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/FINAL_REPORT.md`
- Metrics: `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/all_metrics.tsv`
- Window: `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/window_sweep.tsv`
- Transfer: `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/transfer_summary.tsv`
- Downstream: `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/downstream_summary.tsv`
- Edge: `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/edge_summary.tsv`

Key metrics:

- H0 window best: `ntv2_500m`, window=4096, TE-F1=0.9458, AUPRC=0.9893.
- H0 second: `generanno`, window=4096, TE-F1=0.9430, AUPRC=0.9869.
- B/C 2048 transfer mean TE-F1: `generanno` 0.5477, `ntv2_500m` 0.5367, `dnabert2` 0.4535, `hyenadna` 0.4258.
- B/C 4096 transfer mean TE-F1: `ntv2_500m` 0.5185, `generanno` 0.4851.
- Mouse-only to A1 mean TE-F1: `generanno` 0.8721, `ntv2_500m` 0.8546.
- A2 mixture to A2 all-species mean TE-F1: `generanno` 0.5590, `ntv2_500m` 0.5414; vertebrate-only mean TE-F1: `generanno` 0.7160, `ntv2_500m` 0.6941; held-out invertebrate mean TE-F1 near zero for both.
- Edge effect: non-overlap edge-minus-center is negative for almost all model/window combinations; 512 and some 1024 settings lose about 0.03-0.04 TE-F1, while 4096/8192 usually lose about 0.008-0.015.

Decision:

- Keep `generanno` and `ntv2_500m` as paired candidates; use window=4096 for the next bp-level evaluator stage.
- Do not claim final SOTA from this screen. Token-level proxy, one-chrom transfer eval, quick max-window truncation, and label-source caveats remain.
- Do not keep trying to fit a formal generalization-decay formula now; ordinal-distance correlations are negative but confounded by kingdom/domain shifts and label coverage.
- A2 invertebrate failure should go to tri-review/pivot rather than automatic tuning.

Blocked:

- NTv3 local snapshot lacks required remote-code module.
- Evo2 local snapshot lacks HF adapter/tokenizer metadata.

---

## Result: PIPE-TEFM-SEG-SF-20260618

Date: 2026-06-18

Status: semantic success, screen complete.

Scope: GENERanno-only follow-up with 2048 bp and 4096 bp windows, seed=42. The run completed overlap center-merge inference, segment/boundary/fragmentation/postprocess evaluation, superfamily token-head training, and TE-fragment embedding clustering over B_animal and D_crosskingdom panels.

Primary output:

- Final report: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/FINAL_REPORT.md`
- Overlap/postprocess: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/overlap_postprocess_summary.tsv`
- Edge bins: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/edge_bin_summary.tsv`
- Superfamily: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/superfamily_summary.tsv`
- Embedding clustering: `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries/embedding_cluster_summary.tsv`

Key metrics:

- Best segment-level setting: 4096 window, stride 2048, `hmm_penalty2`, bp-F1 0.9427, segment-F1@IoU0.5 0.7442, boundary-F1@100bp 0.6261.
- 4096 stride 1024 is essentially tied: bp-F1 0.9429, segment-F1@IoU0.5 0.7440, boundary-F1@100bp 0.6255.
- Raw-threshold segment-F1 is much lower: 4096 stride 2048 raw segment-F1 0.5021; 2048 stride 512 raw segment-F1 0.4630. This supports overlap plus smoothing/postprocess for annotation usability.
- Superfamily 2048: TE-detect F1 0.9326, class macro-F1 0.6858, all-6 macro-F1 0.7287.
- Superfamily 4096: TE-detect F1 0.9393, class macro-F1 0.7109, all-6 macro-F1 0.7494.
- Embedding clustering best individual run: B_animal length 512 C1 basic sequence features + contrastive projection, ARI 0.9399, NMI 0.9165, holdout macro-F1 0.9083.
- Embedding clustering mean: C1 basic+contrastive holdout macro-F1 0.7405; A1 pretrained GENERanno+contrastive 0.6436; fine-tuned embedding variants are weaker in this quick screen.

Decision:

- Use GENERanno 4096 bp as the main window for the next segment/superfamily stage.
- Keep overlap center-merge plus HMM/small-gap smoothing as the default postprocess candidate; raw threshold alone is insufficient for interval-quality claims.
- Treat embedding clustering as exploratory; C1 is a strong baseline and must be included before claiming a representation-learning improvement.

Engineering notes:

- `run_cmd_array.sh` now strips CRLF carriage returns from TSV command lines.
- 4096 superfamily required high-memory GPU retry after OOM on a 12 GB GPU.
- Two embedding retries avoided unsupported Blackwell GPU/PyTorch placement.

---

## Result: PIPE-TEFM-FINAL-GENOMEDECAY-20260630

Date: 2026-06-30

Status: semantic success, screen complete.

Scope: local genome-derived selector extension plus fragmentation council. This run used existing `PIPE-TEFM-FINAL-SELECTOR-20260630` anchor-performance rows and added deployable features computable from target genomes before TE annotation: assembly stats and bounded k-mer shift to anchor prototypes.

Primary outputs:

- `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/GENOME_DECAY_REPORT.md`
- `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/selector_genome_feature_results.json`
- `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/genome_feature_table.tsv`
- `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/anchor_pair_genome_features.tsv`
- `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/FRAGMENT_COUNCIL_REPORT.md`

Semantic success:

- Parsed 156 anchor-performance rows and generated 22 target-species genome feature rows.
- All selector outputs were written and finite.
- No target TE annotation variables were used in deployable selector features.
- `mash` and `sourmash` were unavailable, so the run explicitly used bounded k-mer shift as a screen proxy rather than MinHash distances.

Key metrics:

- Baseline deployable RF leave-species-out RMSE: `0.3042`.
- Baseline + assembly stats leave-species-out RMSE: `0.3441`.
- Baseline + bounded k-mer shift leave-species-out RMSE: `0.2666`.
- Baseline + assembly + k-mer leave-species-out RMSE: `0.3493`.
- Genome-only feature set leave-species-out RMSE: `0.3475`.

Interpretation:

- The k-mer shift result supports the user's proposal that genome-derived composition/distance features can improve anchor selection.
- Assembly N50/genome size/contiguity features are not yet reliable in this small screen; they improved in-sample fit but worsened leave-species-out error.
- Claim-grade selector work should install/version Mash or sourmash and use genome-wide or indexed stratified sampling, plus leave-clade-out validation.
- Fragment council supports replacing the current postprocess-centered path with an interval-aware component. Double-strand prediction should be a small inference sanity check only.

Claim eligibility: no. This is a screen-grade local synthesis with bounded k-mer sampling and no new full training.

---

## Result: PIPE-TEFM-FINAL-FRAGSANITY-20260630

Date: 2026-06-30

Status: semantic success, bounded screen complete.

Scope: forward/reverse-complement inference and oracle interval-repair sanity check for animal `ntv2_250m@4096` on mouse chr1. This follows the fragment council recommendation to test double-strand prediction cheaply and estimate whether an interval refiner can repair current bp-logit fragmentation.

Primary outputs:

- `reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/FRAGMENT_SANITY_REPORT.md`
- `reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/fragment_sanity/mouse_chr1.tsv`
- `reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/fragment_sanity_summary.json`
- `reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/fragment_sanity_headline_iou80_boundary5.tsv`

Semantic success:

- Slurm job `9856508` completed with `ok=true`, `n_windows=120`, and `rows=120`.
- The evaluator compared forward-only, reverse-complement-flipped-only, mean-logit, max-prob, and consensus-min merges.
- The evaluator included non-deployable oracle repairs to estimate upper bounds: connect predicted fragments within the same true interval and fill supported true intervals.
- Full 1200-window job `9856510` was cancelled after inference finished because full-length metric computation was too slow in the prototype script; it is not used as evidence.

Key metrics at IoU `0.8`, boundary `5bp`:

- Forward raw: segment-F1 `0.3062`, boundary-F1 `0.0891`.
- Forward CRF-style penalty4: segment-F1 `0.3569`, boundary-F1 `0.1016`.
- Best non-oracle: `consensus_min + crf_style_penalty4`, segment-F1 `0.4149`, boundary-F1 `0.1267`, missed true rate `0.0929`.
- `max_prob` merge was worse than forward under CRF, supporting the council warning that permissive two-strand union can add unsupported predictions.
- Oracle connect within same true interval reached segment-F1 `0.4339`.
- Oracle fill of supported true intervals reached segment-F1 and boundary-F1 `0.9711`.

Interpretation:

- Double-strand inference is not uniformly beneficial. Conservative consensus can help in this bounded mouse chr1 screen, but max/union-style merging is unsafe.
- The very high oracle-fill upper bound supports a frozen interval-refiner route: current bp predictions often touch true intervals, but postprocessing fails to recover coherent intervals.
- Next deployable experiment should train or prototype a non-oracle interval refiner from logits/local interval features, not continue broad threshold/HMM/CRF tuning.

Claim eligibility: no. This is a bounded mechanism screen, not a full-panel result.

---

## Result: PIPE-TEFM-REPAIR-20260618

Date: 2026-06-19

Status: semantic success, screen complete.

Scope: GENERanno 4096 bp single-seed repair/confirmation run for two surprising results from the previous screen: low A2 mixed-animal transfer and weak embedding clustering. The run completed archive-parity, mouse-core, and invertebrate-boost mixed-animal fine-tuning branches; A1/A2/B-panel transfer evaluation; threshold/postprocess segment sweep; 4096 large superfamily head rerun; and embedding diagnostics using clustering, pairwise similarity, and linear probe metrics.

Primary output:

- Summary status: `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/current_status.json`
- Mixed animal transfer: `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/mixed_eval.tsv`
- Segment threshold/postprocess: `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/segment_threshold.tsv`
- Superfamily: `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/superfamily.tsv`
- Embedding diagnostic: `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/embedding_diagnostic.tsv`

Semantic success:

- Slurm completion: all train, segment, embedding diagnostic, 57 eval array tasks, and summary job completed with exit code `0:0`.
- Summary completeness: `mixed_rows=57`, `segment_rows=36`, `superfamily_rows=1`, `embedding_rows=6`.
- Metric parseability: all summary TSVs parsed successfully and numeric cells were finite.
- Log check: no `Traceback`, CUDA OOM, killed process, NaN/inf, or failed job signature found in run error logs; `.err` files mainly contain progress bars and expected model-load warnings.
- Claim eligibility: screen only; cannot claim SOTA.

Key metrics:

- Mixed-animal B fine-tune held-out chromosomes show the model can annotate animal training-domain species well. Mean TE-F1: `invert_boost_animal_4096` 0.9351, `mouse_core_animal_4096` 0.9135, `p5_archive_parity_4096` 0.8205. Invert-boost gives strong TE-F1 for mouse 0.9623, chicken 0.9527, fruit_fly 0.9437, western_clawed_frog 0.9384, zebrafish 0.9080, and C. elegans 0.9054.
- A1 close vertebrate/generalization panel is high for all three branches. Mean TE-F1: archive-parity 0.9114, invert-boost 0.8985, mouse-core 0.8983.
- A2 all-species mean remains around 0.57 because held-out sparse-label invertebrates and distant stress species dominate the failure mode: invert-boost A2 mean TE-F1 0.5750, mouse-core 0.5712, archive-parity 0.5732.
- A2 vertebrate/mammal targets are strong: cattle/horse/human/opossum/pig TE-F1 is about 0.876-0.936 depending on branch. Lizard and X. laevis remain weak-to-moderate with high recall but low precision. Honeybee and beetle remain near-zero/low TE-F1 despite high recall in some settings, supporting a label/distribution/stress-panel explanation rather than a global animal-model failure.
- Segment/postprocess sweep confirms HMM smoothing remains the best interval-quality setting: threshold 0.35 + `hmm_penalty2` gives bp-F1 0.9385, segment-F1@IoU0.5 0.7339, boundary-F1@100bp 0.6181, split true TE rate 0.0456, missed true TE rate 0.0637, short predicted fragment rate 0.0938. Raw threshold has slightly higher bp-F1 at threshold 0.6 (0.9389) but much worse segment-F1 0.4846 and boundary-F1 0.4147.
- 4096 large superfamily head improves substantially when scored on the main four TE superfamilies: TE-detect F1 0.9405, class macro-F1 0.7141, main4 macro-F1 0.8927, all-6 macro-F1 0.7519, accuracy 0.9390. The `Other` class remains unlearned (`other_f1=0`, `pred_other_ratio=0`), so rare/Other should not be part of the primary superfamily claim.
- Embedding diagnostics resolve the apparent contradiction with the archived contrastive work. At length 512, C1 basic sequence features are strongest (ARI 0.9208, holdout macro-F1 0.8784, pair AUC 0.9856, linear-probe macro-F1 0.8886). A1 pretrained GENERanno embeddings are also useful (ARI 0.8000, holdout macro-F1 0.8495, pair AUC 0.9528). B1 H0 binary fine-tuned embeddings are weak for clustering (ARI 0.2822, holdout macro-F1 0.5561), indicating binary token fine-tuning degrades superfamily-clustering geometry rather than proving pretrained embeddings are poor.

Interpretation:

- The previous A2 mixed-animal low score was not because GENERanno cannot annotate animals. It was primarily a panel/label/distribution issue: matched animal species and close vertebrate transfer are strong, while held-out sparse-label invertebrates and some distant stress targets collapse under this strict bp-level one-chrom screen.
- Mouse-core is not clearly better than an invertebrate-boosted animal mixture for the broad animal goal. The best no-human animal branch here is `invert_boost_animal_4096`, because it retains high vertebrate performance and improves the animal training-domain mean.
- The archive-parity branch explains why older mixed-species runs looked good: adding a human-dominant training distribution improves human/close vertebrate behavior but does not solve beetle/honeybee and hurts some no-human animal training-domain targets such as C. elegans.
- For annotation usability, continue with overlap center-merge plus HMM-like smoothing; raw bp threshold optimization alone is not acceptable for segment-level TE annotation claims.
- For superfamily, continue the bp-level head on major classes only; rare/Other needs either exclusion from the primary macro metric, class redesign, or more targeted data.

Recommended next action:

- Run `$tri-review` on `PIPE-TEFM-REPAIR-20260618`, then decide the next pivot. The default technical direction is: keep GENERanno 4096; use `invert_boost_animal_4096` as the no-human animal branch; treat honeybee/beetle as label-source/stress diagnostics rather than primary success criteria; keep HMM smoothing for interval outputs; and use C1/A1 as representation baselines before further contrastive work.

---

## Result: PIPE-TEFM-LOCK-20260619

Date: 2026-06-19

Status: semantic success, screen complete.

Scope: GENERanno 4096 bp single-seed validation after reframe/council. The run separated primary and stress panels, audited label-source concordance, tested stress species-specific recovery fine-tuning, reran embedding objective diagnostics, expanded fragmentation/postprocess evaluation to a multi-species screen, and trained main4+Unknown five-class superfamily heads.

Primary output:

- Summary status: `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/current_status.json`
- Stress recovery eval: `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/recovery_eval.tsv`
- Stress panel audit: `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/stress_panel_audit.tsv`
- Segment multi-species screen: `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/segment_multi_species.tsv`
- Five-class superfamily: `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/superfamily5.tsv`
- Embedding objective diagnostic: `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/embedding_objective.tsv`

Semantic success:

- Slurm completion: prep, train, eval, segment, embedding, and summary jobs completed with exit code `0:0`.
- Summary completeness: `recovery_rows=8`, `sf5_rows=2`, `segment_rows=60`, `embedding_rows=6`.
- Log check: no final-run `Traceback`, CUDA OOM, killed process, missing module, or missing file signature found. Earlier canceled segment retries are excluded from the final run status.
- Metric parseability: summary TSVs parsed successfully. Segment table has `nan` only for `median_boundary_error_bp` in stress cases with no matched boundary or no true segments, not for the main bp/segment/boundary metrics.
- Claim eligibility: screen only; cannot claim SOTA.

Key metrics:

- Stress species-specific recovery confirms three of four distant low-score stress species are recoverable. On the same held-out stress test split, lizard improves from baseline TE-F1 0.2187 to adapted 0.9516; X. laevis from 0.3362 to 0.9343; western honeybee from 0.2545 to 0.8578. Red flour beetle remains poor, from 0.0043 to 0.0714.
- The stress audit supports separating primary and stress panels rather than reporting one mixed mean. Prior source-concordance values are severe for stress entries: honeybee self 4.34 Mb vs UCSC 90 kb strict TE, lizard Jaccard 0.039, X. laevis Jaccard 0.000194, and beetle Jaccard 0.027.
- Five-class main4+Unknown training works better from the original pretrained GENERanno checkpoint than from the binary H0 checkpoint. Base-pretrained SF5 reaches TE-detect F1 0.9041, main4 conditional macro-F1 0.8644, Unknown recall 0.3886, main4 false-unknown rate 0.00031, and Unknown-to-main4 error rate 0.4193. Binary-H0 SF5 has similar TE/main4 scores (TE-F1 0.8978, main4 macro-F1 0.8633) but much worse Unknown recall 0.0426 and Unknown-to-main4 error 0.4632.
- Embedding objective diagnostics confirm the older high clustering result depends on objective/protocol. C1 basic sequence features + contrastive remains strongest (ARI 0.9208, holdout macro-F1 0.8784, linear-probe macro-F1 0.8886). A1 pretrained GENERanno + contrastive is also strong (ARI 0.7987, holdout macro-F1 0.8437). Binary fine-tuned variants are weak: B0 holdout macro-F1 0.4444 and B1 0.5561.
- Fragmentation/postprocess metrics are now multi-species, not single-species: 6 primary species and 4 stress species, capped at 600 windows/species for screen speed. On the primary panel, raw threshold has bp-F1 0.9110 but segment-F1 0.2392, boundary-F1 0.1916, and short predicted fragment rate 0.7898. HMM smoothing improves to bp-F1 0.9276, segment-F1 0.5516, boundary-F1 0.4430, split true-TE rate 0.0063, and short fragment rate 0.0879. CRF-style smoothing is close but slightly lower: bp-F1 0.9273, segment-F1 0.5442, boundary-F1 0.4339.

Interpretation:

- For publication framing, primary and stress panels must be preregistered separately. The primary panel can support normal animal TE annotation claims; the stress panel should be a diagnostic/robustness panel with source-concordance and label-completeness explanations, not part of one headline mean.
- Species-specific recovery shows the model is not simply failing to understand distant animal TEs. Lizard, X. laevis, and honeybee recover strongly after small target fine-tuning, which supports a domain/label-shift explanation and a future usage mode: provide a clade/species calibration recipe. Beetle remains a hard stress failure and should be treated as a label/library/domain-risk case.
- The old embedding high scores are consistent with contrastive/probe protocols, not with the binary TE token fine-tuned embedding geometry. Unsupervised clustering failing to beat kmer/sequence-feature contrastive baselines does not disprove model usefulness; it means representation claims must compare against C1 and should not be based on binary fine-tuned embeddings alone.
- Fragmentation is still material: HMM/CRF-style smoothing reduces short fragments and improves segment/boundary quality, but segment-F1 remains far below bp-F1. The next improvement should target boundaries/segment proposals, not just bp threshold tuning.
- The main4+Unknown design is better than heterogeneous `Other`: it lets us report main4 conditional quality and Unknown reject behavior separately. The base-pretrained initialization is preferred for Unknown handling.

Recommended next action:

- Freeze this as a non-claim validation screen. For the next claim-oriented run, use GENERanno 4096, primary/stress panel split, overlap/HMM as the default interval postprocess, base-pretrained SF5 for main4+Unknown, and C1/A1 as required embedding baselines. Do not include red flour beetle in the primary success mean unless its label/library source is repaired or the task is explicitly defined as stress failure analysis.

## Result: PIPE-TEFM-EXTEND-20260620

Date: 2026-06-21

Status: semantic success, screen complete.

Scope: GENERanno 4096 bp single-seed supplemental screen after reframe/council. The run tightened embedding evidence to family-level dynamic fragments, reran base-pretrained main4+Unknown SF5, transferred `invert_boost_animal_4096` to PlantTE and cross-eval species, tested plant/cross positive-only and PU variants, evaluated PU smoothing/fragmentation, trained stress clade anchors, and extended the generalization decay formula.

Primary output:

- Final report: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/FINAL_REPORT.md`
- Summary status: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/current_status.json`
- Transfer evaluation: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/transfer_eval.tsv`
- Embedding strict screen: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/embedding_strict.tsv`
- Base-pretrained SF5: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/sf5_base.tsv`
- PU segment/postprocess: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/pu_segment.tsv`
- Decay formula: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/decay_formula/formula_fits.json`

Semantic success:

- Slurm completion: prep, embedding extract, embedding cluster, train, eval array, segment array, formula, and summary jobs completed with exit code `0:0`.
- Summary completeness: `transfer_rows=81`, `embedding_rows=20`, `sf5_rows=1`, `segment_rows=72`.
- Metric parseability: summary TSV/JSON outputs are present and parseable.
- Log check: no final-run `Traceback`, CUDA OOM, killed-process, failed-job, or NaN-loss signature found.
- Claim eligibility: screen only; ACTIVE_GOAL/SOTA/comparability contracts remain draft.

Key metrics:

- Family-level embedding screen confirms that pretrained GENERanno embeddings are useful after contrastive projection but still do not beat C1. B_animal genomic internal A1 has ARI 0.4525 / holdout macro-F1 0.5839, while C1 has ARI 0.8663 / holdout macro-F1 0.7512. B_animal boundary A1 has ARI 0.4242 / holdout macro-F1 0.5517, while C1 has ARI 0.8337 / holdout macro-F1 0.6919. D_cross internal/boundary shows the same pattern.
- Dfam consensus vs genomic fragment comparison remains incomplete because no local Dfam consensus FASTA was provided or found; the pipeline wrote a skipped metadata record instead of fabricating data.
- Base-pretrained SF5 reaches TE-detect F1 0.8982, main4 conditional macro-F1 0.8547, Unknown recall 0.3957, Unknown precision 0.6922, and main4 false-unknown rate 0.00019. This replicates the prior main4+Unknown/reject conclusion.
- `invert_boost_animal_4096` is stronger than plant/cross PU variants in most transfer summaries. It reaches plant eval-only mean TE-F1 0.7269 and plant fine-tune-species held-out mean TE-F1 0.6254; cross-eval mean TE-F1 is 0.5914. Plant/cross PU variants usually have recall near 1.0 but low precision, indicating overcalling without reliable negatives.
- On plant examples, `invert_boost` remains strong for teosinte 0.8887, maize 0.9052, rice 0.7437, and sorghum 0.8371, but weak for thale cress 0.2079 and moderate for soybean 0.5651. PU+TV helps maize slightly to 0.9091 but is not the best overall route.
- PU smoothing reduces fragmentation but does not solve overcalling. For PU+TV on soybean, raw segment-F1 is 0.0064 with short-fragment rate 0.8442; HMM penalty2 improves segment-F1 to 0.0589 and short-fragment rate to 0.0948. For teosinte, HMM penalty2 improves segment-F1 from 0.0409 to 0.1585 and short-fragment rate from 0.8527 to 0.0847.
- Stress anchor substitution is weak. `vertebrate_anchor` slightly improves the four-species stress mean TE-F1 to 0.1936 versus `invert_boost` 0.1749, but `insect_anchor` drops to 0.0496 and does not rescue beetle/honeybee.
- Generalization formula improves when label variables are included: distance-only R2 0.1870; distance + label Jaccard R2 0.4128; distance + label Jaccard + TE bp log + plant indicator R2 0.5249.

Interpretation:

- The best current robust branch remains GENERanno 4096 + `invert_boost_animal_4096`, not plant/cross PU.
- Plant transfer is not uniformly bad; the animal no-human model has surprisingly good plant performance in several species. However, plant label concordance remains low and must be used in claim framing.
- Positive-only and naive PU are not primary training routes. The main failure is high recall / low precision overcalling, and smoothing fixes fragments but not the lack of U-region penalty.
- Embedding claims must stay conservative: A1 improves over raw model embeddings, but C1 remains the family-level baseline to beat.
- Decay modeling is now plausible as a descriptive screen only if label concordance/completeness variables are included. Genetic distance alone is too weak.

Recommended next action:

- Continue the GENERanno 4096 + `invert_boost` route for claim-facing annotation validation, but keep Plant/PU/cross-kingdom as diagnostic/ablation evidence until reliable RN/hardN negatives and locked evaluator contracts exist. Supply a real Dfam consensus FASTA before making consensus-vs-genomic embedding claims.

## Result: PIPE-TEFM-CALIB-20260621

Date: 2026-06-21

Status: semantic success, screen complete.

Scope: GENERanno 4096 bp single-seed calibration supplement after user review. The run completed standard supervised plant and cross-kingdom binary fine-tuning with reliable negatives, direct honeybee/beetle diagnostic fine-tuning, insect-no-beetle anchor training, Dfam RepeatMasker consensus family-level embedding clustering, and an extended generalization-decay formula.

Primary output:

- Final report: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/FINAL_REPORT.md`
- Summary status: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/current_status.json`
- Binary eval: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/binary_eval.tsv`
- Dfam consensus embedding: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/embedding_dfam_consensus.tsv`
- Decay formula: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/decay_formula_extended/formula_fits_extended.json`

Semantic success:

- Slurm completion: prep `9245610`, embedding extract `9245611`, train `9245618`, eval `9245619`, embedding cluster `9245620`, formula `9245621`, and summary `9245622` all completed with exit code `0:0`.
- Summary completeness: `binary_eval_rows=98`, `embedding_rows=4`; expected eval outputs are complete (`binary_eval=96`, `direct_species=2`).
- Metric parseability: eval JSONs and summary TSV/JSON outputs are present, parseable, finite, and have no numeric NaN cells.
- Log check: no final-run `Traceback`, CUDA OOM, killed-process, failed-job, missing-file, or NaN-loss signature found.
- Claim eligibility: screen only; cannot claim SOTA.

Key metrics:

- Broad mean TE-F1 by model: `cross_supervised_4096` 0.5786, `TFREPAIR_invert_boost_animal_4096_seed42` 0.5413, `insect_no_beetle_4096` 0.4055, `plant_supervised_4096` 0.3858. Direct honeybee/beetle diagnostic models have fixed-threshold mean TE-F1 0.0.
- Plant fine-tune held-out panel validates the standard supervised correction. Mean TE-F1: `cross_supervised` 0.8568 and `plant_supervised` 0.8431, compared with `animal_invert_boost` 0.6254 and `insect_no_beetle` 0.5600.
- Plant eval-only remains mixed: teosinte is high for plant/cross (`plant=0.9308`, `cross=0.9300`) and animal (`0.8887`), but soybean is better for animal invert-boost (`0.5651`) than plant/cross (`~0.41`).
- Animal/vertebrate cross-eval remains strong for animal invert-boost and cross-supervised: human about 0.90, cattle about 0.92, horse about 0.89, pig about 0.876.
- Insect-no-beetle anchor rescues honeybee under the same cross/stress eval protocol (`western_honey_bee=0.7983`) but not beetle (`red_flour_beetle=0.0059`). This supports honeybee as calibratable domain/label shift and beetle as hard label/library/domain failure.
- Direct honeybee and direct beetle base-pretrained species fine-tuning do not recover fixed-threshold TE-F1. Honeybee still has ranking signal (`own_holdout AUPRC=0.3844`, cross/stress honeybee AUPRC=0.5038), while beetle remains near-no-signal (`own_holdout AUPRC=0.0026`).
- Dfam consensus family-level embedding is now executed. A1 improves over A0 (ARI 0.2242 vs 0.0796; holdout macro-F1 0.4137 vs 0.2383), but C1 basic features + contrastive remains much stronger by ARI/NMI (ARI 0.7083, NMI 0.7135).
- Extended decay formula over 244 rows improves from distance-only R2 0.0396 to full variable R2 0.7407 when label/source, TE amount/composition, GC, train-clade coverage, stress, kingdom, and insect indicators are included.

Interpretation:

- The user was right that plant/cross standard supervised fine-tuning had to be tested separately from PU. With reliable negatives, plant/cross supervised training is useful and substantially improves plant held-out species.
- The correct model choice is panel-specific, not one mixed mean. Cross-supervised is the best broad screen mean and best plant-fine branch; animal invert-boost remains slightly stronger on broad cross-eval and stress means.
- PU remains abandoned as a primary route. Its failure mode is still overcalling without reliable negative control; smoothing/postprocess is not a substitute for RN/hardN design.
- Insect-no-beetle should be treated as a honeybee stress-anchor diagnostic, not a general insect rescue. Beetle remains excluded from primary means unless label/library evidence is repaired.
- Dfam consensus embedding closes the prior missing branch but does not support FM embedding superiority; C1 remains the required baseline.
- Generalization decay should be framed as source-aware. Genetic distance alone is too weak and can be misleading.

Recommended next action:

- Continue claim-prep around GENERanno 4096 with panel-specific reporting: carry forward both `cross_supervised_4096` and `invert_boost_animal_4096` as robust branches, retain insect-no-beetle for honeybee diagnostics, keep C1/A1 embedding baselines, and lock evaluator/comparability contracts before Track B validation.

## Result: PIPE-TEFM-ANCHOR-20260621

Date: 2026-06-21

Status: semantic success, screen complete.

Scope: GENERanno 4096 bp single-seed anchor/Unknown/background supplement. The run trained an insect-primary branch, evaluated animal/cross/insect anchors on stress species, tested background-inclusive embedding clustering, classified Unknown and high-score unannotated candidates with the SF5 head, and fitted deployable versus annotation-aware anchor recommendation formulas.

Primary output:

- Final report: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/FINAL_REPORT.md`
- Status summary: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summaries/current_status.json`
- Binary eval: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summaries/binary_eval.tsv`
- Embedding summary: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summaries/embedding_bg_unknown.tsv`
- SF5 candidates: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/sf5_candidate_summary.json`
- Anchor formula: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/anchor_formula/anchor_formula_results.json`

Semantic success:

- Slurm completion: prep, train, diagnostic extraction, eval, embedding, SF5 CPU retry, formula, and summary completed with exit code `0:0`.
- Summary completeness: `binary_eval_rows=24`, `embedding_rows=8`, SF5 candidate summary present, anchor formula present.
- Metric parseability: 24/24 binary eval JSONs are present and parseable; summary TSV/JSON outputs are finite.
- Log check: the original SF5 job `9288901_1` failed on a Transformers/PyTorch model-loading safety gate and was superseded by CPU-bigmem retry `9298759`, which completed. Final accepted outputs have no unresolved Traceback, CUDA OOM, killed process, missing-file, or NaN-loss signatures.
- Claim eligibility: screen only; selector/formula is not claim-grade until locked panel validation.

Key metrics:

- `insect_primary_4096` has the best six-species stress mean TE-F1 among the tested anchors: 0.5197 versus `insect_no_beetle_4096` 0.4520, `invert_boost_animal_4096` 0.4248, and `cross_supervised_4096` 0.4134.
- Honeybee is recovered by insect-primary training: `western_honey_bee` TE-F1 is 0.9465 for `insect_primary_4096`, compared with 0.0522 for animal invert-boost and 0.0053 for cross-supervised.
- Beetle remains unrecovered across anchors: red flour beetle TE-F1 stays about 0.003-0.006. This supports excluding beetle from primary means and treating it as label/library/domain failure until annotation evidence is repaired.
- Fruit fly and C. elegans remain strong under existing animal/cross anchors; insect-primary preserves high fruit fly 0.9414 and C. elegans 0.8946.
- Background-inclusive embedding still favors basic sequence features plus contrastive projection. For `bg_main4`, C1 reaches ARI 0.8353 / holdout macro-F1 0.7360, while A1 GENERanno embedding + contrastive reaches ARI 0.4067 / holdout macro-F1 0.5630. For `unknown_highscore`, C1 reaches ARI 0.8600 / holdout macro-F1 0.7598, while A1 reaches ARI 0.4049 / holdout macro-F1 0.4949.
- SF5 on 260 Unknown-annotation segments shows substantial main4-like signal: mean best-main4 fraction 0.4706, mean Unknown fraction 0.0620, and mean BG fraction 0.3826. The strongest assigned main4 buckets are DNA and SINE.
- SF5 on strict high-score unannotated candidates does not support a hidden-TE claim in this screen: only 9 candidates pass the strict filter and their mean BG fraction is 0.9974.
- Deployable anchor formula deliberately excluding target TE-annotation variables is useful but still rough: random forest R2 0.7631 in-sample and leave-species-out RMSE 0.3467. Annotation-aware controls confirm label/source variables are explanatory but should not be used for deployment selection.

Interpretation:

- The recommended external-facing model strategy is panel/kingdom-specific, not a single universal mean. Use animal/vertebrate, plant/cross, and insect-primary branches separately, with beetle-style stress failures reported outside primary means.
- Unknown recall cannot simply be sold as a virtue, but Unknown segments with high main4 posterior are a legitimate annotation-audit opportunity. They need cluster support and independent evidence before relabeling.
- High-score unannotated strict-background regions are mostly classified as BG here, so this run does not support a strong model-only novel TE claim.
- FM embeddings improve over raw embeddings after contrastive projection, but C1 remains the strongest clustering baseline even when background sequences are included.
- The deployable selector should use variables available for a new genome before TE annotation, such as kingdom/clade, distance to anchor, GC/kmer shift, anchor type, and training-panel coverage. Annotation-aware formulas are explanatory controls only.

Recommended next action:

- Proceed with panel-specific Track B planning: carry forward `invert_boost_animal_4096`, `cross_supervised_4096` or plant-supervised for plants, and `insect_primary_4096` for honeybee-like insects; keep beetle as stress/audit. Do not claim FM embedding superiority or model-only TE discovery from this screen.

## Result: PIPE-TEFM-FINAL-20260623 NTv3 recovery and model-size matrix closure

Date: 2026-06-29

Status: semantic success after runtime repairs; screen complete for the model-size/window matrix.

Scope: final supplementation of NTv2/NTv3 model-size x window comparison. This entry closes the previously blocked NTv3 branch: NTv3 HF token access, remote-code smoke, single-base label alignment, checkpoint reload, human H0 training, and animal/plant one-chromosome generalization eval all completed.

Primary outputs:

- Matrix summary: `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`
- Status summary: `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/current_status.json`
- NTv3 eval JSONs: `reports/tefm_final/PIPE-TEFM-FINAL-20260623/matrix_eval/ntv3_*`
- Code-review/runtime log: `docs/21_code_review_log.md`

Semantic success:

- NTv3 download/smoke: download retry `9838465` and serial smoke `9838992` completed for all six NTv3 checkpoints.
- NTv3 train: corrected train retries `9839610` and `9839611` produced 30/30 `test_results.json` files; no failed/OOM/NaN Slurm records in the accepted train jobs.
- NTv3 eval: first eval arrays `9844255`/`9844256` failed before metrics due to rotary cache checkpoint loading; this was repaired and superseded by retry arrays `9845158`/`9845159`, which produced 330/330 NTv3 matrix JSONs.
- Final summary: `matrix_eval.tsv` now has 495 rows, matching 165 NTv2 + 330 NTv3 expected rows.
- Claim eligibility: screen only; no SOTA claim or final anchor recommendation until error-bar/repeat and locked selector follow-ups.

Key metrics:

- Human H0 training-screen best overall remains `ntv2_250m_H0_w4096_seed42`: TE-F1 `0.93494`, macro-F1 `0.93627`, AUPRC `0.98395`.
- Best NTv3 human H0 training-screen row is `ntv3_650m_pre_H0_w4096_seed42`: TE-F1 `0.91962`, macro-F1 `0.92137`, AUPRC `0.97752`.
- Best animal_fine generalization mean is `ntv2_250m` at 4096 bp: mean TE-F1 `0.64823` over 6 species. The next NTv3 entry is `ntv3_100m_pre` at 2048 bp with animal_fine mean `0.58223`; `ntv3_650m_pre_8kb` at 4096 bp reaches `0.55296`.
- Best plant_fine mean is `ntv3_100m_pre` at 2048 bp: mean TE-F1 `0.39802` over 5 species. Plant transfer remains low in absolute terms and should not be interpreted as solved by backbone scaling alone.
- Best combined animal+plant mean is `ntv3_100m_pre` at 2048 bp: mean TE-F1 `0.49850` over 11 species, largely because it is more balanced on plant_fine while NTv2-250M remains stronger on animal_fine.

Interpretation:

- Parameter scaling improves in-domain H0 for both NTv2 and NTv3, but larger NTv3 does not dominate cross-species transfer. NTv2-250M/4096 remains the best animal_fine and human H0 screen combination.
- NTv3 adds useful diversity for plant_fine and combined animal+plant means, especially `NTv3_100M_pre` at 2048 bp. This supports keeping model family as an axis in the final selector rather than choosing by parameter count alone.
- The 8kb NTv3 checkpoints are not uniformly better than non-8kb checkpoints in this TE task. The best NTv3 H0 row is non-8kb 650M at 4096 bp.
- The checkpoint reload failure from rotary cache buffers is an engineering issue now fixed; failed eval jobs `9844255`/`9844256` must not be used as model evidence.

Recommended next action:

- Use `ntv2_250m@4096` as the current animal/generalization screen leader and `ntv3_100m_pre@2048` as the strongest plant/combined NTv3 challenger for the next error-bar and multi-anchor stage. Keep panel-specific reporting; do not collapse animal and plant into one headline mean.

## Result: PIPE-TEFM-FINAL-EBAR/STRICTSEG/PLANTQC-20260629

Date: 2026-06-30

Status: semantic success after strict-evaluator repairs; Track-B support screen complete.

Scope: chromosome-repeat error bars for the promoted final matrix candidates, plant label/source QC, and strict segment/boundary/fragmentation evaluation with IoU thresholds `0.5/0.7/0.8/0.9` and boundary tolerances `5/10/25/50/100` bp.

Primary outputs:

- Error-bar summaries: `reports/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/summaries/eval_panel_summary.tsv`
- Plant QC: `reports/tefm_final/PIPE-TEFM-FINAL-PLANTQC-20260629/plant_label_qc.tsv`
- Strict segment summary: `reports/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/summaries/strict_segment_summary.tsv`
- Strict headline table: `reports/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/summaries/strict_segment_headline_iou80_boundary5.tsv`

Semantic success:

- Error-bar prep/eval jobs `9849317` and `9849318` completed and produced 66/66 eval JSONs.
- Strict segment first job `9849319` produced valid NTv2 rows but failed NTv3 rows from an NTv3 tokenizer max-length mismatch; NTv3 retry `9850150` completed 33/33 rows after using `training_meta.token_label_mode`.
- NTv2 strict rows were then re-run as `9852364` after fixing k-mer token probability projection back to bp spans for `EsmTokenizer`; final strict summary has 66/66 JSONs and 6600 rows.
- Claim eligibility: Track-B support only; still not a final SOTA claim.

Key metrics:

- Chromosome-repeat error bars preserve the panel-specific conclusion. `ntv2_250m@4096` animal_fine mean TE-F1 is `0.6431` over 18 chromosome/species rows, while `ntv3_100m_pre@2048` animal_fine mean is `0.5300`.
- Plant_fine favors `ntv3_100m_pre@2048`: mean TE-F1 `0.3833` over 15 chromosome/species rows versus `0.1733` for `ntv2_250m@4096`.
- Plant label/source QC remains a major confounder: 7 plant rows have mean self Label-A vs UCSC/local strict-TE Jaccard `0.0784` (min `0.0427`, max `0.1216`).
- Strict segment, IoU `0.8` and boundary `5` bp: animal_fine `ntv2_250m@4096` best variant is `crf_style_penalty4` with bp-F1 `0.6453`, segment-F1 `0.2557`, boundary-F1 `0.0989`.
- Strict segment, IoU `0.8` and boundary `5` bp: plant_fine `ntv3_100m_pre@2048` best variant is `gap100_min100` with bp-F1 `0.4585`, segment-F1 `0.0305`, boundary-F1 `0.0033`.
- Fragmentation is real under raw thresholds. For animal_fine `ntv2_250m@4096`, raw threshold has about `4359.9` short predicted fragments per row; CRF-style smoothing reduces this to `850.2` while improving strict segment-F1. Gap100/min100 almost eliminates short fragments (`5.5`) but increases missed true TE rate.

Interpretation:

- The final recommendation should be panel-specific: `ntv2_250m@4096` for animal/human-style transfer and `ntv3_100m_pre@2048` for plant diagnostics.
- Strict interval metrics are much harsher than prior IoU50/boundary100 summaries, validating the user's concern that old thresholds were too lenient.
- Smoothing/postprocess improves usability but does not solve boundary accuracy. CRF/HMM-style smoothing preserves more true fragments; aggressive gap/min-length filtering removes short false fragments but also misses more true TEs.
- Plant transfer should be reported with label-source caveats; low strict plant segment metrics cannot be interpreted as model failure alone.

Recommended next action:

- Promote panel-specific anchors into the multi-anchor selector/decay-formula stage, but keep strict interval/boundary metrics as a separate usability claim rather than implying bp-F1 alone gives complete TE annotations.

## Result: PIPE-TEFM-FINAL-SELECTOR-20260630

Date: 2026-06-30

Status: semantic success; local evidence synthesis complete.

Scope: final multi-anchor selector and NTv2-500M species-specific recovery/annotation-quality audit using existing completed results. This analysis does not train new models; it separates target-label species-specific fine-tuning as an audit/upper-bound from non-species-specific anchors usable by a deployable selector.

Primary outputs:

- Final report: `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/FINAL_REPORT.md`
- Species-probe audit: `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/species_probe_quality_audit.tsv`
- Anchor performance matrix: `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/anchor_performance_matrix.tsv`
- Multi-anchor recommendations: `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/multi_anchor_recommendations.tsv`
- Selector formula: `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/selector_formula_results.json`

Semantic success:

- Parsed 22 NTv2-500M species-probe rows and 156 non-species-specific anchor performance rows from existing result tables.
- Generated 22 species-level multi-anchor recommendations.
- Selector features deliberately exclude target TE annotation variables in the deployable model; annotation-aware variables are kept only as explanatory controls.
- Claim eligibility: screen/triage only; selector requires locked validation and tri-review before deployment claims.

Key metrics:

- Species-specific NTv2-500M fine-tune remains poor for `red_flour_beetle` (TE-F1 `0.1494`) and `thale_cress` (TE-F1 `0.4168`). These are audit-label-first species, not automatic training-panel exclusions.
- Partial recovery / caution species: `soybean` (TE-F1 `0.5797`) and `c_elegans` (TE-F1 `0.7667`).
- Many low-concordance plant/amphibian/reptile species can still be calibrated by species-specific fine-tuning, for example rice `0.8075`, maize `0.9353`, lizard `0.9468`, and X. laevis `0.9368`. This supports domain/label-shift interpretation rather than global model failure.
- Observed multi-anchor oracle mean over 22 species is `0.7787`, compared with the best broad single model with at least five rows, `cross_supervised_4096`, mean TE-F1 `0.5432` over 28 rows. This supports a multi-anchor reporting strategy.
- Deployable random-forest selector has in-sample R2 `0.8203` and leave-species-out RMSE `0.3040`; annotation-aware control improves to leave-species-out RMSE `0.2791`, confirming label/source variables explain residuals but should not be used for new-genome deployment.

Interpretation:

- Multi-anchor strategy is now empirically supported as a screen conclusion: animal/human, plant/cross, and insect-specific anchors solve different target panels.
- Red flour beetle remains the hardest label/library/domain-risk species because it is poor even after target fine-tuning.
- The deployable selector is promising as a triage tool, but its leave-species-out error is too high for a strong deployment claim.
- Species-probe recovery is a soft annotation-quality audit and calibration upper-bound, not a standalone exclusion rule.

Recommended next action:

- Keep multi-anchor selector as a screen-complete component, then run claim-grade selector validation/tri-review only after final claim panel and external baseline contracts are locked. Continue separately with the short high-confidence TE fragment / interpretability branch.

## Result: PIPE-TEFM-FINAL-INTERPRET-20260630

Date: 2026-06-30

Status: semantic success; local fragment interpretability screen complete.

Scope: screen-level summary of short high-confidence unannotated/background candidates and Unknown-annotation fragments from the existing `PIPE-TEFM-ANCHOR-20260621` fragment/SF5 outputs. This analysis does not train a model and does not perform saliency/occlusion yet.

Primary outputs:

- Report: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/INTERPRETABILITY_REPORT.md`
- Status: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/current_status.json`
- Feature table: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/fragment_feature_table.tsv`
- Source summary: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/source_feature_summary.tsv`
- High-score strict-BG cases: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/high_score_strict_bg_cases.tsv`
- Unknown main4-like candidates: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/unknown_main4_like_top30.tsv`

Semantic success:

- Parsed 1409 fragment rows: 880 known main4, 260 Unknown annotation, 260 strict background negatives, and 9 high-score strict-background candidates.
- Merged SF5 candidate predictions where available and computed GC, 2-bit entropy, homopolymer, and top 6-mer summaries.
- Script compiled and ran successfully. `current_status.json` reports `ok=true`.
- Independent tri-review completed with 3/3 quorum. All reviewers selected `run-sanity-check-first`, rejected hidden-TE language for strict-BG candidates, and supported Unknown-main4-like annotation audit only after matched controls.
- Claim eligibility: exploratory/screen only; no hidden-TE or model-interpretability claim until matched controls plus saliency/occlusion/motif tests are run.

Key metrics:

- High-score strict-background candidates: n=9, mean binary TE probability `0.8893`, but mean SF5 background fraction `0.9974`.
- Unknown-annotation fragments: n=260, mean best-main4 SF5 fraction `0.4706`, mean Unknown fraction `0.0620`, mean BG fraction `0.3826`.
- The high-score strict-background cases are AT-rich in this screen (mean GC `0.1530`) compared with strict background negatives (mean GC `0.3821`) and known main4 fragments (mean GC `0.4092`).

Interpretation:

- The current high-score strict-background candidates do not support a hidden-TE discovery claim: they are high under the binary detector but nearly all BG under SF5.
- Unknown-annotation fragments are stronger annotation-audit candidates because many receive coherent main4-like SF5 signal.
- The next interpretability step should use matched controls and model-level attribution, especially high-score strict-BG versus matched BG and Unknown-main4-like versus known main4, with saliency/occlusion/k-mer motif enrichment.
- The three referenced PDFs under `docs/inputs/` are present, but this environment lacks a PDF text extractor, so full paper-derived method alignment is still pending.

Recommended next action:

- Keep this as a conservative screen result. Do not claim novel/hidden TE from binary spikes alone; prioritize Unknown-main4-like annotation audit, matched strict-BG controls, saliency/occlusion, and k-mer motif enrichment after installing or providing a PDF text extraction path.

### Matched-control addendum 2026-06-30

Status: semantic success; local matched-control sanity check complete.

Additional outputs:

- Matched-control report: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/MATCHED_CONTROL_REPORT.md`
- Matched pairs: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/matched_control_pairs.tsv`
- Match-quality summary: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/matched_quality_summary.tsv`
- K-mer enrichment: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/matched_kmer_enrichment.tsv`
- PDF method alignment: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/pdf_method_alignment.md`

Semantic success:

- `pypdf` was installed in the user Python site and extracted text from the first eight pages of all three requested PDFs.
- High-score strict-BG matched controls were built within the same species and chromosome (`western_honey_bee`, `GroupUn`): 9/9 candidates matched from a 63-row strict-BG pool.
- Unknown-main4-like controls were built within human known-main4 fragments: 32/32 candidates at SF5 best-main4 fraction `>=0.8` matched from a 661-row human known-main4 pool.
- The script compiled and ran successfully; `matched_control_status.json` reports `ok=true`.

Key metrics:

- High-score strict-BG match quality is acceptable for a composition screen: mean absolute GC delta `0.0521`, mean match distance `1.2163`, quality flag `ACCEPTABLE_COMPOSITION_SCREEN`.
- Unknown-main4-like matching fails the GC-control sanity check: case mean GC `0.6638` vs matched-control mean GC `0.3920`, mean absolute GC delta `0.2723`, quality flag `POOR_GC_MATCH`.
- Unknown-main4-like k-mer enrichment is dominated by GC-rich motifs such as `CGCCCC`, `CGGACG`, and `GGGCAG`, consistent with a high-GC/SVA-like or model-bias audit signal rather than clean main4 relabeling.
- PDF keyword alignment confirms the requested literature set covers attribution/saliency-style methods: `1703.01365v2.pdf` contains integrated-gradients/attribution hits; `2009.07896v1.pdf` contains saliency/occlusion/attribution hits; `ocag070.pdf` had only weak attribution keyword signal in the first eight scanned pages.

Interpretation:

- The high-score strict-BG branch remains a false-positive/trigger-diagnosis branch. It is now better controlled within honeybee `GroupUn`, but n=9 is still too small for prevalence or hidden-TE claims.
- The Unknown-main4-like branch is not ready for annotation correction because matched human known-main4 controls cannot match the GC distribution. The safer interpretation is high-GC/SVA/model-bias audit, followed by coordinate-level RepeatMasker/Dfam/UCSC inspection.
- This addendum completes matched controls, k-mer enrichment, and PDF text extraction at screen level. Model-level saliency/occlusion remains pending and should run as a small Slurm smoke rather than a foreground login-node job.

Recommended next action:

- If interpretability remains publication-relevant, submit a bounded model-level attribution/occlusion smoke on the two contrasts. Until then, manuscript language should say the matched-control audit weakens automatic Unknown relabeling and further rejects hidden-TE wording for strict-BG spikes.

### Model occlusion smoke addendum 2026-06-30

Status: semantic success after runtime repair; bounded Slurm GPU inference completed.

Additional outputs:

- Occlusion report: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/OCCLUSION_SMOKE_REPORT.md`
- Occlusion status: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/occlusion_smoke/occlusion_status.json`
- Occlusion summary: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/occlusion_smoke/occlusion_summary.tsv`
- Occlusion detail: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/occlusion_smoke/occlusion_detail.tsv`

Semantic success:

- Initial one-by-one and full-window-context submissions were cancelled because they were too slow for a bounded smoke. The accepted job `9853298` used fragment-length context and completed with Slurm state `COMPLETED`, exit code `0:0`.
- Output status reports `ok=true`, device `cuda`, 34 fragments, 612 detail rows, chunk size 64 bp.
- Numeric occlusion summary/detail values are finite.

Key metrics:

- High-score strict-BG does not reproduce as high-score in 512 bp fragment context: original binary mean is `0.0205` for cases and `0.0045` for matched controls.
- High-score strict-BG SF5 main4 score remains zero and unchanged by occlusion.
- Unknown-main4-like cases retain high SF5 main4 scores in fragment context: original mean `0.8982` for cases versus `0.6250` for matched known-main4 controls.
- Unknown-main4-like SF5 occlusion sensitivity is strong: mean delta `0.3028`, max delta `0.7285`; matched known-main4 controls have mean delta `0.0630`.
- Unknown-main4-like binary occlusion sensitivity is modestly higher than controls: mean delta `0.0916` versus `0.0698`.

Interpretation:

- The strict-BG branch should be treated as a full-window false-positive/context-trigger diagnostic. Isolated 512 bp occlusion does not support hidden TE.
- The Unknown branch has real local model sensitivity under SF5, but because matched controls failed GC matching, this remains high-GC/SVA-like/model-bias annotation audit rather than automatic relabeling.
- Claim-grade interpretability would need full-window context, alternate perturbation baselines, better GC-matched controls, and coordinate-level RepeatMasker/Dfam/UCSC audit.

Recommended next action:

- Do not continue expanding this branch unless it becomes a figure-level claim. If promoted, repeat with full-window context and better-matched Unknown controls before tri-review.

## Result: PIPE-TEFM-FINAL-INTERVALREFINER-20260630

Date: 2026-06-30

Status: semantic success for bounded 40-window smoke; larger 120-window prototypes were cancelled before evidence generation.

Scope: deployable frozen-bp interval-refiner prototype on mouse chr1 using the existing `ntv2_250m@4096` animal model probability track. The prototype trains lightweight keep/drop and gap-merge classifiers on the first 60% of the bounded coordinate range and evaluates on the held-out 40%.

Primary outputs:

- Report: `reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/INTERVAL_REFINER_REPORT.md`
- Metrics: `reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/interval_refiner_metrics.tsv`
- Status: `reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/interval_refiner_status.json`

Semantic success:

- Slurm job `9856944` completed with state `COMPLETED`, exit code `0:0`, elapsed `00:00:53`.
- Status JSON reports `ok=true`, `n_windows=40`, `prob_mode=consensus_min`.
- Metrics TSV is parseable and contains six test variants under IoU `0.8` and boundary tolerance `5 bp`.
- Earlier 120-window jobs `9856920`, `9856939`, and `9856942` were cancelled before producing TSV/JSON and are not evidence.

Key metrics:

- Test `consensus_min_raw`: segment-F1 `0.4462`, boundary-F1 `0.1385`, missed true rate `0.0161`.
- Test `consensus_min_crf`: segment-F1 `0.4685`, boundary-F1 `0.1261`, missed true rate `0.0161`.
- Best deployable refiner variant, `refiner_keep_drop_gap_merge`: segment-F1 `0.4667`, boundary-F1 `0.1167`, missed true rate `0.0161`.
- Truth-aware `oracle_fill_supported_true`: segment-F1 `0.9919`, boundary-F1 `0.9919`, missed true rate `0.0161`.

Interpretation:

- The deployable lightweight interval refiner does not beat consensus+CRF in this bounded smoke. It modestly reduces short predicted segments but loses strict boundary performance.
- The oracle result confirms that the base bp probabilities often overlap the true TE intervals; the missing component is not more threshold/gap tuning, but a richer interval/boundary-aware objective or decoder.
- This closes the current post-hoc refiner prototype as weak evidence and supports the council recommendation to move to segment-aware decoder, boundary-aware head, interval proposal/refiner with richer context, or semi-Markov/duration-aware decoding.

Recommended next action:

- Do not scale this exact lightweight post-hoc refiner. If fragment usability becomes a claim-bearing component, implement a structurally trained interval/boundary module and keep guardrails: strict IoU/boundary, missed_true_rate, pred_true_backed_rate, short_true_backed_rate, and deleted true-backed vs false-positive fragments.

## Result: PIPE-TEFM-NEXT-DECAY-FRAG-20260630

Date: 2026-06-30

Status: semantic success for selector calibration/action-policy diagnostics and bounded trainable-fragment-decoder smoke; no claim-grade selector or decoder improvement achieved.

Scope: follow-up to the genome-derived selector and fragmentation council. This run tests whether the current decay formula can be converted into useful new-species trust guidance and whether trainable boundary/CRF/duration decoders on frozen bp tracks improve strict segment usability over post-hoc CRF.

Primary outputs:

- Final report: `reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/FINAL_REPORT.md`
- Selector calibration: `reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_calibration/`
- Selector action policy: `reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_action_policy/`
- Trainable decoder smoke: `reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/trainable_fragment_decoders/`
- Tri-review raw outputs: `/tmp/tri_review_PIPE-TEFM-NEXT-DECAY-FRAG-20260630/`
- Council raw outputs: `/tmp/council_tefm_decay_fragment_20260630/`

Semantic success:

- 3/3 tri-review outputs completed and agreed the selector is not yet a reliable point-confidence formula.
- Two-round council completed and recommended bounded selector abstention/routing plus bounded structural fragmentation MVPs rather than a single large coupled project.
- Selector scripts compiled and ran; JSON/TSV outputs are parseable and finite.
- Trainable decoder Slurm job `9858072` completed with state `COMPLETED`, exit code `0:0`, elapsed `00:01:34`.
- `trainable_fragment_decoder_status.json` reports `ok=true`, `n_windows=40`, `train_fraction=0.6`, mouse `chr1` test bp `65536`.

Key metrics:

- Best point selector: `baseline_plus_kmer / leave_species_out`, RMSE `0.2642`, MAE `0.2194`, ECE `0.0372`, top-1 anchor accuracy `0.4545`, top-2 accuracy `0.6818`, mean regret `0.0680`; usable point-formula gate `false`.
- Leave-clade-out selector remains poor across feature sets, with RMSE about `0.40-0.42`; do not use it for distant-clade trust claims.
- Best action policy: top-2/local-probe routing contains true best/top2 anchor for `0.8636` of species and has mean regret after action `0.0071`, but single-anchor high-confidence coverage is `0.0`.
- Decoder strict metrics at IoU `0.8`, boundary `5 bp`: post-hoc `consensus_min_crf_posthoc` segment-F1 `0.4685`, boundary-F1 `0.1261`; `trainable_boundary_cnn` segment-F1 `0.2778`; `duration_prior_decoder` `0.2366`; `trainable_linear_crf` `0.1798`.
- Duration prior increased missed true rate to `0.0484` and deleted true-backed signal; it is not a safe standalone fragment suppressor.

Interpretation:

- The current generalization-decay formula is still not usable as a calibrated point estimate of model trustworthiness on a new species.
- A conservative top-2 selector plus local chromosome probe is the only defensible screen-level deployment form within known clades.
- Frozen-probability trainable decoders did not improve strict interval usability. This does not refute trainable CRF/boundary heads generally; it refutes the weak version attached after frozen bp probability tracks.
- Next fragmentation work should use backbone embeddings or richer emissions, boundary-aware heads, segment/interval proposal scoring, and the existing true-backed deletion guardrails.

Recommended next action:

- Do not scale the current point selector or frozen-logit decoder variants. For selector claim-grade work, add public taxonomy/MinHash or Mash/sourmash distances and validate leave-clade-out with abstention. For fragmentation, implement a near-backbone boundary/interval head or richer interval proposal/scorer before trying trainable CRF/semi-Markov decoding again.

## Result: PIPE-TEFM-STRUCTDEC-20260630

Date: 2026-06-30

Status: semantic success after one environment repair; bounded single-seed joint structured decoder smoke complete.

Scope: first test of HMM/CRF/semi-Markov-style structured objectives as trainable backend components attached to GENERanno token logits during fine-tuning. This differs from previous post-hoc HMM/CRF smoothing and frozen-logit decoder screens.

Primary outputs:

- Report: `reports/tefm_final/PIPE-TEFM-STRUCTDEC-20260630/JOINT_STRUCTURED_DECODER_REPORT.md`
- Metrics: `reports/tefm_final/PIPE-TEFM-STRUCTDEC-20260630/joint_structured_decoder_metrics.tsv`
- Status: `reports/tefm_final/PIPE-TEFM-STRUCTDEC-20260630/joint_structured_decoder_status.json`
- Code-review gate: `outputs/PIPE-TEFM-STRUCTDEC-20260630/code_review_gate.json`

Semantic success:

- First Slurm job `9860192` failed before training because default compute-node Python was 3.9 and GENERanno remote code requires Python 3.10+ syntax. This is recorded as an environment repair, not a model result.
- Retry job `9860193` used `/home/users/j/jwang/.conda/envs/te_benchmark/bin/python`, completed with state `COMPLETED`, exit code `0:0`, elapsed `00:10:32`, MaxRSS `5558284K`.
- Status JSON reports `ok=true`, seed `42`, device `cuda`, `freeze_backbone=false`.
- Metrics TSV is parseable and contains val/test rows for CE baseline, joint HMM, joint CRF, and joint semi-Markov proxy.
- Claim eligibility: smoke only; bounded human H0 quick-data subset, not a final annotation-usability result.

Key test metrics at IoU `0.8`, boundary `5 bp`:

- `ce_baseline`: bp-F1 `0.7406`, segment-F1 `0.3069`, boundary-F1 `0.1414`, missed_true_rate `0.2623`, predicted segments `336`.
- `joint_hmm`: bp-F1 `0.8472`, segment-F1 `0.3836`, boundary-F1 `0.2046`, missed_true_rate `0.3033`, predicted segments `147`.
- `joint_crf`: bp-F1 `0.8579`, segment-F1 `0.3631`, boundary-F1 `0.0921`, missed_true_rate `0.1721`, predicted segments `125`.
- `joint_semimarkov_proxy`: bp-F1 `0.8690`, segment-F1 `0.4258`, boundary-F1 `0.2105`, missed_true_rate `0.3033`, predicted segments `174`.

Interpretation:

- The user’s concern was correct: the fully trainable backend direction had not been tested before. Previous failures were weaker post-hoc/frozen-probability versions.
- The direction is not a failure. All structured objectives improved strict segment-F1 over CE baseline in this bounded smoke, with semi-Markov proxy best for segment/boundary metrics.
- It is not solved either. The best segment/boundary variant increases missed true rate; the CRF variant preserves true intervals better but has poor boundary-F1.
- The next version should combine joint structured training with explicit boundary supervision and true-retention penalty, then evaluate on the mouse strict segment panel used in prior fragmentation screens.

Recommended next action:

- Keep this route alive as a promising but unproven structural direction. Do not declare HMM/CRF/semi-Markov solved; run one stronger bounded iteration with boundary-aware loss and missed-true guardrail before scaling.

## Result: PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630

Date: 2026-06-30

Status: semantic success for bounded selector router and joint structured-decoder iteration; no SOTA claim and no decoder promotion.

Scope: `$pursue` cohort with two publication-validation support components: A) convert the unusable point-estimate generalization formula into a conservative trust router using deployable genome-derived features only, and B) continue the GENERanno 4096 joint structured backend route with boundary-aware and true-retention losses.

Primary outputs:

- Selector conservative router: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/conservative_router/`
- Decoder report: `reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/JOINT_STRUCTURED_DECODER_REPORT.md`
- Decoder metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/joint_structured_decoder_metrics.tsv`
- Decoder status: `reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/joint_structured_decoder_status.json`
- Code-review gate: `outputs/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/code_review_gate.json`

Semantic success:

- Selector script compiled and completed locally; status JSON reports `ok=true`, `deployable_features_only=true`, and `target_te_annotation_features_excluded_from_selector=true`.
- Decoder Slurm job `9860400` completed with state `COMPLETED`; `job_watch` wrote `outputs/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/STATUS=COMPLETED`.
- Decoder status JSON reports `ok=true`, seed `42`, device `cuda`, `freeze_backbone=false`, and parseable val/test rows for CE, joint HMM, joint CRF, semi-Markov proxy, boundary auxiliary loss, and semi-Markov retention loss.
- No OOM, NaN, traceback, or missing-file failure was observed in the final Slurm log; model-load warnings are expected for the local GENERanno token-classification wrapper.
- Claim eligibility: cannot claim SOTA; this is bounded screen support only.

Key metrics:

- Selector selected router gate passed. In leave-species-out/in-panel mode, `baseline_plus_kmer` top-2 shortlist contains the true best anchor for `0.8636` of species, mean regret after top-2 local probe is `0.0071`, p90 regret is `0.0008`, ECE is `0.0372`, and single-anchor high-confidence coverage is `0.0`.
- Selector leave-clade-out mode is not trusted as a formula: selected policy uses explicit abstention for all leave-clade-out species, with local-probe recommended rate `1.0`. The best leave-clade top-2 contains-best rate is only `0.6364`, so distant/new clades require local probe or a new anchor.
- Decoder CE baseline test: segment-F1@IoU0.8 `0.3069`, boundary-F1@5bp `0.1414`, missed_true_rate `0.2623`.
- Decoder best test segment row: `semimarkov_retention`, segment-F1 `0.4439`, boundary-F1 `0.2290`, missed_true_rate `0.3525`, pred_true_backed_rate `0.9402`, short_true_backed_rate `0.8438`.
- Decoder promotion gate failed because missed_true_rate rose by `0.0902` over CE baseline, exceeding the allowed `+0.03` despite segment and boundary improvements.
- CE-relative deletion diagnostics show `semimarkov_retention` deleted `168` baseline fragments, of which `83` were true-backed and `85` false; deleted_true_backed_fraction `0.4940`. This is not acceptable as a pure false-fragment cleanup.

Interpretation:

- The selector is now defensible only as a conservative router: in known/in-panel settings, recommend top-2 anchors plus a local chromosome probe; for leave-clade/new-clade settings, abstain rather than give a confident anchor.
- This does meet the user’s minimum router gate for avoiding confidently wrong anchor calls, but it remains a triage system, not a calibrated F1 formula.
- Boundary-aware/retention training improved strict segment and boundary metrics, confirming the joint structured route has real signal.
- The true-retention problem is not solved. The best variant still deletes many true-backed fragments and increases missed_true_rate, so it cannot be promoted or scaled.

Recommended next action:

- Selector: carry forward as a conservative trust router with mandatory local probe and leave-clade abstention. Do not present it as point-estimate performance prediction.
- Decoder: do not expand training. The next structural route, if any, must use a stronger true-retention constraint or interval-level objective that explicitly penalizes deleting true-backed fragments; otherwise record this branch as future work.

## Result: PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630

Date: 2026-06-30

Status: semantic success for selector MinHash router and interval-survival decoder screen; validator status `not_yet` because one guardrail failed. No SOTA claim.

Scope: `$pursue` continuation for active milestone `TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC`. Selector direction adds deterministic genome-wide bottom-k MinHash-equivalent k-mer distances because `mash`/`sourmash` binaries were unavailable. Decoder direction replaces the failed retention proxy with an interval-level true-retention / fragment-survival objective and segment-aware evidence-preservation decoder on GENERanno 4096.

Primary outputs:

- Selector report: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630/SELECTOR_MINHASH_ROUTER_REPORT.md`
- Selector status: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630/selector_minhash_status.json`
- Decoder report: `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/JOINT_STRUCTURED_DECODER_REPORT.md`
- Decoder metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/joint_structured_decoder_metrics.tsv`
- Decoder status: `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/joint_structured_decoder_status.json`
- Combined validator metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/pursue_combined_metrics.json`
- Code-review gate: `outputs/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/code_review_gate.json`

Semantic success:

- Selector script compiled and completed locally; status JSON reports `ok=true`, `deployable_features_only=true`, and target TE annotation features excluded.
- Decoder Slurm job `9861062` completed with state `COMPLETED`; `job_watch` wrote `outputs/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/STATUS=COMPLETED`.
- Decoder status JSON reports `ok=true`, seed `42`, device `cuda`, `freeze_backbone=false`, and parseable val/test rows for `ce_baseline`, `interval_survival_raw`, and `interval_survival_decoder`.
- No OOM, NaN, traceback, or missing-file failure was observed. Model-load warnings were expected for the local GENERanno token-classification wrapper.
- Claim eligibility: cannot claim SOTA; this is bounded publication-support screen only.

Key metrics:

- Selector selected router still passes only as conservative routing. In leave-species-out/in-panel mode, selected `baseline_plus_kmer` top-2 contains-best is `0.8636`, mean regret `0.0071`, p90 regret `0.0008`, local-probe recommended rate `1.0`, and confidently-wrong single-anchor rate `0.0`.
- Adding MinHash improves leave-clade calibration RMSE from `0.4164` to `0.3716` and leave-clade top-2 from `0.5909` to `0.8182`, but this remains below the top-2 deployment gate. Therefore leave-clade/new-clade mode remains explicit abstention plus local probe/new anchor.
- In leave-species-out mode, `baseline_plus_kmer_minhash` is worse than the prior router (`top2=0.7727`, mean regret `0.0469`), so MinHash is useful as a leave-clade risk feature, not as the in-panel selected policy.
- Decoder CE baseline test: segment-F1@IoU0.8 `0.3069`, boundary-F1@5bp `0.1414`, missed_true_rate `0.2623`.
- `interval_survival_decoder` test: segment-F1@IoU0.8 `0.3756`, boundary-F1@5bp `0.1805`, missed_true_rate `0.2910`; deltas vs CE are `+0.0687`, `+0.0391`, and `+0.0287`, so it passes the primary decoder screen thresholds.
- Guardrail failed: `deleted_true_backed_fraction=0.4592`, above the allowed `0.15`. It deleted `98` CE-baseline fragments, including `45` true-backed and `53` false fragments.
- `validate_goal.py` status is `not_yet`: all primary progress criteria pass, but the decoder true-backed deletion guardrail fails.

Interpretation:

- The selector remains usable only as a conservative top-2/local-probe trust router. MinHash-equivalent distance adds some leave-clade signal but does not create a claim-grade point-estimate formula or a confident single-anchor selector.
- The interval-survival objective is the first decoder iteration in this route that simultaneously improves strict segment-F1 and boundary-F1 while keeping missed_true_rate within the `+0.03` allowance.
- The decoder is still not solved: it removes too many true-backed fragments, so the apparent fragmentation reduction is not cleanly false-fragment-specific.
- This should be treated as a positive structured-objective signal with a retention guardrail failure, not as a deployable interval decoder.

Recommended next action:

- Selector: stop trying to present a point-estimate decay formula from this screen. Carry forward only the conservative router language: known/in-panel top-2 shortlist plus local chromosome probe; leave-clade/new clade abstain.
- Decoder: do not scale as-is. If one more bounded iteration is allowed, it must directly reduce true-backed fragment deletion, e.g. stronger interval survival calibration, proposal-level keep/drop labels, or explicit true-backed deletion penalty. Otherwise record this route as future work under the user’s stop rule.

## Result: PIPE-TEFM-PURSUE-RETCONSTR-20260630

Date: 2026-06-30

Status: semantic success but method failure. Final decoder-only bounded screen completed on a 24GB RTX 3090 after the initial 80GB-specific Slurm request was unavailable. No SOTA claim.

Scope: final allowed decoder iteration after tri-review/pivot for `PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630`. Selector was frozen and not rerun; decoder tested `retention_constrained_interval_loss` with a raw-evidence veto and internal hard gate `deleted_true_backed_fraction <= 0.15`.

Primary outputs:

- Decoder report: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/JOINT_STRUCTURED_DECODER_REPORT.md`
- Decoder metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/joint_structured_decoder_metrics.tsv`
- Decoder status: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/joint_structured_decoder_status.json`
- Combined validator metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/pursue_combined_metrics.json`
- Code-review gate: `outputs/PIPE-TEFM-PURSUE-RETCONSTR-20260630/code_review_gate.json`

Semantic success:

- Code compiled; `pre_submit_gate.py` passed after sbatch hash refresh.
- Initial sbatch submission requesting unavailable 80GB GRES failed before job creation; the script was revised to request one `nvidia_geforce_rtx_3090` and resubmitted.
- Slurm job `9862135` completed with state `COMPLETED`; `job_watch` wrote `outputs/PIPE-TEFM-PURSUE-RETCONSTR-20260630/STATUS=COMPLETED`.
- Status JSON reports `ok=true`, seed `42`, device `cuda`, `freeze_backbone=false`, and parseable val/test rows for CE baseline, `retention_constrained_raw`, and `retention_constrained_decoder`.
- No OOM, NaN, traceback, or missing-file failure was observed.

Key test metrics:

- CE baseline: segment-F1@IoU0.8 `0.3069`, boundary-F1@5bp `0.1414`, missed_true_rate `0.2623`.
- `retention_constrained_decoder`: segment-F1 `0.2534`, boundary-F1 `0.0856`, missed_true_rate `0.2541`, deleted_true_backed_fraction `0.2727`.
- Deltas vs CE: segment-F1 `-0.0535`, boundary-F1 `-0.0558`, missed_true_rate `-0.0082`.
- `retention_constrained_raw`: segment-F1 `0.1841`, boundary-F1 `0.0697`, missed_true_rate `0.1148`, deleted_true_backed_fraction `0.3182`.
- Internal promotion gate reports no gate-eligible variant. `validate_goal.py` status is `not_yet`: selector criteria pass, but decoder segment/boundary criteria fail and true-backed deletion guardrail remains above `0.15`.

Interpretation:

- The final true-retention constraint did reduce missed_true_rate and lowered true-backed deletion compared with the previous interval-survival decoder (`0.4592` to `0.2727`), but it sacrificed strict segment and boundary quality.
- This confirms the tradeoff: stronger retention can preserve true signal, but the current structured objective family cannot simultaneously improve interval completeness, boundary quality, and true-backed fragment selectivity.
- Per the pre-registered pivot rule, decoder optimization stops here and should be written as future work / limitation. Do not start another threshold/gap/post-hoc or survival-loss tweak cycle.

Recommended next action:

- Finalize selector as conservative router-only.
- Stop decoder direction for this milestone. Manuscript/support docs should state: trainable structured decoders showed signal but failed the full usability gate because interval gains and true-retention could not be achieved simultaneously in bounded screens.

## Result: PIPE-TEFM-CAP-POSTPROC-20260701

Date: 2026-07-01

Status: semantic success; diagnostic/comparator only. This run does not reopen `DEC-001` or `DEC-002` and is not a capability promotion.

Scope: bounded multi-threshold and length-adaptive postprocess sensitivity screen on the same small human/mouse GENERanno 4096 panel. Variants included raw thresholds `0.20-0.80`, gap/min-length heuristics, fixed HMM-style penalties, HMM plus high-confidence short-fragment rescue, and length-adaptive short-raw/long-HMM rules.

Primary outputs:

- Main report: `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/POSTPROCESS_THRESHOLD_REPORT.md`
- Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/postprocess_threshold_metrics.tsv`
- Length-bin diagnostics: `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/postprocess_true_length_bins.tsv`
- Strict headline tables: `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/postprocess_headline_iou80_boundary5.tsv`, `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/postprocess_strict_safe_iou80_boundary5.tsv`
- Review/council summary: `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/REVIEW_COUNCIL_SUMMARY.md`

Semantic success:

- Code compiled and passed the exp-scoped pre-submit gate.
- Slurm job `9880686` completed with state `COMPLETED` in `00:04:56` on an RTX 3090.
- Status JSON reports `ok=true`, seed `42`, and finite metric tables.

Key metrics:

- Human `raw_t0.50`: bp-F1 `0.8369`, segment-F1@IoU0.8 `0.1542`, boundary-F1@5bp `0.0763`, missed_true_rate `0.2869`, deleted_true_backed_fraction `0.0000`.
- Human best observed segment row `lenadaptive_raw0.80_hmm1_cut80`: segment-F1 `0.4354`, boundary-F1 `0.2086`, missed_true_rate `0.2992`, but deleted_true_backed_fraction `0.8583`; not acceptable.
- Human strict-guardrail-safe best row `raw_t0.20`: segment-F1 `0.2422`, boundary-F1 `0.1143`, missed_true_rate `0.2541`, deleted_true_backed_fraction `0.0000`, pred_true_backed_rate `0.6721`, overmerge_rate `0.0550`.
- Mouse `raw_t0.50`: bp-F1 `0.8232`, segment-F1 `0.1437`, boundary-F1 `0.0513`, missed_true_rate `0.1133`, deleted_true_backed_fraction `0.0000`.
- Mouse best observed segment row `gap25_min40_t0.60`: segment-F1 `0.5034`, boundary-F1 `0.1724`, missed_true_rate `0.1200`, but deleted_true_backed_fraction `0.4370`; not acceptable.
- Mouse strict-guardrail-safe best row `gap25_min40_t0.50`: segment-F1 `0.4589`, boundary-F1 `0.1575`, missed_true_rate `0.1133`, deleted_true_backed_fraction `0.1042`, pred_true_backed_rate `0.7606`, overmerge_rate `0.1127`.

Interpretation:

- The threshold was indeed part of the strict interval gap: lower raw thresholds improved human strict segment/boundary metrics without deleting CE true-backed fragments, and a simple mouse gap/min-length row was useful under guardrails.
- The best-looking HMM/length-adaptive rows are mostly not safe because they remove many true-backed raw fragments.
- Length-adaptive short-raw/long-HMM does not solve the problem in this screen; it can preserve short calls but leaves or worsens long-TE split/fragment counts.
- No universal postprocess recipe is promoted. The result is useful as a multi-threshold tradeoff figure and as evidence that interval fragmentation is not only a threshold-setting problem.
## Result: BENCH-5TOOL-SMOKE-20260811-R1

### Meta

- Date: 2026-08-11 CEST.
- Resource profile: smoke; claim-ineligible.
- Job: `11519312`, `COMPLETED`, exit `0:0`, elapsed `00:15:13`, 8 CPU, 64 GB requested, batch MaxRSS 1,686,288 KB, 0 GPU.
- Code-review gate: PASS_WITH_WARNINGS plus final fail-closed re-review PASS; machine gate `outputs/BENCH-5TOOL-SMOKE-20260811-R1/code_review_gate.json`.
- Evaluator contract: `docs/19_evaluator_contract.md`, `TEFM-BENCH-5TOOL-SMOKE-1.0.3`; zero-based half-open canonical schema.

### Dataset / contract

- Dataset: official tiny installation fixtures frozen by `input_manifest.json`; no fitted model and no biological benchmark claim.
- Split: not applicable. Leakage audit is `PASS_NOT_APPLICABLE`; no output was used for selection or calibration.
- Denominator: RepeatModeler2+RepeatMasker, EDTA, Earl Grey, HiTE and conditional TEtrimmer; MCHelper was not inserted.

### Paths

- Config: `configs/BENCH-5TOOL-SMOKE-20260811-R1.yaml` (`beaa8a48...`).
- Runner: `scripts/experiments/BENCH-5TOOL-SMOKE-20260811-R1/run_smoke.py` (`cd96f4b9...`).
- Sbatch: `sbatch/BENCH-5TOOL-SMOKE-20260811-R1.sbatch` (`10937ff0...`).
- Metrics: `outputs/BENCH-5TOOL-SMOKE-20260811-R1/metrics.json` (`49839624...`).
- Semantic validation / accounting: `outputs/BENCH-5TOOL-SMOKE-20260811-R1/{semantic_validation,slurm_accounting}.json`.

### Semantic success

- PASS: metrics exist, parse as JSON, all numeric values are finite, five required cells have terminal typed states, and `invalid_cells=0`.
- Adapter synthetic fixtures PASS; coordinate convention is zero-based half-open.
- Output manifest check PASS for all 764 recorded entries; no OOM/NaN/Inf was detected.
- Loss and checkpoint checks are not applicable to an external-workflow identity smoke.
- `primary_metric=0.0` is a valid discrete negative outcome (`engineering_pass_cells / 5`), not a collapsed learned metric.
- Cohort-scoped `validate_goal.py` returned `status=progress`, `run_ok=true`, `semantic_ok=true`; its generic tuning advisory is not applicable to a discrete identity matrix and does not authorize substitution or scaling.

### Metrics

| Metric | Value | Interpretation |
|---|---:|---|
| engineering pass fraction | 0.0 | 0/5 workflows completed every identity/database/min-input/adapter gate |
| engineering pass cells | 0 | valid negative |
| foundational typed blocks | 4 | RM2+RM, Earl Grey, HiTE, TEtrimmer |
| version mismatches | 1 | EDTA payload cannot prove patch version 2.3.0 |
| invalid cells | 0 | matrix result is semantically valid |
| matrix cells | 5 | denominator complete |

### Cell interpretation

- RepeatModeler2+RepeatMasker: exact payloads start, but Dfam 4.0/FamDB is not configured/promoted; RepeatMasker minimum launch fails closed.
- EDTA: exact SIF launches and adapter parses an emitted GFF, but the payload reports only `v2.3`, not target `2.3.0`, and the tiny run terminates at the TIR stage; verdict `VERSION_MISMATCH`.
- Earl Grey: exact 7.3.0 identity/help works, but frozen Dfam 4.0 partitions are not configured; no canonical interval output.
- HiTE: exact 3.3.3 source/digest is known, but no locally accepted exact SIF exists; legacy unpinned 3.0 is rejected.
- TEtrimmer: exact 1.7.4 source overlay launches over the 1.7.2 dependency host and the minimum command exits zero, but no interval output is produced and the dependency/Pfam closure remains incomplete.

### Gates and decision

- Primary engineering gate: FAIL (0/5 fully usable).
- Semantic-success gate: PASS (complete fail-closed matrix).
- SOTA/claim gate: not applicable and forbidden for smoke.
- Recommended action: treat this as a valid negative denominator audit. Resolve the frozen database/runtime blockers before any biological five-workflow benchmark; do not substitute versions after viewing results.
- Tri-review / pivot: pending cohort-level closeout after F/S/G/E asset gates are collected.

---
## Result: FRAG-PARENT-LATTICE-SCREEN-20260811-R1

- Profile: asset-gate smoke for a requested screen; claim-ineligible.
- Allocation: short `srun` Job `11519717`, `COMPLETED 0:0`, 1 CPU/1 GB, 0 GPU, 1 second; no scientific screen job was submitted.
- Primary metric: `asset_gate_pass=0.0`; status `FOUNDATIONAL_TYPED_BLOCK`; semantic success true because the frozen A0/A4/A5/A6 blocked state was reproduced without evidence drift.
- Data/truth: synthetic T0 and golden evaluator are usable only for mechanism semantics. Real-T0 is absent; FlyBase/Rice are T1 positive-only and not bound into a same-input registry.
- Blockers: H0 directory pin absent; no Real-T0 or approved tiered biological input registry; CENTER70/MERGE_STRICT/MERGE_LOOSE/unique accepted postprocessor not frozen.
- Decision: no lattice implementation or biological evaluation was run. Reopen only after the three asset groups are closed; preserve immutable leaves and do not revive DEC-001/002 cousins.
- Evidence: `outputs/FRAG-PARENT-LATTICE-SCREEN-20260811-R1/{metrics,verifier_report}.json`; `docs/experiments/FRAG-PARENT-LATTICE-SCREEN-20260811-R1.md`.

---

## Result: SF-HIER-OPENSET-SCREEN-20260811-R1

- Profile: asset-gate smoke for a requested screen; claim-ineligible.
- Allocation: short `srun` Job `11519729`, `COMPLETED 0:0`, shared S/E audit, 1 CPU/1 GB, 0 GPU, 2 seconds; no scientific screen job was submitted.
- Primary metric: `asset_gate_pass=0.0`; status `FOUNDATIONAL_TYPED_BLOCK`; semantic success true and evidence identities match.
- Blockers: canonical snapshot authorizes only S0 input review; production ontology target/crosswalk is not frozen; family/homology-component and clade keys are absent; production homology pin is absent; historical direct head is not exactly rejoined to canonical loci.
- Leakage/calibration verdict: no model, split, or calibration was executed. A family/homology-blocked zero-overlap audit and validation-only calibration contract are prerequisites.
- Decision: do not implement/run hierarchical open-set comparison on the historical chromosome split.
- Evidence: `outputs/SF-HIER-OPENSET-SCREEN-20260811-R1/{metrics,asset_gate_report}.json`; `docs/experiments/SF-HIER-OPENSET-SCREEN-20260811-R1.md`.

---

## Result: DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1

- Profile: asset-gate smoke for a requested screen; claim-ineligible.
- Allocation: short `srun` Job `11519717`, `COMPLETED 0:0`, shared F/G audit, 1 CPU/1 GB, 0 GPU, 1 second; no scientific screen job was submitted.
- Primary metric: `asset_gate_pass=0.0`; status `FOUNDATIONAL_TYPED_BLOCK`; semantic success true and evidence identities match.
- Blocker: all five anchors (`animal`, `cross`, `human_h0`, `insect`, `plant`) are `PROV_RUN_RECORD_MISSING`; next stage is unauthorized.
- Decision: no Mash/panel/cube/checkpoint evaluation/FATS/PAS fitting was run. Reopen only after exact training genomes, code, config and evaluator run records are reconstructed for every anchor.
- Evidence: `outputs/DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1/{metrics,verifier_report}.json`; `docs/experiments/DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1.md`.

---

## Result: EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1

- Profile: asset-gate smoke for a requested screen; claim-ineligible.
- Allocation: short `srun` Job `11519729`, `COMPLETED 0:0`, shared S/E audit, 1 CPU/1 GB, 0 GPU, 2 seconds; no scientific screen job was submitted.
- Primary metric: `asset_gate_pass=0.0`; status `FOUNDATIONAL_TYPED_BLOCK`; semantic success true and evidence identities match.
- Blockers: 2,200 Dfam fragments lack exact family/copy/component/accession bindings; genomic rows lack assembly/family/copy/component bindings; exact backend and pretrained/untrained weights are incomplete.
- Decision: no embedding, projection, clustering or representation comparison was run. Reopen only after one sealed split and all bindings/weights/backend identities are frozen.
- Evidence: `outputs/EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1/{metrics,asset_gate_report}.json`; `docs/experiments/EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1.md`.

---

## Result: FRAG-EVIDENCE-REGISTRY-20260811-R2

- Date: 2026-08-11 CEST.
- Profile: bounded CPU asset-audit smoke; claim-ineligible; no model inference or scientific screen.
- Allocation history: Job `11521393` failed before payload after 1 second because `set -u` exposed an unset `MKL_INTERFACE_LAYER` during Conda activation. The reviewed environment-only repair activated `benchmark_core` before enabling nounset. Retry Job `11521479` completed `0:0` in 14 seconds on `private-teodoro-gpu`, using 1 CPU, 4 GB requested memory and 0 GPU.
- Formal status: `FOUNDATIONAL_TYPED_BLOCK`; `semantic_success=true`; `scientific_screen_executed=false`.

### Semantic-success validation

- `metrics.json` exists, parses, and all numeric values are finite.
- Six of six registered integrity checks passed: H0 directory pin, truth registry, comparator semantics/probes, environment, command/input identity, and result construction.
- The formal output manifest verifies all 13 runtime artifacts; no NaN/Inf, traceback, OOM or killed-process signature was found.
- Loss, checkpoint and learned-metric degeneracy checks are not applicable to this deterministic asset audit. `integrity_check_count_passed=6` is a discrete completeness count, not a biological performance value.
- Route-local `validate_goal.py` returned `status=progress`, `run_ok=true`, `semantic_ok=true`. Its generic tuning/scaling text is inapplicable to an asset count and does not authorize method tuning, scientific execution or claim promotion.

### Result and interpretation

| Metric | Value | Interpretation |
|---|---:|---|
| integrity checks passed | 6/6 | formal registry audit is reproducible |
| H0 directory pin pass | 1 | frozen directory identity closed |
| truth registry pass | 1 | synthetic T0 and positive-only T1 boundaries are explicit |
| same-input comparator gate pass | 1 | historical comparator semantics and 8/8 probes closed |
| accepted postprocessor count | 0 | no current production postprocessor is frozen |
| scientific lattice implementation count | 0 | MERGE comparators are not a lattice |
| scientific executions | 0 | no biological screen was attempted |

- HMM2 remains a historical fixed comparator, not an accepted method. MERGE_STRICT/LOOSE remain comparator projections and cannot satisfy DEC-001/002 re-entry.
- T1 evidence remains positive-only: unlabeled sequence is not negative, so whole-genome, bp and segment precision/F1 remain prohibited.
- Remaining typed blockers are `ACCEPTED_POSTPROCESSOR_UNFROZEN` and `SCIENTIFIC_LATTICE_UNIMPLEMENTED`; a future T1 screen also requires same-input H0 probability tracks with hashes.
- Decision: F registry closure is complete as an asset milestone, but the scientific F route is still blocked. Await B/S0 collection, cohort tri-review and pivot; do not scale or tune.
- Evidence: `outputs/FRAG-EVIDENCE-REGISTRY-20260811-R2/`; `docs/experiments/FRAG-EVIDENCE-REGISTRY-20260811-R2.md`; Slurm jobs `11521393`, `11521479`.

---

## Result: BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2

- Date: 2026-08-11 CEST.
- Profile: bounded CPU engineering/runtime smoke; claim-ineligible; no biological benchmark.
- Jobs: preparation `11522328`/`11522329`/`11522330`; main `11522405`; 0 GPU throughout. Pfam preparation was deliberately not submitted.
- Application collector status: `COMPLETED`; independent audited status: `FAILED_RUN`; audited `semantic_success=false`; `terminal_cell_count=5` only means five result records exist.

### Semantic-success validation

- Original `metrics.json` and `semantic_validation.json` parse and agree structurally, but their semantic classification is rejected: four executed runtime/integration failures were labeled foundational rather than invalid.
- `artifact_manifest.json` covers 778 files; independent re-hash verified 778/778.
- Original counts are `ENGINEERING_PASS=0`, `FOUNDATIONAL_TYPED_BLOCK=5`, `INVALID_RUN=0`; independent audited counts are `ENGINEERING_PASS=0`, `FOUNDATIONAL_TYPED_BLOCK=1`, `INVALID_RUN=4`. Therefore this is a failed run with intact artifacts, not a valid-negative matrix.
- Slurm accounting service was unavailable at archival time; no scheduler elapsed or job MaxRSS is invented. Per-command time files remain authoritative for child commands; maximum observed child RSS is 768112 KB.

### Cell result

| Workflow | Identity | Minimum/adapter | Terminal interpretation |
|---|---|---|---|
| RepeatModeler2 2.0.9 + RepeatMasker 4.2.4 | RM2/FamDB exact; RM probe used unsupported `-version` | discovery, masking and 43-row adapter pass | `INVALID_RUN`: harness identity probe defect |
| Earl Grey 7.3.0 | exact help and direct Dfam 4.0 query pass | `-r 9606` cannot discover FamDB internally | `INVALID_RUN`: database integration failure |
| HiTE 3.3.3 | exact digest/manifest, runtime probe fails | clean shell has no `python`; no GFF | `INVALID_RUN`: launcher/PATH failure |
| EDTA 2.3.0 | exact tag/commit/tree and official `v2.3` help pass | TIR-Learner `KeyError: 0`; no final GFF | `INVALID_RUN`: dependency/runtime failure |
| TEtrimmer 1.7.4 | exact source tar, no runtime substitution | immutable Pfam release/index absent | foundational asset block |

### Decision boundary

- No workflow performance conclusion, ranking, tuning or claim is allowed.
- Validator verdict is `failed_run`; do not rerun immediately. Repair the collector/classifier and runtime integrations, then require fresh code review. A fully immutable official Pfam release remains a separate prerequisite for TEtrimmer.
- Evidence: `outputs/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/`; `docs/experiments/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2.md`; Job `11522405`.

---

## Result: SF-DIRECT-BASELINE-SCREEN-20260811-R2 CPU DATA

- Date: 2026-08-11 CEST.
- Profile: CPU-only data materialization and leakage gate preceding the S0 direct-superfamily screen; claim-ineligible.
- Job: `11522718`, `private-teodoro-gpu`, 16 CPU/96 GiB/12h limit, 0 GPU.
- Formal status: `DATA_FAILED`; `semantic_success=false`; `scientific_screen_executed=0`; `hierarchical_stage_authorized=false`.

### Semantic-success validation

- The independently reviewed package and machine code-review gate passed; submission preflight and `sbatch --test-only` also passed.
- The CPU synthetic/schema suite ran first. During real data build, Python `csv.DictReader` raised `_csv.Error: field larger than field limit (131072)` while reading the frozen source chunk manifest.
- Failure occurred before Dfam family materialization, split construction, leakage verification, model training or inference. There are no direct-superfamily scientific metrics to interpret.
- Atomic failure handling produced `STATUS=DATA_FAILED`, finite non-result `metrics.json`, `TERMINAL_STATE.json`, `failure.json` and a valid canonical failure manifest.
- Route-local `validate_goal.py` returned `failed_run` from `DATA_FAILED` before evaluating any goal metric.

### Decision boundary

- No GPU S0, S1 hierarchical/open-set work, metric comparison or claim is authorized.
- Required repair is narrow but code-bearing: set and validate an explicit bounded CSV field-size limit and add a large-field regression fixture. It must pass fresh independent code review before a CPU DATA retry.
- Evidence: `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/`; `logs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/data_11522718.err`; `docs/experiments/SF-DIRECT-BASELINE-SCREEN-20260811-R2.md`.

### Repair-only retry: Job 11523252

- The independently reviewed bounded CSV repair passed 15/15 tests and the real pinned manifest probe (495 rows, 17 columns, maximum field 1,203,362 characters). Job `11523252` then ran for about 21 minutes on 16 CPU/96 GiB/0 GPU and passed the original parser failure.
- Formal terminal state is `DATA_TYPED_BLOCK`, `semantic_success=false`, `scientific_screen_executed=0`; the canonical output manifest verifies, no DATA PASS pointer exists, and Slurm accounting remained unavailable after the job left `squeue`.
- The deeper blocker is `DFAM_FAMILY_IDENTITY_UNRESOLVED`: canonical RepeatMasker annotations contain names that cannot be mapped one-to-one to a Dfam 3.9 accession/consensus under the preregistered homology-component contract, including generic/ambiguous names and custom `DR...` families.
- No dataset partition, leakage audit, training, inference, loss, checkpoint or scientific metric was produced. The validator therefore returns `failed_run`; tuning, GPU S0 and S1 remain forbidden.
- This is not evidence that direct superfamily annotation is poor. It is evidence that the current all-record Dfam-accession identity layer is incomplete for the frozen annotation source. The next decision must preserve all P-state records and prevent homology leakage; silently dropping unresolved families or falling back to random/chromosome split is prohibited.
- Evidence: `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/attempts/data-slurm-11523252.tmp/{typed_block,failure}.json`; `logs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/data_11523252.{out,err}`; `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/{STATUS,metrics,TERMINAL_STATE,validate_goal,output_manifest.sha256}`.

---
## Result: SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1

Date: 2026-08-11 CEST

Status: `FAILED_RUN` / `AUDIT_FAILED`; no provenance result.

- Job `11523938` ran the independently reviewed, CPU-only canonical identity audit for about 2 minutes 7 seconds with 4 CPU, 32 GiB limit and 0 GPU.
- Pre-submit, 14/14 allocation-side contract tests and the bounded label-coverage safeguards passed. The audit then failed during the first real FamDB exact-name sweep.
- Root cause: the implementation called each partition leaf's `get_family_by_name()` directly and assumed every Dfam 3.9 partition contained `Lookup/ByName`. Partition `dfam39_full.3.h5` legitimately lacks that group; `famdb_classes.py` raised `KeyError: object 'ByName' doesn't exist`. The official top-level `FamDB.get_family_by_name()` wrapper tolerates such partition-local absence while continuing the search.
- Canonical failure artifacts and `output_manifest.sha256` verify. `STATUS=AUDIT_FAILED`, `semantic_success=false`, `valid_negative=false`; deterministic `validate_goal.py` returned `failed_run` rc3.
- No identifier table, provenance coverage, split, clustering, training, GPU inference or scientific S0 result was produced. The earlier identity/comparability question remains unanswered.
- Slurm accounting was unavailable because `slurmdbd` refused the connection; local timestamps and logs establish the bounded runtime, but MaxRSS/ExitCode remain accounting-unknown.

Decision boundary: stop and notify. Do not retry by broadly swallowing FamDB exceptions. Any repair must explicitly distinguish a structurally absent `Lookup/ByName` index (valid partition skip) from corrupt/unreadable objects, add a real partition-layout regression probe, receive fresh independent review, and then pass the result-chain pivot before another CPU audit. GPU S0 and S1 remain forbidden.

---
## Result: BENCH-RM-HITE-VALIDITY-20260811-R1

Date: 2026-08-11 CEST

Status: overall `FAILED_RUN`; one valid engineering pass and one timed-out invalid cell.

- Job `11523819` ran one independently reviewed offline CPU validity smoke with 4 CPU, 48 GiB limit, 1h walltime and 0 GPU. Local runtime was about 18m32s; Slurm accounting was unavailable because `slurmdbd` refused the connection.
- `repeatmodeler2_repeatmasker=ENGINEERING_PASS`: exact RepeatModeler `2.0.9`, RepeatMasker `4.2.4` and Dfam `4.0` identities all came from exit-zero runtime evidence; both minimum runs exited zero; the explicit RepeatMasker `.out` adapter produced 43 canonical rows. This closes the old RM identity-harness false negative for bounded runtime validity, not biological accuracy.
- `hite=INVALID_RUN`: exact anchored help banner proved HiTE `3.3.3`; direct argv launched the official demo with `--annotate 1`. The 600-second minimum-input budget expired at step 3.3 after completed coarse mapping and TIR work; exit `124`, no final `HiTE.gff`, adapter failed as expected. This is a timeout/incomplete execution, not a version mismatch or tool-quality result.
- Aggregate metrics correctly report 1/2 engineering passes, invalid fraction `0.5`, `semantic_success=false`, `repair_goal_success=false`, `STATUS=FAILED`; `validate_goal.py` returned `failed_run` rc3.
- The artifact manifest contains 334 files / 340,979,896 bytes and independently rehashes with zero missing/mismatch. Peak observed live RSS was below 0.8 GiB; formal MaxRSS remains accounting-unknown.

Decision boundary: stop and notify. Do not rerun both cells automatically. Post-result tri-review must decide whether to reuse the immutable RM pass and run an isolated HiTE-only continuation with a longer but still bounded timeout, or rerun the paired contract. No Earl Grey/EDTA/TEtrimmer/Pfam, GPU, biological benchmark or claim is authorized.

---

## Result: SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1 repair-only retry

### Meta

- Date: 2026-08-11 CEST.
- Resource profile: claim-ineligible CPU asset audit; Job `11524255`, `private-teodoro-gpu`, 4 CPU/32 GiB/2h limit/0 GPU.
- Slurm result: `COMPLETED`, exit `0:0`, elapsed `00:18:32`; `scontrol` confirms no GRES. `sacct` remained unavailable because `slurmdbd` refused the connection.
- Code review: independent fresh PASS for the frozen 12-partition layout and absent-vs-corrupt semantics; machine gate hash-bound six reviewed files.
- Evaluator: `identity_provenance_audit.py` SHA-256 `fad6b175dedec985079436e70a4fd4b71c5e651c123e776542e0c28f796056f9`.

### Semantic success and integrity

- Audit terminal: `IDENTITY_PROVENANCE_TYPED_BLOCK`; `semantic_success=true`, `valid_negative=true`, `claim_eligible=false`.
- Canonical output manifest: 7/7 entries independently rehashed; payload manifest: 5/5 entries independently rehashed; all numeric metrics finite.
- Input conservation: 35,616,746 parsed annotation records; 24,566,629 P records plus 43,728 explicitly label-contract-excluded candidate records; conservation delta `0`, positive identifiers deleted `0`, prefix guesses `0`.
- No split, clustering, model training, inference or calibration occurred. Training-only loss/checkpoint checks are not applicable.

### Audit metrics

| Metric | Value | Gate | Result |
|---|---:|---:|---|
| unique provenance coverage | `0.9583766909` (`6447/6727`) | `1.0` | fail / typed block |
| missing identifier count | `279` | `0` | fail |
| ambiguous identifier count | `1` (`X13_LINE`, two exact candidates) | `0` | fail |
| required accession failures | `0` | `0` | pass |
| label-contract candidate coverage | `0.9982231871` | informational | explicit exclusion blocker |
| label-contract-excluded records / identifiers | `43,728 / 10` | `0` for automatic continuation | fail / human gate |
| duplicate-consensus groups | `0` | `0` | pass |
| label conflicts | `0` | `0` | pass |

The largest unresolved names are not rare noise: `L2a` (726,386 occurrences), `L2c` (650,730), `L2b` (534,347), `L1MB1` (466,086) and `L1M5` (311,054). The explicitly excluded table is dominated by SVA and L1-dependent retroposon identifiers and remains outside the provenance denominator under the currently frozen S0 labeler.

### Goal validation and interpretation

- Route-local `validate_goal.py` returns `failed_run` because the active S direct-superfamily goal requires `main4_conditional_macro_f1`, which this pre-model audit intentionally cannot produce. This is not a contradiction with audit-level semantic success: the audit ran correctly and established that the current exact-accession homology contract is insufficient.
- Exact identity is therefore not ready for leakage-safe S0 materialization. Silently dropping unresolved identifiers, guessing by prefix, treating unlabeled records as negatives, or proceeding to S1 would invalidate the research question.
- Recommended next action: 3-way tri-review, then one human-gated contract decision. No automatic third audit attempt, S0 DATA retry, GPU training or S1 is authorized.

### Paths

- Metrics/report: `outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/{metrics,report}.json`
- Identifier evidence: `outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/attempts/audit-slurm-11524255/{identifier_audit.tsv,label_contract_excluded.tsv,PAYLOAD_MANIFEST.json}`
- Logs: `outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/slurm_11524255.{out,err}`

---
## Result: BENCH-HITE-ISOLATED-20260811-R1

Date: 2026-08-12 CEST

### Execution and semantic validity

- Job `11524485` ran on `private-teodoro-gpu` with 4 CPU, 48 GiB, 0 GPU and a 1-hour limit; Slurm finished `COMPLETED 0:0` in `00:23:04`.
- Code review was independent `PASS` with 0 blockers. Allocation used the frozen HiTE 3.3.3 SIF, official demo fixture, direct argv, offline proxies and the exact 1800-second command timeout.
- `hite_help_identity`: rc0, no timeout, anchored official `HiTE, version 3.3.3` banner.
- `hite_min`: rc0, no timeout, 21m58.53s command wall time, peak RSS 2,111,456 KiB.
- Final `HiTE.gff`: 1,203,491 bytes and 14,318 physical lines. Canonical adapter output: 14,315 data rows, 1,618,618 bytes.
- Artifact manifest independently rehashed 12/12; canonical published payloads rehashed 5/5. The five payload staging paths are intentionally moved during atomic publication; all published canonical paths match their recorded hashes. Runtime environment staged/canonical copies match.
- Terminal: `COMPLETED`; `semantic_success=true`; `hite_engineering_pass=1`; no `STOP.json` or failure bundle.

### Reconciliation and claim boundary

- The parent Job `11523819` remains `FAILED` and immutable.
- Its RM2+RepeatMasker+Dfam4 cell is reused only after byte-level verification and remains `ENGINEERING_PASS_REUSED_BY_HASH`.
- The parent 600-second HiTE timeout is verified, while this isolated continuation supplies the successful HiTE cell. Therefore `two_cell_evidence_ready=true`.
- This is not a single successful denominator run: `single_successful_run=false`, `accuracy_claim=false`, `claim_eligible=false`.
- Route-level `validate_goal.py` against `GOAL_B_DENOMINATOR_R2` returns `failed_run` because the child deliberately does not expose five-cell `terminal_cell_count`. This stops further B compute for result review; it does not invalidate the isolated cell-level engineering pass.

### Evidence

- Canonical outputs: `outputs/BENCH-HITE-ISOLATED-20260811-R1/`.
- Cell result: `outputs/BENCH-HITE-ISOLATED-20260811-R1/attempts/attempt-11524485/cells/hite/result.json`.
- Final GFF/adapter: `outputs/BENCH-HITE-ISOLATED-20260811-R1/attempts/attempt-11524485/work/hite/{HiTE.gff,hite.canonical.tsv}`.
- Logs: `logs/BENCH-HITE-ISOLATED-20260811-R1_slurm_11524485.{out,err}`.

### Tri-review and pivot

- Three external CLI reviewers completed 3/3 quorum and unanimously accepted the isolated HiTE engineering pass and the parent-RM cross-run reconciliation.
- The result closes only 2/5 engineering cells. Parent aggregate remains `FAILED`; no five-cell metric, biological result or claim exists.
- All three flagged raw `further_retry_allowed=true` as inconsistent with the one-attempt human authorization. The raw artifact is preserved; the hash-bound post-run review sets operational retry permission to false.
- Pivot: `continue` by archiving component evidence, then stop at the human gate. No further B compute is authorized.

---
# Result: SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2

Date: 2026-08-12 CEST

Status: `FAILED_RUN_PRE_SCAN_SOURCE_IDENTITY_NAMESPACE_MISMATCH`; no identity-recovery result.

- Job `11526687` passed the machine code-review gate and Slurm routing, started on `gpu034`, then failed in 4 seconds before tests, H5 dataset enumeration, worker launch or checkpoint creation.
- The fail-closed source guard compared the login-node `st_dev=42` with compute-node `st_dev=65`. The symlink-target hash, inode, size, mtime and mode all matched the frozen asset. This is consistent with distinct mount namespaces exposing the same shared file under different device IDs; it is not evidence of content mutation.
- Canonical status is `FORMAL_FAILED_INTEGRITY`, semantic success is false, and the immutable state manifest verifies. The sbatch trap retained a generic error in canonical metrics; `result_semantic_audit.json` preserves the traceback-backed field-level diagnosis.
- Slurm `scontrol` reports `FAILED`, `ExitCode=1:0`, elapsed 4 s, 4 CPU/48 GiB/0 GPU. `sacct` remained unavailable because `slurmdbd` refused the connection.
- `scripts/validate_goal.py` returned `failed_run` (rc3). The old ACTIVE_GOAL metric is not scientifically relevant here; only the stop signal is consumed.
- No automatic retry is allowed. Full catalog, homology split, GPU S0, S1 and claims remain forbidden pending tri-review and pivot.

Evidence: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2/{result_semantic_audit.json,validate_goal.json,preview/CURRENT_STATE.json}`; Job `11526687` logs under `preview/logs/`.

---
# Result: SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2 repair retry

Date: 2026-08-12 CEST

Status: `VALID_NEGATIVE_IDENTITY_RECOVERY_TYPED_BLOCK`; no model result and no downstream authorization.

- Final authorized Job `11526905` completed on `gpu034` with Slurm `COMPLETED`, `ExitCode=0:0`, elapsed `01:40:52`, 4 CPU/48 GiB/0 GPU. `sacct` was unavailable because `slurmdbd` refused the connection; `scontrol` independently verified the terminal resource state.
- All 35 atomic units completed with zero temp checkpoints. The exact denominator is closed: 321,856 Families datasets, 321,856 unique canonical paths, 321,856 unique HDF5 object addresses, 321,856 consensus attrs and 321,818 model attrs.
- The frozen target denominator is exactly 279 identifiers and 6,432,583 occurrences, with zero identifier/occurrence conservation delta. The exhaustive case-sensitive exact-name scan produced zero candidate rows: recovered=0, ambiguous=0, invalid metadata=0, missing=279.
- `X13_LINE` remains outside primary as one audit-only ambiguous identifier with 686 occurrences and two exact candidates with distinct provenance.
- Independent post-run audit rehashed the immutable current state, exact 64-file attempt payload and all 35 two-level checkpoint payloads; file-set/hash mismatch count is zero. Every checkpoint records stable source fields equal and the login/compute device change 42→65 as `audit_only`.
- Supported statement: Dfam 3.9 partition 3 contains no case-sensitive exact `name` match for the frozen 279 identifiers. Unsupported: that the biological families do not exist, that aliases/other official releases cannot resolve them, or that dropping 6.43 million occurrences is safe.
- `scripts/validate_goal.py` reports `failed_run` only because `ACTIVE_GOAL.json` is the older selector/decoder milestone and lacks this asset metric. The independently audited asset result remains semantic-successful and valid-negative; the validator output is consumed only as a mandatory stop signal.
- No further partition-3 retry is authorized. Full catalog, homology split, S0 DATA/GPU, S1 and claims remain false pending tri-review/pivot and an explicit identity-contract human gate.

Evidence: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2/{result_semantic_audit.json,validate_goal.json,preview/CURRENT_STATE.json}` and `preview/attempts/slurm-11526905/`; Job `11526905` logs under `preview/logs/`.

---
# Result: SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1

Date: 2026-08-12 CEST. Job `11527999` completed `0:0` in 14 seconds on `private-teodoro-gpu` with 1 CPU, 2 GiB and 0 GPU.

- Terminal result: `IDENTITY_SOURCE_TYPED_BLOCK`; `semantic_success=true`, `valid_negative=true`, `claim_eligible=false`.
- The frozen Dfam 3.9 curated EMBL source passed gzip/source/dialect/count/integrity checks. All 13 payload entries and the immutable state manifest independently re-hash with zero mismatch.
- Frozen denominator: 279 identifiers and 6,432,583 occurrences. Exact authoritative relations resolve 50 identifiers (1,710,715 occurrences), leave 2 ambiguous (`L1HS`, `L1PREC2`; 11,352 occurrences), and leave 227 missing (4,710,516 occurrences). Identifier and occurrence conservation deltas are zero.
- Direct RepeatMasker superfamily labels remain unchanged; label/species information did not participate in identity resolution. Ten U/ignore identifiers and `X13_LINE` audit-only handling remain unchanged.
- Decision boundary: curated EMBL is authoritative but insufficient. Full catalog, homology split, DATA, GPU S0 and S1 remain unauthorized.
- `validate_goal.py` returns `failed_run` only because the active selector/decoder goal cannot consume this asset metric; the stop signal is retained without reclassifying the valid-negative audit.

Evidence: `outputs/SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1/{result_semantic_audit.json,validate_goal.json,preview/CURRENT_STATE.json}` and `preview/attempts/slurm-11527999/`.
# Result: SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-AUDIT-20260812-R1

Date: 2026-08-12 CEST. Job `11528157` completed `0:0` in 3 minutes 13 seconds on `private-teodoro-gpu` with 1 CPU, 4 GiB and 0 GPU.

- Raw terminal was `ALLFAMILY_TARGET_CROSSWALK_TYPED_BLOCK`, but post-result tri-review reclassifies the scientific result as `FAILED_RUN_GRAMMAR_COMPARABILITY`: source/record execution succeeded, while exhaustive raw-alias semantics did not.
- The formal allocation re-hashed the 2,677,249,806-byte source (SHA-256 `5497d435...`, official MD5 `eafeb77c...`) and consumed the gzip stream to EOF/CRC.
- The target-only stream scanned 4,121,397 sequence records: 26,279 curated DF and 4,095,118 raw DR. DF produced exactly the same 57 candidate rows as Job `11527999`; reconciliation passed.
- The runner observed zero raw-DR candidate rows, but its PI parser did not split official semicolon lists and its DR parser did not accept semicolon-terminated primary identifiers. Therefore “zero exhaustive raw support” is unknown pending one reviewed grammar-repair audit. The curated 50 unique / 2 ambiguous / 227 missing result remains independently valid.
- All 13 payload members and immutable state hashes pass; the 14th payload file is the self-excluded manifest. No full catalog was materialized.
- Conclusion: homology, DATA, GPU S0 and S1 remain unauthorized. One same-source CPU grammar-repair audit is permitted after fresh review; no heuristic or copy-derived fallback is permitted.
- `validate_goal.py=failed_run` is retained only because the active selector/decoder goal cannot consume this asset metric.

Evidence: `outputs/SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-AUDIT-20260812-R1/{result_semantic_audit.json,validate_goal.json,preview/CURRENT_STATE.json}` and `preview/attempts/slurm-11528157/`.

## Grammar-repair result — Job 11528267

The one authorized repair completed `0:0` in 3 minutes 13 seconds with the same 1 CPU/4 GiB/0 GPU envelope. Official grammar telemetry closes the previous caveat: raw DR contains 2,795 `NM` lines and zero `PI`, `SN` or database-reference lines; all raw target-hit counts are zero. Curated DF contains 3,570 period-terminated database references with 56 target hits plus one NM hit, exactly reproducing the 57 curated candidates. The repaired result is a final semantic-successful valid-negative: 50 unique, 2 ambiguous and 227 missing; no downstream authorization and no further same-source repair.

# Result: SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1

Date: 2026-08-12 CEST. Job `11528744` failed `2:0` after 2 seconds on `private-teodoro-gpu`; requested and allocated resources were exactly 1 CPU, 4 GiB, 20 minutes and 0 GPU.

- Profile: CPU-only roundtrip smoke; claim-ineligible. Independent pre-submit review was `PASS_WITH_WARNINGS`, and the allocation passed the machine code-review gate plus 33/33 synthetic tests.
- Semantic success: **fail**. No metrics or primary scientific value exist; `validate_goal.py` deterministically returns `failed_run`.
- Failure location: `validate_formal_resources()` rejected `SLURM_TIMELIMIT` before any FamDB family record was read and before either RepeatMasker arm was started. Slurm's authoritative `scontrol` record nevertheless shows `TimeLimit=00:20:00`, exact reviewed command, partition, CPU and memory.
- Integrity: the formal owner was released; canonical `preview/CURRENT` stayed on `IMPLEMENTED_NOT_RUN`; the failure is attempt-local. No PASS/valid-negative terminal, accession-retention result, geometry comparison or downstream authorization was produced.
- Root cause: an execution-environment contract bug, not a biological or tool result. The code assumed a textual environment variable representation that Baobab did not provide in the expected forms.
- Next action: stop and perform one repair-only validity iteration. Bind resources through strict allocation-side `scontrol` parsing and exact `SubmitLine`/command checks, cover missing/anomalous/override cases and pre-pointer revalidation, then obtain a fresh independent code-review gate before any retry.

Evidence: `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/{result_semantic_audit.json,metrics.audited.json,validate_goal.json,AUDITED_MANIFEST.sha256}` and `preview/logs/slurm-11528744.{out,err}`.

## Result: SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1 — repair retry Job 11528885

Date: 2026-08-12 CEST. Job `11528885` failed `2:0` after 10 seconds on `private-teodoro-gpu`; requested and allocated resources were exactly 1 CPU, 4 GiB, 20 minutes and 0 GPU.

- Profile: CPU-only roundtrip smoke; claim-ineligible. Fresh independent review was `PASS_WITH_WARNINGS`; the allocation passed the machine gate, 37/37 synthetic tests and strict `scontrol` authority reconciliation.
- Semantic success: **fail**. The audited primary metric is null; `validate_goal.py` returns `failed_run`. Loss/checkpoint/seed checks are not applicable because this is a CPU engineering preflight and no model or RepeatMasker comparison ran.
- Failure location: while constructing the pinned official FamDB object, the implementation accessed `FamDBLeaf.added`, which is absent in the installed API. The runner raised `AttributeError` before either RepeatMasker arm started.
- Integrity: `preview/CURRENT` points to immutable `PREFLIGHT_FAILED`; its exact payload manifest verifies. The stderr/stdout, attempt failure, canonical state and post-run semantic audit are closed by `AUDITED_MANIFEST_11528885.sha256`.
- Interpretation: this is an implementation/API-compatibility failure, not evidence for or against accession-preserving annotation, direct-superfamily accuracy, or the six-record roundtrip hypothesis. It is not a valid negative.
- Stop rule: this job consumed the only repair retry authorized after Job `11528744`. No third automatic retry, representative-window gate, full DATA, homology split, GPU S0 or S1 is authorized.
- Recommended next action: `$tri-review` then `$pivot`; reviewers must decide whether to stop this export route or replace the FamDB aggregation component under a new, separately reviewed contract.

Evidence: `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/{result_semantic_audit.11528885.json,metrics.audited.11528885.json,validate_goal.11528885.json,AUDITED_MANIFEST_11528885.sha256}` and `preview/logs/slurm-11528885.{out,err}`.

## Result: FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1 — Job 11529694

Date: 2026-08-12 CEST. Job `11529694` failed `1:0` at 0 seconds on `private-teodoro-gpu`; allocation was exactly 8 CPU, 32 GiB, 2 hours and 0 GPU.

- Profile: Rice T1 curated-positive CPU information-sufficiency audit; claim-ineligible.
- Semantic success: **fail**. Primary metric is null and `validate_goal.py` returns `failed_run`.
- Failure location: allocation-side `runtime_hashes.py` compared the frozen runtime list with `code_review_gate.reviewed_files` and rejected `scripts/pre_submit_gate.py` as absent. The login-side machine gate itself passed, but its reviewed-file closure was incomplete.
- Execution boundary: no allocation-side contract tests, environment snapshot, scheduler snapshot, Rice assembly/truth/library read, sequence mapping, collinearity partition or evaluator execution occurred. The scientific hypothesis remains unknown; this is not a valid negative.
- Integrity: wrapper failure evidence and the temporary preflight traceback are hash-closed in `AUDITED_MANIFEST_11529694.sha256`; preview status remained `IMPLEMENTED_NOT_RUN`.
- Interpretation: fail-closed behavior worked, but the independent review/gate installation missed a shared runtime dependency explicitly required by config. No whole-genome metric, F promotion or downstream authorization exists.
- Recommended next action: `$tri-review` then `$pivot`; any repair must receive a fresh delta review covering the shared pre-submit gate and a new one-shot authorization.

Evidence: `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/{result_semantic_audit.11529694.json,metrics.audited.11529694.json,validate_goal.11529694.json,AUDITED_MANIFEST_11529694.sha256}`.

## Result: FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1 — final retry Job 11531090

Date: 2026-08-12 CEST. Job `11531090` completed `0:0` in 25 seconds on `private-teodoro-gpu` with the exact reviewed envelope of 8 CPU, 32 GiB, 2 hours and 0 GPU.

### Semantic validity and data boundary

- Terminal: `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`; route-local `semantic_success=true`, `scientific_screen_executed=true`, `claim_eligible=false`, `whole_genome_metrics_authorized=false`.
- The audit used only Rice T1 curated-positive multirow groups: 756 truth groups, 2,450 immutable leaves and 304 topology-evaluable groups. Unlabelled genome sequence was never treated as negative. All leaves were retained exactly once (`leaf_retention=1.0`).
- Allocation-side reviewed-runtime closure, 17/17 contract tests, input hashes, exact command manifests, scheduler/environment snapshots and all 17 payload files pass independent hash verification. Stdout and stderr are empty.

### Registered metrics

- Consensus-collinearity mapped only `0.555102` of leaves, below the frozen `0.60` information gate.
- Candidate exact-group recovery was `0.138889`, complete-group recovery `0.142857`, pairwise same-parent harmonic `0.308188`, topology preservation `0.105263`, and boundary-within-5/10/25/50 bp was `0.186508/0.189153/0.195767/0.227513`.
- Candidate cross-RepeatMasker-ID false-fusion proxy was `0.075862`, above the `0.05` safety limit; corresponding purity/false-fusion safety was `0.924138`.
- The evidence is not random: the frozen shuffle null reached only `0.001323` exact recovery and `0.000540` pairwise harmonic, with false fusion `0.988095`.
- It is nevertheless substantially worse than the positive-only comparators. GAP100 reached exact recovery `0.371693`, pairwise harmonic `0.669109`, topology `0.473684`, and all boundary curves `0.376984`; GAP20 reached exact recovery `0.202381`, harmonic `0.516570`, and false fusion `0.051622`.
- In 1,000 chromosome-block bootstrap replicates using pooled sufficient statistics and per-replicate comparator reselection, candidate-minus-comparator means were `-0.232150` for exact recovery (95% interval `[-0.280093,-0.173410]`), `-0.359041` for pairwise harmonic (`[-0.448915,-0.273644]`), and `-0.371362` for topology (`[-0.452308,-0.274306]`).

### Interpretation and stop rule

- Consensus-coordinate evidence carries measurable biological signal relative to the shuffle null, but it is not information-sufficient for the registered preservation-constrained parent join. Only leaf retention, shuffle separation and topology evaluability passed; every promotion/comparator/safety gate failed.
- This is a valid negative for this frozen Rice T1 mechanism, not a whole-genome accuracy result and not evidence that all global biological models are impossible. It does not authorize FlyBase, H0, GPU, scale, threshold tuning, or any DEC-001/002 cousin.
- `scripts/validate_goal.py` returns `failed_run` because the active machine goal still requires historical selector/decoder keys such as `selector_top2_contains_best`. That schema incompatibility is an automation hard stop; it does not overwrite the independently audited route-local valid-negative classification.
- Post-result chain: `2/3 DEGRADED_REVIEW`; Claude and Codex independently chose `abandon-route`, while Antigravity failed three bounded CLI retries. Pivot and DEC-004 close the standalone consensus-collinearity assembler; no further F compute is authorized.

Evidence: `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/{STATUS,CURRENT_STATE.json,metrics.json,result_semantic_audit.11531090.json,validate_goal.11531090.json,AUDITED_MANIFEST_11531090.sha256}` and `attempts/slurm-11531090/`.

## Result: SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1 — Job 11533175

Date: 2026-08-12 CEST. Job `11533175` failed `2:0` after 17 seconds on `private-teodoro-gpu`; requested and allocated resources were exactly 1 CPU, 4 GiB, 10 minutes and 0 GPU.

- Profile: isolated FamDB leaf exact-access CPU probe; claim-ineligible. The fresh independent review was `PASS_WITH_WARNINGS`; the machine gate, exact scheduler reconciliation and 23/23 allocation-side tests passed.
- Semantic success: **fail**. No exact-access primary result was published; `validate_goal.py` returns `failed_run`. This is not a biological result or valid negative.
- Failure location: the single in-memory 6-accession × 12-leaf probe returned, but cleanup then called `FamDB.finalize()`. In read mode, the installed `FamDBLeaf` does not define the write-bookkeeping attribute `added`, so cleanup raised `AttributeError: 'FamDBLeaf' object has no attribute 'added'` before the 72 observations were frozen or published.
- Interpretation: the query outcome is **unknown**. It is invalid to infer either exact-access PASS or typed block from control flow, even though the error occurred after the probe function returned in memory.
- Integrity: the formal failure bundle, wrapper failure bundle, logs, machine gate, route-local semantic audit and old-goal validation are closed by `AUDITED_MANIFEST_11533175.sha256`; all entries independently verify.
- Stop rule: the one-shot authorization is consumed. No automatic retry, RepeatMasker, representative/full annotation, homology, DATA, GPU direct S0 or S1 is authorized. `$tri-review` and `$pivot` must decide whether a new separately reviewed close-only lifecycle repair is scientifically justified or whether this export route stops.
- Post-result chain: `2/3 DEGRADED_REVIEW`; Claude=`run-sanity-check-first`, Codex=`replace-component`, and both prescribe the same single final close-only lifecycle repair. Antigravity returned invalid unrelated output after three bounded retries. Pivot=`replace-component`; no old-code retry or downstream authorization.

Evidence: `outputs/SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1/{result_semantic_audit.11533175.json,validate_goal.11533175.json,AUDITED_MANIFEST_11533175.sha256,code_review_gate.json}` and `preview/logs/slurm-11533175.{out,err}`.

## Result: SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1 — Job 11534847

Date: 2026-08-12 CEST. Job `11534847` completed `0:0` in 25 seconds on `private-teodoro-gpu`; requested and allocated resources were exactly 1 CPU, 4 GiB, 10 minutes and 0 GPU. Peak RSS was `83,432 KiB`.

- Profile: final isolated FamDB read-lifecycle repair and exact-access component probe; claim-ineligible.
- Semantic result: `LEAF_CLOSE_ONLY_PASS`, `semantic_success=true`. Allocation-side 59/59 tests passed, and the frozen six accessions were each queried once against each of the 12 partitions: `72/72` calls, no fallback, no duplicate or missing query.
- Exact observations: `DF000000002.4/AluY`, `DF000000225.4/L1HS_3end`, `DF000000226.4/L1HS_5end`, `DF000000416.4/LTR16A1`, `DF000000859.4/MER53` resolved in partition 7; `DR002419729.2` resolved in partition 3 with empty canonical name and raw class `RC/Helitron`. All records matched the frozen accession/name/class/length/sequence-hash contract.
- Lifecycle result: the immutable observation bundle was published before cleanup; exactly 12 unique HDF5 handles were closed once each, all became invalid, and no cleanup error occurred. The read-mode write finalizer was not called.
- Integrity: scheduler/source/package/gate authority matched before and after execution. The terminal state contains the exact 11-file set and the observation bundle the exact 4-file set; both manifests independently rehash without mismatch. `AUDITED_MANIFEST_11534847.sha256` closes the terminal pointer, payload, observation bundle, audit, old-goal validation, gate and Slurm logs.
- Scope boundary: this is a component PASS only. It proves the installed Dfam 3.9 leaf API and close-only lifecycle for six frozen accessions; it does not authorize RepeatMasker, accession-preserving annotation, representative/full catalog, homology split, DATA construction, GPU direct S0, S1 or any scientific claim. Only a separately implemented and reviewed CPU leaf-adapter proposal becomes human-gate eligible.
- Goal validation: `scripts/validate_goal.py` returns `failed_run` because the active machine goal still requires historical selector/decoder metrics such as `selector_top2_contains_best`. This is a stale goal-schema automation stop and does not override the route-local audited component PASS.
- Binding next step: post-result `$tri-review` and `$pivot`; the one-shot gate is consumed and cannot authorize a repeat.

Evidence: `outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/{result_semantic_audit.11534847.json,validate_goal.11534847.json,AUDITED_MANIFEST_11534847.sha256,code_review_gate.json}`; terminal state `preview/states/slurm-11534847-leaf_close_only_pass-1786527568165971572/`; observation bundle `preview/attempt_observations/slurm-11534847/3dc3bdffd78a83c4a117f45b7e6221b086ea9ded03d9714441fb38e777709476/`.

## Result: SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1 — Job 11535362

Date: 2026-08-12 CEST. Job `11535362` completed `0:0` in 20 seconds on `private-teodoro-gpu`; allocation was exactly 1 CPU, 4 GiB, 10 minutes and 0 GPU, with peak RSS `81,388 KiB`.

- Profile: same-six-record leaf-adapter syntactic preflight; claim-ineligible.
- Terminal: `LEAF_ADAPTER_PREFLIGHT_PASS`, route-local `semantic_success=true`.
- Exact materialization: 6/6 records, 72 exact case-sensitive accession calls, no fallback. The canonical-name and accession.version FASTA views have identical ordered sequence/raw-class semantic hash `0b4b077b...a115`; their only designed difference is the identifier token.
- Header contract: five DF records use canonical names in control and versioned accessions in candidate; the empty-name DR record uses control `DR002419729#RC/Helitron` and candidate `DR002419729.2#RC/Helitron`. Each output row retains accession, versioned accession, raw class, partition, consensus length/hash and DF/DR namespace.
- Lifecycle/integrity: observations were frozen before cleanup; 12/12 unique HDF5 handles closed once. Terminal exact set 12/12 and observation exact set 5/5 independently rehash; source/scheduler/reviewed-package identities match before and after the probe. The audited manifest verifies all terminal, audit, gate and log anchors.
- Interpretation: this proves only a six-record syntactic leaf adapter. It is not RepeatMasker compatibility, annotation geometry, representative concordance, catalog coverage, homology-safe DATA or direct-superfamily model evidence.
- Authorization: a separately implemented/reviewed representative CPU proposal becomes human-gate eligible; RepeatMasker, annotation, representative/full catalog execution, homology, DATA, training, GPU direct S0, S1 and claim remain false pending tri-review/pivot.
- Goal validation: old `ACTIVE_GOAL` returns `failed_run` because `selector_top2_contains_best` is missing. This stale selector/decoder schema is an automation stop and does not overwrite the route-local syntactic component PASS.

Evidence: `outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/{result_semantic_audit.11535362.json,validate_goal.11535362.json,AUDITED_MANIFEST_11535362.sha256,code_review_gate.json}` and the terminal/observation bundles under `preview/`.
