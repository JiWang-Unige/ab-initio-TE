#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import csv
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "stage0_oracle", Path(__file__).with_name("stage0_oracle.py"),
)
assert SPEC is not None and SPEC.loader is not None
oracle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = oracle
SPEC.loader.exec_module(oracle)


class Stage0OracleTest(unittest.TestCase):
    def test_chr13_split_is_frozen_40_30_30(self) -> None:
        roles, manifest = oracle.chr13_split(21 * oracle.SUPERBLOCK_BP + 17)
        self.assertEqual(len(manifest), 22)
        self.assertEqual([roles[index] for index in range(22)].count("DEV"), 9)
        self.assertEqual([roles[index] for index in range(22)].count("CAL_FIT"), 7)
        self.assertEqual([roles[index] for index in range(22)].count("CAL_GATE"), 6)
        self.assertEqual(roles, oracle.chr13_split(21 * oracle.SUPERBLOCK_BP + 17)[0])

    def test_short_union_uses_complete_gap_length(self) -> None:
        union = oracle.ShortUnion([(0, 20), (22, 42), (100, 200)])
        candidate = oracle.Candidate(
            oracle.BaseCandidate("chr3:20-22", "chr3", 0, 20, 20, 22, 22, 42),
            oracle.BRIDGE, 2, 0, 0,
        )
        union.add_gap(candidate)
        self.assertEqual(union.components, 2)
        self.assertEqual(union.short, 1)
        self.assertEqual(union.lengths[union.find(0)], 42)

    def test_interval_subtraction_advances_across_sources(self) -> None:
        self.assertEqual(
            oracle.subtract_intervals([(0, 10), (20, 30), (40, 50)], [(5, 25), (45, 60)]),
            [(0, 5), (25, 30), (40, 45)],
        )

    def test_non_gene_gate_rejects_precision_loss(self) -> None:
        raw_whole = {"precision": 0.9, "recall": 0.8, "f1": 0.847}
        refined_whole = {"precision": 0.898, "recall": 0.81, "f1": 0.852}
        raw_fragment = {"split_rate": 0.5, "fragments_per_truth": 2.0}
        refined_fragment = {"split_rate": 0.4, "fragments_per_truth": 1.7}
        gates = oracle.non_gene_gate(
            raw_whole, refined_whole, raw_fragment, refined_fragment,
            0.5, 0.4, 1000, 10_000, 1000, 0, 5000, 500, 1000, 100_000_000,
        )
        self.assertFalse(gates["whole_mask_precision_drop"])
        self.assertTrue(gates["split_rate_relative_decrease"])

    def test_mixed_gap_can_add_a_fragment_for_a_missed_truth_run(self) -> None:
        raw, _ = oracle.fragment_counts([(0, 10), (30, 40)], [(12, 18)])
        refined, _ = oracle.fragment_counts([(0, 40)], [(12, 18)])
        self.assertEqual(raw["fragments"], 0)
        self.assertEqual(raw["missed_truth_runs"], 1)
        self.assertEqual(refined["fragments"], 1)
        self.assertEqual(refined["missed_truth_runs"], 0)

    def test_distinct_comparator_run_fusion_counts_mixed_gap(self) -> None:
        candidate = oracle.Candidate(
            oracle.BaseCandidate("chr3:10-20", "chr3", 0, 10, 10, 20, 20, 30),
            "AMBIGUOUS", 4, 6, 0,
        )
        chromosome = oracle.ChromData(
            "chr3", 100, [(0, 100)], [(0, 100)], [(0, 100)],
            [(0, 14), (16, 30)], [], [(0, 10), (20, 30)], [candidate],
        )
        diagnostics = oracle.selection_diagnostics([chromosome], {candidate.base.candidate_id})
        self.assertEqual(diagnostics["selected_distinct_comparator_run_fusions"], 1)
        self.assertEqual(diagnostics["selected_comparator_separation_supported_candidates"], 0)

    def test_candidate_label_census_reports_unknown_eligibility(self) -> None:
        known = oracle.Candidate(
            oracle.BaseCandidate("chr3:10-11", "chr3", 0, 10, 10, 11, 11, 20),
            oracle.BRIDGE, 1, 0, 0,
        )
        unknown = oracle.Candidate(
            oracle.BaseCandidate("chr3:30-32", "chr3", 20, 30, 30, 32, 32, 40),
            "UNKNOWN", 0, 0, 2,
        )
        chromosome = oracle.ChromData(
            "chr3", 100, [(0, 100)], [(0, 100)], [(0, 100)],
            [], [], [], [known, unknown],
        )
        census = oracle.candidate_label_census([chromosome])
        self.assertEqual(census["model_eligible_candidates"], 2)
        self.assertEqual(census["comparator_known_gap_bp"], 1)
        self.assertEqual(census["comparator_unknown_candidate_gap_bp"], 2)
        self.assertEqual(census["effective_comparator_unknown_bp"], 2)

    def test_small_pipeline_keeps_chr19_out_of_the_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            for seqid in oracle.CHROMOSOMES:
                chromosome = source / seqid
                chromosome.mkdir(parents=True)
                with gzip.open(chromosome / "region.jsonl.gz", "wt", encoding="utf-8") as handle:
                    handle.write(json.dumps({
                        "chr": seqid, "start": 0, "end": 1024,
                        "sequence": "A" * 1024, "labels": [0] * 1024,
                    }) + "\n")
                candidate = {
                    "candidate_id": f"{seqid}:300-301", "seqid": seqid,
                    "left_run_start": 100, "left_run_end": 300,
                    "gap_start": 300, "gap_end": 301,
                    "right_run_start": 301, "right_run_end": 500,
                }
                with (chromosome / "candidates.tsv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(candidate), delimiter="\t")
                    writer.writeheader()
                    writer.writerow(candidate)
                labeled = {
                    **candidate, "comparator_relation": oracle.BRIDGE,
                    "gap_comparator_positive_bp": 1,
                    "gap_comparator_negative_bp": 0,
                    "gap_comparator_unknown_bp": 0,
                }
                with (chromosome / "labeled.tsv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(labeled), delimiter="\t")
                    writer.writeheader()
                    writer.writerow(labeled)
                (chromosome / "prediction.canonical.tsv").write_text(
                    f"seqid\tstart\tend\n{seqid}\t100\t300\n{seqid}\t301\t500\n",
                    encoding="utf-8",
                )
            positive = root / "positive.bed"
            plus_unknown = root / "plus_unknown.bed"
            bed = "".join(f"{seqid}\t100\t500\n" for seqid in oracle.CHROMOSOMES)
            positive.write_text(bed, encoding="utf-8")
            plus_unknown.write_text(bed, encoding="utf-8")
            refgene = root / "refgene.tsv"
            refgene.write_text("".join(
                f"NM_{seqid}\t{seqid}\t+\t50\t600\t100\t500\t1\t50,\t600,\t0\tGENE_{seqid}\tcmpl\tcmpl\t0,\n"
                for seqid in oracle.CHROMOSOMES
            ), encoding="utf-8")
            output = root / "result"
            result = oracle.run_oracle(source, positive, plus_unknown, refgene, output)
            self.assertEqual(result["status"], "WHOLE_GAP_ORACLE_NO_GO")
            self.assertEqual(result["chromosome_roles"]["sealed_test_labels_not_retained_or_used"], "chr19")
            self.assertEqual(result["zero_risk_topology"]["train"]["strict_bridge"]["candidate_count"], 2)
            self.assertTrue((output / "STATUS").is_file())


if __name__ == "__main__":
    unittest.main()
