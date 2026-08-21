#!/usr/bin/env python3
"""Prepare an immutable queryable Dfam 4.0 FamDB from frozen candidates."""
from __future__ import annotations

import argparse, gzip, hashlib, json, os, shutil, tempfile
from pathlib import Path
from typing import Any

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def unpack(source: Path, destination: Path) -> str:
    with gzip.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    with destination.open("rb") as handle:
        if handle.read(8) != b"\x89HDF\r\n\x1a\n":
            raise RuntimeError(f"{destination.name} is not an HDF5 FamDB partition")
    return digest(destination)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--asset-root", required=True)
    args = p.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise SystemExit("FamDB decompression/preparation requires the dedicated CPU Slurm preparation job")
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve()
    target = Path(args.asset_root).resolve() / config["dfam40"]["asset_subdir"]
    records = []
    for name, output_name in (("full", "dfam40.0.h5"), ("curated_consensus", "dfam40.curated.consensus.0.h5")):
        entry = config["dfam40"][name]; source = (root / entry["path"]).resolve()
        actual = digest(source) if source.is_file() else None
        if actual != entry["sha256"]: raise SystemExit(f"frozen Dfam candidate mismatch: {name}")
        records.append({"id": name, "source": str(source), "source_sha256": actual, "output": output_name})
    # Deliberately exclude the whole experiment-config digest: unrelated HiTE/EDTA
    # repair edits must not invalidate byte-identical frozen Dfam assets.
    requested = {"schema_version": "TEFM-FAMDB-ASSET-2.0.0", "required_database": config["dfam40"]["required_database"], "inputs": records}
    manifest = target / "manifest.json"
    if target.exists():
        if not manifest.is_file(): raise SystemExit(f"refusing unmanifested existing asset: {target}")
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        existing_inputs = [{k: row[k] for k in ("id", "source", "source_sha256", "output")} for row in existing.get("inputs", [])]
        declared = {x.get("name"): x.get("sha256") for x in existing.get("outputs", [])}
        expected_outputs = {"dfam40.0.h5", "dfam40.curated.consensus.0.h5"}
        payload_ok = len(existing.get("outputs", [])) == 2 and set(declared) == expected_outputs and all((target / name).is_file() and digest(target / name) == declared.get(name) for name in expected_outputs)
        wrapper_ok = (target / "famdb.py").is_file() and existing.get("famdb_wrapper_sha256") == digest(target / "famdb.py")
        marker_ok = (target / ".earlgrey.config.complete").is_file()
        schema_ok = existing.get("schema_version") == "TEFM-FAMDB-ASSET-2.0.0"
        environment_path = Path(existing.get("environment_path", ""))
        provenance_ok = all((
            bool(existing.get("preparation_slurm_job_id")),
            existing.get("preparation_code_sha256") == digest(Path(__file__).resolve()),
            existing.get("config_sha256") == digest(config_path),
            environment_path.is_file(),
            existing.get("environment_sha256") == (digest(environment_path) if environment_path.is_file() else None),
        ))
        if not schema_ok or existing.get("required_database") != requested["required_database"] or existing_inputs != records or not provenance_ok or not(payload_ok and wrapper_ok and marker_ok):
            raise SystemExit(f"existing FamDB differs; no overwrite: {target}")
        print(json.dumps({"status": "ALREADY_PREPARED", "asset": str(target)}, sort_keys=True)); return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="famdb.prepare.", dir=str(target.parent)))
    try:
        for record in records: record["output_sha256"] = unpack(Path(record["source"]), staging / record["output"])
        wrapper = staging / "famdb.py"
        wrapper.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexec /usr/local/share/famdb-3.0.0/famdb.py -i \"$(cd \"$(dirname \"$0\")\" && pwd)\" \"$@\"\n", encoding="utf-8")
        wrapper.chmod(0o755); (staging / ".earlgrey.config.complete").touch()
        requested["outputs"] = [{"name": r["output"], "sha256": r["output_sha256"]} for r in records]
        requested["famdb_wrapper_sha256"] = digest(wrapper)
        requested["preparation_slurm_job_id"] = os.environ["SLURM_JOB_ID"]
        requested["preparation_code_sha256"] = digest(Path(__file__).resolve())
        requested["config_sha256"] = digest(config_path)
        requested["environment_sha256"] = os.environ.get("TEFM_PREP_ENV_SHA256")
        requested["environment_path"] = os.environ.get("TEFM_PREP_ENV_FILE")
        if not requested["environment_sha256"] or not requested["environment_path"]:
            raise SystemExit("preparation sbatch must export TEFM_PREP_ENV_SHA256 and TEFM_PREP_ENV_FILE")
        write_json(staging / "manifest.json", requested); os.replace(staging, target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True); raise
    print(json.dumps({"status": "PREPARED", "asset": str(target), "manifest": str(target / "manifest.json")}, sort_keys=True))
    return 0

if __name__ == "__main__": raise SystemExit(main())
