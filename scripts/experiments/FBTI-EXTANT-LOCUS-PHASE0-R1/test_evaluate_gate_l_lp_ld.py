#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "evaluate_gate_l_lp_ld", HERE / "evaluate_gate_l_lp_ld.py"
)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def package_manifest() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in range(120):
        package_id = f"M{index + 1:03d}"
        feature_id = f"FBtiM{index + 1:03d}"
        rows.append(
            {
                "package_id": package_id,
                "role": "main",
                "reserve_pair_rank": "",
                "unit_type": "S0" if index < 60 else "S1",
                "assembly_id": "dmel_r6.68",
                "seqid": "2L",
                "feature_ids": feature_id,
                "deep_audit_feature_id": feature_id if index < 40 else "",
            }
        )
    for rank in range(1, 21):
        for unit_type in ("S0", "S1"):
            package_id = f"R{rank:02d}-{unit_type}"
            rows.append(
                {
                    "package_id": package_id,
                    "role": "reserve",
                    "reserve_pair_rank": str(rank),
                    "unit_type": unit_type,
                    "assembly_id": "dmel_r6.68",
                    "seqid": "2L",
                    "feature_ids": f"FBti{package_id}",
                    "deep_audit_feature_id": "",
                }
            )
    return rows


def active_inputs(reserve_ranks: tuple[int, ...] = ()) -> dict[str, object]:
    packages = package_manifest()
    active = [row for row in packages if row["role"] == "main"]
    active.extend(
        row for row in packages
        if row["role"] == "reserve" and int(row["reserve_pair_rank"]) in reserve_ranks
    )
    context: list[dict[str, str]] = []
    provenance: list[dict[str, str]] = []
    reviews: list[dict[str, str]] = []
    for index, row in enumerate(active):
        feature_id = row["feature_ids"]
        start = 1000 + index * 20
        end = start + 10
        context.append(
            {
                "package_id": row["package_id"],
                "feature_id": feature_id,
                "seqid": "2L",
                "start0": str(start),
                "end0": str(end),
            }
        )
        deep = row["deep_audit_feature_id"] == feature_id
        provenance.append(
            {
                "package_id": row["package_id"],
                "feature_id": feature_id,
                "manifest_assembly_id": "dmel_r6.68",
                "source_assembly_id": "dmel_r6.68",
                "manifest_seqid": "2L",
                "source_seqid": "2L",
                "manifest_start": str(start),
                "manifest_end": str(end),
                "source_start": str(start),
                "source_end": str(end),
                "source_feature_id": feature_id,
                "evidence_packet_id": f"PACKET-{row['package_id']}",
                "deep_audit": "1" if deep else "0",
                "anchor_interpretability": "interpretable_extant_locus" if deep else "",
                "audit_note": "",
            }
        )
        reviews.append(
            {
                "package_id": row["package_id"],
                "actor_id": "ADJ",
                "package_status": "unresolved",
            }
        )
    return {
        "package_rows": packages,
        "context_rows": context,
        "registry_rows": [
            {
                "evidence_code": "FLYBASE_FEATURE_RECORD",
                "independent_of_fbti_endpoint": "0",
            },
            {
                "evidence_code": "SEQUENCE_TSD_COMPATIBILITY",
                "independent_of_fbti_endpoint": "1",
            },
        ],
        "provenance_rows": provenance,
        "reviews": reviews,
        "loci": [],
        "materials": [],
        "boundaries": [],
        "relations": [],
        "projections": [],
        "lr_metrics": {
            "status": "PASS",
            "boundary_status": "EVALUATED",
            "metrics": {
                "boundary_identifiability_gwet_ac1": {
                    "agreement_count": 40,
                    "denominator": 40,
                    "threshold": 0.60,
                },
            },
        },
    }


class GateLLpLdTest(unittest.TestCase):
    def test_lr_failure_precedes_ld_shortfall(self) -> None:
        inputs = active_inputs()
        inputs["lr_metrics"] = {
            "status": "NO_GO_LR",
            "boundary_status": "EVALUATED",
            "metrics": {
                "boundary_identifiability_gwet_ac1": {
                    "agreement_count": 20, "denominator": 40, "threshold": 0.60,
                }
            },
        }
        result = gate.evaluate_gate_l(**inputs)
        self.assertEqual(result["ld"]["status"], "SHORT")
        self.assertEqual(result["status"], "NO_GO_LR")
        self.assertNotIn("next_reserve_pair", result)

    def test_rejects_noncontiguous_reserve_activation(self) -> None:
        inputs = active_inputs((1, 3))
        with self.assertRaisesRegex(gate.ContractError, "contiguous prefix"):
            gate.evaluate_gate_l(**inputs)

    def test_nested_relation_requires_eligible_unique_atom_on_both_loci(self) -> None:
        loci = [
            {
                "package_id": "M001", "actor_id": "ADJ", "locus_id": "child",
                "locus_status": "resolved",
            },
            {
                "package_id": "M001", "actor_id": "ADJ", "locus_id": "parent",
                "locus_status": "resolved",
            },
        ]
        relations = [
            {
                "package_id": "M001", "actor_id": "ADJ", "relation_id": "R1",
                "relation_type": "nested_in", "subject_locus_id": "child",
                "object_locus_id": "parent",
            }
        ]
        child = {
            "package_id": "M001", "atom_id": "A-child", "assignment": "unique",
            "assigned_locus_id": "child", "assigned_segment_ids": "M-child",
            "projection_eligibility": "eligible",
        }
        censored_parent = {
            "package_id": "M001", "atom_id": "A-parent", "assignment": "",
            "assigned_locus_id": "", "assigned_segment_ids": "",
            "projection_eligibility": "package_censored",
        }
        excluded = gate.evaluate_ld(
            {"M001"}, loci, [], relations, [child, censored_parent]
        )
        self.assertEqual(excluded["checks"]["nested_relations"]["numerator"], 0)

        eligible_parent = dict(
            censored_parent,
            projection_eligibility="eligible",
            assignment="unique",
            assigned_locus_id="parent",
            assigned_segment_ids="M-parent",
        )
        included = gate.evaluate_ld(
            {"M001"}, loci, [], relations, [child, eligible_parent]
        )
        self.assertEqual(included["checks"]["nested_relations"]["numerator"], 1)
        self.assertEqual(included["checks"]["nested_relation_packages"]["numerator"], 1)

    def test_rejects_nonblank_package_censored_projection(self) -> None:
        loci = [{
            "package_id": "M001", "actor_id": "ADJ", "locus_id": "L1",
            "locus_status": "resolved",
        }]
        projection = {
            "package_id": "M001", "atom_id": "A1", "assignment": "unique",
            "assigned_locus_id": "L1", "assigned_segment_ids": "M1",
            "projection_eligibility": "package_censored",
        }
        with self.assertRaisesRegex(gate.ContractError, "blank projection fields"):
            gate.evaluate_ld({"M001"}, loci, [], [], [projection])

    def test_unsupported_copied_point_requires_independent_evidence(self) -> None:
        inputs = active_inputs()
        first_context = inputs["context_rows"][0]
        copied = {
            "package_id": "M001",
            "actor_id": "ADJ",
            "locus_id": "L1",
            "side": "left",
            "identifiability": "point",
            "lower_pos": first_context["start0"],
            "upper_pos": first_context["start0"],
            "evidence_codes": "FLYBASE_FEATURE_RECORD",
        }
        packages = gate._index_packages(inputs["package_rows"])
        active = {row["package_id"] for row in inputs["reviews"]}
        context = gate._context_index(inputs["context_rows"])
        registry = gate._registry(inputs["registry_rows"])
        unsupported = gate.evaluate_lp(
            packages, active, context, registry, inputs["provenance_rows"], [copied]
        )
        metric = unsupported["checks"]["unsupported_copied_point_fraction"]
        self.assertEqual((metric["numerator"], metric["denominator"]), (1, 1))
        self.assertEqual(unsupported["status"], "NO_GO_LP")

        supported_row = dict(copied, evidence_codes="SEQUENCE_TSD_COMPATIBILITY")
        supported = gate.evaluate_lp(
            packages, active, context, registry, inputs["provenance_rows"], [supported_row]
        )
        metric = supported["checks"]["unsupported_copied_point_fraction"]
        self.assertEqual((metric["numerator"], metric["denominator"]), (0, 1))
        self.assertEqual(supported["status"], "PASS")

    def test_incomplete_emits_only_next_frozen_pair(self) -> None:
        result = gate.evaluate_gate_l(**active_inputs((1,)))
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["next_reserve_pair"]["reserve_pair_rank"], 2)
        self.assertEqual(result["next_reserve_pair"]["package_ids"], ["R02-S0", "R02-S1"])

        boundary = gate.evaluate_gate_l(**{
            **active_inputs((1,)),
            "lr_metrics": {
                "status": "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS",
                "boundary_status": "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS",
                "metrics": {
                    "boundary_identifiability_gwet_ac1": {
                        "agreement_count": 30, "denominator": 30, "threshold": 0.60,
                    }
                },
            },
        })
        self.assertEqual(boundary["status"], "LABEL_DENOMINATOR_INSUFFICIENT_BOUNDARY_STATUS")
        self.assertNotIn("next_reserve_pair", boundary)


if __name__ == "__main__":
    unittest.main()
