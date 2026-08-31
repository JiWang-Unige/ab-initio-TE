#!/usr/bin/env python3
"""Build the frozen Gate-L provenance audit table for one packet role."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


OUTPUT_FIELDS = [
    "package_id",
    "feature_id",
    "manifest_assembly_id",
    "source_assembly_id",
    "manifest_seqid",
    "source_seqid",
    "manifest_start",
    "manifest_end",
    "source_start",
    "source_end",
    "source_feature_id",
    "evidence_packet_id",
    "deep_audit",
    "anchor_interpretability",
    "audit_note",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing TSV header: {path}")
        return list(reader)


def _gff_id(attributes: str) -> str | None:
    for item in attributes.split(";"):
        if item.startswith("ID="):
            return item[3:]
    return None


def read_raw_features(path: Path) -> dict[str, tuple[str, int, int]]:
    features: dict[str, tuple[str, int, int]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"invalid packet GFF3 row: {path}")
            feature_id = _gff_id(fields[8])
            if feature_id:
                features[feature_id] = (fields[0], int(fields[3]) - 1, int(fields[4]))
    return features


def build_provenance_audit(
    packages_path: Path,
    packet_manifest_path: Path,
    packet_bundle: Path,
    source_assembly_id: str,
    output_path: Path,
) -> None:
    packages = {row["package_id"]: row for row in read_tsv(packages_path)}
    packet_rows = read_tsv(packet_manifest_path)
    output: list[dict[str, str]] = []

    for packet in packet_rows:
        package_id = packet["package_id"]
        package = packages[package_id]
        packet_id = packet["packet_id"]
        packet_dir = packet_bundle / "packets" / packet_id
        context = {
            row["feature_id"]: row
            for row in read_tsv(packet_dir / "context_features.tsv")
        }
        raw = read_raw_features(packet_dir / "raw_flybase_features.gff3")
        deep_feature = package["deep_audit_feature_id"]
        for feature_id in package["feature_ids"].split(","):
            record = context[feature_id]
            source_seqid, source_start, source_end = raw[feature_id]
            output.append(
                {
                    "package_id": package_id,
                    "feature_id": feature_id,
                    "manifest_assembly_id": package["assembly_id"],
                    "source_assembly_id": source_assembly_id,
                    "manifest_seqid": record["seqid"],
                    "source_seqid": source_seqid,
                    "manifest_start": record["start0"],
                    "manifest_end": record["end0"],
                    "source_start": str(source_start),
                    "source_end": str(source_end),
                    "source_feature_id": feature_id,
                    "evidence_packet_id": packet_id,
                    "deep_audit": "1" if feature_id == deep_feature else "0",
                    "anchor_interpretability": "",
                    "audit_note": "",
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=OUTPUT_FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--packet-manifest", type=Path, required=True)
    parser.add_argument("--packet-bundle", type=Path, required=True)
    parser.add_argument("--source-assembly-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_provenance_audit(
        args.packages,
        args.packet_manifest,
        args.packet_bundle,
        args.source_assembly_id,
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
