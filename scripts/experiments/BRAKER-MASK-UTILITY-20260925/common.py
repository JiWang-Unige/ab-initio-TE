"""Shared small helpers for the fixed two-species BRAKER application experiment."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
NAME = "BRAKER-MASK-UTILITY-20260925"
OUT = ROOT / "outputs" / NAME
IMAGE = ROOT / "outputs/TRADITIONAL-GENE-PIPELINE-20260925/preflight-13193436/tmp/build-temp-1854282490/rootfs"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fasta(path):
    name, parts = None, []
    with Path(path).open() as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(parts)
                name, parts = line[1:].split()[0], []
            else:
                parts.append(line.strip())
    if name is not None:
        yield name, "".join(parts)


def write_record(handle, name, sequence):
    handle.write(">" + name + "\n")
    for start in range(0, len(sequence), 80):
        handle.write(sequence[start:start + 80] + "\n")


def native(argv, out, stem):
    started = time.time()
    result = {"argv": argv, "started_epoch": started}
    dump(out / (stem + ".command.json"), result)
    with (out / (stem + ".stdout")).open("w") as stdout, (out / (stem + ".stderr")).open("w") as stderr:
        result["returncode"] = subprocess.run(
            ["/usr/bin/time", "-v", "-o", str(out / (stem + ".time"))] + argv,
            cwd=out, stdout=stdout, stderr=stderr).returncode
    result["wall_seconds"] = time.time() - started
    dump(out / (stem + ".command.json"), result)
    if result["returncode"]:
        raise RuntimeError(f"native {stem} failed: {result['returncode']}")
    return result


def container(out):
    return ["apptainer", "exec", "--cleanenv", "--bind", f"{ROOT}:{ROOT}",
            "--bind", f"{out}:/work", "--pwd", "/work", str(IMAGE)]


def state(stage, species=None):
    return {"protocol": NAME, "stage": stage, "species": species,
            "job_id": os.environ.get("SLURM_JOB_ID"), "started_epoch": time.time(),
            "status": "RUNNING"}
