#!/usr/bin/env python3
"""Generate the Codex/cross-agent skill layer from the Claude skill layer.

Why: Claude skills often have long YAML frontmatter (`description`,
`argument-hint`) and rich Markdown. Codex/other SKILL.md loaders commonly build a
startup skill list from the frontmatter and can fail or exceed context budget when
those descriptions are long, unquoted, or contain Markdown/quotes. This script:

  1. Reads `.claude/skills/<name>/SKILL.md` as the canonical source.
  2. Writes short, YAML-safe frontmatter to `.agents/skills/<name>/SKILL.md`.
  3. Mirrors the same generated skills to `.codex/skills/<name>/SKILL.md` for
     Codex loaders that look there instead of `.agents/skills`.
  4. Copies subdirectories (`scripts/`, `references/`, `examples/`, `evals/`)
     verbatim.

Idempotent. Run by install.sh --driver codex/both, or manually after editing a
Claude skill. Pure stdlib.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()))
SRC = ROOT / ".claude" / "skills"
DSTS = [ROOT / ".agents" / "skills", ROOT / ".codex" / "skills"]
CAP = int(os.environ.get("AUTORESEARCH_CODEX_SKILL_DESC_CAP", "280"))
BUDGET = int(os.environ.get("AUTORESEARCH_CODEX_SKILL_DESC_BUDGET", "8000"))

TAG_RE = re.compile(r"^((?:A[0-9.]+|B[0-9]+|C[0-9.]+|Ph8|\*)·\s*)?(.*)$", re.S)


def parse_frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    front, body = m.group(1), m.group(2)
    out: dict[str, str] = {}
    for line in front.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith(("'", '"')) and len(v) >= 2:
            # JSON/YAML-ish single-line quote; keep robust rather than strict YAML.
            try:
                v = json.loads(v) if v.startswith('"') else v.strip("'")
            except Exception:
                v = v.strip('"').strip("'")
        out[k] = v
    return out, body


def shorten(desc: str) -> str:
    desc = re.sub(r"\s+", " ", (desc or "")).strip()
    m = TAG_RE.match(desc)
    tag = (m.group(1) or "").strip()
    body = (m.group(2) or "").strip()
    # Keep the first strong sentence; avoid frontmatter listing several tasks.
    first = re.split(r"(?<=[.。；;])\s", body, maxsplit=1)[0].strip()
    short = (tag + " " + first).strip() if tag else first
    if len(short) > CAP:
        short = short[: CAP - 1].rstrip() + "…"
    return short


def normalize_body_for_cross_agent(body: str) -> str:
    """Adjust Claude-specific path references in generated Codex/cross-agent skills."""
    body = body.replace(".claude/agents", ".agents/agents")
    body = body.replace(".claude/skills", ".agents/skills")
    note = (
        "> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. "
        "When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; "
        "Claude users keep `/skill-name`.\n\n"
    )
    return note + body


def copy_generated_skill(src_dir: Path, dst_root: Path, name: str, sk_name: str, short: str, body: str):
    dstdir = dst_root / name
    dstdir.mkdir(parents=True, exist_ok=True)
    # Copy subdirs verbatim.
    for sub in src_dir.iterdir():
        if sub.is_dir():
            target = dstdir / sub.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(sub, target)
    fm = "---\n" + f"name: {sk_name}\n" + f"description: {json.dumps(short, ensure_ascii=False)}\n" + "---\n"
    (dstdir / "SKILL.md").write_text(fm + normalize_body_for_cross_agent(body), encoding="utf-8")


def main() -> int:
    if not SRC.is_dir():
        print(f"no claude skills at {SRC}", file=sys.stderr)
        return 1
    for dst in DSTS:
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True, exist_ok=True)

    total = 0
    rows = []
    for skill_path in sorted(SRC.glob("*/SKILL.md")):
        name = skill_path.parent.name
        txt = skill_path.read_text(encoding="utf-8")
        front, body = parse_frontmatter(txt)
        sk_name = front.get("name", name).strip().strip('"').strip("'") or name
        desc = front.get("description", "")
        short = shorten(desc)
        total += len(short)
        for dst in DSTS:
            copy_generated_skill(skill_path.parent, dst, name, sk_name, short, body)
        rows.append((name, len(desc), len(short)))

    for name, old, new in rows:
        print(f"  {name}: desc {old}→{new}")
    print(f"total codex/cross-agent description budget: {total} chars (budget {BUDGET})")
    if total > BUDGET:
        print("⚠️ over budget — tighten CAP or descriptions", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
