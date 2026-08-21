---

# 独立全量研究审阅 — Job 11528885

**审阅者**: Reviewer A=Claude（独立外部 reviewer）
**审阅日期**: 2026-08-12
**审阅范围**: 全量——实验设计、执行、失败根因、假设有效性、路线可持续性、下一步建议

---

## 1. Overall Judgment

**`replace-component`**

科学假设（annotation-time accession-preserving custom library 可保留 accession 且几何不变）本身未被证伪——RepeatMasker 根本没启动。两次连续 engineering failed_run 的根因不同（第一次是 Slurm 资源 guard 假设错误，第二次是 FamDB API 兼容性），说明上一次 blocker 已关闭但科学 payload 仍未开始。路线本身未到可判科学价值的地步，但 FamDB export component 需要替换或修复后才能继续。**不是 abandon-route**——因为 annotation-time accession-preserving 这条路的科学问题尚未被触及——但也**不能继续当前实现**。

---

## 2. SOTA Gap Interpretation

| 项目 | 值 |
|---|---|
| Primary metric | n/a（未产出） |
| SOTA benchmark | n/a（smoke profile，永不 claim） |
| Gap | n/a |
| Tuning justified? | **否**——这不是调参能解决的问题；是 API 集成层面的组件失败 |

---

## 3. Comparability and Benchmark Fairness Audit

| Dimension | Pass / Fail / Unknown | Notes |
|---|---|---|
| Dataset version | **Pass** | 六条 pinned Dfam 3.9 accession，经 FamDB exact fetch + 37 项确定性测试验证，config 冻结 |
| Official split / same split | **n/a** | 本实验无 split 概念（6-record CPU smoke，claim-ineligible） |
| Metric implementation | **n/a** | 无 primary metric 产出；geometry semantic hash 评估器已定义但未运行 |
| Preprocessing | **Pass** | FASTA export contract（control name-header / candidate accession-header）经 37 tests 验证，语法冻结 |
| External weights / tool versions | **Pass** | RepeatMasker 4.2.2、rmblastn、matrix 18p35g/simple1 均 SHA256-pinned；FamDB partitions symlink/inode/mtime 全量校验通过 |
| Test-time inference protocol | **n/a** | RepeatMasker 未启动，无推理发生 |
| Resource profile supports claim? | **n/a** | smoke profile 永不 claim |

---

## 4. Semantic Success and Reproducibility Audit

| Check | Pass / Fail / Unknown | Notes |
|---|---|---|
| Metrics file exists and is parseable | **Fail** | `metrics.audited.11528885.json` 存在且可解析，但 `primary_metric: null`，`semantic_success: false` |
| Values finite / no NaN or Inf | **n/a** | 无科学指标产出 |
| Scientific payload executed | **Fail** | RepeatMasker 从未启动；`scientific_execution_started: false` |
| No leakage signal | **n/a** | 无训练/评估发生 |
| Logs/config/manifests sufficient | **Pass** | stdout/stderr 完整；37/37 tests trace → AttributeError 清晰可追溯；RUN_MANIFEST 含全部 5 个 reviewed file SHA256 + code_review_gate SHA；PAYLOAD_MANIFEST 含 13 个已审计文件；AUDITED_MANIFEST 完整 |
| Stop rule honored | **Pass** | `result_semantic_audit` 明确 `retry_authorized: false`；`validate_goal` 返回 `failed_run`；未绕过 P3 exhaustive 0/279 关闭令；未触及基因组 copy representatives 泄漏红线 |

---

## 5. Architecture/Component Assessment

### 5.1 失败根因定位

错误链路（从 stderr 精确还原）：

```
37 tests OK (0.268s)                    ← 合成测试、Slurm guard、资产校验全部通过
→ pre_submit_gate: PASS_WITH_WARNINGS   ← 审前闸通过
→ formal() 进入 read_selected_families()
→ from famdb_classes import FamDB       ← 导入成功
→ db = FamDB(str(famdb_dir), "r")       ← FamDB 构造成功
→ db.files[partition_no].get_family_by_accession(accession)
→ 返回 FamDBLeaf 对象
→ 访问 fam.repeat_type / fam.name / fam.accession_with_optional_version() 等属性时
→ 内部触发 'FamDBLeaf' object has no attribute 'added'
```

`added` 属性不在 `run_preflight.py` 的任何显式代码中——它是 `famdb_classes` 模块内部 `FamDBLeaf` 方法（很可能是 `accession_with_optional_version()` 或属性惰性加载逻辑）尝试访问的 bookkeeping 字段。这说明：

1. **当前实现假设了一个比实际安装版本更"完整"的 FamDB API**——该版本期望 `FamDBLeaf` 携带一个聚合/版本追踪的 `added` 属性
2. **实际安装的 FamDB API 中 `FamDBLeaf` 不暴露此属性**——可能是 Dfam API 版本差异、安装不完整、或该属性在较新/较旧版本中被移除/重命名

### 5.2 对 annotation-time accession-preserving 假设本身的意义

**无影响。** 该假设的核心问题是：RepeatMasker 在处理 custom library 时，其 `.out` 输出中的 repeat identifier 列是否保留 FASTA header 中的 accession 信息。这是 RepeatMasker 的输入解析行为，与 FamDB API 完全无关。当前失败发生在 FamDB export 层——这是**数据准备管道**的失败，不是科学假设的失败。换言之：

- **科学假设未被测试**（RepeatMasker 未启动）
- **组件假设被证伪**（"我们可以用当前安装的 FamDB API 版本通过 `FamDBLeaf` 精确导出 accession"——这个假设是错的）

### 5.3 具体 Component-Level 选择（非调参）

**选项 A — 替换 FamDB aggregation 为 leaf-level exact access（推荐）**
不用 `FamDBLeaf` 的高层方法（`accession_with_optional_version()` 等），直接访问 leaf 的底层字段。需要先做一次 **read-only API probe**：在交互式 `srun` 中 `import famdb_classes`，`dir(fam)` 列出实际可用属性，找到 `accession`、`name`、`consensus`、`repeat_type`、`repeat_subtype` 的精确字段名，然后重写 `read_selected_families()` 只使用已验证存在的属性。若 `added` 字段在任何代码路径上被触及（即使是间接的），必须完全绕过。

**选项 B — 绕过 FamDB API，直接从 HDF5 读取**
Dfam partition 文件（`.h5`）是标准 HDF5 格式。可以绕过 `famdb_classes` 层，直接用 `h5py` 按 accession 索引读取所需六条记录的 sequence/name/class。优点是消除 API 版本依赖；缺点是需要理解 Dfam HDF5 schema，且丢掉了 FamDB 的 accession 解析逻辑。对六条 pinned 记录的手动验证工作量可控。

**选项 C — 返回官方 FamDB 实现/文档取证**
检查 Dfam 官方 GitHub 仓库中 `famdb_classes.py` 的 `FamDBLeaf` 类定义，确认 `added` 属性是否存在、在哪个版本引入/移除、是否需要额外的初始化或数据库构建步骤。如果当前安装版本确实缺失该属性，升级/降级到匹配版本或打补丁。

**选项 D — 用 `famdb.py` CLI 替代 Python API（最快但最脆弱）**
`famdb.py` 命令行工具（Dfam 官方提供）支持 `-i <accession> --format fasta` 等导出命令。可以 subprocess 调用 CLI 获取六条序列，再自行组装 FASTA header。优点是零 API 依赖；缺点是对 CLI 输出格式的解析假设可能同样脆弱，且不经过 Python API 的类型安全。

### 推荐优先级

**选项 A > 选项 B > 选项 C > 选项 D**

选项 A 是最小改动、最尊重现有代码结构的方式。关键动作是先做一次 **只读 API probe**（不提交正式 job，仅交互式 `srun` 检查），确认实际可用的 FamDB API surface，然后据此重写 `read_selected_families()` 的字段访问部分。

---

## 6. Track Recommendation

### 6.1 第三次 retry 授权

**不允许第三次 CPU retry。** 上次 tri-review 明确规定："若 repair retry 仍在科学 payload 前失败则停止自动重试。"该条件已触发。任何继续必须走**新 exp_id + 独立 code review + 独立 pre_submit_gate**。

### 6.2 允许的操作

| 操作 | 授权 | 条件 |
|---|---|---|
| 交互式 `srun --pty bash` API probe | **是** | 只读，不写任何 canonical state，不消耗 retry budget |
| 新 exp_id read-only FamDB API 探测脚本 | **是** | 新的 smoke exp_id，写入新 output 目录 |
| 替换 FamDB aggregation component | **是（经审批后）** | 必须新 exp_id + 新 code-review-gate + 新 pre_submit_gate + 新 owner lock |
| 继续当前 exp_id 第三次 CPU retry | **否** | stop rule 已触发 |
| GPU / S1 / full DATA | **否** | 所有下游 authorization 均为 false |
| Representative window CPU gate | **否** | 需先过 PREFLIGHT_PASS |

### 6.3 Re-entry 条件

1. 完成一次 API probe（交互式或新 exp_id），证明可以精确获取六条 pinned accession 的 `accession`、`name`、`consensus`（大写、U→T）、`repeat_type`、`repeat_subtype`
2. 新 exp_id 的 `read_selected_families()` 重写后通过 37+ 合成测试（可复用现有 test 套件）
3. 独立 `/code-review-gate` 返回 PASS 或 PASS_WITH_WARNINGS（零 blockers_open）
4. 资源上限：**严格 1 CPU / 4 GiB / 20 min / 0 GPU**，partition `private-teodoro-gpu`

---

## 7. Risks and Blockers

| 风险 | 严重度 | 缓解 |
|---|---|---|
| FamDB API 版本碎片化——Dfam 的 Python API 未稳定版本化，不同安装/构建可能暴露不同的 `FamDBLeaf` 属性集 | **高** | 选项 B（直接 HDF5 读取）作为 fallback；在 API probe 阶段就确认 surface |
| 两次 engineering 失败消耗了信任预算——第三次若再因工程原因失败，用户可能对整个 accession-preserving 路线失去信心 | **中** | 下一次必须是确定性 API probe（不触发 RepeatMasker），降低失败概率 |
| 即使 FamDB export 修好，RepeatMasker 的 custom library header 解析行为仍是未知——可能截断、重写或不保留 `#raw_class` 后缀 | **中** | 这不是当前 blocker；PREFLIGHT_PASS 后再议 |
| Dfam 3.9 的 73.229% occurrence mass 无法权威绑定到 accession（历史 P3 exhaustive 0/279）——即使 roundtrip smoke 通过，代表性窗口 gate 仍需要解决大规模 accession mapping 问题 | **高（远期）** | 当前 smoke 不解决此问题；需在 representative gate 设计阶段单独处理 |
| 选项 B（直接 HDF5）如果遇到 Dfam schema 变更，脆弱性不低于 FamDB API | **低-中** | 六条 pinned 记录的 schema 可手动验证 |

---

## 8. Next Action

**唯一具体下一步：进行一次交互式只读 API probe，列出六条 pinned accession 的 `FamDBLeaf` 实际可用属性。**

具体命令（在 baobab 集群上，严格遵守 srun 纪律）：

```bash
srun -p private-teodoro-gpu --time=00:15:00 --cpus-per-task=1 --mem=4G --pty bash
# 拿到节点后：
conda activate <te_benchmark 或含 famdb_classes 的 env>
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
python3 -c "
import sys; sys.path.insert(0, '<famdb_code_dir>')
from famdb_classes import FamDB
db = FamDB('<famdb_dir>', 'r')
for acc in ['DR002419729', ...]:  # 填六条 accession
    for part_no in db.files:
        fam = db.files[part_no].get_family_by_accession(acc)
        if fam is not None:
            print('===', acc, 'in partition', part_no, '===')
            print('type:', type(fam).__name__)
            print('dir:', [a for a in dir(fam) if not a.startswith('_')])
            for attr in ['accession', 'name', 'consensus', 'repeat_type', 'repeat_subtype']:
                try:
                    print(f'  {attr}: {getattr(fam, attr)!r}')
                except Exception as e:
                    print(f'  {attr}: ERROR {e}')
            # 检查 added 相关
            for attr in dir(fam):
                if 'add' in attr.lower() or 'version' in attr.lower():
                    print(f'  FOUND related attr: {attr}')
            break
db.finalize()
"
```

该 probe 的输出将直接决定选择选项 A（用现有属性重写）还是选项 B（绕过 API 直接读 HDF5）。**这不是第三次 retry**——它是 read-only 诊断，不消耗 retry budget，不写 canonical state。Probe 通过后再设计新 exp_id 的修复方案。

---

## 9. Confidence

**High**

理由：
- 失败根因在 stderr 中精确可追溯（37 tests → AttributeError），无歧义
- 错误发生在 FamDB API 层，与科学假设无关，分类明确
- 历史上下文完整：两次失败的不同根因已被区分，stop rule 的适用条件清晰
- 组件级选择（A-D）覆盖了从最小修复到完全替换的谱系，均有明确的 re-entry 条件
- 唯一不确定性是 FamDB 安装版本的具体 API surface——这正是 next action 要解决的，且解决方式（只读 probe）无风险
