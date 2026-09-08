#!/usr/bin/env python3
"""Optimistic necessary-condition screen for a fixed DEV score ordering."""
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "outputs/GAP-A-B1-SCREEN-20260908-R1"
OUT = ROOT / "outputs/GAP-HN-RANK-FEASIBILITY-20260908-R1"
MANIFEST = ROOT / "outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv"
SPAN = 9 * 5242880
SEEDS = (17, 42, 20260902)


def prefixes(scores, positive, negative, unknown, length):
    order = np.argsort(scores, kind="stable")
    z = scores[order]
    ends = np.flatnonzero(np.r_[z[1:] != z[:-1], True])
    cumulative = [np.cumsum(x[order], dtype=np.int64) for x in
                  (positive, negative, unknown, positive * (length > 5))]
    rows = [dict(threshold=None, selected_candidates=0, positive_bp=0,
                 negative_bp=0, unknown_bp=0, long_positive_bp=0)]
    for end in ends:
        rows.append(dict(threshold=float(z[end]), selected_candidates=int(end + 1),
                         **{k: int(a[end]) for k, a in zip(
                             ("positive_bp", "negative_bp", "unknown_bp", "long_positive_bp"), cumulative)}))
    return rows


def gates(point, count_min, positive_den, long_den, span):
    return dict(candidate_minimum=point["selected_candidates"] >= count_min,
                positive_recovery=point["positive_bp"] * 10 >= positive_den,
                long_positive_recovery=point["long_positive_bp"] * 20 >= long_den,
                known_negative_budget=point["negative_bp"] * 1_000_000 <= span * 10,
                worst_case_budget=(point["negative_bp"] + point["unknown_bp"]) * 1_000_000 <= span * 20)


def focused_test():
    p = prefixes(np.array([0., 0., 1.]), np.array([2, 0, 7]),
                 np.array([0, 1, 0]), np.array([0, 3, 0]), np.array([2, 4, 7]))
    assert [r["selected_candidates"] for r in p] == [0, 2, 3]
    assert p[1]["positive_bp"] == 2 and p[1]["unknown_bp"] == 3
    assert p[2]["long_positive_bp"] == 7
    g = gates(p[1], 2, 20, 1, 100000)
    assert g["known_negative_budget"] and not g["worst_case_budget"]
    assert g["positive_recovery"] and not g["long_positive_recovery"]
    print("tie/unknown/budget-boundary test PASS", flush=True)


def main():
    focused_test()
    assert json.loads((SOURCE / "numerical_audit.json").read_text())["status"] == "PASS"
    with MANIFEST.open() as handle:
        rows = [r for r in csv.DictReader(handle, delimiter="\t")
                if r["seqid"] == "chr13" and r["role"] == "DEV"]
    ids = [r["candidate_id"] for r in rows]
    known = np.array([r["comparator_known"] == "1" for r in rows])
    assert len(rows) == 60574 and known.sum() == 60569 and len(set(ids)) == len(ids)
    positive, negative, unknown, length = [np.array([int(r[k]) for r in rows], dtype=np.int64)
                                          for k in ("positive_bp", "negative_bp", "unknown_bp", "gap_length")]
    assert np.array_equal(positive + negative + unknown, length)
    assert np.array_equal(known, unknown == 0)
    predictions = {}
    for path in sorted((SOURCE / "predictions").glob("DEV-*.npz")):
        with np.load(path) as f:
            block_ids = f["ids"].tolist()
            z = np.stack([f[f"HN-O__seed{s}"] for s in SEEDS]).astype(np.float32).mean(axis=0)
            assert len(block_ids) == len(z) and np.isfinite(z).all()
            for cid, value in zip(block_ids, z):
                assert cid not in predictions
                predictions[cid] = value
    assert set(predictions) == set(ids)
    scores = np.array([predictions[cid] for cid in ids], dtype=np.float32)
    count_min = max(1000, (int(known.sum()) + 99) // 100)
    positive_den = int(positive[known].sum())
    long_den = int(positive[known & (length > 5)].sum())
    assert positive_den > 0 and long_den > 0
    frontier = prefixes(scores, positive, negative, unknown, length)
    for row in frontier:
        row.update(gates(row, count_min, positive_den, long_den, SPAN))
    risk_keys = ("known_negative_budget", "worst_case_budget")
    utility_keys = ("candidate_minimum", "positive_recovery", "long_positive_recovery")
    risk_point = [r for r in frontier if all(r[k] for k in risk_keys)][-1]
    utility_point = next((r for r in frontier if all(r[k] for k in utility_keys)), None)
    feasible = [r for r in frontier if all(r[k] for k in risk_keys + utility_keys)]
    # Independent direct boolean selection, not reuse of cumulative arrays.
    for point in (risk_point, utility_point):
        if point is None:
            continue
        selected = np.zeros(len(scores), dtype=bool) if point["threshold"] is None else scores <= point["threshold"]
        assert int(selected.sum()) == point["selected_candidates"]
        for field, array in (("positive_bp", positive), ("negative_bp", negative),
                             ("unknown_bp", unknown), ("long_positive_bp", positive * (length > 5))):
            assert int(array[selected].sum()) == point[field]
    result = dict(status="NECESSARY_ONLY_FEASIBLE" if feasible else "RANK_ACTION_NECESSARY_NO_GO",
                  dev_rows=len(rows), known_rows=int(known.sum()), unknown_rows=int((~known).sum()),
                  known_positive_bp=positive_den, known_long_positive_bp=long_den,
                  optimistic_genome_span_bp=SPAN, selected_candidate_minimum=count_min,
                  unique_score_thresholds=len(frontier) - 1, feasible_thresholds=len(feasible),
                  risk_limited_maximum=risk_point, minimum_utility_threshold=utility_point,
                  direct_decision_point_recomputation="PASS", cal_or_sealed_scored=False,
                  scope="Optimistic necessary conditions only on reused DEV; no CAL or deployment claim")
    OUT.mkdir(parents=True, exist_ok=False)
    with (OUT / "frontier.tsv").open("x") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(frontier[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(frontier)
    with (OUT / "result.json").open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
