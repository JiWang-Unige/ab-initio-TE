#!/usr/bin/env python3
"""Complete the preserved chicken EDTA cell from the missing Helitron branch.

The preceding recovery job consumed the frozen M4/S7 checkpoint and completed
TIR post-processing, but the original EDTA filter stopped because the
Helitron raw library had not yet been produced.  This driver copies that
failed retry into a new writable tree, runs only the native Helitron branch,
and then runs the unchanged filter/final/annotation stages.  It never writes
to either preserved input tree and never substitutes an empty Helitron file.
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
from typing import Dict, List

from recover_edta import (
    GENOME_BASENAME,
    NORMALIZED_BASENAME,
    PATCH_TARGETS,
    RECOVERY,
    RAW_BASENAME,
    copy_preserved_tree,
    extract_patch,
    native_bindings,
    parse_rss,
    sequence_id_decode_evidence,
    stage_command,
    write_json,
)


def read_prior_retry(path: Path) -> Dict[str, object]:
    """Require the exact failed retry that this continuation is allowed to use."""
    status_path = path / "status.json"
    if not status_path.is_file():
        raise FileNotFoundError(status_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") != "FAILED" or status.get("method") != "EDTA":
        raise ValueError("--failed is not the preserved EDTA retry")
    if status.get("job") != "13189201":
        raise ValueError(f"unexpected prior retry job: {status.get('job')}")
    stages = status.get("stages")
    if not isinstance(stages, list) or len(stages) < 2:
        raise ValueError("prior retry does not contain the required TIR/filter stages")
    tir, filtering = stages[0], stages[1]
    if tir.get("name") != "tir_raw_resume" or tir.get("returncode") != 0:
        raise ValueError("prior TIR stage is not a successful frozen resume")
    if filtering.get("name") != "edta_filter_final_annotation" or filtering.get("returncode") != 2:
        raise ValueError("prior filter stage is not the preserved missing-Helitron failure")
    checkpoint = status.get("checkpoint_consumption", {})
    if checkpoint.get("status") != "PASS" or checkpoint.get("module") != 4 or checkpoint.get("step") != 7:
        raise ValueError("prior retry lacks the required M4/S7 checkpoint-load evidence")
    prior_stderr = path / "edta_filter_final_annotation.stderr"
    stderr = prior_stderr.read_text(encoding="utf-8", errors="replace") if prior_stderr.is_file() else ""
    required = (
        "Helitron raw library file galGal6.fa.mod.EDTA.raw/galGal6.fa.mod.Helitron.intact.raw.fa not exists!",
        "ERROR: Stage 1 library not found",
    )
    if not all(marker in stderr for marker in required):
        raise ValueError("prior filter stderr does not prove the missing-Helitron failure")
    helitron = path / f"{RAW_BASENAME}/galGal6.fa.mod.Helitron.intact.raw.fa"
    if helitron.exists():
        raise ValueError(f"prior tree already contains a Helitron raw library: {helitron}")
    for relative in (
        f"{RAW_BASENAME}/galGal6.fa.mod.LTR.raw.fa",
        f"{RAW_BASENAME}/galGal6.fa.mod.SINE.raw.fa",
        f"{RAW_BASENAME}/galGal6.fa.mod.LINE.raw.fa",
        f"{RAW_BASENAME}/galGal6.fa.mod.TIR.intact.raw.fa",
        f"{NORMALIZED_BASENAME}.RM2.raw.fa",
    ):
        artifact = path / relative
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise ValueError(f"completed prior raw artifact is missing or empty: {artifact}")
    return status


def require_helitron_raw(output: Path) -> Dict[str, object]:
    files = {
        "fasta": output / f"{RAW_BASENAME}/galGal6.fa.mod.Helitron.intact.raw.fa",
        "gff3": output / f"{RAW_BASENAME}/galGal6.fa.mod.Helitron.intact.raw.gff3",
        "bed": output / f"{RAW_BASENAME}/galGal6.fa.mod.Helitron.intact.raw.bed",
    }
    missing = [str(path) for path in files.values() if not path.is_file()]
    empty = [str(path) for path in files.values() if path.is_file() and path.stat().st_size == 0]
    if missing or empty:
        raise RuntimeError(f"native Helitron branch did not produce complete artifacts: missing={missing}, empty={empty}")
    return {
        "status": "PASS",
        "files": {name: {"path": str(path), "bytes": path.stat().st_size} for name, path in files.items()},
        "basis": "EDTA_raw.pl native --type helitron output; no empty-file substitution",
    }


def run(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    failed = args.failed.resolve()
    output = args.output.resolve()
    image = args.image.resolve()
    overlay = args.source_overlay.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to replace continuation output: {output}")
    if not image.is_file() or not overlay.is_dir():
        raise FileNotFoundError("pinned EDTA image or source overlay missing")
    prior = read_prior_retry(failed)
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
        "resume_mode": "fresh output; reuse successful M4/S7 retry and complete Helitron branch; no prior tree writes",
        "resumed_from": str(failed),
        "prior_retry_job": prior.get("job"),
        "prior_retry_slurm_elapsed_seconds": int(args.prior_slurm_seconds),
        "prior_cell_budget_remaining_seconds": budget_seconds,
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
        status["copy"] = dict(copied, wall_seconds=time.monotonic() - copy_started)
        status["reused_tir"] = {
            "status": "PASS",
            "prior_job": prior.get("job"),
            "prior_stage": "tir_raw_resume",
            "prior_returncode": 0,
            "checkpoint": "Module 4 Step 7 load evidence retained in prior status",
            "rerun": False,
        }
        write_json(output / "status.json", status)
        patches = extract_patch(image, output)
        status["compatibility_overlay"] = {
            "files": patches,
            "source_checked_and_compiled": True,
            "policy": "same pinned overlay as prior recovery; only Helitron/filter continuation is executed",
        }
        write_json(output / "status.json", status)
        base = native_bindings(output, overlay, image, patches)
        env = ["env", "HOME=/work/home", "TMPDIR=/work/tmp"]
        genome = "/work/galGal6.fa"
        stage_command(
            output=output,
            status=status,
            name="helitron_raw_continuation",
            started=started,
            budget_seconds=budget_seconds,
            argv=base + env + ["perl", "/opt/edta230/EDTA_raw.pl",
                               "--genome", genome, "--species", "others",
                               "--type", "helitron", "--overwrite", "0", "--threads", "16"],
        )
        status["helitron_artifacts"] = require_helitron_raw(output)
        write_json(output / "status.json", status)
        stage_command(
            output=output,
            status=status,
            name="edta_filter_final_annotation",
            started=started,
            budget_seconds=budget_seconds,
            argv=base + env + ["perl", "/opt/edta230/EDTA.pl",
                               "--genome", genome, "--species", "others",
                               "--step", "filter", "--overwrite", "0",
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
        masked_candidates = [path for pattern in ("*.mod.EDTA.masked.fa", "*.EDTA.masked.fa")
                             for path in output.rglob(pattern)
                             if path.is_file() and path.stat().st_size > 0]
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
