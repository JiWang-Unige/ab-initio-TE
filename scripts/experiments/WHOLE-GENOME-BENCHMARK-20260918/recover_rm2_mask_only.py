#!/usr/bin/env python3
"""Retry only RepeatMasker after a successful RM2 classification stage.

This is deliberately separate from ``recover_rm2.py``: a failed mask stage
must reuse the already produced ``consensi.fa.classified`` byte-for-byte and
must never rerun RepeatClassifier.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict

from common import ensure_empty_output, fasta_stats, file_metadata, run_timed, slurm_context, host_context, write_json
from recover_rm2 import (PARENT_CONFIG, RECOVERY_CONFIG, ROOT, bind_base,
                         copy_once, exactly_one_nonempty, load_json,
                         parent_discovery, stage_env)


def run(args: argparse.Namespace) -> Dict[str, object]:
    parent_cfg = load_json(args.config.resolve())
    recovery_cfg = load_json(RECOVERY_CONFIG)
    if args.species not in parent_cfg["species"]:
        raise ValueError("species is not frozen in parent config: %s" % args.species)
    source_cfg = parent_cfg["species"][args.species]
    method_cfg = parent_cfg["methods"]["RM2"]
    source = Path(source_cfg["fasta"])
    if not source.is_file():
        raise FileNotFoundError("frozen source FASTA missing: %s" % source)
    parent = (ROOT / "outputs/WHOLE-GENOME-BENCHMARK-20260918/native" / args.species / "RM2").resolve()
    provenance = parent_discovery(parent, recovery_cfg)
    resume_from = args.mask_source.resolve()
    resume_status_path = resume_from / "status.json"
    if not resume_status_path.is_file():
        raise FileNotFoundError("mask-only source status is missing: %s" % resume_status_path)
    resume_status = load_json(resume_status_path)
    if resume_status.get("status") != "FAILED":
        raise RuntimeError("mask-only source must be the preserved failed mask attempt: %s" % resume_status.get("status"))
    classifier_stages = [stage for stage in resume_status.get("stages", [])
                         if stage.get("name") == "repeatclassifier"]
    if len(classifier_stages) != 1 or classifier_stages[0].get("returncode") != 0:
        raise RuntimeError("mask-only source does not contain one successful RepeatClassifier stage")
    classified = exactly_one_nonempty([resume_from / "consensi.fa.classified"],
                                      "reused classified library")
    consensi = exactly_one_nonempty([resume_from / "consensi.fa"], "reused consensus library")
    stockholm = exactly_one_nonempty([resume_from / "families.stk"], "reused seed alignments")
    famdb = Path(recovery_cfg["runtime"]["famdb4"])
    rm_image = Path(method_cfg["repeatmasker_image"])
    for path, label in ((famdb, "fixed FamDB4 asset"), (rm_image, "pinned RepeatMasker image")):
        if not path.exists():
            raise FileNotFoundError("%s is missing: %s" % (label, path))
    output = (ROOT / "outputs/WHOLE-GENOME-BENCHMARK-20260918/native" / args.species /
              ("RM2-%s" % args.output_suffix)).resolve()
    ensure_empty_output(output)
    for name in ("work", "tmp", "home", "repeatmasker"):
        (output / name).mkdir()
    status: Dict[str, object] = {
        "protocol": "WHOLE-GENOME-BENCHMARK-20260918",
        "recovery": "RM2_MASK_ONLY_CONTINUATION",
        "species": args.species, "method": "RM2", "status": "RUNNING",
        "started_epoch": time.time(), "input_metadata": dict(file_metadata(source), stats=fasta_stats(source)),
        "software": method_cfg, "recovery_contract": recovery_cfg,
        "host": host_context(), "slurm": slurm_context(), "parent_discovery": provenance,
        "mask_only_source": {"root": str(resume_from), "status": str(resume_status_path),
                              "classifier_stage": classifier_stages[0],
                              "classified_metadata": file_metadata(classified)},
        "famdb_runtime": {"path": str(famdb), "manifest": load_json(famdb / "manifest.json"),
                           "container_path": "/usr/local/share/RepeatMasker/Libraries/famdb",
                           "knowledge_condition": "Dfam 4.0 fixed benchmark asset; no classifier rerun or library filtering"},
        "stages": [],
        "input_contract": "complete unchanged source FASTA; reuse successful classifier output from a fresh mask-only root",
    }
    write_json(output / "status.json", status)
    env = stage_env(output)
    try:
        copy_once(consensi, output / "consensi.fa")
        copy_once(stockholm, output / "families.stk")
        copy_once(classified, output / "consensi.fa.classified")
        classified_stk = resume_from / "families-classified.stk"
        if classified_stk.is_file() and classified_stk.stat().st_size > 0:
            copy_once(classified_stk, output / "families-classified.stk")
        base = bind_base(output, source, famdb)
        masker = base + [str(rm_image), "env", "HOME=/work/home", "TMPDIR=/work/tmp",
                         "FAMDB_DIR=/usr/local/share/famdb-3.0.0/Libraries/famdb",
                         "BLAST_USAGE_REPORT=false", "RepeatMasker", "-e", "rmblast",
                         "-pa", "4", "-gff", "-xsmall", "-lib", "/work/consensi.fa.classified",
                         "-dir", "/work/repeatmasker", str(source)]
        stage = run_timed(masker, output, "repeatmasker", env)
        stage.update({"name": "repeatmasker", "role": "masking",
                      "mask_parallelism": "RepeatMasker -pa 4; same frozen native command",
                      "classification_reused": True})
        status["stages"].append(stage)
        write_json(output / "status.json", status)
        if stage["returncode"] != 0:
            raise RuntimeError("RepeatMasker failed with return code %s" % stage["returncode"])
        annotation = exactly_one_nonempty(list((output / "repeatmasker").glob("*.out.gff")), "RepeatMasker GFF")
        raw_out = exactly_one_nonempty(list((output / "repeatmasker").glob("*.out")), "RepeatMasker .out")
        masked = exactly_one_nonempty(list((output / "repeatmasker").glob("*.masked")), "RepeatMasker masked FASTA")
        copy_once(annotation, output / "annotation.gff3")
        copy_once(raw_out, output / "annotation.out")
        copy_once(masked, output / "masked.fa")
        copy_once(classified, output / "library.fasta")
        status["native_output"] = {"annotation_gff3": "annotation.gff3", "annotation_out": "annotation.out",
                                    "masked_fasta": "masked.fa", "library_fasta": "library.fasta",
                                    "library_source": "consensi.fa.classified", "classification_reused": True,
                                    "source_discovery": str(parent),
                                    "score_method_root": "native/%s/%s" % (args.species, "RM2-%s" % args.output_suffix)}
        status.update({"status": "COMPLETED", "finished_epoch": time.time(),
                       "wall_seconds": time.time() - float(status["started_epoch"]),
                       "timing_scope": "RepeatMasker mask-only continuation; parent discovery and classifier walls retained separately"})
        write_json(output / "status.json", status)
        summary_script = Path(__file__).with_name("summarize_native.py")
        summary = subprocess.run([sys.executable, str(summary_script), "--species", args.species,
                                  "--method", "RM2", "--output-dir", str(output)],
                                 cwd=str(summary_script.parent), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        if summary.returncode != 0:
            status["annotation_summary_error"] = summary.stderr[-4000:]
            write_json(output / "status.json", status)
            raise RuntimeError("native output summary failed with return code %s" % summary.returncode)
        return status
    except Exception as exc:
        status.update({"status": "FAILED", "finished_epoch": time.time(),
                       "wall_seconds": time.time() - float(status["started_epoch"]),
                       "error": repr(exc),
                       "timing_scope": "RepeatMasker mask-only continuation; parent discovery and classifier walls retained separately"})
        write_json(output / "status.json", status)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=PARENT_CONFIG)
    parser.add_argument("--species", required=True, choices=("chicken", "zebrafish"))
    parser.add_argument("--mask-source", type=Path, required=True,
                        help="failed fresh RM2 root containing a successful consensi.fa.classified")
    parser.add_argument("--output-suffix", default="mask-recovery-v2")
    run(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
