#!/usr/bin/env python3
"""Materialize deterministic 20-contig, 5-MiB panels from full FASTA files."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path


def fasta(path):
    opener = gzip.open if path.suffix == ".gz" else open
    name, parts = None, []
    with opener(path, "rt") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(parts).upper()
                header = line[1:].split()
                if not header:
                    raise ValueError(f"empty FASTA header at {path}:{line_number}")
                name, parts = header[0], []
            else:
                if name is None:
                    raise ValueError(f"sequence before FASTA header at {path}:{line_number}")
                parts.append(line)
    if name is not None:
        yield name, "".join(parts).upper()


def read_sizes(path: Path):
    sizes = {}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 2 or not fields[1].isdigit():
            raise ValueError(f"invalid sizes row {path}:{number}")
        if fields[0] in sizes:
            raise ValueError(f"duplicate source contig {fields[0]}")
        sizes[fields[0]] = int(fields[1])
    return sizes


def run(args):
    config = json.loads(args.config.read_text())
    spec = config["species"][args.species]
    width = int(config["selection"]["length_bp"])
    count = int(config["selection"]["contigs"])
    sizes = read_sizes(Path(spec["sizes"]))
    eligible = [(name, length) for name, length in sizes.items() if length >= width]
    selected = sorted(eligible, key=lambda item: (-item[1], item[0]))[:count]
    if len(selected) != count:
        raise ValueError(f"only {len(selected)} usable contigs; expected {count}")
    regions = []
    for index, (name, length) in enumerate(selected):
        start = (length - width) // 2
        regions.append({"panel_id": f"core{index:02d}", "source_seqid": name,
                        "assembly_length_bp": length, "start": start, "end": start + width})
    args.output.mkdir(parents=True, exist_ok=False)
    panel_path = args.output / "panel.fa"
    wanted = {row["source_seqid"]: row for row in regions}
    seen = set()
    with panel_path.open("x") as out:
        for name, sequence in fasta(Path(spec["fasta"])):
            if name not in wanted:
                continue
            if name in seen:
                raise ValueError(f"duplicate selected FASTA contig: {name}")
            seen.add(name)
            row = wanted[name]
            expected = sizes[name]
            if len(sequence) != expected:
                raise ValueError(f"FASTA/sizes mismatch {name}: {len(sequence)} != {expected}")
            sequence = sequence[row["start"]:row["end"]]
            if len(sequence) != width:
                raise ValueError(f"wrong panel length for {name}")
            out.write(f">{row['panel_id']}\n")
            for offset in range(0, len(sequence), 80):
                out.write(sequence[offset:offset + 80] + "\n")
    if seen != set(wanted):
        raise ValueError(f"missing selected FASTA contigs: {sorted(set(wanted) - seen)}")
    result = {"status": "PREPARED", "species": args.species, "source": spec,
              "selection": config["selection"], "regions": regions,
              "total_bp": width * count, "labels_used_in_selection": False,
              "scores_used_in_selection": False, "panel_fasta": str(panel_path.resolve())}
    (args.output / "panel.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--species", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
