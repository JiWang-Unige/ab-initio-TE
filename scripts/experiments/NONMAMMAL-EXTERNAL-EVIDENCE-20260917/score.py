#!/usr/bin/env python3
"""Score fixed D against source-dependent and structural positive layers."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

import panel


TE_CLASSES = {"DNA", "LINE", "SINE", "LTR", "RC", "Retroposon"}


def legacy_reference(source, output, regions):
    classes, selected = Counter(), 0
    with panel.open_text(source) as handle, output.open("w") as out:
        for line in handle:
            fields = line.split()
            if len(fields) < 11 or not fields[0].isdigit():
                continue
            seqid, start, end = fields[4], int(fields[5]) - 1, int(fields[6])
            if seqid not in regions:
                continue
            region = regions[seqid]
            if end <= region["start"] or start >= region["end"]:
                continue
            cls = fields[10].split("/", 1)[0]
            classes[cls] += 1
            if cls in TE_CLASSES:
                out.write(f"{seqid}\t{start}\t{end}\t{fields[9]}\t{fields[10]}\n")
                selected += 1
    return {"panel_rows_by_source_class": dict(classes), "known_te_rows": selected,
            "selected_classes": sorted(TE_CLASSES),
            "unknown_policy": "Unknown and non-TE repeat classes are not used as reference positives; not converted into negatives"}


def structure_reference(source, output, by_panel):
    count = 0
    with source.open() as handle, output.open("w") as out:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            location = line.split()[0]
            match = re.fullmatch(r"(.+):(\d+)\.\.(\d+)", location)
            if match is None:
                raise ValueError(f"unexpected LTR_retriever pass-list location: {location}")
            name, begin, finish = match.groups()
            row = by_panel[name]
            # Native LTR_retriever writes descending locations on minus strand.
            low, high = sorted((int(begin), int(finish)))
            start, end = low - 1, high
            if not 0 <= start < end <= row["end"] - row["start"]:
                raise ValueError(f"structural evidence exceeds panel: {location}")
            out.write(f"{row['seqid']}\t{row['start'] + start}\t{row['start'] + end}\t{location}\n")
            count += 1
    return count


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    prepared = json.loads((args.panel / "panel.json").read_text())
    native = json.loads((args.inference / "summary.json").read_text())
    if native["status"] != "COMPLETED" or native["total_bp"] != prepared["total_bp"]:
        raise ValueError("native inference is incomplete or uses a different denominator")
    if Path(native["input_fasta"]).resolve() != (args.panel / "panel.fa").resolve():
        raise ValueError("native inference does not belong to this fixed panel")
    prediction = args.inference / "material_runs.bed"
    regions = {row["seqid"]: row for row in prepared["regions"]}
    legacy = args.output / "historical_rm_positive.bed"
    legacy_info = legacy_reference(prepared["source"]["historical_rm_out"], legacy, regions)
    result = {"species": prepared["species"], "panel": prepared,
              "inference": str(args.inference), "frozen_threshold": native["threshold"],
              "legacy_source": legacy_info, "layers": {}}
    score_args = argparse.Namespace(panel=args.panel, reference=legacy,
                                    prediction=prediction, layer="historical_repeatmasker_known_TE",
                                    output=args.output / "historical_rm_recovery.json")
    result["layers"]["historical_repeatmasker"] = panel.evaluate(score_args)
    if args.structure:
        exit_file = args.structure / "native.exit_code"
        pass_files = list(args.structure.glob("**/panel.fa.pass.list"))
        result["structure"] = {"directory": str(args.structure),
                               "native_exit": exit_file.read_text().strip() if exit_file.exists() else None,
                               "pass_lists": [str(p) for p in pass_files]}
        if not exit_file.exists() or exit_file.read_text().strip() != "0":
            result["structure"]["status"] = "NATIVE_NOT_COMPLETED_SUCCESSFULLY"
        elif len(pass_files) != 1:
            result["structure"]["status"] = "PASS_LIST_ABSENT_OR_NOT_UNIQUE_REQUIRES_NATIVE_LOG_REVIEW"
        else:
            structural = args.output / "structural_ltr_positive.bed"
            n = structure_reference(pass_files[0], structural,
                                    {row["panel_id"]: row for row in prepared["regions"]})
            result["structure"].update(status="STRUCTURAL_POSITIVE_LAYER", insertion_candidates=n)
            if n:
                score_args.reference = structural
                score_args.layer = "LTR_retriever_native_structural_pass_not_manual_truth"
                score_args.output = args.output / "structural_ltr_recovery.json"
                result["layers"]["structural_ltr"] = panel.evaluate(score_args)
            else:
                result["structure"]["status"] = "NO_STRUCTURAL_POSITIVES_RECOVERY_UNDEFINED"
    result["claim_boundary"] = "Regional positive-layer recovery; no reliable negatives, biological precision/F1, or whole-genome generalization claim. Structural support is algorithmic and selected toward intact LTRs."
    panel.dump(args.output / "result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--inference", type=Path, required=True)
    parser.add_argument("--structure", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(run(parser.parse_args()), indent=2))
