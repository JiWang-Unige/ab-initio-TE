# 注释修订与Unknown：首轮实际结果

2026-09-14。执行依据为用户允许公开推送并要求按Pro收敛方向推进。
本轮有真实的同组装注释差异与历史ontology诊断；尚无新模型FP rescue结果。

## 小鼠 mm10：候选可继续，但 Current 不是单调增加的真值

Baobab job **12693564** 完成，耗时1分50秒，MaxRSS约6.69GiB。
读取[UCSC官方mm10数据库](https://hgdownload.soe.ucsc.edu/goldenPath/mm10/database/)的
`rmskOutBaseline`与`rmskOutCurrent`实际完整表，在固定canonical chr1–19/X/Y/M上比较。
17列SQL字段已核实；数据库坐标使用0-based half-open。

| 比较范围 | Baseline bp | Current bp | 两者共有 bp | Baseline独有 bp | Current独有 bp |
|---|---:|---:|---:|---:|---:|
| 明确TE类 | 1,086,969,162 | 1,082,662,042 | 1,076,537,556 | 10,431,606 | 6,124,486 |
| TE及Unknown/模糊TE | 1,090,067,540 | 1,085,659,829 | 1,079,533,544 | 10,533,996 | 6,126,285 |
| 所有repeat | 1,185,346,433 | 1,180,589,950 | 1,174,546,941 | 10,799,492 | 6,043,009 |

明确TE为SINE/LINE/LTR/DNA/RC/Retroposon，模糊分类单列；不同scope中分类变化可改变差值。
包含的原始记录为5,239,911和5,225,425；按坐标、方向、name/class/family规范化并保留重复次数后，
4,741,333条共同，498,578条仅Baseline，484,092条仅Current。此处记录不是insertion数；
ID、alignment score、consensus offset变化不作为标签identity变化。

**判断：** mm10确实有非零TE注释变化，值得做模型候选的后续对照；但Current的TE覆盖反而较少，
不能预先称其更完整、也不能只统计旧FP转TP。后续必须同时保留新增、删除、分类改变与未解分母。
后续已从[官方关联track](https://genome.ucsc.edu/cgi-bin/hgTrackUi?c=chr1&db=mm10&g=joinedRmsk)
读到Baseline标为RepeatMasker v3.0.1 / db20100302，Current标为v4.0.7 / Dfam_2.0。
这证明软件与库均变动；完整运行命令、具体搜索引擎和原始表生成参数仍未核实，不能作为library-only干预。当前实跑记录状态为
`MATERIAL_CHANGES_PRESENT_PROVENANCE_OPEN`，尚不是same-engine library-only对照或独立真值。

证据：[result.json](../../reports/ANNOTATION-REVISION-20260914/mm10/result.json)、
[逐染色体表](../../reports/ANNOTATION-REVISION-20260914/mm10/per_chrom.tsv)。
区间并集、重叠及bookended坐标的2项测试通过；原始约300MB压缩表留在Baobab，无需进入Git。

## Unknown：先解释ontology，再检验重新分类

只使用已经归档的human chrX `unknown_annotation`行，未加入chr19–22、chr16/18或任何新标注。
从历史代码直接抽取纯函数`map_sf5`重算，90行全部匹配原Unknown标签：

| 原始taxonomy | fragments | 映射原因 |
|---|---:|---|
| Retroposon / SVA | 83 | 明确命名但不属于原四类 |
| RC / Helitron | 2 | 明确命名但不属于原四类 |
| LTR? / LTR? | 4 | 原始分类有不确定标记 |
| DNA? / hAT-Tip100? | 1 | 原始分类有不确定标记 |

85/90是命名类别被旧标签合同合并进Unknown，5/90是模糊注释。
这不是全260片段或全基因组的误注率，也不是模型正确改类的比例；本审计没有读取模型预测来决定分类。
SVA的复合retroposon属性已有[原始研究](https://doi.org/10.1016/j.jmb.2005.09.085)支持；
因此SVA片段被预测为DNA/LTR本身不能证明其family被正确恢复。

**收敛：** 保留旧六类指标。新增审计先按`named_non_main4_taxon`、ambiguous和真正无分类拆开；
对独立审阅样本保留原family与复合结构，不用模型自己给出标签再证明自己正确。
本次不能把Unknown现象统一归因为人工注释不足。

证据：[unknown_result.json](../../reports/ANNOTATION-REVISION-20260914/unknown/unknown_result.json)、
[逐项表](../../reports/ANNOTATION-REVISION-20260914/unknown/unknown_chrx_audit.tsv)。

## 人类后续

新GLM任务实验见[固定hg19 chr1协议](HG19-CHR1-REVISION-20260914.md)。
T2T2022原生注释与四个双向chain来源已固定；获取资源不读取label行、不计算rescue。
只有旧预测和CAL冻结后，才在允许评价区域开展映射、序列一致性及新支持审计。

T2T资源获取作业12695221已于43秒完成：2022Apr14原生annotation和4个chain共535,331,432 bytes，实际[获取记录](../../reports/ANNOTATION-REVISION-20260914/chm13_acquisition.json)已归档。没有解析新的label行或计算映射/rescue。
