#!/usr/bin/env python3
"""Small, dependency-light helpers for the frozen whole-genome benchmark."""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


def write_json(path: Path, value: object) -> None:
    """Atomically publish a JSON manifest without replacing a prior result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    temporary.replace(path)


def file_metadata(path: Path) -> Dict[str, object]:
    """Record lightweight file metadata without reading the file contents."""
    info: Dict[str, object] = {"path": str(path), "exists": path.exists()}
    if path.exists():
        stat = path.stat()
        info.update({"size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return info


def open_text(path: Path):
    if path.suffix.lower() in {".gz", ".bgz", ".gzip"}:
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def fasta_records(path: Path) -> Iterator[Tuple[str, str]]:
    """Yield one uppercase FASTA record at a time, retaining IUPAC symbols."""
    name = None
    chunks: List[str] = []
    seen = set()
    with open_text(path) as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks)
                fields = line[1:].split()
                if not fields:
                    raise ValueError("empty FASTA header at line %d" % line_number)
                name = fields[0]
                if name in seen:
                    raise ValueError("duplicate FASTA record: %s" % name)
                seen.add(name)
                chunks = []
            else:
                if name is None:
                    raise ValueError("sequence before FASTA header at line %d" % line_number)
                chunks.append(line.upper())
    if name is not None:
        yield name, "".join(chunks)


def fasta_stats(path: Path) -> Dict[str, object]:
    records = 0
    total_bp = 0
    first = None
    lengths: Dict[str, int] = {}
    for name, sequence in fasta_records(path):
        if first is None:
            first = name
        records += 1
        lengths[name] = len(sequence)
        total_bp += len(sequence)
    if records == 0:
        raise ValueError("empty FASTA: %s" % path)
    return {"records": records, "total_bp": total_bp, "first_record": first,
            "first_record_bp": lengths[first] if first is not None else 0,
            "min_record_bp": min(lengths.values()), "max_record_bp": max(lengths.values())}


def write_first_prefix(source: Path, destination: Path, prefix_bp: int,
                       record_name: Optional[str] = None) -> Dict[str, object]:
    """Write a fixed prefix of a named source contig for the CPU pilot.

    ``record_name`` is explicit because some assemblies begin with short
    alternate scaffolds.  A missing name or a contig shorter than the fixed
    prefix is an engineering failure, rather than an implicit fallback to a
    different sequence.
    """
    if prefix_bp <= 0:
        raise ValueError("prefix_bp must be positive")
    records = fasta_records(source)
    name = sequence = None
    if record_name is None:
        try:
            name, sequence = next(records)
        except StopIteration:
            raise ValueError("empty FASTA: %s" % source)
    else:
        for candidate_name, candidate_sequence in records:
            if candidate_name == record_name:
                name, sequence = candidate_name, candidate_sequence
                break
        if name is None:
            raise ValueError("pilot contig not found in FASTA: %s" % record_name)
    assert name is not None and sequence is not None
    if len(sequence) < prefix_bp:
        raise ValueError("pilot contig %s has only %d bp; need %d" % (name, len(sequence), prefix_bp))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="ascii") as handle:
        handle.write(">%s\n" % name)
        prefix = sequence[:prefix_bp]
        for start in range(0, len(prefix), 80):
            handle.write(prefix[start:start + 80] + "\n")
    return {"record": name, "start_bp": 0, "end_bp": prefix_bp, "length_bp": prefix_bp}


def _elapsed_seconds(value: str) -> Optional[float]:
    value = value.strip()
    if not value:
        return None
    try:
        if ":" in value:
            fields = value.split(":")
            if len(fields) == 3:
                return float(fields[0]) * 3600 + float(fields[1]) * 60 + float(fields[2])
            if len(fields) == 2:
                return float(fields[0]) * 60 + float(fields[1])
        return float(value)
    except ValueError:
        return None


def parse_time_v(path: Path) -> Dict[str, object]:
    result: Dict[str, object] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if "elapsed_(wall_clock)" in key:
            result["elapsed_wall_seconds"] = _elapsed_seconds(value)
        elif "maximum_resident_set_size" in key:
            try:
                result["max_rss_kb"] = int(value)
            except ValueError:
                result["max_rss_kb"] = value
        elif "user_time" in key:
            result["user_seconds"] = _elapsed_seconds(value)
        elif "system_time" in key:
            result["system_seconds"] = _elapsed_seconds(value)
    return result


def run_timed(argv: List[str], cwd: Path, stem: str, env: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """Run a native stage, preserving stdout/stderr and GNU time -v data."""
    cwd.mkdir(parents=True, exist_ok=True)
    stdout_path = cwd / (stem + ".stdout")
    stderr_path = cwd / (stem + ".stderr")
    time_path = cwd / (stem + ".time")
    started = time.monotonic()
    command = ["/usr/bin/time", "-v", "-o", str(time_path)] + argv
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(command, cwd=str(cwd), stdout=stdout, stderr=stderr, env=env)
    wall = time.monotonic() - started
    result: Dict[str, object] = {"argv": argv, "time_argv": command,
                                 "returncode": completed.returncode,
                                 "wall_seconds_observed": wall,
                                 "stdout": str(stdout_path), "stderr": str(stderr_path),
                                 "time_v": str(time_path)}
    result.update(parse_time_v(time_path))
    return result


def slurm_context() -> Dict[str, object]:
    keys = ("SLURM_JOB_ID", "SLURM_JOB_NAME", "SLURM_JOB_NODELIST", "SLURMD_NODENAME",
            "SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE", "CUDA_VISIBLE_DEVICES")
    return {key: os.environ.get(key) for key in keys if os.environ.get(key) is not None}


def host_context() -> Dict[str, object]:
    return {"hostname": platform.node(), "platform": platform.platform(),
            "architecture": platform.machine(), "python": platform.python_version(),
            "cpu_count_visible": os.cpu_count()}


def ensure_empty_output(path: Path) -> None:
    if path.exists():
        raise FileExistsError("refusing to reuse existing output; preserve it and choose a new run: %s" % path)
    path.mkdir(parents=True, exist_ok=False)


def find_nonempty(paths: Iterable[Path]) -> List[Path]:
    return sorted(path for path in paths if path.is_file() and path.stat().st_size > 0)
