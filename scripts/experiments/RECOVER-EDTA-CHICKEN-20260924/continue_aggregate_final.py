#!/usr/bin/env python3
"""Repair the EDTA raw aggregation and rerun final/annotation only.

The Helitron continuation deliberately called ``EDTA_raw.pl --type helitron``
and therefore did not execute the aggregation in EDTA.pl's ``ALL`` label.
EDTA's ``FINAL`` label needs that aggregate GFF.  This driver starts from a
fresh tree, copies only the completed raw tree and filter-stage combine
artifacts, reproduces the pinned EDTA aggregation commands, and invokes the
unchanged final-to-annotation cascade.  It never copies or reuses the prior
partial ``EDTA.final`` or annotation directories.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Dict

from recover_edta import (
    NORMALIZED_BASENAME,
    PATCH_TARGETS,
    RECOVERY,
    RAW_BASENAME,
    copy_preserved_tree,
    extract_patch,
    native_bindings,
    sequence_id_decode_evidence,
    stage_command,
    write_json,
)


COMBINE_BASENAME = f"{NORMALIZED_BASENAME}.EDTA.combine"
FINAL_BASENAME = f"{NORMALIZED_BASENAME}.EDTA.final"
ANNO_BASENAME = f"{NORMALIZED_BASENAME}.EDTA.anno"


def read_prior_helitron(path: Path) -> Dict[str, object]:
    """Validate the terminal Helitron continuation and its reusable inputs."""
    status_path = path / "status.json"
    if not status_path.is_file():
        raise FileNotFoundError(status_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("method") != "EDTA":
        raise ValueError("--failed is not an EDTA continuation output")
    if status.get("job") != "13189902":
        raise ValueError(f"unexpected Helitron continuation job: {status.get('job')}")
    artifacts = status.get("helitron_artifacts", {})
    if artifacts.get("status") != "PASS":
        raise ValueError("Helitron continuation did not pass its native artifact gate")
    for relative in (
        f"{RAW_BASENAME}/galGal6.fa.mod.LTR.intact.raw.fa",
        f"{RAW_BASENAME}/galGal6.fa.mod.TIR.intact.raw.fa",
        f"{RAW_BASENAME}/galGal6.fa.mod.Helitron.intact.raw.fa",
        f"{RAW_BASENAME}/galGal6.fa.mod.LTR.intact.raw.gff3",
        f"{RAW_BASENAME}/galGal6.fa.mod.TIR.intact.raw.gff3",
    ):
        artifact = path / relative
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise ValueError(f"required raw artifact is missing or empty: {artifact}")
    aggregate = path / f"{RAW_BASENAME}/galGal6.fa.mod.EDTA.intact.raw.gff3"
    if aggregate.exists():
        raise ValueError(f"prior output unexpectedly already contains raw aggregate GFF: {aggregate}")
    combine = path / COMBINE_BASENAME
    stage1 = combine / f"{NORMALIZED_BASENAME}.EDTA.fa.stg1"
    intact_clean = combine / f"{NORMALIZED_BASENAME}.EDTA.intact.fa.cln"
    for artifact in (stage1, intact_clean):
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise ValueError(f"filter-stage combine artifact is missing or empty: {artifact}")
    return status


def copy_combine_stage(failed: Path, output: Path) -> Dict[str, object]:
    """Copy only filter outputs needed by FINAL; exclude all partial final/ANNO."""
    source = failed / COMBINE_BASENAME
    target = output / COMBINE_BASENAME
    if target.exists():
        raise FileExistsError(target)
    shutil.copytree(source, target, symlinks=True)
    links = []
    for directory, dirnames, filenames in os.walk(target, followlinks=False):
        for name in (*dirnames, *filenames):
            link = Path(directory) / name
            if not link.is_symlink():
                continue
            raw_target = os.readlink(link)
            resolved = (link.parent / raw_target).resolve()
            if os.path.isabs(raw_target) or not resolved.is_relative_to(output.resolve()):
                raise ValueError(f"copied combine link escapes fresh output: {link} -> {raw_target}")
            links.append({"path": str(link), "target": raw_target})
    stage1 = target / f"{NORMALIZED_BASENAME}.EDTA.fa.stg1"
    intact_clean = target / f"{NORMALIZED_BASENAME}.EDTA.intact.fa.cln"
    return {
        "source": str(source),
        "target": str(target),
        "stage1": {"path": str(stage1), "bytes": stage1.stat().st_size},
        "intact_clean": {"path": str(intact_clean), "bytes": intact_clean.stat().st_size},
        "relative_links_checked": links,
        "partial_final_copied": False,
        "partial_annotation_copied": False,
    }


def run(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    failed = args.failed.resolve()
    output = args.output.resolve()
    image = args.image.resolve()
    overlay = args.source_overlay.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to replace aggregate recovery output: {output}")
    if not image.is_file() or not overlay.is_dir():
        raise FileNotFoundError("pinned EDTA image or source overlay missing")
    prior = read_prior_helitron(failed)
    budget_seconds = int(args.budget_seconds)
    if budget_seconds <= 0:
        raise ValueError("budget_seconds must be positive")
    output.mkdir(parents=True)
    status: Dict[str, object] = {
        "protocol": RECOVERY,
        "parent_protocol": "WHOLE-GENOME-BENCHMARK-20260918",
        "species": "chicken",
        "assembly": "galGal6",
        "method": "EDTA",
        "status": "RUNNING",
        "job": os.environ.get("SLURM_JOB_ID"),
        "hostname": os.uname().nodename,
        "resources": {"partition": "private-teodoro-gpu", "cpus": 16,
                       "memory_gb": 128, "gres": None},
        "resume_mode": "fresh output; reuse raw+filter combine only; native raw aggregate then FINAL/ANNO",
        "resumed_from": str(failed),
        "prior_helitron_job": prior.get("job"),
        "prior_helitron_slurm_elapsed_seconds": int(args.prior_slurm_seconds),
        "recovery_budget_seconds": budget_seconds,
        "native_parameters": "--species others --sensitive 1 --anno 1 --threads 16; no curated library, CDS, exclude BED, or --force",
        "image": str(image),
        "source_overlay": str(overlay),
        "stages": [],
    }
    write_json(output / "status.json", status)
    started = time.monotonic()
    try:
        copy_started = time.monotonic()
        copied = copy_preserved_tree(failed, output)
        combine = copy_combine_stage(failed, output)
        status["copy"] = dict(copied, wall_seconds=time.monotonic() - copy_started)
        status["reused_filter_combine"] = combine
        status["reused_helitron"] = {
            "status": "PASS",
            "prior_job": prior.get("job"),
            "prior_stage": "helitron_raw_continuation",
            "prior_returncode": 0,
            "rerun": False,
        }
        write_json(output / "status.json", status)
        patches = extract_patch(image, output)
        status["compatibility_overlay"] = {
            "files": patches,
            "source_checked_and_compiled": True,
            "policy": "same pinned overlay; no TIR or Helitron rerun",
        }
        write_json(output / "status.json", status)

        base = native_bindings(output, overlay, image, patches)
        env = ["env", "HOME=/work/home", "TMPDIR=/work/tmp"]
        aggregate_script = r'''set -euo pipefail
cd /work/galGal6.fa.mod.EDTA.raw
cat galGal6.fa.mod.LTR.intact.raw.fa galGal6.fa.mod.TIR.intact.raw.fa galGal6.fa.mod.Helitron.intact.raw.fa > galGal6.fa.mod.EDTA.intact.raw.fa
cat galGal6.fa.mod.TIR.intact.raw.bed galGal6.fa.mod.Helitron.intact.raw.bed | perl /opt/edta230/bin/bed2gff.pl - TE_struc > galGal6.fa.mod.EDTA.intact.gff3.temp
cat galGal6.fa.mod.LTR.intact.raw.gff3 >> galGal6.fa.mod.EDTA.intact.gff3.temp
sort -sV -k1,1 -k4,4 galGal6.fa.mod.EDTA.intact.gff3.temp | grep -v '^#' > galGal6.fa.mod.EDTA.intact.raw.gff3
rm galGal6.fa.mod.EDTA.intact.gff3.temp
test -s galGal6.fa.mod.EDTA.intact.raw.fa
test -s galGal6.fa.mod.EDTA.intact.raw.gff3
'''
        stage_command(
            output=output,
            status=status,
            name="native_raw_intact_aggregate",
            started=started,
            budget_seconds=budget_seconds,
            argv=base + env + ["bash", "-lc", aggregate_script],
        )
        raw_dir = output / RAW_BASENAME
        aggregate_files = {
            "fasta": raw_dir / f"{NORMALIZED_BASENAME}.EDTA.intact.raw.fa",
            "gff3": raw_dir / f"{NORMALIZED_BASENAME}.EDTA.intact.raw.gff3",
        }
        status["native_raw_aggregate"] = {
            "status": "PASS",
            "source_lines": "EDTA.pl ALL lines 516-520 reproduced verbatim in pinned container",
            "files": {name: {"path": str(path), "bytes": path.stat().st_size} for name, path in aggregate_files.items()},
            "components": ["LTR.intact.raw", "TIR.intact.raw", "Helitron.intact.raw"],
        }
        write_json(output / "status.json", status)
        stage_command(
            output=output,
            status=status,
            name="edta_final_annotation",
            started=started,
            budget_seconds=budget_seconds,
            argv=base + env + ["perl", "/opt/edta230/EDTA.pl",
                               "--genome", "/work/galGal6.fa", "--species", "others",
                               "--step", "final", "--overwrite", "0",
                               "--sensitive", "1", "--anno", "1", "--threads", "16"],
        )
        final_candidates = sorted(path for path in output.rglob("*.EDTA.TEanno.gff3")
                                 if path.is_file() and path.stat().st_size > 0)
        library_candidates = sorted(path for path in output.rglob("*.EDTA.TElib.fa")
                                    if path.is_file() and path.stat().st_size > 0)
        if len(final_candidates) != 1 or len(library_candidates) != 1:
            raise RuntimeError(f"terminal EDTA outputs not unique: gff={final_candidates}, lib={library_candidates}")
        annotation = output / "annotation.gff3"
        library = output / "library.fasta"
        shutil.copy2(final_candidates[0], annotation)
        shutil.copy2(library_candidates[0], library)
        status["sequence_id_decoding"] = sequence_id_decode_evidence(output, annotation)
        masked_candidates = sorted({path for pattern in ("*.mod.EDTA.masked.fa", "*.EDTA.masked.fa")
                                    for path in output.rglob(pattern)
                                    if path.is_file() and path.stat().st_size > 0})
        status["native_output"] = {
            "annotation_gff3": "annotation.gff3",
            "library_fasta": "library.fasta",
            "annotation_source": str(final_candidates[0]),
            "library_source": str(library_candidates[0]),
            "masking_output": "masked.fa" if masked_candidates else None,
            "terminal_output_candidates": {"gff3": len(final_candidates), "library": len(library_candidates)},
        }
        if masked_candidates:
            if len(masked_candidates) != 1:
                raise RuntimeError(f"terminal EDTA masked FASTA not unique: {masked_candidates}")
            shutil.copy2(masked_candidates[0], output / "masked.fa")
        status["status"] = "COMPLETED"
        write_json(output / "status.json", status)
        summary_script = root / "scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/summarize_native.py"
        summary = subprocess.run(
            [sys.executable, str(summary_script), "--species", "chicken",
             "--method", "EDTA", "--output-dir", str(output)],
            cwd=str(summary_script.parent), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        if summary.returncode != 0:
            raise RuntimeError(f"native annotation summary failed: {summary.stderr[-4000:]}")
        status["annotation_summary"] = {
            "path": str(output / "annotation_summary.json"),
            "stdout": summary.stdout[-4000:],
            "status": "COMPLETED",
        }
        status.update({"status": "COMPLETED", "finished_epoch": time.time(),
                       "wall_seconds": time.monotonic() - started})
        write_json(output / "status.json", status)
        return 0
    except Exception as exc:
        status.update({"status": "FAILED", "finished_epoch": time.time(),
                       "wall_seconds": time.monotonic() - started,
                       "error": repr(exc)})
        write_json(output / "status.json", status)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--failed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--source-overlay", type=Path, required=True)
    parser.add_argument("--budget-seconds", type=int, required=True)
    parser.add_argument("--prior-slurm-seconds", type=int, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
