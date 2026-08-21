#!/usr/bin/env python3
"""Run RepeatMasker on a combined de novo library plus Dfam specieslib."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

INDEX_SUFFIXES = {
    ".ndb",
    ".nhr",
    ".nin",
    ".njs",
    ".not",
    ".nsq",
    ".ntf",
    ".nto",
}
EXCLUDE_NAMES = {"refineableHash.dat", "rmblastdb.log", "speciesMeta.pm"}


def species_dir_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name.strip().lower()).strip("_")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def append_with_prefix(src: Path, dst_handle, prefix: str) -> int:
    count = 0
    with src.open(errors="ignore") as handle:
        for line in handle:
            if line.startswith(">"):
                count += 1
                header = line[1:].strip()
                dst_handle.write(f">{prefix}{header}\n")
            else:
                dst_handle.write(line)
    return count


def dfam_library_candidates(species_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in sorted(species_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name in EXCLUDE_NAMES:
            continue
        if path.suffix in INDEX_SUFFIXES:
            continue
        candidates.append(path)
    return candidates


def resolve_dfam_inputs(overlay: Path, rm_species: str) -> tuple[Path, list[Path], str]:
    species_root = overlay / "CONS-Dfam_3.9"
    safe = species_dir_name(rm_species)
    search_dirs = [species_root / safe, species_root / f"{safe}.working"]
    for species_dir in search_dirs:
        if not species_dir.exists():
            continue
        specieslib = species_dir / "specieslib"
        if specieslib.exists():
            return species_dir, [specieslib], "single_specieslib"
        candidates = dfam_library_candidates(species_dir)
        if candidates:
            return species_dir, candidates, "split_component_libs"
    raise FileNotFoundError(
        f"missing Dfam species library for {rm_species}: tried "
        + ", ".join(str(path) for path in search_dirs)
    )


def write_status(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", required=True)
    parser.add_argument("--repeatmasker-species", required=True)
    parser.add_argument("--genome", required=True)
    parser.add_argument("--denovo-tool", required=True)
    parser.add_argument("--denovo-library", required=True)
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--repeatmasker", default="/home/users/j/jwang/.conda/envs/te_benchmark/bin/RepeatMasker")
    parser.add_argument("--cpus", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    status_path = outdir / "status.json"
    done = outdir / "DONE"
    failed = outdir / "FAILED"
    if args.force:
        for p in (done, failed):
            if p.exists():
                p.unlink()

    if done.exists() and not args.force:
        print(f"Valid DONE exists; skipping {args.species} {args.denovo_tool}", file=sys.stderr)
        return 0

    genome = Path(args.genome).resolve()
    denovo_library = Path(args.denovo_library).resolve()
    overlay = Path(args.overlay).resolve()
    repeatmasker = Path(args.repeatmasker).resolve()
    species_dir, dfam_inputs, dfam_mode = resolve_dfam_inputs(overlay, args.repeatmasker_species)
    workdir = outdir / "repeatmasker_output"
    workdir.mkdir(parents=True, exist_ok=True)
    combined_lib = outdir / "combined_library.fasta"
    combined_meta = outdir / "combined_library_components.json"

    started = time.time()
    status = {
        "species": args.species,
        "tool": f"{args.denovo_tool}_plus_dfam",
        "base_tool": args.denovo_tool,
        "repeatmasker_species": args.repeatmasker_species,
        "status": "running",
        "started_unix": started,
        "genome": str(genome),
        "denovo_library": str(denovo_library),
        "specieslib_dir": str(species_dir),
        "specieslib_mode": dfam_mode,
        "specieslib_inputs": [str(path) for path in dfam_inputs],
        "overlay": str(overlay),
        "repeatmasker": str(repeatmasker),
        "cpus": args.cpus,
    }
    write_status(status_path, status)

    try:
        if not genome.exists():
            raise FileNotFoundError(f"missing genome: {genome}")
        if not denovo_library.exists():
            raise FileNotFoundError(f"missing de novo library: {denovo_library}")
        if not dfam_inputs:
            raise FileNotFoundError(f"missing Dfam library inputs in: {species_dir}")
        if not repeatmasker.exists():
            raise FileNotFoundError(f"missing RepeatMasker binary: {repeatmasker}")

        if combined_lib.exists():
            combined_lib.unlink()
        dfam_components: list[dict[str, str | int]] = []
        with combined_lib.open("w") as handle:
            dfam_records = 0
            for src in dfam_inputs:
                recs = append_with_prefix(src, handle, f"dfam_{src.stem}_")
                dfam_records += recs
                dfam_components.append(
                    {
                        "path": str(src),
                        "records": recs,
                    }
                )
            denovo_records = append_with_prefix(denovo_library, handle, f"{args.denovo_tool}_")
        combined_meta.write_text(
            json.dumps(
                {
                    "species": args.species,
                    "repeatmasker_species": args.repeatmasker_species,
                    "specieslib_dir": str(species_dir),
                    "specieslib_mode": dfam_mode,
                    "specieslib_records": dfam_records,
                    "specieslib_components": dfam_components,
                    "denovo_library": str(denovo_library),
                    "denovo_library_records": denovo_records,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

        env = os.environ.copy()
        env["LIBDIR"] = str(overlay)
        cmd = [
            str(repeatmasker),
            "-pa",
            str(args.cpus),
            "-xsmall",
            "-gff",
            "-dir",
            str(workdir),
            "-lib",
            str(combined_lib),
            str(genome),
        ]
        log = outdir / "runner.log"
        with log.open("a") as handle:
            handle.write("CMD: " + " ".join(cmd) + "\n")
            proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, env=env)
        if proc.returncode != 0:
            raise RuntimeError(f"RepeatMasker exited with code {proc.returncode}")

        stem = genome.name
        gff_src = workdir / f"{stem}.out.gff"
        out_src = workdir / f"{stem}.out"
        tbl_src = workdir / f"{stem}.tbl"
        masked_src = workdir / f"{stem}.masked"
        if not gff_src.exists() or gff_src.stat().st_size == 0:
            raise FileNotFoundError(f"missing RepeatMasker gff output: {gff_src}")

        annotation_gff3 = outdir / "annotation.gff3"
        library_fasta = outdir / "library.fasta"
        annotation_bed = outdir / "annotation.bed"
        shutil.copy2(gff_src, annotation_gff3)
        shutil.copy2(combined_lib, library_fasta)

        with annotation_bed.open("w") as handle, gff_src.open() as src:
            for line in src:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 5:
                    continue
                start = int(parts[3]) - 1
                end = int(parts[4])
                handle.write(f"{parts[0]}\t{start}\t{end}\n")

        elapsed = time.time() - started
        status.update(
            {
                "status": "success",
                "elapsed_seconds": elapsed,
                "genome_sha256": sha256_file(genome),
                "specieslib_dir": str(species_dir),
                "specieslib_mode": dfam_mode,
                "specieslib_component_sha256": {
                    str(path): sha256_file(path) for path in dfam_inputs
                },
                "denovo_library_sha256": sha256_file(denovo_library),
                "combined_library_path": str(combined_lib),
                "combined_library_sha256": sha256_file(combined_lib),
                "gff3_path": str(annotation_gff3),
                "bed_path": str(annotation_bed),
                "library_path": str(library_fasta),
                "raw_repeatmasker_out": str(out_src) if out_src.exists() else "",
                "raw_repeatmasker_tbl": str(tbl_src) if tbl_src.exists() else "",
                "raw_repeatmasker_masked": str(masked_src) if masked_src.exists() else "",
                "gff3_bytes": annotation_gff3.stat().st_size,
                "bed_bytes": annotation_bed.stat().st_size,
                "library_bytes": library_fasta.stat().st_size,
            }
        )
        write_status(status_path, status)
        done.write_text("OK\n")
        if failed.exists():
            failed.unlink()
        return 0
    except Exception as exc:
        status.update(
            {
                "status": "failed",
                "error_message": str(exc),
                "elapsed_seconds": time.time() - started,
            }
        )
        write_status(status_path, status)
        failed.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
