---
exp_id: SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1
date: 2026-08-12
approach_family: superfamily_identity_provenance
parent_exp: SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1
track: S0_data_foundation
profile: component_smoke
status: COMPLETED_COMPONENT_PASS
primary_metric: resolved_accession_count
value: 6
vs_anchor: 6/6 frozen targets
one_liner: Exact leaf access and close-only read lifecycle pass; downstream S0/S1 remain blocked.
---

# SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1

## 目标与边界

这是 Job 11533175 failed-run 的最终 close-only 修复，不改变其科学 probe。正式作业仍只对冻结的 6 个 accession 按固定 12 个 leaf partition 调用一次 `FamDBLeaf.get_family_by_accession`，总计严格 72 次。禁止 name/prefix/case/alias/copy fallback；不运行 RepeatMasker，不构建 annotation、catalog、homology split、DATA、GPU 或 S1。

Job 11533175 的 audited manifest、semantic audit、validate-goal、machine gate、原 science config 及 scheduler 形状均由 config hash-pin。它的失败机制是 read-mode cleanup 调用了写路径生命周期 API；本修复只对 `db.files` 的 exact partition set 逐 leaf 调用底层 `leaf.file.close()`，并验证 HDF5 handle 已失效。runner 源码不含写路径关闭 API 的 token 或调用。

## IO 与顺序

输入：冻结 FamDB 3.9 12 partitions 的 symlink/resolved stat contract、layout manifest、rmlib config、FamDB Python source、docs/19、Job 11533175 证据、标准 dict machine review gate，以及 Slurm authoritative `scontrol show job -o`。

正式顺序：

1. 验证 positive numeric job、exact 1 CPU/4 GiB/10 min/0 GPU、Command/SubmitLine/TRES、owner、gate、package 和 source。
2. 原子发布 `FORMAL_RUNNING`。
3. process-level termination controller 在 `HandleLifecycle`/`FamDB.__new__` 之前进入；从 constructor、仅一次 6×12 probe、观察 staging、finally cleanup 到 failure/result 结构化均使用同一只记录 TERM/INT 的 controller。handle 一旦可能出现，cleanup 责任即已建立，terminal hook 不重跑科学 API。
4. cleanup 之前，把完整 72-row observation、resolved rows、precleanup metrics 写入 attempt-scoped immutable bundle，并生成自排除 hash manifest。stage 原子成功后即使随后收到 TERM，证据仍被发现、重验和保留，但终态只能 semantic false。
5. 对 12 个 `leaf.file` 逐个显式 `close()`；即使构造器只创建了部分 leaf、异步异常落在 probe→stage、stage→close 或 close 的任意 line event，也清理全部已出现的 frozen-key unique handles。非整数/意外 key、partial keyset、共享 leaf/handle 均在清理后失败；已关闭 handle 只核关闭状态，不二次调用 close。
   - controller 先以 `pthread_sigmask` 同时阻塞 SIGTERM/SIGINT，再在 mask 内安装只记录 pending signum 的 handlers，然后才创建 ownership envelope；constructor/probe/stage/finally entry/close loop 都不会被旧 handler 异步抛异常覆盖。
   - production runner 在 failure/result 已结构化后仍保留 deferred handlers，直到进程退出，不执行有竞态的旧-handler restore/unmask。无 primary 时，pending signal 在 cleanup 后重放为 `TerminationRequested`；已有 primary 时保持其原 type/message，并把 pending signals 和 cleanup failure 作为结构化 secondary，最终仍 rc2。仅 synthetic test 子进程执行显式 restore，核 handler/mask 能恢复且 restore 行注入不会触发旧 handler。
   - machine evidence 将每次 TERM/INT 保存为独立有序事件（`signum/name/order/timestamp_monotonic_ns`）。`raise_if_pending` 已附上的事件必须是 controller 序列的精确前缀；顶层只追加随后到达的 delta。相同 signum 的重复信号不去重，单 TERM、TERM+INT、TERM+TERM 分别严格报告 1、2、2 条，不制造重复。
   - SIGKILL 无法被 Python 捕获、屏蔽或延迟，因此不承诺 SIGKILL 路径能完成 cleanup 或产出 artifact；sbatch 的 KILL 只作为 TERM 宽限期后的 hard stop，不属于可恢复证据合同。
6. cleanup 成功后，才允许发布 PASS 或 typed block；pointer 前再次核 source/package/owner/gate/scheduler 和 observation manifest。
   - terminal `publish` 直接接收 process-level termination controller；不是只依赖 callback 返回前的瞬时检查。callback、CAS、`CURRENT` 临时文件、`os.replace` 与 replace 后核验组成一个 TERM/INT masked critical section，OS pending signal由 controller 主动 drain 成上述有序 machine evidence。production 路径没有 contextmanager `finally` restore/unmask：terminal commit 开始后，TERM/INT 一直 blocked 到 Python 进程正常退出；只有隔离 synthetic test 子进程可调用 `restore_for_tests`。
   - critical section 进入时已有 signal，或 signal 在 science pointer 替换前到达，均禁止 PASS/typed-block pointer，canonical 保持 `FORMAL_RUNNING`。若 signal 恰在最后一次 pre-replace drain 后到达、science pointer 曾短暂切换，runner 会在同一 writer mutex/owner/authority 闭包内发布 immutable `LEAF_CLOSE_ONLY_FAILED` supersession，记录 `commit_superseded=true` 与 `pass_pointer_was_temporarily_published=true`，最终 `CURRENT` 必为 semantic false。
   - 若 termination failure bundle 无法通过 owner/source/package/gate/scheduler/observation 重验，runner 原子恢复此前 `FORMAL_RUNNING` pointer；不得把暂存或短暂切过的 PASS 当 canonical truth。
   - 最后一次 post-replace drain/check 是 terminal linearization point。该点之前已到达的 TERM/INT 必须阻止或 supersede science terminal；该点之后到达的信号属于 post-commit 外部事件，因 production mask 保持到 exit，只留在 kernel OS-pending 集合，不执行 Python handler、不覆盖异常、不改变已经线性化的 CURRENT。SIGKILL 仍不可屏蔽，也不在此保证内。
7. cleanup/runtime/integrity 失败为 rc2、`semantic_success=false`。若 owner/authority 仍闭合，可发布 canonical failure；否则仅写 attempt-local evidence。cleanup 失败保留 precleanup bundle，绝不能升级为 PASS。wrapper trap 不覆盖同 attempt 已发布的精确失败终态。

## 状态与授权

- `LEAF_CLOSE_ONLY_PASS`：只使“未来 leaf-adapter CPU preflight 提案”具备进入人闸的资格。
- `LEAF_CLOSE_ONLY_TYPED_BLOCK`：missing/duplicate/version/name/class/length/sequence/partition drift；语义有效负、rc0、route stop。
- `LEAF_CLOSE_ONLY_FAILED`：cleanup/runtime/integrity 失败，rc2。
- `IMPLEMENTED_NOT_RUN`：仅静态预览，不读取真实 H5、不调用 FamDB API。

所有状态下 annotation、RepeatMasker、annotation roundtrip、full catalog、homology、DATA、GPU、S1 授权均为 false。该实验不具 claim 资格。

## 资源与提交边界

正式资源固定为 `private-teodoro-gpu`、1 CPU、4096 MiB、10 分钟、0 GPU。sbatch 用 480 秒 bounded runner（TERM，30 秒后 KILL），为 cleanup/terminal publish 留出余量；conda activation 后才启用 `set -u`。`pre_submit_gate.py` 接收显式 project root，因此提交脚本不依赖当前工作目录。日志目录必须在 schedule time 已存在且可写。

当前仅完成 synthetic/static tests 和 `IMPLEMENTED_NOT_RUN` preview；没有 code-review PASS gate、没有提交 Slurm、没有打开真实 H5/API。

## 正式结果：Job 11534847

- Slurm：`COMPLETED 0:0`，25 秒，`private-teodoro-gpu`，1 CPU/4 GiB/10m/0GPU，MaxRSS `83,432 KiB`。
- 终态：`LEAF_CLOSE_ONLY_PASS`，`semantic_success=true`，但 `claim_eligible=false`。
- 科学/API 观察：6 个冻结 accession × 12 partitions = 72 次 exact-access 调用，严格 exact-once；6/6 resolved、0 blocked、0 fallback，identity/partition/name/class/length/sequence hash 全部匹配冻结合同。
- cleanup：观察在 cleanup 前冻结；12 个 unique HDF5 handle 各 close 一次，12/12 失效，无 cleanup error。
- 完整性：terminal 11/11 文件与 observation bundle 4/4 文件逐项 SHA256 通过；scheduler/source/package/gate 初末一致。
- 解释：仅证明 leaf API + close-only lifecycle 组件可用。RepeatMasker、annotation、full catalog、homology、DATA、GPU direct S0、S1 和 claim 仍全部未授权。
- 证据：`outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/result_semantic_audit.11534847.json`、`validate_goal.11534847.json`、`AUDITED_MANIFEST_11534847.sha256` 及 terminal/observation manifests。

## Post-result review 与 pivot

- Tri-review：`2/3 DEGRADED_REVIEW`。Claude=`PASS/continue-current-route`；独立 separate Codex=`PASS_WITH_WARNINGS/continue-current-route`；Antigravity 三次无效，外部 Codex CLI 三次因额度耗尽未形成审查。
- Pivot：`continue-current-route`，但只允许一个新的、单独实现并 fresh-review 的 CPU leaf-adapter preflight proposal，仍限同六条记录。
- 不授权：RepeatMasker benchmark、代表性/全量 annotation、catalog、homology、DATA、GPU direct S0、S1、claim。

## 测试覆盖

合成行为测试覆盖：exact 72/never 144、无写路径关闭 token、实际 12 个 `leaf.file.close()`、构造器在第 N 个 handle 后抛出 `BaseException`、partial/unexpected key、共享 leaf/handle、double-close 与 cleanup 继续性；monkeypatch 与 `sys.settrace + os.kill` 窗口矩阵覆盖 controller/constructor 前后、probe 内、旧 probe→stage 行、stage 内/原子发布后、finally entry、close 前/中、postclose，并逐项断言 12 次且不重复关闭。真实信号覆盖 primary OSError + TERM、无 primary TERM、close error + TERM、SIGINT、TERM+INT 多信号；顶层 `main`/attempt failure evidence 另覆盖单 TERM、TERM+INT、两次 TERM、primary+signal、`raise_if_pending` 后到 catch 前的晚到 signal，以及无 signal 空列表，严格验证次数、顺序和事件 schema。terminal commit 以 monkeypatch 和 `sys.settrace + os.kill` 双重覆盖 publish entry、callback return、CURRENT write、`os.replace` 前/后及 post-replace check，并对正常 PASS 与 typed block 各自验证：替换前 signal 保持 RUNNING，替换后 signal 得到闭合 failure supersession，authority drift 则恢复 RUNNING；所有路径 handle 已 exact-once close，最终 CURRENT 从不错误停在科学成功态。额外隔离子进程在 linearization 后、inner `return final`、writer-mutex exit、outer publish return 等尾窗发送真实 TERM，验证 mask 仍含 TERM/INT、handler rows 为零、TERM 只在 OS pending、CURRENT 保持已线性化 PASS/typed block，随后进程正常退出。隔离子进程也覆盖 test-only restore-handler/unmask 行，production source断言不调用 restore。primary/stage error 保持原类型，cleanup error 与 pending signal写入结构化 secondary；无 primary TERM 在 close 完成后才抛 `TerminationRequested`，canonical 保持 `FORMAL_RUNNING` 不晋升。precleanup bundle固定三文件、manifest self-exclusion、exp/attempt/status/count/schema、逐文件 SHA/size、payload SHA与目录名一致、resolved containment、无 symlink ancestor/entry；evil-only、traversal、extra/missing/duplicate/self-entry、tamper和precreated collision均fail-closed。另覆盖owner/state mutex、static不能覆盖formal、strict TRES/Command/SubmitLine、source/package/scheduler drift、Job 11533175 science identity复用、wrapper不覆盖同 attempt terminal。
