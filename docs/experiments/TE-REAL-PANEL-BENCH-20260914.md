# 真实固定区域 benchmark 接入

2026-09-14。当前授权：用户要求继续推进 benchmark；该批开始实际 native caller。

固定输入为外部 D 的鸭嘴兽、海胆、C. briggsae 每物种四个既定 1 MiB 区域，分别接入 RepeatMasker + Dfam 3.9 lineage library、HiTE 3.3.3、RepeatModeler 2.0.9 + RepeatMasker 4.2.4。原 D F 及旧阈值保持不变；短 query ID 只改变名称，逐条保存映射，预测仍在区域内 0-based half-open 坐标。caller 不读取 D 预测或评估标签。

这是 **real-region feasibility / T2 concordance**。4 MiB 的重复拷贝数量与上下文可能不足以支撑 de novo discovery，不能用这个区域试验给全基因组方法排名。它也不是独立 accuracy truth；绝对 precision/F1 不计算。完整同输入全基因组、独立 T1 reference-positive panel、更多工具与总成本矩阵仍另需完成。

每个 native cell 4 CPU、32 GB、最长 110 分钟计算，Slurm 2 小时；9 cell 最多并行3个。RM2 使用 srand42；HiTE 保留自身默认随机行为，不声称所有外部工具都可强制相同随机种子。RepeatMasker `-pa 1` 避免把并行 batch 数误作4个线程。所有 failure、timeout、空 library 和零输出保留，不能删除失败分母。

产物：native logs、各步骤 argv/walltime/peak RSS、最终原生 annotation、canonical prediction、固定预期 cell registry。Omni 接入会明确区分 native Slurm 执行与其后重放/收集，不把已有结果导入的时间写成 native runtime。版本化 SIF 复用已有资产，无重新下载或安装。

当前有限验证：GFF 1-based 端点转 half-open、未映射 query 失败、合法空 annotation 保留零 calls。使用旧 converter，不改历史评分器。
