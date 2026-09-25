#!/usr/bin/env python3
"""Prepare common unannotated-reference HISAT2 alignments for all mask arms."""
import argparse
import json
from pathlib import Path
import shlex
from common import ROOT, NAME, OUT, container, dump, native, state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("species", choices=["chicken", "zebrafish"])
    species = parser.parse_args().species
    config = json.loads((ROOT / "configs" / (NAME + ".inputs.json")).read_text())
    cfg = config["rna"][species]
    if cfg["status"] != "FROZEN" or sum(m["bytes"] for r in cfg["runs"] for m in r["mates"]) > 25000000000:
        raise ValueError("RNA inputs not frozen or exceed per-species budget")
    masks = OUT / species / "masks"
    if json.loads((masks / "status.json").read_text())["status"] != "MASKS_READY":
        raise ValueError("shared uppercase assembly is not ready")
    out = OUT / species / "rna"
    out.mkdir(parents=True, exist_ok=False)
    result = state("deployment short-read RNA alignment", species)
    result["input"] = cfg
    dump(out / "status.json", result)
    try:
        prefix = container(out)
        native(prefix + ["hisat2", "--version"], out, "hisat2-version")
        native(prefix + ["samtools", "--version"], out, "samtools-version")
        (out / "fastq").mkdir()
        (out / "index").mkdir()
        for run in cfg["runs"]:
            for number, mate in enumerate(run["mates"], 1):
                target = out / "fastq" / (run["accession"] + f"_{number}.fastq.gz")
                native(["curl", "--fail", "--location", "--retry", "2", "--max-time", "21600",
                        "--dump-header", str(target) + ".headers", "--output", str(target), mate["url"]],
                       out, run["accession"] + f"-mate{number}-download")
                if target.stat().st_size != mate["bytes"]:
                    raise ValueError("RNA download length differs from frozen ENA metadata")
        index = out / "index/genome"
        native(prefix + ["hisat2-build", "-p", "16", str(masks / "red_genome/genome.fa"), str(index)], out, "hisat2-build")
        bams = []
        for run in cfg["runs"]:
            accession = run["accession"]
            bam = out / (accession + ".bam")
            align = ["hisat2", "-p", "12", "--dta", "--new-summary", "--summary-file", str(out / (accession + ".hisat2-summary.txt")),
                     "-x", str(index), "-1", str(out / "fastq" / (accession + "_1.fastq.gz")),
                     "-2", str(out / "fastq" / (accession + "_2.fastq.gz"))]
            sort = ["samtools", "sort", "-@", "3", "-m", "2G", "-o", str(bam), "-"]
            native(prefix + ["bash", "-o", "pipefail", "-c", shlex.join(align) + " | " + shlex.join(sort)],
                   out, accession + "-align")
            native(prefix + ["samtools", "quickcheck", "-v", str(bam)], out, accession + "-quickcheck")
            native(prefix + ["samtools", "index", "-@", "4", str(bam)], out, accession + "-index")
            native(prefix + ["samtools", "flagstat", "-@", "4", str(bam)], out, accession + "-flagstat")
            bams.append(str(bam))
        result.update(status="RNA_READY", bam_paths=bams,
                      mapping_rule="HISAT2 --dta default unstranded alignment to uppercase exact assembly; no known splice site or GTF input")
    except Exception as exc:
        result.update(status="FAILED", error=repr(exc))
        raise
    finally:
        dump(out / "status.json", result)


if __name__ == "__main__":
    main()
