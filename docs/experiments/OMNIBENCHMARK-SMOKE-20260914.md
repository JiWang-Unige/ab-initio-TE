# OmniBenchmark 最小工程 smoke 记录

**状态：** 已完成本机实际运行；终态为 `ENGINEERING_ONLY`。本记录只覆盖 OmniBenchmark 连通性、坐标转换和失败分母保留，不是 TE 方法结果。

## 范围

本 smoke 使用现有仓库内的一个小 benchmark 目录和根级 `omnibenchmark.yaml` named `default` 入口。DAG 固定为：

```text
fixture → existing adapter convert → existing adapter T0/T1 evaluate → collector
```

fixture 写入两个 contig 的 synthetic FASTA、BED truth、GFF3 prediction、contig lengths 和 cell registry。BED/GFF3 含 contig 起点、终点、重叠 source records 及一处 fragment gap。`T1` 只提供 chrA positive subset，chrB 保持 unknown。

没有运行当前 D、HiTE、RepeatMasker、RM2、EDTA、EarlGrey 或 TEtrimmer；registry 中的 `synthetic_status_unsupported|status|host` 和 `synthetic_status_blocked|status|host` 是专门测试分母保留的工程占位 cell，不代表相应真实方法的能力或失败，两者都保留在 summary denominator。

## 运行契约

- 使用 `/Users/jiwang/Desktop/TE/manuscript-review-20260914/omnibenchmark-venv/bin/ob`，版本 0.6.0。
- 运行时用 `--dirty`，因为 module repository 指向现有项目的本地 working tree；不创建 Git commit。
- 先执行 `ob validate plan` 和 `ob run --dry`，再执行真实 `ob run`；真实运行只使用 host backend 和 synthetic fixture。
- 输出中的 `metrics.json` 复用 `scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py`；T0 保留完整 precision/recall/F1，T1 按现有合同将 precision/F1 置空。
- 输出和 summary 均写入 `ENGINEERING_ONLY` 标志，不能进入论文主结果或方法排名。

## 实际运行与验收

运行命令：

```bash
/Users/jiwang/Desktop/TE/manuscript-review-20260914/omnibenchmark-venv/bin/ob validate plan \
  benchmarks/te_omnibenchmark/benchmark.yaml
/Users/jiwang/Desktop/TE/manuscript-review-20260914/omnibenchmark-venv/bin/ob run \
  benchmarks/te_omnibenchmark/benchmark.yaml --dirty \
  --out-dir /tmp/te-omnibenchmark-run-20260914-d --cores 1 -- \
  --scheduler greedy
```

`ob validate plan` 通过；实际 `ob run` 生成 5 条规则并成功完成 6 个 jobs。run manifest 为 `cdc7446f-39e2-4904-aa55-fb523cef3e39`，运行环境为 macOS ARM64 / Apple M4 / Python 3.12.14。

本次成功 run 的白名单证据已按相对目录归档到 [reports/OMNIBENCHMARK-SMOKE-20260914](../../reports/OMNIBENCHMARK-SMOKE-20260914/)。

关键证据文件：

- [collector summary](../../reports/OMNIBENCHMARK-SMOKE-20260914/collector_summary.json) 和 [manifest](../../reports/OMNIBENCHMARK-SMOKE-20260914/.metadata/manifest.json)
- [T0 metrics](../../reports/OMNIBENCHMARK-SMOKE-20260914/data/fixture/.default/methods/adapter_convert/.default/metrics/evaluate/tier-T0/metrics.json) 与 [T1 metrics](../../reports/OMNIBENCHMARK-SMOKE-20260914/data/fixture/.default/methods/adapter_convert/.default/metrics/evaluate/tier-T1/metrics.json)
- [prediction canonical TSV](../../reports/OMNIBENCHMARK-SMOKE-20260914/data/fixture/.default/methods/adapter_convert/.default/prediction.tsv)、[T0 truth canonical TSV](../../reports/OMNIBENCHMARK-SMOKE-20260914/data/fixture/.default/methods/adapter_convert/.default/truth_t0.tsv)、[T1 truth canonical TSV](../../reports/OMNIBENCHMARK-SMOKE-20260914/data/fixture/.default/methods/adapter_convert/.default/truth_t1.tsv) 和 [cell status](../../reports/OMNIBENCHMARK-SMOKE-20260914/data/fixture/.default/methods/adapter_convert/.default/cell_status.json)

归档还包含 4 份 `performance.txt` 和 5 份短 rule logs；排除了 `.modules`、`.git`、`.snakemake`、cache 以及较长的 Snakemake orchestration log。

1. Omni 解析全局 output IDs，能解析唯一的 root `default` entrypoint，并生成无 unresolved input 的 Snakefile。
2. fixture、convert、T0、T1 和 collector 的 output schema 均存在且可读。
3. T0/T1 指标来自实际 adapter CLI；T0 的 bp F1 为 `0.8837209302325583`，T1 的 bp recall 为 `0.9333333333333333`，T1 的 precision/F1 均为空。
4. 独立集合核对得到 T0 `TP=19, FP=4, FN=1`，T1 `TP=14, FN=1`；与 adapter 输出一致，首尾边界坐标保持为 `[0,5)` 和 `[95,100)`。
5. collector 报告 expected cell 数为 5，observed cell 数为 5，并保留 `COMPLETED=3`、`UNSUPPORTED=1`、`BLOCKED=1`。
6. 额外的缺失证据回退检查中，预期 `COMPLETED` 但没有 output evidence 的 cell 被记为 `FAILED`（`registry_only`）；`UNSUPPORTED`/`BLOCKED` 仍保留，避免缺失 score 被当作零分或完成。
7. `performance.txt`、`.logs`、run manifest 和最终 summary 可追溯到本次 host run。

## 限制

- synthetic full truth 只验证 adapter 和调度工程，不证明任何模型科学性能。
- 该 smoke 不验证外部工具 runtime、真实 assembly、GPU/CPU 吞吐或 Omni 的 Slurm 映射。
- `MetricCollector` 会按 0.6.0 规则收集所引用 stage 的全部 output files；collector 因此按 JSON schema 识别 registry/status/metric 文件，不能把“被收集”解释为新的评分逻辑。
- 失败分母在成功 collector 运行时由 registry 与 sidecar 合并保留；若 upstream native job 失败到使 collector 无法调度，需另行做 post-run status aggregation，不能把缺失 score 当成零分。
- macOS ARM64 上 venv 自带的 Snakemake 默认 ILP solver 是 x86 `cbc`，第一次运行在任何规则启动前因 `Bad CPU type in executable` 退出；显式透传 `--scheduler greedy` 后运行成功。这个是本机调度器兼容性限制，不是 benchmark DAG 失败。

## 后续：GitHub 固定提交的无 dirty 执行

2026-09-14 13:50 UTC，RC0 四臂工程流程已从公开 GitHub 固定源码提交 `1d4bcfa2415d7f437ccf6f9b2bf7ba89766e9aa9` 完成真实执行。初次去掉 `--dirty` 时，Omni 0.6.0 在任何任务启动前拒绝 `url: ../..`：本地路径即使带 commit 仍需 dirty。两份计划现改为 `https://github.com/JiWang-Unige/ab-initio-TE.git`，并固定到包含两个入口的已推送源码提交。

```bash
/Users/jiwang/Desktop/TE/manuscript-review-20260914/omnibenchmark-venv/bin/ob run \
  benchmarks/te_omnibenchmark/rc0.yaml \
  --out-dir /tmp/te-omnibenchmark-rc0-github-20260914 --cores 1 -- \
  --scheduler greedy
```

本次未使用 `--dirty`，完成 12 个 jobs。run ID 为 `623b650a-46f5-462a-93f5-d04b48c739b8`；module metadata 明确记录 GitHub URL、上述提交及 `rc0_fixture.py` 入口。collector 的 10 个预期 cell 全部保留：8 个实际完成的四臂×T0/T1评分、1 个专用合成 UNSUPPORTED、1 个专用合成 BLOCKED。8 份评分均为 `ENGINEERING_ONLY`，T1 precision/F1 保持空值。

紧凑证据位于 [reports/OMNIBENCHMARK-RC0-CLEAN-20260914](../../reports/OMNIBENCHMARK-RC0-CLEAN-20260914/)，包含原 manifest、解析后的 module 信息、实际计划、collector 和 8 份评分。该结果解决了从已提交代码独立执行的问题，仍未执行真实传统方法矩阵，也不提供模型性能或 CPU/GPU 速度结论。
