#!/usr/bin/env python3
"""Fit frozen CAL calibration or apply it to one X0 split."""

from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


WINDOW_BP = 4096
KMER_BP = 6
CAL_SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
IOU_THRESHOLD = 0.8
BOUNDARY_TOLERANCES = (5, 25)
SHORT_BP = 80


def sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    out = np.empty_like(values)
    positive = values >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    out[~positive] = exp_values / (1.0 + exp_values)
    return out


def parse_data_specs(values: list[str]) -> list[tuple[str, Path]]:
    specs = []
    for value in values:
        species, path = value.split("=", 1)
        specs.append((species, Path(path)))
    return specs


def read_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle]


def sequence_tokens(sequence: str) -> list[str]:
    full_length = len(sequence) // KMER_BP * KMER_BP
    tokens = [
        sequence[start : start + KMER_BP]
        for start in range(0, full_length, KMER_BP)
    ]
    tokens.extend(sequence[full_length:])
    return [
        token if set(token) <= {"A", "C", "G", "T"} else "<unk>"
        for token in tokens
    ]


def project_token_margins(
    token_margins: np.ndarray, token_positions: list[int], bp_length: int
) -> np.ndarray:
    """Project native NTv2 k-mer TE-minus-background margins to bases."""
    projected = np.empty(bp_length, dtype=np.float32)
    full_chunks, tail_bp = divmod(bp_length, KMER_BP)
    expected = full_chunks + tail_bp
    if len(token_positions) != expected:
        raise ValueError(f"expected {expected} sequence tokens, observed {len(token_positions)}")
    for chunk, token_position in enumerate(token_positions[:full_chunks]):
        start = chunk * KMER_BP
        projected[start : start + KMER_BP] = token_margins[token_position]
    tail_start = full_chunks * KMER_BP
    for offset, token_position in enumerate(token_positions[full_chunks:]):
        projected[tail_start + offset] = token_margins[token_position]
    return projected


def load_final_model(
    model_dir: Path,
    tokenizer_dir: Path | None,
    cpu: bool,
    model_code_dir: Path | None = None,
):
    import torch
    from transformers import AutoTokenizer

    if model_code_dir is None:
        from transformers import AutoModelForTokenClassification

        model = AutoModelForTokenClassification.from_pretrained(
            str(model_dir), trust_remote_code=True, local_files_only=True
        )
    else:
        from transformers import AutoConfig
        from transformers.dynamic_module_utils import get_class_from_dynamic_module

        config = AutoConfig.from_pretrained(
            str(model_dir), trust_remote_code=True, local_files_only=True
        )
        state = torch.load(model_dir / "pytorch_model.bin", map_location="cpu")
        model_class = get_class_from_dynamic_module(
            config.auto_map["AutoModelForTokenClassification"],
            model_code_dir,
            local_files_only=True,
        )
        model = model_class._from_config(config)
        model.load_state_dict(state, strict=True)
    tokenizer = AutoTokenizer.from_pretrained(
        str(tokenizer_dir or model_dir), trust_remote_code=True, local_files_only=True
    )
    device = torch.device("cpu" if cpu or not torch.cuda.is_available() else "cuda")
    model.to(device)
    model.eval()
    return model, tokenizer, device


def infer_half_margins(
    model, tokenizer, device, sequences: list[str], batch_size: int
) -> list[np.ndarray]:
    import torch

    max_length = ((WINDOW_BP + 5) // 6 + 2 + 7) // 8 * 8
    results: list[np.ndarray] = []
    for offset in range(0, len(sequences), batch_size):
        batch = sequences[offset : offset + batch_size]
        encoded = tokenizer(
            [sequence_tokens(sequence) for sequence in batch],
            is_split_into_words=True,
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_special_tokens_mask=True,
            return_tensors="pt",
        )
        special_tokens_mask = encoded.pop("special_tokens_mask").detach().cpu().numpy()
        attention_mask = encoded["attention_mask"].detach().cpu().numpy()
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
        margins = (logits[:, :, 1] - logits[:, :, 0]).detach().cpu().numpy()
        for sequence, token_margin, attention, special in zip(
            batch, margins, attention_mask, special_tokens_mask
        ):
            token_positions = [
                index
                for index, (attended, is_special) in enumerate(zip(attention, special))
                if attended and not is_special
            ]
            results.append(
                project_token_margins(
                    token_margin, token_positions, len(sequence)
                )
            )
    return results


def decode_labels(label_text: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    labels = np.frombuffer(label_text.encode("ascii"), dtype="S1")
    truth = labels == b"1"
    callable_mask = labels != b"?"
    hard_negative = labels == b"H"
    return truth, callable_mask, hard_negative


def assemble_tiles(
    species: str, records: list[dict], margins: list[np.ndarray]
) -> list[dict]:
    grouped: dict[str, dict[int, tuple[dict, np.ndarray]]] = defaultdict(dict)
    for record, margin in zip(records, margins):
        grouped[str(record["tile_id"])][int(record["half"])] = (record, margin)

    tiles = []
    for tile_id in sorted(grouped):
        left, right = grouped[tile_id][0], grouped[tile_id][1]
        left_record, left_margin = left
        right_record, right_margin = right
        label_text = str(left_record["labels"]) + str(right_record["labels"])
        truth, callable_mask, hard_negative = decode_labels(label_text)
        tiles.append(
            {
                "species": species,
                "assembly": left_record["assembly"],
                "split": left_record["split"],
                "tile_id": tile_id,
                "chrom": left_record["chrom"],
                "start": int(left_record["start"]),
                "end": int(right_record["end"]),
                "margin": np.concatenate((left_margin, right_margin)),
                "truth": truth,
                "callable": callable_mask,
                "hard_negative": hard_negative,
            }
        )
    return tiles


def infer_inputs(
    model,
    tokenizer,
    device,
    data_specs: list[tuple[str, Path]],
    batch_size: int,
) -> dict[str, list[dict]]:
    by_species = {}
    for species, path in data_specs:
        records = read_jsonl(path)
        sequences = [str(record["sequence"]) for record in records]
        margins = infer_half_margins(model, tokenizer, device, sequences, batch_size)
        by_species[species] = assemble_tiles(species, records, margins)
    return by_species


def callable_arrays(
    tiles_by_species: dict[str, list[dict]],
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    result = {}
    for species, tiles in tiles_by_species.items():
        margins = np.concatenate([tile["margin"][tile["callable"]] for tile in tiles])
        truth = np.concatenate([tile["truth"][tile["callable"]] for tile in tiles])
        result[species] = (margins.astype(np.float64), truth.astype(np.float64))
    return result


def fit_platt(
    data: dict[str, tuple[np.ndarray, np.ndarray]]
) -> tuple[float, float, float]:
    """Unregularized nonnegative-slope Platt fit with equal species mass."""
    from scipy import optimize

    prevalence = float(np.mean([np.mean(truth) for _, truth in data.values()]))
    if not 0.0 < prevalence < 1.0:
        raise ValueError("CAL data must contain positive and negative callable bp")
    initial = np.asarray(
        [np.log(prevalence / (1.0 - prevalence)), 0.0], dtype=np.float64
    )

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        intercept, slope = parameters
        losses = []
        gradients = []
        for margins, truth in data.values():
            linear = intercept + slope * margins
            probability = sigmoid(linear)
            residual = probability - truth
            losses.append(np.mean(np.logaddexp(0.0, linear) - truth * linear))
            gradients.append(
                (float(np.mean(residual)), float(np.mean(residual * margins)))
            )
        return float(np.mean(losses)), np.mean(gradients, axis=0)

    result = optimize.minimize(
        objective,
        initial,
        jac=True,
        method="L-BFGS-B",
        bounds=((None, None), (0.0, None)),
        options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-8},
    )
    if not result.success:
        raise RuntimeError(f"CAL Platt fit failed: {result.message}")
    intercept, slope = map(float, result.x)
    return slope, intercept, float(result.fun)


def _choose_threshold_from_scores(
    thresholds: np.ndarray, minimum_f1: np.ndarray, macro_f1: np.ndarray
) -> int:
    best_minimum = float(np.max(minimum_f1))
    eligible = minimum_f1 >= best_minimum - 0.001
    best_macro = float(np.max(macro_f1[eligible]))
    eligible &= macro_f1 >= best_macro - 1e-12
    distance = np.abs(thresholds - 0.5)
    best_distance = float(np.min(distance[eligible]))
    eligible &= distance <= best_distance + 1e-12
    candidates = np.flatnonzero(eligible)
    return int(candidates[np.argmax(thresholds[candidates])])


def select_global_threshold(
    calibrated: dict[str, tuple[np.ndarray, np.ndarray]]
) -> dict[str, object]:
    unique = np.unique(np.concatenate([probability for probability, _ in calibrated.values()]))
    thresholds = np.concatenate(
        (
            [np.nextafter(unique[0], -np.inf)],
            unique,
            [np.nextafter(unique[-1], np.inf)],
        )
    )
    minimum_f1 = np.full(len(thresholds), np.inf, dtype=np.float64)
    macro_f1 = np.zeros(len(thresholds), dtype=np.float64)
    for species, (probability, truth) in calibrated.items():
        positions = np.searchsorted(unique, probability)
        total = np.bincount(positions, minlength=len(unique)).astype(np.float64)
        positives = np.bincount(
            positions, weights=truth, minlength=len(unique)
        ).astype(np.float64)
        true_positive = np.cumsum(positives[::-1])[::-1]
        predicted_positive = np.cumsum(total[::-1])[::-1]
        false_positive = predicted_positive - true_positive
        false_negative = float(np.sum(truth)) - true_positive
        denominator = 2.0 * true_positive + false_positive + false_negative
        f1_unique = np.divide(
            2.0 * true_positive,
            denominator,
            out=np.zeros_like(denominator),
            where=denominator > 0,
        )
        f1 = np.concatenate(([f1_unique[0]], f1_unique, [0.0]))
        minimum_f1 = np.minimum(minimum_f1, f1)
        macro_f1 += f1 / len(calibrated)

    selected = _choose_threshold_from_scores(thresholds, minimum_f1, macro_f1)
    threshold = float(thresholds[selected])
    selected_species_f1 = {}
    for species, (probability, truth) in calibrated.items():
        predicted = probability >= threshold
        true_positive = int(np.sum(predicted & (truth == 1)))
        false_positive = int(np.sum(predicted & (truth == 0)))
        false_negative = int(np.sum(~predicted & (truth == 1)))
        selected_species_f1[species] = _f1(
            true_positive, false_positive, false_negative
        )
    return {
        "threshold": threshold,
        "candidate_count": int(len(thresholds)),
        "minimum_species_f1": float(minimum_f1[selected]),
        "macro_species_f1": float(macro_f1[selected]),
        "species_f1": selected_species_f1,
    }


def runs_from_bool(mask: np.ndarray) -> list[tuple[int, int]]:
    padded = np.pad(mask.astype(np.int8), (1, 1))
    changes = np.diff(padded)
    return list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))


def match_segments(
    truth_segments: list[tuple[int, int]],
    predicted_segments: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    matches = []
    used_truth: set[int] = set()
    for predicted_index, (predicted_start, predicted_end) in enumerate(predicted_segments):
        best_iou, best_truth = 0.0, -1
        for truth_index, (truth_start, truth_end) in enumerate(truth_segments):
            if truth_index in used_truth:
                continue
            overlap = min(predicted_end, truth_end) - max(predicted_start, truth_start)
            if overlap <= 0:
                continue
            union = max(predicted_end, truth_end) - min(predicted_start, truth_start)
            iou = overlap / union
            if iou > best_iou:
                best_iou, best_truth = iou, truth_index
        if best_iou >= IOU_THRESHOLD:
            used_truth.add(best_truth)
            matches.append((predicted_index, best_truth))
    return matches


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(true_positive: int, false_positive: int, false_negative: int) -> float:
    denominator = 2 * true_positive + false_positive + false_negative
    return 2 * true_positive / denominator if denominator else 0.0


def evaluate_species_tiles(
    tiles: list[dict], slope: float, intercept: float, threshold: float
) -> dict[str, object]:
    counts = defaultdict(int)
    for tile in tiles:
        probability = sigmoid(slope * tile["margin"] + intercept)
        truth = tile["truth"].astype(bool)
        callable_mask = tile["callable"].astype(bool)
        hard_negative = tile["hard_negative"].astype(bool)
        predicted = (probability >= threshold) & callable_mask

        counts["callable_bp"] += int(np.sum(callable_mask))
        counts["positive_bp"] += int(np.sum(truth & callable_mask))
        counts["bp_tp"] += int(np.sum(predicted & truth & callable_mask))
        counts["bp_fp"] += int(np.sum(predicted & ~truth & callable_mask))
        counts["bp_fn"] += int(np.sum(~predicted & truth & callable_mask))
        counts["hardN_bp"] += int(np.sum(hard_negative))
        counts["hardN_fp_bp"] += int(np.sum(predicted & hard_negative))

        truth_segments = runs_from_bool(truth & callable_mask)
        predicted_segments = runs_from_bool(predicted)
        matches = match_segments(truth_segments, predicted_segments)
        counts["truth_segments"] += len(truth_segments)
        counts["predicted_segments"] += len(predicted_segments)
        counts["segment_tp"] += len(matches)
        counts["short_predicted_segments"] += sum(
            end - start < SHORT_BP for start, end in predicted_segments
        )
        for tolerance in BOUNDARY_TOLERANCES:
            counts[f"boundary_tp_{tolerance}"] += sum(
                abs(predicted_segments[predicted_index][0] - truth_segments[truth_index][0])
                <= tolerance
                and abs(predicted_segments[predicted_index][1] - truth_segments[truth_index][1])
                <= tolerance
                for predicted_index, truth_index in matches
            )

        for truth_start, truth_end in truth_segments:
            overlaps = sum(
                min(predicted_end, truth_end) > max(predicted_start, truth_start)
                for predicted_start, predicted_end in predicted_segments
            )
            counts["fragment_overlaps"] += overlaps
            counts["split_truth"] += overlaps > 1
            counts["missed_truth"] += overlaps == 0

    segment_fp = counts["predicted_segments"] - counts["segment_tp"]
    segment_fn = counts["truth_segments"] - counts["segment_tp"]
    result = {
        "tiles": len(tiles),
        "callable_bp": counts["callable_bp"],
        "positive_bp": counts["positive_bp"],
        "bp_tp": counts["bp_tp"],
        "bp_fp": counts["bp_fp"],
        "bp_fn": counts["bp_fn"],
        "bp_precision": _ratio(counts["bp_tp"], counts["bp_tp"] + counts["bp_fp"]),
        "bp_recall": _ratio(counts["bp_tp"], counts["bp_tp"] + counts["bp_fn"]),
        "bp_f1": _f1(counts["bp_tp"], counts["bp_fp"], counts["bp_fn"]),
        "truth_segments": counts["truth_segments"],
        "predicted_segments": counts["predicted_segments"],
        "segment_f1_iou_0_8": _f1(counts["segment_tp"], segment_fp, segment_fn),
        "short_prediction_rate": _ratio(
            counts["short_predicted_segments"], counts["predicted_segments"]
        ),
        "fragments_per_truth": _ratio(
            counts["fragment_overlaps"], counts["truth_segments"]
        ),
        "split_rate": _ratio(counts["split_truth"], counts["truth_segments"]),
        "missed_rate": _ratio(counts["missed_truth"], counts["truth_segments"]),
        "hardN_bp": counts["hardN_bp"],
        "hardN_fp_bp": counts["hardN_fp_bp"],
        "hardN_fp_rate": _ratio(counts["hardN_fp_bp"], counts["hardN_bp"]),
    }
    for tolerance in BOUNDARY_TOLERANCES:
        boundary_tp = counts[f"boundary_tp_{tolerance}"]
        result[f"boundary_f1_{tolerance}bp"] = _f1(
            boundary_tp,
            counts["predicted_segments"] - boundary_tp,
            counts["truth_segments"] - boundary_tp,
        )
    return result


def evaluate(
    tiles_by_species: dict[str, list[dict]],
    slope: float,
    intercept: float,
    threshold: float,
) -> tuple[dict[str, dict], dict[str, float]]:
    per_species = {
        species: evaluate_species_tiles(tiles, slope, intercept, threshold)
        for species, tiles in sorted(tiles_by_species.items())
    }
    metric_names = (
        "bp_precision",
        "bp_recall",
        "bp_f1",
        "segment_f1_iou_0_8",
        "boundary_f1_5bp",
        "boundary_f1_25bp",
        "short_prediction_rate",
        "fragments_per_truth",
        "split_rate",
        "missed_rate",
        "hardN_fp_rate",
    )
    summary = {
        f"macro_{name}": float(np.mean([row[name] for row in per_species.values()]))
        for name in metric_names
    }
    summary["minimum_species_bp_f1"] = min(row["bp_f1"] for row in per_species.values())
    return per_species, summary


def require_cal_split(tiles_by_species: dict[str, list[dict]]) -> None:
    observed = {
        tile["split"] for tiles in tiles_by_species.values() for tile in tiles
    }
    if observed != {"CAL"}:
        raise ValueError(f"fit accepts CAL only, observed {sorted(observed)}")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_fit(args) -> dict:
    data_specs = parse_data_specs(args.data)
    observed_species = {species for species, _ in data_specs}
    if len(data_specs) != len(CAL_SPECIES) or observed_species != set(CAL_SPECIES):
        raise ValueError(f"fit requires the six CAL species, observed {sorted(observed_species)}")
    model, tokenizer, device = load_final_model(
        args.model_dir, args.tokenizer_dir, args.cpu, args.model_code_dir
    )
    tiles_by_species = infer_inputs(
        model, tokenizer, device, data_specs, args.batch_size
    )
    require_cal_split(tiles_by_species)
    callable_data = callable_arrays(tiles_by_species)
    slope, intercept, loss = fit_platt(callable_data)
    calibrated = {
        species: (sigmoid(slope * margins + intercept), truth)
        for species, (margins, truth) in callable_data.items()
    }
    selection = select_global_threshold(calibrated)
    calibration = {
        "protocol": "CROSS-SPECIES-L1-X0-PLATT-V1",
        "seed": args.seed,
        "model_dir": str(args.model_dir.resolve()),
        "tokenizer_dir": str((args.tokenizer_dir or args.model_dir).resolve()),
        "model_code_dir": (
            str(args.model_code_dir.resolve()) if args.model_code_dir else None
        ),
        "fit_split": "CAL",
        "species": sorted(callable_data),
        "platt_slope": slope,
        "platt_intercept": intercept,
        "calibration_loss": loss,
        "threshold": selection["threshold"],
        "threshold_selection": selection,
    }
    write_json(args.calibration_json, calibration)
    per_species, summary = evaluate(
        tiles_by_species, slope, intercept, selection["threshold"]
    )
    output = {
        "mode": "fit-cal-only",
        "seed": args.seed,
        "model_dir": str(args.model_dir),
        "calibration_json": str(args.calibration_json),
        "per_species": per_species,
        "summary": summary,
    }
    write_json(args.metrics_json, output)
    return output


def run_apply(args) -> dict:
    calibration = json.loads(args.calibration_json.read_text())
    if calibration["model_dir"] != str(args.model_dir.resolve()):
        raise ValueError("calibration artifact belongs to a different final_model")
    if calibration["tokenizer_dir"] != str(
        (args.tokenizer_dir or args.model_dir).resolve()
    ):
        raise ValueError("calibration artifact belongs to a different tokenizer")
    expected_model_code_dir = (
        str(args.model_code_dir.resolve()) if args.model_code_dir else None
    )
    if calibration["model_code_dir"] != expected_model_code_dir:
        raise ValueError("calibration artifact belongs to a different model code directory")
    data_specs = parse_data_specs(args.data)
    model, tokenizer, device = load_final_model(
        args.model_dir, args.tokenizer_dir, args.cpu, args.model_code_dir
    )
    tiles_by_species = infer_inputs(
        model, tokenizer, device, data_specs, args.batch_size
    )
    per_species, summary = evaluate(
        tiles_by_species,
        float(calibration["platt_slope"]),
        float(calibration["platt_intercept"]),
        float(calibration["threshold"]),
    )
    observed_splits = sorted(
        {tile["split"] for tiles in tiles_by_species.values() for tile in tiles}
    )
    output = {
        "mode": "apply-only",
        "seed": calibration["seed"],
        "model_dir": str(args.model_dir),
        "calibration_json": str(args.calibration_json),
        "observed_splits": observed_splits,
        "per_species": per_species,
        "summary": summary,
    }
    write_json(args.metrics_json, output)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    fit = subparsers.add_parser("fit-cal")
    fit.add_argument("--model-dir", type=Path, required=True)
    fit.add_argument("--tokenizer-dir", type=Path)
    fit.add_argument("--model-code-dir", type=Path)
    fit.add_argument("--data", action="append", required=True, metavar="SPECIES=JSONL.GZ")
    fit.add_argument("--seed", type=int, required=True)
    fit.add_argument("--calibration-json", type=Path, required=True)
    fit.add_argument("--metrics-json", type=Path, required=True)
    fit.add_argument("--batch-size", type=int, default=12)
    fit.add_argument("--cpu", action="store_true")
    fit.set_defaults(func=run_fit)

    apply = subparsers.add_parser("apply-only")
    apply.add_argument("--model-dir", type=Path, required=True)
    apply.add_argument("--tokenizer-dir", type=Path)
    apply.add_argument("--model-code-dir", type=Path)
    apply.add_argument("--data", action="append", required=True, metavar="SPECIES=JSONL.GZ")
    apply.add_argument("--calibration-json", type=Path, required=True)
    apply.add_argument("--metrics-json", type=Path, required=True)
    apply.add_argument("--batch-size", type=int, default=12)
    apply.add_argument("--cpu", action="store_true")
    apply.set_defaults(func=run_apply)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = args.func(args)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
