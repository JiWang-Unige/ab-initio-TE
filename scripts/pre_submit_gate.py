#!/usr/bin/env python3
"""Deterministic pre-submit code-review gate.

Turns `/code-review-gate` from a "discipline + nudge" into a HARD, machine-checkable
gate so a real training submission cannot proceed without a PASS review — even in a
Codex-only environment where the reviewer is Codex itself.

It reads `outputs/<exp_id>/code_review_gate.json` (written by /code-review-gate) and
verifies, deterministically:
  1. the review exists and verdict is PASS / PASS_WITH_WARNINGS (not BLOCKED / absent);
  2. the review is NOT STALE — the files it reviewed still hash-match on disk, so code
     edited AFTER the review cannot sneak past an old PASS;
  3. (advisory) for full/scale, flags `independence: host_self` (same-context self-review)
     as weak — separate-process Codex self-review (`separate_codex`) or `external_cli`
     is preferred. Does not hard-block on this (Codex-only self-review is accepted by design),
     only warns.

code_review_gate.json schema (written by /code-review-gate):
  {
    "exp_id": "EXP-A-001",
    "verdict": "PASS | PASS_WITH_WARNINGS | BLOCKED",
    "reviewer_backend": "codex(separate) | claude | agy | host",
    "independence": "external_cli | separate_codex | host_self",
    "profile": "smoke | screen | full | scale",
    "reviewed_files": {"path/rel/to/root.py": "<sha256>", ...},
    "blockers_open": 0,
    "timestamp": "<iso, written by the agent>"
  }

Exit codes: 0 = PASS (submission may proceed), 2 = usage/IO error,
            3 = BLOCKED / missing / stale (submission must NOT proceed).
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path

PASS_VERDICTS = {"PASS", "PASS_WITH_WARNINGS"}


def sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic pre-submit code-review gate")
    ap.add_argument("--exp-id", required=True)
    ap.add_argument("root", nargs="?", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()
    root = Path(args.root)
    eid = args.exp_id
    gate = root / "outputs" / eid / "code_review_gate.json"

    out = {"exp_id": eid, "ok": False, "verdict": None, "reasons": [], "warnings": []}

    # Machine-recorded waive: the ONLY auditable way to override the deny. A human/agent
    # must write outputs/<exp>/code_review_waived.json with a real reason — clicking "yes"
    # on a prompt is NOT enough. Loud warning; use only when reviewer unavailable / low risk.
    waive = root / "outputs" / eid / "code_review_waived.json"
    if waive.exists():
        try:
            reason = (json.loads(waive.read_text(encoding="utf-8")) or {}).get("reason")
        except (OSError, ValueError, json.JSONDecodeError):
            reason = None
        if reason:
            out["ok"] = True; out["verdict"] = "WAIVED_BY_USER"
            out["warnings"].append(f"code review WAIVED_BY_USER（机器记录）：{reason} — 跳过代码审，风险自负。")
            return _emit(out, args.format, 0)

    if not gate.exists():
        out["reasons"].append(
            f"无 code review 记录（{gate} 缺失）。提交真实训练前必须先跑 /code-review-gate "
            f"（Codex 用 $code-review-gate）产出 PASS。")
        return _emit(out, args.format, 3)

    try:
        data = json.loads(gate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        out["reasons"].append(f"code_review_gate.json 无法解析: {e}")
        return _emit(out, args.format, 3)

    out["verdict"] = data.get("verdict")
    if data.get("verdict") not in PASS_VERDICTS:
        out["reasons"].append(f"verdict={data.get('verdict')!r} 非 PASS/PASS_WITH_WARNINGS（或仍 BLOCKED）。")
        return _emit(out, args.format, 3)
    if int(data.get("blockers_open", 0) or 0) > 0:
        out["reasons"].append(f"仍有 {data.get('blockers_open')} 个未关闭 blocker。")
        return _emit(out, args.format, 3)

    # Staleness: every reviewed file must still hash-match → code edited after the
    # review (the classic "reviewed v1, submitted v2") cannot pass on an old PASS.
    reviewed = data.get("reviewed_files") or {}
    stale = []
    for rel, want in reviewed.items():
        cur = sha256(root / rel)
        if cur is None:
            stale.append(f"{rel}（评审过的文件现已不存在）")
        elif want and cur != want:
            stale.append(f"{rel}（评审后又被改动，hash 不符）")
    if stale:
        out["reasons"].append("code review 已过期（评审后代码又变了），需重跑 /code-review-gate：")
        out["reasons"].extend("  - " + s for s in stale)
        return _emit(out, args.format, 3)
    if not reviewed:
        prof = (data.get("profile") or "").lower()
        if prof in ("screen", "full", "scale"):
            out["reasons"].append(
                f"profile={prof} 但 reviewed_files 为空——无法证明审过哪些代码、也无法做过期(审v1交v2)校验。"
                f"screen/full/scale 必须列出实际审过的文件 + sha256（用 `sha256sum <files>` 生成）。")
            return _emit(out, args.format, 3)
        out["warnings"].append("reviewed_files 为空（smoke 可放行；screen/full/scale 则必须非空，否则 BLOCK）。")

    # Independence advisory (NOT a hard block — Codex-only separate-process self-review is accepted).
    indep = data.get("independence")
    profile = (data.get("profile") or "").lower()
    if profile in ("full", "scale") and indep == "host_self":
        out["warnings"].append(
            "full/scale 用的是 host_self（同上下文自审，独立性最弱）——建议至少用 separate_codex"
            "（新开一个 codex exec 只读进程、新鲜上下文、对抗视角审），claim 前尤其。")

    out["ok"] = True
    return _emit(out, args.format, 0)


def _emit(out: dict, fmt: str, code: int) -> int:
    if fmt == "json":
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        tag = "✓ PASS" if out["ok"] else "🛑 BLOCK"
        print(f"[pre_submit_gate] {out['exp_id']}: {tag} (verdict={out['verdict']})")
        for r in out["reasons"]:
            print("  " + r)
        for w in out["warnings"]:
            print("  ⚠️ " + w)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
