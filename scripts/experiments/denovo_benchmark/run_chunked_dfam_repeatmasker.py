#!/usr/bin/env python3
"""Chunked RepeatMasker rescue for de novo+Dfam augmentation rows."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def fasta_records(path: Path):
    name = None
    lines: list[str] = []
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    yield name, lines
                name = line[1:].strip().split()[0]
                lines = [line]
            else:
                lines.append(line)
    if name is not None:
        yield name, lines


def record_len(lines: list[str]) -> int:
    total = 0
    for line in lines:
        if not line.startswith(">"):
            total += len(line.strip())
    return total


def write_chunk(path: Path, records: list[tuple[str, list[str]]]) -> int:
    bp = 0
    with path.open("w") as handle:
        for _, lines in records:
            for line in lines:
                handle.write(line)
            bp += record_len(lines)
    return bp


def prepare(args: argparse.Namespace) -> int:
    genome = Path(args.genome).resolve()
    combined_lib = Path(args.combined_library).resolve()
    outdir = Path(args.outdir).resolve()
    chunk_root = Path(args.chunk_root).resolve()
    manifest = Path(args.manifest).resolve()
    chunk_root.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    if not genome.exists():
        raise FileNotFoundError(genome)
    if not combined_lib.exists():
        raise FileNotFoundError(combined_lib)

    rows: list[dict[str, str | int]] = []
    current: list[tuple[str, list[str]]] = []
    current_bp = 0
    chunk_id = 0

    def flush() -> None:
        nonlocal chunk_id, current, current_bp
        if not current:
            return
        chunk_id += 1
        chunk_fasta = chunk_root / "chunks" / f"{args.species}_{args.tool}_chunk{chunk_id:04d}.fa"
        chunk_fasta.parent.mkdir(parents=True, exist_ok=True)
        bp = write_chunk(chunk_fasta, current)
        rows.append(
            {
                "task_id": len(rows) + 1,
                "species": args.species,
                "tool": args.tool,
                "chunk_id": chunk_id,
                "chunk_bp": bp,
                "chunk_fasta": str(chunk_fasta),
                "chunk_outdir": str(chunk_root / "repeatmasker_chunks" / f"chunk{chunk_id:04d}"),
                "combined_library": str(combined_lib),
                "final_outdir": str(outdir),
            }
        )
        current = []
        current_bp = 0

    for rec_name, lines in fasta_records(genome):
        bp = record_len(lines)
        if current and current_bp + bp > args.target_bp:
            flush()
        current.append((rec_name, lines))
        current_bp += bp
        if bp >= args.target_bp:
            flush()
    flush()

    fieldnames = [
        "task_id",
        "species",
        "tool",
        "chunk_id",
        "chunk_bp",
        "chunk_fasta",
        "chunk_outdir",
        "combined_library",
        "final_outdir",
    ]
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} chunks to {manifest}")
    return 0


def read_task(manifest: Path, task_id: str) -> dict[str, str]:
    with manifest.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if row["task_id"] == str(task_id):
                return row
    raise KeyError(f"task_id={task_id} not found in {manifest}")


def run_task(args: argparse.Namespace) -> int:
    row = read_task(Path(args.manifest), args.task_id)
    outdir = Path(row["chunk_outdir"])
    outdir.mkdir(parents=True, exist_ok=True)
    done = outdir / "DONE"
    failed = outdir / "FAILED"
    status = outdir / "status.json"
    chunk_fasta = Path(row["chunk_fasta"])
    combined_lib = Path(row["combined_library"])
    expected_gff = outdir / f"{chunk_fasta.name}.out.gff"
    if done.exists() and expected_gff.exists() and expected_gff.stat().st_size > 0:
        print(f"chunk already done: {row['species']} {row['tool']} task={args.task_id}")
        return 0
    if failed.exists():
        failed.unlink()
    payload = {
        "status": "running",
        "species": row["species"],
        "tool": row["tool"],
        "task_id": args.task_id,
        "chunk_fasta": str(chunk_fasta),
        "chunk_bp": row["chunk_bp"],
        "started_unix": time.time(),
    }
    status.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    cmd = [
        args.repeatmasker,
        "-pa",
        str(args.cpus),
        "-xsmall",
        "-gff",
        "-dir",
        str(outdir),
        "-lib",
        str(combined_lib),
        str(chunk_fasta),
    ]
    log = outdir / "runner.log"
    env = os.environ.copy()
    if args.libdir:
        env["LIBDIR"] = args.libdir
    with log.open("a") as handle:
        handle.write("CMD: " + " ".join(cmd) + "\n")
        proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, env=env)
    if proc.returncode != 0 or not expected_gff.exists() or expected_gff.stat().st_size == 0:
        payload.update({"status": "failed", "returncode": proc.returncode, "elapsed_seconds": time.time() - payload["started_unix"]})
        status.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        failed.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 1
    payload.update({"status": "success", "elapsed_seconds": time.time() - payload["started_unix"], "gff3": str(expected_gff)})
    status.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    done.write_text("OK\n")
    return 0


def finalize(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest)
    rows: list[dict[str, str]] = []
    with manifest.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise RuntimeError(f"empty manifest: {manifest}")

    final_outdir = Path(rows[0]["final_outdir"])
    final_outdir.mkdir(parents=True, exist_ok=True)
    gff_out = final_outdir / "annotation.gff3"
    bed_out = final_outdir / "annotation.bed"
    out_out = final_outdir / "annotation.out"
    missing: list[str] = []
    gff_paths: list[Path] = []
    out_paths: list[Path] = []
    for row in rows:
        chunk_fasta = Path(row["chunk_fasta"])
        chunk_outdir = Path(row["chunk_outdir"])
        done = chunk_outdir / "DONE"
        gff = chunk_outdir / f"{chunk_fasta.name}.out.gff"
        out = chunk_outdir / f"{chunk_fasta.name}.out"
        if not done.exists() or not gff.exists() or gff.stat().st_size == 0:
            missing.append(row["task_id"])
        else:
            gff_paths.append(gff)
            if out.exists():
                out_paths.append(out)
    if missing:
        raise RuntimeError(f"{len(missing)} chunks missing/failed: {','.join(missing[:20])}")

    with gff_out.open("w") as dest:
        for idx, path in enumerate(gff_paths):
            with path.open() as src:
                for line in src:
                    if idx and line.startswith("##gff-version"):
                        continue
                    dest.write(line)
    with bed_out.open("w") as bed, gff_out.open() as src:
        for line in src:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            bed.write(f"{parts[0]}\t{int(parts[3]) - 1}\t{parts[4]}\n")
    if out_paths:
        with out_out.open("w") as dest:
            for path in out_paths:
                with path.open(errors="ignore") as src:
                    shutil.copyfileobj(src, dest)
    combined_lib = Path(rows[0]["combined_library"])
    shutil.copy2(combined_lib, final_outdir / "library.fasta")
    status = {
        "status": "success",
        "mode": "chunked_rescue",
        "species": rows[0]["species"],
        "tool": f"{rows[0]['tool']}_plus_dfam",
        "base_tool": rows[0]["tool"],
        "chunk_count": len(rows),
        "manifest": str(manifest),
        "gff3_path": str(gff_out),
        "bed_path": str(bed_out),
        "library_path": str(final_outdir / "library.fasta"),
        "gff3_bytes": gff_out.stat().st_size,
        "bed_bytes": bed_out.stat().st_size,
    }
    (final_outdir / "status.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    (final_outdir / "DONE").write_text("OK\n")
    failed = final_outdir / "FAILED"
    if failed.exists():
        failed.unlink()
    print(f"finalized {rows[0]['species']} {rows[0]['tool']} from {len(rows)} chunks")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--species", required=True)
    p.add_argument("--tool", default="repeatscout")
    p.add_argument("--genome", required=True)
    p.add_argument("--combined-library", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--chunk-root", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--target-bp", type=int, default=80_000_000)
    p.set_defaults(func=prepare)

    p = sub.add_parser("run")
    p.add_argument("--manifest", required=True)
    p.add_argument("--task-id", required=True)
    p.add_argument("--repeatmasker", default="/home/users/j/jwang/.conda/envs/te_benchmark/bin/RepeatMasker")
    p.add_argument("--cpus", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "8")))
    p.add_argument("--libdir", default="/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/dfam_overlay_20260629/rm_lib_overlay")
    p.set_defaults(func=run_task)

    p = sub.add_parser("finalize")
    p.add_argument("--manifest", required=True)
    p.set_defaults(func=finalize)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
