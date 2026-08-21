#!/usr/bin/env python3
"""Fail-closed five-workflow identity/help/minimum-input smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from adapter import convert, synthetic_self_test

TERMINAL_CELL = {"ENGINEERING_PASS", "FOUNDATIONAL_TYPED_BLOCK", "VERSION_MISMATCH", "INVALID_RUN"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def parse_peak_rss(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", path.read_text(errors="replace"))
    return int(match.group(1)) if match else None


def run_command(name: str, command: List[str], log_root: Path, timeout_s: int,
                cwd: Optional[Path] = None) -> Dict[str, Any]:
    stdout_path = log_root / f"{name}.stdout.txt"
    stderr_path = log_root / f"{name}.stderr.txt"
    time_path = log_root / f"{name}.time.txt"
    log_root.mkdir(parents=True, exist_ok=True)
    wrapped = ["/usr/bin/time", "-v", "-o", str(time_path), "timeout", "--signal=TERM", str(timeout_s)] + command
    started = time.monotonic()
    with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
        proc = subprocess.run(wrapped, stdout=out, stderr=err, cwd=str(cwd) if cwd else None, check=False)
    elapsed = time.monotonic() - started
    return {
        "name": name,
        "argv": command,
        "argv_shell_escaped": shlex.join(command),
        "exit_code": proc.returncode,
        "timed_out": proc.returncode == 124,
        "elapsed_seconds": round(elapsed, 6),
        "peak_rss_kb": parse_peak_rss(time_path),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "time_report": str(time_path)
    }


def apptainer(sif: Path, work: Path, shell_command: str) -> List[str]:
    return [
        "apptainer", "exec", "--cleanenv", "--bind", f"{work}:/work", str(sif),
        "env", "HOME=/work/home", "TMPDIR=/work/tmp", "http_proxy=http://127.0.0.1:9",
        "https_proxy=http://127.0.0.1:9", "ftp_proxy=http://127.0.0.1:9",
        "bash", "-lc", shell_command
    ]


def text_for(results: List[Dict[str, Any]]) -> str:
    chunks: List[str] = []
    for result in results:
        for key in ("stdout", "stderr"):
            path = Path(result[key])
            if path.exists():
                chunks.append(path.read_text(errors="replace")[:200000])
    return "\n".join(chunks)


def locate_tetrimmer_source(extracted: Path) -> Path:
    candidates = list(extracted.rglob("tetrimmer/TEtrimmer.py"))
    if len(candidates) != 1:
        raise RuntimeError(f"expected one TEtrimmer.py, found {len(candidates)}")
    return candidates[0].parent


def adapt_outputs(cell_root: Path, ignored_inputs: Optional[List[Path]] = None) -> Dict[str, Any]:
    ignored = {path.resolve() for path in (ignored_inputs or [])}
    candidates: List[Tuple[Path, str]] = []
    for path in cell_root.rglob("*"):
        if not path.is_file() or path.resolve() in ignored or path.name == "canonical_output.tsv":
            continue
        low = path.name.lower()
        if low.endswith((".gff", ".gff3")):
            candidates.append((path, "gff"))
        elif low.endswith((".bed", ".bed6")):
            candidates.append((path, "bed"))
        elif low.endswith(".out") and path.stat().st_size < 100 * 1024 * 1024:
            candidates.append((path, "repeatmasker_out"))
    errors: List[str] = []
    for source, fmt in sorted(candidates, key=lambda item: (item[0].stat().st_size, str(item[0]))):
        target = cell_root / "canonical_output.tsv"
        try:
            rows = convert(source, target, fmt)
            return {"pass": True, "source": str(source), "format": fmt,
                    "output": str(target), "rows": rows, "output_sha256": sha256(target)}
        except Exception as exc:  # retain all adapter diagnostics
            errors.append(f"{source}: {type(exc).__name__}: {exc}")
    return {"pass": False, "source": None, "rows": 0,
            "reason": "no adaptable workflow interval output", "errors": errors}


def workflow_commands(name: str, components: Dict[str, Path], work: Path,
                      tetrimmer_source: Optional[Path]) -> Tuple[List[Tuple[str, List[str]]], List[Tuple[str, List[str]]]]:
    helps: List[Tuple[str, List[str]]] = []
    minimum: List[Tuple[str, List[str]]] = []
    if name == "repeatmodeler2_repeatmasker":
        rm2 = components["repeatmodeler_2_0_9"]
        rmask = components["repeatmasker_4_2_4"]
        helps.extend([
            ("repeatmodeler_version", apptainer(rm2, work, "RepeatModeler -version || RepeatModeler -help")),
            ("repeatmodeler_help", apptainer(rm2, work, "RepeatModeler -help")),
            ("repeatmasker_version", apptainer(rmask, work, "RepeatMasker -version || RepeatMasker --version || RepeatMasker -help")),
            ("repeatmasker_help", apptainer(rmask, work, "RepeatMasker -help"))
        ])
        minimum.extend([
            ("repeatmodeler_minimum", apptainer(rm2, work, "cd /work/cells/repeatmodeler2_repeatmasker/minimum && BuildDatabase -name tinydb genome.fa && RepeatModeler -database tinydb -threads 4")),
            ("repeatmasker_minimum", apptainer(rmask, work, "cd /work/cells/repeatmodeler2_repeatmasker/minimum && RepeatMasker -pa 4 genome.fa"))
        ])
    elif name == "edta":
        sif = components["edta_2_3_0"]
        helps.extend([
            ("edta_version", apptainer(sif, work, "EDTA.pl --version || EDTA.pl | head -n 30")),
            ("edta_help", apptainer(sif, work, "EDTA.pl | head -n 120"))
        ])
        minimum.append(("edta_minimum", apptainer(
            sif, work,
            "cd /work/cells/edta/minimum && EDTA.pl --genome genome.fa --cds genome.cds.fa --exclude genome.exclude.bed --overwrite 1 --sensitive 1 --anno 1 --threads 4"
        )))
    elif name == "earlgrey":
        sif = components["earlgrey_7_3_0"]
        helps.extend([
            ("earlgrey_version", apptainer(sif, work, "earlGrey --version || earlGrey -V || earlGrey 2>&1 | head -n 80")),
            ("earlgrey_help", apptainer(sif, work, "earlGrey 2>&1 | head -n 160"))
        ])
        minimum.append(("earlgrey_minimum", apptainer(
            sif, work,
            "earlGrey -g /work/input/earlgrey_test.fasta -s smoke -o /work/cells/earlgrey/minimum -t 4 -q yes"
        )))
    elif name == "tetrimmer" and tetrimmer_source is not None:
        sif = components["tetrimmer_dependency_runtime_1_7_2"]
        source_in_work = "/work/" + str(tetrimmer_source.relative_to(work))
        helps.extend([
            ("tetrimmer_version", apptainer(sif, work, f"cd {shlex.quote(source_in_work)} && python TEtrimmer.py --version")),
            ("tetrimmer_help", apptainer(sif, work, f"cd {shlex.quote(source_in_work)} && python TEtrimmer.py --help"))
        ])
        minimum.append(("tetrimmer_minimum", apptainer(
            sif, work,
            f"cd {shlex.quote(source_in_work)} && python TEtrimmer.py --input_file /work/input/tetrimmer_test_input.fa --genome_file /work/input/tetrimmer_test_genome.fa --output_dir /work/cells/tetrimmer/minimum --num_threads 4 --classify_all"
        )))
    return helps, minimum


def version_matches(name: str, target: str, output: str) -> bool:
    def exact_numeric(version: str) -> str:
        escaped = re.escape(version)
        return rf"(?<![0-9.]){escaped}(?![0-9.]|[-_.]?(?:alpha|beta|rc|dev|pre)(?![A-Za-z0-9]))"

    patterns = {
        "repeatmodeler2_repeatmasker": [exact_numeric("2.0.9"), exact_numeric("4.2.4")],
        "edta": [exact_numeric("2.3.0")],
        "earlgrey": [exact_numeric("7.3.0")],
        "hite": [exact_numeric("3.3.3")],
        "tetrimmer": [exact_numeric("1.7.4")]
    }
    return all(re.search(pattern, output, re.I) for pattern in patterns[name])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    output = Path(args.output).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project = Path(config["project_root"]).resolve()
    if not os.environ.get("SLURM_JOB_ID"):
        raise SystemExit("research smoke must run inside a Slurm allocation")
    output.mkdir(parents=True, exist_ok=True)
    work = output / "work"
    (work / "input").mkdir(parents=True, exist_ok=True)
    (work / "home").mkdir(parents=True, exist_ok=True)
    (work / "tmp").mkdir(parents=True, exist_ok=True)

    environment = {
        "schema_version": "TEFM-RUNTIME-1.0.0",
        "slurm_job_id": os.environ["SLURM_JOB_ID"],
        "hostname": platform.node(),
        "python": sys.version,
        "platform": platform.platform(),
        "project_root_declared": config["project_root"],
        "project_root_resolved": str(project),
        "config": str(config_path),
        "config_sha256": sha256(config_path),
        "claim_eligible": False
    }
    apptainer_version = subprocess.run(["apptainer", "--version"], text=True, capture_output=True, check=False)
    environment["apptainer_version"] = (apptainer_version.stdout + apptainer_version.stderr).strip()
    write_json(output / "environment.json", environment)

    input_records: List[Dict[str, Any]] = []
    input_map: Dict[str, Path] = {}
    for record in config["inputs"]:
        path = (project / record["path"]).resolve()
        actual = sha256(path) if path.is_file() else None
        ok = path.is_file() and actual == record["sha256"]
        input_records.append({**record, "resolved_path": str(path), "actual_sha256": actual, "pass": ok})
        if not ok:
            raise RuntimeError(f"frozen input mismatch: {record['id']}")
        input_map[record["id"]] = path
    write_json(output / "input_manifest.json", {"inputs": input_records})

    copy_map = {
        "edta_test_genome": "genome.fa", "edta_test_cds": "genome.cds.fa",
        "edta_test_exclude": "genome.exclude.bed", "earlgrey_test_genome": "earlgrey_test.fasta",
        "tetrimmer_test_input": "tetrimmer_test_input.fa", "tetrimmer_test_genome": "tetrimmer_test_genome.fa"
    }
    for input_id, basename in copy_map.items():
        shutil.copy2(input_map[input_id], work / "input" / basename)

    tetrimmer_extract = work / "source" / "tetrimmer_1_7_4"
    tetrimmer_extract.mkdir(parents=True, exist_ok=True)
    with tarfile.open(input_map["tetrimmer_174_source"], "r:gz") as archive:
        members = archive.getmembers()
        if any(member.name.startswith("/") or ".." in Path(member.name).parts for member in members):
            raise RuntimeError("unsafe path in TEtrimmer source archive")
        archive.extractall(tetrimmer_extract)
    tetrimmer_source = locate_tetrimmer_source(tetrimmer_extract)
    source_version_text = (tetrimmer_source / "TEtrimmer.py").read_text(errors="replace")
    source_version_ok = bool(re.search(r'TEtrimmer_version\s*=\s*["\']1\.7\.4["\']', source_version_text))

    adapter_test = synthetic_self_test(output / "adapter_self_test")
    write_json(output / "adapter_self_test.json", adapter_test)

    cells: Dict[str, Any] = {}
    command_manifest: List[Dict[str, Any]] = []
    for name, workflow in config["workflows"].items():
        cell_root = work / "cells" / name
        (cell_root / "minimum").mkdir(parents=True, exist_ok=True)
        ignored_adapter_inputs: List[Path] = []
        if name == "repeatmodeler2_repeatmasker":
            shutil.copy2(work / "input" / "genome.fa", cell_root / "minimum" / "genome.fa")
        if name == "edta":
            for basename in ("genome.fa", "genome.cds.fa", "genome.exclude.bed"):
                shutil.copy2(work / "input" / basename, cell_root / "minimum" / basename)
            ignored_adapter_inputs.append(cell_root / "minimum" / "genome.exclude.bed")
        component_paths: Dict[str, Path] = {}
        component_checks: List[Dict[str, Any]] = []
        for component in workflow.get("components", []):
            path = (project / component["path"]).resolve()
            actual = sha256(path) if path.is_file() else None
            passed = path.is_file() and actual == component["sha256"]
            component_checks.append({**component, "resolved_path": str(path), "actual_sha256": actual, "pass": passed})
            if passed:
                component_paths[component["id"]] = path
        license_path = (project / workflow["license_evidence"]).resolve()
        license_check = {"spdx": workflow["license"], "evidence": str(license_path),
                         "readable": license_path.is_file() and os.access(license_path, os.R_OK),
                         "sha256": sha256(license_path) if license_path.is_file() else None}
        blockers = list(workflow.get("predeclared_blockers", []))
        if not license_check["readable"]:
            blockers.append("license evidence is not readable")
        if len(component_paths) != len(workflow.get("components", [])):
            blockers.append("one or more frozen runtime components are missing or hash-mismatched")
        if name == "hite" and not workflow.get("components"):
            blockers.append("minimum-input launch cannot run without the exact frozen SIF")

        help_results: List[Dict[str, Any]] = []
        min_results: List[Dict[str, Any]] = []
        help_commands, min_commands = workflow_commands(name, component_paths, work, tetrimmer_source)
        if len(component_paths) == len(workflow.get("components", [])) and (name != "hite"):
            for command_name, argv in help_commands:
                result = run_command(command_name, argv, cell_root / "logs", int(config["timeouts_seconds"]["help"]))
                help_results.append(result)
                command_manifest.append(result)
            for command_name, argv in min_commands:
                result = run_command(command_name, argv, cell_root / "logs", int(config["timeouts_seconds"]["minimum_input"]))
                min_results.append(result)
                command_manifest.append(result)

        version_ok = version_matches(name, workflow["target_version"], text_for(help_results)) if help_results else False
        help_ok = bool(help_results) and all(result["exit_code"] in (0, 1) and not result["timed_out"] for result in help_results)
        min_ok = bool(min_results) and all(result["exit_code"] == 0 and not result["timed_out"] for result in min_results)
        if name == "tetrimmer" and not source_version_ok:
            version_ok = False
            blockers.append("exact source overlay does not declare TEtrimmer 1.7.4")
        if not version_ok:
            blockers.append("target version was not confirmed by payload version output")
        if not help_ok:
            blockers.append("offline help/version invocation did not complete acceptably")
        if not min_ok:
            blockers.append("minimum-input launch did not complete with exit code zero")
        adapter = adapt_outputs(cell_root, ignored_adapter_inputs)
        if not adapter["pass"]:
            blockers.append("no actual workflow interval output was converted to canonical schema")

        identity_ok = bool(workflow.get("components")) and all(item["pass"] for item in component_checks)
        if not identity_ok:
            status = "FOUNDATIONAL_TYPED_BLOCK"
        elif not version_ok:
            status = "VERSION_MISMATCH"
        elif blockers:
            status = "FOUNDATIONAL_TYPED_BLOCK"
        elif help_ok and min_ok and adapter["pass"]:
            status = "ENGINEERING_PASS"
        else:
            status = "INVALID_RUN"
        assert status in TERMINAL_CELL
        cells[name] = {
            "status": status,
            "target_version": workflow["target_version"],
            "identity_ok": identity_ok,
            "components": component_checks,
            "license": license_check,
            "database_assets": [item for item in input_records if item["id"].startswith("dfam40")],
            "version_output_ok": version_ok,
            "offline_help_ok": help_ok,
            "minimum_input_ok": min_ok,
            "adapter": adapter,
            "commands": help_results + min_results,
            "blockers": sorted(set(blockers))
        }
        write_json(output / "cells" / name / "result.json", cells[name])

    write_json(output / "command_manifest.json", {"commands": command_manifest})
    write_json(output / "data_leakage_gate.json", {
        "status": "PASS_NOT_APPLICABLE",
        "reason": "identity smoke has no fitted model, split, calibration, or biological test claim",
        "checks": {"test_assets_only": True, "no_output_used_for_selection": True,
                   "coordinate_convention": config["coordinate_convention"], "adapter_self_test": adapter_test["pass"]}
    })
    pass_count = sum(cell["status"] == "ENGINEERING_PASS" for cell in cells.values())
    block_count = sum(cell["status"] == "FOUNDATIONAL_TYPED_BLOCK" for cell in cells.values())
    mismatch_count = sum(cell["status"] == "VERSION_MISMATCH" for cell in cells.values())
    invalid_count = sum(cell["status"] == "INVALID_RUN" for cell in cells.values())
    semantic_success = (len(cells) == 5 and invalid_count == 0 and
                        all(cell["status"] in TERMINAL_CELL for cell in cells.values()))
    metrics = {
        "exp_id": config["exp_id"], "profile": config["profile"],
        "primary_metric": pass_count / 5.0,
        "metrics": {"engineering_pass_cells": pass_count, "typed_block_cells": block_count,
                    "version_mismatch_cells": mismatch_count, "invalid_cells": invalid_count,
                    "matrix_cells": len(cells)},
        "dataset": {"name": "official tiny installation fixtures", "version": "sha256_manifest",
                    "split": "not_applicable_identity_smoke"},
        "evaluator": {"path": str(Path(__file__).resolve()), "version": "TEFM-BENCH-5TOOL-SMOKE-1.0.3"},
        "semantic_success": semantic_success,
        "claim_eligible": False,
        "verdict": ("ENGINEERING_PASS" if pass_count == 5 else
                    ("INVALID_RUN" if invalid_count else
                     ("VERSION_MISMATCH" if mismatch_count else "FOUNDATIONAL_TYPED_BLOCK"))),
        "cells": {name: {"status": cell["status"], "blockers": cell["blockers"]} for name, cell in cells.items()}
    }
    write_json(output / "metrics.json", metrics)
    write_json(output / "summary.json", {"schema_version": "TEFM-BENCH-5TOOL-SUMMARY-1.0.0",
                                          "environment": environment, "metrics": metrics, "cells": cells})
    output_hashes = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in {"output_manifest.sha256", "STATUS"}:
            output_hashes.append(f"{sha256(path)}  {path.relative_to(output)}")
    (output / "output_manifest.sha256").write_text("\n".join(output_hashes) + "\n", encoding="utf-8")
    (output / "STATUS").write_text("COMPLETED\n" if semantic_success else "FAILED\n", encoding="utf-8")
    return 0 if semantic_success else 2


if __name__ == "__main__":
    raise SystemExit(main())
