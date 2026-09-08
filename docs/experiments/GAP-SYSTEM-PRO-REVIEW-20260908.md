# Gap 系统 Pro 审阅：当前路线关闭与基础 mask 效用候选

2026-09-08。用户明确要求 GitHub 提交后在内置浏览器使用 ChatGPT Pro 系统审阅，
并明确批准公开提交。本轮结果快照：
`14cfa0090848e516d0d7e4b178c765e1b73c3ce2`，已核实 origin/main 与本地一致。
40 个 gap 相关文件；未混入跨物种工作、框架退役删除、原始数据、权重或大缓存。

审阅来源：[内置浏览器 Pro 会话](https://chatgpt.com/g/g-p-6a29d586630481918525796032225f68-ji-wangke-ti/c/6aa067ec-ce98-83eb-8581-a8174f721df5)。
界面确认 `6 Pro`，最终答复显示思考 22m33s。Pro 明确报告实际读取固定提交、提纲、
gap 协议、JSON、实现、配置及脚本；这是限定范围的代码/公开记录咨询，
不是全仓审阅或独立计算复现，未访问 HPC 或全部原始预测。以下是摘要，不是原文。

## 结论及证据边界

- 未发现足以推翻现有结论的分母错误、明显配对失衡或 DEV target 直接进入 head
  输入的缺陷；不因此认证全部 checkpoint 历史零泄漏。DEV 复用限制确认性解释。
- HN 的 fraction-MSE 降低 8.5905%、AP 增加 0.083617 是 NT+seam 组合的探索性
  预测增量，不是独立 NT 因果、同插入身份或泛化证据。三个 seed 不是生物重复。
- 固定 HN 分数全部 60497 个完整 tie-group 阈值均无可行动作。保序校准不产生
  新的全局阈值前缀集合，不能消除这个缺口；维持 CAL/部署停止。
- 旧 G/R/H、H0-S screen、C MW/MP 按原规则保持关闭。原全量 A/B1 未执行；
  Gate L/O/E、empty-site 缺独立材料，不改写为实验失败。
- C 的 MW/MP 都 gained=0/lost=0；MP 的 F1 +0.000971 来自 unmatched 净变化，
  且两个新 unmatched 身份出现，不能说恢复正确基因或精准删除一个假基因。
- C 分母为 243 distinct CDS chains（含不同 isoform），不是 243 独立基因；
  27 treatment cells 也不是 27 独立样本。不把此 F1 与常规 gene-level F1 混称。
- 实际 softmask 通道观测及 native CDS-only 解析已有证据，不能凭猜测用“mask
  没有读进去”解释阴性。新增 mask 与 CDS/splice 重叠不等于已造成预测损伤。

## Tiberius 的直接回答

C 测的是 P3 mask 之上的额外 comparator-assisted gap 填补，未比较 P3 与 unmasked。
因此，输入机制已接通，但基础 P3 的实际下游效用仍未被回答，既不能支持也不能否定。
MW/MP 也不是下游最优 mask 的数学上界。当前最有判别力的新问题是基础 mask 效用，
而不是继续同一 DEV 的 gap head/阈值搜索。

## Pro 提议的新协议候选（未授权执行、未冻结）

1. 同一 Tiberius checkpoint、序列、上下文、切窗、推理与后处理，三臂：
   U=大写输入且第六 mask 通道零；P=冻结 P3 mask；R=冻结常规 repeat-mask 参照。
   主比较仅 P-U；R 记录库依赖，不能冒称 library-free 公平替代。
2. U 仍使用相同六通道模型，不切换 no-softmask checkpoint；验证真实模型入口的
   前五通道相同、第六通道符合处理。既有观测机制可复用，不需要额外通用框架。
3. 先核实面板相对 P3/祖先 checkpoint 的训练、选模及历史使用独立性；旧 chr13 DEV
   不改名为确认集，chr19–22 不解封。Pro 举例约20个5Mb core/约1000 coding loci，
   仅是规模讨论，不是现有材料或功效保证。
4. 新主终点可采用一对一 gene-locus 匹配：每 gene 一个参考单位、允许预先固定的
   任一完整 CDS isoform；未匹配预测计 FP，无基因 core 的 FP 保留。旧 chain 指标
   可作次要终点，但绝不替换旧 C 的主口径。
5. Pro 示例投资门为 locus F1 绝对 +0.01 且配对区块区间下界>0、recall 非劣界
   -0.005，并另定丢失正确 loci 上限。这些数值尚非项目批准标准，需要新协议论证。
   基础效用可以来自可靠降低 FP，不必要求 gained>0；这不取消旧 C 的 gained 门。
6. 独立材料不成立则未执行；固定样本/预算结束未过门则关闭该组合，不扫描阈值、
   seed 或 checkpoint。区间过宽是证据不足，不等于证明完全无效。

## Agent 收束

接受关于停止当前 gap 动作路线、区分基础 mask 效用与增量填补、准确命名 CDS-chain
分母的判断。Pro 建议不构成数据访问、实验、训练或解封授权；本次没有提交新作业。
下一项准备工作应先只读核实独立面板与 checkpoint 暴露范围，再决定是否提出新协议。
不把 Pro 末尾关于面板的提问直接转给用户索取仓库中可能已存在的事实。
