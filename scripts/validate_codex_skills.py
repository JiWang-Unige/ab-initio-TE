#!/usr/bin/env python3
"""Validate generated SKILL.md layers for Codex/Claude compatibility.

Checks:
- Frontmatter exists and contains name + YAML-safe single-line description.
- No `argument-hint` in generated Codex/cross-agent skills.
- Description total budget stays under a configurable ceiling.
- `.agents/skills` and `.codex/skills` have the same skill names.

This is intentionally conservative and stdlib-only; it is a smoke test for the
"Codex cannot load skills because frontmatter descriptions are incompatible" bug.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse(p: Path):
    txt = p.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return None, ["missing frontmatter"]
    errs = []
    fields = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            errs.append(f"bad frontmatter line: {line[:80]}")
            continue
        k, v = line.split(":", 1)
        fields[k.strip()] = v.strip()
    if "name" not in fields:
        errs.append("missing name")
    desc = fields.get("description", "")
    if not desc:
        errs.append("missing description")
    elif desc.startswith("*"):
        errs.append("description starts with unquoted YAML alias '*'")
    elif "\n" in desc:
        errs.append("description must be single-line")
    else:
        try:
            if desc.startswith('"'):
                json.loads(desc)
        except Exception as e:
            errs.append(f"description is not JSON/YAML safe: {e}")
    if "argument-hint" in fields:
        errs.append("generated codex skill must not include argument-hint")
    return fields, errs


def validate_layer(root: Path, rel: str, budget: int):
    base = root / rel
    out = {"layer": rel, "exists": base.is_dir(), "skills": [], "total_desc_chars": 0, "errors": []}
    if not base.is_dir():
        out["errors"].append(f"{rel} missing")
        return out
    for p in sorted(base.glob("*/SKILL.md")):
        fields, errs = parse(p)
        desc = (fields or {}).get("description", "") if fields else ""
        desc_unquoted = desc.strip().strip('"').strip("'")
        out["total_desc_chars"] += len(desc_unquoted)
        out["skills"].append({"name": p.parent.name, "desc_chars": len(desc_unquoted), "errors": errs})
        for e in errs:
            out["errors"].append(f"{p}: {e}")
    if out["total_desc_chars"] > budget:
        out["errors"].append(f"description budget exceeded: {out['total_desc_chars']} > {budget}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--budget", type=int, default=8000)
    args = ap.parse_args()
    root = Path(args.root)
    layers = [validate_layer(root, ".agents/skills", args.budget), validate_layer(root, ".codex/skills", args.budget)]
    names = []
    for layer in layers:
        names.append({s["name"] for s in layer["skills"]})
    cross_errors = []
    if all(names) and names[0] != names[1]:
        cross_errors.append({"agents_minus_codex": sorted(names[0] - names[1]), "codex_minus_agents": sorted(names[1] - names[0])})
    out = {"ok": not any(l["errors"] for l in layers) and not cross_errors, "layers": layers, "cross_errors": cross_errors}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
