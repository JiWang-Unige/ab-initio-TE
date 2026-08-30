#!/usr/bin/env python3
"""Run the Human hs1 chr17 HiTE engineering pilot.

The pilot crops the same ``chr17:0-9,830,400`` prefix represented by the
first 1,200 Human 8192-bp test windows, runs the pinned HiTE image, converts
its GFF to the LEMMI canonical interval format, and evaluates it against the
same Human RepeatMasker-style comparator and unknown mask.  The result is an
engineering comparison, not an independent biological truth claim.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterator


CHROM = "chr17"
PREFIX_END = 9_830_400
CANONICAL_FIELDS = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]


def fasta_records(path: Path) -> Iterator[tuple[str, str]]:
    name: str | None = None
    chunks: list[str] = []
    with path.open("r", encoding="ascii") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks)
                name = line[1:].split()[0]
                if not name:
                    raise ValueError(f"empty FASTA name at line {line_no}")
                chunks = []
            elif name is None:
                raise ValueError(f"FASTA sequence precedes header at line {line_no}")
            else:
                chunks.append(line)
        if name is not None:
            yield name, "".join(chunks)


def crop_fasta(path: Path, output: Path, seqid: str = CHROM, end: int = PREFIX_END) -> int:
    """Write one exact prefix FASTA record and return its length."""
    sequence = None
    for name, candidate in fasta_records(path):
        if name == seqid:
            sequence = candidate
            break
    if sequence is None:
        raise ValueError(f"expected a FASTA record named {seqid}")
    if len(sequence) < end:
        raise ValueError(f"{seqid} is shorter than the fixed prefix {end}")
    piece = sequence[:end]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="ascii") as handle:
        handle.write(f">{seqid}\n")
        for start in range(0, len(piece), 80):
            handle.write(piece[start:start + 80] + "\n")
    return len(piece)


def bed_rows(path: Path) -> Iterator[list[str]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip() or raw.startswith(("#", "track", "browser")):
                continue
            columns = raw.rstrip("\n").split("\t")
            if len(columns) < 3:
                raise ValueError(f"BED row {line_no} has fewer than 3 columns")
            start, finish = int(columns[1]), int(columns[2])
            if start < 0 or finish <= start:
                raise ValueError(f"BED row {line_no} has invalid half-open coordinates")
            yield columns


def crop_bed(path: Path, output: Path, seqid: str = CHROM, end: int = PREFIX_END) -> int:
    """Crop a zero-based half-open BED to the fixed prefix."""
    count = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for columns in bed_rows(path):
            if columns[0] != seqid:
                continue
            start, finish = int(columns[1]), int(columns[2])
            clipped_start, clipped_end = max(0, start), min(end, finish)
            if clipped_start >= clipped_end:
                continue
            columns[1], columns[2] = str(clipped_start), str(clipped_end)
            if len(columns) >= 6 and columns[5] == "C":
                columns[5] = "-"
            handle.write("\t".join(columns) + "\n")
            count += 1
    return count


def unknown_rows(strict_bed: Path, plus_unknown_bed: Path) -> list[list[str]]:
    """Return the plus-unknown rows absent from strict TE annotation."""
    strict = {tuple(columns) for columns in bed_rows(strict_bed)}
    return [columns for columns in bed_rows(plus_unknown_bed) if tuple(columns) not in strict]


def write_bed_rows(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for columns in rows:
            handle.write("\t".join(columns) + "\n")


def build_hite_command(sif: Path, work: Path, threads: int) -> list[str]:
    if threads < 1:
        raise ValueError("HiTE threads must be positive")
    return [
        "apptainer", "exec", "--cleanenv", "--bind", f"{work}:/work", str(sif),
        "env", "HOME=/work/home", "TMPDIR=/work/tmp",
        "http_proxy=http://127.0.0.1:9", "https_proxy=http://127.0.0.1:9",
        "ftp_proxy=http://127.0.0.1:9", "all_proxy=socks5://127.0.0.1:9",
        "HTTP_PROXY=http://127.0.0.1:9", "HTTPS_PROXY=http://127.0.0.1:9",
        "FTP_PROXY=http://127.0.0.1:9", "ALL_PROXY=socks5://127.0.0.1:9",
        "NO_PROXY=localhost,127.0.0.1", "no_proxy=localhost,127.0.0.1",
        "python", "/HiTE/main.py", "--genome", "/work/input/hite.fa",
        "--thread", str(threads), "--plant", "0", "--annotate", "1", "--out_dir", "/work/hite",
    ]


def load_adapter(root: Path):
    path = root / "scripts" / "experiments" / "LEMMI-TE-BENCH-20260824-R1" / "adapter.py"
    spec = importlib.util.spec_from_file_location("lemmi_te_adapter_hite_pilot", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load LEMMI adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _intervals(rows: list[tuple[str, int, int]]) -> list[tuple[int, int]]:
    return sorted((start, end) for seqid, start, end in rows if seqid == CHROM)


def subtract_unknown(interval: tuple[int, int], unknown: list[tuple[int, int]]) -> list[tuple[int, int]]:
    start, end = interval
    pieces: list[tuple[int, int]] = []
    cursor = start
    for unknown_start, unknown_end in unknown:
        if unknown_end <= cursor:
            continue
        if unknown_start >= end:
            break
        if unknown_start > cursor:
            pieces.append((cursor, min(unknown_start, end)))
        cursor = max(cursor, unknown_end)
        if cursor >= end:
            break
    if cursor < end:
        pieces.append((cursor, end))
    return pieces


def _write_rows(path: Path, rows: list[tuple[str, int, int]], name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for seqid, start, end in rows:
            writer.writerow({
                "seqid": seqid, "start": start, "end": end, "name": name,
                "score": "0", "strand": ".", "source": "TE-STRUCTURE-H1", "attributes": ".",
            })


def masked_evaluate(adapter, truth: Path, prediction: Path, unknown: Path, lengths: dict[str, int], work: Path) -> dict[str, Any]:
    truth_rows = adapter.read_canonical(truth)
    prediction_rows = adapter.read_canonical(prediction)
    unknown_rows_canonical = adapter.read_canonical(unknown)
    unknown_intervals = _intervals(unknown_rows_canonical)
    clipped_truth: list[tuple[str, int, int]] = []
    clipped_prediction: list[tuple[str, int, int]] = []
    for seqid, start, end in truth_rows:
        clipped_truth.extend((seqid, piece_start, piece_end) for piece_start, piece_end in subtract_unknown((start, end), unknown_intervals))
    for seqid, start, end in prediction_rows:
        clipped_prediction.extend((seqid, piece_start, piece_end) for piece_start, piece_end in subtract_unknown((start, end), unknown_intervals))
    masked_truth = work / "truth.masked.canonical.tsv"
    masked_prediction = work / f"{prediction.stem}.masked.canonical.tsv"
    _write_rows(masked_truth, clipped_truth, "human_reference_te")
    _write_rows(masked_prediction, clipped_prediction, prediction.stem)
    raw = adapter.evaluate(
        masked_truth, masked_prediction, lengths, iou_threshold=0.8,
        boundary_tol_bp=5, truth_tier="T0", overlap_policy="flat_union",
    )
    boundary_25 = adapter.evaluate(
        masked_truth, masked_prediction, lengths, iou_threshold=0.8,
        boundary_tol_bp=25, truth_tier="T0", overlap_policy="flat_union",
    )
    for key in ("boundary_hits", "boundary_precision", "boundary_recall", "boundary_f1"):
        raw[f"{key}_at_25bp"] = boundary_25[key]
    unknown_bp = sum(end - start for _seqid, start, end in unknown_rows_canonical)
    truth_mask = bytearray(lengths[CHROM])
    prediction_mask = bytearray(lengths[CHROM])
    unknown_mask = bytearray(lengths[CHROM])
    for _seqid, start, end in truth_rows:
        truth_mask[start:end] = b"\x01" * (end - start)
    for _seqid, start, end in prediction_rows:
        prediction_mask[start:end] = b"\x01" * (end - start)
    for _seqid, start, end in unknown_rows_canonical:
        unknown_mask[start:end] = b"\x01" * (end - start)
    known = [index for index, value in enumerate(unknown_mask) if not value]
    tp = sum(truth_mask[index] and prediction_mask[index] for index in known)
    fp = sum((not truth_mask[index]) and prediction_mask[index] for index in known)
    fn = sum(truth_mask[index] and (not prediction_mask[index]) for index in known)
    tn = sum((not truth_mask[index]) and (not prediction_mask[index]) for index in known)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    raw.update({
        "bp_n": len(known), "bp_tp": tp, "bp_fp": fp, "bp_fn": fn, "bp_tn": tn,
        "bp_precision": precision, "bp_recall": recall,
        "bp_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "ignored_bp": unknown_bp,
        "unknown_mask": str(unknown),
        "masked_truth": str(masked_truth),
        "masked_prediction": str(masked_prediction),
    })
    return raw


def parse_model_prediction(items: list[str] | None) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError("model predictions must use name=/absolute/path syntax")
        name, path = item.split("=", 1)
        if not name or name in result or not path.startswith("/"):
            raise ValueError("model prediction names must be unique and paths absolute")
        result[name] = Path(path)
    return result


def scratch_workdir(output_root: Path) -> Path:
    scratch_text = os.environ.get("HITE_NODE_SCRATCH")
    if not scratch_text:
        raise RuntimeError("HITE_NODE_SCRATCH is required for the HiTE pilot")
    scratch_root = Path(scratch_text)
    if not scratch_root.is_dir():
        raise FileNotFoundError(f"HITE_NODE_SCRATCH is not a directory: {scratch_root}")
    return scratch_root / output_root.name


def persist_native_output(work: Path, output_root: Path) -> Path:
    destination = output_root / "native"
    shutil.copytree(work / "hite", destination)
    return destination


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.project_root.resolve()
    if not args.assembly.is_file() or not args.strict_bed.is_file() or not args.plus_unknown_bed.is_file() or not args.sif.is_file():
        raise FileNotFoundError("assembly, strict BED, plus-unknown BED and HiTE SIF are all required")
    if args.threads < 1:
        raise ValueError("threads must be positive")
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=False)
    work = scratch_workdir(output_root)
    work.mkdir(parents=True)
    input_dir = work / "input"
    input_dir.mkdir(parents=True)
    work.joinpath("home").mkdir()
    work.joinpath("tmp").mkdir()
    work.joinpath("hite").mkdir()
    fasta = input_dir / "hite.fa"
    truth_bed = input_dir / "truth.bed"
    unknown_bed = input_dir / "unknown.bed"
    lengths_path = input_dir / "lengths.json"
    if crop_fasta(args.assembly, fasta) != PREFIX_END:
        raise ValueError("cropped FASTA length does not equal fixed prefix")
    strict_rows = crop_bed(args.strict_bed, truth_bed)
    unknown_all = unknown_rows(args.strict_bed, args.plus_unknown_bed)
    write_bed_rows(unknown_bed, [row for row in unknown_all if row[0] == CHROM and int(row[1]) < PREFIX_END and int(row[2]) > 0])
    unknown_rows_count = crop_bed(unknown_bed, input_dir / "unknown.crop.bed")
    unknown_bed = input_dir / "unknown.crop.bed"
    if strict_rows == 0:
        raise ValueError("fixed chr17 prefix has no strict Human TE comparator rows")
    lengths = {CHROM: PREFIX_END}
    lengths_path.write_text(json.dumps(lengths, indent=2) + "\n", encoding="utf-8")
    command = build_hite_command(args.sif, work, args.threads)
    hite_log = work / "hite.command.log"
    with hite_log.open("w", encoding="utf-8") as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
    persisted_hite_log = output_root / "hite.command.log"
    shutil.copy2(hite_log, persisted_hite_log)
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)
    hite_gff = work / "hite" / "HiTE.gff"
    if not hite_gff.is_file() or hite_gff.stat().st_size == 0:
        raise FileNotFoundError(f"HiTE did not produce a non-empty expected GFF: {hite_gff}")
    persisted_hite_gff = output_root / "HiTE.gff"
    shutil.copy2(hite_gff, persisted_hite_gff)
    persisted_native = None
    if args.persist_native_output:
        persisted_native = persist_native_output(work, output_root)
    adapter = load_adapter(root)
    truth_canonical = output_root / "truth.canonical.tsv"
    unknown_canonical = output_root / "unknown.canonical.tsv"
    hite_canonical = output_root / "hite.canonical.tsv"
    adapter.convert(truth_bed, truth_canonical, "bed")
    adapter.convert(unknown_bed, unknown_canonical, "bed")
    adapter.convert(hite_gff, hite_canonical, "gff3")
    methods: dict[str, Any] = {"hite": masked_evaluate(adapter, truth_canonical, hite_canonical, unknown_canonical, lengths, work)}
    for name, prediction in parse_model_prediction(args.model_prediction).items():
        methods[name] = masked_evaluate(adapter, truth_canonical, prediction, unknown_canonical, lengths, work)
    result = {
        "status": "ENGINEERING_PASS",
        "profile": "TE-STRUCTURE-PILOT-20260825-R1-HITE-CHR17",
        "claim_eligible": False,
        "claim_scope": "RepeatMasker-comparator agreement only",
        "truth_is_independent_biological_gold": False,
        "coordinate_convention": "zero_based_half_open",
        "prefix": {"seqid": CHROM, "start": 0, "end": PREFIX_END, "windows": 1200, "window_bp": 8192},
        "inputs": {
            "assembly": str(args.assembly), "strict_bed": str(args.strict_bed),
            "plus_unknown_bed": str(args.plus_unknown_bed), "hite_sif": str(args.sif),
            "strict_rows_in_prefix": strict_rows, "unknown_rows_in_prefix": unknown_rows_count,
        },
        "artifacts": {
            "truth_canonical": str(truth_canonical), "unknown_canonical": str(unknown_canonical),
            "hite_gff": str(persisted_hite_gff), "hite_canonical": str(hite_canonical),
            "command_log": str(persisted_hite_log),
            "native_output": str(persisted_native) if persisted_native else None,
        },
        "runtime": {
            "scratch_workdir": str(work), "prefix_fasta": str(fasta),
            "truth_bed": str(truth_bed), "unknown_bed": str(unknown_bed),
        },
        "command": {"argv": command, "shell": shlex.join(command), "log": str(persisted_hite_log), "threads": args.threads},
        "methods": methods,
        "same_truth_and_unknown_mask": True,
    }
    (output_root / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--strict-bed", type=Path, required=True)
    parser.add_argument("--plus-unknown-bed", type=Path, required=True)
    parser.add_argument("--sif", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "40")))
    parser.add_argument("--model-prediction", action="append")
    parser.add_argument("--persist-native-output", action="store_true")
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
