#!/usr/bin/env python3
"""Run one TE-Benchmark plugin for one species/genome."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import logging
import os
import sys
import time
from pathlib import Path

from Bio import SeqIO


TOOL_MODULES = {
    "repeatmodeler": "plugins.repeatmodeler.wrapper",
    "edta": "plugins.edta.wrapper",
    "repeatscout": "plugins.repeatscout.wrapper",
}

DEFAULT_PARAMS = {
    "repeatmodeler": {"engine": "ncbi", "ltr_struct": True},
    "edta": {"species": "others", "sensitive": 1, "anno": 1, "evaluate": 1, "force": 1},
    "repeatscout": {"l": 14, "min_length": 50},
}


CONTAINER_BINDS = (
    "/srv/beegfs:/srv/beegfs",
    "/home/users:/home/users",
)

REPEATSCOUT_SHARD_THRESHOLD_BP = 900_000_000
REPEATSCOUT_SHARD_TARGET_BP = 450_000_000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def setup_logging(outdir: Path) -> logging.Logger:
    outdir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("denovo_runner")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    file_handler = logging.FileHandler(outdir / "runner.log", mode="a")
    file_handler.setFormatter(fmt)
    logger.addHandler(stream)
    logger.addHandler(file_handler)
    logging.getLogger().handlers.clear()
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(stream)
    logging.getLogger().addHandler(file_handler)
    return logger


def ensure_container_binds() -> None:
    bind_value = ",".join(CONTAINER_BINDS)
    for key in ("SINGULARITY_BINDPATH", "APPTAINER_BINDPATH"):
        existing = os.environ.get(key, "")
        existing_parts = [part for part in existing.split(",") if part]
        merged = existing_parts[:]
        for bind in CONTAINER_BINDS:
            if bind not in merged:
                merged.append(bind)
        os.environ[key] = ",".join(merged) if merged else bind_value


def validate_done(done: Path, status_path: Path, species: str, tool: str, genome: Path, container: Path) -> bool:
    if not done.exists() or not status_path.exists():
        return False
    try:
        status = json.loads(status_path.read_text())
    except json.JSONDecodeError:
        return False
    if status.get("species") != species or status.get("tool") != tool:
        return False
    if status.get("status") != "success":
        return False
    if status.get("genome") != str(genome):
        return False
    if status.get("container") != str(container):
        return False
    if status.get("genome_sha256") != sha256_file(genome):
        return False
    if status.get("container_sha256") != sha256_file(container):
        return False
    gff3 = Path(str(status.get("gff3_path", "")))
    lib = Path(str(status.get("library_path", "")))
    return gff3.exists() and gff3.stat().st_size > 0 and lib.exists() and lib.stat().st_size > 0


def patch_repeatscout_timeout(wrapper) -> None:
    """Disable the small-test 3-4h subprocess timeouts for full genomes."""
    original = wrapper._exec

    def no_timeout(cmd, timeout=None):
        return original(cmd, timeout=None)

    wrapper._exec = no_timeout


def fasta_bp(path: Path) -> int:
    total = 0
    for rec in SeqIO.parse(str(path), "fasta"):
        total += len(rec.seq)
    return total


def build_fasta_shards(genome: Path, shard_dir: Path, target_bp: int, logger: logging.Logger) -> list[Path]:
    shard_dir.mkdir(parents=True, exist_ok=True)
    shards: list[Path] = []
    handle = None
    shard_bp = 0
    shard_idx = 0

    def open_next():
        nonlocal handle, shard_bp, shard_idx
        if handle is not None:
            handle.close()
        shard_idx += 1
        shard_bp = 0
        path = shard_dir / f"{genome.stem}.shard{shard_idx:03d}.fa"
        shards.append(path)
        handle = path.open("w")

    try:
        for rec in SeqIO.parse(str(genome), "fasta"):
            rec_len = len(rec.seq)
            if handle is None or (shard_bp > 0 and shard_bp + rec_len > target_bp):
                open_next()
            SeqIO.write(rec, handle, "fasta")
            shard_bp += rec_len
    finally:
        if handle is not None:
            handle.close()

    logger.info("Built %d RepeatScout FASTA shards in %s", len(shards), shard_dir)
    return shards


def append_prefixed_fasta(src: Path, dst_handle, prefix: str) -> int:
    kept = 0
    for rec in SeqIO.parse(str(src), "fasta"):
        rec.id = f"{prefix}{rec.id}"
        rec.name = rec.id
        rec.description = rec.id
        SeqIO.write(rec, dst_handle, "fasta")
        kept += 1
    return kept


def append_gff3_body(src: Path, dst_handle) -> int:
    kept = 0
    if not src.exists() or src.stat().st_size == 0:
        return kept
    with src.open() as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            dst_handle.write(line)
            kept += 1
    return kept


def run_repeatscout_sharded(
    module, genome: Path, outdir: Path, container: Path, cpus: int, memory_gb: int, logger: logging.Logger
):
    """Run RepeatScout on record shards to avoid whole-genome build_lmer_table overflow."""
    from core.lib.plugin_interface import ToolOutput

    total_bp = fasta_bp(genome)
    if total_bp < REPEATSCOUT_SHARD_THRESHOLD_BP:
        wrapper = module.Wrapper(config=DEFAULT_PARAMS["repeatscout"], workdir=outdir)
        wrapper.container_image = container
        patch_repeatscout_timeout(wrapper)
        return wrapper.run(genome_path=genome, output_dir=outdir, cpus=cpus, memory_gb=memory_gb)

    shard_root = outdir / "RepeatScout_shards"
    shard_fastas = build_fasta_shards(genome, shard_root / "fastas", REPEATSCOUT_SHARD_TARGET_BP, logger)
    merged_lib = outdir / "library.fasta"
    merged_gff = outdir / "annotation.gff3"
    metrics = outdir / "metrics.json"
    shard_statuses = []

    lib_records = 0
    gff_features = 0
    with merged_lib.open("w") as lib_out, merged_gff.open("w") as gff_out:
        gff_out.write("##gff-version 3\n")
        for idx, shard_fasta in enumerate(shard_fastas, start=1):
            shard_out = shard_root / f"run_{idx:03d}"
            wrapper = module.Wrapper(config=DEFAULT_PARAMS["repeatscout"], workdir=shard_out)
            wrapper.container_image = container
            patch_repeatscout_timeout(wrapper)
            logger.info("RepeatScout shard %03d/%03d: %s", idx, len(shard_fastas), shard_fasta)
            result = wrapper.run(genome_path=shard_fasta, output_dir=shard_out, cpus=cpus, memory_gb=memory_gb)
            shard_statuses.append(
                {
                    "shard": idx,
                    "fasta": str(shard_fasta),
                    "status": result.status,
                    "error_message": result.error_message,
                    "gff3_path": str(result.gff3_path),
                    "library_path": str(result.library_path),
                }
            )
            if Path(result.library_path).exists() and Path(result.library_path).stat().st_size > 0:
                lib_records += append_prefixed_fasta(Path(result.library_path), lib_out, f"shard{idx:03d}_")
            if Path(result.gff3_path).exists() and Path(result.gff3_path).stat().st_size > 0:
                gff_features += append_gff3_body(Path(result.gff3_path), gff_out)

    metrics.write_text(
        json.dumps(
            {
                "mode": "sharded_repeatscout",
                "genome_bp": total_bp,
                "shards": len(shard_fastas),
                "library_records": lib_records,
                "gff3_features": gff_features,
                "shard_statuses": shard_statuses,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    status = "success" if lib_records > 0 and gff_features > 10 else ("partial" if lib_records > 0 else "failed")
    return ToolOutput(
        gff3_path=merged_gff,
        library_path=merged_lib,
        metrics_path=metrics,
        status=status,
        raw_output_dir=shard_root,
        error_message=None if status == "success" else "sharded RepeatScout produced insufficient standardized output",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True, choices=sorted(TOOL_MODULES))
    parser.add_argument("--species", required=True)
    parser.add_argument("--genome", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--te-benchmark-root", default="/home/users/j/jwang/TE_compare/TE-Benchmark")
    parser.add_argument("--container-dir", default="/home/users/j/jwang/TE_compare/TE-Benchmark/containers")
    parser.add_argument("--cpus", type=int, default=16)
    parser.add_argument("--memory-gb", type=int, default=96)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    outdir = Path(args.outdir).resolve()
    logger = setup_logging(outdir)
    logger.propagate = False
    done = outdir / "DONE"
    failed = outdir / "FAILED"
    status_path = outdir / "status.json"

    te_root = Path(args.te_benchmark_root).resolve()
    if str(te_root) not in sys.path:
        sys.path.insert(0, str(te_root))

    genome = Path(args.genome).resolve()
    container = Path(args.container_dir).resolve() / f"{args.tool}.sif"
    if not genome.exists():
        raise SystemExit(f"missing genome: {genome}")
    if not container.exists():
        raise SystemExit(f"missing container: {container}")

    if done.exists() and not args.force:
        if validate_done(done, status_path, args.species, args.tool, genome, container):
            if failed.exists():
                failed.unlink()
            logger.info("Valid DONE exists; skipping %s %s", args.species, args.tool)
            return 0
        logger.warning("Stale or invalid DONE marker found; rerunning %s %s", args.species, args.tool)

    for marker in (done, failed):
        if marker.exists():
            marker.unlink()

    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    ensure_container_binds()

    started = time.time()
    status: dict[str, object] = {
        "species": args.species,
        "tool": args.tool,
        "genome": str(genome),
        "genome_sha256": sha256_file(genome),
        "container": str(container),
        "container_sha256": sha256_file(container),
        "cpus": args.cpus,
        "memory_gb": args.memory_gb,
        "status": "running",
        "started_unix": started,
    }
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")

    try:
        module = importlib.import_module(TOOL_MODULES[args.tool])
        logger.info("Running tool=%s species=%s genome=%s", args.tool, args.species, genome)
        if args.tool == "repeatscout":
            result = run_repeatscout_sharded(module, genome, outdir, container, args.cpus, args.memory_gb, logger)
        else:
            wrapper = module.Wrapper(config=DEFAULT_PARAMS[args.tool], workdir=outdir)
            wrapper.container_image = container
            result = wrapper.run(genome_path=genome, output_dir=outdir, cpus=args.cpus, memory_gb=args.memory_gb)
        elapsed = time.time() - started

        gff3 = Path(result.gff3_path)
        lib = Path(result.library_path)
        status.update(
            {
                "status": result.status,
                "error_message": result.error_message,
                "elapsed_seconds": elapsed,
                "gff3_path": str(gff3),
                "library_path": str(lib),
                "gff3_bytes": gff3.stat().st_size if gff3.exists() else 0,
                "library_bytes": lib.stat().st_size if lib.exists() else 0,
                "raw_output_dir": str(result.raw_output_dir) if result.raw_output_dir else None,
            }
        )
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")

        if result.status != "success":
            logger.error("Tool returned non-success status: %s", result.status)
            failed.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
            return 2
        if not gff3.exists() or gff3.stat().st_size == 0 or not lib.exists() or lib.stat().st_size == 0:
            logger.error("Required standardized outputs missing or empty")
            failed.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
            return 3

        done.write_text("OK\n")
        logger.info("Completed tool=%s species=%s status=%s", args.tool, args.species, result.status)
        return 0
    except Exception as exc:
        elapsed = time.time() - started
        logger.exception("Unhandled failure")
        status.update({"status": "failed", "error_message": str(exc), "elapsed_seconds": elapsed})
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
        failed.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
