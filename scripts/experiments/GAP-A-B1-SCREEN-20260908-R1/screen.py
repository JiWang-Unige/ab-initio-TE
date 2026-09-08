#!/usr/bin/env python3
"""Prospective, bounded A/B1 screen; no CAL fitting or sealed inputs."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/experiments/GAP-BRIDGE-P3-NT-R2"))
import prepare_pair as pair

base = pair.stage1
EID = "GAP-A-B1-SCREEN-20260908-R1"
OUT = ROOT / "outputs" / EID
MANIFEST = ROOT / "outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv"
REGIONS = ROOT / "outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1"
MISSING = ROOT / "outputs/GAP-BRIDGE-A-COVERAGE-20260906-R1/audit-20260906-r1/partial_candidates.tsv.gz"
P3 = ROOT / "outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet"
NT = ROOT / "software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42"
P3_STATS = ROOT / "outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/train-20260902-r1/scalar_stats.json"
NT_STATS = ROOT / "outputs/GAP-BRIDGE-P3-NT-R2/smoke-20260905-r1/nt_scalar_stats.json"
SEEDS = (17, 42, 20260902)
ARMS = ("H0-O", "HN-O", "H0-S")
BLOCK_WINDOWS = 64
BATCH = 512
MICRO = 128


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(data, handle, indent=2, allow_nan=False)
        handle.write("\n")


def log(event, **kwargs):
    print(json.dumps({"event": event, **kwargs}, allow_nan=False), flush=True)


def block_id(start, end):
    return ((int(end) + 256 - 1) // 8192) // BLOCK_WINDOWS


def sample_blocks(universe):
    rng = np.random.default_rng(20260908)
    return {seq: sorted(rng.choice(sorted(universe[seq]),
                size=math.ceil(len(universe[seq]) / 8), replace=False).tolist())
            for seq in ("chr3", "chr5")}


def geometry(row):
    return dict(candidate_id=row["candidate_id"], seqid=row["seqid"],
        gap_start=int(row["gap_start"]), gap_end=int(row["gap_end"]),
        gap_length=int(row["gap_length"]),
        left_run_length=int(row["left_run_end"]) - int(row["left_run_start"]),
        right_run_length=int(row["right_run_end"]) - int(row["right_run_start"]),
        span_length=int(row["right_run_end"]) - int(row["left_run_start"]),
        # DEV target fields are not projected into feature/inference records.
        target=0.0, stratum=row["length_stratum"])


def prepare(out=OUT):
    if (out / "plan.json").exists():
        raise ValueError("plan already frozen; do not regenerate")
    universe = {seq: set() for seq in ("chr3", "chr5")}
    dev = []
    with MANIFEST.open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            seq, role = row["seqid"], row["role"]
            if seq in universe and role == "TRAIN":
                universe[seq].add(block_id(row["gap_start"], row["gap_end"]))
            elif seq == "chr13" and role == "DEV":
                dev.append(geometry(row))
    selected = sample_blocks(universe)
    with gzip.open(MISSING, "rt") as handle:
        missing = {r["candidate_id"] for r in csv.DictReader(handle, delimiter="\t")
                   if r["role"] in ("TRAIN", "DEV")}
    train_all = base.load_training_candidates(MANIFEST)
    selected_train = [r for r in train_all if block_id(r.gap_start, r.gap_end) in selected[r.seqid]]
    excluded = [r.candidate_id for r in selected_train if r.candidate_id in missing]
    train = [asdict(r) for r in selected_train if r.candidate_id not in missing]
    if any(r["candidate_id"] in missing for r in dev):
        raise ValueError("unexpected DEV coverage missing; do not silently drop DEV")
    if len(dev) != 60574 or set(r["stratum"] for r in train) != set(base.LENGTH_STRATA):
        raise ValueError("DEV completeness or TRAIN six-stratum eligibility differs")
    groups = defaultdict(list)
    for role, rows in (("TRAIN", train), ("DEV", dev)):
        for r in rows:
            groups[(role, r["seqid"], block_id(r["gap_start"], r["gap_end"]))].append(r)
    blocks = []
    for (role, seq, block), rows in sorted(groups.items(), key=lambda z: (z[0][0] != "TRAIN", z[0][1], z[0][2])):
        rows.sort(key=lambda r: (r["gap_start"] - 256, r["gap_end"] + 256, r["candidate_id"]))
        starts = sorted({w for r in rows for w in range((r["gap_start"] - 256) // 8192 * 8192,
                    (r["gap_end"] + 255) // 8192 * 8192 + 1, 8192)})
        blocks.append(dict(key=f"{role}-{seq}-{block:05d}", role=role, seqid=seq, block=block,
                           starts=starts, rows=rows))
    estimate = (len(train) + len(dev)) * (144 * 1024 + 10) * 4
    if estimate > 180 * 1024**3:
        raise ValueError("planned feature cache exceeds 180GiB screen cap")
    plan = dict(experiment_id=EID, sampling_seed=20260908, selected_blocks=selected,
        original_train_known=len(train_all), sampled_train_before_coverage=len(selected_train),
        excluded_train_ids=excluded, training_rows=len(train), dev_rows=len(dev),
        feature_bytes_estimate=estimate, blocks=blocks,
        candidate_manifest=str(MANIFEST), sealed_or_cal_metrics_read=False)
    write_json(out / "plan.json", plan)
    log("PLAN_FROZEN", **{k: v for k, v in plan.items() if k not in ("blocks", "selected_blocks", "excluded_train_ids")})
    return plan


def load_plan(out=OUT):
    return json.loads((out / "plan.json").read_text())


def selected_plan_blocks(plan, smoke=False):
    return [b for b in plan["blocks"] if b["role"] == "TRAIN"][:2] if smoke else plan["blocks"]


def cache_path(out, kind, block):
    return out / "cache" / kind / (block["key"] + ".npz")


def save_arrays(path, **arrays):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".partial")
    # Interrupted partial files are evidence; never overwrite them automatically.
    with pending.open("xb") as handle:
        np.savez(handle, **arrays)
    pending.rename(path)


def region_map(blocks):
    starts = defaultdict(set)
    for b in blocks:
        starts[b["seqid"]].update(b["starts"])
    return {(seq, start): (end, sequence) for seq, wanted in starts.items()
            for start, end, sequence in pair.selected_regions(REGIONS / seq / "region.jsonl.gz", seq, wanted)}


def strict_loader():
    for directory in ("PIPE-TEFM-SEG-SF-20260618", "PIPE-TEFM-SUPP-20260617"):
        sys.path.insert(0, str(ROOT / "pipelines" / directory))
    return pair.load_module(ROOT / "pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py", "screen_strict")


def extract(out=OUT, smoke=False):
    import torch
    plan = load_plan(out)
    blocks = selected_plan_blocks(plan, smoke)
    started = time.perf_counter()
    stats = {"nt_seconds": 0.0, "p3_seconds": 0.0, "nt_windows": 0, "p3_windows": 0,
             "rows_written": 0, "reused_feature_blocks": 0}
    needed_nt = [b for b in blocks if not cache_path(out, "features", b).exists()
                 and not cache_path(out, "nt", b).exists()]
    if needed_nt:
        regions = region_map(needed_nt)
        strict = strict_loader()
        model, tokenizer, metadata = strict.load_trained_model(str(NT))
        device = torch.device("cuda")
        model.to(device).eval().requires_grad_(False)
        for b in needed_nt:
            clock = time.perf_counter()
            probabilities, coverages, ends = [], [], []
            for start in b["starts"]:
                end, sequence = regions[b["seqid"], start]
                ps, cs = [], []
                for offset in range(0, len(sequence), 4096):
                    p, c = pair.native_nt_window(strict, model, tokenizer,
                          sequence[offset:offset+4096], device, metadata["token_label_mode"])
                    ps.append(p)
                    cs.append(c)
                    stats["nt_windows"] += 1
                p, c = np.concatenate(ps), np.concatenate(cs)
                probabilities.append(np.pad(p, (0, 8192-len(p))))
                coverages.append(np.pad(c, (0, 8192-len(c))))
                ends.append(end)
            track = {s: c[:e-s] for s, e, c in zip(b["starts"], ends, coverages)}
            for row in b["rows"]:
                candidate = base.CandidateRow(**row)
                pair.require_crop_coverage(pair.crop_track(track, candidate), candidate)
            save_arrays(cache_path(out, "nt", b), probability=np.asarray(probabilities, dtype=np.float32),
                coverage=np.asarray(coverages, dtype=bool), starts=np.asarray(b["starts"]), ends=np.asarray(ends))
            stats["nt_seconds"] += time.perf_counter() - clock
            log("NT_BLOCK", block=b["key"], windows=len(b["starts"]), seconds=time.perf_counter()-clock)
        del model, tokenizer, regions
        torch.cuda.empty_cache()
    needed_p3 = [b for b in blocks if not cache_path(out, "features", b).exists()]
    stats["reused_feature_blocks"] = len(blocks) - len(needed_p3)
    if needed_p3:
        regions = region_map(needed_p3)
        model, tokenizer, _, device, _ = base.load_c5().load_p3_model(P3)
        model.eval().requires_grad_(False)
        p3_stats, nt_stats = json.loads(P3_STATS.read_text()), json.loads(NT_STATS.read_text())
        for b in needed_p3:
            clock = time.perf_counter()
            features = {}
            for start in b["starts"]:
                end, sequence = regions[b["seqid"], start]
                features[start] = base._p3_forward_window(model, tokenizer, device, start, end, sequence)
                stats["p3_windows"] += 1
            with np.load(cache_path(out, "nt", b)) as nt:
                track = {s: p[:e-s] for s, e, p in zip(nt["starts"], nt["ends"], nt["probability"])}
                coverage = {s: c[:e-s] for s, e, c in zip(nt["starts"], nt["ends"], nt["coverage"])}
            x = np.zeros((len(b["rows"]), 144, 1024), dtype=np.float32)
            g = np.zeros((len(b["rows"]), 10), dtype=np.float32)
            for i, row in enumerate(b["rows"]):
                c = base.CandidateRow(**row)
                last = (c.crop_end-1)//8192*8192
                sequence, logits, latent = base.assemble_crop(features.get(last-8192), features[last], c.crop_start, c.crop_end)
                pair.require_crop_coverage(pair.crop_track(coverage, c), c)
                h0, hn, g0, gn = pair.pair_inputs(base.build_channels(sequence, logits, latent, c),
                    base.standardized_scalars(c, p3_stats), pair.crop_track(track, c), c, nt_stats)
                if not (np.array_equal(h0[:143], hn[:143]) and np.array_equal(g0[:7], gn[:7])
                        and not h0[143].any() and not g0[7:].any()):
                    raise ValueError("actual paired input disagreement")
                x[i], g[i] = hn, gn
            save_arrays(cache_path(out, "features", b), x=x, g=g,
                        ids=np.asarray([r["candidate_id"] for r in b["rows"]]))
            stats["p3_seconds"] += time.perf_counter() - clock
            stats["rows_written"] += len(b["rows"])
            log("P3_FEATURE_BLOCK", block=b["key"], rows=len(b["rows"]), seconds=time.perf_counter()-clock)
        del model, tokenizer, regions
        torch.cuda.empty_cache()
    stats["total_seconds"] = time.perf_counter() - started
    write_json(out / ("smoke_extract.json" if smoke else "extract.json"), stats)
    return stats


def model_module():
    # A separate loaded module instance; historical implementation/files are unchanged.
    module = base.load_stage1_model()
    module.CHANNELS = 144
    module.GEOMETRY_SCALARS = 10
    return module


def new_heads(device):
    import torch
    module = model_module()
    heads, optimizers = {}, {}
    for seed in SEEDS:
        for arm in ARMS:
            torch.manual_seed(seed)
            key = f"{arm}__seed{seed}"
            heads[key] = module.GapHead().to(device)
            optimizers[key] = torch.optim.AdamW(heads[key].parameters(), lr=3e-4, weight_decay=1e-4, betas=(0.9, 0.999))
        states = [heads[f"{arm}__seed{seed}"].state_dict() for arm in ARMS]
        if any(not torch.equal(states[0][name], state[name]) for name in states[0] for state in states[1:]):
            raise ValueError("unpaired initial heads")
    return heads, optimizers


def prepared(x, g, arm):
    if arm != "HN-O":
        x, g = x.clone(), g.clone()
        x[:, 143] = 0
        g[:, 7:] = 0
    return x, g


def update(head, optimizer, x, g, target, weights, arm, seed, epoch, update_index):
    import torch
    import torch.nn.functional as F
    optimizer.zero_grad(set_to_none=True)
    total = 0.0
    for start in range(0, len(x), MICRO):
        stop = min(start + MICRO, len(x))
        torch.manual_seed(seed + epoch*100000 + update_index*10 + start//MICRO)
        xx, gg = prepared(x[start:stop].cuda(), g[start:stop].cuda(), arm)
        logits = head.forward_prepared(xx, gg)
        loss = (F.binary_cross_entropy_with_logits(logits, target[start:stop].cuda(), reduction="none")
                * weights[start:stop].cuda()).sum() / len(x)
        if not torch.isfinite(loss):
            raise ValueError("nonfinite training loss")
        loss.backward()
        total += float(loss.detach().cpu())
    torch.nn.utils.clip_grad_norm_(head.parameters(), 1.0)
    optimizer.step()
    return total


def load_feature(out, b):
    import torch
    with np.load(cache_path(out, "features", b)) as data:
        if data["ids"].tolist() != [r["candidate_id"] for r in b["rows"]]:
            raise ValueError("feature candidate alignment differs")
        return torch.from_numpy(data["x"]), torch.from_numpy(data["g"])


def training(out=OUT, smoke=False):
    import torch
    started = time.perf_counter()
    plan = load_plan(out)
    all_blocks = [b for b in plan["blocks"] if b["role"] == "TRAIN"]
    blocks = all_blocks[:2] if smoke else all_blocks
    candidates = [base.CandidateRow(**r) for b in all_blocks for r in b["rows"]]
    weights = base.global_sample_weights(model_module(), candidates)
    heads, optimizers = new_heads("cuda")
    directory = out / ("smoke_training" if smoke else "training")
    directory.mkdir(exist_ok=False)
    summaries = []
    # The ordered pair shares each loaded batch. The shuffled comparator has its own block flow.
    groups = [[f"{arm}__seed{s}" for s in SEEDS for arm in ARMS[:2]],
              *[[f"H0-S__seed{s}"] for s in SEEDS]]
    for epoch in range(1 if smoke else 2):
        for keys in groups:
            order = list(range(len(blocks)))
            if keys[0].startswith("H0-S"):
                seed = int(keys[0].split("seed")[1])
                order = np.random.default_rng(seed + epoch).permutation(order).tolist()
            sums = {key: 0.0 for key in keys}
            count, updates = 0, 0
            group_start = time.perf_counter()
            for index in order:
                b = blocks[index]
                x, g = load_feature(out, b)
                targets = torch.tensor([r["target"] for r in b["rows"]], dtype=torch.float32)
                w = torch.tensor([weights[r["candidate_id"]] for r in b["rows"]], dtype=torch.float32)
                for left in range(0, len(x), BATCH):
                    right = min(left+BATCH, len(x))
                    for key in keys:
                        arm, seed = key.split("__seed")
                        sums[key] += update(heads[key], optimizers[key], x[left:right], g[left:right],
                            targets[left:right], w[left:right], arm, int(seed), epoch, updates) * (right-left)
                    updates += 1
                    count += right-left
                log("TRAIN_BLOCK", epoch=epoch+1, heads=keys, block=b["key"], samples=count, updates=updates)
            expected = sum(len(b["rows"]) for b in blocks)
            if count != expected:
                raise ValueError("training did not consume every selected row exactly once")
            summary = dict(epoch=epoch+1, heads=keys, samples_per_head=count, updates_per_head=updates,
                           mean_weighted_loss={k: v/count for k, v in sums.items()},
                           seconds=time.perf_counter()-group_start)
            summaries.append(summary)
            write_json(directory / f"epoch{epoch+1}-{keys[0]}.json", summary)
        torch.save({key: {name: value.detach().cpu() for name, value in head.state_dict().items()}
                    for key, head in heads.items()}, directory / f"epoch{epoch+1}.pt")
    result = dict(status="ENGINEERING_COMPLETE", smoke=smoke, summaries=summaries,
        seconds=time.perf_counter()-started, rows=sum(len(b["rows"]) for b in blocks),
        paired_initialization=True, feature_cache_float32=True, cal_or_sealed_scored=False)
    write_json(directory / "summary.json", result)
    return result


def predict(out=OUT):
    import torch
    plan = load_plan(out)
    heads, _ = new_heads("cuda")
    states = torch.load(out / "training/epoch2.pt", map_location="cpu", weights_only=True)
    for key, head in heads.items():
        head.load_state_dict(states[key])
        head.eval()
    directory = out / "predictions"
    directory.mkdir(exist_ok=False)
    for b in [b for b in plan["blocks"] if b["role"] == "DEV"]:
        x, g = load_feature(out, b)
        predictions = {key: [] for key in heads}
        for left in range(0, len(x), MICRO):
            xx, gg = x[left:left+MICRO].cuda(), g[left:left+MICRO].cuda()
            with torch.no_grad():
                for key, head in heads.items():
                    arm = key.split("__seed")[0]
                    ax, ag = prepared(xx, gg, arm)
                    predictions[key].append(head.forward_prepared(ax, ag).cpu().numpy())
        save_arrays(directory / (b["key"] + ".npz"), ids=np.asarray([r["candidate_id"] for r in b["rows"]]),
                    **{k: np.concatenate(v) for k, v in predictions.items()})
        log("DEV_PREDICTED", block=b["key"], rows=len(b["rows"]))
    write_json(directory / "complete.json", dict(dev_rows=plan["dev_rows"], cal_or_sealed_scored=False))


def action_ap(scores, positive, negative):
    # Exact-tie grouped implementation in O(n log n), matching the frozen metric.
    order = np.argsort(-np.asarray(scores), kind="stable")
    scores, positive, negative = np.asarray(scores)[order], np.asarray(positive)[order], np.asarray(negative)[order]
    if positive.sum() <= 0:
        return None
    ends = np.r_[np.flatnonzero(scores[:-1] != scores[1:]), len(scores)-1]
    cp, cn = positive.cumsum()[ends], negative.cumsum()[ends]
    dp = np.diff(np.r_[0.0, cp])
    return float(np.sum(dp/positive.sum()*cp/(cp+cn)))


def metrics(logits, positive, negative):
    logits, positive, negative = (np.asarray(v, dtype=np.float64) for v in (logits, positive, negative))
    if not len(logits):
        return None
    if not all(np.isfinite(v).all() for v in (logits, positive, negative)):
        raise ValueError("nonfinite prediction or endpoint mass")
    length = positive + negative
    if np.any(length <= 0):
        raise ValueError("known endpoint length must be positive")
    p = 1/(1+np.exp(-np.clip(logits, -700, 700)))
    target = negative/length
    mse = float(np.sum(length*(p-target)**2)/length.sum())
    irreducible = float(np.sum(length*target*(1-target))/length.sum())
    brier = float(np.sum(negative*(1-p)**2+positive*p**2)/length.sum())
    if not math.isclose(brier, mse+irreducible, abs_tol=1e-12, rel_tol=1e-12):
        raise ValueError("Brier decomposition mismatch")
    return dict(rows=len(logits), bp=int(length.sum()), fraction_mse=mse, irreducible=irreducible,
                pseudo_base_brier=brier, action_ap=action_ap(1-p, positive, negative))


def decision(control, novel):
    if control["fraction_mse"] <= 0 or control["action_ap"] is None or novel["action_ap"] is None:
        return dict(status="UNDETERMINED", relative_mse_decrease=None)
    decrease = (control["fraction_mse"]-novel["fraction_mse"])/control["fraction_mse"]
    return dict(status="SCREEN_POSITIVE" if decrease >= .05 and novel["action_ap"] >= control["action_ap"]
                else "SCREEN_GATE_FAIL", relative_mse_decrease=decrease,
                action_ap_delta=novel["action_ap"]-control["action_ap"])


def evaluate(out=OUT, purge_path=None):
    plan = load_plan(out)
    truth = {}
    with MANIFEST.open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["seqid"] == "chr13" and row["role"] == "DEV":
                truth[row["candidate_id"]] = row
    ids, arrays = [], defaultdict(list)
    for b in [b for b in plan["blocks"] if b["role"] == "DEV"]:
        with np.load(out / "predictions" / (b["key"]+".npz")) as pred:
            if pred["ids"].tolist() != [r["candidate_id"] for r in b["rows"]]:
                raise ValueError("prediction identity order mismatch")
            ids.extend(pred["ids"].tolist())
            for k in pred.files:
                if k != "ids":
                    arrays[k].append(pred[k])
    if len(ids) != len(set(ids)) or set(ids) != set(truth) or len(ids) != 60574:
        raise ValueError("DEV prediction universe incomplete")
    known = np.asarray([truth[c]["comparator_known"] == "1" for c in ids])
    if int(known.sum()) != 60569:
        raise ValueError("known DEV denominator differs")
    positive = np.asarray([int(truth[c]["positive_bp"]) for c in ids])
    negative = np.asarray([int(truth[c]["negative_bp"]) for c in ids])
    arrays = {k: np.concatenate(v) for k, v in arrays.items()}
    if any(not np.isfinite(v).all() for v in arrays.values()):
        raise ValueError("inference nonfinite, including unknown rows")
    subsets = {"known_DEV": known}
    for stratum in base.LENGTH_STRATA:
        subsets["length_"+stratum] = known & np.asarray([truth[c]["length_stratum"] == stratum for c in ids])
    if purge_path is None:
        raise ValueError("original DEV homology purge is required for promised challenge")
    with Path(purge_path).open() as handle:
        purge = {r["candidate_id"]: r["purged"] == "1" for r in csv.DictReader(handle, delimiter="\t")}
    if set(purge) != set(ids):
        raise ValueError("original purge identities differ from DEV")
    subsets["original_homology_purged_DEV"] = known & np.asarray([not purge[c] for c in ids])
    results = {}
    for arm in ARMS:
        mean_logits = np.mean([arrays[f"{arm}__seed{s}"] for s in SEEDS], axis=0)
        results[arm] = {name: metrics(mean_logits[mask], positive[mask], negative[mask]) for name, mask in subsets.items()}
        results[arm]["per_seed_known_DEV"] = {str(s): metrics(arrays[f"{arm}__seed{s}"][known],
                         positive[known], negative[known]) for s in SEEDS}
    gates = {arm: decision(results["H0-O"]["known_DEV"], results[arm]["known_DEV"]) for arm in ARMS[1:]}
    result = dict(experiment_id=EID, status="RESULTS_COMPLETE", training_rows=plan["training_rows"],
        dev_rows=len(ids), known_dev=int(known.sum()), unknown_dev=int((~known).sum()),
        results=results, gates=gates, claims="exploratory bounded-screen only; no deployment or full-route falsification",
        cal_or_sealed_scored=False)
    write_json(out / "result.json", result)
    log("RESULTS_COMPLETE", gates=gates)
    return result


def smoke_budget(out=OUT):
    plan = load_plan(out)
    e = json.loads((out / "smoke_extract.json").read_text())
    t = json.loads((out / "smoke_training/summary.json").read_text())
    total_windows = sum(len(b["starts"]) for b in plan["blocks"])
    extract_seconds = 1.5*((total_windows-e["p3_windows"])*e["p3_seconds"]/e["p3_windows"]
                        +(2*total_windows-e["nt_windows"])*e["nt_seconds"]/e["nt_windows"])
    # Includes disk loading; nine-head DEV prediction cost conservatively charged as a training pass.
    train_seconds = 1.5*t["seconds"]*(2*plan["training_rows"]+plan["dev_rows"])/t["rows"]
    result = dict(extract_seconds_with_margin=extract_seconds, train_predict_seconds_with_margin=train_seconds,
                  within_two_8h_caps=bool(extract_seconds <= 8*3600 and train_seconds <= 8*3600))
    write_json(out / "smoke_budget.json", result)
    log("SMOKE_BUDGET", **result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("prepare", "smoke", "extract", "train-predict", "evaluate"))
    p.add_argument("--output", type=Path, default=OUT)
    p.add_argument("--purge", type=Path)
    args = p.parse_args()
    if args.command == "prepare":
        prepare(args.output)
    elif args.command == "smoke":
        extract(args.output, True)
        training(args.output, True)
        smoke_budget(args.output)
    elif args.command == "extract":
        extract(args.output)
    elif args.command == "train-predict":
        training(args.output)
        predict(args.output)
    else:
        evaluate(args.output, args.purge)


if __name__ == "__main__":
    main()
