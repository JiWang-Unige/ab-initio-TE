# 论文系统梳理：2026-09-14

已完成 ChatGPT 6 Pro 的系统审阅和完整英文叙事初稿。建议论文中心为：**DNA 模型能够识别 TE-associated material，但碱基一致性、注释片段结构、生物插入实例和低风险下游操作需要分别验证。** 当前证据支持评估与机制论文；尚不支持通用 TE 注释器已经验收完成或广泛部署的主张。

## 第二轮进展

用户追加的八个方向已完成第二轮Pro讨论，并启动并行工程推进。最新入口是[并行实施记录](../../experiments/DIRECTIONS-EXECUTION-20260914.md)、[Pro第二轮完整可见正文](pro-round2-visible-response.txt)及[最终事实勘误](pro-round2-fact-correction.md)。后者修正内部CONF遗漏、TE_final恢复状态、hs1库版本和历史RC结果。新增训练统一单seed42，替代第一轮建议中的新增多seed；历史结果保留。

Omni最小流程已实际跑通，fragment-linking Phase0的9项测试通过；这两项都是工程验证。Tiberius环境修复已提交smoke-r2作业12687393并已进入RUNNING，原20×3和独立评分尚未完成。论文正文只补入已取证的CONF结果，不把本轮设计或toy分数写成研究结果。

## 阅读入口

- [完整英文初稿](manuscript-en.md)：Title、Abstract、Introduction、六节 Results、Discussion、Methods、Availability、References 和主要数字来源表。
- [中文十问决策](review-zh.md)：逐项结论、正文/补充材料取舍与最小缺口。
- [主图、补图与补实验](figures-and-next-experiments.md)：5张主图、9组补充材料及有条件的实验优先级；这是设计，图尚未制作、实验尚未执行。
- [Pro 完整回复原文](pro-full-response.md)：未经重写的完整 Markdown，保留原始建议与原对话的附件链接。
- [取证与交付记录](../../experiments/MANUSCRIPT-SYNTHESIS-20260914.md)、[当前远程状态](../../experiments/MANUSCRIPT-LIVE-STATUS-20260914.md)、[已更正证据导航](../../experiments/MANUSCRIPT-EVIDENCE-BRIEF-20260914.md)。
- [内置浏览器 Pro 对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。

## 来源和保存方式

送审快照是本地 Git `c6781414794c120e41f67d9b43859a4d28453065` 的2,882个已跟踪文件。Pro 实际完成用时46分22秒；本轮通过页面“复制回复”保存62,590字符的完整原文，再按章节提取阅读文件。原文保留文件卡片及 `sandbox:` 链接，它们只在原对话中使用；内置浏览器附件下载未落盘，不能把本地提取稿称为成功下载的独立附件或完整审阅ZIP。下载稿中特有的完整25项证据附录、核算脚本、JSON和索引没有在本地归档；本地已保存完整论文正文、中文判断、图表计划和正文主要数字来源。

这是**完整初稿，不是投稿定稿**。原稿的 `[TO COMPLETE]`、缺失图版和发布信息须处理；Methods中描述ZIP审阅的段落须改为面向论文读者的实际实验方法。Pro的资源预算和新增归档方案只是建议，不是实测或已批准的执行计划。其新增散列建议不作为默认要求；优先用已有版本、坐标、预测和运行记录回答会改变结论的问题。

## 第一轮核实的关键更正

1. `main4_conditional_macro_f1` 在全部有效六类位置上计算每类F1，再平均四主类型。BG/Unknown混淆仍贡献FP/FN；与仅限制true label的conditional accuracy不同。已修正送审导航。
2. 所选 `baseline_plus_kmer` 的leave-species contains-best=19/22，leave-clade=13/22；.6364属于其他组。源码取top2已观测真实F1的最大值，因此.007083是oracle shortlist regret，不能称已执行probe收益。
3. 当前共享D的loader为NTv2-500M H0；与历史250M recipe、GENERanno/P3和HN附加NT-logit输入保持分开。
4. 从D六物种原JSON重算：3,000 tiles、24,541,946 callable bp、7,452,597 positive bp；物种macro bp-F1=.8887612459、run-F1@IoU.8=.4458837761、IoU-qualified joint-boundary-F1@5bp=.2043614175。六物种均参与训练。
5. 新Tiberius smoke 12652888为工程FAILED，`BASE_MASK_OBSERVATION`缺失；完整20core×3尚无结果。旧C无新增正确链是另一已完成科学结果。Pro提出容器环境传参原因是源码支持的推断，未通过修复重跑验证。

## 下一步取舍

优先补齐支撑正文的已有结果与版本记录（包括HN完整frontier），再完成一个当前D与传统完整workflow的同实例比较。要保留未见物种泛化、高效部署或基因注释改善的主张，分别依赖合格独立panel、代表性CPU/GPU性能实验、原Tiberius U/P/R协议结果。无需默认做MoE，也无需为这篇机制论文重开已关闭的HN阈值或旧C路线。

第一轮交付时没有启动新训练、推理、benchmark、Tiberius修复或作业重提；第二轮实际执行更新见上方入口。原冻结规则保持有效。origin本轮确认是public；本地提交不等于已公开推送。
