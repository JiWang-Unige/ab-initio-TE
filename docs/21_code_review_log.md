# Code Review Log / 代码审前闸记录

> 由 `/code-review-gate` 维护。每次实现训练/评估/数据/配置/job 脚本后、提交真实训练前，必须记录一次审查。目标是把 label、metric、split、输出路径等会让结果作废的问题挡在运行前。

## Policy
- `full` / `scale` / claim-candidate 必须有 `PASS` 或 `PASS_WITH_WARNINGS`。
- `screen` 若改了共享训练/eval/data 代码，也必须有审查。
- `smoke` 可只做 host checklist，但若 smoke 之后直接提交 screen/full，仍需本 gate。
- `BLOCKED` 不得提交；用户强行豁免必须写 `WAIVED_BY_USER`。

## Review Entries

### Code Review Gate: PIPE-TEFM-EXTEND-20260620 2026-06-20
- Reviewer mode: separate Codex attempted, blocked by `bwrap: Creating new namespace failed: No space left on device`; host_self fallback review.
- Scope: GENERanno 4096 screen-only supplement pipeline for stricter family-level embeddings, base-pretrained SF5, animal-to-plant transfer, plant/cross-kingdom PU fine-tuning, PU fragmentation checks, stress anchor fine-tuning, and decay formula fitting.
- Verdict: PASS_WITH_WARNINGS

#### Closed blockers
- [x] `pu_token_task.py` initially saved a PU-specific `training_meta.json` that would not load through the existing segment evaluator; it now records `model_path`, `kind=auto_token`, and `token_label_mode=single_nt` so `bp_overlap_segment_eval.py` can load PU checkpoints.
- [x] `prepare_pu_windows.py` initially double-counted overlapping TE intervals in metadata, producing negative `unknown_bp`; unique positive bp counting is now used.
- [x] `embedding_strict.py` consensus-header regex now handles whitespace if a Dfam consensus FASTA is later provided.
- [x] sbatch array lengths were reconciled with generated TSV row counts: prep 9, train 8, eval 81, segment 6, embedding extract 5, embedding cluster 20.

#### Confirmed OK
- PU training data uses `1` for TE-positive bp and `-1` for U/unknown bp; no background windows are sampled in `prepare_pu_windows.py`.
- PU evaluation jobs use standard comparator-built 0/1 JSONL windows from `prepare_ucsc_windows.py`, so reported TE-F1 is still against the fixed strict-TE reference.
- Plant eval-only species are restricted to comparator-available `teosinte` and `soybean`; missing-comparator plants are not silently scored.
- Output paths are isolated under `software_outputs/tefm_extend/PIPE-TEFM-EXTEND-20260620`, `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620`, and `logs/tefm_extend/PIPE-TEFM-EXTEND-20260620`.
- Static validation passed: `python3 -m py_compile pipelines/PIPE-TEFM-EXTEND-20260620/*.py`, `bash -n sbatch/tefm_extend_*_20260620.sbatch`, and two-column TSV checks.
- PU data smoke on rice completed and produced positive `unknown_bp`.
- Machine gate written: `outputs/PIPE-TEFM-EXTEND-20260620/code_review_gate.json`.

#### Warnings
- Review independence is `host_self` because separate Codex could not create a sandbox namespace; this is acceptable only because the run is screen-only and non-claim.
- Dfam consensus source is not configured (`dfam_consensus_fasta: ""`), so consensus extraction will emit an explicit skipped metric unless a consensus FASTA path is added.
- PU loss is a bounded screen design (`u_penalty`, `tv_weight`), not a mature nnPU/theoretical PU implementation.
- Decay formula uses heuristic distance buckets and screen results; it can support mechanism discussion but not a claim-ready phylogenetic model.

### Code Review Gate: PIPE-TEFM-REPAIR-20260618 2026-06-18
- Reviewer mode: host-self pre-submit + read-only archive audit
- Scope: GENERanno 4096 repair/confirmation pipeline for surprising A2 mixed-animal and embedding results, plus segment threshold/postprocess and larger superfamily rerun.
- Verdict: PASS_WITH_WARNINGS

#### Confirmed OK
- New implementation is isolated under `pipelines/PIPE-TEFM-REPAIR-20260618`, `software_outputs/tefm_repair/PIPE-TEFM-REPAIR-20260618`, and `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618`.
- It reuses existing window builders, binary trainer/evaluator, overlap segment evaluator, superfamily trainer, and embedding extractor instead of modifying prior completed pipelines.
- `python3 -m py_compile` passed for all new Python files.
- `bash -n` passed for all new sbatch files.
- Generated command TSVs all have exactly two tab-separated columns.
- Training/superfamily jobs request `nvidia_a100_80gb_pcie`; GPU eval/embedding jobs exclude the known Blackwell node.
- Machine gate written: `outputs/PIPE-TEFM-REPAIR-20260618/code_review_gate.json`.

#### Warnings
- This is screen/repair evidence, not a SOTA claim.
- The `p5_archive_parity_4096` branch intentionally includes human and old training species to diagnose protocol parity; it must not be interpreted as no-human animal generalization.
- Current honeybee/beetle held-out metrics may be dominated by extremely sparse strict-TE positives and need label-coverage interpretation.
- Embedding diagnostics include supervised contrastive projection and linear probes, so they do not constitute purely unsupervised discovery evidence.

### Code Review Gate: PIPE-TEFM-SEG-SF-20260618 2026-06-18
- Reviewer mode: separate_codex council + host复审
- Scope: GENERanno 2048/4096 overlap inference、segment/fragmentation/postprocess evaluator、superfamily token head、embedding clustering、job matrix 与 Slurm scripts。
- Verdict: PASS_WITH_WARNINGS

#### Closed blockers
- [x] `embedding_cluster.py` contrastive A1/B1/C1 原先在 holdout split 前使用全量标签训练 projection；已改为先 stratified split，仅用 train split 学 projection，再评估 holdout。
- [x] `bp_overlap_segment_eval.py` 原先把多个染色体拼接后做 smoothing/segment metrics；已改为 per-chrom 计算，再输出 `WEIGHTED_MEAN`。
- [x] overlap stride 比较原先固定窗口数导致 stride 越小覆盖 genomic span 越短；已改为按 `window/stride` 放大窗口数，近似固定同一 genomic span。
- [x] Slurm scripts 原先缺 array 声明；已拆出 prep/overlap/superfamily/embedding_extract/embedding_cluster 专用 array sbatch，`run_cmd_array.sh` 在非 array 下直接失败。
- [x] sbatch conda 激活原先 fallback 到 base；已删除 fallback，`te_benchmark` 激活失败即失败。

#### Warnings
- 本轮是 quick screen，阈值仍固定 0.5，不能作为 claim-calibrated segment/postprocess 结论。
- window generation 仍按 FASTA 顺序截断；stride 比较已 span-matched，但不是均衡跨染色体采样。
- embedding fragment 抽取按 class quota 平衡，尚非 species × class 完全分层；解释前必须看 species/class counts。
- 当前环境可能缺 `sklearn`/`matplotlib`；脚本有 numpy fallback，图可能跳过但数值会输出。

#### Machine gate
- `outputs/PIPE-TEFM-SEG-SF-20260618/code_review_gate.json`
- `outputs/tefm_seg_sf_/code_review_gate.json`

### Code Review Gate: dfam39_extra_partitions_stage_wget_20260617 2026-06-17
- Reviewer mode: host-read-only
- Scope: Scratch-staged `wget -c` repair for Dfam 3.9 FamDB partitions 2/5/6/12/13/15 before `RMDFAM_FULLPARTITIONS_RERUN_20260617` full RepeatMasker+Dfam rerun.
- Verdict: PASS_WITH_WARNINGS

#### Blockers
- None open.

#### Warnings
- Host self-review only; acceptable for download repair but not sufficient as claim evidence.
- Final annotation chain remains gated on all required `.h5` partitions being present.

#### Confirmed OK
- Downloads compressed partitions under project scratch staging instead of writing active downloads directly to the RepeatMasker famdb directory.
- Uses `wget -c` with bounded attempts to preserve partial progress across network/file-system interruptions.
- Validates gzip before decompression.
- Decompresses to scratch temporary `.h5` and only then publishes to famdb via temp-copy + final rename.
- Does not overwrite existing successful `.h5` partitions.
- Machine gate written: `outputs/dfam39_extra_partitions_stage_wget_20260617/code_review_gate.json`.

#### Reviewed files
- `sbatch/dfam39_extra_partitions_stage_wget_20260617.sbatch` sha256 `87899c49d610c6e34e10fe552d91e1bedbbcc96a0d7e355eb4a0f721929e988c`

### Code Review Gate: dfam39_extra_partitions_repair_20260617 2026-06-17
- Reviewer mode: host-read-only
- Scope: Repair-only Dfam 3.9 FamDB partition acquisition for missing/corrupt partitions 2/5/6/12/13/15 before `RMDFAM_FULLPARTITIONS_RERUN_20260617` full RepeatMasker+Dfam rerun.
- Verdict: PASS_WITH_WARNINGS

#### Blockers
- None open.

#### Warnings
- Host self-review only; acceptable for download repair but not sufficient as claim evidence.
- Final annotation chain remains gated on all required `.h5` partitions being present.

#### Confirmed OK
- Uses per-partition flock locks.
- Does not overwrite existing successful `.h5` partitions.
- Writes fresh downloads to `.download.*` temp files before moving to final `.h5.gz`.
- Validates gzip before decompression and writes decompressed `.h5` to temp before final move.
- Machine gate written: `outputs/dfam39_extra_partitions_repair_20260617/code_review_gate.json`.

#### Reviewed files
- `sbatch/dfam39_extra_partitions_repair_20260617.sbatch` sha256 `9450ed959c1ca347bb5defc0300720b909173a488de8f0e7b1db01c64838c8ec`

### Code Review Gate: RMDFAM_FULLPARTITIONS_RERUN_20260617 2026-06-17
- Reviewer mode: host-read-only
- Scope: CPU-only RepeatMasker+Dfam full-partition rerun over all current ready-by-design animal/plant self Label-A species and assemblies.
- Verdict: PASS_WITH_WARNINGS

#### Blockers
- None open.

#### Warnings
- Dfam partition download/prebuild is still in progress. Do not submit the chunk array until `famdb info` shows partitions 1, 2, 3, 4, 5, 6, 12, 13, 15 and the run-scoped overlay probe confirms plant and missing-animal species libraries are non-empty.
- Old self-run Label-A annotations must not be deleted until this run completes chunk QC, species merge, and ready-by-design repointing.

#### Confirmed OK
- Target manifest is generated from the current `02_ready_by_design/manifests/SPLIT_MANIFEST_ALL.tsv`, yielding 30 unique species/assemblies and 495 chunks.
- Human assemblies included: hs1 as `human`, plus `human_hg19` and `human_hg38`.
- Chunk job writes to a new unique run root: `software_outputs/repeatmasker_dfam/raw_runs/self_labelA/RMDFAM_FULLPARTITIONS_RERUN_20260617`.
- RepeatMasker flags are `-pa 4 -xsmall -gff -species <species>`; no `-a` output is requested.
- Chunk completion requires final `.out.gz`, `.out.gff.gz`, `.tbl.gz`, and `.masked.gz`; a bare `COMPLETE` marker is insufficient.
- Merge job consumes only `chunk_manifest.tsv` and `species_manifest.tsv` from the new run root and writes per-species merged outputs under the same run.
- Syntax checks passed: `python3 -m py_compile` for added Python scripts and `bash -n` for the chunk/merge sbatch scripts.

#### Required fixes before submit
- Complete Dfam downloads and regenerate `rmlib.config`.
- Prepare and probe `rm_lib_overlay`.
- Re-run this gate only if any reviewed script/config/manifest changes before submission.

### Code Review Gate: self_labelA_vs_ucsc_all_species_20260617 2026-06-17
- Reviewer mode: host-read-only
- Scope: CPU-only srun audit comparing all ready-by-design species/assemblies with both self Label-A and UCSC/local strict TE comparator annotations.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `scripts/experiments/compare_self_labelA_ucsc.py`; `sbatch/self_labelA_vs_ucsc_all_species_20260617.sbatch`; `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_ALL_SPECIES_20260617/pair_manifest.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md

#### Blockers
- None.

#### Warnings
- Review independence is `host_self`.
- This is source-concordance evidence only, not model-performance evidence.
- Current metrics are strict TE merged bp overlap/Jaccard; class/family-level decomposition is not included in this run.

#### Confirmed OK
- Label sources are read from `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_ALL_SPECIES_20260617/pair_manifest.tsv`, derived from `02_ready_by_design/manifests/SPLIT_MANIFEST_ALL.tsv`.
- Self-run `.out.gz` parsing keeps only strict TE top-level classes (`LINE`, `SINE`, `LTR`, `DNA`, `RC`, `Retroposon`) before comparing against `*.te_strict.bed`.
- Intervals are merged within each source before bp-level overlap, so fragment counts do not inflate coverage.
- `sbatch/self_labelA_vs_ucsc_all_species_20260617.sbatch` requests CPU only on `private-teodoro-gpu` and uses `srun --cpu-bind=cores`.
- Output path is unique: `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_ALL_SPECIES_20260617/`.
- Machine gate written: `outputs/self_labelA_vs_ucsc_all_species_20260617/code_review_gate.json`.

#### Reviewed files
- `scripts/experiments/compare_self_labelA_ucsc.py` sha256 `5c88d80c989043a7c33c6f6e52fb6b849ed4a5bb64577b2623ff5121f0035bbf`
- `sbatch/self_labelA_vs_ucsc_all_species_20260617.sbatch` sha256 `a710149622b4ce2355a91720ef04d8885f4c42791b3dc14fdefd5614c7cb7c19`
- `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_ALL_SPECIES_20260617/pair_manifest.tsv` sha256 `a7f7c926c00e22b0d444e9ff4fefcbbbc792a784a32322c8cd1cc56e5f74a0a2`

### Code Review Gate: RMDFAM_PLANTTE_COMPLETION_20260617 2026-06-17
- Reviewer mode: host-read-only
- Scope: Complete missing PlantTE self-run RepeatMasker+Dfam Label-A for `sorghum`, `brachypodium`, `setaria_italica`, `wild_rice`, `teosinte`, `arabidopsis_lyrata`, and `soybean`.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `scripts/experiments/repeatmasker_dfam_custom_manifest.py`; `scripts/experiments/merge_repeatmasker_species_chunks.py`; `scripts/experiments/audit_repeatmasker_chunk_outputs.py`; `sbatch/repeatmasker_dfam_plantte_completion_chunks_20260617.sbatch`; `sbatch/repeatmasker_dfam_plantte_completion_merge_20260617.sbatch`; `configs/RMDFAM_PLANTTE_COMPLETION_20260617/species_table.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] All seven target FASTA paths resolve locally; `Arabidopsis lyrata` was downloaded from Ensembl Plants current FTP before manifest generation.
- [x] Manifest has 93 chunk rows and 7 species rows.
- [x] Chunk script uses `-xsmall -gff` and does not request `-a`.
- [x] Chunk script checks the RepeatMasker crossmatch matrices that previously caused ProcessRepeats failures.
- [x] After the initial plant submission exposed shared-library cache writes, the chunk script was updated to copy `RM_LIB_OVERLAY` into each task's node-local scratch directory before running RepeatMasker.

#### Warnings
- Review independence is `host_self`.
- This produces Label-A input annotations only; it does not by itself satisfy the model/evaluator claim contract.

#### Confirmed OK
- `bash -n` passed for both new sbatch scripts.
- `python3 -m py_compile` passed for the manifest, merge, and audit scripts.
- `pre_submit_gate.py` passed for run-level and sbatch-name-level gate IDs.
- Initial chunk job `8997173` was canceled after shared `CONS-Dfam_3.9/*.working/refineableHash.dat` writes caused Remote I/O errors.
- Retry chunk job `8997675` and dependency merge job `8997676` were submitted with per-task local library overlays.

#### Fix / waiver record
- Machine gates written to `outputs/RMDFAM_PLANTTE_COMPLETION_20260617/code_review_gate.json`, `outputs/repeatmasker_dfam_plantte_completion_chunks_20260617/code_review_gate.json`, and `outputs/repeatmasker_dfam_plantte_completion_merge_20260617/code_review_gate.json`.

### Code Review Gate: UCSC_RMSK_SPECIES_PLANTS_FUNGI_20260617 2026-06-17
- Reviewer mode: host-read-only
- Scope: Materialize available plant/fungi UCSC/local external RepeatMasker comparator annotations into a run-like, decompressed layout under `software_outputs/repeatmasker_dfam/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_PLANTS_FUNGI_20260617`.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `scripts/experiments/materialize_ucsc_rmsk_run.py`; `scripts/experiments/process_ucsc_repeatmasker_te.py`; `configs/UCSC_RMSK_SPECIES_PLANTS_FUNGI_20260617/source_manifest.tsv`; `configs/UCSC_RMSK_SPECIES_PLANTS_FUNGI_20260617/missing_external_comparator.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] Output path is unique and separate from self-run Label-A outputs.
- [x] The run writes decompressed raw annotation files, strict TE BED files, plus-unknown TE BED files, per-species `SUMMARY.tsv`, and `COMPLETE` markers.
- [x] Missing comparator species are explicitly recorded in `missing_external_comparator.tsv` instead of being silently treated as available.
- [x] The materialization script now handles both compressed and uncompressed local sources by gzipping uncompressed local sources into the run `raw/` directory before decompression/processing.

#### Warnings
- Review independence is `host_self`.
- This is comparator evidence only; self-run RepeatMasker+Dfam remains Label-A for claim-bearing species.
- `fusarium` currently has 0 strict and 0 plus-unknown TE records because the available `Fusarium graminearum` RepeatMasker source contains only non-TE classes under the current filter.
- Documented plant comparator sources still missing: `setaria_italica`, `green_foxtail`, `tomato`, `wild_rice`, `arabidopsis_lyrata`, and `grape`.

#### Confirmed OK
- `python3 -m py_compile` passed for the materialization and TE conversion scripts.
- `pre_submit_gate.py --exp-id UCSC_RMSK_SPECIES_PLANTS_FUNGI_20260617` passed after the manifest/script hash updates.
- `srun` job `8974763` completed the first 14-target materialization pass; `srun` job `8974859` completed the fission yeast and Fusarium source-quality repair pass.
- `srun` job `8974989` updated the generated status contract so `fusarium` is explicitly marked `OK_ZERO_TE_AFTER_FILTER_WARNING`.
- Final `species_manifest.tsv` has 14 rows and 14 `COMPLETE` markers.

#### Fix / waiver record
- Machine gate written to `outputs/UCSC_RMSK_SPECIES_PLANTS_FUNGI_20260617/code_review_gate.json`.

### Code Review Gate: UCSC_RMSK_SPECIES_ANIMALS_20260617 2026-06-16
- Reviewer mode: host-read-only
- Scope: Materialize UCSC/legacy RepeatMasker comparator annotations for all species/assemblies listed in `docs/species_label_source_audit.md` into a run-like, decompressed layout under `software_outputs/repeatmasker_dfam/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_ANIMALS_20260617`.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `scripts/experiments/materialize_ucsc_rmsk_run.py`; `scripts/experiments/process_ucsc_repeatmasker_te.py`; `configs/UCSC_RMSK_SPECIES_ANIMALS_20260617/source_manifest.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] Manifest covers the audit species set: `human_hg19`, `human_hg38`, `human_hs1`, mouse, rat, dog, chicken, zebrafish, fruit fly, C. elegans, pig, cattle, horse, X. tropicalis, honeybee, and Tribolium.
- [x] Output path is unique and separate from self-run Label-A outputs.
- [x] Raw annotations are copied/downloaded into per-species `raw/` directories and decompressed into directly usable per-species files.
- [x] TE-only BED outputs are decompressed and use the documented strict / plus-unknown filter.

#### Warnings
- Review independence is `host_self`.
- Tribolium uses the old UCSC `triCas2.fa.out.gz` bigZips RepeatMasker snapshot because `triCas2/database/rmsk.txt.gz` is unavailable.
- hs1 uses UCSC `hs1.repeatMasker.out.gz` because `hs1/database/rmsk.txt.gz` returned 404.

#### Confirmed OK
- `python3 -m py_compile` passed for the materialization and TE conversion scripts.
- `pre_submit_gate.py --exp-id UCSC_RMSK_SPECIES_ANIMALS_20260617` passed.
- `srun` job `8974262` completed with exit code `0:0`.

#### Fix / waiver record
- Machine gate written to `outputs/UCSC_RMSK_SPECIES_ANIMALS_20260617/code_review_gate.json`.

### Code Review Gate: RMDFAM_STRESS_HUMAN_ASSEMBLIES_20260617 2026-06-16
- Reviewer mode: host-read-only
- Scope: Custom RepeatMasker 4.2.2 + Dfam 3.9 self-run for optional animal stress species (`opossum`, `lizard`, `x_laevis`) plus human assembly audit self-runs (`hg19`, `hg38`). Also covers the UCSC RepeatMasker to TE-only BED conversion script used for comparator labels.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `scripts/experiments/repeatmasker_dfam_custom_manifest.py`; `scripts/experiments/process_ucsc_repeatmasker_te.py`; `sbatch/repeatmasker_dfam_stress_human_prelib_20260617.sbatch`; `sbatch/repeatmasker_dfam_stress_human_chunks_20260617.sbatch`; `sbatch/repeatmasker_dfam_stress_human_merge_20260617.sbatch`; `configs/RMDFAM_STRESS_HUMAN_ASSEMBLIES_20260617/species_table.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] Species/assembly FASTA availability checked: all 5 target rows resolve to existing FASTA files.
- [x] Output path is unique: `software_outputs/repeatmasker_dfam/RMDFAM_STRESS_HUMAN_ASSEMBLIES_20260617` has no pre-existing chunk/species `COMPLETE` markers before submission.
- [x] Chunk and merge bounds checked: 119 chunk rows and 5 species rows; sbatch arrays are `1-119%24` and `1-5%5`.
- [x] Final-output audit is available and checks actual `.out/.gff/.tbl/.masked` files, not only `COMPLETE` markers.

#### Warnings
- Review independence is `host_self`; no separate fresh-context reviewer was invoked for this operational data run.
- The run is CPU-only but long; `private-teodoro-gpu` with 0 GPU is appropriate under the local smart-sbatch policy, but queue timing can still vary.

#### Confirmed OK
- `python3 -m py_compile` passed for the new manifest/conversion scripts and the existing merge/audit scripts.
- `bash -n` passed for all three new sbatch scripts.
- RepeatMasker flags remain `-xsmall -gff` with no `-a`, matching the current Label-A policy.
- UCSC TE-only comparator files are generated as both `strict` and `plus_unknown`; primary strict keeps `LINE/SINE/LTR/DNA/RC/Retroposon` and excludes tandem/simple/satellite/RNA classes.

#### Fix / waiver record
- Machine gate written to `outputs/RMDFAM_STRESS_HUMAN_ASSEMBLIES_20260617/code_review_gate.json`.

### Code Review Gate: repeatmasker_dfam_human_chr12_chr19_repair_20260616 2026-06-16
- Reviewer mode: host-read-only
- Scope: Repair incomplete human RepeatMasker+Dfam Label-A output by rerunning only hs1 chr12/chr19, rebuilding the human merge from 22 audited old chunks plus 2 repair chunks, and adding strict chunk-output audit gates.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `sbatch/repeatmasker_dfam_human_chr12_chr19_repair_20260616.sbatch`; `sbatch/repeatmasker_dfam_human_repair_merge_20260616.sbatch`; `scripts/experiments/merge_repeatmasker_species_chunks.py`; `scripts/experiments/audit_repeatmasker_chunk_outputs.py`
- Linked evaluator contract: not a model evaluator change; this is Label-A external-software output completeness repair.

#### Blockers
- None open.

#### Warnings
- Review independence is `host_self`; acceptable here because this is a data-preprocessing repair, not a claim-bearing model/evaluator change.
- Repair intentionally reuses 22 human chunks already audited as final-output complete and reruns only chr12/chr19; old incomplete merged human outputs are backed up before overwrite.

#### Confirmed OK
- `merge_repeatmasker_species_chunks.py --force --species-code human` now fails on the old manifest before writing outputs when chr12/chr19 final `.out` files are missing.
- `audit_repeatmasker_chunk_outputs.py` reports human as `MISSING_CHUNK_FINAL_OUTPUTS` and all other completed animals in `RMDFAM_SPECIES_ANIMALS_CHR_20260615` as `OK`.
- Repair chunk manifest contains only chunk indices 13 and 22, with output directories under `RMDFAM_HUMAN_CHR12_CHR19_REPAIR_20260616`, preserving old failed chunk directories for diagnosis.
- Human repair merge manifest points only chr12/chr19 to repair outputs and keeps the other 22 chunk output paths unchanged.

### Code Review Gate: <exp_id> <date>
- Reviewer mode: code-plan-reviewer / host-read-only / cli-advisory
- Scope:
- Verdict: PASS / PASS_WITH_WARNINGS / BLOCKED / WAIVED_BY_USER
- Linked implementation:
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [ ] 

#### Warnings
- 

#### Confirmed OK
- 

#### Fix / waiver record
- 

### Code Review Gate: repeatmasker_dfam_anchor_20260615 2026-06-15
- Reviewer mode: host-read-only after attempted separate Codex review
- Scope: RepeatMasker+Dfam anchor species manifest builder, manifest TSV, and CPU-only Slurm array submission script.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `scripts/experiments/repeatmasker_dfam_anchor_manifest.py`; `sbatch/repeatmasker_dfam_anchor_20260615.sbatch`; `software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/anchor_manifest.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] `sbatch/repeatmasker_dfam_anchor_20260615.sbatch`: initial Bash `IFS=$'\t' read` TSV parsing would have shifted empty fields for species without `legacy_backup_out`. Fixed before submission by parsing the manifest with Python `csv.DictReader`.

#### Warnings
- Separate Codex review was attempted, but its read-only sandbox failed with `bwrap: Creating new namespace failed: No space left on device`; final review independence is therefore `host_self`.
- `--time=5-00:00:00` may be insufficient for human or mouse. The script only touches `COMPLETE` after successful RepeatMasker completion, so timeout will be detectable rather than silently accepted.
- This produces external software annotation artifacts only. It can support data/label gates, but does not by itself satisfy the model-vs-baseline claim contract in docs/19.

#### Confirmed OK
- RepeatMasker smoke passed on plain FASTA and gz FASTA using `/home/users/j/jwang/.conda/envs/te_benchmark/bin/RepeatMasker` version 4.2.2 with Dfam 3.9 and RMBlast 2.14.1.
- Manifest contains six core anchor species with absolute FASTA paths, FASTA byte sizes, MD5 hashes, per-species output directories, and `action=submit`.
- Slurm script is CPU-only (`private-teodoro-gpu`, no GPU gres), run-scoped under `software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/`, and uses exp-scoped logs under `logs/repeatmasker_dfam/`.
- `bash -n` and Python bytecode compilation passed.

#### Fix / waiver record
- Machine gate written to `outputs/repeatmasker_dfam_anchor_20260615/code_review_gate.json`.

### Code Review Gate: repeatmasker_dfam_anchor_small_20260615 2026-06-15
- Reviewer mode: host-read-only
- Scope: Small-resource, small-species-first RepeatMasker+Dfam Slurm array reusing the existing anchor manifest.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `sbatch/repeatmasker_dfam_anchor_small_20260615.sbatch`; `software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/anchor_manifest.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] Duplicate-write risk is controlled only if original pending array tasks `8844442_[2-6]` are cancelled before submitting this small batch. The running human task remains untouched.

#### Warnings
- Review independence is `host_self`; separate Codex review was unavailable earlier due the read-only sandbox `bwrap` failure.
- `--time=5-00:00:00` with `RM_PA=3` may be insufficient for mouse. The script only creates `COMPLETE` after successful RepeatMasker completion.

#### Confirmed OK
- Task map is small-first and points to existing manifest rows: `c_elegans`, `fruit_fly`, `chicken`, `zebrafish`, `mouse`.
- Script uses CPU-only private Slurm resources (`12 CPU`, `64G`, no GPU gres) to fit around the already-running human task.
- Script checks for existing `COMPLETE` before running, preventing redundant work if a species finished elsewhere.
- `bash -n` passed.

#### Fix / waiver record
- Machine gate written to `outputs/repeatmasker_dfam_anchor_small_20260615/code_review_gate.json`.

### Code Review Gate: repeatmasker_dfam_anchor_fullfamdb_retry_20260615 2026-06-15
- Reviewer mode: host-read-only
- Scope: Full-FamDB retry Slurm array for the non-mammalian anchor species that failed against the conda-local partial FamDB.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `sbatch/repeatmasker_dfam_anchor_fullfamdb_retry_20260615.sbatch`; `software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/rm_lib_overlay/`; `software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/anchor_manifest.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] Missing Dfam partitions for C. elegans, Drosophila, chicken, and zebrafish in the conda-local FamDB are addressed by a run-scoped `LIBDIR` overlay pointing `famdb` to `.backup/data/libraries/earlgrey_runtime_famdb`.

#### Warnings
- Review independence is `host_self`; separate Codex review was unavailable earlier due the read-only sandbox `bwrap` failure.
- The full FamDB overlay uses symlinks into `.backup/data/libraries/earlgrey_runtime_famdb`; this path must remain available while jobs run.

#### Confirmed OK
- Full-FamDB overlay smoke tests passed for `Drosophila melanogaster` and `Caenorhabditis elegans`, showing Dfam 3.9 with 4,122,019 families and successful partition access.
- Retry task map is limited to failed non-mammalian species: `c_elegans`, `fruit_fly`, `chicken`, `zebrafish`.
- Script preserves prior failed `RUN_METADATA.txt` before retrying and skips if `COMPLETE` already exists.
- `bash -n` passed.

#### Fix / waiver record
- Machine gate written to `outputs/repeatmasker_dfam_anchor_fullfamdb_retry_20260615/code_review_gate.json`.

### Code Review Gate: repeatmasker_dfam_anchor_zebrafish_fullfamdb_20260615 2026-06-15
- Reviewer mode: host-read-only
- Scope: Standalone full-FamDB zebrafish retry using reduced memory to increase parallelism.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `sbatch/repeatmasker_dfam_anchor_zebrafish_fullfamdb_20260615.sbatch`; `software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/anchor_manifest.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] Duplicate-write risk is controlled only if pending array task `8845481_4` is cancelled before submitting this standalone zebrafish job.

#### Warnings
- Uses `40G` memory to fit current free resources. If this is too low, the job should fail without `COMPLETE` and be resubmitted at `64G`.
- Review independence is `host_self`.

#### Confirmed OK
- Script hard-checks that manifest row 4 resolves to `species_code=zebrafish`.
- Script uses the same full FamDB overlay that passed Drosophila and C. elegans smoke tests.
- Script skips if `COMPLETE` already exists and preserves previous `RUN_METADATA.txt`.
- `bash -n` passed.

#### Fix / waiver record
- Machine gate written to `outputs/repeatmasker_dfam_anchor_zebrafish_fullfamdb_20260615/code_review_gate.json`.

### Code Review Gate: PIPE-TEFM-SUPP-20260617 2026-06-17
- Reviewer mode: host-read-only
- Scope: UCSC strict-TE binary fine-tuning and transfer screen pipeline for DNABERT-2, NT-v2-500M, GENERanno, HyenaDNA, with NTv3/Evo2 compatibility smoke recorded separately.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `configs/pipelines/PIPE-TEFM-SUPP-20260617.yaml`; `pipelines/PIPE-TEFM-SUPP-20260617/prepare_ucsc_windows.py`; `pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py`; `pipelines/PIPE-TEFM-SUPP-20260617/run_cmd_array.sh`; `pipelines/PIPE-TEFM-SUPP-20260617/collect_results.py`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] A2 mixed-train validation originally reused the same selected chromosome as train; fixed by selecting a second eligible chromosome for validation when available.
- [x] Metrics JSON originally lacked an explicit machine-readable primary metric; fixed by adding `primary_metric=te_f1` and `metric_direction=higher_is_better`.
- [x] Runtime environment drift: login shell `coding-rna` uses incompatible transformers 5.11.0. Slurm/smoke execution is pinned to `/home/users/j/jwang/.conda/envs/te_benchmark/bin/python` where DNABERT-2, NT-v2-500M, GENERanno, and HyenaDNA load.

#### Warnings
- Review independence is `host_self`; separate Codex review was not used in this fast execution pass.
- Current metric is token-label proxy for non-single-nucleotide tokenizers. It is acceptable for quick model/window screening but not sufficient alone for final bp/segment-level manuscript claims.
- NTv3_650M_pre is currently BLOCKED for training because the local snapshot lacks `InstaDeepAI/ntv3_base_model` remote-code files required by `auto_map`; Evo2 is BLOCKED because the local snapshot lacks a HF-recognized `model_type`/tokenizer adapter.
- Eval uses UCSC `comparator_strict` only; species with missing strict comparator are skipped rather than silently evaluated against Label-A.

#### Confirmed OK
- Window generation uses UCSC strict TE BED (`comparator_strict`) from ready-by-design manifests and chromosome-level splits; human quick training follows the TE_final-style odd/even held-out chromosome scheme configured in `human_tefinal_split`.
- A2 mixture proportions are explicit in config: mouse 30%, zebrafish 20%, chicken 15%, western_clawed_frog 15%, fruit_fly 10%, c_elegans 10%.
- Output paths are run-scoped under `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/`, reports under `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/`, and logs under `logs/tefm_supp/PIPE-TEFM-SUPP-20260617/`.
- Python bytecode compilation passed for all new scripts.

#### Fix / waiver record
- Machine gates written to `outputs/TFSUPP_*_seed42/code_review_gate.json` and `outputs/SMOKE_hyenadna_w2048/code_review_gate.json` for this reviewed file set.

### Code Review Gate: PIPE-TEFM-LOCK-20260619 2026-06-19
- Reviewer mode: host-read-only after failed separate Codex review.
- Independence: host_self. A separate `codex exec --sandbox read-only` review was attempted but blocked by `bwrap: Creating new namespace failed: No space left on device`, so it could not read files and returned BLOCKED for environment reasons.
- Scope: non-claim comparability-lock validation + stress diagnostics for primary/stress panel split, species-specific recovery, multi-species fragmentation evaluation, sequence-level superfamily objective comparison, and main4+Unknown five-class token head.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `configs/pipelines/PIPE-TEFM-LOCK-20260619.yaml`; `pipelines/PIPE-TEFM-LOCK-20260619/*`; `sbatch/tefm_lock_*_20260619.sbatch`; `configs/pipelines/PIPE-TEFM-LOCK-20260619.*_jobs.tsv`
- Linked evaluator contract: docs/19_evaluator_contract.md
- Linked baseline reproduction: docs/20_baseline_reproduction.md

#### Blockers
- [x] Prep array originally had concurrent jobs that could race while writing per-root `eval_manifest.json`; fixed by reducing prep array concurrency to `%1`.

#### Warnings
- This is screen/non-claim only. ACTIVE_GOAL, docs/19, and docs/20 are not claim-ready.
- Review independence is weak (`host_self`) because the separate Codex read-only sandbox failed before file access.
- Stress recovery is target-species adaptation on held-out chromosomes, not zero-shot or universal all-animal generalization.
- Sequence-level superfamily classifier/probe uses embedding diagnostics and linear-probe style evaluation; it is an objective comparison, not an end-to-end superfamily claim.

#### Confirmed OK
- Python bytecode compilation passed for all new `PIPE-TEFM-LOCK-20260619` scripts.
- `bash -n` passed for all `tefm_lock` sbatch scripts.
- Job TSV row counts match sbatch array ranges: prep=13, train=6, eval=8, segment=10, embedding=6, summarize=1.
- Output paths are run-scoped under `software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/`, reports under `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/`, and logs under `logs/tefm_lock/PIPE-TEFM-LOCK-20260619/`.
- Five-class metrics include `te_detect_f1`, `main4_conditional_macro_f1`, `unknown_recall`, `main4_false_unknown_rate`, and `unknown_to_main4_rate`.
- Segment evaluation keeps primary and stress species in separate report paths and reports bp/segment/boundary/fragmentation metrics from the existing evaluator.

#### Fix / waiver record
- Machine gate written to `outputs/tefm_lock_/code_review_gate.json`; mirrored to `outputs/PIPE-TEFM-LOCK-20260619/code_review_gate.json`.

#### Addendum: SF5 Unknown mapping fix
- After the first prep pass, `animal_sf5_w4096/metadata.json` showed `Unknown` bp support was zero because the legacy superfamily mapper folded `RC`, `Retroposon`, `DNA?`, and `LTR?` into DNA/LTR.
- The scoped fix changed only `pipelines/PIPE-TEFM-LOCK-20260619/prepare_superfamily5_data.py`: strict SINE/LINE/LTR/DNA labels remain main4; ambiguous or non-main RepeatMasker classes now map to `Unknown`.
- Source BED recount confirmed nonzero Unknown support across the selected animal species, including mouse, zebrafish, chicken, western_clawed_frog, fruit_fly, and c_elegans.
- Python compilation passed after the fix; machine gates were refreshed with the new sha256 for all `tefm_lock_*_20260619` job scopes.

#### Addendum: segment retry guard
- The first segment array (`9152614`) had transient import-time failures in `transformers`/PIL on two tasks even though the referenced PIL files existed and repeated import smoke tests passed in `te_benchmark`.
- The failed segment array and its old summary dependency were cancelled; `sbatch/tefm_lock_segment_20260619.sbatch` was changed from `%4` to `%1` and now exports `PYTHONDONTWRITEBYTECODE=1` to reduce concurrent import/cache pressure.
- `bash -n` and Python bytecode checks passed; machine gates were refreshed before resubmission.

#### Addendum: segment screen budget
- The 1800-window segment retry was cancelled because runtime would dominate the screen experiment. `configs/pipelines/PIPE-TEFM-LOCK-20260619.yaml` was changed to `segment_max_windows: 600`, and job TSVs were regenerated.
- This keeps the multi-species fragmentation/boundary diagnostic but marks it as fast screen evidence only; a larger window count is required before manuscript-level segment claims.
- Machine gates were refreshed with hashes for the config and regenerated job TSVs before submitting fast segment job `9152732`.

### Code Review Gate: PIPE-TEFM-EXTEND-20260620 2026-06-20
- Reviewer mode: host-read-only after failed separate Codex review.
- Independence: host_self. A separate `codex exec --sandbox read-only` review was attempted but blocked by `bwrap: Creating new namespace failed: No space left on device`, so it could not read files.
- Scope: supplement screen for strict family/source embedding, base-pretrained SF5, animal-to-plant transfer, plant/cross-kingdom PU, stress anchors, PU smoothing, and decay formula.
- Verdict: PASS_WITH_WARNINGS
- Linked implementation: `configs/pipelines/PIPE-TEFM-EXTEND-20260620.yaml`; `pipelines/PIPE-TEFM-EXTEND-20260620/*`; `sbatch/tefm_extend_*_20260620.sbatch`; `configs/pipelines/PIPE-TEFM-EXTEND-20260620.*_jobs.tsv`

#### Warnings
- This is screen/non-claim only. Branches must be interpreted separately and not collapsed into one headline mean.
- Dfam consensus FASTA is not configured in this run; consensus embedding is expected to emit skipped metadata and cannot support a consensus-vs-genomic conclusion until a real FASTA is supplied.
- PU training does not use unannotated background as reliable negative; strict comparator evaluation remains a proxy against available labels and must be explained as label-limited.

#### Confirmed OK
- Python bytecode compilation passed for all new `PIPE-TEFM-EXTEND-20260620` scripts.
- `bash -n` passed for all `tefm_extend` sbatch scripts.
- Job TSV row counts match sbatch array ranges: prep=9, train=8, eval=81, segment=6, embedding_extract=5, embedding_cluster=20, formula=1, summarize=1.
- PU smoke data generation passed and positive/unknown bp counts are finite after the overlap double-count fix.
- Output paths are run-scoped under `software_outputs/tefm_extend/PIPE-TEFM-EXTEND-20260620/`, reports under `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/`, and logs under `logs/tefm_extend/PIPE-TEFM-EXTEND-20260620/`.

#### Addendum: empty consensus FASTA guard
- The first embedding-extract array exposed a command-generation bug: `dfam_consensus_fasta: ""` produced `--consensus-fasta  --out-jsonl ...`, so argparse treated `--out-jsonl` as the missing value.
- `pipelines/PIPE-TEFM-EXTEND-20260620/make_jobs.py` now omits `--consensus-fasta` when the config value is empty, allowing `embedding_strict.py extract-consensus` to write explicit skipped metadata.
- Job TSVs were regenerated and machine gates refreshed before resubmitting the embedding cluster and summary dependency chain.

#### Addendum: shared-gpu walltime guard
- The first train array was held pending with `PartitionTimeLimit`; `scontrol show partition shared-gpu` reports `MaxTime=12:00:00`.
- `sbatch/tefm_extend_train_20260620.sbatch` was changed from 14h to 12h before resubmitting the train/eval/segment/formula dependency chain.

#### Addendum: embedding extraction speed guard
- The first genomic embedding-extract tasks consumed CPU for over 1 hour without writing fragment outputs because the initial implementation fetched sequence for all TE intervals before choosing top families.
- `pipelines/PIPE-TEFM-EXTEND-20260620/embedding_strict.py` now performs interval-first top-family selection and only fetches sequences for retained labels up to `max_per_label`.
- Python compilation passed after the change; old slow extract tasks were cancelled and the embedding extract/cluster dependency chain will be resubmitted.

#### Addendum: eval/segment backfill walltime
- After training completed, eval/segment arrays were repeatedly held until late evening because their requested walltimes were too conservative for screen tasks.
- `sbatch/tefm_extend_eval_20260620.sbatch` was reduced from 12h to 3h and `sbatch/tefm_extend_segment_20260620.sbatch` from 8h to 3h before resubmitting, matching the 1200-sample eval and 600-window segment screen budget.

#### Addendum: eval/segment GPU backfill route
- Generic shared-gpu eval/segment jobs were still estimated for late evening due fairshare/priority. `sbatch --test-only` showed 3090 nodes could backfill several hours earlier.
- Eval and segment sbatches now request `gpu:nvidia_geforce_rtx_3090:1`. This is a screen inference route only; if 24GB VRAM is insufficient, retry on A100/H100 and record the OOM.

#### Addendum: eval/segment RTX5000 route
- Real 3090 submission was estimated later than generic due scheduler/fairshare changes. RTX5000 test-only showed the best earlier route with 32GB VRAM.
- Eval and segment sbatches were changed to `gpu:nvidia_rtx_5000:1`; if this route OOMs or schedules worse in practice, revert to generic/A100 and record the retry.

#### Addendum: eval/segment route reverted to generic
- Real RTX5000 submission was estimated much later than the generic shared-gpu route. The sbatches were reverted to `gpu:1` while keeping 3h walltime.
- Public-gpu was tested but estimated later than shared-gpu; generic shared-gpu remains the chosen route.
### Code Review Gate: DENOVO_B_ANIMAL_EVAL_20260620 2026-06-20

- Reviewer mode: separate Codex process using `/tmp/pre_submit_DENOVO_B_ANIMAL_EVAL_20260620/pack.md`; follow-up packs `review_fix_pack.md` and `review_path_fix_pack.md`.
- Scope: de novo TE benchmark source-generation scripts and Slurm jobs for `B_animal_production/genomes/eval_only` using RepeatModeler2, EDTA, RepeatScout, plus EarlGrey container build.
- Verdict: `PASS_WITH_WARNINGS`.
- Machine gate: `outputs/DENOVO_B_ANIMAL_EVAL_20260620/code_review_gate.json`.

Blockers found and closed:

- Closed: sbatch scripts originally `cd` into `/home/users/j/jwang/ab-initio-TE`; fixed by pinning `PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE` and adding a hard `readlink -f /home/users/j/jwang/ab-initio-TE == $PROJECT_ROOT` preflight before using the container-visible `/home` alias.
- Closed: runner originally allowed `partial` plus merely-existing GFF3 to write `DONE`; fixed so only `status == success` and non-empty `annotation.gff3` plus non-empty `library.fasta` can write `DONE`.
- Closed: resume originally trusted `DONE`; fixed so skip revalidates `status.json`, species/tool, genome/container paths and hashes, and non-empty outputs.

Warnings:

- `docs/19_evaluator_contract.md` remains draft; this run can generate external annotation sources but cannot support model/SOTA claims by itself.
- EarlGrey is not yet an annotation task in the matrix; first job only builds/configures the EarlGrey Singularity image, then EarlGrey species tasks must be appended after SIF availability is verified.

Reviewed file hashes are recorded in the machine gate JSON.

## Code Review Gate: DENOVO_B_ANIMAL_EVAL_20260620_BIND_FIX

- Date: 2026-06-20
- Reviewer mode: separate Codex pack-only review attempted twice; both were limited by `bwrap: Creating new namespace failed: No space left on device`; final pass is host_self after fixing both pack-review blockers.
- Scope: de novo benchmark TE-Benchmark runner fix for Singularity/Apptainer bind paths and stale DONE/FAILED marker handling before releasing pending tool array tasks and resubmitting failed task 1.
- Verdict: PASS_WITH_WARNINGS

### Blockers Fixed
- [x] Add explicit container binds for `/srv/beegfs` and `/home/users` before wrapper container calls; smoke test confirmed `repeatmodeler.sif` can see cattle FASTA after bind.
- [x] Clear stale `DONE` and `FAILED` markers before real reruns so failed/resubmitted tasks cannot leave contradictory sentinels.
- [x] Clear stale `FAILED` when a valid `DONE` causes a skip, preventing summary scans from reporting false failure.

### Warnings
- Separate Codex could not independently read the filesystem because of the current bwrap namespace error; its two pack-only reviews found blocker issues that were fixed. Final acceptance is host_self and limited to the changed runner plus smoke evidence.
- Existing EDTA task `9181684_2` was already running under the old process environment and was not restarted by this code change.

### Reviewed Files
- `scripts/experiments/denovo_benchmark/run_tecompare_tool.py` sha256 `95fd44b31439f3f6918f99970a9ecd1aab21a68938754c752051cb492bd12330`

## Code Review Gate: denovo_b_animal_eval_earlgrey_20260620

- Date: 2026-06-20
- Reviewer mode: separate Codex pack-only review plus host final pass. Separate reviewer could not read disk due `bwrap: Creating new namespace failed: No space left on device`, but reviewed the full pack and identified blockers that were fixed.
- Scope: EarlGrey pure de novo benchmark runner, task matrix, and CPU-only Slurm array for eight B animal-production eval-only genomes.
- Verdict: PASS_WITH_WARNINGS

### Blockers Fixed
- [x] `materialize_input()` now reuses a work/input genome only when it is the same file or has matching sha256, not merely matching file size.
- [x] `run_earlgrey_from_matrix.sh` now checks that TSV `task_id` matches `SLURM_ARRAY_TASK_ID`.
- [x] sbatch checks configured EarlGrey SIF exists before launching tasks, so failed container build cannot produce misleading task failures.

### Warnings
- Separate reviewer was pack-only because of local sandbox namespace failure; final acceptance is host_self after applying the reviewer blockers.
- The first EarlGrey submission should wait until `containers/earlgrey_configured_dfam39_0-16.sif` exists and passes a small `earlGrey -h` container smoke.

### Reviewed Files
- `scripts/experiments/denovo_benchmark/run_earlgrey_tool.py` sha256 `9459c9ad41aaef8e155de4beecb00a2b331e513f473c70a7256855ab5c00058d`
- `scripts/experiments/denovo_benchmark/run_earlgrey_from_matrix.sh` sha256 `57ee6d932e439f2a7629c7972c0873709a5ac9d081123ccb10e734686c727cff`
- `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/manifests/earlgrey_task_matrix.tsv` sha256 `a3f63af68d1fb340c02e0ec10886b104b2920217857f48d196ded8fb07b5c262`
- `sbatch/denovo_b_animal_eval_earlgrey_20260620.sbatch` sha256 `74a4c35f1bfca41fb93cbee4608354ce94088a54da58bedfd35940d11a9fc4bf`

#### Runtime permission addendum
- First shared-cpu EarlGrey race array `9183050` failed immediately with `execve(): scripts/experiments/denovo_benchmark/run_earlgrey_from_matrix.sh: Permission denied`.
- File mode was corrected to executable (`-rwxr-xr-x`) without changing content hash, and `pre_submit_gate.py --exp-id denovo_b_animal_eval_earlgrey_20260620` still passed before resubmission.

#### Runtime parameter addendum
- EarlGrey 7.2.1 logs reported `/usr/local/bin/earlGrey: illegal option -- q`; the runner no longer passes `-q yes`.
- `python3 -m py_compile scripts/experiments/denovo_benchmark/run_earlgrey_tool.py` passed after the change.
- Machine gate was refreshed with `run_earlgrey_tool.py` sha256 `d8294b5eddd8f103a13f9541f50056df48466fe22b75b96ef3d80a67dc1a362a`.

#### Runtime scheduling addendum: public-bigmem EarlGrey route
- Private 7-day EarlGrey rerun `9189743` had a scheduler start estimate of `2026-07-11T02:00:00`, so it was replaced before start.
- Added `sbatch/denovo_b_animal_eval_earlgrey_public_bigmem_20260620.sbatch` sha256 `a00552b3aba60b32072d5fef8b06af24373a0b5b763c3bf467a3b5d6cb27cf8a`.
- `pre_submit_gate.py --exp-id denovo_b_animal_eval_earlgrey_public_bigmem_20260620` passed with `PASS_WITH_WARNINGS`.
- The route is CPU-only and uses `public-bigmem` with `--array=1-8%2`, `16` CPUs, `128G`, and `4-00:00:00`; formal EarlGrey output directories were empty before submission.
- Private EarlGrey `9189743` was cancelled after public-bigmem job `9189981` was accepted to avoid duplicate writes.

## Code Review Gate: denovo_b_animal_eval_tools_20260620 RepeatScout shard repair

- Date: 2026-06-20
- Reviewer mode: host final after prior separate Codex attempts were blocked by `bwrap: Creating new namespace failed: No space left on device`.
- Scope: RepeatScout-specific repair after cattle failed in `build_lmer_table` with a negative allocation size on the full FASTA.
- Verdict: PASS_WITH_WARNINGS

### Blockers Fixed
- [x] `tool=repeatscout` now detects genomes above 900 Mb and runs RepeatScout on record-based FASTA shards, avoiding the whole-genome lmer-table integer overflow path.
- [x] Sharded outputs are merged into the same standardized files expected by the benchmark: `library.fasta`, `annotation.gff3`, and `metrics.json`.
- [x] The normal RepeatModeler2 and EDTA paths are unchanged.
- [x] `py_compile` and a small shard-construction smoke test passed.

### Warnings
- Review independence is weak (`host_self`) because separate Codex file access remains blocked in this environment.
- Sharded RepeatScout is a pragmatic whole-species benchmark repair. It may miss cross-shard repeat discovery, so final benchmark notes should state that RepeatScout was run in shard mode on large genomes.

### Reviewed Files
- `scripts/experiments/denovo_benchmark/run_tecompare_tool.py` sha256 `b545db450b09765385d2188403455b7768fec030f72882e98a2b5a3ff788fdaa`
- `scripts/experiments/denovo_benchmark/run_task_from_matrix.sh` sha256 `55a390539ea24c2eafc4c1c05d60fd191b2e73f8e693ec75ec53e7ec3db39fc2`
- `sbatch/denovo_b_animal_eval_tools_20260620.sbatch` sha256 `bdb8159b817b8f9c03f64df15df3ce7e54b75b42c3158f450563b6b6695bc73a`

#### Runtime scheduling addendum: shared-cpu small tool race
- Added `sbatch/denovo_b_animal_eval_tools_shared_small_20260620.sbatch` sha256 `4404a0f90df97c4acd75093c2b08f8750442c55bb41e79310f52267c7a5e8c6b`.
- Scope is restricted to small pending RepeatModeler2/EDTA task IDs `7-8,16-17,19-20%3`: lizard, red_flour_beetle, and western_honey_bee.
- Tool logic and output schema are unchanged; the scheduler reuses the reviewed matrix runner and TE-Benchmark wrapper.
- Matching private pending array elements must be cancelled before shared submission to avoid duplicate writes to the same species/tool directories.
- Warning: `shared-cpu` walltime is 12h; any timeout must be treated as failed/incomplete and rerun cleanly on private.

#### Runtime scheduling addendum: public-cpu long rerun
- Date: 2026-06-21.
- Shared-cpu 12h race completed only RepeatScout task IDs `18` and `21`; several other tasks timed out or were cancelled near walltime.
- Cancelled duplicate/incomplete pending or near-timeout tasks before rerun: private `9182082`, private array elements `9181684_10`, `9181684_11`, `9181684_13`, `9181684_14`, `9181684_22`, `9181684_23`, shared `9183049_15`, `9183049_24`, `9183694_17`, `9183694_19`, and `9183694_20`.
- Moved selected partial output directories to `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/raw_outputs/_quarantine_publiccpu_rerun_20260621`; no successful RepeatScout outputs or currently running private task IDs `2`, `4`, `5` were moved.
- Added rerun matrix `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/manifests/tool_task_matrix_publiccpu_rerun_20260621.tsv` sha256 `277e746509cb892df24b005d2cabac00df6b53462765bff0d2aa151994c9434e`; it preserves original task row positions and changes `memory_gb` to `80`.
- Added `sbatch/denovo_b_animal_eval_tools_publiccpu_rerun_20260621.sbatch` sha256 `f4fee7478cf09a99870ef5214b45ffe62bb485b81dc7a1c3f92411f9a4de8f1a`.
- `pre_submit_gate.py --exp-id denovo_b_animal_eval_tools_publiccpu_rerun_20260621` passed with `PASS_WITH_WARNINGS`.
- Submitted public-cpu 4-day rerun array `9245592` for task IDs `1,3,6-17,19-20,22-24%6`.

## Code Review Gate: PIPE-TEFM-ANCHOR-20260621

- Date: 2026-06-21.
- Reviewer mode: attempted separate Codex read-only pack review; environment failed with `bwrap: Creating new namespace failed: No space left on device`, so final verdict is host_self after mechanical path/TSV/hash checks.
- Scope: single-seed screen for insect-primary anchor training, background-inclusive embedding, Unknown/high-score unannotated SF5 diagnostics, and deployable/generalization anchor formula.
- Verdict: PASS_WITH_WARNINGS.

### Confirmed OK
- [x] New training is isolated to `software_outputs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/runs/insect_primary_4096`; no existing run path is overwritten.
- [x] Binary TE labels use the existing `prepare_ucsc_windows.py` / `te_token_task.py` strict TE bp-level contract with `-100` padding masks and TE-F1/AUPRC schema.
- [x] Insect-primary training uses species/split-explicit rows: `fruit_fly:fine_tune`, `c_elegans:fine_tune`, and `western_honey_bee:eval_only`; held-out eval is prepared separately for fine/stress species.
- [x] Background-inclusive embedding writes a separate `BG+main4` fragment file for metric comparison and a separate exploratory Unknown/high-score file for candidate interpretation.
- [x] Anchor formula has two tracks: deployable features exclude TE annotation-derived variables; annotation-aware features are explanatory controls only.
- [x] TSV generation succeeded with expected counts: prep=3, train=1, eval=24, diag_extract=1, embedding_cluster=8, sf5=1, formula=1, summarize=1.
- [x] `python3 -m py_compile pipelines/PIPE-TEFM-ANCHOR-20260621/*.py` passed after a sklearn compatibility fix.

### Warnings
- Review independence is weak (`host_self`) because separate Codex could not run in read-only sandbox on this filesystem.
- This is a screen-profile single-seed run and cannot support SOTA or final publication claims without later claim-grade validation.
- `western_honey_bee` is used as an eval-only anchor source because ready-by-design lacks a fine-tune role for that species in the B animal panel; report this explicitly when interpreting insect-primary results.

### Reviewed Files
- `configs/pipelines/PIPE-TEFM-ANCHOR-20260621.yaml` sha256 `0feac9bf5e2044bf802f378b67566ce58766941e05867cad07e0426746b32de2`
- `pipelines/PIPE-TEFM-ANCHOR-20260621/anchor_formula.py` sha256 `d7aae581a1b126d5f7b8e6961c7d8c549c40801225445301215fddab836caa98`
- `pipelines/PIPE-TEFM-ANCHOR-20260621/diagnose_fragments.py` sha256 `e60bc9dc432ced3907cab1cb946f2c37c41da5becbbf45d76e1757839819a7c0`
- `pipelines/PIPE-TEFM-ANCHOR-20260621/make_jobs.py` sha256 `029b0e9c7b13ff68fc47aaae18e587c1438602986e32cb7e81f29b66996f7e0c`
- `pipelines/PIPE-TEFM-ANCHOR-20260621/summarize_results.py` sha256 `4c6fa43db1431ab639286a4e2c1b2e57d9cee2aa162911b9efabf3c5ff9cfc16`
- `pipelines/PIPE-TEFM-ANCHOR-20260621/run_cmd_array.sh` sha256 `925e62fe72c2678375bee45d7490d97b21d7b7cdc3a74dfda3e03934fe4c7d54`
- `sbatch/tefm_anchor_prep_20260621.sbatch` sha256 `a95948838bb6842cf3a390efb6d3c072c29b5fd23e70fe0f4035a7954a7bf78d`
- `sbatch/tefm_anchor_train_20260621.sbatch` sha256 `b3014d743259a27d016755d468374ff6c1cf5f2d89a138fda2fc31602aed135e`
- `sbatch/tefm_anchor_eval_20260621.sbatch` sha256 `77a7a88b77bb3cc596c92509c20ec09fc91dc1977bc55d2a286114939123993f`
- `sbatch/tefm_anchor_diag_extract_20260621.sbatch` sha256 `8681db913010b5d250f9e75e450217708575c98d48eadb0c45c6e257761195a5`
- `sbatch/tefm_anchor_embedding_cluster_20260621.sbatch` sha256 `cf8c27fe7498a55b507d356f2e65960ed41046601fcaea52a3db47e3df71aa87`
- `sbatch/tefm_anchor_sf5_20260621.sbatch` sha256 `a65d63d801a33a937da3368d493979983d795586d3254a3ecd55696638b4c1c7`
- `sbatch/tefm_anchor_formula_20260621.sbatch` sha256 `12876f105cfe41ab8912bb6d9c5dd9e65faa2638141c33fdba3c37c6f94361d0`
- `sbatch/tefm_anchor_summarize_20260621.sbatch` sha256 `26ab9fad5306d54e6ac93ea51400525c4855354b8e5a48356065722d9fa03b1e`

## Code Review Gate: PIPE-TEFM-FINAL-20260623

- Date: 2026-06-23.
- Reviewer mode: separate explorer read-only review after one Codex read-only attempt failed from local `bwrap` namespace exhaustion. Initial explorer verdict was BLOCKED; blockers were fixed and the same explorer re-reviewed the patched files.
- Scope: final supplemental screen/validation pipeline for NTv2/NTv3 model-size x window matrix, species recovery audit, strict segmentation thresholds, and staged multi-anchor/decay follow-up.
- Verdict: PASS_WITH_WARNINGS.

### Blockers Fixed
- [x] Unknown/U regions are no longer trained or evaluated as negative: `prepare_ucsc_windows.py` paints `comparator_plus_unknown` as `-100`, then strict TE as `1`; token labels ignore `-100`; strict segment bp metrics run only on known bp and screen unknown predictions.
- [x] `prepare_species_holdout.py` now passes `comparator_plus_unknown` for species-specific recovery probe train/val/test.
- [x] NTv3 matrix eval commands now carry the same `TEFM_LOCAL_FILES_ONLY=0 HF_HOME=...` environment used by train/smoke; regenerated TSVs have 330/330 NTv3 eval commands with the env prefix.
- [x] `strict_segment` is approved only with an explicit `sbatch --dependency=afterok:<prep_jobid>` submission; it must not be submitted naked before prep completes.

### Confirmed OK
- [x] `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile` passed for the final pipeline, `te_token_task.py`, `prepare_ucsc_windows.py`, and `prepare_species_holdout.py`.
- [x] Human chrX plus-only Unknown smoke produced `bp_ignore=111`, confirming `-100` labels are materialized.
- [x] Job TSV counts are as expected: download=9, prep=15, smoke=9, train=45, eval=495, species_probe_prep/train/eval=22 each, strict_segment=12, summarize=1.
- [x] Existing sbatch array sizes match their TSVs: download 9, prep 15, smoke 9, strict_segment 12.
- [x] No train/eval sbatch is present or approved yet; first submission is limited to download/prep/smoke and prep-dependent strict_segment.

### Warnings
- `tefm_final_strict_segment_20260623.sbatch` has no embedded `#SBATCH --dependency`; submit command must include `--dependency=afterok:<prep_jobid>`.
- The first run remains screen/validation only and cannot support SOTA/publication claims.
- NTv3 performance must not be interpreted until model smoke passes; adapter/remote-code failures are runtime blockers, not model-quality evidence.

### Reviewed Files
- `pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py` sha256 `efbda0e772b859de33365909368bf19478f58461314a9026a7a276cc7a245c34`
- `pipelines/PIPE-TEFM-SUPP-20260617/prepare_ucsc_windows.py` sha256 `a5f02236422b597b9db2f38455163af0049810709de2f81913e97db34f20c622`
- `pipelines/PIPE-TEFM-CALIB-20260621/prepare_species_holdout.py` sha256 `fc5032d0e45c59ce94206fdd001dc8913f30e2a36b75ae5859c6a2f17d4b281a`
- `configs/pipelines/PIPE-TEFM-FINAL-20260623.yaml` sha256 `64030171e8e8e160242850fd795010099230d0401c9cd886886954b928b2858a`
- `pipelines/PIPE-TEFM-FINAL-20260623/download_snapshot.py` sha256 `f4b9b6661706e98d506b62b34a551353a3970ec84023d40d646de505e3cb9636`
- `pipelines/PIPE-TEFM-FINAL-20260623/make_jobs.py` sha256 `5119f3056abcb8d766670f5a9d06d005430a978ca853761507cdc3093b17e3ac`
- `pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py` sha256 `cfc8de970980a9266e71ec39ed16a406d340e770b2b42ea9f750ed775500351e`
- `pipelines/PIPE-TEFM-FINAL-20260623/summarize_results.py` sha256 `b832c742819f6312f8d2f0cfbff2844baa9bb2b0e971675d0348820e161fc0ff`
- `pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh` sha256 `925e62fe72c2678375bee45d7490d97b21d7b7cdc3a74dfda3e03934fe4c7d54`
- `sbatch/tefm_final_download_20260623.sbatch` sha256 `fe061cb3a2a3622e24e9943c26ae666c2a53bceccee215bba003061d9a148da0`
- `sbatch/tefm_final_prep_20260623.sbatch` sha256 `528cf33e2507df10df9f303b2994c19b3b5e9e9f71df2b0b3601b123b30e5fcc`
- `sbatch/tefm_final_smoke_20260623.sbatch` sha256 `cb9924cbb1d4ea0655fe8fdbf8788a6d1655b3ffd781d3ee16e755c7617ce4e2`
- `sbatch/tefm_final_strict_segment_20260623.sbatch` sha256 `91a67327113f030635673d492643a3d7fcb483a5fc64b9c6d57f0298add67257`

### Incremental Gate: PIPE-TEFM-FINAL-20260623 NTv2 train/eval sbatch

- Date: 2026-06-23.
- Reviewer mode: separate explorer read-only incremental review.
- Scope: NTv2-only train/eval sbatch after NTv3 smoke failed from gated `InstaDeepAI/ntv3_base_model` remote-code access.
- Verdict: PASS_WITH_WARNINGS.

#### Confirmed OK
- [x] `sbatch/tefm_final_train_ntv2_20260623.sbatch` array `1-15%3` covers only `ntv2_50m/100m/250m x 512/1024/2048/4096/8192`; train TSV row 16 starts NTv3.
- [x] `sbatch/tefm_final_eval_ntv2_20260623.sbatch` array `1-165%8` covers only the 165 NTv2 eval rows; eval TSV row 166 starts NTv3.
- [x] Selected train/eval rows contain no `ntv3` and use `TEFM_LOCAL_FILES_ONLY=1`.
- [x] Eval `--model-dir` paths correspond to train `--output-dir` paths.

#### Warnings
- Train sbatch must be submitted with explicit dependency on prep completion and NTv2 smoke success; do not depend on the whole smoke array because NTv3 smoke tasks failed.
- Eval sbatch must be submitted with explicit dependency on the NTv2 train job.
- These are screen-profile single-seed runs and cannot support final model-size claims until eval and later repeat/error-bar stages complete.

#### Reviewed Files
- `sbatch/tefm_final_train_ntv2_20260623.sbatch` sha256 `d7df96b92220a8e135e11148a3bf1a150d9bffde8ae18ffbabc4a26bcc3829fa`
- `sbatch/tefm_final_eval_ntv2_20260623.sbatch` sha256 `f8a115e65fdc8bbec7929b7d12175f837724b43634485560cca2b9f7c146a74b`
- `configs/pipelines/PIPE-TEFM-FINAL-20260623.train_jobs.tsv` sha256 `35950c71072d0755a59fb90f6993aac6e9bb4e7831439c7bbaae5dbfa63179d3`
- `configs/pipelines/PIPE-TEFM-FINAL-20260623.eval_jobs.tsv` sha256 `b2cd4efbc4f87ed7a6624d6f207fa122bb50c08faa403e168f70cbf9db848fd5`

#### Runtime addendum
- Initial NTv2 train submission `9571640` failed immediately because `EsmForTokenClassification` does not support `--gradient-checkpointing`.
- `pipelines/PIPE-TEFM-FINAL-20260623/make_jobs.py` was patched to omit `--gradient-checkpointing` for generated training commands, and train TSV was regenerated.
- New `make_jobs.py` sha256: `fce1ffd7fc08b5e63827cf9a3c010dce7f0882d9daab6a96beea1153b669b91a`.
## Code Review Gate Addendum: PIPE-TEFM-FINAL-20260623 Species Probe

- Date: 2026-06-23
- Scope: add Slurm entrypoints for the NTv2-500M species-specific recovery audit (`species_probe_prep/train/eval`, 22 species).
- Verdict: PASS_WITH_WARNINGS.
- Reviewed files:
  - `sbatch/tefm_final_species_probe_prep_20260623.sbatch`
  - `sbatch/tefm_final_species_probe_train_20260623.sbatch`
  - `sbatch/tefm_final_species_probe_eval_20260623.sbatch`
  - `configs/pipelines/PIPE-TEFM-FINAL-20260623.species_probe_prep_jobs.tsv`
  - `configs/pipelines/PIPE-TEFM-FINAL-20260623.species_probe_train_jobs.tsv`
  - `configs/pipelines/PIPE-TEFM-FINAL-20260623.species_probe_eval_jobs.tsv`
  - `pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh`
  - `pipelines/PIPE-TEFM-CALIB-20260621/prepare_species_holdout.py`
  - `pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py`
- Checks:
  - Manifest probe list was checked against actual `species_code` rows in H0/B_animal/C_plant manifests; all 22 probe species have a row with `comparator_strict`.
  - Initialization model exists at `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_ntv2_500m_H0_w4096_seed42/best_model`.
  - `prep -> train -> eval` is independent of the active NTv2 size sweep, so it can run in parallel.
- Warnings:
  - 500M 4096-bp species-specific training may be slow on shared GPU. The train array is intentionally limited to `%2`; if it OOMs, move the train array to a larger GPU partition rather than changing the biological protocol.
  - This audit is a soft annotation-quality/domain-shift diagnostic. A non-recovered species should not be automatically removed without label-source concordance or stronger supporting evidence.

Runtime repair addendum:
- Initial species-probe train job `9571761` failed immediately for early array tasks because the existing `ntv2_500m` `best_model` directory did not include `modeling_esm.py`, while its config still referenced dynamic `auto_map` code.
- Fix: `te_token_task.py train` now accepts an existing training run root as `--model-path`; when `training_meta.json` is present, it initializes through `load_trained_model()` and records the original base model path in the new run metadata. `make_jobs.py` now points species-probe initialization at the full `TFSUPP_ntv2_500m_H0_w4096_seed42` run root rather than its incomplete `best_model` subdirectory.
- This does not change ordinary NTv2 size-sweep training behavior because those rows still point at raw pretrained model directories without `training_meta.json`.
- Retry `9571897` then confirmed the loader fix but OOMed on 10-12GB shared GPUs. The species-probe train sbatch now requests `gpu:nvidia_a100_80gb_pcie:1`, preserving the protocol and moving only the resource target.
- Strict-segment retry addendum: first strict segment job `9571593` completed prediction for 1200 windows but stalled in fragment/segment matching. `strict_segment_eval.py` now uses sorted interval scans instead of nested all-by-all segment matching, preserving the same IoU/boundary/fragmentation metrics while avoiding pathological runtime when raw predictions are highly fragmented.
- NTv2 size-sweep resource addendum: `ntv2_50m_w8192` failed on a 12GB GPU with CUDA OOM after the first step. Pending high-memory rows were removed from the generic array and moved to `tefm_final_train_ntv2_a100_retry_20260623.sbatch` on A100 80GB: failed 50M-8192, 100M 2048/4096/8192, and all 250M windows. This changes only resource placement, not seed/data/model/window/training hyperparameters.
- Strict-segment data-source addendum: optimized retry `9571966_4` failed because `western_honey_bee` was included as a stress strict-segment target, while the `animal_fine_w4096` prep only contains the animal fine-tune panel. `make_jobs.py` now routes strict-segment honeybee rows to the already prepared species-probe holdout test data under `data/species_probe_ntv2_500m/western_honey_bee/test` and labels those outputs as `species_probe_western_honey_bee`. `pre_submit_gate.py --exp-id PIPE-TEFM-FINAL-20260623` passed after the hash update; failed row 4 was resubmitted as `9572268_4`, and pending row 10 will read the repaired TSV path.
- Species-probe gate-staleness addendum: after the strict honeybee `make_jobs.py` edit, the active `9571917` species-probe train array rows 4-22 were blocked by `pre_submit_gate.py` before training because the species-probe train gate still recorded the prior `make_jobs.py` hash. The train/eval gate metadata was updated to the current hash and both `pre_submit_gate.py --exp-id tefm_final_species_probe_train_20260623` and `--exp-id tefm_final_species_probe_eval_20260623` pass. The impossible old eval dependency `9571918` was cancelled, and failed train rows 4-22 were resubmitted unchanged as A100 retry `9572480`.

## Code Review Gate: tefm_final_ntv3_recovery_20260629

- Reviewer mode: separate read-only explorer + host machine gate
- Scope: NTv3-only final supplementation recovery after HF auth and BeeGFS recovery. Added NTv3-only download/smoke/train/eval sbatch entrypoints without changing existing TSVs, label logic, split logic, or evaluator code.
- Verdict: PASS_WITH_WARNINGS for `tefm_final_download_ntv3_20260629` and `tefm_final_smoke_ntv3_20260629`; BLOCKED for NTv3 train/eval until all NTv3 download and smoke rows are `ok:true`.

### Blockers
- [x] Download sbatch initially lacked explicit `HF_HOME`; fixed in `sbatch/tefm_final_download_ntv3_20260629.sbatch`.
- [ ] NTv3 train/eval gates remain blocked until download rows 4-9 and smoke rows 4-9 complete successfully.

### Warnings
- New download/smoke may overwrite old NTv3 failed status JSONs, but do not touch completed NTv2 train/eval outputs.
- Submit order must remain `download -> smoke -> train -> eval` via Slurm dependencies.
- 8M/100M training is pinned to 24GB RTX 3090 rather than arbitrary small GPUs; 650M training is pinned to A100 80GB. 8192-window rows may still need resource repair if OOM occurs.

### Confirmed OK
- Array ranges select only NTv3 rows: download/smoke `4-9`, train small `16-25,31-40`, train 650M `26-30,41-45`, eval small `166-275,331-440`, eval 650M `276-330,441-495`.
- `run_cmd_array.sh` uses physical TSV line numbers and TSVs have no header.
- New sbatch files do not change label/split/evaluator semantics; `te_token_task.py` remains the binary TE token classifier with `-100` ignored labels and TE-F1/AUPRC metrics.
- Machine gate files written under `outputs/tefm_final_*_ntv3_*_20260629/code_review_gate.json`; pre-submit gate passes for download/smoke and blocks train.

### Submission
- Submitted download array: `9837805`.
- Submitted smoke array with `afterok:9837805`: `9837806`.
- No NTv3 train/eval job submitted at this gate.

### Runtime Recovery Addendum 2026-06-29

- The first NTv3 download recovery showed `401 Unauthorized` for rows 4-7 because the project-local `HF_HOME` did not contain the already-authenticated Hugging Face token. The NTv3-only sbatch files now export `HF_TOKEN` from `/home/users/j/jwang/.cache/huggingface/token` without printing it to logs.
- Download retry `9838465` completed for the previously failed NTv3 rows, and serial smoke job `9838992` completed all six NTv3 variants. Smoke confirmed the wrapped token classifier loads all NTv3 8M/100M/650M, 8kb and non-8kb checkpoints.
- Initial train jobs `9839139`/`9839140` failed before producing valid model evidence because NTv3 tokenization is single-base while the old `offset_or_kmer` label mode compressed labels as if they were k-mers. This failure is a label-alignment runtime bug, not a performance result.
- Fix: `WindowDataset.encode_labels()` now supports `ntv3_single`, and `configs/pipelines/PIPE-TEFM-FINAL-20260623.yaml` maps all six NTv3 models to `token_label_mode: ntv3_single`; regenerated training TSV rows 16-45 carry `--token-label-mode ntv3_single`.
- Separate review returned `PASS_WITH_WARNINGS` for the corrected NTv3 train gates. Effective training retries are `9839610` for NTv3 8M/100M rows on RTX 3090 and `9839611` for NTv3 650M rows on A100 80GB.
- As of this addendum, `9839610`/`9839611` are still running. Six valid training result files exist: all five `ntv3_8m_pre_8kb` windows and `ntv3_650m_pre_8kb` at 512bp. NTv3 eval gates remain intentionally `BLOCKED` until all 30 corrected NTv3 training rows complete successfully.

### Eval Gate Release Addendum 2026-06-29

- Corrected NTv3 training finished successfully: `9839610` and `9839611` produced 30/30 `test_results.json` files with no failed/OOM/NaN Slurm records.
- Human H0 training-screen best among NTv3 rows at release time: `ntv3_650m_pre_H0_w4096_seed42`, TE-F1 `0.9196207335068749`, macro-F1 `0.9213714417253287`, AUPRC `0.9775194715378774`.
- Eval gate files were released from `BLOCKED` to `PASS_WITH_WARNINGS` after the train completion check:
  - `tefm_final_eval_ntv3_small_20260629`: `pre_submit_gate` PASS.
  - `tefm_final_eval_ntv3_650m_20260629`: `pre_submit_gate` PASS.
- Submitted NTv3 generalization eval arrays:
  - small NTv3 8M/100M rows `166-275,331-440%8`: job `9844255`.
  - NTv3 650M rows `276-330,441-495%4`: job `9844256`.

### Eval Load-State Repair Addendum 2026-06-29

- Eval arrays `9844255` and `9844256` failed fast before producing metric JSONs. This was a checkpoint reload issue, not model performance: NTv3 `model_state.pt` contains rotary embedding cache buffers (`*.rotary_embedding.cos_cached` / `*.rotary_embedding.sin_cached`) that are regenerated by the backbone and are not stable learned parameters.
- Fix: `load_trained_model()` now filters only those two rotary cache suffixes before strict `load_state_dict()`. Other missing/unexpected parameters still fail, preserving protection against real checkpoint/schema mismatch.
- Validation: `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile` passed for `te_token_task.py`, and a 5-window eval smoke on `ntv3_8m_pre_8kb_H0_w512_seed42 -> animal_fine/mouse` successfully wrote `/tmp/tefm_ntv3_eval_smoke_20260629.json`.
- Eval gate hash was refreshed to `pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py` sha256 `ce9d5dbb1dd2da5db76440c0396a1883a71790576f9b42f83278c7e1b423ca6a`; retried eval jobs should supersede `9844255`/`9844256`.
- Retried NTv3 generalization eval arrays:
  - small NTv3 8M/100M rows `166-275,331-440%8`: job `9845158`.
  - NTv3 650M rows `276-330,441-495%4`: job `9845159`.

## Code Review Gate: denovo_b_animal_eval_denovo_dfam_publiccpu_20260629

- Date: 2026-06-29
- Reviewer mode: host read-only gate
- Scope: B-animal eval de novo+Dfam augmentation array and downstream UCSC compare chain for the 8 eval-only animal species in `02_ready_by_design/B_animal_production/genomes/eval_only`.
- Verdict: PASS_WITH_WARNINGS

### Confirmed OK
- [x] `sbatch/denovo_b_animal_eval_denovo_dfam_publiccpu_20260629.sbatch` is CPU-only on `public-cpu`, uses unique log paths under `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/denovo_dfam_20260629/`, and reads the fixed 32-row `denovo_dfam_task_manifest_20260629.tsv`.
- [x] `scripts/experiments/denovo_benchmark/run_denovo_dfam_repeatmasker.py` no longer assumes a single `specieslib` file only. It now supports both `specieslib` and mammal-style split Dfam component libraries (`cutlib/longlib/retrolib/...`) and also accepts `<species>.working/specieslib` for still-materializing overlays.
- [x] Smoke evidence on `pig` proved the combined library is built successfully from split Dfam components plus the de novo library before starting RepeatMasker; this removes the previous guaranteed startup failure for mammalian rows.
- [x] `scripts/experiments/prebuild_repeatmasker_specieslibs.py` now audits split component libraries correctly instead of misclassifying mammalian overlays as `SPECIESLIB_TOO_SMALL`.
- [x] `sbatch/denovo_b_animal_eval_denovo_dfam_ucsc_compare_publiccpu_20260629.sbatch` is isolated, CPU-only, writes to a separate log directory, builds a pair manifest from `MANIFEST_ALL.tsv`, runs `compare_denovo_ucsc.py`, and finalizes a ranked UCSC strict-TE overlap report.
- [x] Compare stage is intentionally fixed to `--jobs 1`, avoiding the already observed local `ProcessPoolExecutor` instability seen in repeated self-label/UCSC overlap reruns.

### Warnings
- The old long-running local `prebuild_repeatmasker_specieslibs.py` process finished after the runner fix was added; if its previously written `specieslib_summary.tsv` is missing or stale, regenerate it once before relying on the summary table as evidence. This does not block the actual de novo+Dfam runs because the runner now resolves the overlay directly.
- The temporary smoke directory under `/tmp/denovo_dfam_smoke_pig_*` is non-authoritative and should not be used as benchmark evidence.
- Submission order must remain `9840108 -> 9840601 -> denovo_dFam array -> de novo+Dfam UCSC compare`; do not start the array before `9840601` because the remaining 5 EarlGrey libraries are still in flight.

### 2026-06-29 parser hardening addendum
- [x] `scripts/experiments/denovo_benchmark/run_denovo_dfam_from_matrix.sh` no longer uses `awk` header lookups that are fragile to CRLF task manifests. The runner now parses TSV rows with Python `csv.DictReader`, strips trailing `\r`, and preserves embedded spaces in `repeatmasker_species`.
- [x] A failed partial dry submission (`9843755`) exposed the old bug concretely: `output_dir` was parsed as the whole TSV row, sending outputs into malformed top-level directories. The malformed directories were removed and the gate was refreshed before resubmission.

### 2026-06-29 seqid remap addendum
- [x] `scripts/experiments/denovo_benchmark/compare_denovo_ucsc.py` now repairs standardized annotation seqids during compare instead of assuming finalized `annotation.gff3` already matches UCSC chromosome names. EDTA rows load `edta_output/id_mapping.json`; EarlGrey rows that were standardized from `*.fa.prep.out` reconstruct `ctg_* -> original header` mapping from `work/input/*.fa.prep` and the original genome FASTA.
- [x] Validation on the completed partial benchmark changed exactly the expected three false-zero rows and no others: `cattle EDTA 0.000000 -> 0.650028`, `horse EDTA 0.000000 -> 0.420504`, and `cattle EarlGrey 0.000000 -> 0.735879`. This confirms the fix addresses coordinate naming mismatch rather than changing overlap logic broadly.
- [x] Pending dependency compare jobs were refreshed after the hash change so they do not silently run unreviewed code: base compare `9840721 -> 9845747`, de novo+Dfam partial compare `9844164 -> 9845748`, and full de novo+Dfam compare `9841644 -> 9845764`.

### Reviewed Files
- `scripts/experiments/denovo_benchmark/run_denovo_dfam_repeatmasker.py` sha256 `a5ba502a4abfa4ee0735cc9412547bccec41f4f12de54be6a7e498bf97ef13fe`
- `scripts/experiments/denovo_benchmark/run_denovo_dfam_from_matrix.sh` sha256 `1a86e7508730ad45bcd467f6709357774c867ae52aeffc19056f4e3ce08f8bfb`
- `scripts/experiments/prebuild_repeatmasker_specieslibs.py` sha256 `8ad6e2a465b00162b87c431981c9bd9c6417bdab25ee0700c2c8f82aa2088a52`
- `scripts/experiments/denovo_benchmark/build_denovo_dfam_ucsc_manifest.py` sha256 `8102add6723df05ac29260a20896726f277972e61ec6260f4c5566a3b1b79dca`
- `scripts/experiments/denovo_benchmark/compare_denovo_ucsc.py` sha256 `48a6ad63b5c6f337b2e8fac28b26e7cf57e456f2a6fede94dee008fc82c3c4c7`
- `scripts/experiments/denovo_benchmark/finalize_denovo_ucsc_report.py` sha256 `6b7cae3f3c9f9793be387dddcafb731a6a080b64ec628637cf654b9b55acfffe`
- `sbatch/denovo_b_animal_eval_denovo_dfam_publiccpu_20260629.sbatch` sha256 `82e52a3fff0010fd5ae0205aca7f60b82bd549d419718d01b2f693c26514c790`
- `sbatch/denovo_b_animal_eval_denovo_dfam_ucsc_compare_publiccpu_20260629.sbatch` sha256 `fc3aac12a2c3f1fedcac0ad0876f02fe1afef4525a625ea31d953bb8c6df7d04`

## Code Review Gate: PIPE-TEFM-FINAL-EBAR/STRICTSEG-20260629

- Date: 2026-06-30
- Reviewer mode: host static gate with runtime repair addenda
- Scope: chromosome-repeat error-bar eval, promoted strict segment/boundary/fragmentation eval, and plant label/source QC for final candidate anchors.
- Verdict: PASS_WITH_WARNINGS after repairs; final accepted jobs completed.

### Confirmed OK

- [x] Error-bar prep/eval jobs `9849317` and `9849318` produced 66/66 metadata/eval JSONs.
- [x] Strict segment final output has 66/66 JSONs and 6600 TSV rows under `reports/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/summaries/`.
- [x] Strict evaluator now reports multi-IoU and multi-boundary thresholds instead of relying on IoU 0.5 / boundary 100 bp only.
- [x] Plant QC output was generated from the stable current-ready Label-A/UCSC audit and records 7 plant rows.

### Runtime Repair Addenda

- Initial strict job `9849319` failed all NTv3 rows with `RuntimeError: The size of tensor a (1024) must match the size of tensor b (1025)` because the evaluator reused an old `window+2` special-token inference path. `strict_segment_eval.py` now reads `training_meta.token_label_mode`; `ntv3_single` uses max_length=`window`. NTv3 retry `9850150` completed 33/33 rows.
- The first NTv2 strict rows were then judged superseded because the old k-mer fallback projected token probabilities to only the first bp positions instead of expanding them back to their sequence spans. `strict_segment_eval.py` now uses `offset_mapping` when available and, for NTv2 `EsmTokenizer`, expands `tokenizer.tokenize(seq)` spans in order after the leading special token. Corrected NTv2 retry2 `9852364` completed 33/33 rows.
- Intermediate NTv2 retry `9851972` and initial strict outputs must not be used as evidence; final summaries were regenerated after `9852364`.

### Reviewed Files

- `pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py` sha256 `1ed72d5a79420d8f5820f9969912c335c28821418a443258923c1cbbf273c72a`
- `configs/pipelines/PIPE-TEFM-FINAL-STRICTSEG-20260629.ntv2_retry_jobs.tsv` sha256 `7bf47e70cb88bafe3607d5dfad5ead2a8ad1d922041e2ac4a9e43ee1aef371f8`
- `configs/pipelines/PIPE-TEFM-FINAL-STRICTSEG-20260629.ntv3_retry_jobs.tsv` sha256 `ee71ae50755c8a0fe25f70e16c970aa8d64c57cf76d5e7a57c99c110b28ef18b`
- `sbatch/tefm_final_strictseg_ntv2_retry_20260629.sbatch` sha256 `821342163b3af66133b918a1fd652dc43196b483638abe485e391adc993432f8`
- `sbatch/tefm_final_strictseg_ntv3_retry_20260629.sbatch` sha256 `76b712cb4775de062aacb4839f5f946388278ddcab19e407fa7dfa8faa3a3743`

## Code Review Gate: PIPE-TEFM-FINAL-SELECTOR-20260630

- Date: 2026-06-30
- Reviewer mode: host static synthesis review
- Scope: local-only synthesis script for multi-anchor recommendations, species-probe quality audit, and deployable-vs-annotation-aware selector formula from completed evidence.
- Verdict: PASS_WITH_WARNINGS

### Confirmed OK

- [x] Script reads existing TSV/JSON evidence only; it does not train models, submit Slurm jobs, or overwrite upstream metric files.
- [x] Species-specific NTv2-500M fine-tuning is kept as `species_probe_quality_audit.tsv`, separate from deployable non-species-specific anchor performance.
- [x] Deployable selector features exclude target TE-annotation-derived concordance variables; annotation-aware formula is reported only as an explanatory control.
- [x] `current_status.json` reports `ok=true`, 22 species-probe rows, 156 anchor performance rows, and 22 recommendation rows.

### Warnings

- This is screen/triage evidence, not a claim-grade selector validation.
- The observed multi-anchor oracle uses available historical anchor rows with uneven coverage; it supports panel-specific reporting but does not by itself prove a deployable policy.
- Leave-species-out RMSE remains high (`0.3040`), so selector output should guide anchor choice rather than be presented as calibrated expected F1.

### Reviewed Files

- `pipelines/PIPE-TEFM-FINAL-SELECTOR-20260630/final_selector_summary.py` sha256 `fe5733253a2c5308c586df42776b94f4473ad1c4d3aff4d6fa67b2dd5d4fb36b`
- `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/current_status.json` sha256 `94453d5129f27ec61ba9fc9c7ed13d1e007418e82bbbb707ed0b3d6411ec889e`

## Code Review Gate: PIPE-TEFM-FINAL-INTERPRET-20260630

- Date: 2026-06-30
- Reviewer mode: host static synthesis review
- Scope: local-only fragment interpretability screen from completed fragment JSONL and SF5 candidate prediction artifacts.
- Verdict: PASS_WITH_WARNINGS

### Confirmed OK

- [x] Script reads existing fragment/SF5 artifacts only; it does not train models, submit jobs, or modify upstream predictions.
- [x] Output separates strict background high-score candidates from Unknown annotation and known-main4 controls.
- [x] The report explicitly rejects a hidden-TE claim from the 9 high-score strict-BG candidates because SF5 assigns them almost entirely to BG.
- [x] `current_status.json` reports `ok=true`, 1409 fragment rows, and the expected source counts.

### Warnings

- This is an exploratory screen, not a mechanistic attribution result.
- High-score strict-BG sample size is only 9; use it to design matched-control tests, not to estimate general prevalence.
- The referenced PDFs exist in `docs/inputs/`, but no local PDF text extractor is installed; paper-derived method alignment is pending.
- Independent tri-review was run after this local synthesis and returned 3/3 `run-sanity-check-first`; claim-grade interpretability claims still require a later tri-review after saliency/occlusion/motif analyses are completed.

### Reviewed Files

- `pipelines/PIPE-TEFM-FINAL-INTERPRET-20260630/fragment_interpretability_summary.py` sha256 `16e834da6ac36ab97b486a89dcfb2c0019c381096fadcc033389748b40db783f`
- `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/current_status.json` sha256 `50fcaee4a2d54c1d540e4e66315922c1281292c6b9537905762bd8c185e381f5`

### Matched-control Addendum 2026-06-30

- Reviewer mode: host static synthesis review
- Scope: matched-control, k-mer enrichment, and PDF extraction addendum for the same fragment interpretability branch.
- Verdict: PASS_WITH_WARNINGS

Confirmed OK:

- [x] Script reads existing fragment/SF5 artifacts only and writes addendum outputs under the same report directory.
- [x] High-score strict-BG controls are constrained to the same species/chromosome (`western_honey_bee`, `GroupUn`) rather than using mixed-species background.
- [x] Unknown-main4-like controls are constrained to human known-main4 fragments and the output explicitly records poor GC matching.
- [x] PDF text extraction is now performed with `pypdf` and recorded as method scoping only.

Warnings:

- This addendum still does not run model-level saliency/occlusion.
- Unknown-main4-like matching is flagged `POOR_GC_MATCH`; do not use it as annotation-correction evidence.
- High-score strict-BG remains n=9 and should only support false-positive trigger diagnostics.

Reviewed files:

- `pipelines/PIPE-TEFM-FINAL-INTERPRET-20260630/matched_control_interpretability.py` sha256 `2a32bc8ec950adf0fe68992f740d73fe9f5d705e1effba048546604b1b749a14`
- `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/matched_control_status.json` sha256 `e87cfe8342ff92afc277d95d285c27fbbc4eb2ed6524bd352cd8b68b1096135e`

### Model Occlusion Smoke Gate 2026-06-30

- Reviewer mode: host static pre-submit review
- Scope: bounded GPU inference-only occlusion smoke for the fragment interpretability branch.
- Verdict: PASS_WITH_WARNINGS

Confirmed OK:

- [x] `model_occlusion_smoke.py` is inference-only and reads completed fragment/matched-pair artifacts; it does not train or modify upstream models.
- [x] The smoke is bounded: high-score strict-BG cases plus at most eight Unknown-main4-like case/control pairs, 64 bp chunks, binary and SF5 forward passes only.
- [x] `tefm_final_interpret_occlusion_20260630.sbatch` uses one private 3090 GPU, 2 h walltime, and exp-scoped logs/outputs.
- [x] Disk preflight has ample free space on BeeGFS and report directory is small.

Warnings:

- This is still a smoke-level occlusion diagnostic, not full attribution or saliency.
- It uses `N` chunk replacement and fragment-length context; future claim-grade attribution should compare at least one alternate perturbation baseline and full-window context.
- Results should be interpreted jointly with the matched-control quality flags, especially `POOR_GC_MATCH` for Unknown-main4-like candidates.

Reviewed files:

- `pipelines/PIPE-TEFM-FINAL-INTERPRET-20260630/model_occlusion_smoke.py` sha256 `945379092bb3529c78997ae812804f84727c7f848de5b447610bf951c5bd7af5`
- `sbatch/tefm_final_interpret_occlusion_20260630.sbatch` sha256 `7bf8c13e74fa42eff1489862d63602aa10ae93020e9dacea6e3848177e276815`

Runtime result:

- First submission `9853263` and second submission `9853287` were cancelled by the host because one-by-one/full-window fragment occlusion was too slow for a bounded smoke.
- Repaired script uses fragment-length context and batched per-fragment forward passes.
- Accepted submission `9853298` completed with Slurm state `COMPLETED`, exit code `0:0`.
- Output status: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/occlusion_smoke/occlusion_status.json`, sha256 `4a0d8bafb7ae2a27b083b723f15b501fd881f00f52a00e72db71df69d6644ce8`.

## Code Review Gate: DENOVO_B_ANIMAL_EVAL_RECHAIN_20260630

- Date: 2026-06-30
- Reviewer mode: host static pre-submit review
- Scope: rechain the B-animal eval de novo benchmark after the repaired EarlGrey tail job; run finalize, base de novo vs UCSC compare, full de novo+Dfam RepeatMasker overlay, and de novo+Dfam vs UCSC compare.
- Verdict: PASS_WITH_WARNINGS

### Confirmed OK

- [x] R2 finalize waits on the surviving EarlGrey tail tasks (`9840108_4`, `9840108_5`, `9840108_7`, `9840108_8`) plus repaired red flour beetle task `9854664_6`, instead of depending on failed array task `9840108_6`.
- [x] Base and de novo+Dfam comparison manifests are built from `02_ready_by_design/manifests/MANIFEST_ALL.tsv` and restrict rows to `design == B_animal_production` and eval-only roles (`mammal_holdout`, `invertebrate_holdout`, `optional_stress`).
- [x] Temporary manifest smoke check produced 32 base compare rows and 32 de novo+Dfam overlay tasks, matching 8 B eval species x 4 tools.
- [x] Dfam overlay R2 writes only under `DENOVO_B_ANIMAL_EVAL_20260620/dfam_augmented/<species>/<tool>` and skips existing `DONE` outputs, so completed P27 fix outputs are not overwritten.
- [x] Dfam overlay R2 is submitted only after the existing P27 fix array finishes (`afterany:9843979`) to avoid concurrent writes to the same output directories.
- [x] Compare scripts use UCSC strict TE comparator beds and write R2 reports to new `*_full_20260630` directories; they do not change Label-A or model training data.

### Warnings

- This is an external-tool benchmark/audit chain, not a claim-grade FM result.
- Reviewer independence is `host_self`; acceptable here because this is a rechain/path/dependency repair rather than new model or metric implementation.
- The final benchmark remains incomplete until all R2 jobs exit successfully and result tables are checked for missing/failed rows.

### Reviewed Files

- `sbatch/denovo_b_animal_eval_rechain_finalize_publiccpu_20260630.sbatch` sha256 `c31237176e33e5cb47ce06451e85b0c17a977478044c679aa29d7fb5be96ed98`
- `sbatch/denovo_b_animal_eval_rechain_ucsc_compare_publiccpu_20260630.sbatch` sha256 `329e558d6f95b8d970bb3dc72ce639d4f1b3b52577c0f762ee5e81da31f273f8`
- `sbatch/denovo_b_animal_eval_rechain_denovo_dfam_publiccpu_20260630.sbatch` sha256 `ccc7a4d8ce385366b91929c3f648d628c935535ae4ab9e4fff0fbbe31cc3b127`
- `sbatch/denovo_b_animal_eval_rechain_denovo_dfam_ucsc_compare_publiccpu_20260630.sbatch` sha256 `68a00e26f0195669ca25d4dbc98823d37eacc9e5560f83a4558ae7de7ed604df`
- `scripts/experiments/denovo_benchmark/finalize_existing_outputs.py` sha256 `b2136565ee3f1a7bcbfc550c87dee031b8be080f445c330b4a8a24876e43ef34`
- `scripts/experiments/denovo_benchmark/build_denovo_ucsc_manifest.py` sha256 `e72030d1fad74603bfd2bd5517d74497d9fff620db53defac8b6c05b4ebd02fc`
- `scripts/experiments/denovo_benchmark/build_denovo_dfam_species_table.py` sha256 `c2b525413a9f43ea19e7f4c04b7b0af48b007bb28f7afc6f763606f61679d033`
- `scripts/experiments/denovo_benchmark/build_denovo_dfam_task_manifest.py` sha256 `800422cd3b716a11c52b5dcd79d1c42a0512127b247fc13a0e041806d4ce2f68`
- `scripts/experiments/denovo_benchmark/run_denovo_dfam_from_matrix.sh` sha256 `1a86e7508730ad45bcd467f6709357774c867ae52aeffc19056f4e3ce08f8bfb`
- `scripts/experiments/denovo_benchmark/run_denovo_dfam_repeatmasker.py` sha256 `a5ba502a4abfa4ee0735cc9412547bccec41f4f12de54be6a7e498bf97ef13fe`
- `scripts/experiments/denovo_benchmark/build_denovo_dfam_ucsc_manifest.py` sha256 `8102add6723df05ac29260a20896726f277972e61ec6260f4c5566a3b1b79dca`
- `scripts/experiments/denovo_benchmark/compare_denovo_ucsc.py` sha256 `48a6ad63b5c6f337b2e8fac28b26e7cf57e456f2a6fede94dee008fc82c3c4c7`
- `scripts/experiments/denovo_benchmark/finalize_denovo_ucsc_report.py` sha256 `6b7cae3f3c9f9793be387dddcafb731a6a080b64ec628637cf654b9b55acfffe`
## Code Review Gate: PIPE-TEFM-STRUCTDEC-20260630

- Date: 2026-06-30
- Reviewer mode: host self-review
- Independence: host_self
- Scope: isolated smoke for jointly trained structured decoder losses attached to GENERanno token logits.
- Profile: smoke
- Verdict: PASS_WITH_WARNINGS

### Reviewed Files

- `pipelines/PIPE-TEFM-STRUCTDEC-20260630/train_joint_structured_decoders.py`
- `pipelines/PIPE-TEFM-STRUCTDEC-20260630/run_joint_structured_decoders.sbatch`

### Confirmed OK

- Label/mask: training and evaluation reuse `WindowDataset` from `te_token_task.py`, preserving `single_nt` token-label alignment and `-100` masking for special/padding tokens.
- Structural distinction from failed post-hoc path: losses are computed from `model(**batch).logits` during training, and gradients are backpropagated through model parameters; this is not inference-only HMM/CRF smoothing.
- Candidate mechanisms are structurally distinct for smoke: CE baseline, HMM-like row-normalized Markov NLL, CRF-like free transition NLL, and duration-aware fragmentation proxy.
- Metric guardrail: evaluation reuses strict segment/boundary functions from `strict_segment_eval.py` with IoU `0.8` and boundary `5 bp`, plus fragmentation diagnostics.
- Output paths are exp-scoped under `reports/tefm_final/PIPE-TEFM-STRUCTDEC-20260630/`, `outputs/PIPE-TEFM-STRUCTDEC-20260630/`, and `logs/PIPE-TEFM-STRUCTDEC-20260630/`.
- Sbatch is smoke-scoped, single seed `42`, and requests one A100 80GB GPU on `shared-gpu`.

### Warnings

- The semi-Markov branch is a differentiable duration-aware proxy, not a full exact semi-Markov dynamic program. It can only test whether duration-aware training has signal.
- This is a bounded human H0 quick-data smoke with at most 96 train windows and 40 eval windows. It cannot support a final fragmentation or annotation-usability claim.
- Reviewer independence is `host_self`, weaker than a separate external reviewer; acceptable here only because the profile is smoke and not claim-bearing.

### Required fixes before submit

- None for this smoke profile. If promoted beyond smoke, rerun code-review-gate with a separate reviewer and add a full data/split manifest.

### Repair addendum

- First submission `9860192` failed before training because the compute-node default `python3` was Python 3.9 and GENERanno remote code uses Python 3.10+ typing syntax. This is an environment issue, not a model/decoder failure.
- `run_joint_structured_decoders.sbatch` was updated to call `/home/users/j/jwang/.conda/envs/te_benchmark/bin/python` explicitly. The reviewed sbatch hash in `outputs/PIPE-TEFM-STRUCTDEC-20260630/code_review_gate.json` was refreshed after this edit.

## Code Review Gate: PIPE-TEFM-PURSUE-STRUCTDEC-20260630

- Date: 2026-06-30
- Reviewer mode: host static pre-submit review
- Independence: host_self
- Scope: bounded single-seed GENERanno 4096 structured-decoder screen adding boundary-aware auxiliary loss and semi-Markov retention loss to the prior joint HMM/CRF/semi-Markov cohort.
- Profile: screen
- Verdict: PASS_WITH_WARNINGS

### Reviewed Files

- `pipelines/PIPE-TEFM-STRUCTDEC-20260630/train_joint_structured_decoders.py` sha256 `faa59542d281dcfe767772cfa2e0d168501e0706f3b8e96c662a8b4c0201d704`
- `pipelines/PIPE-TEFM-STRUCTDEC-20260630/run_pursue_structured_decoders.sbatch` sha256 `d5b998c70271fb23598cf267628fb0588e266bcc3696182fd4321ed0171b57d3`

### Confirmed OK

- Label/mask geometry still comes from `WindowDataset`; all new losses respect `labels >= 0` and preserve `-100` ignored labels.
- `boundary_aux` and `semimarkov_retention` are training-time losses attached to model logits, not post-hoc threshold/gap smoothing.
- The screen retains the previous CE baseline, joint HMM, joint CRF, and semi-Markov proxy variants, so the new candidates are compared against the same bounded protocol.
- Strict segment metrics remain IoU `0.8` and boundary `5 bp`; output also includes `missed_true_rate`, `pred_true_backed_rate`, `short_true_backed_rate`, and CE-relative deleted true-backed vs false-fragment diagnostics.
- The sbatch writes to independent `PIPE-TEFM-PURSUE-STRUCTDEC-20260630` report/output/log directories and does not overwrite `PIPE-TEFM-STRUCTDEC-20260630`.
- The sbatch uses `/home/users/j/jwang/.conda/envs/te_benchmark/bin/python`, avoiding the previous Python 3.9 compute-node failure.

### Warnings

- Reviewer independence is `host_self`; acceptable for bounded screen but not for a claim-grade run.
- The semi-Markov branch is still a proxy/duration-aware loss, not an exact full semi-Markov dynamic program.
- The data is the same small human H0 quick panel used for the prior structured-decoder positive signal; success here only permits a larger validation panel, not a publication claim.

### Required fixes before submit

- None for this bounded screen profile.

## Code Review Gate: PIPE-TEFM-CAP-FRAGGRAPH-20260701

- Date: 2026-07-01
- Reviewer mode: host static pre-submit review
- Independence: host_self
- Scope: capability-pursue Round 2 fragment graph linker replacement component.
- Profile: screen
- Verdict: PASS_WITH_WARNINGS

### Reviewed Files

- `pipelines/PIPE-TEFM-CAP-FRAGGRAPH-20260701/train_fragment_graph_linker.py` sha256 `ee3714f7461dcd9aaaf46d164db2aa94553f24c34f0d181205cf5d38b4cde43b`
- `pipelines/PIPE-TEFM-CAP-FRAGGRAPH-20260701/run_fragment_graph_screen.sbatch` sha256 `c55e701ce1f15391bb7424c3320263c203387ab61529c57fbb6bfc1fce0939a4`
- `pipelines/PIPE-TEFM-CAP-FRAGARCH-20260701/train_interval_architectures.py` sha256 `a6b968cfb99c667c82b05f599b1f2a7e7fde3885b471dcc542a2ade248c20412`
- `pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py` sha256 `ce9d5dbb1dd2da5db76440c0396a1883a71790576f9b42f83278c7e1b423ca6a`
- `pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py` sha256 `1ed72d5a79420d8f5820f9969912c335c28821418a443258923c1cbbf273c72a`

### Confirmed OK

- The mechanism is a replacement component rather than a prohibited DEC-001 cousin: CE raw fragments become graph nodes and a learned edge classifier decides adjacency/link/fill.
- The primary `fragment_graph_keepall` decode preserves all CE raw fragments and learns only links between adjacent fragments, directly targeting true-backed deletion guardrails.
- No threshold/gap/HMM/CRF/survival-retention grid is introduced. Fixed 0.5 edge/node decision thresholds are screen defaults, not a searched parameter family.
- The same human/mouse quick panels, seed `42`, strict IoU/boundary metrics, missed_true_rate, pred_true_backed_rate, short_true_backed_rate, deleted fragment diagnostics, overmerge rate, split_true_rate, and mean fragments per true TE are retained.
- The sbatch writes to independent `PIPE-TEFM-CAP-FRAGGRAPH-20260701` log/output/report directories and runs `pre_submit_gate.py` inside the job.

## Code Review Gate: PIPE-TEFM-CAP-POSTPROC-20260701

- Date: 2026-07-01
- Reviewer mode: host static pre-submit review
- Independence: host_self
- Scope: bounded threshold/length-adaptive postprocess diagnostic for TE fragmentation.
- Profile: screen
- Verdict: PASS_WITH_WARNINGS

### Reviewed Files

- `pipelines/PIPE-TEFM-CAP-POSTPROC-20260701/threshold_length_postprocess_screen.py` sha256 `20837afcc70733c233ad1d34eace459bb26350a174fa43dbf51e3fb67cbf4ff2`
- `pipelines/PIPE-TEFM-CAP-POSTPROC-20260701/run_threshold_length_postprocess.sbatch` sha256 `305ce7757f54584a76b641a334401306da829691cfe9f76113e2ebccbe6f9f3e`
- `pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py` sha256 `1ed72d5a79420d8f5820f9969912c335c28821418a443258923c1cbbf273c72a`
- `pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py` sha256 `ce9d5dbb1dd2da5db76440c0396a1883a71790576f9b42f83278c7e1b423ca6a`

### Confirmed OK

- The run does not train a model and does not alter the promoted GENERanno checkpoint.
- The screen uses the same bounded human/mouse quick panel as `PIPE-TEFM-CAP-FRAGGRAPH-20260701`.
- The method space is diagnostic: raw multi-threshold, gap/min-length comparators, fixed HMM penalties, HMM plus short-fragment rescue, and length-adaptive short-raw/long-HMM.
- Metrics include bp precision/recall/F1, strict segment-F1 at IoU `0.5/0.7/0.8/0.9`, boundary-F1 at `5/10/25bp`, missed_true_rate, pred_true_backed_rate, short_true_backed_rate, deleted true-backed fraction, overmerge_rate, split_true_rate, and true-length-bin diagnostics.
- The sbatch writes to independent `PIPE-TEFM-CAP-POSTPROC-20260701` log/output/report directories and runs `pre_submit_gate.py`.

### Warnings

- Reviewer independence is `host_self`; acceptable for a bounded non-claim diagnostic screen, not for claim-grade validation.
- The screen intentionally overlaps threshold/postprocess territory, so interpretation must state this does not reopen DEC-001/DEC-002 as an architecture route.
- Any best-threshold result must be reported together with deletion, missed true, overmerge, and true-backed rates to avoid selecting a cosmetically high segment-F1 row.

### Required fixes before submit

- None for this bounded screen profile.

### Warnings

- Reviewer independence is `host_self`; acceptable only for bounded non-claim screen.
- Because the primary decode keeps all CE raw fragments, deletion guardrails may pass trivially; the method still must beat CRF-style smoothing on strict segment/boundary metrics before any promotion.
- `max_edge_gap=512` is a fixed graph construction cap, not a tuned gap-merge parameter. If results fail, do not start a gap-grid search.

### Required fixes before submit

- None for this bounded screen profile.

## Code Review Gate: PIPE-TEFM-PURSUE-RETCONSTR-20260630

- Date: 2026-06-30
- Reviewer mode: host static pre-submit review
- Independence: host_self
- Scope: final bounded decoder-only screen for retention-constrained interval objective after selector direction was frozen as triage-only.
- Profile: screen
- Verdict: PASS_WITH_WARNINGS

### Reviewed Files

- `pipelines/PIPE-TEFM-STRUCTDEC-20260630/train_joint_structured_decoders.py` sha256 `c1a862708038b60a8de334c955695fc056c9d86b4761f6bf6edd9745e6b214e0`
- `pipelines/PIPE-TEFM-STRUCTDEC-20260630/run_retention_constrained_decoders.sbatch` sha256 `470e76494c7b37d4e58493958c18412fefa923946d3058bc4f78b5104e64ac37`

### Confirmed OK

- The new loss is a training-time objective attached to GENERanno logits; it is not inference-only post-hoc smoothing.
- The job keeps a CE baseline in the same run, same seed, same human H0 4096 quick data, same strict IoU `0.8` and boundary `5 bp` metrics.
- The internal promotion gate now includes `deleted_true_backed_fraction <= 0.15`, matching the active goal guardrail.
- Output, log, and code-review paths are exp-scoped under `PIPE-TEFM-PURSUE-RETCONSTR-20260630`.
- The sbatch uses the Python 3.10+ `te_benchmark` environment explicitly.
- Initial 80GB-specific submission was rejected by Slurm as unavailable; sbatch was revised to request one idle 24GB `nvidia_geforce_rtx_3090`, consistent with the user's preference to try a smaller GPU first.

### Warnings

- Reviewer independence is `host_self`; acceptable only because this is bounded non-claim screen.
- This is the final decoder-only attempt under the active stop rule. If true-backed deletion remains high, do not start another decoder tweak cycle.
- The raw-evidence veto is a constrained structured-decode mechanism intended to protect candidate TE islands; it must not be reinterpreted as a broad threshold/gap tuning result.

### Required fixes before submit

- None for this bounded screen profile.

## Code Review Gate: PIPE-TEFM-PURSUE-INTERVALSURV-20260630

- Date: 2026-06-30
- Reviewer mode: host static pre-submit review
- Independence: host_self
- Scope: bounded single-seed GENERanno 4096 interval-level true-retention / fragment-survival objective and segment-aware rescue decoder.
- Profile: screen
- Verdict: PASS_WITH_WARNINGS

### Reviewed Files

- `pipelines/PIPE-TEFM-STRUCTDEC-20260630/train_joint_structured_decoders.py` sha256 `c3763486745809f872bb78d7fa403fb61ab11f9a59170428726340bd17a6962e`
- `pipelines/PIPE-TEFM-STRUCTDEC-20260630/run_interval_survival_decoders.sbatch` sha256 `34fcb6c4c6602d6269b6d1cda24a3ff66af41de5a590fdb55e380bc6b0307d9f`

### Confirmed OK

- The new interval-survival objective is computed during training from model logits and true TE intervals, so it is not an inference-only post-hoc HMM/CRF smoothing route.
- The bounded variant set keeps a CE baseline in the same job and compares it with `interval_survival_raw` and `interval_survival_decoder`.
- Strict metrics remain IoU `0.8` and boundary `5 bp`, with `missed_true_rate`, `pred_true_backed_rate`, `short_true_backed_rate`, and deleted true-backed versus false-fragment diagnostics preserved.
- The sbatch writes to independent `PIPE-TEFM-PURSUE-INTERVALSURV-20260630` report/output/log directories and uses `/home/users/j/jwang/.conda/envs/te_benchmark/bin/python`.
- Single seed is fixed at `42`; this is a bounded publication-support screen and cannot support a SOTA claim.

### Warnings

- Reviewer independence is `host_self`; acceptable for screen, not for claim-grade training.
- The rescue decoder has fixed evidence-preservation parameters and is not a threshold/gap/post-hoc tuning matrix.
- If segment/boundary improve but missed_true_rate remains above CE + 0.03, this direction must be recorded as requiring stronger true-retention constraints rather than scaled.

### Required fixes before submit

- None for this bounded screen profile.
## Code Review Gate: PIPE-TEFM-CAP-FRAGARCH-20260701

- Date: 2026-07-01
- Reviewer mode: host static pre-submit review; post-run reference-row bugfix re-review
- Independence: host_self
- Scope: bounded capability-pursue screen for interval-aware TE fragmentation architecture.
- Profile: screen
- Verdict: PASS_WITH_WARNINGS

### Reviewed Files

- `pipelines/PIPE-TEFM-CAP-FRAGARCH-20260701/train_interval_architectures.py` sha256 `a6b968cfb99c667c82b05f599b1f2a7e7fde3885b471dcc542a2ade248c20412`
- `pipelines/PIPE-TEFM-CAP-FRAGARCH-20260701/run_interval_arch_screen.sbatch` sha256 `528673f6f0124e3e3797d3cd25799cb0e4e568084808ee7614cfa0640e499b8a`
- `pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py` sha256 `ce9d5dbb1dd2da5db76440c0396a1883a71790576f9b42f83278c7e1b423ca6a`
- `pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py` sha256 `1ed72d5a79420d8f5820f9969912c335c28821418a443258923c1cbbf273c72a`

### Confirmed OK

- The screen tests two genuinely new interval architectures: `boundary_proposal` with start/end heads and learned interval proposal scoring, and `anchor_free_interval` with center/length interval detection.
- The promoted GENERanno 4096 token classifier is loaded as a frozen feature/logit source; only lightweight interval heads are trained.
- The evaluator reuses existing strict segment functions and records segment-F1 at IoU `0.5/0.7/0.8/0.9`, boundary-F1 at `5/10/25 bp`, missed_true_rate, pred_true_backed_rate, short_true_backed_rate, deleted true-backed vs false fragments, overmerge rate, split_true_rate, and mean fragments per true TE.
- CE raw, HMM-style penalty2, and CRF-style penalty4 are recomputed in the same panel; historical survival/retention rows are explicitly marked `same_panel_comparable=False`.
- Output paths are exp-scoped under `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/` and do not overwrite prior structured-decoder results.

### Warnings

- Reviewer independence is `host_self`; acceptable for bounded non-claim screen, not for claim-grade validation.
- `overlap center-merge` is not fabricated on the non-overlap quick panel. It is explicitly deferred to Stage-2 if a new interval architecture passes the first screen.
- The old `TFSUPP_generanno_H0_w4096_seed42` checkpoint gate is waived only for read-only checkpoint loading; it is not a waiver for the new experiment.
- A post-run bug in historical reference parsing was fixed: prior rows now require `variant == interval_survival_decoder` or `retention_constrained_decoder`; same-panel new-architecture metrics were unaffected.

### Required fixes before submit

- None for this bounded screen profile.
# Code Review Gate: denovo_b_animal_eval_dfam_repeatscout_chunked_rescue_20260702

- Date: 2026-07-02
- Reviewer mode: host_self
- Scope: chunked rescue for Dfam-augmented RepeatScout RepeatMasker rows that cannot finish as whole-genome jobs within the public-cpu walltime.
- Verdict: PASS_WITH_WARNINGS

## Blockers

- None.

## Warnings

- `opossum` has one 748 Mb FASTA-record chunk because the rescue preserves original sequence coordinates and avoids intra-record coordinate offset rewriting. If this chunk hits the 4-day partition limit, it needs a second-stage offset-aware split.

## Confirmed OK

- The run sbatch writes only per-chunk `repeatmasker_chunks/chunk*/` outputs during array execution.
- The standard row-level outputs expected by downstream comparison (`annotation.gff3`, `annotation.bed`, `library.fasta`, `DONE`) are written only by the finalize job after all chunks have `DONE` and non-empty `.out.gff`.
- The final output path remains the existing Dfam row path under `dfam_augmented/<species>/repeatscout`, so existing monitor and UCSC comparison scripts do not need path changes.

# Code Review Gate: denovo_b_animal_eval_dfam_repeatscout_chunked_finalize_20260702

- Date: 2026-07-02
- Reviewer mode: host_self
- Scope: finalize chunked rescue rows for cattle/opossum/pig repeatscout_plus_dfam and refresh monitor state.
- Verdict: PASS_WITH_WARNINGS

## Blockers

- None.

## Warnings

- This is a rescue path for benchmark annotation generation, not a claim-bearing model run. It still writes result artifacts, so the machine gate records reviewed script hashes.

## Confirmed OK

- Finalize fails closed if any chunk is missing `DONE` or a non-empty `.out.gff`.
- Finalize concatenates GFF, emits BED with 0-based starts, copies the combined library to `library.fasta`, writes success `status.json`, and removes stale `FAILED` if present.
- `refresh_denovo_monitor.py` runs after finalize so the Dfam matrix reflects the rescued rows before queued compare jobs start.

# Code Review Gate: BENCH-5TOOL-SMOKE-20260811-R1

- Date: 2026-08-11
- Reviewer mode: external Claude CLI, fresh read-only process
- Independence: external_cli
- Scope: exact identity/help/minimum-input/canonical-adapter CPU smoke for the five-workflow denominator
- Final verdict: PASS_WITH_WARNINGS

## Review history

1. Separate Codex review was `BLOCKED` because its local `bwrap` sandbox could not create a namespace (`No space left on device`); it read no target file and was not used as code evidence.
2. External read-only review found no blocker but warned about version regex, contract schema and sbatch failure state. The author fixed these and invalidated the first hashes.
3. Second external review blocked CPU-only routing uncertainty, version-command fallback, timeout and adapter/verdict edge cases. `srun --test-only` proved the 0-GRES job schedulable on gpu035; code was repaired.
4. Final fresh external review read the latest files and returned `PASS_WITH_WARNINGS`; all earlier blockers were closed.

## Blockers

- None open.

## Warnings

- RepeatMasker help is the last version fallback; exact numeric matching plus immutable SIF SHA limits false acceptance, but a future claim-grade gate should prefer a dedicated version API.
- CPU-only smoke runs on `private-teodoro-gpu` without GRES. Slurm test-only job `11518365` proved it schedulable on gpu035 on 2026-08-11; policy changes would require re-running the test.
- Earl Grey dossier/repo slug contains `7.3.1`, while the frozen SIF target remains 7.3.0. The dossier body explicitly records the frozen 7.3.0 identity; no result-time upgrade is permitted.

## Evaluator-contract evidence

- `route_primary_metric`: `run_smoke.py` writes `engineering_pass_cells / 5.0`; higher means more exact workflows passed, and it is route-local only.
- Coordinates: `adapter.py` converts GFF start-1/end, passes BED half-open coordinates, and converts RepeatMasker query begin-1/end; invalid intervals raise.
- Split/leakage: no fitted model, threshold or biological split; `PASS_NOT_APPLICABLE` is written with hashed official fixtures and no output-driven version changes.
- Schema: `exp_id`, `profile`, finite `primary_metric`, `metrics`, `dataset`, `evaluator`, `semantic_success` and `claim_eligible=false` are all emitted.
- Fail closed: identity/hash failure, version mismatch, predeclared database blocker, min-input failure and invalid run remain distinguishable; a complete matrix may be semantically successful without being engineering PASS.

## Confirmed OK

- All code/config/input/runtime paths are experiment-scoped and immutable candidates are verified by SHA-256 before payload execution.
- HiTE has no accepted 3.3.3 SIF and is explicitly typed-blocked; the legacy unpinned 3.0 image is never selected.
- TEtrimmer uses the exact 1.7.4 source archive over a declared 1.7.2 dependency host and cannot silently report the host as 1.7.4.
- Dfam 4.0 gz candidates are recorded but never treated as configured/promoted FamDB partitions.
- The sbatch requests 8 CPU, 64G, 4h and zero GPU, writes unique logs, and traps nonzero exit to FAILED.

## Required fixes before submit

- Initial review had no open code blocker, but debug allocation preflight job `11518384` immediately found an invalid compute-node conda bootstrap path before any research payload ran. The sbatch was changed from nonexistent `/home/users/j/jwang/miniconda3/...` to the live cluster base `/opt/ebsofts/Mamba/23.1.0-4/...`; this invalidates the recorded sbatch hash and requires an independent incremental re-review before submit.
- A narrow sbatch-only reviewer then reported two blockers that are not applicable after cross-file verification: project `$smart-sbatch` explicitly says CPU-only private jobs omit GRES, and Slurm `--test-only` proved this request schedules without a GPU; successful STATUS is written by `run_smoke.py` after all artifacts. Its useful warning was accepted: the sbatch now writes `environment_conda_explicit.txt`. The changed sbatch still requires a final cross-file re-review and new hash.
- Final cross-file external re-review read the repaired sbatch, runner and `$smart-sbatch` CPU fast-path together. Verdict=`PASS_WITH_WARNINGS`, blockers=0. It confirmed zero-GRES private routing, complete RUNNING→COMPLETED/FAILED coverage, corrected Mamba bootstrap and conda manifest. Machine gate sbatch hash was refreshed to `94863b04...`; this is the binding pre-submit review state.
- Debug preflight retry job `11519282` stopped before code execution because `set -u` made the benchmark_core MKL activation hook fail on an unset `MKL_INTERFACE_LAYER`. The sbatch now activates conda under `set -eo pipefail` and enables nounset immediately afterward. This second sbatch repair again invalidates the prior hash and must pass incremental review.
- Incremental review accepted the nounset ordering but, because it scoped itself to the sbatch, did not count the runner's terminal STATUS write. A redundant sbatch-level `COMPLETED` write was added after the Python command; `set -e` guarantees it is unreachable on Python failure. This removes ambiguity for job-watch tooling and requires one final hash refresh.
- Final reviewer subagent found two real fail-closed blockers: `INVALID_RUN` was included in job-level semantic success, and output creation followed conda activation so early activation failure could not write FAILED. The runner now requires `invalid_count==0`; output directory and RUNNING sentinel are created before conda. Both files require final incremental re-review and new binding hashes.
- Final bounded read-only re-review verdict=`PASS`: both fail-closed blockers are closed, runner and sbatch terminal-state behavior is complete, and binding hashes are now `run_smoke.py=cd96f4b9...`, `sbatch=10937ff0...`.
## Code Review Gate: TEFM-NEW-DIRECTIONS asset-gate quartet (2026-08-11)

- Exp IDs: `FRAG-PARENT-LATTICE-SCREEN-20260811-R1`, `SF-HIER-OPENSET-SCREEN-20260811-R1`, `DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1`, `EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1`.
- Reviewer mode: independent read-only Codex subagent; fresh adversarial gate review plus two incremental re-reviews.
- Scope: configs, deterministic asset verifiers, sbatch wrappers, metrics schema, evidence/input/output manifests and exp docs. This review authorizes only short asset-gate reconstruction, not any scientific screen.
- Initial verdict: F/G PASS_WITH_WARNINGS; S/E BLOCKED. Initial blockers were incomplete S/E result schema and stale-success risk when a gate changes.
- Repair 1: all routes now write RUNNING first; evidence/semantic drift becomes `INVALID_RUN` with `semantic_success=false`; config/verifier hashes are input-bound; S/E use boolean claim eligibility and standard metrics/dataset/evaluator fields.
- Repair 2: sbatch traps preserve verifier-written `INVALID_RUN` and only convert missing/RUNNING abnormal exits to FAILED; expected typed-block rc=2 plus exact STATUS maps to wrapper exit 0.
- Final verdict: **PASS for all four source packages**, `blockers_open=0`.
- Remaining scientific blocker: all four asset gates are expected to remain `FOUNDATIONAL_TYPED_BLOCK`; no model/inference/calibration/clustering/biological evaluation is authorized.
- Machine gates: `outputs/<exp_id>/code_review_gate.json`.

### Confirmed OK

- No synthetic T0/code-gate output is represented as a biological scientific result.
- F preserves DEC-001/002 re-entry boundary and refuses scientific execution without A0/A4/A5.
- S refuses family/homology/clade evaluation without frozen production crosswalk/split.
- G refuses fitting/evaluation while all five anchor run records are absent.
- E refuses representation comparison without exact 2,200 bindings, weights and backend pins.
- All output paths are exp-scoped; asset verifiers request 0 GPU.

---

## Code Review Gate: FRAG-EVIDENCE-REGISTRY-20260811-R2

- Date: 2026-08-11
- Reviewer mode: independent read-only Codex subagent with fresh adversarial context
- Independence: `separate_codex`
- Scope: CPU-only H0/truth/comparator asset audit; no fragmentation inference or scientific lattice
- Final verdict: **PASS**

### Review history

1. Initial review was `BLOCKED`: HMM2 was incorrectly called an accepted postprocessor; pure gap merge was presented as the scientific lattice; same-input contig aggregation, state semantics, hash closure and conda runtime were incomplete.
2. The implementation was repaired so HMM2 is historical-only, MERGE is comparator-only, the scientific lattice remains an explicit typed blocker, eight aggregation/leaf probes are frozen, PREVIEW cannot masquerade as a result, and typed-block versus integrity-invalid states have consistent exit semantics.
3. Final delta review added a pre-write `SLURM_JOB_ID` hard gate and a dynamically derived non-degenerate integrity-check count. All reviewed hashes below passed.

### Confirmed OK

- T1 remains positive-only; unlabeled genome space is never a negative class and whole-genome/bp/segment precision or F1 is forbidden without complete T0.
- H0 inventory is deterministic, rejects links/nonregular files and records per-file hashes plus the aggregate pin.
- Config, builder, comparator semantics, sbatch, protocol and evaluator identities are command/input bound; no-git state is explicit.
- Resource request is 1 CPU, 4 GB, 30 minutes and 0 GPU; `benchmark_core` is explicitly activated.

### Remaining scientific blockers

- `ACCEPTED_POSTPROCESSOR_UNFROZEN`
- `SCIENTIFIC_LATTICE_UNIMPLEMENTED`
- Same-input H0 probability tracks for both T1 inputs are absent.
- Whole-genome metrics remain forbidden without a real complete T0.

### Binding reviewed hashes

- `configs/FRAG-EVIDENCE-REGISTRY-20260811-R2.yaml`: `4a0f3247fa24abbadf794e75c481e9c65704537402ea23071b1dccbbdff8ed29`
- `scripts/experiments/FRAG-EVIDENCE-REGISTRY-20260811-R2/build_registry.py`: `23ab0edf94a6a5b7350e49c85fb80d5e9b949aff27fa9a2bd5e985079b72d383`
- `scripts/experiments/FRAG-EVIDENCE-REGISTRY-20260811-R2/frozen_semantics.py`: `eb5ef94311793384e4abe7aac184b62f3e764d8f608fa981475746b4edf42d09`
- `sbatch/FRAG-EVIDENCE-REGISTRY-20260811-R2.sbatch`: `e0560d2d43c41bdafcecd5c9e3bc80fb58cfd1d040f17c4d30eafdc883e22b54`

### Submission authorization

- Allowed: short CPU asset audit through `$smart-sbatch` after Phase 1 passes.
- Forbidden: scientific fragmentation screen, lattice promotion, manuscript claim, full/scale.

---
## Code Review Gate: BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2

- Date: 2026-08-11 CEST.
- Reviewer: independent read-only Codex subagent; multiple full/delta passes after each stable hash revision.
- Final verdict: `PASS` for bounded CPU engineering preparation (`famdb|hite|edta`) and bounded CPU main smoke only.
- Hard exclusions: no Pfam preparation, GPU, full/scale, biological denominator performance or claim.
- Regression evidence: 14/14 behavior-level contract tests, Python AST, JSON and Bash syntax; official EDTA/TEtrimmer CLI semantics; legacy/current FamDB separation; per-cell prerequisite isolation; owner-token lock recovery; output/identity/environment closure; Conda activation with `MKL_INTERFACE_LAYER` unset.
- Final machine gate: `outputs/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/code_review_gate.json`.
- Final reviewed core hashes: config `6d387e243185...`; runner `7a662bc8fbe5...`; FamDB prepare `b14a2076dadc...`; contract tests `5550b24a463f...`; prep sbatch `d996325f6551...`; main sbatch `11212d916b44...`. The machine gate contains the full path-to-hash map.
- Remaining expected typed blocks are scientific/asset state, not open code-review blockers: current `famdb-v2` absent before preparation; Pfam immutable identity absent.

---

## Code Review Gate: SF-DIRECT-BASELINE-SCREEN-20260811-R2

- Date: 2026-08-11 CEST.
- Reviewer: independent read-only Codex subagent with full review and final manifest/route delta reviews.
- Final verdict: `PASS` for the CPU-only DATA materialization, synthetic/schema test and leakage-audit stage.
- Binding scope: exact Dfam-accession homology components, order-level clade holdout, physically separate primary/audit test sets, U/RN/hard-N masks, exact 9,000-row historical rejoin, checkpoint/input hashes and atomic terminal manifests.
- Final reviewed package: config, two frozen contracts, data/task/preflight/CPU/GPU runners, tests and both sbatch files; the full path-to-hash map is in `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/code_review_gate.json`.
- Resource authorization: CPU DATA stage on `private-teodoro-gpu`, 16 CPU/96 GB/12 h, no GRES and therefore 0 GPU.
- Hard sequencing gate: GPU training is not authorized until CPU produces formal `DATA_READY` plus a frozen PASS manifest and both GPU pre-submit checks are rerun. S1 hierarchical/open-set work remains unauthorized until the S0 direct-superfamily result is acceptable and its result-log/validate/tri-review/pivot chain explicitly opens S1.

### Repair-only CSV delta

- Independent verdict: PASS for one CPU DATA retry only. Reviewed changes were the local 2,000,000-character pinned-manifest reader and its real-shape/over-limit tests; hashes are recorded in the refreshed machine gate.
- Evidence: 15/15 tests, real frozen 495×17 manifest with maximum field 1,203,362 characters, SHA-before-parse and global CSV-limit restoration. No scientific, split or metric contract changed.
- Job `11523252` consumed this authorization and ended in a deeper `DFAM_FAMILY_IDENTITY_UNRESOLVED` typed block. This review does not authorize another S run, GPU or S1.

---

## Code Review Gate: SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1 layout repair

- Date: 2026-08-11 CEST.
- Reviewer: independent read-only Codex subagent with fresh adversarial review.
- Final verdict: `PASS`; blockers open: 0.
- Scope: one repair-only CPU identity/provenance retry after failed Job `11523938`; no split, clustering, training, goal revision, GPU or S1.
- The frozen layout enumerates the exact 12 Dfam H5 partitions and identifies partition 3 as the sole legitimate partition without `Lookup/ByName`.
- Runtime may count and skip exact-name lookup only for that frozen structural absence. A present-but-corrupt index, wrong object type, unreadable file or query exception remains a hard `AUDIT_FAILED` error.
- P-state and label-contract-excluded inventories are constructed and conservation-checked before resolution, so the structural skip cannot silently delete candidates.
- Verification: 17/17 tests in `te_benchmark`, Python compile, Bash syntax, JSON parsing and independent live H5 metadata/size/index-layout checks all passed.
- Binding machine gate: `outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/code_review_gate.json`.
- Reviewed hashes: config `7a827c4288c5...`; frozen layout `347888519fda...`; audit code `fad6b175dede...`; tests `da0f52ca24c8...`; sbatch `e435f7ec7e25...`; experiment doc `5b52518fb8e6...`.
- Non-blocking limitation: this audit binds the roughly 600 GiB partition set by rmlib identity, exact filenames/sizes, Dfam/FamDB metadata and index layout rather than full-partition content hashing; the formal report must keep `full_partition_content_hashing_used=false` explicit.

---
# Code Review Gate: BENCH-HITE-ISOLATED-20260811-R1

- Date: 2026-08-11 CEST
- Reviewer: independent read-only Codex subagent
- Verdict: `PASS`; blockers open: 0
- Scope: one CPU-only HiTE 3.3.3 isolated runtime-validity smoke, 4 CPU/48 GiB/1h/0 GPU.
- Reviewed: exact assets and parent timeout evidence, strict identity and direct argv, offline environment, GFF/adapter success, total budget, numeric Slurm guard, RUNNING/failure/canonical publish lifecycle, strict tri-state lock, and permanent STOP after a second timeout.
- Tests: 18/18 behavior tests, Python compile, bash syntax, AST command surface and malformed Slurm-ID injections all passed.
- Hard boundary: no parent pair/five-cell/RM/EarlGrey/EDTA/TEtrimmer/Pfam/GPU run; an existing or newly created `STOP.json` forbids every later HiTE retry.
- Machine gate: `outputs/BENCH-HITE-ISOLATED-20260811-R1/code_review_gate.json`.

---

## Code Review Gate: SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1

- Date: 2026-08-12 CEST.
- Reviewer: independent read-only Codex subagent with fresh adversarial context.
- Final verdict: `PASS`; blockers open: 0.
- Scope: one CPU-only exhaustive metadata recovery over frozen Dfam 3.9 partition 3; 4 CPU/48 GiB/2h/0 GPU. No full 12-partition catalog, homology graph, split, cluster, model, GPU, S0 or S1 is authorized.
- Contract: recover exactly the 279 frozen missing identifiers (6,432,583 occurrences) by case-sensitive `Families` dataset `name` attributes only; preserve `X13_LINE` as a separate ambiguity audit; forbid prefix/case/copy-derived fallback.
- Integrity gates: exact dataset/consensus/model attribute counts `321856/321856/321818`, identifier and occurrence conservation, pinned provenance payload/layout/docs19, positive numeric Slurm ID, owner lock, RUNNING state, atomic payload and terminal manifests.
- Verification: 13/13 synthetic/contract tests, Python compile, Bash syntax, JSON and stable hashes passed. The reviewer did not scan the real partition data.
- `RECOVERY_COMPLETE` only authorizes design/review of a separate full-catalog stage; `homology_split_authorized` remains false. Typed block is a valid negative; integrity/runtime failure is rc2.
- Binding machine gate: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/code_review_gate.json`.
- Non-blocking limitations: the 64 GB H5 is bound by layout, exact size and metadata/count checks rather than a full content hash; externally killed jobs may leave `RUNNING`, which Slurm/ledger must classify rather than treating as a result.

---

## Code Review Gate: SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1

- Date: 2026-08-12 CEST.
- Reviewer: independent read-only Codex subagent; fresh full review after implementation repair.
- Final verdict: `BLOCKED`; blockers open: 3; no Slurm submission authorized.
- Deterministic resource blocker: audited R0 projection `15,878 s / 4 = 3,969.5 s` exceeds the 900 s feasibility ceiling for a 20-minute allocation with 25% headroom, so `PREFLIGHT_FEASIBLE` is mathematically unreachable.
- Code blockers: a completed nonzero child can be masked by another child's timeout and misclassified as rc0 valid-negative; current sampling is proportional by unit but does not guarantee rare path-depth strata.
- Passing evidence: 24/24 synthetic/topology tests, Python compile, Bash syntax, JSON and preview-manifest closure; log directory and common RUNNING cleanup were repaired; path discovery is included in ETA.
- Reviewed hashes: config `16326ce5b807...`; runner `c7354c35caaf...`; tests `b13f7c4ff898...`; sbatch `85a71b6eb202...`; experiment doc `77ebdf3b5e2c...`.
- Machine decision: `outputs/SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1/PRE_SUBMIT_DECISION.json`. It records no throughput measurement and no Slurm job.
- Next boundary: build and freshly review a separate resumable 4-worker formal R0; do not repair/submit this unreachable 20-minute feasibility experiment. R1/R2/GPU/S1 remain forbidden.

---

## Code Review Gate: SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2

- Date: 2026-08-12 CEST.
- Reviewer: independent read-only Codex subagent through fresh full and two delta reviews.
- Final verdict: `PASS_WITH_WARNINGS`; blockers open: 0.
- Scope: exactly one formal CPU-only partition-3 recovery attempt on `private-teodoro-gpu`, 4 CPU/48 GiB/3 h/0 GPU.
- Verification: 25/25 synthetic/static tests, Python compile, Bash syntax, config JSON, all immutable state bundles, deadline-crossing injections, manifest extra/symlink/traversal/self/duplicate/missing injections and full reviewed-file hashes passed.
- Core contract: 35 atomic resumable units; exact 321,856 unique dataset/object paths, 321,856 consensus attributes and 321,818 model attributes; 279 exact-case targets and 6,432,583 occurrence conservation; X13 remains audit-only; no prefix/case/copy fallback.
- Safety: versioned immutable bundles with pointer-last publication; absolute 7,980 s claim and 8,100 s completion cutoffs; source identity rechecked initial/unit/resume/final; nonzero dominates timeout; unreaped children forbid terminal publication.
- Warnings: no 64 GB full-content SHA; BeeGFS speedup remains empirical and rc75 is possible; four-worker equality was exercised through real checkpoint/merge paths with reordered simulated workers rather than a full H5 four-process scan.
- Machine gate: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2/code_review_gate.json`.
- Hard boundary: no automatic retry and no automatic full catalog, homology split, GPU S0 or S1 authorization under any terminal state.

---
### Narrow source-device audit repair delta

- Final reviewer verdict before Job `11526905`: `PASS_WITH_WARNINGS`, blockers open=0, 34/34 tests.
- Reviewed hashes: config `098373330c7066908a24ec02bb863c79caf4f11d3a49b86c702138a42ddca445`; runner `1d3a8b358027148c5e7dba59eb0ad5f9e357394bcdc88e0a7621a191bec9eefa`; tests `f6d4fbfa5817f769287f4a622caf09054e2881e49143e91103f4a3449487b6a0`; sbatch `5375c6e26205b90755fb27cbf597c9686d0056f54bb9658863a961e670d86513`; experiment doc `af1b4654d71eac067924b84646781a623eb07b56e772d8baa5b5c293b99f2499`.
- `st_dev` is audit-only with strict four-field schema; stable source pins remain binding. Missing/forged device audit quarantines the affected unit, while legitimate login/compute device differences do not invalidate checkpoints.
- Authorization was exactly one repair retry with the unchanged 4CPU/48GiB/3h/0GPU profile. That authorization is consumed by Job `11526905`.

---
## 2026-08-12 — SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1

- Verdict: `PASS` after two repair/re-review rounds; independent reviewer backend `codex(separate)`.
- Scope: one bounded Dfam 3.9 curated EMBL authoritative exact-crosswalk audit only.
- Reviewed package: config `5ca60bbb...`, runner `14812569...`, tests `4d2f8f36...`, sbatch `965ca6f8...`, experiment doc `66142b38...`.
- Verified gates: exact case-sensitive `NM/PI/SN/DR`, accession-only `AC/ID`, 279-identifier denominator and occurrence conservation, label/species-blind identity resolution, atomic output closure, formal Slurm-only execution, exact `1 CPU / 2 GiB / 20m / 0 GPU` submission.
- Authorization: one unmodified `sbatch sbatch/SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1.sbatch` submission. No full catalog, homology split, DATA, GPU, or S1 authorization.
## 2026-08-12 — SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-AUDIT-20260812-R1

- Verdict: `PASS`; independent read-only reviewer `codex(separate)`; 19/19 synthetic/behavior tests pass.
- Scope: one target-only Dfam 3.9 all-family support audit. Full-source SHA/MD5/CRC and TOCTOU checks, bounded streaming, exact curated reconciliation, raw-DR support-only semantics, denominator conservation and atomic manifests were reviewed.
- Reviewed package: config `5a9c32e0...`, runner `4531b553...`, tests `6e89ca28...`, sbatch `b303086b...`, experiment doc `2cf6fcaf...`.
- Authorization: one unmodified 1CPU/4GiB/2h/0GPU submission. Full catalog, homology, DATA, GPU, S1 and claim remain unauthorized.
## 2026-08-12 — all-family grammar-repair delta review

- Verdict: `PASS`; old Job `11528157` remains semantically failed and immutable.
- Delta: official PI semicolon-list tokenization, DR semicolon/period terminators, per-tier/per-field grammar telemetry, and tests.
- Reviewed hashes: config `85b7714a...`, runner `0ee726c2...`, tests `62b8f70e...`, sbatch `b303086b...`, doc `37d22b82...`.
- Authorization: one unmodified CPU-only grammar-repair retry; no downstream authorization.

## 2026-08-12 — SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1 first authorization consumed

- Independent verdict before submission: `PASS_WITH_WARNINGS`, blockers open=0; reviewed hashes are recorded in `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/code_review_gate.json`.
- Authorized scope was exactly one unmodified 1CPU/4GiB/20m/0GPU roundtrip smoke. Job `11528744` consumed that authorization and failed in 2 seconds before FamDB/RepeatMasker because the runtime walltime guard depended on a non-portable `SLURM_TIMELIMIT` environment representation.
- The old gate is consumed and must not authorize a retry. Any repair must bind strict scheduler facts, add behavior tests and receive fresh independent review with new hashes.

## 2026-08-12 — SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1 repair authorization consumed

- Fresh repair review was `PASS_WITH_WARNINGS`, blockers open=0, for exact hashes recorded in the replacement machine gate. Authorization covered one unmodified 1CPU/4GiB/20m/0GPU retry only.
- Job `11528885` consumed that authorization. Strict scheduler reconciliation and 37/37 tests passed; the installed FamDB API then failed at `FamDBLeaf.added` before RepeatMasker.
- The gate is now consumed. No third retry is authorized; any component replacement requires a new exp-scoped implementation, fresh code review and post-result pivot authorization.

## 2026-08-12 — FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1

- Independent fresh review plus delta review: `PASS`, blockers open=0; 17/17 tests, Python compile, shell syntax and 15/15 implementation-manifest hashes pass.
- Reviewed scope is strictly one Rice T1 curated-positive, CPU-only information-sufficiency audit. Candidate joins do not use prediction confidence, genomic gap or test-tuned thresholds; fixed seed thresholds only form consensus-coordinate evidence.
- Exact authorization: one unmodified `8 CPU / 32 GiB / 02:00:00 / 0 GPU` submission on `private-teodoro-gpu`. No whole-genome metric, production postprocessor, full-F, GPU or downstream claim is authorized.

## 2026-08-12 — SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1 authorization consumed

- Independent verdict before submission: `PASS_WITH_WARNINGS`, blockers open=0; exact reviewed hashes are stored in `outputs/SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1/code_review_gate.json`.
- Authorized scope was exactly one unmodified 1CPU/4GiB/10m/0GPU leaf exact-access probe. Job `11533175` consumed it and failed after the in-memory probe because read-mode cleanup invoked `FamDB.finalize()` and hit absent `FamDBLeaf.added` before publishing observations.
- The prior gate is consumed. It does not authorize a close-only fix or retry; any continuation requires post-result pivot, a new/updated exp-scoped implementation and fresh independent review.

## 2026-08-12 — SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1 authorization consumed

- Independent final verdict: `PASS_WITH_WARNINGS`, blockers open=0; 59/59 signal/lifecycle/manifest/resource tests, Python compile, Bash syntax and JSON checks passed.
- Reviewed hashes: config `9ad8493196b931b088cc7ba7c046c69acdd9b804afc9a74abec9492c264eaa84`; runner `f9534f53a9b664fead9bc489b88aa8d7438188c46a8fe1c1a0e064ac5ea7810b`; tests `61bf111b20bf4e69a991d59b9e768ba981385d28b1e3da0daddffa8ac60e5f5b`; sbatch `8093f2636a598f3d275a4b90df8e4c20a01c8e1b363ca2759b969763c5c8898d`; experiment doc `54b2fe83638d288effedfafd39ff98cebe9bce7e035e8f611d694e3c84ade554`.
- Scope was exactly one unmodified 1CPU/4GiB/10m/0GPU close-only probe. Job `11534847` consumed the gate and returned `LEAF_CLOSE_ONLY_PASS`.
- Warnings retained: `/usr/bin/timeout` was not content-hash pinned; parent-directory fsync is not explicit; owner-lock creation has a narrow fail-closed stale-lock window.
- This consumed gate authorizes no repeat and no adapter/RepeatMasker/catalog/homology/DATA/GPU/S1 work.

## 2026-08-12 — SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1

- Independent verdict: `PASS_WITH_WARNINGS`, blockers open=0, after two blocker-repair rounds; 29/29 synthetic/behavior tests, Python compile, Bash syntax, config JSON and preview closure pass.
- Reviewed hashes: config `b94f94c5c22b5785ea87a92e457c6af84805334c3daff8f007b494b8d196856f`; runner `83b4b8e76e4dc481a055fe781b6551860c579e5866944d59348d854321737486`; tests `4eea37a507d015644ca8fca79dbe94c30b589b8b73b715e39133607670cd02a3`; sbatch `65bcd9b2efbdf4a989bd5ddde08dbb3e7825ca6f51c8d9257b0498379b68b20d`; experiment doc `a98026c47d5c93a9e2a80032ffca76724ac7a2ece41d527f21438c080f0dca61`.
- Closed blockers: complete bundle revalidation immediately before pointer switch; state/bundle/entry no-symlink and containment; wrapper preserves an existing specific terminal; full formal PASS/typed control-flow scope fixed and tested.
- Warnings: `/usr/bin/timeout` not content-hash pinned; no explicit parent-directory fsync; narrow fail-closed stale owner-lock possibility.
- Exact authorization: one unmodified 1CPU/4GiB/10m/0GPU submission of `sbatch/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1.sbatch`. No RepeatMasker, representative/full annotation, catalog, homology, DATA, training, GPU direct S0, S1 or claim.
