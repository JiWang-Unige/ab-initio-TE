# TE-Refiner 研究路线重构 v5（refinement-focused）

> 版本 v5.0 · 2026-06-14 · 继承并收窄 v4_NatureMethods
> 核心 pivot：从 v4 的"重新定义整个 TE annotation framework"收窄为
> **"对 RepeatMasker 已检测的长 TE 区域做 content-aware refinement"**。
> 严格边界：**不是 full-length TE defragmentation，不做 novel discovery，不做进化全长重建。**

---

## 0. 核心战略判断

三套定位三选一：
- A. v4 完整 framework（含 novel discovery / open-family / full de novo）→ ❌ 太重，踩 TE_final 全部雷区。
- B. zero-human transfer + PU 弱监督（M0/M1/M2 已跑）→ ⚠️ transfer 协议保留；PU 已被 M2 自证伪。
- C. **RM-conditioned TE annotation refinement** → ✅ 最强主线。

为什么 C 最强：它把 TE_final 每个负结果都变成正资产
- bp-F1 饱和 → 我们不打 bp-F1，打 boundary/segment（唯一未饱和瓶颈）
- CRF/HMM 无效 → 全新 FM-conditioned 机制，以两参后处理为必过 baseline
- novel discovery 证伪 → 不做 discovery，不碰陷阱
- "DL 超传统工具"证伪 → 精修 RM 而非替代 RM，死亡 claim 消失
- PU 效果差 → corrupt-recover 自监督，不依赖"未注释=负"
- RM circularity → GT 是已知 clean 版本，corruption 可控，逃出循环
- dm6 跨协议翻车 → refinement 是 within-protocol，天然不需跨协议比较

---

## 1. 主线一句话

TE-Refiner：序列基础模型驱动的、跨物种零人类泛化的 TE 注释精修框架。
给定任意 de novo 工具的粗注释，以"原始注释 + 基因组序列"为联合输入，
输出边界更准、内部更连续、碎片更少的精修注释；核心是 content-aware learned
refinement 系统性超越 content-agnostic 规则后处理，并在无人类标签条件下泛化到人类。

核心科学问题：TE 注释瓶颈已不是检出（bp 饱和 0.94），而是成形（边界/断裂/碎片，
segIoU 仅 0.07-0.67）。一个学到 TE 序列语法的 FM 能否在不依赖物种特异标签、
不依赖人类标注下，把任意工具粗注释精修成生物学可用注释？

---

## 2. 五大贡献

- C1 方法：RM-conditioned refinement 架构（原始注释作 soft-mask/family-prior 输入通道 + refine head）
- C2 范式：corrupt-recover 自监督，绕开 PU 与 circularity
- C3 数据：7+ 物种 harmonized weak-label + refinement benchmark（corrupt 高置信注释测恢复）
- C4 评价：分层 refinement metric（ΔsegIoU/Δboundary/fragmentation/over-merge）+ 多 reference regime
- C5 泛化：zero-human transfer + 系统发育衰减曲线

灵魂对照（证 FM 必要性，可证伪）：
- 对照 A 必输：threshold×min_len×merge_gap 规则后处理（content-agnostic）
- 对照 B 对照：EarlGrey BEAT defrag（library-based）
- 我们必赢：TE-Refiner（content-aware，看 gap/边界两侧真实序列）
- 若赢不过两参后处理 → FM 必要性证伪（一周内可初判）

---

## 3. 任务定义与边界

- 任务名：TE annotation refinement（boundary correction / gap repair / fragment consistency correction）
- 输入：基因组序列 8192bp + 原始粗注释（RM raw，作条件通道）
- 输出：精修 TE intervals（refined boundary + gap 修补 + 碎片合并）
- 直接预测：per-base refined p_TE + boundary-shift + fragment-link score
- 算成功：vs 原始 RM，segIoU@0.5↑ / boundary err↓ / fragmentation↓，且赢过两参后处理，且 zero-human transfer 不崩
- 不属于本项目：判全长真实性 / 进化全长重建 / novel family discovery / 替代 RM 从头注释 / 机械拼接成"完整 TE"

术语红黑榜：
- ✅ refinement / boundary correction / RM-conditioned / reference-reproduction
- ❌ full-length defragmentation / reconstruction / novel TE discovery / "DL outperforms RM" / biological ground truth

---

## 4. 数据与标签

- RM 双重角色：raw RM=条件输入（被精修对象）；RM 高置信∩Dfam-confirmed=clean GT 来源
- 不全量重跑 pipeline；用已有 UCSC/RM track（7 物种就绪）；1-2 pilot 跑标准化 RM 作 evidence regime
- harmonize 只到 order/superfamily（LINE/SINE/LTR/DNA/Helitron），剔 unknown，不做 token-level family
- unknown/未注释 → ignore（不当负类，PU 教训）
- 必存记录：species_manifest / harmonization_rules(版本化) / corruption_recipe / chunk_index / env+command+sha256
- 小规模 pilot 先行（hs1 + 2-3 近域动物），证明范式再扩

---

## 5. 主指标（继承 TE_final METRIC_CONTRACT）

- 主：ΔsegIoU@0.5 提升 + Δboundary_error(bp) 下降 + fragmentation rate 下降 + over-merge penalty
- bp-F1 永不做 headline（夸大边界质量 1.3-11×）
- 强制 metric_level 列（防混指标式翻车）
- 多 reference regime：RM-derived / RM-free structural-union(W11) / Dfam-confirmed
- 近域脊椎动物（bosTau/galGal/xenTro）作诚实主战场（segIoU 0.4-0.6，不 0 不饱和）

---

## 6. 并行推进

- MVP（Week1）：旧 GENERanno N3 ckpt + oracle refinement vs 两参后处理，1 近域物种，CPU，出 go/no-go
- Branch M（主线）：corrupt-recover refiner，必赢两参后处理
- Branch B（并行·基线/数据）：两参后处理 + EarlGrey baseline 全物种 + benchmark 构建
- Branch C（并行·泛化/审计）：zero-human transfer + RM-free reference 多 regime
- 重 pipeline（de novo / 大基因组）永远并行证据轨，绝不阻塞主线
- 砍掉：novel discovery / open-set family / PU full transfer / token-level family
- 暂缓：full de novo 全物种 / 长 context 全量 / family classifier

时间线：W1 MVP → W2-3 corrupt-recover 样本+首训 → W3-4 baseline 全物种 → W4-6 transfer+RM-free → W6-8 ablation+case → W8-10 多 seed+figure

---

## 7. 下一步执行清单

1. [P0] corruption_recipe.yaml + make_refinement_samples.py（4 类 corruption）
2. [P0] E0 MVP oracle_refine_eval.py（旧 ckpt logits，复用 threshold_gap_sweep.py）
3. [P0] 迁移 TE_final 评估器（F5_segment_iou / threshold_gap_sweep / eval_segment_iou_purepython）+ 固化 metric_level
4. [P1] build_refinement_benchmark.py（RM 高置信∩Dfam corrupt 作标准评测集）
5. [P1] rm_free_reference.py（复用 W11，structural-union，纯 CPU 防 circularity）
6. [P1] train_te_refiner.py（M0 框架 + RM-condition 输入 + refine head，先 hs1 in-domain）
7. [P2] 数据补齐（bosTau/galGal/xenTro 近域 case；mouse de novo OOM 缓做）
8. [P2] 落盘方案进 docs/11/12/14 + 修订 ACTIVE_GOAL（primary=transfer_segIoU_at_0.5_macro_species）

---

## 8. 可复用资产（路径已核实）

- TE_final 评估器：/home/users/j/jwang/TE_final/scripts/{threshold_gap_sweep.py, eval_segment_iou_purepython.py, F5_segment_iou.py}
- TE_final METRIC_CONTRACT.md（四级 metric 冻结口径 + forbidden claim patterns）
- TE_final W11/W12/U2 audit 脚本（circularity 拆解）
- GENERanno N3 checkpoint（hg38 3-seed，te_f1 0.9445，warm-start）
- 当前项目 M0 模块化训练框架（可换 backbone/head，PU+ignore-mask loss，染色体 split，check_data）
- 已就绪 7 物种 harmonized weak labels（hs1 + A-6 动物）

---

## 9. 期刊定位（务实）

- 理想：Nature Methods（需 framework + 全 transfer + 多 regime audit + usability + case）
- 现实 backup：Genome Biology / NAR Genomics & Bioinformatics / Bioinformatics（tool+benchmark）
- 若 transfer 崩或增益小 → 主动降级，不为 NM 强行扩不可控实验（TE_final Gate 4 教训）

---

## 10. 风险登记（待 Critical Reviewer / council / tri-review 补强）

- R1 corruption 分布失配：人工 corruption ≠ 真实 RM error，模型可能只学逆人工 corruption
- R2 增益太小：RM 在清晰 LTR 本就好、在 fossil 本就差且 GT 不可信，可改善的中间地带可能窄
- R3 circularity 是否真绕开：clean GT 仍源自 RM 高置信区
- R4 期刊档位现实性待诚实评估
（这些由后续对抗审查闭合，见对话记录）

---

## 11. 决策记录与 Step 0 执行规格（2026-06-14 用户拍板）

### 11.1 决策记录（Decision Log）
- **D-001 期刊定位**：首要目标诚实降级到 **Genome Biology / NAR GAB**；Nature Methods 作为补足 downstream biological impact(C6) 后的 stretch goal。Reason：批判审查判定"把 RM 修准一点"是已有生态增量改良，非新范式，NM 高估约一档半。Rollback：若 C6 downstream 证据扎实改变真实生物学结论，可重瞄 NM。
- **D-002 审查方式**：不跑外部 council/tri-review；以内部 Devil's Advocate 对抗审查为准（已覆盖 comparability/validity/circularity/期刊/过度设计/更快路径六维）。Rollback：主线重大变动或 claim 前可补外部三方。
- **D-003 主线收窄**：MVP 砍掉 RM-condition 输入 + zero-human transfer，先做 unconditioned + 同物种 held-out chr；conditioning/zero-human 降为后续 ablation。Reason：避免三个未验证假设捆成一个赌注、失败无法归因。
- **D-004 范式头号风险**：corrupt-recover 分布失配（人工 corruption ≠ 真实 RM error）升级为头号风险；validity 验证（真实"RM 粗→专家精修"配对）须前置为 Step 0。

### 11.2 Step 0 执行规格（1 周 · 零 GPU · 烧算力前证伪）

| 实验 | 输入 | 方法 | 输出 | 红灯判据 | 复用 |
|---|---|---|---|---|---|
| **F0.1 中间地带宽度** | RM raw intervals(hs1 rmsk) + Dfam-confirmed intervals | 每个 RM TE seg 与最近 Dfam-confirmed seg 算 boundary error + segIoU；"可改善 loci"=boundary err≥X bp 且 Dfam 边界可信 | 可改善 loci 占全 TE 比例 + 分布直方图 | **< 10–15% → headline 破产** | bedtools closest/intersect + pandas |
| **F0.2 真实 error 画像** | F0.1 的 RM-vs-Dfam 配对 | 按 error 类型(boundary shift 方向/幅度 / fragmentation / over-merge)统计；叠加人工 corruption 算子参数分布 | error 类型直方图 + 与 corruption recipe 重叠度 | 重叠度低 → validity 预警 | pandas |
| **F0.3 两参后处理地板** | RM raw + clean reference | refinement 指标(segIoU/boundary)上 grid threshold×min_len×merge_gap 找最佳 | 必须严格超越的地板 ΔsegIoU | 两参后处理已吃掉大部分空间 → DL 边际收益小 | TE_final threshold_gap_sweep.py |

### 11.3 数据就绪现实（启动前必须解决）
- 当前项目顶层 data/outputs/reports/runs 全空（新框架壳）。
- 真实弱标签：`.backup/data/typed_labels/`（本地可见，需验证内容）+ 集群 BeeGFS `/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/`（cluster-only）。
- **M1 Dfam-confirmed 审计产物本地不可见 → 启动 F0.1 前须 `ssh baobab` 定位**（这是 F0.1/F0.2 命门）。
- Step 0 是轻量 bedtools+pandas，按 §12 豁免可在登录节点/本地跑，前提数据可达。

### 11.4 新增贡献 C6 与头号 open question
- **C6 downstream biological impact**（上冲 NM 唯一钥匙）：证明精修后注释改变真实生物学结论（TE age 分布 / TE-gene 调控 / family expansion 史）。
- **Open Q（validity 命门，未解决）**：真实"RM 粗注释→专家精修"金标准配对去哪找？候选 = Dfam curated 独立 HMM hits / 社区手工 curation / 模拟基因组已知插入。

