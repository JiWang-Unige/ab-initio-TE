#!/usr/bin/env python3
"""Acquire one official BRAKER image and check native entry points, not accuracy."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
NAME = "TRADITIONAL-GENE-PIPELINE-20260925"
IMAGE_URI = "docker://teambraker/braker3:v3.1.1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing-sandbox", type=Path,
                        help="Reuse the extracted rootfs after a SIF-packaging timeout; no pull")
    args = parser.parse_args()
    job = os.environ["SLURM_JOB_ID"]
    out = ROOT / "outputs" / NAME / ("preflight-" + job)
    out.mkdir(parents=True, exist_ok=False)
    image = args.existing_sandbox or out / "braker3-v3.1.1.sif"
    if args.existing_sandbox and not (image / ".singularity.d").is_dir():
        raise ValueError("existing sandbox lacks the extracted Apptainer metadata")
    env = dict(os.environ)
    env["APPTAINER_CACHEDIR"] = str(out / "cache")
    env["APPTAINER_TMPDIR"] = str(out / "tmp")
    Path(env["APPTAINER_TMPDIR"]).mkdir()
    result = {"protocol": NAME, "job_id": job, "image_uri": IMAGE_URI,
              "status": "RUNNING", "scope": "image and executable readiness only; no training or genome annotation", "checks": []}
    result["artifact_format"] = "extracted_sandbox" if args.existing_sandbox else "sif"
    result["reused_artifact"] = str(image) if args.existing_sandbox else None
    status = out / "status.json"

    def save():
        status.write_text(json.dumps(result, indent=2) + "\n")

    def run(name, argv, timeout):
        started = time.monotonic()
        with (out / (name + ".stdout")).open("w") as stdout, (out / (name + ".stderr")).open("w") as stderr:
            try:
                rc = subprocess.run(argv, env=env, stdout=stdout, stderr=stderr, timeout=timeout).returncode
            except subprocess.TimeoutExpired:
                rc = 124
        result["checks"].append({"name": name, "argv": argv, "returncode": rc,
                                 "wall_seconds": time.monotonic() - started})
        save()
        return rc

    save()
    if not args.existing_sandbox and run("pull", ["apptainer", "pull", str(image), IMAGE_URI], 3000):
        result["status"] = "ACQUISITION_FAILED"
        save()
        raise SystemExit(1)
    prefix = ["apptainer", "exec", "--cleanenv", str(image)]
    checks = [
        ("braker_version", prefix + ["braker.pl", "--version"]),
        ("augustus_version", prefix + ["augustus", "--version"]),
        ("genemark_entry", prefix + ["bash", "-lc", "command -v gmetp.pl || { test -n \"$GENEMARK_PATH\" && test -x \"$GENEMARK_PATH/gmetp.pl\"; }"]),
    ]
    ok = all([run(name, argv, 120) == 0 for name, argv in checks])
    result["status"] = "ENTRYPOINTS_READY" if ok else "ENTRYPOINT_CHECK_FAILED"
    result["image_path"] = str(image)
    if image.is_file():
        result["image_bytes"] = image.stat().st_size
    result["not_verified"] = ["GeneMark training/license execution", "RNA/protein evidence qualification", "mask use in a full workflow", "scientific prediction or accuracy"]
    save()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
