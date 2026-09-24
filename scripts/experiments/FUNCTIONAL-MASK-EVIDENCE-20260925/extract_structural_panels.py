#!/usr/bin/env python3
"""Extract assembly-matched structural TE evidence for the functional panel.

This script reads only (i) the independently published zebrafish DOCX
supplement, (ii) frozen source coordinates transcribed from the chicken paper,
(iii) NCBI assembly reports, and (iv) the already fixed utility-panel geometry.
It never opens model masks, model predictions, gene scores, or D/U/R outputs.

Coordinates in the published tables are 1-based inclusive. Output coordinates
use both the source convention and 0-based half-open intervals for deterministic
intersection with the existing core/halo geometry.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "reports" / "FUNCTIONAL-MASK-EVIDENCE-20260925" / "evidence"
DEFAULT_ZB_DOCX = EVIDENCE / "zebrafish_zb_supplement" / "nested" / "Supplymental tables and figures.docx"
DEFAULT_ZB_REPORT = EVIDENCE / "assembly_reports" / "GCA_000002035.4_GRCz11_assembly_report.txt"
DEFAULT_CHICKEN_REPORT = EVIDENCE / "assembly_reports" / "GCA_000002315.5_GRCg6a_assembly_report.txt"
DEFAULT_CHICKEN_CORES = ROOT / "reports" / "NONMAMMAL-GENE-UTILITY-20260918" / "chicken" / "geometry.json"
DEFAULT_ZEBRAFISH_CORES = ROOT / "reports" / "NONMAMMAL-GENE-UTILITY-20260918" / "zebrafish" / "geometry.json"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def parse_assembly_report(path: Path) -> dict[str, dict[str, str]]:
    """Return accession -> assembly-report fields for primary molecules."""
    result: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 10 or fields[3] != "Chromosome" or fields[7] != "Primary Assembly":
            continue
        accession = fields[4]
        refseq = fields[6]
        # NCBI reports: Sequence-Role, Assigned-Molecule, Assigned-Molecule-Location,
        # GenBank-Accn, Relationship, RefSeq-Accn, Assembly-Unit, Sequence-Length,
        # UCSC-style-name. In current reports the field positions are fixed at
        # 0..9; keep explicit validation below so a column drift stops the audit.
        if not refseq.startswith("NC_"):
            continue
        result[refseq] = {
            "assigned_molecule": fields[2],
            "refseq_accession": refseq,
            "ucsc_name": fields[9],
            "length": fields[8],
            "assembly_unit": fields[7],
        }
    if not result:
        raise ValueError(f"no primary chromosome rows parsed from {path}")
    return result


def docx_tables(path: Path) -> list[list[list[str]]]:
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    tables: list[list[list[str]]] = []
    for table in root.findall(".//w:tbl", NS):
        rows: list[list[str]] = []
        for tr in table.findall("./w:tr", NS):
            cells: list[str] = []
            for tc in tr.findall("./w:tc", NS):
                text = " ".join("".join(tc.itertext()).split())
                cells.append(text)
            rows.append(cells)
        tables.append(rows)
    return tables


def extract_zb_table(path: Path, accession_map: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    tables = docx_tables(path)
    selected = None
    for table in tables:
        if not table or table[0][:6] != ["ID", "Length(Tn, bp)", "Length(Tpase, aa)", "Chr.", "Location", "TSD"]:
            continue
        if any(row and row[0] == "ZB_copy20" for row in table[1:]):
            selected = table
            break
    if selected is None:
        raise ValueError("Supplementary Table S4 with ZB_copy20 was not found")
    records: list[dict[str, object]] = []
    location_re = re.compile(r"^(?P<accession>(?:NC|NW)_\d+\.\d+):(?P<start>\d+)-(?P<end>\d+)$")
    for row in selected[1:]:
        if len(row) != 6:
            raise ValueError(f"unexpected ZB Table S4 row: {row}")
        ident, length, tpase, source_chr, location, tsd = row
        match = location_re.fullmatch(location)
        if not match:
            raise ValueError(f"unexpected ZB location {location}")
        accession = match.group("accession")
        start1, end1 = int(match.group("start")), int(match.group("end"))
        if end1 - start1 + 1 != int(length):
            raise ValueError(f"length mismatch for {ident}: {location} vs {length}")
        if tsd != "TA":
            raise ValueError(f"unexpected TSD for {ident}: {tsd}")
        assembly_row = accession_map.get(accession)
        if accession.startswith("NC_") and assembly_row is None:
            raise ValueError(f"primary chromosome accession missing from assembly report: {accession}")
        records.append({
            "species": "zebrafish",
            "assembly": "GCA_000002035.4/GRCz11",
            "panel_id": ident,
            "source_accession": accession,
            "source_chromosome": source_chr,
            "seqid": assembly_row["ucsc_name"] if assembly_row else accession,
            "start_1based": start1,
            "end_1based": end1,
            "start0": start1 - 1,
            "end0": end1,
            "orientation": ".",
            "evidence_class": "E_structural_full_length",
            # The paper says 19/20 copies are intact/putatively functional in
            # aggregate, but Table S4 does not identify the one exception.
            # Keep all rows as structural full-length candidates and defer a
            # per-copy autonomy label until an independent ORF/TIR check.
            "full_length_structural_candidate": True,
            "primary_autonomous_candidate": False,
            "autonomy_status": "pending_per_copy_ORF_TIR_rule; source reports 19/20 intact in aggregate",
            "length_bp": int(length),
            "transposase_aa": int(tpase),
            "tsd": tsd,
            "structural_rule": "published full-length 1597-bp element; 341-aa transposase; TA TSD; article reports 20 copies and 19 intact/putatively functional copies in aggregate",
            "orf_evidence": "source reports a 341-aa transposase ORF with DDE/DBD/NLS/GRPR domains; Supplementary Table S4 gives length but does not independently resolve start/stop integrity per copy",
            "experimental_validation": "ZB construct showed transposition activity in HepG2/HeLa and zebrafish enhancer-trapping assays; this does not validate autonomy of every endogenous copy",
            "source": "Supplementary Table S4, gkab045",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7913693/",
        })
    if len(records) != 20:
        raise ValueError(f"expected 20 ZB records, found {len(records)}")
    return records


def chicken_records() -> list[dict[str, object]]:
    """Coordinates explicitly printed in the GRCg6a source article.

    GGERV20's reported >=65 full-length copies have no coordinate table in the
    accessible article; that population count is recorded separately and is
    deliberately not converted into candidate loci here.
    """
    return [
        {
            "species": "chicken",
            "assembly": "GCA_000002315.5/GRCg6a",
            "panel_id": "ALVE6_ALVE-JFevA",
            "source_accession": "NC_006088.5",
            "source_chromosome": "1",
            "seqid": "chr1",
            "start_1based": 210601,
            "end_1based": 214776,
            "start0": 210600,
            "end0": 214776,
            "orientation": "+",
            "evidence_class": "E_structural_partial",
            "full_length_structural_candidate": False,
            "primary_autonomous_candidate": False,
            "autonomy_status": "partial_or_truncated; sensitivity-only",
            "length_bp": 4176,
            "transposase_aa": "",
            "tsd": "GGCGCT at 3' end",
            "structural_rule": "exact GRCg6a insertion; source reports 5-prime truncation, retained ORFs and target-site duplication; sensitivity-only because it is not intact/autonomous",
            "orf_evidence": "source ORFs predicted with GLIMMER3; envelope described as intact, but current locus is 5-prime truncated",
            "experimental_validation": "paper cites historical envelope expression; no current-locus autonomous-activity assay",
            "source": "ALVE/GGERV20 article, Results paragraph on ALVE6",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7597685/",
        },
        {
            "species": "chicken",
            "assembly": "GCA_000002315.5/GRCg6a",
            "panel_id": "ALVE-JFevB",
            "source_accession": "NC_006088.5",
            "source_chromosome": "1",
            "seqid": "chr1",
            "start_1based": 32724216,
            "end_1based": 32731739,
            "start0": 32724215,
            "end0": 32731739,
            "orientation": "+",
            "evidence_class": "E_structural_autonomous_candidate",
            "full_length_structural_candidate": True,
            "primary_autonomous_candidate": True,
            "autonomy_status": "source-reported intact ORF/terminal structure; candidate pending sequence check",
            "length_bp": 7524,
            "transposase_aa": "",
            "tsd": "GGCTTG at both ends",
            "structural_rule": "exact GRCg6a insertion; intact 7524-bp ALVE with gag-pol and envelope ORFs, source reports replication-competent potential",
            "orf_evidence": "source ORFs predicted with GLIMMER3; intact gag-pol and envelope coordinates are reported, including the ribosomal -1 frameshift; no independent CDS start/stop assay in this study",
            "experimental_validation": "WGS junction evidence confirms the reference insertion across 142 chickens; replication-competent potential is a structural inference, not a direct virus-rescue assay here",
            "source": "ALVE/GGERV20 article, Results paragraph on ALVE-JFevB",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7597685/",
        },
    ]


def load_cores(path: Path) -> list[dict[str, object]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    required = {"id", "chrom", "start", "end", "halo_start", "halo_end"}
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"core row missing {sorted(missing)}: {row}")
    return rows


def overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def annotate_overlap(records: list[dict[str, object]], cores: list[dict[str, object]]) -> None:
    for record in records:
        matching = [c for c in cores if c["chrom"] == record["seqid"]]
        core_hit = None
        halo_hit = None
        core_bp = 0
        halo_bp = 0
        for core in matching:
            core_bp += overlap(int(record["start0"]), int(record["end0"]), int(core["start"]), int(core["end"]))
            halo_bp += overlap(int(record["start0"]), int(record["end0"]), int(core["halo_start"]), int(core["halo_end"]))
            if core_bp and core_hit is None:
                core_hit = core["id"]
            if halo_bp and halo_hit is None:
                halo_hit = core["id"]
        record["existing_core_overlap_bp"] = core_bp
        record["existing_halo_overlap_bp"] = halo_bp
        record["existing_core_id"] = core_hit or ""
        record["existing_halo_id"] = halo_hit or ""
        record["in_existing_core"] = bool(core_bp)
        record["in_existing_halo"] = bool(halo_bp)


def write_outputs(out_dir: Path, records: list[dict[str, object]], unresolved: list[dict[str, object]],
                  chicken_cores: list[dict[str, object]], zebrafish_cores: list[dict[str, object]],
                  args: argparse.Namespace) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "species", "assembly", "panel_id", "source_accession", "source_chromosome", "seqid",
        "start_1based", "end_1based", "start0", "end0", "orientation", "evidence_class",
        "full_length_structural_candidate", "primary_autonomous_candidate", "autonomy_status",
        "length_bp", "transposase_aa", "tsd", "structural_rule", "orf_evidence",
        "experimental_validation",
        "source", "source_url", "existing_core_overlap_bp", "existing_halo_overlap_bp",
        "existing_core_id", "existing_halo_id", "in_existing_core", "in_existing_halo",
    ]
    with (out_dir / "structural_panels.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    (out_dir / "unresolved_structural_sources.json").write_text(json.dumps(unresolved, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": "EXTRACTED_ASSEMBLY_MATCHED_STRUCTURAL_PANEL",
        "source_policy": "independent source records only; no D/U/R outputs read",
        "coordinate_convention": "source 1-based inclusive; output start0/end0 0-based half-open",
        "assemblies": {
            "chicken": "GCA_000002315.5/GRCg6a",
            "zebrafish": "GCA_000002035.4/GRCz11",
        },
        "candidate_counts": {
            "all_coordinate_resolved": len(records),
            "chicken": sum(r["species"] == "chicken" for r in records),
            "zebrafish": sum(r["species"] == "zebrafish" for r in records),
        "full_length_structural_candidates": sum(bool(r["full_length_structural_candidate"]) for r in records),
        "primary_autonomous_candidates": sum(bool(r["primary_autonomous_candidate"]) for r in records),
        "independent_source_family_units": 2,
        "family_unit_note": "The 22 loci are not 22 independent families: they are one chicken ALVE source family and one zebrafish ZB/Tc1-mariner source family, with GGERV20 population count unresolved.",
            "primary_in_existing_core": sum(bool(r["primary_autonomous_candidate"]) and bool(r["in_existing_core"]) for r in records),
            "primary_in_existing_halo": sum(bool(r["primary_autonomous_candidate"]) and bool(r["in_existing_halo"]) for r in records),
            "all_in_existing_core": sum(bool(r["in_existing_core"]) for r in records),
            "all_in_existing_halo": sum(bool(r["in_existing_halo"]) for r in records),
        },
        "existing_geometry": {
            "chicken": chicken_cores,
            "zebrafish": zebrafish_cores,
        },
        "unresolved_sources": unresolved,
        "inputs": {
            "zebrafish_docx": str(args.zebrafish_docx),
            "zebrafish_assembly_report": str(args.zebrafish_assembly_report),
            "chicken_assembly_report": str(args.chicken_assembly_report),
            "chicken_cores": str(args.chicken_cores),
            "zebrafish_cores": str(args.zebrafish_cores),
        },
    }
    (out_dir / "structural_panel_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zebrafish-docx", type=Path, default=DEFAULT_ZB_DOCX)
    parser.add_argument("--zebrafish-assembly-report", type=Path, default=DEFAULT_ZB_REPORT)
    parser.add_argument("--chicken-assembly-report", type=Path, default=DEFAULT_CHICKEN_REPORT)
    parser.add_argument("--chicken-cores", type=Path, default=DEFAULT_CHICKEN_CORES)
    parser.add_argument("--zebrafish-cores", type=Path, default=DEFAULT_ZEBRAFISH_CORES)
    parser.add_argument("--out-dir", type=Path, default=EVIDENCE / "structural_panels")
    args = parser.parse_args()
    chicken_map = parse_assembly_report(args.chicken_assembly_report)
    zebrafish_map = parse_assembly_report(args.zebrafish_assembly_report)
    if chicken_map["NC_006088.5"]["ucsc_name"] != "chr1":
        raise ValueError("GRCg6a NC_006088.5 does not map to chr1")
    chicken = chicken_records()
    for row in chicken:
        if row["source_accession"] not in chicken_map:
            raise ValueError(f"chicken source accession missing from GRCg6a report: {row['source_accession']}")
    zebrafish = extract_zb_table(args.zebrafish_docx, zebrafish_map)
    chicken_cores = load_cores(args.chicken_cores)
    zebrafish_cores = load_cores(args.zebrafish_cores)
    annotate_overlap(chicken, chicken_cores)
    annotate_overlap(zebrafish, zebrafish_cores)
    unresolved = [{
        "source": "PMC7597685",
        "family": "GGERV20",
        "reported_count": ">=65 full-length copies in GRCg6a",
        "coordinate_status": "not provided in accessible article/supplement",
        "primary_panel_status": "excluded until a coordinate-bearing source is found",
        "reason": "a population count without per-copy coordinates cannot be intersected with fixed cores without guessing",
        "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7597685/",
    }]
    write_outputs(args.out_dir, chicken + zebrafish, unresolved, chicken_cores, zebrafish_cores, args)
    print(json.dumps({"status": "ok", "output": str(args.out_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
