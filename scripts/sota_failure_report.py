#!/usr/bin/env python3
"""Summarize SOTA source/archive failures so the user can manually provide files.

Scans docs/02_sota_model_inventory.md, refs/sources.md, and refs/dossiers/*.md
for failed PDF/repo/weights/supplementary statuses. It never edits by default.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

FAIL_PAT = re.compile(r"(failed\([^)]*\)|404|403|paywall|cloudflare|restricted|gated|link-only|missing|不可达|失败|未下载)", re.I)
UNKNOWN_PAT = re.compile(r"unknown", re.I)
KIND_HINT_PAT = re.compile(r"(pdf|repo|github|supp|supplement|weight|huggingface|hf|link|url|download|下载|仓库|权重|补充)", re.I)
URL_PAT = re.compile(r"https?://[^\s)\]>'\"]+")


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def collect(root: Path):
    items = []
    paths = [root / "docs/02_sota_model_inventory.md", root / "refs/sources.md"] + sorted((root / "refs/dossiers").glob("*.md"))
    for p in paths:
        txt = read(p)
        if not txt:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            failish = FAIL_PAT.search(line) or (UNKNOWN_PAT.search(line) and KIND_HINT_PAT.search(line))
            if failish:
                urls = URL_PAT.findall(line)
                kind = "unknown"
                low = line.lower()
                if "pdf" in low or ".pdf" in low:
                    kind = "pdf"
                elif "repo" in low or "github" in low:
                    kind = "repo"
                elif "supp" in low or "supplement" in low or "附" in low:
                    kind = "supplementary"
                elif "weight" in low or "huggingface" in low or "hf" in low:
                    kind = "weights"
                items.append({"path": str(p.relative_to(root)), "line": i, "kind": kind, "text": line.strip(), "urls": urls})
    return items


def md(items):
    if not items:
        return "### SOTA source failure report\n未发现明确下载/验证失败项。"
    lines = ["### SOTA source failure report", "以下项目需要用户手动帮助或后续重试（PDF/补充材料/仓库/权重）：", "", "| Kind | Source | Failure | URL(s) |", "|---|---|---|---|"]
    for it in items:
        urls = "<br>".join(it["urls"]) if it["urls"] else "-"
        text = it["text"].replace("|", "\\|")[:260]
        lines.append(f"| {it['kind']} | {it['path']}:{it['line']} | {text} | {urls} |")
    lines.append("\n处理：能手动下载的文件放入 `refs/pdfs/<slug>.pdf` 或 `refs/supp/<slug>/`，私有/大仓库放 `refs/repos/<slug>.link.md` 写清位置，然后重新跑 /sota-inventory 的 verification update。")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--format", choices=["json", "markdown"], default="json")
    args = ap.parse_args()
    root = Path(args.root)
    items = collect(root)
    if args.format == "markdown":
        print(md(items))
    else:
        print(json.dumps({"count": len(items), "items": items}, ensure_ascii=False, indent=2))
    return 1 if items else 0


if __name__ == "__main__":
    raise SystemExit(main())
