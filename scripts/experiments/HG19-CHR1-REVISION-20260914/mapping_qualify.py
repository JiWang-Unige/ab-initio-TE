#!/usr/bin/env python3
"""Qualify unique reciprocal hg19->CHM13 interval mappings.

The production path delegates coordinate conversion to the official UCSC
liftOver executable.  This module only prepares BED records, retains every
liftOver destination, and classifies whether an interval has exactly one
same-length forward mapping whose reverse mapping returns the original
interval.  It never reads target annotations and never computes F1 or a
prediction rescue count.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, Union


VALID_STATES = ("TP", "FP", "FN", "TN")
VALID_STATE_SET = set(VALID_STATES)
OFFICIAL_LIFTOVER_URL = (
    "https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/liftOver"
)


@dataclass(frozen=True)
class SourceInterval:
    """One BED6+tile_id row from the frozen old-confusion export."""

    row_id: int
    mapping_id: str
    chrom: str
    start: int
    end: int
    state: str
    score: str
    strand: str
    tile_id: str

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class LiftedInterval:
    """One mapped BED row emitted by liftOver."""

    mapping_id: str
    chrom: str
    start: int
    end: int
    state: str
    score: str
    strand: str
    tile_id: str

    @property
    def length(self) -> int:
        return self.end - self.start


def resolve_path(root: Path, value: Union[str, Path]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def parse_source_intervals(path: Path, allowed_source: set[str]) -> list[SourceInterval]:
    """Parse all source rows, retaining out-of-scope rows for classification."""
    rows: list[SourceInterval] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 7:
                raise ValueError(f"{path}:{line_no}: expected BED6+tile_id")
            try:
                start, end = int(fields[1]), int(fields[2])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid BED coordinates") from exc
            if start < 0 or end <= start:
                raise ValueError(f"{path}:{line_no}: invalid BED interval")
            state = fields[3].upper()
            if state not in VALID_STATE_SET:
                raise ValueError(
                    f"{path}:{line_no}: expected one of {VALID_STATES}, got {fields[3]!r}"
                )
            rows.append(
                SourceInterval(
                    row_id=line_no,
                    mapping_id=f"r{line_no:09d}",
                    chrom=fields[0],
                    start=start,
                    end=end,
                    state=state,
                    score=fields[4],
                    strand=fields[5],
                    tile_id=fields[6],
                )
            )
    return rows


def bed_fields(
    chrom: str,
    start: int,
    end: int,
    state: str,
    score: str,
    strand: str,
    mapping_id: str,
    tile_id: str,
) -> list[str]:
    return [
        chrom,
        str(start),
        str(end),
        state,
        score,
        strand,
        mapping_id,
        tile_id,
    ]


def write_forward_input(path: Path, rows: Iterable[SourceInterval], allowed_source: set[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for row in rows:
            if row.chrom not in allowed_source:
                continue
            writer.writerow(
                bed_fields(
                    row.chrom,
                    row.start,
                    row.end,
                    row.state,
                    row.score,
                    row.strand,
                    row.mapping_id,
                    row.tile_id,
                )
            )
            count += 1
    return count


def write_reverse_input(path: Path, rows: Iterable[LiftedInterval]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for row in rows:
            writer.writerow(
                bed_fields(
                    row.chrom,
                    row.start,
                    row.end,
                    row.state,
                    row.score,
                    row.strand,
                    row.mapping_id,
                    row.tile_id,
                )
            )
            count += 1
    return count


def parse_lifted_bed(path: Path) -> list[LiftedInterval]:
    """Read mapped BED8 rows and retain every destination row."""
    rows: list[LiftedInterval] = []
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 8:
                # liftOver preserves the input BED fields.  Losing our ID
                # would make a reciprocal pairing unverifiable.
                raise ValueError(f"{path}:{line_no}: mapped row lost BED8 identity fields")
            try:
                start, end = int(fields[1]), int(fields[2])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid mapped coordinates") from exc
            if start < 0 or end <= start:
                raise ValueError(f"{path}:{line_no}: invalid mapped interval")
            rows.append(
                LiftedInterval(
                    mapping_id=fields[6],
                    chrom=fields[0],
                    start=start,
                    end=end,
                    state=fields[3],
                    score=fields[4],
                    strand=fields[5],
                    tile_id=fields[7],
                )
            )
    return rows


def run_liftover(
    liftover: Path,
    input_bed: Path,
    chain: Path,
    mapped_bed: Path,
    unmapped_file: Path,
    log_file: Path,
    *,
    multiple: bool,
    min_match: float,
    bed_plus: int,
) -> None:
    if not liftover.is_file():
        raise FileNotFoundError(f"liftOver executable not found: {liftover}")
    if not chain.is_file():
        raise FileNotFoundError(f"chain file not found: {chain}")
    command = [str(liftover), f"-bedPlus={bed_plus}"]
    if multiple:
        command.append("-multiple")
    command.append(f"-minMatch={min_match:g}")
    command.extend([str(input_bed), str(chain), str(mapped_bed), str(unmapped_file)])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    log_file.write_text(
        "command: "
        + shlex.join(command)
        + f"\nreturncode: {result.returncode}\n"
        + "stdout:\n"
        + result.stdout
        + "stderr:\n"
        + result.stderr,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"liftOver failed with exit code {result.returncode}; see {log_file}")
    if not mapped_bed.exists() or not unmapped_file.exists():
        raise RuntimeError("liftOver completed without both mapped and unmapped outputs")


def classify_interval(
    source: SourceInterval,
    forward: Sequence[LiftedInterval],
    reverse: Sequence[LiftedInterval],
    allowed_source: set[str],
    allowed_target: set[str],
) -> dict[str, object]:
    """Classify one source row without collapsing any mapping destinations."""
    result: dict[str, object] = {
        "row_id": source.row_id,
        "mapping_id": source.mapping_id,
        "source_chrom": source.chrom,
        "source_start0": source.start,
        "source_end": source.end,
        "source_length": source.length,
        "state": source.state,
        "score": source.score,
        "strand": source.strand,
        "tile_id": source.tile_id,
        "source_scope": "IN_SCOPE" if source.chrom in allowed_source else "OUT_OF_SCOPE",
        "mapping_status": "SOURCE_OUT_OF_SCOPE",
        "target_scope": "NONE",
        "qualified_unique_reciprocal_same_length": False,
        "forward_count": len(forward),
        "reverse_count": len(reverse),
        "length_changed": None,
        "forward_chrom": "",
        "forward_start0": "",
        "forward_end": "",
        "forward_length": "",
        "forward_strand": "",
        "reverse_chrom": "",
        "reverse_start0": "",
        "reverse_end": "",
        "reverse_length": "",
        "reverse_strand": "",
        "reverse_exact_source_interval": False,
    }
    if source.chrom not in allowed_source:
        return result
    if not forward:
        result["mapping_status"] = "UNMAPPED_FORWARD"
        return result
    if len(forward) > 1:
        result["mapping_status"] = "AMBIGUOUS_FORWARD"
        result["target_scope"] = "MULTIPLE"
        return result

    mapped = forward[0]
    length_changed = mapped.length != source.length
    result.update(
        {
            "target_scope": "IN_SCOPE" if mapped.chrom in allowed_target else "OUT_OF_SCOPE",
            "length_changed": length_changed,
            "forward_chrom": mapped.chrom,
            "forward_start0": mapped.start,
            "forward_end": mapped.end,
            "forward_length": mapped.length,
            "forward_strand": mapped.strand,
        }
    )
    if not reverse:
        result["mapping_status"] = (
            "LENGTH_CHANGED_REVERSE_UNMAPPED"
            if length_changed
            else "NONRECIPROCAL_REVERSE_UNMAPPED"
        )
        return result
    if len(reverse) > 1:
        result["mapping_status"] = (
            "LENGTH_CHANGED_REVERSE_AMBIGUOUS" if length_changed else "AMBIGUOUS_REVERSE"
        )
        return result

    returned = reverse[0]
    exact = (
        returned.chrom == source.chrom
        and returned.start == source.start
        and returned.end == source.end
    )
    result.update(
        {
            "reverse_chrom": returned.chrom,
            "reverse_start0": returned.start,
            "reverse_end": returned.end,
            "reverse_length": returned.length,
            "reverse_strand": returned.strand,
            "reverse_exact_source_interval": exact,
        }
    )
    if exact and not length_changed and mapped.chrom in allowed_target:
        result["mapping_status"] = "UNIQUE_RECIPROCAL_SAME_LENGTH"
        result["qualified_unique_reciprocal_same_length"] = True
    elif exact and not length_changed:
        result["mapping_status"] = "TARGET_OUT_OF_SCOPE_RECIPROCAL_SAME_LENGTH"
    elif exact:
        result["mapping_status"] = "LENGTH_CHANGED_RECIPROCAL"
    elif length_changed:
        result["mapping_status"] = "LENGTH_CHANGED_NONRECIPROCAL"
    else:
        result["mapping_status"] = "NONRECIPROCAL_COORDINATE"
    return result


def write_outcomes(path: Path, outcomes: Sequence[dict[str, object]]) -> None:
    fields = [
        "row_id",
        "mapping_id",
        "source_chrom",
        "source_start0",
        "source_end",
        "source_length",
        "state",
        "score",
        "strand",
        "tile_id",
        "source_scope",
        "mapping_status",
        "target_scope",
        "qualified_unique_reciprocal_same_length",
        "forward_count",
        "reverse_count",
        "length_changed",
        "forward_chrom",
        "forward_start0",
        "forward_end",
        "forward_length",
        "forward_strand",
        "reverse_chrom",
        "reverse_start0",
        "reverse_end",
        "reverse_length",
        "reverse_strand",
        "reverse_exact_source_interval",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow({field: outcome.get(field, "") for field in fields})


def probe_liftover(liftover: Path) -> dict[str, object]:
    """Record the official binary's usage/version text without requiring success."""
    result = subprocess.run([str(liftover)], text=True, capture_output=True, check=False)
    text = (result.stdout + result.stderr).strip()
    return {"returncode": result.returncode, "output": text[:4000]}


def run_synthetic_cli_smoke(liftover: Path, output: Path) -> dict[str, object]:
    """Exercise the real liftOver CLI with tiny plus- and minus-strand chains."""
    output.mkdir(parents=True, exist_ok=False)
    chains = output / "synthetic_chains"
    chains.mkdir()
    # UCSC liftOver consumes the tName side of these old-to-new chain files
    # as its input.  The first block is a plus-strand offset; the second is a
    # full minus-strand block whose inverse is supplied in the reverse chain.
    forward_chain = chains / "forward.chain"
    forward_chain.write_text(
        "chain 100 chr2 100 + 0 100 chr2 200 + 50 150 1\n"
        "100\n\n"
        "chain 100 chr3 100 + 0 100 chr3 200 - 90 190 2\n"
        "100\n\n",
        encoding="utf-8",
    )
    reverse_chain = chains / "reverse.chain"
    reverse_chain.write_text(
        "chain 100 chr2 200 + 50 150 chr2 100 + 0 100 1\n"
        "100\n\n"
        "chain 100 chr3 200 + 10 110 chr3 100 - 0 100 2\n"
        "100\n\n",
        encoding="utf-8",
    )
    source_rows = [
        SourceInterval(1, "r000000001", "chr2", 10, 20, "FP", "0", "+", "plus"),
        SourceInterval(2, "r000000002", "chr2", 20, 30, "FP", "0", ".", "dot"),
        SourceInterval(3, "r000000003", "chr3", 0, 100, "FN", "0", "+", "minus"),
    ]
    input_bed = output / "synthetic_input.bed"
    write_forward_input(input_bed, source_rows, {"chr2", "chr3"})
    forward_mapped = output / "synthetic_forward.bed"
    forward_unmapped = output / "synthetic_forward.unmapped"
    run_liftover(
        liftover,
        input_bed,
        forward_chain,
        forward_mapped,
        forward_unmapped,
        output / "synthetic_forward.log",
        multiple=True,
        min_match=0.95,
        bed_plus=6,
    )
    forward_rows = parse_lifted_bed(forward_mapped)
    forward_by_id: dict[str, list[LiftedInterval]] = collections.defaultdict(list)
    for row in forward_rows:
        forward_by_id[row.mapping_id].append(row)
    if any(len(forward_by_id[row.mapping_id]) != 1 for row in source_rows):
        raise AssertionError("synthetic forward chain did not produce one row per source")
    plus = forward_by_id["r000000001"][0]
    minus = forward_by_id["r000000003"][0]
    if (plus.chrom, plus.start, plus.end) != ("chr2", 60, 70):
        raise AssertionError(f"plus-strand coordinate mismatch: {plus}")
    dot = forward_by_id["r000000002"][0]
    if (dot.chrom, dot.start, dot.end) != ("chr2", 70, 80):
        raise AssertionError(f"dot-strand coordinate mismatch: {dot}")
    if dot.strand != ".":
        raise AssertionError(f"dot-strand value was not retained: {dot.strand!r}")
    if dot.tile_id != "dot":
        raise AssertionError("liftOver did not preserve the dot-strand identity column")
    if (minus.chrom, minus.start, minus.end) != ("chr3", 10, 110):
        raise AssertionError(f"minus-strand coordinate mismatch: {minus}")
    if minus.strand != "-":
        raise AssertionError(f"minus-strand orientation was not retained: {minus.strand!r}")
    if plus.tile_id != "plus" or minus.tile_id != "minus":
        raise AssertionError("liftOver did not preserve BED extra columns")

    reverse_input = output / "synthetic_reverse_input.bed"
    write_reverse_input(reverse_input, forward_rows)
    reverse_mapped = output / "synthetic_reverse.bed"
    reverse_unmapped = output / "synthetic_reverse.unmapped"
    run_liftover(
        liftover,
        reverse_input,
        reverse_chain,
        reverse_mapped,
        reverse_unmapped,
        output / "synthetic_reverse.log",
        multiple=True,
        min_match=0.95,
        bed_plus=6,
    )
    reverse_rows = parse_lifted_bed(reverse_mapped)
    reverse_by_id: dict[str, list[LiftedInterval]] = collections.defaultdict(list)
    for row in reverse_rows:
        reverse_by_id[row.mapping_id].append(row)
    outcomes = [
        classify_interval(
            row,
            forward_by_id[row.mapping_id],
            reverse_by_id[row.mapping_id],
            {"chr2", "chr3"},
            {"chr2", "chr3"},
        )
        for row in source_rows
    ]
    if any(row["mapping_status"] != "UNIQUE_RECIPROCAL_SAME_LENGTH" for row in outcomes):
        raise AssertionError(f"synthetic reciprocal qualification failed: {outcomes}")
    summary = {
        "status": "LIFTOVER_SYNTHETIC_CLI_SMOKE_PASS",
        "liftover": str(liftover),
        "bed_plus": 6,
        "multiple": True,
        "source_rows": len(source_rows),
        "forward_rows": len(forward_rows),
        "reverse_rows": len(reverse_rows),
        "plus_forward": {"chrom": plus.chrom, "start0": plus.start, "end": plus.end},
        "dot_forward": {
            "chrom": dot.chrom,
            "start0": dot.start,
            "end": dot.end,
            "strand": dot.strand,
        },
        "minus_forward": {
            "chrom": minus.chrom,
            "start0": minus.start,
            "end": minus.end,
            "strand": minus.strand,
        },
        "reciprocal_statuses": [row["mapping_status"] for row in outcomes],
        "target_annotations_read": False,
        "f1_computed": False,
    }
    (output / "smoke_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return summary


def build_summary(
    config: dict,
    source_rows: Sequence[SourceInterval],
    outcomes: Sequence[dict[str, object]],
    forward_rows: Sequence[LiftedInterval],
    reverse_rows: Sequence[LiftedInterval],
    liftover: Path,
    liftover_probe: dict[str, object],
    output: Path,
) -> dict[str, object]:
    status_counts = collections.Counter(str(row["mapping_status"]) for row in outcomes)
    state_counts = collections.Counter(row.state for row in source_rows)
    state_status: dict[str, dict[str, int]] = {}
    for state in VALID_STATES:
        state_status[state] = dict(
            collections.Counter(
                str(row["mapping_status"]) for row in outcomes if row["state"] == state
            )
        )
    target_counts = collections.Counter(str(row["target_scope"]) for row in outcomes)
    qualified = [
        row for row in outcomes if row["qualified_unique_reciprocal_same_length"] is True
    ]
    return {
        "status": "MAPPING_QUALIFICATION_COMPLETED",
        "protocol": config.get("protocol", "HG19_CHM13_MAPPING_QUALIFICATION"),
        "source_interval_count": len(source_rows),
        "source_state_counts": dict(state_counts),
        "outcome_counts": dict(status_counts),
        "outcome_counts_by_state": state_status,
        "target_scope_counts": dict(target_counts),
        "forward_mapped_row_count": len(forward_rows),
        "reverse_mapped_row_count": len(reverse_rows),
        "qualified_unique_reciprocal_same_length_count": len(qualified),
        "qualified_source_bp": int(sum(int(row["source_length"]) for row in qualified)),
        "allowed_source_chromosomes": config["allowed_source_chromosomes"],
        "allowed_target_chromosomes": config["allowed_target_chromosomes"],
        "forbidden_source_chromosomes": config["forbidden_source_chromosomes"],
        "forbidden_target_chromosomes": config["forbidden_target_chromosomes"],
        "min_match": config["min_match"],
        "multiple": config["multiple"],
        "bed_plus": config["bed_plus"],
        "interval_source": str(resolve_path(Path(config["root"]), config["intervals"])),
        "forward_chain": str(resolve_path(Path(config["root"]), config["forward_chain"])),
        "reverse_chain": str(resolve_path(Path(config["root"]), config["reverse_chain"])),
        "liftOver": {
            "path": str(liftover),
            "source_url": config["liftOver_source_url"],
            "probe": liftover_probe,
        },
        "target_annotations_read": False,
        "f1_computed": False,
        "length_changed_mappings_counted_as_same_coordinate": False,
        "outputs": {
            "interval_outcomes": str(output / "interval_outcomes.tsv"),
            "forward_mapped": str(output / "forward_mapped.bed"),
            "forward_unmapped": str(output / "forward_unmapped.txt"),
            "reverse_mapped": str(output / "reverse_mapped.bed"),
            "reverse_unmapped": str(output / "reverse_unmapped.txt"),
        },
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    root = args.root.resolve()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    config["root"] = str(root)
    allowed_source = set(config["allowed_source_chromosomes"])
    allowed_target = set(config["allowed_target_chromosomes"])
    if not config.get("multiple", False):
        raise ValueError("mapping qualification requires liftOver -multiple")
    if int(config.get("bed_plus", 0)) != 6:
        raise ValueError("mapping qualification requires liftOver -bedPlus=6")
    intervals = resolve_path(root, config["intervals"])
    forward_chain = resolve_path(root, config["forward_chain"])
    reverse_chain = resolve_path(root, config["reverse_chain"])
    liftover = args.liftover.resolve()
    output = args.output.resolve()
    if not intervals.is_file():
        raise FileNotFoundError(f"formal EVAL interval export not found: {intervals}")
    if not forward_chain.is_file() or not reverse_chain.is_file():
        raise FileNotFoundError("both reciprocal chain files are required")
    output.mkdir(parents=True, exist_ok=False)

    source_rows = parse_source_intervals(intervals, allowed_source)
    eligible_rows = [row for row in source_rows if row.chrom in allowed_source]
    forward_input = output / "forward_input.bed"
    forward_count = write_forward_input(forward_input, source_rows, allowed_source)
    forward_mapped_path = output / "forward_mapped.bed"
    forward_unmapped_path = output / "forward_unmapped.txt"
    forward_log = output / "forward_liftOver.log"
    if forward_count:
        run_liftover(
            liftover,
            forward_input,
            forward_chain,
            forward_mapped_path,
            forward_unmapped_path,
            forward_log,
            multiple=bool(config["multiple"]),
            min_match=float(config["min_match"]),
            bed_plus=int(config["bed_plus"]),
        )
    else:
        forward_mapped_path.touch()
        forward_unmapped_path.touch()
        forward_log.write_text("skipped: no in-scope source intervals\n", encoding="utf-8")
    forward_rows = parse_lifted_bed(forward_mapped_path)
    source_ids = {row.mapping_id for row in eligible_rows}
    unknown_forward_ids = {row.mapping_id for row in forward_rows} - source_ids
    if unknown_forward_ids:
        raise ValueError(f"forward liftOver emitted unknown mapping IDs: {sorted(unknown_forward_ids)}")

    reverse_input = output / "reverse_input.bed"
    reverse_count = write_reverse_input(reverse_input, forward_rows)
    reverse_mapped_path = output / "reverse_mapped.bed"
    reverse_unmapped_path = output / "reverse_unmapped.txt"
    reverse_log = output / "reverse_liftOver.log"
    if reverse_count:
        run_liftover(
            liftover,
            reverse_input,
            reverse_chain,
            reverse_mapped_path,
            reverse_unmapped_path,
            reverse_log,
            multiple=bool(config["multiple"]),
            min_match=float(config["min_match"]),
            bed_plus=int(config["bed_plus"]),
        )
    else:
        reverse_mapped_path.touch()
        reverse_unmapped_path.touch()
        reverse_log.write_text("skipped: no forward mappings\n", encoding="utf-8")
    reverse_rows = parse_lifted_bed(reverse_mapped_path)
    unknown_reverse_ids = {row.mapping_id for row in reverse_rows} - source_ids
    if unknown_reverse_ids:
        raise ValueError(f"reverse liftOver emitted unknown mapping IDs: {sorted(unknown_reverse_ids)}")

    forward_by_id: dict[str, list[LiftedInterval]] = collections.defaultdict(list)
    reverse_by_id: dict[str, list[LiftedInterval]] = collections.defaultdict(list)
    for row in forward_rows:
        forward_by_id[row.mapping_id].append(row)
    for row in reverse_rows:
        reverse_by_id[row.mapping_id].append(row)
    outcomes = [
        classify_interval(
            row,
            forward_by_id.get(row.mapping_id, []),
            reverse_by_id.get(row.mapping_id, []),
            allowed_source,
            allowed_target,
        )
        for row in source_rows
    ]
    write_outcomes(output / "interval_outcomes.tsv", outcomes)
    liftover_probe = probe_liftover(liftover)
    summary = build_summary(
        config,
        source_rows,
        outcomes,
        forward_rows,
        reverse_rows,
        liftover,
        liftover_probe,
        output,
    )
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "completion.json").write_text(
        json.dumps(
            {
                "status": summary["status"],
                "target_annotations_read": False,
                "f1_computed": False,
                "summary": str(output / "summary.json"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--liftover", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_synthetic_cli_smoke(args.liftover.resolve(), args.output.resolve())
    else:
        if args.config is None:
            parser.error("--config is required unless --self-test is used")
        run(args)


if __name__ == "__main__":
    main()
