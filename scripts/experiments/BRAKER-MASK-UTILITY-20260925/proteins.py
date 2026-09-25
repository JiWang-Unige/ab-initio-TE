#!/usr/bin/env python3
"""Acquire one frozen external protein library and remove both target species."""
from collections import Counter
import gzip
import json
from common import ROOT, NAME, OUT, dump, native, state


def main():
    cfg = json.loads((ROOT / "configs" / (NAME + ".inputs.json")).read_text())["protein"]
    out = OUT / "inputs/proteins"
    out.mkdir(parents=True, exist_ok=False)
    result = state("external protein acquisition and target exclusion")
    result["input"] = cfg
    dump(out / "status.json", result)
    try:
        archive = out / "Vertebrata.odb12.fa.gz"
        native(["curl", "--fail", "--location", "--retry", "2", "--max-time", "18000",
                "--dump-header", str(out / "download.headers"), "--output", str(archive), cfg["url"]], out, "download")
        if archive.stat().st_size != cfg["observed_content_length"]:
            raise ValueError("protein download length differs from frozen metadata")
        counts, excluded = Counter(), set(map(str, cfg["excluded_species_taxids"]))
        kept = bases = 0
        include = False
        with gzip.open(archive, "rt") as src, (out / "vertebrata.exclude-chicken-zebrafish.fa").open("w") as dest:
            for line in src:
                if line.startswith(">"):
                    identifier = line[1:].split()[0]
                    taxid = identifier.split("_", 1)[0]
                    if not taxid.isdigit() or "_" not in identifier:
                        raise ValueError("unrecognized OrthoDB taxonomy header: " + identifier)
                    counts[taxid] += 1
                    include = taxid not in excluded
                    kept += include
                elif include:
                    bases += len(line.strip())
                if include:
                    dest.write(line)
        if not kept or not bases:
            raise ValueError("empty deployment library")
        result.update(status="PROTEINS_READY", species_taxon_counts=dict(counts),
                      excluded_counts={k: counts[k] for k in sorted(excluded)},
                      kept_records=kept, kept_amino_acids=bases,
                      protein_fasta=str(out / "vertebrata.exclude-chicken-zebrafish.fa"))
    except Exception as exc:
        result.update(status="FAILED", error=repr(exc))
        raise
    finally:
        dump(out / "status.json", result)


if __name__ == "__main__":
    main()
