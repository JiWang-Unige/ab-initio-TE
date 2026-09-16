# 长输入 benchmark：冻结运行结果

2026-09-16。冻结的14个cell已全部到可解释终态：13个合格完成，1个CB4 EDTA原生失败。两项EarlGrey起始库恢复12739911已完成，最终组合库和坐标检查通过；新Slurm评分12739923及对应Omnibenchmark回放均已完成。本轮预定执行与结果处理已闭合。**该模型在本次TE_Bench派生模拟中没有达到最佳传统方法的准确性，CPU也没有显示速度优势。真实CB4参考过于稀疏，不能据此完成全基因组准确性排名。**

这里的完成指冻结方案的执行、分母保留和结果处理；不等于证明模型优势或完成了充分的真实TE真值benchmark。

## 输入和评价边界

- `sim100`：TE_Bench/GARLIC派生100,000,000 bp，严格TE材料真值54,481,086 bp；直接生成BED与插入材料核对通过。366个生成库条目全部可按名称/accession在固定RM的Dfam3.9库中找到。它是已知库表示的模拟挑战，不能称为无偏的新家族发现实验，亦不是原TE_Bench论文模拟的直接重跑。
- `c_briggsae`：CB4全部108,384,165 bp；去N后的可评价分母105,416,539 bp。原Label-A严格TE阳性仅1,571 bp，来自SINE类；不把其余序列当真阴性。
- 固定D模型沿用既有checkpoint、六物种CAL和阈值0.42330056285498807；窗口4096 bp，batch12；没有使用模拟结果重训或重新校准。
- 所有native方法使用16 CPU、80GB、同E5-2630V4硬件类别，单cell原预算84600秒。参考辅助的fixed RM/EarlGrey与de novo管线拥有的先验信息不同；完整命令/版本/库条件保留在config、原生status和attempts中。

## 模拟材料结果

| 方法 | Precision | Recall | bp F1 | 完整流程时间（秒） |
|---|---:|---:|---:|---:|
| fixed RepeatMasker 4.2.4 | 0.988781 | 0.964117 | 0.976293 | 1299.70 |
| RepeatModeler2 2.0.9 → RM | 0.983027 | 0.913519 | 0.946999 | 12766.88 |
| HiTE 3.3.3 | 0.992938 | 0.469329 | 0.637386 | 2164.98 |
| EDTA 2.3.0 | 0.983856 | 0.738987 | 0.844020 | 18627.47 |
| EarlGrey 7.3.0 | 0.979105 | 0.970814 | 0.974942 | 11704.95 |
| 固定D，GPU（TITAN X） | 0.887689 | 0.301975 | 0.450648 | 3029.51 |
| 固定D，CPU（16 CPU） | 0.887690 | 0.301975 | 0.450648 | 23861.16 |

固定D的主要局限是召回：约38.03 Mb严格TE材料未被检出。相对fixed RM、RM2、HiTE、EDTA、EarlGrey的F1差分别为−0.525645、−0.496351、−0.186738、−0.393371、−0.524294。按固定100个1Mb块、seed42、10000次配对bootstrap，它们的条件95%区间均低于0；这是此单一模拟输入内的块重采样范围，不代表跨生成seed、跨物种或生物学不确定性。完整区间保存在JSON中。

EarlGrey的低值触发了输出来源检查。标准最终GFF与adapter选择正确，但实际组合库只有1405 bytes，与de novo strained library相同；初始lineage库约3.63MB并未加入。`RepSub=$startCust`仅在被续跑跳过的initial-mask函数中赋值，导致最终RM实际缺少原协议要求的起始库。原始模拟F1=0.123734保留在旧JSON中作为不合格尝试记录，不能作为该参考辅助方法的有效分数或模型胜过EarlGrey的证据。恢复12739911_[0,1]现已完成：仅在新复制目录修复变量恢复，重建受影响final RM/merge；不改阈值/库/输入，不替换成初始RM中间预测。两输入均满足`final_library.exact_concatenation=true`。模拟最终库3,635,244 bytes/1,008条，精确包含strained 1,405 bytes与lineage 3,633,839 bytes；最终GFF 148,589行。合格模拟F1=0.974942；D−EarlGrey的条件95%区间为[−0.531093, −0.517608]。两输入的历史输出均保留，详情见[输出资格报告](earlgrey-recovery/OUTPUT-QUALIFICATION.md)。

## CB4：稀疏参考诊断与完整运行成本

| 方法 | reference-positive recall | 预测TE bp | 完整流程时间（秒） | 状态 |
|---|---:|---:|---:|---|
| fixed RM | 1.000000 | 1608 | 283.03 | 完成 |
| RM2 → RM | 0.350095 | 27438314 | 18113.92 | 完成 |
| HiTE | 0.000000 | 15407514 | 2440.23 | 完成 |
| EDTA | — | — | 32657.08 | 失败，不计零分 |
| EarlGrey | 0.998090 | 28417739 | 10915.88 | 完成，组合库资格通过 |
| 固定D，GPU（P100） | 0.618714 | 9027536 | 3952.27 | 完成 |
| 固定D，CPU | 0.618714 | 9027524 | 26112.05 | 完成 |

这张表不构成真实TE准确性排名。原RM `.tbl` 本身就只有23个SINE条目、1,571 bp，LINE/LTR/DNA阳性均为零；来源记录指出只有16个祖先curated family、没有物种lineage-specific family。fixed RM与Label-A共享近似的RepeatMasker/Dfam来源，因此其100%是来源一致性，不是独立真值上的完美敏感度。固定D覆盖972 bp并漏检599 bp；参考覆盖缺口与模型漏检确实并存。未覆盖参考的预测不能直接认作FP或被“救回”的TE。详见[参考资格报告](reference-qualification/RESULTS.md)。

EDTA在CB4完成TIR/Helitron等阶段后，由于完整LTR候选文件为空而未通过默认候选检查。保留FAILED状态、实际耗时和完整分母；没有使用`--force`绕过，亦不推断CB4不存在LTR。模拟EDTA完整完成123471行输出。见[EDTA终态证据](edta-recovery/FINAL-STATUS.md)。

## 计时、回放和论文用途

CPU固定D在两输入上分别耗时约7h15m和6h38m，均慢于本批其余已合格且完成的CPU native管线；这组数据不支持CPU速度优势。GPU时间单列，设备也不同，不把GPU forward和native CPU全流程作无条件排名。D计时包括模型加载、分词/特征、forward、合并和输出；两种硬件有少量阈值边界数值差异，模拟F1只差约3.7e−8，不假称预测逐碱基完全一致。

EarlGrey/EDTA时间包含选定协议下保存的失败尝试、复制和续跑，不只报最终几分钟。更早的无效库/probe工程尝试也在attempts中披露，但不能把这里的selected-protocol wall time解读为整个项目的全部计算消耗。训练成本没有计入D推理时间，native所用预置数据库构建成本也未计入；本表比较部署时的这条固定注释流程。

Omnibenchmark 0.6.0从固定GitHub commit `4edaeb16e735be4c25fdbace12822f026604f649` 干净回放新`score-12739923`的实际block counts，全部4个工作流job完成，保留13合格完成+1失败，指标与Slurm一致。旧`12738470` bundle及回放保留为历史记录，其中两项EarlGrey协议不合格，不参与当前排名。新的Omni执行复现聚合计算，不宣称重跑了所有native callers；也不把算术一致性当作标签或原生产物的独立验证。详见[新回放证据](omni-12739923/README.md)。

本批结果可进入补充材料的方法/运行成本表，也可作为正文中“适用边界与参考依赖”的结果。不能写成普遍优于传统工具、无脊椎动物普适泛化、新家族发现或真实全基因组accuracy benchmark已充分闭合。当前最明确的真实比较缺口是独立且覆盖广泛的真实TE真值，而不是继续在这份稀疏参考上调参。任何新的真实truth或方法配置应单独预先规定，不覆盖本次结果。

证据：[Slurm实际结果](score-12739923/result.json)、[资格摘要](score-12739923/qualification.json)、[Omni collector](omni-12739923/collector_summary.json)、[固定协议](../../docs/experiments/TE-LONG-BENCH-20260915.md)。原始FASTA、GFF、模型权重和概率数组保留Baobab。
