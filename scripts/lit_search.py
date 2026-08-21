#!/usr/bin/env python3
"""Minimal literature search via Semantic Scholar Academic Graph API.

Pure Python standard library (urllib) — no third-party dependencies.

Use cases:
  - search:  given a method/architecture keyword, find top-N relevant papers.
  - cited-by: given a paper id, list papers that cite it (downstream / newer work).
  - similar: given a paper id, get recommended related papers.

An API key is optional. Without one you share a public pool (~1 req/s,
expect occasional HTTP 429). With a free key set S2_API_KEY for higher limits.
Get a key: https://www.semanticscholar.org/product/api#api-key-form
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

BASE = "https://api.semanticscholar.org"
PAPER_FIELDS = "title,year,venue,citationCount,abstract,openAccessPdf,externalIds"


def _load_secrets_env():
    """Best-effort: if keys aren't in the environment, load them from a
    project-root secrets.env (KEY=val / export KEY=val). Lets API keys travel
    with the framework without requiring the user to `source` it first. Never
    overrides a value already present in the real environment."""
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(os.getcwd(), "secrets.env"),
                 os.path.join(os.path.dirname(here), "secrets.env"),  # project root = scripts/..
                 os.path.join(here, "secrets.env")):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[len("export "):]
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and v and k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass
        return  # first file found wins


class RateLimited(Exception):
    """S2 public pool throttled us (HTTP 429) even after retries."""


def _get(url, retries=4):
    headers = {"User-Agent": "lit-search/1.0"}
    key = os.environ.get("S2_API_KEY")
    if key:
        headers["x-api-key"] = key
    last_429 = False
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                last_429 = True
                if attempt < retries - 1:
                    time.sleep(2 ** attempt + 1)  # exponential backoff: 2,3,5,9s
                    continue
            raise
    if last_429:
        raise RateLimited("HTTP 429 after retries")
    raise RuntimeError("exhausted retries")


def search(query, limit=10):
    """Relevance search: query -> top-N papers (ranked by S2's trained ranker)."""
    qs = urllib.parse.urlencode(
        {"query": query, "limit": limit, "fields": PAPER_FIELDS}
    )
    return _get(f"{BASE}/graph/v1/paper/search?{qs}").get("data", [])


def cited_by(paper_id, limit=10):
    """List papers that cite the given paper (downstream / follow-up work)."""
    qs = urllib.parse.urlencode(
        {"limit": limit, "fields": "title,year,venue,citationCount,externalIds"}
    )
    pid = urllib.parse.quote(paper_id, safe="")
    rows = _get(f"{BASE}/graph/v1/paper/{pid}/citations?{qs}").get("data", [])
    return [r["citingPaper"] for r in rows]


def similar(paper_id, limit=10):
    """Recommended papers related to the given one (for finding alternatives)."""
    qs = urllib.parse.urlencode(
        {"limit": limit, "fields": "title,year,venue,citationCount,externalIds"}
    )
    pid = urllib.parse.quote(paper_id, safe="")
    return _get(
        f"{BASE}/recommendations/v1/papers/forpaper/{pid}?{qs}"
    ).get("recommendedPapers", [])


def _fmt(p):
    pdf = (p.get("openAccessPdf") or {}).get("url") or ""
    ext = p.get("externalIds") or {}
    arxiv = ext.get("ArXiv", "")
    doi = ext.get("DOI", "")
    out = [
        f"  paperId : {p.get('paperId','')}",
        f"  title   : {p.get('title','')}",
        f"  year    : {p.get('year','')}   venue: {p.get('venue','')}",
        f"  cited   : {p.get('citationCount','')}",
    ]
    if arxiv:
        out.append(f"  arXiv   : {arxiv}")
    if doi:
        out.append(f"  doi     : {doi}")
    if pdf:
        out.append(f"  pdf     : {pdf}")
    abs = p.get("abstract")
    if abs:
        out.append(f"  abstract: {abs[:300]}{'...' if len(abs) > 300 else ''}")
    return "\n".join(out)


def main(argv):
    _load_secrets_env()  # pick up S2_API_KEY from secrets.env if not already in env
    if len(argv) < 3:
        print("usage:")
        print("  lit_search.py search '<query>' [N]")
        print("  lit_search.py cited-by <paperId|DOI:...|ARXIV:...> [N]")
        print("  lit_search.py similar  <paperId> [N]")
        return 1
    cmd, arg = argv[1], argv[2]
    n = int(argv[3]) if len(argv) > 3 else 10
    fn = {"search": search, "cited-by": cited_by, "similar": similar}.get(cmd)
    if not fn:
        print(f"unknown command: {cmd}")
        return 1
    try:
        papers = fn(arg, n)
    except RateLimited:
        keyed = bool(os.environ.get("S2_API_KEY"))
        sys.stderr.write(
            "lit_search: Semantic Scholar 限流 (HTTP 429"
            + (", 已用 key 仍被限——稍后重试)\n" if keyed else ", 走公共池)\n")
            + ("  → 设免费 key 提配额: export S2_API_KEY=<key>  "
               "(申请: https://www.semanticscholar.org/product/api#api-key-form)\n"
               if not keyed else "  → 稍等几十秒后重试，或换 cited-by/similar 端点。\n")
            + "  注: 这是检索源限流，不是 bug；可手动到 semanticscholar.org / arXiv 搜后把链接喂给 sota-inventory。\n"
        )
        return 2
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"lit_search: HTTP {e.code} — {e.reason} (id/查询可能无效或源不可达)\n")
        return 2
    except urllib.error.URLError as e:
        sys.stderr.write(f"lit_search: 网络不可达 — {e.reason} (集群计算节点常无外网；在登录节点跑或用 MCP exa)\n")
        return 2
    print(f"# {cmd}: {arg}  ({len(papers)} results)\n")
    for i, p in enumerate(papers, 1):
        print(f"[{i}]")
        print(_fmt(p))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
