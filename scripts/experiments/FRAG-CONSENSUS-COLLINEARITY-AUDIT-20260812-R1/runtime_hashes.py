#!/usr/bin/env python3
"""Fail-closed verification of the independent review's runtime file hashes."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import atomic_write_json, read_json, sha256_file


PASS_VERDICTS = {"PASS", "PASS_WITH_WARNINGS"}


def required_runtime_paths(config_path: Path, config: dict) -> list[str]:
    paths = {config_path.as_posix(), *map(str, config["runtime_code_files"])}
    return sorted(paths)


def verify_reviewed_runtime(root: Path, config_path: Path, exp_id: str) -> dict:
    root = root.resolve()
    config_path = config_path.resolve()
    config = read_json(config_path)
    if config.get("exp_id") != exp_id:
        raise RuntimeError("reviewed-runtime config exp_id mismatch")
    try:
        config_relative = config_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise RuntimeError("config must be below project root") from exc
    gate_path = root / "outputs" / exp_id / "code_review_gate.json"
    gate = read_json(gate_path)
    if gate.get("verdict") not in PASS_VERDICTS or int(gate.get("blockers_open", -1)) != 0:
        raise RuntimeError("independent code-review gate is not a zero-blocker PASS verdict")
    reviewed = gate.get("reviewed_files")
    if not isinstance(reviewed, dict) or not reviewed:
        raise RuntimeError("code-review gate reviewed_files must be a non-empty mapping")
    required = required_runtime_paths(Path(config_relative), config)
    files = []
    for relative in required:
        path = root / relative
        expected = reviewed.get(relative)
        if not isinstance(expected, str) or len(expected) != 64:
            raise RuntimeError(f"runtime path absent from independent reviewed_files: {relative}")
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256_file(path)
        if observed != expected:
            raise RuntimeError(f"reviewed runtime hash drift: {relative}")
        files.append({"path": relative, "sha256": observed, "bytes": path.stat().st_size})
    return {
        "schema_version": "FRAG-COLLINEARITY-REVIEWED-RUNTIME-HASHES-1.0.0",
        "exp_id": exp_id,
        "gate_path": gate_path.relative_to(root).as_posix(),
        "gate_sha256": sha256_file(gate_path),
        "review_verdict": gate["verdict"],
        "reviewed_files": files,
    }


def assert_same_reviewed_runtime(pre: dict, post: dict) -> None:
    if pre != post:
        raise RuntimeError("reviewed runtime hashes changed between preflight and pointer publication")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--exp-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    manifest = verify_reviewed_runtime(args.root, args.config, args.exp_id)
    atomic_write_json(args.out, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
