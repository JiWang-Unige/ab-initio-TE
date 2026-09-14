# 固定 P3 mask 的 Tiberius 下游效用：最终结果

2026-09-15（Europe/Zurich）。全部 20 core × U/P/R 共 60 格原生推理完成，固定评分和独立 CDS 复算通过。**平均效用改善，但预先规定的四项联合门未通过。** 不将门未通过改写为“没有效用”，也不将平均增益改写为“低风险部署已经达标”。

## 结果与决定

同一 hg38 chr16/18 固定面板包含 726 个 Curated RefSeq gene-locus units。U 为无 mask，P 为固定 P3-R1 TE mask，R 为 UCSC 全 repeat mask。计数依据 native CDS 链与参考允许 isoform 的精确匹配；一个 locus 最多计一个 TP，未匹配的独特预测链计 FP。

| 输入 | TP | FP | FN | Precision | Recall | Locus F1 |
|---|---:|---:|---:|---:|---:|---:|
| U | 510 | 367 | 216 | 0.581528 | 0.702479 | 0.636307 |
| P | 549 | 295 | 177 | 0.650474 | 0.756198 | 0.699363 |
| R | 548 | 302 | 178 | 0.644706 | 0.754821 | 0.695431 |

| 比较 | F1 差 | 95% 配对区块 bootstrap 区间 | Recall 差 | 新增 / 丢失正确 locus |
|---|---:|---|---:|---:|
| P−U（主比较） | +0.063056 | [0.036503, 0.106832] | +0.053719 | 55 / 16 |
| R−U | +0.059125 | [0.029941, 0.100812] | +0.052342 | 55 / 17 |
| P−R | +0.003932 | [−0.002606, 0.013370] | +0.001377 | 3 / 2 |

区间来自预先固定的 20 个 core 配对重抽样（10,000 次，seed 20260908）。它描述这个面板的区块不确定性，不是跨物种、全基因组或预训练独立性区间。P−R 区间跨零，不支持优势或等效结论。

| 冻结门 | 观测 | 通过 |
|---|---|---|
| F1 增益 ≥0.01 | 0.063056 | 是 |
| F1 增益区间下界 >0 | 0.036503 | 是 |
| Recall 差 ≥−0.005 | 0.053719 | 是 |
| 丢失 U 正确 locus 比例 ≤1% | 16/510 = 3.1373% | **否** |

最终决定为 `P3_BASE_MASK_UTILITY_GATE_NOT_MET`：依照原协议停止这个固定 P3+Tiberius 效用问题，不追加 seed、阈值、checkpoint 或面板搜索。P 新增 55 个正确 locus、丢失 16 个，净增加 39 个；平均召回改善不能替代对既有正确预测丢失的约束。P 相对 U 另有 148 个新 unmatched prediction signatures，不能把总 FP 降低解读为每一个预测均改善。

## 完整性与修复记录

- 全量作业 12694349 完成，9小时49分37秒，退出 0；不把包含 mask 准备的整个用时作为 Tiberius 单独推理速度。
- 原评分 12696406 在5秒后失败：聚合器把派生 precision/recall/F1 也加进 Counter，chr16:5 无参考 locus 的 recall 为 null，触发类型错误；尚未生成科学结果。
- 修复仅将汇总限制为 TP/FP/FN，再计算 pooled ratios。新增整轮汇总回归覆盖无参考 core 的 FP 保留；共9项本地测试通过。原输入、模型、阈值、分割和全部60格预测均复用。
- 修复评分及独立复算 12710872 完成，10秒，退出0。独立解析 native GTF/GFF3，重算每 core/总体计数、三项差值、gained/lost、bootstrap 和四门，均与主结果一致。
- 20个 preflight 均确认三臂的前五个通道一致，60个原生观测均通过，U mask 为零，P/R mask 非零。配置与冻结配置逐字段一致。chr16:5 的 U/P/R FP 为12/10/11，保留在总分母；该 core 的 recall 为 N/A。

`STATUS` 和 `status.json` 保留其推理完成及早期准备阶段的原始记录。当前完成证据以 [result.json](result.json)、[independent_recheck.json](independent_recheck.json)、[verification.json](verification.json) 和 [execution.json](execution.json) 为准；不能用较早的阶段标记否定后续评分已经完成。

## 论文边界

这是固定模型、固定面板的输入效用结果，可用于说明 TE-associated material mask 能改善总体基因注释一致性，同时仍有局部损失。它不证明 biological insertion 恢复、gap 修复、独立序列/家族/物种泛化，亦不意味着整个 TE 模型不可用。R 使用外部 repeat library。GENERanno 预训练精确坐标未知，`claim_eligible=false` 的边界保持原协议。

原始序列、逐碱基数组、权重及 native 注释仍在 Baobab；此目录仅保存紧凑结果、输入观测及作业证据。详见[冻结协议](../../../docs/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1.md)和[图及图注](../../../docs/manuscript/20260914/figures/tiberius-base-mask-utility-caption.md)。
