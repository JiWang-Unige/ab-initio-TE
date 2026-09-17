"""Load the relative-path model bundle used by the portable CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CAL_SPECIES = ("human", "mouse", "chicken", "zebrafish", "pig", "c_elegans")
PROTOCOL = "CROSS-SPECIES-L1-X0-PLATT-V1"
WINDOW_BP = 4096
KMER_BP = 6


def _read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _relative_path(root: Path, value: str, field: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError(f"bundle manifest field {field} must be relative: {value}")
    if not value or value in {".", ".."}:
        raise ValueError(f"bundle manifest field {field} is empty or unsafe")
    return root / candidate


@dataclass(frozen=True)
class Bundle:
    """Resolved paths and frozen calibration for one portable model bundle."""

    root: Path
    manifest: dict[str, Any]
    calibration: dict[str, Any]
    model_dir: Path
    tokenizer_dir: Path
    model_code_dir: Path
    calibration_path: Path

    @classmethod
    def load(cls, root: Path) -> "Bundle":
        root = Path(root).expanduser()
        manifest_path = root / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"bundle manifest not found: {manifest_path}")
        manifest = _read_json(manifest_path)
        if manifest.get("schema") != "portable-d-bundle/v1":
            raise ValueError("unsupported portable bundle schema")
        required = ("model_dir", "tokenizer_dir", "model_code_dir", "calibration_json")
        missing = [key for key in required if key not in manifest]
        if missing:
            raise ValueError(f"bundle manifest missing fields: {', '.join(missing)}")

        model_dir = _relative_path(root, str(manifest["model_dir"]), "model_dir")
        tokenizer_dir = _relative_path(root, str(manifest["tokenizer_dir"]), "tokenizer_dir")
        model_code_dir = _relative_path(root, str(manifest["model_code_dir"]), "model_code_dir")
        calibration_path = _relative_path(
            root, str(manifest["calibration_json"]), "calibration_json"
        )
        calibration = _read_json(calibration_path)
        bundle = cls(
            root=root,
            manifest=manifest,
            calibration=calibration,
            model_dir=model_dir,
            tokenizer_dir=tokenizer_dir,
            model_code_dir=model_code_dir,
            calibration_path=calibration_path,
        )
        bundle.validate()
        return bundle

    def validate(self) -> None:
        model_id = self.manifest.get("model_id")
        if not model_id or self.calibration.get("model_id") != model_id:
            raise ValueError("model identity differs between manifest and calibration")
        if self.manifest.get("window_bp") != WINDOW_BP:
            raise ValueError("portable D bundle requires 4096-bp windows")
        if self.manifest.get("kmer_bp") != KMER_BP:
            raise ValueError("portable D bundle requires six-base tokens")
        if self.calibration.get("calibration_scope") != "six-species-shared":
            raise ValueError("requires the six-species-shared calibration")
        if self.calibration.get("fit_split") != "CAL":
            raise ValueError("portable inference requires calibration fit on CAL")
        if tuple(self.calibration.get("species", ())) != CAL_SPECIES:
            raise ValueError("calibration species do not match the frozen six-species set")
        # The verified source JSON carries the explicit calibration protocol.
        # The separate historical `protocol` field is retained as provenance,
        # but is not used to reinterpret a calibration artifact.
        protocol = self.calibration.get("calibration_protocol")
        if protocol != PROTOCOL:
            raise ValueError(f"unsupported calibration protocol: {protocol!r}")
        for key in ("platt_slope", "platt_intercept", "threshold"):
            value = self.calibration.get(key)
            if not isinstance(value, (int, float)):
                raise ValueError(f"missing numeric calibration value: {key}")
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError(f"non-finite calibration value: {key}")
        selection = self.calibration.get("threshold_selection", {})
        if float(selection.get("threshold")) != float(self.calibration["threshold"]):
            raise ValueError("calibration threshold differs from frozen threshold selection")
        for name, path in (
            ("model_dir", self.model_dir),
            ("tokenizer_dir", self.tokenizer_dir),
            ("model_code_dir", self.model_code_dir),
        ):
            if not path.exists():
                raise FileNotFoundError(f"bundle {name} not found: {path}")
        if not self.calibration_path.is_file():
            raise FileNotFoundError(f"bundle calibration not found: {self.calibration_path}")
