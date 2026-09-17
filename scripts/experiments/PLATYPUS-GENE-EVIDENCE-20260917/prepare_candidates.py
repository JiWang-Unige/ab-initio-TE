#!/usr/bin/env python3
"""Create the blind prediction union and the fixed 20-core mapping panel."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ARMS = {
    "D": "d_gtf",
    "U_soft": "u_soft_gtf",
    "R_TE": "r_te_gtf",
}


def attrs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in text.rstrip(";").split(";"):
        item = item.strip()
        if not item:
            continue
        match = re.match(r"([^\s]+)\s+\"([^\"]*)\"$", item)
        if match:
            out[match.group(1)] = match.group(2)
        else:
            key, _, value = item.partition(" ")
            out[key] = value.strip('"')
    return out


def parse_gtf(path: Path) -> dict[tuple, dict]:
    transcripts: dict[tuple, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"{path}:{line_no}: expected 9 GTF columns")
            seqname, _source, feature, start, end, _score, strand, _frame, raw_attrs = fields
            if feature != "exon":
                continue
            a = attrs(raw_attrs)
            tid = a.get("transcript_id")
            gid = a.get("gene_id")
            if not tid or not gid:
                raise ValueError(f"{path}:{line_no}: exon lacks gene_id/transcript_id")
            key = (seqname, strand, tid)
            row = transcripts.setdefault(
                key,
                {
                    "seqname": seqname,
                    "strand": strand,
                    "gene_id": gid,
                    "transcript_id": tid,
                    "exons": [],
                },
            )
            row["exons"].append([int(start), int(end)])
    for row in transcripts.values():
        row["exons"] = sorted(set(tuple(x) for x in row["exons"]))
        if not row["exons"]:
            raise ValueError(f"{path}: transcript has no exon")
    return transcripts


def introns(exons: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(left[1] + 1, right[0] - 1) for left, right in zip(exons, exons[1:])]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geometry", type=Path, required=True)
    ap.add_argument("--prepared-regions", type=Path, required=True)
    ap.add_argument("--d-gtf-template", required=True)
    ap.add_argument("--u-soft-gtf-template", required=True)
    ap.add_argument("--r-te-gtf-template", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    geometry = json.loads(args.geometry.read_text(encoding="utf-8"))
    if len(geometry) != 20:
        raise SystemExit(f"expected the fixed 20-core geometry, got {len(geometry)}")
    templates = {
        "D": args.d_gtf_template,
        "U_soft": args.u_soft_gtf_template,
        "R_TE": args.r_te_gtf_template,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    candidates: dict[tuple, dict] = {}
    arm_counts: dict[str, int] = {}
    for core in geometry:
        core_id = core["id"]
        for arm, template in templates.items():
            path = Path(template.format(core=core_id))
            if not path.is_file():
                raise FileNotFoundError(path)
            parsed = parse_gtf(path)
            arm_counts[arm] = arm_counts.get(arm, 0) + len(parsed)
            for row in parsed.values():
                exons = tuple(tuple(x) for x in row["exons"])
                key = (row["seqname"], row["strand"], exons)
                candidate = candidates.setdefault(
                    key,
                    {
                        "candidate_id": f"cand_{len(candidates):07d}",
                        "seqname": row["seqname"],
                        "strand": row["strand"],
                        "exons": [list(x) for x in exons],
                        "arms": [],
                        "occurrences": [],
                    },
                )
                if arm not in candidate["arms"]:
                    candidate["arms"].append(arm)
                candidate["occurrences"].append(
                    {
                        "arm": arm,
                        "core": core_id,
                        "gene_id": row["gene_id"],
                        "transcript_id": row["transcript_id"],
                        "gtf": str(path),
                    }
                )

    panel_fasta = args.out_dir / "blind_panel.fa"
    panel_manifest = []
    with panel_fasta.open("w", encoding="utf-8") as out:
        for core in geometry:
            core_id = core["id"]
            record_id = core["record_id"]
            sequence_path = args.prepared_regions / core_id / "sequence.txt"
            sequence = "".join(sequence_path.read_text(encoding="utf-8").split())
            if len(sequence) != 5_200_000:
                raise ValueError(f"{sequence_path}: expected 5,200,000 bases, got {len(sequence)}")
            out.write(f">{record_id}\n")
            for start in range(0, len(sequence), 80):
                out.write(sequence[start : start + 80] + "\n")
            panel_manifest.append(
                {
                    "core": core_id,
                    "record_id": record_id,
                    "chrom": core["chrom"],
                    "halo_start": core["halo_start"],
                    "halo_end": core["halo_end"],
                    "length": len(sequence),
                }
            )

    candidate_rows = list(candidates.values())
    for row in candidate_rows:
        row["arms"] = sorted(row["arms"])
        row["intron_count"] = len(row["exons"]) - 1
        row["introns"] = [list(x) for x in introns([tuple(x) for x in row["exons"]])]
        row["occurrences"] = sorted(row["occurrences"], key=lambda x: (x["arm"], x["core"], x["transcript_id"]))

    (args.out_dir / "blind_candidates.json").write_text(
        json.dumps(
            {
                "schema": "platypus_blind_gene_candidate_v1",
                "selection": "union of all D/U_soft/R_TE transcript exon chains on fixed 20 cores",
                "reference_annotation_used_for_selection": False,
                "candidate_count": len(candidate_rows),
                "arm_transcript_counts": arm_counts,
                "candidates": candidate_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    with (args.out_dir / "blind_candidates.tsv").open("w", encoding="utf-8") as out:
        out.write("candidate_id\tseqname\tstrand\tintron_count\tstart\tend\tarms\n")
        for row in candidate_rows:
            out.write(
                "\t".join(
                    [
                        row["candidate_id"],
                        row["seqname"],
                        row["strand"],
                        str(row["intron_count"]),
                        str(row["exons"][0][0]),
                        str(row["exons"][-1][1]),
                        ",".join(row["arms"]),
                    ]
                )
                + "\n"
            )
    (args.out_dir / "panel_manifest.json").write_text(
        json.dumps({"schema": "platypus_blind_panel_v1", "cores": panel_manifest}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"candidate_count": len(candidate_rows), "arm_transcript_counts": arm_counts}, indent=2))


if __name__ == "__main__":
    main()
