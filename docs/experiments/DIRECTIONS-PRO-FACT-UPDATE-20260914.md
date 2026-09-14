# 第二轮 Pro 事实补充与纠错

2026-09-14。下列内容来自本轮项目文件与 Baobab 取证，供第二轮讨论完成后补充核对。科学建议不是实验结果。

1. **D 已有内部 CONF。** 先前新简报说“仅内部 DEV/SCREEN”过窄：`CROSS-SPECIES-L1-UPSTREAM-20260904.md` 及 `CROSS-SPECIES-L1-UPSTREAM-20260904-CONF.md` 已归档 worm CONF，D F1 为 seed42 `.794878`、seed17 `.803820`，L 为 `.786766`、`.780510`，CPU uncertainty job `12376069` 已闭环。DEV JSON 的 `conf_evaluated=false` 是生成时状态，不能否定后来的 CONF。**仍没有候选外部物种 D 模型输出，也没有 MoE/adapters 实验。** 本轮未打开任何新封存结果。
2. **hs1 不自动代表更新的 TE 库。** Baobab 现存 `hs1.repeatMasker.version.txt` 明确为 Crossmatch `1.090518`、Dfam_Consensus 和 RepBase `RELEASE 20181026`、`-engine crossmatch -s -species Homo sapiens`。hg19/hg38/hs1 组装与比较注释均已找到，但必须另行锁定新版独立注释/同组装新旧库；不能直接称“后来证实”。见 `ANNOTATION-REVISION-ASSETS-20260914.md`。
3. **TE_final 恢复已完成。** 42 个紧凑文件已复制。当前 M5 是 10,000 fragments、12 classes、13 species：k-mer contrastive B0 ARI `.928141`；GLM B1 `.045053`、B2 `.024541`。Archived Phase7 强 B1 ARI `.6928`、NMI `.7164`确有历史报告，但 hg38 五类与六物种七类 panel 描述冲突，raw comparison 缺失，先作为研究线索。精确 `exp002_consensus_100bp` 找到配置、prepare/train/evaluate 脚本，但两处目录没有找到完成 metrics，NEXT_STEPS 中仍为问号。当前可核验本地 Dfam consensus 1800/10-family 表仍为 A1 ARI `.224190`、C1 `.708307`。这些 panel 不得拼接；未找到也不证明它从未在别处运行。见 `TE-FINAL-DFAM-RECOVERY-20260914.md`。
4. **RC 推理已有局部结果。** mouse chr1/NTv2-250M/4096 的历史 screen：forward raw segment F1 `.3062`、forward CRF `.3569`、consensus-min+CRF `.4149`，最后者 boundary F1 `.1267`。没有 RC-consistency loss/等变训练结果；新路线要区别于已经做过的推理合并。
5. **执行准备。** 原批准 Tiberius 缺失变量的最小修复已经在 Baobab 通过针对性测试和六通道 contract；隔离旧失败 `smoke-r1` 后，新 `smoke-r2` job12687393 已提交，13:59附近为 PENDING(Resources)，尚无新科学结果。Omnibenchmark `0.6.0` 已装入项目外独立 Python3.12 环境；接入先用现有 converter/evaluator 做真正端到端 synthetic engineering smoke，不声称实际跑完所有传统方法。Fragment linking 先做 relation-truth 合同和 synthetic hard negatives，保持 material mask 不变，M2/M3 尚不训练。
6. **新版人类资源已定位。** T2T官方 `marbl/CHM13` README明确列出 `chm13v2.0_RepeatMasker_4.1.2p1.2022Apr14.out` 及hg19/hg38↔CHM13v2双向chain。UCSC `t2tRepeatMasker.html` 描述RMBlast2.10.0+、Dfam3.3加T2T/Dfam3.6及HG002Y新条目。它可作为新版比较资源，但引擎与库同时变化，不能当单独library效应；需要配套engine-matched同组装实验。链接已记入human资产文档，尚未下载大track/执行mapping。

请在第二轮方案基础上，只给这些新事实引起的具体修改及并行顺序调整。保持新实验单 seed42；不要要求多 seed，不把旧静态状态当当前结果，不以未找到历史 artifact 否定新假设。
