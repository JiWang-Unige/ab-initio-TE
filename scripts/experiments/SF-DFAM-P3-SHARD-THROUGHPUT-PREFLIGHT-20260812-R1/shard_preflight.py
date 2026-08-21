#!/usr/bin/env python3
"""Deterministic CPU-only Dfam p3 shard throughput/correctness preflight."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class PerformanceBudgetInfeasible(RuntimeError):
    """A timed engineering probe exceeded its preregistered budget (valid negative)."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: Iterable[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def verify_pin(root: Path, cfg: dict, path_key: str, hash_key: str) -> Path:
    path = root / cfg[path_key]
    if not path.is_file() or sha256_file(path) != cfg[hash_key]:
        raise ValueError(f"PINNED_INPUT_DRIFT:{path_key}")
    return path


def authorization_flags() -> dict:
    return {"r0_authorized": False, "r1_authorized": False, "r2_authorized": False,
            "gpu_authorized": False, "s1_authorized": False,
            "scientific_identity_conclusion_authorized": False}


def ensure_slurm_log_dir(root: Path, cfg: dict) -> Path:
    """Pre-create the directory Slurm opens before the job script can run."""
    log_dir = root / cfg["slurm_log_dir"]
    preview = root / cfg["preview_root"]
    if log_dir.parent != preview or log_dir.is_symlink():
        raise ValueError("SLURM_LOG_DIR_CONTRACT_INVALID")
    log_dir.mkdir(parents=True, exist_ok=True)
    probe = log_dir / ".write_probe.tmp"
    try:
        descriptor = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, b"writable\n")
        finally:
            os.close(descriptor)
    finally:
        if probe.exists():
            probe.unlink()
    sentinel = log_dir / ".slurm_parent_precreated.json"
    atomic_json(sentinel, {"schema_version": "SF-P3-SLURM-LOG-DIR-1.0.0",
                           "root_relative_log_dir": str(log_dir.relative_to(root)),
                           "precreated_before_submission": True, "writable_probe_passed": True})
    return sentinel


def discover_topology_units(handle) -> list[str]:
    import h5py
    units: list[str] = []
    aux, dr = handle.get("Families/Aux"), handle.get("Families/DR")
    if not isinstance(aux, h5py.Group) or not isinstance(dr, h5py.Group):
        raise ValueError("FROZEN_TOPOLOGY_ROOT_MISSING")
    units.extend(f"Families/Aux/{key}" for key in sorted(aux.keys()))
    for first in sorted(dr.keys()):
        first_group = dr[first]
        if not isinstance(first_group, h5py.Group):
            raise ValueError(f"FROZEN_TOPOLOGY_WRONG_TYPE:{first_group.name}")
        units.extend(f"Families/DR/{first}/{second}" for second in sorted(first_group.keys()))
    return units


def validate_inputs(root: Path, cfg: dict) -> tuple[Path, list[str], dict]:
    if cfg.get("authorization") != authorization_flags():
        raise ValueError("AUTHORIZATION_CONTRACT_MUST_REMAIN_ALL_FALSE")
    for path_key, hash_key in (("layout_manifest", "layout_manifest_sha256"),
                               ("rmlib_config", "rmlib_config_sha256"),
                               ("evaluator_contract", "evaluator_contract_sha256"),
                               ("parent_r0_config", "parent_r0_config_sha256"),
                               ("r0_observed_telemetry", "r0_observed_telemetry_sha256")):
        verify_pin(root, cfg, path_key, hash_key)
    telemetry = json.loads((root / cfg["r0_observed_telemetry"]).read_text(encoding="utf-8"))
    expected_telemetry = {"datasets_scanned": int(cfg["feasibility"]["r0_observed_datasets"]),
                          "elapsed_seconds_before_cancel": int(cfg["feasibility"]["r0_observed_elapsed_seconds"]),
                          "projected_full_scan_seconds": int(cfg["feasibility"]["r0_projected_full_scan_seconds"])}
    if any(int(telemetry.get(key, -1)) != value for key, value in expected_telemetry.items()):
        raise ValueError("R0_OBSERVED_TELEMETRY_SEMANTIC_DRIFT")
    source = root / cfg["source_h5"]
    if not source.is_file() or source.stat().st_size != int(cfg["source_h5_size_bytes"]):
        raise ValueError("SOURCE_H5_SIZE_DRIFT")
    layout = json.loads((root / cfg["layout_manifest"]).read_text(encoding="utf-8"))
    entries = [row for row in layout["partitions"] if int(row["partition"]) == int(cfg["source_partition"])]
    if len(entries) != 1 or entries[0]["lookup_by_name"] is not False or int(entries[0]["size_bytes"]) != source.stat().st_size:
        raise ValueError("SOURCE_LAYOUT_CONTRACT_DRIFT")
    import h5py
    with h5py.File(source, "r") as handle:
        metadata = {key: str(handle.attrs.get(key)) for key in ("db_version", "famdb_version", "partition_num")}
        expected = {"db_version": cfg["source_database"]["db_version"],
                    "famdb_version": cfg["source_database"]["famdb_version"],
                    "partition_num": str(cfg["source_partition"])}
        if metadata != expected:
            raise ValueError(f"SOURCE_H5_METADATA_DRIFT:{metadata}")
        units = discover_topology_units(handle)
    unit_hash = sha256_text("".join(unit + "\n" for unit in units))
    if len(units) != int(cfg["topology"]["expected_unit_count"]) or unit_hash != cfg["topology"]["ordered_unit_list_sha256"]:
        raise ValueError(f"SOURCE_TOPOLOGY_DRIFT:{len(units)}:{unit_hash}")
    audit = {"source_h5_size_bytes": source.stat().st_size, "source_partition": int(cfg["source_partition"]),
             "topology_unit_count": len(units), "topology_unit_list_sha256": unit_hash,
             "layout_manifest_sha256": cfg["layout_manifest_sha256"],
             "evaluator_contract_sha256": cfg["evaluator_contract_sha256"],
             "r0_observed_telemetry_sha256": cfg["r0_observed_telemetry_sha256"],
             "full_h5_content_hashing_used": False, "h5_open_mode": "read_only",
             "scientific_target_resolution_executed": False}
    return source, units, audit


def iter_dataset_paths(group):
    import h5py
    for key in sorted(group.keys()):
        item = group[key]
        if isinstance(item, h5py.Dataset):
            yield item.name.lstrip("/")
        elif isinstance(item, h5py.Group):
            yield from iter_dataset_paths(item)
        else:
            raise ValueError(f"WORKLOAD_OBJECT_WRONG_TYPE:{item.name}")


def round_robin_unit_assignment(units: list[str], workers: int) -> dict[int, list[str]]:
    if workers <= 0:
        raise ValueError("INVALID_WORKER_COUNT")
    result = {index: [] for index in range(workers)}
    for index, unit in enumerate(units):
        result[index % workers].append(unit)
    return result


def balanced_unit_assignment(units: list[str], counts: dict[str, int], workers: int) -> dict[int, list[str]]:
    if set(units) != set(counts) or any(counts[unit] <= 0 for unit in units):
        raise ValueError("UNIT_COUNT_CONTRACT_INVALID")
    result, loads = {index: [] for index in range(workers)}, [0] * workers
    for unit in sorted(units, key=lambda value: (-counts[value], value)):
        worker = min(range(workers), key=lambda index: (loads[index], index))
        result[worker].append(unit)
        loads[worker] += counts[unit]
    for worker in result:
        result[worker].sort(key=units.index)
    return result


def inventory_worker(source: Path, units_path: Path, stage: Path) -> dict:
    """Materialize assigned canonical paths with one independent read-only H5 handle."""
    import h5py
    stage.mkdir(parents=True, exist_ok=False)
    payload = json.loads(units_path.read_text(encoding="utf-8"))
    units = payload.get("units")
    if not isinstance(units, list) or not units or len(units) != len(set(units)):
        raise ValueError("INVENTORY_UNIT_PAYLOAD_INVALID")
    started, by_unit = time.monotonic(), {}
    with h5py.File(source, "r") as handle:
        if handle.mode != "r":
            raise ValueError("INVENTORY_H5_NOT_READ_ONLY")
        for unit in units:
            if unit not in handle:
                raise ValueError(f"INVENTORY_UNIT_MISSING:{unit}")
            paths = list(iter_dataset_paths(handle[unit]))
            if not paths or paths != sorted(paths) or len(paths) != len(set(paths)):
                raise ValueError(f"INVENTORY_UNIT_EMPTY_UNSORTED_OR_DUPLICATED:{unit}")
            by_unit[unit] = paths
    elapsed = time.monotonic() - started
    result = {"schema_version": "SF-P3-INVENTORY-WORKER-1.0.0", "status": "INVENTORY_COMPLETE",
              "worker_id": str(payload["worker_id"]), "units": units, "unit_paths": by_unit,
              "dataset_count": sum(len(paths) for paths in by_unit.values()), "elapsed_seconds": elapsed,
              "h5_open_mode": "read_only"}
    atomic_json(stage / "inventory_result.json", result)
    atomic_json(stage / "inventory_manifest.json",
                {"inventory_result_sha256": sha256_file(stage / "inventory_result.json"),
                 "unit_payload_sha256": sha256_file(units_path), "source_size_bytes": source.stat().st_size})
    return result


def run_processes(commands: list[list[str]], timeout_seconds: float, log_dir: Path) -> float:
    if not commands:
        raise ValueError("EMPTY_CHILD_COMMANDS")
    log_dir.mkdir(parents=True, exist_ok=False)
    processes: list[subprocess.Popen] = []
    handles = []
    started = time.monotonic()
    try:
        for index, command in enumerate(commands):
            stdout = (log_dir / f"child_{index}.out").open("w", encoding="utf-8")
            handles.append(stdout)
            stderr = (log_dir / f"child_{index}.err").open("w", encoding="utf-8")
            handles.append(stderr)
            processes.append(subprocess.Popen(command, stdout=stdout, stderr=stderr, text=True))
        deadline = started + timeout_seconds
        while any(process.poll() is None for process in processes):
            if time.monotonic() >= deadline:
                raise PerformanceBudgetInfeasible("CHILD_PERFORMANCE_TIMEOUT")
            time.sleep(0.02)
        returncodes = [process.returncode for process in processes]
        if any(code != 0 for code in returncodes):
            raise RuntimeError(f"CHILD_NONZERO_FAIL_CLOSED:{returncodes}")
        return time.monotonic() - started
    except BaseException:
        for process in processes:
            if process.poll() is None:
                try:
                    process.kill()
                except (OSError, ProcessLookupError):
                    pass
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    process.terminate()
                except (OSError, ProcessLookupError):
                    pass
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError("CHILD_CLEANUP_WAIT_TIMEOUT") from exc
        raise
    finally:
        for handle in handles:
            handle.close()


def launch_inventory_rebuild(source: Path, units: list[str], assignment: dict[int, list[str]], stage: Path,
                             timeout_seconds: float) -> tuple[dict[str, list[str]], float, float]:
    stage.mkdir(parents=True, exist_ok=False)
    executable, python = str(Path(__file__).resolve()), sys.executable
    commands, worker_stages = [], []
    for worker in sorted(assignment):
        payload = stage / f"worker_{worker}_units.json"
        atomic_json(payload, {"worker_id": str(worker), "units": assignment[worker]})
        worker_stage = stage / f"worker_{worker}"
        commands.append([python, executable, "--inventory-worker", "--source", str(source),
                         "--units", str(payload), "--worker-stage", str(worker_stage)])
        worker_stages.append(worker_stage)
    wall = run_processes(commands, timeout_seconds, stage / "logs")
    aggregation_started, by_unit = time.monotonic(), {}
    for worker, worker_stage in zip(sorted(assignment), worker_stages):
        result_path, manifest_path = worker_stage / "inventory_result.json", worker_stage / "inventory_manifest.json"
        if not result_path.is_file() or not manifest_path.is_file():
            raise ValueError("INVENTORY_OUTPUT_TRUNCATED")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sha256_file(result_path) != manifest.get("inventory_result_sha256"):
            raise ValueError("INVENTORY_OUTPUT_HASH_MISMATCH")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "INVENTORY_COMPLETE" or result.get("units") != assignment[worker]:
            raise ValueError("INVENTORY_OUTPUT_SCHEMA_OR_ASSIGNMENT")
        for unit, paths in result["unit_paths"].items():
            if unit in by_unit or paths != sorted(paths) or len(paths) != len(set(paths)):
                raise ValueError("INVENTORY_OUTPUT_DUPLICATE_OR_UNSORTED")
            by_unit[unit] = paths
    if set(by_unit) != set(units):
        raise ValueError("INVENTORY_UNIT_UNION_MISMATCH")
    ordered = {unit: by_unit[unit] for unit in units}
    return ordered, wall, time.monotonic() - aggregation_started


def inventory_identity(by_unit: dict[str, list[str]], units: list[str]) -> tuple[list[str], dict[str, int], str]:
    if list(by_unit) != units:
        raise ValueError("INVENTORY_UNIT_ORDER_MISMATCH")
    paths = [path for unit in units for path in by_unit[unit]]
    counts = {unit: len(by_unit[unit]) for unit in units}
    if not paths or len(paths) != len(set(paths)) or any(count <= 0 for count in counts.values()):
        raise ValueError("INVENTORY_EMPTY_OR_DUPLICATED")
    return paths, counts, sha256_text("".join(path + "\n" for path in paths))


def allocate_stratified_counts(unit_counts: dict[str, int], sample_count: int) -> dict[str, int]:
    if not unit_counts or any(value <= 0 for value in unit_counts.values()) or sample_count < len(unit_counts):
        raise ValueError("STRATIFIED_SAMPLE_CONTRACT_INVALID")
    population = sum(unit_counts.values())
    if sample_count > population:
        raise ValueError("STRATIFIED_SAMPLE_EXCEEDS_POPULATION")
    allocation = {unit: 1 for unit in unit_counts}
    remaining = sample_count - len(allocation)
    ideals = {unit: remaining * unit_counts[unit] / population for unit in unit_counts}
    for unit in allocation:
        extra = min(unit_counts[unit] - 1, math.floor(ideals[unit]))
        allocation[unit] += extra
    unassigned = sample_count - sum(allocation.values())
    order = sorted(unit_counts, key=lambda unit: (-(ideals[unit] - math.floor(ideals[unit])), unit))
    while unassigned:
        progressed = False
        for unit in order:
            if allocation[unit] < unit_counts[unit]:
                allocation[unit] += 1
                unassigned -= 1
                progressed = True
                if not unassigned:
                    break
        if not progressed:
            raise ValueError("STRATIFIED_SAMPLE_ALLOCATION_STALLED")
    return allocation


def build_stratified_workload(by_unit: dict[str, list[str]], units: list[str], count: int) -> tuple[list[str], list[dict]]:
    unit_counts = {unit: len(by_unit[unit]) for unit in units}
    allocation = allocate_stratified_counts(unit_counts, count)
    workload, audit = [], []
    for unit in units:
        population, sample = unit_counts[unit], allocation[unit]
        indices = [min(population - 1, math.floor((index + 0.5) * population / sample)) for index in range(sample)]
        if len(indices) != len(set(indices)):
            raise ValueError("STRATIFIED_MIDPOINT_INDEX_DUPLICATE")
        selected = [by_unit[unit][index] for index in indices]
        workload.extend(selected)
        quartiles = Counter(min(3, (4 * index) // population) for index in indices)
        audit.append({"unit": unit, "population_count": population, "sample_count": sample,
                      "sample_fraction": sample / population, "inverse_probability_weight": population / sample,
                      "selected_min_index": min(indices), "selected_max_index": max(indices),
                      "selected_span_fraction": (max(indices) - min(indices) + 1) / population,
                      "path_depth_min": min(path.count("/") + 1 for path in selected),
                      "path_depth_max": max(path.count("/") + 1 for path in selected),
                      "locality_q1": quartiles[0], "locality_q2": quartiles[1],
                      "locality_q3": quartiles[2], "locality_q4": quartiles[3]})
    if len(workload) != count or len(workload) != len(set(workload)):
        raise ValueError("REPRESENTATIVE_WORKLOAD_TRUNCATED_OR_DUPLICATED")
    return workload, audit


def shard_for_path(path: str, shards: int) -> int:
    if shards <= 0:
        raise ValueError("INVALID_SHARD_COUNT")
    return int(sha256_text(path)[:16], 16) % shards


def partition_workload(paths: list[str], shards: int) -> dict[int, list[str]]:
    result = {index: [] for index in range(shards)}
    for path in paths:
        result[shard_for_path(path, shards)].append(path)
    flattened = [path for index in result for path in result[index]]
    if len(flattened) != len(paths) or len(set(flattened)) != len(paths) or set(flattened) != set(paths):
        raise ValueError("SHARD_UNION_INTERSECTION_EXACTLY_ONCE_FAILED")
    return result


def write_workload(path: Path, dataset_paths: list[str], worker_id: str) -> dict:
    payload = {"schema_version": "SF-P3-WORKLOAD-1.0.0", "worker_id": worker_id,
               "dataset_paths": dataset_paths, "path_count": len(dataset_paths),
               "ordered_paths_sha256": sha256_text("".join(item + "\n" for item in dataset_paths))}
    atomic_json(path, payload)
    return payload


def validate_workload(payload: dict) -> list[str]:
    paths = payload.get("dataset_paths")
    if not isinstance(paths, list) or any(not isinstance(item, str) or not item for item in paths):
        raise ValueError("WORKLOAD_SCHEMA_INVALID")
    digest = sha256_text("".join(item + "\n" for item in paths))
    if int(payload.get("path_count", -1)) != len(paths) or payload.get("ordered_paths_sha256") != digest or len(paths) != len(set(paths)):
        raise ValueError("WORKLOAD_TRUNCATION_OR_HASH_MISMATCH")
    return paths


def decode_attr(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def worker_read(source: Path, workload_path: Path, stage: Path, batch_size: int) -> dict:
    import h5py
    if batch_size <= 0:
        raise ValueError("INVALID_WORKER_BATCH_SIZE")
    stage.mkdir(parents=True, exist_ok=False)
    payload = json.loads(workload_path.read_text(encoding="utf-8"))
    paths = validate_workload(payload)
    started, batch_started, records, batches = time.monotonic(), time.monotonic(), [], []
    with h5py.File(source, "r") as handle:
        if handle.mode != "r":
            raise ValueError("WORKER_H5_NOT_READ_ONLY")
        batch_records = 0
        for index, path in enumerate(paths, 1):
            item = handle.get(path)
            if not isinstance(item, h5py.Dataset):
                raise ValueError(f"WORKER_DATASET_MISSING_OR_WRONG_TYPE:{path}")
            record = {"path": path, "name": decode_attr(item.attrs.get("name")),
                      "has_accession": "accession" in item.attrs, "has_version": "version" in item.attrs,
                      "has_consensus": "consensus" in item.attrs, "has_model": "model" in item.attrs}
            records.append(sha256_text(stable_json(record)))
            batch_records += 1
            if index % batch_size == 0 or index == len(paths):
                now = time.monotonic()
                batches.append({"records": batch_records, "seconds": now - batch_started})
                batch_records, batch_started = 0, now
    elapsed = time.monotonic() - started
    result = {"schema_version": "SF-P3-WORKER-1.0.0", "worker_id": payload["worker_id"],
              "status": "WORKER_COMPLETE", "input_path_count": len(paths), "processed_path_count": len(records),
              "input_ordered_paths_sha256": payload["ordered_paths_sha256"],
              "record_digest_sha256": sha256_text("".join(item + "\n" for item in records)),
              "elapsed_seconds": elapsed, "records_per_second": len(records) / elapsed if elapsed else 0.0,
              "batch_measurements": batches, "h5_open_mode": "read_only"}
    atomic_json(stage / "worker_result.json", result)
    atomic_json(stage / "worker_manifest.json", {"worker_result_sha256": sha256_file(stage / "worker_result.json"),
                "workload_sha256": sha256_file(workload_path), "source_size_bytes": source.stat().st_size})
    return result


def launch_children(commands: list[list[str]], stages: list[Path], timeout_seconds: float,
                    log_dir: Path) -> tuple[list[dict], float]:
    if len(commands) != len(stages) or not commands:
        raise ValueError("CHILD_COMMAND_STAGE_CARDINALITY")
    wall = run_processes(commands, timeout_seconds, log_dir)
    results = []
    for stage in stages:
        result_path, manifest_path = stage / "worker_result.json", stage / "worker_manifest.json"
        if not result_path.is_file() or not manifest_path.is_file():
            raise ValueError(f"CHILD_OUTPUT_TRUNCATED:{stage}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sha256_file(result_path) != manifest.get("worker_result_sha256"):
            raise ValueError(f"CHILD_OUTPUT_HASH_MISMATCH:{stage}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "WORKER_COMPLETE" or result.get("processed_path_count") != result.get("input_path_count"):
            raise ValueError(f"CHILD_OUTPUT_SCHEMA_OR_COUNT:{stage}")
        results.append(result)
    return results, wall


def validate_worker_results(results: list[dict], workloads: list[dict]) -> None:
    if len(results) != len(workloads):
        raise ValueError("WORKER_RESULT_CARDINALITY")
    for result, workload in zip(results, workloads):
        paths = validate_workload(workload)
        if (str(result.get("worker_id")) != str(workload["worker_id"])
                or int(result.get("input_path_count", -1)) != len(paths)
                or int(result.get("processed_path_count", -1)) != len(paths)
                or result.get("input_ordered_paths_sha256") != workload["ordered_paths_sha256"]):
            raise ValueError(f"WORKER_INPUT_OUTPUT_BINDING_MISMATCH:{workload['worker_id']}")


def p95(values: list[float]) -> float:
    if not values:
        raise ValueError("EMPTY_THROUGHPUT_SAMPLE")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def aggregate_measurements(cfg: dict, workload: list[str], sample_shards: dict[int, list[str]],
                           population_unit_assignment: dict[int, list[str]], unit_counts: dict[str, int],
                           serial: dict, parallel: list[dict], parallel_wall_seconds: float,
                           discovery_wall_seconds: float, merge_seconds: float) -> dict:
    if len(parallel) != int(cfg["workload"]["shards"]):
        raise ValueError("PARALLEL_WORKER_CARDINALITY")
    if serial["processed_path_count"] != len(workload) or sum(row["processed_path_count"] for row in parallel) != len(workload):
        raise ValueError("AGGREGATE_PATH_COUNT_CONSERVATION")
    shard_counts = [len(sample_shards[index]) for index in sorted(sample_shards)]
    if sorted(row["processed_path_count"] for row in parallel) != sorted(shard_counts):
        raise ValueError("AGGREGATE_SHARD_COUNT_MISMATCH")
    full_count = int(cfg["topology"]["expected_full_dataset_count"])
    if sum(unit_counts.values()) != full_count:
        raise ValueError("FULL_DATASET_COUNT_CONTRACT_DRIFT")
    population_worker_counts = [sum(unit_counts[unit] for unit in population_unit_assignment[index])
                                for index in sorted(population_unit_assignment)]
    serial_costs = [row["seconds"] / row["records"] for row in serial["batch_measurements"] if row["records"]]
    parallel_costs = [row["seconds"] / row["records"] for worker in parallel
                      for row in worker["batch_measurements"] if row["records"]]
    serial_p95, parallel_p95 = p95(serial_costs), p95(parallel_costs)
    parallel_upper = max(parallel_costs)
    safety = float(cfg["workload"]["cache_and_extrapolation_safety_factor"])
    direct_read_eta = max(population_worker_counts) * parallel_upper * safety
    preflight_chain_eta = discovery_wall_seconds + direct_read_eta + merge_seconds
    observed_speedup = serial["elapsed_seconds"] / parallel_wall_seconds
    speedup_cap = float(cfg["feasibility"]["maximum_explainable_parallel_speedup"])
    explainable_speedup = min(speedup_cap, max(1.0, observed_speedup))
    r0_bound = float(cfg["feasibility"]["r0_projected_full_scan_seconds"]) / explainable_speedup
    conservative_eta = max(preflight_chain_eta, r0_bound)
    r0_seconds_per_dataset = (float(cfg["feasibility"]["r0_observed_elapsed_seconds"])
                              / float(cfg["feasibility"]["r0_observed_datasets"]))
    known_path_seconds_per_dataset = serial["elapsed_seconds"] / len(workload)
    allowed_factor = float(cfg["feasibility"]["maximum_allowed_known_path_speedup_vs_r0"])
    anomaly = known_path_seconds_per_dataset < r0_seconds_per_dataset / allowed_factor
    allocation = float(cfg["feasibility"]["allocation_seconds"])
    headroom = 1.0 - conservative_eta / allocation
    feasible = (not anomaly and conservative_eta <= float(cfg["feasibility"]["maximum_conservative_eta_seconds"])
                and headroom >= float(cfg["feasibility"]["minimum_headroom_fraction"]))
    return {"representative_path_count": len(workload), "sample_shard_path_counts": shard_counts,
            "sample_shard_max_to_mean_skew": max(shard_counts) / statistics.mean(shard_counts),
            "population_worker_dataset_counts": population_worker_counts,
            "population_worker_max_to_mean_skew": max(population_worker_counts) / statistics.mean(population_worker_counts),
            "serial_elapsed_seconds": serial["elapsed_seconds"], "parallel_wall_seconds": parallel_wall_seconds,
            "serial_records_per_second": len(workload) / serial["elapsed_seconds"],
            "parallel_records_per_second": len(workload) / parallel_wall_seconds,
            "parallel_speedup": observed_speedup, "explainable_parallel_speedup": explainable_speedup,
            "serial_p95_seconds_per_dataset": serial_p95, "parallel_p95_seconds_per_dataset": parallel_p95,
            "parallel_max_seconds_per_dataset": parallel_upper, "batch_eta_uses_conservative_max": True,
            "path_discovery_elapsed_seconds": discovery_wall_seconds, "merge_elapsed_seconds": merge_seconds,
            "path_discovery_included_in_eta": True, "direct_read_full_scan_eta_seconds": direct_read_eta,
            "preflight_full_chain_eta_seconds": preflight_chain_eta,
            "r0_observed_seconds_per_dataset": r0_seconds_per_dataset,
            "known_path_serial_seconds_per_dataset": known_path_seconds_per_dataset,
            "known_path_speedup_vs_r0": r0_seconds_per_dataset / known_path_seconds_per_dataset,
            "known_path_speed_anomaly_block": anomaly,
            "r0_parallel_lower_bound_eta_seconds": r0_bound,
            "conservative_parallel_full_scan_eta_seconds": conservative_eta,
            "estimated_headroom_fraction": headroom,
            "minimum_headroom_fraction": cfg["feasibility"]["minimum_headroom_fraction"],
            "throughput_preflight_feasible": feasible}


def package_hashes(root: Path, exp_id: str) -> dict[str, str]:
    paths = [root / "configs" / f"{exp_id}.yaml", root / "scripts/experiments" / exp_id / "shard_preflight.py",
             root / "scripts/experiments" / exp_id / "test_shard_preflight.py", root / "sbatch" / f"{exp_id}.sbatch"]
    return {str(path.relative_to(root)): sha256_file(path) for path in paths}


def create_payload_manifest(stage: Path) -> str:
    files = {str(path.relative_to(stage)): sha256_file(path) for path in sorted(stage.rglob("*"))
             if path.is_file() and path.name != "PAYLOAD_MANIFEST.json"}
    required = {"topology_units.tsv", "unit_sampling.tsv", "workload.tsv", "metrics.json", "report.json",
                "RUN_MANIFEST.json", "env.json"}
    if required - set(files):
        raise ValueError(f"PREFLIGHT_PAYLOAD_MISSING:{sorted(required - set(files))}")
    atomic_json(stage / "PAYLOAD_MANIFEST.json", {"schema_version": "SF-P3-SHARD-PREFLIGHT-PAYLOAD-1.1.0",
                "self_included": False, "files": files})
    return sha256_file(stage / "PAYLOAD_MANIFEST.json")


def verify_payload(stage: Path) -> str:
    manifest_path = stage / "PAYLOAD_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("self_included") is not False or "PAYLOAD_MANIFEST.json" in manifest.get("files", {}):
        raise ValueError("SELF_REFERENTIAL_PREFLIGHT_PAYLOAD")
    for relpath, expected in manifest["files"].items():
        if not (stage / relpath).is_file() or sha256_file(stage / relpath) != expected:
            raise ValueError(f"PREFLIGHT_PAYLOAD_DRIFT:{relpath}")
    return sha256_file(manifest_path)


def finalize_preview(root: Path, cfg: dict, status: str, attempt_id: str, metrics: dict, report: dict,
                     extra_paths: tuple[Path, ...] = ()) -> None:
    preview = root / cfg["preview_root"]
    sentinel = ensure_slurm_log_dir(root, cfg)
    atomic_json(preview / "metrics.json", metrics)
    atomic_json(preview / "report.json", report)
    atomic_text(preview / "STATUS", status + "\n")
    atomic_json(preview / "TERMINAL_STATE.json", {"schema_version": "SF-P3-SHARD-PREFLIGHT-TERMINAL-1.1.0",
                "exp_id": cfg["exp_id"], "status": status, "attempt_id": attempt_id,
                "semantic_success": bool(metrics.get("semantic_success", False)), **authorization_flags(),
                "unlisted_artifacts_are_superseded": True})
    paths = [preview / name for name in ("STATUS", "TERMINAL_STATE.json", "metrics.json", "report.json",
                                          "input_manifest.json", "static_contract.json")] + [sentinel] + list(extra_paths)
    if any(not path.is_file() for path in paths):
        raise ValueError("PREFLIGHT_PREVIEW_ARTIFACT_MISSING")
    unique = {str(path.relative_to(root)): path for path in paths}
    atomic_text(preview / "output_manifest.sha256",
                "".join(f"{sha256_file(unique[name])}  {name}\n" for name in sorted(unique)))
    for line in (preview / "output_manifest.sha256").read_text(encoding="utf-8").splitlines():
        expected, relpath = line.split("  ", 1)
        if sha256_file(root / relpath) != expected:
            raise ValueError(f"PREFLIGHT_PREVIEW_MANIFEST_DRIFT:{relpath}")


def static_preview(root: Path, cfg: dict) -> None:
    _source, units, input_audit = validate_inputs(root, cfg)
    preview = root / cfg["preview_root"]
    preview.mkdir(parents=True, exist_ok=True)
    sentinel = ensure_slurm_log_dir(root, cfg)
    static = {"schema_version": "SF-P3-SHARD-PREFLIGHT-STATIC-1.1.0",
              "package_hashes": package_hashes(root, cfg["exp_id"]), "input_contract": input_audit,
              "topology_units": units, "gpus": 0, "formal_slurm_required": True,
              "slurm_log_dir_precreated": str(sentinel.parent.relative_to(root)),
              "login_node_real_dataset_scan_executed": False}
    metrics = {"profile": cfg["profile"], "status": "IMPLEMENTED_NOT_RUN", "primary_metric": 0.0,
               "semantic_success": False, "throughput_measurement_executed": 0, "claim_eligible": False,
               **authorization_flags(), **input_audit}
    report = {"exp_id": cfg["exp_id"], "status": "IMPLEMENTED_NOT_RUN", "semantic_success": False,
              "answer": "NOT_RUN", "scope": "throughput_and_shard_correctness_only", "input_contract": input_audit}
    atomic_json(preview / "input_manifest.json", static)
    atomic_json(preview / "static_contract.json", static)
    finalize_preview(root, cfg, "IMPLEMENTED_NOT_RUN", "static-preview", metrics, report)


def validate_formal_guard(root: Path, cfg: dict) -> str:
    job_id = os.environ.get("SLURM_JOB_ID", "")
    if not job_id.isdigit() or int(job_id) <= 0:
        raise ValueError("FORMAL_SLURM_GUARD")
    lock_job = root / cfg["preview_root"] / cfg["owner_lock_name"] / "job_id"
    if not lock_job.is_file() or lock_job.read_text(encoding="utf-8").strip() != job_id:
        raise ValueError("FORMAL_OWNER_LOCK_MISMATCH")
    return job_id


def prepare_running(root: Path, cfg: dict, attempt_id: str) -> tuple[Path, list[str], dict]:
    job_id = validate_formal_guard(root, cfg)
    source, units, input_audit = validate_inputs(root, cfg)
    preview = root / cfg["preview_root"]
    manifest = {"schema_version": "SF-P3-SHARD-PREFLIGHT-RUNNING-1.1.0", "attempt_id": attempt_id,
                "slurm_job_id": job_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "package_hashes": package_hashes(root, cfg["exp_id"]), "gpus": 0}
    env = {"python_version": sys.version, "h5py_version": __import__("h5py").__version__,
           "slurm_job_id": job_id, "gpus": 0}
    atomic_json(preview / "RUNNING_MANIFEST.json", manifest)
    atomic_json(preview / "env.json", env)
    atomic_json(preview / "input_manifest.json", manifest)
    atomic_json(preview / "static_contract.json", {"input_contract": input_audit,
                "package_hashes": package_hashes(root, cfg["exp_id"]), "gpus": 0})
    metrics = {"profile": cfg["profile"], "status": "RUNNING", "primary_metric": 0.0,
               "semantic_success": False, "throughput_measurement_executed": 0,
               **authorization_flags(), **input_audit}
    finalize_preview(root, cfg, "RUNNING", attempt_id, metrics, {"exp_id": cfg["exp_id"], "status": "RUNNING"},
                     (preview / "RUNNING_MANIFEST.json", preview / "env.json"))
    return source, units, input_audit


def terminal_failure(root: Path, cfg: dict, attempt_id: str, reason: str, error_type: str = "RuntimeError") -> None:
    """Replace RUNNING atomically after a post-prepare shell or Python failure."""
    preview = root / cfg["preview_root"]
    failure = preview / f"failure.{attempt_id}.json"
    atomic_json(failure, {"error_type": error_type, "error": reason, "semantic_success": False})
    metrics = {"profile": cfg["profile"], "status": "PREFLIGHT_FAILED", "primary_metric": 0.0,
               "semantic_success": False, "throughput_measurement_executed": 0,
               **authorization_flags(), "error": reason}
    report = {"exp_id": cfg["exp_id"], "status": "PREFLIGHT_FAILED", "semantic_success": False,
              "answer": "NOT_ESTABLISHED", "scientific_recovery_or_absence_conclusion": None, "error": reason}
    finalize_preview(root, cfg, "PREFLIGHT_FAILED", attempt_id, metrics, report, (failure,))


def terminal_infeasible(root: Path, cfg: dict, attempt_id: str, reason: str) -> tuple[str, dict]:
    """Performance timeout is an informative engineering negative, not an integrity failure."""
    metrics = {"profile": cfg["profile"], "status": "PREFLIGHT_INFEASIBLE", "primary_metric": -1.0,
               "semantic_success": True, "valid_negative": True, "throughput_measurement_executed": 1,
               "throughput_preflight_feasible": False, "performance_budget_exceeded": True,
               **authorization_flags(), "infeasible_reason": reason}
    report = {"exp_id": cfg["exp_id"], "status": "PREFLIGHT_INFEASIBLE", "semantic_success": True,
              "answer": "ENGINEERING_INFEASIBLE", "scientific_recovery_or_absence_conclusion": None,
              "reason": reason}
    finalize_preview(root, cfg, "PREFLIGHT_INFEASIBLE", attempt_id, metrics, report)
    return "PREFLIGHT_INFEASIBLE", metrics


def run_formal(root: Path, cfg: dict, attempt_id: str) -> tuple[str, dict]:
    preview = root / cfg["preview_root"]
    attempts = preview / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    final, stage = attempts / attempt_id, attempts / (attempt_id + ".tmp")
    try:
        if final.exists() or stage.exists():
            raise ValueError("DIRTY_PREFLIGHT_ATTEMPT_REFUSED")
        stage.mkdir()
        source, units, input_audit = prepare_running(root, cfg, attempt_id)
        workers = int(cfg["workload"]["shards"])
        first_assignment = round_robin_unit_assignment(units, workers)
        first, first_wall, first_merge = launch_inventory_rebuild(
            source, units, first_assignment, stage / "inventory_rebuild_1",
            float(cfg["materialization"]["per_rebuild_timeout_seconds"]))
        partition_planning_started = time.monotonic()
        first_paths, unit_counts, first_inventory_hash = inventory_identity(first, units)
        if len(first_paths) != int(cfg["topology"]["expected_full_dataset_count"]):
            raise ValueError(f"FULL_DATASET_COUNT_CONTRACT_DRIFT:{len(first_paths)}")
        second_assignment = balanced_unit_assignment(units, unit_counts, workers)
        first_partition_planning = time.monotonic() - partition_planning_started
        second, second_wall, second_merge = launch_inventory_rebuild(
            source, units, second_assignment, stage / "inventory_rebuild_2",
            float(cfg["materialization"]["per_rebuild_timeout_seconds"]))
        workload_build_started = time.monotonic()
        second_paths, second_counts, second_inventory_hash = inventory_identity(second, units)
        if first_paths != second_paths or unit_counts != second_counts or first_inventory_hash != second_inventory_hash:
            raise ValueError("INDEPENDENT_INVENTORY_REBUILD_DRIFT")
        count = int(cfg["workload"]["representative_dataset_paths"])
        workload, sampling_audit = build_stratified_workload(first, units, count)
        second_workload, second_sampling_audit = build_stratified_workload(second, units, count)
        workload_hash = sha256_text("".join(path + "\n" for path in workload))
        if workload != second_workload or sampling_audit != second_sampling_audit:
            raise ValueError("INDEPENDENT_WORKLOAD_REBUILD_DRIFT")
        sample_shards = partition_workload(workload, workers)
        workload_build_seconds = time.monotonic() - workload_build_started
        write_tsv(stage / "topology_units.tsv",
                  [{"unit_index": index, "unit": unit, "dataset_count": unit_counts[unit],
                    "formal_worker": next(worker for worker, values in second_assignment.items() if unit in values)}
                   for index, unit in enumerate(units)],
                  ["unit_index", "unit", "dataset_count", "formal_worker"])
        write_tsv(stage / "unit_sampling.tsv", sampling_audit,
                  ["unit", "population_count", "sample_count", "sample_fraction", "inverse_probability_weight",
                   "selected_min_index", "selected_max_index", "selected_span_fraction", "path_depth_min",
                   "path_depth_max", "locality_q1", "locality_q2", "locality_q3", "locality_q4"])
        write_tsv(stage / "workload.tsv",
                  [{"dataset_path": path, "shard": shard_for_path(path, workers)} for path in workload],
                  ["dataset_path", "shard"])
        workdir = stage / "worker_inputs"
        workdir.mkdir()
        serial_input = write_workload(workdir / "serial.json", workload, "serial")
        shard_payloads = [write_workload(workdir / f"shard_{index}.json", sample_shards[index], str(index))
                          for index in range(workers)]
        executable, python = str(Path(__file__).resolve()), sys.executable
        serial_stage = stage / "worker_serial"
        serial_command = [python, executable, "--worker", "--source", str(source), "--workload",
                          str(workdir / "serial.json"), "--worker-stage", str(serial_stage),
                          "--batch-size", str(cfg["workload"]["batch_size"])]
        serial_results, _ = launch_children([serial_command], [serial_stage],
                                            float(cfg["workload"]["serial_child_timeout_seconds"]),
                                            stage / "serial_logs")
        validate_worker_results(serial_results, [serial_input])
        parallel_stages = [stage / f"worker_{index}" for index in range(workers)]
        parallel_commands = [[python, executable, "--worker", "--source", str(source), "--workload",
                              str(workdir / f"shard_{index}.json"), "--worker-stage", str(parallel_stages[index]),
                              "--batch-size", str(cfg["workload"]["batch_size"])] for index in range(workers)]
        parallel_results, parallel_wall = launch_children(
            parallel_commands, parallel_stages, float(cfg["workload"]["parallel_child_timeout_seconds"]),
            stage / "parallel_logs")
        validate_worker_results(parallel_results, shard_payloads)
        discovery_wall = max(first_wall, second_wall)
        merge_seconds = max(first_merge, second_merge) + first_partition_planning + workload_build_seconds
        measurement = aggregate_measurements(cfg, workload, sample_shards, second_assignment, unit_counts,
                                             serial_results[0], parallel_results, parallel_wall,
                                             discovery_wall, merge_seconds)
        status = "PREFLIGHT_FEASIBLE" if measurement["throughput_preflight_feasible"] else "PREFLIGHT_INFEASIBLE"
        metrics = {"profile": cfg["profile"], "status": status,
                   "primary_metric": measurement["estimated_headroom_fraction"], "semantic_success": True,
                   "valid_negative": status == "PREFLIGHT_INFEASIBLE", "throughput_measurement_executed": 1,
                   "claim_eligible": False, **authorization_flags(), **input_audit, **measurement,
                   "canonical_inventory_path_count": len(first_paths),
                   "canonical_inventory_ordered_paths_sha256": first_inventory_hash,
                   "canonical_inventory_independent_rebuilds": 2,
                   "canonical_inventory_rebuild_hash_match": True,
                   "workload_ordered_paths_sha256": workload_hash,
                   "workload_independent_rebuild_hash_match": True,
                   "sampled_unit_count": len(sampling_audit),
                   "all_nonempty_units_sampled": all(row["sample_count"] > 0 for row in sampling_audit),
                   "inventory_rebuild_elapsed_seconds": [first_wall, second_wall],
                   "inventory_rebuild_merge_seconds": [first_merge, second_merge],
                   "unit_partition_planning_seconds": first_partition_planning,
                   "workload_hash_and_shard_build_seconds": workload_build_seconds,
                   "shard_workload_hashes": [payload["ordered_paths_sha256"] for payload in shard_payloads]}
        if not all(math.isfinite(float(value)) for value in metrics.values() if isinstance(value, (int, float))):
            raise ValueError("NONFINITE_PREFLIGHT_METRIC")
        report = {"exp_id": cfg["exp_id"], "status": status, "semantic_success": True,
                  "answer": "ENGINEERING_FEASIBLE" if status == "PREFLIGHT_FEASIBLE" else "ENGINEERING_INFEASIBLE",
                  "scope": "throughput_and_shard_correctness_only", "metrics": metrics,
                  "sampling_audit": sampling_audit,
                  "formal_r0_shape": "35 topology units assigned by exact count to four independent read-only workers; each worker discovers and scans its own subtree; parent merges only after zero exits",
                  "scientific_recovery_or_absence_conclusion": None}
        env = {"python_version": sys.version, "h5py_version": __import__("h5py").__version__,
               "slurm_job_id": os.environ["SLURM_JOB_ID"], "gpus": 0}
        run_manifest = {"schema_version": "SF-P3-SHARD-PREFLIGHT-RUN-1.1.0", "attempt_id": attempt_id,
                        "slurm_job_id": os.environ["SLURM_JOB_ID"],
                        "package_hashes": package_hashes(root, cfg["exp_id"]),
                        "source_size_bytes": source.stat().st_size,
                        "canonical_inventory_ordered_paths_sha256": first_inventory_hash,
                        "workload_ordered_paths_sha256": workload_hash, "gpus": 0}
        atomic_json(stage / "metrics.json", metrics)
        atomic_json(stage / "report.json", report)
        atomic_json(stage / "env.json", env)
        atomic_json(stage / "RUN_MANIFEST.json", run_manifest)
        create_payload_manifest(stage)
        verify_payload(stage)
        os.replace(stage, final)
        verify_payload(final)
        atomic_json(preview / "input_manifest.json", run_manifest)
        atomic_json(preview / "static_contract.json", {"package_hashes": package_hashes(root, cfg["exp_id"]),
                    "input_contract": input_audit, "gpus": 0})
        finalize_preview(root, cfg, status, attempt_id, metrics, report, (final / "PAYLOAD_MANIFEST.json",))
        return status, metrics
    except PerformanceBudgetInfeasible as exc:
        return terminal_infeasible(root, cfg, attempt_id, str(exc))
    except Exception as exc:
        failure = stage / "failure.json" if stage.exists() else preview / f"failure.{attempt_id}.json"
        atomic_json(failure, {"error_type": type(exc).__name__, "error": str(exc),
                              "traceback": traceback.format_exc(), "semantic_success": False})
        terminal_failure(root, cfg, attempt_id, str(exc), type(exc).__name__)
        raise


def terminal_exit_code(status: str) -> int:
    return 0 if status in {"IMPLEMENTED_NOT_RUN", "PREFLIGHT_FEASIBLE", "PREFLIGHT_INFEASIBLE"} else 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--attempt-id", default="static-preview")
    parser.add_argument("--static-check-only", action="store_true")
    parser.add_argument("--prepare-running-only", action="store_true")
    parser.add_argument("--finalize-failed-only", action="store_true")
    parser.add_argument("--failure-reason", default="sbatch_post_prepare_failure")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--inventory-worker", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--workload", type=Path)
    parser.add_argument("--units", type=Path)
    parser.add_argument("--worker-stage", type=Path)
    parser.add_argument("--batch-size", type=int)
    args = parser.parse_args()
    if args.worker:
        if not all((args.source, args.workload, args.worker_stage, args.batch_size)):
            raise SystemExit("worker arguments incomplete")
        worker_read(args.source, args.workload, args.worker_stage, args.batch_size)
        return
    if args.inventory_worker:
        if not all((args.source, args.units, args.worker_stage)):
            raise SystemExit("inventory worker arguments incomplete")
        inventory_worker(args.source, args.units, args.worker_stage)
        return
    if args.config is None:
        raise SystemExit("--config required")
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(cfg["project_root"]).resolve()
    if args.static_check_only:
        static_preview(root, cfg)
        print(json.dumps({"status": "IMPLEMENTED_NOT_RUN", "gpus": 0}, sort_keys=True))
        return
    if args.prepare_running_only:
        prepare_running(root, cfg, args.attempt_id)
        print(json.dumps({"status": "RUNNING", "gpus": 0}, sort_keys=True))
        return
    if args.finalize_failed_only:
        validate_formal_guard(root, cfg)
        terminal_failure(root, cfg, args.attempt_id, args.failure_reason, "SbatchPostPrepareFailure")
        print(json.dumps({"status": "PREFLIGHT_FAILED", "semantic_success": False}, sort_keys=True))
        return
    try:
        status, _metrics = run_formal(root, cfg, args.attempt_id)
    except Exception as exc:
        print(json.dumps({"status": "PREFLIGHT_FAILED", "semantic_success": False,
                          "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps({"status": status, "gpus": 0}, sort_keys=True))
    raise SystemExit(terminal_exit_code(status))


if __name__ == "__main__":
    main()
