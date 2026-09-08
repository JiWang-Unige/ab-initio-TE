#!/usr/bin/env python3
"""One-run independent arithmetic/denominator check, not a new scientific gate."""
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score

from screen import OUT, MANIFEST, ARMS, SEEDS


def main():
    plan = json.loads((OUT / "plan.json").read_text())
    result = json.loads((OUT / "result.json").read_text())
    training = json.loads((OUT / "training/summary.json").read_text())
    ntrain = sum(len(b["rows"]) for b in plan["blocks"] if b["role"] == "TRAIN")
    updates = sum((len(b["rows"])+511)//512 for b in plan["blocks"] if b["role"] == "TRAIN")
    consumption = {}
    for record in training["summaries"]:
        assert record["samples_per_head"] == ntrain
        assert record["updates_per_head"] == updates
        for key in record["heads"]:
            pair = (key, record["epoch"])
            assert pair not in consumption
            assert np.isfinite(record["mean_weighted_loss"][key])
            consumption[pair] = ntrain
    expected = {(f"{a}__seed{s}", e) for a in ARMS for s in SEEDS for e in (1, 2)}
    assert set(consumption) == expected

    predictions = {}
    for b in plan["blocks"]:
        if b["role"] != "DEV":
            continue
        with np.load(OUT / "predictions" / (b["key"]+".npz")) as file:
            for i, cid in enumerate(file["ids"].tolist()):
                assert cid not in predictions
                predictions[cid] = {f"{a}__seed{s}": file[f"{a}__seed{s}"][i]
                                    for a in ARMS for s in SEEDS}
    with MANIFEST.open() as handle:
        rows = [r for r in csv.DictReader(handle, delimiter="\t")
                if r["seqid"] == "chr13" and r["role"] == "DEV"]
    assert len(rows) == 60574 and set(predictions) == {r["candidate_id"] for r in rows}
    assert all(np.isfinite(list(predictions[r["candidate_id"]].values())).all() for r in rows)
    rows = [r for r in rows if r["comparator_known"] == "1"]
    assert len(rows) == 60569
    positive = np.array([int(r["positive_bp"]) for r in rows], dtype=np.float64)
    negative = np.array([int(r["negative_bp"]) for r in rows], dtype=np.float64)
    length = positive+negative
    target = negative/length
    checks = {}
    for arm in ARMS:
        seed_logits = np.array([[predictions[r["candidate_id"]][f"{arm}__seed{s}"] for r in rows]
                                for s in SEEDS], dtype=np.float32)
        logits = seed_logits.mean(axis=0).astype(np.float64)
        risk = 1/(1+np.exp(-np.clip(logits, -700, 700)))
        mse = float(np.average(np.square(target-risk), weights=length))
        # Two weighted pseudo-observations per candidate, not per-base expansion.
        ap = float(average_precision_score(np.tile([1, 0], len(rows)),
                    np.repeat(1-risk, 2), sample_weight=np.column_stack([positive, negative]).ravel()))
        brier = float(np.dot(positive, risk**2)/length.sum()
                      + np.dot(negative, (1-risk)**2)/length.sum())
        saved = result["results"][arm]["known_DEV"]
        for field, value in (("fraction_mse", mse), ("action_ap", ap), ("pseudo_base_brier", brier)):
            assert np.isclose(value, saved[field], atol=1e-12, rtol=1e-10), (arm, field, value, saved[field])
        checks[arm] = dict(fraction_mse=mse, action_ap=ap, pseudo_base_brier=brier)
    for arm in ARMS[1:]:
        control, novel = checks[ARMS[0]], checks[arm]
        if control["fraction_mse"] == 0:
            expected_status = "UNDETERMINED"
        else:
            delta = 1-novel["fraction_mse"]/control["fraction_mse"]
            expected_status = "SCREEN_POSITIVE" if delta >= .05 and novel["action_ap"] >= control["action_ap"] else "SCREEN_GATE_FAIL"
        assert result["gates"][arm]["status"] == expected_status
    audit = dict(status="PASS", dev_predictions=60574, known_dev=60569,
        training_rows_per_head_per_pass=ntrain, updates_per_head_per_pass=updates,
        verified_head_pass_pairs=len(consumption), independently_recomputed=checks,
        method="NumPy weighted averages and sklearn two-weighted-observation AP; no screen metric functions called",
        cal_or_sealed_scored=False,
        manifest_projection="Only chr13 DEV target fields enter arithmetic; other manifest rows are filtered by role/seqid, not scored")
    with (OUT / "numerical_audit.json").open("x") as handle:
        json.dump(audit, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(audit, allow_nan=False))


if __name__ == "__main__":
    main()
