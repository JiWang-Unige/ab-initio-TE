---
name: framework-upgrade
description: "*· Upgrade an existing auto-research project/framework version in place, especially v3.x→v4.x or v4.x minor upgrades, while preserving research content."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Framework-Upgrade: 兼容式框架升级

本 skill 处理“框架本身升级”，不是研究路线 pivot。目标是把旧项目迁到当前 lwcr 版本，同时保留研究真相源：`docs/`、`refs/`、`wiki/`、`ACTIVE_GOAL.json`、`cluster_config.yaml`、`secrets.env`、已有 runs/reports。

## Step 0 · 判定升级类型

先读：
- `README.auto-research.md`、`ARCHITECTURE.md`、`CLAUDE.md`、`AGENTS.md`
- `docs/11_master_plan.md`、`docs/16_artifact_registry.md`、`docs/18_runtime_playbook.md`
- `scripts/build_codex_skills.py`、`scripts/sync_agents_md.sh`、`.codex/hooks.json`、`.claude/settings.json`

分类：

| Type | 典型场景 | 策略 |
|---|---|---|
| `minor-refresh` | v4.x 内增 skill/hook/doc | 直接补文件 + 同步生成 |
| `major-migration` | v3.x → v4.x | 先迁移清单，再分批落盘 |
| `driver-addition` | 单壳补 Claude/Codex/Antigravity | 用 install/sync 保留研究内容 |
| `compat-repair` | hooks/skills/AGENTS 漂移 | 修 canonical 后重生成 |

## Step 1 · 生成升级审计表（先不写）

输出并确认：

```markdown
## Framework upgrade audit <date>
- Current version evidence:
- Target version:
- Driver shells present: Claude / Codex / Antigravity
- Research content to preserve:
- Framework files to refresh:
- New docs to seed-if-absent:
- Skills to add/update:
- Scripts/hooks to add/update:
- Compatibility risks:
```

硬规则：
- `CLAUDE.md` 是 canonical driver contract；`AGENTS.md` 由 `scripts/sync_agents_md.sh` 生成。
- `.agents/skills` 是 canonical skill layer；`.agents/skills` 与 `.codex/skills` 由 `scripts/build_codex_skills.py` 生成。
- 研究内容文件默认 **seed-if-absent**，不能覆盖用户进度。
- 框架脚本、skill 模板、README/ARCHITECTURE 可刷新，但要给出 diff 摘要。

## Step 2 · 兼容保留清单

升级前明确哪些文件只能保留或追加：

| Path | Policy |
|---|---|
| `docs/00-22*.md` | seed-if-absent；已有内容只 append/局部补模板，不整文件覆盖 |
| `docs/experiments/` | 保留 |
| `refs/`, `wiki/` | 保留 |
| `ACTIVE_GOAL.json` | 不直接改目标值；若要改走 `/revise-goal` |
| `cluster_config.yaml` | 保留；环境迁移时走 `/configure-project` |
| `secrets.env`, `.mcp.json` | 保留，不打印真实 secret |
| `runs/`, `outputs/`, `logs/`, `software_outputs/`, `data/` | 保留，不进 git |
| `.git/` | 若存在保留；若不存在只在用户确认后初始化 |

## Step 3 · 执行升级

推荐顺序：

1. 新增/更新 canonical `.agents/skills/<skill>/SKILL.md`。
2. 新增/更新 docs 模板、scripts、hooks。
3. 更新 `CLAUDE.md` 的 skill 列表、流程、文档契约、Update Discipline。
4. 运行：
   ```bash
   python3 scripts/build_codex_skills.py .
   python3 scripts/validate_codex_skills.py .
   bash scripts/sync_agents_md.sh
   ```
5. 若 install 模板也要支持新项目，更新 `install.sh` 的 seed-if-absent 文档列表、目录创建、post-install 检查。

## Step 4 · 升级后验证

至少跑：

```bash
python3 scripts/context_pack.py --purpose iterate
python3 scripts/research_flow_guard.py . --format markdown
python3 scripts/validate_codex_skills.py .
```

若有 git：

```bash
git status --short
```

若无 git，明确报告“当前仍非 git 仓库”，并建议是否启用 `/workspace-matrix` 或 `git init`。

## Step 5 · 写升级记录

把摘要追加到 `docs/22_upgrade_log.md`：

```markdown
## Upgrade <date> — <from> → <to>
- Reason:
- Files changed:
- Research content preserved:
- Compatibility checks:
- Required follow-up:
- Rollback note:
```

同时用 `/note-gate` 把“用户批准的升级方向/新增硬约束”写进 `docs/15_evidence_register.md`，必要时用 `/master-plan` 更新 `docs/11`。

## 边界

- 不把框架升级混成研究目标修订；目标变更走 `/revise-goal` 或 `/route-reset`。
- 不自动删除旧 docs/refs/wiki/runs。
- 不自动 commit、merge、rebase；git 操作只做状态检查或经用户确认的初始化。
- 不把 hooks 当成 skill 执行器；hooks 只能提醒/拦截。

## Handoff

- **Inputs from**: 用户升级请求、README/ARCHITECTURE、旧项目磁盘状态。
- **Uses**: `scripts/build_codex_skills.py`、`scripts/validate_codex_skills.py`、`scripts/sync_agents_md.sh`、`scripts/context_pack.py`。
- **Outputs to**: canonical skills/scripts/docs、`AGENTS.md`、`.agents/.codex` generated layers、`docs/22_upgrade_log.md`。
- **Next**: `/artifact-registry` 审计目录；若路线也要变，转 `/route-reset`。
