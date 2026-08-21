---
name: exp-log
description: "*· After an experiment finishes (right after /result-log), write a dedicated structured per-experiment file docs/experiments/<exp_id>.md (hypothesis / architecture / data / config / result / findings / lineage), then regenerate docs/experiments/ATLAS.md via scripts/build_atlas.p…"
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Exp-Log: per-experiment structured file + categorized atlas

`docs/04` 把所有迭代混在一起、`docs/06` 是结果流水。本 skill 给**每个实验一个独立结构化文件**，并自动维护一个**按方法族分类的全局总览**（预训练类 / 传统DL类 / 混合类…的推进树），让"试过什么、怎么一步步推进来的"一眼看清。

**何时用**：每次 `/result-log` 完之后（hook 会提醒）。`/pursue` 每轮 Step 5 后也调一次。

## Step 1 · 写 per-experiment 文件 `docs/experiments/<exp_id>.md`
用**可被 build_atlas.py 解析的 frontmatter** + 结构化正文：

```markdown
---
exp_id: EXP-B-003
date: 2026-06-09
approach_family: pretrained-LM        # 方法族, atlas 按此分组(如 pretrained-LM / traditional-DL / hybrid / classical-seq / spike)
parent_exp: EXP-B-002                 # lineage 父实验(从哪来), 无则 -
motivated_by: "docs/08 pivot: 大gap→换架构轴"   # 触发来源: 哪个上轮结果/pivot/讨论/投稿缺口促成了这个实验
track: B
profile: full                         # smoke|screen|full|scale
status: done                          # done|failed|spike|parked|promoted
primary_metric: accuracy
value: 0.9504
vs_anchor: "-0.0156 vs sota 0.966"    # 相对锚点/ SOTA
one_liner: "HyenaDNA + weight_decay=0.1 协议对齐"   # 一句话, atlas 表里显示
---

## Why / Motivation (为什么现在做这个)
<**触发来源**：哪个上轮结果/pivot 决策/讨论结论/投稿证据缺口促成了它（指到 docs/06#上轮 / docs/08 / docs/11 §4 待议分支 / docs/14 缺口）。
 **回答什么问题**：这个实验要验证/排除什么。**为什么是现在、为什么不是别的**：在当前 pipeline 里它为何排在这一步。>

## Hypothesis (思路)
<这轮赌什么 / mechanism delta>

## Architecture (架构)
<backbone + head + 关键结构改动; 与父实验的差异>

## Data (数据)
<数据集 / split / 子集比例 / 类分布>

## Config (关键超参)
<lr / bs / epochs / 关键开关如 rc_aug / weight_decay>

## Result
<metric vs anchor/SOTA + semantic success + loss 趋势一句>

## Findings (本实验学到)
<Research / Engineering 发现; 同步进 docs/10>

## Decision
<pivot 结论: tune/scale/换轴/abandon; 指向 docs/08>

## Links
- result-log: docs/06#<exp_id> | tri-review: docs/07 | run: runs/<exp_id> | report: reports/<exp_id>.json
```

> 它不替代 docs/06（流水）/docs/04（ITER）——是**面向单实验的可检索档案**，frontmatter 让总览可自动生成。

## Step 2 · 重生成分类总览
```bash
python3 scripts/build_atlas.py
```
扫 `docs/experiments/*.md` 的 frontmatter，按 `approach_family` 分组 → 写 `docs/experiments/ATLAS.md`：每族一张表（exp_id | one_liner | value | vs | status | parent）+ best-of-family + lineage 链。一眼看清"预训练这条线走到哪、传统DL那条走到哪"。

## 边界
- 只写 `docs/experiments/<exp_id>.md` 和（经脚本）`ATLAS.md`；不动 docs/03/06/08。
- `approach_family` 由你按实验性质声明（脚本据此分组），新族直接写新名字即可，无需改框架。
- spike 实验 status=spike（atlas 单列一组，不混进主线族）。

## Hand-off
- **Inputs from**: `/result-log`(本轮结果) + docs/08(pivot 决策)
- **Uses**: `scripts/build_atlas.py`
- **Outputs to**: `docs/experiments/<exp_id>.md` + `docs/experiments/ATLAS.md`
- **Next**: 下一轮 `/goal-prompt`/`/pursue`；`/retrospective` 和 `/reframe` 读 ATLAS 做全局审视
