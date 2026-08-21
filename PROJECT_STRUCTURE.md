# Project Structure Contract

本文件是 `docs/16_artifact_registry.md` 的根目录版速查。核心原则：**脚本、配置、训练状态、指标摘要、外部软件输出分开存；docs 只存可审计的结论和索引，不塞大文件。**

```text
scripts/                       通用框架脚本 + 可复用项目脚本
scripts/experiments/<exp_id>/   单次实验专用但会影响结果的生成脚本 / wrapper
pipelines/<pipeline_id>/        流程化 DAG 的 stage 脚本 / wrapper
configs/<exp_id>.yaml           每次训练/分析的参数
sbatch/<exp_id>.sbatch          Slurm 提交脚本
runs/<exp_id>/                  checkpoint / tensorboard / 完整训练状态
reports/<exp_id>.json           指标摘要，validate_goal 可读
outputs/<exp_id>/STATUS         作业状态小文件
logs/<exp_id>/                  stdout/stderr 与长日志
software_outputs/<tool>/<run_id>/  第三方软件原始输出 + command/version/hash
external_runs/<source>/         冷导入(/ingest-existing)时外部已有训练 run / 结果的落位区（未经框架产生）
goals/                          goal 合约 / iteration-goal 模板
templates/                      docs / 配置脚手架模板
refs/{pdfs,repos,supp,dossiers}/  文献、代码、补充材料、数据/指标 provenance
wiki/{ideas,notes}/             可检索想法与笔记
docs/                           主记忆：计划、结果、决策、投稿/流程策略
data/{raw,interim,processed}/   数据分层：raw 只读、interim 可重建、processed 可实验
analysis/notebooks/             探索性分析
manuscript/                     投稿图表/补充材料草稿
worktrees/<exp_id>/              optional git worktree 并行代码隔离区（共享代码冲突时才用）
```

任何新文件无法归类时，先运行 `/artifact-registry` 更新目录契约，再落盘。多方向同时修改共享代码时，先运行 `/workspace-matrix` 更新 `docs/17_parallel_workspace.md`，再建 worktree。
