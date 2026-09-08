# A 原候选母体 coverage 审计

只做 CPU 原生 tokenizer 几何审计，不载入 checkpoint、不执行神经网络、不训练、
不计算 donor 决策、不改缓存与 stats。输入仍是原候选 chr3/chr5 的 TRAIN 和 chr13
全部 DEV/CAL_FIT/CAL_GATE；known/unknown 都保留。CAL 仅进入不使用标签目标的
序列覆盖审计，不运行 calibration。chr19–22 region 不读取。

运行（需 Slurm CPU allocation，推荐 generanno 环境）：

```bash
python scripts/experiments/GAP-BRIDGE-A-COVERAGE-20260906-R1/audit_coverage.py \
  --candidate-manifest outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv \
  --region-root outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1 \
  --nt-model software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42 \
  --output outputs/GAP-BRIDGE-A-COVERAGE-20260906-R1/audit-20260906-r1
```

输出目录必须是新目录。输出包括 engineering `coverage_audit.json`、有缺口的原生
窗口坐标区间 `uncovered_windows.tsv.gz`、非全覆盖候选几何/缺失 bp
`partial_candidates.tsv.gz`。后者也含完全 uncovered 的候选。JSON 按 chromosome、
role、原 length_stratum、crop seam、known 联合分层，并附原 candidate block 归属。
没有候选的 block 不产生行；不会从此表推断整个 chr13 DEV partition。
candidate bp 是 occurrence-weighted，重叠 crop 会重复计 bp；native-window bp 是
该染色体 required native windows 的去重 bp，不冒充全染色体 bp。

实现直接执行生产 `strict_segment_eval.infer_probs_for_label_mode` 的原函数源码和
生产 `te_token_task.load_tokenizer`；tokenizer 路径分支与 `load_trained_model` 一致。
仅替换网络输出为长度等于 encoded token 轴的 shape sentinel，并复用已冻结的
`prepare_pair.native_nt_window` actual-branch trace 记录覆盖；sentinel probability
绝不输出为 NT 概率。该等价依赖 frozen auto_token token classifier 保持 token 轴，
不证明未来实际模型推理不会失败/改变输出形状；真实模型 forward exception 可能触发
strict fallback，这种 runtime 分支变化不在 tokenization-only 审计证明范围。
原 smoke 已是实际模型前向证据。

每次作业先使用真实 native tokenizer 检查全 ACGT 与 leading-800-N 两个 sentinel；
单测额外通过执行生产 adapter 源码，分别验证 offsets/fallback 的 ACGT、N 截断、
真实短尾和跨 seam crop 投影。有限数值不是覆盖证据。

`primary_metric=1` 只表示审计完整完成；发现 coverage 缺口是有效诊断，不能因此让
作业失败，也不能过滤候选/用初始化 0 当概率。任何原 crop 缺失 token 覆盖都会阻止
当前不变的全候选 A 输入合同，下一步须先审阅，不自动切 tokenizer 或完整训练。

规划资源：0 GPU、2 CPU、12 GB、预计约 1 h（未实测），2 h 上限。约 0.5 Gb
允许序列需要最多约 120k native windows，逐染色体保留 bool coverage，JSONL
流式读取；结果压缩表而非全 bp 矩阵。本目录不提供或调用 Slurm 提交入口。
