#!/usr/bin/env python3
"""Ownership-safe preparation lock with fail-closed Slurm reconciliation."""
from __future__ import annotations

import argparse
import os
import secrets
import socket
import subprocess
import time
from pathlib import Path


def acquire(lock: Path, job_id: str) -> str:
    if not job_id.isdigit():
        raise RuntimeError("numeric Slurm job id required")
    token = f"{job_id}:{socket.gethostname()}:{os.getpid()}:{secrets.token_hex(12)}"
    lock.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(token + "\n")
            return token
        except FileExistsError:
            owner = lock.read_text(encoding="utf-8").strip()
            owner_job = owner.split(":", 1)[0]
            if not owner_job.isdigit():
                raise RuntimeError(f"unparseable existing lock; fail closed: {owner!r}")
            query = subprocess.run(["squeue", "-h", "-j", owner_job, "-o", "%i"], text=True, capture_output=True, check=False)
            if query.returncode != 0:
                raise RuntimeError(f"cannot reconcile lock owner through squeue; fail closed: rc={query.returncode}")
            if owner_job in query.stdout.split():
                raise RuntimeError(f"active preparation lock owned by Slurm job {owner_job}")
            stale = lock.with_name(f"{lock.name}.stale.{int(time.time())}.{owner_job}")
            os.replace(lock, stale)


def release(lock: Path, token: str) -> bool:
    try:
        current = lock.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return False
    if current != token:
        return False
    lock.unlink()
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    acquire_parser = sub.add_parser("acquire")
    acquire_parser.add_argument("--lock", required=True)
    acquire_parser.add_argument("--job-id", required=True)
    release_parser = sub.add_parser("release")
    release_parser.add_argument("--lock", required=True)
    release_parser.add_argument("--token", required=True)
    args = parser.parse_args()
    if args.action == "acquire":
        print(acquire(Path(args.lock), args.job_id))
        return 0
    return 0 if release(Path(args.lock), args.token) else 3


if __name__ == "__main__":
    raise SystemExit(main())
