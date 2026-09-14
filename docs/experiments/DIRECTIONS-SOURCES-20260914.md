# 研究方向补充：原始来源、物种候选与实验边界

**日期：** 2026-09-14

**用途：** 给本轮 ChatGPT Pro 梳理和后续实验设计使用。本文只做有界定向的原始论文、官方数据库和官方文档取证；本轮没有启动实验，也没有把项目历史输出重新判定为当前结果。

## 先给结论

最适合先做的是 **同一 Release 6 坐标系列的 *Drosophila melanogaster* annotation-revision 对照**：FlyBase 同时提供 R6.31 和当前 R6.68 的版本化转座子序列/注释文件，且官方说明 R4/R5 的旧注释曾被重新映射到 R6，当前 Repeat region track 还可能过时。这能把“模型预测的旧版 FP 后来被新注释支持”从一个人类特例变成可复现的版本修订问题。正式运行前应记录 release provenance、contig 长度并做逐序列可比性核验，确认属于同一序列坐标体系；不把文件 md5 作为额外框架。

第二候选是 ***Arabidopsis thaliana*** 的 TAIR10→Araport11：TAIR 官方统计页把两版列为同样的 119.1 Mb assembly，但统计中的 “transposons and pseudogenes” 是合并项，不能直接当作 TE 数量；应逐条解析 GFF 的 feature type。TAIR12 是新的高完整度 Col-0 assembly，并含专门的 TE 重注释，适合做 assembly+annotation 的另一层验证，不能与 TAIR10→Araport11 混为 annotation-only 对照。

人类 hg19→hg38→hs1 结果可以形成“annotation revision support”子论点，但不能把更新版本标签直接当作真值。*D. melanogaster* 和 *A. thaliana* 的版本对照优先用于检验该现象是否可迁移；斑马鱼和爪蟾适合做注释不完整压力测试，因为已有原始研究显示非哺乳动物中存在广泛的 TE/基因错注释，但其常用旧新 UCSC tracks 主要仍是 assembly 变化，不能冒充独立新版 TE ground truth。

RC/strand 方向应作为输出约束的消融，不能把所有输出强制成同一类 invariance。物质存在和边界概率应在 reverse-complement 下保持一致；插入方向、家族方向和调控方向应保留 equivariant/orientation-aware 输出。fragment linking 应预测“两段是否属于同一个 insertion”，不应再命名为“填补 gap”。Dfam profile HMM 已由 seed MSA 的位置特异残基和 indel 概率表示家族内部变异；multi-prototype 是公平的检索表示比较，不是对 Dfam 或传统 library 的全盘否定。

## 一、必须先固定的科学边界

### 1. “旧版 FP 被新版支持”是修订支持证据，不是自动真值

对任一旧版本预测区间 $P$，建议先建立三层标签：

1. **旧标签：** 旧 assembly/annotation 中是否标为非 TE；
2. **更新标签：** 在新 annotation 中是否有独立 TE feature，以及 family/superfamily 是否相容；
3. **assembly 层：** 区间是否能唯一 lift-over、序列是否仍存在、是否发生重排或坐标不确定。

只有同时满足唯一映射、目标序列存在、非模型来源的新 annotation 有清晰 overlap、且 family 证据不矛盾，才计为“revision-supported candidate”。无法映射、重复多重映射、仅因 assembly 新增序列而出现、或只有同一个模型的检索证据，应分别保留为 `unmappable`、`assembly-only` 或 `model-supported`，不能计作 rescue。若没有独立 instance identity，rescue 的分母只能是 candidate/reference-record/segment 或 bp。

人类实验尤其需要报告 **candidate 数和 bp 数** 两个稳定分母；只有在独立证据能确认 biological instance identity 时才报告 insertion 数，否则报告 reference-record/segment 数，不从 binary fragment 凭空构造 insertion。hg19 一条染色体训练、其余 hg19 染色体测试可以检验 chromosome-held-out generalization；它不能单独证明跨物种泛化，也不能在看到 hg38/hs1 rescue 后重新调阈值。若要支持“注释不完整压低 F1”，主张应写成“新版独立 annotation 支持部分表观 FP 来自标签缺失；量化旧标签对 observed precision/F1 的影响需要独立抽样与完整分母”，不推断 recall 偏差方向，也不写成“所有 FP 都是真阳性”或“可由 genome composition 预测 confidence”。

### 2. 同一物种的多版本不是同一种证据

- **候选 annotation-revision-only 对照：** *D. melanogaster* R6.31→R6.68；*A. thaliana* TAIR10→Araport11。两者都要先核实逐序列可比性和坐标兼容性，资格确认前不称为已成立的 annotation-only 对照。
- **assembly+annotation 候选：** hg19→hg38→hs1；*D. melanogaster* R5.57→R6.68；*A. thaliana* TAIR10/Araport11→TAIR12。
- **assembly-control 候选：** UCSC danRer10→danRer11 和 ce10→ce11 的 RepeatMasker tracks。相同或相近工具/库版本使其可用于显示 assembly 变化，但它们不提供独立的新版人工 TE truth。

## 二、物种和版本候选

| 优先级 | 物种与版本 | 可直接取得的来源 | 适合回答的问题 | 关键限制 |
|---|---|---|---|---|
| 1 | *D. melanogaster* Release 6.31→6.68 | [FlyBase Downloads Overview](https://wiki.flybase.org/wiki/FlyBase:Downloads_Overview)；[R6.31 transposon FASTA index](https://s3ftp.flybase.org/genomes/Drosophila_melanogaster/dmel_r6.31_FB2019_06/fasta/index.html)；[当前 R6.68 index](https://s3ftp.flybase.org/genomes/Drosophila_melanogaster/dmel_r6.68_FB2026_02/fasta/index.html) | 同一 Release 6 坐标系列中，annotation 更新能否把旧 FP 变成新 TE 支持 | 需做逐序列可比性与坐标核验；FlyBase 也说明旧 track 可能过时，不能把当前文件当完美 truth |
| 1b | *D. melanogaster* R5.57→R6.68 | [R5.57 FASTA index](https://s3ftp.flybase.org/genomes/Drosophila_melanogaster/dmel_r5.57_FB2014_03/fasta/index.html)；[Release 6 reference paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC4352887/) | assembly 改善与 annotation 修订共同作用时的 rescue；可作为人类三 assembly 结果的类比 | Release 6 填补/改进了大量 repeat-rich 区域，assembly 和 label 两因素无法完全拆开 |
| 2 | *A. thaliana* TAIR10→Araport11 | [TAIR official Genome Annotation page](https://phoenixbioinformatics.atlassian.net/wiki/spaces/COM/pages/42216279/Genome%2BAnnotation%2Bat%2BTAIR) | 若逐序列核验确认可比，测试 annotation 版本更新是否改变 TE label support | 两者长度同为 119.1 Mb 不证明序列相同；页面统计把 transposons 与 pseudogenes 合并，必须按 GFF feature type 和 provenance 重算 TE 数 |
| 2b | *A. thaliana* TAIR12 | [TAIR12 primary paper](https://academic.oup.com/genetics/article/232/4/iyaf248/8369148)；[TAIR12 BioProject](https://www.ncbi.nlm.nih.gov/bioproject/1358071) | 新 Col-0 assembly、centromere/rDNA 完整化及 TE 重注释能否支持旧版疑似 FP | 145.2 Mb 新 assembly；适合 assembly+annotation 分析，不能作为 TAIR10→Araport11 的同一 assembly 替代品 |
| reserve | *D. rerio* danRer10/GRCz10→danRer11/GRCz11 | [danRer10 UCSC bigZips](https://hgdownload.soe.ucsc.edu/goldenPath/danRer10/bigZips/)；[danRer11 UCSC bigZips](https://hgdownload.soe.ucsc.edu/goldenPath/danRer11/bigZips/)；[TE misannotation study](https://doi.org/10.1186/s13059-023-03102-9) | assembly 变化和非哺乳动物 label incompleteness 的压力测试 | 两版 UCSC RepeatMasker 使用相近的旧 engine/library；不是独立新版人工 annotation |
| reserve | *C. elegans* ce10→ce11/WBcel235 | [ce10 UCSC bigZips](https://hgdownload.soe.ucsc.edu/goldenPath/ce10/bigZips/)；[ce11 UCSC bigZips](https://hgdownload2.soe.ucsc.edu/goldenPath/ce11/bigZips/)；[WormBase data paper](https://doi.org/10.1093/genetics/iyac003) | 可作为当前秀丽隐杆线虫较弱结果的物种诊断和 assembly-control | 公开 RepeatMasker 轨道的独立新版 TE truth 较弱；不建议单靠它形成 annotation-revision 主结论 |

### 为什么把果蝇放在第一位

FlyBase 的官方下载说明明确列出 Release 6 的版本化 transposon FASTA，并说明：绝大多数旧 TE insertion 注释最初来自旧 Release；旧 R4/R5 注释后来尽可能 remap 到 R6，仍有不能 remap 的条目；当前 Repeat region track 由旧分析 lift 到 R6，可能已经过时。这正好提供三个可分层的标签：旧注释、同一 Release 6 的新版注释、跨 assembly 的 remap 结果。

Release 6 论文还记录了 repeat-rich heterochromatin 的大规模改进和残余未解析区域。因此 R5→R6 适合作为 assembly confounding 的正面对照，而不是和 R6.31→R6.68 合并成一个数字。FlyBase 当前版本说明可见 [release notes](https://flybase.org/docs/releasenotes.tx)；文件中应记录实际下载的 release/date，不要只写“FlyBase current”。

### 为什么把拟南芥放在第二位

TAIR 官方页面同时给出 TAIR10、Araport11 的 release 统计，并把两者列为 119.1 Mb；这使它成为第二个可验证的同坐标 annotation revision 候选。可是页面统计项是 “transposons and pseudogenes”，不能直接用 4,827 或 4,853 作为 TE ground truth。TAIR12 论文则明确说明旧 Araport11 已近十年、TAIR12 使用新高完整度 assembly 并重新进行 TE annotation，所以 TAIR12 应单列为 assembly+annotation 层。

### 哪些物种可以说明“注释不全”而不能直接充当新版 truth

Hassan 和 Adelson 的原始 Genome Biology 研究在斑马鱼、爪蟾等非哺乳动物中发现广泛的 TE/CDS overlap 和 TE 被误标为一般转录因子的现象，支持“非哺乳动物 label incompleteness 可能更严重”的动机。它不等于某一条 UCSC track 的逐区真值。故斑马鱼/爪蟾适合做预注册的 stress case：报告模型候选与 independent homology/curation evidence 的交集；不要把同一套 RepeatMasker 输出当作改进后的 gold standard。若已有六物种含 *C. elegans*，建议把它先作为低结果的诊断物种，而不是再据单一 F1 推断“该物种不可用”。

## 三、hg19→hg38→hs1 的可发表设计

固定一个 GLM、固定训练染色体、固定阈值和冻结的旧版预测后，对其余 hg19 染色体执行以下流程：

1. 保存旧版 negative/FP 候选的坐标、方向、family、模型分数和 fragment/insertion 标识；
2. 对每个候选分别做 hg19→hg38、hg19→hs1 的唯一 chain mapping；保留 `unique`, `multi-map`, `unmapped`, `sequence-changed`；
3. 仅在目标序列存在且映射长度/方向满足预先固定规则时，与独立的 hg38/hs1 TE annotation 做 overlap；
4. family/superfamily 相容性另记一列。仅有 “某处有 TE” 而没有同源序列或方向支持的不能算 rescue；
5. 对旧 FP 分三类报告：`revision-supported`, `assembly-only/indeterminate`, `still-negative`，并分别给 candidate 和 bp 的数量和比例；只有独立 instance identity 可得时，才补充 insertion 数；
6. 预先冻结 rescue 规则后，再检查 rescue 比例是否随旧 annotation 的已知不完整区域、重复类型或低复杂度发生变化。

T2T 研究显示，CHM13 的 gap-filled sequence 中发现大量此前缺失或未被目录收录的 repeats，且用 T2T repeat database 重新标注 GRCh38 可找到超过两 Mb 的此前未编目 repeat（[primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC9301658/)）。这支持“reference/library revision 会改变 label”的背景，但不能替代上述候选级 mapping 证据。

## 四、RC、strand 和 biological prior

双链 DNA 的 material/boundary 预测通常应满足 reverse-complement 下的相同输出。Zhou、Shrikumar 和 Kundaje 的系统比较显示，简单 RC augmentation 不能保证模型在 RC 下相同；post-hoc conjoined/test-time RC averaging 是可靠的起点，RC parameter sharing 并非在所有任务中都最好（[PMLR paper](https://proceedings.mlr.press/v165/zhou22a.html)，[PDF](https://proceedings.mlr.press/v165/zhou22a/zhou22a.pdf)）。eBCN 的原始研究进一步指出，早期强制 strict invariance 可能限制有方向性的 motif；内部 representation 可 equivariant，最终输出再按任务决定 invariant 还是 orientation-aware（[eBCN paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6596897/)）。

推荐的最小消融顺序是：

- plain baseline；
- RC augmentation；
- frozen model 的 test-time RC averaging/post-hoc conjoined；
- parameter-tied RC equivariant 版本；
- 仅对存在生物学依据的类别加入 TSD、TIR、LTR-pair 或 motif prior。

每个版本同时报告 material F1、boundary F1、family/orientation accuracy、gap-edge accuracy 和 RC disagreement。不要把 TSD/TIR 当作所有 TE 的硬规则：退化片段、非自主元件、nested insertion 和不同家族未必保留这些信号。该方向的成功标准应是边界/方向一致性和跨 chromosome/species 稳定性改善，而不是只看 aggregate F1。

## 五、fragment linking 的干净定义

RepeatCraft 的原始论文把 RepeatMasker 产生的碎片合并为较完整的 repeat annotation：strict 规则要求相邻碎片有相同 repeat family、在 consensus 上连续且中间没有不同家族；loose 规则允许短的中间 repeat，默认最大间隔 150 bp，并结合距离、consensus coverage、family 和 orientation（[RepeatCraft paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6419915/)；[implementation](https://github.com/niccw/repeatcraftp)）。这说明已有工作解决的是**候选碎片的同一 repeat 合并**，不是对任意 assembly gap 生成 sequence，也不是保证整个 gap 属于一个 insertion。

因此将实验单位定义为：

\[
F_i=[s_i,e_i],\qquad p_{ij}=P(z_i=z_j),
\]

其中 $z_i$ 是所属 TE insertion。比较四级证据：

- **B0 distance：** 仅以 $d_{ij}$ 为输入；
- **B1 rule：** distance、orientation、family、overlap、fragment length，固定一个 RepeatCraft-like 规则；
- **M2 sequence：** 加入 $h_i=Encoder(F_i)$ 和 $h_j$；
- **M3 context：** 再加入 $h_{gap}$、left/right context 和方向。

负例必须包含同一家族但相邻的独立 insertion、nested repeat、相反方向、同一 gap 两侧但证据支持两个 insertion 的情况；否则模型只会学习“同 family + 近距离”。评估分开做 pair AUROC/PR、insertion/cluster F1、base-level material/boundary F1 和 calibrated precision。M3 如果判定两侧相似但中间序列支持独立 insertion，这应被记录为正确的 `separate` 关系，不能被当作 gap 失败。建议输出 uncertain/indeterminate，不把未知 gap 强行标成 negative 或 positive。

## 六、Dfam 与 multi-reference 的公平实验

Dfam 的基本单位是 TE family 的 seed MSA，并从中提供 consensus 和 profile HMM；pHMM 通过位置特异的残基、插入/缺失概率表示家族内部变异（[Dfam help](https://dfam.org/help)；[Dfam original paper](https://academic.oup.com/nar/article/41/D1/D70/1073076)；[Dfam community paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7805219/)）。因此论文中应写成“multi-prototype 检验另一种 sequence retrieval representation”，不要写成“single consensus 是传统方法的普遍错误”。

Arabidopsis 的原始研究直接比较了 multiple reference sequence sets，报告额外检测到 TE sequence，并指出一个真实 consensus 加上捕捉家族结构多样性的 mosaic/reference set 可以补充新片段和 extension（[Buisine, Quesneville & Colot, 2008](https://pubmed.ncbi.nlm.nih.gov/18343092/)，[DOI](https://doi.org/10.1016/j.ygeno.2008.01.005)）。这使该假设有先例，但仍需要严格匹配候选数和阈值。

建议的预注册比较矩阵如下：

| 组 | reference representation | 必须匹配的内容 |
|---|---|---|
| C1 | 每 family 一个 consensus | 从同一个冻结 seed MSA 生成；同一 family 集合 |
| C2 | 每 family $k=2,4,8$ 个 prototype/mosaic | 同一 seed MSA、同一 family 集合；报告 library bytes 和 candidate 数 |
| C3 | 同一 family 集合的 Dfam pHMM | 不改变 query、family prior、搜索阈值或 FDR 规则 |
| C4 | random matched-size/basic k-mer | 匹配 prototype 长度、GC/k-mer 分布和候选预算，作为容量/相似度控制 |
| C5 | GLM embedding retrieval | 固定 embedding、相同 top-k/候选预算；单独评价 retrieval 与 annotation |

公平性约束：

1. 先按 TE family 或 homology cluster 划分 train/validation/test；copy-level random split 只能回答同家族检索，不能回答 novel-family 泛化；
2. 所有方法使用相同 query fragments、相同 family 集合和相同候选数上限，或明确给出 library bytes/candidate-count 曲线；
3. 在冻结的 negative validation set 上选择阈值，使用统一的 per-query FDR 或 family-wise error 控制；不要用 multi-prototype 的 raw max similarity 直接与 single-consensus 的 raw score 比；
4. 分开报告 **retrieval**（Recall@k、MRR、candidate precision、family assignment）与 **annotation**（interval/boundary/insertion F1）；multi-prototype 可能只改善候选召回而不改善边界；
5. 对 $k$ 增大带来的 multiple-testing、存储和运行时间单独报告；若 C2 只在更大候选预算下胜出，结论应写成“accuracy-cost trade-off”；
6. profile-HMM 与 consensus 应尽量从同一个 seed MSA 生成，避免 family selection、training data 或阈值同时变化。

## 七、建议给 Pro 的推进顺序

1. 先冻结并复核人类 hg19→hg38→hs1 的 mapping/rescue 口径，形成 candidate/bp 表，并在有独立 instance identity 时补充 insertion 表；这一步决定“FP 是 annotation revision 还是 assembly-only”。
2. 用 *D. melanogaster* R6.31→R6.68 做第一套同 Release 6 外部版本复核；若旧新版 GFF provenance 和坐标一致，再加 *A. thaliana* TAIR10→Araport11。
3. 用 R5→R6、TAIR12、danRer10→11 或 ce10→11 做 assembly confounding/压力层，不能与 annotation-only 结果合并。
4. 在已冻结的 fragment 输出上做 pair-level linking；先实现 B0/B1，再加入 sequence/context，输出 same-insertion 与 separate-insertion 两类。
5. 对 RC 先做 augmentation 和 test-time/post-hoc conjoined，再考虑 tied equivariance；把 material、boundary、orientation 分开评价。
6. 最后做 multi-reference：C1–C5 同预算、family split、统一 FDR，明确 retrieval gain 是否转化为 annotation gain。

## 直接原始/官方来源

1. [FlyBase Downloads Overview](https://wiki.flybase.org/wiki/FlyBase:Downloads_Overview)；[FlyBase bulk data](https://flybase.org/downloads/bulkdata)。
2. [The Release 6 reference sequence of the Drosophila melanogaster genome](https://pmc.ncbi.nlm.nih.gov/articles/PMC4352887/)。
3. [TAIR official Genome Annotation](https://phoenixbioinformatics.atlassian.net/wiki/spaces/COM/pages/42216279/Genome%2BAnnotation%2Bat%2BTAIR)。
4. [TAIR12 primary paper](https://academic.oup.com/genetics/article/232/4/iyaf248/8369148)。
5. [Fake IDs? Widespread misannotation of DNA transposons as a general transcription factor](https://doi.org/10.1186/s13059-023-03102-9)。
6. [From telomere to telomere: The transcriptional and epigenetic state of human repeat elements](https://pmc.ncbi.nlm.nih.gov/articles/PMC9301658/)。
7. [Towards a Better Understanding of Reverse-Complement Equivariance for Deep Learning Models in Genomics](https://proceedings.mlr.press/v165/zhou22a.html)。
8. [An equivariant Bayesian convolutional network predicts recombination hotspots](https://pmc.ncbi.nlm.nih.gov/articles/PMC6596897/)。
9. [RepeatCraft: a meta-pipeline for repetitive element de-fragmentation and annotation](https://pmc.ncbi.nlm.nih.gov/articles/PMC6419915/)。
10. [Dfam official help](https://dfam.org/help)；[Dfam community paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7805219/)。
11. [Improved detection and annotation of transposable elements using multiple reference sequence sets](https://doi.org/10.1016/j.ygeno.2008.01.005)。
12. [Benchmarking methods for de novo repeat annotation](https://pmc.ncbi.nlm.nih.gov/articles/PMC4524446/)。

**本文件的证据等级：** 来源用于设计和主张边界；没有把任何候选物种的版本差异预先计为模型 rescue，也没有据来源替代项目内的冻结数据核验。
