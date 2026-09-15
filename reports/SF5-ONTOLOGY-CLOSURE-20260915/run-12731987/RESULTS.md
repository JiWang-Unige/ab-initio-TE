# SF5 本体闭合结果（Slurm 12731987）

## 结论

本实验已完成，且覆盖了协议规定的全部数据：5,400 个 TRAIN 窗口、1,440
个完整 VAL 窗口和 2,160 个完整 TEST 窗口；六个物种在每个 split 中分别有
900/240/360 个 4,096 bp 窗口。它修复了历史 SF5 只评分前 1,200 个窗口的覆盖
问题，适合作为“完整六物种、显式区分未解析注释状态”的描述性结果。

该结果仍然是相对于现有 `comparator_plus_unknown` 注释的分类结果。`BG` 表示
该比较器没有覆盖，不能当作经独立实验确认的非 TE；`KNOWN_OTHER_TE`、
`AMBIGUOUS_TE` 和 `UNCLASSIFIED` 也不是独立生物学真值。因此本实验不能单独
证明 family/superfamily 注释、biological insertion recovery 或所有物种的普适
泛化。

## 固定协议和分母

- seed 42，GENERanno-eukaryote-0.5b-base 初始化；900 steps，batch 1、gradient
  accumulation 16、learning rate `2e-5`，完整 VAL 选择 checkpoint 后只评价一次
  完整 TEST。
- 六物种为 mouse、zebrafish、chicken、western-clawed-frog、fruit-fly 和
  *C. elegans*；训练/验证/测试染色体按协议固定，未使用封存物种。
- TEST 的有效位置分母为 `2,160 × 4,096 = 8,847,360`，每个物种为
  `360 × 4,096 = 1,474,560`；BOS/EOS 不进入支持数或指标。
- `support` 是来源文件标为该类别的有效碱基位置数；每类的 TP/FP/FN 是在
  所有有效位置上按 one-vs-rest 计算。`material` 把 ID 1--7 合并为非 BG
  材料，不能直接称为真实 TE。
- `main4_macro_f1` 是 SINE/LINE/LTR/DNA 四个 broad class F1 的平均；每个
  F1 仍在所有八类有效位置上计算。`ontology_macro_f1` 是有正支持的八类
  F1 的平均；`status_macro_f1` 是有正支持的三个状态类 F1 的平均。某物种
  没有某一状态的来源支持时，表中标为 N/A；JSON 的零除约定仍保存为 `0.0`。
- 实现只把 `support > 0` 的标签加入相应 macro 平均；本次完整 VAL/TEST 中
  每个物种的四个 main4 类均有正支持，因此表中的 main4 macro 确实是四类
  F1 的算术平均。

## 完整 VAL 和 TEST

| split | valid positions | material F1 | main4 macro F1 | ontology macro F1 | status macro F1 | accuracy |
|---|---:|---:|---:|---:|---:|---:|
| VAL（完整 1,440 窗口） | 5,898,240 | 0.825348 | 0.821864 | 0.698268 | 0.451356 | 0.905026 |
| TEST（完整 2,160 窗口） | 8,847,360 | 0.884305 | 0.833687 | 0.767866 | 0.630650 | 0.889600 |

TEST 的逐类结果如下。`support` 是来源标签分母，而非窗口数。

| 类别 | precision | recall | F1 | support |
|---|---:|---:|---:|---:|
| BG | 0.927905 | 0.904837 | 0.916226 | 5,196,190 |
| SINE | 0.718624 | 0.770713 | 0.743758 | 75,713 |
| LINE | 0.908154 | 0.946153 | 0.926764 | 1,142,586 |
| LTR | 0.845474 | 0.909237 | 0.876197 | 1,254,710 |
| DNA | 0.768179 | 0.808934 | 0.788030 | 939,741 |
| KNOWN_OTHER_TE | 0.809760 | 0.650142 | 0.721225 | 83,331 |
| AMBIGUOUS_TE | 0.705369 | 0.474903 | 0.567635 | 117,883 |
| UNCLASSIFIED | 0.777929 | 0.492421 | 0.603091 | 37,206 |

逐物种 TEST 结果显示，材料检出和类别区分是两个不同层次：

| 物种 | material F1 | main4 macro F1 | ontology macro F1 | status macro F1 | accuracy |
|---|---:|---:|---:|---:|---:|
| mouse | 0.958057 | 0.849131 | 0.851522 | N/A | 0.930646 |
| zebrafish | 0.837089 | 0.738177 | 0.596344 | 0.327775 | 0.790044 |
| chicken | 0.885859 | 0.642469 | 0.508537 | 0.000000 | 0.980716 |
| western-clawed-frog | 0.738766 | 0.546318 | 0.445552 | 0.000000 | 0.883957 |
| fruit-fly | 0.907496 | 0.911702 | 0.705689 | 0.435616 | 0.842047 |
| *C. elegans* | 0.749035 | 0.712204 | 0.724374 | 0.665039 | 0.910193 |

低的 status F1 不应在没有支持的类别时解释为模型完全不会识别该类别；例如
mouse TEST 没有三个状态类的真实支持，因而 status macro 标为 N/A。chicken
和 western-clawed-frog 有状态支持，但该运行对这些状态没有正确预测，故其零值
是有效的零 F1。

## 与旧六类 checkpoint 的同 TEST 描述性对照

旧 checkpoint 没有重新训练，也没有用修复后的 VAL 重新选模型；它只是在同一
个完整 TEST 上把新数据 ID 5--7 合并成旧的 `Unknown`。因此这不是 ontology
拆分的因果 ablation，但能说明结果量级和旧 prefix 的影响。

| checkpoint / 评价 | material F1 | main4 macro F1 | macro F1 | accuracy |
|---|---:|---:|---:|---:|
| 新八类模型 | 0.884305 | 0.833687 | 0.767866（八类） | 0.889600 |
| 旧六类模型 | 0.884531 | 0.834947 | 0.770027（六类） | 0.884760 |

三个 status 类的逐类 TP/FP/FN 之和只能给出“精确 status 类别”的 micro
F1：TP=128,481、FP=41,342、FN=109,939，support=238,420，precision=0.756558、
recall=0.538885、F1=0.629434。它把 status 之间的错分视为错误；若只把三个
status 合并为一个二值 `Unknown`，status 之间的错分会变成合并后的 TP，而当前
compact JSON 没有联合混淆矩阵，不能报告精确的合并值。已知来源标注 status 支持
238,420、预测 status 总数 169,823、精确 TP 128,481，因此合并二值 F1 的可证
下界为 0.629434、上界为 0.831970（precision 下界 0.756558、recall 下界
0.538885）。旧模型的 `Unknown` F1 是 0.363488（precision=0.704439、
recall=0.244938）；这些是同一来源标签任务上的描述性数值，不能据此识别
ontology split 的因果效果，也不能把来源 Unknown 当作生物学真值。

## 论文可用范围

这组结果可以支持正文或补充材料中的以下表述：历史评分前缀确实低估了六物种
面板的覆盖；在固定 broad-class/status ontology 下，模型在完整 TEST 上有
0.884 的 comparator-relative material F1，且 LINE/LTR/DNA 的 pooled F1 分别
为 0.927、0.876、0.788。显式 status 类的结果可将人工/数据库注释不确定性
作为单独的预测状态报告，但不等同于独立生物学置信度。

应避免把 `material F1` 写成独立 TE 真值 F1，把 `BG` 写成 confirmed negative，
或把该六物种面板写成所有脊椎动物、无脊椎动物或 family/superfamily 泛化证明。
若需要生物学真值或 superfamily 结论，仍需单独的高质量、独立标注数据设计。

## 证据文件

- `dataset_metadata.json`：来源语义、六物种 split、窗口和逐物种标签支持。
- `training_meta.json`：seed、训练参数、完整分母和最佳验证指标。
- `validation_results.json`、`test_results.json`：完整 pooled/per-species 指标。
- `legacy_collapsed_full_test.json`：同完整 TEST 上保留的旧六类 checkpoint 对照。
- `STATUS` 为 `COMPLETED`；远程 checkpoint 和原始序列仍保留在 Baobab，未复制到 Git。
