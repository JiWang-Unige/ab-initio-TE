# GAP-BRIDGE A/C 工程闭合后独立路线审阅

## Provenance 与权限

- 用户要求：修复 C 容器路径，A/C 工程结果齐全后使用内置浏览器 ChatGPT Pro 独立审阅。
- 日期：2026-09-06 CEST；内置浏览器，模型选择器 `6 Pro`，能力菜单 `Pro`。
- 对话：https://chatgpt.com/c/6a9ca454-98ec-83eb-b995-9f0d53fdc77e
- 状态：完整回答已结束；页面出现“复制回复/Pro反馈/启动语音功能”，无停止回答按钮。
  页面最终回复同时保留旧定义段落和后续“总体判断”起始的修订段落；仅采用后者。
- 这是基于提供材料的独立咨询，不是数据独立复现、科学证据、tri-review quorum 或新执行授权。

## 实际提供的证据与更正

- 旧 Stage1 NO_ACTIONABLE_ARM；H−R AUPRC+0.01083，但原Brier改善0.6744%
  未达5%，扣除固定floor也仅1.1684%；低预算H真TE1018/错填314bp，R1407/273bp。
  不改变P3，chr19保持sealed，不以新路线翻案。
- A：Job12398722，chr3八个原候选crop，input alignment PASS；741503 known TRAIN
  拟合统计，未训练HN。原143通道/7标量扩为144/10，原窗口P3=8192、NT=4096/origin0。
  NT chr3[8192,12288)覆盖686/4096，下一窗口完整；八个crop均完整不代表population。
  说明既往训练祖先与foundation预训练坐标不明，禁止human未见泛化主张。
- C：MW=全positive完整gap whole-gap oracle；MP=所有候选gap内positive碱基投影。
  MW17660gap/143476bp，MP461752bp，unknown475bp不变；全9DEVcore60574候选。
  两oracle不是gene utility单调上界，MP−MW混合材料量与分辨率，不能作单因素归因。
- C参考243 distinct CDS chains来自330 eligible转录本行，重复87；非243genes。
  固定panel下0.1%允许correct-chain loss实际上至多0条，原草案阈值未采用。
- C runtime修复物理host→`/work/te`，Job12409697 COMPLETED0:0/113s/1RTX3090。
  固定400050bp first-DEV-candidate样本，三臂0transcripts；没有完全包含的RefSeq
  CDS链，RXFP2跨边界。证明runtime，不证明非空exporter、endpoint或paired效用。
- 初稿对MW/MP、A chromosome、C CPU/GPU的转述错误已在原消息编辑修正；只采用
  修订后完整回答。实际定义以冻结config和结果为准，不以LLM转述修改实验。

## 审阅问题

区分工程完成与未证明项；独立判断A/C继续价值及优先级；给出训练前最小有辨识力
分阶段实验、C阳性gene-bearing控制与端点约定、A coverage处理；指出有价值但未证
主张、禁止主张、停止条件及新授权边界。不因为工程已投入而默认继续完整训练。

## 有效完整回答的忠实摘要

以下来自最终回复后半部“总体判断”至末尾，不是运行结果。

1. **C CONDITIONAL GO；A CONDITIONAL、当前完整训练NO-GO。** C的非空读出和
   评分契约优先，A母体coverage可并行；不因为工程投入而续投。旧Stage1关闭不变。
2. C建议以既定core6（79条参考链）原core/halo为首个gene-bearing技术输入：先验证
   参考/评分语义，再M0真实非空输出，最后看MW/MP收益。检查local→genomic坐标、
   strand、CDS顺序、stop-codon和实际第6track干预。参考自比较243不是330；错位/
   错strand不能被接受。禁止事后±3bp容差或换成intron-only评分。
3. 可事前批准core6仍空时再按顺序检查core10；两者仍空则停止扩大三臂科学运行，
   转有限技术诊断，不持续挑样。此处是Pro建议，**本轮没有批准或运行这两个core**。
4. A审计应包括donor筛选前全部获准gap母体，不只成功生成feature的候选；区分整个
   gap覆盖和head上下文crop覆盖。按split/chromosome/长度/seam/来源/known状态归纳
   缺失。未覆盖logit填0意味着p=0.5，可能错误满足NT>=0.5，故coverage判定先于阈值。
   优先保持原4096/origin0重算受损窗口；残余缺失策略及任何分母/统计变化需事前确认。
5. C正式九core试验前看新增mask是否进入被评分链及实际模型上下文；编码区重叠是
   暴露，不自动等同生物学错填或无害。无candidate core仅在完整输入含halo一致时
   才是无干预对照。正式读出分开新增正确链gain、丢失正确链loss和未匹配预测。
6. C主问题是MW−M0。MW有效gain且零loss可支持本DEV上存在whole-gap干预效用，
   但不证明可学习/部署；无gain无loss不支持改善基因预测，却不否定TE覆盖价值；
   MW loss否定“纯TE填充天然安全”，不否定所有更小选择策略。只有MP有益不能作为
   A whole-gap通过；MP−MW增加318276bp、约3.22倍剂量，分辨率与材料量混杂。
7. 零观察loss只能作为拟议DEV投入门，不是既定阈值或0.1%风险证明；M0正确数若为0，
   正确链保全无有效基线。Pro以独立243条链假设示例得到零损失单侧95%上界约1.2%，
   同时明确实际链相关、M0正确数更少，不能用作本panel的正式置信区间。
8. A只建议一对预定预算/种子H0/HN。共享NT-donor候选时，HN−H0识别该候选池上的
   特征增量，不是NT整个流程的总贡献；若候选池不同则混杂。固定校准材料选门槛，
   DEV不得重新找阈值/挑预算，AUPRC不能替代实际误填预算下的覆盖与admissibility。
9. 停止条件：coverage/donor/missing语义未闭合不训练；配对母体不同不解释增量；
   无admissible policy停止可行动推进；HN不优H0停止NT增量臂；C非空/端点不成立不
   扩科学运行；零loss门若被事前采用则不能净收益抵销loss；预算不足停止并申请。
10. 最有价值的待证主张是：固定P3/whole-gap/完整母体上，NT提高冻结误填预算下的
    comparator-positive覆盖，且真实策略不丢失固定下游读出的原有正确CDS链。
    A/C各自阳性仍不能拼成部署证据，必须单独验证真实校准策略生成的mask；反复使用
    chr13是开发证据，不是独立确认。chr19、partial-fill新路线、剂量配平、基因注释
    决策、新通道/缺失处理及训练/科学门槛均需新协议或授权。

## 质量裁决与本地建议

- **不采纳前半部旧定义段落**：其中将MW当逐碱基oracle、MP当全部known填满，
  将318276bp差额说成非TE，且把113秒称CPU、把新增输入说成10个NT标量。这些均与
  已读取config/JSON矛盾。后半部正确使用whole-gap MW、partial-positive MP及logit
  通道解释，取代前半部。保留此错误说明，防止引用聊天链接时误采旧段落。
- 接受有效建议的优先级：先提出C core6非空/exporter和A全母体coverage两个有界方案，
  不自动训练或全9core推断。零loss是待确认建议，不写回冻结config。
- 限定重算建议：已知NT原生tokenizer发生覆盖截断，重复原命令不保证恢复覆盖；
  必须先确定截断原因及不移动原窗口的可行修复。审计的结果应决定重算还是另立缺失
  协议，不能把“重算”预先记成已解决。
- 输入track的源码语义已有证据，下一轮只补一次实际gene-bearing运行传递核对；
  不重复搭建容器或重复无辨识力空样本。
- 本轮目标完成：路径修复+限定A/C工程闭合+Pro独立路线审阅。科学路线尚未完成，
  没有新训练、科学配对评分、chr19访问、阈值调整或原结果覆盖。
