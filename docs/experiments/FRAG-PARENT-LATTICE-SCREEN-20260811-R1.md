---
exp_id: FRAG-PARENT-LATTICE-SCREEN-20260811-R1
date: 2026-08-11
approach_family: parent-aware-interval-lattice
parent_exp: PIPE-TEFM-CAP-FRAGGRAPH-20260701
motivated_by: "new-mechanism re-entry under immutable-leaf and typed-parent constraints"
track: A
profile: smoke
status: parked
primary_metric: asset_gate_pass
value: 0.0
vs_anchor: "FOUNDATIONAL_TYPED_BLOCK"
one_liner: "A0/A4/A5 未闭合；不可启动 biological parent-lattice screen"
---

# FRAG-PARENT-LATTICE-SCREEN-20260811-R1

- 路线：F，parent-aware fragment lattice。
- 实际动作：计算节点上的只读资产闸门审计；未运行科学 screen。
- Asset-gate allocation：短 `srun` Job `11519717`，`COMPLETED 0:0`，1 CPU/1 GB、0 GPU、实际 1 秒。
- 终态：`FOUNDATIONAL_TYPED_BLOCK`。
- claim eligibility：否。

## 判定

当前只能复用 synthetic T0 做机制/评估器语义验证，不能在生物数据上做可解释为 scientific screen 的比较。A2 synthetic T0 与 A3 golden evaluator 已通过；A0、A4、A5 和 A6 明确阻塞。

类型化阻塞：

1. `F_A0_H0_PIN`：`h0_checkpoint` 目录摘要未被独立冻结。观察摘要为 `4942f175bd9a96f8235f0dfaab917ce5b1e8024a5f16f1019b736a0c8dea35a2`。
2. `F_A4_NO_REAL_T0_OR_TIERED_INPUT_REGISTRY`：real-T0 registry 为空；T1 FlyBase / Rice 仅为 partial positive truth，未形成同输入的 tiered input/truth registry，不能报告全基因组 precision。
3. `F_A5_CENTER70_MERGE_STRICT_MERGE_LOOSE_AND_ACCEPTED_POSTPROCESS_UNFROZEN`：`CENTER70`、`MERGE_STRICT`、`MERGE_LOOSE` 均未通过冻结；历史 accepted postprocessor 又存在 HMM2 threshold 0.35 与较新的 CRF4 口径歧义，禁止静默选择。

Truth tier 盘点：

- T0（complete）：只有 synthetic truth，可用于语义验证。表位于 `software_outputs/scientific_evidence/PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3/run_11475540/payload/stages/A2/`，包括 `truth_elements.tsv`、`truth_body_segments.tsv`、`raw_fragments.tsv`、`centre70_fragments.tsv`；production real T0 不存在。
- T1（partial positive truth）：FlyBase 在 `data/raw/benchmark_v1/flybase/FB2026_02/dmel_r6.68/derived/curated_positive_truth_v1/`；Rice 在 `data/raw/benchmark_v1/rice/derived/edta_v230_positive_segments_v1/`。二者不能推出 whole-genome precision，且尚未绑定到 F 的同输入 comparator registry。
- T2：没有发现已冻结、可被本路线消费的同输入 T2 registry。

Comparator 可重建边界：RAW 已绑定 `pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py`（threshold 0.5）；HMM2/CRF4 可追到 strict evaluator 与 `pipelines/PIPE-TEFM-SEG-SF-20260618/bp_overlap_segment_eval.py`。但 CENTER70 只有 `relative_start=615`、`relative_end=3481` 参数而缺源码绑定；MERGE_STRICT/MERGE_LOOSE 的参数、semantic probe 与源码绑定不完整。因此当前不存在同一冻结 biological input 上的 RAW/CENTER70/MERGE_STRICT/MERGE_LOOSE/accepted-postprocessor 完整输出矩阵。

## 冻结证据入口

- A0：`software_outputs/scientific_evidence/PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3/run_11475540/payload/stages/A0/A0_identity_lock_report.json`
- A2：`software_outputs/scientific_evidence/PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3/run_11475540/payload/stages/A2/A2_validation_report.json`
- A3：`software_outputs/scientific_evidence/PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3/run_11475540/payload/stages/A3/A3_golden_report.json`
- A4：`software_outputs/scientific_evidence/PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3/run_11475540/payload/stages/A4/A4_real_t0_report.json`
- A5：`software_outputs/scientific_evidence/PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3/run_11475540/payload/stages/A5/A5_comparator_report.json`
- A6：`software_outputs/scientific_evidence/PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3/run_11475540/payload/stages/A6/A6_readiness_seal.json`

所有输入 SHA-256 见 `outputs/FRAG-PARENT-LATTICE-SCREEN-20260811-R1/input_manifest.tsv`。

## 可重现入口与边界

`scripts/experiments/FRAG-PARENT-LATTICE-SCREEN-20260811-R1/verify_asset_gate.py` 只校验输入哈希与上述语义字段，并重建有限 `metrics.json`、manifests、报告及 `STATUS`。仅在完整复现当前阻塞时返回 code 2；证据缺失或状态漂移会写 `INVALID_RUN`、`semantic_success=false` 并返回 code 3。

解锁科学 screen 至少需要：独立冻结 H0 checkpoint 目录摘要；建立带 T0/T1/T2 tier 与 claim boundary 的冻结同输入 registry；冻结 RAW/CENTER70/MERGE_STRICT/MERGE_LOOSE/accepted postprocessor 的源码、参数、输出模式和 semantic probes；重新生成 PASS A6 seal，并另行完成代码审与明确执行授权。

Cohort closeout：3/3 tri-review 保持本路线 asset-gated；pivot 先闭合 B denominator，F registry 作为 reviewer-proposed 正交后续，不在本 cohort 继续执行。
