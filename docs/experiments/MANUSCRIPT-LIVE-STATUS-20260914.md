# 论文梳理时的实时状态核查

2026-09-14，Europe/Zurich；只读 SSH，未提交/取消/修改作业，未读取封存科学结果。

主机 `login1.baobab.hpc.unige.ch`；项目 `/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE`。

`squeue -u jwang` 返回表头、无作业行。相关 sacct 记录：

| Job | State | ExitCode | Elapsed |
|---|---|---|---|
|12520644|COMPLETED|0:0|00:00:09|
|12522308_0|COMPLETED|0:0|16:03:48|
|12522308_1|COMPLETED|0:0|02:29:58|
|12522308_2|COMPLETED|0:0|00:12:24|
|12664906_0|COMPLETED|0:0|15:50:00|
|12664906_1|COMPLETED|0:0|02:32:39|
|12652888|FAILED|1:0|00:21:58|

12522308 的已知 Matrix 无效产物不因退出码 0 恢复；使用修复记录判断具体产物有效性。

12652888 的独立阶段结果：本地单元测试在 allocation 通过；P3 export、P.canonical.tsv、U/P/R FASTA、preflight.json 存在；随后 U 臂 Tiberius wrapper 失败。`outputs/P3-TIBERIUS-BASE-MASK-20260911-R1/` 只见 smoke-r1，无完整科学运行。

U.stderr.log 的具体错误：

```text
Traceback (most recent call last):
  File "/work/te/scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/observed_tiberius.py", line 12, in <module>
    TARGET = Path(os.environ["BASE_MASK_OBSERVATION"])
KeyError: 'BASE_MASK_OBSERVATION'
```

smoke-r1/status.json 仍为 `PREPARED_NO_MODEL_OUTPUTS`，reference_units=726，selected_cores=[chr16:0]；它是未更新的中间记录，不能取代 Slurm FAILED 与实际已存在的 P3 文件。主科学端点 P-U 未评估。本轮仅记录此结果，不借论文整理改动/重启另一实验。
