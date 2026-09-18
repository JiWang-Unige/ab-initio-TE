#!/usr/bin/env python3
"""Score full-input calls against the frozen same-assembly comparator layer."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import sys
from typing import Dict, Iterable, List, Optional, Tuple

from common import fasta_records, write_json


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "outputs/WHOLE-GENOME-BENCHMARK-20260918"
TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "RETROPOSON"}
UNKNOWN = {"", "?", "-", "unknown", "unspecified", "unclassified", "na", "none", "."}
UNCERTAIN_MARKERS = ("?", "artefact")
DNA_BASES = frozenset("ACGT")

# EDTA and RepeatMasker use a small set of GFF feature names for material
# calls.  Parent/container rows are handled separately below so their spans do
# not fill sequence gaps between child hit parts.
TE_FEATURE_TYPES = {
    "repeat", "repeat_region", "match", "match_part", "transposable_element",
    "transposable_element_insertion_site", "mobile_element", "retrotransposon",
    "ltr_retrotransposon", "line", "sine", "dna_transposon", "rc",
    "retroposon", "helitron", "tir", "mite", "terminal_inverted_repeat",
    "long_terminal_repeat", "inverted_repeat", "repeat_fragment", "dispersed_repeat",
}
NON_TE_FEATURE_TYPES = {
    "gene", "mrna", "transcript", "exon", "cds", "region", "chromosome",
    "contig", "sequence_feature", "target_site_duplication", "five_prime_utr",
    "three_prime_utr", "rrna_gene", "rrna",
}
STRUCTURAL_FEATURE_TYPES = {
    "long_terminal_repeat", "terminal_inverted_repeat", "inverted_repeat",
    "five_prime_ltr", "three_prime_ltr", "protein_match", "coding_sequence",
}
NON_TE_CLASSES = {
    "simple_repeat", "low_complexity", "satellite", "rna", "rrna", "scrna",
    "snrna", "srprna", "trna", "other", "centromere", "telomere",
}
COMPLETE_TE_FEATURE_TYPES = {
    "repeat", "repeat_region", "transposable_element", "mobile_element",
    "retrotransposon", "ltr_retrotransposon", "line", "sine", "dna_transposon",
    "rc", "retroposon", "helitron", "tir", "mite",
}
CLASS_ATTRIBUTE_KEYS = {
    "classification", "class_family", "repeat_class", "class", "family",
    "repclass", "repeat_type", "target",
}
RM_TE_CLASSES = {"line", "sine", "ltr", "dna", "rc", "retroposon", "ambiguous_te", "ambiguous"}
RM_UNKNOWN_CLASSES = {"", "?", "-", "unknown", "unspecified", "unclassified", "na", "none", "."}


def merge(intervals: Iterable[Tuple[int, int]]) -> List[Tuple[int, int]]:
    merged: List[List[int]] = []
    for left, right in sorted(intervals):
        if right <= left:
            continue
        if not merged or left > merged[-1][1]:
            merged.append([left, right])
        else:
            merged[-1][1] = max(merged[-1][1], right)
    return [(left, right) for left, right in merged]


def overlap(a: List[Tuple[int, int]], b: List[Tuple[int, int]]) -> int:
    i = j = total = 0
    while i < len(a) and j < len(b):
        left = max(a[i][0], b[j][0])
        right = min(a[i][1], b[j][1])
        if right > left:
            total += right - left
        if a[i][1] <= b[j][1]:
            i += 1
        else:
            j += 1
    return total


def broad_class(raw: str) -> str:
    token = raw.strip()
    if token.lower() in UNKNOWN:
        return "Unknown"
    return token.split("/", 1)[0].split("|", 1)[0].split(":", 1)[0].upper()


def uncertain_label(label: str, family: str) -> bool:
    """Return whether a comparator row must be excluded from negative truth."""
    text = "%s %s" % (label.strip().lower(), family.strip().lower())
    token = label.strip().lower()
    return token in UNKNOWN or any(marker in text for marker in UNCERTAIN_MARKERS)


def sum_bp(intervals: Dict[str, List[Tuple[int, int]]], chroms: Optional[set] = None) -> int:
    keys = set(intervals)
    if chroms is not None:
        keys &= chroms
    return sum(right - left for chrom in keys for left, right in intervals.get(chrom, []))


def intersect_intervals(a: List[Tuple[int, int]], b: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Return the sorted intersection of two merged interval lists."""
    i = j = 0
    result: List[Tuple[int, int]] = []
    while i < len(a) and j < len(b):
        left = max(a[i][0], b[j][0])
        right = min(a[i][1], b[j][1])
        if right > left:
            result.append((left, right))
        if a[i][1] <= b[j][1]:
            i += 1
        else:
            j += 1
    return result


def subtract_intervals(base: List[Tuple[int, int]], excluded: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Subtract merged half-open intervals without turning exclusions into negatives."""
    if not excluded:
        return list(base)
    result: List[Tuple[int, int]] = []
    j = 0
    for left, right in base:
        cursor = left
        while j < len(excluded) and excluded[j][1] <= cursor:
            j += 1
        k = j
        while k < len(excluded) and excluded[k][0] < right:
            cut_left, cut_right = excluded[k]
            if cut_left > cursor:
                result.append((cursor, min(cut_left, right)))
            cursor = max(cursor, cut_right)
            if cursor >= right:
                break
            k += 1
        if cursor < right:
            result.append((cursor, right))
    return result


def native_class_candidate(raw: str) -> bool:
    """Whether a native class is sequence-level TE material for binary scoring."""
    value = str(raw or "").strip().replace(" ", "_")
    upper = value.upper()
    if "?" in upper:
        return True
    pieces = [piece for piece in re.split(r"[/|:]", upper) if piece]
    base = pieces[0] if pieces else ""
    if base in {"LINE", "SINE", "LTR", "DNA", "RC", "RETROPOSON", "TIR", "MITE", "TRANSPOSON", "HELITRON"}:
        return True
    if base in {token.upper() for token in UNKNOWN} or (len(pieces) > 1 and pieces[1] in {token.upper() for token in UNKNOWN}):
        return True
    if base.lower() in NON_TE_CLASSES:
        return False
    # Native callers may use a valid TE name outside the main ontology. Keep
    # it as unresolved TE material; only explicit non-TE classes are dropped.
    return True


def parse_labels(path: Path) -> Dict[str, object]:
    intervals: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    uncertain: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    rows = 0
    positive_rows = 0
    unknown_rows = 0
    uncertain_rows = 0
    class_rows: Counter = Counter()
    family_rows: Counter = Counter()
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.split()
            if len(fields) < 13:
                continue
            try:
                chrom, start, end = fields[5], int(fields[6]), int(fields[7])
            except (ValueError, IndexError):
                continue
            if end <= start:
                continue
            rows += 1
            label = fields[11]
            family = fields[12]
            broad = broad_class(label)
            class_rows[broad] += 1
            family_rows[family] += 1
            is_uncertain = uncertain_label(label, family)
            if broad == "Unknown":
                unknown_rows += 1
            if is_uncertain:
                uncertain_rows += 1
                uncertain[chrom].append((start, end))
            elif broad in TE_CLASSES:
                positive_rows += 1
                intervals[chrom].append((start, end))
    merged = {chrom: merge(values) for chrom, values in intervals.items()}
    uncertain_merged = {chrom: merge(values) for chrom, values in uncertain.items()}
    return {"path": str(path), "rows": rows, "positive_rows": positive_rows,
            "unknown_rows": unknown_rows, "uncertain_rows": uncertain_rows,
            "class_rows": dict(sorted(class_rows.items())),
            "family_rows": dict(sorted(family_rows.items())), "positive_intervals": merged,
            "uncertain_intervals": uncertain_merged,
            "positive_union_bp": sum(right - left for values in merged.values() for left, right in values),
            "uncertain_union_bp": sum(right - left for values in uncertain_merged.values() for left, right in values),
            "unknown_is_negative": False,
            "unknown_policy": "Unknown, '?' and ARTEFACT rows are retained as an audit stratum and excluded from both positive truth and negative callable truth"}


def parse_gff(path: Path) -> Dict[str, List[Tuple[int, int]]]:
    """Read native TE material rows with explicit EDTA hierarchy handling.

    EDTA's ``repeat_region`` is the material insertion span; its child
    ``long_terminal_repeat`` and ``target_site_duplication`` rows describe
    subfeatures and must not replace or duplicate that parent.  Other native
    callers commonly emit flat ``dispersed_repeat`` rows.  A parent is never
    removed merely because it has children: child rows are skipped only when
    their parent is a retained material container.
    """
    rows = []
    by_id = {}
    children_by_parent = defaultdict(list)

    def attributes(raw: str) -> Dict[str, str]:
        parsed: Dict[str, str] = {}
        for field in raw.split(";"):
            field = field.strip()
            if not field:
                continue
            if "=" in field:
                key, value = field.split("=", 1)
            elif " " in field:
                key, value = field.split(None, 1)
            else:
                continue
            parsed[key.strip().lower()] = value.strip().strip('"')
        return parsed

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\n").split("\t")
            if len(fields) < 5:
                continue
            attrs = attributes(fields[8] if len(fields) >= 9 else "")
            feature = fields[2].strip().lower() if len(fields) >= 3 else ""
            if feature in NON_TE_FEATURE_TYPES or feature in STRUCTURAL_FEATURE_TYPES:
                continue
            raw_class = next((attrs[key] for key in CLASS_ATTRIBUTE_KEYS if attrs.get(key)), "")
            candidate = False
            if raw_class:
                candidate = native_class_candidate(raw_class)
            elif feature in COMPLETE_TE_FEATURE_TYPES:
                # A named complete feature is an unresolved native call when
                # no class attribute is supplied.  A bare repeat_region is a
                # container and is resolved after its child rows are seen.
                candidate = feature != "repeat_region"
            elif feature not in TE_FEATURE_TYPES:
                continue
            try:
                start, end = int(fields[3]) - 1, int(fields[4])
            except ValueError:
                continue
            if end > start:
                row = {"chrom": fields[0], "start": start, "end": end,
                       "id": attrs.get("id"), "parents": [token.strip() for token in
                       attrs.get("parent", "").split(",") if token.strip()],
                       "feature": feature, "candidate": candidate,
                       "raw_class": raw_class}
                rows.append(row)
                if row["id"]:
                    by_id[row["id"]] = row
                    for parent in row["parents"]:
                        children_by_parent[parent].append(row)
    # Match the pinned class-map parser's EDTA hierarchy contract.  A
    # repeat_region is the complete body when it has only structural LTR/TIR
    # children, but it is suppressed when a complete TE child or explicit
    # match-part evidence replaces the container.  Never infer suppression
    # from the mere presence of an arbitrary child feature.
    suppressed_parent_ids = set()
    for row in rows:
        if not row["candidate"] or row["feature"] != "repeat_region" or not row["id"]:
            continue
        child_features = {child["feature"] for child in children_by_parent.get(row["id"], [])}
        complete_children = child_features & COMPLETE_TE_FEATURE_TYPES
        evidence_children = child_features & {"match", "match_part", "repeat", "repeat_region", "transposable_element"}
        if complete_children or evidence_children:
            suppressed_parent_ids.add(row["id"])
    intervals: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for row in rows:
        if not row["candidate"] or (row["id"] and row["id"] in suppressed_parent_ids):
            continue
        # Structural children were filtered before row construction.  A
        # complete child of a suppressed repeat_region remains as material.
        intervals[row["chrom"]].append((row["start"], row["end"]))
    return {chrom: merge(values) for chrom, values in intervals.items()}


def parse_repeatmasker_out(path: Path) -> Dict[str, List[Tuple[int, int]]]:
    """Parse RepeatMasker ``.out`` material using its native class column.

    RepeatMasker GFF3 stores the target name but not the class/family in a
    stable attribute.  The native ``.out`` table has an explicit class/family
    column, allowing simple/low-complexity/RNA annotations to be excluded from
    this TE-material score while retaining rows classified as Unknown.
    """
    intervals: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError("missing or empty RepeatMasker annotation: %s" % path)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            fields = raw.split()
            # Header and separator lines do not have the 11 data columns.
            if len(fields) < 11:
                continue
            try:
                start, end = int(fields[5]) - 1, int(fields[6])
            except (ValueError, IndexError):
                continue
            if end <= start:
                continue
            class_family = fields[10].strip()
            broad = class_family.split("/", 1)[0].split("|", 1)[0].split(":", 1)[0].strip().lower()
            # RM class tables can mark a TE root as DNA? or LTR?; retain its
            # TE material while preserving the raw source in native summaries.
            broad = broad.rstrip("?!")
            # Unknown is retained as candidate TE material for a native
            # caller; it is not silently converted into a known TE class.
            if broad not in RM_TE_CLASSES and broad not in RM_UNKNOWN_CLASSES:
                continue
            intervals[fields[4]].append((start, end))
    return {chrom: merge(values) for chrom, values in intervals.items()}


def parse_bed(path: Path) -> Dict[str, List[Tuple[int, int]]]:
    intervals: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.split()
            if len(fields) < 3:
                continue
            try:
                start, end = int(fields[1]), int(fields[2])
            except ValueError:
                continue
            if end > start:
                intervals[fields[0]].append((start, end))
    return {chrom: merge(values) for chrom, values in intervals.items()}


def fasta_lengths(path: Path) -> Dict[str, int]:
    fai = Path(str(path) + ".fai")
    if fai.exists():
        result = {}
        for raw in fai.read_text(encoding="utf-8", errors="replace").splitlines():
            fields = raw.split("\t")
            if len(fields) >= 2:
                result[fields[0]] = int(fields[1])
        if result:
            return result
    return {name: len(sequence) for name, sequence in fasta_records(path)}


def fasta_callable_intervals(path: Path) -> Tuple[Dict[str, int], Dict[str, List[Tuple[int, int]]]]:
    """Return raw contig lengths and intervals containing A/C/G/T only."""
    lengths: Dict[str, int] = {}
    callable_intervals: Dict[str, List[Tuple[int, int]]] = {}
    for name, sequence in fasta_records(path):
        lengths[name] = len(sequence)
        callable_intervals[name] = [match.span() for match in re.finditer(r"[ACGT]+", sequence)]
    return lengths, callable_intervals


def metric(pred: Dict[str, List[Tuple[int, int]]], truth: Dict[str, List[Tuple[int, int]]],
           eligible: Dict[str, List[Tuple[int, int]]], chroms: Optional[set] = None) -> Dict[str, object]:
    """Score only within eligible ACGT positions after uncertain-row masking."""
    keys = set(pred) | set(truth) | set(eligible)
    if chroms is not None:
        keys &= chroms
    pred_eligible = {chrom: intersect_intervals(pred.get(chrom, []), eligible.get(chrom, [])) for chrom in keys}
    truth_eligible = {chrom: intersect_intervals(truth.get(chrom, []), eligible.get(chrom, [])) for chrom in keys}
    pred_bp = sum(right - left for chrom in keys for left, right in pred_eligible[chrom])
    truth_bp = sum(right - left for chrom in keys for left, right in truth_eligible[chrom])
    tp = sum(overlap(pred_eligible[chrom], truth_eligible[chrom]) for chrom in keys)
    fp, fn = pred_bp - tp, truth_bp - tp
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {"tp_bp": tp, "fp_bp": fp, "fn_bp": fn, "predicted_union_bp": pred_bp,
            "comparator_positive_union_bp": truth_bp, "precision": precision, "recall": recall, "f1": f1,
            "eligible_callable_bp": sum_bp(eligible, keys), "comparator_relative": True}


def status(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {"status": "MISSING", "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def score(args: argparse.Namespace) -> Dict[str, object]:
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    labels = {}
    lengths = {}
    callable_intervals = {}
    eligible_intervals = {}
    for species, species_cfg in config["species"].items():
        label_path = Path(species_cfg["label_source"])
        source = Path(species_cfg["fasta"])
        if not label_path.is_file():
            raise FileNotFoundError("label source missing: %s" % label_path)
        labels[species] = parse_labels(label_path)
        lengths[species], callable_intervals[species] = fasta_callable_intervals(source)
        eligible_intervals[species] = {
            chrom: subtract_intervals(
                callable_intervals[species].get(chrom, []),
                labels[species]["uncertain_intervals"].get(chrom, []),
            )
            for chrom in callable_intervals[species]
        }
        labels[species]["raw_sequence_bp"] = sum(lengths[species].values())
        labels[species]["acgt_callable_bp"] = sum_bp(callable_intervals[species])
        labels[species]["uncertain_callable_bp"] = sum(
            overlap(callable_intervals[species].get(chrom, []), intervals)
            for chrom, intervals in labels[species]["uncertain_intervals"].items()
        )
        labels[species]["eligible_callable_bp"] = sum_bp(eligible_intervals[species])
    required = []
    outputs = {}
    for species in config["species"]:
        for method in ("EDTA", "RM2"):
            native = EXP / "native" / species / method
            state = status(native / "status.json")
            if state.get("status") != "COMPLETED":
                raise RuntimeError("native cell is not complete: %s" % native)
            if not (native / "annotation.gff3").exists() or not (native / "annotation_summary.json").exists():
                raise RuntimeError("native annotation summary missing: %s" % native)
            if method == "RM2":
                if not (native / "annotation.out").exists():
                    raise RuntimeError("RepeatMasker native .out missing: %s" % native)
                outputs[(species, method)] = parse_repeatmasker_out(native / "annotation.out")
            else:
                outputs[(species, method)] = parse_gff(native / "annotation.gff3")
        d = EXP / "d" / species / "gpu"
        d_state = status(d / "status.json")
        if d_state.get("status") != "COMPLETED":
            raise RuntimeError("D GPU cell is not complete: %s" % d)
        outputs[(species, "D_gpu")] = parse_bed(d / "prediction/material_runs.bed")
        required.append({"species": species, "mode": "D_gpu", "status": d_state.get("status")})
    strata_by_species = {species: {"whole_assembly": None} for species in config["species"]}
    # The independent stratum must follow the actual D checkpoint exposure
    # audit.  The historical SF5 chromosome split is retained in the config
    # only for retrospective reporting and is not a D-independent test set.
    for species, split in config["d_exposure_audit"]["exposure_chromosomes"].items():
        if species in config["species"] and split.get("independent_test"):
            strata_by_species[species]["d_independent_test"] = set(split["independent_test"])
    metrics = {}
    for (species, method), prediction in outputs.items():
        truth = labels[species]["positive_intervals"]
        metrics[species + "/" + method] = {}
        for stratum, chroms in strata_by_species[species].items():
            selected = chroms
            value = metric(prediction, truth, eligible_intervals[species], selected)
            if selected is not None:
                value["stratum_chromosomes"] = sorted(selected)
            raw_bp = sum(lengths[species].values()) if selected is None else sum(
                lengths[species].get(chrom, 0) for chrom in selected
            )
            acgt_bp = sum_bp(callable_intervals[species], selected)
            uncertain_bp = sum(
                overlap(callable_intervals[species].get(chrom, []),
                        labels[species]["uncertain_intervals"].get(chrom, []))
                for chrom in (callable_intervals[species] if selected is None else selected)
            )
            value["raw_sequence_bp"] = raw_bp
            value["acgt_callable_bp"] = acgt_bp
            value["uncertain_excluded_bp"] = uncertain_bp
            value["callable_denominator_bp"] = value["eligible_callable_bp"]
            metrics[species + "/" + method][stratum] = value
    native_composition = {}
    for species in config["species"]:
        for method in ("EDTA", "RM2"):
            summary = json.loads((EXP / "native" / species / method / "annotation_summary.json").read_text())
            native_composition[species + "/" + method] = {"annotation": summary["annotation"], "library": summary["library"]}
    optional_cpu = {}
    cpu_feasibility = {}
    for species in config["species"]:
        path = EXP / "d" / species / "cpu" / "status.json"
        optional_cpu[species] = status(path)
        # A resource-gate decision is deliberately separate from the native
        # full-CPU run status.  This lets the result distinguish an explicit
        # budget-limited non-submission from a missing/unknown run directory.
        feasibility_path = EXP / "d" / species / "cpu_feasibility.json"
        cpu_feasibility[species] = status(feasibility_path)
    result = {
        "protocol": "WHOLE-GENOME-BENCHMARK-20260918", "status": "COMPLETED",
        "accuracy_status": "COMPARATOR_RELATIVE", "species": list(config["species"]),
        "methods": ["EDTA", "RM2", "D_gpu"], "required_cells": required,
        "native_material_parsers": {
            "EDTA": "annotation.gff3: EDTA repeat_region/material rows; child subfeatures are not double-counted and rRNA/target-site rows are excluded",
            "RM2": "annotation.out: retain LINE/SINE/LTR/DNA/RC/Retroposon and Unknown class rows; exclude Simple_repeat, Low_complexity, Satellite, RNA and other non-TE classes",
            "D_gpu": "prediction/material_runs.bed: binary material output",
        },
        "metrics": metrics, "native_composition": native_composition,
        "label_audit": {species: {key: value for key, value in labels[species].items()
                                   if key not in {"positive_intervals", "uncertain_intervals"}}
                        for species in labels},
        "cpu_full_status": optional_cpu,
        "cpu_feasibility": cpu_feasibility,
        "cpu_policy": "A CPU full-genome row is added only after a terminal native run; a pilot or extrapolation is never a measured whole-genome runtime. Explicit resource-gate decisions are reported separately under cpu_feasibility",
        "d_exposure_audit": config["d_exposure_audit"],
        "secondary_historical_strata": config["evaluation"]["secondary_historical_strata"],
        "truth_boundary": config["evaluation"]["truth_boundary"],
        "unknown_policy": "Unknown, '?', and ARTEFACT comparator rows remain reported and are excluded from both positive truth and negative callable truth; known non-TE rows remain eligible negatives",
        "native_class_evaluation": {
            "status": "COMPOSITION_AUDIT_ONLY",
            "reason": "Native class/family counts and Unknown coverage are retained for audit. This binary score does not claim class precision, recall, or a class confusion matrix; D has no class output.",
        },
        "strata_contract": "Each species has its own whole_assembly and D-independent_test strata; no chromosome from another species is scored under its name",
        "labels_used_only_in_score": True,
    }
    out = args.output_dir.resolve()
    if out.exists():
        raise FileExistsError("refusing to replace an existing score directory: %s" % out)
    out.mkdir(parents=True)
    write_json(out / "result.json", result)
    with (out / "metrics.tsv").open("w", encoding="utf-8") as handle:
        handle.write("species\tmethod\tstratum\ttp_bp\tfp_bp\tfn_bp\tprecision\trecall\tf1\n")
        for key, strata_values in metrics.items():
            species, method = key.split("/", 1)
            for stratum, value in strata_values.items():
                handle.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" %
                             (species, method, stratum, value["tp_bp"], value["fp_bp"], value["fn_bp"],
                              value["precision"], value["recall"], value["f1"]))
    print(json.dumps({"status": "COMPLETED", "metrics": metrics,
                      "cpu_full_status": optional_cpu,
                      "cpu_feasibility": cpu_feasibility}, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/WHOLE-GENOME-BENCHMARK-20260918.json")
    parser.add_argument("--output-dir", type=Path, default=EXP / "score")
    score(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
