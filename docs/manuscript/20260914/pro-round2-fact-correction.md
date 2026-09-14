# Pro 第二轮事实勘误原文

2026-09-14；来源：[内置浏览器对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。收到三份新增取证附件后生成，通过“复制回复”归档。以下是原文；工程状态对应附件快照，最终实施进度见 [并行实施记录](../../experiments/DIRECTIONS-EXECUTION-20260914.md)。

## 事实勘误

**1．D应改为“已有内部DEV/SCREEN/CONF”，而非仅DEV/SCREEN。** worm CONF：seed42 **.794878**、seed17 **.803820**；旧JSON的`conf_evaluated=false`只是生成时状态。仍无未见物种D输出，也无MoE/adapters结果；不能由CONF补充改写冻结验收。

**2．TE_final不再是“等待恢复”，而是“42文件已恢复、部分证据仍未闭合”。** M5为10,000 fragments／12类／13物种，最强是**k-mer contrastive B0，ARI=.928141**，不是GLM；必须与本地1,800-fragment Dfam表分开。 历史强B1 **ARI=.6928**确有报告，但hg38五类与六物种七类描述冲突、raw comparison缺失，只能保留为**coarse历史线索**，不能进入定量结果图。`exp002_consensus_100bp`未找到完成metrics；不等于证明它从未在别处运行。

**3．历史注释资源已定位，但尚无“后来证实”。** 本地hs1使用**2018库＋Crossmatch**，不能因组装更新就认定标签更新。 T2T2022新track与双向chain已定位、尚未下载运行；新版同时改变library和engine。应先做**同assembly、engine-matched的新旧库对照**，再扩跨组装mapping。

**4．RC推理合并并非空白。** 旧mouse chr1／NTv2-250M／4096已有segment F1：raw **.3062**、CRF **.3569**、consensus-min＋CRF **.4149**，后者boundary F1 **.1267**。应撤回“从零开始验证推理合并”的前提；这些局部结果不等于当前D或RC等变训练有效。

**5．工程状态更新，科学结论不升级。** Tiberius最小修复已通过针对性测试及六通道contract；smoke **12687393已提交**，附件记录为PENDING，尚不能称通过。Omni 0.6.0接入与linking Phase0并行推进，M2/M3未训练，均非新科学阳性。

## 优先级修订

**优先完成原Tiberius smoke；通过后继续原20×3及原评分。** 并行完成Omni端到端工程样例、linking真值合同与难负例，material mask不变；推进固定D外部数据资格和输出、人类新旧标签对照、TE_final原始结果与panel身份核对。RC先复核旧增益，再检验当前D及训练增量；MoE继续后置。

**新增训练固定单seed42，不追加多seed。** 保留样本／空间不确定性；旧seed17结果、既定bootstrap和PASS／NO-GO均不追溯修改。
