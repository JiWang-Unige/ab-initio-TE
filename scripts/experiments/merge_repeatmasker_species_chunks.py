#!/usr/bin/env python3
"""Merge chunked RepeatMasker outputs into per-species files."""

from __future__ import annotations

import argparse
import csv
import gzip
import shutil
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)


def open_maybe_gzip(path: Path, mode: str):
    if path.suffix == ".gz":
        return gzip.open(path, mode)
    return path.open(mode)


def append_text_inputs(inputs: list[Path], output: Path, skip_headers: bool) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    line_count = 0
    with gzip.open(output, "wt") as out:
        for i, path in enumerate(inputs):
            with open_maybe_gzip(path, "rt") as handle:
                for line_no, line in enumerate(handle):
                    if skip_headers and i > 0 and line_no < 3 and line.startswith(("SW", "score", "There were no")):
                        continue
                    out.write(line)
                    line_count += 1
    return line_count


def concat_binary_inputs(inputs: list[Path], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    bytes_written = 0
    with gzip.open(output, "wb") as out:
        for path in inputs:
            with open_maybe_gzip(path, "rb") as handle:
                shutil.copyfileobj(handle, out)
            bytes_written += path.stat().st_size
    return bytes_written


def first_existing(chunk_dir: Path, suffixes: list[str]) -> Path | None:
    for suffix in suffixes:
        matches = sorted(chunk_dir.glob(f"*{suffix}"))
        if matches:
            return matches[0]
    return None


def require_chunk_file(chunk: dict[str, str], suffixes: list[str], label: str) -> Path:
    chunk_dir = Path(chunk["output_dir"])
    path = first_existing(chunk_dir, suffixes)
    if path is None:
        suffix_list = ",".join(suffixes)
        raise FileNotFoundError(
            f"{chunk['species_code']}:{chunk['chunk_id']} missing {label} output "
            f"in {chunk_dir} (expected one of {suffix_list})"
        )
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-manifest", required=True)
    parser.add_argument("--species-manifest", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--species-code", help="Merge only one species_code from the manifest.")
    parser.add_argument("--force", action="store_true", help="Rebuild merged files even if species COMPLETE exists.")
    args = parser.parse_args()

    chunk_manifest = Path(args.chunk_manifest)
    species_manifest = Path(args.species_manifest)

    chunks_by_species: dict[str, list[dict[str, str]]] = defaultdict(list)
    with chunk_manifest.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            chunks_by_species[row["species_code"]].append(row)

    species_rows: list[dict[str, str]]
    with species_manifest.open(newline="") as handle:
        species_rows = list(csv.DictReader(handle, delimiter="\t"))

    for row in species_rows:
        species = row["species_code"]
        if args.species_code and species != args.species_code:
            continue
        species_out = Path(row["species_output_dir"])
        species_out.mkdir(parents=True, exist_ok=True)
        complete = species_out / "COMPLETE"

        if row["action"] == "skip_existing_complete":
            (species_out / "SKIPPED_EXISTING_COMPLETE").write_text(row["reason"] + "\n")
            continue
        if row["action"] != "submit_chunked":
            (species_out / "BLOCKED").write_text(row["reason"] + "\n")
            continue
        if complete.exists() and not args.force:
            continue

        chunks = sorted(chunks_by_species[species], key=lambda r: int(r["chunk_index"]))
        missing = [r["chunk_id"] for r in chunks if not (Path(r["output_dir"]) / "COMPLETE").exists()]
        if missing:
            raise SystemExit(f"{species}: missing chunk COMPLETE markers: {','.join(missing[:20])}")

        out_files: list[Path] = []
        gff_files: list[Path] = []
        tbl_files: list[Path] = []
        masked_files: list[Path] = []
        final_missing: list[str] = []
        for chunk in chunks:
            try:
                out_files.append(require_chunk_file(chunk, [".fa.out.gz", ".fa.out"], "out"))
                gff_files.append(require_chunk_file(chunk, [".fa.out.gff.gz", ".fa.out.gff"], "gff"))
                tbl_files.append(require_chunk_file(chunk, [".fa.tbl.gz", ".fa.tbl"], "tbl"))
                masked_files.append(require_chunk_file(chunk, [".fa.masked.gz", ".fa.masked"], "masked"))
            except FileNotFoundError as exc:
                final_missing.append(str(exc))
        if final_missing:
            preview = "\n".join(final_missing[:20])
            raise SystemExit(
                f"{species}: chunk COMPLETE markers are insufficient; missing final outputs:\n{preview}"
            )

        metadata = species_out / "MERGE_METADATA.txt"
        with metadata.open("w") as meta:
            meta.write(f"run_id={args.run_id}\n")
            meta.write(f"species_code={species}\n")
            meta.write(f"scientific_name={row['scientific_name']}\n")
            meta.write(f"repeatmasker_species={row['repeatmasker_species']}\n")
            meta.write(f"source_fasta={row['source_fasta']}\n")
            meta.write(f"chunk_count={len(chunks)}\n")
            meta.write(f"chunk_bases={row['chunk_bases']}\n")
            meta.write("repeatmasker_flags=-xsmall -gff; no -a\n")

        outputs = {
            f"{species}.repeatmasker.out.gz": (out_files, True),
            f"{species}.repeatmasker.out.gff.gz": (gff_files, False),
            f"{species}.repeatmasker.tbl.gz": (tbl_files, True),
        }
        with metadata.open("a") as meta:
            for filename, (inputs, skip_headers) in outputs.items():
                if inputs:
                    line_count = append_text_inputs(inputs, species_out / filename, skip_headers=skip_headers)
                    meta.write(f"{filename}\tinputs={len(inputs)}\tlines={line_count}\n")
            if masked_files:
                bytes_seen = concat_binary_inputs(masked_files, species_out / f"{species}.repeatmasker.masked.fa.gz")
                meta.write(f"{species}.repeatmasker.masked.fa.gz\tinputs={len(masked_files)}\tinput_compressed_bytes={bytes_seen}\n")
            for path in sorted(species_out.glob(f"{species}.repeatmasker.*.gz")):
                meta.write(f"merged_file\t{path.name}\t{path.stat().st_size}\n")

        complete.touch()


if __name__ == "__main__":
    main()
