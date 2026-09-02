#!/usr/bin/env python3
"""Frozen Stage 1 statistical primitives.

The functions in this module operate on candidate-level arrays.  A candidate
has a positive-bp mass, a negative-bp mass, and (for deployment) an optional
unknown-bp mass.  Scores are always interpreted in the frozen Stage 1
direction: larger action scores mean more evidence for filling the complete
gap, while larger calibrated risk means more negative fraction.

No evaluator, model, or file-format code belongs here.  Keeping these
operations pure makes the tie handling and the resampling unit explicit to
the scoring runner.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np


LENGTH_STRATA = ("1", "2", "3-5", "6-20", "21-100", "101-512")
DEFAULT_BLOCK_SIZE = 1_000_000
DEFAULT_BOOTSTRAP_REPLICATES = 1_000
DEFAULT_BOOTSTRAP_SEED = 20260902


def _arrays(*values: Sequence[float], allow_empty: bool = False) -> tuple[np.ndarray, ...]:
    arrays = tuple(np.asarray(value, dtype=np.float64) for value in values)
    if not arrays:
        return arrays
    shape = arrays[0].shape
    if any(array.ndim != 1 or array.shape != shape for array in arrays):
        raise ValueError("metric inputs must be one-dimensional arrays of equal length")
    if not allow_empty and shape[0] == 0:
        raise ValueError("metric inputs must not be empty")
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("metric inputs must be finite")
    return arrays


def _nonnegative(*values: Sequence[float], allow_empty: bool = False) -> tuple[np.ndarray, ...]:
    arrays = _arrays(*values, allow_empty=allow_empty)
    if any(np.any(array < 0) for array in arrays):
        raise ValueError("metric masses must be non-negative")
    return arrays


def _risk_arrays(
    p_neg: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    p, positive, negative = _nonnegative(p_neg, positive_bp, negative_bp)
    if np.any(p > 1):
        raise ValueError("predicted negative fractions must be in [0,1]")
    length = positive + negative
    if np.any(length <= 0):
        raise ValueError("each candidate must have positive known bp mass")
    return p, positive, negative, length


def _score_groups(scores: np.ndarray) -> list[np.ndarray]:
    """Return exact-score groups in descending score order."""
    # ``np.unique`` groups every exact floating-point tie before any row-wise
    # operation.  This is the part that prevents arbitrary row-order tie
    # breaking in all weighted ranking metrics.
    unique = np.unique(scores)
    return [np.flatnonzero(scores == score) for score in unique[::-1]]


def weighted_action_ap(
    action_scores: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> float:
    """Return tie-grouped bp-weighted average precision.

    Every candidate contributes ``positive_bp`` positive mass and
    ``negative_bp`` negative mass.  A full exact-score group is admitted at
    once; precision is measured after the whole group and recall increment is
    the group's positive mass.  This is the weighted analogue of the usual
    stepwise average precision and is invariant to row order within ties.
    """
    scores = np.asarray(action_scores, dtype=np.float64)
    positive, negative = _nonnegative(positive_bp, negative_bp)
    if scores.ndim != 1 or scores.shape != positive.shape:
        raise ValueError("metric inputs must be one-dimensional arrays of equal length")
    if not np.all(np.isfinite(scores)):
        raise ValueError("metric inputs must be finite")
    total_positive = float(positive.sum())
    if total_positive <= 0:
        raise ValueError("weighted AP requires positive bp mass")
    cumulative_positive = 0.0
    cumulative_negative = 0.0
    ap = 0.0
    for indices in _score_groups(scores):
        group_positive = float(positive[indices].sum())
        group_negative = float(negative[indices].sum())
        cumulative_positive += group_positive
        cumulative_negative += group_negative
        denominator = cumulative_positive + cumulative_negative
        if denominator > 0 and group_positive > 0:
            ap += (group_positive / total_positive) * (cumulative_positive / denominator)
    return float(ap)


def weighted_action_auroc(
    action_scores: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> float:
    """Return pairwise bp-weighted AUROC with exact ties worth one half."""
    scores = np.asarray(action_scores, dtype=np.float64)
    positive, negative = _nonnegative(positive_bp, negative_bp)
    if scores.ndim != 1 or scores.shape != positive.shape:
        raise ValueError("metric inputs must be one-dimensional arrays of equal length")
    if not np.all(np.isfinite(scores)):
        raise ValueError("metric inputs must be finite")
    total_positive = float(positive.sum())
    total_negative = float(negative.sum())
    if total_positive <= 0 or total_negative <= 0:
        raise ValueError("weighted AUROC requires both positive and negative bp mass")
    lower_scored_negative = total_negative
    concordant = 0.0
    for indices in _score_groups(scores):
        group_positive = float(positive[indices].sum())
        group_negative = float(negative[indices].sum())
        lower_scored_negative -= group_negative
        concordant += group_positive * (lower_scored_negative + 0.5 * group_negative)
    return float(concordant / (total_positive * total_negative))


def weighted_action_metrics(
    action_scores: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> dict[str, float]:
    """Return weighted AP/AUROC, prevalence, and normalized AP."""
    scores = np.asarray(action_scores, dtype=np.float64)
    positive, negative = _nonnegative(positive_bp, negative_bp)
    if scores.ndim != 1 or scores.shape != positive.shape or not np.all(np.isfinite(scores)):
        raise ValueError("metric inputs must be one-dimensional finite arrays of equal length")
    total_positive = float(positive.sum())
    total_negative = float(negative.sum())
    total = total_positive + total_negative
    if total <= 0 or total_positive <= 0 or total_negative <= 0:
        raise ValueError("weighted action metrics require positive and negative bp mass")
    ap = weighted_action_ap(scores, positive, negative)
    prevalence = total_positive / total
    return {
        "average_precision": ap,
        "ap": ap,
        "auroc": weighted_action_auroc(scores, positive, negative),
        "positive_bp_prevalence": prevalence,
        "prevalence": prevalence,
        "normalized_average_precision": ap / prevalence,
        "normalized_ap": ap / prevalence,
    }


weighted_action_average_precision = weighted_action_ap


def pseudo_base_brier(
    p_neg: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> float:
    """Return the literal pseudo-base Bernoulli Brier score."""
    p, positive, negative, length = _risk_arrays(p_neg, positive_bp, negative_bp)
    numerator = negative * (1.0 - p) ** 2 + positive * p**2
    return float(numerator.sum() / length.sum())


def pseudo_base_log_loss(
    p_neg: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> float:
    """Return pseudo-base log loss for the predicted negative fraction.

    Endpoint probabilities are deliberately not clipped: a zero probability
    for observed positive mass (or one for observed negative mass) is an
    infinite log loss, as required by the calibrated-risk definition.
    """
    p, positive, negative, length = _risk_arrays(p_neg, positive_bp, negative_bp)
    with np.errstate(divide="ignore", invalid="ignore"):
        negative_term = np.where(negative > 0, -negative * np.log(p), 0.0)
        positive_term = np.where(positive > 0, -positive * np.log1p(-p), 0.0)
        numerator = negative_term + positive_term
    return float(numerator.sum() / length.sum())


def natural_candidate_brier(
    p_neg: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> float:
    """Return the unweighted candidate mean of ``(p-r)^2``."""
    p, positive, negative, _ = _risk_arrays(p_neg, positive_bp, negative_bp)
    target = negative / (positive + negative)
    return float(np.mean((p - target) ** 2))


def _stratum_names(strata: Sequence[Any], count: int) -> list[str]:
    if len(strata) != count:
        raise ValueError("stratum labels must match candidate count")
    names: list[str] = []
    for value in strata:
        if isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_)):
            index = int(value)
            if not 0 <= index < len(LENGTH_STRATA):
                raise ValueError(f"unsupported length stratum: {value}")
            names.append(LENGTH_STRATA[index])
        else:
            name = str(value)
            if name not in LENGTH_STRATA:
                raise ValueError(f"unsupported length stratum: {value}")
            names.append(name)
    return names


def six_stratum_macro_brier(
    p_neg: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
    strata: Sequence[Any],
) -> float:
    """Return the unweighted mean of six within-stratum pseudo-base Briers."""
    p, positive, negative, _ = _risk_arrays(p_neg, positive_bp, negative_bp)
    names = _stratum_names(strata, len(p))
    if set(names) != set(LENGTH_STRATA):
        raise ValueError("all six frozen length strata are required")
    scores = []
    for stratum in LENGTH_STRATA:
        mask = np.asarray([name == stratum for name in names], dtype=bool)
        scores.append(pseudo_base_brier(p[mask], positive[mask], negative[mask]))
    return float(np.mean(scores))


def calibrated_risk_metrics(
    p_neg: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
    strata: Sequence[Any],
) -> dict[str, float]:
    """Return all frozen calibrated-risk metrics for one candidate set."""
    values = {
        "pseudo_base_brier": pseudo_base_brier(p_neg, positive_bp, negative_bp),
        "pseudo_base_log_loss": pseudo_base_log_loss(p_neg, positive_bp, negative_bp),
        "natural_candidate_brier": natural_candidate_brier(p_neg, positive_bp, negative_bp),
        "six_stratum_macro_brier": six_stratum_macro_brier(p_neg, positive_bp, negative_bp, strata),
    }
    values["stratum_macro_brier"] = values["six_stratum_macro_brier"]
    return values


def _sigmoid(values: np.ndarray) -> np.ndarray:
    output = np.empty_like(values, dtype=np.float64)
    positive = values >= 0
    output[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    output[~positive] = exp_values / (1.0 + exp_values)
    return output


def fit_monotone_platt(
    raw_risk_logits: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> dict[str, Any]:
    """Fit the frozen non-decreasing Platt map with length-weighted soft BCE.

    ``raw_risk_logits`` must already be the mean of the three raw seed risk
    logits.  A failed SciPy solve is returned with ``success=False`` and its
    message; callers must not silently use such a fit.
    """
    z = np.asarray(raw_risk_logits, dtype=np.float64)
    positive, negative = _nonnegative(positive_bp, negative_bp)
    if z.ndim != 1 or z.shape != positive.shape or not np.all(np.isfinite(z)):
        raise ValueError("raw risk logits and masses must be finite one-dimensional arrays of equal length")
    length = positive + negative
    if np.any(length <= 0):
        raise ValueError("each calibration candidate must have positive known bp mass")
    target = negative / length
    try:
        from scipy import optimize
    except ModuleNotFoundError as error:
        return {
            "success": False,
            "status": "SCIPY_UNAVAILABLE",
            "message": str(error),
            "intercept": float("nan"),
            "slope": float("nan"),
            "objective": float("nan"),
        }

    total_length = float(length.sum())
    prevalence = float(negative.sum() / total_length)
    if 0.0 < prevalence < 1.0:
        intercept = float(np.log(prevalence / (1.0 - prevalence)))
    else:
        intercept = 0.0
    initial = np.asarray([intercept, 0.0], dtype=np.float64)

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        linear = parameters[0] + parameters[1] * z
        probability = _sigmoid(linear)
        # softplus(linear) - target*linear is stable for both probability
        # endpoints and has exactly the requested L-weighted BCE objective.
        losses = np.logaddexp(0.0, linear) - target * linear
        value = float(np.sum(length * losses))
        residual = length * (probability - target)
        gradient = np.asarray([residual.sum(), np.dot(residual, z)], dtype=np.float64)
        return value, gradient

    result = optimize.minimize(
        lambda parameters: objective(parameters)[0],
        initial,
        jac=lambda parameters: objective(parameters)[1],
        method="L-BFGS-B",
        bounds=((None, None), (0.0, None)),
        options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-8},
    )
    return {
        "success": bool(result.success),
        "status": int(result.status),
        "message": str(result.message),
        "intercept": float(result.x[0]),
        "slope": float(result.x[1]),
        "objective": float(result.fun),
        "solver": "scipy.optimize.minimize:L-BFGS-B",
        "iterations": int(result.nit),
    }


def apply_monotone_platt(raw_risk_logits: Sequence[float], fit: dict[str, Any]) -> np.ndarray:
    """Apply a successful monotone Platt fit to raw risk logits."""
    if not fit.get("success", False):
        raise ValueError("cannot apply an unsuccessful Platt fit")
    z = np.asarray(raw_risk_logits, dtype=np.float64)
    if z.ndim != 1 or not np.all(np.isfinite(z)):
        raise ValueError("raw risk logits must be a finite one-dimensional array")
    slope = float(fit["slope"])
    intercept = float(fit["intercept"])
    if not np.isfinite(intercept) or not np.isfinite(slope) or slope < 0:
        raise ValueError("Platt fit parameters are invalid")
    return _sigmoid(intercept + slope * z)


def equal_bp_mass_ece(
    p_neg: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
) -> dict[str, Any]:
    """Return frozen equal-bp-mass ten-bin ECE and calibration-in-the-large.

    Candidates are sorted by exact predicted risk.  Equal-risk groups are
    aggregated before binning, and both candidates and groups that cross a bin
    boundary are split proportionally in bp mass.  Thus neither candidate row
    order nor tie order can affect a bin statistic.
    """
    p, positive, negative, length = _risk_arrays(p_neg, positive_bp, negative_bp)
    total = float(length.sum())
    bin_mass = np.zeros(10, dtype=np.float64)
    bin_observed_negative = np.zeros(10, dtype=np.float64)
    bin_predicted_negative = np.zeros(10, dtype=np.float64)
    target_mass = total / 10.0
    current_bin = 0
    for indices in _score_groups(p):
        group_mass = float(length[indices].sum())
        group_negative = float(negative[indices].sum())
        group_score = float(p[indices[0]])
        remaining = group_mass
        while remaining > 0:
            if current_bin >= 9:
                take = remaining
            else:
                capacity = target_mass - bin_mass[current_bin]
                if capacity <= 0:
                    current_bin += 1
                    continue
                take = min(remaining, capacity)
            fraction = take / group_mass
            bin_mass[current_bin] += take
            bin_observed_negative[current_bin] += group_negative * fraction
            bin_predicted_negative[current_bin] += group_score * take
            remaining -= take
            if current_bin < 9 and bin_mass[current_bin] >= target_mass:
                current_bin += 1
    observed_rate = bin_observed_negative / bin_mass
    predicted_rate = bin_predicted_negative / bin_mass
    ece = float(np.sum((bin_mass / total) * np.abs(predicted_rate - observed_rate)))
    citl = float((np.sum(bin_predicted_negative) - np.sum(negative)) / total)
    return {
        "ece": ece,
        "equal_bp_mass_ece": ece,
        "citl": citl,
        "citl_abs": abs(citl),
        "calibration_in_the_large": abs(citl),
        "bin_mass": bin_mass,
        "bin_observed_negative_mass": bin_observed_negative,
        "bin_predicted_negative_mass": bin_predicted_negative,
        "bin_observed_negative_rate": observed_rate,
        "bin_predicted_negative_rate": predicted_rate,
        "total_bp": total,
        "bin_count": 10,
    }


def frozen_budget_frontier(
    p_neg: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
    unknown_bp: Sequence[float],
    callable_bp: float,
    budget: float = 1e-5,
) -> dict[str, Any]:
    """Select the largest complete calibrated-risk tie group within budget."""
    p, positive, negative, unknown = _nonnegative(p_neg, positive_bp, negative_bp, unknown_bp)
    if np.any(p > 1):
        raise ValueError("calibrated negative fractions must be in [0,1]")
    if not np.isfinite(callable_bp) or callable_bp <= 0:
        raise ValueError("callable bp denominator must be positive")
    if not np.isfinite(budget) or budget < 0:
        raise ValueError("budget must be finite and non-negative")
    selected = np.zeros(len(p), dtype=bool)
    threshold: float | None = None
    for score in np.unique(p):
        indices = np.flatnonzero(p == score)
        selected[indices] = True
        worst_case_negative = float(negative[selected].sum() + unknown[selected].sum())
        if worst_case_negative / float(callable_bp) <= budget:
            threshold = float(score)
        else:
            selected[indices] = False
            # All later groups add non-negative worst-case negative mass.
            break
    worst_case_negative = float(negative[selected].sum() + unknown[selected].sum())
    return {
        "selected_mask": selected,
        "threshold": threshold,
        "selected_candidates": int(selected.sum()),
        "selected_positive_bp": float(positive[selected].sum()),
        "selected_known_negative_bp": float(negative[selected].sum()),
        "selected_unknown_bp": float(unknown[selected].sum()),
        "worst_case_negative_bp": worst_case_negative,
        "callable_bp": float(callable_bp),
        "worst_case_negative_rate": worst_case_negative / float(callable_bp),
        "budget": float(budget),
    }


def utility_gate(
    novel_positive_bp: float,
    baseline_positive_bp: float,
    novel_split_edges: float,
    baseline_split_edges: float,
) -> dict[str, Any]:
    """Apply the registered OR utility gate to novel and baseline endpoints."""
    values = np.asarray(
        [novel_positive_bp, baseline_positive_bp, novel_split_edges, baseline_split_edges],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("utility endpoints must be finite and non-negative")
    positive_gain = float(novel_positive_bp - baseline_positive_bp)
    edge_gain = float(novel_split_edges - baseline_split_edges)
    positive_relative = positive_gain / baseline_positive_bp if baseline_positive_bp else (float("inf") if positive_gain > 0 else 0.0)
    edge_relative = edge_gain / baseline_split_edges if baseline_split_edges else (float("inf") if edge_gain > 0 else 0.0)
    positive_pass = positive_gain >= 1000.0 and positive_gain >= 0.10 * baseline_positive_bp
    edge_pass = edge_gain >= 100.0 and edge_gain >= 0.10 * baseline_split_edges
    return {
        "positive_bp_gain": positive_gain,
        "positive_bp_relative_gain": positive_relative,
        "positive_bp_pass": bool(positive_pass),
        "split_edge_gain": edge_gain,
        "split_edge_relative_gain": edge_relative,
        "split_edge_pass": bool(edge_pass),
        "passed": bool(positive_pass or edge_pass),
        "registered_or": True,
    }


def absolute_mb_block_id(
    seqid: str,
    midpoint: float,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> str:
    """Return the absolute ``seqid:block_index`` for a genomic midpoint."""
    if not isinstance(seqid, str) or not seqid:
        raise ValueError("sequence identifier must be non-empty")
    if not np.isfinite(midpoint) or midpoint < 0:
        raise ValueError("genomic midpoint must be finite and non-negative")
    if not isinstance(block_size, (int, np.integer)) or block_size <= 0:
        raise ValueError("block size must be a positive integer")
    return f"{seqid}:{int(np.floor(midpoint)) // int(block_size)}"


def absolute_mb_block_ids(
    seqids: Sequence[str],
    midpoints: Sequence[float],
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> np.ndarray:
    """Return absolute 1-Mb block IDs assigned by candidate midpoint."""
    if len(seqids) != len(midpoints):
        raise ValueError("sequence identifiers and midpoints must have equal length")
    return np.asarray(
        [absolute_mb_block_id(seqid, midpoint, block_size) for seqid, midpoint in zip(seqids, midpoints)],
        dtype=object,
    )


def bootstrap_action_ap_difference(
    action_scores_a: Sequence[float],
    action_scores_b: Sequence[float],
    positive_bp: Sequence[float],
    negative_bp: Sequence[float],
    candidate_block_ids: Sequence[str],
    evaluated_block_universe: Sequence[str],
    n_replicates: int = DEFAULT_BOOTSTRAP_REPLICATES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Return paired 1-Mb block-bootstrap AP difference and linear interval.

    ``evaluated_block_universe`` is explicit and may contain bins with zero
    candidates.  Such bins remain bootstrap units and therefore affect the
    sampling distribution even though they contribute no candidate mass.
    """
    scores_a, scores_b, positive, negative = _arrays(
        action_scores_a, action_scores_b, positive_bp, negative_bp,
    )
    if not np.all(np.isfinite(scores_a)) or not np.all(np.isfinite(scores_b)):
        raise ValueError("action scores must be finite")
    if np.any(positive < 0) or np.any(negative < 0):
        raise ValueError("metric masses must be non-negative")
    if not isinstance(n_replicates, (int, np.integer)) or n_replicates <= 0:
        raise ValueError("bootstrap replicate count must be a positive integer")
    candidate_ids = [str(value) for value in candidate_block_ids]
    universe = [str(value) for value in evaluated_block_universe]
    if len(candidate_ids) != len(scores_a):
        raise ValueError("candidate block IDs must match candidate count")
    if len(set(universe)) != len(universe):
        raise ValueError("evaluated block universe must contain unique block IDs")
    if not universe:
        raise ValueError("evaluated block universe must not be empty")
    lookup = {block_id: index for index, block_id in enumerate(universe)}
    if any(block_id not in lookup for block_id in candidate_ids):
        raise ValueError("candidate block IDs must belong to the evaluated block universe")
    row_block_indices = np.asarray([lookup[block_id] for block_id in candidate_ids], dtype=np.int64)
    rng = np.random.default_rng(seed)
    differences = np.full(int(n_replicates), np.nan, dtype=np.float64)
    block_count = len(universe)
    for replicate in range(int(n_replicates)):
        sampled = rng.integers(0, block_count, size=block_count)
        multiplicity = np.bincount(sampled, minlength=block_count)
        row_weights = multiplicity[row_block_indices].astype(np.float64)
        included = row_weights > 0
        if not np.any(included):
            continue
        replicate_positive = positive[included] * row_weights[included]
        if replicate_positive.sum() <= 0:
            continue
        replicate_negative = negative[included] * row_weights[included]
        differences[replicate] = weighted_action_ap(
            scores_a[included], replicate_positive, replicate_negative,
        ) - weighted_action_ap(
            scores_b[included], replicate_positive, replicate_negative,
        )
    observed_difference = weighted_action_ap(scores_a, positive, negative) - weighted_action_ap(scores_b, positive, negative)
    valid = differences[np.isfinite(differences)]
    if len(valid):
        lower, upper = np.percentile(valid, [2.5, 97.5], method="linear")
        mean = float(np.mean(valid))
    else:
        lower = upper = mean = float("nan")
    return {
        "observed_difference": float(observed_difference),
        "mean_difference": mean,
        "lower_95": float(lower),
        "upper_95": float(upper),
        "replicates": differences,
        "n_replicates": int(n_replicates),
        "valid_replicates": int(len(valid)),
        "evaluated_block_universe": universe,
        "evaluated_block_count": len(universe),
        "zero_candidate_block_count": int(len(universe) - len(set(candidate_ids))),
        "seed": int(seed),
        "percentile_method": "linear",
    }
