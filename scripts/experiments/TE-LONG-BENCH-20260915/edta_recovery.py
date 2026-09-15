#!/usr/bin/env python3
"""Resume failed EDTA cells after runtime compatibility fixes."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


PATCH_TARGETS = {
    "run_GRF.py": "/usr/local/share/TIR-Learner3.0/bin/run_GRF.py",
    "get_fasta_sequence.py": "/usr/local/share/TIR-Learner3.0/bin/get_fasta_sequence.py",
    "check_TIR_TSD.py": "/usr/local/share/TIR-Learner3.0/bin/check_TIR_TSD.py",
}

# These are the frozen TIR-Learner 3.0 constants in the EDTA image.  The
# oracle below is deliberately small: it guards the only coordinate transform
# introduced by this recovery before any native work is resumed.
TIRVISH_SPLIT_SEQ_LEN = 5_000_000
TIRVISH_OVERLAP_SEQ_LEN = 50_000


def split_offset(segment_position: str) -> int:
    """Return the source-genome offset used by TIR-Learner's splitter."""
    try:
        index = int(segment_position.split("of", 1)[0])
        return (index - 1) * TIRVISH_SPLIT_SEQ_LEN
    except ValueError:
        index = int(segment_position.split("of", 1)[0][:-2])
        return index * TIRVISH_SPLIT_SEQ_LEN - TIRVISH_OVERLAP_SEQ_LEN // 2


def verify_split_offset_oracle() -> dict[str, int]:
    """Check normal, overlap, and terminal chunk offsets against split semantics."""
    expected = {
        "1of4": 0,
        "1.5of4": 4_975_000,
        "2of4": 5_000_000,
        "2.5of4": 9_975_000,
        "4of4": 15_000_000,
    }
    observed = {position: split_offset(position) for position in expected}
    if observed != expected:
        raise ValueError(f"TIR-Learner split-offset oracle failed: {observed}")
    return observed


def dump(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def patched_source(name: str, source: str) -> str:
    """Apply one source-checked compatibility patch to a TIR-Learner module."""
    if name == "run_GRF.py":
        old = r'id_pattern = r"^(\w+)_split_([\w.]+of\d+):(\d+):(\d+):(\w+):(\w+)$"'
        new = r'id_pattern = r"^(.+?)_split_([\w.]+of\d+):(\d+):(\d+):(\w+):(\w+)$"'
        active_marker = (
            "def get_GRF_result_df_para(fasta_files_path_list, genome_name, flag_debug, "
            "split_seq_len, overlap_seq_len):"
        )
        if source.count(active_marker) != 1:
            raise ValueError("unexpected run_GRF parallel-result function")
        prefix, active = source.split(active_marker, 1)
        if active.count(old) != 1:
            raise ValueError("unexpected run_GRF split-ID pattern")
        return prefix + active_marker + active.replace(old, new, 1)

    if name == "get_fasta_sequence.py":
        marker = "from const import *\n\n"
        helper = r'''from const import *


def _canonicalize_split_seqids(df_in: pd.DataFrame) -> pd.DataFrame:
    """Map TIR-Learner chunk IDs and local coordinates to the source genome."""
    df = df_in.copy()
    seqids = []
    offsets = []
    for raw_seqid in df["seqid"].astype(str):
        if "_split_" not in raw_seqid:
            seqids.append(raw_seqid)
            offsets.append(0)
            continue
        original, segment = raw_seqid.rsplit("_split_", 1)
        position = segment.split("of", 1)[0]
        if position.endswith(".5"):
            index = int(position[:-2])
            offset = index * TIRvish_split_seq_len - TIRvish_overlap_seq_len // 2
        else:
            index = int(position)
            offset = (index - 1) * TIRvish_split_seq_len
        seqids.append(original)
        offsets.append(offset)

    df["seqid"] = seqids
    offset_series = pd.Series(offsets, index=df.index, dtype="int64")
    for column in ("sstart", "send"):
        df[column] = df[column].astype("int64") + offset_series
    return df


'''
        if source.count(marker) != 1:
            raise ValueError("unexpected get_fasta_sequence import marker")
        source = source.replace(marker, helper, 1)
        marker_call = (
            "def get_start_end(genome_file, df_in, flag_verbose, length=200):\n"
            "    df = df_in.copy()\n"
        )
        if source.count(marker_call) != 1:
            raise ValueError("unexpected get_fasta_sequence coordinate-normalization marker")
        return source.replace(
            marker_call,
            "def get_start_end(genome_file, df_in, flag_verbose, length=200):\n"
            "    df = _canonicalize_split_seqids(df_in)\n",
            1,
        )

    if name == "check_TIR_TSD.py":
        if source.count("family = x[0]") != 2:
            raise ValueError("unexpected pandas positional-family access")
        return source.replace("family = x[0]", 'family = x["TIR_type"]')

    raise ValueError(f"unsupported patch target: {name}")


def extract_and_patch(image: Path, patch_dir: Path) -> list[str]:
    """Extract only the three modules overlaid into the container."""
    # A retry may resume from a prior recovery directory that already carries
    # this overlay.  The source is copied into a new output before this call,
    # so replacing the files here never mutates the preserved failed cell.
    patch_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, target in PATCH_TARGETS.items():
        source = subprocess.check_output(
            ["apptainer", "exec", "--cleanenv", str(image), "cat", target],
            text=True,
        )
        patched = patched_source(name, source)
        # Catch a malformed overlay before EDTA imports it inside the image.
        compile(patched, name, "exec")
        path = patch_dir / name
        path.write_text(patched)
        path.chmod(0o644)
        written.append(name)
    return written


def input_lengths(path: Path) -> dict[str, int]:
    lengths: dict[str, int] = {}
    current = None
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                current = line[1:].split()[0]
                if current in lengths:
                    raise ValueError(f"duplicate input seqid: {current}")
                lengths[current] = 0
            else:
                sequence = line.strip()
                if current is None or set(sequence) - set("ACGTN"):
                    raise ValueError("recovery input must be uppercase ACGTN")
                lengths[current] += len(sequence)
    return lengths


def run(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    cfg = json.loads((root / "configs/TE-LONG-BENCH-20260915.json").read_text())
    dataset = cfg["datasets"][args.dataset]
    failed = args.failed.resolve()
    prior_path = failed / "status.json"
    if not prior_path.is_file():
        raise FileNotFoundError(prior_path)
    prior = json.loads(prior_path.read_text())
    if prior.get("status") != "FAILED" or prior.get("method") != "edta":
        raise ValueError("--failed must be the preserved FAILED EDTA cell")
    if prior.get("dataset") != args.dataset or prior.get("input") != dataset["input"]:
        raise ValueError("failed cell does not match the selected frozen dataset")

    prior_seconds = float(prior.get("wall_seconds", 0.0))
    if cfg["native_timeout_seconds"] - prior_seconds <= 0:
        raise TimeoutError("the unchanged EDTA cell budget is already exhausted")
    prior_steps = list(prior.get("prior_steps", []))
    prior_steps.extend(prior.get("steps", []))

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    work = out / "work"
    status = {
        "protocol": cfg["protocol"],
        "dataset": args.dataset,
        "method": "edta",
        "status": "RUNNING",
        "cpus": cfg["cpus"],
        "memory_gb": cfg["memory_gb"],
        "job": os.getenv("SLURM_JOB_ID"),
        "hostname": os.uname().nodename,
        "input": dataset["input"],
        "scope": dataset["scope"],
        "steps": [],
        "knowledge_condition": cfg["method_information"],
        "resumed_from": str(failed),
        "prior_wall_seconds": prior_seconds,
        "prior_steps": prior_steps,
        "timing_scope": "preserved failed EDTA attempt plus copy and resume; unchanged total native budget",
        "resume_mode": "EDTA --overwrite 0 reusing complete stages; compatibility patch only",
    }
    dump(out / "status.json", status)

    def command(name: str, argv: list[str]) -> None:
        left = int(cfg["native_timeout_seconds"] - prior_seconds - (time.monotonic() - started))
        if left <= 0:
            raise TimeoutError("cell budget exhausted before EDTA resume")
        before = time.monotonic()
        with (out / f"{name}.stdout").open("w") as stdout, (out / f"{name}.stderr").open("w") as stderr:
            result = subprocess.run(
                ["timeout", "--kill-after=30s", str(left), "/usr/bin/time", "-v",
                 "-o", str(out / f"{name}.time"), *map(str, argv)],
                cwd=work,
                stdout=stdout,
                stderr=stderr,
            )
        time_file = out / f"{name}.time"
        rss = re.search(
            r"Maximum resident set size \(kbytes\):\s*(\d+)",
            time_file.read_text() if time_file.exists() else "",
        )
        status["steps"].append({
            "name": name,
            "argv": list(map(str, argv)),
            "exit_code": result.returncode,
            "seconds": time.monotonic() - before,
            "peak_rss_kb": int(rss.group(1)) if rss else None,
        })
        dump(out / "status.json", status)
        if result.returncode in (124, 137):
            raise TimeoutError(f"{name}: timeout")
        if result.returncode:
            raise RuntimeError(f"{name}: exit {result.returncode}")

    try:
        shutil.copytree(failed / "work", work, symlinks=True)
        lengths = input_lengths(work / "panel.fa")
        if sum(lengths.values()) < 100_000_000:
            raise ValueError("recovery input is shorter than the frozen 100 Mb minimum")
        status["input_bp"] = sum(lengths.values())
        status["sequence_count"] = len(lengths)
        dump(out / "sequence_lengths.json", lengths)
        status["split_offset_oracle"] = verify_split_offset_oracle()

        image = root / cfg["runtimes"]["edta"]
        patch_dir = work / "edta_compat" / "TIR-Learner3.0" / "bin"
        patched = extract_and_patch(image, patch_dir)
        status["patched_modules"] = patched
        status["compatibility_fixes"] = {
            "run_GRF.py": "accept dotted accession IDs before _split_ chunk suffix",
            "get_fasta_sequence.py": "map chunk-local GRF coordinates back to original sequence IDs",
            "check_TIR_TSD.py": "replace pandas positional Series access with TIR_type column",
        }
        dump(out / "status.json", status)

        runtime_source = root / cfg["runtimes"]["edta_source"]
        binds = [f"{work}:/work", f"{runtime_source}:/opt/edta230:ro"]
        for name, target in PATCH_TARGETS.items():
            binds.append(f"{patch_dir / name}:{target}:ro")
        prior_edta = next(
            (step for step in prior.get("steps", []) if step.get("name") == "edta"),
            {},
        )
        prior_env = [
            item for item in prior_edta.get("argv", [])
            if isinstance(item, str) and item.startswith("FAMDB_DIR=")
        ]
        argv = ["apptainer", "exec", "--cleanenv"]
        for bind in binds:
            argv.extend(["--bind", bind])
        argv.extend([
            str(image), "env", "HOME=/work/home", "TMPDIR=/work/tmp",
            *prior_env, f"OMP_NUM_THREADS={cfg['cpus']}",
            "perl", "/opt/edta230/EDTA.pl",
            "--genome", "/work/panel.fa", "--overwrite", "0", "--sensitive", "1",
            "--anno", "1", "--threads", str(cfg["cpus"]),
        ])
        command("edta_resume", argv)

        raw = work / "panel.fa.mod.EDTA.TEanno.gff3"
        if not raw.is_file() or not raw.stat().st_size:
            raise RuntimeError(f"final EDTA output absent or empty: {raw}")
        adapter_path = root / "scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py"
        spec = importlib.util.spec_from_file_location("edta_recovery_adapter", adapter_path)
        if spec is None or spec.loader is None:
            raise ImportError(adapter_path)
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        status["prediction_rows"] = adapter.convert(raw, out / "predictions.tsv", "gff3")
        for seqid, start, end in adapter.read_canonical(out / "predictions.tsv"):
            if seqid not in lengths or end > lengths[seqid]:
                raise ValueError("EDTA coordinates differ from common input")
        status.update(status="COMPLETED", native_output=str(raw), native_format="gff3")
    except TimeoutError as exc:
        status.update(status="TIMEOUT", failure_reason=str(exc))
    except Exception as exc:
        status.update(status="FAILED", failure_reason=str(exc))
    finally:
        status["attempt_wall_seconds"] = time.monotonic() - started
        status["wall_seconds"] = prior_seconds + status["attempt_wall_seconds"]
        dump(out / "status.json", status)
    if status["status"] != "COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--dataset", choices=["sim100", "c_briggsae"], required=True)
    parser.add_argument("--failed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
