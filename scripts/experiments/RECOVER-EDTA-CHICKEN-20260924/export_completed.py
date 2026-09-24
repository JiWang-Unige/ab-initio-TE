#!/usr/bin/env python3
"""Export already completed native EDTA output without rerunning discovery.

Job 13190938 completed EDTA but its wrapper rejected standard internal copies.
Select EDTA.pl's published top-level outputs, preserving the failed wrapper.
Also version and correct the independently identified FASTA-header summaries.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

from recover_edta import NORMALIZED_BASENAME, sequence_id_decode_evidence, write_json


def run(root: Path, source: Path, output: Path) -> None:
    started = time.monotonic()
    prior = json.loads((source / "status.json").read_text())
    if prior.get("job") != "13190938" or prior.get("status") != "FAILED":
        raise ValueError("expected preserved wrapper-failed EDTA job 13190938")
    stages = {stage["name"]: stage for stage in prior["stages"]}
    for name in ("native_raw_intact_aggregate", "edta_final_annotation"):
        if stages[name]["returncode"] != 0:
            raise ValueError(f"native stage did not complete: {name}")
    native_log = (source / "edta_final_annotation.stdout").read_text()
    for marker in ("EDTA final stage finished!", "TE annotation using the EDTA library has finished!",
                   "Evaluation of TE annotation finished!"):
        if marker not in native_log:
            raise ValueError(f"missing native completion marker: {marker}")
    source_gff = source / f"{NORMALIZED_BASENAME}.EDTA.TEanno.gff3"
    source_library = source / f"{NORMALIZED_BASENAME}.EDTA.TElib.fa"
    for path in (source_gff, source_library):
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"missing canonical native output: {path}")
    output.mkdir(parents=True, exist_ok=False)
    state = {
        "protocol": "RECOVER-EDTA-CHICKEN-20260924", "parent_protocol": "WHOLE-GENOME-BENCHMARK-20260918",
        "status": "RUNNING", "species": "chicken", "assembly": "galGal6", "method": "EDTA",
        "job": os.environ.get("SLURM_JOB_ID"), "native_job": "13190938",
        "resources": {"partition": "private-teodoro-gpu", "cpus": 4, "memory_gb": 16, "gpus": 0},
        "source": str(source), "preserved_source_status": str(source / "status.json"),
        "operation": "postprocessing export only; no native rerun, training, annotation or threshold change",
        "native_parameters": prior["native_parameters"], "native_stages": prior["stages"],
        "prior_native_slurm_seconds": 5948, "native_remaining_before_export_seconds": 425733,
        "native_raw_aggregate": prior["native_raw_aggregate"],
    }
    write_json(output / "status.json", state)
    try:
        shutil.copy2(source_gff, output / "annotation.gff3")
        shutil.copy2(source_library, output / "library.fasta")
        shutil.copy2(source / f"{NORMALIZED_BASENAME}.seqid.map", output / f"{NORMALIZED_BASENAME}.seqid.map")
        state["sequence_id_decoding"] = sequence_id_decode_evidence(output, output / "annotation.gff3")
        state["native_output"] = {
            "annotation_gff3": "annotation.gff3", "library_fasta": "library.fasta",
            "annotation_source": str(source_gff), "library_source": str(source_library),
            "selection": "EDTA.pl top-level published outputs after native seqid decoding",
            "masking_output": None,
            "maker_masked_source": str(source / f"{NORMALIZED_BASENAME}.MAKER.masked"),
            "maker_mask_policy": "native filtered hardmask (reported 6.19%); not the full TEanno coverage or scoring input",
        }
        sys.path.insert(0, str(root / "scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918"))
        from summarize_native import summarize_gff, summarize_library

        summary = {
            "protocol": "WHOLE-GENOME-BENCHMARK-20260918", "status": "COMPLETED",
            "species": "chicken", "method": "EDTA",
            "annotation": summarize_gff(output / "annotation.gff3"),
            "library": summarize_library(output / "library.fasta"),
            "unknown_policy": "Native unknown rows/headers retained; descriptive GFF rows may contain parent/child overlap",
            "classification_scope": "native GFF classification attribute and FASTA suffix after #",
        }
        write_json(output / "annotation_summary.json", summary)
        repairs = {}
        for species in ("chicken", "zebrafish"):
            native = root / "outputs/WHOLE-GENOME-BENCHMARK-20260918/native" / species / "RM2-mask-recovery-v2"
            path = native / "annotation_summary.json"
            old = json.loads(path.read_text())
            if json.loads((native / "status.json").read_text())["status"] != "COMPLETED":
                raise ValueError(f"RM2 is not completed: {species}")
            backup = native / "annotation_summary.before-header-fix-20260925.json"
            if backup.exists():
                raise FileExistsError(backup)
            shutil.copy2(path, backup)
            old["library"] = summarize_library(native / "library.fasta")
            old["library_summary_revision"] = {
                "revision": "native-fasta-hash-suffix-v1", "backup": str(backup),
                "native_annotation_and_scores_unchanged": True,
            }
            write_json(path, old)
            write_json(output / f"{species}-rm2-summary.json", old)
            repairs[species] = old["library_summary_revision"]
        state.update({"status": "COMPLETED", "annotation_summary": "annotation_summary.json",
                      "rm2_library_summary_repairs": repairs, "finished_epoch": time.time(),
                      "wall_seconds": time.monotonic() - started})
        write_json(output / "status.json", state)
    except Exception as exc:
        state.update({"status": "FAILED", "error": repr(exc), "finished_epoch": time.time(),
                      "wall_seconds": time.monotonic() - started})
        write_json(output / "status.json", state)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.root.resolve(), args.source.resolve(), args.output.resolve())
