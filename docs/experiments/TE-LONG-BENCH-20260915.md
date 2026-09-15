# 长输入 TE benchmark：数据与模拟冻结

2026-09-15，在读取本批方法结果前固定。

## 输入与来源

1. 模拟：TE_Bench 官方仓库 commit `e7b92c56c055737b32720d473927c92894c787b2` 的 `droMelDFTEST` 全基因组模型源，配合 Dfam 3.9 curated EMBL，生成一条 100,000,000 bp 序列。先运行 1 Mb 工程 smoke，smoke 不参与正式评分。
2. 真实：已获准外部物种 C. briggsae CB4（GCA_000004555.3）全基因组。native de novo 方法使用完整序列获取拷贝支撑，GLM 使用同一完整输入。现有 Label-A 只支持注明来源的材料一致性/已注释阳性召回，不把未注释背景称为生物真阴性。

在任何本批 native 评分前，检查到共享 D 的上游协议将 dm6 保留为封存外部面板，因此撤回初稿中的全果蝇真实评价，改用已有获准外部范围的 CB4；不读取 dm6 封存标签。TE_Bench 官方果蝇背景模型用于用户明确要求的合成模拟，不将其称为新真实 dm6 评价。

模拟模型包括背景 k-mer/GC、重复片段与嵌套分布。使用官方 `createModel.pl` 和 `createFakeSequence_dfam.pl`，保留外部代码及其 GPL-3.0 许可，不复制到本项目主体。官方下载包包含模型源和部分测试注释，未提供可直接作为本批输入的完整模拟 FASTA；本批是 TE_Bench/GARLIC 派生模拟，不是论文原始模拟结果重跑。

生成器使用 `--useBED --no_simple --write_base`，不使用 `--align`。直接保存生成时的片段位置，避免以之后的 BLAST 重建结果充当生成真值。PERL 进程 seed42，固定 hash 迭代环境；保存生成资产。最终输入统一大写，去掉 softmask 对真值的提示。

## 真值资格

- 核实 FASTA 长度、BED 坐标和片段 union 与实际小写插入材料一致；末端截断按实际序列明确记录。
- 按 repeat type 区分 TE、非 TE 与未决类别；未决类别从严格 L1 分母中排除。记录实际生成 family 及库匹配覆盖。
- L1 评价是该合成生成过程下的材料真值。背景由模拟器生成，不代表真实基因组中已证实的阴性。
- `urep` 是顶层插入组，不是每个嵌套子插入的唯一生物身份。暂不据此计算 L3 插入恢复；方向字段也不在未经验证时当作真值。

## 比较设计

固定 GLM checkpoint、窗口和已有阈值，禁止在模拟 EVAL 上重新标定。比较 fixed-library RepeatMasker、RepeatModeler2→RepeatMasker、HiTE，并补齐 TE_Bench 中的 EDTA 与 Earl Grey。不同工具拥有的 library/蛋白证据逐项披露，区分参考辅助与 de novo 管线；不给任何方法隐藏的生成位置/生成 family 标签。

每个 native cell 16 CPUs、80 GB、最多 24 h，完整端到端阶段计时；所有失败、超时与缺失保留为状态而不是零分。模拟和真实各一套完整输入，共十个 native cells。模型 GPU 与 CPU 的完整特征/forward/合并成本分开报告，不能把 GPU forward 与传统全流程 CPU 时间直接排名。

在正式 native 作业前将具体命令、版本、库范围和固定 GLM 写入配置。模拟生成库与固定参考库均来自Dfam3.9，这是有利于参考方法的条件；据此限制结论，不把本模拟称为无偏新家族发现，也不声称合成胜出等于真实生物优势。

实际条目覆盖已核实：生成用366个参考条目名称全部按Dfam精确NM及accession匹配到固定RM实际lineage库，无歧义或缺失。该计数包含LTR/内部区段独立记录及rRNA，不能等同于366个生物TE家族。accession匹配忽略末尾版本号，未宣称consensus逐碱基完全相同。详见[库覆盖结果](../../reports/TE-LONG-BENCH-20260915/library-exposure/RESULTS.md)。

来源：[TE_Bench](https://github.com/hkania/TE_Bench)、[论文](https://link.springer.com/article/10.1186/s13100-026-00405-z)、[Dfam 3.9](https://www.dfam.org/releases/Dfam_3.9/families/)。

## 执行资格修正（首次正式比较前）

现有 Dfam4 安装只有 curated 组件，FamDB 请求全 lineage 时报告缺少 uncurated 分区但仍以 exit0 输出部分 FASTA。该输出不能代表完整库。保留 CB4 初次固定 RM 和 EarlGrey 尝试，固定 RM/EarlGrey 的初始参考库统一改为已安装完整分区的 Dfam3.9 lineage curated+uncurated，RepeatMasker 引擎仍固定4.2.4。EarlGrey 使用官方 `-l` 显式传入同一库；RM2/EarlGrey 内部 Dfam4 curated 分类组件与 HiTE/EDTA 原生证据另行披露。导出 stderr 明示缺失时禁止继续评分。

## EarlGrey 容器兼容性恢复

CB4 `12732198_4` 与模拟 `12731947_4` 均在 TEstrainer 已生成精炼库后退出。原镜像的 EarlGrey 脚本用 `find -printf` 选择输出目录，但镜像内 BusyBox find 不支持此参数；脚本将该错误重定向后，由 `pipefail` 触发 exit1。已在同一镜像、同一工作目录复现，非生物学无候选结果。

`native.py` 对实际安装脚本的这一处目录选择替换为 Python 按目录修改时间选取，保持处理阶段、模型、库和参数不变。原始镜像与两次失败目录保留；续跑复制各自工作目录并复用已完成精炼库，不再运行发现和精炼阶段。CB4/模拟续跑为 `12735632_4` / `12735633_4`。截至恢复核查，两者均已进入最终 RepeatMasker 阶段，尚未形成最终 benchmark 结果。

原失败耗时6359.03/7942.04秒从84600秒总预算扣除，复制及续跑耗时继续计入；`wall_seconds` 报原尝试加续跑总时间，另存 `attempt_wall_seconds`。这是有失败恢复记录的全流程成本，不能伪称一次无中断运行的耗时。最终评分12732389已实际更新为等待全部14个选定cell终态，旧失败记录仍在attempts配置。详见[恢复记录](../../reports/TE-LONG-BENCH-20260915/earlgrey-recovery/RECOVERY.md)。
