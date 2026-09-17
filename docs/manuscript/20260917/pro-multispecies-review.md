# ChatGPT Pro 新一轮多物种论文审阅记录

2026-09-17，在内置浏览器原研究会话中提交作者最新九项主线，于12:12 CEST前取得完整可读答复。界面模型为6 Pro；不是本机独立实验复核。

会话：<https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9>。

Pro声明通过GitHub连接器核读固定提交 `675e8039467043f6119542fb076250edc983754b`，包括旧P3-only讨论、D内部及MoE、SF5、长输入benchmark、P3外部结果和历史恢复报告。未访问HPC/weights，也未见本轮三个subagent后来提交的新增证据。以下为准确摘要，不伪装逐字完整转录。

## 核心建议

支持当前作者优先的跨物种TE主线，明确旧P3-only建议不是约束。三层证据：表示和材料识别→带类别及状态的动物TE map→同一固定mask的gene annotation用途。

建议六正文图：模型比较与流程；匹配表示；动物泛化及类别；标签依赖及context；benchmark与成本；下游用途与复用。最终用于外部评估、benchmark和新Tiberius的流程需一致。D、SF5、P3不能分别提供最优数字后拼成“最终模型”。

材料层与分类层可以分开；Tiberius只需要材料mask。分类不确定不能删除材料TE，分类未检出要算最终map的FN；source-state与model-reject分开。SF5是独立GENERanno模型，不是NTv2 D分类头。

## Pro提出的有限补充（尚未全部采用或执行）

- 外部新增最多六物种槽位，两个开发、四个确认；medaka/silkworm及stickleback/turkey/D.simulans/oyster只是候选。每种需assembly、label、项目历史与Tiberius暴露资格。初始每种最多16MiB；预先指定两个确认种再做全基因组，不按模型成绩挑选。
- shared→共享adapter/双专家→固定平均/taxonomy/gate；只有开发域互补成立才训练gate。逐测试种挑champion只算oracle。任何新晋级门须预先固定，不替代旧冻结验收。
- hg19后续支持不证明非记忆；旧human-library RM最多在两个已观察区域做有限回顾性配对。
- context建议最多768固定中心、四种flank、两个相位、两个冻结模型；保持中心序列相同，报告内部/边缘、背景中心与配对不确定性。根任务本轮先采用更小的192 DEV窗口BG/TE shuffle诊断，**不是完整执行这个建议**。
- embedding比较同基座谱系已有权重，固定样本、pooling、split；linear probe、unsupervised cluster、supervised contrastive分别解释。k-mer/组成、random表示、permutation可作控制。旧高ARI不同panel不得拼接。若需目标因果比较，另做两个匹配短训练；本轮尚未启动。
- 最终材料流程冻结后，两个非哺乳下游对象各10×5Mb core，七臂共140 calls；同gene模型固定mask比较，U_nosm整流程另列。既有P3阳性保留而不替代D新用途。
- 发布最小FASTA接口、manifest、notebook及路径解耦；不先宣称universal release。

Pro给出的48 GPU-hour首批、96 GPU-hour训练等预算属于建议，**不是本轮实际消耗或已落实的训练批准**。本轮使用更小资源限额，见 `multispecies-closure-plan.md` 和具体作业协议。

## 与已完成证据的关系

Pro保留D内部、SF5完整测试、P3用途、库控制和benchmark闭合等真实结果；保留模拟低召回、外部限制和局部gene loss。支持停止旧Gap/阈值搜索。它没有承诺Nature Communications录用，也没有宣布尚未完成的泛化或embedding结果成功。

本轮决策见 [有限收束方案](multispecies-closure-plan.md)。作者当前范围与项目实际结果优先于Pro提出的物种名单、预算和晋级草案。

## 后续勘误：Tiberius实际mask输入与context结果

根任务核读官方当前模型YAML后，将 `vertebrates/insecta softmasking:false`、旧昆虫softmask权重、Apis训练暴露及新192-window配对结果送回原对话。Pro随后给出可读修订，明确承认其原140-call提议存在实质性设计错误并撤回。

修订意见：先完成D自身→实际消费mask的哺乳Tiberius用途，同时继续非哺乳TE泛化；旧昆虫softmask模型可作一个物种×4预定core×4臂的有限历史接收器实验，须加current unmasked流程对照；非哺乳脊椎动物暂记无合格mask接收器、效用未评价，不变更成hardmask、不强行翻转flag、不新训gene predictor。根任务已明确旧昆虫配置同样包含Apis训练种，不能把它当未见种。

对context，Pro仅依据所提供本地报告作解释，未独立检查数组。其建议标题为“组成保留扰动揭示固定D的局部序列敏感性与异质context效应”；pooled效应小而21/192窗口绝对变化≥10pp，须展示全部分布。TE shuffle的原位点positive fraction不是recall。该结果不证明具体生物语法、非记忆或GARLIC低召回的主要原因。

Pro建议此机制实验在归档与必要不变量验证后结束，不扩大干预搜索。保留TE、整窗单/二核苷酸计数（含接头）、固定坐标/窗口已由原生runner逐样本验证；TE、BG和内部主分母在选样时确保非空，不重复不影响判断的检查。

当前新增D用途的实际冻结协议是 [D-TIBERIUS-PLATYPUS-20260917](../../experiments/D-TIBERIUS-PLATYPUS-20260917.md)：既有20core追加一个D臂，复用合格原生对照，未把Pro的可选16-call昆虫方案写成已执行。

## 第三轮：固定新结果后的稿件收束

15:47 CEST提交、约15:52 CEST取得完整答复。Pro声明固定读取 `14386820c45ea617127dbefc4f5d293749347f3f` 的本目录两份总表及其外部screen、NTv2表示、SF5、context、便携D与D-Tiberius协议链接；明确未访问HPC、未重跑评分。发送时D完整用途与GENERanno三权重表示均未结束，因此其意见不是这两项结果的验收。

六个结果节的建议为：共享材料模型与独立类别模块；微调后的标签可读出性；固定D的任务外动物材料恢复；注释来源与局部序列组织；长输入质量/成本及便携一致性；固定材料mask的gene用途。它支持已完成的NTv2配对、SF5完整分母、有限外部screen和上下文诊断，同时要求保留TE4聚类未改善、稀疏参考、模拟低召回和无CPU优势。D用途结果必须等全部20core资格与原生评分，不能借P3填补。

Pro把仍影响强结论的主要缺口收敛为两项：

1. **有判别力的外部参考。** 运行前固定非哺乳区域与来源，核查阳性及模型阴性背景并保留未定区域；rich-RM自产标签不是独立金标准。缺可靠负类则只报recovery，不用增加几个稀疏screen代替确认。
2. **库薄弱条件下相对强替代的用途。** 同一输入与合格接收器上比较D、官方nosm、rich-library RM及RM2→RM/Red；区分人为限库和天然库薄弱。全部loss及预定gain/未匹配预测需独立RNA、长转录本或蛋白支持，不能用生成参考的同一批证据循环确认。胜过无mask本身不足以证明该应用主张。

支持停止旧基座/窗口网格和context扩展，先冻结binary D v1，类别为独立可选模块。D+SF5并集八物种、蛙不是组合流程外部种，串接需端到端错误传播与成本。MoE只由合格开发域中的稳定缺口及专家互补触发，不由稀疏标签下的低分触发，不在测试种挑checkpoint。两项正在运行的实验结束不会自动等于Nature Communications级贡献。以上为审阅建议；候选外部面板和新强对照尚不能被写成已经执行。

后续实际完成：GEN三权重配对12854214和D用途评分12853263随后均已完成，详见[当前结果总表](current-results-and-paper-decisions.md)。这两项数值由项目原生输出支持，不属于第三轮Pro已核读的固定提交，不能宣称其由Pro独立复核。
