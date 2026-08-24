#!/usr/bin/env python3
"""Small, fail-closed interval adapter for LEMMI-style TE benchmark cells.

LEMMI itself is a metagenomics benchmark runner.  This module only borrows its
reproducibility shape (one frozen instance, one tool cell, explicit status) and
normalizes common TE annotation files to the TE-FM strict evaluator's
zero-based, half-open convention.  It intentionally does not run callers or
infer truth from a caller's own Dfam output.
"""
from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
import tempfile
from statistics import median
from pathlib import Path
from typing import Iterable

FIELDS = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]


def _record(seqid: str, start: int, end: int, name: str = ".", score: str = ".",
            strand: str = ".", source: str = ".", attributes: str = ".") -> dict[str, object]:
    if not seqid:
        raise ValueError("empty seqid")
    if start < 0 or end <= start:
        raise ValueError(f"invalid half-open interval: {seqid}:{start}-{end}")
    if strand not in {"+", "-", ".", "?"}:
        raise ValueError(f"invalid strand: {strand}")
    return {"seqid": seqid, "start": start, "end": end, "name": name or ".",
            "score": score or ".", "strand": strand, "source": source or ".",
            "attributes": attributes or "."}


def parse_bed(path: Path) -> Iterable[dict[str, object]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 3:
                raise ValueError(f"BED row {line_no} has fewer than 3 columns")
            yield _record(cols[0], int(cols[1]), int(cols[2]),
                          cols[3] if len(cols) > 3 else ".",
                          cols[4] if len(cols) > 4 else ".",
                          cols[5] if len(cols) > 5 else ".", "BED", ".")


def parse_gff(path: Path) -> Iterable[dict[str, object]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) != 9:
                raise ValueError(f"GFF row {line_no} does not have 9 columns")
            seqid, source, feature, start1, end1, score, strand, phase, attrs = cols
            name = feature
            for item in attrs.split(";"):
                if item.startswith(("Name=", "ID=")):
                    name = item.split("=", 1)[1]
                    break
            yield _record(seqid, int(start1) - 1, int(end1), name, score, strand,
                          source, f"feature={feature};phase={phase};{attrs}")


def parse_repeatmasker_out(path: Path) -> Iterable[dict[str, object]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            cols = line.split()
            # Header/separator rows are intentionally ignored; malformed data
            # rows that look like alignments are rejected rather than dropped.
            if not cols or not cols[0].isdigit():
                continue
            if len(cols) < 11:
                raise ValueError(f"RepeatMasker .out row {line_no} is truncated")
            if cols[8] not in {"C", "+", "-"}:
                raise ValueError(f"RepeatMasker .out row {line_no} has bad strand")
            strand = "-" if cols[8] == "C" else cols[8]
            yield _record(cols[4], int(cols[5]) - 1, int(cols[6]), cols[9], cols[0], strand,
                          "RepeatMasker", f"class_family={cols[10]}")


def convert(path: Path, output: Path, fmt: str = "auto") -> int:
    if fmt == "auto":
        low = path.name.lower()
        if low.endswith((".gff", ".gff3")):
            fmt = "gff"
        elif low.endswith((".bed", ".bed6")):
            fmt = "bed"
        elif low.endswith(".out"):
            fmt = "repeatmasker_out"
        else:
            raise ValueError(f"cannot infer adapter format for {path}")
    parsers = {"gff": parse_gff, "gff3": parse_gff, "bed": parse_bed, "repeatmasker_out": parse_repeatmasker_out}
    if fmt not in parsers:
        raise ValueError(f"unsupported format: {fmt}")
    rows = list(parsers[fmt](path))
    rows.sort(key=lambda row: (str(row["seqid"]), int(row["start"]), int(row["end"]), str(row["name"])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def read_canonical(path: Path) -> list[tuple[str, int, int]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != FIELDS:
            raise ValueError(f"canonical fields must be {FIELDS}")
        rows = []
        for row in reader:
            record = _record(row["seqid"], int(row["start"]), int(row["end"]), row["name"],
                             row["score"], row["strand"], row["source"], row["attributes"])
            rows.append((str(record["seqid"]), int(record["start"]), int(record["end"])))
    return rows


def _runs(values: bytearray) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start = None
    for idx in range(len(values) + 1):
        value = values[idx] if idx < len(values) else 0
        if value and start is None:
            start = idx
        elif not value and start is not None:
            out.append((start, idx))
            start = None
    return out


def _mask(rows: list[tuple[str, int, int]], lengths: dict[str, int]) -> dict[str, bytearray]:
    mask = {seqid: bytearray(length) for seqid, length in lengths.items()}
    for seqid, start, end in rows:
        if seqid not in mask:
            raise ValueError(f"interval seqid {seqid!r} missing from declared contig lengths")
        if end > len(mask[seqid]):
            raise ValueError(f"interval exceeds declared contig length: {seqid}:{start}-{end}")
        mask[seqid][start:end] = b"\x01" * (end - start)
    return mask


def _assert_nonoverlap(rows: list[tuple[str, int, int]], role: str) -> None:
    previous: dict[str, tuple[int, int]] = {}
    for seqid, start, end in sorted(rows):
        prior = previous.get(seqid)
        if prior is not None and start < prior[1]:
            raise ValueError(f"{role} overlap is not representable by FM strict masks: {seqid}:{start}-{end}")
        previous[seqid] = (start, end)


def _interval_audit(rows: list[tuple[str, int, int]]) -> dict[str, int]:
    """Count raw intervals, overlapping pairs, and union runs without labels."""
    pair_count = 0
    overlapping_intervals = 0
    interval_count = len(rows)
    by_seq: dict[str, list[tuple[int, int]]] = {}
    for seqid, start, end in rows:
        by_seq.setdefault(seqid, []).append((start, end))
    union_run_count = 0
    for seq_rows in by_seq.values():
        seq_rows.sort()
        active: list[tuple[int, int]] = []
        participating: set[int] = set()
        active_end = None
        for index, (start, end) in enumerate(seq_rows):
            while active and active[0][0] <= start:
                heapq.heappop(active)
            if active:
                pair_count += len(active)
                participating.add(index)
                participating.update(item[1] for item in active)
            heapq.heappush(active, (end, index))
            if active_end is None or start >= active_end:
                union_run_count += 1
                active_end = end
            else:
                active_end = max(active_end, end)
        overlapping_intervals += len(participating)
    return {"raw_interval_count": interval_count, "overlap_count": pair_count,
            "overlap_interval_count": overlapping_intervals,
            "union_run_count": union_run_count}


def _strict(true_seg: list[tuple[int, int]], pred_seg: list[tuple[int, int]], iou_threshold: float,
            boundary_tol: int) -> dict[str, float | int]:
    matched_t: set[int] = set(); matched_p: set[int] = set(); ious = []; errors = []; hits = 0
    true_start = 0
    for pi, (ps, pe) in enumerate(pred_seg):
        while true_start < len(true_seg) and true_seg[true_start][1] <= ps:
            true_start += 1
        best = (0.0, -1)
        ti = true_start
        while ti < len(true_seg):
            ts, te = true_seg[ti]
            if ts >= pe:
                break
            if ti in matched_t:
                ti += 1
                continue
            inter = min(pe, te) - max(ps, ts); union = max(pe, te) - min(ps, ts)
            iou = inter / union
            if iou > best[0]: best = (iou, ti)
            ti += 1
        if best[0] >= iou_threshold:
            ti = best[1]; matched_t.add(ti); matched_p.add(pi); ious.append(best[0])
            ts, te = true_seg[ti]; errors.append((abs(ps - ts) + abs(pe - te)) / 2)
            hits += abs(ps - ts) <= boundary_tol and abs(pe - te) <= boundary_tol
    tp = len(matched_p); fp = len(pred_seg) - tp; fn = len(true_seg) - len(matched_t)
    prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
    bprec = hits / len(pred_seg) if pred_seg else 0.0; brec = hits / len(true_seg) if true_seg else 0.0
    return {"true_segments": len(true_seg), "pred_segments": len(pred_seg), "segment_tp": tp,
            "segment_fp": fp, "segment_fn": fn, "segment_precision": prec, "segment_recall": rec,
            "segment_f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "mean_matched_iou": sum(ious) / len(ious) if ious else 0.0,
            "boundary_precision": bprec, "boundary_recall": brec,
            "boundary_f1": 2 * bprec * brec / (bprec + brec) if bprec + brec else 0.0,
            "boundary_hits": hits, "matched_iou_sum": sum(ious), "boundary_errors": errors,
            "median_boundary_error_bp": median(errors) if errors else None}


def evaluate(truth: Path, prediction: Path, lengths: dict[str, int], iou_threshold: float = 0.8,
             boundary_tol_bp: int = 5, truth_tier: str = "T0",
             overlap_policy: str = "flat_union") -> dict[str, object]:
    """Evaluate a canonical prediction against an independent frozen truth.

    The implementation mirrors ``strict_segment_eval.py``: masks are per
    contig, intervals are one-to-one matched by greedy best IoU, and no model
    or caller threshold is fitted on the evaluation split.
    """
    if truth_tier not in {"T0", "T1"}:
        raise ValueError("truth_tier must be T0 or T1")
    if overlap_policy not in {"flat_union", "require_nonoverlap"}:
        raise ValueError("overlap_policy must be flat_union or require_nonoverlap")
    truth_rows = read_canonical(truth); pred_rows = read_canonical(prediction)
    if overlap_policy == "require_nonoverlap":
        _assert_nonoverlap(truth_rows, "truth")
        _assert_nonoverlap(pred_rows, "prediction")
    truth_audit = _interval_audit(truth_rows); pred_audit = _interval_audit(pred_rows)
    tm = _mask(truth_rows, lengths); pm = _mask(pred_rows, lengths)
    metrics: dict[str, object] = {"truth_tier": truth_tier, "overlap_policy": overlap_policy,
                                  "bp_n": sum(lengths.values()), "bp_tp": 0, "bp_fp": 0, "bp_fn": 0,
                                  "bp_tn": 0, "true_segments": 0, "pred_segments": 0,
                                  "segment_tp": 0, "segment_fp": 0, "segment_fn": 0,
                                  "boundary_hits": 0, "matched_iou_sum": 0.0,
                                  "short_pred_segments": 0, "short_true_backed": 0,
                                  "pred_true_backed": 0, "pred_segments_total": 0,
                                  "mean_fragments_per_true": 0.0, "split_true_rate": 0.0,
                    "missed_true_rate": 0.0}
    metrics.update({f"truth_{key}": value for key, value in truth_audit.items()})
    metrics.update({f"prediction_{key}": value for key, value in pred_audit.items()})
    fragment_counts = []; errors = []; strict_rows = []
    for seqid in lengths:
        tv, pv = tm[seqid], pm[seqid]
        tp = sum(a and b for a, b in zip(tv, pv)); fp = sum((not a) and b for a, b in zip(tv, pv)); fn = sum(a and (not b) for a, b in zip(tv, pv)); tn = sum((not a) and (not b) for a, b in zip(tv, pv))
        for key, value in (("bp_tp", tp), ("bp_fp", fp), ("bp_fn", fn), ("bp_tn", tn)): metrics[key] = int(metrics[key]) + value
        ts, ps = _runs(tv), _runs(pv); row = _strict(ts, ps, iou_threshold, boundary_tol_bp); strict_rows.append(row)
        for key in ("true_segments", "pred_segments", "segment_tp", "segment_fp", "segment_fn"): metrics[key] = int(metrics[key]) + int(row[key])
        metrics["boundary_hits"] = int(metrics["boundary_hits"]) + int(row["boundary_hits"])
        metrics["matched_iou_sum"] = float(metrics["matched_iou_sum"]) + float(row["matched_iou_sum"])
        errors.extend(float(value) for value in row["boundary_errors"])
        true_start = 0
        for pstart, pend in ps:
            metrics["pred_segments_total"] = int(metrics["pred_segments_total"]) + 1
            if pend - pstart < 80:
                metrics["short_pred_segments"] = int(metrics["short_pred_segments"]) + 1
            while true_start < len(ts) and ts[true_start][1] <= pstart:
                true_start += 1
            true_index = true_start
            backed = False
            while true_index < len(ts) and ts[true_index][0] < pend:
                tstart, tend = ts[true_index]
                overlap = min(pend, tend) - max(pstart, tstart)
                if overlap > 0 and overlap / (pend - pstart) >= 0.5:
                    backed = True
                    break
                true_index += 1
            if backed:
                metrics["pred_true_backed"] = int(metrics["pred_true_backed"]) + 1
                if pend - pstart < 80: metrics["short_true_backed"] = int(metrics["short_true_backed"]) + 1
        pred_start = 0
        for tstart, tend in ts:
            while pred_start < len(ps) and ps[pred_start][1] <= tstart:
                pred_start += 1
            pred_index = pred_start
            fragments = 0
            while pred_index < len(ps) and ps[pred_index][0] < tend:
                pstart, pend = ps[pred_index]
                fragments += min(pend, tend) > max(pstart, tstart)
                pred_index += 1
            fragment_counts.append(fragments)
    bp_tp, bp_fp, bp_fn = int(metrics["bp_tp"]), int(metrics["bp_fp"]), int(metrics["bp_fn"])
    bprec = bp_tp / (bp_tp + bp_fp) if bp_tp + bp_fp else 0.0; brec = bp_tp / (bp_tp + bp_fn) if bp_tp + bp_fn else 0.0
    prec = int(metrics["segment_tp"]) / (int(metrics["segment_tp"]) + int(metrics["segment_fp"])) if int(metrics["segment_tp"]) + int(metrics["segment_fp"]) else 0.0
    rec = int(metrics["segment_tp"]) / (int(metrics["segment_tp"]) + int(metrics["segment_fn"])) if int(metrics["segment_tp"]) + int(metrics["segment_fn"]) else 0.0
    total_true = int(metrics["true_segments"]); total_pred = int(metrics["pred_segments"])
    boundary_hits = int(metrics["boundary_hits"]); boundary_precision = boundary_hits / total_pred if total_pred else 0.0; boundary_recall = boundary_hits / total_true if total_true else 0.0
    metrics.update({"bp_precision": bprec, "bp_recall": brec, "bp_f1": 2*bprec*brec/(bprec+brec) if bprec+brec else 0.0,
                    "segment_precision": prec, "segment_recall": rec, "segment_f1": 2*prec*rec/(prec+rec) if prec+rec else 0.0,
                    "segment_iou_mean": float(metrics["matched_iou_sum"]) / int(metrics["segment_tp"]) if int(metrics["segment_tp"]) else 0.0,
                    "mean_matched_iou": float(metrics["matched_iou_sum"]) / int(metrics["segment_tp"]) if int(metrics["segment_tp"]) else 0.0,
                    "boundary_precision": boundary_precision, "boundary_recall": boundary_recall,
                    "boundary_f1": 2*boundary_precision*boundary_recall/(boundary_precision+boundary_recall) if boundary_precision+boundary_recall else 0.0,
                    "median_boundary_error_bp": median(errors) if errors else None,
                    "pred_true_backed_rate": int(metrics["pred_true_backed"]) / int(metrics["pred_segments_total"]) if int(metrics["pred_segments_total"]) else 0.0,
                    "short_true_backed_rate": int(metrics["short_true_backed"]) / int(metrics["short_pred_segments"]) if int(metrics["short_pred_segments"]) else 0.0,
                    "mean_fragments_per_true": sum(fragment_counts)/len(fragment_counts) if fragment_counts else 0.0,
                    "split_true_rate": sum(x > 1 for x in fragment_counts)/len(fragment_counts) if fragment_counts else 0.0,
                    "missed_true_rate": sum(x == 0 for x in fragment_counts)/len(fragment_counts) if fragment_counts else 0.0})
    if truth_tier == "T1":
        # Unlabelled genome sequence is unknown, never a negative denominator.
        for key in ("bp_fp", "bp_tn", "bp_precision", "bp_f1", "segment_fp",
                    "segment_precision", "segment_f1", "boundary_precision",
                    "boundary_f1", "pred_true_backed_rate", "short_true_backed_rate"):
            metrics[key] = None
    metrics["truth_coverage_bp"] = int(metrics["bp_tp"]) / (int(metrics["bp_tp"]) + int(metrics["bp_fn"])) if int(metrics["bp_tp"]) + int(metrics["bp_fn"]) else 0.0
    metrics["bp_recall"] = int(metrics["bp_tp"]) / (int(metrics["bp_tp"]) + int(metrics["bp_fn"])) if int(metrics["bp_tp"]) + int(metrics["bp_fn"]) else 0.0
    metrics["segment_recall"] = int(metrics["segment_tp"]) / (int(metrics["segment_tp"]) + int(metrics["segment_fn"])) if int(metrics["segment_tp"]) + int(metrics["segment_fn"]) else 0.0
    if any(not math.isfinite(float(v)) for v in metrics.values() if isinstance(v, (int, float))): raise ValueError("non-finite metric")
    return metrics


def smoke(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    truth = root / "truth.bed"; pred = root / "pred.gff3"; tc = root / "truth.tsv"; pc = root / "pred.tsv"
    truth.write_text("chr1\t10\t30\ttruth\nchr1\t50\t60\ttruth2\n", encoding="utf-8")
    pred.write_text("##gff-version 3\nchr1\tRM\tTE\t11\t30\t.\t+\t.\tID=p1\nchr1\tRM\tTE\t51\t60\t.\t+\t.\tID=p2\n", encoding="utf-8")
    convert(truth, tc, "bed"); convert(pred, pc, "gff3")
    result = evaluate(tc, pc, {"chr1": 100}, 0.8, 5)
    assert result["bp_tp"] == 30 and result["true_segments"] == 2 and result["pred_segments"] == 2
    return {"pass": True, "coordinate_convention": "zero_based_half_open", "metrics": result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    convert_parser = sub.add_parser("convert", help="normalize BED/GFF3/RepeatMasker output")
    convert_parser.add_argument("--input", type=Path, required=True)
    convert_parser.add_argument("--output", type=Path, required=True)
    convert_parser.add_argument("--format", default="auto", choices=["auto", "bed", "gff", "gff3", "repeatmasker_out"])
    evaluate_parser = sub.add_parser("evaluate", help="score canonical intervals against frozen truth")
    evaluate_parser.add_argument("--truth", type=Path, required=True)
    evaluate_parser.add_argument("--prediction", type=Path, required=True)
    evaluate_parser.add_argument("--lengths", type=Path, required=True, help="JSON object of contig lengths")
    evaluate_parser.add_argument("--truth-tier", choices=["T0", "T1"], default="T0")
    evaluate_parser.add_argument("--iou-threshold", type=float, default=0.8)
    evaluate_parser.add_argument("--boundary-tol-bp", type=int, default=5)
    evaluate_parser.add_argument("--overlap-policy", choices=["flat_union", "require_nonoverlap"], default="flat_union")
    sub.add_parser("self-test", help="run deterministic synthetic smoke")
    args = parser.parse_args()
    if args.command == "self-test":
        with tempfile.TemporaryDirectory(prefix="lemmi-te-adapter-") as root:
            print(json.dumps(smoke(Path(root)), sort_keys=True))
        return 0
    if args.command == "convert":
        print(json.dumps({"rows": convert(args.input, args.output, args.format), "output": str(args.output)}))
        return 0
    lengths = json.loads(args.lengths.read_text(encoding="utf-8"))
    if not isinstance(lengths, dict) or any(not isinstance(v, int) or v < 1 for v in lengths.values()):
        parser.error("--lengths must contain a JSON object of positive integer lengths")
    result = evaluate(args.truth, args.prediction, lengths, args.iou_threshold,
                      args.boundary_tol_bp, args.truth_tier, args.overlap_policy)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
