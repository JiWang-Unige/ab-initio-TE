#!/usr/bin/env python3
"""Run one predeclared complete ETP arm with common RNA/protein inputs."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
from common import OUT, IMAGE, container, dump, native, state


def ready(path, expected):
    value = json.loads(path.read_text())
    if value["status"] != expected:
        raise ValueError(f"input is not ready: {path} ({value['status']})")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("species", choices=["chicken", "zebrafish"])
    parser.add_argument("arm", choices=["D", "RM2_FULL", "RED_FULL"])
    args = parser.parse_args()
    # Real example output, not just versions, is required before expensive work.
    smokes = list(OUT.glob("smoke-*/status.json"))
    if not any(json.loads(p.read_text())["status"] == "ETP_EXAMPLE_COMPLETE" for p in smokes):
        raise ValueError("native ETP example has not completed")
    ready(OUT / args.species / "masks/status.json", "MASKS_READY")
    proteins = ready(OUT / "inputs/proteins/status.json", "PROTEINS_READY")
    rna = ready(OUT / args.species / "rna/status.json", "RNA_READY")
    evaluation = ready(OUT / "evaluation/preparation.json", "EVALUATION_READY")
    ready(Path(evaluation["species"]["zebrafish"]["evaluation_dir"]) / "long-read-denominators.json",
          "LONG_READ_DENOMINATORS_FIXED")
    out = OUT / args.species / "arms" / args.arm
    out.mkdir(parents=True, exist_ok=False)
    result = state("complete native BRAKER ETP", args.species)
    result["arm"] = args.arm
    dump(out / "status.json", result)
    try:
        shutil.copytree(IMAGE / "opt/Augustus/config", out / "augustus-config")
        genome = OUT / args.species / "masks" / (args.arm + ".fa")
        argv = container(out) + ["braker.pl", "--genome=" + str(genome),
            "--prot_seq=" + proteins["protein_fasta"], "--bam=" + ",".join(rna["bam_paths"]),
            "--workingdir=/work/run", f"--species=te_etp_{args.species}_{args.arm.lower()}_20260925",
            "--AUGUSTUS_CONFIG_PATH=/work/augustus-config", "--threads=16"]
        result["input_sources"] = {"rna": rna, "protein_fasta": proteins["protein_fasta"], "masked_genome": str(genome)}
        dump(out / "status.json", result)
        result["native"] = native(argv, out, "braker")
        gtf = out / "run/braker.gtf"
        features = Counter()
        with gtf.open() as handle:
            for line in handle:
                if line.startswith("#") or not line.strip():
                    continue
                fields = line.rstrip().split("\t")
                if len(fields) != 9 or int(fields[3]) > int(fields[4]):
                    raise ValueError("malformed final GTF")
                features[fields[2]] += 1
        if not features["CDS"]:
            raise ValueError("no final CDS")
        result.update(status="PREDICTION_READY", final_gtf=str(gtf), features=dict(features),
                      scientifically_scored=False)
    except Exception as exc:
        result.update(status="FAILED", error=repr(exc))
        raise
    finally:
        dump(out / "status.json", result)


if __name__ == "__main__":
    main()
