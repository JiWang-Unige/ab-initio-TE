#!/usr/bin/env python3
"""Frozen Stage 1 whole-gap risk head.

The model consumes a ``(batch, 143, length)`` crop.  The first ten channels
are frozen P3/geometry channels, channels 10--14 are raw DNA (including PAD),
and channels 15--142 are the frozen P3 decoded latent.  ``GapHead`` masks the
non-active arm channels before the shared readout, so all three arms have the
same trainable structure and parameter count.
"""
from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import Tensor, nn
from torch.nn import functional as F


ARMS = (
    "G_GEOMETRY_LOGITS",
    "R_RAW_LOCAL",
    "H_P3_LATENT",
)
CHANNELS = 143
GEOMETRY_SCALARS = 7
LENGTH_STRATA = ("1", "2", "3-5", "6-20", "21-100", "101-512")


def _check_arm(arm: str) -> str:
    if arm not in ARMS:
        raise ValueError(f"unsupported Stage 1 arm: {arm}")
    return arm


def build_arm_input(features: Tensor, arm: str) -> Tensor:
    """Return an arm-specific copy of a ``(B,143,L)`` feature tensor."""
    _check_arm(arm)
    if features.ndim != 3 or features.size(1) != CHANNELS:
        raise ValueError(f"features must have shape (B,{CHANNELS},L)")
    arm_features = features.clone()
    if arm == ARMS[0]:
        arm_features[:, 10:, :] = 0
    elif arm == ARMS[1]:
        arm_features[:, 15:, :] = 0
    return arm_features


def apply_arm_input(features: Tensor, arm: str) -> Tensor:
    """Stable alias for :func:`build_arm_input`."""
    return build_arm_input(features, arm)


class _ResidualDepthwiseSeparableBlock(nn.Module):
    """One fixed-width residual depthwise-separable convolution block."""

    def __init__(self, dilation: int, width: int = 32) -> None:
        super().__init__()
        self.depthwise = nn.Conv1d(
            width,
            width,
            kernel_size=5,
            padding=2 * dilation,
            dilation=dilation,
            groups=width,
        )
        self.pointwise = nn.Conv1d(width, width, kernel_size=1)
        self.norm = nn.LayerNorm(width)
        self.activation = nn.GELU()

    def forward(self, x: Tensor) -> Tensor:
        residual = x
        y = self.activation(self.depthwise(x))
        y = self.pointwise(y)
        y = self.norm(y.transpose(1, 2)).transpose(1, 2)
        return self.activation(residual + y)


def masked_region_pool(hidden: Tensor, tags: Tensor, valid: Tensor) -> Tensor:
    """Pool hidden channels by left/gap/right tags with a validity mask.

    ``hidden`` is ``(B,32,L)``, ``tags`` is ``(B,3,L)``, and ``valid`` is
    ``(B,1,L)``.  Each region contributes a masked mean followed by a masked
    max, yielding 192 values per candidate.  An empty region contributes
    zeros; right padding therefore cannot enter either statistic.
    """
    pooled: list[Tensor] = []
    for region in range(3):
        mask = tags[:, region : region + 1, :] * valid
        count = mask.sum(dim=-1)
        mean = (hidden * mask).sum(dim=-1) / count.clamp_min(1)
        floor = torch.finfo(hidden.dtype).min
        maximum = hidden.masked_fill(mask <= 0, floor).amax(dim=-1)
        maximum = torch.where(count > 0, maximum, torch.zeros_like(maximum))
        pooled.extend((mean, maximum))
    return torch.cat(pooled, dim=1)


class GapHead(nn.Module):
    """Shared-architecture candidate risk head for one frozen information arm."""

    def __init__(self, arm: str = ARMS[2]) -> None:
        super().__init__()
        self.arm = _check_arm(arm)
        self.readout = nn.Conv1d(CHANNELS, 32, kernel_size=1)
        self.readout_activation = nn.GELU()
        self.readout_norm = nn.LayerNorm(32)
        self.blocks = nn.ModuleList(
            _ResidualDepthwiseSeparableBlock(dilation=dilation)
            for dilation in (1, 2, 4, 8)
        )
        self.mlp = nn.Sequential(
            nn.Linear(192 + GEOMETRY_SCALARS, 64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, 1),
        )

    def forward(self, features: Tensor, geometry: Tensor) -> Tensor:
        """Return one negative-fraction risk logit per candidate."""
        x = build_arm_input(features, self.arm)
        if geometry.ndim != 2 or geometry.size(1) != GEOMETRY_SCALARS:
            raise ValueError(f"geometry must have shape (B,{GEOMETRY_SCALARS})")
        valid = (x[:, 9:10, :] > 0).to(dtype=x.dtype)
        h = self.readout(x)
        h = self.readout_activation(h)
        h = self.readout_norm(h.transpose(1, 2)).transpose(1, 2)
        h = h * valid
        for block in self.blocks:
            h = block(h) * valid
        pooled = masked_region_pool(h, x[:, 4:7, :], valid)
        summary = torch.cat((pooled, geometry), dim=1)
        return self.mlp(summary).squeeze(-1)


def _stratum_name(value: object) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        if 0 <= value < len(LENGTH_STRATA):
            return LENGTH_STRATA[value]
    name = str(value)
    if name not in LENGTH_STRATA:
        raise ValueError(f"unsupported gap-length stratum: {value}")
    return name


def stratum_sample_weights(lengths: Tensor | Sequence[float], stratum_ids: Sequence[object]) -> Tensor:
    """Return mean-one weights with equal total weight in six strata.

    Within each stratum, weights are proportional to gap length.  All six
    frozen strata must be represented; a missing stratum or invalid length
    stops training instead of silently changing the optimization estimand.
    """
    if isinstance(lengths, Tensor):
        values = lengths.to(dtype=torch.get_default_dtype())
    else:
        values = torch.as_tensor(lengths, dtype=torch.get_default_dtype())
    if values.ndim != 1 or len(values) != len(stratum_ids) or len(values) == 0:
        raise ValueError("lengths and stratum_ids must be non-empty one-dimensional pairs")
    if not torch.isfinite(values).all() or (values <= 0).any():
        raise ValueError("gap lengths must be finite and positive")
    names = [_stratum_name(value) for value in stratum_ids]
    if set(names) != set(LENGTH_STRATA):
        raise ValueError("all six frozen length strata are required")
    weights = torch.zeros_like(values)
    for stratum in LENGTH_STRATA:
        mask = torch.tensor(
            [name == stratum for name in names],
            dtype=torch.bool,
            device=values.device,
        )
        stratum_lengths = values[mask]
        weights[mask] = stratum_lengths / stratum_lengths.sum()
    weights = weights * (len(values) / len(LENGTH_STRATA))
    if not torch.isfinite(weights).all() or not torch.isclose(
        weights.mean(), values.new_tensor(1.0), atol=1e-6, rtol=1e-6,
    ):
        raise ValueError("stratum weights failed mean-one normalization")
    return weights


def soft_target_bce(logits: Tensor, targets: Tensor, weights: Tensor) -> Tensor:
    """Compute weighted BCE-with-logits for soft negative-fraction targets."""
    if logits.shape != targets.shape or logits.shape != weights.shape:
        raise ValueError("logits, targets, and weights must have identical shapes")
    if not torch.isfinite(targets).all() or (targets < 0).any() or (targets > 1).any():
        raise ValueError("soft targets must be finite fractions in [0,1]")
    if not torch.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("sample weights must be finite and non-negative")
    if not torch.isclose(
        weights.mean(), weights.new_tensor(1.0), atol=1e-6, rtol=1e-6,
    ):
        raise ValueError("sample weights must be normalized to mean one")
    return F.binary_cross_entropy_with_logits(logits, targets, weight=weights, reduction="mean")

