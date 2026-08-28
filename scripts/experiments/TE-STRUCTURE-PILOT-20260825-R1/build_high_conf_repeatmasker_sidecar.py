#!/usr/bin/env python3
"""Filter raw RepeatMasker ``.out`` hits into a high-confidence BED sidecar.

The sidecar is a reference-annotation conditioning track for the Human P2
pilot.  It is not a full-copy or independent biological truth set.  Hits are
kept only when their top-level RepeatMasker class and alignment geometry pass
the fixed pilot thresholds.  The corpus builder unions touching/overlapping
rows before deriving boundaries.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator


TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "RETROPOSON"}
MIN_SW_SCORE = 225.0
MAX_DIV = 50.0
MAX_DEL = 20.0
MAX_INS = 20.0
MIN_QUERY_SPAN = 64


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def _open_output(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "wt", encoding="utf-8")
    return path.open("wt", encoding="utf-8")


def normalize_class(value: str) -> str:
    """Return the top-level RepeatMasker class without a trailing uncertainty mark."""
    return value.split("/", 1)[0].rstrip("?").upper()


def _number(token: str, *, line_no: int, field: str) -> float:
    try:
        return float(token.rstrip("*"))
    except ValueError as exc:
        raise ValueError(f"RepeatMasker .out row {line_no} has bad {field}: {token!r}") from exc


def _coordinate(token: str, *, line_no: int, field: str, allow_zero: bool = False) -> int:
    value = token.strip()
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    try:
        coordinate = int(value)
    except ValueError as exc:
        raise ValueError(f"RepeatMasker .out row {line_no} has bad {field}: {token!r}") from exc
    if coordinate < 0 or (coordinate == 0 and not allow_zero):
        raise ValueError(f"RepeatMasker .out row {line_no} has non-positive {field}: {token!r}")
    return coordinate


def _selectors_match(seqid: str, seqids: set[str], prefixes: tuple[str, ...]) -> bool:
    return not seqids and not prefixes or seqid in seqids or any(seqid.startswith(prefix) for prefix in prefixes)


def iter_repeatmasker_hits(path: Path) -> Iterator[dict[str, object]]:
    """Yield validated alignment rows, including rows later rejected by thresholds."""
    with _open_text(path) as handle:
        for line_no, line in enumerate(handle, 1):
            columns = line.split()
            if not columns or not columns[0].replace("*", "").isdigit():
                continue
            if len(columns) < 14:
                raise ValueError(f"RepeatMasker .out row {line_no} is truncated")
            strand = columns[8]
            if strand not in {"C", "+", "-"}:
                raise ValueError(f"RepeatMasker .out row {line_no} has bad strand: {strand!r}")
            sw = _number(columns[0], line_no=line_no, field="SW score")
            div = _number(columns[1], line_no=line_no, field="%div")
            deletion = _number(columns[2], line_no=line_no, field="%del")
            insertion = _number(columns[3], line_no=line_no, field="%ins")
            if sw < 0 or any(value < 0 or value > 100 for value in (div, deletion, insertion)):
                raise ValueError(f"RepeatMasker .out row {line_no} has invalid alignment percentages")
            query_start = _coordinate(columns[5], line_no=line_no, field="query start")
            query_end = _coordinate(columns[6], line_no=line_no, field="query end")
            _coordinate(columns[7], line_no=line_no, field="query left", allow_zero=True)
            if strand in {"C", "-"}:
                _coordinate(columns[11], line_no=line_no, field="repeat left", allow_zero=True)
                repeat_end = _coordinate(columns[12], line_no=line_no, field="repeat end")
                repeat_start = _coordinate(columns[13], line_no=line_no, field="repeat start")
            else:
                repeat_start = _coordinate(columns[11], line_no=line_no, field="repeat start")
                repeat_end = _coordinate(columns[12], line_no=line_no, field="repeat end")
                _coordinate(columns[13], line_no=line_no, field="repeat left", allow_zero=True)
            if query_end < query_start:
                raise ValueError(f"RepeatMasker .out row {line_no} has reversed query coordinates")
            if strand == "+" and repeat_end < repeat_start:
                raise ValueError(f"RepeatMasker .out row {line_no} has reversed repeat coordinates")
            yield {
                "seqid": columns[4],
                "start": query_start - 1,
                "end": query_end,
                "name": columns[9],
                "score": sw,
                "strand": "-" if strand == "C" else strand,
                "class_family": columns[10],
                "repeat_class": normalize_class(columns[10]),
                "div_percent": div,
                "del_percent": deletion,
                "ins_percent": insertion,
                "query_span": query_end - query_start + 1,
                "repeat_start": repeat_start,
                "repeat_end": repeat_end,
                "line_no": line_no,
                "passes_thresholds": (
                    sw >= MIN_SW_SCORE
                    and div <= MAX_DIV
                    and deletion <= MAX_DEL
                    and insertion <= MAX_INS
                    and query_end - query_start + 1 >= MIN_QUERY_SPAN
                    and normalize_class(columns[10]) in TE_CLASSES
                ),
            }


def high_confidence_hits(
    path: Path,
    *,
    seqids: Iterable[str] = (),
    prefixes: Iterable[str] = (),
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Return threshold-passing hits and an auditable row-count summary."""
    selected_seqids = set(seqids)
    selected_prefixes = tuple(prefixes)
    stats: Counter[str] = Counter()
    accepted: list[dict[str, object]] = []
    for hit in iter_repeatmasker_hits(path):
        stats["validated_rows"] += 1
        if not _selectors_match(str(hit["seqid"]), selected_seqids, selected_prefixes):
            stats["outside_requested_seqids"] += 1
            continue
        stats["requested_rows"] += 1
        if str(hit["repeat_class"]) not in TE_CLASSES:
            stats["rejected_class"] += 1
            continue
        if float(hit["score"]) < MIN_SW_SCORE:
            stats["rejected_sw"] += 1
            continue
        # The percentages are retained in the local row only while filtering;
        # the fixed thresholds are applied in iter_repeatmasker_hits metadata.
        if not bool(hit["passes_thresholds"]):
            stats["rejected_alignment_threshold"] += 1
            continue
        stats["accepted_rows"] += 1
        accepted.append(hit)
    return accepted, dict(stats)


def write_sidecar(
    input_out: Path,
    output_bed: Path,
    *,
    seqids: Iterable[str] = (),
    prefixes: Iterable[str] = (),
) -> dict[str, object]:
    selected_seqids = tuple(seqids)
    selected_prefixes = tuple(prefixes)
    accepted, counts = high_confidence_hits(
        input_out,
        seqids=selected_seqids,
        prefixes=selected_prefixes,
    )
    accepted.sort(key=lambda row: (str(row["seqid"]), int(row["start"]), int(row["end"]), str(row["name"])))
    output_bed.parent.mkdir(parents=True, exist_ok=True)
    with _open_output(output_bed) as handle:
        for row in accepted:
            handle.write(
                "\t".join(
                    [
                        str(row["seqid"]),
                        str(row["start"]),
                        str(row["end"]),
                        str(row["name"]),
                        str(int(float(row["score"]))),
                        str(row["strand"]),
                    ]
                )
                + "\n"
            )
    return {
        "schema": "high_confidence_repeatmasker_sidecar_v1",
        "input_repeatmasker_out": str(input_out),
        "output_bed": str(output_bed),
        "requested_seqids": sorted(set(selected_seqids)),
        "requested_seqid_prefixes": list(selected_prefixes),
        "filters": {
            "classes": sorted(TE_CLASSES),
            "minimum_sw_score": MIN_SW_SCORE,
            "maximum_div_percent": MAX_DIV,
            "maximum_del_percent": MAX_DEL,
            "maximum_ins_percent": MAX_INS,
            "minimum_query_span_bp": MIN_QUERY_SPAN,
            "coordinate_convention": "zero_based_half_open_query; RepeatMasker coordinates validated as one_based_inclusive",
        },
        "conditioning_semantics": "high_confidence_reference_annotation_rows; not biological full_copy_truth",
        "counts": counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-out", type=Path, required=True)
    parser.add_argument("--output-bed", type=Path, required=True)
    parser.add_argument("--seqid", action="append", default=[])
    parser.add_argument("--seqid-prefix", action="append", default=[])
    args = parser.parse_args()
    result = write_sidecar(
        args.input_out,
        args.output_bed,
        seqids=args.seqid,
        prefixes=args.seqid_prefix,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
