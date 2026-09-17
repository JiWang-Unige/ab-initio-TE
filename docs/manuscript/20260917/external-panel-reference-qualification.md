# 外部候选物种的 assembly / annotation 资格审阅

**审阅日期：** 2026-09-17

**范围：** 仅审阅 `multispecies-closure-plan.md` 中列出的 medaka、silkworm、stickleback、turkey、*D. simulans* 和 oyster 的项目暴露、assembly 配对及公开注释来源。没有运行模型、下载大数据、打开 sealed 评分，也没有新建确认集。本文件的“优先”只表示资料资格和可执行性，不表示模型分数或生物学表现。

## 结论

当前最多保留两个条件性优先对象，并且两个都属于非哺乳动物：

1. **medaka (*Oryzias latipes*, `oryLat2`)：优先级 1。** 项目中已有与 `oryLat2` 配对的 FASTA 和 preliminary RepeatMasker/UCSC 风格区间，且 UCSC 仍公开同一 assembly 的 FASTA、chromosome sizes 和 `fa.out`。但它是2005年的MEDAKA1，公开TE标签使用2006年的库，只能作为方便准备的历史鱼类资产，不能据此优先选为最终确认基因组。
2. **silkworm (*Bombyx mori*, `GCF_014905235.1 / Bmori_2016v1.0`)：优先级 2。** 项目中已有同一 accession 的 FASTA 和 preliminary repeat 区间；UCSC/NCBI 公开了同一 assembly 的 RefSeq gene annotation 入口。它可作为昆虫候选，但当前 TE 区间仍是 preliminary/source-dependent，不能直接当作独立真值。

这两个对象都**没有证据显示已进入当前 D 六物种监督训练或当前固定外部 screen**。旧备份 manifest 中的 `role_from_backup=train` 只证明历史资产曾被列入过一个旧目标集，不能改写为当前模型的训练暴露。当前 D 的训练表仍是 human、mouse、pig、chicken、zebrafish 和 *C. elegans*；SF5 的物种表也不包含这两个候选。

stickleback 目前没有可用的 TE annotation layer；turkey、*D. simulans* 和 oyster 在本次有限检索中没有项目级 assembly/annotation 配对或运行暴露证据。因此它们暂不具备进入确认面板的资格。这个结论是“资料未资格化”，不是对其模型泛化能力的负面结果。

## 逐候选证据

| 候选 | 项目中可配对的 assembly / annotation | 公开来源证据 | 当前项目暴露 | 负类及独立真值资格 | 决定 |
|---|---|---|---|---|---|
| medaka (*O. latipes*) | `oryLat2`；预备 manifest 的 genome size 为 869,000,216 bp，FASTA 为 `.../animals/medaka/oryLat2.fa.gz`，TE 区间为 `rmsk_te.bed.gz`。preliminary layer 有 67,035 个区间、原始区间长度和为 13,056,244 bp；chr1/chr3 的 preliminary TE fraction 分别为 0.014001/0.015002。 | [UCSC currentGenomes/Oryzias_latipes/bigZips](https://hgdownload.soe.ucsc.edu/goldenPath/currentGenomes/Oryzias_latipes/bigZips/) 列出 `oryLat2.fa.gz`、`oryLat2.chrom.sizes` 和 `oryLat2.fa.out.gz`，页面明确为Oct.2005 MEDAKA1，RM open-3-1-6 / RepBase 20061006。另一个[2017 assembly hub](https://hgdownload.soe.ucsc.edu/hubs/GCF/002/234/675/GCF_002234675.1/html/GCF_002234675.1_ASM223467v1.description.html)的 `GCF_002234675.1 / ASM223467v1` 长度734,057,086 bp，**不是oryLat2**；禁止将两者基因/TE坐标混配。 | 只在旧 `P2P3_PRELIM_UCSC_20260615/species_manifest_prelim.tsv` 中有 `animal_a_train_core` / `role_from_backup=train` 记录；不在当前 D 六物种训练表，也不在当前固定 D 外部候选配置。 | `rmsk_te` 是外部/legacy preliminary 标签；`u_quality_prelim.tsv` 的 `all_annotated_repeat_bp=0`、`rn_status=not_constructed`、`claim_eligible=no` 说明它不能提供可靠的 genome-wide 负类或独立 truth。必须锁定 accession、校验 FASTA/标签版本，并在同一 assembly 上自跑固定 RepeatMasker+Dfam Label-A，或另行取得正交证据。 | **优先 1，条件性开发候选。** 可用于准备非哺乳脊椎动物的前瞻性流程；在同版本标签和独立评估层完成前不报告 F1/全基因组准确率。 |
| silkworm (*B. mori*) | `GCF_014905235.1 / Bmori_2016v1.0`；预备 manifest 的 genome size 为 460,349,660 bp，FASTA 为 `.../animals/silkworm/GCF_014905235.1.fa.gz`，TE 区间为 `rmsk_te.bed.gz`。preliminary layer 有 446,424 个区间、原始区间长度和为 129,988,027 bp；NC_051380.1/NC_051358.1 的 preliminary TE fraction 为 0.283706/0.221749。 | [UCSC 的 Bmori_2016v1.0 RefSeq composite](https://hgdownload.soe.ucsc.edu/hubs/GCF/014/905/235/GCF_014905235.1/html/GCF_014905235.1_Bmori_2016v1.0.refSeqComposite.html) 指向同一 assembly 的 RefSeq gene track 和 [NCBI FTP assembly 目录](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/014/905/235/GCF_014905235.1_Bmori_2016v1.0/)。这确认了 assembly/gene annotation 的公开入口，不等于独立 TE truth。 | 只在旧 preliminary/backup manifest 中有 `animal_a_train_core` / `role_from_backup=train` 记录；不在当前 D 六物种训练表，也不在当前固定 D 外部候选配置。 | 当前 TE 区间仍标记为 `external_ucsc_or_legacy_prelim`，`claim_eligible=no`，且 `u_quality` 未构造。NCBI 已有更新 accession 的可能性，不能把新 assembly 的 gene/TE annotation 混配到 `GCF_014905235.1` 上。应锁定旧 accession 或显式改用新 accession 后全套重做。 | **优先 2，条件性开发候选。** 适合补足昆虫方向，但须先固定 accession、重建同版本 TE 标签并定义独立正类/负类。 |
| stickleback (*G. aculeatus*) | 项目旧 manifest 只有 `gasAcu1.fa.gz`，genome size 463,354,448 bp；`annotation_status=missing_annotation`、TE/repeats 路径为空。preliminary chromosome ladder 的 TE interval count 为 0，不应解读为“没有 TE”。 | 本次限定检索未取得可直接配对并已暴露于项目的官方 TE annotation asset。 | 旧 backup manifest 有历史目标集行；无当前 D/SF5 训练或固定 D screen 证据。 | 没有正类层，也不能构造负类；`claim_eligible=no`。 | **暂缓。** 先补齐同 assembly 的可追溯标签和独立评估设计，不能以 zero-interval 运行。 |
| turkey | 本地/远程项目 manifest 未找到候选的 assembly、TE annotation、FASTA 或 inference exposure 配对。 | 未在本次限定检索中建立可引用的项目级官方配对。 | 未见当前 D/SF5 训练或固定 D screen 暴露。 | 无法定义正类或可靠负类。 | **暂缓，资料不足。** |
| *D. simulans* | 本地/远程项目 manifest 未找到固定 assembly、TE annotation 或 inference exposure 配对。 | 未在本次限定检索中建立可引用的项目级官方配对。 | 未见当前 D/SF5 训练或固定 D screen 暴露。 | 无法定义正类或可靠负类。 | **暂缓，资料不足。** |
| oyster | 本地/远程项目 manifest 未找到固定 assembly、TE annotation 或 inference exposure 配对。 | 未在本次限定检索中建立可引用的项目级官方配对。 | 未见当前 D/SF5 训练或固定 D screen 暴露。 | 无法定义正类或可靠负类。 | **暂缓，资料不足。** |

项目内数值均来自 `reports/gates/P2P3_PRELIM_UCSC_20260615/` 的 preliminary 表，而不是重新处理的 genome truth：

- `species_manifest_prelim.tsv`：assembly、FASTA 路径和标签层配对；medaka/silkworm 的 `fasta_md5` 为 `skipped_large_or_missing`。
- `te_len_viz_summary_prelim.tsv`：区间数量、原始长度和及长度分布。
- `chromosome_ladder_prelim.tsv`：固定 preliminary primary/stability 染色体的区间统计。
- `u_quality_prelim.tsv`：明确标注 `prelim_proxy_only`、`rn_status=not_constructed`，不能作为未注释区的真值测量。

## 不能从这些资料推出的结论

1. RepeatMasker、UCSC `rmsk`、`fa.out` 或由它们生成的 `rmsk_te.bed.gz` 可以作为同一标签体系下的 comparator/工作标签，但不能称为独立 ground truth。特别是把所有未标注碱基当负类，会把 library coverage 缺口直接计入模型 FN/FP 解释。
2. 旧 manifest 的 `role_from_backup=train` 不是当前 D 模型训练证据；当前六物种任务监督表支持其不在当前D监督物种名单中；仍应检查历史使用角色后再冻结开发/确认集。预训练暴露未知需另列，不能宣称encoder从未见过这些物种或同源序列；它不自动否定“任务监督外物种”这一较窄描述。
3. preliminary 的 chromosome ladder 只说明资产里存在可读的区间层；它不证明区间准确、完整，亦不证明参考库覆盖充分。stickleback 的 zero interval 反而是缺 annotation 的证据。
4. 当前项目没有为 turkey、*D. simulans*、oyster 找到可直接启动的配对资产；不应为了凑足六个新物种而按分数或“非模式”身份临时替换 assembly。

## 进入实际确认前的最小补齐

对 medaka 和 silkworm 分别完成以下资格门，再决定是否冻结为真正的开发/确认对象：

1. 固定 species、assembly accession、FASTA、chromosome sizes、coordinate convention 和 TE label release；保存可复核的下载地址并核对序列名称/长度与annotation坐标。对 silkworm 不能混用 `GCF_014905235.1` 与更新 accession 的注释。
2. 在完全相同的 assembly 上运行项目固定的 RepeatMasker+Dfam Label-A 生成流程；将旧 UCSC/legacy layer 作为来源敏感性对照，不把它作为独立 truth。
3. 预先定义不依赖模型分数的窗口和正类覆盖。若没有可靠的独立负类，只报告 positive recovery、来源敏感性和人工/正交支持的子集，不报告 genome-wide biological precision/F1。
4. 在看模型结果前分别记录任务训练、项目调参与基座预训练暴露。历史测试/选模角色未排除时只作transfer/development screen；基座预训练未知单列，不与任务监督或新确认集角色混为一谈。
5. 若要连接 Tiberius，另外确认对应 clade 的模型确实消费 softmask；拥有可用 assembly/TE 标签并不自动意味着该物种有合格的下游 gene-annotation receiver。

因此，本文件只完成“候选资格和优先级”审阅，没有把 medaka 或 silkworm 转写成已完成的泛化实验，也没有创建确认集或提交新增推理/训练。作者已有补充实验授权；下一步依赖具体数据和协议，而不是本报告重复请求授权。
