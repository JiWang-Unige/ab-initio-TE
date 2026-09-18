#!/usr/bin/env python3
"""Run one full-input native caller under the frozen whole-genome contract."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional

from common import ensure_empty_output, fasta_stats, file_metadata, run_timed, slurm_context, host_context, write_json


ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "configs/WHOLE-GENOME-BENCHMARK-20260918.json"


def load_config(path: Path) -> Dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def bind_args(out: Path, genome: Path, extra: Optional[Path] = None) -> List[str]:
    # Bind the source directory rather than copying a multi-gigabase assembly.
    args = ["apptainer", "exec", "--cleanenv", "--bind", "%s:/work" % out,
            "--bind", "%s:%s:ro" % (genome.parent, genome.parent)]
    if extra is not None:
        args += ["--bind", "%s:%s:ro" % (extra, extra)]
    args += ["--pwd", "/work"]
    return args


def stage_env() -> Dict[str, str]:
    env = os.environ.copy()
    env.update({"BLAST_USAGE_REPORT": "false", "OMP_NUM_THREADS": "16",
                "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "HOME": "/work/home", "TMPDIR": "/work/tmp"})
    return env


def nonempty(matches: List[Path], label: str) -> Path:
    matches = sorted(path for path in matches if path.is_file() and path.stat().st_size > 0)
    if len(matches) != 1:
        raise RuntimeError("expected exactly one non-empty %s, found %s" % (label, matches))
    return matches[0]


def copy_output(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError("refusing to replace existing output: %s" % destination)
    shutil.copy2(source, destination)


def native_run(args: argparse.Namespace) -> Dict[str, object]:
    config = load_config(args.config.resolve())
    if args.species not in config["species"]:
        raise ValueError("species is not frozen in config: %s" % args.species)
    method = args.method
    method_cfg = config["methods"][method]
    species_cfg = config["species"][args.species]
    output = (ROOT / "outputs/WHOLE-GENOME-BENCHMARK-20260918/native" / args.species / method).resolve()
    ensure_empty_output(output)
    (output / "work").mkdir()
    (output / "tmp").mkdir()
    (output / "home").mkdir()
    source = Path(species_cfg["fasta"])
    if not source.is_file():
        raise FileNotFoundError("frozen source FASTA missing: %s" % source)
    source_info = file_metadata(source)
    source_info["stats"] = fasta_stats(source)
    status: Dict[str, object] = {
        "protocol": "WHOLE-GENOME-BENCHMARK-20260918", "species": args.species,
        "method": method, "status": "RUNNING", "started_epoch": time.time(),
        "input_metadata": source_info, "software": method_cfg, "host": host_context(),
        "slurm": slurm_context(), "stages": [],
        "input_contract": "complete source FASTA; no label read by native runner; contig boundaries retained",
    }
    write_json(output / "status.json", status)
    env = stage_env()
    try:
        if method == "RM2":
            rm2_image = Path(method_cfg["repeatmodeler_image"])
            rm_image = Path(method_cfg["repeatmasker_image"])
            if not rm2_image.is_file() or not rm_image.is_file():
                raise FileNotFoundError("pinned RM2 or RepeatMasker image is missing")
            status["software_metadata"] = {"repeatmodeler_image": file_metadata(rm2_image),
                                            "repeatmasker_image": file_metadata(rm_image)}
            base = bind_args(output, source)
            stage = run_timed(base + [str(rm2_image), "BuildDatabase", "-name", "/work/db", str(source)], output, "builddatabase", env)
            status["stages"].append(dict(stage, name="builddatabase", role="discovery")); write_json(output / "status.json", status)
            if stage["returncode"] != 0:
                raise RuntimeError("BuildDatabase failed")
            stage = run_timed(base + [str(rm2_image), "RepeatModeler", "-database", "/work/db", "-threads", "16", "-srand", "42", "-LTRStruct"], output, "repeatmodeler", env)
            status["stages"].append(dict(stage, name="repeatmodeler", role="discovery")); write_json(output / "status.json", status)
            if stage["returncode"] != 0:
                raise RuntimeError("RepeatModeler failed")
            library = nonempty(list(output.rglob("consensi.fa.classified")), "RepeatModeler classified library")
            rm_out = output / "repeatmasker"
            rm_out.mkdir(exist_ok=True)
            library_guest = "/work/" + str(library.relative_to(output))
            stage = run_timed(base + [str(rm_image), "RepeatMasker", "-e", "rmblast", "-pa", "4", "-gff", "-xsmall",
                                      "-lib", library_guest, "-dir", "/work/repeatmasker", str(source)],
                              output, "repeatmasker", env)
            status["stages"].append(dict(stage, name="repeatmasker", role="masking")); write_json(output / "status.json", status)
            if stage["returncode"] != 0:
                raise RuntimeError("RepeatMasker failed")
            annotation = nonempty(list(rm_out.glob("*.out.gff")), "RepeatMasker GFF")
            raw_out = nonempty(list(rm_out.glob("*.out")), "RepeatMasker .out")
            masked = nonempty(list(rm_out.glob("*.masked")), "RepeatMasker masked FASTA")
            copy_output(annotation, output / "annotation.gff3")
            copy_output(raw_out, output / "annotation.out")
            copy_output(masked, output / "masked.fa")
            copy_output(library, output / "library.fasta")
            status["native_output"] = {"annotation_gff3": "annotation.gff3", "annotation_out": "annotation.out",
                                        "masked_fasta": "masked.fa", "library_fasta": "library.fasta",
                                        "library_source": str(library.relative_to(output)),
                                        "mask_parallelism": "RepeatMasker -pa 4; RMBlast documents four cores per worker"}
        else:
            image = Path(method_cfg["image"])
            overlay = Path(method_cfg["source_overlay"])
            if not image.is_file() or not overlay.is_dir():
                raise FileNotFoundError("pinned EDTA image or source overlay is missing")
            status["software_metadata"] = {"edta_image": file_metadata(image),
                                            "EDTA.pl": file_metadata(overlay / "EDTA.pl")}
            # Use a stable container path for the source overlay.  Binding it
            # back onto its long host path is not reliable with --cleanenv on
            # this Apptainer image, and the failed 12888133 attempt is kept as
            # an engineering record before retrying.
            base = bind_args(output, source)
            base += ["--bind", "%s:/opt/edta230:ro" % overlay]
            command = base + [str(image), "env", "HOME=/work/home", "TMPDIR=/work/tmp", "perl",
                              "/opt/edta230/EDTA.pl", "--genome", str(source),
                              "--species", "others", "--overwrite", "1", "--sensitive", "1",
                              "--anno", "1", "--threads", "16"]
            stage = run_timed(command, output, "edta_all", env)
            stage["role"] = "combined_discovery_and_masking"
            status["stages"].append(dict(stage, name="edta_all")); write_json(output / "status.json", status)
            if stage["returncode"] != 0:
                raise RuntimeError("EDTA failed")
            annotation = nonempty(list(output.rglob("*.EDTA.TEanno.gff3")), "EDTA TEanno GFF3")
            library = nonempty(list(output.rglob("*.EDTA.TElib.fa")), "EDTA TElib FASTA")
            # EDTA also writes a masked file in some releases; retain it when present,
            # while the annotation/library remain the required terminal artifacts.
            masked_candidates = list(output.rglob("*.mod.EDTA.masked.fa")) + list(output.rglob("*.EDTA.masked.fa"))
            copy_output(annotation, output / "annotation.gff3")
            copy_output(library, output / "library.fasta")
            if masked_candidates:
                copy_output(nonempty(masked_candidates, "EDTA masked FASTA"), output / "masked.fa")
            status["native_output"] = {"annotation_gff3": "annotation.gff3", "library_fasta": "library.fasta",
                                        "masking_output": "masked.fa" if (output / "masked.fa").exists() else None,
                                        "discovery_scope": "combined_native_stage"}
        status.update({"status": "COMPLETED", "finished_epoch": time.time(),
                       "wall_seconds": time.time() - float(status["started_epoch"])})
        write_json(output / "status.json", status)
        # The summary is descriptive and does not read labels.  Keep it in the
        # same terminal cell so score.py has one unambiguous native manifest.
        summary_script = Path(__file__).with_name("summarize_native.py")
        summary = subprocess.run([sys.executable, str(summary_script), "--species", args.species,
                                  "--method", method, "--output-dir", str(output)],
                                 cwd=str(summary_script.parent), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        if summary.returncode != 0:
            status["annotation_summary_error"] = summary.stderr[-4000:]
            write_json(output / "status.json", status)
        return status
    except Exception as exc:
        status.update({"status": "FAILED", "finished_epoch": time.time(),
                       "wall_seconds": time.time() - float(status["started_epoch"]),
                       "error": repr(exc)})
        write_json(output / "status.json", status)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--species", required=True, choices=("chicken", "zebrafish"))
    parser.add_argument("--method", required=True, choices=("EDTA", "RM2"))
    native_run(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
