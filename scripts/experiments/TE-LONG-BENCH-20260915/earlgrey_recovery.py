#!/usr/bin/env python3
"""Repair completed EarlGrey cells whose resumed final RM lost ``-l``."""

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


SPECIES = "longbench"
FINAL_DIRS = (
    f"{SPECIES}_Curated_Library",
    f"{SPECIES}_RepeatMasker_Against_Custom_Library",
    f"{SPECIES}_mergedRepeats",
    f"{SPECIES}_RepeatLandscape",
    f"{SPECIES}_summaryFiles",
)
FINAL_STAMPS = ("novoMask.sha256", "mergeRep.sha256", "heliano.sha256")


def dump(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_native_patch(root: Path):
    path = root / "scripts/experiments/TE-LONG-BENCH-20260915/native.py"
    spec = importlib.util.spec_from_file_location("long_native", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.portable_earlgrey


def input_lengths(path: Path) -> dict[str, int]:
    lengths: dict[str, int] = {}
    current: str | None = None
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


def record_count(path: Path) -> int:
    with path.open() as handle:
        return sum(line.startswith(">") for line in handle)


def run(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    cfg = json.loads((root / "configs/TE-LONG-BENCH-20260915.json").read_text())
    dataset = cfg["datasets"][args.dataset]
    completed = args.completed.resolve()
    source_status_path = completed / "status.json"
    if not source_status_path.is_file():
        raise FileNotFoundError(source_status_path)
    prior = json.loads(source_status_path.read_text())
    if prior.get("status") != "COMPLETED" or prior.get("method") != "earlgrey":
        raise ValueError("--completed must be the preserved COMPLETED EarlGrey cell")
    if prior.get("dataset") != args.dataset or prior.get("input") != dataset["input"]:
        raise ValueError("completed cell does not match the selected frozen dataset")
    if not (completed / "work").is_dir():
        raise FileNotFoundError(completed / "work")

    out = args.output.resolve()
    if out == completed:
        raise ValueError("recovery output must be separate from the preserved completed cell")
    out.mkdir(parents=True, exist_ok=False)
    work = out / "work"
    started = time.monotonic()
    prior_seconds = float(prior.get("wall_seconds", 0.0))
    if cfg["native_timeout_seconds"] - prior_seconds <= 0:
        raise TimeoutError("the unchanged EarlGrey cell budget is already exhausted")

    status = {
        "protocol": cfg["protocol"],
        "dataset": args.dataset,
        "method": "earlgrey",
        "status": "RUNNING",
        "cpus": cfg["cpus"],
        "memory_gb": cfg["memory_gb"],
        "job": os.getenv("SLURM_JOB_ID"),
        "array_task": os.getenv("SLURM_ARRAY_TASK_ID"),
        "hostname": os.uname().nodename,
        "input": dataset["input"],
        "scope": dataset["scope"],
        "steps": [],
        "knowledge_condition": cfg["method_information"],
        "resumed_from": str(completed),
        "prior_wall_seconds": prior_seconds,
        "prior_status": prior.get("status"),
        "prior_steps": list(prior.get("prior_steps", [])) + list(prior.get("steps", [])),
        "timing_scope": "preserved completed cell plus copy and final-stage protocol repair; original native budget retained",
        "recovery_mode": "reuse initial mask, RepeatModeler and TEstrainer; rebuild final RM, merge, landscape and summary",
    }
    dump(out / "status.json", status)

    def command(name: str, argv: list[str]) -> None:
        remaining = int(cfg["native_timeout_seconds"] - prior_seconds - (time.monotonic() - started))
        if remaining <= 0:
            raise TimeoutError("cell budget exhausted before EarlGrey recovery")
        before = time.monotonic()
        with (out / f"{name}.stdout").open("w") as stdout, (out / f"{name}.stderr").open("w") as stderr:
            result = subprocess.run(
                ["timeout", "--kill-after=30s", str(remaining), "/usr/bin/time", "-v",
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

    def container(argv: list[str], bind_compat: bool) -> list[str]:
        runtime = {key: root / value for key, value in cfg["runtimes"].items()}
        cmd = ["apptainer", "exec", "--cleanenv", "--bind", f"{work}:/work",
               "--bind", f"{runtime['famdb4']}:/usr/local/share/famdb-3.0.0/Libraries/famdb:ro",
               "--bind", f"{runtime['famdb4']}:/usr/local/share/RepeatMasker/Libraries/famdb:ro"]
        if bind_compat:
            cmd += [
                "--bind", f"{work / 'earlGrey.compat.sh'}:/usr/local/bin/earlGrey:ro",
                "--bind", f"{work / 'LTR_FINDER_parallel.compat'}:/usr/local/share/earlgrey-7.3.0-1/scripts/LTR_FINDER_parallel:ro",
            ]
        return cmd + [
            str(runtime["earlgrey"]), "env", "HOME=/work/home", "TMPDIR=/work/tmp",
            "PERL5LIB=/usr/local/share/RepeatMasker",
            "FAMDB_DIR=/usr/local/share/famdb-3.0.0/Libraries/famdb",
            f"OMP_NUM_THREADS={cfg['cpus']}", *argv,
        ]

    try:
        # The copy is made inside the Slurm allocation.  The source cell is
        # never modified, including its native output and status JSON.
        shutil.copytree(completed / "work", work, symlinks=True)
        lengths = input_lengths(work / "panel.fa")
        if sum(lengths.values()) < 100_000_000:
            raise ValueError("recovery input is shorter than the frozen 100 Mb minimum")
        status["input_bp"] = sum(lengths.values())
        status["sequence_count"] = len(lengths)
        dump(out / "sequence_lengths.json", lengths)

        eg = work / "eg" / "longbench_EarlGrey"
        reusable = {
            "initial_mask": eg / f"{SPECIES}_RepeatMasker" / "panel.fa.prep.masked",
            "database": eg / f"{SPECIES}_Database" / f"{SPECIES}-families.fa",
            "strained": eg / f"{SPECIES}_strainer" / f"{SPECIES}-families.fa.strained",
            "lineage": work / "lineage.fa",
            "ltr_compat": work / "LTR_FINDER_parallel.compat",
        }
        missing = [name for name, path in reusable.items() if not path.is_file() or not path.stat().st_size]
        if missing:
            raise ValueError(f"required reusable EarlGrey artifacts missing: {missing}")

        removed = []
        for name in FINAL_DIRS:
            path = eg / name
            if path.exists():
                shutil.rmtree(path)
                removed.append(str(path.relative_to(work)))
        stamps = eg / ".earlGrey_stamps"
        for name in FINAL_STAMPS:
            path = stamps / name
            if path.exists():
                path.unlink()
                removed.append(str(path.relative_to(work)))
        status["removed_final_cache"] = removed
        status["reused_artifacts"] = {
            name: str(path.relative_to(work)) for name, path in reusable.items()
        }
        dump(out / "status.json", status)

        portable_earlgrey = load_native_patch(root)
        source = subprocess.check_output(
            container(["cat", "/usr/local/bin/earlGrey"], False), text=True
        )
        patched = portable_earlgrey(source)
        subprocess.run(["bash", "-n"], input=patched, text=True, check=True)
        (work / "earlGrey.compat.sh").write_text(patched)
        (work / "earlGrey.compat.sh").chmod(0o755)
        status["compatibility_fix"] = "restore RepSub from -l before final RM on resumed work tree; preserve existing runtime patches"
        dump(out / "status.json", status)

        command("earlgrey_repair", container([
            "earlGrey", "-g", "/work/panel.fa", "-s", SPECIES, "-o", "/work/eg",
            "-t", str(cfg["cpus"]), "-q", "yes", "-l", "/work/lineage.fa",
        ], True))

        combined = eg / f"{SPECIES}_Curated_Library" / f"{SPECIES}_combined_library.fasta"
        strained = reusable["strained"]
        lineage = reusable["lineage"]
        expected = strained.read_bytes() + lineage.read_bytes()
        actual = combined.read_bytes() if combined.is_file() else b""
        if actual != expected:
            raise RuntimeError("final combined library is not strained-library plus lineage.fa")
        status["final_library"] = {
            "path": str(combined.relative_to(work)),
            "combined_bytes": len(actual),
            "strained_bytes": strained.stat().st_size,
            "lineage_bytes": lineage.stat().st_size,
            "combined_records": record_count(combined),
            "strained_records": record_count(strained),
            "lineage_records": record_count(lineage),
            "exact_concatenation": True,
        }
        dump(out / "status.json", status)

        raw = eg / f"{SPECIES}_summaryFiles" / f"{SPECIES}.filteredRepeats.gff"
        if not raw.is_file() or not raw.stat().st_size:
            raise RuntimeError(f"repaired EarlGrey final output absent or empty: {raw}")
        adapter_path = root / "scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py"
        spec = importlib.util.spec_from_file_location("earlgrey_recovery_adapter", adapter_path)
        if spec is None or spec.loader is None:
            raise ImportError(adapter_path)
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        status["prediction_rows"] = adapter.convert(raw, out / "predictions.tsv", "gff3")
        for seqid, start, end in adapter.read_canonical(out / "predictions.tsv"):
            if seqid not in lengths or end > lengths[seqid]:
                raise ValueError("repaired EarlGrey coordinates differ from common input")
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
    parser.add_argument("--completed", type=Path, required=True,
                        help="preserved COMPLETED EarlGrey cell with a resumed final-library protocol issue")
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
