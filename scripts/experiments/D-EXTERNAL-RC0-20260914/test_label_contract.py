#!/usr/bin/env python3
"""Minimal regression for the fixed-D Label-A and callable contracts.

This is the same four-row fixture used during the label-contract rescore
repair.  It intentionally checks only class routing, overlap clipping, and the
callable denominator; it is not a model or biological accuracy test.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import rc0  # noqa: E402


def _run() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="d-label-contract-") as root:
        root_path = Path(root)
        label_out = root_path / "fixture.out"
        # Minimal RepeatMasker .out columns consumed by
        # adapter.parse_repeatmasker_out: score div del ins seqid begin end
        # left strand name class.
        label_out.write_text(
            "\n".join(
                (
                    "   1  0.0  0.0  0.0 chr1 1 20 (0) + LINE1 LINE/L1",
                    "   2  0.0  0.0  0.0 chr1 15 35 (0) + simple1 Simple_repeat",
                    "   3  0.0  0.0  0.0 chr1 30 45 (0) + unknown1 Unknown",
                    "   4  0.0  0.0  0.0 chr1 70 75 (0) + artefact1 ARTEFACT",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        regions = [
            {
                "id": "fixture__r01__chr1__0_100",
                "source_seqid": "chr1",
                "source_length_bp": 100,
                "start_bp": 0,
                "end_bp": 100,
                "length_bp": 100,
            }
        ]
        sequences = {regions[0]["id"]: "A" * 9 + "N" + "C" * 90}
        _, truth_canonical, audit = rc0._make_truth(label_out, regions, root_path)
        buckets = audit["panel_buckets"]
        assert audit["raw_repeatmasker_rows_seen"] == 4
        assert audit["panel_rows_retained_all_buckets"] == 4
        assert buckets["known_te"]["rows"] == 1
        assert buckets["hard_non_te"]["rows"] == 1
        assert buckets["unknown_or_ambiguous"]["rows"] == 1
        assert buckets["excluded_non_te"]["rows"] == 1
        assert buckets["known_te"]["union_bp"] == 20

        callable_truth = rc0._clip_canonical_to_callable(
            truth_canonical, regions, sequences, root_path, "truth_repeatmasker_panel"
        )
        assert rc0.adapter.read_canonical(truth_canonical) == [
            (regions[0]["id"], 0, 20)
        ]
        assert rc0.adapter.read_canonical(callable_truth) == [
            (regions[0]["id"], 0, 9),
            (regions[0]["id"], 10, 20),
        ]

        pred_bed = root_path / "pred.bed"
        pred_bed.write_text(f"{regions[0]['id']}\t0\t20\tpred\n", encoding="utf-8")
        pred_canonical = root_path / "pred.tsv"
        rc0.adapter.convert(pred_bed, pred_canonical, "bed")
        callable_pred = rc0._clip_canonical_to_callable(
            pred_canonical, regions, sequences, root_path, "pred"
        )
        raw_t0 = rc0.adapter.evaluate(
            callable_truth,
            callable_pred,
            {regions[0]["id"]: 100},
            truth_tier="T0",
        )
        corrected_t0 = rc0._correct_callable_metrics(raw_t0, 99, "T0")
        assert raw_t0["bp_n"] == 100
        assert corrected_t0["bp_n"] == 99
        assert corrected_t0["bp_tp"] == 19
        assert corrected_t0["bp_fp"] == 0
        assert corrected_t0["bp_fn"] == 0
        assert corrected_t0["bp_tn"] == 80

        raw_t1 = rc0.adapter.evaluate(
            callable_truth,
            callable_pred,
            {regions[0]["id"]: 100},
            truth_tier="T1",
        )
        corrected_t1 = rc0._correct_callable_metrics(raw_t1, 99, "T1")
        assert corrected_t1["bp_n"] == 99
        assert corrected_t1["bp_tp"] == 19
        assert corrected_t1["bp_fp"] is None
        assert corrected_t1["bp_tn"] is None
        return {
            "status": "PASS",
            "raw_rows": 4,
            "bucket_rows": {name: int(value["rows"]) for name, value in buckets.items()},
            "known_union_bp": int(buckets["known_te"]["union_bp"]),
            "callable_bp": 99,
            "callable_t0_bp_n": int(corrected_t0["bp_n"]),
            "callable_t0_bp_tn": int(corrected_t0["bp_tn"]),
        }


if __name__ == "__main__":
    print(json.dumps(_run(), sort_keys=True))
