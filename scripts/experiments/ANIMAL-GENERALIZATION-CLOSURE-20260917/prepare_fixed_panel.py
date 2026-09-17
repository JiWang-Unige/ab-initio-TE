#!/usr/bin/env python3
"""Prepare a fixed, source-dependent external panel for the D screen.

The panel is deliberately selected from the first four rows of each frozen
UCSC ``chrom.sizes`` source and uses a centered 1-Mb interval on each row.
Labels are only trimmed to those intervals; no model score or label density is
used for region selection.  The script also converts UCSC ``rmsk.txt`` rows to
the small RepeatMasker ``.out`` subset consumed by the existing RC0 evaluator.
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Any, Iterable


WINDOW_BP = 4096
PANEL_BP = 1_048_576


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def open_text(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def source_rows(path: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    with open_text(path) as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 2:
                raise ValueError(f"sizes row {line_no} has fewer than two columns: {path}")
            name, length = cols[0], int(cols[1])
            if length < PANEL_BP:
                continue
            rows.append((name, length))
            if len(rows) == 4:
                break
    if len(rows) != 4:
        raise ValueError(f"fewer than four usable contigs in {path}")
    return rows


def row_overlaps(seqid: str, start: int, end: int, regions: dict[str, tuple[int, int]]) -> bool:
    bounds = regions.get(seqid)
    return bounds is not None and end > bounds[0] and start < bounds[1]


def write_assembly_report(path: Path, rows: list[tuple[str, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# source=UCSC chrom.sizes; synthetic report for fixed source-order panel\n")
        handle.write("# Sequence-Name\tSequence-Role\tAssigned-Molecule\tAssigned-Molecule-Location/Type\tGenBank-Accn\tRelationship\tRefSeq-Accn\tAssembly-Unit\tSequence-Length\tUCSC-style-name\n")
        for index, (seqid, length) in enumerate(rows, 1):
            handle.write(
                f"{seqid}\tsource-chrom-sizes-row\tna\tna\t{seqid}\tna\t{seqid}\tsource-chrom-sizes\t{length}\t{seqid}\n"
            )


def _candidate_regions(candidate: dict[str, Any], prep_dir: Path) -> list[dict[str, Any]]:
    sizes = Path(str(candidate["sizes"]))
    rows = source_rows(sizes)
    report = prep_dir / "synthetic_assembly_report.txt"
    write_assembly_report(report, rows)
    regions: list[dict[str, Any]] = []
    for seqid, length in rows:
        start = (length - PANEL_BP) // 2
        regions.append(
            {
                "seqid": seqid,
                "role": "source-chrom-sizes-row",
                "molecule": "na",
                "length_bp": length,
                "start_bp": start,
                "end_bp": start + PANEL_BP,
            }
        )
    candidate["regions"] = regions
    candidate["assembly_report"] = str(report)
    candidate["fasta_accession_column"] = "GenBank-Accession"
    candidate["panel_selection_source"] = str(sizes)
    candidate["panel_selection_rows"] = [row[0] for row in rows]
    return regions


def _repeatmasker_lines(path: Path) -> Iterable[list[str]]:
    with open_text(path) as handle:
        for line in handle:
            cols = line.split()
            if cols and cols[0].isdigit() and len(cols) >= 11:
                yield cols


def _ucsc_rmsk_to_out(source: Path, output: Path, regions: dict[str, tuple[int, int]]) -> dict[str, int]:
    counts = {"source_rows": 0, "panel_rows": 0, "known_te_rows": 0}
    output.parent.mkdir(parents=True, exist_ok=True)
    with open_text(source) as handle, output.open("w", encoding="utf-8") as out:
        out.write("# fixed panel conversion from UCSC rmsk.txt; coordinates converted to RepeatMasker .out\n")
        out.write("# SW perc div perc del perc ins query position matching repeat class/family\n")
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.split()
            if len(cols) < 13:
                continue
            counts["source_rows"] += 1
            seqid = cols[5]
            start0, end = int(cols[6]), int(cols[7])
            if not row_overlaps(seqid, start0, end, regions):
                continue
            name = cols[10]
            cls = cols[11]
            family = cols[12]
            class_family = cls if "/" in cls else f"{cls}/{family}"
            strand = cols[9]
            if strand not in {"+", "-", "C"}:
                strand = "+"
            # RepeatMasker .out uses one-based inclusive starts and inclusive
            # ends.  UCSC rmsk stores zero-based half-open genome coordinates.
            out.write(
                f"{cols[1]} 0 0 0 {seqid} {start0 + 1} {end} 0 {strand} {name} {class_family} 0 0 0 {cols[-1]}\n"
            )
            counts["panel_rows"] += 1
            if cls.split("/", 1)[0] in {"LINE", "SINE", "LTR", "DNA", "RC", "Retroposon"}:
                counts["known_te_rows"] += 1
    return counts


def _trim_repeatmasker_out(source: Path, output: Path, regions: dict[str, tuple[int, int]]) -> dict[str, int]:
    counts = {"source_rows": 0, "panel_rows": 0, "known_te_rows": 0}
    output.parent.mkdir(parents=True, exist_ok=True)
    with open_text(source) as handle, output.open("w", encoding="utf-8") as out:
        out.write("# fixed panel subset of the same-assembly RepeatMasker .out source\n")
        for cols in _repeatmasker_lines(source):
            counts["source_rows"] += 1
            seqid = cols[4]
            start0, end = int(cols[5]) - 1, int(cols[6])
            if not row_overlaps(seqid, start0, end, regions):
                continue
            out.write(" ".join(cols) + "\n")
            counts["panel_rows"] += 1
            if cols[10].split("/", 1)[0] in {"LINE", "SINE", "LTR", "DNA", "RC", "Retroposon"}:
                counts["known_te_rows"] += 1
    return counts


def ensure_source(candidate: dict[str, Any], prep_dir: Path) -> Path:
    source = Path(str(candidate["label_source"]))
    if source.is_file():
        return source
    url = candidate.get("label_source_url")
    if not url:
        raise FileNotFoundError(f"label source missing and no URL: {source}")
    source = prep_dir / Path(str(url)).name
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(str(url), timeout=120) as response, source.open("wb") as out:
            shutil.copyfileobj(response, out)
    candidate["downloaded_label_source"] = str(source)
    return source


def ensure_sizes(candidate: dict[str, Any], prep_dir: Path) -> Path:
    sizes = Path(str(candidate["sizes"]))
    if sizes.is_file():
        return sizes
    url = candidate.get("label_sizes_url")
    if not url:
        raise FileNotFoundError(f"sizes source missing and no URL: {sizes}")
    sizes = prep_dir / Path(str(url)).name
    if not sizes.exists():
        sizes.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(str(url), timeout=120) as response, sizes.open("wb") as out:
            shutil.copyfileobj(response, out)
    candidate["downloaded_sizes_source"] = str(sizes)
    return sizes


def prepare_one(config: dict[str, Any], candidate: dict[str, Any], root: Path) -> dict[str, Any]:
    candidate_id = str(candidate["id"])
    prep_dir = root / candidate_id
    prep_dir.mkdir(parents=True, exist_ok=True)
    candidate["sizes"] = str(ensure_sizes(candidate, prep_dir))
    regions = _candidate_regions(candidate, prep_dir)
    bounds = {str(row["seqid"]): (int(row["start_bp"]), int(row["end_bp"])) for row in regions}
    source = ensure_source(candidate, prep_dir)
    output = prep_dir / "truth_trimmed.out"
    if candidate["label_format"] == "ucsc_rmsk_table":
        counts = _ucsc_rmsk_to_out(source, output, bounds)
    elif candidate["label_format"] == "repeatmasker_out":
        counts = _trim_repeatmasker_out(source, output, bounds)
    else:
        raise ValueError(f"unsupported label format: {candidate['label_format']}")
    candidate["label_out"] = str(output)
    candidate["label_id"] = f"same-assembly-{candidate_id}-source-dependent"
    candidate["label_status"] = "same-assembly source-dependent fixed panel; not independent truth"
    candidate["label_audit"] = counts
    return {"candidate": candidate_id, "prep_dir": str(prep_dir), **counts, "regions": [r["seqid"] for r in regions]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-config", type=Path, required=True)
    parser.add_argument("--candidate", action="append")
    args = parser.parse_args()
    config = read_json(args.config)
    candidates = config.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("config candidates must be a list")
    selected = set(args.candidate or [str(item["id"]) for item in candidates])
    root = Path(str(config["prep_root"]))
    prepared = []
    for candidate in candidates:
        if str(candidate["id"]) in selected:
            prepared.append(prepare_one(config, candidate, root))
    if set(item["candidate"] for item in prepared) != selected:
        raise ValueError(f"requested candidates not found: {sorted(selected - {item['candidate'] for item in prepared})}")
    args.output_config.parent.mkdir(parents=True, exist_ok=True)
    args.output_config.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PREPARED", "candidates": prepared, "output_config": str(args.output_config)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
