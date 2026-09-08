# GAP-BRIDGE A/C 后续实验：先闭合可解释性

日期：2026-09-06。用户已要求“现在请开展后续实验”。本轮先执行两个独立的有界
readiness实验，再根据结果决定后续科学比较能否成立。所有结果claim-ineligible。
旧Stage1 NO_ACTIONABLE_ARM、P3、原候选/标签/split、chr19–22封存不变；不覆盖原输出。

## 权限与实际对比对象

- A仅审计原P3候选的whole-gap/crop原生NT覆盖，不训练、不重新预测、不重拟合stats，
  不将missing填成概率、不删候选。原协议**不新增NT候选**；固定NT>=0.5 donor是原P3
  合法gap上的描述性comparator，不是额外候选生成器。此前Pro的扩展候选池假设不采用。
- A获准chr3/5 TRAIN和chr13既定DEV/CAL_FIT/CAL_GATE的**输入coverage**审计；不做
  校准/评分/选择，不读sealed chromosome。known用于缺失诊断分组，不成为模型特征。
- C先使用原九core中第一个有参考链的core6（79链），完整core+100kb halo，M0预测。
  如实际M0无CDS，可按预定顺序检查core10一次（19链），不按预测好坏选择更多样本。
  阳性验证不替换最终九core评价面板；不改mask、模型、seq_len=400050或batch_size=1。
- 本轮不采用Pro的新单seed建议去覆盖原A训练契约，不启动未锁定gate的完整head训练。
  后续有限C三臂比较只在非空/端点语义闭合且实测预算可行后另记提交决定；不把
  `loss=0`或旧0.1%草案自动作为科学PASS标准，先报告实际gain/loss/F1和局限。

## A — GAP-BRIDGE-A-COVERAGE-20260906-R1

CPU-only tokenizer/坐标审计；与既有strict NT适配器的实际token投影一致性必须有
含N截断、完整ACGT、边界/跨窗口测试。区分窗口覆盖、整个gap覆盖与head上下文覆盖。
审计原候选母体而非成功features，报告完整/部分/无覆盖候选和bp、split/长度/seam/
known分层。数据处理成功且发现缺失是有效诊断，不是科学NO-GO或计算失败。
如缺失由原生token预算造成，重复原推断不保证补全；先报告原因，不能静默移动窗口。

## C — GAP-BRIDGE-C-ENDPOINT-20260906-R1

使用已成功的Tiberius2.0.7容器和固定源码commit4d657012a3ed4e923f5d0ac5cef65fecae8109bd。
容器项目绑定`/work/te`，源码`/opt/Tiberius`。准备三臂完整core FASTA用于同letters/
softmask传递验证，但本阶段实际基因预测仅M0，避免在端点约定前查看三臂收益。

容器中bricks2marble的`Transcript.to_gtf_rows`直接输出内部0-based半开CDS块为
1-based闭区间CDS；CDS已含terminal stop，start/stop_codon为辅助合成行。
**新端点适配器仅采用原CDS行，不并入或推断3bp**；旧provisional union适配器不改。
使用安装的真实exporter将全部243参考链及重复来源往返为GTF，验证去重、正负链、
halo offset、单碱基错位/错误strand拒绝。参考与预测均按最小genomic CDS start
归属原DEV core，整链包含owner halo；不改eligibility和主评价分母。

实际M0运行需要：非空CDS输出；GTF/GFF3 CDS坐标一致；实际Fasta.one_hot返回的第6
track与输入大小写标记一致、前5track不因大小写改变；生成非空输出不是模型效果PASS。
参考match数不作为工程阈值，0correct不能靠放宽边界修成通过。

## 资源与停点

- A CPU0GPU；C单RTX3090/4CPU/48GiB，上限2小时，包括最多两个预定core的M0。
- 单作业不超过12h，A/C既有共享24GPU-hours上限不重置；此前GPU jobs
  12398722/12398977/12409697合计193s，全部计入。
- 现存其他研究job12270926不触碰。新exp输出及`logs/%x_%j`隔离，不复用失败目录。
- 采用远端on_cluster合同，经已有SSH主机`login1.baobab.hpc.unige.ch`在原project
  执行；本机只同步精确的新代码/配置，不改全局cluster_config或ACTIVE_GOAL。
- 新代码经过self-review、独立code-review-gate、分配内测试后运行；不在login计算。
- A覆盖无法完整解释则停在输入诊断，不训练；C两预定core均空、exporter/坐标/track
  失败则不扩科学运行。失败按工程/材料原因报告，不伪装科学证伪。
