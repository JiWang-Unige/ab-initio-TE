# docs/inputs/

放 deep research 报告(从外部 platform 跑回来)进这里。

## 命名约定

```
docs/inputs/
├── deep_research_prompt.md            # /research-interview 自动生成,不要手动改
├── deep_research_chatgpt_20260516.md  # ChatGPT Deep Research 跑出来的
├── deep_research_perplexity_20260516.md # Perplexity Deep Research
└── deep_research_claude_20260516.md   # Claude(独立 platform,不是这个 Claude Code)
```

## 流程

1. `/research-interview` 产出 `deep_research_prompt.md`
2. 你把它复制到外部 platform 的 Deep Research 模式(建议 2-3 个平台)
3. 回来的 markdown 报告 / 文本 → 重命名按上面格式 → 放本目录
4. `/research-synthesize` 自动读所有 `deep_research_*.md` 合并
