#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


BASE_SEGMENT_F1 = 0.3399561524
BASE_BOUNDARY_F1 = 0.1997807619
MAX_SHORT_RATE = 0.497931
MAX_FRAGMENTS_PER_TRUTH = 1.180148
MIN_BP_F1 = 0.929173
MAX_MISSED_RATE = 0.087532


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    metrics = json.loads(args.metrics.read_text())
    row = next(row for row in metrics["rows"] if row["boundary_tol_bp"] == 5)
    short_rate = row["short_pred_segments"] / row["pred_segments"]
    gates = {
        "segment_f1_above_base": row["segment_f1"] > BASE_SEGMENT_F1,
        "boundary_f1_at_5_above_base": row["boundary_f1"] > BASE_BOUNDARY_F1,
        "short_prediction_rate_at_most_0.497931": short_rate <= MAX_SHORT_RATE,
        "fragments_per_truth_at_most_1.180148": row["mean_fragments_per_true"] <= MAX_FRAGMENTS_PER_TRUTH,
        "bp_f1_at_least_0.929173": row["bp_f1"] >= MIN_BP_F1,
        "missed_rate_at_most_0.087532": row["missed_true_rate"] <= MAX_MISSED_RATE,
    }
    result = {
        "source_metrics": str(args.metrics),
        "claim_scope": metrics["claim_scope"],
        "metrics": {
            "segment_f1": row["segment_f1"],
            "boundary_f1_at_5": row["boundary_f1"],
            "short_prediction_rate": short_rate,
            "fragments_per_truth": row["mean_fragments_per_true"],
            "bp_f1": row["bp_f1"],
            "missed_rate": row["missed_true_rate"],
        },
        "gates": gates,
        "passed": all(gates.values()),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
