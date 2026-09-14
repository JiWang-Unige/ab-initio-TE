# 论文系统梳理与交付记录

日期：2026-09-14，Europe/Zurich。

## Git 与 Pro 送审

- 基线：`c6781414794c120e41f67d9b43859a4d28453065`，本地 main 已提交最新研究进展、框架退役状态和本轮证据导航；提交后工作树干净。
- 附件：`/Users/jiwang/Desktop/TE/manuscript-review-20260914/ab-initio-TE-manuscript-snapshot-20260914.zip`，约 36 MiB，完整已跟踪工作树 2,882 文件；另附 `MANUSCRIPT-EVIDENCE-BRIEF-20260914.md`。
- 通过内置浏览器向 **6 Pro** 实际发送，页面确认附件和用户完整十问；Pro已完成，用时46分22秒。
- 对话：[科研梳理与论文初稿](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。Pro 在可见进度中明确报告已成功解压 2,882 文件。这证明附件访问，不等于逐行语义审计全部文件。
- 已交付十问决策、完整英文论文初稿、主图/补图设计和按必要性排序的补实验。已完成的是系统梳理与完整初稿，不是实验补齐、图版制作或投稿定稿。
- GitHub API 本轮确认 origin 仓库为 public。当前已完成本地提交；新增未发表内容的公开推送单独向用户询问，未获回复前不推送。用户已经明确授权本研究结果交给 ChatGPT Pro，无需再次询问该送审。

## 送审后的补充取证

项目外旧整理包 `ab_initio_TE_results_organized_2026-08-22/05_superfamily_embedding_传统工具与未完成项.md` 明确把 hg19→hg38/hs1 时间切分新增注释 enrichment 列为未完成；该包 SOURCE_NOTES 的证据截止为 2026-08-12。它支持“历史尚未完成”的判断，不独立证明之后从未执行。当前仓库检索也尚未找到完成结果。

Omnibenchmark 官方当前 [CLI reference](https://docs.omnibenchmark.org/latest/reference/) 说明 `ob run` 将 `--` 后的参数直接传给 Snakemake，并提供 dry run、局部 module、环境能力和可选 remote storage。官方 [how-to](https://docs.omnibenchmark.org/latest/howto/) 说明 Apptainer backend 支持 Linux；macOS 本机验证环境与 Baobab 容器执行应分别规划。由此推断可作为现有适配器的轻量调度封装；本轮未安装、未验证本项目 SLURM 接入，不能说已跑通，也无需为论文自动搭建 S3 或网站。

## 完整结果

完整本地阅读入口：[论文交付目录](../manuscript/20260914/README.md)。内置浏览器附件下载未落盘；通过页面“复制回复”获取并保存了62,590字符的完整Markdown原文，文件为 `docs/manuscript/20260914/pro-full-response.md`。随后按原有章节提取英文稿、中文决策和图表/补实验文件；没有冒充下载成功的独立附件或审阅ZIP。原始附件中的额外证据附录和核算脚本仍在Pro对话。

Pro建议收敛为TE材料检测到可用注释的评估/机制论文，主要完成结果包括：六物种内部共享材料检测、两seed训练坐标覆盖收益、受控上下文/边界/初始化比较、HN信息增量与whole-gap动作不可行并存、旧C未增加正确CDS链。通用外部验收、MoE、真正superfamily工具、无监督新家族发现、历史版本后来证实、P3基因注释和转录调控收益均尚未建立。

本轮对Pro提出的实质更正进行了源码/原表核对：main4宏F1不剔除BG/Unknown混淆；所选路由组leave-clade命中13/22，且probe regret实际为oracle；共享D使用500M H0 loader。另从六物种JSON重算分母及三个宏指标，与稿件数字一致。送审导航已更正；原版在 `c678141` 内可追溯。

优先级是已有主结果的预测/坐标/版本记录补齐，以及一个同实例当前D/传统完整workflow比较。独立L1、CPU/GPU性能、原Tiberius U/P/R分别由是否保留外部泛化、高效部署和gene-benefit主张决定。新增散列/索引不是默认工程任务，先复用已有记录。新的实验和公开发表均不因顾问建议自动获准；本轮未执行新实验，也未修复/重提smoke。
