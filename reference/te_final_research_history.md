# 旧项目 TE_final 研究历程 + 理解消化（蕾姆 2026-06-14 整理）

> 用途：把旧项目 `../TE_final/` 的真实研究历程、技术栈、翻车真相、避雷与教训钉死，供新项目从头设计时随时回查，防上下文变长后遗忘。
> **定位**：旧研究是"理解历史 + 避坑"的背景，**不是要继承的蓝图**（用户明确：旧项目做得不好，新研究从头来）。
> 已读来源：INDEX / RESEARCH_STATUS / PAPER_EXPERIMENT_PLAN / F1_DM6_HONESTY_REPORT / 07_tri_review_post_retraction(部分) / 手稿.pdf / research_proposal_v3 / experimental_plan_v4 / 新项目 03_roadmap+0_data README / landscape四队调研。
> 待读：phases/phase0-7 细节、EXECUTION_ROADMAP_v6、TE_BENCHMARK_PLAN、CROSS_SPECIES_GENERALIZATION_REPORT、METRIC_CONTRACT、W11/W12(RM-free)。

---

## 1. 旧项目一句话
hg38 为主的**监督式 per-base TE 检测 + 多物种泛化 benchmark**，投稿 Nature Methods，到 v6/曾撤回重写。**核心方法没真正突破 SOTA，最终靠"诚实报告局限"投稿**。

## 2. 7-Phase 研究体系（= 用户手稿的来源，思路一脉相承）
- Phase 0 Dfam 版本验证 → Phase 1 二分类基线(GENERanno) → Phase 2 传统工具基准 → Phase 3 BIOES 边界 → Phase 4 跨物种泛化 → Phase 5 LLM式混合训练 → Phase 6 PU-Learning → Phase 7 嵌入聚类
- 对应手稿：④(1)跨物种=Ph4、④(1)混合=Ph5、⑥PU=Ph6、④(4)嵌入=Ph7。

## 3. 真实技术栈（★修正之前误解：不是短窗口！）
- **Backbone**：主力 **NT-v2-250M**（实验代号 N13=3-kingdom、N28-animal）；**GENERanno-eukaryote-0.5b-base(500M)** 作 Phase1 hg38 + C.2 第二 backbone(N3)。**backbone 间差 <0.03，"架构假设≫backbone调参"**。GENERanno 注释任务略优。
- **窗口**：**8192bp 和 2048bp（非重叠）** —— GENERanno/NT 能吃 8192bp，不是 512/1024。
- **Split**：**染色体级**（train chr1-16 / dev chr17-18 / test chr19-20），防泄漏 ✓。
- **任务头**：**per-base token classification**（逐token分类），binary(TE/non-TE)→后期 multiclass。**不是检测式**（检测式是新项目相对它的真·新方法）。
- **训练**：weighted-CE(TE权重3.0)/focal；**BF16关键**(FP16梯度崩)；3 epoch；多GPU。

## 4. 关键结果数字（F1_DM6 诚实重算，可信）
- **同协议 unseen test per-base TE F1**：hg38 0.94 / mm39 0.92 / dm6 0.93 / anoGam3 0.86 / arabidopsis 0.75 / oryza 0.87 / zea_mays 0.97 / populus 0.76。
- **⚠️ fungi 近噪声**：neurospora 0.46 / aspergillus 0.51 / saccharomyces 0.07（TE% 仅 0.08-0.31%）→ **fungi 标签/信号极弱，新项目 fungi tier 要警惕**。
- **🔴 远缘物种崩溃**：held-out ci3(海鞘) F1 **0.10-0.18**、ce11(线虫)同类崩 → **phylogenetic-distance ceiling**：进化距离↑→性能↓，ρ=−0.90~−0.92(可复现)。

## 5. 💥 翻车真相（旧项目"做得不好"的核心）
- 头号卖点"dm6 mixture-induced suppression reversal"(声称 ΔF1=+0.601) **被 F.1 sanity check 推翻**：真实 ΔF1=+0.008(CI[−0.0005,+0.019]，不显著) → **论文撤回重写**。
- **根因 = 跨协议比 F1**：0.356 低分来自 TE-Benchmark whole-genome 协议，错当成与 chr-wise 协议可比。诚实重算 dm6=0.93 正常。
- 撤回后卖点退化：**"new SOTA"(脆弱) → "boundary-defining"(把模型远缘崩溃的局限包装成发现)**。

## 6. ✅ 旧项目唯一稳健的真发现
**phylogenetic-distance ceiling**（进化距离→TE识别衰减，ρ=−0.90~−0.92）+ N32 NULL(注释不完整假设被证伪)。这正是手稿④(2)"衰减公式"的实证基础——新项目可正面做成卖点。

## 7. 🚫 避雷清单（旧项目已验证无效，新研究别再踩）
1. **跨协议比 F1 = 致命**（dm6 翻车根因）→ 新项目统一评测协议是生命线。
2. **CRF/BIOES** 后处理无效甚至降点（Ph3/旧E）。
3. **HMM 平滑** 输给便宜的 min-length+merge-gap（旧E）。
4. **TE-family 嵌入聚类** NMI≤0.10 无产物（Ph7/旧G）→ 手稿④(4)该放弃。
5. **随机窗口 split** 泄漏（旧用随机窗→改染色体级）。
6. **PU-Learning**（Ph6）用户试过"效果都不好"。

## 8. 🩸 给新研究的血泪教训（最重要）
1. **统一评测协议从第一天锁死**——旧项目最大翻车就是跨协议。任何跨工具/跨物种比较前先验协议一致。
2. **zero-human 卖点要早测"远缘崩溃"**：旧项目连远缘动物都崩到 F1 0.1。hs1 离训练的哺乳类较近、可能 OK，但**必须早测 hs1 到底崩不崩**，别假设泛化半径无限。
3. **"换backbone+加物种+per-base分类" ≠ 突破**：旧路线做到头也没决定性赢传统工具 → 新研究必须有**真新方法**(检测式/ab initio/长上下文全长)，否则重蹈覆辙。
4. **诚实负结果可发表**，但别把它当主线卖点(旧项目被迫如此)。

## 9. 新项目数据管线现状（scripts/0_data，须 ssh baobab 读）
- 流程：下载→质检(含BUSCO)→TE注释(RepeatMasker+Dfam弱标签)→BUSCO物种难度→训练数据→17检查类分布→18窗口数据集→20 split manifest(+tier_classification_results.json)。
- **🔴 不一致**：0_data README 说窗口 **1000bp/500bp**，但旧项目用 **8192bp**——新项目窗口反更短，待厘清（过时默认？还是先短窗快跑？）。
- **🔴 缺口**：现有是逐碱基 mask，**无检测式 box 标签**；无"碎片→全长 defragment"；长上下文(Evo2)窗口管线未建。
- BUSCO 物种难度 = 意外红利，可喂 P3 衰减曲线。

## 10. 与 v3/v4/手稿/landscape 的关系
- 手稿/v3/v4/旧7-phase 思路一脉相承，但旧项目已证多处执行/评测翻车。
- landscape 四队结论：FM 做逐碱基/全长/跨物种 TE 注释基本空白；YOLO式仅 YORO 一篇(只做一半)；评测无现成benchmark须自建；对标 EDTA(sens75/spec95)。
- 当前未定稿草案：`TE_research_plan_v5_unified.md` + `TE_pipeline_overview.md`（**v1讨论稿，用户要从头重审，勿当定稿**）。

## 11. 待核实/待读
- mouse/zebrafish/chicken 弱标签重跑是否 done（memory 6-08 在跑）。
- fungi rmsk_te.bed <1KB 是否只文件头。
- 18_build_window_dataset / 20_create_split_manifest 的标签格式与 split 粒度（染色体级有没有做）。
- 待读 phases/phase4-7 细节 + ROADMAP_v6 + BENCHMARK_PLAN + CROSS_SPECIES + METRIC_CONTRACT。
