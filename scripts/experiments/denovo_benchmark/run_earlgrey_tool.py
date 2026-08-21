#!/usr/bin/env python3
"""Run EarlGrey for one species/genome with standardized status markers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


CONTAINER_BINDS = (
    "/srv/beegfs:/srv/beegfs",
    "/home/users:/home/users",
)

EARLGREY_OVERRIDE = Path(
    "/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/"
    "DENOVO_B_ANIMAL_EVAL_20260620/containers/earlgrey_sandbox/usr/local/bin/earlGrey"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_container_binds(workdir: Path, tmpdir: Path) -> None:
    tmpdir.mkdir(parents=True, exist_ok=True)
    binds = list(CONTAINER_BINDS) + [f"{workdir}:/work", f"{tmpdir}:/tmp"]
    if EARLGREY_OVERRIDE.exists():
        binds.append(f"{EARLGREY_OVERRIDE}:/usr/local/bin/earlGrey")
    for key in ("SINGULARITY_BINDPATH", "APPTAINER_BINDPATH"):
        existing = [part for part in os.environ.get(key, "").split(",") if part]
        merged = existing[:]
        for bind in binds:
            if bind not in merged:
                merged.append(bind)
        os.environ[key] = ",".join(merged)
    for key in ("TMPDIR", "TEMP", "TMP", "SINGULARITYENV_TMPDIR", "APPTAINERENV_TMPDIR"):
        os.environ[key] = "/tmp"


def materialize_input(genome: Path, input_path: Path) -> None:
    input_path.parent.mkdir(parents=True, exist_ok=True)
    if input_path.exists():
        try:
            if input_path.samefile(genome):
                return
        except OSError:
            pass
        if input_path.stat().st_size == genome.stat().st_size and sha256_file(input_path) == sha256_file(genome):
            return
    tmp = input_path.with_suffix(input_path.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        os.link(genome, tmp)
    except OSError:
        shutil.copy2(genome, tmp)
    tmp.rename(input_path)


def find_first(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists() and path.stat().st_size > 0]
    return existing[0] if existing else None


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def materialize_standardized_output(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    tmp = dst.with_name(dst.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        os.link(src, tmp)
    except OSError:
        shutil.copy2(src, tmp)
    tmp.replace(dst)
    return dst


def determine_runtime_workdir(outdir: Path, species: str) -> tuple[Path, Path]:
    persisted = outdir / "work"
    for key in ("EARLGREY_SCRATCH_ROOT", "SLURM_TMPDIR", "TMPDIR"):
        root = os.environ.get(key, "").strip()
        if not root:
            continue
        base = Path(root)
        if not base.exists():
            continue
        runtime = base / "abinitio_te_earlgrey" / species
        return persisted, runtime
    return persisted, persisted


def sync_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def discover_outputs(workdir: Path, species: str) -> tuple[Path | None, Path | None, Path | None]:
    root = workdir / "output" / f"{species}_EarlGrey"
    summary = root / f"{species}_summaryFiles"
    gff = find_first(
        [
            summary / f"{species}.filteredRepeats.gff",
            root / f"{species}_mergedRepeats" / "looseMerge" / f"{species}.filteredRepeats.gff",
            root / f"{species}_mergedRepeats" / f"{species}.filteredRepeats.gff",
        ]
    )
    bed = find_first(
        [
            summary / f"{species}.filteredRepeats.bed",
            root / f"{species}_mergedRepeats" / "looseMerge" / f"{species}.filteredRepeats.bed",
            root / f"{species}_mergedRepeats" / f"{species}.filteredRepeats.bed",
        ]
    )
    libraries = sorted(root.glob(f"{species}_summaryFiles/*.fa*")) + sorted(root.glob(f"{species}_strainer/*.strained"))
    library = find_first(libraries)
    return gff, bed, library


def valid_output_triplet(gff: Path | None, bed: Path | None, library: Path | None) -> bool:
    return all(path is not None and path.exists() and path.stat().st_size > 0 for path in (gff, bed, library))


def valid_done(done: Path, status_path: Path, species: str, genome: Path, container: Path) -> bool:
    if not done.exists() or not status_path.exists():
        return False
    try:
        status = json.loads(status_path.read_text())
    except json.JSONDecodeError:
        return False
    if status.get("species") != species or status.get("tool") != "earlgrey":
        return False
    if status.get("status") != "success":
        return False
    if status.get("genome_sha256") != sha256_file(genome):
        return False
    if status.get("container_sha256") != sha256_file(container):
        return False
    gff = Path(str(status.get("gff_path", "")))
    bed = Path(str(status.get("bed_path", "")))
    library = Path(str(status.get("library_path", "")))
    std_gff = Path(str(status.get("standardized_gff3_path", "")))
    std_lib = Path(str(status.get("standardized_library_path", "")))
    if not valid_output_triplet(gff, bed, library):
        return False
    return std_gff.exists() and std_gff.stat().st_size > 0 and std_lib.exists() and std_lib.stat().st_size > 0


def standardize_outputs(outdir: Path, gff: Path, bed: Path, library: Path) -> tuple[Path, Path, Path]:
    std_gff = materialize_standardized_output(gff, outdir / "annotation.gff3")
    std_lib = materialize_standardized_output(library, outdir / "library.fasta")
    std_bed = materialize_standardized_output(bed, outdir / "annotation.bed")
    return std_gff, std_lib, std_bed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", required=True)
    parser.add_argument("--genome", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--cpus", type=int, default=16)
    parser.add_argument("--repeatmasker-search-term", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    species = args.species
    genome = Path(args.genome).resolve()
    outdir = Path(args.outdir).resolve()
    container = Path(args.container).resolve()
    if not genome.exists():
        raise SystemExit(f"missing genome: {genome}")
    if not container.exists():
        raise SystemExit(f"missing EarlGrey container: {container}")

    outdir.mkdir(parents=True, exist_ok=True)
    status_path = outdir / "status.json"
    done = outdir / "DONE"
    failed = outdir / "FAILED"
    log_path = outdir / "runner.log"

    if done.exists() and not args.force:
        if valid_done(done, status_path, species, genome, container):
            if failed.exists():
                failed.unlink()
            print(f"Valid DONE exists; skipping {species} EarlGrey")
            return 0

    for marker in (done, failed):
        if marker.exists():
            marker.unlink()

    persisted_workdir, runtime_workdir = determine_runtime_workdir(outdir, species)
    if runtime_workdir != persisted_workdir and (persisted_workdir / "output").exists():
        sync_tree(persisted_workdir / "output", runtime_workdir / "output")
    input_path = runtime_workdir / "input" / f"{species}.fa"
    materialize_input(genome, input_path)
    container_tmpdir = runtime_workdir / "tmp"
    ensure_container_binds(runtime_workdir, container_tmpdir)

    cmd = [
        "singularity",
        "exec",
        str(container),
        "earlGrey",
        "-g",
        f"/work/input/{species}.fa",
        "-s",
        species,
        "-o",
        "/work/output",
        "-t",
        str(args.cpus),
    ]
    if args.repeatmasker_search_term:
        cmd.extend(["-r", args.repeatmasker_search_term])

    started = time.time()
    status: dict[str, object] = {
        "species": species,
        "tool": "earlgrey",
        "genome": str(genome),
        "genome_sha256": sha256_file(genome),
        "container": str(container),
        "container_sha256": sha256_file(container),
        "cpus": args.cpus,
        "repeatmasker_search_term": args.repeatmasker_search_term,
        "persisted_workdir": str(persisted_workdir),
        "runtime_workdir": str(runtime_workdir),
        "container_tmpdir": str(container_tmpdir),
        "status": "running",
        "started_unix": started,
        "command": cmd,
    }
    atomic_write_text(status_path, json.dumps(status, indent=2, sort_keys=True) + "\n")

    with log_path.open("ab") as log:
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=False)

    elapsed = time.time() - started
    if runtime_workdir != persisted_workdir:
        sync_tree(runtime_workdir / "output", persisted_workdir / "output")
    discovery_root = persisted_workdir if persisted_workdir.exists() else runtime_workdir
    gff, bed, library = discover_outputs(discovery_root, species)
    std_gff = std_lib = std_bed = None
    success = proc.returncode == 0 and valid_output_triplet(gff, bed, library)
    if success:
        std_gff, std_lib, std_bed = standardize_outputs(outdir, gff, bed, library)
    status.update(
        {
            "elapsed_seconds": elapsed,
            "returncode": proc.returncode,
            "gff_path": str(gff) if gff else "",
            "bed_path": str(bed) if bed else "",
            "library_path": str(library) if library else "",
            "standardized_gff3_path": str(std_gff) if std_gff else "",
            "standardized_bed_path": str(std_bed) if std_bed else "",
            "standardized_library_path": str(std_lib) if std_lib else "",
            "status": "success" if success else "failed",
        }
    )
    atomic_write_text(status_path, json.dumps(status, indent=2, sort_keys=True) + "\n")

    if status["status"] != "success":
        atomic_write_text(failed, json.dumps(status, indent=2, sort_keys=True) + "\n")
        return 2
    atomic_write_text(done, "OK\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
