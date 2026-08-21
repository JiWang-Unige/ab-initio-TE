---
name: spike
description: "*· Insert an isolated exploratory side-experiment at any time WITHOUT polluting the mainline."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Spike: isolated side-experiment, mainline-safe

想随手试个直觉（换个 head、跑个朴素 CNN、试个野路子），但**不想搅乱主线 /pursue、也不想让差结果污染主轨迹**——用 `/spike`。它是**隔离沙盒**：好了再显式并入主线，差了主线当没发生过。

## 隔离契约（HARD）
- **命名空间**：exp_id 一律 `SPIKE-<topic>-NNN`；产物 `runs/SPIKE-*`、`reports/SPIKE-*.json`、`outputs/SPIKE-*`。
- **不进主线**：spike 结果**不**触发 Track-B 晋升、**不**计入 portfolio 正交配额、**不**进入 anti-tuning 的 gap 轨迹、**永不 claim SOTA**（profile 视作 smoke/screen）。
- **不碰 running 主线**：不改主线 docs/03、不 kill 主线 job、不抢占会饿死主线的资源（本地单卡则排在主线之后/小规模）。
- **per-exp 文件**：写 `docs/experiments/SPIKE-<...>.md`，`status: spike`、`approach_family: spike`（atlas 单列一组，不混主线族）。

## 流程
1. **声明 spike**：一句 hypothesis + 为什么值得花一点资源 + 预算（很小：smoke/screen，几分钟）。
2. **跑**（仍走 `/implement` 去风险 + check_data + run-and-evaluate / 远程小作业）。结果仍过 `validate_goal --profile smoke|screen`（语义成功闸照常，但**永不 claim**）。
3. **`/exp-log`** 记 `docs/experiments/SPIKE-*.md`（status=spike）。`/result-log` 仅记结果，**不**触发主线 pivot/晋升。
4. **裁决**：
   - **promote**（值得并入主线）→ 转成正式 exp_id（`SPIKE-→EXP-*`）并经 `/pivot` 或 `/reframe` 正式纳入主线轨迹（此时才进 portfolio/晋升判定）。
   - **drop**（不行）→ 留个 `docs/experiments/SPIKE-*.md` 存档（status=spike, 一句"为何不行"），主线不受影响；若是"整类方向被否"才升级 `/decisions-log`。

## 与 /pursue 的关系
- `/pursue` 跑主线时可随时穿插 spike；spike **不计入** `max_internal_iterations`、不改主线 cohort。
- iter_ledger 的阶段闸/链路检查**跳过 SPIKE-***（不要求 spike 走完 tri-review→pivot）。

## 边界
- spike 是**探路**不是**主张**：不可用 spike 结果 claim SOTA 或晋升 Track B（必须先 promote 成正式 exp 在 full profile 复跑）。
- 不污染主线四件套（docs/03 roadmap / portfolio 晋升 / anti-tuning 轨迹 / running job）。

## Hand-off
- **Inputs from**: 主人的直觉 / `/grill` 标记的"待验证"小问题 / `/note-add` idea
- **Uses**: `/implement` `/result-log` `/exp-log`(status=spike) `validate_goal`(smoke/screen, 不claim)
- **Outputs to**: `runs/SPIKE-*` + `docs/experiments/SPIKE-*.md`(atlas spike 组)
- **Next**: promote → `/pivot`/`/reframe` 正式纳入主线；drop → 存档，主线不受影响
