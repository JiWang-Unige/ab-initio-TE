# 外部P3/Tiberius：完整200-cell结果

2026-09-16取回；最终score12740044为COMPLETED，exit0:0，35秒。40/40core状态COMPLETED、五臂200/200原生调用全部成功；相同序列大写字符、完整lineage库导出、native模型实际调用与encoding观察均通过。score在全量资格检查之后解析并比较每臂GTF/GFF3的一致性再计分；没有丢弃困难core。

**结论：固定人类P3 mask在两外部哺乳动物上提高了相对无mask对照的注释一致性；预定P−R_TE主比较在两者都未建立优势。各比较仍有原正确locus损失，不能声称低损失部署已通过。**

## 分母与模型

牛ARS-UCD2.0（GCF_002263795.3）、鸭嘴兽mOrnAna1.pri.v4（GCF_004115215.2），每种最长十条常染色体各2个固定5Mb core及100kb halo，共200Mb评价核心、208Mb含上下文输入。参考gene loci为牛470、鸭嘴兽639；是assembly-matched NCBI注释相对CDS-chain/locus一致性，不是独立实验真值。

P来自GENERanno系列人类P3，窗口8192、阈值0.5，**不是**共享NTv2 D。U_soft/P/R_TE/R_all共用softmask-aware Tiberius checkpoint；U_nosm采用官方nosm checkpoint，因此P−U_nosm是完整流程比较，P−U_soft才隔离同checkpoint mask输入。R_TE/R_all来自同次RepeatMasker4.2.4和完整Dfam3.9 lineage curated+uncurated注释。

## 实际计数

| 物种 | 输入 | TP | FP | FN | Precision | Recall | locus F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| cow | U_soft | 272 | 501 | 198 | 0.351876 | 0.578723 | 0.437651 |
| cow | U_nosm | 285 | 284 | 185 | 0.500879 | 0.606383 | 0.548604 |
| cow | P | 307 | 219 | 163 | 0.583650 | 0.653191 | 0.616466 |
| cow | R_TE | 309 | 222 | 161 | 0.581921 | 0.657447 | 0.617383 |
| cow | R_all | 305 | 223 | 165 | 0.577652 | 0.648936 | 0.611222 |
| platypus | U_soft | 381 | 347 | 258 | 0.523352 | 0.596244 | 0.557425 |
| platypus | U_nosm | 358 | 348 | 281 | 0.507082 | 0.560250 | 0.532342 |
| platypus | P | 408 | 338 | 231 | 0.546917 | 0.638498 | 0.589170 |
| platypus | R_TE | 408 | 332 | 231 | 0.551351 | 0.638498 | 0.591733 |
| platypus | R_all | 405 | 329 | 234 | 0.551771 | 0.633803 | 0.589949 |

## 配对效应与局部损失

每物种以十条染色体为cluster，同时重采样同一染色体两个core；10,000次，seed42，全部有效。以下区间是该面板内空间重采样范围，不是跨物种/初始化重复。gain/loss是相对该行对照的正确locus集合变化。

| 物种 | 比较 | ΔF1 | 95%区间 | Gain | Loss | 原正确locus损失 |
|---|---|---:|---|---:|---:|---:|
| cow | P_minus_U_nosm | +0.067861 | [+0.028046, +0.116576] | 53 | 31 | 10.88% |
| cow | P_minus_U_soft | +0.178815 | [+0.147761, +0.207924] | 42 | 7 | 2.57% |
| cow | P_minus_R_TE | -0.000917 | [-0.020464, +0.016219] | 8 | 10 | 3.24% |
| cow | P_minus_R_all | +0.005243 | [-0.013072, +0.021741] | 10 | 8 | 2.62% |
| platypus | P_minus_U_nosm | +0.056828 | [+0.028078, +0.082591] | 90 | 40 | 11.17% |
| platypus | P_minus_U_soft | +0.031745 | [+0.005494, +0.061528] | 51 | 24 | 6.30% |
| platypus | P_minus_R_TE | -0.002563 | [-0.015224, +0.009415] | 12 | 12 | 2.94% |
| platypus | P_minus_R_all | -0.000779 | [-0.017195, +0.015063] | 15 | 12 | 2.96% |

P−U_nosm和P−U_soft区间在两个物种均为正；P−R_TE和P−R_all区间均跨0。不能把无显著差异写成等效/非劣，因为没有预定等效/非劣界限。相对R_TE，牛gain8/loss10，鸭嘴兽gain12/loss12；两者平均F1略低于R_TE，结果不支持替代RM的优势。

全部四个对照的原正确locus损失比例在两物种均超过1%。这记录精确CDS链匹配的得失，不能直接称生物学基因被删除。原人类16/510=3.1373%、1%门失败保持不变，外部结果不会回写该门，也不把平均提升当作低损失验收通过。

## 参考支持分层

牛有220个含NM转录本的loci，U_soft/U_nosm/P/R_TE/R_all的该子集recall为0.650000/0.695455/0.736364/0.740909/0.736364。鸭嘴兽NM子集为0，五臂均为null，不填零。该分层只报recall，不用完整预测FP计算无效的子集precision。NM存在亦不意味着当前全部isoform均人工实验确认。

## 来源与验证范围

[固定协议](../../../docs/experiments/P3-TIBERIUS-EXTERNAL-20260915.md)；[正式结果](result.json)；[40core/200cell资格元数据](completion-qualification.json)；[紧凑计数复核](compact-recheck.json)。本机独立累加per-core TP/FP/FN、复算F1并核对正确locus/gain/loss集合通过；没有把该复核说成第二次native GTF解析或bootstrap重跑。原生GTF/GFF3、序列和模型保留Baobab。

初始smoke和full/score取消、各工程恢复记录保留。最新score替代了被UID0取消的12732548，未改模型或科学评分。旧scope只授权cow P3/Tiberius，不解封共享D cattle。

本预定外部实验的执行、评分与结果解释已经完成。无需因主比较未优于RM而追加阈值、core、物种或训练；把正向流程效用、未建立RM优势和局部损失共同纳入稿件。
