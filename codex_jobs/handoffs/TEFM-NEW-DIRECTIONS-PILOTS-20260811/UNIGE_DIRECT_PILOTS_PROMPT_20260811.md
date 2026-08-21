在 `/home/users/j/jwang/ab-initio-TE` 自主推进 `TEFM-NEW-DIRECTIONS-PILOTS-20260811`。不等待、下载或复刻 ChatGPT Pro 的新代码包；基于远端现有源码、资产和历史证据独立设计、实现并运行新的 bounded pilots。先读 `codex_jobs/handoffs/UNIGE-PRO-INTAKE-20260811-R1/unpacked/UNIGE_BOOTSTRAP_PROTOCOL_20260811.md`，再读 `codex_jobs/handoffs/TEFM-NEW-DIRECTIONS-PILOTS-20260811/UNIGE_DIRECT_PILOTS_PROTOCOL_20260811.md`。

## 用户明确授权

本指令是对首批 bounded smoke/screen cohort 的一次性人工确认：允许自主补齐研究流合同、实现代码、通过 smart-sbatch 提交并等待结果；不需要因普通实现选择再次询问。授权不包括单个作业超过 12 小时、累计新增计算超过 24 GPU-hours、full/scale、多数据库迁移、部署、Git 提交/推送或论文主张。

## 硬性流程

1. 读取 `AGENTS.md`、`CLAUDE.md`、`ACTIVE_GOAL.json`、`docs/02/03/05/06/09/10/11/19/20`、`cluster_config.yaml` 和相关 skills。
2. 运行 `research_flow_guard.py`。若失败，不得跳过：自主执行其 Stage-A `recommended_next`，用官方来源核实五工具版本并通过 `sota-inventory → grill/council → configure-project → benchmark-roadmap` 补齐最小合同；保留旧文档，采用 additive dated patch。
3. 每条路线严格执行 `implement → code-review-gate → check_data/leakage gate → smart-sbatch Phase 1/2 → job reconciliation → result-log → validate/tri-review/pivot`。任何 code-review `BLOCKED`、数据泄漏、路径冲突或 Phase 1 Fail 都不得提交。
4. 登录节点不得运行研究计算。所有代码、工具、统计、图形、训练和推理均由 smart-sbatch/srun 分配的计算节点执行。每个 exp_id 使用独立代码、配置、日志、输出、checkpoint 和 metrics 路径。

## 执行顺序

1. `BENCH-5TOOL-SMOKE-20260811-R1`：冻结并验证 RepeatModeler2+RepeatMasker、EDTA、Earl Grey、HiTE、TEtrimmer 的实际版本、依赖、数据库、离线启动、最小输入和输出 adapter；版本冲突必须 fail closed，不得事后替换。
2. `FRAG-PARENT-LATTICE-SCREEN-20260811-R1`：实现 preservation-constrained parent-aware interval lattice。原始阳性片段不可删除；只允许有证据的父级 join；报告 fragment retention、parent recovery、false fusion、nested handling、segment/boundary 指标，并与 raw、CENTER70、strict/loose merge 及现有 postprocess 比较。
3. `SF-HIER-OPENSET-SCREEN-20260811-R1`：在现有冻结 snapshot 上实现 hierarchical open-set superfamily 预测，输出最深受支持节点或 abstain；采用 family/homology-blocked 与 clade-held-out 划分，报告 risk-coverage、unknown recall、false-unknown rate、hierarchical distance 和 main-class conditional macro-F1。
4. 仅当资产门禁通过才运行 `DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1`：若历史 run provenance 缺失则 clean rebuild；评估 fixed-anchor transfer surface、top-k regret、LOCO/clade holdout 和 abstention，不拟合“万能标量公式”。
5. 仅当 2,200 片段的 family/copy/species 绑定和模型权重被冻结才运行 `EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1`：同一 split/投影/聚类预算比较 pretrained embedding、k-mer、MinHash、alignment、length/GC、random Gaussian 和 untrained network；禁止以 UMAP 图作为结论。

## 完成标准

- 至少完成 Stage-A 合同修复和五工具 smoke；在门禁允许时完成 F、S 两个主 pilot，G/E 可 typed-block。
- 每个已提交作业提供 job ID、脚本/输入/环境 SHA-256、终态、资源使用、metrics、独立验证和 claim eligibility。
- smoke/screen 永不宣称可发表、SOTA 或真实生产验证；失败结果和被否路线必须保留。
- 最终产出 cohort 总结、结果矩阵、下一轮 promotion/stop 决策和所有证据路径。

