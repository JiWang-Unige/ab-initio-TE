#!/usr/bin/env python3
"""Materialize explicit regions and export frozen P3-R1 probability tracks."""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Callable, Iterable, Iterator

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
WINDOW = 8192
STRIDE = 8192
THRESHOLD = 0.5
CANONICAL_FIELDS = [
    "seqid", "start", "end", "name", "score", "strand", "source", "attributes",
]


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="ascii", errors="strict")
    return path.open("rt", encoding="ascii", errors="strict")


def iter_region_chunks(
    assembly: Path, seqid: str, region_start: int, region_end: int,
) -> Iterator[str]:
    """Stream sequence chunks overlapping one zero-based half-open region."""
    current: str | None = None
    position = 0
    emitted = 0
    with _open_text(assembly) as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current == seqid:
                    break
                current = line[1:].split()[0]
                position = 0
                continue
            if current != seqid:
                continue
            sequence = line.upper()
            line_start, line_end = position, position + len(sequence)
            left = max(region_start, line_start)
            right = min(region_end, line_end)
            if left < right:
                piece = sequence[left - line_start:right - line_start]
                emitted += len(piece)
                yield piece
            position = line_end
            if position >= region_end:
                break
    expected = region_end - region_start
    if emitted != expected:
        raise ValueError(
            f"region {seqid}:{region_start}-{region_end} yielded {emitted} bp, expected {expected}"
        )


def iter_region_rows(
    assembly: Path, seqid: str, region_start: int, region_end: int,
) -> Iterator[dict[str, object]]:
    """Yield tail-safe 8192/8192 inference rows for one explicit region."""
    buffer = ""
    next_start = region_start
    for chunk in iter_region_chunks(assembly, seqid, region_start, region_end):
        buffer += chunk
        while len(buffer) >= WINDOW:
            end = next_start + WINDOW
            yield {
                "chr": seqid,
                "start": next_start,
                "end": end,
                "sequence": buffer[:WINDOW],
                "labels": [0] * WINDOW,
            }
            buffer = buffer[STRIDE:]
            next_start += STRIDE
    if buffer:
        yield {
            "chr": seqid,
            "start": next_start,
            "end": region_end,
            "sequence": buffer,
            "labels": [0] * len(buffer),
        }


def write_region_jsonl(
    assembly: Path,
    seqid: str,
    region_start: int,
    region_end: int,
    output_jsonl: Path,
    manifest_path: Path,
) -> dict[str, object]:
    """Write one independent inference shard and its coordinate-coverage proof."""
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    windows = 0
    total_bp = 0
    tail_windows = 0
    next_start = region_start
    with gzip.open(output_jsonl, "wt", encoding="utf-8", newline="\n") as handle:
        for row in iter_region_rows(assembly, seqid, region_start, region_end):
            start, end = int(row["start"]), int(row["end"])
            if start != next_start:
                raise ValueError(f"non-contiguous region rows at {start}, expected {next_start}")
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
            windows += 1
            total_bp += end - start
            tail_windows += int(end - start < WINDOW)
            next_start = end
    expected_bp = region_end - region_start
    expected_windows = (expected_bp + WINDOW - 1) // WINDOW
    if next_start != region_end or total_bp != expected_bp or windows != expected_windows:
        raise ValueError("explicit-region coverage is incomplete")
    result: dict[str, object] = {
        "schema": "gap_bridge_e0_region_jsonl_v1",
        "status": "PASS",
        "assembly": str(assembly),
        "seqid": seqid,
        "region_start": region_start,
        "region_end": region_end,
        "window": WINDOW,
        "stride": STRIDE,
        "windows": windows,
        "expected_windows": expected_windows,
        "total_bp": total_bp,
        "missing_bp": 0,
        "overlap_bp": 0,
        "tail_windows": tail_windows,
        "coverage_complete": True,
        "label_mode": "all_zero_inference_only",
        "truth_read": False,
        "output_jsonl": str(output_jsonl),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def iter_jsonl(path: Path, max_windows: int | None = None) -> Iterator[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if max_windows is not None and index >= max_windows:
                break
            yield json.loads(line)


def stitch_track(
    rows: Iterable[dict[str, object]],
    infer_state_probability: Callable[[str], np.ndarray],
    weights: np.ndarray,
) -> tuple[str, int, np.ndarray, np.ndarray, np.ndarray, int]:
    """Stitch four states in float32, then derive P_TE and the known mask."""
    seqid: str | None = None
    region_start: int | None = None
    next_start: int | None = None
    state_sums = np.zeros((0, 4), dtype=np.float32)
    weight_sums = np.zeros(0, dtype=np.float32)
    known = np.zeros(0, dtype=bool)
    coverage = np.zeros(0, dtype=np.uint8)
    windows = 0
    for index, row in enumerate(rows):
        row_seqid = str(row["chr"])
        if seqid is None:
            seqid = row_seqid
        elif row_seqid != seqid:
            raise ValueError("one P3 export shard must contain exactly one seqid")
        start, end = int(row["start"]), int(row["end"])
        sequence = str(row["sequence"])
        labels = np.asarray(row["labels"], dtype=np.int16)
        length = end - start
        if start < 0 or length != len(sequence) or labels.shape != (length,):
            raise ValueError(f"row {index} sequence/label coordinates disagree")
        if region_start is None:
            region_start = start
            next_start = start
        if start != next_start:
            raise ValueError(f"{row_seqid} export input has missing or overlapping coordinates")
        relative_start = start - region_start
        relative_end = end - region_start
        state_probability = np.asarray(infer_state_probability(sequence), dtype=np.float32)
        if state_probability.shape != (length, 4):
            raise ValueError(f"row {index} state-probability shape disagrees with coordinates")
        if state_sums.shape[0] < relative_end:
            extension = relative_end - state_sums.shape[0]
            state_sums = np.pad(state_sums, ((0, extension), (0, 0)))
            weight_sums = np.pad(weight_sums, (0, extension))
            known = np.pad(known, (0, extension))
            coverage = np.pad(coverage, (0, extension))
        state_sums[relative_start:relative_end] += state_probability * weights[:length, None]
        weight_sums[relative_start:relative_end] += weights[:length]
        known[relative_start:relative_end] = labels >= 0
        coverage[relative_start:relative_end] += 1
        next_start = end
        windows += 1
    if seqid is None or region_start is None:
        raise ValueError("no inference rows")
    if not np.all(coverage == 1):
        raise ValueError(f"{seqid} export input has missing or overlapping coordinates")
    stitched_states = state_sums / weight_sums[:, None]
    p_te = np.sum(stitched_states[:, 1:4], axis=1, dtype=np.float32)
    return seqid, region_start, stitched_states, p_te, known, windows


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_canonical(path: Path, seqid: str, runs: Iterable[tuple[int, int]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for start, end in runs:
            writer.writerow({
                "seqid": seqid,
                "start": start,
                "end": end,
                "name": "P3_prediction",
                "score": ".",
                "strand": ".",
                "source": "P3",
                "attributes": ".",
            })
            count += 1
    return count


def write_probability_tracks(
    output_pte: Path,
    output_states: Path,
    p_te: np.ndarray,
    state_probability: np.ndarray,
) -> None:
    output_pte.parent.mkdir(parents=True, exist_ok=True)
    output_states.parent.mkdir(parents=True, exist_ok=True)
    with output_pte.open("wb") as handle:
        np.save(handle, p_te.astype(np.float32, copy=False), allow_pickle=False)
    with output_states.open("wb") as handle:
        np.save(handle, state_probability.astype(np.float16), allow_pickle=False)


def export_frozen_p3(
    model_dir: Path,
    data_jsonl: Path,
    output_pte: Path,
    output_states: Path,
    output_canonical: Path,
    manifest_path: Path,
    max_windows: int | None,
) -> dict[str, object]:
    """Export four stitched states and derived P_TE without scientific metrics."""
    c5 = _load_module(
        ROOT / "scripts/experiments/C5-HYBRID-PILOT-20260830/c5_hybrid_pilot.py",
        "gap_bridge_e0_c5",
    )
    strict = c5._strict_module()
    model, tokenizer, metadata, device, te = c5.load_p3_model(model_dir)
    weights = strict.center_weights(WINDOW, "triangular")

    def infer(sequence: str) -> np.ndarray:
        import torch

        encoded = tokenizer(
            sequence[:WINDOW], add_special_tokens=False, truncation=True,
            max_length=WINDOW, padding="max_length", return_tensors="pt",
        )
        inputs = {
            key: value.to(device)
            for key, value in encoded.items()
            if key in {"input_ids", "attention_mask"}
        }
        with torch.no_grad():
            logits = model(**inputs).logits
            state_probability = torch.softmax(logits, dim=-1)[0].detach().cpu().numpy()
        return state_probability[:len(sequence)]

    seqid, region_start, state_probability, probability, known, windows = stitch_track(
        iter_jsonl(data_jsonl, max_windows), infer, weights,
    )
    prediction = (probability >= THRESHOLD) & known
    runs = strict.runs_from_bool(prediction)
    write_probability_tracks(output_pte, output_states, probability, state_probability)
    interval_count = write_canonical(
        output_canonical, seqid,
        ((start + region_start, end + region_start) for start, end in runs),
    )
    result: dict[str, object] = {
        "schema": "gap_bridge_e0_p3_export_v1",
        "status": "PASS",
        "model_dir": str(model_dir),
        "model_schema": metadata["schema"],
        "data_jsonl": str(data_jsonl),
        "seqid": seqid,
        "region_start": region_start,
        "region_end": region_start + int(probability.size),
        "length": int(probability.size),
        "windows": windows,
        "window": WINDOW,
        "stride": STRIDE,
        "weight_mode": "triangular",
        "threshold": THRESHOLD,
        "probability_dtype": str(probability.dtype),
        "state_probability_dtype": "float16",
        "state_probability_shape": list(state_probability.shape),
        "state_order": ["background", "interior", "left_boundary", "right_boundary"],
        "known_bp": int(known.sum()),
        "unknown_bp": int((~known).sum()),
        "prediction_intervals": interval_count,
        "scientific_metrics_computed": False,
        "output_pte": str(output_pte),
        "output_states": str(output_states),
        "output_canonical": str(output_canonical),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def stitch_chunk_exports(
    chunk_root: Path,
    seqid: str,
    expected_length: int,
    output_region_jsonl: Path,
    output_region_manifest: Path,
    output_pte: Path,
    output_states: Path,
    output_canonical: Path,
    output_export_manifest: Path,
) -> dict[str, object]:
    """Join aligned shard exports without changing whole-chromosome geometry."""
    chunks: list[tuple[int, int, Path, dict[str, object], dict[str, object]]] = []
    for path in chunk_root.iterdir():
        if not path.is_dir():
            continue
        region = json.loads((path / "region.manifest.json").read_text(encoding="utf-8"))
        export = json.loads((path / "export.manifest.json").read_text(encoding="utf-8"))
        chunks.append((int(region["region_start"]), int(region["region_end"]), path, region, export))
    chunks.sort(key=lambda item: item[0])
    if not chunks:
        raise ValueError(f"no chunk exports under {chunk_root}")

    next_start = 0
    total_windows = 0
    tail_windows = 0
    known_bp = 0
    model_schema = None
    for start, end, path, region, export in chunks:
        if start != next_start or end <= start:
            raise ValueError(f"{seqid} chunks have missing or overlapping coordinates")
        if region["status"] != "PASS" or export["status"] != "PASS":
            raise ValueError(f"non-PASS chunk: {path}")
        if region["seqid"] != seqid or export["seqid"] != seqid:
            raise ValueError(f"wrong seqid in chunk: {path}")
        if int(export["region_start"]) != start or int(export["region_end"]) != end:
            raise ValueError(f"region/export coordinate mismatch: {path}")
        if end < expected_length and end % WINDOW != 0:
            raise ValueError(f"internal chunk boundary is not {WINDOW}-bp aligned: {end}")
        if int(export["length"]) != end - start:
            raise ValueError(f"track length mismatch: {path}")
        schema = str(export["model_schema"])
        if model_schema is None:
            model_schema = schema
        elif model_schema != schema:
            raise ValueError("chunk model schemas differ")
        next_start = end
        total_windows += int(region["windows"])
        tail_windows += int(region["tail_windows"])
        known_bp += int(export["known_bp"])
    if next_start != expected_length:
        raise ValueError(f"{seqid} chunks end at {next_start}, expected {expected_length}")
    expected_windows = (expected_length + WINDOW - 1) // WINDOW
    if total_windows != expected_windows or tail_windows != 1:
        raise ValueError("chunk windows do not reproduce whole-chromosome geometry")

    output_pte.parent.mkdir(parents=True, exist_ok=True)
    pte = np.lib.format.open_memmap(
        output_pte, mode="w+", dtype=np.float32, shape=(expected_length,),
    )
    states = np.lib.format.open_memmap(
        output_states, mode="w+", dtype=np.float16, shape=(expected_length, 4),
    )
    runs: list[tuple[int, int]] = []
    output_region_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_region_jsonl.open("wb") as region_handle:
        for start, end, path, _region, _export in chunks:
            source_pte = np.load(path / "p_te.npy", mmap_mode="r", allow_pickle=False)
            source_states = np.load(path / "states.npy", mmap_mode="r", allow_pickle=False)
            if source_pte.shape != (end - start,) or source_states.shape != (end - start, 4):
                raise ValueError(f"saved track shape mismatch: {path}")
            pte[start:end] = source_pte
            states[start:end] = source_states
            with (path / "region.jsonl.gz").open("rb") as source_region:
                shutil.copyfileobj(source_region, region_handle)
            for row_seqid, left, right in canonical_tuples(path / "prediction.canonical.tsv"):
                if row_seqid != seqid or left < start or right > end or right <= left:
                    raise ValueError(f"canonical interval outside chunk: {path}")
                if runs and left < runs[-1][1]:
                    raise ValueError("chunk canonical intervals overlap")
                if runs and left == runs[-1][1]:
                    runs[-1] = (runs[-1][0], right)
                else:
                    runs.append((left, right))
    pte.flush()
    states.flush()
    del pte, states

    interval_count = write_canonical(output_canonical, seqid, runs)
    region_result: dict[str, object] = {
        "schema": "gap_bridge_phase0_whole_region_v1",
        "status": "PASS",
        "seqid": seqid,
        "region_start": 0,
        "region_end": expected_length,
        "window": WINDOW,
        "stride": STRIDE,
        "windows": total_windows,
        "expected_windows": expected_windows,
        "total_bp": expected_length,
        "missing_bp": 0,
        "overlap_bp": 0,
        "tail_windows": tail_windows,
        "coverage_complete": True,
        "label_mode": "all_zero_inference_only",
        "truth_read": False,
        "chunks": [str(path) for _, _, path, _, _ in chunks],
        "output_jsonl": str(output_region_jsonl),
    }
    export_result: dict[str, object] = {
        "schema": "gap_bridge_phase0_whole_export_v1",
        "status": "PASS",
        "seqid": seqid,
        "region_start": 0,
        "region_end": expected_length,
        "length": expected_length,
        "windows": total_windows,
        "window": WINDOW,
        "stride": STRIDE,
        "threshold": THRESHOLD,
        "model_schema": model_schema,
        "probability_dtype": "float32",
        "state_probability_dtype": "float16",
        "state_probability_shape": [expected_length, 4],
        "state_order": ["background", "interior", "left_boundary", "right_boundary"],
        "known_bp": known_bp,
        "unknown_bp": expected_length - known_bp,
        "prediction_intervals": interval_count,
        "scientific_metrics_computed": False,
        "output_pte": str(output_pte),
        "output_states": str(output_states),
        "output_canonical": str(output_canonical),
    }
    output_region_manifest.write_text(
        json.dumps(region_result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    output_export_manifest.write_text(
        json.dumps(export_result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return export_result


def canonical_tuples(path: Path) -> list[tuple[str, int, int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            (row["seqid"], int(row["start"]), int(row["end"]))
            for row in csv.DictReader(handle, delimiter="\t")
        ]


def identity_result(
    expected: list[tuple[str, int, int]],
    observed: list[tuple[str, int, int]],
    expected_lengths: dict[str, int],
    observed_seqid: str,
    observed_length: int,
) -> dict[str, object]:
    observed_lengths = {observed_seqid: observed_length}
    intervals_equal = expected == observed
    lengths_equal = expected_lengths == observed_lengths
    first_difference = None
    if not intervals_equal:
        limit = min(len(expected), len(observed))
        index = next((i for i in range(limit) if expected[i] != observed[i]), limit)
        first_difference = {
            "index": index,
            "expected": expected[index] if index < len(expected) else None,
            "observed": observed[index] if index < len(observed) else None,
        }
    return {
        "schema": "gap_bridge_e0_p3_identity_v1",
        "status": "PASS" if intervals_equal and lengths_equal else "FAIL",
        "comparison": "ordered (seqid,start,end) tuple equality",
        "expected_intervals": len(expected),
        "observed_intervals": len(observed),
        "intervals_equal": intervals_equal,
        "lengths_equal": lengths_equal,
        "first_difference": first_difference,
        "scientific_metrics_computed": False,
    }


def compare_identity(
    expected_canonical: Path,
    observed_canonical: Path,
    expected_lengths_json: Path,
    observed_export_manifest: Path,
    output_json: Path,
) -> dict[str, object]:
    expected_lengths = {
        str(key): int(value)
        for key, value in json.loads(expected_lengths_json.read_text(encoding="utf-8")).items()
    }
    observed_manifest = json.loads(observed_export_manifest.read_text(encoding="utf-8"))
    result = identity_result(
        canonical_tuples(expected_canonical),
        canonical_tuples(observed_canonical),
        expected_lengths,
        str(observed_manifest["seqid"]),
        int(observed_manifest["length"]),
    )
    result.update({
        "expected_canonical": str(expected_canonical),
        "observed_canonical": str(observed_canonical),
    })
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    materialize = sub.add_parser("materialize-region")
    materialize.add_argument("--assembly", type=Path, required=True)
    materialize.add_argument("--seqid", required=True)
    materialize.add_argument("--start", type=int, required=True)
    materialize.add_argument("--end", type=int, required=True)
    materialize.add_argument("--output-jsonl", type=Path, required=True)
    materialize.add_argument("--manifest", type=Path, required=True)
    export = sub.add_parser("export-p3")
    export.add_argument("--model-dir", type=Path, required=True)
    export.add_argument("--data-jsonl", type=Path, required=True)
    export.add_argument("--output-pte", type=Path, required=True)
    export.add_argument("--output-states", type=Path, required=True)
    export.add_argument("--output-canonical", type=Path, required=True)
    export.add_argument("--manifest", type=Path, required=True)
    export.add_argument("--max-windows", type=int)
    identity = sub.add_parser("identity")
    identity.add_argument("--expected-canonical", type=Path, required=True)
    identity.add_argument("--observed-canonical", type=Path, required=True)
    identity.add_argument("--expected-lengths-json", type=Path, required=True)
    identity.add_argument("--observed-export-manifest", type=Path, required=True)
    identity.add_argument("--output-json", type=Path, required=True)
    stitch = sub.add_parser("stitch-chunks")
    stitch.add_argument("--chunk-root", type=Path, required=True)
    stitch.add_argument("--seqid", required=True)
    stitch.add_argument("--expected-length", type=int, required=True)
    stitch.add_argument("--output-region-jsonl", type=Path, required=True)
    stitch.add_argument("--output-region-manifest", type=Path, required=True)
    stitch.add_argument("--output-pte", type=Path, required=True)
    stitch.add_argument("--output-states", type=Path, required=True)
    stitch.add_argument("--output-canonical", type=Path, required=True)
    stitch.add_argument("--output-export-manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "materialize-region":
        result = write_region_jsonl(
            args.assembly, args.seqid, args.start, args.end,
            args.output_jsonl, args.manifest,
        )
    elif args.command == "export-p3":
        result = export_frozen_p3(
            args.model_dir, args.data_jsonl, args.output_pte, args.output_states,
            args.output_canonical, args.manifest, args.max_windows,
        )
    elif args.command == "identity":
        result = compare_identity(
            args.expected_canonical, args.observed_canonical,
            args.expected_lengths_json, args.observed_export_manifest,
            args.output_json,
        )
    else:
        result = stitch_chunk_exports(
            args.chunk_root, args.seqid, args.expected_length,
            args.output_region_jsonl, args.output_region_manifest,
            args.output_pte, args.output_states, args.output_canonical,
            args.output_export_manifest,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
