#!/usr/bin/env python3
"""Run the frozen sequence-only D model on a full assembly or fixed CPU pilot."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Dict

from common import ensure_empty_output, fasta_stats, file_metadata, run_timed, slurm_context, host_context, write_first_prefix, write_json


ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "configs/WHOLE-GENOME-BENCHMARK-20260918.json"
INFER = ROOT / "scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/infer_fasta.py"


def run(args: argparse.Namespace) -> Dict[str, object]:
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    species_cfg = config["species"][args.species]
    d_cfg = config["methods"]["D"]
    if args.mode == "cpu_pilot":
        output_mode = "cpu_pilot"
    else:
        output_mode = args.mode
    output = (args.output_dir.resolve() if args.output_dir is not None else
              ROOT / "outputs/WHOLE-GENOME-BENCHMARK-20260918/d" / args.species / output_mode).resolve()
    ensure_empty_output(output)
    source = Path(species_cfg["fasta"])
    if not source.is_file():
        raise FileNotFoundError("frozen source FASTA missing: %s" % source)
    source_stats = fasta_stats(source)
    fasta = source
    pilot_region = None
    pilot_record = species_cfg.get("cpu_pilot_record")
    if args.mode == "cpu_pilot":
        fasta = output / "pilot.fa"
        pilot_region = write_first_prefix(source, fasta, args.pilot_bp, pilot_record)
    status: Dict[str, object] = {
        "protocol": "WHOLE-GENOME-BENCHMARK-20260918", "species": args.species,
        "mode": args.mode, "status": "RUNNING", "started_epoch": time.time(),
        "source_fasta_metadata": file_metadata(source), "source_stats": source_stats,
        "inference_fasta_metadata": file_metadata(fasta), "pilot_region": pilot_region,
        "model": {"model_dir": d_cfg["model_dir"], "tokenizer_dir": d_cfg["tokenizer_dir"],
                  "model_code_dir": d_cfg["model_code_dir"], "calibration_json": d_cfg["calibration_json"],
                  "window_bp": d_cfg["window_bp"], "batch_size": d_cfg["batch_size"],
                  "threshold_policy": d_cfg["threshold_policy"]},
        "host": host_context(), "slurm": slurm_context(),
        "labels_used": False, "scientific_metrics_computed": False,
        "input_contract": "fixed source FASTA; no labels, score, or chromosome selection used by inference",
    }
    if pilot_region is not None:
        status["input_contract"] = "first complete 1,048,576-bp prefix of the frozen pilot contig, fixed before any labels or outputs"
    write_json(output / "status.json", status)
    env = os.environ.copy()
    allocated_cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", "1"))
    if allocated_cpus < 1:
        raise ValueError("SLURM_CPUS_PER_TASK must be positive")
    # Keep the CPU benchmark's declared allocation and actual Torch intra-op
    # parallelism aligned.  OpenBLAS remains single-threaded to avoid a second
    # nested pool; Torch inter-op work is fixed at one thread.
    env.update({"TOKENIZERS_PARALLELISM": "false",
                "OMP_NUM_THREADS": str(allocated_cpus),
                "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": str(allocated_cpus),
                "TEFM_TORCH_INTRA_THREADS": str(allocated_cpus),
                "TEFM_TORCH_INTER_THREADS": "1"})
    status["runtime_contract"] = {
        "allocated_cpus": allocated_cpus,
        "omp_num_threads": allocated_cpus,
        "mkl_num_threads": allocated_cpus,
        "openblas_num_threads": 1,
        "torch_intra_op_threads": allocated_cpus,
        "torch_inter_op_threads": 1,
        "dtype_policy": "load checkpoint dtype; no autocast or BF16/FP16 conversion",
    }
    try:
        prediction = output / "prediction"
        command = [sys.executable, str(INFER), "--fasta", str(fasta),
                   "--model-dir", str(d_cfg["model_dir"]), "--tokenizer-dir", str(d_cfg["tokenizer_dir"]),
                   "--model-code-dir", str(d_cfg["model_code_dir"]), "--calibration-json", str(d_cfg["calibration_json"]),
                   "--output-dir", str(prediction), "--batch-size", str(d_cfg["batch_size"])]
        if args.mode != "gpu":
            command.append("--cpu")
        stage = run_timed(command, output, "inference", env)
        status["timing"] = stage
        write_json(output / "status.json", status)
        if stage["returncode"] != 0:
            raise RuntimeError("D inference failed")
        summary_path = prediction / "summary.json"
        if not summary_path.exists():
            raise RuntimeError("D inference returned without summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("status") != "COMPLETED" or summary.get("labels_used") is not False:
            raise RuntimeError("D summary failed the label-free completion contract")
        expected_bp = args.pilot_bp if pilot_region is not None else source_stats["total_bp"]
        if summary.get("total_bp") != expected_bp:
            raise RuntimeError("D output bp does not match fixed input: %s != %s" % (summary.get("total_bp"), expected_bp))
        wall = float(stage["wall_seconds_observed"])
        status.update({"status": "COMPLETED", "finished_epoch": time.time(),
                       "wall_seconds": time.time() - float(status["started_epoch"]),
                       "prediction_summary": "prediction/summary.json",
                       "total_bp": summary["total_bp"],
                       "callable_bp_per_second_end_to_end": expected_bp / wall if wall else None,
                       "device": summary.get("device"),
                       "torch_runtime": summary.get("torch_runtime"),
                       "windows": sum(x.get("windows", 0) for x in summary.get("contigs", []))})
        write_json(output / "status.json", status)
        print(json.dumps({"status": "COMPLETED", "species": args.species, "mode": args.mode,
                          "bp": expected_bp, "wall_seconds": wall,
                          "bp_per_second": expected_bp / wall if wall else None}, sort_keys=True))
        return status
    except Exception as exc:
        status.update({"status": "FAILED", "finished_epoch": time.time(),
                       "wall_seconds": time.time() - float(status["started_epoch"]), "error": repr(exc)})
        write_json(output / "status.json", status)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--species", required=True, choices=("chicken", "zebrafish"))
    parser.add_argument("--mode", required=True, choices=("cpu_pilot", "cpu", "gpu"))
    parser.add_argument("--pilot-bp", type=int, default=1048576)
    parser.add_argument("--output-dir", type=Path,
                        help="optional fresh output directory for preserving an earlier attempt")
    run(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
