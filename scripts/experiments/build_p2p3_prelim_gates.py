#!/usr/bin/env python3
"""Build preliminary P2/P3 gate evidence from existing backup UCSC labels.

This is a pre-claim evidence pack only. The source labels are external/UCSC or
legacy downloaded annotations, not final self-run RepeatMasker+Dfam Label-A.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / ".backup" / "data"
GENOMES = BACKUP / "genome_data" / "current_eukaryotes"
TABLES = BACKUP / "tables"
OUT = ROOT / "reports" / "gates" / "P2P3_PRELIM_UCSC_20260615"

ANNOT_INV = TABLES / "current_eukaryotes_annotation_inventory.tsv"
TARGET_MANIFEST = TABLES / "eukaryote_target_species_manifest.tsv"

LEN_BINS = [
    ("lt100", 0, 100),
    ("100_500", 100, 500),
    ("500_1000", 500, 1000),
    ("1000_2048", 1000, 2048),
    ("2048_4096", 2048, 4096),
    ("4096_8192", 4096, 8192),
    ("gt8192", 8192, None),
]

SEX_OR_ORGANELLE = {
    "chrx",
    "chry",
    "chrm",
    "chrmt",
    "mt",
    "mitochondrion",
    "chloroplast",
    "pt",
}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def open_maybe_gzip(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open()


def md5_short(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_species_dir(kingdom_en: str, species_code: str) -> Path | None:
    kingdom_dir = {
        "Animal": "animals",
        "Plant": "plants",
        "Fungus": "fungi",
    }.get(kingdom_en)
    if not kingdom_dir:
        return None
    p = GENOMES / kingdom_dir / species_code
    return p if p.exists() else None


def file_in_species_dir(species_dir: Path | None, filename: str) -> Path | None:
    if not species_dir or not filename:
        return None
    p = species_dir / filename
    return p if p.exists() else None


def find_first(species_dir: Path | None, patterns: tuple[str, ...]) -> Path | None:
    if not species_dir:
        return None
    for pattern in patterns:
        matches = sorted(species_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def chrom_sizes(species_dir: Path | None, fasta_name: str) -> list[tuple[str, int]]:
    if not species_dir:
        return []
    candidates = list(species_dir.glob("*.chrom.sizes*"))
    if not candidates and fasta_name:
        fai = species_dir / f"{fasta_name}.fai"
        if fai.exists():
            candidates = [fai]
    if not candidates:
        candidates = sorted(species_dir.glob("*.fai"))
    if not candidates:
        return []

    rows: list[tuple[str, int]] = []
    with candidates[0].open() as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            try:
                rows.append((parts[0], int(parts[1])))
            except ValueError:
                continue
    return rows


def is_main_chrom(chrom: str) -> bool:
    c = chrom.lower()
    if c in SEX_OR_ORGANELLE:
        return False
    if "random" in c or "unplaced" in c or "alt" in c or "hap" in c:
        return False
    return True


def length_bin(length: int) -> str:
    for name, lo, hi in LEN_BINS:
        if length >= lo and (hi is None or length < hi):
            return name
    return "unknown"


def read_bed_stats(path: Path | None) -> dict[str, object]:
    stats: dict[str, object] = {
        "interval_count": 0,
        "bp_sum": 0,
        "by_bin": Counter(),
        "by_superfamily": Counter(),
        "by_chrom": Counter(),
        "by_chrom_count": Counter(),
        "short_lt100_count": 0,
        "long_gt8192_count": 0,
    }
    if not path:
        return stats
    with open_maybe_gzip(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            try:
                start = int(parts[1])
                end = int(parts[2])
            except ValueError:
                continue
            length = max(0, end - start)
            if length == 0:
                continue
            sf = parts[8] if len(parts) > 8 and parts[8] else (parts[6] if len(parts) > 6 else "UNKNOWN")
            stats["interval_count"] += 1
            stats["bp_sum"] += length
            stats["by_bin"][length_bin(length)] += length
            stats["by_superfamily"][sf] += length
            stats["by_chrom"][parts[0]] += length
            stats["by_chrom_count"][parts[0]] += 1
            if length < 100:
                stats["short_lt100_count"] += 1
            if length > 8192:
                stats["long_gt8192_count"] += 1
    return stats


def non_te_repeat_bp(path: Path | None) -> int:
    if not path:
        return 0
    hard_classes = ("simple", "low_complexity", "satellite", "tandem", "trf", "rRNA", "tRNA")
    total = 0
    with open_maybe_gzip(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 7:
                continue
            cls = "\t".join(parts[6:9]).lower()
            if any(x.lower() in cls for x in hard_classes):
                try:
                    total += max(0, int(parts[2]) - int(parts[1]))
                except ValueError:
                    continue
    return total


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inv = read_tsv(ANNOT_INV)
    target = {r["folder"]: r for r in read_tsv(TARGET_MANIFEST)}

    species_rows = []
    chrom_rows = []
    len_rows = []
    sf_rows = []
    u_rows = []
    gate_rows = []
    issues = []

    for row in inv:
        code = row["species_code"]
        kingdom = row["kingdom_en"]
        species_dir = find_species_dir(kingdom, code)
        fasta = file_in_species_dir(species_dir, row.get("fasta_file", ""))
        te_bed = file_in_species_dir(species_dir, row.get("annotation_file", ""))
        repeats_bed = find_first(species_dir, ("rmsk_repeats.bed.gz", "*rmsk_repeats*.bed.gz", "*rmsk*repeats*.bed.gz"))
        sizes = chrom_sizes(species_dir, row.get("fasta_file", ""))
        te_stats = read_bed_stats(te_bed)
        hardn_bp = non_te_repeat_bp(repeats_bed)
        trow = target.get(code, {})

        source_regime = "external_ucsc_or_legacy_prelim"
        claim_eligible = "no"
        reason = "preliminary external labels; final claim requires self-run RepeatMasker+Dfam Label-A"
        has_te = str(row.get("has_te_interval_annotation", "")).lower() == "true"

        species_rows.append({
            "species_code": code,
            "kingdom": kingdom,
            "scientific_name": row.get("scientific_name", ""),
            "taxid": "",
            "target_set": row.get("target_set", ""),
            "role_from_backup": row.get("training_scope", ""),
            "priority_from_target_manifest": trow.get("priority", ""),
            "clade_group": trow.get("clade_group", ""),
            "genome_bp": row.get("genome_bp", ""),
            "annotation_status": row.get("annotation_status", ""),
            "has_te_interval_annotation": str(has_te),
            "fasta_path": str(fasta) if fasta else "",
            "te_bed_path": str(te_bed) if te_bed else "",
            "repeats_bed_path": str(repeats_bed) if repeats_bed else "",
            "fasta_md5": md5_short(fasta) if fasta and fasta.exists() and fasta.stat().st_size < 50_000_000 else "skipped_large_or_missing",
            "source_label_regime": source_regime,
            "claim_eligible": claim_eligible,
            "claim_block_reason": reason,
        })

        if not species_dir:
            issues.append(f"{code}: species directory missing")
        if not fasta:
            issues.append(f"{code}: FASTA missing")
        if not te_bed and has_te:
            issues.append(f"{code}: inventory says TE annotation exists but file missing")

        main_sizes = [(c, n) for c, n in sizes if is_main_chrom(c)]
        main_sizes.sort(key=lambda x: x[1], reverse=True)
        primary = main_sizes[0] if main_sizes else ("", 0)
        stability = main_sizes[1] if len(main_sizes) > 1 else ("", 0)
        for role, chrom_tuple in (("primary", primary), ("stability_check", stability)):
            chrom, size = chrom_tuple
            if not chrom:
                continue
            chrom_rows.append({
                "species_code": code,
                "kingdom": kingdom,
                "role": role,
                "chrom": chrom,
                "chrom_size": size,
                "te_bp_raw_sum": te_stats["by_chrom"].get(chrom, 0),
                "te_interval_count": te_stats["by_chrom_count"].get(chrom, 0),
                "te_fraction_raw_sum": f"{(te_stats['by_chrom'].get(chrom, 0) / size) if size else 0:.6f}",
                "selection_status": "prelim_auto_largest_nonsex",
                "claim_eligible": "no",
            })

        base_len = {
            "species_code": code,
            "kingdom": kingdom,
            "scientific_name": row.get("scientific_name", ""),
            "annotation_status": row.get("annotation_status", ""),
            "interval_count": te_stats["interval_count"],
            "te_bp_raw_sum": te_stats["bp_sum"],
            "short_lt100_count": te_stats["short_lt100_count"],
            "long_gt8192_count": te_stats["long_gt8192_count"],
            "source_label_regime": source_regime,
        }
        for name, _, _ in LEN_BINS:
            base_len[f"bp_{name}"] = te_stats["by_bin"].get(name, 0)
        len_rows.append(base_len)

        for sf, bp in te_stats["by_superfamily"].most_common():
            sf_rows.append({
                "species_code": code,
                "kingdom": kingdom,
                "superfamily": sf,
                "te_bp_raw_sum": bp,
                "species_genome_bp": row.get("genome_bp", ""),
                "source_label_regime": source_regime,
            })

        genome_bp = int(row.get("genome_bp") or 0)
        repeat_bp = int(float(row.get("all_annotated_repeat_bp") or 0))
        u_bp_proxy = max(0, genome_bp - repeat_bp)
        u_rows.append({
            "species_code": code,
            "kingdom": kingdom,
            "annotation_status": row.get("annotation_status", ""),
            "genome_bp": genome_bp,
            "all_annotated_repeat_bp": repeat_bp,
            "u_bp_proxy_genome_minus_annotated_repeat": u_bp_proxy,
            "hardn_bp_from_rmsk_repeats_simple_low_satellite_proxy": hardn_bp,
            "rn_status": "not_constructed",
            "u_quality_status": "prelim_proxy_only",
            "claim_eligible": "no",
        })

    gate_rows.extend([
        {
            "gate": "CHROM-LADDER",
            "status": "PRELIM_PARTIAL",
            "evidence": "species_manifest_prelim.tsv; chromosome_ladder_prelim.tsv",
            "remaining": "manual role freeze; self-run Label-A provenance; homology/near-duplicate leakage report",
        },
        {
            "gate": "TE-LEN-VIZ",
            "status": "PRELIM_PARTIAL",
            "evidence": "te_len_viz_summary_prelim.tsv",
            "remaining": "plots; Label-A/B overlay; claim-eligible self-run labels",
        },
        {
            "gate": "LABEL-CONCORDANCE",
            "status": "BLOCKED_NO_LABEL_B",
            "evidence": "none",
            "remaining": "produce Label-B from RepeatModeler2/EDTA/HiTE or selected audit source",
        },
        {
            "gate": "U-QUALITY",
            "status": "PRELIM_PROXY_ONLY",
            "evidence": "u_quality_prelim.tsv",
            "remaining": "construct RN/hardN masks; interval overlaps; independent evidence; self-run labels",
        },
        {
            "gate": "SF-TARGET",
            "status": "PRELIM_PARTIAL",
            "evidence": "sf_target_step1_prelim.tsv",
            "remaining": "per-kingdom threshold decision; Label-A/B concordance; freeze refs/dossiers/sf_target_set.md",
        },
        {
            "gate": "WIN-MATRIX",
            "status": "PRELIM_INPUT_ONLY",
            "evidence": "te_len_viz_summary_prelim.tsv",
            "remaining": "backbone context limits; GPU smoke; refs/dossiers/window_matrix.md freeze",
        },
    ])

    write_tsv(OUT / "species_manifest_prelim.tsv", species_rows, [
        "species_code", "kingdom", "scientific_name", "taxid", "target_set", "role_from_backup",
        "priority_from_target_manifest", "clade_group", "genome_bp", "annotation_status",
        "has_te_interval_annotation", "fasta_path", "te_bed_path", "repeats_bed_path", "fasta_md5",
        "source_label_regime", "claim_eligible", "claim_block_reason",
    ])
    write_tsv(OUT / "chromosome_ladder_prelim.tsv", chrom_rows, [
        "species_code", "kingdom", "role", "chrom", "chrom_size", "te_bp_raw_sum",
        "te_interval_count", "te_fraction_raw_sum", "selection_status", "claim_eligible",
    ])
    len_fields = [
        "species_code", "kingdom", "scientific_name", "annotation_status", "interval_count",
        "te_bp_raw_sum", "short_lt100_count", "long_gt8192_count",
    ] + [f"bp_{name}" for name, _, _ in LEN_BINS] + ["source_label_regime"]
    write_tsv(OUT / "te_len_viz_summary_prelim.tsv", len_rows, len_fields)
    write_tsv(OUT / "sf_target_step1_prelim.tsv", sf_rows, [
        "species_code", "kingdom", "superfamily", "te_bp_raw_sum", "species_genome_bp", "source_label_regime",
    ])
    write_tsv(OUT / "u_quality_prelim.tsv", u_rows, [
        "species_code", "kingdom", "annotation_status", "genome_bp", "all_annotated_repeat_bp",
        "u_bp_proxy_genome_minus_annotated_repeat", "hardn_bp_from_rmsk_repeats_simple_low_satellite_proxy",
        "rn_status", "u_quality_status", "claim_eligible",
    ])
    write_tsv(OUT / "gate_status.tsv", gate_rows, ["gate", "status", "evidence", "remaining"])

    summary = {
        "source": ".backup/data (UCSC/external/legacy labels)",
        "claim_eligible": False,
        "species_total": len(species_rows),
        "species_with_te_annotation": sum(1 for r in species_rows if r["has_te_interval_annotation"] == "True"),
        "issues_count": len(issues),
        "issues_sample": issues[:50],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    readme = f"""# P2/P3 Preliminary Gate Evidence Pack

Date: 2026-06-15

Source: `.backup/data` existing UCSC/external/legacy downloads and derived tables.

Claim eligibility: **NO**. This pack is for engineering rehearsal and route planning only. Final claim-bearing runs require self-run RepeatMasker+Dfam Label-A with versioned software/library manifests, then rerunning these gates.

## Outputs

- `species_manifest_prelim.tsv`: preliminary species/input inventory.
- `chromosome_ladder_prelim.tsv`: automatic largest non-sex/non-organelle chromosome candidates.
- `te_len_viz_summary_prelim.tsv`: TE interval length-bin summary from existing `rmsk_te.bed.gz`.
- `sf_target_step1_prelim.tsv`: preliminary species x superfamily bp table.
- `u_quality_prelim.tsv`: proxy-only U/hardN summary; RN is not constructed.
- `gate_status.tsv`: current gate status and remaining blockers.
- `summary.json`: machine-readable pack summary.

## Interpretation

`LABEL-CONCORDANCE` remains blocked because no independent Label-B audit source is present in this pack. `WIN-MATRIX` has only length-distribution input, not backbone context limits or GPU smoke. `U-QUALITY` is only a proxy because RN/hardN masks and interval-level contamination checks are not constructed.

## Summary

- Species rows: {summary['species_total']}
- Species with interval TE annotation: {summary['species_with_te_annotation']}
- Issues detected: {summary['issues_count']}
"""
    (OUT / "README.md").write_text(readme)


if __name__ == "__main__":
    main()
