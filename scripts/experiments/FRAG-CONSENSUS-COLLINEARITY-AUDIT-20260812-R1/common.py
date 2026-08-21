#!/usr/bin/env python3
"""Shared deterministic IO helpers for the experiment-local audit."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def atomic_write_json(path: Path, value: object) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: Iterable[Mapping[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    os.replace(tmp, path)


def iter_fasta(path: Path) -> Iterator[tuple[str, str]]:
    name: str | None = None
    chunks: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks).upper()
                name = line[1:].split()[0]
                if not name:
                    raise ValueError(f"empty FASTA identifier in {path}")
                if name in seen:
                    raise ValueError(f"duplicate FASTA identifier {name!r} in {path}")
                seen.add(name)
                chunks = []
            elif name is None:
                raise ValueError(f"sequence before header in {path}")
            else:
                chunks.append(line)
    if name is not None:
        yield name, "".join(chunks).upper()


def write_fasta(path: Path, records: Iterable[tuple[str, str]], width: int = 80) -> None:
    parts: list[str] = []
    for name, sequence in records:
        parts.append(f">{name}\n")
        for offset in range(0, len(sequence), width):
            parts.append(sequence[offset : offset + width] + "\n")
    atomic_write_text(path, "".join(parts))


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGTNacgtn", "TGCANtgcan"))[::-1].upper()


def require_hash(root: Path, spec: Mapping[str, object]) -> Path:
    path = root / str(spec["path"])
    expected = str(spec["sha256"])
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = sha256_file(path)
    if observed != expected:
        raise ValueError(f"hash mismatch for {path}: expected {expected}, observed {observed}")
    return path


def stable_token(*parts: object, length: int = 20) -> str:
    body = "\t".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(body).hexdigest()[:length]
