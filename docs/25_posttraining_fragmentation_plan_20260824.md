# Fragmentation、post-training 与论文收尾实验决策报告（2026-08-24）

## 1. 结论先行

当前最合理的主线仍是直接注释，而不是立即退到 traditional refinement 或 long-seed rescue；但首个结构感知配方已经得到阴性 screen 结论。`0.2×boundary distance + 0.05×run SupCon` 确实减少了一部分 reference-run fragmentation，却没有达到预注册幅度，并持续损害 boundary，因此关闭该具体配方，不晋级 multi-seed 或 confirmatory。这个结果不等于整个 P1/post-training 失败。

冻结的推进顺序如下：

1. **P1-C1：已完成并关闭当前配方。** 800-step chr17 screen 只通过 bp-F1 与 missed-truth 两项容忍 gate；segment、boundary、short-fragment 与 fragments/truth 四项未通过。
2. **P1-DAPT：下一项直接实验。** 这是尚未公平测试的 literal continued-MLM；严格语料只用 train chr1，随后再执行与 matched CE 完全相同的 annotation training。
3. **P1-C2：证据条件分支。** 先做 edge↔center disagreement 的只读审计；只有窗口边缘确为主误差，或未来结构机制已有正信号，才启动 paired-view consistency。
4. **Human confirmatory 数据 Gate：与机制 screen 分开。** DAPT 若在 quick panel 有信号，先用现成脚本重建 chromosome-balanced 8192 panel，再做多 seed；不在当前单染色体文件上形成发表 claim。
5. **P2：traditional-call-conditioned refinement。** 若 DAPT 公平失败且 C2 未被误差证据解锁，可把资源转向 P2，但不能声称所有 direct post-training 已穷尽。此时以 RM/EDTA/HiTE 调用作为条件输入，目标改为 refinement/new-candidate prioritization，不再称纯 ab initio。
6. **P3：long seed → target-derived consensus/profile → short-fragment recovery。** 继续阻断，直到获得可识别完整 copy/fullness 的资产并证明长完整 TE 的前提；reference-run 长度分层不足以解锁。

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

### 2.2 核心失败是 base-to-reference-annotation-run gap

已核实的代表性结果为：

| 指标 | 现有代表值 | 解释 |
|---|---:|---|
| bp-F1 | 约 0.9110 | 碱基层覆盖较强 |
| segment-F1 | 约 0.2392 | 严格区间匹配弱 |
| boundary-F1 | 约 0.1916 | 边界定位弱 |
| short-fragment rate | 约 0.7898 | 预测高度碎片化 |
| animal segment-F1@IoU0.8 | 约 0.2557 | 严格 animal 结果仍低 |
| animal boundary-F1@5 bp | 约 0.0989 | 精确边界最弱 |

这说明主问题不是“完全不会识别 TE bp”，而是模型没有把局部 TE evidence 组织成与 reference annotation runs 一致的区间。当前没有经过验证的 parent/copy truth，不能把这些 runs 直接称为完整生物学 TE 实例。

这些代表值来自既有 quick panels；旧报告已经注明 `max_windows` 会被每个 split 的第一条 eligible chromosome 填满。因此它们适合描述已观察到的 gap，不是 publication-level 多染色体估计。

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

| 角色 | 数据 | 当前 JSONL 实际内容 | 是否参与调参 |
|---|---|---|---|
| train | Human HS1 8192 | chr1，3,000 windows | 是 |
| validation | Human HS1 8192 | chr11，3,000 windows | 是 |
| primary screen | Human HS1 8192 | chr17，3,000 windows | 否 |
| frozen transfer | Mouse 8192 | chr1，现成 1200 windows | 否 |
| frozen transfer | Fruit fly 8192 | chr3R，现成 1200 windows | 否 |
| stress-only | Rice 8192 | chromosome 1，现成 1200 windows | 否；不得进入主 gate |

这里的 “frozen transfer” 只指当前 screen 不用这些文件调参。publication-level confirmatory 的精确物种、assembly/release、chromosome split 与数据内容 hash 尚未冻结，不能把这张现成资产表称为正式发表面板。

Human 数据路径：

`software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/{train,val,test}/data.jsonl.gz`

每个 split 3,000 windows。metadata SHA256：

`d5410cf3ab74d98175e20714dee1f61ecfda6a7245be884039c6b1d0a243bbcb`

这是 metadata 文件的 hash，不是三个 gzip JSONL 内容的 hash；而且 metadata 记录了未全部 materialize 的候选 chromosome。重建 confirmatory 时必须另行冻结实际数据文件的内容 hash。

Human train/val/test 的 TE/BG/ignore bp 分别为：

- train：11,106,154 / 13,465,478 / 4,368；
- val：11,946,723 / 12,623,555 / 5,722；
- test：11,199,705 / 13,362,498 / 13,797。

metadata 中登记的候选 chromosome 集合原本为 train `chr1/3/5/7/9`、val `chr11/13/15`、test `chr17/19/20/21/22`，但对实际三个 gzip JSONL 的逐条核对显示，生成过程达到 3,000-window 上限时已在每组第一条 chromosome 停止。因此当前文件不是多染色体 split；`12059558` 与 `12059660` 都只能解释为 chr17 screen。正式 confirmatory 必须按 chromosome 配额重建 8192 panel、核对实际 chromosome 计数并冻结新的 hash，不能沿用上面的 metadata 声称多染色体泛化。

原因已定位到 `prepare_ucsc_windows.py` 对整个 split 使用单一全局 `emitted` cap，并按 FASTA/chromosome 顺序达到上限后停止，而 metadata 回写的是请求列表。构建一个“多染色体、每条染色体固定前缀”的最小 confirmatory 不需要改代码：用现有 `--chrom` 接口逐染色体各生成 600 windows，再由现有 `sample_jsonl_mix.py` 全量合并，可得到 train 5×600、val 3×600、test 5×600。val/test 必须全量评价，不能再用 800/1200 的全局前缀截断。该方案仍不是 chromosome-wide 均匀抽样；若要代表整条染色体，才需要为生成器增加 offset/分层位置采样。

当前三个 split 均覆盖对应 chromosome 的坐标 `0–24,576,000`。gzip SHA256 为 train `9a69cc4c839e1f1f858e1a16ada6b9cffc2624243df0a02525f356baf9bf2d1f`、val `a1be1c8d471844d00fedc18edce2c7852064d627489ba4f534864c2f392616fb`、test `4f56ed9d23bf5a958493aaf6290f4f5e2365a420dead42900825d99a25afb6f0`；逻辑解压 JSONL SHA256 分别为 `6c12899cda8630db238a2199eecf60ad0f6cd7111e260e200bc6e3c5c8a16dcf`、`05f3d9b1d836dd67d7f00e0272f63fd68428f162611fdb5b828378bf8131c65d`、`e58c9314855eccf39e35a4ef3ecca81a2745d30b94687140359e3a6d676dc4f9`。正式重建报告必须同样保存完整 hash，而不是只保存 metadata hash。

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
- 当前 self-Dfam provenance 的 exact identity coverage 为 6447/6727，另有 279 missing、1 ambiguous；该覆盖率不能自动赋给 `comparator_strict` 窗口，不能声称 family/homology-clean。
- 主 Human/Mouse/Fly binary truth 没有已验证的 biological parent/copy truth。
- Rat 与 dog 只有远端 URL，`local_source` 为空，不纳入当前计划。
- Rice RGAP7+EDTA 有 341,313 个 positive-only `rm_id` groups，可用于辅助 parent fragmentation audit，但 unlabeled space 不等于 negative，不能作 whole-genome P1 precision/F1 truth。

### 4.4 Confirmatory 数据 Gate0

最小 human confirmatory 冻结为 train `chr1/3/5/7/9` 各 600、val `chr11/13/15` 各 600、test `chr17/19/20/21/22` 各 600。提交训练前必须逐条核对：实际 chromosome 集合与配额；split 间 chromosome/coordinate 零重叠；`len(sequence)=len(labels)=end-start=8192`；label 只含 `-100/0/1`；bp 三类计数闭合且正负均非零；无重复坐标；每个 gzip、逻辑 JSONL、metadata、输入 FASTA/BED 与生成器的内容 hash。任一 chromosome 出现 N-filter 导致的非连续窗口即 Gate0 FAIL；除非先把 evaluator 改为按连续 coordinate blocks 分开计算，否则不能让它把 gap 两侧压缩成相邻序列。正式 strict test 必须读取全部 3,000 windows，并同时报告五条 chromosome 的逐条结果、chromosome macro 和 pooled counts。

该无代码重建只能称 chromosome-balanced fixed-prefix panel。若要 chromosome-wide representativeness，需要最小增加显式、8192 对齐的 coordinate offset/分层位置采样；不能用增大 `step` 模拟，因为当前 buffer 实现会使内容和记录坐标错位。

## 5. 已执行的 P1-C1

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

Boundary target：对每个连续 truth-positive reference run，训练两个通道分别预测到左/右 reference endpoint 的距离，cap=256 bp 后归一化。若 run 在窗口边缘被裁剪，或边缘相邻为 unknown，缺失一侧不参与对应 loss。

Run contrastive：

- 同一连续 truth-positive run 内的 token 是 positive；
- 不同 truth runs 是 negative；
- run 长度至少 65 bp；
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
| Human confirmatory | chromosome-balanced Human panel | 待 screen 定标 | 多 seed、多染色体机制复核 | 仅限 Human reference-run 结论 |
| identity/multispecies confirmatory | 另建 family/copy/component-safe panel | 待身份 Gate | family/homology-safe 与跨物种复核 | 是，前提是独立身份 Gate 完成 |

Smoke 成功不自动证明 C1 有信号；100-step pilot 也不能替代 800-step screen。每一级只在前一级无运行错误且没有明显机制性伤害后提交。

当前 C1 配方已在 screen 关闭，上述两个 confirmatory 均未对 C1 解锁；它们是未来某个通过 screen 的 DAPT/C2/P2 机制可复用的层级。这里的 Human panel也只能支持预定义五条 chromosome 固定前缀上的复核，不能支持 chromosome-wide representativeness。

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
- reference-run length bins：`<500`、`500–999`、`>=1000 bp`；当前 screen evaluator 尚未实现，必须作为后续只读评价补齐。

这里的 `short-fragment rate` 特指预测区间 `<80 bp` 的比例，不等于上述 reference-run 长度分层。`mean fragments per truth` 统计与每个 truth run 有任意 1 bp overlap 的预测段数，并把 missed truth 记为 0，因此必须与 missed rate 联合解释；后续还应补充仅在 detected truth 上的条件均值。`pred true-backed` 要求预测区间至少 50% 被 truth 覆盖。

以下 1–6 是本轮预注册的定量 screen 决策规则，要求同时通过；它们不是既有仓库已经确认的正式阈值。第 1/2 项是绝对差值，第 3/4 项是相对比例，第 5/6 项是绝对容忍度：

1. segment-F1@IoU0.8 相对 matched CE 至少 `+0.02`；
2. boundary-F1@5 bp 至少 `+0.02`；
3. short-fragment rate 相对下降至少 20%；
4. mean fragments per truth 相对下降至少 15%；
5. bp-F1 下降不超过 0.01；
6. missed truth rate 不超过 `CE + 0.03`；
第 7 个 `pred true-backed rate` 仅作描述性 guardrail，因为没有预注册数值阈值，不纳入 1–6 的 all-pass 判定。所有改善必须同时报告分母，排除“删除预测所以看起来更整洁”。

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

严格 DAPT 只允许使用训练染色体语料；当前 materialized panel 即 chr1。若使用 chr11、chr17、非人物种或未来 confirmatory test sequence，必须明确称为 transductive adaptation，不能与严格 held-out 比较混合。GENERanno 原始预训练语料是否已包含 HS1 或近缘 assembly 仍未知，因此即使 DAPT 有收益，也最多先解释为 domain refresh，不能默认解释为适应全新基因组。

可执行性审计确认远端 base checkpoint 注册了 `GenerannoForMaskedLM`，safetensors 中真实包含形状 `64×1280` 的独立 `lm_head.weight`，tokenizer 具有 `<mask>`（id 4），模型最大位置长度为 8192；eager attention 只扩展 padding mask，SDPA 路径也显式设置 `is_causal=False`，因此它是可继续训练的双向 MLM。当前仓库却没有 MLM dataset/collator 或 `AutoModelForMaskedLM` 的训练命令；`te_token_task.py` 中的 `wrapper_mlm` 只是抽取 MLM backbone hidden state 再训练分类 head，不能当作 DAPT。

下一实验冻结为一个窄的 MLM stage，不修改 C1：

- 只读取现有 Human HS1 chr1 train JSONL 的 `sequence`，即 3,000×8,192 bp、坐标 0–24,576,000；不读取 TE labels，也不把它称为完整 chr1；
- `add_special_tokens=False`，8192 bp=8192 tokens；15% dynamic masking，采用明确的 80% `<mask>` / 10% 随机 A/C/G/T / 10% 保持原 token；N、pad 和所有 metadata/special token 不作为 target；
- full backbone 与 MLM head，seed 42，batch 1、gradient accumulation 16、800 optimizer steps、LR `1e-5`、warmup ratio 0.1、weight decay 0.01、bf16、gradient checkpointing，固定 final checkpoint；
- 输出标准 HF MLM checkpoint、tokenizer 与单独的 `dapt_meta.json`；不能写成现有分类训练使用的 `training_meta.json`；
- 下游比较固定为 `Base→CE 800 steps` 对 `Base→DAPT 800 MLM steps→CE 800 steps`；两个 CE arm 的 classifier-head seed、数据顺序、超参数、final-step、threshold 和 strict evaluator 完全相同；加载 DAPT checkpoint 时只允许丢弃 MLM head并新建相同初始值的 token-classification score head，任何额外 backbone key 缺失直接失败。

不能直接采用 Transformers 默认 MLM collator：tokenizer 的具名 token 数少于模型 64-token vocabulary，默认随机替换可能抽到 annotation/meta tokens。原始 GENERanno 的 mask 比例、替换策略、BOS/EOS 与 reverse-complement 方案没有随 checkpoint 完整冻结，所以以上是预注册、可复现的 literal MLM recipe，而不是声称精确复现原始预训练。该比较也多用了 800 个 MLM steps；阳性只证明增加这个 DAPT stage 有价值，若要声称 MLM objective 优于等算力替代训练，仍需额外 compute control。单配方阴性只关闭这个 recipe；若 bp-F1 提高而 interval/boundary/fragmentation 不改善，仍判定没有解决 fragment 问题。

### 7.2 C2 long-context cross-window consistency

现有 4096 windows 在同一 chromosome 内连续，可组合为 8192/12288 parent loci；GENERanno 也已真实完成 8192 训练。候选设计为两个 offset 8192 views，保留 2–4 kb overlap，在 overlap 上加入 prediction JS consistency 与 representation cosine consistency。

只有在以下条件下启动：

- C1 有 interval/boundary 信号，或误差审计明确显示窗口 edge↔center disagreement 是主因；
- 单 8192-view inference 冻结，不在正式结果中用 view ensemble；
- 与 matched 8192 CE 比较，不把 context length 与 objective 同时变化后归因给其中一个。

### 7.3 P2 traditional conditioned refinement

若 C1 与按误差证据预选的第二个 P1 机制公平失败，可把资源转向 P2；这不等于穷尽所有 direct post-training。输入可包括 RM/EDTA/HiTE calls 与 FM probability/hidden evidence。最低比较矩阵：

- traditional caller alone；
- FM alone；
- traditional + 简单 deterministic refinement；
- traditional-call-conditioned learned refiner。

只有 learned refiner 同时提高严格 interval/boundary、保留 true-backed fragments，并在 low-homology candidates 上提供新增价值时才保留。MoE 只有在 experts 的互补性被测量后才进入。

### 7.4 P3 长序列种子与短 fragment 恢复

首先检验前提“长 TE 更容易准确注释”。必须在 family、divergence、nesting、fullness 和 local context 可比时做 length-stratified 分析；当前 binary JSONL 缺这些字段，所以 `<500/500–999/≥1000 bp` 只能描述 reference-run 长度，不能代表完整 TE copy 长度，也不能据此解锁 P3。

若前提成立，再测试：

`raw genome → FM high-confidence long intervals → target-derived consensus/profile → sensitive genome-wide alignment → short fragment recovery`

必须比较 long seeds 的来源：FM、HiTE、RepeatModeler2/EDTA。若 FM seed 没有提供传统工具未发现的高质量 seed，这条路线缺少核心新增价值。

## 8. 论文可发表条件

### P1 成功时

论文核心可以是：

- 揭示 DNA foundation model 的 base-to-reference-annotation-run gap；
- 提出结构感知 post-training，使 raw genome-only inference 的 interval、boundary、fragmentation 同时改善；
- 在冻结物种/同源面板上展示 inference-time library-free 的新增能力；训练监督仍来自 reference annotation，不能称训练期 library-independent。

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
| 当前 C1 配方 | 阴性，已关闭 | 不支持结构感知 C1 claim | 可补 reference-fusion 诊断解释机制，不再用同配方调参 |
| Literal DAPT 是否有额外价值 | 未测试，下一实验 | 狭义 post-training 结论 | train-chr1 MLM→matched CE 两阶段 |
| edge↔center disagreement | 未审计 | C2 是否解锁 | 固定 checkpoint 的位置分层只读评价 |
| 长完整 TE 是否本质更易注释 | 未证明且当前资产不足 | P3 解锁 | 重建带 copy/fullness/divergence/nesting 的匹配资产 |
| family-disjoint 泛化 | 阻断 | novel-family/generalization claim | 重建 family/copy/component identity |
| Human 五染色体 fixed-prefix 复核 | 尚未构建 | 未来通过 screen 的机制复核 | 600/chrom balanced panel + continuity Gate |
| Human chromosome-wide 泛化 | 阻断 | publication-level Human claim | 增加 coordinate offset/分层位置采样并冻结代表性 panel |
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

### 10.1 Smoke 与运行修正

所有作业均经 SSH 在 Baobab 上提交，并只使用项目的 `smart-sbatch` 规则做资源与路径守门；未采用远端 `AGENTS.md` 的其他工作流。

| job | profile / arm | 结果 | 用途 |
|---|---|---|---|
| `12059508` | smoke CE/C1 array | 两臂均完成，约 5 分 27 秒 | 验证训练、保存与 strict evaluator 全链路 |
| `12059535_1` | vectorized C1 smoke | 完成，3 分 56 秒 | 排除 run-geometry Python 循环为主要瓶颈 |
| `12059546_1` | final hook-path C1 smoke | 完成，1 分 25 秒 | 恢复单次标准 backbone forward；2 steps 训练约 31 秒 |

最终实现通过 classifier forward pre-hook 捕获标准 forward 中送入 `score` 的 hidden state，梯度仍连接 backbone，并在每次 forward 后立即移除 hook。8192 bp→8192 token 几何、无 BOS/EOS、保存重载和 8-window strict evaluation 均通过。早期直接调用 base model 的版本虽然正确，但约 80 秒/optimizer step，不用于后续实验。

### 10.2 100-step directional pilot

Slurm array `12059558` 的 CE/C1 两臂均以 exit code 0 完成，耗时分别 28 分 21 秒和 28 分 42 秒。评估是 test 文件前 300 个窗口，全部位于 chr17；这是方向性 pilot，不是跨染色体或论文级结果。

固定 `raw_threshold=0.5`、IoU=0.8、boundary tolerance=5 bp 的结果：

| 指标 | matched CE | C1 | C1−CE / 相对变化 |
|---|---:|---:|---:|
| bp-F1 | 0.91683 | 0.91183 | −0.00500 |
| bp TP / FP / FN | 1,070,208 / 125,721 / 68,436 | 1,079,926 / 150,132 / 58,718 | recall 上升、FP 同时上升 |
| segment-F1@IoU0.8 | 0.16774 | 0.18983 | +0.02209 |
| segment TP / FP / FN | 1,364 / 11,242 / 2,293 | 1,105 / 6,880 / 2,552 | TP −259，FP −4,362 |
| boundary-F1@5 bp | 0.07551 | 0.06477 | −0.01074 |
| boundary hits / pred / truth | 614 / 12,606 / 3,657 | 377 / 7,985 / 3,657 | hits −237 |
| predicted segments | 12,606 | 7,985 | −36.7% |
| short predictions / all predictions | 10,232 / 12,606 | 5,865 / 7,985 | rate 相对 −9.5% |
| fragment overlaps / truth runs | 5,699 / 3,657 | 4,737 / 3,657 | mean 相对 −16.9% |
| split truth / truth runs | 540 / 3,657 | 383 / 3,657 | rate 相对 −29.1% |
| missed truth / truth runs | 180 / 3,657 | 185 / 3,657 | rate +0.00137 |
| true-backed / predictions | 4,196 / 12,606 | 2,909 / 7,985 | rate +0.03145 |
| median boundary error | 4.0 bp | 5.5 bp | +1.5 bp |

两臂看到完全相同的 11,228,860 个 boundary targets、143,944 个 contrastive anchors 和 18,015 个合格 truth runs。C1 的 boundary loss 均值相对 matched compute-control 下降约 49.5%，contrastive loss 均值下降约 20.8%，说明两个辅助目标被优化；CE 中权重为 0 的 boundary head 本身不训练，因此这个差异不能单独证明 backbone 表示改善。是否改善最终表示或 reference endpoints 只能由独立评价指标判断。

该结果是明确的 mixed signal：C1 大幅减少预测碎片和 segment FP，使 segment-F1 上升；同时严格 segment TP、boundary hits 和 boundary-F1 下降。现有 TSV 没有保存 false-fusion/overmerge 的逐实例计数，因此“C1 正在过合并”只是与现象一致的推断，不能写成已证实事实。

独立审计据此建议停止当前配方；主流程仍将其晋级 800-step screen，理由是 100-step pilot 的学习率已经衰减到零，并不是 800-step schedule 的中间 checkpoint，而且 bp-F1、missed truth 与 fragment 指标没有灾难性失败。这个分歧由 screen 裁决：若更充分训练后仍表现为“碎片更少但边界更差”，当前 C1 配方关闭，不通过调参重命名为成功。

### 10.3 800-step screen

Slurm array `12059660` 两臂均以 exit code 0 完成：CE（task 0）3:27:17，C1（task 1）3:26:00。两臂使用 A100 80GB、seed 42、相同 Human HS1 8192 数据与固定 final-step checkpoint；训练、保存重载和 strict status 均通过。实际 test 文件全部来自 chr17，因此 1,200-window strict screen 只是 chr17 坐标前缀，不是多染色体或随机 Human test。

固定 `raw_threshold=0.5`、IoU=0.8、boundary tolerance=5 bp 的结果：

| 指标 | matched CE | C1 | C1−CE / 相对变化 |
|---|---:|---:|---:|
| bp-F1 | 0.93408 | 0.93081 | −0.00327 |
| bp TP / FP / FN | 4,621,832 / 370,152 / 282,179 | 4,632,177 / 416,796 / 271,834 | TP +10,345，FP +46,644 |
| segment-F1@IoU0.8 | 0.32967 | 0.33260 | +0.00293 |
| segment TP / FP / FN | 7,483 / 23,661 / 6,770 | 6,908 / 20,379 / 7,345 | TP −575，FP −3,282 |
| boundary-F1@5 bp | 0.19552 | 0.18170 | −0.01382 |
| boundary hits / pred / truth | 4,438 / 31,144 / 14,253 | 3,774 / 27,287 / 14,253 | hits −664 |
| predicted segments | 31,144 | 27,287 | −12.38% |
| short predictions / all predictions | 19,917 / 31,144 | 16,536 / 27,287 | rate 相对 −5.24% |
| fragment overlaps / truth runs | 20,222 / 14,253 | 18,935 / 14,253 | mean 相对 −6.36% |
| split truth / truth runs | 2,375 / 14,253 | 2,076 / 14,253 | rate 相对 −12.59% |
| missed truth / truth runs | 849 / 14,253 | 794 / 14,253 | rate −0.00386 |
| true-backed / predictions | 16,839 / 31,144 | 14,981 / 27,287 | rate +0.00833 |
| matched mean IoU | 0.95911 | 0.95447 | −0.00464 |
| median boundary error | 2.0 bp | 2.5 bp | +0.5 bp |

六项预注册 gate：

| gate | 要求 | screen 观察值 | 结果 |
|---|---:|---:|---:|
| segment-F1@0.8 | 绝对 `≥CE+0.02` | +0.00293 | FAIL |
| boundary-F1@5 | 绝对 `≥CE+0.02` | −0.01382 | FAIL |
| short-fragment rate | 相对下降 ≥20% | 5.24% | FAIL |
| mean fragments/truth | 相对下降 ≥15% | 6.36% | FAIL |
| bp-F1 | 下降 ≤0.01 | 下降 0.00327 | PASS |
| missed-truth rate | `≤CE+0.03` | 比 CE 低 0.00386 | PASS |

定量结果为 **2/6 PASS**；描述性的 pred true-backed guardrail 略有改善。两臂看到完全相同的 89,611,584 个 boundary targets、1,145,808 个 contrastive anchors 和 143,392 个合格 runs。C1 的 boundary auxiliary loss 均值从 0.37579 降至 0.04826，SupCon 从 5.00864 降至 2.76714，说明辅助目标被优化；它们没有转化为更好的最终 reference endpoints。

C1 的预测正 bp 增加约 1.14%，预测区间减少 12.38%，严格 segment TP 减少 7.68%，boundary hits 减少 14.96%，matched IoU 与 boundary error 同时变差。这与 over-connection 倾向一致，但当前 TSV 没有显式 false-fusion 计数，且没有 biological copy truth，不能把它报告成已证实的 copy-level overmerge rate。

**决策：关闭当前 C1 配方。** 不晋级 multi-seed、balanced-Human confirmatory 或跨物种实验，也不通过微调两个 loss 权重把同一机制包装成新方向。保留该结果作为“辅助目标可被优化，但少量 fragmentation 改善不足且伤害 boundary”的阴性机制证据。单 seed、单 chr17 fixed-prefix 的阴性 screen 只关闭这个具体配方，不关闭 literal DAPT、证据条件下的 C2 或整个直接注释 P1。
