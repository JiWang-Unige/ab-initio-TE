#!/usr/bin/env python3
"""Compare portable D outputs with the historical D loader on synthetic FASTA.

This validator is intentionally separate from the portable package: it imports
the supplied historical helper only to establish loader parity. It reads no
labels, reference annotation, CONF or reserved species data.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_synthetic_fasta(path: Path) -> list[tuple[str, str]]:
    records = [
        ("chr4096", "ACGT" * 1024),
        ("tail9", "ACGTACGTN"),
        ("tail5", "RYACG"),
    ]
    path.write_text("".join(f">{name}\n{sequence}\n" for name, sequence in records))
    return records


def read_fasta(path: Path) -> list[tuple[str, str]]:
    """Read a small, sequence-only FASTA fixture without labels or metadata."""
    records: list[tuple[str, str]] = []
    name: Optional[str] = None
    parts: list[str] = []
    allowed = set("ACGTRYSWKMBDHVN")
    for line_number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                if not parts:
                    raise ValueError(f"empty FASTA contig: {name}")
                records.append((name, "".join(parts)))
            header = line[1:].split()
            if not header:
                raise ValueError(f"empty FASTA header at line {line_number}")
            name = header[0]
            parts = []
        else:
            if name is None:
                raise ValueError(f"sequence before FASTA header at line {line_number}")
            sequence = line.upper()
            invalid = set(sequence) - allowed
            if invalid:
                raise ValueError(f"unsupported DNA symbols at line {line_number}: {sorted(invalid)}")
            parts.append(sequence)
    if name is not None:
        if not parts:
            raise ValueError(f"empty FASTA contig: {name}")
        records.append((name, "".join(parts)))
    if not records:
        raise ValueError(f"empty FASTA input: {path}")
    if len({name for name, _ in records}) != len(records):
        raise ValueError("duplicate FASTA contig name")
    return records


def read_probability_track(path: Path, records: list[tuple[str, str]]) -> dict[str, np.ndarray]:
    values = {name: np.empty(len(sequence), dtype=np.float64) for name, sequence in records}
    covered = {name: np.zeros(len(sequence), dtype=bool) for name, sequence in records}
    for line in path.read_text().splitlines():
        name, left, right, value = line.split("\t")
        left, right = int(left), int(right)
        values[name][left:right] = float(value)
        covered[name][left:right] = True
    if not all(bool(mask.all()) for mask in covered.values()):
        raise AssertionError("probability bedGraph does not cover every input base")
    return values


def read_material_mask(path: Path, records: list[tuple[str, str]]) -> dict[str, np.ndarray]:
    masks = {name: np.zeros(len(sequence), dtype=bool) for name, sequence in records}
    for line in path.read_text().splitlines():
        name, left, right = line.split("\t")
        masks[name][int(left) : int(right)] = True
    return masks


def read_softmasked(path: Path, records: list[tuple[str, str]]) -> dict[str, str]:
    observed: dict[str, list[str]] = {}
    name = None
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            name = line[1:].split()[0]
            observed.setdefault(name, [])
        elif line:
            if name is None:
                raise AssertionError("softmasked FASTA sequence precedes a header")
            observed[name].append(line.strip())
    return {name: "".join(observed.get(name, [])) for name, _ in records}


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    portable_root = args.portable_root.resolve()
    sys.path.insert(0, str(portable_root))
    from portable_d import fasta as portable_fasta
    from portable_d.bundle import Bundle
    from portable_d.model import sigmoid as portable_sigmoid

    historical = load_module(args.original_helper.resolve(), "historical_l1_eval")
    if args.input_fasta is None:
        input_fasta = args.output_dir / "synthetic.fa"
        records = write_synthetic_fasta(input_fasta)
        input_kind = "synthetic"
    else:
        input_fasta = args.input_fasta.resolve()
        records = read_fasta(input_fasta)
        input_kind = "sequence-only external fixture"
    sequences = [sequence for _, sequence in records]
    # Copy only the small bundle files. The checkpoint is represented by a
    # symlink in this temporary staging directory and is never copied to Mac.
    with tempfile.TemporaryDirectory(prefix="portable_d_bundle_", dir=str(args.output_dir)) as temp:
        staged_root = Path(temp)
        staged_bundle = staged_root / "bundle"
        shutil.copytree(portable_root / "bundle", staged_bundle)
        weights = staged_bundle / "model" / "pytorch_model.bin"
        weights.symlink_to(args.original_model_dir.resolve() / "pytorch_model.bin")
        bundle = Bundle.load(staged_bundle)

        captured: list[np.ndarray] = []
        historical_infer = portable_fasta.infer_half_margins

        def capture(*values, **kwargs):
            margins = historical_infer(*values, **kwargs)
            captured.extend(np.asarray(margin).copy() for margin in margins)
            return margins

        portable_fasta.infer_half_margins = capture
        prediction_dir = args.output_dir / "prediction"
        summary = portable_fasta.run(
            bundle,
            input_fasta,
            prediction_dir,
            device=args.device,
            batch_size=args.batch_size,
            cpu_threads=args.cpu_threads,
        )

    if len(captured) != len(records):
        raise AssertionError(f"expected {len(records)} portable windows, observed {len(captured)}")

    original_model, original_tokenizer, original_device = historical.load_final_model(
        args.original_model_dir,
        args.original_tokenizer_dir,
        args.device == "cpu",
        args.original_code_dir,
    )
    original_margins = historical.infer_half_margins(
        original_model, original_tokenizer, original_device, sequences, args.batch_size
    )
    if len(original_margins) != len(captured):
        raise AssertionError("historical and portable window counts differ")

    slope = float(bundle.calibration["platt_slope"])
    intercept = float(bundle.calibration["platt_intercept"])
    threshold = float(bundle.calibration["threshold"])
    margin_diffs = [
        float(np.max(np.abs(left.astype(np.float64) - right.astype(np.float64))))
        for left, right in zip(captured, original_margins)
    ]
    portable_probabilities = [portable_sigmoid(slope * margin + intercept) for margin in captured]
    historical_probabilities = [portable_sigmoid(slope * margin + intercept) for margin in original_margins]
    probability_diffs = [
        float(np.max(np.abs(left - right)))
        for left, right in zip(portable_probabilities, historical_probabilities)
    ]
    portable_masks = [values >= threshold for values in portable_probabilities]
    historical_masks = [values >= threshold for values in historical_probabilities]
    mask_equal = all(np.array_equal(left, right) for left, right in zip(portable_masks, historical_masks))
    if max(margin_diffs) > args.margin_tolerance:
        raise AssertionError(f"margin mismatch exceeds tolerance: {max(margin_diffs)}")
    if max(probability_diffs) > args.probability_tolerance:
        raise AssertionError(f"probability mismatch exceeds tolerance: {max(probability_diffs)}")
    if not mask_equal:
        raise AssertionError("threshold material masks differ")

    track_probabilities = read_probability_track(
        prediction_dir / "material_probability.bedGraph", records
    )
    track_masks = read_material_mask(prediction_dir / "material_runs.bed", records)
    track_probability_diffs = []
    track_mask_equal = True
    for (name, _), probability, mask in zip(records, portable_probabilities, portable_masks):
        track_probability_diffs.append(float(np.max(np.abs(track_probabilities[name] - probability))))
        track_mask_equal &= bool(np.array_equal(track_masks[name], mask))
    if max(track_probability_diffs) > 0.0:
        raise AssertionError("portable probability track differs from captured portable margins")
    if not track_mask_equal:
        raise AssertionError("portable material BED differs from captured portable margins")
    softmasked = read_softmasked(prediction_dir / "softmasked.fa", records)
    softmask_equal = True
    for (name, sequence), mask in zip(records, portable_masks):
        expected = "".join(
            base.lower() if flag and base in "ACGT" else base.upper()
            for base, flag in zip(sequence, mask)
        )
        softmask_equal &= softmasked[name] == expected
    if not softmask_equal:
        raise AssertionError("softmasked FASTA does not preserve the canonical-base contract")

    portable_positive_bp = [int(mask.sum()) for mask in portable_masks]
    historical_positive_bp = [int(mask.sum()) for mask in historical_masks]
    result = {
        "status": "PASS",
        "protocol": "PORTABLE-D-SMOKE-20260917",
        "scope": f"{input_kind} loader parity; no accuracy/generalization endpoint",
        "model_id": bundle.manifest["model_id"],
        "device": summary["device"],
        "window_lengths_bp": [len(sequence) for _, sequence in records],
        "input_bp": sum(len(sequence) for _, sequence in records),
        "input_fasta": str(input_fasta),
        "material_positive_bp_by_window": portable_positive_bp,
        "portable_material_positive_bp": sum(portable_positive_bp),
        "historical_material_positive_bp": sum(historical_positive_bp),
        "material_mask_nonempty": bool(sum(portable_positive_bp) > 0),
        "portable_windows": len(captured),
        "historical_windows": len(original_margins),
        "margin_max_abs_diff_by_window": margin_diffs,
        "probability_max_abs_diff_by_window": probability_diffs,
        "probability_track_max_abs_diff": max(track_probability_diffs),
        "probability_track_exact_from_portable_margins": max(track_probability_diffs) == 0.0,
        "material_mask_equal": mask_equal and track_mask_equal,
        "softmask_canonical_only": True,
        "softmask_equal": softmask_equal,
        "margin_tolerance": args.margin_tolerance,
        "probability_tolerance": args.probability_tolerance,
        "tail_windows_included": [9, 5] if args.input_fasta is None else [],
        "calibration_threshold": threshold,
        "labels_read": False,
        "reference_annotation_read": False,
        "portable_summary": str((prediction_dir / "summary.json").resolve()),
    }
    (args.output_dir / "smoke_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portable-root", type=Path, required=True)
    parser.add_argument("--original-model-dir", type=Path, required=True)
    parser.add_argument("--original-tokenizer-dir", type=Path)
    parser.add_argument("--original-code-dir", type=Path, required=True)
    parser.add_argument("--original-helper", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--input-fasta",
        type=Path,
        help="Optional sequence-only FASTA fixture; default is the synthetic 4096/9/5-bp fixture",
    )
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--cpu-threads", type=int, default=4)
    parser.add_argument("--margin-tolerance", type=float, default=3e-6)
    parser.add_argument("--probability-tolerance", type=float, default=1e-6)
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    if arguments.original_tokenizer_dir is None:
        arguments.original_tokenizer_dir = arguments.original_model_dir
    print(json.dumps(run(arguments), indent=2, sort_keys=True))
