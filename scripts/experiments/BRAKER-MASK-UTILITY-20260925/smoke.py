#!/usr/bin/env python3
"""Exercise native ETP on the bundled engineering example, never score it."""
import os
import shutil
from collections import Counter
from common import OUT, IMAGE, container, dump, native, state


def main():
    out = OUT / ("smoke-" + os.environ["SLURM_JOB_ID"])
    out.mkdir(parents=True, exist_ok=False)
    result = state("native ETP bundled example")
    dump(out / "status.json", result)
    try:
        shutil.copytree(IMAGE / "opt/Augustus/config", out / "augustus-config")
        argv = container(out) + ["braker.pl", "--genome=/opt/BRAKER/example/genome.fa",
            "--prot_seq=/opt/BRAKER/example/proteins.fa", "--bam=/opt/BRAKER/example/RNAseq.bam",
            "--workingdir=/work/run", "--species=te_etp_smoke_20260925",
            "--AUGUSTUS_CONFIG_PATH=/work/augustus-config", "--threads=8",
            "--gm_max_intergenic=10000", "--skipOptimize"]
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
        result.update(status="ETP_EXAMPLE_COMPLETE", features=dict(features),
                      final_gtf=str(gtf), scientific_result=False,
                      intermediate_files=[str(p.relative_to(out)) for p in (out / "run").rglob("*.gtf")])
    except Exception as exc:
        result.update(status="FAILED", error=repr(exc))
        raise
    finally:
        dump(out / "status.json", result)


if __name__ == "__main__":
    main()
