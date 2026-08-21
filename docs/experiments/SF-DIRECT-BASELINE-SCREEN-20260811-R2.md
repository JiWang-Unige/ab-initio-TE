# SF-DIRECT-BASELINE-SCREEN-20260811-R2

## 2026-08-11 repair-only CPU DATA retry

- Job `11523252`, 16 CPU/96 GiB/0 GPU, about 21 minutes; code review, two machine gates, preflight, `sbatch --test-only`, 15/15 tests and the bounded wide-TSV repair all passed.
- Terminal state: `DATA_TYPED_BLOCK`; canonical output manifest verifies; no `DATA_PASS_MANIFEST.json`, data promotion, leakage audit, training, inference or scientific metric exists.
- Blocker: canonical P-state RepeatMasker family names are not all one-to-one resolvable to Dfam 3.9 accession/consensus (`DFAM_FAMILY_IDENTITY_UNRESOLVED`, including custom `DR...` and generic/ambiguous names).
- Interpretation: direct-superfamily accuracy remains unmeasured. The next identity-layer repair must preserve unresolved positives and prevent homology leakage; random/chromosome fallback and silent record deletion remain forbidden. GPU S0 and S1 are not authorized.
- Result-chain closeout: 3/3 external CLI tri-review judged this a valid comparability block. Pivot selected a bounded source-library/consensus provenance audit before another DATA run. The audit may test exact name and accession resolution, but it may not silently redefine homology components; a sequence-cluster replacement requires the project human gate before changing the S contract.

## 目的与边界

S0 仅回答：在严格 Dfam-accession component / order-clade-held-out 合同下，直接 `BG/SINE/LINE/LTR/DNA/Unknown` 注释是否达到预注册数值门。即使 S0 通过，本 runner 也只输出 `s0_numeric_gate_pass`；`hierarchical_stage_authorized=false`，S1 必须由后续独立流程授权。本实验是 single-seed screen，永不 claim。

主 baseline 从冻结的 `GENERanno-eukaryote-0.5b-base` 初始化，仅用新 train/validation clean retrain。历史 SF5 head 可能见过新 test family，因此只能作为 `CONTINUITY_COMPARATOR_ONLY`；它不参与初始化、checkpoint/temperature 选择或 S0 gate。

## 数据、标签和 split

- 数据源为 `PRE-S0-CANONICAL-20260810-R2` 的 canonical genome、self-label RepeatMasker `.out.gz` 和 comparator-plus-unknown；runner 核对 actual ready alias 指向 frozen target，并逐目标验证 provenance SHA-256。
- 每个 P-state `RepeatMasker repeat_name` 必须通过 pinned FamDB 2.0.0 API exact resolve 到 Dfam 3.9 versioned accession，且必须有 consensus；`homology_component` 使用该 accession identity，并冻结 consensus SHA-256。这里不虚构新的 sequence cluster，而是使用协议允许的官方 Dfam family identity。任一 missing/ambiguous identity 都使 DATA stage `DATA_TYPED_BLOCK`。
- 出现在任一 held-out clade 的 Dfam component 全局冻结到 test；其余 fit-only component 按 accession 的预注册 salted hash 分 train/val。禁止 random/chromosome fallback。family 或 homology-component label conflict 均 typed-block。
- 高阶 clade 冻结为 NCBI order taxid：fit 为 Primates/Rodentia/Cypriniformes/Galliformes/Anura/Diptera/Rhabditida；primary 为 Artiodactyla/Perissodactyla/Hymenoptera/Coleoptera，零重叠。species→order ancestor/name 逐项由 SHA-256 固定的 Dfam 3.9 root FamDB（内嵌 NCBI taxonomy）验证。optional stress 物理隔离且永不进入 numeric gate。
- 多 component 窗口只有全部 Dfam components 属于同一 split 且与 clade role 一致才保留；cross-split mixed、role/split mismatch、short 和 excess-N 窗口剔除并审计。
- 单一 painter `P > hardN > U > RN` 同时产生训练 label、状态 mask 和 coverage。`U=-100`，不当 BG 训练/评分；hardN/RN 是 BG guardrail。coverage 分母包含所有 deterministic primary candidate 的 main4 P bp（含 mixed/mismatch/short/N exclusion），分子只含实际写入 `test_primary` 的 main4 P bp。
- 历史 5,400/1,440/2,160（总 9,000）窗口按 `(species_code, chr, start, end, sha256(sequence))` 唯一 exact rejoin；长度、labels、坐标、每 split count、duplicate/missing 任一失败均 fail closed。

## 训练、评估与原子执行

- CPU stage（0 GPU）：在 `te_benchmark` 中验证 checkpoint/历史数据/canonical/RM 4.2.2/Dfam 3.9/ontology/official taxonomy/Dfam family identity，构建四个物理 partition，运行 tests + leakage verifier，原子 promotion 后生成 DATA PASS。
- GPU stage（1 GPU）：只消费与当前 config/package hash 完全一致且 `homology_component_overlap_count=primary_clade_overlap_count=0` 的 frozen PASS；重新 SHA-256 全部实际消费的 base/historical weights、tokenizer、config 和 remote code。先做 4096-bp full backward smoke，再 clean train、val-only selection，并分别评估 primary/audit 与 clean/historical。
- 主报预注册的 `minimum_clade_main4_macro_f1`、per-clade support 和 `homology_component_overlap_count`；per-species/family 仅作 secondary。audit 永不参与 gate。
- attempt 内 `PAYLOAD_MANIFEST.json` 无自引用地覆盖 metrics/report/RUN manifest/training metadata/calibration/model/env；生成后验证，目录原子 rename 后再验证，最后原子发布并校验 top-level manifest。已有 staging/final、stale quarantine 冲突或 owner lock 均拒绝继续。

## 文件、提交前合同与状态

- Config：`configs/SF-DIRECT-BASELINE-SCREEN-20260811-R2.yaml`
- CPU data/rejoin/leakage：`direct_s0_data.py`、`run_cpu_data_stage.py`
- GPU train/eval/aggregate：`direct_s0_task.py`、`run_direct_screen.py`
- Submission preflight：`preflight_sbatch.py` 必须在 `sbatch` 前创建/检查 log dir 并拒绝已有 owner lock；CPU/GPU job 竞争同一个原子 `.stage_owner.lock`，避免并发竞态。
- Jobs：`.data.sbatch` 为 16 CPU/96 GiB/12h/0 GPU；`.sbatch` 为 1 GPU/8 CPU/64 GiB/12h。两者先 `set -eo`，conda activate 后才 `set -u`。

最终 package 通过独立 `$code-review-gate`，仅授权 CPU DATA stage。Job `11522718` 已提交，但在数据物化前失败；没有训练、推理、DATA PASS 或 S1。

## 资源估计

CPU canonical scan、Dfam identity resolution、hash 与 exact-rejoin 预计 3–6h、0 GPU；GPU smoke + clean 0.5B/4096-bp 训练 + 四次推理预计 6–10h、最多 12 GPU-hours。两个 job 各自 12h 上限。

## CPU DATA 结果：FAILED_RUN

- Job `11522718`，`private-teodoro-gpu`，16 CPU/96 GiB/12h 上限、0 GPU。
- `test_direct_s0.py` 先执行并通过；随后 `direct_s0_data.py build` 在读取冻结的 `chunk_manifest.tsv` 时触发 `_csv.Error: field larger than field limit (131072)`。
- 失败发生在 family/Dfam identity物化、split生成、leakage verifier 和任何训练之前。终态为 `DATA_FAILED`，`semantic_success=false`，`scientific_screen_executed=0`，`hierarchical_stage_authorized=false`。
- canonical output manifest 对失败态闭合；`validate_goal.py` 确定性返回 `failed_run`。
- 下一步不是 GPU 或 S1。必须在 reader 中显式设置有界 `csv.field_size_limit`，添加大字段 regression fixture，重新独立审查后才能申请一次 CPU DATA retry。
