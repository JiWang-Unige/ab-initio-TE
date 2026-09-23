#!/usr/bin/env python3
"""Continue failed whole-genome RM2 cells after terminal discovery.

The parent RM2 directories are immutable evidence.  This continuation copies
only the terminal ``consensi.fa`` and ``families.stk`` from the top-level
RepeatModeler directory, runs the pinned classifier with the fixed Dfam4
asset, and then runs the exact frozen RepeatMasker command in a new output
directory.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Dict, List

from common import ensure_empty_output, fasta_stats, file_metadata, run_timed, slurm_context, host_context, write_json


ROOT = Path(__file__).resolve().parents[3]
PARENT_CONFIG = ROOT / "configs/WHOLE-GENOME-BENCHMARK-20260918.json"
RECOVERY_CONFIG = ROOT / "configs/WHOLE-GENOME-BENCHMARK-20260918-RM2-RECOVERY.json"


def load_json(path: Path) -> Dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def exactly_one_nonempty(paths: List[Path], label: str) -> Path:
    candidates = sorted(path for path in paths if path.is_file() and path.stat().st_size > 0)
    if len(candidates) != 1:
        raise RuntimeError("expected exactly one non-empty %s, found %s" % (label, candidates))
    return candidates[0]


def ordered_terminal_markers(log: Path, markers: List[str]) -> Dict[str, object]:
    text = log.read_text(encoding="utf-8", errors="replace")
    # Some markers, especially ``LTR Structural Analysis``, also occur in the
    # header.  Find each required stage after the preceding stage rather than
    # comparing the first global occurrence.
    positions: Dict[str, int] = {}
    cursor = -1
    for marker in markers:
        position = text.find(marker, cursor + 1)
        positions[marker] = position
        cursor = position
    if any(position < 0 for position in positions.values()):
        raise RuntimeError("terminal RepeatModeler log is missing required markers: %s" % positions)
    return {"path": str(log), "markers": positions, "ordered": True}


def parent_discovery(parent: Path, recovery_cfg: Dict[str, object]) -> Dict[str, object]:
    status_path = parent / "status.json"
    if not status_path.is_file():
        raise FileNotFoundError("parent RM2 status is missing: %s" % status_path)
    status = load_json(status_path)
    if status.get("status") != "FAILED":
        raise RuntimeError("continuation requires the preserved parent status to be FAILED: %s" % status.get("status"))
    stages = status.get("stages", [])
    modeler = [stage for stage in stages if stage.get("name") == "repeatmodeler"]
    if len(modeler) != 1 or modeler[0].get("returncode") != 0:
        raise RuntimeError("parent RepeatModeler stage is not a terminal successful discovery stage")
    argv = modeler[0].get("argv", [])
    if "-LTRStruct" not in argv or "-threads" not in argv or "16" not in [str(value) for value in argv]:
        raise RuntimeError("parent RepeatModeler invocation does not match frozen -LTRStruct/16-thread contract")
    rm_dirs = sorted(path for path in parent.glob("RM_*") if path.is_dir())
    if len(rm_dirs) != 1:
        raise RuntimeError("expected one terminal RM_* directory, found %s" % rm_dirs)
    rm_dir = rm_dirs[0]
    consensi = exactly_one_nonempty([rm_dir / "consensi.fa"], "top-level terminal consensi.fa")
    stockholm = exactly_one_nonempty([rm_dir / "families.stk"], "top-level terminal families.stk")
    log = exactly_one_nonempty([rm_dir / "rmod.log"], "terminal RepeatModeler log")
    log_evidence = ordered_terminal_markers(log, recovery_cfg["discovery_contract"]["required_log_markers_in_order"])
    return {
        "parent_status": str(status_path),
        "parent_status_snapshot": status,
        "rm_dir": str(rm_dir),
        "consensi": str(consensi),
        "families_stk": str(stockholm),
        "rmod_log": str(log),
        "terminal_evidence": log_evidence,
        "consensi_metadata": file_metadata(consensi),
        "families_stk_metadata": file_metadata(stockholm),
        "rmod_log_metadata": file_metadata(log),
        "discovery_wall_seconds": float(modeler[0].get("wall_seconds_observed") or 0.0),
        "discovery_max_rss_kb": modeler[0].get("max_rss_kb"),
    }


def stage_env(output: Path) -> Dict[str, str]:
    env = os.environ.copy()
    env.update({"BLAST_USAGE_REPORT": "false", "OMP_NUM_THREADS": "16",
                "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "HOME": str(output / "home"), "TMPDIR": str(output / "tmp")})
    return env


def bind_base(output: Path, genome: Path, famdb: Path) -> List[str]:
    return [
        "apptainer", "exec", "--cleanenv",
        "--bind", "%s:/work" % output,
        "--bind", "%s:%s:ro" % (genome.parent, genome.parent),
        "--bind", "%s:/opt/famdb:ro" % famdb,
        # RepeatMasker resolves FamDB through its installed library path even
        # when a custom -lib is supplied.  These are the same two fixed
        # runtime binds used by the existing benchmark native wrapper.
        "--bind", "%s:/usr/local/share/famdb-3.0.0/Libraries/famdb:ro" % famdb,
        "--bind", "%s:/usr/local/share/RepeatMasker/Libraries/famdb:ro" % famdb,
        "--pwd", "/work",
    ]


def copy_once(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError("refusing to replace existing recovery artifact: %s" % destination)
    shutil.copy2(source, destination)


def recover(args: argparse.Namespace) -> Dict[str, object]:
    parent_cfg = load_json(args.config.resolve())
    recovery_cfg = load_json(RECOVERY_CONFIG)
    if args.species not in parent_cfg["species"]:
        raise ValueError("species is not frozen in parent config: %s" % args.species)
    species_cfg = parent_cfg["species"][args.species]
    method_cfg = parent_cfg["methods"]["RM2"]
    output = (ROOT / "outputs/WHOLE-GENOME-BENCHMARK-20260918/native" / args.species /
              ("RM2-%s" % args.output_suffix)).resolve()
    ensure_empty_output(output)
    for name in ("work", "tmp", "home", "repeatmasker"):
        (output / name).mkdir()
    source = Path(species_cfg["fasta"])
    if not source.is_file():
        raise FileNotFoundError("frozen source FASTA missing: %s" % source)
    parent = (ROOT / "outputs/WHOLE-GENOME-BENCHMARK-20260918/native" / args.species / "RM2").resolve()
    provenance = parent_discovery(parent, recovery_cfg)
    famdb = Path(recovery_cfg["runtime"]["famdb4"])
    rm2_image = Path(method_cfg["repeatmodeler_image"])
    rm_image = Path(method_cfg["repeatmasker_image"])
    for path, label in ((famdb, "fixed FamDB4 asset"), (rm2_image, "pinned RepeatModeler image"),
                        (rm_image, "pinned RepeatMasker image")):
        if not path.exists():
            raise FileNotFoundError("%s is missing: %s" % (label, path))
    famdb_manifest = famdb / "manifest.json"
    if not famdb_manifest.is_file():
        raise FileNotFoundError("fixed FamDB manifest is missing: %s" % famdb_manifest)
    source_info = file_metadata(source)
    source_info["stats"] = fasta_stats(source)
    status: Dict[str, object] = {
        "protocol": "WHOLE-GENOME-BENCHMARK-20260918",
        "recovery": "RM2_CLASSIFIER_MASK_CONTINUATION",
        "species": args.species,
        "method": "RM2",
        "status": "RUNNING",
        "started_epoch": time.time(),
        "input_metadata": source_info,
        "software": method_cfg,
        "recovery_contract": recovery_cfg,
        "host": host_context(),
        "slurm": slurm_context(),
        "parent_discovery": provenance,
        "famdb_runtime": {"path": str(famdb), "manifest": load_json(famdb_manifest),
                           "manifest_metadata": file_metadata(famdb_manifest),
                           "container_path": "/opt/famdb",
                           "knowledge_condition": "Dfam 4.0 fixed benchmark asset; classifier uses all available asset records and no family filtering"},
        "stages": [],
        "input_contract": "complete unchanged source FASTA; terminal RepeatModeler discovery products reused byte-for-byte in a new output directory",
    }
    write_json(output / "status.json", status)
    env = stage_env(output)
    try:
        # The container is bound at output -> /work, so these continuation
        # inputs deliberately live at the output root.  The separate work/
        # directory is retained for auxiliary scratch/cache files.
        copy_once(Path(provenance["consensi"]), output / "consensi.fa")
        copy_once(Path(provenance["families_stk"]), output / "families.stk")
        status["reused_terminal_products"] = {
            "consensi": "consensi.fa", "families_stk": "families.stk",
            "source_paths": [provenance["consensi"], provenance["families_stk"]],
            "selection": "top-level RM_*/consensi.fa and RM_*/families.stk after -LTRStruct; no round subdirectory"
        }
        write_json(output / "status.json", status)
        base = bind_base(output, source, famdb)
        classifier = base + [str(rm2_image), "env", "HOME=/work/home", "TMPDIR=/work/tmp",
                             "FAMDB_DIR=/opt/famdb", "BLAST_USAGE_REPORT=false",
                             "RepeatClassifier", "-famdb_dir", "/opt/famdb", "-threads", "16",
                             "-consensi", "/work/consensi.fa", "-stockholm", "/work/families.stk"]
        stage = run_timed(classifier, output, "repeatclassifier", env)
        stage.update({"name": "repeatclassifier", "role": "classification",
                      "knowledge_condition": "fixed Dfam 4.0 FamDB-v2"})
        status["stages"].append(stage)
        write_json(output / "status.json", status)
        if stage["returncode"] != 0:
            raise RuntimeError("RepeatClassifier failed with return code %s" % stage["returncode"])
        classified = exactly_one_nonempty([output / "consensi.fa.classified"],
                                          "RepeatClassifier classified library")
        classified_stk = output / "families-classified.stk"
        status["classified_library"] = {"path": "consensi.fa.classified",
                                         "metadata": file_metadata(classified),
                                         "classified_stockholm": file_metadata(classified_stk)}
        write_json(output / "status.json", status)
        library_guest = "/work/consensi.fa.classified"
        masker = base + [str(rm_image), "env", "HOME=/work/home", "TMPDIR=/work/tmp",
                         "FAMDB_DIR=/usr/local/share/famdb-3.0.0/Libraries/famdb",
                         "BLAST_USAGE_REPORT=false", "RepeatMasker", "-e", "rmblast",
                         "-pa", "4", "-gff", "-xsmall", "-lib", library_guest,
                         "-dir", "/work/repeatmasker", str(source)]
        stage = run_timed(masker, output, "repeatmasker", env)
        stage.update({"name": "repeatmasker", "role": "masking",
                      "mask_parallelism": "RepeatMasker -pa 4; same frozen native command"})
        status["stages"].append(stage)
        write_json(output / "status.json", status)
        if stage["returncode"] != 0:
            raise RuntimeError("RepeatMasker failed with return code %s" % stage["returncode"])
        annotation = exactly_one_nonempty(list((output / "repeatmasker").glob("*.out.gff")),
                                           "RepeatMasker GFF")
        raw_out = exactly_one_nonempty(list((output / "repeatmasker").glob("*.out")),
                                       "RepeatMasker .out")
        masked = exactly_one_nonempty(list((output / "repeatmasker").glob("*.masked")),
                                      "RepeatMasker masked FASTA")
        copy_once(annotation, output / "annotation.gff3")
        copy_once(raw_out, output / "annotation.out")
        copy_once(masked, output / "masked.fa")
        copy_once(classified, output / "library.fasta")
        status["native_output"] = {"annotation_gff3": "annotation.gff3", "annotation_out": "annotation.out",
                                    "masked_fasta": "masked.fa", "library_fasta": "library.fasta",
                                    "library_source": "consensi.fa.classified",
                                    "source_discovery": str(parent),
                                    "mask_parallelism": "RepeatMasker -pa 4; RMBlast documents four cores per worker",
                                    "score_method_root": "native/%s/RM2-recovery" % args.species}
        status.update({"status": "COMPLETED", "finished_epoch": time.time(),
                       "wall_seconds": time.time() - float(status["started_epoch"]),
                       "timing_scope": "classifier and RepeatMasker continuation only; parent discovery wall retained separately"})
        write_json(output / "status.json", status)
        summary_script = Path(__file__).with_name("summarize_native.py")
        summary = subprocess.run([sys.executable, str(summary_script), "--species", args.species,
                                  "--method", "RM2", "--output-dir", str(output)], cwd=str(summary_script.parent),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if summary.returncode != 0:
            status["annotation_summary_error"] = summary.stderr[-4000:]
            write_json(output / "status.json", status)
            raise RuntimeError("native output summary failed with return code %s" % summary.returncode)
        return status
    except Exception as exc:
        status.update({"status": "FAILED", "finished_epoch": time.time(),
                       "wall_seconds": time.time() - float(status["started_epoch"]),
                       "error": repr(exc),
                       "timing_scope": "classifier and RepeatMasker continuation only; parent discovery wall retained separately"})
        write_json(output / "status.json", status)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=PARENT_CONFIG)
    parser.add_argument("--species", required=True, choices=("chicken", "zebrafish"))
    parser.add_argument("--output-suffix", default="recovery",
                        help="fresh native output suffix after RM2- (never reuse a prior attempt)")
    recover(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
