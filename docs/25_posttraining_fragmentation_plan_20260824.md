# Fragmentation、post-training 与论文收尾实验决策报告（2026-08-24）

## 1. 结论先行

当前最合理的主线仍是直接注释，而不是立即退到 traditional refinement 或 long-seed rescue。首轮只回答一个问题：在不向推理阶段提供 TE library、RepeatMasker、EDTA 或 HiTE 调用的前提下，训练期显式加入边界与连续 truth-run 监督，能否让 GENERanno 从高 bp-F1 的逐碱基分类器变成更连贯、更准确的 TE interval annotator。

冻结的推进顺序如下：

1. **P1-C1：structure-aware full-backbone adaptation，立即执行。** 与全模型 CE 控制组在相同初始化、数据、顺序、更新数和推理协议下比较。
2. **P1-DAPT：literal continued-MLM，条件执行。** 它确实是狭义的 continued pretraining，但单独没有边界/连续性机制，且需要 MLM→annotation 两阶段；不与首轮 C1 混跑。
3. **P1-C2：long-context cross-window consistency，条件执行。** 若 C1 有方向性信号但跨窗口/窗口边缘仍是主要误差，再加入配对视图一致性。
4. **P2：traditional-call-conditioned refinement。** 仅在两个有意义的 P1 机制公平失败后解锁；此时以 RM/EDTA/HiTE 调用作为条件输入，目标改为 refinement/new-candidate prioritization，不再称纯 ab initio。
5. **P3：long seed → target-derived consensus/profile → short-fragment recovery。** 只有在“长 TE 更易被模型准确识别”经匹配分析成立后才解锁；这是最后方案，创新性与 HiTE 更接近。

首轮的科学定位是 **human-only feasibility**，不是 family-disjoint generalization，也不是 novel-family discovery。当前数据缺少 family/copy/homology-component 身份；任何更强结论都必须等待身份层重建。

## 2. 已确认的现有结果

### 2.1 当前模型不是 frozen backbone + shallow head

现有 `te_token_task.py` 使用 `AutoModelForTokenClassification`，训练时没有冻结 backbone。已完成的 cross-supervised 4096 训练包含 16,200 个训练窗口、2,000 steps，属于完整 backbone 的监督式逐碱基 CE 微调。因而下面的表述不成立：

- “此前只训练了一个额外分类层”；
- “再做一次 full-backbone CE 就是新的 post-training”；
- “旧结果已经证明 continued pretraining 无效”。

真正未被公平测试的是：

- literal MLM/DAPT continued pretraining；
- 对边界与实例连续性有直接训练信号的 full-backbone adaptation；
- 配对长上下文的跨窗口一致性训练。

### 2.2 核心失败是 base-to-instance gap

已核实的代表性结果为：

| 指标 | 现有代表值 | 解释 |
|---|---:|---|
| bp-F1 | 约 0.9110 | 碱基层覆盖较强 |
| segment-F1 | 约 0.2392 | 严格区间匹配弱 |
| boundary-F1 | 约 0.1916 | 边界定位弱 |
| short-fragment rate | 约 0.7898 | 预测高度碎片化 |
| animal segment-F1@IoU0.8 | 约 0.2557 | 严格 animal 结果仍低 |
| animal boundary-F1@5 bp | 约 0.0989 | 精确边界最弱 |

这说明主问题不是“完全不会识别 TE bp”，而是模型没有把局部 TE evidence 组织成正确的生物学实例。

### 2.3 已充分尝试、首轮不再重命名复跑的路线

下列方向已有直接或近邻实验，且没有安全解决 fragmentation：

- threshold、gap merge、minimum length；
- HMM、CRF、semi-Markov 风格平滑；
- frozen refiner、boundary proposal；
- anchor-free interval、fragment graph；
- survival/retention constrained decoder；
- consensus-coordinate merge。

早期某些 coarse segment 指标提高主要来自删除短预测或不安全合并，并常伴随 missed truth 增加。首轮 C1 的推理仍使用原始 token probability + 固定阈值；上述后处理不能计入 C1 的收益。

### 2.4 MoE 目前没有被证明必要

当前只有 conservative selector/triage 的证据，没有一个完整 MoE 系统，也没有证据表明 experts 在同一实例上具有稳定且可路由的互补错误。MoE 不是 fragmentation 的默认解法。若进入 P2，必须先证明不同传统 caller 与 FM 候选的误差互补，再决定是否需要 gating；否则简单的 conditioned refiner 是更小、可解释性更高的方案。

## 3. `TE_final` 对比学习与聚类审计

旧实验中“效果很好”的数值真实存在，但不能解释为严格无监督 family discovery。

### 3.1 Module 5

73,676 条 TE、13 species、12 top-level classes、123 families。冻结表示直接 KMeans 的 class ARI/NMI 为：

| 表示 | ARI | NMI | 审计结论 |
|---|---:|---:|---|
| 6-mer | 0.0315 | 0.1015 | 弱 label-free baseline |
| base GENERanno | 0.0208 | 0.0565 | 弱 |
| binary-finetuned GENERanno | 0.0188 | 0.0714 | 弱 |
| 6-mer + supervised projection | 0.9281 | 0.9713 | 同一批样本用 class 标签训练并评估，非无监督证据 |

### 3.2 Phase 7

最高 KMeans ARI 约 0.9287 的实验使用 class-supervised contrastive learning、oracle K 和 random record split。只读复现显示 hg38 test 的 39/39 families 全部在 train，920/927 repeat names 也在 train。family hard-negative 的 exp003 最接近用户提出的目标，但训练 OOM，未产生有效结果。

因此目前只支持以下保守结论：

> 在泄漏较强、标签参与的同域设置下，监督 metric learning 可以分开已知 top-level TE classes；冻结 FM embedding 是否自发形成可用于新 family discovery 的几何结构，尚未得到支持。

### 3.3 可复用与不可复用

可复用：masked mean pooling、6-mer/MinHash baseline、HDBSCAN/Leiden 框架、cluster stability、noise coverage、metadata schema。

不可复用：random row split、先 upsample/crop 再 split、oracle K 主结果、用标签 ARI 选超参数、把 supervised projection 称作无监督聚类。

新的辅助聚类实验只有在每条记录冻结 `assembly/species/chrom/start/end/family_id/copy_id/component_id/accession` 后才启动。主面板必须包括：

- seen-family、zero homology-component overlap；
- novel-family、entire family test-only；
- leave-one-species-out；
- 6-mer/MinHash、base GENERanno、P1 adapted model、binary-finetuned model 的冻结表示比较；
- HDBSCAN/Leiden 或 label-free K，oracle K 仅作明确 upper bound；
- ARI/NMI/homogeneity/completeness/stability/noise coverage，以及 species-vs-family signal。

同 family 不同 copy 的 supervised contrastive 可作为 taxonomy probe/upper bound，不能作为无监督主方法。

## 4. 冻结的物种与数据矩阵

### 4.1 首轮 P1

| 角色 | 数据 | 冻结 split | 是否参与调参 |
|---|---|---|---|
| train | Human HS1 8192 | chr1/3/5/7/9 | 是 |
| validation | Human HS1 8192 | chr11/13/15 | 是 |
| primary test | Human HS1 8192 | chr17/19/20/21/22 | 否 |
| frozen transfer | Mouse 8192 | chr1，现成 1200 windows | 否 |
| frozen transfer | Fruit fly 8192 | chr3R，现成 1200 windows | 否 |
| stress-only | Rice 8192 | chromosome 1，现成 1200 windows | 否；不得进入主 gate |

Human 数据路径：

`software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/{train,val,test}/data.jsonl.gz`

每个 split 3,000 windows。metadata SHA256：

`d5410cf3ab74d98175e20714dee1f61ecfda6a7245be884039c6b1d0a243bbcb`

Human train/val/test 的 TE/BG/ignore bp 分别为：

- train：11,106,154 / 13,465,478 / 4,368；
- val：11,946,723 / 12,623,555 / 5,722；
- test：11,199,705 / 13,362,498 / 13,797。

### 4.2 标签源

窗口用 `comparator_strict` 绘制 TE，`comparator_plus_unknown` 置为 `-100`；它们不是直接用 self-Dfam 输出绘制。

Self-Dfam 与 comparator 的 bp Jaccard：

- human 0.948128；
- mouse 0.892472；
- fruit fly 0.888725；
- rice 0.042709。

Rice 的外部 PlantTE comparator 与 self-Dfam 严重错位。低 Jaccard 不证明 Rice truth 错误，但证明它与 animal 主 estimand 不同，所以只能作为压力测试。

### 4.3 明确未知与阻断边界

- Binary JSONL 只有 `sequence/labels/chr/start/end`，没有 repName/family/copy/component。
- 当前 Dfam exact identity coverage 为 6447/6727，另有 279 missing、1 ambiguous；不能声称 family/homology-clean。
- 主 Human/Mouse/Fly binary truth 没有已验证的 biological parent/copy truth。
- Rat 与 dog 只有远端 URL，`local_source` 为空，不纳入当前计划。
- Rice RGAP7+EDTA 有 341,313 个 positive-only `rm_id` groups，可用于辅助 parent fragmentation audit，但 unlabeled space 不等于 negative，不能作 whole-genome P1 precision/F1 truth。

## 5. 立即执行的 P1-C1

### 5.1 输入协议

旧 `single_nt` 在 8192 bp 上会加入 BOS/EOS，形成 8194 tokens，超过模型配置的 `max_position_embeddings=8192`。旧作业成功只证明代码能运行，不能消除语义问题。

新实验使用显式 `single_nt_nospecial`：

- 8192 bp = 8192 tokens；
- 不插入 BOS/EOS；
- label 与 token 严格 1:1；
- CE 与 C1 都使用同一协议；
- 新 CE 可以作为 C1 的匹配控制，但不能把它与历史 `single_nt` 数值称为逐位复现。

### 5.2 实验臂

| arm | 初始化 | 主 loss | 训练期辅助 loss | 推理 |
|---|---|---|---|---|
| CE | GENERanno 0.5B base | weighted binary CE | 两项权重均为 0，但走相同 hidden/aux compute | raw token logits |
| C1 | 同一 base | 同一 weighted CE | 0.2×boundary distance + 0.05×run SupCon | raw token logits |

两臂固定：seed 42、batch 1、gradient accumulation 16、LR 2e-5、TE class weight 3、bf16、gradient checkpointing、相同 data order、固定 final step，不按各自 validation bp-F1 选择不同 checkpoint。

### 5.3 C1 目标

Boundary target：对每个连续 truth-positive run，训练两个通道分别预测到左/右真实边界的距离，cap=256 bp 后归一化。若 run 在窗口边缘被裁剪，或边缘相邻为 unknown，缺失一侧不参与对应 loss。

Run contrastive：

- 同一连续 truth-positive run 内的 token 是 positive；
- 不同 truth runs 是 negative；
- run 至少跨 64 bp；
- 每 run 最多 8 tokens，全窗口最多 256 tokens；
- temperature=0.07；
- 少于两个合格 runs 时该 microbatch 的 contrastive loss 为 0，并在训练 metadata 中记录有效 anchors/runs。

总损失：

`L = L_CE + 0.2 L_boundary + 0.05 L_run`

辅助 boundary head 只在训练中存在，最终保存前删除。推理不增加 decoder、library、传统 caller 或后处理。

一个真实风险是 RepeatMasker truth 的两个相邻 runs 可能来自同一 biological copy。当前缺 parent truth，C1 的 negative 定义可能继承并强化 annotation fragmentation。首轮是在检验这个假设，不预设 C1 必然改善。

### 5.4 动态执行层级

| profile | 输入 | steps | 目的 | 可产生 claim? |
|---|---:|---:|---|---|
| infrastructure smoke | Human 8192 | 2 | forward/backward、finite loss、anchors、保存重载、strict eval | 否 |
| directional pilot | Human 8192 | 100 | 检查早期方向与明显伤害 | 否 |
| first screen | Human 8192 | 800 | 首个有意义的 CE/C1 机制比较 | 否，仅决定是否继续 |
| confirmatory | 重建后的多物种/身份安全 panel | 待 pilot 定标 | 多 seed、family/homology-safe 结论 | 是，前提是数据 Gate 完成 |

Smoke 成功不自动证明 C1 有信号；100-step pilot 也不能替代 800-step screen。每一级只在前一级无运行错误且没有明显机制性伤害后提交。

## 6. 评价协议与预注册决策门槛

首轮只比较 `raw_threshold`，阈值固定 0.5。HMM、CRF、gap merge 行仅保留为历史参考，不能计入 C1 收益。

固定报告：

- bp precision/recall/F1；
- segment F1@IoU 0.5/0.7/0.8/0.9；
- boundary F1@5/10/25/50 bp；
- median boundary error；
- split truth rate、missed truth rate、mean fragments per truth；
- short predicted segments / all predicted segments；
- pred true-backed rate、short true-backed rate；
- truth length bins：`<500`、`500–999`、`>=1000 bp`。

以下数值是本轮预注册的 screen 决策规则，不是既有仓库已经确认的正式阈值：

1. segment-F1@IoU0.8 相对 matched CE 至少 `+0.02`；
2. boundary-F1@5 bp 至少 `+0.02`；
3. short-fragment rate 相对下降至少 20%；
4. mean fragments per truth 相对下降至少 15%；
5. bp-F1 下降不超过 0.01；
6. missed truth rate 不超过 `CE + 0.03`；
7. pred true-backed rate 不出现大幅下降；所有改善必须同时报告分母，排除“删除预测所以看起来更整洁”。

若只有 bp-F1 提高而严格 interval/boundary/fragmentation 没有改善，判定 C1 没有解决目标机制。单 seed 800-step screen 阴性也不能宣布整个 P1 公平失败；它只关闭当前 C1 配方。

## 7. C1 之后的条件分支

### 7.1 Literal DAPT

狭义 continued pretraining 的公平实验必须是：

1. 从同一 GENERanno base 开始；
2. 对 raw genome 或训练域序列执行 masked nucleotide modeling；
3. 再用与 CE control 完全相同的 annotation fine-tuning；
4. 比较 `base→CE` 与 `base→DAPT→CE`；
5. token budget、optimizer steps 和额外算力单独报告。

DAPT 模型本身不能输出 TE annotation，仍需要 annotation projection/head。其价值是检验 domain adaptation，而不是“无 head 直接注释”。若 C1 无信号，DAPT 可以作为独立 P1 机制，但不能把更多 CE steps 伪装成 DAPT。

### 7.2 C2 long-context cross-window consistency

现有 4096 windows 在同一 chromosome 内连续，可组合为 8192/12288 parent loci；GENERanno 也已真实完成 8192 训练。候选设计为两个 offset 8192 views，保留 2–4 kb overlap，在 overlap 上加入 prediction JS consistency 与 representation cosine consistency。

只有在以下条件下启动：

- C1 有 interval/boundary 信号，或误差审计明确显示窗口 edge↔center disagreement 是主因；
- 单 8192-view inference 冻结，不在正式结果中用 view ensemble；
- 与 matched 8192 CE 比较，不把 context length 与 objective 同时变化后归因给其中一个。

### 7.3 P2 traditional conditioned refinement

若两个 P1 机制公平失败，输入可包括 RM/EDTA/HiTE calls 与 FM probability/hidden evidence。最低比较矩阵：

- traditional caller alone；
- FM alone；
- traditional + 简单 deterministic refinement；
- traditional-call-conditioned learned refiner。

只有 learned refiner 同时提高严格 interval/boundary、保留 true-backed fragments，并在 low-homology candidates 上提供新增价值时才保留。MoE 只有在 experts 的互补性被测量后才进入。

### 7.4 P3 长序列种子与短 fragment 恢复

首先检验前提“长 TE 更容易准确注释”。必须在 family、divergence、nesting、fullness 和 local context 可比时做 length-stratified 分析；当前 binary JSONL 缺这些字段，所以只能做描述性长度分层，不能作因果结论。

若前提成立，再测试：

`raw genome → FM high-confidence long intervals → target-derived consensus/profile → sensitive genome-wide alignment → short fragment recovery`

必须比较 long seeds 的来源：FM、HiTE、RepeatModeler2/EDTA。若 FM seed 没有提供传统工具未发现的高质量 seed，这条路线缺少核心新增价值。

## 8. 论文可发表条件

### P1 成功时

论文核心可以是：

- 揭示 DNA foundation model 的 base-to-instance gap；
- 提出结构感知 post-training，使 raw genome-only inference 的 interval、boundary、fragmentation 同时改善；
- 在冻结物种/同源面板上展示传统 library-independent 的新增能力。

不要求在所有 overall bp 指标上击败每个传统工具，但必须有一个无法由简单 smoothing/deletion 解释的 strict interval/boundary 优势。

### Novel TE 声明的附加要求

Teacher labels 不能证明 novelty。任何 novel TE 候选还需要独立证据，例如：

- 多拷贝支持；
- TIR/LTR/poly(A)/TSD 等结构；
- domain/profile 支持；
- 与训练 family/homology components 的距离；
- 人工审阅与传统 caller 盲区比较。

### P2/P3 成功时

论文定位应相应改为 `FM-assisted refinement/discovery` 或 `FM-seeded library construction and fragment recovery`，不能继续写成完全 ab initio end-to-end annotation。

## 9. 未确定事项登记

| 事项 | 当前状态 | 会限制什么 | 下一步证据 |
|---|---|---|---|
| C1 是否减少 fragmentation | 未知 | P1 主结论 | CE/C1 2→100→800 steps |
| Literal DAPT 是否有额外价值 | 未测试 | 狭义 post-training 结论 | MLM→matched CE 两阶段 |
| 长 TE 是否本质更易注释 | 未证明 | P3 解锁 | metadata-matched length analysis |
| family-disjoint 泛化 | 阻断 | novel-family/generalization claim | 重建 family/copy/component identity |
| biological parent/copy truth | 阻断 | parent-aware fragmentation | 验证 joined records/独立 gold |
| Rice 主评估可比性 | 不成立 | 跨 kingdom pooled gate | 仅 stress，另建一致 label source |
| MoE 是否必要 | 未证明 | P2 架构 | expert complementarity audit |
| Frozen FM embedding family geometry | 现有证据不支持 | 无监督 discovery | identity-safe label-free clustering |

## 10. 实现与执行记录

本轮只做最小必要改动：

- `te_token_task.py`：新增 exact 1:1 token mode、training-only boundary/run losses、fixed-final checkpoint 选项与输入几何记录；
- `strict_segment_eval.py`：增加同一 exact token mode 的推理映射；
- `sbatch/p1_c1_structure_20260824.sbatch`：CE/C1 共用，按 `PROFILE=smoke|pilot|screen` 动态提交；每个 array element 使用独立 run/report/log 标识。

未增加 decoder、统一框架、一次性抽象、错误吞噬或与当前问题无关的防御逻辑。HERO anti-overdefense 规则已在项目中存在，因此没有重复安装或叠加第二份配置。

Slurm job IDs、资源选择、实时状态和首轮结果将在实际提交后追加到本节。
