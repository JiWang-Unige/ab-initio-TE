#!/usr/bin/env python3
"""Exercise the Gate-L machine chain on the smallest eligible synthetic panel.

This is an engineering integration test.  It deliberately keeps the frozen
120-package L-R denominator, while giving every package one simple locus so
that the chain can be checked without claiming a biological Gate-L result.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
VALIDATOR = HERE / "validate_gate_l_pass1.py"
PROJECTOR = HERE / "project_gate_l_atoms.py"
LR_EVALUATOR = HERE / "evaluate_gate_l_reproducibility.py"
LP_LD_EVALUATOR = HERE / "evaluate_gate_l_lp_ld.py"


PACKET_FIELDS = [
    "packet_id",
    "package_id",
    "role",
    "role_rank",
    "unit_type",
    "hard_cell",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
    "feature_ids",
]

RESPONSE_FIELDS = {
    "package_reviews.tsv": [
        "package_id",
        "actor_id",
        "package_status",
        "topology_resolution",
        "topology_reason",
    ],
    "loci.tsv": [
        "package_id",
        "actor_id",
        "locus_id",
        "locus_status",
        "locus_envelope_start",
        "locus_envelope_end",
    ],
    "material_segments.tsv": [
        "package_id",
        "actor_id",
        "segment_id",
        "locus_id",
        "seqid",
        "start",
        "end",
        "evidence_codes",
        "locus_assignment_status",
    ],
    "boundaries.tsv": [
        "package_id",
        "actor_id",
        "locus_id",
        "side",
        "identifiability",
        "lower_pos",
        "upper_pos",
        "evidence_codes",
    ],
    "interruptions.tsv": [
        "package_id",
        "actor_id",
        "interruption_id",
        "locus_id",
        "child_locus_id",
        "seqid",
        "start",
        "end",
        "interruption_type",
        "evidence_codes",
    ],
    "relations.tsv": [
        "package_id",
        "actor_id",
        "relation_id",
        "relation_type",
        "subject_locus_id",
        "object_locus_id",
        "evidence_codes",
    ],
}

PACKAGE_FIELDS = [
    "package_id",
    "role",
    "reserve_pair_rank",
    "unit_type",
    "hard_cell",
    "assembly_id",
    "seqid",
    "feature_ids",
    "deep_audit_feature_id",
]

CONTEXT_FIELDS = ["package_id", "feature_id", "seqid", "start0", "end0"]

PROVENANCE_FIELDS = [
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
    "evidence_codes",
    "deep_audit",
    "anchor_interpretability",
    "audit_note",
]

ATOM_FIELDS = [
    "package_id",
    "atom_id",
    "seqid",
    "start0",
    "end0",
    "package_censored",
]


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main_packages() -> list[dict[str, str]]:
    cells = (
        ["S0-L1"] * 15
        + ["S0-L2"] * 15
        + ["S0-L3"] * 15
        + ["S0-L4"] * 15
        + ["S1-C1"] * 20
        + ["S1-C2"] * 20
        + ["S1-C3"] * 20
    )
    rows: list[dict[str, str]] = []
    for index, cell in enumerate(cells):
        package_id = f"M{index + 1:03d}"
        feature_id = f"FBti-{package_id}"
        rows.append(
            {
                "package_id": package_id,
                "role": "main",
                "reserve_pair_rank": "",
                "unit_type": "S0" if index < 60 else "S1",
                "assembly_id": "synthetic-asm",
                "seqid": "chrSynthetic",
                "feature_ids": feature_id,
                "deep_audit_feature_id": feature_id if index < 40 else "",
                "hard_cell": cell,
                "start": str(1000 + index * 50),
                "end": str(1020 + index * 50),
            }
        )
    return rows


def all_package_rows() -> list[dict[str, str]]:
    rows = main_packages()
    rows_without_internal = [
        {key: row[key] for key in PACKAGE_FIELDS} for row in rows
    ]
    for rank in range(1, 21):
        for unit_type in ("S0", "S1"):
            package_id = f"R{rank:02d}-{unit_type}"
            rows_without_internal.append(
                {
                    "package_id": package_id,
                    "role": "reserve",
                    "reserve_pair_rank": str(rank),
                    "unit_type": unit_type,
                    "assembly_id": "synthetic-asm",
                    "seqid": "chrSynthetic",
                    "feature_ids": f"FBti-{package_id}",
                    "deep_audit_feature_id": "",
                }
            )
    return rows_without_internal


def packet_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, package in enumerate(main_packages()):
        package_start = int(package["start"])
        package_end = int(package["end"])
        rows.append(
            {
                "packet_id": f"PACKET-{package['package_id']}",
                "package_id": package["package_id"],
                "role": "main",
                "role_rank": str(index + 1),
                "unit_type": package["unit_type"],
                "hard_cell": package["hard_cell"],
                "assembly_id": package["assembly_id"],
                "seqid": package["seqid"],
                "core_start0": str(package_start + 2),
                "core_end0": str(package_end - 2),
                "package_start0": str(package_start),
                "package_end0": str(package_end),
                "feature_ids": package["feature_ids"],
            }
        )
    return rows


def response_rows(actor: str) -> dict[str, list[dict[str, str]]]:
    rows = {filename: [] for filename in RESPONSE_FIELDS}
    for package in main_packages():
        package_id = package["package_id"]
        raw_id = f"PACKET-{package_id}"
        start = int(package["start"]) + 4
        end = int(package["end"]) - 4
        locus_id = "L1"
        rows["package_reviews.tsv"].append(
            {
                "package_id": raw_id,
                "actor_id": actor,
                "package_status": "resolved",
                "topology_resolution": ""
                if actor in {"A1", "A2"}
                else "same_topology_minor_edit",
                "topology_reason": "",
            }
        )
        rows["loci.tsv"].append(
            {
                "package_id": raw_id,
                "actor_id": actor,
                "locus_id": locus_id,
                "locus_status": "resolved",
                "locus_envelope_start": str(start),
                "locus_envelope_end": str(end),
            }
        )
        rows["material_segments.tsv"].append(
            {
                "package_id": raw_id,
                "actor_id": actor,
                "segment_id": "SEG1",
                "locus_id": locus_id,
                "seqid": package["seqid"],
                "start": str(start),
                "end": str(end),
                "evidence_codes": "SYNTHETIC_INDEPENDENT",
                "locus_assignment_status": "assigned",
            }
        )
        rows["boundaries.tsv"].extend(
            {
                "package_id": raw_id,
                "actor_id": actor,
                "locus_id": locus_id,
                "side": side,
                "identifiability": "point",
                "lower_pos": str(position),
                "upper_pos": str(position),
                "evidence_codes": "SYNTHETIC_INDEPENDENT",
            }
            for side, position in (("left", start), ("right", end))
        )
    return rows


class GateLEndToEndTest(unittest.TestCase):
    def test_synthetic_chain_reaches_frozen_denominator_status(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            packet_manifest = root / "packet_manifest.tsv"
            evidence_registry = root / "evidence_registry.tsv"
            write_tsv(packet_manifest, PACKET_FIELDS, packet_rows())
            write_tsv(
                evidence_registry,
                [
                    "evidence_code",
                    "evidence_class",
                    "source_version",
                    "independent_of_fbti_endpoint",
                    "used_by_gate_e",
                ],
                [
                    {
                        "evidence_code": "SYNTHETIC_INDEPENDENT",
                        "evidence_class": "synthetic",
                        "source_version": "v1",
                        "independent_of_fbti_endpoint": "1",
                        "used_by_gate_e": "0",
                    }
                ],
            )
            for actor in ("A1", "A2", "ADJ"):
                input_dir = root / f"raw-{actor}"
                response = response_rows(actor)
                for filename, fields in RESPONSE_FIELDS.items():
                    write_tsv(input_dir / filename, fields, response[filename])

            normalized = {}
            for actor in ("A1", "A2", "ADJ"):
                output_dir = root / f"normalized-{actor}"
                self._run(
                    [
                        sys.executable,
                        str(VALIDATOR),
                        "--packet-manifest",
                        str(packet_manifest),
                        "--evidence-registry",
                        str(evidence_registry),
                        "--input-dir",
                        str(root / f"raw-{actor}"),
                        "--actor",
                        actor,
                        "--output-dir",
                        str(output_dir),
                    ]
                )
                normalized[actor] = output_dir

            atoms = []
            for package in main_packages():
                start = int(package["start"]) + 4
                end = int(package["end"]) - 4
                atoms.append(
                    {
                        "package_id": package["package_id"],
                        "atom_id": f"P3:{package['seqid']}:{start}:{end}",
                        "seqid": package["seqid"],
                        "start0": str(start),
                        "end0": str(end),
                        "package_censored": "0",
                    }
                )
            atom_path = root / "package_atoms.tsv"
            write_tsv(atom_path, ATOM_FIELDS, atoms)
            projection_path = root / "atom_projection.tsv"
            self._run(
                [
                    sys.executable,
                    str(PROJECTOR),
                    "--material-segments",
                    str(normalized["ADJ"] / "material_segments.tsv"),
                    "--package-atoms",
                    str(atom_path),
                    "--output",
                    str(projection_path),
                ]
            )

            packages_path = root / "packages.tsv"
            package_rows = all_package_rows()
            write_tsv(packages_path, PACKAGE_FIELDS, package_rows)
            context_rows = []
            provenance_rows = []
            for package in main_packages():
                package_id = package["package_id"]
                feature_id = package["feature_ids"]
                start = int(package["start"]) + 4
                end = int(package["end"]) - 4
                context_rows.append(
                    {
                        "package_id": package_id,
                        "feature_id": feature_id,
                        "seqid": package["seqid"],
                        "start0": str(start),
                        "end0": str(end),
                    }
                )
                deep = bool(package["deep_audit_feature_id"])
                provenance_rows.append(
                    {
                        "package_id": package_id,
                        "feature_id": feature_id,
                        "manifest_assembly_id": package["assembly_id"],
                        "source_assembly_id": package["assembly_id"],
                        "manifest_seqid": package["seqid"],
                        "source_seqid": package["seqid"],
                        "manifest_start": str(start),
                        "manifest_end": str(end),
                        "source_start": str(start),
                        "source_end": str(end),
                        "source_feature_id": feature_id,
                        "evidence_packet_id": f"PROVENANCE-{package_id}",
                        "evidence_codes": "SYNTHETIC_INDEPENDENT",
                        "deep_audit": "1" if deep else "0",
                        "anchor_interpretability": "interpretable_extant_locus"
                        if deep
                        else "",
                        "audit_note": "",
                    }
                )
            context_path = root / "context.tsv"
            provenance_path = root / "provenance.tsv"
            write_tsv(context_path, CONTEXT_FIELDS, context_rows)
            write_tsv(provenance_path, PROVENANCE_FIELDS, provenance_rows)

            lr_path = root / "lr.json"
            self._run(
                [
                    sys.executable,
                    str(LR_EVALUATOR),
                    "--packages",
                    str(packages_path),
                    "--a1",
                    str(normalized["A1"]),
                    "--a2",
                    str(normalized["A2"]),
                    "--adj",
                    str(normalized["ADJ"]),
                    "--output",
                    str(lr_path),
                ]
            )
            lr = json.loads(lr_path.read_text(encoding="utf-8"))
            self.assertEqual(lr["status"], "PASS")
            self.assertEqual(lr["panel"]["main_packages"], 120)

            final_dir = root / "gate-l-final"
            self._run(
                [
                    sys.executable,
                    str(LP_LD_EVALUATOR),
                    "--packages",
                    str(packages_path),
                    "--context",
                    str(context_path),
                    "--evidence-registry",
                    str(evidence_registry),
                    "--provenance-audit",
                    str(provenance_path),
                    "--adj-bundle",
                    str(normalized["ADJ"]),
                    "--atom-projection",
                    str(projection_path),
                    "--lr-metrics",
                    str(lr_path),
                    "--output-dir",
                    str(final_dir),
                ]
            )
            final = json.loads(
                (final_dir / "gate_l_lp_ld.json").read_text(encoding="utf-8")
            )
            self.assertEqual(final["active_main_packages"], 120)
            self.assertEqual(final["active_reserve_pairs"], 0)
            self.assertEqual(final["ld"]["status"], "SHORT")
            self.assertEqual(final["status"], "INCOMPLETE")

    def _run(self, command: list[str]) -> None:
        result = subprocess.run(
            command,
            cwd=REPO,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            self.fail(
                "command failed ({}):\n{}\n{}".format(
                    result.returncode, result.stdout, result.stderr
                )
            )


if __name__ == "__main__":
    unittest.main()
