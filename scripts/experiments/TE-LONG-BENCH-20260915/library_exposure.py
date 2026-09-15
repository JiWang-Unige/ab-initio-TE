#!/usr/bin/env python3
"""Quantify simulated-family exposure to the fixed RepeatMasker library.

The mapping key is explicit: an input family name must exactly equal one Dfam
EMBL ``NM`` name, and the Dfam record's accession (ignoring only its terminal
version suffix) must occur in the actual ``fasta_acc`` FASTA header.  No fuzzy
name matching or broad-class fallback is used.  Generated truth intervals are
reported both as fragment rows/raw bp and as merged per-sequence union bp so
overlapping fragments are not added twice.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ACCESSION_RE = re.compile(r"^[A-Za-z]{2}\d+(?:\.\d+)?$")
VERSION_RE = re.compile(r"\.\d+$")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def open_text(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def accession_base(value: str) -> str:
    """Normalize only a terminal accession version for EMBL/FASTA linking."""

    token = str(value).strip().split(";", 1)[0].split()[0]
    return VERSION_RE.sub("", token).upper()


def parse_qualification(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    families = payload.get("families")
    if not isinstance(families, Mapping) or not families:
        raise ValueError("qualification file has no families mapping")
    return sorted(str(name) for name in families)


def parse_embl(path: Path) -> List[dict]:
    records: List[dict] = []
    current: Optional[dict] = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            current["names"] = sorted(set(current["names"]))
            current["accessions"] = sorted(set(current["accessions"]))
            records.append(current)
        current = None

    with open_text(path) as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if line == "//":
                flush()
                continue
            if line.startswith("ID   "):
                if current is not None:
                    flush()
                token = line[5:].strip().split(";", 1)[0].split()[0]
                current = {"id": token, "names": [], "accessions": []}
                continue
            if current is None:
                continue
            if line.startswith("NM   "):
                name = line[5:].strip()
                if name:
                    current["names"].append(name)
            elif line.startswith("AC   "):
                for token in line[5:].strip().split(";"):
                    token = token.strip().split()[0] if token.strip() else ""
                    if token and ACCESSION_RE.match(token):
                        current["accessions"].append(token)
    flush()
    if not records:
        raise ValueError("no EMBL records parsed from %s" % path)
    return records


def parse_library_fasta(path: Path) -> List[dict]:
    entries: List[dict] = []
    header: Optional[str] = None
    length = 0

    def flush() -> None:
        nonlocal header, length
        if header is None:
            return
        first = header.split()[0] if header.split() else ""
        raw_accession = first.split("#", 1)[0]
        class_token = first.split("#", 1)[1] if "#" in first else ""
        name_match = re.search(r"(?:^|\s)name=([^\s]+)", header)
        entries.append({
            "header": header,
            "accession_raw": raw_accession,
            "accession_base": accession_base(raw_accession),
            "name": name_match.group(1) if name_match else "",
            "class": class_token,
            "length_bp": int(length),
        })
        header = None
        length = 0

    with open_text(path) as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if line.startswith(">"):
                flush()
                header = line[1:].strip()
            elif header is not None:
                length += len(line.strip())
    flush()
    if not entries:
        raise ValueError("no FASTA entries parsed from %s" % path)
    return entries


def merge_union_bp(intervals: Iterable[Tuple[str, int, int]]) -> int:
    """Merge intervals independently by sequence ID before summing bp."""

    grouped: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for sequence_id, start, end in intervals:
        if end > start:
            grouped[str(sequence_id)].append((int(start), int(end)))
    total = 0
    for values in grouped.values():
        values.sort()
        current_start, current_end = values[0]
        for start, end in values[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                total += current_end - current_start
                current_start, current_end = start, end
        total += current_end - current_start
    return int(total)


def parse_truth(path: Path) -> Tuple[Dict[str, dict], dict]:
    by_family: Dict[str, dict] = defaultdict(lambda: {"fragment_rows": 0, "raw_fragment_bp": 0, "intervals": [], "status_counts": Counter(), "status_raw_bp": Counter(), "status_intervals": defaultdict(list)})
    row_count = 0
    status_counts: Counter = Counter()
    status_fragment_bp: Counter = Counter()
    with open_text(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"seqid", "start", "end", "family", "truth_status"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("truth table lacks required columns: %s" % sorted(required))
        for row in reader:
            family = str(row.get("family", ""))
            if not family:
                continue
            start, end = int(row["start"]), int(row["end"])
            if end < start:
                raise ValueError("truth interval has end < start")
            entry = by_family[family]
            entry["fragment_rows"] += 1
            entry["raw_fragment_bp"] += end - start
            entry["intervals"].append((str(row["seqid"]), start, end))
            truth_status = str(row.get("truth_status", ""))
            entry["status_counts"][truth_status] += 1
            entry["status_raw_bp"][truth_status] += end - start
            entry["status_intervals"][truth_status].append((str(row["seqid"]), start, end))
            status_counts[truth_status] += 1
            status_fragment_bp[truth_status] += end - start
            row_count += 1
    return dict(by_family), {
        "fragment_rows": row_count,
        "truth_status_counts": dict(sorted(status_counts.items())),
        "truth_status_fragment_bp": dict(sorted(status_fragment_bp.items())),
    }


def run(qualification_path: Path, embl_path: Path, library_path: Path, truth_path: Path, output_dir: Path) -> dict:
    qualification_families = parse_qualification(qualification_path)
    embl_records = parse_embl(embl_path)
    library_entries = parse_library_fasta(library_path)
    truth_by_family, truth_audit = parse_truth(truth_path)

    names_to_records: Dict[str, List[dict]] = defaultdict(list)
    for index, record in enumerate(embl_records):
        for name in record["names"]:
            names_to_records[name].append({"index": index, **record})
    library_by_accession: Dict[str, List[dict]] = defaultdict(list)
    for entry in library_entries:
        library_by_accession[entry["accession_base"]].append(entry)

    mapping_rows: List[dict] = []
    state_counts: Counter = Counter()
    matched_names: List[str] = []
    for family in qualification_families:
        exact_records = names_to_records.get(family, [])
        if not exact_records:
            state = "unmatched_no_exact_dfam_name"
            dfam_accessions: List[str] = []
            dfam_ids: List[str] = []
            rm_entries: List[dict] = []
        elif len(exact_records) > 1:
            state = "ambiguous_multiple_exact_dfam_records"
            dfam_accessions = sorted({token for record in exact_records for token in record["accessions"]})
            dfam_ids = sorted({str(record["id"]) for record in exact_records})
            rm_entries = [entry for accession in sorted({accession_base(token) for token in dfam_accessions}) for entry in library_by_accession.get(accession, [])]
        else:
            record = exact_records[0]
            dfam_accessions = sorted(set(record["accessions"]))
            dfam_ids = [str(record["id"])]
            accession_bases = {accession_base(token) for token in dfam_accessions}
            rm_entries = [entry for accession in sorted(accession_bases) for entry in library_by_accession.get(accession, [])]
            state = "matched" if rm_entries else "dfam_exact_but_rm_accession_missing"
        truth = truth_by_family.get(family, {"fragment_rows": 0, "raw_fragment_bp": 0, "intervals": [], "status_counts": {}, "status_raw_bp": {}, "status_intervals": {}})
        te_intervals = truth.get("status_intervals", {}).get("TE", [])
        if state == "matched":
            matched_names.append(family)
        state_counts[state] += 1
        mapping_rows.append({
            "family": family,
            "state": state,
            "dfam_exact_name_record_count": len(exact_records),
            "dfam_ids": dfam_ids,
            "dfam_accessions": dfam_accessions,
            "rm_entry_count_by_accession": len(rm_entries),
            "rm_accessions": sorted({entry["accession_raw"] for entry in rm_entries}),
            "rm_names_by_accession": sorted({entry["name"] for entry in rm_entries if entry["name"]}),
            "generated_fragment_rows": int(truth["fragment_rows"]),
            "generated_raw_fragment_bp": int(truth["raw_fragment_bp"]),
            "generated_union_bp": merge_union_bp(truth["intervals"]),
            "generated_te_fragment_rows": int(truth.get("status_counts", {}).get("TE", 0)),
            "generated_te_raw_fragment_bp": int(truth.get("status_raw_bp", {}).get("TE", 0)),
            "generated_te_union_bp": merge_union_bp(te_intervals),
        })

    dfam_accession_bases = {
        accession_base(token) for record in embl_records for token in record["accessions"]
    }
    write_json(output_dir / "library_exposure_summary.json", {
        "status": "PASS_NUMERIC_EXPOSURE_AUDIT",
        "qualification": {
            "path": str(qualification_path),
            "family_count": len(qualification_families),
            "families": qualification_families,
        },
        "dfam_embl": {
            "path": str(embl_path),
            "record_count": len(embl_records),
            "exact_name_match_count": sum(1 for row in mapping_rows if row["dfam_exact_name_record_count"] == 1),
            "exact_name_unmatched_count": state_counts["unmatched_no_exact_dfam_name"],
            "exact_name_ambiguous_count": state_counts["ambiguous_multiple_exact_dfam_records"],
        },
        "fixed_rm_library": {
            "path": str(library_path),
            "entry_count": len(library_entries),
            "total_library_bp": int(sum(entry["length_bp"] for entry in library_entries)),
            "unique_accession_base_count": len(library_by_accession),
            "entry_count_with_dfam_accession": int(sum(1 for entry in library_entries if entry["accession_base"] in dfam_accession_bases)),
        },
        "truth": {"path": str(truth_path), **truth_audit, "family_count": len(truth_by_family)},
        "mapping": {
            "state_counts": dict(sorted(state_counts.items())),
            "matched_family_count": len(matched_names),
            "unmatched_family_count": int(state_counts["unmatched_no_exact_dfam_name"]),
            "ambiguous_family_count": int(state_counts["ambiguous_multiple_exact_dfam_records"]),
            "dfam_exact_but_rm_missing_family_count": int(state_counts["dfam_exact_but_rm_accession_missing"]),
            "matched_rm_prototype_entry_count": int(sum(row["rm_entry_count_by_accession"] for row in mapping_rows if row["state"] == "matched")),
            "matched_rm_unique_accession_count": int(len({accession for row in mapping_rows if row["state"] == "matched" for accession in row["rm_accessions"]})),
            "matched_rm_header_name_exact_count": int(sum(1 for row in mapping_rows if row["state"] == "matched" and row["rm_names_by_accession"] == [row["family"]])),
            "matched_generated_fragment_rows": int(sum(row["generated_fragment_rows"] for row in mapping_rows if row["state"] == "matched")),
            "matched_generated_raw_fragment_bp": int(sum(row["generated_raw_fragment_bp"] for row in mapping_rows if row["state"] == "matched")),
            "matched_generated_union_bp": merge_union_bp(
                interval for family in matched_names for interval in truth_by_family.get(family, {}).get("intervals", [])
            ),
            "matched_generated_te_fragment_rows": int(sum(row["generated_te_fragment_rows"] for row in mapping_rows if row["state"] == "matched")),
            "matched_generated_te_raw_fragment_bp": int(sum(row["generated_te_raw_fragment_bp"] for row in mapping_rows if row["state"] == "matched")),
            "matched_generated_te_union_bp": merge_union_bp(
                interval for family in matched_names for interval in truth_by_family.get(family, {}).get("status_intervals", {}).get("TE", [])
            ),
            "mapping_key": "exact qualification family == EMBL NM name, then EMBL AC/ID accession base == fasta_acc base",
            "version_rule": "ignore only terminal accession version suffix (e.g. DF000000001.4 -> DF000000001)",
            "fuzzy_name_matching": False,
            "broad_class_fallback": False,
            "union_bp_merges_overlapping_intervals_per_seqid": True,
        },
    })
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "family_mapping.tsv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(mapping_rows[0].keys()) if mapping_rows else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        list_fields = {"dfam_ids", "dfam_accessions", "rm_accessions", "rm_names_by_accession"}
        writer.writerows({key: json.dumps(value, sort_keys=True) if key in list_fields else value for key, value in row.items()} for row in mapping_rows)
    return {"state_counts": dict(state_counts), "matched_family_count": len(matched_names)}


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--embl", required=True, type=Path)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--truth", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


if __name__ == "__main__":
    args = make_parser().parse_args()
    run(args.qualification, args.embl, args.library, args.truth, args.output_dir)
