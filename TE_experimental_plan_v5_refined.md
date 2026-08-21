# 从头注释 TE 的基因组基础模型 — 实验思路计划 (v5 refined)

> 以 v4(`TE_foundation_model_experimental_plan_v4`) 为基础，**融合**：旧项目TE_final血泪教训 + 五发力点框架 + 检测式主线 + 当前代码现实 + landscape实证 + 可复用资产。
> 范围：ab initio(不依赖已知库/同源比对) · zero-human跨物种 · 全长TE逐碱基+检测 · 目标 Nature Methods。
> 配套：`reference/te_final_research_history.md`(旧项目避坑) · `TE_workflow_roadmap.md`(流程骨架)。**本文是细化版的"研究思路主文档"，供继续细化。**

---

## 0. TL;DR
多物种(zero-human)训练一个 **全长 TE 注释模型**——backbone=预训练gLM，**任务头从"逐碱基分类"升级到"1D检测式(全长box+嵌套)"**；在**严格留出物种(含hs1)**上做 ab initio 注释，超越传统工具(RepeatMasker/EDTA)。训练弱标签来自RepeatMasker/Dfam，**靠跨物种留出+未知家族分层+统一评测协议**论证学到的是可泛化序列语义而非"背库"。

## 1. 研究背景与动机
- **意义**：TE占真核基因组很大比例(人~50%,植物>80%),准确可移植注释是基础设施。
- **现状痛点(landscape实证)**：库依赖(RepeatMasker+Dfam)对新物种/未知家族弱、库偏倚;de novo(RepeatModeler2/EarlGrey)碎片化+重人工curation;**经典DL(DeepTE/TERL/TEclass2)几乎全是"对已切好序列做家族分类",无人端到端从基因组逐位发现+定全长边界**。
- **切入点**：把TE注释建模为**全长1D检测+逐碱基标注**,用预训练gLM赌"已隐含编码TE序列语义",以**留出物种**正面回答"ab initio跨物种泛化"。

## 2. 相关工作与差距(landscape四队核实)
- **FM做TE注释=基本空白**:主流gLM榜(GUE/Genomic Benchmarks/BEND/NT-bench)**全不含TE任务**;**Evo/Evo2从未被用于TE**(且Evo2训练主动down-weight repeat→TE是其弱项,既是风险也是机会)。
- **检测式做TE=仅YORO一篇(PLOS One 2023)**,但只检测内部domain、**不做全长边界、不处理嵌套**(合成数据回避重叠);**DETR式做基因组区段检测=公开空白**。
- **评测无现成benchmark**:须自建;对标EDTA碱基级(rice curated库 sens≈75%/spec≈95%)。

## 3. 科学假设与创新点
### 假设
- **H1可解码**:预训练gLM表示已隐含TE语义,轻量头即可解码。
- **H2跨物种泛化**:多物种训练可泛化到留出物种(zero-human→hs1)。
- **H3 ab initio优势**:未知家族/远缘物种上,不依赖库的方法相对优势更大。
- **H4标签突破(新增)**:嵌套/碎片/错误是性能天花板(旧项目证15%不一致);**检测式+嵌套感知标签可突破per-base逐碱基的天花板**。
### 创新点(升级v4)
1. **首个ab initio、全长、跨物种TE检测模型**(任务重定义为1D检测,超YORO:全长边界+嵌套+真实数据)。
2. **zero-human训练+人类留出**:干净证明跨物种泛化、回击"背库"。
3. **已知vs未知家族分层**:量化"学语义vs背库"。
4. **嵌套感知的全长TE建模**(DETR set-prediction治嵌套)。
5. **无golden-label下的可信评测方法学**(护城河,治旧项目翻车根因)。
6. **多物种全长TE基准+权重+评测脚本**(社区资源)。

## 4. 数据与基准
### 4.1 物种split(5-Tier,当前代码已落地)
- **T1训练(Animal,zero-human)**:mouse/zebrafish/chicken/frog/fruit_fly/c_elegans(**排human+灵长**)。
- **T2验证**:cow/opossum(near+far)。**T3留出衰减阶梯**:hs1/chimp/macaque/horse。**T4压力**:sea_urchin/oyster。
### 4.2 标签(★发力点③核心,深入v4)
- 训练弱标签:RepeatMasker full-parse(typed:LINE/SINE/LTR/DNA/Helitron/other)+Dfam。
- **三大标签问题必须正面处理**:① **嵌套**(TE插TE)→检测式box可表达重叠 ② **碎片化**(RM打断全长)→需defragment成全长box,金标准来源待定(结构工具LTRharvest/人工curated) ③ **错误**(三源不一致~15%)→多源并集高置信核+不一致区作鲁棒性分析。
- 评测金标准**求正交**:人工curated+结构证据(TSD/LTR/ORF)+Dfam高置信,**脱离单一库**。
### 4.3 防泄漏(铁律)
染色体级split(T1训练种内部也留test,避旧项目随机窗泄漏)+同源去冗余(CD-HIT/MMseqs2)+zero-human firewall(阈值/min_len在非人T2定)。

## 5. 模型与方法(★最大升级)
### 5.1 backbone(发力点①,定位=使能器非涨分)
- 旧项目实证**backbone差<0.03**→选型不为涨分,**为解锁长上下文吃全长TE**。
- **分阶段**:Stage1先**GENERanno**(当前代码,好微调)把检测头+pipeline跑通(注意:**窗口须从当前1000bp拉回≥8192bp**,1000bp装不下全长TE是退步);Stage2上**Evo2**(长上下文1Mb,单碱基)破全长死结,LoRA/冻结+轻量头适配显存(头号风险)。Caduceus(双向长)作对照。
- **因果性**:Evo2是causal(只看左),做注释须双向头/解掩码补右侧上下文(encoder如GENERanno天生双向,这是其优势)。
### 5.2 任务头(发力点②,v4只有逐碱基→升级)
- **起点**:逐碱基token分类(当前binary baseline,仅smoke)。
- **主升级**:**1D检测头**输出(start,end,class),显存友好+天然element输出+治嵌套;**优先DETR set-prediction**(二分匹配无NMS,天生输出重叠/嵌套)>anchor-YOLO;长度跨度大借FCOS-1D按类分radius;长基因组借滑窗+stable matching。
### 5.3 训练
多物种平衡采样;类不平衡focal/加权(主报AUPRC);BF16(旧项目证FP16崩);**避雷:CRF/BIOES/HMM平滑(旧证无效)**。

## 6. 实验设计(Stage化,融workflow)
- **Stage0地基**:binary baseline smoke(验证zero-human数据流+管线+**hs1留出崩不崩,铁律2**)+统一评测协议冻结+复现RepeatMasker/EDTA。
- **Stage1五发力点便宜pilot(找最佳)**:①GENERanno 1000 vs 8192bp长窗对比+Evo2探针 ②per-base vs 检测头小数据对比 ③标签审计(嵌套/碎片/错误率量化) ④no-human-on-human gold-std pilot ⑤k-mer repeat-score vs Dfam相关性(v3 MVP-1,2周CPU)。
- **Stage2主攻最佳发力点**(开局假设:②检测+③标签核心硬币+①长上下文使能)。
- **消融**:backbone/窗口/检测头vs逐碱基/typed vs binary/多vs单物种。
- **分层评估(核心卖点)**:已知vs未知家族、进化距离衰减曲线、TE类型(LINE/SINE/LTR/DNA/Helitron)。

## 7. 评估指标与统计(融旧项目可复用资产+铁律)
- **★统一协议=生命线**(旧项目最大翻车=跨协议比F1;任何比较前验协议一致)。
- **复用旧评估器`evaluate_predictions.py`**:BP级(sens/spec/F1/MCC)+**element级IoU/median boundary error/fragmentation rate/merge rate**(已现成,不重造)。
- **主指标**:per-base macro-F1/AUPRC(类不平衡)+per-element IoU-F1+边界精度+校准ECE。
- **★no-golden可信评测(发力点④)**:no-human训练在human上评分作gold-std+多版本注释投射比较(手稿⑥);承认弱标签非真值。
- **统计**:3-seed paired bootstrap(旧N23升标配)。

## 8. 计算资源与时间线
baobab private-teodoro-gpu;**头号风险:Evo2体量vs配额→Stage0先做显存smoke**。M0地基→M1 baseline+pilot→M2主攻→M3泛化+评测→M4投稿。

## 9. 风险与缓解(旧项目四铁律 + 避雷)
| 风险 | 缓解 |
|---|---|
| 跨协议比F1(致命) | 统一协议冻结于Stage0 |
| 远缘崩溃(旧证F1 0.1) | Stage0早测hs1;衰减曲线量化 |
| 重复旧套路赢不了 | 必上检测式/长上下文/ab initio真新方法 |
| 弱标签天花板 | 多源高置信核+正交金标准+发力点③ |
| Evo2显存 | LoRA/冻结+轻量头;先smoke |
| 嵌套建模 | DETR set-prediction;小数据先pilot |
**避雷**:CRF/BIOES/HMM·family嵌入聚类·混合提升远缘·PU-Learning·随机窗split·停在1000bp逐碱基binary。

## 10. 预期结果与影响
留出物种(含hs1)上ab initio全长TE注释匹配/超越RepeatMasker(尤其未知家族);进化距离衰减规律;证zero-human可泛化人类。影响:首个ab initio跨物种全长TE检测FM+缺失的benchmark+权重/脚本。

## 11. 关键决策点(待用户细化)
1. **②检测+③标签"核心硬币"假设**成立否?Stage2主攻谁?
2. 检测式:DETR vs YOLO;嵌套怎么建模;全长defragment金标准从哪来。
3. backbone:GENERanno长窗(8192) vs Evo2,Stage1 pilot后定;窗口何时从1000拉长。
4. typed粒度(5类?)/主指标(per-base vs per-element)。
5. zero-human:主线科学claim + production(含human)附线?
6. 五pilot优先级与并行数。

## 12. 下一步
确认§11决策→据此细化各Stage→Stage0 binary baseline smoke先跑(验hs1崩不崩)→Stage1 pilot找最佳发力点。(council/tri-review待思路完全定稿后再上。)
