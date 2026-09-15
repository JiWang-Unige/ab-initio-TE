"""Describe overlap of frozen P/R gains and losses; do not change scoring/gates."""
import json
from pathlib import Path


def main():
    repo = Path(__file__).resolve().parents[2]
    source = Path(
        "reports/P3-TIBERIUS-BASE-MASK-20260911-R1/"
        "full-r1-score-12710872/result.json"
    )
    result = json.loads((repo / source).read_text())
    comparisons = result["comparisons"]
    out = {
        "source": str(source),
        "analysis": "post_hoc_descriptive_overlap_of_existing_locus_matches",
        "unit": "(core, reference_locus_id) from the frozen scorer",
        "original_decision_unchanged": result["decision"],
    }
    for kind in ("gained_units", "lost_units"):
        p = {tuple(x) for x in comparisons["P_minus_U"][kind]}
        r = {tuple(x) for x in comparisons["R_minus_U"][kind]}
        out[kind] = {
            "P_count": len(p),
            "R_count": len(r),
            "shared_count": len(p & r),
            "shared_units": sorted(p & r),
            "P_only_units": sorted(p - r),
            "R_only_units": sorted(r - p),
        }
    out["P_vs_R"] = {
        kind: comparisons["P_minus_R"][kind]
        for kind in ("gained_units", "lost_units")
    }
    target = repo / "docs/manuscript/20260915/tiberius-locus-overlap.json"
    target.write_text(json.dumps(out, indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    main()
