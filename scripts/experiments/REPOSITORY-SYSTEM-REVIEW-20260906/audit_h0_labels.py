"""Read-only ancestry audit; compare cached TRAIN/VAL labels, never TEST.

Inputs are unchanged copies from Baobab. The baseline painter is loaded from
the reviewed Git commit. No dataset, checkpoint, or scientific score is written.
"""
from __future__ import annotations

import argparse
import ast
import bisect
import collections
import gzip
import itertools
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASELINE = "b6b2c08b436c9fe5ce49b2af67f46690fdaa9350"
SOURCE = "pipelines/PIPE-TEFM-SUPP-20260617/prepare_ucsc_windows.py"
ALLOWED = {"train": {"chr1", "chr3", "chr5", "chr7", "chr9"},
           "val": {"chr11", "chr13", "chr15"}}


def painter(source):
    tree = ast.parse(source)
    body = ast.parse("from __future__ import annotations").body
    body += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "paint"]
    scope = {"bisect": bisect}
    exec(compile(ast.Module(body=body, type_ignores=[]), SOURCE, "exec"), scope)
    return scope["paint"]


def load_bed(path):
    intervals = collections.defaultdict(list)
    allowed = set.union(*ALLOWED.values())
    with path.open() as handle:
        for line in handle:
            fields = line.rstrip().split("\t")
            if len(fields) >= 3 and fields[0] in allowed:
                intervals[fields[0]].append((int(fields[1]), int(fields[2])))
    old, fixed = {}, {}
    for chrom, vals in intervals.items():
        vals.sort()
        ends = [b for _, b in vals]
        old[chrom] = (vals, ends)
        fixed[chrom] = (vals, list(itertools.accumulate(ends, max)))
    return old, fixed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    args = parser.parse_args()
    old_source = subprocess.check_output(["git", "show", f"{BASELINE}:{SOURCE}"], cwd=ROOT, text=True)
    paints = [painter(old_source), painter((ROOT / SOURCE).read_text())]
    bedroot = args.input_root / "software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_ANIMALS_20260617/human_hs1"
    strict = load_bed(bedroot / "human_hs1.rmsk_te_strict.bed")
    unknown = load_bed(bedroot / "human_hs1.rmsk_te_plus_unknown.bed")
    recipes = [
        ("ntv2_250m_H0", "tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w4096", 3000, 1200),
        ("ntv2_500m_H0", "tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick", 3000, 800),
    ]
    results = []
    for name, directory, train_n, val_n in recipes:
        for split, limit in (("train", train_n), ("val", val_n)):
            counts = collections.Counter()
            transitions = collections.Counter()
            examples = []
            path = args.input_root / "software_outputs" / directory / split / "data.jsonl.gz"
            with gzip.open(path, "rt") as handle:
                for line in itertools.islice(handle, limit):
                    rec = json.loads(line)
                    assert rec["chr"] in ALLOWED[split], (split, rec["chr"])
                    n = rec["end"] - rec["start"]
                    assert n == len(rec["labels"]) == len(rec["sequence"]) == 4096
                    repainted = []
                    for i, paint in enumerate(paints):
                        labels = [0] * n
                        paint(labels, rec["chr"], rec["start"], rec["end"], unknown[i], -100)
                        paint(labels, rec["chr"], rec["start"], rec["end"], strict[i], 1)
                        repainted.append(labels)
                    old, fixed = repainted
                    mismatch = sum(a != b for a, b in zip(rec["labels"], old))
                    changed = sum(a != b for a, b in zip(old, fixed))
                    counts.update(windows=1, bp=n, cached_old_mismatch_bp=mismatch,
                                  cached_old_mismatch_windows=int(mismatch > 0),
                                  changed_bp=changed, changed_windows=int(changed > 0))
                    transitions.update(f"{a}->{b}" for a, b in zip(old, fixed) if a != b)
                    if (changed or mismatch) and len(examples) < 5:
                        examples.append({"chr": rec["chr"], "start": rec["start"], "end": rec["end"],
                                         "changed_bp": changed, "cached_old_mismatch_bp": mismatch})
            assert counts["windows"] == limit, (name, split, counts["windows"], limit)
            results.append({"recipe": name, "split": split, **counts,
                            "attributable_to_painter": counts["cached_old_mismatch_bp"] == 0,
                            "transitions": dict(transitions), "examples": examples})
    print(json.dumps({"baseline_commit": BASELINE, "assembly": "hs1", "results": results,
                      "scope": "TRAIN/VAL cached input labels only; no test, predictions, or retraining"}, indent=2))


if __name__ == "__main__":
    main()
