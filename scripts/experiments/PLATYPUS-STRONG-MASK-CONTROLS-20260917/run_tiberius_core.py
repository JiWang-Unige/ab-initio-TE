#!/usr/bin/env python3
"""Run one fixed strong mask through the native Tiberius softmask receiver."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT / "outputs/P3-TIBERIUS-EXTERNAL-20260915/prepared/platypus"
MASK_ROOT = ROOT / "outputs/PLATYPUS-STRONG-MASK-CONTROLS-20260917/mask"
BASE = ROOT / "outputs/PLATYPUS-STRONG-MASK-CONTROLS-20260917/tiberius-r2"


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def write_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    tmp.replace(path)


def fasta_sequence(path: Path) -> tuple[str, str]:
    name = None
    chunks: list[str] = []
    with path.open(encoding="ascii") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    raise ValueError("expected one FASTA record")
                name = line[1:]
            else:
                chunks.append(line)
    if name is None:
        raise ValueError(f"empty FASTA: {path}")
    return name, "".join(chunks)


def run(index: int, method: str) -> None:
    geometry = json.loads((PREP / "geometry.json").read_text())
    if len(geometry) != 20:
        raise ValueError("fixed geometry changed")
    core = geometry[index]
    mask_cell = MASK_ROOT / method / core["id"]
    mask_status = json.loads((mask_cell / "status.json").read_text())
    if mask_status.get("status") != "MASK_COMPLETED":
        raise ValueError(f"mask cell is not complete: {mask_cell}")
    mask_manifest = json.loads((mask_cell / "manifest.json").read_text())
    fasta = mask_cell / mask_manifest["mask_fasta"]
    record, sequence = fasta_sequence(fasta)
    if record != core["record_id"]:
        raise ValueError("mask FASTA record does not match fixed core")
    original = (PREP / core["id"] / "sequence.txt").read_text(encoding="ascii").strip()
    if len(sequence) != len(original) or sequence.upper() != original:
        raise ValueError("mask changed the fixed sequence letters")
    observed_masked = sum(base in "acgt" for base in sequence)
    if observed_masked <= 0:
        raise ValueError("strong mask contains no lowercase callable bases")
    out = BASE / method / core["id"]
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        status_path = out / "status.json"
        if status_path.exists() and json.loads(status_path.read_text()).get("status") == "COMPLETED":
            print(json.dumps({"status": "REUSED", "method": method, "core": core["id"]}))
            return
        raise FileExistsError(f"existing partial receiver cell is preserved: {out}")
    out.mkdir()
    status = {"status": "RUNNING", "method": method, "core": core,
              "slurm_job_id": os.getenv("SLURM_JOB_ID"), "steps": []}
    write_json(out / "status.json", status)
    started = time.monotonic()
    b = module(ROOT / "scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py", "strong_mask_base")
    c = b.Core(**{key: core[key] for key in ("chrom", "index", "start", "end", "halo_start", "halo_end")})
    input_manifest = {"core": core, "method": method, "mask_manifest": str((mask_cell / "manifest.json").relative_to(ROOT)),
                      "same_uppercase_letters": True, "observed_masked_acgt_bp": observed_masked,
                      "fasta": str(fasta.relative_to(ROOT))}
    write_json(out / "input.json", input_manifest)
    source = ROOT / "refs/repos/Tiberius-gap-c-r1"
    image = ROOT / "software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1/tiberius_2.0.7.sif"
    if not source.exists() or not image.exists():
        raise FileNotFoundError("frozen Tiberius source or image is missing")
    guest = "/work/te/" + str(fasta.relative_to(ROOT))
    cell_guest = "/work/te/" + str(out.relative_to(ROOT))
    cmd = ["singularity", "exec", "--nv", "--cleanenv",
           "--env", f"CUDA_VISIBLE_DEVICES={os.environ['CUDA_VISIBLE_DEVICES']}",
           "--env", f"TIB_OBSERVATION={cell_guest}/{method}.observation.json",
           "--env", "TIB_EXPECTED_CHANNELS=6",
           "--bind", f"{ROOT}:/work/te", "--bind", f"{source}:/opt/Tiberius", "--pwd", "/work/te", str(image),
           "/usr/bin/python3", "/work/te/scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/observed_tiberius.py",
           "--genome", guest, "--model_cfg", "/opt/Tiberius/model_cfg/mammalia_softmasking_v2.yaml",
           "--seq_len", "400050", "--batch_size", "1", "--out", f"{cell_guest}/{method}.gtf", f"{cell_guest}/{method}.gff3"]
    tick = time.monotonic()
    with (out / f"{method}.stdout").open("w") as stdout, (out / f"{method}.stderr").open("w") as stderr:
        done = subprocess.run(cmd, stdout=stdout, stderr=stderr)
    status["steps"].append({"mode": method, "argv": cmd, "exit_code": done.returncode, "seconds": time.monotonic() - tick})
    write_json(out / "status.json", status)
    if done.returncode:
        status.update({"status": "FAILED", "error": f"Tiberius exit {done.returncode}"})
        write_json(out / "status.json", status)
        raise RuntimeError(f"Tiberius failed: {method}/{core['id']}")
    obs = json.loads((out / f"{method}.observation.json").read_text())
    if not obs.get("passed") or obs.get("expected_channels") != 6 or obs.get("model_calls", 0) < 1:
        raise ValueError("native six-channel observer failed")
    gtf, gtf_counts = b.parse_predictions(out / f"{method}.gtf", c, "gtf")
    gff, gff_counts = b.parse_predictions(out / f"{method}.gff3", c, "gff3")
    if gtf != gff or gtf_counts != gff_counts:
        raise ValueError("native GTF/GFF3 annotations disagree")
    status.update({"status": "COMPLETED", "wall_seconds": time.monotonic() - started,
                   "observed_masked_acgt_bp": observed_masked})
    write_json(out / "status.json", status)
    print(json.dumps({"status": "COMPLETED", "method": method, "core": core["id"], "seconds": status["wall_seconds"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=["RED", "RM2"])
    parser.add_argument("index", type=int, choices=range(20))
    args = parser.parse_args()
    run(args.index, args.method)
