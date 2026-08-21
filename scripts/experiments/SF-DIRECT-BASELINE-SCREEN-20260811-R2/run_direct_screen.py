#!/usr/bin/env python3
"""GPU-only S0 runner consuming one frozen CPU DATA PASS attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(value, encoding="utf-8")
    os.replace(tmp, path)


def atomic_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def nonresult_metrics(cfg: dict, status: str, reason: str | None = None) -> dict:
    value = {
        "schema_version": "TEFM-SF-DIRECT-METRICS-2.0.0", "exp_id": cfg["exp_id"],
        "profile": cfg.get("profile", "screen"), "status": status, "primary_metric": 0.0,
        "semantic_success": False, "claim_eligible": False, "scientific_metrics_valid": 0,
        "scientific_screen_executed": 0, "s0_numeric_gate_pass": False,
        "hierarchical_stage_authorized": False, "audit_in_numeric_gate": False,
    }
    if reason:
        value["terminal_reason"] = reason
    return value


def verify_canonical_output_manifest(root: Path, cfg: dict) -> dict[str, str]:
    manifest = root / cfg["output_root"] / "output_manifest.sha256"
    entries: dict[str, str] = {}
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("  ", 1)
        if len(fields) != 2 or len(fields[0]) != 64 or any(c not in "0123456789abcdef" for c in fields[0]):
            raise ValueError(f"invalid canonical output manifest line {line_number}")
        expected, relpath = fields
        relative = Path(relpath)
        if relative.is_absolute() or ".." in relative.parts or relpath in entries:
            raise ValueError(f"unsafe/duplicate canonical output manifest path: {relpath}")
        target = root / relative
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f"canonical output manifest artifact drift: {relpath}")
        entries[relpath] = expected
    if str(manifest.relative_to(root)) in entries:
        raise ValueError("canonical output manifest must not include itself")
    return entries


def finalize_terminal_state(root: Path, cfg: dict, status: str, attempt_id: str,
                            extra_paths: tuple[Path, ...] = (), reason: str | None = None) -> dict[str, str]:
    """Atomically supersede every prior canonical view with one terminal-state manifest."""
    out = root / cfg["output_root"]
    atomic_text(out / "STATUS", status + "\n")
    if status != "COMPLETED":
        atomic_json(out / "metrics.json", nonresult_metrics(cfg, status, reason))
    success_anchor = None
    if status == "DATA_READY":
        success_anchor = cfg["data_pass_pointer"]
    elif status == "COMPLETED":
        success_anchor = str((out / "PUBLISHED_MANIFEST.json").relative_to(root))
    terminal = {
        "schema_version": "TEFM-SF-DIRECT-TERMINAL-1.0.0", "exp_id": cfg["exp_id"],
        "status": status, "attempt_id": attempt_id, "success_anchor": success_anchor,
        "canonical_manifest": str((out / "output_manifest.sha256").relative_to(root)),
        "unlisted_artifacts_are_superseded": True,
    }
    if reason:
        terminal["reason"] = reason
    atomic_json(out / "TERMINAL_STATE.json", terminal)
    required = [out / "STATUS", out / "code_review_gate.json", out / "input_manifest.json",
                out / "static_contract.json", out / "metrics.json", out / "TERMINAL_STATE.json"]
    if status == "DATA_READY":
        required.append(root / cfg["data_pass_pointer"])
    elif status == "COMPLETED":
        required.extend((out / "PUBLISHED_MANIFEST.json", root / cfg["report_path"]))
    paths = required + list(extra_paths)
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"terminal canonical output artifacts missing: {missing}")
    unique = {str(path.relative_to(root)): path for path in paths}
    payload = "".join(f"{sha256_file(unique[relpath])}  {relpath}\n" for relpath in sorted(unique))
    atomic_text(out / "output_manifest.sha256", payload)
    return verify_canonical_output_manifest(root, cfg)


def safe_attempt_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
        raise ValueError("invalid attempt_id")
    return value


def create_stage(attempts: Path, attempt_id: str) -> tuple[Path, Path]:
    staging, final = attempts / f"gpu-{safe_attempt_id(attempt_id)}.tmp", attempts / f"gpu-{attempt_id}"
    if staging.exists() or final.exists():
        raise FileExistsError(f"refusing dirty/stale GPU attempt: {staging} or {final}")
    staging.mkdir(parents=True)
    return staging, final


def package_files(root: Path, exp: str) -> list[Path]:
    d = root / "scripts/experiments" / exp
    return [root / "configs" / f"{exp}.yaml", d / "direct_s0_data.py", d / "direct_s0_task.py", d / "run_cpu_data_stage.py",
            d / "run_direct_screen.py", d / "preflight_sbatch.py", d / "test_direct_s0.py", d / "FROZEN_ASSET_CONTRACT_V1.json", d / "FROZEN_SPECIES_HOLDOUT_V1.tsv",
            root / "sbatch" / f"{exp}.data.sbatch", root / "sbatch" / f"{exp}.sbatch"]


def current_package_hashes(root: Path, exp: str) -> dict[str, str]:
    return {str(path.relative_to(root)): sha256_file(path) for path in package_files(root, exp)}


def verify_consumed_model_assets(root: Path, cfg: dict) -> dict[str, str]:
    contract_path = root / cfg["asset_contract"]
    if sha256_file(contract_path) != cfg["asset_contract_sha256"]:
        raise ValueError("GPU asset contract identity mismatch")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    observed = {}
    for key, base_key in (("base_checkpoint_files", "base_checkpoint"), ("historical_head_files", "historical_head")):
        base = root / cfg[base_key]
        for relpath, expected in contract[key].items():
            path = base / relpath
            actual = sha256_file(path)
            if actual != expected:
                raise ValueError(f"GPU consumed model asset drift: {base_key}/{relpath}")
            observed[f"{base_key}/{relpath}"] = actual
    return observed


def validate_data_pass(root: Path, cfg: dict, package: dict[str, str]) -> tuple[Path, dict, str]:
    verify_consumed_model_assets(root, cfg)
    pointer_path = root / cfg["data_pass_pointer"]
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if pointer.get("status") != "PASS" or pointer.get("exp_id") != cfg["exp_id"]:
        raise ValueError("DATA PASS pointer is absent/non-PASS/wrong experiment")
    attempt = root / pointer["attempt_relpath"]
    manifest_path = attempt / "PASS_MANIFEST.json"
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != pointer["pass_manifest_sha256"]:
        raise ValueError("DATA PASS manifest identity mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS" or not manifest.get("cpu_tests_pass") or not manifest.get("leakage_audit_pass"):
        raise ValueError("DATA PASS manifest semantic gate false")
    if manifest.get("audit_in_numeric_gate") or not manifest.get("audit_physically_separate"):
        raise ValueError("optional stress audit isolation gate false")
    if manifest.get("homology_component_overlap_count") != 0 or manifest.get("primary_clade_overlap_count") != 0:
        raise ValueError("frozen DATA PASS homology/clade leakage gate false")
    if manifest["config_sha256"] != sha256_file(root / "configs" / f"{cfg['exp_id']}.yaml") or manifest["package_hashes"] != package:
        raise ValueError("DATA PASS is stale relative to current reviewed package")
    for relpath, expected in manifest["files"].items():
        path = attempt / relpath
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"frozen DATA PASS file drift: {relpath}")
    return attempt, manifest, manifest_sha


def quarantine_stale(root: Path, cfg: dict, attempt_id: str) -> None:
    stale = root / cfg["output_root"] / "stale"
    stale.mkdir(parents=True, exist_ok=True)
    targets = [(root / cfg["output_root"] / "metrics.json", stale / f"metrics.{attempt_id}.json"),
               (root / cfg["report_path"], stale / f"report.{attempt_id}.json")]
    for source, target in targets:
        if source.exists():
            if target.exists():
                raise FileExistsError(f"refusing to overwrite stale quarantine: {target}")
            os.replace(source, target)


def write_static_not_run(root: Path, cfg: dict, static: dict) -> None:
    """Replace legacy placeholders so no stale scientific-looking metric survives review."""
    out = root / cfg["output_root"]
    atomic_json(out / "static_contract.json", static)
    finalize_terminal_state(root, cfg, "IMPLEMENTED_NOT_RUN", "static-contract-check",
                            reason="scientific screen not executed")


def create_payload_manifest(stage: Path) -> dict:
    required = {"metrics.json", "report.json", "RUN_MANIFEST.json", "runtime_environment.json", "external_environment_manifest.txt",
                "gpu_smoke.json",
                "clean_direct_head/training_meta.json", "clean_direct_head/calibration.json", "clean_direct_head/best_model/config.json",
                "clean_direct_head/best_model/pytorch_model.bin"}
    files = {str(path.relative_to(stage)): sha256_file(path) for path in sorted(stage.rglob("*"))
             if path.is_file() and path.name != "PAYLOAD_MANIFEST.json"}
    missing = required - set(files)
    if missing:
        raise ValueError(f"payload manifest missing required artifacts: {sorted(missing)}")
    manifest = {"schema_version": "TEFM-SF-DIRECT-PAYLOAD-1.0.0", "hash_algorithm": "sha256",
                "self_included": False, "files": files}
    atomic_json(stage / "PAYLOAD_MANIFEST.json", manifest)
    return manifest


def verify_payload_manifest(stage: Path) -> str:
    path = stage / "PAYLOAD_MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "TEFM-SF-DIRECT-PAYLOAD-1.0.0" or manifest.get("self_included") is not False:
        raise ValueError("payload manifest schema/self-reference invalid")
    if "PAYLOAD_MANIFEST.json" in manifest.get("files", {}):
        raise ValueError("payload manifest is self-referential")
    for relpath, expected in manifest.get("files", {}).items():
        target = stage / relpath
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f"payload artifact drift: {relpath}")
    return sha256_file(path)


def publish_top_level(root: Path, cfg: dict, final: Path, payload_sha: str, metrics: dict, report: dict) -> None:
    out, report_path = root / cfg["output_root"], root / cfg["report_path"]
    atomic_json(out / "metrics.json", metrics)
    atomic_json(report_path, report)
    published = {"schema_version": "TEFM-SF-DIRECT-PUBLISHED-1.0.0", "attempt_relpath": str(final.relative_to(root)),
                 "payload_manifest_sha256": payload_sha, "metrics_sha256": sha256_file(out / "metrics.json"),
                 "report_sha256": sha256_file(report_path), "self_included": False}
    atomic_json(out / "PUBLISHED_MANIFEST.json", published)
    verify_published_manifest(root, cfg)


def verify_published_manifest(root: Path, cfg: dict) -> dict:
    out, report_path = root / cfg["output_root"], root / cfg["report_path"]
    published = json.loads((out / "PUBLISHED_MANIFEST.json").read_text(encoding="utf-8"))
    if published.get("schema_version") != "TEFM-SF-DIRECT-PUBLISHED-1.0.0" or published.get("self_included") is not False:
        raise ValueError("published manifest schema/self-reference invalid")
    final = root / published["attempt_relpath"]
    checks = ((final / "PAYLOAD_MANIFEST.json", published["payload_manifest_sha256"]),
              (out / "metrics.json", published["metrics_sha256"]), (report_path, published["report_sha256"]))
    if any(not path.is_file() or sha256_file(path) != expected for path, expected in checks):
        raise ValueError("top-level atomic publication verification failed")
    return published


def aggregate(cfg: dict, data_attempt: Path, data_manifest_sha: str, gpu_stage: Path, config_sha: str) -> tuple[dict, dict]:
    primary = json.loads((gpu_stage / "clean_primary_metrics.json").read_text(encoding="utf-8"))
    historical = json.loads((gpu_stage / "historical_primary_metrics.json").read_text(encoding="utf-8"))
    audit = json.loads((gpu_stage / "clean_audit_metrics.json").read_text(encoding="utf-8"))
    historical_audit = json.loads((gpu_stage / "historical_audit_metrics.json").read_text(encoding="utf-8"))
    leakage = json.loads((data_attempt / "leakage_audit.json").read_text(encoding="utf-8"))
    metadata = json.loads((data_attempt / "data/metadata.json").read_text(encoding="utf-8"))
    training = json.loads((gpu_stage / "clean_direct_head/training_meta.json").read_text(encoding="utf-8"))
    smoke = json.loads((gpu_stage / "gpu_smoke.json").read_text(encoding="utf-8"))
    if training["initialization"] != cfg["base_checkpoint"] or training["historical_head_used_for_initialization"]:
        raise ValueError("training_meta does not prove clean base initialization")
    if training["initialization_asset_contract_sha256"] != cfg["asset_contract_sha256"]:
        raise ValueError("training_meta initialization asset identity mismatch")
    if training["data_pass_manifest_sha256"] != data_manifest_sha or training["config_sha256"] != config_sha:
        raise ValueError("training_meta data/config identity mismatch")
    if primary["partition"] != "test_primary" or audit["partition"] != "audit_optional_stress":
        raise ValueError("primary/audit evaluation partition mismatch")
    a = cfg["acceptance"]
    gates = {
        "main4_conditional_macro_f1": primary["main4_conditional_macro_f1"] >= a["main4_conditional_macro_f1"],
        "te_detect_f1": primary["te_detect_f1"] >= a["te_detect_f1"],
        "unknown_recall": primary["unknown_recall"] >= a["unknown_recall"],
        "main4_false_unknown_rate": primary["main4_false_unknown_rate"] <= a["main4_false_unknown_rate_max"],
        "eligible_main4_coverage": metadata["eligible_main4_coverage"] >= a["eligible_main4_coverage"],
        "minimum_clade_main4_macro_f1": primary["minimum_clade_main4_macro_f1"] >= a["minimum_clade_main4_macro_f1"],
        "homology_component_overlap_count": leakage["homology_component_overlap_count"] <= a["homology_component_overlap_count_max"],
        "primary_clade_overlap_count": leakage["primary_clade_overlap_count"] <= a["primary_clade_overlap_count_max"],
        "test_calibration_count": primary["test_calibration_count"] == 0,
        "gpu_smoke": smoke["pass"],
    }
    flat = {"primary_metric": primary["main4_conditional_macro_f1"], "main4_conditional_macro_f1": primary["main4_conditional_macro_f1"],
            "te_detect_f1": primary["te_detect_f1"], "unknown_recall": primary["unknown_recall"],
            "main4_false_unknown_rate": primary["main4_false_unknown_rate"], "eligible_main4_coverage": metadata["eligible_main4_coverage"],
            "minimum_clade_main4_macro_f1": primary["minimum_clade_main4_macro_f1"],
            "homology_component_overlap_count": leakage["homology_component_overlap_count"],
            "primary_clade_overlap_count": leakage["primary_clade_overlap_count"], "test_calibration_count": 0,
            "hierarchical_path_distance": primary["hierarchical_path_distance"], "overconfident_leaf_error": primary["overconfident_leaf_error"],
            "RN_te_fpr": primary["RN_te_fpr"], "hardN_te_fpr": primary["hardN_te_fpr"],
            "s0_numeric_gate_pass": all(gates.values()), "hierarchical_stage_authorized": False}
    metrics = {"schema_version": "TEFM-SF-DIRECT-METRICS-2.0.0", "exp_id": cfg["exp_id"], "profile": cfg["profile"],
               "semantic_success": True, "claim_eligible": False, **flat, "acceptance_gates": gates,
               "per_clade": primary["per_clade"], "per_species_secondary": primary["per_species_secondary"], "audit_only_metrics": audit,
               "historical_continuity_comparator": historical, "historical_audit_only_comparator": historical_audit,
               "audit_in_numeric_gate": False, "holdout_unit": "order_taxid", "clade_generalization_claim": True,
               "scientific_metrics_valid": 1, "scientific_screen_executed": 1}
    report = {"exp_id": cfg["exp_id"], "profile": cfg["profile"], "primary_metric": flat["primary_metric"], "metrics": metrics,
              "dataset": {"name": "PRE-S0-CANONICAL-20260810-R2", "version": "Dfam39-accession/order-clade-v3",
                          "split": "Dfam-accession homology_component blocked + order_taxid held-out; optional stress audit-only",
                          "sha256": data_manifest_sha, "data_pass_manifest_sha256": data_manifest_sha,
                          "canonical_manifest_sha256": cfg["canonical_split_sha256"],
                          "ontology_sha256": cfg["ontology_sha256"]},
              "evaluator": {"path": f"scripts/experiments/{cfg['exp_id']}/direct_s0_task.py", "version": "2.0.0",
                            "sha256": sha256_file(Path(cfg["project_root"]) / "scripts/experiments" / cfg["exp_id"] / "direct_s0_task.py")},
              "semantic_success": True, "claim_eligible": False, "config_sha256": config_sha,
              "s0_numeric_gate_pass": all(gates.values()),
              "hierarchical_stage_authorized": False}
    if not all(math.isfinite(float(x)) for x in flat.values() if isinstance(x, (int, float))):
        raise ValueError("non-finite flat metric")
    return metrics, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--static-check-only", action="store_true")
    parser.add_argument("--external-env-manifest", type=Path)
    args = parser.parse_args()
    config = args.config.resolve()
    cfg = json.loads(config.read_text(encoding="utf-8"))
    root, exp = Path(cfg["project_root"]).resolve(), cfg["exp_id"]
    out, scripts = root / cfg["output_root"], root / "scripts/experiments" / exp
    package = current_package_hashes(root, exp)
    static = {"schema_version": "TEFM-SF-DIRECT-STATIC-2.0.0", "config_sha256": sha256_file(config), "package_hashes": package,
              "goal": {"path": cfg["goal_contract"], "sha256": sha256_file(root / cfg["goal_contract"])},
              "protocol": {"path": cfg["protocol"], "sha256": sha256_file(root / cfg["protocol"])}}
    if static["goal"]["sha256"] != cfg["goal_contract_sha256"] or static["protocol"]["sha256"] != cfg["protocol_sha256"]:
        raise ValueError("goal/protocol identity mismatch")
    atomic_json(out / "input_manifest.json", static)
    atomic_json(out / "static_contract.json", static)
    if args.static_check_only:
        write_static_not_run(root, cfg, static)
        print(json.dumps({"status": "IMPLEMENTED_NOT_RUN", "package_files": len(package)}, sort_keys=True))
        return
    attempt_id = safe_attempt_id(args.attempt_id)
    atomic_text(out / "STATUS", "VALIDATING_INPUTS\n")
    try:
        data_attempt, _data_manifest, data_manifest_sha = validate_data_pass(root, cfg, package)
        staging, final = create_stage(root / cfg["attempts_root"], attempt_id)
        quarantine_stale(root, cfg, attempt_id)
    except Exception as exc:
        failure = out / f"validation_failure.{attempt_id}.json"
        atomic_json(failure, {"error_type": type(exc).__name__, "error": str(exc),
                    "traceback": traceback.format_exc()})
        finalize_terminal_state(root, cfg, "FAILED", attempt_id, (failure,), str(exc))
        raise
    atomic_text(out / "STATUS", "RUNNING\n")
    try:
        py = sys.executable
        commands = []
        if args.external_env_manifest is None or not args.external_env_manifest.is_file():
            raise ValueError("GPU stage requires the sbatch-generated environment manifest")
        shutil.copyfile(args.external_env_manifest, staging / "external_environment_manifest.txt")
        atomic_json(staging / "runtime_environment.json", {"python": sys.version, "executable": sys.executable,
                    "platform": platform.platform(), "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "UNSET"),
                    "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "UNSET")})
        smoke_command = [py, str(scripts / "direct_s0_task.py"), "smoke", "--config", str(config), "--data-dir", str(data_attempt / "data"),
                         "--output", str(staging / "gpu_smoke.json")]
        commands.append(smoke_command); subprocess.run(smoke_command, check=True)
        model_dir = staging / "clean_direct_head"
        train_command = [py, str(scripts / "direct_s0_task.py"), "train", "--config", str(config), "--data-dir", str(data_attempt / "data"),
                         "--output-dir", str(model_dir), "--data-pass-sha256", data_manifest_sha]
        commands.append(train_command); subprocess.run(train_command, check=True)
        for model, partition, name in (("clean", "test_primary", "clean_primary_metrics.json"),
                                        ("historical", "test_primary", "historical_primary_metrics.json"),
                                        ("clean", "audit_optional_stress", "clean_audit_metrics.json"),
                                        ("historical", "audit_optional_stress", "historical_audit_metrics.json")):
            command = [py, str(scripts / "direct_s0_task.py"), "eval", "--config", str(config), "--data-dir", str(data_attempt / "data"),
                       "--clean-model-dir", str(model_dir), "--model", model, "--partition", partition, "--output", str(staging / name)]
            commands.append(command); subprocess.run(command, check=True)
        metrics, report = aggregate(cfg, data_attempt, data_manifest_sha, staging, sha256_file(config))
        atomic_json(staging / "metrics.json", metrics)
        atomic_json(staging / "report.json", report)
        atomic_json(staging / "RUN_MANIFEST.json", {"schema_version": "TEFM-SF-DIRECT-RUN-1.0.0", "attempt_id": attempt_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(), "runner_command": sys.argv, "payload_commands": commands,
            "config_sha256": sha256_file(config),
            "data_pass_manifest_sha256": data_manifest_sha, "package_hashes": package,
            "goal_sha256": cfg["goal_contract_sha256"], "protocol_sha256": cfg["protocol_sha256"],
            "evaluator_sha256": report["evaluator"]["sha256"], "test_sha256": package[f"scripts/experiments/{exp}/test_direct_s0.py"],
            "cpu_sbatch_sha256": package[f"sbatch/{exp}.data.sbatch"], "gpu_sbatch_sha256": package[f"sbatch/{exp}.sbatch"]})
        create_payload_manifest(staging)
        payload_sha = verify_payload_manifest(staging)
        os.replace(staging, final)
        if verify_payload_manifest(final) != payload_sha:
            raise ValueError("payload changed during atomic promotion")
        publish_top_level(root, cfg, final, payload_sha, metrics, report)
        finalize_terminal_state(root, cfg, "COMPLETED", attempt_id)
        print(json.dumps({"status": "COMPLETED", "s0_numeric_gate_pass": metrics["s0_numeric_gate_pass"],
                          "hierarchical_stage_authorized": False}, sort_keys=True))
    except Exception as exc:
        failure_root = staging if staging.exists() else final
        failure = failure_root / "failure.json"
        atomic_json(failure, {"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        finalize_terminal_state(root, cfg, "FAILED", attempt_id, (failure,), str(exc))
        raise


if __name__ == "__main__":
    main()
