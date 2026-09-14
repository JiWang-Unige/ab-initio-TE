#!/usr/bin/env python3
"""Join fixed CHM13 support fields after source-only control selection.

The control table is produced without reading the newer annotation.  This
reporting pass only joins the already-computed overlap table after matching is
complete; it cannot alter the selected cases or controls.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


VALID_STATES = ("TP", "FP", "FN", "TN")
CATEGORIES = ("TE", "UNKNOWN", "NONTE", "UNRECOGNIZED")
LAYERS = ("any", "ge50", "ge80")


def _support_field(category: str, layer: str) -> str:
    return f"{category}_{layer}_supported"


def _overlap_field(category: str, layer: str) -> str:
    return f"{category}_{layer}_overlap_bp"


def _bool(value: str, field: str, row_number: int) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"row {row_number}: expected True/False for {field}, got {value!r}")


def _fraction(numerator: int, denominator: int) -> Optional[float]:
    return numerator / float(denominator) if denominator else None


def read_match_table(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"match table has no header: {path}")
        required = {
            "fp_mapping_id",
            "control_mapping_id",
            "match_status",
            "fp_old_te_relation",
            "control_reused",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"match table missing fields: {sorted(missing)}")
        return list(reader)


def read_support_rows(path: Path, wanted: set[str]) -> Dict[str, dict]:
    result: Dict[str, dict] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"support table has no header: {path}")
        required = {"mapping_id"}
        for category in CATEGORIES:
            for layer in LAYERS:
                required.add(_support_field(category, layer))
                required.add(_overlap_field(category, layer))
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"support table missing fields: {sorted(missing)}")
        for row_number, row in enumerate(reader, 2):
            mapping_id = row["mapping_id"]
            if mapping_id in wanted:
                result[mapping_id] = row
    missing_ids = wanted - set(result)
    if missing_ids:
        raise ValueError(f"support table missing selected IDs: {sorted(missing_ids)[:5]}")
    return result


def read_qualification_strata(path: Path) -> dict:
    """Summarize chain/sequence strata without consulting target labels."""
    states = {state: 0 for state in VALID_STATES}
    chain_by_state = {
        state: collections.Counter() for state in VALID_STATES
    }
    sequence_by_state = {
        state: collections.Counter() for state in VALID_STATES
    }
    mismatch_by_state = {
        state: {"checked_n": 0, "mismatch_n": 0, "mismatch_bp_total": 0}
        for state in VALID_STATES
    }
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "state",
            "eligible_for_matching",
            "chain_stratum",
            "sequence_status",
            "mismatch_bp",
        }
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError(f"qualification table missing strata fields: {path}")
        for row_number, row in enumerate(reader, 2):
            state = row["state"]
            if state not in states:
                raise ValueError(f"row {row_number}: unexpected state {state!r}")
            states[state] += 1
            if row["eligible_for_matching"] == "True":
                chain_by_state[state][row["chain_stratum"]] += 1
                sequence_by_state[state][row["sequence_status"]] += 1
                mismatch = row["mismatch_bp"]
                if mismatch != "":
                    value = int(mismatch)
                    mismatch_by_state[state]["checked_n"] += 1
                    mismatch_by_state[state]["mismatch_n"] += value > 0
                    mismatch_by_state[state]["mismatch_bp_total"] += value

    return {
        "source_state_counts": states,
        "chain_strata_by_state": {state: dict(values) for state, values in chain_by_state.items()},
        "sequence_strata_by_state": {
            state: dict(values) for state, values in sequence_by_state.items()
        },
        "mismatch_by_state": mismatch_by_state,
    }


def _support_summary(rows: Sequence[dict], support: Mapping[str, dict]) -> dict:
    matched = [row for row in rows if row["match_status"] == "MATCHED_TN"]
    by_category: MutableMapping[str, MutableMapping[str, dict]] = collections.defaultdict(dict)
    for category in CATEGORIES:
        for layer in LAYERS:
            fp_n = 0
            control_n = 0
            unique_control_ids: set[str] = set()
            unique_control_support: Dict[str, bool] = {}
            for row in matched:
                fp_id = row["fp_mapping_id"]
                control_id = row["control_mapping_id"]
                fp_value = _bool(
                    support[fp_id][_support_field(category, layer)],
                    _support_field(category, layer),
                    0,
                )
                control_value = _bool(
                    support[control_id][_support_field(category, layer)],
                    _support_field(category, layer),
                    0,
                )
                fp_n += fp_value
                control_n += control_value
                unique_control_ids.add(control_id)
                unique_control_support[control_id] = control_value
            unique_n = sum(unique_control_support.values())
            pair_n = len(matched)
            unique_count = len(unique_control_ids)
            by_category[category][layer] = {
                "matched_pair_n": pair_n,
                "fp_supported_n": fp_n,
                "fp_support_fraction": _fraction(fp_n, pair_n),
                "control_supported_n": control_n,
                "control_support_fraction": _fraction(control_n, pair_n),
                "fp_minus_control_fraction": (
                    _fraction(fp_n, pair_n) - _fraction(control_n, pair_n)
                    if pair_n
                    else None
                ),
                "unique_control_n": unique_count,
                "unique_control_supported_n": unique_n,
                "unique_control_support_fraction": _fraction(unique_n, unique_count),
            }
    return dict(by_category)


def _support_by_relation(rows: Sequence[dict], support: Mapping[str, dict]) -> dict:
    relations = sorted({row["fp_old_te_relation"] for row in rows})
    result: Dict[str, dict] = {}
    for relation in relations:
        subset = [row for row in rows if row["fp_old_te_relation"] == relation]
        result[relation] = _support_summary(subset, support)
    return result


def write_joined_table(path: Path, rows: Sequence[dict], support: Mapping[str, dict]) -> None:
    fields = [
        "fp_mapping_id",
        "control_mapping_id",
        "match_status",
        "fp_old_te_relation",
        "fp_old_te_distance_bp",
        "fp_old_te_distance_bin",
        "control_old_te_distance_bp",
        "control_old_te_distance_bin",
        "gc_abs_diff",
        "boundary_distance_abs_diff",
        "candidate_count",
        "control_reused",
    ]
    for side in ("fp", "control"):
        for category in CATEGORIES:
            for layer in LAYERS:
                fields.extend(
                    [
                        f"{side}_{category}_{layer}_supported",
                        f"{side}_{category}_{layer}_overlap_bp",
                    ]
                )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            output = {field: row.get(field, "") for field in fields}
            for side, mapping_id in (("fp", row["fp_mapping_id"]), ("control", row["control_mapping_id"])):
                if row["match_status"] != "MATCHED_TN" and side == "control":
                    continue
                selected = support[mapping_id]
                for category in CATEGORIES:
                    for layer in LAYERS:
                        output[f"{side}_{category}_{layer}_supported"] = selected[
                            _support_field(category, layer)
                        ]
                        output[f"{side}_{category}_{layer}_overlap_bp"] = selected[
                            _overlap_field(category, layer)
                        ]
            writer.writerow(output)


def run(args: argparse.Namespace) -> dict:
    match_rows = read_match_table(args.matched_controls)
    matched_ids = {row["fp_mapping_id"] for row in match_rows}
    matched_ids.update(
        row["control_mapping_id"]
        for row in match_rows
        if row["match_status"] == "MATCHED_TN"
    )
    support = read_support_rows(args.overlap_table, matched_ids)
    qualification_strata = read_qualification_strata(args.qualification_table)
    # A missing FP support row would indicate a broken join even for an
    # unmatched case; require it explicitly before writing the report.
    for row in match_rows:
        if row["fp_mapping_id"] not in support:
            raise ValueError(f"missing FP support row {row['fp_mapping_id']}")
    matched = [row for row in match_rows if row["match_status"] == "MATCHED_TN"]
    unique_controls = {row["control_mapping_id"] for row in matched}
    source_summary = json.loads(args.qualification_summary.read_text(encoding="utf-8"))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_joined_table(output / "matched_support.tsv", match_rows, support)
    summary = {
        "status": "MATCHED_CHM13_SUPPORT_REPORT_COMPLETED",
        "protocol": "HG19_CHM13V2_MATCHED_BACKGROUND_AND_SEQUENCE_QUALIFICATION",
        "seed": 42,
        "source_interval_count": source_summary["source_interval_count"],
        "source_state_counts": source_summary["source_state_counts"],
        "qualified_mapping_count": source_summary["qualified_mapping_count"],
        "qualified_count_by_state": source_summary["qualified_count_by_state"],
        "qualification_strata": qualification_strata,
        "case_fp_qualified_n": len(match_rows),
        "matched_pair_n": len(matched),
        "unmatched_fp_n": len(match_rows) - len(matched),
        "unique_controls_used_n": len(unique_controls),
        "support_by_category_layer": _support_summary(match_rows, support),
        "support_by_old_te_relation": _support_by_relation(match_rows, support),
        "target_annotation_join": {
            "source": "fixed precomputed CHM13 overlap table",
            "selection_completed_before_join": True,
            "new_annotation_used_for_selection": False,
            "model_probability_used_for_selection": False,
            "target_sequence_used_for_selection": False,
        },
        "claim_policy": {
            "matched_control_is_confirmation": False,
            "same_base_f1_computed": False,
            "fp_rescue_claim": False,
            "enrichment_test": False,
        },
        "outputs": {
            "matched_support": str(output / "matched_support.tsv"),
            "summary": str(output / "summary.json"),
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "completion.json").write_text(
        json.dumps(
            {
                "status": summary["status"],
                "new_annotation_used_for_selection": False,
                "same_base_f1_computed": False,
                "fp_rescue_claim": False,
                "summary": str(output / "summary.json"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matched-controls", type=Path, required=True)
    parser.add_argument("--overlap-table", type=Path, required=True)
    parser.add_argument("--qualification-summary", type=Path, required=True)
    parser.add_argument("--qualification-table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
