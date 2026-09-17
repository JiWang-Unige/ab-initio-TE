#!/usr/bin/env python3
"""Hand-computable checks for the observed RNA-evidence failure modes."""
from pathlib import Path
import subprocess
import sys
import tempfile

import summarize_evidence as summary


def sam(name, position, cigar, flag=0, nh=1):
    return f"{name}\t{flag}\tchr1\t{position}\t60\t{cigar}\t*\t0\t0\t*\t*\tNH:i:{nh}\n"


with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    source, output = root / "reads.sam", root / "junctions.tsv"
    # All alignments span the same inclusive intron 111..210. The first two
    # records are mates, the next two are distinct SRA templates with short
    # anchors, and the last record is a multimapper that must not contribute.
    source.write_text(sam("SRR1.1", 101, "10M100N10M") + sam("SRR1.1", 101, "10M100N10M")
                      + sam("SRR1.2", 107, "4M100N10M") + sam("SRR1.3", 107, "4M100N10M")
                      + sam("SRR1.4", 101, "10M100N10M", nh=2))
    subprocess.run([sys.executable, str(Path(__file__).with_name("extract_junctions.py")),
                    "--sam", str(source), "--out", str(output)], check=True, capture_output=True)
    assert output.read_text() == "chr1\t111\t210\t3\t1\t10\n"
    junctions = summary.parse_junctions(output)
    candidate = {"candidate_id": "test", "seqname": "chr1", "strand": "+",
                 "exons": [[101, 110], [211, 220]], "arms": ["D"], "occurrences": []}
    intron = ((111, 210),)
    # RNA full chain has different terminal UTR boundaries but identical
    # splice chain. It should support the intron endpoint, not full equality.
    evidence = summary.candidate_evidence(candidate, junctions,
                 {("chr1", "+", intron): True}, {("chr1", intron): True},
                 {("chr1", "+", ((95, 110), (211, 240))): True}, {})
    assert evidence["stringtie_exact_intron_chain"]
    assert not evidence["stringtie_exact_full_chain"]
    assert not evidence["all_introns_strict"]
    candidate["exons"] = [[101, 110]]
    evidence = summary.candidate_evidence(candidate, junctions, {}, {}, {}, {})
    assert evidence["strict_intron_fraction"] is None
    assert not evidence["stringtie_exact_intron_chain"]
    for parser in (summary.parse_junctions, summary.parse_stringtie):
        try:
            parser(root / "absent")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("missing native output must not become no RNA support")
print("PASS: QNAME/mate accounting, NH filtering, per-template anchors, intron coordinates, UTR boundaries, one-exon and missing-output semantics.")
