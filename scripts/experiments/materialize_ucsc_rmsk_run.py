#!/usr/bin/env python3
"""Materialize UCSC RepeatMasker annotations into a run-like directory."""

from __future__ import annotations

import argparse
import csv
import gzip
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from process_ucsc_repeatmasker_te import (  # noqa: E402
    bed_score,
    keep_class,
    source_rows,
)


FIELDS = [
    "species_code",
    "scientific_name",
    "ucsc_db",
    "source_format",
    "local_source",
    "source_url",
    "notes",
]


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def copy_or_download(row: dict[str, str], raw_dir: Path, force: bool) -> Path:
    source_format = row["source_format"]
    suffix_by_format = {
        "ucsc_table": "rmsk.txt.gz",
        "repeatmasker_out": "repeatmasker.out.gz",
        "bed": "rmsk_source.bed.gz",
    }
    suffix = suffix_by_format.get(source_format)
    if suffix is None:
        raise SystemExit(f"{row['species_code']}: unsupported source_format={source_format}")
    raw_gz = raw_dir / f"{row['species_code']}.{suffix}"
    if raw_gz.exists() and raw_gz.stat().st_size > 0 and not force:
        return raw_gz

    local = Path(row["local_source"]) if row.get("local_source") else None
    if local and local.exists() and local.stat().st_size > 0:
        if local.suffix == ".gz":
            shutil.copyfile(local, raw_gz)
        else:
            with local.open("rb") as inp, gzip.open(raw_gz, "wb") as out:
                shutil.copyfileobj(inp, out)
        return raw_gz

    url = row.get("source_url", "")
    if not url:
        raise FileNotFoundError(f"{row['species_code']}: no local_source and no source_url")
    subprocess.run(
        [
            "curl",
            "-fL",
            "-C",
            "-",
            "--retry",
            "5",
            "--retry-delay",
            "10",
            "-o",
            str(raw_gz),
            url,
        ],
        check=True,
    )
    return raw_gz


def decompress_raw(source: Path, out_path: Path, force: bool) -> None:
    if out_path.exists() and out_path.stat().st_size > 0 and not force:
        return
    with gzip.open(source, "rt") as inp, out_path.open("w") as out:
        shutil.copyfileobj(inp, out)


def bed_source_rows(path: Path):
    with open_text(path) as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 6:
                continue
            rep_class = fields[6] if len(fields) > 6 else ""
            rep_family = fields[7] if len(fields) > 7 else ""
            yield {
                "chrom": fields[0],
                "start": fields[1],
                "end": fields[2],
                "name": fields[3] if len(fields) > 3 else ".",
                "score": fields[4] if len(fields) > 4 else "0",
                "strand": fields[5] if len(fields) > 5 else ".",
                "class": rep_class,
                "family": rep_family,
            }


def iter_rows(source: Path, source_format: str):
    if source_format == "bed":
        yield from bed_source_rows(source)
    else:
        yield from source_rows(source, source_format)


def write_bed_outputs(source: Path, source_format: str, species_dir: Path, species_code: str) -> dict[str, object]:
    totals: dict[str, object] = {
        "total_records": 0,
        "strict_records": 0,
        "plus_unknown_records": 0,
    }
    class_counts: Counter[str] = Counter()
    kept_counts = {"strict": Counter(), "plus_unknown": Counter()}
    outputs = {
        "strict": species_dir / f"{species_code}.rmsk_te_strict.bed",
        "plus_unknown": species_dir / f"{species_code}.rmsk_te_plus_unknown.bed",
    }

    with outputs["strict"].open("w") as strict_out, outputs["plus_unknown"].open("w") as plus_out:
        for row in iter_rows(source, source_format):
            totals["total_records"] = int(totals["total_records"]) + 1
            rep_class = row["class"] or ""
            class_counts[rep_class] += 1
            combined = f"{row['class']}/{row['family']}" if row["family"] else row["class"]
            bed_line = (
                "\t".join(
                    [
                        row["chrom"],
                        row["start"],
                        row["end"],
                        row["name"],
                        bed_score(row["score"]),
                        row["strand"],
                        row["class"],
                        row["family"],
                        combined,
                    ]
                )
                + "\n"
            )
            if keep_class(rep_class, "strict"):
                strict_out.write(bed_line)
                totals["strict_records"] = int(totals["strict_records"]) + 1
                kept_counts["strict"][rep_class] += 1
            if keep_class(rep_class, "plus_unknown"):
                plus_out.write(bed_line)
                totals["plus_unknown_records"] = int(totals["plus_unknown_records"]) + 1
                kept_counts["plus_unknown"][rep_class] += 1

    totals["all_classes"] = ";".join(f"{k}:{v}" for k, v in sorted(class_counts.items()))
    totals["strict_classes"] = ";".join(f"{k}:{v}" for k, v in sorted(kept_counts["strict"].items()))
    totals["plus_unknown_classes"] = ";".join(
        f"{k}:{v}" for k, v in sorted(kept_counts["plus_unknown"].items())
    )
    return totals


def summary_status(metrics: dict[str, object]) -> str:
    total = int(metrics["total_records"])
    plus_unknown = int(metrics["plus_unknown_records"])
    if total == 0:
        return "OK_EMPTY_SOURCE_WARNING"
    if plus_unknown == 0:
        return "OK_ZERO_TE_AFTER_FILTER_WARNING"
    return "OK"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--species-code", help="Materialize only one species_code from the manifest.")
    parser.add_argument("--no-run-summary", action="store_true", help="Do not rewrite run-level README/species_manifest.")
    parser.add_argument("--collect-summary", action="store_true", help="Only collect per-species SUMMARY.tsv files.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest = Path(args.manifest)
    run_root = Path(args.run_root)
    run_root.mkdir(parents=True, exist_ok=True)

    if args.collect_summary:
        summaries = sorted(run_root.glob("*/SUMMARY.tsv"))
        if not summaries:
            raise SystemExit(f"No per-species summaries found under {run_root}")
        rows: list[dict[str, str]] = []
        fields: list[str] | None = None
        for path in summaries:
            with path.open(newline="") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                path_rows = list(reader)
                if not path_rows:
                    continue
                fields = reader.fieldnames if fields is None else fields
                rows.extend(path_rows)
        if not rows or fields is None:
            raise SystemExit(f"No summary rows found under {run_root}")
        with (run_root / "species_manifest.tsv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        (run_root / "README.md").write_text(
            "# UCSC RepeatMasker Animal Reference Run\n\n"
            "Run-like materialization of UCSC RepeatMasker annotations for species listed in "
            "`docs/species_label_source_audit.md`.\n\n"
            "Each species directory contains a decompressed raw annotation file, two decompressed "
            "TE-only BED files, `SUMMARY.tsv`, `COMPLETE`, and `raw/` with the copied/downloaded "
            "compressed source.\n\n"
            "Primary strict TE filter keeps LINE/SINE/LTR/DNA/RC/Retroposon. "
            "`plus_unknown` additionally keeps Unknown/Unspecified.\n"
        )
        return

    with manifest.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    missing = [field for field in FIELDS if field not in (rows[0].keys() if rows else [])]
    if missing:
        raise SystemExit(f"{manifest}: missing required columns: {','.join(missing)}")
    if args.species_code:
        rows = [row for row in rows if row["species_code"] == args.species_code]
        if not rows:
            raise SystemExit(f"{args.species_code}: not found in {manifest}")

    summary_rows: list[dict[str, object]] = []
    for row in rows:
        species = row["species_code"]
        species_dir = run_root / species
        raw_dir = species_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_gz = copy_or_download(row, raw_dir, args.force)

        if row["source_format"] == "ucsc_table":
            raw_text_name = f"{species}.ucsc.rmsk.txt"
        elif row["source_format"] == "repeatmasker_out":
            raw_text_name = f"{species}.repeatmasker.out"
        elif row["source_format"] == "bed":
            raw_text_name = f"{species}.source.bed"
        else:
            raise SystemExit(f"{species}: unsupported source_format={row['source_format']}")
        raw_text = species_dir / raw_text_name
        decompress_raw(raw_gz, raw_text, args.force)

        metrics = write_bed_outputs(raw_gz, row["source_format"], species_dir, species)
        complete = species_dir / "COMPLETE"
        complete.touch()

        summary_rows.append(
            {
                "species_code": species,
                "scientific_name": row["scientific_name"],
                "ucsc_db": row["ucsc_db"],
                "source_format": row["source_format"],
                "raw_compressed": raw_gz,
                "raw_decompressed": raw_text,
                "strict_bed": species_dir / f"{species}.rmsk_te_strict.bed",
                "plus_unknown_bed": species_dir / f"{species}.rmsk_te_plus_unknown.bed",
                "total_records": metrics["total_records"],
                "strict_records": metrics["strict_records"],
                "plus_unknown_records": metrics["plus_unknown_records"],
                "notes": row.get("notes", ""),
                "status": summary_status(metrics),
            }
        )

        per_species_summary = species_dir / "SUMMARY.tsv"
        with per_species_summary.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=list(summary_rows[-1].keys()))
            writer.writeheader()
            writer.writerow(summary_rows[-1])

    if not args.no_run_summary:
        summary_path = run_root / "species_manifest.tsv"
        with summary_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

        readme = run_root / "README.md"
        readme.write_text(
            "# UCSC RepeatMasker Animal Reference Run\n\n"
            "Run-like materialization of UCSC RepeatMasker annotations for species listed in "
            "`docs/species_label_source_audit.md`.\n\n"
            "Each species directory contains a decompressed raw annotation file, two decompressed "
            "TE-only BED files, `SUMMARY.tsv`, `COMPLETE`, and `raw/` with the copied/downloaded "
            "compressed source.\n\n"
            "Primary strict TE filter keeps LINE/SINE/LTR/DNA/RC/Retroposon. "
            "`plus_unknown` additionally keeps Unknown/Unspecified.\n"
        )


if __name__ == "__main__":
    main()
