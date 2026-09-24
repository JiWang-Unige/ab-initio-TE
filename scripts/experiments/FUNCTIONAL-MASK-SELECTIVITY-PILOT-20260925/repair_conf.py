#!/usr/bin/env python3
"""Repair the one confidence mask prepared before the parser/order fix.

This is deliberately limited to the observed chicken/c01 discrepancy.  The
original FASTA, GFF, command record, and mask manifest are moved to explicit
``*-bugged-pre-repair`` names before the corrected confidence arm is
materialized and run.  No other arm is rewritten.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[3]
NAME = "FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925"
SPECIES = "chicken"
CORE_ID = "c01"
OUT = ROOT / "outputs" / NAME
REPORT = ROOT / "reports" / NAME


def load_pilot():
    path = ROOT / "scripts/experiments" / NAME / "pilot.py"
    spec = importlib.util.spec_from_file_location("functional_mask_pilot_repair", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sequence(path: Path) -> str:
    return "".join(line.strip() for line in path.open() if not line.startswith(">"))


def main():
    pilot = load_pilot()
    cell = OUT / SPECIES / CORE_ID
    manifest = pilot.read_json(OUT / SPECIES / "manifest.json")
    row = next(item for item in manifest["cores"] if item["id"] == CORE_ID)
    status_path = cell / "status.json"
    status = pilot.read_json(status_path)
    if status.get("status") != "COMPLETED":
        raise RuntimeError("repair requires the original c01 array task to be completed")
    conf_status = status.get("arms", {}).get("RM2_COMMON_CONF", {})
    if conf_status.get("exit_code") != 0:
        raise RuntimeError("repair requires a successful original c01 confidence arm")

    old_mask = cell / "RM2_COMMON_CONF.fasta"
    old_gff = cell / "RM2_COMMON_CONF.gff3"
    old_stderr = cell / "RM2_COMMON_CONF.stderr"
    old_command = cell / "RM2_COMMON_CONF.command.json"
    old_manifest = cell / "mask_manifest.json"
    required = [old_mask, old_gff, old_stderr, old_command, old_manifest]
    archive_paths = {
        old_mask: cell / "RM2_COMMON_CONF-bugged-pre-repair.fasta",
        old_gff: cell / "RM2_COMMON_CONF-bugged-pre-repair.gff3",
        old_stderr: cell / "RM2_COMMON_CONF-bugged-pre-repair.stderr",
        old_command: cell / "RM2_COMMON_CONF-bugged-pre-repair.command.json",
        old_manifest: cell / "mask_manifest-bugged-pre-repair.json",
    }
    original_files = [old_mask, old_gff, old_stderr, old_command]
    if all(path.exists() for path in required):
        if any(path.exists() for path in archive_paths.values()):
            raise RuntimeError("partial repair has mixed canonical/archive inputs")
        repair_start = True
    elif (not any(path.exists() for path in original_files)
          and old_manifest.exists()
          and all(archive_paths[path].exists() for path in original_files)):
        # A prior attempt may have moved the first four files before failing
        # on the manifest archive.  Continue from that explicit state.
        repair_start = False
    else:
        raise RuntimeError("original c01 confidence artifacts are incomplete")

    rm2 = pilot.lowercase_runs(sequence(cell / "RM2_FULL.fasta"))
    rm2_path = ROOT / pilot.CFG["inputs"]["rm2_annotation_out"].replace("{species}", SPECIES)
    records = pilot.parse_rm2_out(rm2_path, {row["chrom"]})
    quality = pilot.attach_native_quality(rm2, records[row["chrom"]], row["halo"][0])
    grouped = pilot.runs_by_bin(rm2)
    lookup = {(item["interval"][0], item["interval"][1]): item for item in quality}
    quality_grouped = [[lookup[(left, right)] for left, right in group] for group in grouped]
    corrected_runs, corrected_records = pilot.select_exact(
        quality_grouped, row["common_budget_by_stratum_bp"], pilot.quality_key
    )
    u_record, u_seq = pilot.read_single_fasta(cell / "U.fasta")
    corrected_seq = pilot.mask_sequence(u_seq, corrected_runs)
    if corrected_seq.upper() != u_seq.upper():
        raise RuntimeError("corrected mask changed uppercase input sequence")
    corrected_path = cell / "RM2_COMMON_CONF.corrected.fasta"
    pilot.write_fasta(corrected_path, u_record, corrected_seq)

    # Preserve every pre-repair artifact before changing the canonical arm.
    archive = {}
    if repair_start:
        for path, target in archive_paths.items():
            if target.exists():
                raise RuntimeError(f"archive target exists: {target}")
            shutil.move(str(path), str(target))
    elif old_manifest.exists() and not archive_paths[old_manifest].exists():
        shutil.move(str(old_manifest), str(archive_paths[old_manifest]))
    for path, target in archive_paths.items():
        archive[path.name] = str(target)
    if old_mask.exists():
        raise RuntimeError("canonical confidence mask unexpectedly exists before repair")
    shutil.move(str(corrected_path), str(old_mask))

    repair_meta = {
        "protocol": NAME,
        "status": "PREPARED_CORRECTED_CONF_ONLY",
        "species": SPECIES,
        "core": CORE_ID,
        "reason": "prepared mask matched neither old raw-SW nor corrected ratio rule",
        "old_artifacts": archive,
        "new_rule": "divergence ascending, SW/aligned_length descending, alignment length descending, coordinates/ID",
        "new_runs": corrected_runs,
        "new_selection_records": corrected_records,
        "new_summary": pilot.mask_summary(corrected_runs, 100000, len(u_seq) - 100000),
        "new_sequence_uppercase_identity": corrected_seq.upper() == u_seq.upper(),
        "old_full_arm_preserved": True,
        "other_arms_rewritten": False,
    }
    old_manifest_data = json.loads(archive_paths[old_manifest].read_text())
    old_manifest_data["mask_summaries"]["RM2_COMMON_CONF"] = repair_meta["new_summary"]
    old_manifest_data["selection_records"]["RM2_COMMON_CONF"] = corrected_records
    old_manifest_data["conf_rule_repair"] = {
        "status": "COMPLETED_CORRECTED_CONF_ONLY",
        "archived_pre_repair_manifest": str(archive_paths[old_manifest]),
        "rule": repair_meta["new_rule"],
    }
    pilot.dump(old_manifest, old_manifest_data)
    pilot.dump(cell / "conf-rule-repair.json", repair_meta)

    binary = "/opt/ebsofts/AUGUSTUS/3.5.0-foss-2022b/bin/augustus"
    argv = [
        binary,
        "--species=" + pilot.CFG["species"][SPECIES]["augustus_species"],
        "--gff3=on",
        "--softmasking=1",
        "--UTR=off",
        "--stopCodonExcludedFromCDS=false",
        "--alternatives-from-evidence=false",
        "--alternatives-from-sampling=false",
        str(old_mask),
    ]
    command = pilot.run_command(argv, cell, "RM2_COMMON_CONF", pilot.augustus_env())
    (cell / "RM2_COMMON_CONF.stdout").rename(old_gff)
    core = pilot.base.Core(row["chrom"], 1, row["core"][0], row["core"][1], row["halo"][0], row["halo"][1])
    chains, _ = pilot.base.parse_predictions(old_gff, core, "gff3")
    status["arms"]["RM2_COMMON_CONF"] = {
        **command,
        "predicted_chains": len(chains),
        "same_uppercase_letters": True,
        "repaired_from": str(archive["RM2_COMMON_CONF.fasta"]),
        "repair_rule": "sw_per_aligned_length",
    }
    status["status"] = "COMPLETED"
    status["repair_job_id"] = __import__("os").environ.get("SLURM_JOB_ID")
    pilot.dump(status_path, status)
    repair_meta["status"] = "COMPLETED"
    repair_meta["repair_job_id"] = status["repair_job_id"]
    repair_meta["predicted_chains"] = len(chains)
    pilot.dump(cell / "conf-rule-repair.json", repair_meta)
    REPORT.mkdir(parents=True, exist_ok=True)
    pilot.dump(REPORT / "conf-repair-chicken-c01.json", repair_meta)
    print(json.dumps({"status": "COMPLETED", "species": SPECIES, "core": CORE_ID, "predicted_chains": len(chains)}), flush=True)


if __name__ == "__main__":
    main()
