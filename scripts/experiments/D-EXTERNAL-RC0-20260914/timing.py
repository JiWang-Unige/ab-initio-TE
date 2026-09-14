#!/usr/bin/env python3
"""Measure cold and warm inference throughput on the first fixed RC0 region."""
from __future__ import annotations

import argparse
import json
import os
import platform
import time
import traceback
from pathlib import Path

import rc0  # resolved from this experiment directory when run as a script


def _hardware(device: object) -> dict[str, object]:
    """Record the execution host and accelerator when the timing is run."""
    result: dict[str, object] = {
        "hostname": platform.node(),
        "arch": platform.machine(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_job_node": os.environ.get("SLURMD_NODENAME"),
        "slurm_nodelist": os.environ.get("SLURM_JOB_NODELIST"),
    }
    if str(device).startswith("cuda"):
        import torch

        index = torch.cuda.current_device()
        result.update(
            {
                "accelerator": torch.cuda.get_device_name(index),
                "cuda_version": torch.version.cuda,
                "device_index": index,
            }
        )
    else:
        result["cpu_model"] = platform.processor()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--candidate", required=True, choices=["platypus", "sea_urchin", "c_briggsae"])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-root", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--tokenizer-dir", type=Path)
    parser.add_argument("--model-code-dir", type=Path)
    parser.add_argument("--calibration-json", type=Path)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--cpu", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    config = rc0._read_json(args.config.resolve())
    candidate = rc0._candidate(config, args.candidate)
    rc0._check_panel(config, candidate)
    remote_root = Path(args.remote_root or config["remote_root"])
    fasta = rc0._resolve_path(remote_root, str(candidate["fasta"]))
    assert fasta is not None
    if not fasta.is_file():
        raise FileNotFoundError(f"required FASTA missing: {fasta}")
    if args.batch_size < 1:
        raise ValueError("batch size must be positive")
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    first = candidate["regions"][0]
    source_seqid = str(first["seqid"])
    contig = rc0._selected_contigs(fasta, {source_seqid})[source_seqid]
    sequence = contig[int(first["start_bp"]) : int(first["end_bp"])]
    if len(sequence) != int(first["end_bp"]) - int(first["start_bp"]):
        raise ValueError("timing panel slice has wrong length")
    model, tokenizer, device, calibration, load_seconds, model_paths = rc0._load_model(config, args)
    slope = float(calibration["platt_slope"])
    intercept = float(calibration["platt_intercept"])
    timings: list[float] = []
    for repetition in range(2):
        rc0._sync(device)
        start = time.perf_counter()
        values = rc0._infer_sequence(
            sequence, model, tokenizer, device, args.batch_size, slope, intercept
        )
        rc0._sync(device)
        elapsed = time.perf_counter() - start
        if len(values) != len(sequence):
            raise ValueError("timing inference returned wrong length")
        timings.append(elapsed)
    result = {
        "protocol": "D-EXTERNAL-RC0-20260914-CPU-GPU-TIMING",
        "status": "COMPLETED",
        "scientific_scope": "timing only; no accuracy or model-selection endpoint",
        "candidate": candidate["id"],
        "species": candidate["species"],
        "assembly": candidate["assembly"],
        "region": {
            "seqid": source_seqid,
            "start_bp": int(first["start_bp"]),
            "end_bp": int(first["end_bp"]),
            "length_bp": len(sequence),
            "fixed_panel_region_index": 1,
        },
        "model": {
            "seed": int(calibration["seed"]),
            "threshold": float(calibration["threshold"]),
            "calibration_scope": calibration["calibration_scope"],
            "device": str(device),
            "cpu_flag": bool(args.cpu),
            "batch_size": args.batch_size,
            "paths": model_paths,
            "model_load_seconds": load_seconds,
        },
        "hardware": _hardware(device),
        "timing": {
            "cold_forward_seconds": timings[0],
            "warm_forward_seconds": timings[1],
            "windows": (len(sequence) + rc0.WINDOW_BP - 1) // rc0.WINDOW_BP,
            "input_bp": len(sequence),
            "cold_bp_per_second": len(sequence) / timings[0] if timings[0] else None,
            "warm_bp_per_second": len(sequence) / timings[1] if timings[1] else None,
        },
        "panel_selection": config["selection_rule"],
    }
    (output_dir / "timing.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "STATUS.json").write_text(json.dumps({"status": "COMPLETED"}, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "STATUS.json").write_text(
            json.dumps({"status": "FAILED", "error": str(exc), "traceback": traceback.format_exc()}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        raise
    print(json.dumps({"status": result["status"], "candidate": result["candidate"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
