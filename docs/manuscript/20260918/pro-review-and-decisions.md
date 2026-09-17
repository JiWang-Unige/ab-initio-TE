# Pro 审阅与本轮执行决定

内置浏览器原会话、6 Pro，2026-09-18 请求，回复思考 8m28s。Pro 明确表示读取固定提交 `c8d90bbcae0de6320c2cfa4ad2b8c22b3a95a6c0` 的 closure-scope-and-decisions、RNA run-12858354/RESULTS、backbone-transfer-inventory，并核读 D 鸭嘴兽及非哺乳结果；没有访问 HPC、权重或重跑评分。因此是基于报告的设计讨论，不是独立实验复核。

采用的建议：

- 保留原 D 和全部既有证据。先保存冻结 D encoder/binary head 加 class/status head 的部署备选；两次有限机制训练若运行，保持同数据、初始化和预算，隔离类别监督进入 encoder 的增量。材料概率改变后不得借用旧 D 的 downstream/benchmark 结果。
- BG 图与 0.522 首先核对样本/层/pooling；其次控制长度/GC/N/物种组成；最后检查原空间混淆矩阵、各类 P/R、固定 5NN 与线性 probe。不能从一个读出失败推论 GLM 没有 TE 信息。
- NT 官方整基因组与 MLM 说明不等于确定 TE hard/softmask 处理；原始证据不足时保持未核实。
- 专家实验有限结束，不作为主线成功的必要条件。本轮已固定 shared rank16 vs clade 2×rank8、相同可训练总参数与训练呈现；是类群条件专家对照，没有假称已经训练 learned gate。当前不追加 gate 搜索。
- 非哺乳接收器必须实际使用 lowercase。原生 AUGUSTUS 可用，需固定参数、CDS 终止密码子口径并披露同物种参数训练暴露。本轮采用两物种各 10 cores，满足用户明确的多物种需求；比 Pro 建议的单物种四 cores 更大，但仍为预先固定的一批。没有并行另开旧 Tiberius insect 模型训练。
- 全基因组 chicken/zebrafish benchmark 是 seen-species 完整流程/成本比较；质量范围另列预定坐标和训练/历史暴露。RM 标签分数是注释一致性，独立 LTR 阳性只能代表相应结构范围。保留 Unknown 和分类资源依赖；CPU硬件/线程/内存一致，GPU另列，浮点格式不强求全部方法一致。
- D 鸭嘴兽对 U_soft 有自身阳性，对 RM 没建立优势或等效。RNA 22 gains 和 8 losses 均有支持；含 halo 的 104 Mb RNA 候选分母不同于 100 Mb/639 loci 的基因准确率。StringTie 同一 RNA run 不是第二份独立实验。

停止边界：固定统一模型批、一次有限专家比较、两基因组 benchmark、固定非哺乳用途达到可解释终态后整理论文。失败是有效终态，需要区分工程失败与科学阴性；不得通过反复换物种、阈值或模型追求正向结果。正文可突出最强主线，影响其解释的局限仍保留在正文或补充材料。

会话：https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9
