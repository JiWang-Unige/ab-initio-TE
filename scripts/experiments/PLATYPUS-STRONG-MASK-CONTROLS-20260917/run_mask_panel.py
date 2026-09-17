#!/usr/bin/env python3
"""Run one pooled native strong-mask panel on Baobab CPU.

The pooled panel contains the twenty fixed core+halo sequences as independent
FASTA records. A single de novo library is shared by all downstream cores
without inventing sequence across contig boundaries.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT / "outputs/P3-TIBERIUS-EXTERNAL-20260915/prepared/platypus"
BASE = ROOT / "outputs/PLATYPUS-STRONG-MASK-CONTROLS-20260917"
RM2_IMAGE = ROOT / "container_candidates/E1B-OCI-ACQUIRE-20260809A/repeatmodeler_2_0_9.sif"
RM_IMAGE = ROOT / "container_candidates/E1B-OCI-ACQUIRE-20260809A/repeatmasker_4_2_4.sif"
RED = ROOT / "refs/repos/Red/bin/Red"


def write_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    tmp.replace(path)


def fasta_records(path: Path):
    name = None
    chunks: list[str] = []
    with path.open(encoding="ascii") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks)
                name, chunks = line[1:].strip(), []
            else:
                chunks.append(line)
    if name is not None:
        yield name, "".join(chunks)


def write_fasta(path: Path, name: str, sequence: str) -> None:
    with path.open("w", encoding="ascii") as handle:
        handle.write(f">{name}\n")
        for pos in range(0, len(sequence), 80):
            handle.write(sequence[pos:pos + 80] + "\n")


def write_panel(path: Path, geometry: list[dict], sequences: dict[str, str]) -> None:
    with path.open("w", encoding="ascii") as handle:
        for core in geometry:
            name = core["record_id"]
            handle.write(f">{name}\n")
            sequence = sequences[name]
            for pos in range(0, len(sequence), 80):
                handle.write(sequence[pos:pos + 80] + "\n")


def run_command(cmd: list[str], cwd: Path, stem: str) -> dict:
    started = time.monotonic()
    with (cwd / f"{stem}.stdout").open("w", encoding="utf-8") as stdout, (cwd / f"{stem}.stderr").open("w", encoding="utf-8") as stderr:
        result = subprocess.run(cmd, cwd=cwd, stdout=stdout, stderr=stderr)
    entry = {"argv": cmd, "exit_code": result.returncode, "seconds": time.monotonic() - started}
    write_json(cwd / f"{stem}.json", entry)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {stem}")
    return entry


def fixed_panel() -> tuple[list[dict], dict[str, str]]:
    geometry = json.loads((PREP / "geometry.json").read_text())
    if len(geometry) != 20:
        raise ValueError("fixed geometry is not twenty cores")
    sequences = {}
    for core in geometry:
        sequence = (PREP / core["id"] / "sequence.txt").read_text(encoding="ascii").strip()
        if len(sequence) != core["halo_end"] - core["halo_start"] or len(sequence) != 5_200_000:
            raise ValueError(f"unexpected fixed sequence length for {core['id']}")
        if sequence != sequence.upper() or any(base not in "ACGTN" for base in sequence):
            raise ValueError(f"fixed sequence contains unexpected characters for {core['id']}")
        sequences[core["record_id"]] = sequence
    return geometry, sequences


def parse_masked_panel(path: Path, original: dict[str, str]) -> dict[str, str]:
    records = dict(fasta_records(path))
    if set(records) != set(original):
        raise ValueError(f"masked output records differ from fixed pooled panel: {path}")
    for name, sequence in records.items():
        if len(sequence) != len(original[name]) or sequence.upper() != original[name]:
            raise ValueError(f"masked output changed sequence letters or length: {path}/{name}")
    return records


def rm2_summary(cell: Path, names: set[str]) -> dict:
    candidates = sorted(cell.rglob("*.out"))
    by_record = {name: {"repeat_rows": 0, "unknown_rows": 0, "classified_rows": 0,
                        "class_counts": {}, "intervals": []} for name in names}
    for path in candidates:
        if path.name.endswith(".stdout") or path.name.endswith(".stderr"):
            continue
        for line in path.read_text(errors="replace").splitlines():
            if not line.strip() or line.startswith("SW") or line.startswith("score") or line.startswith("position"):
                continue
            fields = line.split()
            if len(fields) < 15 or not fields[0].lstrip("+-").isdigit():
                continue
            record = fields[4]
            if record not in by_record:
                continue
            try:
                begin, end = int(fields[5]), int(fields[6])
            except (ValueError, IndexError):
                continue
            if end <= begin:
                continue
            label = fields[9] if len(fields) > 9 else "Unknown"
            entry = by_record[record]
            entry["repeat_rows"] += 1
            unknown = label in {"Unknown", "?", "-"} or label.startswith("Unknown/")
            entry["unknown_rows"] += int(unknown)
            entry["classified_rows"] += int(not unknown)
            entry["class_counts"][label] = entry["class_counts"].get(label, 0) + 1
            entry["intervals"].append((begin - 1, end))
    total_rows = total_unknown = total_classified = total_bp = 0
    result = {}
    for name, entry in by_record.items():
        merged: list[list[int]] = []
        for left, right in sorted(entry.pop("intervals")):
            if not merged or left > merged[-1][1]:
                merged.append([left, right])
            else:
                merged[-1][1] = max(merged[-1][1], right)
        entry["union_bp_from_out"] = sum(right - left for left, right in merged)
        total_rows += entry["repeat_rows"]
        total_unknown += entry["unknown_rows"]
        total_classified += entry["classified_rows"]
        total_bp += entry["union_bp_from_out"]
        result[name] = entry
    return {"repeatmasker_out_files": [str(path.relative_to(cell)) for path in candidates],
            "total_repeat_rows": total_rows, "total_unknown_rows": total_unknown,
            "total_classified_rows": total_classified, "total_union_bp_from_out": total_bp,
            "by_record": result}


def write_core_manifests(method: str, method_root: Path, geometry: list[dict], original: dict[str, str], masked: dict[str, str], summary: dict | None) -> list[dict]:
    manifests = []
    for core in geometry:
        name = core["record_id"]
        sequence = masked[name]
        core_dir = method_root / core["id"]
        core_dir.mkdir()
        write_fasta(core_dir / "mask.fasta", name, sequence)
        lowercase = sum(base in "acgt" for base in sequence)
        per_record = summary.get("by_record", {}).get(name) if summary else None
        manifest = {"method": method, "status": "MASK_COMPLETED", "core": core,
                    "mask_fasta": "mask.fasta", "panel_record": name,
                    "lowercase_bp": lowercase, "masked_acgt_bp": lowercase,
                    "panel_input_bp": len(original[name]),
                    "library_policy": "complete consensi.fa.classified including Unknown" if method == "RM2" else None,
                    "repeatmasker_summary": per_record}
        write_json(core_dir / "manifest.json", manifest)
        write_json(core_dir / "status.json", manifest)
        manifests.append(manifest)
    return manifests


def run_red(method_root: Path, geometry: list[dict], original: dict[str, str]) -> dict:
    if not RED.exists():
        raise FileNotFoundError(f"official Red binary missing: {RED}")
    genome = method_root / "red_genome"; masked_dir = method_root / "red_masked"; repeats_dir = method_root / "red_repeats"
    genome.mkdir(); masked_dir.mkdir(); repeats_dir.mkdir()
    panel = genome / "panel.fa"; write_panel(panel, geometry, original)
    run_command([str(RED), "-gnm", str(genome), "-msk", str(masked_dir), "-rpt", str(repeats_dir), "-cor", "4", "-frm", "2"], method_root, "red")
    outputs = sorted(masked_dir.glob("*.msk"))
    if len(outputs) != 1:
        raise ValueError(f"Red produced {len(outputs)} pooled .msk files")
    masked = parse_masked_panel(outputs[0], original)
    summary = {"semantic_scope": "all detected repeats; no family classification",
               "native_masked_fasta": str(outputs[0].relative_to(method_root))}
    manifests = write_core_manifests("RED", method_root, geometry, original, masked, summary)
    return {"method": "RED", "status": "MASK_COMPLETED", "panel_fasta": str(panel.relative_to(method_root)),
            "native_masked_fasta": str(outputs[0].relative_to(method_root)),
            "semantic_scope": "all detected repeats; no family classification", "cores": manifests}


def run_rm2(method_root: Path, geometry: list[dict], original: dict[str, str]) -> dict:
    if not RM2_IMAGE.exists() or not RM_IMAGE.exists():
        raise FileNotFoundError("pinned RepeatModeler2/RepeatMasker images are missing")
    panel = method_root / "panel.fa"; write_panel(panel, geometry, original)
    bind = f"{method_root}:/work"; common = ["apptainer", "exec", "--cleanenv", "--bind", bind, "--pwd", "/work"]
    run_command(common + [str(RM2_IMAGE), "BuildDatabase", "-name", "db", "panel.fa"], method_root, "builddatabase")
    run_command(common + [str(RM2_IMAGE), "RepeatModeler", "-database", "db", "-threads", "4", "-srand", "42", "-LTRStruct"], method_root, "repeatmodeler")
    libraries = sorted(method_root.glob("RM_*/consensi.fa.classified"))
    if len(libraries) != 1:
        raise ValueError(f"expected one pooled classified library, found {len(libraries)}")
    library = libraries[0]; rm_out = method_root / "repeatmasker"; rm_out.mkdir()
    run_command(common + [str(RM_IMAGE), "RepeatMasker", "-pa", "4", "-gff", "-xsmall", "-lib", "/work/" + str(library.relative_to(method_root)), "-dir", "/work/repeatmasker", "/work/panel.fa"], method_root, "repeatmasker")
    outputs = sorted(rm_out.glob("*.masked"))
    if len(outputs) != 1:
        raise ValueError(f"RepeatMasker produced {len(outputs)} pooled .masked files")
    masked = parse_masked_panel(outputs[0], original)
    summary = rm2_summary(method_root, set(original)); summary["library"] = str(library.relative_to(method_root))
    manifests = write_core_manifests("RM2", method_root, geometry, original, masked, summary)
    return {"method": "RM2", "status": "MASK_COMPLETED", "panel_fasta": "panel.fa",
            "repeatmodeler_library": str(library.relative_to(method_root)),
            "native_masked_fasta": str(outputs[0].relative_to(method_root)),
            "library_policy": "complete consensi.fa.classified including Unknown",
            "repeatmasker_summary": summary, "cores": manifests}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("method", choices=["RED", "RM2"]); args = parser.parse_args()
    geometry, original = fixed_panel(); method_root = BASE / "mask" / args.method; method_root.mkdir(parents=True, exist_ok=True)
    status_path = method_root / "status.json"
    if status_path.exists():
        old = json.loads(status_path.read_text())
        if old.get("status") == "MASK_COMPLETED":
            print(json.dumps({"status": "REUSED", "method": args.method})); return
        raise FileExistsError(f"existing partial pooled mask panel is preserved: {method_root}")
    status = {"status": "RUNNING", "method": args.method, "core_count": len(geometry),
              "panel_bp": sum(len(sequence) for sequence in original.values()), "slurm_job_id": os.getenv("SLURM_JOB_ID"), "started_epoch": time.time()}
    write_json(status_path, status)
    try:
        result = run_red(method_root, geometry, original) if args.method == "RED" else run_rm2(method_root, geometry, original)
        result.update({"slurm_job_id": os.getenv("SLURM_JOB_ID"), "wall_seconds": time.time() - status["started_epoch"]})
        write_json(method_root / "panel_manifest.json", result); status.update(result); status["status"] = "MASK_COMPLETED"; write_json(status_path, status)
        print(json.dumps({"status": "MASK_COMPLETED", "method": args.method, "seconds": result["wall_seconds"]}))
    except Exception as exc:
        status.update({"status": "MASK_FAILED", "error": repr(exc), "wall_seconds": time.time() - status["started_epoch"]}); write_json(status_path, status); raise


if __name__ == "__main__":
    main()
