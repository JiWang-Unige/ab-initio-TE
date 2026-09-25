#!/usr/bin/env python3
"""Reuse fixed D/RM2 annotation and train native RED on complete assemblies."""
import argparse
from collections import defaultdict
import json
from itertools import zip_longest
import os
from pathlib import Path
from common import ROOT, OUT, dump, fasta, write_record, native, state


def intervals(path, rm=False):
    rows = defaultdict(list)
    with path.open() as handle:
        for line in handle:
            fields = line.split()
            if not fields or (rm and not fields[0].isdigit()):
                continue
            if rm:
                chrom, start, end = fields[4], int(fields[5]) - 1, int(fields[6])
            else:
                chrom, start, end = fields[0], int(fields[1]), int(fields[2])
            if start < 0 or end <= start:
                raise ValueError("bad interval in " + str(path))
            rows[chrom].append((start, end))
    merged = {}
    for chrom, values in rows.items():
        final = []
        for start, end in sorted(values):
            if final and start <= final[-1][1]:
                final[-1] = (final[-1][0], max(end, final[-1][1]))
            else:
                final.append((start, end))
        merged[chrom] = final
    return merged


def masked(sequence, runs):
    parts, previous = [], 0
    for start, end in runs:
        if start < previous or end > len(sequence):
            raise ValueError("mask coordinate outside sequence or overlapping")
        parts.extend([sequence[previous:start], sequence[start:end].translate(str.maketrans("ACGT", "acgt"))])
        previous = end
    parts.append(sequence[previous:])
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("species", choices=["chicken", "zebrafish"])
    species = parser.parse_args().species
    out = OUT / species / "masks"
    out.mkdir(parents=True, exist_ok=False)
    result = state("complete genome mask preparation", species)
    dump(out / "status.json", result)
    try:
        cfg = json.loads((ROOT / "configs/WHOLE-GENOME-BENCHMARK-20260918.json").read_text())
        genome = Path(cfg["species"][species]["fasta"])
        old = ROOT / "outputs/WHOLE-GENOME-BENCHMARK-20260918"
        source_d = old / "d" / species / "gpu/prediction/material_runs.bed"
        source_rm = old / "native" / species / "RM2-mask-recovery-v2/annotation.out"
        masks = {"D": intervals(source_d), "RM2_FULL": intervals(source_rm, rm=True)}
        result["sources"] = {"genome": str(genome), "D": str(source_d), "RM2_FULL": str(source_rm)}
        for directory in ("red_genome", "red_masked", "red_repeats"):
            (out / directory).mkdir()
        rows = []
        with (out / "red_genome/genome.fa").open("w") as upper, (out / "D.fa").open("w") as d, (out / "RM2_FULL.fa").open("w") as rm:
            for name, original in fasta(genome):
                seq = original.upper()
                write_record(upper, name, seq)
                row = {"record": name, "bp": len(seq), "source_lowercase_acgt": sum(original.count(c) for c in "acgt")}
                for arm, handle in (("D", d), ("RM2_FULL", rm)):
                    output = masked(seq, masks[arm].pop(name, []))
                    write_record(handle, name, output)
                    row[arm + "_mask_bp"] = sum(output.count(c) for c in "acgt")
                rows.append(row)
        if any(masks.values()):
            raise ValueError("mask records absent from source genome")
        result["records"] = rows
        dump(out / "status.json", result)
        result["red"] = native([str(ROOT / "refs/repos/Red/bin/Red"), "-gnm", str(out / "red_genome"),
            "-msk", str(out / "red_masked"), "-rpt", str(out / "red_repeats"),
            "-cor", os.environ.get("SLURM_CPUS_PER_TASK", "8"), "-frm", "2"], out, "red")
        files = list((out / "red_masked").glob("*.msk"))
        if len(files) != 1:
            raise ValueError("expected single full-genome RED mask output")
        with (out / "RED_FULL.fa").open("w") as dest:
            for index, pair in enumerate(zip_longest(fasta(genome), fasta(files[0]))):
                original, red = pair
                if original is None or red is None or original[0] != red[0] or original[1].upper() != red[1].upper():
                    raise ValueError("RED sequence/record mismatch")
                # Normalize only ambiguous lowercase symbols; keep ACGT mask.
                seq = "".join(c if c in "acgt" else c.upper() for c in red[1])
                rows[index]["RED_FULL_mask_bp"] = sum(seq.count(c) for c in "acgt")
                write_record(dest, red[0], seq)
        result.update(status="MASKS_READY", records=rows, sequence_identity="same ordered records and uppercase sequence; D/RM2 constructed in source coordinates; RED compared base-for-base")
    except Exception as exc:
        result.update(status="FAILED", error=repr(exc))
        raise
    finally:
        dump(out / "status.json", result)


if __name__ == "__main__":
    main()
