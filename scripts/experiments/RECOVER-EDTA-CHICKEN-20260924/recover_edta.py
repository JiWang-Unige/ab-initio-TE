#!/usr/bin/env python3
"""Resume the preserved chicken EDTA cell in a fresh output tree.

The driver only resumes the TIR-Learner checkpoint and then the unchanged EDTA
filter/final/annotation stages.  It never writes to the preserved failed cell.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional


RECOVERY = "RECOVER-EDTA-CHICKEN-20260924"
GENOME_BASENAME = "galGal6.fa"
NORMALIZED_BASENAME = "galGal6.fa.mod"
RAW_BASENAME = "galGal6.fa.mod.EDTA.raw"
PATCH_TARGETS = {
    "get_fasta_sequence.py": "/usr/local/share/TIR-Learner3.0/bin/get_fasta_sequence.py",
    "check_TIR_TSD.py": "/usr/local/share/TIR-Learner3.0/bin/check_TIR_TSD.py",
}


def write_json(path: Path, value: Dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def patch_source(name: str, source: str) -> str:
    if name == "get_fasta_sequence.py":
        old = '''    df["seq"] = df.swifter.progress_bar(flag_verbose).apply(
        lambda x: str(genome_SeqRecord.seq[x["start"]: x["end"]]), axis=1)'''
        new = '''    df["seq"] = df.apply(
        lambda x: str(genome_SeqRecord.seq[x["start"]: x["end"]]), axis=1)'''
        if source.count(old) != 1:
            raise ValueError("unexpected get_fasta_sequence.py nested-apply source")
        return source.replace(old, new, 1)
    if name == "check_TIR_TSD.py":
        if source.count("family = x[0]") != 2:
            raise ValueError("unexpected check_TIR_TSD.py family access count")
        return source.replace("family = x[0]", 'family = x["TIR_type"]')
    raise ValueError(name)


def extract_patch(image: Path, output: Path) -> Dict[str, str]:
    patch_dir = output / "edta_compat" / "TIR-Learner3.0" / "bin"
    patch_dir.mkdir(parents=True, exist_ok=True)
    written: Dict[str, str] = {}
    for name, target in PATCH_TARGETS.items():
        source = subprocess.check_output(
            ["apptainer", "exec", "--cleanenv", str(image), "cat", target],
            text=True,
        )
        patched = patch_source(name, source)
        compile(patched, name, "exec")
        path = patch_dir / name
        path.write_text(patched, encoding="utf-8")
        path.chmod(0o644)
        written[name] = str(path)
    return written


def parse_rss(time_path: Path) -> Optional[int]:
    if not time_path.exists():
        return None
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)",
                      time_path.read_text(encoding="utf-8", errors="replace"))
    return int(match.group(1)) if match else None


def checkpoint_load_evidence(output: Path) -> Dict[str, object]:
    """Require the native resume log to prove that Module 4/Step 7 loaded.

    ``EDTA_raw.pl --overwrite 0`` delegates checkpoint selection to
    TIR-Learner's ``-c auto`` path.  The copied checkpoint is therefore not
    enough by itself: the recovery must retain the child's explicit load
    message before it can continue to EDTA's downstream stages.
    """
    streams = []
    for name in ("tir_raw_resume.stdout", "tir_raw_resume.stderr"):
        path = output / name
        if path.exists():
            streams.append(path.read_text(encoding="utf-8", errors="replace"))
    text = "\n".join(streams)
    loaded = "Successfully loaded checkpoint" in text
    module_step = bool(re.search(r"Module:\s*4\s*\n\s*Step:\s*7", text))
    if not loaded or not module_step:
        raise RuntimeError(
            "TIR-Learner did not prove loading the frozen Module4 Step7 checkpoint "
            f"(loaded={loaded}, module_step={module_step})"
        )
    return {
        "status": "PASS",
        "message": "Successfully loaded checkpoint",
        "module": 4,
        "step": 7,
        "streams_checked": ["tir_raw_resume.stdout", "tir_raw_resume.stderr"],
    }


def sequence_id_decode_evidence(output: Path, annotation: Path) -> Dict[str, object]:
    """Confirm EDTA's native post-annotation map decoding reached the copy."""
    mapping = output / f"{NORMALIZED_BASENAME}.seqid.map"
    if not mapping.is_file() or mapping.stat().st_size == 0:
        raise RuntimeError(f"native sequence-id map is missing: {mapping}")
    encoded_rows = []
    with annotation.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if fields and re.match(r"^_J[0-9A-Za-z]+$", fields[0]):
                encoded_rows.append({"line": line_number, "seqid": fields[0]})
                if len(encoded_rows) >= 10:
                    break
    if encoded_rows:
        raise RuntimeError(
            "terminal EDTA annotation still contains encoded sequence IDs "
            f"after native decode_text: {encoded_rows}"
        )
    return {
        "status": "PASS",
        "map": str(mapping),
        "encoded_annotation_seqids": 0,
        "basis": "EDTA.pl native seqid_codec decode_text after final annotation",
    }


def stage_command(
    *,
    output: Path,
    status: Dict[str, object],
    name: str,
    argv: List[str],
    started: float,
    budget_seconds: int,
) -> None:
    left = int(budget_seconds - (time.monotonic() - started))
    if left <= 0:
        raise TimeoutError(f"recovery budget exhausted before {name}")
    stdout = output / f"{name}.stdout"
    stderr = output / f"{name}.stderr"
    time_file = output / f"{name}.time"
    before = time.monotonic()
    with stdout.open("w", encoding="utf-8") as stdout_handle, stderr.open("w", encoding="utf-8") as stderr_handle:
        result = subprocess.run(
            ["timeout", "--kill-after=60s", str(left), "/usr/bin/time", "-v", "-o", str(time_file)]
            + argv,
            cwd=str(output),
            stdout=stdout_handle,
            stderr=stderr_handle,
        )
    stage = {
        "name": name,
        "argv": argv,
        "returncode": result.returncode,
        "wall_seconds": time.monotonic() - before,
        "stdout": str(stdout),
        "stderr": str(stderr),
        "time": str(time_file),
        "max_rss_kb": parse_rss(time_file),
    }
    stages = status.setdefault("stages", [])
    assert isinstance(stages, list)
    stages.append(stage)
    write_json(output / "status.json", status)
    if result.returncode in (124, 137):
        raise TimeoutError(f"{name} timed out")
    if result.returncode != 0:
        raise RuntimeError(f"{name} exited {result.returncode}")


def copy_preserved_tree(failed: Path, output: Path) -> Dict[str, object]:
    required = [
        failed / NORMALIZED_BASENAME,
        failed / f"{NORMALIZED_BASENAME}.seqid.map",
        failed / f"{NORMALIZED_BASENAME}.RM2.raw.fa",
        failed / f"{NORMALIZED_BASENAME}.EDTA.raw",
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    shutil.copy2(failed / NORMALIZED_BASENAME, output / NORMALIZED_BASENAME)
    shutil.copy2(failed / f"{NORMALIZED_BASENAME}.seqid.map",
                 output / f"{NORMALIZED_BASENAME}.seqid.map")
    shutil.copy2(failed / f"{NORMALIZED_BASENAME}.RM2.raw.fa",
                 output / f"{NORMALIZED_BASENAME}.RM2.raw.fa")
    shutil.copytree(failed / f"{NORMALIZED_BASENAME}.EDTA.raw",
                    output / f"{NORMALIZED_BASENAME}.EDTA.raw", symlinks=True)
    # EDTA must receive the original basename so it discovers the copied
    # normalized galGal6.fa.mod instead of creating galGal6.fa.mod.mod.
    (output / GENOME_BASENAME).symlink_to(NORMALIZED_BASENAME)
    for dirname in ("home", "tmp"):
        (output / dirname).mkdir()
    checkpoint = output / f"{RAW_BASENAME}/TIR/TIR-Learner_v3_checkpoint_2026-09-19T18-34-43Z"
    info = checkpoint / "info.txt"
    if not info.is_file():
        raise ValueError("copied checkpoint info.txt is missing")
    info_lines = info.read_text(encoding="utf-8").splitlines()
    if len(info_lines) < 3:
        raise ValueError("copied checkpoint info.txt is incomplete")
    try:
        progress = json.loads(info_lines[1])
        working_files = json.loads(info_lines[2])
    except json.JSONDecodeError as exc:
        raise ValueError("copied checkpoint info.txt is not valid JSON") from exc
    if progress != ["others", 4, 7]:
        raise ValueError("copied checkpoint is not the frozen Module4 Step7 checkpoint")
    checkpoint_files = []
    for value in working_files.values():
        csv_path = checkpoint / f"{value}.csv"
        dtype_path = checkpoint / f"{value}_dtypes.txt"
        if not csv_path.is_file() or not dtype_path.is_file():
            raise ValueError(f"copied checkpoint working file is incomplete: {value}")
        checkpoint_files.extend([str(csv_path), str(dtype_path)])
    processed = checkpoint / "TIR-Learner-+-processed_de_novo_result.fa"
    if not processed.is_file() or processed.stat().st_size == 0:
        raise ValueError("copied checkpoint processed_de_novo_result.fa is missing or empty")

    # The preserved EDTA tree contains a few relative links to the normalized
    # genome.  Refuse any absolute/stale link that would make a fresh recovery
    # write outside its own output root.
    links = []
    for directory, dirnames, filenames in os.walk(output / RAW_BASENAME,
                                                   followlinks=False):
        for name in (*dirnames, *filenames):
            link = Path(directory) / name
            if not link.is_symlink():
                continue
            target = os.readlink(link)
            resolved = (link.parent / target).resolve()
            if os.path.isabs(target) or not resolved.is_relative_to(output.resolve()):
                raise ValueError(f"copied EDTA.raw link escapes fresh output: {link} -> {target}")
            links.append({"path": str(link), "target": target})
    return {
        "normalized_genome": str(output / NORMALIZED_BASENAME),
        "raw_tree": str(output / RAW_BASENAME),
        "checkpoint": str(checkpoint),
        "checkpoint_info": info.read_text(encoding="utf-8"),
        "checkpoint_progress": progress,
        "checkpoint_working_files": checkpoint_files,
        "relative_links_checked": links,
    }


def native_bindings(output: Path, overlay: Path, image: Path, patches: Dict[str, str]) -> List[str]:
    args = [
        "apptainer", "exec", "--cleanenv",
        "--bind", f"{output}:/work",
        "--bind", f"{overlay}:/opt/edta230:ro",
        "--pwd", "/work",
    ]
    for name, path in patches.items():
        target = PATCH_TARGETS[name]
        args.extend(["--bind", f"{path}:{target}:ro"])
    args.append(str(image))
    return args


def run(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    failed = args.failed.resolve()
    output = args.output.resolve()
    image = args.image.resolve()
    overlay = args.source_overlay.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to replace recovery output: {output}")
    if not image.is_file() or not overlay.is_dir():
        raise FileNotFoundError("pinned EDTA image or source overlay missing")
    prior_status_path = failed / "status.json"
    if not prior_status_path.is_file():
        raise FileNotFoundError(prior_status_path)
    prior_status = json.loads(prior_status_path.read_text(encoding="utf-8"))
    if prior_status.get("status") != "FAILED" or prior_status.get("method") != "EDTA":
        raise ValueError("--failed is not the preserved failed EDTA cell")
    output.mkdir(parents=True)
    budget_seconds = int(args.budget_seconds)
    if budget_seconds <= 0:
        raise ValueError("budget_seconds must be positive")
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
        "resume_mode": "fresh output; copied Module4 Step7 checkpoint; no original tree writes",
        "resumed_from": str(failed),
        "prior_slurm_elapsed_seconds": int(args.prior_slurm_seconds),
        "fixture_job": args.fixture_job,
        "fixture_slurm_elapsed_seconds": int(args.fixture_seconds),
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
        status["copy"] = dict(copied, wall_seconds=time.monotonic() - copy_started)
        write_json(output / "status.json", status)
        patches = extract_patch(image, output)
        status["compatibility_overlay"] = {
            "files": patches,
            "get_fasta_policy": "pandas DataFrame.apply(axis=1) only at nested-Pool sequence extraction; no coordinate cast",
            "check_TIR_TSD_policy": 'family=x["TIR_type"] at two sites',
            "source_checked_and_compiled": True,
        }
        write_json(output / "status.json", status)

        base = native_bindings(output, overlay, image, patches)
        env = ["env", "HOME=/work/home", "TMPDIR=/work/tmp"]
        genome = "/work/galGal6.fa"
        stage_command(
            output=output,
            status=status,
            name="tir_raw_resume",
            started=started,
            budget_seconds=budget_seconds,
            argv=base + env + ["perl", "/opt/edta230/EDTA_raw.pl",
                               "--genome", genome, "--species", "others",
                               "--type", "tir", "--overwrite", "0", "--threads", "16"],
        )
        status["checkpoint_consumption"] = checkpoint_load_evidence(output)
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

        # summarize_native.py is the frozen WHOLE benchmark adapter.  It
        # requires a terminal status while reading the just-materialized
        # top-level files, so mark pre-summary success and fail closed if the
        # summary itself cannot be generated.
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
    parser.add_argument("--prior-slurm-seconds", type=int, default=166862)
    parser.add_argument("--fixture-job", required=True)
    parser.add_argument("--fixture-seconds", type=int, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
