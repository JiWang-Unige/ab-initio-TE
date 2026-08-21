---
name: decisions-log
description: "B6· Record an abandoned research route to docs/09_decisions_log.md so the project doesn't waste compute re-trying it. Triggered ONLY when /tri-review + /pivot have together decided \"abandon route\" — single experiment failures go to docs/06_results_log.md instead. Includes mandatory cousin list (closely-related variants to also avoid) and re-entry criteria (what new evidence would justify re-opening). This doc is MUST-READ before any new iteration. Use after /pivot decides abandon, not after every failed run."
argument-hint: "<abandoned route description, with evidence reference>"
---

# Decisions Log (abandoned routes only)

把 `$ARGUMENTS` 描述的**整条路线**的放弃决定固化到 `docs/09_decisions_log.md`。

## 触发条件(严格)

只有同时满足:
1. 已跑 `/result-log`(有结果证据)
2. 已跑 `/tri-review`(三方共识或显式分歧)
3. `/pivot` 决策 = abandon

才调用本 skill。

**单次实验失败不触发**——那进 `docs/06_results_log.md` 就够。**只有放弃整条 route**(架构家族 / 数据 view / objective 方向)才进 `docs/09`。

## 输出格式(append-only)

```markdown
## DEC-<NNN>: <route name>

- **Date** (UTC):
- **Abandoned by**: pivot decision <ref>
- **Evidence base**: /result-log <exp_id list>, /tri-review <ref>
- **Resource profile of evidence**: <smoke / screen / full / scale>

### What was tried
<1-3 sentences,具体到机制>

### Why it failed
<必须是机制层,不是"参数没调好">

### What we now believe
<positive belief — 这次失败教给我们什么>

### Cousin list (also avoid)

| Cousin | How similar | Re-allowed if |
|---|---|---|
| <variant A> | 共享 <module> | <new evidence X> |
| <variant B> | 共享 <objective> | <new theoretical result Y> |

### Re-entry criteria

可以重新打开本路线,**仅当**:
- [ ] 出现新的 theoretical / empirical evidence(具体到什么)
- [ ] 找到了新机制能解决之前失败的原因(具体)
- [ ] 资源 / 数据 / 工具有质变(具体)

### Links
- Related result log: docs/06_results_log.md#<exp_id>
- Related tri-review: docs/07_tri_review.md#<ref>
- Related pivot: docs/08_pivot_decisions.md#<ref>
```

## Cousin list 的写法(关键防重)

cousin 不是"任何相似的东西",而是**会犯同样错误**的变体。判断标准:

- 若 cousin 失败原因 = 当前 route 失败原因,则是 cousin
- 若共享被证伪的核心机制(同 backbone family / 同 objective / 同 data view)→ cousin
- 仅参数 / 实现细节差异 → **不是** cousin(那条路线还有救)

写 cousin 是为了让后续 `/goal-prompt` 检测重复时能拦住。要具体,不要 "任何 Transformer 类模型"。

## "迭代前必读"协议

`docs/09_decisions_log.md` 文件顶部必须有一段:

```markdown
# Decisions Log (read before each new iteration)

每次 /goal-prompt 生成新迭代前,Claude 必须先读完整个本文件,确认新方向与任何 abandoned route 都没有 unexplained overlap。

如果新方向落在某个 cousin 列表里,必须在 /goal command 的「差异化说明」段明确写"这次为什么不同",或考虑放弃。
```

## Don'ts

- 单次实验失败不进本文件
- cousin list 不能空着("无 cousin"通常意味着没认真想)
- "Why failed" 不写"参数没调好"
- "What we now believe" 不写"还需更多研究"——必须可操作

## Hand-off

- **Inputs from**: `docs/06_results_log.md` + `docs/07_tri_review.md` + `docs/08_pivot_decisions.md`(abandon 决策)
- **Outputs to**: `docs/09_decisions_log.md` (append)
- **Next step**: `/goal-prompt` 会在生成新 iteration 前读本文件做 cousin 检测
