# 论文最终梳理：送审证据导航

2026-09-14，Europe/Zurich。用户要求：使用 Git 保存最新进展，在内置浏览器用 ChatGPT Pro 系统梳理所有研究结果，形成完整论文，并判断正文/补充材料安排及必要补实验。本文是本轮取证导航和待审判断，不是独立实验、论文 claim 批准或新训练授权。

## 证据层次与当前状态

- 本轮读取本地当前源码、协议、归档表格及 JSON；没有重跑模型或评分，没有读取封存科学面板。
- 远程使用实际主机 `login1.baobab.hpc.unige.ch` 只读核查 Slurm 和指定日志。远端 HEAD 为 `77b639c`，已在本地 `3891293` 的祖先历史内；远端有同步的未提交文件，不能用较旧远端 Git HEAD 代替真实工作树状态。
- `squeue -u jwang` 本轮无作业行。12520644、12522308 与 12664906 的相关子作业均 COMPLETED 0:0。Label-A 原始 12522308 的部分产物曾因 Matrix 错误无效，不能因 exit 0 恢复有效性；可用修复及 CB4 产物见 PANEL-METADATA。
- **新的实时发现：12652888（P3-Tiberius base-mask smoke）FAILED 1:0，21m58s。** U 臂日志明确 `KeyError: 'BASE_MASK_OBSERVATION'`，出自 `observed_tiberius.py:12`。目录只有 smoke-r1，没有完整 20 core × 3 arm 结果；status.json 仍是 `PREPARED_NO_MODEL_OUTPUTS`，但 P3 输出与 U/P/R FASTA 已存在，故该中间状态不能描述整个作业的终态。记录文件见本目录下 `MANUSCRIPT-LIVE-STATUS-20260914.md`。
- 这是工程失败，不是 P-U 科学阴性；尚不能写基因注释改善，也不能据此否定效用。旧 C 的 27 单元已完成科学阴性是另一问题，须单独保留。
- 本轮没有查到已完成的 hg19→hg38→hs1 历史预测再证实实验。现有 human assembly 标签来源一致性与路线提案不能代替时间外验证。送审时请继续全树查找，若未找到保持“未找到可核实证据”，不要写“实验失败”。

## 十个问题及核查入口

### 1. 不同 GLM 基座比较是否完备，能否正文

已有早期 DNABERT2/GENERanno/HyenaDNA/NTv2 screen，以及 NTv2/NTv3 model-size × window 后续。FINAL `matrix_eval.tsv` 本轮直接计数 **495 行**；EBAR 比较 NTv2-250M/4096 与 NTv3-100M/2048，分别有 18 animal 与 15 plant chromosome/species 行。

关键入口：

- `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/window_sweep_current.tsv`
- `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`
- `reports/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/summaries/eval_panel_summary.tsv`
- `docs/06_results_log.md` 的 FINAL/EBAR 两节。
- `docs/experiments/REPOSITORY-SYSTEM-REVIEW-20260906.md`：实际训练呈现量、前 1200 窗口评价范围等不完全匹配，因此旧矩阵不能作纯 backbone/context 因果比较。NTv2-500M 旧 Unknown→0 口径差异需保留。20260906 修复不能自动使旧数值全部更新。

可审判断：足够展示探索性 recipe 比较与设计选择，是否作为正文主结果取决于论文主张；尚不能宣称严格公平的最终全模型排名。不能把 chromosome repeat 当 training seed repeat。

### 2. 同 GLM 不同窗口

早期 512/1024/2048/4096/8192 窗口及 edge bins 有数值；GENERanno 4096 为 .94303，NTv2-500M 4096 为 .94578、8192 为 .93957，均属于该早期 screen。不同表不能混为同一实验分母。

建议审阅主文保留为何选窗口/edge mitigation 的关键一图，完整矩阵和 edge 曲线放补充。真正隔离信息交换的 PAIR8/BLOCK4 是另一后续消融，不能用早期窗口 sweep 代替。

### 3. 物种通用模型、MoE、线虫接近 .8

`CROSS-SPECIES-L1-CLOSURE-20260908.md` 明确 **L1 NOT_COMPLETED**。共享六物种模型和无标签 FASTA 工程入口已实现，不等于外部通用模型完成。源码/配置搜索未找到已执行 MoE 结果；协议仍 NO MOE/conditional。

最新 PAIR8 seed42：worm SCREEN .812998、DEV .794154；BLOCK4 .809500/.795764；冻结 D .802736/.797565；PAIR8 macro DEV .892187。预注册 worm .8 与配对增益门未过，seed17 未释放。接近 .8 可以如实报告，并不允许事后改写已冻结 PASS。更广历史 panel 中还存在 beetle、plants 等低分，不能把六物种内部 DEV 说成所有物种仅 worm 较差。

入口：`CROSS-SPECIES-L1-PAIR-CONTEXT-V1.md`、`reports/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/seed42-decision.json`、`CROSS-SPECIES-L1-RELEASE-READINESS-20260905.md`、`CROSS-SPECIES-L1-FULL-PROTOCOL-DRAFT-20260908.md`、`CROSS-SPECIES-L1-PANEL-METADATA-20260908.md`。

### 4. 能否由基因组特征推断泛化性能或置信度

历史 deployed-feature selector in-sample R2 .8203，但 leave-species-out RMSE .3040；标签来源变量改善解释但不能供新基因组部署。后续 top2+local probe 在内部 leave-species contains-best .8636、regret .0071，leave-clade best .6364，需要 abstain。20260811 新 transfer surface 因 5/5 anchor provenance 缺失未执行，不能记为性能失败。

入口：`docs/10_findings.md`、`reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/`、`DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1.md`。

审阅须区分：物种平均 F1 预测、模型选择、逐 bp probability calibration、OOD 风险提示。这些不是同一个“置信度”。既有失败不证明基因组内生特征在原则上毫无信息。

### 5. hg19→hg38→hs1 后来确认的 TE

当前已核实的是版本间标签来源一致性，不是前瞻发现。请检索所有相关代码/报告；没有坐标级候选与冻结历史数据就不得构造结果。

若作为候选新子论点，最小设计需先界定 old/new assembly 的同源可比区域、旧组装不存在的新序列、liftOver/mapping 失败、旧注释/库日期与 GLM 预训练暴露，以及匹配阴性背景。现代模型回看旧版本只能先称回顾性 annotation recovery，不能自动称预测未来。

### 6. Gap、传统工具与下游用途

`GAP-ROUTE-TERMINAL-AUDIT-20260908.md` 列出真正已关闭、未执行和真值缺失路线。已尝试的有限候选没有可部署 gap 修复；没有穷尽所有可能方案。保持 L1 TE-associated bp material、L2 comparator topology、L3 biological instance 区分。

HN-O 对 H0-O 的 fraction-MSE 降低 8.5905%，action AP .30359897→.38721622；三 seed 一致，信息增量探索性阳性。随后 12520644 对 60,497 完整 tie 阈值无一个满足宽松低风险 whole-gap 动作必要条件，所以固定模型部署仍 NO-GO。NT logit 与 seam 组合效应不能单独归因 NT。

旧 C：27 单元，MW/MP gained=lost=0；MP micro chain F1 +.000971 是 FP 净变化，不是新正确基因。新的 P3 base-mask U/P/R 问题已预注册但 smoke 工程失败，见上。转录调控用途本轮未找到已完成独立效用实验。

请核查传统流程的任务和 library 使用，避免“传统方法也如此”变成无来源的普遍断言。可用性由明确用途及实测收益决定，gap 未解不自动否定 L1，也不能用潜在用途代替效用证据。

### 7. 直接 superfamily 注释

`reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/superfamily5.tsv`：base-pretrained TE detect F1 .9041037，main4 conditional macro-F1 .8644150，Unknown recall .3885974；binary-H0 初始化 main4 .8632672、Unknown recall .0426272。

**命名需纠正**：BG/SINE/LINE/LTR/DNA/Unknown 是粗 TE 类型集合，并非完整生物学 superfamily 清单。conditional main4 排除了部分拒识/背景问题，不能用来替代全输出性能。应同时显示 per-class、全六类、reject/risk-coverage。

20260812 accession-preserving adapter 6/6 仅为语法工程；full identity/homology-safe direct-S0 后续未完成。入口 `SF-DIRECT-BASELINE-SCREEN-20260811-R2.md`、`SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1.md`。历史好分可报告，但不足以宣布广泛可用的真 superfamily 注释器。

### 8. Dfam consensus/contrastive clustering

本轮直接读取 `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/embedding_dfam_consensus.tsv`，1800 fragments、10 clusters：

| setting | ARI | NMI | holdout macro F1 |
|---|---:|---:|---:|
| A0 GLM raw | .079557 | .141071 | .238251 |
| A1 GLM + contrastive | .224190 | .311891 | .413748 |
| C0 basic features | .142266 | .238580 | .338528 |
| C1 basic features + contrastive | .708307 | .713472 | .421935 |

不能把另一 panel 的 C1 ARI .9208 或 A1 .7987 移植到 Dfam consensus。旧审阅指出 pooled train+holdout 的 clustering 指标、身份/同源隔离及预处理边界问题；holdout F1 也需按实际 split 解读。使用 family labels 定义正负对属于监督/弱监督 contrastive training；最后用无监督 clustering 不使整个流程成为无监督发现。

入口 `EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1.md`、`DIRECT-ANNOTATION-CLOSURE-20260824.md`、相关 embedding 实现。当前支持目标函数影响表征的探索，未支持 GLM 优于简单特征或学界通用新家族发现工具。

### 9. 传统 benchmark、CPU 和 Omnibenchmark

`LEMMI-TE-BENCH-20260824-R1.md` 已有同一 FlyBase r6.68 全组装 3 个有效 cell：HiTE、Base-CE、DAPT-CE。T1 positive-only bp recall 为 .448982/.003408/.018514，segment recall@.8 为 .216412/0/.000402；不可报 genome precision/F1。这些是历史 Base/DAPT，不是当前 P3/shared D 的比较，不能相互替代。

五传统工具完整公平矩阵尚未完成；不同物种工程产物和早期部分 de novo 表不能合并成该 R1。最小缺口是同一合格冻结实例的第二个传统完整 workflow，加当前拟发布模型。

已有 CPU synthetic FASTA smoke（8206 bp）证明入口可执行，不是代表性 throughput benchmark。建议补 CPU/GPU 吞吐及 RSS/VRAM、端到端 walltime、cold/warm、线程数/型号、相同 callable bp；区分 raw inference 和整条 library-discovery+annotation 流水线，保留超时/失败分母。不得由小 smoke 外推整基因组耗时。

本轮读取官方教程 https://docs.omnibenchmark.org/latest/tutorial/ ：YAML 支持 data→methods→metrics、Git reference、software environments 和 metric collectors，并提供 `ob validate plan`/dry run。它适合复用现有 adapter 包装 benchmark 的执行和追踪；不会替我们解决标签真值、library fairness、ontology 或 sealed split。当前项目未安装/实现 Omnibenchmark，这一项是可行性建议，非完成的流程。请另核实当前官方运行/HPC 文档后给出最小接入方案，不要求为论文先迁移所有历史实验。

### 10. 遗漏方向和整篇论文叙事

请额外评估：标签来源完整性与 Unknown shielding、token→bp/坐标一致性、bp 检测与结构恢复脱钩、任务微调损害 family geometry、严格负结果和 actionability gap、DNA-only FASTA 接口与计算资源、预训练暴露边界、annotation-audit 候选与解释性负对照。这些应按科学贡献而非工程工作量决定位置。

## 请求 Pro 交付

1. 独立检查附件工作树及现有关键表、代码，不只复述本文；指出本文遗漏或错误。每个重要数值引用文件/字段/分母，冲突以当前有效原表和协议为准。未能访问的原始数据/权重/HPC明确列出。
2. 十问逐项给出：已证实结果、推断、未执行/失败、正文/补充/讨论/暂不纳入，以及改变结论所需最小实验。
3. 给出一个连贯的论文中心论点与 title/abstract/introduction/results/discussion/methods/data-code availability 完整英文初稿，中文解释取舍。不要把全部分支硬拼成万能模型论文；不能以大纲替代完整初稿。证据缺口用明确占位符，禁止编造新实验、数值、统计显著性和引文。
4. 给出主图与补图逐 panel 设计、现有数据路径、图支持/不支持的 claim；补实验按投稿前必要、增强、可以放弃排序，写出改变哪条 claim、成本量级和停止条件。
5. 特别判断是否需要独立 L1 panel、严格公平的小型 backbone 比较、Tiberius 原协议完成、第二传统 workflow 和 CPU 性能实验；不要自动建议 MoE/大规模超参搜索或重开已关闭同类路线。
6. 输出完整可保存 Markdown 及简洁中文决策摘要。如可生成下载文件，也请把主要结果与完整稿件放在可读取回复中。顾问意见不是新实验授权或公开发表批准。
